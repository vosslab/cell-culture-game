# Missing SVG degradation ledger

Audit date: 2026-06-10. Scope: all 38 scenes in `generated/scene_render_stats/`.
Purpose: identify which scenes render with orange placeholder boxes, whether each
gap is documented in `assets/SVG_ASSET_GAPS.md`, and note how the placeholder
geometry affects label and bbox interpretation during WP-6 layout review.

Field glossary (from stats JSON schema):

- `missing_object_names`: object_ids that have no SVG and render as orange placeholder boxes.
- `placeholder_item_count`: count of placeholders actually rendered.
- `advisory_flags: ["degraded"]`: set when one or more objects render as placeholders.
- `no_missing_assets: false`: pass-fail gate that fires whenever `missing_object_names` is non-empty.

---

## Summary

| Metric | Count |
| --- | --- |
| Total scenes in stats corpus | 38 |
| Degraded curriculum/smoke scenes (advisory_flags=degraded) | 34 |
| Dev fixture scenes (placeholder-only, not degraded flag) | 2 |
| Clean scenes (no placeholders) | 2 |
| Distinct missing object_id types (curriculum + smoke, excl. dev fixtures) | 16 |
| Object types documented in SVG_ASSET_GAPS.md | 3 |
| Object types NOT documented in SVG_ASSET_GAPS.md | 13 |

Note: `missing_svg_check` and `type_check` are intentional dev fixture scenes
(classification: `placeholder-only`). They exist to test the placeholder rendering
path; their missing objects (`test_missing_svg_target`, `cell_count_pad`) are not
curriculum objects. They are listed separately below and excluded from undocumented-gap counts.

---

## Undocumented gaps (not in SVG_ASSET_GAPS.md)

The following missing object types appear in curriculum or standard smoke scenes but
have no entry in `assets/SVG_ASSET_GAPS.md`. Each needs to be added to that file.

| Object type | Appears in N scenes | Notes |
| --- | --- | --- |
| `centrifuge` | 4 | Appears in bench, centrifuge, dilution, drug_dilution bench scenes |
| `water_bath` | 4 | Appears in bench, dilution, drug_dilution, mtt prep/readout bench scenes |
| `vortex` | 7 | Most common gap; appears across bench, centrifuge, dilution, incubator, mtt, seeding scenes |
| `p10_gel_loading_tip_box` | 10 | Most widespread gap; all SDS-PAGE scenes plus heat_block, extraction, electrophoresis, sample_prep |
| `gel_comb` | 7 | All SDS-PAGE gel/electrophoresis scenes plus extraction |
| `hood_surface` | 5 | hood_basic, hood_workspace, plate_workspace, plate_drug_treatment, seeding, passage_hood_detachment_hood |
| `incubator` | 3 | hood_workspace, incubator_workspace, seeding_workspace |
| `lightbox` | 1 | imaging_bench |
| `rocking_shaker` | 2 | imaging_bench, sdspage_destain_gel_rock |
| `microscope` | 3 | hemocytometer_view, microscope_basic, passage_hood_detachment_microscope_view |
| `microwave` | 2 | sdspage_destain_gel_rock, staining_bench |
| `plate_reader` | 1 | mtt_solubilization_readout_plate_reader_workspace |
| `heat_block` | 4 | bench_basic, heat_block_bench, sdspage_heat_denature, + listed in SVG_ASSET_GAPS under collapsed-state-pair (SVG exists but only one state) |

Note on `heat_block`: `SVG_ASSET_GAPS.md` lists it under "Collapsed state-pair art"
(has SVG, renders `heat_block_closed`, but no open/closed swap yet). The stats system
still flags it as `missing_object_names`, meaning the object_id lookup fails or the
asset is not registered under the expected name. This discrepancy needs investigation.

---

## Documented gaps (in SVG_ASSET_GAPS.md)

