# M2c generalization preflight report

Run at: 2026-08-03 02:02:17 UTC

## Scope

Lane D3 runs the full layout pipeline on every emitted scene
(all keys in SCENES from generated/scenes.ts). For each scene:

- Parse and normalize the scene YAML
- Resolve all objects to the object library
- Resolve all assets to SVG_MANIFEST
- Run the full convergence loop (up to MAX_LAYOUT_PASSES)
- Run structural guards on final layout
- Capture diagnostics, pass counts, and guard pass/fail verdict

## Method

Each preflight invokes:
`runPipeline(scene, { library: OBJECT_LIBRARY, assets: ASSET_SPECS })`
followed by `runStructuralGuards(result.final, result.scene)` to verify
layout geometry before D4 attempts rendering.

## Results: summary table

| scene | diagnostics | passes | final_items | guard_verdict | overlap_count | zone_overflow |
| --- | --- | --- | --- | --- | --- | --- |
| bench_basic | 9 | 1 | 10 | PASS | 0 | 9 |
| cell_counter_basic | 7 | 1 | 7 | PASS | 0 | 7 |
| cell_counter_workspace | 8 | 1 | 9 | PASS | 0 | 8 |
| centrifuge_workspace | 13 | 1 | 13 | PASS | 0 | 13 |
| dilution_workspace | 8 | 1 | 11 | PASS | 0 | 8 |
| drug_dilution_setup_bench_setup | 7 | 1 | 9 | PASS | 0 | 7 |
| electrophoresis_bench | 16 | 1 | 16 | PASS | 0 | 16 |
| extraction_workspace | 6 | 1 | 6 | PASS | 0 | 6 |
| heat_block_bench | 12 | 1 | 13 | PASS | 0 | 12 |
| hemocytometer_view | 7 | 1 | 9 | PASS | 0 | 7 |
| hood_basic | 5 | 1 | 9 | PASS | 0 | 5 |
| hood_workspace | 4 | 1 | 8 | PASS | 0 | 4 |
| imaging_bench | 13 | 1 | 12 | PASS | 0 | 12 |
| incubator_workspace | 5 | 1 | 6 | PASS | 0 | 5 |
| microscope_basic | 5 | 1 | 7 | PASS | 0 | 5 |
| mtt_reagent_prep_bench_workspace | 8 | 1 | 8 | PASS | 0 | 8 |
| mtt_solubilization_readout_bench_workspace | 3 | 1 | 4 | PASS | 0 | 3 |
| mtt_solubilization_readout_plate_reader_workspace | 2 | 1 | 2 | PASS | 0 | 2 |
| passage_hood_detachment_hood_workspace | 6 | 1 | 10 | PASS | 0 | 6 |
| passage_hood_detachment_microscope_view | 3 | 1 | 6 | PASS | 0 | 3 |
| plate_drug_treatment_media_adjustment_plate_workspace | 2 | 1 | 4 | PASS | 0 | 2 |
| plate_focus_bench | 0 | 1 | 1 | PASS | 0 | 0 |
| plate_focus_hood | 0 | 1 | 1 | PASS | 0 | 0 |
| plate_workspace | 5 | 1 | 6 | PASS | 0 | 5 |
| sample_prep_bench | 11 | 1 | 12 | PASS | 0 | 11 |
| sdspage_attach_lid_and_leads_workspace | 3 | 1 | 4 | PASS | 0 | 3 |
| sdspage_destain_gel_rock_workspace | 2 | 1 | 4 | PASS | 0 | 2 |
| sdspage_destain_gel_setup_workspace | 6 | 1 | 7 | PASS | 0 | 6 |
| sdspage_fill_tank_buffer_workspace | 4 | 1 | 5 | PASS | 0 | 4 |
| sdspage_heat_denature_samples_workspace | 1 | 1 | 3 | FAIL: Structural guard failure (item overlap): item "front_heat_block" overlaps with "front_sds_microtube_rack" by 4.9%. | 1 | 0 |
| sdspage_image_gel_workspace | 4 | 1 | 4 | PASS | 0 | 4 |
| sdspage_load_protein_ladder_workspace | 5 | 1 | 5 | PASS | 0 | 5 |
| sdspage_load_sample_single_lane_workspace | 3 | 1 | 7 | PASS | 0 | 3 |
| sdspage_load_samples_batch_workspace | 3 | 1 | 7 | PASS | 0 | 3 |
| sdspage_prepare_running_buffer_workspace | 16 | 1 | 16 | PASS | 0 | 16 |
| sdspage_prepare_sample_mix_batch_workspace | 4 | 1 | 7 | PASS | 0 | 4 |
| sdspage_prepare_sample_mix_single_lane_workspace | 6 | 1 | 6 | PASS | 0 | 5 |
| sdspage_recycle_buffer_workspace | 3 | 1 | 4 | PASS | 0 | 3 |
| sdspage_run_electrophoresis_workspace | 3 | 1 | 4 | PASS | 0 | 3 |
| sdspage_stain_gel_workspace | 6 | 1 | 7 | PASS | 0 | 6 |
| seeding_workspace | 6 | 1 | 9 | PASS | 0 | 6 |
| staining_bench | 10 | 1 | 10 | PASS | 0 | 10 |

