// Behavior tests for the action-rail cue. The authored prompt carries the
// protocol-specific teaching language; routing identifiers must stay internal.

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import { gesture_instruction, recovery_copy } from "../src/shell/regions/guidance_bar.tsx";

describe("guidance-bar gesture cue", () => {
  const learner_actions = [
    ["click", /Click PBS/],
    ["drag", /Move PBS/],
    ["adjust", /Set.*PBS/],
    ["type", /Enter.*PBS/],
  ];

  for (const [gesture, expected_copy] of learner_actions) {
    test(`${gesture} gives a visible learner-facing action`, () => {
      assert.match(gesture_instruction(gesture, "PBS"), expected_copy);
    });
  }

  test("select identifies the candidate set without revealing the correct target", () => {
    const copy = gesture_instruction("select", "Correct answer");
    assert.match(copy, /blue outlined/);
    assert.doesNotMatch(copy, /Correct answer/);
  });

  test("uses a generic highlighted-action cue while no interaction is active", () => {
    assert.match(gesture_instruction(null, null), /highlighted next action/);
  });
});

describe("guidance-bar value recovery", () => {
  test("tells a typed-value learner to correct the entry", () => {
    const copy = recovery_copy({
      reason_code: "wrong_value",
      target_name: "ignored_internal_target",
      gesture: "type",
    });
    assert.match(copy, /correct the entry/);
    assert.doesNotMatch(copy, /ignored_internal_target/);
  });

  test("tells a numeric learner to adjust the value", () => {
    const copy = recovery_copy({
      reason_code: "wrong_value",
      target_name: "ignored_internal_target",
      gesture: "adjust",
    });
    assert.match(copy, /adjust the value/);
    assert.doesNotMatch(copy, /ignored_internal_target/);
  });
});
