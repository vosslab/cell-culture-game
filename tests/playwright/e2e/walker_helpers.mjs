// tests/playwright/e2e/walker_helpers.mjs
//
// Reusable Playwright helpers for the schema-driven protocol walker that drives
// the NEW Solid protocol host (src/protocol_host.tsx). They read the FROZEN
// read-only walker surfaces only:
//
//   window.PROTOCOL_STEPS  - the step list (id / label / scene / nextId).
//   window.gameState       - the read-only progress projection, including the
//                            active interaction's target/gesture and the
//                            progress signals the progress predicate watches.
//
// Hard real-click integrity rules enforced here (see WALKTHROUGH_GUIDE.md):
//   - Every advance comes from a real visible click via Playwright's
//     actionability-checked locator.click(). No force-click, no dispatchEvent
//     on hidden nodes.
//   - The read-only surfaces are NEVER written. Nothing here calls an internal
//     runtime/protocol API, mutates the emitter, or forces a scene change.
//   - clickTargetAndWaitProgress snapshots observable progress signals BEFORE
//     the click, clicks the visible element, then WAITS for one of those signals
//     to change as a consequence of the real handler. The wait predicate reads
//     state but never sets it. If nothing changes within budget it throws
//     click_did_not_advance.
//   - A target is verified to EXIST and be VISIBLE before the click; a missing
//     or hidden target fails loudly.
//
// The new host mounts exactly one scene at a time into #scene-root and tags it
// with data-active-scene. Scene switches happen through the same gesture model
// (a validated click whose response carries a SceneChange scene_operation), not
// by writing activeScene. So scene scoping is simply the single #scene-root.

//============================================
// Page-error capture (uncaught runtime exceptions)
//============================================

// An uncaught page exception (for example AmbiguousTargetError thrown during
// eager next-target resolution, see docs/active_plans/audits/
// adjust_did_not_advance_rootcause.md) pre-empts the state mutation a driver
// waits for, so the driver only ever sees a bare timeout. Playwright's
// "pageerror" event is the one channel that still reports the real exception.
// Attach this once per page; the drivers below read the latest captured
// message when their own wait times out, so the reported failure carries the
// real error text instead of a content-free "did_not_advance" message.
export function attachPageErrorCapture(page) {
  page.__capturedPageErrors = [];
  page.on("pageerror", (err) => {
    page.__capturedPageErrors.push(err.message);
  });
}

// Read the most recently captured uncaught page exception, or null if none
// have been captured yet (or attachPageErrorCapture was never called).
function latestPageError(page) {
  const captured = page.__capturedPageErrors;
  if (!captured || captured.length === 0) {
    return null;
  }
  return captured[captured.length - 1];
}

// Build the suffix appended to a "did_not_advance" timeout message when a
// page error was captured during the wait. Returns an empty string when no
// page error is available, so unaffected call sites are unchanged.
function pageErrorSuffix(page) {
  const message = latestPageError(page);
  if (message === null) {
    return "";
  }
  return ` (captured page error: ${message})`;
}

//============================================
// Read-only state snapshots
//============================================

// The progress signals a real click may change. Snapshot-compared, never set.
export async function readProgressSnapshot(page) {
  return await page.evaluate(() => {
    const s = window.gameState;
    return {
      activeStepId: s.activeStepId,
      interactionIndex: s.interactionIndex,
      activeScene: s.activeScene,
      completedStepsCount: (s.completedSteps || []).length,
      selectedTool: s.selectedTool,
      heldLiquid: JSON.stringify(s.heldLiquid),
      wrongOrderClicks: s.wrongOrderClicks,
      isComplete: s.isComplete,
      stateRevision: s.stateRevision,
      lastStateDelta: s.lastStateDelta === null ? null : JSON.stringify(s.lastStateDelta),
    };
  });
}

// Read the full read-only gameState projection.
export async function readGameState(page) {
  return await page.evaluate(() => {
    const s = window.gameState;
    return {
      activeStepId: s.activeStepId,
      interactionIndex: s.interactionIndex,
      activeScene: s.activeScene,
      completedSteps: (s.completedSteps || []).slice(),
      selectedTool: s.selectedTool,
      heldLiquid: s.heldLiquid,
      wrongOrderClicks: s.wrongOrderClicks,
      stepsOutOfOrder: s.stepsOutOfOrder,
      isComplete: s.isComplete,
      activeTarget: s.activeTarget,
      activeGesture: s.activeGesture,
      activeMaterialEffects: s.activeMaterialEffects ?? null,
      stateRevision: s.stateRevision,
      lastStateDelta: s.lastStateDelta,
      stateDeltaLog: s.stateDeltaLog ?? null,
      declaredState: s.declaredState ?? null,
      activeStateWrites: s.activeStateWrites ?? null,
    };
  });
}

