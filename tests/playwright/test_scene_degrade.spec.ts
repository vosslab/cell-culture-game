// test_scene_degrade.spec.ts
//
// Converted from the library-model tests/playwright/test_scene_degrade.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
// The runner owns pass/fail signaling (expect) for this file; the browser and
// static server stay self-managed because this spec proves something the
// shared config webServer cannot: a hand-built, in-memory harness bundle that
// injects synthetic test-only objects into OBJECT_LIBRARY at runtime.
//
// Browser regression test for the fail-loud degrade path (FIX 3 audit fix),
// exercised THROUGH THE PRODUCTION RENDER PATH (mountScene -> SceneView ->
// SceneItem).
//
// Background: the Solid renderer's SceneItem component was changed so a
// visual_state RESOLVER FAILURE no longer silently returns null. When
// resolve_visual_state throws (e.g. an unknown formula token), SceneItem:
//   - console.warns loud,
//   - stamps data-resolver-degraded="<message>" on the item node,
//   - notifies SceneView, which sets data-scene-degraded="true" on the scene
//     root ON FIRST RENDER (ordering-independent; no closest()/onMount race),
//   - degrades to the item's bound asset (renders SOMETHING, never blank).
//
// Ordering history: the old harness mounted bare SceneItem nodes and manually
// stamped data-scene-root before rendering. That masked the SceneView onMount
// vs child-effect ordering this test is meant to verify. The harness mounts a
// hand-built clean PipelineResult through the SAME mountScene + SceneView used
// in production, with ZERO structural violations, so a data-scene-degraded can
// only come from the resolver-promotion path -- and the FIRST-RENDER assertion
// below proves it lands without any state write.
//
// The harness (helper_degrade_harness.tsx) injects two synthetic objects into
// OBJECT_LIBRARY at runtime:
//   - test_degrade_obj: valid state_schema but unknown formula token ("badtoken")
//     that causes parse_formula_expr to throw.
//   - test_happy_obj: valid state_schema AND well-formed fill_height formula
//     that resolves cleanly.
//
// Assertions:
//   FIRST RENDER: immediately after mount() returns (no state write, no settle),
//     the scene root already carries data-scene-degraded="true" and the degrade
//     item already carries data-resolver-degraded.
//   DEGRADE path: item renders (not removed), carries data-resolver-degraded,
//     scene root carries data-scene-degraded="true", with NO structural
//     violation marker (data-degraded-violation-count absent).
//   HAPPY path:   item renders, does NOT carry data-resolver-degraded.
//   DISPOSE:      clears data-scene-degraded + data-scene-root, no orphan nodes.

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

// Maps the file extensions the harness page fetches to their MIME types. The
// harness only ever fetches SVG assets (via the manifest-driven svg loader),
// so this stays a small closed set rather than a general-purpose mime table.
const STATIC_CONTENT_TYPES: Record<string, string> = {
  ".svg": "image/svg+xml",
};

interface FirstRenderState {
  sceneDegraded: string | null;
  violationCount: string | null;
  sceneRoot: string | null;
  itemDegraded: string | null;
  itemExists: boolean;
}

interface DegradeState {
  exists: boolean;
  hasSvg: boolean;
  degradedAttr: string | null;
  assetAttr: string | null;
}

interface HappyState {
  exists: boolean;
  degradedAttr: string | null;
  assetAttr: string | null;
}

interface DisposeState {
  sceneDegraded: string | null;
  sceneRoot: string | null;
  childCount: number;
}

interface DegradeHarnessWindow {
  __degrade_harness: {
    mount: () => void;
    dispose: () => void;
  };
}

//============================================
// Build the degrade harness bundle in-memory.
//============================================

