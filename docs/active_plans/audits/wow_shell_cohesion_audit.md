# WOW shell cohesion audit

**Status:** DONE_WITH_CONCERNS (static audit; no production files changed)
**Scope:** `src/shell/`, protocol-host wiring, launcher-to-host transition, and shell-facing CSS.
**Question:** Why does the generalized interface feel like separate systems rather than one student-facing vertical slice?

## Bottom line

The runtime is substantially more coherent than the interface. It has a current
interaction target/gesture, active affordance rings, ordered step progression,
rejection events, a timer state in the scene store, and a terminal completion
event. The student mostly receives a static frame plus one repeated prompt.

The smallest high-value implementation slice is a single **protocol status and
action rail** owned by the shell. It should make exactly one current action
visible, bind that action to the highlighted object, report a rejected attempt
or a timed pause in the same place, and end with a clear completion panel. It
must consume a small, explicit runtime snapshot projection rather than scrape
scene DOM. This is an adapter-plan amendment: `src/shell/adapter/types.ts`
declares the seam closed at lines 3-8.

## Evidence map and ownership

| Problem | Current owner and evidence | Why it fragments the student experience | Proposed owner | Acceptance behavior | Existing / needed browser proof |
| --- | --- | --- | --- | --- | --- |
| The prompt is split across guidance, outline, tip fallback, and hidden compatibility spans. | `src/protocol_host_template.html:30-38,51-60` creates four static prompt/progress surfaces; `src/shell/hud/ProtocolHud.tsx:77-99` teleports four independent Solid roots into them; `src/shell/regions/GuidanceBar.tsx:24-29` renders the prompt while `TipsBubble.tsx:21-44` falls back to "Follow the current step guidance." | A learner sees both an instruction and an often-content-free echo, while the outline repeats truncated prompt text (`StepOutline.tsx:63-70,88-97`). The invisible HUD duplicates the same state (`ProtocolHud.tsx:109-120`). No one region owns "what do I do now?" | `src/shell/hud/ProtocolStatusRail.tsx` (new) owns the single current-action message; `ProtocolHud.tsx` owns one mounted composition root; `src/protocol_host_template.html` retains only semantic layout hosts. | At every active interaction, exactly one visible imperative includes the gesture and student-facing target label. An optional authored tip is visibly subordinate and never replaced by a generic echo. Outline is progress-only, not a second instruction feed. | Existing `tests/playwright/test_framed_layout_m2.spec.ts:107-119` only checks regions exist. **New:** `test_protocol_status_rail.spec.ts` loads a click, select, type, and adjust step; asserts one `[data-current-action]`, matching `[data-affordance="active"]`, and no duplicated prompt text in independent regions. |
| The interface highlights the target but never says which target/gesture the orange ring means. | The snapshot exposes `active_interaction_target` and `active_interaction_gesture` in `src/shell/adapter/types.ts:93-110`; renderer receives them in `src/protocol_host.tsx:349-363`; CSS renders orange/blue rings in `src/style.css:407-458`. `GuidanceBar.tsx:24-29` reads only `current_prompt`. | The visual cue has no textual bridge to the protocol state. This is especially confusing in dense bench scenes, where a generic prompt such as "Set the volume" does not identify the instrument or expected gesture. | `ProtocolStatusRail.tsx`, plus a tiny label resolver supplied by `src/protocol_host.tsx` from the active scene's target adapter / generated object label. | A click/adjust/type instruction names the highlighted object and action; for select, the rail says that blue dashed objects are the candidates. The rail must update after a same-step `SceneChange`. | Existing `tests/playwright/test_interaction_attrs.spec.ts` covers affordance attributes but not learner-facing linkage. **New:** browser assertion that the rail's `data-action-target` equals the active scene item's `data-item-id`, including a scene-change case. |
| Wrong scene clicks have no student-visible retry feedback. | Runtime emits `interaction_rejected` with `reason_code` at `src/shell/adapter/types.ts:156-167`; reducer discards the reason at `src/scene_runtime/protocol/step_machine.ts:257-263`; no region renders `last_outcome`, despite it being available in the snapshot (`types.ts:85-110`). Only the separate type widget renders its local "Entry not accepted" message (`type_input.tsx:77-87,157-168`). | Wrong click, wrong order, and wrong numeric/text entry each fail differently in the runtime but are either silent or use a generic overlay-specific error. A student cannot diagnose whether to retry the same value or return to the highlighted object. | Adapter/runtime owner: `src/shell/adapter/types.ts` and `src/scene_runtime/protocol/step_machine.ts`. View owner: `ProtocolStatusRail.tsx`. Remove local error ownership from `type_input.tsx` / `set_point_editor.tsx` after the rail is proven. | Every rejected visible action produces one persistent-until-next-input rail message with a plain-language reason and the recovery action; correct responses can optionally show authored `feedback.correct`. A retry from failed step validation explicitly says that the step restarted. | Existing `tests/test_shell_signals.mjs` should gain reducer assertions. **New:** `test_protocol_status_rail.spec.ts` deliberately clicks a non-target and submits a bad type/adjust value, then asserts feedback and unchanged progress through visible UI. |
| Progress semantics are technically present but visually ambiguous, and completion erases the current context. | `StepCounter.tsx:24-32` renders bare `completed / total`. `StepOutline.tsx:39-60` calls every card "upcoming" after `current_step_name` is null. On completion reducer sets prompt/tip/target to null (`step_machine.ts:283-293`), which makes `TipsBubble` return its generic fallback (`TipsBubble.tsx:35-41`). | A final 3/3 count does not communicate success, what was accomplished, or where to go next. The outline visually regresses to "upcoming," and the last UI statement is "Follow the current step guidance." | `ProtocolStatusRail.tsx` owns terminal state. `StepOutline.tsx` gains a `complete` display state derived from `is_complete`; `StepCounter.tsx` labels the count ("Step 2 of 5") rather than raw arithmetic. | Completion shows "Protocol complete," the learning outcome/goal or a concise recap, final count, and a visible return-to-launcher or next-protocol action. All outline cards show complete; no generic tip/prompt appears. | Existing walkthroughs prove machine completion but no end-state UI (`tests/playwright/e2e/protocol_walkthrough.spec.ts`). **New:** visible completion assertion after a real mini-protocol walkthrough, plus screenshot. |
| Timed waits block the protocol but communicate only with a small label attached below the equipment. | Host schedules 0.5-2 s projection at `src/protocol_host.tsx:375-390`; `timed_wait_runtime_delay_ms` deliberately caps laboratory time at 2 s (`src/scene_runtime/protocol/timed_wait.ts:5-14`). Store has timer flags (`scene_store.ts:87-90`), renderer shows a label below the object (`scene_item.tsx:696-700`), and its CSS positions it at `bottom: -2.25rem` (`style.css:460-480`). The shell snapshot has no wait state (`adapter/types.ts:93-110`). | The current interaction may already advance while the runtime is deliberately paused; the only explanation can sit outside a crowded or clipped scene object. The learner sees an apparent "next action" that cannot work yet. | Adapter/runtime owner: timed-wait snapshot event/state in `types.ts`, `step_machine.ts`, and host scheduler. View owner: status rail. Scene-item label remains secondary contextual evidence. | On timer start, the rail replaces the action with "Waiting: <display>" and a clear short simulation-time cue; scene controls cannot look ready. On elapsed, the next action appears once, not before. | Existing `tests/test_scene_op_deps.mjs:366-371` proves state write only. **New:** visible timed-wait test observes rail state, waits for it to clear, and completes through the next visible control. |
| Type and adjust actions are detached overlays with their own visual system and feedback rules. | Host appends two roots directly to `document.body` (`protocol_host.tsx:491-557`); `TypeInput.tsx:97-169` uses inline fixed positioning at bottom `16px`, z-index `1000`; adjust follows the same pattern. These controls are outside the layout grid and remain mounted under `?shell=off`. | They can overlap the guidance band and visually read as browser dialogs rather than laboratory controls. They duplicate rejection handling, typography, colors, and action language. Debug independence has accidentally shaped the normal student layout. | `ProtocolHud.tsx` / new rail owns a named action-control slot. `protocol_host.tsx` still supplies callbacks but does not append body roots. `src/style.css` owns shared CSS classes rather than inline styles. | A type/adjust control appears in the rail's action slot, occupies no scene area, has the same completion/retry copy as click/select, and does not overlap the bottom guidance/status surface at 1280x900 or 390x844. `?shell=off` remains a debug-only runtime test and may intentionally omit controls. | Existing `test_shell_disable_flag.spec.ts:47-109` protects debug runtime independence. **New:** viewport screenshots and type/adjust visible-path tests at desktop and narrow viewport. |
| Shell layout is coupled to a static HTML scaffold and independent mounts, making ownership failures non-fatal and hard to observe. | Template owns layout and placeholders (`protocol_host_template.html:23-65`); shell only emits an invisible compatibility container (`ProtocolHud.tsx:109-123`); `mount_into` logs and skips missing regions rather than failing (`ProtocolHud.tsx:47-66`). Host measures the scene before the shell mount (`protocol_host.tsx:199-245,559-573`). | A missing or renamed region silently creates a partial interface. Four independent roots make lifecycle and layout order harder to reason about. The visible shell is not a component tree, so it cannot own a responsive flow. | `ProtocolHud.tsx` becomes the sole visible shell composition root mounted in `#shell-root`; template gives it one `#shell-root` host adjacent to `#scene-root`. `protocol_host.tsx` passes all props once. | Missing required student-facing shell host throws clearly in production pages. One Solid tree owns header, rail, outline, and action control placement. Scene remains a sibling / non-ancestor to preserve asset integrity. | Existing `test_protocol_host.spec.ts:219-241` checks roots and hidden HUD. **New:** test one visible shell root, all critical regions, and a controlled failure for a deliberately malformed test template. |
| Launcher-to-host navigation is a mechanical file list, not a learning-path handoff. | `Launcher.tsx:148-199` divides every item into "Full protocols" and "Mini-protocols"; cards link directly to `<protocol>.html` (`91-133`). The browser test only checks index completeness and that one link mounts roots (`test_launcher.spec.ts:66-127`). | Students must choose among implementation categories rather than a recommended starting point, learning objective, expected time, and the relation of a mini-protocol to a complete workflow. The host opens with no orientation recap. | `Launcher.tsx` owns learner-oriented card hierarchy; `ProtocolStatusRail.tsx` owns a short "you are practicing..." startup block. Generated slim index may need an approved explicit recommendation/path field, not a UI heuristic. | Launcher presents a clearly recommended full workflow and mini-protocol practice alternatives using the authored goal hook and trustworthy estimate only. Host confirms protocol title, learning objective, step count, and a "begin" action before the first required interaction. | Existing `test_launcher.spec.ts` remains index/navigation regression. **New:** assert recommendation/start label and host orientation block; content fixture must use actual authored protocols per `NO_FIXTURE_POLICY.md`. |

