# M10 WP-B2 visual evaluation

## Replacement-wave addendum (2026-08-26)

The approval below is historical evidence. The plate-reader and rocking-shaker
pairs were rebuilt with rounded housings, real tray/platform recesses, and
state changes inside stable physical shells. Their package render review,
independent cross-package review, and current M12 full-consumer evidence are
complete.

## Disposition

**APPROVED.** The four WP-B2 sources meet the M10 visual target. No concrete
source change is required before integration.

## Evidence inspected

- The four owned sources:
  `plate_reader_idle.svg`, `plate_reader_reading.svg`,
  `rocking_shaker_idle.svg`, and `rocking_shaker_running.svg`.
- The M8 [equipment kit](../../figures/equipment_kit/README.md) and its
  [MEASUREMENTS.md](../../figures/equipment_kit/MEASUREMENTS.md), M2
  [counterpart sweep](svg_servier_counterpart_sweep.md), M3
  [census](svg_visual_size_flatness_census.md), and the WP-B2
  [reference and implementation report](svg_m10_wp_b2_reference_and_implementation.md).
- Standalone SVG renders made with `rsvg-convert` at the census normal and
  narrow sizes: reader 523 by 299 and 87 by 50 px; rocker 257 by 157 and
  58 by 36 px.
- Production-shaped scene renders made by `node tools/scene_to_png.mjs`:
  `mtt_solubilization_readout_plate_reader_workspace` at 536 by 302 px,
  `imaging_bench` at 1888 by 1062 px, and both
  `sdspage_destain_gel_setup_workspace` and `staining_bench` at 736 by
  414 px. All four scene renders reported populated scenes, 100% placement
  yield, zero render errors, and zero reported overlap pairs.

The first large reader capture was interrupted while another worker briefly
replaced generated output. The later small production-shaped reader capture,
the large rocker scene, and both task-scene renders completed. That transient
race does not affect the source or the reviewed render results.

## Observed facts

- The reader states share the 560 by 320 frame, housing, plate-opening
  geometry, front controls, base, feet, overlay root, and result anchors.
  Reading changes the contained optical surface, display value, and status
  control while retaining the same silhouette.
- At normal size, the reader has a broad low shell, pale top plane, dark
  recessed trapezoidal chamber, visible plate-sized inner surface, and a
  distinct low control face. At 87 by 50 px, its chamber and dark control
  mass remain visible while the small controls correctly simplify.
- In the real reader task view, the 96-well plate appears directly above the
  reader, and the reader remains visually distinct from the plate and its
  surrounding label/measurement UI.
- The rocker states share the 348 by 213.5 frame, base, feet, controls,
  pivot, tray construction, anchors, and overlay root. The running tray has
  a literal `rotate(8 177 128)` transform about the visible pivot, and the
  active status control changes from pale to green.
- At normal size, the rocker visibly reads as a rigid tray above a centered
  pivot on a broad base; its lit top, front lip, and receding right face
  provide a restrained three-plane volume. The running pose remains seated
  over the pivot rather than translated away from it. At 58 by 36 px, the
  platform angle and green active cue remain distinguishable.
- The static `img` render route is appropriate for all four sources according
  to the M3 census and their generated manifest entries. No direct-root
  material-rendering behavior is expected or needed here.

## Criterion findings

| Criterion | Finding |
| --- | --- |
| Generic plate-reader recognition and reference basis | PASS. The reader is a generic, unbranded absorbance-reader form: wide low housing, recessed plate chamber/window, display, controls, and feet. It does not copy a manufacturer arrangement. |
| Stable reader housing and state change | PASS. The optical window, display tone, and status cue change while the housing and anchors remain stable. The state difference is perceptible without destabilizing the object frame. |
| Rocker platform, pivot, and running pose | PASS. The tray rotates around the depicted mechanism; base and pivot remain fixed. The running pose is mechanically credible and is not a translated tray or a vortex substitute. |
| D04 volume with D01 restraint | PASS. Dark values consistently name actual recesses, the plate chamber, underside/lip, or pivot. The assets keep sparse details and retain readable large masses at the relevant small sizes. |
| Actual MTT, imaging, destaining, and staining consumers | PASS for available production-shaped evidence. The reader task and all three rocker consumer contexts rendered cleanly with the intended relative scale and no measured render errors. |

## Advisory observations

- The two amber running arcs are legible at normal size and help communicate
  reciprocating motion. If a later art pass seeks still more restraint, they
  are the first optional detail to reconsider because they are less physically
  necessary than the eight-degree tray pose and active control. They are not a
  blocker: their placement follows the tray sweep and they remain subordinate
  to the hardware.
- The narrow reader render is inherently generic in isolation; in its actual
  task view, the adjacent 96-well plate and the reader's distinct chamber
  establish the intended identity. No small-size micro-detail should be added
  merely to force brand-free recognition without context.

## Wedge-page note

The repository's "wedge pages" are a namespacing/file-loading regression
fixture for scenes that historically collided on an SVG ID; they are not a
generic visual-art category and do not supply WP-B2 visual evidence. The
focused sources have no `wedge` element or dependency. No wedge-page issue
affects this approval.

## Limitations

This is a visual review, not a replacement for the package normalizer,
compiler, or final browser suite. The first desired large reader scene capture
could not be repeated because concurrent integration briefly removed its
generated manifest; later scene captures and all standalone renders succeeded.
Re-run the final M12 browser/scene gates from a stable generated tree.