function escapedNumberText(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function parseVisibleAdjustCue(cue, target) {
  if (cue.target !== target || cue.gesture !== "adjust") {
    throw new Error(`adjust_visible_cue_mismatch: rail does not identify adjust '${target}'`);
  }
  if (cue.value === null || cue.value.trim() === "") {
    throw new Error(`adjust_visible_value_missing: rail has no data-action-value for '${target}'`);
  }
  const value = Number(cue.value);
  if (!Number.isFinite(value)) {
    throw new Error(`adjust_visible_value_invalid: '${cue.value}' is not a finite number`);
  }
  const numericText = String(value);
  const exactNumber = new RegExp(`(^|[^0-9.])${escapedNumberText(numericText)}($|[^0-9.])`);
  if (!exactNumber.test(cue.text)) {
    throw new Error(
      `adjust_visible_value_unannounced: cue '${cue.text}' does not state exact value '${numericText}'`,
    );
  }
  return numericText;
}

// The walker may enter a set point only when the learner can read the same
// numeric value in the active action rail. This deliberately refuses any
// runtime-only validator projection; an invisible answer is not walkthrough
// evidence.
export async function readVisibleAdjustValue(page, target) {
  const actionRail = page.locator("[data-current-action]").first();
  if ((await actionRail.count()) === 0 || !(await actionRail.isVisible())) {
    throw new Error(`adjust_visible_cue_missing: no visible action rail for '${target}'`);
  }
  const cue = await actionRail.evaluate((element) => {
    const cueElement = element.querySelector(".action-rail-cue");
    return {
      target: element.getAttribute("data-action-target"),
      gesture: element.getAttribute("data-action-gesture"),
      value: element.getAttribute("data-action-value"),
      text: cueElement?.textContent?.trim() ?? "",
    };
  });
  return parseVisibleAdjustCue(cue, target);
}

// Wait for the read-only walker surfaces to appear (after load and after reload).
export async function waitForExports(page, timeoutMs = 8000) {
  try {
    await page.waitForFunction(
      () => {
        return (
          typeof window.gameState !== "undefined" &&
          typeof window.PROTOCOL_STEPS !== "undefined" &&
          Array.isArray(window.PROTOCOL_STEPS) &&
          window.PROTOCOL_STEPS.length > 0
        );
      },
      undefined,
      { timeout: timeoutMs },
    );
  } catch (error) {
    const pageError = latestPageError(page);
    if (pageError !== null) {
      throw new Error(`protocol_runtime_did_not_mount: ${pageError}`, { cause: error });
    }
    throw error;
  }
}

//============================================
// Selectors (scene-scoped to the single mounted scene)
//============================================

// The new host mounts one scene at a time into #scene-root. Scoping to
// #scene-root avoids picking up a shell/outline element that might share an id.
export function resolveSelector(itemId) {
  return `#scene-root [data-item-id="${itemId}"]`;
}

// Save evidence for the authored active target immediately before its visible
// interaction. This stays schema-driven: the target and gesture come from the
// read-only game-state projection, and the element is the same scene-scoped DOM
// node that clickTargetAndWaitProgress will actionability-click.
//
// `visibleTargetBounds` is the intersection of the rendered target box and the
// current viewport, rather than a raw DOMRect that could be nonempty while the
// target is offscreen. A zero-area intersection is a hard evidence failure.
export async function captureVisibleTargetCheckpoint(
  page,
  { protocol, step, target, gesture, interactionIndex, resultsDir },
) {
  const selector = resolveSelector(target);
  const locator = page.locator(selector).first();
  if ((await locator.count()) === 0) {
    throw new Error(`checkpoint_target_missing: ${selector}`);
  }
  if (!(await locator.isVisible())) {
    throw new Error(`checkpoint_target_hidden: ${selector}`);
  }

  // Match Playwright's normal visible-action path before reading geometry; this
  // never dispatches an event or bypasses actionability.
  await locator.scrollIntoViewIfNeeded();
  const bounds = await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const left = Math.max(0, rect.left);
    const top = Math.max(0, rect.top);
    const right = Math.min(window.innerWidth, rect.right);
    const bottom = Math.min(window.innerHeight, rect.bottom);
    return {
      x: left,
      y: top,
      width: Math.max(0, right - left),
      height: Math.max(0, bottom - top),
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  });
  if (bounds.width < 24 || bounds.height < 24) {
    throw new Error(`checkpoint_target_outside_viewport: ${selector}`);
  }

  // The DOM identity that Playwright will click must be the authored target,
  // and it must own an unobscured, learner-sized hit core. This is intentionally
  // a browser hit-test, not a synthetic event or a hidden geometry shortcut.
  const effectiveClickTarget = await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const x = Math.max(rect.left, Math.min(rect.right, rect.left + rect.width / 2));
    const y = Math.max(rect.top, Math.min(rect.bottom, rect.top + rect.height / 2));
    const hit = document.elementFromPoint(x, y);
    const hitItem = hit?.closest?.("[data-item-id]") ?? null;
    const hitRect = hitItem?.getBoundingClientRect();
    return {
      authoredDomTarget: element.getAttribute("data-item-id"),
      hitDomTarget: hitItem?.getAttribute("data-item-id") ?? null,
      coreWidth: hitRect?.width ?? 0,
      coreHeight: hitRect?.height ?? 0,
    };
  });
  if (
    effectiveClickTarget.authoredDomTarget !== target ||
    effectiveClickTarget.hitDomTarget !== target
  ) {
    throw new Error(
      `checkpoint_click_target_mismatch: authored '${target}', DOM '${String(effectiveClickTarget.authoredDomTarget)}', ` +
        `hit '${String(effectiveClickTarget.hitDomTarget)}'`,
    );
  }
  if (effectiveClickTarget.coreWidth < 24 || effectiveClickTarget.coreHeight < 24) {
    throw new Error(
      `checkpoint_click_core_too_small: ${selector} hit core is ` +
        `${effectiveClickTarget.coreWidth}x${effectiveClickTarget.coreHeight}px, need at least 24x24px`,
    );
  }

  // An existing, visible target is not enough: the schema-driven walker knows
  // the answer from gameState, while a learner does not. Require the product UI
  // to advertise that same target through its rendered affordance and current
  // action rail before the walker is allowed to click it.
  const expectedAffordance = gesture === "select" ? "candidate" : "active";
  const affordance = await locator.evaluate((element) => {
    const computed = window.getComputedStyle(element);
    const subpartKind = element.getAttribute("data-subpart-affordance");
    const itemKind = element.getAttribute("data-affordance");
    const kind = subpartKind ?? itemKind ?? "none";
    const isSubpart = subpartKind !== null;
    // Exact-subpart identity lives on the hit-surface group, while the visible
    // learner indicator is its painted child. Reading the group stroke would
    // falsely reject a correctly highlighted lane/well because SVG <g> itself
    // carries no paint.
    const indicator = isSubpart ? element.querySelector(".subpart-focus-indicator") : element;
    const indicatorComputed = indicator === null ? null : window.getComputedStyle(indicator);
    const indicatorWidth = isSubpart
      ? Number.parseFloat(indicatorComputed?.strokeWidth ?? "0")
      : Number.parseFloat(computed.outlineWidth);
    const indicatorStyle = isSubpart
      ? (indicatorComputed?.stroke ?? "none")
      : computed.outlineStyle;
    return {
      kind,
      isSubpart,
      indicatorFound: indicator !== null,
      indicatorWidth,
      indicatorStyle,
    };
  });
  if (affordance.kind !== expectedAffordance) {
    throw new Error(
      `checkpoint_target_not_advertised: ${selector} has affordance ` +
        `'${affordance.kind}', expected '${expectedAffordance}'`,
    );
  }
  if (
    !Number.isFinite(affordance.indicatorWidth) ||
    affordance.indicatorWidth <= 0 ||
    affordance.indicatorStyle === "none"
  ) {
    throw new Error(
      `checkpoint_affordance_not_visible: ${selector} has no painted ` +
        `${affordance.isSubpart ? "stroke" : "outline"}`,
    );
  }

  const actionRail = page.locator("[data-current-action]").first();
  if ((await actionRail.count()) === 0 || !(await actionRail.isVisible())) {
    throw new Error("checkpoint_action_cue_missing: visible [data-current-action] not found");
  }
  const actionCue = await actionRail.evaluate((element) => {
    const cue = element.querySelector(".action-rail-cue");
    return {
      target: element.getAttribute("data-action-target"),
      label: element.getAttribute("data-action-label"),
      gesture: element.getAttribute("data-action-gesture"),
      value: element.getAttribute("data-action-value"),
      text: cue?.textContent?.trim() ?? "",
    };
  });
  if (actionCue.target !== target || actionCue.gesture !== gesture) {
    throw new Error(
      `checkpoint_action_cue_mismatch: rail advertises target '${String(actionCue.target)}' ` +
        `gesture '${String(actionCue.gesture)}', expected '${target}' / '${gesture}'`,
    );
  }
  if (actionCue.text === "") {
    throw new Error("checkpoint_action_cue_empty: current action has no learner-facing cue");
  }
  if (gesture !== "select") {
    if (actionCue.label === null || actionCue.label === "") {
      throw new Error(`checkpoint_action_label_missing: no learner label for '${target}'`);
    }
    if (!actionCue.text.includes(actionCue.label)) {
      throw new Error(
        `checkpoint_action_label_unlinked: cue '${actionCue.text}' does not name ` +
          `'${actionCue.label}'`,
      );
    }
  } else if (actionCue.label !== null && actionCue.text.includes(actionCue.label)) {
    throw new Error(
      `checkpoint_select_answer_revealed: select cue exposes correct label '${actionCue.label}'`,
    );
  }

  const candidateCount =
    gesture === "select"
      ? await page
          .locator(
            [
              '#scene-root [data-affordance="candidate"]',
              '#scene-root [data-subpart-affordance="candidate"]',
            ].join(", "),
          )
          .evaluateAll(
            (elements) =>
              elements.filter((element) => {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return (
                  rect.width > 0 &&
                  rect.height > 0 &&
                  style.visibility !== "hidden" &&
                  style.display !== "none"
                );
              }).length,
          )
      : 0;
  if (gesture === "select" && candidateCount < 2) {
    throw new Error(
      `checkpoint_select_candidates_missing: only ${candidateCount} visible candidates`,
    );
  }

  const safeStep = step.replace(/[^a-z0-9_]/gi, "_");
  const safeTarget = target.replace(/[^a-z0-9_]/gi, "_");
  const screenshot = `${resultsDir}/checkpoint_${safeStep}_i${interactionIndex}_${safeTarget}.png`;
  await page.screenshot({ path: screenshot });
  return {
    protocol,
    step,
    target,
    gesture,
    interactionIndex,
    screenshot,
    visibleTargetBounds: bounds,
    effectiveClickTarget,
    affordance: {
      expectedKind: expectedAffordance,
      renderedKind: affordance.kind,
      indicatorWidth: affordance.indicatorWidth,
      indicatorStyle: affordance.indicatorStyle,
      candidateCount,
    },
    actionCue,
  };
}

