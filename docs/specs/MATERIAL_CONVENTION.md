# Material convention

This document is the canonical **runtime and object rendering convention** for
materials: how a resolved material identity and amount become visible on an
object, the closed render-effect tokens, the closed target vocabulary, the
generic evaluation rule the runtime follows, and the empty/zero and color rules.

This doc owns rendering mechanics only. The other material surfaces live in their
own docs and must not be restated here:

- The closed material terms (material, material identity, material state,
  sentinel, visible material, registry, mixture, waste, transfer, color
  resolver) are defined in [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).
- The `materials.yaml` file schema (keys, `label`, the scalar `display_color`
  hex format, registry scope) is defined in
  [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md).
- The design rationale (why color is identity, why empty is transparent, why
  identity and amount are separate layers) is in
  [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md).
- The validator and cross-YAML agreement rules are in
  `MATERIAL_LINT.md`.
- The `visual_states` authoring keys on an object (`kind`, `cases`, `formula`,
  `applies_to`) are defined in [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).
  This doc names the render-effect and target _semantics_ the runtime applies;
  the object-side declaration keys that select them are owned by that doc.

Protocol terminology is defined in [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).

## Material-rendered SVG ownership

The material-SVG compiler implements the asset syntax, normalization policy,
validation, and derived manifest canonical in
[SVG_PIPELINE.md](SVG_PIPELINE.md). This document owns the cross-layer material
semantics.

Materials remain independent from SVG art:

| Concern                                                                         | Owner                                            |
| ------------------------------------------------------------------------------- | ------------------------------------------------ |
| Material identity and scalar `display_color`                                    | Protocol `materials.yaml` and the color resolver |
| Selection of a complete SVG form; material identity and amount binding          | Object YAML `visual_states`                      |
| Material geometry, document order, clip, source paint fallback, semantic layers | One self-describing material-rendered SVG        |
| Opaque per-layer runtime handles                                                | Generated liquid-region manifest                 |

There is no material-specific SVG sidecar and no material/volume SVG fan-out
for one runtime material binding. Legitimate complete discrete forms remain
independent of this rule.
Object `visual_states` selects complete forms and binds material state; it does
not describe SVG geometry or semantic layers. A root
`data-vlab-rendering="material"` makes a form subject to material normalization
and validation even when unreferenced. A binding controls whether runtime
mutation is applied, not whether the form is processed.

The renderer derives paint from this document's color resolver and amount from
the existing capacity rule. It applies both through generated manifest handles
and the SVG injection seam. Runtime code never queries authored `data-vlab-*`,
uses authored layer names as DOM IDs, or concatenates DOM IDs. Source SVGs keep
literal fallback paint; generated artifacts alone may carry opaque paint handles.

`anchor_liquid_clip` and `anchor_liquid_bounds` remain unique structural SVG
anchors. They support the compiler's derived gravity-part region but are not the
semantic material-layer recipe. Numeric instrument displays remain object-level
text overlays. Static and discrete-state forms remain complete SVG files; a
discrete collection may contain either static or material-rendered forms without
becoming a general animated-SVG system.

An authored semantic material-layer `<g>` must not carry `clip-path`.
`anchor_liquid_clip` remains in `defs`; the compiler applies it only to the
derived liquid region. Ordinary child artwork follows the ordinary SVG
pipeline's supported clip rules.

### Selected-form dispatch

After `visual_states` selects a complete SVG form, an exact root declaration
`data-vlab-rendering="material"` identifies the compiled material path. Invalid
or misplaced reserved attributes fail validation.

An optional root `data-vlab-max-fill-percent` is a closed integer ceiling from
1 through 100. It limits the compiled form's rendered fill height after an
object binding resolves its ordinary percentage; requests above the ceiling
render exactly at the ceiling. It is form geometry, not an object-YAML override.

An optional root `data-vlab-min-fill-percent` is a closed integer floor from 1
through 99. A zero request remains empty; every nonzero resolved percentage
below the floor renders at it. When both floor and ceiling are present, the
floor must not exceed the ceiling. It is form geometry, not an object-YAML
override.

An optional root `data-vlab-body-start-fill-percent` is a closed finite decimal
strictly between 0 and 100 for a conical form. It maps that volume percentage to
the compiled body's measured lower anchor; the runtime linearly interpolates
below it through the cone and above it through the cylindrical body. It is form
geometry, not an object-YAML calibration or asset-name rule.

