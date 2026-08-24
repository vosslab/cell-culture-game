// Regression coverage for the two dense SDS-PAGE structured surfaces.  These
// tests use only painted, learner-visible controls: no game-state reads, test
// hooks, or synthetic protocol advancement.

import { test, expect, type Locator, type Page } from "@playwright/test";

function activeTarget(page: Page): Locator {
  return page.locator(
    [
      "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
      "#scene-root [data-item-id][data-subpart-affordance='active']",
    ].join(", "),
  );
}

async function clickDirectedTarget(page: Page, target: string): Promise<void> {
  const locator = activeTarget(page);
  await expect(locator, `exactly one visible target must direct ${target}`).toHaveCount(1);
  await expect(locator).toHaveAttribute("data-item-id", target);
  await expect(locator).toBeVisible();
  await locator.click();
}

async function setDirectedValue(page: Page, value: string): Promise<void> {
  const input = page.locator("[data-adjust-input]");
  await expect(input, `the directed value ${value} must use the visible editor`).toBeVisible();
  await input.fill(value);
  await page.locator("[data-adjust-commit]").click();
  await expect(page.locator("[data-adjust-panel]")).toBeHidden();
}

async function assertExactSiblings(page: Page, active: string, sibling: string): Promise<void> {
  const activeLocator = page.locator(`[data-subpart-hit][data-item-id='${active}']`);
  const siblingLocator = page.locator(`[data-subpart-hit][data-item-id='${sibling}']`);
  await expect(activeLocator).toHaveCount(1);
  await expect(siblingLocator, `${sibling} must remain a real wrong-click target`).toHaveCount(1);
  await expect(activeLocator).toHaveAttribute("data-subpart-affordance", "active");
  await expect(siblingLocator).toHaveAttribute("data-subpart-affordance", "none");

  const report = await page
    .locator(`[data-subpart-hit][data-item-id^='${active.slice(0, active.lastIndexOf("."))}.']`)
    .evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect();
        return {
          target: element.getAttribute("data-item-id"),
          width: box.width,
          height: box.height,
          centerTarget:
            document
              .elementFromPoint(box.left + box.width / 2, box.top + box.height / 2)
              ?.closest("[data-item-id]")
              ?.getAttribute("data-item-id") ?? null,
        };
      }),
    );
  expect(report.length, `${active} must retain sibling surfaces`).toBeGreaterThan(1);
  for (const entry of report) {
    expect(entry.width, `${entry.target} needs a usable visible core`).toBeGreaterThanOrEqual(24);
    expect(entry.height, `${entry.target} needs a usable visible core`).toBeGreaterThanOrEqual(24);
    expect(entry.centerTarget, `${entry.target} must resolve to its own exact surface`).toBe(
      entry.target,
    );
  }

  // A learner can click the visibly painted sibling, but normal validation
  // rejects it and leaves the directed target in place.
  await siblingLocator.click();
  await expect(activeLocator, `wrong ${sibling} click must not advance ${active}`).toHaveCount(1);
}

test("SDS sample mixing keeps A1 and later A2 as distinct usable rack targets", async ({
  page,
}) => {
  await page.goto("/sdspage_prepare_sample_mix_batch.html", { waitUntil: "networkidle" });
  await clickDirectedTarget(page, "center_p200_sample_micropipette");
  await clickDirectedTarget(page, "rear_left_micropipette_tip_box");
  await setDirectedValue(page, "21");
  await assertExactSiblings(
    page,
    "center_sds_microtube_rack.slot_A1",
    "center_sds_microtube_rack.slot_A2",
  );
  await clickDirectedTarget(page, "center_sds_microtube_rack.slot_A1");
  await clickDirectedTarget(page, "center_sds_microtube_rack.slot_B1");
  await clickDirectedTarget(page, "rear_left_micropipette_tip_box");
  await setDirectedValue(page, "7.5");
  await clickDirectedTarget(page, "rear_center_laemmli");
  await clickDirectedTarget(page, "center_sds_microtube_rack.slot_B1");
  await clickDirectedTarget(page, "rear_left_micropipette_tip_box");
  await setDirectedValue(page, "1.5");
  await clickDirectedTarget(page, "rear_right_bme");
  await clickDirectedTarget(page, "center_sds_microtube_rack.slot_B1");
  await clickDirectedTarget(page, "rear_left_micropipette_tip_box");
  await setDirectedValue(page, "21");
  await assertExactSiblings(
    page,
    "center_sds_microtube_rack.slot_A2",
    "center_sds_microtube_rack.slot_A1",
  );
});

test("SDS gel lane one retains a real, rejectable lane-two sibling", async ({ page }) => {
  await page.goto("/sdspage_load_samples_batch.html", { waitUntil: "networkidle" });
  await clickDirectedTarget(page, "center_p200_micropipette");
  await clickDirectedTarget(page, "right_tool_area_gel_loading_tip_box");
  await setDirectedValue(page, "30");
  await clickDirectedTarget(page, "front_center_sds_microtube_rack.slot_B1");
  await assertExactSiblings(
    page,
    "front_center_gel_cassette.lane_1",
    "front_center_gel_cassette.lane_2",
  );
});
