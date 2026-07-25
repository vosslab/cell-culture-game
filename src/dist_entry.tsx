// src/dist_entry.tsx
//
// Single-bundle dist entry. One esbuild output (dist/main.js) is
// shared by every page in dist/:
//
//   - dist/index.html        -> #launcher-root present -> launcher mount
//   - dist/<protocol>.html   -> #scene-root + #shell-root + window.__PROTOCOL_NAME__
//                                -> protocol_host mount
//   - dist/scene_viewer.html -> #scene-root only, no protocol name, ?scene=<name>
//                                -> scene viewer mount (defaults to hood_basic when
//                                   ?scene= is absent; also serves as bench smoke target)
//
// Note: dist/bench_basic.html loads protocol_host.js, not main.js, so this
// entry never routes bench_basic.html traffic. The scene viewer path above is
// the correct route for standalone scene display via this bundle.
//
// Routing is by DOM presence, not by URL. Each page declares its intent
// by which root elements it includes. The entry runs the matching module
// and ignores the rest. No untyped globals are added.
//
// References:
//   - docs/PRIMARY_CONTRACT.md item 1 (TypeScript runtime is shared)

import { ZONE_PADDING } from "./scene_runtime/layout/constants.js";
import type { PipelineResult } from "./scene_runtime/layout/types.js";

// Pipeline-truth geometry the render tool reads from the page. Shape mirrors the
// dump consumed by scene_calc/dump.py (pre-pixel-conversion). Set by the scene
// viewer mount; absent on the launcher and protocol-host routes.
interface SceneGeometryZone {
  name: string;
  bounds: { left: number; right: number; top: number; bottom: number };
}
interface SceneGeometryPlacement {
  placement_name: string;
  kind: string;
  zone: string;
  asset: string;
  aspect: number;
  scale_source: string;
}
interface SceneGeometry {
  scene_name: string;
  zone_padding: number;
  zones: SceneGeometryZone[];
  placements: SceneGeometryPlacement[];
}
declare global {
  interface Window {
    __SCENE_GEOMETRY__?: SceneGeometry;
  }
}

//============================================
// Scene viewer mount (replaces legacy bench mount)
//============================================

// Renders any named scene without a protocol. The scene name is read from
// the ?scene= URL search param, defaulting to hood_basic when absent.
// On success or recoverable error, sets data-viewer-ready="true" on root
// so automated tools can tell the viewer finished from a page load failure.
async function mount_scene_viewer(root: HTMLElement, scene_name: string): Promise<void> {
  const { SCENES } = await import("../generated/scenes.js");
  const { resolvePrecomputedResult } = await import("./scene_runtime/layout/precomputed_result.js");
  const { renderScene } = await import("./scene_runtime/renderer/index.js");

  // Guard: unknown scene -> visible error banner, no throw.
  const scene = SCENES[scene_name];
  if (!scene) {
    const banner = document.createElement("div");
    banner.style.cssText =
      "padding:1rem;background:#fee;border:2px solid #c00;color:#900;font-family:monospace;";
    banner.textContent = `Scene viewer error: unknown scene "${scene_name}". Check the ?scene= parameter.`;
    root.appendChild(banner);
    // Mark ready so tools know the viewer ran (even on error path).
    root.setAttribute("data-viewer-ready", "true");
    return;
  }

  // Production layout source: consume the build-time precomputed layout for this
  // scene instead of running the runtime engine. The precomputed ComputedItem[]
  // carries _scale_source and aspect, so attachSceneGeometry still has the
  // pipeline-truth fields it needs. No runPipeline call path ships here.
  const result = resolvePrecomputedResult(scene_name, scene);
  renderScene(root, result);
  // Stash pipeline-truth geometry the render tool needs but cannot read from the
  // DOM: per-placement scale_source + intended SVG aspect, and the resolved zone
  // bounds (scene-percent). scene_to_png.mjs reads this together with rendered
  // DOM rects to assemble the dump-shaped geometry. The browser pipeline remains
  // the single geometry producer; this is its output, not a second model.
  attachSceneGeometry(result);
  // Mark ready after a successful render.
  root.setAttribute("data-viewer-ready", "true");
}

