// tests/test_visual_state_resolver.mjs
//
// Behavioral tests for WS-M2-R (resolve_visual_state). Covers the inventoried
// formula set: fill_height (ml/ul/mg), label, conditional (flat and nested),
// compose, svg case selection, material color from the per-protocol registry,
// and fail-loud paths for unknown tokens.
//
// Run with:
//   node --import tsx --test tests/test_visual_state_resolver.mjs

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { resolve_visual_state } from "../src/scene_runtime/renderer/visual_state_resolver.ts";
import { OBJECT_LIBRARY } from "../generated/object_library.ts";

//============================================
// Fixture: a simple per-protocol material registry
//============================================

const MATERIAL_REGISTRY = {
  pbs: {
    label: "1x PBS",
    display_color: "#076dad",
  },
  cell_suspension: {
    label: "Cell suspension",
    display_color: "#935d00",
  },
};

//============================================
// fill_height: flask / tube style container (capacity_ml)
//============================================

describe("fill_height capacity_ml", () => {
  const visual_states = {
    material_name: {
      kind: "svg",
      applies_to: "object",
      cases: [
        { when: "empty", output: { asset_name: "flask_empty" } },
        { when: "pbs", output: { asset_name: "flask" } },
      ],
    },
    material_volume: {
      kind: "composite",
      applies_to: "object",
      formula: "fill_height(state(material_volume), capacity_ml=10.0)",
    },
  };

  test("vol=4, cap=10 -> 40% fill", () => {
    const state = { material_name: "pbs", material_volume: 4 };
    const out = resolve_visual_state(visual_states, state, MATERIAL_REGISTRY);
    assert.equal(out.asset_name, "flask");
    assert.equal(out.overlays.length, 1);
    assert.deepEqual(out.overlays[0], {
      type: "fill",
      field_name: "material_volume",
      fill_percent: 40,
    });
  });

  test("overfill clamps to 100%", () => {
    const state = { material_name: "pbs", material_volume: 50 };
    const out = resolve_visual_state(visual_states, state, MATERIAL_REGISTRY);
    assert.equal(out.overlays[0].fill_percent, 100);
  });

  test("material color resolves from registry", () => {
    const state = { material_name: "pbs", material_volume: 4 };
    const out = resolve_visual_state(visual_states, state, MATERIAL_REGISTRY);
    assert.equal(out.material_color, "#076dad");
    assert.equal(out.data_attrs["data-material"], "pbs");
  });

  test("empty sentinel material has null color", () => {
    const state = { material_name: "empty", material_volume: 0 };
    const out = resolve_visual_state(visual_states, state, MATERIAL_REGISTRY);
    assert.equal(out.material_color, null);
    assert.equal(out.asset_name, "flask_empty");
    assert.equal(out.overlays[0].fill_percent, 0);
  });
});

//============================================
// fill_height: micropipette (capacity_ul) and mtt vial (capacity_mg)
//============================================

describe("fill_height non-ml capacities", () => {
  test("capacity_ul: vol=50 ul, cap=200 -> 25%", () => {
    const visual_states = {
      held_material_volume: {
        kind: "composite",
        applies_to: "object",
        formula: "fill_height(state(held_material_volume), capacity_ul=200)",
      },
    };
    const state = { held_material_volume: 50 };
    const out = resolve_visual_state(visual_states, state, {});
    assert.equal(out.overlays[0].fill_percent, 25);
  });

  test("capacity_mg: mass=5 mg, cap=10 -> 50% (no liquid-unit assumption)", () => {
    const visual_states = {
      material_volume: {
        kind: "composite",
        applies_to: "object",
        formula: "fill_height(state(material_volume), capacity_mg=10)",
      },
    };
    const state = { material_volume: 5 };
    const out = resolve_visual_state(visual_states, state, {});
    assert.equal(out.overlays[0].fill_percent, 50);
  });
});

//============================================
// Declarative anchor material effects (new modular object path)
//============================================

