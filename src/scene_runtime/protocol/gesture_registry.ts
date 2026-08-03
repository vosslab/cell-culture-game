// src/scene_runtime/protocol/gesture_registry.ts
//
// Single gesture-affordance registry keyed by the closed Gesture union. One row
// per gesture co-locates the five things the frozen affordance contract fixes
// for every gesture:
//
//   1. render      -- the visible control the student sees.
//   2. selectors   -- the stable data-* selectors the walker drives.
//   3. value       -- how the committed value leaves the affordance.
//   4. dispatch    -- the single step-machine public method the affordance calls.
//   5. walker_driver -- the visible-UI path the walker uses.
//
// This module replaces the scattered gesture-promotion shim that used to live
// inline in protocol_host.tsx (an ad-hoc ternary that decided click vs select).
// The promotion now lives in exactly one place (scene_click_to_command) and the
// single routing point (dispatch_gesture) mirrors scene_operations.ts's
// exhaustive `never` switch, so an unhandled gesture is a compile error rather
// than a silent fallthrough.
//
// All five gestures route to live step-machine methods: click, select, and
// type route through handle_click / handle_type_commit; adjust and drag route
// through handle_adjust_commit / handle_drag_commit, both fully implemented
// and wired into dispatch_gesture below. Every registry row's `wired` flag is
// true.
//
// References:
//   - docs/archive/decisions/affordance_contract.md (frozen contract)
//   - src/shell/adapter/types.ts (closed Gesture union)
//   - src/scene_runtime/protocol/step_machine.ts (StepMachineHandle dispatch)
//   - src/scene_runtime/protocol/scene_operations.ts (the never-dispatch mirror)
//   - src/shell/hud/type_input.tsx (the template gesture, already co-located)

import type { Gesture } from "../../shell/adapter/types.js";
import type { StepMachineHandle } from "./step_machine.js";

//============================================
// Per-gesture affordance descriptor
//============================================

// Render shape of a gesture's affordance. Descriptive marker, not a widget:
// the concrete control lives in its own module (rendered scene object, the
// TypeInput control, the SetPointEditor, and the host drag surface).
export type GestureRenderKind =
  "rendered_scene_object" | "type_input_overlay" | "set_point_editor_overlay" | "host_drag_surface";

// How the committed value leaves the affordance. "none" means the interaction
// itself (the click / placement) is the whole signal.
export type GestureValueExtraction =
  "none" | "committed_text" | "committed_number" | "destination_placement";

// The single step-machine public method a gesture's affordance calls. Named so
// the frozen dispatch table is greppable and each gesture has exactly one entry.
export type GestureDispatchEntry =
  "handle_click" | "handle_type_commit" | "handle_adjust_commit" | "handle_drag_commit";

// One registry row. All five frozen contract slots for one gesture, co-located.
export interface GestureAffordance {
  readonly gesture: Gesture;
  readonly render: GestureRenderKind;
  // Stable data-* selectors from the frozen contract's selector families.
  readonly selectors: readonly string[];
  readonly value: GestureValueExtraction;
  readonly dispatch_entry: GestureDispatchEntry;
  // Whether dispatch_gesture routes this gesture to a live step-machine method.
  // All five gestures are wired.
  readonly wired: boolean;
  // Walker driver reference: the name of the visible-UI driver the Playwright
  // walker uses (tests/playwright/e2e/walker_helpers.mjs). A reference, not a
  // call: the walker is a separate .mjs harness, so the registry names the
  // driver rather than importing it.
  readonly walker_driver: string;
}

//============================================
// The registry (keyed by the closed Gesture union)
//============================================

// Record<Gesture, ...> forces every closed-set gesture to have exactly one row:
// omitting a key or adding a sixth is a compile error. The five keys ARE the
// closed gesture set; there is no `default` row that silently accepts an unknown
// gesture. Values transcribe the frozen contract's dispatch table and selector
// families verbatim.
export const GESTURE_REGISTRY: Readonly<Record<Gesture, GestureAffordance>> = {
  // A directed click on one scene object. The rendered object IS the affordance.
  click: {
    gesture: "click",
    render: "rendered_scene_object",
    selectors: ['#scene-root [data-item-id="<placement_name>"]'],
    value: "none",
    dispatch_entry: "handle_click",
    wired: true,
    walker_driver: "clickTargetAndWaitProgress",
  },
  // Choosing the next-step object among the present scene objects. Same visible
  // affordance as click; the host promotes a click on the active target to
  // select (scene_click_to_command below).
  select: {
    gesture: "select",
    render: "rendered_scene_object",
    selectors: ['#scene-root [data-item-id="<placement_name>"]'],
    value: "none",
    dispatch_entry: "handle_click",
    wired: true,
    walker_driver: "clickTargetAndWaitProgress",
  },
  // Entering a value into a visible input and committing it. TypeInput control.
  type: {
    gesture: "type",
    render: "type_input_overlay",
    selectors: [
      "[data-type-input-panel]",
      "[data-type-input]",
      "[data-type-target]",
      "[data-type-commit]",
      "[data-type-reject-message]",
    ],
    value: "committed_text",
    dispatch_entry: "handle_type_commit",
    wired: true,
    walker_driver: "typeCommitAndWaitProgress",
  },
  // The SetPointEditor emits an AdjustCommand routed to
  // handle_adjust_commit. One shared numeric set-point editor serves every
  // set-point field.
  adjust: {
    gesture: "adjust",
    render: "set_point_editor_overlay",
    selectors: [
      "[data-adjust-panel]",
      "[data-adjust-input]",
      "[data-adjust-target]",
      "[data-adjust-decrement]",
      "[data-adjust-increment]",
      "[data-adjust-commit]",
      "[data-adjust-reject-message]",
    ],
    value: "committed_number",
    dispatch_entry: "handle_adjust_commit",
    wired: true,
    walker_driver: "adjustCommitAndWaitProgress",
  },
  // The host drag surface emits a DragCommand routed to
  // handle_drag_commit. Source is the interaction target; destination is derived
  // from the interaction's authored response (first LayoutMove.zone). No content
  // protocol authors a drag yet, so the wired path is proven by the step-machine
  // unit test plus the walker driver rather than a live content walk.
  drag: {
    gesture: "drag",
    render: "host_drag_surface",
    selectors: [
      "[data-drag-surface]",
      '#scene-root [data-item-id="<source_placement_name>"]',
      '#scene-root [data-item-id="<destination_placement_name>"]',
    ],
    value: "destination_placement",
    dispatch_entry: "handle_drag_commit",
    wired: true,
    walker_driver: "dragToAndWaitProgress",
  },
};

