// Read-only walker-debug state projections. These tests deliberately exercise
// exported pure helpers rather than the canonical browser walker, which remains
// a consumer and must never gain protocol-specific state logic.

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import {
  resolve_active_state_writes,
  snapshot_active_declared_state,
} from "../src/scene_runtime/protocol/walker_debug.ts";
import { create_scene_store } from "../src/scene_runtime/state/scene_store.ts";
import { build_store_scene_op_deps } from "../src/scene_runtime/protocol/scene_op_deps.ts";

function config_with_group_write() {
  return {
    protocol_name: "debug_projection_fixture",
    protocol_type: "mini_protocol",
    entry_step: "write_row",
    steps: [
      {
        step_name: "write_row",
        prompt: "Write row A.",
        sequence: [
          {
            target: "well_plate_96",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: {
              scene_operations: [
                {
                  type: "ObjectStateChange",
                  target: "well_plate_96.row_A",
                  state: { material_volume: 25, material_name: "cells" },
                },
                {
                  type: "ObjectStateChange",
                  target: "centrifuge",
                  state: { running: true },
                },
              ],
            },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ],
  };
}

describe("walker debug declared-state projection", () => {
  test("expands group writes in runtime order without collapsing repeatable state operations", () => {
    const writes = resolve_active_state_writes(config_with_group_write(), "write_row", 0);
    assert.strictEqual(writes.length, 13);
    assert.deepStrictEqual(writes[0], {
      target: "well_plate_96.A1",
      state: { material_name: "cells", material_volume: 25 },
    });
    assert.deepStrictEqual(writes[11], {
      target: "well_plate_96.A12",
      state: { material_name: "cells", material_volume: 25 },
    });
    assert.deepStrictEqual(writes[12], { target: "centrifuge", state: { running: true } });
  });

  test("returns no expected writes when no active interaction can be resolved", () => {
    assert.deepStrictEqual(resolve_active_state_writes(config_with_group_write(), null, 0), []);
    assert.deepStrictEqual(
      resolve_active_state_writes(config_with_group_write(), "write_row", 1),
      [],
    );
  });

  test("snapshots only active declared state, sorted and detached from mutable store records", () => {
    const store = create_scene_store();
    store.start_session(
      [
        { target: "centrifuge", object_name: "centrifuge" },
        { target: "bme_tube", object_name: "bme_tube" },
      ],
      [],
    );
    store.set_object_state("centrifuge", { running: true });
    const snapshot = snapshot_active_declared_state(store);
    assert.deepStrictEqual(Object.keys(snapshot), ["bme_tube", "centrifuge"]);
    assert.strictEqual(snapshot.centrifuge.running, true);
    snapshot.centrifuge.running = false;
    assert.strictEqual(store.state.centrifuge.state.running, true);
  });

  test("logs group members in the same concrete order as the state-operation runtime", () => {
    const store = create_scene_store({ cells: { label: "Cells", display_color: "#6c6c00" } });
    store.start_session([{ target: "well_plate_96", object_name: "well_plate_96" }], []);
    const deps = build_store_scene_op_deps(store, () => {});
    deps.apply_object_state({
      type: "ObjectStateChange",
      target: "well_plate_96.row_A",
      state: { material_name: "cells", material_volume: 25 },
    });
    assert.deepStrictEqual(
      store.state_delta_log.map((entry) => entry.target),
      Array.from({ length: 12 }, (_, index) => `well_plate_96.A${index + 1}`),
    );
    assert.deepStrictEqual(store.state_delta_log[0].after, {
      material_name: "cells",
      material_volume: 25,
    });
  });
});
