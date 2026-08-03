# SVG material semantic contract

## Decision

Material-rendered SVGs are self-describing. They contain semantic groups and use no external
recipe sidecar. This is a material-specific extension of the existing SVG pipeline, not a
general SVG animation framework.

Static forms remain ordinary SVG files. Discrete-state assets remain collections of complete
forms selected by object `visual_states`; each selected form is independently static or
material-rendered. A numeric display remains an object-level overlay unless a separate plan
identifies a concrete reason to change that boundary.

The measured carrier comparison is in
[svg_semantic_carrier_matrix.md](../audits/svg_semantic_carrier_matrix.md).

## Ownership

| Concern | Authority |
| --- | --- |
| Protocol material registry | `materials.yaml`, including `display_color` |
| Object material binding | object YAML `visual_states` |
| Geometry, clip geometry, and paint fallback | the SVG form |
| SVG layer recipe | embedded semantic groups and reserved attributes in that SVG |
| Runtime identity | derived opaque handles in the liquid-region manifest |
| Paint shade and liquid level | runtime from the selected material and volume state |

The SVG layer recipe never names a protocol, material, color, source-path index, or runtime
DOM id. The generated liquid-region manifest is derived data, never authored input.

The root declaration is per-form processing authority: every SVG with
`data-vlab-rendering="material"` receives material normalization and validation, even when
no object currently references it. Object `visual_states` bindings only gate whether runtime
applies material mutation to a validated form.

After selection, exact root `data-vlab-rendering="material"` selects the compiled
material-layer path; absence selects the ordinary path. Invalid or misplaced reserved
attributes fail rather than falling through. During migration, an ordinary selected form with
an existing `fill_height` / anchor binding retains the live anchor-overlay behavior. A
material-declared selected form with that same binding uses generated liquid-region manifest
handles and the injection seam: material identity recolors semantic groups by role and
volume/capacity transforms the compiler-derived liquid-level group. Runtime creates no rect
and does not query or mutate structural anchors or authored `data-vlab-*`.

For a material form, `anchor_liquid_bounds`, `anchor_liquid_clip`, and existing capacity
fields remain binding/compiler inputs. The compiler validates and resolves those anchors into
the manifest and derived level group; it does not ignore them and this work introduces no new
object YAML target, binding, or token. A root-declared form without a runtime material binding
is still normalized, compiled, and validated, but displays authored fallback paint without
state mutation. Structural anchors are never semantic paint layers.

The authored source remains `assets/<category>/<name>.svg`. An ordinary source
copies verbatim to `dist/assets/svg/<category>/<name>.svg`. A material-declared
source is normalized, sanitized, and compiled to
`generated/material_svg/<category>/<name>.svg`; that derived artifact, never
the source, copies to the same served path. Direct publication of a material
source is a build error. The SVG manifest maps only logical `asset_name` to the
final served relative URL and exposes neither source nor intermediate paths.

## Authored vocabulary

A material-rendered SVG root declares:

```svg
<svg data-vlab-rendering="material" ...>
```

Each semantic layer is a `<g>` with this closed vocabulary:

| Attribute | Required | Values and rule |
| --- | --- | --- |
| `data-vlab-layer-name` | Yes | Unique snake_case semantic identity within one SVG form |
| `data-vlab-layer-kind` | Yes | `fixed` or `material` |
| `data-vlab-paint-role` | Material only | `base`, `highlight`, or `shadow`; a role may repeat across layers |
| `data-vlab-adjustment` | Highlight/shadow only | ASCII finite decimal: highlight `0 < value <= 0.5`; shadow `-0.5 <= value < 0`; forbidden for `base` and `fixed` |

`data-vlab-rendering` is valid only on the root `<svg>` and only with exact
value `material`. The other reserved attributes are valid only on direct
root-child semantic `<g>` elements. Any reserved `data-vlab-*` attribute in an
SVG without that root declaration fails instead of using ordinary
normalization. Unknown, misplaced, and role-incompatible reserved attributes
also fail; nested ordinary artwork groups carry no reserved attributes.

