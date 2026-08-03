# Walk-all FAIL triage

Pre-M13 triage evidence; the certified register is M15 after the sound walker.
This report classifies the 19 FAILs from the post-M12 `npm run walk:all` sweep
(`test-results/walker/sweep_summary.json`, `totalProtocols: 31`, `PASS: 12`,
`FAIL: 19`, `unsupported_gesture: 0`) into layer categories so M16 can start
from evidence instead of a raw run. Read-only: no protocol, source, or scene
file was changed to produce this report.

## Summary

- 19 FAILs total. 5 are already covered by the separate
  [walker_timeout_triage.md](../reports/walker_timeout_triage.md) report
  (all `page.waitForFunction: Timeout 30000ms exceeded`); this report defers to
  that report for those 5 and does not re-derive them.
- Of the remaining 14: 12 are one clear dominant root-cause cluster
  (`target_not_actionable` on an authored subpart click target: 5 protocols)
  plus three smaller clusters (`target_missing`: 4 protocols across 2 root
  causes, `no_active_interaction` state-machine gap: 2 protocols,
  `adjust_did_not_advance`: 2 protocols) and one distinct `validator_rejected`
  case (1 protocol).
- Breakdown by owner: 18 of 19 are M16-fixable (protocol edit, or a scoped
  runtime/step-machine fix inside `src/scene_runtime/` and `src/protocol_host.tsx`,
  both inside the walker-hardening plan's scope). 1 (`passage_hood_detachment`)
  is a protocol/scene co-fix where the fix likely needs one placement added to a
  per-protocol scene YAML; flagged as borderline scene-manager scope since it
  touches `content/protocols/*/scenes/*.yaml` geometry, not just `protocol.yaml`
  flow. Zero are flaky; every FAIL reproduced deterministically on re-run.
- No `AmbiguousTargetError` (the M8 twice-placed-object class named in the
  M12 report as the dominant PRE-M12 class) appears anywhere in these 19. That
  class is confirmed retired: none of the 19 failure messages contain the
  string "Ambiguous", and the dominant post-M12 class is different (subpart
  click-target actionability, below).

## Dominant cluster: target_not_actionable (5 protocols, 1 root cause)

The single largest cluster. A `gesture: click` interaction authored directly
on a `.<subpart>` target (a well, tube, or gel lane) can never advance,
because subparts render as a non-interactive material-tint overlay
(`pointer-events: none`), not as their own `[data-item-id]` DOM node. Confirmed
in `src/scene_runtime/renderer/subpart_visual_state_renderer.tsx`: "The overlay
never intercepts clicks: the base art under it stays the click target." The
click resolver (`src/scene_runtime/protocol/click_resolver.ts`) only ever reads
back a base placement_name, never a subpart-suffixed one. No PASSING protocol
in the 12-PASS set authors a subpart-suffixed `gesture: click` target anywhere
(confirmed by grep across all 12 passing `protocol.yaml` files); the working
pattern (see `cell_seeding_plate_setup`'s `seed_96_well_plate` step) clicks the
BASE placement and reserves the `.<subpart>` suffix for the response's
`ObjectStateChange` only.

| Protocol | Failing target | Evidence |
| --- | --- | --- |
| `mtt_plate_reaction` | `well_plate_96.all_wells` (authored) / resolves to `center_well_plate_96.all_wells` | `test-results/walker/reports/mtt_plate_reaction.json`: step `add_mtt_to_wells` fails immediately on this click; the SAME base object (`center_well_plate_96`) was clicked successfully one step earlier in `gather_mtt_materials` |
| `mtt_solubilization_readout` | `well_plate_96.all_wells` | `content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml:57,87,131` -- three separate steps author the identical pattern |
| `plate_drug_treatment_drug_addition` | `dilution_tube_rack_8.tube_A` (resolves to `rear_center_carb_stocks.tube_A`); every row (A-H) of this protocol repeats the same pattern for both the rack tube AND `well_plate_96.<well>` | `test-results/walker/reports/plate_drug_treatment_drug_addition.json`; `content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml:49,58` (and one occurrence per row) |
| `sdspage_load_protein_ladder` | `gel_cassette.lane_5` | `test-results/walker/reports/sdspage_load_protein_ladder.json`; `content/protocols/sdspage/sdspage_load_protein_ladder/protocol.yaml:123` |
| `sdspage_load_sample_single_lane` | `gel_cassette.lane_1` | `test-results/walker/reports/sdspage_load_sample_single_lane.json`; `content/protocols/sdspage/sdspage_load_sample_single_lane/protocol.yaml:100` |

Owner: M16. Fix direction (not itself a fix): rewrite these interactions to
click the BASE placement (mirroring the passing `cell_seeding_plate_setup`
pattern) and keep the `.<subpart>` suffix only inside `response.scene_operations`
`ObjectStateChange` entries. `plate_drug_treatment_drug_addition` needs this
change applied to every one of its 8 row-steps (both the tube-rack click and the
per-well click), the widest single-protocol blast radius in this set.

## target_missing (4 protocols, 2 root causes)

The named base placement itself does not exist anywhere in the mounted
scene (distinct from the cluster above: here the object was never placed at
all, not merely a non-clickable subpart of something that IS placed).

| Protocol | Failing target | Root cause | Evidence |
| --- | --- | --- | --- |
| `drug_dilution_setup` | `media_bottle` | Scene `dilution_workspace.yaml` explicitly `remove_placements`s `rear_left_media_bottle` (inherited from `bench_basic`) and adds no replacement; the protocol's `prepare_carb_parent_stock` step still targets `media_bottle` | `content/protocols/cell_culture/drug_dilution_setup/scenes/dilution_workspace.yaml:10-13`; `test-results/walker/reports/drug_dilution_setup.json` |
| `sdspage_destain_gel_setup` | `kimwipe_pad` | `kimwipe_pad` is never added as a scene placement anywhere in the repo (`content/base_scenes/staining_bench.yaml:107` literally comments "kimwipe_pad is a placeholder; single item avoids collision") | `test-results/walker/reports/sdspage_destain_gel_setup.json`; `content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml:134` |
| `sdspage_destain_gel_rock` | `kimwipe_pad` | Same root cause as above (companion step `remove_kimwipes`) | `content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml:75` |
| `passage_hood_detachment` | `hood_surface` | Step `inspect_confluence` clicks `microscope` (SceneChange to `passage_hood_detachment_microscope_view`), then in the SAME step's sequence clicks `hood_surface` to return -- but the microscope-view scene (`extends: microscope_basic`) never places `hood_surface`; that placement exists only in `hood_workspace` | `content/protocols/cell_culture/passage_hood_detachment/scenes/microscope_view.yaml`; `content/protocols/cell_culture/passage_hood_detachment/protocol.yaml:21-51`; `test-results/walker/reports/passage_hood_detachment.json` |

Owner: `drug_dilution_setup`, `sdspage_destain_gel_setup`, `sdspage_destain_gel_rock`
are M16-fixable protocol/scene edits inside the walker-hardening plan's
`content/protocols/**` scope (either add the missing placement to the
per-protocol scene YAML, or repoint the protocol step at a target the scene
does provide). `passage_hood_detachment` is the one borderline case: the fix
is a placement addition to a per-protocol `scenes/*.yaml` file (a "return to
hood" object in the microscope-view scene), which sits closer to scene-layout
work; flagging for a scene-manager consult rather than assuming it is a pure
M16 protocol edit.

`kimwipe_pad` is one root cause covering 2 protocols (a single scene-placement
fix in `content/base_scenes/staining_bench.yaml` or the two consuming scene
YAMLs clears both).

## no_active_interaction (2 protocols, suspected shared root cause)

The walker's `readProgressSnapshot`/step-completion check reports the step is
"still active" with "no active target/gesture" immediately after the LAST
interaction in that step's `sequence` was clicked and logged as progressing.
Both instances fail on the FINAL (and in one case, only) interaction of their
step, and in both cases that interaction's `response` includes a `SceneChange`:

| Protocol | Step | Sequence shape | Evidence |
| --- | --- | --- | --- |
| `passage_pellet_reseed` | `transfer_to_conical` | 2 interactions (`t75_flask` click with `SceneChange`, then `conical_15ml_rack` click, no SceneChange); fails after the 2nd (last) click | `content/protocols/cell_culture/passage_pellet_reseed/protocol.yaml:38-71`; `test-results/walker/reports/passage_pellet_reseed.json` |
| `sdspage_heat_denature_samples` | `open_heat_block_lid` | 1 interaction only (`heat_block` click with `SceneChange`); fails on that single click | `content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml:18-38`; `test-results/walker/reports/sdspage_heat_denature_samples.json` |

Both cases exhaust their step's `sequence` (interaction pointer reaches the
end) without the step formally transitioning to `next_step`, leaving the
walker with nothing valid to click next. This looks like a step-machine /
`SceneChange`-timing gap rather than a protocol-authoring error (the YAML
itself is unremarkable -- `sequence_complete` with a `SceneChange` in an
interaction response is a common, otherwise-working pattern elsewhere in the
passing set). Owner: M16, but scoped as a runtime investigation in
`src/scene_runtime/protocol/step_machine.ts` (and/or `protocol_host.tsx`'s
`SceneChange` handling), not a protocol YAML edit. Flagging the two as a
suspected shared root cause for a single fix, though this was not proven by
source-level tracing (read-only triage budget); M16 should confirm before
assuming one fix clears both.

## adjust_did_not_advance (2 protocols, no confirmed shared root cause)

Both throw the same walker error shape (`readProgressSnapshot` sees no change
in `interactionIndex`/`activeStepId`/`activeScene`/`completedSteps`/`isComplete`
within 3000ms of committing an `adjust` set-point), but the two instances do
NOT share an obvious structural trigger on inspection:

| Protocol | Step / target | Committed value | Notes |
| --- | --- | --- | --- |
| `plate_drug_treatment_media_adjustment` | `adjust_media_quadrant_a1_h6` / `multichannel_pipette` | `100` | Preceded IN THE SAME STEP by a `click` on the same target (`multichannel_pipette`) whose response is a `SceneChange`; the click succeeded, the following adjust did not |
| `sdspage_prepare_sample_mix_single_lane` | `add_laemmli_buffer` / `micropipette` | `7.5` | This `adjust` is the FIRST interaction of its step (no preceding click); the SAME protocol's earlier step (`add_protein_sample`) successfully commits `adjust ... set_volume: 21` on the SAME object one step earlier, immediately after a `SceneChange`-carrying click |

The "adjust right after a same-step SceneChange" hypothesis and the "adjust as
first-interaction-with-no-preceding-click" hypothesis were both tested against
each other and neither cleanly explains both failures while explaining the
adjacent SUCCESSFUL adjusts in the same two protocols (`set_volume: 21` in
`sdspage_prepare_sample_mix_single_lane` itself succeeds under a similar
shape). Owner: M16, but this needs a dedicated repro session (stepping through
`src/scene_runtime/protocol/step_machine.ts` adjust-commit handling with
console tracing) rather than the read-only diff-reading this triage budget
allowed. Treat as two data points for the same symptom class, not confirmed as
one root cause.

## validator_rejected (1 protocol, reason_code: step-validator threshold gap)

| Protocol | Step | reason_code | Evidence |
| --- | --- | --- | --- |
| `trypan_blue_counting` | `verify_viability_gate` (last of 9 steps; first 8 pass) | `wrong_value` (step_validator, not interaction validator) | `content/protocols/cell_culture/trypan_blue_counting/protocol.yaml:349-372`; `test-results/walker/reports/trypan_blue_counting.json` |

The step's `step_validator` is `final_state_matches` with `target: cell_counter,
contains: { viability_percent: 90 }`. The prior step (`press_capture`) sets
`viability_percent: 92.5` via `ObjectStateChange`
(`content/protocols/cell_culture/trypan_blue_counting/protocol.yaml:342`). If
`final_state_matches`'s `contains` preset does exact-value matching (as its
name and every other observed usage in this repo implies), `92.5` can never
equal the authored `90`, so the gate never passes -- this matches the prompt's
own stated pedagogy ("viability must be 90% or greater"), which needs a
threshold/comparator semantic the `contains` preset does not appear to have.
Owner: M16 for the protocol-value question, but this may surface a genuine
validator-preset gap (no `>=` comparator in `final_state_matches`) that is a
spec/validator design question rather than a one-line protocol edit; flag for
design review alongside the fix.

## Deferred to walker_timeout_triage.md (5 protocols, timeout FAILs)

`cell_culture_full`, `routine_passage`, `sdspage_full`,
`sdspage_load_samples_batch`, `sdspage_prepare_sample_mix_batch` all fail with
`page.waitForFunction: Timeout 30000ms exceeded`. These are already fully
triaged in [walker_timeout_triage.md](../reports/walker_timeout_triage.md):
all 5 are `protocol_type: sequence_runner` protocols hitting the same real bug
(sequence-runner mini-protocol chaining is not implemented in
`src/protocol_host.tsx`/`src/scene_runtime/protocol/step_machine.ts`, which
throws `Unknown step_name in protocol` before `window.PROTOCOL_STEPS` is ever
populated). One fix clears all 5. Note: that report's 6th timeout entry
(`sdspage_extract_gel_from_cassette`) is now PASS in the current sweep --
its scene-layout label/SVG-overlap defect has been fixed since that report was
written.

## Full FAIL register (19 of 19)

| Protocol | Category | reason_code | Owner | Root-cause group |
| --- | --- | --- | --- | --- |
| `mtt_plate_reaction` | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) |
| `mtt_solubilization_readout` | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) |
| `plate_drug_treatment_drug_addition` | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) |
| `sdspage_load_protein_ladder` | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) |
| `sdspage_load_sample_single_lane` | target_not_actionable | subpart_click_unactionable | M16-protocol | subpart-click cluster (5) |
| `sdspage_destain_gel_setup` | target_missing | placement_never_added | M16-protocol | kimwipe_pad cluster (2) |
| `sdspage_destain_gel_rock` | target_missing | placement_never_added | M16-protocol | kimwipe_pad cluster (2) |
| `drug_dilution_setup` | target_missing | placement_removed_no_replacement | M16-protocol | standalone |
| `passage_hood_detachment` | target_missing | placement_missing_in_transit_scene | scene-manager-external (borderline) | standalone |
| `passage_pellet_reseed` | no_active_interaction | sequence_exhausted_no_transition | M16-runtime | scene-change-completion cluster (2, unconfirmed shared cause) |
| `sdspage_heat_denature_samples` | no_active_interaction | sequence_exhausted_no_transition | M16-runtime | scene-change-completion cluster (2, unconfirmed shared cause) |
| `plate_drug_treatment_media_adjustment` | validator_rejected (adjust) | adjust_did_not_advance | M16-runtime | adjust-commit cluster (2, unconfirmed shared cause) |
| `sdspage_prepare_sample_mix_single_lane` | validator_rejected (adjust) | adjust_did_not_advance | M16-runtime | adjust-commit cluster (2, unconfirmed shared cause) |
| `trypan_blue_counting` | validator_rejected (step) | wrong_value / threshold-gap | M16-protocol + design review | standalone |
| `cell_culture_full` | other (see timeout report) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) |
| `routine_passage` | other (see timeout report) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) |
| `sdspage_full` | other (see timeout report) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) |
| `sdspage_load_samples_batch` | other (see timeout report) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) |
| `sdspage_prepare_sample_mix_batch` | other (see timeout report) | sequence_runner_unimplemented | M16-runtime | sequence-runner cluster (5) |

None of the 19 are `flaky`: every FAIL reproduced deterministically and its
mechanism was traced (or, for the two "unconfirmed shared cause" clusters,
traced far enough to rule out the two most obvious hypotheses without a full
source-level repro session).

## Count breakdown

- M16-fixable protocol edits (content YAML only): 9
  (`mtt_plate_reaction`, `mtt_solubilization_readout`,
  `plate_drug_treatment_drug_addition`, `sdspage_load_protein_ladder`,
  `sdspage_load_sample_single_lane`, `sdspage_destain_gel_setup`,
  `sdspage_destain_gel_rock`, `drug_dilution_setup`, `trypan_blue_counting`)
- M16-fixable runtime/step-machine work (`src/scene_runtime/**`,
  `src/protocol_host.tsx`): 9 (2 no_active_interaction + 2
  adjust_did_not_advance + 5 sequence_runner chaining)
- scene-manager-external (borderline; flagged for consult, not assumed):
  1 (`passage_hood_detachment`)
- Flaky: 0

Dominant root-cause group: the `target_not_actionable` subpart-click cluster,
covering 5 protocols with one fix pattern (click the base placement, not the
subpart). The sequence-runner chaining bug is the next largest at 5 protocols
but was already fully covered by the pre-existing timeout triage report, not
newly discovered here.

## Methodology

1. Read `test-results/walker/sweep_summary.json` for the current 31-protocol
   sweep and enumerated all 19 `FAIL` entries.
2. For each FAIL, read the corresponding
   `test-results/walker/reports/<protocol>.json` for the full entry log
   (per-interaction progress messages), not just the summary's one-line
   `failureReason`.
3. For every non-timeout FAIL, cross-referenced the failing target against the
   protocol's own `protocol.yaml` and the relevant scene YAML(s) under
   `content/protocols/<cluster>/<protocol>/scenes/` and `content/base_scenes/`
   to determine whether the target was (a) never placed, (b) placed but not
   independently clickable (a subpart), or (c) placed and clickable but the
   commit/transition mechanics did not fire.
4. Read `src/scene_runtime/protocol/target_adapter.ts`,
   `src/scene_runtime/protocol/click_resolver.ts`, and
   `src/scene_runtime/renderer/subpart_visual_state_renderer.tsx` to confirm
   the subpart-click-is-never-actionable contract at the source level, and
   `tests/playwright/e2e/walker_helpers.mjs` to confirm exactly which
   `window.gameState` signals the walker's `adjust`/`click`
   -did-not-advance checks watch.
5. Grepped every PASSING protocol's `protocol.yaml` for a subpart-suffixed
   `gesture: click` target and found none, confirming the cluster is isolated
   to the FAIL set.
6. No protocol, scene, or source file was modified. No re-run via
   `protocol_walkthrough_yaml.mjs --protocol <name>` was needed beyond the
   existing sweep's per-protocol reports, which already carried enough detail
   (full interaction-by-interaction entries) for every one of the 19.

## Files referenced

- `test-results/walker/sweep_summary.json`
- `test-results/walker/reports/*.json` (all 19 FAIL reports)
- `docs/active_plans/reports/walker_timeout_triage.md`
- `src/scene_runtime/protocol/target_adapter.ts`
- `src/scene_runtime/protocol/click_resolver.ts`
- `src/scene_runtime/renderer/subpart_visual_state_renderer.tsx`
- `tests/playwright/e2e/walker_helpers.mjs`
- `content/protocols/cell_culture/mtt_plate_reaction/protocol.yaml`
- `content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml`
- `content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml`
- `content/protocols/cell_culture/plate_drug_treatment_drug_addition/scenes/plate_workspace.yaml`
- `content/objects/rack/dilution_tube_rack_8.yaml`
- `content/protocols/sdspage/sdspage_load_protein_ladder/protocol.yaml`
- `content/protocols/sdspage/sdspage_load_sample_single_lane/protocol.yaml`
- `content/protocols/cell_culture/drug_dilution_setup/scenes/dilution_workspace.yaml`
- `content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml`
- `content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml`
- `content/base_scenes/staining_bench.yaml`
- `content/protocols/cell_culture/passage_hood_detachment/protocol.yaml`
- `content/protocols/cell_culture/passage_hood_detachment/scenes/microscope_view.yaml`
- `content/protocols/cell_culture/passage_pellet_reseed/protocol.yaml`
- `content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml`
- `content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml`
- `content/protocols/sdspage/sdspage_prepare_sample_mix_single_lane/protocol.yaml`
- `content/protocols/cell_culture/trypan_blue_counting/protocol.yaml`
