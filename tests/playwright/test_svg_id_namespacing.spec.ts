// test_svg_id_namespacing.spec.ts
//
// Per-render-instance SVG id namespacing verification.
//
// Converted from the library-model tests/playwright/test_svg_id_namespacing.mjs
// (that .mjs stays in place this phase; the batch migration reconciles the set).
// The runner owns pass/fail signaling (expect) for this file; the browser and
// static server stay self-managed because this spec proves something the
// shared config webServer cannot: (1) a bundled test-only harness page that
// exercises the real namespaceSvgIds/injectSvgMarkupInto exports with inline
// fixtures, and (2) the shipped wedge pages served under a GitHub-Pages-style
// repo subpath (the config webServer serves dist/ at the root, not under a
// subpath). Engine is Firefox, matching the original script's documented
// engine choice; the config's chromium project is not used by this file.
//
// Proves BEHAVIOR, not visual inspection alone. Two layers:
//
//   1. Unit layer: drives the REAL exported pure helper namespaceSvgIds and the
//      REAL injectSvgMarkupInto (bundled from src via esbuild and exposed on
//      window) inside Firefox, against small inline fixtures. Asserts every
//      reference form rewrites, two assets that both define id="a" do not
//      cross-clip, the same markup injected twice with different keys does not
//      collide, <style> text url(#id) is rewritten, and there are no duplicate
//      ids among injected SVG descendants. There is no bundled SVG_REGISTRY
//      in this runtime; namespacing mechanics are proven on inline markup.
//
//   2. Integration layer: loads the four real wedge pages from dist/ under a
//      GitHub-Pages-style repo subpath in Firefox, asserts no duplicate ids
//      among injected SVG descendants and that the shaker's clip-path resolves
//      to ITS OWN clipPath (not bottle_green's), and saves before/after
//      screenshots.

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

// The four scenes proven to collide on a shared id="a" (the wedge bug).
const WEDGE_PAGES = [
  "sdspage_destain_gel_rock",
  "sdspage_destain_gel_setup",
  "sdspage_stain_gel",
  "sdspage_image_gel",
];

type ServerHandle = {
  server: http.Server;
  port: number;
  base: string;
};

//============================================
// Small helpers
//============================================

function ensureArtifactDir(): void {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

// Bundle the test harness (real src functions, no registry) into a temp JS file
// using esbuild, then write a host HTML that loads it. Returns the temp dir.
function buildHarness(): string {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "svg_ns_harness_"));
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

// A minimal static file server rooted at dist/, mounted under the repo subpath
// so URLs resolve exactly as they would on a GitHub Pages project site. Also
// serves the harness temp dir at /harness/.
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
    // Harness namespace.
    if (urlPath === "/harness/" || urlPath === "/harness") {
      return path.join(harnessDir, "index.html");
    }
    if (urlPath.startsWith("/harness/")) {
      return path.join(harnessDir, urlPath.slice("/harness/".length));
    }
    // Repo-subpath-mounted dist.
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
// In-page assertion routines (run inside Firefox via page.evaluate)
//============================================

type UnitReport = {
  ok: boolean;
  failures: string[];
  samples: Record<string, unknown>;
};