// Verify that an intentional TimedWait is visibly explained in both the scene
// and the action rail, capture that state, then wait for the runtime to reveal
// the next interaction. A no-active-target interval without these cues is a
// learner-facing dead end and must fail the walkthrough.
export async function waitForVisibleTimedWait(
  page,
  stepName,
  resultsDir,
  report,
  waitBudgetMs = 3000,
) {
  const equipmentStatus = page.locator('[data-timed-wait="active"]:visible').first();
  if ((await equipmentStatus.count()) === 0 || !(await equipmentStatus.isVisible())) {
    throw new Error(`timed_wait_scene_status_missing: step ${stepName}`);
  }
  const waitRail = page.locator("[data-timed-wait-status]").first();
  if ((await waitRail.count()) === 0 || !(await waitRail.isVisible())) {
    throw new Error(`timed_wait_action_status_missing: step ${stepName}`);
  }
  const waitText = (await waitRail.textContent())?.trim() ?? "";
  if (waitText === "" || !waitText.includes("next highlighted action")) {
    throw new Error(`timed_wait_recovery_cue_missing: step ${stepName}`);
  }
  const safeStep = stepName.replace(/[^a-z0-9_]/gi, "_");
  const screenshot = `${resultsDir}/waiting_${safeStep}.png`;
  await page.screenshot({ path: screenshot });
  report.addEntry("info", `Visible timed wait: ${stepName}`, {
    step_name: stepName,
    screenshot,
    wait_text: waitText,
  });

  const startedAt = Date.now();
  await page.waitForFunction(
    (stepId) => {
      const state = window.gameState;
      return (
        document.querySelector('[data-timed-wait="active"]') === null &&
        (state.activeStepId !== stepId || state.activeTarget !== null)
      );
    },
    stepName,
    { timeout: waitBudgetMs },
  );
  const observedDurationMs = Date.now() - startedAt;
  report.addEntry("info", `Timed wait completed: ${stepName}`, {
    step_name: stepName,
    observed_duration_ms: observedDurationMs,
    wait_budget_ms: waitBudgetMs,
  });
  return { screenshot, observedDurationMs, waitBudgetMs };
}

