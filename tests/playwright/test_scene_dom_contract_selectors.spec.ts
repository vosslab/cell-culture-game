// test_scene_dom_contract_selectors.spec.ts
//
// Converted from the library-model tests/playwright/test_scene_dom_contract_selectors.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
//
// Scene DOM contract selector tests (WS-M1-T). Served over HTTP by the
// playwright.config.ts webServer block (build + serve dist/). No per-file
// server, no chromium import, no process.exit.
//
// Asserts contractual data-* attributes on the current renderer output.
// Tests the CONTRACTUAL selectors (frozen as interface):
//   - data-item-id        (walker-addressable identity; present ONLY when the
//                          object's declared capabilities include "clickable",
//                          per M6 "Enforce capabilities in renderer and
//                          candidate enumeration")
//   - data-object-name    (object YAML name)
//   - data-placement-name (scene placement key)
//   - data-zone           (zone name)
//   - data-kind           (object kind enum)
//   - data-depth          (depth tier enum; conditionally present)
//   - data-asset          (asset registry key)
//   - data-label          (present on every label element)
//   - data-label-for      (ties label to placement_name)
//
// INCIDENTAL (not tested here, change freely without breaking contract):
//   - Internal wrapper div nesting depth
//   - CSS class names on item divs
//   - Style properties other than position (left/top/width/height)
//   - z-index values
//   - Internal SVG structure below the top-level <svg> element
//
// This test uses bench_basic as the canonical scene for selector coverage.
// It then spot-checks one protocol scene (hood_workspace) for multi-scene
// coverage.
//
// Selector contract (cite source file:line so a UI change surfaces the coupling):
//   - [data-placement-name], [data-item-id], [data-object-name], [data-zone],
//     [data-kind], [data-depth], [data-asset]
//     src/scene_runtime/renderer/scene_item.tsx
//   - [data-label], [data-label-for]  src/scene_runtime/renderer/scene_item.tsx
//   - #scene-root[data-viewer-ready]  src/dist_entry.tsx

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

//============================================
// Closed enum sets (contractual)
//============================================

const VALID_KINDS = new Set([
  "bottle",
  "equipment",
  "plate",
  "tube",
  "decoration",
  "pipette",
  "rack",
  "waste",
  "flask",
]);

const VALID_DEPTHS = new Set(["back", "mid", "front"]);

//============================================
// Types
//============================================

interface RenderedItem {
  placementName: string | null;
  objectName: string | null;
  itemId: string | null;
  zone: string | null;
  kind: string | null;
  depth: string | null;
  asset: string | null;
  hasInlineSvg: boolean;
  hasLoadedStaticSvg: boolean;
}

interface RenderedLabel {
  labelFor: string | null;
  hasText: boolean;
}

//============================================
// Load a scene via the scene_viewer, relative to the config baseURL.
//============================================

async function loadScene(page: Page, sceneName: string): Promise<void> {
  const url = `/scene_viewer.html?scene=${encodeURIComponent(sceneName)}`;
  await page.goto(url, { waitUntil: "load" });
  await page.locator("#scene-root[data-viewer-ready='true']").waitFor({ state: "attached" });
}

//============================================
// Core selector contract assertions for one scene
//============================================

