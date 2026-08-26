# SVG rebuild batch ownership matrix

## Purpose and boundary

This is the M9--M11 dispatch record for the current M1 inventory. It assigns every
retained production SVG exactly once to an M7 exemplar, an M9--M11 owner package,
or the protected/deferred result-interface boundary. It is execution evidence, not
product metadata and not a permanent-test specification.

The matrix follows the active [visual-quality rebuild plan](../active/svg_visual_quality_rebuild_plan.md),
the [M1 inventory](svg_visual_quality_inventory.md), the [M2 counterpart sweep](svg_servier_counterpart_sweep.md),
and the [M3 size and flatness census](svg_visual_size_flatness_census.md). A package
owner edits only its listed source SVGs and direct source-attribution or reference-board
evidence. It does not edit result interfaces, runtime schemas, scene placement, or
another package's SVGs.

`inline DOM` and `img` below use the generated manifest terms from M1. `bench`,
`hood`, `cell_counter`, and `microscope` name the M3 workspace classes. "Normal"
means the representative common placement; "minimum" means the M3 smallest reachable
placement and therefore the detail-legibility check. Both are review contexts, not
appearance snapshots or durable count gates.

## Dispatch rules

- Start M9, M10, or M11 only after M8 publishes the chosen construction kit. A fresh
  SVG owner and fresh evaluator review each package.
- Keep all states of one physical form together. State means physical condition,
  fill, lid, or attached part; it does not authorize a separate visual language.
- Reuse canonical physical forms where the M1 disposition is
  `REUSE_CANONICAL_FORM`: the owner preserves material anchors and applies one geometry
  to each bound material/object form instead of cloning vessel geometry.
- An overlay or observation asset is reviewed only with its named base or composite.
  Its owner may repair the overlay, but cannot redraw its base in another package.
- M9, M10, and M11 each expose no more than three concurrent, file-disjoint packages.
  Owners may work in parallel only within that milestone's three named packages.

## M7 exemplar ownership

M7 completes the four chosen archetypes before M8. These SVGs are excluded from the
later batches so their established geometry becomes kit evidence rather than a parallel
rewrite target.

| Package              | Physical-form decision and source/board need                                                                                                                                                                                                                                                                                                                          | Review context                                                                    | Exact SVG ownership                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `WP-X4-T75`          | One T75 culture-flask body with empty/filled contents. Use the T75 board and the M2 culture-flask-adjacent source; retain inline material anchors.                                                                                                                                                                                                                    | inline DOM; normal hood/centrifuge workspace, minimum T75 placement               | `binary_state/t75_flask_empty.svg`; `binary_state/t75_flask_filled.svg` |
| `WP-X4-centrifuge`   | One hinged benchtop centrifuge housing. Use the centrifuge board, direct Servier source, and a closed/occluded running state.                                                                                                                                                                                                                                         | img; normal bench/centrifuge workspace, minimum bench placement                   | `binary_state/centrifuge.svg`; `binary_state/centrifuge_running.svg`    |
| `WP-X4-micropipette` | One material-rendered P200 handheld form. `held_material_name` and `held_material_volume` paint only the contained tip through its 200 uL material contract. Use the micropipette board's bounded Eppendorf/Gilson anatomy evidence; P200 has no direct or adjacent Servier construction source unless a later redraw documents a specific reused structural feature. | inline DOM; normal electrophoresis/dilution workspace, minimum dilution placement | `variable_volume/p200_micropipette.svg`                                 |
| `WP-X4-falcon-15ml`  | Canonical 15 mL conical material vessel. Use the Falcon board and direct Servier source; one geometry serves the bound material forms.                                                                                                                                                                                                                                | inline DOM; normal cell-counter/centrifuge workspace, minimum material placement  | `variable_volume/falcon_15ml.svg`                                       |

## M9 consumables and labware

### `WP-C1`: canonical vessels and waste containers

**Source and reuse.** Use the M2 Falcon, microtube, bottle, and tray sources where
recorded. Build one canonical form for each vessel class; preserve material anchors
for `bottle_medium_pink`, `falcon_50ml`, and `microtube`. The balance tubes may reuse
the Falcon vessel construction at their own required proportions. The waste forms have
no local Servier source and need a bounded physical-reference board before redraw.

