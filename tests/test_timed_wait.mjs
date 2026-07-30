import { test, describe } from "node:test";
import assert from "node:assert";

import { timed_wait_runtime_delay_ms } from "../src/scene_runtime/protocol/timed_wait.ts";

describe("TimedWait browser-clock projection", () => {
  test("compresses one lab hour to a brief acknowledgement", () => {
    assert.strictEqual(timed_wait_runtime_delay_ms(60), 300);
  });

  test("clamps short and long phases to an observable, walker-safe range", () => {
    assert.strictEqual(timed_wait_runtime_delay_ms(0.05), 300);
    assert.strictEqual(timed_wait_runtime_delay_ms(2_880), 600);
  });

  test("rejects invalid durations", () => {
    assert.throws(() => timed_wait_runtime_delay_ms(0), /positive finite/);
    assert.throws(() => timed_wait_runtime_delay_ms(Number.NaN), /positive finite/);
  });
});