async function buildHarness(): Promise<string> {
  const entry = path.join(__dirname, "helper_degrade_harness.tsx");
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
  // #scene-root is the scene mount container. mountScene renders SceneView into
  // it; SceneView stamps data-scene-root and reactively owns data-scene-degraded.
  // Sized 1200x675 to match the viewport the harness passes to mountScene so the
  // aspect structural guard stays clean.
  const html =
    "<!doctype html><html><head><meta charset='utf-8'><style>" +
    "#scene-root{position:relative;width:1200px;height:675px;}" +
    "</style></head><body>" +
    "<div id='scene-root'></div>" +
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
      // The harness's SVG loader (svg_manifest_loader.ts) fetches real asset
      // files (e.g. "/assets/svg/equipment/waste_container.svg") by the same
      // relative path the built site serves under dist/. Serve those from the
      // real dist/ output rather than falling back to the harness HTML: a
      // fallback-to-HTML 200 previously masked a missing asset as fetch
      // "success", producing HTML text where SVG markup was expected.
      const filePath = path.join(distRoot, url);
      if (!filePath.startsWith(distRoot)) {
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
        const ext = path.extname(filePath);
        const contentType = STATIC_CONTENT_TYPES[ext] ?? "application/octet-stream";
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

test.describe("scene degrade DOM contract", () => {
  let serverHandle: ServerHandle;
  let browser: Browser;
  let page: Page;
  const consoleWarns: string[] = [];
  const pageErrors: string[] = [];

  test.beforeAll(async () => {
    const bundle = await buildHarness();
    serverHandle = await startServer(bundle);
    browser = await chromium.launch({ headless: true });
    page = await browser.newPage({ viewport: { width: 1200, height: 675 } });

    page.on("pageerror", (e) => pageErrors.push(e.message));
    // Capture console.warn so we can assert the warn was emitted.
    page.on("console", (msg) => {
      if (msg.type() === "warning") {
        consoleWarns.push(msg.text());
      }
    });

    await page.goto(`${serverHandle.base}/`, { waitUntil: "load" });
    await page.waitForFunction(
      () =>
        typeof (window as unknown as { __degrade_harness?: unknown }).__degrade_harness !==
        "undefined",
    );
  });

  test.afterAll(async () => {
    await browser.close();
    await new Promise<void>((resolve) => serverHandle.server.close(() => resolve()));
  });

  test("FIRST-RENDER: scene root carries data-scene-degraded on mount, no structural violation", async () => {
    // Mount through production mountScene and capture the DOM state
    // SYNCHRONOUSLY in the same evaluate, right after mount() returns: no
    // state write, no settle timeout. This proves the scene-degraded marker
    // lands on FIRST render via the SceneView-owned reactive path, not only
    // after a later state change (the regression the old harness could not
    // catch).
    const firstRender: FirstRenderState = await page.evaluate((name: string) => {
      (window as unknown as DegradeHarnessWindow).__degrade_harness.mount();
      const root = document.getElementById("scene-root");
      const item = document.querySelector(`[data-placement-name="${name}"]`);
      return {
        sceneDegraded: root ? root.getAttribute("data-scene-degraded") : null,
        violationCount: root ? root.getAttribute("data-degraded-violation-count") : null,
        sceneRoot: root ? root.getAttribute("data-scene-root") : null,
        itemDegraded: item ? item.getAttribute("data-resolver-degraded") : null,
        itemExists: item !== null,
      };
    }, "test_degrade_obj");

    expect(firstRender.itemExists, "FIRST-RENDER: degrade item must be present").toBe(true);
    expect(firstRender.sceneRoot, "FIRST-RENDER: scene root must carry data-scene-root=true").toBe(
      "true",
    );
    expect(
      firstRender.violationCount,
      "FIRST-RENDER: scene must have NO structural violations (clean harness scene)",
    ).toBeNull();
    expect(
      firstRender.itemDegraded !== null && firstRender.itemDegraded.length > 0,
      "FIRST-RENDER: degrade item must carry data-resolver-degraded on first render",
    ).toBe(true);
    expect(
      firstRender.sceneDegraded,
      "FIRST-RENDER: scene root must carry data-scene-degraded=true on FIRST render via the resolver-promotion path (ordering-independent)",
    ).toBe("true");

    // Allow Solid to flush effects, then re-assert the steady state in the
    // following tests.
    await page.waitForTimeout(100);
  });

  test("DEGRADE path: item renders its bound asset, degraded, scene root marked, console.warn emitted", async () => {
    const degradeState: DegradeState = await page.evaluate((name: string) => {
      const item = document.querySelector(`[data-placement-name="${name}"]`);
      if (!item) {
        return { exists: false, hasSvg: false, degradedAttr: null, assetAttr: null };
      }
      const svg = item.querySelector("svg");
      return {
        exists: true,
        // The Show(when=asset_name) always has a truthy string (the bound
        // asset), so an <svg> should be injected via injectSvgFromManifest.
        hasSvg: svg !== null,
        degradedAttr: item.getAttribute("data-resolver-degraded"),
        assetAttr: item.getAttribute("data-asset"),
      };
    }, "test_degrade_obj");

    expect(degradeState.exists, "DEGRADE: item must be present in the DOM (not removed)").toBe(
      true,
    );
    expect(
      degradeState.degradedAttr !== null && degradeState.degradedAttr.length > 0,
      "DEGRADE: item must carry data-resolver-degraded with a message",
    ).toBe(true);
    expect(
      degradeState.assetAttr !== null && degradeState.assetAttr.length > 0,
      "DEGRADE: item must carry data-asset (bound asset, not blank)",
    ).toBe(true);
    expect(degradeState.hasSvg, "DEGRADE: item must render its bound asset SVG (never blank)").toBe(
      true,
    );

    const sceneDegraded = await page.evaluate(() => {
      const root = document.getElementById("scene-root");
      return root ? root.getAttribute("data-scene-degraded") : null;
    });
    expect(sceneDegraded, "DEGRADE: [data-scene-root] must carry data-scene-degraded=true").toBe(
      "true",
    );

    const warnForDegrade = consoleWarns.some(
      (w) => w.includes("test_degrade_obj") && w.includes("degraded"),
    );
    expect(
      warnForDegrade,
      `DEGRADE: expected a console.warn mentioning "test_degrade_obj" and "degraded"; got: ${JSON.stringify(consoleWarns)}`,
    ).toBe(true);
  });

  test("HAPPY path: item renders without any degrade marker", async () => {
    const happyState: HappyState = await page.evaluate((name: string) => {
      const item = document.querySelector(`[data-placement-name="${name}"]`);
      if (!item) {
        return { exists: false, degradedAttr: null, assetAttr: null };
      }
      return {
        exists: true,
        degradedAttr: item.getAttribute("data-resolver-degraded"),
        assetAttr: item.getAttribute("data-asset"),
      };
    }, "test_happy_obj");

    expect(happyState.exists, "HAPPY: item must be present in the DOM").toBe(true);
    expect(happyState.degradedAttr, "HAPPY: item must NOT carry data-resolver-degraded").toBeNull();
    expect(
      happyState.assetAttr !== null && happyState.assetAttr.length > 0,
      "HAPPY: item must carry data-asset",
    ).toBe(true);

    // Screenshot evidence, captured before dispose so it shows the rendered,
    // degraded-but-not-blank scene.
    await page.screenshot({ path: "test-results/test_scene_degrade.png" });
  });

  test("DISPOSE clears data-scene-degraded + data-scene-root, no orphan nodes", async () => {
    const afterDispose: DisposeState = await page.evaluate(() => {
      (window as unknown as DegradeHarnessWindow).__degrade_harness.dispose();
      const root = document.getElementById("scene-root");
      return {
        sceneDegraded: root ? root.getAttribute("data-scene-degraded") : null,
        sceneRoot: root ? root.getAttribute("data-scene-root") : null,
        childCount: root ? root.children.length : -1,
      };
    });
    expect(afterDispose.sceneDegraded, "DISPOSE: data-scene-degraded must be cleared").toBeNull();
    expect(afterDispose.sceneRoot, "DISPOSE: data-scene-root must be cleared").toBeNull();
    expect(afterDispose.childCount, "DISPOSE: scene root must have no orphan children").toBe(0);

    // Resolver failures go to console.warn, NOT to pageerror; so pageErrors
    // must be empty across the whole harness session.
    expect(pageErrors, `unexpected page errors: ${pageErrors.join("; ")}`).toEqual([]);
  });
});
