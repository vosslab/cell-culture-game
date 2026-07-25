# Instrument SVG identity audit

Status: current protocol-reached corpus reviewed; targeted repairs re-reviewed
blind at 600 px and 180 px, with the later water-bath state pair spot-checked
at 600 px.

## Current verdict

The active object mappings no longer contain the incubator-as-pipette,
slide-as-bottle, hood-as-bottle, cartridge-as-tip-box, pen-as-bottle, or dashed
placeholder failures found in the original audit. The protocol-reached
instrument families now have truthful source art. The highest-risk repairs were
also tested as anonymous rasters by reviewers who were given no expected
identity, source filename, SVG, repository context, or mapping.

The strongest result is not merely "the filename exists." Independent
reviewers identified the repaired microplate reader, electrophoresis power
supply, dry block heater, rocker, pipette-tip boxes, liquid-waste carboy,
and gel-staining tray at both large and scene-thumbnail scales. Their current
confidence range is 91-99%.

Four intentionally conservative qualifications remain:

- The incubator is recognized as an incubator or laboratory oven at 72-77%.
  That is the correct cabinet family, but the current source art does not prove
  a specific CO2-incubator model.
- The lightbox is recognized as a gel-imaging or capture station at 73-98%.
  That is role-compatible with the image-gel lesson, although "lightbox" is not
  every reviewer's first noun.
- The current direct Servier water-bath pair is label-dependent. The empty
  state was read first as an aquarium or circulation pump at 65%, with an
  immersion bath as an alternative; the occupied state was read first as a
  three-flask culture incubation or shaking setup at 53%. These exact
  source-preferred assets are retained, but the layout-manager label must carry
  the precise water-bath identity.
- Disposable wipes and lens tissue remain less specific at thumbnail scale.
  They are support consumables, not instruments, and are retained as a bounded
  visual backlog rather than blocking the instrument verdict.

## Blind method

The current generated scenes were scanned for every reached object of kind
`equipment`, `pipette`, `rack`, `waste`, `plate`, `flask`, or `decoration`.
Their active `visual_states` resolved to 55 unique, non-hidden SVG assets.
Each asset was rendered on white at 600 px and 180 px, then copied to an opaque
code name. Separate reviewers assessed the two scales and reported:

1. most likely real-world object;
2. visible state or action;
3. confidence from 0 to 100;
4. strongest alternative;
5. decisive visual cues.

No reviewer received the asset-name mapping. A low or wrong first identity was
treated as evidence, not averaged away. Targeted SVGs were revised and sent to
fresh reviewers under new opaque codes. The temporary raster corpus lived
under `/tmp`; no blind-test mapping or generated raster was added to production.

## Current recognition results

| Family | Current blind result | Verdict |
| --- | --- | --- |
| 96-well plate | Microplate, 99% at both scales | Pass |
| Automated cell counter and result state | Cell counter/imaging cytometer, 83-99% | Pass |
| Centrifuge open and running states | Centrifuge/microcentrifuge, 94-99% | Pass |
| Cell-counter cartridge and tube racks | Correct cartridge/rack family, 94-99% | Pass |
| Electrode module, tank, and chamber views | Gel-electrophoresis assembly or correct chamber part, 80-99% | Pass |
| Gel cassette, comb, inserted comb, and gel key | Correct gel component, 91-100% | Pass |
| Dry block closed and open states | Dry block/heat block, 92-99% after repair | Pass |
| Hemocytometer | Hemocytometer/cell-counting chamber, 88-96% | Pass |
| Biological safety cabinet states | Biological safety cabinet, 98-99% | Pass |
| Incubator | Laboratory incubator/oven family, 72-77% | Pass with model ambiguity |
| Lightbox states | Gel-imaging/capture station, 73-98% | Pass with noun ambiguity |
| Microscope | Compound microscope, 99% | Pass |
| Microwave states | Microwave at 98-99% large; dedicated 160 px replicate 98% | Pass after replicate |
| Mini-PROTEAN sealed and unsealed states | Precast gel package/cassette, 92-98% | Pass |
| Microplate reader idle and reading states | Microplate reader, 99% at both scales after repair | Pass |
| Electrophoresis power supply off and running states | Electrophoresis power supply, 98-99% after repair | Pass |
| Rocker idle and running states | Laboratory rocker, 91-98% in dedicated replicate | Pass |
| Gel-staining tray | Gel-staining tray, 96-99% after second repair | Pass |
| Vortex | Vortex mixer, 94-96% | Pass |
| Water bath, empty and occupied | Direct Servier pair reads as circulation equipment (65%) and flask incubation/shaking (53%) in current 600 px spot checks | Retain by explicit source preference; label-dependent |
| Multichannel and single-channel micropipettes | Correct pipette family, 99% | Pass |
| Aspirating and serological transfer pipettes | Transfer/serological pipette at thumbnail scale, 78-79% | Pass with subtype ambiguity |
| Standard and gel-loading tip boxes | Correct tip-box subtype, 99% after repair | Pass |
| T75 flask | Tissue-culture flask, 93-96% | Pass |
| Biohazard and liquid-waste containers | Correct waste family, 88-98%; liquid waste 98% after repair | Pass |