At least one material layer has `data-vlab-paint-role="base"`. It need not be unique: for
example, two disconnected regions can both be base-painted. A layer name is unique because it
is the durable semantic handle from which the generator derives opaque runtime handles.

The adjustment grammar is `-?[0-9]+(?:\.[0-9]+)?`, so `+`, exponent,
whitespace, `NaN`, and infinity spellings are invalid. The resolved base
`display_color` is the only color source: base uses it unchanged; highlight and
shadow add their adjustment to normalized OKLCH lightness, clamp to `[0, 1]`,
preserve hue, reduce chroma only as needed for sRGB gamut, and serialize
lowercase `#rrggbb`. Tests may assert ordering, range, and gamut rather than
library-specific rounded hex values.

There is intentionally no `data-vlab-stacking-phase`. SVG document order is the sole stacking
authority. The validator checks that all material layer groups form one contiguous sibling
band in document order; it never uses metadata to reorder artwork. Fixed groups may occur
before or after that band. A semantic layer group may contain nested ordinary artwork groups,
but a nested semantic layer group is invalid; this keeps order and derived manifest entries
unambiguous.

Example:

```svg
<svg data-vlab-rendering="material" ...>
  <g data-vlab-layer-name="glass_back" data-vlab-layer-kind="fixed">...</g>
  <g data-vlab-layer-name="liquid_body"
     data-vlab-layer-kind="material"
     data-vlab-paint-role="base">...</g>
  <g data-vlab-layer-name="liquid_highlight"
     data-vlab-layer-kind="material"
     data-vlab-paint-role="highlight"
     data-vlab-adjustment="0.18">...</g>
  <g data-vlab-layer-name="glass_front" data-vlab-layer-kind="fixed">...</g>
</svg>
```

`id` remains for unique structural anchors such as `anchor_liquid_clip` and
`anchor_liquid_bounds`. `class` remains a styling mechanism. Neither identifies a
material-rendered layer or becomes a runtime handle.

An authored semantic layer `<g>` must not carry `clip-path`.
`anchor_liquid_clip` remains in `defs`; the compiler applies it to the derived
liquid-level group. Ordinary child artwork follows ordinary supported clip rules.

Authored source retains literal donor `fill` and `stroke` values as visual fallbacks and
contains no generated CSS custom properties or runtime paint handles. Material compilation
may add opaque CSS property/paint handles to the normalized/generated runtime output while
retaining those literal fallbacks.

## Required pipeline guarantees

The existing normalizer gains a material policy selected by
`data-vlab-rendering="material"`; ordinary SVGs keep the ordinary policy. It must:

- retain or canonically rewrite only the closed `data-vlab-*` vocabulary;
- preserve semantic groups, child order, and the contiguous material band;
- never merge or flatten across semantic layer boundaries;
- keep structural clip and bounds anchors valid;
- validate the normalized and sanitized output, not only source markup;
- derive per-layer opaque runtime handles and generated CSS paint properties without
  exposing authored attributes to runtime consumers; and
- produce byte-stable output on repeated normalization.

WP-R2 implements and verifies the material policy: normalization and manifest
sanitization preserve and validate the closed semantics deliberately, while retaining the
intentional ban on semantic-group clipping. The ordinary policy remains separate and must
not be used as a reason to special-case individual material assets.

## Validation failures

The normalized-output validator fails a material SVG for a missing/extraneous root declaration,
unknown or misplaced `data-vlab-*` fields, unknown enum values, missing or duplicate layer
names, an absent base role, invalid adjustment syntax/range/sign, nested semantic layers, a
semantic-layer group carrying `clip-path`, a noncontiguous material band, lost structural
anchors, or evidence of a semantic-boundary merge. It also rejects authored material/protocol
names, hex semantic colors, path indexes, and runtime ids in the recipe vocabulary.

## Approval boundary

This record is ratified: the canonical specification patch applies the approved
design direction and its two validation clarifications: no authored stacking phase,
and unique layer names with repeatable paint roles. WP-R2 compiler infrastructure
(material normalizer, validator, and manifest compiler) is implemented and verified.
Durable pilot art and build-loop activation remain M3 work; runtime consumption of
the generated opaque handles remains M4 work.
