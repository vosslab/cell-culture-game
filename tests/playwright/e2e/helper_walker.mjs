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
  adjustCommitAndWaitProgress,
  pickWrongOrderItem,
  recordInjection,
  attachPageErrorCapture,
  captureVisibleTargetCheckpoint,
  waitForVisibleTimedWait,
  readSubpartOverlay,
  verifyMaterialAreaEffectsAfterInteraction,
  pickWrongSiblingItem,
  readVisibleAdjustValue,
  openVisibleActionHint,
} from "./walker_helpers.mjs";

// Whole-run budget: 10 minutes.
const RUN_BUDGET_MS = 600000;
// Per-step budget: 30 seconds.
const STEP_BUDGET_MS = 30000;
// Per-click budget: 3 seconds.
const CLICK_BUDGET_MS = 3000;
// Timed waits are intentionally compressed for browser learning sessions. This
// hard ceiling catches an accidentally authored real-world wait without making
// the evidence assertion depend on an exact animation duration.
const TIMED_WAIT_BUDGET_MS = 1500;

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
      wrongSiblingProbes: 0,
      wrongOrderInjections: 0,
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
      checkpoint.actionCue.progress === "" ||
      checkpoint.actionCue.message === "" ||
      checkpoint.actionCue.goal === "" ||
      checkpoint.actionCue.hint === "" ||
      !checkpoint.actionCue.hintOpen ||
      (checkpoint.gesture !== "select" && checkpoint.actionCue.target !== checkpoint.target) ||
      (checkpoint.gesture === "select" &&
        (checkpoint.actionCue.target !== null ||
          checkpoint.actionCue.label !== null ||
          checkpoint.actionCue.targetText !== "")) ||
      checkpoint.actionCue.gesture !== checkpoint.gesture ||
      !checkpoint.affordance ||
      !checkpoint.effectiveClickTarget ||
      checkpoint.effectiveClickTarget.authoredDomTarget !== checkpoint.target ||
      checkpoint.effectiveClickTarget.hitDomTarget !== checkpoint.target ||
      checkpoint.effectiveClickTarget.coreWidth < (bounds?.isInteractionEnvelope ? 44 : 24) ||
      checkpoint.effectiveClickTarget.coreHeight < (bounds?.isInteractionEnvelope ? 44 : 24) ||
      !checkpoint.declaredStateBefore ||
      !checkpoint.declaredStateAfter ||
      !Array.isArray(checkpoint.declaredStateBefore.activeStateWrites) ||
      (checkpoint.declaredStateBefore.activeStateWrites.length > 0 &&
        (!checkpoint.stateAfterScreenshot || !fs.existsSync(checkpoint.stateAfterScreenshot))) ||
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

function expectedGuidanceFor(authoredProtocol, stepId, interactionIndex) {
  if (authoredProtocol?.protocol_type !== "mini_protocol") return null;
  const step = authoredProtocol.steps.find((candidate) => candidate.step_name === stepId);
  if (step === undefined) {
    throw new Error(
      `authored_guidance_step_missing: '${stepId}' is not in generated protocol data`,
    );
  }
  const interaction = step.sequence[interactionIndex];
  if (interaction === undefined) {
    throw new Error(
      `authored_guidance_interaction_missing: '${stepId}' interaction ${interactionIndex} is not generated`,
    );
  }
  return {
    instruction: interaction.instruction,
    hint: interaction.hint,
    prompt: step.prompt,
  };
}

function declaredStateEvidence(gameState) {
  return {
    revision: gameState.stateRevision,
    snapshot: gameState.declaredState,
    lastDelta: gameState.lastStateDelta,
    stateDeltaLog: gameState.stateDeltaLog,
    activeStateWrites: gameState.activeStateWrites,
  };
}

function exactStateFields(expected, actual) {
  const expectedKeys = Object.keys(expected).sort();
  const actualKeys = Object.keys(actual).sort();
  if (expectedKeys.length !== actualKeys.length) return false;
  return expectedKeys.every(
    (field, index) => field === actualKeys[index] && actual[field] === expected[field],
  );
}