## Per-scene detail

### bench_basic

**Guard verdict:** PASS

**Diagnostics:** 9 (passes: 1, final items: 10)
- vertical/warn/item_escapes_zone_vertically [rear_left_media_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_left_waste]
- vertical/warn/item_escapes_zone_vertically [rear_center_ethanol]
- vertical/warn/item_escapes_zone_vertically [rear_center_pbs]
- vertical/warn/item_escapes_zone_vertically [rear_right_heat_block]
- vertical/warn/item_escapes_zone_vertically [rear_right_vortex]
- vertical/warn/item_escapes_zone_vertically [center_centrifuge]
- vertical/warn/item_escapes_zone_vertically [center_water_bath]
- vertical/warn/item_escapes_zone_vertically [base_right_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 9

### cell_counter_basic

**Guard verdict:** PASS

**Diagnostics:** 7 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_cell_suspension_tube]
- vertical/warn/item_escapes_zone_vertically [rear_counter_slide_cartridge]
- vertical/warn/item_escapes_zone_vertically [rear_trypan_blue_tube]
- vertical/warn/item_escapes_zone_vertically [left_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [left_tip_box]
- vertical/warn/item_escapes_zone_vertically [main_cell_counter]
- vertical/warn/item_escapes_zone_vertically [base_hemocytometer_slide]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 7

### cell_counter_workspace

**Guard verdict:** PASS

**Diagnostics:** 8 (passes: 1, final items: 9)
- vertical/warn/item_escapes_zone_vertically [rear_cell_suspension_tube]
- vertical/warn/item_escapes_zone_vertically [rear_counter_slide_cartridge]
- vertical/warn/item_escapes_zone_vertically [rear_trypan_blue_tube]
- vertical/warn/item_escapes_zone_vertically [left_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [left_tip_box]
- vertical/warn/item_escapes_zone_vertically [instrument_lens_tissue]
- vertical/warn/item_escapes_zone_vertically [main_cell_counter]
- vertical/warn/item_escapes_zone_vertically [right_hemocytometer_slide]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 8

### centrifuge_workspace

**Guard verdict:** PASS

**Diagnostics:** 13 (passes: 1, final items: 13)
- vertical/warn/item_escapes_zone_vertically [rear_left_conical_tube]
- vertical/warn/item_escapes_zone_vertically [rear_left_media_bottle_reseed]
- vertical/warn/item_escapes_zone_vertically [rear_left_waste]
- vertical/warn/item_escapes_zone_vertically [rear_center_conical_rack]
- vertical/warn/item_escapes_zone_vertically [rear_right_biohazard_decant]
- vertical/warn/item_escapes_zone_vertically [rear_right_vortex]
- vertical/warn/item_escapes_zone_vertically [center_t75_flask_reseed]
- vertical/warn/item_escapes_zone_vertically [base_right_tip_box]
- vertical/warn/item_escapes_zone_vertically [right_aspirating_pipette]
- vertical/warn/item_escapes_zone_vertically [right_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [center_centrifuge_spin]
- vertical/warn/item_escapes_zone_vertically [base_right_micropipette]
- vertical/warn/item_escapes_zone_vertically [right_label_pen]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 13

### dilution_workspace

**Guard verdict:** PASS

**Diagnostics:** 8 (passes: 1, final items: 11)
- vertical/warn/item_escapes_zone_vertically [carb_stock]
- vertical/warn/item_escapes_zone_vertically [rear_left_media_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_left_waste]
- vertical/warn/item_escapes_zone_vertically [met_stock]
- vertical/warn/item_escapes_zone_vertically [rear_right_vortex]
- vertical/warn/item_escapes_zone_vertically [dilution_rack]
- vertical/warn/item_escapes_zone_vertically [carb_intermediate]
- vertical/warn/item_escapes_zone_vertically [met_working_tube]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 8

### drug_dilution_setup_bench_setup

**Guard verdict:** PASS

**Diagnostics:** 7 (passes: 1, final items: 9)
- vertical/warn/item_escapes_zone_vertically [rear_left_carboplatin_stock]
- vertical/warn/item_escapes_zone_vertically [rear_left_waste]
- vertical/warn/item_escapes_zone_vertically [rear_center_metformin_stock]
- vertical/warn/item_escapes_zone_vertically [rear_right_vortex]
- vertical/warn/item_escapes_zone_vertically [center_dilution_tube_rack]
- vertical/warn/item_escapes_zone_vertically [center_metformin_working_tube]
- vertical/warn/item_escapes_zone_vertically [center_microtube_intermediate]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 7

### electrophoresis_bench

**Guard verdict:** PASS

**Diagnostics:** 16 (passes: 1, final items: 16)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_ladder_tube]
- vertical/warn/item_escapes_zone_vertically [rear_left_recycle_buffer_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_left_running_buffer_10x]
- vertical/warn/item_escapes_zone_vertically [rear_right_gel_opening_tool]
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [center_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_p10_gel_loading_tip_box]
- vertical/warn/item_escapes_zone_vertically [front_left_mini_protean_gel]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]
- vertical/warn/item_escapes_zone_vertically [front_right_gel_comb]
- vertical/warn/item_escapes_zone_vertically [center_ddh2o_bottle]
- vertical/warn/item_escapes_zone_vertically [center_electrode_module]
- vertical/warn/item_escapes_zone_vertically [center_p200_micropipette]
- vertical/warn/item_escapes_zone_vertically [center_running_buffer_1x_carboy]
- vertical/warn/item_escapes_zone_vertically [front_center_waste_container]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 16

### extraction_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 6)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]
- vertical/warn/item_escapes_zone_vertically [rear_right_gel_opening_tool]
- vertical/warn/item_escapes_zone_vertically [center_electrode_module]
- vertical/warn/item_escapes_zone_vertically [front_center_staining_tray]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 6

### heat_block_bench

**Guard verdict:** PASS

**Diagnostics:** 12 (passes: 1, final items: 13)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_ladder]
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_sample]
- vertical/warn/item_escapes_zone_vertically [rear_center_bme]
- vertical/warn/item_escapes_zone_vertically [rear_center_laemmli]
- vertical/warn/item_escapes_zone_vertically [rear_right_ddh2o]
- vertical/warn/item_escapes_zone_vertically [rear_right_waste]
- vertical/warn/item_escapes_zone_vertically [mid_eppendorf_rack]
- vertical/warn/item_escapes_zone_vertically [mid_p10_tip_box]
- vertical/warn/item_escapes_zone_vertically [front_heat_block]
- vertical/warn/item_escapes_zone_vertically [front_micropipette]
- vertical/warn/item_escapes_zone_vertically [front_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 12

### hemocytometer_view

**Guard verdict:** PASS

**Diagnostics:** 7 (passes: 1, final items: 9)
- vertical/warn/item_escapes_zone_vertically [rear_tip_box]
- vertical/warn/item_escapes_zone_vertically [rear_ethanol_bottle]
- vertical/warn/item_escapes_zone_vertically [staining_tubes]
- vertical/warn/item_escapes_zone_vertically [left_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [main_microscope]
- vertical/warn/item_escapes_zone_vertically [prepared_hemocytometer]
- vertical/warn/item_escapes_zone_vertically [right_microtube_left]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 7

### hood_basic

**Guard verdict:** PASS

**Diagnostics:** 5 (passes: 1, final items: 9)
- vertical/warn/item_escapes_zone_vertically [rear_left_ethanol]
- vertical/warn/item_escapes_zone_vertically [base_rear_center_pbs]
- vertical/warn/item_escapes_zone_vertically [rear_center_waste]
- vertical/warn/item_escapes_zone_vertically [base_rear_right_media]
- vertical/warn/item_escapes_zone_vertically [base_rear_right_sterile_water]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### hood_workspace

**Guard verdict:** PASS

**Diagnostics:** 4 (passes: 1, final items: 8)
- vertical/warn/item_escapes_zone_vertically [rear_left_fresh_media]
- vertical/warn/item_escapes_zone_vertically [rear_center_conical_tube]
- vertical/warn/item_escapes_zone_vertically [rear_right_incubator]
- vertical/warn/item_escapes_zone_vertically [center_t75_flask]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 4

### imaging_bench

**Guard verdict:** PASS

**Diagnostics:** 13 (passes: 1, final items: 12)
- vertical/warn/item_escapes_zone_vertically [rear_coomassie]
- vertical/warn/item_escapes_zone_vertically [rear_destain]
- vertical/warn/item_escapes_zone_vertically [center_ddh2o_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_center_rocking_shaker]
- vertical/warn/item_escapes_zone_vertically [rear_ethanol_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [rear_tip_box]
- vertical/warn/item_escapes_zone_vertically [center_lightbox]
- vertical/warn/item_escapes_zone_vertically [center_staining_tray]
- vertical/warn/item_escapes_zone_vertically [left_microtube]
- vertical/warn/item_escapes_zone_vertically [right_micropipette]
- vertical/warn/item_escapes_zone_vertically [right_waste_container]
- labels/info/label_row_staggered [rear_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 12

### incubator_workspace

**Guard verdict:** PASS

**Diagnostics:** 5 (passes: 1, final items: 6)
- vertical/warn/item_escapes_zone_vertically [mtt_solution]
- vertical/warn/item_escapes_zone_vertically [drying_surface]
- vertical/warn/item_escapes_zone_vertically [hazard_waste_bin]
- vertical/warn/item_escapes_zone_vertically [main_incubator]
- vertical/warn/item_escapes_zone_vertically [pipette_multichannel]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### microscope_basic

**Guard verdict:** PASS

**Diagnostics:** 5 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_tip_box]
- vertical/warn/item_escapes_zone_vertically [rear_ethanol_bottle]
- vertical/warn/item_escapes_zone_vertically [left_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [left_cell_suspension]
- vertical/warn/item_escapes_zone_vertically [main_microscope]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### mtt_reagent_prep_bench_workspace

**Guard verdict:** PASS

**Diagnostics:** 8 (passes: 1, final items: 8)
- vertical/warn/item_escapes_zone_vertically [rear_left_waste]
- vertical/warn/item_escapes_zone_vertically [rear_right_vortex]
- vertical/warn/item_escapes_zone_vertically [center_mtt_solution_tube]
- vertical/warn/item_escapes_zone_vertically [base_right_tip_box]
- vertical/warn/item_escapes_zone_vertically [right_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [rear_left_mtt_powder]
- vertical/warn/item_escapes_zone_vertically [rear_center_pbs_bottle]
- vertical/warn/item_escapes_zone_vertically [base_right_micropipette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 8

### mtt_solubilization_readout_bench_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_left_dmso]
- vertical/warn/item_escapes_zone_vertically [rear_right_plate_reader]
- vertical/warn/item_escapes_zone_vertically [right_multichannel_pipette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### mtt_solubilization_readout_plate_reader_workspace

**Guard verdict:** PASS

**Diagnostics:** 2 (passes: 1, final items: 2)
- vertical/warn/item_escapes_zone_vertically [rear_left_plate_loading_target]
- vertical/warn/item_escapes_zone_vertically [center_plate_reader]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 2

### passage_hood_detachment_hood_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 10)
- vertical/warn/item_escapes_zone_vertically [rear_left_pbs]
- vertical/warn/item_escapes_zone_vertically [rear_center_trypsin]
- vertical/warn/item_escapes_zone_vertically [rear_left_ethanol]
- vertical/warn/item_escapes_zone_vertically [rear_center_media]
- vertical/warn/item_escapes_zone_vertically [rear_center_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [rear_right_incubator]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 6

### passage_hood_detachment_microscope_view

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 6)
- vertical/warn/item_escapes_zone_vertically [rear_tip_box]
- vertical/warn/item_escapes_zone_vertically [rear_right_hood_return]
- vertical/warn/item_escapes_zone_vertically [left_microtube_rack]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### plate_drug_treatment_media_adjustment_plate_workspace

**Guard verdict:** PASS

**Diagnostics:** 2 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_center_media]
- vertical/warn/item_escapes_zone_vertically [right_tool_micropipette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 2

### plate_focus_bench

**Guard verdict:** PASS

**Diagnostics:** 0 (passes: 1, final items: 1)
(none)

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 0

### plate_focus_hood

**Guard verdict:** PASS

**Diagnostics:** 0 (passes: 1, final items: 1)
(none)

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 0

### plate_workspace

**Guard verdict:** PASS

**Diagnostics:** 5 (passes: 1, final items: 6)
- vertical/warn/item_escapes_zone_vertically [rear_center_carb_stocks]
- vertical/warn/item_escapes_zone_vertically [rear_right_incubator]
- vertical/warn/item_escapes_zone_vertically [rear_center_carb_parent_stock]
- vertical/warn/item_escapes_zone_vertically [rear_center_metformin_stock]
- vertical/warn/item_escapes_zone_vertically [right_micropipette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### sample_prep_bench

**Guard verdict:** PASS

**Diagnostics:** 11 (passes: 1, final items: 12)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_ladder]
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_sample]
- vertical/warn/item_escapes_zone_vertically [rear_center_ddh2o]
- vertical/warn/item_escapes_zone_vertically [rear_center_laemmli]
- vertical/warn/item_escapes_zone_vertically [rear_right_bme]
- vertical/warn/item_escapes_zone_vertically [rear_right_waste]
- vertical/warn/item_escapes_zone_vertically [mid_eppendorf_rack]
- vertical/warn/item_escapes_zone_vertically [mid_p10_tip_box]
- vertical/warn/item_escapes_zone_vertically [center_micropipette]
- vertical/warn/item_escapes_zone_vertically [center_microtube_rack]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 11

### sdspage_attach_lid_and_leads_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### sdspage_destain_gel_rock_workspace

**Guard verdict:** PASS

**Diagnostics:** 2 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_center_destain_waste]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_kimwipe]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 2

### sdspage_destain_gel_setup_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_center_destain]
- vertical/warn/item_escapes_zone_vertically [rear_right_ddh2o]
- vertical/warn/item_escapes_zone_vertically [center_microwave]
- vertical/warn/item_escapes_zone_vertically [center_rocking_shaker]
- vertical/warn/item_escapes_zone_vertically [center_staining_tray]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_waste]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 6

### sdspage_fill_tank_buffer_workspace

**Guard verdict:** PASS

**Diagnostics:** 4 (passes: 1, final items: 5)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [center_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [front_left_electrophoresis_inner_chamber]
- vertical/warn/item_escapes_zone_vertically [front_right_electrophoresis_outer_chamber]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 4

### sdspage_heat_denature_samples_workspace

**Guard verdict:** FAIL
**Guard failure message:** Structural guard failure (item overlap): item "front_heat_block" overlaps with "front_sds_microtube_rack" by 4.9%.

**Diagnostics:** 1 (passes: 1, final items: 3)
- meta/error/item_overlap [front_heat_block] obj=heat_block

**Zones shrunk per pass:** 0

**Overlap count:** 1
**Zone overflow count:** 0

### sdspage_image_gel_workspace

**Guard verdict:** PASS

**Diagnostics:** 4 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [center_ddh2o_bottle]
- vertical/warn/item_escapes_zone_vertically [center_lightbox]
- vertical/warn/item_escapes_zone_vertically [center_staining_tray]
- vertical/warn/item_escapes_zone_vertically [right_waste_container]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 4

### sdspage_load_protein_ladder_workspace

**Guard verdict:** PASS

**Diagnostics:** 5 (passes: 1, final items: 5)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_ladder_tube]
- vertical/warn/item_escapes_zone_vertically [center_p200_micropipette]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_gel_loading_tip_box]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]
- vertical/warn/item_escapes_zone_vertically [front_center_sds_microtube_rack]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### sdspage_load_sample_single_lane_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_gel_loading_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### sdspage_load_samples_batch_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_gel_loading_tip_box]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### sdspage_prepare_running_buffer_workspace

**Guard verdict:** PASS

**Diagnostics:** 16 (passes: 1, final items: 16)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_ladder_tube]
- vertical/warn/item_escapes_zone_vertically [rear_left_recycle_buffer_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_left_running_buffer_10x]
- vertical/warn/item_escapes_zone_vertically [rear_right_gel_opening_tool]
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [center_serological_pipette]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_p10_gel_loading_tip_box]
- vertical/warn/item_escapes_zone_vertically [front_left_mini_protean_gel]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]
- vertical/warn/item_escapes_zone_vertically [front_right_gel_comb]
- vertical/warn/item_escapes_zone_vertically [center_ddh2o_carboy]
- vertical/warn/item_escapes_zone_vertically [center_electrode_module]
- vertical/warn/item_escapes_zone_vertically [center_p200_micropipette]
- vertical/warn/item_escapes_zone_vertically [center_running_buffer_preparation_carboy]
- vertical/warn/item_escapes_zone_vertically [front_center_waste_container]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 16

