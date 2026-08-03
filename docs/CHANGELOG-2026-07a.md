## 2026-07-02

### Additions and New Features

- Added `devel/clean_build.sh`, the light build cleaner wired to the `npm run clean` target. It
  wipes build output, tool caches, and test artifacts while keeping `node_modules` (and Rust
  `target/`) intact, so the next build is ab initio with no reinstall.
- Updated `devel/dist_clean.sh` (the deep reset) to keep the committed `package-lock.json`, so a
  distribution-clean checkout still drives a reproducible `npm ci`.
- Repointed the `clean` npm alias in `package.json` from `./dist_clean.sh` to
  `./devel/clean_build.sh`.
- Started tracking `package-lock.json` (removed it from `.gitignore`) so this GitHub Pages repo
  carries a reproducible lockfile.
- Added a "Try it live" GitHub Pages link near the top of README.md pointing to https://vosslab.github.io/virtual-lab-protocol-simulation/, so readers can launch the live app in one click.

### Removals and Deprecations

- Removed the root `dist_clean.sh`; both cleaners now live only under `devel/`
  (`devel/clean_build.sh` light, `devel/dist_clean.sh` deep).

## 2026-07-01

### Additions and New Features

- Added a light root `dist_clean.sh` (`rm -rf dist _site *.tsbuildinfo .eslintcache`,
  rooted via `git rev-parse --show-toplevel`), modeled on `sports-life-game/dist_clean.sh`.
  Repointed `npm run clean` to `./dist_clean.sh` so the clean front door removes build
  output while keeping `node_modules/` and dependency installs intact. `devel/dist_clean.sh`
  remains in place as the separate deep-reset tool (also removes `node_modules`).
- Added missing `npm run test:playwright` alias mirroring `./run_playwright_tests.sh`
  (canonical shell-script/npm-alias pair per `docs/TYPESCRIPT_STYLE.md`).

### Fixes and Maintenance

- Reformatted 7 files with `prettier --write` after the prettier 3.9.4 floor bump. The
  fleet-wide prettier floor bump changed formatting output such that these previously-clean
  files failed `prettier --check`. Ran `npx prettier --write
  '**/*.{ts,tsx,mts,cts,js,mjs,cjs}'` to conform to the canonical `.prettierrc`;
  whitespace-only, no logic change.
- Aligned the `build`, `serve`, and `check` `package.json` script aliases to the canonical
  `./X.sh` front-door form (`./build_github_pages.sh`, `./run_web_server.sh`,
  `./check_codebase.sh`), matching the other TypeScript repos instead of the outlier
  `bash X.sh` form.
- Set `tsconfig.json` `jsx` to `preserve` to match the Solid convention used by the sibling
  Solid repos (`concept-map-maker`, `pseudo-code-mapper`); `jsxImportSource: solid-js` is
  unchanged. `tsc` runs `--noEmit` (typecheck only) and `esbuild-plugin-solid` performs the
  actual JSX transform, so this affects only how tsc type-checks JSX, not the emitted bundle.
- Fixed `./check_codebase.sh` lint gate: added browser-context globals in
  `eslint.config.local.js` for `tools/protocol_to_png.mjs`, `tools/scene_to_png.mjs`,
  `tools/scorecard_m2.mjs`, `tools/svg_picker/**`, and `tests/test_walker_debug.mjs`.
  These files reference `window`/`document` inside Playwright `page.evaluate` /
  `page.waitForFunction` browser callbacks (or, for the test file, a `globalThis.window`
  stub), not real Node globals, so `no-undef` was flagging correct code. Mechanical fix
  per the documented pattern; gate now passes clean (typecheck, lint, format, unit tests).

## 2026-06-27

### Additions and New Features

- Added `run_scene_health.py` (root-level): visible single-command entry point for non-technical scene authors.
  Runs the full two-step chain (`layout_metrics.mjs --all` then
  `layout_health_report.mjs --all`) with no npm or node knowledge required.
  `python3 run_scene_health.py` checks all scenes and streams the scorecard;
  `python3 run_scene_health.py <scene_name>` checks one scene and prints a
  compact summary (finding, categories, verdict, severity, target) plus the
  report path; `python3 run_scene_health.py --list` lists known scene names.
  Friendly prereq checks (node on PATH, tools present) with plain-language
  errors. No precompute step required: metrics tool runs the pipeline live.
- Extended `docs/specs/SCENE_METRICS.md` with task-first workflow section "How do
  I get scene metrics for my new scene?" (6-step workflow: edit YAML, run
  `python3 run_scene_health.py <scene_name>` -- script does everything, read
  scorecard row, open `health_report.md` for full detail, revise YAML, rerun
  until acceptable) and a troubleshooting mini-list (scene not found, report did
  not update, metrics look wrong, borderline warning). Single-scene mode prints
  to stdout only; all-scenes mode writes `test-results/layout_health/health_report.md`.
- Added `tools/layout_golden_diff.mjs` (M1/WS-A): ephemeral regression harness that
  captures a gitignored snapshot at `test-results/layout_reference_snapshot.json`
  and compares engine output after changes. Snapshot includes provenance (scene count,
  generated-layout hash, command, timestamp) and staleness warnings when older than the
  current engine state. Accessible via `npm run layout:diff` and `npm run layout:refresh`.
- Added `tools/layout_metrics.mjs` (M1/WS-B): raw per-scene geometry tool reporting
  rectangle-union fill, largest-empty-rect, per-zone and per-grid occupancy, per-object
  scale and floor proxies, label overlaps, AABB overlap graph, and balance. Generates a
  per-scene overlay summary; accessible via `npm run layout:metrics`.
