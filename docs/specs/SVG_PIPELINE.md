# SVG asset pipeline

## Purpose

This document is the canonical specification for how SVG art is stored,
copied into the built site, loaded at runtime, and isolated per render
instance. It defines the ownership boundary between the SVG asset pipeline
and the rest of the codebase.

SVG art is authored as source files under `assets/<category>/`. At build time
an ordinary source is copied verbatim into the served site, while a
material-declared source is compiled through its semantic pipeline before its
derived artifact is copied to that same served location. A generated
relative-path manifest maps each logical asset name to its final served URL.
At runtime the renderer chooses one of two render modes per object: a
static `<img>`, or fetched-and-namespaced inline SVG DOM. SVG markup is
never bundled into the JavaScript bundle.

The boundary statement governs everything below:

- The SVG pipeline owns asset loading, DOM injection, per-render-instance
  id namespacing, and bare-anchor lookup inside a rendered SVG instance.
- The material layer owns semantic material state, color resolution, and
  render-effect declarations. Material vocabulary is defined in
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md), not here.

## Language-neutral art and accessible labels

Source SVG art is language-neutral. Instrument identity, state, instructions,
and other student-facing prose belong in layout-manager DOM labels or object
data, giving future localization and accessibility work a clear ownership
boundary. No i18n system is being implemented now; this boundary keeps it
unblocked. When imported art contains prose, remove it and recreate it outside
the SVG. Text-to-path conversion is never a way to pass normalization or
blind-recognition assessment with embedded prose.

Sparse, approved physically intrinsic markings may remain when they are part
of an instrument: numbers, scientific units or symbols, polarity, graduations,
and plate row or column coordinates. Use them sparingly. The SVG normalization
gate does not accept live `text`, `tspan`, or `textPath` elements. Prefer
authored path geometry for the few approved intrinsic markings that remain. If
an imported intrinsic marking arrives as live SVG text, prefer
`rsvg-convert --format svg` to prepare a separate path-only SVG before running
the repository normalizer. The repository does not integrate a desktop SVG
editor. Legacy or imported provenance is never an exception for prose. Librsvg
is not a runtime or build dependency.

Blind recognition is diagnostic evidence for instrument identity, not a
universal perfection gate. Improve ambiguous assets where the evidence reveals
an important pedagogical risk, while accepting non-material ambiguity once the
scene communicates the intended learning task.

## Visual acceptance dialect

The canonical visual target for repository equipment art is **de-shadowed
Servier Medical Art**: the Bioicons files credited to the Servier collection,
adapted to this repository's language-neutral and material-rendering rules.
Other Bioicons contributor collections are not style references; their visual
languages vary too widely to define a coherent laboratory scene.

This target preserves a scientifically recognizable, object-appropriate
silhouette and projection. It uses thin dark-charcoal outer and structural
contours; a pale cyan or blue glass/plastic body where appropriate; off-white
highlights; muted dark mechanical parts; and a controlled object or material
accent. Material colors remain owned by the material pipeline. A retained
detail must clarify function or material at normal scene size: typical examples
are a graduation band, cap ribs, lens, control, electrode, or pipette tip.

Remove detached floor shadows with the repository normalizer's narrow
floor-shadow operation before cropping the asset. This does not require flat
art: retain only the local shade, liquid depth, recess, or highlight needed to
read a cavity, glass, liquid, control, or physical depth. Avoid dense internal
contours, repeated near-identical color steps, white backplates, chrome-like
reflections, and other decorative modeling that does not survive scene-scale
review.

Every selected state family shares a stable silhouette, projection, viewBox,
canvas, safe padding, and contour/fill roles. The visible state difference is
authored inside that fixed frame; a state swap must not look like object motion
or rescaling. Material-rendered forms additionally preserve the semantic
groups, anchors, clips, and paint-role contract defined below. New artwork
without a suitable Servier source may use this grammar, but must be an original
scientifically recognizable drawing rather than an imitation of an unrelated
source asset.

