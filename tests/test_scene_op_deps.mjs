// tests/test_scene_op_deps.mjs
//
// Node --test suite for the store-driven SceneOpDeps (WS-M3-D). Proves that
// each scene operation drives the reactive scene_store correctly, and that the
// SceneChange identity-reconciliation policy holds across a transition.
//
// These deps replace the old imperative build_scene_op_deps that poked DOM
// attributes. Here the contract is: ObjectStateChange/CursorAttach write the
// store; SceneChange reconciles the destination target set and preserves
// declared state for exact shared identities; LayoutMove fails loudly while
// unsupported; TimedWait writes runtime equipment-phase flags and delegates
// scheduling.
//
// The render_scene closure is the test seam: in the browser, protocol_host
// passes a closure that runs mountScene in reconcile mode. Here we inject an
// explicit destination target list and run the same store operation directly.
//
// Transition matrix:
//   - exact shared targets retain declared state
//   - new targets seed schema defaults
//   - absent targets and their subparts drop
//   - runtime-only flags reset
//   - cursor-held tool/material is restored when the tool remains present

import { test, describe } from "node:test";
import assert from "node:assert";

import { create_scene_store } from "../src/scene_runtime/state/scene_store.ts";
import { build_store_scene_op_deps } from "../src/scene_runtime/protocol/scene_op_deps.ts";
import { OBJECT_LIBRARY } from "../generated/object_library.js";

//============================================
// Helpers
//============================================

// Seed a store with the bench-like fixture set used across the suite.
//   micropipette: cursor-attachable tool with held_material_name + set_volume
//   bme_tube: material container (material_name enum + material_volume)
//   centrifuge:   instrument (running bool + set_rpm float)
function seed_scene(store) {
  store.seed_from_scene([
    { target: "micropipette", object_name: "micropipette" },
    { target: "bme_tube", object_name: "bme_tube" },
    { target: "centrifuge", object_name: "centrifuge" },
  ]);
}

// Build deps with a render_scene closure that reconciles a fixed destination
// target list (the way protocol_host mounts a SceneChange destination).
function deps_with_next_scene(store, nextSceneSeeds) {
  const render_scene = (_scene_name) => {
    store.reconcile_scene(nextSceneSeeds);
  };
  return build_store_scene_op_deps(store, render_scene);
}

//============================================
// ObjectStateChange
//============================================

describe("scene_op_deps ObjectStateChange", () => {
  test("writes a declared object field to the store", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "centrifuge",
      state: { running: true },
    });
    assert.strictEqual(store.state["centrifuge"].state.running, true);
  });

  test("partial-merges: a second write keeps the first", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "centrifuge",
      state: { set_rpm: 3000 },
    });
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "centrifuge",
      state: { running: true },
    });
    assert.strictEqual(store.state["centrifuge"].state.set_rpm, 3000);
    assert.strictEqual(store.state["centrifuge"].state.running, true);
  });

  test("auto-seeds a subpart target on first write", () => {
    // Registry-backed subpart material acceptance (D1): the store carries a
    // registry registering the written material. The test's subject is the
    // auto-seed-on-first-write behavior, not material acceptance.
    const store = create_scene_store({
      media: { label: "Growth media", display_color: "#6c6c00" },
    });
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    // conical_15ml_rack.slot_0 is NOT in the seed list; the deps must seed it.
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "conical_15ml_rack.slot_0",
      state: { material_name: "media" },
    });
    assert.strictEqual(store.state["conical_15ml_rack.slot_0"].state.material_name, "media");
    // Auto-seeding the subpart must not disturb an existing sibling.
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "centrifuge",
      state: { running: true },
    });
    assert.strictEqual(store.state["centrifuge"].state.running, true);
  });
});

//============================================
// ObjectStateChange subpart-group fan-out
//============================================

