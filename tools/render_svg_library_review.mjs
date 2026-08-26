#!/usr/bin/env node

/** Generate the tracked, file://-usable equipment source gallery. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ASSET_ROOT = path.join(REPO_ROOT, "assets", "equipment");
const OUTPUT_PATH = path.join(REPO_ROOT, "docs", "figures", "equipment_kit", "review.html");
const PROTECTED_RESULT_NAMES = new Set([
  "cell_viability_results_display",
  "electrophoresis_endpoint_display",
  "gel_image_results_display",
  "hemocytometer_observation_display",
  "mtt_reader_results_display",
  "plate_reader_absorbance_result_panel",
  "plate_reader_normalized_viability_panel",
]);

function listSvgFiles(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...listSvgFiles(entryPath));
    if (entry.isFile() && entry.name.endsWith(".svg")) files.push(entryPath);
  }
  return files.sort((left, right) => left.localeCompare(right));
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function displayName(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function asGalleryPath(filePath) {
  return path.relative(path.dirname(OUTPUT_PATH), filePath).split(path.sep).join("/");
}

function buildAssets() {
  const files = listSvgFiles(ASSET_ROOT);
  if (files.length === 0) throw new Error(`No SVG files found below ${ASSET_ROOT}`);

  return files.map((filePath) => {
    const relativePath = path.relative(ASSET_ROOT, filePath).split(path.sep).join("/");
    const [family] = relativePath.split("/");
    const name = path.basename(filePath, ".svg");
    return {
      family,
      galleryPath: asGalleryPath(filePath),
      name,
      protectedResult: PROTECTED_RESULT_NAMES.has(name),
    };
  });
}

function groupByFamily(assets) {
  const families = new Map();
  for (const asset of assets) {
    const familyAssets = families.get(asset.family) ?? [];
    familyAssets.push(asset);
    families.set(asset.family, familyAssets);
  }
  return families;
}

function cardHtml(asset) {
  const family = escapeHtml(asset.family);
  const galleryPath = escapeHtml(asset.galleryPath);
  const name = escapeHtml(displayName(asset.name));
  const protectedBadge = asset.protectedResult
    ? '\n                <span class="badge badge--protected">Protected result UI</span>'
    : "";

  return `          <article class="asset-card" data-family="${family}">
            <a class="asset-frame" href="${galleryPath}" target="_blank">
              <img src="${galleryPath}" alt="${name} authored SVG" />
            </a>
            <div class="asset-copy">
              <h3>${name}</h3>
              <div class="badges">
                <span class="badge">${family}</span>${protectedBadge}
              </div>
              <a class="asset-path" href="${galleryPath}" target="_blank">${galleryPath}</a>
            </div>
          </article>`;
}

function familySectionHtml(family, assets) {
  const safeFamily = escapeHtml(family);
  const title = escapeHtml(displayName(family));
  const cards = assets.map(cardHtml).join("\n");

  return `      <section class="family" data-family-section="${safeFamily}"
        aria-labelledby="${safeFamily}-heading">
        <header class="family-heading">
          <div>
            <p class="eyebrow">Authored behavior</p>
            <h2 id="${safeFamily}-heading">${title}</h2>
          </div>
          <p><span data-family-count="${safeFamily}">${assets.length}</span> source assets</p>
        </header>
        <div class="asset-grid">
${cards}
        </div>
      </section>`;
}

function familyOptionsHtml(families) {
  return [...families.keys()]
    .map((family) => {
      const safeFamily = escapeHtml(family);
      const title = escapeHtml(displayName(family));
      return `              <option value="${safeFamily}">${title}</option>`;
    })
    .join("\n");
}

function familySectionsHtml(families) {
  return [...families].map(([family, assets]) => familySectionHtml(family, assets)).join("\n");
}

function pageCss() {
  return `
      :root {
        color-scheme: light dark;
        --canvas: #ece9df;
        --surface: #fffdf8;
        --surface-raised: #fff;
        --ink: #19323e;
        --muted: #51636b;
        --line: #b8c5c8;
        --accent: #0d617f;
        --accent-ink: #063c51;
        --notice: #865d06;
        --notice-bg: #fff2cf;
        --danger: #982d27;
        --danger-bg: #ffe9e5;
        --lab-backdrop: #e5dfd0;
        --art-card: 230px;
        --radius: 14px;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
      }
      @media (prefers-color-scheme: dark) {
        :root {
          --canvas: #17272e;
          --surface: #20343c;
          --surface-raised: #29414a;
          --ink: #eff7f7;
          --muted: #b8c9ca;
          --line: #527079;
          --accent: #80d2ed;
          --accent-ink: #d8f5fd;
          --notice: #ffd272;
          --notice-bg: #493a16;
          --danger: #ffaca2;
          --danger-bg: #4d2928;
          --lab-backdrop: #d9d1bf;
        }
      }
      * { box-sizing: border-box; }
      html { background: var(--canvas); }
      body { margin: 0; background: var(--canvas); color: var(--ink); }
      a { color: var(--accent); text-underline-offset: 0.18em; }
      a:focus-visible, input:focus-visible, select:focus-visible {
        outline: 3px solid #e99d10;
        outline-offset: 3px;
      }
      code, .asset-path { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .skip-link {
        position: absolute;
        inset-inline-start: 1rem;
        inset-block-start: -4rem;
        z-index: 4;
        padding: 0.7rem 1rem;
        background: var(--surface-raised);
        color: var(--ink);
      }
      .skip-link:focus { inset-block-start: 1rem; }
      .hero { border-block-end: 7px solid #78a5b1; background: #173947; color: #f6fcfc; }
      .hero__inner, main { inline-size: min(1680px, calc(100% - 2rem)); margin-inline: auto; }
      .hero__inner { padding-block: clamp(2rem, 6vw, 5rem); }
      .eyebrow {
        margin: 0 0 0.5rem;
        color: #9ed5e5;
        font-size: 0.76rem;
        font-weight: 780;
        letter-spacing: 0.11em;
        text-transform: uppercase;
      }
      h1 {
        max-inline-size: 21ch;
        margin: 0;
        font-size: clamp(2rem, 6vw, 4.7rem);
        line-height: 0.98;
        letter-spacing: -0.045em;
      }
      .lede {
        max-inline-size: 72ch;
        margin: 1.2rem 0 0;
        color: #dcebed;
        font-size: clamp(1rem, 1.8vw, 1.2rem);
        line-height: 1.55;
      }
      main { padding-block: 1.8rem 4.5rem; }
      .notice {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 0.85rem;
        margin-block-end: 2rem;
        padding: 1rem 1.1rem;
        border: 1px solid var(--notice);
        border-inline-start: 6px solid var(--notice);
        border-radius: var(--radius);
        background: var(--notice-bg);
      }
      .notice-mark {
        display: grid;
        place-items: center;
        inline-size: 1.8rem;
        block-size: 1.8rem;
        border-radius: 50%;
        background: var(--notice);
        color: #1f1b0d;
        font-weight: 900;
      }
      .notice strong { display: block; }
      .notice p { max-inline-size: 85ch; margin: 0.25rem 0 0; line-height: 1.55; }
      .notice a { color: currentColor; font-weight: 700; }
      .library-heading, .family-heading {
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        justify-content: space-between;
      }
      .library-heading { gap: 0.7rem 2rem; margin-block: 2.8rem 1rem; }
      .library-heading h2 {
        margin: 0;
        color: var(--accent-ink);
        font-size: clamp(1.5rem, 3vw, 2.35rem);
        letter-spacing: -0.025em;
      }
      .library-heading p {
        max-inline-size: 68ch;
        margin: 0;
        color: var(--muted);
        line-height: 1.5;
      }
      .controls {
        display: grid;
        grid-template-columns: minmax(14rem, 2fr) minmax(11rem, 1fr) minmax(12rem, 1fr);
        gap: 0.8rem;
        padding: 0.9rem;
        border: 1px solid var(--line);
        border-radius: var(--radius);
        background: var(--surface);
        box-shadow: 0 0.65rem 1.6rem rgb(10 37 47 / 0.1);
      }
      .control { display: grid; gap: 0.35rem; min-inline-size: 0; }
      .control label {
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 760;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }
      .control input, .control select {
        min-inline-size: 0;
        min-block-size: 2.6rem;
        border: 1px solid var(--line);
        border-radius: 0.55rem;
        background: var(--surface-raised);
        color: var(--ink);
        padding-inline: 0.7rem;
        font: inherit;
      }
      .control input[type="range"] { padding-inline: 0; accent-color: var(--accent); }
      .inventory-meta { margin: 0.9rem 0 2.2rem; color: var(--muted); }
      .inventory-meta strong { color: var(--ink); }
      .family { margin-block: 2.8rem; scroll-margin-block-start: 1rem; }
      .family[hidden], .asset-card[hidden] { display: none; }
      .family-heading {
        gap: 0.5rem 1rem;
        border-block-end: 2px solid var(--line);
        padding-block-end: 0.65rem;
        margin-block-end: 1rem;
      }
      .family-heading .eyebrow { color: var(--muted); }
      .family-heading h2 {
        margin: 0;
        color: var(--accent-ink);
        font-size: clamp(1.35rem, 2.5vw, 2rem);
      }
      .family-heading > p { margin: 0; color: var(--muted); }
      .asset-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--art-card)), 1fr));
        gap: 0.9rem;
      }
      .asset-card {
        min-inline-size: 0;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 0.75rem;
        background: var(--surface);
      }
      .asset-frame {
        display: grid;
        place-items: center;
        aspect-ratio: 1;
        padding: 1rem;
        border-block-end: 1px solid var(--line);
        background: var(--lab-backdrop);
      }
      .asset-frame:hover { background: #d9edf1; }
      .asset-frame img {
        display: block;
        inline-size: 100%;
        block-size: 100%;
        object-fit: contain;
      }
      .asset-copy { display: grid; gap: 0.5rem; padding: 0.8rem; }
      .asset-copy h3 { margin: 0; font-size: 0.96rem; line-height: 1.25; overflow-wrap: anywhere; }
      .asset-path {
        color: var(--muted);
        font-size: 0.66rem;
        line-height: 1.4;
        overflow-wrap: anywhere;
      }
      .badges { display: flex; flex-wrap: wrap; gap: 0.35rem; }
      .badge {
        display: inline-flex;
        align-items: center;
        inline-size: fit-content;
        min-block-size: 1.45rem;
        padding-inline: 0.5rem;
        border-radius: 999px;
        background: #d8edf2;
        color: #0c4355;
        font-size: 0.66rem;
        font-weight: 760;
      }
      .badge--protected { background: var(--danger-bg); color: var(--danger); }
      .empty {
        display: none;
        margin: 2rem 0;
        padding: 2rem;
        border: 1px dashed var(--line);
        border-radius: var(--radius);
        color: var(--muted);
        text-align: center;
      }
      .empty[data-visible="true"] { display: block; }
      @media (max-width: 760px) {
        .hero__inner, main { inline-size: min(100% - 1.25rem, 1680px); }
        .controls { grid-template-columns: 1fr; }
      }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; }
      }
      @media print {
        .controls { display: none; }
        .asset-grid { --art-card: 170px; }
      }`;
}

function pageScript() {
  return `
      const cards = [...document.querySelectorAll(".asset-card")];
      const sections = [...document.querySelectorAll(".family")];
      const search = document.querySelector("#asset-search");
      const family = document.querySelector("#family-filter");
      const size = document.querySelector("#asset-size");
      const count = document.querySelector("#visible-count");
      const empty = document.querySelector("#empty-result");

      function updateFilters() {
        const query = search.value.trim().toLowerCase();
        let visible = 0;
        for (const card of cards) {
          const matchesSearch = !query || card.textContent.toLowerCase().includes(query);
          const matchesFamily = family.value === "all" || card.dataset.family === family.value;
          card.hidden = !(matchesSearch && matchesFamily);
          if (!card.hidden) visible += 1;
        }
        for (const section of sections) {
          const familyCount = section.querySelectorAll(".asset-card:not([hidden])").length;
          section.hidden = familyCount === 0;
          section.querySelector("[data-family-count]").textContent = String(familyCount);
        }
        count.textContent = String(visible);
        empty.dataset.visible = String(visible === 0);
      }

      function updateCardSize() {
        document.documentElement.style.setProperty("--art-card", size.value + "px");
      }

      search.addEventListener("input", updateFilters);
      family.addEventListener("change", updateFilters);
      size.addEventListener("input", updateCardSize);`;
}

function documentHtml(assets, families) {
  const css = pageCss();
  const options = familyOptionsHtml(families);
  const sections = familySectionsHtml(families);
  const script = pageScript();

  return `<!-- Generated by tools/render_svg_library_review.mjs. Do not hand-edit. -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="light dark" />
    <title>Authored equipment SVG library review</title>
    <style>${css}
    </style>
  </head>
  <body>
    <a class="skip-link" href="#library">Skip to asset library</a>
    <header class="hero"><div class="hero__inner">
      <p class="eyebrow">Current authored production sources</p>
      <h1>Equipment SVG library review</h1>
      <p class="lede">Browse all ${assets.length} authored equipment SVGs directly from the
        source tree. Each card loads the live file, so this review page never substitutes a copied
        illustration for the production asset.</p>
    </div></header>
    <main>
      <aside class="notice" aria-label="Historical candidate warning">
        <span class="notice-mark" aria-hidden="true">!</span>
        <div>
          <strong>Historical candidates are not acceptance artwork.</strong>
          <p>The prior four-object candidate page showed cubist direction experiments, not this
            library. They remain only as a rejected comparison record.
            <a href="candidates/review.html">Open the archived candidate notice</a> or inspect
            actual current scenes through <code>./run_web_server.sh</code> and
            <code>/scene_viewer.html?scene=&lt;name&gt;</code>.</p>
        </div>
      </aside>
      <section id="library" aria-labelledby="library-heading">
        <div class="library-heading">
          <div>
            <p class="eyebrow">Live inventory</p>
            <h2 id="library-heading">All authored equipment</h2>
          </div>
          <p>Use the controls to narrow the view. Without JavaScript, every source remains visible
            and grouped by its authored behavior path.</p>
        </div>
        <div class="controls" aria-label="Asset review controls">
          <div class="control">
            <label for="asset-search">Search name or source path</label>
            <input id="asset-search" type="search" placeholder="centrifuge, pipette, gel..."
              autocomplete="off" />
          </div>
          <div class="control"><label for="family-filter">Authored behavior</label>
            <select id="family-filter"><option value="all">All behaviors</option>
${options}
            </select>
          </div>
          <div class="control"><label for="asset-size">Card width</label>
            <input id="asset-size" type="range" min="160" max="380" value="230" />
          </div>
        </div>
        <p class="inventory-meta"><strong id="visible-count">${assets.length}</strong> of
          ${assets.length} source assets shown. Click an artwork card or source path to open its
          live SVG.</p>
        <div id="family-sections">
${sections}
        </div>
        <p id="empty-result" class="empty">No authored source assets match those filters.</p>
      </section>
    </main>
    <script>${script}
    </script>
  </body>
</html>
`;
}

function main() {
  console.log("=== SVG LIBRARY REVIEW: DISCOVER AUTHORED EQUIPMENT ===");
  const assets = buildAssets();
  const families = groupByFamily(assets);
  const html = documentHtml(assets, families);
  console.log(
    `Found ${assets.length} authored equipment SVGs in ${families.size} behavior families.`,
  );
  console.log("=== SVG LIBRARY REVIEW: WRITE LIVE-LINKED GALLERY ===");
  fs.writeFileSync(OUTPUT_PATH, html, "utf8");
  console.log(`Wrote ${OUTPUT_PATH}`);
}

main();
