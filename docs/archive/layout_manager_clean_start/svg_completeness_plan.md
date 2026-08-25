# SVG completeness plan

Date: 2026-05-22
Lane: C (SVG completeness)
Scope: read-only audit of SVG assets, object YAMLs, and experiment templates.
Output: this plan document only. No SVG, YAML, or template edits.

## 1. Purpose

Establish a single inventory of the scientific SVG assets the production
runtime needs, the placeholders that currently substitute for missing
assets, and the prioritized list of SVGs to author or commission before
the next layout-manager implementation can claim visual completeness.

User invariant (recorded in the lane prompt):

> All scientific objects must render as real SVGs. No placeholder
> bubbles, empty outlines, or generic fallback blobs. Production must
> never show `assets/equipment/_placeholder.svg`.

Canonical references this plan honors:

- [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md) item 3:
  clickable objects are SVG-backed scene objects laid out by the layout
  engine.
- [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md): never crop
  scientific SVG assets.
- [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md): asset
  enters under `assets/equipment/*.svg`, flows through the generator and
  facade, never bypassed.

## 2. Inventory of `assets/equipment/`

127 files tracked under `assets/equipment/` (count from
`git ls-files assets/equipment/ | wc -l`). 124 are SVG files. The three
non-SVG entries are documentation and sidecar:

- `bottle.colormap.json` (recolor sidecar)
- `MISSING_SVG_PLACEHOLDERS.md` (inventory of named placeholders)
- `SOURCES.md` (attribution log)

One of the 124 SVGs is the fallback file: `_placeholder.svg`. The other
123 are scientific assets. Grouping below assigns each scientific asset
to one kind. The grouping uses `kind:` from object YAMLs when an asset
is referenced by one; otherwise a filename heuristic (described in
section 11 source-of-truth note).

| Kind       | SVG count | Notes                                                                                                                              |
| ---------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| bottle     | 46        | includes bottles, vials, carboys, microtubes, sample tubes, falcon tubes; many ship `_empty`, `_filled` legacy variants            |
| flask      | 7         | one canonical `t75_flask`; six historical variants (`_legacy`, `_servier`, `_v2`..`_v5`)                                           |
| pipette    | 10        | aspirating, multichannel, p10 / p200 variants, serological, plus `micropipette_rack`                                               |
| plate      | 2         | `96well_pcr_plate`, `well_plate_24`                                                                                                |
| rack       | 3         | `conical_15ml_rack`, `microtube_rack_24_placeholder` (named placeholder), `tip_box`                                                |
| decoration | 7         | tip boxes, kimwipe pad, ethanol spray, gel loading tips, professor avatar                                                          |
| waste      | 3         | `biohazard_decant`, `waste_container`, `waste_tray`                                                                                |
| equipment  | 46        | centrifuge, microscope, microwave, plate reader, vortex, water bath, etc.; many ship `_new`, `_old`, `_legacy` historical variants |
| fallback   | 1         | `_placeholder.svg` (dashed-border rectangle, 100x100 viewBox)                                                                      |

Total scientific SVGs: 123 (excludes `_placeholder.svg`).
Total SVG files: 124.

The full per-kind enumeration is regenerable from
[`_temp_group_audit.py`](#11-data-sources-and-regeneration) (a temp
script removed after this audit; see section 11).

## 3. Inventory of `content/objects/`

78 object YAMLs tracked under `content/objects/`
(`git ls-files content/objects/ | wc -l`). Each declares
`object_name`, `kind`, and one or more `asset_name` references inside
`visual_states`. Distribution by kind directory:

| Kind directory | YAML count |
| -------------- | ---------- |
| bottle         | 31         |
| decoration     | 7          |
| equipment      | 21         |
| flask          | 2          |
| pipette        | 7          |
| plate          | 1          |
| rack           | 4          |
| waste          | 4          |

Across the 78 YAMLs, 67 unique `asset_name` values are referenced.
Eleven YAMLs reference more than one asset (typically state variants
such as `lightbox_off` / `lightbox_on`,
`microwave_closed` / `microwave_open`,
`p200_micropipette_empty` / `p200_micropipette_filled`).

