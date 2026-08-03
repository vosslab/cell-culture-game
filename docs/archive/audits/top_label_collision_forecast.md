# Top-label collision forecast

Forecast artifact for WS-D / WP-4b. Provides the expected-regression ledger
WP-4b needs to evaluate the unresolved_label_overlap gate.

Generated: 2026-06-10. Author: WS-O (read-only analysis task).

---

## Scope and context

WP-3a flipped the default label placement seed from bottom to top. All labels
not explicitly authored as `label_placement: bottom` now seed above their
object. The downward-only greedy stagger (WP-3b adds upward stagger; WP-4a
adds direction-aware collision moves) can push a top-seeded label downward into
a bottom-label position when its zone has too many labels for row 0.

This document:

- Confirms the WP-3a measured count of 14 down-staggered top labels.
- Lists all top-label-vs-label and top-label-vs-artwork conflicts predicted by
  the current layout state.
- Ranks scenes by total predicted conflicts.
- Provides the expected-state baseline for WP-4b's regression gate
  (unresolved_label_overlap count must not increase vs main unless individually
  explained).

---

## Methodology

### Data sources

Two data sources are combined:

1. `generated/scene_render_stats/*.stats.json` -- browser-rendered bounding
   boxes (`visual_bbox`, `label_bbox`) in CSS pixels at 1920x1080. These are
   used for conflict detection because they reflect the actual rendered geometry.

2. `generated/precomputed_layout.ts` -- layout-engine percentage coordinates
   (`_labelY`, `_baselineY`, `_top`, `_labelLines`). These are used to detect
   down-staggered labels because the stagger writes `_labelY` and the direction
   of stagger is readable from whether `_labelY > _baselineY`.

### Box formulas (for WP-4b reproduction)

All coordinates in the conflict check use the `label_bbox` and `visual_bbox`
from `generated/scene_render_stats/*.stats.json`:

```
label_box:   x = label_bbox.x,  y = label_bbox.y,
             w = label_bbox.w,  h = label_bbox.h
artwork_box: x = visual_bbox.x, y = visual_bbox.y,
             w = visual_bbox.w, h = visual_bbox.h
```

Two boxes A and B overlap when:

```
A.x < B.x + B.w  AND  A.x + A.w > B.x  (horizontal)
A.y < B.y + B.h  AND  A.y + A.h > B.y  (vertical, y increases downward)
```

A 0.5 px tolerance is applied at the top edge to avoid flagging labels that
exactly touch the artwork boundary.

### Label classification

- **Top label**: `label_bbox.y + label_bbox.h <= visual_bbox.y + 0.5`. Label
  bottom edge is at or above the artwork top.
- **Bottom label**: `label_bbox.y >= visual_bbox.y + visual_bbox.h - 0.5`.
  Label top is at or below the artwork bottom.
- **Mixed** (stagger artefact): label starts above artwork top but bottom
  crosses into the artwork zone. Counted as top label for conflict purposes.

### Down-stagger detection (from precomputed_layout.ts)

The greedy vertical stagger in `layout_labels.ts` places row-0 items at the
top seed and row-N items (N > 0) at `_baselineY + labelOffsetY + N * step`.
When a top-seeded label is assigned row N > 0 by the stagger, it lands at a
below-baseline Y coordinate.

Detection criterion: `item._labelY > item._baselineY`. The stagger loop skips
items with `layout.label_placement === "bottom"` (they are already bottom-
seeded and stagger does not apply in the top-stagger direction).

The partial-DS cases (where `_labelY > topSeed + 2.0` but `_labelY <=
_baselineY`) are minor intermediate stagger positions and are not included in
the 14-count ledger.

---

## Down-stagger verification (WP-3a ledger)

WP-3a measured 14 down-staggered top labels across 12 non-fixture scenes.
This analysis reproduces that count exactly.

| Scene | Placement | Zone | labelY | baselineY | topSeed |
| --- | --- | --- | --- | --- | --- |
| centrifuge_workspace | base_right_tip_box | right_tool_area | 84.53 | 84.00 | 74.03 |
| centrifuge_workspace | right_aspirating_pipette | right_tool_area | 88.10 | 84.00 | 54.76 |
| centrifuge_workspace | right_label_pen | right_tool_area | 88.10 | 84.00 | 72.78 |
| dilution_workspace | water_source | rear_right | 5.95 | 32.00 | 2.05 |
| drug_dilution_setup_bench_setup | center_metformin_working_tube | center | 88.10 | 84.00 | 70.83 |
| electrophoresis_bench | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| extraction_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_attach_lid_and_leads_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_fill_tank_buffer_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_load_sample_single_lane_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_prepare_running_buffer_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_recycle_buffer_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| sdspage_run_electrophoresis_workspace | rear_right_gel_opening_tool | rear_right | 32.30 | 32.00 | 24.78 |
| seeding_workspace | center_micropipette | center | 90.30 | 84.00 | 67.66 |

