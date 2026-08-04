// tests/playwright/material_render_capture.mjs
//
// Capture the material surfaces that a student sees at the authoritative
// initial state of every emitted protocol-host page.  A standalone scene viewer
// deliberately has no active protocol material registry, so it is useful for
// scene geometry but is not evidence for material identity colors.
//
// The capture is declarative: it discovers the two generic renderer surfaces
// rather than naming objects or protocols:
//   - liquid_region: compiled semantic liquid groups
//   - subpart: generated structured-subpart material shapes
//
// Each visible surface gets a before/after pair with only that one surface
// hidden.  The Python companion uses that pair to measure the actual painted
// footprint without assuming a flat RGB color or a particular SVG silhouette.

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const DIST_DIR = path.join(REPO_ROOT, "dist");
const PROTOCOLS_PATH = path.join(REPO_ROOT, "generated", "protocols.ts");
const VIEWPORT = { width: 1920, height: 1080 };
const READY_TIMEOUT_MS = 10000;

const MIME_MAP = {
  ".css": "text/css",
  ".html": "text/html",
  ".js": "application/javascript",
  ".json": "application/json",
  ".mjs": "application/javascript",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

function start_server(dist_dir) {
  const dist_root = path.resolve(dist_dir);
  const server = http.createServer((req, res) => {
    const request_url = new URL(req.url ?? "/", "http://127.0.0.1");
    const relative_path = request_url.pathname === "/" ? "/index.html" : request_url.pathname;
    const file_path = path.resolve(dist_root, `.${relative_path}`);
    if (file_path !== dist_root && !file_path.startsWith(`${dist_root}${path.sep}`)) {
      res.writeHead(403, { "Content-Type": "text/plain" });
      res.end("Path escapes the built artifact directory");
      return;
    }
    const extension = path.extname(file_path);
    fs.readFile(file_path, (error, data) => {
      if (error) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end(`Not found: ${relative_path}`);
        return;
      }
      res.writeHead(200, { "Content-Type": MIME_MAP[extension] ?? "application/octet-stream" });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.listen(0, "127.0.0.1", () => resolve(server));
    server.on("error", reject);
  });
}

function read_emitted_protocol_names() {
  if (!fs.existsSync(PROTOCOLS_PATH)) {
    throw new Error(`Protocol index not found: ${PROTOCOLS_PATH}`);
  }
  const source = fs.readFileSync(PROTOCOLS_PATH, "utf8");
  const index_start = source.indexOf("export const PROTOCOLS_INDEX");
  const index_end = source.indexOf("] as const", index_start);
  if (index_start < 0 || index_end < 0) {
    throw new Error("Could not locate PROTOCOLS_INDEX in generated/protocols.ts");
  }
  const names = [
    ...source.slice(index_start, index_end).matchAll(/protocol_name:\s*'([a-z0-9_]+)'/g),
  ].map((match) => match[1]);
  if (names.length === 0 || names.some((name) => name === undefined)) {
    throw new Error("PROTOCOLS_INDEX has no emitted protocol names");
  }
  for (const name of names) {
    if (!fs.existsSync(path.join(DIST_DIR, `${name}.html`))) {
      throw new Error(
        `Protocol host page missing: dist/${name}.html; run bash build_github_pages.sh`,
      );
    }
  }
  return names;
}

function sanitize_for_filename(value) {
  return value.replace(/[^a-zA-Z0-9_-]/g, "_");
}

function surface_selector() {
  // Liquid runtime metadata belongs to the injected DOM-SVG host. Asset and
  // placement identity belong to its enclosing scene item, so do not require
  // both contracts to be stamped on one element.
  return [
    "[data-liquid-material-field]",
    "[data-subpart-name][data-material-field][data-material-name]",
  ].join(", ");
}

async function wait_for_protocol_scene(page) {
  await page.waitForSelector("#scene-root[data-active-scene] [data-placement-name]", {
    state: "attached",
    timeout: READY_TIMEOUT_MS,
  });
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll('[data-svg-render-mode="dom-svg"]')).every(
        (host) =>
          host.querySelector("svg") !== null ||
          (host.getAttribute("data-svg-load-error") ?? "") !== "",
      ),
    undefined,
    { timeout: READY_TIMEOUT_MS },
  );
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(resolve));
    await new Promise((resolve) => requestAnimationFrame(resolve));
  });
}

