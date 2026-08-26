# M9 WP-C2 visual evaluator findings

## Replacement-wave addendum (2026-08-26)

The approval below is historical D01-D05 evidence. The current repair wave
reworked the plate, slide, rack, tip-box, and waste-container forms around
rounded rims, actual cavities, seated repeated parts, and coherent shallow
walls rather than faceted icon planes. The exact Servier pipette-box projection
was rejected as visually inadequate; the loading-tip and general tip boxes are
controlled repository adaptations with adjacent-source evidence. Package render
review, independent cross-package review, and current M12 full-consumer
evidence are complete; retained compact captures are historical one-time proof.

## Decision

**APPROVED.** The nine WP-C2 sources form a coherent, restrained family of shallow
labware. At normal task sizes each names a physical object, its functional opening
or recess, and its repeated-part pattern. At literal M3 minima, the sources retain
their intended silhouettes without trying to preserve sub-pixel anatomy through
extra dark bands or heavier contours.

This is a fresh visual evaluation of the sources as rendered on 2026-08-25. It is
not a replacement for the implementation worker's normalizer, taxonomy, or
runtime-contract checks.

## Evidence inspected

- The frozen [equipment-kit README](../../figures/equipment_kit/README.md) and
  [MEASUREMENTS.md](../../figures/equipment_kit/MEASUREMENTS.md), including the
  selected D04 construction logic with D01 restraint.
- The WP-C2 [reference and implementation report](svg_m9_wp_c2_reference_and_implementation.md).
- The M1 [inventory](svg_visual_quality_inventory.md), M2
  [counterpart sweep](svg_servier_counterpart_sweep.md), and M3
  [size and flatness census](svg_visual_size_flatness_census.md).
- Fresh `rsvg-convert` source renders of all nine SVGs at 640 px width and at the
  census literal-minimum widths. The minimum widths ranged from 13 px for the
  hemocytometer slide to 143 px for the foreground plate.
- The shared built `scene_viewer.html` over local HTTP in Chromium at 1280 by 800:
  `plate_focus_hood`, `heat_block_bench`, and `cell_counter_basic`. The first
  capture attempt crossed a concurrent build update; a second cell-counter capture
  completed after the viewer ready marker and found seven scene placements.

## Observed findings

| Subgroup | Sources | Observed result | Call |
| --- | --- | --- | --- |
| Plate and counter cartridge | `96well_pcr_plate.svg`, `counter_slide_cartridge.svg` | The plate is immediately a skirted 8 by 12 well array. The orientation notch, raised rim, and lower skirt establish a real shallow body. The cartridge reads as a compact instrument cassette: its ten vertical slide channels sit in a dark bay, not on a decorative stripe. | APPROVED |
| Tubes and racks | `dilution_tube_rack.svg`, `heat_block_rack.svg`, `microtube_rack_8.svg`, `tube_rack.svg` | Each rack owns a distinct opening plane and front/receding faces. Tubes enter real openings; they do not float as a row of unrelated cylinders. The small dilution rack remains calm because eight tube bodies are identical and the dark opening line is a physical seat. The larger two-row and oblique racks retain readable grouping without a repeated-rim texture. | APPROVED |
| Slide and tip box | `hemocytometer_slide.svg`, `tip_box.svg` | The slide has three functional regions: side chambers, a deeper central counting chamber, and a right chamber. The tip box reads as an opened clear lid over a tray of tips; its pale lid grid is subordinate to the tray rather than a dense stripe field. At their M3 minima (about 13 px and 27 px wide), internal chamber/tip anatomy intentionally falls below the visual floor and the compact silhouettes remain. | APPROVED |
| Waste container | `waste_container.svg` | The body, cap/handle hardware, foreground label plane, and biohazard mark produce a recognizable waste carboy. The handle is a functional overlap, and the red mark carries identity without adding unrelated dark values. | APPROVED |

## Consumer-context findings

- **Plate focus/hood:** The production viewer shows the plate as the dominant
  foreground teaching object. Its pale top plane separates from the warm bench,
  while every well remains a physical recess rather than a flat polka-dot field.
  The upper rim and lower skirt give depth without competing with the well task.
- **Heat-block bench:** The rack language stays coherent beside the closed heat
  block, microtube rack, and tip boxes. At bench scale, repeated tubes and tips
  read as stored laboratory parts rather than high-frequency noise. The compact
  heat-block item retains its block-and-seated-tube identity.
- **Cell-counter bench:** The slide cartridge is recognizable at the rear-shelf
  scale as a dark-bay cartridge, while the larger microtube rack and tip box retain
  distinct silhouettes. The hemocytometer is deliberately small in this overview;
  its detailed central grid belongs to the microscope/counting scenes, not the
  cell-counter overview. No contrast or family-coherence failure was observed.

## Judgment against the kit

The sources apply D04 only to real structure: plate skirt, cartridge bay, rack
openings, slide chamber, lid overlap, receding rack faces, and waste-container
hardware. They use D01 restraint by leaving broad faces pale and by avoiding
gratuitous repeated ellipses, nested rims, and dark horizontal bands. The shared
`#294657` contour/recess language and pale-blue mechanical faces make the group
cohere with the M7 kit without forcing every object into the same projection.

The principal low-size result is intentional: source-specific detail becomes
unreadable at the literal minimum, but no source adds visual noise to counter that
fact. This matches the measured kit rule that silhouette, face separation, and the
scene selection treatment win below the normal detail floor.

## Advisory follow-up

- Keep the dedicated microscope/counting scene review in the final M12 browser
  integration gate. It is the appropriate place to verify the hemocytometer's
  chamber detail after material-state and interaction overlays are present; this
  overview-level review does not ask a 13 px placement to carry that instruction.
- Retain the source-level normalizer and structural checks recorded by the WP-C2
  worker. This visual approval has not rerun them and makes no claim about
  concurrent whole-tree failures outside this package.
