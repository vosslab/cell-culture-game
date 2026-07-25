// Shared, deterministic interpretation of scene-item render evidence.
//
// The browser collector in scene_to_png.mjs gathers DOM facts, then delegates
// placeholder classification and visual-box selection here. Keeping those
// decisions outside page.evaluate makes the diagnostic contract directly
// testable without a browser and prevents renderer-mode assumptions from
// leaking into scene statistics.

// A browser reports a loaded <img> as complete with intrinsic dimensions.
// `complete` alone also describes a broken image, so both natural dimensions
// are required before a static SVG image counts as rendered art.
export function isLoadedStaticSvgImage(staticImage) {
  return (
    staticImage !== null &&
    staticImage.present === true &&
    staticImage.complete === true &&
    staticImage.naturalWidth > 0 &&
    staticImage.naturalHeight > 0
  );
}

// Classifies one item from renderer DOM facts. Explicit placeholder markers
// always win: a generated placeholder-art SVG may itself contain an inline
// <svg> or a successfully loaded <img>, but it remains a placeholder by
// authored diagnostic intent.
export function classifyRenderedItem(snapshot, placeholderKeys) {
  if (snapshot.placeholderKind !== null) {
    return { isPlaceholder: true, placeholderKind: snapshot.placeholderKind };
  }
  if (snapshot.hasMissingSvgMarker) {
    return { isPlaceholder: true, placeholderKind: "missing-svg" };
  }
  if (snapshot.assetKey !== null && placeholderKeys.has(snapshot.assetKey)) {
    return { isPlaceholder: true, placeholderKind: "placeholder-art" };
  }

  if (snapshot.hasInlineSvg || isLoadedStaticSvgImage(snapshot.staticImage)) {
    return { isPlaceholder: false, placeholderKind: null };
  }

  // A declared graphic host with no usable visual is an asset-load failure,
  // rather than an absent scene object. This includes an unloaded or broken
  // static image and a DOM-SVG host whose fetch/injection failed.
  if (snapshot.hasDomSvgHost || snapshot.staticImage !== null) {
    return { isPlaceholder: true, placeholderKind: "missing-svg" };
  }

  return { isPlaceholder: true, placeholderKind: "missing-object" };
}

function hasPositiveArea(bbox) {
  return bbox !== null && bbox.width > 0 && bbox.height > 0;
}

// Prefer the real artwork's box over the layout wrapper. The wrapper remains
// the fallback for placeholder text or an unloaded image, which has no visual
// footprint to measure.
export function selectVisualBbox(snapshot) {
  if (snapshot.hasInlineSvg && hasPositiveArea(snapshot.inlineSvgBbox)) {
    return snapshot.inlineSvgBbox;
  }
  if (isLoadedStaticSvgImage(snapshot.staticImage) && hasPositiveArea(snapshot.staticImageBbox)) {
    return snapshot.staticImageBbox;
  }
  return snapshot.placementBbox;
}