Alternatively, a non-conical form may declare
`data-vlab-fill-height-exponent`, a finite decimal in `(0, 10]`. The runtime
normalizes its effective percentage by the form ceiling or 100, then maps height
as `q^exponent`; this is form geometry, not an object-YAML calibration or
asset-name rule. It is mutually exclusive with the conical body-start calibration.

An object-level `fill_height` binding selects generated liquid-region manifest
handles through the SVG injection seam: identity recolors semantic material
groups by role and volume/capacity applies the generic liquid-part operations:
fixed `bottom`, Y-scaled `body`, and translated `surface`. Below a conical
form's `body-start` percentage, the surface uniformly scales by
`effective_fill / body_start_fill` about the liquid-bounds horizontal center
and surface datum, then translates to the calibrated level; at or above that
percentage it remains full width. The
material runtime neither creates a rect nor queries/mutates structural anchors
or authored `data-vlab-*`.

The compiler derives separate private datums for the base-surface top (the
volume reading) and the authored body's top (the body join). The runtime aligns
the scaled body top to that scaled join datum. An oval body join is therefore at
its tangent line, not at the oval's lower edge: its sides meet the oval without
gaps or corners extending above the tangent. These are derived geometry, not
asset-name rules or authored offset attributes.

For the material path, the existing YAML binding and capacity fields remain
valid compiler inputs. The compiler validates the required structural-anchor
contract and emits the manifest handles and derived gravity-part region; it does not
expose structural anchor elements to the compiled runtime. Anchors are not
semantic paint layers and are not ignored. This introduces no new object YAML
field, target, or binding token. A root-declared form without a
runtime material binding remains compiled and validated and displays authored
fallback paint without state mutation.

## The general render model

A material becomes visible through one declarative binding contract that is identical for
every object kind that holds, contains, or carries a material: a well subpart, a
pipette, a reagent bottle, a flask, a conical tube, a microtube, a waste
container, and an electrophoresis chamber all render through the same model. The
model has four declarative parts and one resolver:

- a **driving state field** (the `state_field` whose value drives the render):
  a material-identity field (`material_name` / `held_material_name`) or a
  material-amount field (`material_volume` / `held_material_volume`);
- an **`applies_to` scope** (`object` or `subpart`): whether the effect renders
  on the whole object or independently per structured subpart;
- a **`render_effect`** (the closed set below): what visible change the field
  drives;
- a **`target`** (the closed vocabulary below): which authored/generated binding
  region the effect addresses;
- the **color resolver** (defined in [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)),
  the single component that turns a material name into a color.

The runtime keys on these four declarative parts, never on object identity. No
runtime code path names "plate", "well", "pipette", or any specific object. A new
structured object renders its materials by declaring these parts plus its
geometry or anchors; it requires no new object-specific TypeScript renderer. This
is the declarative ownership boundary (contract item 1): `materials.yaml` owns
what color a material is, the object declaration owns where and why color
appears, generated data owns subpart geometry, and TypeScript owns only how to
interpret the declared contract.

## Render-effect set (closed)

A `render_effect` is the visible change a driving field produces. The set is
closed and extensible only by a vocabulary edit (see
[SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md)); an author selects an
effect, never invents one. There are exactly two effects, one per render layer:

| `render_effect` | Layer    | Driving field type      | Updates                                                              |
| --------------- | -------- | ----------------------- | -------------------------------------------------------------------- |
| `material_tint` | identity | a material-name field   | generated subpart fill, or compiled material semantic groups by role |
| `fill_height`   | amount   | a material-volume field | generated subpart geometry, or compiled gravity-part operations      |

The two layers are independent (see [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md)):
color encodes identity and only identity; height encodes amount and only amount.
A vessel may declare one effect, the other, or both; each is resolved
independently from its own driving field.

### `material_tint` (identity layer)

`material_tint` recolors the fill of the target region to the resolved material's
`display_color`. It is the effect that makes a clear well or vessel read as the
right substance (blue reads as PBS, pink as media, violet as a drug). It targets
only the fillable interior region named by `target`; it never recolors the
glassware outline, the cap, or a label.

Typed params:

