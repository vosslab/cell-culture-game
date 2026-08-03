# Walker click-bug register (certified)

M15 deliverable. This is the CERTIFIED register, produced against the sound
walker tree (post M1 validator truth, M2->M13 gesture affordances, M6
actionability enforcement, M12 adjust/drag, M13 load-time gesture invariant).
It supersedes [walk_all_fail_triage.md](walk_all_fail_triage.md) (the pre-M13
read-only triage) as the reference document; M16 consumes THIS file. Every
row below is cross-checked against `test-results/walker/sweep_summary.json`
from the run that produced this register (`timestamp:
2026-07-04T01:00:29.524Z`). Zero protocol, source, or scene file was changed
to produce this register.

## Sweep totals

`npm run walk:all`: **PASS=12, unsupported_gesture=0, FAIL=19** (of 31
protocols under `content/protocols/**`).

This matches the pre-triage baseline (PASS=12 / FAIL=19 / unsupported_gesture=0)
exactly. No protocol flipped PASS<->FAIL membership between the pre-triage run
and this certified run.

### Status since this certified snapshot

The table below is the certified M15 snapshot from the timestamped run above; it
is preserved as history. Current OWNED status for every red / handshake item now
lives in two reconciled sections lower in this file: the
[Scene-manager handshake](#scene-manager-handshake-out-of-walker-scope) owned
ledger (each open row names its owner and the exact clearing action, with resolved
rows kept for history) and [Load-time invariants](#load-time-invariants) (the
owner-approved decision plus the reds each invariant produces). Several
snapshot-table rows have since been cleared by scene-manager placement edits; read
those two sections for present truth rather than re-reading each table row as still
red.

One wording drift (not a category or membership change): `trypan_blue_counting`
now fails with `click_did_not_advance: click on main_cell_counter produced no
state change after 3000ms` instead of the pre-triage's step-validator-shaped
message. The failing step is still `verify_viability_gate` (the last of 9
steps, first 8 pass), and the underlying root cause is unchanged: the step's
`final_state_matches` validator checks `viability_percent: 90` exactly against
the `92.5` set by the prior step, which can never match. The walker now
surfaces this as a stalled click (it keeps re-clicking `main_cell_counter`
waiting for a progress signal that the never-passing step validator never
produces) rather than the older validator-rejection wording. Same protocol,
same step, same fix direction; flagging the wording change so M16 does not
treat it as a new bug.

## Wrong-order negative pass

Ran `protocol_walkthrough_yaml.mjs --wrong-order` against 3 sampled PASS
protocols. In `--wrong-order` mode the walker injects a real visible click on
a non-required scene object before every correct interaction and asserts the
runtime's `wrongOrderClicks` counter increments with no progress, then
proceeds with the correct click. All 3 protocols completed all their steps
with every injected wrong-order click correctly rejected:

| Protocol | Steps | Wrong-order injections | Result |
| --- | --- | --- | --- |
| `cell_seeding_plate_setup` | 4/4 passed | 5 injected (`center_hood_surface`), all rejected (no advance) | Walker PASSED |
| `mtt_reagent_prep` | 4/4 passed | injected (`base_right_micropipette`), all rejected (no advance) | Walker PASSED |
| `sdspage_stain_gel` | 5/5 passed | injected (`center_microwave`), all rejected (no advance) | Walker PASSED |

This confirms the runtime rejects out-of-order interactions (does not silently
advance on a wrong click) rather than the walker only ever exercising the
happy path.

## Ranked clusters (most severe first, by protocol count)

1. **subpart_click_unactionable** -- 5 protocols. A `gesture: click` authored
   directly on a `.<subpart>` target (well, tube, gel lane) can never resolve
   to a DOM node; subparts render as a non-interactive material-tint overlay.
2. **sequence_runner_unimplemented** -- 5 protocols. Every `protocol_type:
   sequence_runner` protocol times out at 30s because mini-protocol chaining
   is not implemented; `window.PROTOCOL_STEPS` never populates.
3. **target_missing** -- now 3 protocols across 2 root causes (`kimwipe_pad`
   never placed: 2 protocols; `hood_surface` missing from a transit scene: 1).
   The former `media_bottle` removed-with-no-replacement cause
   (`drug_dilution_setup`) is RESOLVED/STALE; see the note on that row below and
   the scene-manager handshake section.

## Full register (19 of 19 FAILs)

| Protocol | Step | Gesture | Category | reason_code | Owner | Root-cause group | Screenshot | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `mtt_plate_reaction` | `add_mtt_to_wells` | click | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) | `test-results/walker/fail_add_mtt_to_wells.png` | `test-results/walker/reports/mtt_plate_reaction.json`: target `center_well_plate_96.all_wells` not in DOM |
| `mtt_solubilization_readout` | `add_dmso_to_wells` | click | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) | `test-results/walker/fail_add_dmso_to_wells.png` | `test-results/walker/reports/mtt_solubilization_readout.json`: target `center_well_plate_96.all_wells` not in DOM |
| `plate_drug_treatment_drug_addition` | `add_carb_row_b` | click | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) | `test-results/walker/fail_add_carb_row_b.png` | `test-results/walker/reports/plate_drug_treatment_drug_addition.json`: target `rear_center_carb_stocks.tube_A` not in DOM (fails on row B, the first row walked) |
| `sdspage_load_protein_ladder` | `dispense_into_lane_5` | click | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) | `test-results/walker/fail_dispense_into_lane_5.png` | `test-results/walker/reports/sdspage_load_protein_ladder.json`: target `front_center_gel_cassette.lane_5` not in DOM |
| `sdspage_load_sample_single_lane` | `dispense_lane` | click | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) | `test-results/walker/fail_dispense_lane.png` | `test-results/walker/reports/sdspage_load_sample_single_lane.json`: target `front_center_gel_cassette.lane_1` not in DOM |
| `cell_culture_full` | (none reached) | n/a | other (timeout) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) | see Screenshot caveat below | `test-results/walker/reports/cell_culture_full.json`: `page.waitForFunction: Timeout 30000ms exceeded` |
| `routine_passage` | (none reached) | n/a | other (timeout) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) | see Screenshot caveat below | `test-results/walker/reports/routine_passage.json`: same timeout shape |
| `sdspage_full` | (none reached) | n/a | other (timeout) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) | see Screenshot caveat below | `test-results/walker/reports/sdspage_full.json`: same timeout shape |
| `sdspage_load_samples_batch` | (none reached) | n/a | other (timeout) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) | see Screenshot caveat below | `test-results/walker/reports/sdspage_load_samples_batch.json`: same timeout shape |
| `sdspage_prepare_sample_mix_batch` | (none reached) | n/a | other (timeout) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) | `test-results/walker/crash_screen.png` (last-run timeout; see caveat) | `test-results/walker/reports/sdspage_prepare_sample_mix_batch.json`: same timeout shape |
| `sdspage_destain_gel_setup` | `place_kimwipes` | click | target_missing | placement_never_added | M16-protocol | kimwipe_pad cluster (2) | `test-results/walker/fail_place_kimwipes.png` | `test-results/walker/reports/sdspage_destain_gel_setup.json`: target `kimwipe_pad` not in DOM |
| `sdspage_destain_gel_rock` | `remove_kimwipes` | click | target_missing | placement_never_added | M16-protocol | kimwipe_pad cluster (2) | `test-results/walker/fail_remove_kimwipes.png` | `test-results/walker/reports/sdspage_destain_gel_rock.json`: target `kimwipe_pad` not in DOM |
| `drug_dilution_setup` | `prepare_carb_parent_stock` | click | RESOLVED/STALE (was target_missing) | placement_removed_no_replacement | none (fixed) | standalone | `test-results/walker/fail_prepare_carb_parent_stock.png` | RESOLVED: `dilution_workspace.yaml` `remove_placements` now carries a documented comment (lines 11-13) to KEEP the inherited `rear_left_media_bottle` because the protocol clicks `media_bottle` as the diluent in every dilution step; the `media_bottle` not-in-DOM bug no longer reproduces |
| `passage_hood_detachment` | `inspect_confluence` | click | target_missing | placement_missing_in_transit_scene | scene-manager-external (borderline) | standalone | `test-results/walker/fail_inspect_confluence.png` | `test-results/walker/reports/passage_hood_detachment.json`: target `hood_surface` not in DOM (microscope-view scene never places it) |
| `passage_pellet_reseed` | `transfer_to_conical` | click | no_active_interaction | sequence_exhausted_no_transition | M16-runtime | scene-change-completion cluster (2, unconfirmed shared cause) | `test-results/walker/fail_transfer_to_conical.png` | `test-results/walker/reports/passage_pellet_reseed.json`: step still active, no active target/gesture after last interaction |
| `sdspage_heat_denature_samples` | `open_heat_block_lid` | click | no_active_interaction | sequence_exhausted_no_transition | M16-runtime | scene-change-completion cluster (2, unconfirmed shared cause) | `test-results/walker/fail_open_heat_block_lid.png` | `test-results/walker/reports/sdspage_heat_denature_samples.json`: step still active, no active target/gesture after last interaction |
| `plate_drug_treatment_media_adjustment` | `adjust_media_quadrant_a1_h6` | adjust | validator_rejected (adjust) | adjust_did_not_advance | M16-runtime | adjust-commit cluster (2, unconfirmed shared cause) | `test-results/walker/fail_adjust_media_quadrant_a1_h6.png` | `test-results/walker/reports/plate_drug_treatment_media_adjustment.json`: committing set-point "100" produced no state change after 3000ms |
| `sdspage_prepare_sample_mix_single_lane` | `add_laemmli_buffer` | adjust | validator_rejected (adjust) | adjust_did_not_advance | M16-runtime | adjust-commit cluster (2, unconfirmed shared cause) | `test-results/walker/fail_add_laemmli_buffer.png` | `test-results/walker/reports/sdspage_prepare_sample_mix_single_lane.json`: committing set-point "7.5" produced no state change after 3000ms |
| `trypan_blue_counting` | `verify_viability_gate` | click | validator_rejected (step) | wrong_value / threshold-gap | M16-protocol + design review | standalone | `test-results/walker/fail_verify_viability_gate.png` | `test-results/walker/reports/trypan_blue_counting.json`: `click_did_not_advance` on `main_cell_counter`, first 8/9 steps pass; see wording-drift note above |

