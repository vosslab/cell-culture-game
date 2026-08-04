// tests/test_flatten_sequence_runner.mjs
//
// Unit tests for flatten_sequence_runner: expanding a sequence_runner into one
// flat mini_protocol-shaped config whose next_step chain plays every constituent
// mini-protocol in order (namespaced ids, boundary rechaining, per-mini entry
// scene). Inline configs only; no fixture directories.
//
// Run with:
//   node --import tsx --test tests/test_flatten_sequence_runner.mjs

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { flatten_sequence_runner } from "../src/scene_runtime/protocol/flatten_sequence_runner.ts";
import { create_scene_store } from "../src/scene_runtime/state/scene_store.ts";

//============================================
// Fixture helpers
//============================================

// A single-step mini-protocol whose entry step opens via a SceneChange to
// `scene` (precedence-2 entry-scene resolution). `next_step` chains within the
// mini; a two-step mini is built by chaining two of these.
function make_step(step_name, target, scene, next_step) {
  const scene_operations = scene === null ? [] : [{ type: "SceneChange", to_scene: scene }];
  return {
    step_name,
    prompt: `Prompt for ${step_name}`,
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
    next_step,
  };
}

function make_mini(protocol_name, entry_step, steps) {
  return { protocol_name, protocol_type: "mini_protocol", entry_step, steps };
}

function make_runner(protocol_name, entry_step, mini_protocols) {
  return { protocol_name, protocol_type: "sequence_runner", entry_step, mini_protocols };
}

//============================================
// Tests
//============================================

describe("flatten_sequence_runner - pass-through", () => {
  test("a non-runner config is returned unchanged", () => {
    const mini = make_mini("m", "s0", [make_step("s0", "obj", "scene_x", null)]);
    const out = flatten_sequence_runner(mini, { m: mini });
    assert.strictEqual(out, mini);
  });
});

describe("flatten_sequence_runner - chaining", () => {
  // Two distinct minis, each two steps, chained by a runner.
  const alpha = make_mini("alpha", "a0", [
    make_step("a0", "obj_a0", "scene_alpha", "a1"),
    make_step("a1", "obj_a1", null, null),
  ]);
  const beta = make_mini("beta", "b0", [
    make_step("b0", "obj_b0", "scene_beta", "b1"),
    make_step("b1", "obj_b1", null, null),
  ]);
  const runner = make_runner("runner_ab", "a0", ["alpha", "beta"]);
  const protocols = { alpha, beta, runner_ab: runner };

  test("flattened config is a mini_protocol with all constituent steps", () => {
    const flat = flatten_sequence_runner(runner, protocols);
    assert.strictEqual(flat.protocol_type, "mini_protocol");
    assert.strictEqual(flat.protocol_name, "runner_ab");
    assert.strictEqual(flat.steps.length, 4);
  });

  test("entry_step is the first constituent's namespaced entry step", () => {
    const flat = flatten_sequence_runner(runner, protocols);
    assert.strictEqual(flat.entry_step, "mp0__a0");
  });

  test("step ids are namespaced per instance so duplicates stay distinct", () => {
    const flat = flatten_sequence_runner(runner, protocols);
    const ids = flat.steps.map((s) => s.step_name);
    assert.deepStrictEqual(ids, ["mp0__a0", "mp0__a1", "mp1__b0", "mp1__b1"]);
  });

  test("terminal step of a mini chains to the next mini's entry step", () => {
    const flat = flatten_sequence_runner(runner, protocols);
    const by_id = new Map(flat.steps.map((s) => [s.step_name, s]));
    // Within alpha: a0 -> a1.
    assert.strictEqual(by_id.get("mp0__a0").next_step, "mp0__a1");
    // alpha terminal (a1) rechained to beta entry.
    assert.strictEqual(by_id.get("mp0__a1").next_step, "mp1__b0");
    // Within beta: b0 -> b1.
    assert.strictEqual(by_id.get("mp1__b0").next_step, "mp1__b1");
    // Last constituent terminal stays null so the whole runner completes.
    assert.strictEqual(by_id.get("mp1__b1").next_step, null);
  });

  test("each constituent entry step carries its resolved entry scene", () => {
    const flat = flatten_sequence_runner(runner, protocols);
    const by_id = new Map(flat.steps.map((s) => [s.step_name, s]));
    assert.strictEqual(by_id.get("mp0__a0").scene, "scene_alpha");
    assert.strictEqual(by_id.get("mp1__b0").scene, "scene_beta");
  });
});

describe("flatten_sequence_runner - strict constituent shape", () => {
  const load = make_mini("load", "l0", [make_step("l0", "lane", "scene_load", null)]);
  const runner = make_runner("runner_ll", "l0", ["load", "load"]);
  const protocols = { load, runner_ll: runner };

  test("rejects a repeated direct mini", () => {
    assert.throws(() => flatten_sequence_runner(runner, protocols), /repeats constituent/);
  });

  test("rejects a nested runner rather than silently inlining it", () => {
    const alpha = make_mini("alpha", "a0", [make_step("a0", "obj_a0", "scene_alpha", null)]);
    const beta = make_mini("beta", "b0", [make_step("b0", "obj_b0", "scene_beta", null)]);
    const inner = make_runner("inner", "a0", ["alpha", "beta"]);
    const outer = make_runner("outer", "a0", ["inner"]);
    const protocols = { alpha, beta, inner, outer };
    assert.throws(() => flatten_sequence_runner(outer, protocols), /must be a mini_protocol/);
  });

  test("starts a real session from only the runner root initial_state", () => {
    const mini = {
      ...make_mini("with_initial", "m0", [make_step("m0", "obj", "scene_m", null)]),
      initial_state: [{ target: "centrifuge", state: { running: true } }],
    };
    const root = {
      ...make_runner("root", "m0", ["with_initial"]),
      initial_state: [{ target: "centrifuge", state: { running: false } }],
    };
    const flat = flatten_sequence_runner(root, { with_initial: mini, root });
    assert.deepStrictEqual(flat.initial_state, root.initial_state);
    const store = create_scene_store();
    store.start_session(
      [{ target: "centrifuge", object_name: "centrifuge" }],
      flat.initial_state ?? [],
    );
    // The constituent requested `running: true`, but it never crosses the
    // runner flatten/session boundary. The root value is the live projection.
    assert.strictEqual(store.state.centrifuge.state.running, false);
    // The session retains the root override and also hydrates every declared
    // centrifuge control from its schema default.  This checks the runner
    // boundary without freezing the set of controls an instrument may expose.
    assert.deepStrictEqual(store.snapshot_declared_state(), {
      centrifuge: {
        running: false,
        set_rcf: 200,
        set_rpm: 1200,
        set_time_min: 5,
      },
    });
  });
});

describe("flatten_sequence_runner - errors", () => {
  test("missing constituent throws a locating error", () => {
    const runner = make_runner("r", "x0", ["ghost"]);
    assert.throws(() => flatten_sequence_runner(runner, { r: runner }), /ghost/);
  });

  test("runner with no mini_protocols throws", () => {
    const runner = make_runner("r", "x0", []);
    assert.throws(() => flatten_sequence_runner(runner, { r: runner }), /no mini_protocols/);
  });
});