### sdspage_prepare_sample_mix_batch_workspace

**Guard verdict:** PASS

**Diagnostics:** 4 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_sample]
- vertical/warn/item_escapes_zone_vertically [rear_center_laemmli]
- vertical/warn/item_escapes_zone_vertically [rear_right_bme]
- vertical/warn/item_escapes_zone_vertically [center_microtube_rack]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 4

### sdspage_prepare_sample_mix_single_lane_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 6)
- vertical/warn/item_escapes_zone_vertically [rear_left_protein_sample]
- vertical/warn/item_escapes_zone_vertically [rear_center_laemmli]
- vertical/warn/item_escapes_zone_vertically [rear_right_bme]
- vertical/warn/item_escapes_zone_vertically [center_micropipette]
- vertical/warn/item_escapes_zone_vertically [center_microtube_rack]
- labels/info/label_row_staggered [center_micropipette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 5

### sdspage_recycle_buffer_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [front_left_electrophoresis_inner_chamber]
- vertical/warn/item_escapes_zone_vertically [front_right_electrophoresis_outer_chamber]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### sdspage_run_electrophoresis_workspace

**Guard verdict:** PASS

**Diagnostics:** 3 (passes: 1, final items: 4)
- vertical/warn/item_escapes_zone_vertically [rear_center_electrophoresis_tank]
- vertical/warn/item_escapes_zone_vertically [rear_right_power_supply]
- vertical/warn/item_escapes_zone_vertically [front_center_gel_cassette]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 3

### sdspage_stain_gel_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 7)
- vertical/warn/item_escapes_zone_vertically [rear_left_coomassie_stain]
- vertical/warn/item_escapes_zone_vertically [rear_right_ddh2o]
- vertical/warn/item_escapes_zone_vertically [center_microwave]
- vertical/warn/item_escapes_zone_vertically [center_rocking_shaker]
- vertical/warn/item_escapes_zone_vertically [center_staining_tray]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_waste]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 6