- Added `tools/layout_health_report.mjs` (M2/WS-C): interprets raw geometry metrics
  into provisional health categories (`healthy`, `shrink-stressed`,
  `high-empty-space-plus-shrink`, `crowded`, `label-stressed`, `sparse`). Classifies
  each scene finding as `engine-fit`, `authoring`, `intentional`, or `healthy` with
  per-scene diagnoses and a worst-first author scorecard. Distribution-derived
  PROVISIONAL bands (pending human approval); shrink fields labeled PROXY; borderline
  tagging. Accessible via `npm run layout:health`.
- Added `npm run layout:health` alias (`node --import tsx tools/layout_health_report.mjs --all`)
  to `package.json`.
- Extended `docs/LAYOUT_REMAINING_WORK.md` with sections 8-10 (M2/WS-D): section 8
  explains the health report for scene designers (how to generate, category reference,
  finding reference, reading evidence blocks); section 9 documents the PROVISIONAL
  metric bands (fill, LER, shrink, label conflict) with distribution-derived values;
  section 10 lists the 16 authoring-class scenes worst-first with one-line diagnoses
  and authoring targets.
- Added `docs/active_plans/audits/layout_geometry_audit.md` (M3/WS-E): documents the
  audit contract, constraint set, and objective function; the three shrink mechanisms
  as a greedy rescue heuristic; the sparse-and-shrunk answer; ranked findings; and
  filled M5 decision templates. M5 verdict: NO-GO (see Decisions below).
- Added report-only off-canvas validation diagnostic stream (M3/WS-F): the validate
  phase classifies each item against scene_bounds as `fully_off_canvas` (error-level)
  or `partial_overflow` (magnitude-scaled warning). Findings surface on
  `PipelineResult.offCanvasDiagnostics` as a separate stream that never blocks the
  build gate. New `tools/offcanvas_baseline.mjs` writes a baseline report to
  `docs/active_plans/audits/offcanvas_baseline.md` (0 of 38 scenes flagged).
  New `src/scene_runtime/layout/diagnostics/offcanvas.ts` holds the diagnostic type
  and classifier. Placement output is byte-identical to HEAD.
  New `tests/test_layout_offcanvas.mjs` exercises the off-canvas classifier.
- Added `tests/test_layout_config.mjs` (M4/WS-J): 16 behavioral config-precedence
  tests covering zone_gap split (confirmed intentional; no disagreeing duplicate),
  scene-level and zone-level overrides, and strategy-local values.
- Added `docs/specs/SCENE_METRICS.md`: canonical scene-metrics reference for scene
  writers. Five-section structure: quickstart (commands, output path, scorecard
  columns), category meanings (sparse, crowded, shrink-stressed, label-stressed,
  off-canvas, high-empty-space-plus-shrink), finding-to-action table (authoring,
  engine-fit, intentional, validation) with practical authoring moves, evidence-field
  glossary (fill ratio, largest empty rectangle, scale, floor hits, overlap graph,
  balance; PROVISIONAL bands and PROXY shrink signals noted), and maintainer notes
  (band derivation, current provisional values, severity scoring weights). Content
  moved from `docs/LAYOUT_REMAINING_WORK.md` sections 8.2-8.4 and 9; those sections
  now point here. Linked from `AGENTS.md` specs list and
  `docs/specs/PROTOCOL_AUTHORING_GUIDE.md` related references.

### Fixes and Maintenance

