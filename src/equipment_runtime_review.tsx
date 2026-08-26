// src/equipment_runtime_review.tsx
//
// Human review surface for every generated SVG manifest entry. Each card uses
// the same SvgHost component as production scenes, so static and DOM-required
// assets travel through their actual shipping render modes.

import { createMemo, createSignal, For, type JSXElement } from "solid-js";

import { SVG_MANIFEST, type SvgManifestEntry } from "../generated/svg_manifest.js";
import { SvgHost } from "./scene_runtime/renderer/svg_host.js";

type Backdrop = "light" | "dark" | "checker";
type RenderModeFilter = "all" | "dom-svg" | "img";

interface ReviewAsset {
  assetName: string;
  manifest: SvgManifestEntry;
  renderMode: Exclude<RenderModeFilter, "all">;
}

const REVIEW_ASSETS: readonly ReviewAsset[] = Object.entries(SVG_MANIFEST)
  .map(function makeReviewAsset([assetName, manifest]): ReviewAsset {
    return {
      assetName,
      manifest,
      renderMode: manifest.requires_dom_svg ? "dom-svg" : "img",
    };
  })
  .sort(function compareReviewAssets(left, right): number {
    return left.assetName.localeCompare(right.assetName);
  });

const DOM_ASSET_COUNT = REVIEW_ASSETS.filter(function needsDomSvg(asset): boolean {
  return asset.renderMode === "dom-svg";
}).length;

export function EquipmentRuntimeReview(): JSXElement {
  const [query, setQuery] = createSignal<string>("");
  const [renderMode, setRenderMode] = createSignal<RenderModeFilter>("all");
  const [backdrop, setBackdrop] = createSignal<Backdrop>("light");
  const [cardSize, setCardSize] = createSignal<number>(260);

  const visibleAssets = createMemo<readonly ReviewAsset[]>(() => {
    const normalizedQuery = query().trim().toLowerCase();
    return REVIEW_ASSETS.filter(function assetMatches(asset): boolean {
      const matchesQuery =
        normalizedQuery.length === 0 || asset.assetName.toLowerCase().includes(normalizedQuery);
      const matchesMode = renderMode() === "all" || asset.renderMode === renderMode();
      return matchesQuery && matchesMode;
    });
  });

  return (
    <main
      class="equipment-review-page"
      data-backdrop={backdrop()}
      data-review-entry-count={REVIEW_ASSETS.length}
      style={{ "--equipment-card-size": `${cardSize()}px` }}
    >
      <header class="equipment-review-header">
        <p class="equipment-review-kicker">Production renderer proof</p>
        <h1>Laboratory equipment runtime review</h1>
        <p class="equipment-review-intro">
          Every generated asset appears through the same tiered SVG host used by real scenes.
          DOM-required forms are fetched, ID-namespaced, and injected; ordinary forms remain opaque
          images.
        </p>
        <dl class="equipment-review-summary" aria-label="Review inventory">
          <div>
            <dt>Total assets</dt>
            <dd>{REVIEW_ASSETS.length}</dd>
          </div>
          <div>
            <dt>Inline DOM</dt>
            <dd>{DOM_ASSET_COUNT}</dd>
          </div>
          <div>
            <dt>Image mode</dt>
            <dd>{REVIEW_ASSETS.length - DOM_ASSET_COUNT}</dd>
          </div>
        </dl>
      </header>

      <section class="equipment-review-controls" aria-label="Artwork filters">
        <label class="equipment-review-control">
          <span>Find an asset</span>
          <input
            type="search"
            value={query()}
            placeholder="microtube, lead, flask..."
            onInput={(event) => setQuery(event.currentTarget.value)}
          />
        </label>
        <label class="equipment-review-control">
          <span>Shipping mode</span>
          <select
            value={renderMode()}
            onInput={(event) => setRenderMode(event.currentTarget.value as RenderModeFilter)}
          >
            <option value="all">All modes</option>
            <option value="dom-svg">Inline DOM SVG</option>
            <option value="img">Image</option>
          </select>
        </label>
        <label class="equipment-review-control">
          <span>Backdrop</span>
          <select
            value={backdrop()}
            onInput={(event) => setBackdrop(event.currentTarget.value as Backdrop)}
          >
            <option value="light">Lab light</option>
            <option value="dark">Dark bench</option>
            <option value="checker">Transparency grid</option>
          </select>
        </label>
        <label class="equipment-review-control equipment-review-size-control">
          <span>Artwork size: {cardSize()} px</span>
          <input
            type="range"
            min="160"
            max="380"
            step="20"
            value={cardSize()}
            onInput={(event) => setCardSize(event.currentTarget.valueAsNumber)}
          />
        </label>
      </section>

      <div class="equipment-review-result-line" role="status">
        {visibleAssets().length} of {REVIEW_ASSETS.length} assets shown
      </div>

      <section class="equipment-review-grid" aria-label="Rendered equipment assets">
        <For
          each={visibleAssets()}
          fallback={<p class="equipment-review-empty">No assets match.</p>}
        >
          {(asset) => (
            <article
              class="equipment-review-card"
              data-asset-name={asset.assetName}
              data-expected-render-mode={asset.renderMode}
            >
              <div class="equipment-review-art">
                <SvgHost
                  asset={asset.assetName}
                  svgInstanceKey={`equipment_review__${asset.assetName}__primary`}
                />
              </div>
              <div class="equipment-review-copy">
                <h2>{asset.assetName.replace(/_/g, " ")}</h2>
                <span class={`equipment-review-mode equipment-review-mode--${asset.renderMode}`}>
                  {asset.renderMode === "dom-svg" ? "inline DOM SVG" : "image"}
                </span>
                <code>{asset.manifest.path}</code>
              </div>
            </article>
          )}
        </For>
      </section>
    </main>
  );
}
