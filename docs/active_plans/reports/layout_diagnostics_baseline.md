# Layout diagnostics baseline

Current-state record of which scenes emit which layout diagnostics when `runPipeline` runs over every generated scene at a canonical 16:9 viewport (1920x1080). This is a read-only evidence snapshot taken before any layout-engine changes, so later improvements are measurable.

- Generated: 2026-07-25 00:28 UTC
- Scenes scanned: 40
- Viewport: 1920x1080 (16:9)
- Source: `tests/e2e/e2e_layout_diagnostics_baseline.mjs` over `generated/scenes.ts`

## Worst scenes by diagnostics

| Rank | Scene | Score | Diagnostics |
| --- | --- | --- | --- |
| 1 | `electrophoresis_bench` | 160 | item_escapes_zone_vertically=16 |
| 2 | `sdspage_prepare_running_buffer_workspace` | 160 | item_escapes_zone_vertically=16 |
| 3 | `imaging_bench` | 121 | item_escapes_zone_vertically=12, label_row_staggered=1 |
| 4 | `heat_block_bench` | 120 | item_escapes_zone_vertically=12 |
| 5 | `sample_prep_bench` | 110 | item_escapes_zone_vertically=11 |
| 6 | `staining_bench` | 100 | item_escapes_zone_vertically=10 |
| 7 | `bench_basic` | 90 | item_escapes_zone_vertically=9 |
| 8 | `centrifuge_workspace` | 90 | item_escapes_zone_vertically=9 |
| 9 | `cell_counter_workspace` | 80 | item_escapes_zone_vertically=8 |
| 10 | `dilution_workspace` | 80 | item_escapes_zone_vertically=8 |
| 11 | `cell_counter_basic` | 70 | item_escapes_zone_vertically=7 |
| 12 | `drug_dilution_setup_bench_setup` | 70 | item_escapes_zone_vertically=7 |
| 13 | `hemocytometer_view` | 70 | item_escapes_zone_vertically=7 |
| 14 | `mtt_reagent_prep_bench_workspace` | 70 | item_escapes_zone_vertically=7 |
| 15 | `sdspage_load_sample_single_lane_workspace` | 70 | item_escapes_zone_vertically=7 |
| 16 | `seeding_workspace` | 70 | item_escapes_zone_vertically=7 |
| 17 | `extraction_workspace` | 60 | item_escapes_zone_vertically=6 |
| 18 | `sdspage_destain_gel_setup_workspace` | 60 | item_escapes_zone_vertically=6 |
| 19 | `sdspage_stain_gel_workspace` | 60 | item_escapes_zone_vertically=6 |
| 20 | `hood_basic` | 50 | item_escapes_zone_vertically=5 |
| 21 | `incubator_workspace` | 50 | item_escapes_zone_vertically=5 |
| 22 | `microscope_basic` | 50 | item_escapes_zone_vertically=5 |
| 23 | `passage_hood_detachment_hood_workspace` | 50 | item_escapes_zone_vertically=5 |
| 24 | `sdspage_prepare_sample_mix_single_lane_workspace` | 50 | item_escapes_zone_vertically=5 |
| 25 | `hood_workspace` | 40 | item_escapes_zone_vertically=4 |
| 26 | `plate_workspace` | 40 | item_escapes_zone_vertically=4 |
| 27 | `sdspage_fill_tank_buffer_workspace` | 40 | item_escapes_zone_vertically=4 |
| 28 | `sdspage_image_gel_workspace` | 40 | item_escapes_zone_vertically=4 |
| 29 | `sdspage_load_protein_ladder_workspace` | 40 | item_escapes_zone_vertically=4 |
| 30 | `mtt_solubilization_readout_bench_workspace` | 30 | item_escapes_zone_vertically=3 |
| 31 | `passage_hood_detachment_microscope_view` | 30 | item_escapes_zone_vertically=3 |
| 32 | `sdspage_attach_lid_and_leads_workspace` | 30 | item_escapes_zone_vertically=3 |
| 33 | `sdspage_recycle_buffer_workspace` | 30 | item_escapes_zone_vertically=3 |
| 34 | `sdspage_run_electrophoresis_workspace` | 30 | item_escapes_zone_vertically=3 |
| 35 | `mtt_solubilization_readout_plate_reader_workspace` | 20 | item_escapes_zone_vertically=2 |
| 36 | `sdspage_destain_gel_rock_workspace` | 20 | item_escapes_zone_vertically=2 |

Score weights hard structural failures (`max_iterations_reached`=100, overflow/tab-stop/vertical-escape=10, clamp=5, identity=8) above label residuals (`label_collision_residual`=3, `label_row_staggered`=1); any other kind weighs 2.

## Per-scene diagnostics

