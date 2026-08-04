// A learner-visible regression for the two independently addressable
// hemocytometer liquid regions. No game-state reads or test-only advancement.

import { test, expect, type Locator, type Page } from "@playwright/test";

function activeTarget(page: Page): Locator {
  return page.locator(
    [
      "#scene-root [data-item-id][data-affordance='active']",
      "#scene-root [data-item-id][data-subpart-affordance='active']",
    ].join(", "),
  );
}

async function clickDirectedTarget(page: Page, target: string): Promise<void> {
  const locator = activeTarget(page);
  await expect(locator, `one visible control must direct ${target}`).toHaveCount(1);
  await expect(locator).toHaveAttribute("data-item-id", target);
  await locator.click();
}

test("hemocytometer diamond keeps a center-hittable semicircle sibling that is rejected", async ({
  page,
}) => {
  await page.goto("/trypan_blue_counting.html", { waitUntil: "networkidle" });
  await clickDirectedTarget(page, "right_p20_micropipette");
  await clickDirectedTarget(page, "left_tip_box");
  const input = page.locator("[data-adjust-input]");
  await expect(input).toBeVisible();
  await input.fill("10");
  await page.locator("[data-adjust-commit]").click();
  await expect(page.locator("[data-adjust-panel]")).toBeHidden();
  await clickDirectedTarget(page, "rear_trypan_blue_tube");

  const diamond = page.locator(
    "[data-subpart-hit][data-item-id='right_hemocytometer_slide.diamond']",
  );
  const semicircle = page.locator(
    "[data-subpart-hit][data-item-id='right_hemocytometer_slide.semicircle']",
  );
  await expect(diamond).toHaveCount(1);
  await expect(semicircle).toHaveCount(1);
  await expect(diamond).toHaveAttribute("data-subpart-affordance", "active");
  await expect(semicircle).toHaveAttribute("data-subpart-affordance", "none");

  const geometry = await page
    .locator("[data-subpart-hit][data-item-id^='right_hemocytometer_slide.']")
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
  expect(geometry).toHaveLength(2);
  for (const chamber of geometry) {
    expect(chamber.width, `${chamber.target} must have a usable core`).toBeGreaterThanOrEqual(24);
    expect(chamber.height, `${chamber.target} must have a usable core`).toBeGreaterThanOrEqual(24);
    expect(chamber.centerTarget, `${chamber.target} centre must resolve to itself`).toBe(
      chamber.target,
    );
  }

  await semicircle.click();
  await expect(diamond, "a wrong chamber click must be rejected without advancing").toHaveCount(1);
});
