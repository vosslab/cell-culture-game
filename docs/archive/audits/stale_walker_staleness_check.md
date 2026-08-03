# Stale walker staleness check

Status: DONE. `tests/playwright/walker/` is provably dead. No files were modified
or deleted by this check. A human must run the `git rm` listed at the bottom.

## What this checks

`tests/playwright/walker/` is a second-generation walker built against an extinct
runtime contract (`data-testid` selectors, a `__RUNTIME_PROTOCOL_CONFIG` global).
The live walker is `tests/playwright/e2e/protocol_walkthrough_yaml.mjs` plus
`walker_helpers.mjs`. This check confirms nothing outside the folder still
references the old tree before the human deletes it (M14b docs reconciliation
depends on this being confirmed dead).

## Evidence

### 1. No live reference to `playwright/walker` outside the folder itself

```bash
grep -rn "playwright/walker" --include=*.mjs --include=*.sh --include=*.json --include=*.ts .
```

Output (21 hits, all self-references):

- `tests/playwright/walker/run.mjs` (4 hits) - its own usage-comment docstring,
  e.g. `node tests/playwright/walker/run.mjs --protocol mtt_solubilization_readout`.
- `tests/playwright/walker/audit_all.mjs` (2 hits) - its own header-comment
  docstring, e.g. `node tests/playwright/walker/audit_all.mjs`.
- `.claude/worktrees/agent-*/tests/playwright/walker/run.mjs` and
  `.../audit_all.mjs` (15 hits across three agent worktrees) - these are git
  worktree checkouts of this same repo (untracked, agent-scoped scratch
  directories), not a second call site. They carry the same self-referencing
  docstring text, not an external import.

No hit comes from `package.json`, a `.github/*` workflow, `check_codebase.sh`,
`run_playwright_tests.sh`, or any file outside `tests/playwright/walker/` (and
its worktree copies).

Supporting checks:

```bash
git ls-files ".github/*"
# (no output - no tracked workflow files exist yet)

grep -n "walker" package.json
# (no output)

grep -n "walker" check_codebase.sh
# (no output)

grep -n "walker" run_playwright_tests.sh
# (no output)
```

### 2. No live runtime emits the extinct contract

```bash
grep -rn "__RUNTIME_\|data-testid" src/
```

Output: empty. Nothing under `src/` emits `__RUNTIME_PROTOCOL_CONFIG` or any
`data-testid` attribute. The current runtime uses `data-*` selectors documented
in `src/scene_runtime/protocol/gesture_registry.ts` (per-gesture stable
selectors), not `data-testid`.

### 3. No relative import of a walker submodule from outside the folder

```bash
grep -rln "walker/engine\|walker/index\|walker/click_resolver\|walker/screenshot" \
  --include=*.mjs --include=*.ts --include=*.js .
```

Output: empty after excluding the folder itself and its worktree copies (no
external caller imports `engine.mjs`, `index.js`, `click_resolver.js`, or
`screenshot.js`).

## File list for the human `git rm`

`git ls-files tests/playwright/walker/` and a plain `find` agree on the same
7 tracked files, none of which appear anywhere else in the repo:

```
tests/playwright/walker/audit_all.mjs
tests/playwright/walker/click_resolver.js
tests/playwright/walker/engine.mjs
tests/playwright/walker/index.js
tests/playwright/walker/run.mjs
tests/playwright/walker/screenshot.js
tests/playwright/walker/tsconfig.json
```

## Instruction

Human runs:

```bash
git rm tests/playwright/walker/audit_all.mjs \
  tests/playwright/walker/click_resolver.js \
  tests/playwright/walker/engine.mjs \
  tests/playwright/walker/index.js \
  tests/playwright/walker/run.mjs \
  tests/playwright/walker/screenshot.js \
  tests/playwright/walker/tsconfig.json
```

`git rm` preserves history per `docs/REPO_STYLE.md`; a plain `rm` is not used.
The empty `tests/playwright/walker/` directory disappears automatically once
its tracked contents are removed (git does not track empty directories).

## Status

DONE - the tree is provably dead. M14b (docs reconciliation) may proceed once
the human completes the `git rm` above.
