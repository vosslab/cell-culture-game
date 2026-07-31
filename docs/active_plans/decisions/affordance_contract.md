# Affordance contract

Status: committed (expert_coder, milestone M10). This is the frozen design
contract adopted so the M11 registry and the M12 adjust/drag primitives build
against a settled shape without blocking on a human. This milestone writes no
code; it fixes the shape M11 and M12 implement. The human may override later;
until then this contract is binding and is M11's and M12's entry criterion.

This contract depends on the M7 target-identity decision
([target_identity.md](target_identity.md)): `placement_name` is the DOM and
target key, and every scene-object selector below (`data-item-id`) carries the
resolved `placement_name`. It conforms to the closed gesture and validator
vocabulary in [../../specs/PROTOCOL_VOCABULARY.md](../../specs/PROTOCOL_VOCABULARY.md)
and the walker rule in [../../PRIMARY_SPEC.md](../../PRIMARY_SPEC.md). It
introduces no new authored YAML field.

## What this contract freezes

`src/shell/hud/type_input.tsx` is the template. It is the one gesture module
that already co-locates the five things every gesture affordance must fix:

1. Render shape -- the visible control the student sees.
2. Stable selectors -- the `data-*` attributes the walker drives.
3. Value extraction -- how the committed value leaves the affordance.
4. Dispatch entry -- the single public step-machine method the affordance calls.
5. Walker driver -- the visible-UI path the walker uses to complete the gesture.

Every gesture in the closed set (`click`, `select`, `type`, `adjust`, `drag`)
gets these same five slots frozen here. M11 builds one registry keyed by the
`Gesture` union that owns exactly one dispatch entry per gesture, replacing the
scattered promotion shim at `src/protocol_host.tsx:345-353`. M12 builds the two
new affordances (`adjust`, `drag`) against the frozen selectors and dispatch
entries below.

## Design defaults adopted

- **One shared numeric set-point editor for every `adjust` field.** A single
  editor module (stepper buttons plus a direct numeric entry) serves every
  set-point field: `set_volume`, `set_rpm`, a timed duration, `set_voltage`,
  `set_temperature`, and a titration pH. All are numeric set-points, so all use
  one control. No field needs a different control. A future non-numeric
  set-point (for example a discrete enum selector) would be a new control that
  requires its own ratification; it is out of scope here and is not implied.
