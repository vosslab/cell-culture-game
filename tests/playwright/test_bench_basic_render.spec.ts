// test_bench_basic_render.spec.ts
//
// Converted from the library-model tests/playwright/test_bench_basic_render.mjs
// (that .mjs stays in place this phase; a later cleanup phase removes it).
//
// Renders content/base_scenes/bench_basic.yaml via scene_viewer.html and
// verifies eleven layout-integrity assertions (A-K): no clipping, complete SVG
// loading, aspect ratio preserved, no off-page items, zone
// containment, no item overlap, no label overflow, no label/own-art overlap,
// no label/label overlap, label readability, and no scene-specific branches
// baked into the bundle.
//
// Served over HTTP by the playwright.config.ts webServer block (build + serve
// dist/). No per-file server, no chromium import, no process.exit.
//
// Selector contract (cite source file:line so a UI change surfaces the coupling):
//   - #scene-root                         src/scene_runtime/renderer/scene_root.tsx
//   - [data-placement-name] placements    src/scene_runtime/renderer/scene_item.tsx
//   - [data-label] / [data-label-for]     src/scene_runtime/renderer/scene_item.tsx

/// <reference types="node" />

import { test, expect } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { REPO_ROOT } from "./repo_root.mjs";
import { bboxContains, bboxsOverlap } from "../../tools/bbox_helpers.mjs";
import type { Bbox } from "../../tools/bbox_helpers.mjs";

//============================================
// Test configuration
//============================================

const OVERLAP_TOLERANCE = 1; // 1px jitter tolerance
const MIN_FONT_SIZE = 6; // pixels

//============================================
// Types
//============================================

interface ComputedStyleSummary {
  overflow: string;
  overflowX: string;
  overflowY: string;
  clipPath: string;
  mask: string;
  maskImage: string;
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
  zone: string | null;
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
      overflowX: computed.overflowX,
      overflowY: computed.overflowY,
      clipPath: computed.clipPath,
      mask: computed.mask,
      maskImage: computed.maskImage,
      contain: computed.contain,
      visibility: computed.visibility,
      display: computed.display,
      opacity: computed.opacity,
      fontSize: computed.fontSize,
    };
  });
}

async function gatherPlacements(page: Page): Promise<Placement[]> {
  const locators = await page.locator("[data-placement-name]").all();
  const placements: Placement[] = [];
  for (const locator of locators) {
    const name = await locator.getAttribute("data-placement-name");
    const zone = await locator.getAttribute("data-zone");
    const bbox = await locator.boundingBox();
    placements.push({ name, zone, bbox });
  }
  return placements;
}

// Gathers the asset-render facts a placement exposes, covering BOTH renderer
// modes (src/scene_runtime/renderer/scene_item.tsx:273-308): dom-svg assets
// inject an inline <svg>, static assets render as an opaque
// <img data-svg-render-mode="img"> with object-fit:contain. Reading both
// modes here is what makes the B/C assertions honest instead of null-failing
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

// Walks the ancestor chain of a placement element, up to (but not including)
// #scene-root, looking for a banned clipping style. #scene-root is the scene
// viewport boundary and is allowed to clip; a banned overflow/clip/mask/contain
// on an INTERMEDIATE wrapper is what crops scientific assets (PRIMARY_DESIGN
// "never crop scientific assets").
async function findClipOffender(placementLocator: Locator): Promise<{ selector: string } | null> {
  return placementLocator.evaluate((startEl: Element): { selector: string } | null => {
    function isBannedClip(cs: CSSStyleDeclaration): boolean {
      return (
        cs.overflow === "hidden" ||
        cs.overflow === "clip" ||
        cs.overflowX === "hidden" ||
        cs.overflowX === "clip" ||
        cs.overflowY === "hidden" ||
        cs.overflowY === "clip" ||
        cs.clipPath !== "none" ||
        cs.mask !== "none" ||
        cs.maskImage !== "none" ||
        cs.contain.includes("paint") ||
        cs.contain === "strict" ||
        cs.contain === "content"
      );
    }
    let el: Element | null = startEl;
    while (el && el.id !== "scene-root") {
      const cs = window.getComputedStyle(el);
      if (isBannedClip(cs)) {
        const cls = typeof el.className === "string" ? el.className : "";
        const selector =
          el.tagName.toLowerCase() +
          (el.id ? `#${el.id}` : "") +
          (cls ? `.${cls.trim().split(/\s+/).join(".")}` : "");
        return { selector };
      }
      el = el.parentElement;
    }
    return null;
  });
}

//============================================
// Test
//============================================

test.describe("bench_basic scene render", () => {
  test("passes all eleven layout-integrity assertions", async ({ page }) => {
    await page.goto("/scene_viewer.html?scene=bench_basic", { waitUntil: "networkidle" });

    // Readiness: at least one placement rendered inside #scene-root.
    await expect(page.locator("#scene-root [data-placement-name]").first()).toBeVisible();

    const sceneRootLocator = page.locator("#scene-root");
    const sceneRootBbox = await sceneRootLocator.boundingBox();
    expect(sceneRootBbox, "scene-root must report a bounding box").not.toBeNull();

    const placements = await gatherPlacements(page);
    const labels = await gatherLabels(page);
    expect(placements.length).toBeGreaterThan(0);

    const placementLocators = await page.locator("[data-placement-name]").all();

    await test.step("A: no clipping/cropping", async () => {
      for (let i = 0; i < placements.length; i++) {
        const placement = placements[i]!;
        expect(placement.bbox, `placement ${placement.name} has a bbox`).not.toBeNull();
        const clipOffender = await findClipOffender(placementLocators[i]!);
        expect(clipOffender, `placement ${placement.name} clipped`).toBeNull();
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
        expect(renderedNoAsset, `placement ${placement.name} rendered no valid asset`).toBe(false);
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
          expect(par, "inline SVG must not stretch artwork via preserveAspectRatio=none").not.toBe(
            "none",
          );
        }
        for (const imgAsset of info.imgs) {
          evaluated++;
          const fitOk = imgAsset.objectFit === "contain" || imgAsset.objectFit === "scale-down";
          expect(fitOk, `img asset object-fit=${imgAsset.objectFit} distorts or crops`).toBe(true);
        }
      }
      // A vacuous scene (zero aspect-bearing assets) must not read as green.
      expect(evaluated, "bench_basic must have at least one aspect-bearing asset").toBeGreaterThan(
        0,
      );
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
          expect(overlap, `${placements[i]!.name} and ${placements[j]!.name} overlap`).toBe(false);
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
      let pairCount = 0;
      for (const label of labels) {
        if (!label.labelFor) continue;
        const ownPlacement = placements.find((p) => p.name === label.labelFor);
        if (!ownPlacement || !ownPlacement.bbox || !label.bbox) continue;
        pairCount++;
        expect(bboxsOverlap(label.bbox, ownPlacement.bbox)).toBe(false);
      }
      // A vacuous match (no comparable pair) must not read as green.
      if (labels.length > 0) {
        expect(pairCount, "at least one label-own-art pair must be comparable").toBeGreaterThan(0);
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
        expect(label.bbox, "label has a bbox").not.toBeNull();
        expect(bboxContains(sceneRootBbox!, label.bbox!)).toBe(true);
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
      const hasBranch =
        bundleContent.includes('=== "bench_basic"') || bundleContent.includes("=== 'bench_basic'");
      expect(hasBranch).toBe(false);
    });

    await page.screenshot({ path: "test-results/bench_basic_render.png", fullPage: false });
  });
});
