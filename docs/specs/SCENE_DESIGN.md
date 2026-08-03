# Scene design

Specification for the `validation/scene_design/` package: composition-quality
scorecard that mirrors the post-render `LAYOUT_SCORECARD.md` model but
consumes simulator output instead of `precheck.mjs`, so it runs in seconds
against an in-progress YAML.

Scope boundaries:

- Scene design **scores** composition quality on a 0-100 scale. It does not
  predict render failures (that is [SCENE_LINT.md](SCENE_LINT.md)).
- Scene design **never gates** the validation pipeline; the CLI always exits
  0 unless invoked with a missing scene path. Scores are comparative, not
  absolute.
- Scene design **does not score** scenes the render predictor would mark
  broken (`gated_by_render_predictor` field reserved for that signal; see
  [#scorecard-shape](#scorecard-shape)).
- Scene design **consumes** the same rendered geometry as scene lint, loaded
  by `validation/scene_calc/dump.py` from `generated/scene_render_stats/<scene>.stats.json`.
  The single geometry producer is the browser render pipeline
  (`tools/scene_to_png.mjs` -> `tools/scene_stats.mjs`); scene_calc computes no
  layout. Metrics that need geometry return None when the stats file is missing
  (the loader fails loudly rather than predicting). Render first:
  `node tools/scene_to_png.mjs --all`.

## CLI surface

Invocation: `source source_me.sh && python3 -m validation.scene_design.cli`.

Shared flags (`-S/--scene`, `-O/--only`) come from
`validation/shared_toolkit/cli.py`. Scene-design-specific flags:

| Flag | Argument | Default | Effect |
| --- | --- | --- | --- |
| `-m`, `--markdown` | none | off | Emit cards as Markdown sections instead of JSONL. |
| `--no-history` | none | off | Skip writing a row to the scorecard history archive. |

### Exit codes

| Code | Condition |
| --- | --- |
| 0 | Always, when scenes load + classify cleanly. Scene design is advisory only. |
| 1 | Scene YAML failed to load, scene-class detection raised. |
| 2 | Invocation error (missing `-S`, invalid glob). |

## Scorecard shape

Defined in `validation/scene_design/cards.py`. JSONL writer emits one JSON
object per line; Markdown writer (`-m`) emits one `## <scene>` section
per card.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `scene` | str | yes | Scene name. |
| `class` | str | yes | Detected scene class (see [#scene-class-detection](#scene-class-detection)). |
| `score` | float or null | yes | Weighted-sum design score in `[0, 100]`. Null when any required metric for the class is None. |
| `confidence` | str | yes | `computed` (dump succeeded) or `partial` (dump failed; dump-consuming metrics returned None). |
| `gated_by_render_predictor` | bool | yes | Reserved for future integration with scene lint render-blocking findings. Currently always `false`. |
| `metrics` | object | yes | Map of metric name -> score (float 0-100) or null. See [#metric-catalog](#metric-catalog). |
| `suggestions` | list | yes | Advisory move suggestions from [#suggest-engine](#suggest-engine). Empty list when the engine is not invoked or no monotonic improvement found. |

Example JSONL row:

```json
{"scene":"bench_basic","class":"composition","score":56.67,"confidence":"computed","gated_by_render_predictor":false,"metrics":{"primary_area_ratio":61.76,"support_distance":74.30, ...},"suggestions":[]}
```

## Scene-class detection

Classes are mutually exclusive. Detection follows a strict 5-step order in
`validation/scene_design/class_detect.py::detect`:

| Step | Test | Class |
| --- | --- | --- |
| 1 | `len(scene['placements']) == 0` | `template` |
| 2 | `len(scene['placements']) == 1` | `zoom_detail` |
| 3 | `len(scene['placements']) >= 10` | `dense_clutter` |
| 4 | Primary placement (`data-primary: true`) has `kind in {'instrument', 'equipment'}` | `instrument_heavy` |
| 5 | Default fallback | `composition` |

Detection raises `SceneClassError` only on structural errors (`scene` is
not a dict, `scene_name` missing, `placements` is not a list). A scene
that fails detection cannot be scored; the CLI exits 1.

Placement-count classes are derived from valid scene structure. Authors do not
add a separate classification field to scene YAML.

Known limitations (decision-gated):

- Step 3 reads `scene['placements']`; row-slot scenes carry `rows[]` /
  `slots[]` instead and currently classify as `composition`.
- Step 4 reads `placement['kind']`, which is an object-library field, not
  an authored placement field; in the current corpus no placement carries
  `kind` on the placement itself, so step 4 never fires.

## Per-class weight tables

Weight tables in `validation/scene_design/weights.py`. Each class's
weights sum to 1.00. Metrics not listed in a class's table do not
contribute to that class's score.

### template (no placements)

| Metric | Weight |
| --- | --- |
| `predicted_label_overlap` | 0.40 |
| `label_wrap_rate` | 0.40 |
| `largest_empty_band` | 0.20 |

### composition (default fallback)

| Metric | Weight |
| --- | --- |
| `primary_area_ratio` | 0.28 |
| `support_distance` | 0.24 |
| `scene_density` | 0.18 |
| `predicted_label_overlap` | 0.18 |
| `aspect_fidelity` | 0.06 |
| `label_wrap_rate` | 0.06 |

### instrument_heavy (primary is instrument or equipment)

| Metric | Weight |
| --- | --- |
| `primary_area_ratio` | 0.35 |
| `support_distance` | 0.20 |
| `scene_density` | 0.15 |
| `predicted_label_overlap` | 0.15 |
| `aspect_fidelity` | 0.10 |
| `label_wrap_rate` | 0.05 |

### zoom_detail (one placement)

| Metric | Weight |
| --- | --- |
| `primary_area_ratio` | 0.56 |
| `scene_density` | 0.22 |
| `predicted_label_overlap` | 0.11 |
| `label_wrap_rate` | 0.11 |

### dense_clutter (`>=10` placements)

| Metric | Weight |
| --- | --- |
| `predicted_label_overlap` | 0.30 |
| `label_wrap_rate` | 0.25 |
| `support_distance` | 0.20 |
| `scene_density` | 0.10 |
| `aspect_fidelity` | 0.10 |
| `primary_area_ratio` | 0.05 |

## Score aggregation

`validation/scene_design/score.py::aggregate_score(metrics, scene_class)`.

NotReady semantics: if ANY metric in the class's weight table is None, the
aggregate returns None. This protects against partial scores that would
mislead reviewers; a scene with one missing metric is reported as
`"score": null` with `confidence: partial`.

When all required metrics are non-None:

```
score = sum(metric_value * weight for metric, weight in class_weights)
```

Each metric returns a 0-100 float; the weighted sum stays in `[0, 100]`.

`aggregate_score` raises `ValueError` if the scene class is not in
WEIGHTS (programming error; the class enum is closed).

## Metric catalog

All metrics live under `validation/scene_design/metrics/`. Each function
takes `(scene, dump_data)` and returns `float | None`. None means
NotReady (missing inputs, degenerate geometry, or class-specific opt-out).

### Hierarchy (`metrics/hierarchy.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `primary_area_ratio(scene, dump)` | primary footprint area / total footprint area, scaled 0-100 | None if no placements |
| `primary_prominence(scene, dump)` | primary area / largest supporter area, normalized to 2x target, 0-100 | None if no supporters |
| `primary_detection_confidence(scene)` | 100 if explicit `data-primary: true`, 50 if heuristic fallback, None if no placements | Scene-only (no dump required) |

### Balance (`metrics/balance.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `largest_empty_band(scene, dump)` | 100 minus 200-pts-per-unit penalty on largest contiguous empty band as fraction of scene; floors at 0 | Grid-scan over horizontal and vertical bands |
| `scene_occupied(scene, dump)` | 100 inside target band `[0.15, 0.70]`, linear penalty outside | total footprint area / scene area |

`largest_empty_band` intentionally does not punish a deliberately empty
zone unless it leaves a large contiguous dead band; an empty zone beside a
well-grouped one is acceptable.

`zone_footprint_balance` (footprint evenness across zones) and
`row_overcrowding` (per-zone row-load) were removed: both rewarded spreading
objects across more zones, which fights the grouping intent in
[LAYOUT_ENGINE.md](LAYOUT_ENGINE.md#zone-population-and-alignment-aesthetics).
See
[scorecard_metric_spec_discrepancy.md](../archive/decisions/scorecard_metric_spec_discrepancy.md)
for the removal record.

### Proximity (`metrics/proximity.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `support_distance(scene, dump)` | 100 at distance 0, 0 at normalized distance `>= 0.50` | Mean Euclidean distance from supporters to primary center, normalized by scene diagonal |
| `protocol_step_affinity(scene)` | Always None (skeleton) | Protocol-vocabulary access not yet wired |

### Labels (`metrics/labels.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `predicted_label_overlap(scene, dump)` | 100 at no collisions; degrades linearly to 0 | Fraction of placements whose `label_bbox` intersects another footprint or label bbox |
| `label_to_object_distance(scene, dump)` | 100 at distance 0, 0 at normalized distance `>= 0.25` | Mean center-to-center gap between label and footprint, normalized by scene diagonal |
| `label_wrap_rate(scene, dump)` | 100 at no wrapping | Fraction of labels with height > 5.0 scene-% (predicted wrap) |

### Density (`metrics/density.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `scene_density(scene, dump)` | Same target band and scoring formula as `scene_occupied` | Total footprint area / scene area |

`row_overcrowding` was removed; see the Balance section above for the removal
note. Its legitimate overflow-detection intent (an object not fitting its
zone) is covered by scene-lint rule `B2` `item_taller_than_zone`, which fires
when a placement's required scale to fit its zone falls below `MIN_SCALE`
(see [SCENE_LINT.md](SCENE_LINT.md)).

### Composition (`metrics/composition.py`)

| Metric | Returns | Notes |
| --- | --- | --- |
| `tab_stops_symmetry(scene, dump)` | 100 when populated columns have equal width sums; -20 pts/unit when max/min ratio > 1.0 | None when `< 2` populated columns |
| `depth_tier_usage(scene, dump)` | `distinct_tiers / 3 * 100` | Distinct tiers inferred from zone names (rear=1, mid=2, front=3) |
| `aspect_fidelity(scene, dump)` | 100 minus mean `aspect_delta_pct` across valid placements | None when all placements have `scale_source='skipped_error'` |

## History archive

Source: `validation/scene_design/archive.py`. Default path is
`test-results/scene_design/history/scorecard_history.jsonl`. The directory
is gitignored; the archive is a runtime artifact.

Each CLI invocation appends one JSONL row per scored scene unless
`--no-history` is set:

| Field | Type | Description |
| --- | --- | --- |
| `run_id` | str | ISO-8601 UTC timestamp, seconds precision. |
| `date_utc` | str | `YYYY-MM-DD` derived from `run_id`. |
| `scene` | str | Scene name. |
| `class` | str | Detected scene class. |
| `score` | float or null | Aggregate score, or null if NotReady. |
| `metric_values` | object | Every current metric with its per-scene value. |

Read API:

| Function | Returns | Behavior on missing file |
| --- | --- | --- |
| `load_history(path)` | `list[dict]` | Returns `[]` |
| `score_for_run(history, scene, run_id)` | `float` or None | Returns None if not found |
| `score_quarter_range(history, scene, start_date, end_date)` | `list[dict]` | Filters history by scene + date range |

`load_history` raises `json.JSONDecodeError` on malformed lines (no
silent skip).

Decision-gated: `score_at_commit(scene, sha)` was dropped during the
2026-05-24 plan revision (agents have no git access). `score_for_run`
keyed on `run_id` replaces it.

## Quarterly report

Source: `validation/scene_design/quarterly.py`. Manual-trigger only; no
scheduling.

Canonical invocation:

```
source source_me.sh && python3 -m validation.scene_design.quarterly \
    --quarter 2026-Q2 \
    --history-path test-results/scene_design/history/scorecard_history.jsonl \
    --out docs/active_plans/active/scene_lint/scorecard_quarterly_2026-Q2.md
```

| Argument | Required | Default | Meaning |
| --- | --- | --- | --- |
| `--quarter` | yes | n/a | `YYYY-Qn` (1 through 4). |
| `--history-path` | no | `test-results/scene_design/history/scorecard_history.jsonl` | Archive to read. |
| `--out` | yes | n/a | Markdown output file path; parent directories created. |

Quarter-to-date mapping (`quarter_to_dates`):

| Quarter | Months | End day |
| --- | --- | --- |
| Q1 | 01-03 | 31 |
| Q2 | 04-06 | 30 |
| Q3 | 07-09 | 30 |
| Q4 | 10-12 | 31 |

Report contents:

- Score-change table per scene, ranked by largest swing (`max - min`).
- "Bottom decile" section listing the lowest-scoring 10% of scenes when
  `>= 10` scenes have data.
- Methodology footer explaining min/max-bound semantics (chronological
  first/last is not used).

## Suggest engine

Source: `validation/scene_design/suggest.py`. Library-only; no CLI
entry point.

Public entry point:

```
suggest_moves(scene_path: Path, n_suggestions: int = 1) -> list[dict]
```

Returns suggestions only for scenes scoring below their per-class floor.
Each suggestion dict carries `placement_name`, `move_type`,
`move_description`, `baseline_score`, `projected_score`, `score_delta`.

### Class floors

Module-level constant `CLASS_FLOORS` in `suggest.py`:

| Class | Floor |
| --- | --- |
| `template` | 70.0 |
| `composition` | 65.0 |
| `instrument_heavy` | 65.0 |
| `zoom_detail` | 70.0 |
| `dense_clutter` | 60.0 |

`DEFAULT_CLASS_FLOOR = 65.0` for unknown classes.

### Mutation classes

| Type | Mutator | Parameters |
| --- | --- | --- |
| `zone_reassign` | `_mutate_zone_reassign(scene, placement_name, new_zone_name)` | Iterates over every authored zone (per SPEC_DESIGN_CHECKLIST.md rule 25, zones use `zone_name` keys). |
| `display_width_cm_adjust` | `_mutate_display_width_cm(scene, placement_name, delta_cm)` | Deltas: `+/- 10, 20, 30` cm; floors at 0 (removes the field). |
| `data_primary_flip` | `_mutate_data_primary_flip(scene, placement_name)` | Toggles `data-primary`; default `False` if absent. |

### Guards

Score-monotonicity guard: a candidate move is dropped if its projected
score is not strictly greater than the baseline. Enforced inside the
candidate loop in `suggest_moves`.

Render-risk guard: before emit, `_check_render_risk` writes the mutated
scene to a temp YAML, runs the full scene-lint rule set, and filters
moves that introduce new `(rule, placement_name)` keys in the
ESCAPE_REQUIRED set vs. baseline. Filtered moves are logged via the
suppressed list but never returned to the caller.

### Known limitation (decision-gated)

`dump_scene_geometry` now loads rendered geometry from a scene's
`generated/scene_render_stats/<scene>.stats.json`. The suggest engine scores
hypothetical *mutated* scenes, which have never been rendered and so have
no stats.json. The loader raises `RuntimeError` for the missing file,
`_score_mutation` catches it and returns None, and the engine produces zero
monotonic-improvement suggestions in practice. This is correct by the
validator-follows-generator design: a layout cannot be validated until it is
rendered. The fix path is to render candidate mutations through the browser
pipeline before scoring them (a render-in-the-loop suggest engine), not to
re-introduce a Python geometry model.

## Pipeline integration

Scene design runs as a stage in `validation/validate.py` alongside the
other validation tools. Always advisory; never affects the validate-suite
exit code. See [../USAGE.md](../USAGE.md) for stage order.

## Dependencies

| Module | Purpose |
| --- | --- |
| `validation/scene_calc/dump.py` | `dump_scene_geometry(path)` feeds every dump-consuming metric. |
| `validation/scene_lint/cli.py` | `run_all_rules` consumed by the render-risk guard. |
| `validation/scene_lint/findings.py` | `Verdict` enum used to identify ESCAPE_REQUIRED findings. |
| `validation/shared_toolkit/yaml_io.py` | YAML loader. |
| `validation/shared_toolkit/cli.py` | Shared argparse base (`-S/--scene`, `-O/--only`). |

## References

- [SCENE_LINT.md](SCENE_LINT.md) - sibling render-failure predictor tool.
- [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) - geometry primitives and units consumed via the SIM dump.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) - canonical scene terms.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) - authored YAML schema.
- [SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md) - vocabulary closure rules.
- `design_advice/SCENE_DESIGN_LINT_PLAN.md` - original v1 design proposal (pre-implementation).