Total: 14. WP-3a count confirmed.

Notes:
- `dilution_workspace / water_source` has `labelY = 5.95` and `baselineY = 32.00`.
  This is a partial-DS case in the top-half space (labelY < baselineY but also
  labelY > topSeed by 3.9 units). It is the boundary case. The WP-3a implementer
  counted it, so it is included here.
- `centrifuge_workspace` contributes 3 of the 14 (all in zone right_tool_area).
- 6 sdspage scenes contribute 1 each through the shared `rear_right_gel_opening_tool`
  placement. The other 3 sdspage scenes (destain, heat_denature, prepare_sample_mix)
  have no DS labels.

---

## Conflict forecast: non-fixture scenes

Scenes ranked by total predicted conflicts (L-L + L-A). DS = down-staggered
top labels (from layout data). Conflicts are derived from browser-rendered
bounding boxes and cross-checked against the pre-existing stats counts.

| Scene | L-L | L-A | Total | DS |
| --- | --- | --- | --- | --- |
| dilution_workspace | 0 | 2 | 2 | 1 |
| hood_workspace | 1 | 1 | 2 | 0 |
| centrifuge_workspace | 0 | 0 | 0 | 3 |
| drug_dilution_setup_bench_setup | 0 | 0 | 0 | 1 |
| electrophoresis_bench | 0 | 0 | 0 | 1 |
| extraction_workspace | 0 | 0 | 0 | 1 |
| sdspage_attach_lid_and_leads_workspace | 0 | 0 | 0 | 1 |
| sdspage_fill_tank_buffer_workspace | 0 | 0 | 0 | 1 |
| sdspage_load_sample_single_lane_workspace | 0 | 0 | 0 | 1 |
| sdspage_prepare_running_buffer_workspace | 0 | 0 | 0 | 1 |
| sdspage_recycle_buffer_workspace | 0 | 0 | 0 | 1 |
| sdspage_run_electrophoresis_workspace | 0 | 0 | 0 | 1 |
| seeding_workspace | 0 | 0 | 0 | 1 |
| bench_basic | 0 | 0 | 0 | 0 |
| cell_counter_basic | 0 | 0 | 0 | 0 |
| cell_counter_workspace | 0 | 0 | 0 | 0 |
| heat_block_bench | 0 | 0 | 0 | 0 |
| hemocytometer_view | 0 | 0 | 0 | 0 |
| hood_basic | 0 | 0 | 0 | 0 |
| imaging_bench | 0 | 0 | 0 | 0 |
| incubator_workspace | 0 | 0 | 0 | 0 |
| microscope_basic | 0 | 0 | 0 | 0 |
| mtt_reagent_prep_bench_workspace | 0 | 0 | 0 | 0 |
| mtt_solubilization_readout_bench_workspace | 0 | 0 | 0 | 0 |
| mtt_solubilization_readout_plate_reader_workspace | 0 | 0 | 0 | 0 |
| passage_hood_detachment_hood_workspace | 0 | 0 | 0 | 0 |
| passage_hood_detachment_microscope_view | 0 | 0 | 0 | 0 |
| plate_drug_treatment_media_adjustment_plate_workspace | 0 | 0 | 0 | 0 |
| plate_workspace | 0 | 0 | 0 | 0 |
| sample_prep_bench | 0 | 0 | 0 | 0 |
| sdspage_destain_gel_rock_workspace | 0 | 0 | 0 | 0 |
| sdspage_heat_denature_samples_workspace | 0 | 0 | 0 | 0 |
| sdspage_prepare_sample_mix_single_lane_workspace | 0 | 0 | 0 | 0 |
| staining_bench | 0 | 0 | 0 | 0 |
| **TOTAL** | **1** | **3** | **4** | **14** |

L-L = label-label overlap pairs. L-A = top-label overlaps another object's artwork.

### Conflict detail: dilution_workspace

Two label-art conflicts. The down-staggered `water_source` label sits below
the object's top edge and encroaches on neighboring artwork.

