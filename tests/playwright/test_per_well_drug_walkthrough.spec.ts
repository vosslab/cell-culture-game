// Browser evidence that the first authored drug-treatment step can be completed
// through learner-visible controls and paints its intended 96-well row.
//
// The values and row expectations below are the actual teaching content in
// content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml.
// The test never reads or writes internal game state: each click follows the
// visible active affordance, and each value is entered through a visible control.

import { test, expect, type Page } from "@playwright/test";
import { PROTOCOL_MATERIALS } from "../../generated/protocol_materials.js";

const PROTOCOL = "plate_drug_treatment_drug_addition";
const PLATE = "well_plate_96";
const ROW_B = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11", "B12"];
const UNTARGETED_CONTROLS = ["A1", "C1", "H12", "D6"];
const CARBOPLATIN_COLOR = PROTOCOL_MATERIALS[PROTOCOL]?.carboplatin?.display_color;

interface WellFill {
  fill: string | null;
  material: string | null;
}

async function readWellFill(page: Page, subpart: string): Promise<WellFill> {
  const shape = page.locator(`[data-subpart-overlay='${PLATE}'] [data-subpart-name='${subpart}']`);
  return shape.evaluate((element): WellFill => ({
    fill: element.getAttribute("fill"),
    material: element.getAttribute("data-material-name"),
  }));
}

async function clickActiveSceneTarget(page: Page): Promise<void> {
  const activeTarget = page.locator(
    [
      "#scene-root [data-item-id][data-affordance='active']",
      "#scene-root [data-item-id][data-subpart-affordance='active']",
    ].join(", "),
  );
  await expect(
    activeTarget,
    "a directed click interaction must expose exactly one visible active target",
  ).toHaveCount(1);
  await expect(activeTarget).toBeVisible();
  await activeTarget.click();
}

test("per-well drug walkthrough: visible row-B dispensing paints carboplatin", async ({ page }) => {
  expect(
    CARBOPLATIN_COLOR,
    "carboplatin must be registered for the authored protocol",
  ).toBeTruthy();
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });
  await page.screenshot({ path: "test-results/per_well_drug_walkthrough_00_before.png" });

  const advertisedSubpartTargets = page.locator("#scene-root [data-subpart-hit][data-item-id]");
  await expect(
    advertisedSubpartTargets,
    "inactive subpart geometry must not advertise delegated click targets",
  ).toHaveCount(0);

  // The authored first interaction changes to the plate workspace.
  await clickActiveSceneTarget(page);
  const adjustInput = page.locator("[data-adjust-input]");
  await expect(adjustInput).toBeVisible();
  await adjustInput.fill("5");
  await page.locator("[data-adjust-commit]").click();
  await expect(page.locator("[data-adjust-panel]")).toBeHidden();

  // The next authored interaction selects the first dilution tube. Its
  // subpart hit surface now becomes a real, visible target.
  await expect(
    advertisedSubpartTargets,
    "an active structured-object interaction must expose its subpart targets",
  ).not.toHaveCount(0);
  await clickActiveSceneTarget(page);
  await expect(
    advertisedSubpartTargets,
    "subpart targets must stop advertising click identity after the interaction",
  ).toHaveCount(0);

  // Each repeated learner click on the visible plate advances one authored
  // row-B dispense. Wait for that well's rendered material, never elapsed time.
  for (const well of ROW_B) {
    await clickActiveSceneTarget(page);
    const shape = page.locator(`[data-subpart-overlay='${PLATE}'] [data-subpart-name='${well}']`);
    await expect(shape).toHaveAttribute("fill", CARBOPLATIN_COLOR!);
    await expect(shape).toHaveAttribute("data-material-name", "carboplatin");
  }

  await page.screenshot({ path: "test-results/per_well_drug_walkthrough_01_after.png" });

  for (const well of UNTARGETED_CONTROLS) {
    const fill = await readWellFill(page, well);
    expect(fill.fill, `${well} must remain unfilled by row-B dispensing`).toBe("transparent");
    expect(fill.material, `${well} must not acquire carboplatin`).not.toBe("carboplatin");
  }
  expect(pageErrors, "no uncaught page errors during visible dispensing").toEqual([]);
});
