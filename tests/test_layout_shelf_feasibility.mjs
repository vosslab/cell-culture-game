// Cross-zone shelf feasibility regression tests. Run with:
//   node --import tsx --test tests/test_layout_shelf_feasibility.mjs
//
// A shared shelf is a placement preference. It may only be used when every
// object's artwork plus initial label strip remains inside its own reflowed tier
// row; otherwise that whole tier falls back to one shelf per zone row.

import test from "node:test";
import assert from "node:assert/strict";

import { verticalLayout } from "../src/scene_runtime/layout/index.ts";

const VIEWPORT = { w: 1920, h: 1080 };
const EPS = 1e-9;

function makeZone(id) {
  // Equal authored vertical extents make these side-by-side zones one candidate
  // cross-zone shelf. Their COMPUTED rows below intentionally differ in the
  // infeasible case.
  return { id, bounds: { left: 1, right: 99, top: 5, bottom: 95 } };
}

function makeItem(name, visualWidth, labelPlacement = "top", anchorY = "bottom", anchorOffset = 0) {
  return {
    placement_name: name,
    _visualWidth: visualWidth,
    aspect: 1,
    _labelBoxHeight: 2,
    _labelPlacement: labelPlacement,
    layout: {
      anchor_y: anchorY,
      anchor_y_offset: anchorOffset,
      label_placement: labelPlacement,
    },
  };
}

function makeBand(id, rowTop, rowHeight, placementName) {
  return {
    id,
    top: rowTop,
    bottom: rowTop + rowHeight,
    baseline: rowTop + rowHeight,
    tiers: [
      {
        depthTier: 1,
        rowTop,
        rowHeight,
        placementNames: [placementName],
      },
    ],
  };
}

test("verticalLayout: infeasible cross-zone shelf demotes each tier row locally", () => {
  const zones = [makeZone("left_zone"), makeZone("right_zone")];
  const zoneLayouts = new Map([
    ["left_zone", [makeItem("left_reagent", 5.625)]],
    ["right_zone", [makeItem("right_waste", 5.625)]],
  ]);
  // The candidate shared baseline would be 40, which pushes left_reagent's
  // object and top label below its own [10, 30] row. The local shelves are 30
  // and 40 respectively, both of which fit their measured reservation.
  const bands = new Map([
    ["left_zone", makeBand("left_zone", 10, 20, "left_reagent")],
    ["right_zone", makeBand("right_zone", 20, 20, "right_waste")],
  ]);
  const diagnostics = [];

  const placed = verticalLayout(zoneLayouts, zones, bands, VIEWPORT, diagnostics);
  const left = placed.get("left_zone")[0];
  const right = placed.get("right_zone")[0];

  assert.notEqual(
    left._baselineY,
    right._baselineY,
    "infeasible tier uses local rather than shared shelves",
  );
  assert.ok(
    diagnostics.some((diagnostic) => diagnostic.kind === "item_escapes_zone_vertically"),
    "the infeasible shared shelf is reported rather than silently clipping an object",
  );
});

test("verticalLayout: feasible cross-zone shelf remains shared", () => {
  const zones = [makeZone("left_zone"), makeZone("right_zone")];
  const zoneLayouts = new Map([
    ["left_zone", [makeItem("left_reagent", 5.625)]],
    ["right_zone", [makeItem("right_waste", 4.5)]],
  ]);
  const bands = new Map([
    ["left_zone", makeBand("left_zone", 10, 20, "left_reagent")],
    ["right_zone", makeBand("right_zone", 10, 20, "right_waste")],
  ]);
  const diagnostics = [];

  const placed = verticalLayout(zoneLayouts, zones, bands, VIEWPORT, diagnostics);
  const left = placed.get("left_zone")[0];
  const right = placed.get("right_zone")[0];

  assert.ok(
    Math.abs(left._baselineY - right._baselineY) < EPS,
    "a clean shelf keeps one shared baseline across its zones",
  );
  assert.equal(
    diagnostics.some((diagnostic) => diagnostic.kind === "item_escapes_zone_vertically"),
    false,
    "feasible alignment emits no demotion warning",
  );
});

test("verticalLayout: shifted tip artwork is measured below its shelf", () => {
  const zones = [makeZone("left_zone"), makeZone("right_zone")];
  const zoneLayouts = new Map([
    ["left_zone", [makeItem("shifted_tip", 5.625, "bottom", "tip", 3)]],
    ["right_zone", [makeItem("ordinary_bottom", 5.625, "bottom")]],
  ]);
  // Without the tip offset, a bottom label exactly fills this row reservation.
  // The positive offset lowers the actual object bottom by 3 percentage points,
  // so its label must make the candidate shelf infeasible.
  const bands = new Map([
    ["left_zone", makeBand("left_zone", 10, 20, "shifted_tip")],
    ["right_zone", makeBand("right_zone", 10, 20, "ordinary_bottom")],
  ]);
  const diagnostics = [];

  const placed = verticalLayout(zoneLayouts, zones, bands, VIEWPORT, diagnostics);
  const tip = placed.get("left_zone")[0];

  assert.ok(tip._top + tip._height > tip._baselineY);
  assert.ok(diagnostics.some((diagnostic) => diagnostic.kind === "item_escapes_zone_vertically"));
});

test("verticalLayout: top-anchored artwork is measured below its shelf", () => {
  const zones = [makeZone("left_zone"), makeZone("right_zone")];
  const zoneLayouts = new Map([
    ["left_zone", [makeItem("centered_object", 5.625, "bottom", "top")]],
    ["right_zone", [makeItem("ordinary_bottom", 5.625, "bottom")]],
  ]);
  // `anchor_y: top` is the supported centered fallback. Its object bottom lies
  // half an object height below the baseline, so baseline + gap is not a valid
  // bottom-label seed.
  const bands = new Map([
    ["left_zone", makeBand("left_zone", 10, 20, "centered_object")],
    ["right_zone", makeBand("right_zone", 10, 20, "ordinary_bottom")],
  ]);
  const diagnostics = [];

  const placed = verticalLayout(zoneLayouts, zones, bands, VIEWPORT, diagnostics);
  const centered = placed.get("left_zone")[0];

  assert.ok(centered._top + centered._height > centered._baselineY);
  assert.ok(diagnostics.some((diagnostic) => diagnostic.kind === "item_escapes_zone_vertically"));
});
