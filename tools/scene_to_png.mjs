#!/usr/bin/env node

// tools/scene_to_png.mjs
//
// WS-M2-A + WS-M2-C: Render scene pages to PNG and report render stats.
//
// Usage (bare node):
//   node tools/scene_to_png.mjs --scene <name> [--png] [--out <path>] [--viewport WxH]
//   node tools/scene_to_png.mjs --all [--png] [--out <dir>] [--viewport WxH]
//
// Output split:
//   <scene>.stats.json -> generated/scene_render_stats/ (ALWAYS written; machine
//                         validation evidence from DOM bbox measurement, not the
//                         PNG; see STATS_DIR).
//   <scene>.png        -> test-results/scenes/ (ONLY when --png is passed).
//   summary.json       -> test-results/scenes/ (--all run report).
//   --out controls the PNG/summary dir ONLY; stats always go to
//   generated/scene_render_stats regardless of --out.
//
// --scene <name>           : Render one named scene from the manifest.
// --all                    : Render every EMITTED scene in the manifest.
//                            Skipped scenes get a summary row but no PNG.
// --png                    : Also write the PNG screenshot. Without it, the
//                            page is rendered and stats are computed/written,
//                            but no screenshot is captured. Default: off.
// --out <path>             : Single-scene: path for the PNG file (with --png).
//                            --all: PNG/summary output directory
//                            (default: test-results/scenes/). Does not affect
//                            stats.json location.
// --missing-svg <mode>     : strict | placeholder. Recorded in stats.json but
//                            does NOT trigger a rebuild. To switch mode, run:
//                            bash build_github_pages.sh, then re-run this tool.
// --viewport WxH           : Viewport size (default 1920x1080).
//
// Speed design:
//   - Assumes dist/ already exists. If missing, emits a clear error and exits.
//   - Launches ONE chromium browser and ONE HTTP server for the whole run.
//   - Reuses a single page for sequential scene renders.
//   - Waits on #scene-root[data-viewer-ready="true"], NOT networkidle.
//   - Uses waitUntil:"load" (not networkidle) for fast goto.
//   - A 100ms settle is the only fixed sleep; tunable via SETTLE_MS constant.
//
// Category classification (mutually exclusive):
//   populated        : at least one real (non-placeholder) rendered item.
//   placeholder-only : all rendered items are placeholders.
//   empty            : viewer-ready but zero rendered items.
//   load-failed      : page threw or timed out before ready marker.
//   skipped          : manifest says outcome=skipped; no render attempted.

import { chromium } from "playwright";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { classifyRenderedItem, selectVisualBbox } from "./scene_render_diagnostics.mjs";
import { computeSceneStats } from "./scene_stats.mjs";

//============================================
// Paths
//============================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const DIST_DIR = path.join(REPO_ROOT, "dist");
const MANIFEST_PATH = path.join(REPO_ROOT, "generated", "scene_manifest.json");
// Machine-readable stats.json files always write here, separate from the
// human PNG/summary outputs under test-results/scenes. --out never moves them.
const STATS_DIR = path.join(REPO_ROOT, "generated", "scene_render_stats");
const SVG_PLACEHOLDER_KEYS_PATH = path.join(REPO_ROOT, "generated", "svg_placeholder_keys.ts");

//============================================
// Placeholder-asset key set
//============================================

// Reads the SVG_PLACEHOLDER_KEYS array out of the generated
// svg_placeholder_keys.ts module. The generated file is TypeScript, so rather
// than pull in a TS loader just for this tool, parse the single string-array
// literal directly. Returns a Set of asset keys whose render is a dashed-box
// placeholder.
function read_placeholder_keys() {
  if (!fs.existsSync(SVG_PLACEHOLDER_KEYS_PATH)) {
    throw new Error(
      `SVG placeholder keys not found: ${SVG_PLACEHOLDER_KEYS_PATH}\nRun: bash pipeline/build_generated.sh`,
    );
  }
  const text = fs.readFileSync(SVG_PLACEHOLDER_KEYS_PATH, "utf8");
  const blockMatch = text.match(/SVG_PLACEHOLDER_KEYS[^=]*=\s*\[([\s\S]*?)\]/);
  if (!blockMatch) {
    throw new Error(
      `SVG_PLACEHOLDER_KEYS export missing from ${SVG_PLACEHOLDER_KEYS_PATH}. ` +
        "Regenerate with pipeline/gen_svg_manifest.py.",
    );
  }
  const keys = [];
  const keyRegex = /"([^"]+)"/g;
  let m;
  while ((m = keyRegex.exec(blockMatch[1])) !== null) {
    keys.push(m[1]);
  }
  return new Set(keys);
}

