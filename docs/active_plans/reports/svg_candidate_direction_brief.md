# SVG candidate-direction brief

**Historical experiment, superseded and rejected as current art direction on
2026-08-26.** This M5 brief preserves how D01-D05 were compared. The
realistic-equipment replacement wave rejects all five as production direction;
none supplies an accepted D04 handoff, fallback, or live rendering workflow.
Use the frozen fixture directories and
`docs/figures/equipment_kit/candidates/README.md` for historical evidence, and
inspect current production art at `docs/figures/equipment_kit/review.html`.

## Purpose and decision boundary

This M5 brief turns the four M4 reference boards into five comparable
developed-massing experiments. It is not an equipment-kit rule and does not
change an authored application SVG. The candidate sources and renders are
review fixtures. The original M6 selection and proposed M8 extraction are
historical only, superseded by the 2026-08-26 replacement direction.

The experiment changes construction, not identity or branding. Every candidate
uses the same generic T75, compact benchtop centrifuge, single-channel P200
micropipette, and clear 15 mL conical tube. It may vary viewer elevation,
upper-left light, contour hierarchy, face-value separation, rim/opening
emphasis, and detail removal. It must not obtain distinctness merely by
changing hue, adding labels, imitating a manufacturer, or adding decorative
texture.

The M0 normalizer boundary is binding: no candidate uses a filter, blur,
drop-shadow, or non-`none` filter reference. A detached editorial floor shadow
is absent from these fixtures. Depth must come from ordered overlap, separate
physical faces, recess value, and occlusion. A low-value foot, plinth, cone,
or side face remains object geometry, never a candidate for shadow removal.

## Evidence carried into M5

- The T75 is recognizable by a broad shallow chamber, angled neck, and cap.
  Its normal small placement can be only about 15 by 5 CSS pixels, so the
  chamber/cap silhouette and liquid boundary carry more weight than cap ribs or
  graduations.
- The centrifuge needs a squat housing, top chamber, rotor recess, rear hinge,
  front controls, and feet. Its smaller current placement is about 39 by 54
  CSS pixels; the housing and lid/cavity relationship must survive before
  rotor wells or controls do.
- The P200's smallest current placement is about 7 by 27 CSS pixels. Its
  plunger, body silhouette, colored range collar, shaft/tip direction, and
  one display/recess cue must survive. Detail that becomes a stripe is removed.
- The 15 mL tube can be about 2 by 14 CSS pixels in a crowded scene. Its cap,
  long body, conical bottom, and material surface must therefore survive as
  massing rather than as a graduation ladder or reflection texture.

These measurements come from
[svg_exemplar_size_flatness_slice.md](svg_exemplar_size_flatness_slice.md) and
[svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md). The
candidate batch has a true real-size benchmark as well as a controlled
enlarged comparison surface. The latter is diagnostic only; it is not a claim
that all four objects are simultaneously readable at their most crowded
placement.

## Shared control variables

All five directions use these literal temporary swatches. They are review
inputs, not production palette tokens or material registry values.

| Role | Swatch | Use in every direction |
| --- | --- | --- |
| Review canvas | `#F5F7F8` | Neutral bench-composite background. |
| Lit equipment face | `#E8F0F4` | Top or near-lit physical face. |
| Base equipment face | `#B9CCD7` | Main housing, cap, or tool mass. |
| Receding equipment face | `#7895A5` | Side plane, under-lid face, or far wall. |
| Deep recess | `#3B5668` | Cavity, opening, display recess, or interior. |
| Contour | `#294657` | Outer silhouette and selected occlusion edge. |
| Clear-plastic light | `#DDEBF1` | T75 and tube fixed vessel face. |
| Cool material probe | `#1E40AF` | Falcon material-range review only. |
| Warm material probe | `#C0266D` | Falcon material-range review only. |

Keep all direction comparisons at the same four object bounds, anchor points,
object order, controlled camera, and swatches. A candidate may choose a listed
value from the table below, but it may not introduce a new accent color to win
the comparison. The cool and warm probes test material-role derivation only;
they are not a preference variable.

### Source and composite frame

Each candidate source SVG has `viewBox="0 0 320 320"` and
`preserveAspectRatio="xMidYMid meet"`. It has exactly this stable top-level
group order, with no transform on `candidate-root`:

```text
svg
  defs
  g#candidate-root
    g#back-masses
    g#material-band
    g#front-masses
    g#contours
    g#anchors
```