//============================================
// Real-click + wait-for-progress
//============================================

// Verify a target exists and is visible, then click it and wait for an
// observable progress signal to change as a consequence of the real handler.
//
// progressKind:
//   "advance"  - expect one of the forward progress signals to change
//                (interactionIndex, activeStepId, activeScene, completedSteps,
//                 selectedTool, heldLiquid). Throws click_did_not_advance if
//                nothing changes within budget.
//   "reject"   - (wrong-order injection) expect wrongOrderClicks to increment
//                and the step position to stay unchanged. Throws if the click is
//                silently accepted as progress.
export async function clickTargetAndWaitProgress(
  page,
  itemId,
  report,
  { clickBudgetMs = 3000, progressKind = "advance", screenshotOpts = null } = {},
) {
  const selector = resolveSelector(itemId);
  const locator = page.locator(selector).first();

  // Rule b: verify EXISTS and VISIBLE before clicking. Fail loud otherwise.
  const count = await locator.count();
  if (count === 0) {
    throw new Error(`Element ${selector} does not exist in DOM`);
  }
  const visible = await locator.isVisible();
  if (!visible) {
    throw new Error(`Element ${selector} is not visible`);
  }

  // Rule d: snapshot observable progress signals BEFORE the click.
  const before = await readProgressSnapshot(page);

  // Rule a: real, actionability-checked click on the visible element.
  await locator.click({ timeout: clickBudgetMs });
  report.summary.totalClicks++;
  report.info(`Clicked ${itemId}`);

  if (progressKind === "reject") {
    // Expect wrongOrderClicks to increment; step/index must NOT advance.
    await page
      .waitForFunction((b) => window.gameState.wrongOrderClicks > b.wrongOrderClicks, before, {
        timeout: 1500,
      })
      .catch(() => {
        /* timeout handled by post-state read below */
      });
    const after = await readProgressSnapshot(page);
    if (after.wrongOrderClicks <= before.wrongOrderClicks) {
      throw new Error(
        `wrong_order_not_rejected: click on ${itemId} did not increment wrongOrderClicks ` +
          `(before ${before.wrongOrderClicks}, after ${after.wrongOrderClicks})`,
      );
    }
    if (
      after.interactionIndex !== before.interactionIndex ||
      after.activeStepId !== before.activeStepId ||
      after.stateRevision !== before.stateRevision ||
      after.lastStateDelta !== before.lastStateDelta
    ) {
      throw new Error(
        `wrong_order_advanced_step: click on ${itemId} advanced the step ` +
          `(idx ${before.interactionIndex}->${after.interactionIndex}, ` +
          `step ${before.activeStepId}->${after.activeStepId}, revision ` +
          `${before.stateRevision}->${after.stateRevision})`,
      );
    }
    report.info(`Wrong-order click on ${itemId} rejected (no advance)`);
  } else {
    // Rule d: wait for a forward progress signal. The predicate READS state.
    try {
      await page.waitForFunction(
        (b) => {
          const s = window.gameState;
          if (s.interactionIndex !== b.interactionIndex) return true;
          if (s.activeStepId !== b.activeStepId) return true;
          if (s.activeScene !== b.activeScene) return true;
          if ((s.completedSteps || []).length > b.completedStepsCount) return true;
          if (s.selectedTool !== b.selectedTool) return true;
          if (JSON.stringify(s.heldLiquid) !== b.heldLiquid) return true;
          if (s.isComplete !== b.isComplete) return true;
          return false;
        },
        before,
        { timeout: clickBudgetMs },
      );
    } catch {
      throw new Error(
        `click_did_not_advance: click on ${itemId} produced no state change after ${clickBudgetMs}ms` +
          pageErrorSuffix(page),
      );
    }
    report.info(`Click on ${itemId} progressed`);
  }

  // Optional per-click screenshot.
  if (screenshotOpts && screenshotOpts.mode === "per-click") {
    const { resultsDir, stepName, interactionIndex, clickIndex, gesture, target } = screenshotOpts;
    const screenshotName = `click_${stepName}_i${interactionIndex}_c${clickIndex}_${itemId}.png`;
    const screenshotPath = `${resultsDir}/${screenshotName}`;
    await page.screenshot({ path: screenshotPath });
    report.addEntry("info", `Screenshot: ${screenshotName}`, {
      screenshot: screenshotPath,
      step_name: stepName,
      interaction_index: interactionIndex,
      click_index: clickIndex,
      gesture: gesture || "click",
      target: target || itemId,
      item_id: itemId,
    });
  }
  return { before, after: await readProgressSnapshot(page) };
}

