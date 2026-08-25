// Unit + fixture tests for src/scene_runtime/layout. Uses tsx loader so we
// can import the TS source directly. Run via:
//   node --import tsx --test tests/test_layout_engine.mjs
// or the npm scripts target.

import test from "node:test";
import assert from "node:assert/strict";

import {
  bindObjects,
  buildGlobalDefaults,
  clampSceneBounds,
  DEMO_ASSET_SPECS,
  DEMO_OBJECT_LIBRARY,
  groupByZone,
  horizontalLayout,
  layoutLabels as _layoutLabels,
  normalizeSchema,
  PX_PER_SCENE_PERCENT,
  resolveInheritance,
  runPipeline,
  scaleToRealWorld,
  verticalLayout,
  WORKSPACE_PX_PER_CM,
  wrapLabel,
} from "../src/scene_runtime/layout/index.ts";

const HEAT_BLOCK_BENCH = {
  scene_name: "heat_block_bench",
  workspace: "bench",
  scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
  zones: [
    {
      id: "rear_supplies",
      bounds: { left: 5, right: 95, top: 10, bottom: 35 },
      baseline: 32,
      align: "tab-stops",
    },
    {
      id: "work_surface",
      bounds: { left: 20, right: 80, top: 45, bottom: 75 },
      baseline: 72,
      align: "center",
    },
  ],
  placements: [
    {
      placement_name: "rear_left_eppendorf_rack",
      object_name: "microtube_rack_24",
      zone: "rear_supplies",
      depth_tier: 1,
      align_stop: "left",
    },
    {
      placement_name: "rear_right_protein_ladder",
      object_name: "protein_ladder_tube",
      zone: "rear_supplies",
      depth_tier: 1,
      align_stop: "right",
    },
    {
      placement_name: "center_heat_block",
      object_name: "heat_block",
      zone: "work_surface",
      depth_tier: 1,
    },
  ],
};

function runHeatBlock() {
  return runPipeline(HEAT_BLOCK_BENCH, {
    library: DEMO_OBJECT_LIBRARY,
    assets: DEMO_ASSET_SPECS,
  });
}

// ---- Stage 2 ----
test("normalizeSchema: Schema A passthrough applies layout_rules defaults", () => {
  const out = normalizeSchema({ ...HEAT_BLOCK_BENCH });
  assert.equal(out.source, "zone_bounds");
  assert.notEqual(out.scene.layout_rules.zone_gap, undefined);
  assert.notEqual(out.scene.layout_rules.label_offset_y, undefined);
});

// ---- Stage 3 ----
test("resolveInheritance: extends applies remove/deactivate/reposition/add in order", () => {
  const base = {
    scene_name: "base",
    workspace: "bench",
    scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
    zones: [],
    placements: [
      {
        placement_name: "keep",
        object_name: "heat_block",
        zone: "work_surface",
      },
      {
        placement_name: "kill",
        object_name: "media_bottle",
        zone: "work_surface",
      },
      { placement_name: "off", object_name: "waste_jar", zone: "work_surface" },
      {
        placement_name: "mover",
        object_name: "t75_flask",
        zone: "work_surface",
      },
    ],
  };
  const extender = {
    scene_name: "ext",
    workspace: "bench",
    extends: "base",
    scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
    zones: [],
    placements: [],
    remove_placements: [{ placement_name: "kill" }],
    deactivate_placements: [{ placement_name: "off" }],
    reposition_placements: [{ placement_name: "mover", zone: "tools" }],
    add_placements: [
      {
        placement_name: "new_one",
        object_name: "media_bottle",
        zone: "work_surface",
      },
    ],
  };
  const out = resolveInheritance(extender, { base });
  assert.equal(out.placements.length, 4);
  assert.equal(
    out.placements.find((p) => p.placement_name === "kill"),
    undefined,
  );
  const off = out.placements.find((p) => p.placement_name === "off");
  assert.equal(off.active, false);
  const mover = out.placements.find((p) => p.placement_name === "mover");
  assert.equal(mover.zone, "tools");
  assert.ok(out.placements.find((p) => p.placement_name === "new_one"));
});

// ---- Stage 4 ----
test("bindObjects: merges layout hints, identity fields cannot be overridden", () => {
  const diags = [];
  const bound = bindObjects(
    [{ placement_name: "p", object_name: "heat_block", zone: "z" }],
    DEMO_OBJECT_LIBRARY,
    DEMO_ASSET_SPECS,
    diags,
  );
  assert.equal(bound[0].kind, "equipment");
  assert.equal(bound[0].aspect, 1.35);
  assert.equal(bound[0].layout.display_width_cm, 25);
  assert.equal(diags.length, 0);
});

test("bindObjects: unknown_object emits diagnostic + render-error card", () => {
  const diags = [];
  const bound = bindObjects(
    [{ placement_name: "p", object_name: "ghost", zone: "z" }],
    DEMO_OBJECT_LIBRARY,
    DEMO_ASSET_SPECS,
    diags,
  );
  // Diagnostic is still recorded so the missing object is visible to tooling.
  assert.equal(diags.length, 1);
  assert.equal(diags[0].kind, "unknown_object");
  // The internal render error retains the placement for diagnostic rendering.
  assert.equal(bound[0]._error, undefined);
  assert.equal(bound[0]._render_error, "missing-object");
  // It carries a real Kind so downstream layout stages treat it normally.
  assert.equal(bound[0].kind, "decoration");
});

// ---- Stage 5 ----
test("scaleToRealWorld: cm_model formula matches SCALING_MODEL.md", () => {
  const diags = [];
  const bound = bindObjects(
    HEAT_BLOCK_BENCH.placements,
    DEMO_OBJECT_LIBRARY,
    DEMO_ASSET_SPECS,
    diags,
  );
  const scaled = scaleToRealWorld(bound, "bench", {}, diags);

  const pxPerCm = WORKSPACE_PX_PER_CM.bench;
  const rack = scaled.find((p) => p.placement_name === "rear_left_eppendorf_rack");
  const expected = (12 * pxPerCm) / (13 * PX_PER_SCENE_PERCENT);
  assert.ok(Math.abs(rack._width_scale - expected) < 0.001, `rack got ${rack._width_scale}`);
  assert.equal(rack._scale_source, "cm_model");

  const heat = scaled.find((p) => p.placement_name === "center_heat_block");
  const expectedHeat = (25 * pxPerCm) / (18 * PX_PER_SCENE_PERCENT);
  assert.ok(Math.abs(heat._width_scale - expectedHeat) < 0.001);
});

test("scaleToRealWorld: unknown workspace falls back to authored width_scale + emits diagnostic", () => {
  const diags = [];
  const bound = bindObjects(
    [{ placement_name: "p", object_name: "heat_block", zone: "z" }],
    DEMO_OBJECT_LIBRARY,
    DEMO_ASSET_SPECS,
    diags,
  );
  const scaled = scaleToRealWorld(bound, "incubator", { workspacePxPerCm: { bench: 3.2 } }, diags);
  assert.equal(scaled[0]._scale_source, "fallback_no_workspace");
  assert.ok(diags.some((d) => d.kind === "unknown_workspace"));
});