describe("scene_op_deps ObjectStateChange group fan-out", () => {
  test("a group write fans out to every declared member well", () => {
    // Registry registers the drug so the subpart material write is accepted.
    const store = create_scene_store({
      cells: { label: "Cells", display_color: "#6c6c00" },
    });
    store.seed_from_scene([{ target: "well_plate_96", object_name: "well_plate_96" }]);
    const deps = build_store_scene_op_deps(store, () => {});
    // Bulk write to the all_wells subpart_group.
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "well_plate_96.all_wells",
      state: { material_name: "cells", material_volume: 100 },
    });
    // Every declared member well received the write to its own slot. The expected
    // count comes from the object's own declared subpart_geometry (one entry per
    // physical well position), not from the all_wells group under test, so this
    // does not just re-read the array being asserted.
    const members = OBJECT_LIBRARY["well_plate_96"].subpart_groups["all_wells"];
    const wellCount = Object.keys(OBJECT_LIBRARY["well_plate_96"].subpart_geometry).length;
    assert.strictEqual(members.length, wellCount);
    for (const well of members) {
      const entry = store.state[`well_plate_96.${well}`];
      assert.ok(entry !== undefined, `well ${well} should be seeded by the fan-out`);
      assert.strictEqual(entry.state.material_name, "cells");
      assert.strictEqual(entry.state.material_volume, 100);
    }
    // No non-rendered "all_wells" pseudo-node was written.
    assert.strictEqual(store.state["well_plate_96.all_wells"], undefined);
  });

  test("a smaller group write reaches only its members", () => {
    const store = create_scene_store({
      cells: { label: "Cells", display_color: "#6c6c00" },
    });
    store.seed_from_scene([{ target: "well_plate_96", object_name: "well_plate_96" }]);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "well_plate_96.row_A",
      state: { material_name: "cells", material_volume: 50 },
    });
    // row_A members written; a non-member (B1) is untouched (unseeded).
    assert.strictEqual(store.state["well_plate_96.A1"].state.material_volume, 50);
    assert.strictEqual(store.state["well_plate_96.A12"].state.material_volume, 50);
    assert.strictEqual(store.state["well_plate_96.B1"], undefined);
  });

  test("a single-subpart write is not fanned out", () => {
    const store = create_scene_store({
      cells: { label: "Cells", display_color: "#6c6c00" },
    });
    store.seed_from_scene([{ target: "well_plate_96", object_name: "well_plate_96" }]);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "well_plate_96.A1",
      state: { material_name: "cells", material_volume: 25 },
    });
    assert.strictEqual(store.state["well_plate_96.A1"].state.material_volume, 25);
    assert.strictEqual(store.state["well_plate_96.A2"], undefined);
  });
});

//============================================
// CursorAttach
//============================================

describe("scene_op_deps CursorAttach", () => {
  test("attach sets the cursor_attached flag", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_cursor_attach({
      type: "CursorAttach",
      target: "micropipette",
      operation: "attach",
    });
    assert.strictEqual(store.state["micropipette"].flags.cursor_attached, true);
  });

  test("attach preserves an already-held material", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    // First an ObjectStateChange sets the held material on the tool, then a
    // later CursorAttach must not clobber it.
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "micropipette",
      state: { held_material_name: "trypan_blue", held_material_volume: 10 },
    });
    // Held-material lives in the object state for the tool; mirror it onto the
    // cursor flags via attach. attach reads current held flags (none yet), so
    // first set the cursor held material directly, then re-attach.
    store.set_cursor("micropipette", {
      attach: true,
      held_material_name: "trypan_blue",
      held_material_volume: 10,
    });
    deps.apply_cursor_attach({
      type: "CursorAttach",
      target: "micropipette",
      operation: "attach",
    });
    const flags = store.state["micropipette"].flags;
    assert.strictEqual(flags.cursor_attached, true);
    assert.strictEqual(flags.held_material_name, "trypan_blue");
  });

  test("detach clears the cursor flag and held material", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    store.set_cursor("micropipette", { attach: true, held_material_name: "trypan_blue" });
    deps.apply_cursor_attach({
      type: "CursorAttach",
      target: "micropipette",
      operation: "detach",
    });
    const flags = store.state["micropipette"].flags;
    assert.strictEqual(flags.cursor_attached, false);
    assert.strictEqual(flags.held_material_name, null);
  });
});

//============================================
// SceneChange reconciliation matrix
//============================================

