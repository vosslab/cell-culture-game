# File structure

## Top-level layout

| Path                                                                              | Purpose                                                                                                                                                                                           |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [README.md](../README.md)                                                         | Project overview and quick start                                                                                                                                                                  |
| [AGENTS.md](../AGENTS.md)                                                         | AI agent coding rules and pointers                                                                                                                                                                |
| [CLAUDE.md](../CLAUDE.md)                                                         | Claude Code rule manifest (loads style docs)                                                                                                                                                      |
| [VERSION](../VERSION)                                                             | CalVer version string                                                                                                                                                                             |
| [LICENSE.LGPL_v3](../LICENSE.LGPL_v3)                                             | Code license                                                                                                                                                                                      |
| [LICENSE.CC_BY_4_0](../LICENSE.CC_BY_4_0)                                         | Content license                                                                                                                                                                                   |
| [build_github_pages.sh](../build_github_pages.sh)                                 | Canonical production build into `dist/`                                                                                                                                                           |
| [run_web_server.sh](../run_web_server.sh)                                         | Build then serve `dist/` on local loopback                                                                                                                                                        |
| [check_codebase.sh](../check_codebase.sh)                                         | Aggregate lint, typecheck, and test gate                                                                                                                                                          |
| [render_liquid_volume_contact_sheet.sh](../render_liquid_volume_contact_sheet.sh) | Rebuilds published assets, then renders all five variable-volume families into one HTML/PNG contact sheet                                                                                         |
| `run_fast_checks.sh`                                                              | Umbrella fast gate: build, `check_codebase.sh`, `pytest`, content validation (no browser sweep)                                                                                                   |
| [run_playwright_tests.sh](../run_playwright_tests.sh)                             | Front door for every browser test: build as needed, then run `npx playwright test` against `playwright.config.ts` (`.spec.ts` files, including the protocol walker sweep spec)                    |
| [source_me.sh](../source_me.sh)                                                   | Bash environment for Python 3.12                                                                                                                                                                  |
| [package.json](../package.json)                                                   | Node dev dependencies and npm scripts                                                                                                                                                             |
| [tsconfig.json](../tsconfig.json)                                                 | Repo-root TypeScript compiler config (strict)                                                                                                                                                     |
| [tsconfig.lint.json](../tsconfig.lint.json)                                       | Wider typecheck covering `tests/` and `tools/`                                                                                                                                                    |
| `playwright.config.ts`                                                            | Playwright test-runner config: `testDir: tests/playwright`, `testMatch: **/*.spec.ts`, single chromium project, `webServer` builds then serves `dist/` on one shared random port for every worker |
| [pip_requirements-dev.txt](../pip_requirements-dev.txt)                           | Python dev dependencies (pytest, pyflakes)                                                                                                                                                        |
| [eslint.config.js](../eslint.config.js)                                           | ESLint flat config                                                                                                                                                                                |
| [REPO_TYPE](../REPO_TYPE)                                                         | Repo type marker (`typescript`)                                                                                                                                                                   |

## Key subtrees

### `src/` - Authored TypeScript runtime

Browser entry points, scene runtime, and shell HUD. All authored; nothing
under `src/` is generated.

