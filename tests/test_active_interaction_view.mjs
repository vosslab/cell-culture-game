// Unit coverage for the canonical runtime-owned active interaction projection.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  actionable_active_interaction_view,
  resolve_active_interaction_action,
  unavailable_active_interaction_view,
} from "../src/scene_runtime/protocol/active_interaction_view.ts";

const resolvers = {
  to_placement: (target) => `placement_${target}`,
  to_label: (target) => `Label for ${target}`,
};

function interaction(
  gesture,
  target = "target",
  validator = { preset: "correct_target" },
  instruction = "Click the highlighted lab control.",
  hint = "Use the visible highlighted control to continue.",
) {
  return {
    target,
    gesture,
    instruction,
    hint,
    validator,
    response: { scene_operations: [] },
  };
}

test("authored instruction and hint are selected as an atomic pair", () => {
  const action = resolve_active_interaction_action(
    {
      ...interaction("click", "heat_block"),
      instruction: "Close the heat-block lid to begin incubation.",
      hint: "The rack is already inside; closing the lid starts the process.",
    },
    resolvers,
  );

  assert.deepEqual(
    [action.instruction, action.hint],
    [
      "Close the heat-block lid to begin incubation.",
      "The rack is already inside; closing the lid starts the process.",
    ],
  );
});

test("authored select and type guidance remain answer-safe before an attempt", () => {
  const select = resolve_active_interaction_action(
    interaction(
      "select",
      "correct_choice",
      { preset: "correct_choice" },
      "Choose the option that matches the procedure.",
      "Compare the outlined options with the step goal before choosing.",
    ),
    resolvers,
  );
  const type = resolve_active_interaction_action(
    interaction(
      "type",
      "counter",
      { preset: "target_with_value", value: { reported_count: 12345 } },
      "Record the observation in the visible field.",
      "Use the measurement you observed in the preceding step.",
    ),
    resolvers,
  );

  assert.doesNotMatch(
    `${select.instruction} ${select.hint}`,
    /correct_choice|placement_correct_choice/i,
  );
  assert.doesNotMatch(`${type.instruction} ${type.hint}`, /12345/);
});

test("timed-wait projection retains index and count while clearing the action", () => {
  assert.deepEqual(unavailable_active_interaction_view(3, 5, "timed_wait"), {
    index: 3,
    count: 5,
    availability: "timed_wait",
    action: null,
  });
  assert.deepEqual(unavailable_active_interaction_view(5, 5, "transition"), {
    index: 5,
    count: 5,
    availability: "transition",
    action: null,
  });
});

test("actionable projection exposes its authoritative sequence position", () => {
  const view = actionable_active_interaction_view(2, 4, interaction("click", "tube"), resolvers);
  assert.equal(view.index, 2);
  assert.equal(view.count, 4);
  assert.equal(view.availability, "actionable");
  assert.equal(view.action?.placement_name, "placement_tube");
});
