# Gesture rubric decision

Status: adopted default (M21). This decision commits the gesture rubric by
adopting the documented default from the authoring guide. A human may override
any mapping later.

This rubric maps each teaching skill class to exactly one gesture from the
closed gesture set. It is the source M22 (gesture right-sizing) checks each
protocol against. The gesture set is closed and defined canonically in
[../../specs/PROTOCOL_VOCABULARY.md](../../specs/PROTOCOL_VOCABULARY.md);
this doc assigns each gesture a skill class, it does not add gestures.

## Source

The mapping is drawn directly from the "pedagogy-first rule" and the per-step
authoring checklist in
[../../specs/PROTOCOL_AUTHORING_GUIDE.md](../../specs/PROTOCOL_AUTHORING_GUIDE.md).
The authoring guide states each gesture's teaching purpose verbatim:

- `adjust` on a continuous control teaches a set-point skill.
- `click` on a scene object teaches recognition and sequencing.
- `select` on an answer-choice target teaches a decision.
- `drag` on a scene object teaches a spatial placement skill.
- `type` on a control teaches entering a precise value.

The guide also names the anti-pattern this rubric exists to catch: collapsing a
skill-based interaction into a rote `click`, for example encoding a pipette
volume as a field on a `click` instead of using `gesture: adjust`.

## The rubric

Each skill class maps to exactly one teaching gesture. Choose the gesture that
matches the skill the step teaches, not the gesture that is easiest to wire.

| Skill class | Teaching gesture | What the student practices |
| --- | --- | --- |
| Set-point on a continuous control | `adjust` | Dialing a numeric set point (pipette volume, power-supply voltage, incubator temperature, titrated pH) up or down to a target value. |
| Decision among present objects | `select` | Choosing the correct next object or answer choice from the objects already visible in the scene. |
| Spatial placement | `drag` | Moving an object to a correct destination zone or slot. |
| Precise typed value | `type` | Entering an exact value (a count, a concentration) as committed text. |
| Single directed action | `click` | Recognizing and acting on one directed scene object in sequence. |

Notes on boundaries between classes:

- `adjust` is the continuous, skill-based set-point gesture. It must not
  collapse into `click`. A step that asks the student to reach a numeric set
  point uses `adjust`, never a `click` carrying a value field.
- `select` chooses among objects already present in the scene (it reuses the
  visible scene-object click affordance; there is no separate answer-choice
  list). A directed action on one known object is `click`, not `select`.
- `type` is for a precise value the student must produce exactly; `adjust` is
  for a value the student dials toward. Prefer `adjust` when the control is a
  continuous set point and `type` when the value is an entered figure.

## The one-line reason rule

Every protocol step uses the rubric gesture for the skill it teaches. A step
that teaches a rubric skill class but stays `click`-only must carry a one-line
reason documenting why. Absent that reason, a `click`-only step that teaches a
non-`click` skill class is a rubric violation M22 fixes.

A valid one-line reason names a concrete blocker, for example: the target has
no wired continuous control yet, or the value is fixed by the protocol and the
student makes no set-point decision. "It was simpler to click" is not a valid
reason; that is exactly the anti-pattern the rubric catches.

## Self-check checklist for M22

Run this checklist against each protocol step to verify it against the rubric.

- [ ] The step's taught skill class is identified (set-point, decision,
      placement, precise value, or single directed action).
- [ ] The interaction `gesture` matches the rubric row for that skill class.
- [ ] No step encodes a set-point as a value field on a `click`; a set-point
      step uses `adjust` with the `target_with_value` validator preset.
- [ ] No decision among present objects is encoded as a bare `click`; a
      decision uses `select` with the `correct_choice` validator preset.
- [ ] No spatial placement is encoded as a `click`; a placement uses `drag`.
- [ ] No precise typed value is encoded as a `click`; a typed value uses
      `type` with the `target_with_value` validator preset.
- [ ] Any step that teaches a non-`click` skill class but stays `click`-only
      carries a one-line reason naming a concrete blocker.
- [ ] The changed step still teaches its objective and completes under the
      walker through the visible UI.

## Related references

- [../../specs/PROTOCOL_AUTHORING_GUIDE.md](../../specs/PROTOCOL_AUTHORING_GUIDE.md):
  the pedagogy-first rule and per-step checklist this rubric draws from.
- [../../specs/PROTOCOL_VOCABULARY.md](../../specs/PROTOCOL_VOCABULARY.md):
  the closed gesture value set and slot charters.
- [affordance_contract.md](affordance_contract.md): the per-gesture affordance
  contract M10 committed, which the wired gestures implement.
