// Connected browser acceptance for the production protocol session.
//
// The test runs the built dist page from playwright.config.ts, advances only
// through visible learner controls, proves that those actions write the real
// versioned localStorage record, reloads the same page, and continues from the
// visibly restored point. Screenshots come from that exact browser session.

import { test, expect, type Page } from "@playwright/test";

import { SCHEMA_VERSION } from "../../src/schema_version";
import { PROTOCOL_SESSION_STORAGE_KEY } from "../../src/scene_runtime/protocol/session_persistence";

const PROTOCOL = "sdspage_attach_lid_and_leads";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error(`${label} is not a record`);
  }
  return value;
}

async function waitForStablePaint(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
  });
}

test("visible protocol actions persist, resume, complete, and reset", async ({
  page,
}, testInfo) => {
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });

  const sessionStatus = page.locator("[data-session-status]");
  const guidedProgress = page.locator("[data-region='step-counter']");
  const currentAction = page.locator("[data-current-action]");
  const activeTarget = page.locator(
    [
      "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
      "#scene-root [data-subpart-hit][data-subpart-affordance='active']",
    ].join(", "),
  );
  const startOver = page.getByRole("button", { name: "Start over" });

  await expect(sessionStatus).toHaveText("Autosave on");
  await expect(guidedProgress).toContainText("0 / 3");
  await expect(currentAction).toHaveAttribute("data-action-label", "Electrophoresis tank");
  await expect(activeTarget).toHaveCount(1);
  await expect(activeTarget).toBeVisible();
  const freshSessionRoot = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  expect(freshSessionRoot).toBeNull();

  await page.reload({ waitUntil: "networkidle" });

  await expect(sessionStatus).toHaveText("Autosave on");
  await expect(guidedProgress).toContainText("0 / 3");
  await expect(currentAction).toHaveAttribute("data-action-label", "Electrophoresis tank");
  const reloadedFreshSessionRoot = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  expect(reloadedFreshSessionRoot).toBeNull();

  await activeTarget.click();

  await expect(sessionStatus).toHaveText("Progress saved");
  await expect(guidedProgress).toContainText("1 / 3");
  await expect(currentAction).toHaveAttribute(
    "data-action-label",
    "Electrophoresis tank black terminal",
  );
  await expect(currentAction).toHaveAttribute(
    "data-action-target",
    "rear_center_electrophoresis_tank.black_terminal",
  );

  const beforeReloadPath = testInfo.outputPath("01-progress-saved-before-reload.png");
  await waitForStablePaint(page);
  await page.screenshot({ path: beforeReloadPath });
  await testInfo.attach("progress saved before reload", {
    path: beforeReloadPath,
    contentType: "image/png",
  });

  const rawSessionRoot = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  expect(rawSessionRoot, "the learner action must write the production save key").not.toBeNull();
  const parsedRoot: unknown = JSON.parse(rawSessionRoot ?? "null");
  const root = requireRecord(parsedRoot, "session root");
  expect(root.schema_version).toBe(SCHEMA_VERSION);
  const sessions = requireRecord(root.sessions, "session map");
  const session = requireRecord(sessions[PROTOCOL], "protocol session");
  const machine = requireRecord(session.machine, "step-machine checkpoint");
  const declaredState = requireRecord(session.declared_state, "declared-state archive");
  const tankState = requireRecord(declaredState.electrophoresis_tank, "tank state");
  expect(machine.active_step_name).toBe("connect_black_cathode_lead");
  expect(machine.completed_step_names).toEqual(["secure_lid"]);
  expect(tankState.lid_present).toBe(true);
  const firstPersistenceRevision = session.persistence_revision;
  expect(typeof firstPersistenceRevision).toBe("number");

  await page.reload({ waitUntil: "networkidle" });

  await expect(sessionStatus).toHaveText("Progress restored");
  await expect(guidedProgress).toContainText("1 / 3");
  await expect(currentAction).toHaveAttribute(
    "data-action-label",
    "Electrophoresis tank black terminal",
  );
  await expect(currentAction).toHaveAttribute(
    "data-action-target",
    "rear_center_electrophoresis_tank.black_terminal",
  );
  const restoredRevisionText = await page
    .locator("html")
    .getAttribute("data-protocol-session-revision");
  const restoredRevision = Number(restoredRevisionText);
  expect(restoredRevision).toBe(Number(firstPersistenceRevision));
  const reloadedSavedSessionRoot = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  const reloadedSavedRoot = requireRecord(
    JSON.parse(reloadedSavedSessionRoot ?? "null"),
    "reloaded saved root",
  );
  const reloadedSavedSessions = requireRecord(reloadedSavedRoot.sessions, "reloaded sessions");
  const reloadedSavedSession = requireRecord(
    reloadedSavedSessions[PROTOCOL],
    "reloaded protocol session",
  );
  expect(reloadedSavedSession.persistence_revision).toBe(firstPersistenceRevision);

  const restoredPath = testInfo.outputPath("02-progress-restored-after-reload.png");
  await waitForStablePaint(page);
  await page.screenshot({ path: restoredPath });
  await testInfo.attach("progress restored after reload", {
    path: restoredPath,
    contentType: "image/png",
  });

  await expect(activeTarget).toHaveCount(1);
  await expect(activeTarget).toBeVisible();
  await activeTarget.click();
  await expect(sessionStatus).toHaveText("Progress saved");
  await expect(guidedProgress).toContainText("2 / 3");

  await expect(currentAction).toHaveAttribute(
    "data-action-label",
    "Electrophoresis tank red terminal",
  );
  await expect(currentAction).toHaveAttribute(
    "data-action-target",
    "rear_center_electrophoresis_tank.red_terminal",
  );
  await expect(activeTarget).toHaveCount(1);
  await expect(activeTarget).toBeVisible();
  await activeTarget.click();
  await expect(sessionStatus).toHaveText("Progress saved");
  await expect(page.locator("[data-protocol-complete]")).toBeVisible();
  await expect(guidedProgress).toContainText("3 / 3");

  const completedPath = testInfo.outputPath("03-completed-after-resume.png");
  await waitForStablePaint(page);
  await page.screenshot({ path: completedPath });
  await testInfo.attach("completed after resume", {
    path: completedPath,
    contentType: "image/png",
  });

  await startOver.click();
  const resetDialog = page.getByRole("dialog", { name: "Start this protocol over?" });
  await expect(resetDialog).toBeVisible();
  await expect(resetDialog).toContainText("clears your saved progress for this protocol");
  await resetDialog.getByRole("button", { name: "Clear progress and start over" }).click();

  await expect(sessionStatus).toHaveText("Autosave on");
  await expect(guidedProgress).toContainText("0 / 3");
  await expect(currentAction).toHaveAttribute("data-action-label", "Electrophoresis tank");
  const resetRoot = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  const parsedResetRoot: unknown = JSON.parse(resetRoot ?? "null");
  const resetSessions = requireRecord(
    requireRecord(parsedResetRoot, "reset root").sessions,
    "sessions",
  );
  expect(resetSessions[PROTOCOL]).toBeUndefined();
});