- Audit-fix pass: scrubbed planning-scaffold tags (WP-#, WS-#, M#) from all
  comments and docstrings in `tests/test_normalize_svg_v3.py`; renamed 8 test
  functions to drop the `wp3b_` prefix; added `pathlib` import and annotated 3
  unannotated helper params. Replaced `sys.exit(1)` with `raise SystemExit(1)`
  in `run_scene_health.py` (PYTHON_STYLE: avoid sys.exit). Corrected
  `docs/specs/SCENE_METRICS.md` single-scene-mode description (the command
  DOES write `health_report.md`, contrary to the prior text). Added
  `run_scene_health.py` and `docs/specs/SCENE_METRICS.md` to
  `docs/FILE_STRUCTURE.md` table. Reordered `docs/LAYOUT_REMAINING_WORK.md`
  section 8.1 so the designer-facing `python3 run_scene_health.py` command
  leads, with node/npm forms moved to a maintainer subsection. Fixed
  `docs/CODE_ARCHITECTURE.md` normalize_svg_v3 deps filename from
  `pip_requirements.txt` to `pip_requirements-dev.txt`.
- Removed the fixture-manifest harness from `tests/test_normalize_svg_v3.py`
  (`_MANIFEST_PATH`, `_load_manifest`, `_manifest_normalize_params`,
  `test_manifest_entries_normalize`, `_manifest_rejection_params`,
  `test_manifest_rejection_entries`, `_manifest_viewbox_params`,
  `test_manifest_viewbox_entries`): the external file
  `tests/fixtures/svg_normalizer/expected_bboxes.json` is banned per
  PYTEST_STYLE.md (no fixtures in the repo) and its absence was aborting
  collection of all 4556+ tests. Replaced with five inline real-SVG cases
  covering the manifest scope areas not already exercised by existing inline
  tests: relative `h`/`v` path commands (bbox width/height round-trip),
  relative `l` (lineto) commands (triangle bbox), relative `a` arc command
  (arc-bulge capture), viewBox with padding (dimensions include 2x padding),
  and viewBox with zero padding (dimensions tight to geometry). Collection no
  longer errors; `pytest tests/` passes 4677 tests.
- Repaired a dead ancestor-walk in `tests/playwright/test_bench_basic_render.mjs`
  Assertion A (M3/WS-G): replaced with a real `parentElement` clip-detection walk up
  to `#scene-root` that checks for `overflow`, `clip`, `mask`, and `contain` CSS
  properties. Spec result stays 9/11 (Assertions B/C are pre-existing missing-SVG
  failures unrelated to this change).
- ESLint config (task #11): added browser-globals override for browser-context files
  (suppresses false-positive `window`/`document` errors); added `^_` ignore pattern
  for `no-unused-vars`; removed genuinely dead symbols; added `{cause}` to two
  rethrows. `check_codebase.sh` now passes all 5 checks.

### Decisions and Failures

- M5 audit verdict NO-GO (M3/WS-E): the geometry audit found zero same-tier collisions
  across all 38 scenes. The 6 engine-fit scenes are authoring-bounded (packed zones
  narrower than their content), not solver defects. A fixed-row reformulation is
  theoretically feasible but unmotivated given that authoring edits resolve all flagged
  cases. Decision and full analysis recorded in
  `docs/active_plans/audits/layout_geometry_audit.md`.
- Golden baseline refresh deferred to human (M1/WS-A): the `test-results/layout_reference_snapshot.json`
  snapshot must be captured from a clean committed tree. It is currently stale-but-harmless;
  a byte-identical precompute confirms no layout change occurred. Run
  `npm run layout:refresh` from a clean committed tree to establish the post-wave baseline.
- M4 (WS-H/WS-I): confirmed the layered config module (`src/scene_runtime/layout/config/`)
  and all call-site wiring already shipped before this wave; no new config module was added
  to avoid duplication. The `label_offset_y` reconciliation (canonical 3.5) was confirmed
  already present.

## 2026-06-26

### Behavior or Interface Changes

- Redesigned `tools/layout_golden_diff.mjs` to use an ephemeral, gitignored snapshot
  at `test-results/layout_reference_snapshot.json` instead of `tests/fixtures/`.
  The snapshot is never committed; it is captured with `--refresh` from a clean engine
  state at the start of a refactor session and compared after changes. The compare mode
  exits non-zero with a clear message when the snapshot is absent, instructing the user
  to run `--refresh` first. Added `fs.mkdirSync` in the refresh path so `test-results/`
  is created automatically on a fresh clone.
- Added `layout:refresh` npm script alias (`npm run layout:refresh`) alongside the
  existing `layout:diff` alias.
- Updated `docs/USAGE.md` layout regression harness section to document the ephemeral
  lifecycle; removed the three-condition committed-fixture refresh procedure.

### Decisions and Failures

- Moved the snapshot from `tests/fixtures/` (not gitignored, commit-eligible) to
  `test-results/` (gitignored at line 7 of `.gitignore`) after the user ruled out
  committed fixtures. The prior snapshot at `tests/fixtures/layout_reference_snapshot.json`
  is now orphaned (no longer read or written by the tool) and is safe to delete manually.

## 2026-06-11

### Fixes and Maintenance

- Ran a pre-commit six-pass audit of the vertical-layout-reflow change and applied
  the resulting fixes.
- Removed planning-scaffolding work-package tags (`WP-*`) from committed code
  comments across the layout engine and `tools/scene_scale_report.mjs`. The
  explanations are preserved; only the tags are stripped, since work-package tags
  are forbidden in committed code under the planning-terminology rule.
- `tools/scene_scale_report.mjs` now surfaces the per-scene `labelDominant` flag in
  both the single-scene view and the `--all` table, so the label-dominant review
  signal is readable without re-deriving it from the pipeline.
- Trimmed corpus-snapshot prose (a specific scene name, raw scale digits, a headroom
  margin, and "today") from the `UNIFORM_RESCALE_MIN_SCALE` comment in
  `layout/constants.ts`, keeping the durable structural explanation.
- Corrected a stale comment in `tests/e2e/e2e_layout_parity_16x9.mjs` that claimed
  the convergence loop keys on the `item_escapes_zone_vertically` diagnostic; that
  keying was removed, and the loop now iterates on horizontal signals only.
- Rewrote the stale "Build pipeline" section of `docs/specs/SCENE_YAML_FORMAT.md`
  (left over from the PRECOMP3 cleanup) to the current chain:
  `gen_scene_index.py` -> `generated/scenes.ts` -> `precompute_layout.mjs` ->
  `generated/precomputed_layout.ts`.
- Refreshed `docs/LAYOUT_REMAINING_WORK.md`: converted now-committed "untracked
  file" notes to Markdown links and closed the completed git-add closeout row.

### Decisions and Failures

- Confirmed four pre-existing issues are out of scope for this change and tracked
  them separately in `docs/LAYOUT_REMAINING_WORK.md` section 7: `extraction_workspace`
  renders blank (empty authored content), the `long_labels_smoke` dev fixture
  references an undeclared object `dmf_bottle`, and the `SCENE_YAML_FORMAT.md`
  PRECOMP3 staleness (now fixed above).

### Developer Tests and Notes

- Derived test expectations from imported layout constants instead of hardcoded
  literals: `REAR_CONTENT` / `FRONT_CONTENT` in `tests/test_layout_reflow_zones.mjs`
  (from `ZONE_PADDING` and `DEPTH_TIER_GAP`) and `LABEL_OFFSET_Y` in
  `tests/test_layout_vertical_footprint.mjs` (from `buildGlobalDefaults`).
  `test_layout_engine.mjs` now uses the live item aspect instead of a pinned 1.35.
- Post-fix gates: `tsc` clean (both configs), 103 layout tests pass,
  `check_codebase.sh` 6/6, pytest markdown-links and ascii pass, and zero `WP-*`
  tags remain in code.
- Produced the full per-scene WP-4 evidence table for all 34 non-fixture scenes
  and committed it at
  [vertical_reflow_wp4_evidence_table.md](archive/reports/vertical_reflow_wp4_evidence_table.md).
  Both hard contracts hold: zero never-crop hard fails and zero own-art label
  overlaps across all populated scenes (G4 hard gate met). The sweep surfaced
  four label-on-label crowding scenes (`hemocytometer_view`, `microscope_basic`,
  `passage_hood_detachment_microscope_view`, `seeding_workspace`) logged as a
  legibility follow-up in `docs/LAYOUT_REMAINING_WORK.md` section 7.6;
  `extraction_workspace` was reconfirmed as a pre-existing load failure (empty
  authored content), out of scope for the reflow.

## 2026-06-10

### Additions and New Features

- Added `tools/scene_scale_report.mjs`: developer tool that runs the real layout
  pipeline read-only and reports, per scene, the reflow overflow ratio, required
  uniform scale, health label (healthy/dense/overloaded), and the heaviest vertical
  band group with its top contributing items. `--scene <name>` prints the per-zone
  breakdown; `--all` prints a sorted table (densest first) plus a count summary.
  Read-only; never writes to `generated/` or `dist/`. Exit 0 on success; exit 1 on
  unknown scene name or bad arguments.

- Vertical reflow WP-3a: connected the measured-extent spine end to end. Reordered
  the placement phases (`phases.ts`) to the final serial order
  `place-horizontal -> measure-vertical -> reflow-zones -> place-vertical ->
  place-labels -> resolve-collisions -> validate`, so `measure-vertical` now runs
  BEFORE `place-vertical`. Because `_height` is 0 before placement, the measure
  stage sources the NATURAL object height (`_visualWidth * viewportAspect /
  aspect`) and threads it to `verticalFootprintFor` as an explicit `objectHeight`
  trailing parameter (the single `wrapLabel` call site is preserved; the resolved
  wrap-tuning config is threaded). Rewrote `vertical_layout.ts` to CONSUME the
  computed `ComputedZoneBand`: each item's object strip is placed inside its
  depth-tier row (`objectTopInRow` per label side -- top label below its label
  strip, bottom label at the row top) and the baseline is back-solved per anchor
  mode via `baselineFromObjectTop` (`bottom | tip | center`, the algebraic inverse
  of `anchorTop`, which is kept). The per-object vertical shrink (`fitFactor` +
  `maxHeightInZone`) is removed; objects keep natural `_height` / `_visualWidth`
  (aspect preserved, never-crop safe by construction). The existing `depth_tier` ->
  vertical layering is preserved: `DEPTH_BASELINE_OFFSET.back = -4` (rear toward the
  top), and reflow places the rear tier (lowest `depth_tier`) first at the band top,
  ascending downward. Pointed the label clamps (`layout_labels.ts` `verticalBandFor`
  and `resolveLabelCollisions` `LabelWork.bandTop/bandBottom`) at the computed band,
  not the authored zone bounds, and added the terminal safety flip: a label flips
  side when its candidate box overlaps its own object's art OR exits the computed
  band and the other side fully clears; when neither side clears it picks the
  lowest-overlap side and emits a label-clearance diagnostic. Threaded
  `reflowOverflow` / `reflowTotalContent` / `reflowSceneRange{Top,Bottom}` from
  `reflowZones` through `phases.ts` onto `PipelineResult` (`run_pipeline.ts`,
  `types.ts`) so WP-3b can trigger the uniform rescale; WP-3a leaves the honest
  overflow signal and the compressed bands. The keystone defect is fixed:
  `sdspage_recycle_buffer_workspace`'s `recycle_buffer_bottle` is now a 2-line top
  label whose bottom edge (`_labelY` 38.75, box 4.40 -> bottom 43.15) sits clear of
  its own object top (47.15), no longer occluding its own cap. New unit tests
  (`tests/test_layout_engine.mjs`): object keeps natural height, top/bottom-label
  tier spacing, anchor back-solve for all three modes, missing-band fallback,
  computed-band vertical clamp, and a terminal flip staying inside its measured row
  extent. Precompute regenerated and byte-identical across two runs; parity e2e GO
  38/38 (`all_exact=true`, `sweep_ok=true`); `check_codebase.sh` 6/6.

- Vertical reflow WP-3b: added the terminal scene-wide uniform OBJECT rescale.
  When reflow content overflows the scene vertical range, one aspect-preserving
  factor is applied to every object's width AND height together (never-crop safe
  by construction; an object cannot distort or crop when its width and height
  shrink by the same factor). The fixed layout magnitudes -- label line height,
  label gap, depth-tier gap, and zone padding -- stay constant under the rescale;
  only object art scales. Threads `reflowUniformScale` through `phases.ts` /
  `vertical_layout.ts`, repurposes the per-item `item_escapes_zone_vertically`
  diagnostic into the scene-level `scene_reflow_overflow` signal, and emits a
  `labelDominant` review flag for scenes where labels rather than art dominate
  the vertical budget after rescale.

- Vertical reflow WP-3c: corrected the uniform-rescale denominator. The first
  WP-3b draft divided the available scene range by `totalContent`, but
  `totalContent` includes fixed non-scaling overhead (zone padding, tier gaps,
  per-item label box plus label gap) that the rescale must NOT shrink. Dividing
  by it under-scaled over-full scenes, so front-zone art still placed past
  `scene_bounds.bottom` and rendered cropped. The corrected factor shrinks only
  the scalable object-height portion:
  `scale = (sceneRange - fixedOverhead) / (totalContent - fixedOverhead)`, with a
  deterministic fixed-point refinement that re-solves when the heaviest tier row
  switches under the new scale.

- Vertical reflow WP-2: added the zone-band reflow stage
  `src/scene_runtime/layout/reflow_zones.ts` (`reflowZones`), the zone-level
  vertical fold that lifts WP-1a's per-item `_combinedHeight` to bands. Per zone:
  items bucket into depth tiers (one row per `depth_tier`, default 0), each tier
  row height is the MAX `_combinedHeight` over the tier's side-by-side items (a
  per-tier-max sum, not a union), and
  `zoneContentExtent = sum_tier(rowHeight) + (tierCount-1)*tierGap + 2*zonePad`.
  The scene's vertical range reflows across zones in depth order (rear -> front =
  authored band-top order): when content fits, each zone gets its content extent
  plus a share of the leftover distributed proportionally to authored band height;
  when content overflows, zones compress to their content extent and the overflow
  is handed to the WP-3b uniform object rescale. Produces
  `ComputedZoneBand { id, top, bottom, baseline, tiers }` (with
  `ComputedTierRow { depthTier, rowTop, rowHeight, placementNames }`) added to
  `types.ts`; the authored baseline is recomputed by the fraction formula
  (`baselineFraction = (baseline - authoredTop) / authoredHeight` clamped to
  `[0, 1]`, then `computedBaseline = computedTop + fraction * computedHeight`),
  with absent baselines mapped to the band center and out-of-range fractions
  reported in `baselineClamps`. Added a `reflow-zones` phase in `phases.ts` after
  `measure-vertical` (read-only w.r.t. position; writes only `ctx.zoneBands`), a
  `DEPTH_TIER_GAP` constant aliasing the existing depth spacing magnitude
  (`tierGap = depthOffset`, no new magic constant), and a `zoneBands` field on
  `PipelineResult`. New unit tests in `tests/test_layout_reflow_zones.mjs` assert
  per-tier-max content extent, depth-order placement (independent of input order),
  proportional leftover distribution, the baseline fraction formula, a reported
  out-of-band clamp, the overflow compression path, and tier-row spacing.

  Reflow range source (hard acceptance): the reflow range is `scene.scene_bounds`
  verbatim -- `sceneRangeTop = scene_bounds.top`, `sceneRangeBottom =
  scene_bounds.bottom`. This is the same `SceneBoundsRect` rect
  `clamp_scene_bounds.ts` validates item bboxes against and that
  `structural_guards.ts` requires every zone and label to lie inside, so the band
  reflow shares the rendered viewport (no header-band or clipping drift). WP-2
  only PRODUCES the bands; `vertical_layout.ts` still owns object geometry, so the
  precompute is byte-identical (regenerated, zero git diff; deterministic
  double-run byte-identical) and `ComputedZoneBand` is produced for every zone in
  all 38 scenes. WP-3a rewrites `place-vertical` to CONSUME the bands.

