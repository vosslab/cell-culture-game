// SVG injection helpers for the renderer. The runtime injects scene SVGs by
// fetching SVG file text via svg_manifest_loader (injectSvgFromManifest); the
// raw-markup seam injectSvgMarkupInto is for build/test callers that already
// hold markup (no manifest, no fetch). Both route through the shared
// namespaceSvgIds id-isolation helper before insertion. resolveAnchor exposes a
// bare-anchor -> namespaced-element lookup on a host that an SVG was injected
// into. Throws loudly on empty/unparseable assets. No fallback SVG, no
// diagnostic error, with no silent failures. There is no bundled-SVG-markup registry path:
// the giant inline SVG_REGISTRY left the runtime bundle in the registry-to-manifest cutover.
//
// Inline SVGs share internal ids (every Servier-normalized asset declares the
// same generic ids such as clipPath id="a"). HTML ids must be unique per
// document, so two inlined SVGs that both define id="a" make every url(#a) /
// clip-path / href reference resolve to the FIRST match in document order --
// one object's geometry then clips to another object's clip rect. The fix is to
// namespace every id per render instance before insertion, and rewrite every
// internal reference consistently. This isolates each injected instance by
// construction rather than patching collisions per asset.
//
// namespaceSvgIds is a PURE helper: it takes an already-parsed SVG root and
// rewrites ids and references in place, independent of where the markup came
// from. The markup SOURCE is source-agnostic: markup comes from the fetch path
// or a test caller; the id-isolation step does not change.

import { fetchSvgText } from "./svg_manifest_loader.js";

// Generated material transforms position independently-rounded scale and
// translation values around an authored anchor.  Three decimal places can
// move a seam by a visible fraction of an SVG unit when the anchor is far from
// the origin.  Keep enough fractional precision that the generated transform
// preserves the underlying analytic geometry for every material asset.
const SVG_NUMBER_DECIMALS = 9;

function format_svg_number(value: number): string {
  if (!Number.isFinite(value)) {
    throw new Error("liquid-region injection: SVG number must be finite");
  }
  const rounded = Number(value.toFixed(SVG_NUMBER_DECIMALS));
  return Object.is(rounded, -0) ? "0" : String(rounded);
}

//============================================

// Data attribute used to stamp the per-render-instance namespace onto the host
// element after injection. resolveAnchor reads it to map a bare authored id to
// its namespaced injected element WITHOUT re-deriving the asset/scene/placement
// naming -- SVG owns the naming, callers ask by bare id only.
const SVG_INSTANCE_NAMESPACE_ATTR = "data-svg-instance-namespace";

// The injection path is the sole owner of concrete per-instance SVG references.
// Material renderers receive a bare authored target and an operation that applies
// the already-resolved local reference; they never inspect an SVG id or build a
// url(#...) string themselves.
export interface ResolvedSvgAnchor {
  element: Element;
  applyClipPath(target: SVGElement): void;
}

export type InjectedLiquidPaintRole = "base" | "highlight" | "shadow";
export type InjectedLiquidPart = "bottom" | "body" | "surface";

export interface InjectedLiquidPaint {
  paint_handle: string;
  paint_role: InjectedLiquidPaintRole;
  liquid_part: InjectedLiquidPart;
  adjustment: number | null;
}

export interface InjectedLiquidRegion {
  bounds: Readonly<{ x: number; y: number; width: number; height: number }>;
  surfaceReferenceY: number | null;
  bodyJoinY: number | null;
  bodyAnchorY: number | null;
  maxFillPercent: number | null;
  minFillPercent: number | null;
  bodyStartFillPercent: number | null;
  fillHeightExponent: number | null;
  paints: readonly InjectedLiquidPaint[];
  setPaint(paint_handle: string, color: string): void;
  setBodyScale(scaleY: number): void;
  setSurfaceTransform(dy: number, scale: number): void;
  setRevealTop(y: number): void;
  setVisible(visible: boolean): void;
}

interface LiquidRegionManifestPaint extends InjectedLiquidPaint {
  element_handle: string;
}

