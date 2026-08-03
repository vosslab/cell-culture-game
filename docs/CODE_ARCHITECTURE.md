# Code architecture

Protocol terminology is defined in [specs/PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md).
This doc uses that vocabulary without restating definitions.

## Overview

A browser-based educational simulation that teaches laboratory techniques
(cell culture, SDS-PAGE) through step-by-step YAML-authored mini-protocols.
Protocol and scene content lives as YAML in `content/` and is compiled to
TypeScript by generator scripts in `pipeline/` before each build. The shared
TypeScript runtime under `src/` renders scenes, drives protocol steps, and
surfaces a HUD shell to the student.

Build output is a GitHub Pages-ready directory at `dist/`. A shared bundle
(`dist/launcher.js`, `dist/protocol_host.js`) serves every page; routing is
by DOM-element presence, not by URL.

## Major components

### Entry and routing (`src/`)

| File                                                      | Purpose                                                                                                              |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| [dist_entry.tsx](../src/dist_entry.tsx)                   | Bundle entry; routes to launcher, protocol host, or bench by DOM root presence                                       |
| [launcher_entry.tsx](../src/launcher_entry.tsx)           | Launcher bundle entry; mounts Solid `Launcher` into `#launcher-root`                                                 |
| [protocol_host_entry.tsx](../src/protocol_host_entry.tsx) | Protocol-host bundle entry; imports `protocol_host.tsx`                                                              |
| [protocol_host.tsx](../src/protocol_host.tsx)             | Wires layout pipeline, renderer, step machine, click resolver, and HUD for one protocol page                         |
| `src/launcher/protocol_launcher.tsx`                      | Solid component; renders the protocol selector from `PROTOCOLS_INDEX_SLIM`                                           |
| [index.html](../src/index.html)                           | Bench page (render smoke target; copied to `dist/bench_basic.html`)                                                  |
| [index.html](../src/launcher/index.html)                  | Launcher page (copied to `dist/index.html`)                                                                          |
| `src/protocol_host_template.html`                         | Six-region framed-interface shell for per-protocol pages (`#scene-root`, `#shell-root`, named `data-region` targets) |

`protocol_host.tsx` mount order:

1. Resolve protocol name from `?protocol=` query string or `window.__PROTOCOL_NAME__`.
2. Look up `ProtocolConfig` from `generated/protocols.ts`. A
   `sequence_runner` is flattened once here into its direct, unique
   `mini_protocol` leaves; the runner root remains the sole owner of any
   `initial_state` declaration.
3. Resolve entry scene via `resolve_entry_scene_name` (see scene_runtime/protocol below).
4. Paint `#scene-root` from the precomputed layout. The shipped bundle loads
   `PRECOMPUTED_LAYOUT[scene_name]` from `generated/precomputed_layout.ts`
   (build-time layout at the canonical 16:9 frame) and assembles a
   `PipelineResult` from it via `resolve_precomputed_result` /
   `make_precomputed_result` in
   `src/scene_runtime/layout/precomputed_result.ts` (the renderer reads only
   `final` and `scene`); a missing entry throws. WP-PRECOMP3 retired the runtime
   `runPipeline` engine and the `?layout=runtime` parity switch from every shipped
   entry, so the production bundle holds no `runPipeline` call path -- the
   precomputed layout is the single production path. The runtime engine in
   `src/scene_runtime/layout/` is now BUILD-ONLY: `pipeline/precompute_layout.mjs`
   runs it to emit `generated/precomputed_layout.ts`, and tests still import it,
   but it is tree-shaken out of `dist/protocol_host.js`, `dist/scene_viewer.js`,
   and `dist/launcher.js`. The CSS forces `#scene-root` to an exact 16:9 letterboxed frame
   (`.scene-panel` size container + `.scene-panel-inner` 16:9), so precomputed
   16:9 positions are pixel-correct at any panel size; resizing changes only the
   neutral bars and uniform scale, never the scene-internal layout.
5. Build emitter, scene-op handler, step machine, and click resolver.
6. Mount `ProtocolHud` into `#shell-root` (unless `?shell=off`).
7. Call `step_machine.start()`.

### Scene runtime - layout (`src/scene_runtime/layout/`)

Multi-pass layout pipeline. Converts a scene YAML record plus the object
library into positioned, scaled `ComputedItem` records. As of WP-PRECOMP3 this
engine is BUILD-ONLY: `pipeline/precompute_layout.mjs` runs it to emit
`generated/precomputed_layout.ts`, and tests import it, but no `runPipeline` call
path ships in the production browser bundle. The shipped render path consumes the
precomputed layout via `precomputed_result.ts` instead.

| File                                                                           | Purpose                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [precomputed_result.ts](../src/scene_runtime/layout/precomputed_result.ts)     | Production seam (WP-PRECOMP3): `resolve_precomputed_result` / `make_precomputed_result` build a renderer-ready `PipelineResult` from `PRECOMPUTED_LAYOUT[scene_name]` (throws on a missing entry). Imports `buildDecisionMetadata` directly (not the barrel) so the shipped bundle drags in no `runPipeline` call path. This is the only layout module the production bundle reaches at render time. |
| [phases.ts](../src/scene_runtime/layout/phases.ts)                             | Phase registry: named phase sequence including vertical measurement and zone reflow before vertical placement, with explicit read/mutate boundaries and bounded convergence loop                                                                                                                                                                                                                     |
| [run_pipeline.ts](../src/scene_runtime/layout/run_pipeline.ts)                 | Top-level pipeline runner; drives named phases from the registry (build-only since WP-PRECOMP3)                                                                                                                                                                                                                                                                                                      |
| [types.ts](../src/scene_runtime/layout/types.ts)                               | All layout type definitions (`PipelineResult`, `ComputedItem`, `PlacementAuthored`, etc.)                                                                                                                                                                                                                                                                                                            |
| [constants.ts](../src/scene_runtime/layout/constants.ts)                       | Layout constants (`DEFAULT_VIEWPORT`, `WORKSPACE_PX_PER_CM`, shrink factor)                                                                                                                                                                                                                                                                                                                          |
| [bind_objects.ts](../src/scene_runtime/layout/bind_objects.ts)                 | Stage: bind object YAML to placements                                                                                                                                                                                                                                                                                                                                                                |
| [resolve_inheritance.ts](../src/scene_runtime/layout/resolve_inheritance.ts)   | Stage: resolve base-scene inheritance chain                                                                                                                                                                                                                                                                                                                                                          |
| [normalize_schema.ts](../src/scene_runtime/layout/normalize_schema.ts)         | Stage: normalize Schema A scene fields and apply layout-rule defaults                                                                                                                                                                                                                                                                                                                                |
| [scale_to_real_world.ts](../src/scene_runtime/layout/scale_to_real_world.ts)   | Stage: convert real-world dimensions to pixels                                                                                                                                                                                                                                                                                                                                                       |
| [lower_semantic_zones.ts](../src/scene_runtime/layout/lower_semantic_zones.ts) | Lowers coordinate-free authored semantic zones into internal bounds and baselines from placement demand; preserves fully geometric legacy scenes                                                                                                                                                                                                                                                     |
| [horizontal_layout.ts](../src/scene_runtime/layout/horizontal_layout.ts)       | Stage: compute x positions                                                                                                                                                                                                                                                                                                                                                                           |
| [vertical_footprint.ts](../src/scene_runtime/layout/vertical_footprint.ts)     | Shared object-plus-wrapped-label vertical extent measurement for later zone reflow                                                                                                                                                                                                                                                                                                                   |
| [reflow_zones.ts](../src/scene_runtime/layout/reflow_zones.ts)                 | Computes measured vertical bands per zone and reports overflow; does not mutate item geometry                                                                                                                                                                                                                                                                                                        |
| [vertical_layout.ts](../src/scene_runtime/layout/vertical_layout.ts)           | Stage: compute y positions                                                                                                                                                                                                                                                                                                                                                                           |
| [group_by_zone.ts](../src/scene_runtime/layout/group_by_zone.ts)               | Stage: group placements by zone                                                                                                                                                                                                                                                                                                                                                                      |
| [footprint.ts](../src/scene_runtime/layout/footprint.ts)                       | Footprint helpers                                                                                                                                                                                                                                                                                                                                                                                    |
| [clamp_scene_bounds.ts](../src/scene_runtime/layout/clamp_scene_bounds.ts)     | Clamp placements to scene bounds                                                                                                                                                                                                                                                                                                                                                                     |
| [layout_labels.ts](../src/scene_runtime/layout/layout_labels.ts)               | Label positioning                                                                                                                                                                                                                                                                                                                                                                                    |
| [wrap_label.ts](../src/scene_runtime/layout/wrap_label.ts)                     | Label line-wrap helper                                                                                                                                                                                                                                                                                                                                                                               |
| [index.ts](../src/scene_runtime/layout/index.ts)                               | Barrel re-export: `runPipeline`                                                                                                                                                                                                                                                                                                                                                                      |

