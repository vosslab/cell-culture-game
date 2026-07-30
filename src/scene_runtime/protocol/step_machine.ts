// src/scene_runtime/protocol/step_machine.ts
//
// Pure step machine for the typed protocol runtime. Owns step
// progression, interaction-index advancement, validator dispatch,
// scene-operation handoff, and ProtocolShellEvent emission via the
// injected RuntimeEmitterHandle.
//
// Public surface: create_step_machine() factory returning
// StepMachineHandle. No DOM, no globals, no window.
//
// References:
// - docs/PRIMARY_SPEC.md (entry_step, step structure, outcome
//   resolution, retry semantics, walker rule)
// - docs/specs/PROTOCOL_VOCABULARY.md (gesture, interaction, step,
//   sequence, response, scene_operations, validators)
// - docs/active_plans/active/web_ui/seam_interface.md (event lifecycle,
//   snapshot derivation)
// - src/shell/adapter/types.ts (closed seam)
// - src/scene_runtime/protocol/emitter.ts (RuntimeEmitterHandle, SnapshotReducer)
// - src/scene_runtime/protocol/validators.ts (validator dispatch)

import type {
  Gesture,
  InteractionRejectReason,
  InteractionValidatorPreset,
  ProtocolConfig,
  ProtocolShellEvent,
  ProtocolStep,
  SceneOperation,
  ShellViewSnapshot,
  StepValidatorPreset,
  ValidatorReference,
  ValidatorPreset,
} from "../../shell/adapter/types";
import type { RuntimeEmitterHandle, SnapshotReducer } from "./emitter";
// SceneOpHandler is defined canonically in scene_operations.ts (the module that
// builds the handler). Import it here (type-only, allowed within protocol/) and
// re-export so this module's existing public surface is unchanged.
import type { SceneOpHandler } from "./scene_operations";
import {
  dispatch_interaction_validator,
  dispatch_step_validator,
  type Interaction as ValidatorInteraction,
  type ProtocolStep as ValidatorStep,
  type ObjectStateSnapshot,
} from "./validators";
import { is_interaction_preset, is_step_preset } from "./preset_guards";
// Read-only schema-lookup seam. Type-only import: the protocol layer names the
// lookup shape but never imports scene_store/registry. The construction layer
// supplies the implementation through the options object.
import type { StateFieldLookup } from "./state_field_lookup";
// Load-time authored-value validation pass. Uses only the injected lookup plus
// ProtocolConfig; imports no store/registry.
import { validate_authored_validator_values } from "./authored_value_check";
// Load-time gesture-affordance invariant. Reads GESTURE_REGISTRY (the single
// source of registered/wired gestures) plus ProtocolConfig; imports no
// store/registry. It rejects unsupported gesture configurations during loading.
import { validate_gesture_affordances } from "./gesture_affordance_check";
// Load-time structure-derived pedagogy consistency invariant. Checks two
// narrow structured-claim shapes -- a "The N steps" learning-block claim and a
// prompt-named dotted target token -- against the authored structure; imports
// no store/registry.
import { validate_pedagogy_consistency } from "./pedagogy_consistency_check";
// Load-time target-existence invariant. Walks the reachable step
// graph, tracking scene transitions the same way the runtime does, and checks
// each authored target against a per-scene TargetAdapter; imports no
// store/registry.
import {
  validate_target_existence,
  validate_seeded_scene_operation_targets,
  validate_authored_subpart_targets,
  type SceneTargetAdapterResolver,
} from "./target_existence_check";
// Target-identity adapter seam. The step machine names the resolver shape
// but never builds it: the construction layer (protocol_host.tsx) supplies a
// scene-scoped adapter, so authored targets normalize to the unique DOM
// placement_name (equality, active_interaction_target) and back to the object
// store key (state reads). IDENTITY_TARGET_ADAPTER is the adapter-less default.
import { IDENTITY_TARGET_ADAPTER, type TargetAdapter } from "./target_adapter";

//============================================
// Public types
//============================================

// SceneOpHandler re-exported from its canonical home (scene_operations.ts).
export type { SceneOpHandler };

export interface StepMachineHandle {
  start(): void;
  handle_click(target: string, gesture: Gesture): void;
  handle_modal_close(committed: boolean, choice_id: string | null): void;
  handle_timer_elapsed(equipment_name: string): void;
  // Commit a typed value for the active `type` interaction. The committed text
  // is the raw string the student typed into the visible type-input affordance
  // (src/shell/hud/type_input.tsx). It is validated by the active interaction's
  // target_with_value preset: the typed text is coerced to the type of the
  // single field declared in the validator's `value` block and compared. A
  // match advances exactly like a validated click; a mismatch emits
  // interaction_rejected (wrong_value) and does NOT advance.
  // Returns true when the commit was accepted (validation passed) and false
  // when the commit was rejected (wrong value, wrong target, or no active step).
  handle_type_commit(target: string, typed_text: string): boolean;
  // Commit a numeric set-point for the active `adjust` interaction. The
  // committed_number is the value the student reached in the visible shared
  // numeric set-point editor (src/shell/hud/set_point_editor.tsx), whether by
  // stepper clicks or direct numeric entry. It is validated by the active
  // interaction's target_with_value preset: the number is coerced to the type of
  // the single field the validator's `value` block declares (the field's DECLARED
  // type, mirroring handle_type_commit's coercion, so a float set-point compares
  // as a float and an int as an int), then compared. A match advances exactly
  // like a validated click; a mismatch emits interaction_rejected (wrong_value)
  // and does NOT advance. Returns true on accept, false on reject.
  handle_adjust_commit(target: string, committed_number: number): boolean;
  // Commit a drag placement for the active `drag` interaction. `target` is the
  // dragged source scene object; `destination_placement` is the drop target's
  // placement_name (the destination scene object's data-item-id). The source is
  // checked against the interaction target and the destination against the
  // destination the interaction's authored response names (the `zone` of the
  // first LayoutMove scene_operation). A match applies the interaction response
  // and advances; the step's step_validator (for example final_state_matches)
  // then confirms the accepted final state. Returns true on accept, false on
  // reject.
  handle_drag_commit(target: string, destination_placement: string): boolean;
}

//============================================
// Snapshot reducer (exported for emitter wiring)
//============================================

