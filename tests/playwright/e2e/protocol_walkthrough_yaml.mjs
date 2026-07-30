// tests/playwright/e2e/protocol_walkthrough_yaml.mjs
//
// Schema-driven UI walker for the NEW Solid protocol host (src/protocol_host.tsx).
//
// It loads /<protocol>.html exactly as a student would, clears localStorage,
// reloads, reads the FROZEN read-only walker surfaces (window.PROTOCOL_STEPS +
// window.gameState), and drives the protocol entirely through real visible
// clicks. Dispatch is from the interaction's closed gesture set + resolved
// target only. There are NO step-name branches and NO per-protocol special
// cases.
//
// Hard real-click integrity (see WALKTHROUGH_GUIDE.md "How the walker decides
// what to click"):
//   1. Every advance comes from a real visible click via locator.click()
//      (Playwright actionability check: attached, visible, stable, hit-testable).
//   2. The target is verified to exist and be visible before clicking; missing
//      or hidden targets fail loudly. No force-click, no dispatchEvent.
//   3. window.PROTOCOL_STEPS / window.gameState are READ-ONLY. The walker never
//      writes them, never calls an internal runtime/protocol API to advance,
//      never forces a scene change, never mutates window.prompt/confirm.
//   4. clickTargetAndWaitProgress snapshots progress signals before the click and
//      waits for one to change as a consequence of the real handler.
//   5. Scene switches happen through the same visible-click gesture model (a
//      validated click whose response carries a SceneChange), not by writing
//      activeScene.
//
// Schema-driven dispatch:
//   The walker reads gameState.activeTarget + gameState.activeGesture (the
//   current interaction, projected read-only from the runtime snapshot -- the
//   same fields the runtime itself uses to resolve a click's gesture) and acts
//   on the closed gesture set: click, drag, adjust, select, type.
//   Only "click" is driveable through the new host's current visible UI (the
//   click resolver promotes a click on the active target to the active gesture).
//   Any gesture the new host has no visible affordance for FAILS with a clear
//   unsupported_gesture classification (M4-D records it); the walker NEVER
//   silently skips and NEVER adds a per-protocol branch.
//
// Usage:
//   node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <id> [options]
//
// Options:
//   -p, --protocol NAME    Protocol id (per-protocol page dist/<id>.html).
//   --wrong-order          Negative mode: inject a wrong visible click before
//                          each correct one and assert the runtime rejects it.
//   --screenshots MODE     per-step (default) | per-interaction | per-click.
//   --server-url URL       Injected-server mode: navigate against an already
//                          running static server at URL (e.g.
//                          http://127.0.0.1:8421) instead of self-serving. The
//                          walker spawns NO server of its own; the caller owns
//                          the server's lifetime. The sweep uses this so every
//                          concurrent walk shares ONE server.
//   --port N               Self-serve port override. Ignored when --server-url is
//                          given. Also honors the PORT env var.
//   --out-dir PATH         Results directory (default test-results/walker). Give
//                          each concurrent run a distinct out-dir so parallel
//                          walkers never touch the same report or screenshot.
//   -h, --help             Show help and exit.
//
// Server ownership is injectable (fix the design, not the symptom):
//   - SELF-SERVE (default, no --server-url): the walker asks the OS for a free
//     port, starts its own python3 -m http.server, confirms that child bound the
//     port, and tears down only that child at the end. --port and PORT remain
//     explicit overrides and fail before navigation if already occupied.
//   - INJECTED-SERVER (--server-url URL): the walker does NOT spawn a server; it
//     navigates against URL/<protocol>.html and uses URL's origin for the
//     request-failure filter and the readiness wait.
//
// Output: <out-dir>/ (screenshots + playthrough_report.json).

import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

import { REPO_ROOT } from "../repo_root.mjs";
import {
  resolveSelfServePort,
  startOwnedStaticServer,
  stopOwnedStaticServer,
} from "./walker_server.mjs";

import {
  waitForExports,
  readGameState,
  clickTargetAndWaitProgress,
  typeCommitAndWaitProgress,
  adjustCommitAndWaitProgress,
  pickWrongOrderItem,
  recordInjection,
  attachPageErrorCapture,
  captureVisibleTargetCheckpoint,
  waitForVisibleTimedWait,
  readSubpartOverlay,
  verifyMaterialAreaAfterInteraction,
} from "./walker_helpers.mjs";

