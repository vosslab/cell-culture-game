# Scene stage consumer discovery (WP3.0)

Scope: every invocation of `scene_lint` / `scene_design` in the repo.
Purpose: determine which call sites parse stdout and what format each needs, so
WP3.1/WP3.2 can safely convert default output to human text while preserving
the current JSONL bytes behind `--json`/`--ndjson`.

Discovery date: 2026-05-30.

---

## Search commands and hits

```bash
grep -rn "scene_lint|scene-lint|scene_design|scene-design" . \
  --include="*.py" --include="*.sh" --include="*.mjs" --include="*.ts" \
  --include="*.js" --include="*.json" --include="*.md" -l
```

Non-doc, non-internal hits that represent call sites or stdout consumers:

- `validation/validate.py` (lines 87-88, 175-192, 233, 274-318)
- `tests/e2e/e2e_scene_design_cli.py` (line 25)
- `tests/test_validation_verbosity.py` (line 37 -- stage name list only)
- `tools/scene_stats.mjs` (line 283 -- comment only, not an invocation)

No hits in:
- `pipeline/` (no invocations)
- `.github/` (no CI configs present)
- `package.json` scripts
- shell scripts (`*.sh`)

---

## Action table

| call_site | how_invoked | consumes_stdout? | action |
| --- | --- | --- | --- |
| `validation/validate.py:87-88` (stage dispatch map) | subprocess via `_run_one_script`; passes `-q`/`-v` and `--json`/`--ndjson` from parent args | YES -- text mode: last non-empty line displayed; json/ndjson mode: calls `json.loads(stdout)` at line 282, which CRASHES on multi-line JSONL | `update to pass --json` |
| `validation/validate.py:274-318` (json merge path) | consumes the subprocess stdout from the stage dispatch above | YES -- `json.loads(stdout)` (single-doc parse); currently fails with JSONDecodeError when scene stages emit JSONL | `update to pass --json` |
| `tests/e2e/e2e_scene_design_cli.py:25` | `python3 -m validation.scene_design.cli -S <scene>` directly (no `--json` flag) | YES -- line 33: `json.loads(result.stdout.strip().split('\n')[0])`; parses first line as JSON object | `human-only, text is fine` -- see note |
| `tests/test_validation_verbosity.py:37` | stage name string in a list literal only; invokes via `validate.py --only <stage>` in `run_stage_subprocess` helper | No -- the helper captures stdout/stderr for line-count assertions; does not parse as JSON | `human-only, text is fine` |
| `tools/scene_stats.mjs:283` | comment reference only; not an invocation | No | not a call site |

### Notes on action table rows

**`validate.py` (two rows, same call site):**
The `_run_one_script` function at lines 188-192 already passes `--json` or
`--ndjson` to stage CLIs when `args.output_format` is set. However, both
`scene_lint/cli.py` and `scene_design/cli.py` currently IGNORE `args.output_format`
and always emit JSONL regardless of flag. The net effect is:
- `validate.py --json` crashes with JSONDecodeError at line 282 when any scene
  stage runs, because `json.loads` cannot parse multi-line JSONL.
- `validate.py` text mode (no `--json`): works today because it just displays the
  last non-empty stdout line; the JSONL is displayed raw.

WP3.1/WP3.2 must ensure that when `--json` or `--ndjson` is passed, the stage
emits a single JSON document (or proper ndjson), so validate.py's merge path
can call `json.loads` successfully. The action label is `update to pass --json`.

**`tests/e2e/e2e_scene_design_cli.py:25`:**
This test calls scene_design directly (no flag) and parses `stdout.split('\n')[0]`
as a JSON object. It expects JSONL format on the default (no-flag) path.
However, M3 will change the default output to human text; this call site will
break after WP3.2 unless it is updated. The test must either add `--json` to
its invocation or be rewritten to parse human text.
Recommended action: WP3.2 updates this call site to add `--json` so it keeps
parsing structured output. Label: `update to pass --json`.

**Revised action for e2e test:**

| call_site | how_invoked | consumes_stdout? | action |
| --- | --- | --- | --- |
| `tests/e2e/e2e_scene_design_cli.py:25` | `python3 -m validation.scene_design.cli -S <scene>` (no `--json`) | YES -- parses first stdout line as JSON | `update to pass --json` |

---

## Per-flag machine-format shapes

### scene_lint/cli.py

Current behavior: ignores `args.output_format` entirely. The final output
path (line 287) always calls `write_findings_jsonl(findings, sys.stdout)`.