async function assert_scene_not_degraded(page, protocol_name, browser_diagnostics) {
  const degradation = await page.evaluate(() => {
    const root = document.querySelector("#scene-root");
    const items = Array.from(document.querySelectorAll("[data-resolver-degraded]")).map(
      (element) => ({
        placement_name:
          element.closest("[data-placement-name]")?.getAttribute("data-placement-name") ?? "",
        message: element.getAttribute("data-resolver-degraded") ?? "",
      }),
    );
    const svg_load_failures = Array.from(
      document.querySelectorAll('[data-svg-load-error]:not([data-svg-load-error=""])'),
    ).map((element) => element.getAttribute("data-svg-load-error") ?? "");
    return {
      scene_degraded: root?.getAttribute("data-scene-degraded") ?? "",
      structural_violation_count: root?.getAttribute("data-degraded-violation-count") ?? "",
      items,
      svg_load_failures,
    };
  });
  if (
    degradation.scene_degraded === "true" ||
    degradation.items.length > 0 ||
    degradation.svg_load_failures.length > 0
  ) {
    const resolver_details = degradation.items
      .map((item) => `${item.placement_name}: ${item.message}`)
      .join("; ");
    const details = [
      degradation.structural_violation_count === ""
        ? ""
        : `structural violations=${degradation.structural_violation_count}`,
      resolver_details === "" ? "" : `resolver failures=${resolver_details}`,
      degradation.svg_load_failures.length === 0
        ? ""
        : `SVG load failures=${degradation.svg_load_failures.join(" | ")}`,
      browser_diagnostics.length === 0
        ? ""
        : `browser diagnostics=${browser_diagnostics.join(" | ")}`,
    ]
      .filter((detail) => detail !== "")
      .join("; ");
    throw new Error(`Protocol ${protocol_name} rendered a degraded material scene: ${details}`);
  }
}

async function collect_surfaces(page) {
  return page.evaluate(async (selector) => {
    function rect_to_record(rect) {
      return { x: rect.x, y: rect.y, w: rect.width, h: rect.height };
    }
    function kind_for(source_element) {
      if (source_element.matches("[data-liquid-material-field]")) {
        return "liquid_region";
      }
      return "subpart";
    }
    function fill_for(element, style, kind, source_element) {
      if (kind === "liquid_region") {
        return source_element.getAttribute("data-liquid-color") ?? "";
      }
      if (element instanceof SVGElement) return style.fill;
      return style.backgroundColor;
    }
    function has_visible_paint(element, style, geometry, kind, source_element) {
      const fill = fill_for(element, style, kind, source_element);
      const rgba_match = /^rgba\(([^)]+)\)$/.exec(fill);
      const rgba_parts = rgba_match === null ? [] : rgba_match[1].split(",");
      const alpha = rgba_parts.length === 4 ? Number(rgba_parts[3]) : 1;
      return (
        geometry.width > 0 &&
        geometry.height > 0 &&
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0" &&
        fill !== "none" &&
        fill !== "transparent" &&
        alpha > 0
      );
    }

    const missing_field_shapes = document.querySelectorAll(
      "[data-subpart-overlay] [data-subpart-name][data-material-name]:not([data-material-field])",
    );
    if (missing_field_shapes.length > 0) {
      throw new Error("Structured material shapes are missing their declared material field");
    }

    const liquid_manifest = await fetch("/assets/liquid_regions.json").then((response) =>
      response.json(),
    );
    const surfaces = [];
    for (const [index, source_element] of Array.from(
      document.querySelectorAll(selector),
    ).entries()) {
      const owner = source_element.closest("[data-placement-name][data-object-name]");
      if (owner === null) {
        throw new Error("Material surface is not owned by a declared scene placement");
      }
      const kind = kind_for(source_element);
      let element = source_element;
      if (kind === "liquid_region") {
        const asset_name = owner.getAttribute("data-asset") ?? "";
        if (asset_name === "") {
          throw new Error("Compiled liquid host has no owning asset identity");
        }
        const region_handle = liquid_manifest[asset_name]?.region_handle;
        if (typeof region_handle !== "string" || region_handle === "") {
          throw new Error(`Compiled liquid manifest entry is missing for ${asset_name}`);
        }
        element = Array.from(owner.querySelectorAll("g")).find((group) =>
          group.id.endsWith(`__${region_handle}`),
        );
        if (!(element instanceof SVGGElement)) {
          throw new Error(`Compiled liquid region is missing for ${asset_name}`);
        }
      }
      element.setAttribute("data-material-capture-id", `surface_${index}`);
      const geometry = element.getBoundingClientRect();
      const owner_geometry = owner.getBoundingClientRect();
      if (owner_geometry.width <= 0 || owner_geometry.height <= 0) {
        throw new Error("Material surface owner has no rendered geometry");
      }
      const style = window.getComputedStyle(element);
      const driving_field =
        kind === "liquid_region"
          ? (source_element.getAttribute("data-liquid-material-field") ?? "")
          : (element.getAttribute("data-material-field") ?? "");
      const subpart_name =
        kind === "subpart" ? (element.getAttribute("data-subpart-name") ?? "") : "";
      const material_name =
        kind === "liquid_region"
          ? (source_element.getAttribute("data-liquid-material-name") ?? "")
          : (element.getAttribute("data-material-name") ??
            owner.getAttribute("data-material") ??
            "");
      const visible = has_visible_paint(element, style, geometry, kind, source_element);
      if (driving_field === "") {
        throw new Error("Material surface has no declared driving field");
      }
      if (visible && material_name === "") {
        throw new Error("Visible material surface has no material identity");
      }
      surfaces.push({
        capture_id: `surface_${index}`,
        kind,
        placement_name:
          owner.getAttribute("data-placement-name") ?? owner.getAttribute("data-item-id") ?? "",
        object_name: owner.getAttribute("data-object-name") ?? "",
        driving_field,
        subpart_name,
        material_name,
        computed_fill: fill_for(element, style, kind, source_element),
        visible,
        geometry: rect_to_record(geometry),
        owner_geometry: rect_to_record(owner_geometry),
      });
    }
    return surfaces;
  }, surface_selector());
}