- Vertical reflow WP-1a: added the vertical measured-extent helper
  `src/scene_runtime/layout/vertical_footprint.ts` (`verticalFootprintFor`), the
  vertical mirror of `footprint.ts`. It folds the width-stable wrapped label box
  into an item's vertical extent and returns
  `{ labelLines, labelBoxHeight, combinedHeight }` where
  `combinedHeight = _height + labelOffsetY + labelBoxHeight` using the REAL
  wrapped line count. The combined extent magnitude is side-independent (the same
  whether the label sits above or below the object). Added a `measure-vertical`
  stage in `phases.ts` that records `_combinedHeight`, `_labelBoxHeight`,
  `_labelPlacement`, and the reused `_labelLines` onto placed items without
  changing any object geometry. New `ComputedItem` fields `_combinedHeight`,
  `_labelBoxHeight`, `_labelPlacement` (optional, magnitude + side recorded
  separately). New unit tests in `tests/test_layout_vertical_footprint.mjs` assert
  the 1-line and 2-line combined extents and that the value is identical for `top`
  and `bottom` placement. `generated/precomputed_layout.ts` regenerated:
  geometry and label-line fields byte-identical across all 38 scenes / 437 items;
  only the three new fields were added. This is the measured base every later
  reflow work package depends on; placement and labels are unchanged.

  Decision: the plan specified inserting `measure-vertical` between
  `place-horizontal` and `place-vertical`, but `_height` is filled by
  `place-vertical` (`place-horizontal` leaves `_height = 0`), so the combined
  extent would be meaningless there. WP-1a keeps `place-vertical` unchanged, so the
  stage is placed AFTER `place-vertical` (the only point where `_height` is real);
  a later work package that rewrites `place-vertical` reorders the stage ahead of
  it and sources the object height differently.

