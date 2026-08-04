# M0 layout parity: fixed 16:9 precompute vs live panel

Work package WP-FEAS1. Proves the existing layout engine produces the same `ComputedItem[]` at a canonical 16:9 precompute viewport as at a live 16:9 panel, so layout can move to compile time behind the 16:9 contract.

## Verdict

- Go signal: GO
- Scenes checked: 57
- Scenes passing parity + scene_name keying: 57
- All scenes exact bit-for-bit (no epsilon needed): yes
- Viewport sweep correct: yes

## Reproducibility parameters

- Precompute (canonical) viewport: 1920x1080
- Live panel viewport (parity control): 1280x720 (same 16:9 aspect, different pixel size)
- Sort order (serialization): items sorted ascending by `placement_name` before diffing, stable string compare.
- Serialization method: field-by-field compare over the ComputedItem fields the renderer reads (_scale, _centerX, _baselineY, _top, _visualWidth, _height, _footprint, _labelX, _labelY, _labelLines).
- Numeric tolerance: 1e-9 absolute (IEEE-754 noise only).
- Tolerance rationale: same-aspect 16:9 viewports run identical floating-point arithmetic in `vertical_layout.ts` (the only viewport-dependent term is `viewport.w / viewport.h`, identical for any 16:9 size), so exact equality is the expectation. The epsilon absorbs representational noise only; the report flags any non-exact match.

## Per-scene parity

| scene_name | items | parity | exact-zero | max abs delta | scene_name keyed | consumed artifact |
| --- | --- | --- | --- | --- | --- | --- |
| bench_basic | 9 | PASS | yes | 0 | yes | match |
| cell_counter_basic | 7 | PASS | yes | 0 | yes | match |
| cell_counter_workspace | 10 | PASS | yes | 0 | yes | match |
| centrifuge_workspace | 15 | PASS | yes | 0 | yes | match |
| dilution_calculation_200 | 5 | PASS | yes | 0 | yes | match |
| dilution_calculation_50 | 5 | PASS | yes | 0 | yes | match |
| dilution_calculation_500 | 5 | PASS | yes | 0 | yes | match |
| dilution_calculation_60 | 5 | PASS | yes | 0 | yes | match |
| dilution_initial_calculation_review | 4 | PASS | yes | 0 | yes | match |
| dilution_volume_review | 4 | PASS | yes | 0 | yes | match |
| dilution_workspace | 13 | PASS | yes | 0 | yes | match |
| drug_dilution_setup_bench_setup | 12 | PASS | yes | 0 | yes | match |
| electrophoresis_bench | 16 | PASS | yes | 0 | yes | match |
| extraction_workspace | 9 | PASS | yes | 0 | yes | match |
| heat_block_bench | 12 | PASS | yes | 0 | yes | match |
| hemocytometer_count_review | 4 | PASS | yes | 0 | yes | match |
| hemocytometer_view | 8 | PASS | yes | 0 | yes | match |
| hood_basic | 9 | PASS | yes | 0 | yes | match |
| hood_workspace | 11 | PASS | yes | 0 | yes | match |
| imaging_bench | 11 | PASS | yes | 0 | yes | match |
| incubator_workspace | 8 | PASS | yes | 0 | yes | match |
| microscope_basic | 7 | PASS | yes | 0 | yes | match |
| mtt_reagent_prep_bench_workspace | 10 | PASS | yes | 0 | yes | match |
| mtt_solubilization_readout_bench_workspace | 6 | PASS | yes | 0 | yes | match |
| mtt_solubilization_readout_plate_reader_workspace | 2 | PASS | yes | 0 | yes | match |
| mtt_solubilization_readout_result_review | 4 | PASS | yes | 0 | yes | match |
| passage_hood_detachment_hood_workspace | 12 | PASS | yes | 0 | yes | match |
| passage_hood_detachment_microscope_view | 7 | PASS | yes | 0 | yes | match |
| plate_drug_treatment_media_adjustment_plate_map_review | 3 | PASS | yes | 0 | yes | match |
| plate_drug_treatment_media_adjustment_plate_workspace | 6 | PASS | yes | 0 | yes | match |
| plate_focus_bench | 1 | PASS | yes | 0 | yes | match |
| plate_focus_hood | 1 | PASS | yes | 0 | yes | match |
| plate_workspace | 6 | PASS | yes | 0 | yes | match |
| sample_prep_bench | 11 | PASS | yes | 0 | yes | match |
| sdspage_assemble_electrode_module_workspace | 4 | PASS | yes | 0 | yes | match |
| sdspage_attach_lid_and_leads_workspace | 7 | PASS | yes | 0 | yes | match |
| sdspage_destain_gel_rock_workspace | 6 | PASS | yes | 0 | yes | match |
| sdspage_destain_gel_setup_workspace | 7 | PASS | yes | 0 | yes | match |
| sdspage_fill_tank_buffer_workspace | 6 | PASS | yes | 0 | yes | match |
| sdspage_heat_denature_samples_workspace | 2 | PASS | yes | 0 | yes | match |
| sdspage_image_gel_result_review | 5 | PASS | yes | 0 | yes | match |
| sdspage_image_gel_workspace | 6 | PASS | yes | 0 | yes | match |
| sdspage_load_protein_ladder_workspace | 7 | PASS | yes | 0 | yes | match |
| sdspage_load_sample_single_lane_workspace | 8 | PASS | yes | 0 | yes | match |
| sdspage_load_samples_batch_workspace | 8 | PASS | yes | 0 | yes | match |
| sdspage_prepare_gel_cassette_workspace | 3 | PASS | yes | 0 | yes | match |
| sdspage_prepare_running_buffer_workspace | 3 | PASS | yes | 0 | yes | match |
| sdspage_prepare_sample_mix_batch_workspace | 8 | PASS | yes | 0 | yes | match |
| sdspage_prepare_sample_mix_single_lane_workspace | 9 | PASS | yes | 0 | yes | match |
| sdspage_recycle_buffer_workspace | 6 | PASS | yes | 0 | yes | match |
| sdspage_run_electrophoresis_endpoint_review | 8 | PASS | yes | 0 | yes | match |
| sdspage_run_electrophoresis_workspace | 11 | PASS | yes | 0 | yes | match |
| sdspage_stain_gel_workspace | 7 | PASS | yes | 0 | yes | match |
| seeding_calculation_review | 4 | PASS | yes | 0 | yes | match |
| seeding_workspace | 10 | PASS | yes | 0 | yes | match |
| staining_bench | 10 | PASS | yes | 0 | yes | match |
| viability_review | 5 | PASS | yes | 0 | yes | match |

