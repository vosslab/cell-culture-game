## 2026-06-09

### Decisions and Failures

- `docs/active_plans/reports/normalize_svg_v3_findings.md`: corrected the Rank 1
  next-feature recommendation. A per-target clip probe over the corpus showed
  that 1083 of the 1120 `CLIPPATH_UNSUPPORTED_COMPLEX` rejections are stroke-only
  TARGETS (not complex clip geometry), and 3435 of those targets / 1077 files are
  no-op clips (the clip region already contains the target, typically an
  editor-emitted page-bounds safety clip). The prior writeup mis-prescribed
  expanding the clip by stroke width; the real fix is a bounded no-op short
  circuit (drop the clip ref when `clip_poly.contains(target_envelope)`) that
  unblocks ~1077 files and roughly doubles the normalized count, with no
  stroke-to-path machinery. Genuine stroke trims (57 targets) stay rejected.

### Additions and New Features

- `src/style.css`: round 1.7 refinement -- split `#scene-root::after` surface-band into two selector groups: WARM amber/wood-tone (`rgba(80,60,30,0.10/0.18)`) for bench-type workspaces (bench, cell_counter); NEUTRAL cool blue-grey (`rgba(120,125,130,0.12/0.20)`) for clinical workspaces (microscope, incubator, plate_reader); hood workspace remains excluded (no band); geometry (top:78%, z-index:0, pointer-events:none) unchanged; contact drop-shadow unchanged; `generated/precomputed_layout.ts` byte-identical; 8 re-renders in `test-results/m7_after_r17/`.
- `src/style.css`: round 1.6 refinement -- recolored `#scene-root::after` surface band from warm amber (`rgba(160,140,100)` / `rgba(148,124,82)`) to neutral cool/clinical grey (`rgba(120,125,130)` / `rgba(110,116,122)`); enabled band for `microscope` workspace (previously excluded); hood workspace remains excluded; neutralized contact drop-shadow tint from warm-brown `rgba(80,60,30,0.26)` to neutral dark grey `rgba(40,44,48,0.26)` with identical blur/offset/opacity; `generated/precomputed_layout.ts` byte-identical; 8 re-renders in `test-results/m7_after_r16/`.
- `src/style.css`: added grounding cue (round 1) -- a `filter: drop-shadow` contact shadow on each `[data-placement-name]` item and a faint bench-surface gradient on `#scene-root::after` so scene objects read as resting on a bench rather than floating; no layout geometry changed, `generated/precomputed_layout.ts` remains byte-identical.
- `src/style.css`, `src/scene_runtime/renderer/render_scene.tsx`: round 1.5 refinement -- gated the `#scene-root::after` warm bench-surface band on `data-scene-workspace` (bench, cell_counter, incubator, plate_reader only; omitted for hood and microscope workspaces whose interior is not a warm bench surface); `mountScene` now stamps `data-scene-workspace` from `result.scene.workspace` and the dispose cleans it up; strengthened the contact drop-shadow from `(0px 5px 6px 0.20)` to `(0px 6px 8px 0.26)` for clearer perceptibility; `generated/precomputed_layout.ts` remains byte-identical; 8 re-renders in `test-results/m7_after_r15/`.
- `docs/FILE_STRUCTURE.md`: added the three new layout subdirs
  `src/scene_runtime/layout/config/`, `diagnostics/`, and `strategies/` with
  their file listings; added `phases.ts` to the layout subtree; added
  `docs/NEWS.md` to the docs table; added `devel/ai_polish_review.mjs` to the
  devel table.
- `docs/CODE_ARCHITECTURE.md`: added subsections for `config/`, `diagnostics/`,
  and `strategies/` after the existing `geometry/` subsection; added `phases.ts`
  to the layout file table.
- `docs/USAGE.md`: updated the render-flow pseudocode to show
  `resolvePrecomputedResult` as the production/browser path and note that
  `runPipeline` is invoked only at build time by `pipeline/precompute_layout.mjs`.
- `docs/specs/LAYOUT_ENGINE.md`: replaced the stale pre-PRECOMP3 bulk (retired
  `tools/build_scene_data.py`, `src/scene_configs.ts`, `computeSceneLayout()`,
  `src/tsconfig.json`, `game_state.ts`, old scene YAML paths) with a concise
  accurate description of the compile-time model; preserved the intact
  "Compile-time model and known limitations" section; updated Verification
  commands to `npx tsc --noEmit -p tsconfig.json` and `bash build_github_pages.sh`.

- `tools/svg_feature_census.py`: new read-only census that walks every element
  of all 3125 wild SVGs under `OTHER_REPOS/` and records, per file, which
  normalization-relevant features are present (clipPath, transform, text,
  shapes, gradient, filter, mask, use/symbol, image, foreignObject, style,
  non-ASCII id, attribution), cross-tabbed against the live v3 verdict. Emits
  `docs/active_plans/reports/svg_feature_census.{json,md}`.
- `docs/active_plans/reports/svg_imagehash_similarity_3125.md`: consolidated
  report combining the full imagehash run (721 normalizable files, both engines,
  0 render errors, 87% cross-engine identical) with the feature census.
  Documents that clipPath is the largest normalization requirement (1393 files,
  44.6%; 1119 reject complex) and confirms widening the simple-clip allowlist as
  the highest-value next feature.
- Re-ran `tests/e2e/e2e_svg_visual_regression.py --full` over all currently
  normalizable wild SVGs; refreshed `svg_visual_regression.{json,md}`.

### Behavior or Interface Changes