| Scene | Passes | Converged | Total | item_escapes_zone_vertically | label_row_staggered |
| --- | --- | --- | --- | --- | --- |
| `bench_basic` | 1 | YES | 9 | 9 | . |
| `cell_counter_basic` | 1 | YES | 7 | 7 | . |
| `cell_counter_workspace` | 1 | YES | 8 | 8 | . |
| `centrifuge_workspace` | 1 | YES | 9 | 9 | . |
| `dilution_workspace` | 1 | YES | 8 | 8 | . |
| `drug_dilution_setup_bench_setup` | 1 | YES | 7 | 7 | . |
| `electrophoresis_bench` | 1 | YES | 16 | 16 | . |
| `extraction_workspace` | 1 | YES | 6 | 6 | . |
| `heat_block_bench` | 1 | YES | 12 | 12 | . |
| `hemocytometer_view` | 1 | YES | 7 | 7 | . |
| `hood_basic` | 1 | YES | 5 | 5 | . |
| `hood_workspace` | 1 | YES | 4 | 4 | . |
| `imaging_bench` | 1 | YES | 13 | 12 | 1 |
| `incubator_workspace` | 1 | YES | 5 | 5 | . |
| `microscope_basic` | 1 | YES | 5 | 5 | . |
| `mtt_reagent_prep_bench_workspace` | 1 | YES | 7 | 7 | . |
| `mtt_solubilization_readout_bench_workspace` | 1 | YES | 3 | 3 | . |
| `mtt_solubilization_readout_plate_reader_workspace` | 1 | YES | 2 | 2 | . |
| `passage_hood_detachment_hood_workspace` | 1 | YES | 5 | 5 | . |
| `passage_hood_detachment_microscope_view` | 1 | YES | 3 | 3 | . |
| `plate_drug_treatment_media_adjustment_plate_workspace` | 1 | YES | 0 | . | . |
| `plate_focus_bench` | 1 | YES | 0 | . | . |
| `plate_focus_hood` | 1 | YES | 0 | . | . |
| `plate_workspace` | 1 | YES | 4 | 4 | . |
| `sample_prep_bench` | 1 | YES | 11 | 11 | . |
| `sdspage_attach_lid_and_leads_workspace` | 1 | YES | 3 | 3 | . |
| `sdspage_destain_gel_rock_workspace` | 1 | YES | 2 | 2 | . |
| `sdspage_destain_gel_setup_workspace` | 1 | YES | 6 | 6 | . |
| `sdspage_fill_tank_buffer_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_heat_denature_samples_workspace` | 1 | YES | 0 | . | . |
| `sdspage_image_gel_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_load_protein_ladder_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_load_sample_single_lane_workspace` | 1 | YES | 7 | 7 | . |
| `sdspage_prepare_running_buffer_workspace` | 1 | YES | 16 | 16 | . |
| `sdspage_prepare_sample_mix_single_lane_workspace` | 1 | YES | 5 | 5 | . |
| `sdspage_recycle_buffer_workspace` | 1 | YES | 3 | 3 | . |
| `sdspage_run_electrophoresis_workspace` | 1 | YES | 3 | 3 | . |
| `sdspage_stain_gel_workspace` | 1 | YES | 6 | 6 | . |
| `seeding_workspace` | 1 | YES | 7 | 7 | . |
| `staining_bench` | 1 | YES | 10 | 10 | . |

## Severity-graded de-overlap diagnostics

Counts from `result.severityDiagnostics` (keyed by `code`), the de-overlap Error/Warning/Review stream. `unresolved_label_overlap` is the overlap-gate metric. `unresolved_overlap` is a bounds Error (object too big for its zone), not a label issue. A `.` means the code did not fire for that scene.

| Scene | unfittable_asset |
| --- | --- |
| `bench_basic` | . |
| `cell_counter_basic` | . |
| `cell_counter_workspace` | . |
| `centrifuge_workspace` | . |
| `dilution_workspace` | . |
| `drug_dilution_setup_bench_setup` | . |
| `electrophoresis_bench` | . |
| `extraction_workspace` | . |
| `heat_block_bench` | . |
| `hemocytometer_view` | 9 |
| `hood_basic` | . |
| `hood_workspace` | 8 |
| `imaging_bench` | . |
| `incubator_workspace` | . |
| `microscope_basic` | 7 |
| `mtt_reagent_prep_bench_workspace` | . |
| `mtt_solubilization_readout_bench_workspace` | . |
| `mtt_solubilization_readout_plate_reader_workspace` | . |
| `passage_hood_detachment_hood_workspace` | 9 |
| `passage_hood_detachment_microscope_view` | 6 |
| `plate_drug_treatment_media_adjustment_plate_workspace` | 3 |
| `plate_focus_bench` | . |
| `plate_focus_hood` | . |
| `plate_workspace` | 5 |
| `sample_prep_bench` | . |
| `sdspage_attach_lid_and_leads_workspace` | . |
| `sdspage_destain_gel_rock_workspace` | . |
| `sdspage_destain_gel_setup_workspace` | . |
| `sdspage_fill_tank_buffer_workspace` | . |
| `sdspage_heat_denature_samples_workspace` | . |
| `sdspage_image_gel_workspace` | . |
| `sdspage_load_protein_ladder_workspace` | . |
| `sdspage_load_sample_single_lane_workspace` | . |
| `sdspage_prepare_running_buffer_workspace` | . |
| `sdspage_prepare_sample_mix_single_lane_workspace` | . |
| `sdspage_recycle_buffer_workspace` | . |
| `sdspage_run_electrophoresis_workspace` | . |
| `sdspage_stain_gel_workspace` | . |
| `seeding_workspace` | 8 |
| `staining_bench` | . |

## Overlap pairs

Each row is one overlap Error from `result.severityDiagnostics`, naming the two involved placements, the zone, the diagnostic code, and the remaining penetration depth (scene-percent). `unresolved_label_overlap` is a label sitting over another label or artwork; `unresolved_overlap` is an object escaping its zone bounds. Same-zone pairs are in-zone collisions; differing zone membership for the two names indicates a cross-zone graze.

None. No overlap Error fired in any scene.

## Scenes that failed to run

None. Every scene ran to completion.