## Remaining non-instrument backlog

| Support asset | Blind result | Disposition |
| --- | --- | --- |
| `kimwipe_pad` | Sterile wrapper/wipe-like item, 40-64% | Improve when its lesson needs brand-independent wipe recognition. |
| `lens_tissue` | Clear tray/box, 76-82% | Redesign before requiring tissue-vs-wipe discrimination. |
| `paper_towel_pad` | Folded wipe/paper, 62-72% | Adequate for pat-dry action; visual specificity can improve later. |

## Historical baseline

The sections below preserve the original pre-repair evidence. They explain why
the repair work was necessary, but their state-to-asset mappings and priority
list are superseded by the current results above.

## Historical question answered

The current source tree does **not** map an incubator to a pipette: the
`incubator` object resolves to `assets/equipment/incubator.svg`, which renders
as a front-loading incubator. However, the broader concern is valid. Four
active objects still display a scientifically unrelated SVG, including a
hemocytometer slide rendered as a reagent bottle and a BSC workspace rendered
as a reagent bottle. The static reference test passes because every name
resolves to a real SVG; it does not judge whether the SVG depicts the named
instrument.

This audit follows the SVG ownership and source-to-manifest contract in
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) and the contract requirement
that clickable scene objects be SVG-backed representations of their actual
objects in [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md).

## Method and limits

For every equipment object and all pipette objects, this audit traversed each
`visual_states.*.cases[].output.asset_name`, resolved the key by basename
through `assets/**/*.svg`, and rasterized the source SVG with CairoSVG. The
contact sheets are retained locally under
`test-results/instrument_svg_identity/`:

- `equipment_contact_sheet.png` (28 resolved equipment state assets)
- `pipettes_contact_sheet.png` (10 resolved pipette state assets)
- `state_and_risk_pairs.png` (the new state pairs and high-risk mappings)
- `supporting_instruments.png` (tip-box and loading-tip support assets)

These images establish what the **current authored source SVGs** depict. They
do not prove that every browser scene emits every selected asset at its final
scale; the prior SVG audit recorded an emitted-manifest coverage gap. They
also do not establish whether a state mutation is reached by a particular
protocol. Source identity and state-pair claims below are kept separate from
that runtime question.

## P0: misleading active substitutions

| Authored object | State to source-asset mapping | What the pixels show | Classification | Required correction |
| --- | --- | --- | --- | --- |
| `hemocytometer_slide` | `material_name` `empty`, `trypan_blue`, `cell_suspension`, and `trypan_blue_mixture` -> `bottle` -> `assets/equipment/bottle.svg` | A capped magenta reagent bottle; no slide, cover slip, or counting chamber | **Misleading substitution** | Draw a hemocytometer slide/chamber asset with a material region; map every slide state to it. |
| `hood_surface` | `surface_cleanliness` `dirty` and `ethanol_sprayed` -> `hood_workspace_surface` -> `assets/equipment/hood_workspace_surface.svg` | A capped magenta reagent bottle; no biosafety-cabinet work surface | **Misleading substitution** | Replace with a BSC work-surface illustration; add a visible clean/dirty cue if that state remains instructionally significant. |
| `counter_slide_cartridge` (rack, non-equipment support instrument) | all state cases -> `tip_box` -> `assets/equipment/tip_box.svg` | An empty pipette-tip box / tray; not a cell-counter slide cartridge | **Misleading substitution** | Draw a cartridge that visually fits the automated cell counter and map it explicitly. |
| `label_pen` (pipette-kind utility) | `in_hand` `false` and `true` -> `bottle` -> `assets/equipment/bottle.svg` | A capped magenta reagent bottle; not a marker or pen | **Misleading substitution** | Move or retain its authoring kind as appropriate, but give it a pen asset before it is a required click target. |

The first two are directly in learning workflows and should block claims that
all core equipment is visually trustworthy. The cartridge and label pen are
also wrong-object representations, but their priority depends on the
protocols in which they are required.

