// test_generalization_render.spec.ts
//
// Converted from the library-model tests/playwright/test_generalization_render.mjs
// (that .mjs stays in place this phase; a later cleanup phase removes it).
//
// Renders EVERY base scene discovered under content/base_scenes/ (via
// discoverBaseSceneNames() in ./helper_scene_discovery.mjs, not a hand-maintained
// list) through scene_viewer.html and asserts the same render-integrity
// contract as test_bench_basic_render.spec.ts, generalized across both
// renderer asset modes:
//   - dom-svg mode: inline <svg> with content, preserveAspectRatio != "none"
//   - img mode: <img data-svg-render-mode="img"> loaded, object-fit contain/
//     scale-down
//
// A vacuous match (zero comparable pairs/assets for an assertion that should
// have evaluated at least one) is a hard failure, not a silent pass.
//
// Served over HTTP by the playwright.config.ts webServer block (build + serve
// dist/). No per-file server, no chromium import, no process.exit.
//
// Selector contract (cite source file:line so a UI change surfaces the coupling):
//   - #scene-root                         src/scene_runtime/renderer/scene_root.tsx
//   - [data-placement-name] placements    src/scene_runtime/renderer/scene_item.tsx
//   - [data-label] / [data-label-for]     src/scene_runtime/renderer/scene_item.tsx
//   - [data-svg-render-mode="img"]        src/scene_runtime/renderer/scene_item.tsx:273-308
//   - [data-svg-load-error]               src/scene_runtime/renderer/scene_item.tsx:245,251-262

/// <reference types="node" />

import { test, expect } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { REPO_ROOT } from "./repo_root.mjs";
import { discoverBaseSceneNames } from "./helper_scene_discovery.mjs";
import { bboxContains, bboxsOverlap } from "../../tools/bbox_helpers.mjs";
import type { Bbox } from "../../tools/bbox_helpers.mjs";

//============================================
// Test configuration
//============================================

const OVERLAP_TOLERANCE = 1; // 1px jitter tolerance
const MIN_FONT_SIZE = 6; // pixels

// Scenes to render: discovered from content/base_scenes/ so every base scene
// that exists is exercised, not a stale hand-maintained list.
const SCENES_TO_RENDER = discoverBaseSceneNames();

// Data-driven expected-fail registry: known-routed scene defects owned by
// other teams. Each scene renders as its own discrete test, so test.fail()
// targets exactly one scene without weakening the shared assertion suite.
// test.fail() still RUNS the render and assertions (unlike test.skip/
// test.fixme); if the scene is ever fixed, its test starts passing and
// Playwright reports an unexpected pass, forcing this entry to be removed.
const EXPECTED_FAIL_SCENES: Record<string, string> = {};

//============================================
// Types
//============================================

interface ComputedStyleSummary {
  overflow: string;
  clipPath: string;
  contain: string;
  visibility: string;
  display: string;
  opacity: string;
  fontSize: string;
}

interface SvgAssetInfo {
  hasContent: boolean;
  preserveAspectRatio: string | null;
}

interface ImgAssetInfo {
  naturalWidth: number;
  naturalHeight: number;
  objectFit: string;
}

interface PlacementAssetInfo {
  hasLoadError: boolean;
  failText: boolean;
  svgs: SvgAssetInfo[];
  imgs: ImgAssetInfo[];
}

interface Placement {
  name: string | null;
  bbox: Bbox | null;
}

interface LabelInfo {
  bbox: Bbox | null;
  text: string | null;
  labelFor: string | null;
  styles: ComputedStyleSummary;
}

//============================================
// Helpers
//============================================

async function checkComputedStyles(locator: Locator): Promise<ComputedStyleSummary> {
  return locator.evaluate((el: Element): ComputedStyleSummary => {
    const computed = window.getComputedStyle(el);
    return {
      overflow: computed.overflow,
      clipPath: computed.clipPath,
      contain: computed.contain,
      visibility: computed.visibility,
      display: computed.display,
      opacity: computed.opacity,
      fontSize: computed.fontSize,
    };
  });
}