describe("declarative anchor material effects", () => {
  test("pairs scoped volume_ml with scoped material identity and capacity_ml", () => {
    const visual_states = {
      inner_chamber_volume_ml: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ml: 12,
      },
    };
    const out = resolve_visual_state(
      visual_states,
      { inner_chamber_volume_ml: 3, inner_chamber_material_name: "pbs" },
      MATERIAL_REGISTRY,
    );
    assert.equal(out.anchor_material_effects[0].fill_percent, 25);
    assert.equal(out.anchor_material_effects[0].color, "#076dad");
  });

  test("empty or zero material effects remain explicit no-fill descriptions", () => {
    const visual_states = {
      material_volume: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ml: 10,
      },
    };
    const out = resolve_visual_state(
      visual_states,
      { material_name: "empty", material_volume: 0 },
      MATERIAL_REGISTRY,
    );
    assert.equal(out.anchor_material_effects[0].color, null);
    assert.equal(out.anchor_material_effects[0].fill_percent, 0);
  });

  test("requires the generic paired material field", () => {
    const visual_states = {
      held_volume_ul: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ul: 200,
      },
    };
    assert.throws(
      () => resolve_visual_state(visual_states, { held_volume_ul: 10 }, MATERIAL_REGISTRY),
      /held_material_name/,
    );
  });

  test("non-empty material plus zero paired amount degrades loudly", () => {
    const visual_states = {
      material_name: {
        applies_to: "object",
        render_effect: "material_tint",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
      },
    };
    assert.throws(
      () =>
        resolve_visual_state(
          visual_states,
          { material_name: "pbs", material_volume: 0 },
          MATERIAL_REGISTRY,
        ),
      /non-empty material 'pbs' has zero paired amount/,
    );
  });

  test("fill_height rejects non-empty material with a missing amount", () => {
    const visual_states = {
      material_volume: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ml: 10,
      },
    };
    assert.throws(
      () => resolve_visual_state(visual_states, { material_name: "pbs" }, MATERIAL_REGISTRY),
      /non-empty material 'pbs' requires amount field 'material_volume'/,
    );
  });

  test("fill_height rejects empty material with a positive amount", () => {
    const visual_states = {
      material_volume: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ml: 10,
      },
    };
    assert.throws(
      () =>
        resolve_visual_state(
          visual_states,
          { material_name: "empty", material_volume: 2 },
          MATERIAL_REGISTRY,
        ),
      /empty material has positive amount/,
    );
  });

  test("null material identity degrades loudly instead of becoming no fill", () => {
    const visual_states = {
      material_volume: {
        applies_to: "object",
        render_effect: "fill_height",
        target: "anchor_liquid_bounds",
        clip: "anchor_liquid_clip",
        capacity_ml: 10,
      },
    };
    assert.throws(
      () =>
        resolve_visual_state(
          visual_states,
          { material_name: null, material_volume: 2 },
          MATERIAL_REGISTRY,
        ),
      /invalid material identity/,
    );
  });
});

//============================================
// label: set-point overlay
//============================================

describe("label formula", () => {
  test("label renders value with format and {value} substitution", () => {
    const visual_states = {
      set_volume: {
        kind: "overlay",
        applies_to: "object",
        formula: 'label(state(set_volume), format="{value} ml")',
      },
    };
    const state = { set_volume: 25 };
    const out = resolve_visual_state(visual_states, state, {});
    assert.deepEqual(out.overlays[0], {
      type: "text",
      field_name: "set_volume",
      text: "25 ml",
    });
    assert.equal(out.label_text, "25 ml");
  });
});

//============================================
// conditional: flat and nested (label inside conditional)
//============================================

describe("conditional formula", () => {
  test("flat conditional picks then branch when truthy", () => {
    const visual_states = {
      excess_wiped: {
        kind: "overlay",
        applies_to: "object",
        formula: 'conditional(state(excess_wiped), "Wiped clean", "Excess present")',
      },
    };
    const out_true = resolve_visual_state(visual_states, { excess_wiped: true }, {});
    assert.equal(out_true.label_text, "Wiped clean");
    const out_false = resolve_visual_state(visual_states, { excess_wiped: false }, {});
    assert.equal(out_false.label_text, "Excess present");
  });

  test("nested label inside conditional (cell_counter case)", () => {
    const visual_states = {
      cell_count: {
        kind: "overlay",
        applies_to: "object",
        formula:
          'conditional(state(cell_count), label(state(cell_count), format="Count: {value}"), "Ready")',
      },
    };
    const out_counted = resolve_visual_state(visual_states, { cell_count: 1200 }, {});
    assert.equal(out_counted.label_text, "Count: 1200");
    const out_zero = resolve_visual_state(visual_states, { cell_count: 0 }, {});
    assert.equal(out_zero.label_text, "Ready");
  });
});

//============================================
// compose: implemented, not no-opped
//============================================

