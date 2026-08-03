#!/usr/bin/env node
/* global document, HTMLElement, SVGGElement, window */
// Build a self-contained HTML and PNG volume contact sheet through the real
// compiled-material SVG injection and liquid writer. Outputs are developer
// evidence under rendered-reports/, never generated/, dist/, or test-results/.

import { randomBytes } from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { build } from "esbuild";
import { firefox } from "playwright";

const DEFAULT_VOLUMES = Object.freeze([0, 5, 10, 25, 50, 75, 85, 90, 100]);
const ASSET_RE = /^[a-z][a-z0-9_]*$/;
const COLOR_RE = /^#[0-9a-fA-F]{6}$/;

//============================================
export function formatDebugNumber(value) {
  if (!Number.isFinite(value)) {
    throw new Error("debug number must be finite");
  }
  const rounded = Number(value.toFixed(3));
  return Object.is(rounded, -0) ? "0" : String(rounded);
}

//============================================
export function effectiveFillDiagnostics(requestedPercent, maxFillPercent, minFillPercent = null) {
  if (!Number.isFinite(requestedPercent) || requestedPercent < 0 || requestedPercent > 100) {
    throw new Error("requested fill must be a finite percentage in [0, 100]");
  }
  if (
    maxFillPercent !== null &&
    (!Number.isFinite(maxFillPercent) || maxFillPercent < 0 || maxFillPercent > 100)
  ) {
    throw new Error("max fill must be null or a finite percentage in [0, 100]");
  }
  if (
    minFillPercent !== null &&
    (!Number.isFinite(minFillPercent) || minFillPercent < 0 || minFillPercent > 100)
  ) {
    throw new Error("min fill must be null or a finite percentage in [0, 100]");
  }
  const upperBoundedPercent = Math.min(requestedPercent, maxFillPercent ?? 100);
  const effectivePercent =
    upperBoundedPercent === 0 ? 0 : Math.max(upperBoundedPercent, minFillPercent ?? 0);
  return { effectivePercent, clamped: effectivePercent !== requestedPercent };
}

//============================================
export function formatCreationTimestamp(value) {
  const createdAt = new Date(value);
  if (!Number.isFinite(createdAt.getTime())) {
    throw new Error("creation timestamp must be a valid date");
  }
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(createdAt);
}

const MIME_TYPES = Object.freeze({
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".woff2": "font/woff2",
});

//============================================
export function parseVolumeList(raw) {
  const values = raw.split(",").map((part) => Number(part));
  if (
    values.length === 0 ||
    values.some((value) => !Number.isFinite(value) || value < 0 || value > 100)
  ) {
    throw new Error("volumes must be comma-separated finite numbers in [0, 100]");
  }
  return values;
}

//============================================
export function parseColorList(raw) {
  const colors = raw.split(",");
  if (colors.length === 0 || colors.some((color) => !COLOR_RE.test(color))) {
    throw new Error("colors must be comma-separated #rrggbb values");
  }
  return colors.map((color) => color.toLowerCase());
}

//============================================
export function assignAssetColors(assetNames, colors) {
  if (colors.length === 0) {
    throw new Error("at least one contact-sheet color is required");
  }
  return assetNames.map((_, index) => colors[index % colors.length]);
}

