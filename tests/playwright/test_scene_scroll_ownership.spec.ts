// The shell owns the browser viewport. A scene may need a larger declared
// interaction frame than the space left by coaching chrome; in that case only
// the scene panel may scroll. Page-level scrolling would move the fixed shell
// and make an otherwise valid subpart sibling unreachable.

import { test, expect, type Page } from "@playwright/test";

const PROTOCOL = "trypan_blue_counting";
const PLATE_PROTOCOL = "cell_seeding_plate_setup";

interface ReadonlyScrollOwnershipWindow {
  readonly gameState?: {
    readonly activeStepId: string | null;
    readonly interactionIndex: number;
  };
}

async function clickCurrentWholeAction(page: Page): Promise<void> {
  const before = await page.evaluate(() => ({
    step: (window as ReadonlyScrollOwnershipWindow).gameState?.activeStepId,
    index: (window as ReadonlyScrollOwnershipWindow).gameState?.interactionIndex,
  }));
  if (before.step === undefined || before.index === undefined) {
    throw new Error("scroll ownership test requires the read-only walker state");
  }
  const active = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
  );
  await expect(active).toHaveCount(1);
  await active.click();
  await page.waitForFunction((previous) => {
    const state = (window as ReadonlyScrollOwnershipWindow).gameState;
    return (
      state !== undefined &&
      (state.activeStepId !== previous.step || state.interactionIndex !== previous.index)
    );
  }, before);
}

test("active scene targets scroll within the scene panel, never the document", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });

  const target = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
  );
  await expect(target).toHaveCount(1);
  await expect(target).toBeVisible();
  // Advance once through the same visible learner path. The host must align
  // the next action itself; this test intentionally does not call the
  // walker's scrollIntoViewIfNeeded helper.
  await target.click();
  await expect(target).toHaveCount(1);
  await expect(target).toBeVisible();

  const geometry = await page.evaluate(() => {
    const panel = document.querySelector(".scene-panel");
    const target = document.querySelector(
      "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
    );
    if (!(panel instanceof HTMLElement) || !(target instanceof HTMLElement)) {
      throw new Error("scroll-ownership proof requires a scene panel and active envelope");
    }
    const targetBox = target.getBoundingClientRect();
    return {
      documentScrollY: window.scrollY,
      documentHeight: document.documentElement.scrollHeight,
      viewportHeight: window.innerHeight,
      panelScrollHeight: panel.scrollHeight,
      panelClientHeight: panel.clientHeight,
      panelOverflowY: window.getComputedStyle(panel).overflowY,
      targetInsideViewport:
        targetBox.top >= 0 && targetBox.bottom <= window.innerHeight && targetBox.height >= 44,
    };
  });

  expect(geometry.documentScrollY, "the document must remain anchored at the shell top").toBe(0);
  expect(
    geometry.documentHeight,
    "the fixed desktop shell must not create a page-scroll escape hatch",
  ).toBeLessThanOrEqual(geometry.viewportHeight + 1);
  expect(geometry.panelOverflowY, "the bounded scene region owns any required scroll").toBe("auto");
  expect(geometry.panelScrollHeight).toBeGreaterThanOrEqual(geometry.panelClientHeight);
  expect(geometry.targetInsideViewport, "the active learner target remains usable").toBe(true);
});

test("phone layout keeps document flow vertical and scene overflow local", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 300 });
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });

  await expect(page.locator("#guidance-text")).not.toHaveText("Loading...");
  const activeTarget = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
  );
  await expect(activeTarget).toHaveCount(1);

  const layout = await page.evaluate(() => {
    const regions = [
      document.querySelector('[data-region="header"]'),
      document.querySelector('[data-region="scene-panel"]'),
      document.querySelector('[data-region="interaction-controls"]'),
      document.querySelector('[data-region="guidance-bar"]'),
      document.querySelector('[data-region="outline"]'),
    ];
    if (regions.some((region) => region === null)) {
      throw new Error("phone scroll ownership requires all documented shell regions");
    }
    const regionNames = ["header", "scene", "controls", "guidance", "outline"];
    const visibleRegionNames = regions
      .map((region, index) => ({
        name: regionNames[index],
        top: (region as HTMLElement).getBoundingClientRect().top,
        height: (region as HTMLElement).getBoundingClientRect().height,
      }))
      .filter(({ height }) => height > 0)
      .sort((left, right) => left.top - right.top)
      .map(({ name }) => name);
    const order = visibleRegionNames.every(
      (name, index) =>
        name === regionNames.filter((expected) => visibleRegionNames.includes(expected))[index],
    );
    const grid = document.querySelector(".protocol-page-grid");
    const panel = document.querySelector(".scene-panel");
    if (!(grid instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
      throw new Error("phone scroll ownership requires the page grid and scene panel");
    }
    return {
      order,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      viewportWidth: window.innerWidth,
      gridHeight: grid.getBoundingClientRect().height,
      viewportHeight: window.innerHeight,
      gridOverflow: window.getComputedStyle(grid).overflow,
      panelOverflowX: window.getComputedStyle(panel).overflowX,
      panelOverflowY: window.getComputedStyle(panel).overflowY,
      documentHeight: document.documentElement.scrollHeight,
    };
  });

  expect(layout.order, "regions stay in header/scene/controls/guidance/outline order").toBe(true);
  expect(
    layout.documentWidth,
    "minimum interaction frames must not widen the document",
  ).toBeLessThanOrEqual(layout.viewportWidth + 1);
  expect(layout.bodyWidth, "body content must not widen the document").toBeLessThanOrEqual(
    layout.viewportWidth + 1,
  );
  expect(layout.gridOverflow, "narrow shell returns scrolling to normal document flow").toBe(
    "visible",
  );
  expect(layout.gridHeight).toBeGreaterThanOrEqual(layout.viewportHeight);
  expect(layout.documentHeight).toBeGreaterThan(layout.viewportHeight);
  expect(layout.panelOverflowX, "scene panel owns horizontal frame overflow").toBe("auto");
  expect(layout.panelOverflowY, "scene panel owns scene-frame overflow").toBe("auto");

  const outline = page.locator('[data-region="outline"]');
  await outline.scrollIntoViewIfNeeded();
  await expect(outline).toBeVisible();
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);

  const guidance = page.locator('[data-region="guidance-bar"]');
  await guidance.scrollIntoViewIfNeeded();
  await expect(guidance.locator("#guidance-text")).toBeVisible();
  await activeTarget.scrollIntoViewIfNeeded();
  await expect(activeTarget).toBeVisible();
});