## Smallest cohesive implementation slice

This deliberately does **not** try to redesign all SVGs, author content, or
replace the layout engine. It fixes the shared layer that makes every protocol
feel less fragmented.

```text
protocol runtime
  -> explicit ShellViewSnapshot: current action | feedback | waiting | complete
  -> one ProtocolHud component tree
  -> one status-and-action rail
       -> text bridge to highlighted scene target
       -> retry / timer / completion state
       -> type and adjust controls in the same action slot
  -> scene remains a sibling, preserving SVG layout/cropping guarantees
```

### Required ownership boundaries

1. **Plan amendment first:** the adapter is a closed surface. Add only explicit
   state required to show `last_rejection` (reason plus target/gesture) and
   `pending_timed_wait` (target/display). Do not add open `metadata`, arbitrary
   feedback blobs, or direct shell-to-runtime mutation.
2. **Runtime owns facts:** `step_machine.ts` and the timer callback derive
   rejection/wait/completion facts. The shell must never infer them from CSS,
   timers, or DOM attributes.
3. **Shell owns presentation:** `ProtocolHud.tsx` and the new status rail select
   the one learner-visible message and use existing snapshot data. The type and
   adjust components become controls in this composition, not global overlays.
4. **Template owns only hosts:** retain sibling scene/shell structure, but stop
   distributing learner-visible shell content across static placeholders.
