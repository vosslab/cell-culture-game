# SVG asset gaps

This file owns current equipment-art gaps after the 2026-08-24 SVG consistency
sweep. [TODO](../docs/TODO.md) and [ROADMAP](../docs/ROADMAP.md) own protocol,
layout, validation, and result-UI workstreams.

Generic, unbranded, model-independent repository artwork qualifies as a
finished target.

## Current status

- All authored object `asset_name` values resolve through the recursive SVG
  registry.
- Every retained equipment SVG uses finished artwork.
- The strict SVG audit covers 131 objects and 146 retained SVGs with no orphan
  or structural findings.
- Material identity and volume rendering use the scalar `display_color` and
  semantic SVG material pipeline; the retired pink/orange/green proxy family is
  no longer the runtime model.
- Per-well material identity and amount rendering for `well_plate_96` are
  implemented and production-browser tested.
- The incubator sizing correction is complete; `display_width_cm` is 40 rather
  than the obsolete 55 cm value recorded by the old checklist.

## Remaining state-form debt

The following declared states currently select one shared SVG form. Current
protocols keep each field at its default value, making these bounded future
authoring slots.

| Object     | State field | Current rendering                                                 | Future completion                                              |
| ---------- | ----------- | ----------------------------------------------------------------- | -------------------------------------------------------------- |
| incubator  | `door_open` | Both cases select `incubator.svg`                                 | Add and wire a generic open-door state if a protocol uses it   |
| microwave  | `door_open` | The field has an empty composite; running uses closed/heating art | Add and wire a generic open-door state if a protocol uses it   |
| microscope | `light_on`  | Both cases select `microscope.svg`                                | Add a restrained illumination cue if a protocol uses the field |
| vortex     | `running`   | Both cases select `vortex.svg`                                    | Add a distinct running cue if a protocol writes the state      |

Resolved state families include heat-block lid, rocking-shaker running,
lightbox power, power-supply running, centrifuge running, water-bath occupancy,
electrode-module clamps, electrophoresis leads, and gel-cassette lifecycle; each
selects distinct retained artwork.

## Out of scope

The seven byte-preserved result composites remain future application-owned UI
work in [TODO](../docs/TODO.md) and [ROADMAP](../docs/ROADMAP.md). This ledger
continues to track equipment artwork.
