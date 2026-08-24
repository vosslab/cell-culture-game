# Protocol vocabulary

This document is the canonical vocabulary for protocol authoring,
runtime code, tests, and documentation in this repository. Every
protocol-related doc, code comment, error message, validator
output, and authoring guide must use these exact terms with
these exact meanings.

Related docs:

- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md)
- [PROTOCOL_STEPS.md](PROTOCOL_STEPS.md)
- [PROTOCOL_AUTHORING_GUIDE.md](PROTOCOL_AUTHORING_GUIDE.md)
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) -- the scene-side
  vocabulary; the scene-vs-protocol boundary section below
  cross-references it.
- [../CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md)

## Protocol kinds

Every authored protocol YAML file declares a top-level
`protocol_type` field. The value is drawn from a closed enum. The
authored kinds, and the structural terms that surround them, are:

- **Protocol package** -- the folder under
  `content/protocols/<cluster>/<name>/` that holds `protocol.yaml`,
  `materials.yaml`, and `scenes/`. A structural unit, not a
  `protocol_type` value.
- **Mini-protocol** (`protocol_type: mini_protocol`) -- one
  authored student-facing workflow with normal steps, a `learning`
  block, scenes, materials, and referenced objects. Scope is set by
  its `learning` block. Step count is determined by pedagogy. Each
  step is one pedagogical unit per learning block. Over-atomization
  (UI-shortcut steps) and under-atomization (multi-skill steps) are
  review-gated, not count-gated.
- **Sequence runner** (`protocol_type: sequence_runner`) -- an
  ordered pathway that connects mini-protocols into a larger
  student-facing sequence. Declares a non-empty, unique list of direct
  mini-protocol leaves in place of authored steps. Nested runners and repeated
  leaves are invalid. May be rendered in student-facing content as "full
  protocol".

The bare word "protocol" is not a formal kind or enum value.
Precise terms (`protocol.yaml`, protocol package, protocol-level
field, `protocol_type`, mini-protocol, sequence runner) stay valid
and are preferred in schema and file-structure contexts. There is
no `protocol_type: protocol` value.

## The two-level model

The model is a tight linear protocol spec with three nested levels:
`protocol`, `step`, and `interaction`. A `step` wraps an ordered
`sequence` of interactions. Each interaction is one `gesture` on one
`target`, checked by its own `validator`, with its own `response`.

The full shape:

```
protocol
  protocol_type           # one of mini_protocol, sequence_runner
  protocol_name           # stable snake_case identifier for this protocol
  entry_step              # step_name of the first step
  steps[]                 # the steps that make up the protocol
step
  step_name               # stable snake_case identifier for this step
  prompt                  # what the student is asked to accomplish
  sequence[]              # ordered list of interactions; order always matters
    interaction
      target              # the addressable scene object or control
      gesture             # how the student acts on the target
      validator           # named preset: checks this gesture on this target
      instruction         # required non-empty plain-string next-action guidance
      hint                # required non-empty plain-string disclosed guidance
      response            # container: scene_operations, optional feedback
  step_validator          # named preset: checks whole-step completion
  outcome                 # mapping: on_success, on_failure
  next_step               # names the next step by its step_name, or null
```

A `step` is one pedagogical unit -- one thing the student is asked
to accomplish. A step is often multi-gesture. "Wash the flask with
4 mL PBS" is a single step, but completing it takes three gestures:
click the pipette, click the PBS source, click the flask. The
two-level model exists so the step stays the pedagogical unit while
the individual gestures live inside it in an ordered `sequence`.

### Initial session state

**Initial session state** is an optional root `initial_state` list that
establishes declared state before the entry interaction. Each entry is exactly
`{target, state}`. Its target names one object, one declared subpart, or one
declared `subpart_group`; a group expands to its concrete members before
validation. It is not an interaction target and never makes one learner action
apply to several objects.

The `state` mapping is non-empty and flat. Every field and value follows the
target's declared state schema, including primitive type, numeric range, unit,
and enum checks. Object-level material identity uses its declared enum. A
subpart `material_name` or `held_material_name` uses the active protocol
material registry plus `empty` and `mixed`; other subpart enums remain closed
by their declared enum. Resolved targets may not duplicate the same concrete
identity, including a group member; an object and its subpart are distinct. The
runtime stores the resulting state in one durable target-keyed archive and
reactively projects the current scene from it. Scene reconciliation preserves
the archive; Restart clears it and reapplies the root seed.

For a direct mini-protocol launch, the mini-protocol root is the session seed.
For a sequence runner launch, the runner root is the only seed. A constituent
mini-protocol's `initial_state` is not applied when that mini runs within the
runner.

### Required slots

- A `protocol` requires `protocol_type`, `protocol_name`, `entry_step`,
  and `steps`.
- All six `step` slots are required: `step_name`, `prompt`, `sequence`,
  `step_validator`, `outcome`, `next_step`. `next_step` may be
  `null` for a terminal step, but the slot must be present.
- Six `interaction` slots are required: `target`, `gesture`, `instruction`,
  `hint`, `validator`, and `response`. The guidance fields are non-empty plain
  strings authored for every interaction.
- `response.scene_operations` is required (it may be an empty
  list); `response.feedback` is optional.
- A `scene_operation` requires `type` plus that type's documented
  typed fields.

The `interaction` has six declared keys, all required: `target`, `gesture`,
`instruction`, `hint`, `validator`, and `response`.
There is no separate interaction
task-type slot -- the target's `kind` carries the task semantics.
Interactions are not addressable by name.

### The `protocol` level

A `protocol` is the top level. It wraps the whole linear sequence
of steps and has four slots:

