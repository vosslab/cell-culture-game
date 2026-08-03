# Material vocabulary

This document is the canonical vocabulary for the material system: material
authoring in `materials.yaml`, the material-side validators, the color
resolver, and every material-related comment, error message, and authoring
guide in this repository. Every material-related doc, code comment, error
message, validator output, and authoring guide must use these exact terms
with these exact meanings.

Material is the fourth authoring vocabulary, alongside protocol, object, and
scene. The protocol side names what happens; the object side names what a
thing is and how its state appears; the scene side names where things appear;
the material side names what is inside, held by, produced by, or removed from
objects, and what color that substance renders. The protocol-side counterpart
is [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md); the object-side
counterpart is [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md); the scene-side
counterpart is [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).

This doc names the vocabulary and settles the sentinel/visible classification.
The exact `materials.yaml` file schema (keys, required fields, hex format,
registry scope) lives in [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md). The
runtime rendering convention (render effects, targets, fill behavior) lives in
[MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md). The design rationale lives in
[MATERIAL_DESIGN.md](MATERIAL_DESIGN.md). The validator and cross-YAML
rules live in `MATERIAL_LINT.md`. This doc names terms
and classification; it does not encode schema mechanics, rendering mechanics,
or lint rules.

## What a material is

A **material** is anything physically present in, on, produced by, removed
from, or transferred between objects. Reagents, growth media, cells, mixtures,
suspensions, diluted drugs, assay products, and waste streams are all
materials. Liquid is the most common physical form, but the vocabulary is not
liquid-bound: a future powder, solid, or gel material is named the same way
and carries the same fields.

A material is distinct from an object. An **object** is an interactable
rendered thing (a flask, a bottle, a pipette, a well). A material is what an
object can hold, contain, receive, produce, or discard. A bottle is an object;
PBS is a material; a PBS bottle is an object whose `material_name` state field
resolves to `pbs`. The full object boundary is in
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).

## Material identity and material state

A material has two separable aspects, and they are different layers:

- **Material identity** is *what* the material is: its name and its color.
  Identity answers "is this well PBS, media, or carboplatin?" Identity is
  carried by the `material_name` state field (or `held_material_name` on a
  tool) and renders as the material's color.
- **Material state** is the runtime condition of a material inside one object
  at one moment: the value of an object's `material_name` plus
  `material_volume` fields (or `held_material_name` plus `held_material_volume`
  on a tool). Material state is per-object (and per-subpart for a structured
  surface); the same material identity can be present in many objects at once.

Identity is authored once per material in `materials.yaml`. State is set per
object by the protocol through `ObjectStateChange` (defined in
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)). The amount of material
(`material_volume`) is part of material state but is not part of material
identity: volume changes how much fill shows, never what color it is.

## Material name

A **material name** is the snake_case identifier that names a material
identity. It is the value an object's `material_name` (or `held_material_name`)
state field takes, and it is the key under which a visible material is
registered in `materials.yaml`. A material name names a substance or a state
marker; it never names a color, an asset, or a volume. Protocol YAML and object
YAML write a material name; they never write a hex color.

The set of material names is not a single global closed enum. It is the union
of the sentinel allowlist (closed, defined below) and the material names
registered in the active protocol's material registry (open per protocol, but
each registration is a closed schema entry). This is the registry-backed model:
the curriculum owns its treatments by registering them, and a shared object
such as `well_plate_96` does not enumerate every drug.

## Display color

`display_color` is the authored field that gives a visible material its color.
It is a **single scalar hex string** (for example `"#a719db"`), not a nested
mapping. There is no `light`/`dark` split and no theme branch: this project
targets light scientific workspaces only, and the one scalar color is used for
all rendering. The exact hex format and validation live in
[MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md); the rule that the resolver reads only the scalar
form lives in [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).

`display_color` is the sole source of material color. Color comes from the
material registry, never from protocol YAML, object YAML, scene YAML, or
TypeScript. Adding a new material color is a `materials.yaml` edit, not a code
or asset change.

## Material identity versus SVG recipe

The protocol material registry and an SVG's rendering recipe are different
vocabularies with different owners. `materials.yaml` names a material and gives
it a `label` and `display_color`. Object `visual_states` bind material identity
and amount state to an object form. A material-rendered SVG describes only its
own semantic regions; it contains no material name or color and has no YAML
sidecar. The exact SVG contract belongs to [SVG_PIPELINE.md](SVG_PIPELINE.md).
For variable-volume vessels, material regions use the closed optional gravity
parts `bottom`, `body`, and `surface`. A form may also own a closed maximum fill
percent as reviewed vessel geometry; this ceiling never comes from material,
object, or protocol YAML.