//============================================
export function previousAssetColors(markup) {
  if (markup === null) {
    return new Set();
  }
  const colors = new Set();
  for (const match of markup.matchAll(/data-asset-color="(#[0-9a-fA-F]{6})"/g)) {
    colors.add(match[1].toLowerCase());
  }
  // Read the legacy inline style too, so the first random build cannot repeat
  // any color from the formerly fixed palette.
  for (const match of markup.matchAll(/--asset-color:\s*(#[0-9a-fA-F]{6})/g)) {
    colors.add(match[1].toLowerCase());
  }
  return colors;
}

//============================================
export function generateRandomColors(count, excludedColors = new Set(), byteSource = randomBytes) {
  if (!Number.isInteger(count) || count <= 0) {
    throw new Error("random color count must be a positive integer");
  }
  const excluded = new Set(Array.from(excludedColors, (color) => color.toLowerCase()));
  const colors = [];
  for (let attempt = 0; colors.length < count && attempt < 10_000; attempt += 1) {
    const bytes = byteSource(3);
    if (!(bytes instanceof Uint8Array) || bytes.length < 3) {
      throw new Error("random color source must return at least three bytes");
    }
    const color = `#${Array.from(bytes.slice(0, 3), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("")}`;
    if (!excluded.has(color) && !colors.includes(color)) {
      colors.push(color);
    }
  }
  if (colors.length !== count) {
    throw new Error("could not generate enough distinct random colors");
  }
  return colors;
}

//============================================
export function parseArgs(argv) {
  const positional = [];
  const assetNotes = {};
  let colors = null;
  let volumes = [...DEFAULT_VOLUMES];
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--color") {
      colors = parseColorList(argv.at(index + 1) ?? "");
      index += 1;
    } else if (value === "--colors") {
      colors = parseColorList(argv.at(index + 1) ?? "");
      index += 1;
    } else if (value === "--volumes") {
      volumes = parseVolumeList(argv.at(index + 1) ?? "");
      index += 1;
    } else if (value === "--note") {
      const rawNote = argv.at(index + 1) ?? "";
      const separator = rawNote.indexOf("=");
      const assetName = rawNote.slice(0, separator);
      const note = rawNote.slice(separator + 1);
      if (separator <= 0 || !ASSET_RE.test(assetName) || note.trim().length === 0) {
        throw new Error("notes must use asset_name=explanation syntax");
      }
      assetNotes[assetName] = note.trim();
      index += 1;
    } else if (value.startsWith("-")) {
      throw new Error(`unknown option: ${value}`);
    } else {
      positional.push(value);
    }
  }
  if (positional.length === 0 || positional.some((assetName) => !ASSET_RE.test(assetName))) {
    throw new Error(
      "usage: node tools/liquid_volume_contact_page.mjs <asset_name> [asset_name ...] " +
        "[--color #rrggbb | --colors #rrggbb,#rrggbb,...] " +
        "[--volumes 0,5,10,25,50,75,85,90,100] " +
        "[--note asset_name=explanation]",
    );
  }
  const unknownNote = Object.keys(assetNotes).find((assetName) => !positional.includes(assetName));
  if (unknownNote !== undefined) {
    throw new Error(`note names unselected asset: ${unknownNote}`);
  }
  return {
    assetNames: positional,
    assetNotes,
    colors,
    volumes,
  };
}

//============================================
function safeDistPath(distRoot, requestUrl) {
  const pathname = decodeURIComponent(new URL(requestUrl, "http://127.0.0.1").pathname);
  const relative = pathname === "/" ? "bench_basic.html" : pathname.slice(1);
  if (relative.split("/").includes("..")) {
    return null;
  }
  const candidate = path.resolve(distRoot, relative);
  const prefix = `${path.resolve(distRoot)}${path.sep}`;
  return candidate.startsWith(prefix) ? candidate : null;
}

