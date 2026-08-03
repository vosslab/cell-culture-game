# Gesture model and status

Status: cross-layer reference, verified 2026-07-24.

## Authority and purpose

This document keeps the gesture model understandable across protocol authoring,
interface controls, scene affordances, runtime dispatch, validation, and the
browser walker. It exists because those layers can share a physical browser
input without sharing the same pedagogical meaning.

[PRIMARY_CONTRACT.md](../PRIMARY_CONTRACT.md) and
[PRIMARY_SPEC.md](../PRIMARY_SPEC.md) remain authoritative. This document does
not silently override them. An explicitly reopened definition is marked
`REOPENED` and must be resolved through evidence plus an owner-approved primary
specification change.

## Keep these three layers separate

| Layer | Question | Example |
| --- | --- | --- |
| Authored gesture | What pedagogical action is the learner performing? | `click`, `select`, `adjust`, `type`, or `drag` in protocol YAML |
| Physical browser input | What does the learner physically do in the browser? | Pointer click, text entry, numeric commit, or drag movement |
| Affordance and capability | What visible UI or object contract makes that input possible? | Scene object, choice control, set-point editor, type input, or drag surface |

A physical browser click does not automatically settle the authored gesture.
For example, a learner can activate a multiple-choice answer with a mouse
click, a keyboard, or assistive technology. "Multiple choice" describes the
decision format, while "click" describes only one possible physical input.
Likewise, the current runtime can receive a DOM click and dispatch it under an
active `select` interaction. That implementation fact does not prove that
`select` is the right authored abstraction.

The object capability named `clickable` is also a separate layer. It is the
current closed object-schema gate for a pointer-interactive scene placement.
There is no separate `selectable` object capability in the current schema.
That naming fact does not make the `select` gesture synonymous with `click`.

## Closed gesture set

The authored gesture value set remains closed:

| Gesture | Pedagogical role | Validator coupling | Current visible path | Authored evidence | Status |
| --- | --- | --- | --- | ---: | --- |
| `click` | Act on one directed lab object; teaches recognition and sequencing | `correct_target` | Pointer interaction with a rendered scene target | 400 interactions | Implemented and browser-proven |
| `adjust` | Set a continuous or numeric set point | `target_with_value` | Shared set-point editor and Commit control | 56 interactions | Implemented and browser-proven |
| `select` | `REOPENED`: reserved value with conflicting historical meanings; its distinct pedagogical purpose is not yet justified | `correct_choice` | Current June path uses rendered scene objects and candidate rings; no current answer-choice UI | 0 interactions | Semantics disputed, unused, and possibly unnecessary |
| `type` | Enter and commit a precise value or text | `target_with_value` | Shared type-input control and Commit button | 0 interactions | Implemented path, no curriculum proof |
| `drag` | Perform a spatial source-to-destination action | `correct_target` | Host drag surface | 0 interactions | Runtime path exists; no curriculum proof; accessibility work required |

The authored counts above come from the current `content/protocols/**/protocol.yaml`
corpus. Sequence runners add no new gesture declarations because they reuse
mini-protocol steps.

## Do not invent a `click` and `select` distinction

The current contract gives `click` and `select` different names and validator
presets (`correct_target` versus `correct_choice`), but the repository does not
yet have authored `select` evidence that demonstrates a necessary pedagogical
distinction.

What is known:

- `click` is the implemented authored gesture for acting on a scene target.
- A physical click can also activate an ordinary button, radio control, or
  multiple-choice answer.
- Multiple choice is a decision format, not proof that the protocol needs a
  separate `select` gesture.
- The present runtime can promote a scene click to `select`, but that mechanism
  is not curriculum evidence.

Until a distinct need is demonstrated, do not describe `select` as synonymous
with multiple choice or assign it a remembered meaning with false confidence.

### `click` has compositional flavors

The protocol does not need a separate gesture name for every consequence of a
click. One authored `click` combines with the target's declared capabilities
and the interaction's response operations:

| Composition | Learner-facing meaning |
| --- | --- |
| `click` + `CursorAttach` `attach` | Pick up or grab an attachable object |
| `click` + `CursorAttach` `detach` | Put down or release the held object |
| `click` + `ObjectStateChange` | Operate, transfer, label, open, close, or otherwise change semantic state |
| `click` + `SceneChange` | Inspect an object or move to another work area |
| `click` + `TimedWait` | Start the authored timed action |
| `click` on a structured subpart | Act on one well, lane, slot, or other addressable subpart |

For example, the `cursor_attachable` object capability allows the grab/release
flavor, while `CursorAttach` records what that accepted click accomplishes.
These are compositional click flavors, not new gesture enum values.

The same principle could support a future answer control: a mouse click,
keyboard activation, or assistive-technology command could all activate one
semantic choice control. That UI format still would not, by itself, justify
the separate authored name `select`.