The pipeline derives a liquid-region manifest from normalized semantic SVG
structure. That manifest provides opaque runtime handles and is generated data,
not authored material content. One SVG recipe can therefore render any material
identity from any protocol registry without a material-specific variant.

## Material condition is a separate material

A material's **condition** -- fresh versus old, clean versus dirty, unused
versus spent, unreacted versus reacted -- is expressed as a separate material
name with its own scalar `display_color`, not as an alternate color mode of one
material. `media` and `spent_media` are two materials; `mtt` and `formazan`
(the reacted product) are two materials; a fresh buffer and its waste stream
are two materials. There is no condition flag, no palette mode, and no nested
color variant on a single material. This keeps `display_color` a single scalar
and keeps each visible condition independently colorable and independently
nameable by the protocol.

## Sentinel

A **sentinel** is a material name that carries no registered material identity
and is exempt from registration in `materials.yaml`. A sentinel is a state
marker, not a substance: it names a condition of the container rather than a
chemical or biological thing inside it. The sentinel allowlist is a closed set
owned by this doc; an author cannot add a sentinel by editing YAML.

The closed sentinel allowlist is exactly two values:

| Sentinel | Renders | Meaning |
| --- | --- | --- |
| `empty` | no fill (transparent) | The container holds no material. Base object art shows through. |
| `mixed` | a color | A generic blended material whose specific identity is not tracked. |

`empty` is the only **non-rendering** sentinel: a well or vessel whose
`material_name` is `empty` (or whose `material_volume` is `0`) renders no fill,
and the base object art shows through unchanged (no neutral ring, no gray
placeholder). Every other material name -- including the sentinel `mixed` --
resolves to a color.

`mixed` is a sentinel because it carries no tracked identity (you cannot say
which reagents it is), but it is still a visible material: it must resolve to a
color. Because `mixed` is not registered in `materials.yaml`, its color is a
spec-defined built-in (see "Built-in visual identity" below); it never renders
invisible.

## Visible material

A **visible material** is any material name that resolves to a color and
therefore shows fill when present in a non-empty, non-zero-volume container.
Every material name except `empty` is a visible material. A visible material
gets its color through exactly one of two mechanisms:

- **Registry-backed.** The material name is registered in the active protocol's
  `materials.yaml` with a `label` and a scalar `display_color`. This is the
  default and the strongly preferred mechanism for every named substance.
- **Built-in visual identity.** The material name is one of the small,
  spec-defined set whose color is fixed in the spec rather than authored per
  protocol (today, only the sentinel `mixed`). A built-in is not registered in
  `materials.yaml`.

The binding invariant (D2): with an active, provided material registry, a
non-`empty`, non-built-in material name that resolves to no color is a resolver
error, never a silent invisible "success". The error is surfaced by the color
resolver (see "Color resolver" below), never papered over with a fallback color
or an invisible well. A null registry is instead the explicitly bounded
no-protocol-color-context case used for diagnostic or unseeded rendering; it is
not registry acceptance.

## Material registry

