# Plan: Semantic in-SVG liquid rendering

## Context

At the start of this plan, materials rendered by painting a flat `<rect>` on top of the artwork
(`src/scene_runtime/renderer/anchor_material_renderer.ts`, 176 lines). The rect is
positioned inside `anchor_liquid_bounds` and clipped to `anchor_liquid_clip`. The real
liquid drawn in the art was never touched, so `assets/equipment/bottle_medium_pink.svg`
stayed pink under a green block. The overlay had been removed twice at the user's
request and returned twice, because the specs describe it as the render model:
`MATERIAL_CONVENTION.md` names overlays 11 times, `OBJECT_YAML_FORMAT.md` 12 times,
`SVG_PIPELINE.md` 4 times.

Evidence already published in
[servier_svg_color_variants.md](reports/servier_svg_color_variants.md), confirmed independently
here:

- The neutral glass, cap, and outline palette is shared across variants: `#333`, `#55919f`,
  `#90bac4`, `#9d869a`, `#a9cad2`, `#b6d2d9`, `#b9d6dd`, `#c0b0ba`, `#c4c4c4`, `#dde9ec`,
  `#e3eef1`, `#e7e0e3`, `#ebebeb`, `#f6fafb`, `#f7f4f4`, `#fff`. Only the tinted ramp
  changes between pink, orange, and green.
- The tinted ramp runs light-to-dark and paints the medium surface, bulk medium, side and
  bottom shadows, and the colored label border. Pink carries 13 variant colors, orange 10,
  green 9. One color repeats across several paths (green `#01642a` five times, pink
  `#88016c` three times), so the tinted PATH count exceeds the distinct-color count.
- Variant colors appear on `stroke` as well as `fill` (pink `#dba6cb` is a stroke). Any
  classification that looks only at `fill` misses part of the ramp.
- Path order and count DIFFER across variants (44 / 42 / 43 paths; viewBoxes differ
  slightly). The report's color-neutralized comparison still differs within every family:
  these are sibling drawings, not palette swaps. Cross-variant positional diffing is
  therefore invalid, and the report's own conclusion is palette substitution within one
  file, never synthesis by merging variants.
- The test-tube family gives a clean reference: a 13-path empty glass tube plus 20-path
  filled tubes whose four added colors are exactly body, meniscus/light, side shadow, deep
  shadow. That is the role set this plan parameterizes, and the empty-glass file is the
  visual target for a zero-volume vessel.
- Closed microtubes carry TWO independent ramps: plastic body/lid/hinge, and liquid. Only
  the liquid ramp is material-driven; the plastic ramp is asset identity and stays fixed.
- Translucency in these files is painted with gray/white/highlight paths. Every explicit
  `fill-opacity` and `stroke-opacity` is `1`, so no alpha handling is needed.

The same conclusion was reached independently for three unrelated families (medium bottles,
test tubes, microtubes), not one. That is what makes the rejection of positional and
path-index matching an architectural fact rather than a bottle-specific observation, and it
is why a flat glass-versus-liquid split is insufficient: the report documents interleaved
glass, liquid, highlight, shadow, and label elements in the same drawing.

Color clustering is therefore BOOTSTRAPPING only. It proposes which elements belong to a
ramp at import time, exactly as the report's "choose a geometry master, replace the complete
ramp" workflow does. Once semantic layer names are assigned, those names are the authored
identity and fill values are never read again to infer meaning. Runtime handles are derived
from the layer names during generation or injection; the SVG never authors a runtime DOM id.
That is why color clustering appears in M1 and disappears from every later milestone.

- Structurally the donors are simple: one root `<svg>`, one `<defs>`, one `<clipPath>`,
  flat path list, no groups, no gradients, no masks, no symbols, no semantic ids.
- The colored and neutral paths intermesh in stacking order. A liquid highlight sits above
  the rear glass contour and below the front rim, so a flat `bottle` / `liquid` split
  cannot express the art. The art needs fixed back layers, one contiguous liquid band, and
  fixed front layers. The source keeps literal donor fills and strokes; material compilation
  adds derived CSS custom-property paint handles only to the normalized/generated runtime
  artifact.

So the problem is semantic cleanup, not vector geometry. The fix is a one-time refactor
of each vessel asset into a fixed-back/material/fixed-front document-order band, with the
liquid band clipped to the bottle interior, semantic object layers, same-role adjacent paths merged, and fills driven by
derived CSS custom properties. Volume follows the gravity-part contract recorded in
`audits/liquid_gravity_part_hypothesis.md`: a fixed bottom, Y-scaled middle body,
and translated fixed-shape surface, with any unused part omitted.

## Objectives

- Recolor the real liquid paths of a vessel so an empty bottle looks empty and a
  green-media bottle looks green, with the donor artwork's highlights, shading, and
  surface relationships intact.
- Move the liquid surface with one volume parameter while keeping the bottom anchored,
  scaling only the middle body in Y, and translating the fixed-shape meniscus.
- Retire the overlay renderer after all selected material forms are converted; the compiled
  material path has no overlay-rect fallback.
- Keep authoring declarative: a material-rendered SVG is self-describing through one
  closed semantic attribute vocabulary, while the existing object YAML `visual_states`
  block supplies the material binding and volume. No recipe sidecar and no new open-ended
  field are introduced.

## Design philosophy

The trade-off is a one-time refactor cost for the five evidenced continuously variable
vessel families bought against permanent visual honesty. This is "long-term over short-term" and
"fix the design, not the symptom" from `docs/REPO_STYLE.md`: the overlay is a symptom
patch over art the runtime refused to understand, and every attempt to improve it has
been shading a rectangle.

Rejected alternative: translating one finite liquid group. The Falcon contact page
falsified it: moving the surface also moved the bottom, exposed paint outside the tube,
emptied the cone at high fill, and stopped full volume at the donor meniscus. Hidden
overscan improved one render but retained the wrong physical model.

Accepted model: material layers declare the closed optional part vocabulary `bottom`,
`body`, or `surface`. The compiler derives opaque handles and geometric calibration. The
runtime keeps `bottom` stationary, scales `body` only in Y about its lower anchor, and
translates `surface` without deformation under stationary vessel and reveal clips.

Rejected alternative: per-material or per-volume variants for one runtime material
binding (`bottle_green.svg`, `bottle_orange.svg`, or separate volume-specific art). The
donor variants exist and are tempting, but the fan-out is unbounded (materials x
volumes x vessels) and `MATERIAL_CONVENTION.md` forbids it when one paired binding
uses runtime material rendering. Donor variants are used as identification evidence
only; the repo keeps one canonical form for that binding. This does not reject
legitimate complete discrete forms such as `mtt_powder_vial_empty.svg` or
`sharps_container_full.svg`, whose filenames and selecting field do not by
themselves determine rendering intent.

Rejected alternative: two physical files (`bottle.svg` plus `liquid.svg`) assembled by
external references. External references hit CORS and local-loading limits, survive
design-tool round-trips badly, complicate export and embedding, and force shared clip paths
and custom properties across document boundaries. One SVG with ordinary semantic `<g>`
elements keeps geometry and roles together. `<symbol>` / `<use>` adds no needed capability
and is rejected by the current normalizer, so this plan does not expand that support.

Rejected alternative: a flat two-group split (`<g id="bottle">` then `<g id="liquid">`).
It forces every neutral path below or above every colored path, which the intermeshed
donor stacking forbids.

- Evidence strategy for uncertain methods: the asset census in M1 is what decides how many
  assets can be refactored mechanically, how many need hand art work, and whether
  structured subparts (wells, lanes, rack slots) can use the same mechanism. No conversion
  work is scheduled past the pilot until that census exists.
- Semantic-storage decision: material-rendered SVGs are self-describing. Geometry,
  document order, and semantic roles travel together; a separate recipe sidecar is rejected
  because it would duplicate identity and permit synchronization drift. M2 measures the
  current pipeline and confirms the approved semantic carrier and normalization guarantees,
  but it does not reopen external recipe storage.

This plan does not create a general animated-SVG system. Asset organization uses two
independent axes rather than three mutually exclusive buckets:

| Axis                          | Values                            | Meaning                                                                                         |
| ----------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------- |
| Selection model               | `single` or `discrete_collection` | Render one file, or let object `visual_states` select one complete form from a named collection |
| Rendering model, per SVG form | `static` or `material_rendered`   | Treat the selected file as opaque, or recolor and transform its authored material layers        |

A discrete collection can therefore contain a material-rendered form. For example, a
microtube collection could select complete open and closed SVGs while only the closed form
contains liquid layers. That is still file selection first and material rendering second;
it does not require a generalized animation system.

Every source filename remains understandable outside its directory. Files use descriptive
snake_case names such as `power_supply_off.svg`, `centrifuge_lid_open.svg`, or
`microtube_1_5ml_closed.svg`, never generic `open.svg`, `closed.svg`, or `asset.svg`.
Capacity or size appears when it distinguishes forms. The filename does not add a
`material_rendered` suffix unless two otherwise identical forms differ only by rendering
capability.

The power supply demonstrates why the distinction matters: `running` selects
`power_supply_off` or `power_supply_on`, while `set_voltage` uses the existing text-overlay
feature. The heat block likewise selects `heat_block_closed` or `heat_block_open`. Neither
case needs the runtime to inspect arbitrary SVG paths. Material rendering is exceptional
because liquid identity and amount must modify artwork inside one canonical asset.

## Scope

- Refactor the five true continuously variable families (1.5 mL microtube, 15 mL and
  50 mL conical tubes, media/reagent bottle, and serological pipette) into a
  fixed-back/material/fixed-front document-order structure
  (`bottle_back`, contiguous `liquid_*` groups, `bottle_front`) with semantic object layers
  and literal donor paint fallbacks in source. Material compilation emits runtime paint
  handles in the normalized/generated artifact.
