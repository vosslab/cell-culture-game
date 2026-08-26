// Learner-facing protocol outcome regressions.
//
// Selector contract:
// - The shared walker helpers (tests/playwright/e2e/walker_helpers.mjs) only
//   read window.gameState to identify the NEXT visible target; they advance
//   solely through Playwright's actionability-checked clicks and visible set
//   point controls.
// - [data-action-recovery] is the guidance-bar recovery text rendered by
//   src/shell/regions/guidance_bar.tsx.
// - data-asset-layer and data-overlay-field are emitted by
//   src/scene_runtime/renderer/scene_item.tsx for visual state evidence.
//
// These checks deliberately stop before the final interpretation selection.
// They prove that the observation a student needs is visible BEFORE protocol
// completion, rather than merely proving that the stored end state exists.

import { test, expect, type Page } from "@playwright/test";

import {
  adjustCommitAndWaitProgress,
  clickTargetAndWaitProgress,
  readGameState,
  waitForVisibleTimedWait,
} from "./e2e/walker_helpers.mjs";

interface WalkReport {
  summary: { totalClicks: number };
  info: (message: string) => void;
  addEntry: (level: string, message: string, details: Record<string, unknown>) => void;
}

interface ReadonlyWalkerWindow {
  readonly gameState?: {
    readonly activeTarget: string | null;
    readonly activeGesture: string | null;
  };
}

function walkReport(): WalkReport {
  return {
    summary: { totalClicks: 0 },
    info: () => undefined,
    addEntry: () => undefined,
  };
}

async function visibleActionValue(page: Page): Promise<string> {
  const action = page.locator("[data-current-action]").first();
  await expect(action).toBeVisible();
  const value = await action.getAttribute("data-action-value");
  expect(value, "an adjust action must expose its required visible value").not.toBeNull();
  return value!;
}

// The action rail names the learner-visible placed target, which may be more
// specific than an abstract authored object name. Read it, then delegate the
// real scene click and progress wait to the shared walker helper.
async function clickVisibleActionAndWaitProgress(page: Page, report: WalkReport): Promise<string> {
  const action = page.locator("[data-current-action]").first();
  await expect(action).toBeVisible();
  const target = await action.getAttribute("data-action-target");
  expect(target, "the visible action must name its scene target").not.toBeNull();
  await clickTargetAndWaitProgress(page, target!, report);
  return target!;
}

// Drive only by the current learner-visible action. gameState is read-only
// walker diagnostics, never a progress API; every transition below is a real
// visible click or a visible numeric-control commit via the shared helper.
async function walkToStep(page: Page, protocol: string, destinationStep: string): Promise<void> {
  const report = walkReport();
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto(`/${protocol}.html`, { waitUntil: "networkidle" });
  await page
    .waitForFunction(() => (window as ReadonlyWalkerWindow).gameState !== undefined, undefined, {
      timeout: 5_000,
    })
    .catch(() => {
      throw new Error(
        `${protocol} did not mount its learner runtime: ` +
          (pageErrors.join(" | ") || "no page error captured"),
      );
    });

  for (let actionCount = 0; actionCount < 180; actionCount += 1) {
    const state = await readGameState(page);
    if (state.activeStepId === destinationStep) return;

    if (state.activeTarget === null || state.activeGesture === null) {
      // Timed states keep their own visible learner-facing status. Wait for the
      // next real action rather than touching the protocol runtime.
      await page.waitForFunction(
        () => {
          const current = (window as ReadonlyWalkerWindow).gameState;
          return (
            current !== undefined && current.activeTarget !== null && current.activeGesture !== null
          );
        },
        undefined,
        { timeout: 5_000 },
      );
      continue;
    }

    if (state.activeGesture === "adjust") {
      await adjustCommitAndWaitProgress(page, await visibleActionValue(page), report);
      continue;
    }
    if (state.activeGesture === "click" || state.activeGesture === "select") {
      await clickTargetAndWaitProgress(page, state.activeTarget, report);
      continue;
    }

    throw new Error(
      `pedagogy outcome walk encountered unsupported visible gesture '${state.activeGesture}' ` +
        `before '${destinationStep}' in '${protocol}'`,
    );
  }

  throw new Error(`pedagogy outcome walk did not reach '${destinationStep}' in '${protocol}'`);
}

