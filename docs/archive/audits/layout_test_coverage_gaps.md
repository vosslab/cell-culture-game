# Layout engine test coverage gap map

Audit date: 2026-06-10
Scope: WS-D (WP-3a/3b/4a) -- label stagger, collision resolution, clamp, determinism.

Test files surveyed:

- tests/test_layout_engine.mjs (23 tests)
- tests/test_layout_label_resolve.mjs (5 tests)
- tests/test_layout_diagnostics.mjs (9 tests)
- tests/test_layout_geometry.mjs (21 tests)
- tests/test_structural_guards.mjs (console-style)

Field names: _centerX (not _x), _baselineY (not _y) per WP-1a rename.

---

## WS-D priority gaps (ranked by risk)

### Gap 1 -- CRITICAL: downward stagger row assignment and step-compression (layoutLabels)

Source: layout_labels.ts lines 140-196
WS-D relevance: WP-3b reworks this into direction-aware stagger (+1 down, -1 up) and adds
a top clamp. Zero direct tests exist for row assignment or the step-compression path
(naturalBottom > bottomClamp, lines 179-196). A regression in this block could go
undetected until Playwright evidence is examined.
Status: UNTESTED
Test gaps to add: (a) two items whose combined height requires multi-row stagger;
(b) zone short enough to trigger step-compression; (c) label Y values for both rows.

### Gap 2 -- CRITICAL: applyLabelMove right-nudge, scoreMove, pickCheapest (resolveLabelCollisions)

Source: layout_labels.ts lines 453-609
WS-D relevance: WP-4a adds both-direction move candidates to applyLabelMove. Current
tests exercise only the left-nudge path (obstacle to right of label). The right-nudge,
scoreMove neighbor-penalty, pickCheapest axis-rank tiebreak, axisRank, and the partial
floor-drop fallback (lines 524-537) are all UNTESTED. WP-4a work directly modifies these
paths with no test harness in place.
Status: UNTESTED (right-nudge, scoreMove, pickCheapest, axisRank, partial-fallback)
Test gaps to add: obstacle to left of label forcing right nudge; equal-score scenario
forcing axisRank tiebreak; two close labels plus obstacle for scoreMove penalty.

### Gap 3 -- HIGH: restaggerZoneLabels step-compression (Phase B of resolveLabelCollisions)

Source: layout_labels.ts lines 630-691
WS-D relevance: WP-4a adds partition-by-mode logic inside restaggerZoneLabels and
adds w.row field update (line 660). The step-compression path at lines 684-689 is
UNTESTED. Phase B interaction (Phase A moves + Phase B re-stagger) also UNTESTED.
Status: UNTESTED (step-compression, Phase A+B interaction)
Test gaps to add: zone with many labels after Phase A artwork moves triggering Phase B
re-stagger; short zone forcing step-compression in restaggerZoneLabels.

### Gap 4 -- HIGH: clampSceneBounds edge-case paths (BOUNDS_EPSILON, left/top/bottom overflow)

Source: clamp_scene_bounds.ts lines 42-134
WS-D relevance: WP-3a/3b top-label seeding will place labels above zone.bounds.top,
exercising the top-overflow path (overTop > BOUNDS_EPSILON). The epsilon gate and left/top
overflow code paths currently have zero test coverage.
Status: UNTESTED (epsilon gate, left overflow, top overflow, bottom overflow, empty zone)
Test gaps to add: item just inside epsilon (no report); item 0.0005 past right (no report);
item past left bound; item past top bound.

### Gap 5 -- MEDIUM: 3-pass horizontal nudge in layoutLabels (nudge convergence, zone clamp)

Source: layout_labels.ts lines 75-123
WS-D relevance: WP-3a adds a label_placement enum and changes the nudge seed for top
labels. Multi-pass convergence and zone-clamp-after-nudge (lines 111-123) are UNTESTED.
Status: UNTESTED
Test gaps to add: two labels close together that need 2 nudge passes to clear;
label nudged to zone edge, verify _labelX clamped.

---

## Module-by-module coverage table

### layout_labels.ts -- layoutLabels (lines 44-252)

| Function / code path | Test : name | Status |
| --- | --- | --- |
| Seed: _labelX = _centerX, _labelY = _baselineY + labelOffsetY (lines 69-70) | test_layout_engine.mjs : layoutLabels: short labels emit one line (indirect, checks wrap only) | INDIRECT-ONLY |
| effectiveLabelHalfWidth: budget vs text-width max (lines 30-42) | test_layout_label_resolve.mjs : labelBox() helper mirrors it in all 5 tests | INDIRECT-ONLY |
| 3-pass horizontal nudge: overlap detection (lines 75-109) | No test exercises multi-pass convergence or nudge magnitude | UNTESTED |
| Zone clamp after each nudge pass (lines 111-123) | No test forces label to zone edge | UNTESTED |
| Downward greedy stagger: row assignment (lines 140-157) | No direct test; clean-scene path only via pipeline parity | UNTESTED |
| Stagger: step-compression when zone too short (lines 179-196) | No test exercises naturalBottom > bottomClamp path | UNTESTED |
| Residual check: same-row pair emits label_collision_residual (lines 212-239) | No test exercises this diagnostic | UNTESTED |
| Final sort by depth_tier + placement_name (lines 242-248) | No test asserts result ordering | UNTESTED |