### Screenshot caveat: sequence-runner cluster

The single walker writes fixed, non-namespaced screenshot filenames
(`fail_<step_id>.png`, `crash_screen.png`) into the shared
`test-results/walker/` directory, and `walk_all_protocols.mjs` only archives
the JSON report per protocol, not screenshots. All 5 sequence-runner timeouts
crash before any step is reached (the outer `catch` writes `crash_screen.png`,
not a per-step `fail_*.png`), and each of the 5 runs overwrites the same
`crash_screen.png` in turn. Only the LAST one to run in the sweep
(`sdspage_prepare_sample_mix_batch`) survives on disk; the other 4
(`cell_culture_full`, `routine_passage`, `sdspage_full`,
`sdspage_load_samples_batch`) have no protocol-specific screenshot from this
run. This is a real gap in the walker's screenshot naming for crash-class
failures, not a re-triage gap; flagging for M16-runtime alongside the
sequence-runner fix itself (namespace `crash_screen.png` by protocol id, the
same way `fail_<step_id>.png` is namespaced by step).

## Scene-manager handshake (out of walker scope)

The M16 wave closed here for walker scope. Every `target_missing` failure (and
the ambiguous-target crashes that surface as page exceptions) is a scene-placement
gap, not a walker, protocol-flow, or runtime defect. The fix for each is a scene
YAML edit owned by the SEPARATE scene-manager plan. The walker tree changed
nothing in these scenes; it only surfaces the gaps.