The **material registry** is the set of visible materials authored in one
protocol's `materials.yaml` file. The registry is per protocol: each protocol
package owns its own `content/protocols/<cluster>/<protocol_name>/materials.yaml`,
and a material name resolves against the active protocol's registry, not a
global table. The registry holds only registry-backed visible materials;
sentinels and built-ins are not registry entries. The registration check (the
stepper's `s-unregistered` gate) requires that every non-sentinel, non-built-in
material name written by the protocol appears in that protocol's registry. The
exact file schema is in [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md); the registration rule is in
`MATERIAL_LINT.md`.

## Mixture

A **mixture** is a visible material produced by combining two or more input
materials. A mixture is a normal visible material: it has its own material name
and its own scalar `display_color`. There are two ways a mixture is named:

- **Tracked mixture.** The combined material has a known, curriculum-relevant
  identity, so it is registered in `materials.yaml` under its own name with its
  own color. Example: `carboplatin_metformin_combo` (a registered material with
  `display_color: "#b84db8"`). A tracked mixture is registry-backed.
- **Untracked mixture.** The combined material's specific identity does not
  matter to the lesson, so it is named with the sentinel `mixed`. An untracked
  mixture is a built-in (the `mixed` sentinel color).

Mixtures are not a separate vocabulary surface and have no `mix(...)` field, no
component list, and no nesting. A mixture is just a material name (registered or
the `mixed` sentinel) the protocol writes with `ObjectStateChange`, exactly
like any other material.

## Waste

A **waste** material is a visible material that names a disposal stream rather
than a usable reagent. Waste materials follow the normal visible-material rule:
each waste stream the protocol writes is registered in `materials.yaml` under
its own material name with its own scalar `display_color` (for example
`waste_mtt`, `waste_media`). Waste is not a sentinel class and is not exempt
from registration. A waste stream that a protocol writes but does not register
is a registration error, the same as any other unregistered visible material.
Naming waste streams separately (rather than collapsing them into one `waste`)
lets the curriculum color and track each stream distinctly.

## Transfer

A **transfer** is moving material between two objects: a tool picks material up
from a source and discharges it into a destination. A transfer is authored as
protocol interactions whose `response` carries `ObjectStateChange` operations
on the source, the tool, and the destination state fields; the material side
contributes only the vocabulary (`material_name`, `material_volume`,
`held_material_name`, `held_material_volume`) the transfer reads and writes.
Transfer is not a material-side primitive and has no `transfer(...)` field; the
protocol vocabulary owns the act, and the material vocabulary owns the named
substance being moved. Discharging PBS from a pipette into well A1 is one
protocol interaction whose `response` clears the tool's `held_material_name`
and sets the well's `material_name: pbs` and `material_volume`.

## When a biological thing is a visible material

The binding rule for biological things such as `cells`: a biological thing is a
**visible material** -- registered like any reagent -- exactly when a protocol
writes it into an object's `material_name` (or `held_material_name`) state
field. If a protocol can put cells into a well and the student must see which
wells hold cells, then `cells` is a visible material with a registered scalar
`display_color`, not a sentinel and not an intrinsic, unrendered property.

This is the same binding test that classifies every material name:

> If a protocol writes the name into a `material_name` /
> `held_material_name` field and it is not `empty`, it is a visible material
> and must resolve to a color (registry-backed by default; built-in only for
> the closed `mixed` case).

`cells`, `formazan` (and `formazan_dmso_solution`), `mtt`, and the waste
streams all pass this test and are therefore visible registry-backed materials,
not sentinels. The only material names that are not visible materials are the
two sentinels, and of those only `empty` does not render.

## Settled sentinel/visible classification (D2 boundary)

This table settles the D2 sentinel/visible boundary for every material value
the audit found written into `well_plate_96` wells, plus the two sentinels. The
deciding rule is the binding test above: `empty` is the only non-rendering
sentinel; `mixed` is the only built-in visible material; every other written
material name is a registry-backed visible material that must appear in the
active protocol's `materials.yaml` with a scalar `display_color`.

| Material name | Class | Renders | Deciding rule |
| --- | --- | --- | --- |
| `empty` | sentinel | no (transparent) | The only non-rendering sentinel; names "no material present"; base art shows through. |
| `mixed` | built-in (sentinel) | yes (built-in color) | Sentinel: carries no tracked identity; but a non-`empty` material renders, so its color is a spec-defined built-in, not a registry entry. |
| `media` | registry-backed visible | yes | Names a substance written into wells; registered with a scalar `display_color`. |
| `cells` | registry-backed visible | yes | A biological thing written into `material_name`; passes the binding test; registered with a scalar `display_color`. |
| `formazan_dmso_solution` | registry-backed visible | yes | The MTT assay product in DMSO, written into wells; registered with a scalar `display_color`. |
| `formazan` | registry-backed visible | yes | The MTT assay product (crystal precipitate), written into wells; registered with a scalar `display_color`. A separate material from `mtt` (condition rule: reacted product is its own material). |
| `waste_mtt` | registry-backed visible | yes | A named disposal stream written into wells; waste is not a sentinel; registered with a scalar `display_color`. |
| `waste_media`, `waste_drug`, `waste_buffer` | registry-backed visible | yes | Named disposal streams; same rule as `waste_mtt`; each registered separately when a protocol writes it. |
| `carboplatin` | registry-backed visible | yes | A named drug written into wells; registered with a scalar `display_color`. |
| `carboplatin_metformin_combo` | registry-backed visible | yes | A tracked mixture with a curriculum-relevant identity; registered with its own scalar `display_color`. |
| `mtt` | registry-backed visible | yes | A named reagent written into wells; registered with a scalar `display_color`. |

This settles the open question carried by the prior MATERIAL_CONVENTION
sentinel table, which had listed `cells`, `formazan`, and the `waste_*` streams
as sentinels. They are not sentinels. The current `content/` registries already
register `cells`, `mtt`, `formazan`, and `waste_mtt` with colors, so the
content is already on the visible-material side; the audit-gate resolution is to
keep the content and narrow the sentinel allowlist to the two true state
markers (`empty`, `mixed`). Migrating those registrations from nested to scalar
`display_color` is the WP-MAT-SWEEP work; confirming registry coverage is the
WP-MATERIALS work; rejecting an unregistered visible material is the
WP-MAT-LINT and stepper `s-unregistered` work.

## Color resolver

The **color resolver** is the single place a material name becomes a color. It
takes a material name and an optional material registry and returns a concrete
typed result: a success carrying a color or `null`, or a failure carrying a
reason. `empty` is the only authored material name that yields `null` before
lookup; a null material name, or a non-built-in name evaluated without a
registry in diagnostic/unseeded no-context mode, can also succeed with `null`.
It reads the scalar `display_color` and selects no theme.
The resolver is the only component allowed to turn a name into a color;
components must not invent local color fallbacks and must not reinterpret a
failure. The resolver's exact typed contract, the failure cases, and the
degrade path live in [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) and
`MATERIAL_LINT.md`; this doc names the term and fixes the invariant that a
non-empty name missing from an authoritative provided registry (including
`{}`) is a resolver failure, never a silent invisible success. A null registry
is no color context, not registry acceptance.

## The material side of the boundary

The four-way authoring boundary names what each vocabulary owns:

- **Protocol** names what happens, and writes a `material_name` (or
  `held_material_name`) value through `ObjectStateChange`. The protocol never
  names a color, an asset, or a registry entry's color. Canonical doc:
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
- **Object** names what a thing is and declares the `material_name` /
  `material_volume` (or `held_material_name` / `held_material_volume`)
  `state_fields` and the `visual_states` that say where and how a material
  renders on that object. The object never declares a color. Canonical doc:
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- **Scene** names where objects are placed. The scene never names a material.
  Canonical doc: [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).
- **Material** names what a substance is and what color it is. The material
  registry owns `label` and the scalar `display_color`. The material side never
  declares where a material appears (object-side) or when it is written
  (protocol-side). Canonical doc: this file, plus the schema in
  [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md) and the rendering convention in
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).

