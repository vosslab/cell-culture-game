# Structured object material corpus catalog

Read-only corpus map produced as input evidence for the walker material-verification
design. Covers three questions: (1) which objects have named subpart areas and
material overlays, (2) which protocol writes push material into a group or single
subpart, and (3) which of those writes are actually asserted anywhere. Source of
truth is `content/objects/**/*.yaml` and `content/protocols/**/protocol.yaml` as of
this scan.

## Part 1: structured objects with named subpart areas

A "structured" object declares a `structure:` block with a `subpart_kind` and a
`name_pattern`. Material overlay means it declares `material_name` /
`material_volume` state fields with `applies_to: subpart`.

| object_name | subpart_kind | subparts | subpart_groups | material overlay |
| --- | --- | --- | --- | --- |
| `well_plate_96` | well | 96: `A1`..`H12` (8 rows x 12 cols) | `rows` (`row_A`..`row_H`), `columns` (`col_1`..`col_12`), `plate_region` (`all_wells`), `blocks` (`block_A_1_6`, `block_A_7_12`, `block_B_H_1_6`, `block_B_H_7_12`) | YES (per-well `material_name` sentinel `[empty, mixed]` + registry-backed; `material_volume` 0..300 ul) |
| `gel_cassette` | lane | 10: `lane_1`..`lane_10` | `all_lanes` (region: all 10 lanes) | YES (per-lane `material_name` `[empty, protein_ladder, protein_sample_denatured]`; `material_volume` 0..30 ul). Also object-level bool fields: `tape_present`, `comb_present`, `top_plate_inserted`, `side_clamps_locked`, `wing_clamps_locked` |
| `dilution_tube_rack_8` | tube | 8: `tube_A`..`tube_H` | none | YES (per-tube `material_name` `[empty, carboplatin, media]`; `material_volume` 0..1000 ul, with `fill_height` composite) |
| `conical_15ml_rack` | slot | 6: `slot_1`..`slot_6` (list) | none | YES (per-slot `material_name` `[empty, cells, media]`; `material_volume` 0..15 ml, `fill_height` composite) |
| `counter_slide_cartridge` | slot | 10: `slide_1`..`slide_10` (list) | none | DEGENERATE (per-slot `material_name` allowed `[empty]` only, `material_volume` max 0; holder only, plus object-level `slide_count` int). No real material is ever stored. |

### Structured-looking objects that are NOT per-subpart material containers

- `microtube_rack_24`: no `structure:` block at all. `material_name` / `material_volume`
  are object-scope placeholders (allowed `[empty]`). Not a subpart container despite the
  "24-slot" label. `capabilities: [clickable]` only.
- `multichannel_pipette`: no subparts. Holds material at object scope
  (`held_material_name`, `held_material_volume`). Has a `channel_addressing` block
  (`channels: 8`, `addressable_subpart_kinds: [well, column]`) describing what plate
  subparts it can address, but the pipette itself is not a subpart surface.
- `mini_protean_gel`: NOT the lane-bearing object. Only a `sealed` bool. The gel with
  addressable lanes is `gel_cassette` above.

Net: only `well_plate_96`, `gel_cassette`, `dilution_tube_rack_8`, and
`conical_15ml_rack` are live per-area material surfaces. Only `well_plate_96` and
`gel_cassette` declare `subpart_groups`. `conical_15ml_rack` is a structured material
surface that NO protocol currently writes (see Part 2).

## Part 2: protocol writes into a group or single subpart

Every `ObjectStateChange` whose `target` is a dotted `<object>.<suffix>` reference.
152 dotted writes total across 9 protocols. Counts collapse repeated per-well /
per-tube / per-lane writes into a family row.

| protocol | step(s) | target family | fields written | material_name value(s) |
| --- | --- | --- | --- | --- |
| `cell_seeding_plate_setup` | seed step | `well_plate_96.all_wells` (group) | `material_name`, `material_volume` | `cells` |
| `passage_pellet_reseed` | 2 steps | `well_plate_96.all_wells` (group) | one write `material_name` only; one `material_name`+`material_volume` | `media` |
| `mtt_plate_reaction` | 3 steps | `well_plate_96.all_wells` (group) | `material_name`, `material_volume` (x3) | `mtt`, `formazan`, `empty` |
| `mtt_solubilization_readout` | `add_dmso_to_wells` (+1) | `well_plate_96.all_wells` (group) | one `material_name`+`material_volume`, one `material_volume` only | `formazan_dmso_solution` |
| `plate_drug_treatment_media_adjustment` | 4 steps | `well_plate_96.block_A_1_6`, `block_A_7_12`, `block_B_H_1_6`, `block_B_H_7_12` (groups) | `material_name`, `material_volume` (1 each) | `cells` |
| `plate_drug_treatment_drug_addition` | many steps | `well_plate_96.<single well>` B1..H12 (126 single-well writes, 18 per row B-H) | `material_name`, `material_volume` | `carboplatin`, `carboplatin_metformin_combo` |
| `drug_dilution_setup` | 6 tube steps | `dilution_tube_rack_8.tube_A`..`tube_G` (single subpart) | 6 writes `material_name`+`material_volume`; 6 follow-up `material_volume`-only (dilution top-up) | `carboplatin` |
| `sdspage_load_protein_ladder` | load step | `gel_cassette.lane_5` (single subpart) | `material_name`, `material_volume` | `protein_ladder` |
| `sdspage_load_sample_single_lane` | load step | `gel_cassette.lane_1` (single subpart) | `material_name`, `material_volume` | `protein_sample_denatured` |

