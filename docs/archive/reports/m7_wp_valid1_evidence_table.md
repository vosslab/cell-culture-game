# M7 WP-VALID1 layered-review evidence table

Closeout evidence for the compile-time layout-engine plan
(`partitioned-shimmying-dragonfly`), milestone M7 / work package WP-VALID1.
This report fills the required scene-by-scene evidence table and records the
layered-review outcome (typed diagnostics, bbox-stats regression signal, AI
visual-polish review, and human-review routing).

- Date: 2026-06-08
- Viewport: 1920x1080 (exact 16:9); PNGs clipped to the `#scene-root` content bbox
- Layout source: `generated/precomputed_layout.ts` (compile-time, served in the browser
  inside a 16:9 letterbox; the runtime engine is retired from the production path)
- Before evidence: `test-results/m7_before_baseline/` plus
  `docs/active_plans/reports/m7_layout_before_baseline_gallery.md`
- After evidence: `test-results/m7_after/` (this report)
- Engine diagnostics source: `tests/e2e_layout_diagnostics_baseline.mjs` ->
  `docs/active_plans/reports/layout_diagnostics_baseline.md`
- AI review: `docs/active_plans/reports/m7_ai_polish_review.json`

## Method notes

Two distinct measurement surfaces are reported, and they do not always agree:

- Engine diagnostics (authoritative): the typed severity-graded diagnostics the
  layout engine itself emits over `generated/scenes.ts` at 16:9. These are the build
  truth. None of the eight scenes emits any Error-severity code; the only residuals are
  Warning/structural codes (`label_row_staggered`, `item_escapes_zone_vertically`,
  `zone_clamped_to_bounds`, `max_iterations_reached`), and only `seeding_workspace`
  still carries any.
- Rendered bbox stats (supporting signal): per-scene metrics measured from the rendered
  DOM by the read-only `tools/scene_to_png.mjs`, written to
  `generated/scene_render_stats/<scene>.stats.json`. These measure rendered geometry
  after placeholder substitution, so a missing real asset (rendered as a default-sized
  placeholder box) can register a bbox overlap the engine's geometric model does not see.
  This explains the divergences below (for example `electrophoresis_bench`:
  engine label residual 0, rendered `label_overlap_pair_count` 1).

The `tools/scorecard_m2.mjs` bbox scorecard could not be run: it depends on a removed
`src/main.ts` single-scene entry point (`rewriteMainTsForScene` reads `src/main.ts`,
which no longer exists after the scene-viewer refactor). It is a stale tool predating the
multi-entry build and the compile-time precompute path. Editing `tools/` is out of scope
for this work package (the user owns `tools/` for the v3 SVG normalizer), so the scorecard
is flagged for the human rather than patched. The per-scene rendered bbox stats above
serve as the quantitative regression signal in its place.

## Scene-by-scene evidence table

