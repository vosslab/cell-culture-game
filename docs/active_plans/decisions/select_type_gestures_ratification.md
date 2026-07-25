# Decision: select and type gestures ratification reopened (WS-M5-ST)

Status: REOPENED on 2026-07-24. This file records the June implementation,
but its `select` interpretation is no longer an accepted owner decision.

## Owner clarification (2026-07-24)

The repo owner initially recalled `select` as a more specialized decision
gesture, but then clarified that multiple-choice controls can use ordinary
browser clicks and that the intended distinct role of `select` is not
remembered. The worked decision example in
[PROTOCOL_AUTHORING_GUIDE.md](../../specs/PROTOCOL_AUTHORING_GUIDE.md) and the
protocol vocabulary immediately before commit `d5493bd0` are therefore
historical evidence, not a recovered owner decision.

The June implementation instead broadened `select` to choosing among all
clickable scene objects and removed the answer-choice-list concept. Current
content provides no deciding evidence because it authors zero `select`
interactions. Do not treat the June interpretation below as ratified.

No vocabulary or runtime rewrite is authorized by this clarification alone.
Resolve the design later by comparing real decision tasks against the existing
compositional `click` model. A click can produce different semantic results
through the target capabilities and response operations, including
`CursorAttach`, `ObjectStateChange`, `SceneChange`, and `TimedWait`. Only retain
or redefine `select` if a bounded prototype demonstrates a distinct need.
Then update the canonical primary specification with explicit owner approval.

The cross-layer evidence and experiment boundary are recorded in
`docs/specs/GESTURE_MODEL.md`.

## Summary

The June workstream implemented the then-recorded `select` and `type` behavior
outside the original Solid-renderer-migration plan (WS-M4). This work was
tracked as workstream WS-M5-ST.

## Decision

The June implementation recorded these behaviors:

- `select`: means "choose the correct next-step scene object among those present
  in the active scene." It reuses the visible click affordance (no separate
  answer-choice list UI is required). The `correct_choice` validator was
  redefined to target-equality: the selected item's `data-item-id` must match
  the expected target name.

- `type`: supported through the visible type-input affordance
  (`[data-type-input]` + `[data-type-commit]`) implemented in
  `src/shell/hud/type_input.tsx`. The affordance renders only while the active
  interaction's gesture is `type`. The walker fills the input and clicks Commit;
  the committed value routes to `step_machine.handle_type_commit` and is
  validated by the `target_with_value` preset.

## Deferred gestures

`adjust` and `drag` remain deferred. No visible set-point control or drag
surface exists in the host. The walker fails `unsupported_gesture` on protocols
that require either gesture. This is a host/scene/runtime extension task, not a
walker-branch task.

## Spec references

- `docs/PRIMARY_SPEC.md`: gesture value set, `select` and `type` descriptions,
  validator preset definitions (`correct_choice`, `target_with_value`).
- `docs/specs/PROTOCOL_VOCABULARY.md`: canonical gesture and validator terms.
