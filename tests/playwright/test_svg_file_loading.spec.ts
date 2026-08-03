// test_svg_file_loading.spec.ts
//
// M5-e acceptance: GitHub Pages-safe SVG file loading under a repo subpath.
//
// Converted from the library-model tests/playwright/test_svg_file_loading.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the
// set). The runner owns pass/fail signaling (expect) for this file; the
// browser and static server stay self-managed because this spec proves
// something the shared config webServer cannot: the shipped bundle served
// under a GitHub-Pages-style repo subpath (the config webServer serves dist/
// at the root, not under a subpath), plus an esbuild-bundled harness page
// that exposes the real resolveAnchor export. Engine is Firefox, matching the
// original script's documented engine choice; the config's chromium project
// is not used by this file.
//
// This test proves the M5 SVG cutover end-to-end IN THE BROWSER, served under a
// GitHub-Pages-style project subpath so relative manifest paths must resolve the
// same way they would on a real project site. It covers, mapped to the M5-e
// acceptance bullets:
//
//   B1 (subpath load, no 404): the manifest-referenced SVG URLs resolve with
//       HTTP 200 under the repo subpath -- at least one <img> src and one
//       fetched dom-svg asset. Relative paths must work under the subpath, not
//       only at the server root.
//   B2 (wedge render): the four wedge pages render with zero duplicate injected-
//       SVG ids (mirrors the existing namespacing test's wedge scan).
//   B3 (tiering by declaration): an asset whose manifest entry has
//       requires_dom_svg:true renders as an injected <svg> (NOT <img>); an asset
//       with requires_dom_svg:false renders as <img> (NOT injected svg). Targets
//       are chosen from generated/svg_manifest.ts cross-referenced with the
//       assets actually present on the page (data-asset), not hardcoded guesses.
//   B4 (anchor seam): on a real injected dom-svg instance carrying the bare
//       authored anchor id "anchor_liquid_bounds", the REAL resolveAnchor(host,
//       "anchor_liquid_bounds") returns the namespaced element, with NO
//       asset/placement string concatenation in the test. resolveAnchor is the
//       shipped exported resolver, reached through the same window-harness
//       mechanism the existing test uses (esbuild bundle of
//       svg_namespacing_harness.ts), injected onto a real production page.
//   B5 (evidence): before/after screenshots of the four wedge pages to
//       test-results/.
//
// Server + harness + subpath-mount + firefox setup are COPIED from
// test_svg_id_namespacing.spec.ts (the M5-e plan instructs reuse of that exact
// mechanism; the helper is not exported there, so the minimal pieces are
// copied with this comment rather than invented anew).

import { test, expect } from "@playwright/test";
import path from "node:path";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { firefox, type Browser } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../");
const ARTIFACT_DIR = path.join(REPO_ROOT, "test-results");
const REPO_SUBPATH = "virtual-lab-protocol-simulation";

// The four scenes proven to collide on a shared id="a" (the wedge bug). Same
// list as the namespacing test; these are the pages M5-e must render cleanly.
const WEDGE_PAGES = [
  "sdspage_destain_gel_rock",
  "sdspage_destain_gel_setup",
  "sdspage_stain_gel",
  "sdspage_image_gel",
];

// The wedge page that carries the concrete tiering targets. The
// staining_bench placements on this page include destain_bottle -> bottle_medium_pink
// (requires_dom_svg:true) and rocking_shaker ->
// rocking_shaker_idle (requires_dom_svg:false). See PROBE_TARGETS below.
const PROBE_PAGE = "sdspage_destain_gel_rock";

// Material SVG compilation replaces authored anchors with opaque runtime
// handles, so B4 intentionally exercises the still-authored-anchor contract on
// the binary T75 state asset. passage_pellet_reseed seeds that flask with
// cell_suspension, selecting t75_flask_filled on its real entry scene.
const ANCHOR_PROBE_PAGE = "passage_pellet_reseed";