// Empty starting snapshot. Fields populate as events arrive.
export function initial_snapshot(protocol_name: string): ShellViewSnapshot {
  const snapshot: ShellViewSnapshot = {
    protocol_name,
    current_step_name: null,
    current_prompt: null,
    // No step is active yet; tip is null until step_started fires.
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
  return snapshot;
}

// Helper to look up the current interaction's target and gesture
// from the config, given the step name and interaction index.
function get_active_interaction(
  config: ProtocolConfig,
  step_name: string | null,
  index: number,
): { target: string | null; gesture: Gesture | null } {
  if (!step_name) {
    return { target: null, gesture: null };
  }
  // sequence_runner protocols have no steps list; this helper is mini_protocol only.
  const steps = config.steps ?? [];
  const step = steps.find((s) => s.step_name === step_name);
  if (!step) {
    return { target: null, gesture: null };
  }
  if (index < 0 || index >= step.sequence.length) {
    return { target: null, gesture: null };
  }
  const interaction = step.sequence[index];
  if (!interaction) {
    return { target: null, gesture: null };
  }
  return {
    target: interaction.target,
    gesture: interaction.gesture,
  };
}

// Pure reducer mapping each ProtocolShellEvent to the next snapshot.
// See seam_interface.md "Snapshot derivation".
// The config is captured in the factory closure, below.
//
// resolve_target_to_placement normalizes the active interaction's authored
// target to the unique DOM placement_name before it enters the snapshot, so
// every consumer of active_interaction_target -- the walker's activeTarget
// projection, the select-promotion equality in protocol_host, and the scene
// item's affordance highlight -- sees the same placement_name the DOM stamps as
// data-item-id. Optional and defaulting to identity: pure unit tests and the
// config-only default reducer supply no scene adapter, and with no placements a
// target IS its own placement.
function create_snapshot_reducer(
  config: ProtocolConfig,
  resolve_target_to_placement: (target: string) => string = (target) => target,
  resolve_target_label: (target: string) => string = (target) => target,
): SnapshotReducer {
  // Resolve an active target to its placement_name, passing through null.
  function to_active_placement(target: string | null): string | null {
    if (target === null) {
      return null;
    }
    return resolve_target_to_placement(target);
  }
  // Resolve an authored target to the object library's learner-facing label,
  // passing through null. The host supplies the generated-label resolver;
  // adapter-less unit tests use the identity default.
  function to_active_label(target: string | null): string | null {
    if (target === null) {
      return null;
    }
    return resolve_target_label(target);
  }
  return (prev, event) => {
    switch (event.kind) {
      case "protocol_loaded": {
        const next: ShellViewSnapshot = {
          ...prev,
          protocol_name: event.protocol_name,
          progress: {
            completed_step_count: 0,
            total_step_count: event.total_step_count,
          },
          is_complete: false,
          last_rejection: null,
          active_interaction_target: null,
          active_interaction_label: null,
          active_interaction_gesture: null,
          pending_timed_wait: null,
        };
        return next;
      }
      case "step_started": {
        const active = get_active_interaction(config, event.step_name, 0);
        // Resolve the step's tip from config; null when absent.
        // sequence_runner protocols have no steps list; this path is mini_protocol only.
        const steps = config.steps ?? [];
        const started_step = steps.find((s) => s.step_name === event.step_name);
        const step_tip = started_step?.tip ?? null;
        const next: ShellViewSnapshot = {
          ...prev,
          current_step_name: event.step_name,
          current_prompt: event.prompt,
          current_tip: step_tip,
          current_interaction_index: 0,
          // A completed-step acknowledgement is useful only during the
          // transition itself. Once the next step becomes actionable, leave
          // the student with one unambiguous next action rather than a stale
          // success message from the preceding step.
          last_outcome: null,
          last_rejection: null,
          active_interaction_target: to_active_placement(active.target),
          active_interaction_label: to_active_label(active.target),
          active_interaction_gesture: active.gesture,
          pending_timed_wait: null,
        };
        return next;
      }
      case "interaction_validated": {
        const next_index = event.interaction_index + 1;
        const active = get_active_interaction(config, event.step_name, next_index);
        const next: ShellViewSnapshot = {
          ...prev,
          current_interaction_index: next_index,
          pending_validator_kind: event.validator_preset,
          last_rejection: null,
          active_interaction_target: to_active_placement(active.target),
          active_interaction_label: to_active_label(active.target),
          active_interaction_gesture: active.gesture,
        };
        return next;
      }
      case "interaction_rejected": {
        const next: ShellViewSnapshot = {
          ...prev,
          pending_validator_kind: event.validator_preset,
          last_rejection: {
            reason_code: event.reason_code,
            target_name: event.target_name,
            gesture: event.gesture,
          },
        };
        return next;
      }
      case "step_completed": {
        const completed_delta = event.resolution === "complete" ? 1 : 0;
        const next: ShellViewSnapshot = {
          ...prev,
          progress: {
            completed_step_count: prev.progress.completed_step_count + completed_delta,
            total_step_count: prev.progress.total_step_count,
          },
          last_outcome: {
            step_name: event.step_name,
            resolution: event.resolution,
            retry_count: 0,
          },
          current_interaction_index: 0,
          active_interaction_target: null,
          active_interaction_label: null,
          active_interaction_gesture: null,
          pending_timed_wait: null,
        };
        return next;
      }
      case "protocol_completed": {
        const next: ShellViewSnapshot = {
          ...prev,
          current_step_name: null,
          current_prompt: null,
          current_tip: null,
          last_rejection: null,
          is_complete: true,
          active_interaction_target: null,
          active_interaction_label: null,
          active_interaction_gesture: null,
          pending_timed_wait: null,
        };
        return next;
      }
      case "scene_changed": {
        // Re-resolve the active interaction's target against the newly-mounted
        // scene. A same-step SceneChange (authored in an interaction response)
        // swaps the live scene adapter; the active_interaction_target computed by
        // the preceding interaction_validated (or step_started) event was resolved
        // against the OLD scene's adapter and is now stale. By the time this event
        // fires, the scene-op handler has already rebound the adapter, so re-running
        // the resolver here maps the same semantic target onto the NEW scene's
        // placement. Without this, an adjust/type/click/select commit on the new
        // scene's node is scored against the old scene's placement and rejected as
        // out-of-order (the runtime's wrong-order counter increments and the step
        // stalls). This fixes the whole scene-change-completion family, not any one
        // protocol; it is data-driven off the active step + interaction index with
        // no protocol/step-name branch. A step-entry scene render (sequence_runner
        // boundary) also emits scene_changed, but the step_started that immediately
        // follows recomputes these fields for the new step, so this recompute is a
        // harmless transient there and the authoritative fix for a mid-step change.
        const active = get_active_interaction(
          config,
          prev.current_step_name,
          prev.current_interaction_index,
        );
        const next: ShellViewSnapshot = {
          ...prev,
          active_scene_name: event.to_scene,
          active_interaction_target: to_active_placement(active.target),
          active_interaction_label: to_active_label(active.target),
          active_interaction_gesture: active.gesture,
        };
        return next;
      }
      case "scene_operation_applied": {
        return prev;
      }
      case "timed_wait_started": {
        const next: ShellViewSnapshot = {
          ...prev,
          active_interaction_target: null,
          active_interaction_label: null,
          active_interaction_gesture: null,
          pending_timed_wait: {
            target_name: event.target_name,
            display: event.display,
            duration_min: event.duration_min,
          },
        };
        return next;
      }
      case "timed_wait_elapsed": {
        const active = get_active_interaction(
          config,
          prev.current_step_name,
          prev.current_interaction_index,
        );
        const next: ShellViewSnapshot = {
          ...prev,
          active_interaction_target: to_active_placement(active.target),
          active_interaction_label: to_active_label(active.target),
          active_interaction_gesture: active.gesture,
          pending_timed_wait: null,
        };
        return next;
      }
      case "modal_opened": {
        const next: ShellViewSnapshot = {
          ...prev,
          modal: {
            is_open: true,
            kind: event.modal_kind,
            prompt: event.prompt,
            choices: event.choices,
            invoking_target: event.invoking_target,
          },
        };
        return next;
      }
      case "modal_closed": {
        const next: ShellViewSnapshot = {
          ...prev,
          modal: {
            is_open: false,
            kind: null,
            prompt: null,
            choices: [],
            invoking_target: null,
          },
        };
        return next;
      }
      case "help_opened": {
        const next: ShellViewSnapshot = {
          ...prev,
          help: { is_open: true, topic: event.topic },
        };
        return next;
      }
      case "help_closed": {
        const next: ShellViewSnapshot = {
          ...prev,
          help: { is_open: false, topic: null },
        };
        return next;
      }
      case "tray_changed": {
        const next: ShellViewSnapshot = {
          ...prev,
          tray: { items: event.items },
        };
        return next;
      }
      default: {
        // Compile-time exhaustiveness.
        const exhaustion_check: never = event;
        throw new Error(`Unhandled event kind in reducer: ${String(exhaustion_check)}`);
      }
    }
  };
}

// Export a default reducer for use in tests or contexts without config access.
// This version cannot populate active_interaction_* fields, so those remain null.
// For full functionality, use create_snapshot_reducer with config.
const default_snapshot_reducer: SnapshotReducer = create_snapshot_reducer({
  protocol_name: "",
  protocol_type: "mini_protocol",
  entry_step: "",
  steps: [],
});

export { create_snapshot_reducer, default_snapshot_reducer as snapshot_reducer };

//============================================
// Internal helpers
//============================================

// Walk steps reachable from entry_step via next_step links. Returns
// the count of unique step_names reachable. Cycles (a step pointing
// back at an earlier step) are not counted twice.
function count_reachable_steps(config: ProtocolConfig): number {
  if (config.protocol_type === "sequence_runner") {
    const mini_protocols = config.mini_protocols ?? [];
    return mini_protocols.length;
  }
  const steps = config.steps ?? [];
  if (steps.length === 0) {
    return 0;
  }
  const by_name: Map<string, ProtocolStep> = new Map();
  for (const step of steps) {
    by_name.set(step.step_name, step);
  }
  const seen: Set<string> = new Set();
  let cursor: string | null = config.entry_step;
  while (cursor !== null && !seen.has(cursor)) {
    seen.add(cursor);
    const step = by_name.get(cursor);
    if (!step) {
      break;
    }
    cursor = step.next_step;
  }
  return seen.size;
}

// Convert a config Interaction into the shape validators.ts expects.
function to_validator_interaction(
  target: string,
  gesture: Gesture,
  preset: InteractionValidatorPreset,
  params: Record<string, unknown> | undefined,
): ValidatorInteraction {
  const validator_block: ValidatorInteraction["validator"] = params
    ? { preset, parameters: params }
    : { preset };
  const interaction: ValidatorInteraction = {
    target,
    gesture,
    validator: validator_block,
  };
  return interaction;
}

function validator_parameters(ref: ValidatorReference): Record<string, unknown> | undefined {
  // `value` is the sole authored spelling (vocabulary-closure patch; `params` alias removed).
  const authored_value = ref.value;
  if (authored_value === undefined) {
    return undefined;
  }
  const out: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(authored_value)) {
    out[key] = val;
  }
  return out;
}