**Review.** `inline DOM`; normal cell-counter, centrifuge, and reagent-prep contexts;
minimum placements for the small tubes/vial and the waste-container workspace.

**Exact SVG ownership.**

- `binary_state/centrifuge_balance_tube_empty.svg`
- `binary_state/centrifuge_balance_tube_matched.svg`
- `binary_state/hazardous_liquid_waste_empty.svg`
- `binary_state/hazardous_liquid_waste_filled.svg`
- `binary_state/reagent_reservoir_empty.svg`
- `binary_state/reagent_reservoir_filled.svg`
- `variable_volume/bottle_medium_pink.svg`
- `variable_volume/falcon_50ml.svg`
- `variable_volume/microtube.svg`

### `WP-C2`: plates, slides, racks, and tip boxes

**Source and reuse.** Use the M2 multiwell-plate, counting-chamber, and pipette-box
sources. Each rack owns its complete body/well geometry; do not copy the microtube
form into rack SVGs. Keep reusable tip-box structure coherent between the ordinary
box here and the electrophoresis-specific boxes in `WP-E1`.

**Review.** Mixed inline DOM/img as recorded by M1; normal plate, heat-block, and
cell-counter contexts; minimum small-slide and rack placements.

**Exact SVG ownership.**

- `static/96well_pcr_plate.svg`
- `static/counter_slide_cartridge.svg`
- `static/dilution_tube_rack.svg`
- `static/heat_block_rack.svg`
- `static/hemocytometer_slide.svg`
- `static/microtube_rack_8.svg`
- `static/tip_box.svg`
- `static/tube_rack.svg`
- `static/waste_container.svg`

## M10 tools and instruments

### `WP-H1`: liquid-handling tools

**Source and reuse.** The P20/P1000 family inherits the M7 micropipette construction
kit but retains capacity-specific proportions and state anchors. P20, P200, and P1000
use the M4 bounded Eppendorf/Gilson anatomy evidence and are `no_servier_source` until
a specific reused Servier structural feature is documented. P10 and multichannel forms
retain their actual direct Servier provenance. The repeat dispenser and serological
pipette forms use their separately evidenced adjacent pistol and glass-pipette sources.
Keep the serological-pipette pack and its loose material form together so shared shaft
and scale decisions do not drift.

**Review.** Mostly inline DOM; normal dilution, hood, and electrophoresis contexts;
minimum aspirating-pipette, label-scale, and P20/P1000 placements.

**Exact SVG ownership.**

- `binary_state/serological_pipette_pack_available.svg`
- `binary_state/serological_pipette_pack_depleted.svg`
- `variable_volume/aspirating_pipette.svg`
- `variable_volume/multichannel_pipette.svg`
- `variable_volume/p1000_micropipette.svg`
- `variable_volume/p10_micropipette.svg`
- `variable_volume/p20_micropipette.svg`
- `variable_volume/repeat_dispenser.svg`
- `variable_volume/serological_pipette.svg`

### `WP-B1`: primary benchtop instruments

**Source and reuse.** Keep each instrument's full state family together. Use the M2
analyzer housing for the cell counter; retain direct detailed Servier geometry for the
incubator, vortex, and water-bath family; and use the controlled repository-authored
compound-microscope adaptation after the direct Servier projection proved visually
inadequate. Use the existing source records or an E2 board for each otherwise absent
source. Heat-block, lightbox, and microwave states share one manufactured housing with
a state-specific opening, lid, or illumination treatment.

**Review.** img; normal bench/cell-counter/microscope contexts; minimum rear-bench
placement and the lightbox/cell-counter state contexts.

**Exact SVG ownership.**

- `binary_state/cell_counter_instrument.svg`
- `binary_state/cell_counter_result.svg`
- `binary_state/heat_block_closed.svg`
- `binary_state/heat_block_open.svg`
- `binary_state/lightbox_off.svg`
- `binary_state/lightbox_on.svg`
- `binary_state/microwave_closed.svg`
- `binary_state/microwave_heating.svg`
- `binary_state/water_bath.svg`
- `binary_state/water_bath_occupied.svg`
- `static/incubator.svg`
- `static/microscope.svg`
- `static/vortex.svg`

