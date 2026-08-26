# M11 WP-O1 overlays and observations

## Scope and contract

WP-O1 owns only the 27 static overlays, observation graphics, and learner-context
assets listed in the [batch matrix](svg_batch_ownership_matrix.md). It does not
change result interfaces, object YAML, runtime code, source attribution, or base
equipment. Every source preserves its registered viewBox and transparent composite
frame. The implementation follows the M8 kit only where a physical base needs a
shared contour, palette, or front-left light direction; microscopy, gel evidence,
and learner cards stay evidence graphics rather than pretend apparatus.

The construction references were the local SVG skill stack: *Mastering SVG*,
`viewBox and viewport in SVG`, for the stable full-frame overlay coordinate system,
and *A Handbook of Biological Illustration*, `CLARITY`, for evidence that exposes
only the observable distinction at normal scene size. The gel overlays are compared
to the WP-E1 rebuilt cassette; the lightbox overlays use the WP-B1 display plane;
hemocytometer evidence uses the WP-C2 slide grid; crystals use the WP-C2 96-well
coordinates.

## Implemented registrations

| Sources | Disposition and registered composite evidence |
| --- | --- |
| `gel_cassette_bottom_tape.svg`, `gel_cassette_comb_inserted.svg`, `gel_cassette_side_clamps_locked.svg`, `gel_cassette_top_plate_removed.svg`, `gel_cassette_wing_clamps_locked.svg` | Rebuilt as transparent `214 x 308` fragments over the WP-E1 cassette. Tape follows the lower plate, comb aligns to all ten lane wells, clamps remain outside the cassette cavity, and the removed plate is a right-receding translucent physical plate. |
| `gel_migration_not_started.svg`, `gel_migration_running.svg`, `gel_migration_near_bottom.svg`, `gel_migration_overrun.svg` | Rebuilt as transparent `214 x 308` evidence layers. The old opaque mini-cassette backgrounds were removed so the WP-E1 base stays visible. Dye fronts now occupy the stable gel cavity and communicate start, progress, stop-zone, and overrun without prose. |
| `lightbox_gel_tray.svg`, `lightbox_gel_separated_unstained.svg`, `lightbox_gel_stained.svg`, `lightbox_gel_destaining.svg`, `lightbox_gel_destained.svg`, `lightbox_capture_complete.svg`, `lightbox_image_bands_visible.svg`, `lightbox_image_molecular_weight_scale.svg` | Rebuilt in the unchanged `160 x 120` frame against the sloped WP-B1 lightbox display. Tray/gel layers follow one receding plane; capture, bands, and scale are separate transparent evidence states. |
| `cell_counter_manual_live_dead_panel.svg`, `cell_counter_manual_quadrants_panel.svg` | Preserved `372 x 213` monitor registration. Semantic groups separate viable/nonviable cells and counted grid evidence while leaving the result display and DOM numeric overlays visible below. |
| `hemocytometer_live_dead_cells_visible.svg`, `hemocytometer_quadrants_counted.svg` | Preserved `400 x 220` and registered the visible cells precisely inside the WP-C2 slide chamber. The counted state adds only the chamber grid and count marks. |
| `microscope_field_confluent_70_80.svg`, `microscope_field_rounded_detached.svg` | Rebuilt as normalizer-compatible `283.843 x 489.184` observation layers. Each retains the microscope field frame and uses adherent versus rounded cell morphology as the only evidence distinction. |
| `well_plate_formazan_crystals.svg` | Rebuilt as a normalizer-compatible `393.3275 x 278.5243` overlay with crystal clusters registered to WP-C2 well centers. It has no plate body, so the live material surface remains visible. |
| `angry_professor.svg`, `calculation_pad.svg`, `interpretation_choice_card.svg` | Retouched learner-context art in their original frames. These remain language-neutral visual cues: instructor expression, lined writing surface, and selected choice geometry; no physical-equipment provenance claim is made. |

## Verification

- `python3 tools/normalize_svg_v3.py -o /private/tmp/svg_m11_wp_o1_normalized -i <all 27 owned sources>` passes for every owned source. The two microscopy fields and crystal overlay were changed from unsupported `use` instances to explicit geometry, so the normalizer now accepts them.
- `npm run build` passes after the source edits and recompiles the manifest and real composite registrations.
- `git diff --check -- assets/equipment/static docs/active_plans/reports/svg_m11_wp_o1_reference_and_implementation.md` passes.

The M12 production-browser pass remains responsible for the final normal/minimum
scene screenshots and interaction-state coverage across electrophoresis, imaging,
cell-counter, microscope, plate, and learner-review workspaces.