| Object type | SVG_ASSET_GAPS.md section | Scenes affected | Placeholder effect |
| --- | --- | --- | --- |
| `power_supply` | Placeholder objects | electrophoresis_bench, extraction_workspace, sdspage_attach_lid_and_leads, sdspage_fill_tank_buffer, sdspage_load_sample_single_lane, sdspage_prepare_running_buffer, sdspage_recycle_buffer, sdspage_run_electrophoresis | Placeholder is a fixed-size orange box. Its bbox is smaller and differently shaped than a real power supply. Label sits below box at expected label_y; bbox width and height unreliable for overlap checks. |
| `cell_counter` | Interim or hand-authored art | cell_counter_basic, cell_counter_workspace | Note: stats flag cell_counter as `missing_object_names` even though SVG_ASSET_GAPS.md says hand-authored art exists. Either the object_id lookup is broken or the asset path name differs. Real geometry may be present but not measured correctly. |
| `gel_opening_tool` | Placeholder objects | Not seen in any current stats file (object may not be placed in any active scene) | N/A currently. |
| `kimwipe_pad` | Placeholder objects | Not seen in any current stats file | N/A currently. |
| `electrode_module` | Placeholder objects | Not seen in any current stats file | N/A currently. |

---

## Per-scene degradation table

Scenes are sorted by name. "Placeholders" = `placeholder_item_count`. "Doc status" = whether all missing objects appear in `SVG_ASSET_GAPS.md`. Bbox/label note describes how placeholders distort layout review.

### bench_basic

| Field | Value |
| --- | --- |
| Placeholders | 4 |
| Missing objects | `centrifuge`, `water_bath`, `heat_block`, `vortex` |
| Doc status | `heat_block` partially documented (state-pair); `centrifuge`, `water_bath`, `vortex` UNDOCUMENTED |
| Bbox/label note | Four large placeholders replace major bench instruments; their uniform orange-box size makes spacing appear more even than real art would. Do not read zone coverage or inter-object spacing as representative. |

### cell_counter_basic

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `cell_counter` |
| Doc status | Documented under interim art; however stats flag it as missing, suggesting asset path mismatch |
| Bbox/label note | Single placeholder replaces the main cell counter instrument. The bbox area and aspect ratio of the placeholder will not match real cell-counter art; label position is fixed below a generic-sized box. |

### cell_counter_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `cell_counter` (contributes 2 placeholders, likely two placed instances) |
| Doc status | Same as cell_counter_basic; interim-art documented but flagged missing in stats |
| Bbox/label note | Two placeholders for same missing object type; both are identically sized orange boxes. Any overlap or spacing check against them is unreliable. |

### centrifuge_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `centrifuge`, `vortex` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Centrifuge placeholder will be far smaller than a real centrifuge footprint; vortex placeholder similarly undersized. Zone occupancy readings misleading. |

### dilution_workspace

| Field | Value |
| --- | --- |
| Placeholders | 3 |
| Missing objects | `centrifuge`, `water_bath`, `vortex` |
| Doc status | All UNDOCUMENTED |
| Bbox/label note | Three placeholders; bench instruments replaced by uniform-sized boxes. Layout density and overlap metrics will read false-clean. |

### drug_dilution_setup_bench_setup

| Field | Value |
| --- | --- |
| Placeholders | 3 |
| Missing objects | `centrifuge`, `water_bath`, `vortex` |
| Doc status | All UNDOCUMENTED |
| Bbox/label note | Same as dilution_workspace. Three bench instruments are orange boxes; spacing and occupancy metrics are not meaningful. |

### electrophoresis_bench

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Five placeholders including the large power supply. The power supply box occupies a different footprint than real art would. The gel_comb and tip_box placeholders are also generic-sized. Treat all five positions as geometry-unknown. |

### extraction_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same pattern as electrophoresis_bench. Five placeholder objects; treat all five bbox positions as unreliable for layout scoring. |