| Param           | Required | Type | Allowed values                            | Meaning                                                  |
| --------------- | -------- | ---- | ----------------------------------------- | -------------------------------------------------------- |
| `render_effect` | yes      | enum | `material_tint`                           | selects the identity effect                              |
| `applies_to`    | yes      | enum | `object`, `subpart`                       | render once for the object, or independently per subpart |
| `target`        | yes      | enum | a member of the target vocabulary (below) | which region's `fill` is recolored                       |

The driving field is the `visual_states` key the effect is declared under (a
material-name field); the effect names no field of its own. Color comes only from
the color resolver reading the material's scalar `display_color`; the declaration
names no hex value.

Example (a well subpart tinted by its own material identity):

```yaml
visual_states:
  material_name:
    applies_to: subpart
    render_effect: material_tint
    target: subpart_geometry
```

At render time, for each well subpart the runtime reads that subpart's
`material_name`, resolves it through the color resolver, and sets the `fill` of
that subpart's generated geometry to the resolved color. When the value is
`empty` (or the subpart's `material_volume` is `0`), no fill is rendered (see
empty/zero semantics below).

### `fill_height` (amount layer)

`fill_height` raises and lowers the liquid surface with the material amount,
computed from the driving volume field against a declared capacity. Height
encodes amount and never identity. For an object-level material binding,
compilation supplies opaque manifest handles for optional `bottom`, `body`, and
`surface` parts. Runtime leaves bottom geometry stationary, scales the middle
body only in Y about its lower anchor, uniformly narrows a conical surface in
both axes below its body-start percentage before translating it in Y, and
updates a reveal boundary in stationary vessel coordinates. The
complete material region is hidden at zero.
The fixed layers alone must render a continuous empty vessel: a recolored donor
liquid path must not remain fixed merely because it resembles glass, and no
fixed path may expose an artificial endpoint at the donor meniscus. Every
liquid-dependent base, tint, side shade, highlight, shadow, bubble, and
reflection belongs to `bottom`, `body`, or `surface` according to how it behaves
as the level changes. At every rendered amount, no material-dependent feature
may remain above the current surface; a surface feature moves with that surface.
The authored target bounds are the supported operating range: their top may
preserve headspace or stop below a cross-section change. Therefore 100% is the
declared capacity at that reviewed maximum, not necessarily the vessel's
geometric brim. A tapered shoulder that changes liquid width is outside the
constant-middle proof and must be separately decomposed before the supported
range enters it.

Typed params:

| Param           | Required | Type  | Allowed values                               | Meaning                                                                                                 |
| --------------- | -------- | ----- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `render_effect` | yes      | enum  | `fill_height`                                | selects the amount effect                                                                               |
| `applies_to`    | yes      | enum  | `object`, `subpart`                          | render once for the object, or independently per subpart                                                |
| `target`        | yes      | enum  | `anchor_liquid_bounds` or `subpart_geometry` | compiler source bounds for an object-level material SVG, or generated geometry for a structured subpart |
| `clip`          | no       | enum  | `anchor_liquid_clip`                         | compiler source clip for an object-level material SVG                                                   |
| `capacity_ul`   | one of   | float | positive number                              | the vessel capacity in microliters; the volume/capacity denominator                                     |
| `capacity_ml`   | one of   | float | positive number                              | the vessel capacity in milliliters; the volume/capacity denominator                                     |

Exactly one of `capacity_ul` / `capacity_ml` is declared, matching the driving
volume field's unit. The driving field is the `visual_states` key the effect is
declared under (a material-volume field).

Example (a serological pipette filled by the amount it holds, for reference; the
existing vessel fill behavior):

```yaml
visual_states:
  held_material_volume:
    applies_to: object
    render_effect: fill_height
    target: anchor_liquid_bounds
    clip: anchor_liquid_clip
    capacity_ml: 25.0
```

`fill_height` has two intentional mechanisms: object-level material SVGs use
compiled gravity parts; structured subparts use generated subpart geometry.

## Target vocabulary (closed)

A `target` names the authored/generated binding region an effect uses. The
vocabulary is closed and covers generated geometry (structured subparts) and
compiler-only SVG structural anchors. An object-level anchor binding selects
generated manifest handles and a derived gravity-part region; it never resolves
a structural anchor at runtime. The YAML target never becomes a runtime material
DOM selector.