interface LiquidRegionManifestEntry {
  region_handle: string;
  reveal_handle: string;
  paints: LiquidRegionManifestPaint[];
  bounds: { x: number; y: number; width: number; height: number };
  surface_reference_y: number | null;
  body_join_y: number | null;
  body_anchor_y: number | null;
  max_fill_percent: number | null;
  min_fill_percent: number | null;
  body_start_fill_percent: number | null;
  fill_height_exponent: number | null;
}

const LIQUID_REGIONS_URL = "assets/liquid_regions.json";
const injectedLiquidRegions = new WeakMap<HTMLElement, InjectedLiquidRegion>();
let liquidRegionManifestPromise: Promise<Record<string, LiquidRegionManifestEntry>> | undefined;

//============================================

// Lookup metadata returned by namespaceSvgIds. The instance namespace is the
// final prefix string applied to every id; renameMap maps each bare authored id
// to its namespaced id (first-occurrence target used for reference rewriting).
// Returning this instead of void lets the injection layer stamp the namespace
// on the host and lets resolveAnchor find a bare authored id's namespaced
// element without reconstructing the naming convention.
export interface SvgNamespaceResult {
  instanceNamespace: string;
  renameMap: Map<string, string>;
}

//============================================

// Make a prefix safe to use inside an SVG/HTML id.
function sanitizeIdPart(part: string): string {
  return part.replace(/[^A-Za-z0-9_-]/g, "_");
}

//============================================

