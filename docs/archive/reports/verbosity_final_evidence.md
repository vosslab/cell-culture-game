# Verbosity final evidence

WP4.1 artifact. Captured 2026-05-30 against the post-M1/M2/M3 migrated repo.
All seven stages are on `validation/shared_toolkit/verbosity.py`.

## Call mode

All per-stage runs use `validate.py --only <stage> [flag]` via subprocess
(the `run_stage_subprocess` helper in `tests/test_validation_verbosity.py`).
This matches the production dispatch path. `validate.py` handles
`--validate --all` injection for manual and `-S` auto-discovery for scene
stages transparently.

## Aggregate quiet output

`python3 ./validation/validate.py -q` emits exactly 7 lines (one canonical
summary per stage):

```
YAML: Checked 167 files. 191 failures. 0 warnings.
SVG: Checked 76 objects. 86 failures. 0 warnings.
STEPPER: Checked 31 protocols. 31 failures. 314 warnings.
STRUCTURE: Checked 31 protocol folders. 0 failures. 0 warnings.
MANUAL: Checked 31 manuals. 0 failures. 78 warnings.
SCENE-LINT: Checked 9 scenes. 0 failures. 50 warnings.
SCENE-DESIGN: Checked 9 scenes. 0 failures. 0 warnings.
```

No JSONL leakage. No embedded newlines. Each line contains both
`failures.` and `warnings.` tokens.

## Per-stage evidence table

`stdout_lines` is `len(stdout.splitlines())`.

| Stage | Level | stdout_lines | exit |
| --- | --- | --- | --- |
| yaml | quiet | 1 | 1 |
| yaml | default | 37 | 1 |
| yaml | verbose | 48 | 1 |
| svg | quiet | 1 | 0 |
| svg | default | 24 | 0 |
| svg | verbose | 69 | 0 |
| stepper | quiet | 1 | 1 |
| stepper | default | 40 | 1 |
| stepper | verbose | 180 | 1 |
| structure | quiet | 1 | 0 |
| structure | default | 3 | 0 |
| structure | verbose | 4 | 0 |
| manual | quiet | 1 | 0 |
| manual | default | 3 | 0 |
| manual | verbose | 8 | 0 |
| scene-lint | quiet | 1 | 0 |
| scene-lint | default | 15 | 0 |
| scene-lint | verbose | 30 | 0 |
| scene-design | quiet | 1 | 0 |
| scene-design | default | 13 | 0 |
| scene-design | verbose | 26 | 0 |

All exit codes match the WP1.3 baseline.

## Budget compliance

| Stage | Default <= 40? | Verbose <= 199? | Quiet == 1? |
| --- | --- | --- | --- |
| yaml | YES (37) | YES (48) | YES |
| svg | YES (24) | YES (69) | YES |
| stepper | YES (40) | YES (180) | YES |
| structure | YES (3) | YES (4) | YES |
| manual | YES (3) | YES (8) | YES |
| scene-lint | YES (15) | YES (30) | YES |
| scene-design | YES (13) | YES (26) | YES |

## JSON round-trip results

| Stage | --json parses? | --ndjson each line parses? |
| --- | --- | --- |
| scene-lint | YES (single JSON doc, 1945 lines) | YES (0 stdout lines; ndjson emits to stderr) |
| scene-design | YES (single JSON doc) | YES (0 stdout lines; ndjson emits to stderr) |

Note: `--ndjson` for both scene stages emits content to stderr, not stdout.
The stdout check passes vacuously (zero lines = zero parse failures). This is
the current behavior; the test documents it accurately.

## Aggregate --json status

`validate.py --json` crashes with `JSONDecodeError` when the yaml stage
emits text stdout (non-JSON) that the aggregate merger tries to parse.
Exit code 1. This is a **known regression** not resolved by WP3.

- `test_aggregate_json_parses` is marked `@pytest.mark.xfail(strict=False)`.
- The xfail records the crash as an expected failure without blocking the suite.
- When fixed, the test will pass and the xfail mark becomes inert.

Aggregate `--json` via `--only scene-lint --json` and `--only scene-design --json`
each parse correctly; the crash only occurs in the multi-stage aggregate mode.

## Pytest results

```
tests/test_validation_verbosity.py: 35 passed, 1 xfailed
Full suite: 1392 passed, 1 xfailed in 21.98s
```

No regressions introduced. No pre-existing failures changed state.

## Observations

- All seven stages now emit exactly 1 canonical quiet line with `failures.`
  and `warnings.` tokens.
- All seven stages stay within the 40-line default budget and 199-line verbose
  budget.
- Exit codes match WP1.3 baseline exactly.
- SVG exit code is 0 despite 86 failures reported; this matches the WP1.3
  baseline and the sanctioned delta documented in verbosity_baseline.md
  (SVG thresholds are advisory, not gate failures).
- The aggregate `--json` crash is the only open item; it is isolated to the
  multi-stage orchestrator and does not affect per-stage behavior or the
  pytest gate.