- Merge same-role adjacent paths where fill, opacity, stroke, and stacking allow, targeting
  roughly 22-35 paths per asset (about 8-12 back, 5-10 liquid, 8-12 front, one interior
  clip) instead of the donor's 42-44.
- Run an early carrier experiment on representative material structures, confirm the
  canonical embedded vocabulary, and implement an asset-type-aware semantic normalization
  path before durable material-asset conversion.
- Inventory the current SVG fleet on both asset-taxonomy axes; determine whether directory
  layout, descriptive naming, existing `visual_states`, or a small collection manifest
  should express organization; and identify every collection containing both static and
  material-rendered forms.
- Add an OKLCH shade-derivation module that produces a coordinated palette from one
  material `display_color`.
- Replace `anchor_material_renderer.ts` with a gravity-part property writer.
- Preserve the existing object YAML `fill_height` / `material_tint` binding vocabulary while
  converting selected material forms; do not add a target/token migration.
- Rewrite the specs so the form-root dispatch is explicit and documents the compiled material
  path as role recolor plus a stationary reveal, fixed bottom, Y-scaled body, and translated
  surface.
- Add lint that rejects an asset declaring material rendering without a recipe, and
  rejects a reintroduced overlay rect.
- Add Playwright visual evidence across material x volume for every converted asset.

## Non-goals

- Ship material-identity or volume-specific fan-out SVG assets for one runtime
  material binding. This does not prohibit legitimate complete discrete forms.
- Add light/dark theming or a second color source beyond scalar `display_color`.
- Change the protocol, layout, or walker vocabularies.
- Generalize all SVG assets into animations, sprite collections, or mutable internal DOM.
- Replace discrete form selection for open/closed, on/off, running/idle, or similar object
  states. Those remain complete flat SVG files selected by object `visual_states`.
- Move numeric instrument displays into SVG internals. Existing `label(...)` text overlays
  remain the object-level display mechanism unless a separate future plan finds a concrete
  visual defect.
- Perform a speculative directory-wide move before M2 measures the current naming,
  resolver, attribution, validation, and tooling impact. If physical reorganization is
  justified, M2 records an explicit migration boundary rather than hiding it inside art
  conversion patches.
- Add a generic animation vocabulary, arbitrary SVG scripting, SMIL, `<symbol>` / `<use>`,
  or asset-specific runtime selectors.
- Convert structured subparts (96 wells, gel lanes, rack slots). M8 measures and decides;
  any conversion is a follow-on plan. This version succeeds without it because grid subparts
  already render with correct spatial correspondence through generated geometry, while
  vessels are the surface where the overlay is visibly wrong today.
- Add keyboard or ARIA affordances to the SVG layer (out of scope per
  `docs/PRIMARY_DESIGN.md` accessibility scope).

## Current state summary

| Surface          | Now                                                                                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Assets           | 119 SVGs under behavior-organized `assets/equipment/`; five are true variable-volume material forms                                                                   |
| Objects          | M6 audited the 48 historical object-level effects; 29 select the five true variable-volume forms, and all others are discrete, static, or structured-subpart concerns |
| Discrete forms   | `power_supply_off` / `power_supply_on` and `heat_block_closed` / `heat_block_open` are selected by `visual_states.kind: svg`                                          |
| Numeric displays | power supply voltage and other set points use `visual_states.kind: overlay` with `label(...)`, outside SVG path mutation                                              |
| Renderer         | `liquid_paint.ts` is the only object-level material renderer and writes compiled gravity-part state through generated handles                                         |
| Color            | `material_color.ts` resolves name -> `ColorResult`; sound, reusable, keep it                                                                                          |
| Injection        | `inject_svg.ts` fetches asset text, parses and namespaces internal ids per instance, and exposes compiled material handles                                            |
| Subparts         | `subpart_dispatch.ts` / `subpart_visual_state_renderer.tsx` paint generated circles over the plate art                                                                |

`inject_svg.ts` already walks the parsed SVG for id namespacing, which is the seam the new
work extends. `material_color.ts` and the anchors stay; only the rect stamping dies.

## Architecture boundaries and ownership

- Selection and rendering are orthogonal. Object `visual_states` owns selection among
  complete forms; it never mutates one form into another. Each selected SVG form separately
  declares or omits material-rendering semantics.
- A static form remains opaque and requires neither an SVG layer recipe nor injected DOM
  merely because it belongs to a discrete collection.
- A form whose root declares `data-vlab-rendering="material"` always receives material
  normalization and validation, whether or not an object currently references it. An object
  material binding gates runtime mutation of that already-validated form; it does not select
  the asset-processing policy.
- After selection, exact root `data-vlab-rendering="material"` selects the compiled
  material-layer path; absence identifies a static opaque form. Invalid or misplaced reserved
  attributes fail. An object-level `fill_height` binding uses generated manifest handles and
  the injection seam: material identity recolors semantic groups by role and volume/capacity
  updates the compiler-derived reveal plus optional `bottom`, `body`, and `surface` parts. It
  creates no painted runtime rect and never queries/mutates anchors or authored `data-vlab-*`.
  `anchor_liquid_bounds`,
  `anchor_liquid_clip`, and existing capacity fields remain compiler inputs for material
  forms; no new object YAML target, binding, or token is introduced. A declared unbound
  material form is still compiled/validated and displays authored fallback paint without
  state mutation. Structural anchors are never semantic paint layers.
- `assets/<category>/<name>.svg` remains the sole authored source. An ordinary source copies
  verbatim to `dist/assets/svg/<category>/<name>.svg`; a material-declared source compiles
  through `generated/material_svg/<category>/<name>.svg`, and only that derived artifact
  copies to the same served path. Publishing a material source directly is a build error.
  The generated SVG manifest maps logical `asset_name` only to the final served relative URL.
- Logical `asset_name` remains the object-authoring key. If M2 chooses physical
  subdirectories, the generated SVG manifest resolves that key to a path; protocol and
  object YAML do not acquire directory paths.
- The **protocol material registry** is `materials.yaml`. Its closed two-key schema
  (`label`, `display_color`) stays the sole authored material color, per
  `MATERIAL_YAML_FORMAT.md`.
- The **object material binding** is the object YAML `visual_states` entry. It says which
  object state uses material identity or amount; it does not describe SVG geometry.
- The **SVG layer recipe** is the semantic rendering description associated with one SVG.
  It owns `layer_name`, `layer_kind`, `paint_role`, and `adjustment`, but
  never a material name, protocol name, hex color, authored runtime id, or path index. It
  is embedded in the material-rendered SVG; there is no external recipe file.
- An **object layer**, also called a **material-rendered layer** when
  `layer_kind: material`, is one semantic SVG region described by the recipe.
- The refactored SVG always owns geometry, document stacking order, and the interior clip.
  One recipe remains reusable across any number of protocol material registries because it
  contains no material-specific value.
- The **derived liquid-region manifest** is `generated/liquid_regions.json`. It is generated
  from normalized semantic SVG structure and supplies runtime handles; it is never authored.

### Canonical material-SVG contract

The ratified authored carrier is ordinary SVG groups plus a reserved, closed
`data-vlab-*` attribute vocabulary. This is clearer than encoding structured values in
`class`, supports repeated paint roles without duplicate ids, and leaves `id` reserved for
unique structural anchors such as `anchor_liquid_clip`. Current stripping of arbitrary
`data-*` attributes is a pipeline behavior to change deliberately, not a reason to choose a
less expressive contract.

```svg
<svg data-vlab-rendering="material" ...>
  <defs>
    <clipPath id="anchor_liquid_clip">...</clipPath>
  </defs>
  <g data-vlab-layer-name="glass_back"
     data-vlab-layer-kind="fixed">...</g>
  <g data-vlab-layer-name="liquid_body"
     data-vlab-layer-kind="material"
     data-vlab-paint-role="base">...</g>
  <g data-vlab-layer-name="liquid_highlight"
     data-vlab-layer-kind="material"
     data-vlab-paint-role="highlight"
     data-vlab-adjustment="0.18">...</g>
  <g data-vlab-layer-name="liquid_shadow"
     data-vlab-layer-kind="material"
     data-vlab-paint-role="shadow"
     data-vlab-adjustment="-0.15">...</g>
  <g data-vlab-layer-name="glass_front"
     data-vlab-layer-kind="fixed">...</g>
</svg>
```

- One semantic layer is one `<g>` and may contain one or many paths. Paint metadata lives
  on the group, so shape-to-path conversion cannot silently detach it from one child.
- `data-vlab-rendering="material"` is allowed only on the root `<svg>`. Any reserved
  `data-vlab-*` attribute in an SVG without that exact root declaration fails rather than
  falling through the ordinary policy. In a material SVG, every other reserved attribute is
  valid only on a direct root-child semantic group; unknown, misplaced, or role-incompatible
  attributes fail, and nested ordinary artwork groups carry none.
- `data-vlab-layer-name` is unique within one SVG form and is authored semantic identity,
  not a DOM id. Runtime identity is generated from the normalized document.
- Initial `paint_role` values are the closed set `base`, `highlight`, and `shadow`.
  A paint role may repeat across distinct, uniquely named material groups; every
  material-rendered SVG requires at least one `base` group, not exactly one. `adjustment`
  is per group, required for highlight/shadow and forbidden for `base` and fixed layers. It
  uses only the ASCII finite-decimal grammar `-?[0-9]+(?:\.[0-9]+)?`: highlight is
  `0 < value <= 0.5`; shadow is `-0.5 <= value < 0`; no plus sign, exponent, whitespace,
  `NaN`, or infinity spelling is accepted. A new role is an explicit schema-and-renderer
  extension, not an asset-local escape hatch.
- SVG document order is the sole stacking authority. All material groups form one contiguous
  middle band: any fixed groups before that band are derived back layers, and any fixed
  groups after it are derived front layers. Validation rejects an empty material band, a
  material group after a front fixed group, or any fixed group inside the material band.
