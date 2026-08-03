# Layout engine

## Overview

The layout engine places scene objects (bottles, pipettes, instruments, etc.)
into horizontally-zoned rows and emits positioned `ComputedItem` records. It
does not know lab biology, protocol meaning, click behavior, or scene-specific
rendering.

The engine runs at BUILD TIME only. `pipeline/precompute_layout.mjs` runs
`runPipeline` over every scene at canonical 16:9 (1920x1080) and emits
`generated/precomputed_layout.ts`. The production browser loads precomputed
positions via `resolvePrecomputedResult` in
`src/scene_runtime/layout/precomputed_result.ts` and never calls `runPipeline`.

Authored scene YAML is coordinate-free. Source zones provide only semantic
identity, declaration order, and approved alignment hints. The engine derives
scene bounds, zone bounds, and baselines after object binding and measurement.
Numeric geometry in this document refers to internal resolved records, not an
authoring surface.
Tests import the engine directly. See [CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md)
for the full file-level map.

The scene runtime is documented in [SCENE_ARCHITECTURE.md](SCENE_ARCHITECTURE.md).
The scene YAML schema is documented in [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md).
Object identity (state, assets, subparts) is documented in
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) and [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).

## Build pipeline

```text
content/base_scenes/*.yaml   +   content/protocols/.../scenes/*.yaml
  |
  v
pipeline/gen_scene_index.py  ->  generated/scenes.ts (SCENES)
  |
  v
pipeline/precompute_layout.mjs
  (imports SCENES, OBJECT_LIBRARY, ASSET_SPECS; runs runPipeline per scene)
  |
  v
generated/precomputed_layout.ts  (PRECOMPUTED_LAYOUT: per-scene { final: ComputedItem[] })
  |
  v
production browser: resolvePrecomputedResult(scene_name, scene)
  ->  PipelineResult  ->  renderScene()
```

## Production render path

```typescript
// protocol_host.tsx (simplified)
const scene_name = resolve_entry_scene_name(config, PROTOCOLS);
const scene = SCENES[scene_name];
const result = resolvePrecomputedResult(scene_name, scene);
renderScene(root, result);
```

`resolvePrecomputedResult` loads `PRECOMPUTED_LAYOUT[scene_name].final`, wraps
it in a `PipelineResult`, and passes it to the renderer. A missing entry throws.
No `runPipeline` call path ships in the production bundle.

## Source module seams

The layout engine is structured into four seams under
`src/scene_runtime/layout/`. See [CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md)
for file-level details.

- `geometry/` - Pure 2D AABB geometry core. Immutable `Vector` and `Aabb` value
  types. `detectCollision` returns a rich `Collision` fact;
  `buildResolutionCandidate` proposes the cheaper-axis correction.
  Geometry is pure and stateless; placement phases own all mutation.
- `config/` - `LayoutConfig` resolution by fixed precedence: global defaults,
  scene `layout_rules`, zone overrides, placement-derived values, then
  strategy-local values. Stages read every tunable through `LayoutConfig` rather
  than importing constants directly.
- `diagnostics/` - Severity-graded typed diagnostics keyed by severity (Error /
  Warning / Review-required) and likely owner. Error-severity codes fail the
  build. Per-scene decision metadata (selected strategy, packer trigger/result,
  shrink applied, rows created, resolved config) is emitted separately from the
  diagnostic stream.
- `strategies/` - `PlacementStrategy` seam with two implementations.
  `row_strategy.ts` is the default. The overflow packer (`pack_strategy.ts`)
  engages only when a row would shrink below the configured threshold or overflow;
  it preserves primary-object scale and input order before maximizing area.

`phases.ts` holds the phase registry. `runPipeline` drives named phases:
`prepare -> resolve-metadata -> measure -> partition -> place-horizontal ->
measure-vertical -> reflow-zones -> place-vertical -> place-labels ->
resolve-collisions -> validate -> report`,
with explicit read/mutate boundaries and a bounded deterministic convergence loop.
The former `clamp_scene_bounds` step is now a validation phase (`validate_bounds`),
not a silent fix.

## When to use the layout engine

Use it when the scene is made of lab objects arranged in physical rows or zones:
benches, hoods, shelves, equipment racks, storage areas, pipette stations.

