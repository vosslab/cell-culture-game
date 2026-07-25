// Seed-list behavior for authored, generated object definitions. These tests
// deliberately use real object-library entries rather than synthetic fixtures.

import assert from "node:assert/strict";
import test from "node:test";

import { OBJECT_LIBRARY } from "../generated/object_library.js";
import { build_seed_list } from "../src/scene_runtime/renderer/scene_view.tsx";

function resultWith(...objectNames) {
  return { final: objectNames.map((object_name) => ({ object_name })) };
}

function targets(seeds) {
  return seeds.map((seed) => seed.target);
}

test("well plate seeds its object state and every declared well in order", () => {
  const plate = OBJECT_LIBRARY.well_plate_96;
  const wells = plate.subparts ?? [];
  const seeds = build_seed_list(resultWith("well_plate_96"));

  const expected = ["well_plate_96", ...wells.map((well) => `well_plate_96.${well}`)];
  assert.deepEqual(targets(seeds), expected);
  assert.ok(seeds.every((seed) => seed.object_name === "well_plate_96"));
});

test("dilution rack seeds declared tubes without a state-free bare rack", () => {
  const rack = OBJECT_LIBRARY.dilution_tube_rack_8;
  const tubes = rack.subparts ?? [];
  const seeds = build_seed_list(resultWith("dilution_tube_rack_8"));

  assert.deepEqual(
    targets(seeds),
    tubes.map((tube) => `dilution_tube_rack_8.${tube}`),
  );
  assert.ok(!targets(seeds).includes("dilution_tube_rack_8"));
});

test("duplicate placements share one deterministic set of object and subpart seeds", () => {
  const rack = OBJECT_LIBRARY.dilution_tube_rack_8;
  const plate = OBJECT_LIBRARY.well_plate_96;
  const rackTargets = (rack.subparts ?? []).map((tube) => `dilution_tube_rack_8.${tube}`);
  const plateTargets = [
    "well_plate_96",
    ...(plate.subparts ?? []).map((well) => `well_plate_96.${well}`),
  ];
  const seeds = build_seed_list(
    resultWith("dilution_tube_rack_8", "dilution_tube_rack_8", "well_plate_96", "well_plate_96"),
  );

  assert.deepEqual(targets(seeds), [...rackTargets, ...plateTargets]);
  assert.equal(new Set(targets(seeds)).size, seeds.length, "each store target is seeded once");
});

test("an unknown rendered object emits no seed", () => {
  assert.deepEqual(build_seed_list(resultWith("missing_object")), []);
});