## Source-tree boundary

| Tree                 | Contents                                                     | Hand-edited? |
| -------------------- | ------------------------------------------------------------ | ------------ |
| `assets/<category>/` | Authored source SVG art, the single tracked source of truth. | YES          |
| `src/`               | Authored TypeScript only.                                    | YES          |
| `generated/`         | Gitignored; regenerated by build scripts from `assets/`.     | NO           |
| `dist/`              | Disposable build output; served site.                        | NO           |

`generated/` is gitignored and regenerated from `assets/` before tsc and
the bundler. The single tracked source of truth for SVG art is the file
under `assets/<category>/`; PR diffs show authored source SVGs, not derived
strings. `dist/` is ephemeral; the build script writes it and is free to
remove it.

## SVG file output

Source SVGs live under `assets/<category>/<name>.svg`. The source is always
the single tracked truth. At build time an ordinary SVG copies directly to the
served site. A material-declared SVG is normalized, sanitized, and compiled to
`generated/material_svg/<category>/<name>.svg`; only that derived artifact is
then copied to the same served path. This mirrors the bundled-font copy step
the build script already performs for `assets/fonts/*.woff2` into
`dist/assets/fonts/`.

| Path role             | Shape                                          |
| --------------------- | ---------------------------------------------- |
| Authored source       | `assets/<category>/<name>.svg`                 |
| Material intermediate | `generated/material_svg/<category>/<name>.svg` |
| Final served output   | `dist/assets/svg/<category>/<name>.svg`        |

An ordinary SVG's served file is byte-identical to its authored source. A
material-declared SVG's served file is byte-identical to its compiled derived
artifact, never directly to the authored source. Direct publication of a
material-declared source is a build error. No per-asset string constant is
emitted into any TypeScript bundle. The generated SVG manifest maps only a
logical `asset_name` to the final served relative URL; it exposes neither the
authored source path nor an intermediate generated path.

## Asset taxonomy and material-rendered SVG contract

This is the canonical contract for the material-SVG compiler and its gates.
Material-declared forms use the compiled semantic path in the live renderer.
Ordinary forms remain opaque complete SVGs.

SVG assets have two independent axes:

| Axis                          | Values                          | Authority                                         |
| ----------------------------- | ------------------------------- | ------------------------------------------------- |
| Selection model               | `single`, `discrete_collection` | Object YAML `visual_states` `kind: svg` case maps |
| Rendering model, per SVG form | `static`, `material_rendered`   | The SVG form's root declaration after validation  |

A discrete collection is a set of complete SVG forms selected by object YAML.
There is no collection manifest or directory-derived selection. Each form is
independently static or material-rendered. Static forms are complete opaque
files; numeric displays remain object-level text overlays.

Author sources under the behavior directories `assets/equipment/static/`,
`binary_state/`, `multi_state/`, or `variable_volume/`. Placement is a validated
projection of object-YAML selection cardinality and the SVG root rendering
declaration; directories do not become a second behavior authority. A recursive
unique-stem registry preserves logical YAML names and stable flattened public
URLs across source moves. New or renamed selected forms use descriptive lowercase
snake_case names carrying family and state, such as `power_supply_off.svg` or
`microtube_1_5ml_closed.svg`. Bare `open.svg`,
`closed.svg`, `on.svg`, and `off.svg` are invalid. Do not add a
`material_rendered` suffix merely to duplicate SVG metadata.

### Ownership and processing boundary

A material-rendered SVG is self-describing; no SVG layer-recipe sidecar exists.

| Concern                                                           | Authority                        |
| ----------------------------------------------------------------- | -------------------------------- |
| Material identity and `display_color`                             | Protocol `materials.yaml`        |
| Selected form and material/amount binding                         | Object YAML `visual_states`      |
| Geometry, document order, clips, source fallback, semantic recipe | The SVG form                     |
| Opaque runtime element/paint handles                              | Generated liquid-region manifest |