//============================================
// Timing constants
//============================================

// Maximum ms to wait for the viewer-ready marker.
// 5 s is enough for successful scenes (~150ms); load-failed scenes timeout here.
// Lower = faster --all runs when many scenes are broken.
const READY_TIMEOUT_MS = 5000;
// Small settle after ready marker (DOM paint flush). Keep <= 150ms per spec.
const SETTLE_MS = 100;
// Maximum ms for page.goto before we declare load-failed.
const GOTO_TIMEOUT_MS = 12000;

//============================================
// MIME map for inline HTTP server
//============================================

const MIME_MAP = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".map": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".woff2": "font/woff2",
};

//============================================
// CLI argument parser
//============================================

function parse_args(argv) {
  const args = {
    scene: null,
    all: false,
    out: null,
    png: false,
    missing_svg: "placeholder",
    viewport: { width: 1920, height: 1080 },
  };

  let i = 2;
  while (i < argv.length) {
    const tok = argv[i];
    if (tok === "--scene") {
      args.scene = argv[++i];
    } else if (tok === "--all") {
      args.all = true;
    } else if (tok === "--out") {
      args.out = argv[++i];
    } else if (tok === "--png") {
      args.png = true;
    } else if (tok === "--missing-svg") {
      const mode = argv[++i];
      if (mode !== "strict" && mode !== "placeholder") {
        throw new Error(`--missing-svg must be "strict" or "placeholder", got: ${mode}`);
      }
      args.missing_svg = mode;
    } else if (tok === "--viewport") {
      const vp = argv[++i];
      const m = vp.match(/^(\d+)[xX](\d+)$/);
      if (!m) {
        throw new Error(`--viewport must be WxH (e.g. 1920x1080), got: ${vp}`);
      }
      args.viewport = { width: parseInt(m[1], 10), height: parseInt(m[2], 10) };
    } else {
      throw new Error(`Unknown argument: ${tok}`);
    }
    i++;
  }

  if (!args.scene && !args.all) {
    throw new Error("Specify --scene <name> or --all");
  }
  if (args.scene && args.all) {
    throw new Error("--scene and --all are mutually exclusive");
  }

  return args;
}

//============================================
// Manifest reader
//============================================

function read_manifest() {
  if (!fs.existsSync(MANIFEST_PATH)) {
    throw new Error(`Scene manifest not found: ${MANIFEST_PATH}\nRun: bash build_github_pages.sh`);
  }
  const raw = fs.readFileSync(MANIFEST_PATH, "utf8");
  const parsed = JSON.parse(raw);
  return parsed.scenes;
}

function find_manifest_entry(scenes, scene_name) {
  const entry = scenes.find((s) => s.name === scene_name);
  return entry ?? null;
}

//============================================
// HTTP server (inline Node server, no external deps)
//============================================

async function start_server(dist_dir) {
  const server = http.createServer((req, res) => {
    // Strip query string; default to index.html for bare /
    const url_path = req.url ? req.url.split("?")[0] : "/";
    const norm = url_path === "/" ? "/index.html" : url_path;
    const file_path = path.join(dist_dir, norm);
    const ext = path.extname(file_path);
    const content_type = MIME_MAP[ext] ?? "application/octet-stream";

    fs.readFile(file_path, (err, data) => {
      if (err) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end(`Not found: ${norm}`);
        return;
      }
      res.writeHead(200, { "Content-Type": content_type });
      res.end(data);
    });
  });

  await new Promise((resolve, reject) => {
    server.listen(0, "127.0.0.1", () => resolve());
    server.on("error", reject);
  });

  const addr = server.address();
  const port = typeof addr === "object" && addr ? addr.port : 0;
  const base_url = `http://127.0.0.1:${port}`;

  return {
    port,
    base_url,
    close: () => new Promise((resolve) => server.close(() => resolve())),
  };
}

//============================================
// Playwright: check browser installed
//============================================