// Concrete tiering + anchor targets, chosen by reading generated/svg_manifest.ts
// and confirming the assets are actually placed on PROBE_PAGE:
//   - bottle_medium_pink:  requires_dom_svg:true  -> must inject an <svg>.
//   - rocking_shaker_idle: requires_dom_svg:false -> must render as an <img>.
const DOM_SVG_ASSET = "bottle_medium_pink";
const IMG_ASSET = "rocking_shaker_idle";
const ANCHOR_DOM_SVG_ASSET = "t75_flask_filled";
const ANCHOR_BARE_ID = "anchor_liquid_bounds";

type ServerHandle = {
  server: http.Server;
  port: number;
  base: string;
};

//============================================
// Small helpers
//============================================

// A polite random settle delay before screenshot/network-ish steps (repo style).
function randomSettleMs(): number {
  return 120 + Math.floor(Math.random() * 180);
}

function ensureArtifactDir(): void {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

// Bundle the test harness (real src functions incl. resolveAnchor, no registry)
// into a temp ESM file with esbuild, write a host HTML for the /harness/ route,
// and ALSO keep the bundled harness.js so it can be added as a module script tag
// onto a real production page (B4 needs the REAL resolveAnchor on that page).
// COPIED from test_svg_id_namespacing.spec.ts (server/build/subpath-mount reuse).
function buildHarness(): string {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "svg_load_harness_"));
  const entry = path.join(REPO_ROOT, "tests/playwright/svg_namespacing_harness.ts");
  const outFile = path.join(tmpDir, "harness.js");
  const result = spawnSync(
    "npx",
    [
      "esbuild",
      entry,
      "--bundle",
      "--format=esm",
      "--target=es2020",
      "--platform=browser",
      `--outfile=${outFile}`,
    ],
    { cwd: REPO_ROOT, encoding: "utf8" },
  );
  if (result.status !== 0) {
    throw new Error(`esbuild harness build failed:\n${result.stderr || result.stdout}`);
  }
  const html =
    "<!doctype html><html><head><meta charset='utf-8'></head>" +
    "<body><div id='host'></div>" +
    "<script type='module' src='harness.js'></script></body></html>";
  fs.writeFileSync(path.join(tmpDir, "index.html"), html);
  return tmpDir;
}

// A minimal static file server rooted at dist/, mounted under the repo subpath so
// URLs resolve exactly as on a GitHub Pages project site. Also serves the harness
// temp dir at /harness/. COPIED from test_svg_id_namespacing.spec.ts.
function startServer(harnessDir: string): Promise<ServerHandle> {
  const distRoot = path.join(REPO_ROOT, "dist");
  const mime: Record<string, string> = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".map": "application/json",
  };

  function resolveFile(urlPath: string): string | null {
    if (urlPath === "/harness/" || urlPath === "/harness") {
      return path.join(harnessDir, "index.html");
    }
    if (urlPath.startsWith("/harness/")) {
      return path.join(harnessDir, urlPath.slice("/harness/".length));
    }
    const prefix = `/${REPO_SUBPATH}/`;
    if (urlPath.startsWith(prefix)) {
      const rel = urlPath.slice(prefix.length) || "index.html";
      return path.join(distRoot, rel);
    }
    return null;
  }

  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || "/").split("?")[0] ?? "/");
    const filePath = resolveFile(urlPath);
    if (filePath === null || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      res.statusCode = 404;
      res.end("not found");
      return;
    }
    const ext = path.extname(filePath);
    res.setHeader("Content-Type", mime[ext] || "application/octet-stream");
    fs.createReadStream(filePath).pipe(res);
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address !== null ? address.port : 0;
      resolve({ server, port, base: `http://127.0.0.1:${port}` });
    });
  });
}

//============================================
// In-page assertion routines (run inside Firefox)
//============================================

type WedgeReport = {
  ok: boolean;
  failures: string[];
  dupCount: number;
  svgCount: number;
};