| flag | shape | description |
| --- | --- | --- |
| (no flag) | JSONL | One JSON object per line. Each line is a single finding dict with keys: `scene`, `placement_name`, `rule`, `verdict`, `predicts`, `bbox_type`, `confidence`, `message`, `evidence`, `fix_hints`, `suppressed_by`. No wrapping array or envelope. |
| `--json` | JSONL (identical to no flag) | `--json` is accepted by the shared argparse (`args.output_format = 'json'`) but scene_lint never reads `args.output_format`. Output is byte-identical to the no-flag run. |
| `--ndjson` | JSONL (identical to no flag) | Same situation. `args.output_format = 'ndjson'` is silently ignored. |

**Determinism:** byte-identical across two runs on the same input (verified by md5
on `bench_basic.yaml`). JSONL ordering is stable (scene order follows sorted path
list; finding order within a scene follows rule execution order).

**Implication for WP3.1:** After migration, `--json` and `--ndjson` must each emit
something parseable by `json.loads` (single JSON document) or by the ndjson path
in validate.py. Recommend: `--json` emits `{"findings": [...]}` (array wrapped in
object), `--ndjson` keeps one-JSON-object-per-line. Both are semantically
equivalent to the current per-line objects.

### scene_design/cli.py

Current behavior: checks `args.markdown_output` but not `args.output_format`.
Default path (no `--markdown` flag) always calls `write_cards_jsonl(cards)`.

| flag | shape | description |
| --- | --- | --- |
| (no flag) | JSONL | One JSON object per line. Each line is a scene card dict with keys: `scene`, `class`, `score`, `confidence`, `gated_by_render_predictor`, `metrics` (dict of 15 named float fields), `suggestions` (list). No wrapping array or envelope. |
| `--json` | JSONL (identical to no flag) | `args.output_format` is never read; `--json` flag is silently ignored. Byte-identical to no-flag output. |
| `--ndjson` | JSONL (identical to no flag) | Same. `--ndjson` silently ignored. |
| `--markdown` / `-m` | Markdown sections | Emits one Markdown section per scene (`## <scene_name>`, card text). Uses `write_cards_markdown`. Not affected by verbosity. |

**Determinism:** byte-identical across two runs on the same input (verified by md5
on `bench_basic.yaml`). Card ordering follows the order scenes are processed
(sorted yaml path list).

**Implication for WP3.2:** After migration, `--json` and `--ndjson` must emit
parseable structured output. `--markdown` is already an explicit format flag
(orthogonal to verbosity per the contract spec). Recommend: `--json` emits
`{"cards": [...]}`, `--ndjson` keeps one-card-per-line.

---

## Determinism verdict

Both stages are byte-deterministic on identical inputs:
- `scene_lint`: byte-identical md5 across two runs on `bench_basic.yaml`.
- `scene_design`: byte-identical md5 across two runs on `bench_basic.yaml`.

WP3.1 and WP3.2 MAY assert byte-identity for `--json`/`--ndjson` output against
baseline, as long as input fixtures are fixed. No semantic-equivalence-only
fallback is needed.

---

## Current bugs discovered during discovery

1. `validate.py --json` crashes with JSONDecodeError when scene-lint or
   scene-design runs (line 282 calls `json.loads` on JSONL with multiple lines).
   WP3.1/WP3.2 fix this by making `--json` emit a single parseable JSON document.

2. `scene_lint/cli.py` and `scene_design/cli.py` silently accept `--json` and
   `--ndjson` from the shared argparse but produce identical JSONL output for all
   three modes. The flags have no effect today.

---

## Call sites that WP3.1/WP3.2 must update to pass --json

The following call sites parse stdout as JSON and will break when the default
output changes to human text:

| call_site | who fixes | what to do |
| --- | --- | --- |
| `validation/validate.py:282` -- `json.loads(stdout)` in json/ndjson merge path | WP3.1 + WP3.2 (each stage must make `--json` return a parseable single doc) | When `--json` is passed, emit `{"findings": [...]}` (scene_lint) or `{"cards": [...]}` (scene_design); validate.py then gets parseable JSON. |
| `tests/e2e/e2e_scene_design_cli.py:25+33` -- direct CLI call with no flag, parses first stdout line | WP3.2 | Add `--json` to the subprocess call; update the json parse to handle the wrapped `{"cards": [...]}` envelope. |

No other stdout consumer exists in Python, shell, JS/TS, pipeline, or CI configs.

---

## Resolved ambiguous rows

No rows were left ambiguous. All rows have been resolved above.

Summary of actions:
- `update to pass --json`: validate.py dispatch path, e2e test for scene_design.
- `human-only, text is fine`: test_validation_verbosity.py (line-count assertions only).
- Not a call site: tools/scene_stats.mjs (comment only).
