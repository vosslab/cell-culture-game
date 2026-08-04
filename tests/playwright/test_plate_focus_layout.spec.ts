// tests/playwright/test_plate_focus_layout.spec.ts
//
// Behavioral acceptance for the cell-seeding plate-focused teaching scene.
// The test measures real rendered DOM boxes rather than authored coordinates.
// Selector contract: SceneItem emits data-placement-name and data-object-name.

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

const PROTOCOL_PAGE = "/cell_seeding_plate_setup.html";
const PLATE_SELECTOR =
  "#scene-root [data-placement-name='foreground_well_plate_96'][data-object-name='well_plate_96']";
const INCUBATOR_SELECTOR =
  "#scene-root [data-placement-name='rear_right_incubator'][data-object-name='incubator']";

const VIEWPORTS = [
  { name: "desktop", width: 1920, height: 1080 },
  { name: "narrow_tablet", width: 800, height: 900 },
];

interface SceneMeasurement {
  rootWidth: number;
  rootCenterX: number;
  plateCenterX: number;
  plateTop: number;
  plateWidth: number;
  incubatorBottom: number;
  incubatorWidth: number;
}

async function measureTeachingComposition(page: Page): Promise<SceneMeasurement> {
  return page.evaluate(
    ({ plateSelector, incubatorSelector }): SceneMeasurement => {
      const root = document.querySelector("#scene-root");
      const plate = document.querySelector(plateSelector);
      const incubator = document.querySelector(incubatorSelector);
      if (root === null || plate === null || incubator === null) {
        throw new Error("cell-seeding teaching composition is missing a required scene item");
      }

      const rootBox = root.getBoundingClientRect();
      const plateBox = plate.getBoundingClientRect();
      const incubatorBox = incubator.getBoundingClientRect();
      return {
        rootWidth: rootBox.width,
        rootCenterX: rootBox.x + rootBox.width / 2,
        plateCenterX: plateBox.x + plateBox.width / 2,
        plateTop: plateBox.y,
        plateWidth: plateBox.width,
        incubatorBottom: incubatorBox.y + incubatorBox.height,
        incubatorWidth: incubatorBox.width,
      };
    },
    { plateSelector: PLATE_SELECTOR, incubatorSelector: INCUBATOR_SELECTOR },
  );
}

test.describe("cell-seeding plate-focused teaching composition", () => {
  for (const viewport of VIEWPORTS) {
    test(`${viewport.name}: plate is centered, foregrounded, and dominant`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(PROTOCOL_PAGE, { waitUntil: "networkidle" });
      const calculationChoice = page.locator(
        "#scene-root [data-object-name='calculation_2_8_ml'][data-affordance='candidate']",
      );
      await expect(calculationChoice).toHaveCount(1);
      await calculationChoice.click();
      await expect(page.locator(PLATE_SELECTOR)).toBeVisible();
      await expect(page.locator(INCUBATOR_SELECTOR)).toBeVisible();

      const measured = await measureTeachingComposition(page);
      const centerOffset = Math.abs(measured.plateCenterX - measured.rootCenterX);
      expect(centerOffset, "plate center stays near the scene center").toBeLessThanOrEqual(
        measured.rootWidth * 0.1,
      );
      expect(
        measured.plateTop,
        "plate remains below secondary incubator context",
      ).toBeGreaterThanOrEqual(measured.incubatorBottom);
      expect(
        measured.plateWidth,
        "plate occupies a legible share of the scene",
      ).toBeGreaterThanOrEqual(measured.rootWidth * 0.255);
      expect(
        measured.plateWidth,
        "plate remains dominant over the incubator",
      ).toBeGreaterThanOrEqual(measured.incubatorWidth * 1.5);
    });
  }
});
