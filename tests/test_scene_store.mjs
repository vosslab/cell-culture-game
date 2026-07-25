// tests/test_scene_store.mjs
//
// Node --test suite for the reactive scene store (WS-M2-S).
//
// Proves the behavioral contract:
//   - partial-merge writes at object level (one field changes, others hold)
//   - partial-merge writes at subpart level (e.g. rack.slot_0)
//   - subpart writes validate against the SUBPART schema, not the object one
//   - scene reconciliation preserves shared scientific state and resets flags
//   - cursor attach carries held material; detach clears it
//   - reset returns the store to empty
//   - an undeclared-key write throws (ObjectStateChange hard error)
//
// Real object names are used so the test exercises the generated schemas:
//   - "centrifuge": object-level "running" (bool) + "set_rpm" (float)
//   - "bme_tube": object-level "material_name" (enum) + "material_volume" (float)
//   - "conical_15ml_rack": subpart "material_name" (enum) + "material_volume" (float)

import { test, describe } from "node:test";
import assert from "node:assert";

import { createRoot, createSignal, createMemo } from "solid-js";

import { create_scene_store } from "../src/scene_runtime/state/scene_store.ts";
import { OBJECT_LIBRARY } from "../generated/object_library.js";

//============================================
// Reactive-build detection
//============================================
//
// Solid ships two builds. Under the browser/client build, createMemo tracks
// signal reads and recomputes on change. Under the SSR "server" build (which
// `node --import tsx` resolves by default via the package "node" export
// condition), createMemo is a non-tracking stub: it computes eagerly and never
// recomputes. The store reads/writes still work in both builds, so the
// distinct-value assertions below run everywhere; the fine-grained reactivity
// assertions only have meaning under the reactive build. We probe once at load
// and skip the reactivity sub-tests when running on the non-reactive build.
//
// To exercise the reactivity assertions, run node with the reactive build:
//   node --conditions=browser --import tsx --test tests/test_scene_store.mjs
function detect_solid_reactive() {
  let recomputed = false;
  createRoot((dispose) => {
    const [value, set_value] = createSignal(0);
    let runs = 0;
    const memo = createMemo(() => {
      runs += 1;
      return value();
    });
    // Force the initial compute, change the signal, then re-read.
    memo();
    set_value(1);
    memo();
    // The reactive build recomputes on the signal change; the server stub does not.
    recomputed = runs >= 2;
    dispose();
  });
  return recomputed;
}

const SOLID_REACTIVE = detect_solid_reactive();

//============================================
// Helpers
//============================================

// A small fixture registry. Subpart material_name acceptance is registry-backed
// (D1): a subpart write of a non-sentinel material is accepted only when that
// material is registered in the active protocol. The rack subpart tests register
// the cell/media names they write so the registry-backed gate accepts them; the
// two sentinels (empty, mixed) are always accepted with or without a registry.
const FIXTURE_REGISTRY = {
  cells: { label: "Seeded cells", display_color: "#cc0066" },
  media: { label: "Growth media", display_color: "#6c6c00" },
};

// Seed a store with the three fixture targets used across the suite. The
// rack uses a subpart suffix so subpart-schema validation is exercised. The
// store carries FIXTURE_REGISTRY so subpart material writes of cells/media pass
// the registry-backed D1 gate; object-level enum fields are unaffected.
function seeded_store() {
  const store = create_scene_store(FIXTURE_REGISTRY);
  store.seed_from_scene([
    { target: "centrifuge", object_name: "centrifuge" },
    { target: "bme_tube", object_name: "bme_tube" },
    { target: "conical_15ml_rack.slot_0", object_name: "conical_15ml_rack" },
  ]);
  return store;
}

//============================================
// Seeding
//============================================

describe("scene_store seeding", () => {
  test("seeds declared fields to their schema defaults", () => {
    const store = seeded_store();
    // Read the schema default so this assertion stays valid if the YAML default changes.
    const set_rpm_default = OBJECT_LIBRARY["centrifuge"].state_schema["set_rpm"].default;
    assert.strictEqual(store.state["centrifuge"].state.running, false);
    assert.notStrictEqual(store.state["centrifuge"].state.set_rpm, undefined);
    assert.strictEqual(store.state["centrifuge"].state.set_rpm, set_rpm_default);
  });

  test("records object_name and subpart for a subpart target", () => {
    const store = seeded_store();
    const entry = store.state["conical_15ml_rack.slot_0"];
    assert.strictEqual(entry.object_name, "conical_15ml_rack");
    assert.strictEqual(entry.subpart, "slot_0");
  });

  test("object target has a null subpart", () => {
    const store = seeded_store();
    assert.strictEqual(store.state["centrifuge"].subpart, null);
  });
});