## Terms

| Term | One-line definition |
| --- | --- |
| material | Anything physically present in, on, produced by, removed from, or transferred between objects; a reagent, media, cells, mixture, suspension, drug, assay product, or waste stream. |
| material identity | What a material is: its name and its color; carried by `material_name` / `held_material_name` and rendered through `display_color`. |
| material state | The runtime condition of a material inside one object: that object's `material_name` plus `material_volume` (or `held_material_name` plus `held_material_volume`) values. |
| material name | The snake_case identifier naming a material identity; the value of `material_name` / `held_material_name` and the key of a registry entry. |
| `display_color` | The single scalar hex string giving a visible material its color; the sole source of material color; no theme branch. |
| material condition | Fresh vs old, clean vs dirty, unreacted vs reacted; expressed as a separate material name with its own color, never an alternate color mode. |
| sentinel | A material name carrying no registered identity, exempt from registration; the closed allowlist is `empty` and `mixed`. |
| visible material | Any material name that resolves to a color (every name except `empty`); registry-backed by default, built-in only for `mixed`. |
| material registry | The set of visible materials authored in one protocol's `materials.yaml`; per-protocol, not global. |
| SVG layer recipe | The self-describing semantic rendering description inside one material-rendered SVG form; it describes regions, never a material or color. |
| object material binding | The object YAML `visual_states` declaration that connects object material/amount state to rendering; it does not describe SVG geometry. |
| material-rendered layer | One semantic SVG region identified for recoloring and one closed gravity-part behavior. |
| liquid bottom | Optional material part anchored to the vessel bottom; it never translates or stretches. |
| liquid body | Optional middle material part scaled only in Y about its fixed lower anchor. |
| liquid surface | Optional fixed-shape meniscus or surface detail translated only in Y. |
| derived liquid-region manifest | Generated runtime data derived from normalized material SVG semantics; it supplies opaque handles and is never authored. |
| mixture | A visible material produced by combining inputs; tracked (registered) or untracked (the `mixed` sentinel); no component-list vocabulary. |
| waste | A visible material naming a disposal stream; registered per stream; not a sentinel. |
| transfer | Moving material between objects via protocol `ObjectStateChange` ops on source, tool, and destination state fields; not a material-side primitive. |
| color resolver | The single component that turns `string \| null` material name plus `MaterialRegistry \| null` into a typed color result. `empty` is the only authored name returning null before lookup; null name means no material field, and null registry means no active protocol color context. |