describe("scene_op_deps SceneChange reconciliation matrix", () => {
  test("a shared target retains its declared scientific state", () => {
    const store = create_scene_store();
    seed_scene(store);
    // The next scene contains the same identity-bearing vessel.
    const deps = deps_with_next_scene(store, [{ target: "bme_tube", object_name: "bme_tube" }]);
    const schema = OBJECT_LIBRARY["bme_tube"].state_schema;
    const changed_name = schema["material_name"].allowed.find(
      (name) => name !== schema["material_name"].default,
    );
    if (changed_name === undefined) throw new Error("bme_tube needs an alternate material state");
    const changed_volume = schema["material_volume"].default === 0 ? 1 : 0;
    store.set_object_state("bme_tube", {
      material_name: changed_name,
      material_volume: changed_volume,
    });
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    assert.deepStrictEqual(
      {
        material_name: store.state["bme_tube"].state.material_name,
        material_volume: store.state["bme_tube"].state.material_volume,
      },
      {
        material_name: changed_name,
        material_volume: changed_volume,
      },
    );
  });

  test("a new target starts at defaults while absent targets are dropped", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = deps_with_next_scene(store, [
      { target: "well_plate_96.A1", object_name: "well_plate_96" },
    ]);
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    assert.strictEqual(store.state["centrifuge"], undefined);
    assert.strictEqual(
      store.state["well_plate_96.A1"].state.material_name,
      OBJECT_LIBRARY["well_plate_96"].subpart_state_schema["material_name"].default,
    );
  });

  test("cursor-held tool and material persist across SceneChange", () => {
    const store = create_scene_store();
    seed_scene(store);
    // The tool is placed in the NEXT scene too, so its cursor state can carry.
    const deps = deps_with_next_scene(store, [
      { target: "micropipette", object_name: "micropipette" },
    ]);
    store.set_cursor("micropipette", {
      attach: true,
      held_material_name: "trypan_blue",
      held_material_volume: 10,
    });
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    const flags = store.state["micropipette"].flags;
    assert.strictEqual(flags.cursor_attached, true);
    assert.strictEqual(flags.held_material_name, "trypan_blue");
    assert.strictEqual(flags.held_material_volume, 10);
  });

  test("selected flag clears on SceneChange", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = deps_with_next_scene(store, [{ target: "centrifuge", object_name: "centrifuge" }]);
    store.set_flags("centrifuge", { is_selected: true });
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    const flags = store.state["centrifuge"].flags;
    assert.strictEqual(flags.is_selected, false);
  });

  test("subpart state clears on leaving the scene", () => {
    // A subpart material write is registry-backed (D1): the store carries a
    // registry that registers the written material so acceptance passes. The
    // test's subject is destination membership, not material acceptance.
    const store = create_scene_store({
      media: { label: "Growth media", display_color: "#6c6c00" },
    });
    seed_scene(store);
    const deps = deps_with_next_scene(store, [{ target: "centrifuge", object_name: "centrifuge" }]);
    // Write a subpart in the current scene (auto-seeded).
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "conical_15ml_rack.slot_0",
      state: { material_name: "media" },
    });
    assert.strictEqual(store.state["conical_15ml_rack.slot_0"].state.material_name, "media");
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    // The subpart instance is gone after leaving the scene.
    assert.strictEqual(store.state["conical_15ml_rack.slot_0"], undefined);
  });

  test("a held tool absent from the next scene drops its cursor state", () => {
    const store = create_scene_store();
    seed_scene(store);
    // Next scene does NOT contain the micropipette.
    const deps = deps_with_next_scene(store, [{ target: "centrifuge", object_name: "centrifuge" }]);
    store.set_cursor("micropipette", { attach: true, held_material_name: "trypan_blue" });
    deps.apply_scene_change({ type: "SceneChange", to_scene: "next" });
    // micropipette is not in the new scene, so its cursor state cannot carry.
    assert.strictEqual(store.state["micropipette"], undefined);
  });
});

//============================================
// LayoutMove (unsupported: fail loud)
//============================================

describe("scene_op_deps LayoutMove", () => {
  test("LayoutMove throws instead of reporting false success", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    assert.throws(
      () => deps.apply_layout_move({ type: "LayoutMove", target: "centrifuge", zone: "mid" }),
      /no placement-override surface/,
    );
  });
});

//============================================
// TimedWait (runtime phase + injected scheduler)
//============================================

describe("scene_op_deps TimedWait", () => {
  test("TimedWait marks the target active and delegates scheduling", () => {
    const store = create_scene_store();
    seed_scene(store);
    const scheduled = [];
    const deps = build_store_scene_op_deps(
      store,
      () => {},
      (op) => scheduled.push(op),
    );
    const op = {
      type: "TimedWait",
      target: "centrifuge",
      duration_min: 0.05,
      display: "Centrifuging",
    };
    deps.start_timed_wait(op);
    assert.strictEqual(store.state["centrifuge"].flags.timed_wait_active, true);
    assert.strictEqual(store.state["centrifuge"].flags.timed_wait_display, "Centrifuging");
    assert.deepStrictEqual(scheduled, [op]);
  });

  test("TimedWait on an unseeded target fails loudly", () => {
    const store = create_scene_store();
    seed_scene(store);
    const deps = build_store_scene_op_deps(store, () => {});
    assert.throws(
      () =>
        deps.start_timed_wait({
          type: "TimedWait",
          target: "not_seeded_equipment",
          duration_min: 1,
        }),
      /not seeded/,
    );
  });
});