| `target`               | Kind                     | Region it names                                                                      |
| ---------------------- | ------------------------ | ------------------------------------------------------------------------------------ |
| `subpart_geometry`     | generated geometry       | the generated shape for the current structured subpart (well, lane, rack position)   |
| `anchor_liquid_bounds` | compiler-only SVG anchor | the authored operating range from which the compiler derives the gravity-part region |
| `anchor_liquid_clip`   | compiler-only SVG anchor | the authored clip used to constrain the derived gravity-part region                  |

### Generated geometry targets

`subpart_geometry` resolves to the generated shape for the subpart the effect is
currently rendering. The generator emits one typed geometry entry per subpart,
position-derived from the base art so the colored shape sits on the real subpart
(spatial correspondence). The shape set is closed; `circle` covers round wells
and `rect` covers rectangular subparts (gel lanes, rack slots). Other shapes
(`ellipse`, `path`) are added only when a current or near-term SVG needs one;
`path` is avoided unless no simpler shape fits.

```
type SubpartGeometry =
  | { shape: "circle"; cx: number; cy: number; r: number }
  | { shape: "rect"; x: number; y: number; w: number; h: number };
type SubpartGeometryMap = Record<string, SubpartGeometry>;
```

The 96-well plate emits `circle` entries keyed by subpart name (`A1`, `B7`,
`H12`). The map is the typed, deterministically ordered input the overlay
renderer iterates; each subpart-name key resolves to its own geometry so a write
to `A1` colors the top-left well and a write to `H12` colors the bottom-right.

### SVG anchor targets

`anchor_liquid_bounds` and `anchor_liquid_clip` name the two invisible structural
anchors authored into an object-level material SVG. They are compiler inputs,
not runtime targets: the material pipeline validates them and derives generated
handles plus the gravity-part region. Structured subparts instead use
`subpart_geometry` and do not use these anchors.

```
type AnchorTarget = "anchor_liquid_bounds" | "anchor_liquid_clip";
```

A visual-state target is therefore either a `subpart_geometry` region (resolved
through the `SubpartGeometryMap`) or an `AnchorTarget` consumed by the compiler.

#### Authored anchor SVG structure

Each base SVG that supports liquid rendering defines a `<clipPath>` with bare id
`anchor_liquid_clip` shaped to the container interior (the fillable region only,
excluding cotton plug, tip, cap, or label), and an invisible
`anchor_liquid_bounds` rect marking the region the fill rises within.

```svg
<defs>
	<clipPath id="anchor_liquid_clip">
		<rect x="5.5" y="15" width="5" height="101" rx="0.5"/>
	</clipPath>
</defs>
<rect id="anchor_liquid_bounds" x="5.5" y="15" width="5" height="101"
      fill="none" stroke="none" display="none"/>
```

The clip geometry must cover the interior space where liquid appears without
spilling onto non-liquid parts of the art.

#### Anchor id boundary

The authored SVG carries bare `id="anchor_liquid_clip"` and
`id="anchor_liquid_bounds"`, and the object declaration names those bare targets
(`anchor_liquid_bounds`, `anchor_liquid_clip`). These names are declarative
compiler inputs, not live DOM ids. The compiler consumes them before publishing
the material artifact, and runtime never reads or resolves them.

The asset-readiness check opens each selected material SVG and confirms both bare
ids are present; a missing id is reported against the SVG path, not the YAML.

SVG DOM is the legitimate rendering substrate here, not application state. For an
object whose internal SVG structure is part of its declared contract (anchors,
clip-paths, gradients, material targets, per-instance id namespacing), the
injected SVG DOM is the correct and allowed place that structure lives. The DOM
is never used as application state or control flow: render state, reactivity, and
attribute updates stay in the Solid layer, and the runtime never reads a value
back out of the DOM to decide what to do next.

DOM access is isolated in the SVG injection layer. A compiled material runtime
issues no `document.querySelector`, no `getElementById`, no string-built
`url(#...)` reference, and no structural-anchor lookup or mutation. It updates
only role paint through opaque manifest handles and gravity-part operations; it
does not use the DOM as a state store.

##### No id construction by name concatenation (invariant)

Runtime material code must not construct a DOM id by concatenating asset, scene,
placement, target, or anchor names (no `<asset_name>__anchor_liquid_clip`, no
`<placement>_<target>`, no string-built `url(#...)` reference). The material
layer owns declarative target names only. Constructing an id by name is a
layer-boundary violation.

