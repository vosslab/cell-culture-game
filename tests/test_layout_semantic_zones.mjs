// Semantic zones are authored groupings. The layout manager lowers them to
// internal geometry after measurement; source zone names carry no geometry.

import assert from "node:assert/strict";
import test from "node:test";

import {
  DEMO_ASSET_SPECS,
  DEMO_OBJECT_LIBRARY,
  runPipeline,
} from "../src/scene_runtime/layout/index.ts";
import { resolvePrecomputedScene } from "../src/scene_runtime/layout/precomputed_result.ts";

const library = {
  ...DEMO_OBJECT_LIBRARY,
  display_plate: {
    ...DEMO_OBJECT_LIBRARY.heat_block,
    object_name: "display_plate",
    kind: "plate",
    label: "96-well plate",
    asset: "display_plate",
    layout: {
      default_width: 48,
      label_width: 18,
      anchor_y: "bottom",
      display_width_cm: 36,
    },
  },
};

const assets = {
  ...DEMO_ASSET_SPECS,
  display_plate: { default_width: 48, label_width: 18, aspect: 1.5 },
};

function semanticScene(zoneNames = ["focus", "support"]) {
  return {
    scene_name: "semantic_plate_scene",
    workspace: "bench",
    zones: zoneNames.map((id) => ({ id })),
    placements: [
      { placement_name: "plate", object_name: "display_plate", zone: zoneNames[0] },
      { placement_name: "media", object_name: "media_bottle", zone: zoneNames[1] },
      { placement_name: "pipet", object_name: "serological_pipette", zone: zoneNames[1] },
    ],
  };
}

function run(scene) {
  return runPipeline(scene, { library, assets });
}

test("semantic zones need no source coordinates and lower without mutating source", () => {
  const scene = semanticScene();
  const before = structuredClone(scene);
  const result = run(scene);

  assert.deepEqual(scene, before, "layout preserves authored scene input");
  assert.ok(
    result.scene.zones.every((zone) => zone.bounds !== undefined && zone.baseline !== undefined),
    "layout lowers coordinate-free authored zones to renderable geometry",
  );
});

test("opaque zone names do not influence semantic-zone geometry", () => {
  const first = run(semanticScene(["alpha", "beta"]));
  const second = run(semanticScene(["any_name", "renamed_group"]));

  const geometry = (result) =>
    result.scene.zones.map((zone) => ({
      bounds: zone.bounds,
      baseline: zone.baseline,
    }));
  assert.deepEqual(geometry(first), geometry(second));
});

test("larger measured placement demand receives more semantic-zone width", () => {
  const result = run(semanticScene());
  const [plateZone, supportZone] = result.scene.zones;
  const width = (zone) => zone.bounds.right - zone.bounds.left;

  assert.ok(width(plateZone) > width(supportZone));
});

test("lowered semantic zones remain usable workspace regions", () => {
  const result = run(semanticScene(["first", "second"]));
  const { scene_bounds, zones } = result.scene;

  for (const zone of zones) {
    assert.ok(zone.bounds.left >= scene_bounds.left);
    assert.ok(zone.bounds.right <= scene_bounds.right);
    assert.ok(zone.bounds.top >= scene_bounds.top);
    assert.ok(zone.bounds.bottom <= scene_bounds.bottom);
  }
  assert.ok(
    zones.every(
      (zone, index) =>
        index === 0 ||
        zone.bounds.top > zones[index - 1].bounds.top ||
        zones[index - 1].bounds.right <= zone.bounds.left,
    ),
    "lowered zones must not overlap",
  );
});

test("semantic flow wraps declaration-ordered zones into measured vertical bands", () => {
  const zoneIds = ["a", "b", "c", "d", "e"];
  const scene = {
    scene_name: "semantic_flow",
    workspace: "bench",
    zones: zoneIds.map((id) => ({ id })),
    placements: zoneIds.map((zone, index) => ({
      placement_name: `plate_${index}`,
      object_name: "display_plate",
      zone,
      depth_tier: index % 2,
    })),
  };
  const result = run(scene);
  const zones = result.scene.zones;

  assert.ok(
    zones.some((zone, index) => index > 0 && zone.bounds.top > zones[index - 1].bounds.top),
    "measured demand creates a later flow row instead of fixed equal slots",
  );
  for (let index = 1; index < zones.length; index += 1) {
    const previous = zones[index - 1];
    const current = zones[index];
    if (current.bounds.top === previous.bounds.top) {
      assert.ok(previous.bounds.right <= current.bounds.left);
    } else {
      assert.ok(previous.bounds.bottom <= current.bounds.top);
    }
  }
});

test("legacy coordinate-bearing scenes retain their authored geometry", () => {
  const scene = {
    scene_name: "legacy_scene",
    workspace: "bench",
    scene_bounds: { left: 2, right: 98, top: 4, bottom: 96 },
    zones: [
      {
        id: "legacy_zone",
        bounds: { left: 10, right: 90, top: 20, bottom: 80 },
        baseline: 72,
        align: "center",
      },
    ],
    placements: [{ placement_name: "media", object_name: "media_bottle", zone: "legacy_zone" }],
  };
  const result = run(scene);

  assert.deepEqual(result.scene.scene_bounds, scene.scene_bounds);
  assert.deepEqual(result.scene.zones, scene.zones);
});

test("semantic precomputed scenes require serialized resolved geometry", () => {
  assert.throws(
    () => resolvePrecomputedScene("semantic_plate_scene", semanticScene(), [], undefined),
    /lacks resolved geometry/,
  );
});

test("serialized precomputed geometry is used verbatim", () => {
  const source = semanticScene();
  const resolved = run(source).scene;

  assert.equal(resolvePrecomputedScene("semantic_plate_scene", source, [], resolved), resolved);
});
