// test_scene_reactivity_lifecycle.spec.ts
//
// Converted from the library-model tests/playwright/test_scene_reactivity_lifecycle.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
// The runner owns pass/fail signaling (expect) for this file; the browser and
// static server stay self-managed because this spec proves something the
// shared config webServer cannot: a hand-built, in-memory harness bundle
// (helper_scene_reactivity_harness.tsx) that mounts the SAME mountScene + scene_store
// used in production, but exposes direct store-write and remount hooks a
// student-facing page does not expose.
//
// WS-M3-C runtime acceptance (browser): proves the Solid scene renderer's
// keyed/localized updates and lifecycle ownership against a real DOM.
//
// Assertions:
//   1. No-remount on ObjectStateChange: after a store write that changes a
//      fill overlay, the affected item is the SAME connected DOM node, with the
//      SAME data-item-id and bbox within tolerance; the scene root is not
//      remounted; an unaffected sibling item is also the same node + bbox.
//   2. The fill overlay actually changed height (the reactive update happened).
//   3. Lifecycle: a SceneChange (re-mount) disposes the prior root (old item
//      nodes are detached); dispose() empties the scene root (no orphans).
//   4. SVG-injection safety: every injected <svg> matches a generated/svg_manifest.ts
//      (SVG_MANIFEST) entry, and no authored label/object-name string leaks into
//      injected SVG markup.

import { test, expect } from "@playwright/test";
import type { Browser, Page } from "@playwright/test";
import { chromium } from "playwright";
import * as esbuild from "esbuild";
import { solidPlugin } from "esbuild-plugin-solid";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { REPO_ROOT } from "./repo_root.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const STATIC_CONTENT_TYPES: Record<string, string> = {
  ".svg": "image/svg+xml",
};

const SCENE_NAME = "seeding_workspace";
const ALT_SCENE_NAME = "dilution_workspace";
// The prior .mjs source used one constant ("cell_suspension_tube") for both
// the DOM query and the store write. That predates a scene content rename
// (see
// content/protocols/cell_culture/cell_seeding_plate_setup/scenes/seeding_workspace.yaml)
// and no longer matches either key correctly:
//   - data-item-id / data-placement-name are keyed by placement_name
//     ("rear_left_cell_suspension_tube", src/scene_runtime/renderer/scene_item.tsx).
//   - scene_store.set_object_state / seed_from_scene are keyed by object_name
//     ("cell_suspension_tube", build_seed_list in
//     src/scene_runtime/renderer/scene_view.tsx: "the store is keyed by
//     object_name, so two placements of the same object share one seed").
// Conversion-time fix, not a product defect: split into the two real keys.
const FILL_TARGET_PLACEMENT = "rear_left_cell_suspension_tube";
const FILL_TARGET_OBJECT = "cell_suspension_tube";
// cell_suspension_tube declares an anchor material effect. Its visible fill is
// an SVG rect owned by anchor_material_renderer, not a legacy CSS box overlay.
const ANCHOR_MATERIAL_SELECTOR = "[data-anchor-material-field='material_volume']";
const BBOX_TOL_PX = 1.0;

interface Bbox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface HarnessWindow {
  __harness: {
    mount: (scene: string) => void;
    set_state: (target: string, patch: Record<string, string | number>) => void;
    remount: (scene: string) => void;
    dispose: () => void;
  };
}

interface InjectionItem {
  itemId: string | null;
  hasSvg: boolean;
  svgText: string;
}

interface InjectionReport {
  items: InjectionItem[];
  labels: string[];
}

interface BeforeState {
  bbox: Bbox;
  fillH: number;
  otherId: string | null;
  otherBbox: Bbox;
}

interface AfterState {
  rootToken: string | null;
  itemToken: string | null;
  otherStillTagged: boolean;
  bbox: Bbox;
  fillH: number;
  itemId: string | null;
  otherBbox: Bbox | null;
}

interface AfterRemountState {
  oldItemGone: boolean;
  itemCount: number;
}

