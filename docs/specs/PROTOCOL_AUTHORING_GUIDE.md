# Protocol authoring guide

This guide walks a new author through writing a protocol from scratch: the
three YAML files, the validator, and the real-UI walker. It uses the
canonical vocabulary defined in
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md). Read that document first;
this guide assumes those terms.

Related references:

- [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md): canonical terms.
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md): full schema for
  `materials.yaml` and `protocol.yaml`.
- [PROTOCOL_STEPS.md](PROTOCOL_STEPS.md): the step model and runtime
  resolution.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md): the scene placement schema.
- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md): canonical object terms
  (`state_fields`, `visual_states`, structured surfaces and subparts) the
  protocol's `target` names resolve against.
- [WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md): the YAML-driven UI walker
  (canonical real-UI regression test).
- [SCENE_METRICS.md](SCENE_METRICS.md): layout health report quickstart and
  metric reference for scene writers (categories, findings, evidence glossary,
  provisional bands).

## Terminology

The authored kinds (`mini_protocol`, `sequence_runner`) and
the surrounding structural terms (protocol package, `protocol_type`,
`protocol.yaml`) are defined canonically in
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md#protocol-kinds). This
guide uses those terms.

## What a protocol package is

A protocol package is a self-contained folder under
`content/protocols/<cluster>/<protocol_name>/` with files:

```
content/protocols/<cluster>/<protocol_name>/
  protocol.yaml     # protocol_type, parts, days, and the ordered list of steps
  materials.yaml     # liquids, reagents, cells, waste, and other materials
  scenes/
    <scene_name>.yaml     # protocol-specific scene overrides (optional)
```

Shared objects live in `content/objects/`. Protocol scenes place them under
`content/protocols/<cluster>/<protocol_name>/scenes/`. Every `protocol.yaml` declares
a `protocol_type` (one of `mini_protocol`, `sequence_runner`).
A mini-protocol must define a `learning` block with required fields
`objectives`, `outcomes`, and `goals`, and a top-level `entry_step`
field naming the first step's `step_name`. The protocol has no `entry`
block and declares no opening scene; scene context comes from the
first step's interactions and any `SceneChange` operation in their
responses.

A Python builder reads these files, validates them, and emits TypeScript
modules that the browser bundle imports. No YAML is parsed at runtime.

## Write the flow sketch first

Before writing any YAML, sketch the flow. [PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md)
requires this: the author works out the click path and the visible state
changes before touching `protocol.yaml`. The sketch may be a diagram or a
short table, but it must name, in order:

- the objects that matter for the mini-protocol;
- the first object the student clicks;
- for each step, the target that receives the action and the gesture used
  on it;
- the state change the student sees after each interaction;
- the next step the flow moves to.

This sketch is the design source for the `learning` block, the step chain,
the `sequence` of interactions, and the screenshot checkpoints a walker
verifies. Write the sketch, then encode it as `protocol.yaml` following the
schema in the rest of this guide.

[gen_flow_view.py](../../pipeline/gen_flow_view.py) generates a flow
view from an already-written `protocol.yaml` (steps, click path, gestures,
state changes, transitions). That generated view is an AUDIT/consistency
artifact for checking a finished protocol against its intended flow -- it is
not the design source. The design source is the flow sketch an author writes
before implementation, described above.

## The two-level model

Every protocol is a tight linear spec with three nested levels: `protocol`,
`step`, and `interaction`.

```
protocol
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
      response            # container: scene_operations, optional feedback
  step_validator          # named preset: checks whole-step completion
  outcome                 # mapping: on_success, on_failure
  next_step               # names the next step by its step_name, or null
```

A `step` is one pedagogical unit. A step is often multi-gesture; the
individual gestures live inside it in the ordered `sequence`. Each
`interaction` has exactly the four slots `target`, `gesture`, `validator`,
`response`. The full slot charters and the closed `gesture` value set
(`click`, `drag`, `adjust`, `select`, `type`) are in
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
For cross-layer gesture status and the unresolved role of the currently unused
`select` value, see `docs/specs/GESTURE_MODEL.md`.

## Writing materials.yaml

`materials.yaml` declares every material the protocol references: reagents,
liquids, cells, waste, mixtures, suspensions, diluted drugs, or other
materials. Each material entry has a unique snake_case name, a `label`,
and a `display_color`. A material name is what an `ObjectStateChange`
`scene_operation` writes into an object's flat declared `material_name`
(or `held_material_name`) `state_field`.