- **One `drag` placement primitive with one host affordance.** Drag is modeled
  as source, destination, and accepted-final-state. The source is the dragged
  scene object (the interaction `target`); the destination is another scene
  object; the accepted-final-state is checked by the interaction's existing
  `validator` (and the step's `step_validator`). One host drag surface over
  `#scene-root` serves every drag interaction; there is no per-object drag
  widget and no per-protocol branch.
- **No new authored field.** `adjust` reuses the `target_with_value` preset's
  existing `value` mapping (the committed number is coerced to the declared
  value type and compared, exactly as `type` does). `drag` reuses the existing
  `target` (source) plus the interaction's existing `response`/`validator`
  slots; the destination is derived from those authored slots, not from a new
  field. The gesture set itself is already closed and already contains all five
  gestures, so nothing is added to the vocabulary.

## Per-gesture contract

### click

- Render shape: no dedicated overlay module. The rendered scene object IS the
  affordance. It carries `data-item-id={placement_name}` (M6 stamps it only when
  the object's `capabilities` include `clickable`; decoration objects get no id
  and no candidacy). The hover outline and candidate ring come from
  `src/scene_runtime/renderer/affordance_candidates.ts`, capability-gated by M6.
- Stable selectors: `#scene-root [data-item-id="<placement_name>"]`
  (`resolveSelector` in `tests/playwright/e2e/walker_helpers.mjs:94`).
- Value extraction: none. The click event itself is the signal; the resolved
  gesture stays `click` for a directed scene object.
- Dispatch entry: `step_machine.handle_click(target, "click")`.
- Walker driver: `clickTargetAndWaitProgress(page, placement_name, report)` --
  verify exists and visible, real actionability-checked `locator.click()`, then
  wait for a forward progress signal.

### select

- Render shape: the same visible scene-object affordance as `click`. For a
  `select` interaction the renderer shows equal candidate rings on all clickable
  scene objects and never singles out the correct one (see
  [../../specs/PROTOCOL_VOCABULARY.md](../../specs/PROTOCOL_VOCABULARY.md)
  "select versus click" and SCENE_VOCABULARY interaction-affordance). There is
  no separate answer-choice list and no modal.
- Stable selectors: same as `click` --
  `#scene-root [data-item-id="<placement_name>"]`.
- Value extraction: none beyond the clicked object's `placement_name`. The
  `correct_choice` preset checks target-equality: the selected object equals the
  interaction `target`.
- Dispatch entry: `step_machine.handle_click(target, "select")`. The registry
  promotes a click on the active target to the active `select` gesture, exactly
  as the current shim does at `protocol_host.tsx:348-352`, but from a single
  registry entry rather than an inline ternary.
- Walker driver: `clickTargetAndWaitProgress(page, placement_name, report)` --
  identical to `click`; the host promotes the click to `select`.

### type

- Render shape: `TypeInput` control (`src/shell/hud/type_input.tsx`, the
  template). An in-flow panel mounted in the permanent host
  `#type-input-root`, shown only while `active_interaction_gesture === "type"`.
  Contains a labeled text input, a Commit button, and a visible rejection
  message. The host is outside the optional HUD shell, so `?shell=off` remains
  functional without a body-mounted overlay.
- Stable selectors: `[data-type-input-panel]` (container), `[data-type-input]`
  (the input), `[data-type-target]` (carries the active target),
  `[data-type-commit]` (the button), `[data-type-reject-message]` (rejection).
- Value extraction: the raw draft text from the input, handed to `on_commit`;
  the `target_with_value` preset coerces it to the declared value type before
  comparing.
- Dispatch entry: `step_machine.handle_type_commit(target, committed_text)` --
  the only advance path; `on_commit` calls it and returns accepted/rejected.
- Walker driver:
  `typeCommitAndWaitProgress(page, typedText, report)` -- verify the input and
  Commit button exist and are visible, real `fill()` then real `click()` on
  Commit, then wait for a forward progress signal
  (`walker_helpers.mjs`). The canonical curriculum walker never reads expected
  text from debug state. If a curriculum `type` interaction has no
  learner-visible answer source, it fails with `type_answer_not_visible`.
  No curriculum protocol in this release authors `type`.

### adjust

- Render shape: `SetPointEditor` control (new, M12), mirroring `TypeInput`. An
  in-flow panel mounted in the permanent host `#adjust-editor-root`, shown only
  while `active_interaction_gesture === "adjust"`. Contains a decrement button,
  a direct numeric input, an increment button (the stepper), a Commit button,
  and a visible rejection message. One editor instance serves every set-point
  field; the field being set is named by the active interaction, not by the
  widget.
- Stable selectors (frozen for M12 and the walker): `[data-adjust-panel]`
  (container), `[data-adjust-input]` (the numeric input), `[data-adjust-target]`
  (carries the active target), `[data-adjust-decrement]` and
  `[data-adjust-increment]` (the stepper buttons), `[data-adjust-commit]` (the
  button), `[data-adjust-reject-message]` (rejection). The names mirror the
  `data-type-*` family one-for-one.
- Value extraction: the committed numeric set-point from the editor (whether the
  student reached it by stepper clicks or direct entry). The `target_with_value`
  preset coerces the committed number to the declared value type and compares,
  the same path `type` uses. No new authored field.
- Dispatch entry: `step_machine.handle_adjust_commit(target, committed_number)`
  (new public method, M12). It is the sole advance path for `adjust`, mirroring
  `handle_type_commit`, and returns accepted/rejected for visible feedback.
- Walker driver: `adjustCommitAndWaitProgress(page, numericValue, report)` (new,
  M12) -- verify `[data-adjust-input]` and `[data-adjust-commit]` exist and are
  visible, real `fill()` of the numeric input then real `click()` on Commit,
  then wait for a forward progress signal. The walker reads the expected
  set-point only from the learner-visible current-action rail
  (`[data-current-action][data-action-value]`) and verifies that the displayed
  cue states the same numeric value. It does not read a validator-answer
  projection from `gameState`.

### drag

- Render shape: one host drag surface over `#scene-root` (new, M12). The source
  is the dragged scene object and the destination is another scene object; both
  are ordinary rendered scene items carrying `data-item-id={placement_name}`.
  The drag ghost and any highlight of a valid destination are owned by the
  scene/object render layer, not by protocol logic. There is one drag surface,
  not a per-object widget.
- Stable selectors (frozen for M12 and the walker): the source is
  `#scene-root [data-item-id="<source_placement_name>"]`; the destination is
  `#scene-root [data-item-id="<destination_placement_name>"]`. A host marker
  `[data-drag-surface]` identifies the drag-enabled overlay so the walker can
  assert the affordance is mounted before driving it.
- Value extraction: the destination `placement_name` (from the drop target's
  `data-item-id`). The accepted-final-state is checked by the interaction's
  existing `validator` and the step's `step_validator` (for example
  `final_state_matches` after a `LayoutMove` in the interaction `response`); the
  destination binding uses only existing authored slots.