## Equipment mapping and visual classification

The arrows below are exact current YAML state-to-asset mappings. `Same asset`
means the stated values select an identical source asset and therefore cannot
teach that transition through a whole-asset visual change.

| Object | State -> asset -> source SVG | Pixel assessment |
| --- | --- | --- |
| `cell_counter` | `slide_loaded` `false`/`true` -> `cell_counter_instrument` -> `assets/equipment/cell_counter_instrument.svg` | Correct identity; screen and capture controls read as an automated cell counter. State-pair identity failure. |
| `centrifuge` | `running` `false`/`true` -> `centrifuge` -> `assets/equipment/centrifuge.svg` | Correct identity (bench centrifuge). State-pair identity failure. |
| `electrode_module` | `mounted`, `cassette_mounted`, and `wing_clamps_open`, each `false`/`true` -> `electrode_module` -> `assets/equipment/electrode_module.svg` | **Missing/placeholder**: dashed empty rectangle, not electrophoresis hardware. |
| `electrophoresis_tank` | `inner_chamber_material_name` all three values -> `electrophoresis_tank_inner_chamber`; `outer_chamber_material_name` all three values -> `electrophoresis_tank_outer_chamber` -> corresponding `assets/equipment/*.svg` | Generic-but-honest chamber views. They distinguish inner from outer chamber, but neither material change is visible in the source art. |
| `gel_cassette` | `material_name` `empty`, `protein_ladder`, `protein_sample_denatured` -> `mini_protean_gel` -> `assets/equipment/mini_protean_gel.svg` | **Misleading substitution / state-pair identity failure**: depicts the same gel-and-pipette scene used by the sealed gel. |
| `gel_comb` | `position` `in_cassette`/`not_in_cassette` -> `gel_comb` -> `assets/equipment/gel_comb.svg` | **Misleading identity**: byte-identical to `gel_cassette.svg` and `mini_protean_gel.svg`; cannot distinguish comb from cassette. |
| `gel_opening_tool` | `visible` `true`/`false` -> `gel_opening_tool` -> `assets/equipment/gel_opening_tool.svg` | **Missing/placeholder**: dashed empty rectangle. |
| `heat_block` | `lid_open` `false` -> `heat_block_closed`; `true` -> `heat_block_open` -> corresponding `assets/equipment/*.svg` | **Correct identity and successful state pair**. Closed version visibly has a closed lid; open version exposes six tubes and open lid. Temperature readout and controls remain recognizable. |
| `hemocytometer_slide` | all four `material_name` values -> `bottle` -> `assets/equipment/bottle.svg` | **P0 misleading substitution**, detailed above. |
| `hood_surface` | `surface_cleanliness` `dirty`/`ethanol_sprayed` -> `hood_workspace_surface` -> `assets/equipment/hood_workspace_surface.svg` | **P0 misleading substitution**, detailed above. |
| `incubator` | `door_open` `false`/`true` -> `incubator` -> `assets/equipment/incubator.svg` | Correct identity: front-loading incubator, not a pipette. Door-open state has no source-art cue. |
| `lightbox` | `powered_on` `false` -> `lightbox_off`; `true` -> `lightbox_on` -> corresponding `assets/equipment/*.svg` | **Correct identity and successful state pair**. Off is dark with gray indicator; on has a bright cyan illuminated panel, green indicator, and highlighted capture control. |
| `microscope` | `light_on` `false`/`true` -> `microscope` -> `assets/equipment/microscope.svg`; objective values use overlays, not an asset swap | Correct identity (compound microscope). Light state has no whole-asset cue; objective-specific overlay needs browser verification. |
| `microwave` | `door_open` `false`/`true` -> `microwave_closed` -> `assets/equipment/microwave_closed.svg` | Correct identity, but explicit door-state pair failure. |
| `mini_protean_gel` | `sealed` `true`/`false` -> `mini_protean_gel` -> `assets/equipment/mini_protean_gel.svg` | Generic-but-honest gel cassette illustration in isolation, but byte-identical to `gel_comb.svg` and `gel_cassette.svg`; sealing has no cue. |
| `plate_reader` | `reading` `false`/`true` -> `plate_reader` -> `assets/equipment/plate_reader.svg` | Correct identity (microplate reader). Reading state has no cue. |
| `power_supply` | `running` `false`/`true` -> `power_supply_on` -> `assets/equipment/power_supply_on.svg` | Generic-but-honest bench power supply; both states show a lit `300` display, so off/running is misleading. |
| `rocking_shaker` | `running` `false`/`true` -> `rocking_shaker_idle` -> `assets/equipment/rocking_shaker_idle.svg` | Correct identity (platform shaker); motion/running has no cue. |
| `staining_tray` | `material_name` `empty`, `running_buffer_1x`, `coomassie_stain`, `destain`, `ddh2o` -> the matching `staining_tray_*` SVG | Correct tray silhouette, but the five rasterized assets are visually indistinguishable at object scale; material/state-pair identity failure. |
| `vortex` | `running` `false`/`true` -> `vortex` -> `assets/equipment/vortex.svg` | Correct identity (vortex mixer); running state has no cue. |
| `water_bath` | `running` `false`/`true` -> `water_bath` -> `assets/equipment/water_bath.svg` | Correct identity; state pair has no cue. |

