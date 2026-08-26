# Falcon 15 mL reference board

## Scope and decision

This M4 board covers the material-rendered vessel exemplar
`assets/equipment/variable_volume/falcon_15ml.svg`.

**Recognition target:** a generic, clear 15 mL conical centrifuge tube with a
blue screw cap, visible volume graduations, a writing panel, and a pointed
pellet-collecting bottom; it must read as the tube class without a Falcon wordmark.

Use `falcon_15ml`, not `microtube`, for the exemplar. The Falcon form is the
cleaner hard case for the current contract: it has a long cylindrical body,
a conical bottom, a declared cone-to-body calibration, and all three gravity
parts (`bottom`, `body`, and `surface`). `microtube.svg` has a hinged cap and a
much more compound silhouette, which would confound a review of volume behavior.
The selected form is also the 15 mL tube shared by the `conical_15ml` object and
other conical-tube objects, with a 15 mL capacity binding.

## Reference board

| View | Evidence | What to retain in a generic drawing |
| --- | --- | --- |
| Product three-quarter image | [Corning 352096 product page](https://ecatalog.corning.com/life-sciences/b2c/US/en/Liquid-Handling/Tubes%2C-Liquid-Handling/Centrifuge-Tubes/Falcon%C2%AE-Conical-Centrifuge-Tubes/p/352096) | A clear, narrow 15 mL tube; blue dome-seal cap; long round body; conical lower chamber; blue graduations; and a pale writing patch. The page identifies 17 mm outside diameter, 120 mm length, 15 mL capacity, and a 2.5 mL graduation interval. |
| Orthographic and cap detail | [Corning LSR00039 technical drawing](https://www.corning.com/catalog/cls/documents/drawings/LSR00039-Falcon-Conical-Tube-15mL-PP-352096-352097-and-352196.pdf) | Keep the cap-over-body shoulder, the cap's circular section, the cylindrical body, and the cone as separately legible masses. This is the dimensional reference, not a logo or label template. |
| Product-family reference | [Corning Falcon product selection guide](https://www.corning.com/catalog/cls/documents/selection-guides/CLS-F-PSG-001.pdf) | Confirms that the 15 mL family is 17 x 120 mm and combines dark-blue printed graduations, a white writing patch, and a polyethylene dome-seal screw cap. It supports sparse intrinsic marks rather than dense labeling. |
| Installed source counterpart | [assets/equipment/SOURCES.md](../../../assets/equipment/SOURCES.md) and [docs/Servier_svg_list.txt](../../Servier_svg_list.txt) | The local mapping names `Microbiology/Servier/falcon-15ml-empty.svg`; the corpus list also names pink and empty 15 mL Falcon variants. Reuse its simplified, source-derived silhouette only as provenance, not as a material-color authority. |

Access date for all external and local reference checks: 2026-08-25.

### Bounded search record

| Lookup | Query | Result |
| --- | --- | --- |
| Named manufacturer | `site:corning.com Falcon 15 mL conical centrifuge tube product specifications graduations cap` | Found Corning 352096. It supplies the physical class, material, cap, dimensions, capacity, and graduation interval. |
| Object class and drawing | `site:corning.com Falcon 15 mL conical centrifuge tube technical drawing pdf` | Found Corning LSR00039, a primary technical drawing for 15 mL PP Falcon tubes. |
| Servier provenance | Local `rg -n -i "falcon-15ml|microtube" docs/Servier_svg_list.txt assets/equipment/SOURCES.md` | Found the adopted Falcon empty source and its color sibling in the installed corpus list; the local ledger calls the form material-rendered. |

This is the plan's required manufacturer-name, object-class, and Servier-metadata
search. No branded geometry, typography, or product-number text should transfer
to the rebuilt generic asset.

## Installed construction-corpus anchors

These installed `svg-creator-expert` references answer construction questions,
not product identity. Paths are relative to that skill's `references/local-only/`
directory; literal anchors were verified in the installed files on 2026-08-25.

| Construction question | Corpus path and literal search anchor | Part informed |
| --- | --- | --- |
| Volume, perspective, and cuts | `object_construction/How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`: `X-Y-Z Coordinate System`, `Working With Volume`, `Planning Before Perspective`, `Cutting Volumes` | Construct the cap, long body, shoulder, and continuous cone as connected volumes before cutting the transparent interior. |
| Tubes, caps, and cylinders | Same source: `Ellipse Basics And Terminology`; `technical_drawing/Technical_Drawing_with_Engineering_Graphics_Sixteenth_Edition-2023.md`: `Curves and Circles in Perspective` | Align cap rim, body cross-section, shoulder, and runtime liquid surface as one coherent cylindrical family. |
| Line hierarchy | `scientific_illustration/A_Handbook_of_Biological_Illustration-1988.md`: `heaviest lines are used to draw the closest parts`, `CLARITY` | Prioritize the near cap/body/cone contour while keeping far clear-plastic edges and graduations subordinate. |
| SVG structure | `svg_authoring/Mastering_SVG-2018.md`: `viewBox and viewport in SVG` | Preserve one stable coordinate system for the fixed shell and `bottom`/`body`/`surface` material anchors. |
| Draw order | `vector_tools/Quick_and_Easy_Vector_Graphics-2020.md`: `Z-Ordering` | Paint far clear-plastic face, semantic material bands, near face, writing patch, graduations, and final contours in physical order. |

## Recognition and volume

### Physical evidence

- The physical tube is a 15 mL, clear conical centrifuge tube with a 17 mm
  outside diameter and 120 mm length. Its long, narrow proportion is the first
  recognition cue.
- The blue polyethylene dome-seal screw cap is a separate upper cylinder with a
  small overhang. A shoulder/rim transition must make the cap read as seated on
  the tube, not as a flat blue rectangle.
- The body is cylindrical, then transitions at a visible circular shoulder into
  a cone that terminates in a rounded point. The cone must be visibly deeper than
  a V-shaped graphic: it collects a pellet and proves the low-volume shape.
- Printed graduations and a writing patch are genuine family features. They are
  physical intrinsic marks, but neither brand nor product number is required for
  class recognition.

### Chosen projection

Use a near-front, slightly elevated three-quarter projection: the tube remains
upright and nearly symmetric, while the cap top, liquid surface, body join, and
cone shoulder show horizontal ellipses. Keep the vertical axis straight. A wide
oblique view weakens the writing panel and graduations; a strict front elevation
flattens the cylindrical and conical volume.

All circular horizontal sections use a shared horizontal major axis. The cap-top,
cap-base, body join, liquid surface, and cone shoulder must share the same minor
axis direction and viewing elevation; do not mix a circular cap with a flat
liquid line. The cap ellipses are widest, the body and surface ellipses match the
inner bore, and the cone shoulder narrows continuously into the tip. Exact
ellipse radii are drawing choices, not manufacturer dimensions.

### Massing thumbnails

At the real scene size, compare these before polish:

1. `A: front elevation` -- cap cylinder, long body, cone. Reject if the surface
   becomes a straight stripe or the cone reads as a flat triangle.
2. `B: slight three-quarter` -- same three major masses plus visible cap top,
   surface ellipse, and one lighter near wall. Preferred: it communicates volume
   without hiding the intrinsic marks.
3. `C: stronger three-quarter` -- increased side plane and cap overhang. Reject
   if the writing patch or graduation ladder becomes too narrow to read.

The finished form must be compared with this board at its actual workspace size,
not approved from an enlarged isolated render.

## Construction brief

### Major masses and marks

| Major mass | Must communicate | Simplified construction |
| --- | --- | --- |
| Cap | A closed screw cap seated on a tube | Blue, shallow cylinder with top and bottom ellipses, restrained vertical ribbing, dark outer contour, and a slightly darker far side. |
| Rim and shoulder | Cap-to-vessel connection | A narrow pale rim/neck below the cap; keep a single clear occlusion edge and a small side-plane value shift. |
| Cylindrical body | Clear plastic volume | Broad pale near face, darker far side, thin dark silhouette, and one restrained vertical reflection. Do not make transparency depend on the material color. |
| Conical bottom | Centrifuge-tube identity and low-volume capacity | A cone that starts at the body join, narrows continuously, has a rounded point, and retains a near/far plane value split. |
| Liquid | Material identity and amount | A colored surface ellipse plus a body that joins tangent to that ellipse and a stationary cone base. |
| Marks | Generic laboratory use | One narrow pale writing panel and a sparse one-side graduation ladder. Use dark-blue major ticks and only a few Arabic numerals such as `5`, `10`, and `15`; omit trademark, product number, warning prose, and dense minor ticks. |

### Face values and lines

- Put the strongest outline on the nearest outer silhouette and cap rim.
- Use a lighter internal line for graduations, panel edge, body join, and
  far-side cap ribbing. Never use the marks as a second heavy outline.
- Model volume with near/far face values and overlap first. Gradients are
  unnecessary for this exemplar; a thin fixed reflection is sufficient evidence
  of clear plastic.
- Keep vessel plastic blue-white/neutral and cap blue. Material color belongs
  only to the semantic material band, so warm and cool materials remain equally
  legible through the clear vessel.

## Material behavior board

### Ownership boundary

The following table separates physical drawing evidence from runtime mechanics.
It follows [docs/specs/SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) and
[docs/specs/MATERIAL_CONVENTION.md](../../specs/MATERIAL_CONVENTION.md).

| Concern | Physical/intrinsic fact | Runtime-specific contract |
| --- | --- | --- |
| Tube, cap, rim, label patch, graduation ink, and plastic reflection | They are stationary parts of a clear 15 mL conical tube. | They remain `fixed` SVG layers and must not acquire material tint or height behavior. |
| Material identity and form selection | Liquid can be visibly colored inside a clear tube. | The object YAML's `material_name` `kind: svg` cases all select `falcon_15ml`; that field supplies the material identity for the compiled material instance. The resolver's `display_color` supplies its base color, and `highlight` and `shadow` derive from it with the authored OKLCH adjustments. Do not add a duplicate object-level `material_tint` declaration. |
| Material amount | A low volume occupies the pointed cone before rising into the cylinder. | The object YAML's `material_volume` declares `render_effect: fill_height` with `capacity_ml: 15`; the root's `data-vlab-body-start-fill-percent="2.8672624"` maps the cone/body transition. |
| Empty tube | A clear tube with no liquid remains recognizable. | Zero volume or `empty` produces no visible material region; no neutral placeholder, residual donor liquid, or painted meniscus remains. |
| Liquid boundary | A horizontal meniscus follows the level and narrows inside a cone. | Generated handles apply the closed gravity parts: stationary `bottom`, Y-scaled `body`, and Y-translated `surface`; the runtime does not inspect authored semantic names or anchors. |

### Required material split

The material groups remain one contiguous band between fixed back and fixed front
art. The existing form gives the intended division; a rebuild preserves behavior,
not donor colors:

| Part | Purpose across volumes | Required paint roles |
| --- | --- | --- |
| `bottom` | Fixed, colored conical base and its far-side shade. It is the only visible liquid geometry at the smallest nonzero amount. | At least base plus a shadow where the cone has a far plane. |
| `body` | Cylindrical liquid column above the cone. It scales only in Y from the lower join, with base for the broad liquid mass and shadow for the far wall. | Base and shadow; a second base is allowed for a separate inner/outer volume plane. |
| `surface` | Fixed-shape meniscus, rim cue, and any small specular detail. It moves in Y with the level and narrows below the body-start point. | Highlight for the meniscus/specular cue; shadow/highlight only where they move with the surface. |

No liquid-colored bubble, reflection, side shade, donor-meniscus remnant, or
highlight may sit in a fixed group. No material feature may persist above the
current surface. The runtime receives generated opaque handles, never authored
layer names, IDs, or a runtime-created rectangle.

### Resolved fill behavior

M7 removed the former authored 10% minimum-fill floor. The source now declares
only `data-vlab-body-start-fill-percent="2.8672624"`; every nonzero amount is
therefore continuous from the pointed cone upward. Below 2.8672624%, the
surface narrows with the cone and no cylindrical body column is shown. At and
above that transition, the liquid reaches the full-width body. The earlier
10%-floor conflict is resolved rather than retained as a compatibility mode.

The browser material oracle exercises 0%, a below-body-start amount, the exact
body-start amount, partial body fill, full fill, and cool/warm colors through
the compiled manifest and DOM injection path. It checks the semantic liquid
handles and geometry rather than decorative source coordinates. See
`tests/playwright/test_liquid_render.spec.ts`.

This decision adds no second object-level `material_tint` effect. Ownership
remains one shared form selected by `material_name`, with `material_volume`
driving the sole declared `fill_height` amount effect.

### Fill and color matrix

Use this matrix for M7 material-range review. The cool/warm pair deliberately
tests semantic-role derivation rather than the source artwork's pink fallback.

| Resolved amount | Expected geometry | Cool material | Warm material |
| --- | --- | --- | --- |
| 0% / 0 mL | No material; clear fixed vessel only | `#1e40af` test color absent | `#c0266d` test color absent |
| Below 2.8672624%, nonzero | Cone-only liquid: fixed bottom, narrowed surface, and no cylindrical body column. | All base, highlight, and shadow paints derive from `#1e40af` | The same roles derive from `#c0266d` |
| 2.8672624% | Exact cone-to-body transition: the surface reaches full width without a gap or an overshooting body column. | Preserve hue relationship through role derivation | Preserve the same relationship without a pink-source exception |
| 10% | Full-width cylindrical low column and surface continue from the completed cone. | Preserve hue relationship through role derivation | Preserve the same relationship without a pink-source exception |
| 50% | Full-width cylindrical column, surface ellipse, and fixed cone base read as one volume | Near/far liquid faces remain distinct | Near/far liquid faces remain distinct |
| 100% | Liquid reaches the authored bounds while retaining headspace implied by the form | No material-dependent detail exceeds the surface | No material-dependent detail exceeds the surface |

The listed hex values are deliberate verification inputs, not material registry
definitions or new asset colors. A real protocol registry remains the authority
for each displayed material color.

## Provenance and uncertainty

The local source ledger states that the adopted Falcon asset is a Servier Medical
Art adaptation under CC BY 3.0; `docs/Servier_svg_list.txt` places its local
corpus path beneath `cc-by-3.0`. The current [Servier terms of use](https://smart.servier.com/terms-of-use/)
state that SMART medical images are CC BY 4.0 and require attribution, a license
link, and changed-work disclosure. This board records both facts without
rewriting the ledger: the exact historical license of the installed source needs
provenance reconciliation before any attribution policy is changed.

For an adapted Servier-derived drawing, retain the local required attribution
until that reconciliation: `Servier Medical Art`, source URL
`https://smart.servier.com/`, the applicable CC license link, and a statement
that the image was adapted. Manufacturer pages and drawings establish physical
facts only; they do not grant permission to copy Corning branding, photography,
or technical artwork.

## Handoff

- Selected exemplar: `assets/equipment/variable_volume/falcon_15ml.svg`.
- Primary physical references: Corning 352096 product page, LSR00039 drawing,
  and Falcon selection guide, all linked above.
- Local provenance inputs: `assets/equipment/SOURCES.md` and
  `docs/Servier_svg_list.txt`.
- Contract inputs: `docs/specs/SVG_PIPELINE.md` and
  `docs/specs/MATERIAL_CONVENTION.md`.
- Open uncertainty: historical CC BY 3.0 local ledger versus current SMART CC
  BY 4.0 terms. It affects attribution documentation, not the unbranded
  construction or the material-rendering contract.

## Checks

Run from the repository root after creating this report:

```bash
source source_me.sh && python3 tests/check_ascii_compliance.py \
  -i docs/active_plans/reports/svg_reference_board_falcon_15ml.md
source source_me.sh && python3 -m pytest tests/test_markdown_links.py
```

Result on 2026-08-25: ASCII/ISO-8859-1 check passed. The full Markdown-link
suite found one unrelated pre-existing broken link in `assets/equipment/SOURCES.md`
to a missing `svg_servier_counterpart_sweep.md`; every local link authored in
this report was checked directly and resolves.