//============================================
// Scene reconciliation
//============================================

describe("scene_store reconciliation", () => {
  test("preserves shared state while replacing membership and resetting flags", () => {
    const store = seeded_store();
    store.set_object_state("bme_tube", { material_name: "bme", material_volume: 2.5 });
    store.set_flags("bme_tube", { is_selected: true });

    store.reconcile_scene([
      { target: "bme_tube", object_name: "bme_tube" },
      { target: "micropipette", object_name: "micropipette" },
    ]);

    assert.strictEqual(store.state["bme_tube"].state.material_name, "bme");
    assert.strictEqual(store.state["bme_tube"].state.material_volume, 2.5);
    assert.strictEqual(store.state["bme_tube"].flags.is_selected, false);
    assert.notStrictEqual(store.state["micropipette"], undefined);
    assert.strictEqual(store.state["centrifuge"], undefined);
  });

  test("rejects a malformed destination without partially replacing the scene", () => {
    const store = seeded_store();
    store.set_object_state("centrifuge", { running: true });

    assert.throws(
      () =>
        store.reconcile_scene([
          { target: "bme_tube", object_name: "bme_tube" },
          { target: "centrifuge", object_name: "micropipette" },
        ]),
      /does not match declared object_name/,
    );

    assert.strictEqual(store.state["centrifuge"].state.running, true);
    assert.notStrictEqual(store.state["conical_15ml_rack.slot_0"], undefined);
    assert.strictEqual(store.state["micropipette"], undefined);
  });
});

//============================================
// Partial-merge writes (object level)
//============================================

describe("scene_store object-level partial merge", () => {
  test("writing one field leaves the others at their seeded value", () => {
    const store = seeded_store();
    // Write only set_rpm; running must stay at its default false.
    store.set_object_state("centrifuge", { set_rpm: 3000 });
    assert.strictEqual(store.state["centrifuge"].state.set_rpm, 3000);
    assert.strictEqual(store.state["centrifuge"].state.running, false);
  });

  test("a second write merges on top of the first", () => {
    const store = seeded_store();
    store.set_object_state("centrifuge", { set_rpm: 3000 });
    store.set_object_state("centrifuge", { running: true });
    // Both writes survive: merge, not replace.
    assert.strictEqual(store.state["centrifuge"].state.set_rpm, 3000);
    assert.strictEqual(store.state["centrifuge"].state.running, true);
  });

  test("material fields merge on a material container", () => {
    const store = seeded_store();
    const name_default = OBJECT_LIBRARY["bme_tube"].state_schema["material_name"].default;
    store.set_object_state("bme_tube", { material_volume: 2.5 });
    assert.strictEqual(store.state["bme_tube"].state.material_volume, 2.5);
    // material_name stays at its seeded default.
    assert.strictEqual(store.state["bme_tube"].state.material_name, name_default);
  });
});

//============================================
// Partial-merge writes (subpart level)
//============================================

describe("scene_store subpart-level partial merge", () => {
  test("writes a subpart field validated against the subpart schema", () => {
    const store = seeded_store();
    store.set_object_state("conical_15ml_rack.slot_0", { material_name: "cells" });
    const entry = store.state["conical_15ml_rack.slot_0"];
    assert.strictEqual(entry.state.material_name, "cells");
    // material_volume holds at the subpart default of 0.
    assert.strictEqual(entry.state.material_volume, 0);
  });

  test("subpart partial merge keeps prior subpart writes", () => {
    const store = seeded_store();
    store.set_object_state("conical_15ml_rack.slot_0", { material_name: "media" });
    store.set_object_state("conical_15ml_rack.slot_0", { material_volume: 12 });
    const entry = store.state["conical_15ml_rack.slot_0"];
    assert.strictEqual(entry.state.material_name, "media");
    assert.strictEqual(entry.state.material_volume, 12);
  });
});

//============================================
// Schema-level validation
//============================================

