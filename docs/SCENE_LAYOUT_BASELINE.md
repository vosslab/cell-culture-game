# Scene layout baseline

This is a committed, hand-refreshed snapshot of the scene corpus taken right after M19
turned on the failBuild layout gate (`pipeline/precompute_layout.mjs` calling
`countBuildFailures` on every non-exempt scene's `severityDiagnostics`, exiting 1 on any
hit). Unlike `test-results/layout_health/` and
`docs/active_plans/reports/layout_diagnostics_baseline.md` (both regenerated on every run
and either gitignored or scratch), this file is a durable reference point: it records what
"clean" looked like the day the gate went live, so later drift is easy to spot.

Refresh this file by hand at each release, or whenever the gate's exempt-scene list or the
corpus composition changes meaningfully. Do not auto-regenerate it as part of the build.

## Refresh command

```bash
./build_github_pages.sh
node --import tsx pipeline/precompute_layout.mjs
npm run scene:png -- --all
source source_me.sh && python3 -m validation.scene_lint.cli
source source_me.sh && python3 -m validation.scene_design.cli --markdown
node --import tsx tests/e2e/e2e_layout_diagnostics_baseline.mjs
```

## Snapshot: 2026-07-04

- `precompute_layout.mjs`: emitted 38 scenes to `generated/precomputed_layout.ts`
  (viewport 1920x1080). Exit code 0.
- `countBuildFailures` on every non-exempt scene: 0. The failBuild gate passes clean.
- `build_github_pages.sh`: exit code 0.
- Historical health scorecard: 38 scenes analyzed by the now-retired proxy report.
  The count is preserved as snapshot evidence only; current refreshes use rendered
  evidence plus `validation.scene_lint` and `validation.scene_design` above.

## Health scorecard (worst-first, top 10 of 38)

| Rank | Scene | Severity | Finding | Categories |
| --- | --- | --- | --- | --- |
| 1 | `adversarial_overflow_smoke` | 174.32 | engine-fit | high-empty-space-plus-shrink, shrink-stressed, crowded, label-stressed |
| 2 | `mtt_solubilization_readout_bench_workspace` | 73.96 | engine-fit | high-empty-space-plus-shrink, shrink-stressed |
| 3 | `centrifuge_workspace` | 73.66 | engine-fit | high-empty-space-plus-shrink, shrink-stressed, crowded, label-stressed |
| 4 | `incubator_workspace` | 72.54 | engine-fit | high-empty-space-plus-shrink, shrink-stressed |
| 5 | `hemocytometer_view` | 40.05 | intentional | crowded, label-stressed |
| 6 | `passage_hood_detachment_hood_workspace` | 32.26 | authoring | shrink-stressed, crowded |
| 7 | `plate_drug_treatment_media_adjustment_plate_workspace` | 29.71 | authoring | shrink-stressed |
| 8 | `extraction_workspace` | 28.89 | authoring | shrink-stressed, label-stressed |
| 9 | `hood_workspace` | 28.58 | authoring | shrink-stressed, crowded |
| 10 | `passage_hood_detachment_microscope_view` | 28.32 | intentional | crowded, label-stressed |

Historical full scorecard: `test-results/layout_health/health_report.md` (the retired
report's regenerated, gitignored output). Category totals for this run:
`high-empty-space-plus-shrink`=4,
`shrink-stressed`=17, `crowded`=8, `label-stressed`=18, `healthy`=13, `sparse`=5.

## layout_diagnostics Error table

`result.severityDiagnostics` Error-level residuals, from
`tests/e2e/e2e_layout_diagnostics_baseline.mjs` (`docs/active_plans/reports/
layout_diagnostics_baseline.md` is the always-current, regenerated companion to this
row set):

| Scene | Code | Zone | Item A | Item B | Depth | Exempt? |
| --- | --- | --- | --- | --- | --- | --- |
| `adversarial_overflow_smoke` | `unresolved_overlap` | `zone_b` | `b_1` | `b_2` | 10.07 | YES |
| `adversarial_overflow_smoke` | `unresolved_overlap` | `zone_c` | `c_1` | `c_2` | 4.26 | YES |
| `hemocytometer_view` | `unresolved_label_overlap` | `rear_right` | `rear_ethanol_bottle` | `right_hemocytometer_slide_clear` | 0.71 | YES |
| `hemocytometer_view` | `unresolved_label_overlap` | `right_bench` | `right_hemocytometer_slide_clear` | `staining_bottles` | 1.47 | YES |
| `hemocytometer_view` | `unresolved_label_overlap` | `rear_right` | `staining_bottles` | `right_hemocytometer_slide_clear` | 1.47 | YES |

Both scenes carrying Error-level residuals are named in
`BUILD_GATE_EXEMPT_SCENES` (`src/scene_runtime/layout/diagnostics/severity_model.ts`):
`adversarial_overflow_smoke` is an intentional-overflow dev fixture and `hemocytometer_view`
is intentional cross-tier layering (dense scene, content stays readable). No non-exempt
scene carries any Error-level `severityDiagnostics` code in this snapshot, which is exactly
what `countBuildFailures == 0` means.

## What would break this baseline

- A non-exempt scene starts emitting `unresolved_overlap` or `unresolved_label_overlap`
  (or any other `failBuild: true` code): the build gate fails and this file is stale by
  definition, since the gate itself would already be red.
- A currently-exempt scene loses its exemption (removed from
  `BUILD_GATE_EXEMPT_SCENES`): re-run the refresh commands above and update both tables.
- The scene count drifts from 38 (a scene added, removed, or newly skipped by validation):
  update the snapshot counts and re-run the health scorecard.
