# Layout error diagnostics investigation

Completed read-only investigation of the 4 Error-severity `severityDiagnostics`
emitted across the 8 review scenes. None is an engine bug; all are authored-composition
issues the diagnostic system correctly surfaces.

## Summary

Across the 8 review scenes the engine emits 4 Error-severity `severityDiagnostics`.
NONE is an engine bug; all are authored-composition issues the diagnostic system
correctly surfaces.

## Error table

| diagnostic_code | scene | involved items | depth scene-pct | root cause | owner | minimal fix |
| --- | --- | --- | --- | --- | --- | --- |
| `unresolved_label_overlap` | `bench_basic` | `rear_left_waste` label vs `center_centrifuge` ARTWORK | 2.4 | `rear_left` zone (top 5-36) and `center` zone (top 38-94) share left edge x=5; centrifuge artwork top y=38 clips the waste label band at y~36. The new `effectiveLabelHalfWidth` detection (geometry-lever-1) widened the detection box enough to flag this cross-zone label-vs-artwork collision; the 4-pass resolver cannot clear it because any nudge hits the zone boundary. | scene-author | Raise `center` zone top to >=40, or reduce `rear_left` `label_offset_y` so the waste label sits at y<=34. |
| `unresolved_label_overlap` | `passage_hood_detachment_microscope_view` | `left_cell_suspension` label vs `instrument_t75_flask` LABEL (symmetric, counts as 2) | ~0.95 each | `instrument_area` (left 31-71) and `left_bench` (left 4-36) overlap at x=31-36; `t75_flask` placed in that band collides with `cell_suspension` (`align_stop` right ~x=36). | scene-author | Move `instrument_t75_flask` to `left_bench` (`align_stop` left), or narrow `instrument_area` left bound to >=37. |
| `unresolved_overlap` | `seeding_workspace` | `rear_right_incubator` | 12.85 | `incubator` `display_width_cm=55` in hood workspace -> visual width ~38 scene-pct and height exceeds the `rear_right` zone (height 31 scene-pct); even at `MIN_SCALE` 0.55 it escapes the zone vertically; `clampSceneBounds` validate phase records worst-axis overshoot 12.85. Pre-existing from M6 (vertical auto-fit severity emission), independent of label work. | scene-author (zone too small) / object-author (object too wide) | Move incubator to a dedicated >=50pct-tall right-side zone, or reduce incubator `display_width_cm` to ~25 in the object library. |

## Classification

Errors 1-3 are authored-scene zone-geometry problems. The `seeding_workspace` error is
an authored-scene zone-too-small issue plus a contributing oversized object. No engine
bug exists among the four.

## M7 zero-Error reconciliation

The 3 label Errors POSTDATE M7. They were surfaced on 2026-06-09 by the
`effectiveLabelHalfWidth` detection widening (the M7-era narrower `label_width` detection
cleared them within the 4-pass budget). The `seeding_workspace` `unresolved_overlap` was
introduced by M6 (2026-06-08, same day as M7) when `clampSceneBounds` began emitting
severity; the M7 evidence table reflects a pre-M6 measurement, so its "zero Error" line
was inaccurate for `seeding_workspace`.

Net: the M7 claim is correct for the 3 label Errors, inaccurate for the seeding object
overlap. See [m7_wp_valid1_evidence_table.md](m7_wp_valid1_evidence_table.md) for the
original M7 evidence.

## Tooling gap

The diagnostics baseline runner (`tests/e2e/e2e_layout_diagnostics_baseline.mjs`) queries
the OLD runtime `diagnostics` stream, NOT `severityDiagnostics`, which is why the baseline
shows `bench_basic` and `passage_hood_detachment_microscope_view` as clean. A baseline
refresh should add a `severityDiagnostics` column. See
[layout_diagnostics_baseline.md](../../active_plans/reports/layout_diagnostics_baseline.md) for the pre-refresh
baseline data.

## Open design question (route to human)

Whether a tiny cross-zone label graze that the label layer structurally cannot fix without
an object move should remain Error (`unresolved_label_overlap`, author must fix zone
geometry) or be downgraded to a Warning (`poor_label_alignment`) is a
diagnostic-severity-contract decision, not an agent edit. Route to human for resolution.
