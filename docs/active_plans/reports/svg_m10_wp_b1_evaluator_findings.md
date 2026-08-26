# M10 WP-B1 visual evaluator findings

## Replacement-wave addendum (2026-08-26)

The approval below describes the rejected historical visual direction. The
current repair restores detailed normalized Servier geometry for the water-bath
pair, incubator, and vortex where the direct source is credible. The microscope
is instead a controlled repository-authored physical adaptation because the
exact Servier projection remained cubist at consumer size. State frames,
anchors, and ownership remain unchanged. Package-level renders, independent
cross-package review, and current M12 full-consumer evidence are complete.

## Verdict

**APPROVED.** The thirteen WP-B1 sources are coherent physical-equipment art
and the compact real-scene evidence gap is closed. No source-art revision is
required for this package.

## Scope and evidence

This is an independent visual review of the WP-B1 sources listed in
[svg_m10_wp_b1_reference_and_implementation.md](svg_m10_wp_b1_reference_and_implementation.md).
It uses the M8 [equipment kit](../../figures/equipment_kit/README.md),
[measurements](../../figures/equipment_kit/MEASUREMENTS.md), M2
[counterpart sweep](svg_servier_counterpart_sweep.md), and M3
[size and flatness census](svg_visual_size_flatness_census.md).

Observed render evidence:

- All 13 authored SVGs rendered with Librsvg at standalone normal size and
  their actual M3 minimum widths. The small render preserves the object mass,
  outer contour, and the state cue; it does not attempt to preserve controls
  or text below the M8 normal-size detail floor.
- The built app rendered through HTTP at 1920x1080 and compact viewports:
  `bench_basic` at 452x800, `cell_counter_basic` at 383x800, and
  `microscope_basic` at 383x800. Each had 100 percent placement yield, zero
  render errors, and zero art-overlap pairs.
- State pairs retain matching viewBoxes: counter 372x213, heat block and
  lightbox 160x120, microwave 404x268, and water bath 296x290. The counter
  and water bath also retain `overlay_root`, `anchor_label`, and `anchor_error`.

The compact check is actual browser evidence, not a mocked comparison page.

## Family calls

| Family | Call | Observed facts | Judgment |
| --- | --- | --- | --- |
| Cell counter | APPROVED | Both forms retain the wide analyzer cabinet, recessed display, right control stack, feet, and the same 372x213 frame. The acquisition display and result trace are visibly different without changing the housing. At the 66x38 literal minimum, the cabinet and display/control split still read. | A recognizable generic automated cell counter with restrained D04 display recesses; the result is an appropriate physical state, not a separate result-screen UI. |
| Heat block | APPROVED | The closed form is a compact heated-instrument silhouette. The open form exposes a rear lid, dark deck recess, and seated tubes. The 30x23 literal minimum retains the closed/open distinction through silhouette and light/dark opening. | The lid/cavity/tube relation is real D04 occlusion, while the three-plane shell remains as quiet as D01 asks. |
| Lightbox | APPROVED | Both forms have the same low instrument shell and bounded tray opening. The powered form changes the contained tray from dark to lit rather than adding unrelated decoration. At 80x60 it remains a readable shallow imaging base. | The physical tray recess makes the controlled illumination believable and avoids a generic dark rectangle. |
| Microwave | APPROVED | The stable cabinet, recessed window, feet, and right control panel remain fixed. Heating changes the visible cavity illumination and adds a contained vessel behind the window. The 72x48 minimum preserves the cabinet/window/control separation. | The dark window is a real cavity and the warm state stays physically closed, so D04 does not become arbitrary banding. |
| Water bath | APPROVED | Both forms retain the same large shallow enclosure, near rim, front controls, and 296x290 frame. Occupied tubes rise from a water surface behind that unchanged near rim. The 104x102 minimum remains the strongest readily recognized bath silhouette in the package. | State continuity is especially strong: added tubes and water describe occupancy without rebuilding the apparatus. |
| Incubator | APPROVED | The tall cabinet has a clear door/window, side control strip, top plane, and feet. At its 52x65 literal minimum the cabinet-plus-door silhouette remains clear. | The light front plane, dark control recess, and restrained side plane express a functional incubator without decorative shading. |
| Microscope | APPROVED | The compound microscope keeps an angled head, objective/stage overlap, coarse-focus wheel, and wide base. The actual compact 383px `microscope_basic` scene shows a legible instrument mass and it remains recognizable at the 33x57 M3 minimum. | This is the clearest identity-carrier among the small vertical assets; physical overlaps, not extra outlines, carry its depth. |
| Vortex | APPROVED | The cup, tilted control deck, pedestal, and base remain visible at normal size. The 17x20 literal minimum intentionally reduces to cup-on-pedestal silhouette, consistent with the census's minimum-use context. | The source does not promise micro-control readability at 17px. Its silhouette remains sufficient as a contextual bench object; normal-size placements retain the functional details. |

## Cross-family judgment

Observed: each asset uses the kit's `#294657` contour/cavity role and the
related cool mechanical face values, with one shallow elevated/front-left
construction language. Cabinets, bath, heat block, lightbox, microwave, and
counter share a recognizable restrained three-plane family; incubator,
microscope, and vortex stay compatible without being forced into box shapes.

Judgment: the package achieves D04 where it names a physical recess, far plane,
or overlap (display cavities, trays, lids, doors, and vessel/window interiors)
and D01 where added depth would only make the assets busy. It is coherent across
bench, cell-counter, and microscope contexts and retains silhouette-first
legibility at literal minimum placement.

## Non-blocking presentation note

At the compact browser viewports, surrounding DOM labels and state chips become
larger than several contextual SVGs and can visually collide with one another.
The render statistics show zero SVG-art overlap pairs, and the assets themselves
remain unclipped and recognizable. This is a shared responsive scene-label
presentation concern, outside WP-B1 source ownership; it is advisory rather
than a reason to alter these SVGs.

## Limitations

- This review judges recognition, physical plausibility, state continuity, and
  rendered coherence. It does not re-audit the owner YAML, semantic taxonomy,
  provenance license entries, or measured color contrast.
- The temporary standalone and browser captures are evaluation evidence, not a
  checked-in new visual fixture. The production app and the census remain the
  durable reproducible paths.