Do not use it for structured scientific surfaces where individual subpart
positions or fills matter: 96-well plate grids, microtube racks (if tube fills
matter), microscope fields, plate-reader tables, gel lanes, graphs, or
instrument control panels. Use a custom geometry renderer for those surfaces.
The surrounding loose objects may still use the layout engine.

## Zones

A source zone is an ordered semantic group declared by `zone_name`, optional
`align`, and optional `label`. The manager derives its internal bounds and
baseline from measured demand. The former per-zone `gap` field is
retired; the inter-placement gap budget lives on scene-wide
`layout_rules.zone_gap` instead. See [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md)
"Zones" for the authored schema.

Alignment modes:

| Mode        | Placement rule                                                                   |
| ----------- | -------------------------------------------------------------------------------- |
| `left`      | First item visual left edge is flush with the padded left edge.                  |
| `right`     | Last item visual right edge is flush with the padded right edge.                 |
| `center`    | Cluster visual midpoint is centered in the padded zone.                          |
| `justify`   | First and last visual edges are pushed to both padded edges.                     |
| `tab-stops` | Items partitioned by `align_stop` into left, center, and right sub-clusters.     |

Zones represent meaningful physical regions. Avoid creating a zone for every
item; use `tab-stops` when one row has left, center, and right clusters.

The engine applies zone padding internally
(`bounds.left + ZONE_PADDING .. bounds.right - ZONE_PADDING`). Scene authors
do not pre-subtract padding in YAML.

### Zone population and alignment aesthetics

Think about the scene from an aesthetic scope: better alignment looks better,
especially where a zone holds only 1-2 objects. Objects that share a zone share
that zone's row baselines, so they line up cleanly; objects split across
separate side-by-side zones each resolve their own baseline and read as floating
at slightly different heights.

Author for alignment:

- Group related objects into ONE zone and let the alignment mode (`justify`,
  `center`, `tab-stops`) organize them into rows. Prefer fewer, fuller zones
  over many sparse zones.
- Leaving a zone empty is fine and often better. An empty zone costs nothing; a
  needless extra zone splits what should be one row and hurts alignment.
- Reserve a separate zone for a genuinely separate physical region, not for a
  horizontal slot within one shelf. For left/center/right clusters in a single
  shelf, use one zone with `tab-stops`, not three side-by-side zones.
- Put like with like. Keep a set of similar objects together in one group: five
  similar reagent bottles belong in one zone, organized as a row. When a scene
  has two distinct sets (for example reagent bottles versus waste containers),
  give each set its own group rather than interleaving them, so each group reads
  as a coherent unit.

Example: a rear shelf of five similar bottles reads best as one rear zone
(bottles aligned across it, like with like) rather than three side-by-side rear
zones holding one or two bottles each. Grouping by kind and aligning within the
group is the organizing goal; balancing footprint across many zones is not.

## Overflow

When items do not fit, the engine shrinks gaps then scales footprints and visual
widths down to the configured minimum. If content is still too large, negative
gaps (visible overlap) are permitted as an intentional failure mode. Fix
overflow by changing semantic zone membership, using tab stops, or correcting
an object-side intrinsic display dimension when it is wrong everywhere.

## Vertical placement

Vertical placement depends on two distinct per-placement fields that are
easy to confuse:

- `depth` (`back`, `mid`, `front`) scales an item's HORIZONTAL footprint
  only (`DEPTH_SCALE`: `back` 0.80, `mid` 1.00, `front` 1.10; see
  `footprint.ts`). It has no effect on vertical position or baseline. No
  current scene authors it; every placement defaults to `mid` (scale 1.00).