- Literal donor fills and strokes remain source fallbacks. The compiler derives canonical
  paint handles; authored SVG never contains a runtime CSS-property or instance id. `base`
  uses the resolved `display_color` unchanged. Highlight/shadow add their adjustment to
  normalized OKLCH lightness, clamp to `[0, 1]`, preserve hue, reduce chroma only as needed
  for sRGB gamut, and serialize lowercase `#rrggbb`; no per-asset color source exists.
- `anchor_liquid_clip` and `anchor_liquid_bounds` remain unique structural anchors. The
  material compiler applies the vessel clip to its stationary derived region after semantic
  normalization, avoiding the ordinary normalizer's destructive simple-clip flattening. An
  authored semantic layer `<g>` may not carry `clip-path`; ordinary child artwork follows
  ordinary supported clip rules.

M2 compared this approved contract with reserved class tokens in the full probe matrix.
Changing the carrier after that evidence requires updating this section and explicit user
approval; silently falling back to incidental current behavior is forbidden.

### Asset-type-aware normalization

There is one normalizer implementation with shared parsing, security, geometry, bbox, and
serialization code, plus two explicit policies:

- Ordinary policy: static forms, including every form in a discrete collection, continue
  through the current visual-normalization behavior.
- Material policy: root `data-vlab-rendering="material"` selects semantic normalization and
  validation independently of object bindings.
  Recognized semantic attributes and group boundaries are canonicalized and preserved;
  transforms may be baked into child geometry but semantic groups and child order survive;
  no merge crosses a semantic layer; the material clip and bounds anchors survive; and the
  normalized result is validated before runtime compilation.

The material policy is not a forked second normalizer. It is a first-class policy in the
same pipeline so security and geometry fixes cannot drift between asset types.

### Authoritative layer for each concern

Stated once so no two layers can disagree silently:

| Concern                        | Authority                                                         | Everything else                                                                                                     |
| ------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Stacking order                 | the SVG's document order                                          | the validator derives fixed back/material/fixed front bands from document order; no authored metadata duplicates it |
| Semantic layer identity        | recipe `layer_name`                                               | runtime handles and DOM ids are derived; raw authored DOM ids are not the contract                                  |
| Semantic classification        | recipe `layer_kind`, `paint_role`, and `adjustment`               | fill values are never re-read to infer a role after import                                                          |
| Material color                 | `materials.yaml` scalar `display_color` via `material_color.ts`   | the recipe carries no material or color; the SVG's literal fills are fallbacks only                                 |
| Object-to-material behavior    | object YAML `visual_states`                                       | neither the recipe nor the SVG names protocol materials                                                             |
| Derived shades and fill level  | runtime (`oklch_shade.ts`, `liquid_paint.ts`)                     | nothing else computes a color or a level                                                                            |
| Runtime element lookup         | generated manifest plus the SVG-injection seam in `inject_svg.ts` | no authored runtime id and no consumer string concatenation, per `MATERIAL_CONVENTION.md`                           |
| Derived liquid-region manifest | generator output only                                             | never authored, never a tiebreak; regenerated every build                                                           |

On disagreement the build fails loudly. No layer silently wins.

### Naming conventions this work follows

Per `docs/REPO_STYLE.md`, `docs/PYTHON_STYLE.md`, and `docs/TYPESCRIPT_STYLE.md`:

| Surface                                     | Convention                                                                                                       | Examples from this plan                                                                                                                         |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Python and TypeScript filenames             | snake_case, lowercase ASCII and underscores                                                                      | `refactor_liquid_svg.py`, `svg_liquid_census.py`, `gen_liquid_regions.py`, `svg_layer_recipe_validator.py`, `oklch_shade.ts`, `liquid_paint.ts` |
| Test filenames                              | snake_case with the tier's prefix                                                                                | `test_svg_layer_recipe_validator.py`, `test_oklch_shade.mjs`, `test_liquid_render.spec.ts`                                                      |
| Durable reference docs                      | SCREAMING_SNAKE_CASE `.md`                                                                                       | `MATERIAL_CONVENTION.md`, `MATERIAL_LINT.md`                                                                                                    |
| Working plan and report docs                | snake_case `.md`                                                                                                 | `liquid_asset_census.md`, `structured_subpart_render_model.md`                                                                                  |
| Recipe fields and enum values               | snake_case                                                                                                       | `layer_name`, `layer_kind`, `paint_role`, `adjustment`, `liquid_body`                                                                           |
| Semantic layer names                        | snake_case                                                                                                       | `bottle_back`, `liquid_body`, `liquid_shadow_left`, `glass_front`                                                                               |
| Runtime handles and CSS custom properties   | derived from asset plus `layer_name`, never authored API                                                         | exact encoding chosen by the generator and opaque to consumers                                                                                  |
| TypeScript type, interface, and class names | CamelCase, per `docs/TYPESCRIPT_STYLE.md` ("Reserve CamelCase for class names, type names, and interface names") | `ColorResult`, `SvgLayerRole`, `LiquidPaintPlan`                                                                                                |
| TypeScript function names                   | follow the file being edited; new material-layer files use snake_case to match `material_color.ts`               | `resolve_color_result`, `resolve_visual_state`, and new `resolve_liquid_paint`                                                                  |
| Generated artifacts                         | snake_case filenames under `generated/`                                                                          | `liquid_regions.json`                                                                                                                           |

Measured note on the TypeScript function row: `docs/TYPESCRIPT_STYLE.md` fixes filename and
type casing but states no rule for function identifiers, and the runtime is genuinely split
today. Of the exported functions under `src/scene_runtime/`, 51 are snake_case
(`resolve_color_result`, `resolve_visual_state`, `validate_correct_target`) and about 64 are
camelCase (`resolveSvgAnchor`, `namespaceSvgIds`, `runStructuralGuards`). `ColorResult` is a
type, so its CamelCase is the documented rule; `resolveSvgAnchor` is a function, so it sits
in the undocumented half. This plan follows the local file rather than imposing a global
rule: work inside `inject_svg.ts` keeps that file's camelCase, and the new material-layer
files match `material_color.ts` with snake_case. Normalizing the split repo-wide is a
separate style decision and stays out of this plan's scope.

### Tool flow (non-circular)

The semantic contract is processed in one direction:

1. M2 inventories the two asset-taxonomy axes and probes `id`, reserved `class` tokens, and
   reserved `data-vlab-*` attributes through normalization, manifest sanitization, repeated
   runs, nested/repeated groups, clipping, shape conversion, and duplicate injection.
2. M2 records current behavior and the cost of each carrier. Current stripping is evidence
   about migration work, not a veto over a clearer authored contract.
3. Under the approved contract, the normalizer gains one material policy alongside the ordinary
   policy. It canonicalizes the selected embedded vocabulary, preserves semantic group
   boundaries and ordering, and refuses transformations that would erase meaning.
4. A material-SVG validator runs on the normalized output, not only the source. It proves
   full classification, one contiguous material band, unique layer names, allowed roles, clip/bounds
   integrity, and no cross-boundary merge.
5. `pipeline/gen_liquid_regions.py` consumes only the validated normalized structure,
   derives opaque runtime paint and element handles, and emits the liquid-region manifest.
6. The refactor tool consumes the ratified semantic contract. TypeScript consumes only the
   generated manifest; neither infers meaning from fills, classes, or arbitrary DOM.

- The object YAML `visual_states` block still owns where and why color appears.
- TypeScript owns only: derive the palette, write custom properties, and apply the generic
  gravity-part operations. It contains no asset-name or vessel-family branch.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component                                                                                                                                                                                      | Review boundary                                                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1 / WS-CENSUS         | `tools/svg_liquid_census.py`, report under `docs/active_plans/audits/`                                                                                                                         | read-only; no asset or runtime edits                                                                                                                                         |
| M2 / WS-RECIPE         | two-axis inventory and carrier evidence; decision records; ratified material/object/SVG specification alignment; then the material normalizer, validator, and `pipeline/gen_liquid_regions.py` | WP-R1 documentation ratification is complete; no durable pilot asset, directory migration, or runtime edits before WP-R2 semantic normalization is implemented and validated |
| M3 / WS-ART            | `tools/refactor_liquid_svg.py`, pilot assets                                                                                                                                                   | asset art only; one pilot per vessel shape                                                                                                                                   |
| M4 / WS-RUNTIME        | `src/scene_runtime/renderer/liquid_paint.ts`, `oklch_shade.ts`, `inject_svg.ts` seam                                                                                                           | runtime only; consumes M2/M3 output                                                                                                                                          |
| M5 / WS-FLEET + WS-ORG | finish the two non-pilot variable-volume families; then implement the recursive asset registry and behavior directories                                                                        | artwork acceptance precedes the registry/path migration, so an asset moves only once                                                                                         |
| M6 / WS-FLEET          | reclassify legacy material-effect bindings, retain only true variable-volume bindings, remove `anchor_material_renderer.ts`                                                                    | one owner, one patch, tree green throughout                                                                                                                                  |
| M7 / WS-DOCS           | post-cutover removal of migration-only ordinary-overlay prose, `MATERIAL_LINT.md` activation, `docs/CHANGELOG.md`                                                                              | later cleanup and enforcement; it does not re-ratify the M2 design                                                                                                           |
| M8 / WS-SUBPART        | spike on `96well_pcr_plate.svg` plus a decision record                                                                                                                                         | evidence and verdict only; conversion is a follow-on plan                                                                                                                    |

## Milestone plan