export function validateDeclaredStateMutation(before, after, target, step, interactionIndex) {
  const expectedWrites = before.activeStateWrites;
  if (
    !Array.isArray(expectedWrites) ||
    !Array.isArray(before.stateDeltaLog) ||
    !Array.isArray(after.stateDeltaLog)
  ) {
    throw new Error(
      `declared_state_contract_missing: ${step} interaction ${interactionIndex} on '${target}' ` +
        "does not expose activeStateWrites and ordered stateDeltaLog on the read-only walker surface",
    );
  }
  const observedDeltas = after.stateDeltaLog.slice(before.stateDeltaLog.length);
  if (expectedWrites.length === 0) {
    // Scene reconciliation can legitimately advance the diagnostic revision
    // while a SceneChange mounts a new projection. It is not a declared write.
    // A changed concrete delta, however, would falsely invent one.
    if (observedDeltas.length !== 0) {
      throw new Error(
        `declared_state_unexpected_delta: ${step} interaction ${interactionIndex} recorded ` +
          `${observedDeltas.length} state delta(s) without ObjectStateChange`,
      );
    }
    return;
  }
  if (after.stateRevision <= before.stateRevision) {
    throw new Error(
      `declared_state_revision_missing: ${step} interaction ${interactionIndex} authored ObjectStateChange ` +
        `but revision stayed ${before.stateRevision}`,
    );
  }
  if (observedDeltas.length !== expectedWrites.length) {
    throw new Error(
      `declared_state_delta_count_mismatch: ${step} interaction ${interactionIndex} expected ` +
        `${expectedWrites.length} ordered write(s), got ${observedDeltas.length}`,
    );
  }
  for (let writeIndex = 0; writeIndex < expectedWrites.length; writeIndex++) {
    const expectedWrite = expectedWrites[writeIndex];
    const observedDelta = observedDeltas[writeIndex];
    if (expectedWrite === undefined || observedDelta === undefined) {
      throw new Error(`declared_state_delta_missing: ${step} interaction ${interactionIndex}`);
    }
    if (observedDelta.target !== expectedWrite.target) {
      throw new Error(
        `declared_state_delta_order_mismatch: ${step} interaction ${interactionIndex} write ${writeIndex} ` +
          `expected '${expectedWrite.target}', got '${observedDelta.target}'`,
      );
    }
    if (!exactStateFields(expectedWrite.state, observedDelta.after)) {
      throw new Error(
        `declared_state_delta_field_mismatch: ${step} interaction ${interactionIndex} write ${writeIndex} ` +
          `does not exactly match '${expectedWrite.target}' fields`,
      );
    }
  }
  const finalWrite = expectedWrites[expectedWrites.length - 1];
  const finalDelta = observedDeltas[observedDeltas.length - 1];
  if (
    finalWrite === undefined ||
    finalDelta === undefined ||
    after.lastStateDelta === null ||
    after.lastStateDelta.target !== finalDelta.target ||
    !exactStateFields(finalDelta.after, after.lastStateDelta.after)
  ) {
    throw new Error(
      `declared_state_final_delta_mismatch: ${step} interaction ${interactionIndex} final log entry ` +
        "does not agree with lastStateDelta",
    );
  }
  // declaredState is a detached active-scene map, not a writable archive dump.
  // It proves every concrete target that remains learner-visible after the
  // action; the ordered writes and lastStateDelta cover a target that departed
  // during a scene transition.
  if (before.declaredState !== null && after.declaredState !== null) {
    const expectedFinalState = new Map();
    for (const write of expectedWrites) {
      const prior = expectedFinalState.get(write.target) ?? {};
      expectedFinalState.set(write.target, { ...prior, ...write.state });
    }
    for (const [writeTarget, expectedState] of expectedFinalState) {
      const afterTarget = after.declaredState[writeTarget];
      if (afterTarget === undefined) continue;
      for (const [field, value] of Object.entries(expectedState)) {
        if (afterTarget[field] !== value) {
          throw new Error(
            `declared_state_snapshot_field_mismatch: ${step} interaction ${interactionIndex} expected ` +
              `${writeTarget}.${field}=${String(value)}, got ${String(afterTarget[field])}`,
          );
        }
      }
    }
  }
}

// A TimedWait can deliberately defer ObjectStateChange operations until its
// visible phase completes. The pre-click projected writes remain the source of
// truth; this predicate only decides whether validation must wait for that
// learner-visible phase instead of observing its intentionally unchanged start.
export function shouldAwaitTimedStateWrite(gameState, timedWaitVisible) {
  return (
    Array.isArray(gameState.activeStateWrites) &&
    gameState.activeStateWrites.length > 0 &&
    timedWaitVisible
  );
}

export function expectedRejectedClickCount(summary) {
  return summary.wrongSiblingProbes + summary.wrongOrderInjections;
}