`back-masses`, `material-band`, `front-masses`, and `contours` make draw order
inspectable. `anchors` contains zero-paint reference points only and is never
used as a visual plane. Each source includes these named anchors as empty
groups or unpainted points: `anchor-center`, `anchor-baseline`,
`anchor-left`, and `anchor-right`. The visible art is centered on
`anchor-center`; `anchor-baseline` is the lowest intended physical contact
point, not a floor shadow. Its position stays fixed among all five directions
for a given archetype.

The review-only source frame is deliberately separate from app viewBoxes and
runtime anchors. Before M7, the selected direction is translated back to each
asset's required production viewBox and state/material contract rather than
changing those contracts to suit a 320-square fixture.

The 320-square Falcon candidate sources are common-frame visual surrogates,
not material SVGs. Their nested `bottom`, `body`, and `surface` markers preview
the conceptual vessel split for review, but they are not canonical runtime
material semantics: they must not set `data-vlab-rendering="material"`, use a
material root declaration, or be represented as production-compatible. M7
translates the selected construction into the real production Falcon source,
adds its required material root declaration and direct-root semantic layers,
and validates the actual material contract there.

## The five candidate directions

| ID and name | Elevation and light | Contours and face values | Opening/rim and simplification decision |
| --- | --- | --- | --- |
| `D01-servier-shallow` | 18 degree elevated three-quarter; light from upper left. | Outer contour `#294657`; lit/base/receding faces use `#E8F0F4`, `#B9CCD7`, `#7895A5`. | One clear rim and one interior edge. Keep only one characteristic detail per object. This is the restrained Servier-adjacent baseline. |
| `D02-rim-forward` | 26 degree elevation; upper-left light with a more exposed top plane. | Same contour; lit/base/receding faces use `#E8F0F4`, `#B9CCD7`, `#7895A5` with the largest visible light-to-receding separation. | Use paired outer/inner rims and a visibly thick opening/cavity. Remove secondary side markings. It tests whether recess and nesting solve the flatness problem. |
| `D03-mass-first` | 14 degree elevation; upper-left light. | Outer contour only at silhouette and decisive overlaps; interior marks use base/receding separation rather than dark lines. | One broad opening/rim; omit all non-recognition detail. It tests whether large, calm planes read better at the smallest sizes. |
| `D04-occlusion-strong` | 22 degree elevation; upper-left light with a distinctly darker under-plane. | Outer contour plus a selective occlusion contour at the nearest overlap; recess uses `#3B5668`, lit/base/receding faces use the shared swatches. | Use a deep cavity, cap-over-neck, lid-over-hinge, or sleeve-over-shaft overlap as the main cue. Limit small marks to one display or one graduation tick cluster. |
| `D05-quiet-cylinder` | 20 degree elevation; upper-left light with front-near face dominant. | Moderate outer contour; light/base/receding faces use `#E8F0F4`, `#B9CCD7`, `#7895A5`, but no dark internal contour except openings. | Cylinders and vessels receive coherent ellipse pairs; manufactured edges stay quiet. Retain only cap, rim, display, or surface details that clarify the mass. |

The five directions are intentionally close enough to compare as one language,
yet make different falsifiable massing claims. `D01` asks whether a restrained
baseline is already enough. `D02` asks whether stronger nested rims fix weak
openings. `D03` asks whether extra contours are causing the icon reading.
`D04` asks whether explicit overlap/recess is the missing depth cue. `D05`
asks whether consistent cylinder construction gives vessels and tools a common
visual grammar without over-modeling instruments.

## Per-archetype nonnegotiables

### T75 flask

- Retain the broad shallow three-quarter chamber, angled neck, separate cap,
  visible rim, and contained liquid boundary. The cap and neck must read as a
  short cylinder/tube, not a colored tab.
- Empty and filled states keep the same production silhouette, projection,
  chamber geometry, viewBox, clips, and anchors. Filled adds only contained
  liquid behind final near contours; it never changes the flask's pose.
- Every direction shows at least a top face, a near or end wall, and an opening
  or cap-rim overlap. Cap ribs are optional only after the cap cylinder reads.

### Centrifuge

- Retain a squat housing with front controls and feet, top opening, nested
  rotor/cavity, and rear-hinged lid. The opening is an oval cut into the top
  plane, not a front-facing target disk.
- Idle and running states retain one mounting frame, projection, body extent,
  and control face. Motion may be represented only by a safe state cue after
  the rotor is occluded by the closed lid; it must not turn the device into a
  different object or expose a spinning rotor.