Sample YAML shape (from `content/objects/equipment/heat_block.yaml`):

```
visual_states:
  lid_open:
    kind: svg
    cases:
      - when: false
        output: { asset_name: heat_block_closed }
      - when: true
        output: { asset_name: heat_block_open }
```

The `asset_name` value names a file under `assets/equipment/` without
the `.svg` extension. The facade (`src/svg_assets.ts`) resolves the
name to a generated SVG constant.

## 4. Cross-reference: experiments vs assets

Experiment files audited:

- `experiments/css_native_layout/templates/*.html` (10 production
  templates at the top level; 20 additional alternates under `dir_b/`
  and `dir_c/` not in scope for production)
- `experiments/css_native_layout/scenes/*.yaml` (two dense scenes)
- `experiments/css_native_layout/stress_scenes/**/*.yaml` and
  `*.html` (stress corpus, gold scenes, batch artifacts)
- `experiments/css_native_layout/spike_fixtures/**/*.html` (runtime
  dump fixtures)
- `experiments/css_native_layout/object_footprints.yaml` (closed
  object_name -> footprint class mapping, 124 entries)

The 10 production templates reference 35 unique SVG basenames. Every
one of those 35 is backed by a real SVG file under
`assets/equipment/`. No production template references
`_placeholder.svg` (the fallback). See section 7 for the placeholder
audit.

Across experiments more broadly (templates + scenes + stress + spike),
35 SVG basenames are referenced via `assets/equipment/<name>.svg`
img-src paths. 40 distinct object_name tokens appear as
`data-object-name="..."` attributes. The footprints YAML lists 124
object_name keys.

Combined experiment-referenced object_names plus footprint-map keys
total 144 distinct names. 79 of those have no matching YAML under
`content/objects/`. See section 6 for the asymmetry analysis.

## 5. Missing SVG assets

A missing SVG is an `asset_name` referenced by an object YAML or a
production template that has no corresponding `.svg` file under
`assets/equipment/`. Twelve such references exist today, all from
object YAMLs (none from production templates). Source object YAMLs are
listed alongside each name.

| Missing SVG name                      | Referenced by                                         |
| ------------------------------------- | ----------------------------------------------------- |
| `centrifuge_idle`                     | `content/objects/equipment/centrifuge.yaml`           |
| `centrifuge_spinning`                 | `content/objects/equipment/centrifuge.yaml`           |
| `electrophoresis_tank_with_lid`       | `content/objects/equipment/electrophoresis_tank.yaml` |
| `electrophoresis_tank_with_module`    | `content/objects/equipment/electrophoresis_tank.yaml` |
| `electrophoresis_tank_without_lid`    | `content/objects/equipment/electrophoresis_tank.yaml` |
| `electrophoresis_tank_without_module` | `content/objects/equipment/electrophoresis_tank.yaml` |
| `plate_reader_idle`                   | `content/objects/equipment/plate_reader.yaml`         |
| `plate_reader_reading`                | `content/objects/equipment/plate_reader.yaml`         |
| `trypan_blue_bottle`                  | `content/objects/bottle/trypan_blue_bottle.yaml`      |
| `water_bath_heating`                  | `content/objects/equipment/water_bath.yaml`           |
| `water_bath_idle`                     | `content/objects/equipment/water_bath.yaml`           |
| `well`                                | `content/objects/plate/well_plate_96.yaml`            |

Pattern observations:

- `centrifuge.yaml`, `electrophoresis_tank.yaml`, `plate_reader.yaml`,
  and `water_bath.yaml` declare state-variant `asset_name` entries
  (idle / running, with / without lid, etc.) that the asset folder
  does not yet ship. The current asset folder has base SVGs
  (`centrifuge.svg`, `electrophoresis_tank.svg`,
  `plate_reader.svg`, `water_bath.svg`) but not the variants.
- `trypan_blue_bottle` is a fresh bottle entry with no SVG yet.
- `well` is the inner well of the 96-well plate. The 96-well plate
  asset (`96well_pcr_plate.svg`) exists; an individual well sub-asset
  does not. This may be intentional (rendered as a primitive shape by
  the well-plate adapter, not as a standalone SVG) and the YAML
  reference may be unsafe.

