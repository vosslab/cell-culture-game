# WP-C2 plates, slides, racks, and tip boxes

## Scope and visual contract

This M9 package rebuilds the nine source SVGs assigned to `WP-C2` in the
[svg_batch_ownership_matrix.md](svg_batch_ownership_matrix.md). The sources
remain ordinary production SVGs under `assets/equipment/static/`; no object
YAML, generated output, runtime schema, result interface, or source-ledger row
changed in this workstream.

The recognition target is a compact family of shallow labware: a plate reads as
a skirted well array, a slide reads as a recessed counting chamber, a rack owns
its openings and frame, and a tip box reads as an opened lid over a coherent
tip tray. At ordinary size, D04 supplies only physical depth (top planes,
well recesses, lid overlap, and receding faces); D01 removes decorative bands
and arbitrary darkening. At the M3 minimums, silhouette, opening pattern, and
selection affordance take precedence over unreadably fine detail.

All sources retain their authored `viewBox` and `preserveAspectRatio` behavior.
The active equipment-kit convention is the front-left, shallow-elevation view,
upper-left/front light, `#294657` contour/recess, and restrained
`#b9ccd7` / `#e8f0f4` / `#7895a5` face hierarchy from
[equipment_kit/README.md](../../figures/equipment_kit/README.md) and
[equipment_kit/MEASUREMENTS.md](../../figures/equipment_kit/MEASUREMENTS.md).

## Identity and source evidence

The M2 counterpart sweep supplies the direct visual evidence for the two
identity-sensitive forms:

- `96well_pcr_plate.svg` uses the Servier-adjacent `multiwell-plate-3d.svg`
  construction evidence: a shallow top plane, plate rim, and regular recessed
  well array.
- `counter_slide_cartridge.svg` and `hemocytometer_slide.svg` use the
  Servier-adjacent `counting-chamber-3d-1.svg` evidence: slide thickness,
  chamber recesses, and a legible top opening.

Those records are in
[svg_servier_counterpart_sweep.md](svg_servier_counterpart_sweep.md). The
racks, ordinary tip box, and waste container are original fixed-equipment
constructions using their current object contracts and the frozen kit; they do
not claim a new direct-source relationship. No `SOURCES.md` update is needed.

## Implemented source files

| Source | Construction result | Preserved runtime boundary |
| --- | --- | --- |
| `static/96well_pcr_plate.svg` | Added real shallow top and lower skirt planes around the established 8 x 12 well field. | `A1` through `H12`, each `data-subpart-id`, row groups, and plate geometry stay intact. |
| `static/counter_slide_cartridge.svg` | Rebuilt one low cartridge shell, dark slide bay, ten readable slide channels, and a lower count window. | `overlay_root`, `anchor_label`, and `anchor_error` remain exact. |
| `static/dilution_tube_rack.svg` | Built a one-row rack frame with eight real openings and capped clear tubes as rack-owned geometry. | Root ID and the ordinary static asset binding remain intact. |
| `static/heat_block_rack.svg` | Built a compact six-well block and three seated tubes with a true front/right housing split. | Existing composite binding from `heat_block.yaml` remains intact. |
| `static/hemocytometer_slide.svg` | Rebuilt the slide thickness, left chamber, central recessed counting chamber, and right chamber. | `diamond`, `semicircle`, `overlay_root`, liquid clip/bounds, label, and error anchors remain exact. |
| `static/microtube_rack_8.svg` | Rebuilt one two-row rack body with eight dark openings; it does not borrow microtube vessel geometry. | All eight `slot_A1`--`slot_B4` identifiers remain exact. |
| `static/tip_box.svg` | Rebuilt a hinged clear lid, tray, front face, and 12-tip matrix. | `overlay_root`, label anchor, and error anchor remain exact; the structural language is compatible with later electrophoresis boxes without changing them. |
| `static/tube_rack.svg` | Rebuilt a 24-slot oblique rack with rack-owned opening plane and seated tube masses. | Root `x_7`, viewBox, and image binding remain intact. |
| `static/waste_container.svg` | Rebuilt the handled waste carboy as a clear fixed body, cap/handle hardware, and foreground label plane. | Liquid clip, foreground hook, overlay root, and all four anchors remain exact. |

## Validation and render evidence

Each source parsed and normalized successfully to an isolated temporary output
directory with `tools/normalize_svg_v3.py`; the source viewBoxes were not
rewritten. The normalizer also verifies local paint references and rejects
unsupported `<use>` / `<symbol>` dependencies, so repeated geometry is
authored explicitly in each source.

Focused checks completed:

- `tests/test_svg_asset_taxonomy_validator.py`: 18 passed.
- `tests/test_svg_normalizer_clips.py` and `tests/test_svg_normalizer_shadows.py`:
  43 passed.
- `tests/test_object_asset_refs.py`: 2 passed after the shared asset registry
  reached its current, duplicate-free state.
- Fresh standalone `rsvg-convert` images at 640 x 480 were inspected as a
  nine-up contact sheet on a white background. The checked normal/minimum
  scene contexts come from the M3 census: plate focus/hood, cell-counter,
  dilution/heat-block, and microscope/bench contexts.

Real-workspace browser proof is reserved for the
integration build because this workstream is explicitly barred from writing
`generated/` or `dist/`; the retained subpart/anchor contracts identify the
required browser oracles.

## Construction references used

The object construction follows the local SVG-creator route: manufactured
forms are organized as major planes and real negative spaces before repeated
detail; repeated wells and slots are laid out as exact, editable SVG geometry;
and render review judges the normal and minimum scenes rather than an invented
pixel floor. The local passages used were the skill's Robertson
`WORKING WITH VOLUME` route and Mastering SVG `viewBox and viewport in SVG`
route, as directed by the active SVG-creator skill. The M2 sweep above remains
the subject-identity source of truth.
