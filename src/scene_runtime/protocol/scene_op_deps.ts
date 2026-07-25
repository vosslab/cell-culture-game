// src/scene_runtime/protocol/scene_op_deps.ts
//
// Store-driven SceneOpDeps factory. Replaces the imperative attribute-poking
// build_scene_op_deps that lived in protocol_host.tsx. Each
// scene operation primitive writes the reactive scene_store (or drives the
// scene re-render) so the Solid renderer updates visible state automatically;
// no DOM attribute is patched here.
//
// Mapping (PRIMARY_SPEC.md "Scene operations"):
//   - ObjectStateChange -> scene_store.set_object_state (partial merge of
//     declared state fields; mounted scenes seed declared subparts up front,
//     with first-write seeding retained as a no-op safety net).
//   - CursorAttach      -> scene_store.set_cursor (attach/detach). The op
//     carries no material, so only the cursor_attached flag is driven; held
//     material is set by an ObjectStateChange on the held tool's
//     held_material_* fields.
//   - SceneChange       -> re-render the target scene through the same
//     generated YAML pipeline as the initial mount. Exact target identities
//     present in both scenes retain declared state; new targets seed defaults;
//     absent targets drop; transient flags reset; cursor-held tool/material is
//     then restored for a carried target.
//   - LayoutMove        -> fails loudly until the layout engine exposes a
//     placement-override write surface. Accepting an operation without moving
//     the object would report false success.
//   - TimedWait         -> writes runtime equipment-phase flags for the render
//     layer and delegates elapsed scheduling to the host.
//
// References:
//   - docs/PRIMARY_SPEC.md (scene operations)
//   - docs/active_plans/active/ (LayoutMove Option A decision,
//     walker debug surface)
//   - src/scene_runtime/state/scene_store.ts (store API)
//   - src/scene_runtime/protocol/scene_operations.ts (SceneOpDeps interface)

import type {
  ObjectStateChangeOp,
  CursorAttachOp,
  SceneChangeOp,
  LayoutMoveOp,
  TimedWaitOp,
} from "../../shell/adapter/types.js";
import type { SceneStore, StateValue, TargetSeed } from "../state/scene_store.js";
import { expand_subpart_group_target } from "../state/subpart_group_expand.js";
import type { SceneOpDeps } from "./scene_operations.js";

//============================================
// Cursor-held snapshot (transition carry)
//============================================

// One cursor-held target carried across a SceneChange. Declared object state is
// reconciled by the store; cursor attachment lives in transient runtime flags,
// so it is snapshotted separately and restored after the scene mount.
interface CursorCarry {
  target: string;
  held_material_name: string | null;
  held_material_volume: number | null;
}

// Capture every cursor-attached target's held state from the store so it can
// be reapplied after SceneChange reconciliation. Reads only; no mutation.
function snapshot_cursor_carry(store: SceneStore): CursorCarry[] {
  const carry: CursorCarry[] = [];
  for (const target of Object.keys(store.state)) {
    const entry = store.state[target];
    if (entry === undefined) {
      continue;
    }
    if (entry.flags.cursor_attached) {
      carry.push({
        target,
        held_material_name: entry.flags.held_material_name,
        held_material_volume: entry.flags.held_material_volume,
      });
    }
  }
  return carry;
}

//============================================
// Subpart seeding for ObjectStateChange
//============================================

// Split a target into its object segment (before the first ".") to decide
// whether a write addresses a subpart instance that must be seeded first.
function object_segment(target: string): string {
  const dot = target.indexOf(".");
  return dot < 0 ? target : target.slice(0, dot);
}

//============================================
// Store-driven deps factory
//============================================

