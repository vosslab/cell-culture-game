# Scene layout baseline (2026-07-03)

Pre-dispatch evidence for the "Scene layout pass - de-shrink the clusters + clear the three
overlaps" plan (`cheerful-whistling-kahn.md`, task T0). Read-only probe: no scene, object, base
scene, test, or engine file is edited by this task. This report is the only file this task
writes.

## Commands run

```bash
bash pipeline/build_generated.sh
node --import tsx pipeline/precompute_layout.mjs
source source_me.sh && python3 run_scene_health.py
```

Key output lines:

```text
Generated 56 SVG entries into generated/svg_manifest.ts
SCENE SUMMARY: 38 emitted, 1 skipped (missing-svg mode: placeholder).
  SKIPPED long_labels_smoke: validation error: Placement 'rear_dmf_bottle' references
  unknown object 'dmf_bottle' (pre-existing, unrelated dev fixture; not in plan scope)
Regenerated generated/ (object_library, svg_manifest, svg_placeholder_keys, scenes, protocols).

precompute_layout: emitted 38 scenes to generated/precomputed_layout.ts (viewport 1920x1080)

layout_metrics: 38 scene(s) -> test-results/layout_metrics
layout health report: 38 scenes analyzed
wrote: test-results/layout_health/health_report.md
wrote: test-results/layout_health/health_report.json
```

An additional read-only evidence tool, already checked into the repo
(`tests/e2e/e2e_layout_diagnostics_baseline.mjs`, "SIDE-QUEST evidence tool (throwaway, read-only
with respect to the engine)"), was also run to inspect the engine's `severityDiagnostics` stream
directly, because `run_scene_health.py`'s JSON does not surface the `unresolved_overlap` code at
all (see "Overlap-scene finding" below). It writes only its own designated output file
(`docs/active_plans/reports/layout_diagnostics_baseline.md`); no scene/object/base-scene/test/
engine file was edited.

```bash
node --import tsx tests/e2e/e2e_layout_diagnostics_baseline.mjs
```

## Full worst-first scorecard (as printed)