- `depth_tier` (a number) is the key that drives VERTICAL row banding.
  Items in a zone bucket into one row per distinct `depth_tier` value;
  ascending `depth_tier` orders rows toward the band top (rear tier
  first). See [Two-pass vertical reflow](#two-pass-vertical-reflow) below
  for how tier rows and their shared baseline are computed.

A SHELF is one `depth_tier` row across zones that semantic-zone lowering places
in the same derived horizontal row (for example
`rear_left` / `rear_center` / `rear_right`). Every object on a shelf shares
ONE baseline, so a row of unequal-height objects lands its bottom edges on
one common line instead of each zone floating at its own height. Zones the
reflow merely fused for a partial vertical overlap (a working-surface band
that touches a front band) keep their own shelves; only zones that resolve to
the same derived row form one shelf (`groupBandsByAuthoredRow` in
`vertical_layout.ts`).

The shared shelf baseline is derived by `shelfBaselineFor()`: the lowest
computed row bottom across the
   shelf's tier rows (`max(rowTop + rowHeight)`, so the tallest column
   defines the line), pulled up by the largest bottom-side label reserve
   present on the shelf, and floored so the tallest object's top never
   rises above its own row (containment). This computed geometry is the
sole source of the final anchor line. `baseline_override` is not an authored
placement field. The resolved zone baseline is internal geometry used by later
placement and diagnostic stages.

