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
} from "./e2e/walker_helpers.mjs";

interface WalkReport {
  summary: { totalClicks: number };
  info: (message: string) => void;
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
  };
}

async function visibleActionValue(page: Page): Promise<string> {
  const action = page.locator("[data-current-action]").first();
  await expect(action).toBeVisible();
  const value = await action.getAttribute("data-action-value");
  expect(value, "an adjust action must expose its required visible value").not.toBeNull();
  return value!;
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
        `${protocol} did not mount its learner runtime: ${pageErrors.join(" | ") || "no page error captured"}`,
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
  const candidates = page.locator("#scene-root [data-affordance='candidate']:visible");
  expect(
    await candidates.count(),
    "both scientific choices must be visibly offered",
  ).toBeGreaterThanOrEqual(2);
  await expect(page.locator("[data-current-action]")).toContainText(
    "Choose from the blue outlined lab items.",
  );

  // The displayed 92.5% viability clears the stated gate, so Recount is the
  // scientifically wrong visible alternative. This is a real click, not a
  // synthetic rejection, and the protocol must remain at the decision.
  await page.locator("#scene-root [data-item-id='viability_recount_choice']").click();
  const viabilityRecovery = page.locator("[data-action-recovery]");
  await expect(viabilityRecovery).toContainText("You chose: Stop and recount");
  await expect(viabilityRecovery).toContainText("Correct: Proceed: viability above 90%");
  await expect(viabilityRecovery).toContainText(
    "Compare the displayed viability percentage with the stated threshold before deciding whether to proceed or recount.",
  );
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);

  await page.locator("#scene-root [data-item-id='viability_proceed_choice']").click();
  await expect(page.locator("[data-protocol-complete]")).toBeVisible();
  await expect(page.locator("[data-interaction-feedback='correct']")).toContainText(
    "The displayed viability clears the stated gate",
  );
});

test("SDS-PAGE endpoint requires a stop decision before switching the supply off", async ({
  page,
}) => {
  await walkToStep(page, "sdspage_run_electrophoresis", "stop_at_tracking_dye_endpoint");

  await expect(
    page.locator("#scene-root [data-placement-name='center_electrophoresis_endpoint_display'] img"),
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
    "Do not continue this run: the visible dye front is already near the bottom of the gel. Select Stop now, then switch the supply off.",
  );
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);

  await page.locator("#scene-root [data-placement-name='front_left_endpoint_stop_now']").click();
  await expect(page.locator("[data-current-action]")).toContainText("Power Supply");
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
  await expect(reader.locator("[data-overlay-field='mean_absorbance']")).toHaveText(
    "Selected blank-corrected A: 0.2",
  );
  await expect(reader.locator("[data-overlay-field='normalized_viability_percent']")).toHaveText(
    "Selected viability: 22% of control",
  );
  await expect(page.locator("[data-current-action]")).toContainText(
    "blank-corrected dose-response display",
  );
  expect(
    await page.locator("#scene-root [data-affordance='candidate']:visible").count(),
    "the displayed MTT result must be followed by visible interpretation choices",
  ).toBeGreaterThanOrEqual(2);
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);
});

test("SDS image exposes lane identity, capture metadata, and quality before interpretation", async ({
  page,
}) => {
  await walkToStep(page, "sdspage_image_gel", "interpret_ladder_and_sample_lanes");

  const lightbox = page.locator("#scene-root [data-object-name='lightbox']");
  await expect(lightbox).toBeVisible();
  await expect(
    page.locator("#scene-root [data-placement-name='center_gel_image_results_display'] img"),
  ).toBeVisible();
  await expect(lightbox.locator("[data-asset-layer='lightbox_image_bands_visible']")).toBeVisible();
  await expect(lightbox.locator("[data-overlay-field='lane_pattern']")).toHaveText(
    "Lanes: samples_1_to_3_ladder_5",
  );
  await expect(lightbox.locator("[data-overlay-field='archive_metadata_status']")).toHaveText(
    "Archive record: group_a_lane_map_recorded",
  );
  await expect(lightbox.locator("[data-overlay-field='image_quality_status']")).toHaveText(
    "Image quality: lanes_sharp_evenly_lit",
  );
  await expect(page.locator("[data-current-action]")).toContainText(
    "24-28 kDa miraculin monomer band",
  );
  expect(
    await page.locator("#scene-root [data-affordance='candidate']:visible").count(),
    "the lane-resolved image must be followed by visible interpretation choices",
  ).toBeGreaterThanOrEqual(2);
  await expect(page.locator("[data-protocol-complete]")).toHaveCount(0);
});