The root declaration `data-vlab-rendering="material"` is the sole rendering
declaration. Its optional `data-vlab-max-fill-percent` integer ceiling (1 through 100) limits the form's rendered fill height. Its optional
`data-vlab-min-fill-percent` integer floor (1 through 99) leaves a zero request
empty and clamps every nonzero request below the floor up to it; when both are
present, the floor cannot exceed the ceiling. A conical form may instead declare
the closed `data-vlab-body-start-fill-percent` finite decimal in `(0, 100)`, the
volume percentage at which its liquid reaches the measured lower anchor of the
stretchable body. Every such SVG receives material normalization and validation,
even if unreferenced. Object material binding gates runtime mutation only; it
never gates material processing.

A non-conical form may instead declare `data-vlab-fill-height-exponent`, a
finite decimal in `(0, 10]`. It maps normalized effective fill `q` to height as
`q^exponent`, where `q` is divided by the form ceiling or 100. It cannot be
combined with `data-vlab-body-start-fill-percent`.

### Material dispatch

After object YAML selects a complete form, an exact root
`data-vlab-rendering="material"` identifies the compiled material-layer path.
A reserved attribute with an invalid value or at an invalid location is an
error.

An object-level `fill_height` binding uses the generated liquid-region manifest
and injection seam: material identity recolors semantic material groups by role,
and volume/capacity drives the compiler-derived gravity parts. It creates no
runtime rect and does not query or mutate structural anchors or authored
`data-vlab-*`.

The compiler derives private base-surface and body-join datums from the
artwork. The first is the volume-reading coordinate; the second is the
stretchable body's top. Runtime aligns the scaled body to the scaled join datum,
so an oval meets the body at its tangent line rather than leaving side gaps or
placing rectangular corners above the tangencies. These are derived geometry,
not authored calibrations.

For a material form, `anchor_liquid_bounds`, `anchor_liquid_clip`, and the
existing capacity fields remain compiler inputs. The compiler validates and
resolves those structural anchors into the generated manifest and derived liquid
region; it does not ignore them and this patch introduces no new object YAML
target, binding, or token. A declared material form without a runtime material
binding is still normalized, compiled, and validated, but displays its authored
fallback paint without state mutation. Structural anchors are never semantic
paint layers.

### Closed authored semantic vocabulary

Only a root `<svg data-vlab-rendering="material">` is material-rendered. The
root declaration is allowed only on the root `<svg>` and only with the exact
value `material`. Its semantic layers are direct root-child `<g>` elements.
Ordinary artwork groups may nest within a semantic group, but semantic groups
may not nest.

