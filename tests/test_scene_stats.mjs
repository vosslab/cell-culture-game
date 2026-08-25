// Deterministic unit tests for tools/scene_stats.mjs.
//
// All inputs are fixed mocks; no browser, no network. Assertions are
// behavioral (derived from the mock inputs), not magic constants: render-yield
// equals rendered/source, dropped-count equals the source names that did not
// render, and percent_empty_approx equals 1 - summed-area/scene-area clamped.
//
// Run via:
//   node --test tests/test_scene_stats.mjs

import { test } from "node:test";
import assert from "node:assert/strict";

import { computeSceneStats } from "../tools/scene_stats.mjs";

//============================================
// Mock builders
//============================================

// Builds a manifest entry with the given source placement names.
function makeManifestEntry(name, sourceNames, overrides = {}) {
  return {
    name: name,
    outcome: "emitted",
    reason: null,
    source_placement_count: sourceNames.length,
    source_placement_names: sourceNames,
    ...overrides,
  };
}

// Builds a rendered item record. bbox defaults to a 10x10 box at the origin.
function makeItem(placementName, overrides = {}) {
  return {
    placementName: placementName,
    objectName: placementName + "_obj",
    zone: "bench",
    kind: "object",
    depth: 0,
    bbox: { x: 0, y: 0, width: 10, height: 10 },
    hasRenderError: false,
    renderErrorKind: null,
    ...overrides,
  };
}

const SCENE_ROOT = { x: 0, y: 0, width: 100, height: 100 };

//============================================
// Render yield and dropped placements
//============================================