Write-shape summary:
- Group fan-out writes: `all_wells` (4 protocols), the 4 `block_*` regions
  (`media_adjustment`). No protocol writes `row_*`, `col_*`, or `gel_cassette.all_lanes`.
- Single-subpart writes: 126 single wells (`drug_addition`), 8 tubes (`drug_dilution`,
  6 filled), 2 gel lanes (`lane_5`, `lane_1`).
- `conical_15ml_rack` slots and `counter_slide_cartridge` slides receive no material
  writes from any protocol.

## Part 3: current verification coverage and the gap

### What is asserted per-area today

- `tests/playwright/e2e/protocol_walkthrough.spec.ts` uses the canonical visible
  walker to verify every structured material write. For `all_wells`, it proves
  all 96 concrete wells are painted, learner-sized, and reach the authored
  material while no untargeted member changes. It uses ordinary Playwright
  clicks and the visible action rail; no page-side synthetic click or hidden
  answer projection remains.
- `tests/playwright/test_per_well_drug_walkthrough.spec.ts` drives
  `plate_drug_treatment_drug_addition`, asserts row B (`B1`..`B12`) reaches
  `data-material-name = carboplatin`, and proves sampled untargeted seeded-cell
  wells retain their exact pre-treatment state.
- `tests/test_scene_op_deps.mjs` -- unit test that an `ObjectStateChange` to
  `well_plate_96.all_wells` fans out to each member well in the store and writes NO
  `well_plate_96.all_wells` pseudo-node. Mechanism-level, not rendered/per-protocol.
- `tests/playwright/test_subpart_well_plate_render.mjs` and
  `tests/test_subpart_visual_state_renderer.mjs` -- render the per-well material tint
  overlay from state; they prove the render path, not any protocol's write.
- `tests/test_object_validator_well_plate_subpart_material.py`,
  `tests/test_stepper_subpart_state.py`, `tests/test_object_library_visual_states.py` --
  schema / stepper shape checks (a structured well plate must declare per-subpart
  material fields; rack/tube exempt). Not per-area value verification.
- `tests/test_target_adapter.mjs` references `gel_cassette` only for
  placement<->object name resolution, NOT lane material.

### Coverage gap: writes with no per-area verification

| write | verified? |
| --- | --- |
| `mtt_solubilization_readout` -> `all_wells` (formazan_dmso_solution) | YES (walker, 5 wells) |
| `plate_drug_treatment_drug_addition` -> single wells (carboplatin) | PARTIAL (walker asserts row B + D11; carboplatin only, not `carboplatin_metformin_combo`) |
| `cell_seeding_plate_setup` -> `all_wells` (cells) | NO per-area assertion |
| `passage_pellet_reseed` -> `all_wells` (media) | NO per-area assertion |
| `mtt_plate_reaction` -> `all_wells` (mtt / formazan / empty, 3 sequential) | NO per-area assertion (multi-write material progression untested) |
| `plate_drug_treatment_media_adjustment` -> `block_A_1_6`, `block_A_7_12`, `block_B_H_1_6`, `block_B_H_7_12` (cells) | NO per-area assertion; no test reads any `block_*` group at all |
| `drug_dilution_setup` -> `tube_A`..`tube_G` (carboplatin + volume top-ups) | NO per-area assertion; no test reads `dilution_tube_rack_8` tube material/fill |
| `sdspage_load_protein_ladder` -> `lane_5` (protein_ladder) | NO per-area assertion; no test reads any `gel_cassette` lane material |
| `sdspage_load_sample_single_lane` -> `lane_1` (protein_sample_denatured) | NO per-area assertion |

Key gaps for the walker material-verification design to close:
1. Two of five live subpart surfaces have zero per-area verification of protocol
   writes: `dilution_tube_rack_8` (tubes) and `gel_cassette` (lanes). The gel lane and
   tube DOM/overlay read path is unproven end-to-end (only well plate has a proven
   `data-subpart-name` reader).
2. `block_*` group writes (`media_adjustment`) are entirely unverified; no test reads a
   block group. Only `all_wells` fan-out has walker coverage.
3. Sequential same-target material progression (`mtt_plate_reaction`: mtt -> formazan ->
   empty on `all_wells`) is untested; existing walker checks a single before/after.
4. `volume-only` follow-up writes (drug_dilution top-ups; the second
   `mtt_solubilization_readout` write) change `material_volume` without `material_name`;
   no test asserts a volume-only per-area change.
5. The two live surfaces with no writes at all (`conical_15ml_rack`,
   `counter_slide_cartridge`) are out of scope for write-verification but worth noting
   so the design does not assume every structured surface is exercised.
