# M11 WP-O1 visual evaluation

## Replacement-wave addendum (2026-08-26)

The approval below is historical evidence. The contextual-art repair retained
intentional panels and overlays while making gel migration fronts physical and
horizontal, microscope fields morphologically irregular with nuclei, and
formazan deposits granular rather than faceted. Package review, independent
cross-package review, and current M12 full-consumer evidence are complete.

## Scope and method

This is a fresh visual review of the 27 composite-only and learner-context SVGs
owned by WP-O1 in [svg_batch_ownership_matrix.md](svg_batch_ownership_matrix.md#wp-o1-overlays-observation-graphics-and-feedback-art).
It evaluates them only with their named bases: WP-E1's cassette, WP-B1's
lightbox, WP-C2's hemocytometer and plate, and the real cell-counter/microscope
consumers. Protected result-interface SVGs are outside this review.

I read the WP-O1 implementation record, the M1 inventory, the M3 size census,
and the published equipment kit. I inspected all 27 source layers in a
temporary diagnostic composite sheet, then used the built `scene_viewer.html`
with Chromium at 1920 x 1080 and 320 x 640. The initial in-sandbox Chromium
launch failed with macOS Mach-port denial; the same local renderer succeeded
outside that sandbox. No source or application files were changed.

## Observed facts

- Every cassette fragment and migration source uses `viewBox="0 0 214 308"`,
  exactly matching `gel_cassette_empty.svg`. The layers occupy the appropriate
  part of that shared frame: comb at the well row, tape at the bottom plate,
  clamp layers outside the cavity, migration evidence in the gel cavity, and
  the removed plate on the right-receding face.
- Every lightbox layer uses the unchanged `160 x 120` frame of the WP-B1
  lightbox base. Gel/tray evidence is confined to the sloped display region;
  capture, band, and molecular-weight indications are separate transparent
  layers.
- The two hemocytometer observation layers use the `400 x 220` WP-C2 slide
  frame. The two microscope-field layers use the microscope's
  `283.843 x 489.184` frame. The crystal layer uses the plate's
  `393.3275 x 278.5243` frame.
- The diagnostic sheet shows a stable visual vocabulary: blue migration fronts,
  bounded gel bands, transparent tray/display layers, clear versus blue cells,
  a counted grid, dense adherent versus spaced rounded cells, and localized
  purple crystal clusters. None adds rendered learner prose; the three
  learner-context assets communicate only expression, a writing surface, and
  selected-choice geometry.
- All 27 sources passed `source source_me.sh && python3
  tools/normalize_svg_v3.py` individually into `/private/tmp/m11_o1_normalized`.
- Built browser captures for `sdspage_prepare_gel_cassette_workspace`,
  `sdspage_image_gel_workspace`, `hemocytometer_count_review`, and
  `passage_hood_detachment_microscope_view` were populated with 100% placement
  yield and no render errors at both viewports. Their default protocol states
  do not activate every WP-O1 composite, so those captures prove the real
  delivery/consumer path and base registrations, while the diagnostic composite
  inspection establishes each individual layer's state art.

## Findings

| Subgroup | Judgment | Finding |
| --- | --- | --- |
| Cassette fragments and migration layers (9) | APPROVED | The shared `214 x 308` registration preserves the visible WP-E1 cassette. Comb, tape, clamp, and removed-plate geometry reads as physical attachment/removal rather than a competing cassette; all four migration states stay in the gel cavity and make start, progress, stop zone, and overrun distinguishable without prose. |
| Lightbox tray, gel, and capture evidence (8) | APPROVED | The layers follow the WP-B1 display's receding plane. Trays and gels remain visually subordinate to the lightbox housing; bands and molecular-weight marks are legible evidence instead of an opaque replacement display. |
| Cell-counter and hemocytometer observations (4) | APPROVED | Manual panels preserve their monitor registration. The hemocytometer overlays align to the WP-C2 chamber: live/dead marks are distinguishable by color and the counted state adds an intelligible grid/count annotation without replacing the slide. |
| Microscope fields and plate crystals (3) | APPROVED | The confluent field reads as adherent, near-confluent morphology and the alternate field as detached rounded cells. Crystal clusters remain localized to well centers and do not introduce a duplicate plate or imply liquid fill. |
| Learner-context art (3) | APPROVED | The instructor, calculation pad, and choice card are recognizable at normal built-consumer scale, language-neutral in rendered art, and visually separate from apparatus provenance claims. |

## Normal and minimum evidence

- At 1920 px, the real cassette, lightbox, hemocytometer/counter, and
  microscope consumers are clear, unclipped, and visually coherent with their
  named physical bases. The available initial scenes show the base registrations
  rather than all later protocol-state layers.
- At 320 px, the existing scene-wide layout compresses placement labels and
  state-overlay pills into collisions. The associated art reduces to
  silhouette/context, as M3's low placement widths predict. This occurs in
  unmodified base consumers too; it is a renderer responsive-layout issue, not
  a defect in a WP-O1 SVG or its composite registration.

## Advisory and limitations

- **Advisory, integration owner:** resolve the global 320 px label/pill
  collisions in the scene renderer or responsive layout. Do not add prose or
  compensating labels into these SVGs.
- The static scene viewer deliberately renders initial scene state. A visible-UI
  walkthrough that reaches every later overlay state remains M12 evidence; it
  is not a reason to mutate these assets or to reject their demonstrated shared
  coordinate registrations.

## Decision

**WP-O1: APPROVED.** No concrete visual blocker was observed in the owned
sources, their named coordinate frames, or the real built consumer path. Keep
the M12 walkthrough and the responsive-label advisory as integration work.
