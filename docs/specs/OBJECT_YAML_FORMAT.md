# Object YAML format

Object terminology is defined in [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
This doc uses that vocabulary. Where this doc names a section without
restating its meaning (for example "render map" or "named group"), the
vocabulary doc is the authority.

This document specifies the per-object YAML schema for the object library.
An object library file declares one object: identity, structure, the typed
`state_fields` schema, the `visual_states` from state value to visual asset,
the closed `capabilities` set, and object-default layout hints. The scene
side names the object only by `object_name`
([SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md)); the protocol side mutates
declared state through `ObjectStateChange`
([PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)).

## File layout

One object per file. The filename is the object `object_name` plus `.yaml`, in
snake_case. Examples: `well_plate_96.yaml`, `serological_pipette.yaml`,
`pbs_bottle.yaml`.

The rule is "one object per file" so a file rename always renames exactly
one object name and a code-search for an object name always lands in exactly one
file. Grouped library files (one file per `kind`, or one file per scene)
are explicitly out of scope for this doc.

Files live under `content/objects/<kind>/`. Subdirectory grouping by `kind`
(`content/objects/plate/`, `content/objects/bottle/`, etc.) is required.
Every object file lives in a subdirectory named exactly after its declared
`kind` value.

The object library is the authoring surface. The build pipeline compiles
the object library into a generated TypeScript module the scene driver and
adapters consume. No YAML parser ships in the browser; runtime callers read
the generated module.

## Top-level fields

Every object file is a single YAML mapping with the following top-level
keys. The "Required" column is the schema rule; the "Section" column links
to the per-section detail below.

| Field           | Type                | Required           | Section                             |
| --------------- | ------------------- | ------------------ | ----------------------------------- |
| `object_name`   | string              | yes                | [Object identity](#object-identity) |
| `kind`          | enum string         | yes                | [Object identity](#object-identity) |
| `label`         | string              | yes                | [Object identity](#object-identity) |
| `structure`     | mapping             | no                 | [Structure](#structure)             |
| `state_fields`  | list of mapping     | yes (may be empty) | [state_fields](#state_fields)       |
| `visual_states` | mapping             | yes (may be empty) | [Visual states](#visual-states)     |
| `capabilities`  | list of enum string | yes (may be empty) | [Capabilities](#capabilities)       |
| `layout`        | mapping             | yes                | [Layout hints](#layout-hints)       |

`state_fields`, `visual_states`, and `capabilities` are required even when
empty (the empty list and empty mapping forms). This is deliberate: an
object's authoring surface always lists its declared state, its visual states,
and its capabilities, even when there are none, so a reader never has to
guess whether absence means "none" or "forgot to add". The empty forms
are written `state_fields: []`, `visual_states: {}`, `capabilities: []`.

## Object identity

Identity fields name the object and classify it. They are stable across
scenes; a scene placement may not override identity.

| Field         | Type        | Required | Allowed                                                                                  | Default            |
| ------------- | ----------- | -------- | ---------------------------------------------------------------------------------------- | ------------------ |
| `object_name` | string      | yes      | snake_case, unique across the object library                                             | none (must be set) |
| `kind`        | enum string | yes      | one of `plate`, `bottle`, `flask`, `pipette`, `rack`, `waste`, `equipment`, `decoration` | none (must be set) |
| `label`       | string      | yes      | any non-empty string                                                                     | none (must be set) |

The `object_name` value must equal the filename without the `.yaml` extension. The
build pipeline rejects a mismatch.

`asset_name` (today's `items[]` sub-field in scene YAML) is **not** an
identity field. The object resolves an asset through `visual_states` from
declared state; a single literal asset becomes a `visual_states` entry with
one case. See [Visual states](#visual-states).

## Structure

The `structure` block declares addressable internal subparts. It is
optional. An object with no `structure` block is a flat object (a bottle, a
flask, a single-tube vial). An object with a `structure` block is a
structured surface; its subparts are first-class addressable units inside
the object's namespace.

| Field                            | Type            | Required                     | Allowed                                                                          | Default |
| -------------------------------- | --------------- | ---------------------------- | -------------------------------------------------------------------------------- | ------- |
| `structure.subpart_kind`         | enum string     | yes (if `structure` present) | one of `well`, `tube`, `lane`, `slot`, `channel`                                 | none    |
| `structure.layout`               | enum string     | yes (if `structure` present) | one of `grid`, `list`, `custom`                                                  | none    |
| `structure.rows`                 | int             | yes (if `layout: grid`)      | positive integer                                                                 | none    |
| `structure.cols`                 | int             | yes (if `layout: grid`)      | positive integer                                                                 | none    |
| `structure.count`                | int             | yes (if `layout: list`)      | positive integer                                                                 | none    |
| `structure.name_pattern`         | string          | yes (if `structure` present) | a string with one or more bracketed tokens drawn from the closed token set below | none    |
| `structure.subpart_state_fields` | list of mapping | no                           | same shape as [state_fields](#state_fields) entries; applied per subpart         | unset   |
| `structure.subpart_groups`       | mapping         | no                           | see [Subpart groups](#subpart-groups) section below                              | unset   |

`structure.layout` accepts only `grid` or `list`; any other value is
rejected by the build pipeline.

### name_pattern token set

`structure.name_pattern` is a small templating string. The closed token set
fixed by this format is:

| Token          | Meaning                                               | Valid in            |
| -------------- | ----------------------------------------------------- | ------------------- |
| `{row_letter}` | The row index `0..rows-1` mapped to letters `A..Z`    | `layout: grid` only |
| `{row}`        | The row index `1..rows` (1-based numeric)             | `layout: grid` only |
| `{col}`        | The column index `1..cols` (1-based numeric)          | `layout: grid` only |
| `{col_letter}` | The column index `0..cols-1` mapped to letters `A..Z` | `layout: grid` only |
| `{index}`      | The subpart index `0..count-1` (0-based numeric)      | `layout: list` only |

A token is written exactly as shown above, including the braces. Literal
characters between tokens are preserved verbatim. No other tokens are
allowed; an unknown token is a build-time error.

Examples:

- `name_pattern: "{row_letter}{col}"` on an 8x12 grid yields `A1`, `A2`,
  ..., `H12` (the 96-well plate convention).
- `name_pattern: "slot_{index}"` on a list of count 8 yields `slot_0`,
  `slot_1`, ..., `slot_7` (a tube-rack convention).
- `name_pattern: "lane_{row}"` on a 6x1 grid yields `lane_1`, `lane_2`, ...,
  `lane_6` (a single-column gel convention).

### Grouped targets are listed explicitly

Protocols list explicit subparts (for example `treatment_plate.A1`,
`treatment_plate.A2`, ..., `treatment_plate.A12`). The "subparts
belong to the object, not the scene" rule holds; the vocabulary has
no named-group construct.

### Subpart groups

A structured-grid object may declare additional addressable namespaces
over one underlying set of canonical cells through `structure.subpart_groups`.
This optional block allows authors to address a group of cells at a higher
granularity (a row, a column, or a plate region) instead of enumerating
every cell individually. The canonical cells generated by `name_pattern`
remain the primary namespace; subpart groups are additional overlays.

`structure.subpart_groups` is a mapping where each key is an author-chosen
snake_case label and each value is a group-kind mapping. Each group-kind
mapping carries:

| Field        | Type            | Required | Allowed                          | Default |
| ------------ | --------------- | -------- | -------------------------------- | ------- |
| `group_kind` | enum string     | yes      | one of `row`, `column`, `region` | none    |
| `members`    | list of mapping | yes      | non-empty list; see below        | none    |

Each member in the `members` list is a mapping with:

| Field      | Type           | Required | Allowed                                                            | Default |
| ---------- | -------------- | -------- | ------------------------------------------------------------------ | ------- |
| `name`     | string         | yes      | snake_case, unique within this object's all groups                 | none    |
| `contains` | list of string | yes      | non-empty list of canonical cell names generated by `name_pattern` | none    |

Authoring rules:

- `subpart_groups` is OPTIONAL. Objects that do not need group addressing
  simply omit the block.
- The `group_kind` enum is closed: `row | column | region`. No other
  group kinds are allowed without a separate architect memo and user
  ratification.
- Every cell name in a member's `contains` list must resolve to a canonical
  cell generated by `name_pattern`. The build pipeline rejects unknown cell
  names, duplicate member ids, and empty `contains` lists.
- Subpart groups are overlapping addressable overlays by design. One canonical
  cell may belong to any number of groups, including two groups of the same
  `group_kind`. This overlap is intended, not an error: `all_wells` (a `region`
  covering every cell) necessarily overlaps each `block_*` quadrant (also
  `region`), and every `row_*` overlaps every `col_*`. Group addressing is by
  member `name`, never by `group_kind`, so an overlapping cell is still
  addressed unambiguously. See
  [MATERIAL_STRUCTURED_AREAS.md](MATERIAL_STRUCTURED_AREAS.md) for the ratified
  cascade-write model these overlays serve.
- A `region` group kind addresses "the whole object" or "a contiguous semantic
  block of cells". A region member lists its cells explicitly in `contains`
  (each an existing canonical cell); it is NOT an open authoring surface for
  arbitrary runtime-computed selections.
- Subpart groups are only valid on structured-grid objects
  (`structure.layout: grid` or `structure.layout: list`). Flat objects
  have no subpart groups.
- A group member declared on a structured-grid object defines a new
  addressable target in the object's namespace, resolvable by the protocol
  side through the same dotted syntax used for canonical cells
  (e.g., `well_plate_96.row_A`, `well_plate_96.col_3`, `well_plate_96.all_wells`).

See [Subpart-addressing recommendation](../archive/subpart_addressing_recommendation.md)
for design rationale and usage patterns. The worked example below demonstrates
subpart groups on a 96-well plate.

## state_fields

`state_fields` is the typed schema of declared state variables on this
object. Every field is a flat primitive: `enum`, `int`, `float`, or
`bool`. There is no `string` type (use `enum` with a closed `allowed`
list) and no composite `liquid` or `set_point` type. Liquid materials
and instrument set-points are modeled as multiple flat fields per
object.

Every entry is a mapping with the required keys `field_name`, `type`,
`default`, plus per-type metadata and the optional `applies_to` and
`description`.

| Field         | Type           | Required | Allowed                                                | Default  |
| ------------- | -------------- | -------- | ------------------------------------------------------ | -------- |
| `field_name`  | string         | yes      | snake_case, unique within this object's `state_fields` | none     |
| `type`        | enum string    | yes      | one of `enum`, `int`, `float`, `bool`                  | none     |
| `default`     | matches `type` | yes      | must satisfy `type` and the per-type metadata below    | none     |
| `applies_to`  | enum string    | no       | one of `object`, `subpart`                             | `object` |
| `description` | string         | no       | one-line author-facing string                          | unset    |

`applies_to: subpart` is only valid when this object has a `structure`
block. Declaring `applies_to: subpart` on a flat object is a build-time
error. The form is equivalent to listing the same field under
`structure.subpart_state_fields`; an author may use either form.

### Per-type constraint metadata

Constraint metadata is a closed per-type set. Only the keys listed
below are allowed on a `state_field` entry; an unknown metadata key is
a build-time error. There is no open-ended `constraints:` object.

| `type`  | Allowed metadata keys (alongside `field_name`, `type`, `default`, `applies_to`, `description`)                                 |
| ------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `enum`  | `allowed` (non-empty list of strings, required); `default` is one value from `allowed`                                         |
| `int`   | `unit` (string), `min` (int), `max` (int), `step` (int); `default` is an int satisfying `min`/`max`/`step` when present        |
| `float` | `unit` (string), `min` (float), `max` (float), `step` (float); `default` is a float satisfying `min`/`max`/`step` when present |
| `bool`  | none beyond `default` (one of `true`, `false`)                                                                                 |

Unit strings for numeric fields are authored ASCII-only, per the repo-wide
rule in [../MARKDOWN_STYLE.md](../MARKDOWN_STYLE.md); non-ASCII characters are
written as HTML entities. Standard runtime units include `ml`, `ul`, `rpm`,
`C`, `s`, `min`. A Greek-letter unit (for example `&micro;l`) renders as its
Unicode glyph in the browser: see the "Glyph rendering" convention in
[MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md#glyph-rendering).

### Modeling material and set-point state with flat fields

Materials are modeled as several flat fields per object or per
subpart. The canonical pattern is `material_name` (an `enum` of allowed
material ids) and `material_volume` (a `float` with a `unit` and a range)
for a vessel; or `held_material_name` plus `held_material_volume` for a tool
that carries material. Material ids in the `enum`'s `allowed` list must
resolve to declared entries in a `materials.yaml` registry (see
[MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md)). The shared material
model is in [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md); render-rule
helpers (`fill_height`) are defined in the [formula
mini-language](#formula-mini-language) below.

Instrument set-points are modeled as a single `float` field with
`unit`, `min`, `max`, and `step` metadata (for example `set_volume`
on a serological pipette).

### Kind-to-material-field convention

The choice between `material_name` (vessel semantics) and `held_material_name`
(tool semantics) is closed per `kind`. The table below pins the convention for
each kind enum value. Authors must select one of these field-name pairs for
each kind; no kind permits both in the same file.

| `kind`       | Material field                                                                     | Semantics                                                                                                                                                                                                                                                                                               |
| ------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pipette`    | `held_material_name`, `held_material_volume`                                       | Tool that carries material between containers; held by cursor or in hand                                                                                                                                                                                                                                |
| `bottle`     | `material_name`, `material_volume`                                                 | Stationary container; sits in scene and holds material                                                                                                                                                                                                                                                  |
| `flask`      | `material_name`, `material_volume`                                                 | Stationary container; sits in scene and holds material                                                                                                                                                                                                                                                  |
| `waste`      | `material_name`, `material_volume`                                                 | Stationary container; collects discarded material                                                                                                                                                                                                                                                       |
| `rack`       | `material_name`, `material_volume` (per subpart)                                   | Structured container; subparts hold material in `structure.subpart_state_fields`                                                                                                                                                                                                                        |
| `plate`      | `material_name`, `material_volume` (per subpart)                                   | Structured container; subparts (wells) hold material in `structure.subpart_state_fields`                                                                                                                                                                                                                |
| `equipment`  | `material_name`, `material_volume` or `held_material_name`, `held_material_volume` | Equipment with internal chambers or containers. Case-by-case per equipment function: vessel-like equipment (staining tray, tank) uses `material_name` and MUST also declare `material_container` capability to affirm vessel semantics; tool-like equipment (aspirating head) uses `held_material_name` |
| `decoration` | N/A                                                                                | Static visual; no material state; `state_fields` must be empty                                                                                                                                                                                                                                          |

Material field naming is closed: these are the only two allowed field names across
all objects. An object declares material through either pair, never both together,
and always paired (never `material_name` without `material_volume` or vice versa).
A `state_field` with an unknown material-related name (for example
`container_material` or `liquid_type`) is a build-time error.

## Visual states

The `visual_states` is the object's state-to-visual function. It is a mapping
keyed by `state_field` name. For each named field, it declares how to
resolve the field's value to a visual output (an SVG asset name, an SVG
overlay name, or a composite of these). An object declares named closed
visual variants; `visual_states` is not a generic rendering map or
expression surface.

The `visual_states` is the only authoring surface in this format that names
SVG asset names or overlay names. An identity field, a `state_field`, a
capability, or a layout hint never names an asset name.

| Field                              | Type                  | Required                                                                            | Allowed                                                                        | Default  |
| ---------------------------------- | --------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------- |
| `visual_states.<field>.kind`       | enum string           | yes                                                                                 | one of `svg`, `overlay`, `composite`                                           | none     |
| `visual_states.<field>.cases`      | list of case mappings | required for `state_field.type` of `enum` or `bool`; forbidden for `int` or `float` | see [Cases schema](#cases-schema) below                                        | none     |
| `visual_states.<field>.formula`    | string                | required for `state_field.type` of `int` or `float`; forbidden for `enum` or `bool` | a string drawn from the closed [formula mini-language](#formula-mini-language) | none     |
| `visual_states.<field>.applies_to` | enum string           | no                                                                                  | one of `object`, `subpart`                                                     | `object` |

Every key in `visual_states` must name a declared `state_field` on this
object. A `visual_states` key with no matching `state_field` is a build-time
error. The reverse is also enforced: every `state_field` must have a
matching `visual_states` entry. A field whose value never affects the
visual is declared with an explicit `visual_states.<field>.kind: composite`
and an empty composite list so absence stays loud.

A `visual_states` entry for an `applies_to: subpart` `state_field` must
itself be `applies_to: subpart`. Mixing per-subpart state with per-object
rendering, or vice versa, is a build-time error.

### Cases schema

A `cases` list contains one case mapping per allowed value of the
`state_field`. Coverage is enforced: every value in the field's `allowed`
list must appear as a `when` value in exactly one case (for `bool`, both
`true` and `false` must be covered).

Every case mapping has the shape:

| Field    | Type                       | Required | Allowed                                 |
| -------- | -------------------------- | -------- | --------------------------------------- |
| `when`   | matches `state_field.type` | yes      | a value from the field's `allowed` list |
| `output` | mapping                    | yes      | one of the four output shapes below     |

The `output` mapping takes one of three shapes, matching the
`visual_states.<field>.kind`:

| `kind`      | `output` shape                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------------- |
| `svg`       | `{asset_name: <asset_name>}` -- one asset name resolved by the SVG pipeline                       |
| `overlay`   | `{overlay_name: <overlay_name>}` -- one SVG fragment name composited over the base                |
| `composite` | `{composite: [<output mapping>, ...]}` -- a non-empty ordered list of any of the two shapes above |

A composite list is rendered top to bottom; the first entry is the base
layer and each subsequent entry composites over the previous.

### Complete-form selection and material binding

The `kind: svg` case maps are the sole object-YAML authority for selecting
complete SVG forms. A one-case map selects a single form; the forms selected
by a state field's complete case map are a discrete-state collection. No
collection manifest is authored, and filenames or directories do not define a
collection.

The selected SVG form alone determines its rendering model: exact root
`data-vlab-rendering="material"` dispatches to the compiled material path;
the absence of that declaration identifies a static opaque form. Selection and
rendering are independent, so one collection can include both static and
material-rendered forms. Object YAML never declares a rendering model, semantic
layer, or SVG recipe. See [SVG_PIPELINE.md](SVG_PIPELINE.md) for the per-form
asset contract.

Paired material identity and amount entries remain the object material binding
authority. Object-level `fill_height` with `anchor_liquid_bounds`, optional
`anchor_liquid_clip`, and exactly one matching capacity value drives the
compiled material SVG's role paint and derived gravity-part transform. These
values are compiler and manifest inputs; no `liquid_region`, binding token, or
target token is added to this schema.

Object YAML must not name `layer_name`, `paint_role`, `adjustment`, stacking
phase, runtime handles, DOM ids, or SVG-recipe sidecars. Runtime material code
does not query authored `data-vlab-*` through object declarations. Numeric
`label(...)` remains an object-level overlay and does not make arbitrary SVG
internals mutable.

An object material binding makes its selected form require inline, injected
SVG DOM regardless of an empty material value. `requires_dom_svg` is derived
by the renderer from the selected form and binding; it is not an object-YAML
field.

### Formula mini-language

A `formula` value is a string drawn from a closed mini-language. The
mini-language is intentionally narrow: every token is fixed by this format
and the runtime resolves it. Per-object formula code is not allowed; if a
state-to-visual mapping cannot be expressed in the tokens below, the
correct response is to extend the mini-language in a future revision of
this doc, not to embed code in an object file.

The closed token set is:

| Token                                                      | Operand types                                                                                              | Meaning                                                                                                                                                                          |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `state(<field_name>)`                                      | any `int` or `float` `state_field` declared on this object                                                 | the current numeric value of the named field                                                                                                                                     |
| `const(<number>)`                                          | numeric literal                                                                                            | a literal number (decimal or integer)                                                                                                                                            |
| `const(<string>)`                                          | string literal                                                                                             | a literal string in double quotes                                                                                                                                                |
| `+` `-` `*` `/`                                            | numeric operands                                                                                           | basic arithmetic, left-associative                                                                                                                                               |
| `min(a, b)` `max(a, b)`                                    | numeric operands                                                                                           | bounded arithmetic                                                                                                                                                               |
| `clamp(value, lo, hi)`                                     | numeric operands                                                                                           | clamp `value` to `[lo, hi]`                                                                                                                                                      |
| `fill_height(state(<volume_field>), capacity_ml=<number>)` | a numeric volume `state_field` (typically a `float` named `material_volume`, `held_material_volume`, etc.) | bind volume to compiled material-SVG gravity parts using the matching capacity, or to generated geometry for an intentional structured-subpart binding, as defined in [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) |
| `label(state(<numeric_field>), format=<string>)`           | a numeric `state_field` (typically a set-point `float`)                                                    | render the value as an overlay text label, using the format string with `{value}` placeholder; the format string supplies the unit text                                          |
| `conditional(<cond>, <then>, <else>)`                      | `cond` is `state(<field>)` or a string literal; `then` and `else` are each a string literal or a nested `label(...)` token | choose `then` when `cond` is truthy, else `else`; a `bool` field is truthy when `true`, a numeric field when nonzero, an enum/string field when non-empty and not the `empty` sentinel; the chosen branch resolves to its overlay |
| `compose(<token>, <token>, ...)`                           | any of the above                                                                                           | compose multiple effects (for example a fill plus a label) into one render output; ordered top to bottom                                                                         |

A formula is one expression. Multiple expressions are composed through
`compose(...)`, not by concatenation or by multi-line strings.

This is the complete token set. An unknown token, an arity mismatch
(wrong number of operands), or a type mismatch (for example `fill_height`
applied to a non-numeric field) is a build-time error.

Worked formula examples appear in the [worked-example sections](#worked-example-96-well-plate)
below.

## Capabilities

`capabilities` is a list of affordance tags drawn from the closed
vocabulary owned by [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md). The
list may be empty. An object may not invent capabilities; adding a
capability value requires an explicit edit to the vocabulary doc.

The closed list (with the meaning summary; the vocabulary doc is the
authority):

| Capability                 | Summary                                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `clickable`                | accepts a `click` gesture                                                                                                                       |
| `material_container`       | holds tracked material; expects flat material `state_fields` such as `material_name` and `material_volume` and matching `visual_states` entries |
| `instrument_with_setpoint` | exposes one or more numeric set-point `state_fields` (typically `float` with `unit`, `min`, `max`); expects an `adjust` gesture                 |
| `structured_surface`       | has a `structure` block with subparts                                                                                                           |
| `cursor_attachable`        | may be attached to the cursor by a `CursorAttach` `scene_operation`                                                                             |
| `decoration_only`          | rendered as a static visual; accepts no gestures and no state mutation                                                                          |

### Mutual-exclusion rule

`decoration_only` is mutually exclusive with `clickable`,
`material_container`, `instrument_with_setpoint`, `structured_surface`,
and `cursor_attachable`. An object that declares `decoration_only` may
not declare any of the other five; an object that declares any of the
other five may not declare `decoration_only`. The build pipeline
enforces this rule and rejects a violating capability list.

The five non-decoration capabilities are otherwise freely combinable. A
96-well plate is `[clickable, structured_surface, material_container]`; a
serological pipette is `[clickable, material_container,
instrument_with_setpoint, cursor_attachable]`; a benchtop label is
`[decoration_only]`.

### Capability-to-schema dependencies

When a capability is declared, the rest of the object schema must support
it. The dependencies are:

| Capability                 | Required schema                                                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `material_container`       | at least one material `state_field` (typically a `material_name` `enum` and a `material_volume` `float`) and matching `visual_states` entries              |
| `instrument_with_setpoint` | at least one numeric set-point `state_field` (a `float` with `unit`, `min`, `max`) and a matching `visual_states` entry                                    |
| `structured_surface`       | a `structure` block with `subpart_kind`, `layout`, and `name_pattern`                                                                                      |
| `cursor_attachable`        | no schema dependency (an object that is cursor-attachable simply declares it; the protocol-level `CursorAttach` `scene_operation` consumes the capability) |
| `clickable`                | no schema dependency (every object that is clickable simply declares it)                                                                                   |
| `decoration_only`          | the object's `state_fields` list is empty and the `visual_states` mapping is empty (a decoration carries no declared state and no state-driven rendering)  |

A capability declared without its required schema is a build-time error.

### Channel addressing

Pipette objects may declare optional multi-channel capability metadata
through a `channel_addressing` block (a sibling to the `capabilities`
list, not nested within it). This block describes the pipette's channel
configuration and which subpart group kinds it can address.

`channel_addressing` is a mapping with the following fields:

| Field                       | Type                | Required | Allowed                                   | Default |
| --------------------------- | ------------------- | -------- | ----------------------------------------- | ------- |
| `channels`                  | int                 | yes      | positive integer (typically 1, 8, or 12)  | none    |
| `addressable_subpart_kinds` | list of enum string | yes      | non-empty subset of `[well, row, column]` | none    |

Authoring rules:

- `channel_addressing` is OPTIONAL. A pipette object without this block
  defaults to single-channel, well-only addressing (the safe fallback that
  matches historical behavior).
- The `channels` field indicates how many simultaneously-dispensing channels
  the pipette has. A single-channel pipette is `channels: 1`; an 8-channel
  multichannel is `channels: 8`; a 12-channel multichannel is `channels: 12`.
- The `addressable_subpart_kinds` list declares which group kinds (declared
  via [subpart groups](#subpart-groups) on target objects) this pipette may
  address. A single-channel pipette typically lists `[well]`. An 8-channel
  multichannel typically lists `[well, column]`. A 12-channel multichannel
  typically lists `[well, row]`.
- The `region` group kind is intentionally NOT included in any pipette's
  `addressable_subpart_kinds`. Region addressing is reserved for hand-liquid
  addition (bottle, reservoir, bulk reagent dispense) and is incompatible
  with channeled pipettes.
- The stepper validates that when a pipette acts on a subpart-group target,
  the target's `group_kind` is present in the pipette's
  `addressable_subpart_kinds`. If not, the stepper emits an ERROR.

See [Subpart-addressing recommendation](../archive/subpart_addressing_recommendation.md)
for design rationale and usage patterns. The worked example below demonstrates
`channel_addressing` on single-channel and multichannel pipettes.

## Layout hints

`layout` is a mapping of object-default visual metrics the layout engine
([LAYOUT_ENGINE.md](LAYOUT_ENGINE.md)) consumes when a scene places the
object. A scene placement may override every field in the `layout` block.

| Field                    | Type        | Required | Allowed                           | Default                                            |
| ------------------------ | ----------- | -------- | --------------------------------- | -------------------------------------------------- |
| `layout.default_width`   | float       | yes      | positive number, in layout units  | none                                               |
| `layout.label_width`     | float       | no       | positive number, in layout units  | unset; layout engine falls back to `default_width` |
| `layout.anchor_y_offset` | float       | no       | any number (positive or negative) | `0`                                                |
| `layout.width_scale`     | float       | no       | positive number                   | `1.0`                                              |
| `layout.anchor_y`        | enum string | no       | one of `bottom`, `tip`, `top`     | `bottom`                                           |

`layout` itself is required; `layout.default_width` is the only required
sub-field. The other sub-fields are optional and fall through to the
defaults listed above. `layout.anchor_y: top` is an engine fallback that
centers the object vertically on the shared row baseline; no current object
authors it. See [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) "Anchor-coordinate
convention" for the three modes and their `_top` formulas.

## Worked example: 96-well plate

The 96-well plate is the canonical example for structured surfaces,
per-subpart flat-primitive `state_fields`, the `structured_surface`
capability, and per-subpart `visual_states` entries.

```yaml
object_name: well_plate_96
kind: plate
label: 96-well plate

structure:
  subpart_kind: well
  layout: grid
  rows: 8
  cols: 12
  name_pattern: "{row_letter}{col}"
  subpart_groups:
    rows:
      group_kind: row
      members:
        - name: row_A
          contains: [A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12]
        - name: row_B
          contains: [B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12]
        - name: row_C
          contains: [C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12]
        - name: row_D
          contains: [D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12]
        - name: row_E
          contains: [E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12]
        - name: row_F
          contains: [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12]
        - name: row_G
          contains: [G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12]
        - name: row_H
          contains: [H1, H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12]
    columns:
      group_kind: column
      members:
        - name: col_1
          contains: [A1, B1, C1, D1, E1, F1, G1, H1]
        - name: col_2
          contains: [A2, B2, C2, D2, E2, F2, G2, H2]
        - name: col_3
          contains: [A3, B3, C3, D3, E3, F3, G3, H3]
        - name: col_4
          contains: [A4, B4, C4, D4, E4, F4, G4, H4]
        - name: col_5
          contains: [A5, B5, C5, D5, E5, F5, G5, H5]
        - name: col_6
          contains: [A6, B6, C6, D6, E6, F6, G6, H6]
        - name: col_7
          contains: [A7, B7, C7, D7, E7, F7, G7, H7]
        - name: col_8
          contains: [A8, B8, C8, D8, E8, F8, G8, H8]
        - name: col_9
          contains: [A9, B9, C9, D9, E9, F9, G9, H9]
        - name: col_10
          contains: [A10, B10, C10, D10, E10, F10, G10, H10]
        - name: col_11
          contains: [A11, B11, C11, D11, E11, F11, G11, H11]
        - name: col_12
          contains: [A12, B12, C12, D12, E12, F12, G12, H12]
    plate_region:
      group_kind: region
      members:
        - name: all_wells
          contains:
            [
              A1,
              A2,
              A3,
              A4,
              A5,
              A6,
              A7,
              A8,
              A9,
              A10,
              A11,
              A12,
              B1,
              B2,
              B3,
              B4,
              B5,
              B6,
              B7,
              B8,
              B9,
              B10,
              B11,
              B12,
              C1,
              C2,
              C3,
              C4,
              C5,
              C6,
              C7,
              C8,
              C9,
              C10,
              C11,
              C12,
              D1,
              D2,
              D3,
              D4,
              D5,
              D6,
              D7,
              D8,
              D9,
              D10,
              D11,
              D12,
              E1,
              E2,
              E3,
              E4,
              E5,
              E6,
              E7,
              E8,
              E9,
              E10,
              E11,
              E12,
              F1,
              F2,
              F3,
              F4,
              F5,
              F6,
              F7,
              F8,
              F9,
              F10,
              F11,
              F12,
              G1,
              G2,
              G3,
              G4,
              G5,
              G6,
              G7,
              G8,
              G9,
              G10,
              G11,
              G12,
              H1,
              H2,
              H3,
              H4,
              H5,
              H6,
              H7,
              H8,
              H9,
              H10,
              H11,
              H12,
            ]

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
    applies_to: subpart
    render_effect: material_tint
    target: subpart_geometry
  material_volume:
    kind: composite
    applies_to: subpart
    formula: fill_height(state(material_volume), capacity_ul=300)

capabilities: [clickable, structured_surface, material_container]

layout:
  default_width: 14
  label_width: 8
```

Reading: the plate has no plate-level state, 96 wells (`A1..H12`) each
carrying two flat `state_fields` (`material_name`, `material_volume`).
The `subpart_groups` block declares three overlapping namespaces: 8 rows
(`row_A` through `row_H`), 12 columns (`col_1` through `col_12`), and one
region (`all_wells`). A protocol that acts on a single row may address
`treatment_plate.row_A` instead of enumerating 12 individual wells; a
protocol that reads the entire plate may address `treatment_plate.all_wells`
in one target. Individual well addressing (`treatment_plate.A1`,
..., `treatment_plate.A12`) remains available for fine-grained protocols.
Each well's `visual_states` resolves the two flat fields independently: the
existing `material_tint` / `subpart_geometry` binding for identity and a
`fill_height(...)` formula for volume. No SVG asset name appears in any
`state_field`.

## Worked example: serological pipette

The serological pipette is the canonical example for flat-primitive
`state_fields` on a flat object, the `instrument_with_setpoint` and
`cursor_attachable` capabilities, the `label(...)` formula token, and
the `anchor_y: tip` layout hint.

```yaml
object_name: serological_pipette
kind: pipette
label: Serological pipette

state_fields:
  - field_name: set_volume
    type: float
    unit: ml
    min: 0.1
    max: 25.0
    step: 0.1
    default: 1.0
    description: Volume the pipette is set to dispense.
  - field_name: held_material_name
    type: enum
    allowed: [empty, pbs, media, trypsin, dmso]
    default: empty
    description: Material currently aspirated in the pipette barrel.
  - field_name: held_material_volume
    type: float
    unit: ml
    min: 0
    max: 25.0
    default: 0
    description: Volume of material currently held, in milliliters.

visual_states:
  set_volume:
    kind: overlay
    formula: label(state(set_volume), format="{value} ml")
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
      - when: dmso
        output: { asset_name: serological_pipette }
  held_material_volume:
    kind: composite
    formula: fill_height(state(held_material_volume), capacity_ml=25.0)

capabilities:
  [clickable, material_container, instrument_with_setpoint, cursor_attachable]

layout:
  default_width: 3
  label_width: 6
  anchor_y: tip
  anchor_y_offset: 0
```

Reading: the pipette is a flat object (no `structure` block, no
subparts). It declares three flat `state_fields`: `set_volume` (a
`float` with `unit`, `min`, `max`, and `step`), `held_material_name` (an
`enum` of which material is loaded), and `held_material_volume` (a `float`
for the amount held). The `visual_states` resolves each independently:
the set-point becomes an overlay label, every material case selects the same
complete pipette form, and the volume becomes a fill height. No SVG asset name
appears in any `state_field`. The layout hints (`default_width: 3`, `label_width: 6`,
`anchor_y_offset: 0`, `anchor_y: tip`) are object-owned; the tip anchor
reflects that a serological pipette is tip-anchored wherever it is
placed. This pipette has no `channel_addressing` block, so it defaults to
single-channel, well-only addressing.

### Worked example: 8-channel multichannel pipette

An 8-channel multichannel pipette declares `channel_addressing` to indicate
multi-channel capability and column-level addressability:

```yaml
object_name: multichannel_8ch
kind: pipette
label: 8-channel pipette

state_fields:
  - field_name: set_volume
    type: float
    unit: ul
    min: 10
    max: 200
    step: 1
    default: 50
    description: Volume the pipette is set to dispense per channel.
  - field_name: held_material_name
    type: enum
    allowed: [empty, pbs, media, trypsin]
    default: empty
    description: Material aspirated across all channels.
  - field_name: held_material_volume
    type: float
    unit: ul
    min: 0
    max: 200
    default: 0
    description: Volume held per channel, in microliters.

visual_states:
  set_volume:
    kind: overlay
    formula: label(state(set_volume), format="{value} ul")
  held_material_name:
    kind: svg
    cases:
      - when: empty
        output: { asset_name: pipette_8ch_empty }
      - when: pbs
        output: { asset_name: pipette_8ch_filled }
      - when: media
        output: { asset_name: pipette_8ch_filled }
      - when: trypsin
        output: { asset_name: pipette_8ch_filled }
  held_material_volume:
    kind: composite
    formula: fill_height(state(held_material_volume), capacity_ul=200)

capabilities:
  [clickable, material_container, instrument_with_setpoint, cursor_attachable]

channel_addressing:
  channels: 8
  addressable_subpart_kinds: [well, column]

layout:
  default_width: 8
  label_width: 12
  anchor_y: tip
```

Reading: the 8-channel multichannel declares `channel_addressing` with
`channels: 8` and `addressable_subpart_kinds: [well, column]`. This pipette
may address a plate's wells individually (single-channel behavior) or
column groups (8-channel behavior on a 96-well plate). When targeting a
column group like `plate.col_3`, the stepper validates that the pipette's
`addressable_subpart_kinds` includes `column`. If a protocol erroneously
tried to use this pipette on a `row` group, the stepper emits an ERROR
because `row` is not in the pipette's allowed kinds.

## Cross-file validation rules

The build pipeline (a follow-on plan deliverable) enforces these rules at
build time. A violating object file fails the build loudly; this format
does not specify defensive defaults that hide a missing required field.

### Identity

- The object's `object_name` equals the filename without the `.yaml` extension.
- `object_name` is unique across the object library.
- `kind` is one of the eight values in [Object identity](#object-identity).

### Structure

- `structure.layout: grid` requires `rows` and `cols`; `layout: list`
  requires `count`; any other value is rejected.
- Every token in `structure.name_pattern` is in the closed token set; arity
  matches the layout (`{row_letter}` and `{row}` only valid for grid;
  `{index}` only valid for list).
- `structure` accepts only the fields declared above; unknown keys are
  rejected. The vocabulary has no named-group construct.
- If `structure.subpart_groups` is present, every group member's `contains`
  list must reference only canonical cell names generated by this object's
  `name_pattern`. Unknown cell names are rejected.
- Within a single `group_kind`, no cell may appear in more than one group
  member's `contains` list. Overlapping membership within a `group_kind` is
  a build-time error.
- Every group member must have a unique `name` across all groups in all
  group kinds. Duplicate member names are rejected.
- Subpart groups are only valid when `structure` has `layout: grid` or
  `layout: list`. Groups on flat objects are rejected.

### Cascade-write rule (ObjectStateChange on group targets)

When a protocol's `ObjectStateChange` interaction targets a group member
(e.g., `well_plate_96.row_A`), the state change writes both the group
member's own subpart-state record AND propagates every declared field in
the change to every canonical cell named in the group member's `contains`
list.

- The write is cascade: the group member is updated, and then each cell in
  `contains` is updated with only the fields explicitly named in the change
  payload. Unmentioned fields are not cleared or reset.
- The stepper validates at write time that every group member exists, every
  cell in `contains` accepts the named field per the object's
  `state_fields`, and no per-cell write conflict occurs (same cell named by
  overlapping groups in one step is a build-time error).
- A pipette object with `channel_addressing` is validated: if the pipette
  acts on a group target whose `group_kind` is not in the pipette's
  `addressable_subpart_kinds`, the stepper emits an ERROR.

### state_fields

- Every `state_field.name` is unique within this object's
  `state_fields`.
- `type` is one of `enum`, `int`, `float`, `bool`.
- Per-type metadata satisfies the [closed metadata rules](#per-type-constraint-metadata)
  above; unknown metadata keys are rejected.
- `default` is present and satisfies the type and metadata.
- `applies_to: subpart` is only valid when the object has a `structure`
  block.
- For material `enum` fields (typically `material_name`), material ids in
  `allowed` must resolve to declared entries in a material registry.

### visual_states

- Every `visual_states` key matches a declared `state_field` name.
- Every declared `state_field` has a matching `visual_states` entry (a
  field with no visual effect declares an explicit
  `visual_states.<field>.kind: composite` with an empty composite list).
- For `enum` and `bool` `state_fields`, every value in the field's
  `allowed` list appears in exactly one `cases[].when`.
- For `int` and `float` `state_fields`, the `formula` string parses
  against the closed [formula mini-language](#formula-mini-language).
- A `visual_states` entry for an `applies_to: subpart` `state_field` is
  itself `applies_to: subpart`.
- Each `kind: svg` `cases` map is the complete-form selection authority.
  Object YAML does not infer collections from filenames or directories, and
  does not declare a material rendering model or SVG internals.
- An object-level material identity/amount binding may use `fill_height` with
  `anchor_liquid_bounds`, optional `anchor_liquid_clip`, and exactly one
  matching capacity value. Those compiler inputs drive the selected
  material SVG's compiled manifest path. Structured-subpart bindings use
  generated geometry instead.

### capabilities

- Every entry is in the closed six-value capability list: `clickable`,
  `material_container`, `instrument_with_setpoint`, `structured_surface`,
  `cursor_attachable`, `decoration_only`.
- `decoration_only` is mutually exclusive with the other five.
- Every declared capability's
  [schema dependency](#capability-to-schema-dependencies) is satisfied.

### layout

- `layout.default_width` is set and positive.
- Optional sub-fields, when present, satisfy their type and range rules.

### Hygiene

- ASCII-only across the file; UTF-8 glyphs are escaped per
  [../MARKDOWN_STYLE.md](../MARKDOWN_STYLE.md) (for example `&micro;`); codegen
  decodes each entity to its Unicode glyph for display, per the "Glyph
  rendering" convention in
  [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md#glyph-rendering).
- Snake_case is used for every id (`id`, `state_field.name`, reagent
  ids).

## Generated TypeScript surface

The build pipeline compiles the object library into a generated TypeScript
module. This format doc does not specify the runtime shape of that module; the
protocol-side analogue (the per-protocol generated module described in
[PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md)) is the closest
reference. The runtime never reads object YAML directly; it reads the
generated module the build emits.

## See also

- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) -- the canonical object
  vocabulary; this doc encodes its YAML schema.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) -- the scene-side
  vocabulary; the scene names objects by `object_name`.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) -- the scene YAML schema;
  scene placements consume the override surface this format declares.
- [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md) -- the protocol
  vocabulary, including the `ObjectStateChange` primitive that mutates
  declared object state.
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md) -- the protocol
  YAML schema; material ids referenced by `material_name` `state_fields`
  are declared in a material registry.
- [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) -- the layout engine that
  consumes object-side layout hints.
- [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) -- the shared material
  model that the material `state_field` type and the `fill_height` formula
  token build on.
- [SVG_PIPELINE.md](SVG_PIPELINE.md) -- the SVG asset pipeline; the
  `visual_states` resolves to asset names the pipeline owns.
- [../MARKDOWN_STYLE.md](../MARKDOWN_STYLE.md) -- ASCII-only and escaping
  rules for YAML and markdown.
