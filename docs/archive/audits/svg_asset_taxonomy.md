# SVG Asset Taxonomy Audit

## Purpose

This M2 evidence record separates an SVG form's selection model from its rendering
model. It deliberately derives collections from object YAML `visual_states`, rather
than guessing from filenames. It does not change existing assets, paths, or object
bindings.

## Method and evidence

Commands run from the repository root on 2026-07-31:

```sh
find assets/equipment -maxdepth 1 -name '*.svg' | wc -l
source source_me.sh && python3 - <<'PY'
# Parse every content/objects YAML file with PyYAML; collect kind: svg case
# outputs, render_effect declarations, and their object_name.
PY
rg -n "assets/equipment|ASSETS_DIR.*equipment|equipment.*\\.svg" \
  pipeline validation tools/svg_picker tests docs/{CODE_ARCHITECTURE.md,FILE_STRUCTURE.md,SVG_ATTRIBUTION.md,THIRD_PARTY_ASSETS.md,USAGE.md}
```

Results:

- `assets/equipment/` contains 117 SVG source files, each with a unique stem.
- 78 stems are referenced by at least one `kind: svg` object visual state; 39
  files have no current object reference.
- Object YAML declares 18 discrete collections containing 39 distinct forms.
- 48 object files declare the legacy material effects (`fill_height` or
  `material_tint`). Those references reach 27 distinct SVG forms. They are
  *material-rendering candidates*, not currently self-describing material-rendered
  SVGs: no source SVG presently declares the proposed semantic contract.
- Only `staining_tray` combines a multi-form collection and a material effect. Its
  selected form is chosen by `gel_state`; the current effect still applies at object
  scope. Consequently, current YAML cannot state whether one selected form is static
  while another is material-rendered. The future per-form semantic SVG declaration is
  needed to express that distinction.

The collection result comes from the actual `kind: svg` case maps. In particular,
the five staining-tray forms are a collection even though `material_name` itself
always selects `staining_tray_empty`; `gel_state` is the later SVG selection in the
runtime's authored-order resolver.

## Taxonomy interpretation

| Axis | Existing authoritative evidence | Target authority |
| --- | --- | --- |
| Selection | Object YAML `visual_states.<field>.kind: svg` case outputs | The same object YAML case maps |
| Rendering | Legacy object-level `render_effect` reaches a selected SVG, but does not classify individual forms | Each material-rendered SVG's validated root semantic declaration |

Thus the current source does not contain a confirmed material-rendered SVG under the
new definition. It contains 27 forms that must be considered candidates during
conversion. A form with no material declaration remains static, whether it is a
single asset or selected from a collection.

## Discrete collections derived from `visual_states`

All forms below are currently static under the future taxonomy except the
`staining_tray` candidate collection. `mtt_powder_container` and
`sharps_container` select complete art for content state but have no material render
effect, so they remain ordinary discrete forms.

| Object collection | Selecting field(s) | Complete SVG forms | Current rendering evidence |
| --- | --- | --- | --- |
| `cell_counter` | `slide_loaded`, `capture_pressed` | `cell_counter_instrument`, `cell_counter_result` | static |
| `centrifuge` | `running` | `centrifuge`, `centrifuge_running` | static |
| `electrode_module` | `wing_clamps_open` | `electrode_module_open`, `electrode_module_closed` | static |
| `electrophoresis_tank` | `lid_present` | `electrophoresis_tank_open`, `electrophoresis_tank_lidded` | static |
| `gel_comb` | `position` | `gel_comb`, `gel_comb_in_cassette` | static |
| `gel_opening_tool` | `visible` | `gel_opening_tool`, `gel_opening_tool_hidden` | static |
| `heat_block` | `lid_open` | `heat_block_closed`, `heat_block_open` | static |
| `hood_surface` | `surface_cleanliness` | `hood_workspace_surface`, `hood_workspace_surface_clean` | static |
| `lightbox` | `powered_on` | `lightbox_off`, `lightbox_on` | static |
| `microwave` | `running` | `microwave_closed`, `microwave_heating` | static |
| `mini_protean_gel` | `sealed` | `mini_protean_gel`, `mini_protean_gel_unsealed` | static |
| `mtt_powder_container` | `material_name` | `mtt_powder_vial`, `mtt_powder_vial_empty` | static |
| `plate_reader` | `reading` | `plate_reader_idle`, `plate_reader_reading` | static |
| `power_supply` | `running` | `power_supply_off`, `power_supply_on` | static; its numeric display is an object text overlay |
| `rocking_shaker` | `running` | `rocking_shaker_idle`, `rocking_shaker_running` | static |
| `sharps_container` | `material_name` | `sharps_container`, `sharps_container_full` | static |
| `staining_tray` | `material_name`, `gel_state` | `staining_tray_empty`, `staining_tray_buffer`, `staining_tray_stain`, `staining_tray_destain`, `staining_tray_water` | all five are material-rendering candidates; no per-form distinction is currently authored |
| `water_bath` | `vessels_present` | `water_bath`, `water_bath_occupied` | static |

