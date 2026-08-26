// Scene rendering. Public Solid mount facade for the scene renderer.
//
// This module is the durable public mount facade. It mounts the Solid
// <SceneView> into a root element and OWNS the active scene's Solid root
// dispose function.
//
// Two entry points:
//   - renderScene(root, result, viewport?): backwards-compatible facade used by
//     the scene viewer and protocol host. It creates an internal store,
//     seeds it from the PipelineResult, mounts SceneView, and tracks the
//     dispose handle PER ROOT so a re-render into the same root disposes the
//     prior Solid root first (no orphan roots/effects/listeners). Returns void
//     for source compatibility with existing callers.
//   - mountScene(root, result, opts): the full mount surface. Accepts an
//     external store + material registry and RETURNS a dispose handle. The
//     store-driven scene_operations layer uses this so it can hold the store,
//     drive ObjectStateChange writes, and dispose on SceneChange.
//
// Report-mode + structural-guard behavior, label sizing, background, and the
// depth-ordered item/label emission all live in scene_view.tsx now; this file
// is the lifecycle owner.
//
// Lifecycle (plan "Browser runtime constraints"): a Solid root created by
// render() must be disposed to release its effects/listeners. renderScene
// tracks one dispose per root in a WeakMap and calls it before mounting a new
// root into the same element. protocol_host calls the returned dispose on
// teardown; SceneChange disposes before mounting the next scene.

import { render } from "solid-js/web";

import type { PipelineResult } from "../layout/types.js";
import { create_scene_store, type SceneStore } from "../state/scene_store.js";
import type { ActiveAffordanceAccessor } from "../protocol/affordance.js";
import { enumerate_candidate_targets } from "./affordance_candidates.js";
import type { MaterialRegistry } from "./visual_state_resolver.js";
import { SceneView, build_seed_list } from "./scene_view.js";

//============================================
// Public dispose handle
//============================================

// Disposing a mounted scene tears down its Solid root: every reactive effect,
// memo, and ref-attached listener created under the root is released, and the
// rendered DOM children are removed.
export type SceneDispose = () => void;

// Per-root dispose tracking for the backwards-compatible renderScene facade.
// A WeakMap keyed by the root element so a second renderScene into the same
// root disposes the first mount without leaking the prior Solid root.
const ROOT_DISPOSERS = new WeakMap<HTMLElement, SceneDispose>();

//============================================
// Full mount surface
//============================================

// Options for mountScene. store and materialRegistry are supplied by the
// caller (the scene-op layer / protocol host) so the same reactive store
// drives both the renderer and the protocol operations.
export interface MountSceneOptions {
  // External reactive store. The scene is seeded from the PipelineResult into
  // this store before mounting.
  store: SceneStore;
  // Active protocol's material registry (per-package materials.yaml), or null
  // when no protocol material context exists (e.g. the scene viewer). A provided
  // registry is authoritative; null disables material-color resolution.
  materialRegistry: MaterialRegistry | null;
  // Optional pixel viewport used by the aspect structural guard. Must match the
  // viewport passed to runPipeline so the aspect check is consistent.
  viewport?: { w: number; h: number };
  // Store seeding policy. "replace" is a fresh mount; "reconcile" preserves
  // declared state for exact targets present in both scenes while adding and
  // dropping targets to match the new scene; "none" is for harnesses that
  // deliberately pre-seed the store. Defaults to "replace".
  seedMode?: "replace" | "reconcile" | "none";
  // Optional active-affordance accessor (affordance plumbing). When provided,
  // the renderer derives each scene object's highlight ring from the active
  // interaction read through this accessor in arrow form (Solid store-dep rule).
  // Absent for the scene viewer / facade render, where no protocol interaction
  // context exists, so no highlight ring is computed. Passed by reference into
  // SceneItem.
  activeAffordance?: ActiveAffordanceAccessor;
  // Host-owned sibling root for the SceneView's non-occluding state-text rail.
  // Production browser hosts must provide it. It is optional only for
  // deliberately state-free renderer harnesses; SceneView fails loudly if
  // resolved state text would otherwise be omitted.
  annotationRoot?: HTMLElement;
}

