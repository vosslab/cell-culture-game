// src/shell/adapter/types.ts
//
// Typed seam between the protocol runtime (authoritative) and the
// Solid.js shell (observer). The runtime publishes ProtocolShellEvent
// values; the shell subscribes and derives ShellViewSnapshot for
// component rendering. The shell never mutates protocol state.
//
// Closed surface. Adding a variant requires a plan amendment.
//
// References:
// - docs/specs/PROTOCOL_VOCABULARY.md (gesture, validator presets,
//   scene operation primitives, step/interaction model)
// - docs/PRIMARY_SPEC.md (entry_step, outcome resolution, walker rule)
// - docs/archive/web_ui/runtime_seam_plan.md

//============================================
// Closed enums mirrored from PROTOCOL_VOCABULARY.md
//============================================

// Gesture set per PROTOCOL_VOCABULARY.md gesture vocabulary.
export type Gesture = "click" | "drag" | "adjust" | "select" | "type";

// Validator presets per PRIMARY_SPEC.md "Validators and outcome".
export type InteractionValidatorPreset = "correct_target" | "correct_choice" | "target_with_value";

export type StepValidatorPreset = "sequence_complete" | "final_state_matches";

export type ValidatorPreset = InteractionValidatorPreset | StepValidatorPreset;

// Outcome resolution per PRIMARY_SPEC.md "Validators and outcome".
export type StepOutcomeResolution = "complete" | "retry";

// Scene operation primitives per PROTOCOL_VOCABULARY.md
// "scene_operation primitives".
export type SceneOperationType =
  "ObjectStateChange" | "CursorAttach" | "SceneChange" | "LayoutMove" | "TimedWait";

//============================================
// Snapshot consumed by Solid shell signals
//============================================

// Modal / help / tray live states are derived from event history and
// surfaced to the shell as a readonly snapshot. The shell renders the
// snapshot; it never reaches back into the runtime to change it.

export type ModalKind = "interaction_choice" | "tool_picker" | "alert";

export interface ModalState {
  readonly is_open: boolean;
  readonly kind: ModalKind | null;
  readonly prompt: string | null;
  readonly choices: ReadonlyArray<ModalChoice>;
  readonly invoking_target: string | null;
}

export interface ModalChoice {
  readonly choice_id: string;
  readonly label: string;
}

export interface HelpState {
  readonly is_open: boolean;
  readonly topic: string | null;
}

export interface TrayItem {
  readonly tool_id: string;
  readonly label: string;
  readonly is_enabled: boolean;
}

export interface TrayState {
  readonly items: ReadonlyArray<TrayItem>;
  // The toolbar exposes independent tool availability. A selected-tool
  // state must be represented by a closed field when the shell needs one.
}

export interface ProgressTuple {
  readonly completed_step_count: number;
  readonly total_step_count: number;
}

export interface LastOutcome {
  readonly step_name: string;
  readonly resolution: StepOutcomeResolution;
  readonly retry_count: number;
}

// The latest rejected interaction is deliberately a closed projection of the
// runtime event. It gives the learner-facing shell enough information to
// explain a recovery without teaching the shell to inspect scene DOM or infer
// protocol state. A valid interaction or a new step clears it.
export interface LastRejection {
  readonly reason_code: InteractionRejectReason;
  readonly target_name: string;
  readonly gesture: Gesture;
  // Choice labels are projected only after a rejected select. They let the
  // shell teach the observed decision without revealing the answer beforehand.
  readonly selected_label: string | null;
  readonly expected_label: string | null;
}

// A short learner-facing acknowledgement tied to the most recent accepted or
// rejected interaction. The runtime projects only the already-ratified
// response.feedback fields; the shell never inspects response operations.
export interface LastInteractionFeedback {
  readonly kind: "correct" | "incorrect";
  readonly message: string;
}

// A TimedWait temporarily blocks further learner input. The runtime owns this
// fact and projects only the learner-facing display text and duration needed by
// the shell; the shell does not infer a wait by scraping scene DOM or running
// its own timer.
export interface PendingTimedWait {
  readonly target_name: string;
  readonly display: string | null;
  readonly duration_min: number;
}