There is no confirmed mixed static/material collection in today's assets, because
the new material semantic declaration does not exist yet. The staining tray is the
only collection requiring a deliberate M3 classification of every selected form;
it must be either all material-rendered or split explicitly by per-form declarations.
It must not inherit capability merely from collection membership.

## All SVG forms and current classification evidence

Every entry is `assets/equipment/<asset_name>.svg`. `single` means the form is not a
member of a multi-form collection in current object YAML. `candidate` means an object
with a legacy material render effect reaches it; it is not a claim that the file already
has material semantics. A dash means there is no current object reference.

| Asset name | Selection | Rendering evidence | Object references |
| --- | --- | --- | --- |
| `96well_pcr_plate` | single | candidate | `well_plate_96` |
| `angry_professor` | single | static | `professor_avatar` |
| `aspirating_pipette` | single | candidate | `aspirating_pipette` |
| `biohazard_decant` | single | candidate | `biohazard_decant` |
| `biohazard_decant_bin` | single | candidate | `biohazard_decant_bin` |
| `bottle`, `bottle_medium_pink` | single | static | - |
| `bottle_green` | single | candidate | 12 bottle/carboy objects |
| `bottle_orange` | single | candidate | `ethanol_bottle` |
| `bottle_pink` | single | candidate | `media_bottle`, `trypsin_bottle` |
| `cell_counter_instrument`, `cell_counter_result` | collection: `cell_counter` | static | `cell_counter` |
| `centrifuge`, `centrifuge_running` | collection: `centrifuge` | static | `centrifuge` |
| `centrifuge_new`, `conical_15ml_rack`, `drug_vial_rack` | single | static | - |
| `counter_slide_cartridge`, `dilution_tube_rack`, `gel_cassette`, `gel_loading_tip_box` | single | static | named matching object |
| `electrode_module` | single | static | - |
| `electrode_module_closed`, `electrode_module_open` | collection: `electrode_module` | static | `electrode_module` |
| `electrophoresis_tank` | single | static | - |
| `electrophoresis_tank_inner_chamber`, `electrophoresis_tank_outer_chamber` | single | candidate | corresponding chamber object |
| `electrophoresis_tank_lidded`, `electrophoresis_tank_open` | collection: `electrophoresis_tank` | static | `electrophoresis_tank` |
| `ethanol_spray`, `heat_block_rack`, `incubator_new`, `lightbox_capture_complete`, `lightbox_gel_tray` | single | static | - |
| `falcon_15ml` | single | candidate | six liquid objects plus `conical_15ml_rack` |
| `falcon_50ml` | single | candidate | four liquid objects |
| `gel_comb`, `gel_comb_in_cassette` | collection: `gel_comb` | static | `gel_comb` |
| `gel_opening_tool`, `gel_opening_tool_hidden` | collection: `gel_opening_tool` | static | `gel_opening_tool` |
| `heat_block_closed`, `heat_block_open` | collection: `heat_block` | static | `heat_block` |
| `hemocytometer_slide` | single | candidate | `hemocytometer_slide` |
| `hood_workspace_surface`, `hood_workspace_surface_clean` | collection: `hood_surface` | static | `hood_surface` |
| `incubator`, `kimwipe_pad`, `label_pen`, `lens_tissue` | single | static | named matching object |
| `lightbox_off`, `lightbox_on` | collection: `lightbox` | static | `lightbox` |
| `micropipette_rack`, `microscope_new`, `multichannel_pipette_new` | single | static | - |
| `microscope` | single | static | `microscope` |
| `microtube` | single | candidate | three liquid objects |
| `microtube_empty`, `microtube_filled`, `microtube_open_translucent`, `microtube_rack_24_placeholder` | single | static | - |
| `microtube_rack_8` | single | static | `microtube_rack_8` |
| `microwave_closed`, `microwave_heating` | collection: `microwave` | static | `microwave` |
| `mini_protean_gel`, `mini_protean_gel_unsealed` | collection: `mini_protean_gel` | static | `mini_protean_gel` |
| `mtt_powder_vial`, `mtt_powder_vial_empty` | collection: `mtt_powder_container` | static | `mtt_powder_container` |
| `mtt_vial` | single | candidate | `mtt_solution_tube`, `mtt_vial` |
| `multichannel_pipette` | single | candidate | `multichannel_pipette` |
| `p10_gel_loading_tip`, `p10_gel_loading_tip_box` | single | static | named matching object |
| `p10_micropipette_empty` | single | candidate | `p10_micropipette` |
| `p10_micropipette_filled` | single | static | - |
| `p200_micropipette_empty` | single | candidate | `micropipette`, `p200_micropipette` |
| `p200_micropipette_filled` | single | static | - |
| `paper_towel_pad`, `plate_reader`, `plate_reader_new` | single | static | `paper_towel_pad`; otherwise - |
| `plate_reader_idle`, `plate_reader_reading` | collection: `plate_reader` | static | `plate_reader` |
| `power_supply_off`, `power_supply_on` | collection: `power_supply` | static | `power_supply` |
| `protein_ladder_tube` | single | candidate | `protein_ladder_tube` |
| `protein_ladder_tube_empty`, `protein_ladder_tube_filled` | single | static | - |
| `protein_sample_tube` | single | candidate | `protein_sample_tube` |
| `protein_sample_tube_empty`, `protein_sample_tube_filled` | single | static | - |
| `rocking_shaker_idle`, `rocking_shaker_running` | collection: `rocking_shaker` | static | `rocking_shaker` |
| `running_buffer_1x_carboy`, `_empty`, `_filled` | single | static | - |
| `serological_pipette` | single | candidate | `serological_pipette` |
| `sharps_container`, `sharps_container_full` | collection: `sharps_container` | static | `sharps_container` |
| `staining_tray_buffer`, `_destain`, `_empty`, `_stain`, `_water` | collection: `staining_tray` | candidate | `staining_tray` |
| `t75_flask` | single | candidate | `t75_flask`, `t75_flask_new` |
| `t75_flask_servier`, `_v2`, `_v3`, `_v4`, `_v5` | single | static | - |
| `tip_box` | single | static | `micropipette_tip_box` |
| `tip_box_new` | single | static | - |
| `tube_rack` | single | static | `microtube_rack_24` |
| `vortex` | single | static | `vortex` |
| `waste_container` | single | candidate | `waste_container` |
| `waste_tray`, `water_bath_new`, `well_plate_24` | single | static | - |
| `water_bath`, `water_bath_occupied` | collection: `water_bath` | static | `water_bath` |

