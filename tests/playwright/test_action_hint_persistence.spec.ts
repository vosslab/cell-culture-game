// Production-stack regression for learner-owned action-hint disclosure.
//
// Selector contract:
// - src/shell/regions/guidance_bar.tsx renders the native details disclosure
//   and its current authored text as [data-action-hint] and
//   [data-action-hint-text].
// - src/scene_runtime/renderer/scene_item.tsx renders the active whole-object
//   interaction envelope used for every visible click in this real protocol.

import { test, expect, type Locator } from "@playwright/test";

const PROTOCOL = "sdspage_heat_denature_samples";

async function click_active_target(active_target: Locator): Promise<void> {
  await expect(active_target).toHaveCount(1);
  await expect(active_target).toBeVisible();
  await active_target.click();
}

test("an opened native action hint survives scene and shell branch remounts", async ({ page }) => {
  await page.goto(`/${PROTOCOL}.html`, { waitUntil: "networkidle" });

  const active_target = page.locator(
    "#scene-root [data-interaction-envelope][data-interaction-envelope-kind='active']",
  );
  const hint = page.locator("details[data-action-hint]");
  const summary = hint.getByText("Need a hint?", { exact: true });
  const hint_text = hint.locator("[data-action-hint-text]");

  await expect(hint).not.toHaveAttribute("open");
  await summary.click();
  await expect(hint).toHaveAttribute("open", "");
  await expect(hint_text).toHaveText("The block is pre-set; open it before placing the rack.");

  // This accepted interaction changes scenes. The scene remount is a sibling
  // of the shell, and must not reset the learner's disclosure choice.
  await click_active_target(active_target);
  await expect(hint).toHaveAttribute("open", "");
  await expect(hint_text).toHaveText(
    "Load samples B1-B3 and ladder B4 together before closing the lid.",
  );

  await click_active_target(active_target);
  await expect(hint).toHaveAttribute("open", "");
  await expect(hint_text).toHaveText(
    "The rack is inside; closing the lid begins the timed incubation.",
  );

  // The third action replaces the guidance branch with the timed-wait status,
  // then mounts a fresh details node for the next step.
  await click_active_target(active_target);
  await expect(page.locator("[data-timed-wait-status]")).toBeVisible();
  await expect(hint).toHaveAttribute("open", "");
  await expect(hint_text).toHaveText(
    "The 5-minute timed denaturation is complete; expose the rack for retrieval.",
  );

  // An explicit native close remains authoritative on later interactions.
  await summary.press("Enter");
  await expect(hint).not.toHaveAttribute("open");
  await click_active_target(active_target);
  await expect(hint).not.toHaveAttribute("open");
  await expect(hint_text).toHaveText(
    "Keep the labeled tubes together so their lane identities remain paired.",
  );
});
