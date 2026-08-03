# Label alignment baseline audit

Generated: 2026-06-10

## Overview

This audit covers all 38 stats files in test-results/scene_label_alignment/stats_before/. It provides per-scene layout quality metrics as a baseline for WP-6 review and WP-4b risk ranking. Scenes are ranked worst-first by composite score. Dev fixtures are flagged [F].

## Schema notes

Fields read from each .stats.json (schema confirmed consistent across all 38 files):

- geometry.placements[].visual_bbox (x, y, w, h): rendered artwork bounding box
- geometry.placements[].label_bbox (x, y, w, h): label bounding box
- geometry.scene_bounds (left, right, top, bottom): scene pixel extents; coordinate_space is css_px_top_left
- layout.label_overlap_pair_count: label-vs-label overlap pairs
- layout.label_art_overlap_count: label-vs-artwork overlap count
- layout.clipped_item_count: items clipped by scene bounds; nearest analog for clamp count (no clamp field present)
- layout.fully_offscreen_item_count: items fully outside scene (collected but not used in composite score)

## Metric definitions

- avg_offset_px: mean |visual_bbox_center_x - label_bbox_center_x| across all placements in the scene.
  Formula: abs((visual_bbox.x + visual_bbox.w/2) - (label_bbox.x + label_bbox.w/2))
- lbl_pairs: layout.label_overlap_pair_count
- lbl_art: layout.label_art_overlap_count
- clipped: layout.clipped_item_count (clamp proxy; no dedicated clamp field in schema)
- rear_band: count of placements whose visual_bbox vertically intersects the 32-38% band of scene height.
  band_top = scene_top + 0.32 * scene_h; band_bot = scene_top + 0.38 * scene_h (scene_h = scene_bounds.bottom - scene_bounds.top).
  Intersection test: vb.y < band_bot AND (vb.y + vb.h) > band_top.
- score: composite = lbl_pairs*3 + lbl_art*2 + clipped*4 + avg_offset_px/10 + rear_band

## Spot-check verification

Scene: bench_basic, placement index 0: base_right_micropipette

visual_bbox: x=1773.96875, w=36.046875
obj_center_x  = 1773.96875 + 36.046875 / 2 = 1791.9921875
label_bbox:   x=1717.7890625, w=100.546875
label_center_x = 1717.7890625 + 100.546875 / 2 = 1768.0625
offset = |1791.9921875 - 1768.0625| = 23.9296875 px

This 23.9 px contributes to bench_basic avg_offset of 89.6 px. The centrifuge placement has a much larger offset (~282 px) that dominates the scene average.

## Per-scene baseline table (worst-first)

Column key: avg_offset = mean center offset (px), lbl_pairs = label overlap pairs, lbl_art = label-art overlaps, clipped = clipped items (clamp proxy), rear_band = placements in 32-38% vertical band, n = placement count, score = composite. [F] = dev fixture.

