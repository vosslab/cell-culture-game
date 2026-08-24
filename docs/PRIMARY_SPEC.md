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
        instruction: "Open the well plate workspace."
        hint: "Choose the well plate's visible click target."
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

A `protocol` carries `protocol_name`, `entry_step`, and either `steps` or
`mini_protocols`; it may also carry a root `initial_state` session seed. Each
`step` carries `step_name`, `prompt`, `sequence`, `step_validator`, `outcome`,
and `next_step`. Each `interaction` in a `sequence` carries `target`,
`gesture`, `instruction`, `hint`, `validator`, and `response`; the guidance
fields are required non-empty plain strings.
Flow is `entry_step` plus `next_step`;
YAML `steps` list order is reading convenience only and never controls flow.
Sequence runners list constituent mini-protocols rather than authored steps;
see Sequence runners below. Step count is determined by pedagogy. Each step is
one pedagogical unit per learning block. Over-atomization (UI-shortcut steps)
and under-atomization (multi-skill steps) are review-gated, not count-gated.

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

Each `interaction` in a `sequence` has six required slots: `target` (the
semantic scene object or control acted on), `gesture` (how the student acts on
it), `instruction` and `hint` (non-empty plain-string pre-action guidance),
`validator` (a named preset checking that one gesture on that one target), and
`response` (the post-validation system behavior). The task semantics of an
interaction come from the target's `kind` plus the `gesture`; the schema has no
separate task-type or completion-path discriminator. What were the legacy
`interactionSequence`, `directTool`, `modal`, and `multipleChoice` kinds are
all just steps: an ordered `click` sequence, a one-interaction `sequence`, an
interaction whose `response` carries a `SceneChange` or `feedback`-only
payload, and a `select`-gesture interaction validated by `correct_choice`.

Within one step, every repeated exact `(target, gesture)` pair must author
guidance whose normalized `instruction` values are distinct, and whose
normalized `hint` values must be distinct, so the live next-action message and
an already-open hint both change between materially different substeps. A
`select` pair must not name the correct target, placement identity, or learner
label before a rejection; a `type` pair must not reveal a literal expected
value. The content validator enforces these literal identity checks using the
available object and placement registry. It does not claim to recognize every
scientific synonym, so author review remains responsible for pedagogical
quality.

Guidance progression follows reachable flow. After every accepted interaction
that has a successor, the runtime advances the visible `instruction` and any
already-open `hint` together to the next authored pair. Therefore adjacent
authored interactions in reachable flow use distinct normalized `instruction`
and `hint` text, including the boundary from the final interaction in one step
to the first interaction in `next_step`. This adjacency rule compares flow
neighbors regardless of target or gesture. The within-step repeated exact
`(target, gesture)` rule above is stricter: every occurrence of that pair uses
distinct normalized instruction and hint values, even when occurrences are
separated by another interaction.

The generator preserves the required authored guidance in the generated
interaction data. The protocol runtime projects that pair into the active
interaction view with the current ordinal, resolved placement, learner label,
gesture, and any safe adjustment value. The shell renders that projection only
and does not infer or supply a next action from response state or object-field
names.

This is a breaking pre-production migration: existing authored interactions
without both guidance fields must be updated before validation; no compatibility
default or generic runtime fallback exists.

For every clickable placement, build-time layout emits a derived interaction
envelope and validates it at the scene's derived minimum 16:9 frame. The frame
guarantees a 44 CSS-pixel hit core, envelope containment, and no positive-area
overlap between clickable envelopes. The generated frame and envelopes are the
runtime source of truth: the host reserves the frame and the renderer exposes
the transparent delegated envelope without resizing scientific artwork. This
does not add authored YAML fields or alter the closed interaction vocabulary.

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
`BadAuthoredValueError`. Numeric values must also satisfy the field's declared
`min`, `max`, and `step`; a protocol cannot, for example, set a P200 below its
20 uL minimum. The YAML content validator enforces the same numeric constraint
before generation. This is a startup guard, not a new authored YAML field.
Authors add nothing; bad values simply fail loudly before or when the protocol
first loads rather than silently during a student session.

## Targets and the scene boundary

A `target` is the addressable, semantic scene object or control a student acts
on. It is named, not positional. Protocol YAML is geometry-free: it names no
coordinate. A scene adapter holds a registry that maps each semantic `target`
name to a concrete scene object. Interactive targets are one object or one
declared subpart (for example `treatment_plate.A1`); an interaction never fans
out to a group. See [specs/SCENE_VOCABULARY.md](specs/SCENE_VOCABULARY.md) for
the scene side of this boundary.

- Scientific SVG assets must never be cropped or aspect-distorted in display. See [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md) and [specs/SVG_PIPELINE.md](specs/SVG_PIPELINE.md).

## Initial session state

`initial_state` is an optional root protocol field that declares state needed
before the entry interaction. It is a list of entries with exactly `target` and
`state`:

```yaml
initial_state:
  - target: microtube_rack_8.slot_A1
    state:
      material_name: protein_sample_raw
      material_volume: 21
```

