## Scene-lint non-determinism audit

Status: NEW / read-only investigation. Not yet routed to a fix owner's active
plan; this file records the reproduction and pinned root cause so the finding
is not lost.

### Reproduction (observed)

- Batch A: direct `python3 validation/scene_lint/cli.py -q -S content/base_scenes/*.yaml`
  run 5 times in a row -> "Checked 9 scenes. 0 errors. 55 warnings." every time.
- Batch B: aggregate `python3 validation/validate.py -q` (SCENE-LINT stage) run
  5 times in a row -> "9 errors. 0 warnings." every time.
- Batch C: direct invocation again immediately after Batch B -> "9 errors."
- A live `ls generated/scene_render_stats/` returned "No such file or
  directory" mid-run (the evidence directory vanished because an external
  build was in flight at that moment).
- This confirms the reported 0/7/9 error-count flip is real and reproducible,
  not an artifact of a single bad run.

```text
Batch A (direct, x5):   0 errors, 55 warnings  (each run)
Batch B (aggregate, x5): 9 errors, 0 warnings  (each run)
Batch C (direct, after B): 9 errors
ls generated/scene_render_stats/  -> No such file or directory (mid-run)
```

### Pinned root cause: cross-process filesystem race, no coordination primitive

- `pipeline/build_generated.sh:23` runs `rm -rf generated` (then recreates the
  directory), unconditionally wiping the entire `generated/` tree, including
  `generated/scene_render_stats/`, every time `build_github_pages.sh` runs.
  `build_github_pages.sh:57` calls `bash pipeline/build_generated.sh` first in
  the build sequence.
- `tools/scene_to_png.mjs:514-517` is the ONLY producer of
  `generated/scene_render_stats/*.stats.json`, and it runs near the end of
  `build_github_pages.sh` (`build_github_pages.sh:161-165`), rendering one
  scene at a time in a per-scene render loop (`node tools/scene_to_png.mjs
  --all`).
- `validation/scene_calc/dump.py:140-146` raises `MissingRenderEvidenceError`
  when a scene's `stats.json` is absent. `validation/scene_lint/cli.py:191-212`
  catches that error and emits a `missing_render_evidence` BLOCKED finding per
  scene, and each BLOCKED finding is counted as one error. Between the
  directory wipe and the last `stats.json` write, the directory is absent or
  only partially populated, so a concurrent `validate` run observes anywhere
  from 0 to N BLOCKED findings purely from timing (N=9 for the base scenes).
- `run_validate.sh`'s own header states that validation "reads EXISTING
  generated evidence... never renders... If the stats are missing, validation
  fails clearly" -- that contract is violated by this race, not by any
  scene-lint rule logic. The rule implementations (`rules_group_a`,
  `rules_group_b`, `findings.py`) have no ordering-dependent logic; they only
  consume whatever `dump_scene_geometry` returns.
- Session note: the trigger condition is running `validate` concurrently with
  `build_github_pages.sh` / `pipeline/build_generated.sh` in the same
  checkout, for example when multiple agents each rebuild the same working
  tree in parallel. Serializing build-then-validate is the immediate
  workaround; it is not a fix for the underlying race.

### Classification

Render-evidence architecture race between the build pipeline and the
validation pipeline. This is NOT a trivial determinism bug (not unsorted
iteration order, not dict ordering); it is a filesystem-level race between two
processes that share `generated/` with no lock or handoff signal.

### Owner and clearing action

Route jointly to:

- the validation owner (`validation/scene_calc/dump.py`,
  `validation/scene_lint/cli.py`)
- the pipeline owner (`pipeline/build_generated.sh`, `build_github_pages.sh`,
  `tools/scene_to_png.mjs`)

Durable fix candidates (listed for the owners to choose from; none applied by
this audit):

1. Stop the unrelated `rm -rf generated` from sweeping up
   `scene_render_stats`: move that evidence outside `generated/`, or
   explicitly preserve the subdirectory across the wipe.
2. Have `scene_to_png.mjs` render into a temporary directory and atomically
   rename it into place only after the full `--all` batch completes, so
   readers never see a partial directory.
3. Add a `generated/.building` lock marker that `validate.py` checks; when
   present, report "build in progress, retry" instead of emitting spurious
   `missing_render_evidence` BLOCKED findings.

### Cross-links

- [walker_click_bug_register.md](walker_click_bug_register.md) tracks a
  separate class of walker/click defects; this file is a distinct
  render-evidence race and is not a duplicate of that register.
- This audit file is new/untracked as of this writing, so
  `tests/test_markdown_links.py` (which only resolves git-tracked files)
  cannot see inbound links to it yet. Links FROM this file point only to
  already-tracked files.
