# Layout remaining work label delta audit

## Header note

- Date: 2026-06-10
- Auditor: WS-I subagent (task 15)
- Feeds: WP-6 doc update
- Stats source: `test-results/scene_label_alignment/stats_before/` (38 files)
- Doc source: `docs/LAYOUT_REMAINING_WORK.md` (747 lines)
- Scene coordinate space: CSS px, origin top-left at (16, 16), scene size 1888 x 1062 px
- Scene-percent conversion: `(css_px_value - origin) / size * 100`

## Delta table

| # | Doc line(s) | Claim | Status | Stats evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | 420 | bench_basic: engine emits unresolved_label_overlap Error | CONFIRMED | bench_basic.stats.json layout.label_art_overlap_count=2; label_overlap_pair_count=0 | Error code name comes from diagnostics stream, not stats JSON. |
| 2 | 423 | Involved items: rear_left_waste label vs center_centrifuge ARTWORK | CONFIRMED | rear_left_waste label_bbox y=398.3125; center_centrifuge visual_bbox y=419.546875 | Both present in baseline render. |
| 3 | 424 | rear_left zone top y=5 | CONFIRMED | rear_left.top=69.1 px -> (69.1-16)/1062*100 = 5.0 pct | Exact match. |
| 4 | 424 | rear_left zone bottom y=36 | CONFIRMED | rear_left.bottom=398.32 px -> 36.0 pct | Exact match. |
| 5 | 424-425 | rear_left zone left edge x=5 | CONFIRMED | rear_left.left=110.4 px -> (110.4-16)/1888*100 = 5.0 pct | Exact match. |
| 6 | 425 | center zone top y=38 | CONFIRMED | center.top=419.56 px -> 38.0 pct | Exact match. |
| 7 | 425 | center zone bottom y=94 | CONFIRMED | center.bottom=1014.28 px -> 94.0 pct | Exact match. |
| 8 | 426 | centrifuge artwork top reaches y=38 | CONFIRMED | center_centrifuge.visual_bbox.y=419.546875 px -> 38.0 pct | Exact match. |
| 9 | 426 | waste label band at approximately y=36 | CONFIRMED | rear_left_waste.label_bbox.y=398.3125 px -> 36.0 pct | Exact match. |
| 10 | 433-434, 437-438, 627 | Fix: raise center y_start to >=40 or reduce rear_left label_offset_y so waste label sits at y<=34 | CONFIRMED (authoring fix, not a stats metric) | Zone boundaries confirmed above | Fix prescription geometrically sound. |
| 11 | 462-465, 727 | passage_hood_detachment_microscope_view: x2 symmetric unresolved_label_overlap involving left_cell_suspension label vs instrument_t75_flask LABEL | STALE - count discrepancy | stats: label_overlap_pair_count=0; label_art_overlap_count=1; doc claims 2 entries | "x2" is a diagnostic-entry count (one per direction), not a stats geometry-pair count; label_overlap_pair_count=0 inconsistent with a label-vs-label collision; WP-6 should clarify. |
| 12 | 464 | instrument_area zone left x=31 | CONFIRMED | instrument_area.left=601.28 px -> 31.0 pct | Exact match. |
| 13 | 464 | instrument_area zone right x=71 | CONFIRMED | instrument_area.right=1356.48 px -> 71.0 pct | Exact match. |
| 14 | 465 | left_bench zone left x=4 | CONFIRMED | left_bench.left=91.52 px -> 4.0 pct | Exact match. |
| 15 | 465 | left_bench zone right x=36 | CONFIRMED | left_bench.right=695.68 px -> 36.0 pct | Exact match. |
| 16 | 465 | overlap band x=31 to x=36 | CONFIRMED | instrument_area left 31.0, left_bench right 36.0 | Confirmed. |
| 17 | 726 | bench_basic overshoot 2.4 scene-pct | UNVERIFIABLE FROM STATS | stats has no overshoot magnitude field | Source is docs/active_plans/reports/layout_error_diagnostics_investigation.md. |
| 18 | 727 | passage_hood overshoot ~0.95 each | UNVERIFIABLE FROM STATS | stats has no overshoot magnitude field | Same as row 17. |
| 19 | 420, 460 | bench_basic label_art_overlap_count=2 but doc describes only 1 Error | STALE - undocumented second overlap | bench_basic.stats.json layout.label_art_overlap_count=2; doc lines 422-430 describe one collision | WP-6 must identify the second counted pair. |

## Summary

| Status | Count | Rows |
| --- | --- | --- |
| CONFIRMED | 14 | 1-10, 12-16 |
| STALE (count discrepancy, geometry confirmed) | 1 | 11 |
| STALE (undocumented second overlap) | 1 | 19 |
| UNVERIFIABLE FROM STATS | 2 | 17, 18 |

## Key findings for WP-6

1. All zone coordinate claims are exact matches to the baseline stats; fix prescriptions are geometrically sound.
2. bench_basic has label_art_overlap_count=2 in stats but the doc describes only one collision (rear_left_waste vs center_centrifuge artwork). WP-6 must identify and document the second counted pair.
3. The "x2" phrasing for passage_hood_detachment_microscope_view is a diagnostic-entry count (one entry per direction of overlap), not a stats geometry-pair count. label_overlap_pair_count=0 in stats is inconsistent with a label-vs-label collision. WP-6 should add a clarifying note to the doc.
4. Overshoot magnitudes (2.4 pct for bench_basic, ~0.95 each for passage_hood) are sourced from `docs/active_plans/reports/layout_error_diagnostics_investigation.md`, not from the stats_before JSON files, and cannot be independently verified from stats alone.
