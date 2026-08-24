// src/protocol_host_entry.tsx
//
// Protocol-host bundle entry. Imports the full scene runtime, renderer,
// SVG registry, protocol data, shell adapter, and ProtocolHud. Also
// covers the bench smoke page (dist/bench_basic.html) which only has
// #scene-root and no protocol name; sharing the bundle keeps the build
// simple and avoids a third esbuild output.
//
// Builds to dist/protocol_host.js, loaded by:
//   - dist/<protocol_name>.html (per-protocol host page)
//   - dist/bench_basic.html     (legacy bench render smoke target)
//
// Launcher is split out into src/launcher_entry.tsx -> dist/launcher.js.

//============================================
// Bench (legacy main.ts) mount
//============================================

async function mount_bench(root: HTMLElement): Promise<void> {
  const { SCENES } = await import("../generated/scenes.js");
  const { resolvePrecomputedResult } = await import("./scene_runtime/layout/precomputed_result.js");
  const { renderScene } = await import("./scene_runtime/renderer/index.js");

  const scene = SCENES.hood_basic;
  if (!scene) {
    throw new Error("Scene hood_basic not found in SCENES index");
  }
  // Production layout source: consume the build-time precomputed layout for
  // hood_basic instead of running the runtime engine. No runPipeline call path
  // ships in this bundle.
  const result = resolvePrecomputedResult("hood_basic", scene);
  renderScene(root, result);
}

//============================================
// Protocol host mount
//============================================

async function mount_protocol_host(): Promise<void> {
  // The host module wires the runtime and shell bindings. Its
  // top-level call site mounts on import, so a dynamic import is enough.
  await import("./protocol_host.js");
}

//============================================
// Route
//============================================

function route(): Promise<void> {
  const scene_root = document.getElementById("scene-root");
  if (!(scene_root instanceof HTMLElement)) {
    throw new Error("protocol_host_entry: #scene-root element not found");
  }
  const has_protocol_name =
    typeof window.__PROTOCOL_NAME__ === "string" && window.__PROTOCOL_NAME__ !== "";
  const has_shell_root = document.getElementById("shell-root") instanceof HTMLElement;
  if (has_protocol_name && has_shell_root) {
    return mount_protocol_host();
  }
  return mount_bench(scene_root);
}

route().catch((err: unknown) => {
  // eslint-disable-next-line no-console
  console.error("protocol_host_entry failed:", err);
  throw err;
});