### seeding_workspace

**Guard verdict:** PASS

**Diagnostics:** 6 (passes: 1, final items: 9)
- vertical/warn/item_escapes_zone_vertically [rear_left_cell_suspension_tube]
- vertical/warn/item_escapes_zone_vertically [rear_center_media_bottle]
- vertical/warn/item_escapes_zone_vertically [rear_right_incubator]
- vertical/warn/item_escapes_zone_vertically [right_multichannel_pipette]
- vertical/warn/item_escapes_zone_vertically [rear_left_conical_tube_for_dilution]
- vertical/warn/item_escapes_zone_vertically [rear_center_vortex]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 6

### staining_bench

**Guard verdict:** PASS

**Diagnostics:** 10 (passes: 1, final items: 10)
- vertical/warn/item_escapes_zone_vertically [rear_left_coomassie_stain]
- vertical/warn/item_escapes_zone_vertically [rear_center_destain]
- vertical/warn/item_escapes_zone_vertically [rear_right_ddh2o]
- vertical/warn/item_escapes_zone_vertically [center_microwave]
- vertical/warn/item_escapes_zone_vertically [center_rocking_shaker]
- vertical/warn/item_escapes_zone_vertically [center_staining_tray]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_waste]
- vertical/warn/item_escapes_zone_vertically [rear_left_coomassie_recycle]
- vertical/warn/item_escapes_zone_vertically [rear_center_destain_waste]
- vertical/warn/item_escapes_zone_vertically [right_tool_area_kimwipe]

