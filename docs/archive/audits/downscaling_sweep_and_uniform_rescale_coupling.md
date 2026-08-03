# Downscaling sweep + uniform-rescale coupling finding

Date: 2026-07-03. Author: scene-layout manager. Status: sweep complete; one finding
routes to the architect (layout-engine change, out of scene-YAML boundary).

## Task

Rank every scene by downscaling (final_scale), find the binding constraint per low-floor
scene, and split each into "scene-YAML fixable (my lane)" vs "engine coupling (escalate)".
Constraint: large-by-design objects (incubator 40cm, microscope 35cm) are spec; never shrink,
reshape, or re-bbox one to lift a floor. Never touch the >= 0.50 gate to make numbers pass.

## Ranked final_scale table (mean ascending, scenes below 0.60)

Measured from `test-results/layout_metrics/<scene>_metrics.json`
(`uniform_rescale.factor`, `per_object[].final_scale`, `per_object[].dm_shrink`).

| scene | min | mean | uniform factor | coupling victims | crowded (dm<1) |
| --- | --- | --- | --- | --- | --- |
| passage_hood_detachment_hood_workspace (T7, before) | 0.254 | 0.427 | 0.461 | 7 | 2 |
| passage_hood_detachment_hood_workspace (T7, after) | 0.275 | 0.462 | 0.499 | 7 | 2 |
| hood_workspace (passage_pellet_reseed) | 0.318 | 0.524 | 0.577 | 0 | 3 |
| extraction_workspace | 0.327 | 0.569 | 0.584 | 0 | 1 |
| bench_basic | 0.329 | 0.572 | 0.599 | 0 | 2 |
| plate_workspace | 0.365 | 0.564 | 0.608 | 0 | 2 |
| plate_drug_treatment_media_adjustment_plate_workspace | 0.450 | 0.505 | 0.512 | 0 | 1 |
| seeding_workspace | 0.493 | 0.578 | 0.587 | 0 | 1 |
| electrophoresis_bench + 7 sdspage children | 0.584 | 0.584 | 0.584 | 0 | 0 |

- coupling victims = uncrowded objects (dm_shrink >= 0.98) dragged below 0.50 purely by the
  global uniform factor.
- crowded = objects with dm_shrink < 0.98 (genuine per-zone horizontal crowding).

## Mechanism (from `src/scene_runtime/layout/vertical_layout.ts`)

The scene-wide `uniform_rescale` is a vertical stack fit: every tier-row stacks vertically,
and total content height (object heights + per-row label overhead, `fixedOverhead`) must fit
the scene range through ONE factor applied to every object's width AND height (aspect
preserved), clamped to `[floor, 1]`. `labelDominant` is true when label height, not artwork,
drives the budget -- true on every low-floor scene.

Consequences confirmed empirically on T7:
- Adding a populated tier-row LOWERS the factor (more stacked label overhead): moving the
  pipette to its own tier dropped 0.461 -> 0.334.
- Moving the microscope into the wide center zone crowded the flask and dropped it to 0.308.
- Collapsing a sparse tier-row (hood_surface tier 2 -> tier 1, sharing the flask's center row)
  RAISED it 0.461 -> 0.499. This is the applied T7 fix. Kept.

## Per-scene classification

- T7 `passage_hood_detachment_hood_workspace`: SCENE lane, partially fixed. Collapsing the
  sparse third tier-row lifted the 7 readable glassware objects 0.461 -> 0.499 and mean to
  0.462. The two remaining sub-floor objects are the microscope (0.394) and aspirating pipette
  (0.275), both dm_shrink-crowded in the 27-wide `right_tool_area`. Lifting THOSE needs either a
  wider tool zone (a `hood_basic` base edit that regresses the 4 passing hood siblings) or the
  engine change below. The microscope and incubator are large-by-design and were NOT shrunk.
- All other low-floor scenes: mean already >= 0.50; their sub-floor MIN is one or two
  dm_shrink-crowded objects in a packed zone. These are the standard packer floors, not a
  readability defect across the scene.

## Finding for the architect (engine, out of scene-YAML boundary)

The single global `uniform_rescale` factor couples one over-tall row (a large-by-design object
plus its label) to every unrelated object in the scene. On T7, 7 of 9 objects are uncrowded
(dm_shrink = 1.0) yet dragged to the factor because ONE factor scales the whole scene. No
scene-YAML reallocation lifts those 7 past the factor; only reducing tier-row count helps, and
that bottoms out at the 2-row minimum (the applied fix). The durable fix is a layout-model
change: per-zone or per-object scale floors (or a per-band factor) instead of one global
factor, so a large-by-design object in one band does not shrink readable glassware in another.

This coupling limits T7 today and is the shared mechanism behind every `labelDominant`
uniform rescale in the corpus, so it generalizes. Routing to the architect per the boundary
rule; no `src/` edit made. Recommendation: per-band uniform factors keyed on the tier-rows
that actually overflow, leaving non-overflowing bands at scale 1.0.

## Legitimately dense, documented as-is

`hemocytometer_view` (trypan_blue_counting) carries a residual `unresolved_label_overlap`
between `right_hemocytometer_slide_clear` and the rear_right bottles. It stems from genuine
cross-zone OBJECT overlap in a dense-by-design scene (overlap_count 6), not a label nudge that
label_placement can resolve. Left as authored; flagged to the walker manager for a density
decision (gate-exempt like the other dense fixtures, or a separate density rework ticket).

## Tier-collapse pass results

Date: 2026-07-03. Follow-on pass using the new `tools/rank_scene_layout.py` inspection
helper, which ranks scenes on `collapsibility`, `coupling_loss`, `victim_fraction`,
`crowd_bound_count`, `zone_spread`, `mean_scale`, and the pedagogy axis
`target_prominence`, plus `label_dominant` / `tier_collapsible` routing flags.

Three sparse scenes with `crowd_bound_count == 0` and no `label_dominant` flag collapsed
cleanly from 2 tier-rows to 1, lifting the scene-wide uniform rescale factor to full size
(1.000) with no object shrunk and no overlap/overflow regression:

- `content/protocols/cell_culture/drug_dilution_setup/scenes/bench_setup.yaml`
  (0.604 -> 1.000)
- `content/protocols/cell_culture/mtt_solubilization_readout/scenes/bench_workspace.yaml`
  (0.653 -> 1.000; also removed the non-target inherited `center_water_bath` to clear a
  same-tier collision, mirroring the `bench_setup` precedent)
- `content/protocols/cell_culture/mtt_plate_reaction/scenes/incubator_workspace.yaml`
  (0.667 -> 1.000; incubator kept at full authored size)

A fourth candidate, the `content/base_scenes/electrophoresis_bench.yaml` base (7 SDS-PAGE
children plus extraction), was measured and rejected: it is label-dominant (uniform factor
0.584 is set by label vertical overflow, not tier-row overhead), so a tier collapse produced
zero factor gain and even reopened `unresolved_label_overlap` errors on a full collapse. The
edit was reverted net-zero and routed to the architect as label-space / engine work,
consistent with the existing architect finding above.

With these three wins landed and the electrophoresis base confirmed label-dominant, the
clean-collapse lever (`crowd_bound_count == 0`, not `label_dominant`, `tier_rows > 1`) is now
exhausted across the corpus: no scene currently reports `tier_collapsible == True`. Any
further factor gains require the per-band/per-zone uniform-rescale engine change described in
the architect finding above, not further scene-YAML tier restructuring.