// The single readonly object the shell components consume. Every Solid
// signal in the shell maps to a property here.
export interface ShellViewSnapshot {
  readonly protocol_name: string;
  readonly current_step_name: string | null;
  readonly current_prompt: string | null;
  // Professor-tip for the current step. Null when the step has no tip or no step is active.
  readonly current_tip: string | null;
  readonly current_interaction_index: number;
  // Total ordered interactions in the active pedagogical step. This lets the
  // learner-facing action rail distinguish action-level progress from the
  // guided-step completion count.
  readonly current_interaction_count: number;
  readonly progress: ProgressTuple;
  readonly last_outcome: LastOutcome | null;
  readonly last_rejection: LastRejection | null;
  readonly last_interaction_feedback: LastInteractionFeedback | null;
  readonly pending_validator_kind: ValidatorPreset | null;
  readonly modal: ModalState;
  readonly help: HelpState;
  readonly tray: TrayState;
  readonly active_scene_name: string | null;
  readonly is_complete: boolean;
  readonly active_interaction_target: string | null;
  readonly active_interaction_label: string | null;
  readonly active_interaction_gesture: Gesture | null;
  // The one authored target_with_value value for an active adjust gesture.
  // This is a learner-facing projection, never a validation backchannel:
  // click, drag, select, and type interactions always expose null.
  readonly active_interaction_value: string | number | boolean | null;
  readonly pending_timed_wait: PendingTimedWait | null;
}

//============================================
// Event variants emitted by the runtime
//============================================

// Lifecycle.

export interface ProtocolLoadedEvent {
  readonly kind: "protocol_loaded";
  readonly protocol_name: string;
  readonly entry_step_name: string;
  readonly total_step_count: number;
}

export interface ProtocolCompletedEvent {
  readonly kind: "protocol_completed";
  readonly protocol_name: string;
}

// Step machine.

export interface StepStartedEvent {
  readonly kind: "step_started";
  readonly step_name: string;
  readonly prompt: string;
  readonly interaction_count: number;
}

export interface StepCompletedEvent {
  readonly kind: "step_completed";
  readonly step_name: string;
  readonly resolution: StepOutcomeResolution;
}

// Per-interaction events.

export interface InteractionValidatedEvent {
  readonly kind: "interaction_validated";
  readonly step_name: string;
  readonly interaction_index: number;
  readonly target_name: string;
  readonly gesture: Gesture;
  readonly validator_preset: InteractionValidatorPreset;
  // Optional learner-facing acknowledgement from response.feedback.correct.
  readonly feedback?: string | null;
}

export interface InteractionRejectedEvent {
  readonly kind: "interaction_rejected";
  readonly step_name: string;
  readonly interaction_index: number;
  readonly target_name: string;
  readonly gesture: Gesture;
  readonly validator_preset: InteractionValidatorPreset;
  readonly reason_code: InteractionRejectReason;
  // Optional learner-facing recovery guidance from response.feedback.incorrect.
  readonly feedback?: string | null;
}

export type InteractionRejectReason =
  "wrong_target" | "wrong_value" | "out_of_order" | "no_active_step";

// Scene side-effects emitted after the runtime calls into the renderer.

export interface SceneChangedEvent {
  readonly kind: "scene_changed";
  readonly from_scene: string | null;
  readonly to_scene: string;
}

export interface SceneOperationAppliedEvent {
  readonly kind: "scene_operation_applied";
  readonly operation_type: SceneOperationType;
  readonly target_name: string | null;
}

export interface TimedWaitStartedEvent {
  readonly kind: "timed_wait_started";
  readonly target_name: string;
  readonly display: string | null;
  readonly duration_min: number;
}

export interface TimedWaitElapsedEvent {
  readonly kind: "timed_wait_elapsed";
  readonly target_name: string;
}

// Modal / help / tray surface events.

export interface ModalOpenedEvent {
  readonly kind: "modal_opened";
  readonly modal_kind: ModalKind;
  readonly prompt: string;
  readonly choices: ReadonlyArray<ModalChoice>;
  readonly invoking_target: string | null;
}

