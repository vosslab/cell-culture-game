import assert from "node:assert/strict";
import { test } from "node:test";

import { isDistinctWrongOrderCandidate } from "./playwright/e2e/walker_helpers.mjs";

test("whole-object target excludes itself but accepts a different object", () => {
  assert.equal(isDistinctWrongOrderCandidate("plate", "plate"), false);
  assert.equal(isDistinctWrongOrderCandidate("plate", "pipette"), true);
});

test("exact target excludes its structured parent but accepts a sibling", () => {
  assert.equal(isDistinctWrongOrderCandidate("plate.B1", "plate"), false);
  assert.equal(isDistinctWrongOrderCandidate("plate.B1", "plate.A1"), true);
});

test("declared group excludes its structured parent but accepts another object", () => {
  assert.equal(isDistinctWrongOrderCandidate("plate.all_wells", "plate"), false);
  assert.equal(isDistinctWrongOrderCandidate("plate.all_wells", "dmso_tube"), true);
});

test("missing candidate is never accepted", () => {
  assert.equal(isDistinctWrongOrderCandidate("plate.all_wells", null), false);
});
