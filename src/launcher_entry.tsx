// src/launcher_entry.tsx
//
// Launcher bundle entry. Mounts the launcher UI only. Imports the slim
// protocols index (metadata only: protocol_name, cluster, display_title,
// learning_goal_hook) so the launcher bundle stays lightweight and does
// not pull in scene runtime, renderer, SVG registry, or scene data.
//
// Builds to dist/launcher.js, loaded by dist/index.html (the launcher
// page). See docs/active_plans/active/web_ui/bundle_audit.md for the
// rationale behind the two-bundle split.

import { render } from "solid-js/web";
import { PROTOCOLS_INDEX_SLIM } from "../generated/protocols_index_slim.js";
import { Launcher } from "./launcher/protocol_launcher.js";

const root = document.getElementById("launcher-root");
if (!(root instanceof HTMLElement)) {
  throw new Error("launcher_entry: #launcher-root element not found");
}

render(() => <Launcher index={PROTOCOLS_INDEX_SLIM} />, root);