- **`protocol_type`** -- the kind of protocol authored. A closed
  enum: one of `mini_protocol` or `sequence_runner`.
  See [Protocol kinds](#protocol-kinds) for definitions.
- **`protocol_name`** -- a stable snake_case identifier for the protocol,
  for example `protocol_name: cell_culture`.
- **`entry_step`** -- the `step_name` of the first step the runtime
  runs. Flow starts here and follows `next_step` from step to step.
- **`steps`** -- the list of steps. List order is reading
  convenience only; protocol flow is `entry_step` plus `next_step`,
  never `steps` list order.

The `protocol` level exists so flow has a defined start. Without
`entry_step`, the first step would be implied by file order, and
file order is never flow.

### The interaction chain

Within a step, the chain runs:

1. The student performs a `gesture` on a `target`. That pair is one
   `interaction`.
2. The interaction's `validator` -- a named preset -- checks that
   one gesture on that one target: was the right gesture done on
   the right target?
3. A valid interaction fires its `response`: the scene operations
   the gesture causes plus optional feedback.
4. The step's interactions run in `sequence` order. When the
   sequence is satisfied, the step's `step_validator` -- also a
   named preset -- checks whole-step completion.
5. The `step_validator` result drives the `outcome` mapping:
   `on_success` resolves the step, `on_failure` retries the whole
   step (the entire `sequence` resets). Once the step resolves,
   `next_step` names which step runs next. Advancing is not an
   `outcome` value.

### Guidance progression

After every accepted interaction that has a successor in reachable flow, the
runtime advances the visible `instruction` and any already-open `hint`
together to the next authored pair. Adjacent authored interactions in
reachable flow therefore use distinct normalized `instruction` and `hint`
text, including the boundary between a step's final interaction and the first
interaction in `next_step`. This adjacency rule compares flow neighbors
regardless of target or gesture. The content validator applies a stricter
rule within each step: every repeated exact `(target, gesture)` pair uses
distinct normalized instruction and hint values, even when those occurrences
are separated by another interaction.

### Slot charters

Each slot owns one concern.

| Level       | Slot             | Charter                                                                                               |
| ----------- | ---------------- | ----------------------------------------------------------------------------------------------------- |
| protocol    | `protocol_type`  | The kind of protocol authored: one of `mini_protocol`, `sequence_runner`. Closed enum.                |
| protocol    | `protocol_name`  | The stable snake_case identifier for the protocol.                                                    |
| protocol    | `entry_step`     | Names the first step by its `step_name`; flow starts here.                                            |
| protocol    | `steps`          | The list of steps; list order is not protocol flow.                                                   |
| step        | `step_name`      | The stable snake_case identifier for the step, used for flow, tests, and debugging.                   |
| step        | `prompt`         | States what the student is asked to accomplish in this step.                                          |
| step        | `sequence`       | The ordered list of interactions that make up the step; order always matters.                         |
| step        | `step_validator` | Named preset that checks whole-step completion, not one gesture.                                      |
| step        | `outcome`        | A mapping that says how the step resolves: `on_success` and `on_failure`.                             |
| step        | `next_step`      | Names the next step by its `step_name`, or `null` for a terminal step; this controls protocol flow.   |
| interaction | `target`         | Names the addressable scene object or control acted on.                                               |
| interaction | `gesture`        | Names how the student acts on the target.                                                             |
| interaction | `instruction`    | Required non-empty plain-string primary next-action guidance authored for this interaction.           |
| interaction | `hint`           | Required non-empty plain-string disclosed next-action guidance authored for this interaction.         |
| interaction | `validator`      | Named preset that checks this one gesture on this one target.                                         |
| interaction | `response`       | Container for post-validation system behavior: `scene_operations` and optional structured `feedback`. |

## Step naming and protocol flow

- **`step_name` is the stable identifier.** Every step has a `step_name`:
  a stable snake_case semantic identifier, for example
  `step_name: pbs_wash`. It is chosen for meaning, not for position. It
  is the step's stable reference for protocol flow, tests,
  debugging, and future code migration.
- **`next_step` controls flow.** A step's `next_step` slot names
  the next step by its `step_name`, for example `next_step: add_trypsin`.
  Flow does not come from YAML file order and does not come from a
  numeric index.
- **`next_step: null` is a terminal step.** A step with
  `next_step: null` has no successor; the protocol ends when it
  resolves. The slot is always present; `null` is its terminal
  value.
- **YAML file order is not flow.** Reordering step blocks in the
  YAML must not change protocol flow. Flow is `entry_step` plus
  `next_step` only. A `step_index` may exist for display order
  only -- it is not part of the protocol-flow spec and never
  controls flow.
- **`outcome` has no `advance`.** Advancing to the next step is
  `next_step`'s job. `outcome` never carries an `advance` value and
  never names a step.

### Sequence ordering

- **`sequence` order is always meaningful.** The interactions in a
  step's `sequence` run and validate in the order listed -- always.
  There is no unordered mode.
- **Step order and interaction order do not mix.** Step order is
  controlled by `next_step`. Interaction order is controlled by
  `sequence` list order.
- **All authored names are snake_case.** The `step_name`, the
  `protocol_name`, `entry_step` targets, and `next_step` targets
  are always snake_case. Every YAML key and every authored
  identifier value is snake_case. The only exception is the six
  `scene_operation` primitive type names, which stay PascalCase
  because they are class-like type names used as the value of the
  `type` field.

## The `target` slot

A `target` is the addressable, semantic scene object or control the
student acts on. It is named, not positional: the runtime tracks
named scene objects (`serological_pipette`, `pbs_bottle`, `flask`,
`incubator`, a specific answer choice), not coordinate regions or
response variables. A protocol author writes the target's name; the
scene adapter owns where that object is and how it is drawn.

### A target declares its kind

A target declares its `kind`. The kind says what sort of thing the
target is and, with that, what acting on it means. A liquid-handling
tool, a reagent source, a destination vessel, a piece of timed
equipment, a popup control, an answer choice -- each is a target
kind. The kind is the target's stable semantic type.

### The kind carries the task semantics

Because the target's kind carries the task semantics, the model
needs no separate interaction task-type slot. The work a gesture
does is determined by the gesture plus the kind of target it lands
on. Clicking a reagent-source target means "draw from this
source"; clicking a destination-vessel target means "dispense into
this destination"; clicking an answer-choice target means "select
this answer". The author does not also tag the interaction with a
task type -- the target's kind already says it.

This is why this doc does not name `plate target` or `tube target`.
Those were scene-specific task-type metadata. The target's kind
plus the gesture carries the task semantics with no plate- or
tube-shaped slot.

## The `gesture` slot

A `gesture` is how the student acts on a target. It is the physical
input the student performs. The gesture value set is closed:

| Gesture  | What the student does                                                                                                                                                |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `click`  | Clicks the target. The simple, discrete gesture.                                                                                                                     |
| `drag`   | Drags the target, or drags from the target to another target.                                                                                                        |
| `adjust` | Moves a continuous control to a set-point value. The skill-based gesture.                                                                                            |
| `select` | Chooses the next-step object among the scene objects already present. The primary way a student drives a protocol; reuses the visible scene-object click affordance. |
| `type`   | Enters a value or text into a visible input and commits it.                                                                                                          |

For the current cross-layer implementation status, compositional `click`
flavors, and the explicitly reopened `select` question, see
`docs/specs/GESTURE_MODEL.md`. That status reference does not alter the closed
vocabulary in this document.

### `adjust` is the skill-based set-point gesture

`adjust` is the continuous, skill-based set-point gesture. The student moves
an adjustable control until it reaches a target value: a micropipette or
repeating-dispenser volume, a power-supply voltage, or a pH titrated to a
target. Loading a graduated serological pipette is not a digital set-point
operation. Collapsing an adjustable setting
into a `click` teaches the student nothing about volume set-points.
`adjust` keeps skill-based parameter-setting from collapsing into
`click`.

### `select` versus `click`

`select` and `click` are kept distinct:

- `click` is acting on a specific scene object the step already
  directs the student to -- a pipette, a bottle, an incubator. The
  target is a single thing in the world to act on.
- `select` is choosing the correct next-step object among the scene
  objects already present. The selectable set is simply the
  clickable scene objects already rendered (each carries its own
  `data-item-id`); there is no separate answer-choice list, no modal,
  and no choice identifier. Selecting the interaction's `target`
  advances; selecting any other present object is rejected (the same
  discipline as a wrong-order click) and does not advance.

`select` reuses the same visible scene-object click affordance as
`click`; the runtime promotes a click on the active target to the
active `select` gesture. The author's intent differs (choosing among
present objects vs. acting on one directed object), so the two
gestures stay separate even though the affordance is shared. For
`select`, the renderer shows equal candidate rings on all clickable
objects and never singles out the correct answer; see
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md#interaction-affordance) "Interaction affordance".