**Zones shrunk per pass:** 0

**Overlap count:** 0
**Zone overflow count:** 10

## Summary and next steps

**D4-ready (preflight pass):** 41 / 42

### Preflight-passing scenes (ready for D4 render):

- **bench_basic**: 9 diagnostics
- **cell_counter_basic**: 7 diagnostics
- **cell_counter_workspace**: 8 diagnostics
- **centrifuge_workspace**: 13 diagnostics
- **dilution_workspace**: 8 diagnostics
- **drug_dilution_setup_bench_setup**: 7 diagnostics
- **electrophoresis_bench**: 16 diagnostics
- **extraction_workspace**: 6 diagnostics
- **heat_block_bench**: 12 diagnostics
- **hemocytometer_view**: 7 diagnostics
- **hood_basic**: 5 diagnostics
- **hood_workspace**: 4 diagnostics
- **imaging_bench**: 13 diagnostics
- **incubator_workspace**: 5 diagnostics
- **microscope_basic**: 5 diagnostics
- **mtt_reagent_prep_bench_workspace**: 8 diagnostics
- **mtt_solubilization_readout_bench_workspace**: 3 diagnostics
- **mtt_solubilization_readout_plate_reader_workspace**: 2 diagnostics
- **passage_hood_detachment_hood_workspace**: 6 diagnostics
- **passage_hood_detachment_microscope_view**: 3 diagnostics
- **plate_drug_treatment_media_adjustment_plate_workspace**: 2 diagnostics
- **plate_focus_bench**: 0 diagnostics
- **plate_focus_hood**: 0 diagnostics
- **plate_workspace**: 5 diagnostics
- **sample_prep_bench**: 11 diagnostics
- **sdspage_attach_lid_and_leads_workspace**: 3 diagnostics
- **sdspage_destain_gel_rock_workspace**: 2 diagnostics
- **sdspage_destain_gel_setup_workspace**: 6 diagnostics
- **sdspage_fill_tank_buffer_workspace**: 4 diagnostics
- **sdspage_image_gel_workspace**: 4 diagnostics
- **sdspage_load_protein_ladder_workspace**: 5 diagnostics
- **sdspage_load_sample_single_lane_workspace**: 3 diagnostics
- **sdspage_load_samples_batch_workspace**: 3 diagnostics
- **sdspage_prepare_running_buffer_workspace**: 16 diagnostics
- **sdspage_prepare_sample_mix_batch_workspace**: 4 diagnostics
- **sdspage_prepare_sample_mix_single_lane_workspace**: 6 diagnostics
- **sdspage_recycle_buffer_workspace**: 3 diagnostics
- **sdspage_run_electrophoresis_workspace**: 3 diagnostics
- **sdspage_stain_gel_workspace**: 6 diagnostics
- **seeding_workspace**: 6 diagnostics
- **staining_bench**: 10 diagnostics

### Preflight-failing scenes (needs fix before D4):

- **sdspage_heat_denature_samples_workspace**: Structural guard failure (item overlap): item "front_heat_block" overlaps with "front_sds_microtube_rack" by 4.9%.

Scenes that pass structural guards proceed to D4 rendering.
Scenes that fail are classified per D5 taxonomy.
