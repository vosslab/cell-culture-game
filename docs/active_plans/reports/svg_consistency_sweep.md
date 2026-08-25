# SVG consistency sweep ledger

## Baseline and disposition

This is the operational inventory for the de-shadowed Servier consistency
sweep. It records the baseline discovered by
`source source_me.sh && python3 validation/svg/asset_audit.py --json` on
2026-08-24. It is a planning and review ledger, not a second SVG behavioral
specification; [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) remains canonical.

<!-- prettier-ignore -->
| Baseline SVGs | Edit | Delete | Preserve and defer |
| ---: | ---: | ---: | ---: |
| 186 | 139 | 40 | 7 |

- **edit:** retain the named source SVG and revise it to the visual acceptance
  dialect; filenames, selected object bindings, semantic anchors, and material
  declarations remain stable.
- **delete:** approved M1 cleanup deletion. Each name is an exact current
  `cleanup_surface.orphans` advisory. Re-run the audit and confirm no new
  authored reference before removal.
- **defer:** preserve the source SVG unchanged in this sweep. These are
  overloaded result composites whose application-owned migration is documented
  in the [SVG interface scope audit](../audits/svg_embedded_interface_scope.md).

## Workstream ownership

<!-- prettier-ignore -->
| Workstream | Owns | Completion evidence |
| --- | --- | --- |
| M1 cleanup | Approved orphan deletions | Fresh asset audit and reachability proof |
| WS-A vessels | Variable-volume material forms | Semantic anchors/roles preserved and volume renders |
| WS-B state families and instruments | Binary/multi-state families and listed instruments | Stable family canvas/viewBox and visible state distinction |
| WS-C tools and consumables | Retained static physical objects | Small- and source-scale render review |
| WS-D evidence | Language-neutral observation/evidence art | Small- and source-scale render review; no student-facing prose |
| result migration | Seven result composites | Out of scope; unchanged checksum during sweep |

The sweep applies the de-shadowed Servier Medical Art dialect in
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md): Servier is the sole Bioicons
style reference, detached floor shadows are removed narrowly, local form
shading is reduced rather than flattened, and original replacement art follows
that grammar without copying an unrelated icon.

## Baseline asset rows