// Project the authored step_validator into the {object_name: {field: value}}
// parameters shape validate_final_state_matches compares against. A
// final_state_matches step is authored as { target, contains }: a single object
// name plus a flat {field: value} map. Nest `contains` under `target` so the
// validator reads the same nested shape it expects. Every other step preset
// (sequence_complete) declares no parameters, so this returns undefined for them.
//
// This projection is the fix for the runtime bug where the old code read
// step_validator.value (undefined for final_state_matches) and so handed the
// validator no parameters, forcing a perpetual retry. Authoring uses
// .target/.contains, mirroring authored_value_check.ts.
function step_validator_parameters(ref: ValidatorReference): Record<string, unknown> | undefined {
  if (ref.preset !== "final_state_matches") {
    return undefined;
  }
  const target = ref.target;
  const contains = ref.contains;
  if (target === undefined || contains === undefined) {
    return undefined;
  }
  const fields: Record<string, unknown> = {};
  for (const [field, value] of Object.entries(contains)) {
    fields[field] = value;
  }
  const nested: Record<string, unknown> = {};
  nested[target] = fields;
  return nested;
}

// Convert a config ProtocolStep into the shape validators.ts expects.
function to_validator_step(step: ProtocolStep): ValidatorStep {
  const preset: StepValidatorPreset = narrow_step_preset(step.step_validator.preset);
  const sequence: ReadonlyArray<ValidatorInteraction> = step.sequence.map((interaction) =>
    to_validator_interaction(
      interaction.target,
      interaction.gesture,
      narrow_interaction_preset(interaction.validator.preset),
      validator_parameters(interaction.validator),
    ),
  );
  // Project the step-validator parameters from the authored shape. For
  // final_state_matches this nests `contains` under `target`; other step presets
  // carry no parameters. (Previously this read step_validator.value, which is
  // undefined for final_state_matches and starved the validator of parameters.)
  const parameters = step_validator_parameters(step.step_validator);
  const validator_block: ValidatorStep["step_validator"] = parameters
    ? {
        preset,
        parameters,
      }
    : { preset };
  const out: ValidatorStep = {
    step_name: step.step_name,
    sequence,
    step_validator: validator_block,
  };
  return out;
}

//============================================
// Load-time preset validation
//============================================

// Validate that every authored validator preset names a preset legal for the
// slot it occupies: a step's `step_validator` must use a step-family preset, and
// each interaction's `validator` must use an interaction-family preset. A
// violation throws once, at protocol load, with every locating field needed to
// find the offending YAML: the protocol name, the step name, the slot kind, the
// interaction index (when the slot is an interaction), the offending preset
// value, and the expected preset family for that slot.
function validate_protocol_presets(config: ProtocolConfig): void {
  const protocol_name = config.protocol_name;
  for (const step of config.steps ?? []) {
    const step_name = step.step_name;

    // Step slot: must be a step-family preset.
    const step_preset = step.step_validator.preset;
    if (!is_step_preset(step_preset)) {
      let message = `Invalid validator preset in protocol "${protocol_name}",`;
      message += ` step "${step_name}", slot "step_validator":`;
      message += ` preset "${String(step_preset)}" is not a step-family preset.`;
      message += ` Expected one of the step-family presets`;
      message += ` (sequence_complete, final_state_matches).`;
      throw new Error(message);
    }

    // Interaction slots: each must be an interaction-family preset.
    step.sequence.forEach((interaction, interaction_index) => {
      const interaction_preset = interaction.validator.preset;
      if (!is_interaction_preset(interaction_preset)) {
        let message = `Invalid validator preset in protocol "${protocol_name}",`;
        message += ` step "${step_name}",`;
        message += ` slot "interaction.validator" at interaction index ${interaction_index}:`;
        message += ` preset "${String(interaction_preset)}" is not an interaction-family preset.`;
        message += ` Expected one of the interaction-family presets`;
        message += ` (correct_target, correct_choice, target_with_value).`;
        throw new Error(message);
      }
    });
  }
}

