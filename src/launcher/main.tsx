// Launcher entry point: mounts the Launcher component to #launcher-root.
// Reads PROTOCOLS_INDEX from the generated protocols file and renders
// the launcher interface via Solid.js.

import { render } from "solid-js/web";
import { PROTOCOLS_INDEX_SLIM } from "../../generated/protocols_index_slim.js";
import { Launcher } from "./protocol_launcher.js";

//============================================

const root = document.getElementById("launcher-root");
if (!root) {
  throw new Error("#launcher-root element not found in DOM");
}

render(() => <Launcher index={PROTOCOLS_INDEX_SLIM} />, root);