<!-- prettier-ignore -->
| Source SVG | Disposition | Owner |
| --- | --- | --- |
| `binary_state/cell_counter_instrument.svg` | edit | WS-B state families |
| `binary_state/cell_counter_result.svg` | edit | WS-B state families |
| `binary_state/centrifuge.svg` | edit | WS-B state families |
| `binary_state/centrifuge_balance_tube_empty.svg` | edit | WS-B state families |
| `binary_state/centrifuge_balance_tube_matched.svg` | edit | WS-B state families |
| `binary_state/centrifuge_running.svg` | edit | WS-B state families |
| `binary_state/electrode_module_closed.svg` | edit | WS-B state families |
| `binary_state/electrode_module_open.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_black_lead_attached.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_black_lead_unattached.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_buffer_dam.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_buffer_dam_seated.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_red_lead_attached.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_red_lead_unattached.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_tank_lidded.svg` | edit | WS-B state families |
| `binary_state/electrophoresis_tank_open.svg` | edit | WS-B state families |
| `binary_state/gel_comb.svg` | edit | WS-B state families |
| `binary_state/gel_comb_in_cassette.svg` | edit | WS-B state families |
| `binary_state/gel_opening_tool.svg` | edit | WS-B state families |
| `binary_state/gel_opening_tool_hidden.svg` | edit | WS-B state families |
| `binary_state/hazardous_liquid_waste_empty.svg` | edit | WS-B state families |
| `binary_state/hazardous_liquid_waste_filled.svg` | edit | WS-B state families |
| `binary_state/heat_block_closed.svg` | edit | WS-B state families |
| `binary_state/heat_block_open.svg` | edit | WS-B state families |
| `binary_state/hood_workspace_surface.svg` | edit | WS-B state families |
| `binary_state/hood_workspace_surface_clean.svg` | edit | WS-B state families |
| `binary_state/lightbox_off.svg` | edit | WS-B state families |
| `binary_state/lightbox_on.svg` | edit | WS-B state families |
| `binary_state/microwave_closed.svg` | edit | WS-B state families |
| `binary_state/microwave_heating.svg` | edit | WS-B state families |
| `binary_state/mini_protean_gel.svg` | edit | WS-B state families |
| `binary_state/mini_protean_gel_unsealed.svg` | edit | WS-B state families |
| `binary_state/mtt_powder_vial.svg` | edit | WS-B state families |
| `binary_state/mtt_powder_vial_empty.svg` | edit | WS-B state families |
| `binary_state/p1000_micropipette_empty.svg` | edit | WS-B state families |
| `binary_state/p1000_micropipette_filled.svg` | edit | WS-B state families |
| `binary_state/p200_micropipette_loaded.svg` | edit | WS-B state families |
| `binary_state/p200_micropipette_unloaded.svg` | edit | WS-B state families |
| `binary_state/p20_micropipette_empty.svg` | edit | WS-B state families |
| `binary_state/p20_micropipette_filled.svg` | edit | WS-B state families |
| `binary_state/plate_reader_idle.svg` | edit | WS-B state families |
| `binary_state/plate_reader_reading.svg` | edit | WS-B state families |
| `binary_state/power_supply_off.svg` | edit | WS-B state families |
| `binary_state/power_supply_on.svg` | edit | WS-B state families |
| `binary_state/protein_ladder_tube_empty.svg` | edit | WS-B state families |
| `binary_state/protein_ladder_tube_filled.svg` | edit | WS-B state families |
| `binary_state/protein_sample_tube_empty.svg` | edit | WS-B state families |
| `binary_state/protein_sample_tube_filled.svg` | edit | WS-B state families |
| `binary_state/reagent_reservoir_empty.svg` | edit | WS-B state families |
| `binary_state/reagent_reservoir_filled.svg` | edit | WS-B state families |
| `binary_state/repeat_dispenser_empty.svg` | edit | WS-B state families |
| `binary_state/repeat_dispenser_loaded.svg` | edit | WS-B state families |
| `binary_state/rocking_shaker_idle.svg` | edit | WS-B state families |
| `binary_state/rocking_shaker_running.svg` | edit | WS-B state families |
| `binary_state/serological_pipette_pack_available.svg` | edit | WS-B state families |
| `binary_state/serological_pipette_pack_depleted.svg` | edit | WS-B state families |
| `binary_state/sharps_container.svg` | edit | WS-B state families |
| `binary_state/sharps_container_full.svg` | edit | WS-B state families |
| `binary_state/t75_flask_empty.svg` | edit | WS-B state families |
| `binary_state/t75_flask_filled.svg` | edit | WS-B state families |
| `binary_state/water_bath.svg` | edit | WS-B state families |
| `binary_state/water_bath_occupied.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_inner_chamber_empty.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_inner_chamber_filled.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_inner_chamber_leak_checked.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_inner_chamber_partial.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_outer_chamber_empty.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_outer_chamber_filled.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_outer_chamber_leak_checked.svg` | edit | WS-B state families |
| `multi_state/electrophoresis_outer_chamber_partial.svg` | edit | WS-B state families |
| `multi_state/gel_cassette_destained.svg` | edit | WS-B state families |
| `multi_state/gel_cassette_destaining.svg` | edit | WS-B state families |
| `multi_state/gel_cassette_empty.svg` | edit | WS-B state families |
| `multi_state/gel_cassette_separated_unstained.svg` | edit | WS-B state families |
| `multi_state/gel_cassette_stained.svg` | edit | WS-B state families |
| `multi_state/staining_tray_buffer.svg` | edit | WS-B state families |
| `multi_state/staining_tray_destain.svg` | edit | WS-B state families |
| `multi_state/staining_tray_empty.svg` | edit | WS-B state families |
| `multi_state/staining_tray_stain.svg` | edit | WS-B state families |
| `multi_state/staining_tray_water.svg` | edit | WS-B state families |
| `static/96well_pcr_plate.svg` | edit | WS-C tools and consumables |
| `static/angry_professor.svg` | edit | WS-C tools and consumables |
| `static/aspirating_pipette.svg` | edit | WS-B instruments |
| `static/biohazard_decant.svg` | edit | WS-B instruments |
| `static/biohazard_decant_bin.svg` | edit | WS-B instruments |
| `static/bottle.svg` | delete | M1 cleanup |
| `static/bottle_green.svg` | delete | M1 cleanup |
| `static/bottle_orange.svg` | delete | M1 cleanup |
| `static/bottle_pink.svg` | delete | M1 cleanup |
| `static/calculation_pad.svg` | edit | WS-D evidence |
| `static/cell_counter_manual_live_dead_panel.svg` | edit | WS-D evidence |
| `static/cell_counter_manual_quadrants_panel.svg` | edit | WS-D evidence |
| `static/cell_viability_results_display.svg` | defer | result migration |
| `static/centrifuge_new.svg` | delete | M1 cleanup |
| `static/conical_15ml_rack.svg` | delete | M1 cleanup |
| `static/counter_slide_cartridge.svg` | edit | WS-C tools and consumables |
| `static/dilution_tube_rack.svg` | edit | WS-C tools and consumables |
| `static/drug_vial_rack.svg` | delete | M1 cleanup |
| `static/electrode_module.svg` | delete | M1 cleanup |
| `static/electrophoresis_endpoint_display.svg` | defer | result migration |
| `static/electrophoresis_tank.svg` | delete | M1 cleanup |
| `static/electrophoresis_tank_inner_chamber.svg` | delete | M1 cleanup |
| `static/electrophoresis_tank_module_mounted.svg` | edit | WS-B instruments |
| `static/electrophoresis_tank_outer_chamber.svg` | delete | M1 cleanup |
| `static/ethanol_spray.svg` | delete | M1 cleanup |
| `static/gel_cassette_bottom_tape.svg` | edit | WS-C tools and consumables |
| `static/gel_cassette_comb_inserted.svg` | edit | WS-C tools and consumables |
| `static/gel_cassette_side_clamps_locked.svg` | edit | WS-C tools and consumables |
| `static/gel_cassette_top_plate_removed.svg` | edit | WS-C tools and consumables |
| `static/gel_cassette_wing_clamps_locked.svg` | edit | WS-C tools and consumables |
| `static/gel_image_results_display.svg` | defer | result migration |
| `static/gel_loading_tip_box.svg` | edit | WS-C tools and consumables |
| `static/gel_migration_near_bottom.svg` | edit | WS-D evidence |
| `static/gel_migration_not_started.svg` | edit | WS-D evidence |
| `static/gel_migration_overrun.svg` | edit | WS-D evidence |
| `static/gel_migration_running.svg` | edit | WS-D evidence |
| `static/heat_block_rack.svg` | edit | WS-B instruments |
| `static/hemocytometer_live_dead_cells_visible.svg` | edit | WS-D evidence |
| `static/hemocytometer_observation_display.svg` | defer | result migration |
| `static/hemocytometer_quadrants_counted.svg` | edit | WS-D evidence |
| `static/hemocytometer_slide.svg` | edit | WS-D evidence |
| `static/incubator.svg` | edit | WS-B instruments |
| `static/incubator_new.svg` | delete | M1 cleanup |
| `static/interpretation_choice_card.svg` | edit | WS-D evidence |
| `static/kimwipe_pad.svg` | edit | WS-C tools and consumables |
| `static/label_pen.svg` | edit | WS-C tools and consumables |
| `static/lens_tissue.svg` | edit | WS-C tools and consumables |
| `static/lightbox_capture_complete.svg` | edit | WS-D evidence |
| `static/lightbox_gel_destained.svg` | edit | WS-D evidence |
| `static/lightbox_gel_destaining.svg` | edit | WS-D evidence |
| `static/lightbox_gel_separated_unstained.svg` | edit | WS-D evidence |
| `static/lightbox_gel_stained.svg` | edit | WS-D evidence |
| `static/lightbox_gel_tray.svg` | edit | WS-D evidence |
| `static/lightbox_image_bands_visible.svg` | edit | WS-D evidence |
| `static/lightbox_image_molecular_weight_scale.svg` | edit | WS-D evidence |
| `static/micropipette_rack.svg` | delete | M1 cleanup |
| `static/microscope.svg` | edit | WS-B instruments |
| `static/microscope_field_confluent_70_80.svg` | edit | WS-D evidence |
| `static/microscope_field_rounded_detached.svg` | edit | WS-D evidence |
| `static/microscope_new.svg` | delete | M1 cleanup |
| `static/microtube_empty.svg` | delete | M1 cleanup |
| `static/microtube_filled.svg` | delete | M1 cleanup |
| `static/microtube_open_translucent.svg` | delete | M1 cleanup |
| `static/microtube_rack_24_placeholder.svg` | delete | M1 cleanup |
| `static/microtube_rack_8.svg` | edit | WS-C tools and consumables |
| `static/mtt_reader_results_display.svg` | defer | result migration |
| `static/mtt_vial.svg` | edit | WS-C tools and consumables |
| `static/multichannel_pipette.svg` | edit | WS-B instruments |
| `static/multichannel_pipette_new.svg` | delete | M1 cleanup |
| `static/p10_gel_loading_tip.svg` | edit | WS-C tools and consumables |
| `static/p10_gel_loading_tip_box.svg` | edit | WS-C tools and consumables |
| `static/p10_micropipette_empty.svg` | edit | WS-C tools and consumables |
| `static/p10_micropipette_filled.svg` | delete | M1 cleanup |
| `static/p200_micropipette_empty.svg` | delete | M1 cleanup |
| `static/p200_micropipette_filled.svg` | delete | M1 cleanup |
| `static/paper_towel_pad.svg` | edit | WS-C tools and consumables |
| `static/plate_reader.svg` | delete | M1 cleanup |
| `static/plate_reader_absorbance_result_panel.svg` | defer | result migration |
| `static/plate_reader_new.svg` | delete | M1 cleanup |
| `static/plate_reader_normalized_viability_panel.svg` | defer | result migration |
| `static/protein_ladder_tube.svg` | delete | M1 cleanup |
| `static/protein_sample_tube.svg` | delete | M1 cleanup |
| `static/recycle_buffer_funnel.svg` | edit | WS-C tools and consumables |
| `static/running_buffer_1x_carboy.svg` | delete | M1 cleanup |
| `static/running_buffer_1x_carboy_empty.svg` | delete | M1 cleanup |
| `static/running_buffer_1x_carboy_filled.svg` | delete | M1 cleanup |
| `static/t75_flask.svg` | delete | M1 cleanup |
| `static/t75_flask_servier.svg` | delete | M1 cleanup |
| `static/t75_flask_v2.svg` | delete | M1 cleanup |
| `static/t75_flask_v3.svg` | delete | M1 cleanup |
| `static/t75_flask_v4.svg` | delete | M1 cleanup |
| `static/t75_flask_v5.svg` | delete | M1 cleanup |
| `static/tip_box.svg` | edit | WS-C tools and consumables |
| `static/tip_box_new.svg` | delete | M1 cleanup |
| `static/tube_rack.svg` | edit | WS-C tools and consumables |
| `static/vortex.svg` | edit | WS-B instruments |
| `static/waste_container.svg` | edit | WS-C tools and consumables |
| `static/waste_tray.svg` | delete | M1 cleanup |
| `static/water_bath_new.svg` | delete | M1 cleanup |
| `static/well_plate_24.svg` | delete | M1 cleanup |
| `static/well_plate_formazan_crystals.svg` | edit | WS-D evidence |
| `variable_volume/bottle_medium_pink.svg` | edit | WS-A vessels |
| `variable_volume/falcon_15ml.svg` | edit | WS-A vessels |
| `variable_volume/falcon_50ml.svg` | edit | WS-A vessels |
| `variable_volume/microtube.svg` | edit | WS-A vessels |
| `variable_volume/serological_pipette.svg` | edit | WS-A vessels |

