// test_rear_tip_box_rack_identity.spec.ts
//
// The transient-spinning-snowglobe plan's groupVerticalBands fix
// resolved a transitive band-merge that fused rear_left,
// left_bench, instrument_area, rear_right, and right_bench into one
// computed band, coincidentally stacking rear_tip_box and
// left_microtube_rack at a 100% render overlap. This spec proves the fix
// holds for the three affected scenes named in the plan and for the
// pedagogy gate: both objects remain independently visible AND clickable
// by their own placement identity (no z-order occlusion), per
// docs/PRIMARY_CONTRACT.md item 3.
//
// microscope_basic is the surviving scene that intentionally contains both
// placements. Protocol-specific observation scenes now use dedicated result
// displays and no longer inherit this unrelated rack/tip-box composition.
//
// Selector contract:
//   - #scene-root                      src/scene_runtime/renderer/scene_root.tsx
//   - [data-placement-name]            src/scene_runtime/renderer/scene_item.tsx

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

import { bboxsOverlap } from "../../tools/bbox_helpers.mjs";

//============================================
// Test configuration
//============================================

const AFFECTED_SCENES = ["microscope_basic"];

const ITEM_A = "rear_tip_box";
const ITEM_B = "left_microtube_rack";

interface PixelBbox {
  x: number;
  y: number;
  width: number;
  height: number;
}

//============================================
// Helpers
//============================================

// Reads the CSS-pixel bbox of one [data-placement-name] element on the
// currently-loaded page. Fails loudly (via expect) rather than returning
// null so a missing placement cannot silently pass this identity check.
async function placementBbox(page: Page, placementName: string): Promise<PixelBbox> {
  const locator = page.locator(`[data-placement-name="${placementName}"]`);
  await expect(locator, `${placementName} must render exactly once`).toHaveCount(1);
  const bbox = await locator.boundingBox();
  expect(bbox, `${placementName} must report a bounding box`).not.toBeNull();
  return bbox as PixelBbox;
}

// Confirms that clicking at an item's own bbox center resolves to that
// item's OWN [data-placement-name] identity, not an overlapping sibling's.
// document.elementFromPoint is the browser's own hit-test, the same
// resolution a real student click performs, so this is the direct evidence
// for "clickable by its own placement identity" rather than an inferred
// non-overlap on rectangles alone.
async function resolvedPlacementAtCenter(page: Page, bbox: PixelBbox): Promise<string | null> {
  const cx = bbox.x + bbox.width / 2;
  const cy = bbox.y + bbox.height / 2;
  return page.evaluate(
    ({ cx, cy }) => {
      const hit = document.elementFromPoint(cx, cy);
      const owner = hit === null ? null : hit.closest("[data-placement-name]");
      return owner === null ? null : owner.getAttribute("data-placement-name");
    },
    { cx, cy },
  );
}

//============================================
// Tests: one per affected scene
//============================================

test.describe("rear_tip_box / left_microtube_rack independent identity", () => {
  for (const sceneName of AFFECTED_SCENES) {
    test(`${sceneName}: both items render distinct and click to their own identity`, async ({
      page,
    }) => {
      await page.goto(`/scene_viewer.html?scene=${sceneName}`, { waitUntil: "networkidle" });
      await page.locator("#scene-root [data-placement-name]").first().waitFor({ state: "visible" });

      const bboxA = await placementBbox(page, ITEM_A);
      const bboxB = await placementBbox(page, ITEM_B);

      // Regression guard: the plan's defect was a 100% render overlap between
      // these two items (structural_guards.ts Guard 3). Confirm the fix holds.
      expect(
        bboxsOverlap(bboxA, bboxB),
        `${ITEM_A} and ${ITEM_B} must render non-overlapping in ${sceneName}`,
      ).toBe(false);

      // Pedagogy gate: a click at each item's own bbox center must hit-test
      // to that item's OWN placement identity, not the other's. This is the
      // browser's real hit-test (document.elementFromPoint), so it proves
      // neither item's clickable area is occluded by the other.
      const hitA = await resolvedPlacementAtCenter(page, bboxA);
      expect(hitA, `clicking ${ITEM_A}'s own center must resolve to ${ITEM_A}`).toBe(ITEM_A);

      const hitB = await resolvedPlacementAtCenter(page, bboxB);
      expect(hitB, `clicking ${ITEM_B}'s own center must resolve to ${ITEM_B}`).toBe(ITEM_B);

      // Playwright's own actionability check (trial click): visible, stable,
      // and receives pointer events at its own location without another
      // element intercepting the hit test. No side effects are triggered.
      await page.locator(`[data-placement-name="${ITEM_A}"]`).click({ trial: true });
      await page.locator(`[data-placement-name="${ITEM_B}"]`).click({ trial: true });

      await page.screenshot({
        path: `test-results/rear_tip_box_rack_identity_${sceneName}.png`,
        fullPage: false,
      });
    });
  }
});