// Builds a serializable geometry summary from the pipeline result and attaches
// it to window so the render tool can read pipeline-truth values (scale_source,
// intended aspect, resolved zone bounds) that are not present as DOM attributes.
function attachSceneGeometry(result: PipelineResult): void {
  const zones = result.scene.zones.map((zone) => {
    const band = result.zoneBands.get(zone.id);
    if (band === undefined) {
      throw new Error(`scene geometry missing final reflow band for zone "${zone.id}"`);
    }
    return {
      name: zone.id,
      // Final reflow bands are scene-percent (0..100 per axis). Pixel conversion
      // happens in the render tool against #scene-root, matching item placement.
      bounds: {
        left: zone.bounds.left,
        right: zone.bounds.right,
        top: band.top,
        bottom: band.bottom,
      },
    };
  });
  const placements = result.final.map((item) => ({
    placement_name: item.placement_name,
    kind: item.kind,
    zone: item.zone,
    asset: item.asset,
    // Intended asset aspect (SVG viewBox w/h). Used for aspect_delta_pct.
    aspect: item.aspect,
    // Pipeline scale-source enum (cm_model | fallback_* | skipped_error).
    scale_source: item._scale_source,
  }));
  window.__SCENE_GEOMETRY__ = {
    scene_name: result.scene.scene_name,
    zone_padding: ZONE_PADDING,
    zones,
    placements,
  };
}

//============================================
// Launcher mount
//============================================

async function mount_launcher(root: HTMLElement): Promise<void> {
  const { render } = await import("solid-js/web");
  const { PROTOCOLS_INDEX_SLIM } = await import("../generated/protocols_index_slim.js");
  const { Launcher } = await import("./launcher/protocol_launcher.js");
  render(() => <Launcher index={PROTOCOLS_INDEX_SLIM} />, root);
}

//============================================
// Protocol host mount
//============================================

async function mount_protocol_host(): Promise<void> {
  // The host module wires every M2 runtime + M3 shell binding. Its
  // top-level call site mounts on import, so a dynamic import is enough.
  await import("./protocol_host.js");
}

//============================================
// Route
//============================================

function route(): Promise<void> {
  // Order matters. Protocol host is the most specific: it requires a
  // protocol name set on window AND a scene-root. If only scene-root is
  // present, check for ?scene= to use the scene viewer, else fall back
  // to bench (hood_basic). Launcher uses its own dedicated root.
  const launcher_root = document.getElementById("launcher-root");
  if (launcher_root instanceof HTMLElement) {
    return mount_launcher(launcher_root);
  }
  const scene_root = document.getElementById("scene-root");
  if (scene_root instanceof HTMLElement) {
    const has_protocol_name =
      typeof window.__PROTOCOL_NAME__ === "string" && window.__PROTOCOL_NAME__ !== "";
    const has_shell_root = document.getElementById("shell-root") instanceof HTMLElement;
    if (has_protocol_name && has_shell_root) {
      return mount_protocol_host();
    }
    // Scene viewer: activated when no protocol name is set. Read ?scene=
    // from the URL; fall back to hood_basic when absent (bench smoke target).
    const url_params = new URLSearchParams(window.location.search);
    const scene_param = url_params.get("scene");
    const scene_name = scene_param !== null && scene_param !== "" ? scene_param : "hood_basic";
    return mount_scene_viewer(scene_root, scene_name);
  }
  throw new Error("dist_entry: no recognized root element (#launcher-root or #scene-root)");
}

route().catch((err: unknown) => {
  // Surface routing or mount failures loudly for unexpected errors
  // (e.g. dynamic import failures). Known recoverable errors (unknown scene)
  // are handled inside mount_scene_viewer and never reach here.
  // eslint-disable-next-line no-console
  console.error("dist_entry failed:", err);
  // Do NOT rethrow: rethrowing leaves a blank page with no user-visible
  // feedback. The console.error above is the only useful signal.
});