| M   | Title                                                     | Summary                                                                                                                                   | Goal                                                                                              |
| --- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| M1  | Asset census                                              | Cluster colors per anchored asset, classify refactor difficulty                                                                           | Know the real fleet cost before converting anything                                               |
| M2  | SVG asset taxonomy and semantic pipeline contract         | Inventory selection/rendering axes, settle organization, measure carriers, ratify and implement material normalization                    | Asset organization and normalized material semantics are unambiguous before durable conversion    |
| M3  | Art refactor tool and pilot                               | Semantic groups and optional gravity parts on 3 pilots                                                                                    | One bottle, one tube, one pipette provably right                                                  |
| M4  | Runtime paint                                             | OKLCH derivation and gravity-part writer                                                                                                  | Browser evidence of color + level on the pilots                                                   |
| M5  | True volume fleet and source organization                 | Convert Falcon 50 mL and microtube; after all five families pass, add the recursive registry and move the fleet into behavior directories | True volume assets are complete and 119 SVG sources are navigable without leaking paths into YAML |
| M6  | Overlay retirement                                        | Reclassify legacy effects, keep only true volume bindings, delete the rect renderer and its tests                                         | No overlay code path exists                                                                       |
| M7  | Post-cutover migration-prose removal and anti-return lint | Remove temporary ordinary-overlay migration prose after the code cutover; activate lint that enforces the already-ratified model          | The hack cannot come back through the docs                                                        |
| M8  | Structured-subpart decision record                        | Spike plus written verdict on wells, lanes, rack slots                                                                                    | The question is answered and closed, not left open                                                |

### Milestone: M1 asset census

- Depends on: none.
- Deliverables: `tools/svg_liquid_census.py`; a census report under
  `docs/archive/audits/liquid_asset_census.md` with one row per anchored asset:
  distinct fills, candidate liquid family (colors inside `anchor_liquid_clip` bounds and
  outside the shared neutral palette), path count in that family, and a classification of
  `mechanical`, `hand_art`, or `no_liquid_drawn`.
- Workstreams: WS-CENSUS.
- Entry criteria: none.
- Exit criteria: every one of the 33 anchored assets classified; the plate, gel-cassette,
  and rack assets additionally reported so M8 has evidence; report states how many assets
  have no drawn liquid and therefore need art added.
- Parallel-plan ready: yes.

### Milestone: M2 SVG asset taxonomy and semantic pipeline contract

WP-R1 completed the M2 architecture gate: self-describing material SVG, asset
organization, the exact embedded carrier, and canonical specification are
ratified. WP-R2 has implemented and verified the normalizer, validator, derived
manifest compiler, and validation-only asset-taxonomy gate. M3 now owns durable
pilot art and build-loop activation; M4 owns runtime consumption.

- Depends on: M1.
- Deliverables: a two-axis inventory of all current SVG forms and their object references;
  `docs/archive/audits/svg_asset_taxonomy.md` and
  `docs/archive/decisions/svg_asset_taxonomy.md`; a carrier comparison table in
  `docs/archive/audits/svg_semantic_carrier_matrix.md`; and
  `docs/archive/decisions/svg_material_semantic_contract.md`. WP-R1 has also
  ratified the canonical anti-regression alignment in `SVG_PIPELINE.md`, all six
  `MATERIAL*.md` specifications, both `OBJECT*.md` specifications,
  `SPEC_DESIGN_CHECKLIST.md`, and `docs/FILE_STRUCTURE.md`. WP-R2 has implemented
  material policy in `tools/normalize_svg_v3.py`, normalized-output validation,
  `pipeline/gen_liquid_regions.py`, and the validation-only asset-taxonomy gate.
- Workstreams: WS-RECIPE.
- Entry criteria: census classifications exist.
- Decision procedure:
  1. Inventory current source paths, filenames, `asset_name` references, and
     `visual_states` selections. Classify selection as `single` or
     `discrete_collection` and each SVG form as `static` or `material_rendered`. Explicitly
     report cross-axis combinations.
  2. Compare organization by descriptive naming alone, existing object `visual_states`, a
     small generated or authored collection manifest, and physical subdirectories. Record
     the resolver, attribution, picker, validation, and documentation changes each option
     requires. Prefer the smallest source-of-truth model that makes collections and
     rendering capability mechanically discoverable.
  3. Build pilot cases for one path per role, multiple paths sharing a role, nested groups,
     fixed back/front layers, clipping, shape-to-path conversion, two instances, and an
     intentionally invalid asset.
  4. Measure `id`, reserved class tokens, and reserved data attributes against preservation,
     deterministic repeated output, authoring clarity, normalized-output validation, and
     runtime derivation. Include the normalizer and the later manifest sanitizer; passing
     only one stage is not success.
  5. Confirm the approved semantic-group carrier and material-policy guarantees against the
     evidence. The design selects `data-vlab-*`; a future replacement requires a decision
     record and explicit user approval, never an implementation fallback.
  6. Implement the material policy, validate its normalized output, generate opaque runtime
     handles, and prove independent duplicate instances. Ordinary SVGs remain on the
     existing policy.
- Exit criteria: the taxonomy record selects how collections and rendering capability are
  discovered, whether physical relocation is warranted now or in a bounded follow-on, and
  the filename rule (`<descriptive_asset_name>_<state>.svg`, never a bare state filename);
  the semantic-contract record confirms the approved carrier and explicit normalization
  guarantees; the organization and closed vocabulary are recorded before durable recipe
  authoring begins; the normalized-output validator rejects unknown fields and enum values,
  missing or duplicate layer names, no `base` paint role, recipe/SVG
  mismatches, and any material name, protocol name, hex color, path index, or authored
  runtime id; it detects a semantic-boundary merge; the generator emits the derived
  manifest from the pilot; repeated normalization is byte-stable; `pytest tests/` green.
- Parallel-plan ready: no. The experiment, organization decision, and implementation form
  one serial gate.

### Milestone: M3 art refactor tool and pilot

- Depends on: M2.
- Deliverables: `tools/refactor_liquid_svg.py`; three refactored pilot assets covering
  three vessel shapes (`bottle_medium_pink.svg`, `falcon_15ml.svg`,
  `serological_pipette.svg`); the WP-T0 spike verdict recorded.
- Workstreams: WS-ART, plus WS-RUNTIME for the WP-T0 spike.
- Entry criteria: the material semantic contract and normalizer policy are ratified, and
  normalized pilot inputs validate with no unclassified object layer.
- Exit criteria: the WP-T0 plain-group contract passes with recorded browser evidence; each
  pilot carries one contiguous material band with stable layer names, a compiler-clipped
  gravity-part region, and generated paint handles for fill and stroke; semantic normalization
  (`tools/svg_validate.py`, `tools/normalize_svg_v3.py`) passes; the refactor-fidelity
  tolerance in the visual gate is met.
- Parallel-plan ready: yes (one work package per pilot after the tool lands).
- Status: accepted. The Falcon pilot falsified whole-liquid translation and the three pilot
  assets now prove the gravity-part contract: stationary bottom, Y-only middle-body scaling,
  fixed-shape surface translation, zero-volume hiding, and stationary clipping.

### Milestone: M4 runtime paint

- Depends on: M3.
- Deliverables: `src/scene_runtime/renderer/oklch_shade.ts`;
  `src/scene_runtime/renderer/liquid_paint.ts`; the injection-time liquid seam in
  `inject_svg.ts`; Playwright spec covering material x volume on the pilots.
- Workstreams: WS-RUNTIME.
- Entry criteria: pilots refactored.
- Exit criteria: for each pilot, three materials x {0, 25, 60, 100} percent render with
  derived shades, the level surface tracks the fraction within tolerance, zero liquid pixels
  outside the interior clip, and an empty vessel shows clear glass.
- Parallel-plan ready: no. The shade module, the seam, and the writer are one tight
  contract; splitting them creates more interface churn than it saves.
- Status: accepted. `liquid_paint.ts`, OKLCH derivation, and the injection seam implement
  generic bottom/body/surface operations; final contact artifacts exercise all five assets.

### Milestone: M5 true volume fleet and source organization

- Depends on: M4.
- Deliverables:
  1. embedded gravity-part semantics for `falcon_50ml.svg` and `microtube.svg`, completing
     the five true continuously variable families;
  2. accepted volume contact pages for all five families;
  3. after that acceptance, one recursive unique-stem asset registry and the physical
     source move into `static/`, `binary_state/`, `multi_state/`, and
     `variable_volume/`, with every flat-path consumer migrated and directory placement
     validated against object YAML plus SVG semantics.
- Workstreams: WS-FLEET, then WS-ORG.
- Entry criteria: M4 exit evidence recorded.
- Exit criteria: all five true volume families pass the visual gate through
  `liquid_paint.ts`; logical `asset_name` values remain stable; source lookup is recursive;
  no executable flat-path assumption remains; directory placement is linted; provenance and
  final publication still resolve; `./check_codebase.sh` is green before and after the move.
- Parallel-plan ready: partially. The two art conversions are independent. The shared
  registry and physical move are one serial migration and begin only after both pass.
- Status: accepted. All five variable-volume assets pass the contact gate, and WP-ORG moved
  the fleet into validated behavior directories without changing logical `asset_name` values.

### Milestone: M6 overlay retirement

- Depends on: M5.
- Deliverables: every legacy `fill_height` or `material_tint` object binding is classified
  as a true variable-volume binding, a discrete complete-form state, a structured-region
  concern, or an invalid legacy effect. True volume bindings retain their existing closed
  vocabulary while selecting converted material forms;
  `anchor_material_renderer.ts` and its tests are removed along with their call sites.
- Workstreams: WS-FLEET (single owner, serial by design).
- Entry criteria: both M5 art conversions and the subsequent organization migration landed.
- Exit criteria: `liquid_paint.ts` is the only material render path in `src/`;
  `./check_codebase.sh` and `./run_playwright_tests.sh` green; every existing protocol
  walkthrough still completes through visible UI.
- Parallel-plan ready: no. One owner touches the shared YAML surface and performs the
  removal in one patch, which keeps the tree green at every step.
- Status: accepted. The legacy-effect disposition audit is complete;
  `anchor_material_renderer.ts` is removed and `liquid_paint.ts` is the sole object-level
  material renderer.

### Milestone: M7 post-cutover migration-prose removal and anti-return lint