Well subparts (`target: subpart_geometry`) are namespace-safe by construction:
they render into a separate overlay SVG built from generated geometry that
references no base-SVG ids.

## Generic evaluation rule

The runtime applies one rule for every render effect, with no object-specific
branch:

1. For each `visual_states` entry, read its driving state field, its
   `applies_to` scope, its `render_effect`, and its `target`.
2. Resolve the driving field independently per scope: for `applies_to: object`,
   read the object's field value once; for `applies_to: subpart`, read each
   structured subpart's field value independently (a per-subpart material name is
   resolved per subpart, not once for the whole object).
3. For a `material_tint` effect, resolve the material name through the color
   resolver to a color; for a `fill_height` effect, compute the level fraction
   from the volume and capacity.
4. Dispatch by target scope: generated subparts update their generated geometry;
   object-level material SVGs use generated manifest handles to write role paint
   and apply the generic gravity-part operations. The runtime never adds,
   removes, or reorders DOM nodes per state change.

Generated subparts and compiled material SVGs are separate intentional
mechanisms. The former updates generated subpart geometry; the latter changes
existing gravity-part state through the generated manifest. Neither path adds,
removes, or reorders nodes on state change.

## Color resolver behavior

The color resolver (named and bounded in
[MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)) is the single component that
turns a material name into a renderable color. This doc owns its runtime
behavior: its typed result, what each input maps to, and how rendering consumes
the result. No other component turns a name into a color, and no component
invents a local fallback color or reinterprets a failure.

`resolve_color_result(material_name, material_registry)` takes a
`string | null` material name and a `MaterialRegistry | null`. A `null` name
means the object declares no material field; it is not an authored material
name (`empty` remains the authored named-absence value). A `null` registry
means there is no active protocol color context, as in diagnostic scene-viewer
or unseeded rendering. It is not an empty authoritative registry.

The resolver returns a concrete typed result, a discriminated union of a
success or a failure:

```
type ColorResult =
  | { ok: true; color: string | null }
  | { ok: false; reason: string };
```

The `color` of a success is either a `#rrggbb` hex string or `null`. `null` is
not a failure. It can mean the authored `empty` sentinel, that the object has
no material field, or that a diagnostic render has no protocol color context.
A failure carries a human-readable `reason` and renders no color through the
degrade path, never a painted region.

The resolver maps each input to exactly one result:

| Input condition                                                                     | Result                           | Rendered as                                         |
| ----------------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------------- |
| `material_name` is `null`                                                           | `{ ok: true, color: null }`      | no material field; no material paint                |
| material name is `empty`                                                            | `{ ok: true, color: null }`      | no fill (`fill="transparent"`); art shows through   |
| material name is `mixed` (with either registry value)                               | `{ ok: true, color: "#686868" }` | the spec-fixed built-in gray                        |
| non-built-in name with `material_registry: null`                                    | `{ ok: true, color: null }`      | diagnostic/unseeded render: no active color context |
| non-sentinel name in a provided registry with valid scalar `display_color`          | `{ ok: true, color: "#rrggbb" }` | that scalar color                                   |
| non-sentinel name absent from any provided registry, including `{}`                 | `{ ok: false, reason }`          | the per-item degrade path (never a color)           |
| name in a provided registry whose `display_color` is missing or not valid `#rrggbb` | `{ ok: false, reason }`          | the per-item degrade path (never a color)           |

`empty` is the only authored material name that returns `ok: true` with
`color: null` before registry lookup. It is not the only runtime input that can
produce null color. The built-in `mixed` is resolved by the resolver itself to
the concrete spec-fixed gray `#686868` (see "Built-in material colors" below);
it is never a registry lookup and never resolves to `null`. The resolver reads only the scalar
`display_color` (see [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md) for the
`^#[0-9a-f]{6}$` format); it selects no theme and reads no `.light` / `.dark`
branch, because no such branch exists.

The success/failure split is the rendering boundary: an `ok: true` result paints
the resolved `color` (or has no material paint for `null`), and an `ok: false`
result is routed, unmodified, to the observable per-item degrade path defined
in `MATERIAL_LINT.md`. A consumer must not catch an `ok: false` and substitute a
color, and must not treat `color: null` as a failure. The binding invariant from
[MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md) applies when a registry is
provided: a non-`empty`, non-built-in name must resolve from that authoritative
registry or fail visibly. The null-registry diagnostic exception is not registry
acceptance and must never apply when a registry is provided.