async function hide_surface(page, capture_id, hidden) {
  await page.evaluate(
    ({ id, hide }) => {
      const element = document.querySelector(`[data-material-capture-id="${id}"]`);
      if (!(element instanceof HTMLElement || element instanceof SVGElement)) {
        throw new Error(`Material surface ${id} disappeared before capture`);
      }
      element.setAttribute("data-material-capture-hidden", hide ? "true" : "false");
      if (hide) {
        element.setAttribute("data-material-capture-original-visibility", element.style.visibility);
        element.style.setProperty("visibility", "hidden");
      } else {
        const original = element.getAttribute("data-material-capture-original-visibility") ?? "";
        element.style.setProperty("visibility", original);
        element.removeAttribute("data-material-capture-original-visibility");
      }
    },
    { id: capture_id, hide: hidden },
  );
}

async function capture_protocol(page, base_url, protocol_name, out_dir) {
  const browser_diagnostics = [];
  const on_console = (message) => {
    if (message.type() === "warning" || message.type() === "error") {
      browser_diagnostics.push(`${message.type()}: ${message.text()}`);
    }
  };
  const on_page_error = (error) => {
    browser_diagnostics.push(`pageerror: ${error.message}`);
  };
  page.on("console", on_console);
  page.on("pageerror", on_page_error);
  try {
    await page.goto(`${base_url}/${protocol_name}.html?shell=off`, { waitUntil: "load" });
    await wait_for_protocol_scene(page);
    await assert_scene_not_degraded(page, protocol_name, browser_diagnostics);
    const active_scene = await page.locator("#scene-root").getAttribute("data-active-scene");
    if (active_scene === null || active_scene === "") {
      throw new Error(`Protocol ${protocol_name} reached no active initial scene`);
    }
    const surfaces = await collect_surfaces(page);
    const visible_surfaces = surfaces.filter((surface) => surface.visible);
    let png_before = null;
    if (visible_surfaces.length > 0) {
      png_before = `${protocol_name}.initial.png`;
      await page.screenshot({ path: path.join(out_dir, png_before) });
    }
    for (const surface of visible_surfaces) {
      await hide_surface(page, surface.capture_id, true);
      const png_after = `${protocol_name}.initial.no_${sanitize_for_filename(surface.capture_id)}.png`;
      await page.screenshot({ path: path.join(out_dir, png_after) });
      await hide_surface(page, surface.capture_id, false);
      surface.png_after = png_after;
    }
    return { protocol_name, initial_scene: active_scene, png_before, surfaces };
  } finally {
    page.off("console", on_console);
    page.off("pageerror", on_page_error);
  }
}

async function main() {
  const out_dir = process.argv[2];
  if (!out_dir) throw new Error("Usage: material_render_capture.mjs <out_dir>");
  if (!fs.existsSync(path.join(DIST_DIR, "protocol_host.js"))) {
    throw new Error("dist/protocol_host.js not found. Run: bash build_github_pages.sh");
  }
  fs.mkdirSync(out_dir, { recursive: true });
  const protocol_names = read_emitted_protocol_names();
  const server = await start_server(DIST_DIR);
  const address = server.address();
  const base_url = `http://127.0.0.1:${address.port}`;
  let browser = null;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: VIEWPORT });
    const protocols = [];
    const failures = [];
    for (const protocol_name of protocol_names) {
      try {
        const record = await capture_protocol(page, base_url, protocol_name, out_dir);
        protocols.push(record);
        console.log(`${protocol_name}: ${record.surfaces.length} material surface(s)`);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        failures.push(`${protocol_name}: ${message}`);
        console.error(`${protocol_name}: CAPTURE FAILED: ${message}`);
      }
    }
    if (failures.length > 0) {
      throw new Error(
        `Material capture failed for ${failures.length} protocol(s):\n${failures.join("\n")}`,
      );
    }
    const payload = {
      schema_version: "protocol-host-material-surfaces-v3",
      generated_at: new Date().toISOString(),
      viewport: VIEWPORT,
      protocols,
    };
    fs.writeFileSync(path.join(out_dir, "capture.json"), JSON.stringify(payload, null, 2));
  } finally {
    if (browser !== null) {
      await browser.close();
    }
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error("material_render_capture error:", error);
  process.exit(1);
});