// Mount a Solid scene into root, returning a dispose handle. Clears root first,
// applies the requested store-seeding policy, then renders SceneView. The
// returned dispose tears down the Solid root; any previously tracked dispose
// for this root is invoked first.
export function mountScene(
  root: HTMLElement,
  result: PipelineResult,
  opts: MountSceneOptions,
): SceneDispose {
  // Dispose any prior mount in this root before clearing + mounting a new one.
  const prior = ROOT_DISPOSERS.get(root);
  if (prior) {
    prior();
    ROOT_DISPOSERS.delete(root);
  }

  // Clear root via removeChild loop (no innerHTML; matches the old renderer's
  // one allowed clear site). render() appends the Solid tree afterward.
  while (root.firstChild) {
    root.removeChild(root.firstChild);
  }

  // Stamp the scene's workspace kind on the root so CSS can gate render-layer
  // effects (e.g. the warm bench-surface ::after band) on workspace type.
  // Hood and microscope workspaces must not render a bench surface cue.
  // This attribute is cleared in the dispose function below.
  root.setAttribute("data-scene-workspace", result.scene.workspace);

  const seeds = build_seed_list(result);
  const seed_mode = opts.seedMode ?? "replace";
  if (seed_mode === "replace") {
    opts.store.seed_from_scene(seeds);
  } else if (seed_mode === "reconcile") {
    opts.store.reconcile_scene(seeds);
  }

  // Enumerate the resolver-accepted candidate object names ONCE per scene mount.
  // Reuses the same PipelineResult.final the renderer stamps as data-item-id and
  // the click resolver walks, so candidates never drift from selectable objects
  // (see affordance_candidates.ts enumerate_candidate_targets). Passed by reference into the
  // scene items; per-item memos only call .has() (O(1)) and never rebuild it.
  const candidate_targets = enumerate_candidate_targets(result);

  // Mount the Solid view. render() returns its own dispose function.
  const solid_dispose = render(
    () => (
      <SceneView
        root={root}
        result={result}
        store={opts.store}
        materialRegistry={opts.materialRegistry}
        viewport={opts.viewport}
        activeAffordance={opts.activeAffordance}
        candidateTargets={candidate_targets}
        annotationRoot={opts.annotationRoot}
      />
    ),
    root,
  );

  const dispose: SceneDispose = () => {
    solid_dispose();
    // Remove the background + degraded markers SceneView set on the root so a
    // disposed scene leaves the root clean for the next mount.
    root.style.background = "";
    root.removeAttribute("data-scene-root");
    root.removeAttribute("data-scene-degraded");
    root.removeAttribute("data-degraded-violation-count");
    root.removeAttribute("data-bg-asset-pending");
    // Remove the workspace stamp set above so a re-mounted scene always gets
    // the correct workspace class from its own PipelineResult.
    root.removeAttribute("data-scene-workspace");
    if (ROOT_DISPOSERS.get(root) === dispose) {
      ROOT_DISPOSERS.delete(root);
    }
  };

  ROOT_DISPOSERS.set(root, dispose);
  return dispose;
}

//============================================
// Backwards-compatible facade
//============================================

/**
 * Render a complete scene from a PipelineResult into root.
 *
 * Backwards-compatible facade matching the historical signature. Internally it
 * mounts the Solid SceneView with a fresh internal store seeded from the
 * PipelineResult. Calling it again on the same root disposes the prior Solid
 * root first, so reused roots never leak effects or listeners.
 *
 * @param root - HTMLElement (typically #scene-root) to render into
 * @param result - PipelineResult from runPipeline
 * @param viewport - Optional pixel dimensions of the scene root panel. When
 *                   provided, the aspect structural guard uses these dimensions.
 *                   Must match the viewport passed to runPipeline.
 */
export function renderScene(
  root: HTMLElement,
  result: PipelineResult,
  viewport?: { w: number; h: number },
  annotationRoot?: HTMLElement,
): void {
  // Fresh internal store per facade render. The state-free contract render
  // seeds declared object fields to their schema defaults.
  const store = create_scene_store();
  const options: MountSceneOptions = {
    store,
    // No protocol context in the facade render path: material colors cannot be
    // resolved without a protocol's materials.yaml, so null disables color.
    materialRegistry: null,
  };
  if (viewport !== undefined) {
    options.viewport = viewport;
  }
  if (annotationRoot !== undefined) {
    options.annotationRoot = annotationRoot;
  }
  mountScene(root, result, options);
}