```text
src/
+- dist_entry.tsx              -- bundle entry; DOM-presence router
+- launcher_entry.tsx          -- launcher bundle entry
+- protocol_host_entry.tsx     -- protocol-host bundle entry
+- protocol_host.tsx           -- wires pipeline, renderer, step machine, HUD
+- index.html                  -- bench page (smoke target)
+- scene_viewer_template.html  -- scene viewer HTML template (copied to dist/scene_viewer.html)
+- style.css                   -- stylesheet (copied to dist/)
+- launcher/
|  +- index.html               -- launcher HTML page
|  +- protocol_launcher.tsx    -- Solid protocol-selector component
|  `- main.tsx                 -- launcher Solid mount
+- scene_runtime/
|  +- layout/                  -- multi-pass layout pipeline
|  |  +- run_pipeline.ts       -- top-level pipeline runner
|  |  +- types.ts              -- PipelineResult, ComputedItem, layout types
|  |  +- constants.ts          -- DEFAULT_VIEWPORT, shrink factor
|  |  +- phases.ts             -- phase registry: named phase sequence with read/mutate boundaries
|  |  +- lower_semantic_zones.ts -- coordinate-free source zones -> internal bounds and baselines
|  |  +- vertical_footprint.ts -- shared object-plus-label vertical extent measurement
|  |  +- reflow_zones.ts       -- measured zone bands for vertical placement; no item mutation
|  |  +- geometry/              -- pure 2D AABB geometry core (no layout state)
|  |  |  +- types.ts            -- Vector, Aabb, Collision, ResolutionCandidate value types
|  |  |  `- collision.ts        -- aabbFromBounds, detectCollision, buildResolutionCandidate, sortResolutionOrder
|  |  +- config/                -- LayoutConfig resolution (global defaults -> scene -> zone -> strategy)
|  |  |  +- types.ts            -- LayoutConfig and related config types
|  |  |  +- resolve_config.ts   -- config precedence resolver
|  |  |  `- index.ts            -- barrel export
|  |  +- diagnostics/           -- severity-graded typed diagnostics and decision metadata
|  |  |  +- severity_model.ts   -- Error / Warning / Review-required severity types
|  |  |  +- payload.ts          -- typed diagnostic payload shapes
|  |  |  +- decision_metadata.ts -- per-scene decision metadata (strategy, packer, shrink, config)
|  |  |  +- offcanvas.ts        -- off-canvas classifier: fully_off_canvas / partial_overflow (report-only, never gates)
|  |  |  `- index.ts            -- barrel export
|  |  +- strategies/            -- PlacementStrategy seam and implementations
|  |  |  +- placement_strategy.ts -- PlacementStrategy interface
|  |  |  +- row_strategy.ts     -- default row strategy
|  |  |  +- pack_strategy.ts    -- overflow packer (engages below threshold or on overflow)
|  |  |  `- index.ts            -- barrel export
|  |  `- (bind_objects, normalize_schema, resolve_inheritance, scale_to_real_world,
|  |      group_by_zone, horizontal_layout, vertical_layout, layout_labels,
|  |      clamp_scene_bounds, footprint, wrap_label, index).ts
|  +- protocol/                -- step machine and protocol drivers
|  |  +- affordance.ts         -- pure affordance-kind mapping (compute_affordance_kind, affordance types)
|  |  +- gesture_registry.ts   -- GESTURE_REGISTRY: per-gesture affordance contract + dispatch_gesture, scene_click_to_command
|  |  +- resolve_entry_scene.ts -- entry-scene resolution + empty-scene guard
|  |  +- target_adapter.ts     -- protocol-target -> DOM identity adapter (resolve_to_placement/object, AmbiguousTargetError)
|  |  +- flatten_sequence_runner.ts -- rejects nested/repeated leaves and flattens unique direct mini-protocols into one chained step flow
|  |  +- step_machine.ts       -- pure step machine (no DOM)
|  |  +- validators.ts         -- interaction and step validator dispatch
|  |  +- authored_value_check.ts -- load-time authored-value guard for target_with_value / final_state_matches
|  |  +- gesture_affordance_check.ts -- load-time invariant: authored gesture must be registered + wired (UnaffordancedGestureError)
|  |  +- target_existence_check.ts -- load-time invariant: authored target must exist in the scene
|  |  +- scene_operations.ts   -- routes the five SceneOperation primitives to injected store-backed deps
|  |  +- scene_op_deps.ts      -- SceneOpDeps interface + store-backed factory
|  |  +- walker_debug.ts       -- read-only walkthrough evidence: active target, stateRevision, and lastStateDelta
|  |  +- click_resolver.ts     -- DOM click -> step machine
|  |  `- emitter.ts            -- ProtocolShellEmitter, RuntimeEmitterHandle
|  +- state/                   -- Solid signal store for shared scene state
|  |  `- scene_store.ts        -- active Solid projection plus target-keyed durable protocol session archive; owns start_session/reconcile_scene/snapshot_declared_state
|  `- renderer/                -- Solid DOM rendering from PipelineResult
|     +- render_scene.tsx      -- public Solid mount facade (mounts SceneView)
|     +- affordance_candidates.ts -- renderer-layer candidate enumeration (enumerate_candidate_targets)
|     +- scene_view.tsx        -- Solid SceneView (bg, items, labels, guards)
|     +- scene_item.tsx        -- Solid SceneItem (per-item + missing-svg placeholder)
|     +- subpart_hit_surface.tsx -- declaration-geometry exact-subpart/group hit surfaces and focused affordances
|     +- visual_state_resolver.ts -- state + visual_states -> renderable description
|     +- render_background.ts  -- background (gradient or asset)
|     +- structural_guards.ts  -- six layout validation guards
|     +- inject_svg.ts         -- fetched SVG injection, instance ID namespacing, and compiled liquid-region binding
|     +- svg_manifest_loader.ts -- runtime SVG manifest fetch/cache layer
|     +- material_acceptance.ts -- shared registry-backed material-name acceptance predicate
|     +- liquid_paint.ts       -- generated-handle liquid color and gravity-part writer
|     +- oklch_shade.ts        -- role-based material shade derivation
|     `- index.ts              -- barrel: renderScene, mountScene, SceneView, SceneItem
`- shell/
   +- adapter/
   |  `- types.ts              -- closed seam: ProtocolConfig, ShellViewSnapshot, events, ops
   +- signals.ts               -- Solid signal helpers + subscribeEmitterToSnapshot
   +- hud/
   |  +- protocol_hud.tsx      -- owns the student-facing shell composition
   |  +- type_input.tsx        -- visible type-input affordance (data-type-input / data-type-commit)
   |  `- set_point_editor.tsx  -- shared numeric set-point editor for the adjust gesture (data-adjust-input / data-adjust-commit)
   `- regions/
      +- authored_tip.tsx      -- optional authored technique tip
      +- guidance_bar.tsx      -- current action, recovery, and completion
      +- step_counter.tsx      -- labeled completed/total counter
      `- step_outline.tsx      -- read-only ordered step cards