## Deferred result composites

The following seven files are intentionally not edited, normalized, renamed,
or deleted by this sweep:

<!-- prettier-ignore -->
| Source SVG | Baseline SHA-256 |
| --- | --- |
| `static/cell_viability_results_display.svg` | `54cf24b73c687828337ec8b200bf81f20563a495a3b6524d306b0c0ebd3429fb` |
| `static/electrophoresis_endpoint_display.svg` | `2d8a0147715f69a28edd817d2b7505e28a7712431c6b2c5fa945c390765aa7fc` |
| `static/gel_image_results_display.svg` | `5e3d51aa52f2fe816201c6f444ab8289179859448891738cd2e644657cbcc8dc` |
| `static/hemocytometer_observation_display.svg` | `ebe1ebb3ee5a2e8e3ad87f3fabd7f9f86831755553b2bf3ee81e06b668985358` |
| `static/mtt_reader_results_display.svg` | `de60bd7474619c68dd5d6b5dec67d62e78ab33183778d47beca8cc91d0bd734a` |
| `static/plate_reader_absorbance_result_panel.svg` | `ef0d9352c691dfadbf652163de4e02885d127033a57fc48ff2ac4ecadecc296d` |
| `static/plate_reader_normalized_viability_panel.svg` | `39a9c97ae98e8833b9df7e595b75b6a8a65ad34c2ffeea6a54c1ec6ed0457487` |

