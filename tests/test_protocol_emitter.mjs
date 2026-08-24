// tests/test_protocol_emitter.mjs
//
// Node --test suite for ProtocolShellEmitter.
// Tests: subscribe + emit + get_snapshot happy path, multiple subscribers,
// unsubscribe stops delivery, reducer is applied before notification,
// and snapshot immutability (readonly annotations).

import { test, describe } from "node:test";
import assert from "node:assert";

// Import the emitter factory and types from the compiled output.
// Since this is a .mjs test, we import from the TypeScript output.
// The build system (tsc or esbuild) will have compiled src/scene_runtime/protocol/emitter.ts
// to dist/ or an equivalent output location. For Node --test in development,
// we use --import tsx to handle TypeScript on the fly.
//
// However, since the instructions say "node --import tsx --test", we need to
// import the TS source directly. tsx handles the transpilation.

import { createProtocolShellEmitter } from "../src/scene_runtime/protocol/emitter.ts";

//============================================
// Test fixture: initial snapshot and reducer
//============================================

function createFixtureSnapshot() {
  return {
    protocol_name: "test_protocol",
    current_step_name: null,
    current_prompt: null,
    active_interaction: null,
    current_tip: null,
    progress: {
      completed_step_count: 0,
      total_step_count: 3,
    },
    last_outcome: null,
    pending_validator_kind: null,
    modal: {
      is_open: false,
      kind: null,
      prompt: null,
      choices: [],
      invoking_target: null,
    },
    help: {
      is_open: false,
      topic: null,
    },
    tray: {
      items: [],
    },
    active_scene_name: null,
    is_complete: false,
    pending_timed_wait: null,
  };
}

function createFixtureReducer() {
  return (prev, event) => {
    // Simple reducer: update current_step_name on step_started,
    // increment completed_step_count on step_completed.
    // For most events, return snapshot unchanged.
    if (event.kind === "step_started") {
      return {
        ...prev,
        current_step_name: event.step_name,
        current_prompt: event.prompt,
      };
    }
    if (event.kind === "step_completed") {
      if (event.resolution === "complete") {
        return {
          ...prev,
          progress: {
            ...prev.progress,
            completed_step_count: prev.progress.completed_step_count + 1,
          },
        };
      }
    }
    if (event.kind === "protocol_completed") {
      return {
        ...prev,
        current_step_name: null,
        is_complete: true,
      };
    }
    return prev;
  };
}

//============================================
// Tests
//============================================

