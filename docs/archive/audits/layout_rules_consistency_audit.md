# SIDE QUEST: layout_rules consistency audit

Audit of authoring-level layout inconsistencies across `content/base_scenes/*.yaml`
(9 files) plus a sample of derived scene YAMLs under `content/protocols/`.
Read-only. No YAML edits were made.

Vocabulary reference: `docs/specs/SCENE_YAML_FORMAT.md` and `docs/specs/LAYOUT_ENGINE.md`.

---

## Section 1. Scope and method

Base scenes audited (9 files under `content/base_scenes/`):

- `bench_basic.yaml`
- `cell_counter_basic.yaml`
- `electrophoresis_bench.yaml`
- `heat_block_bench.yaml`
- `hood_basic.yaml`
- `imaging_bench.yaml`
- `microscope_basic.yaml`
- `sample_prep_bench.yaml`
- `staining_bench.yaml`

Derived scenes sampled (5 files under `content/protocols/`):

- `cell_culture/passage_hood_detachment/scenes/hood_workspace.yaml`
- `cell_culture/passage_pellet_reseed/scenes/hood_workspace.yaml`
- `sdspage/sdspage_heat_denature_samples/scenes/sdspage_heat_denature_samples_workspace.yaml`
- `sdspage/sdspage_prepare_sample_mix_single_lane/scenes/sample_prep_bench_override.yaml`
- `sdspage/sdspage_fill_tank_buffer/scenes/sdspage_fill_tank_buffer_workspace.yaml`

---

## Section 2. layout_rules inventory (base scenes)

All values from the `layout_rules:` block of each file. A `-` means the field is absent.

| Scene | label_line_height | label_offset_y | zone_gap | default_align_stop |
| --- | --- | --- | --- | --- |
| bench_basic | 1.1 | 4 | 4 | center |
| cell_counter_basic | 1.1 | 4 | 2 | - |
| electrophoresis_bench | 1.1 | 4 | 2 | - |
| heat_block_bench | 1.1 | 4 | 2 | - |
| hood_basic | 1.1 | 4 | 4 | center |
| imaging_bench | 1.1 | 4 | 2 | - |
| microscope_basic | 1.1 | 4 | 2 | - |
| sample_prep_bench | 1.1 | 4 | 2 | - |
| staining_bench | 1.1 | 4 | 2 | - |

`label_font_size`, `label_placement`, and `cluster_spacing_px` are absent from every base scene.

Findings:

- `label_line_height: 1.1` and `label_offset_y: 4` are identical across all 9 scenes.
  All 9 scenes carry these redundantly with no comment explaining intent.
- `zone_gap` splits into two values: 4 (bench_basic, hood_basic) and 2 (all others).
  No documented rationale separates these two groups.
- `default_align_stop: center` is present only in bench_basic and hood_basic.
  The other 7 scenes omit it; engine fallback for missing field is undocumented.

---

## Section 3. Zone name inventory (base scenes)

| Scene | Rear zones | Mid zones | Working zone | Tool zones |
| --- | --- | --- | --- | --- |
| bench_basic | rear_left, rear_center, rear_right | - | center | right_tool_area |
| cell_counter_basic | rear_shelf | - | instrument_area | left_bench, right_accessory_area |
| electrophoresis_bench | rear_left, rear_center, rear_right | - | center, front_left, front_right | right_tool_area |
| heat_block_bench | rear_left, rear_center, rear_right | mid_left, mid_right | front | right_tool_area |
| hood_basic | rear_left, rear_center, rear_right | - | center | right_tool_area |
| imaging_bench | rear_left, rear_center, rear_right | - | center | left_tool_area, right_tool_area |
| microscope_basic | rear_left, rear_right | - | instrument_area | left_bench, right_bench |
| sample_prep_bench | rear_left, rear_center, rear_right | mid_left, mid_right | center | right_tool_area |
| staining_bench | rear_left, rear_center, rear_right | - | center | right_tool_area |

Findings:

- Six scenes use the `rear_left / rear_center / rear_right` triplet. cell_counter_basic uses
  `rear_shelf` (single wide zone); microscope_basic uses only `rear_left` and `rear_right`.
- The primary working zone is named `center` in 5 scenes, `instrument_area` in 2,
  and `front` in 1 (heat_block_bench). These three names cover the same semantic role.
- heat_block_bench names the front working surface `front`; sample_prep_bench uses the
  same structural layout (rear + mid_left/mid_right + front) but names it `center`.
- `right_tool_area` is the consistent name in 6 of 9 scenes. cell_counter_basic uses
  `right_accessory_area`; microscope_basic uses `right_bench`.