- Vertical reflow WP-1b: established a SINGLE `wrapLabel` call site and decoupled
  the vertical-escape signal from the convergence loop. `layout_labels.ts` now
  consumes the `_labelLines` / `_labelBoxHeight` the `measure-vertical` stage
  already computed instead of re-wrapping the label a second time; the only
  operative `wrapLabel` call is now in `vertical_footprint.ts`
  (`verticalFootprintFor`), with a guarded fallback in `layout_labels.ts` that
  fires only for direct-call unit tests where `_labelLines` is absent. The two
  sites can no longer diverge: `verticalFootprintFor` gained optional
  `avgCharWidthPct` / `budgetTolerance` parameters and the measure-vertical phase
  threads the resolved `config.avgCharWidthPct` / `config.wrapBudgetTolerance`, so
  the measure wrap and the fallback wrap read the same config values. Proof:
  `generated/precomputed_layout.ts` regenerated with all 437 `_labelLines` arrays
  byte-identical before/after (including all 129 two-line wraps, e.g. the six in
  `sdspage_recycle_buffer_workspace`); deterministic double-run byte-identical.

  `item_escapes_zone_vertically` was removed from `run_pipeline.ts`
  `FITTABLE_KINDS`, so the convergence loop's per-zone `_width_scale` shrink +
  re-entry now triggers on HORIZONTAL fit signals only (`zone_overflow_negative_gap`,
  `tab_stop_overflow`). A vertical escape is a height problem; shrinking a zone's
  width to "fix" it was the wrong lever (the legacy mechanism this reflow plan
  removes). The diagnostic is still emitted by `vertical_layout.ts` as a
  scene-level reflow-overflow signal (WP-3b repurposes it into the scene-wide
  uniform object rescale). Convergence iteration count DECREASED, not increased:
  total passes 46 -> 43; `hood_workspace` 3 -> 1 and `seeding_workspace` 3 -> 2
  (both were vertical-driven), while horizontal-driven scenes
  (`adversarial_overflow_smoke`, `imaging_bench`) stayed at 3.

