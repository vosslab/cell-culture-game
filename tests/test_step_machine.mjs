// tests/test_step_machine.mjs
//
// Node --test suite for the protocol step machine.
// Covers start, click happy path, wrong_target rejection, step
// completion + next_step transition, terminal step + no_active_step,
// retry path, modal_close (correct_choice), and snapshot reducer.

import { test, describe } from "node:test";
import assert from "node:assert";

import { createProtocolShellEmitter } from "../src/scene_runtime/protocol/emitter.ts";
import {
  create_step_machine,
  initial_snapshot,
  create_snapshot_reducer,
} from "../src/scene_runtime/protocol/step_machine.ts";
import { UnaffordancedGestureError } from "../src/scene_runtime/protocol/gesture_affordance_check.ts";
import {
  UnknownAuthoredTargetError,
  UnseededSceneOperationTargetError,
} from "../src/scene_runtime/protocol/target_existence_check.ts";
import {
  StepCountClaimMismatchError,
  PromptTargetDriftError,
} from "../src/scene_runtime/protocol/pedagogy_consistency_check.ts";
import { build_target_adapter } from "../src/scene_runtime/protocol/target_adapter.ts";

//============================================
// Fixture builders
//============================================

function make_click_step(name, target, next_step) {
  return {
    step_name: name,
    prompt: `Click ${target}`,
    sequence: [
      {
        target,
        gesture: "click",
        validator: { preset: "correct_target" },
        response: { scene_operations: [] },
      },
    ],
    step_validator: { preset: "sequence_complete" },
    outcome: { on_success: "complete", on_failure: "retry" },
    next_step,
  };
}

function make_two_click_step(name, t1, t2, next_step) {
  return {
    step_name: name,
    prompt: "Click two things",
    sequence: [
      {
        target: t1,
        gesture: "click",
        validator: { preset: "correct_target" },
        response: {
          scene_operations: [{ type: "SceneChange", to_scene: "scene_b" }],
        },
      },
      {
        target: t2,
        gesture: "click",
        validator: { preset: "correct_target" },
        response: { scene_operations: [] },
      },
    ],
    step_validator: { preset: "sequence_complete" },
    outcome: { on_success: "complete", on_failure: "retry" },
    next_step,
  };
}

function make_config(steps, entry_step) {
  return {
    protocol_name: "test_proto",
    protocol_type: "mini_protocol",
    entry_step,
    steps,
  };
}

// Stub lookup for the M1B-2 seam. These existing tests do not target the
// load-time value pass (WP-TEST adds those). The pass is now live (WP-CHECK),
// so the stub must report a RESOLVED field, not an unknown reference: every
// authored value in these fixtures is numeric, so a typed int result accepts
// them without coupling these tests to real object schemas. Returning
// unknown_object here would wrongly fail-load every mini_protocol fixture.
function stub_lookup_state_field() {
  return { kind: "typed", field_type: "int" };
}

// observed_state seeds the read_object_state seam: a {target: {field: value}}
// map of the LIVE scene-store state the click path and final_state_matches
// snapshot read. Defaults to empty (no observed state). target_with_value and
// final_state_matches now judge against this observed state, not the authored
// expected values, so a case that expects a match seeds the matching state here.
function build_harness(config, observed_state = {}) {
  const events = [];
  const scene_ops = [];
  const start_snapshot = initial_snapshot(config.protocol_name);
  const reducer = create_snapshot_reducer(config);
  const emitter = createProtocolShellEmitter(start_snapshot, reducer);
  emitter.subscribe((event) => events.push(event));
  const machine = create_step_machine(config, emitter, (op) => scene_ops.push(op), {
    lookup_state_field: stub_lookup_state_field,
    read_object_state: (target) => observed_state[target] ?? {},
  });
  return { machine, events, scene_ops, emitter };
}

function kinds(events) {
  return events.map((e) => e.kind);
}

//============================================
// Tests
//============================================

describe("step machine - start", () => {
  test("emits protocol_loaded then step_started for entry_step", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const k = kinds(events);
    assert.strictEqual(k[0], "protocol_loaded");
    assert.strictEqual(k[1], "step_started");
    const loaded = events[0];
    assert.strictEqual(loaded.entry_step_name, "a");
    assert.strictEqual(loaded.total_step_count, 1);
    assert.strictEqual(events[1].step_name, "a");
  });
});

describe("step machine - happy path click", () => {
  test("validated click advances interaction_index and emits interaction_validated", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.target_name, "t1");
    assert.strictEqual(validated.interaction_index, 0);
    assert.strictEqual(emitter.get_snapshot().current_interaction_index, 1);
  });

  test("scene_operation_applied and scene_changed fire for SceneChange op", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, events, scene_ops } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    assert.strictEqual(scene_ops.length, 1);
    assert.strictEqual(scene_ops[0].type, "SceneChange");
    const k = kinds(events);
    assert.ok(k.includes("scene_operation_applied"));
    assert.ok(k.includes("scene_changed"));
  });
});

describe("step machine - TimedWait sequencing", () => {
  test("pauses at TimedWait and resumes later operations exactly once", () => {
    const step = make_click_step("wait", "centrifuge", null);
    step.sequence[0].response.scene_operations = [
      {
        type: "TimedWait",
        target: "centrifuge",
        duration_min: 1,
        display: "Centrifuging",
      },
      {
        type: "ObjectStateChange",
        target: "centrifuge",
        state: { running: false },
      },
    ];
    const { machine, events, scene_ops, emitter } = build_harness(make_config([step], "wait"));

    machine.start();
    machine.handle_click("centrifuge", "click");

    assert.deepStrictEqual(
      scene_ops.map((op) => op.type),
      ["TimedWait"],
    );
    // The interaction validator has fired, so the read-only shell snapshot may
    // project the next interaction index; step completion remains blocked until
    // the timed phase elapses.
    assert.strictEqual(emitter.get_snapshot().is_complete, false);

    machine.handle_click("centrifuge", "click");
    assert.strictEqual(events.at(-1).kind, "interaction_rejected");
    assert.strictEqual(events.at(-1).reason_code, "out_of_order");

    machine.handle_timer_elapsed("other_equipment");
    assert.deepStrictEqual(
      scene_ops.map((op) => op.type),
      ["TimedWait"],
    );

    machine.handle_timer_elapsed("centrifuge");
    assert.deepStrictEqual(
      scene_ops.map((op) => op.type),
      ["TimedWait", "ObjectStateChange"],
    );
    assert.strictEqual(emitter.get_snapshot().is_complete, true);
    assert.strictEqual(events.filter((event) => event.kind === "interaction_validated").length, 1);
  });
});