### heat_block_bench

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `heat_block`, `p10_gel_loading_tip_box` |
| Doc status | `heat_block` partially documented (state-pair art section) but stats flag it as missing; `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | This is the reference example cited in the task spec. The heat_block placeholder is a generic orange box; the p10 tip box placeholder similarly. Two object positions have unreliable bbox dimensions. |

### hemocytometer_view

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `microscope` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Single large placeholder for the microscope. The microscope is a major scene object; its placeholder will substantially underrepresent the real footprint. Label is below the orange box, not below a correctly scaled instrument. |

### hood_basic

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `hood_surface` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | The hood_surface is the dominant background element of hood scenes. Its placeholder replaces the wide tabletop graphic; scene appears to float items on a plain background. Any hood-specific spatial reasoning from this scene is unreliable. |

### hood_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `hood_surface`, `incubator` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Hood background and incubator both placeholder. Double displacement; rear zone items appear against plain background. Incubator is large; its real art would significantly change rear-zone packing. |

### imaging_bench

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `lightbox`, `rocking_shaker` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Both major instruments on the imaging bench are placeholder boxes. The real lightbox is wide and flat; the rocking shaker is bulky. Placeholder sizes do not represent either. |

### incubator_workspace

| Field | Value |
| --- | --- |
| Placeholders | 3 |
| Missing objects | `incubator`, `vortex` (3 placeholders from 2 missing types, suggesting multiple placements) |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | The incubator is also flagged in SVG_ASSET_GAPS.md (build follow-ups section) as rendering too large and clipping the rear_right zone. Without real art, the placeholder size obscures whether that size bug is resolved. |

### microscope_basic

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `microscope` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Same as hemocytometer_view. The microscope placeholder is the only item; bbox is generic orange box, not microscope-shaped. |

### missing_svg_check (dev fixture)

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `test_missing_svg_target` |
| Doc status | Intentional dev fixture; not a curriculum object. Not a gap to document. |
| Bbox/label note | Single-object placeholder-only scene for testing the placeholder path. Ignore for layout review. |

### mtt_reagent_prep_bench_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `water_bath`, `vortex` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Two bench instruments replaced by boxes. Bench occupancy and zone spacing metrics are not representative. |

### mtt_solubilization_readout_bench_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `water_bath`, `vortex` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Same as mtt_reagent_prep_bench_workspace. |

### mtt_solubilization_readout_plate_reader_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `plate_reader`, `vortex` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | The plate reader is the primary instrument in this scene; its placeholder is a generic box that does not represent the real footprint. Any label alignment check against this scene is against the wrong geometry. |

### passage_hood_detachment_hood_workspace

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `hood_surface` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Same as hood_basic. Hood background is a wide placeholder; foreground items float without correct spatial context. |

### passage_hood_detachment_microscope_view

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `microscope` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Same as microscope_basic. |

### plate_drug_treatment_media_adjustment_plate_workspace

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `hood_surface` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Hood background is a placeholder. Foreground plate and liquid objects display against plain background; their relative positions are still valid, but background-relative spatial reasoning is unreliable. |

### plate_workspace

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `hood_surface` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Same as plate_drug_treatment scene. |

### sample_prep_bench

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `p10_gel_loading_tip_box` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Single placeholder for the gel-loading tip box. Tip box placeholder is small; its bbox footprint is likely near-correct in size, but the aspect ratio and exact dimensions will differ from real art. |

### sdspage_attach_lid_and_leads_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same pattern as electrophoresis_bench and extraction_workspace. Five placeholder positions; power supply footprint especially unreliable. |

### sdspage_destain_gel_rock_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `microwave`, `rocking_shaker` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Both instruments are placeholder boxes. The microwave is typically a large item; its placeholder will not represent its real footprint. |

### sdspage_fill_tank_buffer_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same as sdspage_attach_lid_and_leads_workspace. |

### sdspage_heat_denature_samples_workspace

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `heat_block`, `p10_gel_loading_tip_box` |
| Doc status | `heat_block` partially documented (state-pair); `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same pattern as heat_block_bench. |