test("incorrect Trypan Blue viability choice gives specific visible recovery feedback", async ({
  page,
}) => {
  await walkToStep(page, "trypan_blue_counting", "verify_viability_gate");

  await expect(
    page.locator("#scene-root [data-placement-name='main_viability_results_display'] img"),
  ).toBeVisible();
  const actionHint = page.locator("[data-action-hint]");
  const hintSummary = actionHint.locator("summary");
  const hintText = actionHint.locator("[data-action-hint-text]");
  await hintSummary.click();
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(hintText).toBeVisible();
  await expect(hintText).toContainText(/visible percentage|threshold|evidence/i);
  await expect(hintText).not.toContainText("Proceed: viability above 90%");
  await expect(hintText).not.toContainText("Stop and recount");
  await expect(hintText).not.toContainText("92.5%");
  await expect(page.locator("[data-current-action-instruction]")).not.toContainText(
    "Proceed: viability above 90%",
  );
  await expect(page.locator("[data-current-action-target-label]")).toHaveCount(0);
  const candidates = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='candidate']:visible",
  );
  expect(
    await candidates.count(),
    "both scientific choices must be visibly offered",
  ).toBeGreaterThanOrEqual(2);
  const candidateGeometry = await candidates.evaluateAll((elements) =>
    elements.map((element) => {
      const box = element.getBoundingClientRect();
      const topmost = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
      return {
        target: element.getAttribute("data-item-id"),
        width: box.width,
        height: box.height,
        centerTarget: topmost?.closest("[data-item-id]")?.getAttribute("data-item-id") ?? null,
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
      };
    }),
  );
  for (const candidate of candidateGeometry) {
    expect(
      candidate.width,
      `${candidate.target} preserves the shared 44px hit baseline`,
    ).toBeGreaterThanOrEqual(44);
    expect(
      candidate.height,
      `${candidate.target} preserves the shared 44px hit baseline`,
    ).toBeGreaterThanOrEqual(44);
    expect(candidate.centerTarget, `${candidate.target} owns its visible click center`).toBe(
      candidate.target,
    );
  }
  for (let index = 0; index < candidateGeometry.length; index += 1) {
    for (let other = index + 1; other < candidateGeometry.length; other += 1) {
      const first = candidateGeometry[index]!;
      const second = candidateGeometry[other]!;
      const overlap =
        first.left < second.right &&
        second.left < first.right &&
        first.top < second.bottom &&
        second.top < first.bottom;
      expect(
        overlap,
        `${first.target} and ${second.target} remain distinct candidate actions`,
      ).toBe(false);
    }
  }
  await expect(page.locator("[data-current-action-instruction]")).toContainText(
    "Compare the displayed viability percentage with the stated downstream " +
      "gate and choose the matching decision.",
  );
  await expect(hintText).toHaveText(
    "Use the counter's visible percentage and the threshold shown in the " +
      "review screen as your evidence.",
  );
  await expect(page.locator("[data-current-action-instruction]")).not.toContainText(
    "Choose one blue outlined lab item.",
  );
  await expect(hintText).not.toContainText("Choose one blue outlined lab item.");

  // The displayed 92.5% viability clears the stated gate, so Recount is the
  // scientifically wrong visible alternative. This is a real click, not a
  // synthetic rejection, and the protocol must remain at the decision.
  await page.locator("#scene-root [data-item-id='viability_recount_choice']").click();
  const viabilityRecovery = page.locator("[data-action-recovery]");
  await expect(viabilityRecovery).toContainText("You chose: Stop and recount");
  await expect(viabilityRecovery).toContainText("Correct: Proceed: viability above 90%");
  await expect(viabilityRecovery).toContainText(
    "Compare the displayed viability percentage with the stated threshold " +
      "before deciding whether to proceed or recount.",
  );
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);

  await page.locator("#scene-root [data-item-id='viability_proceed_choice']").click();
  await expect(page.locator("[data-protocol-complete]")).toBeVisible();
  await expect(page.locator("[data-interaction-feedback='correct']")).toContainText(
    "The displayed viability clears the stated gate",
  );
});