async function check_playwright_installed() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    await browser.close();
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (
      msg.includes("Executable") ||
      msg.includes("not found") ||
      msg.includes("install") ||
      msg.includes("executable")
    ) {
      console.error("Playwright browser not installed. Run: npx playwright install chromium");
      process.exit(1);
    }
    throw err;
  }
}

//============================================
// DOM query: collect rendered items from the page
//============================================

// Collects all [data-placement-name] elements from the page.
// Returns an array matching the renderedItems shape scene_stats.mjs expects.
async function collect_rendered_items(page, placeholderKeys) {
  const snapshots = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("[data-placement-name]"));
    return els.map((el) => {
      const rect = el.getBoundingClientRect();
      const placementBbox =
        rect.width > 0 || rect.height > 0
          ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
          : null;

      // Only the SVG injected into the base DOM-SVG host is evidence that the
      // placement's declared asset rendered. Subpart material and hit-surface
      // overlays can also contain SVG, but must not mask a failed base asset.
      const domSvgHost = el.querySelector('[data-svg-render-mode="dom-svg"]');
      const baseSvgEl = domSvgHost?.querySelector("svg") ?? null;
      const svgRect = baseSvgEl?.getBoundingClientRect() ?? null;
      const inlineSvgBbox =
        svgRect !== null && (svgRect.width > 0 || svgRect.height > 0)
          ? { x: svgRect.x, y: svgRect.y, width: svgRect.width, height: svgRect.height }
          : null;
      const imageEl = el.querySelector('img[data-svg-render-mode="img"]');
      const imageRect = imageEl?.getBoundingClientRect() ?? null;
      const staticImageBbox =
        imageRect !== null && (imageRect.width > 0 || imageRect.height > 0)
          ? { x: imageRect.x, y: imageRect.y, width: imageRect.width, height: imageRect.height }
          : null;
      const staticImage = imageEl
        ? {
            present: true,
            complete: imageEl.complete,
            naturalWidth: imageEl.naturalWidth,
            naturalHeight: imageEl.naturalHeight,
          }
        : null;

      return {
        placementName: el.getAttribute("data-placement-name") ?? "",
        objectName: el.getAttribute("data-object-name") ?? null,
        zone: el.getAttribute("data-zone") ?? null,
        kind: el.getAttribute("data-kind") ?? null,
        depth: el.hasAttribute("data-depth") ? Number(el.getAttribute("data-depth")) : null,
        placeholderKind: el.getAttribute("data-placeholder-kind"),
        hasMissingSvgMarker: el.hasAttribute("data-missing-svg"),
        assetKey: el.getAttribute("data-asset"),
        hasInlineSvg: baseSvgEl !== null,
        hasDomSvgHost: domSvgHost !== null,
        staticImage,
        placementBbox,
        inlineSvgBbox,
        staticImageBbox,
      };
    });
  });

  return snapshots.map((snapshot) => {
    const classification = classifyRenderedItem(snapshot, placeholderKeys);
    return {
      placementName: snapshot.placementName,
      objectName: snapshot.objectName,
      zone: snapshot.zone,
      kind: snapshot.kind,
      depth: snapshot.depth,
      bbox: snapshot.placementBbox,
      visualBbox: selectVisualBbox(snapshot),
      ...classification,
    };
  });
}

// Collects [data-label] elements.
// Returns an array of { bbox, text } matching the labels shape scene_stats.mjs expects.
async function collect_labels(page) {
  return page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("[data-label]"));
    return els.map((el) => {
      const rect = el.getBoundingClientRect();
      const bbox =
        rect.width > 0 || rect.height > 0
          ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
          : null;
      return {
        bbox,
        text: el.textContent ?? "",
        // data-label-for ties a label to the placement it labels (render_label.ts).
        labelFor: el.getAttribute("data-label-for") ?? null,
      };
    });
  });
}

// Reads the pipeline-truth geometry summary the viewer stashed on window.
// Returns null when absent (e.g. load-failed or non-viewer page).
async function collect_scene_geometry(page) {
  return page.evaluate(() => {
    return window.__SCENE_GEOMETRY__ ?? null;
  });
}

// Collects the #scene-root bounding box.
async function collect_scene_root_bbox(page) {
  return page.evaluate(() => {
    const el = document.getElementById("scene-root");
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  });
}

