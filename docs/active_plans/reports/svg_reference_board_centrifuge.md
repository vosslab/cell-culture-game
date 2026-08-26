# Centrifuge reference board

Date accessed: 2026-08-25.

## Recognition target

A compact, generic benchtop microcentrifuge is recognized as a low, deep housing with a front
control face and feet, a circular top opening containing a tube rotor, and a rear-hinged lid that
closes over that opening.

## Bounded search log

| Query | Result | Use |
| --- | --- | --- |
| `Eppendorf Centrifuge 5425 5425 R` | The official product page shows the closed instrument, open rotor chamber, top view, front keypad, knob, multiple rotors, and soft-touch lid closure. | Main physical reference and viewpoint set. |
| `Eppendorf Centrifuge 5425 R operating manual lid rotor` | The official manual says to open the centrifuge lid fully so it cannot slam shut; it depicts the chamber, rotor, and rotor lid. | Hinge/opening and cavity/rotor evidence. |
| `Thermo Scientific MT 17 benchtop centrifuge manual` | The official Thermo Fisher manual listing identifies an operator manual for tabletop centrifuges covering controls, rotor programs, operation, and safety. | Independent manufacturer confirmation that the class has a control face plus serviceable rotor enclosure. |
| `Bioicons Servier centrifuge` | The local Bioicons checkout contains the exact `cc-by-3.0/Lab_apparatus/Servier/centrifuge.svg` counterpart. | Source-reuse and style evidence, not physical-product evidence. |

This completes the required bounded lookup: named manufacturer, object class, and Servier source
metadata were checked. The Eppendorf page supplies a three-quarter/open product photograph plus
closed side/top and close control views; use the three-quarter/open view as the massing reference,
the top/open view as the cavity and rotor reference, and the front/control image as the
control-placement reference. These are distinct viewpoints; do not reproduce its brand, markings,
or product-specific decorative details.

## Sources and licenses