The `anchor_y` mode then maps the shelf baseline to the item's top edge;
see [Anchor-coordinate convention](#anchor-coordinate-convention) below for
the three modes and their `_top` formulas.

### Placement-layer alignment, not an extent-layer constraint

Cross-zone shelf alignment is a PLACEMENT-layer preference; it must never
become an EXTENT-layer (reflow) constraint. Shelf alignment moves anchor
LINES only, and it runs strictly after the reflow stage has already fixed
every band's height and reserved its label space (see
[Two-pass vertical reflow](#two-pass-vertical-reflow)), so aligning a shelf
can never grow a band or push a label into overflow.

This ordering is a hard rule, not a style preference. Reflow decides band
and tier-row heights, including each item's label reserve, before any
shelf line is computed; `shelfBaselineFor()` only reads that already-fixed
geometry and never feeds back into it. Folding shelf alignment into the
extent layer instead -- letting a cross-zone alignment goal renegotiate
band or tier-row heights -- would force label reserve to be recomputed
after label space was already budgeted, reopening exactly the class of
regression this two-pass split exists to prevent (see the
`groupVerticalBands` transitive band-merge defect and the
`unresolved_label_overlap` label-relayout note in
[wp_f1_bottom_align_scene_churn.md](../archive/reports/wp_f1_bottom_align_scene_churn.md)
for two real incidents caused by cross-zone geometry decisions leaking
into the wrong phase). Keeping shelf alignment strictly placement-layer
makes that class of regression structurally impossible, not merely rare.

A scene dense enough that a clean shared shelf line is not available
degrades gracefully rather than failing the build: an item whose band
lookup comes up empty falls back to its own per-zone baseline (computed
from that item's own zone bounds alone, not the cross-zone shelf), and the
engine emits an `item_escapes_zone_vertically` Warning-severity diagnostic
naming the zone and placement. Because every item on an unalignable tier
takes this same per-item fallback path, the net effect is that the whole
tier demotes to independent per-zone baselines rather than one shared
shelf line. This is always a Warning, never a build-failing Error; the
scene still renders, and the diagnostic tells a reviewer exactly which
placement lost shared shelf alignment. Alignment yields to
label-resolvability, tier by tier, locally -- never the other way around.

## Anchor-coordinate convention

The layout engine uses an explicit anchor-coordinate convention for all
computed layout-output fields. This convention applies only to these
output fields; scene authors continue to place objects through row, zone,
and placement rules in scene YAML and never write raw coordinates.

### Horizontal axis: shared footprint and visual center

`_centerX` is the shared horizontal center of both the object's footprint
box and its visual box, expressed as a scene percent. These two boxes share
one center because no horizontal visual offset exists in the system (the
visual box is always centered inside its footprint span). `_centerX` is
therefore simultaneously the footprint center, visual center, and label
anchor.

Bbox edges are derived, never stored:

- Visual left = `_centerX - _visualWidth / 2`
- Visual right = `_centerX + _visualWidth / 2`
- Footprint left = `_centerX - footprint / 2`

The renderer and structural guards derive CSS and bbox edges from
`_centerX` at the layout-to-render boundary:
`left: ${item._centerX - item._visualWidth / 2}%`.

Guard: if a horizontal visual offset field (`anchor_x`, `offset_x`,
`x_offset`) is ever introduced into the object or scene YAML vocabularies,
this section must be revisited to state which center `_centerX` means and
label attachment must then derive from the visual bbox center explicitly.

### Vertical axis: baseline with anchor modes

`_baselineY` is the vertical anchor baseline of the item's row
(scene percent). The `anchor_y` mode pins the object to this baseline.

The three anchor modes are (see `src/scene_runtime/layout/vertical_layout.ts`):

| `anchor_y` | Top-edge derivation (`_top`)                                    |
| ---------- | --------------------------------------------------------------- |
| `bottom`   | `_top = _baselineY - _height`                                   |
| `tip`      | `_top = _baselineY + anchor_y_offset - _height`                 |
| `top`      | `_top = _baselineY - _height / 2` (centering fallback; the `top` keyword is treated as center, unused by authored scenes) |

`_top` is a derived output field computed by `anchorTop()` in
`vertical_layout.ts`. It is stored for renderer consumption and is not
primary state.

In `tip` mode, `anchor_y_offset` shifts the anchored tip relative to the
baseline. A positive `anchor_y_offset` moves the object downward (the
tip hangs below the baseline by `anchor_y_offset`).

### Label coordinate fields

- `_labelX`: label center (scene percent); seeded from the object `_centerX`.
- `_labelY`: label TOP edge (scene percent); the renderer positions the
  label box using this top edge.

## Label placement semantics

`label_placement` controls whether a label renders above or below its
object. The two values are defined:

| Value    | Seed formula                                                              | Stagger direction                          |
| -------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| `top`    | `_labelY = _top - label_offset_y - line_height_pct * label_line_count`   | Stagger upward, away from artwork (default). |
| `bottom` | `_labelY = _baselineY + label_offset_y`                                   | Stagger downward (legacy direction).        |

`label_offset_y` is the symmetric artwork-to-label gap for both directions;
its magnitude does not change when placement flips.

Precedence (highest to lowest):

1. Per-placement `layout.label_placement` in scene YAML.
2. Scene-wide `layout_rules.label_placement` in scene YAML.
3. Engine config default: `top`.

The validator accepts an absent field at either location; the default is
resolved in the layout engine, not the validator.

`top` is the system default. Every scene renders labels above objects
unless an explicit `bottom` value is authored at the scene or placement
level. An authored `layout_rules.label_placement: bottom` restores
below-labels for a whole scene; per-placement `layout.label_placement`
overrides a single object. Both are accepted, documented authoring
choices, not workarounds.

Schema detail is in [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) "Layout
rules" and [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) "Label placement".

## Two-pass vertical reflow

The vertical axis is laid out by a measured-extent reflow that mirrors the
horizontal `footprintFor` convention on the other axis. Horizontally, the engine
measures each item's footprint (object plus side gaps) and packs footprints into
zones. Vertically, the engine measures each item's vertical extent and reflows
those extents into computed zone bands, then spaces depth-tier rows inside each
band.

The pass order is measure vertical extent, then reflow zone bands, then space
tier rows, then a terminal uniform object rescale when content still overflows
the scene range.

### Measured vertical extent (first-class quantity)

The measured vertical extent is the object height plus the artwork-to-label gap
plus the wrapped-label box height. It is computed by `verticalFootprintFor`
(`src/scene_runtime/layout/vertical_footprint.ts`), the vertical counterpart of
the horizontal `footprintFor`. The extent uses the REAL wrapped line count, so a
two-line label contributes a taller box than a one-line label. The magnitude is
side-independent: a `top` label and a `bottom` label produce the same combined
extent, because the gap and the box are the same size whichever side the label
sits on.

This measured extent is a first-class layout quantity. Tier-row heights, band
heights, and the uniform-rescale denominator are all derived from it, not from
the bare object height.

### Computed zone bands

A computed zone band (`ComputedZoneBand`) is the reflowed vertical range a zone
occupies after measurement. Zones whose derived vertical ranges overlap are
treated as one band group (side-by-side zones in a derived row share a band);
the group's height is the maximum of its member zones' content extents. Inside a
band, items bucket into depth-tier rows (one row per `depth_tier`), each row
height is the maximum measured extent over the side-by-side items in that tier,
and the rear tier is placed first at the band top with later tiers descending.
The depth-tier-to-vertical ordering and the rear-toward-top offset are preserved
from the pre-reflow model.

When the summed band content fits the scene vertical range, leftover space is
distributed proportionally to authored band height. When it does not fit, bands
compress to their content extents and the residual overflow is handed to the
uniform rescale below.

### Band-owned AABB containment invariant

Every coordinate in this invariant is expressed in the same frame as the rest
of this doc: scene percent (see the anchor-coordinate convention above), not
pixels and not authored zone units.

The invariant made true by construction: each item's final placed object box
(an axis-aligned bounding box, AABB) is contained within its assigned
computed zone band, and computed zone bands form a non-overlapping partition
of the scene's vertical range. An item cannot be placed with its box
extending outside the band that owns it, and two bands cannot claim the same
vertical range.

Band membership is same-horizontal-row grouping, not raw vertical-range
overlap. `groupVerticalBands` (`src/scene_runtime/layout/reflow_zones.ts`)
groups zones into one band only when they occupy the same horizontal row
(exact side-by-side zones, or a small documented partial-overlap pair). A
zone whose derived vertical span crosses multiple row cohorts is a spanning
overlay, not a row participant, and is placed in its own resolved bounds
outside the contiguous row stack rather than fusing the rows it crosses. A
predicate that instead treats any vertical-range overlap as row membership
lets a single tall zone transitively bridge unrelated rows into one band,
which breaks the containment invariant above: two items from different
authored rows can then be placed inside the same computed band and land at
the same coordinates.

The engine's own diagnostic must reflect final placement, not per-band
containment alone. A check that only verifies each item sits inside its own
band cannot see two items from different bands landing on the same
coordinates when those bands were wrongly fused upstream; the diagnostic
compares final placed object AABBs (the same boxes `vertical_layout.ts`
produces and the renderer draws) across every zone, not only within a single
band, so a real overlap always increments the reported overlap count. The
post-render guard (`checkNoItemOverlap`,
`src/scene_runtime/renderer/structural_guards.ts`) is the independent
rendered-DOM oracle for this same invariant.

### Terminal uniform object rescale

When reflowed content still overflows the scene vertical range, one
aspect-preserving factor is applied to every object's width and height together.
Because width and height shrink by the same factor, no object is cropped or
aspect-distorted by the rescale -- it is never-crop safe by construction. The
fixed layout magnitudes (label line height, label gap, tier gap, zone padding)
stay constant; only object art scales.

The rescale factor shrinks only the scalable object-height portion of the
content, not the fixed overhead:
`scale = (sceneRange - fixedOverhead) / (totalContent - fixedOverhead)`, where
`fixedOverhead` is the sum of zone padding, tier gaps, and per-item label boxes
and gaps. The factor is clamped to a floor of `UNIFORM_RESCALE_MIN_SCALE`
(`0.27`), the smallest value that still fits every measured non-fixture scene
with zero scientific art past the scene bottom. This vertical floor is distinct
from the horizontal packer `MIN_SCALE`.

### Design intent: forgiving, lenient, mutable, mercurial

The vertical layout manager is forgiving, lenient, mutable, and mercurial:

- forgiving: it accommodates imperfect fit, and never crops or crashes.
- demand-aware: derived bounds follow measured object and label demand.
- mutable: bands, baselines, and rows are computed, not fixed.
- mercurial: it reflows readily as measured content changes.

## Adding a new layout-driven scene

1. Create the scene YAML under `content/base_scenes/<name>.yaml`.
2. Define `placements` with stable `placement_name`, `object_name`, `zone`,
   `depth_tier`, and approved categorical hints (`align_stop`, `anchor_y`, or
   `label_placement`) when needed.
3. Define ordered `zones` with `zone_name`, optional `align`, and optional
   author-facing `label`; the manager derives bounds and baselines.
4. Add any missing `ASSET_SPECS` entries in `generated/object_library.ts`
   (via `content/objects/` YAML and `pipeline/gen_object_library.py`).
5. Re-run `bash pipeline/build_generated.sh` and then `pipeline/precompute_layout.mjs`
   to regenerate `generated/precomputed_layout.ts`.
6. Type-check with `npx tsc --noEmit -p tsconfig.json`.
7. Save screenshot evidence at laptop and desktop viewports.
8. If the scene participates in a protocol, run the relevant Playwright walker.

## Tuning order

1. Zone declaration order and placement zone membership.
2. `align`, `align_stop`, and depth tiers.
3. Object `display_width_cm` or other intrinsic object metric when that object
   is wrong everywhere.
4. Renderer-level label policy for dense, secondary placements.
5. Re-render and inspect the derived composition before changing another layer.

Avoid changing engine constants for a single scene; constants affect every
layout-driven scene.

## Off-canvas diagnostic stream (report-only)

The validate phase classifies every placed item against the scene bounds and
emits findings on `PipelineResult.offCanvasDiagnostics`. This stream is
report-only: it never blocks the build gate and does not affect placement output.

Two severity levels are used:

| Classification | Condition | Severity |
| --- | --- | --- |
| `fully_off_canvas` | Item bounding box lies entirely outside scene bounds. | Error-level (reported, not gating). |
| `partial_overflow` | Item bounding box partially crosses scene bounds. | Warning; severity scales with overflow magnitude. |

The classifier lives in `src/scene_runtime/layout/diagnostics/offcanvas.ts`.
`tools/offcanvas_baseline.mjs` writes a baseline report to
`docs/active_plans/audits/offcanvas_baseline.md` that lists every scene with its
count of flagged items. Placement byte values are unaffected by the classifier:
it reads existing `ComputedItem` records and adds diagnostic entries without
modifying coordinates.

Use `PipelineResult.offCanvasDiagnostics` in tools and tests to surface
off-canvas items without running a full browser render. The diagnostics are
separate from `PipelineResult.diagnostics` (severity-graded gate diagnostics) and
do not appear in the build log unless a tool explicitly surfaces them.

## Verification for code and YAML changes

For layout code or scene YAML changes:

```bash
npx tsc --noEmit -p tsconfig.json
bash build_github_pages.sh
```

Then save screenshot evidence at laptop and desktop viewports. A passing type
check proves the layout code compiles; screenshot evidence proves visual
correctness. If the scene participates in a protocol, also run the relevant
Playwright walker.

## Layout invariant: no clipping or distortion

Canonical home: [../PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md).

The layout engine must size containers to fit their placed objects' natural aspect ratios. A container that clips or distorts its placed asset is a layout failure regardless of bbox-level metrics. This rule applies even if precheck reports `hard_fail_count = 0`.

Forbidden in any rendered scene:

- Cropped bottoms of volumetric flasks
- Cropped bottle necks or caps
- Clipped pipette tips
- Hidden instrument edges
- Object artwork cut off by cards, regions, wrappers, `overflow: hidden`, or `.object-graphic` containers
- Squashing or stretching that changes the intended asset aspect ratio

Diagnostic requirement:

- The `artwork_integrity` check must compare the rendered asset bbox against its parent placement card and flag overflow clipping plus aspect-ratio deviation > 5%.
- Visible clipping is HARD FAIL.
- Aspect distortion is HARD FAIL for lab glassware, pipettes, plates, and instruments; advisory for decorative items.

Fix direction (not a substitute for the rule):

- Use `object-fit: contain`, never `cover`.
- Preserve SVG `preserveAspectRatio="xMidYMid meet"`.
- Remove parent `overflow: hidden` where it clips assets.
- Size cards around assets, not assets into too-small cards.
- Add `min-height` / `min-width` for tall glassware cards.

Anti-patterns (forbidden):

- Do not "fix" cropping by hiding cropped assets, deleting DOM, or weakening diagnostics.
- Do not accept a high score if the asset is visibly cropped.
- Do not claim visual success while glassware bottoms are cut off.

## Verification for documentation edits

For documentation-only edits, no runtime test is required. For code or scene
YAML changes that affect layout:

```bash
bash build_github_pages.sh
npx tsc --noEmit -p tsconfig.json
```

Then save screenshot evidence at laptop and desktop viewports. A passing type
check proves the layout code compiles; it does not prove the scene is visually
correct. If the scene participates in a protocol, also run the relevant
Playwright walker or scene-specific smoke test.

## Compile-time model and known limitations

The layout engine now runs at build time, not in the browser. The sections above
describe the algorithm; this section records the current model and its known
limitations so authors know what the engine does and does not do today.

Current model:

- Compile-time layout. `pipeline/precompute_layout.mjs` runs the engine over every
  scene at a canonical 16:9 viewport (1920x1080) and emits
  `generated/precomputed_layout.ts` (one `ComputedItem[]` per scene). The production
  browser path loads those precomputed positions and renders them inside an exact 16:9
  letterbox; resizing the window changes only the letterbox bars and the uniform scale
  factor, never the scene-internal composition. 16:9 is the single compiled contract; an
  alternate aspect ships as a separate authored scene variant, not as per-viewport reflow.
- Pure 2D geometry core. `src/scene_runtime/layout/geometry/` provides immutable
  `Vector` and `Aabb` value types plus an AABB collision detector that returns a rich
  `Collision` fact and a `ResolutionCandidate` (cheaper-axis correction, x-first tie-break).
  Geometry is pure and proposes corrections; only placement phases mutate positions.
- Declarative config. `src/scene_runtime/layout/config/` resolves a `LayoutConfig` by a
  fixed precedence (global defaults -> scene `layout_rules` -> zone overrides ->
  placement-derived -> strategy-local) with distinct label and object spacing keys. Stages
  read every tunable through `LayoutConfig` rather than importing constants directly.
- Placement strategies. `src/scene_runtime/layout/strategies/` exposes a
  `PlacementStrategy` seam; `row_strategy.ts` is the default and an overflow packer engages
  only when a row would shrink below the configured threshold or overflow, preserving
  primary-object scale and input order before maximizing area. Object placement stays 1D
  row footprint; same-tier de-overlap is deferred (see below).
- Phase registry. `run_pipeline.ts` runs named phases (`prepare -> resolve-metadata ->
  measure -> partition -> place-horizontal -> measure-vertical -> reflow-zones ->
  place-vertical -> place-labels -> resolve-collisions -> validate -> report`) with
  explicit read/mutate boundaries and a bounded, deterministic convergence loop. The
  former `clamp_scene_bounds` step is now a validation phase (`validate_bounds`), not a
  silent fix.
- Severity-graded diagnostics. `src/scene_runtime/layout/diagnostics/` emits typed
  diagnostics keyed by severity (Error / Warning / Review-required) and likely owner.
  Error-severity codes fail the build; Warnings and Review-required surface in the report
  and allow success. Per-scene decision metadata (selected strategy, packer trigger/result,
  shrink applied, rows created, resolved config) is emitted separately from the diagnostic
  stream.

Known limitations:

- Same-depth-tier object de-overlap is not implemented. Objects in the same `depth_tier`
  are placed as 1D row footprints and are not pushed apart by 2D geometry. Cross-tier
  overlap is preserved on purpose as authored z-layering. M7 evidence found no genuine
  same-tier real-asset overlap that harms composition, so this work (M8) stays deferred and
  evidence-gated (see
  [m8_same_tier_overlap_evidence.md](../archive/reports/m8_same_tier_overlap_evidence.md)).
- Authored per-zone strategy and per-item priority are not exposed in YAML. The strategy
  and shrink priority are derived (kind, footprint, `placement_name` tiebreak); a closed
  authored-enum surface is the deferred M9 RFC.
- Label placement resolves label-label and label-vs-artwork overlaps to zero for feasible
  scenes; an infeasible scene emits an `unresolved_label_overlap` Error with an actionable
  payload rather than silently clamping. A label clear of overlaps but far from its anchor
  is a `poor_label_alignment` Warning, not an error.
- Overall visual polish (composition, pedagogy, plausibility) is judged by a layered review
  -- typed diagnostics, the rendered bbox stats as a regression signal, an AI visual-polish
  reviewer over before/after screenshots, and human review for appeals -- not by any single
  score. The bbox scorecard is a regression detector, not the optimization target.

## Related docs

- [SCENE_ARCHITECTURE.md](SCENE_ARCHITECTURE.md) - Runtime scene driver,
  registry, adapter, and capability model.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) - Scene YAML fields and build
  pipeline.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) - Canonical scene terms.
- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) - Canonical object terms;
  asset metrics like `default_width` migrate here in the follow-on plan.
- [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) - Object-definition YAML
  schema referenced by scene placements.
- [SVG_PIPELINE.md](SVG_PIPELINE.md) - SVG asset generation and ownership.
