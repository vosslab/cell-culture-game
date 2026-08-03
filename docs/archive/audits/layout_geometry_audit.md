# Scene layout geometric audit

This audit interprets the M2 scene health report against the layout engine
source, states the layout contract, constraint set, and objective function,
answers whether any scene is simultaneously sparse and heavily shrunk, ranks
each finding by value over risk, and fills a decision template for each
structural candidate. It is the gate document for milestone M5 (the conditional
structural packing refactor).

The hard product rule it serves lives in
[../../PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md) (never crop scientific
assets) and [../../PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md) item 1
(geometry is pure TypeScript). The engine reference is
[../../specs/LAYOUT_ENGINE.md](../../specs/LAYOUT_ENGINE.md). Authoring follow-ups
route to [../../LAYOUT_REMAINING_WORK.md](../../LAYOUT_REMAINING_WORK.md).

## Evidence basis and limits

- Source of metrics: `test-results/layout_health/health_report.json` and
  `health_report.md`, regenerated with
  `node --import tsx tools/layout_health_report.mjs --all`. 38 scenes analyzed.
- Shrink evidence is PROXY-derived. The engine exposes no true
  rescale-iteration counter and no floors-hit counter. The proxy fields are
  `final_scale`, `at_h_floor`, the uniform-rescale factor, `shrunk_passes`, and
  `dm_shrink`. No iteration count is reported or implied. This matches scope
  decision 1 (shrink telemetry is out of scope for M1/M2; precise instrumentation
  is a conditional M5 prerequisite, not assumed here).
- Geometry metrics are approximate authoring diagnostics: 50x50 largest-empty-
  rectangle grid, 200x200 union-area fill (scope decision 6). Scenes near a band
  edge are tagged borderline in the health report; this audit treats borderline
  engine-fit scenes as candidates for confirmation, not as proven defects.
- This audit edits no engine code. Every `file:line` citation below was
  cross-checked against the current source.

## The contract

The layout engine is a pure-TypeScript, build-time geometry solver. It places
scene objects into horizontally-zoned, depth-tiered rows and emits positioned
`ComputedItem` records consumed verbatim by the renderer.

| Item | Value | Source |
| --- | --- | --- |
| Frame | scene-percent, 0..100 of viewport per axis | `types.ts:2` |
| Origin | top-left, y increases downward | `types.ts:2`, `DEFAULT_SCENE_BOUNDS` `constants.ts:117` |
| Canonical viewport | 1920 x 1080 (16:9); any 16:9 yields identical layout | `DEFAULT_VIEWPORT` `constants.ts:116`; `LAYOUT_ENGINE.md` build pipeline |
| Default scene bounds | left 1, right 99, top 5, bottom 95 (scene-percent) | `DEFAULT_SCENE_BOUNDS` `constants.ts:117` |
| Bounds tolerance | report-only; bounds are seeds, not walls | `validatePhase` `phases.ts:433`; `LAYOUT_ENGINE.md` "forgiving, lenient" |
| Label-collision tolerance | `config.labelCollisionTolerance` slack on overlap tests | `layout_labels.ts:96,235` |
| Rescale fit tolerance | `UNIFORM_RESCALE_FIT_TOLERANCE = 1e-6` scene-percent | `vertical_layout.ts:283` |

The bounds check is report-only by design: the validate phase measures overflow
and records diagnostics but never moves an item to satisfy bounds
(`mutatesPositions: false`, `phases.ts:435`). The never-crop guarantee is met
upstream by aspect-preserving shrink, not by clamping.

## Constraint set

The engine optimizes placement subject to these constraints. Each is a real
behavior in the source, not an aspiration.

