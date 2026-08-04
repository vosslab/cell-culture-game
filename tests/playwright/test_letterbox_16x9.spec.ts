// test_letterbox_16x9.spec.ts
//
// Converted from the library-model tests/playwright/test_letterbox_16x9.mjs
// (that .mjs stays in place this phase; a later cleanup phase removes it).
//
// WP-PRECOMP2 evidence: the protocol host renders the scene inside an EXACT
// 16:9 letterboxed frame, and resizing the browser changes ONLY the
// letterbox bars / uniform scale -- never the scene-internal layout.
//
// What this spec proves against the built dist/ (served by the
// playwright.config.ts webServer block):
//   1. #scene-root has an exact 16:9 aspect ratio (width/height == 16/9
//      within a 0.5% tolerance) at every tested viewport aspect ratio,
//      including panels wider-than-16:9 and taller-than-16:9.
//   2. The scene-internal layout is identical across viewports: each
//      rendered item's center, expressed as a PERCENT of the #scene-root
//      frame, matches the canonical 16:9 viewport within a small tolerance.
//      Only the frame's pixel size and the surrounding neutral bars change.
//
// The production path loads PRECOMPUTED_LAYOUT (no ?layout=runtime), so
// this also exercises the precomputed-consume switch end to end.
//
// Selector contract:
//   - #scene-root                    src/scene_runtime/renderer/scene_root.tsx
//   - [data-item-id] scene items     src/scene_runtime/renderer/scene_item.tsx

/// <reference types="node" />

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

// mtt_reagent_prep's entry scene (mtt_reagent_prep_bench_workspace) is
// populated, so it renders multiple data-item-id objects to measure.
const PROTOCOL_PAGE = "mtt_reagent_prep.html";

// Viewports spanning three panel-aspect regimes. The grid/header/guidance-bar
// chrome makes the scene panel's own aspect differ from the window aspect, so
// these deliberately bracket both sides of 16:9 to exercise both pillarbox
// (wide) and letterbox (tall) regimes.
const VIEWPORTS = [
  { name: "canonical_1920x1080", width: 1920, height: 1080 }, // ~16:9 window
  { name: "wide_2400x1000", width: 2400, height: 1000 }, // very wide
  { name: "tall_1100x1200", width: 1100, height: 1200 }, // tall / narrow
  { name: "small_1280x800", width: 1280, height: 800 }, // 16:10
];

const TARGET_ASPECT = 16 / 9;
// Aspect tolerance: 0.5% of the target ratio. Sub-pixel rounding of
// width/height from getBoundingClientRect keeps the measured ratio within
// this band.
const ASPECT_TOLERANCE = TARGET_ASPECT * 0.005;
// Scene-percent center tolerance across viewports, in percent of the frame.
// Pure CSS letterboxing should reproduce identical percent centers; this
// small band only absorbs sub-pixel measurement noise at different pixel
// sizes.
const CENTER_PCT_TOLERANCE = 0.6;

interface ItemCenter {
  xPct: number;
  yPct: number;
}

interface FrameMeasurement {
  width: number;
  height: number;
  items: Record<string, ItemCenter>;
}

// Reads the #scene-root rect plus each data-item-id center expressed as a
// percent of the scene-root frame. Percent centers are the scene-percent
// coordinate space, invariant under pure letterboxing.
async function measure(page: Page): Promise<FrameMeasurement> {
  return page.evaluate((): FrameMeasurement => {
    const root = document.querySelector("#scene-root");
    if (!root) throw new Error("#scene-root not found");
    const r = root.getBoundingClientRect();
    const items: Record<string, ItemCenter> = {};
    for (const el of document.querySelectorAll("#scene-root [data-item-id]")) {
      const b = el.getBoundingClientRect();
      const cx = b.x + b.width / 2;
      const cy = b.y + b.height / 2;
      const itemId = el.getAttribute("data-item-id");
      if (itemId === null) continue;
      items[itemId] = {
        xPct: ((cx - r.x) / r.width) * 100,
        yPct: ((cy - r.y) / r.height) * 100,
      };
    }
    return { width: r.width, height: r.height, items };
  });
}

test.describe("protocol host: exact 16:9 letterbox frame", () => {
  for (const vp of VIEWPORTS) {
    test(`${vp.name}: #scene-root is exact 16:9`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(`/${PROTOCOL_PAGE}`, { waitUntil: "networkidle" });
      await expect(page.locator("#scene-root [data-item-id]").first()).toBeVisible();

      const m = await measure(page);
      const ratio = m.width / m.height;
      expect(
        Math.abs(ratio - TARGET_ASPECT),
        `${vp.name}: frame ${m.width.toFixed(1)}x${m.height.toFixed(1)} ratio=${ratio.toFixed(4)}`,
      ).toBeLessThanOrEqual(ASPECT_TOLERANCE);

      await page.screenshot({
        path: `test-results/letterbox_16x9/${vp.name}.png`,
        fullPage: false,
      });
    });
  }

  test("scene-internal layout is invariant across viewports (only bars/scale change)", async ({
    page,
  }) => {
    // Re-measure every viewport in this single test so the comparison does
    // not depend on ordering/state carried between the per-viewport tests
    // above (each Playwright test gets a fresh page/context).
    const remeasured: { vp: string; frame: FrameMeasurement }[] = [];
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(`/${PROTOCOL_PAGE}`, { waitUntil: "networkidle" });
      await expect(page.locator("#scene-root [data-item-id]").first()).toBeVisible();
      remeasured.push({ vp: vp.name, frame: await measure(page) });
    }

    const canonical = remeasured.find((x) => x.vp === "canonical_1920x1080");
    expect(
      canonical,
      "canonical_1920x1080 viewport must produce a measurement",
    ).not.toBeUndefined();

    for (const meas of remeasured) {
      if (meas.vp === canonical!.vp) continue;
      for (const [id, c] of Object.entries(canonical!.frame.items)) {
        const other = meas.frame.items[id];
        expect(
          other,
          `${meas.vp}: item ${id} present in canonical but missing here`,
        ).not.toBeUndefined();
        const dx = Math.abs(other!.xPct - c.xPct);
        const dy = Math.abs(other!.yPct - c.yPct);
        expect(dx, `${meas.vp}: item ${id} x center moved`).toBeLessThanOrEqual(
          CENTER_PCT_TOLERANCE,
        );
        expect(dy, `${meas.vp}: item ${id} y center moved`).toBeLessThanOrEqual(
          CENTER_PCT_TOLERANCE,
        );
      }
    }
  });
});