//============================================
// Real type-fill + commit (for the `type` gesture)
//============================================

// Drive a `type` interaction through the VISIBLE type-input affordance
// (src/shell/hud/type_input.tsx): verify the input + commit button exist and
// are visible, fill the input with a real Playwright fill() (actionability-
// checked), then click the visible Commit button and wait for an observable
// forward progress signal. No internal state write, no force interaction.
//
// typedText: the raw string the student would type.
export async function typeCommitAndWaitProgress(
  page,
  typedText,
  report,
  { clickBudgetMs = 3000 } = {},
) {
  const inputLocator = page.locator("[data-type-input]").first();
  const commitLocator = page.locator("[data-type-commit]").first();

  // Rule b: verify EXISTS and VISIBLE before interacting. Fail loud otherwise.
  if ((await inputLocator.count()) === 0) {
    throw new Error("type_input_missing: [data-type-input] affordance not in DOM for type gesture");
  }
  if (!(await inputLocator.isVisible())) {
    throw new Error("type_input_hidden: [data-type-input] affordance is not visible");
  }
  if ((await commitLocator.count()) === 0 || !(await commitLocator.isVisible())) {
    throw new Error("type_commit_missing: [data-type-commit] button not visible for type gesture");
  }

  // Rule d: snapshot observable progress signals BEFORE the commit.
  const before = await readProgressSnapshot(page);

  // Real, actionability-checked fill + commit.
  await inputLocator.fill(typedText);
  await commitLocator.click();
  report.summary.totalClicks++;
  report.info(`Typed "${typedText}" and committed`);

  try {
    await page.waitForFunction(
      (b) => {
        const s = window.gameState;
        if (s.interactionIndex !== b.interactionIndex) return true;
        if (s.activeStepId !== b.activeStepId) return true;
        if (s.activeScene !== b.activeScene) return true;
        if ((s.completedSteps || []).length > b.completedStepsCount) return true;
        if (s.isComplete !== b.isComplete) return true;
        return false;
      },
      before,
      { timeout: clickBudgetMs },
    );
  } catch {
    throw new Error(
      `type_did_not_advance: committing "${typedText}" produced no state change after ${clickBudgetMs}ms` +
        pageErrorSuffix(page),
    );
  }
  report.info(`Type commit "${typedText}" progressed`);
}

//============================================
// Real set-point commit (for the `adjust` gesture)
//============================================

// Drive an `adjust` interaction through the VISIBLE shared numeric set-point
// editor (src/shell/hud/set_point_editor.tsx): verify the numeric input + commit
// button exist and are visible, fill the input with a real Playwright fill()
// (actionability-checked), then click the visible Commit button and wait for an
// observable forward progress signal. No internal state write, no force
// interaction.
//
// numericValue: the set-point visibly announced by data-action-value in the
// learner-facing action rail.
export async function adjustCommitAndWaitProgress(
  page,
  numericValue,
  report,
  { clickBudgetMs = 3000 } = {},
) {
  const inputLocator = page.locator("[data-adjust-input]").first();
  const commitLocator = page.locator("[data-adjust-commit]").first();

  // Rule b: verify EXISTS and VISIBLE before interacting. Fail loud otherwise.
  if ((await inputLocator.count()) === 0) {
    throw new Error(
      "adjust_input_missing: [data-adjust-input] affordance not in DOM for adjust gesture",
    );
  }
  if (!(await inputLocator.isVisible())) {
    throw new Error("adjust_input_hidden: [data-adjust-input] affordance is not visible");
  }
  if ((await commitLocator.count()) === 0 || !(await commitLocator.isVisible())) {
    throw new Error(
      "adjust_commit_missing: [data-adjust-commit] button not visible for adjust gesture",
    );
  }

  // Rule d: snapshot observable progress signals BEFORE the commit.
  const before = await readProgressSnapshot(page);

  // Real, actionability-checked fill + commit.
  await inputLocator.fill(numericValue);
  await commitLocator.click();
  report.summary.totalClicks++;
  report.info(`Set set-point "${numericValue}" and committed`);

  try {
    await page.waitForFunction(
      (b) => {
        const s = window.gameState;
        if (s.interactionIndex !== b.interactionIndex) return true;
        if (s.activeStepId !== b.activeStepId) return true;
        if (s.activeScene !== b.activeScene) return true;
        if ((s.completedSteps || []).length > b.completedStepsCount) return true;
        if (s.isComplete !== b.isComplete) return true;
        return false;
      },
      before,
      { timeout: clickBudgetMs },
    );
  } catch {
    throw new Error(
      `adjust_did_not_advance: committing set-point "${numericValue}" produced no state change ` +
        `after ${clickBudgetMs}ms` +
        pageErrorSuffix(page),
    );
  }
  report.info(`Adjust commit "${numericValue}" progressed`);
}