// Rewrite every `url(#oldId)` reference in a single string to `url(#newId)`,
// covering the unquoted, double-quoted, single-quoted, and whitespace-padded
// forms: url(#a), url("#a"), url('#a'), url( #a ). Only LOCAL fragment
// references (the `#id` form) are rewritten; external URLs and non-local
// fragments are left untouched because they never match a local rename key.
function rewriteUrlRefs(value: string, rename: Map<string, string>): string {
  // Fast path: nothing to do when there is no url( token at all.
  if (!value.includes("url(")) {
    return value;
  }
  // One generic regex captures the optional quote and the fragment id, with
  // optional surrounding whitespace. The captured id is looked up in the
  // rename map; an unknown id (external or non-local fragment) is left as-is.
  const urlRefPattern = /url\(\s*(['"]?)#([^'")\s]+)\1\s*\)/g;
  function replaceOne(match: string, quote: string, oldId: string): string {
    const newId = rename.get(oldId);
    if (newId === undefined) {
      return match;
    }
    return `url(${quote}#${newId}${quote})`;
  }
  return value.replace(urlRefPattern, replaceOne);
}

//============================================

// Namespace every id in a parsed SVG root and rewrite all internal references.
//
// References are rewritten by a GENERIC attribute scan, not an enumerated list:
// any attribute value containing `url(#id)` (covers clip-path, mask, filter,
// fill, stroke, and style) is rewritten in every quoted/unquoted/whitespace
// form, and `href` / `xlink:href` values of the form `#id` are rewritten. In
// addition, `url(#id)` references inside the text content of embedded <style>
// elements are rewritten (8 shipped assets carry <style> blocks; at least one
// references a gradient via fill:url(#radial-gradient) inside style text). This
// covers every current reference form without a hand-listed attribute set.
//
// svgInstanceKey is the final, already-composed namespace string for this
// rendered SVG instance (the caller in injectSvgMarkupInto folds asset name, scene/
// page id, and placement name into it and sanitizes it). This helper is source-
// agnostic: it takes an already-parsed SVG root plus that key, and isolates ids.
// The manifest-fetch path only changes how the SVG text is loaded, never how
// ids are isolated, so it reuses this helper unchanged.
//
// Returns SvgNamespaceResult (the instance namespace string plus the bare-id ->
// namespaced-id rename map) so callers can stamp the namespace on the host and
// resolve bare authored ids (e.g. anchor_liquid_bounds) to their namespaced
// elements. Existing callers that ignore the return value are unaffected.
export function namespaceSvgIds(svgRoot: Element, svgInstanceKey: string): SvgNamespaceResult {
  // Build the rename map and apply it to the id-defining attributes.
  //
  // `rename` maps an old id to the namespaced id used for REFERENCE rewriting:
  // a `url(#oldId)` / `href="#oldId"` reference must point at the first element
  // that defined `oldId`, because that is the element the browser resolves to in
  // document order. So `rename` records only the FIRST occurrence of each id.
  //
  // Source assets can illegally repeat an id (e.g. the microtube asset declares
  // id="anchor_liquid_bounds" on both a clip rect and a separate hidden rect).
  // Duplicate-id source elements are NOT valid reference targets, but they must
  // still come out of namespacing with UNIQUE ids so the injected subtree has no
  // duplicate ids (a hard acceptance criterion: injected subtrees must have no
  // duplicate ids). `assignedIds` tracks every
  // id already emitted so a repeated source id gets a stable disambiguating
  // suffix on the element only; the reference target (first occurrence) is left
  // untouched.
  const rename = new Map<string, string>();
  const assignedIds = new Set<string>();
  const idedElements = [svgRoot, ...Array.from(svgRoot.querySelectorAll("[id]"))];
  for (const el of idedElements) {
    const oldId = el.getAttribute("id");
    if (oldId === null) {
      continue;
    }
    const baseId = `${svgInstanceKey}__${oldId}`;
    if (!rename.has(oldId)) {
      // First occurrence: this is the canonical reference target for oldId.
      rename.set(oldId, baseId);
    }
    // Guarantee a unique emitted id even when the source repeats an id. The
    // first occurrence keeps baseId; later duplicates take baseId__dup2, __dup3.
    let uniqueId = baseId;
    let dupCounter = 2;
    while (assignedIds.has(uniqueId)) {
      uniqueId = `${baseId}__dup${dupCounter}`;
      dupCounter += 1;
    }
    assignedIds.add(uniqueId);
    el.setAttribute("id", uniqueId);
  }

  // nothing references anything if there are no ids
  if (rename.size === 0) {
    return { instanceNamespace: svgInstanceKey, renameMap: rename };
  }

  // rewrite references on every element, including the root
  const allElements = [svgRoot, ...Array.from(svgRoot.querySelectorAll("*"))];
  for (const el of allElements) {
    for (const attr of Array.from(el.attributes)) {
      let value = attr.value;

      // url(#id) references in any attribute value (fill, stroke, clip-path,
      // mask, filter, style, ...), all quote/whitespace forms.
      value = rewriteUrlRefs(value, rename);

      // href / xlink:href = "#id" (localName is "href" for both)
      if (attr.localName === "href" && value.startsWith("#")) {
        const target = rename.get(value.slice(1));
        if (target !== undefined) {
          value = `#${target}`;
        }
      }

      if (value !== attr.value) {
        attr.value = value;
      }
    }

    // <style> text content: rewrite url(#id) references inside the CSS text.
    // The style element's text node carries references like
    // fill:url(#radial-gradient) that the attribute scan above never sees.
    // Preserve all other CSS text; only local id url() references change.
    if (el.localName === "style") {
      const cssText = el.textContent;
      if (cssText !== null && cssText.includes("url(")) {
        const rewritten = rewriteUrlRefs(cssText, rename);
        if (rewritten !== cssText) {
          el.textContent = rewritten;
        }
      }
    }
  }

  return { instanceNamespace: svgInstanceKey, renameMap: rename };
}

//============================================

/**
 * Inject already-held SVG markup into a host element, isolating its internal ids
 * per render instance. This is the source-agnostic raw-markup seam: the runtime
 * reaches it through injectSvgFromManifest (fetched file text), and build/test
 * callers that already hold markup call it directly. There is NO bundled-markup
 * registry lookup here; the giant inline SVG_REGISTRY left the runtime bundle in
 * the registry-to-manifest cutover. Throws if the markup is empty, unparseable, or non-svg.
 *
 * @param host - HTMLElement to inject the SVG into
 * @param assetName - asset_name (used only for error context and the namespace)
 * @param svgMarkup - the SVG markup text to inject
 * @param svgInstanceKey - svgInstanceKey is a stable runtime-only namespace key
 *   for this rendered SVG instance. It is not authored YAML vocabulary and must
 *   not be used as a protocol, object, or scene id.
 * @returns the namespace result (instance namespace + bare-id rename map)
 * @throws Error if the markup is empty, fails to parse, or is non-svg
 */
export function injectSvgMarkupInto(
  host: HTMLElement,
  assetName: string,
  svgMarkup: string,
  svgInstanceKey: string,
): SvgNamespaceResult {
  // Empty / whitespace-only markup would inject nothing and draw a silent blank
  // layer. Fail loudly. Repo principle: loud failures, never silent blank.
  if (svgMarkup.trim().length === 0) {
    throw new Error(`SVG asset markup is empty: "${assetName}"`);
  }

  return injectSvgMarkup(host, assetName, svgMarkup, svgInstanceKey);
}

//============================================

function manifest_record(value: unknown, context: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`liquid-region manifest: ${context} must be an object`);
  }
  return value as Record<string, unknown>;
}

function manifest_string(value: unknown, context: string): string {
  if (typeof value !== "string" || !/^lr_[0-9a-f]{16}$/.test(value)) {
    throw new Error(`liquid-region manifest: ${context} must be an opaque handle`);
  }
  return value;
}

function manifest_number(value: unknown, context: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`liquid-region manifest: ${context} must be finite numeric`);
  }
  return value;
}