describe("ProtocolShellEmitter", () => {
  test("subscribe + emit + get_snapshot happy path", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    // Initial snapshot should match what we passed in.
    const snap0 = emitter.get_snapshot();
    assert.strictEqual(snap0.protocol_name, "test_protocol");
    assert.strictEqual(snap0.current_step_name, null);

    // Emit a step_started event.
    const stepStartedEvent = {
      kind: "step_started",
      step_name: "step_1",
      prompt: "Do the first step",
      interaction_count: 2,
    };

    let event_received = null;
    const unsubscribe = emitter.subscribe((event) => {
      event_received = event;
    });

    emitter.emit(stepStartedEvent);

    // The subscriber should have received the event.
    assert.deepStrictEqual(event_received, stepStartedEvent);

    // The snapshot should be updated by the reducer.
    const snap1 = emitter.get_snapshot();
    assert.strictEqual(snap1.current_step_name, "step_1");
    assert.strictEqual(snap1.current_prompt, "Do the first step");

    // Progress should still be 0 (only step_completed increments it).
    assert.strictEqual(snap1.progress.completed_step_count, 0);

    unsubscribe();
  });

  test("multiple subscribers all receive the event", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    const events1 = [];
    const events2 = [];
    const events3 = [];

    emitter.subscribe((event) => {
      events1.push(event);
    });
    emitter.subscribe((event) => {
      events2.push(event);
    });
    emitter.subscribe((event) => {
      events3.push(event);
    });

    const event1 = {
      kind: "step_started",
      step_name: "step_a",
      prompt: "Start A",
      interaction_count: 1,
    };
    const event2 = {
      kind: "protocol_completed",
      protocol_name: "test_protocol",
    };

    emitter.emit(event1);
    emitter.emit(event2);

    // All three subscribers should have received both events in order.
    assert.strictEqual(events1.length, 2);
    assert.strictEqual(events2.length, 2);
    assert.strictEqual(events3.length, 2);

    assert.deepStrictEqual(events1[0], event1);
    assert.deepStrictEqual(events1[1], event2);
    assert.deepStrictEqual(events2[0], event1);
    assert.deepStrictEqual(events2[1], event2);
    assert.deepStrictEqual(events3[0], event1);
    assert.deepStrictEqual(events3[1], event2);
  });

  test("unsubscribe stops further delivery", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    const events1 = [];
    const events2 = [];

    const unsub1 = emitter.subscribe((event) => {
      events1.push(event);
    });
    const _unsub2 = emitter.subscribe((event) => {
      events2.push(event);
    });

    const event1 = {
      kind: "step_started",
      step_name: "step_1",
      prompt: "Do step 1",
      interaction_count: 1,
    };

    emitter.emit(event1);
    assert.strictEqual(events1.length, 1);
    assert.strictEqual(events2.length, 1);

    // Unsubscribe the first listener.
    unsub1();

    const event2 = {
      kind: "step_completed",
      step_name: "step_1",
      resolution: "complete",
    };

    emitter.emit(event2);

    // events1 should still have only 1 event (unsubscribed).
    // events2 should have 2 events (still subscribed).
    assert.strictEqual(events1.length, 1);
    assert.strictEqual(events2.length, 2);
    assert.deepStrictEqual(events2[1], event2);
  });

  test("reducer is applied before subscribers notified", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    let snapshot_during_event = null;

    emitter.subscribe(() => {
      // Capture the snapshot when the listener is called.
      snapshot_during_event = emitter.get_snapshot();
    });

    const event = {
      kind: "step_completed",
      step_name: "step_1",
      resolution: "complete",
    };

    // Before emit, progress is 0.
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 0);

    emitter.emit(event);

    // The listener's captured snapshot should show the reducer's result
    // (completed_step_count incremented).
    assert.strictEqual(snapshot_during_event.progress.completed_step_count, 1);

    // The current snapshot should also reflect the change.
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 1);
  });

  test("snapshot is readonly (TS-level; fresh object on each emit)", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    const snap1 = emitter.get_snapshot();

    // TypeScript enforces readonly at compile time. At runtime, JavaScript
    // does not prevent mutations on plain objects. This test documents the
    // intended behavior: the reducer produces a new snapshot object on each
    // emit, so even if someone mutates a stale snapshot, it does not affect
    // the current snapshot held by the emitter.

    // Get the snapshot, then emit an event to produce a new one.
    const event = {
      kind: "step_started",
      step_name: "step_1",
      prompt: "Do it",
      interaction_count: 1,
    };
    emitter.emit(event);

    const snap2 = emitter.get_snapshot();

    // snap1 and snap2 are different objects (different identity).
    assert.notStrictEqual(snap1, snap2);

    // Now mutate the old snapshot (this violates the readonly contract,
    // but we verify the emitter is not affected).
    snap1.current_step_name = "hacked";

    // snap1 is now mutated, but the emitter's current snapshot should
    // reflect the reducer's result, not the mutation.
    assert.strictEqual(snap2.current_step_name, "step_1");
    assert.strictEqual(emitter.get_snapshot().current_step_name, "step_1");

    // The old snapshot is garbage now, but that's the caller's problem
    // (they violated the readonly contract).
    assert.strictEqual(snap1.current_step_name, "hacked");
  });

  test("snapshot identity changes on every emit (new object each time)", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    const snap1 = emitter.get_snapshot();

    const event = {
      kind: "step_started",
      step_name: "step_1",
      prompt: "Do it",
      interaction_count: 1,
    };

    emitter.emit(event);

    const snap2 = emitter.get_snapshot();

    // Even though the reducer might return a new object, snap2 should be
    // a different object reference than snap1 (because the reducer creates
    // a new object via spread or explicit construction).
    // Note: this depends on the reducer's implementation. Our fixture reducer
    // uses spread syntax, so objects should differ.
    assert.notStrictEqual(snap1, snap2);
  });

  test("multiple emits accumulate reducer state", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    // Emit step_completed three times.
    emitter.emit({
      kind: "step_completed",
      step_name: "step_1",
      resolution: "complete",
    });
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 1);

    emitter.emit({
      kind: "step_completed",
      step_name: "step_2",
      resolution: "complete",
    });
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 2);

    emitter.emit({
      kind: "step_completed",
      step_name: "step_3",
      resolution: "complete",
    });
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 3);
  });

  test("step_completed with retry does not increment progress", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    // Emit step_completed with retry (not complete).
    emitter.emit({
      kind: "step_completed",
      step_name: "step_1",
      resolution: "retry",
    });

    // Progress should remain 0.
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 0);

    // Now emit a complete one.
    emitter.emit({
      kind: "step_completed",
      step_name: "step_1",
      resolution: "complete",
    });

    // Progress should be 1.
    assert.strictEqual(emitter.get_snapshot().progress.completed_step_count, 1);
  });

  test("protocol_completed clears current_step_name and sets is_complete", () => {
    const initial = createFixtureSnapshot();
    const reducer = createFixtureReducer();
    const emitter = createProtocolShellEmitter(initial, reducer);

    // Set a current step.
    emitter.emit({
      kind: "step_started",
      step_name: "step_1",
      prompt: "Do it",
      interaction_count: 1,
    });

    assert.strictEqual(emitter.get_snapshot().current_step_name, "step_1");
    assert.strictEqual(emitter.get_snapshot().is_complete, false);

    // Emit protocol_completed.
    emitter.emit({
      kind: "protocol_completed",
      protocol_name: "test_protocol",
    });

    // current_step_name should be cleared, is_complete should be true.
    assert.strictEqual(emitter.get_snapshot().current_step_name, null);
    assert.strictEqual(emitter.get_snapshot().is_complete, true);
  });
});