describe("step machine - wrong target", () => {
  test("emits interaction_rejected with reason wrong_target; no advance", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("oops", "click");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
    assert.strictEqual(emitter.get_snapshot().current_interaction_index, 0);
    // No interaction_validated should have fired.
    assert.ok(!events.some((e) => e.kind === "interaction_validated"));
  });

  test("a correct interaction clears an earlier rejection within the same step", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("oops", "click");
    assert.ok(emitter.get_snapshot().last_rejection);

    machine.handle_click("t1", "click");
    assert.strictEqual(emitter.get_snapshot().last_rejection, null);
  });
});

describe("step machine - step completion and next_step", () => {
  test("all interactions validated -> step_completed complete + next step_started", () => {
    const cfg = make_config(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
    );
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_click("obj_a", "click");
    const completed = events.find((e) => e.kind === "step_completed" && e.step_name === "a");
    assert.ok(completed);
    assert.strictEqual(completed.resolution, "complete");
    // step_started for "b" must follow.
    const started_b = events.find((e) => e.kind === "step_started" && e.step_name === "b");
    assert.ok(started_b);
  });

  test("starting the next step clears the previous outcome and rejection", () => {
    const cfg = make_config(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
    );
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("not_obj_a", "click");
    assert.ok(emitter.get_snapshot().last_rejection);

    machine.handle_click("obj_a", "click");
    const snapshot = emitter.get_snapshot();
    assert.deepStrictEqual(
      [snapshot.current_step_name, snapshot.last_outcome, snapshot.last_rejection],
      ["b", null, null],
    );
  });
});

describe("step machine - step-entry scene render (sequence_runner boundary)", () => {
  // A step declaring a scene different from the current one transitions to it on
  // entry, BEFORE step_started, so the step's first target is visible. This is
  // the mechanism that plays sequence_runner mini-protocol boundaries.
  function make_scene_click_step(name, target, scene, next_step) {
    const step = make_click_step(name, target, next_step);
    return { ...step, scene };
  }

  function build_scene_harness(config, initial_scene) {
    const events = [];
    const scene_ops = [];
    const start_snapshot = initial_snapshot(config.protocol_name);
    const reducer = create_snapshot_reducer(config);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    emitter.subscribe((event) => events.push(event));
    const machine = create_step_machine(config, emitter, (op) => scene_ops.push(op), {
      lookup_state_field: stub_lookup_state_field,
      read_object_state: () => ({}),
      initial_scene,
    });
    return { machine, events, scene_ops };
  }

  test("entry step whose scene equals initial_scene emits no SceneChange", () => {
    const cfg = make_config([make_scene_click_step("a", "obj_a", "scene_a", null)], "a");
    const { machine, scene_ops } = build_scene_harness(cfg, "scene_a");
    machine.start();
    assert.strictEqual(scene_ops.length, 0);
  });

  test("entering a step with a new scene renders it before step_started", () => {
    const cfg = make_config(
      [
        make_scene_click_step("a", "obj_a", "scene_a", "b"),
        make_scene_click_step("b", "obj_b", "scene_c", null),
      ],
      "a",
    );
    const { machine, events, scene_ops } = build_scene_harness(cfg, "scene_a");
    machine.start();
    // Entry step a matches initial scene: no scene op yet.
    assert.strictEqual(scene_ops.length, 0);
    // Complete step a; entering step b must render scene_c (its scene differs).
    machine.handle_click("obj_a", "click");
    const scene_change = scene_ops.find((op) => op.type === "SceneChange");
    assert.ok(scene_change, "a SceneChange op should fire on entering step b");
    assert.strictEqual(scene_change.to_scene, "scene_c");
    // The scene_changed event must precede step_started for b so the adapter is
    // rebound before the active interaction is derived.
    const scene_changed_idx = events.findIndex(
      (e) => e.kind === "scene_changed" && e.to_scene === "scene_c",
    );
    const started_b_idx = events.findIndex((e) => e.kind === "step_started" && e.step_name === "b");
    assert.ok(scene_changed_idx >= 0 && started_b_idx >= 0);
    assert.ok(scene_changed_idx < started_b_idx);
  });
});

