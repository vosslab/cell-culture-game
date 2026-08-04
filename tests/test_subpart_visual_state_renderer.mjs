// tests/test_subpart_visual_state_renderer.mjs
//
// Genericity + dispatch-contract tests for the structured-subpart material-tint
// interpreter (M3 WP-SUBPART-RENDER). These are PURE tests of the dispatch
// predicate find_material_tint_subpart_field; they call it on hand-built object
// defs and never render a Solid component (the browser render is proven by
// tests/playwright/test_subpart_well_plate_render.mjs).
//
// The point of these tests is the MODULARITY claim: the interpreter keys on the
// DECLARED contract (subpart_geometry + a subpart material_tint visual_state on
// some field), not on object identity, field name, or shape. A second structured
// object -- a different object name, a different driving-field name, rect geometry
// instead of circle -- dispatches identically with NO new TypeScript. These tests
// encode exactly that: the same predicate returns the right field for a real
// well_plate_96-shaped def AND for a synthetic rect-subpart def with a renamed
// field, and returns null whenever any part of the contract is missing.
//
// Run with:
//   node --import tsx --test tests/test_subpart_visual_state_renderer.mjs

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  find_material_tint_subpart_field,
  find_subpart_material_contract,
} from "../src/scene_runtime/renderer/subpart_dispatch.ts";
import {
  circle_fill_path,
  resolve_subpart_material_state,
} from "../src/scene_runtime/renderer/subpart_material_state.ts";

//============================================
// Def builders (minimal ObjectDef shapes)
//============================================

// A minimal valid ObjectDef carrying the subpart material-tint contract. The
// driving field name, object name, and geometry shape are all parameterized so a
// single builder produces a circle-well plate OR a rect-lane object with a renamed
// field, proving the predicate hardcodes none of them.
function make_def(opts) {
  const {
    object_name,
    field_name,
    shape, // "circle" | "rect"
    with_geometry = true,
    with_view_box = true,
    applies_to = "subpart",
    render_effect = "material_tint",
    target = "subpart_geometry",
  } = opts;

  const geom =
    shape === "rect"
      ? { L1: { shape: "rect", x: 0, y: 0, w: 10, h: 10 } }
      : { A1: { shape: "circle", cx: 5, cy: 5, r: 2 } };

  const def = {
    object_name,
    kind: "plate",
    label: object_name,
    asset: "some_asset",
    capabilities: [],
    layout: { default_width: 10, label_width: 5 },
    state_schema: {},
    visual_states: {
      [field_name]: { applies_to, render_effect, target },
    },
    subpart_state_schema: {},
  };
  if (with_geometry) {
    def.subpart_geometry = geom;
  }
  if (with_view_box) {
    def.view_box = { min_x: 0, min_y: 0, width: 100, height: 100 };
  }
  return def;
}

//============================================
// Contract is satisfied -> returns the declared field name
//============================================

describe("dispatch predicate keys on the declared contract, not identity", () => {
  test("circle-well plate (material_name) -> dispatches on the declared field", () => {
    const def = make_def({
      object_name: "well_plate_96",
      field_name: "material_name",
      shape: "circle",
    });
    const contract = find_material_tint_subpart_field(def);
    assert.notEqual(contract, null);
    // The field NAME is read from the declaration, never hardcoded.
    assert.equal(contract.field_name, "material_name");
  });

  test("SECOND structured object: rect subparts + RENAMED field, no new TS", () => {
    // A synthetic gel-lane-style object: different object name, a different
    // driving-field name ("lane_material"), and rect geometry. The same predicate
    // must dispatch with no code change, proving modularity.
    const def = make_def({
      object_name: "gel_8_lane",
      field_name: "lane_material",
      shape: "rect",
    });
    const contract = find_material_tint_subpart_field(def);
    assert.notEqual(contract, null);
    assert.equal(contract.field_name, "lane_material");
  });
});

//============================================
// Contract is NOT satisfied -> returns null (no dispatch)
//============================================

describe("predicate returns null when any contract part is missing", () => {
  test("no subpart_geometry -> null (nothing to draw)", () => {
    const def = make_def({
      object_name: "no_geom",
      field_name: "material_name",
      shape: "circle",
      with_geometry: false,
    });
    assert.equal(find_material_tint_subpart_field(def), null);
  });

  test("no view_box -> null (no coordinate frame)", () => {
    const def = make_def({
      object_name: "no_viewbox",
      field_name: "material_name",
      shape: "circle",
      with_view_box: false,
    });
    assert.equal(find_material_tint_subpart_field(def), null);
  });

  test("applies_to: object (not subpart) -> null", () => {
    const def = make_def({
      object_name: "obj_scope",
      field_name: "material_name",
      shape: "circle",
      applies_to: "object",
    });
    assert.equal(find_material_tint_subpart_field(def), null);
  });

  test("wrong render_effect (fill_height) -> null", () => {
    const def = make_def({
      object_name: "fill_only",
      field_name: "material_volume",
      shape: "circle",
      render_effect: "fill_height",
    });
    assert.equal(find_material_tint_subpart_field(def), null);
  });

  test("wrong target (anchor, not subpart_geometry) -> null", () => {
    const def = make_def({
      object_name: "anchor_target",
      field_name: "material_name",
      shape: "circle",
      target: "anchor_liquid_bounds",
    });
    assert.equal(find_material_tint_subpart_field(def), null);
  });

  test("no material_tint subpart visual_state at all -> null", () => {
    const def = {
      object_name: "plain_plate",
      kind: "plate",
      label: "plain",
      asset: "a",
      capabilities: [],
      layout: { default_width: 10, label_width: 5 },
      state_schema: {},
      visual_states: {
        // Only an object-level svg case; no subpart material_tint.
        inspection_status: {
          kind: "svg",
          applies_to: "object",
          cases: [{ when: "x", output: { asset_name: "a" } }],
        },
      },
      subpart_state_schema: {},
      subpart_geometry: { A1: { shape: "circle", cx: 5, cy: 5, r: 2 } },
      view_box: { min_x: 0, min_y: 0, width: 100, height: 100 },
    };
    assert.equal(find_material_tint_subpart_field(def), null);
  });
});

