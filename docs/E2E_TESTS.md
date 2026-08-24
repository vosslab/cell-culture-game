# E2E_TESTS.md

End-to-end (E2E) testing conventions for this repo.

## Two E2E homes

This repo supports two distinct E2E execution models, each with its own folder:

- `tests/playwright/` (and optional `tests/playwright/e2e/` sub-grouping) - **browser-based E2E**: full Playwright walkthroughs and browser-driven tests. TypeScript repos include `PLAYWRIGHT_USAGE.md` in their propagated `docs/` folder.
- `tests/e2e/` - **non-browser E2E**: shell/Python orchestration for whole-system testing: CLIs, builds, services, multi-suite coordination. This doc focuses on the non-browser model.

Both are excluded from `pytest tests/` via `collect_ignore = ["e2e", "playwright"]` in `tests/conftest.py`.

## Test layout overview

This repo organizes tests in four tiers, all under the `tests/` umbrella:

- `tests/test_*.py` - fast pytest unit and integration tests. Run with `pytest tests/`.
- `tests/test_*.mjs` - pure Node tests, if any (rare; not browser-driven).
- `tests/playwright/` (with optional `tests/playwright/e2e/` subfolder) - browser-driven Playwright tests. TypeScript repos include `PLAYWRIGHT_USAGE.md` in their propagated `docs/` folder.
- `tests/e2e/` - non-browser whole-system E2E. Shell/Python orchestration (`e2e_*.sh`, `e2e_*.py`). Run directly, not via pytest.

## Why tests/e2e/ is excluded from pytest

Pytest is the fast lane. Tests under `tests/` should run in seconds so the
suite stays useful during development. End-to-end tests are by nature slow:
they invoke real scripts, read and write real files, and may hit the network
or external tools. Mixing them into `pytest tests/` makes the fast lane slow
and discourages running it.

Pytest's `collect_ignore = ["e2e", "playwright"]` in `tests/conftest.py` actively excludes
both the `tests/e2e/` and `tests/playwright/` subtrees from pytest collection, regardless of filenames
inside them. This is the primary safety mechanism. Additionally, `.mjs` and `.sh`
files are invisible to pytest by extension, and Python orchestration scripts use
the `e2e_*` prefix as a secondary, human-readable convention.

## Where non-browser E2E tests live

- Folder: `tests/e2e/` under `tests/` at the repo root.
- Pytest is configured to ignore the subtree via `collect_ignore = ["e2e", "playwright"]` in
  `tests/conftest.py`, so file naming inside `tests/e2e/` cannot accidentally pull slow tests into the fast lane.
- Recommended naming for readability:
  - `e2e_*.sh` for shell runners.
  - `e2e_*.py` for Python orchestration.
- Each E2E script is self-contained and exits non-zero on failure.

`tests/` (excluding `tests/e2e/` and `tests/playwright/`) stays reserved for fast pytest tests (see
[PYTEST_STYLE.md](PYTEST_STYLE.md)).

## How to run non-browser E2E tests

- Run a single shell runner: `bash tests/e2e/e2e_<name>.sh`.
- Run a single Python runner: `source source_me.sh && python3 tests/e2e/e2e_<name>.py`.
- Run the repository's exhaustive build-and-test gate: `./super_all_tests.sh`.
  It covers every `tests/e2e/e2e_*` file plus Playwright, pytest, validation,
  generated render evidence, and the build.
- For browser-driven Playwright runs, TypeScript repos include `PLAYWRIGHT_USAGE.md` in their propagated `docs/` folder.
- Do not invoke E2E tests from `pytest tests/`. Keep the two suites separate.

`super_all_tests.sh` is intentionally single-writer within one checkout because
its build outputs, generated reports, browser evidence, and `SUPER_LOG.txt` are
shared. A concurrent invocation exits before changing those files and reports
the saved owner PID when available. PID liveness alone does not prove that the
process is still the suite because operating systems recycle PIDs. If an
ungraceful termination leaves `.super_all_tests.lock`, verify the process
identity and confirm that no exhaustive suite is active before removing the
stale lock directory. The lock artifact is ignored by Git.

The exhaustive runner gives every non-browser E2E a default five-minute
process-group boundary through `tools/run_with_timeout.py`, then executes
connected Playwright acceptance before shell E2Es. This preserves rendered
statistics for their Python/Node consumers and prevents an external-tool
regression from hiding the user workflow result. Set `E2E_TIMEOUT_SECONDS` when a
deliberately longer E2E is required. A timeout or other nonzero exit is reported
as a normal failed gate and the summary still completes.

## Naming conventions test

File naming conventions are enforced by `templates/typescript/tests/test_test_naming_conventions.py`
(ships only to `REPO_TYPE=typescript` consumer repos) to prevent silent bugs:

- No `test_*.py` files anywhere under `tests/e2e/` (since `collect_ignore` would skip them silently, mismatching the name).
- No `test_*.py` files anywhere under `tests/playwright/` (same trap).
- All Python files under `tests/e2e/` must use the `e2e_*.py` prefix.
- All shell files under `tests/e2e/` must use the `e2e_*.sh` prefix.
- Any file with a Playwright import must live under `tests/playwright/`.

## What E2E tests should cover

- Whole-script behavior: run the CLI end to end with realistic arguments and
  check the produced files or exit code.
- I/O round trips: encode a file with one script, decode with another,
  compare to the original.
- Integration with external tools where mocking would defeat the point.
- Anything that needs user input or read/write to files (the `assert` rules
  forbid asserts in plain scripts entirely; cover that behavior here instead;
  see [PYTHON_STYLE.md](PYTHON_STYLE.md#assert)).

## What E2E tests should not cover

- Pure function correctness. That belongs in pytest under `tests/`.
- Anything fast enough to live in pytest. If a check finishes in under a
  second and does not touch the real filesystem in a meaningful way, it is a
  unit test, not an E2E test.

## Asserts and failures

- E2E test scripts may use `assert` (they are test files, not plain scripts).
- Prefer explicit exit codes and clear stderr messages so a failing E2E run
  is easy to diagnose without reading the script.

## Related docs

- [PYTEST_STYLE.md](PYTEST_STYLE.md): fast pytest unit and integration tests under `tests/`.
- Browser-driven test conventions: the website family (`website` and its inheriting `typescript`) includes `PLAYWRIGHT_USAGE.md` in their propagated `docs/` folder for tests under `tests/playwright/`.
- Browser test authoring style: the website family (`website` and its inheriting `typescript`) includes `PLAYWRIGHT_TEST_STYLE.md`, shipped via the `templates/website/` overlay, in their propagated `docs/` folder for how to write Playwright tests under `tests/playwright/`.
- [PYTHON_STYLE.md](PYTHON_STYLE.md): repo-wide Python rules, including
  the `assert`-only-in-tests boundary.