test("invalid persisted domain state is discarded before the first render", async ({ page }) => {
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });
  const sessionStatus = page.locator("[data-session-status]");
  const guidedProgress = page.locator("[data-region='step-counter']");
  const activeTarget = page.locator(
    [
      "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
      "#scene-root [data-subpart-hit][data-subpart-affordance='active']",
    ].join(", "),
  );

  await activeTarget.click();
  await expect(sessionStatus).toHaveText("Progress saved");

  // Narrow corruption-boundary setup: retain the production-written version,
  // fingerprint, and checkpoint, but make its scientific archive impossible to
  // restore. The user-journey test above never seeds or mutates storage.
  const corruptedRoot = await page.evaluate((storageKey) => {
    const raw = window.localStorage.getItem(storageKey);
    if (raw === null) {
      throw new Error("production session was not written");
    }
    const root = JSON.parse(raw) as {
      sessions: Record<string, { declared_state: Record<string, unknown> }>;
    };
    const session = root.sessions.sdspage_attach_lid_and_leads;
    if (session === undefined) {
      throw new Error("production protocol session is missing");
    }
    session.declared_state = {};
    return JSON.stringify(root);
  }, PROTOCOL_SESSION_STORAGE_KEY);
  await page.addInitScript(
    ({ storageKey, serializedRoot }) => {
      window.localStorage.setItem(storageKey, serializedRoot);
    },
    {
      storageKey: PROTOCOL_SESSION_STORAGE_KEY,
      serializedRoot: corruptedRoot,
    },
  );

  await page.reload({ waitUntil: "networkidle" });

  await expect(sessionStatus).toHaveText("Autosave on");
  await expect(guidedProgress).toContainText("0 / 3");
  await expect(page.locator("[data-current-action]")).toHaveAttribute(
    "data-action-label",
    "Electrophoresis tank",
  );
  const clearedSession = await page.evaluate(
    (storageKey) => window.localStorage.getItem(storageKey),
    PROTOCOL_SESSION_STORAGE_KEY,
  );
  const parsed = requireRecord(JSON.parse(clearedSession ?? "null"), "cleared root");
  expect(requireRecord(parsed.sessions, "cleared sessions")[PROTOCOL]).toBeUndefined();
});