describe("step machine - same-step SceneChange re-resolves active target", () => {
  // Regression: mtt_solubilization_readout read_absorbance. A step's first
  // interaction carries a SceneChange in its response; the NEXT interaction in
  // the same step names a semantic target that resolves to a DIFFERENT placement
  // in the new scene. Before the fix, active_interaction_target was resolved
  // against the OLD scene's adapter by interaction_validated and never
  // re-resolved after the scene swapped, so the follow-on commit was scored
  // against the stale old-scene placement and rejected as out-of-order. The
  // reducer's scene_changed case now re-resolves the active target against the
  // newly-mounted scene.

  // Two-interaction step: interaction 0 clicks the semantic target and its
  // response changes the scene; interaction 1 acts (adjust) on the SAME semantic
  // target, which the scene-aware resolver maps to a new placement in scene_b.
  function make_scene_change_then_adjust_step(name) {
    return {
      step_name: name,
      prompt: "click then adjust across a scene change",
      sequence: [
        {
          target: "plate_reader",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: {
            scene_operations: [{ type: "SceneChange", to_scene: "scene_b" }],
          },
        },
        {
          target: "plate_reader",
          gesture: "adjust",
          validator: { preset: "target_with_value", value: { wavelength_nm: 560 } },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("active_interaction_target follows the new scene's placement after a same-step SceneChange", () => {
    const cfg = make_config([make_scene_change_then_adjust_step("read")], "read");

    // Real per-scene adapters, one placement per scene for the same object, built
    // the same way protocol_host builds them. The live adapter swaps on the scene
    // change, exactly like protocol_host's current_adapter.
    const adapter_scene_a = build_target_adapter([
      { object_name: "plate_reader", placement_name: "rear_right_plate_reader" },
    ]);
    const adapter_scene_b = build_target_adapter([
      { object_name: "plate_reader", placement_name: "center_plate_reader" },
    ]);
    const adapters = { scene_a: adapter_scene_a, scene_b: adapter_scene_b };
    // Mutable live-adapter ref, mirroring protocol_host's current_adapter swap.
    let current_adapter = adapter_scene_a;

    // In protocol_host the equality adapter and the reducer resolver both delegate
    // to the one live per-scene adapter, so they always agree. Mirror that: a
    // stable delegating wrapper reads current_adapter on every call.
    const scene_aware_adapter = {
      resolve_to_placement: (target) => current_adapter.resolve_to_placement(target),
      resolve_to_object: (target) => current_adapter.resolve_to_object(target),
      has_target: (target) => current_adapter.has_target(target),
      placements_for: (target) => current_adapter.placements_for(target),
    };

    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg, (target) =>
      current_adapter.resolve_to_placement(target),
    );
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);

    // Scene op handler swaps the live adapter BEFORE the scene_changed event fires,
    // matching apply_response_scene_ops (handler runs, then scene_changed emits).
    const scene_op_handler = (op) => {
      if (op.type === "SceneChange") {
        current_adapter = adapters[op.to_scene] ?? current_adapter;
      }
    };
    // Per-scene resolver for the load-time target-existence invariant.
    const resolve_scene_target_adapter = (name) => adapters[name];
    const machine = create_step_machine(cfg, emitter, scene_op_handler, {
      lookup_state_field: stub_lookup_state_field,
      read_object_state: () => ({}),
      target_adapter: scene_aware_adapter,
      resolve_scene_target_adapter,
      initial_scene: "scene_a",
    });

    machine.start();
    // At entry, the active interaction is interaction 0 in scene_a.
    assert.strictEqual(emitter.get_snapshot().active_interaction_target, "rear_right_plate_reader");

    // Validate interaction 0: this advances to interaction 1 AND runs the
    // SceneChange. The active target for interaction 1 must now be resolved
    // against scene_b, not the stale scene_a placement.
    machine.handle_click("rear_right_plate_reader", "click");

    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_scene_name, "scene_b");
    assert.strictEqual(snap.current_interaction_index, 1);
    assert.strictEqual(snap.active_interaction_gesture, "adjust");
    // The fix: active_interaction_target re-resolved against scene_b.
    assert.strictEqual(snap.active_interaction_target, "center_plate_reader");
  });
});

describe("step machine - terminal step + protocol_completed", () => {
  test("emits protocol_completed; subsequent clicks emit no_active_step", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("obj_a", "click");
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
    assert.strictEqual(emitter.get_snapshot().is_complete, true);

    const before = events.length;
    machine.handle_click("obj_a", "click");
    const new_events = events.slice(before);
    const rejected = new_events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "no_active_step");
  });
});