// ---- Stage 6 ----
test("groupByZone: sorts by depth_tier ASC, then placement_name", () => {
  const placements = [
    {
      placement_name: "z_high_tier",
      object_name: "heat_block",
      zone: "w",
      depth_tier: 2,
    },
    {
      placement_name: "a_low_tier",
      object_name: "heat_block",
      zone: "w",
      depth_tier: 1,
    },
    {
      placement_name: "b_low_tier",
      object_name: "heat_block",
      zone: "w",
      depth_tier: 1,
    },
  ];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const grouped = groupByZone(scaled, [
    { id: "w", bounds: { left: 0, right: 100, top: 0, bottom: 100 } },
  ]);
  const ws = grouped.groups.get("w");
  assert.equal(ws[0].placement_name, "a_low_tier");
  assert.equal(ws[1].placement_name, "b_low_tier");
  assert.equal(ws[2].placement_name, "z_high_tier");
});

test("groupByZone: unknown zone -> orphan + diagnostic", () => {
  const diags = [];
  const placements = [
    {
      placement_name: "orphan",
      object_name: "heat_block",
      zone: "missing_zone",
    },
  ];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const grouped = groupByZone(
    scaled,
    [{ id: "w", bounds: { left: 0, right: 100, top: 0, bottom: 100 } }],
    diags,
  );
  assert.equal(grouped.orphans.length, 1);
  assert.equal(diags[0].kind, "unknown_zone");
});

// ---- Stage 7 ----
test("horizontalLayout: center alignment positions a single item at zone midpoint", () => {
  const placements = [
    {
      placement_name: "p",
      object_name: "heat_block",
      zone: "w",
      depth_tier: 1,
    },
  ];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const grouped = groupByZone(scaled, [
    {
      id: "w",
      bounds: { left: 20, right: 80, top: 45, bottom: 75 },
      baseline: 72,
      align: "center",
    },
  ]);
  const layouts = horizontalLayout(grouped.groups, [
    {
      id: "w",
      bounds: { left: 20, right: 80, top: 45, bottom: 75 },
      baseline: 72,
      align: "center",
    },
  ]);
  const items = layouts.get("w");
  assert.equal(items.length, 1);
  assert.equal(items[0]._centerX, 50);
});

// ---- Stage 8: place-vertical consumes computed zone bands ----
//
// The rewritten verticalLayout(zoneLayouts, zones, zoneBands, viewport, diags,
// config) places each item's object strip inside its tier row and back-solves the
// baseline per anchor mode. These tests build a synthetic ComputedZoneBand (the
// reflow-zones output) and a measured item, then assert the object placement.

// Build a ComputedZoneBand with one tier row containing the named placements.
function makeBand(id, top, bottom, rowTop, rowHeight, placementNames) {
  return {
    id,
    top,
    bottom,
    baseline: (top + bottom) / 2,
    tiers: [{ depthTier: 0, rowTop, rowHeight, placementNames }],
  };
}

test("verticalLayout: object keeps natural height, aspect preserved (no shrink)", () => {
  const placements = [{ placement_name: "p", object_name: "heat_block", zone: "w", depth_tier: 0 }];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  bound[0].aspect = 1.0;
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const zones = [{ id: "w", bounds: { left: 20, right: 80, top: 45, bottom: 75 }, baseline: 72 }];
  const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
  const measured = horiz.get("w")[0];
  // The measured item carries the label-strip fields the place stage reads.
  measured._labelBoxHeight = 2.2;
  measured._labelPlacement = "top";
  const bands = new Map([["w", makeBand("w", 45, 75, 46, 12, ["p"])]]);
  const vert = verticalLayout(horiz, zones, bands, { w: 1920, h: 1080 });
  const item = vert.get("w")[0];
  // Natural height: visualWidth * (1920/1080) / aspect (aspect 1.0); never shrunk.
  const expected = item._visualWidth * (1920 / 1080);
  assert.ok(Math.abs(item._height - expected) < 0.001, "object keeps natural height");
  // Width is unchanged from the horizontal stage (no per-object vertical shrink).
  assert.ok(Math.abs(item._visualWidth - measured._visualWidth) < 1e-9, "width unchanged");
});

test("verticalLayout: top label rests the object bottom on the row shelf (row bottom)", () => {
  const placements = [{ placement_name: "p", object_name: "heat_block", zone: "w", depth_tier: 0 }];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const zones = [{ id: "w", bounds: { left: 20, right: 80, top: 45, bottom: 99 } }];
  const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
  const measured = horiz.get("w")[0];
  // Fix the natural height (visualWidth * 1920/1080 / aspect = 12 * 1.7778 / 2 =
  // 10.667) well below the row height so the shelf term wins.
  measured._visualWidth = 12;
  measured.aspect = 2;
  measured._labelBoxHeight = 2.2;
  measured._labelPlacement = "top";
  const rowTop = 48;
  const rowHeight = 30;
  const bands = new Map([["w", makeBand("w", 45, 99, rowTop, rowHeight, ["p"])]]);
  const vert = verticalLayout(horiz, zones, bands, { w: 1920, h: 1080 });
  const item = vert.get("w")[0];
  // Bottom-anchor: a top-label object's bottom edge sits on the row shelf, which is
  // the row bottom because a top label reserves no space below the shelf.
  assert.ok(
    Math.abs(item._top + item._height - (rowTop + rowHeight)) < 1e-9,
    "object bottom rests on the row bottom shelf",
  );
  // The object stays inside the row (its top is at or below the row top).
  assert.ok(item._top >= rowTop - 1e-9, "object top stays inside the row");
});

test("verticalLayout: bottom label rests the object bottom on the shelf above the label reserve", () => {
  const cfg = buildGlobalDefaults();
  const gap = cfg.labelOffsetY;
  const placements = [{ placement_name: "p", object_name: "heat_block", zone: "w", depth_tier: 0 }];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const zones = [{ id: "w", bounds: { left: 20, right: 80, top: 45, bottom: 99 } }];
  const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
  const measured = horiz.get("w")[0];
  measured._visualWidth = 12;
  measured.aspect = 2; // nH = 10.667, well under the row height
  const labelBox = 2.2;
  measured._labelBoxHeight = labelBox;
  measured._labelPlacement = "bottom";
  const rowTop = 48;
  const rowHeight = 30;
  const bands = new Map([["w", makeBand("w", 45, 99, rowTop, rowHeight, ["p"])]]);
  const vert = verticalLayout(horiz, zones, bands, { w: 1920, h: 1080 });
  const item = vert.get("w")[0];
  // Bottom label: the shelf is pulled UP by the label reserve (gap + label box) so
  // the label strip stays inside the row below the object bottom.
  const shelf = rowTop + rowHeight - (gap + labelBox);
  assert.ok(
    Math.abs(item._top + item._height - shelf) < 1e-9,
    "object bottom rests on the shelf above the reserved label strip",
  );
  // The reserved strip between the object bottom and the row bottom is exactly the
  // label gap plus the label box.
  const reserve = rowTop + rowHeight - (item._top + item._height);
  assert.ok(
    Math.abs(reserve - (gap + labelBox)) < 1e-9,
    "the label reserve equals gap + label box",
  );
});

