# WP-ENUM: well_plate_96 material union harvest

Workstream: M1 WP-ENUM (plan: dynamic-coalescing-flask.md)
Date: 2026-06-03

## Harvest command

```
source source_me.sh && python3 tools/harvest_well_materials.py
```

Script location: `tools/harvest_well_materials.py`

The script reads `well_plate_96.yaml` to build the subpart-group expansion map,
then walks every `content/protocols/**/protocol.yaml` file and collects every
`ObjectStateChange` that sets `material_name` on a `well_plate_96.*` target.
Group targets (all_wells, block_*, row_*, col_*) are expanded to member wells
using the `subpart_groups` declared in the object YAML, not a hardcoded 8x12
grid. Sequence runner protocols (no `steps` list) are skipped.

## Repeatability

The command was run twice on 2026-06-03. Both runs produced identical output.
Material union, authored-write count, and expanded-per-well count are stable
across runs (the script is purely read-only, no filesystem state).

## Alias/template/generated write path check

Only `protocol.yaml` files were checked. Scene YAML files use `extends:` for
YAML scene inheritance, which is not a protocol write template. The check
searched for Jinja-style delimiters (`{%`, `{{`) and `include:` / `alias:` keys
in protocol.yaml files.

Result: **none found**. No template, alias, jinja, or generated protocol write
path was detected in any `protocol.yaml` under `content/protocols/`.
All well material writes are authored directly in protocol YAML files.

## Protocol files with well_plate_96 material writes

| Protocol file | direct | group | bare obj |
| --- | --- | --- | --- |
| cell_culture/cell_seeding_plate_setup/protocol.yaml | 0 | 1 | 0 |
| cell_culture/mtt_plate_reaction/protocol.yaml | 0 | 3 | 0 |
| cell_culture/mtt_solubilization_readout/protocol.yaml | 0 | 1 | 0 |
| cell_culture/passage_pellet_reseed/protocol.yaml | 0 | 2 | 0 |
| cell_culture/plate_drug_treatment_drug_addition/protocol.yaml | 126 | 0 | 0 |
| cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml | 0 | 4 | 0 |

Notes:
- Paths above are relative to `content/protocols/`.
- "direct" = ObjectStateChange with target `well_plate_96.<well>` where `<well>` is
  a specific cell (A1, B7, ...).
- "group" = ObjectStateChange with target `well_plate_96.<group>` where `<group>` is
  a named subpart_group (all_wells, block_B_H_1_6, ...).
- "bare obj" = ObjectStateChange with target exactly `well_plate_96` (no subpart dot).

Several protocols contain `target: well_plate_96` gesture-click interactions (e.g.
`mtt_plate_reaction` gather step, `cell_seeding_plate_setup` incubate step). These
are navigation/click gestures only; they do NOT write `material_name` and are
outside scope of this material harvest. The plan's "11 bare writes" referred to
these gesture targets, not to bare material state writes. Confirmed: 0 bare
ObjectStateChange material writes exist in the current protocol set.

## Group expansion map

From `structure.subpart_groups` in `content/objects/plate/well_plate_96.yaml`:

| Group name | Member count |
| --- | --- |
| all_wells | 96 |
| block_A_1_6 | 6 |
| block_A_7_12 | 6 |
| block_B_H_1_6 | 42 |
| block_B_H_7_12 | 42 |
| col_1 through col_12 | 8 each |
| row_A through row_H | 12 each |

## Material union

Authored-write count = one authored `ObjectStateChange` regardless of how many wells
it expands to. Expanded-per-well count = total per-well instances after group expansion.

| material_name | authored | expanded | bare_obj |
| --- | --- | --- | --- |
| carboplatin | 84 | 84 | 0 |
| carboplatin_metformin_combo | 42 | 42 | 0 |
| cells | 5 | 192 | 0 |
| empty | 1 | 96 | 0 |
| formazan | 1 | 96 | 0 |
| formazan_dmso_solution | 1 | 96 | 0 |
| media | 2 | 192 | 0 |
| mtt | 1 | 96 | 0 |
| TOTAL | 137 | 894 | 0 |

Material union: `[carboplatin, carboplatin_metformin_combo, cells, empty, formazan,
formazan_dmso_solution, media, mtt]`

Union size: **8 materials**.

