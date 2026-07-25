// Test suite for structural_guards.ts
// Tests each of the 8 guards with passing and failing cases.
// Fixtures use center-coordinate semantics (WP-1b): _centerX is the horizontal
// center; itemBbox derives left = _centerX - _visualWidth/2.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  runStructuralGuards,
  collectStructuralViolations,
  enforceNoLabelOwnSvgOverlap,
} from "../src/scene_runtime/renderer/structural_guards.ts";

//============================================
// Test helper: create minimal mock data
//============================================

function createMockItem(overrides = {}) {
  // Default item fits inside test_zone bounds [5, 30, 10, 40] (left,right,top,bottom).
  // _centerX=17, _visualWidth=12 -> itemBbox left=11, right=23 (inside zone [5,30]).
  // _top=15, _height=10 -> itemBbox top=15, bottom=25 (inside zone [10,40]).
  // _labelY=27 -> label below item, inside scene bounds [1,99,5,95].
  // Vortex: SVG aspect 0.8398498359904226, viewport 1920x1080 (aspect 1.777777778)
  // percent_aspect = aspect / viewport_aspect ~0.472414
  // For _visualWidth=12: _height = 12 / 0.472414 ~25.408
  return {
    placement_name: "test_item",
    object_name: "vortex",
    zone: "test_zone",
    kind: "equipment",
    asset: "vortex",
    depth: "mid",
    label: "Test",
    layout: {
      default_width: 12,
      label_width: 10,
      anchor_y: "bottom",
      anchor_y_offset: 0,
      width_scale: 1.0,
      fudge: 0,
    },
    _centerX: 17,
    _top: 15,
    _visualWidth: 12,
    // For Guard 5 aspect check: correct vortex aspect at _visualWidth=12
    _height: 25.408, // percent_aspect = 12/25.408 ~0.472414, renderedAspect = 0.472414 * 1.778 ~0.8398
    _labelX: 17,
    // Label below item: _top + _height = 15 + 25.408 = 40.408, label at 42, inside scene [5,95]
    _labelY: 42,
    _labelLines: ["Test"],
    ...overrides,
  };
}

function createMockScene(overrides = {}) {
  return {
    scene_name: "test_scene",
    workspace: "bench",
    scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
    zones: [
      {
        id: "test_zone",
        bounds: { left: 5, right: 30, top: 10, bottom: 50 },
      },
    ],
    layout_rules: { zone_gap: 2 },
    placements: [],
    ...overrides,
  };
}

//============================================
// Guard 1: Every item inside its zone bbox
//============================================

test("guard 1: item inside zone passes", () => {
  const item = createMockItem();
  const scene = createMockScene();
  // Should not throw
  runStructuralGuards([item], scene);
});