| Constraint | Meaning | Where enforced |
| --- | --- | --- |
| In-bounds (report) | items measured against `scene_bounds`; overflow graded, not clamped | `validatePhase` `phases.ts:433`; off-canvas classifier `phases.ts:449` |
| Aspect preserved | every shrink scales width and height by one factor; never crops | uniform rescale `vertical_layout.ts:386` onward; `LAYOUT_ENGINE.md:287` |
| Label legibility | object shrink has a floor so art stays readable | `MIN_SCALE = 0.55` `constants.ts:71`; `UNIFORM_RESCALE_MIN_SCALE = 0.27` `constants.ts:79` |
| Row order | item input order is preserved within a row | `row_strategy` / packer order, `LAYOUT_ENGINE.md:76` |
| Depth tiers | back/mid/front rows stack rear-toward-top with depth scale | `DEPTH_SCALE` `constants.ts:109`; reflow `phases.ts:290` |
| Same-tier non-overlap | objects in one tier row are 1D footprints with a minimum gap | `footprintFor` packing; gap floor in `row_strategy` |
| Related-item grouping | a zone is a meaningful physical region; tab-stops cluster within a row | zones `LAYOUT_ENGINE.md:100`; `ALIGN_MODES` `constants.ts:4` |

Two of these constraints are load-bearing for the M5 verdict and deserve
emphasis:

- Same-tier non-overlap is enforced as a 1D row-footprint pack, not through the
  2D `detectCollision` predicate. The predicate exists (`geometry/collision.ts`)
  and is consumed only by label de-overlap today (`layout_labels.ts:22`).
- Related-item grouping pins each object to an authored zone with fixed x-bounds
  (`x0`, `x1`). The horizontal packer fits objects WITHIN those x-bounds; it does
  not spill an object into canvas outside its zone. This is the single most
  important fact for interpreting the engine-fit findings below.

## Objective function

The packing model the audit uses as its lens optimizes, in priority order:

1. Maximize readable scale (keep `final_scale` high, away from the floors).
2. Minimize empty space inside the packable zones.
3. Avoid collisions (same-tier object overlap; label-vs-art and label-vs-label).
4. Preserve authored structure (zone membership, row order, depth tiers,
   tab-stop alignment, label side).

Objective 4 constrains objectives 1 and 2: the solver may not enlarge an object
by moving it out of its authored zone, even when empty canvas sits next to that
zone. This ordering is what makes the engine-fit scenes an authoring question,
not a solver question (see the central question below).

## The three shrink mechanisms (greedy rescue heuristic)

The engine has no single global fit solve. Instead it applies three independent
greedy shrink levers, in pipeline order, each rescuing a different overflow mode
for the objective above. Documenting them as one heuristic is the point: fit
logic accreted into three stages with three behaviors and two floors.

### Mechanism 1: horizontal convergence loop (per-zone width-scale)

- Location: `run_pipeline.ts:105` (loop), `run_pipeline.ts:143` (apply).
- Behavior: after each placement pass, every zone that emitted a fittable
  diagnostic has its items' `_width_scale` multiplied by `shrinkFactor`
  (`LAYOUT_SHRINK_FACTOR = 0.9`, `constants.ts:94`), then the placement phases
  re-run. Fittable kinds are `zone_overflow_negative_gap` and `tab_stop_overflow`
  only (`FITTABLE_KINDS` `run_pipeline.ts:57`); a vertical escape does not drive
  this loop.
- Bound: `maxPasses` (`MAX_LAYOUT_PASSES = 3`, `constants.ts:93`). On the last
  pass it emits `max_iterations_reached` and stops (`run_pipeline.ts:126`).
- Floor: the loop itself has no scale floor; the per-zone packer it re-enters
  enforces the `MIN_SCALE = 0.55` floor (mechanism 2).

### Mechanism 2: per-zone overflow packer (non-uniform shrink)

- Location: dispatch `horizontal_layout.ts:42`; trigger `horizontal_layout.ts:45`.
- Behavior: per zone, the dispatcher probes the row layout's required uniform
  scale; if `requiredScale < config.packer.thresholdScale` or the row overflows,
  it engages `packStrategy` (non-uniform per-item shrink plus gap compaction)
  instead of `rowStrategy`. The packer preserves primary-object scale and input
  order before maximizing area (`LAYOUT_ENGINE.md:76`).
- Floor: `MIN_SCALE = 0.55` (`constants.ts:71`), the horizontal packer floor.
  An item pinned here is reported `at_h_floor` in the health proxy.