//============================================
// Real drag placement (for the `drag` gesture)
//============================================

// Drive a `drag` interaction through the host drag surface: resolve the source
// and destination scene objects (both carry data-item-id={placement_name}),
// verify each exists and is visible, drive a real Playwright source.dragTo(dest)
// (actionability-checked, no forced event), then wait for an observable forward
// progress signal.
//
// No content protocol authors a drag yet, so this driver is exercised by the
// walker only once a real drag protocol lands; until then it is proven by the
// step-machine unit test of handle_drag_commit. It is a real, visible-UI driver
// with no internal state write, kept in parity with the other gesture drivers.
export async function dragToAndWaitProgress(
  page,
  sourceItemId,
  destinationItemId,
  report,
  { clickBudgetMs = 3000 } = {},
) {
  const sourceLocator = page.locator(resolveSelector(sourceItemId)).first();
  const destLocator = page.locator(resolveSelector(destinationItemId)).first();

  // Rule b: verify BOTH endpoints EXIST and are VISIBLE before dragging.
  if ((await sourceLocator.count()) === 0) {
    throw new Error(`drag_source_missing: ${resolveSelector(sourceItemId)} does not exist in DOM`);
  }
  if (!(await sourceLocator.isVisible())) {
    throw new Error(`drag_source_hidden: ${resolveSelector(sourceItemId)} is not visible`);
  }
  if ((await destLocator.count()) === 0) {
    throw new Error(
      `drag_destination_missing: ${resolveSelector(destinationItemId)} does not exist in DOM`,
    );
  }
  if (!(await destLocator.isVisible())) {
    throw new Error(
      `drag_destination_hidden: ${resolveSelector(destinationItemId)} is not visible`,
    );
  }

  // Rule d: snapshot observable progress signals BEFORE the drag.
  const before = await readProgressSnapshot(page);

  // Real, actionability-checked drag from source to destination.
  await sourceLocator.dragTo(destLocator);
  report.summary.totalClicks++;
  report.info(`Dragged ${sourceItemId} onto ${destinationItemId}`);

  try {
    await page.waitForFunction(
      (b) => {
        const s = window.gameState;
        if (s.interactionIndex !== b.interactionIndex) return true;
        if (s.activeStepId !== b.activeStepId) return true;
        if (s.activeScene !== b.activeScene) return true;
        if ((s.completedSteps || []).length > b.completedStepsCount) return true;
        if (s.isComplete !== b.isComplete) return true;
        return false;
      },
      before,
      { timeout: clickBudgetMs },
    );
  } catch {
    throw new Error(
      `drag_did_not_advance: dragging ${sourceItemId} onto ${destinationItemId} produced no ` +
        `state change after ${clickBudgetMs}ms` +
        pageErrorSuffix(page),
    );
  }
  report.info(`Drag ${sourceItemId}->${destinationItemId} progressed`);
}

//============================================
// Wrong-order item picker
//============================================

// Pick a visible, pointer-actionable scene item that is NOT the required target.
// Used by --wrong-order mode to inject a real browser click on a non-required
// object. The runtime still evaluates that input under the authored `click` or
// `select` gesture; those protocol semantics remain distinct.
//
// Visibility alone is insufficient: structured-object hit surfaces keep inert
// subpart nodes in the DOM while a whole-object interaction is active. Those
// nodes have non-zero geometry, but the base SVG correctly receives pointer
// events instead. Match the candidate against the topmost data-item-id at its
// center so the picker follows the same hit-testing path as a real click.
//
// An exact or declared-group target also leaves its structured object's parent
// wrapper in the DOM. That wrapper is not a different learner action: member
// hit surfaces own the actionable area. Exclude it so wrong-order mode chooses
// a genuinely different object or concrete sibling.
export function isDistinctWrongOrderCandidate(requiredItemId, candidateItemId) {
  if (candidateItemId === null || candidateItemId === requiredItemId) return false;
  const dot = requiredItemId.indexOf(".");
  if (dot > 0 && candidateItemId === requiredItemId.slice(0, dot)) return false;
  return true;
}

export async function pickWrongOrderItem(page, requiredItemId) {
  return await page.evaluate((required) => {
    const items = document.querySelectorAll("#scene-root [data-item-id]");
    const requiredDot = required.indexOf(".");
    const requiredParent = requiredDot > 0 ? required.slice(0, requiredDot) : null;
    for (const elem of items) {
      const itemId = elem.getAttribute("data-item-id");
      if (itemId === null || itemId === required || itemId === requiredParent) continue;
      const style = window.getComputedStyle(elem);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const rect = elem.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      if (
        centerX < 0 ||
        centerY < 0 ||
        centerX >= window.innerWidth ||
        centerY >= window.innerHeight
      ) {
        continue;
      }
      const hit = document.elementFromPoint(centerX, centerY);
      const hitItem = hit?.closest?.("[data-item-id]") ?? null;
      if (hitItem?.getAttribute("data-item-id") !== itemId) continue;
      return itemId;
    }
    return null;
  }, requiredItemId);
}