#### Geometry core (`src/scene_runtime/layout/geometry/`)

Pure 2D AABB geometry core. Immutable `Aabb` and `Vector` value types carry no
layout state. `detectCollision` returns a `Collision` with `overlapVectorAtoB`,
`separationForA`, and `separationForB`; `buildResolutionCandidate` turns a
`Collision` into a `ResolutionCandidate`, and `sortResolutionOrder` orders
candidates deterministically. The geometry stays pure (no mutation); the label
and object-placement layout phases consume it later and own all mutation.

| File                                                              | Purpose                                                                                |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [types.ts](../src/scene_runtime/layout/geometry/types.ts)         | Immutable value types: `Vector`, `Aabb`, `Collision`, `ResolutionCandidate`            |
| [collision.ts](../src/scene_runtime/layout/geometry/collision.ts) | `aabbFromBounds`, `detectCollision`, `buildResolutionCandidate`, `sortResolutionOrder` |

#### Layout config (`src/scene_runtime/layout/config/`)

Resolves a `LayoutConfig` by a fixed precedence: global defaults, scene
`layout_rules`, zone overrides, placement-derived values, then strategy-local
values. Stages read every tunable through `LayoutConfig` rather than importing
constants directly, so tuning one scene does not affect others.

| File                                                | Purpose                                 |
| --------------------------------------------------- | --------------------------------------- |
| `src/scene_runtime/layout/config/types.ts`          | `LayoutConfig` and related config types |
| `src/scene_runtime/layout/config/resolve_config.ts` | Config precedence resolver              |
| `src/scene_runtime/layout/config/index.ts`          | Barrel export                           |

#### Diagnostics (`src/scene_runtime/layout/diagnostics/`)

Severity-graded typed diagnostics emitted by layout phases. Error-severity codes
fail the build; Warnings and Review-required surface in the report and allow
success. Per-scene decision metadata (selected strategy, packer trigger/result,
shrink applied, rows created, resolved config) is emitted separately from the
diagnostic stream.

