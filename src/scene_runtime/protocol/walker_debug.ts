// src/scene_runtime/protocol/walker_debug.ts
//
// Read-only walker/debug surface. Restores window.PROTOCOL_STEPS and
// window.gameState that the Solid HUD migration dropped, so the canonical
// walker (tests/playwright/e2e/protocol_walkthrough_yaml.mjs) and ad-hoc
// debugging can read protocol progress. These are FROZEN contract surfaces per
// docs/specs/WALKTHROUGH_GUIDE.md and the migration plan's
// "Browser runtime constraints":
//
//   - They are READ-ONLY signals. Tests may read them; nothing here mutates
//     game state, and the runtime never advances by writing them. They are a
//     projection of the step machine's emitter snapshot + the scene_store.
//   - No new window globals beyond the two documented surfaces are added.
//
// gameState surfaces the walker progress-predicate signals the helper
// clickItemAndWaitProgress() reads (walker_helpers.mjs):
//   activeStepId, interactionIndex, activeScene, completedSteps (count + ids),
//   selectedTool + heldLiquid (cursor/held state), plus wrongOrderClicks /
//   stepsOutOfOrder counters the walker's end-state assertions read. It also
//   surfaces activeTarget / activeGesture (the current interaction's target and
//   gesture, projected read-only from the snapshot) so the schema-driven walker
//   knows which visible [data-item-id] element to click next without any
//   per-protocol branch or internal-API call. These mirror the exact fields the
//   runtime itself uses to resolve a click's gesture (protocol_host.tsx).
//
// The signals are sourced from:
//   - the emitter snapshot (current_step_name, current_interaction_index,
//     active_scene_name, progress.completed_step_count, is_complete);
//   - step_completed / interaction_rejected events (completed-step ids,
//     wrong-order counters);
//   - the scene_store (cursor-attached tool + held material).
//
// References:
//   - docs/specs/WALKTHROUGH_GUIDE.md (window surfaces; progress predicate)
//   - tests/playwright/e2e/walker_helpers.mjs (fields the walker reads)
//   - src/scene_runtime/protocol/emitter.ts (snapshot + event stream)
//   - src/scene_runtime/state/scene_store.ts (cursor/held state)

import type {
  ProtocolConfig,
  ProtocolShellEvent,
  ProtocolStep,
} from "../../shell/adapter/types.js";
import type { RuntimeEmitterHandle } from "./emitter.js";
import type { SceneStore, StatePartial } from "../state/scene_store.js";
import { OBJECT_LIBRARY } from "../../../generated/object_library.js";
import { expand_subpart_group_target } from "../state/subpart_group_expand.js";
import { find_material_tint_subpart_field } from "../renderer/subpart_dispatch.js";

//============================================
// Public surface types (frozen walker contract)
//============================================

// One step in the read-only PROTOCOL_STEPS list. The walker iterates this list
// and reads id / next_step for flow assertions. Shape mirrors the new protocol
// vocabulary (step_name -> id, next_step -> nextId), not the legacy game.
export interface WalkerStep {
  id: string;
  label: string;
  scene: string | null;
  nextId: string | null;
}

// Held-material projection. tool is the cursor-attached object_name; liquid is
// the held material name. Both null when nothing is held.
export interface HeldLiquid {
  tool: string | null;
  liquid: string | null;
}