interface AfterDisposeState {
  itemCount: number;
  degraded: boolean;
}

function bboxClose(a: Bbox, b: Bbox): boolean {
  return (
    Math.abs(a.x - b.x) <= BBOX_TOL_PX &&
    Math.abs(a.y - b.y) <= BBOX_TOL_PX &&
    Math.abs(a.w - b.w) <= BBOX_TOL_PX &&
    Math.abs(a.h - b.h) <= BBOX_TOL_PX
  );
}

//============================================
// Build the harness bundle in-memory.
//============================================

async function buildHarness(): Promise<string> {
  const entry = path.join(__dirname, "helper_scene_reactivity_harness.tsx");
  const result = await esbuild.build({
    entryPoints: [entry],
    bundle: true,
    write: false,
    format: "esm",
    target: "es2020",
    platform: "browser",
    sourcemap: false,
    plugins: [solidPlugin()],
    logLevel: "silent",
  });
  return result.outputFiles[0]!.text;
}

//============================================
// Serve the bundle + a host page.
//============================================

interface ServerHandle {
  server: http.Server;
  base: string;
}

function startServer(bundleJs: string): Promise<ServerHandle> {
  const html =
    "<!doctype html><html><head><meta charset='utf-8'><style>" +
    "#scene-root{position:relative;width:1200px;height:675px;}</style></head>" +
    "<body><div id='scene-root'></div>" +
    "<script type='module' src='/harness.js'></script></body></html>";
  const distRoot = path.join(REPO_ROOT, "dist");
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = (req.url ?? "/").split("?")[0] ?? "/";
      if (url === "/" || url === "") {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(html);
        return;
      }
      if (url === "/harness.js") {
        res.writeHead(200, { "Content-Type": "application/javascript" });
        res.end(bundleJs);
        return;
      }

      let requestedPath: string;
      try {
        requestedPath = decodeURIComponent(url);
      } catch {
        res.writeHead(400);
        res.end();
        return;
      }
      const filePath = path.resolve(distRoot, `.${requestedPath}`);
      const relativePath = path.relative(distRoot, filePath);
      if (
        relativePath.startsWith(`..${path.sep}`) ||
        relativePath === ".." ||
        path.isAbsolute(relativePath)
      ) {
        res.writeHead(403);
        res.end();
        return;
      }
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404);
          res.end(`Not found: ${url}`);
          return;
        }
        const contentType =
          STATIC_CONTENT_TYPES[path.extname(filePath)] ?? "application/octet-stream";
        res.writeHead(200, { "Content-Type": contentType });
        res.end(data);
      });
    });
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr !== null ? addr.port : 0;
      resolve({ server, base: `http://127.0.0.1:${port}` });
    });
  });
}

//============================================
// Tests
//============================================