// Computes an integer-pixel screenshot clip rect from the scene-root bbox,
// clamped to the viewport. Playwright rejects a clip that exceeds the page,
// so we round to whole pixels and clamp x/y/width/height inside the viewport.
// Returns null when the bbox is missing or has no positive area (caller falls
// back to a full-viewport screenshot).
function compute_scene_clip(scene_root_bbox, viewport_size) {
  if (!scene_root_bbox) return null;
  if (!viewport_size) return null;

  const vp_w = viewport_size.width;
  const vp_h = viewport_size.height;

  // Round the origin down and the far edges so the rect stays whole-pixel
  // and never extends past where the content actually is.
  let x = Math.floor(scene_root_bbox.x);
  let y = Math.floor(scene_root_bbox.y);
  const right = Math.ceil(scene_root_bbox.x + scene_root_bbox.width);
  const bottom = Math.ceil(scene_root_bbox.y + scene_root_bbox.height);

  // Clamp the origin into the viewport.
  if (x < 0) x = 0;
  if (y < 0) y = 0;

  // Clamp the far edges into the viewport, then derive width/height.
  const clamped_right = Math.min(right, vp_w);
  const clamped_bottom = Math.min(bottom, vp_h);
  const width = clamped_right - x;
  const height = clamped_bottom - y;

  // Reject degenerate rects (zero/negative area).
  if (width <= 0 || height <= 0) return null;

  return { x, y, width, height };
}

//============================================
// Render provenance
//============================================

// Builds the informational provenance stamped into the geometry dump: which
// built renderer bundle produced the geometry, and when this render ran. This
// is passed into the deterministic scene_stats module so it never reads the
// clock or filesystem itself. renderer_bundle carries the bundle mtime so a
// stale dump (built from an older bundle) is visible in the dump.
function compute_render_provenance() {
  const bundle_path = path.join(DIST_DIR, "scene_viewer.js");
  let renderer_bundle = "dist/scene_viewer.js";
  if (fs.existsSync(bundle_path)) {
    const mtime = fs.statSync(bundle_path).mtime.toISOString();
    renderer_bundle = `dist/scene_viewer.js@${mtime}`;
  }
  return {
    renderer_bundle,
    rendered_at: new Date().toISOString(),
  };
}

//============================================
// Render one scene: load, wait for ready, capture, compute stats
//============================================