### Mechanism 3: terminal uniform object rescale (one scene-wide factor)

- Location: `applyUniformRescale` `vertical_layout.ts:386`; invoked once from
  `run_pipeline.ts:165` when reflow reported the measured content overflows the
  scene vertical range.
- Behavior: one aspect-preserving factor multiplies every object's width and
  height, then the vertical tail re-runs once. It is a terminal scalar: it does
  NOT re-enter the convergence loop (`run_pipeline.ts:194`).
- Refinement: a bounded fixed-point loop, up to
  `UNIFORM_RESCALE_MAX_REFINE = 8` iterations (`vertical_layout.ts:279`,
  `vertical_layout.ts:348`), because the winning row can switch as scale shrinks.
- Floor: `UNIFORM_RESCALE_MIN_SCALE = 0.27` (`constants.ts:79`), distinct from
  the horizontal `MIN_SCALE`. Below the floor the scene reports `stillOverflow`
  (a real overload), and the factor is pinned to 0.27.

Summary: three shrink levers, two scale floors (0.55 horizontal, 0.27 vertical),
one capped loop (3 passes), one capped refinement (8 iterations). This is the
accreted-heuristic state any structural refactor must replace or justify.

## Central question: is any scene simultaneously sparse and heavily shrunk?

Answer: yes, for six scenes, but the empty space is authored dead space outside
the packable zones, not space the solver could legitimately use without
overriding authored zone geometry. The shrink is a correct response to
authored-narrow zones, not a solver defect.

The health report classifies exactly six scenes as engine-fit (room exists yet
the solver shrinks). They are the `high-empty-space-plus-shrink` category:

| Scene | fill | largest empty rect | mean final_scale | floor proxy |
| --- | --- | --- | --- | --- |
| adversarial_overflow_smoke | 0.0749 | 70% lower | 0.6833 | 67% at_h_floor; no uniform rescale |
| seeding_workspace | 0.0655 | 30.2% right | 0.2887 | 100% at_h_floor; uniform 0.3811 |
| sdspage_destain_gel_rock_workspace | 0.0255 | 22.9% right | 0.3187 | 100% at_h_floor; uniform 0.3187 |
| staining_bench | 0.0255 | 22.9% right | 0.3187 | 100% at_h_floor; uniform 0.3187 |
| drug_dilution_setup_bench_setup | 0.0651 | 24.1% center | 0.4198 | 100% at_h_floor; uniform 0.5205 |
| hood_basic | 0.1005 | 24.4% center | 0.485 | 100% at_h_floor; uniform 0.485 |

The proxy signal is unambiguous: these scenes shrink objects toward the floors
while a large empty rectangle sits to one side (right, center, or lower).

The decisive geometric fact is WHERE the empty rectangle sits. In every case it
sits to one side of the packed content, outside the x-span of the zones the
objects are assigned to. The engine respects authored zone `x0`/`x1` as hard
horizontal walls for packing (objective 4, related-item grouping). The empty
band belongs to a different, narrow, or unused zone region. The solver therefore
cannot widen objects into it without discarding authored zone geometry.

The health report's own suggested authoring targets confirm this. For all six
the remedy is authoring, not engine: "widen the packed zone (rear_right /
center) or spread objects into the empty band." That is a scene-YAML edit
(widen `x1`, reassign objects, or add a zone row), not a solver change. The
engine-fit LABEL is accurate as a proxy observation (room exists on canvas while
content shrinks); the engine-fit CAUSE is not a solver defect (the room is not in
a packable zone).

One scene needs a separate note. `adversarial_overflow_smoke` is a dev/test
overflow fixture with 21 objects and a 70% empty lower band; it intentionally
stresses the packer and is not a curriculum scene. It is excluded from the
student launcher and should not drive an engine decision.

The 16 authoring-class scenes (rank 7-23 in the scorecard, e.g.
`passage_hood_detachment_hood_workspace`, the sdspage workspaces) are the
honest authoring cases: too many objects for their zones, shrunk to fit with
little spare room. Only one scene reaches the vertical floor at all
(`passage_hood_detachment_hood_workspace`, uniform 0.27 AT v-floor). These route
to authoring, already the M2/WS-D path into
[../../LAYOUT_REMAINING_WORK.md](../../LAYOUT_REMAINING_WORK.md).

