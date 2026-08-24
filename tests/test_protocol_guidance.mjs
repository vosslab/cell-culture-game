// Content-backed checks for required authored guidance on every semantic action.
// The generated registry is emitted from content/protocols/**/protocol.yaml,
// so this test exercises the same protocol objects consumed by the runtime.

import { test } from "node:test";
import assert from "node:assert/strict";

import { PROTOCOLS } from "../generated/protocols.ts";

function normalize_guidance(value) {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function flow_ordered_steps(protocol) {
  const by_name = new Map(protocol.steps.map((step) => [step.step_name, step]));
  const ordered = [];
  const seen = new Set();
  let next_name = protocol.entry_step;
  while (next_name !== null) {
    const step = by_name.get(next_name);
    assert.notEqual(
      step,
      undefined,
      `${protocol.protocol_name} points to missing step '${next_name}'`,
    );
    assert.equal(
      seen.has(step.step_name),
      false,
      `${protocol.protocol_name} flow loops at '${step.step_name}'`,
    );
    seen.add(step.step_name);
    ordered.push(step);
    next_name = step.next_step;
  }
  assert.equal(
    ordered.length,
    protocol.steps.length,
    `${protocol.protocol_name} flow must visit every authored step`,
  );
  return ordered;
}

test("every authored interaction has non-empty guidance", () => {
  for (const protocol of Object.values(PROTOCOLS)) {
    if (protocol.protocol_type !== "mini_protocol") {
      continue;
    }
    for (const step of protocol.steps) {
      for (const interaction of step.sequence) {
        const context = `${protocol.protocol_name}/${step.step_name} ${interaction.target}/${interaction.gesture}`;
        assert.equal(
          typeof interaction.instruction,
          "string",
          `${context} must define instruction`,
        );
        assert.equal(typeof interaction.hint, "string", `${context} must define hint`);
        assert.notEqual(
          normalize_guidance(interaction.instruction),
          "",
          `${context} instruction must be non-empty`,
        );
        assert.notEqual(
          normalize_guidance(interaction.hint),
          "",
          `${context} hint must be non-empty`,
        );
      }
    }
  }
});

test("adjacent authored actions use distinct instruction and hint guidance", () => {
  for (const protocol of Object.values(PROTOCOLS)) {
    if (protocol.protocol_type !== "mini_protocol") {
      continue;
    }
    let previous = null;
    for (const step of flow_ordered_steps(protocol)) {
      for (const interaction of step.sequence) {
        const current = {
          instruction: normalize_guidance(interaction.instruction),
          hint: normalize_guidance(interaction.hint),
          context: `${protocol.protocol_name}/${step.step_name} ${interaction.target}/${interaction.gesture}`,
        };
        if (previous !== null) {
          assert.notEqual(
            current.instruction,
            previous.instruction,
            `${current.context} repeats the immediately preceding instruction from ${previous.context}`,
          );
          assert.notEqual(
            current.hint,
            previous.hint,
            `${current.context} repeats the immediately preceding hint from ${previous.context}`,
          );
        }
        previous = current;
      }
    }
  }
});
