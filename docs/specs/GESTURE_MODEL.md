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
Likewise, a DOM click can dispatch an active `select` interaction. The shared
pointer event does not make `select` synonymous with `click`: the authored
gesture records whether the learner acts on a directed object or chooses among
visible alternatives.

The object capability named `clickable` is also a separate layer. It is the
current closed object-schema gate for a pointer-interactive scene placement.
There is no separate `selectable` object capability in the current schema.
That naming fact does not make the `select` gesture synonymous with `click`.

## Closed gesture set

The authored gesture value set remains closed:

| Gesture | Pedagogical role | Validator coupling | Current visible path | Authored evidence | Status |
| --- | --- | --- | --- | ---: | --- |
| `click` | Act on one directed lab object; teaches recognition and sequencing | `correct_target` | Pointer interaction with a rendered scene target | Current protocol corpus | Implemented and browser-proven |
| `adjust` | Set a continuous or numeric set point | `target_with_value` | Shared set-point editor and Commit control | Current protocol corpus | Implemented and browser-proven |
| `select` | Choose among visible alternatives; teaches interpretation or a laboratory decision | `correct_choice` | Clickable rendered choice cards | Current decision protocols | Implemented and visible-walker-proven |
| `type` | Enter and commit a precise value or text | `target_with_value` | Shared type-input control and Commit button | No current curriculum use | Runtime path only; do not substitute hidden answer entry for visible evidence |
| `drag` | Perform a spatial source-to-destination action | `correct_target` | Host drag surface | Current protocol corpus | Runtime path available; curriculum use remains evidence-driven |

The evidence column is intentionally qualitative. Protocol content changes as
learning activities are revised, and sequence runners add no gesture
declarations because they reuse mini-protocol steps.

## `click` and `select` differ

The current contract gives `click` and `select` different names and validator
presets (`correct_target` versus `correct_choice`). Use `click` for a directed
physical action. Use `select` when the learner must choose among visible,
meaningfully different alternatives and receive feedback on that decision.

Current calculation and interpretation steps use paired visible choice cards.
This keeps the learner's evidence and decision in the scene; the honest
visible walker can inspect and activate the same cards. `select` is not a
generic substitute for a normal scene click, nor does every clickable object
become a choice.

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

Do not use these misleading shortcuts:

- "`select` must mean multiple choice."
- "Every clickable object is therefore a select answer."
- "A shared DOM event proves the authored gestures are interchangeable."
- "Different enum names prove different pedagogy."
- "The walker can promote a browser click, so the model is validated."

## Evidence boundary

`select` is reserved for a genuine interpretation or laboratory decision, not
for a directed physical action. Its visible alternatives must be present in
the scene, distinguishable without relying only on color, and paired with
feedback that explains the result. Unit tests can prove dispatch mechanics,
but visible walkthroughs remain the evidence that the alternatives and
feedback teach the intended skill.

Do not use `select` merely to make a normal step harder. If the learner is
only following a directed physical action, author `click` instead.

## Pointer-target identity

`data-item-id` is the scene-side identity used by delegated pointer routing.
It is not itself a protocol gesture. A node should advertise that identity only
while it can receive the corresponding scene interaction.

For structured objects, dormant subpart geometry may remain in the DOM for
layout and rendering, but it must not advertise an actionable `data-item-id`
until its hit surface is enabled. The walker additionally verifies browser
hit-testing before choosing an alternative target, because visibility and
nonzero geometry alone do not prove pointer actionability.

This rule supports `click` and `select` while keeping their distinct learning
purposes visible to authors.

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

`click`, `adjust`, and `select` currently reach curriculum proof. `type` and
`drag` remain runtime paths without current authored curriculum evidence.

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
