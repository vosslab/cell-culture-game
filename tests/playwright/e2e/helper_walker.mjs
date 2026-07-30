// tests/playwright/e2e/helper_walker.mjs
//
// Shared visible-UI walk engine for the schema-driven protocol walker that
// drives the Solid protocol host (src/protocol_host.tsx).
//
// This is the engine extracted out of the legacy CLI walker
// (protocol_walkthrough_yaml.mjs main()) so the runner-model sweep spec
// (protocol_walkthrough.spec.ts) drives the EXACT SAME step walk without
// spawning a child process or its own server. The engine operates on a Page the
// caller provides (a Playwright test fixture page under the runner model), so it
// carries NO chromium.launch, NO python http.server, NO process.exit. Server
// ownership belongs entirely to the playwright.config.ts webServer block now.
//
// Hard real-click integrity is unchanged (see WALKTHROUGH_GUIDE.md and
// walker_helpers.mjs):
//   1. Every advance comes from a real visible click / fill+commit through the
//      actionability-checked helpers in walker_helpers.mjs. No force-click, no
//      dispatchEvent, no hidden-node clicks.
//   2. window.PROTOCOL_STEPS / window.gameState are READ-ONLY. The engine never
//      writes them, never calls an internal runtime/protocol API to advance,
//      never forces a scene change, never mutates window.prompt/confirm.
//   3. Dispatch is from the interaction's closed gesture set + resolved target
//      only. There are NO step-name branches and NO per-protocol special cases.
//   4. The structured material-area oracle (verifyMaterialAreaAfterInteraction)
//      runs around every material-writing interaction, unchanged.
//
// The engine RETURNS a structured WalkOutcome; it never exits the process. The
// runner spec asserts honestly on that outcome with expect(): a protocol that
// does not complete through visible UI fails its test.

import path from "node:path";
import fs from "node:fs";

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

// Whole-run budget: 10 minutes.
const RUN_BUDGET_MS = 600000;
// Per-step budget: 30 seconds.
const STEP_BUDGET_MS = 30000;
// Per-click budget: 3 seconds.
const CLICK_BUDGET_MS = 3000;

// Closed gesture set (PRIMARY_SPEC.md). "click", "select", "type", and "adjust"
// have visible affordances in the host; "drag" stays classified-unsupported for
// the SWEEP because no content protocol authors a drag yet (the affordance is
// wired and proven by the unit test + driver, so adding it here is a one-line
// change once a real drag protocol lands).
const SUPPORTED_GESTURES = new Set(["click", "select", "type", "adjust"]);
const KNOWN_GESTURES = new Set(["click", "drag", "adjust", "select", "type"]);

//============================================
// Report (accumulates evidence; assertion is the caller's job)
//============================================

// A plain evidence accumulator the walker_helpers drivers write into
// (report.info / report.summary.totalClicks++). The runner spec reads the
// resulting summary and asserts on it; the engine itself never throws to signal
// protocol failure, it records it.
export class WalkerReport {
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
// (target + gesture) and acting on it via a real visible interaction, until the
// step's id changes (it completed and the runtime advanced) or the protocol
// completes. Throws on any step-level failure; the caller records it as a failed
// step.
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
      // The host has no visible affordance for this gesture yet. Fail loudly;
      // never silently skip, never branch per protocol.
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
    // projection of authored config + generated object schema; null for every
    // non-material-write interaction. No per-protocol branch.
    const materialEffect = gs.activeMaterialEffect;
    let materialBeforeOverlay = null;
    if (materialEffect !== null) {
      materialBeforeOverlay = await readSubpartOverlay(page, materialEffect.object_name);
    }

