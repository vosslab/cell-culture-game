# M10 WP-H1 liquid-handling implementation

Date: 2026-08-25

## Visual contract

WP-H1 uses the selected D04 construction language with D01 restraint: a shallow
rear plane, one coherent front silhouette, a dark near contour, and only the
contained disposable tip, cartridge, or glass barrel receives material paint.
Each form remains readable at its normal and minimum scene size without a
material-dependent body color.

The construction pass used the local `How_to_Draw...-2013.md` routes `WORKING
WITH VOLUME` and `ELLIPSE BASICS AND TERMINOLOGY`, and `Mastering_SVG-2018.md`
route `viewBox and viewport in SVG`. The results use named root semantic layers,
a fixed/material/fixed drawing order, literal fallback paint, and the existing
compiled liquid-region boundary.

## Evidence and reconstruction

- P20 and P1000 retain the bounded Eppendorf/Gilson anatomy evidence from the
  [M4 micropipette board](svg_reference_board_micropipette.md). They are
  capacity-specific: P20 stays narrow with a yellow volume collar; P1000 has a
  wider barrel, sleeve, and tip bore. M2 remains `no_servier_source` for both.
- P10 retains direct Servier provenance from
  `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Chemistry/Servier/micropipette.svg`.
  Its controlled redesign keeps the small-capacity slender body and tip-only
  material surface. The direct-source attribution remains in `SOURCES.md`.
- Multichannel retains direct Servier provenance from
  `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Chemistry/Servier/micropipette-multi.svg`.
  The rebuilt source exposes eight aligned dispensing bores as one physical form.
- Repeat dispenser uses the M2 `pipette-pistol.svg` adjacent source for its
  cartridge axis, trigger, and outlet. Its visible material is restricted to the
  disposable cartridge.
- Aspirating and serological pipettes use M2's `pipette-glass.svg` adjacent
  source for the glass shaft, open tip, and graduation-bearing profile. The
  existing serological source already had the required semantic liquid contract;
  its shaft, marks, and ownership stay canonical.
- The serological-pipette pack is intentionally a physical availability state,
  not a material container. Its available/depleted pair shares the same oblique
  carton geometry and only changes the visible loose-pipette contents.

## Clean migration

| Retired source path or paths | Canonical source | Object change |
| --- | --- | --- |
| `binary_state/p20_micropipette_empty.svg`, `binary_state/p20_micropipette_filled.svg` | `variable_volume/p20_micropipette.svg` | P20 now resolves one form and paints `held_material_volume` to its tip at 20 ul. |
| `binary_state/p1000_micropipette_empty.svg`, `binary_state/p1000_micropipette_filled.svg` | `variable_volume/p1000_micropipette.svg` | P1000 now resolves one form and paints its wider tip at 1000 ul. |
| `static/p10_micropipette_empty.svg` | `variable_volume/p10_micropipette.svg` | P10 now paints its tip at 10 ul. |
| `binary_state/repeat_dispenser_empty.svg`, `binary_state/repeat_dispenser_loaded.svg` | `variable_volume/repeat_dispenser.svg` | Dispenser now paints the disposable cartridge at 120 ul; the setpoint and tip fields remain independent. |
| `static/aspirating_pipette.svg` | `variable_volume/aspirating_pipette.svg` | Aspirator now paints only its glass barrel at 10 ml. |
| `static/multichannel_pipette.svg` | `variable_volume/multichannel_pipette.svg` | Multichannel now paints its eight aligned bores at 300 ul per channel. |

No aliases or compatibility assets remain for migrated forms. The pack remains
binary because depletion is a stock/physical state, not held material. The
existing `variable_volume/serological_pipette.svg` remains the canonical loose
pipette material form at 25 ml.

## Validation record

- Material normalizer accepts each newly authored variable-volume source.
- Focused semantic-layer and object visual-state tests pass (83 tests).
- `pipeline/gen_svg_manifest.py`, `pipeline/gen_liquid_regions.py`, and the
  production build complete on the integrated tree.
- The real Chromium `test_liquid_render.spec.ts` fleet passes 3 tests. It now
  exercises each migrated source at empty, partial, and full levels in three
  material colors (`#076dad`, `#c2015a`, `#5a8f20`), checks the compiled
  gravity-region transform and stationary clip, and captures the browser matrix.

## Visual reveal correction

Independent review caught that the first variable-tool pass satisfied the
material-region transform assertions while opaque fixed-front tip, barrel, and
cartridge fills hid the painted contents. The correction keeps liquid in its
semantic material layers and makes only the physical viewing regions transparent:

- P10, P20, and P1000 retain outlined disposable tips with a pale translucent
  glass face, so the colored fill reads through the correct tip only.
- The repeat dispenser retains its cartridge rim, graduations, and bright
  reflection, but its cartridge face has no opaque fixed fill.
- Aspirating-pipette barrel and multichannel dispensing bank retain the front
  outline, graduations/bores, and highlight while their viewing faces are
  translucent.

The re-rendered production matrices visibly distinguish empty, partial, and
full blue, magenta, and green contents. The shared fleet now also includes the
M7 P200 exemplar, preventing the approved reference form from dropping out of
the generic compiled-material browser oracle.
