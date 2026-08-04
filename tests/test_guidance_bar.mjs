// Behavior tests for the action-rail cue. The authored prompt carries the
// protocol-specific teaching language; routing identifiers must stay internal.

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import {
  action_progress_copy,
  gesture_instruction,
  recovery_copy,
  selection_recovery_details,
} from "../src/shell/regions/guidance_bar.tsx";

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

  test("adjust gives the exact requested numeric value to the learner", () => {
    assert.strictEqual(
      gesture_instruction("adjust", "P200 micropipette", 25),
      "Set P200 micropipette to 25 using the control below.",
    );
  });

  test("select identifies the candidate set without revealing the correct target", () => {
    const copy = gesture_instruction("select", "Correct answer", 25);
    assert.match(copy, /blue outlined/);
    assert.doesNotMatch(copy, /Correct answer/);
    assert.doesNotMatch(copy, /25/);
  });

  test("type does not reveal its validator answer", () => {
    const copy = gesture_instruction("type", "cell count", 12345);
    assert.match(copy, /Enter/);
    assert.doesNotMatch(copy, /12345/);
  });

  test("uses a generic highlighted-action cue while no interaction is active", () => {
    assert.match(gesture_instruction(null, null), /highlighted next action/);
  });
});

describe("guidance-bar action progress", () => {
  test("shows ordinal progress for every active ordered interaction", () => {
    assert.strictEqual(action_progress_copy(0, 4), "Action 1 of 4");
    assert.strictEqual(action_progress_copy(1, 4), "Action 2 of 4");
    assert.strictEqual(action_progress_copy(3, 4), "Action 4 of 4");
  });

  test("does not show stale progress outside an active interaction", () => {
    assert.strictEqual(action_progress_copy(0, 0), null);
    assert.strictEqual(action_progress_copy(4, 4), null);
  });
});

describe("guidance-bar value recovery", () => {
  test("tells a typed-value learner to correct the entry", () => {
    const copy = recovery_copy({
      reason_code: "wrong_value",
      target_name: "ignored_internal_target",
      gesture: "type",
      selected_label: null,
      expected_label: null,
    });
    assert.match(copy, /correct the entry/);
    assert.doesNotMatch(copy, /ignored_internal_target/);
  });

  test("tells a numeric learner to adjust the value", () => {
    const copy = recovery_copy({
      reason_code: "wrong_value",
      target_name: "ignored_internal_target",
      gesture: "adjust",
      selected_label: null,
      expected_label: null,
    });
    assert.match(copy, /adjust the value/);
    assert.doesNotMatch(copy, /ignored_internal_target/);
  });

  test("names the next highlighted physical action without revealing a select answer", () => {
    assert.match(
      recovery_copy(
        {
          reason_code: "wrong_target",
          target_name: "wrong",
          gesture: "click",
          selected_label: null,
          expected_label: null,
        },
        "PBS bottle",
        "click",
      ),
      /PBS bottle/,
    );
    const selectCopy = recovery_copy(
      {
        reason_code: "wrong_target",
        target_name: "wrong",
        gesture: "select",
        selected_label: "Wrong answer",
        expected_label: "Correct answer",
      },
      "Correct answer",
      "select",
    );
    assert.match(selectCopy, /blue outlined/);
    assert.doesNotMatch(selectCopy, /Correct answer/);
  });

  test("repeats a rejected choice, the correct choice, and the authored reason", () => {
    const details = selection_recovery_details(
      {
        reason_code: "wrong_target",
        target_name: "wrong",
        gesture: "select",
        selected_label: "Continue running",
        expected_label: "Stop now",
      },
      "The dye front is already near the bottom of the gel.",
    );
    assert.deepStrictEqual(details, {
      selected: "Continue running",
      correct: "Stop now",
      why: "The dye front is already near the bottom of the gel.",
    });
  });
});