- imaging_bench is the only scene with both `left_tool_area` and `right_tool_area`.

---

## Section 4. Zone bounds and baseline comparison

Rear band (top/bottom/baseline in percent units):

| Scene | Rear top | Rear bottom | Rear baseline | Notes |
| --- | --- | --- | --- | --- |
| bench_basic | 5 | 36 | 32 | three sub-zones |
| cell_counter_basic | 5 | 32 | 28 | one wide zone (rear_shelf) |
| electrophoresis_bench | 5 | 36 | 32 | three sub-zones |
| heat_block_bench | 5 | 32 | 28 | three sub-zones |
| hood_basic | 5 | 36 | 32 | three sub-zones |
| imaging_bench | 5 | 34 | 30 | three sub-zones |
| microscope_basic | 5 | 34 | 30 | two sub-zones |
| sample_prep_bench | 5 | 32 | 28 | three sub-zones |
| staining_bench | 8 | 36 | 32 | top starts at 8 not 5 |

Working zone bounds:

| Scene | Zone name | left | right | top | bottom | baseline |
| --- | --- | --- | --- | --- | --- | --- |
| bench_basic | center | 5 | 68 | 38 | 94 | 84 |
| cell_counter_basic | instrument_area | 27 | 73 | 40 | 92 | 90 |
| electrophoresis_bench | center | 10 | 85 | 38 | 76 | 64 |
| heat_block_bench | front | 8 | 84 | 64 | 94 | 90 |
| hood_basic | center | 5 | 68 | 38 | 94 | 84 |
| imaging_bench | center | 20 | 80 | 38 | 92 | 84 |
| microscope_basic | instrument_area | 31 | 71 | 18 | 92 | 88 |
| sample_prep_bench | center | 8 | 84 | 66 | 94 | 90 |
| staining_bench | center | 10 | 82 | 38 | 94 | 84 |

Findings:

- staining_bench rear zones start at `top: 8` while scene_bounds starts at `top: 5`.
  All other scenes start their first zone at top: 5 matching scene_bounds.
- Rear baselines cluster at three undocumented values: 28, 30, and 32.
- Rear band bottom varies: 32 (3 scenes), 34 (2 scenes), 36 (4 scenes). No comments.
- Working zone baselines vary: 64 (electrophoresis), 84 (bench/hood/imaging/staining),
  88 (microscope), 90 (cell_counter, heat_block, sample_prep). No comments.

---

## Section 5. Zone align values by scene

| Scene | rear zones | mid zones | working zone | tool zones |
| --- | --- | --- | --- | --- |
| bench_basic | tab-stops x3 | - | tab-stops | tab-stops |
| cell_counter_basic | tab-stops | - | center | tab-stops x2 |
| electrophoresis_bench | center x3 | - | tab-stops | center x3 |
| heat_block_bench | tab-stops x3 | tab-stops x2 | tab-stops | tab-stops |
| hood_basic | tab-stops x3 | - | tab-stops | tab-stops |
| imaging_bench | tab-stops x3 | - | tab-stops | tab-stops x2 |
| microscope_basic | tab-stops x2 | - | center | tab-stops x2 |
| sample_prep_bench | tab-stops x3 | tab-stops x2 | tab-stops | tab-stops |
| staining_bench | center x3 | - | tab-stops | tab-stops |

Findings:

- electrophoresis_bench and staining_bench use `align: center` in rear zones;
  7 other scenes use `align: tab-stops` for the same rear band. No comment explains.
- cell_counter_basic and microscope_basic set the instrument zone to `align: center`
  (appropriate for a single large instrument); all other working zones use `tab-stops`.
- electrophoresis_bench uses `align: center` for right_tool_area and both front zones,
  while all other scenes use `tab-stops` for equivalent tool areas.

---

## Section 6. anchor_y and anchor_y_offset usage

No base scene placement uses `anchor_y`, `anchor_y_offset`, or `baseline_override`.
All placements fall through to object-library defaults. The 5 sampled derived scenes
also make no use of these fields. Internally consistent across the base layer.

---

## Section 7. display_width_cm field

The field `display_width_cm` does not appear in any base scene YAML and is absent
from the `layout_rules` schema table in `docs/specs/SCENE_YAML_FORMAT.md`.
This field name is absent from the authored surface entirely. No finding.

---

## Section 8. background field consistency

| Scene | Background type |
| --- | --- |
| bench_basic | gradient inline |
| cell_counter_basic | gradient inline |
| electrophoresis_bench | asset: bench_workspace_bg |
| heat_block_bench | asset: bench_workspace_bg |
| hood_basic | gradient inline |
| imaging_bench | asset: bench_workspace_bg |
| microscope_basic | asset: microscope_view_bg |
| sample_prep_bench | gradient inline |
| staining_bench | gradient inline |