- Dispatch entry:
  `step_machine.handle_drag_commit(target, destination_placement)` (new public
  method, M12). It is the sole advance path for `drag`; `target` is the source,
  `destination_placement` is the resolved drop placement.
- Walker driver:
  `dragToAndWaitProgress(page, source_placement, destination_placement, report)`
  (new, M12) -- resolve both endpoints with `resolveSelector`, verify each
  exists and is visible, drive a real Playwright `source.dragTo(destination)`
  (actionability-checked, no forced event), then wait for a forward progress
  signal. The destination is read read-only from a debug projection derived from
  the interaction's authored `response`/`validator` (a debug surface, not an
  authored field).

## Frozen dispatch table

One dispatch entry per gesture. M11's registry maps each `Gesture` union member
to exactly one row; there is no scattered if-chain and no promotion ternary
outside the registry.

| Gesture  | Affordance module                             | Dispatch entry (step-machine public method)         | Validator preset it feeds                  |
| -------- | --------------------------------------------- | --------------------------------------------------- | ------------------------------------------ |
| `click`  | rendered scene object                         | `handle_click(target, "click")`                     | `correct_target`                           |
| `select` | rendered scene object (equal candidate rings) | `handle_click(target, "select")`                    | `correct_choice`                           |
| `type`   | `TypeInput` control                           | `handle_type_commit(target, committed_text)`        | `target_with_value`                        |
| `adjust` | `SetPointEditor` control (M12)                | `handle_adjust_commit(target, committed_number)`    | `target_with_value`                        |
| `drag`   | host drag surface (M12)                       | `handle_drag_commit(target, destination_placement)` | interaction `validator` / `step_validator` |

## Selector families (frozen)

| Gesture            | Selectors the walker drives                                                                                                                                                        |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `click` / `select` | `#scene-root [data-item-id="<placement_name>"]`                                                                                                                                    |
| `type`             | `[data-type-input-panel]`, `[data-type-input]`, `[data-type-target]`, `[data-type-commit]`, `[data-type-reject-message]`                                                           |
| `adjust`           | `[data-adjust-panel]`, `[data-adjust-input]`, `[data-adjust-target]`, `[data-adjust-decrement]`, `[data-adjust-increment]`, `[data-adjust-commit]`, `[data-adjust-reject-message]` |
| `drag`             | `[data-drag-surface]`, source and destination `#scene-root [data-item-id="<placement_name>"]`                                                                                      |

The `adjust` selector family is a deliberate one-for-one mirror of the `type`
family, so a reviewer verifies the parallel by name.

## Self-check checklist

M11 (registry) and M12 (primitives) verify their work against these objective
checks. Each is checkable by reading code, running `grep`, or running the
walker; none depends on judgment.

- [ ] The registry keys are exactly the closed gesture set: `click`, `select`,
      `type`, `adjust`, `drag`. No sixth key, no `default` branch that silently
      accepts an unknown gesture.