test("guard 1: zone lookup miss throws", () => {
  // Item references a zone that does not exist in the scene -> zone_lookup violation
  const item = createMockItem({ zone: "nonexistent_zone" });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 2: Every zone inside scene_bounds
//============================================

test("guard 2: zone inside scene passes", () => {
  const item = createMockItem();
  const scene = createMockScene();
  runStructuralGuards([item], scene);
});

test("guard 2: zone outside scene bounds throws", () => {
  const scene = createMockScene({
    zones: [
      {
        id: "test_zone",
        bounds: { left: 0, right: 100, top: 0, bottom: 100 }, // exceeds [1,99,5,95]
      },
    ],
  });
  // Use an item that fits in the oversized zone
  const item = createMockItem({ _centerX: 50, _top: 50 });
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 3: No item-item overlap
//============================================

test("guard 3: overlapping items throw", () => {
  // item_a: _centerX=17, _visualWidth=10 -> left=12, right=22
  // item_b: _centerX=19, _visualWidth=10 -> left=14, right=24
  // Overlap: max(12,14)=14 to min(22,24)=22 -> 8 units wide -> >1% overlap
  const itemA = createMockItem({
    placement_name: "item_a",
    _centerX: 17,
    _visualWidth: 10,
    _height: 21.17, // vortex aspect (10 / 0.472414)
  });
  const itemB = createMockItem({
    placement_name: "item_b",
    _centerX: 19, // overlaps with item_a
    _visualWidth: 10,
    _height: 21.17,
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([itemA, itemB], scene), Error);
});

test("guard 3: non-overlapping items pass", () => {
  // item_c: _centerX=10, _visualWidth=5 -> left=7.5, right=12.5
  // item_d: _centerX=16, _visualWidth=5 -> left=13.5, right=18.5
  // Gap: 13.5-12.5 = 1.0 (no overlap)
  const itemC = createMockItem({
    placement_name: "item_c",
    _centerX: 10,
    _top: 10,
    _visualWidth: 5,
    _height: 10.58, // vortex aspect (5 / 0.472414)
    _labelY: 22,
  });
  const itemD = createMockItem({
    placement_name: "item_d",
    _centerX: 17,
    _top: 10,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 22,
  });
  const scene = createMockScene();
  runStructuralGuards([itemC, itemD], scene);
});

//============================================
// Guard 4: Same-row, same-cluster gap >= zone_gap
//============================================

test("guard 4: adjacent items with sufficient gap pass", () => {
  // item_4a: _centerX=10, _visualWidth=5 -> left=7.5, right=12.5
  // item_4b: _centerX=17, _visualWidth=5 -> left=14.5, right=19.5
  // Gap = 14.5-12.5 = 2.0, zone_gap=2 (percent) -> passes
  const item4A = createMockItem({
    placement_name: "item_4a",
    _centerX: 10,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const item4B = createMockItem({
    placement_name: "item_4b",
    _centerX: 17,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const scene = createMockScene();
  runStructuralGuards([item4A, item4B], scene);
});

test("guard 4: floating-point noise at the required gap passes", () => {
  const item4A = createMockItem({
    placement_name: "item_4a",
    _centerX: 10,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const item4B = createMockItem({
    placement_name: "item_4b",
    _centerX: 16.999999999,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const scene = createMockScene();
  runStructuralGuards([item4A, item4B], scene);
});

test("guard 4: adjacent same-tier items below the scene-percent gap throw", () => {
  const item4A = createMockItem({
    placement_name: "item_4a",
    depth_tier: 1,
    _centerX: 10,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const item4B = createMockItem({
    placement_name: "item_4b",
    depth_tier: 1,
    _centerX: 16,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 35,
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item4A, item4B], scene), /zone gap/);
});

test("guard 4: edge-aligned items in separate depth tiers are separate rows", () => {
  const item4A = createMockItem({
    placement_name: "item_4a",
    depth_tier: 1,
    _centerX: 10,
    _top: 10,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 23,
  });
  const item4B = createMockItem({
    placement_name: "item_4b",
    depth_tier: 2,
    _centerX: 15.05,
    _top: 55,
    _visualWidth: 5,
    _height: 10.58,
    _labelY: 68,
  });
  const scene = createMockScene({
    zones: [
      {
        id: "test_zone",
        bounds: { left: 5, right: 30, top: 5, bottom: 75 },
      },
    ],
  });
  runStructuralGuards([item4A, item4B], scene);
});

test("guard 4: separate tab-stop clusters do not invent a shared-row gap requirement", () => {
  // `tab-stops` anchors left, center, and right clusters independently. The
  // layout engine applies zone_gap inside each cluster, not between clusters.
  // These close-but-nonoverlapping items therefore remain structurally valid.
  const item4A = createMockItem({
    placement_name: "left_cluster_item",
    align_stop: "left",
    _centerX: 10,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelX: 10,
    _labelY: 35,
  });
  const item4B = createMockItem({
    placement_name: "center_cluster_item",
    align_stop: "center",
    _centerX: 15.75,
    _top: 20,
    _visualWidth: 5,
    _height: 10.58,
    _labelX: 15.75,
    _labelY: 35,
  });
  const scene = createMockScene({
    zones: [
      {
        id: "test_zone",
        align: "tab-stops",
        bounds: { left: 5, right: 30, top: 10, bottom: 50 },
      },
    ],
  });
  runStructuralGuards([item4A, item4B], scene);
});

//============================================
// Guard 5: Aspect ratio preserved
//============================================

test("guard 5: correct vortex aspect passes", () => {
  // vortex SVG aspect 0.8398; viewport 1920x1080; correct _height for _visualWidth=12 is ~25.41
  const item = createMockItem({
    placement_name: "item_5_good",
    asset: "vortex",
    _visualWidth: 12,
    _height: 25.41,
    _centerX: 17,
    _top: 15,
    _labelY: 42,
  });
  const scene = createMockScene();
  runStructuralGuards([item], scene);
});

test("guard 5: wrong aspect throws", () => {
  // _height=6 -> percent_aspect = 12/6 = 2.0 -> renderedAspect = 2.0*1.7778 ~3.556 (vs expected 0.8398)
  const item = createMockItem({
    placement_name: "item_5_bad",
    asset: "vortex",
    _visualWidth: 12,
    _height: 6, // wrong aspect
    _centerX: 17,
    _top: 15,
    _labelY: 42,
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 6: Asset resolves in SVG_MANIFEST
//============================================

test("guard 6: real asset passes", () => {
  const item = createMockItem({ placement_name: "item_6_good", asset: "vortex" });
  const scene = createMockScene();
  runStructuralGuards([item], scene);
});

test("guard 6: missing asset throws", () => {
  const item = createMockItem({
    placement_name: "item_6_bad",
    asset: "nonexistent_asset_xyz",
    _height: 25.408, // keep valid aspect to avoid aspect check error first
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 7: No label outside scene
//============================================

test("guard 7: label inside scene passes", () => {
  const item = createMockItem({
    placement_name: "item_7_good",
    _labelX: 50, // inside scene [1, 99]
    _labelY: 50, // inside scene [5, 95]
    _labelLines: ["Label"],
    _height: 25.408,
  });
  const scene = createMockScene();
  runStructuralGuards([item], scene);
});

test("guard 7: label outside scene throws", () => {
  // _labelX=105 -> labelLeft = 105 - (13*0.45)/2 = 105 - 2.925 = 102.075 -> outside [1,99]
  const item = createMockItem({
    placement_name: "item_7_bad",
    _labelX: 105, // outside scene [1, 99]
    _labelY: 50,
    _labelLines: ["Out of bounds"],
    _height: 25.408,
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 8: No label overlap with own SVG
//============================================

test("guard 8: label above SVG does not overlap", () => {
  // item: _centerX=17, _top=20, _visualWidth=10, _height=21.17
  // itemBbox: left=12, right=22, top=20, bottom=41.17
  // label: _labelX=17, _labelY=7 -> labelTop=7, labelBottom=7+2.2=9.2 (below scene top=5)
  // labelLeft=17-0.45*3/2=17-0.675=16.325, labelRight=17.325
  // No vertical overlap: labelBottom=9.2 < itemTop=20
  const item = createMockItem({
    placement_name: "item_8_good",
    _centerX: 17,
    _top: 20,
    _visualWidth: 10,
    _height: 21.17,
    _labelX: 17,
    _labelY: 7,
    _labelLines: ["Far"],
  });
  const scene = createMockScene();
  runStructuralGuards([item], scene);
});

test("guard 8: label overlapping own SVG throws", () => {
  // item: _centerX=17, _top=15, _visualWidth=12, _height=25.408
  // itemBbox: left=11, right=23, top=15, bottom=40.408
  // label: "Overlapping text with lots of words" = 35 chars
  // labelWidth = 35 * 0.45 = 15.75
  // _labelX=17 -> labelLeft=17-7.875=9.125, labelRight=24.875
  // _labelY=20 -> labelTop=20, labelBottom=22.2
  // Horizontal overlap: max(11,9.125)=11 to min(23,24.875)=23 -> 12 wide
  // Vertical overlap: max(15,20)=20 to min(40.408,22.2)=22.2 -> 2.2 tall
  // guard 8 fires (overlap > 1%)
  const item = createMockItem({
    placement_name: "item_8_bad",
    _centerX: 17,
    _top: 15,
    _visualWidth: 12,
    _height: 25.408,
    _labelX: 17,
    _labelY: 20, // inside SVG bbox
    _labelLines: ["Overlapping text with lots of words"],
  });
  const scene = createMockScene();
  assert.throws(() => runStructuralGuards([item], scene), Error);
});

//============================================
// Guard 8 gate escalation: own-art overlap hard-fails at live render
//============================================

test("enforceNoLabelOwnSvgOverlap throws when own-art overlap is present", () => {
  // Same geometry as the throwing Guard 8 case: the label sits over its own SVG.
  const item = createMockItem({
    placement_name: "item_8_escalate",
    _centerX: 17,
    _top: 15,
    _visualWidth: 12,
    _height: 25.408,
    _labelX: 17,
    _labelY: 20, // inside SVG bbox -> own-art overlap
    _labelLines: ["Overlapping text with lots of words"],
  });
  const scene = createMockScene();
  // The renderer collects in report mode, then escalates Guard 8 specifically.
  const violations = collectStructuralViolations([item], scene);
  assert.throws(() => enforceNoLabelOwnSvgOverlap(violations), Error);
});

test("enforceNoLabelOwnSvgOverlap does not throw on a clean scene", () => {
  // Label well clear of its own SVG -> no own-art overlap, no escalation throw.
  const item = createMockItem({
    placement_name: "item_8_clean",
    _centerX: 17,
    _top: 20,
    _visualWidth: 10,
    _height: 21.17,
    _labelX: 17,
    _labelY: 7,
    _labelLines: ["Far"],
  });
  const scene = createMockScene();
  const violations = collectStructuralViolations([item], scene);
  enforceNoLabelOwnSvgOverlap(violations);
});