// Renders one scene. Returns a result object.
// page is reused across calls; out_dir is the directory for outputs.
async function render_scene(
  page,
  base_url,
  scene_name,
  manifest_entry,
  out_dir,
  missing_svg_mode,
  placeholder_keys,
  write_png,
) {
  const t_start = Date.now();

  const url = `${base_url}/scene_viewer.html?scene=${encodeURIComponent(scene_name)}`;

  const page_errors = [];
  // Remove old listeners so reruns on the same page do not accumulate them.
  page.removeAllListeners("pageerror");
  page.on("pageerror", (err) => page_errors.push(err.message));

  let load_failed = false;

  try {
    // waitUntil:"load" is faster than "networkidle"; we wait on the ready marker next.
    await page.goto(url, { waitUntil: "load", timeout: GOTO_TIMEOUT_MS });
  } catch {
    load_failed = true;
  }

  if (!load_failed) {
    // Wait for the viewer-ready marker. This fires on EVERY path: populated,
    // placeholder-only, empty scene, AND the unknown-scene error banner.
    try {
      await page.waitForSelector("#scene-root[data-viewer-ready='true']", {
        timeout: READY_TIMEOUT_MS,
      });
    } catch {
      // Timed out waiting for the ready marker -- treat as load-failed.
      load_failed = true;
    }
  }

  if (!load_failed && page_errors.length > 0) {
    load_failed = true;
  }

  // Small settle to allow any post-ready DOM paint.
  if (!load_failed) {
    await new Promise((r) => setTimeout(r, SETTLE_MS));
  }

  // Collect DOM data (empty arrays / null on load-failed).
  let rendered_items = [];
  let labels = [];
  let scene_root_bbox = null;
  let scene_geometry = null;

  if (!load_failed) {
    rendered_items = await collect_rendered_items(page, placeholder_keys);
    labels = await collect_labels(page);
    scene_root_bbox = await collect_scene_root_bbox(page);
    scene_geometry = await collect_scene_geometry(page);
  }

  // Compute stats using the shared module. Provenance is gathered here (the
  // impure caller) and passed in so scene_stats stays deterministic.
  const provenance = compute_render_provenance();
  const stats = computeSceneStats({
    sceneName: scene_name,
    manifestEntry: manifest_entry,
    renderedItems: rendered_items,
    labels,
    sceneRootBbox: scene_root_bbox,
    sceneGeometry: scene_geometry,
    provenance,
    loadFailed: load_failed,
  });

  // Stamp the missing-svg mode so the JSON is self-documenting.
  stats.build_note = {
    missing_svg_mode,
    note: "missing_svg_mode is a passthrough flag. Changing it requires re-running bash build_github_pages.sh.",
  };

  // Save the stats JSON to the generated stats dir (NOT out_dir). Stats come
  // from DOM bbox measurement above; this write must not depend on the PNG.
  // The PNG and summary.json are human artifacts under test-results/scenes; the
  // machine stats are required validation evidence under
  // generated/scene_render_stats and are written ALWAYS, regardless of --png.
  fs.mkdirSync(STATS_DIR, { recursive: true });
  const stats_path = path.join(STATS_DIR, `${scene_name}.stats.json`);
  fs.writeFileSync(stats_path, JSON.stringify(stats, null, 2));

  // Save the PNG only when requested via --png.
  let png_path = null;
  if (write_png) {
    fs.mkdirSync(out_dir, { recursive: true });
    png_path = path.join(out_dir, `${scene_name}.png`);
    // Clip the screenshot to the #scene-root content so non-16:9 scenes do not
    // letterbox. Without this, the scene (and its proportional labels) occupies
    // only part of the 1920px-wide PNG and reads as tiny with empty margins.
    // This is a pure image-export crop; it does not touch the stats/geometry math.
    const clip_rect = compute_scene_clip(scene_root_bbox, page.viewportSize());
    if (clip_rect) {
      await page.screenshot({ path: png_path, clip: clip_rect });
    } else {
      // Bbox missing or unusable (load-failed, zero-size). Fall back to the full
      // viewport so we still emit a PNG, and warn so the cause is visible.
      console.warn(`  warning: ${scene_name} scene-root bbox unusable; capturing full viewport`);
      await page.screenshot({ path: png_path, fullPage: false });
    }
  }

  const elapsed_ms = Date.now() - t_start;
  return { scene_name, stats, png_path, stats_path, elapsed_ms, load_failed };
}

//============================================
// Human summary printer (single scene)
//============================================

function print_scene_summary(result) {
  const { scene_name, stats, elapsed_ms } = result;
  const cat = stats.classification.category;
  const counts = stats.counts;
  const layout = stats.layout;
  const flags = stats.flags.advisory_flags;

  console.log(`  scene:          ${scene_name}`);
  console.log(`  category:       ${cat}`);
  console.log(
    `  rendered:       ${counts.rendered_placement_count} / ${counts.source_placement_count} placements (${counts.render_yield_percent}% yield)`,
  );
  console.log(`  real items:     ${counts.real_item_count}`);
  console.log(`  placeholders:   ${counts.placeholder_item_count}`);
  console.log(`  approx empty:   ${layout.percent_empty_approx}%`);
  console.log(`  overlaps:       ${layout.overlap_pair_count} pairs`);
  if (counts.dropped_placement_count > 0) {
    console.log(
      `  dropped:        ${counts.dropped_placement_count} (${counts.dropped_placement_names.join(", ")})`,
    );
  }
  if (stats.flags.missing_svg_names.length > 0) {
    console.log(`  missing-svg:    ${stats.flags.missing_svg_names.join(", ")}`);
  }
  if (stats.flags.missing_object_names.length > 0) {
    console.log(`  missing-object: ${stats.flags.missing_object_names.join(", ")}`);
  }
  if (flags.length > 0) {
    console.log(`  flags:          ${flags.join(", ")}`);
  }
  console.log(`  elapsed:        ${elapsed_ms} ms`);
}

//============================================
// --all mode: console table printer
//============================================

