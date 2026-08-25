# Layout diagnostics baseline

Current-state record of which scenes emit which layout diagnostics when `runPipeline` runs over every generated scene at a canonical 16:9 viewport (1920x1080). This is a read-only evidence snapshot taken before any layout-engine changes, so later improvements are measurable.

- Generated: 2026-08-24 21:48 UTC
- Scenes scanned: 57
- Viewport: 1920x1080 (16:9)
- Source: `tests/e2e/e2e_layout_diagnostics_baseline.mjs` over `generated/scenes.ts`

## Worst scenes by diagnostics

| Rank | Scene | Score | Diagnostics |
| --- | --- | --- | --- |
| 1 | `electrophoresis_bench` | 160 | item_escapes_zone_vertically=16 |
| 2 | `imaging_bench` | 111 | item_escapes_zone_vertically=11, label_row_staggered=1 |
| 3 | `heat_block_bench` | 110 | item_escapes_zone_vertically=11 |
| 4 | `drug_dilution_setup_bench_setup` | 101 | item_escapes_zone_vertically=10, label_row_staggered=1 |
| 5 | `centrifuge_workspace` | 100 | item_escapes_zone_vertically=10 |
| 6 | `passage_hood_detachment_hood_workspace` | 100 | item_escapes_zone_vertically=10 |
| 7 | `staining_bench` | 100 | item_escapes_zone_vertically=10 |
| 8 | `sample_prep_bench` | 91 | item_escapes_zone_vertically=9, label_row_staggered=1 |
| 9 | `bench_basic` | 90 | item_escapes_zone_vertically=9 |
| 10 | `cell_counter_workspace` | 90 | item_escapes_zone_vertically=9 |
| 11 | `sdspage_run_electrophoresis_workspace` | 90 | item_escapes_zone_vertically=9 |
| 12 | `dilution_workspace` | 80 | item_escapes_zone_vertically=8 |
| 13 | `extraction_workspace` | 80 | item_escapes_zone_vertically=8 |
| 14 | `sdspage_run_electrophoresis_endpoint_review` | 80 | item_escapes_zone_vertically=8 |
| 15 | `sdspage_load_protein_ladder_workspace` | 71 | item_escapes_zone_vertically=7, label_row_staggered=1 |
| 16 | `cell_counter_basic` | 70 | item_escapes_zone_vertically=7 |
| 17 | `hemocytometer_view` | 60 | item_escapes_zone_vertically=6 |
| 18 | `sdspage_destain_gel_setup_workspace` | 60 | item_escapes_zone_vertically=6 |
| 19 | `sdspage_prepare_sample_mix_single_lane_workspace` | 60 | item_escapes_zone_vertically=6 |
| 20 | `sdspage_stain_gel_workspace` | 60 | item_escapes_zone_vertically=6 |
| 21 | `hood_basic` | 50 | item_escapes_zone_vertically=5 |
| 22 | `hood_workspace` | 50 | item_escapes_zone_vertically=5 |
| 23 | `incubator_workspace` | 50 | item_escapes_zone_vertically=5 |
| 24 | `microscope_basic` | 50 | item_escapes_zone_vertically=5 |
| 25 | `mtt_reagent_prep_bench_workspace` | 50 | item_escapes_zone_vertically=5 |
| 26 | `plate_drug_treatment_media_adjustment_plate_workspace` | 50 | item_escapes_zone_vertically=5 |
| 27 | `sdspage_fill_tank_buffer_workspace` | 50 | item_escapes_zone_vertically=5 |
| 28 | `sdspage_image_gel_result_review` | 50 | item_escapes_zone_vertically=5 |
| 29 | `sdspage_load_sample_single_lane_workspace` | 50 | item_escapes_zone_vertically=5 |
| 30 | `sdspage_load_samples_batch_workspace` | 50 | item_escapes_zone_vertically=5 |
| 31 | `sdspage_recycle_buffer_workspace` | 50 | item_escapes_zone_vertically=5 |
| 32 | `viability_review` | 50 | item_escapes_zone_vertically=5 |
| 33 | `dilution_calculation_200` | 40 | item_escapes_zone_vertically=4 |
| 34 | `dilution_calculation_50` | 40 | item_escapes_zone_vertically=4 |
| 35 | `dilution_calculation_500` | 40 | item_escapes_zone_vertically=4 |
| 36 | `dilution_calculation_60` | 40 | item_escapes_zone_vertically=4 |
| 37 | `sdspage_assemble_electrode_module_workspace` | 40 | item_escapes_zone_vertically=4 |
| 38 | `sdspage_attach_lid_and_leads_workspace` | 40 | item_escapes_zone_vertically=4 |
| 39 | `sdspage_image_gel_workspace` | 40 | item_escapes_zone_vertically=4 |
| 40 | `sdspage_prepare_sample_mix_batch_workspace` | 40 | item_escapes_zone_vertically=4 |
| 41 | `dilution_volume_review` | 30 | item_escapes_zone_vertically=3 |
| 42 | `mtt_solubilization_readout_bench_workspace` | 30 | item_escapes_zone_vertically=3 |
| 43 | `mtt_solubilization_readout_result_review` | 30 | item_escapes_zone_vertically=3 |
| 44 | `passage_hood_detachment_microscope_view` | 30 | item_escapes_zone_vertically=3 |
| 45 | `plate_workspace` | 30 | item_escapes_zone_vertically=3 |
| 46 | `sdspage_prepare_gel_cassette_workspace` | 30 | item_escapes_zone_vertically=3 |
| 47 | `hemocytometer_count_review` | 20 | item_escapes_zone_vertically=2 |
| 48 | `sdspage_destain_gel_rock_workspace` | 20 | item_escapes_zone_vertically=2 |