- Every direction shows body top/front/side massing, two nested chamber rims,
  and a lid thickness/hinge overlap. Rotor wells and button clusters yield to
  those cues at small size.

### P200 micropipette

- Retain a generic single-channel adjustable-pipette silhouette: plunger
  cylinder, front and side body faces, one inset display/recess, range collar,
  ejector/sleeve overlap, tapered shaft, and disposable-tip direction.
- Loaded and unloaded variants retain body, collar, display, shaft, tip pose,
  anchors, and viewBox. The visible state difference is limited to the
  contained tip/liquid cue; it never recolors or reshapes the instrument body.
- Every direction uses at least one body-side overlap and one cylindrical or
  rounded plunger cue. Remove display numerals, logos, dense seams, and fine
  ejector texture before losing the collar/shaft silhouette.

### Falcon 15 mL material vessel

- Retain cap cylinder, seated rim/shoulder, long cylindrical clear body,
  continuous conical lower mass, and an ellipse-consistent liquid surface. The
  tube remains generic: no Falcon wordmark, catalog text, or copied label.
- In the review fixture, use nested `bottom`/`body`/`surface` markers only to
  preview the conceptual material split; do not declare the SVG as a runtime
  material asset. In M7, translate the selected construction into the real
  Falcon production SVG and preserve its required direct-root semantic layers,
  root material declaration, clip and paint-role behavior, fill-height
  calibration, and stable viewBox. There, material color may occur only in the
  material band and derives from the runtime role pipeline.
- Every direction separates clear-plastic faces by overlap/value, not a filter
  or a donor-pink reflection. Graduations and writing panel remain sparse and
  subordinate to cap/body/cone/surface recognition.

## Candidate artifact layout

M5 working renders may be disposable under
`rendered-reports/equipment_svg_reviews/candidates/`. Once the evaluator
shortlists the five directions, promote the exact inputs and evidence below to
the tracked review-fixture tree. Nothing in this tree is discovered by the SVG
manifest generator or served as application art.

```text
docs/figures/equipment_kit/candidates/
  README.md
  D01-servier-shallow/
    source/
      t75_flask.svg
      centrifuge.svg
      p200_micropipette.svg
      falcon_15ml.svg
    renders/
      bench-composite-1920.png
      bench-composite-320.png
      bench-composite-real-size.png
      min-size-crops.png
      silhouette-composite-320.png
    evidence.md
  D02-rim-forward/
  D03-mass-first/
  D04-occlusion-strong/
  D05-quiet-cylinder/
```

Each `source/*.svg` follows the common 320-square/group/anchor contract above.
`evidence.md` names the direction, literal swatches, source references, render
command, evaluator finding, and any failed massing hypothesis. Rendered PNGs
are evidence only; they do not become pixel-regression fixtures.

## File-disjoint candidate ownership

M5 has five direction directories but only four source archetypes. Assign one
SVG coder to each archetype. That coder alone owns the named source across all
five direction directories; no direction-wide coder may edit another
archetype's source.

| Owner | Exclusive files in every `D01` through `D05` directory |
| --- | --- |
| T75 SVG coder | `source/t75_flask.svg` |
| Centrifuge SVG coder | `source/centrifuge.svg` |
| P200 SVG coder | `source/p200_micropipette.svg` |
| Falcon SVG coder | `source/falcon_15ml.svg` |

The four coders may work concurrently. They freeze all 20 source files only
after every candidate passes M0 normalizer acceptance; this is a required
source-freeze gate, not an optional later boundary. The acceptance record must
show the source path and pass result for each of the 20 fixtures. No composite
work starts before that complete pass. After the freeze, exactly one
compositor/fixture owner creates every `renders/` file, each direction's
`evidence.md`, the candidate-tree `README.md`, and the tracked-fixture
promotion. The independent evaluator is read-only: it may inspect sources and
composites, write a ranking outside this tree, and request a correction, but
it edits neither source nor fixture. A correction reopens only the owning
archetype's source; the compositor then regenerates its derived evidence after
that source again passes normalizer acceptance and re-freezes.

## Bench-composite and minimum-size rendering recipe

### M3 real-size benchmark