This section is the durable OWNED ledger: each currently-open row names its owner
and the exact clearing action; resolved rows are kept for history and marked
RESOLVED. The guard this ledger serves: the moment a scene reds at load,
scene-manager sees exactly which seed clears it. Loud and owned is good; loud and
orphaned is the between-plans trap. Every open row below therefore carries both an
owner and a clearing action.

Placement items must use `clickable` capability; a `decoration_only` placement
will still fail the walker (M6).

Load-time and diagnosability context:

- The M16-D load-time target-existence invariant
  ([target_existence_check.ts](../../../src/scene_runtime/protocol/target_existence_check.ts))
  now makes bugs 1-3 below (missing placements) fail loud at protocol load
  instead of trapping a student mid-walk.
- The walker `pageerror` listener
  ([walker_helpers.mjs](../../../tests/playwright/e2e/walker_helpers.mjs)
  line 45) now surfaces bug 4's `AmbiguousTargetError` (thrown during
  next-target resolution) as the real exception, instead of a bare
  `waitForFunction` timeout.

### Currently open (scene-manager owned)

Each row: owner = scene-manager plan, plus the exact clearing action. These are
the loud-and-owned rows the load-time invariants below make fail at load.

O1. **`conical_15ml` not seeded in `hood_workspace` (passage_pellet_reseed).**
    The `transfer_to_conical` step attaches `conical_15ml` as a CursorAttach held
    tool and mutates it with `ObjectStateChange`, but
    [hood_workspace.yaml](../../../content/protocols/cell_culture/passage_pellet_reseed/scenes/hood_workspace.yaml)
    seeds only `conical_15ml_rack`, not the `conical_15ml` tube itself (the tube
    exists in `centrifuge_workspace`). Clearing action: seed `conical_15ml`
    (`clickable`) in `hood_workspace.yaml`. This row WILL red at LOAD once
    load-time invariant 2 lands (see [Load-time invariants](#load-time-invariants))
    -- that is intended: loud and owned. Owner: scene-manager plan.

O2. **`microtube_rack_24` placed twice in `heat_block_bench.yaml`.** Two distinct
    racks share `object_name: microtube_rack_24` -- placements `front_microtube_rack`
    (line 140) and `mid_eppendorf_rack` (line 118) in
    [heat_block_bench.yaml](../../../content/base_scenes/heat_block_bench.yaml).
    A bare `microtube_rack_24` target is ambiguous. Durable clearing action: give
    the two racks distinct `object_name`s. Owner: scene-manager plan. (Protocol-side
    placement-name disambiguation is the in-scope per-protocol relief already
    applied; the durable `object_name` split is the scene fix.)

O3. **`microtube_rack_24` placed twice in `sample_prep_bench.yaml`.** Same
    `object_name` collision class -- placements `center_microtube_rack` (line 143)
    and `mid_eppendorf_rack` (line 120) in
    [sample_prep_bench.yaml](../../../content/base_scenes/sample_prep_bench.yaml).
    Durable clearing action: distinct `object_name`s. Owner: scene-manager plan.
    This scene backs `sdspage_prepare_sample_mix_single_lane`, whose content-side
    relief is tracked as OC1 below.

O4. **Hood pointer-overlap: `right_hemocytometer_slide_clear` over
    `rear_right_hood_return`.** Surfaced by HoodSceneRefFix (and any earlier-recorded
    hemocytometer-over-hood_return item): the hemocytometer slide sits over the
    hood-return affordance, so a pointer click can land on the wrong object.
    Clearing action: re-place or re-zone so the slide does not overlap the
    hood-return affordance. Owner: scene-manager plan.

O5. **`gel_cassette` / `dilution_tube_rack_8` per-subpart material has no
    visible per-area rendering.** Surfaced by the material-area walker oracle
    (see the 2026-07-04 material-oracle entry in
    [CHANGELOG.md](../../CHANGELOG.md)): tube and lane material
    writes fire zero "Material-area verified" lines, and a DOM probe found
    `data-subpart-overlay` present only for `well_plate_96`. Root cause: the
    `gel_cassette` lane renders material via `kind: svg` whose three material
    cases all emit the SAME asset `mini_protean_gel` (loading a lane produces
    ZERO visual change, a silent no-op); `dilution_tube_rack_8` tubes render
    `material_volume` via `kind: composite` with no `subpart_geometry` and no
    material-tint overlay. Both objects carry per-subpart material STATE with
    no visible per-area rendering. Affected protocols: `drug_dilution_setup`
    (tube writes), `sdspage_load_protein_ladder` and
    `sdspage_load_sample_single_lane` (lane writes). Clearing action: give
    `gel_cassette` / `dilution_tube_rack_8` a `material_tint` subpart overlay
    (`subpart_geometry`), or fix the gel's identical-asset SVG cases so lane
    loading is visible; the existing walker material-area oracle then covers
    them automatically with no walker change. Owner: renderer / object-schema
    owner (architect / scene-manager territory) -- NOT the walker plan (the
    walker only reads; this is a renderer/object change).

### Currently open (content, walker plan)

OC1. **`sdspage_prepare_sample_mix_single_lane` ambiguous `microtube_rack_24` at
     step `cap_and_rack`.** Being cleared now via placement-name disambiguation
     (authored target `microtube_rack_24` -> `center_microtube_rack`; NoActiveProbe).
     Owner: walker plan. In-progress; resolves shortly. Under load-time invariant 1
     this protocol reds at load until the content fix lands (see
     [Load-time invariants](#load-time-invariants)). The durable scene-side split is
     O3.

### Currently open (pedagogy-held, class-wide)

This is a class-wide ruling, open-by-design, not a walker-plan or content defect.
Owner = ARCHITECT (via a Direction-B RFC), with the exact clearing action below.

OP1. **Discrimination-bearing subpart-click class (PEDAGOGY-HELD).** Any
     interaction-level `gesture: click` (or `select`) whose target is a
     discrimination-bearing subpart -- one the student must pick correctly among
     its siblings -- stays held. Subparts render as a `pointer-events: none`
     material overlay with no DOM node, so the click can never resolve; but these
     are NOT auto-rewritten to base-click, because collapsing a
     discrimination-bearing subpart click to a base-object click erases the taught
     skill (which dose in which well/row, which lane) and degenerates the UX to
     repeated identical base-object clicks. Stated as a class so it catches future
     members automatically. Today's ONLY member (and canonical):
     `plate_drug_treatment_drug_addition` (`add_carb_row_b` and all eight
     row-steps; targets `dilution_tube_rack_8.tube_A..G`, seeded as
     `rear_center_carb_stocks.tube_A`, plus per-well `well_plate_96.<well>` dose
     mapping). Status: PEDAGOGY-HELD. Owner: ARCHITECT (Direction-B RFC).
     Clearing action: a future Direction-B RFC -- a proposal that must go to the
     architect, because it reverses the architect-locked pointer-events:none
     overlay contract and touches the scene renderer + scene YAML -- that gives
     discrimination-bearing subpart overlays (`tube_X`, `well_XX`, `lane_N`)
     independent `[data-item-id]` click targets. It is a separate future plan, not
     walker or content work this session. See
     [subpart_click_pattern.md](../decisions/subpart_click_pattern.md)
     (class ruling + Direction-B RFC stub) and
     [midwalk_sweep_triage.md](midwalk_sweep_triage.md) (mid-walk confirmation).

     EXCLUDED from this held class (do NOT fold into the RFC):
     `well_plate_96.all_wells` and any `subpart_group` bulk state-write
     (`mtt_plate_reaction`, `mtt_solubilization_readout`) write the same state to
     every subpart at once -- no correct-subpart choice to preserve -- and are
     served by runtime group-write in a SEPARATE lane, following the base-click
     rewrite. Technique-only single-subpart steps whose graded skill is not
     subpart discrimination (`sdspage_load_sample_single_lane`, dispense
     technique) also follow the base-click rewrite, not this held class.

### Resolved (kept for history)

R1. **`hood_surface` return affordance (passage_hood_detachment).** RESOLVED. Was
    handshake item 1. The `passage_hood_detachment` microscope view
    ([microscope_view.yaml](../../../content/protocols/cell_culture/passage_hood_detachment/scenes/microscope_view.yaml))
    now places `hood_surface` (`clickable`, line 31) as the hood-return affordance
    the `inspect_confluence` step clicks. Also cleared the wrapper sequence runners
    `cell_culture_full` and `routine_passage`.

R2. **`plate_reader` doorway (mtt_solubilization_readout).** RESOLVED. Was handshake
    item 2. The bench workspace
    ([bench_workspace.yaml](../../../content/protocols/cell_culture/mtt_solubilization_readout/scenes/bench_workspace.yaml))
    now places `plate_reader` (`clickable`, line 31) as the reader doorway before
    its `SceneChange` to the reader workspace.

R3. **`kimwipe_pad` on the staining bench.** RESOLVED. Was handshake item 3. The
    shared base scene
    ([staining_bench.yaml](../../../content/base_scenes/staining_bench.yaml))
    now places a real `kimwipe_pad` (`clickable`, line 116) that
    `sdspage_destain_gel_setup` (`place_kimwipes`) and `sdspage_destain_gel_rock`
    (`remove_kimwipes`) click. Also cleared the wrapper sequence runner
    `sdspage_full`.

R4. **Duplicate `media_bottle` / `laemmli_4x_bottle` -> `AmbiguousTargetError`.**
    RESOLVED. Was handshake item 4.
    [plate_workspace.yaml](../../../content/protocols/cell_culture/plate_drug_treatment_media_adjustment/scenes/plate_workspace.yaml)
    now `remove_placements` the inherited `media_bottle` and keeps `rear_center_media`
    (lines 25-36), and
    [sample_prep_bench.yaml](../../../content/base_scenes/sample_prep_bench.yaml)
    now places `laemmli_4x_bottle` once (`rear_center_laemmli`). The live
    duplicate-placement class today is `microtube_rack_24` (see O2, O3).

R5. **`unresolved_label_overlap` blocked the M19 failBuild gate.** RESOLVED. Was
    handshake item 5. The layout engine had reported `unresolved_label_overlap`
    (severity Error, `failBuild:true`) on the shared placements `front_right_gel_comb`
    and `right_tool_area_p10_gel_loading_tip_box` across eight non-exempt scenes
    (`electrophoresis_bench`, `extraction_workspace`, and six `sdspage_*`
    workspaces). The scene-manager placement edits cleared all eight; a fresh
    reconciliation confirmed `countBuildFailures` on non-exempt scenes is 0 and the
    M19 failBuild gate was flipped live in `pipeline/precompute_layout.mjs`. The only
    remaining `unresolved_label_overlap` is on the exempt `hemocytometer_view`; the
    only remaining `unresolved_overlap` is the exempt `adversarial_overflow_smoke`
    dev fixture. The 3 historical object-overlap scenes (`seeding_workspace`,
    `hood_workspace`, `imaging_bench`) are clean.

R6. **`microscope_basic` base scene failed generalization assertions F (item
    overlap) and I (label-label overlap), scoring 7/11.** RESOLVED. Was open item
    O6. Surfaced by the content-derived base-scene discovery widening in
    `tests/playwright/test_generalization_render.mjs` (see the 2026-07-04
    "Base-scene test sets" entry in [CHANGELOG.md](../../CHANGELOG.md));
    `microscope_basic` was one of the 4 base scenes the stale hand list had never
    exercised. Initially suspected as the same shared-base-zone placement-overlap
    family as O4, but the actual root cause was different: `groupVerticalBands` in
    `src/scene_runtime/layout/reflow_zones.ts` used raw vertical-range overlap as
    band membership, so a tall spanning zone could transitively bridge two
    disjoint rows into one band and let items from unrelated rows overlap
    undetected. Clearing action landed: a `crossesDisjointRowGap` predicate now
    excludes that transitive-bridge case from band membership, and a new
    engine-level `item_overlap` diagnostic
    (`src/scene_runtime/layout/diagnostics/item_overlap.ts`) un-blinds cross-zone
    item overlaps generally (shared AABB overlap predicate reused by both
    `run_pipeline.ts` and `structural_guards.ts`). `microscope_basic` was removed
    from `EXPECTED_FAIL_SCENES`, and an identity-clickability spec was added to
    guard the fix. Owner: scene-manager plan (landed).

## Load-time invariants

Decision LANDED (owner-approved, Option 1): land BOTH load-time invariants,
content-fix-first. Blast-radius evidence:
[load_time_invariants_blast_radius.md](load_time_invariants_blast_radius.md)
measured ZERO regression to any currently-passing protocol -- both invariants only
touch protocols already broken at runtime, converting a confusing mid-walk symptom
into a named, located load-time error (the M13 / M16-D / `authored_value_check.ts`
pattern).

- Invariant 1 (reject ambiguous target in `validate_target_existence`): a bare
  `object_name` placed more than once in the active scene throws a named load-time
  error; explicit placement-name targets are exempt. Will red at load:
  `sdspage_prepare_sample_mix_single_lane` -- cleared by its content fix OC1 (in
  progress); durable scene-side split is O3.
- Invariant 2 (`ObjectStateChange` / `CursorAttach` scene-op target must be
  seeded): a scene-op target not seeded in the active scene throws a named load-time
  error. Will red at LOAD: `passage_pellet_reseed` -- cleared by scene-manager
  seeding `conical_15ml` (O1). This is the loud-and-owned row: it reds at load the
  moment invariant 2 lands, and O1 names exactly which seed clears it.

## Methodology

1. Built the current tree (`npm run build`), then ran the full sweep
   (`npm run walk:all`) across all 31 curriculum protocols under
   `content/protocols/**`.
2. Read `test-results/walker/sweep_summary.json` from that run and diffed its
   19 FAIL protocol ids and PASS/FAIL counts against
   [walk_all_fail_triage.md](walk_all_fail_triage.md)'s baseline.
3. For every FAIL, read `test-results/walker/reports/<protocol>.json` (the
   archived per-protocol walker report) to confirm the exact failing
   `step_name`, `target`, `gesture`, and error message, rather than trusting
   only the one-line summary reason.
4. Ran `protocol_walkthrough_yaml.mjs --wrong-order` directly (not through the
   sweep runner) against 3 sampled PASS protocols to prove the runtime rejects
   out-of-order interactions, using the walker's existing visible-UI
   injection path (`pickWrongOrderItem` / `recordInjection`); no protocol,
   scene, or source file was touched.
5. Matched each FAIL's failing `step_name` to its `fail_<step_id>.png`
   screenshot already on disk in `test-results/walker/` from the sweep run
   (filenames do not collide across protocols since step names are unique
   per-protocol, except the sequence-runner crash-screen collision noted
   above).
6. No protocol, scene, or source file was modified to produce this register.

## Files referenced

- `test-results/walker/sweep_summary.json`
- `test-results/walker/reports/*.json` (all 19 FAIL reports plus the 3
  wrong-order sample reports)
- `test-results/walker/fail_*.png`, `test-results/walker/crash_screen.png`
- [walk_all_fail_triage.md](walk_all_fail_triage.md) (pre-M13 baseline this
  register certifies against)
- [walker_timeout_triage.md](../reports/walker_timeout_triage.md) (sequence-runner
  timeout root cause)