// Gathers the asset-render facts a placement exposes, covering BOTH renderer
// modes so the aspect/fallback assertions stay honest instead of null-failing
// every img-mode asset.
async function gatherPlacementAssetInfo(placementLocator: Locator): Promise<PlacementAssetInfo> {
  return placementLocator.evaluate((el: Element): PlacementAssetInfo => {
    const loadErrEl = el.querySelector("[data-svg-load-error]");
    const errAttr = loadErrEl ? loadErrEl.getAttribute("data-svg-load-error") : null;
    const hasLoadError = errAttr !== null && errAttr.length > 0;
    const textContent = el.textContent ?? "";
    const failText = textContent.includes("SVG load failed");
    const svgEls = Array.from(el.querySelectorAll("svg"));
    const svgs = svgEls.map((s) => {
      return {
        hasContent: s.innerHTML.trim().length > 0,
        preserveAspectRatio: s.getAttribute("preserveAspectRatio"),
      };
    });
    const imgEls = Array.from(el.querySelectorAll('img[data-svg-render-mode="img"]'));
    const imgs = imgEls.map((im) => {
      const image = im as HTMLImageElement;
      const computed = window.getComputedStyle(image);
      return {
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
        objectFit: computed.objectFit,
      };
    });
    return { hasLoadError, failText, svgs, imgs };
  });
}

async function gatherPlacements(page: Page): Promise<Placement[]> {
  const locators = await page.locator("[data-placement-name]").all();
  const placements: Placement[] = [];
  for (const locator of locators) {
    const name = await locator.getAttribute("data-placement-name");
    const bbox = await locator.boundingBox();
    placements.push({ name, bbox });
  }
  return placements;
}

async function gatherLabels(page: Page): Promise<LabelInfo[]> {
  const locators = await page.locator("[data-label]").all();
  const labels: LabelInfo[] = [];
  for (const locator of locators) {
    const bbox = await locator.boundingBox();
    const text = await locator.textContent();
    const labelFor = await locator.getAttribute("data-label-for");
    const styles = await checkComputedStyles(locator);
    labels.push({ bbox, text, labelFor, styles });
  }
  return labels;
}

//============================================
// Tests: one per discovered base scene
//============================================

