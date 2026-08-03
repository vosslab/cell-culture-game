# Layout model-layer synthesis (MR / WP-RESEARCH1)

Status: ratified for coding. This memo gates M1 (geometry) and M5 (object
placement) of plan `partitioned-shimmying-dragonfly`. It confirms the
research-synthesis interfaces from that plan's "Model layer design" section and
ships concrete contracts: TypeScript type sketches, a phase-registry skeleton,
and packer pseudocode. Coders implement against the contracts below.

All coordinates are scene-percent (0..100 of the canonical 16:9 frame per axis),
matching the existing engine convention stated in
`src/scene_runtime/layout/types.ts:2`.

## How to read this memo

Every interface below carries a one-line verdict: sufficient (implement as
written) or changed (implement the stated change). Section "Interface changes
and rejected alternatives" collects the deltas and the plan edits they imply.
Coder-facing rules are written in positive imperative form: do X, use Y,
preserve Z.

## Grounding sources

- Existing engine: `src/scene_runtime/layout/run_pipeline.ts`,
  `types.ts`, `horizontal_layout.ts`, `constants.ts`.
- SAT.js collision response: `OTHER_REPOS/UI/sat-js/SAT.js:576-607` (the
  `Response` object) and `SAT.js:698-734` (overlap and minimum-axis selection).
- elkjs option layering: `OTHER_REPOS/UI/elkjs/src/js/elk-api.js:13-72`
  (`defaultLayoutOptions` merged with per-call and per-node `layoutOptions`).

## Geometry and collision response

Verdict: sufficient. Geometry stays pure and deterministic. It computes
collision facts and proposes corrections; it never mutates positions. Only
layout phases apply corrections.

`Vector` and `Aabb` are immutable value types in scene-percent. `Aabb` uses the
`{ x, y, w, h }` top-left-plus-size form (the synthesis form), distinct from the
existing `Bounds { left, right, top, bottom }` edge form in `types.ts:28-33`.
Keep both: `Bounds` stays the zone/scene edge type the renderer and validator
already read; `Aabb` is the new geometry value type. Provide a one-line adapter
`aabbFromBounds(b: Bounds): Aabb` so phases can lift a zone or a placement box
into geometry space without duplicating math.

```ts
// layout/geometry/types.ts
export interface Vector {
  readonly x: number;
  readonly y: number;
}

// Axis-aligned box, top-left origin plus size, scene-percent.
export interface Aabb {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

// An immutable computed fact about one overlapping pair. Returned whole (not a
// bare vector) so a diagnostic can name both boxes and a separating vector
// without a second lookup.
export interface Collision {
  readonly boxIdA: string;
  readonly boxIdB: string;
  // The axis of minimum penetration; the cheaper axis to separate on.
  readonly overlapAxis: "x" | "y";
  // Penetration depth on overlapAxis, always positive.
  readonly overlapDepth: number;
  // Points from A's center toward B's center. Sign reference for the pair.
  readonly overlapVectorAtoB: Vector;
  // Moves A fully clear of B along overlapAxis. Magnitude === overlapDepth.
  readonly separationForA: Vector;
  // The exact negation of separationForA; moves B fully clear of A.
  readonly separationForB: Vector;
  // True when A is entirely inside B (and vice versa for bInA).
  readonly aInB: boolean;
  readonly bInA: boolean;
}

// A correction a layout phase may choose from. suggestedAxis is the cheaper
// (minimum-depth) axis; altAxis is the other axis when a phase prefers a row
// drop over a nudge. direction is the unit sign on suggestedAxis.
export interface ResolutionCandidate {
  readonly collision: Collision;
  readonly suggestedAxis: "x" | "y";
  readonly magnitude: number;
  readonly direction: -1 | 1;
  readonly altAxis?: "x" | "y";
}
```

Detection and tie-break rules (state these as code):

- Compute x-overlap and y-overlap as interval overlaps of the two boxes. Boxes
  collide only when both overlaps are strictly positive; treat touching edges
  (overlap === 0) as separated, not collided.
- Choose `overlapAxis` as the axis of smaller positive overlap. This mirrors
  SAT.js, which tracks the minimum absolute overlap across axes and keeps that
  axis's normal (`SAT.js:728-734`).
- Deterministic tie-break: when x-overlap === y-overlap, pick `x` first.
- `separationForA` lies on `overlapAxis` with the sign that moves A away from B
  (the side A's center sits on relative to B's center); `separationForB` is its
  exact negation. Magnitude equals `overlapDepth` on both.
- `aInB` / `bInA` mirror SAT.js `Response.aInB` / `bInA`
  (`SAT.js:603-604, 703-720`): true unless one box's edge falls outside the
  other on the tested axis.