const DIST_DIR = path.join(REPO_ROOT, "dist");
// Single-run default results dir. A no-flag invocation writes here with the
// historical report filename (playthrough_report.json); parallel callers pass a
// distinct --out-dir.
const DEFAULT_RESULTS_DIR = path.join(REPO_ROOT, "test-results", "walker");

// Whole-run budget: 10 minutes.
const RUN_BUDGET_MS = 600000;
// Per-step budget: 30 seconds.
const STEP_BUDGET_MS = 30000;
// Per-click budget: 3 seconds.
const CLICK_BUDGET_MS = 3000;

// Closed gesture set (PRIMARY_SPEC.md). "click", "select", "type", and "adjust"
// have visible affordances in the host:
//   - click  : a real visible click on the active scene object.
//   - select : choosing the next-step object among the present scene objects;
//              reuses the same visible-click affordance (the host promotes a
//              click on the active target to the active `select` gesture).
//   - type   : filling + committing the visible type-input affordance
//              ([data-type-input] / [data-type-commit]).
//   - adjust : setting + committing a value in the visible shared numeric
//              set-point editor ([data-adjust-input] / [data-adjust-commit]).
// "drag" stays classified-unsupported for the SWEEP because no content protocol
// authors a drag yet; the drag affordance + handle_drag_commit are wired (M12)
// and proven by the step-machine unit test + walker driver, and adding "drag"
// here is a one-line change once a real drag protocol lands.
const SUPPORTED_GESTURES = new Set(["click", "select", "type", "adjust"]);
const KNOWN_GESTURES = new Set(["click", "drag", "adjust", "select", "type"]);

//============================================
// Arg parsing
//============================================

function parseArgs() {
  const args = process.argv.slice(2);
  const result = {
    protocol: "sdspage_assemble_electrode_module",
    wrongOrder: false,
    screenshotMode: "per-step",
    // port stays null unless --port is passed; main() resolves the self-serve
    // port (explicit --port, then PORT env, then OS-assigned) only in self-serve mode.
    port: null,
    // serverUrl null means self-serve; a non-null URL selects injected-server mode.
    serverUrl: null,
    outDir: DEFAULT_RESULTS_DIR,
  };
  const VALID_SCREENSHOT_MODES = ["per-step", "per-interaction", "per-click"];

  if (args.includes("--help") || args.includes("-h")) {
    const usage = `Usage: node tests/playwright/e2e/protocol_walkthrough_yaml.mjs [OPTIONS]

Schema-driven walker for the new Solid protocol host. Loads /<protocol>.html,
reads the read-only window.PROTOCOL_STEPS / window.gameState surfaces, and drives
the protocol through real visible clicks (no per-protocol branches).

Options:
  -p, --protocol NAME      Protocol id (page dist/<id>.html). Default:
                           sdspage_assemble_electrode_module.
      --wrong-order        Negative mode: inject a wrong visible click before each
                           correct one and assert the runtime rejects it.
      --screenshots MODE   per-step (default) | per-interaction | per-click.
      --server-url URL     Injected-server mode: navigate against an already
                           running static server at URL; spawn no server. The
                           sweep uses this so all walks share ONE server.
      --port N             Self-serve port override (ignored with --server-url).
                           Default: PORT env var, else an OS-assigned free port.
      --out-dir PATH       Results directory (default test-results/walker).
  -h, --help               Show this help message and exit.`;
    console.log(usage);
    process.exit(0);
  }

  for (let i = 0; i < args.length; i++) {
    if ((args[i] === "--protocol" || args[i] === "-p") && i + 1 < args.length) {
      result.protocol = args[i + 1];
      i++;
    } else if (args[i] === "--wrong-order") {
      result.wrongOrder = true;
    } else if (args[i] === "--screenshots" && i + 1 < args.length) {
      const mode = args[i + 1];
      if (!VALID_SCREENSHOT_MODES.includes(mode)) {
        console.error(
          `Invalid --screenshots value '${mode}'. Valid: ${VALID_SCREENSHOT_MODES.join(", ")}`,
        );
        process.exit(1);
      }
      result.screenshotMode = mode;
      i++;
    } else if (args[i] === "--port" && i + 1 < args.length) {
      const parsedPort = Number.parseInt(args[i + 1], 10);
      if (!Number.isInteger(parsedPort) || parsedPort < 1 || parsedPort > 65535) {
        console.error(`Invalid --port value '${args[i + 1]}'. Expected an integer 1-65535.`);
        process.exit(1);
      }
      result.port = parsedPort;
      i++;
    } else if ((args[i] === "--server-url" || args[i] === "--base-url") && i + 1 < args.length) {
      // Injected-server mode. Strip any trailing slash so URL joins are clean.
      result.serverUrl = args[i + 1].replace(/\/+$/, "");
      i++;
    } else if (args[i] === "--out-dir" && i + 1 < args.length) {
      // Resolve against REPO_ROOT so a relative --out-dir lands in the repo,
      // matching how the default results dir is computed.
      result.outDir = path.resolve(REPO_ROOT, args[i + 1]);
      i++;
    }
  }
  return result;
}