// Pick a real visible sibling of an exact dotted target. The sibling must belong
// to the same structured object and pass the browser's center hit-test, so this
// proves a learner's plausible wrong well/lane click is rejected by normal UI.
export async function pickWrongSiblingItem(page, requiredItemId) {
  const dot = requiredItemId.indexOf(".");
  if (dot < 1) return null;
  const objectName = requiredItemId.slice(0, dot);
  return await page.evaluate(
    ({ required, object }) => {
      const prefix = `${object}.`;
      const items = document.querySelectorAll("#scene-root [data-item-id]");
      for (const element of items) {
        const itemId = element.getAttribute("data-item-id");
        if (itemId === null || itemId === required || !itemId.startsWith(prefix)) continue;
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        if (
          style.display === "none" ||
          style.visibility === "hidden" ||
          rect.width < 24 ||
          rect.height < 24
        )
          continue;
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        if (x < 0 || y < 0 || x >= window.innerWidth || y >= window.innerHeight) continue;
        const hit = document.elementFromPoint(x, y)?.closest?.("[data-item-id]");
        if (hit?.getAttribute("data-item-id") === itemId) return itemId;
      }
      return null;
    },
    { required: requiredItemId, object: objectName },
  );
}

//============================================
// Structured material-area verification (generic, schema-driven)
//============================================

// Read every rendered subpart on one structured object's material overlay as a
// pure DOM read: for each [data-subpart-name] shape inside the object's
// [data-subpart-overlay] svg, capture its material name (data-material-name) and
// its resolved fill. Returns a map { subpartName: { material, fill } }. Empty
// object when no overlay for that object is mounted in the current scene.
//
// This is the generic counterpart of the bespoke all-wells reader: it enumerates
// EVERY rendered subpart (not a hand-picked sample) so both the positive check
// (targeted subparts changed) and the negative check (nothing else changed) can
// run over the full rendered set.
export async function readSubpartOverlay(page, objectName) {
  return await page.evaluate((obj) => {
    const out = {};
    const root = document.querySelector("#scene-root");
    if (root === null) return out;
    const overlay = root.querySelector(`[data-subpart-overlay='${obj}']`);
    if (overlay === null) return out;
    const shapes = overlay.querySelectorAll("[data-subpart-name]");
    for (const shape of shapes) {
      const name = shape.getAttribute("data-subpart-name");
      if (name === null) continue;
      out[name] = {
        material: shape.getAttribute("data-material-name"),
        fill: shape.getAttribute("fill"),
      };
    }
    return out;
  }, objectName);
}

// Wait (best-effort, bounded) for the first expected member subpart to reach the
// authored material value, so the reactive overlay has settled before the full
// snapshot is read. A timeout is swallowed: the subsequent assertion reads the
// real post-state and reports the actual mismatch rather than a bare timeout.
async function waitForSubpartMaterial(page, objectName, subpartName, value, timeoutMs) {
  try {
    await page.waitForFunction(
      ({ obj, sub, val }) => {
        const root = document.querySelector("#scene-root");
        if (root === null) return false;
        const overlay = root.querySelector(`[data-subpart-overlay='${obj}']`);
        if (overlay === null) return false;
        const shape = overlay.querySelector(`[data-subpart-name='${sub}']`);
        if (shape === null) return false;
        return shape.getAttribute("data-material-name") === val;
      },
      { obj: objectName, sub: subpartName, val: value },
      { timeout: timeoutMs },
    );
  } catch {
    // Let the assertion below read and report the real state.
  }
}

// Assert the structured material-area effect: EVERY expected member subpart now
// carries material_value (and its fill visibly changed when it was a real
// transition), and EVERY other rendered subpart kept its prior material and fill
// ("and nothing else", MATERIAL_DESIGN.md spatial correspondence). Throws a
// single material_area_mismatch Error listing every problem when any check fails.
// A pure comparison over the before/after DOM snapshots; no state is written.
export function verifyMaterialAreaEffect(effect, before, after, report) {
  const { object_name, material_value, expected_subparts } = effect;
  const expectedSet = new Set(expected_subparts);

  // The overlay must be mounted to verify a structured material write. A missing
  // overlay means the student saw no material area change where the protocol
  // wrote one -- a spatial-correspondence failure, not a pass.
  if (Object.keys(after).length === 0) {
    throw new Error(
      `material_area_no_overlay: object '${object_name}' has no rendered subpart overlay, ` +
        `so the write of '${material_value}' to ${expected_subparts.length} subpart(s) is not visible`,
    );
  }

  const problems = [];

  // POSITIVE: every targeted member carries the authored material; its fill
  // changed when the material actually transitioned (a member already holding
  // the value is a legitimate no-op, not a bug).
  for (const name of expected_subparts) {
    const a = after[name];
    if (a === undefined) {
      problems.push(`expected member '${name}' is not rendered in the overlay`);
      continue;
    }
    if (a.material !== material_value) {
      problems.push(
        `member '${name}': material '${a.material}' !== authored '${material_value}' (silent no-op)`,
      );
    }
    const b = before[name];
    if (b !== undefined && b.material !== material_value && a.fill === b.fill) {
      problems.push(
        `member '${name}': fill did not change (before '${b.fill}' after '${a.fill}') ` +
          `though material transitioned to '${material_value}'`,
      );
    }
  }

  // NEGATIVE: no non-targeted rendered subpart changed material or fill.
  for (const name of Object.keys(after)) {
    if (expectedSet.has(name)) continue;
    const a = after[name];
    const b = before[name];
    if (b === undefined) continue; // newly appeared; nothing to compare against
    if (a.material !== b.material || a.fill !== b.fill) {
      problems.push(
        `non-target subpart '${name}' changed: material '${b.material}'->'${a.material}', ` +
          `fill '${b.fill}'->'${a.fill}'`,
      );
    }
  }

  if (problems.length > 0) {
    throw new Error(
      `material_area_mismatch on '${object_name}' (value '${material_value}', ` +
        `${expected_subparts.length} expected member(s)): ${problems.join("; ")}`,
    );
  }
  report.info(
    `Material-area verified on '${object_name}': ${expected_subparts.length} member(s) = ` +
      `'${material_value}', ${Object.keys(after).length - expected_subparts.length} other subpart(s) unchanged`,
  );
}

