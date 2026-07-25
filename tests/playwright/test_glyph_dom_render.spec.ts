// test_glyph_dom_render.spec.ts
//
// WP-A4: browser DOM-text proof that the author-entity -> codegen-decode ->
// DOM-glyph convention (docs/specs/MATERIAL_YAML_FORMAT.md, "Glyph rendering")
// actually reaches the rendered page. drug_dilution_setup's authored YAML
// writes concentrations as HTML entities ("400 &micro;M"); the codegen decode
// step must turn that into the real U+00B5 MICRO SIGN glyph before it ever
// reaches Solid JSX, so the DOM never carries the literal escaped form.
//
// Builds the production protocol-host bundle (same esbuild + solidPlugin
// transform as pipeline/build_main_bundle.mjs) pinned to drug_dilution_setup,
// serves it over HTTP, and asserts against real rendered DOM text:
//   - #guidance-text (GuidanceBar, src/shell/regions/guidance_bar.tsx) contains
//     the micro sign glyph.
//   - .outline-step-card (StepOutline, src/shell/regions/step_outline.tsx)
//     visible text contains the micro sign glyph.
//   - .outline-step-card's title attribute (step_outline.tsx, the full
//     untruncated prompt) contains the micro sign glyph.
// Every check also asserts the literal entity string "&micro;" is absent, so
// the test is non-vacuous: before the WP-A2/WP-A3 decode wiring landed, these
// same assertions would have failed against the raw entity text.

import { test, expect } from "@playwright/test";
import type { Browser, Page } from "@playwright/test";
import { chromium } from "playwright";
import * as esbuild from "esbuild";
import { solidPlugin } from "esbuild-plugin-solid";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

import { REPO_ROOT } from "./repo_root.mjs";

// U+00B5 MICRO SIGN, written as a JS unicode escape so the source file stays ASCII-only.
const MICRO_SIGN = "\u00B5";
const PROTOCOL_NAME = "drug_dilution_setup";

//============================================
// Build the host bundle pinned to drug_dilution_setup.
//============================================

async function buildHostBundle(outDir: string): Promise<void> {
  fs.mkdirSync(outDir, { recursive: true });

  // Generators are expected to have already run via npm run check (or any
  // other prebuild path); this test does not re-run them.
  const protocolsTs = path.join(REPO_ROOT, "generated/protocols.ts");
  if (!fs.existsSync(protocolsTs)) {
    throw new Error("generated/protocols.ts missing; run npm run check first");
  }

  // Entry matches pipeline/build_main_bundle.mjs's protocol-host target
  // exactly, and the output filename matches what
  // src/protocol_host_template.html loads (./protocol_host.js).
  const entry = path.join(REPO_ROOT, "src/protocol_host_entry.tsx");
  const outJs = path.join(outDir, "protocol_host.js");
  const result = await esbuild.build({
    entryPoints: [entry],
    bundle: true,
    format: "esm",
    target: "es2020",
    platform: "browser",
    sourcemap: true,
    outfile: outJs,
    plugins: [solidPlugin()],
    logLevel: "silent",
  });
  if (result.errors.length > 0) {
    throw new Error(`esbuild failed to bundle ${entry}: ${JSON.stringify(result.errors)}`);
  }

  const htmlTemplate = fs.readFileSync(
    path.join(REPO_ROOT, "src/protocol_host_template.html"),
    "utf8",
  );
  const htmlRendered = htmlTemplate.split("{{PROTOCOL_NAME}}").join(PROTOCOL_NAME);
  fs.writeFileSync(path.join(outDir, "index.html"), htmlRendered);

  // Copy stylesheet so the wrapper does not 404.
  const cssSrc = path.join(REPO_ROOT, "src/style.css");
  if (fs.existsSync(cssSrc)) {
    fs.copyFileSync(cssSrc, path.join(outDir, "style.css"));
  } else {
    fs.writeFileSync(path.join(outDir, "style.css"), "");
  }
}

//============================================
// Serve the temp directory over HTTP.
//============================================

interface ServerHandle {
  server: http.Server;
  base: string;
}

function startServer(rootDir: string): Promise<ServerHandle> {
  const mime: Record<string, string> = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".map": "application/json",
  };

  const server = http.createServer((req, res) => {
    const urlPath = (req.url ?? "/").split("?")[0] ?? "/";
    const norm = urlPath === "/" ? "/index.html" : urlPath;
    const filePath = path.join(rootDir, norm);
    const ext = path.extname(filePath);
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end(`Not found: ${norm}`);
        return;
      }
      res.writeHead(200, { "Content-Type": mime[ext] ?? "application/octet-stream" });
      res.end(data);
    });
  });

  return new Promise((resolve) => {
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

test.describe("drug_dilution_setup glyph rendering", () => {
  let outDir: string;
  let serverHandle: ServerHandle;
  let browser: Browser;
  let page: Page;

  test.beforeAll(async () => {
    outDir = fs.mkdtempSync(path.join(REPO_ROOT, "test-results", "glyph_dom_render_"));
    await buildHostBundle(outDir);
    serverHandle = await startServer(outDir);
    browser = await chromium.launch();
    page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(serverHandle.base, { waitUntil: "load" });
    // Wait for the HUD to mount and the guidance bar to carry real text.
    await expect(page.locator("#guidance-text")).not.toHaveText("Loading...");
  });

  test.afterAll(async () => {
    await browser.close();
    await new Promise<void>((resolve) => serverHandle.server.close(() => resolve()));
    fs.rmSync(outDir, { recursive: true, force: true });
  });

  test("guidance bar renders the micro sign glyph, not the literal entity", async () => {
    const guidanceText = await page.locator("#guidance-text").textContent();
    expect(guidanceText).not.toBeNull();
    expect(guidanceText).toContain(MICRO_SIGN);
    expect(guidanceText).not.toContain("&micro;");
  });

  test("outline step card text renders the micro sign glyph, not the literal entity", async () => {
    const cards = page.locator(".outline-step-card");
    await expect(cards.first()).toBeVisible();
    const cardTexts = await cards.allTextContents();
    const joinedText = cardTexts.join(" ");
    expect(joinedText).toContain(MICRO_SIGN);
    expect(joinedText).not.toContain("&micro;");
  });

  test("outline step card title attribute renders the micro sign glyph, not the literal entity", async () => {
    // step_outline.tsx sets title={step.prompt} to the full, untruncated
    // prompt (the visible card text is truncated by short_label()).
    const titles = await page
      .locator(".outline-step-card")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("title") ?? ""));
    const joinedTitles = titles.join(" ");
    expect(joinedTitles).toContain(MICRO_SIGN);
    expect(joinedTitles).not.toContain("&micro;");

    await page.screenshot({ path: "test-results/test_glyph_dom_render_00_outline.png" });
  });
});