```

The framed interface uses six named DOM regions in `src/protocol_host_template.html`:
`header` (tips + counter), `scene` (bounded 16:9 panel), `outline` (step list),
and `guidance` (teal prompt bar). `#shell-root` is a sibling of `#scene-root`,
never an ancestor.

### `pipeline/` - Codegen and build scripts

Every script that emits to `generated/`, assembles bundles, or produces
`dist/` artifacts. Invoked by `package.json` pre-hooks and
`build_github_pages.sh`.

| File                                                           | Purpose                                                                                                                                                                                                                                  |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [gen_object_library.py](../pipeline/gen_object_library.py)     | `content/objects/` YAML -> `generated/object_library.ts`                                                                                                                                                                                 |
| [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py)         | `assets/**/*.svg` -> `generated/svg_manifest.ts` final URL mapping and source-versus-compiled publication into `dist/assets/svg/`                                                                                                        |
| `pipeline/gen_liquid_regions.py`                               | Validated gravity-part material SVG -> compiled SVG plus aggregate opaque-handle manifest                                                                                                                                                |
| [gen_scene_index.py](../pipeline/gen_scene_index.py)           | Scene YAML -> `generated/scenes.ts` + `generated/scene_manifest.json`; `--missing-svg=strict                                                                                                                                             | placeholder`(default`placeholder`) |
| [gen_protocols.py](../pipeline/gen_protocols.py)               | Protocol YAML -> `generated/protocols.ts` + `generated/protocols_index_slim.ts` + `generated/protocol_materials.ts` (per-protocol material registry and validated typed `initial_state` from each package)                               |
| [entity_decode.py](../pipeline/entity_decode.py)               | Codegen helper: `decode_entities()` maps authored HTML entities (`&micro;` etc.) to Unicode glyphs at emit time; imported by `gen_protocols.py` and `gen_object_library.py` so `generated/**` carries the glyph while source stays ASCII |
| [gen_flow_view.py](../pipeline/gen_flow_view.py)               | Protocol YAML -> `generated/flow_views/<protocol_name>.txt`, a per-protocol audit view (click path, gestures, state changes, transitions); not the design source, see [PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md)   |
| [build_protocol_index.py](../pipeline/build_protocol_index.py) | Protocol index build helpers                                                                                                                                                                                                             |
| [list_protocols.py](../pipeline/list_protocols.py)             | Reads `PROTOCOLS_INDEX`; `emit` writes one `dist/<name>.html` per protocol                                                                                                                                                               |
| [scene_inheritance.py](../pipeline/scene_inheritance.py)       | Scene YAML inheritance resolution library (imported by gen_scene_index)                                                                                                                                                                  |
| [build_main_bundle.mjs](../pipeline/build_main_bundle.mjs)     | esbuild Node API: bundles launcher and protocol-host entries                                                                                                                                                                             |
| [precompute_layout.mjs](../pipeline/precompute_layout.mjs)     | Runs the layout engine for every scene at canonical 16:9 (1920x1080) -> `generated/precomputed_layout.ts` (`{ final: ComputedItem[] }` per scene). Runs after `build_generated.sh`.                                                      |

### `content/` - Authored YAML

All authored YAML; nothing under `content/` is generated or gitignored.

```text
content/
+- objects/                    -- reusable object definitions by kind
|  +- bottle/, equipment/, flask/, pipette/, plate/, rack/, waste/, decoration/
+- base_scenes/                -- shared base scenes (bench, hood, microscope, etc.)
+- protocols/
|  +- cell_culture/            -- cell culture mini-protocols and runners
|  +- sdspage/                 -- SDS-PAGE mini-protocols, including direct-leaf batch preparation and loading packages
|  `- runners/                 -- sequence-runner protocols
+- objects_quarantine/         -- quarantined objects pending restoration review
`- base_scenes_quarantine/     -- quarantined base scenes pending restoration review
```

Each mini-protocol folder contains:

```text
content/protocols/<cluster>/<protocol_name>/
+- protocol.yaml               -- protocol_type, entry_step, learning block, steps
+- materials.yaml              -- material definitions for this protocol
`- scenes/                     -- per-protocol scene YAML overrides
```

`content/protocols/sdspage/` owns the SDS batch packages
`sdspage_prepare_sample_mix_batch` and `sdspage_load_samples_batch`; they are
not reusable nested runners. Their `initial_state` declarations seed the
normalized `microtube_rack_8` slots used by the associated SDS scenes.

### `validation/` - YAML and scene validators

Standalone Python validators. Entry point: [validate.py](../validation/validate.py).

```text
validation/
+- validate.py                 -- aggregate entry: runs every validation stage
+- yaml_schema/                -- schema + cross-field rules for protocol, object, scene YAML
+- stepper/                    -- step-flow walker: shared StateMap, initial-state seeding, scene operations, and material transfer ledger
+- svg/                        -- SVG asset audit plus semantic-layer and object-selected taxonomy validators
+- manual/                     -- human-readable protocol manual renderer
+- scene_lint/                 -- pre-render failure predictor (Group A BLOCKED, Group B advisory)
+- scene_design/               -- composition scorecard (weighted metrics, advisory only)
+- scene_calc/                 -- thin loader of rendered geometry (stats.json) for lint and design; no layout math
+- structure/                  -- layout structural check
`- shared_toolkit/             -- discovery, YAML I/O, findings, reporter, CLI helpers
```