```text
Worst-first scorecard (rank. scene  severity  finding  [categories]):
 1. adversarial_overflow_smoke  sev=174.27  engine-fit  [high-empty-space-plus-shrink, shrink-stressed, crowded, label-stressed]
    verdict: engine leaves usable space (lower) while shrinking content toward the floor
    target:  objects shrink while the lower stays empty; widen the packed zone (zone_b) or spread objects into the lower empty band so the solver need not shrink
 2. seeding_workspace  sev=100.05  engine-fit  [high-empty-space-plus-shrink, shrink-stressed]
    verdict: engine leaves usable space (right) while shrinking content toward the floor
    borderline: label~stressed-edge
    target:  objects shrink while the right stays empty; widen the packed zone (rear_right) or spread objects into the right empty band so the solver need not shrink
 3. sdspage_destain_gel_rock_workspace  sev=90.88  engine-fit  [high-empty-space-plus-shrink, shrink-stressed]
    verdict: engine leaves usable space (right) while shrinking content toward the floor
    borderline: fill~sparse-edge, ler~room-edge
    target:  objects shrink while the right stays empty; widen the packed zone (center) or spread objects into the right empty band so the solver need not shrink
 4. staining_bench  sev=90.88  engine-fit  [high-empty-space-plus-shrink, shrink-stressed]
    verdict: engine leaves usable space (right) while shrinking content toward the floor
    borderline: fill~sparse-edge, ler~room-edge
    target:  objects shrink while the right stays empty; widen the packed zone (center) or spread objects into the right empty band so the solver need not shrink
 5. drug_dilution_setup_bench_setup  sev=85.53  engine-fit  [high-empty-space-plus-shrink, shrink-stressed]
    verdict: engine leaves usable space (center) while shrinking content toward the floor
    borderline: ler~room-edge, shrink~stressed-edge
    target:  objects shrink while the center stays empty; widen the packed zone (center) or spread objects into the center empty band so the solver need not shrink
 6. hood_basic  sev=81.79  engine-fit  [high-empty-space-plus-shrink, shrink-stressed]
    verdict: engine leaves usable space (center) while shrinking content toward the floor
    borderline: ler~room-edge, shrink~stressed-edge
    target:  objects shrink while the center stays empty; widen the packed zone (rear_right) or spread objects into the center empty band so the solver need not shrink
 7. passage_hood_detachment_hood_workspace  sev=60.34  authoring  [shrink-stressed]
    verdict: content is shrunk to fit with little spare room; likely too many objects for the zones
    borderline: fill~sparse-edge
    target:  too many objects for the zones; reduce count in zone center or add a zone row
 8. extraction_workspace  sev=56.31  authoring  [shrink-stressed, crowded, label-stressed]
    verdict: content is shrunk to fit with little spare room; likely too many objects for the zones
    borderline: fill~sparse-edge, ler~room-edge, label~stressed-edge
    target:  reduce object count or split zone rear_center across an added row
 9. electrophoresis_bench  sev=48.31  authoring  [shrink-stressed, label-stressed]
    verdict: content is shrunk to fit with little spare room; likely too many objects for the zones
    borderline: fill~sparse-edge, ler~room-edge, label~stressed-edge
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
10. sdspage_attach_lid_and_leads_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
11. sdspage_fill_tank_buffer_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
12. sdspage_load_sample_single_lane_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
13. sdspage_prepare_running_buffer_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
14. sdspage_recycle_buffer_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
15. sdspage_run_electrophoresis_workspace  sev=48.31  authoring  [shrink-stressed, label-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
16. plate_drug_treatment_media_adjustment_plate_workspace  sev=42.29  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone rear_center or add a zone row
17. hood_workspace  sev=41.08  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone rear_right or add a zone row
18. hemocytometer_view  sev=40.05  intentional  [crowded, label-stressed]
    target:  no change needed (intentional non-same-tier layering); confirm overlaps are by design
19. plate_workspace  sev=38.41  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone rear_right or add a zone row
20. bench_basic  sev=36.44  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone center or add a zone row
21. dilution_workspace  sev=33.73  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone rear_right or add a zone row
22. mtt_reagent_prep_bench_workspace  sev=33.23  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone center or add a zone row
23. centrifuge_workspace  sev=33.07  authoring  [shrink-stressed]
    target:  too many objects for the zones; reduce count in zone center or add a zone row
24. microscope_basic  sev=28.92  intentional  [crowded, label-stressed]
25. passage_hood_detachment_microscope_view  sev=28.41  intentional  [crowded, label-stressed]
26. incubator_workspace  sev=26.17  healthy  [healthy]
27. mtt_solubilization_readout_bench_workspace  sev=20.34  healthy  [healthy]
28. cell_counter_workspace  sev=12.91  healthy  [healthy]
29. sdspage_prepare_sample_mix_single_lane_workspace  sev=11.22  healthy  [healthy]
30. mtt_solubilization_readout_plate_reader_workspace  sev=8  healthy  [healthy]
31. cell_counter_basic  sev=2.86  healthy  [healthy]
32. heat_block_bench  sev=2.6  healthy  [healthy]
33. sample_prep_bench  sev=2.6  healthy  [healthy]
34. sdspage_heat_denature_samples_workspace  sev=2.6  healthy  [healthy]
35. imaging_bench  sev=0  healthy  [healthy]
36. missing_svg_check  sev=0  intentional  [sparse]
37. select_check  sev=0  intentional  [sparse]
38. type_check  sev=0  intentional  [sparse]
```

## Raw health_report.json

Full contents of `test-results/layout_health/health_report.json` as of this run (this directory
is gitignored, so this embedded copy is the durable record):

