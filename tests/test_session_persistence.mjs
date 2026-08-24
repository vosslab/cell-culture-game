// Browser-session persistence boundary tests.

import { describe, test } from "node:test";
import assert from "node:assert";

import { SCHEMA_VERSION } from "../src/schema_version.ts";
import {
  PROTOCOL_SESSION_STORAGE_KEY,
  create_protocol_session_persistence,
  fingerprint_protocol,
} from "../src/scene_runtime/protocol/session_persistence.ts";

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    this.values.set(key, value);
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

function checkpoint(overrides = {}) {
  return {
    active_step_name: "first",
    interaction_index: 1,
    completed_step_names: [],
    current_scene: "workspace",
    is_complete: false,
    pending_timed_wait: null,
    ...overrides,
  };
}

describe("protocol session persistence", () => {
  test("fingerprints the exact protocol shape deterministically", () => {
    const first = {
      protocol_name: "demo",
      protocol_type: "mini_protocol",
      entry_step: "first",
      steps: [],
    };
    const changed = { ...first, entry_step: "second" };
    assert.strictEqual(fingerprint_protocol(first), fingerprint_protocol(first));
    assert.notStrictEqual(fingerprint_protocol(first), fingerprint_protocol(changed));
  });

  test("round-trips a validated session through one versioned storage key", () => {
    const storage = new MemoryStorage();
    const persistence = create_protocol_session_persistence(storage, "demo", "shape-a");
    assert.deepStrictEqual(persistence.load(), { kind: "fresh", session: null });

    const revision = persistence.save(
      checkpoint(),
      { centrifuge: { running: true, set_rpm: 1200 } },
      [
        {
          target: "centrifuge",
          cursor_attached: true,
          held_material_name: null,
          held_material_volume: null,
        },
      ],
      7,
    );
    assert.strictEqual(revision, 1);
    assert.deepStrictEqual([...storage.values.keys()], [PROTOCOL_SESSION_STORAGE_KEY]);

    const reloaded = create_protocol_session_persistence(storage, "demo", "shape-a").load();
    assert.strictEqual(reloaded.kind, "restored");
    assert.strictEqual(reloaded.session.persistence_revision, 1);
    assert.strictEqual(reloaded.session.state_revision, 7);
    assert.deepStrictEqual(reloaded.session.machine, checkpoint());
    assert.deepStrictEqual(reloaded.session.declared_state.centrifuge, {
      running: true,
      set_rpm: 1200,
    });
  });

  test("discards stale protocol progress without deleting another protocol", () => {
    const storage = new MemoryStorage();
    const first = create_protocol_session_persistence(storage, "first", "shape-a");
    const second = create_protocol_session_persistence(storage, "second", "shape-b");
    first.save(checkpoint(), {}, [], 0);
    second.save(checkpoint(), {}, [], 0);

    const stale = create_protocol_session_persistence(storage, "first", "shape-new").load();
    assert.deepStrictEqual(stale, { kind: "discarded", session: null });
    assert.strictEqual(
      create_protocol_session_persistence(storage, "second", "shape-b").load().kind,
      "restored",
    );
  });

  test("removes malformed or wrong-version data instead of restoring it", () => {
    const storage = new MemoryStorage();
    storage.setItem(PROTOCOL_SESSION_STORAGE_KEY, "not json");
    const malformed = create_protocol_session_persistence(storage, "demo", "shape-a").load();
    assert.deepStrictEqual(malformed, { kind: "discarded", session: null });
    assert.strictEqual(storage.getItem(PROTOCOL_SESSION_STORAGE_KEY), null);

    storage.setItem(
      PROTOCOL_SESSION_STORAGE_KEY,
      JSON.stringify({ schema_version: SCHEMA_VERSION + 1, sessions: {} }),
    );
    const wrong_version = create_protocol_session_persistence(storage, "demo", "shape-a").load();
    assert.deepStrictEqual(wrong_version, { kind: "discarded", session: null });
    assert.strictEqual(storage.getItem(PROTOCOL_SESSION_STORAGE_KEY), null);
  });

  test("clears only the active protocol session", () => {
    const storage = new MemoryStorage();
    const first = create_protocol_session_persistence(storage, "first", "shape-a");
    const second = create_protocol_session_persistence(storage, "second", "shape-b");
    first.save(checkpoint(), {}, [], 0);
    second.save(checkpoint(), {}, [], 0);

    assert.strictEqual(first.clear(), true);
    assert.strictEqual(first.load().kind, "fresh");
    assert.strictEqual(second.load().kind, "restored");
  });
});