The consumed-artifact column compares `PRECOMPUTED_LAYOUT[scene].final` (generated/precomputed_layout.ts, the exact array the browser production path renders under WP-PRECOMP2) against the runtime engine at the canonical 16:9 frame. `match` means the build artifact is byte-current with the engine.

## Viewport sweep

Each viewport is compared against the canonical 16:9 frame, aggregated across every scene. Only the 16:9 rows are gated: in the browser the CSS (`.scene-panel-inner { aspect-ratio: 16 / 9 }`) locks the panel to 16:9, so the live path always presents a 16:9 viewport and must move no field. The off-16:9 rows are contrast controls that document why the lock matters: a different PX_PER_SCENE_PERCENT factor shifts `_height` for every item and cascades into `_width_scale`, `_centerX`, and the rest. That is genuine per-aspect reflow, not pure letterboxing -- exactly the behavior the 16:9 contract removes. These rows are reported, not failed.

| viewport | aspect | fields moved vs 16:9 | result |
| --- | --- | --- | --- |
| 1920x1080 | 16:9 | (none) | GATED OK |
| 1280x720 | 16:9 | (none) | GATED OK |
| 2560x1440 | 16:9 | (none) | GATED OK |
| 960x540 | 16:9 | (none) | GATED OK |
| 1600x1000 | off-16:9 | _baselineY, _height, _labelX, _labelY, _scale, _top, _visualWidth | control: full per-aspect reflow (expected) |
| 1024x768 | off-16:9 | _baselineY, _height, _labelX, _labelY, _scale, _top, _visualWidth | control: full per-aspect reflow (expected) |

## Static-layout evidence (re-confirmed)

- `LayoutMove` is a no-op: `src/scene_runtime/protocol/scene_op_deps.ts` `apply_layout_move` warns and does not mutate layout.
- `ObjectStateChange` changes object state and appearance only; it does not re-run the layout pipeline.
- No resize listener: `src/protocol_host.tsx` measures `#scene-root` once via `getBoundingClientRect` at scene render; it registers no resize handler.
- Fixed placement set: the placement set is resolved once per scene load; `SceneChange` re-runs the same `render_protocol_scene` path keyed by `scene_name` (`SCENES[next_scene_name]`).

## SceneChange keying

`protocol_host.render_protocol_scene` resolves a scene as `SCENES[next_scene_name]`. A precomputed-layout map keyed by `scene_name` is reachable by the identical key; every scene self-reports its key (`scene.scene_name === scene_name`), confirmed in the per-scene table.

## Excluded scenes

- long_labels_smoke: absent from generated SCENES: scene validation error (placement references unknown object 'dmf_bottle'); never lays out, so it cannot be a parity subject. Exclusion is unrelated to viewport aspect.

## Blockers

- None.