describe("scene_store schema validation", () => {
  test("undeclared key on an object target throws", () => {
    const store = seeded_store();
    assert.throws(
      () => store.set_object_state("centrifuge", { not_a_field: 1 }),
      /undeclared state key "not_a_field"/,
    );
  });

  test("undeclared key on a subpart target throws", () => {
    const store = seeded_store();
    // set_rpm is a valid OBJECT-level field on some objects but is NOT a
    // declared SUBPART field on the rack: subpart validation must reject it,
    // proving validation uses the subpart schema, not the object schema.
    assert.throws(
      () => store.set_object_state("conical_15ml_rack.slot_0", { set_rpm: 1000 }),
      /undeclared state key "set_rpm"/,
    );
  });

  test("a rejected write leaves the target state untouched", () => {
    const store = seeded_store();
    try {
      store.set_object_state("centrifuge", { running: true, bogus: 1 });
    } catch {
      // Expected: validation throws before any field is written.
    }
    // running must remain at its default because validation failed first.
    assert.strictEqual(store.state["centrifuge"].state.running, false);
  });

  test("a wrong-typed value throws", () => {
    const store = seeded_store();
    // set_rpm is a float; a string value must be rejected.
    assert.throws(
      () => store.set_object_state("centrifuge", { set_rpm: "fast" }),
      /expects number/,
    );
  });

  test("writing to an unseeded target throws", () => {
    const store = seeded_store();
    assert.throws(() => store.set_object_state("microscope", { x: 1 }), /not seeded/);
  });
});

//============================================
// Cursor attach / detach
//============================================

describe("scene_store cursor", () => {
  test("attach carries the held material", () => {
    const store = seeded_store();
    store.set_cursor("bme_tube", {
      attach: true,
      held_material_name: "bme",
      held_material_volume: 1.0,
    });
    const flags = store.state["bme_tube"].flags;
    assert.strictEqual(flags.cursor_attached, true);
    assert.strictEqual(flags.held_material_name, "bme");
    assert.strictEqual(flags.held_material_volume, 1.0);
  });

  test("detach clears the held material", () => {
    const store = seeded_store();
    store.set_cursor("bme_tube", { attach: true, held_material_name: "bme" });
    store.set_cursor("bme_tube", { attach: false });
    const flags = store.state["bme_tube"].flags;
    assert.strictEqual(flags.cursor_attached, false);
    assert.strictEqual(flags.held_material_name, null);
    assert.strictEqual(flags.held_material_volume, null);
  });
});

//============================================
// Reset
//============================================

describe("scene_store reset", () => {
  test("reset empties every seeded target", () => {
    const store = seeded_store();
    store.set_object_state("centrifuge", { running: true });
    store.reset();
    assert.strictEqual(store.state["centrifuge"], undefined);
    assert.strictEqual(store.state["bme_tube"], undefined);
  });

  test("the store is reusable after reset", () => {
    const store = seeded_store();
    store.reset();
    store.seed_from_scene([{ target: "centrifuge", object_name: "centrifuge" }]);
    assert.strictEqual(store.state["centrifuge"].state.running, false);
  });
});

//============================================
// seed_target (single-target insert, WS-M3-D)
//============================================

describe("scene_store seed_target", () => {
  test("adds a subpart instance without resetting siblings", () => {
    const store = seeded_store();
    // Mutate an existing object so we can prove it survives a later seed_target.
    store.set_object_state("centrifuge", { running: true });
    // Add a new subpart instance not present in the original seed list.
    store.seed_target({ target: "conical_15ml_rack.slot_1", object_name: "conical_15ml_rack" });
    // The new subpart exists at its defaults.
    assert.strictEqual(store.state["conical_15ml_rack.slot_1"].state.material_volume, 0);
    // The previously-mutated sibling is untouched.
    assert.strictEqual(store.state["centrifuge"].state.running, true);
  });

  test("seed_target is a no-op for an already-seeded target", () => {
    const store = seeded_store();
    store.set_object_state("bme_tube", { material_name: "bme" });
    // Re-seeding the same target must NOT reset its written state.
    store.seed_target({ target: "bme_tube", object_name: "bme_tube" });
    assert.strictEqual(store.state["bme_tube"].state.material_name, "bme");
  });
});

//============================================
// Enum membership validation (WS-M3-D)
//============================================

