// tests/test_material_area_verify.mjs
//
// Unit coverage for the generic structured material-area assertion
// verifyMaterialAreaEffect (tests/playwright/e2e/walker_helpers.mjs). The browser
// sweep exercises the bulk all_wells fan-out end to end (mtt_solubilization_readout
// verifies all 96 members), but the single-subpart and partial-plate NEGATIVE
// path ("the targeted well changed AND nothing else did") is carried in the
// corpus only by protocols currently blocked upstream by pre-existing, non-material
// scene bugs. This test drives that positive+negative logic directly over inline
// before/after overlay snapshots so both branches run deterministically:
//   - a single-subpart write leaves every other well untouched (pass),
//   - a silent no-op (targeted well kept its old material) is caught,
//   - a stray change to a non-targeted well is caught ("and nothing else"),
//   - a missing overlay is caught (spatial-correspondence failure).
//
// verifyMaterialAreaEffect is a pure comparison over DOM snapshots (no Playwright,
// no page), so it imports and runs under `node --test` with no browser.
//
// Run: node --test tests/test_material_area_verify.mjs

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  verifyMaterialAreaEffect,
  verifyMaterialAreaEffects,
} from "./playwright/e2e/walker_helpers.mjs";

// A report stub: verifyMaterialAreaEffect logs one info line on success.
const noopReport = { info() {} };

// A three-well plate snapshot: A1 empty, A2/A3 already hold media.
function baseBefore() {
  return {
    A1: { material: "empty", fill: "#ffffff" },
    A2: { material: "media", fill: "#ffcc00" },
    A3: { material: "media", fill: "#ffcc00" },
  };
}

//============================================
// Positive + negative "nothing else changed"
//============================================

test("single-subpart write passes when only the targeted well changes", () => {
  const effect = {
    object_name: "well_plate_96",
    material_field: "material_name",
    material_value: "carboplatin",
    expected_subparts: ["A1"],
  };
  const before = baseBefore();
  // Only A1 transitions; A2/A3 untouched.
  const after = {
    A1: { material: "carboplatin", fill: "#3355ff" },
    A2: { material: "media", fill: "#ffcc00" },
    A3: { material: "media", fill: "#ffcc00" },
  };
  // Passes with no throw.
  verifyMaterialAreaEffect(effect, before, after, noopReport);
});

test("silent no-op is caught: targeted well kept its old material", () => {
  const effect = {
    object_name: "well_plate_96",
    material_field: "material_name",
    material_value: "carboplatin",
    expected_subparts: ["A1"],
  };
  const before = baseBefore();
  // A1 did NOT change (the silent-material bug class).
  const after = baseBefore();
  assert.throws(
    () => verifyMaterialAreaEffect(effect, before, after, noopReport),
    /material_area_mismatch.*A1.*silent no-op/s,
  );
});

test("stray change to a non-targeted well is caught (nothing else must change)", () => {
  const effect = {
    object_name: "well_plate_96",
    material_field: "material_name",
    material_value: "carboplatin",
    expected_subparts: ["A1"],
  };
  const before = baseBefore();
  // A1 correctly changes, but A3 also changes -- a spatial-correspondence leak.
  const after = {
    A1: { material: "carboplatin", fill: "#3355ff" },
    A2: { material: "media", fill: "#ffcc00" },
    A3: { material: "carboplatin", fill: "#3355ff" },
  };
  assert.throws(
    () => verifyMaterialAreaEffect(effect, before, after, noopReport),
    /material_area_mismatch.*non-target subpart 'A3' changed/s,
  );
});

//============================================
// Overlay presence + group fan-out
//============================================

test("missing overlay is a failure, not a pass", () => {
  const effect = {
    object_name: "well_plate_96",
    material_field: "material_name",
    material_value: "carboplatin",
    expected_subparts: ["A1"],
  };
  assert.throws(
    () => verifyMaterialAreaEffect(effect, baseBefore(), {}, noopReport),
    /material_area_no_overlay/,
  );
});

test("bulk write passes when every member transitions and nothing else exists", () => {
  const effect = {
    object_name: "well_plate_96",
    material_field: "material_name",
    material_value: "cells",
    expected_subparts: ["A1", "A2", "A3"],
  };
  const before = baseBefore();
  const after = {
    A1: { material: "cells", fill: "#22aa55" },
    A2: { material: "cells", fill: "#22aa55" },
    A3: { material: "cells", fill: "#22aa55" },
  };
  verifyMaterialAreaEffect(effect, before, after, noopReport);
});

//============================================
// Multiple authored effects on one structured object
//============================================

test("mixed sample and ladder writes validate every lane from one scene snapshot", () => {
  const effects = [
    {
      object_name: "gel_cassette",
      material_field: "material_name",
      material_value: "protein_sample_denatured",
      expected_subparts: ["lane_1", "lane_2", "lane_3"],
    },
    {
      object_name: "gel_cassette",
      material_field: "material_name",
      material_value: "protein_ladder_denatured",
      expected_subparts: ["lane_4"],
    },
  ];
  const beforeByObject = new Map([
    [
      "gel_cassette",
      {
        lane_1: { material: "empty", fill: "#ffffff" },
        lane_2: { material: "empty", fill: "#ffffff" },
        lane_3: { material: "empty", fill: "#ffffff" },
        lane_4: { material: "empty", fill: "#ffffff" },
        lane_5: { material: "empty", fill: "#ffffff" },
      },
    ],
  ]);
  const afterByObject = new Map([
    [
      "gel_cassette",
      {
        lane_1: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_2: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_3: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_4: { material: "protein_ladder_denatured", fill: "#4455cc" },
        lane_5: { material: "empty", fill: "#ffffff" },
      },
    ],
  ]);

  verifyMaterialAreaEffects(effects, beforeByObject, afterByObject, noopReport);
});

test("mixed material write rejects a changed lane outside every authored effect", () => {
  const effects = [
    {
      object_name: "gel_cassette",
      material_field: "material_name",
      material_value: "protein_sample_denatured",
      expected_subparts: ["lane_1", "lane_2", "lane_3"],
    },
    {
      object_name: "gel_cassette",
      material_field: "material_name",
      material_value: "protein_ladder_denatured",
      expected_subparts: ["lane_4"],
    },
  ];
  const beforeByObject = new Map([
    [
      "gel_cassette",
      {
        lane_1: { material: "empty", fill: "#ffffff" },
        lane_2: { material: "empty", fill: "#ffffff" },
        lane_3: { material: "empty", fill: "#ffffff" },
        lane_4: { material: "empty", fill: "#ffffff" },
        lane_5: { material: "empty", fill: "#ffffff" },
      },
    ],
  ]);
  const afterByObject = new Map([
    [
      "gel_cassette",
      {
        lane_1: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_2: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_3: { material: "protein_sample_denatured", fill: "#cc4455" },
        lane_4: { material: "protein_ladder_denatured", fill: "#4455cc" },
        lane_5: { material: "protein_sample_denatured", fill: "#cc4455" },
      },
    ],
  ]);

  assert.throws(
    () => verifyMaterialAreaEffects(effects, beforeByObject, afterByObject, noopReport),
    /material_area_multi_mismatch.*non-target subpart 'lane_5' changed/,
  );
});