## 6. Orphan SVG assets

An orphan SVG is a file under `assets/equipment/` that is referenced
neither by an object YAML's `asset_name` nor by any experiment template,
scene, stress scene, spike fixture, or `object_footprints.yaml` entry.
49 orphan SVGs exist today:

```
angry_professor
biohazard_decant
bme_bottle_empty
bottle_medium_pink
cell_counter_old
centrifuge
conical_15ml_rack
coomassie_recycle_bottle_empty
coomassie_stain_bottle_empty
ddh2o_bottle_empty
destain_bottle_empty
destain_waste_bottle_empty
falcon_50ml
falcon_50ml_new
incubator_legacy
incubator_new
laemmli_4x_bottle_empty
micropipette_rack
microscope_new
microscope_old
microtube_empty
microtube_filled
microtube_open_translucent
multichannel_pipette_new
multichannel_pipette_old
p10_gel_loading_tip
plate_reader
plate_reader_new
plate_reader_old
protein_ladder_tube_empty
protein_sample_tube_empty
protein_sample_tube_filled
recycle_buffer_bottle_empty
recycle_buffer_bottle_filled
running_buffer_10x_bottle_empty
running_buffer_1x_carboy_empty
t75_flask_legacy
t75_flask_servier
t75_flask_v2
t75_flask_v3
t75_flask_v4
t75_flask_v5
tip_box_old
vortex_new
vortex_old
water_bath
water_bath_new
water_bath_old
well_plate_24
```

Orphan categories:

- **Legacy / historical variants** (24): six t75 flask iterations,
  three microscope variants, three plate reader variants, three vortex
  variants, three water bath variants, two falcon 50ml variants, two
  incubator variants. The current object YAMLs reference exactly one
  base asset per equipment kind. Legacy variants linger from earlier
  development rounds.
- **`_empty` state variants** (12): the legacy variant pattern in
  `docs/specs/SVG_PIPELINE.md` "How to add or update a recipe" is
  superseded by the canonical single-base-SVG + runtime liquid overlay
  rule in `docs/specs/MATERIAL_CONVENTION.md`. `_empty` and `_filled`
  pairs are leftover from the legacy recipe approach.
- **Material-overlay variants** (`microtube_open_translucent`,
  `bottle_medium_pink`): Bioicons facade aliases discussed in
  `docs/specs/SVG_PIPELINE.md` "Bioicons facade aliases"; not yet wired
  into a content YAML so they appear orphan but are reachable through
  the facade.
- **Currently-unused decoration / waste** (`angry_professor`,
  `biohazard_decant`): assets present in the folder but absent from any
  scene currently authored.

Orphan SVGs are not a defect per se. They become a defect if they
crowd out the legitimate asset set or block a clean canonical inventory.
The action recommendation is in section 8 (asset folder hygiene), not a
prerequisite for visual completeness.

## 7. The `_placeholder.svg` policy

### Current location and shape

`assets/equipment/_placeholder.svg` is a 100x100 viewBox SVG with a
dashed border (`stroke #999, stroke-width 2, stroke-dasharray 4,2`),
the literal text "PLACEHOLDER" rendered in center, and no
content-specific identity. It is the visual fallback that the
experiment-local stress renderer
`experiments/css_native_layout/render_stress_to_html.py` substitutes
when an object_name has no real SVG.

### Where it appears

A strict-boundary audit (matching `/_placeholder.svg` only, not
substring matches that catch `microtube_rack_24_placeholder.svg`)
finds seven tracked files referencing the fallback:

- 1 file under `assets/equipment/` itself: `SOURCES.md` (description).
- 5 archived plan / audit docs under
  `docs/archive/plan-reset-2026-05-22/` (descriptive, not rendered).
- 1 stress-results summary under
  `experiments/css_native_layout/stress_results/` (log of stress
  rendering).
- 2 references in this onboarding bundle's
  `ONBOARDING.md` (descriptive).