Score weights hard structural failures (`max_iterations_reached`=100, overflow/tab-stop/vertical-escape=10, clamp=5, identity=8) above label residuals (`label_collision_residual`=3, `label_row_staggered`=1); any other kind weighs 2.

## Per-scene diagnostics

| Scene | Passes | Converged | Total | item_escapes_zone_vertically | label_row_staggered |
| --- | --- | --- | --- | --- | --- |
| `bench_basic` | 1 | YES | 9 | 9 | . |
| `cell_counter_basic` | 1 | YES | 7 | 7 | . |
| `cell_counter_workspace` | 1 | YES | 9 | 9 | . |
| `centrifuge_workspace` | 1 | YES | 10 | 10 | . |
| `dilution_calculation_200` | 1 | YES | 4 | 4 | . |
| `dilution_calculation_50` | 1 | YES | 4 | 4 | . |
| `dilution_calculation_500` | 1 | YES | 4 | 4 | . |
| `dilution_calculation_60` | 1 | YES | 4 | 4 | . |
| `dilution_initial_calculation_review` | 1 | YES | 0 | . | . |
| `dilution_volume_review` | 1 | YES | 3 | 3 | . |
| `dilution_workspace` | 1 | YES | 8 | 8 | . |
| `drug_dilution_setup_bench_setup` | 1 | YES | 11 | 10 | 1 |
| `electrophoresis_bench` | 1 | YES | 16 | 16 | . |
| `extraction_workspace` | 1 | YES | 8 | 8 | . |
| `heat_block_bench` | 1 | YES | 11 | 11 | . |
| `hemocytometer_count_review` | 1 | YES | 2 | 2 | . |
| `hemocytometer_view` | 1 | YES | 6 | 6 | . |
| `hood_basic` | 1 | YES | 5 | 5 | . |
| `hood_workspace` | 1 | YES | 5 | 5 | . |
| `imaging_bench` | 1 | YES | 12 | 11 | 1 |
| `incubator_workspace` | 1 | YES | 5 | 5 | . |
| `microscope_basic` | 1 | YES | 5 | 5 | . |
| `mtt_reagent_prep_bench_workspace` | 1 | YES | 5 | 5 | . |
| `mtt_solubilization_readout_bench_workspace` | 1 | YES | 3 | 3 | . |
| `mtt_solubilization_readout_plate_reader_workspace` | 1 | YES | 0 | . | . |
| `mtt_solubilization_readout_result_review` | 1 | YES | 3 | 3 | . |
| `passage_hood_detachment_hood_workspace` | 1 | YES | 10 | 10 | . |
| `passage_hood_detachment_microscope_view` | 1 | YES | 3 | 3 | . |
| `plate_drug_treatment_media_adjustment_plate_map_review` | 1 | YES | 0 | . | . |
| `plate_drug_treatment_media_adjustment_plate_workspace` | 1 | YES | 5 | 5 | . |
| `plate_focus_bench` | 1 | YES | 0 | . | . |
| `plate_focus_hood` | 1 | YES | 0 | . | . |
| `plate_workspace` | 1 | YES | 3 | 3 | . |
| `sample_prep_bench` | 1 | YES | 10 | 9 | 1 |
| `sdspage_assemble_electrode_module_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_attach_lid_and_leads_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_destain_gel_rock_workspace` | 1 | YES | 2 | 2 | . |
| `sdspage_destain_gel_setup_workspace` | 1 | YES | 6 | 6 | . |
| `sdspage_fill_tank_buffer_workspace` | 1 | YES | 5 | 5 | . |
| `sdspage_heat_denature_samples_workspace` | 1 | YES | 0 | . | . |
| `sdspage_image_gel_result_review` | 1 | YES | 5 | 5 | . |
| `sdspage_image_gel_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_load_protein_ladder_workspace` | 1 | YES | 8 | 7 | 1 |
| `sdspage_load_sample_single_lane_workspace` | 1 | YES | 5 | 5 | . |
| `sdspage_load_samples_batch_workspace` | 1 | YES | 5 | 5 | . |
| `sdspage_prepare_gel_cassette_workspace` | 1 | YES | 3 | 3 | . |
| `sdspage_prepare_running_buffer_workspace` | 1 | YES | 0 | . | . |
| `sdspage_prepare_sample_mix_batch_workspace` | 1 | YES | 4 | 4 | . |
| `sdspage_prepare_sample_mix_single_lane_workspace` | 1 | YES | 6 | 6 | . |
| `sdspage_recycle_buffer_workspace` | 1 | YES | 5 | 5 | . |
| `sdspage_run_electrophoresis_endpoint_review` | 1 | YES | 8 | 8 | . |
| `sdspage_run_electrophoresis_workspace` | 1 | YES | 9 | 9 | . |
| `sdspage_stain_gel_workspace` | 1 | YES | 6 | 6 | . |
| `seeding_calculation_review` | 1 | YES | 0 | . | . |
| `seeding_workspace` | 1 | YES | 0 | . | . |
| `staining_bench` | 1 | YES | 10 | 10 | . |
| `viability_review` | 1 | YES | 5 | 5 | . |

