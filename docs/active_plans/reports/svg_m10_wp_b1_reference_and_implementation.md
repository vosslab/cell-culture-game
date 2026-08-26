# M10 WP-B1 primary benchtop instruments

## Scope

This execution record owns only the thirteen sources assigned to `WP-B1` in
[the batch matrix](svg_batch_ownership_matrix.md#wp-b1-primary-benchtop-instruments):
the two cell-counter forms, heat-block, lightbox, microwave, and water-bath
state pairs, plus the incubator, microscope, and vortex. It does not change a
result interface, object contract, runtime schema, generated artifact, or
source-attribution ledger.

## Identity and source boundary

| Family               | Identity evidence used                                                                                                  | Implementation decision                                                                                                                                                                                                                                             |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cell counter         | M2's bounded `hba1canalyzer.svg` adjacent source: analyzer housing, recessed display, and front-panel stack             | A repository-authored generic counter; the source guides housing construction only, not direct provenance. The acquisition and result forms keep one analyzer cabinet and change only the display/result hardware.                                                  |
| Heat block           | Existing DBCLS thermal-cycler records in `SOURCES.md`                                                                   | One shallow three-plane heated-block housing; closed state has the closed deck/lid and open state exposes a rear-hinged lid, true deck recess, and seated tubes.                                                                                                    |
| Lightbox             | M2 records no local Servier counterpart for gel transillumination                                                       | One image-instrument housing with a true recessed tray. The powered form changes only the tray illumination and control indication. The separately owned gel/tray/result overlays remain untouched.                                                                 |
| Microwave            | M2 records no local Servier counterpart for laboratory microwave heating                                                | One microwave shell and true window cavity; heating adds only an illuminated cavity and a physically contained rotating vessel.                                                                                                                                     |
| Water bath           | Direct detailed Servier `bath-empty.svg` and `bath_filled.svg` records                                                  | The normalized source geometry is retained; only runtime anchors and the stable state frame are adapted. The occupied form changes only its interior water surface and tubes seated in that bath.                                                                   |
| Incubator and vortex | Direct detailed Servier `incubator.svg` and `agitator.svg` records                                                      | The normalized source geometry is retained with the runtime frame and anchors. The forms preserve the identifiable cabinet and vortex-cup mechanisms.                                                                                                               |
| Microscope           | Direct Servier `microscope.svg` was reviewed as a historical source, then rejected visually as an inadequate projection | A controlled repository-authored compound-microscope adaptation replaces the direct projection. It preserves the runtime frame, anchors, and semantic component IDs while using physically legible binocular, objective, stage, condenser, arm, and base relations. |

`lightbox_*` and `microwave_*` remain explicitly no-local-Servier families;
the M2 sweep documents the bounded search terms. No source record was claimed
or altered for them. The existing `cell_counter_instrument.svg` ledger row
continues to identify it as repository-authored rather than elevating an
adjacent analyzer reference into direct provenance.

### Bounded physical boards for no-local-source identities

| Family    | Bounded primary reference                                                                                                                                                | Retained generic structure                                                                                                                                                                                                              |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lightbox  | [E-Gel Imager UV Light Base user guide](https://documents.thermofisher.com/TFS-Assets/LSG/manuals/egel_imager_man.pdf), accessed 2026-08-25                              | A top glass plate within a bordered opening and a power switch on the front/right. The art uses a generic low, shallow instrument and does not copy its labels, callouts, or product-specific housing.                                  |
| Microwave | [Panasonic microwave component manual](https://www.help.na.panasonic.com/wp-content/uploads/2023/02/NNSA615_NNSA616_NNSA620_F00038M94SP_ENG_FR.pdf), accessed 2026-08-25 | A cabinet enclosing a door/windowed cavity, interior tray, and a distinct right-side control panel. The heating state makes the cavity lamp and contained vessel visible; it does not claim microwave operation while the door is open. |

The lightbox guide names the glass plate, bounded top opening, and power switch;
the microwave manual depicts the cavity, glass tray, roller ring, door lock, and
right-side controls. These are class-defining physical relationships only. No
manufacturer artwork, branding, text, or interface arrangement was copied.

## Construction and state continuity

The original M10 pass used the now-rejected D04-with-D01 candidate direction.
The current assets preserve only its durable runtime continuity requirements;
their realistic construction instead uses physically named shells, openings,
occlusions, transparent faces, and functional overlaps. No SVG contains
learner prose or a detached floor shadow.

- Both cell-counter files retain `viewBox="0 0 372 213"`, the stable
  `overlay_root`, and the exact label/error anchors. Their external housing,
  front-panel placement, controls, camera, and feet are identical.
- Both water-bath files retain `viewBox="0 0 296 290"`, the stable overlay
  root, and exact label/error anchors. The water surface and seated tubes are
  behind the unchanged near rim.
- The heat-block, lightbox, and microwave pairs retain their original viewBox
  dimensions and safe frame. State art is limited to the physical opening,
  illumination, or contained heating/bath hardware.
- Incubator, microscope, and vortex retain their original viewBoxes,
  `overlay_root`, and exact anchors. The microscope adaptation additionally
  preserves its established stable semantic component IDs.

## Validation and render evidence

| Check                               | Result                                                                                                                                                                                         |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| XML parse for all thirteen SVGs     | Pass (`xmllint --noout`)                                                                                                                                                                       |
| Normalizer to temporary output      | Pass for all thirteen sources; source viewBoxes stay authored and untouched                                                                                                                    |
| Object/YAML and SVG taxonomy checks | Pass: `20 passed` (`tests/test_svg_asset_taxonomy_validator.py`, `tests/test_object_asset_refs.py`)                                                                                            |
| Production build at capture         | Pass: `npm run build`; then-current 135 SVG entries, 57 emitted scenes                                                                                                                         |
| Standalone render inspection        | Pass: Librsvg renders of result counter, open heat block, lightbox on, heating microwave, occupied bath, incubator, microscope, and vortex; reviewed at their intrinsic delivery aspect ratios |
| HTTP-served scene inspection        | Pass at 1920x1080: `bench_basic`, `cell_counter_basic`, and `microscope_basic` each rendered populated with 100% placement yield, 0 render errors, and 0 overlap pairs                         |

The current M3 census establishes the literal small-context scale facts for
this package: heat block reaches `30.32 x 22.74` CSS px, lightbox reaches
`80.34 x 60.26`, microwave reaches `72.19 x 47.89`, vortex reaches
`16.95 x 20.18`, and the microscope's compact hood placement reaches
`33.36 x 57.49`. The implementation keeps those cases silhouette-first and
does not force unsupported micro-detail below the M8 normal-size stroke floor.

The production-shaped renderer was rebuilt and inspected for all three named
contexts. A later concurrent build cleanup removed `dist/` before the compact
viewport repeat could launch; this is a transient evidence gap, not an SVG or
contract failure. The next M10 integration browser run should capture the
same three contexts at their M3 minimum layouts after the shared build is
stable.
