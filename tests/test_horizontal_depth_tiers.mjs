// Regression coverage for horizontal tier partitioning. A depth tier is one
// vertical shelf, so only peers in the same tier compete for horizontal space.

import test from "node:test";
import assert from "node:assert/strict";

import { buildGlobalDefaults, horizontalLayout } from "../src/scene_runtime/layout/index.ts";

const ZONE = { id: "focus", bounds: { left: 0, right: 60, top: 0, bottom: 100 } };

function item(name, depthTier, width) {
  return {
    placement_name: name,
    object_name: name,
    zone: ZONE.id,
    depth_tier: depthTier,
    depth: "mid",
    kind: "equipment",
    layout: { default_width: width, label_width: width },
    _width_scale: 1,
  };
}

test("horizontalLayout: distinct tiers each use the full zone width", () => {
  const diagnostics = [];
  const packerSink = new Map();
  const layouts = horizontalLayout(
    new Map([[ZONE.id, [item("rear_focus", 0, 45), item("front_focus", 1, 45)]]]),
    [ZONE],
    {},
    diagnostics,
    buildGlobalDefaults(),
    { packerSink },
  );

  // Each item fits independently. Combining distinct vertical shelves into
  // one horizontal row would incorrectly shrink both items.
  assert.equal(
    diagnostics.some((entry) => entry.kind === "zone_overflow_negative_gap"),
    false,
  );
  assert.ok(
    layouts.get(ZONE.id).every((placed) => placed._scale === 1),
    "separate shelves must not shrink one another horizontally",
  );
});

test("horizontalLayout: a genuinely overloaded tier still reports overflow", () => {
  const diagnostics = [];
  const packerSink = new Map();
  horizontalLayout(
    new Map([
      [
        ZONE.id,
        [
          item("left_overload", 0, 80),
          item("right_overload", 0, 80),
          item("separate_fitting_tier", 1, 20),
        ],
      ],
    ]),
    [ZONE],
    {},
    diagnostics,
    buildGlobalDefaults(),
    { packerSink },
  );

  assert.equal(
    diagnostics.some((entry) => entry.kind === "zone_overflow_negative_gap"),
    true,
  );
});