test("verticalLayout: a tier row shares one baseline so unequal objects bottom-align", () => {
  // The core fix: two objects of DIFFERENT natural heights in one tier row land
  // their bottom edges on one common line (the shared shelf baseline), instead of
  // hanging from the row top.
  const placements = [
    { placement_name: "a", object_name: "heat_block", zone: "w", depth_tier: 0 },
    { placement_name: "b", object_name: "heat_block", zone: "w", depth_tier: 0 },
  ];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const zones = [{ id: "w", bounds: { left: 10, right: 90, top: 45, bottom: 99 } }];
  const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
  const items = horiz.get("w");
  // Force two different natural heights via aspect (nH = visualWidth * 1920/1080 /
  // aspect): item a is tall (aspect 1.5 -> nH 14.22), item b is short (aspect 3 ->
  // nH 7.11).
  items[0]._visualWidth = 12;
  items[0].aspect = 1.5;
  items[0]._labelBoxHeight = 2.0;
  items[0]._labelPlacement = "top";
  items[1]._visualWidth = 12;
  items[1].aspect = 3;
  items[1]._labelBoxHeight = 2.0;
  items[1]._labelPlacement = "top";
  const rowTop = 48;
  const rowHeight = 40;
  const bands = new Map([["w", makeBand("w", 45, 99, rowTop, rowHeight, ["a", "b"])]]);
  const vert = verticalLayout(horiz, zones, bands, { w: 1920, h: 1080 });
  const a = vert.get("w").find((it) => it.placement_name === "a");
  const b = vert.get("w").find((it) => it.placement_name === "b");
  // The two objects have genuinely different heights (the scene the fix targets).
  assert.ok(Math.abs(a._height - b._height) > 1, "the two objects differ in height");
  // Their bottom edges land on one common line.
  assert.ok(
    Math.abs(a._top + a._height - (b._top + b._height)) < 1e-9,
    "unequal-height objects share one bottom shelf line",
  );
  // They share one baseline (the shelf), and a bottom-anchored object's bottom sits
  // on it.
  assert.ok(Math.abs(a._baselineY - b._baselineY) < 1e-9, "the row shares one baseline");
  assert.ok(
    Math.abs(a._top + a._height - a._baselineY) < 1e-9,
    "a bottom-anchored object's bottom sits on the baseline",
  );
});

test("verticalLayout: tip offset 0 bottoms on the shelf; tip offset and center shift predictably", () => {
  // With the shared baseline, anchor_y maps the baseline to the object edge: bottom
  // and tip(offset 0) put the bottom on the baseline; a positive tip offset hangs
  // the tip below it; center (anchor_y "top") puts the object center on it.
  const rowTop = 50;
  const rowHeight = 40;
  function placeWithAnchor(anchor, anchorOffset = 0) {
    const placements = [
      { placement_name: "p", object_name: "heat_block", zone: "w", depth_tier: 0 },
    ];
    const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
    const scaled = scaleToRealWorld(bound, "bench", {}, []);
    scaled[0].layout.anchor_y = anchor;
    scaled[0].layout.anchor_y_offset = anchorOffset;
    const zones = [{ id: "w", bounds: { left: 20, right: 80, top: 45, bottom: 99 } }];
    const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
    const measured = horiz.get("w")[0];
    measured._visualWidth = 12;
    measured.aspect = 2; // nH = 10.667 < rowHeight, so the shelf term wins
    measured._labelBoxHeight = 2.2;
    measured._labelPlacement = "top";
    const bands = new Map([["w", makeBand("w", 45, 99, rowTop, rowHeight, ["p"])]]);
    const vert = verticalLayout(horiz, zones, bands, { w: 1920, h: 1080 });
    return vert.get("w")[0];
  }
  // Top-label single item: the shelf is the row bottom.
  const shelf = rowTop + rowHeight;
  const bot = placeWithAnchor("bottom");
  assert.ok(Math.abs(bot._top + bot._height - shelf) < 1e-9, "bottom anchor sits on the shelf");
  const tip0 = placeWithAnchor("tip", 0);
  assert.ok(Math.abs(tip0._top + tip0._height - shelf) < 1e-9, "tip offset 0 sits on the shelf");
  const tip3 = placeWithAnchor("tip", 3);
  assert.ok(
    Math.abs(tip3._top + tip3._height - (shelf + 3)) < 1e-9,
    "a positive tip offset hangs the tip below the shelf",
  );
  const cen = placeWithAnchor("top");
  assert.ok(
    Math.abs(cen._top + cen._height / 2 - shelf) < 1e-9,
    "center anchor puts the object center on the shelf",
  );
});

test("verticalLayout: missing band falls back to the zone top and flags the item", () => {
  // A direct call with no band for the zone must still place the object (at the
  // zone top) AND emit an item_escapes_zone_vertically diagnostic, not crash.
  const placements = [{ placement_name: "p", object_name: "heat_block", zone: "w", depth_tier: 0 }];
  const bound = bindObjects(placements, DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS, []);
  const scaled = scaleToRealWorld(bound, "bench", {}, []);
  const zones = [{ id: "w", bounds: { left: 20, right: 80, top: 45, bottom: 75 } }];
  const horiz = horizontalLayout(groupByZone(scaled, zones).groups, zones);
  const measured = horiz.get("w")[0];
  measured._labelBoxHeight = 2.2;
  measured._labelPlacement = "bottom";
  const diags = [];
  const vert = verticalLayout(horiz, zones, new Map(), { w: 1920, h: 1080 }, diags);
  const item = vert.get("w")[0];
  assert.ok(Math.abs(item._top - 45) < 1e-9, "object falls back to the zone top");
  const escape = diags.find((d) => d.kind === "item_escapes_zone_vertically");
  assert.ok(escape !== undefined, "missing band flags item_escapes_zone_vertically");
});

// ---- Stage 9 ----
test("layoutLabels: short labels emit one line", () => {
  assert.deepEqual(wrapLabel("Hi", 10), ["Hi"]);
});

test("layoutLabels: long labels wrap at nearest space to middle", () => {
  const lines = wrapLabel("a very long heat block label", 5);
  assert.equal(lines.length, 2);
});