// Narrow an authored step-slot preset to the step-family type. validate_protocol_presets()
// has already proven, at protocol load, that every step_validator preset is a step-family
// member; this narrow restates that proof for the type system at the use site without a
// lateral down-cast. The throw is unreachable in a loaded protocol and exists only so the
// function has a non-`never` narrowed return on every path.
function narrow_step_preset(preset: ValidatorPreset): StepValidatorPreset {
  if (!is_step_preset(preset)) {
    throw new Error(`Non-step-family preset reached step slot: "${String(preset)}".`);
  }
  return preset;
}

// Narrow an authored interaction-slot preset to the interaction-family type.
// Same load-time guarantee and unreachable-throw rationale as narrow_step_preset above.
function narrow_interaction_preset(preset: ValidatorPreset): InteractionValidatorPreset {
  if (!is_interaction_preset(preset)) {
    throw new Error(`Non-interaction-family preset reached interaction slot: "${String(preset)}".`);
  }
  return preset;
}

//============================================
// Factory
//============================================

// Construction-time options for create_step_machine. Threaded as an options
// object (not a positional arg) so future load-time validators can inject more
// read-only dependencies without churning the call signature again.
export interface StepMachineOptions {
  // Read-only declared-field lookup supplied by the construction layer. The
  // load-time authored-value validation pass consumes this to check every authored
  // validator value against the target's declared field type. This options object
  // only threads it through; the value checks land in authored_value_check.ts.
  lookup_state_field: StateFieldLookup;
  // Read-only observed object-state reader supplied by the construction layer.
  // Given a semantic target name, it returns that target's CURRENT declared-state
  // fields as a flat {field: value} map (the live scene_store observed state), or
  // an empty map when the target is not seeded. The pure protocol layer names the
  // shape but never imports scene_store; the construction layer supplies the impl.
  //
  // This is the genuine observed source both state-touching validators read:
  //   - handle_click feeds it to target_with_value so a click is judged against
  //     real store state, not the authored expected value (which always matched).
  //   - emit_step_validator_outcome builds the final_state_matches snapshot from
  //     it so a step passes or fails on observed state instead of retrying forever.
  read_object_state: ObjectStateReader;
  // Scene-scoped target-identity adapter. Supplied by the construction
  // layer, rebuilt per mounted scene. The equality path normalizes both the
  // authored interaction.target and the clicked value to the unique DOM
  // placement_name through resolve_to_placement; the state-read path normalizes
  // to the object_name store key through resolve_to_object. Optional and
  // defaulting to the identity adapter: pure unit tests supply no scene, and
  // with no placements a target is its own placement and object.
  target_adapter?: TargetAdapter;
  // Per-scene target-adapter resolver for the load-time target-existence
  // invariant. The construction layer eagerly builds a TargetAdapter
  // for every scene the protocol's reachable step graph can visit (via
  // collect_reachable_scene_names) and supplies this lookup so the check can
  // verify each authored target against the SCENE actually active at that
  // point in the flow, not only the entry scene. Optional and defaulting to a
  // resolver that always returns the single `target_adapter` above (or
  // IDENTITY): pure unit tests exercise one scene (or none) and see the same
  // behavior as before this option existed.
  resolve_scene_target_adapter?: SceneTargetAdapterResolver;
  // Initially-mounted scene name. Seeds the step machine's current-scene tracker
  // so the step-entry scene render fires ONLY on an actual scene change. The host
  // resolves this the same way it resolves the initial mount scene, so entering
  // the entry step (whose scene equals the mounted scene) causes no redundant
  // re-render. Optional: pure unit tests omit it, and with no step declaring a
  // scene the tracker is never consulted. This is the mechanism that plays
  // sequence_runner mini-protocol boundaries (each mini's flattened entry step
  // declares its resolved entry scene; entering it renders that scene).
  initial_scene?: string;
}

// Read-only observed object-state reader. See StepMachineOptions.read_object_state.
export type ObjectStateReader = (
  target: string,
) => Readonly<Record<string, string | number | boolean>>;