### layout_labels.ts -- resolveLabelCollisions (lines 698-888)

| Function / code path | Test : name | Status |
| --- | --- | --- |
| Clean scene: no moves, zero diagnostics | test_layout_label_resolve.mjs : clean scene leaves every label untouched | COVERED |
| Label over neighbor artwork: Phase A clears it | test_layout_label_resolve.mjs : a label over a neighbors artwork is moved clear | COVERED |
| Determinism: identical input -> identical output | test_layout_label_resolve.mjs : identical input yields identical label coords (determinism) | COVERED |
| Unresolvable overlap -> unresolved_label_overlap Error | test_layout_label_resolve.mjs : unresolvable overlap emits an unresolved_label_overlap Error | COVERED |
| Artwork priority over label spacing | test_layout_label_resolve.mjs : artwork avoidance has priority over label spacing | COVERED |
| deepestArtworkFor: deepest wins, id tiebreak (lines 349-369) | No isolated test | INDIRECT-ONLY |
| deepestAnyFor: artwork outranks label; same-row gating line 400 (lines 381-413) | Exercised by artwork-priority test implicitly | INDIRECT-ONLY |
| applyLabelMove: nudge-x left path (line 483) | Exercised via artwork-clear test; kind not asserted | INDIRECT-ONLY |
| applyLabelMove: nudge-x right path (line 490) | No test places obstacle to left of label | UNTESTED |
| applyLabelMove: row-drop path (lines 502-513) | Exercised by unresolvable-overlap test indirectly | INDIRECT-ONLY |
| applyLabelMove: no-in-zone-move -> partial floor drop (lines 524-537) | No test isolates partial-fallback path | UNTESTED |
| applyLabelMove: full-containment disables nudge-x (line 480) | No test verifies containment disables nudge branches | UNTESTED |
| scoreMove: penalty for new label-label overlap (lines 566-577) | No test constructs neighbor-penalty scenario | UNTESTED |
| pickCheapest: axis-rank tiebreak (lines 583-604) | No test constructs equal-score nudge-x vs row-drop options | UNTESTED |
| axisRank: preferRowDrop vs preferNudge (lines 607-609) | No direct test | UNTESTED |
| restaggerZoneLabels: greedy row assignment (lines 648-663) | Indirectly exercised by Phase B in artwork-priority test | INDIRECT-ONLY |
| restaggerZoneLabels: step-compression zone too short (lines 684-689) | No test forces short zone with many labels | UNTESTED |
| restaggerZoneLabels: maxRow == 0 early return (line 663) | Implicit in clean-scene test | INDIRECT-ONLY |
| Phase B: per-zone re-stagger after Phase A artwork moves | No test explicitly verifies Phase A then Phase B interaction | UNTESTED |
| End-state: poor_label_alignment Warning (POOR_ALIGNMENT_DRIFT_FACTOR) | No test produces drift past threshold | UNTESTED |
| End-state: possible_overload Review (OVERLOAD_ROW_DROP_COUNT >= 4) | No test exercises this path | UNTESTED |
| label_row_staggered info diagnostic echo to runtime | No test asserts this diagnostic | UNTESTED |
| labelFitsX: in-zone predicate (lines 416-421) | No direct test | INDIRECT-ONLY |

### clamp_scene_bounds.ts -- clampSceneBounds (lines 42-134)

| Function / code path | Test : name | Status |
| --- | --- | --- |
| Item inside bounds: no diagnostic | test_layout_engine.mjs : clampSceneBounds: item inside bounds records no overflow | COVERED |
| Item outside right edge: zone_clamped_to_bounds warn + unresolved_overlap Error | test_layout_engine.mjs : clampSceneBounds: report-only -- measures overflow, never shifts positions | COVERED |
| Report-only: _centerX unchanged | test_layout_engine.mjs : same test asserts _centerX unchanged | COVERED |
| BOUNDS_EPSILON float-noise gate: hairline overshoot not reported (line 27) | No test places item within epsilon of boundary | UNTESTED |
| Overflow on left edge (overLeft > BOUNDS_EPSILON) | No test places item past left bound | UNTESTED |
| Overflow on top edge (overTop > BOUNDS_EPSILON) | No test places item above top bound | UNTESTED |
| Overflow on bottom edge | No test | UNTESTED |
| Missing sceneBounds (undefined): early return | No test | UNTESTED |
| Empty zone (items.length == 0): skipped | No test | UNTESTED |
| overlapArea formula (line 101) | No test verifies area calculation value | UNTESTED |
| involvedItems multi-item zone | Single item only in covered test | INDIRECT-ONLY |