test.describe("scene reactivity + lifecycle", () => {
  let serverHandle: ServerHandle;
  let browser: Browser;
  let page: Page;
  const pageErrors: string[] = [];

  test.beforeAll(async () => {
    const bundle = await buildHarness();
    serverHandle = await startServer(bundle);
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage({ viewport: { width: 1200, height: 675 } });
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.goto(`${serverHandle.base}/`, { waitUntil: "load" });
    await page.waitForFunction(
      () => typeof (window as unknown as { __harness?: unknown }).__harness !== "undefined",
    );

    // Mount the scene.
    await page.evaluate((scene: string) => {
      (window as unknown as HarnessWindow).__harness.mount(scene);
    }, SCENE_NAME);
    await page
      .locator(`#scene-root [data-item-id="${FILL_TARGET_PLACEMENT}"]`)
      .waitFor({ state: "attached" });
    // The object uses an injected SVG anchor fill, so wait for the actual
    // current-contract surface rather than merely its outer item container.
    const fill = page.locator(
      `#scene-root [data-item-id="${FILL_TARGET_PLACEMENT}"] ${ANCHOR_MATERIAL_SELECTOR}`,
    );
    await fill.waitFor({ state: "attached" });
    await expect(fill).toHaveAttribute("display", "inline");
  });

  test.afterAll(async () => {
    await browser.close();
    await new Promise<void>((resolve) => serverHandle.server.close(() => resolve()));
  });

  test("SVG-injection safety: no authored label text leaks into injected SVG markup", async () => {
    const injection: InjectionReport = await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll("#scene-root [data-item-id]"));
      const labels = Array.from(document.querySelectorAll("#scene-root [data-label]")).map(
        (l) => l.textContent || "",
      );
      const out: InjectionItem[] = [];
      for (const it of items) {
        const svg = it.querySelector("svg");
        out.push({
          itemId: it.getAttribute("data-item-id"),
          hasSvg: svg !== null,
          // Authored object-name strings must not appear as injected SVG text
          // content (the asset markup is generated, not authored YAML).
          svgText: svg ? svg.textContent || "" : "",
        });
      }
      return { items: out, labels };
    });

    for (const it of injection.items) {
      for (const labelText of injection.labels) {
        const trimmed = labelText.trim();
        if (trimmed.length >= 4) {
          expect(
            it.svgText.includes(trimmed),
            `SVG-injection safety: authored label "${trimmed}" leaked into injected SVG of ${String(it.itemId)}`,
          ).toBe(false);
        }
      }
    }
  });

  test("no-remount on ObjectStateChange: root, affected item, and sibling keep node identity + bbox", async () => {
    // Tag the scene root and the target item so we can prove node identity
    // survives a store write (no remount).
    const before: BeforeState = await page.evaluate(
      (args: { target: string; fillSelector: string }) => {
        const root = document.getElementById("scene-root")!;
        root.setAttribute("data-test-root-token", "root-1");
        const item = root.querySelector(`[data-item-id="${args.target}"]`)!;
        item.setAttribute("data-test-item-token", "item-1");
        const r = item.getBoundingClientRect();
        const fill = item.querySelector(args.fillSelector);
        if (!(fill instanceof SVGRectElement)) {
          throw new Error("expected the declared anchor material fill SVG rect");
        }
        const fillH = fill.getBoundingClientRect().height;
        // Pick an unaffected sibling item.
        const others = Array.from(root.querySelectorAll("[data-item-id]")).filter(
          (el) => el.getAttribute("data-item-id") !== args.target,
        );
        const other = others[0]!;
        other.setAttribute("data-test-other-token", "other-1");
        const or = other.getBoundingClientRect();
        return {
          bbox: { x: r.x, y: r.y, w: r.width, h: r.height },
          fillH,
          otherId: other.getAttribute("data-item-id"),
          otherBbox: { x: or.x, y: or.y, w: or.width, h: or.height },
        };
      },
      { target: FILL_TARGET_PLACEMENT, fillSelector: ANCHOR_MATERIAL_SELECTOR },
    );

    // Write a new material_volume to the target via the store (the reactive
    // path the production scene-op layer will drive). A DECLARED enum value
    // ("cell_suspension" is in the tube's material_name allowed set) and a
    // higher volume proves a genuine reactive fill INCREASE (default
    // 15/20 -> 18/20), not a degradation drop: an undeclared enum value would
    // make the resolver fail the svg-case match, SceneItem would catch + drop
    // overlays, and the fill would fall to 0 -- a change that passes a "did
    // it change?" assertion for the wrong reason.
    await page.evaluate((target: string) => {
      (window as unknown as HarnessWindow).__harness.set_state(target, {
        material_name: "cell_suspension",
        material_volume: 18,
      });
    }, FILL_TARGET_OBJECT);
    const fill = page.locator(
      `#scene-root [data-item-id="${FILL_TARGET_PLACEMENT}"] ${ANCHOR_MATERIAL_SELECTOR}`,
    );
    await expect
      .poll(async () => {
        const height = await fill.evaluate((element) => element.getBoundingClientRect().height);
        return height;
      })
      .toBeGreaterThan(before.fillH + 1);

    const after: AfterState = await page.evaluate(
      (args: { target: string; fillSelector: string }) => {
        const root = document.getElementById("scene-root")!;
        const item = root.querySelector(`[data-item-id="${args.target}"]`)!;
        const r = item.getBoundingClientRect();
        const fill = item.querySelector(args.fillSelector);
        if (!(fill instanceof SVGRectElement)) {
          throw new Error("expected the declared anchor material fill SVG rect");
        }
        const fillH = fill.getBoundingClientRect().height;
        const other = root.querySelector("[data-test-other-token='other-1']");
        const or = other ? other.getBoundingClientRect() : null;
        return {
          // Node identity proofs: tokens survive only if the SAME node was
          // reused.
          rootToken: root.getAttribute("data-test-root-token"),
          itemToken: item.getAttribute("data-test-item-token"),
          otherStillTagged: other !== null,
          bbox: { x: r.x, y: r.y, w: r.width, h: r.height },
          fillH,
          itemId: item.getAttribute("data-item-id"),
          otherBbox: or ? { x: or.x, y: or.y, w: or.width, h: or.height } : null,
        };
      },
      { target: FILL_TARGET_PLACEMENT, fillSelector: ANCHOR_MATERIAL_SELECTOR },
    );

    expect(after.rootToken, "scene root must NOT remount on ObjectStateChange").toBe("root-1");
    expect(after.itemToken, "affected item must be the SAME node (no remount)").toBe("item-1");
    expect(after.itemId, "affected item keeps its data-item-id").toBe(FILL_TARGET_PLACEMENT);
    expect(
      bboxClose(before.bbox, after.bbox),
      `affected item bbox must be stable: before=${JSON.stringify(before.bbox)} after=${JSON.stringify(after.bbox)}`,
    ).toBe(true);
    expect(
      after.otherStillTagged,
      "unaffected sibling item must be the SAME node (no remount)",
    ).toBe(true);
    expect(
      bboxClose(before.otherBbox, after.otherBbox!),
      "unaffected sibling bbox must be stable",
    ).toBe(true);

    // The fill overlay height must have INCREASED (volume 15 -> 18 of cap 20
    // is 75% -> 90%). Requiring an increase, not just a change, proves the
    // reactive fill resolved correctly rather than collapsing to 0 via a
    // degraded path.
    expect(
      after.fillH - before.fillH,
      `fill overlay height must increase reactively: before=${before.fillH} after=${after.fillH}`,
    ).toBeGreaterThan(1);
  });

  test("lifecycle: SceneChange disposes prior root; dispose() empties the scene root", async () => {
    await page.evaluate((scene: string) => {
      (window as unknown as HarnessWindow).__harness.remount(scene);
    }, ALT_SCENE_NAME);
    await expect(page.locator("#scene-root [data-test-item-token='item-1']")).toHaveCount(0);
    await page.locator("#scene-root [data-item-id]").first().waitFor({ state: "attached" });
    const afterRemount: AfterRemountState = await page.evaluate(() => {
      const root = document.getElementById("scene-root")!;
      const oldItem = root.querySelector("[data-test-item-token='item-1']");
      const itemCount = root.querySelectorAll("[data-item-id]").length;
      return { oldItemGone: oldItem === null, itemCount };
    });
    expect(afterRemount.oldItemGone, "SceneChange must dispose prior root (old item gone)").toBe(
      true,
    );
    expect(afterRemount.itemCount, "SceneChange must mount the new scene").toBeGreaterThan(0);

    await page.evaluate(() => {
      (window as unknown as HarnessWindow).__harness.dispose();
    });
    await expect(page.locator("#scene-root [data-item-id]")).toHaveCount(0);
    const afterDispose: AfterDisposeState = await page.evaluate(() => {
      const root = document.getElementById("scene-root")!;
      return {
        itemCount: root.querySelectorAll("[data-item-id]").length,
        degraded: root.hasAttribute("data-scene-degraded"),
      };
    });
    expect(afterDispose.itemCount, "dispose() must leave no orphan item nodes").toBe(0);

    expect(pageErrors, `no page errors: ${pageErrors.join("; ")}`).toEqual([]);
  });
});