function print_all_summary_table(results) {
  // Pad a string to width (right-truncate if too long).
  function pad(s, w) {
    const str = String(s);
    if (str.length >= w) return str.slice(0, w);
    return str + " ".repeat(w - str.length);
  }

  const header = `${"SCENE".padEnd(48)} ${"CAT".padEnd(18)} ${"YIELD".padEnd(7)} ${"REAL".padEnd(5)} ${"PH".padEnd(4)} ${"EMPTY%".padEnd(7)} ${"OVLP".padEnd(5)} ${"FLAGS".padEnd(20)} ${"MS".padEnd(6)}`;
  console.log("\n" + header);
  console.log("-".repeat(header.length));

  for (const r of results) {
    const cat = r.category;
    const yield_str = r.render_yield_percent !== undefined ? `${r.render_yield_percent}%` : "-";
    const real_str = r.real_item_count !== undefined ? String(r.real_item_count) : "-";
    const ph_str = r.placeholder_item_count !== undefined ? String(r.placeholder_item_count) : "-";
    const empty_str = r.percent_empty_approx !== undefined ? `${r.percent_empty_approx}%` : "-";
    const ovlp_str = r.overlap_pair_count !== undefined ? String(r.overlap_pair_count) : "-";
    const flags_str = (r.advisory_flags ?? []).join(",") || "-";
    const ms_str = r.elapsed_ms !== undefined ? String(r.elapsed_ms) : "-";

    const row = `${pad(r.scene_name, 48)} ${pad(cat, 18)} ${pad(yield_str, 7)} ${pad(real_str, 5)} ${pad(ph_str, 4)} ${pad(empty_str, 7)} ${pad(ovlp_str, 5)} ${pad(flags_str, 20)} ${pad(ms_str, 6)}`;
    console.log(row);
  }
}

//============================================
// Single-scene mode
//============================================

async function run_single(args) {
  const scenes = read_manifest();
  const manifest_entry = find_manifest_entry(scenes, args.scene);

  if (!manifest_entry) {
    console.error(`Scene "${args.scene}" not found in scene manifest.`);
    console.error(`Available scenes: ${scenes.map((s) => s.name).join(", ")}`);
    process.exit(1);
  }

  if (!fs.existsSync(path.join(DIST_DIR, "scene_viewer.html"))) {
    console.error("dist/scene_viewer.html not found. Run: bash build_github_pages.sh");
    process.exit(1);
  }

  // Handle manifest-skipped scene gracefully (no render).
  if (manifest_entry.outcome === "skipped") {
    console.log(`scene:    ${args.scene}`);
    console.log(`category: skipped`);
    console.log(`reason:   ${manifest_entry.reason ?? "(no reason recorded)"}`);
    console.log("No PNG rendered (scene is skipped in the manifest).");
    return;
  }

  const out_dir = args.out
    ? path.dirname(args.out)
    : path.join(REPO_ROOT, "test-results", "scenes");
  const png_override = args.out ?? null;

  await check_playwright_installed();

  const placeholder_keys = read_placeholder_keys();

  const server = await start_server(DIST_DIR);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: args.viewport });

  try {
    console.log(`Rendering scene: ${args.scene}`);
    const result = await render_scene(
      page,
      server.base_url,
      args.scene,
      manifest_entry,
      out_dir,
      args.missing_svg,
      placeholder_keys,
      args.png,
    );

    // If a specific --out path was given, move the PNG there (only when a PNG
    // was actually written via --png).
    if (result.png_path && png_override && png_override !== result.png_path) {
      fs.mkdirSync(path.dirname(png_override), { recursive: true });
      fs.renameSync(result.png_path, png_override);
      result.png_path = png_override;
    }

    console.log("");
    print_scene_summary(result);
    if (result.png_path) {
      console.log(`  png:            ${result.png_path}`);
    }
    console.log(`  stats:          ${result.stats_path}`);
  } finally {
    await browser.close();
    await server.close();
  }
}

//============================================
// --all mode
//============================================

