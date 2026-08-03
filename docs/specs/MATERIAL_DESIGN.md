# Material design

This document explains the design philosophy for materials in the virtual lab
protocol simulation: why material identity must be visible where the student
acts, why protocol YAML never names colors, who owns color versus where color
appears, why an empty container must read as visibly different from a filled one,
and why identity and amount are two separate render layers.

This is a rationale doc. It states the "why". It does not define the
`materials.yaml` schema, object `visual_states` keys, render-effect or target
tokens, or lint rules. Those live in their owning docs:

- The closed material terms (material, sentinel, visible material, registry,
  mixture, waste, transfer) are defined in
  [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).
- The `materials.yaml` schema and the scalar `display_color` field are defined
  in [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md).
- The runtime render convention (the render-effect tokens, the target
  vocabulary, the identity and amount layers as schema) is defined in
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).
- The material-SVG processing contract, including its closed semantic
  vocabulary, is defined in [SVG_PIPELINE.md](SVG_PIPELINE.md).
- The validator and cross-YAML agreement rules are defined in
  `MATERIAL_LINT.md`.

Where a term or token is named below, it is named for the rationale and pointed
at its owning doc. This doc never introduces a new field or token.

## Why materials exist as their own concept

The core design goal of the simulation is that a student learns a protocol by
seeing the correct objects, clicking the correct sequence, and watching the
correct state changes happen on screen (see
[PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md)). A protocol is mostly about moving
substances between vessels: media into a flask, trypsin onto cells, a drug into
a well, spent buffer into a waste container. Those substances are materials.

Treating a material as its own concept, separate from the object that holds it,
is what lets one neutral vessel teach many lessons. A bottle is an object; PBS is
a material; a PBS bottle is a bottle whose material state resolves to PBS. The
same neutral bottle art can read as PBS, media, or trypsin depending only on the
material it currently holds. This separation is the reason adding a new reagent
to the curriculum is a content edit, not a new piece of art and not new
TypeScript.

## Spatial correspondence: identity visible where the student acts (D11)

The binding pedagogical invariant for materials is spatial correspondence: the
student must see the material state change in the same place the protocol says it
changed.