## Filename and folder evidence

The present flat `assets/equipment/` directory does not express either axis. File
names are useful human hints, but they are not authoritative: examples include an
unreferenced `centrifuge_new.svg`, object-selected `centrifuge.svg` and
`centrifuge_running.svg`, and unreferenced filled/empty variants beside a single
object-selected base form.

No file has a bare state-only stem such as `open.svg`, `closed.svg`, `on.svg`, or
`off.svg`. The state-bearing names that are used (`power_supply_off`,
`heat_block_open`) carry family identity and satisfy the proposed snake_case rule.
Several existing collections use a bare family stem as their default form
(`centrifuge`, `water_bath`, `gel_comb`, `mtt_powder_vial`, `sharps_container`), so
they do not yet make the default state explicit. Historical/import suffixes such as
`_new`, `_v2`, and `_servier` are also not stable form names. These are naming debt
that the behavior-directory migration must report; they do not independently
establish a state category.

## Flat-path consumers

The following consumers assume direct files in `assets/equipment/`; moving assets now
would change their contracts or tests.

| Area | Flat-path consumer | Consequence of relocation |
| --- | --- | --- |
| Pipeline | `pipeline/gen_scene_index.py:187-204,821-822` | enumerates only `assets/equipment/` with `os.listdir` |
| Pipeline | `pipeline/gen_object_library.py:100-112` | already recurses under `assets/`, but maps by bare filename stem |
| Pipeline | `pipeline/gen_svg_manifest.py:443-469` | supports category directories but only maps one immediate category and requires globally unique stems |
| Validation | `validation/yaml_schema/object_validator.py:982-1015` | anchor check constructs `assets/equipment/<asset_name>.svg` |
| Validation | `validation/svg/asset_audit.py:38-40,189-456` | audit, source provenance, placeholder record, and SVG enumeration all use the flat equipment directory |
| Validation | `tests/test_object_asset_refs.py:1-48` | gate uses `ASSETS_DIR.glob('*.svg')` |
| Picker | `tools/svg_picker/build_candidate_manifest.py:232-234` | indexes `assets/equipment/` as the in-repo source |
| Picker | `tools/svg_picker/build_missing_targets.py:7,68,211`; `apply_decisions.py:112-173` | calculates targets and copies/moves directly to `assets/equipment/<name>.svg` |
| Picker | `tools/svg_picker/serve_picker.sh:4` | serves only the equipment directory boundary |
| Attribution | `assets/equipment/SOURCES.md`; `MISSING_SVG_PLACEHOLDERS.md`; `docs/THIRD_PARTY_ASSETS.md:16-88` | provenance records names/files at their current flat paths |
| Documentation | `docs/FILE_STRUCTURE.md:267,405`, `docs/CODE_ARCHITECTURE.md:256,360,452-454`, `docs/USAGE.md:110,117-118` | authoring and build instructions prescribe the flat location |