### sdspage_load_sample_single_lane_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same as sdspage_fill_tank_buffer_workspace. |

### sdspage_prepare_running_buffer_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same as other SDS-PAGE gel scenes. |

### sdspage_prepare_sample_mix_single_lane_workspace

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `p10_gel_loading_tip_box` |
| Doc status | UNDOCUMENTED |
| Bbox/label note | Single placeholder for the gel-loading tip box. Same note as sample_prep_bench. |

### sdspage_recycle_buffer_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same as other SDS-PAGE gel scenes. |

### sdspage_run_electrophoresis_workspace

| Field | Value |
| --- | --- |
| Placeholders | 5 |
| Missing objects | `gel_comb`, `power_supply`, `p10_gel_loading_tip_box` |
| Doc status | `power_supply` documented; `gel_comb` and `p10_gel_loading_tip_box` UNDOCUMENTED |
| Bbox/label note | Same as other SDS-PAGE gel scenes. The power supply is actively used during this step; its placeholder geometry is especially misleading in an electrophoresis-run scene. |

### seeding_workspace

| Field | Value |
| --- | --- |
| Placeholders | 3 |
| Missing objects | `hood_surface`, `vortex`, `incubator` |
| Doc status | All UNDOCUMENTED |
| Bbox/label note | Hood background and two instruments are placeholders. Rear zone geometry is doubly unreliable: hood surface is a plain background and incubator is a generic box. |

### staining_bench

| Field | Value |
| --- | --- |
| Placeholders | 2 |
| Missing objects | `microwave`, `rocking_shaker` |
| Doc status | Both UNDOCUMENTED |
| Bbox/label note | Same as sdspage_destain_gel_rock_workspace. |

### type_check (dev fixture)

| Field | Value |
| --- | --- |
| Placeholders | 1 |
| Missing objects | `cell_count_pad` |
| Doc status | Intentional dev fixture; not a curriculum object. Not a gap to document. |
| Bbox/label note | Single-object placeholder-only scene for type-system testing. Ignore for layout review. |

---

## Reviewer guidance for WP-6

When reviewing a degraded scene during a label-alignment pass:

1. Check this ledger before interpreting layout metrics. If the scene is in the
   degraded table, note which object_ids are placeholders before reading the stats.
2. Orange placeholder boxes have a uniform generic size that does not match the real
   instrument footprint. Do not flag a spacing issue as a layout bug if the spacing
   is relative to a placeholder.
3. The `label_overlap_pair_count` and `label_art_overlap_count` fields in the stats
   may be artificially low (placeholder is smaller than real art, so labels do not
   overlap the placeholder even though they would overlap the real asset).
4. The `percent_empty_approx` field will read too high for scenes with large
   instruments missing (e.g. centrifuge, incubator, microscope).
5. For clean layout review results, only trust the geometry of objects listed as
   `real_item_count` in the stats. Placeholder-backed objects should be treated as
   geometry-unknown for spacing and alignment purposes.

---

## Discrepancies to investigate

Two documented objects in `SVG_ASSET_GAPS.md` appear in stats as `missing_object_names`
despite being described as having some form of asset:

| Object | SVG_ASSET_GAPS.md claim | Stats evidence | Action needed |
| --- | --- | --- | --- |
| `heat_block` | Listed under collapsed-state-pair (has `heat_block_closed` SVG) | Appears in `missing_object_names` in bench_basic, heat_block_bench, sdspage_heat_denature | Confirm whether the asset path registration matches what the scene lookup expects |
| `cell_counter` | Listed under interim art (has hand-authored SVG) | Appears in `missing_object_names` in cell_counter_basic, cell_counter_workspace | Confirm whether the asset path or object_id registration is correct |
