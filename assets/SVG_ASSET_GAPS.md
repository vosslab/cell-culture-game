# SVG asset gaps

Tracks SVG assets that are placeholders, proxies, or interim art and need real
source art. Human updates this as art is sourced.

This file is a working checklist from the asset rework completed 2026-05-30.
Check a box once the gap is resolved.

## Placeholder objects

No source art was found for these objects, so they currently render as an orange
placeholder box. Each needs real art sourced or imported.

| Object | Current state | Done looks like | Status |
| --- | --- | --- | --- |
| power_supply | Orange placeholder box | Real lab power-supply SVG imported and normalized | [ ] |
| electrode_module | Orange placeholder box | Real electrode-module SVG imported and normalized | [ ] |
| gel_opening_tool | Orange placeholder box | Real gel-opening-tool SVG imported and normalized | [ ] |

## Interim or hand-authored art

These work today but should be swapped for a real icon if a good source turns up.

| Object | Asset | Current state | Done looks like | Status |
| --- | --- | --- | --- | --- |
| cell_counter | cell_counter_instrument.svg | Hand-authored by a subagent | Replaced with a real benchtop cell-counter icon | [ ] |

The protocol-facing tissue family is complete: `kimwipe_pad.svg` depicts four
loosely knotted Kimwipes for gel destaining, `lens_tissue.svg` depicts a
lint-free slide-edge wipe, and `paper_towel_pad.svg` depicts an absorbent
stack beneath a 96-well plate. These are distinct hand-authored scientific
silhouettes, not placeholders or interchangeable proxy art.

## Color proxies

The palette is currently limited to pink, orange, and green. The per-material
recolor pipeline was lost in the Solid.js rewrite, so bottles cannot tint per
material. Blue dyes currently proxy to bottle_green because no blue bottle
variant exists.

The real fix is restoring the display_color recolor pipeline in the Solid.js
runtime (tracked follow-up). After that, single-base bottle art tints per
material and these proxies go away.

| Material or bottle | Current proxy | Done looks like | Status |
| --- | --- | --- | --- |
| coomassie_stain | bottle_green (blue dye) | Tinted blue from single-base bottle art | [ ] |
| running buffers (SDS-PAGE) | bottle_green (blue dye) | Tinted blue from single-base bottle art | [ ] |
| display_color recolor pipeline | Lost in Solid.js rewrite | Recolor pipeline restored in Solid.js runtime | [ ] |

Note for human: list any other blue-dye bottles affected here as they are
identified, so the recolor follow-up covers them all.

## Collapsed state-pair art

There is no dynamic-SVG runtime yet, so open/closed and on/off states share one
asset. The object's state field is retained; the visual flips back once a second
asset plus a runtime swap land.

| Object | State field | Both states render as | Done looks like | Status |
| --- | --- | --- | --- | --- |
| heat_block | lid_open true/false | heat_block_closed | Open and closed art swap on state | [ ] |
| rocking_shaker | idle/running | idle | Idle and running art swap on state | [ ] |
| lightbox | on/off | on | On and off art swap on state | [ ] |
| microwave | open/closed | closed | Open and closed art swap on state | [ ] |
| power_supply | on/off | off | On and off art swap on state | [ ] |

## Deferred structured-surface art

| Object | Current state | Done looks like | Status |
| --- | --- | --- | --- |
| well_plate_96 | Placed in base scenes (object-level material only) | Per-well material overlays render in the Solid.js runtime | [ ] |

The 96-well plate is one object. Wells are per-well material overlays, like a
bottle liquid, not 96 separate scene objects. The object is now registered and
placed (`content/objects/plate/well_plate_96.yaml`) with object-level material
placeholders only; per-well distinct material state and overlay rendering remain
unimplemented (protocols writing per-well drug materials currently FAIL the
STEPPER stage). See docs/TODO.md.

## Build and protocol follow-ups

Open issues from the 2026-05-30 workstream that are not asset-art gaps but block
clean scene/protocol builds. Tracked here so they are not lost.

| Issue | Current state | Done looks like | Status |
| --- | --- | --- | --- |
| Stepper errors | Pre-existing systemic `placement_name_collision` and `ambiguous_target_in_scene` across protocols | Root cause investigated and resolved or suppressed with documented tickets | [ ] |
| SVG normalization backlog | ~49 objects not normalized | All object SVGs normalized via the pipeline normalizer | [ ] |
| Validator gate gap | `check_codebase.sh` does not run `validate.py` | `validate.py` wired into the check gate so validation failures fail CI | [ ] |
| Incubator oversize | `incubator` object renders too large and clips the rear_right zone | Incubator sized so it fits rear_right without clipping | [ ] |
| Recolor pipeline | `display_color` recolor pipeline lost in Solid.js rewrite (see Color proxies above) | Recolor pipeline restored in Solid.js runtime | [ ] |