After every integrated wave, run this command from the repository root and
compare its seven hashes with the table; halt integration if any differs:

```sh
shasum -a 256 assets/equipment/static/{cell_viability_results_display,electrophoresis_endpoint_display,gel_image_results_display,hemocytometer_observation_display,mtt_reader_results_display,plate_reader_absorbance_result_panel,plate_reader_normalized_viability_panel}.svg
```

Their migration is explicitly deferred in [TODO.md](../../TODO.md) and
[ROADMAP.md](../../ROADMAP.md). The scope audit, not this asset sweep, owns
the future decision about typed result state and application UI.

## Per-wave closeout

For every edited row, attach a before/after source render and a production
scene render to the workstream handoff. Validate XML/reference health,
normalization, family geometry, material semantics where applicable, and
learner-facing language boundaries. Do not use pixel-equivalence as a visual
quality gate. After each integrated wave, regenerate the inventory and reconcile
this table before proceeding to the next one.

## Final closeout

- Final disposition: 139 retained SVGs modified, 40 retired SVGs deleted, and
  seven result composites byte-preserved.
- The final asset audit reports 131 objects, 146 SVGs, and zero findings.
- The material baseline was intentionally refreshed after visual review; the
  production material contact sheet passed.
- `./run_playwright_tests.sh` passed 115/115 and `./super_all_tests.sh` passed
  20/20.
- Those delivery counts describe the SVG-sweep tree before the later vendored
  template refresh. Combined-tree revalidation remains pending until the
  vendored permanent-test blockers are resolved.
- The labeled all-SVG contact sheet is published at
  [final_equipment_contact_sheet.svg](../../figures/final_equipment_contact_sheet.svg)
  as the final review artifact. Human visual acceptance remains pending.