## Severity-graded de-overlap diagnostics

Counts from `result.severityDiagnostics` (keyed by `code`), the de-overlap Error/Warning/Review stream. `unresolved_label_overlap` is the overlap-gate metric. `unresolved_overlap` is a bounds Error (object too big for its zone), not a label issue. A `.` means the code did not fire for that scene.

| Scene | poor_label_alignment | unfittable_asset |
| --- | --- | --- |
| `bench_basic` | . | . |
| `cell_counter_basic` | . | . |
| `cell_counter_workspace` | . | 10 |
| `centrifuge_workspace` | . | 15 |
| `dilution_calculation_200` | . | . |
| `dilution_calculation_50` | . | . |
| `dilution_calculation_500` | . | . |
| `dilution_calculation_60` | . | . |
| `dilution_initial_calculation_review` | . | . |
| `dilution_volume_review` | . | . |
| `dilution_workspace` | . | . |
| `drug_dilution_setup_bench_setup` | 1 | . |
| `electrophoresis_bench` | . | . |
| `extraction_workspace` | . | . |
| `heat_block_bench` | . | . |
| `hemocytometer_count_review` | . | . |
| `hemocytometer_view` | . | 8 |
| `hood_basic` | . | . |
| `hood_workspace` | . | 11 |
| `imaging_bench` | . | . |
| `incubator_workspace` | . | . |
| `microscope_basic` | . | 7 |
| `mtt_reagent_prep_bench_workspace` | 1 | . |
| `mtt_solubilization_readout_bench_workspace` | . | . |
| `mtt_solubilization_readout_plate_reader_workspace` | . | . |
| `mtt_solubilization_readout_result_review` | . | . |
| `passage_hood_detachment_hood_workspace` | . | 12 |
| `passage_hood_detachment_microscope_view` | . | 7 |
| `plate_drug_treatment_media_adjustment_plate_map_review` | . | . |
| `plate_drug_treatment_media_adjustment_plate_workspace` | . | 6 |
| `plate_focus_bench` | . | . |
| `plate_focus_hood` | . | . |
| `plate_workspace` | . | 6 |
| `sample_prep_bench` | . | . |
| `sdspage_assemble_electrode_module_workspace` | . | . |
| `sdspage_attach_lid_and_leads_workspace` | . | . |
| `sdspage_destain_gel_rock_workspace` | . | . |
| `sdspage_destain_gel_setup_workspace` | . | . |
| `sdspage_fill_tank_buffer_workspace` | . | . |
| `sdspage_heat_denature_samples_workspace` | . | . |
| `sdspage_image_gel_result_review` | . | . |
| `sdspage_image_gel_workspace` | . | . |
| `sdspage_load_protein_ladder_workspace` | 1 | . |
| `sdspage_load_sample_single_lane_workspace` | . | . |
| `sdspage_load_samples_batch_workspace` | . | . |
| `sdspage_prepare_gel_cassette_workspace` | . | . |
| `sdspage_prepare_running_buffer_workspace` | . | . |
| `sdspage_prepare_sample_mix_batch_workspace` | . | . |
| `sdspage_prepare_sample_mix_single_lane_workspace` | . | . |
| `sdspage_recycle_buffer_workspace` | . | . |
| `sdspage_run_electrophoresis_endpoint_review` | . | . |
| `sdspage_run_electrophoresis_workspace` | . | . |
| `sdspage_stain_gel_workspace` | . | . |
| `seeding_calculation_review` | . | . |
| `seeding_workspace` | . | 10 |
| `staining_bench` | . | . |
| `viability_review` | . | . |

## Overlap pairs

Each row is one overlap Error from `result.severityDiagnostics`, naming the two involved placements, the zone, the diagnostic code, and the remaining penetration depth (scene-percent). `unresolved_label_overlap` is a label sitting over another label or artwork; `unresolved_overlap` is an object escaping its zone bounds. Same-zone pairs are in-zone collisions; differing zone membership for the two names indicates a cross-zone graze.

None. No overlap Error fired in any scene.

## Scenes that failed to run

None. Every scene ran to completion.