### `tests/` - Test suite

Three tiers isolated by [conftest.py](../tests/conftest.py)
(`collect_ignore = ["e2e", "playwright"]`).

```text
tests/
+- conftest.py                 -- pytest config; collect_ignore for e2e and playwright
+- test_*.py                   -- fast pytest: pyflakes, ASCII, indent, shebang, imports, etc.
+- test_*.mjs                  -- Node unit tests (run by node --import tsx --test)
+- TESTS_README.md             -- test-suite overview
+- file_utils.py           -- shared REPO_ROOT helper
+- e2e/                        -- non-browser E2E runners (e2e_*.py, e2e_*.sh)
`- playwright/                 -- browser-driven tests, runner model (@playwright/test)
   +- repo_root.mjs            -- shared REPO_ROOT resolver
   +- smoke.spec.ts            -- broadest test: launcher loads, a protocol card opens a scene
   +- test_*.spec.ts           -- runner specs (framed layout, initial scene, etc.)
   +- helper_*.mjs / .tsx      -- non-test support (scene discovery, render harnesses)
   `- e2e/                     -- full-path walkthroughs
      `- protocol_walkthrough.spec.ts  -- one test() per curriculum protocol (native
                                          Playwright workers) plus a wrong-order negative test
```

`playwright.config.ts` (repo root) owns `testDir: tests/playwright`, `testMatch:
**/*.spec.ts`, and the shared `webServer` (builds then serves `dist/` on one
random port for every worker). `run_playwright_tests.sh` is the front door for
every browser test (`npx playwright test`); `super_all_tests.sh`'s browser
step is a single call to it.

Key pytest files:

| File                                                                                | Purpose                             |
| ----------------------------------------------------------------------------------- | ----------------------------------- |
| [test_pyflakes_code_lint.py](../tests/test_pyflakes_code_lint.py)                   | Pyflakes lint gate                  |
| [test_ascii_compliance.py](../tests/test_ascii_compliance.py)                       | ASCII source check                  |
| [test_markdown_links.py](../tests/test_markdown_links.py)                           | Markdown link validity              |
| [test_shebangs.py](../tests/test_shebangs.py)                                       | Shebang consistency                 |
| [test_import_dot.py](../tests/test_import_dot.py)                                   | Forbids relative imports            |
| [test_import_requirements.py](../tests/test_import_requirements.py)                 | Third-party imports declared        |
| [test_test_naming_conventions.py](../tests/test_test_naming_conventions.py)         | Test layout and naming              |
| [test_spec_docs_no_camelcase_yaml.py](../tests/test_spec_docs_no_camelcase_yaml.py) | Spec doc camelCase gate             |
| [test_walker_no_step_branches.py](../tests/test_walker_no_step_branches.py)         | Walker must not branch on step name |

Key Node test files:

| File                                                                          | Purpose                                                                                                                                    |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| [test_layout_engine.mjs](../tests/test_layout_engine.mjs)                     | Layout pipeline unit tests                                                                                                                 |
| [test_step_machine.mjs](../tests/test_step_machine.mjs)                       | Step machine unit tests                                                                                                                    |
| [test_structural_guards.mjs](../tests/test_structural_guards.mjs)             | Structural guard unit tests                                                                                                                |
| [test_resolve_entry_scene.mjs](../tests/test_resolve_entry_scene.mjs)         | Entry-scene resolution unit tests                                                                                                          |
| [test_visual_state_resolver.mjs](../tests/test_visual_state_resolver.mjs)     | Visual-state resolver (formulas, materials, missing-svg)                                                                                   |
| [test_scene_operations.mjs](../tests/test_scene_operations.mjs)               | Scene operations unit tests                                                                                                                |
| [test_protocol_emitter.mjs](../tests/test_protocol_emitter.mjs)               | Emitter unit tests                                                                                                                         |
| [test_shell_signals.mjs](../tests/test_shell_signals.mjs)                     | Shell signal binding tests                                                                                                                 |
| [test_m2_integration.mjs](../tests/test_m2_integration.mjs)                   | M2 framed-layout integration                                                                                                               |
| [test_flatten_sequence_runner.mjs](../tests/test_flatten_sequence_runner.mjs) | Direct-leaf runner flattening, unique constituents, and root-only initial-state ownership                                                  |
| [test_scene_store.mjs](../tests/test_scene_store.mjs)                         | Session archive lifecycle, initial-state expansion, rehydration, revision, and declared-state writes                                       |
| [test_walker_debug.mjs](../tests/test_walker_debug.mjs)                       | Walker debug projection, including `stateRevision` and `lastStateDelta`                                                                    |
| `test_material_color.mjs`                                                     | D3 resolver contract: all `resolve_color_result` success and failure cases                                                                 |
| `test_subpart_visual_state_renderer.mjs`                                      | Subpart material-tint renderer: dispatch predicate, fill, transparent empty, degrade path                                                  |
| `tests/test_protocol_initial_state.py`                                        | YAML validation and generation rules for root `initial_state`                                                                              |
| `tests/test_stepper_runner_state.py`                                          | Shared runner StateMap and direct-leaf runner semantics                                                                                    |
| `test_material_acceptance_cross_layer.mjs`                                    | Cross-layer acceptance: stepper D1 and TS runtime store accept and reject the same material names                                          |
| `tests/test_layout_offcanvas.mjs`                                             | Off-canvas classifier unit tests (exercises `PipelineResult.offCanvasDiagnostics` fully_off_canvas and partial_overflow paths)             |
| `tests/test_layout_config.mjs`                                                | Config-precedence unit tests: 16 behavioral tests covering zone_gap split, scene-level and zone-level overrides, and strategy-local values |

### `assets/` - Source SVG art

`assets/equipment/` contains tracked source SVG files for all lab objects,
organized by behavior rather than by object kind:

| Directory          | Authored behavior                                          |
| ------------------ | ---------------------------------------------------------- |
| `static/`          | One opaque complete form                                   |
| `binary_state/`    | Opaque forms selected by a two-form object state           |
| `multi_state/`     | Opaque forms selected by a state with more than two forms  |
| `variable_volume/` | Self-describing material SVG with continuous liquid amount |

`validation/svg/asset_registry.py` recursively discovers these sources and
requires every filename stem to be globally unique. The logical stem remains the
YAML `asset_name`. Source organization is intentionally not part of YAML or the
published URL: `assets/equipment/binary_state/power_supply_off.svg`, for example,
still publishes as `assets/svg/equipment/power_supply_off.svg`.

An ordinary equipment SVG is one complete source file. A material-rendered SVG
is also one source file, but is self-describing through the closed semantic contract in
[SVG_PIPELINE.md](specs/SVG_PIPELINE.md); it has no recipe sidecar. The
material normalizer and compiler derive its generated artifact and
liquid-region manifest from that SVG. Compiled by
`pipeline/gen_liquid_regions.py`; final URL mapping
and publication remain with [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py).
Before any generator runs, `pipeline/build_generated.sh` invokes
`validation/svg/material_anti_return_lint.py` to enforce the post-cutover
material-rendering boundary.

`assets/equipment/bottle.colormap.json` is a tracked, legacy unreferenced
migration-debt file. It is not a supported authoring surface and will be
removed through the ratified material-SVG migration; see
[SVG_PIPELINE.md](specs/SVG_PIPELINE.md).

### `tools/` - Developer-only helpers

Scripts that do not appear in any build chain. See [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
for the full list.

Key tools:

| File                                                      | Purpose                                                                                                                                                                                                                                                           |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/normalize_svg_v3.py`                               | SVG ingestion-gate normalizer (lxml + tinycss2 + shapely): normalize-or-reject pipeline; run before adding any SVG to `assets/`; see [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) for support contract and ingestion workflow                                     |
| `tools/svg_semantic_inspector.py`                         | Read-only normalized SVG inspector; reports material layer/part, clip, frame, and gravity bounds and compares donor-variant paint while preserving manual physical classification; never infers physical volume                                                   |
| `tools/liquid_volume_contact_page.mjs`                    | Builds self-contained HTML and PNG volume contact sheets under `rendered-reports/liquid_volume_contacts/` through the real compiled SVG injection and liquid writer                                                                                               |
| `tools/liquid_render_harness.ts`                          | Shared developer/test browser adapter for exercising the real compiled liquid injection and writer without duplicating their implementation                                                                                                                       |
| `tools/outline_svg_text.sh`                               | Optional, on-demand Inkscape authoring wrapper for approved physically intrinsic markings, including during legacy/import preparation; it never authorizes prose outlining and writes a validated, non-destructive copy before the separate v3 normalization step |
| [svg_to_html_render.mjs](../tools/svg_to_html_render.mjs) | Renders an SVG on five color swatches via Playwright Firefox and writes `<stem>_render.{html,png}` to CWD; use `--no-open` to skip auto-open                                                                                                                      |
| [svg_identity_sweep.py](../tools/svg_identity_sweep.py)   | Perceptual-hash duplicate/mislabel sweep over `assets/**/*.svg`; emits a review report                                                                                                                                                                            |
| [svg_feature_census.py](../tools/svg_feature_census.py)   | Read-only feature census over the wild SVG corpus (`OTHER_REPOS/`); counts clipPath/transform/text/etc. per file, cross-tabbed against the v3 verdict; emits `docs/active_plans/reports/svg_feature_census.{json,md}`                                             |
| `tools/layout_golden_diff.mjs`                            | `layout:diff` / `layout:refresh` -- ephemeral regression harness; captures a gitignored snapshot at `test-results/layout_reference_snapshot.json` with provenance and staleness detection; compares engine output after a change                                  |
| `tools/layout_metrics.mjs`                                | `layout:metrics` -- raw per-scene geometry metrics (rectangle-union fill, largest-empty-rect, occupancy, scale proxies, AABB overlap graph, balance) with per-scene overlay                                                                                       |
| `tools/layout_health_report.mjs`                          | `layout:health` -- interprets raw geometry metrics into provisional health categories and a worst-first author scorecard; writes `test-results/layout_health/`                                                                                                    |
| `tools/offcanvas_baseline.mjs`                            | Writes `docs/active_plans/audits/offcanvas_baseline.md` (per-scene off-canvas item counts from `PipelineResult.offCanvasDiagnostics`)                                                                                                                             |
| `tools/scene_render_diagnostics.mjs`                      | Pure classifier for scene-render DOM evidence and asset visual bounding boxes                                                                                                                                                                                     |

### `devel/` - Maintainer scripts

| File                                                  | Purpose                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| [setup_playwright.sh](../devel/setup_playwright.sh)   | Idempotent Playwright (chromium) install                      |
| [setup_typescript.sh](../devel/setup_typescript.sh)   | TypeScript dev environment setup                              |
| [dist_clean.sh](../devel/dist_clean.sh)               | Wipe `generated/` and `dist/`                                 |
| [rotate_changelog.py](../devel/rotate_changelog.py)   | Changelog rotation (keeps two newest day blocks)              |
| [query_changelog.py](../devel/query_changelog.py)     | Changelog search by date, category, keyword                   |
| [commit_changelog.py](../devel/commit_changelog.py)   | Draft commit message from new changelog entries               |
| [bump_version.py](../devel/bump_version.py)           | Version bump helper                                           |
| [ai_polish_review.mjs](../devel/ai_polish_review.mjs) | AI visual-polish reviewer over before/after scene screenshots |

### `docs/` - Documentation

| File                                                                   | Purpose                                                                                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [NEWS.md](NEWS.md)                                                     | Curated release highlights and announcements                                                                              |
| [CHANGELOG.md](CHANGELOG.md)                                           | Chronological record of changes                                                                                           |
| [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)                           | System design, components, and data flow                                                                                  |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md)                                 | This file                                                                                                                 |
| [INSTALL.md](INSTALL.md)                                               | Prerequisites and setup                                                                                                   |
| [USAGE.md](USAGE.md)                                                   | Build and run instructions                                                                                                |
| [AUTHORS.md](AUTHORS.md)                                               | Maintainers and contributors                                                                                              |
| [ROADMAP.md](ROADMAP.md)                                               | Planned work                                                                                                              |
| [TODO.md](TODO.md)                                                     | Backlog scratchpad                                                                                                        |
| [E2E_TESTS.md](E2E_TESTS.md)                                           | E2E test conventions                                                                                                      |
| [PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md)                             | Playwright browser-test usage                                                                                             |
| [PYTEST_STYLE.md](PYTEST_STYLE.md)                                     | Pytest conventions                                                                                                        |
| [PYTHON_STYLE.md](PYTHON_STYLE.md)                                     | Python conventions                                                                                                        |
| [TYPESCRIPT_STYLE.md](TYPESCRIPT_STYLE.md)                             | TypeScript conventions                                                                                                    |
| [MARKDOWN_STYLE.md](MARKDOWN_STYLE.md)                                 | Markdown formatting rules                                                                                                 |
| [REPO_STYLE.md](REPO_STYLE.md)                                         | Repo-wide conventions                                                                                                     |
| [HUMAN_GUIDANCE.md](HUMAN_GUIDANCE.md)                                 | Stable human authoring guidance, including language-neutral SVG art                                                       |
| [LAYOUT_REMAINING_WORK.md](LAYOUT_REMAINING_WORK.md)                   | Scene-by-scene layout and aesthetic remaining work reference                                                              |
| [PRIMARY_CONTRACT.md](PRIMARY_CONTRACT.md)                             | Hard design invariants                                                                                                    |
| [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md)                                 | Design philosophy                                                                                                         |
| [PRIMARY_SPEC.md](PRIMARY_SPEC.md)                                     | Technical specification                                                                                                   |
| [CLAUDE_HOOK_USAGE_GUIDE.md](CLAUDE_HOOK_USAGE_GUIDE.md)               | Claude Code permissions hook reference                                                                                    |
| [specs/PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md)           | Canonical protocol vocabulary                                                                                             |
| [specs/PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md)         | Protocol YAML schema reference                                                                                            |
| [specs/PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md) | Worked authoring example                                                                                                  |
| `specs/GESTURE_MODEL.md`                                               | Cross-layer gesture, input, capability, and evidence status reference                                                     |
| [specs/PROTOCOL_STEPS.md](specs/PROTOCOL_STEPS.md)                     | Step-flow architecture                                                                                                    |
| [specs/SCENE_VOCABULARY.md](specs/SCENE_VOCABULARY.md)                 | Canonical scene vocabulary                                                                                                |
| [specs/SCENE_YAML_FORMAT.md](specs/SCENE_YAML_FORMAT.md)               | Scene YAML schema reference                                                                                               |
| [specs/SCENE_ARCHITECTURE.md](specs/SCENE_ARCHITECTURE.md)             | Scene wiring and runtime                                                                                                  |
| [specs/SCENE_METRICS.md](specs/SCENE_METRICS.md)                       | Scene-author guide to the layout health report                                                                            |
| [SCENE_LAYOUT_BASELINE.md](SCENE_LAYOUT_BASELINE.md)                   | Committed, hand-refreshed layout health/diagnostics snapshot taken after the failBuild gate went live                     |
| [specs/OBJECT_VOCABULARY.md](specs/OBJECT_VOCABULARY.md)               | Canonical object vocabulary                                                                                               |
| [specs/OBJECT_YAML_FORMAT.md](specs/OBJECT_YAML_FORMAT.md)             | Object-definition YAML schema reference                                                                                   |
| [specs/LAYOUT_ENGINE.md](specs/LAYOUT_ENGINE.md)                       | Layout-engine placement reference                                                                                         |
| [specs/MATERIAL_DESIGN.md](specs/MATERIAL_DESIGN.md)                   | Design rationale for scalar color, transparent empty, and the separate identity/amount layers                             |
| [specs/MATERIAL_VOCABULARY.md](specs/MATERIAL_VOCABULARY.md)           | Canonical material terms, the settled sentinel/visible classification, and the D1 predicate entry point                   |
| [specs/MATERIAL_YAML_FORMAT.md](specs/MATERIAL_YAML_FORMAT.md)         | `materials.yaml` schema: entry keys, scalar `display_color` hex format, D1 predicate, closed-key rule, sentinel exemption |
| [specs/MATERIAL_CONVENTION.md](specs/MATERIAL_CONVENTION.md)           | Runtime render-effect and target convention, color resolver typed result, SVG anchor contract, and recolor model          |
| `MATERIAL_LINT.md`                                                     | Validator and audit surface: lint rules L1-L10, D3 resolver contract, cross-YAML agreement rule, and validator hook table |
| [specs/SVG_PIPELINE.md](specs/SVG_PIPELINE.md)                         | SVG asset ownership and pipeline                                                                                          |
| [specs/SCALING_MODEL.md](specs/SCALING_MODEL.md)                       | Scaling model notes                                                                                                       |
| [specs/WALKTHROUGH_GUIDE.md](specs/WALKTHROUGH_GUIDE.md)               | Real-browser protocol walkthrough guide                                                                                   |
| [specs/SPEC_DESIGN_CHECKLIST.md](specs/SPEC_DESIGN_CHECKLIST.md)       | Author YAML vocabulary lock checklist                                                                                     |
| `active_plans/`                                                        | In-flight plan documents (active, audits, reports, decisions, workstreams)                                                |
| `archive/`                                                             | Archived plans and design notes                                                                                           |

## Generated artifacts

All gitignored (see [.gitignore](../.gitignore)):

| Path                                                                  | Source script                                                                                                                                                        |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `generated/object_library.ts`                                         | [gen_object_library.py](../pipeline/gen_object_library.py)                                                                                                           |
| `generated/svg_manifest.ts`                                           | [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py)                                                                                                               |
| `generated/liquid_regions.json`                                       | `pipeline/gen_liquid_regions.py`                                                                                                                                     |
| `generated/material_svg/<category>/<name>.svg`                        | `pipeline/gen_liquid_regions.py`                                                                                                                                     |
| `generated/svg_placeholder_keys.ts`                                   | [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py) (build/test-only placeholder key array)                                                                       |
| `generated/scenes.ts`                                                 | [gen_scene_index.py](../pipeline/gen_scene_index.py)                                                                                                                 |
| `generated/scene_manifest.json`                                       | [gen_scene_index.py](../pipeline/gen_scene_index.py) (per-scene classification, source of truth for scene tooling)                                                   |
| `generated/protocols.ts`                                              | [gen_protocols.py](../pipeline/gen_protocols.py)                                                                                                                     |
| `generated/protocols_index_slim.ts`                                   | [gen_protocols.py](../pipeline/gen_protocols.py)                                                                                                                     |
| `generated/protocol_materials.ts`                                     | [gen_protocols.py](../pipeline/gen_protocols.py) (per-protocol material registry; keyed by protocol_name)                                                            |
| `generated/flow_views/<protocol_name>.txt`                            | [gen_flow_view.py](../pipeline/gen_flow_view.py) (per-protocol audit view; not the design source)                                                                    |
| `generated/precomputed_layout.ts`                                     | [precompute_layout.mjs](../pipeline/precompute_layout.mjs) (`PRECOMPUTED_LAYOUT`: per-scene `{ final: ComputedItem[] }` at canonical 16:9)                           |
| `generated/scene_render_stats/<scene>.stats.json`                     | renderer-produced scene geometry stats consumed by SCENE-LINT/SCENE-DESIGN, written by [scene_to_png.mjs](../tools/scene_to_png.mjs) after the Pages bundle is built |
| `dist/`                                                               | [build_github_pages.sh](../build_github_pages.sh) (GitHub Pages bundle)                                                                                              |
| `dist/assets/svg/<category>/<name>.svg`                               | SVG assets copied by [build_github_pages.sh](../build_github_pages.sh)                                                                                               |
| `dist/scene_viewer.html`                                              | Copied from `src/scene_viewer_template.html` during build                                                                                                            |
| `test-results/`                                                       | Playwright screenshots and reports                                                                                                                                   |
| `test-results/scenes/<scene>.png`, `test-results/scenes/summary.json` | optional human artifacts (PNG screenshots and run report), written only with `node tools/scene_to_png.mjs --all --png`                                               |
| `rendered-reports/liquid_volume_contacts/`                            | persistent, gitignored HTML and PNG material-volume visual-review artifacts written by `render_liquid_volume_contact_sheet.sh`                                       |
| `node_modules/`                                                       | npm install output                                                                                                                                                   |

The `generated/` tree is rebuilt from current YAML and SVG sources on every
build. Do not place authored files there.

## Documentation map

| Question                                                  | Document                                                                                                                                                                             |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| How is the system designed?                               | [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)                                                                                                                                         |
| Where does each file live?                                | This file                                                                                                                                                                            |
| What are the hard rules?                                  | [PRIMARY_CONTRACT.md](PRIMARY_CONTRACT.md)                                                                                                                                           |
| What is the YAML schema?                                  | [specs/PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md), [specs/SCENE_YAML_FORMAT.md](specs/SCENE_YAML_FORMAT.md), [specs/OBJECT_YAML_FORMAT.md](specs/OBJECT_YAML_FORMAT.md) |
| How do I author a protocol?                               | [specs/PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md)                                                                                                               |
| How do gestures map to browser input and object behavior? | `specs/GESTURE_MODEL.md`                                                                                                                                                             |
| How do I set up the repo?                                 | [INSTALL.md](INSTALL.md)                                                                                                                                                             |
| How do I run the game?                                    | [USAGE.md](USAGE.md)                                                                                                                                                                 |
| What is planned next?                                     | [ROADMAP.md](ROADMAP.md) and [TODO.md](TODO.md)                                                                                                                                      |

## Where to add new work

| Type                    | Location                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| New mini-protocol       | `content/protocols/<cluster>/<name>/` with `protocol.yaml`, `scenes/`, `materials.yaml`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| New base scene          | `content/base_scenes/<name>.yaml`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| New lab object          | `content/objects/<kind>/<name>.yaml`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| New SVG asset           | `assets/equipment/<behavior>/<name>.svg`, where `<behavior>` is `static`, `binary_state`, `multi_state`, or `variable_volume` and must agree with the validator's YAML/SVG-derived projection (move prose labels to layout-manager DOM or object data; outline only approved physically intrinsic markings, including during legacy/import preparation, with `tools/outline_svg_text.sh`, then run `tools/normalize_svg_v3.py`; provenance never permits prose outlining. Ordinary equipment SVGs are complete files. Material-rendered SVGs are self-describing files that follow the closed [SVG_PIPELINE.md](specs/SVG_PIPELINE.md) semantic contract; no recipe sidecar is authored, and the material artifact/manifest are generated.) |
| New pipeline generator  | `pipeline/` (register in `package.json` pre-hooks; update these two docs)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| New shell region        | `src/shell/regions/` (mount in `src/shell/hud/protocol_hud.tsx`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| New runtime module      | `src/` (imported from entry or scene runtime)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| New validation rule     | `validation/yaml_schema/` or `validation/scene_lint/`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Fast pytest test        | `tests/test_*.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Node unit test          | `tests/test_*.mjs`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Playwright browser test | `tests/playwright/*.spec.ts` (runner model; see `playwright.config.ts`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Full-path walkthrough   | `tests/playwright/e2e/*.spec.ts`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Non-browser E2E         | `tests/e2e/e2e_*.py` or `tests/e2e/e2e_*.sh`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Developer utility       | `tools/` (never `pipeline/`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Documentation           | `docs/` with SCREAMING_SNAKE_CASE filename                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Spec vocabulary         | `docs/specs/`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Active plans            | `docs/active_plans/active/`, `audits/`, `reports/`, `decisions/`, or `workstreams/`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
