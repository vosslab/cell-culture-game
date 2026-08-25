// Scene render-yield stats.
//
// computeSceneStats() reports not only what rendered, but what VANISHED: it
// compares the source placements declared in generated/scene_manifest.json
// against the items the browser actually rendered, so a coder can see drops.
//
// SCOPE (WS-M2-B): only easy-to-implement stats land here -- a direct count, a
// divide, or a single bbox check against sceneRootBbox. Anything that needs new
// capture infra or nontrivial geometry (browser-event counts, exact rectangle
// union, severe-overlap/occlusion, stability across runs, balance, zone
// coverage, contrast, interaction-readiness) is deferred to docs/ROADMAP.md and
// is intentionally NOT computed here.
//
// percent_empty_approx is a NAIVE coverage estimate: 1 - (sum of item areas /
// scene area), clamped to [0, 100]. Overlapping items double-count their area,
// so the sum can exceed the scene area and the "empty" estimate is an
// over/undercount, never an exact rectangle union. Named _approx for that
// reason; exact union is deferred.

import { bboxsOverlap } from "./bbox_helpers.mjs";

//============================================
// Input shapes (documented, not enforced)
//============================================

// manifestEntry: one entry from generated/scene_manifest.json:
//   { name, outcome: "emitted"|"skipped", reason: string|null,
//     source_placement_count: int, source_placement_names: string[] }
//
// renderedItems: array of rendered placement records collected by the CLI
// (WS-M2-A/C populates this from DOM queries). Each item:
//   { placementName: string,
//     objectName: string|null,
//     zone: string|null,
//     kind: string|null,
//     depth: number|null,
//     bbox: { x, y, width, height } | null,
//     hasRenderError: boolean,
//     renderErrorKind: "missing-svg" | "missing-object" | null }
//
// labels: array of { bbox: {x,y,width,height}|null, text: string } (label
// readability stats are deferred; labels are accepted for symmetry and a count).
//
// sceneRootBbox: { x, y, width, height } -- the #scene-root bounding box.

//============================================
// Tuning constants (hardcoded, not flags)
//============================================

// A populated scene whose naive coverage is below this is flagged near-empty.
// Advisory only; gates no milestone. Threshold value is a WS-M2-B decision.
const NEAR_EMPTY_COVERAGE_PERCENT = 5;

// An item whose rendered area is at or below this many square px is "tiny".
const TINY_ITEM_AREA_PX = 100;

//============================================
// Small numeric helpers
//============================================

