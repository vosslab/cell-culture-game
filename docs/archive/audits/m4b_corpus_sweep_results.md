# WS-M4-B Protocol Corpus Sweep Results

**Date:** 2026-06-02
**Total protocols:** 31

## Outcome counts

- unsupported_gesture: 14
- completed: 7
- render_failure: 5
- missing_object: 4
- other: 1

## Per-protocol results table

| Protocol | Type | Render | Walker | Failing Step | Failing Target | Gesture |
| --- | --- | --- | --- | --- | --- | --- |
| cell_culture_full | sequence_runner | page-load-failure | render_failure |  |  |  |
| cell_seeding_plate_setup | mini_protocol | populated | unsupported_gesture | calculate_dilution_volume | serological_pipette | adjust |
| drug_dilution_setup | mini_protocol | populated | unsupported_gesture | prepare_carb_parent_stock | micropipette | adjust |
| mtt_plate_reaction | mini_protocol | populated | missing_object |  | well_plate_96 |  |
| mtt_reagent_prep | mini_protocol | populated | unsupported_gesture | prepare_solution_tube | micropipette | adjust |
| mtt_solubilization_readout | mini_protocol | populated | unsupported_gesture | add_dmso_to_wells | micropipette | adjust |
| passage_hood_detachment | mini_protocol | populated | missing_object |  | hood_surface |  |
| passage_pellet_reseed | mini_protocol | populated | other | transfer_to_conical |  |  |
| plate_drug_treatment_drug_addition | mini_protocol | populated | unsupported_gesture | add_carb_row_b | micropipette | adjust |
| plate_drug_treatment_media_adjustment | mini_protocol | populated | unsupported_gesture | adjust_media_quadrant_a1_h6 | multichannel_pipette | adjust |
| routine_passage | sequence_runner | page-load-failure | render_failure |  |  |  |
| sdspage_assemble_electrode_module | mini_protocol | populated | completed |  |  |  |
| sdspage_attach_lid_and_leads | mini_protocol | populated | completed |  |  |  |
| sdspage_destain_gel_rock | mini_protocol | populated | unsupported_gesture | rock_run | rocking_shaker | adjust |
| sdspage_destain_gel_setup | mini_protocol | populated | missing_object |  | kimwipe_pad |  |
| sdspage_extract_gel_from_cassette | mini_protocol | populated | completed |  |  |  |
| sdspage_fill_tank_buffer | mini_protocol | populated | unsupported_gesture | fill_inner_chamber | serological_pipette | adjust |
| sdspage_full | sequence_runner | page-load-failure | render_failure |  |  |  |
| sdspage_heat_denature_samples | mini_protocol | populated | completed |  |  |  |
| sdspage_image_gel | mini_protocol | populated | missing_object |  | waste_container |  |
| sdspage_load_protein_ladder | mini_protocol | populated | unsupported_gesture | set_micropipette_volume | p200_micropipette | adjust |
| sdspage_load_sample_single_lane | mini_protocol | populated | unsupported_gesture | draw_sample | p200_micropipette | adjust |
| sdspage_load_samples_batch | sequence_runner | page-load-failure | render_failure |  |  |  |
| sdspage_prepare_gel_cassette | mini_protocol | populated | completed |  |  |  |
| sdspage_prepare_running_buffer | mini_protocol | populated | unsupported_gesture | dilute_10x_concentrate | serological_pipette | adjust |
| sdspage_prepare_sample_mix_batch | sequence_runner | page-load-failure | render_failure |  |  |  |
| sdspage_prepare_sample_mix_single_lane | mini_protocol | populated | unsupported_gesture | add_protein_sample | micropipette | adjust |
| sdspage_recycle_buffer | mini_protocol | populated | completed |  |  |  |
| sdspage_run_electrophoresis | mini_protocol | populated | unsupported_gesture | set_voltage | power_supply | adjust |
| sdspage_stain_gel | mini_protocol | populated | completed |  |  |  |
| trypan_blue_counting | mini_protocol | populated | unsupported_gesture | add_trypan_blue_to_chamber | micropipette | adjust |