- Depends on: M6.
- Deliverables: removal of the migration-only ordinary-overlay prose retained during the
  cutover from the already-ratified material and object specifications; activation of the
  `MATERIAL_LINT.md` rule set that fails the build on a reintroduced overlay rect or an
  anchored asset without a valid embedded semantic contract selected by M2; and a
  `docs/CHANGELOG.md` entry. M7 does not reopen or defer M2's canonical specification
  ratification.
- Workstreams: WS-DOCS.
- Entry criteria: the overlay path is gone from `src/`.
- Exit criteria: zero occurrences of the overlay render model in the five specs; the lint
  fails on a deliberately reintroduced rect and passes on the converted tree;
  `pytest tests/test_markdown_links.py` green.
- Parallel-plan ready: yes (one work package per spec file, lint owned by one package).
- Status: accepted. Migration-only prose is removed, anti-return lint is active, and the
  2026-08-01 changelog records the Falcon failure and durable replacement.

### Milestone: M8 structured-subpart decision record

This milestone delivers an ANSWER, not a maybe. Converting grid subparts is out of scope for
this plan; deciding whether they should be converted is in scope and completes here.

- Depends on: M7.
- Deliverables: a runtime spike that drives 96 independent per-cell material states through
  the production generated-geometry subpart renderer, with measured update timing; a written decision
  record under `docs/archive/decisions/structured_subpart_render_model.md`; a
  corresponding statement in `MATERIAL_STRUCTURED_AREAS.md`.
- Workstreams: WS-SUBPART.
- Entry criteria: M7 landed.
- Exit criteria: the record answers four questions with evidence: do per-cell addressable
  elements exist in the art; can 96 cells hold independent material state through this
  mechanism; does a full-plate write update within frame budget; does generated geometry
  already satisfy spatial correspondence as well or better. The record states one verdict:
  convert in a follow-on plan, or keep generated geometry for grids permanently and say why
  in the spec. Either verdict closes the question.
- Parallel-plan ready: no. One spike, one record, one owner.
- Status: accepted. The measured spike and decision record keep generated geometry
  permanently for wells, rack slots, and gel lanes.

## Workstream breakdown

### Workstream: WS-CENSUS

- Goal: replace guesses about fleet cost with measured per-asset data.
- Owner: one `reviewer`-class agent (read-only).
- Work packages: WP-C1.
- Needs: nothing.
- Provides: the classification every later milestone schedules against.
- Review boundary, when modifying the repository: writes only the census report and the
  census tool.

### Workstream: WS-RECIPE

- Goal: make SVG selection/rendering organization explicit and make embedded material
  semantics survive a deliberate, validated normalization path.
- Owner: one `coder`-class agent.
- Work packages: WP-R0, WP-R1, WP-R2.
- Needs: WS-CENSUS classifications.
- Provides: a two-axis asset taxonomy decision, approved canonical semantic SVG contract,
  material-normalization policy, and derived liquid-region manifest.
- Review boundary, when modifying the repository: scratch pilot and decision/spec/tooling
  only until the decision; no runtime edits and no durable fleet asset edits in M2.

### Workstream: WS-ART

- Goal: turn flat donor path lists into semantic, parameterized liquid geometry.
- Owner: one `expert_coder`-class agent (this is the hardest judgment work in the plan).
- Work packages: WP-A1, WP-A2.
- Needs: approved semantic SVG contract plus validated normalized pilot assets.
- Provides: the asset contract the runtime binds to.
- Review boundary, when modifying the repository: `assets/equipment/variable_volume/*.svg` and the refactor
  tool only.

### Workstream: WS-RUNTIME

- Goal: derive a coordinated palette and drive the generic gravity parts from one level
  parameter, without rebuilding DOM.
- Owner: one `expert_coder`-class agent.
- Work packages: WP-T1, WP-T2, WP-T3.
- Needs: refactored pilots.
- Provides: the render path that replaces the overlay.
- Review boundary, when modifying the repository: `src/scene_runtime/renderer/` only.

### Workstream: WS-FLEET

- Goal: finish the two remaining true variable-volume assets, organize the SVG source
  fleet by behavior, classify the legacy effect bindings, and delete the overlay.
- Owner: one `expert_coder`-class owner for volume art, followed by one registry/migration
  owner and one retirement owner.
- Work packages: WP-F1, WP-F2, WP-ORG, then WP-F5 in that order.
- Needs: proven mechanism from M4.
- Provides: an overlay-free tree.
- Review boundary, when modifying the repository: WP-F1/WP-F2 own only their asset art,
  WP-ORG owns registry/path migration, and WP-F5 alone owns the object-YAML effect surface
  and renderer removal.

### Workstream: WS-DOCS

- Goal: make the specification describe the real model so the hack has no source.
- Owner: one `planner`-class agent plus one `coder`-class agent for the lint.
- Work packages: WP-D1, WP-D2.
- Needs: overlay code deleted.
- Provides: the anti-return gate.
- Review boundary, when modifying the repository: `docs/specs/`, `docs/CHANGELOG.md`, and
  the lint test.

## Work packages

### Work package: WP-C1 color-family census

- Owner: WS-CENSUS.
- Touch points: `tools/svg_liquid_census.py`,
  `docs/archive/audits/liquid_asset_census.md`.
- Depends on: none.
- Acceptance criteria: per asset, the tool reports distinct fills, the fills whose geometry
  falls inside the `anchor_liquid_clip` bounds, the fills shared with the neutral palette
  seen across the donor variants, the candidate liquid path count, each candidate's
  document-order position relative to the liquid band, a merge estimate (how many
  paths share fill, opacity, stroke, and adjacency), and a classification of `mechanical` /
  `hand_art` / `no_liquid_drawn`. Each classification is checked automatically: the tool
  renders a per-asset highlight sheet that paints each candidate element in isolation, so
  the proposal is verifiable from an artifact rather than from someone's eye. Color
  clustering is a proposal engine only; the committed identity of an element is its assigned
  semantic layer name, and later milestones read recipe semantics rather than fill values.
- Evidence or review, when useful: the report names the three donor bottles as the
  neutral-palette reference and shows the pink family it recovers.
- Obvious follow-ons: order M5's asset batches by classification, cheapest first.

### Work package: WP-R0 asset-taxonomy inventory and self-describing pilot

- Owner: WS-RECIPE.
- Touch points: `docs/archive/audits/svg_asset_taxonomy.md`; a copy of
  `assets/equipment/bottle_medium_pink.svg` and comparison artifacts under `test-results/`;
  no durable asset move or recipe file.
- Depends on: WP-C1.
- Acceptance criteria:
  1. Record every SVG's logical `asset_name`, source path, object references, selection
     model, rendering model, and collection membership. Derive discrete collections from
     object `visual_states`, not filename guessing; use naming only as a validation signal.
  2. Confirm that `power_supply_off` / `power_supply_on`, heat-block open/closed forms, and
     `label(...)` set-point displays need no internal semantic SVG contract. Flag any
     collection containing both static and material-rendered forms.
  3. Report whether the current flat directory and filenames already express each axis;
     enumerate hard-coded flat-path consumers in pipeline, validation, picker, attribution,
     and docs; compare the cost of descriptive naming, a collection manifest, recursive
     directories, or a combination.
  4. Check filename quality. A discrete form carries family identity plus state in
     snake_case, for example `power_supply_off.svg` or `centrifuge_lid_open.svg`; a bare
     `open.svg`, `closed.svg`, `on.svg`, or `off.svg` is invalid. Capacity/size is included
     only when it distinguishes variants.
  5. Build a carrier matrix for `id`, reserved class tokens, and reserved `data-*`
     attributes across: one path per role; several paths sharing a role; nested role groups;
     fixed back/front groups; a shape converted to path; clipped material content; repeated
     normalization; duplicate asset instances; and an intentionally invalid asset.
  6. For each carrier, measure normalizer output, manifest-sanitizer output, group/order
     preservation, repeated roles, authoring clarity, validator precision, and deterministic
     runtime-handle derivation. Do not mark a carrier successful because one early stage
     preserves it.
  7. Record current destructive behavior explicitly. The known baseline includes arbitrary
     `data-*` loss in manifest sanitization, semantic data loss during basic-shape-to-path
     conversion, and rejection of `clip-path` on a `<g>` target. These are migration inputs,
     not permanent constraints on the material policy.
- Evidence or review, when useful: comparison table, preserved-before/after markup,
  generator output, failure text for the invalid case, and a two-instance browser screenshot
  under `test-results/`.
- Status: complete. WP-R1 ratified the architecture and WP-R2 implemented and verified
  the approved semantic pipeline; durable pilot art and build-loop activation remain M3.

### Work package: WP-R1 asset organization and semantic-contract ratification (complete)

- Owner: WS-RECIPE.
- Touch points: `docs/archive/audits/svg_asset_taxonomy.md`,
  `docs/archive/audits/svg_semantic_carrier_matrix.md`,
  `docs/archive/decisions/svg_asset_taxonomy.md`, and
  `docs/archive/decisions/svg_material_semantic_contract.md`; `docs/specs/SVG_PIPELINE.md`;
  all six `docs/specs/MATERIAL*.md` files; both `docs/specs/OBJECT*.md` files;
  `docs/specs/SPEC_DESIGN_CHECKLIST.md`; and `docs/FILE_STRUCTURE.md`.
