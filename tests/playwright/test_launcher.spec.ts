// test_launcher.spec.ts
//
// Converted from the library-model tests/playwright/test_launcher.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
//
// M4 WP-4-1 launcher test. Loads dist/index.html (served by the
// playwright.config.ts webServer block; no per-file server, no chromium
// import, no process.exit) and asserts:
//   - The launcher renders exactly the protocol ids listed in
//     PROTOCOLS_INDEX (from generated/protocols.ts), no more and no fewer.
//   - Guided workflows come first; technique practice is grouped in native
//     disclosures and uses human-readable labels and calls to action.
//   - Clicking the mtt_reagent_prep card navigates to
//     mtt_reagent_prep.html and both #scene-root and #shell-root
//     render on that page.
//
// Drives the visible UI only (per PRIMARY_CONTRACT.md item 4). Does not
// import src/ or read window.gameState.
//
// Selector contract (cite source file:line so a UI change surfaces the coupling):
//   - [data-launcher-root]        src/launcher/protocol_launcher.tsx
//   - [data-protocol-id] cards    src/launcher/protocol_launcher.tsx
//   - #scene-root, #shell-root    src/protocol_host_template.html:47,65

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { REPO_ROOT } from "./repo_root.mjs";

interface ProtocolIndexEntry {
  protocol_name: string;
  protocol_type: string;
}

//============================================
// Extract expected protocol_name list
//============================================

function loadExpectedIndex(): ProtocolIndexEntry[] {
  // Read generated/protocols.ts and pull the PROTOCOLS_INDEX entries.
  const file = path.join(REPO_ROOT, "generated/protocols.ts");
  const src = fs.readFileSync(file, "utf8");
  // Locate the PROTOCOLS_INDEX literal. The file ends with `] as const;` so we
  // slice from `PROTOCOLS_INDEX` to the next closing `]`.
  const startIdx = src.indexOf("PROTOCOLS_INDEX");
  if (startIdx < 0) {
    throw new Error("PROTOCOLS_INDEX not found in generated/protocols.ts");
  }
  const bracketStart = src.indexOf("[", startIdx);
  const bracketEnd = src.indexOf("\n] as const", bracketStart);
  if (bracketStart < 0 || bracketEnd < 0) {
    throw new Error("PROTOCOLS_INDEX shape unexpected in generated/protocols.ts");
  }
  const blob = src.slice(bracketStart, bracketEnd + 1);
  const names: ProtocolIndexEntry[] = [];
  const re = /protocol_name:\s*["']([^"']+)["'][^}]*protocol_type:\s*["']([^"']+)["']/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(blob)) !== null) {
    names.push({ protocol_name: m[1]!, protocol_type: m[2]! });
  }
  if (names.length === 0) {
    throw new Error("PROTOCOLS_INDEX parsed zero entries");
  }
  return names;
}

async function expectPrimaryCopyFitsViewport(page: Page): Promise<void> {
  const viewport = page.viewportSize();
  expect(viewport, "viewport must be readable").not.toBeNull();
  const primaryCopy = page.locator(
    [
      "[data-launcher-title]:visible",
      ".launcher-subtitle:visible",
      ".tier-heading:visible",
      ".tier-description:visible",
      ".cluster-heading:visible",
      "[data-launcher-link-name]:visible",
      "[data-launcher-step-count]:visible",
      "[data-launcher-cta]:visible",
    ].join(", "),
  );
  const count = await primaryCopy.count();
  expect(count, "launcher must expose primary instructional copy").toBeGreaterThan(0);

  for (let index = 0; index < count; index += 1) {
    const copy = primaryCopy.nth(index);
    await expect(copy).toBeVisible();
    const box = await copy.boundingBox();
    expect(box, `primary copy ${index} must have a box`).not.toBeNull();
    expect(box!.x, `primary copy ${index} must not run off the left edge`).toBeGreaterThanOrEqual(
      0,
    );
    expect(
      box!.x + box!.width,
      `primary copy ${index} must not run off the right edge`,
    ).toBeLessThanOrEqual(viewport!.width + 1);
    const hasHorizontalOverflow = await copy.evaluate(
      (element) => element.scrollWidth > element.clientWidth + 1,
    );
    expect(hasHorizontalOverflow, `primary copy ${index} must not be horizontally clipped`).toBe(
      false,
    );
  }
}

