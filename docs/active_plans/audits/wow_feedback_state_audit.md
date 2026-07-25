# Feedback and completion-state audit

## Scope and evidence

This is a read-only audit of the student-facing protocol host. It traces the
closed runtime event stream into the current visible shell. It does not change
the contract or production code.

The contract requires a student to see the relevant object, action, state
change, and next step ([PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md)).
The current runtime has more state than the shell presents: the snapshot holds
`last_outcome`, `pending_validator_kind`, `is_complete`, active target, and
active gesture, while `interaction_rejected` carries a reason code
([step_machine.ts](../../../src/scene_runtime/protocol/step_machine.ts),
[types.ts](../../../src/shell/adapter/types.ts)).

Evidence reviewed:

- The reducer and event emitters in
  [step_machine.ts](../../../src/scene_runtime/protocol/step_machine.ts).
- The host's timer, renderer wiring, and startup path in
  [protocol_host.tsx](../../../src/protocol_host.tsx).
- Shell surfaces in [protocol_hud.tsx](../../../src/shell/hud/protocol_hud.tsx),
  [guidance_bar.tsx](../../../src/shell/regions/guidance_bar.tsx),
  [authored_tip.tsx](../../../src/shell/regions/authored_tip.tsx),
  [type_input.tsx](../../../src/shell/hud/type_input.tsx), and
  [set_point_editor.tsx](../../../src/shell/hud/set_point_editor.tsx).
- Existing runtime tests:
  [test_step_machine.mjs](../../../tests/test_step_machine.mjs),
  [test_protocol_emitter.mjs](../../../tests/test_protocol_emitter.mjs), and
  [test_timed_wait.mjs](../../../tests/test_timed_wait.mjs).
- Existing browser evidence paths: the protocol walker writes `initial_state.png`,
  per-step screenshots, and `final_screen.png` under `test-results/`
  ([helper_walker.mjs](../../../tests/playwright/e2e/helper_walker.mjs)).

## State matrix

| State | Trigger and runtime event/snapshot | Current visible response | Defect | Desired response | Acceptance test |
| --- | --- | --- | --- | --- | --- |
| Initial/loading | Host has a fully populated initial snapshot, then `machine.start()` emits `protocol_loaded` and `step_started`. | The static shell mounts; prompt is empty only during the tiny pre-start interval. | No explicit loading/error boundary. A startup exception leaves a blank or partially static page. | A short `Preparing your lab...` state until `step_started`; a visible, actionable host-error panel for setup failure. | Browser boot test asserts loading disappears into a named first step; injected missing protocol/scene asserts error panel, not only `pageerror`. |
| Active step | `step_started` sets prompt, tip, interaction index, active target, and gesture. | Guidance bar shows prompt; tip bubble shows authored tip or generic fallback; active SVG receives an affordance ring. | The student is told a step but not the expected gesture or why that object is active. Generic fallback repeats no useful coaching. | Guidance names object and gesture in learner language; active ring and a compact "Click/adjust/type here" cue agree. | Screenshot and DOM assertion show prompt, one highlighted target, and gesture cue for click, select, type, adjust, and drag. |
| Wrong target / wrong gesture | Any invalid scene action emits `interaction_rejected` with `wrong_target`; snapshot preserves target/gesture and stores only validator kind. | No shell component reads the rejection event or reason. The highlight remains, so the runtime is correct but visibly silent. | Student experiences a click that appears ignored; no recovery instruction. | Transient, non-shaming coach panel: "Not that yet. First [expected action]." Retain target ring. | Visible wrong-object click produces `data-feedback-kind=wrong_target`, names the next action, does not advance, and clears after correct action. |
| Wrong value / retry | Type, adjust, drag, or state validator rejects with `wrong_value`; final-state failure emits `step_completed: retry` then restarts the same step. | Type and adjust show generic rejection text. Drag and click-state failures are silent. Step retry immediately restores the same prompt without explaining what did not meet the criterion. | Equivalent semantic failure gets inconsistent feedback; the highest-value teaching moment is absent for most paths. | Explain the failed criterion at the interaction level; on retry say what must be corrected before redoing the sequence. Never expose validator jargon. | Each gesture family receives a wrong-value browser test; final-state retry shows retry feedback, unchanged progress, reset interaction count, and a useful next instruction. |
| Valid interaction | `interaction_validated` advances the index, applies operations, and changes active target/gesture. | Object state can visibly change and next target is ringed. No acknowledgement occurs if the operation itself has little visual movement. | A valid click may feel like nothing happened until the learner notices the next ring. | Brief success acknowledgement tied to observed state change, then a clear next cue. Keep it quiet enough for multi-click steps. | Correct interaction asserts a success cue and changed next-target cue; screenshot pair proves a visible before/after difference. |
| Type/adjust validation | Visible fixed-bottom editor calls the public commit API. Invalid numeric draft and rejected adjust set `aria-invalid` plus a message; type rejection shows a message. | This is the one feedback family with a visible error message. | The messages are generic, the type input lacks `aria-invalid`, and neither labels the target, expected unit/range, or recovery route. The fixed panel can also compete with a low scene object. | Target-specific label, units/constraints from authoring, inline error state for both controls, and anchor/avoidance behavior that does not cover the active asset. | Browser tests submit blank, non-finite, and wrong values; assert visible target-aware text, `aria-invalid` on both controls, focus stays in field, and active asset remains unobscured. |
| Timed wait | Validated response runs `TimedWait`; the store marks target `timed_wait_active`, the renderer shows its display badge, input is rejected during the wait, and callback resumes operations. | An equipment-local pale badge appears only when the target is visible and its bottom offset is not clipped. The walkthrough can detect `[data-timed-wait=active]`. | The semantic pause is technically visible but weak, local, and disconnected from the guidance/progress shell; clicking during the wait receives an event but no student-facing explanation. | A global phase banner with equipment, authored display, compressed-time progress/remaining indicator, and "Waiting - controls resume shortly." Keep the local badge as object anchoring. | Browser screenshot while active proves global and local wait cues; attempted click shows wait explanation; elapsed transition removes both and resumes exactly once. |
| Step completion / transition | `step_completed: complete` increments progress, clears active interaction, then emits the next `step_started`; scene change may happen first. | Step counter changes and outline's current card moves. The clear-to-next transition can be visually instantaneous. | No confirmation of what was achieved, and no explicit scene-transition acknowledgement. The outline marks prior cards only by positional status. | A short completion pulse/stamp naming the accomplished action, then a next-step handoff. New scene gets an arrival label before its active cue. | Two-step browser walkthrough captures completion and next-step states; asserts progress increments once, previous card receives completed status, and next cue is visible after a scene change. |
| Protocol complete | Final valid step emits `step_completed: complete`, then `protocol_completed`; reducer sets `is_complete=true` and clears prompt/tip/active target. | The counter may read total/total, but prompt and tip become empty/fallback, all outline cards become `upcoming`, and no completion component reads `is_complete`. | This is a direct visual contradiction: successful completion removes guidance, erases completed/current outline status, and provides no student confirmation or next action. | Dedicated completion screen/banner with outcome summary, objectives/outcomes recap, elapsed/practice option, and return-to-protocol-list action. Keep every outline item completed. | Complete a real mini-protocol by visible UI; final screenshot must contain completion title, total/total, all cards completed, no active ring, and a usable next action. |
| Fatal author/runtime error | Load-time validators, missing scene/protocol, unsupported `LayoutMove`, or renderer/store operations throw descriptive errors. | Console/page error and test failure. There is no caught UI error surface. | Fail-loud engineering is correct, but a student sees a broken simulation rather than a recoverable explanation. | A separate fatal boundary says the activity could not load, gives a non-sensitive identifier, retry/return actions, and preserves detailed error in console/report. | Inject known missing protocol, scene, and unsupported operation in host harness; assert one visible fatal panel and no misleading completion/progress state. |