Findings:

- All five gradient scenes use identical values (`from: "#E8E2D0"`, `to: "#D4CBB3"`,
  `angle: 180`) duplicated inline in each file.
- `background.type`, `background.from`, `background.to`, `background.angle` appear in
  5 base scenes but are NOT listed in the `SCENE_YAML_FORMAT.md` background schema table.
  The schema documents only `background.asset` and `background.bounds`.
  These gradient fields are either a fused-format residue or an undocumented extension.

---

## Section 9. workspace field values vs. schema

`SCENE_YAML_FORMAT.md` documents valid workspace values as:
`equipment_bench`, `wet_lab_hood`, `modal_overlay`, `dedicated_plate`.

| Scene | Authored value | In schema? |
| --- | --- | --- |
| bench_basic | bench | NO |
| cell_counter_basic | cell_counter | NO |
| electrophoresis_bench | bench | NO |
| heat_block_bench | bench | NO |
| hood_basic | hood | NO |
| imaging_bench | bench | NO |
| microscope_basic | microscope | NO |
| sample_prep_bench | bench | NO |
| staining_bench | bench | NO |

All 9 authored workspace values are absent from the schema documentation.
Complete mismatch between spec and files. One surface must be the single source of truth.

---

## Section 10. Derived scene layout_rules inheritance

| Derived scene | Extends | Own layout_rules? |
| --- | --- | --- |
| passage_hood_detachment_hood_workspace | hood_basic | absent |
| hood_workspace (pellet_reseed) | hood_basic | absent |
| sdspage_heat_denature_samples_workspace | heat_block_bench | absent |
| sdspage_prepare_sample_mix_single_lane_workspace | sample_prep_bench | absent |
| sdspage_fill_tank_buffer_workspace | electrophoresis_bench | absent |

All 5 sampled derived scenes omit `layout_rules` and inherit from their base scene.
This is consistent behavior across the derived layer.

---

## Section 11. Recommendations

12 recommendations. Severity: HIGH = affects multiple scenes or schema truth;
MEDIUM = affects 2-4 scenes; LOW = single scene or cosmetic.
No new vocabulary terms are proposed. All changes are consistency-oriented.

### R-01 (HIGH): Remove redundant label_line_height and label_offset_y

All 9 base scenes set `label_line_height: 1.1` and `label_offset_y: 4` identically.
If these equal the engine defaults, remove them from all 9 files.
If they differ from defaults, add a single comment in one reference file explaining
the override. Source: all 9 base scene `layout_rules:` blocks.

### R-02 (HIGH): Align workspace field values with schema documentation

All 9 base scenes use workspace values (`bench`, `hood`, `cell_counter`, `microscope`)
that are absent from the `SCENE_YAML_FORMAT.md` documented enum.
Either update the schema table in `SCENE_YAML_FORMAT.md` to list the actual values,
or migrate the YAML files to the documented enum. One must be the single source of truth.
Source: all 9 base scenes; `docs/specs/SCENE_YAML_FORMAT.md` workspace table.

### R-03 (HIGH): Unify working zone name (center vs. instrument_area vs. front)

The main forward working surface is named `center` in 5 scenes, `instrument_area`
in 2, and `front` in 1 (heat_block_bench). heat_block_bench and sample_prep_bench
share the same layout pattern (rear triplet + mid_left/mid_right + working surface)
but diverge on the name. Rename `front` to `center` in heat_block_bench to match.
Source: `heat_block_bench.yaml` zone_name `front`; `sample_prep_bench.yaml` zone_name `center`.

### R-04 (MEDIUM): Unify zone_gap (4 vs. 2)

bench_basic and hood_basic set `zone_gap: 4`; all other 7 scenes use `zone_gap: 2`.
No comment documents the difference. Either document the reason or normalize to one value.
Source: `bench_basic.yaml` and `hood_basic.yaml` layout_rules.

### R-05 (MEDIUM): Document or unify rear zone baseline values (28, 30, 32)

Three distinct rear baseline values appear across scenes with no inline comments.
28: cell_counter_basic, heat_block_bench, sample_prep_bench.
30: imaging_bench, microscope_basic. 32: bench_basic, electrophoresis_bench, hood_basic, staining_bench.
If object heights drive the choice, add a brief inline comment per rear zone.
If accidental, normalize to a single value. Source: all 9 base scene zone blocks.

### R-06 (MEDIUM): Document or unify rear zone bottom bounds (32, 34, 36)