function manifest_nullable_number(value: unknown, context: string): number | null {
  return value === null ? null : manifest_number(value, context);
}

function parse_liquid_region_entry(asset_name: string, value: unknown): LiquidRegionManifestEntry {
  const entry = manifest_record(value, `'${asset_name}'`);
  const raw_bounds = manifest_record(entry.bounds, `'${asset_name}'.bounds`);
  const bounds = {
    x: manifest_number(raw_bounds.x, `'${asset_name}'.bounds.x`),
    y: manifest_number(raw_bounds.y, `'${asset_name}'.bounds.y`),
    width: manifest_number(raw_bounds.width, `'${asset_name}'.bounds.width`),
    height: manifest_number(raw_bounds.height, `'${asset_name}'.bounds.height`),
  };
  if (bounds.width <= 0 || bounds.height <= 0) {
    throw new Error(`liquid-region manifest: '${asset_name}' bounds must have positive size`);
  }
  const surface_reference_y = manifest_nullable_number(
    entry.surface_reference_y,
    `'${asset_name}'.surface_reference_y`,
  );
  const body_join_y = manifest_nullable_number(entry.body_join_y, `'${asset_name}'.body_join_y`);
  const body_anchor_y = manifest_nullable_number(
    entry.body_anchor_y,
    `'${asset_name}'.body_anchor_y`,
  );
  const max_fill_percent = manifest_nullable_number(
    entry.max_fill_percent,
    `'${asset_name}'.max_fill_percent`,
  );
  if (
    max_fill_percent !== null &&
    (!Number.isInteger(max_fill_percent) || max_fill_percent < 1 || max_fill_percent > 100)
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}'.max_fill_percent must be an integer in [1, 100]`,
    );
  }
  const min_fill_percent = manifest_nullable_number(
    entry.min_fill_percent,
    `'${asset_name}'.min_fill_percent`,
  );
  if (
    min_fill_percent !== null &&
    (!Number.isInteger(min_fill_percent) || min_fill_percent < 1 || min_fill_percent > 99)
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}'.min_fill_percent must be an integer in [1, 99]`,
    );
  }
  if (
    min_fill_percent !== null &&
    max_fill_percent !== null &&
    min_fill_percent > max_fill_percent
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}' minimum fill must not exceed maximum fill`,
    );
  }
  const body_start_fill_percent = manifest_nullable_number(
    entry.body_start_fill_percent,
    `'${asset_name}'.body_start_fill_percent`,
  );
  const fill_height_exponent = manifest_nullable_number(
    entry.fill_height_exponent,
    `'${asset_name}'.fill_height_exponent`,
  );
  if (
    fill_height_exponent !== null &&
    (!Number.isFinite(fill_height_exponent) ||
      fill_height_exponent <= 0 ||
      fill_height_exponent > 10)
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}'.fill_height_exponent must be in (0, 10]`,
    );
  }
  if (body_start_fill_percent !== null && fill_height_exponent !== null) {
    throw new Error(
      `liquid-region manifest: '${asset_name}' body-start and exponent calibrations are mutually exclusive`,
    );
  }
  if (
    body_start_fill_percent !== null &&
    (!Number.isFinite(body_start_fill_percent) ||
      body_start_fill_percent <= 0 ||
      body_start_fill_percent >= 100)
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}'.body_start_fill_percent must be in (0, 100)`,
    );
  }
  if (
    (body_anchor_y !== null || body_join_y !== null) &&
    (surface_reference_y === null || body_anchor_y === null || body_join_y === null)
  ) {
    throw new Error(`liquid-region manifest: '${asset_name}' body calibration is incomplete`);
  }
  if (
    surface_reference_y !== null &&
    body_join_y !== null &&
    body_anchor_y !== null &&
    (body_join_y < surface_reference_y || body_anchor_y <= body_join_y)
  ) {
    throw new Error(`liquid-region manifest: '${asset_name}' body join calibration is invalid`);
  }
  if (
    body_start_fill_percent !== null &&
    (surface_reference_y === null || body_join_y === null || body_anchor_y === null)
  ) {
    throw new Error(`liquid-region manifest: '${asset_name}' body-start calibration is incomplete`);
  }
  if (
    body_start_fill_percent !== null &&
    (body_anchor_y! <= bounds.y || body_anchor_y! >= bounds.y + bounds.height)
  ) {
    throw new Error(
      `liquid-region manifest: '${asset_name}' body-start anchor must remain inside bounds`,
    );
  }
  if (!Array.isArray(entry.paints) || entry.paints.length === 0) {
    throw new Error(`liquid-region manifest: '${asset_name}'.paints must be a non-empty array`);
  }
  const paints = entry.paints.map((raw_paint, index): LiquidRegionManifestPaint => {
    const paint = manifest_record(raw_paint, `'${asset_name}'.paints[${index}]`);
    const role = paint.paint_role;
    if (role !== "base" && role !== "highlight" && role !== "shadow") {
      throw new Error(`liquid-region manifest: '${asset_name}' has an unknown paint role`);
    }
    const liquid_part = paint.liquid_part;
    if (liquid_part !== "bottom" && liquid_part !== "body" && liquid_part !== "surface") {
      throw new Error(`liquid-region manifest: '${asset_name}' has an unknown liquid part`);
    }
    const adjustment =
      paint.adjustment === null
        ? null
        : manifest_number(paint.adjustment, `'${asset_name}'.paints[${index}].adjustment`);
    if ((role === "base") !== (adjustment === null)) {
      throw new Error(`liquid-region manifest: '${asset_name}' has an invalid role adjustment`);
    }
    return {
      element_handle: manifest_string(
        paint.element_handle,
        `'${asset_name}'.paints[${index}].element_handle`,
      ),
      paint_handle: manifest_string(
        paint.paint_handle,
        `'${asset_name}'.paints[${index}].paint_handle`,
      ),
      paint_role: role,
      liquid_part,
      adjustment,
    };
  });
  return {
    region_handle: manifest_string(entry.region_handle, `'${asset_name}'.region_handle`),
    reveal_handle: manifest_string(entry.reveal_handle, `'${asset_name}'.reveal_handle`),
    paints,
    bounds,
    surface_reference_y,
    body_join_y,
    body_anchor_y,
    max_fill_percent,
    min_fill_percent,
    body_start_fill_percent,
    fill_height_exponent,
  };
}