- `tools/normalize_svg_v3.py`: no-op clip elimination shipped. When a clip
  region fully contains the clipped target (the common editor-emitted
  page-bounds safety clip), the clip-path reference is dropped and the target
  geometry is left unchanged -- render-identical, no precision loss. New
  helpers: `_clip_is_noop`, `_clip_polygon_for_flatten`,
  `_target_envelope_polygon`, `_target_is_stroke_only`,
  `_resolved_stroke_width`; `_flatten_one_clip` and
  `_target_segments_for_clip` rewritten. 10 new unit tests and 5 fixtures
  added. Measured effect: normalized files rose from 721 to 1757
  (`CLIPPATH_UNSUPPORTED_COMPLEX` fell from 1120 to 84).

- Patch 2: `label_placement` added as a closed `top|bottom` enum scene-object
  field. Spec docs updated (`docs/specs/LAYOUT_ENGINE.md` label-anchor
  convention, `docs/specs/SCENE_YAML_FORMAT.md`,
  `docs/specs/SCENE_VOCABULARY.md`) plus validator coverage in
  `src/scene_runtime/validation/yaml_schema` and new
  `tests/test_label_placement_validator.py`.

### Behavior or Interface Changes

- Vertical reflow WP-1b: two items change geometry as a direct, intended result
  of the loop decouple -- `rear_right_incubator` in `hood_workspace` and
  `seeding_workspace` (the `rear_right` 138% uniform-fallback scenes named in the
  plan's blast-radius analysis). The object sits at the `MIN_SCALE` (0.55) vertical
  auto-fit floor in both before and after; the only change is that the loop no
  longer applies an EXTRA vertical-escape-driven `_width_scale` shrink on top of
  the floored object, so `_width_scale` rises (1.40625 -> 1.736), `_shrunk_passes`
  drops to 0, and the object renders slightly larger. All other 435 items and 36
  scenes are byte-identical. The item still emits `item_escapes_zone_vertically`
  as a diagnostic; full handling of these two scenes (uniform fallback rescale)
  lands in WP-3b.
- Sibling overlap-detector hardening: removed the own-placement exclusion from
  all four label-over-art overlap detectors so a label overlapping its OWN
  object's art is now counted and gated, not silently skipped. Affected
  detectors: `scene_stats` `label_art_overlap_count`, `scene_lint` check B8,
  `structural_guards` Guard 8, and Playwright Assertion H. Assertion H now
  resolves label-to-object ownership through `data-label-for` (the rendered
  sibling relationship) instead of a DOM ancestor walk that matched nothing, and
  it now loud-fails when zero comparable label-art pairs are found rather than
  passing vacuously. Guard 8 own-art overlap is promoted to a hard fail at live
  render.
- Patch 1a: convention rename `_x`->`_centerX` and `_y`->`_baselineY` across
  `src/scene_runtime`, with `generated/precomputed_layout.ts` regenerated
  value-identical (no geometry change).
- Patch 1b: renderer and `structural_guards` boundary conversion to center
  semantics (`left = _centerX - _visualWidth/2`); fixed the label-bbox height
  bug; precompute output byte-identical.
- Patch 3a: layout engine enum plumbing for `label_placement` plus top/bottom
  seed geometry.
- Patch 3b: per-zone direction-aware stagger -- top labels stagger up and clamp
  at the zone top edge.
- Patch 4a: global resolve-collisions made direction-aware, distinguishing
  clamp-drift from collision-displacement for cause context.
- Patch 4b: diagnostics baseline refreshed with 4 authored
  `label_placement: bottom` overrides; main-corpus `unresolved_label_overlap`
  count fell from 5 to 1.

### Fixes and Maintenance

- Vertical reflow WP-3a defect fix: `reflow_zones.ts` stacked EVERY authored zone
  into its own vertical band, but real scenes lay out 5-7 zones as a grid of 2-3
  horizontal rows (side-by-side zones share an authored vertical extent, e.g.
  `rear_left` / `rear_center` / `rear_right` all at the same authored
  `top..bottom`). Stacking the side-by-side zones summed their content extents into
  the scene's vertical range, producing a false 1.5x-4.4x overflow and placing
  most objects off-screen (13 of 16 in `sdspage_recycle_buffer_workspace`, bottoms
  at y=124..322 in a 95-unit scene) -- the exact "deterministic but wrong stacking"
  risk from the plan risk register. Added `groupVerticalBands`: zones whose
  authored vertical ranges OVERLAP (transitively, by a sweep on authored top) merge
  into one vertical band group, the group's height is the MAX of its member zones'
  content extents, and every member zone gets the same computed band top/bottom
  with its tier rows placed inside that shared band. This restores the pre-reflow
  authored-grid semantics (each zone placed in its own authored bounds, never
  stacked) while still reflowing across the distinct vertical bands in depth order.
  The off-screen count for the recycle scene dropped from 13/16 to the residual
  genuine multi-tier overflow handed to WP-3b. New unit tests
  (`tests/test_layout_reflow_zones.mjs`) assert that exact side-by-side zones share
  one computed band (content counted once, no false overflow) and that partially
  overlapping authored bands (the real `[38,76]` center vs `[72,94]` front sdspage
  pair) merge into one vertical band.

- `src/scene_runtime/layout/layout_labels.ts`: fixed the rear-zone top-label
  clamp-onto-own-art defect. The seed-level top-clamp used to raise a top label
  DOWN to `zone.top + padding` with no guard that the label must stay above its
  own object's visual top, so a rear-zone object near the scene top got its label
  pushed onto its own cap (the `recycle_buffer_bottle` "bott" occlusion). Top
  labels now clamp their TOP edge into `[topClamp, _top - labelHeight]` so a label
  with room above its object stays fully clear of its own art. When the object
  sits so high that even `topClamp` leaves no room above it, the label flips to a
  zone-confined BOTTOM fallback (effective `label_placement: bottom` carried
  forward to the stagger and resolve-collisions phases) so the text moves off the
  cap rather than overprinting it. Clean top/bottom scenes are byte-identical.
  `generated/precomputed_layout.ts` regenerated (deterministic, double-run
  identical). Two new fixtures in `tests/test_layout_engine.mjs` cover the
  no-room-above flip and the tall-object recycle geometry. Known residual: a tall
  rear object whose zone is too short for either placement (recycle_buffer_bottle:
  zone [5,36], object span [9.946,32], 2-line label needs 4.4% but only ~3.4%
  gap exists above) still overlaps its own body; this is a surfaced
  zone-sizing/label-width infeasibility, not a silent cap overprint, and is left
  for a follow-up (widen `label_width` to one line or extend the rear zone).

- Patch 5: deleted the stale `[data-label]` CSS block from `src/style.css`; the
  block no longer matched any rendered element after the center-anchor
  conversion.

- `docs/active_plans/audits/top_label_collision_forecast.md`: WS-O read-only
  forecast artifact for WP-4b. Confirms the WP-3a count of 14 down-staggered
  top labels (centrifuge_workspace 3; dilution_workspace, drug_dilution_setup_bench_setup,
  electrophoresis_bench, extraction_workspace, seeding_workspace, and 6 sdspage_*
  scenes at 1 each). Total predicted conflicts: 4 across 2 non-fixture scenes
  (dilution_workspace 2 L-A, hood_workspace 1 L-L + 1 L-A). Worst-3 scenes:
  dilution_workspace, hood_workspace, centrifuge_workspace. Cross-checked against
  stats JSON `label_overlap_pair_count`/`label_art_overlap_count` fields.

- `docs/active_plans/audits/missing_svg_degradation_ledger.md`: audit of all
  38 scenes in `generated/scene_render_stats/` for placeholder/degraded status.
  34 curriculum/smoke scenes degrade (advisory_flags=degraded); 2 are intentional
  dev fixtures; 2 are clean. 16 distinct missing object_id types found; 13 are
  undocumented in `assets/SVG_ASSET_GAPS.md` (centrifuge, water_bath, vortex,
  p10_gel_loading_tip_box, gel_comb, hood_surface, incubator, lightbox,
  rocking_shaker, microscope, microwave, plate_reader, and heat_block overlap
  discrepancy). Includes per-scene bbox/label note and WP-6 reviewer guidance.
  Two discrepancies flagged: heat_block and cell_counter are listed in
  SVG_ASSET_GAPS.md as having assets but still appear as missing_object_names
  in stats (likely asset path or registration mismatch).

- `docs/active_plans/audits/playwright_label_assertion_inventory.md`: static
  inventory of label-related assertions in `tests/playwright/` as WP-6
  pre-flight. Classifies each assertion as BREAKS-LEGITIMATELY (H, I overlap
  checks in bench_basic and generalization), NEEDS-JUDGMENT (G containment),
  or UNAFFECTED (J readability, dom_contract selectors, reactivity SVG-safety).
  Includes file:line citations and recommended pre-WP-6 actions.

- `test-results/scene_label_alignment/after_p1_metrics.json`: generated
  after-metrics artifact for the G1 gate / WP-1b review advisory. Computed
  from `generated/scene_render_stats/*.stats.json` (post-WP-1b renderer
  boundary fix). 38 scenes, 437 labeled placements, 307 pass (70.3%), 130
  fail. WP-1b reported 113 failures over non-fixture scenes; the full-corpus
  count is 130, the difference being exactly the 17 failures in the
  adversarial_overflow_smoke dev fixture. Remaining failures are horizontal
  label-center displacement -- engine rework deferred to WP-3a+.

- `tools/normalize_svg_v3.py`: conservative-containment follow-up -- corrected
  the buffer direction in `_clip_is_noop` so the safety margin shrinks the
  clip polygon inward rather than growing the target envelope outward,
  preventing borderline clips from being incorrectly classified as no-ops.
  Genuine stroke trims (57 cases) and complex clip sides remain rejected.

- `docs/LAYOUT_REMAINING_WORK.md`: new durable reference doc covering all remaining scene layout and aesthetic work after the grounding-cue and label-disambiguation-spacing shipped; includes scene-by-scene void/focal/label/Error status for all 9 review scenes, the 4 Error diagnostic cross-reference table, the two pending non-authoring decisions (label-Error severity contract and baseline-tool gap), recommended priority sequence, and human-only git/closeout items; added row to `docs/FILE_STRUCTURE.md` docs table.

- Applied close-out audit fixes across the vertical-reflow surface:
  corrected the stale `(0.40)` floor comment in `vertical_layout.ts` to
  reference `UNIFORM_RESCALE_MIN_SCALE` by name; fixed the B8
  label-intersection comment in `rules_group_b.py` to say it checks all
  placements including the label's own object; replaced the `34-scene corpus`
  hard count in `constants.ts` with `every non-fixture scene`; removed the
  dead `itemEscapesZoneTolerance` config field and the
  `ITEM_ESCAPES_ZONE_TOLERANCE` constant (no remaining consumers after the
  per-object-shrink removal); fixed `tools/scene_scale_report.mjs` to report
  the pipeline's actual `reflowUniformScale` instead of the superseded
  `sceneRange/totalContent` ratio, and renamed its functions to camelCase;
  exported `UNIFORM_RESCALE_MIN_SCALE`, `ZONE_PADDING`, `DEPTH_TIER_GAP`, and
  `LABEL_LINE_HEIGHT_PCT` from the layout barrel so four test files assert
  against the constants instead of copy-pasted literals; corrected the
  phase-order lists and retired verification commands in
  `docs/specs/LAYOUT_ENGINE.md`; added a two-pass vertical reflow SHIPPED
  entry to `docs/LAYOUT_REMAINING_WORK.md`.

### Decisions and Failures

- Uniform-rescale floor recalibration (0.40 -> 0.27) to honor never-crop.
  `UNIFORM_RESCALE_MIN_SCALE` was lowered from 0.40 to 0.27 in
  `src/scene_runtime/layout/constants.ts`. The prior 0.40 floor rested on the
  flawed `sceneRange / totalContent` estimate (the WP-3c denominator bug); once
  the denominator was corrected to the scalable-object-height-only form, the true
  fixed-point minimum across every non-fixture scene is 0.2879
  (`passage_hood_detachment_hood_workspace`, the densest). A 0.27 floor leaves
  ~0.018 headroom so every non-fixture scene fits with zero scientific art past
  the scene bottom. Keeping 0.40 would have re-clamped the densest scenes above
  their required scale and reintroduced cropping, violating the never-crop
  invariant; the floor was lowered to the smallest value that still fits the
  measured corpus. This is the vertical uniform-rescale floor and is distinct
  from the horizontal packer `MIN_SCALE` (0.55), which is unchanged.

- Viewport-overflow regression learning note (root cause + fix). After the first
  WP-3b uniform rescale shipped, over-full scenes still rendered front-zone art
  clipped past the viewport bottom even though the rescale was active. Root cause:
  the rescale denominator divided by `totalContent`, which folds in fixed
  non-scaling overhead (zone padding, tier gaps, per-item label box + gap), so the
  computed factor was too large and only partly closed the overflow. The fix
  (WP-3c) subtracts the fixed overhead from both sides of the ratio so the factor
  shrinks only the object-height portion that can actually scale, plus a
  fixed-point refinement for winning-row switches. The 0.40 floor recalibration
  above is a direct consequence: the corrected denominator changed the measured
  minimum scale. Recorded as a debugging record -- a too-large rescale factor that
  "looked active" but did not clear overflow traces to a denominator that mixed
  scalable and non-scalable height. See
  `docs/active_plans/audits/viewport_overflow_reflow_investigation.md` (a new
  untracked file this cycle; it becomes a link once a human commits it).

- Pipette label offset root-cause audit: the ~6px pipette/tool label offset is
  not label misplacement. Two contributing causes: (a) un-normalized
  pipette/tool SVGs that `tools/normalize_svg_v3.py` rejects with
  `CLIPPATH_UNSUPPORTED_COMPLEX` -- a `PRIMARY_CONTRACT` item-3 gap, deferred per
  user; and (b) the alignment gate's `visual_bbox` measures the SVG element rect
  rather than the drawn-path `getBBox`, which is harmless for normalized assets.
  Decision: labels attach to `_centerX` (footprint center); no engine
  `_visualCenterX` is added. Normalized-only alignment is 78% with zero genuine
  label-on-ink misplacement. See
  `docs/active_plans/audits/pipette_label_offset_root_cause.md` and
  `docs/LAYOUT_REMAINING_WORK.md` section 4.3.

### Developer Tests and Notes

- Vertical reflow WP-4 evidence sweep. Regenerated the precompute and rendered
  before/after PNGs plus stats for every scene. Direct label-vs-own-art bbox
  check = 0 overlaps; never-crop hard fails = 0; parity e2e GO 38/38; pytest
  1753 passing; `check_codebase.sh` 6/6. The `image_evaluator` visual verdict
  marked all twelve densest scenes (uniform scale 0.27-0.32, `labelDominant`)
  SHIP-OK, confirmed viewport-bottom clipping is visually gone, and confirmed the
  `sdspage_recycle_buffer_workspace` keystone (`recycle_buffer_bottle`) survived
  the rescale without re-occluding its own cap.

- Patch 6: global retune evidence sweep. Labels now render centered above
  objects (default flip). The Playwright suite was repaired for the
  `scene_viewer.html` architecture: bundle path `dist/main.js`->`scene_viewer.js`,
  `scene_viewer.html?scene=` navigation, `.first()` locators, and dead-code
  removal. Before/after PNG sets and stats are under
  `test-results/scene_label_alignment/`; the per-scene review table is at
  `docs/active_plans/reports/label_alignment_wp6_review.md`. All 34 non-fixture
  scenes were visually evaluated (0 never-crop, 0 clipping); never-crop hard
  fails 0.