// Read-only projection of the active interaction's expected structured-object
// material write. Present only when the active interaction's response writes the
// declared material-tint SUBPART field of a structured object (a plate, rack, or
// gel). The walker reads this to run the material-area verification: after the
// interaction it asserts every expected member subpart carries material_value and
// its fill changed, and every OTHER rendered subpart kept its prior material/fill
// ("and nothing else", MATERIAL_DESIGN.md spatial correspondence). It is a pure
// projection of authored protocol config + generated object schema (the same
// fan-out the runtime's ObjectStateChange uses via expand_subpart_group_target),
// never a state write. Null when the active interaction writes no structured
// material area.
export interface MaterialAreaEffect {
  // The structured object whose subpart overlay changes (e.g. "well_plate_96").
  object_name: string;
  // The declared material-tint subpart field written (read from the object's
  // visual_states contract, never hardcoded; typically "material_name").
  material_field: string;
  // The authored material value written to every expected member, as a string.
  material_value: string;
  // The concrete member subpart names the write reaches (a single subpart, a
  // column/row/region group's members, or a bulk all-cells group's members),
  // expanded via the same fan-out the runtime applies.
  expected_subparts: string[];
}

// Read-only declared-state projection for exactly the currently mounted scene.
// The durable protocol archive is deliberately excluded: it may contain a tube
// or well that is not visible and therefore cannot be verified in this scene.
export type ActiveDeclaredState = Readonly<Record<string, StatePartial>>;

// One concrete ObjectStateChange write the active interaction will apply.
// `target` is after data-driven subpart-group expansion, and ordering matches
// the runtime dispatcher: authored operation order, then group member order.
export interface ActiveStateWrite {
  readonly target: string;
  readonly state: StatePartial;
}

// Read-only game-state projection consumed by the walker progress predicate.
export interface WalkerGameState {
  activeStepId: string | null;
  interactionIndex: number;
  activeScene: string | null;
  completedSteps: string[];
  selectedTool: string | null;
  heldLiquid: HeldLiquid;
  wrongOrderClicks: number;
  stepsOutOfOrder: number;
  isComplete: boolean;
  // Monotonic declared-state/reconciliation revision from the session store.
  // It gives diagnostics a stable proof that a visible state mutation was
  // actually applied without exposing a writable state surface.
  stateRevision: number;
  // Most recent concrete declared-state mutation. Group writes report their
  // resolved member target, never the authored pseudo-group name.
  lastStateDelta: {
    target: string;
    before: Readonly<Record<string, string | number | boolean>>;
    after: Readonly<Record<string, string | number | boolean>>;
  } | null;
  // Full ordered history of concrete declared writes in this session. Group
  // writes appear as their expanded members in exact runtime order.
  stateDeltaLog: ReadonlyArray<{
    target: string;
    before: Readonly<Record<string, string | number | boolean>>;
    after: Readonly<Record<string, string | number | boolean>>;
  }>;
  // Current declared state for targets mounted in activeScene only. Runtime
  // flags and durable-but-absent session targets are intentionally omitted.
  declaredState: ActiveDeclaredState;
  // Concrete declared-state writes expected if the active interaction succeeds.
  // A group fan-out appears as one entry per member in deterministic runtime
  // order; repeated writes are retained rather than collapsed, because the
  // runtime applies them sequentially and collapsing would hide a conflict.
  activeStateWrites: ReadonlyArray<ActiveStateWrite>;
  // The current interaction's target and gesture, projected read-only from the
  // step machine's emitter snapshot (active_interaction_target /
  // active_interaction_gesture). These are the SAME fields the runtime itself
  // uses to resolve which gesture a click on a target counts as
  // (see protocol_host.tsx attach_click_resolver). The schema-driven walker
  // reads them to know which VISIBLE [data-item-id] element to click next, so
  // it can drive the protocol with no per-protocol branch and no internal-API
  // call. Both null when no interaction is active (between steps / complete).
  activeTarget: string | null;
  activeGesture: string | null;
  // For a `drag` interaction only: the accepted destination the student should
  // drop the source object onto, as a placement identity string. Derived
  // read-only from the active interaction's authored response (the `zone` of its
  // first LayoutMove scene_operation) -- the same authored slot the runtime's
  // handle_drag_commit derives the destination from. The walker reads this to
  // know which destination scene object to drag onto. Null when the active
  // interaction is not a `drag` gesture or authors no LayoutMove destination.
  activeDragDestination: string | null;
  // Every structured material-tint write the active response will apply, in
  // authored operation order. Distinct effects may target the same rack or gel
  // with different materials, so this remains a list rather than one lossy
  // representative effect.
  activeMaterialEffects: ReadonlyArray<MaterialAreaEffect>;
}

