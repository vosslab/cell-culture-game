# Third-Party Assets

This document lists all third-party assets integrated into the cell-culture game.

## Servier Medical Art Icons

The following Servier Medical Art bioicons have been integrated under the CC-BY-3.0 license. Each icon is sourced from the Servier Medical Art collection (https://smart.servier.com/) via bioicons.com (https://bioicons.com/).

License: CC-BY-3.0 (https://creativecommons.org/licenses/by/3.0/)
Attribution: Servier Medical Art, smart.servier.com

### Microbiology Collection

| Source File                     | Destination File                  | Modifications                                                              |
| ------------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| culture-flask-filled-lid.svg    | assets/equipment/t75_flask_v5.svg | Added anchor_liquid_clip, anchor_liquid_bounds, anchor_label, overlay_root |
| falcon-15ml-empty.svg           | assets/equipment/falcon_15ml.svg  | Added anchor system                                                        |
| falcon-50ml-empty.svg           | assets/equipment/falcon_50ml.svg  | Added anchor system                                                        |
| cell-culture-equipment-1.svg    | assets/equipment/cell_counter_instrument.svg | Added anchor system                                             |
| tube-screwcap-closed-orange.svg | assets/equipment/mtt_vial.svg     | Added anchor system                                                        |

### Lab Apparatus Collection

| Source File           | Destination File                  | Modifications       |
| --------------------- | --------------------------------- | ------------------- |
| centrifuge.svg        | assets/equipment/centrifuge.svg   | Added anchor system |
| incubator.svg         | assets/equipment/incubator.svg    | Added anchor system |
| microscope.svg        | assets/equipment/microscope.svg   | Added anchor system |
| spectrophotometer.svg | assets/equipment/plate_reader.svg | Added anchor system |
| bath-empty.svg; bath_filled.svg | assets/equipment/water_bath.svg; assets/equipment/water_bath_occupied.svg | Direct normalized adaptations of the respective Servier open-bath source; shared stable frame and runtime anchors only |
| agitator.svg          | assets/equipment/vortex.svg       | Added anchor system |

### Chemistry Collection

| Source File            | Destination File                          | Modifications       |
| ---------------------- | ----------------------------------------- | ------------------- |
| micropipette-multi.svg | assets/equipment/multichannel_pipette.svg | Added anchor system |
| pipette-box.svg        | assets/equipment/tip_box.svg              | Added anchor system |

## Bioicons CC-0 Lab Apparatus

Additional lab apparatus icons sourced from bioicons.com (https://bioicons.com/) under the CC-0 / Public Domain dedication. Each icon's contributor is credited in the table.

License: CC-0 / Public Domain (https://creativecommons.org/publicdomain/zero/1.0/)
Source: https://bioicons.com/

| Source File                | Destination File                      | Author / Contributor | Modifications                                                                  |
| -------------------------- | ------------------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| 96well_pcr_plate_kelly.svg | assets/equipment/96well_pcr_plate.svg | Xi-Chen              | None (registered as SVG_96WELL_PCR_PLATE via pipeline/generate_svg_globals.py) |

## DBCLS Lab Apparatus Icons

Lab apparatus icon sourced from bioicons.com (https://bioicons.com/) under the CC-BY-4.0 license.

License: CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)
Attribution: DBCLS, https://dbcls.rois.ac.jp/
Source: OTHER_REPOS/bioicons/static/icons/cc-by-4.0/Lab_apparatus/DBCLS/shaker.svg

| Source File | Destination File                             | Modifications                      |
| ----------- | -------------------------------------------- | ---------------------------------- |
| shaker.svg  | assets/equipment/rocking_shaker_idle.svg     | Normalized with normalize_svg_v2.py (arc-fixed); no anchors added |

## Anchor System

All integrated Servier SVGs include the following anchor elements for layout and interaction:

- `anchor_liquid_clip`: clipPath defining the liquid-bearing region (for bottles, flasks, tubes)
- `anchor_liquid_bounds`: rect covering the liquid region bounds
- `anchor_label`: rect positioning dynamic label overlays
- `anchor_error`: rect for error indicator positioning
- `overlay_root`: transparent group for engine-injected dynamic overlays

Non-liquid equipment (centrifuge, microscope, etc.) include only:

- `anchor_label`: rect positioning dynamic labels
- `overlay_root`: transparent overlay mount

## Material rendering

Object declarations select material effects; the shared renderer resolves the
active protocol material registry and updates declared regions in injected SVG
instances. `src/scene_runtime/renderer/anchor_material_renderer.ts` owns the
DOM mutation for the `anchor_liquid_bounds` target and optional
`anchor_liquid_clip`. SVG injection owns per-instance anchor resolution, so
assets provide anchors rather than object-specific recoloring code.

The current equipment source and attribution ledger is
`assets/equipment/SOURCES.md`.

## Attribution Footer

Credit line to include in HTML footer:
"Servier Medical Art icons by Servier (https://smart.servier.com/), licensed under CC-BY-3.0. Sourced via bioicons.com (https://bioicons.com/)."
