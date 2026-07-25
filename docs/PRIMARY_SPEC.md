# Primary specification

This document is the technical specification for the virtual lab protocol games repo. [PRIMARY_CONTRACT.md](PRIMARY_CONTRACT.md) defines the hard invariants. [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md) describes the design philosophy. [specs/SPEC_DESIGN_CHECKLIST.md](specs/SPEC_DESIGN_CHECKLIST.md) defines the Author YAML vocabulary lock that closes authoring surfaces. This specification defines the schema and runtime expectations that implement those invariants.

## Protocol types

Every protocol declares a `protocol_type` field. The active enum values are `mini_protocol` and `sequence_runner`. Definitions for each kind, the protocol package surface, and the structural use of the word "protocol" live in [PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md#protocol-kinds).

## Protocol YAML top-level fields

Each protocol lives in `content/protocols/<cluster>/<protocol_name>/protocol.yaml` and declares the following top-level fields:

```yaml
protocol_type: mini_protocol
protocol_name: open_plate_workspace
entry_step: open_plate_workspace
learning:
  objectives: "Students completing this mini-protocol will have achieved..."
  outcomes: "Students completing this mini-protocol will be able to..."
  goals: "Overall, this mini-protocol aims to accomplish..."
steps:
  - step_name: open_plate_workspace
    prompt: "Open the well plate workspace."
    sequence:
      - target: well_plate
        gesture: click
        validator: { preset: correct_target }
        response:
          scene_operations:
            - type: SceneChange
              to_scene: well_plate_workspace
    step_validator: { preset: sequence_complete }
    outcome:
      on_success: complete
      on_failure: retry
    next_step: null
```

A `protocol` carries `protocol_name`, `entry_step`, and `steps`. Each `step` carries `step_name`, `prompt`, `sequence`, `step_validator`, `outcome`, and `next_step`. Each `interaction` in a `sequence` carries `target`, `gesture`, `validator`, and `response`. Flow is `entry_step` plus `next_step`; YAML `steps` list order is reading convenience only and never controls flow. Sequence runners list constituent mini-protocols rather than authored steps; see Sequence runners below. Step count is determined by pedagogy. Each step is one pedagogical unit per learning block. Over-atomization (UI-shortcut steps) and under-atomization (multi-skill steps) are review-gated, not count-gated.

## Entry step

The `entry_step` field declares where protocol flow starts.

- `entry_step` is the `step_name` of the first step the runtime runs. Flow starts there and follows `next_step` from step to step.
- The scene a protocol opens in is not a protocol-level field. The protocol vocabulary is geometry-free and scene-free at the flow level; a step's interactions name semantic `target` objects, and the scene adapter resolves those names. A `SceneChange` scene operation in a step's `response` transitions the scene context. See [specs/PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md) and [specs/SCENE_VOCABULARY.md](specs/SCENE_VOCABULARY.md).

### Entry-scene resolution precedence

The runtime resolves the initial scene from the entry step using this precedence:

1. The entry step's optional `scene:` field, when present and non-empty.
2. The first `SceneChange.to_scene` found anywhere in the entry step's `sequence` (scans all interactions, not only `sequence[0]`).
3. Throw a clear error naming the protocol and entry step.

No protocol-level `entry_scene` field exists or is read; adding one would violate the vocabulary closure rule.

For `sequence_runner` protocols: the runner carries no `steps` list. Resolution delegates to the first listed mini-protocol by looking it up in the protocol registry and applying the same three-step precedence to its entry step.

Validation rules:

- `entry_step` must name a `step_name` present in the `steps` list.
- A mini-protocol must not open in the hood unless its first step takes place in the hood. The hood is not a default starting scene.

## Learning block

The `learning` block records the pedagogy contract.

For mini-protocols the three fields are required and use these required leading phrases:

- `objectives`: "Students completing this mini-protocol will have achieved..."
- `outcomes`: "Students completing this mini-protocol will be able to..."
- `goals`: "Overall, this mini-protocol aims to accomplish..."

For sequence runners the `learning` block carries the overall pathway's pedagogy and may use "Students completing this protocol..." in place of the mini-protocol phrasing.

## Step structure

A step is one pedagogical unit. Its structure is the same for every step; there is no per-step discriminator that branches the schema. Every step carries:

- `step_name`: the stable snake_case identifier, used for flow, tests, and debugging.
- `prompt`: what the student is asked to accomplish.
- `sequence`: the ordered list of interactions that make up the step. Order always matters; there is no unordered mode.
- `step_validator`: a named preset that checks whole-step completion.
- `outcome`: the `{on_success, on_failure}` mapping that says how the step resolves.
- `next_step`: names the next step by its `step_name`, or `null` for a terminal step.

Each `interaction` in a `sequence` carries exactly four slots: `target` (the semantic scene object or control acted on), `gesture` (how the student acts on it), `validator` (a named preset checking that one gesture on that one target), and `response` (the post-validation system behavior). The task semantics of an interaction come from the target's `kind` plus the `gesture`; the schema has no separate task-type or completion-path discriminator. What were the legacy `interactionSequence`, `directTool`, `modal`, and `multipleChoice` kinds are all just steps: an ordered `click` sequence, a one-interaction `sequence`, an interaction whose `response` carries a `SceneChange` or `feedback`-only payload, and a `select`-gesture interaction validated by `correct_choice`.

### Gestures

A `gesture` is how the student acts on a target. The value set is closed: `click`, `drag`, `adjust`, `select`, `type`. `adjust` is the continuous, skill-based set-point gesture (a pipette volume, a power-supply voltage, a titrated pH); it must not collapse into `click`. `select` chooses the correct next-step object among the scene objects already present (it reuses the visible scene-object click affordance; there is no answer-choice list); `click` acts on a single directed scene object in the lab space.

### Scene operations

A `response` holds `scene_operations` (an ordered, possibly empty list of typed primitives) and optional `feedback`. There are five ratified `scene_operation` primitives, named with PascalCase `type` values: `ObjectStateChange`, `CursorAttach`, `SceneChange`, `LayoutMove`, `TimedWait`. They describe how the scene changes in response to a validated interaction. The set is closed but extensible. `SvgSwap`, `ColorChange`, `LiquidDisplayChange`, and `SetPointDisplayChange` are reclassified to the object/render layer (invoked by an object's `visual_states`), and `ObjectStateChange` is the sole protocol primitive that mutates declared object state, including material fields (`material_name`, `material_volume`, and the corresponding `held_material_name` / `held_material_volume` on tools) and set-point fields (`set_volume`, `set_temperature`, `set_rpm`, etc.).

### Validators and outcome

Every `validator` and every `step_validator` is a named preset with typed parameters; content creators select from the documented preset library and never write custom validation logic. Interaction presets: `correct_target`, `correct_choice`, `target_with_value`. `correct_choice` is target-equality on the selected scene object (the student chose the correct next-step object among the present objects); `target_with_value` also backs the `type` gesture by coercing the committed text to the declared value's type before comparing. Step presets: `sequence_complete`, `final_state_matches`. The `outcome` mapping has exactly two keys: `on_success: complete` resolves the step, after which flow moves to `next_step`; `on_failure: retry` restarts the whole step, resetting the entire `sequence`. `outcome` never carries an `advance` value and never names a step.

The walker, validator, and runtime dispatch from the step and interaction structure above. They must not dispatch from a `step_name` or from per-protocol special cases.

### Load-time authored-value check

At protocol load the runtime validates every authored value used in a
`target_with_value` validator and every field reference used in a
`final_state_matches` step validator. Each reference is checked against the
target object's declared state-field schema. A type-wrong or unknown reference
throws a named, author-facing error: `UnknownAuthoredObjectError`,
`UnknownAuthoredSubpartError`, `UnknownAuthoredFieldError`, or
`BadAuthoredValueError`. This is a startup guard, not a new authored YAML
field. Authors add nothing; bad values simply fail loudly when the protocol
first loads rather than silently at runtime during a student session.

## Targets and the scene boundary

A `target` is the addressable, semantic scene object or control a student acts on. It is named, not positional. Protocol YAML is geometry-free: it names no plate, well, tube, gel, column, lane, rack, or coordinate. A scene adapter holds a registry that maps each semantic `target` name to a concrete scene object. Targets that fan out to several scene objects are listed explicitly by subpart (for example `treatment_plate.A1`, `treatment_plate.A2`); the vocabulary has no named-group construct. See [specs/SCENE_VOCABULARY.md](specs/SCENE_VOCABULARY.md) for the scene side of this boundary.

- Scientific SVG assets must never be cropped or aspect-distorted in display. See [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md) and [specs/SVG_PIPELINE.md](specs/SVG_PIPELINE.md).

## Events

Events are emitted by the runtime on a state transition, not hand-authored per step. The runtime emits a `<step_name>_complete` event when a step's `step_validator` passes, and a `<equipment_name>_elapsed` event when a timed phase ends. Event names are snake_case and derived from the `step_name` or equipment name of the thing they report; an author who renames a step renames its completion event with it.

## Sequence runners

A sequence runner is a protocol with `protocol_type: sequence_runner`. It declares the ordered list of constituent mini-protocols in place of authored steps. A sequence runner has its own `entry_step` (matching the first mini-protocol's `entry_step`) and a `learning` block scoped to the overall pathway.

## Walker requirement

The walker is a runtime verifier generated from the protocol and scene YAML.

The walker:

- loads the page normally, including the welcome screen;
- starts in the scene reached by the protocol's `entry_step` (resolved through that step's target adapter or a `SceneChange` operation);
- clicks visible objects, buttons, modal controls, and answer choices;
- saves screenshots before and after each meaningful interaction;
- may read game state for verification.

The walker must not:

- branch on a `step_name`, a `protocol_name`, or any per-protocol special case;
- write to game state or any internal runtime state;
- mutate `window.prompt`, `window.confirm`, or similar DOM globals;
- call internal runtime APIs to make progress;
- click DOM nodes that are present but not visibly clickable.

If the walker cannot complete a step through visible UI, the YAML schema, the scene affordance, or the runtime behavior is incomplete. The fix is to extend the YAML, fix the scene, or fix the runtime; the fix is never a per-step or per-protocol walker branch.

## Source-code and content layout

Authored TypeScript source for the shared scene runtime lives under `src/scene_runtime/`. Generated runtime data (protocols, scenes, inventory, registry) emits under `generated/` at the repo root. Do not place generated files under `src/`.

Curriculum content lives under `content/protocols/<cluster>/<protocol_name>/`.

Mini-protocol HTML output uses the `<protocol_name>.html` convention. Example: `passage_hood_detachment.html`, `trypan_blue_counting.html`, `cell_culture_full.html`.

## No schema version

This repo has exactly one schema surface (the closed YAML vocabularies for protocol, scene, object, and material). It does not carry, and must not introduce, a separate schema-version number.

Rules:

- No `schema_version`, `spec_version`, or equivalent field in any authored YAML file.
- No per-surface version constants in code (no `OBJECT_SCHEMA_VERSION`, `PROTOCOL_SCHEMA_VERSION`, `SCENE_SCHEMA_VERSION`).
- No version tokens in test, validator, or generator filenames (no `_v3_`, `_v5_`, `_v7_`). Tests are named for the behavior under test, not for the spec revision that introduced it.
- The unified version anchor is the repo `VERSION` file (CalVer `0Y.0M.PATCH`, currently `26.07`). A schema change ships as a normal repo version bump plus a `docs/CHANGELOG.md` entry; consumers track the repo version, not a per-surface counter.
- `generated/` is rebuilt from current source on every run. There is no persisted artifact whose schema can drift from the source, so no cache-invalidation handle is needed.

Trigger for revisiting this rule: the first time a downstream consumer persists built artifacts across runs (TS runtime snapshot, student-progress store keyed by protocol shape, CDN-served bundle). At that point, introduce exactly one repo-wide `SCHEMA_VERSION` constant; never per-surface counters. Until that trigger fires, the repo `VERSION` is the schema version.

This rule may be promoted to `docs/PRIMARY_CONTRACT.md` once a persistent consumer exists. While it lives here, it is still binding: a patch that adds per-surface schema versioning or version tokens to filenames is rejected at review.
