# Decision: remove zone_footprint_balance and row_overcrowding metrics

Status: RATIFIED
Date: 2026-07-05
Scope: validation/scene_design (metrics/balance.py, metrics/density.py,
weights.py, cli.py, suggest.py), tests/e2e/e2e_scene_design_cli.py,
docs/specs/SCENE_DESIGN.md.

## Problem

Two scene-design scorecard metrics rewarded spreading placements across more
zones, in direct conflict with the grouping design intent documented in
[LAYOUT_ENGINE.md](../../specs/LAYOUT_ENGINE.md#zone-population-and-alignment-aesthetics):
"logical grouping wins; keep like with like in one zone and prefer fewer,
fuller zones."

1. `zone_footprint_balance` (`metrics/balance.py`) scored the ratio of the
   most-loaded to least-loaded POPULATED zone. A scene that correctly grouped
   a coherent set of objects into a single zone (the encouraged pattern)
   could not even compute this metric (it needs `>= 2` populated zones), and
   a scene that spread objects across zones to chase evenness scored higher
   than one that grouped them. The metric's own doc note already carried an
   "authoring priority" caveat instructing authors to ignore a low score here
   -- a metric whose own spec tells authors not to trust it is not doing its
   job.

2. `row_overcrowding` (`metrics/density.py`) scored the highest per-zone
   footprint-width load, summed across every `depth_tier` in a zone. A zone
   that correctly grouped several tiered rows (for example a back row of
   three bottles and a front row of two) summed both rows' widths against one
   zone width and was flagged as overcrowded even though each tier row fit its
   line individually. This is the same anti-grouping pressure as (1): it
   pushed authors to split a well-grouped zone into several sparser zones to
   raise the score.

Both metrics required a caveat paragraph in `docs/specs/SCENE_DESIGN.md`
telling authors to disregard the metric's own signal in the common
well-grouped case. A metric that needs an explicit "ignore this metric when
it fires" note is a defect in the metric's design, not a documentation gap.

## Decision

Remove both metrics from the scorecard:

- Delete `zone_footprint_balance` from `validation/scene_design/metrics/balance.py`,
  along with its now-unused `_build_zone_placement_map` helper.
- Delete `row_overcrowding` from `validation/scene_design/metrics/density.py`,
  along with its now-unused `_build_zone_placement_map` and `_zone_inner_width`
  helpers.
- Remove both metrics from `validation/scene_design/weights.py`'s
  `composition` and `zoom_detail` weight tables (the only two classes that
  weighted `zone_footprint_balance`; `row_overcrowding` was never weighted in
  any class). The removed weight is redistributed proportionally across the
  remaining metrics in each class so every class still sums to 1.00.
- Remove the corresponding imports and `compute_metrics` /
  `compute_metrics_from_dict` entries from `cli.py` and `suggest.py`.
- Remove `row_overcrowding` from the dump-consuming metric list asserted by
  `tests/e2e/e2e_scene_design_cli.py`.
- Update `docs/specs/SCENE_DESIGN.md`: drop both metric-catalog rows, both
  weight-table entries, and the two authoring-priority / tier caveats that
  existed only to tell authors to disregard these metrics.

The `zone_reassign` suggest-engine mutation (`_mutate_zone_reassign` in
`suggest.py`) is retained. It is a general-purpose move (try a placement in a
different zone) used to search for score improvements across every metric,
not a mechanism built specifically to chase `zone_footprint_balance`; removing
the two metrics leaves it scored against the remaining metric set with no
code change needed.

## Coverage check: legitimate intent preserved elsewhere

`row_overcrowding`'s own docstring described its target as "a gradient of the
render predictor's MIN_SCALE binary" -- the real overflow-detection intent
(an object does not fit its zone) is already covered by scene-lint rule `B2`
`item_taller_than_zone` in `validation/scene_lint/`, which fires when a
placement's required scale to fit its zone falls below `MIN_SCALE` (0.55; see
[SCENE_LINT.md](../../specs/SCENE_LINT.md)). That rule is a hard render-risk
gate, not an advisory 0-100 score, and it does not share `row_overcrowding`'s
tier-blind flaw (it evaluates one placement against its own zone, not a
summed cross-tier width). No replacement metric is needed in scene_design.

`zone_footprint_balance` had no equivalent legitimate intent to preserve: its
only stated purpose was footprint evenness across zones, which is the
behavior this decision rejects.

## Consequence

Scene-design scorecards now carry 14 metrics instead of 16. Historical
`scorecard_history.jsonl` rows written before this change still carry the
two removed keys in their `metric_values` object; the history reader
(`load_history`) does not require a fixed key set, so old rows remain
readable. `quarterly.py` reports whichever metrics are present per row and is
unaffected.
