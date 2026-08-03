# Mid-walk sweep triage (4 protocols)

Requested by team-lead to check M16 acceptance ("full walker sweep green across
all 26 protocols") ground truth on 4 protocols reported failing mid-walk:
`mtt_solubilization_readout`, `passage_hood_detachment`,
`plate_drug_treatment_drug_addition`, `trypan_blue_counting`. Read-only triage;
no protocol, scene, or source file was changed to produce this report.

Method: fresh `./build_github_pages.sh`, then
`node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <name>` for
each of the 4, cross-checked against
[walker_click_bug_register.md](walker_click_bug_register.md) and
[subpart_click_pattern.md](../decisions/subpart_click_pattern.md).

## Summary table

| Protocol | Failing step | Gesture | Exact symptom | Root-cause class | Owned by | Fix direction |
| --- | --- | --- | --- | --- | --- | --- |
| `plate_drug_treatment_drug_addition` | `add_carb_row_b` | click | `Element #scene-root [data-item-id="rear_center_carb_stocks.tube_A"] does not exist in DOM` | SUBPART-CLICK: interaction `target` names `dilution_tube_rack_8.tube_A`/per-well `well_plate_96.<well>`, a subpart with no DOM node | PEDAGOGY-HELD, class-wide -- canonical member of the discrimination-bearing subpart-click class (`subpart_click_pattern.md` owner ruling; register row OP1). Owner = ARCHITECT (Direction-B RFC) | Stays held: base-click rewrite rejected class-wide (drops dose/well/lane discrimination, degenerate UX). Durable fix is a future Direction-B RFC owned by the architect (subpart overlays get real click targets); not walker-plan-fixable. `all_wells`/`subpart_group` bulk writes are excluded from the class |
| `passage_hood_detachment` | `inspect_confluence` | click | `locator.click: Timeout 30000ms exceeded` -- `rear_right_hood_return` resolves but a `right_hemocytometer_slide_clear` subtree intercepts pointer events on top of it | SCENE: hood pointer-overlap, `microscope_view`/`hood_workspace` | ALREADY OWNED -- register row O4 (scene-manager plan). Confirmed still reproducing verbatim; the earlier `hood_surface` target-missing bug (R1) is separately RESOLVED, but O4's overlap was never cleared | Re-place or re-zone `right_hemocytometer_slide_clear` so it no longer sits over the `rear_right_hood_return` affordance |
| `trypan_blue_counting` | `verify_viability_gate` (step 9/9, last) | click | `click_did_not_advance: click on main_cell_counter produced no state change after 3000ms` | CONTENT/PROTOCOL: `press_capture` sets `viability_percent: 92.5` (protocol.yaml:340); `verify_viability_gate`'s `final_state_matches` checks `viability_percent: 90` exactly (protocol.yaml:366) -- can never match | ALREADY OWNED -- register row (M16-protocol + design review). Confirmed byte-for-byte, including the documented wording drift (now surfaces as `click_did_not_advance` instead of a validator-rejection message) | Change the literal `90` to `92.5` (or add a threshold-style validator param if one exists) so the gate matches the value actually set upstream; needs a design call on whether the pedagogy intends an exact match or a >=90 threshold |
| `mtt_solubilization_readout` | `read_absorbance` (step 3/3, last) | adjust | `adjust_did_not_advance: committing set-point "560" produced no state change after 3000ms`; the protocol's OWN `wrongOrderClicks` counter increments to 1 on this exact commit | RUNTIME (new, not in register): after the step's own `SceneChange` (bench_workspace -> plate_reader_workspace) the reducer's `activeTarget` is left resolved to the OLD scene's placement (`rear_right_plate_reader`) instead of re-resolving `plate_reader` against the NEW scene's placement (`center_plate_reader`); the adjust commit on the correct new-scene node is then scored as an out-of-order click and the step stalls | UNOWNED / NEW. This is not `plate_drug_treatment_drug_addition`'s subpart-click row and not O4; it is a distinct target-resolution timing bug adjacent to the documented [adjust_did_not_advance_rootcause.md](adjust_did_not_advance_rootcause.md) mechanism (stale/ambiguous target resolved for the interaction AFTER a same-step transition), but that report's 2 confirmed cases were both `AmbiguousTargetError` from duplicate placements -- this one shows no page exception and a live `wrongOrderClicks` increment instead, so it is a related but separately-confirmed instance, likely the same family as the register's "scene-change-completion cluster" (`sequence_exhausted_no_transition`, 2 unconfirmed protocols: `passage_pellet_reseed`, `sdspage_heat_denature_samples`). Needs a walker-plan/runtime fix: re-resolve `activeTarget`'s placement against the newly-mounted scene after a same-step `SceneChange`, not the pre-transition scene | Add a new register row for this occurrence (do not silently fold into the register's stale `mtt_solubilization_readout: add_dmso_to_wells` row, which is itself now STALE/RESOLVED -- see note below) |