If a protocol step says "add carboplatin to well B7", then well B7 -- the shape
at B7's real position on the plate -- must be the shape that changes. A write to a
single well must color that one well. A group or cascade write (for example "all
wells", a block, or a column) must color exactly its member wells, each in its
own place, and nothing else.

This is pedagogy, not cosmetics. The student is learning where on a physical
plate an action lands. If the action targets B7 but the top-left well lights up,
or if the whole plate tints uniformly, the simulation has taught the wrong
spatial fact even though "a color changed". Misplacement is a failure even when
the colors themselves render correctly.

Three things are therefore load-bearing, not decorative:

- The map from a subpart name to its position must be correct: B7 must resolve to
  B7's coordinates, A1 to the top-left, H12 to the bottom-right.
- Generated geometry must align to the underlying art, so the colored shape sits
  on the real well and not beside it.
- Verification asserts that the specific targeted subpart changed, not merely
  that some subparts differ.

Spatial correspondence is why material identity is rendered at the same address
the protocol writes (for example a per-well subpart), rather than as a single
plate-wide indicator. The state lives where the student acts so the appearance
changes where the student acts.

## Why protocol YAML never names a color

The three authoring layers have strict ownership (see
[PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md) and
[SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md)): protocol is intent, object
is representation and state, scene is placement. A lower layer must not learn
higher-layer meaning, and a higher layer must not name lower-layer mechanisms.

A color is a lower-layer mechanism. A protocol step expresses intent: "the well
now holds carboplatin." It names a semantic material, not a hex value and not an
asset. If protocol YAML named a color directly, three problems follow:

- The protocol would encode a rendering decision it has no authority over,
  breaking the intent-only contract for protocol YAML.
- The same material could be colored inconsistently across protocols, because
  each protocol would carry its own copy of the color.
- Changing a material's color would require editing every protocol that uses it,
  instead of one registry entry.

Keeping color out of protocol YAML keeps the protocol layer about what is true in
the simulation, and lets the appearance of that truth be decided once, in one
place, by the layer that owns appearance.

## Materials own color; object YAML owns where color appears (D7)

Color has exactly one owner and one place it appears, and those are deliberately
two different layers.

- A material owns what color it is. The material registry
  ([MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md)) is the single source for a
  material's `display_color`. Carboplatin is one color everywhere it appears,
  because that color is declared once on the material.
- An object owns where and why that color appears. The object's declared visual
  state ([MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md)) says which region of
  the object is tinted by the material, driven by which state field, with which
  effect. A well plate declares that its per-well region is tinted by the well's
  material; a bottle declares that its liquid interior is tinted by the bottle's
  material. The object decides the placement of color; the material decides the
  value of color.

This split exists because "what color is carboplatin" and "where does carboplatin
show up on this object" are genuinely different questions with different owners. A
new reagent answers only the first (one registry entry). A new vessel answers
only the second (one object declaration). Neither has to know the other's
internals.

TypeScript owns neither answer. The runtime interprets the declared contract --
it reads which field drives which effect on which region, and resolves the
material name to its color through one resolver -- but it never decides which
object gets colored and never carries a per-object color rule. A render behavior
like "tint this region by the material's color" must be expressed as a declarable
token that TypeScript interprets, not as logic hardcoded in a component. If the
runtime hardcoded object-specific color placement, it would reopen the closed
authoring surface and recreate exactly the per-object coupling this design
removes. The acceptance test for this boundary is modularity: a new structured
object (another plate, a rack, a chamber) should render its materials with new
YAML, anchors, and generated geometry only, with no new object-specific
TypeScript renderer.

## Why empty must be visibly distinct from filled (D4)

An empty container and a filled container must not look the same. Emptiness is a
real state a student must be able to read at a glance: an empty well has not been
treated yet, an empty flask has been aspirated, an empty waste bottle is fresh.

The design choice is that `empty` is the one material value that renders no fill:
the subpart or vessel region is transparent and the base art shows through. A
filled container shows its material's color in that region. The contrast between
"base art shows through" and "region carries a material color" is what makes
empty legible.

Empty renders as transparent rather than as a neutral gray ring or a gray fill,
because any visible fill -- even gray -- reads as "something is present here." A
gray ring around an untreated well would imply the well already holds a material,
which is the opposite of what empty means. Absence of fill is the honest visual
for absence of material.

This sets a hard rule when a protocol registry is present: a non-empty,
non-built-in material that is missing there, or whose registry color is invalid,
is an observable resolver failure routed through the existing per-item degrade
path (`MATERIAL_LINT.md`). If a well claims to hold a material but renders
invisibly, the student sees an empty-looking well that the protocol believes is
full -- a spatial-correspondence lie.

The bounded diagnostic/unseeded case is different: without an active protocol
registry, the resolver returns `color: null` rather than claiming registry
acceptance. A null material field and the authored `empty` sentinel are also
successful no-color cases. With any supplied registry, including `{}`, a
non-empty non-built-in name must resolve through that registry; it cannot become
a silent invisible success.

## Why identity and amount are separate layers (D5)

Material rendering carries two independent facts, and they are kept as two
separate render layers because they answer two separate questions:

- Identity (the what): which material is present. Identity is shown by tinting
  the region with the material's color. Blue reads as PBS; pink reads as media;
  violet reads as a drug. Color encodes identity and only identity.
- Amount (the how much): how much material is present. Amount is shown by how
  high the fill rises in the region, driven by the material volume against the
  vessel capacity. Height encodes amount and only amount.

Conflating the two would make the simulation lie. If color also encoded amount
(for example, fading the color as volume drops), a half-full PBS vessel and a
full PBS vessel would read as two different materials, and material identity
would become unreadable mid-protocol -- exactly when the student most needs to
track what is in each vessel. Keeping color for identity and height for amount
means identity stays constant and legible at every fill level, and amount changes
without ever changing what the material appears to be.

The two layers are also independent in scope. Identity (the color/tint layer) is
the layer that makes a well or vessel read as the right substance. Amount (the
fill-height layer) is a separate concern that some vessels render and some do
not. For the per-well plate work that motivated this material spec set, only the
identity layer is rendered on wells: each well is tinted by its material, and the
well's stored material amount is tracked and validated but does not modulate well
color, opacity, or fill height. The amount layer for wells is a non-goal of that
work. The general two-layer model is defined for the whole convention
([MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md)) so that the same declarative
contract serves wells, pipettes, bottles, and chambers; a vessel that renders the
amount layer does so through the same model, not through a parallel mechanism.

## Why material SVGs describe themselves

A material-rendered vessel is exceptional because the runtime must recolor and
transform regions _inside_ its artwork. The semantic rendering recipe therefore
lives with the geometry in that SVG form, rather than in a parallel YAML sidecar
or in material/volume fan-out variants. The SVG owns its layer boundaries,
document order, clip geometry, and fallback paint; `materials.yaml` supplies the
selected material's base color; object YAML supplies the selected form and the
material/amount binding. [SVG_PIPELINE.md](SVG_PIPELINE.md) owns the exact
reserved attributes and validation rules.

This preserves the useful separation between identity and amount inside one
vessel form. The renderer derives role-specific shades from the registry color,
then applies the volume/capacity gravity-part model to compiler-derived geometry:
a stationary lower shape, a middle body scaled only in Y, and a fixed-shape
surface translated only in Y. Assets omit parts they do not need.
It does not replace a runtime material-bound vessel with a per-material or
per-volume SVG, stamp a generic runtime rectangle over the form, or make color a
property of the artwork recipe. This does not prohibit ordinary complete discrete
forms that genuinely differ in geometry, form, or depicted contents (for example
an emptied MTT powder vial or a full sharps container); filename words such as
`empty` and `full` do not determine rendering intent.

The canonical variable-volume shape is:

```text
       movable meniscus
      +--------------+
      |              |
      | stretched    |
      | middle body  |
      |              |
      +--------------+
       fixed bottom
          \    /
           \  /
            \/
```

The meniscus moves but does not stretch. The middle body stretches only in Y.
The cone, rounded base, bulb, or tip remains fixed in vessel coordinates and is
fully hidden only when volume is zero. A stationary reveal boundary prevents
paint above the requested surface without moving the bottom artwork.

Semantic classification follows physical behavior, not color alone. Donor
families with differently colored contents provide a first pass: geometry whose
fill or stroke changes across variants is a strong material candidate. A second
pass reviews every candidate plus white, translucent, highlight, shadow, bubble,
and reflection geometry near the donor liquid. Each liquid-dependent feature is
assigned to `bottom`, `body`, or `surface`; only vessel or glass artwork remains
fixed. The fixed layers must render a coherent empty vessel by themselves and
must not retain a seam or path endpoint at the donor meniscus. At every reviewed
level, no material-dependent feature may remain above the current surface;
surface features move with it.

The authored liquid bounds define the asset's supported operating range. Their
top may preserve deliberate headspace or stop below a changing cross-section;
100% means the declared vessel capacity reaches that supported maximum, not that
liquid is painted to the geometric brim. For the current bottle pilot, logical
requests plateau at the independently reviewed straight-body limit at 85%.
Entering the tapered shoulder above that supported limit would require reviewed
variable-width geometry and is not simulated by stretching the constant-width
middle farther.

The pipeline derives opaque runtime paint and element handles from normalized
semantic groups. Runtime code uses those generated handles; it never depends on
authored `data-vlab-*` attributes or authored DOM ids. This keeps an artist's
semantic labels reviewable while allowing independently rendered instances of
the same SVG to remain isolated.

This is not a general animated-SVG system. Static SVGs remain opaque files, and
open/closed or on/off objects remain collections of complete forms selected by
object `visual_states`. A discrete collection may contain a material-rendered
form, but each form independently declares whether it needs material processing.
An object that is not meaningfully variable-height, such as a T75 culture flask
shown empty or with its normal shallow working layer, should select complete
empty/filled forms instead of declaring a continuous liquid-height animation.
Numeric displays remain object-level overlays.

## Single scalar color: light scientific workspaces only

Every material declares a single scalar `display_color`
([MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md)). The project targets light
scientific workspaces only. There is no light/dark theme, no theme-aware color
selection, and no dark-background rendering. One color is used for a material in
every place it renders.

A single scalar color keeps the material model honest about what it represents.
Color means material identity, full stop. There is no second axis of color
meaning to reconcile against a background mode.

Material condition is handled by identity, not by a color mode. A spent, dirty,
old, or reacted form of a substance is a separate material entry with its own
scalar color -- for example fresh media and spent media are two materials, each
with one color -- not two palette modes of one material. This keeps "what is
this" as the single thing color answers: a different condition is a different
material with a different identity color, which is exactly what the student should
read.

## Non-goals

- A light/dark theme or any dark-background rendering. Color is a single scalar;
  there is no theme branch.
- An amount (fill-height) render layer for wells. Well material amount is stored
  and validated, but well color is the identity layer only. The general amount
  layer is defined in the convention for vessels that use it; it is not part of
  the per-well plate work.
- Schema, token, and lint definitions. This doc gives rationale only; the schema
  lives in [MATERIAL_YAML_FORMAT.md](MATERIAL_YAML_FORMAT.md) and
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md), and the validator rules live
  in `MATERIAL_LINT.md`.
- Encoding any color rule in TypeScript. The runtime interprets declared tokens;
  it never carries an object-specific or convention-specific color placement
  rule.
- An SVG layer-recipe sidecar, material/volume fan-out variants for one runtime
  material binding, or a general
  mutable/animated-SVG framework. Material semantics are an internal contract
  of a material-rendered form only.