async function fetch_liquid_region_manifest(): Promise<Record<string, LiquidRegionManifestEntry>> {
  const response = await fetch(LIQUID_REGIONS_URL);
  if (!response.ok) {
    throw new Error(
      `liquid-region manifest fetch failed at '${LIQUID_REGIONS_URL}': ` +
        `${response.status} ${response.statusText}`,
    );
  }
  const raw: unknown = await response.json();
  const record = manifest_record(raw, "root");
  const parsed: Record<string, LiquidRegionManifestEntry> = {};
  for (const [asset_name, value] of Object.entries(record)) {
    parsed[asset_name] = parse_liquid_region_entry(asset_name, value);
  }
  return parsed;
}

async function load_liquid_region_manifest(): Promise<Record<string, LiquidRegionManifestEntry>> {
  if (liquidRegionManifestPromise === undefined) {
    liquidRegionManifestPromise = fetch_liquid_region_manifest();
    liquidRegionManifestPromise.catch(() => {
      liquidRegionManifestPromise = undefined;
    });
  }
  return liquidRegionManifestPromise;
}

function resolve_generated_handle(
  host: HTMLElement,
  rename_map: ReadonlyMap<string, string>,
  handle: string,
): SVGElement {
  const concrete_id = rename_map.get(handle);
  if (concrete_id === undefined) {
    throw new Error(`liquid-region injection: SVG does not define generated handle '${handle}'`);
  }
  const element = host.querySelector(`[id="${concrete_id}"]`);
  if (!(element instanceof SVGElement)) {
    throw new Error(`liquid-region injection: generated handle '${handle}' is not SVG geometry`);
  }
  return element;
}

