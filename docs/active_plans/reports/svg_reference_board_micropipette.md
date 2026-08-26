# Micropipette reference board

## Scope and recommendation

Recognition target: a generic single-channel, adjustable-volume, air-displacement
micropipette with a disposable tip, recognizable at scene size as the hand-held
tool used to aspirate and dispense microliter volumes. Do not make it a trace or
a branded product portrait.

Use the P200 (20-200 uL) family as the M4 exemplar. Current content uses it in
21 YAML files, versus P20 in 8 and P1000 in 4. It is centrally placed in the
electrophoresis bench and repeatedly drives SDS-PAGE sample mixing, loading, and
gel-loading workflows. P20 and P1000 remain essential family variants, but their
lower current scene reach makes them weaker first exemplars.

## What must survive simplification

A reader recognizes the object from this ordered chain of parts: a short
cylindrical thumb plunger at the top; a tall, hand-width main housing; an inset
dark volume window with readable pale digits; a colored volume-range collar; a
separate thumb/finger grip and tip-ejector control; a long narrowing lower shaft;
a removable disposable tip; and a very small terminal outlet. The
[Eppendorf Research plus operating manual](https://www.eppendorf.com/product-media/doc/en/186591/Eppendorf_Liquid-Handling_Operating-manual_Research-plus_Eppendorf-Research-plus.pdf)
confirms the generic functional mapping: the control button aspirates and
dispenses, the volume setting ring changes a four-digit volume display, and the
ejector button drives an ejector sleeve downward to remove the tip.
[Gilson PIPETMAN](https://www.gilson.com/pipetman-g.html) independently
identifies the generic class as a fully adjustable air-displacement pipette using
disposable tips.

At the intended narrow, tall scene footprint, silhouette alone should retain the
plunger, broad upper body, narrower shaft, and pointed tip. The volume window and
range collar then distinguish it from a transfer pipette or dispenser. Do not rely
on brand marks, fine labels, or a liquid color to identify it.

## Developed-massing construction brief

Projection: near-front three-quarter view, with the plunger and volume window
facing the viewer and a 10-15 degree visible side plane. Keep the long axis nearly
vertical; use only enough yaw to expose depth, not enough to hide the display. Use
a common upper-left light direction.

1. Build the plunger as a shallow cylinder: top ellipse, darker side wall, and a
   slight overhang above the body. A second smaller ellipse or rim is enough at
   scene size.
2. Build the main hand housing as three masses: broad front plane, narrow darker
   receding side plane, and a short undercut or lower shoulder. The grip should
   be an overlapping ergonomic lobe, not a colored rectangle pasted across a body.
3. Cut an inset volume-window recess into the front plane. Give it a dark inner
   face, a thin bright upper/left bevel, and a short darker lower/right edge.
   Draw only 3-4 high-contrast digits or bars at actual display scale; preserve
   the window even where digits must simplify away.
4. Place the color-coded range collar below the window as a collar around the
   body: front face, visible side wrap, and a thin ellipse or curved seam at the
   transition. It is a manufactured component, not a liquid indicator.
5. Make the ejector a separate front-side lever/button attached near the upper
   body and a sleeve that overlaps the shaft. The sleeve needs a visible front
   face and a darker side/underside so it reads as a mechanism.
6. Taper the shaft in two stages: a relatively substantial tip cone/shaft just
   below the ejector sleeve, then a thinner disposable tip. Use overlap at the
   sleeve-to-shaft joint and at the tip fitting. Give the tip cone a small
   elliptical opening/rim and a narrow darker receding edge. The terminal outlet
   can be one dark tick, not a second outlined rectangle.
7. Carry volume with face values and overlaps before gradients: light main front,
   mid plunger and grip, dark window and side planes, and a separate light
   translucent or white tip. Use ellipses only for genuinely cylindrical rims
   and buttons; do not sprinkle circles as decoration.
8. Keep the outer contour heaviest, structural seams medium, and only
   window/bevel/terminal detail light. At the 4 cm P200 display width, delete
   unreadable seams rather than violating the measured stroke floor.

This produces convincing volume because the viewer can see the front face, a
receding side, cylindrical plunger rims, the inset window, and nested overlaps
from housing to ejector sleeve to tip cone to disposable tip. The current assets
instead use front-elevation rectangles and trapezoids only; the inspected P20,
P200, and P1000 empty forms have no ellipse or transform, so their otherwise
correct part inventory still reads as flat UI geometry.

## Family and state treatment

The current P20, P200, and P1000 drawings already establish a useful range-color
family: P20 yellow, P200 orange, P1000 blue-grey, with increasing housing and tip
widths. Preserve that semantic distinction as a physical nominal-volume/model
family color collar plus proportional shaft/tip change. It must not change with
liquid identity, held volume, fresh/used status, or interaction state.

Physically observable persistent changes:

- No tip versus fitted disposable tip is visible and may be a structural SVG state
  when the protocol makes it important.
- A colored liquid column can be visible inside a translucent fitted tip after
  aspiration, but many real samples are colorless; it is optional illustrative
  evidence, not the definition of a filled micropipette.
- The volume setting can physically change the digits in the volume window. This
  is a presentation of `set_volume`, not an overlay label placed outside the
  instrument.
- A plunger is visibly depressed only during an action pose. Stable loaded and
  empty states should not imply a depressed plunger.

Material/runtime states that should not be faked as physical product variation:

- `held_material_name` and `held_material_volume` are logical contents; use
  them to choose an optional, contained tip-liquid mark, never to recolor the
  body or range collar.
- `tip_status: fresh` versus `used` is generally not visually reliable for a
  generic disposable tip. Keep it as runtime/material state unless the lesson
  deliberately requires a visible contamination marker, which would be a teaching
  overlay rather than product anatomy.
- `cursor_attachable`, clickability, active/candidate rings, and external
  set-volume/tip-status overlays are runtime affordances, not equipment geometry.

Current mappings support this separation: P20 and P1000 choose empty/filled
assets from `held_material_name`; P200 has one material-rendered asset. All three
retain set-volume and tip-status as overlays. The P200 maps its contained tip
liquid from `held_material_name` and `held_material_volume`, never from a second
instrument asset or a recolored body. The rebuild preserves that clean state
boundary while making the base anatomy three-dimensional.

## Bounded reference search

Access date for every source and query below: 2026-08-25.

| Query | Result and use |
| --- | --- |
| `site:gilson.com Pipetman G adjustable volume pipette features volume display tip ejector` | [Gilson PIPETMAN](https://www.gilson.com/pipetman-g.html). Use for generic class, single-channel volume-range breadth, disposable-tip, and ejector facts. |
| `site:eppendorf.com Research plus pipette operating manual adjustable volume display ejector` | [Eppendorf Research plus operating manual](https://www.eppendorf.com/product-media/doc/en/186591/Eppendorf_Liquid-Handling_Operating-manual_Research-plus_Eppendorf-Research-plus.pdf). Use for part-to-function mapping: control button, four-digit volume display, volume setting ring, ejector button, ejector sleeve, and nominal-volume color coding. |
| `site:rainin.com adjustable volume pipette anatomy plunger volume display tip ejector` | No selected Rainin primary result was returned in this bounded lookup. The two independent manufacturers above already provide a manufacturer page plus a component-level primary manual; do not invent a third-source claim. |
| Local Servier search: `rg -l -i 'pipet|pipette' OTHER_REPOS/bioicons/static/icons/cc-by-3.0` | `Chemistry/Servier/micropipette.svg` exists, and [assets/equipment/SOURCES.md](../../../assets/equipment/SOURCES.md) records it only for `p10_micropipette.svg`. No P200 asset has a direct-source row, so record P200 as `no_servier_source` for direct provenance; do not call a palette-only resemblance `servier_adjacent`. |

## Installed construction-corpus anchors

These installed `svg-creator-expert` references answer construction questions,
not product identity. Paths are relative to that skill's `references/local-only/`
directory; literal anchors were verified in the installed files on 2026-08-25.

| Construction question | Corpus path and literal search anchor | Part informed |
| --- | --- | --- |
| Volume, perspective, and cuts | `object_construction/How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`: `X-Y-Z Coordinate System`, `Working With Volume`, `Planning Before Perspective`, `Cutting Volumes` | Block the plunger, grip, display housing, collar, sleeve, shaft, and tip as connected tapered masses before adding detail. |
| Tubes, caps, and cylinders | Same source: `Ellipse Basics And Terminology`; `technical_drawing/Technical_Drawing_with_Engineering_Graphics_Sixteenth_Edition-2023.md`: `Curves and Circles in Perspective` | Keep the plunger cap, grip section, collar, sleeve, shaft, and disposable tip on one cylindrical axis. |
| Line hierarchy | `scientific_illustration/A_Handbook_of_Biological_Illustration-1988.md`: `heaviest lines are used to draw the closest parts`, `CLARITY` | Emphasize the near grip/sleeve overlap and tip boundary while simplifying window and ejector detail at use size. |
| SVG structure | `svg_authoring/Mastering_SVG-2018.md`: `viewBox and viewport in SVG` | Keep the full tool and tip-only material region on one stable coordinate system across volumes and colors. |
| Draw order | `vector_tools/Quick_and_Easy_Vector_Graphics-2020.md`: `Z-Ordering` | Layer rear grip plane, front housing, inset display, sleeve, shaft, contained material, and tip contour without recoloring the body. |

## Sources and licensing

- Eppendorf material is primary manufacturer evidence. Reference anatomy and
  operation only; do not copy diagrams, photos, labels, or trade dress.
- Gilson material is primary manufacturer evidence. Reference the generic
  adjustable air-displacement/disposable-tip/ejector architecture only; no image
  reuse.
- The local generic Servier source is existing P10 provenance, not P200
  provenance. The P200 redraw remains independently authored and unbranded. Do
  not add a P200 attribution row unless documented Servier geometry is actually
  reused.

Manufacturer page images and manuals remain copyrighted and trademarked reference
material. The shipped SVG must be independently authored, generic, and unbranded;
facts and proportions are referenced, not copied.

## Current-repo evidence and handoff

- `content/objects/pipette/p20_micropipette.yaml`: 2-20 uL, 4 cm display width,
  one tip-only material-rendered P20 form.
- `content/objects/pipette/p200_micropipette.yaml`: 20-200 uL, 4 cm display
  width, one P200 asset with a 200 uL tip-only `fill_height` material contract.
- `content/objects/pipette/p1000_micropipette.yaml`: 100-1000 uL, 5 cm display
  width, one tip-only material-rendered P1000 form.
- `assets/equipment/variable_volume/p20_micropipette.svg`,
  `assets/equipment/variable_volume/p200_micropipette.svg`, and
  `assets/equipment/variable_volume/p1000_micropipette.svg`: common
  front-elevation construction and no `ellipse`/`transform` match. Each form
  restricts material paint to its contained disposable tip.
- Usage count method: distinct YAML files matching the object id under `content/`:
  P20 8, P200 21, P1000 4. Counts are usage evidence, not a public-API claim.

Handoff: use this board for M5 developed-massing candidates, then compare the
P200 finished exemplar back against its silhouette, visible planes, display/window,
collar, ejector/sleeve, shaft/tip, and contained-liquid treatment. The sources do
not establish a particular brand's exact surface, color, or proportions as
mandatory; those remain intentionally generic.

## Checks

Run after materializing this ASCII-only report:

```text
source source_me.sh && python3 -m pytest tests/test_markdown_links.py -q
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py -q
```

The source-page photographs may change; the access date is recorded. The selected
sources establish shared anatomy and operations, not a universal industry-standard
location for every control. Keep the final silhouette generic and resolve
model-specific details only if a later family contract needs them.