    // Correct interaction: drive the active interaction through its visible
    // affordance and wait for a progress signal produced by the real handler.
    if (gesture === "type") {
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
    // fails this step (and reds the protocol in the sweep).
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
// Whole-protocol walk (operates on a caller-provided page)
//============================================

// Drive one protocol end to end through the visible UI on the provided page.
// options: { protocol, baseUrl, wrongOrder, screenshotMode, resultsDir }.
// Returns a WalkOutcome; never throws for a protocol failure (records it), only
// rethrows a truly unexpected engine crash after saving the report.
export async function runProtocolWalk(page, options) {
  const {
    protocol,
    baseUrl,
    wrongOrder = false,
    screenshotMode = "per-step",
    resultsDir,
  } = options;

  if (!fs.existsSync(resultsDir)) {
    fs.mkdirSync(resultsDir, { recursive: true });
  }

  const report = new WalkerReport();
  report.protocol = protocol;
  report.wrongOrderMode = wrongOrder;
  report.screenshotMode = screenshotMode;

  const runStart = Date.now();
  // The host serves a per-protocol page at dist/<protocol>.html; the config
  // webServer serves dist/ at baseUrl.
  const gameUrl = `${baseUrl}/${encodeURIComponent(protocol)}.html`;
  const originForFilter = new URL(baseUrl).origin;

  // Capture uncaught page exceptions so the wait-for-progress drivers can report
  // the real runtime error instead of a bare "did_not_advance" timeout.
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

  let outcome;
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
    // would). Best-effort so the walker stays compatible if one is added later.
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

    await page.screenshot({ path: path.join(resultsDir, "initial_state.png") });

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
          wrongOrderMode: wrongOrder,
          screenshotMode,
          resultsDir,
        });
        report.summary.stepsWalked++;
        report.summary.stepsPassed++;
        report.info(`Step passed: ${step.id}`);
        const stepScreenshot = path.join(
          resultsDir,
          `step_${report.summary.stepsWalked}_${step.id}.png`,
        );
        await page.screenshot({ path: stepScreenshot });
      } catch (err) {
        report.summary.stepsWalked++;
        report.summary.stepsFailed++;
        report.summary.failureReason = err.message;
        report.error(`Step failed: ${step.id} - ${err.message}`, { stepId: step.id });
        await page.screenshot({ path: path.join(resultsDir, `fail_${step.id}.png`) });
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
      if (ending.wrongOrderClicks > 0 && !wrongOrder) {
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

    await page.screenshot({ path: path.join(resultsDir, "final_screen.png") });

    const errorCount = report.entries.filter((e) => e.severity === "error").length;
    const passed = errorCount === 0 && report.summary.stepsFailed === 0;
    outcome = {
      passed,
      protocol,
      stepCount: steps.length,
      stepsPassed: report.summary.stepsPassed,
      stepsFailed: report.summary.stepsFailed,
      isComplete: ending.isComplete,
      failureReason: report.summary.failureReason,
      errorCount,
      checkpointManifest: report.checkpointManifest,
      checkpointManifestValid:
        report.checkpointManifest.length > 0 && checkpointProblems.length === 0,
    };
  } catch (err) {
    report.error(`Walker crashed: ${err.message}`, { stack: err.stack });
    report.summary.failureReason = err.message;
    try {
      await page.screenshot({ path: path.join(resultsDir, "crash_screen.png") });
    } catch {
      // ignore screenshot failure
    }
    const errorCount = report.entries.filter((e) => e.severity === "error").length;
    outcome = {
      passed: false,
      protocol,
      stepCount: 0,
      stepsPassed: report.summary.stepsPassed,
      stepsFailed: report.summary.stepsFailed,
      isComplete: false,
      failureReason: report.summary.failureReason,
      errorCount,
      checkpointManifest: report.checkpointManifest,
      checkpointManifestValid: false,
    };
  }

  const reportPath = path.join(resultsDir, "playthrough_report.json");
  report.save(reportPath);
  console.log(`Report saved to ${reportPath}`);

  // Compact human-readable diagnostics for the spec's expect() message.
  const errorLines = report.entries
    .filter((e) => e.severity === "error")
    .map((e) => e.message)
    .slice(0, 6);
  outcome.diagnostics =
    `steps ${outcome.stepsPassed}/${outcome.stepCount} passed, ${outcome.stepsFailed} failed, ` +
    `isComplete=${outcome.isComplete}, report=${reportPath}` +
    (errorLines.length > 0 ? `\n  - ${errorLines.join("\n  - ")}` : "");
  return outcome;
}