- `src/scene_runtime/layout/layout_labels.ts`: geometry lever 1 (label disambiguation), round 2b -- the per-zone horizontal nudge keeps `effectiveLabelHalfWidth` (the wider of authored `label_width` budget vs rendered text width) for overlap DETECTION so budget-exceeding labels no longer overprint while the engine reports "converged", but the nudge MAGNITUDE is now minimal and anchor-preserving: a pair is separated only when its effective extents actually overlap beyond the shared collision tolerance (`gap < want - collisionTolerance`), and a pair already clear under effective width is left exactly at its anchored position. The earlier round 2 version drove the nudge to a full effective-half-width sum unconditionally and re-clamped every label, which shoved already-fitting labels off their bottle bases (hood_basic "Sterile water" detached; staining_bench labels slid off-anchor) and dropped one label below the visible frame (staining_bench "Waste container"). FRAME SAFETY: both the per-zone stagger floor (`layoutLabels`) and the global re-stagger floor (`restaggerZoneLabels`) now reserve the deepest label's rendered height so a multi-line label's BOTTOM edge stays inside the padded zone (within the renderable scene frame) instead of clamping only its top; a label is never pushed below the visible frame, and a small residual overlap is tolerated over off-frame ejection. Determinism preserved (same stable sort, bounded pass cap, x-first tie-break, pure helper): `generated/precomputed_layout.ts` byte-identical across two `pipeline/precompute_layout.mjs` runs. Error-severity diagnostics over the 8 review scenes unchanged from the round 2 baseline (no new Errors; electrophoresis_bench's transient round-2b residual against the gel cleared by keeping full `want` clearance for real overlaps); 4 pre-existing author-side cross-zone Errors remain (bench_basic label-vs-artwork, passage_hood label-vs-label x2, seeding_workspace object overlap) and are out of this labels-only scope. 8 re-renders in `test-results/m7_after_r2b_labels/`; hood_basic + staining_bench restored to anchored/in-frame, electrophoresis_bench + seeding_workspace stay de-overlapped.

### Fixes and Maintenance

- Rotated `docs/CHANGELOG.md` (was 1655 lines): kept 2026-06-08 and 2026-06-05;
  archived 2026-06-04 through 2026-05-23 to `docs/CHANGELOG-2026-06a.md`.
- `tests/e2e/e2e_svg_visual_regression.py`: corrected three stale notes that
  claimed v3 does not yet flatten simple clipPaths. v3 flattens simple clips
  (allowlist) and rejects complex ones; only the small simple-clip subset is
  normalized.

## 2026-06-08

### Additions and New Features

- WP-3c (D1): added floor-shadow removal to `tools/normalize_svg_v3.py`.
  Two new CLI flags (both default-off): `--remove-floor-shadow` deletes detected
  floor-shadow elements before the single bbox crop so the viewBox tightens to the
  real object; `--shadow-dry-run` reports candidates (xpath, bbox, signal, crop delta)
  without deleting or writing output. Detection function
  `detect_floor_shadow_candidates` is a pure testable helper: candidate must be
  wide-flat (width/height > 3), sit in the bottom band (center_y in lowest ~20% of
  overall height), and carry at least one shadow signal (resolved fill-opacity < 0.5,
  desaturated near-grey hex fill, or id/class containing "shadow"); blur-filter alone
  is insufficient (filters are already rejected). Reads only inline style and
  presentation attributes -- no guessing from `<style>` class rules. Wired in
  `normalize_svg_file` BEFORE `compute_bbox`. Isolated: not part of core pass/fail;
  flag-off is a strict no-op (121+13=134 passed, 1 skipped).
  `tests/test_normalize_svg_v3.py` gains 13 new D1 tests covering detection with each
  signal, negative/no-false-positive cases, no-guess-on-unsupported-CSS, flag-off
  retained vs flag-on tightened viewBox, dry-run no-deletion, and S1 integrity after
  removal. `_fill_is_desaturated_grey` and `_shadow_signal` are also unit-tested.
- WP-4a: declared new Python dependencies in `pip_requirements.txt`: `lxml`
  (XML parse/serialize for v3; preferred over ElementTree for namespace control),
  `tinycss2` (CSS `<style>` block parsing for F8 `url(#id)` ref rewrite and
  geometry-affecting CSS detection), `shapely` (bounded geometry primitive for
  simple-clipPath flattening; curves flattened to polylines within fixed tolerance
  before intersection).
- Added `tools/normalize_svg_v3.py` as the SVG ingestion gate (milestones M1-M3,
  WP-1a through WP-3c). Single normalize-or-reject pipeline with no warning-only path:
  transform flattening (A1: translate/scale/rotate/matrix, nested groups, arc-under-matrix SVD);
  shape->path including rounded-rect (A2); stroke-aware bbox (A3: half stroke-width + miter);
  decimal precision (A4); text/script/filter/mask/marker/use/image/foreignObject/DOCTYPE/complex-clipPath
  rejection with stable reason codes (A5, S2); reference-integrity hard gate (S1);
  editor-cruft removal (B1: Inkscape/Sodipodi/Adobe ns allowlist; attribution preserved);
  F8 `<style>` `url(#id)` ref rewrite via tinycss2; canonical lxml serialization (S4:
  stable ns, UTF-8, no ns0:, final newline, metadata/comments/title/desc preserved);
  floor-shadow removal (D1, opt-in, default off). Depends on lxml, tinycss2, shapely.
  Simple-clipPath flattening (A6, required scope, uses shapely) is implemented in v3;
  shapely must be installed for that path to execute. Complex clips always reject
  (`CLIPPATH_UNSUPPORTED_COMPLEX`) regardless of shapely availability. v2 is unchanged;
  v3 is the new ingestion gate; corpus re-normalize is a separate follow-up.
- WP-4a: updated `docs/FILE_STRUCTURE.md` and `docs/CODE_ARCHITECTURE.md` to document
  `tools/normalize_svg_v3.py`, the normalizer support contract (normalize/preserve/reject
  dispositions), all rejection reason codes, the ingestion workflow, and the shapely/lxml/tinycss2
  dependency rationale. Updated audit `docs/active_plans/audits/normalize_svg_v2_audit.md`
  to record v3 resolutions for F8, F9, and F10. New working docs under
  `docs/active_plans/`: v3 audit, findings synthesis, parity report, and visual-regression
  report.
- WP-4b / WP-1c: `--report-json` flag emits a machine-readable per-file verdict JSON
  (normalize/reject, reason code, bbox, elapsed time) for downstream tooling and the
  wild-corpus runner. Feature classifier assigns one of 21 stable reason codes to every
  rejection so callers never parse human-readable messages.
- WP-3e: simple-clipPath flattening (A6) uses shapely to compute the intersection of a
  simple clip path (single rect/circle/ellipse/polygon subpath) with each clipped element's
  path geometry; curves are flattened to polylines within a fixed tolerance before
  intersection. Complex clipPaths (multiple subpaths, nested clips, or shapes v3 cannot
  resolve) always reject with `CLIPPATH_UNSUPPORTED_COMPLEX` regardless of shapely
  availability.
- userSpaceOnUse gradient/pattern sync (WP-2a): when a gradient or pattern uses
  `gradientUnits="userSpaceOnUse"` and is referenced by a transformed element, v3 bakes
  the element transform into `gradientTransform` (single-use case) so the rendered colors
  stay correct after transform flattening. A gradient shared by elements with differing
  transforms rejects (`UNSUPPORTED_TRANSFORM`) because there is no
  single correct transform to bake.

- Added `src/scene_runtime/layout/strategies/` (M5 / WP-STRAT1), the
  `PlacementStrategy` seam for horizontal placement. `placement_strategy.ts`
  declares the `PlacementStrategy` type (places one zone's items given the
  zone's items, the `Zone`, and a resolved `StrategyContext` carrying `gap`,
  `minScale`, `zonePadding`, `LayoutConfig`, and the shared diagnostics sink)
  and returns that zone's `ComputedItem[]`. `row_strategy.ts` holds the
  historical row placement logic verbatim (left/right/center/justify/tab-stops
  plus the overflow uniform-shrink path). `horizontal_layout.ts` is now a thin
  dispatcher: it resolves the shared context once, selects a strategy per zone
  (`selectStrategy`, only `row` exists today), and delegates; its exported
  signature is unchanged so callers and tests are unaffected. Output-neutral:
  regenerating `generated/precomputed_layout.ts` produced zero diff across all
  38 scenes. WP-STRAT2 (the denser packer and shrink-priority) plugs into
  `selectStrategy` later without rewriting the dispatcher.

- Added `src/scene_runtime/layout/diagnostics/` (M2 / WP-DIAG1), the
  severity-graded diagnostic infrastructure and per-scene decision metadata, all
  output-neutral for layout positions. `severity_model.ts` implements the
  ratified severity table as closed typed data (`SEVERITY_DIAGNOSTIC_CODES`,
  `SEVERITY_TABLE`) plus `buildDiagnostic`, `severityRuleFor`, `failsBuild`, and
  `countBuildFailures`; each code maps to a fixed severity (`Error` /
  `Warning` / `Review-required`), `failBuild` flag, likely owner, YAML pointer
  level, trigger, and suggested fix. `payload.ts` defines the actionable payload
  (`ActionablePayload`, `AttemptedMove`) carried by `unresolved_label_overlap`
  and `unresolved_overlap` -- scene, zone, involved items, remaining overlap
  depth/area, available area, attempted moves, and a suggested YAML fix -- via
  `buildActionablePayload`. `decision_metadata.ts` defines `ZoneDecision` /
  `DecisionMetadata` and builders; `run_pipeline.ts` now populates a per-scene
  `DecisionMetadata` (current behavior: strategy `row`, packer not-needed,
  per-item shrink derived from `_shrunk_passes`) and exposes it on
  `PipelineResult.decisionMetadata`, separate from the diagnostics array. Added
  `tests/test_layout_diagnostics.mjs` asserting the two overlap Errors carry the
  full payload shape, plus the severity mapping and metadata builders. M4/M5/M6
  will emit the new codes; this task ships only the model, payload, and metadata
  infrastructure. Also applied three WP-CFG1 review cleanups (output-neutral):
  `phases.ts` `validate.mutatesPositions` is now accurately `true` (clamp still
  translates groups on overflow today; flips to `false` in M6), `horizontal_layout.ts`
  reads `config.defaultAlignStop` instead of the raw `layout_rules` fallback, and
  `run_pipeline.ts` `applyRuntimeOverrides` freezes its returned config.
- Added `src/scene_runtime/layout/config/` (M2 / WP-CFG1), the declarative LayoutConfig
  layer: `types.ts` declares `LayoutConfig`, `SpacingConfig`, `PackerConfig`, and
  `ZoneLayoutConfig`; `resolve_config.ts` provides `buildGlobalDefaults` (copies the
  canonical defaults out of `constants.ts`) and `resolveConfig`, which merges by the
  ratified precedence (global defaults -> scene `layout_rules` -> zone overrides ->
  placement-derived -> strategy-local) and returns a frozen config. The stage functions
  (`horizontal_layout.ts`, `vertical_layout.ts`, `layout_labels.ts`, `wrap_label.ts`) now
  read every tunable through `LayoutConfig` instead of importing constants directly; each
  keeps an optional trailing `config` parameter defaulting to `buildGlobalDefaults()` so
  direct callers stay byte-identical. Three flagged tunable conflicts were resolved and
  documented in `config/types.ts`: canonical `labelOffsetY` is 3.5 (the effective `?? 3.5`
  fallback, not the unused 4 in `DEFAULT_LAYOUT_RULES`); the duplicated `zone_gap` default
  consolidates to one `objectGap` (2); `ZONE_PADDING` splits into distinct
  `objectZonePadding` / `labelZonePadding` keys (both 1.5); and the two equal 0.3 collision
  tolerances share one `labelCollisionTolerance` key. This is output-neutral: the
  regenerated `generated/precomputed_layout.ts` is byte-identical across all 38 scenes.
- Added `src/scene_runtime/layout/phases.ts` (M2 / WP-CFG1), the phase registry that
  replaces the hardcoded 10-stage sequence in `run_pipeline.ts`. It defines the `Phase`
  interface (`name`, `mutatesPositions`, `run(ctx, config)`), `PHASE_ORDER` (prepare,
  resolve-metadata, measure, partition, place-horizontal, place-vertical, place-labels,
  resolve-collisions, validate, report), and a `runPhases` driver. `run_pipeline.ts` runs
  identity resolution once, then re-expresses the existing bounded convergence loop over the
  placement phases (re-enter only on new fittable diagnostics, cap at `maxPasses`). The
  `validate` phase wraps the existing `clamp_scene_bounds` behavior unchanged (the
  clamp->validate change and `validate_bounds.ts` rename remain M6/WP-VERT1), and
  `resolve-collisions` is a no-op pass-through slot reserved for M4/M5. Behavior is
  identical: same phase order, per-pass diagnostics, shrink step, and final assembly.
- Added `devel/ai_polish_review.mjs` (M2 / WP-VISAI1), the Claude visual-polish reviewer.
  It renders canonical 16:9 before/after PNGs per scene via the read-only renderer
  `tools/scene_to_png.mjs`, packages the images plus geometry-free scene metadata and a
  fixed visual-polish rubric into one Messages API request per scene (raw `fetch`, no SDK
  dependency), and saves a structured JSON verdict beside the scorecard report at
  `docs/active_plans/reports/ai_polish_review.json`. Each scene scores six rubric items
  (1-5) plus `overall_polish` (0-100), `confidence` (low|medium|high), `blocking_findings`,
  and `review_required`. The model is set by `CLAUDE_VISION_MODEL` (default
  `claude-opus-4-8`) so a model-name change needs no code edit. Report-only: it gates
  nothing and is not wired into the deterministic build. On missing `ANTHROPIC_API_KEY`,
  API failure, or a malformed verdict it emits `visual_review_unavailable`
  (`review_required: true`, routing to human review) and always exits 0; `--dry-run`
  exercises the full render + payload-assembly path with no network call, and
  `--show-payload` prints the request shape (base64 elided). Lives in `devel/` for now
  (relocate to `tools/` once the v3 SVG normalizer work lands). Usage, JSON schema, the
  escalation gate, and the 11-scene calibration set are documented in
  `docs/archive/decisions/ai_polish_review_calibration.md`.
- Added `src/scene_runtime/layout/geometry/types.ts` and
  `src/scene_runtime/layout/geometry/collision.ts` (M1 / WP-GEO1), the pure 2D AABB
  geometry core. `types.ts` declares the immutable `Vector`, `Aabb`, `Collision`, and
  `ResolutionCandidate` value types; `collision.ts` provides `aabbFromBounds`,
  `detectCollision` (returning `overlapVectorAtoB`, `separationForA`, `separationForB`),
  `buildResolutionCandidate`, and `sortResolutionOrder`. The geometry stays pure (no
  mutation); the label and object-placement layout phases consume it later and own all
  mutation. Covered by `tests/test_layout_geometry.mjs` (21 tests).
- Added `pipeline/precompute_layout.mjs` (M3 step 1 / WP-PRECOMP1), the build-time
  layout precompute generator. It runs the layout engine via `runPipeline` for every
  scene in the generated `SCENES` map at the canonical 16:9 frame (1920x1080) and emits
  `generated/precomputed_layout.ts`, exporting `PRECOMPUTED_LAYOUT` as a `scene_name`-keyed
  map of `{ final: ComputedItem[] }`. It depends only on the stable
  `runPipeline(scene, {library, assets, viewport})` signature and imports the generated
  `SCENES`, `OBJECT_LIBRARY`, and `ASSET_SPECS`. Output is deterministic (scenes and items
  sorted by name) so two builds are byte-identical. Wired into `build_github_pages.sh`
  immediately after `bash pipeline/build_generated.sh` so the generated artifacts it reads
  exist first. M0 (`tests/e2e/e2e_layout_parity_16x9.mjs`) proved running the engine at
  canonical 16:9 matches the live runtime layout, making the fixed-frame precompute a valid
  source of layout. WP-PRECOMP2 (browser consume) and WP-PRECOMP3 (runtime-engine retirement)
  are separate later tasks; this change only adds the generator and the build wiring.
- Added `tests/e2e/e2e_layout_parity_16x9.mjs`, the M0 / WP-FEAS1 precompute parity
  proof. For every scene in the generated `SCENES` map it runs the existing layout
  engine at the canonical 16:9 precompute viewport (1920x1080) and at a different-size
  16:9 live panel (1280x720) and diffs the full `ComputedItem[]` field-by-field,
  including `_top` and `_height`. It also confirms `SceneChange` keying by `scene_name`
  and runs a viewport sweep. Writes a reproducible report to
  `docs/active_plans/reports/m0_layout_parity_16x9.md` (viewport dimensions, sort order,
  serialization method, tolerance). Run with `node --import tsx
  tests/e2e/e2e_layout_parity_16x9.mjs`.

### Behavior or Interface Changes

- `tools/normalize_svg_v3.py` is an ingestion gate run before adding SVGs to `assets/`.
  It normalizes or rejects-with-reason; there is no silent partial success, no warning-only
  path, and no `--strict` toggle. Every rejection carries a stable 21-code reason so
  authors know exactly what to fix before re-submitting an asset.
- userSpaceOnUse gradients/patterns referenced by a transformed element are now
  transformed in sync during flattening: single-use cases bake the element transform into
  `gradientTransform`; shared gradients under differing transforms reject with a named
  reason code rather than silently losing color.

- M3 step 4 / WP-PRECOMP3: retired the runtime layout engine (`runPipeline`) from
  the shipped browser bundle. The production scene-render path now consumes only
  the build-time precomputed layout (`generated/precomputed_layout.ts`). Added
  `src/scene_runtime/layout/precomputed_result.ts` as the single production seam
  (`make_precomputed_result`, `resolve_precomputed_result`): it looks up
  `PRECOMPUTED_LAYOUT[scene_name]`, throws loudly on a missing entry, and
  assembles a renderer-ready `PipelineResult`. It imports `buildDecisionMetadata`
  directly from `diagnostics/decision_metadata.js` (not the layout barrel) so the
  production module graph drags in no engine call path. `src/protocol_host.tsx`
  dropped the `runPipeline` import, the `?layout=runtime` parity switch, the
  `LayoutMode`/`resolve_layout_mode` machinery, and its local
  `make_precomputed_result`, keeping only the precomputed path. The two other
  shipped entries that still rendered scenes via the engine were switched to the
  same seam: `src/protocol_host_entry.tsx` `mount_bench` and `src/dist_entry.tsx`
  `mount_scene_viewer` now call `resolve_precomputed_result`. Parity was proven in
  WP-PRECOMP2 (GO 38/38, consumed=match) before this removal. The engine stays on
  disk and remains build-only: `pipeline/precompute_layout.mjs` and tests still
  import it. Verified the built `dist/protocol_host.js`, `dist/scene_viewer.js`,
  and `dist/launcher.js` contain zero `runPipeline`/`run_pipeline` references and
  none of the engine pipeline-stage functions (`runPhases`, `horizontalLayout`,
  `verticalLayout`, `clampSceneBounds`, `scaleToRealWorld`, `resolveInheritance`);
  esbuild tree-shook the engine out of the shipped bundles. `tsc --noEmit` clean,
  329 Node tests pass, `test_letterbox_16x9.mjs` PASS (exact 16:9, items=9 across
  all viewports) against the rebuilt dist.

- M3 steps 2-3 / WP-PRECOMP2: the protocol host now renders inside an EXACT 16:9
  letterboxed frame and consumes the build-time precomputed layout by default.
  `src/style.css` makes `.scene-panel` a size container (`container-type: size`)
  and sizes `.scene-panel-inner` to `min(100cqw, calc(100cqh * 16 / 9))` with
  `aspect-ratio: 16 / 9`, forcing the largest exact-16:9 box that fits the panel,
  centered, with neutral `.scene-panel` bars (`#e8e0cc`) around it. This fixes the
  M0-review gap where header/guidance-bar heights left the panel slightly off
  16:9: a plain `width:100%` + `max-height:100%` box stays off-16:9 on a
  wider-than-16:9 panel (the explicit width wins), while the container-query
  `min()` keeps it exactly 16:9 in both the pillarbox (wide) and letterbox (tall)
  regimes. `.scene-panel-inner` is layout chrome, not a scene-content selector, so
  the container-query sizing passes `tools/check_css_content_policy.py`.
  `src/protocol_host.tsx` loads `PRECOMPUTED_LAYOUT[scene_name]` from
  `generated/precomputed_layout.ts` as the single production path (no runtime
  fallback ships to users); a missing entry throws loudly. The runtime
  `runPipeline` engine stays SELECTABLE behind `?layout=runtime` for parity
  proving only (WP-PRECOMP3 retires it). `make_precomputed_result` assembles a
  full `PipelineResult` from the precomputed `final` plus the live scene; the
  renderer reads only `final` and `scene`, so the other engine-internal fields are
  explicit empties (no cast, no `runPipeline` call). The M0 parity script
  `tests/e2e/e2e_layout_parity_16x9.mjs` gains a consumed-artifact check that diffs
  `PRECOMPUTED_LAYOUT[scene].final` against the runtime engine at the canonical
  16:9 frame; it reports GO 38/38 with every scene `consumed=match` after the
  M4/M5/M6 engine changes. New `tests/playwright/test_letterbox_16x9.mjs` proves
  against the built `dist/` that `#scene-root` is exact 16:9 at four bracketing
  viewport aspects (wide, tall, 16:9, 16:10) and that every item's scene-percent
  center is invariant across viewports (only the bars/scale change), with
  before/after screenshots saved under `test-results/letterbox_16x9/`.

- M5 / WP-STRAT2: overflow packer plus derived shrink priority, plugged into the
  WP-STRAT1 `selectStrategy` seam. New `src/scene_runtime/layout/strategies/pack_strategy.ts`
  is a single-row, order-preserving, deterministic packer (four reduced phases:
  width approximation, row placement, compaction-only-on-overflow, whitespace
  expansion) that applies NON-UNIFORM, priority-based shrink plus gap compaction
  where the row strategy's uniform shrink bottoms out at MIN_SCALE and emits an
  overflow diagnostic. The dispatcher (`horizontal_layout.ts`) now probes the row
  layout per zone (`probeRow`) and engages the packer on the positive trigger:
  required row scale below `config.packer.thresholdScale` (0.75) OR overflow
  (negative gap / out of bounds). Shrink priority is derived (never authored):
  semantic kind first (decoration/waste shrink before tools before
  plate/equipment), footprint second, `placement_name` tiebreak; the primary
  teaching object's scale is preserved (weighted heaviest in the lexicographic
  cost `[primaryWeightedShrinkPct, orderViolations, gapDeficit, overhang]`). A zone
  still unfittable at MIN_SCALE emits an actionable `unresolved_overlap` Error
  (`buildActionablePayload`). The per-zone packer decision is recorded in
  `DecisionMetadata` via the new `buildPackZoneDecision`
  (selectedStrategy `pack`, requiredRowScale, packerThreshold, packerAttempted,
  packerResult, rowsCreated, shrinkApplied). This CHANGES layout output by design:
  overloaded zones are packed instead of overlapping. Diagnostic effect over 38
  scenes at 1920x1080: scenes hitting `max_iterations_reached` dropped 19 -> 4,
  `tab_stop_overflow` 35 -> 0; `hood_basic` and `sample_prep_bench` now converge in
  1 pass. The 4 remaining non-converged scenes are legitimate: `hood_workspace` and
  `seeding_workspace` are M6 vertical-escape cases (`item_escapes_zone_vertically`),
  and `adversarial_overflow_smoke` plus `imaging_bench` are genuine authoring
  overload (a label wider than its zone, or far more items than fit), each now
  surfaced as an actionable `unresolved_overlap`. The packer never stacks rows by
  mutating `_y` (vertical recomputes `_y` from the zone baseline, which would wipe
  it); the elkjs rectpacking "rows" collapse to one row and the compaction phase
  carries the work. Added the `packer: overloaded zone packs with no negative gap,
  primary keeps scale` unit test.