```json
{
  "bands": {
    "sample_size": 38,
    "fill": {
      "metric": "fill.fraction",
      "basis": "p25..p75 (target range)",
      "target_low": 0.028,
      "target_high": 0.1095,
      "min": 0.022,
      "median": 0.0662,
      "max": 0.4543,
      "note": "fill is low repo-wide; sparse = below p25, dense = above p75 (relative)"
    },
    "ler": {
      "metric": "largest_empty_rectangle.area_fraction",
      "basis": "p75 (elevated) / p90 (severe)",
      "elevated_edge": 0.2288,
      "severe_edge": 0.4091,
      "min": 0.1428,
      "median": 0.2024,
      "max": 0.7,
      "note": "a large empty rectangle means usable room exists in the scene"
    },
    "shrink": {
      "metric": "mean final_scale (PROXY)",
      "basis": "p50 (median readable scale)",
      "stressed_edge": 0.4656,
      "min": 0.2444,
      "median": 0.4656,
      "max": 1,
      "hard_floors": {
        "h_floor": 0.55,
        "v_floor": 0.27
      },
      "note": "shrink-stressed = mean final_scale at or below the median, OR uniform rescale at floor, OR a majority of objects at the packer floor (all PROXY)"
    },
    "label": {
      "metric": "overlap_graph.label_conflict_count",
      "basis": "p90 (auxiliary, not one of the three required bands)",
      "stressed_edge": 2,
      "max": 24,
      "note": "label-conflict distribution is degenerate (mostly zero); edge applied with a margin"
    }
  },
  "categoryCounts": {
    "high-empty-space-plus-shrink": 6,
    "shrink-stressed": 22,
    "crowded": 5,
    "label-stressed": 12,
    "healthy": 10,
    "sparse": 3
  },
  "findingCounts": {
    "engine-fit": 6,
    "authoring": 16,
    "intentional": 6,
    "healthy": 10
  }
}
```

The `diagnoses` array (38 entries, one per scene) is reproduced in full in the worst-first
scorecard above (every field: `categories`, `borderline`, `finding`, `verdict`, `evidence`,
`suggestion`, `severity`); it is not duplicated a second time here to keep this report scannable.
The six scenes named in the Wave-0 mandate are pulled out explicitly below with their complete
`evidence` arrays.

## The 3 healthy bench_basic children (starting metrics, must stay healthy)

| Scene | Severity | Finding | Mean final_scale | Min final_scale | Object count | Uniform rescale factor |
| --- | --- | --- | --- | --- | --- | --- |
| `mtt_solubilization_readout_bench_workspace` | 20.34 | healthy | 0.661 | 0.661 | 8 | 0.661 |
| `mtt_solubilization_readout_plate_reader_workspace` | 8 | healthy | 0.8667 | 0.8667 | 7 | 0.8667 |
| `incubator_workspace` | 26.17 | healthy | 0.5638 | 0.5638 | 9 | 0.5638 |

All three currently pass the Exit metric already (`mean final_scale >= 0.50`, no
`post_rescale_overflow`, no live overlap). T4 (`bench_basic` base edit) is the only Wave-1 task
with regression risk to these three; the base-edit blast radius section of the plan already
flags this. This baseline is the pre-edit reference T-INT diffs against.

## The 3 named "overlap" scenes: starting state (REVISED from the plan text)

The plan's Context section states all three of `seeding_workspace`, `hood_workspace`, and
`imaging_bench` currently carry a live `unresolved_overlap` Error. Live evidence from this run
does not support that for two of the three. Findings:

`run_scene_health.py`'s JSON has no `unresolved_overlap` field at all. Its `overlap_graph`
(built by `tools/layout_metrics.mjs`) is a POST-LAYOUT AABB collision check on rendered boxes;
`unresolved_overlap` is a SEPARATE engine-level diagnostic code emitted by the packer
(`src/scene_runtime/layout/strategies/pack_strategy.ts`) into `result.severityDiagnostics` only
when a zone's row-fit computation cannot satisfy even the `MIN_SCALE` (0.55) floor. Neither
stream is wired into `run_scene_health.py`'s output (that wiring is explicitly owned by the
sibling walker plan's D6 item, not this plan). To read the live `unresolved_overlap` state, this
task ran the existing `tests/e2e/e2e_layout_diagnostics_baseline.mjs` tool, which calls
`runPipeline` directly and reports `result.severityDiagnostics` by code.