export interface ModalClosedEvent {
  readonly kind: "modal_closed";
  readonly committed: boolean;
  readonly chosen_choice_id: string | null;
}

export interface HelpOpenedEvent {
  readonly kind: "help_opened";
  readonly topic: string;
}

export interface HelpClosedEvent {
  readonly kind: "help_closed";
}

export interface TrayChangedEvent {
  readonly kind: "tray_changed";
  readonly items: ReadonlyArray<TrayItem>;
}

// Closed discriminated union. Add variants only via plan amendment.
export type ProtocolShellEvent =
  | ProtocolLoadedEvent
  | ProtocolCompletedEvent
  | StepStartedEvent
  | StepCompletedEvent
  | InteractionValidatedEvent
  | InteractionRejectedEvent
  | SceneChangedEvent
  | SceneOperationAppliedEvent
  | TimedWaitStartedEvent
  | TimedWaitElapsedEvent
  | ModalOpenedEvent
  | ModalClosedEvent
  | HelpOpenedEvent
  | HelpClosedEvent
  | TrayChangedEvent;

export type ProtocolShellEventKind = ProtocolShellEvent["kind"];

//============================================
// Emitter contract
//============================================

// The runtime exposes only subscribe + a current-snapshot read. No
// public emit, no public mutation. emit is package-private to the
// runtime module.

export type ProtocolShellEventListener = (event: ProtocolShellEvent) => void;

export interface ProtocolShellEmitter {
  subscribe(listener: ProtocolShellEventListener): UnsubscribeFn;
  get_snapshot(): ShellViewSnapshot;
}

export type UnsubscribeFn = () => void;

//============================================
// Protocol configuration types
//============================================

// Closed enum for protocol kinds per PRIMARY_SPEC.md and PROTOCOL_VOCABULARY.md
export type ProtocolKind = "mini_protocol" | "sequence_runner";

// Learning block for mini-protocols and sequence runners.
export interface LearningBlock {
  readonly objectives: string;
  readonly outcomes: string;
  readonly goals: string;
}

// Validator reference: a discriminated union keyed on `preset`, mirroring the
// SceneOperation union below. The `preset` literal selects which authored fields
// are legal; every illegal field is typed `never` so it cannot be authored on
// the wrong preset, while remaining a declared (optional) key so union-wide reads
// in the step machine and authored-value checker keep resolving without narrowing.
// Field legality per docs/PRIMARY_SPEC.md "Validators and outcome":
// - correct_target / correct_choice / sequence_complete: `preset` only.
// - target_with_value: carries a flat {field: value} `value` map.
// - final_state_matches: carries a single object `target` plus a flat {field:
//   value} `contains` map.
// Authored YAML uses `value`/`target`/`contains`; the legacy `params` alias was
// removed by the vocabulary-closure patch.
export interface CorrectTargetValidator {
  readonly preset: "correct_target";
  readonly value?: never;
  readonly target?: never;
  readonly contains?: never;
}

export interface CorrectChoiceValidator {
  readonly preset: "correct_choice";
  readonly value?: never;
  readonly target?: never;
  readonly contains?: never;
}

export interface TargetWithValueValidator {
  readonly preset: "target_with_value";
  readonly value?: Readonly<Record<string, string | number | boolean>>;
  readonly target?: never;
  readonly contains?: never;
}

export interface SequenceCompleteValidator {
  readonly preset: "sequence_complete";
  readonly value?: never;
  readonly target?: never;
  readonly contains?: never;
}

export interface FinalStateMatchesValidator {
  readonly preset: "final_state_matches";
  readonly target?: string;
  readonly contains?: Readonly<Record<string, string | number | boolean>>;
  readonly value?: never;
}

// Discriminated union of validator references (interaction + step presets).
export type ValidatorReference =
  | CorrectTargetValidator
  | CorrectChoiceValidator
  | TargetWithValueValidator
  | SequenceCompleteValidator
  | FinalStateMatchesValidator;

// Five scene operation primitives per PRIMARY_SPEC.md.
export interface ObjectStateChangeOp {
  readonly type: "ObjectStateChange";
  readonly target: string;
  readonly state: Readonly<Record<string, string | number | boolean>>;
  readonly transition?: string;
}