// Clamps a number into [min, max].
function clamp(value, min, max) {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

// Rounds to one decimal place for stable, human-readable percentages.
function round1(value) {
  return Math.round(value * 10) / 10;
}

// Area of a bbox, or 0 when the bbox is missing.
function bboxArea(bbox) {
  if (!bbox) return 0;
  return bbox.width * bbox.height;
}

//============================================
// Layout checks (single bbox vs sceneRootBbox)
//============================================

// True when item is entirely outside the scene root (no overlap at all).
function isFullyOffscreen(itemBbox, sceneRootBbox) {
  if (!itemBbox || !sceneRootBbox) return false;
  return !bboxsOverlap(itemBbox, sceneRootBbox, 0);
}

// True when the item overlaps the scene root but is not fully contained
// (some part is clipped by the scene edge). Fully-offscreen items are reported
// separately and are not also counted as clipped.
function isClipped(itemBbox, sceneRootBbox) {
  if (!itemBbox || !sceneRootBbox) return false;
  if (isFullyOffscreen(itemBbox, sceneRootBbox)) return false;
  const withinLeft = itemBbox.x >= sceneRootBbox.x;
  const withinTop = itemBbox.y >= sceneRootBbox.y;
  const withinRight = itemBbox.x + itemBbox.width <= sceneRootBbox.x + sceneRootBbox.width;
  const withinBottom = itemBbox.y + itemBbox.height <= sceneRootBbox.y + sceneRootBbox.height;
  const fullyContained = withinLeft && withinTop && withinRight && withinBottom;
  return !fullyContained;
}

//============================================
// Count and yield section
//============================================

// Builds the counts section: source vs rendered, drops, yield, render errors.
function computeCounts(manifestEntry, renderedItems) {
  const sourcePlacementCount = manifestEntry.source_placement_count;
  const sourceNames = manifestEntry.source_placement_names;

  const renderedPlacementCount = renderedItems.length;
  const droppedPlacementCount = Math.max(0, sourcePlacementCount - renderedPlacementCount);

  // Dropped names: source placement names not present among rendered items.
  // Only meaningful when the manifest actually carries source names.
  const renderedNameSet = new Set(renderedItems.map((item) => item.placementName));
  const droppedPlacementNames = sourceNames.filter((name) => !renderedNameSet.has(name));

  const renderErrorItemCount = renderedItems.filter((item) => item.hasRenderError).length;
  const realItemCount = renderedPlacementCount - renderErrorItemCount;

  // Render yield: successfully rendered items / source, as a percent. Diagnostic
  // error cards represent failed content and therefore stay outside the yield.
  // A source count of zero yields 100% by convention.
  let renderYieldPercent;
  if (sourcePlacementCount === 0) {
    renderYieldPercent = 100;
  } else {
    renderYieldPercent = round1((realItemCount / sourcePlacementCount) * 100);
  }

  let renderErrorFraction;
  if (renderedPlacementCount === 0) {
    renderErrorFraction = 0;
  } else {
    renderErrorFraction = round1(renderErrorItemCount / renderedPlacementCount);
  }

  const counts = {
    source_placement_count: sourcePlacementCount,
    rendered_placement_count: renderedPlacementCount,
    dropped_placement_count: droppedPlacementCount,
    dropped_placement_names: droppedPlacementNames,
    render_yield_percent: renderYieldPercent,
    real_item_count: realItemCount,
    render_error_item_count: renderErrorItemCount,
    render_error_fraction: renderErrorFraction,
  };
  return counts;
}

//============================================
// Missing-asset name collection
//============================================

// Collects object names for diagnostic render errors by kind.
function computeMissingNames(renderedItems) {
  const missingObjectNames = [];
  const missingSvgNames = [];
  for (const item of renderedItems) {
    if (!item.hasRenderError) continue;
    // Prefer the object name; fall back to placement name when absent.
    const label = item.objectName || item.placementName;
    if (item.renderErrorKind === "missing-object") {
      missingObjectNames.push(label);
    } else if (item.renderErrorKind === "missing-svg") {
      missingSvgNames.push(label);
    }
  }
  return { missingObjectNames, missingSvgNames };
}

//============================================
// Layout section
//============================================

// Builds the layout section: coverage, overlaps, clipping, offscreen, tiny.
function computeLayout(renderedItems, sceneRootBbox, labels) {
  const sceneArea = bboxArea(sceneRootBbox);

  // Naive coverage: sum of successfully rendered item areas over scene area.
  // Overlaps double-count. Diagnostic error cards stay outside the occupancy
  // estimate so the metric reflects delivered artwork.
  let summedItemArea = 0;
  for (const item of renderedItems) {
    if (item.hasRenderError) continue;
    summedItemArea += bboxArea(item.bbox);
  }
  let percentEmptyApprox;
  if (sceneArea === 0) {
    // No scene area to divide by; report fully empty rather than divide by zero.
    percentEmptyApprox = 100;
  } else {
    const coverageFraction = summedItemArea / sceneArea;
    percentEmptyApprox = round1(clamp((1 - coverageFraction) * 100, 0, 100));
  }

  // Pairwise overlap count using the shared helper.
  let overlapPairCount = 0;
  for (let i = 0; i < renderedItems.length; i++) {
    for (let j = i + 1; j < renderedItems.length; j++) {
      const a = renderedItems[i].bbox;
      const b = renderedItems[j].bbox;
      if (!a || !b) continue;
      if (bboxsOverlap(a, b, 0)) overlapPairCount++;
    }
  }

  // Pairwise label-vs-label overlap count. Labels with a null bbox (zero-size,
  // not rendered) are skipped so they cannot register a collision.
  let labelOverlapPairCount = 0;
  for (let i = 0; i < labels.length; i++) {
    for (let j = i + 1; j < labels.length; j++) {
      const a = labels[i].bbox;
      const b = labels[j].bbox;
      if (!a || !b) continue;
      if (bboxsOverlap(a, b, 0)) labelOverlapPairCount++;
    }
  }

  // Label-vs-art overlap count: each label box against every item box, with no
  // identity exclusion. A label sitting over its own object art is an overlap
  // and must be counted; there is no instance where any overlap should be
  // excluded. Counting own-art overlap is how the recycle_buffer_bottle
  // label-on-own-cap defect is now caught instead of passing green.
  let labelArtOverlapCount = 0;
  for (const label of labels) {
    if (!label.bbox) continue;
    for (const item of renderedItems) {
      if (!item.bbox) continue;
      if (bboxsOverlap(label.bbox, item.bbox, 0)) labelArtOverlapCount++;
    }
  }

  let clippedItemCount = 0;
  let fullyOffscreenItemCount = 0;
  let tinyItemCount = 0;
  for (const item of renderedItems) {
    if (isFullyOffscreen(item.bbox, sceneRootBbox)) {
      fullyOffscreenItemCount++;
    } else if (isClipped(item.bbox, sceneRootBbox)) {
      clippedItemCount++;
    }
    if (item.bbox && bboxArea(item.bbox) <= TINY_ITEM_AREA_PX) {
      tinyItemCount++;
    }
  }

  const layout = {
    percent_empty_approx: percentEmptyApprox,
    overlap_pair_count: overlapPairCount,
    label_overlap_pair_count: labelOverlapPairCount,
    label_art_overlap_count: labelArtOverlapCount,
    clipped_item_count: clippedItemCount,
    fully_offscreen_item_count: fullyOffscreenItemCount,
    tiny_item_count: tinyItemCount,
    label_count: 0,
  };
  return layout;
}

//============================================
// Geometry block (dump-shaped, single pixel space)
//============================================
//
// This is the canonical geometry the scene_calc validator consumes. It is the
// browser pipeline's output (rendered DOM rects + pipeline-truth aspect and
// scale_source), assembled here so there is exactly one geometry producer.
//
// All boxes are CSS pixels with a top-left origin, in {x, y, w, h} form. Zone
// inner_rect is also pixels (converted from the scene-percent zone bounds using
// the rendered #scene-root box, then padded by zone_padding), so every box fed
// to a rule shares one coordinate space.

// Threshold mirrors validation/scene_lint ASPECT_DISTORTION_THRESHOLD_PCT and
// validation/scene_calc/aspect.py. Kept here only for documentation; the value
// is applied by the rules layer, not gated here.

// Converts a {x,y,width,height} DOM rect to a {x,y,w,h} dump box, or a zeroed
// box when the rect is missing.
function toDumpBox(rect) {
  if (!rect) return { x: 0, y: 0, w: 0, h: 0 };
  return { x: rect.x, y: rect.y, w: rect.width, h: rect.height };
}

// Converts a {x,y,w,h} dump box to {left,right,top,bottom} edge-coordinate form,
// matching the zone bounds/inner_rect convention so every box on a zone entry
// shares one shape.
function dumpBoxToEdges(box) {
  return {
    left: box.x,
    right: box.x + box.w,
    top: box.y,
    bottom: box.y + box.h,
  };
}

// Computes aspect_delta_pct for one rendered item: how far the rendered visual
// box deviates from the intended SVG aspect, as a percentage. Mirrors
// validation/scene_calc/aspect.py: abs(rendered - authored) / authored * 100.
// visualDumpBox is a {x, y, w, h} dump box. Returns 0 when the intended aspect
// or rendered box is unusable.
function aspectDeltaPct(visualDumpBox, intendedAspect) {
  if (!visualDumpBox || visualDumpBox.w <= 0 || visualDumpBox.h <= 0) return 0;
  if (!intendedAspect || intendedAspect <= 0) return 0;
  const renderedAspect = visualDumpBox.w / visualDumpBox.h;
  const delta = (Math.abs(renderedAspect - intendedAspect) / intendedAspect) * 100;
  return round1(delta);
}

// Converts a scene-percent edge rect to a pixel edge rect using the rendered
// scene-root box. percent (0..100 per axis) maps linearly onto the scene-root
// pixel extent.
function pctEdgesToPx(edgesPct, sceneRootBbox) {
  return {
    left: sceneRootBbox.x + (edgesPct.left / 100) * sceneRootBbox.width,
    right: sceneRootBbox.x + (edgesPct.right / 100) * sceneRootBbox.width,
    top: sceneRootBbox.y + (edgesPct.top / 100) * sceneRootBbox.height,
    bottom: sceneRootBbox.y + (edgesPct.bottom / 100) * sceneRootBbox.height,
  };
}

// Converts a scene-percent zone-bounds rect to a padded pixel inner_rect.
// Padding is applied in scene-percent, then converted to pixels.
function zoneInnerRectPx(boundsPct, paddingPct, sceneRootBbox) {
  const inner = {
    left: boundsPct.left + paddingPct,
    right: boundsPct.right - paddingPct,
    top: boundsPct.top + paddingPct,
    bottom: boundsPct.bottom - paddingPct,
  };
  return pctEdgesToPx(inner, sceneRootBbox);
}

// Scene-bounds in pixel edge form: the rendered scene-root box edges. All
// placement boxes are measured against the same scene-root, so this is the
// pixel-space scene_bounds the rules compare against.
function sceneBoundsPx(sceneRootBbox) {
  return {
    left: sceneRootBbox.x,
    right: sceneRootBbox.x + sceneRootBbox.width,
    top: sceneRootBbox.y,
    bottom: sceneRootBbox.y + sceneRootBbox.height,
  };
}

// Builds the dump-shaped geometry block from rendered items, labels, the
// pipeline-truth geometry summary, and the scene-root box. Returns null when
// the pipeline geometry or scene-root box is unavailable (load-failed pages);
// the loader treats a null geometry block as "not renderable" and fails loudly.
function computeGeometry(renderedItems, labels, sceneGeometry, sceneRootBbox, provenance) {
  if (!sceneGeometry || !sceneRootBbox) return null;

  // Index pipeline-truth placements and labels by placement name.
  const truthByName = new Map();
  for (const p of sceneGeometry.placements) {
    truthByName.set(p.placement_name, p);
  }
  const labelByPlacement = new Map();
  for (const lab of labels) {
    if (lab.labelFor) labelByPlacement.set(lab.labelFor, lab);
  }

  const placements = [];
  for (const item of renderedItems) {
    const truth = truthByName.get(item.placementName);
    // placement_bbox: the positioned item div rect.
    const placementBox = toDumpBox(item.bbox);
    // visual_bbox: the inner SVG asset rect (or div rect when no SVG).
    const visualBox = toDumpBox(item.visualBbox ?? item.bbox);
    // label_bbox: the matched label element rect.
    const labelRec = labelByPlacement.get(item.placementName);
    const labelBox = toDumpBox(labelRec ? labelRec.bbox : null);
    // footprint_bbox: the rendered layout footprint, taken as the union of the
    // placement box and its label box (the space the item plus label occupy).
    const footprintBox = unionBox(placementBox, labelBox);

    const intendedAspect = truth ? truth.aspect : null;
    const scaleSource = truth ? truth.scale_source : "skipped_error";
    placements.push({
      placement_name: item.placementName,
      kind: item.kind ?? (truth ? truth.kind : "unknown"),
      asset_path: truth ? truth.asset : "<unknown>",
      visual_bbox: visualBox,
      placement_bbox: placementBox,
      footprint_bbox: footprintBox,
      label_bbox: labelBox,
      aspect_delta_pct: aspectDeltaPct(visualBox, intendedAspect),
      scale_source: scaleSource,
    });
  }

  // Measured per-zone extent: the union of the placement boxes of every rendered
  // item tagged with that data-zone. This is the RENDERED zone footprint, keyed
  // by item.zone (the DOM data-zone attribute), distinct from the DECLARED zone
  // bounds/inner_rect below (pipeline-truth scene-percent bounds). Items with no
  // zone or no positive-area box contribute nothing.
  const zoneItemUnions = new Map();
  for (const item of renderedItems) {
    if (!item.zone) continue;
    const box = toDumpBox(item.bbox);
    if (box.w <= 0 || box.h <= 0) continue;
    const prev = zoneItemUnions.get(item.zone);
    zoneItemUnions.set(item.zone, prev ? unionBox(prev, box) : box);
  }

  const zones = [];
  for (const zone of sceneGeometry.zones) {
    const boundsPx = pctEdgesToPx(zone.bounds, sceneRootBbox);
    const innerRect = zoneInnerRectPx(zone.bounds, sceneGeometry.zone_padding, sceneRootBbox);
    // item_union_rect: measured union (edge-coord pixels) of every rendered item
    // whose data-zone equals this zone, or null when no item rendered into it.
    const unionForZone = zoneItemUnions.get(zone.name) ?? null;
    zones.push({
      name: zone.name,
      bounds: boundsPx,
      inner_rect: innerRect,
      item_union_rect: unionForZone ? dumpBoxToEdges(unionForZone) : null,
    });
  }

  return {
    coordinate_space: "css_px_top_left",
    scene_bounds: sceneBoundsPx(sceneRootBbox),
    placements,
    zones,
    // Informational render provenance (which built bundle produced this geometry
    // and when the render ran). Supplied by the impure caller so this module
    // stays deterministic; null when the caller passes none.
    provenance: provenance ?? null,
  };
}

// Union of two {x,y,w,h} boxes. A zero-area box contributes nothing.
function unionBox(a, b) {
  const aValid = a.w > 0 && a.h > 0;
  const bValid = b.w > 0 && b.h > 0;
  if (!aValid && !bValid) return { x: 0, y: 0, w: 0, h: 0 };
  if (!bValid) return { ...a };
  if (!aValid) return { ...b };
  const left = Math.min(a.x, b.x);
  const top = Math.min(a.y, b.y);
  const right = Math.max(a.x + a.w, b.x + b.w);
  const bottom = Math.max(a.y + a.h, b.y + b.h);
  return { x: left, y: top, w: right - left, h: bottom - top };
}

//============================================
// Classification (mutually exclusive categories)
//============================================

// Returns one of: populated | error-only | empty.
// "load-failed" is set by the caller when the page threw before render; it is
// passed in via opts.loadFailed. "skipped" is set by the caller from the
// manifest, never computed here.
function classifyScene(counts, loadFailed) {
  if (loadFailed) return "load-failed";
  if (counts.rendered_placement_count === 0) return "empty";
  if (counts.real_item_count === 0) return "error-only";
  return "populated";
}

//============================================
// Advisory flags (orthogonal, can stack)
//============================================

// near-empty: a populated scene whose naive coverage is below threshold.
// degraded: renders real items but drops source placements or has missing assets.
function computeAdvisoryFlags(category, counts, layout, missing) {
  const flags = [];

  const isNearEmpty =
    category === "populated" && 100 - layout.percent_empty_approx < NEAR_EMPTY_COVERAGE_PERCENT;
  if (isNearEmpty) flags.push("near-empty");

  const hasMissingAssets =
    missing.missingObjectNames.length > 0 || missing.missingSvgNames.length > 0;
  const isDegraded =
    counts.real_item_count > 0 && (counts.dropped_placement_count > 0 || hasMissingAssets);
  if (isDegraded) flags.push("degraded");

  return flags;
}

//============================================
// Pass/fail verdict (raw stats are primary; NO single quality score)
//============================================

function computePassFail(category, counts, missing) {
  const renders = category === "populated" || category === "error-only";
  const noDroppedPlacements = counts.dropped_placement_count === 0;
  const noMissingAssets =
    missing.missingObjectNames.length === 0 && missing.missingSvgNames.length === 0;
  return {
    renders,
    no_dropped_placements: noDroppedPlacements,
    no_missing_assets: noMissingAssets,
  };
}

//============================================
// Public entry point
//============================================

// Computes the full structured stats object for one scene.
//
// args:
//   sceneName: string
//   manifestEntry: manifest row (see shape note above)
//   renderedItems: array of rendered item records (see shape note above)
//   labels: array of label records (see shape note above)
//   sceneRootBbox: { x, y, width, height } | null
//   loadFailed: optional boolean -- true when the page threw before render
//
// Returns a STRUCTURED object with sections: identity, classification, counts,
// layout, flags, pass_fail.
export function computeSceneStats({
  sceneName,
  manifestEntry,
  renderedItems,
  labels,
  sceneRootBbox,
  sceneGeometry = null,
  provenance = null,
  loadFailed = false,
}) {
  const items = renderedItems || [];
  const labelList = labels || [];

  const counts = computeCounts(manifestEntry, items);
  const missing = computeMissingNames(items);
  const layout = computeLayout(items, sceneRootBbox, labelList);
  layout.label_count = labelList.length;

  // Dump-shaped geometry for the scene_calc validator (single producer). Null on
  // load-failed pages; the loader fails loudly rather than synthesizing geometry.
  const geometry = computeGeometry(items, labelList, sceneGeometry, sceneRootBbox, provenance);

  const category = classifyScene(counts, loadFailed);
  const advisoryFlags = computeAdvisoryFlags(category, counts, layout, missing);
  const passFail = computePassFail(category, counts, missing);

  const stats = {
    identity: {
      scene_name: sceneName,
      outcome: manifestEntry.outcome,
      reason: manifestEntry.reason,
    },
    classification: {
      category: category,
    },
    counts: counts,
    layout: layout,
    flags: {
      advisory_flags: advisoryFlags,
      missing_object_names: missing.missingObjectNames,
      missing_svg_names: missing.missingSvgNames,
    },
    pass_fail: passFail,
    geometry: geometry,
  };
  return stats;
}
