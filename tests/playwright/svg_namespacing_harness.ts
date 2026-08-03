// Browser test harness for SVG id namespacing (M1).
//
// This entry exposes the REAL post-cutover renderer functions on window, so the
// Playwright test in test_svg_id_namespacing.mjs can exercise the actual shipped
// code against small inline fixtures and (for the wedge-page integration check)
// fetched shipped-asset markup. There is NO bundled SVG_REGISTRY and NO
// injectSvgInto seam: the M5 cutover removed both. Namespacing mechanics are
// proven against inline markup passed directly into injectSvgMarkupInto; the
// manifest/fetch path is reserved for fetched-file rendering.
//
// It is a test-only entry. It is bundled on demand by the test (esbuild) into a
// temp file and never shipped in dist/.

import {
  namespaceSvgIds,
  injectSvgMarkupInto,
  injectSvgFromManifest,
  resolveAnchor,
  resolveSvgAnchor,
} from "../../src/scene_runtime/renderer/inject_svg.js";
import {
  resolveSvgUrl,
  requiresDomSvg,
  fetchSvgText,
} from "../../src/scene_runtime/renderer/svg_manifest_loader.js";

// A typed window surface so the harness avoids `any`.
type SvgNamespacingHarness = {
  namespaceSvgIds: typeof namespaceSvgIds;
  injectSvgMarkupInto: typeof injectSvgMarkupInto;
  injectSvgFromManifest: typeof injectSvgFromManifest;
  resolveAnchor: typeof resolveAnchor;
  resolveSvgAnchor: typeof resolveSvgAnchor;
  resolveSvgUrl: typeof resolveSvgUrl;
  requiresDomSvg: typeof requiresDomSvg;
  fetchSvgText: typeof fetchSvgText;
  // Feed raw markup straight through injectSvgMarkupInto (markup is passed by
  // value, so all parse/namespace/insert guards run without any registry).
  // Lets negative-path tests exercise the empty / parse-error / non-svg throw
  // cases without a specially crafted shipped asset.
  injectRawMarkup: (host: HTMLElement, markup: string, key: string) => void;
};

declare global {
  interface Window {
    svgHarness: SvgNamespacingHarness;
  }
}

// Inject raw markup directly. assetName is used only for error context and the
// namespace; we reuse the scratch key for both so the same prefix rule applies.
function injectRawMarkup(host: HTMLElement, markup: string, key: string): void {
  injectSvgMarkupInto(host, key, markup, key);
}

window.svgHarness = {
  namespaceSvgIds,
  injectSvgMarkupInto,
  injectSvgFromManifest,
  resolveAnchor,
  resolveSvgAnchor,
  resolveSvgUrl,
  requiresDomSvg,
  fetchSvgText,
  injectRawMarkup,
};