## Event-to-UI gaps

The key observation is not missing instrumentation. The event union already
provides `interaction_rejected.reason_code`, `step_completed.resolution`,
`scene_changed`, `scene_operation_applied`, and `protocol_completed`. The
snapshot likewise preserves `last_outcome` and `is_complete`. The current HUD
subscribes to that snapshot but renders only step name/prompt/progress in an
`aria-hidden` compatibility node, plus four region projections: prompt, tip,
counter, and outline. No production shell component consumes the rejection,
resolution, completion, or error state.

The timed-wait path is the exception. It has a visible object-local badge and
browser coverage, but no shell-level continuation explanation. That explains
why the walker can correctly wait while a student can still interpret the
brief pause as a stalled interaction.

The completion defect is the most severe contradiction: `protocol_completed`
sets `current_step_name`, prompt, tip, and active affordance to null. The
outline's null-current logic renders every card as upcoming. Thus the most
successful terminal state reads as less informative than the initial state.

## Ranked fixes

1. **P0: Add one shared feedback/completion region driven by the existing
   snapshot and last event.** It must render reject reason, retry, validated
   acknowledgement, timed-wait status, transition, completion, and fatal state.
   This repairs the largest coverage gap without altering protocol vocabulary.
2. **P0: Make completion a first-class visible state.** Preserve completed
   outline status after terminal completion and show an outcome-oriented finish
   panel with a next action. This directly satisfies the visible-UI contract.
3. **P1: Turn wrong actions into recovery coaching.** Map the closed reject
   reasons to short learner language and retain the active affordance. Start
   with wrong target and final-state retry, then cover wrong value/gesture.
4. **P1: Promote TimedWait from an object badge to a phase state.** Add global
   wait feedback and an explicit response to blocked input; retain the local
   equipment marker for spatial meaning.
5. **P1: Normalize value-entry feedback.** Make type and adjust equally
   target-aware, invalid-state aware, and visually non-obscuring.
6. **P2: Add a host error boundary.** Keep developer errors loud, but give
   students a truthful recoverable screen instead of a silent broken page.

## Test plan

Extend the existing visible-UI walker rather than adding internal-state-only
tests. For each row above, capture a screenshot at the state boundary and
assert a stable semantic selector such as `data-feedback-kind`,
`data-protocol-complete`, or `data-host-error`. Unit tests should continue to
prove event and reducer correctness; browser tests must prove that an emitted
event changes the screen in a pedagogically coherent way.

The focused Node command run during this audit passed emitter and timer tests,
but direct execution of `tests/test_step_machine.mjs` failed before assertions
because Node ESM could not resolve the extensionless `validators` import from
`step_machine.ts`. Run the repository's supported TypeScript/test command when
implementing these acceptance tests; do not treat that direct-Node failure as a
product-state failure.

## Residual risk

This audit traces source and existing test/screenshot mechanisms. It does not
claim a fresh visual inspection of every protocol in a browser. The follow-up
must use the real walker and inspect captures for representative click, select,
type, adjust, drag, timed-wait, scene-change, retry, completion, and fatal
states.
