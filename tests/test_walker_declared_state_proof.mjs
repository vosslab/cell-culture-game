// Focused contract tests for the walker evidence gate. These test only the
// read-only snapshots the browser walker consumes; they never mount a protocol
// or call a runtime API.

import test from "node:test";
import assert from "node:assert/strict";

import {
  expectedRejectedClickCount,
  wrongOrderAccountingProblem,
  shouldAwaitTimedStateWrite,
  validateDeclaredStateMutation,
} from "./playwright/e2e/helper_walker.mjs";
import { parseVisibleAdjustCue } from "./playwright/e2e/walker_helpers.mjs";

function state({
  revision,
  delta = null,
  stateDeltaLog = delta === null ? [] : [delta],
  writes = [],
  declaredState = {},
}) {
  return {
    stateRevision: revision,
    lastStateDelta: delta,
    stateDeltaLog,
    activeStateWrites: writes,
    declaredState,
  };
}

test("declared-state proof accepts final concrete write, revision, and scene snapshot", () => {
  const writes = [
    { target: "plate.A1", state: { material_name: "media", material_volume: 200 } },
    { target: "plate.A2", state: { material_name: "media", material_volume: 200 } },
  ];
  const before = state({ revision: 4, writes });
  const after = state({
    revision: 6,
    writes: [],
    delta: {
      target: "plate.A2",
      before: { material_name: "empty", material_volume: 0 },
      after: { material_name: "media", material_volume: 200 },
    },
    stateDeltaLog: [
      {
        target: "plate.A1",
        before: { material_name: "empty", material_volume: 0 },
        after: { material_name: "media", material_volume: 200 },
      },
      {
        target: "plate.A2",
        before: { material_name: "empty", material_volume: 0 },
        after: { material_name: "media", material_volume: 200 },
      },
    ],
    declaredState: {
      "plate.A1": { material_name: "media", material_volume: 200 },
      "plate.A2": { material_name: "media", material_volume: 200 },
    },
  });
  validateDeclaredStateMutation(before, after, "pipette", "dispense", 2);
});

test("declared-state proof rejects a missing revision for an authored state write", () => {
  const writes = [{ target: "tube", state: { material_volume: 10 } }];
  const before = state({ revision: 4, writes });
  const after = state({
    revision: 4,
    delta: { target: "tube", before: { material_volume: 0 }, after: { material_volume: 10 } },
  });
  assert.throws(
    () => validateDeclaredStateMutation(before, after, "tube", "dispense", 0),
    /declared_state_revision_missing/,
  );
});

test("declared-state snapshot compares the final value for repeated concrete writes", () => {
  const writes = [
    { target: "tube", state: { material_volume: 10 } },
    { target: "tube", state: { material_volume: 0, material_name: "empty" } },
  ];
  const before = state({ revision: 4, writes });
  const after = state({
    revision: 6,
    delta: {
      target: "tube",
      before: { material_volume: 10 },
      after: { material_volume: 0, material_name: "empty" },
    },
    stateDeltaLog: [
      { target: "tube", before: { material_volume: 0 }, after: { material_volume: 10 } },
      {
        target: "tube",
        before: { material_volume: 10 },
        after: { material_volume: 0, material_name: "empty" },
      },
    ],
    declaredState: { tube: { material_volume: 0, material_name: "empty" } },
  });
  validateDeclaredStateMutation(before, after, "pipette", "empty_tube", 1);
});

test("ordered delta log rejects a missing first write across a scene transition", () => {
  const writes = [
    { target: "source_tube", state: { material_volume: 0 } },
    { target: "destination_tube", state: { material_volume: 10 } },
  ];
  const before = state({
    revision: 8,
    writes,
    declaredState: { source_tube: { material_volume: 10 } },
  });
  const after = state({
    revision: 10,
    writes: [],
    delta: {
      target: "destination_tube",
      before: { material_volume: 0 },
      after: { material_volume: 10 },
    },
    // The scene transition removed source_tube, so only a full ordered log can
    // expose that its required source decrement never happened.
    stateDeltaLog: [
      {
        target: "destination_tube",
        before: { material_volume: 0 },
        after: { material_volume: 10 },
      },
    ],
    declaredState: { destination_tube: { material_volume: 10 } },
  });
  assert.throws(
    () => validateDeclaredStateMutation(before, after, "transfer_button", "transfer", 0),
    /declared_state_delta_count_mismatch/,
  );
});

test("declared-state proof permits a scene reconciliation revision without inventing a write", () => {
  const before = state({
    revision: 4,
    delta: { target: "tube", before: { material_volume: 0 }, after: { material_volume: 10 } },
  });
  const after = state({
    revision: 5,
    delta: { target: "tube", before: { material_volume: 0 }, after: { material_volume: 10 } },
  });
  validateDeclaredStateMutation(before, after, "next_scene_object", "move_scene", 0);
});

test("declared-state proof rejects a fabricated delta when no ObjectStateChange is authored", () => {
  const before = state({ revision: 4 });
  const after = state({
    revision: 5,
    delta: { target: "tube", before: { material_volume: 0 }, after: { material_volume: 10 } },
  });
  assert.throws(
    () => validateDeclaredStateMutation(before, after, "next_scene_object", "move_scene", 0),
    /declared_state_unexpected_delta/,
  );
});

test("timed wait defers declared-write validation until visible completion", () => {
  const delayedWrite = state({
    revision: 4,
    writes: [{ target: "cell_counter", state: { focused: true } }],
  });
  assert.equal(shouldAwaitTimedStateWrite(delayedWrite, true), true);
  assert.equal(shouldAwaitTimedStateWrite(delayedWrite, false), false);
  assert.equal(shouldAwaitTimedStateWrite(state({ revision: 4 }), true), false);
});

test("adjust refuses a hidden validator answer without a matching visible cue", () => {
  const hiddenValidatorAnswer = 10;
  assert.equal(hiddenValidatorAnswer, 10);
  assert.throws(
    () =>
      parseVisibleAdjustCue(
        { target: "pipette", gesture: "adjust", value: null, text: "Set the requested value." },
        "pipette",
      ),
    /adjust_visible_value_missing/,
  );
  assert.throws(
    () =>
      parseVisibleAdjustCue(
        { target: "pipette", gesture: "adjust", value: "10", text: "Set the requested value." },
        "pipette",
      ),
    /adjust_visible_value_unannounced/,
  );
  assert.equal(
    parseVisibleAdjustCue(
      { target: "pipette", gesture: "adjust", value: "10", text: "Set exactly 10 microliters." },
      "pipette",
    ),
    "10",
  );
});

test("wrong-click accounting accepts mandatory sibling probes in normal mode", () => {
  const summary = { wrongSiblingProbes: 6, wrongOrderInjections: 0 };
  assert.equal(expectedRejectedClickCount(summary), 6);
  assert.equal(wrongOrderAccountingProblem(summary, 6), null);
});

test("wrong-click accounting includes explicit negative-mode injections", () => {
  const summary = { wrongSiblingProbes: 12, wrongOrderInjections: 7 };
  assert.equal(expectedRejectedClickCount(summary), 19);
  assert.match(
    wrongOrderAccountingProblem(summary, 18),
    /wrong_order_accounting_mismatch: observed 18 rejected click\(s\), expected 19/,
  );
});
