// tests/test_load_time_scene_invariants.mjs
//
// Node --test suite for the two load-time scene invariants added beside the
// M16-D target-existence check in create_step_machine:
//   - Invariant 1: reject an ambiguous interaction target (an object placed
//     more than once in the active scene) -> AmbiguousAuthoredTargetError.
//   - Invariant 2: reject a store-writing scene operation target that is not
//     seeded in the active scene -> UnseededSceneOperationTargetError, with the
//     narrowed held-tool exemption.
//
// Configs are constructed inline in each test body (repo no-fixtures rule); the
// scene adapter is built from an inline placement list via build_target_adapter,
// so ambiguity and seeded-ness are controlled per case.

import { test, describe } from "node:test";
import assert from "node:assert";

import { createProtocolShellEmitter } from "../src/scene_runtime/protocol/emitter.ts";
import {
  create_step_machine,
  initial_snapshot,
  create_snapshot_reducer,
} from "../src/scene_runtime/protocol/step_machine.ts";
import { build_target_adapter } from "../src/scene_runtime/protocol/target_adapter.ts";
import {
  AmbiguousAuthoredTargetError,
  UnseededSceneOperationTargetError,
  UnknownAuthoredSubpartTargetError,
} from "../src/scene_runtime/protocol/target_existence_check.ts";

//============================================
// Inline builders
//============================================

// A single-step, single-interaction mini_protocol. The interaction clicks
// `target`; `scene_operations` is the authored response op list under test.
function make_config(target, scene_operations) {
  return {
    protocol_name: "test_proto",
    protocol_type: "mini_protocol",
    entry_step: "step_a",
    steps: [
      {
        step_name: "step_a",
        prompt: `Click ${target}`,
        sequence: [
          {
            target,
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ],
  };
}

// Construct a step machine (runs all load-time checks) against a scene adapter
// built from `bindings`. Wrapped in a thunk so a test can assert it throws or
// does not throw at construction time.
function construct(config, bindings) {
  const adapter = build_target_adapter(bindings);
  const start_snapshot = initial_snapshot(config.protocol_name);
  const reducer = create_snapshot_reducer(config);
  const emitter = createProtocolShellEmitter(start_snapshot, reducer);
  return () =>
    create_step_machine(config, emitter, () => {}, {
      lookup_state_field: () => ({ kind: "typed", field_type: "int" }),
      read_object_state: () => ({}),
      target_adapter: adapter,
    });
}

//============================================
// Invariant 1: ambiguous interaction target
//============================================

describe("load-time invariant: ambiguous interaction target", () => {
  test("throws when the interaction target is placed more than once", () => {
    const cfg = make_config("obj_x", []);
    const bindings = [
      { object_name: "obj_x", placement_name: "p1" },
      { object_name: "obj_x", placement_name: "p2" },
    ];
    assert.throws(construct(cfg, bindings), AmbiguousAuthoredTargetError);
  });

  test("does not throw when the interaction target is placed once", () => {
    const cfg = make_config("obj_x", []);
    const bindings = [{ object_name: "obj_x", placement_name: "p1" }];
    assert.doesNotThrow(construct(cfg, bindings));
  });

  test("does not throw when a specific placement_name disambiguates", () => {
    const cfg = make_config("p1", []);
    const bindings = [
      { object_name: "obj_x", placement_name: "p1" },
      { object_name: "obj_x", placement_name: "p2" },
    ];
    assert.doesNotThrow(construct(cfg, bindings));
  });
});

//============================================
// Invariant 2: scene-op target must be seeded
//============================================

describe("load-time invariant: scene-op target seeded", () => {
  test("throws when an ObjectStateChange target is not seeded in the scene", () => {
    const cfg = make_config("clicker", [
      { type: "ObjectStateChange", target: "ghost", state: { open: true } },
    ]);
    const bindings = [{ object_name: "clicker", placement_name: "clicker" }];
    assert.throws(construct(cfg, bindings), UnseededSceneOperationTargetError);
  });

  test("does not throw when the ObjectStateChange target is seeded", () => {
    const cfg = make_config("clicker", [
      { type: "ObjectStateChange", target: "tube", state: { open: true } },
    ]);
    const bindings = [
      { object_name: "clicker", placement_name: "clicker" },
      { object_name: "tube", placement_name: "tube" },
    ];
    assert.doesNotThrow(construct(cfg, bindings));
  });

  test("exempts a held-only tool that is never state-mutated", () => {
    // pipette is cursor-attached and NOT seeded in the scene, but never an
    // ObjectStateChange subject, so it renders via the tray overlay and is exempt.
    const cfg = make_config("clicker", [
      { type: "CursorAttach", target: "pipette", operation: "attach" },
    ]);
    const bindings = [{ object_name: "clicker", placement_name: "clicker" }];
    assert.doesNotThrow(construct(cfg, bindings));
  });

  test("does NOT exempt a held tool that is also an ObjectStateChange subject", () => {
    // Mirrors passage_pellet_reseed's conical_15ml: the object is cursor-attached
    // AND state-mutated in a scene where it is not seeded, so it must fail loud.
    const cfg = make_config("clicker", [
      { type: "ObjectStateChange", target: "conical", state: { volume: 5 } },
      { type: "CursorAttach", target: "conical", operation: "attach" },
    ]);
    const bindings = [{ object_name: "clicker", placement_name: "clicker" }];
    assert.throws(construct(cfg, bindings), UnseededSceneOperationTargetError);
  });
});

//============================================
// Invariant 3: subpart suffix must be declared
//============================================

// These use the real well_plate_96 object (declares 96 well subparts and the
// all_wells / row_* / col_* / block_* subpart_groups) so the suffix check reads
// the generated declared vocabulary, not an inline stub.
describe("load-time invariant: subpart suffix declared", () => {
  test("does not throw for a declared subpart_group write (all_wells)", () => {
    const cfg = make_config("well_plate_96", [
      {
        type: "ObjectStateChange",
        target: "well_plate_96.all_wells",
        state: { material_name: "mixed", material_volume: 100 },
      },
    ]);
    const bindings = [{ object_name: "well_plate_96", placement_name: "plate1" }];
    assert.doesNotThrow(construct(cfg, bindings));
  });

  test("does not throw for a declared single subpart write (A1)", () => {
    const cfg = make_config("well_plate_96", [
      {
        type: "ObjectStateChange",
        target: "well_plate_96.A1",
        state: { material_name: "mixed", material_volume: 25 },
      },
    ]);
    const bindings = [{ object_name: "well_plate_96", placement_name: "plate1" }];
    assert.doesNotThrow(construct(cfg, bindings));
  });

  test("throws for an undeclared subpart_group write", () => {
    const cfg = make_config("well_plate_96", [
      {
        type: "ObjectStateChange",
        target: "well_plate_96.every_single_well",
        state: { material_name: "mixed" },
      },
    ]);
    const bindings = [{ object_name: "well_plate_96", placement_name: "plate1" }];
    assert.throws(construct(cfg, bindings), UnknownAuthoredSubpartTargetError);
  });

  test("throws for an undeclared subpart on the interaction target", () => {
    const cfg = make_config("well_plate_96.Z99", []);
    const bindings = [{ object_name: "well_plate_96", placement_name: "plate1" }];
    assert.throws(construct(cfg, bindings), UnknownAuthoredSubpartTargetError);
  });
});