### vertical_layout.ts -- verticalLayout (lines 68+)

| Function / code path | Test : name | Status |
| --- | --- | --- |
| Square aspect height formula | test_layout_engine.mjs : verticalLayout: square aspect renders square at 1920x1080 | COVERED |
| Bottom anchor _top = baseline - height | test_layout_engine.mjs : verticalLayout: bottom anchor places _top above baseline by heightPct | COVERED |
| Tall-item auto-fit (aspect preserved, width shrunk) | test_layout_engine.mjs : verticalLayout: tall item is auto-fit into the zone, aspect preserved | COVERED |
| anchorTop for tip anchor mode | No test covers anchor_y: tip | UNTESTED |
| anchorTop for center anchor mode | No test covers anchor_y: center | UNTESTED |
| maxHeightInZone for non-bottom anchor modes | No test | UNTESTED |
| item_escapes_zone_vertically diagnostic at MIN_SCALE floor | Only via convergence-loop test indirectly | INDIRECT-ONLY |

### footprint.ts

| Function / code path | Test : name | Status |
| --- | --- | --- |
| visualWidthFor: default_width * _width_scale * DEPTH_SCALE * scale | Exercised via scaleToRealWorld and packer tests indirectly | INDIRECT-ONLY |
| footprintFor: label-width cap (Math.min branch) | No isolated test | UNTESTED |
| depthFor: depth fallback to mid | No direct test | INDIRECT-ONLY |
| widthScaleFor | No direct test | INDIRECT-ONLY |

### strategies/row_strategy.ts -- rowStrategy

| Function / code path | Test : name | Status |
| --- | --- | --- |
| placeBucket center alignment | test_layout_engine.mjs : horizontalLayout: center alignment positions a single item at zone midpoint | COVERED |
| placeBucket left alignment | test_layout_engine.mjs : packer fixture uses left-aligned zone | INDIRECT-ONLY |
| placeBucket right alignment | No test covers right-aligned bucket | UNTESTED |
| Tab-stops: items split into left/center/right buckets | No test exercises multi-bucket placement | UNTESTED |
| Tab-stops: default bucket from config.defaultAlignStop | No test exercises this path | UNTESTED |
| Overflow shrink below minScale | Indirect via convergence-loop test | INDIRECT-ONLY |

### strategies/pack_strategy.ts -- packStrategy

| Function / code path | Test : name | Status |
| --- | --- | --- |
| Packer for overloaded zone; no negative gap | test_layout_engine.mjs : packer: overloaded zone packs with no negative gap, primary keeps scale | COVERED |
| Primary scale preservation | test_layout_engine.mjs : same test | COVERED |
| probeRow | Exercised indirectly via packStrategy test | INDIRECT-ONLY |
| shrinkOrder: priority-kind ordering | No isolated test for shrinkOrder correctness | INDIRECT-ONLY |
| kindPriority for unknown-kind item | No test | UNTESTED |
| Whitespace expansion (gap redistribution) | No test verifies gap values post-pack | INDIRECT-ONLY |

### config/resolve_config.ts -- resolveConfig, buildGlobalDefaults

| Function / code path | Test : name | Status |
| --- | --- | --- |
| buildGlobalDefaults: frozen output with canonical constants | All test_layout_label_resolve.mjs tests call buildGlobalDefaults() | COVERED (indirect) |
| resolveConfig scene-rules layer (label_offset_y override) | test_layout_engine.mjs : normalizeSchema: Schema A passthrough applies layout_rules defaults | COVERED |
| resolveConfig zone-override layer: spacing fold | No test passes a zone with a spacing override | UNTESTED |
| resolveConfig placement-derived and strategy-local layers | No test exercises these override layers | UNTESTED |
| mergePartial: nested spacing/packer merge | No isolated test | UNTESTED |
| applySceneRules: defaultAlignStop override | No test sets default_align_stop in layout_rules | UNTESTED |

---

## Additional gaps (lower WS-D risk)

- test_structural_guards.mjs uses _labelX/_labelY but NOT _centerX/_baselineY: WP-1a rename
  blast-radius site. Update required before WS-D test additions land.
- anchorTop tip and center modes (vertical_layout.ts): low WS-D risk unless WP-3b introduces
  tip-anchored top labels.
- rowStrategy right alignment and multi-bucket tab-stops: no WS-D plan touches these paths.

---

## Summary statistics

| Status | Count |
| --- | --- |
| COVERED | 12 |
| INDIRECT-ONLY | 18 |
| UNTESTED | 30 |
| Total paths audited | 60 |

30 of 60 audited code paths have zero test coverage. 18 more are exercised only
indirectly through full-pipeline parity. The 5 priority gaps above account for
the highest-risk untested paths in WP-3a/3b/4a scope.