## Conclusion for M2

Use a non-overlapping two-source behavior model:

1. Object `visual_states` remains the sole authority for a discrete collection and
   its state-to-`asset_name` selection.
2. A validated root declaration inside each material-rendered SVG is the sole
   authority for that individual form's rendering model.

No collection manifest is needed: it would duplicate `visual_states` case maps without
resolving any current ambiguity. The user subsequently rejected the conclusion that
117 SVG sources should remain flat merely because relocation has a broad cost. The
approved organization migration will project the authoritative behavior into
`static/`, `binary_state/`, `multi_state/`, and `variable_volume/` directories. It is
sequenced after the five true variable-volume families are complete.

The broad consumer list above is therefore the migration scope, not a reason to avoid
the work. One recursive, unique-stem registry must replace those assumptions before
the physical move so logical `asset_name` values remain stable and directory paths do
not leak into object YAML.

The M2 validation rule should instead derive collections from object YAML and assert:

- each selected `asset_name` resolves through the generated asset registry;
- a discrete-form filename is descriptive snake_case and, when it expresses a state,
  includes the asset family plus that state;
- no form is material-rendered unless its own normalized SVG declares the validated
  semantic contract;
- a collection may mix rendering models, but each form must declare its own model.

## Post-migration evidence

WP-ORG completed the approved projection after the five variable-volume families
passed their contact-page gate. The source census remains 117 unique logical forms:

| Behavior directory | SVG forms |
| --- | ---: |
| `static/` | 73 |
| `binary_state/` | 34 |
| `multi_state/` | 5 |
| `variable_volume/` | 5 |

`validation/svg/asset_registry.py` is now the recursive unique-stem authority used
by generators, validation, audits, and picker tooling. The placement validator
projects ordinary-state cardinality from object YAML and material capability from
the SVG root, then rejects any source outside its derived behavior directory.

The physical move did not change object YAML. A clean generation and Pages build
resolved all 78 referenced logical names and published the same flattened URLs under
`dist/assets/svg/equipment/`. The earlier flat-path-consumer table is retained as
historical migration evidence; its executable consumers now resolve through the
registry or recursively indexed provenance.
