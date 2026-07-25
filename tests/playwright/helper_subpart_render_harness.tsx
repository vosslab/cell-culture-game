// tests/playwright/helper_subpart_render_harness.tsx
//
// TEST-ONLY harness entry (helper_-prefixed; never a production route).
// Bundled on the fly by test_subpart_well_plate_render.mjs with esbuild +
// esbuild-plugin-solid, served, and driven by Playwright to prove the GENERIC
// structured-subpart material-tint renderer (M3 WP-SUBPART-RENDER) through the
// PRODUCTION render path (runPipeline -> mountScene -> SceneView -> SceneItem ->
// SubpartVisualStateOverlay).
//
// This harness mounts the SAME production mountScene + scene_store, using the
// REAL generated plate_focus_bench scene (which places well_plate_96). It drives
// per-well state ONLY through the store's normal seed/write path:
//   - seed_subpart  -> store.seed_target  (the scene-op layer's subpart seed)
//   - write_subpart -> store.set_object_state (the ObjectStateChange write)
// It NEVER hand-edits the DOM, never mutates the renderer, and never bypasses the
// store's schema validation. The well_plate_96 subpart material_name enum is the
// closed sentinel FLOOR [empty, mixed]; runtime acceptance is registry-backed
// (D1): a non-sentinel material is accepted at a well only when registered in the
// active protocol's registry. The harness wires that registry into the store
// (create_scene_store(MATERIAL_REGISTRY)) exactly as protocol_host does, so it can
// write:
//   - mixed       -> the built-in color #686868 (painted, no registry needed)
//   - empty       -> null color -> fill "transparent" (no fill; base art shows)
//   - carboplatin -> a REGISTERED drug -> its scalar display_color #a719db
//     (registry-backed acceptance + registry-backed color, end to end)
//
// The registry is supplied to BOTH the store (acceptance) and mountScene (color
// resolution), exercising the full production materialRegistry path.

import { runPipeline } from "../../src/scene_runtime/layout/index.js";
import { mountScene } from "../../src/scene_runtime/renderer/index.js";
import { create_scene_store, type SceneStore } from "../../src/scene_runtime/state/scene_store.js";
import { SCENES } from "../../generated/scenes.js";
import { OBJECT_LIBRARY, ASSET_SPECS } from "../../generated/object_library.js";
import type { MaterialRegistry } from "../../src/scene_runtime/renderer/visual_state_resolver.js";

// The plate-focused production scene that places well_plate_96
// (placement foreground_well_plate_96).
const SCENE_NAME = "plate_focus_bench";
const PLATE_OBJECT = "well_plate_96";

// A small material registry. carboplatin is the registered drug the drug-color
// render proof writes; its scalar display_color #a719db matches the production
// registry (generated/protocol_materials.ts). media exercises a second registry
// entry. The sentinels (mixed, empty) need no registry entry.
const MATERIAL_REGISTRY: MaterialRegistry = {
  carboplatin: { label: "Carboplatin solution", display_color: "#a719db" },
  media: { label: "Growth media", display_color: "#e87fb0" },
};

// The store is created WITH the registry so subpart material acceptance is
// registry-backed (D1) -- exactly as protocol_host wires it. This lets the
// harness write a registered drug to a well through the normal store path.
const store: SceneStore = create_scene_store(MATERIAL_REGISTRY);
let dispose_fn: (() => void) | null = null;

function get_scene_root(): HTMLElement {
  const el = document.getElementById("scene-root");
  if (!(el instanceof HTMLElement)) {
    throw new Error("subpart render harness: #scene-root not found");
  }
  return el;
}

// Mount the real plate_focus_bench scene through the production path. seed_from_scene
// (run inside mountScene) seeds object-level targets only; subpart targets are
// seeded on demand by seed_subpart below, exactly as the scene-op layer will.
function do_mount(): void {
  if (dispose_fn) {
    dispose_fn();
    dispose_fn = null;
  }
  const scene = SCENES[SCENE_NAME];
  if (!scene) {
    throw new Error(`subpart render harness: unknown scene ${SCENE_NAME}`);
  }
  const result = runPipeline(scene, { library: OBJECT_LIBRARY, assets: ASSET_SPECS });
  dispose_fn = mountScene(get_scene_root(), result, {
    store,
    materialRegistry: MATERIAL_REGISTRY,
  });
}

function do_dispose(): void {
  if (dispose_fn) {
    dispose_fn();
    dispose_fn = null;
  }
}

declare global {
  interface Window {
    __subpart_harness: {
      mount(): void;
      dispose(): void;
      // Seed one well subpart through the store's normal subpart seed path.
      seed_subpart(subpart_name: string): void;
      // Write declared subpart state through the store's normal write path
      // (schema + enum validated). Throws if the value is not in the subpart
      // enum, which is correct: the harness must not bypass validation.
      write_subpart(subpart_name: string, partial: Record<string, string | number | boolean>): void;
      PLATE_OBJECT: string;
    };
  }
}

window.__subpart_harness = {
  mount: do_mount,
  dispose: do_dispose,
  seed_subpart(subpart_name: string): void {
    // Build the subpart target ("well_plate_96.A1") and seed it via the store's
    // targeted insert. A no-op if already seeded; never resets siblings.
    store.seed_target({ target: `${PLATE_OBJECT}.${subpart_name}`, object_name: PLATE_OBJECT });
  },
  write_subpart(subpart_name: string, partial: Record<string, string | number | boolean>): void {
    store.set_object_state(`${PLATE_OBJECT}.${subpart_name}`, partial);
  },
  PLATE_OBJECT,
};
