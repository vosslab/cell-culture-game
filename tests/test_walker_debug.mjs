// tests/test_walker_debug.mjs
//
// Node --test suite for the read-only walker/debug surface (WS-M3-D). Proves
// that install_walker_debug_surface installs window.PROTOCOL_STEPS and
// window.gameState and that gameState projects the progress-predicate signals
// the canonical walker reads (active step, interaction index, active scene,
// completed-step ids, cursor/held state, wrong-order counters).
//
// window does not exist in Node, so the suite installs a minimal stub on
// globalThis before importing the module under test. The surfaces are READ
// here; nothing in the test mutates them to advance state (that is the frozen
// read-only contract).

import { test, describe } from "node:test";
import assert from "node:assert";

// Minimal window stub so the module's window.* writes have a home. Must be set
// before importing the module (the module references the global Window type at
// runtime only via window.*, which resolves against this stub).
globalThis.window = globalThis.window ?? {};

const { install_walker_debug_surface, build_protocol_steps } =
  await import("../src/scene_runtime/protocol/walker_debug.ts");
const { create_scene_store } = await import("../src/scene_runtime/state/scene_store.ts");
const { createProtocolShellEmitter } = await import("../src/scene_runtime/protocol/emitter.ts");
const { create_snapshot_reducer } = await import("../src/scene_runtime/protocol/step_machine.ts");

//============================================
// Fixture: a tiny two-step config
//============================================

function make_config() {
  return {
    protocol_type: "mini_protocol",
    protocol_name: "walker_debug_fixture",
    entry_step: "step_one",
    steps: [
      {
        step_name: "step_one",
        prompt: "Click the centrifuge.",
        sequence: [
          {
            target: "centrifuge",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: {
              scene_operations: [{ type: "SceneChange", to_scene: "bench" }],
            },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: "step_two",
      },
      {
        step_name: "step_two",
        prompt: "Finish.",
        sequence: [
          {
            target: "centrifuge",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ],
  };
}

function make_emitter(config) {
  const reducer = create_snapshot_reducer(config);
  const initial = {
    protocol_name: config.protocol_name,
    current_step_name: null,
    current_prompt: null,
    current_tip: null,
    current_interaction_index: 0,
    progress: { completed_step_count: 0, total_step_count: 2 },
    last_outcome: null,
    pending_validator_kind: null,
    modal: { is_open: false, kind: null, prompt: null, choices: [], invoking_target: null },
    help: { is_open: false, topic: null },
    tray: { items: [] },
    active_scene_name: null,
    is_complete: false,
    active_interaction_target: null,
    active_interaction_gesture: null,
  };
  return createProtocolShellEmitter(initial, reducer);
}

//============================================
// PROTOCOL_STEPS
//============================================

describe("walker_debug PROTOCOL_STEPS", () => {
  test("build_protocol_steps maps step_name/prompt/scene/next", () => {
    const steps = build_protocol_steps(make_config());
    assert.strictEqual(steps.length, 2);
    assert.strictEqual(steps[0].id, "step_one");
    // scene resolves from the first SceneChange in the step sequence.
    assert.strictEqual(steps[0].scene, "bench");
    assert.strictEqual(steps[0].nextId, "step_two");
    assert.strictEqual(steps[1].nextId, null);
  });

  test("install exposes window.PROTOCOL_STEPS as an array", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    assert.ok(Array.isArray(window.PROTOCOL_STEPS));
    assert.strictEqual(window.PROTOCOL_STEPS.length, 2);
    dispose();
  });
});

//============================================
// gameState projection
//============================================

describe("walker_debug gameState", () => {
  test("gameState exists immediately, activeStepId null before start", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    assert.ok(window.gameState);
    assert.strictEqual(window.gameState.activeStepId, null);
    assert.deepStrictEqual(window.gameState.completedSteps, []);
    dispose();
  });

  test("activeStepId tracks step_started", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    emitter.emit({
      kind: "step_started",
      step_name: "step_one",
      prompt: "Click the centrifuge.",
      interaction_count: 1,
    });
    assert.strictEqual(window.gameState.activeStepId, "step_one");
    dispose();
  });

  test("activeTarget/activeGesture project the current interaction from step_started", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    emitter.emit({
      kind: "step_started",
      step_name: "step_one",
      prompt: "Click the centrifuge.",
      interaction_count: 1,
    });
    // The reducer fills active_interaction_target/gesture from config[step_one][0].
    assert.strictEqual(window.gameState.activeTarget, "centrifuge");
    assert.strictEqual(window.gameState.activeGesture, "click");
    dispose();
  });

  test("completedSteps records ids on step_completed complete", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    emitter.emit({ kind: "step_completed", step_name: "step_one", resolution: "complete" });
    assert.ok(window.gameState.completedSteps.includes("step_one"));
    // A retry resolution must NOT count as completed.
    emitter.emit({ kind: "step_completed", step_name: "step_two", resolution: "retry" });
    assert.ok(!window.gameState.completedSteps.includes("step_two"));
    dispose();
  });

  test("activeScene tracks scene_changed", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    emitter.emit({ kind: "scene_changed", from_scene: null, to_scene: "bench" });
    assert.strictEqual(window.gameState.activeScene, "bench");
    dispose();
  });

  test("wrongOrderClicks counts wrong-target rejections", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    emitter.emit({
      kind: "interaction_rejected",
      step_name: "step_one",
      interaction_index: 0,
      target_name: "wrong_thing",
      gesture: "click",
      validator_preset: "correct_target",
      reason_code: "wrong_target",
    });
    assert.strictEqual(window.gameState.wrongOrderClicks, 1);
    dispose();
  });

  test("selectedTool/heldLiquid reflect the cursor-attached tool", () => {
    const config = make_config();
    const store = create_scene_store();
    store.seed_from_scene([{ target: "p20_micropipette", object_name: "p20_micropipette" }]);
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    store.set_cursor("p20_micropipette", {
      attach: true,
      held_material_name: "trypan_blue",
      held_material_volume: 10,
    });
    // gameState is rebuilt on emitter events; emit a benign event to refresh.
    emitter.emit({
      kind: "scene_operation_applied",
      operation_type: "CursorAttach",
      target_name: "p20_micropipette",
    });
    assert.strictEqual(window.gameState.selectedTool, "p20_micropipette");
    assert.strictEqual(window.gameState.heldLiquid.liquid, "trypan_blue");
    dispose();
  });

  test("projects the latest declared-state delta and revision read-only", () => {
    const config = make_config();
    const store = create_scene_store();
    store.start_session([{ target: "centrifuge", object_name: "centrifuge" }], []);
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    const before = window.gameState.stateRevision;
    store.set_object_state("centrifuge", { running: true });
    emitter.emit({
      kind: "scene_operation_applied",
      operation_type: "ObjectStateChange",
      target_name: "centrifuge",
    });
    assert.ok(window.gameState.stateRevision > before);
    assert.deepStrictEqual(window.gameState.lastStateDelta, {
      target: "centrifuge",
      before: { running: false },
      after: { running: true },
    });
    dispose();
  });

  test("dispose removes both window surfaces", () => {
    const config = make_config();
    const store = create_scene_store();
    const emitter = make_emitter(config);
    const dispose = install_walker_debug_surface(config, emitter, store);
    dispose();
    assert.strictEqual(window.PROTOCOL_STEPS, undefined);
    assert.strictEqual(window.gameState, undefined);
  });
});