test("a fitting active plate-column group is aligned inside the scene scrollport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(`/${PLATE_PROTOCOL}.html`, { waitUntil: "networkidle" });

  // The first select has many candidates, so choose its known visible card. All
  // following preparation actions have exactly one whole-object envelope.
  const calculation = page.locator("#scene-root [data-item-id='calculation_2_8_choice']").first();
  await expect(calculation).toBeVisible();
  await calculation.click();
  await page.waitForFunction(
    () =>
      (window as ReadonlyScrollOwnershipWindow).gameState?.activeStepId ===
      "prepare_diluted_suspension",
  );

  for (let count = 0; count < 8; count += 1) {
    await clickCurrentWholeAction(page);
  }
  for (let count = 0; count < 2; count += 1) {
    await clickCurrentWholeAction(page);
  }

  const adjustInput = page.locator("[data-adjust-input]");
  await expect(adjustInput).toBeVisible();
  await adjustInput.fill("100");
  await page.locator("[data-adjust-commit]").click();
  await page.waitForFunction(() => {
    const state = (window as ReadonlyScrollOwnershipWindow).gameState;
    return state?.activeStepId === "seed_96_well_plate" && state.interactionIndex === 3;
  });

  // These are the final two ordinary clicks before the first column group.
  // Do not scroll the group under test: production must align it as the action
  // becomes active for a learner.
  await clickCurrentWholeAction(page);
  await clickCurrentWholeAction(page);

  const groupTarget = "foreground_well_plate_96.col_1";
  const groupMembers = page.locator(
    `#scene-root [data-subpart-group-target='${groupTarget}'][data-item-id='${groupTarget}']`,
  );
  await expect(groupMembers).toHaveCount(8);

  await expect
    .poll(async () =>
      page.evaluate((target) => {
        const panel = document.querySelector(".scene-panel");
        const members = [...document.querySelectorAll(`[data-subpart-group-target='${target}']`)];
        if (!(panel instanceof HTMLElement) || members.length !== 8) {
          return false;
        }
        const port = panel.getBoundingClientRect();
        return members.every((member) => {
          const rect = member.getBoundingClientRect();
          const hit = document.elementFromPoint(
            rect.left + rect.width / 2,
            rect.top + rect.height / 2,
          );
          return (
            rect.width >= 25.9 &&
            rect.height >= 25.9 &&
            rect.top >= port.top &&
            rect.bottom <= port.bottom &&
            hit?.closest("[data-item-id]")?.getAttribute("data-item-id") === target
          );
        });
      }, groupTarget),
    )
    .toBe(true);

  const groupGeometry = await page.evaluate((target) => {
    const panel = document.querySelector(".scene-panel");
    if (!(panel instanceof HTMLElement)) {
      throw new Error("plate-column proof requires the scene scrollport");
    }
    return {
      documentScrollY: window.scrollY,
      panelScrollTop: panel.scrollTop,
      panelClientHeight: panel.clientHeight,
      panelScrollHeight: panel.scrollHeight,
      members: [...document.querySelectorAll(`[data-subpart-group-target='${target}']`)].map(
        (member) => {
          const rect = member.getBoundingClientRect();
          return {
            name: member.getAttribute("data-subpart-name"),
            width: rect.width,
            height: rect.height,
          };
        },
      ),
    };
  }, groupTarget);
  expect(groupGeometry.documentScrollY, "the group reveal must not move the document").toBe(0);
  expect(groupGeometry.panelScrollHeight).toBeGreaterThan(groupGeometry.panelClientHeight);
  expect(groupGeometry.panelScrollTop, "the fitting group needs a local reveal").toBeGreaterThan(0);
  expect(groupGeometry.members.map(({ name }) => name)).toEqual([
    "A1",
    "B1",
    "C1",
    "D1",
    "E1",
    "F1",
    "G1",
    "H1",
  ]);
  for (const member of groupGeometry.members) {
    expect(
      member.width,
      `${member.name} retains its declared 26px interaction region`,
    ).toBeGreaterThanOrEqual(25.9);
    expect(
      member.height,
      `${member.name} retains its declared 26px interaction region`,
    ).toBeGreaterThanOrEqual(25.9);
  }
});