- [ ] Each gesture has exactly one dispatch entry, matching the frozen dispatch
      table. `grep` finds no gesture routing outside the registry (the shim at
      `protocol_host.tsx:345-353` is gone).
- [ ] Every affordance uses only the frozen `data-*` selectors above. No
      positional, text-content, or nth-child selector drives a gesture.
- [ ] No new authored YAML field is introduced. A `grep` of the protocol schema
      and `validation/yaml_schema/` shows no field added for `adjust` or `drag`;
      both reuse `target`, `gesture`, `validator`, and `response`.
- [ ] `adjust` uses the one shared numeric set-point editor for all five
      set-point fields; there is a single editor module, not one per field.
- [ ] `drag` uses one host drag surface (`[data-drag-surface]`) for every drag
      interaction; there is no per-object drag widget and no per-protocol branch.
- [ ] Each affordance's only advance path is its single public step-machine
      method. No affordance writes runtime state directly; each reads a
      read-only snapshot accessor, mirroring `type_input.tsx`.
- [ ] The walker drives each gesture through the visible affordance with a
      real, actionability-checked interaction. It never forces an event, never
      dispatches a synthetic event, and never writes `gameState`.
- [ ] `click`, `select`, and `type` route through the registry with no behavior
      change: the existing walker sweep on click/select/type protocols stays
      green.

## Residual risks for M11 (registry)

- Promotion parity. The registry must reproduce the current promotion exactly:
  a click on the active target when the active gesture is `select` counts as
  `select`; a click on a non-active target stays `click` and is rejected as
  wrong-order. Moving this from the inline ternary
  (`protocol_host.tsx:348-352`) into the registry must not change which clicks
  advance. Regression guard: the existing wrong-order UI pass.
- Exhaustiveness. The registry should mirror the `SceneOperation` discriminated
  union's `never`-exhaustive dispatch (M9 makes `Gesture` a discriminated
  union), so an unhandled gesture is a compile error, not a runtime fallthrough.
- No affordance for `adjust`/`drag` yet at M11. M11 lands with `click`,
  `select`, `type` wired and `adjust`/`drag` still routing to the M2 temporary
  guard. The registry must leave a single, obvious seam for M12 to plug the two
  new dispatch entries into, not a scattered set of edits.

## Residual risks for M12 (primitives)

- Shared editor, per-field value type. The one numeric editor serves five
  fields with different declared value types (int volume, int RPM, float
  voltage, etc.). The committed number must be coerced to the active field's
  declared type before `target_with_value` compares, the same coercion
  `handle_type_commit` already performs. A hard-coded numeric type would fail a
  float set-point.
- Drag destination binding. The destination is derived from existing authored
  slots (`response`/`validator`), not a new field. M12 must settle precisely
  which existing slot names the destination (a `LayoutMove.to_slot` in the
  `response`, or a `final_state_matches` target/state) and derive it there. If
  no existing slot can name a destination cleanly, that is a vocabulary finding
  to escalate under the cost guardrail, not a new authored field to add
  silently.
- Visible answer provenance. The final `adjust` driver reads the exact set
  point from the visible current-action rail, not `gameState`. The `type`
  driver refuses to proceed without a learner-visible answer source. Drag
  destination routing remains read-only, but no curriculum protocol authors
  `drag` in this release. This closes the hidden-answer risk without adding an
  authored field or a write path.
- Overlay independence. `TypeInput` mounts to `document.body` so it works with
  `?shell=off`. The `SetPointEditor` overlay must do the same; a set-point
  editor mounted inside the optional shell would vanish under `?shell=off` and
  break the walker.
- Drag actionability on scene items. Playwright `dragTo` needs both endpoints
  visible and hit-testable. Because `data-item-id` now carries `placement_name`
  (M7), a scene that places one object twice exposes two distinct drag
  endpoints; M12's drag fixture must confirm the source and destination resolve
  to the intended placements, not collapse onto one.
- Deleting the M2 stopgap. Once `adjust` and `drag` have real affordances and
  M13 lands the load-time invariant, the M2 temporary runtime guard is removed.
  M12 should leave the guard's replacement seam obvious so M13's deletion is
  clean.