### `WP-B2`: plate reader and rocking shaker

**Source and reuse.** The reader needs an E2 board using M2's spectrophotometer-adjacent
source before redraw; its idle/reading states share a single housing, plate opening,
and controls. The rocking shaker retains one platform and base, changing only its
running state treatment; do not treat Servier's agitator as a direct source.

**Review.** img; normal plate-reader/imaging/staining contexts; minimum rear-bench
placements and the reader result-review workspace.

**Exact SVG ownership.**

- `binary_state/plate_reader_idle.svg`
- `binary_state/plate_reader_reading.svg`
- `binary_state/rocking_shaker_idle.svg`
- `binary_state/rocking_shaker_running.svg`

## M11 electrophoresis, safety, overlays, and evidence

### `WP-E1`: electrophoresis physical system

**Source and reuse.** Treat the chamber, cassette, gel, comb, lid, and module as one
interoperable physical system. Use direct Servier gel-electrophoresis sources for the
gel/cassette family, the electrophoresis-chamber-adjacent source for tank and nested
chamber forms, and a bounded board for leads and power supply. Keep each chamber and
cassette state family in one package; the static cassette fragments belong to `WP-O1`
because they only render in named composites.

**Review.** Mixed img/inline DOM; normal electrophoresis bench and SDS-PAGE assembly
contexts; minimum lead, tip, and gel-tool placements plus tank/cassette composite checks.

**Exact SVG ownership.**

- `binary_state/electrophoresis_buffer_dam.svg`
- `binary_state/electrophoresis_buffer_dam_seated.svg`
- `binary_state/electrophoresis_tank_lidded.svg`
- `binary_state/electrophoresis_tank_open.svg`
- `static/gel_comb.svg`
- `binary_state/mini_protean_gel.svg`
- `binary_state/mini_protean_gel_unsealed.svg`
- `binary_state/power_supply_off.svg`
- `binary_state/power_supply_on.svg`
- `multi_state/electrophoresis_inner_chamber_empty.svg`
- `multi_state/electrophoresis_inner_chamber_filled.svg`
- `multi_state/electrophoresis_inner_chamber_leak_checked.svg`
- `multi_state/electrophoresis_inner_chamber_partial.svg`
- `multi_state/electrophoresis_outer_chamber_empty.svg`
- `multi_state/electrophoresis_outer_chamber_filled.svg`
- `multi_state/electrophoresis_outer_chamber_leak_checked.svg`
- `multi_state/electrophoresis_outer_chamber_partial.svg`
- `multi_state/gel_cassette_destained.svg`
- `multi_state/gel_cassette_destaining.svg`
- `multi_state/gel_cassette_empty.svg`
- `multi_state/gel_cassette_separated_unstained.svg`
- `multi_state/gel_cassette_stained.svg`
- `static/electrophoresis_tank_black_lead_connected.svg`
- `static/electrophoresis_tank_module_mounted.svg`
- `static/electrophoresis_tank_red_lead_connected.svg`
- `static/gel_loading_tip_box.svg`
- `static/gel_opening_tool.svg`
- `static/p10_gel_loading_tip.svg`
- `static/p10_gel_loading_tip_box.svg`

### `WP-S1`: safety, containment, and bench support

**Source and reuse.** This package owns the bench/safety objects rather than learner
evidence. It needs boards for the hood surface, biohazard decant pair, and sharps form,
all of which have no direct Servier counterpart. The electrode module shares the
electrophoresis-chamber construction vocabulary but remains here because it is a
bench-safety accessory. Keep all five staining-tray liquid states together using M2's
dyetray-adjacent source.

**Review.** Mixed img/inline DOM; normal hood, staining, cell-counter, and SDS-PAGE
contexts; minimum label-pen, tissue, and decant placements plus hood-surface composite.

**Exact SVG ownership.**

- `binary_state/electrode_module_closed.svg`
- `binary_state/electrode_module_open.svg`
- `binary_state/hood_workspace_surface.svg`
- `binary_state/hood_workspace_surface_clean.svg`
- `multi_state/staining_tray_buffer.svg`
- `multi_state/staining_tray_destain.svg`
- `multi_state/staining_tray_empty.svg`
- `multi_state/staining_tray_stain.svg`
- `multi_state/staining_tray_water.svg`
- `static/biohazard_decant.svg`
- `static/biohazard_decant_bin.svg`
- `static/kimwipe_pad.svg`
- `static/label_pen.svg`
- `static/lens_tissue.svg`
- `static/paper_towel_pad.svg`
- `static/recycle_buffer_funnel.svg`
- `static/sharps_container.svg`

