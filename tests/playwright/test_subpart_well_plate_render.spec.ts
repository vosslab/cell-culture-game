// test_subpart_well_plate_render.spec.ts
//
// M3 WP-SUBPART-RENDER browser acceptance (contract item 4, D11 spatial
// correspondence). Proves the GENERIC structured-subpart material-tint renderer
// paints each well by its own per-subpart material, through the PRODUCTION render
// path (runPipeline -> mountScene -> SceneView -> SceneItem ->
// SubpartVisualStateOverlay), driving state ONLY through the store's normal
// seed/write path (never hand-editing the DOM, never bypassing schema/enum
// validation).
//
// Converted from the library-model tests/playwright/test_subpart_well_plate_render.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
// The runner owns pass/fail signaling (expect) and the chromium browser (the
// project's "chromium" fixture) for this file; a per-file static server stays
// self-managed because this spec mounts an esbuild-plugin-solid-bundled test
// harness (a Solid render sandbox exposing window.__subpart_harness), not the
// shipped app the shared config webServer serves.
//
// The harness mounts the REAL generated plate_focus_bench scene (which places
// well_plate_96). The well subpart material_name enum is the closed sentinel
// FLOOR [empty, mixed]; runtime acceptance is registry-backed (D1, task #26), so
// the harness store carries a registry that registers 200 microM carboplatin. This
// test writes:
//   - mixed       -> the spec-fixed built-in color #686868 (painted)
//   - empty       -> null color -> fill "transparent" (no fill; base art shows)
//   - carboplatin_200umol -> a REGISTERED drug -> its scalar display color, proving
//     the registry-backed write reaches a well AND renders the registry color, end
//     to end (this is the #26 drug-color render proof).
//
// Assertions (all by data-subpart-name, the spatial-correspondence handle):
//   1. exactly 96 [data-subpart-name] shapes render in the plate overlay.
//   2. BEFORE any write: every well renders fill="transparent" (all unseeded).
//   3. AFTER writes A1=mixed, A2=empty (explicit), H1=mixed (a second painted
//      well at a distant position), D6=carboplatin_200umol (a registered drug at a
//      third position): A1 paints #686868, H1 paints #686868, D6 paints the
//      registered carboplatin color, A2 is transparent (explicitly emptied), H12
//      is transparent (never written). A1 and A2 therefore show DIFFERENT fills;
//      the painted wells sit at their correct grid positions, the rest transparent.
//   4. the overlay svg has pointer-events:none (base art stays clickable).
//   5. no page errors.

import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import * as esbuild from "esbuild";
import { solidPlugin } from "esbuild-plugin-solid";
import http from "node:http";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const SHOT_DIR = path.join(REPO_ROOT, "test-results", "subpart_render");
const BUILT_ASSETS_DIR = path.join(REPO_ROOT, "dist", "assets");

const PLATE = "well_plate_96";
// The spec-fixed built-in color for the `mixed` sentinel (MATERIAL_CONVENTION.md).
const MIXED_COLOR = "#686868";
const TRANSPARENT = "transparent";

//============================================
// Read a material's display_color straight out of generated/protocol_materials.ts
//============================================

// Text-parses the generated PROTOCOL_MATERIALS literal (same approach as
// test_launcher.mjs's load_expected_index for generated/protocols.ts) rather than
// importing the .ts module, since this reads a plain generated data file.
function readMaterialDisplayColor(protocolName: string, materialName: string): string {
  const file = path.join(REPO_ROOT, "generated/protocol_materials.ts");
  const src = fs.readFileSync(file, "utf8");
  // Find the registry block for this protocol: `protocol_name: { ... },` on its own line.
  const protocolRe = new RegExp(`\\b${protocolName}:\\s*\\{`);
  const protocolMatch = protocolRe.exec(src);
  if (protocolMatch === null) {
    throw new Error(`Protocol ${protocolName} not found in generated/protocol_materials.ts`);
  }
  // Registry entries are emitted one protocol per line, so the line end closes the block.
  const lineEnd = src.indexOf("\n", protocolMatch.index);
  const blob = src.slice(protocolMatch.index, lineEnd);
  // Match the exact material key, then pull its display_color.
  const materialRe = new RegExp(`\\b${materialName}:\\s*\\{[^}]*display_color:\\s*"([^"]+)"`);
  const materialMatch = materialRe.exec(blob);
  if (materialMatch === null || materialMatch[1] === undefined) {
    throw new Error(
      `Material ${materialName} not found under ${protocolName} in generated/protocol_materials.ts`,
    );
  }
  return materialMatch[1];
}