No production template under `experiments/css_native_layout/templates/`
references `_placeholder.svg`. Three showcase HTML demos under
`experiments/css_native_layout/showcase/` contain the string in inline
comments only; visually they render real SVGs.

### Why it exists

The experiment-local static renderer
(`render_stress_to_html.py` lines 105-116) substitutes
`_placeholder.svg` when an `object_name.svg` file is absent in
`assets/equipment/`. This keeps the stress-render pipeline running over
synthetic stress scenes that mention objects with no committed art.
The renderer warns on every fallback so the missing asset is visible
in the build log.

The renderer is explicit that this is experiment-local:

```python
# experiments/css_native_layout/render_stress_to_html.py
"""
This is an EXPERIMENT-LOCAL static visual-test renderer. It is not the
production runtime renderer.
"""
```

### Production rule

Production runtime must never render `_placeholder.svg`. Two stronger
formulations follow:

- **Refuse to load.** The production SVG facade
  (`src/svg_assets.ts`) must not expose `_placeholder` as a resolvable
  asset id. The generator (`pipeline/generate_svg_globals.py`) emits a
  per-asset constant for every `assets/equipment/*.svg`; the facade is
  the choke point that decides which constants are exposed to scenes.
- **Hard-fail at the precheck / diagnostic gate.** Any rendered DOM
  whose `<img src=...>` resolves to `_placeholder.svg` is a hard fail.
  This is symmetrical with the no-crop hard fail in
  `docs/PRIMARY_DESIGN.md`; both protect "the rendered scene shows the
  real object."

These rules are statements of intent here. Implementation lives outside
this lane: the lane is documentation-only.

## 8. SVG completeness plan

Prioritized list of SVGs to author or commission, partitioned by
production use.

### MUST-HAVE (12 assets; production-blocking)

These twelve missing SVGs are referenced by canonical object YAMLs
under `content/objects/`. A production scene that uses any of these
objects cannot render its declared state without these assets. They
are the only blocker between the current asset folder and a complete
production-render path.

- `centrifuge_idle` and `centrifuge_spinning` (centrifuge run states).
  Today only `centrifuge.svg` and `centrifuge_new.svg` exist.
- `electrophoresis_tank_with_lid`, `electrophoresis_tank_without_lid`,
  `electrophoresis_tank_with_module`,
  `electrophoresis_tank_without_module` (gel-tank lid and electrode
  module states). Today only `electrophoresis_tank.svg` plus inner /
  outer chamber sub-parts exist.
- `plate_reader_idle` and `plate_reader_reading` (plate reader
  run states). Today only `plate_reader.svg`, `plate_reader_new.svg`,
  and `plate_reader_old.svg` exist.
- `water_bath_idle` and `water_bath_heating` (water bath run states).
  Today only `water_bath.svg`, `water_bath_new.svg`, and
  `water_bath_old.svg` exist.
- `trypan_blue_bottle` (named reagent bottle for the trypan-blue
  cell-count workflow).
- `well` (single well sub-asset for the 96-well plate). This entry is
  flagged for review: a single well may be a render primitive emitted
  by the well-plate adapter rather than a standalone SVG file. Resolve
  whether the YAML asset_name should remain `well` (which then needs a
  real SVG) or be removed in favor of an adapter-rendered primitive.

### SHOULD-HAVE (used in stress and gold scenes; not production-blocking)

The stress corpus references additional object_name tokens that do not
have an SVG and do not yet have an object YAML either. The renderer
falls back to `_placeholder.svg` for these in stress output. They are
not currently in any production template, so they are not blocking
production visual completeness, but they will appear if those scenes
are promoted to real protocols.

Examples (drawn from `object_footprints.yaml` and stress scenes;
absent from production templates):

- `beaker_250ml`, `flask_250ml`, `flask_1000ml`, `erlenmeyer_2000ml`,
  `graduated_cylinder`, `graduated_cylinder_500ml`,
  `graduated_cylinder_1000ml` (general glassware).