describe("compose formula", () => {
  test("compose contributes each part's overlays in order", () => {
    const visual_states = {
      material_volume: {
        kind: "composite",
        applies_to: "object",
        formula:
          'compose(fill_height(state(material_volume), capacity_ml=10), label(state(set_volume), format="{value} ml"))',
      },
    };
    const state = { material_volume: 2, set_volume: 7 };
    const out = resolve_visual_state(visual_states, state, {});
    assert.equal(out.overlays.length, 2);
    assert.equal(out.overlays[0].type, "fill");
    assert.equal(out.overlays[0].fill_percent, 20);
    assert.equal(out.overlays[1].type, "text");
    assert.equal(out.overlays[1].text, "7 ml");
  });
});

//============================================
// svg case selection: bool cases and placeholder path
//============================================

describe("svg case selection", () => {
  test("bool when-cases select asset", () => {
    const visual_states = {
      slide_loaded: {
        kind: "svg",
        applies_to: "object",
        cases: [
          { when: false, output: { asset_name: "counter_idle" } },
          { when: true, output: { asset_name: "counter_loaded" } },
        ],
      },
    };
    const out = resolve_visual_state(visual_states, { slide_loaded: true }, {});
    assert.equal(out.asset_name, "counter_loaded");
    assert.equal(out.placeholder, undefined);
  });

  test("no svg entry yields placeholder=true", () => {
    const visual_states = {
      set_volume: {
        kind: "overlay",
        applies_to: "object",
        formula: 'label(state(set_volume), format="{value} ml")',
      },
    };
    const out = resolve_visual_state(visual_states, { set_volume: 3 }, {});
    assert.equal(out.asset_name, null);
    assert.equal(out.placeholder, true);
  });

  test("empty composite literal is a no-op", () => {
    const visual_states = {
      material_name: {
        kind: "svg",
        applies_to: "object",
        cases: [{ when: "empty", output: { asset_name: "tube" } }],
      },
      material_volume: { kind: "composite", applies_to: "object", composite: [] },
    };
    const out = resolve_visual_state(
      visual_states,
      { material_name: "empty", material_volume: 0 },
      {},
    );
    assert.equal(out.asset_name, "tube");
    assert.equal(out.overlays.length, 0);
  });
});

describe("authored equipment composite states", () => {
  test("heat-block rack state adds its declared visual layer", () => {
    const out = resolve_visual_state(
      OBJECT_LIBRARY.heat_block.visual_states,
      { set_temperature: 95, lid_open: false, rack_present: true },
      null,
    );
    assert.equal(out.asset_name, "heat_block_closed");
    assert.deepEqual(out.asset_layers, ["heat_block_rack"]);
  });

  test("lightbox tray and capture states add ordered visual evidence", () => {
    const out = resolve_visual_state(
      OBJECT_LIBRARY.lightbox.visual_states,
      {
        powered_on: true,
        tray_present: true,
        image_captured: true,
        gel_state: "destained",
      },
      null,
    );
    assert.equal(out.asset_name, "lightbox_on");
    assert.deepEqual(out.asset_layers, ["lightbox_capture_complete", "lightbox_gel_tray"]);
    assert.equal(out.label_text, "Gel: destained");
  });
});

//============================================
// fail-loud paths
//============================================

describe("fail-loud paths", () => {
  test("unknown formula token throws", () => {
    const visual_states = {
      x: { kind: "overlay", applies_to: "object", formula: "bogus(state(x))" },
    };
    assert.throws(() => resolve_visual_state(visual_states, { x: 1 }, {}), /unknown formula token/);
  });

  test("unregistered non-sentinel material throws", () => {
    const visual_states = {
      material_name: {
        kind: "svg",
        applies_to: "object",
        cases: [{ when: "media", output: { asset_name: "bottle" } }],
      },
    };
    assert.throws(
      () => resolve_visual_state(visual_states, { material_name: "media" }, {}),
      /not in protocol material registry/,
    );
  });

  test("no matching svg case throws", () => {
    const visual_states = {
      material_name: {
        kind: "svg",
        applies_to: "object",
        cases: [{ when: "empty", output: { asset_name: "bottle" } }],
      },
    };
    assert.throws(
      () =>
        resolve_visual_state(
          visual_states,
          { material_name: "cell_suspension" },
          MATERIAL_REGISTRY,
        ),
      /no svg case matched/,
    );
  });
});