## Findings ranked by value over risk

Each candidate illogic is ranked by the value of fixing it against the risk of
the fix. Higher value-over-risk ranks higher.

| Rank | Finding | Value | Risk | Class | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Tunable sprawl: 2 floors, 1 loop cap, 1 refine cap, duplicate defaults | medium (clarity) | low (M4 is additive, harness-guarded) | engine hygiene | Addressed by M4 config consolidation, not M5 |
| 2 | Six engine-fit scenes shrink while side canvas is empty | medium (legibility) | high (fix needs authored-zone override) | authoring | Route to authoring; not a solver defect |
| 3 | Same-tier 2D de-overlap via `collision.ts` | low (no real collisions exist) | medium (could split intended layering) | none | NO-GO; zero same-tier collisions in all 38 scenes |
| 4 | Fixed-row packing reformulation replacing the three shrink stages | low-medium (fewer floors/phases) | high (rewrite a green 38-scene solver) | engine | NO-GO at this gate; feasible but unmotivated |

The highest value-over-risk item (tunable sprawl) is already owned by M4 and is
out of M5 scope. The two structural candidates (ranks 3 and 4) are the M5 gate
subjects and are templated below.

## Decision template: candidate (a) same-tier 2D de-overlap

- Summary: run the existing `detectCollision` predicate over same-tier object
  pairs and apply `buildResolutionCandidate` separations, so two objects in the
  same depth tier never visibly overlap.
- Affected files: `src/scene_runtime/layout/vertical_layout.ts` and/or
  `horizontal_layout.ts` (the same-tier consumer), reusing
  `src/scene_runtime/layout/geometry/collision.ts` (predicate unchanged).
- Invariant to preserve: cross-tier and cross-zone overlap stays exactly as
  authored z-layering. Only same-tier pairs may separate. The predicate already
  distinguishes these; the metrics tag every overlap edge same-tier, cross-tier,
  or cross-zone.
- Allowed deltas: position nudges of same-tier objects that currently overlap,
  along the cheaper-axis separation the predicate proposes.
- Rejection criteria (any one rejects the candidate):
  - No scene has a visually-confirmed same-tier collision (overlay screenshot,
    not numeric bbox overlap alone, since transparent padding can mislead).
  - The change would separate any cross-tier or cross-zone pair.
- Exact tests: `node --import tsx --test tests/test_layout_*.mjs`;
  `node tools/layout_metrics.mjs --all` showing same-tier overlap edges before
  and after; Playwright overlay screenshots of any named collision scene;
  `bash check_codebase.sh` 6/6.
- Evidence and verdict: NO-GO. The M2 overlap graph reports same-tier overlap
  count 0 for every one of the 38 scenes. The only object overlaps that exist
  are cross-zone z-layering (e.g. `hemocytometer_view` 6 cross-zone,
  `microscope_basic` 3 cross-zone, `passage_hood_detachment_microscope_view` 4
  cross-zone), all classified intentional and readable. The first rejection
  criterion fires: there is no real same-tier collision to fix. This candidate
  has nothing to act on. Confirmed: no scene has a same-tier collision.

## Decision template: candidate (b) fixed-row packing reformulation

- Summary: replace the three shrink stages with one fixed-row packer. Zone bands
  and depth tiers are fixed rows; each row is packed in 1D for order, gap,
  alignment, and tab-stops; rows stack vertically; one global fit scale
  maximizes viewport fill subject to never-crop and aspect preservation, using
  the shrink-severity and empty-space measures as the objective.
- Affected files: `src/scene_runtime/layout/run_pipeline.ts` (remove the
  convergence loop), `vertical_layout.ts` (remove the terminal uniform rescale),
  `horizontal_layout.ts` and `strategies/` (collapse row/packer dispatch),
  `constants.ts` (retire one or both floors). The renderer is untouched.
