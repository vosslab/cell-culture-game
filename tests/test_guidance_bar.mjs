// Behavior tests for the action-rail cue. The authored prompt carries the
// protocol-specific teaching language; routing identifiers must stay internal.

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import {
  action_progress_copy,
  recovery_copy,
  selection_recovery_details,
} from "../src/shell/regions/guidance_bar.tsx";
import { resolve_active_interaction_action } from "../src/scene_runtime/protocol/active_interaction_view.ts";

const resolvers = {
  to_placement: (target) => `placement_${target}`,
  to_label: (target) => target,
};

function action_for(
  gesture,
  target = "PBS",
  validator = { preset: "correct_target" },
  instruction = `Use the highlighted ${target} for this procedure step.`,
  hint = `The highlighted ${target} is ready for the next action.`,
) {
  return resolve_active_interaction_action(
    {
      target,
      gesture,
      instruction,
      hint,
      validator,
      response: { scene_operations: [] },
    },
    resolvers,
  );
}

describe("guidance-bar authored action cue", () => {
  test("uses the authored instruction and hint together", () => {
    assert.strictEqual(
      action_for(
        "adjust",
        "P200 micropipette",
        { preset: "target_with_value", value: { set_volume: 25 } },
        "Set the P200 micropipette to 25 using the control below.",
        "Set the volume before continuing with the transfer.",
      ).instruction,
      "Set the P200 micropipette to 25 using the control below.",
    );
  });

  test("select identifies the candidate set without revealing the correct target", () => {
    const copy = action_for(
      "select",
      "Correct answer",
      { preset: "correct_choice" },
      "Choose the option that matches the procedure.",
      "Compare the blue outlined options with the step goal before choosing.",
    ).instruction;
    assert.match(copy, /Choose/);
    assert.doesNotMatch(copy, /Correct answer/);
    assert.doesNotMatch(copy, /25/);
  });

  test("type does not reveal its validator answer", () => {
    const copy = action_for(
      "type",
      "cell count",
      { preset: "target_with_value", value: { reported_count: 12345 } },
      "Record the observation in the visible field.",
      "Use the measurement you observed in the preceding step.",
    ).instruction;
    assert.match(copy, /Record/);
    assert.doesNotMatch(copy, /12345/);
  });

  test("select hint stays generic and does not reveal the target label or value", () => {
    const hint = action_for(
      "select",
      "Correct answer",
      { preset: "correct_choice" },
      "Choose the option that matches the procedure.",
      "Compare the blue outlined options with the step goal before choosing.",
    ).hint;
    assert.match(hint, /blue outlined|available choices|compare/i);
    assert.doesNotMatch(hint, /Correct answer/);
    assert.doesNotMatch(hint, /25/);
  });

  test("type hint does not reveal the validator answer", () => {
    const hint = action_for(
      "type",
      "cell count",
      { preset: "target_with_value", value: { reported_count: 12345 } },
      "Record the observation in the visible field.",
      "Use the measurement you observed in the preceding step.",
    ).hint;
    assert.match(hint, /measurement|preceding step/i);
    assert.doesNotMatch(hint, /12345/);
  });

  test("adjust hint may expose the requested value", () => {
    const hint = action_for(
      "adjust",
      "P200 micropipette",
      { preset: "target_with_value", value: { set_volume: 25 } },
      "Set the P200 micropipette to 25 using the control below.",
      "Set the value to 25 before continuing with the transfer.",
    ).hint;
    assert.match(hint, /25/);
    assert.match(hint, /control|value|setting/i);
  });

  test("click hint gives positive authored guidance", () => {
    assert.strictEqual(
      action_for(
        "click",
        "PBS bottle",
        { preset: "correct_target" },
        "Open the PBS bottle.",
        "Use the highlighted bottle in the lab scene.",
      ).hint,
      "Use the highlighted bottle in the lab scene.",
    );
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
  test("default recovery leads with a positive next action", () => {
    const cases = [
      {
        rejection: {
          reason_code: "wrong_target",
          target_name: "wrong",
          gesture: "click",
          selected_label: null,
          expected_label: null,
        },
        expected_label: "PBS bottle",
        expected_gesture: "click",
      },
      {
        rejection: {
          reason_code: "wrong_value",
          target_name: "micropipette",
          gesture: "adjust",
          selected_label: null,
          expected_label: null,
        },
        expected_label: "P200 micropipette",
        expected_gesture: "adjust",
      },
      {
        rejection: {
          reason_code: "out_of_order",
          target_name: "wrong",
          gesture: "click",
          selected_label: null,
          expected_label: null,
        },
        expected_label: null,
        expected_gesture: null,
      },
    ];

    for (const { rejection, expected_label, expected_gesture } of cases) {
      const copy = recovery_copy(rejection, expected_label, expected_gesture);
      const first_sentence = copy.split(/[.!?]/u, 1)[0] ?? "";
      assert.match(
        first_sentence,
        /^(?:Target|Next|Use|Set|Enter|Move|Choose|Select|Complete|Try|Check)\b/i,
        `recovery must lead with its next action: ${copy}`,
      );
      assert.doesNotMatch(first_sentence, /\b(?:not|wrong|doesn't|does not)\b/i);
    }
  });

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