//============================================
async function startDistServer(distRoot) {
  const server = http.createServer((request, response) => {
    const requested = safeDistPath(distRoot, request.url ?? "/");
    if (requested === null) {
      response.writeHead(400).end("invalid path");
      return;
    }
    fs.readFile(requested, (error, content) => {
      if (error !== null) {
        response.writeHead(error.code === "ENOENT" ? 404 : 500).end("not found");
        return;
      }
      const contentType = MIME_TYPES[path.extname(requested)] ?? "application/octet-stream";
      response.writeHead(200, { "Content-Type": contentType }).end(content);
    });
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (address === null || typeof address === "string") {
    server.close();
    throw new Error("contact-page server did not receive a TCP port");
  }
  return { server, origin: `http://127.0.0.1:${address.port}` };
}

//============================================
function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

//============================================
function contactMarkup(assetNames, assetNotes, assetColors, volumes, createdAtIso, colorMode) {
  const assetSections = assetNames
    .map((assetName, assetIndex) => {
      const cards = volumes
        .map(
          (volume, volumeIndex) => `
        <article class="card" data-volume="${volume}">
          <h3>${formatDebugNumber(volume)}% requested</h3>
          <div class="asset" id="asset-${assetIndex}-${volumeIndex}"></div>
          <p class="details">rendering</p>
        </article>`,
        )
        .join("");
      const note = assetNotes[assetName];
      const assetColor = assetColors[assetIndex];
      return `
    <section class="asset-group" data-asset-name="${assetName}" data-asset-color="${assetColor}" style="--asset-color: ${assetColor}">
      <h2>${assetName} <span class="color-swatch" aria-hidden="true"></span><code>${assetColor}</code></h2>
      ${note === undefined ? "" : `<p class="asset-note">${escapeHtml(note)}</p>`}
      <div class="cards">${cards}</div>
    </section>`;
    })
    .join("");
  const title = assetNames.length === 1 ? assetNames[0] : "Variable-volume assets";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title} volume contact sheet</title>
  <style>
    :root { color-scheme: light; font-family: system-ui, sans-serif; background: #f3f5f7; }
    body { margin: 0; padding: 24px; color: #17212b; }
    header { margin: 0 0 18px; }
    h1 { margin: 0 0 6px; font-size: 26px; }
    header p { margin: 3px 0; color: #52606d; }
    code { background: #e6eaee; border-radius: 4px; padding: 2px 5px; }
    main { display: grid; gap: 24px; }
    .asset-group > h2 { margin: 0 0 10px; font-size: 22px; }
    .color-swatch { width: 0.8em; height: 0.8em; margin: 0 5px 0 8px; display: inline-block;
      border: 1px solid #52606d; border-radius: 50%; background: var(--asset-color); }
    .asset-note { margin: -4px 0 10px; color: #52606d; }
    .cards { display: grid; grid-template-columns: repeat(${volumes.length}, minmax(150px, 1fr)); gap: 12px; }
    .card { background: white; border: 1px solid #cbd3da; border-radius: 10px; padding: 12px;
      box-shadow: 0 2px 8px rgb(23 33 43 / 8%); }
    h3 { min-height: 2.4em; margin: 0; display: flex; align-items: center;
      justify-content: center; text-align: center; font-size: 20px; }
    .asset { height: 330px; display: flex; align-items: center; justify-content: center;
      background: linear-gradient(135deg, #fff 0 50%, #f6f2e9 50%); overflow: hidden; }
    .asset svg { width: 100%; height: 100%; display: block; }
    .details { min-height: 5.8em; margin: 8px 0 0; color: #52606d; font: 12px/1.3 ui-monospace, monospace;
      overflow-wrap: anywhere; white-space: pre-line; }
  </style>
</head>
<body data-contact-created-at="${createdAtIso}" data-color-mode="${colorMode}">
  <header>
    <h1>${title}: volume contact sheet</h1>
    <p><strong>Created:</strong> <time datetime="${createdAtIso}">${formatCreationTimestamp(createdAtIso)}</time></p>
    <p><strong>Build ID:</strong> <code>${createdAtIso}</code>; <strong>color mode:</strong> ${colorMode}.</p>
    <p>Real compiled SVG injection and liquid writer; default colors are newly randomized per asset on every rebuild.</p>
    <p>Each card reports requested fill, rendered fill, clamp state, and surface coordinate.</p>
    <p>Each card is serialized after rendering, so this file remains self-contained.</p>
  </header>
  <main>${assetSections}</main>
</body>
</html>`;
}

//============================================
async function buildHarness(outputPath) {
  await build({
    entryPoints: ["tools/liquid_render_harness.ts"],
    outfile: outputPath,
    bundle: true,
    format: "iife",
    target: "es2020",
    platform: "browser",
    logLevel: "silent",
  });
}

//============================================
async function renderContactPage(
  page,
  assetNames,
  assetNotes,
  fillDiagnostics,
  assetColors,
  volumes,
  harnessPath,
  createdAtIso,
  colorMode,
) {
  await page.setContent(
    contactMarkup(assetNames, assetNotes, assetColors, volumes, createdAtIso, colorMode),
  );
  await page.addScriptTag({ path: harnessPath });
  await page.evaluate(
    async ({ selectedAssets, selectedColors, selectedVolumes, selectedFillDiagnostics }) => {
      function formatNumber(value) {
        const rounded = Number(value.toFixed(3));
        return Object.is(rounded, -0) ? "0" : String(rounded);
      }
      const response = await fetch("assets/liquid_regions.json");
      const manifest = await response.json();
      for (let assetIndex = 0; assetIndex < selectedAssets.length; assetIndex += 1) {
        const selectedAsset = selectedAssets[assetIndex];
        const entry = manifest[selectedAsset];
        if (typeof entry !== "object" || entry === null) {
          throw new Error(`missing liquid manifest entry for ${selectedAsset}`);
        }
        for (let volumeIndex = 0; volumeIndex < selectedVolumes.length; volumeIndex += 1) {
          const volume = selectedVolumes[volumeIndex];
          const host = document.querySelector(`#asset-${assetIndex}-${volumeIndex}`);
          if (!(host instanceof HTMLElement)) {
            throw new Error(`missing contact host ${assetIndex}:${volumeIndex}`);
          }
          const rendered = await window.liquidRenderHarness.injectAndRender(
            host,
            selectedAsset,
            `volume_contact_${selectedAsset}_${volumeIndex}`,
            volume === 0 ? null : selectedColors[assetIndex],
            volume,
          );
          if (!rendered) {
            throw new Error(`${selectedAsset} did not use compiled liquid rendering`);
          }
          const region = Array.from(host.querySelectorAll("g")).find((group) =>
            group.id.endsWith(`__${entry.region_handle}`),
          );
          if (!(region instanceof SVGGElement)) {
            throw new Error(`${selectedAsset} liquid region missing at ${volume}%`);
          }
          const partTransforms = entry.paints.map((paint) => {
            const element = Array.from(host.querySelectorAll("g")).find((group) =>
              group.id.endsWith(`__${paint.element_handle}`),
            );
            return `${paint.liquid_part}: ${element?.getAttribute("transform") ?? "fixed"}`;
          });
          const detail = host.parentElement?.querySelector(".details");
          if (detail instanceof HTMLElement) {
            const fill = selectedFillDiagnostics[assetIndex][volumeIndex];
            const reveal = Array.from(host.querySelectorAll("rect")).find((rect) =>
              rect.id.endsWith(`__${entry.reveal_handle}`),
            );
            const surfaceY = reveal?.getAttribute("y");
            const details = [
              `requested: ${formatNumber(volume)}%`,
              `rendered fill: ${formatNumber(fill.effectivePercent)}%`,
              `clamped: ${fill.clamped ? "yes" : "no"}`,
              volume === 0
                ? "liquid region: hidden"
                : `surface y: ${formatNumber(Number(surfaceY))}`,
            ];
            if (volume > 0) {
              details.push(...new Set(partTransforms));
            }
            detail.textContent = details.join("\n");
          }
        }
      }
      document.querySelectorAll("script").forEach((script) => script.remove());
    },
    {
      selectedAssets: assetNames,
      selectedColors: assetColors,
      selectedVolumes: volumes,
      selectedFillDiagnostics: fillDiagnostics,
    },
  );
}

//============================================
async function closeServer(server) {
  await new Promise((resolve, reject) => {
    server.close((error) => (error === undefined ? resolve() : reject(error)));
  });
}

//============================================
export async function main(argv = process.argv.slice(2)) {
  const { assetNames, assetNotes, colors, volumes } = parseArgs(argv);
  const createdAtIso = new Date().toISOString();
  const distRoot = "dist";
  const manifestPath = path.join(distRoot, "assets", "liquid_regions.json");
  if (!fs.existsSync(manifestPath)) {
    throw new Error("missing dist/assets/liquid_regions.json; run ./build_github_pages.sh first");
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const fillDiagnostics = assetNames.map((assetName) => {
    const entry = manifest[assetName];
    if (typeof entry !== "object" || entry === null) {
      throw new Error(`missing liquid manifest entry for ${assetName}`);
    }
    return volumes.map((volume) =>
      effectiveFillDiagnostics(volume, entry.max_fill_percent, entry.min_fill_percent),
    );
  });
  const outputDirectory = path.join("rendered-reports", "liquid_volume_contacts");
  fs.mkdirSync(outputDirectory, { recursive: true });
  const outputStem = assetNames.length === 1 ? assetNames[0] : "all_variable_volume_assets";
  const htmlPath = path.join(outputDirectory, `${outputStem}.html`);
  const pngPath = path.join(outputDirectory, `${outputStem}.png`);
  const previousMarkup = fs.existsSync(htmlPath) ? fs.readFileSync(htmlPath, "utf8") : null;
  const colorMode = colors === null ? "random" : "explicit";
  const selectedColors =
    colors ?? generateRandomColors(assetNames.length, previousAssetColors(previousMarkup));
  const assetColors = assignAssetColors(assetNames, selectedColors);
  const temporaryDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "liquid_contact_"));
  const harnessPath = path.join(temporaryDirectory, "harness.js");
  await buildHarness(harnessPath);
  const { server, origin } = await startDistServer(distRoot);
  const browser = await firefox.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1540, height: 900 } });
    await page.goto(`${origin}/bench_basic.html`, { waitUntil: "networkidle" });
    await renderContactPage(
      page,
      assetNames,
      assetNotes,
      fillDiagnostics,
      assetColors,
      volumes,
      harnessPath,
      createdAtIso,
      colorMode,
    );
    fs.writeFileSync(htmlPath, await page.content(), "utf8");
    await page.screenshot({ path: pngPath, fullPage: true });
  } finally {
    await browser.close();
    await closeServer(server);
  }
  console.log(`wrote ${htmlPath}`);
  console.log(`wrote ${pngPath}`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`ERROR: ${error.message}`);
    process.exitCode = 1;
  });
}