async function assertSceneSelectorContract(page: Page, sceneName: string): Promise<void> {
  const items: RenderedItem[] = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("[data-placement-name]"));
    return els.map((el) => {
      const domSvgHost = el.querySelector('[data-svg-render-mode="dom-svg"]');
      const staticImage = el.querySelector<HTMLImageElement>('img[data-svg-render-mode="img"]');
      return {
        placementName: el.getAttribute("data-placement-name"),
        objectName: el.getAttribute("data-object-name"),
        itemId: el.getAttribute("data-item-id"),
        zone: el.getAttribute("data-zone"),
        kind: el.getAttribute("data-kind"),
        depth: el.getAttribute("data-depth"),
        asset: el.getAttribute("data-asset"),
        hasInlineSvg: (domSvgHost?.querySelector("svg") ?? null) !== null,
        hasLoadedStaticSvg:
          staticImage !== null &&
          staticImage.complete &&
          staticImage.naturalWidth > 0 &&
          staticImage.naturalHeight > 0,
      };
    });
  });

  expect(items.length, `${sceneName}: at least one rendered item`).toBeGreaterThan(0);

  // Declared scene zones (pipeline-truth) the viewer stashes on window. Every
  // item's data-zone must be one of these: the geometry dump groups rendered
  // item boxes by data-zone into each declared zone's item_union_rect, so an
  // item whose data-zone matches no declared zone would silently drop out of
  // every union. Assert the membership contract here.
  const declaredZones: string[] | null = await page.evaluate(() => {
    const geo = (window as unknown as { __SCENE_GEOMETRY__?: { zones: { name: string }[] } })
      .__SCENE_GEOMETRY__;
    if (!geo) return null;
    return geo.zones.map((z) => z.name);
  });
  expect(
    Array.isArray(declaredZones) && declaredZones.length > 0,
    `${sceneName}: window.__SCENE_GEOMETRY__ declares at least one zone`,
  ).toBe(true);
  const declaredZoneSet = new Set(declaredZones ?? []);
  for (const item of items) {
    expect(
      declaredZoneSet.has(item.zone ?? ""),
      `${sceneName}[${String(item.placementName)}]: data-zone "${String(item.zone)}" is a declared scene zone`,
    ).toBe(true);
  }

  const labels: RenderedLabel[] = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("[data-label]"));
    return els.map((el) => ({
      labelFor: el.getAttribute("data-label-for"),
      hasText: (el.textContent ?? "").trim().length > 0,
    }));
  });

  const placementNameSet = new Set(items.map((item) => item.placementName));

  for (const item of items) {
    const id = item.placementName ?? "(no-placement-name)";

    expect(
      typeof item.placementName === "string" && item.placementName.length > 0,
      `${sceneName}[${id}]: data-placement-name non-empty`,
    ).toBe(true);

    // data-item-id: when present, non-empty (walker-addressable identity).
    // Absent entirely on a non-clickable item (decoration_only capability, or
    // an internal render-error item bound with capabilities: []).
    if (item.itemId !== null) {
      expect(
        item.itemId.length,
        `${sceneName}[${id}]: data-item-id non-empty when present`,
      ).toBeGreaterThan(0);
    }

    expect(
      typeof item.objectName === "string" && item.objectName.length > 0,
      `${sceneName}[${id}]: data-object-name non-empty`,
    ).toBe(true);

    expect(
      typeof item.zone === "string" && item.zone.length > 0,
      `${sceneName}[${id}]: data-zone non-empty`,
    ).toBe(true);

    expect(
      typeof item.kind === "string" && VALID_KINDS.has(item.kind),
      `${sceneName}[${id}]: data-kind in closed enum (got "${String(item.kind)}")`,
    ).toBe(true);

    // data-depth: when present, in closed enum.
    if (item.depth !== null) {
      expect(
        VALID_DEPTHS.has(item.depth),
        `${sceneName}[${id}]: data-depth in closed enum when present (got "${item.depth}")`,
      ).toBe(true);
    }

    expect(
      typeof item.asset === "string" && item.asset.length > 0,
      `${sceneName}[${id}]: data-asset non-empty`,
    ).toBe(true);

    // Every generated scene item renders through one of the two real-art modes.
    expect(
      item.hasInlineSvg || item.hasLoadedStaticSvg,
      `${sceneName}[${id}]: item has inline SVG or loaded static SVG image`,
    ).toBe(true);
  }

  expect(labels.length, `${sceneName}: at least one label`).toBeGreaterThan(0);
  for (const label of labels) {
    expect(
      label.labelFor !== null && placementNameSet.has(label.labelFor),
      `${sceneName}: data-label-for="${String(label.labelFor)}" references a known placement`,
    ).toBe(true);
    expect(
      label.hasText,
      `${sceneName}: label[for=${String(label.labelFor)}] has text content`,
    ).toBe(true);
  }
}

//============================================
// Tests
//============================================

test.describe("scene DOM contract selectors", () => {
  test("bench_basic: contractual attribute coverage", async ({ page }) => {
    // Suppress expected console noise from scene operations stubs.
    page.on("console", () => {});

    await loadScene(page, "bench_basic");
    await assertSceneSelectorContract(page, "bench_basic");
  });

  test("hood_workspace: multi-scene selector coverage", async ({ page }) => {
    page.on("console", () => {});

    await loadScene(page, "hood_workspace");
    await assertSceneSelectorContract(page, "hood_workspace");
  });
});
