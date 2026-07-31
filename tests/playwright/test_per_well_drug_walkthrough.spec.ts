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
  const activeSurfaces = page.locator(
    [
      "#scene-root [data-item-id][data-affordance='active']",
      "#scene-root [data-item-id][data-subpart-affordance='active']",
    ].join(", "),
  );
  const activeIdentities = await activeSurfaces.evaluateAll((elements) => [
    ...new Set(elements.map((element) => element.getAttribute("data-item-id"))),
  ]);
  expect(
    activeIdentities,
    "a directed click interaction must expose exactly one active semantic target",
  ).toHaveLength(1);
  const activeTarget = activeSurfaces.first();
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
  const untargetedBefore = new Map<string, WellFill>();
  for (const well of UNTARGETED_CONTROLS) {
    untargetedBefore.set(well, await readWellFill(page, well));
  }

  const advertisedSubpartTargets = page.locator("#scene-root [data-subpart-hit][data-item-id]");
  await expect(
    advertisedSubpartTargets,
    "inactive subpart geometry must not advertise delegated click targets",
  ).toHaveCount(0);

  // The authored first interaction changes to the plate workspace. Read the
  // next setpoint from the same visible action rail the learner sees instead of
  // duplicating protocol internals in the browser driver.
  await clickActiveSceneTarget(page);
  const adjustRail = page.locator(
    "[data-current-action][data-action-gesture='adjust'][data-action-value]",
  );
  await expect(adjustRail).toBeVisible();
  const visibleSetpoint = await adjustRail.getAttribute("data-action-value");
  expect(visibleSetpoint, "the action rail must visibly identify the 60 µL row draw").toBe("60");
  const adjustInput = page.locator("[data-adjust-input]");
  await expect(adjustInput).toBeVisible();
  await adjustInput.fill(visibleSetpoint!);
  await page.locator("[data-adjust-commit]").click();
  await expect(page.locator("[data-adjust-panel]")).toBeHidden();

  // The next authored interaction selects the first dilution tube. Its
  // subpart hit surface now becomes a real, visible target.
  await expect(
    advertisedSubpartTargets,
    "an active structured-object interaction must expose its subpart targets",
  ).not.toHaveCount(0);

  // A directed dotted target focuses its one real tube, but every sibling tube
  // stays addressable through the normal delegated resolver. That lets a wrong
  // learner click reach the ordinary step-machine rejection path instead of
  // disappearing into an inert overlay. The focused original rack scales its
  // declared tube geometry to a 24px usable core without inventing a second
  // representation or overlapping invisible sibling targets.
  const exactTargetReport = await advertisedSubpartTargets.evaluateAll((elements) =>
    elements.map((element) => {
      const box = element.getBoundingClientRect();
      return {
        target: element.getAttribute("data-item-id"),
        affordance: element.getAttribute("data-subpart-affordance"),
        width: box.width,
        height: box.height,
        hitStrokeWidth: ((): string | null => {
          const pad = element.querySelector(".subpart-hit-target");
          return pad === null ? null : getComputedStyle(pad).strokeWidth;
        })(),
        hitVectorEffect: ((): string | null => {
          const pad = element.querySelector(".subpart-hit-target");
          return pad === null ? null : getComputedStyle(pad).vectorEffect;
        })(),
        hitPointerEvents: ((): string | null => {
          const pad = element.querySelector(".subpart-hit-target");
          return pad === null ? null : getComputedStyle(pad).pointerEvents;
        })(),
        centerHitTarget:
          document
            .elementFromPoint(box.left + box.width / 2, box.top + box.height / 2)
            ?.closest("[data-item-id]")
            ?.getAttribute("data-item-id") ?? null,
      };
    }),
  );
  expect(
    exactTargetReport.length,
    "the rack must expose more than the directed tube",
  ).toBeGreaterThan(1);
  const activeExact = exactTargetReport.filter((entry) => entry.affordance === "active");
  expect(activeExact, "only the directed dotted target is painted active").toHaveLength(1);
  const activeExactTarget = activeExact[0]?.target;
  expect(activeExactTarget, "the directed exact target needs a delegated identity").toBeTruthy();
  const exactPlacement = activeExactTarget?.slice(0, activeExactTarget.lastIndexOf("."));
  expect(
    exactPlacement,
    "the exact target must carry a placement-qualified subpart name",
  ).toBeTruthy();
  expect(
    exactTargetReport.filter(
      (entry) => entry.affordance === "active" || entry.affordance === "candidate",
    ),
    "a directed click must not paint a sibling as active",
  ).toHaveLength(1);
  for (const entry of exactTargetReport) {
    expect(entry.target, "each rendered sibling must retain its exact click identity").toMatch(
      new RegExp(`^${exactPlacement}\\.[^.]+$`, "u"),
    );
    expect(entry.width, `${entry.target} must have a 24px-wide usable core`).toBeGreaterThanOrEqual(
      24,
    );
    expect(
      entry.height,
      `${entry.target} must have a 24px-high usable core`,
    ).toBeGreaterThanOrEqual(24);
    expect(
      entry.hitStrokeWidth,
      `${entry.target} must not overlap a sibling with invisible padding`,
    ).toBe("0px");
    expect(
      entry.hitVectorEffect,
      `${entry.target} must use declared geometry, not a stroke proxy`,
    ).toBe("none");
    expect(entry.hitPointerEvents, `${entry.target} must use its full exact geometry`).toBe("all");
    expect(
      entry.centerHitTarget,
      `${entry.target} must resolve on its visible geometric centre`,
    ).toBe(entry.target);
  }
  const wrongExact = exactTargetReport.find((entry) => entry.target !== activeExactTarget);
  expect(wrongExact?.target, "the rack must offer a non-directed sibling click").toBeTruthy();
  await page.locator(`[data-subpart-hit][data-item-id='${wrongExact?.target}']`).click();
  await expect(
    page.locator(`[data-subpart-hit][data-item-id='${activeExactTarget}']`),
    "a wrong exact-sibling click must be rejected without advancing the interaction",
  ).toHaveCount(1);
  await clickActiveSceneTarget(page);
  await expect(
    advertisedSubpartTargets,
    "the next exact plate target must expose its real sibling wells for normal rejection",
  ).not.toHaveCount(0);

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
    expect(fill, `${well} must retain its exact pre-treatment seeded-cell state`).toEqual(
      untargetedBefore.get(well),
    );
    expect(fill.material, `${well} must not acquire carboplatin`).not.toBe("carboplatin");
  }
  expect(pageErrors, "no uncaught page errors during visible dispensing").toEqual([]);
});