test("cell-seeding select guidance is authored and advances after the real card click", async ({
  page,
}) => {
  await page.goto("/cell_seeding_plate_setup.html", { waitUntil: "networkidle" });

  const action = page.locator("[data-current-action]");
  const instruction = action.locator("[data-current-action-instruction]");
  const actionMessage = page.locator("[data-current-action-instruction] #guidance-text");
  const actionHint = page.locator("[data-action-hint]");
  const hintText = actionHint.locator("[data-action-hint-text]");

  await expect(action).toHaveAttribute("data-action-gesture", "select");
  await expect(action).not.toHaveAttribute("data-action-target");
  await expect(instruction).toContainText(
    "Choose the calculation card that matches the displayed dilution equation and target volume.",
  );
  await actionHint.locator("summary").click();
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(hintText).toHaveText(
    "Use the visible stock concentration, target concentration, and 12 mL " +
      "final volume to identify the card whose V1 is in milliliters.",
  );
  await expect(actionMessage).not.toContainText("calculation_2_8_ml");
  await expect(hintText).not.toContainText("2.8 mL");
  await expect(page.locator("[data-current-action-target-label]")).toHaveCount(0);

  await page.locator("#scene-root [data-placement-name='calculation_2_8_choice']").click();

  await expect(action).toHaveAttribute(
    "data-action-target",
    "right_sterile_serological_pipette_pack",
  );
  await expect(action).toHaveAttribute("data-action-gesture", "click");
  await expect(instruction).toContainText(
    "Fit a fresh serological pipette for the media transfer.",
  );
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(hintText).toHaveText(
    "Use a sterile graduated pipette to draw the measured media first.",
  );
  await expect(actionMessage).toContainText(
    "Fit a fresh serological pipette for the media transfer.",
  );
});

test("an open hint follows each authored repeated mixing action", async ({ page }) => {
  await walkToStep(page, "trypan_blue_counting", "mix_by_pipetting");

  const actionHint = page.locator("[data-action-hint]");
  const hintSummary = actionHint.locator("summary");
  const hintText = actionHint.locator("[data-action-hint-text]");
  await hintSummary.click();
  await expect(actionHint).toHaveAttribute("open", "");

  const report = walkReport();
  await clickVisibleActionAndWaitProgress(page, report);
  const action = page.locator("[data-current-action]");
  const instruction = action.locator("[data-current-action-instruction]");
  await expect(action).toHaveAttribute("data-action-target", "right_hemocytometer_slide.diamond");
  await expect(action).toHaveAttribute("data-action-gesture", "click");
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(instruction).toContainText("Complete mixing cycle 1 in the central diamond.");
  await expect(hintText).toHaveText(
    "Pipette the mixture gently up and down once; stop after cycle 1.",
  );

  await clickVisibleActionAndWaitProgress(page, report);
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(instruction).toContainText("Complete mixing cycle 2 in the central diamond.");
  await expect(hintText).toHaveText(
    "Pipette the mixture gently up and down once; stop after cycle 2.",
  );

  await clickVisibleActionAndWaitProgress(page, report);
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(instruction).toContainText("Complete mixing cycle 3 in the central diamond.");
  await expect(hintText).toHaveText(
    "Pipette the mixture gently up and down once; stop after cycle 3.",
  );
});