### `WP-O1`: overlays, observation graphics, and feedback art

**Source and reuse.** These assets have no standalone apparatus mandate. The owner
works from the named bases and consumer composites: gel-cassette fragments with the
gel/cassette states in `WP-E1`; lightbox tray and gel-image evidence with `WP-B1`'s
lightbox states; hemocytometer observations with `WP-C2`'s slide and `WP-B1`'s
microscope/cell-counter; plate crystals with `WP-C2`'s plate. `angry_professor` and
the interpretation card remain learner-context art and do not borrow physical-equipment
construction rules beyond legibility.

**Review.** Use each asset's M1 mode in every named base/composite, especially
electrophoresis bench, imaging bench, cell-counter, microscope, and decision-review
workspaces. There is no standalone contact-sheet acceptance for this package.

**Exact SVG ownership.**

- `static/angry_professor.svg`
- `static/calculation_pad.svg`
- `static/cell_counter_manual_live_dead_panel.svg`
- `static/cell_counter_manual_quadrants_panel.svg`
- `static/gel_cassette_bottom_tape.svg`
- `static/gel_cassette_comb_inserted.svg`
- `static/gel_cassette_side_clamps_locked.svg`
- `static/gel_cassette_top_plate_removed.svg`
- `static/gel_cassette_wing_clamps_locked.svg`
- `static/gel_migration_near_bottom.svg`
- `static/gel_migration_not_started.svg`
- `static/gel_migration_overrun.svg`
- `static/gel_migration_running.svg`
- `static/hemocytometer_live_dead_cells_visible.svg`
- `static/hemocytometer_quadrants_counted.svg`
- `static/interpretation_choice_card.svg`
- `static/lightbox_capture_complete.svg`
- `static/lightbox_gel_destained.svg`
- `static/lightbox_gel_destaining.svg`
- `static/lightbox_gel_separated_unstained.svg`
- `static/lightbox_gel_stained.svg`
- `static/lightbox_gel_tray.svg`
- `static/lightbox_image_bands_visible.svg`
- `static/lightbox_image_molecular_weight_scale.svg`
- `static/microscope_field_confluent_70_80.svg`
- `static/microscope_field_rounded_detached.svg`
- `static/well_plate_formazan_crystals.svg`

## Protected/deferred result interfaces

These seven application-owned result interfaces are protected by the existing scope
boundary. They remain byte-preserved and receive no M7--M11 SVG owner. M12 may verify
their reachability without modifying them.

- `static/cell_viability_results_display.svg`
- `static/electrophoresis_endpoint_display.svg`
- `static/gel_image_results_display.svg`
- `static/hemocytometer_observation_display.svg`
- `static/mtt_reader_results_display.svg`
- `static/plate_reader_absorbance_result_panel.svg`
- `static/plate_reader_normalized_viability_panel.svg`

## Coverage validation

The checked source inventory contains 130 retained production SVGs. This matrix assigns
123 to M7--M11 and seven to protected/deferred result interfaces. The MTT empty
state selects the already-owned canonical `microtube` asset; it does
not own a duplicate shell. Before dispatch, run
the following one-time evidence check; it compares path sets, not a permanent asset-count
test:

```sh
find assets/equipment -type f -name '*.svg' -printf '%P\n' | sort > /tmp/on_disk_svg_paths
rg -o '`(?:binary_state|multi_state|static|variable_volume)/[^`]+\.svg`' \
  docs/active_plans/reports/svg_batch_ownership_matrix.md \
  | sed -E 's/.*`([^`]+)`.*/\1/' | sort > /tmp/matrix_svg_paths
diff -u /tmp/on_disk_svg_paths /tmp/matrix_svg_paths
```

The command must have no output. Markdown and ASCII validation follow the repository
documentation gates; this file deliberately makes no visual or asset-count assertion
part of the durable test suite.