describe("per-subpart amount contract and behavior", () => {
  test("renamed identity and amount fields dispatch with declared capacity", () => {
    const def = make_def({
      object_name: "rack",
      field_name: "tube_identity",
      shape: "rect",
    });
    def.visual_states.tube_amount = {
      applies_to: "subpart",
      render_effect: "fill_height",
      target: "subpart_geometry",
      capacity_ul: 100,
    };
    const contract = find_subpart_material_contract(def);
    assert.equal(contract?.identity_field_name, "tube_identity");
    assert.equal(contract?.amount.capacity, 100);
  });

  test("invalid capacities stay declared and fail loudly", () => {
    const def = make_def({ object_name: "rack", field_name: "identity", shape: "rect" });
    def.visual_states.amount = {
      applies_to: "subpart",
      render_effect: "fill_height",
      target: "subpart_geometry",
      capacity_ul: 0,
      capacity_ml: 1,
    };
    const contract = find_subpart_material_contract(def);
    assert.notEqual(contract, null);
    const state = resolve_subpart_material_state("media", 5, null, contract.amount.capacity_error, {
      media: { label: "Media", display_color: "#123456" },
    });
    assert.match(state.degraded, /exactly one positive/);
  });

  test("capacity requires one declared finite positive value", () => {
    const invalid_capacities = [
      { capacity_ul: Number.NaN },
      { capacity_ul: Number.POSITIVE_INFINITY },
      { capacity_ul: -1 },
      { capacity_ul: 100, capacity_ml: "malformed" },
    ];
    for (const capacity_fields of invalid_capacities) {
      const def = make_def({ object_name: "rack", field_name: "identity", shape: "rect" });
      def.visual_states.amount = {
        applies_to: "subpart",
        render_effect: "fill_height",
        target: "subpart_geometry",
        ...capacity_fields,
      };
      const contract = find_subpart_material_contract(def);
      assert.notEqual(contract, null);
      assert.match(contract.amount.capacity_error, /exactly one positive/);
    }
  });

  test("amounts above capacity remain visibly full", () => {
    const state = resolve_subpart_material_state("media", 150, 100, "", {
      media: { label: "Media", display_color: "#123456" },
    });
    assert.equal(state.fill_percent, 100);
  });

  test("circle amount emits no artwork when empty and a closed fill when nonempty", () => {
    const circle = { shape: "circle", cx: 10, cy: 10, r: 5 };
    assert.equal(circle_fill_path(circle, 0), "");
    assert.match(circle_fill_path(circle, 25), /12\.5/);
    assert.match(circle_fill_path(circle, 75), /7\.5/);
  });

  test("zero visible amount is valid without corrupting a nonzero sibling", () => {
    const registry = { media: { label: "Media", display_color: "#123456" } };
    const zeroAmount = resolve_subpart_material_state("media", 0, 100, "", registry);
    const sibling = resolve_subpart_material_state("media", 50, 100, "", registry);
    assert.deepEqual(
      { fill: zeroAmount.fill, percent: zeroAmount.fill_percent, degraded: zeroAmount.degraded },
      { fill: "transparent", percent: 0, degraded: "" },
    );
    assert.deepEqual(
      { fill: sibling.fill, percent: sibling.fill_percent },
      { fill: "#123456", percent: 50 },
    );
  });

  test("empty plus zero is transparent success while malformed state degrades", () => {
    const empty = resolve_subpart_material_state("empty", 0, 100, "", {});
    const malformed = resolve_subpart_material_state("media", "50", 100, "", {});
    assert.equal(empty.degraded, "");
    assert.match(malformed.degraded, /not numeric/);
  });

  test("wrong identity type and registry failure degrade without a fallback color", () => {
    const wrong_identity = resolve_subpart_material_state(7, 50, 100, "", {});
    const unknown_material = resolve_subpart_material_state("unknown", 50, 100, "", {});
    assert.match(wrong_identity.degraded, /identity is missing/);
    assert.match(unknown_material.degraded, /not in protocol material registry/);
  });
});
