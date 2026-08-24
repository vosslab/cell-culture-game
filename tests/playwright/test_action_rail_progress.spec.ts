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
  const activeTarget = page.locator(
    [
      "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
      "#scene-root [data-subpart-hit][data-subpart-affordance='active']",
    ].join(", "),
  );
  const actionInstruction = actionRail.locator("[data-current-action-instruction]");
  const guidanceText = page.locator("#guidance-text");
  const stepGoal = page.locator("[data-current-step-goal]");
  const hint = page.locator("[data-action-hint]");
  const hintText = hint.locator("[data-action-hint-text]");

  async function expectAction(
    ordinal: number,
    target: string,
    gesture: string,
    previousMessage: string,
  ): Promise<string> {
    await expect(actionProgress).toHaveText(`Action ${ordinal} of 5`);
    await expect(actionRail).toHaveAttribute("data-action-target", target);
    await expect(actionRail).toHaveAttribute("data-action-gesture", gesture);
    await expect(guidanceText).not.toHaveText(previousMessage);
    const message = (await guidanceText.textContent()) ?? "";
    expect(message.trim(), `action ${ordinal} must announce a live instruction`).not.toBe("");
    if (gesture !== "select") {
      await expect(actionInstruction).toContainText(/Target:\s*\S+/i);
    }
    return message;
  }

  async function expectVisibleTarget(target: string): Promise<void> {
    await expect(activeTarget).toHaveCount(1);
    await expect(activeTarget).toBeVisible();
    await expect(activeTarget).toHaveAttribute("data-item-id", target);
  }

  await expect(actionRail).toBeVisible();
  await expect(actionProgress).toHaveText("Action 1 of 5");
  await expect(actionInstruction).toHaveAttribute("role", "status");
  await expect(actionInstruction).toHaveAttribute("aria-live", "polite");
  await expect(actionInstruction).toHaveAttribute("aria-atomic", "true");
  await expect(actionInstruction).toContainText("Target: P20 micropipette");
  await expect(guidanceText).toBeVisible();
  await expect(actionInstruction).toHaveAttribute("data-current-action-instruction", "");
  const initialActionMessage = await guidanceText.textContent();
  await expect(stepGoal).toBeVisible();
  await expect(stepGoal).toContainText("Step goal");
  const initialStepGoal = await stepGoal.textContent();
  await expect(hint).toHaveCount(1);
  await expect(hint.locator("summary")).toHaveText("Need a hint?");
  await expect(hintText).toBeAttached();
  const initialHint = await hintText.textContent();
  await hint.locator("summary").click();
  await expect(hint).toHaveAttribute("open", "");
  await expect(hintText).toBeVisible();
  await hint.locator("summary").press("Enter");
  await expect(hint).not.toHaveAttribute("open");
  await hint.locator("summary").press("Space");
  await expect(hint).toHaveAttribute("open", "");
  await expect(hintText).toBeVisible();
  const hintFocus = await hint.locator("summary").evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      focused: document.activeElement === element,
      focusVisible: element.matches(":focus-visible"),
      outlineStyle: style.outlineStyle,
      outlineWidth: Number.parseFloat(style.outlineWidth),
    };
  });
  expect(hintFocus.focused).toBe(true);
  expect(hintFocus.focusVisible).toBe(true);
  expect(hintFocus.outlineStyle).not.toBe("none");
  expect(hintFocus.outlineWidth).toBeGreaterThanOrEqual(3);
  await expect(guidedProgress).toContainText("0 / 9");
  await expectVisibleTarget("right_p20_micropipette");
  const wrongWholeObject = page.locator(
    "#scene-root [data-interaction-envelope][data-item-id='left_tip_box']",
  );
  await expect(
    wrongWholeObject,
    "a visible wrong whole-object action remains reachable through its own envelope",
  ).toHaveCount(1);
  await expect(wrongWholeObject).toHaveAttribute("data-interaction-envelope-kind", "none");
  await wrongWholeObject.click();
  await expect(actionRail).toHaveAttribute("data-action-target", "right_p20_micropipette");
  await expect(page.locator("[data-action-recovery]")).toBeVisible();
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
    "the initial pipette target needs a 44px clickable core",
  ).toBeGreaterThanOrEqual(44);
  expect(
    targetBounds.height,
    "the initial pipette target needs a 44px clickable core",
  ).toBeGreaterThanOrEqual(44);

  await activeTarget.click();

  const secondActionMessage = await expectAction(
    2,
    "left_tip_box",
    "click",
    initialActionMessage ?? "",
  );
  await expect(stepGoal).toHaveText(initialStepGoal ?? "");
  await expect(hint).toHaveAttribute("open", "");
  await expect(hintText).toBeVisible();
  await expect(hintText).not.toHaveText(initialHint ?? "");
  await expect(guidedProgress).toContainText("0 / 9");

  await expectVisibleTarget("left_tip_box");
  await activeTarget.click();
  const thirdActionMessage = await expectAction(
    3,
    "right_p20_micropipette",
    "adjust",
    secondActionMessage,
  );
  await expect(stepGoal).toHaveText(initialStepGoal ?? "");
  await expect(guidedProgress).toContainText("0 / 9");
  await expect(page.locator("[data-adjust-panel]")).toBeVisible();

  const adjustInput = page.locator("[data-adjust-input]");
  await expect(adjustInput).toBeVisible();
  await expect(adjustInput).toHaveAttribute("data-adjust-target", "right_p20_micropipette");
  await adjustInput.fill("10");
  await page.locator("[data-adjust-commit]").click();

  const fourthActionMessage = await expectAction(
    4,
    "rear_trypan_blue_tube",
    "click",
    thirdActionMessage,
  );
  await expect(stepGoal).toHaveText(initialStepGoal ?? "");
  await expect(guidedProgress).toContainText("0 / 9");
  await expect(hint).toHaveAttribute("open", "");
  await expect(hintText).toBeVisible();

  await expectVisibleTarget("rear_trypan_blue_tube");
  await activeTarget.click();
  const fifthActionMessage = await expectAction(
    5,
    "right_hemocytometer_slide.diamond",
    "click",
    fourthActionMessage,
  );
  await expect(stepGoal).toHaveText(initialStepGoal ?? "");
  await expect(guidedProgress).toContainText("0 / 9");

  await expectVisibleTarget("right_hemocytometer_slide.diamond");
  await expect(activeTarget).toHaveAttribute("data-subpart-affordance", "active");
  await activeTarget.click();

  await expect(actionProgress).toHaveText("Action 1 of 5");
  await expect(actionRail).toHaveAttribute("data-action-target", "left_tip_box");
  await expect(actionRail).toHaveAttribute("data-action-gesture", "click");
  await expect(guidanceText).not.toHaveText(fifthActionMessage);
  await expect(stepGoal).toContainText("Step goal");
  await expect(stepGoal).not.toHaveText(initialStepGoal ?? "");
  await expect(guidedProgress).toContainText("1 / 9");
});
