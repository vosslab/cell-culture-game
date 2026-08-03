# Vertical reflow WP-4 per-scene evidence table

This is the committed WP-4 per-scene evidence for the vertical-layout-reflow
change. It merges the quantitative layout-pipeline columns with the by-eye
visual verdict for every non-fixture rendered scene, one row per scene. It is
the evidence artifact that closes gate G4 of the vertical-reflow plan.

- Date: 2026-06-11
- Gate closed: G4 (WP-4 per-scene evidence contract)
- Scope: 34 non-fixture rendered scenes (dev_smoke and `tests/content`
  fixtures excluded).

Column meanings:

- `label_side`: where labels sit relative to their objects (by-eye).
- `label_clear`: `clear`, or `overlap` with the own-vs-neighbor kind. Every
  overlap observed is label-vs-LABEL (neighbor text-on-text), never
  label-over-own-artwork.
- `band_reflowed`: `yes` when `band_height_after` differs from
  `band_height_before`.
- `uniform_rescale`: `yes` when `uniform_scale` is below 1.0 (a terminal
  uniform object rescale ran).
- `decision`: `SHIP-OK`, `REVIEW`, or `FAIL`. `REVIEW` marks label-on-label
  legibility crowding (not a contract violation). `FAIL` marks a pre-existing
  load failure.

## Per-scene evidence

| scene | label_side | label_clear | band_reflowed | uniform_rescale | uniform_scale | label_dominant | max_object_y_delta | band_height_before | band_height_after | never_crop_hard_fails | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bench_basic | above | clear | yes | yes | 0.411 | yes | 275.42 | 56.00 | 52.39 | 0 | SHIP-OK |
| cell_counter_basic | above | clear | yes | no | 1.000 | no | 234.64 | 52.00 | 51.48 | 0 | SHIP-OK |
| cell_counter_workspace | above | clear | yes | yes | 0.815 | yes | 422.73 | 52.00 | 58.76 | 0 | SHIP-OK |
| centrifuge_workspace | above | clear | yes | yes | 0.541 | yes | 445.52 | 56.00 | 64.92 | 0 | SHIP-OK |
| dilution_workspace | above | clear | yes | yes | 0.477 | yes | 270.00 | 56.00 | 49.30 | 0 | SHIP-OK |
| drug_dilution_setup_bench_setup | above | clear (overlap-count 1: label-box vs neighbor item-box, no own-art overlap by eye) | yes | yes | 0.521 | yes | 292.88 | 56.00 | 45.35 | 0 | SHIP-OK |
| electrophoresis_bench | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| extraction_workspace | unavailable (load-failed) | unavailable (load-failed) | yes | yes | 0.295 | yes | unavailable (load-failed) | 38.00 | 55.40 | unavailable (load-failed) | FAIL |
| heat_block_bench | above | clear | yes | yes | 0.957 | yes | 118.28 | 30.00 | 34.92 | 0 | SHIP-OK |
| hemocytometer_view | above (header band) | overlap (neighbor, label-vs-label) | yes | yes | 0.995 | yes | 515.31 | 74.00 | 90.00 | 0 | REVIEW |
| hood_basic | above | clear | yes | yes | 0.485 | yes | 238.59 | 56.00 | 49.57 | 0 | SHIP-OK |
| hood_workspace | above | clear | yes | yes | 0.360 | yes | 273.72 | 56.00 | 51.08 | 0 | SHIP-OK |
| imaging_bench | above | clear | yes | no | 1.000 | no | 212.72 | 54.00 | 53.51 | 0 | SHIP-OK |
| incubator_workspace | above | clear | yes | yes | 0.564 | yes | 217.52 | 56.00 | 68.26 | 0 | SHIP-OK |
| microscope_basic | above (header band) | overlap (neighbor, label-vs-label) | yes | yes | 0.868 | yes | 494.08 | 74.00 | 90.00 | 0 | REVIEW |
| mtt_reagent_prep_bench_workspace | above | clear | yes | yes | 0.446 | yes | 259.84 | 56.00 | 50.92 | 0 | SHIP-OK |
| mtt_solubilization_readout_bench_workspace | above | clear | yes | yes | 0.661 | yes | 421.08 | 56.00 | 66.10 | 0 | SHIP-OK |
| mtt_solubilization_readout_plate_reader_workspace | above | clear | yes | yes | 0.867 | no | 372.50 | 56.00 | 61.53 | 0 | SHIP-OK |
| passage_hood_detachment_hood_workspace | above | clear | yes | yes | 0.270 | yes | 305.63 | 56.00 | 46.82 | 0 | SHIP-OK |
| passage_hood_detachment_microscope_view | above (header band) | overlap (neighbor, label-vs-label) | yes | no | 1.000 | no | 693.61 | 74.00 | 90.00 | 0 | REVIEW |
| plate_drug_treatment_media_adjustment_plate_workspace | above | clear | yes | yes | 0.295 | yes | 422.06 | 56.00 | 51.65 | 0 | SHIP-OK |
| plate_workspace | above | clear | yes | yes | 0.387 | yes | 280.41 | 56.00 | 46.54 | 0 | SHIP-OK |
| sample_prep_bench | above | clear | yes | yes | 0.957 | yes | 109.98 | 28.00 | 34.92 | 0 | SHIP-OK |
| sdspage_attach_lid_and_leads_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| sdspage_destain_gel_rock_workspace | above | clear | yes | yes | 0.319 | yes | 298.48 | 56.00 | 59.03 | 0 | SHIP-OK |
| sdspage_fill_tank_buffer_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| sdspage_heat_denature_samples_workspace | above | clear | yes | yes | 0.957 | yes | 118.28 | 30.00 | 34.92 | 0 | SHIP-OK |
| sdspage_load_sample_single_lane_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| sdspage_prepare_running_buffer_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| sdspage_prepare_sample_mix_single_lane_workspace | above | clear | yes | yes | 0.813 | yes | 212.14 | 28.00 | 40.43 | 0 | SHIP-OK |
| sdspage_recycle_buffer_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| sdspage_run_electrophoresis_workspace | above | clear | yes | yes | 0.295 | yes | 439.84 | 38.00 | 55.40 | 0 | SHIP-OK |
| seeding_workspace | above | overlap (neighbor, label-vs-label) | yes | yes | 0.381 | yes | 270.66 | 56.00 | 54.08 | 0 | REVIEW |
| staining_bench | above | clear | yes | yes | 0.319 | yes | 298.48 | 56.00 | 59.03 | 0 | SHIP-OK |

