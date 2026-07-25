// test_framed_layout_m2.spec.ts
//
// Converted from the library-model tests/playwright/test_framed_layout_m2.mjs
// (that .mjs stays in place this phase; a later cleanup phase removes it).
//
// WP-EVID-2 -- M2 framed-layout measurable evidence.
//
// Asserts:
//   1. #scene-root width AND height are each strictly less than the viewport.
//   2. The scene panel contains >= 1 [data-item-id] (scene rendered non-blank).
//   3. The visible action rail projects the current authored prompt and gesture.
//   4. An authored tip is shown only when the protocol actually supplies one.
//   5. A step-counter region [data-region="step-counter"] exists and is visible.
//   6. An outline region [data-region="outline"] exists and is visible.
//   7. A guidance bar [data-region="guidance-bar"] exists and is visible.
//   8. The current step card has data-step-status="current" (distinct styling).
//
// Coordinate-integrity check (WP-FRAME-2):
//   8. Every [data-item-id] bounding box is within #scene-root bounding box
//      (no overflow outside the bounded panel).
//   9. The click target (center) for the first [data-item-id] lands inside
//      #scene-root.
//
// Evidence protocol: sdspage_heat_denature_samples (3 items, heat-block
// scene). Nominated by M0 gap report as the sdspage cluster evidence
// candidate.
//
// Served over HTTP by the playwright.config.ts webServer block (build +
// serve dist/). No per-file server, no chromium import, no process.exit.

import { test, expect } from "@playwright/test";
import type { Locator } from "@playwright/test";

const EVIDENCE_PROTOCOL = "sdspage_heat_denature_samples";

// Asserts a bounding box A is contained within bounding box B (with a small
// pixel tolerance for sub-pixel rounding).
function boxInside(
  inner: { x: number; y: number; width: number; height: number },
  outer: { x: number; y: number; width: number; height: number },
  tolerancePx = 2,
): boolean {
  const leftOk = inner.x >= outer.x - tolerancePx;
  const topOk = inner.y >= outer.y - tolerancePx;
  const rightOk = inner.x + inner.width <= outer.x + outer.width + tolerancePx;
  const bottomOk = inner.y + inner.height <= outer.y + outer.height + tolerancePx;
  return leftOk && topOk && rightOk && bottomOk;
}

async function visibleRegionBox(
  locator: Locator,
  regionName: string,
): Promise<{
  x: number;
  y: number;
  width: number;
  height: number;
}> {
  await expect(locator, `region "${regionName}" must be attached`).toHaveCount(1, {
    timeout: 5000,
  });
  const box = await locator.boundingBox();
  expect(box, `region "${regionName}" must have a bounding box`).not.toBeNull();
  expect(box!.width, `region "${regionName}" must have non-zero width`).toBeGreaterThan(0);
  expect(box!.height, `region "${regionName}" must have non-zero height`).toBeGreaterThan(0);
  return box!;
}

test.describe(`framed layout evidence: ${EVIDENCE_PROTOCOL}`, () => {
  test("scene panel is bounded, chrome regions render, coordinates stay inside the panel", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/${EVIDENCE_PROTOCOL}.html`, { waitUntil: "networkidle" });

    await expect(page.locator("#scene-root [data-item-id]").first()).toBeVisible({ timeout: 8000 });
    // Shell components mount asynchronously (Solid onMount); wait for the
    // guidance text to move off its initial "Loading..." placeholder.
    await expect(page.locator("#guidance-text")).not.toHaveText("Loading...", { timeout: 4000 });

    //============================================
    // Assertion 1: #scene-root is smaller than viewport
    //============================================

    const viewportSize = page.viewportSize();
    expect(viewportSize, "viewport size must be readable").not.toBeNull();
    const vpW = viewportSize!.width;
    const vpH = viewportSize!.height;

    const sceneRootBox = await page.locator("#scene-root").boundingBox();
    expect(sceneRootBox, "#scene-root must have a bounding box").not.toBeNull();
    expect(sceneRootBox!.width, "#scene-root must be bounded, not full-viewport").toBeLessThan(vpW);
    expect(sceneRootBox!.height, "#scene-root must be bounded, not full-viewport").toBeLessThan(
      vpH,
    );

    //============================================
    // Assertion 2: scene panel contains >= 1 [data-item-id]
    //============================================

    const itemCount = await page.locator("#scene-root [data-item-id]").count();
    expect(itemCount, `page errors: ${pageErrors.join(" | ")}`).toBeGreaterThanOrEqual(1);

    //============================================
    // Assertions 3-7: current action and chrome regions visible. The former
    // generic tips bubble is deliberately gone: a tip is only rendered when a
    // protocol author supplied one. This evidence protocol has no authored tip,
    // so the shell must not invent generic coaching copy.
    //============================================

    const actionRail = page.locator("[data-current-action]").first();
    await visibleRegionBox(actionRail, "current-action");
    await expect(actionRail.locator("#guidance-text")).toBeVisible();
    await expect(actionRail.locator(".action-rail-prompt")).toHaveText(/\S/);
    await expect(actionRail.locator(".action-rail-cue")).toHaveText(/\S/);
    await expect(actionRail.locator("[data-authored-tip]")).toHaveCount(0);
    await visibleRegionBox(page.locator('[data-region="step-counter"]').first(), "step-counter");
    await visibleRegionBox(page.locator('[data-region="outline"]').first(), "outline");
    await visibleRegionBox(page.locator('[data-region="guidance-bar"]').first(), "guidance-bar");

    //============================================
    // Assertion 8: current step card has data-step-status="current"
    //============================================

    await expect(page.locator('[data-step-status="current"]').first()).toBeVisible();

    //============================================
    // Assertion 8: all [data-item-id] bboxes within #scene-root
    // (coordinate-integrity / WP-FRAME-2)
    //============================================

    const itemIds = await page
      .locator("#scene-root [data-item-id]")
      .evaluateAll((els) => els.map((el) => el.getAttribute("data-item-id")));

    for (const itemId of itemIds) {
      const itemBox = await page.locator(`[data-item-id="${itemId}"]`).first().boundingBox();
      expect(itemBox, `item "${itemId}" must have a bounding box`).not.toBeNull();
      expect(
        boxInside(itemBox!, sceneRootBox!),
        `item "${itemId}" bounding box must stay inside #scene-root`,
      ).toBe(true);
    }

    //============================================
    // Assertion 9: click target for first item lands inside #scene-root
    // (coordinate-integrity / WP-FRAME-2)
    //============================================

    expect(
      itemIds.length,
      "at least one item must be present for the click-target check",
    ).toBeGreaterThan(0);
    const firstId = itemIds[0]!;
    const firstBox = await page.locator(`[data-item-id="${firstId}"]`).first().boundingBox();
    expect(firstBox, `item "${firstId}" must have a bounding box`).not.toBeNull();

    const clickX = firstBox!.x + firstBox!.width / 2;
    const clickY = firstBox!.y + firstBox!.height / 2;
    const insideScene =
      clickX >= sceneRootBox!.x &&
      clickX <= sceneRootBox!.x + sceneRootBox!.width &&
      clickY >= sceneRootBox!.y &&
      clickY <= sceneRootBox!.y + sceneRootBox!.height;
    expect(insideScene, `click center for "${firstId}" must land inside #scene-root`).toBe(true);

    await page.screenshot({
      path: `test-results/m2_framed_layout_${EVIDENCE_PROTOCOL}.png`,
      fullPage: false,
    });
  });
});