| scene | known issue | before evidence | after evidence | diagnostics (engine) | scorecard deltas (rendered bbox stats) | AI review summary | final status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cell_counter_basic | tiny primary object | `test-results/m7_before_baseline/cell_counter_basic.png` | `test-results/m7_after/cell_counter_basic.png` | clean (total=0, converged) | yield 85.7%, empty 91.7%, overlaps 0, label-overlap 0, clipped 0; primary `main_cell_counter` 560x392 px (~10.7% of frame) | visual_review_unavailable (no creds) -> human review | OK on diagnostics; primary still small, AI/human polish review pending |
| staining_bench | label overlaps | `test-results/m7_before_baseline/staining_bench.png` | `test-results/m7_after/staining_bench.png` | clean (total=0, converged) | yield 77.8%, empty 92.8%, overlaps 0, label-overlap 0; 2 placeholders (microwave, rocking_shaker) | visual_review_unavailable -> human review | OK on diagnostics (label collisions resolved); 2 missing assets are an author/asset item |
| sample_prep_bench | vertical overflow | `test-results/m7_before_baseline/sample_prep_bench.png` | `test-results/m7_after/sample_prep_bench.png` | clean (total=0, converged) | yield 92.3%, empty 91.6%, overlaps 0, clipped 0, offscreen 0 | visual_review_unavailable -> human review | OK; vertical overflow resolved, converges in one pass |
| hood_basic | vertical overflow | `test-results/m7_before_baseline/hood_basic.png` | `test-results/m7_after/hood_basic.png` | clean (total=0, converged) | yield 90%, empty 82.4%, overlaps 2 (both cross-tier z-layering), clipped 0, offscreen 0 | visual_review_unavailable -> human review | OK; vertical overflow resolved; remaining overlaps are authored cross-tier z-layering |
| seeding_workspace | residual label collisions | `test-results/m7_before_baseline/seeding_workspace.png` (7 overlap pairs) | `test-results/m7_after/seeding_workspace.png` (2 overlap pairs) | non-converged: item_escapes_zone_vertically=1, label_row_staggered=1, max_iterations_reached=1, zone_clamped_to_bounds=1 (all Warning/structural; no Error) | object overlaps 7 -> 2; label-overlap 2; clipped 1; 3 placeholders (hood_surface, vortex, incubator) | visual_review_unavailable -> human review | DIAGNOSTICS-RESIDUAL: no Error, but only non-converged scene; residuals tied to 3 missing assets; route to human review |
| electrophoresis_bench | layout drift | `test-results/m7_before_baseline/electrophoresis_bench.png` | `test-results/m7_after/electrophoresis_bench.png` | clean (total=0, converged) | yield 68.8%, empty 87.5%, object overlaps 0, label-overlap 1 (placeholder-driven), 5 placeholders | visual_review_unavailable -> human review | OK on diagnostics; drift cleared; low yield is missing-asset driven |
| heat_block_bench | layout drift | `test-results/m7_before_baseline/heat_block_bench.png` | `test-results/m7_after/heat_block_bench.png` | clean (total=0, converged) | yield 84.6%, empty 92%, overlaps 0, label-overlap 0, clipped 0; 2 placeholders | visual_review_unavailable -> human review | OK on diagnostics; drift cleared |
| passage_hood_detachment_microscope_view | layout drift | `test-results/m7_before_baseline/passage_hood_detachment_microscope_view.png` (2 overlap pairs) | `test-results/m7_after/passage_hood_detachment_microscope_view.png` (1 overlap pair) | clean (total=0, converged) | object overlaps 2 -> 1 (the remaining pair is cross-tier z-layering), label-art overlap 1, 1 placeholder (microscope) | visual_review_unavailable -> human review | OK on diagnostics; drift cleared; remaining overlap is authored cross-tier |

## Layered-review verdict

- Integration gate (zero Error diagnostics): PASS. No scene of the eight emits any
  Error-severity diagnostic. Seven of eight converge clean; `seeding_workspace` carries
  only Warning/structural residuals, all tied to three missing real assets.
- Determinism gate: PASS. `generated/precomputed_layout.ts` regenerated byte-identical
  (md5 `93369602c8faa50ee81edc9b0c5dbb71`) after `prettier --write` and again after a full
  `bash build_github_pages.sh`.
- Scorecard regression signal (advisory): rendered object-overlap counts dropped where
  measured before (`seeding_workspace` 7 -> 2, passage view 2 -> 1); remaining rendered
  overlaps are either cross-tier z-layering or placeholder-box artifacts.
- AI review gate: not yet a gate. Credentials absent, so all 11 calibration scenes (8 named
  + 3 positive controls) returned `visual_review_unavailable`, routing every scene to human
  visual review. The reviewer stays report-only until a credentialed calibration run shows
  stable, useful results.
- Human review required for: all eight scenes (because of `visual_review_unavailable`), and
  in particular `seeding_workspace` (sole non-converged scene) and `cell_counter_basic`
  (primary object still small relative to the frame).

## Residual items routed elsewhere

- Missing real SVG assets (placeholder boxes) drive most of the remaining low yield and the
  rendered-bbox overlaps: `hood_surface`, `vortex`, `incubator`, `microwave`,
  `rocking_shaker`, `heat_block`, `microscope`, `power_supply`, `gel_comb`,
  `p10_gel_loading_tip_box`. These are author/asset items, not layout-engine defects.
- The stale `tools/scorecard_m2.mjs` (`src/main.ts` dependency) is flagged for the human.