// ---- layoutLabels seed geometry (label_placement top | bottom) ----
//
// Build a minimal ComputedItem carrying just the fields layoutLabels reads at
// seed time: artwork box (_centerX/_top/_visualWidth/_height), the row baseline
// (_baselineY), and the resolved layout hint (label_width + optional
// label_placement). A roomy single-item zone keeps the horizontal nudge and the
// vertical stagger no-ops so the seeded _labelY is observable directly.
function seedItem(name, opts) {
  return {
    placement_name: name,
    object_name: name,
    label: opts.label ?? name,
    zone: "z",
    _centerX: opts.centerX ?? 50,
    _baselineY: opts.baselineY ?? 60,
    _top: opts.top ?? 40,
    _visualWidth: opts.visualWidth ?? 10,
    _height: opts.height ?? 20,
    _footprint: opts.visualWidth ?? 10,
    _scale: 1,
    _width_scale: 1,
    depth_tier: opts.depthTier ?? 0,
    layout: {
      default_width: opts.visualWidth ?? 10,
      label_width: opts.labelWidth ?? 8,
      anchor_y: "bottom",
      anchor_y_offset: 0,
      ...(opts.placement !== undefined ? { label_placement: opts.placement } : {}),
    },
  };
}

const SEED_ZONE = { id: "z", bounds: { left: 0, right: 100, top: 0, bottom: 100 } };

function runSeed(items, layoutRules = {}) {
  const map = new Map([["z", items]]);
  const out = _layoutLabels(map, [SEED_ZONE], layoutRules, []);
  return out.get("z");
}

test("layoutLabels: top placement (default) seeds a 1-line label above the object", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  const it = seedItem("vortex", { label: "Vortex", top: 40, baselineY: 60 });
  const [out] = runSeed([it]); // default placement is top
  assert.equal(out._labelLines.length, 1, "single short label is one line");
  // top seed: _labelY (label TOP edge) = _top - offset - lineH * lineCount.
  const expected = 40 - offset - lineH * 1;
  assert.ok(Math.abs(out._labelY - expected) < 1e-9, `top 1-line: ${out._labelY} vs ${expected}`);
  // The label bottom edge sits offset above the object top (gap == labelOffsetY).
  const labelBottom = out._labelY + lineH * out._labelLines.length;
  assert.ok(Math.abs(40 - labelBottom - offset) < 1e-9, "gap from label bottom to object top");
});

test("layoutLabels: top placement seeds a 2-line label above the object", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // A label whose wrapped form is two lines under the budget.
  const it = seedItem("longlabel", {
    label: "a very long heat block label",
    labelWidth: 5,
    top: 40,
  });
  const [out] = runSeed([it]);
  assert.equal(out._labelLines.length, 2, "label wraps to two lines");
  const expected = 40 - offset - lineH * 2;
  assert.ok(Math.abs(out._labelY - expected) < 1e-9, `top 2-line: ${out._labelY} vs ${expected}`);
});

test("layoutLabels: scene-wide bottom reproduces the legacy below-baseline seed", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const it = seedItem("flask", { label: "Flask", baselineY: 60 });
  const [out] = runSeed([it], { label_placement: "bottom" });
  // legacy bottom seed: _labelY = _baselineY + labelOffsetY.
  const expected = 60 + offset;
  assert.ok(Math.abs(out._labelY - expected) < 1e-9, `bottom seed: ${out._labelY} vs ${expected}`);
});

test("layoutLabels: per-placement override wins over scene rule and default", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // Scene rule says bottom; one placement overrides to top, the other inherits.
  const topItem = seedItem("a_top", { label: "A", centerX: 25, top: 40, placement: "top" });
  const botItem = seedItem("b_bottom", { label: "B", centerX: 75, baselineY: 60 });
  const out = runSeed([topItem, botItem], { label_placement: "bottom" });
  const a = out.find((o) => o.placement_name === "a_top");
  const b = out.find((o) => o.placement_name === "b_bottom");
  const expectedTop = 40 - offset - lineH * 1;
  const expectedBottom = 60 + offset;
  assert.ok(
    Math.abs(a._labelY - expectedTop) < 1e-9,
    `override top: ${a._labelY} vs ${expectedTop}`,
  );
  assert.ok(
    Math.abs(b._labelY - expectedBottom) < 1e-9,
    `inherited bottom: ${b._labelY} vs ${expectedBottom}`,
  );
});

// ---- layoutLabels computed-band clamp + terminal flip ----
//
// After the reflow, the vertical label clamp and the terminal safety flip read
// the COMPUTED band (reflow-zones output) instead of the authored zone bounds.
// These tests pass an explicit zoneBands map whose band edges DIFFER from the
// authored SEED_ZONE bounds, then assert the clamp honors the band edges and the
// flip stays inside the band's reserved row.

// Run layoutLabels with an explicit computed band for the seed zone. The band id
// matches the zone id; its edges are deliberately narrower than the authored
// SEED_ZONE [0, 100] so a clamp against the band is observable.
function runSeedWithBand(items, band, layoutRules = {}) {
  const map = new Map([["z", items]]);
  const bands = new Map([["z", band]]);
  const out = _layoutLabels(map, [SEED_ZONE], layoutRules, [], buildGlobalDefaults(), bands);
  return out.get("z");
}

test("layoutLabels: vertical clamp uses the computed band, not the authored zone", () => {
  const cfg = buildGlobalDefaults();
  const pad = cfg.spacing.labelZonePadding;
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // A small object near the top of a computed band whose floor (50) is far above
  // the authored zone floor (100). Its bottom label seeds labelOffsetY below the
  // object bottom; the seed lands inside the band so the side stays bottom (no
  // flip), and the clamp's job is only to hold the label inside the band. The
  // observable proof: the padded BAND floor (50 - pad) bounds the label, whereas a
  // clamp against the authored zone would only bound it at the padded AUTHORED
  // floor (100 - pad), ~50 units lower.
  const it = seedItem("deep", {
    label: "Deep",
    centerX: 50,
    top: 22,
    height: 4,
    baselineY: 26,
    placement: "bottom",
  });
  // Computed band [10, 50]; object bottom (26) leaves ample room below for the
  // bottom label inside the band, so the side stays bottom.
  const band = {
    id: "z",
    top: 10,
    bottom: 50,
    baseline: 30,
    tiers: [{ depthTier: 0, rowTop: 20, rowHeight: 28, placementNames: ["deep"] }],
  };
  const [out] = runSeedWithBand([it], band);
  // The side stayed bottom (the seed had room inside the band, no flip needed).
  assert.equal(out.layout.label_placement ?? "top", "bottom", "bottom side has room, no flip");
  const labelHeight = lineH * out._labelLines.length;
  const labelBottom = out._labelY + labelHeight;
  // The label's bottom edge stays at or above the padded BAND floor (50 - pad). A
  // clamp against the authored zone (floor 100) would permit a label bottom up to
  // ~98.5; the band clamp bounds it at ~48.5, proving the clamp reads the band.
  const paddedBandFloor = band.bottom - pad;
  const paddedAuthoredFloor = SEED_ZONE.bounds.bottom - pad;
  assert.ok(
    labelBottom <= paddedBandFloor + 1e-6,
    `label bottom ${labelBottom} clamped to band floor ${paddedBandFloor}`,
  );
  assert.ok(
    paddedBandFloor < paddedAuthoredFloor - 1,
    "band floor is well above the authored floor (the clamp difference is observable)",
  );
  // The ideal bottom seed (object bottom + offset) sits inside the band, so the
  // label lands at its seed and well within the band floor.
  const seedBottom = it._top + it._height + offset + labelHeight;
  assert.ok(
    labelBottom <= seedBottom + 1e-6,
    "label is not pushed below its ideal seed by the band clamp",
  );
});