- Depends on: WP-R0.
- Acceptance criteria:
  1. Select the asset-organization source of truth: existing `visual_states`, a small
     collection manifest, directory layout, or an explicit combination with non-overlapping
     ownership. The record says whether a 117-file relocation belongs in this plan or a
     bounded follow-on and lists the exact pipeline/validation consumers affected.
  2. Keep the two axes independent: collection membership never implies mutable SVG, and a
     material-rendered form can belong to either a single selection or a discrete
     collection.
  3. Record self-describing SVG as the approved sole recipe authority. No external recipe
     filename, schema, parser, or synchronization rule is introduced.
  4. Compare the embedded carriers primarily on clarity, repeated-role support, structured
     metadata, deterministic canonicalization, and validation quality. Current accidental
     preservation ranks below those design properties because the pipeline is owned here.
  5. Record the approved `data-vlab-*` group contract and its measured behavior. A future
     carrier replacement requires a concrete defect, decision-record update, and explicit
     user approval. `id` stays for unique structural anchors or generated runtime identity;
     `class` stays for styling.
  6. Record the approved closed semantic vocabulary: `layer_name`; `layer_kind` with values
     `material` or `fixed`; `paint_role` with values `base`, `highlight`, or `shadow`;
     signed numeric `adjustment` for highlight/shadow. `layer_name` is unique within one
     SVG form; paint roles may repeat across different named material groups; every
     material-rendered SVG has at least one `base` group. The syntax has no free-form
     extension map.
  7. Record material-policy guarantees: recognized semantic groups/attributes survive or
     canonicalize deterministically; group and child order survives; transforms may bake
     into geometry without deleting the group; no merge crosses a semantic boundary;
     material clip/bounds anchors survive; all material groups form one contiguous
     document-order band between optional fixed back and fixed front groups; and normalized
     output must validate before compilation.
  8. Obtain user approval before a future new binding contract item or vocabulary extension
     enters the specs.
- Evidence or review, when useful: the decision record includes the carrier table, current
  failure probes, exact canonical markup, and the selected guarantees.
- Status: accepted and incorporated in the canonical specifications. WP-R2 has implemented
  and verified the ratified material policy. The canonical material/object specification
  alignment remains the anti-regression boundary; no M3 pilot/build activation or M4 runtime
  implementation is thereby complete.

### Work package: WP-R2 material normalizer, normalized validator, and derived manifest

- Owner: WS-RECIPE.
- Touch points: `tools/normalize_svg_v3.py`; the material-SVG validator under `validation/`;
  `tests/test_svg_layer_recipe_validator.py`; `pipeline/gen_liquid_regions.py`;
  `pipeline/gen_svg_manifest.py`; `docs/FILE_STRUCTURE.md`;
  `docs/CODE_ARCHITECTURE.md`. `pipeline/build_generated.sh` integration waits until M3
  supplies durable pilot assets.
- Depends on: WP-R1.
- Acceptance criteria: the shared normalizer detects the material root declaration and
  applies the ratified material policy while ordinary files retain current behavior. A
  second pass is byte-identical. The normalized-output validator rejects an unknown
  semantic attribute or enum, missing or duplicated `layer_name`, no `base` paint role,
  an invalid material band (split material groups, a fixed group inside the band, or a
  material group after a front fixed group), invalid adjustment, material or protocol name,
  literal semantic color, path index, authored runtime id, lost clip/bounds anchor, and any
  merge across layers. It validates every form whose root declares material rendering,
  whether or not an object currently binds it; static forms remain opaque even inside a
  discrete collection. Object material bindings gate runtime mutation, not validation.
  It also rejects generic state-only filenames and verifies collection membership through
  the M2-selected authority. The generator emits a test liquid-region manifest from the
  normalized pilot, including opaque derived runtime handles and palette adjustments,
  without re-reading fill colors. The build publishes ordinary sources verbatim but publishes
  a material-declared form only from its
  `generated/material_svg/<category>/<name>.svg` artifact to the normal final
  `dist/assets/svg/<category>/<name>.svg` URL; direct source publication fails and the SVG
  manifest exposes only the final relative URL. The pipeline addition updates both structure
  docs in the same patch as required by `AGENTS.md`.
- Evidence or review, when useful: tests keep SVG inputs inline under `tmp_path`; no
  `tests/fixtures/`, rejected-carrier parser, or duplicated normalizer is created.
- Obvious follow-ons: M3 writes durable pilot recipes and activates build integration.
- Status: complete. WP-R2 implemented and verified the material normalizer, normalized-output
  validator, derived liquid-region manifest compiler, publication planner, and validation-only
  taxonomy gate. It intentionally did not add durable pilot art, change the build loop, or add
  runtime manifest consumption.

### Work package: WP-T0 semantic-group runtime spike

- Owner: WS-RUNTIME (runs during M3, before any fleet commitment).
- Touch points: a scratch page plus `tests/playwright/test_liquid_contract_spike.spec.ts`.
- Depends on: WP-A2 (one pilot is enough).
- Acceptance criteria: recorded browser evidence, not assumption, for each assumption the
  architecture rests on:
  1. Generated paint properties reach every path inside a semantic group.
  2. The compiler-applied `anchor_liquid_clip` remains stationary around the generated region.
  3. Two injected copies receive distinct derived runtime handles without authored layer
     ids or consumer selector construction.
  4. Mutating body scale, surface translation, and reveal inside one injected instance
     affects only that instance; bottom geometry keeps no transform.
  5. Runtime code resolves semantic layers exclusively through the generated manifest and
     injection seam, never by querying `data-vlab-*` directly.
- Evidence or review, when useful: fail M3 if any assumption fails. A fallback requires a
  contract revision and user approval; it is not an asset-specific special case.
- Obvious follow-ons: the proven group contract is what WP-A1 emits and WP-T3 binds.
- Status: complete. The focused browser spec proves inherited group paint, compiler clipping,
  independent duplicate instances, instance-local transforms, and manifest-only runtime
  resolution against the published pilot artifacts.

### Work package: WP-A1 refactor tool

- Owner: WS-ART.
- Touch points: `tools/refactor_liquid_svg.py`.
- Depends on: WP-R2.
- Acceptance criteria: the tool consumes a donor asset plus reviewed census classification,
  writes the ratified semantic groups and attributes, invents no runtime identity, and is
  idempotent (a second run is a no-op).
  1. Emit ordinary `<g>` layers in document order. Each semantic group may contain one or
     many paths; material groups form one contiguous band, with optional fixed groups before
     and after it, so the compiler can derive one stationary liquid region without reordering
     art. Each material group also declares exactly one gravity part.
  2. Keep donor `fill` and `stroke` values as literal fallbacks in source. Variant colors
     appear on strokes too, so the compiler must bind both. Generated paint handles, not the
     authoring tool, parameterize the normalized runtime artifact.
  3. Derive fixed back and fixed front layers from the material band's document-order
     boundaries; fail rather than reorder if fixed and material groups interleave. Never
     merge across different semantic groups.

  `anchor_liquid_bounds` is retained as the reveal frame. The 22-35 path band is a review
  heuristic reported by the tool, not a pass/fail criterion.

- Evidence or review, when useful: literal donor fill and stroke fallbacks in the authored
  SVG mean an asset opened directly in a browser looks exactly like the donor. The generated
  runtime artifact may add opaque CSS paint handles while retaining those fallbacks, making
  the before/after visual diff a real check rather than a formality.
- Obvious follow-ons: run it over the remaining M5 Falcon 50 mL conversion; the empty
  microtube donor requires reviewed liquid artwork rather than path classification.
- Status: complete. The idempotent tool and its focused behavioral tests are green.

### Work package: WP-A2 pilot refactors

- Owner: WS-ART.
- Touch points: `assets/equipment/bottle_medium_pink.svg`, `assets/equipment/falcon_15ml.svg`,
  `assets/equipment/serological_pipette.svg`, and their embedded material semantics.
- Depends on: WP-A1.
- Acceptance criteria: three shapes refactored; `tools/svg_validate.py` and
  `tools/normalize_svg_v3.py` pass; visual diff against the pre-refactor render is within
  tolerance; each asset's interior clip excludes cap, rim, label, and exterior shading.
- Evidence or review, when useful: before/after PNGs via `tools/svg_to_html_render.mjs`
  written to `test-results/`.
- Obvious follow-ons: hand the shapes to WS-RUNTIME as the binding contract.
- Status: accepted. All three pilots use the approved optional gravity parts; the earlier
  single-translation screenshots remain falsification evidence, not acceptance evidence.

### Work package: WP-T1 OKLCH shade derivation

- Owner: WS-RUNTIME.
- Touch points: `src/scene_runtime/renderer/oklch_shade.ts`,
  `tests/test_oklch_shade.mjs`.
- Depends on: WP-A2.
- Acceptance criteria: given one `#rrggbb` and a list of `{paint_role, adjustment}` entries,
  the module returns one `#rrggbb` per entry, computed in OKLCH so positive highlight and
  negative shadow adjustments stay perceptually even across hues. Round-trip and ordering
  properties are asserted (a `highlight` result is lighter than `base`, a `shadow` result darker, output
  stays in sRGB gamut) rather than hardcoded hex constants,
  per `docs/PYTEST_STYLE.md`. The implementation applies the closed adjustment grammar and
  range, uses `L' = clamp(L + adjustment, 0, 1)`, preserves hue, reduces chroma only for
  sRGB gamut, and serializes lowercase hex; it introduces no per-asset color source.
  `material_color.ts` stays the only name-to-color resolver and is consumed unchanged.
- Evidence or review, when useful: a table of one material rendered across the five roles.
- Obvious follow-ons: reuse for any future material-condition color work.
- Status: complete. Property tests cover base preservation, highlight/shadow lightness
  ordering across hues, lowercase sRGB output, gamut fitting, and invalid adjustments.

### Work package: WP-T2 injection-time liquid seam

- Owner: WS-RUNTIME.
- Touch points: `src/scene_runtime/renderer/inject_svg.ts`.
- Depends on: WP-R2.
- Acceptance criteria: injection consumes the derived manifest and builds a host-local map
  from opaque generated handles to element references while parsing the normalized SVG.
  Runtime consumers neither query `data-vlab-*` nor construct selectors or ids. Unique
  structural anchors continue through the existing namespacing seam. Two placements of the
  same asset in one scene stay independent.
- Evidence or review, when useful: extend `tests/playwright/test_svg_id_namespacing.spec.ts`
  with two bottles at different volumes and colors.
- Obvious follow-ons: the same seam is what the M8 subpart spike measures against.
- Status: complete. Injection parses the aggregate manifest, validates opaque handles, and
  exposes host-scoped operations; browser evidence proves duplicate-instance isolation.

