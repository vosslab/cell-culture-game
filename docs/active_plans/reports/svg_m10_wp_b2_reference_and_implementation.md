# M10 WP-B2 reader and rocker

## Scope and decision

This report records the bounded M10 `WP-B2` rebuild of the plate-reader and rocking-shaker
state families. It follows the frozen [equipment kit](../../figures/equipment_kit/README.md),
the M2 [counterpart sweep](svg_servier_counterpart_sweep.md), and the `WP-B2` ownership row in
[svg_batch_ownership_matrix.md](svg_batch_ownership_matrix.md). It does not alter object YAML,
runtime selection, result panels, generated output, or `assets/equipment/SOURCES.md`.

The edited, img-safe sources are:

- [plate_reader_idle.svg](../../../assets/equipment/binary_state/plate_reader_idle.svg)
- [plate_reader_reading.svg](../../../assets/equipment/binary_state/plate_reader_reading.svg)
- [rocking_shaker_idle.svg](../../../assets/equipment/binary_state/rocking_shaker_idle.svg)
- [rocking_shaker_running.svg](../../../assets/equipment/binary_state/rocking_shaker_running.svg)

## Plate-reader reference board

### Evidence role

The reader is a generic microplate absorbance instrument, not a tracing or product replica.
The M2 source disposition remains `servier_adjacent`: the local
`Lab_apparatus/Servier/spectrophotometer.svg` is visual-language guidance for a compact housing,
recessed opening, and compact controls, not plate-reader provenance. Its counterpart entry is in
[svg_servier_counterpart_sweep.md](svg_servier_counterpart_sweep.md#servier-adjacent-construction-references).

Physical structure is bounded by these primary manufacturer references, accessed 2026-08-25:

- [Agilent BioTek 800 TS Absorbance Reader](https://www.agilent.com/en/product/clinical-microplate-instrumentation/clinical-microplate-readers/clinical-absorbance-microplate-readers/biotek-800-ts-absorbance-reader-1623178)
  establishes a benchtop reader for 96-well plates, a local color touch screen, controls, and
  absorbance wavelength range.
- [SpectraMax M3/M4/M5/M5e user guide](https://www.moleculardevices.com/sites/default/files/en/assets/user-guide/br/spectramax-m3m5e-userguide-0112-0015l.pdf)
  establishes a plate drawer that moves into a dark plate chamber, uses a central plate window,
  and closes for a read.

This evidence supports a broad, low housing with a shallow elevated top, a plate-sized recessed
drawer/chamber, a front control/display plane, and a stable lower footprint. It does not support
copied branding, product-specific button arrangement, screen wording, or a particular optical
module. Those details are intentionally omitted.

### Recognition and construction

The recognition target at the 87 by 50 px normal reader-workspace render is a plate reader rather
than a centrifuge, incubator, or result card: a wide low instrument, a clearly dark trapezoidal
plate chamber, a pale plate window inside it, and a distinct low front control face provide that
read. The source uses the M8 front-left shallow camera and upper-left light. Three housing planes
make the shell; the darkest fixed value names only the optical/drawer recess and display inset.

Both states retain exact `viewBox="0 0 560 320"`,
`preserveAspectRatio="xMidYMid meet"`, housing, plate opening, controls, base, IDs, `overlay_root`,
and the result-panel anchors. `reading` changes only the contained optical surface, screen value,
and status control. It remains a whole-asset static SVG selected by `plate_reader.yaml`; no result
panel or object contract is replicated in the artwork.

### Real placement evidence

The M3 census gives the same plate-reader asset family these actual placements:

| Context | Screen size evidence | Review use |
| --- | --- | --- |
| `mtt_solubilization_readout_bench_workspace/rear_right_plate_reader` | 523.26 by 299.00 px at 1920; 102.47 by 58.55 px at 376 | Rear-bench normal/minimum check |
| `mtt_solubilization_readout_plate_reader_workspace/center_plate_reader` | 523.26 by 299.00 px at 1920; 87.21 by 49.83 px at 320 | Focused reader task view |
| `mtt_solubilization_readout_result_review/rear_center_plate_reader` | 687.50 by 392.86 px at 1920; 114.58 by 65.48 px at 320 | Result-panel compatibility check |

At the focused 523 px render, the 7-unit outer reader contour converts to 6.54 CSS px and its
3-unit identity edges convert to 2.80 CSS px. At the literal 87 px narrow render, they reduce to
1.09 and 0.47 CSS px, so the chamber silhouette and face separation, rather than the tiny controls,
carry recognition as required by the kit.

## Rocking-shaker reference board

### Evidence role

The rocking shaker has no local Servier mechanism source. M2 records the bounded local search for
`rocking shaker orbital shaker`, and explicitly excludes `agitator.svg` as a rocking-shaker
adoption in [svg_servier_counterpart_sweep.md](svg_servier_counterpart_sweep.md#no-servier-source-in-the-bounded-local-search).
The existing DBCLS provenance remains untouched in `assets/equipment/SOURCES.md`; this drawing
does not newly reuse external geometry.

The physical reference is the [Thermo Scientific Digital Platform Rocker](https://www.thermofisher.com/order/catalog/product/88882014),
accessed 2026-08-25. It establishes gentle rocking for staining/destaining gels, a tray platform,
digital speed/time control, and adjustable rocking angle. The generic reconstruction therefore
shows a broad rigid tray above a centered pivot and a short, stable control-bearing base. It omits
brand marks, exact display text, accessories, motor details, and claimed operating angle.

### State construction

Both shaker states retain exact `viewBox="0 0 348 213.5"`,
`preserveAspectRatio="xMidYMid meet"`, base, feet, control face, pivot, platform geometry,
IDs, anchors, and `overlay_root`. In `rocking_shaker_running.svg` the same platform rotates eight
degrees around the visible pivot, while a small pair of amber arcs communicates the bounded rocking
sweep. The active green control is a state cue, not a decorative light. This is physical motion
about a mechanism; it is not a translated tray, detached motion glyph, or a vortex/agitator
substitute.

The base and pivot begin behind the platform. The tray's pale top, front lip, and darker right side
show the same D04 physical overlap with D01 restraint used by the M8 centrifuge. The upper-left
highlight and dark pivot/recess remain subordinate to the tray silhouette.

### Real placement evidence

The M3 census gives these normal and small shaker uses:

| Context | Screen size evidence | Review use |
| --- | --- | --- |
| `imaging_bench/rear_center_rocking_shaker` | 256.67 by 157.47 px at 1920; 80.34 by 49.29 px at 601 | Rear-bench minimum check |
| `sdspage_destain_gel_setup_workspace/center_rocking_shaker` | 256.67 by 157.47 px at 1920; 57.75 by 35.43 px at 432 | Destaining task view |
| `staining_bench/center_rocking_shaker` | 256.67 by 157.47 px at 1920; 57.75 by 35.43 px at 432 | Staining task view |

At the 256.67 px normal width, the 6-unit outer contour converts to 4.43 CSS px and the 3-unit
control/platform detail to 2.21 CSS px. At the 57.75 px narrow render, the same values reduce to
1.00 and 0.50 CSS px; platform angle, tray lip, pivot relationship, and state color therefore carry
the running distinction rather than unreadable control detail.

## Construction sources and validation

The drawing method used the local `svg-creator-expert` sources:

- `How_to_Draw_Drawing_and_Sketching_Objects_and_Environments_from_Your_Imagination-2013.md`,
  `Working With Volume` and `Planning Before Perspective`: establish simple massing before shallow
  projected detail.
- `Mastering_SVG-2018.md`, `viewBox and viewport in SVG`: maintains a stable responsive coordinate
  system for each state family.
- `A_Handbook_of_Biological_Illustration-1988.md`, `CLARITY` and `SHADING CONVENTION`: limits detail
  to identity-bearing features and applies the upper-left light convention.

Run the package evidence from the repository root:

```bash
source source_me.sh && python3 tools/normalize_svg_v3.py --shadow-dry-run -i assets/equipment/binary_state/plate_reader_idle.svg -i assets/equipment/binary_state/plate_reader_reading.svg -i assets/equipment/binary_state/rocking_shaker_idle.svg -i assets/equipment/binary_state/rocking_shaker_running.svg
source source_me.sh && python3 -m pytest tests/test_svg_asset_taxonomy_validator.py tests/test_object_asset_refs.py -q
npm run build
```

The normalizer command is deliberately non-mutating: ordinary normalizer output would create a
`*.normalized.svg` sibling beside each source, which is not a tracked asset and can poison a later
asset-tree build. The dry run reports the floor-shadow boundary without writing a sibling. The
authored family viewBoxes deliberately remain the object-YAML/result-panel stable frame; do not
replace them with a tight diagnostic crop.

Current package evidence is clean: `npm run build` completed after the four source changes; the
focused taxonomy/object checks passed 20 tests; Chromium standalone renders were inspected; and
the MTT reader Playwright journey passed with both idle and reading assets served as static images.
The matching rocking-shaker subpath/img check passed and fetched the static asset with HTTP 200.
A broader external Firefox retry remains an environment-sensitive follow-up rather than a source
failure verdict; its result must be recorded separately from the Chromium source/build evidence.