- `pbs_buffer_bottle`, `tris_buffer_bottle`,
  `phosphate_buffered_saline_solution_bottle_500ml`,
  `sodium_dodecyl_sulfate_running_buffer_bottle`,
  `tetramethylethylenediamine_catalyst_bottle`,
  `tris_acetate_edta_electrophoresis_buffer_bottle` (named reagent
  bottles).
- `tube_rack_15ml`, `tube_rack_24`, `microtube_rack`,
  `dilution_rack`, `drug_vial_rack` (rack variants).
- `tip_box_10`, `tip_box_200`, `p1000_pipette`, `micropipette_p10`,
  `micropipette_p1000`, `micropipette_p200` (pipette and tip
  variants).
- `glass_slide`, `slide`, `sample_tube`, `ladder_tube`,
  `drug_vial`, `mtt_vial` (small tools and sample tubes).

The full list of 79 stress-only object names without YAML is in the
audit JSON output recorded at audit time (path
`/tmp/svg_audit_result.json`, key `objects_without_yaml`).

The SHOULD-HAVE inventory is open and changes as new protocols are
authored. A canonical entry only enters MUST-HAVE when a corresponding
object YAML under `content/objects/` is committed.

### NICE-TO-HAVE (decorative; current orphans)

Decorative orphans already in `assets/equipment/`
(`angry_professor`, `bottle_medium_pink`, `microtube_open_translucent`)
do not block production. They are available through the SVG facade
when an object YAML or scene references them. No new SVG work is
required.

### Out-of-scope here

- Material color overlays applied to the single base SVG (the
  canonical rule in
  [MATERIAL_CONVENTION.md](../../specs/MATERIAL_CONVENTION.md)).
  Liquid-state visuals are produced at runtime from one base SVG;
  authoring more `_empty` / `_filled` pairs is the wrong fix.
- Legacy `_empty` / `_filled` orphan deletion. That is a separate
  asset-folder hygiene pass that touches no scene and no contract.
  Defer until a clean retirement criterion is approved.

## 9. Acceptance criteria for "SVG complete"

A future lane that closes this gap should accept these gates:

1. **Zero placeholders in production templates.** No file under
   `experiments/css_native_layout/templates/*.html` (top level, not
   `dir_b/` / `dir_c/`) and no canonical scene HTML under any future
   production scene path may contain the substring
   `/_placeholder.svg` in any `<img src=...>`.
2. **Production runtime refuses to load `_placeholder.svg`.** The SVG
   facade in `src/svg_assets.ts` must not include `_placeholder` in
   any exposed asset-id list; `getEquipmentSvg("_placeholder")` must
   throw. The placeholder file may stay in `assets/equipment/` as the
   experiment-local fallback for the static stress renderer, but it is
   not reachable through the facade.
3. **Every `asset_name` in `content/objects/` resolves.** A new
   pytest check (suggested name `tests/test_object_assets_resolve.py`)
   walks every `content/objects/**/*.yaml`, collects every
   `asset_name`, and asserts each name has a matching
   `assets/equipment/<name>.svg`. Today the 12 names in section 5
   would fail; the check is the gate that confirms they have been
   filled.
4. **CI flags new placeholder references.** A repo-wide check
   (extending `tests/test_markdown_links.py` style or a new
   `tests/test_no_placeholder_references.py`) fails if any tracked
   file outside `docs/`, `assets/equipment/SOURCES.md`,
   `assets/equipment/MISSING_SVG_PLACEHOLDERS.md`, and
   `experiments/css_native_layout/render_stress_to_html.py` introduces
   a new `_placeholder.svg` reference. This pins the fallback inside
   the experiment-local renderer and prevents drift back into
   production code or production templates.
5. **No-crop diagnostic remains hard fail.** Section 9 here does not
   subsume the no-crop rule in
   [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md). A real SVG
   that is cropped or aspect-distorted is still a visual failure even
   if the asset is present and the placeholder check passes.

## 10. Out-of-scope decisions

This lane does not propose, and a future implementation lane must not
treat this plan as authority for:

- Commissioning new SVG art. This plan enumerates the work; the
  authoring lane is separate.
