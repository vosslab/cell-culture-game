// Browser acceptance for the in-flow type and adjust control hosts.
//
// The Trypan Blue protocol reaches an authored `adjust` action after the learner
// visibly selects the P20 and mounts a fresh tip. The correct 10 microliter set
// point is part of that protocol's teaching content; the test drives it only
// through the learner-visible numeric input.

import { test, expect, type Page } from "@playwright/test";

const PROTOCOL = "trypan_blue_counting";
const TEACHING_SET_POINT = "10";

async function openFirstAdjustControl(page: Page): Promise<void> {
  const activeTarget = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
  );
  await expect(activeTarget).toHaveCount(1);
  await activeTarget.click();
  await expect(activeTarget).toHaveCount(1);
  await activeTarget.click();
}

interface PanelLayout {
  panelPosition: string;
  panelInsideControls: boolean;
  sceneOverlapsPanel: boolean;
  guidanceOverlapsPanel: boolean;
  outlineOverlapsPanel: boolean;
  bodyOverflowsHorizontally: boolean;
}

async function readPanelLayout(page: Page): Promise<PanelLayout> {
  return page.evaluate((): PanelLayout => {
    function boxesOverlap(first: DOMRect, second: DOMRect): boolean {
      return (
        first.left < second.right &&
        first.right > second.left &&
        first.top < second.bottom &&
        first.bottom > second.top
      );
    }

    const panel = document.querySelector("[data-adjust-panel]");
    const controls = document.querySelector('[data-region="interaction-controls"]');
    const scene = document.querySelector('[data-region="scene-panel"]');
    const guidance = document.querySelector('[data-region="guidance-bar"]');
    const outline = document.querySelector('[data-region="outline"]');
    if (
      !(panel instanceof HTMLElement) ||
      !(controls instanceof HTMLElement) ||
      !(scene instanceof HTMLElement) ||
      !(guidance instanceof HTMLElement) ||
      !(outline instanceof HTMLElement)
    ) {
      throw new Error("in-flow control acceptance requires all protocol regions");
    }

    const panelBox = panel.getBoundingClientRect();
    const controlsBox = controls.getBoundingClientRect();
    return {
      panelPosition: window.getComputedStyle(panel).position,
      panelInsideControls:
        panelBox.left >= controlsBox.left &&
        panelBox.right <= controlsBox.right &&
        panelBox.top >= controlsBox.top &&
        panelBox.bottom <= controlsBox.bottom,
      sceneOverlapsPanel: boxesOverlap(scene.getBoundingClientRect(), panelBox),
      guidanceOverlapsPanel: boxesOverlap(guidance.getBoundingClientRect(), panelBox),
      outlineOverlapsPanel: boxesOverlap(outline.getBoundingClientRect(), panelBox),
      bodyOverflowsHorizontally: document.documentElement.scrollWidth > window.innerWidth,
    };
  });
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "narrow", width: 820, height: 928 },
]) {
  test(`${viewport.name}: active adjust control stays in flow and recovers by keyboard`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });
    await openFirstAdjustControl(page);

    const controls = page.locator('[data-region="interaction-controls"]');
    const adjustPanel = page.locator("[data-adjust-panel]");
    const input = page.locator("[data-adjust-input]");

    await expect(controls).toBeVisible();
    await expect(adjustPanel).toBeVisible();
    await expect(input).toBeVisible();
    await expect(page.locator("#type-input-root")).toBeEmpty();

    const layout = await readPanelLayout(page);
    expect(layout.panelPosition).not.toBe("fixed");
    expect(layout.panelInsideControls).toBe(true);
    expect(layout.sceneOverlapsPanel).toBe(false);
    expect(layout.guidanceOverlapsPanel).toBe(false);
    expect(layout.outlineOverlapsPanel).toBe(false);
    expect(layout.bodyOverflowsHorizontally).toBe(false);

    await input.fill("1");
    await input.press("Enter");
    await expect(page.locator("[data-adjust-reject-message]")).toBeVisible();
    await expect(input).toHaveAttribute("aria-invalid", "true");

    await input.fill(TEACHING_SET_POINT);
    await input.press("Enter");
    await expect(adjustPanel).toBeHidden();
  });
}

test("shell=off retains a functional in-flow adjust root", async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 928 });
  await page.goto(`/${PROTOCOL}.html?shell=off`, { waitUntil: "networkidle" });
  await openFirstAdjustControl(page);

  await expect(page.locator("#shell-root")).toBeEmpty();
  await expect(page.locator("#adjust-editor-root")).toBeAttached();
  const input = page.locator("[data-adjust-input]");
  await expect(input).toBeVisible();

  await input.fill(TEACHING_SET_POINT);
  await input.press("Enter");
  await expect(page.locator("[data-adjust-panel]")).toBeHidden();
});