test("launcher renders exactly the PROTOCOLS_INDEX protocols and navigates to one", async ({
  page,
}) => {
  const expected = loadExpectedIndex();
  const expectedNames = expected.map((e) => e.protocol_name);

  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(`console.error: ${msg.text()}`);
    }
  });

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/index.html", { waitUntil: "networkidle" });
  await expect(page.locator("[data-launcher-root]")).toBeVisible();

  // Student-facing organization, not the generated protocol id, drives the
  // launcher. Guided workflows occupy the first tier and focused technique
  // practice comes next.
  const tiers = page.locator("[data-launcher-tier]");
  await expect(tiers.first()).toHaveAttribute("data-launcher-tier", "runners");
  await expect(page.getByRole("heading", { name: "Guided workflows" })).toBeVisible();
  await expect(page.getByText("Follow the authored steps in each workflow.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Focused technique practice" })).toBeVisible();
  await expect(
    page.getByText("Practice one laboratory technique at a time, grouped by topic."),
  ).toBeVisible();

  const guidedPath = page.getByRole("link", { name: "Browse guided workflows" });
  const practicePath = page.getByRole("link", { name: "Practice a focused technique" });
  await expect(guidedPath).toBeVisible();
  await expect(guidedPath).toHaveAttribute("href", "#guided-workflows");
  await expect(practicePath).toBeVisible();
  await expect(practicePath).toHaveAttribute("href", "#focused-technique-practice");
  await expect(page.locator("#guided-workflows")).toHaveCount(1);
  await expect(page.locator("#focused-technique-practice")).toHaveCount(1);

  const allLauncherText = await page.locator("[data-launcher-root]").innerText();
  expect(allLauncherText, "launcher must not expose implementation ids to students").not.toMatch(
    /\b[a-z0-9]+(?:_[a-z0-9]+)+\b/,
  );

  const firstWorkflow = page.locator('[data-launcher-tier="runners"] [data-launcher-link]').first();
  await expect(firstWorkflow).toBeVisible();
  await expect(firstWorkflow.locator("[data-launcher-kind]")).toHaveText("Guided workflow");
  await expect(firstWorkflow.locator("[data-launcher-step-count]")).toHaveText(/^\d+ steps$/);
  await expect(firstWorkflow.locator("[data-launcher-cta]")).toHaveText("Open guided workflow");

  // Native disclosures remain keyboard- and browser-operable. They begin
  // closed so the student sees topic choices before the complete catalog.
  const cellCultureSection = page.locator('.cluster-section[data-cluster="cell_culture"]');
  const firstDisclosure = cellCultureSection.locator("details.cluster-disclosure");
  await expect(firstDisclosure).not.toHaveAttribute("open", "");
  const firstSummary = firstDisclosure.locator("[data-launcher-cluster-toggle]");
  await expect(firstSummary).toBeVisible();
  await expect(firstSummary.locator(".cluster-entry-count")).toHaveText(/^\d+ techniques$/);
  await expect(firstSummary.locator(".cluster-toggle-show")).toBeVisible();
  await expect(firstSummary.locator(".cluster-toggle-hide")).toBeHidden();
  await firstSummary.click();
  await expect(firstDisclosure).toHaveAttribute("open", "");
  await expect(firstSummary.locator(".cluster-toggle-show")).toBeHidden();
  await expect(firstSummary.locator(".cluster-toggle-hide")).toBeVisible();

  await expectPrimaryCopyFitsViewport(page);

  // Collect every rendered protocol id.
  const rendered = await page
    .locator("[data-protocol-id]")
    .evaluateAll((els) => els.map((el) => el.getAttribute("data-protocol-id")));

  // Every expected protocol must render.
  for (const name of expectedNames) {
    expect(rendered, `Launcher missing [data-protocol-id=${name}]`).toContain(name);
  }

  // The rendered set must be exactly the expected set: every rendered id
  // must be a real PROTOCOLS_INDEX entry, and the counts must match so
  // nothing extra sneaks in.
  for (const id of rendered) {
    const match = expected.find((e) => e.protocol_name === id);
    expect(
      match,
      `Launcher rendered unknown id ${String(id)} (not in PROTOCOLS_INDEX)`,
    ).toBeDefined();
  }
  expect(
    rendered.length,
    `Launcher rendered ${rendered.length} entries; PROTOCOLS_INDEX has ${expectedNames.length}`,
  ).toBe(expectedNames.length);

  await page.screenshot({ path: "test-results/test_launcher_00_index.png" });

  // Click the mtt_reagent_prep entry and confirm navigation.
  const link = page.locator('[data-protocol-id="mtt_reagent_prep"]');
  await expect(link).toHaveCount(1);
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", "mtt_reagent_prep.html");
  await expect(link.locator("[data-launcher-kind]")).toHaveText("Focused technique practice");
  await expect(link.locator("[data-launcher-step-count]")).toHaveText(/^\d+ steps$/);
  await expect(link.locator("[data-launcher-cta]")).toHaveText("Practice this technique");
  await Promise.all([page.waitForLoadState("networkidle"), link.click()]);

  await expect(page).toHaveURL(/\/mtt_reagent_prep\.html$/);
  await expect(page).toHaveTitle("MTT: Reagent prep | Virtual Lab Coach");
  await expect(page.locator("[data-protocol-display-title]")).toHaveText("MTT: Reagent prep");
  await expect(page.locator("[data-protocol-display-title]")).not.toHaveText(/mtt_reagent_prep/);

  // Confirm both mount roots exist and the scene rendered at least one item.
  await expect(page.locator("#scene-root")).toBeAttached();
  await expect(page.locator("#shell-root")).toBeAttached();
  const sceneItems = page.locator("#scene-root [data-item-id]");
  await expect(sceneItems.first()).toBeVisible();

  await page.screenshot({ path: "test-results/test_launcher_01_mtt_reagent_prep.png" });

  const errors = [...pageErrors, ...consoleErrors];
  expect(errors, `Page errors: ${errors.join(" | ")}`).toEqual([]);
});

test("launcher paths and collapsed practice groups remain usable on a narrow screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/index.html", { waitUntil: "networkidle" });

  await expect(page.getByRole("heading", { name: "Choose your lab experience" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Browse guided workflows" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Practice a focused technique" })).toBeVisible();

  const disclosures = page.locator("details.cluster-disclosure");
  expect(await disclosures.count()).toBeGreaterThan(0);
  for (let index = 0; index < (await disclosures.count()); index += 1) {
    await expect(disclosures.nth(index)).not.toHaveAttribute("open", "");
  }

  const horizontalOverflow = await page
    .locator("[data-launcher-root]")
    .evaluate((root) => root.scrollWidth > root.clientWidth + 1);
  expect(horizontalOverflow, "launcher must not overflow horizontally").toBe(false);
  await expectPrimaryCopyFitsViewport(page);
});
