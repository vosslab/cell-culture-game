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

### Local provenance verification

The direct Servier mappings in this ledger were verified against the local
Bioicons checkout under
`OTHER_REPOS/bioicons/static/icons/cc-by-3.0/`. Its license text is at
`OTHER_REPOS/bioicons/static/icons/cc-by-3.0/LICENSE`; the checkout README
attributes Servier Medical Art at https://smart.servier.com under CC BY 3.0.
The M2 counterpart coverage ledger is at
`docs/active_plans/reports/svg_servier_counterpart_sweep.md`.
This verification adds no duplicate adoption rows: the table entries below
remain the canonical per-asset provenance mappings.

## Servier Adoptions

The following retained SVGs are direct or state-specific adaptations of Servier
Medical Art sources.

### Lab Apparatus / Servier

| Our Filename                           | Servier Source                                  | Notes                                                                              |
| -------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------- |
| `gel_cassette_empty.svg`               | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Empty gel electrophoresis cassette                                                 |
| `mini_protean_gel.svg`                 | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Same source as gel_cassette_empty; represents gel slab                             |
| `gel_comb.svg`                         | `Lab_apparatus/Servier/gel-electrophoresis.svg` | Comb detail from gel apparatus                                                     |
| `mini_protean_gel_unsealed.svg`        | `Lab_apparatus/Servier/gel-electrophoresis.svg` | State-specific unsealed gel-slab adaptation                                        |
| `gel_cassette_destained.svg`           | `Lab_apparatus/Servier/gel-electrophoresis.svg` | State-specific destained gel-cassette adaptation                                   |
| `gel_cassette_destaining.svg`          | `Lab_apparatus/Servier/gel-electrophoresis.svg` | State-specific destaining gel-cassette adaptation                                  |
| `gel_cassette_separated_unstained.svg` | `Lab_apparatus/Servier/gel-electrophoresis.svg` | State-specific separated, unstained gel-cassette adaptation                        |
| `gel_cassette_stained.svg`             | `Lab_apparatus/Servier/gel-electrophoresis.svg` | State-specific stained gel-cassette adaptation                                     |
| `centrifuge.svg`                       | `Lab_apparatus/Servier/centrifuge.svg`          | Direct normalized detailed geometry; runtime IDs and anchors added                 |
| `centrifuge_running.svg`               | `Lab_apparatus/Servier/centrifuge.svg`          | Controlled closed-lid state adaptation on the same detailed apparatus              |
| `incubator.svg`                        | `Lab_apparatus/Servier/incubator.svg`           | Direct normalized detailed geometry; runtime IDs and anchors added                 |
| `water_bath.svg`                       | `Lab_apparatus/Servier/bath-empty.svg`          | Direct normalized empty water-bath state; shared frame and runtime anchors only    |
| `water_bath_occupied.svg`              | `Lab_apparatus/Servier/bath_filled.svg`         | Direct normalized occupied water-bath state; shared frame and runtime anchors only |
| `vortex.svg`                           | `Lab_apparatus/Servier/agitator.svg`            | Direct normalized detailed geometry; runtime IDs and anchors added                 |

### Chemistry / Servier

| Our Filename               | Servier Source                             | Notes                                                                                  |
| -------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------- |
| `p10_micropipette.svg`     | `Chemistry/Servier/micropipette.svg`       | Direct normalized detailed geometry with the required tip-only material semantics      |
| `p10_gel_loading_tip.svg`  | `Chemistry/Servier/pipette-plastic.svg`    | Plastic pipette tip                                                                    |
| `multichannel_pipette.svg` | `Chemistry/Servier/micropipette-multi.svg` | Direct normalized detailed geometry with controlled dispensing-bore material semantics |

### Microbiology / Servier

| Our Filename             | Servier Source                                        | Notes                                                                         |
| ------------------------ | ----------------------------------------------------- | ----------------------------------------------------------------------------- |
| `falcon_15ml.svg`        | `Microbiology/Servier/falcon-15ml-empty.svg`          | Direct normalized detailed geometry with runtime material layers              |
| `falcon_50ml.svg`        | `Microbiology/Servier/falcon-50ml-empty.svg`          | Direct normalized detailed geometry with runtime material layers              |
| `bottle_medium_pink.svg` | `Microbiology/Servier/bottle-medium-pink.svg`         | Direct normalized detailed geometry with runtime material layers              |
| `microtube.svg`          | `Microbiology/Servier/microtube-open-translucent.svg` | Adapted open-cap geometry with repository runtime-material layers and anchors |

### Lab Apparatus / DBCLS (CC-BY-4.0)