Naming maps to SAT.js intent without inheriting its sign ambiguity:

| This memo | SAT.js `Response` | Note |
| --- | --- | --- |
| `overlapDepth` | `overlap` (`SAT.js:605`) | magnitude only, positive |
| `separationForA` | `overlapV` (`SAT.js:591`) | full MTV that extracts A from B |
| `overlapAxis` + `direction` | `overlapN` (`SAT.js:590`) | unit normal split into axis + sign |
| `aInB` / `bInA` | `aInB` / `bInA` | same meaning |

We name the vectors explicitly (`overlapVectorAtoB`, `separationForA`,
`separationForB`) because SAT.js's single `overlapV` plus a reversible
`overlapN` is a known sign-bug source; an immutable pair removes the ambiguity.

Resolution order (state in code): when a phase resolves a set of collisions,
sort candidates by `overlapDepth` descending, tie-break by `(boxIdA, boxIdB)`
lexicographically, so output is stable across builds.

## Phase model

Verdict: sufficient. Replace the four scattered fixes (label, vertical,
horizontal, clamp) with named phases and explicit mutation boundaries, run by a
phase registry in `run_pipeline.ts`. The phase order is:

```
prepare -> resolve-metadata -> measure -> partition ->
place-horizontal -> place-vertical -> place-labels ->
resolve-collisions -> validate -> report
```

Read/mutate boundary (state affirmatively in code):

- `place-horizontal`, `place-vertical`, `place-labels`, and `resolve-collisions`
  mutate item positions. These are the only position-mutating phases.
- `resolve-collisions` is the only phase that applies geometry results
  (`ResolutionCandidate`s) to positions.
- `prepare`, `resolve-metadata`, `measure`, `partition`, `validate`, and
  `report` are read-only with respect to position. Any phase may call geometry
  in read-only mode for measurement, validation, diagnostics, or reporting;
  only `resolve-collisions` turns a geometry result into a position change.
- Rename `clamp_scene_bounds.ts` to `validate_bounds.ts`. It becomes the
  `validate` phase: it measures out-of-bounds and emits a diagnostic, and stops
  silently translating the whole group as `clampSceneBounds` does today
  (`run_pipeline.ts:91-96`). The position fix moves into `resolve-collisions`;
  validation reports what remains.

Registry skeleton (pseudocode):

```text
type PhaseName =
  'prepare' | 'resolve-metadata' | 'measure' | 'partition' |
  'place-horizontal' | 'place-vertical' | 'place-labels' |
  'resolve-collisions' | 'validate' | 'report'

# Each phase is a pure function over a context value plus the resolved config.
# mutatesPositions is documentation enforced by review and by ctx access:
# read-only phases receive a readonly view of positions.
interface Phase {
  name: PhaseName
  mutatesPositions: boolean   # true only for place-* and resolve-collisions
  run(ctx: LayoutContext, config: LayoutConfig): LayoutContext
}

PHASE_ORDER = [prepare, resolve-metadata, measure, partition,
               place-horizontal, place-vertical, place-labels,
               resolve-collisions, validate, report]

function runPhases(ctx, config):
  for phase in PHASE_ORDER:
    ctx = phase.run(ctx, config)
  return ctx
```

Convergence loop (keep the existing bounded loop in `run_pipeline.ts:75-136`,
re-expressed over phases):

```text
function runPipeline(scene, opts):
  ctx = buildContext(scene, opts)        # prepare..partition, single pass
  for pass in 0 .. config.maxPasses - 1:
    ctx = runPlacementPhases(ctx, config)  # place-* -> resolve-collisions -> validate
    newFittable = ctx.diagnostics.filter(isFittableAndNew)
    if newFittable is empty: break
    if pass is last:
      emit max_iterations_reached
      break
    ctx = shrinkZones(ctx, zonesOf(newFittable))   # mirrors current shrink step
  return report(ctx)
```

The loop re-enters only on NEW fittable diagnostics, caps at `maxPasses`
(`MAX_LAYOUT_PASSES` is 3 today, `constants.ts:76`), and uses stable tie-breaks,
so it cannot loop or vary between builds. This convergence loop and the bounded
label passes are our own design, not borrowed from SAT.js (a single-shot test)
or ELK; keep them strictly bounded.

Provenance: the ordered multi-phase pipeline is the elkjs idea (ELK's layered
algorithm is phased: layer assignment, ordering, node placement, edge routing,
compaction, label handling). SAT.js contributes only the per-pair geometry
inside `resolve-collisions`.

## Config hierarchy