function bind_liquid_region(
  host: HTMLElement,
  entry: LiquidRegionManifestEntry | undefined,
  rename_map: ReadonlyMap<string, string>,
): void {
  injectedLiquidRegions.delete(host);
  if (entry === undefined) {
    return;
  }
  const region_group = resolve_generated_handle(host, rename_map, entry.region_handle);
  if (!(region_group instanceof SVGGElement)) {
    throw new Error("liquid-region injection: region handle must identify an SVG group");
  }
  const reveal_rect = resolve_generated_handle(host, rename_map, entry.reveal_handle);
  if (!(reveal_rect instanceof SVGRectElement)) {
    throw new Error("liquid-region injection: reveal handle must identify an SVG rect");
  }
  const paint_elements = new Map<string, SVGElement>();
  for (const paint of entry.paints) {
    if (paint_elements.has(paint.paint_handle)) {
      throw new Error(`liquid-region injection: duplicate paint handle '${paint.paint_handle}'`);
    }
    paint_elements.set(
      paint.paint_handle,
      resolve_generated_handle(host, rename_map, paint.element_handle),
    );
  }
  // Generated gravity transforms are always outermost so any authored local
  // transform remains part of the semantic artwork rather than being erased by
  // a later material update.
  const authored_transforms = new Map<string, string | null>(
    [...paint_elements].map(([paint_handle, element]) => [
      paint_handle,
      element.getAttribute("transform"),
    ]),
  );
  function set_generated_transform(paint_handle: string, generated: string): void {
    const element = paint_elements.get(paint_handle)!;
    const authored = authored_transforms.get(paint_handle);
    element.setAttribute("transform", authored === null ? generated : `${generated} ${authored}`);
  }
  injectedLiquidRegions.set(host, {
    bounds: Object.freeze({ ...entry.bounds }),
    surfaceReferenceY: entry.surface_reference_y,
    bodyJoinY: entry.body_join_y,
    bodyAnchorY: entry.body_anchor_y,
    maxFillPercent: entry.max_fill_percent,
    minFillPercent: entry.min_fill_percent,
    bodyStartFillPercent: entry.body_start_fill_percent,
    fillHeightExponent: entry.fill_height_exponent,
    paints: Object.freeze(
      entry.paints.map((paint) =>
        Object.freeze({
          paint_handle: paint.paint_handle,
          paint_role: paint.paint_role,
          liquid_part: paint.liquid_part,
          adjustment: paint.adjustment,
        }),
      ),
    ),
    setPaint(paint_handle: string, color: string): void {
      if (!paint_elements.has(paint_handle)) {
        throw new Error(`liquid-region injection: unknown paint handle '${paint_handle}'`);
      }
      host.style.setProperty(`--${paint_handle}`, color);
    },
    setBodyScale(scaleY: number): void {
      if (!Number.isFinite(scaleY) || scaleY < 0) {
        throw new Error("liquid-region injection: body scale must be finite and non-negative");
      }
      if (entry.body_anchor_y === null) {
        if (scaleY !== 0) {
          throw new Error("liquid-region injection: body scale requested without body artwork");
        }
        return;
      }
      const translateY = entry.body_anchor_y * (1 - scaleY);
      const scaleValue = format_svg_number(scaleY);
      const translateValue = format_svg_number(translateY);
      for (const paint of entry.paints) {
        if (paint.liquid_part === "body") {
          set_generated_transform(
            paint.paint_handle,
            `matrix(1 0 0 ${scaleValue} 0 ${translateValue})`,
          );
        }
      }
    },
    setSurfaceTransform(dy: number, scale: number): void {
      if (!Number.isFinite(dy) || !Number.isFinite(scale) || scale < 0) {
        throw new Error(
          "liquid-region injection: surface transform must be finite and non-negative",
        );
      }
      const offsetValue = format_svg_number(dy);
      const scaleValue = format_svg_number(scale);
      const centerX = entry.bounds.x + entry.bounds.width / 2;
      const centerXValue = format_svg_number(centerX);
      const negativeCenterXValue = format_svg_number(-centerX);
      const referenceY = entry.surface_reference_y;
      const referenceYValue = referenceY === null ? null : format_svg_number(referenceY);
      const negativeReferenceYValue = referenceY === null ? null : format_svg_number(-referenceY);
      for (const paint of entry.paints) {
        if (paint.liquid_part === "surface") {
          const generated =
            scale === 1 || referenceYValue === null || negativeReferenceYValue === null
              ? `translate(0, ${offsetValue})`
              : `translate(0, ${offsetValue}) translate(${centerXValue}, ${referenceYValue}) scale(${scaleValue}) translate(${negativeCenterXValue}, ${negativeReferenceYValue})`;
          set_generated_transform(paint.paint_handle, generated);
        }
      }
    },
    setRevealTop(y: number): void {
      const bottom = entry.bounds.y + entry.bounds.height;
      if (!Number.isFinite(y) || y < entry.bounds.y || y > bottom) {
        throw new Error("liquid-region injection: reveal top must remain inside bounds");
      }
      reveal_rect.setAttribute("y", format_svg_number(y));
      reveal_rect.setAttribute("height", format_svg_number(bottom - y));
    },
    setVisible(visible: boolean): void {
      region_group.setAttribute("display", visible ? "inline" : "none");
    },
  });
}