| rank | scene | avg_offset | lbl_pairs | lbl_art | clipped | rear_band | n | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | extraction_workspace | 63.2 | 2 | 2 | 0 | 1 | 17 | 17.3 |
| 2 | mtt_reagent_prep_bench_workspace | 111.7 | 1 | 1 | 0 | 0 | 10 | 16.2 |
| 3 | seeding_workspace | 75.9 | 1 | 0 | 1 | 1 | 13 | 15.6 |
| 4 | centrifuge_workspace | 85.6 | 2 | 0 | 0 | 0 | 14 | 14.6 |
| 5 | type_check [F] | 135.2 | 0 | 0 | 0 | 1 | 1 | 14.5 |
| 6 | hood_workspace | 93.8 | 0 | 0 | 1 | 1 | 11 | 14.4 |
| 7 | bench_basic | 89.6 | 0 | 2 | 0 | 1 | 11 | 14 |
| 8 | mtt_solubilization_readout_bench_workspace | 95.9 | 0 | 2 | 0 | 0 | 8 | 13.6 |
| 9 | passage_hood_detachment_microscope_view | 105.2 | 0 | 1 | 0 | 1 | 9 | 13.5 |
| 10 | plate_drug_treatment_media_adjustment_plate_workspace | 94.7 | 0 | 1 | 0 | 1 | 12 | 12.5 |
| 11 | microscope_basic | 104 | 0 | 0 | 0 | 1 | 8 | 11.4 |
| 12 | incubator_workspace | 83.2 | 0 | 1 | 0 | 1 | 9 | 11.3 |
| 13 | cell_counter_basic | 105.9 | 0 | 0 | 0 | 0 | 7 | 10.6 |
| 14 | hemocytometer_view | 95.8 | 0 | 0 | 0 | 1 | 10 | 10.6 |
| 15 | missing_svg_check [F] | 94.4 | 0 | 0 | 0 | 1 | 1 | 10.4 |
| 16 | mtt_solubilization_readout_plate_reader_workspace | 101.2 | 0 | 0 | 0 | 0 | 7 | 10.1 |
| 17 | hood_basic | 100.5 | 0 | 0 | 0 | 0 | 10 | 10 |
| 18 | electrophoresis_bench | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 19 | sdspage_attach_lid_and_leads_workspace | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 20 | sdspage_fill_tank_buffer_workspace | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 21 | sdspage_prepare_running_buffer_workspace | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 22 | sdspage_recycle_buffer_workspace | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 23 | sdspage_run_electrophoresis_workspace | 58 | 1 | 0 | 0 | 1 | 16 | 9.8 |
| 24 | sdspage_load_sample_single_lane_workspace | 55.7 | 1 | 0 | 0 | 1 | 17 | 9.6 |
| 25 | plate_workspace | 90.2 | 0 | 0 | 0 | 0 | 13 | 9 |
| 26 | cell_counter_workspace | 90.2 | 0 | 0 | 0 | 0 | 9 | 9 |
| 27 | passage_hood_detachment_hood_workspace | 89.4 | 0 | 0 | 0 | 0 | 12 | 8.9 |
| 28 | select_check [F] | 54.1 | 0 | 0 | 0 | 2 | 2 | 7.4 |
| 29 | sdspage_destain_gel_rock_workspace | 70.6 | 0 | 0 | 0 | 0 | 9 | 7.1 |
| 30 | staining_bench | 70.6 | 0 | 0 | 0 | 0 | 9 | 7.1 |
| 31 | dilution_workspace | 70.4 | 0 | 0 | 0 | 0 | 15 | 7 |
| 32 | drug_dilution_setup_bench_setup | 66.7 | 0 | 0 | 0 | 0 | 13 | 6.7 |
| 33 | imaging_bench | 66.4 | 0 | 0 | 0 | 0 | 11 | 6.6 |
| 34 | adversarial_overflow_smoke [F] | 57 | 0 | 0 | 0 | 0 | 21 | 5.7 |
| 35 | heat_block_bench | 50.3 | 0 | 0 | 0 | 0 | 13 | 5 |
| 36 | sdspage_heat_denature_samples_workspace | 50.3 | 0 | 0 | 0 | 0 | 13 | 5 |
| 37 | sample_prep_bench | 46.4 | 0 | 0 | 0 | 0 | 13 | 4.6 |
| 38 | sdspage_prepare_sample_mix_single_lane_workspace | 46.2 | 0 | 0 | 0 | 0 | 13 | 4.6 |

Row count: 38

## Worst-5 scenes (WP-4b risk candidates)

1. extraction_workspace -- score 17.3. Has both label-label overlap pairs (2) and label-art overlaps (2), plus rear-band congestion (1). Multiple simultaneous defect types; highest-priority fix target.
2. mtt_reagent_prep_bench_workspace -- score 16.2. Highest avg_offset in corpus (111.7 px), plus label pair (1) and label-art overlap (1). High offset combined with crowding.
3. seeding_workspace -- score 15.6. Clipped item (1), label pair (1), rear-band congestion (1). Three separate defect types.
4. centrifuge_workspace -- score 14.6. Two label-pair overlaps (2); highest lbl_pairs count in corpus. No art overlaps or clipping.
5. type_check [F] -- score 14.5. Dev fixture with single placement and extreme avg_offset (135.2 px). Score is purely offset-driven; no overlap or clipping defects.

## Summary statistics

- Total label overlap pairs: 13 (11 of 38 scenes affected)
- Total label-art overlaps: 10 (7 of 38 scenes affected)
- Total clipped items (clamp proxy): 2 (2 scenes: hood_workspace, seeding_workspace)
- Total rear-band 32-38% placements: 20 across all scenes
- Mean avg_center_offset across all 38 scenes: 77.8 px
- Scenes with composite score above 10: 17 of 38
- Scenes with zero overlap/clipping defects (lbl_pairs=0, lbl_art=0, clipped=0): 24 of 38

## Schema surprises

- No clamp_count field: the task spec requested clamp counts but no such field exists in the schema. clipped_item_count is the nearest structural analog.
- Uniform viewport: all 38 scenes have scene_h_px=1062 (top=16, bottom=1078). The 32-38% rear band is px 355-419 in every scene.
- Six sdspage scenes share identical metrics (avg_offset=58.0, lbl_pairs=1, n=16, rear_band=1). These scenes are structurally near-identical and will move together in any fix pass.
- type_check [F] ranks in the worst-5 purely from avg_offset (135.2 px on a single 1-placement fixture). Its score is not comparable to multi-placement production scenes.

