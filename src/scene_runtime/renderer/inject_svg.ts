// SVG injection helpers for the renderer. The runtime injects scene SVGs by
// fetching SVG file text via svg_manifest_loader (injectSvgFromManifest); the
// raw-markup seam injectSvgMarkupInto is for build/test callers that already
// hold markup (no manifest, no fetch). Both route through the shared
// namespaceSvgIds id-isolation helper before insertion. resolveAnchor exposes a
// bare-anchor -> namespaced-element lookup on a host that an SVG was injected
// into. Throws loudly on empty/unparseable assets. No fallback SVG, no
// placeholder, no silent failures. There is no bundled-SVG-markup registry path:
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
  // Fetch (cached by URL). Loud throw on fetch failure or empty body.
  const svgText = await fetchSvgText(assetName);
  return injectSvgMarkup(host, assetName, svgText, svgInstanceKey);
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

  return result;
}