| Our Filename                 | Source                                                  | Notes                                                                                   |
| ---------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `heat_block_closed.svg`      | `cc-by-4.0/Lab_apparatus/DBCLS/thermalcycler-pcr.svg`   | Lid and control anatomy reference for the repository-authored orthographic closed state |
| `heat_block_open.svg`        | `cc-by-4.0/Lab_apparatus/DBCLS/thermalcycler-pcr-2.svg` | Lid and control anatomy reference for the repository-authored orthographic open state   |
| `rocking_shaker_idle.svg`    | `cc-by-4.0/Lab_apparatus/DBCLS/shaker.svg`              | Normalized idle rocking-shaker state                                                    |
| `rocking_shaker_running.svg` | `cc-by-4.0/Lab_apparatus/DBCLS/shaker.svg`              | Repository-authored running-state adaptation                                            |
| `tube_rack.svg`              | `cc-by-4.0/Lab_apparatus/DBCLS/tube-rack.svg`           | Simplified normalized rack retaining the source composition                             |

Attribution: TogoTV / DBCLS (https://togotv.dbcls.jp/en/pics.html)
License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
Commercial use permitted.

### Bioicons CC0

| Our Filename           | Source                                                  | Notes                                                                              |
| ---------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `96well_pcr_plate.svg` | `cc-0/Lab_apparatus/Xi-Chen/96well_pcr_plate_kelly.svg` | Public-domain orientation reference for the repository-authored orthographic plate |
| `t75_flask_empty.svg`  | `cc-0/Lab_apparatus/Marcel_Tisch/T75_flask.svg`         | Empty state preserving the existing public-domain flask geometry                   |
| `t75_flask_filled.svg` | `cc-0/Lab_apparatus/Marcel_Tisch/T75_flask.svg`         | Filled state preserving the existing public-domain flask geometry                  |

## Repository artwork

The tables above are the confirmed external-source mappings. Git history owns
the change provenance for repository-authored artwork. Add each newly confirmed
external source here before reuse so licensing and attribution stay explicit.

Generic, unbranded repository artwork is an accepted finished target alongside
sourced art.

| Our Filename                                | Repository source and notes                                                                                                                                                                            |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `cell_counter_instrument.svg`               | Repository-authored generic automated cell counter; no external source geometry retained.                                                                                                              |
| `gel_opening_tool.svg`                      | Repository-authored generic aluminum cassette-opening lever; manufacturer manuals informed its physical role.                                                                                          |
| `electrophoresis_tank_black_lead_connected.svg` | Repository-authored apparatus overlay: one black plug is seated on the tank's measured cathode terminal and its cable exits toward the supply side.                                                   |
| `electrophoresis_tank_red_lead_connected.svg`   | Repository-authored apparatus overlay: one red plug is seated on the tank's measured anode terminal and its cable exits toward the supply side without crossing the black lead.                       |
| `lightbox_off.svg`                          | Repository-authored orthographic gel lightbox with one shared off/on housing.                                                                                                                          |
| `lightbox_on.svg`                           | Repository-authored orthographic gel lightbox with one shared off/on housing.                                                                                                                          |
| `microwave_closed.svg`                      | Repository-authored orthographic laboratory microwave with a closed, unlit door.                                                                                                                       |
| `microwave_heating.svg`                     | Repository-authored orthographic heating state preserving the same closed-door housing.                                                                                                                |
| `microscope.svg`                            | Repository-authored compound microscope. The exact Servier projection was not visually adequate for the required realistic physical form; it is adjacent reference only, not reused geometry.          |
| `gel_loading_tip_box.svg`                   | Repository-authored gel-loading-tip box. The exact Servier pipette-box projection was not visually adequate; it is adjacent construction evidence only.                                                |
| `p10_gel_loading_tip_box.svg`               | Repository-authored P10 gel-loading-tip box. The exact Servier pipette-box projection was not visually adequate; it is adjacent construction evidence only.                                            |
| `tip_box.svg`                               | Repository-authored general tip box. The exact Servier pipette-box projection was not visually adequate; it is adjacent construction evidence only.                                                    |
| `hazardous_liquid_waste_empty.svg`          | Repository-authored generic closed hazardous-waste carboy; bounded manufacturer and EPA reference research informed anatomy and handling context, without copied geometry or trade dress.              |
| `hazardous_liquid_waste_filled.svg`         | Filled companion using the same repository-authored hazardous-waste carboy geometry and contained liquid.                                                                                              |
| `aspirating_pipette.svg`                    | Repository-authored variable-volume aspirating pipette; the local Servier glass-pipette source is construction guidance only, not copied geometry.                                                     |
| `p20_micropipette.svg`                      | Independently authored generic P20 construction; no Servier source or geometry reused. Manufacturer anatomy evidence is recorded in `docs/active_plans/reports/svg_reference_board_micropipette.md`.   |
| `p200_micropipette.svg`                     | Independently authored generic P200 construction; no Servier source or geometry reused. Manufacturer anatomy evidence is recorded in `docs/active_plans/reports/svg_reference_board_micropipette.md`.  |
| `p1000_micropipette.svg`                    | Independently authored generic P1000 construction; no Servier source or geometry reused. Manufacturer anatomy evidence is recorded in `docs/active_plans/reports/svg_reference_board_micropipette.md`. |
| `repeat_dispenser.svg`                      | Repository-authored variable-volume repeat dispenser; the local Servier pipette-pistol source is construction guidance only, not copied geometry.                                                      |