- M4 / WP-LABEL1: global 2D label de-overlap with label-vs-artwork avoidance. The
  `resolve-collisions` phase (previously a no-op slot) now runs a new
  `resolveLabelCollisions` pass in `layout_labels.ts` after labels are placed. It
  builds label and object-artwork AABBs via the M1 geometry core
  (`detectCollision`, `buildResolutionCandidate`) and resolves overlaps in two
  phases: Phase A clears every label off a NEIGHBORING object's artwork (a check
  the legacy adjacent-pair nudge never did) using the geometry separation vectors,
  preferring a horizontal nudge and falling back to a discrete, zone-bounded row
  drop; full containment (`Collision.aInB`/`bInA`) forces a row drop since one
  interval step cannot clear it. Artwork boxes are obstacles and never move, so
  object positions are unchanged. Phase B re-separates any label-label overlap
  with the proven distinct-row stagger (a row drop is the only label-label move,
  preserving Phase A's horizontal separation and the legacy
  `label_collision_residual = 0` semantics). Artwork avoidance has priority over
  label spacing; an artwork move is scored to introduce the least new label-label
  overlap. The sweep is a fixed pass budget (`config.labelMaxResolvePasses`,
  default 4) that stops early when clear, with deterministic tie-breaks (sort by
  `_labelX` then `placement_name`), so identical input yields identical label
  coordinates. End states are classified into the severity stream
  (`run_pipeline` surfaces them on `PipelineResult.severityDiagnostics`): a label
  still overlapping after the budget -> `unresolved_label_overlap` Error (built
  with `buildDiagnostic` + `buildActionablePayload`: scene, zone, involved labels,
  remaining overlap depth/area, available area, attempted moves, suggested fix); a
  clear-but-drifted label -> `poor_label_alignment` Warning; a dense row-dropped
  cluster -> `possible_overload` Review-required. These are report-only (no build
  gates on `severityDiagnostics` yet, matching M6's `unresolved_overlap`). Output
  changes by design: `generated/precomputed_layout.ts` was regenerated and its
  only changed values are `_labelX`/`_labelY` (object geometry is byte-identical).
  Across the 38-scene 16:9 sweep this drops label-vs-artwork overlaps from 24 to 9
  while keeping the engine's `label_collision_residual` at 0; the residual 9
  artwork overlaps and the same-zone tight-zone label overlaps are raised as 5
  `unresolved_label_overlap` Errors (the genuinely unfittable cases, e.g. a label
  on a zone floor under the oversized `centrifuge_spin` body) plus 12
  `poor_label_alignment` Warnings. Added `tests/test_layout_label_resolve.mjs`
  (clean-scene no-op, label-vs-artwork clearance, determinism, the unresolved
  Error, and the artwork-priority rule). New config tunable `labelMaxResolvePasses`
  (4) and a `LabelWork.row` field feed the row-aware classifier.
- M6 / WP-VERT1: aspect-aware vertical auto-fit replaces the silent scene-bounds
  clamp. `vertical_layout.ts` now shrinks a too-tall item so it sits inside its
  zone instead of escaping: the fit is anchor-aware (a bottom-anchored bottle
  pinned near the zone bottom shrinks when it overshoots the zone TOP, not only
  when its raw height exceeds the full zone span), preserves the asset aspect
  exactly (width and height scale by the same factor, never distorted), and is
  floored so the applied placement scale never drops below `config.packer.minScale`
  (MIN_SCALE). The `validate` phase (`clamp_scene_bounds.ts`) is now REPORT-ONLY:
  it no longer translates an out-of-bounds zone group by (dx, dy); it measures the
  overshoot, keeps a `zone_clamped_to_bounds` measurement in the runtime stream,
  and emits a structured `unresolved_overlap` Error (via `buildDiagnostic` +
  `buildActionablePayload`: scene, zone, involved items, remaining overlap
  depth/area, available area, attempted moves, suggested fix) for any zone whose
  items still escape `scene_bounds` at the MIN_SCALE floor. `phases.ts`
  `validate.mutatesPositions` is set back to `false` (it no longer mutates
  positions) with an updated comment; `run_pipeline.ts` surfaces the per-scene
  `unresolved_overlap` Errors on a new `PipelineResult.severityDiagnostics` array,
  kept separate from the closed-kind `diagnostics` stream. Output changes by
  design: `generated/precomputed_layout.ts` was regenerated. Across the 38-scene
  16:9 baseline sweep this drops `max_iterations_reached` from 30 scenes to 19,
  `item_escapes_zone_vertically` from 17 occurrences to 2 (both the genuine
  unfittable `rear_right_incubator` in `hood_workspace` and `seeding_workspace`,
  now correctly raised as `unresolved_overlap` Errors), and `zone_clamped_to_bounds`
  from 21 to 3. Every remaining `max_iterations_reached` scene is now driven by
  horizontal `tab_stop_overflow` / `zone_overflow_negative_gap`, which the M5
  packer owns; `sample_prep_bench` and `hood_basic` fit vertically (no vertical
  escape, no bounds clamp) but retain that residual horizontal tab overflow, while
  `staining_bench` converges cleanly. FOLLOW-UP for the human: the plan renames
  `clamp_scene_bounds.ts` -> `validate_bounds.ts` (and `clampSceneBounds` ->
  `validateBounds`); an agent cannot run `git mv`, so the behavior change landed in
  place and the rename plus import updates remain a manual step.

### Fixes and Maintenance

- Gradient-under-transform color-loss fix (WP-15 / imagehash finding): the visual-regression
  harness (imagehash, chromium + firefox) flagged a class of assets that rendered grey after
  v3 normalization. The first fix baked the element transform into `gradientTransform` before
  removing the element transform attribute. NOTE (corrected 2026-06-08): a browser recheck
  proved this first fix was INSUFFICIENT -- cpu.svg still greyed (phash ~40, dhash ~41 in
  both engines). See the 2026-06-08 entry for the full root cause (the crop-to-origin shift
  was added to `userSpaceOnUse` gradient coordinates, and stroke-width was not scaled on
  flatten) and the corrected, render-verified fix.
- Gradient-under-transform color-loss: CORRECTED root cause and fix (browser render as ground
  truth, chromium + firefox). The earlier "bake element matrix into `gradientTransform`" change
  was geometrically correct but two later passes still broke the render: (1) `shift_element`
  added the crop-to-origin `(dx,dy)` directly to every `cx/cy/x1/y1/x2/y2`, including
  `userSpaceOnUse` gradient/pattern coordinates -- but those coordinates resolve THROUGH the
  paint transform, so the raw-coordinate shift was re-scaled by the baked matrix and the paint
  landed off the geometry (single-stop collapse); it also corrupted `objectBoundingBox` 0..1
  fractions. (2) transform flattening baked the element matrix into geometry but never scaled
  `stroke-width`, so a stroke authored under a 0.4x scale rendered ~2.4x too thick and filled
  the hole-cutouts of cpu.svg's grid mesh, hiding the colored layer beneath. Fix:
  `shift_element` now leaves gradient/pattern coordinate attributes untouched -- it prepends
  `translate(dx,dy)` to the `userSpaceOnUse` paint's transform and leaves `objectBoundingBox`
  paints alone -- and `_flatten_one` scales `stroke-width` (attr and inline style) by the
  matrix's uniform scale factor (guarded by the existing non-uniform-stroke reject). Verified:
  a minimal probe (one `userSpaceOnUse` linearGradient under `scale(2)translate(...)`) went
  from collapsed-solid to render-identical; cpu.svg now renders the full colorful CPU in both
  engines (dhash 41 -> 33; residual phash 40 is the no-crop reframe of the original's
  content-clipping viewBox, not color loss); genomesequencer-3.svg (phash 10/dhash 2),
  scanning-electron-microscope-sem.svg (phash 2/dhash 1), and centrifuge-big.svg (phash
  4/dhash 1) all render render-identical. See
  `docs/active_plans/reports/svg_gradient_fix_verification.md`.
- Visibility bbox fix: elements with `style="display:none"` or `fill:none;stroke:none` are
  now excluded from the rendered bbox computation. Previously they inflated the viewBox,
  causing unnecessary whitespace. Invisible elements are stripped or flagged, not measured.
- Arc transform ZeroDivision hardening: the arc-under-matrix SVD path now guards against
  degenerate matrices (determinant near zero) that previously raised `ZeroDivisionError`
  on malformed wild SVGs.
- Non-UTF-8 input hardening: files with non-UTF-8 encoding now fail with `PARSER_ERROR`
  rather than propagating a UnicodeDecodeError traceback.

### Decisions and Failures

- normalize_svg_v3.py design decisions (WP-4a summary): single normalize-or-reject
  path with no modes -- no `--strict`, no cleanup/style toggles; diagnostics never
  change the verdict. Unsupported features (text, unexpanded `<use>`, filter, mask,
  marker, complex clipPath, foreignObject, external resources, embedded raster,
  DOCTYPE/entities, scripts/handlers/animation, geometry-affecting CSS, and
  input-altering parser recovery) all reject with a reason code. Text rejection (A5):
  authoring rule is convert text to paths before ingestion; no zero-size bbox fallback.
  Tier C features (id shortening, gradient dedup, group collapse, point reduction) are
  non-goals; enforced by behavior tests, not grep. Floor-shadow (D1) does not affect
  the gate verdict. v2 stays until parity is proven on corpus; corpus re-normalize and
  CI ingestion gate are separate follow-up decisions for the human.
- Shapely adopted (not hand-rolled) for clip intersection (WP-3e decision): writing a
  correct polygon-clip intersection from scratch introduces its own correctness risk
  (edge cases, degenerate geometry, winding-order bugs). Shapely is a well-tested
  computational geometry library already in `pip_requirements.txt`. The decision is to
  depend on it and reject (not silently skip) when it is unavailable.
- Data-driven next investment: complex clipPath is the number-one ingestion blocker.
  Wild-corpus run: 1120 of 2404 rejections (~47%) are `CLIPPATH_UNSUPPORTED_COMPLEX`;
  50 of the 74 rejected committed assets fail for the same reason. Widening the
  simple-clip allowlist (multi-subpath rects, nested clips from common editors) is
  the highest-value follow-up for the human to consider.
- M0 parity gate result: GO. All 38 emitted scenes match bit-for-bit (max abs delta 0,
  no epsilon needed) between the canonical 16:9 precompute and the live 16:9 panel, so
  layout can move to compile time behind the 16:9 contract. Tolerance chosen: 1e-9
  absolute (IEEE-754 noise only); exact equality is the expectation because the only
  viewport-dependent term in `vertical_layout.ts` is `viewport.w / viewport.h`, identical
  for any 16:9 size. `long_labels_smoke` is the sole excluded scene: it fails scene
  validation (placement references unknown object `dmf_bottle`) and is therefore absent
  from `SCENES` (`SCENES_SKIPPED = 1`), so it never lays out; the exclusion is unrelated
  to viewport aspect. The viewport sweep gates only the 16:9 rows (all move zero fields);
  off-16:9 rows are contrast controls and show full per-aspect reflow (the convergence
  loop's shrink decision keys on `item_escapes_zone_vertically`, which depends on
  `_height`), documenting exactly why the 16:9 lock is needed rather than failing the
  gate. Re-confirmed the static-layout evidence: `LayoutMove` no-op
  (`scene_op_deps.ts`), `ObjectStateChange` appearance-only, no resize listener
  (`protocol_host.tsx` measures `#scene-root` once), fixed placement set per scene load.

### Developer Tests and Notes

- normalize_svg_v3.py test suite (milestones M1-M3, WP-3c, WP-3e): 160 pytest cases
  in `tests/test_normalize_svg_v3.py` covering: bbox/arc/matrix/transformArc pure
  functions; shape->path bbox equality; precision (fmt_precise); F8 `<style>` url(#id)
  ref rewrite; S1 ref-integrity; reject-fixtures for each unsupported feature with the
  correct reason code; behavior tests confirming Tier-C absence; the canonical geometry
  invariant; simple-clipPath flattening (A6); gradient/pattern userSpaceOnUse sync;
  arc ZeroDivision + non-UTF-8 PARSER_ERROR hardening; visibility bbox exclusion;
  and 13 D1 floor-shadow tests. Fixture manifest:
  `tests/fixtures/svg_normalizer/expected_bboxes.json`.
- E2E wild runner (WP-4b): `tests/e2e/e2e_normalize_svg_wild.py` runs the
  normalize-or-reject classifier over 3125 wild SVGs (bioicons, lab icons, UI icons).
  Final result: 721 normalize, 2404 reject, 0 crashes. Per-file verdicts saved to
  `docs/active_plans/reports/normalize_svg_v3_wild_verdicts.{json,md}`.
- Parity report (WP-4b): v2 vs v3 on the 102 committed `assets/` SVGs -- 27 normalize
  under v3 at this stage; the rest reject (primarily complex clipPath). Report at
  `docs/active_plans/reports/normalize_svg_v3_parity.md`.
- Visual-regression harness (WP-12): imagehash perceptual hash comparison across
  chromium + firefox for every normalize-passing asset. Detected the gradient-under-
  transform color-loss bug (see Fixes). Report at
  `docs/active_plans/reports/svg_visual_regression.md`.
- Synthesis findings (WP-14): `docs/active_plans/reports/normalize_svg_v3_findings.md`
  summarizes what the 3125-SVG corpus + imagehash harness revealed: rejection breakdown
  by code, the gradient bug root cause, the complex-clipPath dominance, and the
  recommended next-investment ranking.
- M7 / WP-VALID1 closeout for the compile-time layout-engine plan: cleared accumulated
  Prettier drift with `prettier --write` (output-neutral -- `generated/precomputed_layout.ts`
  regenerated byte-identical, md5 `93369602c8faa50ee81edc9b0c5dbb71`, across both a regen and a
  full `bash build_github_pages.sh`); the full Node suite (327 pass, 2 skipped) and all six
  `check_codebase.sh` steps pass. Re-ran `tests/e2e_layout_diagnostics_baseline.mjs`: seven of
  the eight named scenes converge clean with zero diagnostics, and only `seeding_workspace`
  carries Warning/structural residuals (no Error-severity codes anywhere). Captured 16:9
  after-screenshots for the eight named scenes into `test-results/m7_after/`, ran the
  report-only Claude visual-polish reviewer over the 11-scene calibration set (credentials
  absent -> `visual_review_unavailable` for all, routing to human review;
  `docs/active_plans/reports/m7_ai_polish_review.json`), and filled the scene-by-scene evidence
  table in `docs/active_plans/reports/m7_wp_valid1_evidence_table.md`. Same-tier object-overlap
  evidence (`docs/active_plans/reports/m8_same_tier_overlap_evidence.md`) found no genuine
  same-`depth_tier` real-asset overlap, so M8 stays deferred. The `tools/scorecard_m2.mjs`
  bbox scorecard could not run (stale `src/main.ts` dependency removed by the scene-viewer
  refactor); flagged for the human and replaced as the regression signal by the per-scene
  rendered bbox stats. Refreshed `docs/specs/LAYOUT_ENGINE.md` with the compile-time model and
  known limitations; cleared the resolved layout-drift items in `docs/TODO.md`
  (electrophoresis_bench, heat_block_bench, passage_hood_detachment_microscope_view).

## 2026-06-05

### Additions and New Features

- Extended `docs/archive/decisions/tooling_evaluation.md` with a "Browser UX
  affordance layer" section answering the sharper question of what simplifies the
  incomplete browser UI. Finding: no app framework helps; the browser is already
  fully data-driven, and the gap is three missing gesture controls (`adjust`, `drag`,
  `select`; `adjust` has 44 unplayable authored uses), hand-rolled working gestures,
  and stubbed scene operations (`TimedWait`, `LayoutMove`, asset background). Top
  recommendation: a `src/protocol_ui/` affordance layer mapping interaction to control
  to step-machine handler, with Floating UI for object-anchored coach marks and one
  headless library (Kobalte preferred over Ark UI) for widget internals. Evaluates
  `@thisbeyond/solid-dnd`, solid-motionone, svg-pan-zoom, Zag.js, `@dschz/solid-flow`,
  and SVG.js (rejected for scene objects per contract item 3). Includes a "How to
  obtain the code" subsection with npm install and import examples.
- Added a "Layout engine helpers (SVG placement)" section to
  `docs/archive/decisions/tooling_evaluation.md`. Finding: do not replace the
  deterministic zone-based row engine; most FOSS "SVG placement" tools are graph,
  diagram, drag, or collision tools. Two binding constraints recorded: output must stay
  deterministic (clean scenes are byte-identical; force/stress solvers are
  non-deterministic unless seeded) and any helper must be a pure pipeline stage emitting
  the existing `ComputedItem` shape. Verdicts: SAT.js (adopt-candidate, deterministic
  collision utility for the hand-rolled `layout_labels.ts` geometry), elkjs and D3-force
  (conditional, single-zone solver / seeded relax post-pass only), rectangle-packer
  (conditional, inventory surfaces only), Cytoscape.js / Dagre (skip for scene;
  authoring or debug diagrams only).
- Precision pass on `docs/archive/decisions/tooling_evaluation.md` to avoid
  overstating what is missing or forbidden: SVGO retagged "skip unless folded into the
  existing pipeline" (not "already done"); `select` corrected to working via the
  click-to-select promotion in `protocol_host.tsx` (not "ring only, no commit"), so
  three of five gestures work and only `adjust`/`drag` lack a control; `TimedWait`
  reworded from "stub" to minimal-but-observable via a subsequent state write; SVG.js
  changed to reject-for-placement / conditional-for-subpart-internals (contract item 3
  allows custom subpart geometry); localStorage gains a note that progress persistence
  needs a separate restore test because the canonical walkthrough starts from cleared
  storage. Final ranking revised accordingly.
- Added a "TypeScript tooling gaps (support, not replace)" section to
  `docs/archive/decisions/tooling_evaluation.md` (ts-pattern, fast-check,
  Playwright `toHaveScreenshot`, @axe-core/playwright, Knip, TypeDoc, API Extractor,
  ts-morph), with verdicts checked against the code rather than taken from the external
  review. Key correction: ts-pattern was downgraded from adopt-candidate to conditional
  because the repo already enforces compile-time exhaustiveness with a `never` default
  (`src/scene_runtime/protocol/scene_operations.ts:127`, `validators.ts`), so its
  headline pitch is already covered dependency-free. fast-check confirmed absent (real
  gap) and runner-agnostic under `node --import tsx --test`; `toHaveScreenshot`
  confirmed available via the existing `@playwright/test` devDependency (no new dep)
  with zero current uses. Closed sets, the click-to-select promotion
  (`protocol_host.tsx:326`), and the test runner were all verified in source.