The rear band `bottom` value is 32 (3 scenes), 34 (2 scenes), or 36 (4 scenes).
No inline comment in any file explains the choice. Same approach as R-05: add comments
or normalize. Source: all 9 base scene zone bounds.

### R-07 (MEDIUM): Align default_align_stop presence across scenes

`default_align_stop: center` appears only in bench_basic and hood_basic. The other 7
scenes omit it, leaving placements without `align_stop` at an undocumented engine fallback.
Add `default_align_stop` to every scene that uses `tab-stops` zones and has placements
without explicit `align_stop`, or document the engine default in `SCENE_YAML_FORMAT.md`.
Source: cell_counter_basic, electrophoresis_bench, heat_block_bench, imaging_bench,
microscope_basic, sample_prep_bench, staining_bench layout_rules blocks.

### R-08 (MEDIUM): Align rear-zone align values (center vs. tab-stops)

electrophoresis_bench and staining_bench use `align: center` for their rear zones;
the other 7 scenes use `align: tab-stops`. Establish a rule: `center` for zones
with exactly one item, `tab-stops` for zones with two or more items.
Source: `electrophoresis_bench.yaml` rear zone align values; `staining_bench.yaml` same.

### R-09 (MEDIUM): staining_bench rear zones start at top: 8, not top: 5

All other scenes begin their first zone at `top: 5` matching `scene_bounds.top: 5`.
staining_bench starts rear zones at `top: 8`, leaving a 3-unit unoccupied gap.
Change to `top: 5` unless the gap is intentional; add a comment if it is.
Source: `staining_bench.yaml` rear zone bounds `top: 8`.

### R-10 (MEDIUM): Undocumented gradient background fields

Five scenes use `background.type: gradient` with `from`, `to`, `angle` sub-fields.
These fields are absent from the `SCENE_YAML_FORMAT.md` background schema table,
which documents only `background.asset` and `background.bounds`.
Add the gradient variant to the schema table, or replace inline gradients with a
named background asset and remove the undocumented fields.
Source: bench_basic, cell_counter_basic, hood_basic, sample_prep_bench, staining_bench
background blocks; `docs/specs/SCENE_YAML_FORMAT.md` background section.

### R-11 (LOW): Identical gradient values duplicated in five files

All five gradient scenes share `from: "#E8E2D0"`, `to: "#D4CBB3"`, `angle: 180` inline.
Introduce a named background asset (e.g. `bench_gradient_bg`) and replace the five
inline blocks with `background: { asset: bench_gradient_bg }`, following the convention
of the other four scenes. Source: bench_basic, cell_counter_basic, hood_basic,
sample_prep_bench, staining_bench background blocks.

### R-12 (LOW): right_bench and right_accessory_area vs. right_tool_area

`right_tool_area` names the right secondary column in 6 of 9 scenes.
cell_counter_basic uses `right_accessory_area`; microscope_basic uses `right_bench`.
Evaluate whether renaming to `right_tool_area` improves authoring consistency.
If the semantic distinction is intentional, add an inline comment.
Source: `cell_counter_basic.yaml` zone_name `right_accessory_area`;
`microscope_basic.yaml` zone_name `right_bench`.

---

## Section 12. Summary table

| ID | Severity | Scope | Short description |
| --- | --- | --- | --- |
| R-01 | HIGH | all 9 base scenes | Redundant label_line_height/label_offset_y in every scene |
| R-02 | HIGH | all 9 base scenes + spec | workspace values do not match schema enum |
| R-03 | HIGH | heat_block_bench | Working zone named `front` not `center` |
| R-04 | MEDIUM | bench_basic, hood_basic | zone_gap 4 vs. 2; no documented reason |
| R-05 | MEDIUM | all 9 base scenes | Rear baseline 28/30/32 with no comment |
| R-06 | MEDIUM | all 9 base scenes | Rear bottom bounds 32/34/36 with no comment |
| R-07 | MEDIUM | 7 base scenes | default_align_stop absent; engine fallback undocumented |
| R-08 | MEDIUM | electrophoresis_bench, staining_bench | Rear zones use center vs. tab-stops inconsistently |
| R-09 | MEDIUM | staining_bench | Rear zones start at top:8 not top:5 |
| R-10 | MEDIUM | 5 scenes + spec | Gradient background fields absent from schema |
| R-11 | LOW | 5 scenes | Identical gradient duplicated inline in 5 files |
| R-12 | LOW | cell_counter_basic, microscope_basic | right_bench/right_accessory_area vs. right_tool_area |

12 recommendations total: 3 HIGH, 6 MEDIUM, 3 LOW.

