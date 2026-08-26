# Object vocabulary

This document is the canonical vocabulary for the object system: object
authoring, the object library, object-side validators, and object-related
documentation in this repository. Every object-related doc, code comment,
error message, validator output, and authoring guide must use these exact
terms with these exact meanings.

This doc is the third corner of a three-vocabulary model. The protocol
side names what happens; the object side names what a thing is and how
its state appears; the scene side names where things appear and how the
space is arranged. The protocol-side counterpart is
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md); the scene-side
counterpart is [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md). Where a
concept is protocol-side or scene-side, this doc points to the relevant
canonical doc rather than redefining it.

YAML schema detail (the exact authoring file shape, file naming, and
validation rules) lives in [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).
This doc names the vocabulary; the format doc encodes the schema.

## What an object is

An **object** is the unit of authoring for "what a thing is". One object
definition declares one identity, one structure (subparts only), one
schema of flat-primitive state variables,
one map from state values to visual assets, one closed capability set,
and one set of layout hints. The object definition does not say where
the thing goes (that is scene-side; see
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md)) and does not say what should
happen to it (that is protocol-side; see
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)).

The object owns SVG manipulation. The protocol sets semantic state
through `ObjectStateChange`; the object's `visual_states` resolves the
state value to a visual asset. The protocol never names an SVG asset name
and never names a visual variant. This central design rule means every part
of the schema below enforces this separation.

## Canonical object identity, no extends

Objects are canonical-by-object_name. Each object definition lives in
`content/objects/<kind>/<object_name>.yaml` where `<kind>` matches the object's declared `kind` field,
and is the single authoritative source for that
object's identity, state schema, visual_states, and capabilities. Objects have
no `extends` and no template-object layer.

If an object differs meaningfully from an existing one, mint a new object_name
rather than reusing or templating the existing object. This rule preserves
object identity as a permanent, versioned, stand-alone contract.

For the asymmetric design across objects, protocols, and scenes, see
[SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) "Asymmetry rationale".

## Object identity

Identity fields name the object and classify it. They are stable across
scenes; a scene placement may not override them.

| Field         | Required | Purpose                                                                                                                                                                                                                          |
| ------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `object_name` | yes      | Stable object name. Unique across the object library. The scene side names this object only by `object_name`.                                                                                                                    |
| `kind`        | yes      | Coarse classification. Closed enum: `plate`, `bottle`, `flask`, `pipette`, `rack`, `waste`, `equipment`, `decoration`. The eight values mirror today's `kind` sub-field; the inventory observed all eight in shipped scene YAML. |
| `label`       | yes      | Required human-readable name. Object-owned; scene may not override.                                                                                                                                                              |