### The gesture extension rule

The gesture value set is closed but extensible. A new gesture may
be added only when the evidence shows a student input that none of
`click`, `drag`, `adjust`, `select`, or `type` expresses, that the
input recurs across more than one protocol, and that it is a
stable, reusable input shape. Adding a gesture requires the same
justification as adding a base primitive (see the cost guardrail
below).

## The pedagogy-first rule

The `target` and `gesture` slots are not just UI plumbing. They are
a pedagogical choice. The rule:

**An author chooses each interaction's `target` (and its `kind`)
and its `gesture` so the interaction teaches the specific lab skill
the step is about. The shape of an interaction is a pedagogical
decision, not just a UI decision.**

The `kind` plus the `gesture` determine what the interaction
teaches:

- `adjust` on a continuous control teaches a **set-point skill**.
- `click` on a scene object teaches **recognition and sequencing**.
- `select` on the correct next-step object among the present objects
  teaches a **decision**.
- `drag` on a scene object teaches a **spatial placement** skill.
- `type` on a control teaches **entering a precise value**.

### The anti-pattern: collapsing a skill into a rote click

The anti-pattern this rule exists to catch is collapsing a skill-based
interaction into a rote `click`. The clearest case is setting an adjustable
micropipette or repeating dispenser: encoding that setting as a timed `click`
or a plain `click` with no set point teaches nothing about volume control.
Shipped liquid-handling steps that encode an adjustable setting as a field on
a `click` with no `adjust` gesture do not match the ratified vocabulary. The
correct shape is `gesture: adjust` on the adjustable tool target, validated by
`target_with_value` with the set-point value. A serological pipette is loaded
to a graduation and represents that transfer through explicit material state.

An interaction whose `target`/`gesture` pairing does not match its
step's skill is a vocabulary violation, not an author preference.

## The `response` container

A `response` is the interaction's sixth slot. It is the container
for post-validation system behavior -- what the system does after
an interaction is validated. It is not itself a primitive: it holds
primitives. A `response` has exactly two fields:

| Field              | Required           | What it holds                                                                 |
| ------------------ | ------------------ | ----------------------------------------------------------------------------- |
| `scene_operations` | yes (may be empty) | An ordered list of typed `scene_operation` primitives.                        |
| `feedback`         | no                 | Optional learner-facing messaging, structured into `correct` and `incorrect`. |

The canonical shape of a `response`:

```yaml
response:
  scene_operations:
    - type: CursorAttach
      target: serological_pipette
      operation: attach
    - type: ObjectStateChange
      target: serological_pipette
      state:
        held_material_name: pbs
        held_material_volume: 4
  feedback:
    correct: PBS loaded.
    incorrect: Use the PBS bottle.
```

### Why `response` is broader than a scene effect

A validated interaction does not always change the scene. It can be
`feedback` only (a correct multiple-choice answer with an empty
`scene_operations` list), a modal open or close, or a full scene
mutation. `response` is the broad container; `scene_operation` is
the narrow typed layer inside it.

### `scene_operations`

`scene_operations` is an ordered list of typed `scene_operation`
primitives. It may be empty. Order matters: the runtime applies the
list top to bottom, so the pipette-empty operation must precede the
flask-fill operation when one liquid moves between two objects.

### `feedback`

`feedback` is optional learner-facing messaging tied to this one
interaction. It is structured into two sub-keys: `correct`, the
message shown when the interaction validates, and `incorrect`, the
corrective hint shown when it does not. It carries no scene effect;
anything visible in the scene belongs in `scene_operations`.

### State change is explicit only

State change is **explicit in a `response` via a `scene_operation`
mutation only.** In the ratified tight spec, `response` has two
fields: `scene_operations` and optional `feedback`. Additional
bookkeeping paths require a future evidence-gated vocabulary
update. If a protocol later proves it needs
non-visual bookkeeping no `scene_operation` can carry, that is
evidence for a future plan under the cost guardrail; the tight spec
does not assume it.

## Scene operation primitives

A `scene_operation` is one of a small, ratified set of typed
primitives. Each is the smallest protocol-visible scene effect the
runtime guarantees across every scene. `scene_operation` primitives
**describe how the scene changes, not what the learner does**: the
learner acts with a `gesture` on a `target`; the `scene_operation`
is what the scene does in response.