// Build the store-driven SceneOpDeps.
//
// store              the reactive scene store shared with the Solid renderer.
// render_scene       re-render a named scene into the scene root. The caller
//                    (protocol_host) owns reconciliation, mountScene, and the
//                    prior-root dispose. Cursor carry is applied here AFTER
//                    that closure runs.
export function build_store_scene_op_deps(
  store: SceneStore,
  render_scene: (scene_name: string) => void,
  schedule_timed_wait: (op: TimedWaitOp) => void = () => {},
): SceneOpDeps {
  const deps: SceneOpDeps = {
    //----------------------------------------
    apply_object_state(op: ObjectStateChangeOp): void {
      // Build the partial-merge write once; every fanned-out target receives the
      // same declared-state payload. The store validates every key against the
      // resolved schema and throws on an undeclared key/value.
      const partial: Record<string, StateValue> = {};
      for (const key of Object.keys(op.state)) {
        const value = op.state[key];
        if (value !== undefined) {
          partial[key] = value;
        }
      }
      // A group write ("well_plate_96.all_wells") fans out to every member
      // subpart so each member's own store slot (and its overlay) updates; a
      // bare object or single-subpart target resolves to itself. Data-driven off
      // the object's declared subpart_groups; no object or group name is
      // special-cased.
      const write_targets = expand_subpart_group_target(op.target);
      for (const write_target of write_targets) {
        // Mounted scenes seed declared subparts in build_seed_list. Retain this
        // idempotent first-write seed as a safety net for valid targets reached
        // outside normal mounting; it never resets an existing target.
        const obj = object_segment(write_target);
        if (write_target !== obj) {
          // Subpart target: ensure the instance is seeded WITHOUT disturbing any
          // sibling target's state. seed_target is a no-op when already present.
          const seed: TargetSeed = { target: write_target, object_name: obj };
          store.seed_target(seed);
        }
        store.set_object_state(write_target, partial);
      }
    },

    //----------------------------------------
    apply_cursor_attach(op: CursorAttachOp): void {
      // CursorAttach carries no material; drive only the cursor_attached flag.
      // Held material is set separately via an ObjectStateChange on the tool's
      // held_material_* fields, and is preserved by set_cursor on re-attach
      // only when this op explicitly re-supplied it (it never does here), so
      // an attach must not clobber an already-held material: read current held
      // state and carry it through.
      if (op.operation === "attach") {
        const entry = store.state[op.target];
        const held_name = entry?.flags.held_material_name ?? null;
        const held_volume = entry?.flags.held_material_volume ?? null;
        store.set_cursor(op.target, {
          attach: true,
          ...(held_name !== null ? { held_material_name: held_name } : {}),
          ...(held_volume !== null ? { held_material_volume: held_volume } : {}),
        });
      } else {
        store.set_cursor(op.target, { attach: false });
      }
    },

    //----------------------------------------
    apply_scene_change(op: SceneChangeOp): void {
      // Capture cursor-held tool/material BEFORE reconciliation resets runtime
      // flags, then reapply it after the caller mounts the new scene. Declared
      // state continuity and the destination target set are owned by the store.
      const carry = snapshot_cursor_carry(store);
      render_scene(op.to_scene);
      for (const c of carry) {
        // Only reapply to a target that exists in the new scene. A held tool
        // that is not placed in the next scene drops its cursor state (it is
        // not visible to re-attach to); this is the documented behavior.
        if (store.state[c.target] === undefined) {
          continue;
        }
        store.set_cursor(c.target, {
          attach: true,
          ...(c.held_material_name !== null ? { held_material_name: c.held_material_name } : {}),
          ...(c.held_material_volume !== null
            ? { held_material_volume: c.held_material_volume }
            : {}),
        });
      }
    },

    //----------------------------------------
    apply_layout_move(op: LayoutMoveOp): void {
      throw new Error(
        `LayoutMove cannot be applied: the runtime has no placement-override surface ` +
          `(target "${op.target}" -> zone "${op.zone}")`,
      );
    },

    //----------------------------------------
    start_timed_wait(op: TimedWaitOp): void {
      store.set_flags(op.target, {
        timed_wait_active: true,
        timed_wait_display: op.display ?? null,
      });
      schedule_timed_wait(op);
    },
  };
  return deps;
}