export function resolveInjectedLiquidRegion(host: HTMLElement): InjectedLiquidRegion | null {
  return injectedLiquidRegions.get(host) ?? null;
}

//============================================

/**
 * Async injection path: fetch SVG file text by manifest URL, then namespace and
 * inject. Used for DOM-SVG-required objects after the cutover. The fetched text
 * is cached per asset URL by svg_manifest_loader (one fetch reused across all
 * placements); id namespacing still runs per render instance after retrieval.
 *
 * Fetch failure throws through fetchSvgText (loud, never a silent blank). The
 * caller is responsible for awaiting this inside a tracked async primitive (a
 * Solid resource) so the failure surfaces, not an unhandled rejection.
 *
 * @param host - HTMLElement to inject the SVG into
 * @param assetName - asset_name key in SVG_MANIFEST
 * @param svgInstanceKey - stable runtime-only per-render-instance namespace key
 * @returns the namespace result (instance namespace + bare-id rename map)
 * @throws Error if the fetch fails, or the body is empty/malformed/non-svg
 */
export async function injectSvgFromManifest(
  host: HTMLElement,
  assetName: string,
  svgInstanceKey: string,
): Promise<SvgNamespaceResult> {
  // Fetch both immutable artifacts in parallel. SVG text is cached by URL; the
  // aggregate liquid manifest is cached once for the page.
  const [svgText, liquid_manifest] = await Promise.all([
    fetchSvgText(assetName),
    load_liquid_region_manifest(),
  ]);
  const result = injectSvgMarkup(host, assetName, svgText, svgInstanceKey);
  bind_liquid_region(host, liquid_manifest[assetName], result.renameMap);
  return result;
}

//============================================

/**
 * Resolve a BARE authored id (e.g. "anchor_liquid_bounds") to its namespaced
 * injected element for this rendered instance. SVG owns id naming AND lookup:
 * the caller never concatenates asset/scene/placement names. Reads the
 * per-instance namespace stamped on the host by injectSvgMarkup, applies the
 * single namespacing prefix rule, and looks the element up inside the host.
 *
 * Returns null when no element with that bare id was injected (the authored id
 * is absent from the asset), which is a normal "no such anchor" answer, not an
 * error. Throws only if the host was never stamped (injection did not run).
 *
 * @param host - HTMLElement an SVG was injected into via injectSvgMarkupInto/Manifest
 * @param bareAuthoredId - the bare authored id from object YAML / source SVG
 * @returns the namespaced injected Element, or null if not present
 * @throws Error if the host carries no injected-SVG namespace stamp
 */
