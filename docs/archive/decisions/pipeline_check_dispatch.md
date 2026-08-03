# Decision: pipeline_check.py removed from svg stage dispatch

## Summary

`validation/svg/pipeline_check.py` was listed in the `svg` stage_map in
`validation/validate.py:80` but the file did not exist. At runtime this
caused `validate.py:112-114` to print "Stage script not found" for every
`--only svg` run. The file was removed from active dispatch (WP1.2).

## Decision

Remove `pipeline_check.py` from the active stage_map. The file is absent
and not referenced as planned future work in any active doc, ROADMAP.md,
TODO.md, check_codebase.sh, CI config, or source tree. References in
changelog archives (`docs/CHANGELOG-2026-05b.md`, `docs/CHANGELOG-2026-05d.md`)
and `docs/archive/` describe it as completed and then superseded work, not
planned work. The SVG determinism + coverage gate it once performed is now
run directly by `check_codebase.sh` (confirmed: `check_codebase.sh` has no
`pipeline_check` reference, so that wiring was also removed at some point).

Outcome: `validation/validate.py --only svg -q` now runs only `asset_audit.py`
and prints one canonical summary line. No "Stage script not found" output.

## Search commands and hits

```
grep -rn "pipeline_check" validation/ tests/ pipeline/ tools/
```
Hits: `validation/validate.py:80` (the stage_map entry, now removed).

```
grep -rn "pipeline_check" docs/
```
Hits: `docs/USAGE.md:208`, `docs/VALIDATION_JSON_SCHEMA.md:14,106`,
`docs/CHANGELOG-2026-05b.md` (multiple lines describing past completion),
`docs/CHANGELOG-2026-05d.md` (exit-code migration, past tense),
`docs/archive/tools_split_and_consolidate.md` (archived plan artifact),
`docs/archive/web_ui/cleanup_handoff.md` (archived artifact).
None describe pipeline_check.py as planned future work.

```
grep -n "pipeline_check" check_codebase.sh
```
No hits.

```
ls .github/
```
No .github directory exists in the repo.

```
grep -n "pipeline_check" docs/ROADMAP.md docs/TODO.md
```
No hits (or files not present).

## Files edited

- `validation/validate.py`: removed `validation/svg/pipeline_check.py` from
  the svg stage_map list and updated the `_stage_scripts` docstring to
  document why.

## Verification

Command:
```
source source_me.sh && python3 ./validation/validate.py --only svg -q
```
Output:
```
SVG: Checked 76 objects. 86 failures. 0 warnings.
```
No "Stage script not found" line. Exit confirms the stage runs cleanly.