The target may name one object, one declared subpart, or one declared
`subpart_group`. A group expands to its declared concrete subparts before the
seed is checked and applied. Two entries that resolve to the same concrete
target identity are an error, including repeated entries or group/member
duplication. An object target and one of its subpart targets are distinct
identities and may both be seeded.

`state` is a non-empty flat mapping. Every key must be a declared state field
for the resolved object or subpart; values must have the declared primitive
type, satisfy numeric range and unit constraints, and satisfy enum closure.
For object-level writes, enum fields, including material identity when declared
at object level, use the object's closed `allowed` list. For subpart
`material_name` or `held_material_name`, the material identity is instead
registry-backed: it must be `empty`, `mixed`, or a material registered by the
active protocol. All other subpart enum fields retain their declared enum
check. This does not create an untyped state escape hatch.

The runtime begins one fresh session by validating and applying the root seed
to its durable target-keyed declared-state archive, then projects the
active scene reactively from that archive. Scene changes reconcile the active
projection without deleting archived state for objects not currently visible;
later writes update both. Restart clears the archive and begins again from the
same root seed. `initial_state` is optional and does not replace object defaults
for targets it does not name.

## Events

Events are emitted by the runtime on a state transition, not hand-authored per step. The runtime emits a `<step_name>_complete` event when a step's `step_validator` passes, and a `<equipment_name>_elapsed` event when a timed phase ends. Event names are snake_case and derived from the `step_name` or equipment name of the thing they report; an author who renames a step renames its completion event with it.

## Sequence runners

A sequence runner is a protocol with `protocol_type: sequence_runner`. It
declares a non-empty ordered list of unique direct `mini_protocol` leaves in
place of authored steps. Every name must resolve; nested runners and repeated
constituents are errors. A runner has its own `entry_step` (matching the first
mini-protocol's `entry_step`) and a `learning` block scoped to the overall
pathway.

The runner root is the one session boundary. If the runner declares
`initial_state`, it is the only seed applied to its flattened run. A constituent
mini-protocol's `initial_state` is ignored while it is executed by a runner;
that mini seed applies only when the mini-protocol is launched directly. This
prevents a later constituent from silently resetting previously produced state.

## Walker requirement

The walker is a runtime verifier generated from the protocol and scene YAML.

The walker:

- loads the page normally, including the welcome screen;
- starts in the scene reached by the protocol's `entry_step` (resolved through that step's target adapter or a `SceneChange` operation);
- clicks visible objects, buttons, modal controls, and answer choices;
- saves screenshots before and after each meaningful interaction;
- may read game state for verification.

Before a directed action, the walker proves that the exact target is visible,
in the viewport, and has a painted active affordance with a matching visible
action cue. An exact subpart target must expose a target core at least 24 by 24
CSS pixels. A declared subpart-group target exposes every concrete member as a
painted, learner-sized surface with the group identity; nonmembers retain their
exact identities for rejection, while an all-member group is recorded as having
no false sibling to probe. The walker records the visible interaction ordinal plus
`stateRevision` and `lastStateDelta` before and after each checkpoint. During a
wrong-order pass it clicks one visible actionable sibling rather than the
required target and proves that the runtime rejects it without advancing.
Timed waits show an explanatory rail and scene timer for a 0.3-0.6 second
browser acknowledgement before the next interaction becomes active.

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

## Persistence schema version

The browser now persists student progress across page loads. This is the first downstream consumer whose stored shape can drift from current source, so the repo has exactly one persistence schema version.

Rules:

- No `schema_version`, `spec_version`, or equivalent field in any authored YAML file.
- `src/schema_version.ts` owns the sole repo-wide `SCHEMA_VERSION` constant. There are no per-surface constants such as `OBJECT_SCHEMA_VERSION`, `PROTOCOL_SCHEMA_VERSION`, or `SCENE_SCHEMA_VERSION`.
- No version tokens in test, validator, or generator filenames (no `_v3_`, `_v5_`, `_v7_`). Tests are named for the behavior under test, not for the spec revision that introduced it.
- The repo `VERSION` remains the release identifier. A breaking persistence-shape change increments `SCHEMA_VERSION` and is recorded in `docs/CHANGELOG.md`; it does not add another version domain.
- All protocol sessions live under the one `virtual_lab.protocol_sessions` localStorage root. The root carries `schema_version`; entries are keyed by protocol name rather than spread across independently versioned keys.
- Every saved session carries a fingerprint of the flattened protocol's reachable step and interaction shape. A schema mismatch or fingerprint mismatch invalidates that session rather than restoring progress against different content.
- Persisted JSON is untrusted input. The loader validates the root, machine checkpoint, declared object state, cursor state, revisions, and exact reachable flow before restoration. Any invalid record is discarded cleanly and the protocol starts fresh.
- A save is written only at a stable step-machine checkpoint after an accepted interaction's synchronous response operations and transition have settled. A reload therefore restores the same next action and scientific state the student last saw.
- `generated/` remains rebuilt from source and carries no independent version counter.