## Pipettes and support instruments

| Object | State -> asset -> source SVG | Pixel assessment |
| --- | --- | --- |
| `aspirating_pipette` | all material states -> `aspirating_pipette` -> `assets/equipment/aspirating_pipette.svg` | Generic-but-honest slender disposable aspirating pipette. |
| `micropipette` | `empty` -> `p200_micropipette_empty`; all filled material states -> `p200_micropipette_filled` -> matching `assets/equipment/*.svg` | Correct micropipette identity; empty/filled cue is subtle but present at tip. |
| `multichannel_pipette` | all material states -> `multichannel_pipette` -> `assets/equipment/multichannel_pipette.svg` | Correct multichannel identity; no material-state cue. |
| `p10_micropipette` | `empty` -> `p10_micropipette_empty`; filled states -> `p10_micropipette_filled` -> matching `assets/equipment/*.svg` | Correct micropipette identity; distinguishable only by its source label/key rather than an obvious size marking at contact-sheet scale. |
| `p200_micropipette` | `empty` -> `p200_micropipette_empty`; filled states -> `p200_micropipette_filled` -> matching `assets/equipment/*.svg` | Correct micropipette identity; same size-marking caveat. |
| `serological_pipette` | all material states -> `serological_pipette` -> `assets/equipment/serological_pipette.svg` | Correct identity (graduated serological pipette); no material-state cue. |
| `label_pen` | `in_hand` `false`/`true` -> `bottle` -> `assets/equipment/bottle.svg` | **Misleading substitution**. |
| `micropipette_tip_box` | all state cases -> `tip_box` -> `assets/equipment/tip_box.svg` | Generic-but-honest open tip tray, though individual tips are not legible. |
| `p10_gel_loading_tip` | all state cases -> `p10_gel_loading_tip` -> `assets/equipment/p10_gel_loading_tip.svg` | Correct narrow gel-loading tip identity. |
| `p10_gel_loading_tip_box` | all state cases -> `p10_gel_loading_tip_box` -> `assets/equipment/p10_gel_loading_tip_box.svg` | Generic-but-honest tip-box silhouette; visually very close to the ordinary tip box. |
| `counter_slide_cartridge` | all state cases -> `tip_box` -> `assets/equipment/tip_box.svg` | **Misleading substitution**. |

## Highest-priority fixes

1. Replace the hemocytometer-slide, BSC-workspace, and counter-slide-cartridge
   substitutions before treating their associated lessons as visually valid.
2. Replace the two dashed placeholders (`electrode_module`,
   `gel_opening_tool`) with actual equipment art.
3. Separate gel comb, gel cassette, and sealed Mini-PROTEAN gel. Their three
   source SVG files are byte-identical (SHA-256
   `196fc0484d751840944092d5340d7fe12ec851effc2e0b6ee2638ba171a8656f`).
4. Preserve the new heat-block and lightbox state pairs as the pattern for
   microwave, incubator, power supply, shaker, vortex, centrifuge, plate
   reader, water bath, and staining tray. The newly edited pairs are clear
   source-art improvements, but still need a browser-flow regression.
5. Add a semantic asset-identity test table: object id, intended equipment
   family, allowed asset keys, and a required human-reviewed thumbnail. A
   filename-existence test alone cannot catch a bottle-in-place-of-slide bug.

## Verification record

```bash
source source_me.sh && python3 -m pytest tests/test_object_asset_refs.py \
  tests/test_svg_manifest_predicate.py -q
# 10 passed in 0.14s

source source_me.sh && python3 -m pytest tests/test_markdown_links.py -q
# 547 passed in 0.40s
```

The first command validates every selected SVG key and the generated-manifest
predicate. It cannot certify semantic correctness; the rendered contact sheets
and explicit classifications above supply that separate review layer.