- Deleting orphan SVGs. Removing legacy variants requires a
  retirement criterion and a confirmation that no scene path resolves
  to them.
- Modifying object YAMLs to drop missing `asset_name` references. The
  twelve missing-SVG cases in section 5 may be resolved either by
  authoring the SVG or by collapsing the variant in YAML; the choice
  is content-author work, not asset-pipeline work.
- Editing the SVG facade or generator. Sections 7 and 9 describe
  intent; implementation is the production runtime lane's job.
- Promoting `_placeholder.svg` to a styled production fallback. The
  user invariant in section 1 forbids this.

## 11. Data sources and regeneration

Inventory counts in this plan come from explicit
`git ls-files <pathspec>` queries against tracked files at HEAD:

| Count                                     | Command                                                                          |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| 127 tracked files under assets/equipment/ | `git ls-files assets/equipment/ \| wc -l`                                        |
| 124 SVG files in assets/equipment/        | `git ls-files assets/equipment/ \| grep -c '\.svg$'` (piped grep allowed)        |
| 78 object YAMLs                           | `git ls-files content/objects/ \| wc -l`                                         |
| 10 production templates                   | `git ls-files experiments/css_native_layout/templates/ \| grep -v dir_ \| wc -l` |

Cross-reference data (asset references, orphan list, missing list)
came from temp Python scripts under repo root with `_temp_` prefix.
Those scripts read tracked files, parse `asset_name` / `overlay_name`
references from YAMLs, scan `<img src=...>` patterns in HTML
templates, and compute set differences. The intermediate JSON output
was written to `/tmp/svg_audit_result.json` (gitignored;
recomputable). Per
[PYTHON_STYLE.md](../../PYTHON_STYLE.md) the underscore-prefixed
temp scripts are safe to delete after the audit and were created only
for this evidence pass.

If the audit needs to be re-run later, the regeneration shape is:

1. From repo root: `git ls-files assets/equipment/ \| grep '\.svg$'`
   for the SVG basenames.
2. From repo root: `git ls-files content/objects/` for the YAML
   inventory; parse each with `import yaml` for `object_name`,
   `kind`, and every `asset_name` / `overlay_name`.
3. From repo root: walk `experiments/css_native_layout/templates/`
   (top level only) and extract `assets/equipment/<name>.svg`
   patterns.
4. Compute set differences: missing = (yaml refs union template refs)
   minus (svg basenames); orphan = svg basenames minus (yaml refs
   union experiment refs union footprint keys).

## 12. Handoff

This document is the Lane C output. It is documentation-only. No
SVG, YAML, template, runtime, or generator file is modified by this
lane.

Next-lane prerequisites:

- A user decision on whether `well` (section 5) should be a real
  standalone SVG or removed in favor of an adapter-rendered primitive.
- A user decision on whether to delete the 49 orphan SVGs or keep them
  pinned for historical reference. Section 6 lists them but does not
  recommend deletion.

Until those decisions land, the canonical interpretation is: 11 truly
missing assets (the section 5 list minus `well`) plus one ambiguous
case (`well`) are the production-blocking work. Everything else
identified in section 8 SHOULD-HAVE and NICE-TO-HAVE is open content
work that follows protocol authoring, not asset-pipeline scope.

## 13. References

- [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md) - item 3
  binds clickable objects to SVG-backed scene objects.
- [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md) - never-crop
  rule for scientific SVG.
- [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) - asset
  pipeline ownership, the `assets/equipment/` source of truth, the
  generator and facade boundary.
- [MATERIAL_CONVENTION.md](../../specs/MATERIAL_CONVENTION.md) -
  single-base-SVG plus runtime liquid overlay rule that supersedes
  legacy `_empty` / `_filled` variant pairs.
- [ONBOARDING.md](ONBOARDING.md) -
  lane index and the broader clean-start context.
- The retired `assets/equipment/MISSING_SVG_PLACEHOLDERS.md` inventory recorded
  eleven named stand-in assets at the time of this plan. The 2026-08-24
  equipment-art census replaced every retained stand-in with finished artwork
  and removed that stale inventory; Git history preserves the original record.