### Material-SVG shade derivation

For a material-rendered SVG, every material semantic group derives paint only
from the resolved base `display_color`; there is no per-asset color source.
`base` uses that lowercase `#rrggbb` color unchanged. `highlight` and `shadow`
require an authored `data-vlab-adjustment` whose syntax and allowed range are
defined in [SVG_PIPELINE.md](SVG_PIPELINE.md): highlight is strictly positive
and at most `0.5`; shadow is at least `-0.5` and strictly negative.

The compiler converts the resolved base color to OKLCH, computes
`L' = clamp(L + adjustment, 0, 1)`, preserves hue, and reduces chroma only as
needed to reach the sRGB gamut. It serializes the result as lowercase
`#rrggbb`. This is an additive delta to normalized OKLCH lightness, not a new
color source and not a material-specific or asset-specific override.

Property-style tests may assert role ordering, accepted adjustment range, and
sRGB-gamut serialization; they must not freeze a particular color-library's
rounding into exact shade constants.

## Empty, null, and zero-volume semantics

The sentinel material `empty` is the only authored material name that renders
no fill. The runtime skips visible material fill entirely when either:

- the driving identity field is `empty` (`material_name == empty` or
  `held_material_name == empty`), or
- the driving amount field is `0` (`material_volume == 0` or
  `held_material_volume == 0`).