| Scene | `overlap_graph.overlap_count` (AABB) | `severityDiagnostics` `unresolved_overlap` count | Converged? |
| --- | --- | --- | --- |
| `seeding_workspace` | 0 | 0 | YES (2 passes) |
| `hood_workspace` | 0 | 0 | YES (1 pass, 0 diagnostics -- fully clean) |
| `imaging_bench` | 0 | 1 (`left_tool_area`, `left_rocking_shaker`, depth 1) | NO (`max_iterations_reached`, `zone_overflow_negative_gap`) |

Only `imaging_bench` currently has a live `unresolved_overlap` Error. `seeding_workspace` and
`hood_workspace` show zero live overlap Errors of either kind today.

Root cause of the discrepancy, confirmed by reading the two child scene YAML files directly:
both `content/protocols/cell_culture/cell_seeding_plate_setup/scenes/seeding_workspace.yaml` and
`content/protocols/cell_culture/passage_pellet_reseed/scenes/hood_workspace.yaml` carry explicit
author comments stating the base `rear_right` bottles (`base_rear_right_media`,
`base_rear_right_sterile_water`) and a `right_tool_area` pipette were REMOVED (not resized or
retiered) specifically because they collided with the oversized incubator once it was added.
Quoting `seeding_workspace.yaml`: "Remove base rear-right bottles to make room for the
incubator... This were previously only deactivated, which left them rendered and crowding the
center band; removing them frees the space the incubator needs" and "[the aspirating pipette's]
right_tool_area slot sat under the large incubator and overlapped it; remove it to declutter the
right tool band." The overlap was already worked around by DELETING the competing placements,
not by resizing the incubator asset or widening the zone. That workaround is exactly why
`rear_right` now holds only a single item (the incubator alone) in both scenes: the packer's
per-zone row-fit check (`compact()` in `pack_strategy.ts`) essentially always succeeds for a
lone item, so no `unresolved_overlap` fires today.

Practical implication for the Exit metric: the `unresolved_overlap == 0` line item for
`seeding_workspace` and `hood_workspace` is ALREADY satisfied, before any Wave-1/Wave-2 edit. The
correctness milestone's "3 overlaps cleared" framing should be read as 1 live overlap
(`imaging_bench`) to clear, plus 2 scenes (`seeding_workspace`, `hood_workspace`) that must simply
not have a new one reintroduced while the shrink is fixed (a real risk: T11/T8 must not
re-populate `rear_right`/`right_tool_area` with the previously-removed items unless the
incubator is shrunk or the zone widened enough to hold everyone; re-adding without either would
resurrect a live overlap that is not there today).

`imaging_bench` also did NOT converge (`max_iterations_reached=1`,
`zone_overflow_negative_gap=1`) even though `run_scene_health.py` labels it "healthy" (severity 0,
mean final_scale 1). The health report's shrink-proxy metrics are blind to this convergence
failure because `imaging_bench`'s overall fill/shrink numbers look fine; only the engine-level
`severityDiagnostics` stream shows the packer gave up on `left_tool_area` specifically. This is a
narrow, single-zone problem (`left_rocking_shaker`, `display_width_cm=28`, alone in a 16-scene-
percent-wide `left_tool_area` zone -- the packer cannot shrink it to fit even at `MIN_SCALE=0.55`),
not a scene-wide issue, and matches T-IMG's planned scope exactly ("retier or reposition onto a
clear tab-stop"). Flag for T-IMG: this is a real, live, non-converging Error, not a cosmetic
label conflict -- verify with `tests/e2e/e2e_layout_diagnostics_baseline.mjs` (not just
`run_scene_health.py`) after the fix, since the health-report proxy alone would not have caught
it going in and would not necessarily catch a regression either.

## Incubator root-cause probe

Files read: `content/objects/equipment/incubator.yaml`, `content/base_scenes/hood_basic.yaml`,
`content/protocols/cell_culture/cell_seeding_plate_setup/scenes/seeding_workspace.yaml`, plus
`content/protocols/cell_culture/passage_pellet_reseed/scenes/hood_workspace.yaml` for a
cross-check (the other hood-family child that also adds the incubator).

- `incubator.yaml`: `layout.display_width_cm: 55`, `default_width: 22`, `label_width: 14`.
- `hood_basic.yaml`'s own `placements` list carries NO incubator; the base `rear_right` zone
  (`left:67, right:95, top:5, bottom:36`, 28 scene-percent wide) holds only `media_bottle` and
  `sterile_water_bottle`. The incubator is added ONLY by `add_placements` in the two child
  scenes, always into `rear_right`, always paired with `remove_placements` deleting the two base
  bottles plus a `right_tool_area` pipette.
- Both children's own comments state the mechanism directly: "The oversized incubator art covers
  the entire right_tool_area X-range, so the hood tools live in the center and rear_center bands
  instead" (`seeding_workspace.yaml`) and "It is large equipment whose rendered height spans most
  of the scene, so it claims the entire right side... any tool placed there would sit under the
  incubator" (`hood_workspace.yaml`, pellet_reseed).

Verdict on premise (a) -- CONFIRMED for the shrink half, REVISED for the overlap half:

- CONFIRMED: the incubator's 55cm width is the direct, author-documented cause of the tool
  evacuation into `center`. `seeding_workspace` evacuates 3 items (`right_aspirating_pipette` plus
  the loss of the two rear_right bottles displaces `rear_center_media_bottle` there too) into
  `center`, which now stacks 3 depth tiers across 6-7 items in a single 38-scene-percent-tall
  zone; this is the dominant driver of `seeding_workspace`'s severity-100.05, mean-final-scale-
  0.2887 shrink (worst-ranked scene in the corpus). `hood_workspace` (pellet_reseed) shows the
  identical, smaller-scale pattern (2 evacuated items, sev 41.08, mean final_scale 0.3153).
- REVISED: the incubator does NOT currently drive a live `rear_right` `unresolved_overlap` Error
  in either child (see previous section) -- that collision was already resolved by removing the
  competing placements outright, not by resizing the incubator or widening the zone. So "resizing
  the incubator... likely clears both the overlap and much of the seeding shrink in one edit" is
  only half accurate today: there is no live overlap left to clear, and a resize alone will help
  the shrink only modestly (see size comparison below), not by itself.
- Sibling equipment size check (evidence for whether resizing the incubator stays "comparable to
  sibling equipment objects" per the plan's own recognizability bar): `display_width_cm` across
  the equipment library -- `incubator` 55, `water_bath` 55, `centrifuge` 51, `hood_surface` 50,
  `plate_reader` 50, `cell_counter` 38, `electrophoresis_tank` 35, `microscope` 35, `microwave`
  35, `power_supply` 22. The incubator's 55cm is not an outlier; it ties `water_bath` and sits
  only ~8% above `centrifuge`. A resize large enough to free meaningful `rear_right` width (say,
  down toward 45-48cm) would still be within the realistic benchtop-incubator range and close to
  sibling scale, but a resize alone is unlikely to free enough width to re-admit the 2-3 evacuated
  items back into `rear_right`/`right_tool_area`; the zone is only 28 scene-percent wide and
  `right_tool_area` (`70-97`, hood_basic) overlaps the incubator's rendered X-range at any width
  above roughly 45-50cm equivalent, per the children's own "covers the entire right_tool_area
  X-range" comment.

Recommendation (does not change Wave-1 T2's scope, confirms it): treat the incubator resize as
a complementary edit, not the sole lever. T2 (`hood_basic.yaml`) already scopes BOTH "decrowd the
stacked center, open a second band, AND widen `rear_right`" -- that combination, not the incubator
resize alone, is what actually relieves the shrink. A modest incubator resize (within the
sibling-equipment range above) is worth pairing with the zone widening so evacuated items have
somewhere to return to, but it is not on its own sufficient and should not be billed as clearing
an overlap that is not currently live.

## Feasibility of the 0.50 floor: extraction_workspace and staining_bench

Read `mean final_scale >= 0.50` together with the plan's stricter, primary Exit-metric line:
"no terminal uniform vertical rescale applied (`uniform_rescale` factor is null)". The packer's
own per-row floor is `MIN_SCALE = 0.55` (`src/scene_runtime/layout/constants.ts`); the SEPARATE,
last-resort whole-scene uniform rescale (`UNIFORM_RESCALE_MIN_SCALE = 0.27`) only engages when
per-row packing at `MIN_SCALE` still cannot fit the vertical content into the scene's fixed
`scene_bounds`. Both scenes below currently show `uniform_rescale.applied: true` -- the last-
resort pass is live for both today, which is why every object in each scene reports an identical
`final_scale` (the packer-floor-then-uniform-rescale collapses to one shared number). The real
target is eliminating that last-resort pass entirely: once it does not trigger, per-row scales
bottom out at 0.55 (above the 0.50 floor) by construction, so "no uniform rescale" and "mean
final_scale >= 0.50" become the same practical target.

### extraction_workspace (17 objects)

- `content/protocols/sdspage/sdspage_extract_gel_from_cassette/scenes/extraction_workspace.yaml`
  extends `electrophoresis_bench` and adds exactly one placement
  (`front_center_staining_tray`, `object_name: staining_tray`, zone `front_left`, depth_tier 1).
  All 17 objects and the crowding come from the base `electrophoresis_bench.yaml`, which is
  Wave-1 T1's target, not a per-child problem.
- Current metrics: fill 0.0303 (3.03%, extremely sparse), `largest_empty_rectangle` 21.6% at
  lower-right, `uniform_rescale` factor 0.2948 (`label_dominant: true`), all 17 objects at
  identical `final_scale` 0.2948 and `at_h_floor: true`.
- `electrophoresis_bench.yaml`'s `center` zone (`top:38, bottom:76`, 38 scene-percent tall) stacks
  7 of the 17 objects across 3 depth tiers. Reading
  `src/scene_runtime/layout/vertical_layout.ts` (`applyUniformRescale`): the uniform rescale
  shrinks only the SCALABLE object-height portion; the label strip, `labelGap`, `zonePad`, and
  `tierGap` per row are FIXED overhead that does not shrink. With 3 stacked rows in one zone, the
  fixed per-row overhead accumulates and, per the current low scale, appears to already consume
  most of the zone's height budget -- exactly the mechanism the plan's own fix ("split center into
  a mid row" / "add a front_center zone") targets: reducing simultaneous depth-tier count per
  zone directly reduces total fixed overhead and should let the scalable object-height component
  (hence the achievable uniform scale) grow substantially.
- A secondary, smaller issue: `front_center_staining_tray` (zone `front_left`, but
  positionally under `center`'s bottom edge) cross-zone-overlaps `center_serological_pipette` at
  depth 0.422 (the `center` zone's `bottom:76` and `front_left`'s `top:72` bands overlap by 4
  scene-percent). This is a real but small `overlap_count: 1` already present; worth a one-line
  fix note for whichever Wave-2 task (T5) repositions this placement, but it is not the shrink
  driver.
- Feasibility verdict: FEASIBLE, no per-scene floor recorded. The scene is extremely sparse
  (3% fill, 21.6% largest empty rectangle) and the shrink is fixed-overhead/row-count driven, not
  area-driven; redistributing the `center` zone's 7-item, 3-tier stack into an added row/zone (T1)
  plus repositioning the added `staining_tray` clear of the cross-zone graze (T5) has ample empty
  canvas to work with and, per the engine's own uniform-rescale mechanism, should let the
  last-resort pass stop triggering without removing any of the 17 objects. This is a directional
  assessment from reading the metrics and the engine's rescale code, not a simulated post-edit
  number; T1/T5 owners should re-run `run_scene_health.py extraction_workspace` after their edit
  to confirm, and only fall back to a documented floor if that confirmation genuinely fails with
  every targeted object still present.

### staining_bench (3 tall objects, 9 total)

- `content/base_scenes/staining_bench.yaml`: `center` zone (`top:38, bottom:94`, 56 scene-percent
  tall) holds exactly 3 items, one per depth tier: `center_staining_tray` (tier 1, `align_stop:
  left`), `center_microwave` (tier 2, `align_stop: center`), `center_rocking_shaker` (tier 3,
  `align_stop: right`). `display_width_cm`: `staining_tray` 22, `microwave` 35, `rocking_shaker`
  28 -- each occupies its own full row.
- Current metrics: fill 0.0255 (2.55%, the sparsest engine-fit scene in the corpus),
  `largest_empty_rectangle` 22.9% at right (matches: `right_tool_area` holds only 1 item and
  is nearly empty), `uniform_rescale` factor 0.3187 (`label_dominant: true`), all 9 objects at
  identical `final_scale` 0.3187.
- Same mechanism as `extraction_workspace`: 3 stacked depth-tier rows of large, "tall" equipment
  in one zone accumulate fixed per-row overhead (label strip + gaps) that the uniform rescale
  cannot shrink away, forcing the whole-scene floor pass.
- Feasibility verdict: FEASIBLE, no per-scene floor recorded. This is the sparsest engine-fit
  scene measured (2.55% fill) with a large, nearly-empty `right_tool_area` (holds only
  `right_micropipette`) immediately available. Wave-1 T3's proposed fix (move `rocking_shaker`
  into the widened `right_tool_area`, or add a front band) reduces `center` from 3 stacked rows to
  2, which by the same fixed-overhead argument above should raise the achievable scale well past
  0.50 without removing `staining_tray`, `microwave`, or `rocking_shaker`. As with
  `extraction_workspace`, this is a directional, evidence-based call, not a simulated result; T3
  should re-run `run_scene_health.py staining_bench` (and check the no-op overlay
  `sdspage_destain_gel_rock_workspace`, byte-identical metrics today) after its edit.

Neither scene required a documented per-scene floor. If a Wave-1 owner's actual edit still cannot
clear the last-resort uniform rescale while keeping every protocol-targeted object present, they
should record a per-scene floor at that point (the highest scale reached with all objects present)
rather than remove an object to force 0.50.

## Summary of verdicts for the handoff

- INCUBATOR: premise (a) CONFIRMED for the shrink mechanism (author-documented,
  reproducible across both hood-family children that add the incubator); REVISED for the overlap
  mechanism (no live `unresolved_overlap` today in `seeding_workspace` or `hood_workspace` -- it
  was pre-empted by removing placements, not by resizing/retiering). Wave-1 T2's existing scope
  (decrowd center AND widen `rear_right`) already matches the needed combined fix; no change to
  that task's brief is required, but T8/T11 owners should not treat "clear the overlap" as
  separate, already-done work, and must not reintroduce a live overlap by re-adding evacuated
  items without first widening the zone or shrinking the incubator enough to fit them.
- FEASIBILITY: both `extraction_workspace` and `staining_bench` are assessed FEASIBLE for the
  standard 0.50 floor (equivalently, eliminating the last-resort uniform rescale) without removing
  any protocol-targeted object. No per-scene floor is recorded for either scene at this time.
- CONCERN for Wave-1/Wave-2 briefs: `imaging_bench` is healthy by the `run_scene_health.py` proxy
  but does NOT converge in the engine's own pipeline run (`max_iterations_reached`). T-IMG should
  verify with `tests/e2e/e2e_layout_diagnostics_baseline.mjs`, not `run_scene_health.py` alone,
  both before and after its fix.
- CORRECTNESS MILESTONE reframing: of the "3 overlaps to clear," only `imaging_bench` has one
  live today. `seeding_workspace` and `hood_workspace` already read `unresolved_overlap == 0`; the
  milestone for those two is "stays at 0" (a non-regression requirement during the shrink fix),
  not "clear from Error."