// Read live from generated/protocol_materials.ts (also matched by the harness
// registry in helper_subpart_render_harness.tsx). The drug-color render proof asserts
// a well painted this after a registry-backed carboplatin write.
const CARBOPLATIN_COLOR = readMaterialDisplayColor(
  "plate_drug_treatment_drug_addition",
  "carboplatin_200umol",
);

// A complete, deterministic row-major plate. This is deliberately derived from
// the same canonical naming scheme as the object, rather than querying or
// mutating the SVG artwork. The M8 spike exercises the existing store and
// generated geometry contract, not a second renderer.
const ALL_WELLS = Array.from({ length: 8 }, (_, rowIndex) =>
  Array.from(
    { length: 12 },
    (_, columnIndex) => `${String.fromCharCode("A".charCodeAt(0) + rowIndex)}${columnIndex + 1}`,
  ),
).flat();
const FULL_PLATE_SAMPLE_COUNT = 25;
const FRAME_MS_AT_60HZ = 1000 / 60;
const FULL_PLATE_P95_FRAME_BUDGET_MS = FRAME_MS_AT_60HZ * 2;

type FullPlateTiming = {
  elapsed_ms: number;
  all_expected: boolean;
  rendered_count: number;
};

//============================================
// Build the harness bundle in-memory.
//============================================

async function buildHarness(): Promise<string> {
  const entry = path.join(__dirname, "helper_subpart_render_harness.tsx");
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
  const output = result.outputFiles[0];
  if (output === undefined) {
    throw new Error("esbuild produced no output for the subpart render harness");
  }
  return output.text;
}

//============================================
// Serve the bundle + a host page.
//============================================

type ServerHandle = { server: http.Server; port: number };

const ASSET_MIME_TYPES: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

function respondNotFound(res: http.ServerResponse): void {
  res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("Not found");
}

function serveBuiltAsset(urlPath: string, res: http.ServerResponse): boolean {
  if (!urlPath.startsWith("/assets/")) {
    return false;
  }

  let relativePath: string;
  try {
    relativePath = decodeURIComponent(urlPath.slice("/assets/".length));
  } catch {
    respondNotFound(res);
    return true;
  }
  const pathParts = relativePath.split(/[\\/]/u);
  if (
    relativePath.length === 0 ||
    path.isAbsolute(relativePath) ||
    pathParts.some((part) => part.length === 0 || part === "." || part === "..")
  ) {
    respondNotFound(res);
    return true;
  }

  const assetPath = path.resolve(BUILT_ASSETS_DIR, relativePath);
  const assetRootPrefix = `${BUILT_ASSETS_DIR}${path.sep}`;
  if (!assetPath.startsWith(assetRootPrefix)) {
    respondNotFound(res);
    return true;
  }
  fs.readFile(assetPath, (error, data) => {
    if (error !== null) {
      respondNotFound(res);
      return;
    }
    const contentType = ASSET_MIME_TYPES[path.extname(assetPath).toLowerCase()];
    res.writeHead(200, {
      "Content-Type": contentType ?? "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    res.end(data);
  });
  return true;
}

function startServer(bundleJs: string): Promise<ServerHandle> {
  const html =
    "<!doctype html><html><head><meta charset='utf-8'><style>" +
    "#scene-root{position:relative;width:1200px;height:675px;background:#fff;}</style></head>" +
    "<body><div id='scene-root'></div>" +
    "<script type='module' src='/harness.js'></script></body></html>";
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = new URL(req.url ?? "/", "http://127.0.0.1").pathname;
      if (urlPath === "/harness.js") {
        res.writeHead(200, { "Content-Type": "application/javascript" });
        res.end(bundleJs);
        return;
      }
      if (serveBuiltAsset(urlPath, res)) {
        return;
      }
      if (urlPath === "/") {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(html);
        return;
      }
      respondNotFound(res);
    });
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address !== null ? address.port : 0;
      resolve({ server, port });
    });
  });
}