When the fill is skipped, the base object art shows through unchanged: no fill
rect, no neutral ring, no gray placeholder. Transparency is the honest visual for
absence of material (see [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md)). The color
resolver returns `null` for `empty`, and the runtime renders `fill="transparent"`
(or omits the fill node's color) for that region.

Resolver outcome and amount-state validation are separate:

- With an authoritative registry, a non-`empty` material name that resolves to
  no color is a resolver failure, never a silent invisible "success". The
  runtime routes it to the observable per-item degrade path defined in
  `MATERIAL_LINT.md`.
- A non-empty material with volume `0` is a valid no-visible-amount state under
  this skip rule; it is not a `ColorResult` failure. A missing required volume
  for a `fill_height` binding is likewise a separate object binding/state
  validation failure, not resolver output.
- In a diagnostic render with a null registry, a non-built-in material name can
  resolve to null because no protocol color context exists. That exception does
  not relax the authoritative-registry binding invariant.

`empty` is the single authored named-absence value; runtime null color also has
the explicitly bounded no-field and no-color-context meanings above.

## Shared material-bound form, no material or volume fan-out

When a paired material identity and amount binding uses runtime material
rendering (`material_tint` and/or `fill_height`), every case in that pair selects
the same complete SVG form. The compiled material path changes semantic groups
and its derived gravity-part region from that state. Material identity and amount
therefore change runtime paint and level, not the selected SVG filename.

This rule is deliberately narrower than a filename rule. Complete discrete forms
remain valid when they represent genuine form, geometry, or content states, even
when their names include words such as `empty` or `full`, or when the selecting
field is material-like but has no paired runtime material binding. For example,
`mtt_powder_vial.svg` / `mtt_powder_vial_empty.svg` and
`sharps_container.svg` / `sharps_container_full.svg` are legitimate ordinary
discrete forms. Names alone never classify an asset's intent.

The prohibited fan-out is selecting different forms solely to encode the color
or liquid level of a paired runtime material binding, such as making the same
vessel choose `<object>_with_<material>.svg` or separate empty/filled art for
its `fill_height` state. That fan-out is rejected by
`validation/yaml/object_validator.py` (and the rules in `MATERIAL_LINT.md`).

## Declaration-based render mode

Render mode is decided by the selected form's declared SVG requirements, not by
its current runtime state. A material-declared selected form requires injected,
per-instance-namespaced SVG DOM and does not flip to an `<img>` when empty.

An object binding supplies the state and target. Its material-declared form uses
the compiled material manifest. An `<img>` exposes no internal DOM and cannot
host a compiled material instance.

The trigger is the declaration, not the value. A bottle that declares
`fill_height` but currently holds `empty` still renders as injected SVG because
compiled material handles must already have a DOM home. Deciding render mode
from the current value would incorrectly flip an object between `<img>` and
injected SVG as its state changes.

## Single scalar display_color rendering

`display_color` is the sole source of material color for both identity paint
(`material_tint`) and liquid appearance controlled with `fill_height`. It is a **single
scalar hex string**, read as-is by the color resolver. This project targets light
scientific workspaces only: there is no light/dark theme, no `.light` / `.dark`
branch, and no theme-aware color selection. One color renders a material in every
place it appears.

Material condition (fresh vs spent, unreacted vs reacted) is a separate material
name with its own scalar color, never an alternate color mode of one material
(see [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)). The object and protocol
YAML never name a hex color; they name a material name, and the runtime resolves
that name to its scalar `display_color` through the object's declared visual
state.

## Built-in material colors

A built-in is a visible material whose color is fixed by this spec rather than
authored per protocol. The built-in set is closed and is the only place a color
appears outside `materials.yaml`. Today the set has exactly one member, the
sentinel `mixed`:

| Material name | Built-in `display_color` | Renders | Why built-in                                                                                                                            |
| ------------- | ------------------------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `mixed`       | `#686868`                | yes     | A sentinel carrying no tracked identity, so it is not a registry entry; a non-`empty` material must render, so its color is spec-fixed. |

`#686868` is a neutral gray with a 5.57:1 contrast ratio against the white
workspace background (meeting the 5.5:1 bar that
[MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md)
requires of registry colors). Gray carries no specific hue, which matches the
meaning of `mixed`: visibly present, but of unidentified composition. The color
resolver returns this built-in color for `mixed`; `mixed` is never registered in
`materials.yaml` and never renders invisible. Every material name other than the
two sentinels (`empty`, `mixed`) is a registry-backed visible material whose
color comes from its `materials.yaml` entry; see
[MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md) for the settled
sentinel/visible classification.

## Convention scope

The render model binds every kind that holds, contains, or carries a material:

- `bottle` (every reagent bottle, including waste-feeder bottles)
- `flask` (T75 and other cell-culture flasks)
- conical tube (`conical_tube` and `conical_tube_in_rack`)
- microtube (the dilution microtube subpart inside the well-plate workspace)
- waste container (every `content/objects/waste/*.yaml` object)
- electrophoresis chamber (the inner and outer chambers inside
  `content/objects/equipment/electrophoresis_tank.yaml`, each pairing its own
  per-chamber `<prefix>material_name` / `<prefix>material_volume`)
- well subpart (each well inside `content/objects/plate/well_plate_96.yaml`)
- pipette (every `content/objects/pipette/*.yaml`; uses the `held_material_*`
  field pair instead of `material_*`)

For every kind above, fill color is material identity (driven by `material_tint`
from the resolved `display_color`), and fill height is material amount (driven by
`fill_height` from the volume); the selected form root dispatches the rendering
mechanism. The fill never encodes progress state. Progress
state (active, completed, future) is carried by an outline CSS class on the host
element, which never touches the fill color, so material identity stays readable
at every progress stage.

## Worked example: a well subpart and a vessel

Identity layer on a well subpart, plus the separate object-level amount layer on
a vessel:

```yaml
# well subpart (per-subpart identity layer; implemented by the well_plate_96 plan)
visual_states:
  material_name:
    applies_to: subpart
    render_effect: material_tint
    target: subpart_geometry

# vessel (object-level amount layer; specified here, implemented by a separate plan)
visual_states:
  material_volume:
    applies_to: object
    render_effect: fill_height
    target: anchor_liquid_bounds
    clip: anchor_liquid_clip
    capacity_ul: 1000
```

For the well: when a subpart's `material_name` is `media`, the runtime resolves
`media` to its registered color and tints that one well's generated circle; when
the subpart is `empty`, the well renders transparent. For the vessel, the
material pipeline validates `anchor_liquid_bounds` and `anchor_liquid_clip`,
derives its gravity-part region, and runtime controls those parts through opaque
manifest handles in proportion to `material_volume / 1000 ul`.

## Testing

Material-path tests verify generated manifest handles, role recoloring,
gravity-part operations, and no direct runtime anchor or `data-vlab-*` access.

1. Semantic liquid parts are visible when a pipette is loaded.
2. Their color matches the resolved `display_color` for the held material name.
3. Fill height is non-zero and consistent with the volume/capacity ratio.
