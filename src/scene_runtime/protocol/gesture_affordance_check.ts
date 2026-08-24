// src/scene_runtime/protocol/gesture_affordance_check.ts
//
// Load-time gesture-affordance invariant.
//
// This pass runs once at protocol load, inside create_step_machine, BESIDE
// validate_protocol_presets and validate_authored_validator_values, BEFORE any
// handler closure is built and BEFORE any browser session exists. It reads
// GESTURE_REGISTRY -- the single source of registered/wired gestures -- and
// rejects any authored interaction whose gesture has no registry row or whose
// row is not wired (wired: false). A gesture with no live affordance cannot be
// completed through the visible UI, so the protocol fails loud at load rather
// than trapping a student mid-walk when the click reaches an unaffordanced step.
//
// This centralizes the runtime affordance invariant that belongs at the
// interaction boundary rather than checking it only at click time. The
// invariant is data-driven off
// GESTURE_REGISTRY: it hardcodes no gesture list, so it grows automatically as
// the registry adds gestures or flips a row's wired flag.
//
// The pass owns ALL error behavior for the gesture check. It never falls back,
// never returns a silent false, and never wraps work in a broad try/catch.
//
// References:
//   - docs/PRIMARY_SPEC.md (closed gesture set, walker visible-UI requirement)
//   - src/scene_runtime/protocol/gesture_registry.ts (GESTURE_REGISTRY, wired flag)
//   - src/scene_runtime/protocol/authored_value_check.ts (the load-time pass
//     pattern this file mirrors: named error, location suffix, pass entry point)

import type { Gesture, ProtocolConfig } from "../../shell/adapter/types";
import { GESTURE_REGISTRY, type GestureAffordance } from "./gesture_registry";

//============================================
// Named author-facing error
//============================================

// Locating fields the error carries so the offending YAML interaction can be
// found without guessing.
interface GestureAffordanceLocation {
  readonly protocol_name: string;
  readonly step_name: string;
  readonly interaction_index: number;
  readonly target: string;
  readonly gesture: string;
}

// Build the shared "in protocol ... step ... interaction ... target ... gesture
// ..." suffix used by the error message.
function location_suffix(location: GestureAffordanceLocation): string {
  let suffix = ` in protocol "${location.protocol_name}",`;
  suffix += ` step "${location.step_name}",`;
  suffix += ` interaction index ${location.interaction_index},`;
  suffix += ` target "${location.target}",`;
  suffix += ` gesture "${location.gesture}".`;
  return suffix;
}

// An authored interaction names a gesture with no live affordance: either the
// gesture has no GESTURE_REGISTRY row at all, or its row is declared but not
// wired. Carries a detail sentence naming which of the two miss classes fired.
export class UnaffordancedGestureError extends Error {
  constructor(location: GestureAffordanceLocation, detail: string) {
    let message = `Authored interaction uses a gesture with no wired affordance`;
    message += location_suffix(location);
    message += ` ${detail}`;
    super(message);
    this.name = "UnaffordancedGestureError";
  }
}

//============================================
// Pass entry point
//============================================

// Validate that every authored interaction's gesture has a wired affordance in
// GESTURE_REGISTRY. Throws UnaffordancedGestureError on the first miss; returns
// normally when every gesture resolves to a wired registry row. Called inside
// create_step_machine, beside validate_protocol_presets and
// validate_authored_validator_values.
export function validate_gesture_affordances(config: ProtocolConfig): void {
  const protocol_name = config.protocol_name;
  // Read the registry through a string-keyed view so an out-of-set gesture (a
  // malformed config, or a synthesized test value) resolves to undefined rather
  // than being assumed present. noUncheckedIndexedAccess then types every lookup
  // as GestureAffordance | undefined, giving the absent-row branch below a real
  // narrowing target. GESTURE_REGISTRY stays the single source of truth; this is
  // only a read view over it.
  const registry: Readonly<Record<string, GestureAffordance>> = GESTURE_REGISTRY;

  for (const step of config.steps ?? []) {
    const step_name = step.step_name;
    step.sequence.forEach((interaction, interaction_index) => {
      const gesture: Gesture = interaction.gesture;
      const location: GestureAffordanceLocation = {
        protocol_name,
        step_name,
        interaction_index,
        target: interaction.target,
        gesture: String(gesture),
      };
      const affordance: GestureAffordance | undefined = registry[gesture];
      // Miss class 1: no registry row for this gesture at all.
      if (affordance === undefined) {
        const detail = `No affordance registry row is declared for this gesture.`;
        throw new UnaffordancedGestureError(location, detail);
      }
      // Miss class 2: the row exists but its affordance is not wired, so no
      // visible control can complete the interaction.
      if (!affordance.wired) {
        let detail = `Its affordance registry row is declared but not wired`;
        detail += ` (wired: false), so no visible control can complete it.`;
        throw new UnaffordancedGestureError(location, detail);
      }
    });
  }
}