//============================================
// Page-side helpers (serialized into the browser).
//============================================

type FillReport = { present: boolean; fill: string | null; material: string | null };

type SvgReadyReport = { state: "ready" | "failed"; detail: string };

async function waitForPlateBaseSvg(page: Page): Promise<void> {
  const readiness = await page.waitForFunction((plate) => {
    const root = document.getElementById("scene-root");
    const item = root?.querySelector(`[data-object-name='${plate}']`);
    const domHost = item?.querySelector<HTMLElement>("[data-svg-render-mode='dom-svg']");
    if (domHost === null || domHost === undefined) {
      return null;
    }
    const loadError = domHost.getAttribute("data-svg-load-error");
    if (loadError !== null) {
      return { state: "failed", detail: loadError };
    }
    if (domHost.querySelector("svg") !== null) {
      return { state: "ready", detail: "" };
    }
    return null;
  }, PLATE);
  const report = (await readiness.jsonValue()) as SvgReadyReport;
  expect(report, `plate base SVG load failed: ${report.detail}`).toEqual({
    state: "ready",
    detail: "",
  });
}

// Read the fill attribute of one subpart shape by data-subpart-name. Runs in the
// page. Takes a single [plate, subpart] array because page.evaluate passes one
// serialized arg.
function readFillPage(args: string[]): FillReport {
  const plate = args[0] ?? "";
  const subpart = args[1] ?? "";
  const root = document.getElementById("scene-root");
  const overlay = root !== null ? root.querySelector(`[data-subpart-overlay='${plate}']`) : null;
  if (overlay === null) {
    return { present: false, fill: null, material: null };
  }
  const shape = overlay.querySelector(`[data-subpart-name='${subpart}']`);
  if (shape === null) {
    return { present: false, fill: null, material: null };
  }
  return {
    present: true,
    fill: shape.getAttribute("fill"),
    material: shape.getAttribute("data-material-name"),
  };
}

//============================================
// Test
//============================================

