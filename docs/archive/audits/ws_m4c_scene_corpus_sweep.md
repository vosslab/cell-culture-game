# WS-M4-C scene corpus sweep results

Date: 2026-06-02
Task: M4 workstream WS-M4-C -- scene-side corpus sweep.
Renderer: Solid (M3).

## Summary

- Build: PASS (npm run build completed cleanly)
- Scenes rendered: 37 total (35 populated, 1 placeholder-only, 1 skipped)
- Contract diff: 36/36 PASS (0 failures, 0 contract_drift)
- No renderer regression detected.

## Per-scene results table

| Scene | Category | Yield | Real | PH | Empty% | Overlaps | Contract |
| --- | --- | --- | --- | --- | --- | --- | --- |
| adversarial_overflow_smoke | populated | 100% | 21 | 0 | 96.7% | 4 | PASS |
| bench_basic | populated | 100% | 10 | 0 | 75.4% | 0 | PASS |
| cell_counter_basic | populated | 100% | 7 | 0 | 80.7% | 1 | PASS |
| cell_counter_workspace | populated | 88.9% | 8 | 1 | 80.7% | 2 | PASS |
| centrifuge_workspace | populated | 100% | 13 | 0 | 83.7% | 0 | PASS |
| dilution_workspace | populated | 100% | 14 | 0 | 74.7% | 1 | PASS |
| drug_dilution_setup_bench_setup | populated | 100% | 12 | 0 | 76.1% | 3 | PASS |
| electrophoresis_bench | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| extraction_workspace | populated | 82.4% | 14 | 3 | 84.4% | 0 | PASS |
| heat_block_bench | populated | 100% | 13 | 0 | 90.7% | 0 | PASS |
| hemocytometer_view | populated | 100% | 10 | 0 | 67.2% | 2 | PASS |
| hood_basic | populated | 100% | 9 | 0 | 76.2% | 0 | PASS |
| hood_workspace | populated | 100% | 11 | 0 | 57.6% | 2 | PASS |
| imaging_bench | populated | 100% | 11 | 0 | 86.8% | 0 | PASS |
| incubator_workspace | populated | 88.9% | 8 | 1 | 81.8% | 0 | PASS |
| long_labels_smoke | skipped | - | - | - | - | - | no baseline (skipped) |
| microscope_basic | populated | 100% | 8 | 0 | 69.6% | 1 | PASS |
| missing_svg_check | placeholder-only | 0% | 0 | 1 | 100% | 0 | PASS |
| mtt_reagent_prep_bench_workspace | populated | 100% | 9 | 0 | 81.1% | 1 | PASS |
| mtt_solubilization_readout_bench_workspace | populated | 100% | 8 | 0 | 80.4% | 0 | PASS |
| mtt_solubilization_readout_plate_reader_workspace | populated | 100% | 7 | 0 | 87.3% | 0 | PASS |
| passage_hood_detachment_hood_workspace | populated | 100% | 13 | 0 | 69.8% | 1 | PASS |
| passage_hood_detachment_microscope_view | populated | 100% | 9 | 0 | 68.4% | 1 | PASS |
| plate_drug_treatment_media_adjustment_plate_workspace | populated | 100% | 12 | 0 | 71% | 1 | PASS |
| plate_workspace | populated | 100% | 13 | 0 | 72.2% | 2 | PASS |
| sample_prep_bench | populated | 100% | 13 | 0 | 91.4% | 0 | PASS |
| sdspage_attach_lid_and_leads_workspace | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| sdspage_destain_gel_rock_workspace | populated | 100% | 9 | 0 | 82.5% | 0 | PASS |
| sdspage_fill_tank_buffer_workspace | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| sdspage_heat_denature_samples_workspace | populated | 100% | 13 | 0 | 90.7% | 0 | PASS |
| sdspage_load_sample_single_lane_workspace | populated | 82.4% | 14 | 3 | 85.6% | 0 | PASS |
| sdspage_prepare_running_buffer_workspace | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| sdspage_prepare_sample_mix_single_lane_workspace | populated | 100% | 14 | 0 | 91.3% | 0 | PASS |
| sdspage_recycle_buffer_workspace | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| sdspage_run_electrophoresis_workspace | populated | 81.3% | 13 | 3 | 85.7% | 0 | PASS |
| seeding_workspace | populated | 100% | 13 | 0 | 53.9% | 5 | PASS |
| staining_bench | populated | 100% | 9 | 0 | 82.5% | 0 | PASS |

## Notes on scenes not at 100% yield (placeholders present)

These scenes have placeholder items. All were ALREADY captured in the M1 baseline
(the baseline froze their placeholder counts), so they are not regressions.

- cell_counter_workspace: 1 placeholder (yield 88.9%)
- electrophoresis_bench: 3 placeholders (yield 81.3%)
- extraction_workspace: 3 placeholders (yield 82.4%)
- incubator_workspace: 1 placeholder (yield 88.9%)
- sdspage_attach_lid_and_leads_workspace: 3 placeholders (yield 81.3%)
- sdspage_fill_tank_buffer_workspace: 3 placeholders (yield 81.3%)
- sdspage_load_sample_single_lane_workspace: 3 placeholders (yield 82.4%)
- sdspage_prepare_running_buffer_workspace: 3 placeholders (yield 81.3%)
- sdspage_recycle_buffer_workspace: 3 placeholders (yield 81.3%)
- sdspage_run_electrophoresis_workspace: 3 placeholders (yield 81.3%)

These are pre-existing placeholder assets (electrode_module, gel_opening_tool,
kimwipe_pad, power_supply_off) flagged by SVG_PLACEHOLDER_KEYS. Not renderer
regressions.

## Skipped scene

- long_labels_smoke: skipped by the manifest (validation error: unknown object
  'dmf_bottle' in scene YAML). No baseline exists for it; not counted in the
  contract diff.

## Contract drift

None. 0 violations across 36 baselined scenes.

## Verification commands (exact output)

npm run build last line:
  Built dist/ (GitHub Pages-ready).

node tools/scene_to_png.mjs --all category totals line:
  TOTAL                37

node tests/e2e/e2e_scene_dom_contract_diff.mjs summary:
  total:  36
  passed: 36
  failed: 0
  PASS: scene DOM contract diff check

## Output locations

- PNGs and stats: test-results/scenes/<scene>.png and <scene>.stats.json
- Summary: test-results/scenes/summary.json
- This file: docs/active_plans/audits/ws_m4c_scene_corpus_sweep.md

## Residual risks

- adversarial_overflow_smoke flags near-empty (96.7% empty, 4 overlaps) -- this is
  intentional for the overflow smoke test.
- seeding_workspace has 5 overlap pairs -- pre-existing layout concern, not a
  renderer regression (passes contract check).
- Placeholder items across 10 scenes are pre-existing gaps tracked in
  assets/SVG_ASSET_GAPS.md, not Solid renderer regressions.
- The `long_labels_smoke` scene is skipped because its YAML references an unknown
  object; it has no baseline. This is a content authoring gap, not a renderer issue.

## Status

DONE