Note on plan estimate vs harvest: The pre-approval audit estimated ~252 direct well
writes and ~12 all_wells + ~8 block writes. The actual count is 126 direct writes
(plate_drug_treatment_drug_addition: 7 rows x 12 wells carboplatin = 84, plus 7 rows
x 6 cols combo = 42) and 11 authored group writes. These are the correct authored
counts from the current protocol YAML files; the estimate was a rough pre-code scan.
The expanded total (894) is what produces the STEPPER error count because the stepper
validates each expanded per-well write against the object-level enum.

## Per-material audit classification (D2)

Classification per locked decision D2: `empty` is the only sentinel (renders
transparent); every other value that appears in a visible well must resolve to a
color via registry entry (`label` + scalar `display_color`) or a spec-defined
built-in visual identity. Classification below is the audit read; final authority
is WP-MAT-VOCAB (pending, blocks D2 settlement). If WP-MAT-VOCAB classifies
differently, that classification supersedes this one.

| material_name | D2 class (audit) | registered in materials.yaml | notes |
| --- | --- | --- | --- |
| carboplatin | registry-backed | YES - plate_drug_treatment_drug_addition/materials.yaml | nested display_color (light/dark); needs WP-MAT-SWEEP scalar migration |
| carboplatin_metformin_combo | registry-backed | YES - plate_drug_treatment_drug_addition/materials.yaml | nested display_color; needs WP-MAT-SWEEP |
| cells | registry-backed | YES - cell_seeding_plate_setup/materials.yaml, plate_drug_treatment_media_adjustment/materials.yaml | nested display_color; needs WP-MAT-SWEEP |
| empty | sentinel | YES (passage_pellet_reseed) | sentinel; renders transparent (D4); no color required |
| formazan | registry-backed | YES - mtt_plate_reaction/materials.yaml | nested display_color; needs WP-MAT-SWEEP |
| formazan_dmso_solution | registry-backed | YES - mtt_solubilization_readout/materials.yaml | nested display_color; needs WP-MAT-SWEEP |
| media | registry-backed | YES - plate_drug_treatment_drug_addition, cell_seeding_plate_setup, passage_pellet_reseed | nested display_color; needs WP-MAT-SWEEP |
| mtt | registry-backed | YES - mtt_plate_reaction/materials.yaml | nested display_color; needs WP-MAT-SWEEP |

Summary of classification:
- Sentinel (renders transparent, no color required): `empty`
- Registry-backed (must have scalar `display_color` after WP-MAT-SWEEP): all 7 others

All 7 registry-backed materials are currently registered with a nested
`display_color.light`/`.dark` schema. All require the WP-MAT-SWEEP scalar migration
before the color resolver (D3) can read them as a single scalar hex.

## Count of "11 bare writes" clarification for WP-PROTO-MIGRATE

The plan lists WP-PROTO-MIGRATE as migrating "11 bare object-level writes." This
harvest confirms 0 bare ObjectStateChange material writes exist (no `target:
well_plate_96` with `material_name` in any ObjectStateChange). The 11 bare entries
from the pre-approval audit were `target: well_plate_96` gesture-click interactions
(not state writes). These do not write `material_name` and do not generate STEPPER
errors. WP-PROTO-MIGRATE should re-audit whether gesture-click bare targets require
migration or if the pre-approval count included non-write interactions.

## Residual risks

- All 7 non-sentinel materials are registered with nested `display_color.light/.dark`.
  WP-MAT-SWEEP must convert all of them before WP-MATERIALS can confirm coverage.
  No material is missing from the registry; all are present and will be coverage-
  confirmed by WP-MATERIALS after the sweep.
- The STEPPER errors (834 total) expand from 137 authored group/direct writes
  because each group write cascades to all member wells at validation time. After
  WP-STEPPER adds the per-subpart state path, the same 137 authored writes will
  validate correctly without any protocol YAML changes.
- No alias/template/generated write path was found. The harvest is complete as-is;
  no additional scan is needed for coverage.

## Handoff

- To WP-YAML: material union = 8 materials (list above). If M0 chooses registry-backed
  `material_name` for subpart fields (D1), no enum is needed on the object; the
  transitional union enum is the 8-material list above. The registry is confirmed
  present for all 7 non-sentinel materials.
- To WP-MATERIALS: all 7 non-sentinel materials are registered. After WP-MAT-SWEEP
  converts each to scalar `display_color`, WP-MATERIALS confirms coverage is complete.
- To WP-PROTO-MIGRATE: 0 bare ObjectStateChange material writes found. Re-confirm
  scope with the plan owner before migrating gesture-click bare targets (they do not
  cause STEPPER material errors).