export function create_step_machine(
  config: ProtocolConfig,
  emitter: RuntimeEmitterHandle,
  scene_op_handler: SceneOpHandler,
  options: StepMachineOptions,
): StepMachineHandle {
  // Build step lookup once.
  const steps_by_name: Map<string, ProtocolStep> = new Map();
  for (const step of config.steps ?? []) {
    steps_by_name.set(step.step_name, step);
  }

  // Load-time preset validation. Validate every authored preset against the
  // slot family it occupies BEFORE any handler closure runs, so a misslotted or
  // unknown preset (a step preset in an interaction slot, or vice versa) fails
  // loud at protocol load with full locating fields, instead of surfacing as a
  // nameless `never` throw deep inside the step machine at runtime.
  validate_protocol_presets(config);

  // Load-time authored-value validation. Run BEFORE any handler closure, beside
  // validate_protocol_presets, so an authored validator value that targets an
  // unknown object/subpart/field, or that mistypes a resolved field, fails loud
  // at protocol load with full locating fields. Uses only the injected read-only
  // lookup plus ProtocolConfig; no store/registry import here.
  // The runtime numeric-coercion backstop in validators.ts remains as a backstop.
  const lookup_state_field: StateFieldLookup = options.lookup_state_field;
  validate_authored_validator_values({
    protocol_config: config,
    lookup_state_field,
  });

  // Load-time gesture-affordance invariant. Run BEFORE any handler closure,
  // beside the two validators above, so an authored interaction whose gesture
  // has no wired affordance in GESTURE_REGISTRY fails loud at protocol load with
  // full locating fields, before the emitter/handlers build and before any
  // browser session. The invariant is data-driven from the
  // registry, so it hardcodes no gesture list and needs no per-protocol branch.
  validate_gesture_affordances(config);

  // Load-time structure-derived pedagogy consistency invariant. Run BEFORE any
  // handler closure, beside the three checks above, so a "The N steps"
  // learning-block claim or a prompt-named dotted target token that no longer
  // matches the authored structure fails loud at protocol load, instead of
  // silently drifting out of sync with the steps a student actually walks.
  validate_pedagogy_consistency(config);

  // Scene-scoped target-identity adapter. Defaults to identity for the
  // adapter-less unit-test context. resolve_to_placement normalizes the equality
  // path to the DOM key; resolve_to_object normalizes the state-read path to the
  // object_name store key. Built here (moved above the target-existence check)
  // so the existence pass below has a default adapter to fall back on.
  const target_adapter: TargetAdapter = options.target_adapter ?? IDENTITY_TARGET_ADAPTER;

  // Load-time target-existence invariant. Run BEFORE any handler
  // closure, beside the three checks above, so an authored `target` that
  // resolves to no known placement or object in the SCENE ACTIVE AT THAT
  // POINT in the reachable step graph fails loud at protocol load with full
  // locating fields, instead of trapping a student mid-walk on an
  // unresolvable click target. Defaults to always resolving `target_adapter`
  // regardless of scene name, which is exactly the prior (pre-multi-scene)
  // behavior for the adapter-less/single-scene unit-test context.
  const resolve_scene_target_adapter: SceneTargetAdapterResolver =
    options.resolve_scene_target_adapter ?? ((): TargetAdapter => target_adapter);
  validate_target_existence(config, options.initial_scene ?? null, resolve_scene_target_adapter);

  // Load-time seeded scene-operation target invariant. Run BESIDE
  // validate_target_existence, using the same reachable-graph scene tracking,
  // so a store-writing scene operation whose target is not seeded in the scene
  // active where the operation executes fails loud at protocol load, instead of
  // degrading into a
  // misleading mid-walk torn-snapshot "no_active_interaction" when the runtime
  // op throws a `not seeded` error. A held tool that is only ever
  // cursor-attached (never state-mutated or timed) stays exempt.
  validate_seeded_scene_operation_targets(
    config,
    options.initial_scene ?? null,
    resolve_scene_target_adapter,
  );

  // Load-time subpart-suffix invariant. Run BESIDE the two above, on the same
  // reachable-graph scene tracking, so an authored "<object>.<suffix>" target
  // whose suffix names no declared subpart or subpart_group of that object fails
  // loud at load. Without it a group write (well_plate_96.all_wells) or a
  // per-well write would silently address a non-rendered pseudo-node mid-walk
  // with no visible change (has_target strips the suffix, so a typo'd group or
  // well currently passes prefix-only existence).
  validate_authored_subpart_targets(
    config,
    options.initial_scene ?? null,
    resolve_scene_target_adapter,
  );

  // Read-only observed object-state reader. Captured in the factory closure so
  // the click path and the step-validator snapshot both read the live scene
  // store instead of the authored expected values.
  const read_object_state: ObjectStateReader = options.read_object_state;

  // Mutable machine state.
  let active_step_name: string | null = null;
  let interaction_index = 0;
  let started = false;
  let completed = false;
  // A validated interaction pauses at its first TimedWait operation. Operations
  // after the wait remain queued so authored response order is preserved; the
  // timer callback resumes from next_operation_index without validating the
  // interaction a second time.
  let pending_timed_wait: {
    readonly step_name: string;
    readonly interaction_index: number;
    readonly target: string;
    readonly operations: ReadonlyArray<SceneOperation>;
    readonly next_operation_index: number;
  } | null = null;
  // Current rendered scene, tracked so the step-entry scene render fires only on
  // an actual change. Seeded from the initially-mounted scene and updated by both
  // the step-entry render and every authored SceneChange scene_operation.
  let current_scene: string | null = options.initial_scene ?? null;

  function current_step(): ProtocolStep | null {
    if (active_step_name === null) {
      return null;
    }
    return steps_by_name.get(active_step_name) ?? null;
  }

  function enter_step(step_name: string): void {
    const step = steps_by_name.get(step_name);
    if (!step) {
      throw new Error(`Unknown step_name in protocol: ${step_name}`);
    }
    active_step_name = step.step_name;
    interaction_index = 0;
    pending_timed_wait = null;
    // Step-entry scene render. ProtocolStep.scene is the authoritative
    // initial/transition scene for the step; when it names a scene different from
    // the one currently rendered, transition to it BEFORE step_started so the
    // step's first target is visible and the scene adapter is rebound for the new
    // scene. This is the general mechanism that plays sequence_runner boundaries:
    // each flattened constituent's entry step declares its resolved entry scene,
    // so entering it renders that scene. It is data-driven off step.scene with no
    // protocol-name branch; a step without a scene field (every normal
    // mini-protocol step) leaves behavior unchanged.
    if (typeof step.scene === "string" && step.scene !== "" && step.scene !== current_scene) {
      const scene_change_op: SceneOperation = { type: "SceneChange", to_scene: step.scene };
      // The handler re-renders the target scene (disposing the prior root and
      // rebuilding the scene adapter) before the reducer derives step_started's
      // active interaction against the new scene.
      scene_op_handler(scene_change_op);
      current_scene = step.scene;
      const scene_changed: ProtocolShellEvent = {
        kind: "scene_changed",
        from_scene: null,
        to_scene: step.scene,
      };
      emitter.emit(scene_changed);
    }
    const event: ProtocolShellEvent = {
      kind: "step_started",
      step_name: step.step_name,
      prompt: step.prompt,
      interaction_count: step.sequence.length,
    };
    emitter.emit(event);
  }

  function emit_applied_scene_op(op: SceneOperation): void {
    const target_name = "target" in op ? op.target : null;
    const applied: ProtocolShellEvent = {
      kind: "scene_operation_applied",
      operation_type: op.type,
      target_name,
    };
    emitter.emit(applied);
    if (op.type === "SceneChange") {
      current_scene = op.to_scene;
      const scene_changed: ProtocolShellEvent = {
        kind: "scene_changed",
        from_scene: null,
        to_scene: op.to_scene,
      };
      emitter.emit(scene_changed);
    }
  }

  function finish_validated_interaction(step: ProtocolStep): void {
    interaction_index += 1;
    if (interaction_index >= step.sequence.length) {
      emit_step_validator_outcome(step);
    }
  }

  function apply_response_scene_ops_from(
    step: ProtocolStep,
    ops: ReadonlyArray<SceneOperation>,
    start_index: number,
  ): void {
    for (let op_index = start_index; op_index < ops.length; op_index += 1) {
      const op = ops[op_index];
      if (op === undefined) {
        throw new Error(`Missing scene operation at response index ${String(op_index)}`);
      }
      if (op.type === "TimedWait") {
        pending_timed_wait = {
          step_name: step.step_name,
          interaction_index,
          target: op.target,
          operations: ops,
          next_operation_index: op_index + 1,
        };
      }
      scene_op_handler(op);
      emit_applied_scene_op(op);
      if (op.type === "TimedWait") {
        const wait_started: ProtocolShellEvent = {
          kind: "timed_wait_started",
          target_name: op.target,
          display: op.display ?? null,
          duration_min: op.duration_min,
        };
        emitter.emit(wait_started);
        return;
      }
    }
    finish_validated_interaction(step);
  }

  // Build the observed object-state snapshot a final_state_matches step validator
  // compares against, reading the live scene store for every object named in the
  // projected step-validator parameters. sequence_complete declares no
  // parameters, so its snapshot is empty and unused. Reading the real store here
  // is what lets final_state_matches pass or fail on observed state instead of
  // retrying forever against an empty default.
  function build_step_object_state_snapshot(validator_step: ValidatorStep): ObjectStateSnapshot {
    const parameters = validator_step.step_validator.parameters;
    if (parameters === undefined) {
      return {};
    }
    const snapshot: Record<string, Record<string, string | number | boolean>> = {};
    for (const object_name of Object.keys(parameters)) {
      // The final_state_matches parameters are keyed by authored target names.
      // Normalize each to the object_name store key before reading, so a target
      // authored as a placement_name still hits the object_name-keyed store. The
      // snapshot itself stays keyed by the authored name the validator projects.
      const store_key = target_adapter.resolve_to_object(object_name);
      snapshot[object_name] = { ...read_object_state(store_key) };
    }
    return snapshot;
  }

  function emit_step_validator_outcome(step: ProtocolStep): void {
    const preset = narrow_step_preset(step.step_validator.preset);
    const validator_step = to_validator_step(step);
    // Pass the real observed snapshot (was undefined, which the validator
    // defaulted to {} and never matched, forcing perpetual retry).
    const object_state_snapshot = build_step_object_state_snapshot(validator_step);
    const passed = dispatch_step_validator(
      preset,
      validator_step,
      step.sequence.length,
      object_state_snapshot,
    );
    if (passed) {
      const completed_event: ProtocolShellEvent = {
        kind: "step_completed",
        step_name: step.step_name,
        resolution: "complete",
      };
      emitter.emit(completed_event);
      if (step.next_step === null) {
        active_step_name = null;
        completed = true;
        const done_event: ProtocolShellEvent = {
          kind: "protocol_completed",
          protocol_name: config.protocol_name,
        };
        emitter.emit(done_event);
        return;
      }
      enter_step(step.next_step);
      return;
    }
    // Step validator failed: emit retry and restart the sequence.
    const retry_event: ProtocolShellEvent = {
      kind: "step_completed",
      step_name: step.step_name,
      resolution: "retry",
    };
    emitter.emit(retry_event);
    interaction_index = 0;
    const restart_event: ProtocolShellEvent = {
      kind: "step_started",
      step_name: step.step_name,
      prompt: step.prompt,
      interaction_count: step.sequence.length,
    };
    emitter.emit(restart_event);
  }

  function emit_rejection(
    step_name: string,
    index: number,
    target: string,
    gesture: Gesture,
    preset: ValidatorPreset,
    reason: InteractionRejectReason,
  ): void {
    // The reject event's validator_preset is an interaction preset.
    // For no_active_step we fall back to correct_target as a safe
    // default; the reason_code carries the real signal.
    const interaction_preset: InteractionValidatorPreset =
      preset === "sequence_complete" || preset === "final_state_matches"
        ? "correct_target"
        : preset;
    const event: ProtocolShellEvent = {
      kind: "interaction_rejected",
      step_name,
      interaction_index: index,
      target_name: target,
      gesture,
      validator_preset: interaction_preset,
      reason_code: reason,
    };
    emitter.emit(event);
  }

  function handle_validated(
    step: ProtocolStep,
    target: string,
    gesture: Gesture,
    preset: InteractionValidatorPreset,
  ): void {
    const validated: ProtocolShellEvent = {
      kind: "interaction_validated",
      step_name: step.step_name,
      interaction_index,
      target_name: target,
      gesture,
      validator_preset: preset,
    };
    emitter.emit(validated);
    // Apply scene operations for the validated interaction.
    const interaction = step.sequence[interaction_index];
    if (interaction) {
      apply_response_scene_ops_from(step, interaction.response.scene_operations, 0);
      return;
    }
    finish_validated_interaction(step);
  }

  //============================================
  // Public handle methods
  //============================================

  function start(): void {
    if (started) {
      return;
    }
    started = true;
    const total = count_reachable_steps(config);
    const loaded: ProtocolShellEvent = {
      kind: "protocol_loaded",
      protocol_name: config.protocol_name,
      entry_step_name: config.entry_step,
      total_step_count: total,
    };
    emitter.emit(loaded);
    enter_step(config.entry_step);
  }

  function handle_click(target: string, gesture: Gesture): void {
    const step = current_step();
    if (!started || completed || step === null) {
      emit_rejection(
        active_step_name ?? "",
        0,
        target,
        gesture,
        "correct_target",
        "no_active_step",
      );
      return;
    }
    const interaction = step.sequence[interaction_index];
    if (!interaction) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        gesture,
        "correct_target",
        "no_active_step",
      );
      return;
    }
    if (pending_timed_wait !== null) {
      const preset = narrow_interaction_preset(interaction.validator.preset);
      emit_rejection(step.step_name, interaction_index, target, gesture, preset, "out_of_order");
      return;
    }
    const preset = narrow_interaction_preset(interaction.validator.preset);
    // Out-of-order target or wrong gesture: reject as wrong_target. Normalize
    // BOTH sides through the adapter to the unique DOM placement_name before
    // comparing: the clicked `target` arrives as a placement_name (the DOM
    // data-item-id the click resolver read), and the authored interaction.target
    // is a semantic/object name. Resolving one side only would reintroduce the
    // object-vs-placement mismatch. resolve_to_placement is identity on a value
    // that is already a placement_name, so the clicked side is unchanged.
    const resolved_interaction_target = target_adapter.resolve_to_placement(interaction.target);
    const resolved_clicked_target = target_adapter.resolve_to_placement(target);
    if (
      resolved_interaction_target !== resolved_clicked_target ||
      interaction.gesture !== gesture
    ) {
      emit_rejection(step.step_name, interaction_index, target, gesture, preset, "wrong_target");
      return;
    }
    // Dispatch the preset validator. Clicks feed correct_target
    // or target_with_value; correct_choice is feed via modal. The validator
    // re-checks clicked_target === interaction.target internally, so feed it the
    // ADAPTER-RESOLVED placement on BOTH sides: build the validator
    // interaction with resolved_interaction_target and pass resolved_clicked_target.
    // Passing the raw authored target and the clicked placement_name would fail
    // the validator's own equality even though the step-machine equality above
    // matched.
    const validator_interaction = to_validator_interaction(
      resolved_interaction_target,
      interaction.gesture,
      preset,
      validator_parameters(interaction.validator),
    );
    // Observed value map for target_with_value comes from the LIVE scene store,
    // not the authored validator parameters. Reading the authored parameters here
    // compared the expected value against itself, so the check was always ok. The
    // store read makes a click whose target state does not match the authored
    // value fail with wrong_value. Normalize the clicked placement_name to the
    // object_name store key: the store is object_name-keyed, so a
    // placement_name would miss it and read {} incorrectly.
    const value_map =
      preset === "target_with_value"
        ? read_object_state(target_adapter.resolve_to_object(target))
        : {};
    const result = dispatch_interaction_validator(
      preset,
      validator_interaction,
      resolved_clicked_target,
      null,
      value_map,
    );
    if (!result.ok) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        gesture,
        preset,
        result.reason ?? "wrong_target",
      );
      return;
    }
    handle_validated(step, target, gesture, preset);
  }

  function handle_modal_close(committed: boolean, choice_id: string | null): void {
    const step = current_step();
    if (!started || completed || step === null) {
      // Emit a no_active_step rejection instead of a silent return, matching
      // handle_click/handle_type_commit, so a dropped modal-close event is
      // observable (interaction_rejected) rather than vanishing. No interaction
      // exists here, so target/gesture are neutral placeholders.
      emit_rejection(active_step_name ?? "", 0, "", "select", "correct_target", "no_active_step");
      return;
    }
    const interaction = step.sequence[interaction_index];
    if (!interaction) {
      emit_rejection(
        step.step_name,
        interaction_index,
        "",
        "select",
        "correct_target",
        "no_active_step",
      );
      return;
    }
    if (pending_timed_wait !== null) {
      const preset = narrow_interaction_preset(interaction.validator.preset);
      emit_rejection(
        step.step_name,
        interaction_index,
        interaction.target,
        interaction.gesture,
        preset,
        "out_of_order",
      );
      return;
    }
    const preset = narrow_interaction_preset(interaction.validator.preset);
    if (!committed) {
      // Cancel: emit interaction_rejected (reason: out_of_order) so the
      // shell sees the user dismissed the modal without committing.
      // interaction_index does not advance; the next click re-enters the
      // same interaction.
      emit_rejection(
        step.step_name,
        interaction_index,
        interaction.target,
        interaction.gesture,
        preset,
        "out_of_order",
      );
      return;
    }
    const validator_interaction = to_validator_interaction(
      interaction.target,
      interaction.gesture,
      preset,
      validator_parameters(interaction.validator),
    );
    const result = dispatch_interaction_validator(
      preset,
      validator_interaction,
      interaction.target,
      choice_id,
      {},
    );
    if (!result.ok) {
      emit_rejection(
        step.step_name,
        interaction_index,
        interaction.target,
        interaction.gesture,
        preset,
        result.reason ?? "wrong_value",
      );
      return;
    }
    handle_validated(step, interaction.target, interaction.gesture, preset);
  }

  function handle_timer_elapsed(equipment_name: string): void {
    const step = current_step();
    if (!started || completed || step === null) {
      // Emit a no_active_step rejection instead of a silent return, matching
      // handle_click/handle_type_commit, so a dropped timer-elapsed event is
      // observable (interaction_rejected). The equipment name is the target;
      // a timer has no gesture, so "click" is a neutral placeholder.
      emit_rejection(
        active_step_name ?? "",
        0,
        equipment_name,
        "click",
        "correct_target",
        "no_active_step",
      );
      return;
    }
    const pending = pending_timed_wait;
    if (pending === null) {
      emit_rejection(
        step.step_name,
        interaction_index,
        equipment_name,
        "click",
        "correct_target",
        "out_of_order",
      );
      return;
    }
    if (
      pending.step_name !== step.step_name ||
      pending.interaction_index !== interaction_index ||
      pending.target !== equipment_name
    ) {
      emit_rejection(
        step.step_name,
        interaction_index,
        equipment_name,
        "click",
        "correct_target",
        "out_of_order",
      );
      return;
    }
    pending_timed_wait = null;
    const wait_elapsed: ProtocolShellEvent = {
      kind: "timed_wait_elapsed",
      target_name: equipment_name,
    };
    emitter.emit(wait_elapsed);
    apply_response_scene_ops_from(step, pending.operations, pending.next_operation_index);
  }

  function handle_type_commit(target: string, typed_text: string): boolean {
    const step = current_step();
    if (!started || completed || step === null) {
      emit_rejection(active_step_name ?? "", 0, target, "type", "correct_target", "no_active_step");
      return false;
    }
    const interaction = step.sequence[interaction_index];
    if (!interaction) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "type",
        "correct_target",
        "no_active_step",
      );
      return false;
    }
    if (pending_timed_wait !== null) {
      const preset = narrow_interaction_preset(interaction.validator.preset);
      emit_rejection(step.step_name, interaction_index, target, "type", preset, "out_of_order");
      return false;
    }
    const preset = narrow_interaction_preset(interaction.validator.preset);
    // A type commit only applies to the active `type` interaction on its target.
    // The committed `target` is the type-input's active target, sourced from the
    // snapshot's active_interaction_target, which is now the adapter-resolved
    // placement_name. Normalize BOTH sides to placement_name so the authored
    // interaction.target (a semantic/object name) matches it.
    const resolved_type_interaction_target = target_adapter.resolve_to_placement(
      interaction.target,
    );
    const resolved_type_committed_target = target_adapter.resolve_to_placement(target);
    if (
      interaction.gesture !== "type" ||
      resolved_type_interaction_target !== resolved_type_committed_target
    ) {
      emit_rejection(step.step_name, interaction_index, target, "type", preset, "wrong_target");
      return false;
    }
    // Build the value_map from the typed text. target_with_value compares the
    // validator's declared `value` fields against this map. The visible type
    // input yields a single string; coerce it to each declared field's type so
    // a numeric field compares as a number, not a string.
    const expected = validator_parameters(interaction.validator) ?? {};
    const value_map = build_typed_value_map(expected, typed_text);
    // Feed the validator the ADAPTER-RESOLVED placement on both sides, same
    // as handle_click: the validator re-checks clicked_target === interaction.target
    // internally, and the committed `target` is a placement_name.
    const validator_interaction = to_validator_interaction(
      resolved_type_interaction_target,
      interaction.gesture,
      preset,
      expected,
    );
    const result = dispatch_interaction_validator(
      preset,
      validator_interaction,
      resolved_type_committed_target,
      null,
      value_map,
    );
    if (!result.ok) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "type",
        preset,
        result.reason ?? "wrong_value",
      );
      return false;
    }
    handle_validated(step, target, "type", preset);
    return true;
  }

  function handle_adjust_commit(target: string, committed_number: number): boolean {
    const step = current_step();
    if (!started || completed || step === null) {
      emit_rejection(
        active_step_name ?? "",
        0,
        target,
        "adjust",
        "correct_target",
        "no_active_step",
      );
      return false;
    }
    const interaction = step.sequence[interaction_index];
    if (!interaction) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "adjust",
        "correct_target",
        "no_active_step",
      );
      return false;
    }
    if (pending_timed_wait !== null) {
      const preset = narrow_interaction_preset(interaction.validator.preset);
      emit_rejection(step.step_name, interaction_index, target, "adjust", preset, "out_of_order");
      return false;
    }
    const preset = narrow_interaction_preset(interaction.validator.preset);
    // A set-point commit only applies to the active `adjust` interaction on its
    // target. The committed `target` is the set-point editor's active target,
    // sourced from the snapshot's active_interaction_target (the adapter-resolved
    // placement_name. Normalize BOTH sides to placement_name so the authored
    // interaction.target (a semantic/object name) matches it, mirroring
    // handle_type_commit.
    const resolved_adjust_interaction_target = target_adapter.resolve_to_placement(
      interaction.target,
    );
    const resolved_adjust_committed_target = target_adapter.resolve_to_placement(target);
    if (
      interaction.gesture !== "adjust" ||
      resolved_adjust_interaction_target !== resolved_adjust_committed_target
    ) {
      emit_rejection(step.step_name, interaction_index, target, "adjust", preset, "wrong_target");
      return false;
    }
    // Build the value_map from the committed number. target_with_value compares
    // the validator's declared `value` fields against this map. Coerce the number
    // through the SAME authored-value-directed path handle_type_commit uses
    // (build_typed_value_map keyed off each declared field's authored type), so a
    // float set-point (voltage 3.5) compares as a float and an int set-point
    // (set_volume 1000) as an int. A hard-coded numeric type would fail a float.
    const expected = validator_parameters(interaction.validator) ?? {};
    const value_map = build_typed_value_map(expected, String(committed_number));
    // Feed the validator the ADAPTER-RESOLVED placement on both sides, same
    // as handle_type_commit: the validator re-checks clicked_target ===
    // interaction.target internally, and the committed `target` is a placement_name.
    const validator_interaction = to_validator_interaction(
      resolved_adjust_interaction_target,
      interaction.gesture,
      preset,
      expected,
    );
    const result = dispatch_interaction_validator(
      preset,
      validator_interaction,
      resolved_adjust_committed_target,
      null,
      value_map,
    );
    if (!result.ok) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "adjust",
        preset,
        result.reason ?? "wrong_value",
      );
      return false;
    }
    handle_validated(step, target, "adjust", preset);
    return true;
  }

  function handle_drag_commit(target: string, destination_placement: string): boolean {
    const step = current_step();
    if (!started || completed || step === null) {
      emit_rejection(active_step_name ?? "", 0, target, "drag", "correct_target", "no_active_step");
      return false;
    }
    const interaction = step.sequence[interaction_index];
    if (!interaction) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "drag",
        "correct_target",
        "no_active_step",
      );
      return false;
    }
    if (pending_timed_wait !== null) {
      const preset = narrow_interaction_preset(interaction.validator.preset);
      emit_rejection(step.step_name, interaction_index, target, "drag", preset, "out_of_order");
      return false;
    }
    const preset = narrow_interaction_preset(interaction.validator.preset);
    // A drag commit only applies to the active `drag` interaction whose source is
    // the dragged object. Normalize BOTH sides to placement_name so the authored
    // interaction.target (semantic/object name) matches the committed source
    // placement_name, mirroring handle_click / handle_type_commit.
    const resolved_drag_source_target = target_adapter.resolve_to_placement(interaction.target);
    const resolved_drag_committed_source = target_adapter.resolve_to_placement(target);
    if (
      interaction.gesture !== "drag" ||
      resolved_drag_source_target !== resolved_drag_committed_source
    ) {
      emit_rejection(step.step_name, interaction_index, target, "drag", preset, "wrong_target");
      return false;
    }
    // Derive the accepted destination from EXISTING authored slots (no new YAML
    // field): the `zone` of the first LayoutMove scene_operation in the
    // interaction's response is where the drag moves the source object. Normalize
    // both the authored destination and the committed drop placement through the
    // adapter so the comparison is in placement space. A drag interaction that
    // authors no LayoutMove destination is an authoring gap: reject as wrong_value
    // so it fails loud rather than silently accepting any drop.
    const authored_destination = derive_drag_destination(interaction.response.scene_operations);
    if (authored_destination === null) {
      emit_rejection(step.step_name, interaction_index, target, "drag", preset, "wrong_value");
      return false;
    }
    const resolved_authored_destination = target_adapter.resolve_to_placement(authored_destination);
    const resolved_committed_destination =
      target_adapter.resolve_to_placement(destination_placement);
    if (resolved_authored_destination !== resolved_committed_destination) {
      emit_rejection(step.step_name, interaction_index, target, "drag", preset, "wrong_value");
      return false;
    }
    // Source + destination both accepted. Run the interaction's own preset
    // validator on the source (drag interactions validate the source with
    // correct_target; target_with_value would read live store state as
    // handle_click does), then apply the response and advance. The step's
    // step_validator (final_state_matches) confirms the accepted final state.
    const validator_interaction = to_validator_interaction(
      resolved_drag_source_target,
      interaction.gesture,
      preset,
      validator_parameters(interaction.validator),
    );
    const value_map =
      preset === "target_with_value"
        ? read_object_state(target_adapter.resolve_to_object(target))
        : {};
    const result = dispatch_interaction_validator(
      preset,
      validator_interaction,
      resolved_drag_committed_source,
      null,
      value_map,
    );
    if (!result.ok) {
      emit_rejection(
        step.step_name,
        interaction_index,
        target,
        "drag",
        preset,
        result.reason ?? "wrong_target",
      );
      return false;
    }
    handle_validated(step, target, "drag", preset);
    return true;
  }

  const handle: StepMachineHandle = {
    start,
    handle_click,
    handle_modal_close,
    handle_timer_elapsed,
    handle_type_commit,
    handle_adjust_commit,
    handle_drag_commit,
  };
  return handle;
}

