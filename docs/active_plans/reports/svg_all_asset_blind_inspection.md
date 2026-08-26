# All-asset blind SVG image inspection

Date: 2026-08-26.

## Purpose

This is one-time implementation evidence collected before renewed human review. It is not a permanent
visual-regression test, fixture corpus, alternate gallery, or acceptance decision.

## Superseding human review

Human review rejected several assets after this blind pass. The rendered corpus check missed logical and
ownership defects that were obvious with filenames, state pairs, and repository history available:

- lead connectors overlapped their cable/plug geometry instead of showing a credible connection;
- several instruments used arbitrary skewed projections;
- the MTT empty state duplicated the microtube;
- the rebuild displaced the established detailed T75 flask and Servier-derived microtube.

Those findings supersede the `PASS` below for acceptance purposes. The affected artwork was recovered from
the repository's frozen final-equipment contact sheet, and the redundant MTT-empty SVG was removed so the
empty state now selects the canonical microtube. Later ownership repairs also removed the full-cassette
`gel_comb_in_cassette` composite and the material-specific MTT vial. The cassette now solely owns its
inserted comb, and runtime material rendering paints MTT inside `microtube`. A second-pass
ownership review then deleted four standalone binary lead cards and added two tank-coordinate
connection overlays. The current authored corpus therefore contains 130 SVGs, not the 135
inspected in this historical run. The opaque `Q`
codes and conclusions below describe the pre-recovery bytes only.

The authored tree inspected at that time under `assets/equipment/` contained 135 SVG files. Each file was rendered on white
at 600 px and 180 px with its aspect ratio preserved, assigned a randomized opaque code from `Q001` through
`Q135`, and placed on one of 15 contact sheets. The inspector received only the rendered pixels. It did not
receive filenames, expected identities, SVG/XML, repository context, or the private mapping.

The temporary mapping, individual PNGs, contact sheets, and evaluator reports lived under `/private/tmp` and
were not added to the repository.

## Complete-corpus result

- 135 of 135 pre-recovery source SVGs rendered at both sizes.
- The mapping matched that pre-recovery source tree exactly, with no missing or extra path.
- The first independent inspector accounted for `Q001` through `Q135` exactly once, with no missing or
  duplicate code.
- No cropped object, detached shadow, missing chunk, malformed render, or cubist/faceted low-poly object was
  observed.
- The inspector returned PASS and separated 21 low-confidence or context-dependent items from hard failures.
  It reported no hard failure.

The low-confidence group mapped principally to electrophoresis overlays and subcomponents, blank chamber
states, small disposable accessories, and depleted packaging. Those assets need their owning object or scene
to communicate full semantics and were not judged as failed standalone instruments.

## Blind identity adjudication

Mapping the first report exposed several incorrect first-noun guesses despite the clean geometry. A second
fresh inspector therefore reviewed 33 ambiguous raster pairs. It received neither the mapping nor the first
report and accounted for all 33 codes.

The second pass correctly identified the compound microscope at 99 percent confidence, all three open
microtube or vial states at 97-98 percent, the Falcon-style conical tube at 98 percent, and the clean hood
surface as a biosafety cabinet at 86 percent. It identified the empty water bath as a plausible shaking bath
and the occupied state as an incubator shaker or shaking water bath. This resolves the first inspector's
spurious liquid-handler and dispenser calls without changing source art.

Ten codes remained genuinely context-dependent in the second pass:

| Code   | Current source                                       | Why standalone identity is limited                                |
| ------ | ---------------------------------------------------- | ----------------------------------------------------------------- |
| `Q031` | `binary_state/lightbox_off.svg`                      | Unlit instrument window lacks the illuminated gel context.        |
| `Q034` | `binary_state/gel_comb.svg`                          | Long isolated comb reads as a generic rack without its cassette.  |
| `Q039` | `binary_state/mini_protean_gel_unsealed.svg`         | State cue depends on the gel-apparatus workflow.                  |
| `Q046` | `static/lightbox_gel_destaining.svg`                 | Sparse observation overlay is not a standalone object.            |
| `Q048` | `binary_state/lightbox_on.svg`                       | Lit instrument window remains a generic benchtop enclosure alone. |
| `Q061` | `static/lightbox_gel_destained.svg`                  | Sparse observation overlay is not a standalone object.            |
| `Q064` | `binary_state/cell_counter_result.svg`               | Recognizable only as an analytical instrument.                    |
| `Q069` | `binary_state/electrophoresis_buffer_dam_seated.svg` | Small apparatus subcomponent needs its tank context.              |
| `Q077` | `binary_state/electrophoresis_buffer_dam.svg`        | Small apparatus subcomponent needs its tank context.              |
| `Q089` | `static/electrophoresis_tank_module_mounted.svg`     | Reads as a generic dual-well cartridge alone.                     |

Two further forms were plausible at the correct family level but retained category uncertainty: the filled
reagent reservoir (`Q008`) and the empty water bath (`Q100`).

## Human-review watchlist

The following coherent, non-cubist forms received a persistent but wrong or over-broad first noun. They are
not automated failures; they are the most useful targets for a human recognizability decision:

| Code   | Current source                                       | Blind reading                                                     |
| ------ | ---------------------------------------------------- | ----------------------------------------------------------------- |
| `Q018` | `static/gel_opening_tool.svg`                        | USB-style tool rather than cassette-opening lever.                |
| `Q027` | `binary_state/centrifuge_running.svg`                | Vortex mixer rather than closed running centrifuge.               |
| `Q036` | `binary_state/rocking_shaker_running.svg`            | Laboratory balance rather than rocking platform.                  |
| `Q114` | `binary_state/rocking_shaker_idle.svg`               | Laboratory balance rather than rocking platform.                  |
| `Q057` | `binary_state/heat_block_closed.svg`                 | Small printer rather than closed heating block or thermal cycler. |
| `Q075` | `binary_state/plate_reader_reading.svg`              | Centrifuge rather than microplate reader.                         |
| `Q111` | `binary_state/plate_reader_idle.svg`                 | Centrifuge rather than microplate reader.                         |
| `Q117` | `binary_state/serological_pipette_pack_depleted.svg` | Wipe dispenser rather than empty pipette pack.                    |
| `Q130` | `static/lens_tissue.svg`                             | Gel tray rather than folded lens tissue.                          |

The water-bath pair is retained deliberately. `water_bath.svg` and `water_bath_occupied.svg` are the direct
normalized Servier `bath-empty.svg` and `bath_filled.svg` sources selected by the user. Both blind reviewers
found the forms physically coherent and non-cubist; the second reviewer placed them in the shaking-bath or
incubator-shaker family.

No SVG source was changed solely because an image model supplied a different noun. Human review did cause
the bounded recovery described above because context exposed defects that the blind inspection missed.
Inspect the complete current library at `docs/figures/equipment_kit/review.html`.

This source-raster inspection does not satisfy the plan's exhaustive
shipping-render-mode requirement. The gallery uses `<img>` elements and does
not exercise every DOM-required asset through the built inline-DOM path.