- Invariant to preserve: never-crop and aspect preservation
  ([../../PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md)); pure-TS authority
  (`PRIMARY_CONTRACT.md` item 1); authored zone membership, row order, depth
  tiers, tab-stop alignment, and fixed label overhead. The plan's gate forbids
  losing horizontal row reflow, per-row alignment, depth scaling, or fixed label
  overhead.
- Allowed deltas: per-scene coordinate changes within the regression harness,
  each categorized; an equal-or-better health report (no new off-canvas, no new
  never-crop failures, no worse label-stress, no new shrink-stressed scenes
  unless explained, scorecard improved or justified).
- Rejection criteria (any one rejects the candidate):
  - The health report does not show the solver packing poorly in a way the
    reformulation fixes.
  - The reformulation cannot meet at least one yardstick (fewer solver phases,
    fewer scale floors, fewer fallback paths, or fewer tunables) AND an
    equal-or-better health report.
  - It would relieve the engine-fit scenes only by overriding authored zone
    x-bounds (violating preserve-authored-structure).
- Exact tests: `node pipeline/precompute_layout.mjs`;
  `node tools/layout_golden_diff.mjs`; `node tools/layout_health_report.mjs
  --all`; `node --import tsx --test tests/test_layout_*.mjs`;
  `bash check_codebase.sh`; Playwright screenshots for every scene whose
  composition shifts.
- Evidence and verdict: NO-GO at this gate. The equivalence sketch below
  confirms the model is expressive and feasible, but the gate's motivating
  condition is not met and two rejection criteria fire (see the verdict section).

### Fixed-row packing equivalence sketch (scope decision 4, done here)

This sketch confirms whether fixed-row packing can express the four required
behaviors and whether it meets at least one yardstick. Per scope decision 4 it
is completed in this M3 audit; if the model could not express these, M5 may not
select it.

| Required behavior | Expressible in fixed-row packing? | How |
| --- | --- | --- |
| Tab-stops | YES | a row's 1D pack partitions items by `align_stop` into left/center/right sub-clusters; `row_strategy` already does this within a row |
| Per-row alignment | YES | each fixed row carries its own align mode (`ALIGN_MODES` `constants.ts:4`); alignment is a 1D row property |
| Depth scaling | YES | `DEPTH_SCALE` (`constants.ts:109`) applies per tier before packing; tiers map one-to-one to fixed rows |
| Fixed label overhead | YES | the measured vertical extent adds label gap plus label box as a fixed term independent of object scale (`verticalFootprintFor`, `LAYOUT_ENGINE.md:255`); a global object scale leaves it fixed by construction |

Yardstick check: a single global fit scale would replace the `MIN_SCALE` (0.55)
and `UNIFORM_RESCALE_MIN_SCALE` (0.27) floors plus the per-zone width-scale loop
with one floor and one solve. That is fewer scale floors (2 to 1), fewer solver
phases (the convergence loop and the terminal rescale collapse into one fit), and
fewer tunables (the loop cap, the refine cap, and one floor retire). The model
meets at least one yardstick.

Conclusion of the sketch: fixed-row packing CAN express tab-stops, per-row
alignment, depth scaling, and fixed label overhead, and it meets multiple
yardsticks. Expressiveness and feasibility are NOT the blocker. The blocker is
motivation and the authored-structure constraint, addressed next.

## M5 gate verdict

Verdict: NO-GO. No candidate clears the M5 entry gate. M5 closes with this no-go
artifact, per the plan's resolved decision 3 (a no-go is a valid, fully-specified
outcome) and the risk-register row "Packing simplification is infeasible ->
selecting none is a valid recorded outcome."

The deciding evidence, against the gate's three triggers:

- Trigger (a), named same-tier collisions: FAILS. The M2 overlap graph reports
  same-tier overlap count 0 across all 38 scenes. The de-overlap candidate has no
  real defect to act on.
