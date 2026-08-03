# Legacy material-binding disposition audit

## Scope and method

This is the M6 closure record for the historical object-level effect surface.
It is deliberately based on repository evidence, not on asset names or visual
guessing:

```sh
git grep -l 'render_effect: fill_height\|render_effect: material_tint' HEAD -- content/objects
source source_me.sh && python3 -m pytest tests/test_material_effect_retirement.py -q
```

The first command identifies the 48 historical effect-bearing object YAMLs:
46 object-level `fill_height` effects and two structured `material_tint`
effects. Current YAML and the recursive SVG registry determine each final
form/mechanism below. The companion M6 regression test proves that every
current object-level amount binding selects a registered material-rendered
variable-volume form and that all five such forms are selected.

There were also four formula-only `fill_height(...)` structured-subpart
entries. They were not among the 48 object-level render effects, so they are
listed separately rather than silently disappearing from the audit.

## Historical object-level effect dispositions

| Historical object YAML | Final category | Final selected form or mechanism |
| --- | --- | --- |
| `content/objects/bottle/bme_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/carboplatin_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/cell_suspension_tube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/conical_15ml.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/conical_tube_for_dilution.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/coomassie_recycle_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/coomassie_stain_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/ddh2o_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/ddh2o_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/destain_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/destain_waste_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/dmso_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/ethanol_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/laemmli_4x_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/media_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/metformin_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/metformin_working_tube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/microtube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/microtube_15ml_intermediate.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/mtt_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/pbs_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/recycle_buffer_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_10x_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_1x_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_preparation_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/sterile_water_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/trypan_blue_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/trypsin_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/pipette/serological_pipette.yaml` | true variable-volume | `serological_pipette`; compiled material gravity parts |
| `content/objects/bottle/protein_ladder_tube.yaml` | discrete complete-form | `protein_ladder_tube_empty` or `protein_ladder_tube_filled` |
| `content/objects/bottle/protein_sample_tube.yaml` | discrete complete-form | `protein_sample_tube_empty` or `protein_sample_tube_filled` |
| `content/objects/equipment/staining_tray.yaml` | discrete complete-form | `staining_tray_empty`, `staining_tray_buffer`, `staining_tray_stain`, `staining_tray_destain`, or `staining_tray_water` |
| `content/objects/flask/t75_flask.yaml` | discrete complete-form | `t75_flask_empty` or `t75_flask_filled` |
| `content/objects/flask/t75_flask_new.yaml` | discrete complete-form | `t75_flask_empty` or `t75_flask_filled` |
| `content/objects/bottle/mtt_solution_tube.yaml` | invalid legacy effect | static `mtt_vial`; amount remains state only |
| `content/objects/bottle/mtt_vial.yaml` | invalid legacy effect | static `mtt_vial`; amount remains state only |
| `content/objects/equipment/electrophoresis_inner_chamber.yaml` | invalid legacy effect | static `electrophoresis_tank_inner_chamber`; amount remains state only |
| `content/objects/equipment/electrophoresis_outer_chamber.yaml` | invalid legacy effect | static `electrophoresis_tank_outer_chamber`; amount remains state only |
| `content/objects/pipette/aspirating_pipette.yaml` | invalid legacy effect | static `aspirating_pipette`; aspirated amount is not visual volume |
| `content/objects/pipette/micropipette.yaml` | invalid legacy effect | static `p200_micropipette_empty`; setpoint remains text overlay |
| `content/objects/pipette/multichannel_pipette.yaml` | invalid legacy effect | static `multichannel_pipette`; setpoint remains text overlay |
| `content/objects/pipette/p10_micropipette.yaml` | invalid legacy effect | static `p10_micropipette_empty`; setpoint remains text overlay |
| `content/objects/pipette/p200_micropipette.yaml` | invalid legacy effect | static `p200_micropipette_empty`; setpoint remains text overlay |
| `content/objects/waste/biohazard_decant.yaml` | invalid legacy effect | static `biohazard_decant`; amount remains state only |
| `content/objects/waste/biohazard_decant_bin.yaml` | invalid legacy effect | static `biohazard_decant_bin`; amount remains state only |
| `content/objects/waste/waste_container.yaml` | invalid legacy effect | static `waste_container`; amount remains state only |
| `content/objects/equipment/hemocytometer_slide.yaml` | structured concern | `material_tint` on generated chamber geometry; amount is explicit no-op |
| `content/objects/plate/well_plate_96.yaml` | structured concern | `material_tint` on generated well geometry; amount is explicit no-op |

Totals: 29 true variable-volume, five discrete complete-form, two structured
concerns, and 12 invalid legacy effects = 48 historical effect-bearing object
YAMLs.

## Formula-only structured-subpart dispositions

| Historical object YAML | Final category | Final selected form or mechanism |
| --- | --- | --- |
| `content/objects/equipment/gel_cassette.yaml` | structured concern | lane amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/conical_15ml_rack.yaml` | structured concern | slot amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/dilution_tube_rack_8.yaml` | structured concern | tube amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/microtube_rack_8.yaml` | structured concern | tube amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |

## Final invariant

Object-level `fill_height` is now reserved for the five compiled,
material-rendered gravity-part SVG forms. All other forms are selected as
complete SVGs, remain static while retaining protocol state, or use the
separate structured-subpart mechanism. No ordinary SVG receives a whole-object
liquid effect.