declare global {
  interface Window {
    // Frozen read-only walker/debug surfaces.
    PROTOCOL_STEPS?: ReadonlyArray<WalkerStep>;
    gameState?: WalkerGameState;
  }
}

//============================================
// PROTOCOL_STEPS derivation
//============================================

// Resolve the scene a step takes place in, when statically knowable: an
// explicit step.scene wins, else the first SceneChange.to_scene in the step's
// sequence, else null (the step inherits the active scene at runtime).
function resolve_step_scene(step: ProtocolStep): string | null {
  if (typeof step.scene === "string" && step.scene !== "") {
    return step.scene;
  }
  for (const interaction of step.sequence) {
    for (const op of interaction.response.scene_operations) {
      if (op.type === "SceneChange") {
        return op.to_scene;
      }
    }
  }
  return null;
}

// Build the read-only PROTOCOL_STEPS list from a protocol config. Empty for a
// sequence_runner (no authored steps list); the walker reads PROTOCOL_STEPS
// only for mini_protocol flows.
export function build_protocol_steps(config: ProtocolConfig): WalkerStep[] {
  const steps = config.steps ?? [];
  const out: WalkerStep[] = [];
  for (const step of steps) {
    out.push({
      id: step.step_name,
      label: step.prompt,
      scene: resolve_step_scene(step),
      nextId: step.next_step,
    });
  }
  return out;
}

//============================================
// Active set-point / destination derivation (read-only)
//============================================

// Look up the active interaction for a step + index, or null when out of range.
function active_interaction_at(
  config: ProtocolConfig,
  step_name: string | null,
  index: number,
): ProtocolStep["sequence"][number] | null {
  if (step_name === null) {
    return null;
  }
  const steps = config.steps ?? [];
  const step = steps.find((s) => s.step_name === step_name);
  if (!step) {
    return null;
  }
  if (index < 0 || index >= step.sequence.length) {
    return null;
  }
  return step.sequence[index] ?? null;
}

// Resolve the accepted drop destination for a `drag` interaction, as a string.
// The destination is the `zone` of the first LayoutMove scene_operation in the
// interaction's authored response -- the same authored slot the runtime's
// handle_drag_commit derives the destination from. Returns null when the active
// interaction is not a `drag` gesture or authors no LayoutMove destination.
function resolve_active_drag_destination(
  config: ProtocolConfig,
  step_name: string | null,
  index: number,
): string | null {
  const interaction = active_interaction_at(config, step_name, index);
  if (!interaction || interaction.gesture !== "drag") {
    return null;
  }
  for (const op of interaction.response.scene_operations) {
    if (op.type === "LayoutMove") {
      return op.zone;
    }
  }
  return null;
}

// Strip the subpart suffix from a fanned-out "<object>.<member>" write target.
// Returns "" for a bare object target (no "."), which the caller filters out.
function subpart_suffix(target: string): string {
  const dot = target.indexOf(".");
  return dot < 0 ? "" : target.slice(dot + 1);
}

