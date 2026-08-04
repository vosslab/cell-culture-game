// Browser evidence that the action rail distinguishes concrete ordered actions
// from the pedagogical guided-step counter. The learner uses the normal visible
// scene target; no state is read or mutated through the runtime API.

import { test, expect } from "@playwright/test";

const PROTOCOL = "trypan_blue_counting";

test("action rail advances within the first Trypan Blue guided step", async ({ page }) => {
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });

  const actionRail = page.locator("[data-current-action]");
  const actionProgress = actionRail.locator("[data-current-action-progress]");
  const guidedProgress = page.locator("[data-region='step-counter']");
  const activeTarget = page.locator("#scene-root [data-item-id][data-affordance='active']");

  await expect(actionRail).toBeVisible();
  await expect(actionProgress).toHaveText("Action 1 of 5");
  await expect(guidedProgress).toContainText("0 / 9");
  await expect(activeTarget).toHaveCount(1);
  await expect(activeTarget).toBeVisible();
  const targetBounds = await activeTarget.evaluate((element) => {
    const box = element.getBoundingClientRect();
    return {
      left: box.left,
      top: box.top,
      right: box.right,
      bottom: box.bottom,
      width: box.width,
      height: box.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  });
  expect(
    targetBounds.left,
    "the initial pipette target must be inside the visible viewport",
  ).toBeGreaterThanOrEqual(0);
  expect(
    targetBounds.top,
    "the initial pipette target must be inside the visible viewport",
  ).toBeGreaterThanOrEqual(0);
  expect(
    targetBounds.right,
    "the initial pipette target must be inside the visible viewport",
  ).toBeLessThanOrEqual(targetBounds.viewportWidth);
  expect(
    targetBounds.bottom,
    "the initial pipette target must be inside the visible viewport",
  ).toBeLessThanOrEqual(targetBounds.viewportHeight);
  expect(
    targetBounds.width,
    "the initial pipette target needs a 24px clickable core",
  ).toBeGreaterThanOrEqual(24);
  expect(
    targetBounds.height,
    "the initial pipette target needs a 24px clickable core",
  ).toBeGreaterThanOrEqual(24);

  await activeTarget.click();

  await expect(actionProgress).toHaveText("Action 2 of 5");
  await expect(guidedProgress).toContainText("0 / 9");

  // The active target can redraw after the first click (for example, a
  // cursor-attached pipette state). Re-check the newly active DOM node rather
  // than trusting the launch geometry: the generic focus rule must survive
  // that visual-state transition too.
  const transitionedTarget = page.locator("#scene-root [data-item-id][data-affordance='active']");
  await expect(transitionedTarget).toHaveCount(1);
  const transitionedBounds = await transitionedTarget.evaluate((element) => {
    const box = element.getBoundingClientRect();
    return {
      left: box.left,
      top: box.top,
      right: box.right,
      bottom: box.bottom,
      width: box.width,
      height: box.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  });
  expect(transitionedBounds.left).toBeGreaterThanOrEqual(0);
  expect(transitionedBounds.top).toBeGreaterThanOrEqual(0);
  expect(transitionedBounds.right).toBeLessThanOrEqual(transitionedBounds.viewportWidth);
  expect(transitionedBounds.bottom).toBeLessThanOrEqual(transitionedBounds.viewportHeight);
  expect(transitionedBounds.width).toBeGreaterThanOrEqual(24);
  expect(transitionedBounds.height).toBeGreaterThanOrEqual(24);

  // Fresh-tip selection is now an explicit contamination-control action.
  // Completing it advances to the value-setting action without completing the
  // broader trypan-blue preparation step.
  await transitionedTarget.click();
  await expect(actionProgress).toHaveText("Action 3 of 5");
  await expect(guidedProgress).toContainText("0 / 9");
  await expect(page.locator("[data-adjust-panel]")).toBeVisible();
});