describe("scene_store enum membership", () => {
  test("an enum value outside the allowed set throws", () => {
    const store = seeded_store();
    // bme_tube.material_name allowed is ['empty', 'bme']; trypan_blue is not.
    assert.throws(
      () => store.set_object_state("bme_tube", { material_name: "trypan_blue" }),
      /not in allowed/,
    );
  });

  test("an enum value inside the allowed set is accepted", () => {
    const store = seeded_store();
    store.set_object_state("bme_tube", { material_name: "bme" });
    assert.strictEqual(store.state["bme_tube"].state.material_name, "bme");
  });

  test("a rejected enum write leaves the target untouched", () => {
    const store = seeded_store();
    const seeded_state = { ...store.state["bme_tube"].state };
    try {
      store.set_object_state("bme_tube", { material_name: "not_real" });
    } catch {
      // expected
    }
    assert.deepStrictEqual(store.state["bme_tube"].state, seeded_state);
  });
});

//============================================
// Registry-backed subpart material acceptance (D1, mirrors Python stepper)
//============================================
//
// A SUBPART material_name write is accepted when the value is a built-in
// (empty / mixed) OR a name registered in the active protocol's material
// registry -- NOT against the object's declared enum [empty, mixed] floor. This
// mirrors validation/stepper/state.py:mutate_state_field so a per-well drug write
// the stepper accepts also reaches the well at runtime. A registered drug is
// accepted and stored; an unregistered non-sentinel name is rejected; the two
// sentinels are accepted with or without a registry. The generic enum gate stays
// intact for non-material fields and for object-level material fields.

// Seed a single well of a plate with a registry that registers carboplatin.
function drug_registry_store() {
  const store = create_scene_store({
    carboplatin: { label: "Carboplatin solution", display_color: "#a719db" },
  });
  store.seed_from_scene([{ target: "well_plate_96.A1", object_name: "well_plate_96" }]);
  return store;
}

describe("scene_store registry-backed subpart material acceptance", () => {
  test("a registered drug is accepted and stored at a well subpart", () => {
    const store = drug_registry_store();
    // carboplatin is NOT in the object's declared [empty, mixed] floor, but it
    // is registered, so the registry-backed D1 gate accepts and stores it.
    store.set_object_state("well_plate_96.A1", { material_name: "carboplatin" });
    assert.strictEqual(
      store.getSubpartStateField("well_plate_96", "A1", "material_name"),
      "carboplatin",
    );
  });

  test("an unregistered non-sentinel material is rejected at a well subpart", () => {
    const store = drug_registry_store();
    // metformin is neither a built-in nor registered in this store: reject.
    assert.throws(
      () => store.set_object_state("well_plate_96.A1", { material_name: "metformin" }),
      /not registered in the active protocol material registry/,
    );
    // The rejected write left the well at its seeded default.
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "material_name"), "empty");
  });

  test("the sentinels empty and mixed are accepted at a well subpart", () => {
    const store = drug_registry_store();
    store.set_object_state("well_plate_96.A1", { material_name: "mixed" });
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "material_name"), "mixed");
    store.set_object_state("well_plate_96.A1", { material_name: "empty" });
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "material_name"), "empty");
  });

  test("a non-material enum field still rejects an out-of-enum value", () => {
    // Generic enum validation is intact: inspection_status is an object-level
    // enum [not_inspected, cells_healthy] on well_plate_96; a value outside it
    // throws through the same generic gate, not the material predicate.
    const store = create_scene_store();
    store.seed_from_scene([{ target: "well_plate_96", object_name: "well_plate_96" }]);
    assert.throws(
      () => store.set_object_state("well_plate_96", { inspection_status: "not_a_status" }),
      /not in allowed/,
    );
  });

  test("a subpart drug write is rejected when there is no registry", () => {
    // With a null registry (diagnostic context) only the built-ins pass, exactly
    // as the Python stepper rejects a non-sentinel against an empty registry.
    const store = create_scene_store();
    store.seed_from_scene([{ target: "well_plate_96.A1", object_name: "well_plate_96" }]);
    assert.throws(
      () => store.set_object_state("well_plate_96.A1", { material_name: "carboplatin" }),
      /not registered in the active protocol material registry/,
    );
  });
});

//============================================
// getSubpartStateField (narrow reactive read, WS-M3-STORE)
//============================================
//
// Fixture scene: a 96-well plate with two wells, A1 and A2, seeded as separate
// subpart targets. The structured-subpart renderer (M3 #19) reads each well's
// material state independently through getSubpartStateField(placementId,
// subpartName, fieldName). well_plate_96 declares subpart fields material_name
// (enum: empty|mixed) and material_volume (float, ul). A1 and A2 are loaded
// with DIFFERENT material states so the accessor must return distinct values
// and update reactively per well.