// Returns a report object; all logic uses the REAL window.svgHarness functions.
function runUnitChecksInPage(): UnitReport {
  const H = (window as unknown as { svgHarness: Record<string, (...args: never[]) => unknown> })
    .svgHarness;
  const out: UnitReport = { ok: true, failures: [], samples: {} };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  function parseSvg(markup: string): Element {
    const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
    return doc.documentElement;
  }

  // --- Reference-form coverage: url() in many attributes + quoting/whitespace,
  // plus href and xlink:href. One fixture defines id="a" and references it in
  // clip-path, mask, filter, fill, stroke, style (quoted + whitespace), href,
  // and xlink:href.
  const refFixture =
    "<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>" +
    "<defs><clipPath id='a'><rect/></clipPath>" +
    "<linearGradient id='g'><stop/></linearGradient></defs>" +
    "<rect clip-path='url(#a)' mask=\"url('#a')\" filter='url( #a )' " +
    "fill='url(#g)' stroke=\"url(#g)\" style='fill:url(#g); stroke: url( #a )'/>" +
    "<use href='#a'/><use xlink:href='#a'/>" +
    "</svg>";
  const refRoot = parseSvg(refFixture);
  (H.namespaceSvgIds as (root: Element, key: string) => void)(refRoot, "K1");
  const xml = new XMLSerializer().serializeToString(refRoot);
  out.samples.refXml = xml;

  // Every local reference must now point at the prefixed id; no bare #a / #g
  // local refs may remain.
  if (!xml.includes("url(#K1__a)")) fail("clip-path/filter url(#a) not rewritten");
  if (!xml.includes("#K1__a") || /href="#a"/.test(xml)) fail("href #a not rewritten");
  // xlink:href serializes as href in the xlink namespace; check no bare #a left.
  if (/#a(?![A-Za-z0-9_])/.test(xml.replace(/#K1__a/g, ""))) {
    fail("a bare #a local reference survived rewriting");
  }
  if (!xml.includes("url(#K1__g)")) fail("fill/stroke/style url(#g) not rewritten");
  // The id attributes themselves must be prefixed.
  if (!xml.includes('id="K1__a"') || !xml.includes('id="K1__g"')) {
    fail("id attributes not prefixed");
  }
  // No remaining un-namespaced url(#a) or url(#g) anywhere.
  if (/url\(\s*['"]?#a[\s'")]/.test(xml)) fail("un-namespaced url(#a) survived");
  if (/url\(\s*['"]?#g[\s'")]/.test(xml)) fail("un-namespaced url(#g) survived");

  // --- <style> text-node rewrite via a class-based style block referencing a
  // gradient by id inside CSS text.
  const styleFixture =
    "<svg xmlns='http://www.w3.org/2000/svg'>" +
    "<style>.body{fill:url(#radial-gradient);}</style>" +
    "<radialGradient id='radial-gradient'><stop/></radialGradient>" +
    "<rect class='body'/></svg>";
  const styleRoot = parseSvg(styleFixture);
  (H.namespaceSvgIds as (root: Element, key: string) => void)(styleRoot, "STY");
  const styleXml = new XMLSerializer().serializeToString(styleRoot);
  out.samples.styleXml = styleXml;
  if (!styleXml.includes("url(#STY__radial-gradient)")) {
    fail("<style> text url(#radial-gradient) not rewritten");
  }
  if (styleXml.includes("url(#radial-gradient)")) {
    fail("un-namespaced url(#radial-gradient) survived in <style>");
  }

  // --- Duplicate source id: a malformed-but-shipped asset can declare the same
  // id twice (the microtube asset declares id="anchor_liquid_bounds" on a clip
  // rect AND a hidden rect). Namespacing must still emit UNIQUE ids per element
  // (no duplicate ids in the injected subtree), while the reference still points
  // at the first definition.
  const dupIdFixture =
    "<svg xmlns='http://www.w3.org/2000/svg'>" +
    "<defs><clipPath id='c'><rect id='bounds' width='5' height='5'/></clipPath></defs>" +
    "<rect data-role='clipped' clip-path='url(#c)' width='9' height='9'/>" +
    "<rect id='bounds' display='none' width='1' height='1'/></svg>";
  const dupRoot = parseSvg(dupIdFixture);
  (H.namespaceSvgIds as (root: Element, key: string) => void)(dupRoot, "DUP");
  const dupIds = Array.from(dupRoot.querySelectorAll("[id]")).map((e) => e.id);
  out.samples.dupIds = dupIds;
  const dupSeen = new Set<string>();
  let dupCollision = false;
  for (const id of dupIds) {
    if (dupSeen.has(id)) dupCollision = true;
    dupSeen.add(id);
  }
  if (dupCollision)
    fail(`duplicate emitted id from a duplicate-source-id asset: ${dupIds.join(",")}`);
  // The clip reference must still resolve to an element inside this subtree.
  const clippedEl = dupRoot.querySelector("[data-role='clipped']");
  const clipRefAttr = clippedEl !== null ? clippedEl.getAttribute("clip-path") : null;
  const clipRefMatch = clipRefAttr !== null ? clipRefAttr.match(/url\(\s*['"]?#([^'")\s]+)/) : null;
  if (!clipRefMatch || dupRoot.querySelector(`#${CSS.escape(clipRefMatch[1] ?? "")}`) === null) {
    fail("duplicate-id fixture: clip reference does not resolve");
  }

  // --- Two different assets that BOTH define id="a" must not cross-clip. Inject
  // both into separate hosts with different keys; each clip-path must resolve to
  // an id that exists INSIDE its own injected subtree.
  const assetA =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs><clipPath id='a'><rect width='10' height='10'/></clipPath></defs>" +
    "<rect data-role='body' clip-path='url(#a)' width='100' height='100'/></svg>";
  const assetB =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs><clipPath id='a'><rect width='99' height='99'/></clipPath></defs>" +
    "<rect data-role='body' clip-path='url(#a)' width='100' height='100'/></svg>";

  function injectInlineMarkup(markup: string, key: string): HTMLDivElement {
    // Use the REAL raw-markup injection seam (parse + namespace + stamp +
    // insert). Markup is passed by value; no registry is involved.
    const div = document.createElement("div");
    div.className = "injected-svg-host";
    document.body.appendChild(div);
    (
      H.injectSvgMarkupInto as (
        host: HTMLDivElement,
        key: string,
        markup: string,
        ns: string,
      ) => void
    )(div, key, markup, key);
    return div;
  }

  const hostA = injectInlineMarkup(assetA, "assetA__sceneX__p1");
  const hostB = injectInlineMarkup(assetB, "assetB__sceneX__p2");

  function clipResolvesInOwnSubtree(host: HTMLDivElement): boolean {
    const body = host.querySelector("[data-role='body']");
    const ref = body !== null ? body.getAttribute("clip-path") : null;
    const m = ref !== null ? ref.match(/url\(\s*['"]?#([^'")\s]+)/) : null;
    if (!m) return false;
    const id = m[1] ?? "";
    return host.querySelector(`#${CSS.escape(id)}`) !== null;
  }

  if (!clipResolvesInOwnSubtree(hostA))
    fail("assetA clip-path does not resolve in its own subtree");
  if (!clipResolvesInOwnSubtree(hostB))
    fail("assetB clip-path does not resolve in its own subtree");

  const idA = hostA.querySelector("clipPath")?.id;
  const idB = hostB.querySelector("clipPath")?.id;
  if (idA === idB) fail("two id=a assets collided to the same namespaced id");

  // --- The SAME markup injected twice with DIFFERENT keys must not collide.
  // This is the multi-placement case: one asset rendered at two placements gets
  // a distinct per-instance namespace each time, so no id overlaps. Uses an
  // inline fixture that carries an internal clip-path reference so we also prove
  // each instance's references resolve inside its own subtree.
  const sameAsset =
    "<svg xmlns='http://www.w3.org/2000/svg'>" +
    "<defs><clipPath id='clip'><rect width='10' height='10'/></clipPath></defs>" +
    "<rect data-role='body' clip-path='url(#clip)' fill='url(#clip)' width='50' height='50'/>" +
    "</svg>";
  const h1 = document.createElement("div");
  const h2 = document.createElement("div");
  h1.className = "injected-svg-host";
  h2.className = "injected-svg-host";
  document.body.appendChild(h1);
  document.body.appendChild(h2);
  (
    H.injectSvgMarkupInto as (host: HTMLDivElement, key: string, markup: string, ns: string) => void
  )(h1, "same_asset", sameAsset, "sceneA__placement1");
  (
    H.injectSvgMarkupInto as (host: HTMLDivElement, key: string, markup: string, ns: string) => void
  )(h2, "same_asset", sameAsset, "sceneA__placement2");
  const ids1 = Array.from(h1.querySelectorAll("[id]")).map((e) => e.id);
  const ids2 = Array.from(h2.querySelectorAll("[id]")).map((e) => e.id);
  const overlap = ids1.filter((x) => ids2.includes(x));
  if (ids1.length === 0) fail("same-asset instance 1 produced no ids");
  if (overlap.length > 0) fail(`same asset twice collided on ids: ${overlap.join(",")}`);
  out.samples.sameAssetIdSample = ids1.slice(0, 3);

  // Every SVG-internal reference in instance 1 resolves inside instance 1.
  const refEls1 = Array.from(h1.querySelectorAll("[clip-path],[mask],[filter],[fill],[stroke]"));
  for (const el of refEls1) {
    for (const attr of ["clip-path", "mask", "filter", "fill", "stroke"]) {
      const v = el.getAttribute(attr);
      if (!v) continue;
      const mm = v.match(/url\(\s*['"]?#([^'")\s]+)/);
      if (!mm) continue;
      if (h1.querySelector(`#${CSS.escape(mm[1] ?? "")}`) === null) {
        fail(`same-asset ref ${attr}=${v} does not resolve inside its own instance`);
      }
    }
  }

  // --- A <style>-bearing asset keeps its style url() reference local after
  // injection through the real injectSvgMarkupInto seam (the t75_flask shape:
  // CSS text references a gradient by id).
  const styleAssetFixture =
    "<svg xmlns='http://www.w3.org/2000/svg'>" +
    "<style>.fill-area{fill:url(#grad);}</style>" +
    "<linearGradient id='grad'><stop/></linearGradient>" +
    "<rect class='fill-area' width='40' height='40'/></svg>";
  const hf = document.createElement("div");
  hf.className = "injected-svg-host";
  document.body.appendChild(hf);
  (
    H.injectSvgMarkupInto as (host: HTMLDivElement, key: string, markup: string, ns: string) => void
  )(hf, "style_asset", styleAssetFixture, "sceneF__flask1");
  const styleEls = Array.from(hf.querySelectorAll("style"));
  for (const s of styleEls) {
    const txt = s.textContent || "";
    const matches = txt.match(/url\(\s*['"]?#([^'")\s]+)/g) || [];
    for (const mraw of matches) {
      const idMatch = mraw.match(/#([^'")\s]+)/);
      const id = idMatch !== null ? idMatch[1] : undefined;
      if (id !== undefined && hf.querySelector(`#${CSS.escape(id)}`) === null) {
        fail(`<style> asset url ${mraw} unresolved after namespacing`);
      }
    }
  }

  // --- No duplicate ids AMONG injected SVG descendants, scoped to injected
  // subtrees only (never over unrelated app/UI ids).
  const allIds: string[] = [];
  for (const hostDiv of Array.from(document.querySelectorAll(".injected-svg-host"))) {
    for (const el of Array.from(hostDiv.querySelectorAll("[id]"))) {
      allIds.push(el.id);
    }
  }
  const seen = new Set<string>();
  const dups = new Set<string>();
  for (const id of allIds) {
    if (seen.has(id)) dups.add(id);
    seen.add(id);
  }
  if (dups.size > 0) fail(`duplicate ids among injected SVG descendants: ${[...dups].join(",")}`);

  return out;
}

// Exercise the anchor material renderer through the real injection seam. The
// assertions are lifecycle behavior: the same stable overlay rect is hidden on
// clear and error, then reused on recovery; the injection boundary applies the
// concrete local clip reference rather than material code rebuilding it.
function runAnchorMaterialLifecycleChecksInPage(): UnitReport {
  const H = (window as unknown as { svgHarness: Record<string, unknown> }).svgHarness;
  const out: UnitReport = { ok: true, failures: [], samples: {} };

  function fail(message: string): void {
    out.ok = false;
    out.failures.push(message);
  }

  type AnchorEffect = {
    type: "anchor_material";
    field_name: string;
    render_effect: "fill_height";
    target: "anchor_liquid_bounds" | "subpart_geometry";
    clip: "anchor_liquid_clip";
    fill_percent: number;
    material_name: string;
    color: string;
  };
  type SvgAnchorHandle = {
    element: Element;
    applyClipPath(target: SVGElement): void;
  };
  const inject = H.injectSvgMarkupInto as (
    host: HTMLDivElement,
    asset: string,
    markup: string,
    key: string,
  ) => void;
  const render = H.renderAnchorMaterialEffects as (
    host: HTMLElement,
    effects: readonly AnchorEffect[],
  ) => void;
  const resolve = H.resolveSvgAnchor as (
    host: HTMLElement,
    bareTarget: string,
  ) => SvgAnchorHandle | null;

  const markup =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs>" +
    "<clipPath id='anchor_liquid_clip'><rect x='2' y='4' width='10' height='20'/></clipPath>" +
    "</defs><rect id='anchor_liquid_bounds' x='2' y='4' width='10' height='20' display='none'/>" +
    "<g id='overlay_root'></g><path id='foreground_identity' d='M0 0h1v1z'/>" +
    "</svg>";
  const host = document.createElement("div");
  document.body.appendChild(host);
  inject(host, "vessel", markup, "scene__vessel");

  const visible: AnchorEffect = {
    type: "anchor_material",
    field_name: "material_volume",
    render_effect: "fill_height",
    target: "anchor_liquid_bounds",
    clip: "anchor_liquid_clip",
    fill_percent: 50,
    material_name: "pbs",
    color: "#076dad",
  };
  render(host, [visible]);
  const overlayGroup = host.querySelector("[data-anchor-material-overlay='true']");
  const overlayRoot = resolve(host, "overlay_root")?.element;
  const foregroundIdentity = resolve(host, "foreground_identity")?.element;
  if (!(overlayGroup instanceof SVGGElement) || !(overlayRoot instanceof SVGGElement)) {
    fail("overlay_root fixture did not create an SVG overlay group");
    return out;
  }
  if (overlayGroup.parentNode !== overlayRoot) {
    fail("material overlay did not mount inside the authored overlay_root");
  }
  if (
    !(foregroundIdentity instanceof SVGPathElement) ||
    (overlayGroup.compareDocumentPosition(foregroundIdentity) &
      Node.DOCUMENT_POSITION_FOLLOWING) ===
      0
  ) {
    fail("material overlay does not remain before the foreground identity marker");
  }
  const firstRect = host.querySelector("[data-anchor-material-field='material_volume']");
  if (!(firstRect instanceof SVGRectElement)) {
    fail("visible material effect did not create a stable SVG rect");
    return out;
  }
  if (firstRect.getAttribute("display") !== "inline") {
    fail("visible material effect was not displayed");
  }
  const clipPath = firstRect.getAttribute("clip-path");
  if (clipPath === null) {
    fail("injection seam did not apply a concrete local clip reference");
  } else {
    const clipId = clipPath.match(/^url\(#([^)]*)\)$/)?.[1];
    const clipTarget = firstRect.ownerSVGElement?.querySelector(`[id="${clipId}"]`);
    if (clipId === undefined || clipTarget === null) {
      fail("material clip reference does not resolve inside its own SVG instance");
    }
  }

  const clipAnchor = resolve(host, "anchor_liquid_clip");
  const seamProbe = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  if (clipAnchor === null) {
    fail("injection seam could not resolve the bare clip anchor");
  } else {
    clipAnchor.applyClipPath(seamProbe);
    if (seamProbe.getAttribute("clip-path") !== firstRect.getAttribute("clip-path")) {
      fail("injection seam did not own the concrete clip-path reference");
    }
  }

  render(host, []);
  if (firstRect.getAttribute("display") !== "none") {
    fail("clearing effects left a stale visible material fill");
  }

  render(host, [{ ...visible, fill_percent: 25, color: "#cc0066" }]);
  const recoveredRect = host.querySelector("[data-anchor-material-field='material_volume']");
  if (recoveredRect !== firstRect) {
    fail("material recovery replaced the static overlay rect");
  }
  if (
    firstRect.getAttribute("display") !== "inline" ||
    firstRect.getAttribute("fill") !== "#cc0066"
  ) {
    fail("material recovery did not update the existing overlay rect");
  }
  if (host.querySelector("[data-anchor-material-overlay='true']") !== overlayGroup) {
    fail("material recovery replaced the authored overlay group");
  }

  let errorSeen = false;
  try {
    render(host, [{ ...visible, target: "subpart_geometry" }]);
  } catch {
    errorSeen = true;
  }
  if (!errorSeen) {
    fail("invalid anchor effect did not fail loudly");
  }
  if (firstRect.getAttribute("display") !== "none") {
    fail("a failed effect left the prior material fill visible");
  }
  out.samples.overlayNodeStable = recoveredRect === firstRect;

  inject(host, "vessel", markup, "scene__vessel_reinjected");
  render(host, [visible]);
  const reinjectedGroup = host.querySelector("[data-anchor-material-overlay='true']");
  const reinjectedRoot = resolve(host, "overlay_root")?.element;
  if (!(reinjectedGroup instanceof SVGGElement) || !(reinjectedRoot instanceof SVGGElement)) {
    fail("reinjected SVG fixture did not recreate an SVG overlay group");
  } else if (reinjectedGroup === overlayGroup || reinjectedGroup.parentNode !== reinjectedRoot) {
    fail("reinjected SVG did not recreate the material overlay below its new overlay_root");
  }

  const fallbackMarkup =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs>" +
    "<clipPath id='anchor_liquid_clip'><rect x='2' y='4' width='10' height='20'/></clipPath>" +
    "</defs><rect id='anchor_liquid_bounds' x='2' y='4' width='10' height='20' display='none'/>" +
    "</svg>";
  const fallbackHost = document.createElement("div");
  document.body.appendChild(fallbackHost);
  inject(fallbackHost, "legacy_vessel", fallbackMarkup, "scene__legacy_vessel");
  render(fallbackHost, [visible]);
  const fallbackSvg = fallbackHost.querySelector("svg");
  const fallbackGroup = fallbackHost.querySelector("[data-anchor-material-overlay='true']");
  if (!(fallbackSvg instanceof SVGSVGElement) || !(fallbackGroup instanceof SVGGElement)) {
    fail("legacy SVG fixture did not create an SVG root overlay group");
  } else if (fallbackGroup.parentNode !== fallbackSvg) {
    fail("legacy SVG without overlay_root did not retain the root-overlay fallback");
  }

  const invalidRootMarkup =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs>" +
    "<clipPath id='anchor_liquid_clip'><rect x='2' y='4' width='10' height='20'/></clipPath>" +
    "</defs><rect id='anchor_liquid_bounds' x='2' y='4' width='10' height='20' display='none'/>" +
    "<rect id='overlay_root' x='0' y='0' width='1' height='1'/></svg>";
  const invalidRootHost = document.createElement("div");
  document.body.appendChild(invalidRootHost);
  inject(invalidRootHost, "invalid_root", invalidRootMarkup, "scene__invalid_root");
  let invalidRootError = false;
  try {
    render(invalidRootHost, [visible]);
  } catch {
    invalidRootError = true;
  }
  if (!invalidRootError) {
    fail("a non-group overlay_root did not fail loudly");
  }

  const foreignRootMarkup =
    "<svg xmlns='http://www.w3.org/2000/svg'><defs>" +
    "<clipPath id='anchor_liquid_clip'><rect x='2' y='4' width='10' height='20'/></clipPath>" +
    "</defs><rect id='anchor_liquid_bounds' x='2' y='4' width='10' height='20' display='none'/>" +
    "<svg><g id='overlay_root'></g></svg></svg>";
  const foreignRootHost = document.createElement("div");
  document.body.appendChild(foreignRootHost);
  inject(foreignRootHost, "foreign_root", foreignRootMarkup, "scene__foreign_root");
  let foreignRootError = false;
  try {
    render(foreignRootHost, [visible]);
  } catch {
    foreignRootError = true;
  }
  if (!foreignRootError) {
    fail("an overlay_root from another SVG root did not fail loudly");
  }
  return out;
}

type WedgeReport = {
  ok: boolean;
  failures: string[];
  dupCount: number;
  svgCount: number;
};

// Scoped duplicate-id + clip-resolution check for a real rendered wedge page.
function runWedgePageChecksInPage(): WedgeReport {
  const out: WedgeReport = { ok: true, failures: [], dupCount: 0, svgCount: 0 };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  // Injected SVG subtrees only: every <svg> the renderer placed inside a
  // [data-placement-name] item. We collect ids within those subtrees, never
  // unrelated app/UI ids.
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

  // Each SVG-internal reference resolves inside its OWN rendered SVG instance.
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

type NegativeReport = { ok: boolean; failures: string[] };

// Negative-path checks: injectSvgMarkupInto must throw loudly for each invalid
// markup case. Uses the harness-exposed injectRawMarkup helper to feed raw
// markup through all guards. There is no missing-key case:
// markup is passed by value, never looked up by key. Each check captures the
// thrown error message and verifies the expected stable prefix substring.
function runNegativePathChecksInPage(): NegativeReport {
  const H = (window as unknown as { svgHarness: Record<string, (...args: never[]) => unknown> })
    .svgHarness;
  const out: NegativeReport = { ok: true, failures: [] };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  // Helper: assert that calling fn() throws and that the message contains needle.
  function assertThrows(label: string, fn: () => void, needle: string): void {
    let caught: unknown = null;
    try {
      fn();
    } catch (e) {
      caught = e;
    }
    if (caught === null) {
      fail(`${label}: expected a throw but none occurred`);
      return;
    }
    const msg = caught instanceof Error ? caught.message : JSON.stringify(caught);
    if (!msg.includes(needle)) {
      fail(`${label}: threw but message "${msg}" does not contain "${needle}"`);
    }
  }

  const scratch = document.createElement("div");
  const injectRawMarkup = H.injectRawMarkup as (
    host: HTMLDivElement,
    markup: string,
    key: string,
  ) => void;

  // Case 1: empty / whitespace-only markup.
  // The empty-string and whitespace cases both hit the trim().length === 0 guard
  // in injectSvgMarkupInto.
  assertThrows("empty markup", () => injectRawMarkup(scratch, "   ", "k2"), "markup is empty");

  // Case 2: malformed markup that produces a <parsererror>.
  // An unclosed tag is enough to trigger DOMParser to return a parsererror root.
  assertThrows(
    "malformed markup",
    () => injectRawMarkup(scratch, "<svg><unclosed", "k3"),
    "failed to parse",
  );

  // Case 3: well-formed XML whose root is not <svg>.
  // A valid XML document with a <div> root passes the parser but fails the
  // localName === "svg" guard.
  assertThrows(
    "non-svg root",
    () =>
      injectRawMarkup(
        scratch,
        '<div xmlns="http://www.w3.org/1999/xhtml"><p>not svg</p></div>',
        "k4",
      ),
    "non-svg root",
  );

  return out;
}

type ShakerReport = { ok: boolean; failures: string[]; info: Record<string, string> };

// Resolve the shaker placement's clip-path and confirm it lands on a clipPath
// that lives INSIDE the shaker's own SVG, never bottle_green's.
function runShakerClipCheckInPage(): ShakerReport {
  const out: ShakerReport = { ok: true, failures: [], info: {} };

  function fail(msg: string): void {
    out.ok = false;
    out.failures.push(msg);
  }

  // The shaker item is the placement whose data-asset is the shaker. Find it by
  // data-asset attribute (a data-* attribute, never a rewritten SVG id).
  const shakerItem = document.querySelector('[data-placement-name][data-asset*="shaker"]');
  if (shakerItem === null) {
    // Not every wedge page necessarily has the shaker; report and pass.
    out.info.note = "no shaker placement on this page";
    return out;
  }

  // Post-cutover, an asset is injected as DOM SVG only when its manifest entry
  // has requires_dom_svg: true; otherwise it renders as an opaque <img>. The
  // rocking shaker is a non-DOM-SVG asset, so it carries no injected <svg> and
  // therefore CANNOT cross-clip into another instance's clipPath -- the wedge
  // bug is structurally impossible for it. That is a correct render, not a
  // failure. The cross-instance clip-isolation guarantee for whatever IS
  // injected on this page is still proven by runWedgePageChecksInPage, which
  // scans every injected SVG subtree for duplicate ids and unresolved refs.
  const svg = shakerItem.querySelector("svg");
  if (svg === null) {
    out.info.note =
      "shaker renders as non-DOM-SVG <img> (requires_dom_svg false); cannot cross-clip";
    return out;
  }

  // Find any clip-path reference inside the shaker SVG and confirm the target
  // clipPath is a descendant of THIS svg, not elsewhere in the document.
  const clipped = svg.querySelector("[clip-path]");
  if (clipped !== null) {
    const ref = clipped.getAttribute("clip-path");
    const m = ref !== null ? ref.match(/url\(\s*['"]?#([^'")\s]+)/) : null;
    if (m) {
      const id = m[1] ?? "";
      out.info.shakerClipRef = ref ?? "";
      const local = svg.querySelector(`#${CSS.escape(id)}`);
      if (local === null) {
        fail(`shaker clip-path ${ref} does not resolve inside the shaker SVG`);
      }
      // Confirm the FIRST document-order match is the local one (the bug was
      // that document-order resolved to bottle_green's clipPath).
      const docMatch = document.getElementById(id);
      if (docMatch !== null && !svg.contains(docMatch)) {
        fail(`shaker clip id "${id}" resolves to an element OUTSIDE the shaker SVG`);
      }
    }
  } else {
    out.info.note = "shaker svg has no clip-path reference on this page";
  }

  return out;
}

//============================================
// Tests
//============================================

test.describe("svg id namespacing", () => {
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

  test("unit: every reference form, two id=a assets, same asset twice, <style> text, no dup ids", async () => {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${serverHandle.base}/harness/`, { waitUntil: "load" });
    // Wait for the module to attach the harness.
    await page.waitForFunction(
      () => (window as unknown as { svgHarness?: unknown }).svgHarness !== undefined,
      {
        timeout: 5000,
      },
    );

    const report = await page.evaluate(runUnitChecksInPage);
    if (report.failures.length > 0) {
      console.error("UNIT FAILURES:\n  " + report.failures.join("\n  "));
    }
    console.log("sample namespaced same-asset ids:", report.samples.sameAssetIdSample);
    expect(errors, `page errors: ${errors.join("; ")}`).toEqual([]);
    expect(report.ok, `unit namespacing checks failed: ${report.failures.join("; ")}`).toBe(true);
    await page.close();
  });

  test("unit: injectSvgMarkupInto throws loudly for empty, malformed, and non-svg markup", async () => {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${serverHandle.base}/harness/`, { waitUntil: "load" });
    await page.waitForFunction(
      () => (window as unknown as { svgHarness?: unknown }).svgHarness !== undefined,
      {
        timeout: 5000,
      },
    );

    // Run the negative cases inside Firefox where injectSvgMarkupInto is live.
    // Each case must throw; the test captures and checks the message.
    const report = await page.evaluate(runNegativePathChecksInPage);
    if (report.failures.length > 0) {
      console.error("NEGATIVE-PATH FAILURES:\n  " + report.failures.join("\n  "));
    }
    expect(errors, `page errors: ${errors.join("; ")}`).toEqual([]);
    expect(report.ok, `negative-path checks failed: ${report.failures.join("; ")}`).toBe(true);
    await page.close();
  });

  test("unit: anchor material overlay hides stale state and recovers through injection seam", async () => {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    await page.goto(`${serverHandle.base}/harness/`, { waitUntil: "load" });
    await page.waitForFunction(
      () => (window as unknown as { svgHarness?: unknown }).svgHarness !== undefined,
      {
        timeout: 5000,
      },
    );

    const report = await page.evaluate(runAnchorMaterialLifecycleChecksInPage);
    if (report.failures.length > 0) {
      console.error("ANCHOR MATERIAL FAILURES:\n  " + report.failures.join("\n  "));
    }
    expect(errors, `page errors: ${errors.join("; ")}`).toEqual([]);
    expect(
      report.ok,
      `anchor material lifecycle checks failed: ${report.failures.join("; ")}`,
    ).toBe(true);
    await page.close();
  });

  test("integration: four wedge pages render cleanly with no duplicate injected-SVG ids", async () => {
    for (const slug of WEDGE_PAGES) {
      const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      const url = `${serverHandle.base}/${REPO_SUBPATH}/${slug}.html`;
      await page.goto(url, { waitUntil: "networkidle" });
      await page.waitForSelector("[data-placement-name] svg", { timeout: 8000 });
      await page.waitForFunction(() => document.fonts.status === "loaded");

      await page.screenshot({ path: path.join(ARTIFACT_DIR, `wedge_${slug}.png`) });

      const wedge = await page.evaluate(runWedgePageChecksInPage);
      const shaker = await page.evaluate(runShakerClipCheckInPage);

      if (wedge.failures.length > 0) {
        console.error(`[${slug}] WEDGE FAILURES:\n  ` + wedge.failures.join("\n  "));
      }
      if (shaker.failures.length > 0) {
        console.error(`[${slug}] SHAKER FAILURES:\n  ` + shaker.failures.join("\n  "));
      }
      console.log(
        `[${slug}] injected svgs=${wedge.svgCount} duplicateInjectedIds=${wedge.dupCount} ` +
          `shakerInfo=${JSON.stringify(shaker.info)}`,
      );

      expect(errors, `[${slug}] page errors: ${errors.join("; ")}`).toEqual([]);
      expect(wedge.svgCount, `[${slug}] no injected SVGs found`).toBeGreaterThan(0);
      expect(
        wedge.dupCount,
        `[${slug}] duplicate injected-SVG ids: ${wedge.failures.join("; ")}`,
      ).toBe(0);
      expect(wedge.ok, `[${slug}] wedge checks failed: ${wedge.failures.join("; ")}`).toBe(true);
      expect(shaker.ok, `[${slug}] shaker clip check failed: ${shaker.failures.join("; ")}`).toBe(
        true,
      );
      await page.close();
    }
  });
});