5. **Scene renderer retains visual affordance:** orange/blue rings and the
   equipment-local wait marker remain; the rail is their textual and temporal
   explanation, not a duplicate scene rendering system.

### Acceptance scenario

For a real mini-protocol with click, invalid click, type/adjust, timed wait,
and completion:

1. Launcher explains the selected learning block and starts the protocol.
2. Host shows one action: verb + target, matching the active ring.
3. A wrong visible click produces recovery guidance without changing progress.
4. A timed operation changes the rail to waiting; no premature next-action cue
   appears; completion of the timer reveals the next action.
5. Type/adjust controls occupy the same action location and use the same
   feedback language.
6. The final step shows a completion recap, all outline steps complete, and a
   clear return/continue route.

## Test-gap summary

Current tests prove roots, region existence, CSS affordance attributes, debug
shell independence, generated index coverage, and internal scene-store timer
flags. They do **not** prove a coherent student state transition across
instruction -> wrong action -> recovery -> timed wait -> completion. That
end-to-end browser proof is the main missing acceptance test for this slice.

## Residual risks and NEEDS_CONTEXT items

- **NEEDS_CONTEXT:** Student-facing target labels need a canonical generated
  object label source. The snapshot currently carries machine
  placement/object names; displaying raw identifiers would not be an upgrade.
- **NEEDS_CONTEXT:** A launcher "recommended path" must be authored or approved
  as a vocabulary addition. Do not infer curricular sequence solely from file
  names or current index order.
- **Risk:** A responsive shell must not constrain, crop, or place content inside
  `#scene-root`; `PRIMARY_CONTRACT.md` item 3 and `PRIMARY_DESIGN.md` visual
  integrity rule remain binding.
- **Risk:** Existing `?shell=off` tests are valuable debug checks, but normal
  student affordances should not be architected around debug-mode independence.

## Static verification

- Read-only source audit completed over the files cited above.
- Existing test inventory reviewed: `test_launcher.spec.ts`,
  `test_protocol_host.spec.ts`, `test_framed_layout_m2.spec.ts`,
  `test_shell_disable_flag.spec.ts`, interaction-affordance tests, walkthroughs,
  and `test_scene_op_deps.mjs`.
- ASCII-only check: PASS (`LC_ALL=C rg -n '[^\\x00-\\x7F]'` returned no matches).
