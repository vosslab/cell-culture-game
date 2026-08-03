# Per-band uniform-rescale scale-floor decision record

- Date: 2026-07-04
- Status: decision-ready, awaiting architect routing
- Author: scene-layout manager

## Mechanism

The scene-wide `uniform_rescale` is one vertical-stack-fit factor applied to
every object's width AND height (aspect preserved), clamped to `[floor, 1]`.
When `label_dominant` is true, that factor is driven by label vertical
overflow, NOT by object tier-row overhead. Source:

Consequence: one over-tall label band sets the scale for every unrelated object
in the scene; a tier collapse yields ZERO factor gain on these scenes.

## Affected scenes

These scenes report `label_dominant=True` and `tier_collapsible=False`, from the
combined table.

| scene | factor | mean_final_scale | crowd_bound | tcoll |
| --- | --- | --- | --- | --- |
| electrophoresis_bench | 0.58 | 0.58 | 0 | False |
| sdspage_attach_lid_and_leads_workspace | 0.58 | 0.58 | 0 | False |
| sdspage_fill_tank_buffer_workspace | 0.58 | 0.58 | 0 | False |
| sdspage_prepare_running_buffer_workspace | 0.58 | 0.58 | 0 | False |
| sdspage_recycle_buffer_workspace | 0.58 | 0.58 | 0 | False |
| sdspage_run_electrophoresis_workspace | 0.58 | 0.58 | 0 | False |
| sdspage_load_sample_single_lane_workspace | 0.58 | 0.58 | 0 | False |
| extraction_workspace | 0.58 | 0.57 | 1 | False |
| passage_hood_detachment_hood_workspace | 0.50 | 0.46 | 2 | False |
| hood_workspace (passage_pellet_reseed) | 0.58 | 0.52 | 3 | False |
| plate_drug_treatment_media_adjustment_plate_workspace | 0.51 | 0.50 | 1 | False |

Notes:

- The `passage_hood_detachment_hood_workspace` row carries the documented T7
  floor 0.499.
- The seven SDS-PAGE children plus `electrophoresis_bench` are crowd=0 (pure
  label-dominant, the cleanest demonstration).
- The last three rows are label-dominant AND crowd-bound.

## Corrected predicate

Stated plainly: `crowd_bound == 0` alone does NOT predict a clean collapse. The
correct predicate is `crowd_bound == 0 AND not label_dominant`, encoded as the
tool's `tcoll` flag. A crowd=0 but label-dominant scene (the SDS-PAGE family)
yields zero gain from a collapse. This corrects an earlier "crowd=0 = collapse
win" heuristic.

## Contrast evidence

This evidence proves tier-collapse DOES work when a scene is not
`label_dominant`, so the lever is finished, not broken. Before/after
`final_scale` factor:

| scene | before | after |
| --- | --- | --- |
| drug_dilution_setup/bench_setup | 0.604 | 1.000 |
| mtt_solubilization_readout/bench_workspace | 0.653 | 1.000 |
| mtt_plate_reaction/incubator_workspace | 0.667 | 1.000 |

These were crowd=0 AND not `label_dominant`; they collapsed to full size. The
label-dominant family cannot.

## Recommendation

Add per-band or per-object scale floors (or a per-band uniform factor keyed on
the tier-rows that actually overflow) so a label-dominant band stops setting the
factor for the whole scene; non-overflowing bands stay at scale 1.0. This is a
layout-model change in
architect-owned.

## Cross-references

- Prior audit:
- Inspection tool:
- Metrics dir:

The separate `centrifuge_workspace` (crowd=4) engine-only evidence travels to
the architect alongside this record.