export function wrongOrderAccountingProblem(summary, observedWrongOrderClicks) {
  const expected = expectedRejectedClickCount(summary);
  if (observedWrongOrderClicks !== expected) {
    return (
      `wrong_order_accounting_mismatch: observed ${observedWrongOrderClicks} rejected click(s), ` +
      `expected ${expected} (${summary.wrongSiblingProbes} wrong-sibling probe(s) + ` +
      `${summary.wrongOrderInjections} --wrong-order injection(s))`
    );
  }
  return null;
}

// Reveal and prove one declared member at a time. A group can legitimately be
// larger than the scene scrollport, so a learner never needs its full union on
// screen. Each exact subpart keeps its existing 24px hit-core contract.
async function proveDeclaredSubpartGroup(page, target, gesture, report) {
  const groupMembers = page.locator(
    `#scene-root [data-subpart-group-target="${target}"][data-item-id="${target}"]`,
  );
  const groupMemberCount = await groupMembers.count();
  if (groupMemberCount === 0) return 0;
  if (groupMemberCount < 2) {
    throw new Error(
      `subpart_group_incomplete: declared group '${target}' exposes only ` +
        `${groupMemberCount} visible member surface`,
    );
  }

  const expectedAffordance = gesture === "select" ? "candidate" : "active";
  const windowAnchor = await page.evaluate(() => ({ x: window.scrollX, y: window.scrollY }));
  const memberNames = new Set();
  const groupProblems = [];

  for (let memberIndex = 0; memberIndex < groupMemberCount; memberIndex++) {
    const memberLocator = groupMembers.nth(memberIndex);
    await memberLocator.evaluate((element) => {
      const panel = element.closest(".scene-panel");
      if (!(panel instanceof HTMLElement)) return;
      const memberRect = element.getBoundingClientRect();
      const panelRect = panel.getBoundingClientRect();
      const horizontal =
        panel.scrollLeft +
        memberRect.left -
        panelRect.left -
        (panel.clientWidth - memberRect.width) / 2;
      const vertical =
        panel.scrollTop +
        memberRect.top -
        panelRect.top -
        (panel.clientHeight - memberRect.height) / 2;
      panel.scrollLeft = Math.max(0, Math.min(horizontal, panel.scrollWidth - panel.clientWidth));
      panel.scrollTop = Math.max(0, Math.min(vertical, panel.scrollHeight - panel.clientHeight));
    });

    // Wait for the scene-owned scrollport, never browser scroll, to reveal the
    // member with a learner-sized core and the exact delegated group identity.
    await page.waitForFunction(
      ({ target: groupTarget, index }) => {
        const members = Array.from(
          document.querySelectorAll("#scene-root [data-subpart-group-target][data-item-id]"),
        ).filter(
          (element) =>
            element.getAttribute("data-subpart-group-target") === groupTarget &&
            element.getAttribute("data-item-id") === groupTarget,
        );
        const element = members[index];
        const panel = element?.closest(".scene-panel");
        if (!(element instanceof Element) || !(panel instanceof HTMLElement)) return false;
        const rect = element.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();
        const tolerance = 0.5;
        const insidePanel =
          rect.left >= panelRect.left - tolerance &&
          rect.top >= panelRect.top - tolerance &&
          rect.right <= panelRect.right + tolerance &&
          rect.bottom <= panelRect.bottom + tolerance;
        const insideBrowser =
          rect.left >= -tolerance &&
          rect.top >= -tolerance &&
          rect.right <= window.innerWidth + tolerance &&
          rect.bottom <= window.innerHeight + tolerance;
        const hit = document
          .elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
          ?.closest?.("[data-item-id]");
        return (
          rect.width >= 24 - tolerance &&
          rect.height >= 24 - tolerance &&
          insidePanel &&
          insideBrowser &&
          hit?.getAttribute("data-item-id") === groupTarget
        );
      },
      { target, index: memberIndex },
      { timeout: CLICK_BUDGET_MS },
    );

    const member = await memberLocator.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      const indicator = element.querySelector(".subpart-focus-indicator");
      const indicatorStyle = indicator === null ? null : window.getComputedStyle(indicator);
      const hit = document
        .elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
        ?.closest?.("[data-item-id]");
      return {
        member: element.getAttribute("data-subpart-name"),
        target: element.getAttribute("data-item-id"),
        affordance: element.getAttribute("data-subpart-affordance"),
        width: rect.width,
        height: rect.height,
        centerTarget: hit?.getAttribute("data-item-id") ?? null,
        strokeWidth: Number.parseFloat(indicatorStyle?.strokeWidth ?? "0"),
        stroke: indicatorStyle?.stroke ?? "none",
      };
    });
    if (member.member === null || memberNames.has(member.member)) {
      groupProblems.push(`duplicate or unnamed member '${String(member.member)}'`);
    } else {
      memberNames.add(member.member);
    }
    if (member.target !== target || member.centerTarget !== target) {
      groupProblems.push(
        `member '${String(member.member)}' resolves DOM '${String(member.target)}' / ` +
          `centre '${String(member.centerTarget)}'`,
      );
    }
    if (member.affordance !== expectedAffordance) {
      groupProblems.push(
        `member '${String(member.member)}' affordance '${String(member.affordance)}'`,
      );
    }
    if (member.width < 24 || member.height < 24) {
      groupProblems.push(
        `member '${String(member.member)}' core ${member.width}x${member.height}px`,
      );
    }
    if (
      !Number.isFinite(member.strokeWidth) ||
      member.strokeWidth <= 0 ||
      member.stroke === "none"
    ) {
      groupProblems.push(`member '${String(member.member)}' has no painted focus stroke`);
    }
  }

  const windowAfter = await page.evaluate(() => ({ x: window.scrollX, y: window.scrollY }));
  if (windowAfter.x !== windowAnchor.x || windowAfter.y !== windowAnchor.y) {
    throw new Error(
      `subpart_group_window_scroll_changed: '${target}' moved browser scroll from ` +
        `${windowAnchor.x},${windowAnchor.y} to ${windowAfter.x},${windowAfter.y}`,
    );
  }
  if (groupProblems.length > 0) {
    throw new Error(
      `subpart_group_not_obvious: '${target}' failed member proof: ${groupProblems.join("; ")}`,
    );
  }
  report.info(
    `[subpart-group proof] ${target} reveals ${groupMemberCount} distinct, painted, ` +
      `learner-sized member surfaces one at a time`,
  );
  return groupMemberCount;
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
  const { wrongOrderMode, screenshotMode, resultsDir, authoredProtocol, guidanceTracker } = opts;
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
        await waitForVisibleTimedWait(page, step.id, resultsDir, report, TIMED_WAIT_BUDGET_MS);
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
    if (target.includes(".")) {
      const groupMemberCount = await proveDeclaredSubpartGroup(page, target, gesture, report);

      const wrongSibling = await pickWrongSiblingItem(page, target);
      if (wrongSibling === null) {
        if (groupMemberCount === 0) {
          throw new Error(
            `wrong_sibling_missing: exact target '${target}' has no visible clickable sibling`,
          );
        }
        const objectPrefix = `${target.slice(0, target.indexOf("."))}.`;
        const nonMemberIdentities = await page
          .locator("#scene-root [data-subpart-hit][data-item-id]")
          .evaluateAll(
            (elements, args) => [
              ...new Set(
                elements
                  .map((element) => element.getAttribute("data-item-id"))
                  .filter(
                    (itemId) =>
                      itemId !== null && itemId.startsWith(args.prefix) && itemId !== args.target,
                  ),
              ),
            ],
            { prefix: objectPrefix, target },
          );
        if (nonMemberIdentities.length > 0) {
          throw new Error(
            `wrong_sibling_not_actionable: group target '${target}' has non-member ` +
              `identities ${nonMemberIdentities.join(", ")} but none has a visible 24px core`,
          );
        }
        report.info(
          `[wrong-sibling probe] ${target} covers every declared rendered member; ` +
            `there is no false sibling to click`,
        );
      } else {
        report.info(`[wrong-sibling probe] clicking ${wrongSibling} (not exact target ${target})`);
        recordInjection(report, step.id, wrongSibling);
        report.summary.wrongSiblingProbes++;
        await clickTargetAndWaitProgress(page, wrongSibling, report, {
          clickBudgetMs: CLICK_BUDGET_MS,
          progressKind: "reject",
        });
      }
    }

    if (wrongOrderMode && gesture !== "type" && gesture !== "adjust") {
      const wrongItem = await pickWrongOrderItem(page, target);
      if (wrongItem) {
        report.info(`[wrong-order injection] clicking ${wrongItem} (not the active target)`);
        recordInjection(report, step.id, wrongItem);
        report.summary.wrongOrderInjections++;
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
      expectedGuidance: expectedGuidanceFor(authoredProtocol, step.id, gs.interactionIndex),
      guidanceTracker,
    });
    const declaredBefore = await readGameState(page);
    checkpoint.declaredStateBefore = declaredStateEvidence(declaredBefore);

    // Structured material-area verification (generic, schema-driven). When the
    // active interaction's response writes a structured object's declared
    // material-tint subpart field, snapshot that object's per-subpart overlay
    // BEFORE the click so the after-verify can assert the targeted members
    // changed and nothing else did. activeMaterialEffects is a read-only
    // projection of authored config + generated object schema; it is empty for
    // every non-material-write interaction. No per-protocol branch.
    const materialEffects = gs.activeMaterialEffects;
    const materialBeforeOverlays = new Map();
    if (Array.isArray(materialEffects)) {
      for (const objectName of new Set(materialEffects.map((effect) => effect.object_name))) {
        materialBeforeOverlays.set(objectName, await readSubpartOverlay(page, objectName));
      }
    }

    // Correct interaction: drive the active interaction through its visible
    // affordance and wait for a progress signal produced by the real handler.
    if (gesture === "type") {
      throw new Error(
        `type_answer_not_visible: step ${step.id} type interaction on '${target}' has no ` +
          "visible learner-facing answer source",
      );
    } else if (gesture === "adjust") {
      const setPoint = await readVisibleAdjustValue(page, target);
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

    // A response may intentionally start a visible TimedWait before applying
    // its declared writes. Wait through that learner-visible phase here, in the
    // SAME checkpoint, so validation reads the completed mutation rather than
    // treating the expected delayed state as a missing write. This consumes the
    // phase, so the next loop cannot duplicate the wait evidence.
    const activeTimedWait = page.locator('[data-timed-wait="active"]:visible').first();
    const timedWaitVisible =
      (await activeTimedWait.count()) > 0 && (await activeTimedWait.isVisible());
    if (shouldAwaitTimedStateWrite(declaredBefore, timedWaitVisible)) {
      const timedWaitEvidence = await waitForVisibleTimedWait(
        page,
        step.id,
        resultsDir,
        report,
        TIMED_WAIT_BUDGET_MS,
      );
      checkpoint.timedWait = timedWaitEvidence;
    }

    // After the interaction settles, run the material-area assertion: every
    // targeted member subpart carries the authored material and its fill
    // changed, and every OTHER rendered subpart kept its prior material/fill.
    // A mismatch throws material_area_multi_mismatch, which fails this step
    // (and reds the protocol in the sweep).
    if (Array.isArray(materialEffects) && materialEffects.length > 0) {
      await verifyMaterialAreaEffectsAfterInteraction(
        page,
        materialEffects,
        materialBeforeOverlays,
        report,
      );
    }

    const declaredAfter = await readGameState(page);
    checkpoint.declaredStateAfter = declaredStateEvidence(declaredAfter);
    validateDeclaredStateMutation(
      declaredBefore,
      declaredAfter,
      target,
      step.id,
      gs.interactionIndex,
    );
    if (
      Array.isArray(declaredBefore.activeStateWrites) &&
      declaredBefore.activeStateWrites.length > 0 &&
      resultsDir !== null
    ) {
      const safeTarget = target.replace(/[^a-z0-9_]/gi, "_");
      const screenshotPath = `${resultsDir}/state_after_${step.id}_i${interactionCounter}_${safeTarget}.png`;
      await page.screenshot({ path: screenshotPath });
      checkpoint.stateAfterScreenshot = screenshotPath;
    }
    // The manifest is evidence of a completed checkpoint, never a pre-click
    // promise. Add it only after the visible interaction and any delayed write
    // have both been validated.
    report.addCheckpoint(checkpoint);

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
    authoredProtocol = null,
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

    // Open the native learner hint once through its real visible summary. The
    // interaction loop then proves that the same disclosure stays open and
    // updates to the current authored hint after every accepted action.
    await openVisibleActionHint(page);
    report.info("Opened visible native action hint");

    // Playwright gives each test an isolated fresh browser context. Enter the
    // product through its normal page load; do not mutate browser persistence
    // behind the learner UI.
    report.info("Using the isolated browser context's normal product start state");

    // Dismiss a product-declared welcome control by clicking it (a real user
    // would). Identity is explicit so unrelated commands such as "Start over"
    // can never be mistaken for initial entry.
    const startBtn = page.locator("#welcome-start-btn, [data-welcome-start]").first();
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
    const guidanceTracker = { instruction: null, hint: null };
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
          authoredProtocol,
          guidanceTracker,
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
      const wrongOrderProblem = wrongOrderAccountingProblem(
        report.summary,
        ending.wrongOrderClicks,
      );
      if (wrongOrderProblem !== null) {
        report.error(wrongOrderProblem);
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
