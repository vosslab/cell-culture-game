// tests/playwright/helper_degrade_harness.tsx
//
// TEST-ONLY harness entry (helper_-prefixed; never a production route).
// Bundled on the fly by test_scene_degrade.mjs with esbuild + esbuild-plugin-solid.
//
// Purpose: exercise the fail-loud degrade path added by the FIX-3 audit fix,
// THROUGH THE PRODUCTION RENDER PATH (mountScene -> SceneView -> SceneItem).
// Earlier this harness mounted bare SceneItem instances and manually stamped
// data-scene-root, which masked the SceneView onMount/child-effect ordering this
// test is meant to verify. It now mounts a hand-built PipelineResult via the
// SAME mountScene + SceneView used in production, so the test validates the real
// first-render scene-degraded promotion (now owned reactively by SceneView).
//
// When resolve_visual_state throws (unknown formula token), SceneItem must:
//   1. console.warn loud,
//   2. stamp data-resolver-degraded="<message>" on the item node,
//   3. notify SceneView, which sets data-scene-degraded="true" on the scene root
//      ON FIRST RENDER (ordering-independent),
//   4. still render the item's bound asset (NEVER blank / never removed).
//
// Two synthetic OBJECT_LIBRARY entries are injected at runtime:
//   - "test_degrade_obj": valid state_schema with a material_volume field,
//     but a visual_states formula using an UNKNOWN token ("badtoken") that
//     causes parse_formula_expr to throw.
//   - "test_happy_obj": valid state_schema AND an explicit nonvisual
//     declaration for its amount field. No degrade expected.
//
// The two items are positioned inside scene_bounds with empty label lists so the
// hand-built scene produces ZERO structural violations. That guarantees a
// data-scene-degraded="true" comes ONLY from the resolver-promotion path, not
// from SceneView's structural-violation marker.

import { mountScene } from "../../src/scene_runtime/renderer/index.js";
import { derive_scene_interaction_geometry } from "../../src/scene_runtime/layout/interaction_geometry.js";
import { create_scene_store, type SceneStore } from "../../src/scene_runtime/state/scene_store.js";
import {
  ASSET_SPECS,
  OBJECT_LIBRARY,
  OBJECT_STATE_SCHEMAS,
} from "../../generated/object_library.js";
import type {
  ComputedItem,
  ObjectDef,
  ObjectVisualStates,
  ObjectStateSchema,
  PipelineResult,
  SceneA,
} from "../../src/scene_runtime/layout/types.js";

//============================================
// Synthetic object definitions
//============================================

// BAD visual_states: formula uses an unknown token so parse_formula_expr throws.
const BAD_VISUAL_STATES: ObjectVisualStates = {
  material_volume: {
    kind: "composite",
    applies_to: "object",
    // "badtoken" is NOT in the closed token set; the parser will throw:
    //   visual_state_resolver: unknown formula token 'badtoken': ...
    formula: "badtoken(state(material_volume), capacity_ml=10.0)",
  },
};

// GOOD visual_states: the seeded amount field is intentionally nonvisual.
// Static complete-form objects use this closed declaration when their retained
// amount state should not drive generated geometry or an authored liquid anchor.
const GOOD_VISUAL_STATES: ObjectVisualStates = {
  material_volume: {
    kind: "composite",
    applies_to: "object",
  },
};

// Shared state_schema for both objects: one float field with default 5.0.
const SHARED_STATE_SCHEMA = {
  material_volume: {
    field_name: "material_volume",
    type: "float" as const,
    default: 5.0,
    applies_to: "object" as const,
    unit: "ml",
    min: 0,
    max: 10.0,
  },
};

const DEGRADE_OBJ_NAME = "test_degrade_obj";
const HAPPY_OBJ_NAME = "test_happy_obj";
const HARNESS_ASSET = "waste_container";
const HARNESS_VIEWPORT = { w: 1200, h: 675 };
const HARNESS_VISUAL_WIDTH = 10;

// Keep this synthetic PipelineResult aligned with the generated asset contract,
// rather than copying a viewBox aspect that can legitimately change when the
// scientific asset is redesigned. Structural guard 5 consumes this same
// generated aspect at runtime.
function get_harness_asset_aspect(): number {
  const asset_spec = ASSET_SPECS[HARNESS_ASSET];
  if (asset_spec === undefined) {
    throw new Error(`degrade harness: missing generated asset spec for ${HARNESS_ASSET}`);
  }
  return asset_spec.aspect;
}

const HARNESS_ASSET_ASPECT = get_harness_asset_aspect();

// Both maps must be patched: OBJECT_LIBRARY is read by SceneItem (visual_states)
// and OBJECT_STATE_SCHEMAS by scene_store.seed_from_scene (default seeding).
(OBJECT_STATE_SCHEMAS as Record<string, ObjectStateSchema>)[DEGRADE_OBJ_NAME] = SHARED_STATE_SCHEMA;
(OBJECT_STATE_SCHEMAS as Record<string, ObjectStateSchema>)[HAPPY_OBJ_NAME] = SHARED_STATE_SCHEMA;