// Drive the full material-area verification around one interaction. `before` is
// the overlay snapshot captured BEFORE the interaction's click; this reads the
// AFTER snapshot (once the first expected member has settled) and asserts.
export async function verifyMaterialAreaAfterInteraction(page, effect, before, report) {
  const firstMember = effect.expected_subparts[0];
  if (firstMember !== undefined) {
    await waitForSubpartMaterial(
      page,
      effect.object_name,
      firstMember,
      effect.material_value,
      1500,
    );
  }
  const after = await readSubpartOverlay(page, effect.object_name);
  verifyMaterialAreaEffect(effect, before, after, report);
}

// Verify every structured material effect authored by one interaction as one
// atomic visible change. Effects for one object are merged by concrete member
// in operation order, so a legitimate ladder lane transition cannot be treated
// as an unexpected change while sample lanes transition to a different material.
export function verifyMaterialAreaEffects(effects, beforeByObject, afterByObject, report) {
  const expectedByObject = new Map();
  for (const effect of effects) {
    let expectedMembers = expectedByObject.get(effect.object_name);
    if (expectedMembers === undefined) {
      expectedMembers = new Map();
      expectedByObject.set(effect.object_name, expectedMembers);
    }
    for (const member of effect.expected_subparts) {
      expectedMembers.set(member, effect.material_value);
    }
  }

  const problems = [];
  for (const [objectName, expectedMembers] of expectedByObject) {
    const before = beforeByObject.get(objectName) ?? {};
    const after = afterByObject.get(objectName) ?? {};
    if (Object.keys(after).length === 0) {
      problems.push(`object '${objectName}' has no rendered subpart overlay`);
      continue;
    }
    for (const [member, materialValue] of expectedMembers) {
      const afterMember = after[member];
      if (afterMember === undefined) {
        problems.push(`object '${objectName}' expected member '${member}' is not rendered`);
        continue;
      }
      if (afterMember.material !== materialValue) {
        problems.push(
          `object '${objectName}' member '${member}' material '${afterMember.material}' !== '${materialValue}'`,
        );
      }
      const beforeMember = before[member];
      if (
        beforeMember !== undefined &&
        beforeMember.material !== materialValue &&
        afterMember.fill === beforeMember.fill
      ) {
        problems.push(
          `object '${objectName}' member '${member}' fill did not change for material transition`,
        );
      }
    }
    for (const [member, afterMember] of Object.entries(after)) {
      if (expectedMembers.has(member)) continue;
      const beforeMember = before[member];
      if (
        beforeMember !== undefined &&
        (afterMember.material !== beforeMember.material || afterMember.fill !== beforeMember.fill)
      ) {
        problems.push(
          `object '${objectName}' non-target subpart '${member}' changed: ` +
            `material '${beforeMember.material}'->'${afterMember.material}', ` +
            `fill '${beforeMember.fill}'->'${afterMember.fill}'`,
        );
      }
    }
  }
  if (problems.length > 0) {
    throw new Error(`material_area_multi_mismatch: ${problems.join("; ")}`);
  }
  for (const [objectName, expectedMembers] of expectedByObject) {
    report.info(
      `Material-area verified on '${objectName}': ${expectedMembers.size} authored member transition(s)`,
    );
  }
}

export async function verifyMaterialAreaEffectsAfterInteraction(
  page,
  effects,
  beforeByObject,
  report,
) {
  await Promise.all(
    effects.map(async (effect) => {
      const member = effect.expected_subparts[0];
      if (member !== undefined) {
        await waitForSubpartMaterial(page, effect.object_name, member, effect.material_value, 1500);
      }
    }),
  );
  const objectNames = [...new Set(effects.map((effect) => effect.object_name))];
  const afterByObject = new Map();
  for (const objectName of objectNames) {
    afterByObject.set(objectName, await readSubpartOverlay(page, objectName));
  }
  verifyMaterialAreaEffects(effects, beforeByObject, afterByObject, report);
}

//============================================
// Report logging helpers
//============================================

export function recordInfo(report, message) {
  report.info(message);
}

export function recordWarn(report, message) {
  report.warn(message);
}

export function recordError(report, stepId, kind, evidence) {
  report.error(`[${kind}] ${evidence}`, { stepId });
}

export function recordInjection(report, stepId, itemId) {
  report.addEntry("injection", `[injection] step ${stepId}: clicked wrong-order item ${itemId}`, {
    stepId,
    injectedItemId: itemId,
  });
}