test("timed wait retains the protocol cursor and restores the next action", async ({ page }) => {
  await walkToStep(page, "sdspage_run_electrophoresis", "run_to_tracking_dye_endpoint");

  const report = walkReport();
  const cursorBeforeWait = await readGameState(page);
  await expect(page.locator("[data-current-action]")).toHaveAttribute(
    "data-action-label",
    "Power Supply",
  );
  await clickVisibleActionAndWaitProgress(page, report);
  await expect(page.locator('[data-timed-wait="active"]:visible')).toBeVisible();
  const timedWaitStatus = page.locator("[data-timed-wait-status]");
  await expect(timedWaitStatus).toContainText("next highlighted action");
  await expect(timedWaitStatus).toContainText(
    /30\s*(?:minutes?|min).*(?:simulated|compressed)|(?:simulated|compressed).*30\s*(?:minutes?|min)/i,
  );
  await expect(page.locator("[data-current-action]")).toHaveCount(0);
  const cursorDuringWait = await readGameState(page);
  expect(cursorDuringWait.activeStepId).toBe(cursorBeforeWait.activeStepId);
  expect(cursorDuringWait.interactionIndex).toBe(cursorBeforeWait.interactionIndex + 1);
  expect(cursorDuringWait.activeTarget).toBeNull();
  expect(cursorDuringWait.activeGesture).toBeNull();

  await waitForVisibleTimedWait(
    page,
    "run_to_tracking_dye_endpoint",
    "test-results/guidance_timed_wait",
    report,
  );
  const restoredAction = page.locator("[data-current-action]");
  await expect(restoredAction).toBeVisible();
  await expect(restoredAction).toHaveAttribute("data-action-gesture", "select");
  await expect(restoredAction).not.toHaveAttribute("data-action-target");
  await expect(restoredAction).not.toHaveAttribute("data-action-label");
});

test("SDS-PAGE endpoint requires a stop decision before switching the supply off", async ({
  page,
}) => {
  await walkToStep(page, "sdspage_run_electrophoresis", "stop_at_tracking_dye_endpoint");

  await expect(
    page.locator(
      "#scene-root " + "[data-placement-name='center_electrophoresis_endpoint_display'] img",
    ),
  ).toBeVisible();
  await expect(
    page.locator("#scene-root [data-placement-name='front_left_endpoint_stop_now']"),
  ).toBeVisible();
  await expect(
    page.locator("#scene-root [data-placement-name='front_right_endpoint_continue']"),
  ).toBeVisible();

  // Continuing is intentionally visible so the learner can compare it with the
  // evidence, but it must be rejected and leave the physical supply untouched.
  await page.locator("#scene-root [data-placement-name='front_right_endpoint_continue']").click();
  const endpointRecovery = page.locator("[data-action-recovery]");
  await expect(endpointRecovery).toContainText(
    "You chose: Continue running: let the dye front pass the gel",
  );
  await expect(endpointRecovery).toContainText(
    "Correct: Stop now: dye front is at the safe endpoint",
  );
  await expect(endpointRecovery).toContainText(
    "Do not continue this run: the visible dye front is already near the " +
      "bottom of the gel. Select Stop now, then switch the supply off.",
  );
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);

  await page.locator("#scene-root [data-placement-name='front_left_endpoint_stop_now']").click();
  const powerSupplyAction = page.locator("[data-current-action]");
  await expect(powerSupplyAction).toHaveAttribute("data-action-label", "Power Supply");
  await expect(powerSupplyAction.locator("[data-current-action-instruction]")).toContainText(
    "Turn off the power supply at the tracking-dye endpoint.",
  );
  await page.locator("#scene-root [data-placement-name='rear_right_power_supply']").click();
  await expect(page.locator("[data-protocol-complete]")).toBeVisible();
  await expect(page.locator("[data-interaction-feedback='correct']")).toContainText(
    "Power is off at the visible endpoint",
  );
});

test("MTT readout starts with visible retained crystals but zero liquid", async ({ page }) => {
  await page.goto("/mtt_solubilization_readout.html", { waitUntil: "networkidle" });

  const plate = page.locator("#scene-root [data-placement-name='foreground_well_plate_96']");
  const crystalLayer = plate.locator("[data-asset-layer='well_plate_formazan_crystals'] img");
  await expect(plate).toBeVisible();
  await expect(crystalLayer).toBeVisible();
  await expect(plate.locator("[data-subpart-name][data-fill-percent='0']")).toHaveCount(96);
  await expect(page.locator("#scene-root")).not.toHaveAttribute("data-scene-degraded", "true");
});