export interface CursorAttachOp {
  readonly type: "CursorAttach";
  readonly target: string;
  readonly operation: "attach" | "detach";
}

export interface SceneChangeOp {
  readonly type: "SceneChange";
  readonly to_scene: string;
}

export interface LayoutMoveOp {
  readonly type: "LayoutMove";
  readonly target: string;
  readonly zone: string;
}

export interface TimedWaitOp {
  readonly type: "TimedWait";
  readonly target: string;
  readonly duration_min: number;
  readonly display?: string;
}

// Discriminated union of scene operation primitives.
export type SceneOperation =
  ObjectStateChangeOp | CursorAttachOp | SceneChangeOp | LayoutMoveOp | TimedWaitOp;

// Interaction feedback (optional).
export interface InteractionFeedback {
  readonly correct?: string;
  readonly incorrect?: string;
}

// Response to a validated interaction.
export interface InteractionResponse {
  readonly scene_operations: ReadonlyArray<SceneOperation>;
  readonly feedback?: InteractionFeedback;
}

// Single interaction in a step's sequence.
export interface Interaction {
  readonly target: string;
  readonly gesture: Gesture;
  readonly validator: ValidatorReference;
  readonly response: InteractionResponse;
}

// Step outcome resolution mapping per PRIMARY_SPEC.md.
export interface StepOutcome {
  readonly on_success: "complete";
  readonly on_failure: "retry";
}

// Single protocol step.
export interface ProtocolStep {
  readonly step_name: string;
  readonly prompt: string;
  // Optional per-step scene declaration. When present, the runtime uses this
  // as the authoritative initial/transition scene for this step (precedence 1
  // in resolve_entry_scene_name). See docs/specs/PROTOCOL_YAML_FORMAT.md.
  readonly scene?: string;
  // Optional professor-tip string for the tip bubble. Null/absent when not authored.
  // See docs/specs/PROTOCOL_YAML_FORMAT.md optional step-fields table.
  readonly tip?: string;
  readonly sequence: ReadonlyArray<Interaction>;
  readonly step_validator: ValidatorReference;
  readonly outcome: StepOutcome;
  readonly next_step: string | null;
}

// Declared state established when a protocol session starts. The target may
// name an object, one declared subpart, or one declared subpart group; the
// runtime expands groups before validating and applying the flat state map.
// This is deliberately the same primitive value domain as ObjectStateChange:
// state schema validation, material-registry checks, ranges, and enum closure
// remain runtime responsibilities rather than becoming an authoring escape
// hatch here.
export interface InitialStateEntry {
  readonly target: string;
  readonly state: Readonly<Record<string, string | number | boolean>>;
}

// Protocol configuration (mini_protocol or sequence_runner).
export interface ProtocolConfig {
  readonly protocol_name: string;
  readonly protocol_type: ProtocolKind;
  readonly entry_step: string;
  readonly learning?: LearningBlock;
  readonly steps?: ReadonlyArray<ProtocolStep>;
  readonly mini_protocols?: ReadonlyArray<string>;
  readonly initial_state?: ReadonlyArray<InitialStateEntry>;
}

// Index entry for student-visible protocols.
export interface ProtocolIndexEntry {
  readonly protocol_name: string;
  readonly cluster: string;
  readonly protocol_type: ProtocolKind;
  readonly learning_hook: string | null;
}

// Slim launcher metadata. Subset of ProtocolIndexEntry plus a derived
// display_title (Title Case, underscores -> spaces, with hard-coded
// acronyms preserved) and a renamed learning_goal_hook so the launcher
// bundle never has to import the full ProtocolConfig surface. Emitted
// by pipeline/gen_protocols.py to generated/protocols_index_slim.ts.
export interface ProtocolIndexSlimEntry {
  readonly protocol_name: string;
  readonly cluster: string;
  readonly display_title: string;
  readonly learning_goal_hook: string | null;
  readonly protocol_type: ProtocolKind;
  readonly step_count: number;
  // Stub for future walker-populated estimate. Today no emitter populates
  // this; the launcher renders "~Ns" only if present.
  readonly estimated_seconds?: number;
}