`bench-composite-real-size.png` is the real-size proof. It is a 1:1 CSS-pixel
contact sheet, not an enlarged review canvas: each tile preserves the listed
source frame dimensions and its art box at normal and minimum placement. The
compositor must put normal and minimum tiles side by side per archetype, retain
the neutral background, and record the table verbatim in that direction's
`evidence.md`. It may add thin non-art tile boundaries outside the source
frames for inspection, but it must not scale, crop, redraw, or add a bench,
hand, label, callout, or shadow within a source frame.

| Archetype | Normal source workspace / placement | Normal frame; visual box | Minimum source workspace / placement | Minimum frame; visual box |
| --- | --- | --- | --- | --- |
| T75 | `passage_hood_detachment_hood_workspace/center_flask` | 486 x 273 CSS px; 16.20 x 5.18 CSS px | `centrifuge_workspace/center_t75_flask_new_reseed` | 555 x 312 CSS px; 15.41 x 4.93 CSS px |
| Centrifuge | `bench_basic/center_centrifuge` | 452 x 254 CSS px; 96.64 x 132.22 CSS px | `centrifuge_workspace/center_centrifuge_spin` | 555 x 312 CSS px; 39.30 x 53.77 CSS px |
| P200 | `sdspage_prepare_sample_mix_batch_workspace/center_p200_sample_micropipette` | 400 x 225 CSS px; 7.29 x 29.18 CSS px | `drug_dilution_setup_bench_setup/right_p200_micropipette` | 523 x 294 CSS px; 6.71 x 26.85 CSS px |
| Falcon 15 mL | `dilution_workspace/carb_intermediate` | 539 x 303 CSS px; 11.86 x 70.72 CSS px | `centrifuge_workspace/rear_center_conical_rack` | 555 x 312 CSS px; 2.31 x 13.78 CSS px |

This named benchmark is derived from the M3 census rows for
`t75_flask_empty`, `centrifuge`, `p200_micropipette_loaded`, and
`falcon_15ml`; matching state companions share the same placement geometry.
The normal tile tests the ordinary in-scene reading. The minimum tile tests
mass survival and does not reject an otherwise physically correct object merely
because that placement is below a reasonable identification threshold.

### Enlarged diagnostic comparisons

1. Assemble the four 320-square sources into one neutral 1920 by 1080
   enlarged diagnostic bench composite in this fixed left-to-right order: T75,
   centrifuge, P200, Falcon. Place their `anchor-baseline` points on a shared
   bench line and preserve the same object scale/position for `D01` through
   `D05`. Do not add a backdrop, logos, hand, callout, or shadow to compensate
   for weak massing.
2. Produce `bench-composite-1920.png` from the same source order and draw
   order. Then downsample that exact diagnostic composite to
   `bench-composite-320.png` using a high-quality renderer; do not re-layout
   its contents for the smaller image. Neither file is real-size proof.
3. Produce `min-size-crops.png` from the same M3 table as
   `bench-composite-real-size.png`; use its exact normal and minimum source
   frame and visual-box values rather than a guessed thumbnail.
4. Produce `silhouette-composite-320.png` with one common dark fill per object,
   no internal lines, no material color, and no openings. Use it only to test
   major silhouette and balance. Recognition and reference-back review still
   use the full-color composite and the M4 boards.
5. The evaluator ranks candidates with cited observations for each archetype:
   silhouette, volume/occlusion, board-backed recognition, and small-size
   legibility. A concrete failure such as "centrifuge cavity reads as a front
   target" or "P200 collar disappears at its normal placement" blocks that
   candidate. A palette preference or uncited taste comment does not substitute
   for the named visual observation.

The render recipe is a historical controlled experiment, not a parallel mock
of the application. It is no longer a live renderer or acceptance path; M7/M12
production validation has been superseded by the current replacement evidence.

## M5 exit and M6 handoff

The historical candidate batch was ready for M6 only when all five IDs had the four source
fixtures, a complete 20-source M0 normalizer acceptance record, 1920/320 bench
composites, actual-size crops, silhouette diagnostic, and an independent
evaluator ranking. The M6 decision record compared the same five candidates
using Servier consistency, board fidelity, real-size legibility, coherent bench
depth, and the evaluator's cited findings. It made a provisional D04 decision
before the user rejected the complete D01-D05 pool. Preserve the directories as
frozen evidence, not for re-selection.

## Validation

Run from the repository root after this report is added:

```bash
source source_me.sh && python3 -m pytest tests/test_markdown_links.py -q
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py -q
git diff --check
```

The report is intentionally ASCII-only. It specifies one controlled M5
experiment and defers schema, runtime, and durable-kit changes until a selected
direction has visual evidence.