// Seed a plate fixture with two wells (A1, A2) at their subpart defaults.
function plate_fixture_store() {
  const store = create_scene_store();
  store.seed_from_scene([
    { target: "well_plate_96.A1", object_name: "well_plate_96" },
    { target: "well_plate_96.A2", object_name: "well_plate_96" },
  ]);
  return store;
}

describe("scene_store getSubpartStateField", () => {
  test("A1 and A2 return distinct material states after divergent writes", () => {
    const store = plate_fixture_store();
    // Load the two wells with different material states.
    store.set_object_state("well_plate_96.A1", { material_name: "mixed", material_volume: 100 });
    store.set_object_state("well_plate_96.A2", { material_name: "empty", material_volume: 0 });
    // The narrow accessor reads each well's field independently.
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "material_name"), "mixed");
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A2", "material_name"), "empty");
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "material_volume"), 100);
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A2", "material_volume"), 0);
  });

  test("returns undefined for an unseeded subpart", () => {
    const store = plate_fixture_store();
    // A3 was never seeded; the accessor reports absence rather than throwing.
    assert.strictEqual(
      store.getSubpartStateField("well_plate_96", "A3", "material_name"),
      undefined,
    );
  });

  test("returns undefined for a field not on the subpart", () => {
    const store = plate_fixture_store();
    // set_rpm is not a well subpart field; reading it yields undefined.
    assert.strictEqual(store.getSubpartStateField("well_plate_96", "A1", "set_rpm"), undefined);
  });

  test("A1 and A2 memos track fine-grained and independently", { skip: !SOLID_REACTIVE }, () => {
    createRoot((dispose) => {
      const store = plate_fixture_store();
      // Count recomputations of a memo over each well's material_name.
      let a1_runs = 0;
      let a2_runs = 0;
      const a1_name = createMemo(() => {
        a1_runs += 1;
        return store.getSubpartStateField("well_plate_96", "A1", "material_name");
      });
      const a2_name = createMemo(() => {
        a2_runs += 1;
        return store.getSubpartStateField("well_plate_96", "A2", "material_name");
      });
      // Force initial computation; both start at the seeded default.
      assert.strictEqual(a1_name(), "empty");
      assert.strictEqual(a2_name(), "empty");
      assert.strictEqual(a1_runs, 1);
      assert.strictEqual(a2_runs, 1);

      // Write A1 only. The A1 memo must recompute to the new value; the A2 memo
      // must NOT recompute, proving fine-grained per-subpart subscription.
      store.set_object_state("well_plate_96.A1", { material_name: "mixed" });
      assert.strictEqual(a1_name(), "mixed");
      assert.strictEqual(a2_name(), "empty");
      assert.strictEqual(a1_runs, 2);
      assert.strictEqual(a2_runs, 1);

      // Now write A2 only. Symmetric result: A2 recomputes, A1 stays put.
      store.set_object_state("well_plate_96.A2", { material_name: "mixed" });
      assert.strictEqual(a1_name(), "mixed");
      assert.strictEqual(a2_name(), "mixed");
      assert.strictEqual(a1_runs, 2);
      assert.strictEqual(a2_runs, 2);

      dispose();
    });
  });

  test(
    "a read of an unseeded subpart becomes visible after a later seed+write",
    {
      skip: !SOLID_REACTIVE,
    },
    () => {
      createRoot((dispose) => {
        const store = plate_fixture_store();
        let runs = 0;
        const a5_name = createMemo(() => {
          runs += 1;
          return store.getSubpartStateField("well_plate_96", "A5", "material_name");
        });
        // A5 is not seeded yet: the reactive read subscribes to the empty slot.
        assert.strictEqual(a5_name(), undefined);
        assert.strictEqual(runs, 1);
        // Seed A5 and write it; the memo must recompute and pick up the value.
        store.seed_target({ target: "well_plate_96.A5", object_name: "well_plate_96" });
        store.set_object_state("well_plate_96.A5", { material_name: "mixed" });
        assert.strictEqual(a5_name(), "mixed");
        assert.ok(runs >= 2);
        dispose();
      });
    },
  );
});
