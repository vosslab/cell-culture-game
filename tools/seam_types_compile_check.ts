// tools/seam_types_compile_check.ts
//
// Compile-time-only assertions over the shell seam types. Picked up by
// tsconfig.lint.json (which scopes tsc to tests/**/*.ts and
// tools/**/*.ts). Not executed by any runtime test runner -- tsc is the
// only consumer.
//
// Purpose:
//   1. Fail the typecheck:lint gate if the seam union or snapshot shape
//      changes incompatibly (a variant removed, a field renamed).
//   2. Document the intended exhaustiveness pattern for consumers.
//
// Per docs/PYTEST_STYLE.md, this file asserts behavior (the type
// surface) not a tunable constant.

import type {
  ProtocolShellEvent,
  ProtocolShellEventKind,
  ShellViewSnapshot,
  Gesture,
  InteractionValidatorPreset,
  StepValidatorPreset,
} from "../src/shell/adapter/types";

//============================================
// 1. Every ProtocolShellEvent variant carries a `kind`.
//============================================

type EventKind = ProtocolShellEvent["kind"];
type _KindMatchesIndex = EventKind extends ProtocolShellEventKind ? true : false;
const _kind_match_check: _KindMatchesIndex = true;
void _kind_match_check;

//============================================
// 2. Exhaustiveness sentinel: a switch over the kind union with `never`
//    in the default branch forces the compiler to error if a variant is
//    added without a matching case.
//============================================

export function _check_exhaustive(event: ProtocolShellEvent): string {
  switch (event.kind) {
    case "protocol_loaded":
      return event.protocol_name;
    case "protocol_completed":
      return event.protocol_name;
    case "step_started":
      return event.step_name;
    case "step_completed":
      return event.step_name;
    case "interaction_validated":
      return event.target_name;
    case "interaction_rejected":
      return event.target_name;
    case "scene_changed":
      return event.to_scene;
    case "scene_operation_applied":
      return event.operation_type;
    case "timed_wait_started":
      return event.target_name;
    case "timed_wait_elapsed":
      return event.target_name;
    case "modal_opened":
      return event.modal_kind;
    case "modal_closed":
      return String(event.committed);
    case "help_opened":
      return event.topic;
    case "help_closed":
      return "help_closed";
    case "tray_changed":
      return String(event.items.length);
    default: {
      const _exhaustive: never = event;
      return _exhaustive;
    }
  }
}

//============================================
// 3. Snapshot shape: assert required fields exist with expected types.
//    Building a minimal snapshot literal forces the compiler to verify
//    every required field is present.
//============================================

const _snapshot_shape_check: ShellViewSnapshot = {
  protocol_name: "x",
  current_step_name: null,
  current_prompt: null,
  current_tip: null,
  current_interaction_index: 0,
  progress: { completed_step_count: 0, total_step_count: 0 },
  last_outcome: null,
  last_rejection: null,
  pending_validator_kind: null,
  modal: {
    is_open: false,
    kind: null,
    prompt: null,
    choices: [],
    invoking_target: null,
  },
  help: { is_open: false, topic: null },
  tray: { items: [] },
  active_scene_name: null,
  is_complete: false,
  active_interaction_target: null,
  active_interaction_label: null,
  active_interaction_gesture: null,
  pending_timed_wait: null,
};
void _snapshot_shape_check;

//============================================
// 4. Closed enums: at least one example value per enum compiles.
//============================================

const _gesture_check: Gesture = "click";
const _interaction_validator_check: InteractionValidatorPreset = "correct_target";
const _step_validator_check: StepValidatorPreset = "sequence_complete";
void _gesture_check;
void _interaction_validator_check;
void _step_validator_check;