test("layoutLabels: terminal flip stays inside the measured row extent", () => {
  const cfg = buildGlobalDefaults();
  const lineH = cfg.labelLineHeightPct;
  // A TALL object placed at the band top so the AUTHORED bottom side has no room
  // (the object's bottom is at the band floor): the bottom candidate would exit
  // the band, while the top side clears. The terminal flip must choose top and the
  // flipped label must stay inside the reserved row [bandTop, bandBottom].
  const bandTop = 20;
  const bandBottom = 50;
  const objectTop = 31; // leaves a top strip (top side has room), bottom is full
  const objectHeight = 18; // object bottom 49, just above the band floor 50
  const it = seedItem("tall", {
    label: "Tall",
    centerX: 50,
    top: objectTop,
    height: objectHeight,
    baselineY: objectTop + objectHeight,
    placement: "bottom", // authored side is bottom; the flip should pick top
  });
  const band = {
    id: "z",
    top: bandTop,
    bottom: bandBottom,
    baseline: (bandTop + bandBottom) / 2,
    tiers: [
      { depthTier: 0, rowTop: bandTop, rowHeight: bandBottom - bandTop, placementNames: ["tall"] },
    ],
  };
  const [out] = runSeedWithBand([it], band);
  // The flip resolved the side to top (carried forward on the layout object).
  assert.equal(out.layout.label_placement, "top", "authored bottom flips to top (no room below)");
  const labelHeight = lineH * out._labelLines.length;
  const labelBottom = out._labelY + labelHeight;
  // The flipped top label clears its own art: its bottom edge sits at or above the
  // object top.
  assert.ok(
    labelBottom <= objectTop + 1e-6,
    `flipped top label clears own art: bottom ${labelBottom} <= object top ${objectTop}`,
  );
  // It stays inside the measured row extent (the band the reflow reserved).
  assert.ok(out._labelY >= bandTop - 1e-6, `label top ${out._labelY} inside band top ${bandTop}`);
  assert.ok(labelBottom <= bandBottom + 1e-6, "label bottom inside the band floor");
});

// ---- layoutLabels direction-aware stagger (per-zone, per-group ladder) ----
//
// The seed helpers above (seedItem / runSeed / SEED_ZONE) feed these too. Two
// items sharing a centerX seed both labels at the same _labelX; a wide label
// budget (labelWidth 60, half-width 30) is wider than the zone can relieve
// horizontally, so the pre-stagger nudge cannot separate them and the loser is
// forced onto row 1. Single-line labels keep naturalStep == lineHeightPct and a
// roomy vertical band keeps the step uncompressed, so expected ladder Ys are
// exact. WIDE_LABEL is the budget that reliably overflows the SEED_ZONE width.
const WIDE_LABEL = 60;

test("layoutLabels: vertically separate depth tiers do not share a stagger ladder", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // These labels deliberately share x and side, but their object tiers are
  // vertically separate. Treating them as one horizontal interval graph would
  // move the lower label upward into the upper tier's artwork.
  const upper = seedItem("upper", {
    label: "Upper",
    centerX: 50,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
    depthTier: 0,
  });
  const lower = seedItem("lower", {
    label: "Lower",
    centerX: 50,
    top: 60,
    labelWidth: WIDE_LABEL,
    placement: "top",
    depthTier: 1,
  });
  const diags = [];
  const out = _layoutLabels(new Map([["z", [upper, lower]]]), [SEED_ZONE], {}, diags).get("z");
  const byName = new Map(out.map((item) => [item.placement_name, item]));
  assert.equal(byName.get("upper")._labelY, 40 - offset - lineH);
  assert.equal(byName.get("lower")._labelY, 60 - offset - lineH);
  assert.equal(
    diags.some((diagnostic) => diagnostic.kind === "label_row_staggered"),
    false,
    "already-clear tiers emit no invented stagger diagnostic",
  );
});

test("layoutLabels: same-tier horizontal overlap still receives distinct stagger rows", () => {
  const a = seedItem("a", {
    label: "A",
    centerX: 50,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
    depthTier: 1,
  });
  const b = seedItem("b", {
    label: "B",
    centerX: 50,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
    depthTier: 1,
  });
  const diags = [];
  const out = _layoutLabels(new Map([["z", [a, b]]]), [SEED_ZONE], {}, diags).get("z");
  assert.notEqual(out[0]._labelY, out[1]._labelY, "same-tier overlap uses separate rows");
  assert.equal(
    diags.some((diagnostic) => diagnostic.kind === "label_row_staggered"),
    true,
    "same-tier overlap retains the existing stagger behavior",
  );
});

test("layoutLabels: colliding top labels stagger UPWARD (rows above the seed)", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // Both top labels at the same centerX with wide budgets -> forced overlap.
  const a = seedItem("a", {
    label: "A",
    centerX: 50,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
  });
  const b = seedItem("b", {
    label: "B",
    centerX: 50,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
  });
  const out = runSeed([a, b]); // default placement is top
  const ys = out.map((o) => o._labelY).sort((x, y) => x - y);
  // Row-0 baseline (the seed): _top - offset - lineH * 1.
  const baseline = 40 - offset - lineH * 1;
  // One label keeps the baseline; the other ladders UP by exactly one lineH.
  const rowOne = baseline - lineH * 1;
  assert.ok(Math.abs(ys[1] - baseline) < 1e-9, `row0 ${ys[1]} vs baseline ${baseline}`);
  assert.ok(Math.abs(ys[0] - rowOne) < 1e-9, `row1 (up) ${ys[0]} vs ${rowOne}`);
  // Upward means the staggered label sits ABOVE (smaller Y) the row-0 label.
  assert.ok(ys[0] < ys[1], "top stagger moves a label upward, not down");
});

test("layoutLabels: colliding bottom labels stagger DOWNWARD (legacy direction)", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  const a = seedItem("a", { label: "A", centerX: 50, baselineY: 60, labelWidth: WIDE_LABEL });
  const b = seedItem("b", { label: "B", centerX: 50, baselineY: 60, labelWidth: WIDE_LABEL });
  const out = runSeed([a, b], { label_placement: "bottom" });
  const ys = out.map((o) => o._labelY).sort((x, y) => x - y);
  const baseline = 60 + offset; // legacy bottom seed
  const rowOne = baseline + lineH * 1;
  assert.ok(Math.abs(ys[0] - baseline) < 1e-9, `row0 ${ys[0]} vs baseline ${baseline}`);
  assert.ok(Math.abs(ys[1] - rowOne) < 1e-9, `row1 (down) ${ys[1]} vs ${rowOne}`);
  assert.ok(ys[1] > ys[0], "bottom stagger moves a label downward, not up");
});