export function resolveAnchor(host: HTMLElement, bareAuthoredId: string): Element | null {
  const instanceNamespace = host.getAttribute(SVG_INSTANCE_NAMESPACE_ATTR);
  if (instanceNamespace === null) {
    throw new Error(
      "resolveAnchor: host has no injected-SVG namespace stamp; " +
        "inject an SVG via injectSvgMarkupInto/injectSvgFromManifest first.",
    );
  }
  // Apply the SAME prefix rule namespaceSvgIds uses for first-occurrence ids.
  // No duplicated string template: namespace + "__" + bare id.
  const namespacedId = `${instanceNamespace}__${bareAuthoredId}`;
  // querySelector escapes are unnecessary because sanitizeIdPart already
  // restricts the namespace and ids to [A-Za-z0-9_-]; use an attribute selector
  // so a hyphen in the id never trips CSS id-selector parsing.
  return host.querySelector(`[id="${namespacedId}"]`);
}

//============================================

// Resolve a bare authored anchor and return the limited operation a material
// renderer needs for a clip target. This keeps both id inspection and local
// SVG-reference construction inside the injection layer, where per-instance
// namespacing is already owned.
export function resolveSvgAnchor(
  host: HTMLElement,
  bareAuthoredId: string,
): ResolvedSvgAnchor | null {
  const element = resolveAnchor(host, bareAuthoredId);
  if (element === null) {
    return null;
  }
  const concreteId = element.getAttribute("id");
  if (concreteId === null || concreteId.length === 0) {
    throw new Error(`resolveSvgAnchor: injected anchor '${bareAuthoredId}' has no concrete SVG id`);
  }
  const clipPathReference = `url(#${concreteId})`;
  return {
    element,
    applyClipPath(target: SVGElement): void {
      target.setAttribute("clip-path", clipPathReference);
    },
  };
}

//============================================

// Shared parse + namespace + stamp + insert. Source-agnostic: identical for
// test-held markup and fetched-file text. Parses to a DOM, runs the two loud
// guards (parse error, non-svg root via the documentElement check), namespaces
// ids per render instance, stamps the namespace on the host for resolveAnchor,
// and replaces the host's children.
function injectSvgMarkup(
  host: HTMLElement,
  assetName: string,
  svgMarkup: string,
  svgInstanceKey: string,
): SvgNamespaceResult {
  // Parse to a DOM so id namespacing operates on real attributes, not regex
  // over a string. A parse error element means malformed markup -- fail loudly.
  const parsed = new DOMParser().parseFromString(svgMarkup, "image/svg+xml");
  const parseError = parsed.querySelector("parsererror");
  if (parseError !== null) {
    throw new Error(`SVG asset failed to parse: "${assetName}"`);
  }

  // Confirm the parsed root is actually an <svg>. Malformed XML can yield a
  // non-svg root without producing a <parsererror>, which would otherwise be
  // injected as a meaningless element. Fail loudly.
  const svgRoot = parsed.documentElement;
  if (svgRoot.localName !== "svg") {
    throw new Error(`SVG asset parsed to a non-svg root <${svgRoot.localName}>: "${assetName}"`);
  }

  // Build the final per-render-instance namespace. The asset name is the human-
  // readable component, but never the whole namespace: assetName alone would
  // collide when the same asset is placed twice. The caller-supplied
  // svgInstanceKey (scene/page id + placement name) makes it unique per rendered
  // instance, giving the shape <asset_name>__<scene_or_page_id>__<placement_name>.
  const instanceNamespace = sanitizeIdPart(`${assetName}__${svgInstanceKey}`);
  const result = namespaceSvgIds(svgRoot, instanceNamespace);

  // Stamp the namespace on the host so resolveAnchor can map a bare authored id
  // to its namespaced element without re-deriving the naming convention.
  host.setAttribute(SVG_INSTANCE_NAMESPACE_ATTR, instanceNamespace);

  // import into the host's document and replace any prior content
  const imported = document.importNode(svgRoot, true);
  host.replaceChildren(imported);
  injectedLiquidRegions.delete(host);

  return result;
}