Verdict: sufficient. Resolve `LayoutConfig` by explicit precedence (lowest to
highest):

```
global defaults -> scene layout_rules -> zone overrides ->
placement-derived values -> strategy-local options
```

This mirrors elkjs, which merges `defaultLayoutOptions` (engine global) with
per-call `layoutOptions` and per-node options on the graph
(`elk-api.js:13-72`). Per-zone and per-placement overrides draw from existing
schema fields only (`LayoutRules`, `Zone.align/baseline/label`,
`PlacementAuthored.depth_tier/align_stop/baseline_override/layout`); this memo
adds no authored YAML.

```ts
// layout/config/types.ts
export interface SpacingConfig {
  // Margin-based spacing in scene-percent. Label and object spacing are
  // distinct keys; do not collapse them into one gap.
  readonly objectGap: number;   // between objects in a row (today: zone_gap)
  readonly labelGap: number;    // between labels during de-overlap
  readonly zonePadding: number; // inset from zone edges (today: ZONE_PADDING)
}

export interface PackerConfig {
  // Required row scale below which the packer is preferred over uniform shrink.
  readonly thresholdScale: number; // PACKER_THRESHOLD_SCALE, default 0.75
  readonly minScale: number;       // MIN_SCALE floor, 0.55 today
}

export interface LayoutConfig {
  readonly spacing: SpacingConfig;
  readonly packer: PackerConfig;
  readonly maxPasses: number;       // MAX_LAYOUT_PASSES, 3 today
  readonly shrinkFactor: number;    // LAYOUT_SHRINK_FACTOR, 0.9 today
  readonly labelFontSize: number;
  readonly labelLineHeight: number;
  readonly labelOffsetY: number;
  // Per-zone overrides resolved from Zone fields; sparse, keyed by zone id.
  readonly zoneOverrides: Readonly<Record<string, Partial<ZoneLayoutConfig>>>;
}

// The subset a per-zone override may set (drawn from existing zone/placement
// schema fields, never new authored keys).
export interface ZoneLayoutConfig {
  readonly align: AlignMode;        // existing Zone.align enum, constants.ts:4
  readonly baseline: number;        // existing Zone.baseline
  readonly spacing: SpacingConfig;
}

// resolveConfig(global, scene.layout_rules, zone, placementDerived, strategyLocal)
// applies the precedence above and returns a frozen LayoutConfig. It also
// records the effective resolved options into DecisionMetadata.resolvedConfig.
export function resolveConfig(
  globalDefaults: LayoutConfig,
  sceneRules: LayoutRules,
  zone: Zone,
  placementDerived: Partial<LayoutConfig>,
  strategyLocal: Partial<LayoutConfig>,
): LayoutConfig;
```

Spacing is margin-based and scene-percent; it interacts with shrink and packing
per zone (a tighter `objectGap` lets a row avoid the packer; the resolved
spacing is reported in the metadata).

## Packer objective and trigger

Verdict: sufficient. Run the row strategy first; use the packer only when the
row layout would require unacceptable shrink or produces overflow. The trigger
is a positive rule with a configurable threshold, not a hard truth.

```text
function placeZone(items, zone, config):
  rowResult = rowStrategy(items, zone, config)
  requiredScale = rowResult.scale          # uniform scale the row needed
  overflow = rowResult.overflowPct > 0     # negative-gap / out-of-bounds
  packerNeeded = requiredScale < config.packer.thresholdScale or overflow

  metadata.record(zone, {
    requiredRowScale: requiredScale,
    threshold: config.packer.thresholdScale,
    packerAttempted: packerNeeded,
  })

  if not packerNeeded:
    return rowResult

  packResult = packStrategy(items, zone, config)   # see cost below
  if packResult.fits:                              # all items scale >= MIN_SCALE
    metadata.record(zone, { packerResult: 'fit', rows: packResult.rows })
    return packResult

  # Could not fit even at MIN_SCALE: this is authoring overload.
  emit unresolved_overlap with actionable payload(
    scene, zone, items, remainingOverlap, availableArea,
    attemptedMoves, suggestedFix)
  metadata.record(zone, { packerResult: 'unresolved' })
  return packResult.bestEffort
```

`PACKER_THRESHOLD_SCALE` defaults to 0.75 and lives in `LayoutConfig.packer`,
not as a hard constant. `MIN_SCALE` (0.55, `constants.ts:68`) is the floor.

Lexicographic cost (minimize in strict priority order). Subject to the hard
constraints scale >= `MIN_SCALE`, in-bounds, and preserved input order; a
candidate that violates a hard constraint is infeasible and never compared:

```text
# Compare two feasible packings A and B. Return -1 if A is better.
function packingCost(packing):
  return [
    primaryWeightedShrinkPct(packing),   # 1. minimize; primary object weighted heaviest
    orderViolations(packing),            # 2. minimize departures from input order
    gapDeficit(packing),                 # 3. minimize negative/insufficient gaps
    overhang(packing),                   # 4. minimize out-of-zone overhang
  ]

function better(a, b):
  for i in 0 .. 3:
    if costA[i] != costB[i]: return costA[i] < costB[i] ? a : b
  return a   # full tie: keep first (stable)
```

Primary-weighted shrink is first, so the packer preserves the primary teaching
object's scale before maximizing area. Four reduced phases inside the packer:
width approximation, row placement, compaction (only on overflow), whitespace
expansion -- the elkjs rectpacking shape (`partitioned-shimmying-dragonfly.md`
"Packer objective and trigger"). Emit `unresolved_overlap` only when the packer
cannot fit at `MIN_SCALE`.

## Decision metadata

Verdict: sufficient. The build emits per-scene decision metadata beside
`generated/precomputed_layout.ts`, separate from the typed diagnostic stream.
The scorecard and the AI reviewer read this metadata; diagnostics stay the
severity-graded problem stream.

```ts
// layout/diagnostics/decision_metadata.ts
export interface ZoneDecision {
  readonly zoneId: string;
  readonly selectedStrategy: "row" | "pack";
  readonly requiredRowScale: number;
  readonly packerThreshold: number;
  readonly packerAttempted: boolean;
  readonly packerResult: "not-needed" | "fit" | "unresolved";
  readonly rowsCreated: number;
  // Per-item shrink actually applied, keyed by placement_name.
  readonly shrinkApplied: Readonly<Record<string, number>>;
  readonly resolvedConfig: LayoutConfig;
  // Constraints the engine could not satisfy (mirrors emitted Errors by code).
  readonly unresolvedConstraints: readonly string[];
}

export interface DecisionMetadata {
  readonly sceneName: string;
  readonly zones: readonly ZoneDecision[];
}
```

## Interface changes and rejected alternatives

Interface changes (deltas from the plan's synthesis prose):

1. `Aabb` is added alongside, not in place of, the existing `Bounds` edge type.
   Provide `aabbFromBounds`. Rationale: `Bounds { left, right, top, bottom }`
   is already the renderer/validator contract (`types.ts:28-33`); replacing it
   would ripple far beyond geometry. No plan-text change needed; this is an
   additive clarification.

2. `LayoutConfig` gains an explicit `packer: PackerConfig` sub-object carrying
   `thresholdScale` and `minScale`, rather than a bare `PACKER_THRESHOLD_SCALE`
   constant. Rationale: the plan already requires the threshold be configurable
   ("configurable threshold ... not a hard truth"); placing it under
   `LayoutConfig.packer` satisfies that and keeps `resolveConfig` the single
   merge point. No plan-text change needed.

3. The `validate` phase replaces the silent group translation in
   `clampSceneBounds`. The plan already calls for renaming
   `clamp_scene_bounds.ts` to `validate_bounds.ts`; this memo makes explicit
   that the translate-the-group behavior at `run_pipeline.ts:91-96` is dropped
   and the position fix moves to `resolve-collisions`. No plan-text change
   needed; it is the intended reading of "a validation phase, not a silent fix".

No interface required a blocking change. Every interface is sufficient for
coding as written above.

Rejected alternatives:

- Mutable shared `Response` object (SAT.js style, `SAT.js:587-607`): SAT.js
  reuses one `Response` across tests to avoid allocation. Rejected for the
  layout engine because mutation-by-reuse is a determinism and aliasing hazard
  across phases; build time is not a hot path. Use immutable `Collision` values.
- Single `overlapV` + reversible `overlapN` for direction: rejected as a known
  sign-bug source. Use the named `separationForA` / `separationForB` pair.
- Folding `Aabb` into `Bounds`: rejected; the two serve different layers (edge
  type for zones/renderer vs geometry value type).
- One merged spacing key for labels and objects: rejected; the plan requires
  distinct label and object spacing keys, so `SpacingConfig` keeps them split.
- A force-directed or stress de-overlap solver: rejected as non-deterministic
  (breaks the byte-identical build guarantee). Geometry stays exact AABB + MTV.

## Plan edits implied

None blocking. The three interface clarifications above are additive and
consistent with the existing plan text; M1 and M5 may start against the
contracts in this memo. Recommended (non-blocking) follow-on: when M1 lands
`layout/geometry/`, cite this memo as the ratified contract in
`docs/specs/LAYOUT_ENGINE.md`.
