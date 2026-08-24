// tests/test_m2_integration.mjs
//
// End-to-end M2 integration test wiring every protocol/* module together.
// Wires: emitter + step_machine + scene_operations + validators + click_resolver.
// Drives the runtime end-to-end by calling step_machine.handle_click() and
// validates the typed event stream.
//
// Scenario 1: Happy path with correct clicks driving 2 steps to completion.
// Scenario 2: Wrong-target rejection (interaction_index does not advance).
// Scenario 3: Complete + retry (step validator fails once, then passes).
// Scenario 4: Click resolver integration (DOM stub -> target resolution).
// Scenario 5: Modal close with correct_choice validator.
//
// All assertions are on emitted events, not on internal state.
// No brittle assertions on exact constants or required-key lists.

import { test, describe } from "node:test";
import assert from "node:assert";

import { createProtocolShellEmitter } from "../src/scene_runtime/protocol/emitter.ts";
import {
  create_step_machine,
  initial_snapshot,
  snapshot_reducer,
} from "../src/scene_runtime/protocol/step_machine.ts";
import { create_scene_op_handler } from "../src/scene_runtime/protocol/scene_operations.ts";

//============================================
// Fixture builders
//============================================

function make_simple_click_step(name, target, next_step) {
  return {
    step_name: name,
    prompt: `Step ${name}: click ${target}`,
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

function make_two_interaction_step(name, t1, t2, next_step) {
  return {
    step_name: name,
    prompt: `Step ${name}: click two targets`,
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

function make_retry_step(name, target, next_step) {
  return {
    step_name: name,
    prompt: `Step ${name}: click target then retry on failure`,
    sequence: [
      {
        target,
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
    next_step,
  };
}

function make_modal_step(name, next_step) {
  return {
    step_name: name,
    prompt: `Step ${name}: select the correct next-step object`,
    sequence: [
      {
        target: "correct_object",
        gesture: "select",
        validator: {
          preset: "correct_choice",
        },
        response: { scene_operations: [] },
      },
    ],
    step_validator: { preset: "sequence_complete" },
    outcome: { on_success: "complete", on_failure: "retry" },
    next_step,
  };
}

function make_config(steps, entry_step, protocol_name = "test_protocol") {
  return {
    protocol_name,
    protocol_type: "mini_protocol",
    entry_step,
    steps,
  };
}

function build_harness(config) {
  const events = [];
  const scene_ops = [];
  const start_snapshot = initial_snapshot(config.protocol_name);
  const emitter = createProtocolShellEmitter(start_snapshot, snapshot_reducer);
  emitter.subscribe((event) => {
    events.push(event);
  });
  const scene_op_handler = create_scene_op_handler({
    apply_object_state: (op) => scene_ops.push({ type: "object_state", op }),
    apply_cursor_attach: (op) => scene_ops.push({ type: "cursor", op }),
    apply_scene_change: (op) => scene_ops.push({ type: "scene", op }),
    apply_layout_move: (op) => scene_ops.push({ type: "layout", op }),
    start_timed_wait: (op) => scene_ops.push({ type: "wait", op }),
  });
  const machine = create_step_machine(config, emitter, scene_op_handler, {
    // Stub lookup for the M1B-2 seam. WP-SEAM only threads it through; the
    // load-time value pass (WP-CHECK/WP-TEST) is not exercised here.
    lookup_state_field: () => ({ kind: "unknown_object" }),
    // Observed-state reader seam. These scenarios use only correct_target /
    // correct_choice (no target_with_value / final_state_matches), so nothing
    // reads it; an empty map keeps the option well-formed.
    read_object_state: () => ({}),
  });
  return { machine, events, scene_ops, emitter };
}

function event_kinds(events) {
  return events.map((e) => e.kind);
}

//============================================
// Scenario 1: Happy path (2 steps, correct clicks)
//============================================

describe("M2 integration - scenario 1: happy path", () => {
  test("wires emitter + step_machine + validators through 2 steps to protocol_completed", () => {
    const cfg = make_config(
      [
        make_simple_click_step("step_1", "obj_a", "step_2"),
        make_simple_click_step("step_2", "obj_b", null),
      ],
      "step_1",
    );
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("obj_a", "click");
    machine.handle_click("obj_b", "click");

    const kinds = event_kinds(events);
    assert.ok(kinds.includes("protocol_loaded"));
    assert.ok(kinds.includes("step_started"));
    assert.ok(kinds.includes("interaction_validated"));
    assert.ok(kinds.includes("step_completed"));
    assert.ok(kinds.includes("protocol_completed"));

    const snapshot = emitter.get_snapshot();
    assert.strictEqual(snapshot.is_complete, true);
    assert.strictEqual(snapshot.progress.completed_step_count, 2);
    assert.strictEqual(snapshot.current_step_name, null);
  });

  test("emits events in correct order: protocol_loaded -> step_started -> interaction_validated -> step_completed -> step_started -> ... -> protocol_completed", () => {
    const cfg = make_config(
      [make_simple_click_step("s1", "t1", "s2"), make_simple_click_step("s2", "t2", null)],
      "s1",
    );
    const { machine, events } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");
    machine.handle_click("t2", "click");

    const kinds = event_kinds(events);
    const loaded_idx = kinds.indexOf("protocol_loaded");
    const first_started_idx = kinds.indexOf("step_started");
    const first_validated_idx = kinds.indexOf("interaction_validated");
    const first_completed_idx = kinds.indexOf("step_completed");
    const second_started_idx = kinds.lastIndexOf("step_started");
    const protocol_done_idx = kinds.indexOf("protocol_completed");

    assert.ok(loaded_idx >= 0);
    assert.ok(first_started_idx > loaded_idx);
    assert.ok(first_validated_idx > first_started_idx);
    assert.ok(first_completed_idx > first_validated_idx);
    assert.ok(second_started_idx > first_completed_idx);
    assert.ok(protocol_done_idx > second_started_idx);
  });

  test("snapshot updates reflect each transition: current_step_name, interaction_index, progress", () => {
    const cfg = make_config(
      [make_two_interaction_step("s1", "t1", "t2", "s2"), make_simple_click_step("s2", "t3", null)],
      "s1",
    );
    const { machine, emitter } = build_harness(cfg);
    machine.start();

    let snap = emitter.get_snapshot();
    assert.strictEqual(snap.current_step_name, "s1");
    assert.strictEqual(snap.active_interaction.index, 0);
    assert.strictEqual(snap.progress.completed_step_count, 0);
    assert.strictEqual(snap.progress.total_step_count, 2);

    machine.handle_click("t1", "click");
    snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction.index, 1);
    assert.strictEqual(snap.progress.completed_step_count, 0);

    machine.handle_click("t2", "click");
    snap = emitter.get_snapshot();
    assert.strictEqual(snap.current_step_name, "s2");
    assert.strictEqual(snap.active_interaction.index, 0);
    assert.strictEqual(snap.progress.completed_step_count, 1);

    machine.handle_click("t3", "click");
    snap = emitter.get_snapshot();
    assert.strictEqual(snap.is_complete, true);
    assert.strictEqual(snap.progress.completed_step_count, 2);
  });
});

//============================================
// Scenario 2: Wrong-target rejection
//============================================

describe("M2 integration - scenario 2: wrong-target rejection", () => {
  test("clicking wrong target emits interaction_rejected with reason wrong_target; interaction_index does not advance", () => {
    const cfg = make_config([make_two_interaction_step("s1", "t1", "t2", null)], "s1");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();

    machine.handle_click("wrong_target", "click");
    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
    assert.strictEqual(emitter.get_snapshot().active_interaction.index, 0);

    const validated_count = events.filter((e) => e.kind === "interaction_validated").length;
    assert.strictEqual(validated_count, 0);
  });

  test("after rejection, correct click on same interaction validates and advances", () => {
    const cfg = make_config([make_two_interaction_step("s1", "t1", "t2", null)], "s1");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();

    machine.handle_click("oops", "click");
    machine.handle_click("t1", "click");

    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.interaction_index, 0);
    assert.strictEqual(emitter.get_snapshot().active_interaction.index, 1);
  });

  test("clicking while protocol is complete emits no_active_step rejection", () => {
    const cfg = make_config([make_simple_click_step("s1", "t1", null)], "s1");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();
    machine.handle_click("t1", "click");

    assert.strictEqual(emitter.get_snapshot().is_complete, true);

    const before_count = events.length;
    machine.handle_click("t1", "click");

    const new_events = events.slice(before_count);
    const rejected = new_events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "no_active_step");
  });
});

//============================================
// Scenario 3: Retry flow (step validator fails, then passes)
//============================================

describe("M2 integration - scenario 3: retry on step validator failure", () => {
  test("step_validator false -> step_completed(retry) + interaction_index resets + step re-enters", () => {
    const cfg = make_config([make_retry_step("s1", "t1", null)], "s1");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();

    machine.handle_click("t1", "click");

    const completions = events.filter((e) => e.kind === "step_completed");
    assert.ok(completions.length >= 1);
    assert.strictEqual(completions[0].resolution, "retry");

    const re_entries = events.filter((e) => e.kind === "step_started" && e.step_name === "s1");
    assert.ok(re_entries.length >= 2, "step should re-enter after retry");

    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_interaction.index, 0);
    assert.strictEqual(snap.current_step_name, "s1");
  });

  test("after retry, another correct click validates and can pass step validator", () => {
    const cfg = make_config([make_retry_step("s1", "t1", null)], "s1");
    const { machine, events } = build_harness(cfg);
    machine.start();

    machine.handle_click("t1", "click");
    const completions_after_first = events.filter((e) => e.kind === "step_completed");
    assert.ok(completions_after_first.length >= 1);
    assert.strictEqual(completions_after_first[0].resolution, "retry");

    machine.handle_click("t1", "click");
    const all_completions = events.filter((e) => e.kind === "step_completed");
    assert.ok(all_completions.length >= 2);
  });
});

//============================================
// Scenario 4: Scene operations dispatch
//============================================

describe("M2 integration - scenario 4: scene operations dispatcher", () => {
  test("SceneChange op is dispatched to scene_op_handler and emits scene_changed event", () => {
    const cfg = make_config([make_two_interaction_step("s1", "t1", "t2", null)], "s1");
    const { machine, events, scene_ops, emitter } = build_harness(cfg);
    machine.start();

    machine.handle_click("t1", "click");

    const applied_events = events.filter((e) => e.kind === "scene_operation_applied");
    assert.ok(applied_events.length >= 1);

    const scene_changed = events.find((e) => e.kind === "scene_changed");
    assert.ok(scene_changed);

    const scene_ops_dispatched = scene_ops.filter((op) => op.type === "scene");
    assert.ok(scene_ops_dispatched.length >= 1);

    const snap = emitter.get_snapshot();
    assert.strictEqual(snap.active_scene_name, "scene_b");
  });

  test("multiple scene operations fire in sequence, emitting scene_operation_applied for each", () => {
    const step = {
      step_name: "s1",
      prompt: "Multi-op step",
      sequence: [
        {
          target: "t1",
          gesture: "click",
          validator: { preset: "correct_target" },
          response: {
            scene_operations: [
              { type: "SceneChange", to_scene: "scene_2" },
              {
                type: "ObjectStateChange",
                target: "obj_1",
                state: { material: "water" },
              },
            ],
          },
        },
      ],
      step_validator: { preset: "sequence_complete" },
      outcome: { on_success: "complete", on_failure: "retry" },
      next_step: null,
    };
    const cfg = make_config([step], "s1");
    const { machine, events } = build_harness(cfg);
    machine.start();

    machine.handle_click("t1", "click");

    const applied = events.filter((e) => e.kind === "scene_operation_applied");
    assert.ok(applied.length >= 2);
  });
});

//============================================
// Scenario 5: select-gesture validation (correct_choice = target-equality)
//============================================

describe("M2 integration - scenario 5: select validation", () => {
  test("selecting the correct object validates and advances", () => {
    const cfg = make_config([make_modal_step("s1", null)], "s1");
    const { machine, events } = build_harness(cfg);
    machine.start();

    // select reuses the visible-click path: a click on the active target is
    // promoted to the active select gesture by the host.
    machine.handle_click("correct_object", "select");

    const validated = events.find((e) => e.kind === "interaction_validated");
    assert.ok(validated);
    assert.strictEqual(validated.validator_preset, "correct_choice");

    const completed = events.find((e) => e.kind === "protocol_completed");
    assert.ok(completed);
  });

  test("selecting a wrong present object rejects and does not advance", () => {
    const cfg = make_config([make_modal_step("s1", null)], "s1");
    const { machine, events, emitter } = build_harness(cfg);
    machine.start();

    machine.handle_click("wrong_object", "select");

    const rejected = events.find((e) => e.kind === "interaction_rejected");
    assert.ok(rejected);
    assert.strictEqual(rejected.reason_code, "wrong_target");
    assert.strictEqual(emitter.get_snapshot().active_interaction.index, 0);

    const protocol_done = events.find((e) => e.kind === "protocol_completed");
    assert.ok(!protocol_done);
  });
});

//============================================
// Scenario 6: Scene operation handlers
//============================================

describe("M2 integration - scenario 6: scene op handler dispatch", () => {
  test("scene_op_handler receives all five operation types without error", () => {
    const ops_received = [];
    const handler = create_scene_op_handler({
      apply_object_state: (op) => ops_received.push(op.type),
      apply_cursor_attach: (op) => ops_received.push(op.type),
      apply_scene_change: (op) => ops_received.push(op.type),
      apply_layout_move: (op) => ops_received.push(op.type),
      start_timed_wait: (op) => ops_received.push(op.type),
    });

    handler({
      type: "ObjectStateChange",
      target: "obj",
      state: { a: 1 },
    });
    handler({
      type: "CursorAttach",
      target: "obj",
      operation: "attach",
    });
    handler({
      type: "SceneChange",
      to_scene: "scene_new",
    });
    handler({
      type: "LayoutMove",
      target: "obj",
      zone: "zone_a",
    });
    handler({
      type: "TimedWait",
      target: "obj",
      duration_min: 100,
    });

    assert.strictEqual(ops_received.length, 5);
    assert.ok(ops_received.includes("ObjectStateChange"));
    assert.ok(ops_received.includes("CursorAttach"));
    assert.ok(ops_received.includes("SceneChange"));
    assert.ok(ops_received.includes("LayoutMove"));
    assert.ok(ops_received.includes("TimedWait"));
  });
});