The full `materials.yaml` field tables and cross-file validation rules are in
[PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md).

## Writing protocol.yaml

`protocol.yaml` carries the `learning` block, the top-level `entry_step`
field, the `parts` and `days` organizational metadata, and the `steps` list.
Steps are the runnable units; protocol flow is `entry_step` plus each
step's `next_step`, not array position.

### A worked step

"Wash the flask with 4 mL PBS" is one step. It is the canonical
multi-gesture case:

```yaml
- step_name: pbs_wash
  prompt: "Wash the flask with 4 mL PBS."
  sequence:
    - target: serological_pipette
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: CursorAttach
            target: serological_pipette
            operation: attach
    - target: pbs_bottle
      gesture: click
      validator: { preset: correct_target }
      response:
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

### A set-point step

Setting a pipette volume is a real lab skill. Encode it with `gesture:
adjust` and the `target_with_value` validator preset, never as a plain
`click` with a volume field:

```yaml
- step_name: set_pipette_volume
  prompt: "Set the serological pipette to 4 mL."
  sequence:
    - target: serological_pipette
      gesture: adjust
      validator: { preset: target_with_value, value: { set_volume: 4 } }
      response:
        scene_operations:
          - type: ObjectStateChange
            target: serological_pipette
            state:
              set_volume: 4
  step_validator: { preset: sequence_complete }
  outcome:
    on_success: complete
    on_failure: retry
  next_step: draw_pbs
```

### A decision step

A multiple-choice or phase-keep decision is a `select`-gesture interaction
validated by `correct_choice`:

```yaml
- step_name: choose_dilution
  prompt: "Which recipe makes 1 mL of 200 &micro;M working solution from a 10 mM stock?"
  sequence:
    - target: choice_20uL_stock
      gesture: select
      validator: { preset: correct_choice }
      response:
        feedback:
          correct: "Correct: 20 &micro;L stock + 980 &micro;L media is 200 &micro;M."
          incorrect: "Check your math with C1V1 = C2V2."
  step_validator: { preset: sequence_complete }
  outcome:
    on_success: complete
    on_failure: retry
  next_step: prepare_working_solution
```

`scene_operations` may be an empty list here; a correct choice can be
`feedback`-only.

### A subpart-targeting step

The protocol YAML is geometry-free: it names no plate, no well, no row,
no x/y. Subparts of a structured object (wells, lanes, slots) are declared
by the object via `structure.subparts` (see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)). A protocol addresses a
single subpart as `<object_name>.<subpart_name>` (for example
`treatment_plate.A1`).

A step that acts on several subparts emits one interaction per subpart.
Worked example for two wells in row B:

```yaml
- step_name: add_media_row_b
  prompt: "Add 100 &micro;L media to wells B1 and B2."
  sequence:
    - target: serological_pipette
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: CursorAttach
            target: serological_pipette
            operation: attach
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
    - target: treatment_plate.B2
      gesture: click
      validator: { preset: correct_target }
      response:
        scene_operations:
          - type: ObjectStateChange
            target: treatment_plate.B2
            state:
              material_name: media
              material_volume: 100
  step_validator:
    preset: final_state_matches
    target: treatment_plate.B2
    contains: { material_name: media }
  outcome:
    on_success: complete
    on_failure: retry
  next_step: add_media_row_c
```

When real authoring pain from per-subpart enumeration appears, named
groups may be revisited as a separate vocabulary addition.

## Domain verbs: authoring shorthand only

A domain verb -- `wash`, `dispense`, `grind`, `assemble`, `draw`,
`titrate`, and so on -- is the word a YAML author naturally reaches for.
Domain verbs are **authoring vocabulary and documentation shorthand, not
protocol YAML fields** in the initial tight spec. The executable YAML is
always the expanded two-level model: `step`, `sequence`, `target`,
`gesture`, `validator`, `response`, `scene_operations`, `step_validator`,
`outcome`, `next_step`.

This guide may teach with domain verbs, but every domain verb shown here
includes its explicit expansion to the literal slots. A domain verb implies
no hidden state change: all state change is explicit in a `response` as a
`scene_operation` mutation.

A future plan may add domain-verb macros, but only after the expanded form
is stable.

### Interaction-level domain verb: `draw`

`draw` is shorthand for one interaction -- one `target`, one `gesture`, one
`validator`, one `response`. "Draw 4 mL PBS into the pipette" expands to
an `ObjectStateChange` writing the pipette's flat declared liquid fields:

```yaml
- target: pbs_bottle
  gesture: click
  validator: { preset: correct_target }
  response:
    scene_operations:
      - type: ObjectStateChange
        target: serological_pipette
        state:
          held_material_name: pbs
          held_material_volume: 4