## Notes on register drift

- The certified register's row for `mtt_solubilization_readout` names failing
  step `add_dmso_to_wells` with `target center_well_plate_96.all_wells not in
  DOM` (subpart-click cluster). That row is now STALE: the current run passes
  `add_dmso_to_wells` and `trituration_to_dissolve` cleanly (both already use
  base-placement clicks, matching the auto-apply-safe verdict
  `subpart_click_pattern.md` gives this protocol) and instead fails three
  steps later at `read_absorbance`, a step the register never mentions. The
  subpart-click fix for this protocol's first two steps has evidently already
  landed; a NEW distinct bug now blocks the third step. Register maintainers
  should replace the `add_dmso_to_wells` row with the `read_absorbance` row
  above rather than mark the protocol simply "still red."
- `passage_hood_detachment`'s handshake history has two separate items: R1
  (`hood_surface` target-missing, RESOLVED) and O4 (hemocytometer/hood_return
  pointer overlap, still OPEN). The current mid-walk failure is O4, not a
  regression of R1.
- `trypan_blue_counting` and `plate_drug_treatment_drug_addition` reproduce
  exactly as already recorded; no drift.

## Answer to the M16 acceptance question

Of the 4: 2 are ALREADY OWNED and correctly tracked (`passage_hood_detachment`
-> scene-manager O4; `trypan_blue_counting` -> M16-protocol + design review
content bug). 1 is PEDAGOGY-HELD by an explicit class-wide owner ruling
(`plate_drug_treatment_drug_addition` is the canonical member of the
discrimination-bearing subpart-click class): the owner chose KEEP HELD for the
whole class, with the durable fix deferred to a future Direction-B RFC owned by
the architect (it reverses the architect-locked pointer-events:none overlay
contract). It closes M16 as an owned, documented held class and is not expected to
go green without that RFC. `all_wells`/`subpart_group` bulk writes are excluded
from the class and follow the base-click rewrite in a separate lane. 1 is an UNOWNED regression/new bug
(`mtt_solubilization_readout`'s `read_absorbance` scene-change target
staleness) that is not represented anywhere in the current register and needs
a new row plus a walker-plan/runtime fix before M16 can claim this protocol
green. M16 is not fully closed: 1 of the 4 is a genuine unaccounted-for gap,
and 1 more (`plate_drug_treatment_drug_addition`) is open-by-design pending
the pedagogy owner, not walker-plan work.

## Files referenced

- [walker_click_bug_register.md](walker_click_bug_register.md)
- [subpart_click_pattern.md](../decisions/subpart_click_pattern.md)
- [adjust_did_not_advance_rootcause.md](adjust_did_not_advance_rootcause.md)
- `content/protocols/cell_culture/trypan_blue_counting/protocol.yaml` (lines
  325-370)
- `content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml`
  (lines 104-149) and its `scenes/bench_workspace.yaml` /
  `scenes/plate_reader_workspace.yaml`
- `content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml`
- `test-results/walker/playthrough_report.json` (from each of the 4 runs
  above, overwritten per run -- last run on disk is `mtt_solubilization_readout`)
