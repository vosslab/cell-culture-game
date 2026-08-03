# Session state and runner integrity

## Decision

Adopt one explicit protocol-session model:

- `initial_state` is an optional root list of exact `{target, state}` entries.
- A target may be one object, one declared subpart, or one declared
  `subpart_group`; group members expand before validation and application.
- Each concrete target identity may be seeded once. Group/member duplication
  and repeated-target identity are errors; an object and one of its subparts
  are distinct identities and may both be seeded.
- `state` is a non-empty flat mapping constrained by declared fields, primitive
  types, numeric ranges and units, and enum closure. Object-level material enums
  use the declared `allowed` list; subpart material identity uses the active
  registry plus `empty` and `mixed`.
- The browser owns a durable target-keyed archive and an active-scene
  reactive projection. Scene changes reconcile projection from archive; state
  writes update both; Restart clears archive and starts from root seed.
- A directly launched mini-protocol applies its own root seed. A sequence
  runner applies only its root seed; a constituent mini-protocol never reseeds
  a running runner session.
- A sequence runner is a non-empty ordered list of unique direct
  `mini_protocol` leaves. Unknown names, repeated names, and nested runners are
  invalid everywhere the package is loaded or walked.

## Rationale

Independent mini-protocol practice needs a truthful starting state, while a
full experiment needs state to remain continuous across scene changes and
constituent boundaries. Implicit scene defaults solved neither problem: they
made prerequisites invisible and allowed state to disappear. Applying every
mini's seed in a runner would be equally incorrect because it would silently
erase prior work.

The strict runner shape makes the session owner and execution order obvious to
the generator, runtime, Python stepper, walker, and instructor. A nested or
repeated runner is not a harmless convenience; it obscures whether a state
transition is first use, replay, or reset.

## Implementation ownership

| Layer | Owner files | Enforced result |
| --- | --- | --- |
| YAML closure and validation | `validation/yaml_schema/constants.py`, `validation/yaml_schema/protocol_validator.py`, `pipeline/gen_protocols.py` | Bad seed shape, overlap, target, field, type, range, enum, material, or runner member fails before generated output. |
| Generated/runtime type | `src/shell/adapter/types.ts`, `src/scene_runtime/protocol/flatten_sequence_runner.ts` | `InitialStateEntry` is emitted and a runner retains only its own root seed. |
| Browser session | `src/protocol_host.tsx`, `src/scene_runtime/state/scene_store.ts` | One fresh session starts once, reconciles scenes, and exposes immutable state diagnostics. |
| Python semantics | `validation/stepper/state.py`, `validation/stepper/runner.py`, `validation/stepper/scene_ops.py` | One state map and material ledger span the runner's direct leaves. |
| Proof | `tests/test_protocol_initial_state.py`, `tests/test_scene_store.mjs`, `tests/test_flatten_sequence_runner.mjs`, `tests/test_stepper_runner_state.py` | Valid direct and runner paths retain expected state; invalid forms fail loudly. |

## Acceptance record

The implementation is accepted only when the focused tests listed above,
content lint, a generated build, and direct plus runner browser walkthroughs
pass. The complete release gates remain recorded in
[wow_recovery_plan.md](../../archive/wow_recovery_plan.md).

## Non-decisions

- This record does not introduce a state-schema version, a new scene operation,
  or an interaction-group target.
- It does not make a group a clickable learner target; interaction targets stay
  singular and exact.
- It does not preserve a session across a browser reload. Restart is explicitly
  a fresh session from the root seed.