Do not use these misleading shortcuts:

- "`select` must mean multiple choice."
- "Every clickable object is therefore a select answer."
- "A shared DOM event proves the authored gestures are interchangeable."
- "Different enum names prove different pedagogy."
- "The walker can promote a browser click, so the model is validated."

## Reopened `select` decision

The repository currently contains two incompatible interpretations.

### Presented-choice interpretation

The worked decision step in
[PROTOCOL_AUTHORING_GUIDE.md](PROTOCOL_AUTHORING_GUIDE.md) and the protocol
vocabulary before commit `d5493bd0` describe `select` as choosing one option
from a presented set. Examples include:

- a multiple-choice calculation;
- a phase or fraction to keep;
- a decision that can succeed with feedback and no scene-state mutation.

This interpretation needs explicit answer-choice data and a visible choice
surface. Older runtime types still retain modal and choice identifiers, but the
current interface vocabulary says modal UI is not implemented. The owner has
now clarified that multiple-choice controls could use ordinary browser clicks
and does not remember this as the intended role of `select`; therefore this
history is evidence of a past design, not evidence that it should return.

### June scene-object interpretation

Commit `d5493bd0` changed `select` to choosing the correct next-step object
among all present clickable scene objects, removed the answer-choice-list
concept, and made `correct_choice` target equality on the selected scene
object. The current runtime registry, candidate rings, and validator comments
implement this interpretation.

### Evidence boundary

Current curriculum content authors no `select` interaction, so neither
interpretation has live content or browser evidence. Unit tests can prove
dispatch mechanics, but they cannot decide which model teaches the intended
skill.

Do not perform a vocabulary-wide rewrite from this document. Resolve the
decision later with bounded comparisons:

1. Identify two or three real protocol decisions that might need something
   beyond `click`; include multiple choice only as one candidate format.
2. Prototype the smallest accessible interaction for each candidate without
   changing the closed production vocabulary.
3. Compare those prototypes with ordinary `click` controls and with the June
   scene-object discrimination model.
4. Measure whether a separate authored gesture improves authoring clarity,
   validation, visible feedback, or learning evidence.
5. If no distinct benefit appears, propose retiring the unused `select` value.
6. If a distinct benefit appears, build one real vertical slice and walk it in
   the browser.
7. Obtain explicit owner approval, then update `PRIMARY_SPEC.md`, the protocol
   vocabulary, schema, interface vocabulary, runtime, walker, and tests
   together.

Until that slice is complete, new production `select` content would depend on
an unsettled contract.

## Pointer-target identity

`data-item-id` is the scene-side identity used by delegated pointer routing.
It is not itself a protocol gesture. A node should advertise that identity only
while it can receive the corresponding scene interaction.

For structured objects, dormant subpart geometry may remain in the DOM for
layout and rendering, but it must not advertise an actionable `data-item-id`
until its hit surface is enabled. The walker additionally verifies browser
hit-testing before choosing an alternative target, because visibility and
nonzero geometry alone do not prove pointer actionability.

This rule supports `click` and the current scene-target implementation of
`select` without deciding whether the unused authored `select` value is
ultimately necessary.

## Accessibility note for `drag`

No drag implementation or content change is part of the current work.

Before `drag` becomes curriculum content, the same source-to-destination action
must have an accessible non-drag path. At minimum, keyboard and assistive
technology users need a visible way to choose the source and destination and
commit the same semantic operation, with equivalent validation and feedback.
A pointer-only drag path is not sufficient acceptance evidence.

## Evidence status versus implementation status

"Code path exists" and "gesture is taught successfully" are different claims.

| Evidence level | Meaning |
| --- | --- |
| Schema | YAML accepts the gesture and validator pairing |
| Unit | Validator and step-machine behavior pass without a browser |
| Visible control | The learner-facing affordance exists |
| Walker | A real browser can complete the interaction without state mutation |
| Curriculum proof | At least one production protocol uses the gesture for the intended skill |
| Pedagogical proof | Screenshots and review show that the interaction teaches the intended distinction |

`click` and `adjust` currently reach curriculum proof. `select`, `type`, and
`drag` do not.

## Related documents

- [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md): canonical protocol terms.
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md): authored gesture slot and
  validator coupling.
- [PROTOCOL_AUTHORING_GUIDE.md](PROTOCOL_AUTHORING_GUIDE.md): pedagogy-first
  worked examples.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md): scene target and affordance
  terminology.
- [INTERFACE_VOCABULARY.md](INTERFACE_VOCABULARY.md): shell control and
  selector contract.
- [WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md): visible browser interaction
  evidence.
- [select_type_gestures_ratification.md](../archive/decisions/select_type_gestures_ratification.md):
  reopened June decision record.
- [wow_gesture_coverage_audit.md](../archive/audits/wow_gesture_coverage_audit.md):
  corpus and proof audit.