// Mirror of the namespacing test's scoped wedge scan (B2): no duplicate ids
// among injected SVG subtrees, and every SVG-internal reference resolves inside
// its own rendered SVG instance.
function runWedgePageChecksInPage(): WedgeReport {
  const out: WedgeReport = { ok: true, failures: [], dupCount: 0, svgCount: 0 };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  const svgs = Array.from(document.querySelectorAll("[data-placement-name] svg"));
  out.svgCount = svgs.length;

  const idCounts = new Map<string, number>();
  for (const svg of svgs) {
    const els = [svg, ...Array.from(svg.querySelectorAll("[id]"))];
    for (const el of els) {
      const id = el.getAttribute("id");
      if (!id) continue;
      idCounts.set(id, (idCounts.get(id) || 0) + 1);
    }
  }
  for (const [id, count] of idCounts) {
    if (count > 1) {
      out.dupCount += 1;
      fail(`duplicate id within injected SVG subtrees: "${id}" x${count}`);
    }
  }

  for (const svg of svgs) {
    const refEls = svg.querySelectorAll("[clip-path],[mask],[filter],[fill],[stroke]");
    for (const el of Array.from(refEls)) {
      for (const attr of ["clip-path", "mask", "filter", "fill", "stroke"]) {
        const v = el.getAttribute(attr);
        if (!v) continue;
        const m = v.match(/url\(\s*['"]?#([^'")\s]+)/);
        if (!m) continue;
        if (svg.querySelector(`#${CSS.escape(m[1] ?? "")}`) === null) {
          fail(`ref ${attr}=${v} does not resolve inside its own SVG instance`);
        }
      }
    }
  }

  return out;
}

type TierReport = {
  ok: boolean;
  failures: string[];
  domSvgFound: boolean;
  imgFound: boolean;
  imgSrc: string | null;
  domSvgNamespace: string | null;
};

// B3 tiering by declaration, plus collecting the SVG asset URLs that must load
// with HTTP 200 (B1). The render mode is read from the DOM the renderer emitted:
//   - a DOM-SVG-required asset renders a div[data-svg-render-mode="dom-svg"] that
//     CONTAINS an injected <svg>, and the host div carries
//     data-svg-instance-namespace.
//   - a static asset renders an <img data-svg-render-mode="img"> with a src URL.
// The item div carries data-asset (the live asset name) and data-placement-name.
// Returns the located render modes plus one <img> src and one dom-svg manifest
// URL for the network 200 check.
function probeTieringInPage(args: { domSvgAsset: string; imgAsset: string }): TierReport {
  const domSvgAsset = args.domSvgAsset;
  const imgAsset = args.imgAsset;
  const out: TierReport = {
    ok: true,
    failures: [],
    domSvgFound: false,
    imgFound: false,
    imgSrc: null,
    domSvgNamespace: null,
  };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  // Locate the item whose live asset is the DOM-SVG target. data-asset is a
  // data-* attribute (never a rewritten SVG id), so this selection is stable.
  const domItem = document.querySelector(`[data-placement-name][data-asset="${domSvgAsset}"]`);
  if (domItem === null) {
    fail(`dom-svg target "${domSvgAsset}" not present on page (no [data-asset] match)`);
  } else {
    const svgHostDiv = domItem.querySelector('div[data-svg-render-mode="dom-svg"]');
    const injectedSvg = domItem.querySelector("svg");
    const asImg = domItem.querySelector('img[data-svg-render-mode="img"]');
    if (svgHostDiv === null || injectedSvg === null) {
      fail(`dom-svg target "${domSvgAsset}" did not inject an <svg> (tiering broke)`);
    }
    if (asImg !== null) {
      fail(`dom-svg target "${domSvgAsset}" rendered as <img>, must be injected svg`);
    }
    if (svgHostDiv !== null) {
      out.domSvgNamespace = svgHostDiv.getAttribute("data-svg-instance-namespace");
      if (out.domSvgNamespace === null) {
        fail(`dom-svg host for "${domSvgAsset}" has no data-svg-instance-namespace stamp`);
      }
    }
    out.domSvgFound = svgHostDiv !== null && injectedSvg !== null && asImg === null;
  }

  // Locate the item whose live asset is the static <img> target.
  const imgItem = document.querySelector(`[data-placement-name][data-asset="${imgAsset}"]`);
  if (imgItem === null) {
    fail(`img target "${imgAsset}" not present on page (no [data-asset] match)`);
  } else {
    const asImg = imgItem.querySelector('img[data-svg-render-mode="img"]');
    const injectedSvg = imgItem.querySelector("svg");
    if (asImg === null) {
      fail(`img target "${imgAsset}" did not render as <img> (tiering broke)`);
    }
    if (injectedSvg !== null) {
      fail(`img target "${imgAsset}" injected an <svg>, must be a static <img>`);
    }
    if (asImg !== null) {
      out.imgSrc = asImg.getAttribute("src");
      if (out.imgSrc === null || out.imgSrc.length === 0) {
        fail(`img target "${imgAsset}" has no src`);
      }
      // The manifest emits relative paths (no leading slash) so they resolve
      // under the repo subpath. A leading slash would break GH Pages project
      // sites; assert it is relative.
      if (out.imgSrc !== null && out.imgSrc.startsWith("/")) {
        fail(`img src "${out.imgSrc}" is absolute (leading slash); must be relative`);
      }
    }
    out.imgFound = asImg !== null && injectedSvg === null;
  }

  return out;
}

type AnchorReport = {
  ok: boolean;
  failures: string[];
  resolved: boolean;
  resolvedId: string | null;
};

// B4 anchor seam: resolve the bare authored anchor id on the REAL injected
// dom-svg host using the shipped resolveAnchor (exposed on window.svgHarness via
// the harness module script added to this page). NO string concatenation here.
// Returns whether the resolver found a namespaced element and that the element
// truly lives inside the host's injected SVG subtree.
function probeAnchorInPage(args: { domSvgAsset: string; bareId: string }): AnchorReport {
  const domSvgAsset = args.domSvgAsset;
  const bareAnchorId = args.bareId;
  const out: AnchorReport = { ok: true, failures: [], resolved: false, resolvedId: null };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  const harness = (window as unknown as { svgHarness?: { resolveAnchor?: unknown } }).svgHarness;
  if (harness === undefined || typeof harness.resolveAnchor !== "function") {
    fail("window.svgHarness.resolveAnchor not available on page");
    return out;
  }

  const domItem = document.querySelector(`[data-placement-name][data-asset="${domSvgAsset}"]`);
  if (domItem === null) {
    fail(`anchor host asset "${domSvgAsset}" not present on page`);
    return out;
  }
  const host = domItem.querySelector('div[data-svg-render-mode="dom-svg"]');
  if (host === null) {
    fail(`anchor host for "${domSvgAsset}" has no dom-svg host div`);
    return out;
  }

  // The REAL resolver. It reads the per-instance namespace stamped on the host
  // and applies the single namespacing prefix rule -- the test never builds the
  // namespaced id itself.
  const resolveAnchor = harness.resolveAnchor as (host: Element, bareId: string) => Element | null;
  const el = resolveAnchor(host, bareAnchorId);
  if (el === null) {
    fail(`resolveAnchor returned null for bare id "${bareAnchorId}" on "${domSvgAsset}"`);
    return out;
  }
  out.resolved = true;
  out.resolvedId = el.getAttribute("id");
  // The resolved element must live inside this host's injected SVG subtree.
  if (!host.contains(el)) {
    fail(`resolved anchor element is not inside the host's injected SVG`);
  }
  // The resolved id must be the namespaced form (carries the bare id as suffix
  // and is not the bare id itself), proving namespacing actually ran.
  if (out.resolvedId === bareAnchorId) {
    fail(`resolved id equals the bare id "${bareAnchorId}" (namespacing did not run)`);
  }
  if (out.resolvedId !== null && !out.resolvedId.endsWith(`__${bareAnchorId}`)) {
    fail(`resolved id "${out.resolvedId}" does not end with the bare anchor id`);
  }

  return out;
}

//============================================
// Network helper: assert a manifest-relative SVG URL loads 200 under the subpath
//============================================

// Resolve a page-relative SVG src against the served wedge-page URL and fetch it,
// asserting HTTP 200 and an svg content type. Runs in Node (not the page) so the
// status code is unambiguous. relPath is the manifest-relative path emitted by
// the renderer (no leading slash), e.g. "assets/svg/equipment/rocking_shaker_idle.svg".
async function fetchSvgStatus(
  base: string,
  relPath: string,
): Promise<{ url: string; status: number; contentType: string }> {
  // The wedge pages are served at /<subpath>/<page>.html, so a relative SVG src
  // resolves against /<subpath>/. Build that absolute URL explicitly.
  const url = `${base}/${REPO_SUBPATH}/${relPath}`;
  const res = await fetch(url);
  const contentType = res.headers.get("content-type") || "";
  return { url, status: res.status, contentType };
}

//============================================
// Tests
//============================================

test.describe("svg file loading under a repo subpath", () => {
  let harnessDir: string;
  let serverHandle: ServerHandle;
  let browser: Browser;

  test.beforeAll(async () => {
    ensureArtifactDir();
    harnessDir = buildHarness();
    serverHandle = await startServer(harnessDir);
    browser = await firefox.launch({ headless: true });
  });

  test.afterAll(async () => {
    await browser.close();
    await new Promise<void>((resolve) => serverHandle.server.close(() => resolve()));
    fs.rmSync(harnessDir, { recursive: true, force: true });
  });

  test("B2/B5: four wedge pages render cleanly under the subpath; before/after screenshots", async () => {
    for (const slug of WEDGE_PAGES) {
      const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      const url = `${serverHandle.base}/${REPO_SUBPATH}/${slug}.html`;
      await page.goto(url, { waitUntil: "networkidle" });
      await page.waitForSelector("[data-placement-name] svg", { timeout: 8000 });
      await page.waitForTimeout(randomSettleMs());

      await page.screenshot({ path: path.join(ARTIFACT_DIR, `fileload_${slug}_before.png`) });

      const wedge = await page.evaluate(runWedgePageChecksInPage);

      await page.waitForTimeout(randomSettleMs());
      await page.screenshot({ path: path.join(ARTIFACT_DIR, `fileload_${slug}_after.png`) });

      if (wedge.failures.length > 0) {
        console.error(`[${slug}] WEDGE FAILURES:\n  ` + wedge.failures.join("\n  "));
      }
      console.log(
        `[${slug}] injected svgs=${wedge.svgCount} duplicateInjectedIds=${wedge.dupCount}`,
      );

      expect(errors, `[${slug}] page errors: ${errors.join("; ")}`).toEqual([]);
      expect(wedge.svgCount, `[${slug}] no injected SVGs found`).toBeGreaterThan(0);
      expect(wedge.dupCount, `[${slug}] duplicate injected-SVG ids`).toBe(0);
      expect(wedge.ok, `[${slug}] wedge checks failed: ${wedge.failures.join("; ")}`).toBe(true);
      await page.close();
    }
  });

  test("B1/B3: tiering by declaration (dom-svg vs img) and SVG assets load 200 under the subpath", async () => {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    const url = `${serverHandle.base}/${REPO_SUBPATH}/${PROBE_PAGE}.html`;
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForSelector("[data-placement-name] svg", { timeout: 8000 });
    await page.waitForTimeout(randomSettleMs());

    // B3: tiering by declaration.
    const tier = await page.evaluate(probeTieringInPage, {
      domSvgAsset: DOM_SVG_ASSET,
      imgAsset: IMG_ASSET,
    });
    if (tier.failures.length > 0) {
      console.error("TIERING FAILURES:\n  " + tier.failures.join("\n  "));
    }
    console.log(
      `tiering: domSvg(${DOM_SVG_ASSET})=${tier.domSvgFound} ns=${tier.domSvgNamespace} ` +
        `img(${IMG_ASSET})=${tier.imgFound} imgSrc=${tier.imgSrc}`,
    );
    expect(errors, `page errors: ${errors.join("; ")}`).toEqual([]);
    expect(tier.ok, `tiering checks failed: ${tier.failures.join("; ")}`).toBe(true);
    expect(
      tier.domSvgFound,
      `dom-svg target "${DOM_SVG_ASSET}" did not render as injected svg`,
    ).toBe(true);
    expect(tier.imgFound, `img target "${IMG_ASSET}" did not render as <img>`).toBe(true);

    // B1: the <img> src (a manifest-relative URL) must load 200 under the subpath.
    expect(tier.imgSrc, "no <img> src captured for the 200 check").toBeTruthy();
    const imgStatus = await fetchSvgStatus(serverHandle.base, tier.imgSrc ?? "");
    console.log(`img asset GET ${imgStatus.url} -> ${imgStatus.status} (${imgStatus.contentType})`);
    expect(imgStatus.status, `img SVG did not load 200: ${imgStatus.url}`).toBe(200);
    expect(imgStatus.contentType).toMatch(/svg/);

    // B1: a fetched dom-svg asset must also load 200 under the subpath. The
    // dom-svg asset's relative path mirrors the <img> shape (assets/svg/...); use
    // the known DOM-SVG asset path which the renderer fetched to inject the <svg>.
    const domSvgRel = `assets/svg/equipment/${DOM_SVG_ASSET}.svg`;
    const domStatus = await fetchSvgStatus(serverHandle.base, domSvgRel);
    console.log(
      `dom-svg asset GET ${domStatus.url} -> ${domStatus.status} (${domStatus.contentType})`,
    );
    expect(domStatus.status, `dom-svg SVG did not load 200: ${domStatus.url}`).toBe(200);
    expect(domStatus.contentType).toMatch(/svg/);

    await page.close();
  });

  test("B4: resolveAnchor returns the namespaced element for a real injected anchor", async () => {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    const url = `${serverHandle.base}/${REPO_SUBPATH}/${ANCHOR_PROBE_PAGE}.html`;
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForSelector("[data-placement-name] svg", { timeout: 8000 });
    await page.waitForTimeout(randomSettleMs());

    // Add the REAL resolver onto this real production page via the same window-harness
    // mechanism the existing test uses: the esbuild-bundled harness module exposes
    // window.svgHarness.resolveAnchor (the shipped export). No src is modified.
    await page.addScriptTag({
      path: path.join(harnessDir, "harness.js"),
      type: "module",
    });
    await page.waitForFunction(
      () => (window as unknown as { svgHarness?: unknown }).svgHarness !== undefined,
      {
        timeout: 5000,
      },
    );

    const anchor = await page.evaluate(probeAnchorInPage, {
      domSvgAsset: ANCHOR_DOM_SVG_ASSET,
      bareId: ANCHOR_BARE_ID,
    });
    if (anchor.failures.length > 0) {
      console.error("ANCHOR FAILURES:\n  " + anchor.failures.join("\n  "));
    }
    console.log(`anchor: resolved=${anchor.resolved} resolvedId=${anchor.resolvedId}`);

    expect(errors, `page errors: ${errors.join("; ")}`).toEqual([]);
    expect(anchor.resolved, `resolveAnchor did not resolve "${ANCHOR_BARE_ID}"`).toBe(true);
    expect(anchor.ok, `anchor checks failed: ${anchor.failures.join("; ")}`).toBe(true);
    await page.close();
  });
});