//============================================
// Injected-server readiness
//============================================

async function waitForInjectedServer(url, maxMs = 5000) {
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(url);
      if (resp.ok) return;
    } catch {
      // keep retrying
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error("injected server never came up");
}

//============================================
// Report
//============================================

class WalkerReport {
  constructor() {
    this.timestamp = new Date().toISOString();
    this.protocol = "";
    this.wrongOrderMode = false;
    this.screenshotMode = "per-step";
    this.entries = [];
    this.checkpointManifest = [];
    this.summary = {
      stepsWalked: 0,
      stepsPassed: 0,
      stepsFailed: 0,
      totalClicks: 0,
      failureReason: null,
    };
  }

  addEntry(severity, message, metadata = {}) {
    this.entries.push({ timestamp: new Date().toISOString(), severity, message, ...metadata });
    console.log(`[${severity.toUpperCase()}] ${message}`);
  }

  info(msg, metadata) {
    this.addEntry("info", msg, metadata);
  }
  warn(msg, metadata) {
    this.addEntry("warn", msg, metadata);
  }
  error(msg, metadata) {
    this.addEntry("error", msg, metadata);
  }

  save(filePath) {
    const dirPath = path.dirname(filePath);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
    fs.writeFileSync(filePath, JSON.stringify(this, null, 2));
  }

  addCheckpoint(checkpoint) {
    this.checkpointManifest.push(checkpoint);
    this.info(`Checkpoint: ${checkpoint.step} / ${checkpoint.target}`, { checkpoint });
  }
}

function checkpointManifestProblems(report) {
  return report.checkpointManifest.flatMap((checkpoint, index) => {
    const bounds = checkpoint.visibleTargetBounds;
    const missing =
      !checkpoint.protocol ||
      !checkpoint.step ||
      !checkpoint.target ||
      !checkpoint.gesture ||
      !checkpoint.screenshot ||
      !fs.existsSync(checkpoint.screenshot) ||
      !checkpoint.actionCue ||
      checkpoint.actionCue.text === "" ||
      checkpoint.actionCue.target !== checkpoint.target ||
      checkpoint.actionCue.gesture !== checkpoint.gesture ||
      !checkpoint.affordance ||
      checkpoint.affordance.expectedKind !== checkpoint.affordance.renderedKind ||
      checkpoint.affordance.indicatorWidth <= 0 ||
      !bounds ||
      bounds.width <= 0 ||
      bounds.height <= 0 ||
      bounds.x < 0 ||
      bounds.y < 0 ||
      bounds.x + bounds.width > bounds.viewportWidth ||
      bounds.y + bounds.height > bounds.viewportHeight;
    return missing
      ? [`checkpoint ${index} is missing learner-cue, affordance, screenshot, or viewport proof`]
      : [];
  });
}

//============================================
// Step walker (schema-driven, one ordered sequence of interactions)
//============================================

