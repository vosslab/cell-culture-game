// tests/playwright/e2e/protocol_walkthrough_yaml.mjs
//
// CLI wrapper for the one shared visible-UI walker engine. Browser launch and
// server ownership live here; all learner-path interactions and evidence live
// in helper_walker.mjs, the same engine used by the Playwright runner.

import { chromium } from "playwright";
import path from "node:path";

import { REPO_ROOT } from "../repo_root.mjs";
import { runProtocolWalk } from "./helper_walker.mjs";
import {
  resolveSelfServePort,
  startOwnedStaticServer,
  stopOwnedStaticServer,
} from "./walker_server.mjs";

const DIST_DIR = path.join(REPO_ROOT, "dist");
const DEFAULT_RESULTS_DIR = path.join(REPO_ROOT, "test-results", "walker");
const VALID_SCREENSHOT_MODES = new Set(["per-step", "per-interaction", "per-click"]);

function usage() {
  return `Usage: node tests/playwright/e2e/protocol_walkthrough_yaml.mjs [OPTIONS]

Schema-driven walker for the Solid protocol host. It uses real visible UI only;
the CLI and Playwright runner share the same proof engine.

Options:
  -p, --protocol NAME      Protocol id (page dist/<id>.html).
      --wrong-order        Probe a wrong visible target before correct actions.
      --screenshots MODE   per-step (default) | per-interaction | per-click.
      --server-url URL     Use an already-running static server.
      --port N             Self-serve port override (ignored with --server-url).
      --out-dir PATH       Results directory (default test-results/walker).
  -h, --help               Show this help and exit.`;
}

function parseArgs() {
  const result = {
    protocol: "sdspage_assemble_electrode_module",
    wrongOrder: false,
    screenshotMode: "per-step",
    port: null,
    serverUrl: null,
    outDir: DEFAULT_RESULTS_DIR,
  };
  const args = process.argv.slice(2);
  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    if (arg === "--help" || arg === "-h") {
      console.log(usage());
      process.exit(0);
    }
    const value = args[index + 1];
    if ((arg === "--protocol" || arg === "-p") && value !== undefined) {
      result.protocol = value;
      index++;
    } else if (arg === "--wrong-order") {
      result.wrongOrder = true;
    } else if (arg === "--screenshots" && value !== undefined) {
      if (!VALID_SCREENSHOT_MODES.has(value)) {
        throw new Error(`Invalid --screenshots '${value}'`);
      }
      result.screenshotMode = value;
      index++;
    } else if (arg === "--server-url" && value !== undefined) {
      result.serverUrl = value.replace(/\/+$/, "");
      index++;
    } else if (arg === "--port" && value !== undefined) {
      const port = Number.parseInt(value, 10);
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error(`Invalid --port '${value}'`);
      }
      result.port = port;
      index++;
    } else if (arg === "--out-dir" && value !== undefined) {
      result.outDir = path.resolve(REPO_ROOT, value);
      index++;
    }
  }
  return result;
}

async function waitForInjectedServer(url) {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // The caller owns startup; wait briefly for its normal bind.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Injected server never became ready: ${url}`);
}

async function main() {
  const args = parseArgs();
  let server = null;
  let baseUrl = args.serverUrl;
  const browser = await chromium.launch({ headless: true });
  try {
    if (baseUrl === null) {
      const port = resolveSelfServePort(args.port);
      server = await startOwnedStaticServer({
        port,
        directory: DIST_DIR,
        cwd: REPO_ROOT,
      });
      baseUrl = server.baseUrl;
    } else {
      await waitForInjectedServer(baseUrl);
    }
    const page = await browser.newPage();
    const outcome = await runProtocolWalk(page, {
      protocol: args.protocol,
      baseUrl,
      wrongOrder: args.wrongOrder,
      screenshotMode: args.screenshotMode,
      resultsDir: args.outDir,
    });
    console.log(outcome.diagnostics);
    if (!outcome.passed) process.exitCode = 1;
  } finally {
    await browser.close();
    if (server !== null) await stopOwnedStaticServer(server.child);
  }
}

main().catch((error) => {
  const message = error instanceof Error ? (error.stack ?? error.message) : String(error);
  console.error(`Walker fatal error: ${message}`);
  process.exitCode = 1;
});