## Completed protocols

- **sdspage_assemble_electrode_module**: 4 steps passed, ? clicks, no console errors
- **sdspage_attach_lid_and_leads**: 1 steps passed, ? clicks, no console errors
- **sdspage_extract_gel_from_cassette**: 5 steps passed, ? clicks, no console errors
- **sdspage_heat_denature_samples**: 4 steps passed, ? clicks, no console errors
- **sdspage_prepare_gel_cassette**: 4 steps passed, ? clicks, no console errors
- **sdspage_recycle_buffer**: 3 steps passed, ? clicks, no console errors
- **sdspage_stain_gel**: 5 steps passed, ? clicks, no console errors

## Render failures (sequence runners)

All 5 render failures are `sequence_runner` protocols.
Error: `Unknown step_name in protocol` -- the sequence runner references a step_name from a constituent mini-protocol that does not exist in the runner's own steps list.

- **cell_culture_full**: page.waitForFunction: Timeout 30000ms exceeded.
- **routine_passage**: page.waitForFunction: Timeout 30000ms exceeded.
- **sdspage_full**: page.waitForFunction: Timeout 30000ms exceeded.
- **sdspage_load_samples_batch**: page.waitForFunction: Timeout 30000ms exceeded.
- **sdspage_prepare_sample_mix_batch**: page.waitForFunction: Timeout 30000ms exceeded.

## Unsupported gesture (adjust)

All 14 unsupported_gesture failures are `adjust` gesture -- the new host has no visible affordance for set-point controls yet.

- **cell_seeding_plate_setup**: step `calculate_dilution_volume`, target `serological_pipette`, gesture `adjust`
- **drug_dilution_setup**: step `prepare_carb_parent_stock`, target `micropipette`, gesture `adjust`
- **mtt_reagent_prep**: step `prepare_solution_tube`, target `micropipette`, gesture `adjust`
- **mtt_solubilization_readout**: step `add_dmso_to_wells`, target `micropipette`, gesture `adjust`
- **plate_drug_treatment_drug_addition**: step `add_carb_row_b`, target `micropipette`, gesture `adjust`
- **plate_drug_treatment_media_adjustment**: step `adjust_media_quadrant_a1_h6`, target `multichannel_pipette`, gesture `adjust`
- **sdspage_destain_gel_rock**: step `rock_run`, target `rocking_shaker`, gesture `adjust`
- **sdspage_fill_tank_buffer**: step `fill_inner_chamber`, target `serological_pipette`, gesture `adjust`
- **sdspage_load_protein_ladder**: step `set_micropipette_volume`, target `p200_micropipette`, gesture `adjust`
- **sdspage_load_sample_single_lane**: step `draw_sample`, target `p200_micropipette`, gesture `adjust`
- **sdspage_prepare_running_buffer**: step `dilute_10x_concentrate`, target `serological_pipette`, gesture `adjust`
- **sdspage_prepare_sample_mix_single_lane**: step `add_protein_sample`, target `micropipette`, gesture `adjust`
- **sdspage_run_electrophoresis**: step `set_voltage`, target `power_supply`, gesture `adjust`
- **trypan_blue_counting**: step `add_trypan_blue_to_chamber`, target `micropipette`, gesture `adjust`

## Missing objects

- **mtt_plate_reaction**: `well_plate_96` not in DOM (step `None`)
- **passage_hood_detachment**: `hood_surface` not in DOM (step `None`)
- **sdspage_destain_gel_setup**: `kimwipe_pad` not in DOM (step `None`)
- **sdspage_image_gel**: `waste_container` not in DOM (step `None`)

## Other failures

- **passage_pellet_reseed**: Step failed: transfer_to_conical - no_active_interaction: step transfer_to_conical has no active target/gesture but is still active