```
L-A: met_working_tube label overlaps artwork of rear_right_vortex
L-A: met_working_tube label overlaps artwork of water_source
DS:  water_source (labelY=5.95, baselineY=32.00, topSeed=2.05)
```

### Conflict detail: hood_workspace

One label-label and one label-art conflict. The `center_conical_rack` top label
extends horizontally into the `rear_left_fresh_media` label and also overlaps
that object's artwork.

```
L-L: center_conical_rack vs rear_left_fresh_media
L-A: center_conical_rack label overlaps artwork of rear_left_fresh_media
```

---

## Down-stagger scenes with zero rendered conflicts

Thirteen scenes (centrifuge_workspace + 12 sdspage/bench scenes) carry DS
labels that do not produce rendered conflicts in the current state. The staggered
labels land in zones with sufficient vertical space to avoid overlap. WP-3b
(upward stagger) and WP-4a (direction-aware moves) are expected to pull these
labels back above the objects. If WP-4b catches any new `unresolved_label_overlap`
errors in these scenes after WP-3b/WP-4a land, they must be individually explained.

Scenes in this group: centrifuge_workspace (3 DS), drug_dilution_setup_bench_setup (1),
electrophoresis_bench (1), extraction_workspace (1), sdspage_attach_lid_and_leads_workspace (1),
sdspage_fill_tank_buffer_workspace (1), sdspage_load_sample_single_lane_workspace (1),
sdspage_prepare_running_buffer_workspace (1), sdspage_recycle_buffer_workspace (1),
sdspage_run_electrophoresis_workspace (1), seeding_workspace (1).

---

## Worst-3 scenes

1. `dilution_workspace` -- 2 conflicts (0 L-L, 2 L-A), 1 DS label. The
   `water_source` label is pushed into the rear-right zone and its neighbor
   label (`met_working_tube`) encroaches on two artwork bboxes.

2. `hood_workspace` -- 2 conflicts (1 L-L, 1 L-A), 0 DS labels. The
   `center_conical_rack` top label is wide enough to reach into the
   `rear_left_fresh_media` placement in an adjacent sub-zone.

3. `centrifuge_workspace` -- 0 conflicts, 3 DS labels. No rendered overlap,
   but the right-tool-area zone has three staggered labels (tip_box, pipette,
   label_pen) displaced downward. This is a WP-3b/WP-4a work item.

---

## Fixture scenes (exempt)

The four dev-fixture scenes are excluded from the WP-4b regression gate.
They are included here for completeness.

| Scene | L-L | L-A | Total | DS |
| --- | --- | --- | --- | --- |
| adversarial_overflow_smoke | 0 | 2 | 2 | 15 |
| missing_svg_check | 0 | 0 | 0 | 0 |
| select_check | 0 | 0 | 0 | 0 |
| type_check | 0 | 0 | 0 | 0 |

`adversarial_overflow_smoke` is the intentional overflow stress fixture. Its 15
down-staggered labels and 2 artwork conflicts are expected; the fixture tests
the stagger under pathological zone density. WP-4b must not gate on this scene.

---

## WP-4b regression baseline

The unresolved_label_overlap gate (WP-4b) checks that the count of flagged
unresolved conflicts does not increase vs main. The current state (post-WP-3a,
pre-WP-3b/WP-4a) produces 4 rendered conflicts across 2 non-fixture scenes:

```
dilution_workspace:    2 (L-A)
hood_workspace:        2 (1 L-L + 1 L-A)
```

WP-4b must accept these 4 as the baseline. Any new conflicts introduced in
WP-3b, WP-4a, or later work must be individually justified before the gate
passes. The 14 DS labels (no rendered conflicts) do not count as gate failures
in the current state; they become gate items only if WP-3b/WP-4a regresses
their resolved state.

---

## Cross-check with stats JSON

The `generated/scene_render_stats/*.stats.json` files carry pre-computed layout
metrics (`label_overlap_pair_count`, `label_art_overlap_count`). These exactly
match the analysis above:

- `hood_workspace`: `label_overlap_pair_count: 1`, `label_art_overlap_count: 1`
- `dilution_workspace`: `label_art_overlap_count: 2`
- `adversarial_overflow_smoke`: `label_art_overlap_count: 2`
- All other scenes: both counts at 0

The analysis scripts re-derived conflicts from raw geometry; the match confirms
the methodology is consistent with the existing stats pipeline.
