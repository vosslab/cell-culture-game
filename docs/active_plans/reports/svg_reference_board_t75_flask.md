# T75 flask reference board

## Purpose and target

This M4 board supplies the reference-back standard for the transparent-vessel
exemplar in [svg_visual_quality_rebuild_plan-v2.md](../active/svg_visual_quality_rebuild_plan-v2.md).

**Recognition target:** At scene size, a student recognizes a low-profile 75 cm2
tissue-culture flask from its broad transparent growth chamber, canted or angled
wide neck, and distinct screw cap before reading a label or inspecting small detail.

The subject is the generic T75 tissue-culture-flask family, not a branded product.
Manufacturer references establish physical structure; the local Servier corpus
establishes adjacent illustration language. This board does not authorize copying
manufacturer photographs, labels, logos, or branded geometry.

## Bounded search record

Access date for every result: 2026-08-25.

| Lookup | Query or path | Result and use |
| --- | --- | --- |
| Object class | `T75 tissue culture flask angled neck vented cap` | [Corning U-shaped Flask page](https://www.corning.com/worldwide/en/products/life-sciences/products/u-shaped-flask.html) confirms a 75 cm2 culture surface, canted/angled neck styles, and plug-seal, vented, or phenolic caps. It establishes the common family, not one required SKU. |
| Manufacturer drawing | `Corning 75 cm2 canted neck flask technical data sheet` | [Corning LSR00154 technical data sheet](https://www.corning.com/catalog/cls/documents/drawings/LSR00154_Falcon_TC_Flask_Canted_Plug_Vent_353135_353136.pdf) supplies the structural reference: clear polystyrene, broad flat footprint, canted neck, molded graduations, perimeter stacking rims, and a 0.2 micrometre vent membrane in a vented cap. |
| Second manufacturer family | `Nunc EasYFlask 75 cm2 angled neck wide opening` | [Thermo Scientific Nunc EasYFlask 75 cm2 page](https://www.thermofisher.com/order/catalog/product/156499) confirms an angled neck, wide opening, low profile, slightly angled side walls, and volume graduations on both sides. It prevents the drawing from accidentally becoming a Corning-specific U-flask. |
| Servier/local metadata | `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Microbiology/Servier/*culture-flask*` | Four adjacent Servier assets exist: `culture-flask-empty.svg`, `culture-flask-filled-lid.svg`, `culture-flask-filled-nolid.svg`, and `culture-flask-stacked.svg`. They are a `servier_adjacent` source for transparent-face layering, cap contrast, and fill-state separation; none is treated as exact T75 product geometry. |
| Local exact-name metadata | `OTHER_REPOS/bioicons/static/icons/cc-0/Lab_apparatus/Marcel_Tisch/T75_flask.svg` | An exact-name CC0 Bioicons asset exists, but the current shipped pair is repository-authored according to [assets/equipment/SOURCES.md](../../../assets/equipment/SOURCES.md). It is a breadth check only, not a source to trace. |

## Reference views

Use the three views below together. They cover the normal three-quarter presentation
and the two structural checks that a single product photograph cannot provide.

| View | Source | What to carry into the generic drawing |
| --- | --- | --- |
| Three-quarter product view | [Corning 430641U product page](https://ecatalog.corning.com/life-sciences/b2b/US/en/Surfaces/Advanced-Cell-Culture-Surfaces/Corning%C2%AE-Cell-Culture-Flasks/p/430641U) | The product image and product data support a low, broad, transparent chamber, canted neck, rounded shoulder, and cap at one corner. The perspective shows the top, near side wall, far rim, and cap cylinder together. |
| Orthographic/technical view | [Corning LSR00154 technical data sheet](https://www.corning.com/catalog/cls/documents/drawings/LSR00154_Falcon_TC_Flask_Canted_Plug_Vent_353135_353136.pdf) | Use it to retain the long rectangular cell-growth footprint, neck-to-body proportion, rim, and cap/neck relationship. It also supports molded graduations and the vent-cap function without importing a label. |
| Alternate angled-neck family | [Thermo Scientific Nunc EasYFlask 75 cm2 page](https://www.thermofisher.com/order/catalog/product/156499) | The product view and description support a wide angled opening, low profile, slightly angled walls, and bilateral graduations. It demonstrates that neck angle and cap treatment vary within the recognizable family. |

The board meets the normal M4 reference shape: three useful views, including a
three-quarter view, from two manufacturers plus a technical sheet. The small
rendering should retain family-level anatomy, not a chosen catalog number.

## Installed construction-corpus anchors

These installed `svg-creator-expert` references answer construction questions,
not product identity. Paths are relative to that skill's `references/local-only/`
directory; literal anchors were verified in the installed files on 2026-08-25.

| Construction question | Corpus path and literal search anchor | Part informed |
| --- | --- | --- |
| Volume, perspective, and cuts | `object_construction/How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`: `X-Y-Z Coordinate System`, `Working With Volume`, `Planning Before Perspective`, `Cutting Volumes` | Establish the shallow chamber as a real top, near, end, and far-rim volume before cutting in the angled neck. |
| Tubes, caps, and cylinders | Same source: `Ellipse Basics And Terminology`; `technical_drawing/Technical_Drawing_with_Engineering_Graphics_Sixteenth_Edition-2023.md`: `Curves and Circles in Perspective` | Keep the neck opening, cap end, cap side wall, and liquid surface on one coherent perspective axis. |
| Line hierarchy | `scientific_illustration/A_Handbook_of_Biological_Illustration-1988.md`: `heaviest lines are used to draw the closest parts`, `CLARITY` | Give the near chamber rim and cap overlap priority while keeping far transparent edges lighter. |
| SVG structure | `svg_authoring/Mastering_SVG-2018.md`: `viewBox and viewport in SVG` | Preserve the shared state viewBox and scale every contour/material anchor consistently. |
| Draw order | `vector_tools/Quick_and_Easy_Vector_Graphics-2020.md`: `Z-Ordering` | Paint far transparent faces, clipped liquid, near faces, and final contours in physical back-to-front order. |

## Recognition anatomy

Several manufacturer examples share these high-value parts:

- Broad, shallow, flat-bottomed rectangular culture chamber: the dominant mass
  and the reason it is a tissue-culture flask rather than a reagent bottle.
- One shoulder flowing into a canted or angled, wide access neck: it provides
  pipet/scraper access and gives the silhouette its distinctive asymmetric corner.
- Separate screw cap at the neck: vented, plug-seal, or solid is a product-state
  variation, but a cap with a visibly cylindrical side wall is a recognition cue.
- Transparent walls with a visible rim/stacking perimeter and an interior growth
  face: the empty form reads as a vessel only when more than the outside contour
  is present.
- A broad planar base rather than an upright bottle body: it communicates the
  75 cm2 attachment area.

Optional family detail includes sparse molded graduations and a small vent cue.
Keep neither as a required branded pattern; both disappear before the major
silhouette at actual use size.

## Volume and projection

Use a stable three-quarter, slightly elevated view: body long axis left-to-right;
cap at the near-left corner; viewer sees the top growth plane, near side plane,
left end plane, and a narrow far/right rim. This is the authored pair's existing
view and the most economical way to show both vessel volume and the angled
neck/cap cylinder.

Required masses and depth cues:

- **Top plane:** a broad, pale transparent quadrilateral or rounded polygon; its
  far rim confirms a shallow chamber rather than a flat icon.
- **Near and end walls:** distinct transparent face values, with the near wall
  slightly darker than the top and the end wall differentiated by overlap. Do not
  rely on a gradient as the sole depth cue.
- **Rim and opening:** an outer perimeter/stacking rim, an inner growth-face
  boundary, and a visibly open neck mouth behind or below the cap. The neck should
  read as an angled short tube, not as a blue tab glued to the body.
- **Cap cylinder:** elliptical end or rim plus a curved/stacked side band. A few
  wide rib lines are enough to imply a threaded cap; evenly spaced micro-ribs are
  not.
- **Liquid:** a clipped, level plane inside the chamber. Its top boundary follows
  the chamber's perspective, while its near-side body shows depth. It must remain
  behind the final chamber contours.

The local Servier `culture-flask-*` forms are useful construction adjacency: they
distinguish top, front, end, rim, cap, and filled interior with face values and
draw final dark contours over transparent and liquid layers. Their color choices
and detailed marks are not a trace target.

## Current state contract

The shipped state pair is:

- `assets/equipment/binary_state/t75_flask_empty.svg`
- `assets/equipment/binary_state/t75_flask_filled.svg`

Both share `viewBox="0 0 299.901 95.865"`, `flask`, `cap`, `chamber`, and
`chamber_contours` groups, the same chamber path, `overlay_root`, `anchor_label`,
`anchor_error`, and the liquid clip anchor. The filled state alone adds `liquid`,
clipped to that exact chamber path, with a level medium layer. The YAML state
mapping selects empty only for `material_name: empty`; media, PBS, trypsin, and
cell suspension select the filled asset in both `t75_flask` object definitions.

| Shared, therefore preserve | Observable state difference, therefore preserve |
| --- | --- |
| Projection, silhouette, cap/neck position, chamber geometry, transparent wall hierarchy, anchors, and viewBox | Empty shows only transparent chamber faces; filled adds a liquid layer inside the same chamber and redraws near contours above it. |
| One generic T75 identity across `t75_flask` and `t75_flask_new` | YAML selects the fixed empty or filled SVG; any filled hue is authored state art, not runtime material tint. A new runtime tint or material-schema behavior requires separate contract approval. The fixed filled SVG must not imply a proprietary medium brand or duplicate the chamber with a different silhouette. |

The current empty asset already has top, near, end, and side faces plus a ribbed
cap. The redesign should strengthen their coherent perspective and
opening/cylindrical read, not break the shared clipping and overlay contract.

## Simplification at use size

The object has `display_width_cm` 17 or 20 and a 299.901-by-95.865 viewBox; it is
a shallow, wide scene object, not a product illustration. At real use size:

- Keep: body silhouette, three-to-four major faces, rim, one neck opening/cap
  cylinder, and the filled liquid boundary.
- Reduce: cap ribs to a few directional strokes; preserve an ellipse/rim rather
  than every thread.
- Omit: logos, catalog/lot text, dense graduations, vent-membrane texture, molded
  plastic seams, fasteners, and exact scraper divots. A single short graduation
  cue is optional only if it survives.
- Avoid: a fully opaque blue body, unbounded liquid, or parallel outlines of equal
  value. Each would erase the transparent-vessel reading or flatten the volume.

## Construction brief

Build the shared T75 geometry first in the current 299.901-by-95.865 coordinate
contract: place a broad shallow chamber on the three-quarter axes, then construct
the angled neck and a cap cylinder as separate masses. Establish the transparent
top, near, end, and far-rim values; clip a perspective-correct level liquid region
to the chamber only; then draw the strongest near contours last. Reuse exactly the
current state anchors and shared chamber geometry so empty and filled differ only
by the contained-liquid layer.

Start with two or three thumbnail massings at real rendered size:

1. Current cap-near-left three-quarter.
2. Cap-far-left three-quarter.
3. Shallow cap-near-left with stronger neck ellipse.

Retain the option that makes the cap/neck and broad growth surface recognizable at
a glance while keeping the liquid boundary legible.

## Sources and license

- Corning and Thermo Scientific pages/manuals are factual structural references
  only. No manufacturer photograph, logo, catalog text, or branded design is
  reproduced.
- Local `cc-by-3.0/Microbiology/Servier/culture-flask-*.svg` is a style-adjacent
  reference. If any Servier geometry is reused, add the precise source path, CC BY
  3.0 attribution, and adaptation note to `assets/equipment/SOURCES.md` before
  shipping. This board itself reuses no SVG geometry.
- The current files remain repository-authored state adaptations as recorded in
  [assets/equipment/SOURCES.md](../../../assets/equipment/SOURCES.md).

## Handoff

This board is ready for M5/M7: compare each candidate and finished T75 state pair
back to the recognition target, the three-quarter volume requirements, and the
shared-state table. Remaining uncertainty is intentional family variation: a final
generic form may use a canted or angled neck and a vented or solid cap, provided it
does not copy a manufacturer's branding or SKU-specific marks.
