# Scene lint

Specification for the `validation/scene_lint/` package: pre-render predictor
that answers "will this scene render, or trigger fail-loud?" Emits findings
with one of three verdicts and exits the process accordingly.

Scope boundaries:

- Scene lint **predicts** render failures from scene YAML; it does not render
  scenes. The browser-side renderer + `precheck.mjs` remain authoritative for
  post-render verification.
- Scene lint **gates** the validation pipeline only on `BLOCKED` findings.
  `ESCAPE_REQUIRED` findings stay advisory until promoted to strict via
  [#promotion-config](#promotion-config) and `--strict`.
- Scene lint **does not score** composition quality. That belongs to
  [SCENE_DESIGN.md](SCENE_DESIGN.md).
- Scene lint **consumes** rendered geometry, never a Python layout model. The
  single geometry producer is the browser render pipeline
  (`tools/scene_to_png.mjs` -> `tools/scene_stats.mjs`), which lays out every
  shipped scene through the real TypeScript layout engine and writes the
  rendered bounding boxes to `generated/scene_render_stats/<scene>.stats.json`.
  `validation/scene_calc/dump.py` is a thin loader of that stats file; it
  performs no layout math. When the validator disagrees with the render, the
  validator is wrong by definition (the generator wins). If a scene's
  stats.json is missing, the loader fails loudly (Group B is skipped with a
  `dump_error` finding); it never re-derives geometry. Render first:
  `node tools/scene_to_png.mjs --all`. See
  [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) for the layout primitives the renderer
  applies.

The two-tool split (lint vs. design) is intentional: a single mega-lint
mixing render failures and composition advisories failed in practice
(7 CSS trials chasing precheck hard-fail counts that conflated the two).

## CLI surface

Invocation: `source source_me.sh && python3 -m validation.scene_lint.cli`.

Shared flags (`-S/--scene`, `--strict`, `-O/--only`) come from
`validation/shared_toolkit/cli.py`. Scene-lint-specific flags:

| Flag | Argument | Default | Effect |
| --- | --- | --- | --- |
| `--report-only` | none | off | Print findings; do not exit non-zero. |
| `--suppressions` | path | none | Load Group B suppression manifest before applying advisories. |
| `--promotions` | path | `validation/scene_lint/promotions.yaml` | Load promotion config when `--strict` is set. |
| `--no-promotions` | none | off | Skip promotion loading even when `--strict` is set. |
| `--validate-against` | path | none | Path to labeled corpus YAML for confusion-table evaluation. |
| `--emit-confusion` | path stem | none | Output stem for per-rule confusion-table Markdown reports. Requires `--validate-against`. |

### Exit codes

| Code | Condition |
| --- | --- |
| 0 | No `BLOCKED` findings; `--strict` either disabled or no promoted-rule `ESCAPE_REQUIRED` findings. |
| 1 | At least one `BLOCKED` finding, OR `--strict` set and at least one `ESCAPE_REQUIRED` from a successfully-promoted rule. |
| 2 | Invocation error (missing `-S`, invalid flag combination, missing path, failed manifest load). |

`--report-only` forces exit 0 regardless of finding count; useful for
diagnostic runs.

## Finding shape

Defined in `validation/scene_lint/findings.py`. JSONL writer
(`write_findings_jsonl`) emits one JSON object per line; Markdown writer
(`write_findings_markdown`) groups findings by scene.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `scene` | str | yes | Scene name where the finding was detected. |
| `placement_name` | str or null | yes | Placement inside the scene; null for scene-level findings. |
| `rule` | str | yes | Rule identifier (`duplicate_scene_name`, `aspect_distorted_predicted`, `B1`, etc.). |
| `verdict` | enum | yes | One of `BLOCKED`, `ESCAPE_REQUIRED`, `CLEAN`. |
| `predicts` | list of str | no | Predicted failure modes (`crop_loss`, `distortion`, `invisible_object`, etc.). |
| `bbox_type` | str | no | Bbox category from the SIM dump (`visual_bbox`, `placement_bbox`, `footprint_bbox`). |
| `confidence` | enum | yes | One of `high`, `medium`, `low`. Derived from `scale_source`. |
| `message` | str | yes | Human-readable explanation. |
| `evidence` | object | no | Diagnostic data (computed values, thresholds, offending field). |
| `fix_hints` | list of str | no | Suggested fixes. |
| `suppressed_by` | str or null | no | Suppression entry identifier if filtered, else null. |

## Verdict semantics

| Verdict | Suppressible | Gates exit code | Meaning |
| --- | --- | --- | --- |
| `BLOCKED` | no | always (CLI exit 1) | Scene cannot enter the layout pipeline; authoring error. |
| `ESCAPE_REQUIRED` | yes (Group B only) | only under `--strict` for promoted rules | Predicted render failure; advisory by default. |
| `CLEAN` | n/a | no | Reserved for positive assertions; not currently emitted by any rule. |

Group A findings (verdict `BLOCKED`) are never suppressible. The escape
hatch for an unwanted Group A finding is to fix the YAML, not to add a
suppression entry; reviewer-agreed deferrals live in
`docs/active_plans/active/scene_lint/group_a_deferrals.md`.

## Confidence derivation

Each Group B finding inherits its confidence from the SIM dump's
`scale_source` for the offending placement:

| `scale_source` | Confidence |
| --- | --- |
| `cm_model` | high |
| `fallback_authored` | medium |
| `fallback_no_workspace` | low |
| `skipped_error` | low |

Low-confidence findings on a promoted rule stay advisory unless the
promotion entry sets `low_confidence_approved: true`. This protects
against false strict-mode failures when only fallback data is available.

## Group A rule catalog

Source: `validation/scene_lint/rules_group_a.py`. All findings carry
`verdict: BLOCKED`, `confidence: high`, and are never suppressible.

| Rule | Trigger | Coordinates with |
| --- | --- | --- |
| `duplicate_scene_name` | Two or more scene YAML files declare the same `scene_name`. | vocab lint (partial overlap) |
| `duplicate_placement_name` | A scene has two placements with the same `placement_name` after inheritance resolution. | vocab lint |
| `forbidden_source_geometry` | Scene YAML supplies coordinates, bounds, baselines, numeric placement geometry, or an unknown source-scene key. | vocab lint |
| `missing_svg_asset` | A placement's `asset` path does not resolve to a file under `assets/`. | unique to scene lint |
| `invalid_svg_viewbox` | A placement's asset SVG has missing or non-positive `viewBox` dimensions. | unique to scene lint |
| `inheritance_unknown_base` | A scene's `extends` references a base that does not exist. | unique to scene lint |
| `inheritance_multi_level` | The `extends` chain is more than one level deep. | unique to scene lint |
| `inheritance_cycle` | The `extends` chain forms a cycle. | unique to scene lint |
| `inheritance_locked_field_mutation` | `reposition_placements` mutates a field other than `zone` or `data-primary`. | unique to scene lint |
| `inheritance_dangling_ref` | `deactivate_placements` or `reposition_placements` targets a placement removed by `remove_placements`. | unique to scene lint |

The coverage matrix at `validation/scene_lint/coverage_matrix.md` enumerates
which Group A rules are owned here vs. delegated to vocab lint.

## Group B rule catalog

Source: `validation/scene_lint/rules_group_b.py`. All findings carry
`verdict: ESCAPE_REQUIRED`. Confidence is derived per
[#confidence-derivation](#confidence-derivation). Findings are suppressible
per [#suppression-manifest](#suppression-manifest).

| Rule | `bbox_type` | Trigger | Notes |
| --- | --- | --- | --- |
| `B1` `aspect_distorted_predicted` | `visual_bbox` | Predicted aspect delta > 5%. | Skips placements with `scale_source='skipped_error'`. |
| `B2` `item_taller_than_zone` | `placement_bbox` | Required scale to fit in zone < `MIN_SCALE` (0.55). | Skips `skipped_error`. |
| `B3` `row_footprint_overflow` | `footprint_bbox` | Sum of row footprint widths exceeds zone inner width. | Skips silently when dump has no row info (row-slot schema not yet wired). |
| `B4` `placement_bbox_outside_scene` | `placement_bbox` | `placement_bbox` extends past `scene_bounds` on any edge. | Zero tolerance; skips `skipped_error`. |
| `B5` `placement_bbox_outside_zone` | `placement_bbox` | `placement_bbox` extends past zone `inner_rect` beyond 4-px tolerance (`~0.347` scene-%). | Skips `skipped_error`. |
| `B6` `item_item_overlap` | `footprint_bbox` | Two placements in the same zone have non-zero `footprint_bbox` intersection. | Each pair reported once. |
| `B7` `label_offscreen` | `label_bbox` | `label_bbox` extends outside `scene_bounds` horizontally. | Left and right edges only. |
| `B8` `label_object_overlap` | `label_bbox` | `label_bbox` intersects a placement's `visual_bbox` with > 10 px^2 area. | Conservative: checks all placements, not just scientific kinds. |
| `B9` `invisible_placement` | `visual_bbox` | Five triggers: area < 100 px^2, height > 2 * zone height, `scale_source='skipped_error'`, missing `default_width`, or `fallback_authored` scale source. | Confidence varies per trigger. |
| `B10` `zone_overlap` | derived zone geometry | Two rendered zones have non-zero intersection. | Uses renderer-produced geometry; source YAML does not contain zone bounds. |

A `dump_error` finding (verdict `BLOCKED`, confidence `low`) is emitted
when `dump_scene_geometry` raises on a scene; all Group B rules for that
scene are skipped, but Group A findings still fire.

## Suppression manifest

Schema enforced by `validation/scene_lint/suppressions.py`. Default path
is unset; pass `--suppressions <path>` to enable.

Manifest top-level shape:

```yaml
suppressions:
  - rule: B1
    scene: bench_basic
    placement_name: rear_left_waste     # optional; null/absent = scene-wide
    reason: Accepted distortion; legacy asset shape
    ticket: VLAB-123
    owner: alice@example.com
    expires: 2026-08-24                 # YYYY-MM-DD
```

Required fields per entry: `rule`, `scene`, `reason`, `ticket`, `owner`,
`expires`. `placement_name` is optional; when absent, the entry matches
every placement under `(rule, scene)`.

Validation rules:

| Condition | Result |
| --- | --- |
| Missing any required field | `malformed_suppression` advisory (HIGH confidence); entry not loaded. |
| `rule` is a Group A rule name | `malformed_suppression` advisory; entry not loaded. |
| `expires` not parseable as `YYYY-MM-DD` | `malformed_suppression` advisory; entry not loaded. |
| `expires` < today (already expired) | `expired_suppression` advisory (MEDIUM confidence); entry not loaded. |
| `expires` within 90 days of today | `malformed_suppression` advisory (HIGH confidence); entry not loaded. |
| All checks pass | Entry loaded; matching findings filtered from output. |

Matching tuple is `(rule, scene, placement_name)`. Suppressed findings are
removed from output entirely (not flagged as `suppressed_by`); the
suppression entry itself emits no advisory.

The "within 90 days" rule reflects the implementation: entries must have
strictly more than 90 days remaining to be accepted. Short-horizon
suppressions are treated as "do the review now"; long-horizon suppressions
commit the owner to a documented justification.

## Promotion config

Schema enforced by `validation/scene_lint/promotion.py`. Default path is
`validation/scene_lint/promotions.yaml`; override with `--promotions
<path>`; disable with `--no-promotions`.

Config top-level shape:

```yaml
promotions:
  - rule: B1
    promoted_at: "2026-05-24"
    precision: 0.92
    recall: 0.85
    positive_count: 25
    low_confidence_approved: false  # optional; defaults to false
```

Required fields per entry: `rule`, `promoted_at`, `precision`, `recall`,
`positive_count`. `low_confidence_approved` is optional and defaults to
`false`.

Promotion bar (decision-gated; immutable in `promotion.py`):

| Threshold | Constant | Minimum |
| --- | --- | --- |
| Precision | `MIN_PRECISION` | 0.90 |
| Recall | `MIN_RECALL` | 0.80 |
| Positive label count | `MIN_POSITIVE_COUNT` | 20 |

At load time each entry is re-validated against the current labeled
corpus (when `--validate-against` is also passed). Rules failing
re-validation emit a `promotion_below_bar` advisory (MEDIUM confidence)
and are omitted from the active promotion set.

Group A rule names in a promotion entry are rejected with a
`Cannot promote Group A rule` advisory (HIGH confidence).

Strict-mode behavior: when `--strict` is set, the CLI exits 1 on any
`ESCAPE_REQUIRED` finding whose `rule` is in the active promotion set
(after re-validation).

## Confusion-table corpus

Schema enforced by `validation/scene_lint/confusion.py`. The corpus drives
both promotion re-validation (above) and the standalone
`--validate-against` / `--emit-confusion` reporting path.

Top-level key is `labels` (canonical) or `entries` (accepted alias for
auto-seeded files). Each entry carries one of two shapes:

Positive label (rule SHOULD fire here):

```yaml
- label_type: positive
  scene: bench_basic
  placement_name: rear_left_waste
  precheck_kind: aspect_distorted
  mapped_rule: B1
  reviewer: alice@example.com
  reviewed_at: 2026-05-24
```

Negative label (rule SHOULD NOT fire here):

```yaml
- label_type: negative
  scene: hood_basic
  placement_name: micropipette
  candidate_rule: B1
  reviewer: alice@example.com
  reviewed_at: 2026-05-24
  rationale: Aspect within tolerance; visually verified.
```

Required fields per label type:

| Label type | Required fields |
| --- | --- |
| positive | `label_type`, `scene`, `placement_name`, `precheck_kind`, `mapped_rule`, `reviewer`, `reviewed_at` |
| negative | `label_type`, `scene`, `placement_name`, `candidate_rule`, `reviewer`, `reviewed_at`, `rationale` |

Missing any required field raises `ValueError`; the loader does not
silently skip malformed entries.

Confusion math (`compute_confusion`):

| Cell | Definition |
| --- | --- |
| TP | Positive label for the rule; finding fired with matching `(scene, placement_name)`. |
| FN | Positive label for the rule; finding did not fire. |
| FP | Negative label for the rule; finding fired (rule false-alarmed). |
| TN | Negative label for the rule; finding did not fire. |
| Precision | `TP / (TP + FP)`; None when `TP + FP == 0`. |
| Recall | `TP / (TP + FN)`; None when `TP + FN == 0`. |

Per-rule reports are written by `write_confusion_markdown` to
`<emit_stem>_<rule>.md` files (one per rule observed in either findings
or positive labels).

## Pipeline integration

Scene lint runs as a stage in `validation/validate.py` alongside the
other validation tools. The integration order is documented in
[../USAGE.md](../USAGE.md).

Group A rules run first across all loaded scenes; the duplicate-scene
check runs once across the entire set, then per-scene Group A rules
run, then `dump_scene_geometry` is called once per scene and reused
across all Group B rules.

## Dependencies

| Module | Purpose |
| --- | --- |
| `validation/scene_calc/dump.py` | Thin loader: reads `generated/scene_render_stats/<scene>.stats.json` (produced by the browser render) and returns the rendered geometry as the canonical input to Group B rules. Computes no layout. |
| `tools/scene_to_png.mjs` + `tools/scene_stats.mjs` | The single geometry producer: render each scene through the real TS layout engine and emit rendered bboxes, `aspect_delta_pct`, `scale_source`, and zone `inner_rect` into stats.json. |
| `validation/shared_toolkit/scene_loaders.py` | `load_svg_viewbox`, `resolve_inheritance`, typed inheritance exceptions consumed by Group A rules. |
| `validation/shared_toolkit/yaml_io.py` | YAML loader with error wrapping. |
| `validation/shared_toolkit/cli.py` | Shared argparse base (`-S/--scene`, `--strict`, `-O/--only`). |
| `validation/yaml_schema/scene_base_validator.py` | Coordinated coverage for `invalid_*` rules; see coverage matrix. |

## References

- [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) - geometry primitives and units consumed by Group B.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) - canonical scene terms.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) - authored YAML schema validated by Group A.
- [SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md) - vocabulary closure rules (notably rule 25 on `_name` vs `_id`).
- [SCENE_DESIGN.md](SCENE_DESIGN.md) - sibling composition scorecard tool.
- `validation/scene_lint/coverage_matrix.md` - per-rule coverage delegation between vocab lint and scene lint.
- `design_advice/SCENE_LINT_PLAN.md` - original v3 design proposal (pre-implementation; carries some stale invocation examples).