test("layoutLabels: top ladder clamps the TOP edge at the padded zone top", () => {
  // A rear zone with a high top (top=5) and several colliding top labels whose
  // natural upward ladder would escape above the zone top. The clamp must hold
  // the deepest row's TOP edge (_labelY) at or below zone.top + padding, so no
  // label escapes the scene root (Playwright assertion G containment risk).
  const cfg = buildGlobalDefaults();
  const pad = cfg.spacing.labelZonePadding;
  const REAR_ZONE = { id: "z", bounds: { left: 0, right: 100, top: 5, bottom: 95 } };
  // Five labels stacked at one centerX force rows 0..4. Their row-0 seed sits
  // inside the zone (top=20 -> baseline 14.3), but the natural upward ladder
  // (4 * lineHeight) would escape above the zone top, so the step must compress.
  const items = [];
  for (let i = 0; i < 5; i++) {
    items.push(
      seedItem("t" + i, {
        label: "T" + i,
        centerX: 50,
        top: 20,
        labelWidth: WIDE_LABEL,
        placement: "top",
      }),
    );
  }
  const map = new Map([["z", items]]);
  const out = _layoutLabels(map, [REAR_ZONE], {}, []);
  const labels = out.get("z");
  const topClamp = 5 + pad;
  for (const o of labels) {
    // _labelY is the label TOP edge; it must never rise above the padded zone top.
    assert.ok(
      o._labelY >= topClamp - 1e-6,
      `${o.placement_name} top ${o._labelY} must stay >= clamp ${topClamp}`,
    );
  }
  // The deepest row should sit at (or compressed onto) the clamp line, distinct
  // from the row-0 baseline -- the ladder did not collapse every row onto it.
  const ys = labels.map((o) => o._labelY).sort((x, y) => x - y);
  assert.ok(Math.abs(ys[0] - topClamp) < 1e-6, `deepest row ${ys[0]} sits on clamp ${topClamp}`);
  const distinct = new Set(ys.map((y) => y.toFixed(4)));
  assert.equal(distinct.size, ys.length, "every laddered row stays at a distinct Y");
});

test("layoutLabels: a rear-zone top label with no room above falls back to bottom", () => {
  // Rear-zone clamp-onto-cap fix: a rear-zone object (zone top=5) whose own top
  // sits near the scene top leaves no vertical room for a top label between the
  // padded zone top and the object's own visual top. The old seed-level top-clamp
  // raised such a label DOWN to zone.top + padding, where its BOTTOM edge crossed
  // below the object top and overprinted its own art. The fixed engine detects the
  // no-room-above case and falls back to BOTTOM placement (seed below the object)
  // rather than clamping the label onto the cap.
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  const pad = cfg.spacing.labelZonePadding;
  const REAR_ZONE = { id: "z", bounds: { left: 0, right: 100, top: 5, bottom: 95 } };
  // Object top=6, baseline=60: with topClamp=6.5 and labelHeight=lineH, the top
  // ceiling (6 - lineH = 3.8) is above the padded zone top (6.5), so there is no
  // room for a top label above the object.
  const it = seedItem("rear", {
    label: "Rear",
    centerX: 50,
    top: 6,
    baselineY: 60,
    placement: "top",
  });
  const map = new Map([["z", [it]]]);
  const out = _layoutLabels(map, [REAR_ZONE], {}, []);
  const [o] = out.get("z");
  const topClamp = 5 + pad;
  const ceiling = 6 - lineH * 1; // highest top-label Y whose bottom clears the object
  assert.ok(ceiling < topClamp, "test geometry: no room above the object for a top label");
  // The label must NOT overprint its own art. The seed logic places the bottom label below
  // the object's ART bottom (_top + _height = 6 + 20 = 26), not below _baselineY,
  // so the clearance check uses the art bottom.
  const objectBottom = 6 + 20;
  const labelBottom = o._labelY + lineH * o._labelLines.length;
  assert.ok(
    labelBottom <= 6 + 1e-9 || o._labelY >= objectBottom - 1e-9,
    `rear label bottom ${labelBottom} must clear object top 6 OR flip below art bottom`,
  );
  // Concretely: the engine flips to the bottom seed below the art (artBottom +
  // offset = 29.5).
  const bottomSeed = objectBottom + offset;
  assert.ok(
    Math.abs(o._labelY - bottomSeed) < 1e-9,
    `rear label flipped to bottom seed ${o._labelY} vs ${bottomSeed}`,
  );
});

test("layoutLabels: a rear-zone TALL top label clamped into its own art flips to bottom", () => {
  // The named recycle_buffer defect: a tall rear-zone bottle (zone top=5, object
  // top ~10) with a 2-line top label. The 2-line ideal seed escapes above the zone
  // top, the old top-clamp pushed it to 6.5, and the label span [6.5, 10.9]
  // crossed the bottle visual top (9.946) -- overprinting the cap. The fix flips
  // such a label to bottom placement so it no longer overlaps its own art.
  const cfg = buildGlobalDefaults();
  const lineH = cfg.labelLineHeightPct;
  const pad = cfg.spacing.labelZonePadding;
  const REAR_ZONE = { id: "z", bounds: { left: 0, right: 100, top: 5, bottom: 95 } };
  // 2-line label (forced via a narrow budget) over a tall object whose top=9.946,
  // mirroring the recycle_buffer_bottle geometry.
  const it = seedItem("recycle_bottle", {
    label: "Buffer recycle bottle",
    labelWidth: 8,
    centerX: 25.887,
    top: 9.946,
    baselineY: 32,
    height: 22.054,
    placement: "top",
  });
  const map = new Map([["z", [it]]]);
  const out = _layoutLabels(map, [REAR_ZONE], {}, []);
  const [o] = out.get("z");
  assert.equal(o._labelLines.length, 2, "the recycle label wraps to two lines");
  const topClamp = 5 + pad;
  const labelHeight = lineH * o._labelLines.length;
  const ceiling = 9.946 - labelHeight; // highest top-label Y clearing the object top
  assert.ok(
    ceiling < topClamp,
    "test geometry: no room above the tall object for a 2-line top label",
  );
  const labelBottom = o._labelY + labelHeight;
  // Either the label bottom clears the object top, or the label flipped below it.
  assert.ok(
    labelBottom <= 9.946 + 1e-9 || o._labelY >= 32 - 1e-9,
    `tall rear label bottom ${labelBottom} must clear object top 9.946 OR flip below baseline`,
  );
});