describe("step machine - retry path", () => {
  test("step_validator fail -> step_completed(retry) + interaction_index resets", () => {
    // Use final_state_matches with empty snapshot to force false.
    const step = {
      step_name: "a",
      prompt: "go",
      sequence: [
        {
          target: "t1",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: {
        preset: "final_state_matches",
        value: { some_obj: { field: "expected" } },
      },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([step], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    const completed = events.filter((e) => e.kind === "step_completed");
    assert.ok(completed.length >= 1);
    assert.strictEqual(completed[0].resolution, "retry");
    // Sequence restarts: a second step_started for "a".
    const started_a = events.filter((e) => e.kind === "step_started" && e.step_name === "a");
    assert.ok(started_a.length >= 2);
    assert.strictEqual(emitter.get_snapshot().current_interaction_index, 0);
  });
});

describe("step machine - select chooses the next-step object (correct_choice)", () => {
  // Corrected semantics (WS-M5-ST): a `select` interaction validated by
  // correct_choice means "the student chose the correct next-step object among
  // the present scene objects". It is driven through the same visible-click path
  // (handle_click) with the select gesture; target-equality decides.
  function make_select_step() {
    return {
      step_name: "a",
      prompt: "pick the plate",
      sequence: [
        {
          target: "treatment_plate",
          gesture: "select",
          validator: { preset: "correct_choice" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("selecting the correct object validates and completes", () => {
    const cfg = make_config([make_select_step()], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_click("treatment_plate", "select");
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.gesture, "select");
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
  });

  test("selecting a wrong present object rejects and does not advance", () => {
    const cfg = make_config([make_select_step()], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("waste_beaker", "select");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
    assert.strictEqual(emitter.get_snapshot().current_step_name, "a");
  });
});

describe("step machine - type commit (target_with_value)", () => {
  // A `type` interaction asks the student to enter a value. handle_type_commit
  // takes the raw typed text, coerces it to the validator's declared field type,
  // and validates via target_with_value.
  function make_type_step() {
    return {
      step_name: "a",
      prompt: "enter the count",
      sequence: [
        {
          target: "cell_counter",
          gesture: "type",
          validator: { preset: "target_with_value", value: { entered_count: 42 } },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("committing the correct typed value validates and completes", () => {
    const cfg = make_config([make_type_step()], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_type_commit("cell_counter", "42");
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.gesture, "type");
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
  });

  test("committing a wrong typed value rejects and does not advance", () => {
    const cfg = make_config([make_type_step()], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_type_commit("cell_counter", "13");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_value");
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
  });

  test("committing on a non-type interaction rejects with wrong_target", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_type_commit("obj_a", "anything");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
  });
});

describe("step machine - adjust commit (target_with_value)", () => {
  // An `adjust` interaction asks the student to set a numeric set-point.
  // handle_adjust_commit takes the committed number, coerces it to the declared
  // field type, and validates via target_with_value (same path as type).
  function make_adjust_step(field, expected) {
    return {
      step_name: "a",
      prompt: "set the volume",
      sequence: [
        {
          target: "micropipette",
          gesture: "adjust",
          validator: { preset: "target_with_value", value: { [field]: expected } },
          response: {
            scene_operations: [
              { type: "ObjectStateChange", target: "micropipette", state: { [field]: expected } },
            ],
          },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("committing the correct set-point validates and completes", () => {
    const cfg = make_config([make_adjust_step("set_volume", 1000)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_adjust_commit("micropipette", 1000);
    assert.strictEqual(ok, true);
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.gesture, "adjust");
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
  });

  test("committing a wrong set-point rejects and does not advance", () => {
    const cfg = make_config([make_adjust_step("set_volume", 1000)], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_adjust_commit("micropipette", 500);
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_value");
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
  });

  test("a float set-point is preserved, not truncated (declared-type coercion)", () => {
    // A hard-coded numeric (parseInt) coercion would truncate 3.5 to 3 and fail.
    // Committing the exact float must be accepted, proving the coercion follows
    // the field's declared/authored type instead of an integer default.
    const cfg = make_config([make_adjust_step("set_voltage", 3.5)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_adjust_commit("micropipette", 3.5);
    assert.strictEqual(ok, true);
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
  });

  test("a truncated float set-point rejects (3 != 3.5)", () => {
    const cfg = make_config([make_adjust_step("set_voltage", 3.5)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_adjust_commit("micropipette", 3);
    assert.strictEqual(ok, false);
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
  });

  test("committing on a non-adjust interaction rejects with wrong_target", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_adjust_commit("obj_a", 1);
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
  });
});

describe("step machine - drag commit", () => {
  // A `drag` interaction moves a source scene object to a destination. The
  // destination is derived from the interaction response's first LayoutMove.zone
  // (no new authored field). handle_drag_commit checks source + destination, then
  // applies the response and advances.
  function make_drag_step(withLayoutMove = true) {
    const scene_operations = withLayoutMove
      ? [{ type: "LayoutMove", target: "source_obj", zone: "dest_zone" }]
      : [];
    return {
      step_name: "a",
      prompt: "drag the object",
      sequence: [
        {
          target: "source_obj",
          gesture: "drag",
          validator: { preset: "correct_target" },
          response: { scene_operations },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("dragging the source onto the authored destination validates and completes", () => {
    const cfg = make_config([make_drag_step()], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_drag_commit("source_obj", "dest_zone");
    assert.strictEqual(ok, true);
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.gesture, "drag");
    const done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(done);
  });

  test("dragging onto a wrong destination rejects with wrong_value", () => {
    const cfg = make_config([make_drag_step()], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_drag_commit("source_obj", "wrong_zone");
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_value");
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
  });

  test("dragging a wrong source rejects with wrong_target", () => {
    const cfg = make_config([make_drag_step()], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_drag_commit("wrong_source", "dest_zone");
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
  });

  test("a drag interaction with no authored destination rejects with wrong_value", () => {
    const cfg = make_config([make_drag_step(false)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_drag_commit("source_obj", "dest_zone");
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_value");
  });

  test("committing a drag on a non-drag interaction rejects with wrong_target", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    const ok = machine.handle_drag_commit("obj_a", "dest_zone");
    assert.strictEqual(ok, false);
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
  });
});

describe("step machine - reducer snapshot derivation", () => {
  function two_step_harness() {
    const cfg = make_config(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
    );
    return build_harness(cfg);
  }

  test("opening a protocol exposes its first learner step", () => {
    const { machine, emitter } = two_step_harness();
    machine.start();
    const snapshot = emitter.get_snapshot();

    assert.deepStrictEqual(
      [snapshot.current_step_name, snapshot.progress.total_step_count, snapshot.is_complete],
      ["a", 2, false],
    );
  });

  test("moving to the next learner step clears transient feedback", () => {
    const { machine, emitter } = two_step_harness();
    machine.start();
    machine.handle_click("obj_a", "click");
    const snapshot = emitter.get_snapshot();

    assert.deepStrictEqual(
      [
        snapshot.current_step_name,
        snapshot.progress.completed_step_count,
        snapshot.last_outcome,
        snapshot.last_rejection,
      ],
      ["b", 1, null, null],
    );
  });

  test("finishing the authored flow marks the protocol complete", () => {
    const { machine, emitter } = two_step_harness();
    machine.start();
    machine.handle_click("obj_a", "click");
    machine.handle_click("obj_b", "click");
    const snapshot = emitter.get_snapshot();

    assert.deepStrictEqual(
      [snapshot.is_complete, snapshot.progress.completed_step_count, snapshot.last_rejection],
      [true, 2, null],
    );
  });
});

describe("step machine - active_interaction_target and active_interaction_gesture", () => {
  test("step_started sets target and gesture to the first interaction", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction_target, "t1");
    assert.strictEqual(snap.active_interaction_gesture, "click");
  });

  test("interaction_validated advances target and gesture to the next interaction", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction_target, "t2");
    assert.strictEqual(snap.active_interaction_gesture, "click");
  });

  test("last interaction validates -> target and gesture become null", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    machine.handle_click("t2", "click");
    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction_target, null);
    assert.strictEqual(snap.active_interaction_gesture, null);
  });

  test("step_completed clears target and gesture", () => {
    const cfg = make_config(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
    );
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    let snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction_target, "obj_a");
    assert.strictEqual(snap.active_interaction_gesture, "click");
    machine.handle_click("obj_a", "click");
    snap = emitter.get_snapshot();
    // After step_completed and step_started for "b", the target/gesture
    // should be set to the first (and only) interaction of "b".
    assert.strictEqual(snap.active_interaction_target, "obj_b");
    assert.strictEqual(snap.active_interaction_gesture, "click");
  });

  test("protocol_completed clears target and gesture", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    assert.strictEqual(emitter.get_snapshot().active_interaction_target, "obj_a");
    machine.handle_click("obj_a", "click");
    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.is_complete, true);
    assert.strictEqual(snap.active_interaction_target, null);
    assert.strictEqual(snap.active_interaction_gesture, null);
  });

  test("interaction_rejected does not change target or gesture", () => {
    const cfg = make_config([make_two_click_step("a", "t1", "t2", null)], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    const before = emitter.get_snapshot();
    assert.strictEqual(before.active_interaction_target, "t1");
    machine.handle_click("wrong", "click");
    const after = emitter.get_snapshot();
    assert.strictEqual(after.active_interaction_target, "t1");
    assert.strictEqual(after.active_interaction_gesture, "click");
  });
});

describe("step machine - target_with_value authored value", () => {
  test("adjust interaction validates when observed store state matches the value block", () => {
    const config = {
      protocol_name: "p",
      protocol_type: "mini_protocol",
      entry_step: "s1",
      steps: [
        {
          step_name: "s1",
          prompt: "Set the pipette volume.",
          sequence: [
            {
              target: "serological_pipette",
              gesture: "adjust",
              validator: {
                preset: "target_with_value",
                value: { set_volume: 25 },
              },
              response: {
                scene_operations: [
                  {
                    type: "ObjectStateChange",
                    target: "serological_pipette",
                    state: { set_volume: 25 },
                  },
                ],
              },
            },
          ],
          step_validator: { preset: "sequence_complete" },
          outcome: { on_success: "complete", on_failure: "retry" },
          next_step: null,
        },
      ],
    };
    // The student adjusted the pipette to 25 before committing, so the live
    // store reflects set_volume: 25. target_with_value now reads this observed
    // state (not the authored value block), so seed it to match.
    const { machine, events, scene_ops } = build_harness(config, {
      serological_pipette: { set_volume: 25 },
    });

    machine.start();
    machine.handle_click("serological_pipette", "adjust");

    assert.ok(events.some((ev) => ev.kind === "interaction_validated"));
    assert.ok(events.some((ev) => ev.kind === "protocol_completed"));
    assert.strictEqual(scene_ops.length, 1);
    assert.strictEqual(scene_ops[0].type, "ObjectStateChange");
  });

  // M3 load-bearing test (WS-C): under the pre-M1 bug, handle_click sourced the
  // "observed" value map for target_with_value from the AUTHORED validator
  // parameters (validator_parameters(interaction.validator)), never the scene
  // store. That means the comparison was always authored-vs-authored, i.e.
  // always equal, so this exact case (an observed store value that DISAGREES
  // with the authored expected value) would have wrongly validated and
  // completed the protocol. Under M1's fix, handle_click reads the value map
  // from read_object_state(target) (the live observed store this harness
  // seeds), so a mismatched observed value must reject with wrong_value and
  // must NOT advance or complete. This is the test that discriminates
  // old-vs-new runtime behavior; the earlier "matches" test above cannot,
  // because authored-vs-authored always passed too.
  test("adjust interaction rejects wrong_value when observed store state disagrees with the authored value", () => {
    const config = {
      protocol_name: "p",
      protocol_type: "mini_protocol",
      entry_step: "s1",
      steps: [
        {
          step_name: "s1",
          prompt: "Set the pipette volume.",
          sequence: [
            {
              target: "serological_pipette",
              gesture: "adjust",
              validator: {
                preset: "target_with_value",
                value: { set_volume: 25 },
              },
              response: {
                scene_operations: [
                  {
                    type: "ObjectStateChange",
                    target: "serological_pipette",
                    state: { set_volume: 25 },
                  },
                ],
              },
            },
          ],
          step_validator: { preset: "sequence_complete" },
          outcome: { on_success: "complete", on_failure: "retry" },
          next_step: null,
        },
      ],
    };
    // The live store reports set_volume: 10 (the student has not adjusted the
    // pipette to the authored expected value of 25). This seeded observed
    // state disagrees with the authored value block, so the click must fail.
    const { machine, events, emitter } = build_harness(config, {
      serological_pipette: { set_volume: 10 },
    });

    machine.start();
    machine.handle_click("serological_pipette", "adjust");

    const rejected = events.find((ev) => ev.kind === "interaction_rejected");
    assert.ok(rejected, "expected an interaction_rejected event");
    assert.strictEqual(rejected.reason_code, "wrong_value");
    assert.ok(!events.some((ev) => ev.kind === "interaction_validated"));
    assert.ok(!events.some((ev) => ev.kind === "protocol_completed"));
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
    assert.strictEqual(emitter.get_snapshot().current_interaction_index, 0);
  });
});

describe("step machine - final_state_matches authored target/contains (positive path)", () => {
  // Positive-path integration coverage (M3 WS-C item 3): before this test,
  // final_state_matches only had a negative/retry-forever integration case
  // (the "retry path" describe block above, which forces failure with an
  // authored .value shape that never projects). This test exercises the real
  // authored .target/.contains shape end to end: the click completes the
  // sequence, emit_step_validator_outcome reads the seeded observed store
  // snapshot, the fields match, and the step (and protocol) must complete
  // rather than retry.
  test("step_validator passes end-to-end when observed state matches authored target/contains", () => {
    const config = {
      protocol_name: "p",
      protocol_type: "mini_protocol",
      entry_step: "s1",
      steps: [
        {
          step_name: "s1",
          prompt: "Aspirate the medium.",
          sequence: [
            {
              target: "serological_pipette",
              gesture: "click",
              validator: { preset: "correct_target" },
              response: { scene_operations: [] },
            },
          ],
          step_validator: {
            preset: "final_state_matches",
            target: "serological_pipette",
            contains: { set_volume: 25 },
          },
          outcome: { on_success: "complete", on_failure: "retry" },
          next_step: null,
        },
      ],
    };
    // The live store already reflects the expected post-step state. (Fields
    // authored here must be numeric: the stub_lookup_state_field seam above
    // reports every field as declared int, so a string field would trip the
    // load-time authored-value type check unrelated to the behavior under test.)
    const { machine, events, emitter } = build_harness(config, {
      serological_pipette: { set_volume: 25 },
    });

    machine.start();
    machine.handle_click("serological_pipette", "click");

    const completed = events.find((ev) => ev.kind === "step_completed" && ev.step_name === "s1");
    assert.ok(completed, "expected a step_completed event for s1");
    assert.strictEqual(completed.resolution, "complete");
    // No retry: only one step_started for "s1" (the initial one), not a second.
    const started_s1 = events.filter((ev) => ev.kind === "step_started" && ev.step_name === "s1");
    assert.strictEqual(started_s1.length, 1);
    assert.ok(events.some((ev) => ev.kind === "protocol_completed"));
    assert.strictEqual(emitter.get_snapshot().is_complete, true);
  });

  test("step_validator retries when observed state does not match authored target/contains", () => {
    const config = {
      protocol_name: "p",
      protocol_type: "mini_protocol",
      entry_step: "s1",
      steps: [
        {
          step_name: "s1",
          prompt: "Aspirate the medium.",
          sequence: [
            {
              target: "serological_pipette",
              gesture: "click",
              validator: { preset: "correct_target" },
              response: { scene_operations: [] },
            },
          ],
          step_validator: {
            preset: "final_state_matches",
            target: "serological_pipette",
            contains: { set_volume: 25 },
          },
          outcome: { on_success: "complete", on_failure: "retry" },
          next_step: null,
        },
      ],
    };
    // The observed set_volume disagrees with the authored contains block.
    const { machine, events, emitter } = build_harness(config, {
      serological_pipette: { set_volume: 5 },
    });

    machine.start();
    machine.handle_click("serological_pipette", "click");

    const completed = events.filter((ev) => ev.kind === "step_completed");
    assert.ok(completed.length >= 1);
    assert.strictEqual(completed[0].resolution, "retry");
    const started_s1 = events.filter((ev) => ev.kind === "step_started" && ev.step_name === "s1");
    assert.ok(started_s1.length >= 2, "expected sequence to restart with a second step_started");
    assert.ok(!events.some((ev) => ev.kind === "protocol_completed"));
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
    assert.strictEqual(emitter.get_snapshot().current_interaction_index, 0);
  });
});

describe("step machine - current_tip snapshot field", () => {
  test("current_tip is set from step.tip on step_started", () => {
    const step = {
      step_name: "a",
      prompt: "Click the bottle",
      tip: "Make sure the cap is loose before clicking.",
      sequence: [
        {
          target: "obj_a",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([step], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    assert.strictEqual(
      emitter.get_snapshot().current_tip,
      "Make sure the cap is loose before clicking.",
    );
  });

  test("current_tip reverts to null when protocol completes", () => {
    const step = {
      step_name: "a",
      prompt: "Click the bottle",
      tip: "Tip text here.",
      sequence: [
        {
          target: "obj_a",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([step], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    assert.strictEqual(emitter.get_snapshot().current_tip, "Tip text here.");
    machine.handle_click("obj_a", "click");
    assert.strictEqual(emitter.get_snapshot().is_complete, true);
    assert.strictEqual(emitter.get_snapshot().current_tip, null);
  });

  test("current_tip transitions from tip step to null step on next_step", () => {
    const step_with_tip = {
      step_name: "a",
      prompt: "Step A",
      tip: "Here is the tip.",
      sequence: [
        {
          target: "obj_a",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: "b",
    };
    const step_no_tip = {
      step_name: "b",
      prompt: "Step B",
      sequence: [
        {
          target: "obj_b",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([step_with_tip, step_no_tip], "a");
    const { machine, emitter } = build_harness(cfg);
    machine.start();
    assert.strictEqual(emitter.get_snapshot().current_tip, "Here is the tip.");
    machine.handle_click("obj_a", "click");
    // Step B has no tip; current_tip must be null.
    assert.strictEqual(emitter.get_snapshot().current_tip, null);
  });
});

describe("step machine - M2 temporary gesture-collapse guard", () => {
  // A bare pointer click must not silently satisfy an `adjust` or `drag`
  // interaction (those need a real affordance built in M12). protocol_host.tsx
  // stops promoting a bare click to adjust/drag, and handle_click rejects the
  // resulting bare "click" gesture on an adjust/drag interaction. `select` is a
  // genuine click promotion and still advances. This guard is TEMPORARY and is
  // replaced by M13's load-time gesture-affordance invariant.
  function make_gesture_step(gesture) {
    return {
      step_name: "a",
      prompt: `${gesture} the tool`,
      sequence: [
        {
          target: "tool",
          gesture,
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("a bare click does not satisfy an adjust interaction (rejects, no advance)", () => {
    const cfg = make_config([make_gesture_step("adjust")], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("tool", "click");
    assert.ok(!events.some((e) => e.kind === "interaction_validated"));
    assert.ok(!events.some((e) => e.kind === "protocol_completed"));
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(emitter.get_snapshot().is_complete, false);
    assert.strictEqual(emitter.get_snapshot().current_step_name, "a");
  });

  test("a bare click does not satisfy a drag interaction (rejects, no advance)", () => {
    const cfg = make_config([make_gesture_step("drag")], "a");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("tool", "click");
    assert.ok(!events.some((e) => e.kind === "interaction_validated"));
    assert.ok(!events.some((e) => e.kind === "protocol_completed"));
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(emitter.get_snapshot().current_step_name, "a");
  });

  test("select still advances (a genuine click promotion is unaffected)", () => {
    const cfg = make_config([make_gesture_step("select")], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_click("tool", "select");
    assert.ok(events.some((e) => e.kind === "interaction_validated"));
    assert.ok(events.some((e) => e.kind === "protocol_completed"));
  });
});

describe("step machine - dropped events surface a no_active_step rejection", () => {
  // handle_modal_close and handle_timer_elapsed formerly returned silently when
  // no step was active, so a dropped event vanished. They now emit a
  // no_active_step interaction_rejected, matching handle_click/handle_type_commit,
  // so the dropped event is observable to any emitter subscriber (window.gameState).
  test("handle_modal_close before start emits no_active_step", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    // No start(): there is no active step.
    machine.handle_modal_close(true, "choice_1");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "no_active_step");
  });

  test("handle_timer_elapsed before start emits no_active_step", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.handle_timer_elapsed("incubator");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "no_active_step");
  });

  test("handle_timer_elapsed after protocol complete emits no_active_step", () => {
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_click("obj_a", "click");
    const before = events.length;
    machine.handle_timer_elapsed("incubator");
    const rejected = events.slice(before).find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "no_active_step");
  });
});

describe("step machine - load-time preset validation", () => {
  test("throws when a step preset sits in an interaction slot", () => {
    // sequence_complete is a step-family preset; placing it in the
    // interaction.validator slot must fail loud at load with locating fields.
    const bad_step = {
      step_name: "misslotted_interaction",
      prompt: "Click obj_a",
      sequence: [
        {
          target: "obj_a",
          gesture: "click",
          validator: { preset: "sequence_complete" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([bad_step], "misslotted_interaction");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(thrown, "expected create_step_machine to throw");
    const msg = String(thrown.message);
    // Protocol name, step name, slot kind, interaction index, offending preset,
    // and the expected interaction-family must all appear.
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("misslotted_interaction"), "missing step name");
    assert.ok(msg.includes("interaction.validator"), "missing slot kind");
    // Assert the interaction is identified in the message without coupling to
    // a literal "index 0" phrasing that may change with implementation refactors.
    assert.ok(
      msg.includes("interaction") && msg.includes("0"),
      "missing interaction location indicator",
    );
    assert.ok(msg.includes("sequence_complete"), "missing offending preset");
    assert.ok(msg.includes("interaction-family"), "missing expected family");
  });

  test("throws when an interaction preset sits in a step slot", () => {
    // correct_target is an interaction-family preset; placing it in the
    // step_validator slot must fail loud at load with locating fields.
    const bad_step = {
      step_name: "misslotted_step",
      prompt: "Click obj_a",
      sequence: [
        {
          target: "obj_a",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "correct_target" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([bad_step], "misslotted_step");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(thrown, "expected create_step_machine to throw");
    const msg = String(thrown.message);
    // Step slot has no interaction index; the rest of the fields must appear.
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("misslotted_step"), "missing step name");
    assert.ok(msg.includes("step_validator"), "missing slot kind");
    assert.ok(msg.includes("correct_target"), "missing offending preset");
    assert.ok(msg.includes("step-family"), "missing expected family");
  });

  test("valid protocol passes load-time preset validation", () => {
    // A fully valid protocol must construct without throwing.
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    assert.doesNotThrow(() => build_harness(cfg));
  });
});

//============================================
// Load-time gesture-affordance invariant (M13)
//============================================

describe("step machine - load-time gesture-affordance invariant", () => {
  // An interaction whose gesture has no wired affordance in GESTURE_REGISTRY
  // must fail loud at protocol load, before any handler closure or browser
  // session. All five real gestures are wired, so this synthesizes an
  // out-of-set gesture ("levitate") to exercise the absent-row miss class.
  function make_unaffordanced_step() {
    return {
      step_name: "conjure",
      prompt: "Do the impossible",
      sequence: [
        {
          target: "wand",
          gesture: "levitate",
          validator: { preset: "correct_target" },
          response: { scene_operations: [] },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
  }

  test("throws UnaffordancedGestureError when a gesture has no wired affordance", () => {
    const cfg = make_config([make_unaffordanced_step()], "conjure");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(thrown, "expected create_step_machine to throw");
    assert.ok(thrown instanceof UnaffordancedGestureError, "expected an UnaffordancedGestureError");
    const msg = String(thrown.message);
    // The message must locate the offending interaction so the YAML is findable.
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("conjure"), "missing step name");
    assert.ok(msg.includes("wand"), "missing target");
    assert.ok(msg.includes("levitate"), "missing offending gesture");
  });

  test("a normal all-click protocol constructs without throwing", () => {
    // Every gesture here is wired (click), so the invariant must pass.
    const cfg = make_config(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
    );
    assert.doesNotThrow(() => build_harness(cfg));
  });

  test("a wired adjust interaction passes the invariant at load", () => {
    // adjust is a wired gesture (M12), so a protocol using it must construct.
    const adjust_step = {
      step_name: "a",
      prompt: "set the volume",
      sequence: [
        {
          target: "micropipette",
          gesture: "adjust",
          validator: { preset: "target_with_value", value: { set_volume: 1000 } },
          response: {
            scene_operations: [
              { type: "ObjectStateChange", target: "micropipette", state: { set_volume: 1000 } },
            ],
          },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([adjust_step], "a");
    assert.doesNotThrow(() => build_harness(cfg));
  });
});

//============================================
// Load-time target-existence invariant (M16-D)
//============================================

describe("step machine - load-time target-existence invariant", () => {
  // A scene that places one object, "obj_a", once. Mirrors the shape
  // protocol_host.tsx builds from a mounted scene's ComputedItems.
  function build_known_target_adapter() {
    return build_target_adapter([{ object_name: "obj_a", placement_name: "obj_a" }]);
  }

  test("throws UnknownAuthoredTargetError when an interaction target is unknown", () => {
    // "hood_surface" names nothing the scene provides (the target_missing
    // symptom from the walker sweep), so construction must fail loud.
    const cfg = make_config([make_click_step("only_step", "hood_surface", null)], "only_step");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
        target_adapter: build_known_target_adapter(),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(thrown, "expected create_step_machine to throw");
    assert.ok(
      thrown instanceof UnknownAuthoredTargetError,
      "expected an UnknownAuthoredTargetError",
    );
    const msg = String(thrown.message);
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("only_step"), "missing step name");
    assert.ok(msg.includes("interaction.target"), "missing slot kind");
    assert.ok(msg.includes("hood_surface"), "missing offending target");
  });

  test("a protocol whose targets all resolve to known placements passes", () => {
    // "obj_a" resolves through the supplied adapter, so construction must
    // succeed even though the default IDENTITY adapter is not in play.
    const cfg = make_config([make_click_step("only_step", "obj_a", null)], "only_step");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    assert.doesNotThrow(() =>
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
        target_adapter: build_known_target_adapter(),
      }),
    );
  });

  test("no target_adapter supplied (default IDENTITY) always passes", () => {
    // Pure unit tests with no scene adapter must keep passing: identity
    // resolution treats every target as its own known placement.
    const cfg = make_config([make_click_step("a", "obj_a", null)], "a");
    assert.doesNotThrow(() => build_harness(cfg));
  });

  test("a cursor-attached (held/tool) target is exempt from placement checking", () => {
    // "pipette" is never placed in the scene, but it IS the target of a
    // CursorAttach "attach" scene_operation, so the check must exempt it
    // rather than falsely reporting it missing (mirrors real tool targets
    // like aspirating_pipette, rendered through the tray/cursor overlay, not
    // a static scene placement).
    const held_step = {
      step_name: "pick_up_pipette",
      prompt: "Pick up the pipette",
      sequence: [
        {
          target: "pipette",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: {
            scene_operations: [{ type: "CursorAttach", target: "pipette", operation: "attach" }],
          },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([held_step], "pick_up_pipette");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    // No scene knows about "pipette" at all (an empty-bindings adapter), yet
    // construction must not throw: the target is held/tool, exempt.
    const empty_adapter = build_target_adapter([]);
    assert.doesNotThrow(() =>
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
        target_adapter: empty_adapter,
      }),
    );
  });

  test("a per-scene resolver checks a target against the scene active at that point", () => {
    // "bench_item" is placed only in "scene_b". The first interaction
    // transitions from "scene_a" to "scene_b" via SceneChange; the second
    // interaction's target must be checked against "scene_b", not the
    // initial scene, so the resolver must be consulted per current scene.
    const cfg = make_config([make_two_click_step("a", "t1", "bench_item", null)], "a");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    const scene_a_adapter = build_target_adapter([{ object_name: "t1", placement_name: "t1" }]);
    const scene_b_adapter = build_target_adapter([
      { object_name: "bench_item", placement_name: "bench_item" },
    ]);
    const adapters = { scene_a: scene_a_adapter, scene_b: scene_b_adapter };
    assert.doesNotThrow(() =>
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
        initial_scene: "scene_a",
        resolve_scene_target_adapter: (name) => adapters[name],
      }),
    );
  });

  test("a per-scene resolver still rejects a target missing from its own scene", () => {
    // "bench_item" is placed only in "scene_a" here (not "scene_b"), so after
    // the SceneChange to "scene_b" the second interaction's target must fail.
    const cfg = make_config([make_two_click_step("a", "t1", "bench_item", null)], "a");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    const scene_a_adapter = build_target_adapter([
      { object_name: "t1", placement_name: "t1" },
      { object_name: "bench_item", placement_name: "bench_item" },
    ]);
    const scene_b_adapter = build_target_adapter([]);
    const adapters = { scene_a: scene_a_adapter, scene_b: scene_b_adapter };
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
        initial_scene: "scene_a",
        resolve_scene_target_adapter: (name) => adapters[name],
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(
      thrown instanceof UnknownAuthoredTargetError,
      "expected an UnknownAuthoredTargetError",
    );
    assert.ok(String(thrown.message).includes("bench_item"), "missing offending target");
    assert.ok(String(thrown.message).includes("scene_b"), "missing offending scene");
  });
});

//============================================
// Load-time seeded scene-operation target invariant
//============================================

describe("step machine - load-time seeded scene-operation target invariant", () => {
  function make_timed_wait_config() {
    const step = make_click_step("start_incubation", "start_control", null);
    step.sequence[0].response.scene_operations = [
      {
        type: "TimedWait",
        target: "incubator",
        duration_min: 30,
        display: "Incubating",
      },
    ];
    return make_config([step], "start_incubation");
  }

  function create_seeded_operation_machine(cfg, adapter) {
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    return create_step_machine(cfg, emitter, () => {}, {
      lookup_state_field: stub_lookup_state_field,
      read_object_state: () => ({}),
      target_adapter: adapter,
      initial_scene: "incubation_scene",
    });
  }

  test("an unseeded TimedWait fails protocol initialization", () => {
    const cfg = make_timed_wait_config();
    const adapter = build_target_adapter([
      { object_name: "start_control", placement_name: "start_control" },
    ]);
    assert.throws(
      () => create_seeded_operation_machine(cfg, adapter),
      UnseededSceneOperationTargetError,
    );
  });

  test("a TimedWait accepts a target seeded in the active scene", () => {
    const cfg = make_timed_wait_config();
    const adapter = build_target_adapter([
      { object_name: "start_control", placement_name: "start_control" },
      { object_name: "incubator", placement_name: "incubator" },
    ]);
    assert.doesNotThrow(() => create_seeded_operation_machine(cfg, adapter));
  });

  test("ObjectStateChange remains subject to the same seeded-target invariant", () => {
    const step = make_click_step("start", "start_control", null);
    step.sequence[0].response.scene_operations = [
      { type: "ObjectStateChange", target: "incubator", state: { running: true } },
    ];
    const cfg = make_config([step], "start");
    const adapter = build_target_adapter([
      { object_name: "start_control", placement_name: "start_control" },
    ]);
    assert.throws(
      () => create_seeded_operation_machine(cfg, adapter),
      UnseededSceneOperationTargetError,
    );
  });
});

//============================================
// Load-time structure-derived pedagogy consistency invariant (M23)
//============================================

describe("step machine - load-time pedagogy consistency invariant", () => {
  function make_config_with_learning(steps, entry_step, learning) {
    return {
      protocol_name: "test_proto",
      protocol_type: "mini_protocol",
      entry_step,
      learning,
      steps,
    };
  }

  test("throws StepCountClaimMismatchError when the learning block claims the wrong step count", () => {
    const cfg = make_config_with_learning([make_click_step("a", "obj_a", null)], "a", {
      objectives: "Students completing this mini-protocol will have achieved fluency.",
      outcomes: "Students completing this mini-protocol will be able to do it.",
      goals: "Overall, this mini-protocol aims to accomplish it. The 3 steps cover it.",
    });
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(
      thrown instanceof StepCountClaimMismatchError,
      "expected a StepCountClaimMismatchError",
    );
    const msg = String(thrown.message);
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("goals"), "missing learning field name");
    assert.ok(msg.includes("3"), "missing claimed count");
    assert.ok(msg.includes("1"), "missing actual count");
  });

  test("a learning block whose step-count claim matches the authored steps passes", () => {
    const cfg = make_config_with_learning(
      [make_click_step("a", "obj_a", "b"), make_click_step("b", "obj_b", null)],
      "a",
      {
        objectives: "Students completing this mini-protocol will have achieved fluency.",
        outcomes: "Students completing this mini-protocol will be able to do it.",
        goals: "Overall, this mini-protocol aims to accomplish it. The 2 steps cover it.",
      },
    );
    assert.doesNotThrow(() => build_harness(cfg));
  });

  test("throws PromptTargetDriftError when a prompt names another step's dotted target token", () => {
    const steps = [
      {
        step_name: "misnamed",
        prompt: "Insert the treated plate into well_plate_96.all_wells.",
        sequence: [
          {
            target: "plate_reader",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: "dose",
      },
      {
        step_name: "dose",
        prompt: "Dose every well.",
        sequence: [
          {
            target: "well_plate_96.all_wells",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ];
    const cfg = make_config(steps, "misnamed");
    const start_snapshot = initial_snapshot(cfg.protocol_name);
    const reducer = create_snapshot_reducer(cfg);
    const emitter = createProtocolShellEmitter(start_snapshot, reducer);
    let thrown = null;
    try {
      create_step_machine(cfg, emitter, () => {}, {
        lookup_state_field: stub_lookup_state_field,
        read_object_state: () => ({}),
      });
    } catch (err) {
      thrown = err;
    }
    assert.ok(thrown instanceof PromptTargetDriftError, "expected a PromptTargetDriftError");
    const msg = String(thrown.message);
    assert.ok(msg.includes("test_proto"), "missing protocol name");
    assert.ok(msg.includes("misnamed"), "missing step name");
    assert.ok(msg.includes("well_plate_96.all_wells"), "missing offending target token");
  });

  test("a prompt naming its own step's dotted target token passes", () => {
    const steps = [
      {
        step_name: "dose",
        prompt: "Dose well_plate_96.all_wells with DMSO.",
        sequence: [
          {
            target: "well_plate_96.all_wells",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ];
    const cfg = make_config(steps, "dose");
    assert.doesNotThrow(() => build_harness(cfg));
  });

  test("a bare object-name mention elsewhere in the protocol never fires (narrow scope)", () => {
    // "micropipette" is a bare (non-dotted) token, so ordinary narrative prose
    // naming an object used elsewhere in the protocol must never be flagged.
    const steps = [
      make_click_step("a", "micropipette", "b"),
      {
        step_name: "b",
        prompt: "Set the micropipette aside and click the plate.",
        sequence: [
          {
            target: "well_plate_96",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ];
    const cfg = make_config(steps, "a");
    assert.doesNotThrow(() => build_harness(cfg));
  });
});