`asset_name` (today's `items[]` sub-field) is **not** an identity field on
the object. The object resolves an asset through `visual_states` from
declared state, so a single asset literal is just a `visual_states`
entry with one case. See [Visual states](#visual-states) below.

## Structured surfaces and subparts

Some objects have addressable internal structure. A 96-well plate has
96 wells. A dilution tube rack has tubes. A gel has lanes. A
multichannel pipette has channels. The object declares this structure
once; a protocol addresses individual subparts by reference into the
object's own declared structure.

Protocols address subparts explicitly (for example
`treatment_plate.A1`, `treatment_plate.A2`). The vocabulary has no
named-group construct.

The structure block is optional. An object with no structure block is a
**flat object** (a bottle, a flask, a single-tube vial). An object with
a structure block is a **structured surface**, and its subparts are
first-class addressable units inside that object's namespace.

| Field                            | Required                   | Purpose                                                                                                                                                                         |
| -------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `structure.subpart_kind`         | yes (if structure present) | What each subpart is (`well`, `tube`, `lane`, `slot`, `channel`).                                                                                                               |
| `structure.layout`               | yes (if structure present) | One of `grid` or `list`. A grid declares rows and cols; a list declares an ordered count.                                                                                       |
| `structure.rows`                 | grid only                  | Row count.                                                                                                                                                                      |
| `structure.cols`                 | grid only                  | Column count.                                                                                                                                                                   |
| `structure.count`                | list only                  | Subpart count.                                                                                                                                                                  |
| `structure.name_pattern`         | yes (if structure present) | How a subpart name is built from its row, col, or index. For example `{row_letter}{col}` for a 96-well plate (A1..H12); `slot_{index}` for a list-layout rack (slot_0..slot_n). |
| `structure.subpart_state_fields` | no                         | A schema of state variables that every subpart carries. Same shape as the object-level `state_fields` schema, applied per subpart.                                              |

Subpart state is not a separate vocabulary. It is the same
[`state_fields`](#state_fields) schema applied at subpart granularity.
A 96-well plate has zero or few plate-level state fields and several
flat per-well fields (`material_name`, `material_volume`);
a multichannel pipette has the same flat material fields per channel.

### Grouped targets are listed explicitly

A protocol that needs to act on a row of wells, a tube column, or a
set of gel lanes lists each subpart by reference (for example
`treatment_plate.A1`, `treatment_plate.A2`, ...,
`treatment_plate.A12`). The object's `name_pattern` is the only naming
contract; the scene never sees grouping.

## Materials

**Material** is the material currently inside or held by an object. This may
be a reagent, waste, old media, cells, a mixture, suspension, or diluted
drug. The `material_name` field (on objects holding material) or
`held_material_name` field (on tools carrying material) reference entries in
a `materials.yaml` registry.

## state_fields

`state_fields` is the object's typed schema of declared state
variables. It is the contract between the protocol and the object: a
protocol reads or sets a `state_field` by name; the object resolves
what that state means visually through [`visual_states`](#visual-states).
Anything not in `state_fields` is not part of the object's authoring
surface.

Every `state_field` is a flat primitive. Allowed types are `enum`,
`int`, `float`, and `bool`. There is no `string` type (use `enum`
with a closed `allowed` list) and no composite `material` or `set_point`
type. Materials and instrument set-points are modeled as multiple
flat fields per object (for example `material_name` plus `material_volume`
for a well; `set_volume` for an adjustable-pipette set point).
The runtime material-state model decomposes across these flat fields.

| Field         | Required | Purpose                                                                                                                                                                                |
| ------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `field_name`  | yes      | Field name, snake_case, scoped to this object.                                                                                                                                         |
| `type`        | yes      | One of `enum`, `int`, `float`, `bool`.                                                                                                                                                 |
| `default`     | yes      | Initial value. Required so an object's start state is never undefined. Must satisfy the per-type metadata below.                                                                       |
| `applies_to`  | no       | `object` (default) or `subpart`. When `subpart`, the field is declared per subpart instead of per object. Equivalent to listing the same field under `structure.subpart_state_fields`. |
| `description` | no       | One-line author-facing description.                                                                                                                                                    |

### Per-type constraint metadata

Constraint metadata is closed per primitive type. Only the
keys listed below are allowed; an unknown metadata key is a build-time
error. There is no open-ended `constraints` object.

| Type    | Allowed metadata keys                                                                           |
| ------- | ----------------------------------------------------------------------------------------------- |
| `enum`  | `allowed` (non-empty list of strings, required), `default` (one value from `allowed`, required) |
| `int`   | `unit` (string), `min` (int), `max` (int), `step` (int), `default` (int, required)              |
| `float` | `unit` (string), `min` (float), `max` (float), `step` (float), `default` (float, required)      |
| `bool`  | `default` (`true` or `false`, required)                                                         |

The `visual_states` entry for an `enum` field must cover every value in
`allowed`. Numeric fields (`int`, `float`) are resolved through the
formula mini-language defined in
[OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md). `bool` fields use the
`cases` form (one case for `true`, one for `false`).

The `applies_to: subpart` form is the bridge between object-level
`state_fields` and `structure.subpart_state_fields`. An author may
declare "every well has a `material_volume` field" once at the object
level with `applies_to: subpart`, instead of restating it under
structure. Both forms are equivalent.

## Visual states

The `visual_states` is the object's state-to-visual function. The protocol
sets semantic state via `ObjectStateChange`; the object's `visual_states`
resolves the new state value to a visual asset (an SVG file, an overlay).
An object declares named closed visual variants; `visual_states` is not a
generic rendering map or expression surface. Unknown variants are a build
error. The object owns the visual representation; the protocol stays
semantic.

The `visual_states` is keyed by `state_field` name. For each named
`state_field`, it maps state values to visual outputs.

### Form selection and material rendering

For `visual_states.<field>.kind: svg`, the closed `cases` mapping is the
sole object-authoring authority for selecting complete SVG forms. A single
form is a one-case mapping; a discrete-state collection is the set of forms
selected by the cases for one or more object state fields. There is no
collection manifest, and filenames and asset directories do not declare a
collection.

Selection and rendering are independent. After a case selects its complete
form, the SVG pipeline reads that form's exact root declaration. A root
`data-vlab-rendering="material"` selects the compiled material-rendering
path; its absence selects the ordinary SVG path. One discrete collection may
therefore contain static and material-rendered forms. Object YAML neither
declares a rendering model nor describes layers inside a selected form. See
[SVG_PIPELINE.md](SVG_PIPELINE.md) for the asset contract.

The paired material identity and amount entries in `visual_states` remain the
object's material binding authority. They supply the registered material and
volume; they do not name SVG geometry. A material-bound selected form stays
inline SVG DOM even while its amount is zero because the compiled material
instance needs the same injected DOM home. `requires_dom_svg` is derived from
the selected form and binding, not authored in object YAML.

| Field                              | Required                | Purpose                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `visual_states.<field>.kind`       | yes                     | One of `svg`, `overlay`, `composite`. `svg` names a base SVG asset name. `overlay` names an SVG fragment composited over the base. `composite` is a list of any of the above.                                                                                                                                                                                                                        |
| `visual_states.<field>.cases`      | yes for `enum` / `bool` | One case per allowed value of the `state_field`. Each case has a `when` (the state value) and an output (asset_name, overlay_name, or composite list).                                                                                                                                                                                                                                               |
| `visual_states.<field>.formula`    | yes for `int` / `float` | A declarative recipe drawn from the closed mini-language in [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) (for example `fill_height(...)`). For numeric fields where enumerating cases is impractical, the formula names the rendering rule; the runtime resolves it. The token set is closed; per-object formula code is not allowed. |
| `visual_states.<field>.applies_to` | no                      | `object` or `subpart`. When `subpart`, the `visual_states` applies per subpart (for example one fill per well). Default: `object`.                                                                                                                                                                                                                                                                   |

Rules:

- Every value in a `state_field`'s `allowed` list must have a
  `visual_states` case (`enum`, `bool`) or be covered by a formula
  (numeric `int` and `float` fields).
- A `visual_states` entry for an `applies_to: subpart` `state_field` must
  itself be `applies_to: subpart`.
- The `visual_states` is the only object-side authoring surface that names
  SVG asset names or overlay names. An identity field, a `state_field`, a
  capability, or a layout hint never names an asset name.
- **One selected form per paired runtime material binding (variant-collapse
  rule).** When paired identity and amount entries use runtime material rendering
  (for example `material_tint` with `fill_height(...)`), every material-name case
  resolves to the same `asset_name`. The sentinel `empty` resolves to that same
  form. Material identity and amount change runtime material state, not the
  selected form. Pairing is by shared field-name prefix, so an electrophoresis
  chamber that declares both `inner_chamber_material_*` and
  `outer_chamber_material_*` validates each pair independently. See
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) for the binding and dispatch
  contract. A material-rendered selected form uses generated, opaque manifest
  handles for role paint and the derived gravity-part transform. Structured
  subpart material rendering remains a separate generated-geometry mechanism.

  This rule does not prohibit complete discrete forms that depict genuine form
  or geometry changes. Contents already carried by material state do not justify
  a second vessel form: pre-weighed MTT powder uses the canonical microtube form
  in both material states. Filenames never determine intent.

Object YAML must not name an SVG `layer_name`, `paint_role`, `adjustment`,
stacking phase, runtime handle, DOM id, or SVG-recipe sidecar. Runtime code
does not query authored `data-vlab-*` through an object declaration. Those
are SVG-pipeline concerns, not object vocabulary. The existing
`anchor_liquid_bounds`, optional `anchor_liquid_clip`, and capacity values
remain binding/compiler inputs for `fill_height`; their interpretation is
defined by [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).

`SvgSwap`, `ColorChange`, `LiquidDisplayChange`, and
`SetPointDisplayChange` are object/render-layer mechanisms invoked by
`visual_states` when state changes. They are not protocol-side scene
operations and never appear as authored slots in protocol YAML or scene
YAML. The protocol-side primitive that drives them is
`ObjectStateChange`, which writes the flat declared state fields
(`material_name`, `material_volume`, `held_material_name`,
`held_material_volume`, `set_volume`, `set_temperature`, `set_rpm`,
etc.); `visual_states` then resolves the new state to the appropriate
render output.

The full set of allowed `formula` tokens (the formula mini-language) is
intentionally narrow; the canonical enumeration belongs in
`docs/OBJECT_YAML_FORMAT.md` alongside the schema for `cases`.

## Capabilities

**Capabilities** are coarse declarations of what an object affords. The
capability set is the contract for what kinds of interactions a scene
and a protocol may attempt against this object. The inventory observed
`capabilities` as a top-level scene-YAML key on most current scene
files; in the cleaned vocabulary it moves to the object (a capability
is a property of what the thing is, not where it is placed).

| Field          | Required           | Purpose                         |
| -------------- | ------------------ | ------------------------------- |
| `capabilities` | yes (may be empty) | Closed list of affordance tags. |

The capability vocabulary is a closed list owned by this doc. An object
may not invent capabilities, and there are no open-ended capability
objects. Adding a capability value requires an explicit edit to this
vocabulary. The closed list is:

| Capability                 | Meaning                                                                                                                                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `clickable`                | The object accepts a `click` gesture (per the `gesture` set in [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)). An object that is not `clickable` is never clickable, regardless of placement.            |
| `material_container`       | The object holds tracked material; expects flat `state_fields` such as `material_name` and `material_volume` and a visual rule for them. Used by every container (bottle, flask, pipette, well-as-subpart). |
| `instrument_with_setpoint` | The object exposes one or more numeric set-point `state_fields` (typically `float` with `unit`, `min`, `max`); expects an `adjust` gesture from the protocol side.                                          |
| `structured_surface`       | The object has a `structure` block with subparts. Every plate, gel, rack, and multichannel pipette carries this capability.                                                                                 |
| `cursor_attachable`        | The object may be attached to the cursor by a `CursorAttach` `scene_operation`. Tools that the learner picks up and carries (a serological pipette, a transfer pipette) carry this capability.              |
| `decoration_only`          | The object is rendered as a static visual and accepts no gestures and no state mutation. Mutually exclusive with every other capability above.                                                              |

`decoration_only` is mutually exclusive with `clickable`,
`material_container`, `instrument_with_setpoint`, `structured_surface`,
and `cursor_attachable`. The other five are freely combinable.

A scene placement may not override `capabilities`. An object that
declares `[clickable, material_container]` carries those affordances in
every scene that places it.

## Layout hints

**Layout hints** are object-side defaults that the layout engine
([LAYOUT_ENGINE.md](LAYOUT_ENGINE.md)) consumes when the scene places
the object. They are visual metrics of the object itself, not of any
one scene. A scene placement may override layout hints only; this is
the only override category.

| Field                    | Required | Purpose                                                                                                             |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `layout.default_width`   | yes      | Default visual width in layout units.                                                                               |
| `layout.display_width_cm` | no      | Object-owned real-world display width used by the scaling model.                                                     |
| `layout.label_width`     | no       | Width budget for the label.                                                                                         |
| `layout.anchor_y_offset` | no       | Vertical anchor adjustment; observed on pipette assets.                                                             |
| `layout.anchor_y`        | no       | One of `bottom`, `tip`, or `top` (engine fallback, centers on the derived baseline). A serological pipette is anchored at its tip wherever it is placed. |

## Object ownership of SVG manipulation

The object owns the state-to-visual map and SVG manipulation boundary. The
protocol sets semantic state through `ObjectStateChange`; the object's
`visual_states` resolves the asset. The protocol never names an SVG asset
name and never names a visual variant.

This rule is binding on:

- [`state_fields`](#state_fields) -- the only authoring surface for
  declared state.
- [`visual_states`](#visual-states) -- the only authoring surface for
  state-to-visual resolution and complete-form selection.
- `ObjectStateChange` (defined in
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)) -- the only
  protocol primitive that mutates declared state on an object. An
  `ObjectStateChange` targets a declared `state_field` by name and
  provides a value matching that field's primitive type (`enum`,
  `int`, `float`, or `bool`). Nested writes are not allowed. The
  validator rejects unknown field names and type-mismatched values.
  Example payload (well at A1 receives 100 ul of PBS): `state: {
material_name: pbs, material_volume: 100 }`. The
  earlier nested form `state: { held_liquid: { reagent: pbs, volume:
100 } }` is not valid.

## The object side of the boundary

The three-way boundary names what each vocabulary owns:

- **Protocol** names what happens. The protocol asks the object to be
  in a different declared state through `ObjectStateChange`; the
  object resolves the visual. Canonical doc:
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
- **Object** names what a thing is and how its state appears. An
  object declares identity, structure (subparts only), the typed
  flat-primitive `state_fields` schema, the
  `visual_states` from state value to complete visual output, the closed
  `capabilities` set, and object-default layout hints. The object
  owns the state-to-visual map and SVG manipulation. The object never
  names where it goes in any one scene.
- **Scene** names where things appear and how the space is arranged.
  A scene references objects by object_name, places them inside named zones,
  supplies ordered semantic zones and bounded layout hints, and declares the
  static background backdrop. The layout manager derives scene and zone
  geometry. A
  scene never declares object identity, `state_fields`, `visual_states`,
  or `capabilities`. Canonical doc:
  [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).

A scene placement may carry only the categorical `layout.anchor_y` and
`layout.label_placement` hints. A placement may not
override identity (`object_name`, `kind`, `label`), `state_fields`,
`visual_states`, or `capabilities`.

## Worked example: 96-well plate

The 96-well plate is the canonical example for structured surfaces and
per-subpart flat-primitive `state_fields`. The candidate is the
`well_plate_96` asset observed in the inventory.

```yaml
object_name: well_plate_96
kind: plate
label: 96-well plate

structure:
  subpart_kind: well
  layout: grid
  rows: 8
  cols: 12
  name_pattern: "{row_letter}{col}" # A1..H12; row_letter is A..H, col is 1..12

state_fields:
  - field_name: material_name
    type: enum
    allowed: [empty, pbs, media, trypsin, dmso, drug_a, drug_b]
    default: empty
    applies_to: subpart
    description: Material currently in this well.
  - field_name: material_volume
    type: float
    unit: ul
    min: 0
    max: 300
    default: 0
    applies_to: subpart
    description: Volume of material in this well, in microliters.

visual_states:
  material_name:
    kind: svg
    applies_to: subpart
    cases:
      - when: empty
        output: { asset_name: well }
      - when: pbs
        output: { asset_name: well }
      - when: media
        output: { asset_name: well }
      - when: trypsin
        output: { asset_name: well }
      - when: dmso
        output: { asset_name: well }
      - when: drug_a
        output: { asset_name: well }
      - when: drug_b
        output: { asset_name: well }
  material_volume:
    kind: composite
    applies_to: subpart
    formula: fill_height(state(material_volume), capacity_ul=300)

capabilities: [clickable, structured_surface, material_container]

layout:
  default_width: 14
  label_width: 8
```

Reading: the plate has no plate-level state, 96 wells (A1..H12) each
carrying two flat `state_fields` (`material_name`, `material_volume`).
A protocol that needs to act on row A lists each subpart explicitly:
`treatment_plate.A1`, `treatment_plate.A2`, ..., `treatment_plate.A12`.
Each well's `visual_states` resolves the two flat fields to a base SVG
and a fill height independently. No SVG asset name appears in any
`state_field`. The `row_letter` and `col` tokens in `name_pattern` are
object-vocabulary literals (the row index 0..7 maps to A..H; the col
index 1..12 maps to itself); the same pattern would express `slot_0..slot_7`
for a list-layout rack via `name_pattern: "slot_{index}"`.

## Worked example: serological pipette

A serological pipette is a single-use, graduated transfer pipette. It is a
canonical example of a flat material container: the protocol records what was
drawn and the volume loaded to the graduation, but does not invent a digital
set point. Adjustable micropipettes and repeating dispensers carry their own
numeric set-point fields.

```yaml
object_name: serological_pipette
kind: pipette
label: Serological pipette

state_fields:
  - field_name: held_material_name
    type: enum
    allowed:
      [empty, media, pbs, trypsin, cells, cell_suspension,
       running_buffer_10x, running_buffer_1x, ddh2o]
    default: empty
    description: Material currently loaded in the pipette barrel.
  - field_name: held_material_volume
    type: float
    unit: ml
    min: 0
    max: 25.0
    default: 0
    description: Volume drawn to the graduation, in milliliters.
  - field_name: freshness
    type: enum
    allowed: [sterile, used]
    default: sterile
    description: Whether this disposable pipette has contacted a reagent source.

visual_states:
  held_material_name:
    kind: svg
    cases:
      - when: empty
        output: { asset_name: serological_pipette }
      - when: pbs
        output: { asset_name: serological_pipette }
      - when: media
        output: { asset_name: serological_pipette }
      - when: trypsin
        output: { asset_name: serological_pipette }
      - when: cells
        output: { asset_name: serological_pipette }
      - when: cell_suspension
        output: { asset_name: serological_pipette }
      - when: running_buffer_10x
        output: { asset_name: serological_pipette }
      - when: running_buffer_1x
        output: { asset_name: serological_pipette }
      - when: ddh2o
        output: { asset_name: serological_pipette }
  held_material_volume:
    kind: composite
    formula: fill_height(state(held_material_volume), capacity_ml=25.0)
  freshness:
    kind: overlay
    formula: 'label(state(freshness), format="Pipette: {value}")'

capabilities:
  [clickable, material_container, cursor_attachable]

layout:
  default_width: 3
  label_width: 6
  anchor_y: tip
  anchor_y_offset: 0
```

Reading: the pipette is a flat object (no `structure` block, no subparts). It
declares `held_material_name`, `held_material_volume`, and `freshness`.
Together these show what was drawn, the graduation volume, and whether the
disposable pipette has contacted a source. The `visual_states` resolves those
fields independently: the material selects a complete SVG form, the volume
becomes a fill-height binding, and freshness becomes an object-level overlay
label. A material-declared selected form uses compiled gravity parts; object
YAML does not describe its internals. No SVG asset name appears in any
`state_field`. The
layout hints (`default_width: 3`, `label_width: 6`, `anchor_y_offset: 0`,
`anchor_y: tip`) are object-owned; the tip anchor reflects that a
serological pipette is tip-anchored wherever it is placed.

## Terms

| Term                | One-line definition                                                                                                                                                                                                                                      |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| object              | The unit of authoring for "what a thing is"; one identity, one structure, one schema of state, one visual_states map, one capability set, one set of layout hints.                                                                                       |
| object library      | The collection of object definitions a scene references by `object_name`; the home of every object-identity slot.                                                                                                                                        |
| object_name         | The stable string name for an object; the only handle the scene side names.                                                                                                                                                                              |
| material            | Anything physically present in, on, produced by, removed from, or transferred between objects (reagent, waste, old media, cells, mixture, suspension, diluted drug). Authored in `materials.yaml`. See [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md). |
| flat object         | An object with no `structure` block; no subparts.                                                                                                                                                                                                        |
| structured surface  | An object with a `structure` block declaring addressable subparts.                                                                                                                                                                                       |
| subpart             | An addressable internal unit of a structured surface (a `well`, `tube`, `lane`, `slot`, `channel`).                                                                                                                                                      |
| `state_field`       | One declared, typed flat-primitive state variable on an object or per subpart; the contract between the protocol and the object.                                                                                                                         |
| `visual_states`     | The object's state-to-visual function; its `svg` cases select complete forms and its material entries bind identity and amount. It never describes internal SVG layers. |
| capability          | A closed-vocabulary affordance tag declared on the object: `clickable`, `material_container`, `instrument_with_setpoint`, `structured_surface`, `cursor_attachable`, `decoration_only`.                                                                  |
| layout hint         | An object-owned visual metric or anchor the layout engine consumes (`display_width_cm`, `default_width`, `label_width`, `anchor_y_offset`, `anchor_y`). Scene placements cannot override intrinsic metrics. |
| `ObjectStateChange` | The protocol-level primitive that mutates declared `state_fields` on an object; defined in [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).                                                                                                             |