- Trigger (b), green only by extreme shrink a better fit model would relieve:
  FAILS on the relief test. The six floor-pinned engine-fit scenes shrink because
  their objects are assigned to authored-narrow zones; the empty canvas sits
  OUTSIDE those zones' x-bounds. A fit model that honors authored zones shrinks
  exactly as today; a fit model that uses the empty band must override authored
  zone geometry, which the preserve-authored-structure constraint and the gate's
  "without losing per-row alignment" clause forbid. The relief is authoring
  (widen the zone or spread objects), not a solver change. Rejection criterion 3
  of candidate (b) fires.
- Trigger (c), solver packs poorly and can be simplified with equal-or-better
  health: FAILS on "packs poorly." Within authored constraints the solver packs
  correctly: zero never-crop hard fails, zero off-canvas art, zero same-tier
  overlap, every cross-tier overlap intentional. The only sense in which it
  "leaves room" is the authored dead space of trigger (b). Rewriting a green
  38-scene solver to shave two floors and a loop, when no scene is actually
  broken and the motivating cases are authoring problems, is high risk for low
  value. This conflicts with "focus on important issues" and "long-term over
  short-term" (a speculative rewrite risks regressing 32 healthy/authoring/
  intentional scenes). The tunable-sprawl concern is real but is already owned by
  the additive, harness-guarded M4 config consolidation, which does not touch the
  solver.

The selection rule resolves to none: candidate (a) only if same-tier collisions
exist (they do not); otherwise candidate (b) only if trigger (b) or (c) holds and
proves feasibility (the model is feasible but neither trigger holds). Select none.

What ships from this no-go:

- This audit, with the contract, constraint set, objective function, the
  sparse-and-shrunk answer, and both filled decision templates.
- The fixed-row equivalence sketch on record: the model is feasible and
  expressive, kept for a future "re-author the six engine-fit scenes, then
  reconsider the solver" path, should the authoring fixes land and the case
  recur.
- The six engine-fit scenes and the 16 authoring-class scenes routed to
  [../../LAYOUT_REMAINING_WORK.md](../../LAYOUT_REMAINING_WORK.md) as authoring
  work (widen zones, reassign objects, or add zone rows), owned by WS-D.

## Pure-TS authority and renderer boundary

Confirmed. Geometry is computed entirely in pure TypeScript and the renderer
consumes it verbatim.

- Authority: `runPipeline` (`run_pipeline.ts:59`) computes every coordinate.
  `pipeline/precompute_layout.mjs` bakes the result into
  `generated/precomputed_layout.ts` at build time
  (`LAYOUT_ENGINE.md:32`). The production browser loads precomputed positions via
  `resolvePrecomputedResult`
  (`src/scene_runtime/layout/precomputed_result.ts`) and never calls
  `runPipeline` (`LAYOUT_ENGINE.md:39`, `LAYOUT_ENGINE.md:55`).
- Renderer boundary: `src/scene_runtime/renderer/scene_item.tsx`,
  `scene_view.tsx`, and `render_scene.tsx` place objects from the
  `PipelineResult` with CSS absolute percentages, verbatim; layout is static
  after mount. No renderer file computes geometry. This satisfies
  `PRIMARY_CONTRACT.md` item 1 and is a strength to preserve, not a target to
  migrate into SolidJS.

Any structural change (if a future re-author path revives candidate (b)) edits
only `src/scene_runtime/layout/` and leaves `renderer/*.tsx` untouched; the
untouched renderer file set is itself the positive boundary check.

## CHANGELOG bullet (for closeout)

- Added `docs/active_plans/audits/layout_geometry_audit.md` (WS-E, M3): states
  the layout contract, constraint set, and objective function; documents the
  three shrink mechanisms with file:line; answers the sparse-and-shrunk question
  (six engine-fit scenes shrink while side canvas is authored dead space, a
  routing-to-authoring case, not a solver defect); fills decision templates for
  same-tier de-overlap (NO-GO, zero same-tier collisions in 38 scenes) and the
  fixed-row packing reformulation (feasible and expressive per the equivalence
  sketch, but NO-GO at the M5 gate); confirms pure-TS layout authority and the
  verbatim renderer boundary. M5 gate verdict: NO-GO, no structural patch;
  engine-fit and authoring scenes routed to docs/LAYOUT_REMAINING_WORK.md.