// Walk the active step by repeatedly reading the read-only active interaction
// (target + gesture) and acting on it via a real visible click, until the step's
// id changes (it completed and the runtime advanced) or the protocol completes.
async function walkActiveStep(page, step, report, opts) {
  const { wrongOrderMode, screenshotMode, resultsDir } = opts;
  report.info(`Walking step: ${step.id}`, { stepId: step.id });

  const stepStart = Date.now();
  let interactionCounter = 0;

  // Loop over the step's interactions. The runtime advances interactionIndex on
  // each validated interaction and changes activeStepId when the step completes.
  while (true) {
    if (Date.now() - stepStart > STEP_BUDGET_MS) {
      throw new Error(`step_stalled: step ${step.id} exceeded ${STEP_BUDGET_MS}ms budget`);
    }

    const gs = await readGameState(page);

    // Step finished: the runtime resolved this step and moved on (or completed).
    if (gs.activeStepId !== step.id) {
      return;
    }

    const target = gs.activeTarget;
    const gesture = gs.activeGesture;
    if (target === null || gesture === null) {
      const timedWait = page.locator('[data-timed-wait="active"]:visible').first();
      if ((await timedWait.count()) > 0) {
        report.info(`Waiting for visible timed phase on step ${step.id}`);
        await waitForVisibleTimedWait(page, step.id, resultsDir, report, CLICK_BUDGET_MS);
        continue;
      }
      throw new Error(
        `no_active_interaction: step ${step.id} has no active target/gesture but is still active`,
      );
    }

    // Schema-driven dispatch from the closed gesture set. No step-name branch.
    if (!KNOWN_GESTURES.has(gesture)) {
      throw new Error(`unknown_gesture: '${gesture}' not in closed gesture set on step ${step.id}`);
    }
    if (!SUPPORTED_GESTURES.has(gesture)) {
      // Classify for M4-D: the new host has no visible affordance for this
      // gesture yet. Fail loudly; never silently skip, never branch per protocol.
      throw new Error(
        `unsupported_gesture: gesture '${gesture}' on target '${target}' (step ${step.id}) has ` +
          `no visible affordance in the new host yet; classify in M4-D`,
      );
    }

    // Wrong-order injection (negative mode): a real visible click on a
    // non-required item must be rejected by the runtime. Only meaningful for the
    // visible-click gestures (click/select); a `type` or `adjust` interaction is
    // driven through an overlay affordance, not an alternative scene object, so
    // injection is skipped for those.
    if (wrongOrderMode && gesture !== "type" && gesture !== "adjust") {
      const wrongItem = await pickWrongOrderItem(page, target);
      if (wrongItem) {
        report.info(`[wrong-order injection] clicking ${wrongItem} (not the active target)`);
        recordInjection(report, step.id, wrongItem);
        await clickTargetAndWaitProgress(page, wrongItem, report, {
          clickBudgetMs: CLICK_BUDGET_MS,
          progressKind: "reject",
        });
      } else {
        report.info(`[wrong-order injection] skipped: no alternative visible item`, {
          stepId: step.id,
        });
      }
    }

    // Capture after any negative probe and immediately before the authored
    // interaction, so the manifest documents the exact visible target the
    // student-path action will use.
    const checkpoint = await captureVisibleTargetCheckpoint(page, {
      protocol: report.protocol,
      step: step.id,
      target,
      gesture,
      interactionIndex: gs.interactionIndex,
      resultsDir,
    });
    report.addCheckpoint(checkpoint);

    // Structured material-area verification (generic, schema-driven). When the
    // active interaction's response writes a structured object's declared
    // material-tint subpart field, snapshot that object's per-subpart overlay
    // BEFORE the click so the after-verify can assert the targeted members
    // changed and nothing else did. activeMaterialEffect is a read-only
    // projection of authored config + generated object schema (walker_debug.ts);
    // null for every non-material-write interaction. No per-protocol branch.
    const materialEffect = gs.activeMaterialEffect;
    let materialBeforeOverlay = null;
    if (materialEffect !== null) {
      materialBeforeOverlay = await readSubpartOverlay(page, materialEffect.object_name);
    }

    // Correct interaction: drive the active interaction through its visible
    // affordance and wait for a progress signal produced by the real handler.
    if (gesture === "type") {
      // The expected typed value is read read-only from gameState.activeTypeValue
      // (projected from the authored validator `value`, the same read-only basis
      // the walker uses to know which object to click). A real fill + commit on
      // the visible [data-type-input] / [data-type-commit] affordance.
      const typedText = gs.activeTypeValue;
      if (typedText === null) {
        throw new Error(
          `type_value_missing: step ${step.id} type interaction on '${target}' has no ` +
            `activeTypeValue to type (validator declares no expected value)`,
        );
      }
      await typeCommitAndWaitProgress(page, typedText, report, {
        clickBudgetMs: CLICK_BUDGET_MS,
      });
    } else if (gesture === "adjust") {
      // The expected set-point is read read-only from gameState.activeAdjustValue
      // (projected from the authored target_with_value `value`, the same
      // read-only basis the walker uses for type and for which object to click).
      // A real fill + commit on the visible [data-adjust-input] /
      // [data-adjust-commit] shared numeric set-point editor.
      const setPoint = gs.activeAdjustValue;
      if (setPoint === null) {
        throw new Error(
          `adjust_value_missing: step ${step.id} adjust interaction on '${target}' has no ` +
            `activeAdjustValue to set (validator declares no expected value)`,
        );
      }
      await adjustCommitAndWaitProgress(page, setPoint, report, {
        clickBudgetMs: CLICK_BUDGET_MS,
      });
    } else {
      // click and select both drive a real visible click on the active scene
      // object. select promotes that click to the active gesture in the host.
      const perClickOpts =
        screenshotMode === "per-click" && resultsDir !== null
          ? {
              mode: "per-click",
              resultsDir,
              stepName: step.id,
              interactionIndex: gs.interactionIndex,
              clickIndex: 0,
              gesture,
              target,
            }
          : null;

      await clickTargetAndWaitProgress(page, target, report, {
        clickBudgetMs: CLICK_BUDGET_MS,
        progressKind: "advance",
        screenshotOpts: perClickOpts,
      });
    }

    // After the interaction settles, run the material-area assertion: every
    // targeted member subpart carries the authored material and its fill
    // changed, and every OTHER rendered subpart kept its prior material/fill.
    // A mismatch throws material_area_mismatch / material_area_no_overlay, which
    // fails this step (and reds the protocol in the sweep) -- exactly the silent
    // material no-op class the bespoke all-wells test caught, now generic.
    if (materialEffect !== null && materialBeforeOverlay !== null) {
      await verifyMaterialAreaAfterInteraction(page, materialEffect, materialBeforeOverlay, report);
    }

    // Per-interaction screenshot after the interaction's click completes.
    if (screenshotMode === "per-interaction" && resultsDir !== null) {
      const safeTarget = target.replace(/[^a-z0-9_]/gi, "_");
      const screenshotName = `interaction_${step.id}_i${interactionCounter}_${safeTarget}.png`;
      const screenshotPath = `${resultsDir}/${screenshotName}`;
      await page.screenshot({ path: screenshotPath });
      report.addEntry("info", `Screenshot: ${screenshotName}`, {
        screenshot: screenshotPath,
        step_name: step.id,
        interaction_index: interactionCounter,
        gesture,
        target,
      });
    }
    interactionCounter++;
  }
}