//============================================
// Gesture commands (the payload dispatch_gesture routes)
//============================================

// A resolved, ready-to-dispatch gesture. Discriminated on `gesture`, mirroring
// the SceneOperation union: each member carries exactly the payload its
// dispatch entry consumes. click/select carry only the target; type carries the
// committed text; adjust/drag carry their own payloads, and all five arms are
// wired into dispatch_gesture below.
export interface ClickCommand {
  readonly gesture: "click";
  readonly target: string;
}

export interface SelectCommand {
  readonly gesture: "select";
  readonly target: string;
}

export interface TypeCommand {
  readonly gesture: "type";
  readonly target: string;
  readonly committed_text: string;
}

export interface AdjustCommand {
  readonly gesture: "adjust";
  readonly target: string;
  readonly committed_number: number;
}

export interface DragCommand {
  readonly gesture: "drag";
  readonly target: string;
  readonly destination_placement: string;
}

export type GestureCommand =
  ClickCommand | SelectCommand | TypeCommand | AdjustCommand | DragCommand;

// Outcome of routing one gesture command. `accepted` carries the runtime's
// accept/reject signal for gestures whose dispatch entry returns one (type, and
// later adjust). click/select dispatch is fire-and-forget: the step machine
// emits its own interaction_rejected event, so `accepted` is null for them.
export interface GestureDispatchResult {
  readonly accepted: boolean | null;
}

//============================================
// Scene-click promotion (the replaced shim, now single-sourced)
//============================================

// Resolve a raw scene click into the gesture command the runtime should act on.
// This reproduces the promotion EXACTLY as the old inline ternary did (former
// protocol_host.tsx shim): a click on the active target while the active gesture
// is `select` becomes a select command; every other scene click stays a click
// command. A bare click is never promoted to adjust/drag/type; an active
// adjust/drag interaction reached by a click stays a click command and is
// handled by the click dispatch arm below.
export function scene_click_to_command(
  active_gesture: Gesture | null,
  active_target: string | null,
  clicked_target: string,
): GestureCommand {
  const is_active_target = active_target === clicked_target;
  if (is_active_target && active_gesture === "select") {
    return { gesture: "select", target: clicked_target };
  }
  return { gesture: "click", target: clicked_target };
}

//============================================
// Single dispatch point (mirrors scene_operations.ts never-dispatch)
//============================================

// Route one resolved gesture command to its single step-machine dispatch entry.
// This is the ONE place gesture routing happens; the frozen dispatch table's
// "one dispatch entry per gesture" rule is enforced here by construction. The
// switch mirrors create_scene_op_handler's exhaustive `never` default, so adding
// a sixth gesture to the union is a compile error, not a runtime fallthrough.
export function dispatch_gesture(
  machine: StepMachineHandle,
  command: GestureCommand,
): GestureDispatchResult {
  switch (command.gesture) {
    case "click": {
      // A directed scene-object click.
      machine.handle_click(command.target, "click");
      return { accepted: null };
    }
    case "select": {
      // A promoted click on the active target (correct_choice equality).
      machine.handle_click(command.target, "select");
      return { accepted: null };
    }
    case "type": {
      // The committed text routes to the sole type advance path; the returned
      // boolean drives the affordance's visible rejection message.
      const accepted = machine.handle_type_commit(command.target, command.committed_text);
      return { accepted };
    }
    case "adjust": {
      // The committed set-point routes to the sole adjust advance path; the
      // returned boolean drives the set-point editor's visible rejection message.
      const accepted = machine.handle_adjust_commit(command.target, command.committed_number);
      return { accepted };
    }
    case "drag": {
      // The resolved drop placement routes to the sole drag advance path; the
      // returned boolean is the host drag surface's accept signal.
      const accepted = machine.handle_drag_commit(command.target, command.destination_placement);
      return { accepted };
    }
    default: {
      // Compile-time exhaustiveness over the closed Gesture union. A new gesture
      // makes this assignment a TypeScript error until it is routed above.
      const exhaustive_check: never = command;
      throw new Error(
        `gesture_registry: unhandled gesture command: ${String(
          (exhaustive_check as GestureCommand).gesture,
        )}`,
      );
    }
  }
}