test("MTT reader shows a blank-corrected result before the dose-response conclusion", async ({
  page,
}) => {
  await walkToStep(page, "mtt_solubilization_readout", "interpret_dose_response");

  const reader = page.locator("#scene-root [data-placement-name='rear_center_plate_reader']");
  const resultsDisplay = page.locator(
    "#scene-root [data-placement-name='center_mtt_results_display']",
  );
  await expect(reader).toBeVisible();
  await expect(resultsDisplay).toBeVisible();
  await expect(resultsDisplay.locator("img")).toBeVisible();
  const readerAnnotations =
    "[data-scene-annotations] " + "[data-annotation-for='rear_center_plate_reader']";
  await expect(
    page.locator(readerAnnotations + "[data-annotation-field='mean_absorbance']"),
  ).toContainText("Selected blank-corrected A: 0.2");
  await expect(
    page.locator(readerAnnotations + "[data-annotation-field='normalized_viability_percent']"),
  ).toContainText("Selected viability: 22% of control");
  await expect(page.locator("[data-current-action]")).toContainText(
    "blank-corrected dose-response display",
  );
  expect(
    await page
      .locator(
        "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='candidate']:visible",
      )
      .count(),
    "the displayed MTT result must be followed by visible interpretation choices",
  ).toBeGreaterThanOrEqual(2);
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);
});

test("SDS image exposes lane identity and capture evidence", async ({ page }) => {
  await walkToStep(page, "sdspage_image_gel", "interpret_ladder_and_sample_lanes");

  const lightbox = page.locator("#scene-root [data-object-name='lightbox']");
  await expect(lightbox).toBeVisible();
  await expect(
    page.locator("#scene-root [data-placement-name='center_gel_image_results_display'] img"),
  ).toBeVisible();
  await expect(lightbox.locator("[data-asset-layer='lightbox_image_bands_visible']")).toBeVisible();
  const imageAnnotations =
    "[data-scene-annotations] " + "[data-annotation-for='rear_center_captured_lightbox']";
  await expect(
    page.locator(imageAnnotations + "[data-annotation-field='lane_pattern']"),
  ).toContainText("Lanes: samples_1_to_3_ladder_5");
  await expect(
    page.locator(imageAnnotations + "[data-annotation-field='archive_metadata_status']"),
  ).toContainText("Archive record: group_a_lane_map_recorded");
  await expect(
    page.locator(imageAnnotations + "[data-annotation-field='image_quality_status']"),
  ).toContainText("Image quality: lanes_sharp_evenly_lit");
  await expect(page.locator("[data-current-step-goal]")).toContainText(
    "Review the visible captured image with the ladder",
  );
  await expect(page.locator("[data-current-action-instruction]")).toContainText(
    "Select the conclusion supported by the visible ladder and lane-resolved bands.",
  );
  const actionHint = page.locator("[data-action-hint]");
  await actionHint.locator("summary").click();
  await expect(actionHint).toHaveAttribute("open", "");
  await expect(actionHint.locator("[data-action-hint-text]")).toHaveText(
    "Compare sample-band positions with the molecular-weight reference and check for extra bands.",
  );
  await expect(page.locator("[data-current-step-goal]")).not.toContainText(
    /24-28 kDa|expected[- ]size|monomer band/i,
  );
  await expect(page.locator("[data-current-action-instruction]")).not.toContainText(
    /24-28 kDa|expected[- ]size|monomer band/i,
  );
  await expect(page.locator("[data-current-action-instruction]")).not.toContainText(
    /24-28 kDa|expected[- ]size|monomer band/i,
  );
  await expect(page.locator("[data-action-hint-text]")).not.toContainText(
    /24-28 kDa|expected[- ]size|monomer band/i,
  );
  expect(
    await page
      .locator(
        "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='candidate']:visible",
      )
      .count(),
    "the lane-resolved image must be followed by visible interpretation choices",
  ).toBeGreaterThanOrEqual(2);
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);

  await page
    .locator("#scene-root [data-placement-name='front_left_gel_conclusion_expected_band']")
    .click();
  await expect(page.locator("[data-interaction-feedback='correct']")).toContainText(
    "lanes 1-3 show the expected 24-28 kDa monomer band",
  );
  await expect(
    lightbox.locator("[data-asset-layer='lightbox_image_molecular_weight_scale']"),
  ).toBeVisible();
  await expect(page.locator("[data-protocol-complete]")).toBeVisible();
});
