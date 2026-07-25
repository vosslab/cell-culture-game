// Behavior tests for the read-only protocol outline. Uses the real TypeScript
// module through the repository's canonical tsx test loader.
//
// Run with: node --import tsx --test tests/test_step_outline.mjs

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import { order_steps_by_flow, step_status } from "../src/shell/regions/step_outline.tsx";

function make_step(step_name, next_step) {
  return {
    step_name,
    prompt: `Prompt for ${step_name}`,
    sequence: [],
    step_validator: { preset: "sequence_complete" },
    outcome: { on_success: "complete", on_failure: "retry" },
    next_step,
  };
}

function snapshot_at(current_step_name) {
  return {
    current_step_name,
    is_complete: false,
  };
}

describe("step outline flow order", () => {
  test("uses entry_step and next_step links when inline YAML-order input is shuffled", () => {
    const shuffled_steps = [
      make_step("finish", null),
      make_step("prepare", "load"),
      make_step("load", "finish"),
    ];

    const ordered_steps = order_steps_by_flow(shuffled_steps, "prepare");
    const ordered_names = ordered_steps.map((step) => step.step_name);

    assert.deepEqual(ordered_names, ["prepare", "load", "finish"]);
  });

  test("marks completed, current, and later steps from the authored flow", () => {
    const ordered_names = ["prepare", "load", "finish"];

    assert.deepEqual(
      ordered_names.map((step_name) => step_status(step_name, snapshot_at("load"), ordered_names)),
      ["complete", "current", "upcoming"],
    );
  });

  test("rejects a broken next_step link instead of inventing a display order", () => {
    const steps = [make_step("prepare", "missing_step")];

    assert.throws(() => order_steps_by_flow(steps, "prepare"), /cannot find step "missing_step"/);
  });

  test("rejects a next_step cycle instead of repeating outline cards", () => {
    const steps = [make_step("prepare", "load"), make_step("load", "prepare")];

    assert.throws(() => order_steps_by_flow(steps, "prepare"), /cycle at step "prepare"/);
  });
});