```

### Step-level domain verb: `wash`

`wash` is shorthand for a whole `sequence` plus its `step_validator`. "Wash
the flask with 4 mL PBS" expands to the three-interaction `pbs_wash` step
shown in "A worked step" above: pick up the pipette (`CursorAttach`), draw
the PBS (`ObjectStateChange` writing `held_material_name` and
`held_material_volume`), dispense into the flask (`ObjectStateChange`
clearing the pipette's `held_material_*` fields and writing the flask's
`material_name` and `material_volume`), checked by a `final_state_matches`
`step_validator`.

When you write a protocol, think in domain verbs, then write the expanded
slots. The expansion is the verb's definition; there is nothing to a domain
verb except the slots it expands to.

## The pedagogy-first rule

An author chooses each interaction's `target` and `gesture` so the
interaction teaches the specific lab skill the step is about. The shape of
an interaction is a pedagogical decision, not just a UI decision:

- `adjust` on a continuous control teaches a set-point skill.
- `click` on a scene object teaches recognition and sequencing.
- `select` on an answer-choice target teaches a decision.
- `drag` on a scene object teaches a spatial placement skill.
- `type` on a control teaches entering a precise value.

The anti-pattern this rule catches is collapsing a skill-based interaction
into a rote `click` -- for example encoding a pipette volume as a field on
a `click` instead of using `gesture: adjust`. See
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md) for the full rule.

## Per-step authoring checklist

Run through this checklist for every step you write.

- **Each interaction has exactly four slots.** Every `interaction` carries
  `target`, `gesture`, `validator`, and `response` -- no more, no fewer.
- **Gesture matches the skill.** A set-point step uses `adjust`; a decision
  uses `select`; a scene-object action uses `click`. Do not collapse a
  skill into a rote `click`.
- **Targets are semantic and geometry-free.** Write a semantic `target`
  name; never write a well coordinate, a row range, or an x/y. A subpart
  of a structured object is written as `<object_name>.<subpart_name>`;
  a step that acts on several subparts emits one interaction per subpart.
- **Validators are named presets.** Every `validator` and `step_validator`
  is a preset from the documented library, with that preset's typed
  parameters. Never write free-form validation logic.
- **Responses carry explicit state change.** `response.scene_operations` is
  an ordered list of typed primitives (possibly empty); `feedback` is
  optional. All state change is a `scene_operation` mutation.
- **Outcome is a mapping.** `outcome` always has `on_success` and
  `on_failure`. The bare-scalar form is rejected.
- **Flow is named.** `next_step` names the next step by its `step_name`, or
  is `null` for a terminal step. `entry_step` names the first step by its
  `step_name`.
- **Referenced materials exist.** Every material name written by an
  `ObjectStateChange` into a flat material `state_field` (`material_name`,
  `held_material_name`) exists in `materials.yaml`.

## Build and walk loop

Iterate on a protocol with a short loop: audit, validate, build, walk. Stop
at the first failure and read the message. The builder runs all schema and
cross-file rules; the walker plays the protocol through the real DOM.

| Stage            | Purpose                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------- |
| Audit            | Quick per-step completeness report.                                                         |
| Validate         | Run all schema and cross-file rules without writing output.                                 |
| Build            | Validate and emit the generated TypeScript modules.                                         |
| Walk             | Rebuild the bundle, launch Playwright, and play the protocol through the real DOM.          |
| Wrong-order walk | Inject a wrong-order interaction before each correct one and assert the soft-fail behavior. |

Run Python tooling through the repo environment: `source source_me.sh && python3 ...`.

The build and walk commands and their exact flags are documented in
[WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md). When the protocol audits
clean, validates, builds, and walks green, it is shippable -- but a
mini-protocol is not complete until the visible interaction works through
the same path a student uses.