async function run_all(args) {
  if (!fs.existsSync(path.join(DIST_DIR, "scene_viewer.html"))) {
    console.error("dist/scene_viewer.html not found. Run: bash build_github_pages.sh");
    process.exit(1);
  }

  const scenes = read_manifest();
  const out_dir = args.out ?? path.join(REPO_ROOT, "test-results", "scenes");
  fs.mkdirSync(out_dir, { recursive: true });

  await check_playwright_installed();

  const placeholder_keys = read_placeholder_keys();

  const server = await start_server(DIST_DIR);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: args.viewport });

  const summary_rows = [];
  const t_all_start = Date.now();

  try {
    for (const entry of scenes) {
      const t_scene_start = Date.now();

      // Skipped scenes: record row, no render.
      if (entry.outcome === "skipped") {
        console.log(`[skipped]  ${entry.name}  -- ${entry.reason ?? "(no reason)"}`);
        summary_rows.push({
          scene_name: entry.name,
          category: "skipped",
          render_yield_percent: undefined,
          real_item_count: undefined,
          placeholder_item_count: undefined,
          placeholder_count: undefined,
          percent_empty_approx: undefined,
          overlap_pair_count: undefined,
          advisory_flags: [],
          elapsed_ms: 0,
          reason: entry.reason ?? null,
          png_path: null,
          stats_path: null,
        });
        continue;
      }

      // Emitted scenes: render.
      let result;
      try {
        result = await render_scene(
          page,
          server.base_url,
          entry.name,
          entry,
          out_dir,
          args.missing_svg,
          placeholder_keys,
          args.png,
        );
      } catch (err) {
        // Continue past a failing render -- record load-failed row.
        const elapsed_ms = Date.now() - t_scene_start;
        const err_msg = err instanceof Error ? err.message : String(err);
        console.error(`[ERROR] ${entry.name}: ${err_msg}`);
        summary_rows.push({
          scene_name: entry.name,
          category: "load-failed",
          render_yield_percent: 0,
          real_item_count: 0,
          placeholder_item_count: 0,
          placeholder_count: 0,
          percent_empty_approx: 100,
          overlap_pair_count: 0,
          advisory_flags: [],
          elapsed_ms,
          reason: err_msg,
          png_path: null,
          stats_path: null,
        });
        continue;
      }

      const stats = result.stats;
      summary_rows.push({
        scene_name: entry.name,
        category: stats.classification.category,
        render_yield_percent: stats.counts.render_yield_percent,
        real_item_count: stats.counts.real_item_count,
        placeholder_item_count: stats.counts.placeholder_item_count,
        placeholder_count: stats.counts.placeholder_item_count,
        percent_empty_approx: stats.layout.percent_empty_approx,
        overlap_pair_count: stats.layout.overlap_pair_count,
        label_overlap_pair_count: stats.layout.label_overlap_pair_count,
        label_art_overlap_count: stats.layout.label_art_overlap_count,
        advisory_flags: stats.flags.advisory_flags,
        elapsed_ms: result.elapsed_ms,
        reason: null,
        png_path: result.png_path,
        stats_path: result.stats_path,
      });

      const cat = stats.classification.category;
      console.log(`[${cat.padEnd(16)}] ${entry.name}  (${result.elapsed_ms} ms)`);
    }
  } finally {
    await browser.close();
    await server.close();
  }

  const total_ms = Date.now() - t_all_start;

  // Write summary.json.
  const summary_path = path.join(out_dir, "summary.json");
  fs.writeFileSync(
    summary_path,
    JSON.stringify({ generated_at: new Date().toISOString(), scenes: summary_rows }, null, 2),
  );

  // Print table + totals.
  print_all_summary_table(summary_rows);

  // Category counts.
  const cat_counts = {};
  for (const row of summary_rows) {
    cat_counts[row.category] = (cat_counts[row.category] ?? 0) + 1;
  }

  console.log("\n--- Category totals ---");
  for (const [cat, count] of Object.entries(cat_counts).sort()) {
    console.log(`  ${cat.padEnd(20)} ${count}`);
  }
  console.log(`  ${"TOTAL".padEnd(20)} ${summary_rows.length}`);
  console.log(`\nTotal elapsed: ${total_ms} ms  (${(total_ms / 1000).toFixed(1)} s)`);
  console.log(`Summary written to: ${summary_path}`);
}

//============================================
// Entry point
//============================================

async function main() {
  let args;
  try {
    args = parse_args(process.argv);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`Usage error: ${msg}`);
    console.error("Usage: node tools/scene_to_png.mjs --scene <name> | --all [options]");
    process.exit(1);
  }

  if (args.scene) {
    await run_single(args);
  } else {
    await run_all(args);
  }
}

main().catch((err) => {
  console.error("scene_to_png error:", err);
  process.exit(1);
});