// Resolve the active interaction's expected structured material-area effect, or
// null when it writes no structured subpart material. Scans the interaction's
// ObjectStateChange ops; for each, looks up the target object in the generated
// object library and asks the SAME predicate the renderer uses
// (find_material_tint_subpart_field) whether that object declares a per-subpart
// material-tint contract. When the op writes that declared field, the write is a
// structured material-area write: its concrete member subparts are expanded with
// the SAME fan-out the runtime applies (expand_subpart_group_target), then kept
// to real declared subparts so a bare-object write resolves to no members and is
// skipped. Pure read of authored config + generated schema; no object or field
// name is special-cased.
function resolve_active_material_effects(
  config: ProtocolConfig,
  step_name: string | null,
  index: number,
): MaterialAreaEffect[] {
  const interaction = active_interaction_at(config, step_name, index);
  if (!interaction) {
    return [];
  }
  const effects: MaterialAreaEffect[] = [];
  for (const op of interaction.response.scene_operations) {
    if (op.type !== "ObjectStateChange") {
      continue;
    }
    // The object segment before the first "." owns the subpart namespace.
    const dot = op.target.indexOf(".");
    const object_name = dot < 0 ? op.target : op.target.slice(0, dot);
    const def = OBJECT_LIBRARY[object_name];
    if (def === undefined) {
      continue;
    }
    // Ask the renderer's own dispatch predicate whether this object declares the
    // per-subpart material-tint contract, and which field drives it.
    const contract = find_material_tint_subpart_field(def);
    if (contract === null) {
      continue;
    }
    const field = contract.field_name;
    const written = op.state[field];
    if (written === undefined) {
      continue;
    }
    // Expand to concrete member subparts using the runtime's fan-out, then keep
    // only real declared subparts (a bare-object write yields none -> skip).
    const declared = new Set(def.subparts ?? []);
    const members: string[] = [];
    for (const write_target of expand_subpart_group_target(op.target)) {
      const member = subpart_suffix(write_target);
      if (member !== "" && declared.has(member)) {
        members.push(member);
      }
    }
    if (members.length === 0) {
      continue;
    }
    effects.push({
      object_name,
      material_field: field,
      material_value: String(written),
      expected_subparts: members,
    });
  }
  return effects;
}

// Expand every ObjectStateChange in the active response into the exact concrete
// write sequence that build_store_scene_op_deps applies. No names or groups are
// special-cased: the shared group resolver owns expansion, and its declared
// member order is preserved. Do not merge repeated targets/fields; sequential
// write order is observable runtime behavior and is the unambiguous proof the
// walker needs to compare after an interaction.
export function resolve_active_state_writes(
  config: ProtocolConfig,
  step_name: string | null,
  index: number,
): ActiveStateWrite[] {
  const interaction = active_interaction_at(config, step_name, index);
  if (interaction === null) {
    return [];
  }
  const writes: ActiveStateWrite[] = [];
  for (const op of interaction.response.scene_operations) {
    if (op.type !== "ObjectStateChange") {
      continue;
    }
    const state: Record<string, string | number | boolean> = {};
    for (const key of Object.keys(op.state).sort()) {
      const value = op.state[key];
      if (value !== undefined) {
        state[key] = value;
      }
    }
    for (const target of expand_subpart_group_target(op.target)) {
      writes.push({ target, state: { ...state } });
    }
  }
  return writes;
}

// Snapshot only the current reactive scene projection, sorting target names for
// a stable read-only diagnostic representation. The store archive is excluded
// by construction; callers can never use this walker surface to inspect or
// alter absent-scene scientific state.
export function snapshot_active_declared_state(store: SceneStore): ActiveDeclaredState {
  const snapshot: Record<string, StatePartial> = {};
  for (const target of Object.keys(store.state).sort()) {
    const entry = store.state[target];
    if (entry !== undefined) {
      snapshot[target] = { ...entry.state };
    }
  }
  return snapshot;
}

//============================================
// gameState projection
//============================================

// Read the cursor-attached tool + held material from the store. The first
// cursor-attached target is treated as the selected tool; its held material is
// the held liquid. Returns nulls when nothing is held.
function read_held(store: SceneStore): { tool: string | null; liquid: string | null } {
  for (const target of Object.keys(store.state)) {
    const entry = store.state[target];
    if (entry === undefined) {
      continue;
    }
    if (entry.flags.cursor_attached) {
      return { tool: target, liquid: entry.flags.held_material_name };
    }
  }
  return { tool: null, liquid: null };
}