| File                                                        | Purpose                                                                                                                                                                                         |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/scene_runtime/layout/diagnostics/severity_model.ts`    | Error / Warning / Review-required severity types                                                                                                                                                |
| `src/scene_runtime/layout/diagnostics/payload.ts`           | Typed diagnostic payload shapes                                                                                                                                                                 |
| `src/scene_runtime/layout/diagnostics/decision_metadata.ts` | Per-scene decision metadata type                                                                                                                                                                |
| `src/scene_runtime/layout/diagnostics/offcanvas.ts`         | Off-canvas classifier: emits `fully_off_canvas` (error-level) or `partial_overflow` (magnitude-scaled warning) onto `PipelineResult.offCanvasDiagnostics`; report-only, never blocks build gate |
| `src/scene_runtime/layout/diagnostics/item_overlap.ts`      | Shared AABB overlap predicate and the item_overlap cross-zone diagnostic; imported by run_pipeline.ts and structural_guards.ts                                                                  |
| `src/scene_runtime/layout/diagnostics/index.ts`             | Barrel export                                                                                                                                                                                   |

#### Placement strategies (`src/scene_runtime/layout/strategies/`)

`PlacementStrategy` seam with two implementations. `row_strategy.ts` is the
default. The overflow packer (`pack_strategy.ts`) engages only when a row would
shrink below the configured threshold or overflow; it preserves primary-object
scale and input order before maximizing area. Object placement is 1D row
footprint; same-tier de-overlap is deferred (see Known gaps).

| File                                                        | Purpose                       |
| ----------------------------------------------------------- | ----------------------------- |
| `src/scene_runtime/layout/strategies/placement_strategy.ts` | `PlacementStrategy` interface |
| `src/scene_runtime/layout/strategies/row_strategy.ts`       | Default row strategy          |
| `src/scene_runtime/layout/strategies/pack_strategy.ts`      | Overflow packer strategy      |
| `src/scene_runtime/layout/strategies/index.ts`              | Barrel export                 |

### Scene runtime - protocol (`src/scene_runtime/protocol/`)

Step machine, validators, scene operations, and click resolver.

| File                                                                                     | Purpose                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [resolve_entry_scene.ts](../src/scene_runtime/protocol/resolve_entry_scene.ts)           | `resolve_entry_scene_name` (step.scene -> SceneChange fallback -> throw; runner delegation); `assert_scene_not_empty` guard                                                                                                                                                                                               |
| [step_machine.ts](../src/scene_runtime/protocol/step_machine.ts)                         | Pure step machine: step progression, interaction-index advancement, validator dispatch, scene-op handoff, event emission                                                                                                                                                                                                  |
| [validators.ts](../src/scene_runtime/protocol/validators.ts)                             | Interaction and step validator dispatch (`correct_target`, `correct_choice`, `target_with_value`, `sequence_complete`, `final_state_matches`)                                                                                                                                                                             |
| [gesture_registry.ts](../src/scene_runtime/protocol/gesture_registry.ts)                 | `GESTURE_REGISTRY`: one row per closed `Gesture` (render shape, `data-*` selectors, value extraction, single dispatch entry, walker driver); owns `scene_click_to_command` and `dispatch_gesture` (the single gesture-routing point, exhaustive `never` default)                                                          |
| [target_adapter.ts](../src/scene_runtime/protocol/target_adapter.ts)                     | Protocol-target -> DOM identity adapter: `resolve_to_placement` / `resolve_to_object`, `AmbiguousTargetError` on non-unique object_name, `TARGET_DOM_ATTR` / `TARGET_DOM_SELECTOR`                                                                                                                                        |
| [flatten_sequence_runner.ts](../src/scene_runtime/protocol/flatten_sequence_runner.ts)   | Validates and flattens a `sequence_runner` into one chained step list. Constituents must be present, direct `mini_protocol` leaves, and unique; each leaf step is namespaced and terminal steps chain to the next leaf.                                                                                                   |
| [authored_value_check.ts](../src/scene_runtime/protocol/authored_value_check.ts)         | Load-time authored-value guard for `target_with_value` / `final_state_matches` (UnknownAuthored*/BadAuthoredValue errors)                                                                                                                                                                                                 |
| [gesture_affordance_check.ts](../src/scene_runtime/protocol/gesture_affordance_check.ts) | Load-time invariant `validate_gesture_affordances`: an authored gesture whose `GESTURE_REGISTRY` row is absent or `wired: false` throws `UnaffordancedGestureError` at protocol load                                                                                                                                      |
| [target_existence_check.ts](../src/scene_runtime/protocol/target_existence_check.ts)     | Load-time invariant: an authored `target` that does not resolve to a scene object throws at protocol load                                                                                                                                                                                                                 |
| [scene_operations.ts](../src/scene_runtime/protocol/scene_operations.ts)                 | Routes five `SceneOperation` primitives to injected deps (exhaustive switch over `ObjectStateChange`, `CursorAttach`, `SceneChange`, `LayoutMove`, `TimedWait`)                                                                                                                                                           |
| [scene_op_deps.ts](../src/scene_runtime/protocol/scene_op_deps.ts)                       | Store-driven `SceneOpDeps`: `ObjectStateChange`/`CursorAttach` write `scene_store`; `SceneChange` reconciles the destination projection against the session archive and reapplies cursor-held state; `LayoutMove` is a reported no-op (Option A); `TimedWait` exposes an observable equipment phase before the next write |
| [walker_debug.ts](../src/scene_runtime/protocol/walker_debug.ts)                         | Read-only walker/debug surface: installs `window.PROTOCOL_STEPS` + `window.gameState` projected from the emitter snapshot + scene store, including `stateRevision` and the concrete `lastStateDelta` (frozen contract)                                                                                                    |
| [click_resolver.ts](../src/scene_runtime/protocol/click_resolver.ts)                     | Attaches DOM click listener; maps click target to interaction validator                                                                                                                                                                                                                                                   |
| [affordance.ts](../src/scene_runtime/protocol/affordance.ts)                             | Pure affordance-kind mapping: `compute_affordance_kind` + types `AffordanceKind`, `AffordanceGesture` (= canonical `Gesture` \| null), `ActiveAffordanceAccessor`, `ComputeAffordanceKindArgs`; no Solid reactive reads, no I/O, no layout import                                                                         |
| [emitter.ts](../src/scene_runtime/protocol/emitter.ts)                                   | `ProtocolShellEmitter` and `RuntimeEmitterHandle`; snapshot reducer pattern                                                                                                                                                                                                                                               |

Scene operations drive the reactive `scene_store` (WS-M3-D): a validated
interaction's `ObjectStateChange` writes declared object state, the Solid
renderer reacts, and a `SceneChange` re-renders the next scene while preserving
cursor-held tool/material. `protocol_host.tsx` wires the store-driven deps and
restores the read-only `window.PROTOCOL_STEPS` / `window.gameState` surfaces.

#### Protocol session state (`src/scene_runtime/state/scene_store.ts`)

The store separates durable scientific state from the currently rendered scene.
Its archive is keyed by authored target identity, including dotted subparts such
as `microtube_rack_8.slot_A1`; its reactive projection contains only targets in
the active scene. `start_session(seeds, initial_state)` clears the archive,
validates the optional root-level `initial_state`, expands declared subpart
groups, rejects overlapping resolved targets, and mounts the first projection.
`reconcile_scene(seeds)` replaces that projection and rehydrates each target
from the archive or declared defaults, with runtime-only flags reset.
`snapshot_declared_state()` returns a detached declared-state view, including
targets that are temporarily absent from the rendered scene. A fresh session or
`reset()` clears retained state.

`initial_state` has the same closed primitive state domain as an
`ObjectStateChange`: object, declared subpart, and declared subpart-group
targets are allowed only when their fields, types, ranges, enums, units, and
material registry entries validate. The YAML validator and
[gen_protocols.py](../pipeline/gen_protocols.py) enforce this at generation
time; the store repeats the runtime boundary checks. A direct mini-protocol
uses its own declaration. A flattened sequence runner uses only the runner
root's declaration, so a constituent cannot silently seed a shared session.

### Scene runtime - renderer (`src/scene_runtime/renderer/`)

Renders a `PipelineResult` into the DOM. The paint path is Solid: a reactive
`SceneView` component renders one `SceneItem` per placement and reacts to the
`scene_store`. The earlier imperative item-paint path (`render_item.ts`,
`render_label.ts`) is retired; `render_scene.tsx` is the public Solid mount
facade and `scene_item.tsx` / `scene_view.tsx` own item and label rendering.

| File                                                                               | Purpose                                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [render_scene.tsx](../src/scene_runtime/renderer/render_scene.tsx)                 | Public Solid mount facade: creates the scene store, mounts `SceneView` into `#scene-root`, returns a dispose handle                                                                                                                                                                             |
| [affordance_candidates.ts](../src/scene_runtime/renderer/affordance_candidates.ts) | `enumerate_candidate_targets(result)`: renderer-layer candidate-set enumeration over clickable placements plus geometry-complete declared subparts and groups; single source of truth with the click resolver                                                                                   |
| [scene_view.tsx](../src/scene_runtime/renderer/scene_view.tsx)                     | Solid `SceneView`: renders background, one `SceneItem` per placement, and label elements; runs structural guards (collects violations) and sets `data-scene-degraded`                                                                                                                           |
| [scene_item.tsx](../src/scene_runtime/renderer/scene_item.tsx)                     | Solid `SceneItem`: reactive single-item paint (position, depth, SVG inject, missing-svg placeholder dashed box, `data-*` attributes), including focused scaling around an active exact subpart or declared group                                                                                |
| [subpart_hit_surface.tsx](../src/scene_runtime/renderer/subpart_hit_surface.tsx)   | Generic declaration-owned SVG hit surface for dotted targets. It requires generated geometry, maps a declared group to each concrete member, preserves nonmember sibling identities for rejection, and throws rather than falling back to the parent object when target geometry is incomplete. |
| [visual_state_resolver.ts](../src/scene_runtime/renderer/visual_state_resolver.ts) | Pure (no-DOM, no-Solid) resolver mapping object state + authored `visual_states` + per-protocol material registry to a renderable description                                                                                                                                                   |
| [render_background.ts](../src/scene_runtime/renderer/render_background.ts)         | Render scene background (gradient or asset)                                                                                                                                                                                                                                                     |
| [structural_guards.ts](../src/scene_runtime/renderer/structural_guards.ts)         | Six structural guards (item count, bounds, aspect ratio, asset presence, etc.); collects all violations rather than throwing on the first; throwing wrapper is exposed for tests/CI                                                                                                             |
| [inject_svg.ts](../src/scene_runtime/renderer/inject_svg.ts)                       | Manifest-fetch SVG DOM path: `injectSvgFromManifest` and `injectSvgMarkupInto` both route through `namespaceSvgIds`; material forms also bind compiler-generated opaque liquid-region handles. No `injectSvgInto` or bundled-registry path.                                                     |
| `material_color.ts`                                                                | D3 color resolver: `resolve_color_result(material_name, registry)` returns `ColorResult` discriminated union (empty/null, built-in mixed/#686868, registry-backed scalar, or `ok:false` failure)                                                                                                |
| `material_acceptance.ts`                                                           | D1 registry-backed acceptance predicate: mirrors Python stepper `mutate_state_field` so TS store and Python stepper accept and reject the same material names                                                                                                                                   |
| [liquid_paint.ts](../src/scene_runtime/renderer/liquid_paint.ts)                   | Sole object-level material writer: recolors compiled paint handles and applies stationary-bottom, scaled-body, and translated-surface operations from compiler-owned geometry.                                                                                                                  |
| [oklch_shade.ts](../src/scene_runtime/renderer/oklch_shade.ts)                     | Derives coordinated base, highlight, and shadow colors from one material display color.                                                                                                                                                                                                         |
| `subpart_dispatch.ts`                                                              | JSX-free dispatch predicate (`find_material_tint_subpart_field`): identifies structured objects with a `material_tint`/`subpart` render effect from the declaration, not runtime value                                                                                                          |
| `subpart_visual_state_renderer.tsx`                                                | Solid subpart material-tint overlay: one static `<svg>` per structured object over generated `subpart_geometry`; per-subpart `createMemo` reads via `getSubpartStateField` and `resolve_color_result`; `ok:true`+color paints, `ok:true`+null transparent, `ok:false` degrades                  |
| [svg_manifest_loader.ts](../src/scene_runtime/renderer/svg_manifest_loader.ts)     | Runtime SVG manifest fetch/cache layer; loads SVG files from `dist/assets/svg/` via `generated/svg_manifest.ts`                                                                                                                                                                                 |
| [index.ts](../src/scene_runtime/renderer/index.ts)                                 | Barrel re-export: `renderScene`, `mountScene`, `SceneView`, `SceneItem`, `renderBackground`                                                                                                                                                                                                     |

### Shell and HUD (`src/shell/`)

Solid.js observer layer. Subscribes to the emitter; never mutates protocol state.

| File                                                      | Purpose                                                                                 |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [types.ts](../src/shell/adapter/types.ts)                 | Closed seam contract: `ProtocolConfig`, `ShellViewSnapshot`, all event/op/gesture types |
| [signals.ts](../src/shell/signals.ts)                     | Re-exports Solid signals; `subscribeEmitterToSnapshot` binding helper                   |
| [protocol_hud.tsx](../src/shell/hud/protocol_hud.tsx)     | Owns the student-facing protocol shell composition                                      |
| [step_outline.tsx](../src/shell/regions/step_outline.tsx) | Read-only ordered step cards with complete/current/upcoming states                      |
| [authored_tip.tsx](../src/shell/regions/authored_tip.tsx) | Optional authored technique tip without a generic fallback                              |
| [step_counter.tsx](../src/shell/regions/step_counter.tsx) | Labeled completed/total counter                                                         |
| [guidance_bar.tsx](../src/shell/regions/guidance_bar.tsx) | Current action, recovery feedback, authored tip, and completion handoff                 |

The shell is a sibling of `#scene-root`, never an ancestor (asset-crop rule).

### Build pipeline (`pipeline/`)

All scripts that emit to `generated/` or produce `dist/` artifacts. Run by
`package.json` pre-hooks and `build_github_pages.sh`.

| File                                                           | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [gen_object_library.py](../pipeline/gen_object_library.py)     | YAML under `content/objects/` -> `generated/object_library.ts`; emits `OBJECT_LIBRARY` (per-object `state_schema`, `visual_states`, `subpart_state_schema`, and for grid-structured objects `subpart_geometry` + `view_box` per PATH-B), `ASSET_SPECS`, `OBJECT_STATE_SCHEMAS` (object-level state-field contract for store validation), `OBJECT_SUBPART_STATE_SCHEMAS` (subpart-level state-field contract). `state_fields` are the contract; `visual_states` are the rendering map.                 |
| [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py)         | Emits the final URL manifest and owns source-versus-compiled publication. Ordinary forms publish from source; material forms require their matching compiled artifact.                                                                                                                                                                                                                                                                                                                                |
| `pipeline/gen_liquid_regions.py`                               | Validated material SVG -> `generated/material_svg/<category>/<name>.svg` plus the single sorted `generated/liquid_regions.json` aggregate of opaque runtime handles, paint roles/adjustments, and resolved bounds.                                                                                                                                                                                                                                                                                    |
| [gen_scene_index.py](../pipeline/gen_scene_index.py)           | Scene YAML -> `generated/scenes.ts` + `generated/scene_manifest.json` (per-scene classification: emitted/skipped/errored); `--missing-svg=strict                                                                                                                                                                                                                                                                                                                                                      | placeholder`flag (default`placeholder`) |
| [gen_protocols.py](../pipeline/gen_protocols.py)               | Protocol YAML -> `generated/protocols.ts` + `generated/protocols_index_slim.ts` + `generated/protocol_materials.ts` (per-protocol material registry from each package `materials.yaml`). It validates and emits root `initial_state` entries as typed `InitialStateEntry` data rather than a free-form runtime payload.                                                                                                                                                                               |
| [gen_flow_view.py](../pipeline/gen_flow_view.py)               | Protocol YAML -> `generated/flow_views/<protocol_name>.txt`, a per-protocol audit view rendering the step chain, click path, gestures, and state changes already authored in `protocol.yaml`. An audit/consistency artifact only; the design source is the flow sketch an author writes before implementation, per [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md) and [PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md). Skips `sequence_runner` protocols (no authored `steps` of their own). |
| [entity_decode.py](../pipeline/entity_decode.py)               | Shared codegen helper: `decode_entities(s)` converts authored HTML entities (named + numeric) to Unicode at the string-emit choke points in `gen_protocols.py` (`to_ts_literal`) and `gen_object_library.py` (label emit), so committed source stays ASCII while `generated/**` carries the rendered glyph.                                                                                                                                                                                           |
| [build_protocol_index.py](../pipeline/build_protocol_index.py) | Protocol index helpers                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| [list_protocols.py](../pipeline/list_protocols.py)             | Parses `PROTOCOLS_INDEX` from generated TS; `emit` subcommand writes per-protocol HTML                                                                                                                                                                                                                                                                                                                                                                                                                |
| [scene_inheritance.py](../pipeline/scene_inheritance.py)       | Scene YAML inheritance resolution library (shared by gen_scene_index)                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| [build_main_bundle.mjs](../pipeline/build_main_bundle.mjs)     | esbuild Node API bundle: `src/launcher_entry.tsx` -> `dist/launcher.js`, `src/protocol_host_entry.tsx` -> `dist/protocol_host.js`                                                                                                                                                                                                                                                                                                                                                                     |
| [precompute_layout.mjs](../pipeline/precompute_layout.mjs)     | Runs the layout engine (`runPipeline`) for every scene at canonical 16:9 (1920x1080) -> `generated/precomputed_layout.ts` (`PRECOMPUTED_LAYOUT`: per-scene `{ final: ComputedItem[] }`). Runs via `node --import tsx` in `build_github_pages.sh` after `build_generated.sh`, since it imports the generated `SCENES`, `OBJECT_LIBRARY`, and `ASSET_SPECS`. Deterministic (scenes and items sorted) so two builds are byte-identical.                                                                  |

#### Material-rendered SVG compilation and runtime paint

Ordinary SVG forms are injected as opaque artwork and do not receive object-level
material painting. The anti-return lint rejects ordinary object-level fill
bindings and retired rectangle-overlay code. There is no migration fallback from
a material form to an ordinary anchor lookup.

The approved material path is dispatched solely by the exact root declaration.
The material-aware normalizer/compiler processes the self-describing SVG,
preserve and validate its closed `data-vlab-*` semantic contract, and emit both
a compiled SVG artifact and its opaque liquid-region manifest. Its source-to-
distribution flow is:

```text
assets/equipment/variable_volume/<form>.svg (data-vlab-rendering="material")
  -> material-aware normalization and semantic validation
  -> generated/material_svg/equipment/variable_volume/<form>.svg
     + generated/liquid_regions.json
  -> dist/assets/svg/equipment/<form>.svg
     + aggregate liquid-region manifest consumed at runtime
```

`validation/svg/asset_registry.py` is the one recursive source registry. It
requires globally unique stems and lets authoring paths change without changing
logical YAML names. `pipeline/gen_svg_manifest.py` deliberately flattens the
behavior directory at the publication boundary, so existing public URLs remain
stable. The Pages build publishes compiler artifacts at those ordinary final SVG
URLs and copies the aggregate manifest to `dist/assets/liquid_regions.json`.
The injection seam resolves opaque generated handles to host-local element
references. `liquid_paint.ts` applies role-derived OKLCH paint through inherited
CSS custom properties, keeps `bottom` fixed, scales `body` only in Y, translates
the fixed-shape `surface`, and updates a stationary-coordinate reveal boundary.
It never looks up or mutates
`anchor_liquid_bounds` / `anchor_liquid_clip`, creates an overlay rectangle,
or queries authored `data-vlab-*` attributes. The existing anchors and capacity
remain compiler inputs, and the object YAML binding uses no new token.

### Validation (`validation/`)

Python validators for YAML content, SVG assets, and protocol step flow.
Entry point: [validate.py](../validation/validate.py).

| Subtree                      | Purpose                                                                                                                                                                                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `validation/yaml_schema/`    | Schema and cross-field rules for protocol, object, and scene YAML                                                                                                                                                                                                                                                                                |
| `validation/stepper/`        | Protocol step-flow walker: holds one `StateMap` across every direct leaf of a runner, applies initial state, checks validator/outcome/scene-op semantics, and audits material transfer ledgers (units, fanout, channel/subpart addressing, source decrement, held-pipette clear, and timed transformations)                                      |
| `validation/svg/`            | SVG asset usage audit plus the semantic material-layer and object-selected asset-taxonomy boundaries. `material_anti_return_lint.py` is invoked by `pipeline/build_generated.sh` before generators, blocking retired rectangle overlays, direct authored semantic DOM access, malformed material forms, and ordinary object-level fill bindings. |
| `validation/manual/`         | Human-readable protocol manual renderer                                                                                                                                                                                                                                                                                                          |
| `validation/scene_lint/`     | Pre-render failure predictor (BLOCKED Group A / advisory Group B)                                                                                                                                                                                                                                                                                |
| `validation/scene_design/`   | Composition scorecard (weighted metrics, advisory only)                                                                                                                                                                                                                                                                                          |
| `validation/scene_calc/`     | Thin loader of rendered geometry (`generated/scene_render_stats/<scene>.stats.json`) for scene_lint and scene_design; computes no layout. Single geometry producer: the browser render pipeline (`tools/scene_to_png.mjs` -> `tools/scene_stats.mjs`).                                                                                           |
| `validation/structure/`      | Layout structural check                                                                                                                                                                                                                                                                                                                          |
| `validation/shared_toolkit/` | Shared discovery, YAML I/O, findings, reporter, CLI helpers                                                                                                                                                                                                                                                                                      |

### Testing (`tests/`)

Three tiers, isolated by [conftest.py](../tests/conftest.py)
(`collect_ignore = ["e2e", "playwright"]`):

- **Fast pytest** (`tests/test_*.py`): pyflakes, ASCII compliance, tab indentation,
  trailing whitespace, shebangs, import policy, init-file hygiene, protocol YAML
  validators, spec doc camelCase gate, test naming conventions, and more.
- **Node unit tests** (`tests/test_*.mjs`, run by `node --import tsx --test`):
  layout engine, step machine, structural guards, resolve_entry_scene,
  visual_state_resolver, scene operations, shell signals, walker
  no-step-branches, off-canvas classifier (`tests/test_layout_offcanvas.mjs`),
  config-precedence (`tests/test_layout_config.mjs`), and more.
- **Playwright browser tests** (`tests/playwright/`), runner model
  (`@playwright/test` + `playwright.config.ts` + `*.spec.ts`): framed-layout
  evidence, initial-scene evidence, interaction attrs, launcher, protocol host,
  solid walker, viewport sweep, and non-test `helper_*.mjs`/`.tsx` support
  files. `playwright.config.ts` owns the shared `webServer` (builds then
  serves `dist/` on one random port for every worker), so specs navigate
  against `baseURL` rather than each managing its own server. The full-path
  walkthrough lives under `tests/playwright/e2e/protocol_walkthrough.spec.ts`:
  one `test()` per curriculum protocol, discovered from
  `content/protocols/**/protocol.yaml` and driven by native Playwright workers
  (replacing the earlier custom worker-pool sweep), plus a wrong-order
  negative test. `run_playwright_tests.sh` is the front door for the whole
  suite (`npx playwright test`).
- **Non-browser E2E** (`tests/e2e/`): `e2e_*.py` runners for bandit security,
  facade smoke, gen_protocols, gen_scene_index, and scene_design CLI.

### Developer tools (`tools/`)

Developer-only helpers that do not appear in any build chain.

| File                                                                | Purpose                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [run_smoke.py](../tools/run_smoke.py)                               | Fast browser smoke test wrapper                                                                                                                                                                                                                                                   |
| [run_protocol_walkthrough.py](../tools/run_protocol_walkthrough.py) | Full protocol E2E wrapper                                                                                                                                                                                                                                                         |
| [build_test_fixture.sh](../tools/build_test_fixture.sh)             | Bundle a well-plate adapter for a Playwright test fixture directory                                                                                                                                                                                                               |
| `tools/normalize_svg_v3.py`                                         | SVG ingestion-gate normalizer (lxml + tinycss2 + shapely); see below                                                                                                                                                                                                              |
| `tools/svg_semantic_inspector.py`                                   | Read-only SVG inspector that reports material semantic-layer, clip, and level-frame bounds and geometry-matches donor variants to propose paint-changing candidates plus shared white/translucent review items; it never infers volume or replaces physical and renderer evidence |
| `tools/liquid_volume_contact_page.mjs`                              | Developer visual gate that serializes real compiled-liquid runtime output into a self-contained volume contact HTML page and PNG under `rendered-reports/liquid_volume_contacts/`; its sibling renderer script rebuilds the complete five-family sheet in one step                |
| `tools/liquid_render_harness.ts`                                    | Shared browser adapter used by the volume contact tool and focused Playwright tests; delegates injection and painting to production modules                                                                                                                                       |
| `tools/outline_svg_text.sh`                                         | Optional, on-demand Inkscape authoring preparer for approved physically intrinsic markings, including during legacy/import preparation; never an authorization to outline prose; validates its temporary SVG and publishes only when no live text remains                         |
| [check_css_content_policy.py](../tools/check_css_content_policy.py) | CSS content policy checker (invoked by check_codebase.sh)                                                                                                                                                                                                                         |
| [html_to_pdf.mjs](../tools/html_to_pdf.mjs)                         | Playwright-based HTML-to-PDF renderer                                                                                                                                                                                                                                             |
| [seam_types_compile_check.ts](../tools/seam_types_compile_check.ts) | Compile-time type check for seam interface literals                                                                                                                                                                                                                               |
| [README.md](../tools/svg_picker/README.md)                          | Browser-based SVG asset picker for content authors                                                                                                                                                                                                                                |
| [scene_to_png.mjs](../tools/scene_to_png.mjs)                       | `scene:png` -- renders a scene page to PNG + writes render-yield stats                                                                                                                                                                                                            |
| `tools/scene_render_diagnostics.mjs`                                | Pure DOM-evidence classifier and visual-bounding-box selector for scene render diagnostics                                                                                                                                                                                        |
| [protocol_to_png.mjs](../tools/protocol_to_png.mjs)                 | `protocol:png` -- renders a protocol page to PNG; records load outcomes                                                                                                                                                                                                           |
| [scene_stats.mjs](../tools/scene_stats.mjs)                         | `computeSceneStats` -- shared scene statistics helper                                                                                                                                                                                                                             |
| [bbox_helpers.mjs](../tools/bbox_helpers.mjs)                       | Shared bounding-box helper utilities used by scene tools                                                                                                                                                                                                                          |
| `tools/layout_golden_diff.mjs`                                      | `layout:diff` / `layout:refresh` -- ephemeral regression harness; captures and compares a gitignored layout baseline snapshot at `test-results/layout_reference_snapshot.json` with provenance (scene count, generated-layout hash, command, timestamp) and staleness detection   |
| `tools/layout_metrics.mjs`                                          | `layout:metrics` -- raw per-scene geometry metrics (rectangle-union fill, largest-empty-rect, per-zone and per-grid occupancy, per-object scale and floor proxies, label overlaps, AABB overlap graph, balance); per-scene overlay                                                |
| `tools/layout_health_report.mjs`                                    | `layout:health` -- interprets raw geometry metrics into provisional health categories and a worst-first author scorecard; writes `test-results/layout_health/health_report.{md,json}`                                                                                             |
| `tools/offcanvas_baseline.mjs`                                      | Reads `PipelineResult.offCanvasDiagnostics` for every scene and writes a baseline report to `docs/active_plans/audits/offcanvas_baseline.md`                                                                                                                                      |

#### SVG text outlining and ingestion-gate normalization

Source SVG art remains language-neutral: identity, state, and instructional
prose belong in layout-manager DOM labels or object data, leaving future
localization and accessibility work a clear ownership boundary. No i18n system
is being implemented now. When prose appears in imported art, remove it and
recreate it outside the SVG rather than path-converting it to pass normalization
or blind-recognition assessment. Approved physically intrinsic markings such as
numbers, scientific units or symbols, polarity, graduations, and plate
coordinates may remain in the art.

`tools/outline_svg_text.sh` is an optional, on-demand authoring preparation
step for an approved physically intrinsic marking, including one retained
during legacy/import preparation. Provenance never permits prose outlining. It
calls Inkscape with `--export-text-to-path`, writes to a same-directory
temporary file, verifies XML validity and the absence of `text`, `tspan`, and
`textPath` elements, then publishes the result. It is not a Brewfile entry,
required installation, runtime, or build dependency. Its default form refuses
an existing output; `--in-place` is explicit:

```bash
tools/outline_svg_text.sh raw.svg outlined.svg
tools/outline_svg_text.sh --in-place assets/equipment/static/my_asset.svg
```

`normalize_svg_v3.py` remains the separate SVG ingestion gate for ordinary
forms. The approved material-aware policy is a deliberate extension of that
pipeline, not a second generic normalizer; see [SVG_PIPELINE.md](specs/SVG_PIPELINE.md).

`normalize_svg_v3.py` is the SVG ingestion gate for ordinary static and
discrete-state forms. Every such SVG must pass through v3 before being added to
`assets/`. The tool has one job: either produce a guaranteed-safe normalized
file, or reject the input with a clear reason and suggested fix. There is no
"success with a warning" path. A form declaring
`data-vlab-rendering="material"` instead uses the material policy: shared
safety/geometry work plus semantic preservation,
post-normalization validation, and compiled-artifact/manifest generation.

**Pipeline** (stages execute in order):

```text
parse (lxml; recovery that alters input -> reject)
  -> classify features, reject unsupported (S2)
  -> transform flatten (A1: translate/scale/rotate/matrix, nested groups, arc-under-matrix SVD)
  -> shape->path (A2: rect, rounded-rect, circle, ellipse, line, polyline, polygon)
  -> editor-cruft removal (B1: Inkscape/Sodipodi/Adobe ns allowlist)
  -> optional floor-shadow removal (D1: --remove-floor-shadow, default off)
  -> compute bbox with stroke pad (A3: half stroke-width + miter allowance)
  -> decimal precision (A4)
  -> shift geometry + rewrite viewBox to cropped origin box
  -> serialize (S4: stable ns, UTF-8, no ns0:, final newline, preserve metadata/comments)
  -> reference-integrity check (S1: every internal ref resolves, or reject)
  -> emit diagnostics (--report-json)
```

**Two outcomes per file:** normalized (output parses, canonical invariant holds,
all refs resolve) or rejected (one primary reason code + suggested fix, non-zero
exit, no output written, input untouched).

**Ordinary-form canonical internal invariant:** after transform flattening and
shape conversion, all visible geometry on normalized elements is absolute path
data in root coordinates with no geometry-affecting `transform` remaining. The
hidden `anchor_liquid_bounds` resource is the narrow exception: it remains an
untransformed root-coordinate `<rect>` as compiler input; ordinary published
forms treat it as inert metadata. For a material form, the compiler consumes and
removes that bounds anchor before publication. The
compiled gravity-part region still references the retained clip definition, but runtime
uses only generated handles and never queries or mutates either authored anchor.
`gradientTransform`/`patternTransform` are paint-space exemptions.

**Dependencies** (declared in `pip_requirements-dev.txt`):

- `lxml`: XML parse and serialize (preferred over ElementTree for namespace control)
- `tinycss2`: CSS `<style>` block parsing; used to rewrite `url(#id)` refs on ASCII rename (F8) and to detect geometry-affecting CSS rules
- `shapely`: bounded geometry primitive for simple-clipPath flattening; curves are flattened to polylines within a fixed tolerance before intersection

**Ordinary-form normalizer support contract** -- every feature has one
disposition. Material-declared forms use the approved semantic policy above,
which preserves validated semantic group boundaries rather than flattening or
merging across them:

| Feature                                                                        | Disposition                                                                                                                                 |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`             | normalize -> absolute path in root coords                                                                                                   |
| element `transform` (translate/scale/rotate/matrix/skew), nested groups        | normalize -> flatten into coords                                                                                                            |
| `gradientTransform`, `patternTransform`                                        | preserve (paint-space only)                                                                                                                 |
| simple `clipPath` (one path/shape, no nested clips/mask/filter/text/image/use) | normalize -> flatten to path geometry, drop clip ref                                                                                        |
| complex `clipPath`                                                             | reject (`CLIPPATH_UNSUPPORTED_COMPLEX`)                                                                                                     |
| `filter`, `mask`, `marker`                                                     | reject                                                                                                                                      |
| `<text>`, `<tspan>`, `textPath`                                                | reject (`TEXT_UNSUPPORTED`); remove prose to layout-manager DOM/object data, then outline only approved intrinsic markings before ingestion |
| `<use>`, `<symbol>`                                                            | reject (`USE_OR_SYMBOL_UNSUPPORTED`)                                                                                                        |
| `<image>` base64 or external `href`                                            | reject (`EMBEDDED_RASTER_UNSUPPORTED` / `EXTERNAL_RESOURCE_UNSUPPORTED`)                                                                    |
| `foreignObject`                                                                | reject                                                                                                                                      |
| `<script>`, `on*=`, animation                                                  | reject (`SCRIPT_OR_HANDLER` / `ANIMATION_UNSUPPORTED`)                                                                                      |
| `<!DOCTYPE>` / `<!ENTITY>`                                                     | reject (`DOCTYPE_OR_ENTITY`)                                                                                                                |
| inline `style=` geometry/cleanup props                                         | normalize (resolve listed props from inline styles)                                                                                         |
| `<style>` block                                                                | preserve; rewrite `url(#id)` refs on rename (F8); reject if geometry-affecting rule found (`STYLE_GEOMETRY_UNSUPPORTED`)                    |
| editor cruft (Inkscape/Sodipodi/Adobe ns)                                      | normalize (remove, B1 allowlist)                                                                                                            |
| `dc/cc/rdf` metadata, `<title>`, `<desc>`, pre-root comments                   | preserve                                                                                                                                    |
| parse failure                                                                  | reject (`PARSER_ERROR`)                                                                                                                     |

**Rejection reason codes** (stable tokens used in reports and tests):
`TEXT_UNSUPPORTED`, `USE_OR_SYMBOL_UNSUPPORTED`, `FILTER_UNSUPPORTED`,
`MASK_UNSUPPORTED`, `MARKER_UNSUPPORTED`, `CLIPPATH_UNSUPPORTED_COMPLEX`,
`FOREIGNOBJECT_UNSUPPORTED`, `EXTERNAL_RESOURCE_UNSUPPORTED`,
`EMBEDDED_RASTER_UNSUPPORTED`, `DOCTYPE_OR_ENTITY`, `SCRIPT_OR_HANDLER`,
`ANIMATION_UNSUPPORTED`, `STYLE_GEOMETRY_UNSUPPORTED`, `STYLE_UNPARSEABLE`,
`UNSUPPORTED_TRANSFORM`, `UNSUPPORTED_UNIT`, `NONSCALING_STROKE_UNRESOLVED`,
`PARSER_ERROR`, `UNRESOLVED_REFERENCE`, `PATTERN_UNSUPPORTED`, `EMPTY_GEOMETRY`.

**CLI options:** `-i`/`-o`, `--in-place`, `--padding`, `--remove-floor-shadow`,
`--shadow-dry-run`, `--report-json`, `--self-test`.

**Note on simple-clipPath flattening:** simple-clipPath flattening (A6) is part of
the v3 design and uses shapely. It is implemented in v3; the shapely package must
be installed for that path to execute. Complex clips always reject regardless.

**Ingestion workflow:** run v3 on every SVG before placing it in `assets/`.
If v3 rejects, fix the asset per the reason code (examples: remove prose text
and move it to layout-manager DOM; outline only approved intrinsic markings for
`TEXT_UNSUPPORTED`; pre-flatten filters or masks before ingestion for
`FILTER_UNSUPPORTED`; remove scripts for `SCRIPT_OR_HANDLER`) and re-run. A
normalized output is written only when all verification gates pass.

```bash
tools/outline_svg_text.sh raw.svg outlined.svg
source source_me.sh && python3 tools/normalize_svg_v3.py -i outlined.svg -o assets/equipment/static/
# or to normalize in place after copying:
source source_me.sh && python3 tools/normalize_svg_v3.py --in-place assets/equipment/static/my_asset.svg
```

**Placement:** `tools/` (dev utility; emits nothing to `generated/` or `dist/`;
not wired into any build script or `package.json` hook). The corpus
re-normalization sweep and the CI/pre-commit ingestion gate are follow-up work
after v3 proves stable on the corpus and one import batch.

## Data flow

Opening a protocol page end-to-end:

```text
Browser loads dist/<protocol_name>.html
  |
  v
dist_entry.tsx: sees window.__PROTOCOL_NAME__ + #scene-root + #shell-root
  |
  v
protocol_host.tsx: look up ProtocolConfig in generated/protocols.ts
  |
  v
flatten_sequence_runner(): validate unique direct mini leaves and form one
  chained step list; retain only the runner root initial_state
  |
  v
resolve_entry_scene_name(): entry step's scene: field -> SceneChange fallback -> throw
  |
  v
resolve_precomputed_result(scene_name, scene): single production layout path
  |     PRECOMPUTED_LAYOUT[scene_name].final (build-time, 16:9; throws if missing)
  |     -> make_precomputed_result(scene, final) -> PipelineResult
  |
  | (WP-PRECOMP3: runPipeline retired from the shipped bundle. The runtime
  |  engine -- normalizeSchema -> resolveInheritance -> bindObjects ->
  |  scaleToRealWorld -> lowerSceneZones -> groupByZone -> horizontalLayout ->
  |  verticalFootprintFor -> reflowZones -> verticalLayout -> layoutLabels ->
  |  clampSceneBounds -- now runs only at BUILD time in
  |  pipeline/precompute_layout.mjs and in tests.)
  |
  v
renderScene(#scene-root, result): mounts Solid SceneView -> structural guards
  (collect violations, set data-scene-degraded + console.warn instead of
  throwing) -> renderBackground -> SceneItem per placement (inject_svg or
  placeholder) -> label elements
  |
  v
assert_scene_not_empty(): throws for student protocols with 0 items
  |
  v
createProtocolShellEmitter(): emitter + initial ShellViewSnapshot
create_scene_op_handler(build_store_scene_op_deps(store, render_scene)):
  ops write the reactive scene_store (SceneChange re-renders + reconciles)
install_walker_debug_surface(): window.PROTOCOL_STEPS + window.gameState (read-only)
create_step_machine(): pure step machine, no DOM
attach_click_resolver(): DOM click -> step machine
  |
  v
ProtocolHud.mount(#shell-root): StepOutline, TipsBubble, StepCounter, GuidanceBar
  subscribes via Solid signal to emitter snapshot
  |
  v
step_machine.start(): emits step_started for entry step -> HUD renders first prompt
  |
  v
Student clicks a visible whole-object or exact-subpart data-item-id
  -> click_resolver -> step_machine.handle_click()
  -> dispatch_interaction_validator() -> on success: scene_operations write
     the reactive scene_store -> Solid renderer reacts (artwork/highlight) and
     window.gameState reflects progress
  -> emit step progress events -> HUD re-renders
```

Scene operations are store-driven (WS-M3-D): `ObjectStateChange` writes both
the active projection and the durable session archive, so the Solid renderer
updates the affected item reactively and a later scene can rehydrate it.
`SceneChange` re-renders the next scene, reconciles its target projection, and
preserves cursor-held tool/material. `TimedWait` marks a visible, input-blocking
equipment phase and supports the following authored state transformation;
`LayoutMove` is an explicit reported no-op (zero authored uses, Option A). The
read-only `window.gameState` / `window.PROTOCOL_STEPS` surfaces give the walker
the active target, revision, and last declared-state delta without allowing it
to mutate protocol progress. Full PRIMARY_CONTRACT item 4 completion (every
student-visible protocol walked end-to-end) is the M4 corpus gate.

## Solid.js import boundary

Solid.js is the reactive rendering framework. Its imports are permitted only
in specific subtrees. This boundary is declared here and enforced by
[test_typescript_boundaries.py](../tests/test_typescript_boundaries.py).

```text
Solid ALLOWED:    src/shell/
                  src/scene_runtime/renderer/
                  src/scene_runtime/state/

Solid FORBIDDEN:  src/scene_runtime/layout/
                  src/scene_runtime/protocol/
                  pipeline/
                  validation/
                  generated/
```

Rationale for each zone:

- `src/shell/` - the HUD observer layer; already uses Solid signals and
  components.
- `src/scene_runtime/renderer/` - hosts the Solid scene components
  (`SceneView`, `SceneItem`) that consume `PipelineResult` and emit the
  stable `data-*` DOM contract. The imperative item-paint path is retired.
- `src/scene_runtime/state/` - hosts the reactive object-state store
  (Solid signals/stores); object-state reactivity is Solid's job.
- `src/scene_runtime/layout/` - pure geometry pipeline; must never depend
  on the reactive framework. If layout uses Solid, two layout systems exist.
- `src/scene_runtime/protocol/` - the step machine (stepper); must not
  depend on Solid as a component. The stepper calls store operations through
  a small runtime bridge. Exception: `import type` statements that reference
  Solid types from the state layer are permitted (type-only, no runtime cost).
- `pipeline/` - build pipeline scripts that emit to `generated/`; must not
  depend on the reactive framework.
- `validation/` - Python-based YAML validators and protocol stepper simulation;
  TypeScript files here must not depend on the reactive framework.
- `generated/` - compiled YAML data files; must not import Solid.

The lint rule is enforced at pytest time. A violation in any forbidden zone
fails the `pytest tests/` gate.

## Testing and verification

```bash
# Fast pytest gate (Python)
pytest tests/

# Node unit tests (TypeScript modules, no browser)
npm run pretest:node && node --import tsx --test tests/test_*.mjs

# Codebase check gate (typecheck, lint, format, node tests)
bash check_codebase.sh

# Umbrella fast gate (build, check_codebase.sh, pytest, content validation)
bash run_fast_checks.sh

# Browser test suite (builds dist/ as needed, then runs every *.spec.ts,
# including the protocol walker sweep spec, through the Playwright runner)
bash run_playwright_tests.sh

# A single spec, or a subset, via the same front door
bash run_playwright_tests.sh tests/playwright/smoke.spec.ts
```

What each gate checks:

- **pytest**: pyflakes, ASCII compliance, tab indentation, shebang hygiene,
  import policy, init-file hygiene, protocol YAML validators, markdown links,
  test naming conventions, spec doc camelCase gate.
- **node tests**: layout engine pipeline, step machine, structural guards,
  entry-scene resolution, visual_state_resolver, scene operations,
  protocol emitter, shell signals, walker no-step-branches.
- **check_codebase.sh**: TypeScript typecheck (tsconfig.json + tsconfig.lint.json),
  ESLint zero warnings, Prettier format check, CSS content policy, node unit tests.
- **Playwright** (runner model, `playwright.config.ts` + `*.spec.ts`):
  framed-layout measurable evidence, initial-scene rendering evidence, and the
  full-path walker sweep under `tests/playwright/e2e/protocol_walkthrough.spec.ts`
  (one `test()` per curriculum protocol, native Playwright workers, plus a
  wrong-order negative test), all served by the config's shared `webServer`.
- **run_fast_checks.sh**: umbrella fast gate that runs the build, `check_codebase.sh`,
  `pytest tests/`, and content validation; it excludes the slower browser test
  suite, which runs separately through `run_playwright_tests.sh`.
- **run_playwright_tests.sh**: builds `dist/` as needed, then runs
  `npx playwright test` against `playwright.config.ts`, which covers every
  `.spec.ts` file including the walker sweep, and prints a final PASS/FAIL line.

See [E2E_TESTS.md](E2E_TESTS.md) and [PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md)
for browser-test conventions.

## Extension points

- **New mini-protocol**: create `content/protocols/<cluster>/<name>/` with
  `protocol.yaml`, a `scenes/` directory, and optionally `materials.yaml`.
  Re-run the four pipeline generators (`npm run prebuild`).
  See [specs/PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md).
- **New scene**: add a YAML file under `content/base_scenes/` or alongside a
  protocol's `scenes/` directory. Re-run `pipeline/gen_scene_index.py`.
  See [specs/SCENE_YAML_FORMAT.md](specs/SCENE_YAML_FORMAT.md).
- **New scene region component**: add a Solid `.tsx` file under
  `src/shell/regions/` and mount it in `src/shell/hud/protocol_hud.tsx`.
- **New pipeline generator**: add the script to `pipeline/` (not `tools/`);
  register it in `package.json` `prebuild` and `pretest:node` hooks;
  update [FILE_STRUCTURE.md](FILE_STRUCTURE.md) and
  [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) in the same patch
  (per `AGENTS.md` binding-location rule).
- **New validation rule**: add to the appropriate `validation/yaml_schema/`
  or `validation/scene_lint/` module; new rules in `scene_lint` must go
  through Group A (BLOCKED) or Group B (advisory) classification.

## Known gaps

- `LayoutMove` remains an explicit reported no-op (zero authored uses, Option
  A). Verify a real authored drag workflow before changing this semantic seam.
- `drag` has no content protocol yet. The drag affordance and
  `step_machine.handle_drag_commit` are wired and unit-tested, but the walker
  sweep still classifies a `drag` interaction `unsupported_gesture` because no
  authored protocol exercises it; adding `drag` to the walker's supported set is
  a one-line change once a real drag protocol lands.