### Work package: WP-T3 liquid paint writer

- Owner: WS-RUNTIME.
- Touch points: `src/scene_runtime/renderer/liquid_paint.ts`,
  `src/scene_runtime/renderer/visual_state_resolver.ts`,
  `tests/playwright/test_liquid_render.spec.ts`.
- Depends on: WP-T1, WP-T2.
- Acceptance criteria: on a state change the writer sets one generated paint property per
  material-rendered manifest entry on the host, using explicit resolved hex values rather than
  `color-mix()` so older SVG rendering paths stay supported. It leaves every `bottom`
  transform untouched, applies a Y-only matrix about the shared lower anchor to every
  `body`, translates every `surface` by the same Y offset without scaling, and updates a
  reveal boundary in stationary vessel coordinates. It adds, removes, and reorders no DOM
  node. `empty` or zero volume hides the liquid group so clear art shows through. A
  resolver failure routes to the existing degrade path and paints nothing.
- Evidence or review, when useful: Playwright matrix of three materials x four volumes per
  pilot, with a leakage check that no liquid-role pixel falls outside the interior clip and
  a tolerant comparison rather than exact pixel identity.
- Obvious follow-ons: WP-F5 retires the old renderer once the matrix is green fleet-wide.
- Status: accepted. The gravity-part matrix and duplicate-instance isolation evidence are
  recorded; the former single-transform implementation is retired.

### Work package: WP-F1..WP-F2 remaining variable-volume art

- Owner: WS-FLEET, one owner per asset.
- Touch points: `assets/equipment/falcon_50ml.svg` and
  `assets/equipment/microtube.svg`, each with embedded gravity-part groups.
- Depends on: WP-T3.
- Acceptance criteria: both assets validate and pass the same zero-to-full contact-page
  gate as the three pilots. The microtube's empty donor receives reviewed liquid artwork;
  the conversion tool must not pretend absent donor paths were classified.
- Evidence or review, when useful: one screenshot sheet per asset under `test-results/`.
- Obvious follow-ons: WP-ORG begins only after both sheets are accepted.
- Status: accepted. The Falcon 50 mL and microtube are part of the regenerated five-asset
  contact evidence.

### Work package: WP-ORG recursive registry and behavior directories

- Owner: WS-ORG, single owner.
- Touch points: all flat-path consumers listed in
  `audits/svg_asset_taxonomy.md`; source SVG paths under `assets/equipment/`;
  attribution, architecture, file-structure, and authoring documentation.
- Depends on: WP-F1, WP-F2.
- Acceptance criteria: one recursive registry resolves globally unique filename stems;
  object YAML retains stable logical `asset_name` values; the generated manifest owns final
  URLs; validation derives and enforces `static`, `binary_state`, `multi_state`, and
  `variable_volume` placement; every tracked SVG is moved exactly once; provenance remains
  resolvable; the fresh build, codebase check, and object-reference tests pass.
- Evidence or review, when useful: before/after category counts, a zero-result flat-path
  consumer grep, and successful fresh generated/dist rebuilds.
- Obvious follow-ons: WP-F5 operates on the organized source tree.
- Status: accepted. The recursive unique-stem registry and behavior-directory projection are
  live; registry, reference, build, and codebase gates pass.

### Work package: WP-F5 overlay retirement

- Owner: WS-FLEET, single owner.
- Touch points: the 46 `fill_height` and 2 `material_tint` object YAML files as an audit
  surface; only bindings classified as true variable volume remain amount-driven;
  `src/scene_runtime/renderer/anchor_material_renderer.ts` and its tests and call sites.
- Depends on: WP-ORG.
- Acceptance criteria: object YAMLs retain the existing target vocabulary while
  `liquid_paint.ts` becomes the only material render path in `src/`;
  `./check_codebase.sh` and `./run_playwright_tests.sh`
  green; every protocol walkthrough completes through visible UI.
- Evidence or review, when useful: a walkthrough run log plus the Playwright summary.
- Obvious follow-ons: M7 removes the remaining migration-only ordinary-overlay prose and
  activates the anti-return lint after this code cutover.
- Status: accepted. The disposition audit classifies all historical bindings; only the five
  true variable-volume forms retain object-level liquid rendering.

### Work package: WP-D1 post-cutover migration-prose removal

- Owner: WS-DOCS.
- Touch points: only the already-ratified specification files that still contain
  migration-only ordinary-overlay prose after WP-F5, plus `docs/CHANGELOG.md`.
  `docs/specs/MATERIAL_YAML_FORMAT.md` retains its material-registry schema; WP-R1 updated
  its boundary text so it cannot be read as an SVG-layer recipe authority.
- Depends on: WP-F5.
- Acceptance criteria: the render-effect table keeps the two-layer split (`material_tint`
  is identity, `fill_height` is amount) and defines their material-form mechanism as role
  recolor and gravity-part level operations. `anchor_liquid_bounds` / `anchor_liquid_clip` remain existing
  binding/compiler inputs, not runtime overlay targets, and no `liquid_region` or new YAML
  token is introduced. After code cutover, every remaining migration-only ordinary-overlay
  sentence is deleted, not softened. Per `docs/PRIMARY_DESIGN.md` vocabulary closure, no
  open map or free-form field is introduced.
- Evidence or review, when useful: an independent `reviewer`-class pass confirming zero
  overlay-model sentences survive.
- Obvious follow-ons: `docs/CHANGELOG.md` entry naming the removal and the reason.
- Status: accepted. The independent review found and removed the final material-design
  migration sentence; permanent lint now rejects the retired model.

### Work package: WP-D2 anti-return lint

- Owner: WS-DOCS.
- Touch points: `tests/test_material_render_model.py` (or the existing material lint test),
  `docs/specs/MATERIAL_LINT.md`.
- Depends on: WP-D1.
- Acceptance criteria: the check fails when `src/` creates an SVG `rect` for a
  material-declared form, when a declared material SVG lacks its root declaration or has
  invalid normalized semantics, when a material layer is unclassified, and when runtime
  material code queries authored semantic attributes directly. An object-level
  `fill_height` binding on an ordinary selected form fails. Failures name the file and rule.
- Evidence or review, when useful: run the check against a scratch reintroduction of the
  rect and show the failure text.
- Obvious follow-ons: none; this is the closure gate.
- Status: accepted. The repository-wide `src/` lint fails on deliberate overlay, semantic
  access, material-structure, and ordinary-form binding regressions before generation.

## Acceptance criteria and gates

- Per-patch gate: `./check_codebase.sh` green; `pytest tests/` green; touched docs pass
  `pytest tests/test_markdown_links.py`.
- Integration gate: `./run_playwright_tests.sh` green, including the new liquid matrix;
  every existing protocol walkthrough still completes through visible UI per contract
  item 4 in `docs/PRIMARY_CONTRACT.md`.
- Visual gate, with stated tolerances (never exact pixel identity):
  - Refactor fidelity: a refactored asset rendered with no custom properties set differs
    from its pre-refactor render in at most 1 percent of non-transparent pixels, counting
    only pixels whose perceptual difference exceeds a small delta-E threshold. Anti-aliasing
    along re-grouped edges is expected and does not fail the gate.
  - Containment: no material-role pixel appears outside a 1 CSS-pixel dilation of the
    interior clip boundary. The dilation absorbs anti-aliasing fringe; anything beyond it is
    real leakage.
  - Level accuracy: the rendered liquid surface sits within 2 percent of vessel height of
    the commanded `volume / capacity` fraction.
  - Empty state: at zero volume, no material-role pixel is painted anywhere.
  - The 22-35 path band is a review heuristic in the tool report, not a gate.
- Independent review gate: one `reviewer`-class agent audits M6 and M7 for a surviving
  overlay path in code or prose.

## Test and verification strategy

- pytest (`tests/`): ordinary-versus-material normalizer dispatch, semantic-attribute and
  group preservation, normalization idempotency, normalized-output validation, full-cover
  classification, contiguous-material-band enforcement, semantic-boundary merge rejection, and manifest
  generation. A small inline SVG string is written to `tmp_path` per case; no
  `tests/fixtures/` directory.
- Node (`node --import tsx --test 'tests/test_*.mjs'`): OKLCH derivation properties and
  level-transform arithmetic, asserted as ordering and range properties.
- Playwright (`tests/playwright/`): the material x volume matrix per converted asset, the
  two-instance namespacing case, and the leakage check. Screenshots numbered per step into
  `test-results/`.
- Walker: existing walkthroughs are the regression net for material state. The material-area
  oracle probes compiled liquid groups for vessels; `well_plate_96` and other structured
  areas remain on generated geometry under the accepted M8 verdict.

## Migration and compatibility policy

Hard cutover, no dual path. Each asset was unconverted or converted during migration; no
fallback renderer remains after M6. During the historical M5 conversion, the overlay renderer
served unconverted assets while batches landed one at a time with a green tree between them;
M6 then performed the single removal patch after every batch was in. `generated/` is rebuilt
every run, so no persisted artifact can drift; per `docs/PRIMARY_SPEC.md` no schema-version
field is introduced.

## Risk register