// Install the read-only walker/debug surfaces on window. Subscribes to the
// emitter and rebuilds window.gameState after every event from the snapshot +
// store. Returns an unsubscribe function for host teardown.
//
// The returned object also records completed-step ids and wrong-order counters,
// which are not carried in the snapshot (the snapshot tracks a completed COUNT,
// not the id list the walker's completedSteps.includes(id) predicate needs).
export function install_walker_debug_surface(
  config: ProtocolConfig,
  emitter: RuntimeEmitterHandle,
  store: SceneStore,
): () => void {
  // Build the static step list once.
  window.PROTOCOL_STEPS = build_protocol_steps(config);

  // Mutable counters not carried by the snapshot.
  const completed_steps: string[] = [];
  let wrong_order_clicks = 0;
  let steps_out_of_order = 0;

  function rebuild_game_state(): void {
    const snapshot = emitter.get_snapshot();
    const held = read_held(store);
    const game_state: WalkerGameState = {
      activeStepId: snapshot.current_step_name,
      interactionIndex: snapshot.current_interaction_index,
      activeScene: snapshot.active_scene_name,
      // Fresh array each rebuild so a reader cannot mutate the internal list.
      completedSteps: completed_steps.slice(),
      selectedTool: held.tool,
      heldLiquid: { tool: held.tool, liquid: held.liquid },
      wrongOrderClicks: wrong_order_clicks,
      stepsOutOfOrder: steps_out_of_order,
      isComplete: snapshot.is_complete,
      stateRevision: store.state_revision,
      lastStateDelta: store.last_state_delta,
      stateDeltaLog: store.state_delta_log,
      declaredState: snapshot_active_declared_state(store),
      activeStateWrites: resolve_active_state_writes(
        config,
        snapshot.current_step_name,
        snapshot.current_interaction_index,
      ),
      // Read-only projection of the snapshot's active-interaction fields. The
      // walker mirrors the runtime's own click resolution by clicking the
      // visible element whose data-item-id equals activeTarget. active_interaction_target
      // now carries the adapter-resolved placement_name (M8 target identity): the
      // reducer normalizes the authored target to the unique DOM placement_name
      // before it enters the snapshot, so activeTarget and data-item-id agree
      // (both the placement_name) and the walker's [data-item-id="<activeTarget>"]
      // selector matches with zero walker-logic change, even when a scene renames
      // a placement (placement_name hood_flask for object_name t75_flask).
      activeTarget: snapshot.active_interaction_target,
      activeGesture: snapshot.active_interaction_gesture,
      activeDragDestination: resolve_active_drag_destination(
        config,
        snapshot.current_step_name,
        snapshot.current_interaction_index,
      ),
      activeMaterialEffects: resolve_active_material_effects(
        config,
        snapshot.current_step_name,
        snapshot.current_interaction_index,
      ),
    };
    window.gameState = game_state;
  }

  function on_event(event: ProtocolShellEvent): void {
    // Record completed step ids (resolution "complete" only; "retry" restarts
    // the step and must not count as completed).
    if (event.kind === "step_completed" && event.resolution === "complete") {
      if (!completed_steps.includes(event.step_name)) {
        completed_steps.push(event.step_name);
      }
    }
    // Wrong-order signal: an interaction rejected for a wrong target/order is
    // the runtime declining to advance on a non-required click.
    if (event.kind === "interaction_rejected") {
      if (event.reason_code === "wrong_target" || event.reason_code === "out_of_order") {
        wrong_order_clicks += 1;
        steps_out_of_order += 1;
      }
    }
    rebuild_game_state();
  }

  const unsubscribe = emitter.subscribe(on_event);
  // Seed the surface immediately so a reader before the first event sees a
  // well-formed gameState (activeStepId null until start() fires step_started).
  rebuild_game_state();

  return () => {
    unsubscribe();
    delete window.PROTOCOL_STEPS;
    delete window.gameState;
  };
}