//============================================
// Main
//============================================

async function main() {
  const args = parseArgs();
  const RESULTS_DIR = args.outDir;

  // Injectable server ownership. In injected-server mode the caller (the sweep)
  // owns a single shared server and passes its URL; the walker spawns nothing.
  // In self-serve mode the walker owns a child server and proves its child bound
  // the requested port before it creates a browser or navigates anywhere.
  const injectedServer = args.serverUrl !== null;
  let selfServePort = null;
  let baseUrl = args.serverUrl;
  let server = null;

  if (!fs.existsSync(RESULTS_DIR)) {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  }

  const report = new WalkerReport();
  report.protocol = args.protocol;
  report.wrongOrderMode = args.wrongOrder;
  report.screenshotMode = args.screenshotMode;

  if (injectedServer) {
    try {
      await waitForInjectedServer(`${baseUrl}/`);
    } catch (error) {
      report.error(`Injected server startup failed: ${error.message}`);
      report.save(path.join(RESULTS_DIR, "playthrough_report.json"));
      process.exitCode = 1;
      return;
    }
  } else {
    selfServePort = resolveSelfServePort(args.port);
    try {
      const ownedServer = await startOwnedStaticServer({
        port: selfServePort,
        directory: DIST_DIR,
        cwd: REPO_ROOT,
      });
      server = ownedServer.child;
      selfServePort = ownedServer.port;
      baseUrl = ownedServer.baseUrl;
    } catch (error) {
      report.error(`Self-serve startup failed: ${error.message}`);
      report.save(path.join(RESULTS_DIR, "playthrough_report.json"));
      process.exitCode = 1;
      return;
    }
  }

  const serverDesc = injectedServer ? `injected ${baseUrl}` : `self-serve port ${selfServePort}`;
  console.log(
    `Starting walker: protocol=${args.protocol}, wrongOrder=${args.wrongOrder}, ` +
      `screenshots=${args.screenshotMode}, server=${serverDesc}, outDir=${RESULTS_DIR}`,
  );

  // The URL is now either caller-owned and reachable, or backed by the child
  // that this walker just confirmed bound its port.
  const originForFilter = new URL(baseUrl).origin;

  const runStart = Date.now();
  // The new host serves a per-protocol page at dist/<protocol>.html.
  const gameUrl = `${baseUrl}/${encodeURIComponent(args.protocol)}.html`;

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (error) {
    report.error(`Browser launch failed: ${error.message}`);
    report.save(path.join(RESULTS_DIR, "playthrough_report.json"));
    if (server !== null) {
      await stopOwnedStaticServer(server);
    }
    process.exitCode = 1;
    return;
  }

  let page;
  try {
    page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  } catch (error) {
    report.error(`Browser page setup failed: ${error.message}`);
    report.save(path.join(RESULTS_DIR, "playthrough_report.json"));
    await browser.close();
    if (server !== null) {
      await stopOwnedStaticServer(server);
    }
    process.exitCode = 1;
    return;
  }

  // Capture uncaught page exceptions (see docs/active_plans/audits/
  // adjust_did_not_advance_rootcause.md) so the wait-for-progress drivers can
  // report the real runtime error instead of a bare "did_not_advance" timeout.
  attachPageErrorCapture(page);

  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  const networkErrors = [];
  page.on("requestfailed", (req) => {
    try {
      const url = new URL(req.url());
      if (url.origin === originForFilter) {
        networkErrors.push({
          url: req.url(),
          method: req.method(),
          reason: req.failure().errorText,
        });
      }
    } catch {
      // ignore parse errors
    }
  });

  try {
    // Normal browser entry.
    report.info("Navigating to protocol page", { url: gameUrl });
    await page.goto(gameUrl, { waitUntil: "networkidle" });
    await waitForExports(page);
    report.info("Walker surfaces ready");

    // Fresh browser state: clear persistence and hard reload.
    report.info("Clearing localStorage and reloading");
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    await waitForExports(page);

    // Dismiss any visible welcome/start control by clicking it (a real user
    // would). The new host has no welcome modal; this is best-effort so the
    // walker stays compatible if one is added later.
    const startBtn = page
      .locator('button:has-text("Start"), button:has-text("Begin"), #welcome-start-btn')
      .first();
    if ((await startBtn.count()) > 0 && (await startBtn.isVisible())) {
      report.info("Dismissing visible start control");
      await startBtn.click();
    }

    const steps = await page.evaluate(() => window.PROTOCOL_STEPS);
    if (!steps || steps.length === 0) {
      throw new Error("No protocol steps found in window.PROTOCOL_STEPS");
    }
    report.info(`Protocol has ${steps.length} steps`, { stepCount: steps.length });

    await page.screenshot({ path: path.join(RESULTS_DIR, "initial_state.png") });

    // Walk steps in flow order (entry_step then next_step), driven by the
    // runtime: read the active step id, find its descriptor, walk it.
    const stepById = new Map(steps.map((s) => [s.id, s]));
    let guard = 0;
    while (guard < steps.length + 5) {
      guard++;
      if (Date.now() - runStart > RUN_BUDGET_MS) {
        report.error(`run_stalled: exceeded ${RUN_BUDGET_MS}ms whole-run budget`);
        report.summary.failureReason = "run_stalled";
        break;
      }

      const gs = await readGameState(page);
      if (gs.isComplete || gs.activeStepId === null) {
        break;
      }
      const step = stepById.get(gs.activeStepId);
      if (!step) {
        throw new Error(`active step '${gs.activeStepId}' not in PROTOCOL_STEPS`);
      }

      try {
        await walkActiveStep(page, step, report, {
          wrongOrderMode: args.wrongOrder,
          screenshotMode: args.screenshotMode,
          resultsDir: RESULTS_DIR,
        });
        report.summary.stepsWalked++;
        report.summary.stepsPassed++;
        report.info(`Step passed: ${step.id}`);
        const stepScreenshot = path.join(
          RESULTS_DIR,
          `step_${report.summary.stepsWalked}_${step.id}.png`,
        );
        await page.screenshot({ path: stepScreenshot });
      } catch (err) {
        report.summary.stepsWalked++;
        report.summary.stepsFailed++;
        report.summary.failureReason = err.message;
        report.error(`Step failed: ${step.id} - ${err.message}`, { stepId: step.id });
        await page.screenshot({ path: path.join(RESULTS_DIR, `fail_${step.id}.png`) });
        break;
      }
    }

    // End-state assertions.
    const ending = await readGameState(page);
    report.info("Final game state", {
      activeStepId: ending.activeStepId,
      completedStepsCount: ending.completedSteps.length,
      wrongOrderClicks: ending.wrongOrderClicks,
      isComplete: ending.isComplete,
    });

    if (report.summary.stepsFailed === 0) {
      if (!ending.isComplete) {
        report.error("Protocol did not reach isComplete=true (not all steps completed)");
      }
      if (ending.activeStepId !== null) {
        report.error("activeStepId is not null at end (not all steps completed)");
      }
      if (ending.completedSteps.length !== steps.length) {
        report.error(
          `completedSteps ${ending.completedSteps.length} !== step count ${steps.length}`,
        );
      }
      if (ending.wrongOrderClicks > 0 && !args.wrongOrder) {
        report.error(`wrongOrderClicks = ${ending.wrongOrderClicks} (should be 0)`);
      }
    }

    if (consoleErrors.length > 0) {
      report.error(`Console errors detected: ${consoleErrors.length}`, {
        errors: consoleErrors.slice(0, 5),
      });
    }
    if (networkErrors.length > 0) {
      report.error(`Network errors detected: ${networkErrors.length}`, { errors: networkErrors });
    }

    const checkpointProblems = checkpointManifestProblems(report);
    if (report.checkpointManifest.length === 0) {
      report.error("Checkpoint manifest is empty after a visible-UI walk");
    }
    for (const problem of checkpointProblems) {
      report.error(`Checkpoint manifest invalid: ${problem}`);
    }

    const errorCount = report.entries.filter((e) => e.severity === "error").length;
    if (errorCount > 0 || report.summary.stepsFailed > 0) {
      console.log(
        `\nWalker FAILED: ${errorCount} errors, ${report.summary.stepsFailed} steps failed`,
      );
      console.log(`Passed: ${report.summary.stepsPassed}/${steps.length} steps`);
      process.exitCode = 1;
    } else {
      console.log(`\nWalker PASSED: all ${report.summary.stepsWalked} steps completed`);
      process.exitCode = 0;
    }

    await page.screenshot({ path: path.join(RESULTS_DIR, "final_screen.png") });
  } catch (err) {
    report.error(`Walker crashed: ${err.message}`, { stack: err.stack });
    report.summary.failureReason = err.message;
    process.exitCode = 1;
    try {
      await page.screenshot({ path: path.join(RESULTS_DIR, "crash_screen.png") });
    } catch {
      // ignore screenshot failure
    }
  } finally {
    const reportPath = path.join(RESULTS_DIR, "playthrough_report.json");
    report.save(reportPath);
    console.log(`Report saved to ${reportPath}`);
    await browser.close();
    // Only tear down a server this walker owns; the injected server outlives it.
    if (server !== null) {
      await stopOwnedStaticServer(server);
    }
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
