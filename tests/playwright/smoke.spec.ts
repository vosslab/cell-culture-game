// smoke.spec.ts - broadest boot + one-visible-control smoke for the app.
//
// Converted from the library-model tests/playwright/test_protocol_selector.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
// The runner owns pass/fail and the shared server; this spec asserts only what
// a student sees: the launcher boots, protocol cards render, a real click on a
// card navigates to that protocol's page, and the scene mounts a clickable
// object.
//
// Served over HTTP by the playwright.config.ts webServer block (build + serve
// dist/). No per-file server, no chromium import, no process.exit.
//
// Selector contract (cite source file:line so a UI change surfaces the coupling):
//   - h1 "Choose your lab experience"  src/launcher/protocol_launcher.tsx
//   - protocol card anchors (getByRole) src/launcher/protocol_launcher.tsx
//   - data-protocol-id (stable app id)  src/launcher/protocol_launcher.tsx
//   - #scene-root [data-item-id] items  src/protocol_host_template.html:47,
//                                       src/scene_runtime/renderer/scene_item.tsx:34
//
// mtt_reagent_prep is a known-good mini-protocol whose entry scene renders
// scene items; it is targeted by its stable data-protocol-id (app state that an
// accessible role cannot express), while the launcher boot is asserted through
// accessible getByRole selectors first.

import { test, expect } from "@playwright/test";

const SMOKE_PROTOCOL_ID = "mtt_reagent_prep";

test("smoke: launcher boots, a card click opens a protocol scene", async ({ page }) => {
  // Surface uncaught page errors so a runtime failure fails the test loudly.
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });

  await page.goto("/");

  // Boot: the launcher heading is visible (web-first, auto-retries until ready).
  await expect(
    page.getByRole("heading", { name: "Choose your lab experience", level: 1 }),
  ).toBeVisible();

  // A learner-visible launcher card is ready to open.
  const cards = page.locator("[data-launcher-link]");
  await expect(cards.first()).toBeVisible();

  await page.screenshot({ path: "test-results/smoke_00_launcher.png" });

  // Visible control: click the known-good protocol card by its stable app id.
  const card = page.locator(`[data-protocol-id="${SMOKE_PROTOCOL_ID}"]`);
  const disclosure = page.locator("details.cluster-disclosure").filter({ has: card });
  await expect(disclosure).toHaveCount(1);
  await disclosure.locator("summary").click();
  await expect(card).toBeVisible();
  await card.click();

  // Navigation reached the protocol's own page.
  await expect(page).toHaveURL(new RegExp(`/${SMOKE_PROTOCOL_ID}\\.html$`));

  // The scene mounted at least one clickable scene object (web-first wait
  // replaces the old fixed sleep in the .mjs source).
  const sceneItems = page.locator("#scene-root [data-item-id]");
  await expect(sceneItems.first()).toBeVisible();

  await page.screenshot({ path: "test-results/smoke_01_scene.png" });

  // No uncaught page errors during the boot + navigation path.
  expect(pageErrors).toEqual([]);
});