test("layoutLabels: a clean (non-colliding) scene keeps every label on row 0", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // Three top labels spread far apart so no pair overlaps horizontally.
  const a = seedItem("a", { label: "A", centerX: 10, top: 40, placement: "top" });
  const b = seedItem("b", { label: "B", centerX: 50, top: 40, placement: "top" });
  const c = seedItem("c", { label: "C", centerX: 90, top: 40, placement: "top" });
  const diags = [];
  const map = new Map([["z", [a, b, c]]]);
  const out = _layoutLabels(map, [SEED_ZONE], {}, diags);
  const labels = out.get("z");
  const baseline = 40 - offset - lineH * 1;
  for (const o of labels) {
    assert.ok(Math.abs(o._labelY - baseline) < 1e-9, `${o.placement_name} on row 0 baseline`);
  }
  // No stagger means no label_row_staggered diagnostics emitted.
  const staggered = diags.filter((d) => d.kind === "label_row_staggered");
  assert.equal(staggered.length, 0, "clean scene emits no stagger diagnostics");
});

test("layoutLabels: mixed top/bottom zone staggers each group independently", () => {
  const cfg = buildGlobalDefaults();
  const offset = cfg.labelOffsetY;
  const lineH = cfg.labelLineHeightPct;
  // Two top labels collide (same centerX) and two bottom labels collide (same
  // centerX, different column). The groups are vertically disjoint, so the top
  // pair ladders UP and the bottom pair ladders DOWN without affecting each other.
  const t1 = seedItem("t1", {
    label: "T1",
    centerX: 30,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
  });
  const t2 = seedItem("t2", {
    label: "T2",
    centerX: 30,
    top: 40,
    labelWidth: WIDE_LABEL,
    placement: "top",
  });
  const b1 = seedItem("b1", {
    label: "B1",
    centerX: 70,
    baselineY: 60,
    labelWidth: WIDE_LABEL,
    placement: "bottom",
  });
  const b2 = seedItem("b2", {
    label: "B2",
    centerX: 70,
    baselineY: 60,
    labelWidth: WIDE_LABEL,
    placement: "bottom",
  });
  const out = runSeed([t1, t2, b1, b2]);
  const topYs = out
    .filter((o) => o.placement_name.startsWith("t"))
    .map((o) => o._labelY)
    .sort((x, y) => x - y);
  const botYs = out
    .filter((o) => o.placement_name.startsWith("b"))
    .map((o) => o._labelY)
    .sort((x, y) => x - y);
  const topBaseline = 40 - offset - lineH * 1;
  const botBaseline = 60 + offset;
  // Top group: row0 at baseline, row1 ABOVE it.
  assert.ok(Math.abs(topYs[1] - topBaseline) < 1e-9, "top row0 at top baseline");
  assert.ok(Math.abs(topYs[0] - (topBaseline - lineH)) < 1e-9, "top row1 above baseline");
  // Bottom group: row0 at baseline, row1 BELOW it -- unaffected by the top group.
  assert.ok(Math.abs(botYs[0] - botBaseline) < 1e-9, "bottom row0 at bottom baseline");
  assert.ok(Math.abs(botYs[1] - (botBaseline + lineH)) < 1e-9, "bottom row1 below baseline");
  // The two groups never cross: every top label stays above every bottom label.
  assert.ok(topYs[1] < botYs[0], "top group stays entirely above bottom group");
});

// ---- Stage 10 / validate (report-only bounds validation) ----
test("clampSceneBounds: report-only - measures overflow, never shifts positions", () => {
  const items = [
    {
      placement_name: "p",
      object_name: "heat_block",
      zone: "w",
      depth_tier: 1,
      _centerX: 95,
      _baselineY: 50,
      _top: 40,
      _height: 20,
      _visualWidth: 20,
      _footprint: 20,
      _scale: 1,
      _labelX: 95,
      _labelY: 55,
      _labelLines: ["x"],
      _width_scale: 1,
      _scale_source: "cm_model",
      _px_per_cm: 3.2,
      active: true,
      aspect: 1.35,
      kind: "equipment",
      asset: "heat_block",
      capabilities: [],
      label: "x",
      layout: {
        default_width: 18,
        label_width: 12,
        anchor_y: "bottom",
        anchor_y_offset: 0,
        width_scale: 1,
        fudge: 1,
      },
    },
  ];
  const diags = [];
  const overflows = [];
  const zones = [{ id: "w", bounds: { left: 0, right: 100, top: 0, bottom: 100 } }];
  // Item right edge = 95 + 20/2 = 105, past scene_bounds.right (99) by 6.
  const out = clampSceneBounds(
    new Map([["w", items]]),
    zones,
    { left: 1, right: 99, top: 5, bottom: 95 },
    diags,
    overflows,
    "fixture_scene",
  );
  const result = out.get("w")[0];
  // Report-only: position is unchanged (no shift), no _clamped mutation.
  assert.equal(result._centerX, 95);
  assert.equal(result._clamped, undefined);
  // A measurement diagnostic still records the overshoot for existing tooling.
  assert.equal(diags[0].kind, "zone_clamped_to_bounds");
  assert.ok(diags[0].dx > 0);
  // A structured, fixable unresolved_overlap Error is recorded for the zone.
  assert.equal(overflows.length, 1);
  const err = overflows[0].diagnostic;
  assert.equal(err.code, "unresolved_overlap");
  assert.equal(err.severity, "Error");
  assert.equal(err.failBuild, true);
  assert.equal(err.pointer.scene_name, "fixture_scene");
  assert.equal(err.pointer.zone_name, "w");
  assert.ok(err.payload.involvedItems.includes("p"));
  assert.ok(err.payload.remainingOverlapDepth > 0);
});

test("clampSceneBounds: item inside bounds records no overflow", () => {
  const items = [
    {
      placement_name: "p",
      object_name: "heat_block",
      zone: "w",
      _centerX: 50,
      _baselineY: 50,
      _top: 40,
      _height: 20,
      _visualWidth: 20,
      _footprint: 20,
      _scale: 1,
      _labelX: 50,
      _labelY: 55,
      _labelLines: ["x"],
      _width_scale: 1,
      _scale_source: "cm_model",
      _px_per_cm: 3.2,
      active: true,
      aspect: 1.35,
      kind: "equipment",
      asset: "heat_block",
      capabilities: [],
      label: "x",
      layout: {
        default_width: 18,
        label_width: 12,
        anchor_y: "bottom",
        anchor_y_offset: 0,
      },
    },
  ];
  const diags = [];
  const overflows = [];
  const zones = [{ id: "w", bounds: { left: 0, right: 100, top: 0, bottom: 100 } }];
  clampSceneBounds(
    new Map([["w", items]]),
    zones,
    { left: 1, right: 99, top: 5, bottom: 95 },
    diags,
    overflows,
    "ok_scene",
  );
  assert.equal(diags.length, 0);
  assert.equal(overflows.length, 0);
});

// ---- runPipeline + convergence loop ----
test("runPipeline: heat_block_bench fixture converges in 1 pass, no diagnostics", () => {
  const result = runHeatBlock();
  assert.equal(result.diagnostics.length, 0);
  assert.equal(result.passes[0].zones_shrunk.length, 0);
});