//============================================
// Drag destination derivation
//============================================

// Derive the accepted drag destination from the interaction's authored response,
// using only EXISTING authored slots (no new YAML field). The destination is the
// `zone` of the first LayoutMove scene_operation: a drag moves its source object
// to that zone, so the LayoutMove already names where the source lands. Returns
// null when the response authors no LayoutMove, which the caller treats as an
// authoring gap and rejects loudly rather than accepting any drop.
//
// This is the single authored slot for the destination (the
// contract permits either a LayoutMove destination or a final_state_matches
// target/state; LayoutMove.zone is the cleaner, response-local choice). When a
// first drag content protocol lands, confirm the zone-name vs
// placement_name mapping resolves through the scene adapter; today no content
// protocol authors a drag, so this path is proven by the step-machine unit test.
function derive_drag_destination(ops: ReadonlyArray<SceneOperation>): string | null {
  for (const op of ops) {
    if (op.type === "LayoutMove") {
      return op.zone;
    }
  }
  return null;
}

//============================================
// Typed-value coercion for the `type` gesture
//============================================

// Build the value_map a target_with_value validator compares against, from the
// raw typed text. Each field the validator's `value` block declares is filled
// with the typed text coerced to that field's value kind (number vs string vs
// boolean), inferred from the expected value's JS type. A `type` interaction
// declares exactly one expected field in practice, but every declared field is
// filled identically so multi-field declarations stay well-defined.
function build_typed_value_map(
  expected: Record<string, unknown>,
  typed_text: string,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, expected_value] of Object.entries(expected)) {
    out[key] = coerce_typed_text(typed_text, expected_value);
  }
  return out;
}

// Coerce the typed string to the JS type of the expected value so a numeric
// field compares as a number. A non-numeric string against a numeric field
// yields NaN, which never strict-equals the expected number, so it correctly
// rejects. A boolean field compares the lowercased text against "true".
function coerce_typed_text(typed_text: string, expected_value: unknown): unknown {
  const trimmed = typed_text.trim();
  if (typeof expected_value === "number") {
    return Number(trimmed);
  }
  if (typeof expected_value === "boolean") {
    return trimmed.toLowerCase() === "true";
  }
  return trimmed;
}