1. [Eppendorf Centrifuge 5425/5425 R product page](https://www.eppendorf.com/us-en/Products/Centrifugation/Microcentrifuges/Centrifuge-5425-5425R-p-PF-934144), official product page, accessed 2026-08-25.

   This is primary manufacturer evidence. It establishes the broad, deep tabletop housing;
   front-facing keypad/knob controls; rear-hinged lid; circular OptiBowl chamber; fixed-angle and
   other rotor options; and a 48 cm open-lid height versus 24 cm closed height for the 5425.
   Product photographs are reference evidence only; no manufacturer artwork is to be copied.

2. [Eppendorf operating manual: Centrifuge 5425 R](https://www.eppendorf.com/product-media/doc/en/924635/Centrifugation_Operating-manual_Centrifuge-5425-R.pdf), official manual, accessed 2026-08-25.

   This is primary manufacturer evidence. Section 5.4.6 requires opening the lid fully so it
   cannot slam shut, and the manual's rotor-lid figure distinguishes the vessel cavity, rotor body,
   tube bores, and removable rotor lid. Copyright remains with Eppendorf; use facts and observed
   structural relationships, not copied figures.

3. [Eppendorf operating manual: Centrifuge 5425](https://www.eppendorf.com/product-media/doc/en/338022/Centrifugation_Operating-manual_Centrifuge-5425.pdf), official manual, accessed 2026-08-25.

   This is primary manufacturer evidence. It identifies an open key, a start/stop key, and a
   running indication. Copyright remains with Eppendorf; use facts and observed control/state
   relationships only.

4. [Thermo Scientific MT 17 and MTR 17, MT 21 and MTR 21 user manual](https://knowledge1.thermofisher.com/Lab_Equipment/Centrifuges/Table_Top_Centrifuges/Table_Top_Centrifuge_Operator_Manuals/Thermo_Scientific_MT17_and_MT17R_MT21_and_MT21R_-_User_Manual), official manual landing page, accessed 2026-08-25.

   This independent primary manufacturer source confirms a tabletop-centrifuge operator manual
   with controls, rotor programs, operation, safety, and maintenance. Copyright remains with
   Thermo Fisher; it supports generic class structure only.

5. Servier centrifuge, local source:
   `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Lab_apparatus/Servier/centrifuge.svg`; [upstream raw source](https://raw.githubusercontent.com/duerrsimon/bioicons/refs/heads/main/static/icons/cc-by-3.0/Lab_apparatus/Servier/centrifuge.svg).

   The checkout path declares CC BY 3.0 and names Servier as author. The source establishes the
   intended illustration lineage: restrained blue-gray scientific-icon palette, broad rounded
   housing, layered lid/chamber ellipses, simplified dark control face, and paired feet. The repo's
   [SOURCES.md](../../../assets/equipment/SOURCES.md) maps both the idle and running assets to this
   counterpart. Retain required attribution when the source is adapted; this board does not treat
   the original as a physical-product drawing.

6. `How to Draw: Drawing and Sketching Objects and Environments from Your Imagination` (2013),
   local passage `HINGING AND ROTATING FLAPS AND DOORS`, accessed 2026-08-25 at
   `/Users/vosslab/nsh/vosslab-skills/skills/experts/svg-creator-expert/references/local-only/object_construction/How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`.

   This installed construction reference anchors the requested hinge treatment. Its extracted
   passage is principally a heading and Diagram 075, so it does not provide sufficiently legible
   prose to support an exact geometric rule. Treat the manual and observed product views as the
   physical evidence; use the passage only for its topic-level instruction that a flap/door should
   rotate about a fixed hinge rather than translate or become a second unrelated shape.

## Installed construction-corpus anchors

These installed `svg-creator-expert` references answer construction questions,
not product identity. Paths are relative to that skill's `references/local-only/`
directory; literal anchors were verified in the installed files on 2026-08-25.

| Construction question | Corpus path and literal search anchor | Part informed |
| --- | --- | --- |
| Volume, perspective, and cuts | `object_construction/How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`: `X-Y-Z Coordinate System`, `Working With Volume`, `Planning Before Perspective`, `Cutting Volumes` | Construct one squat housing with top, front, and receding side planes before cutting the circular chamber into its top. |
| Tubes, caps, and cylinders | Same source: `Ellipse Basics And Terminology`; `technical_drawing/Technical_Drawing_with_Engineering_Graphics_Sixteenth_Edition-2023.md`: `Curves and Circles in Perspective` | Align chamber rim, rotor, hub, and tube bores as nested cylindrical masses. |
| Hinge axis and lid motion | Same object-construction source: `Hinging And Rotating Flaps And Doors` | Keep one rear hinge axis; rotate the lid about it and expose the underside rather than translating or redrawing the lid. |
| Line hierarchy | `scientific_illustration/A_Handbook_of_Biological_Illustration-1988.md`: `heaviest lines are used to draw the closest parts`, `CLARITY` | Prioritize the near housing edge, chamber lip, and lid underside without turning the control face into dark decoration. |
| SVG structure | `svg_authoring/Mastering_SVG-2018.md`: `viewBox and viewport in SVG` | Preserve the state-pair viewBox so open/running housing geometry and anchors remain registered. |
| Draw order | `vector_tools/Quick_and_Easy_Vector_Graphics-2020.md`: `Z-Ordering` | Paint housing, cavity, rotor, rear hinge, lid underside, lid top, controls, and near contours in physical order. |

## What makes the object recognizable

Keep these class-defining parts, because they recur across the manufacturer evidence and distinguish
the instrument from a scale, incubator, or plate reader:

- A squat, broad, deep benchtop housing, with a body noticeably wider than the control face and a
  stable lower footprint.
- A large circular or slightly elliptical lid/chamber assembly on the upper body; it is the
  dominant top mass, not an ornamental front disc.
- A rear hinge line behind the chamber, plus an open lid whose lower edge clearly remains attached
  at that line.
- An inset circular cavity beneath the open lid; show a thick rim, darker well, and a smaller
  cylindrical rotor within it.
- A radial fixed-angle tube rotor: central hub plus six to eight evenly spaced tube bores, each
  drawn as an ellipse or short tapered well. The rotor must be visibly smaller than the cavity so
  it reads as a removable cylinder nested in a housing.
- A front control face below the chamber: one dark display rectangle, a small group of round or
  pill buttons, and one larger start/open control. Do not use text, a copied arrangement, branded
  logos, or an exact product interface.
- Two visible rubber feet or a continuous lower base, placed under the near left and near right
  corners. The body should visibly sit on them instead of ending at the bench line.

Simplify away vent grilles, screws, warnings, model labels, detailed button legends, and exact rotor
counts unless the final render needs them for recognition. Those features are not class-defining at
play size.

## What gives it convincing volume

Use a modest high three-quarter, front-left view. It shows the front controls, the right side plane,
the top opening, and the open-lid thickness at once; a strict front elevation hides cavity depth and
turns the rotor into a target-like disc. Keep parallel projected edges consistent across body, panel,
hinge, and lid; use perspective only as much as the current SVG dialect needs.

Developed-massing construction brief:

1. Block the body as a rounded rectangular trunk, not a stack of flat front shapes. Start with top,
   front, and one side plane. The top plane recedes slightly; the near front face is the
   control-bearing plane; the side plane is darker or less lit. Round the front vertical corners
   only after the three planes read.
2. Set a shallow plinth or a body-bottom shadow above the feet. Project the two feet down from the
   same body perspective, make the near foot slightly larger or darker, and leave a narrow visible
   gap to the bench/floor shadow.
3. Cut an oval chamber into the top plane. Draw an outer elliptical rim, a thinner inner rim, then
   a dark elliptical cavity. The two rim ellipses share center, rotation, and minor-axis direction.
   The cavity is dark because it recedes, not because it is an unrelated black disk.
4. Build the rotor as a short cylinder seated in the cavity: upper ellipse, visible inner wall or
   side band, lower dark ellipse, and center hub. Place evenly spaced tube bores around the hub.
   Near bores can be slightly wider/lower; far bores are foreshortened and partly occluded by the
   cavity rim. This creates depth without needing many tubes.
5. Establish a single rear hinge axis tangent to the far chamber rim. Draw a short hinge barrel or
   two small hinge knuckles where lid and body meet. Rotate the open lid mass about that axis; its
   near edge moves up and toward the viewer, but the rear edge stays on-axis. Give the lid a visible
   outer shell, thin rim/edge, and a darker underside so it is a shallow shell rather than a
   duplicated ellipse hovering above the rotor.
6. Project the control face on the front plane. Recess the dark panel slightly with a top/side edge,
   then place a pale display and the few control marks. Maintain a clear gap between chamber/lid and
   controls, as in the manufacturer views.
7. Use four value roles: light top/lid highlight; base body color; darker side/underside; darkest
   cavity/panel. Add one concise rim highlight along the upper lid or chamber edge. Do not use
   gradients, photo texture, copied screen readouts, or a large cast shadow to manufacture volume.
8. Test the silhouette at small size, then judge the finished colored object at intended workspace
   size. The silhouette alone may not identify a centrifuge; the open cavity, radial rotor, hinge,
   controls, and feet are legitimate required recognition evidence under E6.

## Source role separation

The Servier SVG is the reusable visual-language source: it demonstrates the desired simplified
scientific-icon styling, color family, layered elliptical forms, compact controls, and feet. It is
not adequate evidence for a physical mechanism by itself.

The Eppendorf product page and manuals are the physical-structure sources: they establish a lid that
opens upward from a rear hinge, an enclosed circular chamber, a removable cylindrical rotor with tube
bores, a control relationship on the front face, and the substantially taller open state. Thermo
Fisher is an independent class check, not a shape template. The final asset should be generic,
structurally faithful, and visually simplified rather than an Eppendorf look-alike.

## Idle and running family contract

The family must retain one shared geometry specification: identical body bounding box, camera/view,
housing planes, chamber/lid outline, hinge axis, front-panel placement, feet/base, anchors, and
control geometry. Do not re-proportion, rotate, translate, or redraw the whole instrument between
states.

- Idle/open state: lid visibly rotated about the rear hinge; cavity and stationary radial rotor
  visible; no motion marks; neutral status control. This is the state for loading and balancing
  tubes.
- Running/closed state: same lid closes on the same hinge into the same chamber outline; rotor is
  occluded by the safety lid/window except for a muted radial cue; motion arcs or slight radial blur
  stay inside the window only; running/start indicator changes to green or another validated active
  color. Keep the body and front controls fixed.
- The state difference must communicate a safety-relevant fact: the student cannot load or alter
  rotor contents while the lid is closed/running. The running mark must not imply an exposed
  spinning rotor.

Current-state note: `assets/equipment/binary_state/centrifuge.svg` is an open, front-facing
circular-chamber drawing and `centrifuge_running.svg` is a closed, front-facing circular-lid drawing.
The intended rebuild should improve both together to the shared three-quarter construction above, not
preserve their present geometry mismatch as a compatibility boundary.

## Handoff and uncertainty

This board is sufficient research for M4, but it is not a product-dimension drawing and should not
fix an exact lid angle, tube count, rotor capacity, or button arrangement. Those are deliberately
generic choices to be settled by the selected visual direction and real-size review. The drawing
passage's OCR is weak at its actual hinge section, so its content should not be overstated;
manufacturer photos/manuals are the evidence for the mechanism. Before accepting a finished SVG,
compare it back to this board for supported silhouette, proportions, planes, cavity, hinge, controls,
and feet.

## Checks

- ASCII: run `LC_ALL=C rg -n '[^\\x00-\\x7F]' docs/active_plans/reports/svg_reference_board_centrifuge.md`;
  expected no matches.
- Markdown links: run `source source_me.sh && python3 -m pytest tests/test_markdown_links.py -q`;
  all local Markdown links must resolve from a tracked file. The external URLs above are
  primary-source citations; they are not local-link-test targets.