test("runPipeline: _width_scale fixture values match spec section 7", () => {
  const result = runHeatBlock();
  const byName = new Map(result.stages.scaled.map((p) => [p.placement_name, p]));
  const pxPerCm = WORKSPACE_PX_PER_CM.bench;
  const rack = byName.get("rear_left_eppendorf_rack");
  const heat = byName.get("center_heat_block");
  const ladder = byName.get("rear_right_protein_ladder");
  assert.ok(Math.abs(rack._width_scale - (12 * pxPerCm) / (13 * PX_PER_SCENE_PERCENT)) < 0.001);
  assert.ok(Math.abs(heat._width_scale - (25 * pxPerCm) / (18 * PX_PER_SCENE_PERCENT)) < 0.001);
  assert.ok(Math.abs(ladder._width_scale - (3 * pxPerCm) / (4 * PX_PER_SCENE_PERCENT)) < 0.001);
});

test("runPipeline: heat_block fixture _centerX and _height match Stage 7/8 math", () => {
  const result = runHeatBlock();
  const heat = result.final.find((p) => p.placement_name === "center_heat_block");
  assert.ok(Math.abs(heat._centerX - 50) < 0.1, `heat_block centered at _centerX=${heat._centerX}`);
  const expectedHeight = (heat._visualWidth * (1920 / 1080)) / heat.aspect;
  assert.ok(Math.abs(heat._height - expectedHeight) < 0.001);
});

test("runPipeline: convergence loop shrinks _width_scale on overflow", () => {
  // Cram 7 same-tier instances of a wide item into one narrow horizontal row.
  const overflowScene = {
    scene_name: "overflow",
    workspace: "bench",
    scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
    zones: [
      {
        id: "tight",
        bounds: { left: 40, right: 60, top: 45, bottom: 75 },
        baseline: 72,
        align: "center",
      },
    ],
    placements: Array.from({ length: 7 }, (_, i) => ({
      placement_name: `p${i}`,
      object_name: "heat_block",
      zone: "tight",
      depth_tier: 1,
    })),
  };
  const result = runPipeline(overflowScene, {
    library: DEMO_OBJECT_LIBRARY,
    assets: DEMO_ASSET_SPECS,
  });
  const shrunkSomewhere = result.passes.some((p) => p.zones_shrunk.includes("tight"));
  assert.ok(shrunkSomewhere, "same-tier horizontal overflow should trigger convergence shrink");
  // Every placement in the overfull zone shares the zone-level shrink.
  const cmDerived = (25 * WORKSPACE_PX_PER_CM.bench) / (18 * PX_PER_SCENE_PERCENT);
  assert.ok(
    result.stages.scaled.every((p) => p._width_scale < cmDerived),
    "convergence shrink should reduce every overfull-zone width scale",
  );
});

test("runPipeline: clean scene reports passes.length === 1 with zones_shrunk empty", () => {
  const result = runHeatBlock();
  assert.deepEqual(result.passes[0].zones_shrunk, []);
});

test("runPipeline: identityDiagCount excludes placement-stage diagnostics", () => {
  const result = runHeatBlock();
  assert.equal(result.identityDiagCount, 0);
});

// ---- Stage 7 packer ----
// A deliberately overloaded single-row zone: a narrow zone packed with an
// equipment primary plus several lower-priority fillers whose scale-1 footprints
// overflow. The packer must engage, fit with no negative gap, preserve the
// primary's scale, and lay items out left-to-right without overlap.
const OVERLOADED_BENCH = {
  scene_name: "overloaded_bench",
  workspace: "bench",
  scene_bounds: { left: 1, right: 99, top: 5, bottom: 95 },
  zones: [
    {
      id: "packed_row",
      // Narrow zone so the row of items cannot fit at scale 1.
      bounds: { left: 20, right: 60, top: 45, bottom: 85 },
      baseline: 80,
      align: "left",
    },
  ],
  placements: [
    // The primary teaching object (equipment kind, highest shrink priority).
    {
      placement_name: "p_heat_block",
      object_name: "heat_block",
      zone: "packed_row",
      depth_tier: 1,
    },
    // Lower-priority fillers that should shrink first.
    {
      placement_name: "f_rack_a",
      object_name: "microtube_rack_24",
      zone: "packed_row",
      depth_tier: 1,
    },
    {
      placement_name: "f_rack_b",
      object_name: "microtube_rack_24",
      zone: "packed_row",
      depth_tier: 1,
    },
    { placement_name: "f_waste", object_name: "waste_jar", zone: "packed_row", depth_tier: 1 },
  ],
};

test("packer: overloaded zone packs with no negative gap, primary keeps scale", () => {
  const result = runPipeline(OVERLOADED_BENCH, {
    library: DEMO_OBJECT_LIBRARY,
    assets: DEMO_ASSET_SPECS,
  });

  // The dispatcher must have selected the packer for the overloaded zone.
  const zoneDecision = result.decisionMetadata.zones.find((z) => z.zoneId === "packed_row");
  assert.ok(zoneDecision, "expected a decision for packed_row");
  assert.equal(zoneDecision.selectedStrategy, "pack");
  assert.equal(zoneDecision.packerAttempted, true);
  assert.equal(zoneDecision.packerResult, "fit");

  // The packed items, in input order.
  const items = result.stages.horizontal.get("packed_row");
  assert.equal(items.length, 4);

  // No negative gap: adjacent footprints must not overlap (left edge of item i+1
  // is at or past the right edge of item i).
  const ordered = [...items].sort((a, b) => a._centerX - b._centerX);
  for (let i = 0; i < ordered.length - 1; i++) {
    const rightEdge = ordered[i]._centerX + ordered[i]._footprint / 2;
    const leftEdgeNext = ordered[i + 1]._centerX - ordered[i + 1]._footprint / 2;
    assert.ok(
      leftEdgeNext >= rightEdge - 1e-6,
      `negative gap between ${ordered[i].placement_name} and ${ordered[i + 1].placement_name}`,
    );
  }

  // Primary preservation: the equipment primary keeps a scale at least as large
  // as every filler's, and the fillers carry the shrink.
  const primaryScale = zoneDecision.shrinkApplied.p_heat_block;
  for (const name of ["f_rack_a", "f_rack_b", "f_waste"]) {
    assert.ok(
      primaryScale >= zoneDecision.shrinkApplied[name] - 1e-9,
      `primary scale ${primaryScale} should be >= filler ${name} scale ${zoneDecision.shrinkApplied[name]}`,
    );
  }
  // At least one filler actually shrank (the zone was genuinely overloaded).
  const anyFillerShrank = ["f_rack_a", "f_rack_b", "f_waste"].some(
    (n) => zoneDecision.shrinkApplied[n] < 1,
  );
  assert.ok(anyFillerShrank, "expected at least one filler to shrink in an overloaded zone");
});