test("render yield is rendered over source as a percent", () => {
  // 4 source placements, 3 of them rendered -> 75%.
  const sourceNames = ["a", "b", "c", "d"];
  const manifestEntry = makeManifestEntry("yield_scene", sourceNames);
  const renderedItems = [makeItem("a"), makeItem("b"), makeItem("c")];

  const stats = computeSceneStats({
    sceneName: "yield_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });

  const expectedYield = (renderedItems.length / sourceNames.length) * 100;
  assert.equal(stats.counts.render_yield_percent, expectedYield);
  assert.equal(stats.counts.source_placement_count, sourceNames.length);
  assert.equal(stats.counts.rendered_placement_count, renderedItems.length);
});

test("dropped count and names are the source placements that did not render", () => {
  const sourceNames = ["a", "b", "c", "d"];
  const manifestEntry = makeManifestEntry("drop_scene", sourceNames);
  // Render only a and c; b and d dropped.
  const renderedItems = [makeItem("a"), makeItem("c")];

  const stats = computeSceneStats({
    sceneName: "drop_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });

  const expectedDropped = sourceNames.filter(
    (name) => !renderedItems.some((item) => item.placementName === name),
  );
  assert.equal(stats.counts.dropped_placement_count, expectedDropped.length);
  assert.deepEqual(stats.counts.dropped_placement_names, expectedDropped);
});

test("zero source placements yields 100 percent and no drops", () => {
  const manifestEntry = makeManifestEntry("empty_source", []);
  const stats = computeSceneStats({
    sceneName: "empty_source",
    manifestEntry,
    renderedItems: [],
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.counts.render_yield_percent, 100);
  assert.equal(stats.counts.dropped_placement_count, 0);
});

//============================================
// Coverage approximation math
//============================================

test("percent_empty_approx equals 1 minus summed-area over scene-area", () => {
  // Scene is 100x100 = 10000. Two non-overlapping 20x20 items = 800 total.
  const sourceNames = ["a", "b"];
  const manifestEntry = makeManifestEntry("coverage_scene", sourceNames);
  const renderedItems = [
    makeItem("a", { bbox: { x: 0, y: 0, width: 20, height: 20 } }),
    makeItem("b", { bbox: { x: 50, y: 50, width: 20, height: 20 } }),
  ];

  const stats = computeSceneStats({
    sceneName: "coverage_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });

  const sceneArea = SCENE_ROOT.width * SCENE_ROOT.height;
  const summed = 20 * 20 + 20 * 20;
  const expectedEmpty = (1 - summed / sceneArea) * 100;
  assert.equal(stats.layout.percent_empty_approx, expectedEmpty);
});

test("percent_empty_approx clamps to zero when items over-cover via overlap", () => {
  // Two fully-overlapping items each filling the whole scene: summed area is
  // 2x the scene area, so the naive coverage exceeds 1 and empty clamps to 0.
  const sourceNames = ["a", "b"];
  const manifestEntry = makeManifestEntry("overcover_scene", sourceNames);
  const fullBox = { x: 0, y: 0, width: 100, height: 100 };
  const renderedItems = [
    makeItem("a", { bbox: { ...fullBox } }),
    makeItem("b", { bbox: { ...fullBox } }),
  ];

  const stats = computeSceneStats({
    sceneName: "overcover_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });

  assert.equal(stats.layout.percent_empty_approx, 0);
  // The two identical full-scene boxes also register as one overlapping pair.
  assert.equal(stats.layout.overlap_pair_count, 1);
});

//============================================
// Classification and render-error accounting
//============================================

test("category is empty when nothing rendered", () => {
  const manifestEntry = makeManifestEntry("blank_scene", ["a", "b"]);
  const stats = computeSceneStats({
    sceneName: "blank_scene",
    manifestEntry,
    renderedItems: [],
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.classification.category, "empty");
  assert.equal(stats.pass_fail.renders, false);
});

test("category is error-only when all rendered items are diagnostic errors", () => {
  const manifestEntry = makeManifestEntry("ph_scene", ["a", "b"]);
  const renderedItems = [
    makeItem("a", { hasRenderError: true, renderErrorKind: "missing-svg" }),
    makeItem("b", { hasRenderError: true, renderErrorKind: "missing-object" }),
  ];
  const stats = computeSceneStats({
    sceneName: "ph_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.classification.category, "error-only");
  assert.equal(stats.counts.real_item_count, 0);
  assert.equal(stats.counts.render_error_item_count, 2);
  assert.deepEqual(stats.flags.missing_svg_names, ["a_obj"]);
  assert.deepEqual(stats.flags.missing_object_names, ["b_obj"]);
  // An error card still proves the renderer produced observable output.
  assert.equal(stats.pass_fail.renders, true);
});

test("category is populated and degraded flag set when real items but drops exist", () => {
  const manifestEntry = makeManifestEntry("degraded_scene", ["a", "b", "c"]);
  // Two real items rendered, c dropped.
  const renderedItems = [makeItem("a"), makeItem("b")];
  const stats = computeSceneStats({
    sceneName: "degraded_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.classification.category, "populated");
  assert.ok(stats.flags.advisory_flags.includes("degraded"));
  assert.equal(stats.pass_fail.no_dropped_placements, false);
});

test("load-failed category set from caller flag overrides render counts", () => {
  const manifestEntry = makeManifestEntry("failed_scene", ["a"]);
  const stats = computeSceneStats({
    sceneName: "failed_scene",
    manifestEntry,
    renderedItems: [makeItem("a")],
    labels: [],
    sceneRootBbox: SCENE_ROOT,
    loadFailed: true,
  });
  assert.equal(stats.classification.category, "load-failed");
});

//============================================
// Layout: clipping, offscreen, tiny
//============================================

test("clipped and fully-offscreen items are counted distinctly", () => {
  const manifestEntry = makeManifestEntry("layout_scene", ["inside", "clip", "off"]);
  const renderedItems = [
    // Fully inside the scene root.
    makeItem("inside", { bbox: { x: 10, y: 10, width: 10, height: 10 } }),
    // Straddles the right edge -> clipped.
    makeItem("clip", { bbox: { x: 95, y: 10, width: 20, height: 10 } }),
    // Entirely past the bottom edge -> fully offscreen.
    makeItem("off", { bbox: { x: 10, y: 200, width: 10, height: 10 } }),
  ];
  const stats = computeSceneStats({
    sceneName: "layout_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.layout.clipped_item_count, 1);
  assert.equal(stats.layout.fully_offscreen_item_count, 1);
});

test("tiny items are counted by area threshold", () => {
  const manifestEntry = makeManifestEntry("tiny_scene", ["big", "small"]);
  const renderedItems = [
    makeItem("big", { bbox: { x: 0, y: 0, width: 30, height: 30 } }),
    // 5x5 = 25 sq px, at or below the 100 sq px threshold.
    makeItem("small", { bbox: { x: 40, y: 40, width: 5, height: 5 } }),
  ];
  const stats = computeSceneStats({
    sceneName: "tiny_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.layout.tiny_item_count, 1);
});

//============================================
// Label collision counts
//============================================

test("two overlapping labels count one label-overlap pair", () => {
  const manifestEntry = makeManifestEntry("label_scene", ["a"]);
  const renderedItems = [makeItem("a", { bbox: { x: 0, y: 0, width: 5, height: 5 } })];
  // Two label boxes that overlap each other.
  const labels = [
    { bbox: { x: 40, y: 40, width: 20, height: 10 }, text: "one", labelFor: null },
    { bbox: { x: 50, y: 42, width: 20, height: 10 }, text: "two", labelFor: null },
  ];
  const stats = computeSceneStats({
    sceneName: "label_scene",
    manifestEntry,
    renderedItems,
    labels,
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.layout.label_overlap_pair_count, 1);
});

test("disjoint labels count zero label-overlap pairs", () => {
  const manifestEntry = makeManifestEntry("label_scene", ["a"]);
  const renderedItems = [makeItem("a", { bbox: { x: 0, y: 0, width: 5, height: 5 } })];
  // Two label boxes that do not overlap.
  const labels = [
    { bbox: { x: 10, y: 10, width: 10, height: 10 }, text: "one", labelFor: null },
    { bbox: { x: 60, y: 60, width: 10, height: 10 }, text: "two", labelFor: null },
  ];
  const stats = computeSceneStats({
    sceneName: "label_scene",
    manifestEntry,
    renderedItems,
    labels,
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.layout.label_overlap_pair_count, 0);
});

test("every label-art overlap counts, including a label over its own item", () => {
  const manifestEntry = makeManifestEntry("label_scene", ["own", "other"]);
  const renderedItems = [
    makeItem("own", { bbox: { x: 0, y: 0, width: 20, height: 20 } }),
    makeItem("other", { bbox: { x: 50, y: 50, width: 20, height: 20 } }),
  ];
  // No identity exclusion: own-art overlap counts. labelOwn (5,5,60x60) covers
  // both the "own" item (0,0,20x20) and the "other" item (50,50,20x20) -> 2
  // overlaps. labelOther (52,52,5x5) sits over its own "other" item -> 1 more.
  // labelOther does not reach "own". Total: 3 counted overlaps.
  const labels = [
    { bbox: { x: 5, y: 5, width: 60, height: 60 }, text: "own", labelFor: "own" },
    { bbox: { x: 52, y: 52, width: 5, height: 5 }, text: "other", labelFor: "other" },
  ];
  const stats = computeSceneStats({
    sceneName: "label_scene",
    manifestEntry,
    renderedItems,
    labels,
    sceneRootBbox: SCENE_ROOT,
  });
  // labelOwn-vs-own, labelOwn-vs-other, labelOther-vs-other all count.
  assert.equal(stats.layout.label_art_overlap_count, 3);
});

//============================================
// Geometry: per-zone item union and provenance
//============================================

test("zone item_union_rect is the edge-form union of same-zone item boxes", () => {
  const manifestEntry = makeManifestEntry("zone_scene", ["a", "b"]);
  // Two items both tagged data-zone "bench"; one item-free zone "shelf".
  const renderedItems = [
    makeItem("a", { zone: "bench", bbox: { x: 10, y: 10, width: 20, height: 20 } }),
    makeItem("b", { zone: "bench", bbox: { x: 50, y: 40, width: 10, height: 10 } }),
  ];
  const sceneGeometry = {
    zones: [
      { name: "bench", bounds: { left: 0, right: 100, top: 0, bottom: 100 } },
      { name: "shelf", bounds: { left: 0, right: 100, top: 0, bottom: 100 } },
    ],
    zone_padding: 0,
    placements: [],
  };
  const stats = computeSceneStats({
    sceneName: "zone_scene",
    manifestEntry,
    renderedItems,
    labels: [],
    sceneRootBbox: SCENE_ROOT,
    sceneGeometry,
  });
  const benchZone = stats.geometry.zones.find((z) => z.name === "bench");
  // Union of (10,10,20x20) and (50,40,10x10): left=10, top=10, right=60, bottom=50.
  assert.deepEqual(benchZone.item_union_rect, { left: 10, right: 60, top: 10, bottom: 50 });
  // A zone with no rendered items has a null union.
  const shelfZone = stats.geometry.zones.find((z) => z.name === "shelf");
  assert.equal(shelfZone.item_union_rect, null);
});

test("geometry provenance echoes the informational stamp from the caller", () => {
  const manifestEntry = makeManifestEntry("prov_scene", ["a"]);
  // A fixed provenance object (no clock read) so the assertion stays stable.
  const provenance = {
    renderer_bundle: "dist/scene_viewer.js@2020-01-01T00:00:00.000Z",
    rendered_at: "2020-01-01T00:00:00.000Z",
  };
  const sceneGeometry = { zones: [], zone_padding: 0, placements: [] };
  const stats = computeSceneStats({
    sceneName: "prov_scene",
    manifestEntry,
    renderedItems: [makeItem("a")],
    labels: [],
    sceneRootBbox: SCENE_ROOT,
    sceneGeometry,
    provenance,
  });
  assert.deepEqual(stats.geometry.provenance, provenance);
});

//============================================
// Structured output shape
//============================================

test("output has the documented section structure", () => {
  const manifestEntry = makeManifestEntry("shape_scene", ["a"]);
  const stats = computeSceneStats({
    sceneName: "shape_scene",
    manifestEntry,
    renderedItems: [makeItem("a")],
    labels: [{ bbox: { x: 0, y: 0, width: 5, height: 5 }, text: "x" }],
    sceneRootBbox: SCENE_ROOT,
  });
  assert.equal(stats.identity.scene_name, "shape_scene");
  assert.equal(stats.layout.label_count, 1);
});