| Attribute                           | Required on                  | Allowed value and validation                                                                                                                                        |
| ----------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data-vlab-layer-name`              | every semantic group         | Unique lowercase snake_case name within the form                                                                                                                    |
| `data-vlab-layer-kind`              | every semantic group         | `fixed` or `material`                                                                                                                                               |
| `data-vlab-paint-role`              | `material` group             | `base`, `highlight`, or `shadow`; roles may repeat                                                                                                                  |
| `data-vlab-adjustment`              | `highlight` / `shadow` group | ASCII finite decimal; `highlight`: `0 < value <= 0.5`; `shadow`: `-0.5 <= value < 0`                                                                                |
| `data-vlab-liquid-part`             | `material` group             | `bottom`, `body`, or `surface`; optional parts use only these closed values                                                                                         |
| `data-vlab-max-fill-percent`        | root material SVG            | Optional integer from `1` through `100`; resolved fill percentages above it render at this ceiling                                                                  |
| `data-vlab-min-fill-percent`        | root material SVG            | Optional integer from `1` through `99`; zero remains empty and nonzero resolved percentages below it render at this floor, which cannot exceed the optional ceiling |
| `data-vlab-body-start-fill-percent` | root material SVG            | Optional finite decimal strictly between `0` and `100`; conical volume-to-height calibration reaches the measured body anchor at this percentage                    |
| `data-vlab-fill-height-exponent`    | root material SVG            | Optional finite decimal in `(0, 10]`; non-conical normalized fill maps to height as `q^exponent`, mutually exclusive with body-start calibration                    |

`data-vlab-paint-role` and `data-vlab-liquid-part` are forbidden on fixed groups. `data-vlab-adjustment` is
required for `highlight` and `shadow`, and forbidden on `base` and fixed groups.
Its syntax is the strict ASCII finite-decimal grammar `-?[0-9]+(?:\.[0-9]+)?`:
there is no `+`, exponent, whitespace, `NaN`, or infinity spelling. At least
one material group must have role `base`; it need not be unique. Every material
group declares one liquid part. `bottom` remains fixed in vessel coordinates,
`body` scales only in Y about its lower anchor, and `surface` translates in Y.
For a form with body-start calibration, a surface below that percentage also
uniformly scales about the liquid-bounds horizontal center and surface datum by
`effective_fill / body_start_fill`; at or above the body start it has scale 1.
An asset omits a part it does not need.

`data-vlab-rendering`, optional `data-vlab-max-fill-percent`, optional
`data-vlab-min-fill-percent`, optional `data-vlab-body-start-fill-percent`, and optional `data-vlab-fill-height-exponent`
are allowed only on the root. The remaining reserved attributes are allowed only on direct
root-child semantic groups, with the role-dependent requirements in the table.
Any `data-vlab-*` attribute anywhere in an SVG without the exact rendering
declaration is a build error, not ordinary SVG input. Unknown, misplaced, or
role-incompatible reserved attributes are also build errors. Ordinary nested
artwork groups inside semantic groups carry no reserved attributes. There is no
free-form extension map: a carrier, role, or vocabulary extension requires a
specification edit and user approval.

No authored stacking attribute exists. SVG document order is the sole stacking
authority. Material groups form exactly one nonempty contiguous top-level band;
fixed groups before it derive the back phase and fixed groups after it derive
the front phase. A split or interleaved band fails validation. Visible/renderable
geometry outside semantic groups also fails, except `defs` and structural
anchors.

`id` is reserved for unique structural anchors such as
`anchor_liquid_clip` and `anchor_liquid_bounds`; `class` is styling only.
Authored source retains literal `fill` and `stroke` fallback paint and contains
neither authored runtime IDs nor generated CSS paint properties/handles. The
material compiler may add opaque handles only in normalized/generated output.

### Material normalization, manifest, and runtime boundary

There is one normalizer implementation with shared parsing, security, geometry,
bbox, and serialization work, but two explicit policies. The ordinary policy
continues visual normalization for static forms. The material policy is selected
only by the root declaration above and deliberately preserves or canonicalizes
the closed vocabulary, semantic groups and order, structural anchors, and
document boundaries. It never merges or flattens across semantic layers.

The material policy validates both normalized and sanitized output, derives a
liquid-region manifest with opaque runtime handles, and is byte-stable on repeat.
It deliberately preserves or canonicalizes the closed semantic contract and rejects
an authored semantic-layer `<g>` carrying `clip-path`. `anchor_liquid_clip` remains
in `defs`, and the compiler applies it to its derived region after semantic
normalization. Ordinary child artwork remains subject to the ordinary supported
clip rules; ordinary-policy sanitizer and group-clip limitations do not relax the
material policy.

The build loop publishes validated material assets through this compiler.

`anchor_liquid_bounds` is compiler-only: the generated manifest carries its
validated numeric rectangle and the compiler removes the anchor from the
published material artifact. The generated region retains a stationary reference
to `anchor_liquid_clip`. The compiler also derives a reveal boundary in stationary
vessel coordinates, so bottom artwork never moves and body clipping does not move
with its Y transform. Runtime uses generated handles only; it never queries or
mutates either authored anchor.

The bounds rectangle defines the full authored operating range. Its top may be
below the vessel brim when reviewed headspace is intentional or a changing
cross-section is not yet modeled. An optional root maximum fill percent further
limits the reachable fraction of those bounds; the generated manifest carries
that ceiling to the generic runtime. Both calibrations must be visible in
contact-page evidence and neither may be hidden in an asset-name runtime branch.

Material authoring uses a two-pass classification audit. When a donor family has
differently colored content variants, geometry-matched fill and stroke changes
propose material candidates. That evidence is never automatic classification:
white or translucent highlights, bubbles, shadows, and reflections near the
donor liquid still receive physical review. Every liquid-dependent element is
assigned to `bottom`, `body`, or `surface`; true vessel and glass art stays
fixed. The fixed layers must independently render a coherent empty vessel with
no residual boundary at the donor meniscus. Contact-page review at several
levels then verifies that no material-dependent feature remains above the
current surface, except a surface feature translated with that surface.

Runtime consumers use only the generated manifest and injection seam. They
never query `data-vlab-*`, use authored layer names as DOM IDs, concatenate DOM
IDs, or rebuild artwork. `<symbol>` / `<use>` and a general animated-SVG system
are outside this contract.

## Relative-path manifest

The generator emits a manifest that maps each asset name to its final served
relative URL. The TypeScript field name is `path`.

| Manifest field | Type   | Value                                           |
| -------------- | ------ | ----------------------------------------------- |
| `asset_name`   | string | The asset key (source basename without `.svg`). |
| `path`         | string | `assets/svg/<category>/<name>.svg`              |

The `path` value is a RELATIVE URL with no leading slash. The leading-slash
form is prohibited.

- A leading slash (`/assets/svg/...`) resolves against the server origin
  root. GitHub Pages project sites are served under a repository subpath
  (`/<repo>/`), so a leading-slash URL points outside the deployed site and
  the asset returns 404 in production.
- A relative URL (`assets/svg/...`) resolves against the page location, so
  it works identically when served from the origin root locally and from
  the repository subpath on GitHub Pages.

Every manifest `path` is relative. The manifest never emits an absolute or
leading-slash URL, and a manifest entry that begins with `/` is a build error.

## Per-render-instance id namespacing

Multiple SVGs inlined into one document collide on internal ids: HTML ids
must be unique per document, and a generic `clipPath id="a"` shipped by many
assets resolves a reference to the first matching id in document order, not
the one inside its own asset. The pipeline isolates every rendered SVG
instance by rewriting its internal ids before insertion.

The single naming authority is the helper `namespaceSvgIds(svgRoot,
svgInstanceKey)`. It takes an already-parsed SVG root and a stable
runtime-only namespace key, and rewrites every internal id and every
reference to it. No other code reconstructs namespaced ids by string
concatenation.

The namespaced id prefix shape is:

```
<asset_name>__<scene_or_page_id>__<placement_name>__<old_id>
```

| Prefix component   | Meaning                                              |
| ------------------ | ---------------------------------------------------- |
| `asset_name`       | Human-readable asset component (debuggability only). |
| `scene_or_page_id` | The scene or page the instance renders in.           |
| `placement_name`   | The placement within that scene or page.             |
| `old_id`           | The original authored id from the source SVG.        |

The `asset_name` component is for readability and is never the whole
namespace. The combination of `scene_or_page_id` and `placement_name`
guarantees uniqueness when the same asset is placed twice, when a base
scene and an overlay reuse a placement name, or when multiple views show the
same scene side by side. The composed `svg_instance_key` is a stable runtime
namespace key only; it is not authored YAML vocabulary and must not be used
as a protocol, object, or scene id.

Reference rewriting covers every form an internal reference can take:

| Reference form               | Where it appears                                                         |
| ---------------------------- | ------------------------------------------------------------------------ |
| `url(#id)`                   | any attribute (`clip-path`, `mask`, `filter`, `fill`, `stroke`, `style`) |
| `url("#id")` / `url('#id')`  | quoted forms in any attribute                                            |
| `url( #id )`                 | whitespace forms in any attribute                                        |
| `href="#id"`                 | `href` attribute                                                         |
| `xlink:href="#id"`           | `xlink:href` attribute                                                   |
| `url(#id)` in `<style>` text | local id references inside embedded CSS                                  |

The style-text rewrite preserves CSS text except for LOCAL id `url(#id)`
references; it does not rewrite external URLs or non-local fragments. Only
malformed SVG, unsupported external URL references, or forms the namespacer
cannot safely rewrite are rejected. A `<style>` block is never rejected
merely for containing local id references.

## Tiered rendering

The renderer chooses one of two render modes per object. The choice is
fixed for the object's lifetime and is computed from the object's
declaration, never from its current material or visual state.

| Render mode    | When                                   | DOM shape                              |
| -------------- | -------------------------------------- | -------------------------------------- |
| Static `<img>` | selected form has no internal SVG need | `<img src="<manifest url>">`           |
| Inline SVG DOM | selected form is DOM-SVG-required      | fetched SVG text, namespaced, injected |

A static `<img>` object stays clickable and highlightable through
container-level CSS; the `<img>` is a leaf and its internals are opaque.

A material-declared selected form needs the inline SVG DOM path to consume its
compiled manifest. A static selected form without an internal target remains
eligible for `<img>`.

## DOM-SVG-required predicate

`requires_dom_svg` means the selected form must render as inline SVG DOM after
fetching its SVG file text, so its compiled material manifest or structured
subpart geometry can render. It does NOT mean SVG markup is bundled into
JavaScript.

The predicate is computed from the object's DECLARED capabilities, never
from current state. An empty flask that declares an internal liquid region
is DOM-SVG-required even when it holds nothing, so render mode is stable
across the object's lifetime.

`requires_dom_svg` means the object needs access to the INTERNAL structure
of its SVG. It does NOT mean the object merely has a visual state. An object
that only labels over its asset, swaps the whole asset, or is just clickable
needs no internal access and renders as an `<img>`.

The predicate is derived from live object signals only (capabilities and
`visual_states` declarations that exist in object YAML today). The closed
material render-effect vocabulary is live: the generator validates and emits
`material_tint` / `fill_height` effects for `subpart_geometry` and SVG-anchor
targets, and the runtime renders those generated declarations. Closure-gating
still applies: authors select only the documented effect and target tokens;
they cannot introduce an arbitrary rendering mechanism.

`requires_dom_svg` remains deliberately conservative. A
`material_container` or `structured_surface` declaration already requires
internal SVG access, and the predicate also recognizes the established formula
and composite signals below. Object-level material rendering uses the compiled
material-manifest path; structured surfaces use their generated geometry.

An object is DOM-SVG-required if its declaration has ANY of:

| Declared trigger                                            | Why it needs internal SVG access                             |
| ----------------------------------------------------------- | ------------------------------------------------------------ |
| capability `material_container`                             | holds material; internal liquid region must be DOM-reachable |
| capability `structured_surface`                             | plate/rack subparts use internal overlay geometry            |
| a `fill_height(` formula in any `visual_state`              | renders compiled gravity parts or generated subpart geometry |
| a `kind: composite` state with a NON-EMPTY `composite` list | layers real internal subparts                                |
| any `visual_state` of an unknown/unrecognized kind          | SAFE BIAS: may target internals; defaults to required        |

Generated `subpart_geometry` and compiled material manifests require the inline
SVG DOM path. Object-level anchors are compiler-only source inputs.

A static `<img>` (img-eligible, `requires_dom_svg = false`) is allowed when
the declaration has ONLY:

- generic `kind: overlay` states (a text/label layer drawn OVER the asset as a
  separate DOM layer; it works over an `<img>` and needs no internal access);
- an EMPTY `composite: []` (no internal subparts to target);
- whole-asset `kind: svg` swaps (just change the `<img>` src);
- clickable-only or container-level click and highlight capabilities.

SAFE BIAS: an unknown or unrecognized `visual_state` kind or effect that could
target internals defaults to DOM-SVG-required. A real material or internal-SVG
effect is never silently rendered as an opaque `<img>`.

`requires_dom_svg` is a GENERATED value. The generator derives it from the
declared fields above and emits it; it is not authored by hand and is not a
manual material flag. Runtime reads it as data and may assert in dev/test
that it agrees with declarations, but does not rediscover object semantics
on every render.

## One SVG DOM path

There is exactly one inline SVG DOM render path:

```
static SVG file text
        |
        v
fetch by manifest URL (cached per asset URL)
        |
        v
namespaceSvgIds(svgRoot, svgInstanceKey)   per render instance
        |
        v
inject inline; material and anchor rendering target the namespaced DOM
```

Fetched SVG text is cached by asset URL: one fetch per asset, reused across
every placement. Id namespacing still runs per render instance after
retrieval. There is no old-registry compatibility path. The renderer does
not maintain both a bundled-markup path and a fetched-file path; the
material renderer targets the single id-namespaced DOM produced by this
flow.

## Deactivated placements

Deactivation is a render-time placement flag, not an object-capability
mutation. When a placement is deactivated by a protocol scene's
`deactivate_placements` operation, the placement remains visible for student
orientation but is muted and non-clickable. The object's declared
`capabilities` list is unchanged; only the placement's runtime availability
is flagged.

The renderer chooses the concrete visual treatment (grayscale, opacity, or
other) and the SVG pipeline applies that treatment to the deactivated
placement's rendered node.

See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the inheritance-side
definition of `deactivate_placements`.

## Never crop in display

Canonical home: [../PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md).

Once an asset enters the rendering pipeline, no downstream container may clip or distort it. A scene cannot pass visual review if any scientific SVG asset is cropped or aspect-distorted enough to change what the object is. This rule applies even if precheck reports `hard_fail_count = 0`.

Forbidden in any rendered scene:

- Cropped bottoms of volumetric flasks
- Cropped bottle necks or caps
- Clipped pipette tips
- Hidden instrument edges
- Object artwork cut off by cards, regions, wrappers, `overflow: hidden`, or `.object-graphic` containers
- Squashing or stretching that changes the intended asset aspect ratio

Diagnostic requirement:

- The `artwork_integrity` check must compare the rendered asset bbox against its parent placement card and flag overflow clipping plus aspect-ratio deviation > 5%.
- Visible clipping is HARD FAIL.
- Aspect distortion is HARD FAIL for lab glassware, pipettes, plates, and instruments; advisory for decorative items.

Fix direction (not a substitute for the rule):

- Use `object-fit: contain`, never `cover`.
- Preserve SVG `preserveAspectRatio="xMidYMid meet"`.
- Remove parent `overflow: hidden` where it clips assets.
- Size cards around assets, not assets into too-small cards.
- Add `min-height` / `min-width` for tall glassware cards.

Anti-patterns (forbidden):

- Do not "fix" cropping by hiding cropped assets, deleting DOM, or weakening diagnostics.
- Do not accept a high score if the asset is visibly cropped.
- Do not claim visual success while glassware bottoms are cut off.

## Missing SVG assets

`pipeline/gen_scene_index.py` emits scenes only when every placed object resolves
all of its SVG assets. A missing-asset report names every affected placement,
object, and asset id; the generator then exits non-zero before writing a new
scene artifact. This single strict path keeps authored content and generated
runtime data aligned.

## Related docs

- [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) - material state, color
  resolution, and the authoring vocabulary for liquid anchors.
- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) - Scene YAML schema and the
  scene driver and capability runtime that consume rendered SVGs.
- [../CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md) - System design overview;
  the SVG modules section points here for the ownership rule.
- [../FILE_STRUCTURE.md](../FILE_STRUCTURE.md) - Directory map for `assets/`,
  `src/`, `generated/`, and `dist/`.