// Reuse a real asset (waste_container) so the bound asset resolves in the SVG
// registry and the structural asset guard stays clean.
(OBJECT_LIBRARY as Record<string, ObjectDef>)[DEGRADE_OBJ_NAME] = {
  object_name: DEGRADE_OBJ_NAME,
  kind: "waste",
  label: "Test Degrade Object",
  asset: HARNESS_ASSET,
  capabilities: ["clickable"],
  layout: { default_width: 5, label_width: 8, anchor_y: "bottom", anchor_y_offset: 0 },
  state_schema: SHARED_STATE_SCHEMA,
  visual_states: BAD_VISUAL_STATES,
  subpart_state_schema: {},
};

(OBJECT_LIBRARY as Record<string, ObjectDef>)[HAPPY_OBJ_NAME] = {
  object_name: HAPPY_OBJ_NAME,
  kind: "waste",
  label: "Test Happy Object",
  asset: HARNESS_ASSET,
  capabilities: ["clickable"],
  layout: { default_width: 5, label_width: 8, anchor_y: "bottom", anchor_y_offset: 0 },
  state_schema: SHARED_STATE_SCHEMA,
  visual_states: GOOD_VISUAL_STATES,
  subpart_state_schema: {},
};

//============================================
// Hand-built clean PipelineResult
//============================================

// Build one computed item placed well inside scene_bounds with NO label (so the
// label structural guards are skipped) and an aspect derived from the bound
// asset's generated specification (so the aspect guard stays clean when the
// asset artwork evolves).
function make_item(object_name: string, x_offset: number): ComputedItem {
  // Structural guard 5 calculates rendered aspect as
  // (_visualWidth / _height) * viewportAspect. Solve that formula for height
  // using the generated viewBox aspect so this hand-built item follows the
  // same geometry contract as a PipelineResult.
  const viewport_aspect = HARNESS_VIEWPORT.w / HARNESS_VIEWPORT.h;
  const visual_height = (HARNESS_VISUAL_WIDTH * viewport_aspect) / HARNESS_ASSET_ASPECT;
  return {
    placement_name: object_name,
    object_name,
    zone: "center",
    depth: "mid",
    kind: "waste",
    label: object_name,
    asset: HARNESS_ASSET,
    capabilities: ["clickable"],
    aspect: 1.0,
    layout: { default_width: 5, label_width: 8, anchor_y: "bottom", anchor_y_offset: 0 },
    _width_scale: 1.0,
    _scale_source: "cm_model",
    _px_per_cm: null,
    _scale: 1.0,
    _centerX: x_offset,
    _baselineY: 40,
    _top: 40,
    _visualWidth: HARNESS_VISUAL_WIDTH,
    _height: visual_height,
    _footprint: HARNESS_VISUAL_WIDTH,
    _labelX: x_offset + 5,
    _labelY: 80,
    // Empty label list skips the label structural guards (7 and 8).
    _labelLines: [],
  };
}

function make_scene(): SceneA {
  return {
    scene_name: "degrade_harness_clean",
    workspace: "bench",
    scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
    zones: [
      {
        id: "center",
        bounds: { left: 5, right: 95, top: 8, bottom: 94 },
        align: "tab-stops",
        baseline: 84,
        label: "Center",
      },
    ],
    placements: [],
  };
}

function make_result(): PipelineResult {
  const final = [make_item(DEGRADE_OBJ_NAME, 20), make_item(HAPPY_OBJ_NAME, 50)];
  return {
    scene: make_scene(),
    final,
    interactionGeometry: derive_scene_interaction_geometry(final),
  } as PipelineResult;
}

//============================================
// Harness mount wiring (production mountScene)
//============================================

const store: SceneStore = create_scene_store();

// Pre-seed both objects so their state is non-empty (SceneItem skips the
// resolver on empty state). seed_from_scene initialises material_volume=5.0.
store.seed_from_scene([
  { target: DEGRADE_OBJ_NAME, object_name: DEGRADE_OBJ_NAME },
  { target: HAPPY_OBJ_NAME, object_name: HAPPY_OBJ_NAME },
]);

let dispose_fn: (() => void) | null = null;

function get_scene_root(): HTMLElement {
  const el = document.getElementById("scene-root");
  if (!(el instanceof HTMLElement)) {
    throw new Error("degrade harness: #scene-root not found");
  }
  return el;
}

// Mount via the production mountScene -> SceneView -> SceneItem path. SceneView
// stamps data-scene-root and reactively owns data-scene-degraded; we do NOT
// stamp data-scene-root manually here. The aspect guard uses the same viewport
// the host page sizes the root to (1200x675).
function do_mount(): void {
  if (dispose_fn) {
    dispose_fn();
    dispose_fn = null;
  }
  dispose_fn = mountScene(get_scene_root(), make_result(), {
    store,
    materialRegistry: null,
    seedMode: "none",
    viewport: HARNESS_VIEWPORT,
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
    __degrade_harness: {
      mount(): void;
      dispose(): void;
      set_state(target: string, partial: Record<string, string | number | boolean>): void;
      DEGRADE_OBJ_NAME: string;
      HAPPY_OBJ_NAME: string;
    };
  }
}

window.__degrade_harness = {
  mount: do_mount,
  dispose: do_dispose,
  set_state(target: string, partial: Record<string, string | number | boolean>): void {
    store.set_object_state(target, partial);
  },
  DEGRADE_OBJ_NAME,
  HAPPY_OBJ_NAME,
};
