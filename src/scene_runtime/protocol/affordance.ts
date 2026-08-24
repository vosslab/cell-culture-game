// src/scene_runtime/protocol/affordance.ts
//
// Pure, Solid-free affordance derivation for scene-object highlighting.
//
// The affordance ring shown on a scene object is DERIVED view state, not
// stored state. Per SolidJS guidance (concepts/effects.mdx: "avoid setting
// signals within effects... use createMemo to compute new values that rely on
// other reactive values"), the renderer computes each object's AffordanceKind
// with a createMemo from (active target, active gesture, this object's target,
// candidate set) read off the protocol snapshot signal. This module owns the
// PURE intent-to-kind mapping; it adds no store flag and runs no createEffect.
// Candidate-set enumeration depends on the layout/render PipelineResult and so
// lives in the renderer layer (renderer/affordance_candidates.ts), not here.
// See the affordance plan in docs/active_plans.
//
// Design subtlety driving the kind mapping: for a `select` step the active
// target IS the correct answer, so glowing it would spoil the choice. `select`
// therefore highlights the whole candidate SET equally (and never singles out
// the answer), while every other directed gesture glows the one active target.
//
// Layer boundary (PRIMARY_DESIGN.md): this is the protocol layer's
// intent-to-kind mapping. It names no SVG asset, reads no YAML, has no
// per-protocol branch, and does not change gesture dispatch.

import type { Accessor } from "solid-js";

import type { Gesture } from "../../shell/adapter/types.js";

//============================================
// Types
//============================================

// The three affordance states a scene object can be in.
//   "active"    -> the single directed object for a click/drag/adjust/type step
//   "candidate" -> one of the equally-ringed objects for a select step
//   "none"      -> no ring
export type AffordanceKind = "active" | "candidate" | "none";

// The gesture of the active interaction, or null when no interaction is active.
// Reuses the canonical Gesture union plus the no-active-interaction null case
// carried in ShellViewSnapshot.active_interaction.action (Gesture | null),
// so there is no parallel gesture vocabulary to drift from the canonical one.
export type AffordanceGesture = Gesture | null;

// Arguments to the pure compute_affordance_kind helper. All four inputs are
// plain values read by the caller (the renderer memo) at compute time; this
// helper performs no reactive reads of its own.
export interface ComputeAffordanceKindArgs {
  // The active interaction's target object name, or null when none is active.
  active_target: string | null;
  // The active interaction's gesture, or null when none is active.
  active_gesture: AffordanceGesture;
  // The object name this affordance kind is being computed for.
  item_target: string;
  // The set of resolver-accepted candidate object names for the active scene.
  // O(1) membership only; the renderer must NOT rebuild this per item.
  candidate_targets: ReadonlySet<string>;
}

// Accessor returning the active-interaction slice of the protocol snapshot.
// The renderer reads this in ARROW form INSIDE its memo (never passed as a
// plain object snapshot) so the snapshot dependency is tracked reactively and
// the ring updates automatically on every step/interaction/scene change.
export type ActiveAffordanceAccessor = Accessor<{
  active_target: string | null;
  active_gesture: AffordanceGesture;
}>;

//============================================
// Pure affordance-kind mapping
//============================================

// Compute the affordance kind for one scene object. Pure: no Solid imports
// beyond the Accessor type alias above, no I/O, no global state. Rules:
//   - `select` gesture AND item in candidate_targets -> "candidate"
//     (every present candidate rings equally; the answer is never singled out)
//   - any OTHER directed gesture (click/drag/adjust/type) AND
//     item == active_target -> "active"
//   - otherwise -> "none"
export function compute_affordance_kind(args: ComputeAffordanceKindArgs): AffordanceKind {
  const { active_target, active_gesture, item_target, candidate_targets } = args;

  // Select step: ring the whole candidate set equally, never the answer alone.
  if (active_gesture === "select") {
    if (candidate_targets.has(item_target)) {
      return "candidate";
    }
    return "none";
  }

  // Every other directed gesture glows the single active target. A null gesture
  // (no active interaction) or a null active_target yields "none".
  if (active_gesture !== null && active_target !== null && item_target === active_target) {
    return "active";
  }

  return "none";
}
