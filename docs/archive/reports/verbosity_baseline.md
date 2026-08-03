# Verbosity baseline report

WP1.3 artifact. Captured 2026-05-30 against the post-WP1.1/WP1.2, pre-stage-migration
state of the repo. M2/M3 stage migrations compare their results against this snapshot.

## Fixture decision

**Decision: full repo content tree, no selector scope.**

Rationale:

- `tests/content/dev_smoke/` contains protocol YAML only; it cannot satisfy the svg stage
  (which scans `assets/equipment/*.svg`), the scene-lint/scene-design stages (which require
  `content/base_scenes/*.yaml`), or the structure stage (which walks folder layout).
- The yaml stage's `-p` selector silently exits with code 1 and produces no output when a
  protocol filter is passed (pre-migration bug, not WP1.3 scope); scoped runs via `-p` are
  therefore unreliable as a determinism strategy until the stages are migrated.
- The full tree is the canonical reference for all seven stages and exercises each stage's
  real scanning logic. The plan's risk mitigation is to assert upper bounds and exactly-one-line
  quiet only, so legitimate content additions do not break tests.
- M2/M3 per-stage tests will use the same full-tree invocation and update this table's rows
  as each stage is migrated.

Scene stages (`scene-lint`, `scene-design`) are invoked against all nine `content/base_scenes/*.yaml`
files (the same auto-discovery that `validate.py` applies when no `-S` selector is given).

## Call mode per stage

Each stage is invoked via **subprocess** in the test helper, matching how `validate.py` runs
them. This is the faithful path: it exercises the same environment, PYTHONPATH setup, and
flag-forwarding that the production orchestrator uses.

`direct import + main()` was rejected because:

- The scene stages in particular use argparse with `sys.argv`; direct import would require
  mocking `sys.argv` and capturing `sys.stdout`, which is fragile.
- subprocess matches the production dispatch; any divergence is a test artifact, not evidence.

### Per-stage command reference

| Stage | Direct invocation | Notes |
| --- | --- | --- |
| yaml | `python3 validation/yaml_schema/content_lint.py [-q\|-v]` | No selector; scans all `content/`. |
| svg | `python3 validation/svg/asset_audit.py [-q\|-v]` | Scans all `assets/equipment/*.svg`. |
| stepper | `python3 validation/stepper/step_check.py [-q\|-v]` | Scans all protocols in `content/`. |
| structure | `python3 validation/structure/layout_check.py [-q\|-v]` | Walks folder layout under `content/`. |
| manual | `python3 validation/manual/protocol_manual.py --validate --all [-q\|-v]` | `--validate --all` flags added by validate.py; direct run needs them explicitly. |
| scene-lint | `python3 validation/scene_lint/cli.py -S content/base_scenes/*.yaml [-q\|-v]` | `-S` glob expanded by validate.py; direct run needs explicit paths. |
| scene-design | `python3 validation/scene_design/cli.py -S content/base_scenes/*.yaml [-q\|-v]` | Same as scene-lint. |

### Via validate.py (the test helper path)

```
python3 ./validation/validate.py --only <stage> [-q|-v]
```

`validate.py` handles the `--validate --all` injection for manual and the `-S` auto-discovery
for scene stages; the test helper passes through verbosity flags identically.

## Exit code mapping

| Exit code | Meaning |
| --- | --- |
| 0 | Stage passed (no errors above threshold) |
| 1 | Stage failed (one or more errors found, or stage script not found) |

There are no other exit codes used by these stages. The `stepper` stage exits 1 because it
finds failing protocols. The `yaml` stage exits 1 because it finds 191 schema errors.

## Baseline table

Captured by running `python3 ./validation/validate.py --only <stage> [-q|-v]` with no content
selectors. `stdout_lines` is `len(stdout.splitlines())`. `stderr_lines` is `len(stderr.splitlines())`.
All stderr values are 0 for every stage at every level.

| Stage | Level | stdout_lines | stderr_lines | exit |
| --- | --- | --- | --- | --- |
| yaml | quiet | 2 | 0 | 1 |
| yaml | default | 658 | 0 | 1 |
| yaml | verbose | 675 | 0 | 1 |
| svg | quiet | 1 | 0 | 0 | M2 WP2.2 |
| svg | default | 24 | 0 | 0 | M2 WP2.2 |
| svg | verbose | 69 | 0 | 0 | M2 WP2.2 |
| stepper | quiet | 1 | 0 | 1 |
| stepper | default | 160 | 0 | 1 |
| stepper | verbose | 185 | 0 | 1 |
| structure | quiet | 1 | 0 | 0 |
| structure | default | 3 | 0 | 0 |
| structure | verbose | 3 | 0 | 0 |
| manual | quiet | 1 | 0 | 0 |
| manual | default | 198 | 0 | 0 |
| manual | verbose | 198 | 0 | 0 |
| scene-lint | quiet | 10 | 0 | 0 |
| scene-lint | default | 618 | 0 | 0 |
| scene-lint | verbose | 618 | 0 | 0 |
| scene-design | quiet | 10 | 0 | 0 |
| scene-design | default | 83 | 0 | 0 |
| scene-design | verbose | 83 | 0 | 0 |

## Observations and known drift

The following observations document pre-migration behavior that the M2/M3 work packages
are expected to fix. They are baseline facts, not bugs WP1.3 resolves.

- **yaml quiet = 2 lines, not 1.** The summary string contains a hard newline embedded in the
  middle: `"YAML: Validated 167 files (76 objects, 9 base scenes, 25 protocol scenes, 26 \nmaterials, 31 protocols). 191 failures."` This is a pre-migration line-wrapping artifact in
  the yaml stage. WP2.1 resolves it by adopting the canonical `summary_line`.
- **yaml quiet uses "Validated", not "Checked".** The canonical grammar is
  `Checked <N> <label>. <F> failures. <W> warnings.` WP2.1 migrates this.
- **yaml default = 658 lines, verbose = 675.** Far above the 40-line default budget. The yaml
  stage is not yet migrated to level-gated output. WP2.1 resolves this.
- **structure verbose = default = 3 lines.** The stage has no verbose branch. WP2.4 adds it.
- **manual verbose = default = 198 lines.** The stage has no verbose branch. WP2.5 adds it.
  Also 198 lines exceeds the 40-line default budget; WP2.5 resolves both.
- **scene-lint quiet = 10 lines, default = 618, verbose = 618.** The stage ignores `-q`/`-v`
  entirely and emits JSONL to stdout. The 10 lines at quiet is one header line plus 9 JSONL
  findings for one scene. WP3.1 adds human text gated by level.
- **scene-design quiet = 10 lines, default = 83, verbose = 83.** Same issue as scene-lint.
  WP3.2 adds human text gated by level.
- **svg sanctioned delta.** WP1.2 removed `pipeline_check.py` from the svg stage dispatch.
  The svg stage baseline (exit 0, quiet 1 line) reflects the post-WP1.2 state; it no longer
  emits "Stage script not found". This is the one sanctioned exit-code delta documented in
  the plan.

## Update protocol for M2/M3

When a stage is migrated, the corresponding row(s) in the baseline table above are updated
to reflect post-migration behavior. The update adds an "M2" or "M3" note to the row.
M4 (WP4.1) captures the final whole-suite evidence table in a separate report.