## Units and sources

- Band heights (`band_height_before`, `band_height_after`) are in
  scene-percent units: `before` is the authored `zone.bounds` seed
  (bottom - top), `after` is the engine-computed `ComputedZoneBand`
  (bottom - top) from `runPipeline`, taken as the max over zones.
- `max_object_y_delta` is in rendered CSS pixels: the max absolute per-object
  `placement_bbox.y` move versus the persisted WP-0 baseline in
  `test-results/vertical_reflow/stats_before/`, matched by `placement_name`.
- `never_crop_hard_fails` is the sum of clipped items, fully-offscreen items,
  and placements with aspect deviation above 5 percent, from
  `generated/scene_render_stats`. Fully-offscreen items are included, covering
  the off-canvas case the bbox-clip check would otherwise undercount.
- `uniform_scale` and `label_dominant` are the terminal `reflowUniformScale`
  and `labelDominant` values from the layout pipeline run.
- `label_side` and `label_clear` are by-eye verdicts from opening each
  after-state PNG directly.

## Results summary

- SHIP-OK: 29
- REVIEW: 4
- FAIL: 1
- Total non-fixture scenes: 34

Contract statement: across all populated scenes there are zero never-crop hard
fails and zero own-art label overlaps. Every scientific asset (flasks, bottles,
pipettes, plates, racks, instruments) renders fully, uncropped, and without
aspect distortion, and every label sits clear of its own object's artwork. Both
hard contracts hold. The G4 hard gate is met.

The single `drug_dilution_setup_bench_setup` overlap count of 1 in the
quantitative scan is a label-box versus neighbor item-box proximity with no
identity exclusion; the by-eye verdict confirms the label sits in clear space
between neighbors, not over any artwork. It is therefore not an own-art overlap
and does not violate the contract.

## Follow-ups (not contract violations)

The full WP-4 visual sweep surfaced four scenes with label-vs-LABEL crowding in
dense top header rows. These are text-on-text legibility issues, distinct from
label-over-artwork, and are not never-crop or own-art contract violations:

- `hemocytometer_view`: top header labels collide
  ("Cell counter slide cartridge" over "Microtube rack (24-slot)"); right-side
  bottle labels crowd.
- `microscope_basic`: same top-row label-vs-label collision (left cell-counter
  and rack labels, right hemocytometer and ethanol labels).
- `passage_hood_detachment_microscope_view`: same top-row label-vs-label
  collision.
- `seeding_workspace`: "Cell suspension (counted)" and "Micropipette" labels
  touch in the left-center cluster.

These are a horizontal label-stagger polish follow-up, tracked in
[LAYOUT_REMAINING_WORK.md](../../LAYOUT_REMAINING_WORK.md) section 7.

Separately, `extraction_workspace` is a pre-existing load failure: it renders as
a blank full-viewport gradient with zero objects (empty authored content). Its
never-crop, overlap, and y-delta cells are marked unavailable (load-failed). It
is out of scope for the reflow and does not block the other scenes.