test.describe("subpart well plate render", () => {
  let serverHandle: ServerHandle;
  let base: string;

  test.beforeAll(async () => {
    fs.mkdirSync(SHOT_DIR, { recursive: true });
    const bundle = await buildHarness();
    serverHandle = await startServer(bundle);
    base = `http://127.0.0.1:${serverHandle.port}`;
  });

  test.afterAll(async () => {
    await new Promise<void>((resolve) => serverHandle.server.close(() => resolve()));
  });

  test("material-tint overlay paints wells by state, with correct spatial correspondence", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.setViewportSize({ width: 1200, height: 675 });
    await page.goto(`${base}/`, { waitUntil: "load" });
    await page.waitForFunction(
      () =>
        typeof (window as unknown as { __subpart_harness?: unknown }).__subpart_harness !==
        "undefined",
      { timeout: 5000 },
    );

    // Mount the real plate_focus_bench scene (places well_plate_96).
    await page.evaluate(() =>
      (window as unknown as { __subpart_harness: { mount: () => void } }).__subpart_harness.mount(),
    );
    await page.waitForSelector(`#scene-root [data-subpart-overlay='${PLATE}']`, { timeout: 5000 });
    await waitForPlateBaseSvg(page);

    //----------------------------------------
    // 1. Exactly 96 subpart shapes render.
    //----------------------------------------
    const shapeCount = await page.evaluate((plate) => {
      const root = document.getElementById("scene-root");
      const overlay =
        root !== null ? root.querySelector(`[data-subpart-overlay='${plate}']`) : null;
      return overlay === null ? 0 : overlay.querySelectorAll("[data-subpart-name]").length;
    }, PLATE);
    expect(
      shapeCount,
      `plate overlay must render exactly 96 subpart shapes, got ${shapeCount}`,
    ).toBe(96);

    //----------------------------------------
    // 2. BEFORE any write: every well is transparent (all unseeded).
    //----------------------------------------
    const beforeA1 = await page.evaluate(readFillPage, [PLATE, "A1"]);
    const beforeH12 = await page.evaluate(readFillPage, [PLATE, "H12"]);
    expect(beforeA1.fill, "A1 must be transparent before any write").toBe(TRANSPARENT);
    expect(beforeH12.fill, "H12 must be transparent before any write").toBe(TRANSPARENT);

    await page.screenshot({ path: path.join(SHOT_DIR, "before_writes.png") });

    //----------------------------------------
    // 3. Drive per-well state through the store's normal seed/write path.
    //    A1 = mixed (painted), A2 = empty (explicit), H1 = mixed (second painted
    //    well, distant position), H12 = left unset (transparent control).
    //----------------------------------------
    await page.evaluate(() => {
      const h = (
        window as unknown as {
          __subpart_harness: {
            seed_subpart: (name: string) => void;
            write_subpart: (
              name: string,
              patch: { material_name: string; material_volume: number },
            ) => void;
          };
        }
      ).__subpart_harness;
      // A1: seed then write the `mixed` sentinel (the store accepts it).
      h.seed_subpart("A1");
      h.write_subpart("A1", { material_name: "mixed", material_volume: 200 });
      // A2: seed then write `empty` explicitly (a real write to the empty state).
      h.seed_subpart("A2");
      h.write_subpart("A2", { material_name: "empty", material_volume: 0 });
      // H1: seed then write `mixed` (a second painted well, bottom-left corner).
      h.seed_subpart("H1");
      h.write_subpart("H1", { material_name: "mixed", material_volume: 200 });
      // D6: seed then write `carboplatin_200umol`, a REGISTERED drug. This is the #26
      // proof: the registry-backed acceptance lets the drug write reach the well,
      // and the renderer paints carboplatin's registered display_color (#a719db).
      h.seed_subpart("D6");
      h.write_subpart("D6", {
        material_name: "carboplatin_200umol",
        material_volume: 200,
      });
      // H12: intentionally NOT seeded/written -> stays the unseeded transparent
      // control, proving an unwritten well renders no fill.
    });
    await expect
      .poll(() => page.evaluate(readFillPage, [PLATE, "D6"]), {
        message: "the registered concentration-specific drug write must reach D6",
      })
      .toEqual({
        present: true,
        fill: CARBOPLATIN_COLOR,
        material: "carboplatin_200umol",
      });

    const a1 = await page.evaluate(readFillPage, [PLATE, "A1"]);
    const a2 = await page.evaluate(readFillPage, [PLATE, "A2"]);
    const h1 = await page.evaluate(readFillPage, [PLATE, "H1"]);
    const d6 = await page.evaluate(readFillPage, [PLATE, "D6"]);
    const h12 = await page.evaluate(readFillPage, [PLATE, "H12"]);

    // A1 painted with the built-in mixed color; its data-material-name reflects it.
    expect(a1.fill, `A1 must paint ${MIXED_COLOR} after mixed write, got ${a1.fill}`).toBe(
      MIXED_COLOR,
    );
    expect(a1.material, `A1 data-material-name must be "mixed", got ${a1.material}`).toBe("mixed");
    // H1 (a distant painted well) also paints the mixed color.
    expect(h1.fill, `H1 must paint ${MIXED_COLOR} after mixed write, got ${h1.fill}`).toBe(
      MIXED_COLOR,
    );
    // D6 (a registered drug) paints carboplatin's registered scalar color, and
    // its data-material-name reflects the stored drug. This is the #26 proof:
    // the registry-backed subpart write reached the well AND renders the registry
    // color end to end.
    expect(
      d6.fill,
      `D6 must paint ${CARBOPLATIN_COLOR} after carboplatin_200umol write, got ${d6.fill}`,
    ).toBe(CARBOPLATIN_COLOR);
    expect(
      d6.material,
      `D6 data-material-name must be "carboplatin_200umol", got ${d6.material}`,
    ).toBe("carboplatin_200umol");
    // A2 explicitly written empty -> transparent (different fill from A1).
    expect(a2.fill, `A2 must be transparent after empty write, got ${a2.fill}`).toBe(TRANSPARENT);
    // A1 and A2 must differ (the core "two different fills" proof).
    expect(a1.fill, "A1 and A2 must show DIFFERENT fills").not.toBe(a2.fill);
    // The drug well differs from both the built-in well and the empty control.
    expect(d6.fill, "D6 (carboplatin) and A1 (mixed) must show DIFFERENT fills").not.toBe(a1.fill);
    expect(d6.fill, "D6 (carboplatin) and A2 (empty) must show DIFFERENT fills").not.toBe(a2.fill);
    // H12 never written -> transparent control.
    expect(h12.fill, `H12 (unset) must be transparent, got ${h12.fill}`).toBe(TRANSPARENT);

    await page.screenshot({ path: path.join(SHOT_DIR, "after_writes.png") });

    //----------------------------------------
    // 4. Overlay does not intercept clicks (pointer-events: none).
    //----------------------------------------
    const pe = await page.evaluate((plate) => {
      const root = document.getElementById("scene-root");
      const overlay =
        root !== null ? root.querySelector(`[data-subpart-overlay='${plate}']`) : null;
      return overlay === null ? null : getComputedStyle(overlay).pointerEvents;
    }, PLATE);
    expect(pe, `overlay must have pointer-events:none, got ${pe}`).toBe("none");

    //----------------------------------------
    // 5. No page errors throughout.
    //----------------------------------------
    expect(pageErrors, `no page errors: ${pageErrors.join("; ")}`).toEqual([]);
  });

  test("96 independent normal store writes reach the existing generated-geometry overlay within two frames", async ({
    page,
  }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));

    await page.setViewportSize({ width: 1200, height: 675 });
    await page.goto(`${base}/`, { waitUntil: "load" });
    await page.waitForFunction(
      () =>
        typeof (window as unknown as { __subpart_harness?: unknown }).__subpart_harness !==
        "undefined",
      { timeout: 5000 },
    );
    await page.evaluate(() =>
      (window as unknown as { __subpart_harness: { mount: () => void } }).__subpart_harness.mount(),
    );
    await page.waitForSelector(`#scene-root [data-subpart-overlay='${PLATE}']`, { timeout: 5000 });
    await waitForPlateBaseSvg(page);

    // Seed all wells once through the same production store method used by scene
    // operations. Seeding is deliberately outside the timed steady-state write:
    // it initializes empty state and is not part of a real full-plate material
    // replacement.
    await page.evaluate(
      ({ wells }) => {
        const h = (
          window as unknown as {
            __subpart_harness: { seed_subpart: (name: string) => void };
          }
        ).__subpart_harness;
        for (const well of wells) {
          h.seed_subpart(well);
        }
      },
      { wells: ALL_WELLS },
    );

    // Assign a three-material pattern. A per-cell expected value proves this is
    // not a single shared plate state or an all-wells visual shortcut.
    const patterns = [
      ALL_WELLS.map((_, index) =>
        index % 3 === 0 ? "mixed" : index % 3 === 1 ? "carboplatin_200umol" : "media",
      ),
      ALL_WELLS.map((_, index) =>
        index % 3 === 0 ? "media" : index % 3 === 1 ? "mixed" : "carboplatin_200umol",
      ),
    ];
    const warmup = patterns[0];
    if (warmup === undefined) {
      throw new Error("M8 timing setup requires a warm-up pattern");
    }

    async function writeAndMeasure(expected: string[]): Promise<FullPlateTiming> {
      return page.evaluate(
        async ({ plate, wells, expectedMaterials }) => {
          const h = (
            window as unknown as {
              __subpart_harness: {
                write_subpart: (
                  name: string,
                  patch: { material_name: string; material_volume: number },
                ) => void;
              };
            }
          ).__subpart_harness;
          const overlay = document.querySelector(`[data-subpart-overlay='${plate}']`);
          if (overlay === null) {
            throw new Error("M8 timing: missing plate overlay");
          }
          // Begin just after a frame boundary. The following rAF is the next
          // reactive DOM/render completion opportunity after all 96 store writes.
          await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
          const start = performance.now();
          for (let index = 0; index < wells.length; index += 1) {
            const well = wells[index];
            const material = expectedMaterials[index];
            if (well === undefined || material === undefined) {
              throw new Error("M8 timing: well/material pattern mismatch");
            }
            h.write_subpart(well, { material_name: material, material_volume: 200 });
          }
          await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
          const elapsed_ms = performance.now() - start;
          const shapes = Array.from(overlay.querySelectorAll<SVGElement>("[data-subpart-name]"));
          return {
            elapsed_ms,
            rendered_count: shapes.length,
            all_expected:
              shapes.length === wells.length &&
              wells.every(
                (well, index) =>
                  overlay
                    .querySelector(`[data-subpart-name='${well}']`)
                    ?.getAttribute("data-material-name") === expectedMaterials[index],
              ),
          };
        },
        { plate: PLATE, wells: ALL_WELLS, expectedMaterials: expected },
      );
    }

    // Prime subscriptions and browser caches before timing. This still has to
    // reach every cell before any sample is accepted.
    const warmupResult = await writeAndMeasure(warmup);
    expect(warmupResult.rendered_count).toBe(96);
    expect(warmupResult.all_expected).toBe(true);

    const samples: FullPlateTiming[] = [];
    for (let index = 0; index < FULL_PLATE_SAMPLE_COUNT; index += 1) {
      const pattern = patterns[index % patterns.length];
      if (pattern === undefined) {
        throw new Error("M8 timing setup requires a measurement pattern");
      }
      const sample = await writeAndMeasure(pattern);
      expect(sample.rendered_count, `sample ${index} must retain all 96 wells`).toBe(96);
      expect(sample.all_expected, `sample ${index} must reach all independent target states`).toBe(
        true,
      );
      samples.push(sample);
    }

    const ordered = samples.map((sample) => sample.elapsed_ms).sort((a, b) => a - b);
    const p95Index = Math.ceil(ordered.length * 0.95) - 1;
    const p95 = ordered[p95Index];
    const median = ordered[Math.floor(ordered.length / 2)];
    if (p95 === undefined || median === undefined) {
      throw new Error("M8 timing produced no samples");
    }
    // A complete plate is one learner-visible change. Two 60 Hz frames (33.333
    // ms) is the deliberately conservative browser budget: one frame is the
    // first available animation-frame opportunity after a just-missed boundary;
    // a second tolerates
    // ordinary scheduling variance. The p95, rather than one lucky sample,
    // makes the gate resistant to timer jitter.
    expect(
      p95,
      `M8 full-plate p95 ${p95.toFixed(3)} ms; samples: ${ordered.map((v) => v.toFixed(3)).join(", ")}`,
    ).toBeLessThanOrEqual(FULL_PLATE_P95_FRAME_BUDGET_MS);
    // rAF timestamps are quantized around 16.7 ms, so a 20 ms median permits
    // normal timer rounding while still requiring the first animation-frame opportunity.
    expect(
      median,
      "M8 full-plate median must fit in the first 60 Hz animation-frame opportunity",
    ).toBeLessThanOrEqual(20);
    console.log(
      `M8 96-well update timing: n=${samples.length}; median=${median.toFixed(3)} ms; ` +
        `p95=${p95.toFixed(3)} ms; budget=${FULL_PLATE_P95_FRAME_BUDGET_MS.toFixed(3)} ms; ` +
        `samples=[${ordered.map((value) => value.toFixed(3)).join(", ")}].`,
    );
    expect(pageErrors, `no page errors: ${pageErrors.join("; ")}`).toEqual([]);
  });
});