| Risk                                                                                                             | Impact                                                                                                   | Trigger                                                                                                                      | Owner      | Mitigation                                                                                                                                                                              |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A donor color is shared by liquid and by glass or cap                                                            | Recoloring bleeds outside the liquid                                                                     | Census reports a color inside and outside the interior clip                                                                  | WS-CENSUS  | Classification is per semantic layer, not per color, so the two regions receive different `layer_kind` values; the census flags the pair for review                                     |
| A white, translucent, or glass-colored donor path still depends on the liquid level                              | A bubble, highlight, side tint, or donor-level seam remains fixed while the surface moves                | Contact page exposes a material-associated feature above the requested surface or an empty-vessel seam at the donor meniscus | WS-ART     | Run geometry-matched variant comparison as evidence, then physically review all candidates and shared white/translucent paths; fixed layers alone must render a continuous empty vessel |
| A path merge changes stacking and breaks the art                                                                 | Highlights jump in front of or behind glass                                                              | Visual diff after WP-A1 pass 2                                                                                               | WS-ART     | The tool refuses a merge when a differently-classified path sits between the candidates in document order, and the before/after diff is a milestone exit gate                           |
| Re-export or optimization drops semantic attributes or groups                                                    | A material asset looks correct at rest but cannot render state                                           | Material-mode normalization or re-import loses a `data-vlab-*` group                                                         | WS-RECIPE  | The material policy deliberately preserves/canonicalizes the contract and validates normalized output; source-only success never passes the build                                       |
| Ordinary clip flattening consumes the liquid region                                                              | The stationary reveal or moving surface loses its containment boundary, or normalization rejects the SVG | A semantic `<g>` carries `clip-path` through the ordinary pass                                                               | WS-RECIPE  | Source retains the unique clip anchor unreferenced; material compilation applies it to the stationary runtime region after semantic normalization                                       |
| A vessel has material layers separated by fixed art                                                              | One contiguous compiled liquid region cannot preserve the artwork's required ordering                    | Census reports a material group after fixed front art or fixed art inside the material band                                  | WS-CENSUS  | The contiguous-band contract rejects the form. Redraw it into fixed back/material/fixed front order or create a reviewed future semantic-contract extension before conversion           |
| An asset draws no liquid at all                                                                                  | Cannot tag what does not exist                                                                           | Census classification `no_liquid_drawn`                                                                                      | WS-ART     | Hand-author one liquid body path shaped to the interior clip, then treat it as `mechanical`                                                                                             |
| A second ramp shares the liquid family: a colored label border on a bottle, a plastic body on a closed microtube | A green media bottle gets a green label, or a red microtube's contents turn red with its plastic         | Semantic classification review                                                                                               | WS-RECIPE  | No extra schema. `layer_kind: fixed` keeps that group at donor values; `layer_kind: material` opts it into recoloring                                                                   |
| Gravity parts meet poorly                                                                                        | A seam or gap appears between cone, body, and surface                                                    | Contact page at 10, 25, 75, and 100 percent                                                                                  | WS-ART     | Require stationary-coordinate reveal, shared authored join datums, and browser evidence for every converted family                                                                      |
| Derived shades lose contrast for dark materials                                                                  | Liquid unreadable against the workspace                                                                  | OKLCH derivation of a dark `display_color`                                                                                   | WS-RUNTIME | Clamp derived lightness into the gamut and reuse `tools/contrast_calculator.py` for the readability check                                                                               |
| Fleet conversion stalls mid-way                                                                                  | Two render models coexist longer than planned                                                            | A sequenced package slips                                                                                                    | WS-FLEET   | Keep art acceptance, source organization, and overlay retirement as separately green packages; the overlay stays until the classified retirement package                                |
| Spec rewrite softens rather than deletes                                                                         | The hack returns a third time                                                                            | Review of WP-D1                                                                                                              | WS-DOCS    | The independent review gate checks for zero surviving overlay-model sentences, and WP-D2 lint makes reintroduction a build failure                                                      |

## Rollout and release checklist

- [x] M1 census report published and read before any conversion is scheduled.
- [x] Two-axis SVG asset inventory and organization decision recorded.
- [x] Carrier matrix covers normalizer, sanitizer, shape conversion, clipping, repeated
      roles, invalid semantics, idempotency, and duplicate instances.
- [x] Approved self-describing material-SVG contract confirmed by the carrier matrix;
      material normalizer policy, normalized-output validator, and derived manifest green.
- [x] Whole-liquid translation falsified; gravity-part hypothesis accepted and audited for
      the primary volume-vessel families.
- [x] Pilot evidence (three shapes, three materials, four volumes) recorded.
- [x] All five true variable-volume families pass their volume contact pages. The bottle has
      an authored 85% request ceiling, so 85%, 90%, and 100% render identically with the same
      meniscus. The 50 mL conical's 100% endpoint aligns the bottom of its concave meniscus with
      the drawn 50 mL graduation. The microtube surface renders a complete elliptical rim, and
      its stretchable body begins at the scaled lower edge of that meniscus with no visible
      body pixels above it. The user's later acceptance of every non-microtube row resolved the
      earlier tentative 70% bottle-cap proposal in favor of the rendered 85% ceiling.
- [x] Recursive registry and behavior-directory move landed as one green migration.
- [x] Existing object YAML bindings retained; `liquid_paint.ts` is the only object-level
      material render path.
- [x] Migration-only ordinary-overlay prose removed and anti-return lint fails on a deliberate
      reintroduction.
- [x] Structured-subpart decision record written and signed: generated geometry remains
      permanent for structured material areas.
- [x] At the original plan-closure gate, `./check_codebase.sh` passed all 5 checks,
      `pytest tests/` passed 5503 cases, the build passed, and
      `./run_playwright_tests.sh` passed 101 cases. Current totals live in the
      latest changelog entry rather than rewriting this historical evidence.
- [x] Every protocol walkthrough completes through visible UI in the full Playwright run.
- [x] Final five-asset contact HTML/PNG artifacts regenerated after the full browser gate.
- [x] `docs/CHANGELOG.md` entry written for human commit.

## Documentation close-out requirements

- Active plan / progress tracker: no duplicate `svg_liquid_rendering.md` tracker is created.
  The repository's current convention keeps this active root-level plan as the source of
  truth until explicit archival; the historical copy requirement is obsolete.
- `docs/CHANGELOG.md` entry: under `### Behavior or Interface Changes`, the move from
  overlay rect to in-SVG semantic liquid; under `### Removals and Deprecations`, the
  deletion of the overlay renderer and its target vocabulary; under
  `### Decisions and Failures`, why the overlay returned twice and what now prevents it.
- Archive / closure notes: at close, move the active plan to `docs/archive/` with `git mv`
  so history is preserved, per `docs/REPO_STYLE.md`.
- Repository rules this work follows: Python tools use tabs, full type annotations, and
  `source source_me.sh && python3` invocation per `docs/PYTHON_STYLE.md`; tests keep their
  inputs inline in `tmp_path` per `docs/PYTEST_STYLE.md`; the generator lives under
  `pipeline/` because it emits into `generated/`, the two authoring helpers live under
  `tools/` because they are development-time only, and the pipeline addition updates
  `docs/FILE_STRUCTURE.md` and `docs/CODE_ARCHITECTURE.md` in the same patch per
  `AGENTS.md`.

## Patch plan and reporting format

- Patch 1: census tool plus report (M1).
- Patch 2: two-axis asset inventory, carrier matrix, and decision records (M2 evidence).
- Patch 3: approved material normalizer policy, normalized-output validator, manifest
  generator, and architecture docs (M2 implementation).
- Patch 4: refactor tool plus three pilot assets (M3).
- Patch 5: OKLCH module, injection seam, liquid writer, pilot Playwright matrix (M4).
- Patch 6: Falcon 50 mL and microtube conversions plus the combined five-family acceptance
  sheet (M5 art).
- Patch 7: recursive registry, behavior-directory validation, and physical source move
  after all five variable-volume assets pass (M5 organization).
- Patch 8: legacy-effect classification plus removal of the rect renderer (M6).
- Patch 9: spec closeout plus anti-return lint (M7).
- Patch 10: subpart spike plus decision record (M8).

Each patch reports: files touched, gate commands run with their output, and persistent,
gitignored visual evidence paths under `rendered-reports/`.

## Open questions and decisions needed

- M2's semantic carrier work is complete. Its original flat-directory decision was
  superseded by user review: behavior directories are approved, with the implementation
  intentionally sequenced as WP-ORG after the five true variable-volume assets pass.
  Any future semantic contract or vocabulary extension still requires explicit user
  approval.
- M3 architecture decision resolved: the Falcon matrix and semantic inspector showed that
  translating a finite group moves its lower boundary as well as its surface. The approved
  model decomposes liquid into optional `bottom`, `body`, and `surface` parts. See
  `audits/liquid_gravity_part_hypothesis.md`. Do not restore whole-group translation or hide
  the defect with bottom overscan.
- M3 geometry and visual gate tooling: `tools/svg_semantic_inspector.py` reports normalized
  semantic-layer, clip, and level-frame bounds without inferring physical volume. Its
  `--compare-variants` mode geometry-matches sibling donors and proposes paint-changing
  material candidates while separately flagging shared white/translucent art for physical
  review; neither output is automatic classification.
  `tools/liquid_volume_contact_page.mjs` uses the real compiled injection and liquid writer to
  serialize one or more assets at a reviewed volume series into self-contained HTML and PNG
  persistent, gitignored evidence under `rendered-reports/liquid_volume_contacts/`.
  `tools/render_liquid_volume_contact_sheet.sh` rebuilds the published assets and renders
  all five variable-volume families with one command. Diagnostics distinguish requested fill,
  rendered fill, and whether the compiler-owned ceiling clamped the request. The bottle's
  authored 85% ceiling makes every request from 85% through 100% render identically.
- Manager/subagent decision procedure for the structured-subpart question (the scope item the
  user left open, now converted into M8's deliverable rather than left pending):
  - Decision owner or dedicated class: WS-SUBPART runs the spike; the `architect` class
    signs the record.
  - Evidence and decision rule: if `96well_pcr_plate.svg`, `gel_cassette.svg`, and
    `microtube_rack_8.svg` carry addressable per-cell elements AND the spike shows 96
    independent per-cell states updating within frame budget, the record recommends a
    follow-on conversion plan. Otherwise the record fixes generated geometry as the correct
    grid mechanism and `MATERIAL_STRUCTURED_AREAS.md` states that split as deliberate.
    Either way M8 ends with a written verdict, so nothing is carried forward as an open item.
- M4 surface-role decision resolved: fixed-shape surface groups reuse the closed `base`,
  `highlight`, and `shadow` paint roles while `data-vlab-liquid-part="surface"` owns their
  motion. No fourth paint role is needed.