test.describe("base scene generalization render", () => {
  // A base scene with zero discovered names would silently vacuous-pass an
  // empty test.describe; fail loudly instead so a broken discovery helper is
  // never mistaken for "every scene passed".
  test("at least one base scene was discovered", () => {
    expect(SCENES_TO_RENDER.length).toBeGreaterThan(0);
  });

  for (const sceneName of SCENES_TO_RENDER) {
    test(`${sceneName}: passes all render-integrity assertions`, async ({ page }) => {
      const routedReason = EXPECTED_FAIL_SCENES[sceneName];
      if (routedReason !== undefined) {
        test.fail(true, routedReason);
      }

      await page.goto(`/scene_viewer.html?scene=${sceneName}`, { waitUntil: "networkidle" });

      // Readiness: at least one placement rendered inside #scene-root.
      await expect(page.locator("#scene-root [data-placement-name]").first()).toBeVisible();

      const sceneRootBbox = await page.locator("#scene-root").boundingBox();
      expect(sceneRootBbox, "scene-root must report a bounding box").not.toBeNull();

      const placements = await gatherPlacements(page);
      const labels = await gatherLabels(page);
      expect(placements.length, `${sceneName} must render at least one placement`).toBeGreaterThan(
        0,
      );

      const placementLocators = await page.locator("[data-placement-name]").all();

      await test.step("A: no clipping/cropping", async () => {
        for (let i = 0; i < placements.length; i++) {
          const placement = placements[i]!;
          const styles = await checkComputedStyles(placementLocators[i]!);
          const clipped =
            styles.overflow === "hidden" ||
            styles.clipPath !== "none" ||
            styles.contain.includes("paint");
          expect(clipped, `placement ${placement.name} clipped`).toBe(false);
          expect(bboxContains(sceneRootBbox!, placement.bbox!)).toBe(true);
        }
      });

      await test.step("B: every placement renders complete SVG artwork", async () => {
        for (let i = 0; i < placements.length; i++) {
          const placement = placements[i]!;
          const info = await gatherPlacementAssetInfo(placementLocators[i]!);
          const hasContentSvg = info.svgs.some((s) => s.hasContent);
          const hasLoadedImg = info.imgs.some((im) => im.naturalWidth > 0 && im.naturalHeight > 0);
          const renderedNoAsset =
            info.hasLoadError || info.failText || (!hasContentSvg && !hasLoadedImg);
          expect(renderedNoAsset, `placement ${placement.name} rendered no valid asset`).toBe(
            false,
          );
        }
      });

      await test.step("C: aspect ratio preserved (both modes)", async () => {
        let evaluated = 0;
        for (const locator of placementLocators) {
          const info = await gatherPlacementAssetInfo(locator);
          for (const svgAsset of info.svgs) {
            if (!svgAsset.hasContent) continue;
            evaluated++;
            const par = (svgAsset.preserveAspectRatio ?? "").trim().toLowerCase();
            expect(
              par,
              "inline SVG must not stretch artwork via preserveAspectRatio=none",
            ).not.toBe("none");
          }
          for (const imgAsset of info.imgs) {
            evaluated++;
            const fitOk = imgAsset.objectFit === "contain" || imgAsset.objectFit === "scale-down";
            expect(fitOk, `img asset object-fit=${imgAsset.objectFit} distorts or crops`).toBe(
              true,
            );
          }
        }
        // A vacuous scene (zero aspect-bearing assets) must not read as green.
        expect(
          evaluated,
          `${sceneName} must have at least one aspect-bearing asset`,
        ).toBeGreaterThan(0);
      });

      await test.step("D: no item off-page", () => {
        for (const placement of placements) {
          expect(bboxContains(sceneRootBbox!, placement.bbox!)).toBe(true);
        }
      });

      await test.step("F: no item overlap", () => {
        for (let i = 0; i < placements.length; i++) {
          for (let j = i + 1; j < placements.length; j++) {
            const overlap = bboxsOverlap(
              placements[i]!.bbox!,
              placements[j]!.bbox!,
              OVERLAP_TOLERANCE,
            );
            expect(overlap, `${placements[i]!.name} and ${placements[j]!.name} overlap`).toBe(
              false,
            );
          }
        }
      });

      await test.step("G: no label outside scene", () => {
        for (const label of labels) {
          expect(label.bbox, "label has a bbox").not.toBeNull();
          expect(bboxContains(sceneRootBbox!, label.bbox!)).toBe(true);
        }
      });

      await test.step("H: no label-own-svg overlap", () => {
        // Ownership is the SIBLING relationship the renderer emits via
        // data-label-for, not an ancestor data-placement-name.
        let pairCount = 0;
        for (const label of labels) {
          if (!label.labelFor || !label.bbox) continue;
          const ownPlacement = placements.find((p) => p.name === label.labelFor);
          if (!ownPlacement || !ownPlacement.bbox) continue;
          pairCount++;
          expect(bboxsOverlap(label.bbox, ownPlacement.bbox)).toBe(false);
        }
        if (labels.length > 0) {
          expect(pairCount, "at least one label-own-art pair must be comparable").toBeGreaterThan(
            0,
          );
        }
      });

      await test.step("I: no label-label overlap", () => {
        for (let i = 0; i < labels.length; i++) {
          for (let j = i + 1; j < labels.length; j++) {
            const l1 = labels[i]!;
            const l2 = labels[j]!;
            if (!l1.bbox || !l2.bbox) continue;
            expect(bboxsOverlap(l1.bbox, l2.bbox, OVERLAP_TOLERANCE)).toBe(false);
          }
        }
      });

      await test.step("J: label readability (hard failures)", () => {
        for (const label of labels) {
          expect(label.text?.trim().length ?? 0).toBeGreaterThan(0);
          expect(label.styles.visibility).not.toBe("hidden");
          expect(label.styles.display).not.toBe("none");
          expect(parseFloat(label.styles.opacity)).not.toBe(0);
          const fontSizeMatch = label.styles.fontSize.match(/^([\d.]+)px$/);
          if (fontSizeMatch) {
            expect(parseFloat(fontSizeMatch[1]!)).toBeGreaterThanOrEqual(MIN_FONT_SIZE);
          }
        }
      });

      await test.step("K: no scene-specific branches in the bundle", () => {
        const bundlePath = path.join(REPO_ROOT, "dist/scene_viewer.js");
        expect(fs.existsSync(bundlePath), `${bundlePath} exists`).toBe(true);
        const bundleContent = fs.readFileSync(bundlePath, "utf8");
        const hasBranch = SCENES_TO_RENDER.some(
          (name) =>
            bundleContent.includes(`=== "${name}"`) || bundleContent.includes(`=== '${name}'`),
        );
        expect(hasBranch, "bundle must not branch on a literal scene name").toBe(false);
      });

      await page.screenshot({
        path: `test-results/generalization/${sceneName}.png`,
        fullPage: false,
      });
    });
  }
});