### The five ratified primitives

Five `scene_operation` primitives are ratified at the protocol
level. Each is named with its typed fields.

Four reclassified primitives were moved out of the protocol-level set
into the object/render layer: `SvgSwap` and `ColorChange` are
render-layer mechanisms named by the object's `visual_states`.
`LiquidDisplayChange` and `SetPointDisplayChange` are also reclassified
the same way: the protocol writes semantic state through `ObjectStateChange`
against the object's flat declared liquid and set-point `state_fields`,
and the object's `visual_states` resolves how they appear. The protocol stays
semantic and never names an SVG asset id, a color value, a liquid display
update, or a set-point display update. See [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
The semantic primitive that supersedes all four at the protocol level is
`ObjectStateChange`, which writes the flat declared liquid fields (`material_name` and
`material_volume` for vessels and wells; corresponding
`held_material_name` / `held_material_volume` for tools) and the flat
declared set-point fields (`set_volume`, `set_temperature`,
`set_rpm`, etc.).

| Primitive           | Typed fields                                                                                                                         | One-line meaning                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ObjectStateChange` | `type`, `target`, `state` (a flat mapping of `state_field` name to primitive value), optional `transition` (`instant` or `animated`) | Semantic state change: sets one or more declared `state_fields` on a target object or subpart. The object's `visual_states` resolves the new state to a visual; the protocol does not name the visual. A protocol that acts on several subparts emits one `ObjectStateChange` per subpart. This is the sole protocol primitive for liquid state mutation; write the flat declared liquid fields and let the object's `visual_states` resolve the visual. This primitive changes what the simulation IS (declared state), not how it LOOKS.                                                                                                                                                                       |
| `CursorAttach`      | `type`, `target`, `operation` (`attach` or `detach`)                                                                                 | Semantic state change: sets the runtime's held-material state -- "the learner is now holding this object instance" (`attach`) or "the learner is no longer holding it" (`detach`). It must not be read as "draw the object under the cursor"; the cursor-follow visual is rendered by the scene / object-render layer in response to the held-material state change. This primitive changes what the simulation IS (held material), not how it LOOKS.                                                                                                                                                                                                                                                            |
| `SceneChange`       | `type`, `to_scene`                                                                                                                   | Semantic state change: transitions the runtime's active scene id to another scene. The protocol names which scene; the scene-runtime renders the transition. This primitive changes what the simulation IS (the active scene), not how it LOOKS.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `LayoutMove`        | `type`, `target`, `to_slot` (and optional `to_scene` for cross-scene transitions)                                                    | Ratified semantic placement change: names an existing placement and its destination without encoding animation timing, pixel coordinates, layout rules, or visual motion. It is not executable in the current runtime: every `LayoutMove` dispatch throws because the layout engine exposes no placement-override write surface. It therefore cannot yet reposition an object or perform a cross-scene move. The primitive remains in the closed vocabulary; executable support requires that write surface.                                                                                                                                                                                                     |
| `TimedWait`         | `type`, `target`, `duration_min`, `display`                                                                                          | Semantic state change: advances the runtime's equipment-state for the named target -- the timed phase starts and then elapses. It must not be read as "show a spinner" or "render a progress bar"; the visible progress display is owned by the object's `visual_states` over the equipment's declared timed-phase state. The protocol names what equipment, for how long, and what timed condition is satisfied; the object / render layer renders the display. The `display` field is an authoring hint to the render layer about display style, not a protocol-side appearance knob and never an SVG asset id. This primitive changes what the simulation IS (the equipment's timed phase), not how it LOOKS. |

The liquid display path and the set-point display path both moved to the
object's `visual_states`; there is no longer a display-change family at the
protocol level.

### `ObjectStateChange` is the semantic state-mutation primitive

`ObjectStateChange` is the only protocol primitive that writes into
declared object `state_fields`. The protocol names a `target` (an
object name, or a subpart reference such as `treatment_plate.A1`) and
a `state` mapping of `state_field` name to value. A protocol that
acts on several subparts emits one `ObjectStateChange` per subpart. The object's `visual_states` resolves
the new state value to a visual asset; the protocol never names an
SVG asset id and never names a color value.

`ObjectStateChange` is flat-field-only: it targets a declared
`state_field` by name and provides a value matching that field's
primitive type (`enum`, `int`, `float`, or `bool`). Nested writes are
not allowed. The validator rejects unknown field names and
type-mismatched values. Example payload (well A1 receives 100 ul
of PBS):

```yaml
- type: ObjectStateChange
  target: treatment_plate.A1
  state:
    material_name: pbs
    material_volume: 100
```

The earlier nested form `state: { held_liquid: { reagent: pbs,
volume: 100 } }` is not valid. See
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) for the `state_fields`
schema and the `visual_states` resolution rule.

### Liquid state mutation uses `ObjectStateChange`

Liquid state mutation is expressed through `ObjectStateChange` against
the object's flat declared liquid fields. Tools and vessels declare those
fields directly (typically `material_name` and `material_volume`
for vessels and wells; `held_material_name` and `held_material_volume` for tools).
The `visual_states` resolves the new field values to a fill height, tint, and asset.

Object-level material fields use the object's declared material enum. A
structured subpart's `material_name` or `held_material_name` uses the active
protocol material registry plus `empty` and `mixed`, because shared structured
objects deliberately declare only their sentinel enum floor. Other subpart enum
fields still use their declared enum.

Each liquid state change maps to a flat-field write:

- `hold` (a tool drawing liquid) -- write the tool's
  `held_material_name` and `held_material_volume` to the new values.
- `set` (assigning a target's material directly, including emptying
  with `volume_ml: 0`) -- write the target's `material_name` to the new
  reagent (or `null` / the empty enum value) and `material_volume` to
  the new value.
- `add` (a destination receiving a transfer on top of existing
  material) -- emit one `ObjectStateChange` for the new total. The
  protocol computes the resulting volume; the object owns no
  add-versus-set distinction at the render layer.

### The set is closed but extensible

The five primitives are a closed but extensible set, governed by
the cost guardrail below. Instrument-produced data (a cell count, an
absorbance value, a gel band pattern) has no `scene_operation` that
records it as runtime state. Instrument-produced data stays
`feedback`-only.

## Domain verbs

A domain verb is an author-facing named composition over the
two-level model. `grind`, `draw`, `dispense`, `assemble`, `wash` --
these are the words a YAML author actually writes. A domain verb is
**authoring vocabulary, not base vocabulary**: it expands to slots
that are already defined, and it adds no new runtime concept.

### The composition rule

A domain verb expands at one of the two levels:

- An **interaction-level** domain verb expands to **one
  interaction** -- one `target`, one `gesture`, one `validator`,
  one `response`.
- A **step-level** domain verb expands to a **whole `sequence` plus
  its `step_validator`** -- several interactions and the whole-step
  check.

Each domain verb has a documented expansion. The expansion is the
verb's definition; there is nothing to a domain verb except the
slots it expands to.

### A domain verb implies no hidden state change

A domain verb implies **no hidden state change**. All state change
is explicit in a `response` as a `scene_operation` mutation. A
domain verb never reaches past the `response` container to mutate
runtime state on the side. If a verb appears to need a side effect,
that side effect must surface as a `scene_operation` in one of the
interactions the verb expands to. A verb that cannot be expressed
as the two-level model is itself evidence the model is missing
something -- it is a finding to escalate, not a special case to
code around.

### Ratified domain verbs

The baseline interaction-level verbs are `draw`, `dispense`, `grind`,
`aspirate`, `pour`, `mix`, `spray`, `move`, `use` (equipment),
`navigate`, and `select` (answer). The baseline step-level verbs are
`wash` and `assemble`. Additional cheap verbs include `titrate`,
`dissect`, `place`, `clamp`, `unwrap`, `remove`, `open`, `connect`,
`image`, `set`, `stain`, and `destain`, each with a documented
expansion. New domain verbs are the cheap, expected layer: authors
add them with documented expansions as their protocols read naturally.

## Cost guardrail

The three layers have different costs to extend, and the difference
is deliberate.

| Layer                       | Cost to add | Bar to clear                                                                                                                  |
| --------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Domain verb                 | Cheap       | A documented expansion to existing slots.                                                                                     |
| `gesture` value             | Expensive   | Evidence: a recurring input shape no current gesture expresses.                                                               |
| `scene_operation` primitive | Expensive   | Evidence: a recurring scene effect no composition of existing primitives expresses.                                           |
| Validator preset            | Expensive   | Evidence: a recurring validation shape no existing preset expresses.                                                          |
| `protocol_type` value       | Expensive   | Evidence: a recurring authoring shape no existing kind expresses. Closed enum; same bar as a new `scene_operation` primitive. |

New domain verbs are cheap and expected. New `gesture` values, new
`scene_operation` primitives, and new validator presets are
expensive: each is a permanent addition to the base vocabulary and
requires evidence -- a recurring shape, across more than one
protocol, that no existing primitive or composition expresses. The
cheap layer is cheap precisely because it cannot smuggle in
expensive behavior.

## No template-protocol layer

Protocols are spec-shaped, not template-based. Protocols do not use
`extends`, and cross-protocol reuse is not via template inheritance.
Similarity across protocols comes from the shared `learning -> steps ->
sequence -> interaction -> response` structure itself, not from
copied templates. When reusing an entire protocol as part of a larger
pathway, use the `sequence_runner` composition form already specified
in [../PRIMARY_SPEC.md](../PRIMARY_SPEC.md). Reopening this design
decision (for example, adding protocol-level `extends`) is a separate
ratified decision, not an implicit extension point. See the asymmetry
rationale in [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for why
protocols, objects, and scenes differ in this regard.

## The validator and state model

There are two validation scopes: the per-gesture interaction
`validator` and the whole-step `step_validator`. Both are named
presets with typed parameters.

### Validators are named presets

Every `validator` and every `step_validator` is a **named preset
with typed parameters**:

```yaml
validator: { preset: <name>, ...typed params }
```

A validator is never free-form prose, never an inline expression,
and never a raw structured object the author writes by hand.
Content creators select from the documented preset library below;
they never write custom validation logic. A new preset requires
ratification evidence -- the same cost-guardrail discipline as a
new `scene_operation` primitive.

### The interaction `validator`

The interaction `validator` judges one interaction: did the student
perform the correct `gesture` on the correct `target`. It is narrow
on purpose -- one gesture, one target, one yes-or-no result. It
checks **local correctness only** and does not look at the rest of
the sequence; it does not check the final state of the step. A true
result fires the interaction's `response`; a false result does not,
and drives the step's `outcome.on_failure`.

### The `step_validator`

The `step_validator` judges the whole step: did the step reach its
intended completion. It runs only after every interaction in the
`sequence` has fired its `validator` and the runtime has applied
each `response`. It checks **only whole-step completion**: it does
not re-run the interaction validators. A step can have every
interaction validate and still fail a `final_state_matches`
`step_validator` if the sequence added up wrong -- that is exactly
the wide check the `step_validator` exists for.

The two scopes are deliberate and separate: the interaction
`validator` answers "did the student do this one part right", the
`step_validator` answers "did the step complete".

### The validator preset library

The initial preset library has five presets: three interaction
presets and two step presets.

| Preset                | Scope                        | Required fields                                                     | What it checks                                                                                                                                                                                                                                                                                                                                              |
| --------------------- | ---------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `correct_target`      | interaction `validator` only | `preset`                                                            | The student performed the interaction's `gesture` on the interaction's `target`.                                                                                                                                                                                                                                                                            |
| `correct_choice`      | interaction `validator` only | `preset`                                                            | The student selected the correct next-step object: the selected scene object equals the interaction's `target` (target-equality). The selectable set is the clickable scene objects already present; there is no separate answer-choice list. Used by a `select`-gesture interaction.                                                                       |
| `target_with_value`   | interaction `validator` only | `preset`, `value` (a mapping of typed value keys)                   | The student performed the `gesture` on the `target` and the target reached the named `value` -- the preset an `adjust`- or `type`-gesture interaction uses. The value must satisfy the target field's declared type and numeric `min`, `max`, and `step`. For a `type` interaction the committed text is coerced to the declared value's type and compared. |
| `sequence_complete`   | `step_validator` only        | `preset`                                                            | Every interaction in the step's `sequence` validated, in order.                                                                                                                                                                                                                                                                                             |
| `final_state_matches` | `step_validator` only        | `preset`, `target`, `contains` (a mapping of expected target state) | After the sequence runs, the named `target` is in the state described by `contains`, regardless of the exact path.                                                                                                                                                                                                                                          |

Preset shapes in YAML:

```yaml
validator: { preset: correct_target }
validator: { preset: correct_choice }
validator: { preset: target_with_value, value: { volume_ml: 4 } }
step_validator: { preset: sequence_complete }
step_validator:
  preset: final_state_matches
  target: flask
  contains: { material_name: pbs, volume_ml: 4 }
```

New presets are added under the cost guardrail. Content creators
never write custom validation logic; they request a new preset
with evidence, and the preset is ratified into this library.

### The `outcome` slot

`outcome` is a **mapping**, not a bare scalar. It has exactly two
keys:

```yaml
outcome:
  on_success: complete
  on_failure: retry
```

| Key          | Meaning                                                                                                                                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `on_success` | What happens when the `step_validator` passes. `complete` resolves the step; flow then moves to `next_step`.                                                                                                                    |
| `on_failure` | What happens when the `step_validator` does not pass, or an interaction `validator` returned false. `retry` restarts the whole step -- the entire `sequence` resets and the student redoes the step from its first interaction. |

`outcome` is a mapping. The bare-scalar form `outcome: complete` is
rejected: it cannot say what happens on failure. The vocabulary has
no `on_hint_requested`, no `branches` mapping, and no adaptive review.

`outcome` does not advance the protocol. Advancing is `next_step`'s
job.

The iterative loop -- destaining until the background is clear --
is expressed as a `final_state_matches` `step_validator` plus an
`outcome.on_failure: retry`. While the named state is not reached,
`on_failure: retry` restarts the whole step. There is no separate
`repeat_until` construct and no separate loop step type.

### The runtime state model

The vocabulary assumes a small, named runtime state. Every
`validator` preset and every `step_validator` preset reads this
state; every state change is written by a `response`.

| State             | What it tracks                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| held material     | Which tool, if any, is attached to the cursor, and what liquid it carries.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| target material   | The tracked liquid identity and volume on each vessel and tool.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| set-point values  | The current value of a continuous control (a pipette volume, a power-supply voltage, a titration pH).                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| equipment state   | Whether a piece of equipment has run, and -- for timed equipment -- whether its timed phase has started and elapsed.                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| phase state       | A multi-phase result the student must resolve (a centrifuged tube holding an aqueous and an organic phase).                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| object appearance | Decomposed by the object-render-layer split: the asset id and color shown for each object are render-layer outputs of the object's `visual_states` over its declared `state_fields` (see [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)); the layout slot of each scene object stays scene-level placement. The protocol writes declared `state_fields` via `ObjectStateChange`; the ratified `LayoutMove` vocabulary names a layout-slot change, but current runtime dispatch throws before any layout state changes. The protocol never names an asset id or a color. |

This state is named and non-positional, the same as `target`: the
runtime tracks it by name. The scene adapter renders it; the
protocol vocabulary names the state, not the rendering.

Each `scene_operation` primitive maps to the runtime state it
changes:

| Primitive           | Runtime state it changes                                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `ObjectStateChange` | declared object `state_fields` -- the named, typed state variables an object owns; the object's `visual_states` resolves the value to a visual. |
| `CursorAttach`      | held material -- the cursor-attachment state of the target.                                                                                     |
| `SceneChange`       | the active scene id.                                                                                                                            |
| `LayoutMove`        | No current runtime state: dispatch throws before changing the target's layout slot.                                                             |
| `TimedWait`         | equipment state -- the target equipment's timed phase, started and then elapsed.                                                                |

The object's `visual_states` resolves declared `state_fields` to a
visual; see [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).

### The event-emission rule

- **The emission rule.** An event is emitted on a state transition
  the rest of the protocol may react to: an interaction firing a
  true `validator`, a step resolving `complete`, or a
  timed-equipment phase elapsing. Events are emitted by the
  runtime, not hand-authored per interaction. The runtime emits a
  `<step_name>_complete` event when the `step_validator` passes.
- **The naming convention.** Event names are snake_case, derived
  from the `step_name` or equipment name of the thing they report,
  suffixed with the transition: `<step_name>_complete` when a step
  resolves, `<equipment_name>_elapsed` when a timed phase ends. There
  is one convention; the legacy kebab-case and mixed forms are retired.

Event names are derived, not separately authored: because the
`step_name` and the equipment `target` name are already stable
snake_case identifiers, the event name follows from them. An author
who renames a step renames its completion event with it.

## The scene-vs-protocol boundary

This is the hard boundary between what the protocol vocabulary
names and what a scene adapter owns. It exists because of a
documented failure: PRIMARY_CONTRACT item 1 records that earlier
TypeScript was built around the hood scene and treated other scenes
as derivatives. The same failure reappeared one layer up -- the
shipped protocol vocabulary carried `plateTargets`, `tubeTargets`,
and the four-`kind` completion-path taxonomy, all of them
cell-culture-scene drift baked into what should be a scene-agnostic
protocol vocabulary. The boundary rule is the guardrail that keeps
that drift out. Removing `plate target` and `tube target` from this
canonical vocabulary is the direct result.

### The boundary rule

The quotable rule a doc reviewer and a YAML author both apply:

**The protocol vocabulary names no plate, no well, no tube, no gel,
no column, no lane, no rack, and no coordinate. It names semantic
targets, gestures, validators, and named runtime state. The scene
adapter owns all geometry, all target expansion, and how every
`gesture` is rendered and input. If a protocol YAML file contains a
geometric noun or a coordinate, that is a boundary violation -- the
geometry belongs on the scene side, addressed through a semantic
target name.**

Two consequences follow:

- **The protocol YAML is geometry-free.** No well coordinates, no
  `A1:A12` spans, no row or column ranges, no plate structure, no
  x/y. A protocol step that treats a row of wells writes one
  semantic target name; the scene resolves it.
- **The scene adapter is the only place geometry lives.** Where a
  target sits, how big it is, how a `gesture` is captured as input,
  how a set-point display is drawn, how a timed-wait progress bar
  animates -- all scene-adapter territory.

### Slot-by-slot ownership

| Level       | Slot             | Side     | What each side owns                                                         |
| ----------- | ---------------- | -------- | --------------------------------------------------------------------------- |
| protocol    | `protocol_name`  | protocol | The protocol's stable snake_case identifier.                                |
| protocol    | `entry_step`     | protocol | Names the first step; pure protocol flow.                                   |
| protocol    | `steps`          | protocol | The list of steps; pure protocol flow.                                      |
| step        | `step_name`      | protocol | The step's stable snake_case identifier.                                    |
| step        | `prompt`         | protocol | The student-facing instruction text.                                        |
| step        | `sequence`       | protocol | The ordered list of interactions; order is protocol-owned.                  |
| step        | `step_validator` | shared   | Protocol selects the preset; scene/runtime supplies the state it checks.    |
| step        | `outcome`        | protocol | The `on_success` / `on_failure` mapping; pure protocol flow.                |
| step        | `next_step`      | protocol | Names the next step; pure protocol flow.                                    |
| interaction | `target`         | shared   | Protocol names a semantic target; scene resolves it to geometry.            |
| interaction | `gesture`        | shared   | Protocol names the gesture; scene owns how it is rendered and input.        |
| interaction | `validator`      | shared   | Protocol selects the preset; scene/runtime supplies the state it checks.    |
| interaction | `response`       | shared   | Protocol names `scene_operations` and `feedback`; scene renders the effect. |

### Target resolution: adapter registry plus explicit subparts

How a protocol `target` resolves to a concrete scene object is the
adapter-registry plus explicit-subpart mechanism:

- **The adapter registry maps a `target` name to a scene object.**
  The scene adapter holds a registry that maps each semantic
  `target` name the protocol uses to a concrete scene object. The
  protocol writes `target: flask`; the adapter's registry resolves
  `flask` to the scene's flask object.
- **Grouped targets are listed explicitly.** The vocabulary has no
  named-group construct. A protocol that needs to act on several
  subparts -- a row of wells, a tube column, a set of gel lanes --
  emits one interaction per subpart, addressing each as
  `<object_name>.<subpart_name>` (for example `treatment_plate.A1`).
  The object's `id_pattern` (defined in
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)) is the only naming
  contract.
- **The protocol vocabulary stays geometry-free.** No ranges, no
  plate structure, no well coordinates in protocol YAML; only
  semantic object names and subpart names drawn from the object's
  declared `id_pattern`.

This explicit-subpart pattern is what replaces `plate target` and
`tube target`. Those fields pushed plate and tube geometry into the
protocol vocabulary; the protocol lists each addressable subpart by name.

Worked example -- which file owns which:

```yaml
# protocol YAML -- names semantic targets and flat-primitive state, no geometry
- step_name: add_media_row_b
  prompt: "Add 100 uL media to every well in row B."
  sequence:
    - target: serological_pipette
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: CursorAttach
            target: serological_pipette
            operation: attach
    - target: media_bottle
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: ObjectStateChange
            target: serological_pipette
            state:
              held_material_name: media
              held_material_volume: 1.2
    # The protocol lists each well in row B explicitly.
    # The pattern below repeats once per well B1..B12, dispensing
    # 0.1 mL into each. Twelve interactions are abbreviated for brevity.
    - target: treatment_plate.B1
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: ObjectStateChange
            target: treatment_plate.B1
            state:
              material_name: media
              material_volume: 100
  step_validator:
    preset: final_state_matches
    target: treatment_plate.B1
    contains: { material_name: media, material_volume: 100 }
  outcome:
    on_success: complete
    on_failure: retry
  next_step: add_media_row_c
```

The protocol YAML writes one interaction per subpart and never lists
a well coordinate or a row range. The object's `id_pattern` resolves
each `treatment_plate.<subpart_name>` reference; the scene YAML owns
where the plate is placed but never names subparts.

### The "click target" / `ClickTarget` collision

`PROTOCOL_VOCABULARY.md` once said "click target" and
`SCENE_VOCABULARY.md` says `ClickTarget`, with no cross-reference.
The resolution:

- **`target` is the protocol-side term.** A `target` is the
  semantic, geometry-free name a protocol author writes. This doc
  uses `target` for that concept and retires "click target"
  entirely. "Click target" was a UI/DOM-level phrase that never
  belonged in the protocol vocabulary.
- **`placement` is the scene-side term.** A `placement` is the
  concrete, geometry-bearing thing the adapter registry
  resolves a `target` name to. It is the scene-side authoring unit,
  canonical in [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).
- **`ClickTarget` is scoped to one narrow runtime type.**
  `ClickTarget` stays as the name of the specific `{itemId}` driver
  payload it denotes in [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md)
  -- a low-level click-event payload, not the addressable-object
  concept.

The single canonical split: a protocol names a **`target`**; the
scene adapter resolves that name to a **`placement`** (or a
named group of placements). This doc encodes the protocol-side
half. The scene-side half -- `placement` and the narrow
`ClickTarget` runtime type -- is owned by
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).

## Worked example: a multi-gesture step

"Wash the flask with 4 mL PBS" is one step. It is the canonical
multi-gesture case, shown here as one step inside a `protocol`'s
`steps` list:

```yaml
protocol:
  protocol_name: cell_culture
  entry_step: pbs_wash
  steps:
    - step_name: pbs_wash
      prompt: "Wash the flask with 4 mL PBS."
      sequence:
        - target: serological_pipette
          gesture: click
          validator: { preset: correct_target }
          response:
            # the pipette is picked up and follows the cursor
            scene_operations:
              - type: CursorAttach
                target: serological_pipette
                operation: attach
        - target: pbs_bottle
          gesture: click
          validator: { preset: correct_target }
          response:
            # 4 mL PBS is drawn into the held pipette; flat liquid
            # state_fields.
            scene_operations:
              - type: ObjectStateChange
                target: serological_pipette
                state:
                  held_material_name: pbs
                  held_material_volume: 4
            feedback:
              correct: PBS loaded.
              incorrect: Use the PBS bottle.
        - target: flask
          gesture: click
          validator: { preset: correct_target }
          response:
            # the PBS is dispensed from the pipette into the flask;
            # each side updates its own flat state_fields.
            scene_operations:
              - type: ObjectStateChange
                target: serological_pipette
                state:
                  held_material_name: null
                  held_material_volume: 0
              - type: ObjectStateChange
                target: flask
                state:
                  material_name: pbs
                  material_volume: 4
      step_validator:
        preset: final_state_matches
        target: flask
        contains:
          material_name: pbs
          material_volume: 4
      outcome:
        on_success: complete
        on_failure: retry
      next_step: add_trypsin
```

Reading the chain:

- One `protocol`, `name: cell_culture`, with `entry_step: pbs_wash`
  -- flow starts at the `pbs_wash` step.
- One `step`, `name: pbs_wash`, with one `prompt`. The student is
  asked to accomplish one thing.
- Three `interaction` entries in the `sequence`, each with required
  `target`, `gesture`, non-empty `instruction`, non-empty `hint`, `validator`,
  and `response` slots. Each guidance pair states its explicit authored next
  action and remains answer-safe for select and type attempts. Each is
  one `gesture` on one `target`.
- Each interaction has its own `validator` preset; `correct_target`
  checks just that gesture on just that target.
- Each interaction has its own `response`: `scene_operations` plus
  optional `feedback`. State change is explicit in the
  `scene_operation` mutations -- there is no `state_update` slot.
- After the three interactions run in order, the `step_validator`
  preset `final_state_matches` asserts the flask holds 4 mL PBS.
- The `outcome` mapping resolves the step on success and restarts
  the whole step on failure. Flow then moves to `next_step`:
  `add_trypsin`.

## Container terms

| Term                      | Definition                                                                                                                                                                                       | Where it surfaces                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| **Protocol package**      | The folder under `content/protocols/<cluster>/<name>/` that holds `protocol.yaml`, `materials.yaml`, and `scenes/`. A structural unit, not a `protocol_type` value.                              | `content/protocols/<cluster>/<name>/`                      |
| **Protocol type**         | The kind of protocol authored. Closed enum: `mini_protocol`, `sequence_runner`.                                                                                                                  | `protocol.protocol_type` field                             |
| **Mini-protocol**         | One authored student-facing workflow with normal steps, a `learning` block, scenes, materials, and referenced objects. Step count is determined by pedagogy.                                     | `protocol_type: mini_protocol`                             |
| **Sequence runner**       | An ordered non-empty list of unique direct mini-protocol leaves. It declares the pathway in place of authored steps; nested runners and repeats are invalid. May be rendered as "full protocol". | `protocol_type: sequence_runner`                           |
| **Protocol**              | The top-level YAML block and the three-nested-level model (`protocol -> step -> interaction`). Structural umbrella; not a `protocol_type` value.                                                 | `protocol` block in `protocol.yaml`                        |
| **Initial session state** | Optional root seed list. It establishes declared object or subpart state before entry; a declared group expands only for this seed.                                                              | `protocol.initial_state[]`                                 |
| **Step**                  | One pedagogical unit -- one thing the student is asked to accomplish. Often multi-gesture.                                                                                                       | one entry in `protocol.steps`                              |
| **Sequence**              | The ordered list of interactions inside a step; order always matters.                                                                                                                            | `step.sequence`                                            |
| **Interaction**           | One `gesture` on one `target`, with its own required non-empty `instruction`, `hint`, `validator`, and `response`.                                                                            | one entry in `step.sequence`                               |
| **Instruction**           | Required non-empty plain-string primary next-action text. Adjacent reachable-flow interactions and repeated exact `(target, gesture)` substeps use distinct normalized text.                  | `interaction.instruction`                                  |
| **Hint**                  | Required non-empty plain-string disclosed next-action support. Adjacent reachable-flow interactions and repeated exact `(target, gesture)` substeps use distinct normalized text.             | `interaction.hint`                                         |
| **Target**                | The addressable, semantic scene object or control the student acts on. Named, not positional.                                                                                                    | `interaction.target`                                       |
| **Gesture**               | How the student acts on the target. One of `click`, `drag`, `adjust`, `select`, `type`.                                                                                                          | `interaction.gesture`                                      |
| **Validator**             | A named preset that checks one gesture on one target.                                                                                                                                            | `interaction.validator`                                    |
| **Step validator**        | A named preset that checks whole-step completion.                                                                                                                                                | `step.step_validator`                                      |
| **Response**              | The container for post-validation system behavior: `scene_operations` and optional `feedback`.                                                                                                   | `interaction.response`                                     |
| **Scene operation**       | One of the five ratified typed primitives describing how the scene changes.                                                                                                                      | `response.scene_operations[]`                              |
| **Outcome**               | The `{on_success, on_failure}` mapping that says how the step resolves.                                                                                                                          | `step.outcome`                                             |
| **Domain verb**           | An author-facing named composition over the two-level model. Expands to existing slots.                                                                                                          | authoring shorthand; expands to `step`/`interaction` slots |

## Reagent and material terms

These lab-domain terms are kept; they describe substances, not
model structure.

| Term                      | Definition                                                                                                                                                                                |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Reagent**               | A substance defined in the protocol's reagent data.                                                                                                                                       |
| **Liquid**                | A reagent currently being moved, held, or tracked. Named in an `ObjectStateChange` writing the object's flat declared liquid fields (for example `material_name` / `held_material_name`). |
| **Stock solution**        | The highest-concentration reagent supplied in a bottle or vial at the start of the protocol. Never used directly on cells; diluted first.                                                 |
| **Intermediate dilution** | A temporary tube of solution prepared by diluting a stock solution down toward a usable working concentration.                                                                            |
| **Working solution**      | The final, ready-to-dose dilution delivered into a vessel at the protocol-specified volume.                                                                                               |

## Test-tier terms

These describe the test tooling the repo runs today. They are
unchanged by the vocabulary redesign.

| Term                    | Definition                                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Walker**              | YAML-driven UI playthrough that clicks the real DOM. Canonical real-UI regression test.                             |
| **Wrong-order UI pass** | Variant of the walker that injects a wrong-order click before each correct sequence and asserts soft-fail behavior. |
| **Human playtest**      | A human plays the game. The only thing that judges UX clarity.                                                      |
