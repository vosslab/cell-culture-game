# SVG asset sources

This ledger records confirmed source mappings for retained equipment SVGs. File
names are basenames under `assets/equipment/`; the recursive asset registry owns
their `binary_state/`, `multi_state/`, `static/`, or `variable_volume/`
location. Rows cover retained source mappings.

## Attribution

All Servier-adopted SVGs in this directory are licensed under **CC BY 3.0 (Servier)**.

Attribution: Servier Medical Art (https://smart.servier.com)
License: CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/)
Commercial use permitted.

## Servier Adoptions

The following retained SVGs are direct or state-specific adaptations of Servier
Medical Art sources.

### Lab Apparatus / Servier

| Our Filename              | Servier Source                                  | Notes                                                                              |
| ------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| `gel_cassette_empty.svg`  | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Empty gel electrophoresis cassette                                                 |
| `mini_protean_gel.svg`    | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Same source as gel_cassette_empty; represents gel slab                             |
| `gel_comb.svg`            | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Comb detail from gel apparatus                                                     |
| `centrifuge.svg`          | `Lab_apparatus/Servier/centrifuge.svg`          | Idle benchtop centrifuge state                                                     |
| `centrifuge_running.svg`  | `Lab_apparatus/Servier/centrifuge.svg`          | Repository-authored running-state adaptation                                       |
| `incubator.svg`           | `Lab_apparatus/Servier/incubator.svg`           | Normalized incubator form                                                          |
| `microscope.svg`          | `Lab_apparatus/Servier/microscope.svg`          | Normalized microscope form                                                         |
| `water_bath.svg`          | `Lab_apparatus/Servier/bath-empty.svg`          | Direct normalized empty water-bath state; shared frame and runtime anchors only    |
| `water_bath_occupied.svg` | `Lab_apparatus/Servier/bath_filled.svg`         | Direct normalized occupied water-bath state; shared frame and runtime anchors only |
| `vortex.svg`              | `Lab_apparatus/Servier/agitator.svg`            | Normalized benchtop vortex form                                                    |

### Chemistry / Servier

| Our Filename                  | Servier Source                             | Notes                              |
| ----------------------------- | ------------------------------------------ | ---------------------------------- |
| `p10_micropipette_empty.svg`  | `Chemistry/Servier/micropipette.svg`       | Micropipette                       |
| `p10_gel_loading_tip_box.svg` | `Chemistry/Servier/pipette-box.svg`        | Pipette tip box                    |
| `p10_gel_loading_tip.svg`     | `Chemistry/Servier/pipette-plastic.svg`    | Plastic pipette tip                |
| `multichannel_pipette.svg`    | `Chemistry/Servier/micropipette-multi.svg` | Normalized multichannel pipette    |
| `tip_box.svg`                 | `Chemistry/Servier/pipette-box.svg`        | Normalized general pipette-tip box |

### Microbiology / Servier

| Our Filename             | Servier Source                                | Notes                                        |
| ------------------------ | --------------------------------------------- | -------------------------------------------- |
| `falcon_15ml.svg`        | `Microbiology/Servier/falcon-15ml-empty.svg`  | Material-rendered conical form               |
| `falcon_50ml.svg`        | `Microbiology/Servier/falcon-50ml-empty.svg`  | Material-rendered conical form               |
| `bottle_medium_pink.svg` | `Microbiology/Servier/bottle-medium-pink.svg` | Shared material-rendered reagent-bottle form |

### Lab Apparatus / DBCLS (CC-BY-4.0)

| Our Filename                 | Source                                                  | Notes                                                            |
| ---------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- |
| `heat_block_closed.svg`      | `cc-by-4.0/Lab_apparatus/DBCLS/thermalcycler-pcr.svg`   | PCR thermal cycler (lid closed); used as heat block closed state |
| `heat_block_open.svg`        | `cc-by-4.0/Lab_apparatus/DBCLS/thermalcycler-pcr-2.svg` | PCR thermal cycler (lid open); used as heat block open state     |
| `rocking_shaker_idle.svg`    | `cc-by-4.0/Lab_apparatus/DBCLS/shaker.svg`              | Normalized idle rocking-shaker state                             |
| `rocking_shaker_running.svg` | `cc-by-4.0/Lab_apparatus/DBCLS/shaker.svg`              | Repository-authored running-state adaptation                     |
| `tube_rack.svg`              | `cc-by-4.0/Lab_apparatus/DBCLS/tube-rack.svg`           | Simplified normalized rack retaining the source composition      |

Attribution: TogoTV / DBCLS (https://togotv.dbcls.jp/en/pics.html)
License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
Commercial use permitted.

### Bioicons CC0

| Our Filename           | Source                                                  | Notes                                                                              |
| ---------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `96well_pcr_plate.svg` | `cc-0/Lab_apparatus/Xi-Chen/96well_pcr_plate_kelly.svg` | Public-domain orientation reference for the repository-authored orthographic plate |

## Repository artwork

The tables above are the confirmed external-source mappings. Git history owns
the change provenance for repository-authored artwork. Add each newly confirmed
external source here before reuse so licensing and attribution stay explicit.

Generic, unbranded repository artwork is an accepted finished target alongside
sourced art.

| Our Filename                  | Repository source and notes                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `cell_counter_instrument.svg` | Repository-authored generic automated cell counter; no external source geometry retained.                     |
| `gel_opening_tool.svg`        | Repository-authored generic aluminum cassette-opening lever; manufacturer manuals informed its physical role. |
| `mtt_powder_vial.svg`         | Discrete solid-content form using the canonical repository microtube geometry and a contained powder bed.     |
| `mtt_powder_vial_empty.svg`   | Empty companion using the same canonical repository microtube geometry.                                       |
| `t75_flask_empty.svg`         | State adaptation of the repository-authored root `T75_flask.svg`.                                             |
| `t75_flask_filled.svg`        | Filled state adaptation of the repository-authored root `T75_flask.svg`.                                      |
