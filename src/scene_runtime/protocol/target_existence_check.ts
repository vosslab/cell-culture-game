// src/scene_runtime/protocol/target_existence_check.ts
//
// Load-time target-existence invariant (M16-D).
//
// This pass runs once at protocol load, inside create_step_machine, BESIDE
// validate_protocol_presets, validate_authored_validator_values, and
// validate_gesture_affordances, BEFORE any handler closure is built. It walks
// the reachable step graph (entry_step -> next_step, same reachability walk
// as count_reachable_steps in step_machine.ts) while tracking the CURRENT
// scene exactly as the runtime does (enter_step's step.scene transition, then
// apply_response_scene_ops's SceneChange updates as each interaction
// validates). At each interaction and each final_state_matches step_validator,
// it resolves a scene-scoped TargetAdapter for the scene active at that point
// and rejects any authored `target` whose prefix resolves to no known
// placement_name or object_name in THAT scene.
//
// Per-scene resolution matters: a protocol legitimately visits several scenes
// via SceneChange, and a target valid in scene B is not necessarily placed in
// the ENTRY scene A. Checking every target against only the entry scene's
// adapter would both miss real misses (a target that belongs to no scene the
// protocol ever reaches) and, worse, falsely reject targets that are placed
// correctly in a later scene. Simulating the same scene-tracking the runtime
// performs is what keeps this check sound.
//
// A target that names nothing the scene it is used in provides can never be
// clicked, so the protocol fails loud at load rather than trapping a student
// mid-walk when the click reaches an unresolvable step (the "target_missing"
// symptom from the walker sweep, e.g. passage_hood_detachment naming
// hood_surface).
//
// Cursor-attached (held/tool) targets are exempt. A target that is ever the
// `target` of a CursorAttach "attach" scene_operation anywhere in the
// protocol (a pipette, a conical tube, a label pen -- picked up and carried)
// is rendered through the tray/cursor-overlay affordance, not through a
// static scene placement, so it legitimately has no entry in a scene's
// `placements:` list. Checking it against the placement-only TargetAdapter
// would be a false miss, not a real one. This exemption trades checking the
// tool's very first pickup placement (out of scope here) for soundness: a
// held target is never flagged as missing once it has been cursor-attached
// anywhere in the flow.
//
// The pass owns ALL error behavior for the target-existence check. It never
// falls back, never returns a silent false, and never wraps work in a broad
// try/catch.
//
// References:
//   - docs/PRIMARY_SPEC.md (targets and the scene boundary)
//   - docs/active_plans/decisions/target_identity.md (M7/M8 placement_name /
//     object_name split this check reads through)
//   - src/scene_runtime/protocol/target_adapter.ts (TargetAdapter.has_target)
//   - src/scene_runtime/protocol/step_machine.ts (enter_step /
//     apply_response_scene_ops: the runtime scene-tracking this pass mirrors)
//   - src/scene_runtime/protocol/gesture_affordance_check.ts (the load-time
//     pass pattern this file mirrors: named error, location suffix, pass
//     entry point)

import { OBJECT_LIBRARY } from "../../../generated/object_library.js";
import type { ProtocolConfig, ProtocolStep } from "../../shell/adapter/types";
import type { TargetAdapter } from "./target_adapter";

// Resolves a scene name to its TargetAdapter, or undefined when the scene is
// not known to the resolver (a genuinely unresolvable scene name is a
// separate failure class -- scene existence, not target existence -- already
// caught elsewhere; this pass simply skips validation for that scene rather
// than duplicating that guard).
export type SceneTargetAdapterResolver = (scene_name: string) => TargetAdapter | undefined;

//============================================
// Named author-facing error
//============================================

// Locating fields the error carries so the offending YAML reference can be
// found without guessing. slot names which authored field carried the
// unresolvable target: an interaction's `target`, or a final_state_matches
// step_validator's `target`.
interface TargetExistenceLocation {
  readonly protocol_name: string;
  readonly step_name: string;
  readonly scene_name: string;
  readonly slot: "interaction.target" | "step_validator.target";
  readonly interaction_index: number | null;
  readonly target: string;
}

// Build the shared "in protocol ... step ... scene ... slot ... target ..."
// suffix used by the error message.
function location_suffix(location: TargetExistenceLocation): string {
  let suffix = ` in protocol "${location.protocol_name}",`;
  suffix += ` step "${location.step_name}",`;
  suffix += ` scene "${location.scene_name}",`;
  suffix += ` slot "${location.slot}"`;
  if (location.interaction_index !== null) {
    suffix += ` at interaction index ${location.interaction_index}`;
  }
  suffix += `,`;
  suffix += ` target "${location.target}".`;
  return suffix;
}

// An authored `target` names no placement or object the scene active at that
// point in the protocol flow provides. The scene, the YAML target, or the
// protocol's flow is incomplete; the fix is never a per-protocol runtime
// branch.
export class UnknownAuthoredTargetError extends Error {
  constructor(location: TargetExistenceLocation) {
    let message = `Authored target does not resolve to any known scene placement`;
    message += location_suffix(location);
    message += ` No placement_name or object_name in that scene matches it.`;
    super(message);
    this.name = "UnknownAuthoredTargetError";
  }
}

// An authored interaction `target` names an object placed MORE THAN ONCE in the
// scene active at that point, so it cannot resolve to a single DOM element.
// resolve_to_placement throws AmbiguousTargetError for the same condition, but
// only when the interaction is reached mid-walk; this invariant promotes it to
// a named load-time error carrying the competing placement_names. The fix is to
// name one specific placement_name in the YAML, never a per-protocol runtime
// branch.
export class AmbiguousAuthoredTargetError extends Error {
  constructor(location: TargetExistenceLocation, competing_placements: readonly string[]) {
    let message = `Authored target names an object placed more than once`;
    message += location_suffix(location);
    message += ` It resolves to ${competing_placements.length} placements`;
    message += ` (${competing_placements.join(", ")}).`;
    message += ` Name one placement_name to disambiguate.`;
    super(message);
    this.name = "AmbiguousAuthoredTargetError";
  }
}

// Scene-operation primitives that write to the scene store and therefore need
// a target seeded in the active scene. CursorAttach is included because its
// non-held targets update cursor/store state; TimedWait sets render flags
// before the host schedules the elapsed event.
type SeededSceneOperationType = "ObjectStateChange" | "CursorAttach" | "TimedWait";

// Locating fields the seeded-scene-operation error carries. operation_type
// names which primitive referenced the unseeded target.
interface SeededSceneOperationTargetLocation {
  readonly protocol_name: string;
  readonly step_name: string;
  readonly scene_name: string;
  readonly operation_type: SeededSceneOperationType;
  readonly interaction_index: number;
  readonly target: string;
}

// A scene operation that writes to the scene store names a `target` that is
// not seeded in the scene active at the point the operation executes. The
// runtime would otherwise throw `scene_store: ... not seeded` mid-walk. This
// invariant promotes that to a named load-time error. The fix is to seed the
// object in that scene (scene layer) or correct the authored flow; never a
// per-protocol runtime branch.
export class UnseededSceneOperationTargetError extends Error {
  constructor(location: SeededSceneOperationTargetLocation) {
    let message = `Scene operation target is not seeded in the active scene`;
    message += ` in protocol "${location.protocol_name}",`;
    message += ` step "${location.step_name}",`;
    message += ` scene "${location.scene_name}",`;
    message += ` scene_operation "${location.operation_type}"`;
    message += ` at interaction index ${location.interaction_index},`;
    message += ` target "${location.target}".`;
    message += ` No placement_name or object_name in that scene matches it.`;
    super(message);
    this.name = "UnseededSceneOperationTargetError";
  }
}

// Locating fields the subpart-suffix error carries. slot names which authored
// field carried the bad "<object>.<suffix>" reference.
interface SubpartSuffixLocation {
  readonly protocol_name: string;
  readonly step_name: string;
  readonly scene_name: string;
  readonly slot: "interaction.target" | "step_validator.target" | "scene_operation.target";
  readonly interaction_index: number | null;
  readonly object_name: string;
  readonly suffix: string;
  readonly target: string;
}

// An authored target names an "<object>.<suffix>" whose suffix is neither a
// declared subpart instance nor a declared subpart_group of that object. The
// object prefix resolves (validate_target_existence already guaranteed that),
// but the suffix addresses nothing the object declares, so a write to it would
// land on a non-rendered pseudo-node (no visible change) or fail to fan out.
// The fix is to name a declared subpart or subpart_group in the YAML, or to add
// the subpart/group to the object's structure block; never a per-protocol
// runtime branch.
export class UnknownAuthoredSubpartTargetError extends Error {
  constructor(location: SubpartSuffixLocation, declared_subparts: number, declared_groups: number) {
    let message = `Authored target names an undeclared subpart or subpart_group`;
    message += ` in protocol "${location.protocol_name}",`;
    message += ` step "${location.step_name}",`;
    message += ` scene "${location.scene_name}",`;
    message += ` slot "${location.slot}"`;
    if (location.interaction_index !== null) {
      message += ` at interaction index ${location.interaction_index}`;
    }
    message += `,`;
    message += ` target "${location.target}".`;
    message += ` Object "${location.object_name}" declares ${declared_subparts} subparts`;
    message += ` and ${declared_groups} subpart_groups,`;
    message += ` none named "${location.suffix}".`;
    super(message);
    this.name = "UnknownAuthoredSubpartTargetError";
  }
}

//============================================
// Step-graph scene-tracking walk
//============================================

// One point in the flow graph where a target is authored, tagged with the
// scene that is CURRENT at that exact point (mirroring step_machine's
// runtime scene tracker). slot/interaction_index locate the authored field.
interface TargetReference {
  readonly step_name: string;
  readonly scene_name: string;
  readonly slot: "interaction.target" | "step_validator.target";
  readonly interaction_index: number | null;
  readonly target: string;
}

// One point in the flow graph where a store-writing scene operation names a
// target, tagged with the scene CURRENT when that operation executes. A
// response's scene_operations run in the scene active at the START of their
// interaction (any SceneChange in the same response only takes effect for the
// NEXT interaction), so a scene-operation reference shares its interaction
// target's scene.
interface SeededSceneOperationReference {
  readonly step_name: string;
  readonly scene_name: string;
  readonly operation_type: SeededSceneOperationType;
  readonly interaction_index: number;
  readonly target: string;
}

// Both reference streams produced by the single reachable-graph traversal.
interface ProtocolReferences {
  readonly targets: TargetReference[];
  readonly seeded_scene_operations: SeededSceneOperationReference[];
}

// Walk the reachable step graph (entry_step -> next_step, cycle-safe via a
// visited set, identical reachability rule to count_reachable_steps) and
// collect one TargetReference per authored target plus one
// SeededSceneOperationReference per store-writing scene operation, each tagged
// with the scene active at that point. This is the single traversal
// collect_reachable_scene_names, validate_target_existence, and
// validate_seeded_scene_operation_targets build on, so they never drift out of
// sync on how scene transitions are tracked.
//
// Scene tracking mirrors the runtime exactly:
//   - enter_step: if the step declares a non-empty `scene` different from the
//     current scene, that scene becomes current BEFORE the step's first
//     interaction is checked.
//   - apply_response_scene_ops: a validated interaction's SceneChange updates
//     the current scene BEFORE the next interaction (or the step_validator)
//     is checked. ObjectStateChange / CursorAttach ops in the same response
//     execute BEFORE that SceneChange, so they are recorded at the pre-change
//     scene.
function walk_protocol_references(
  config: ProtocolConfig,
  initial_scene: string | null,
): ProtocolReferences {
  const targets: TargetReference[] = [];
  const seeded_scene_operations: SeededSceneOperationReference[] = [];
  const steps = config.steps ?? [];
  if (steps.length === 0) {
    return { targets, seeded_scene_operations };
  }
  const by_name: Map<string, ProtocolStep> = new Map();
  for (const step of steps) {
    by_name.set(step.step_name, step);
  }

  let current_scene = initial_scene;
  const visited: Set<string> = new Set();
  let cursor: string | null = config.entry_step;

  while (cursor !== null && !visited.has(cursor)) {
    visited.add(cursor);
    const step = by_name.get(cursor);
    if (!step) {
      break;
    }

    // Step-entry scene transition, mirroring enter_step.
    if (typeof step.scene === "string" && step.scene !== "" && step.scene !== current_scene) {
      current_scene = step.scene;
    }

    step.sequence.forEach((interaction, interaction_index) => {
      const scene_name = current_scene ?? "";
      targets.push({
        step_name: step.step_name,
        scene_name,
        slot: "interaction.target",
        interaction_index,
        target: interaction.target,
      });
      // Store-writing scene-operation targets execute in the scene active at
      // the start of this interaction, BEFORE any SceneChange in the same
      // response. Record them at scene_name (the pre-change scene) for the
      // seeded-target invariant.
      for (const op of interaction.response.scene_operations) {
        if (
          op.type === "ObjectStateChange" ||
          op.type === "CursorAttach" ||
          op.type === "TimedWait"
        ) {
          seeded_scene_operations.push({
            step_name: step.step_name,
            scene_name,
            operation_type: op.type,
            interaction_index,
            target: op.target,
          });
        }
      }
      // Post-validation scene transition, mirroring apply_response_scene_ops.
      for (const op of interaction.response.scene_operations) {
        if (op.type === "SceneChange") {
          current_scene = op.to_scene;
        }
      }
    });

    // final_state_matches step_validator's target, checked against the scene
    // active once the whole sequence has completed.
    const step_validator_target = step.step_validator.target;
    if (
      step.step_validator.preset === "final_state_matches" &&
      step_validator_target !== undefined
    ) {
      targets.push({
        step_name: step.step_name,
        scene_name: current_scene ?? "",
        slot: "step_validator.target",
        interaction_index: null,
        target: step_validator_target,
      });
    }

    cursor = step.next_step;
  }

  return { targets, seeded_scene_operations };
}

//============================================
// Cursor-attached (held/tool) target exemption
//============================================

// Collect every target that is ever the `target` of a CursorAttach "attach"
// scene_operation anywhere in the protocol's steps, regardless of
// reachability. Held/tool targets render through the tray/cursor-overlay
// affordance, not a static scene placement, so this pass exempts them from
// the placement-existence check (see the module-level comment above).
function collect_cursor_attached_targets(config: ProtocolConfig): Set<string> {
  const held: Set<string> = new Set();
  for (const step of config.steps ?? []) {
    for (const interaction of step.sequence) {
      for (const op of interaction.response.scene_operations) {
        if (op.type === "CursorAttach" && op.operation === "attach") {
          held.add(op.target);
        }
      }
    }
  }
  return held;
}

// Collect every target that is ever the subject of a store-writing scene
// operation that requires a seeded entry even when it is cursor-attached.
// TimedWait belongs here because start_timed_wait sets flags on its target
// before scheduling the elapsed event. A tool that is only cursor-attached
// remains exempt because it renders through the tray/cursor-overlay affordance,
// not a static scene placement.
function collect_seed_required_scene_operation_targets(config: ProtocolConfig): Set<string> {
  const subjects: Set<string> = new Set();
  for (const step of config.steps ?? []) {
    for (const interaction of step.sequence) {
      for (const op of interaction.response.scene_operations) {
        if (op.type === "ObjectStateChange" || op.type === "TimedWait") {
          subjects.add(op.target);
        }
      }
    }
  }
  return subjects;
}

//============================================
// Reachable-scene collection (construction-layer seam)
//============================================

// Collect every distinct scene name the reachable step graph visits,
// including the initial scene. The construction layer (protocol_host.tsx)
// uses this BEFORE calling create_step_machine to eagerly build a
// TargetAdapter for every scene the protocol can reach, so the load-time
// check below has a real adapter for each scene it needs, not only the entry
// scene.
export function collect_reachable_scene_names(
  config: ProtocolConfig,
  initial_scene: string | null,
): Set<string> {
  const scene_names: Set<string> = new Set();
  if (initial_scene !== null) {
    scene_names.add(initial_scene);
  }
  // Interaction/step_validator target references already carry every reachable
  // scene (one per interaction, tagged with its active scene), so the target
  // stream alone covers every scene the eager adapter build must cover.
  for (const reference of walk_protocol_references(config, initial_scene).targets) {
    if (reference.scene_name !== "") {
      scene_names.add(reference.scene_name);
    }
  }
  return scene_names;
}

//============================================
// Pass entry point
//============================================

// Validate that every authored target reference resolves to a known scene
// placement or object, checked against the scene active at that point in the
// reachable step graph. Throws UnknownAuthoredTargetError on the first miss;
// returns normally when every target resolves (or when its scene has no
// resolver entry, which is treated as "not checkable here", not a miss).
// Called inside create_step_machine, beside validate_protocol_presets,
// validate_authored_validator_values, and validate_gesture_affordances.
export function validate_target_existence(
  config: ProtocolConfig,
  initial_scene: string | null,
  resolve_scene_adapter: SceneTargetAdapterResolver,
): void {
  const protocol_name = config.protocol_name;
  const held_targets = collect_cursor_attached_targets(config);

  for (const reference of walk_protocol_references(config, initial_scene).targets) {
    if (held_targets.has(reference.target)) {
      // Held/tool target: exempt (see module-level comment).
      continue;
    }
    const adapter = resolve_scene_adapter(reference.scene_name);
    if (adapter === undefined) {
      // The scene itself is not resolvable by the supplied resolver (a
      // separate, scene-existence failure class already guarded elsewhere).
      // Skip rather than duplicate that guard here.
      continue;
    }
    const location: TargetExistenceLocation = {
      protocol_name,
      step_name: reference.step_name,
      scene_name: reference.scene_name,
      slot: reference.slot,
      interaction_index: reference.interaction_index,
      target: reference.target,
    };
    if (!adapter.has_target(reference.target)) {
      throw new UnknownAuthoredTargetError(location);
    }
    // Ambiguity invariant: an interaction target that resolves to more than one
    // placement cannot resolve to a single DOM element. Applied to interaction
    // targets only, matching resolve_to_placement's runtime path (the click,
    // type, adjust, and drag equality checks). A final_state_matches step
    // validator target reads state through resolve_to_object, which does not
    // throw on ambiguity, so it is not checked here.
    if (reference.slot === "interaction.target") {
      const competing = adapter.placements_for(reference.target);
      if (competing.length > 1) {
        throw new AmbiguousAuthoredTargetError(location, competing);
      }
    }
  }
}

//============================================
// Seeded scene-operation target invariant (pass entry point)
//============================================

// Validate that every store-writing scene-operation target is seeded (known) in
// the scene active at the point the operation executes. Throws
// UnseededSceneOperationTargetError on the first miss; returns normally when
// every target resolves (or when its scene has no resolver entry, or when it is
// an exempt held-only tool).
//
// Held-tool exemption, narrowed: a target that is cursor-attached somewhere in
// the protocol AND is never the subject of ObjectStateChange or TimedWait is
// exempt (it renders through the tray/cursor-overlay affordance, not a static
// placement). A held tool that IS an ObjectStateChange or TimedWait subject is
// NOT exempt: the operation writes a real store entry, so it must be seeded in
// the active scene.
//
// Called inside create_step_machine, beside validate_target_existence.
export function validate_seeded_scene_operation_targets(
  config: ProtocolConfig,
  initial_scene: string | null,
  resolve_scene_adapter: SceneTargetAdapterResolver,
): void {
  const protocol_name = config.protocol_name;
  const held_targets = collect_cursor_attached_targets(config);
  const seed_required_targets = collect_seed_required_scene_operation_targets(config);

  for (const reference of walk_protocol_references(config, initial_scene).seeded_scene_operations) {
    // Exempt only a held tool that never needs a seeded store entry (see above).
    if (held_targets.has(reference.target) && !seed_required_targets.has(reference.target)) {
      continue;
    }
    const adapter = resolve_scene_adapter(reference.scene_name);
    if (adapter === undefined) {
      // Scene not resolvable here (separate scene-existence failure class).
      continue;
    }
    if (!adapter.has_target(reference.target)) {
      const location: SeededSceneOperationTargetLocation = {
        protocol_name,
        step_name: reference.step_name,
        scene_name: reference.scene_name,
        operation_type: reference.operation_type,
        interaction_index: reference.interaction_index,
        target: reference.target,
      };
      throw new UnseededSceneOperationTargetError(location);
    }
  }
}

//============================================
// Subpart-suffix invariant (pass entry point)
//============================================

// Split a target into its prefix (object_name or placement_name) and the suffix
// after the FIRST ".". A prefix-only target has an empty suffix.
function split_target_suffix(target: string): { prefix: string; suffix: string } {
  const dot = target.indexOf(".");
  if (dot < 0) {
    return { prefix: target, suffix: "" };
  }
  return { prefix: target.slice(0, dot), suffix: target.slice(dot + 1) };
}

// Check one suffix-bearing target against the resolved object's declared subpart
// vocabulary. Resolves the prefix to an object_name through the scene adapter
// (so a placement_name prefix maps to its object), then requires the suffix to
// be a declared subpart instance or subpart_group of that object. Throws
// UnknownAuthoredSubpartTargetError on a miss. A target with no suffix, an
// unresolvable scene, or a prefix that names no known object here is skipped
// (prefix existence is the sibling validate_target_existence invariant).
function check_subpart_suffix(
  protocol_name: string,
  step_name: string,
  scene_name: string,
  slot: SubpartSuffixLocation["slot"],
  interaction_index: number | null,
  target: string,
  adapter: TargetAdapter | undefined,
): void {
  const { prefix, suffix } = split_target_suffix(target);
  if (suffix === "") {
    // No subpart addressed; nothing to validate here.
    return;
  }
  if (adapter === undefined || !adapter.has_target(prefix)) {
    // Scene not resolvable, or prefix unknown in this scene: the prefix-level
    // invariant owns that failure class; do not double-report it here.
    return;
  }
  // Map the prefix to its object_name (identity for an object_name prefix, the
  // owning object for a placement_name prefix), then read the declared vocab.
  const resolved_object = adapter.resolve_to_object(prefix);
  const def = OBJECT_LIBRARY[resolved_object];
  if (def === undefined) {
    // Prefix resolves in-scene but names no library object: a separate failure
    // class (an object referenced with no library entry), not a suffix miss.
    return;
  }
  const declared_subparts = def.subparts ?? [];
  const declared_groups = def.subpart_groups ?? {};
  const is_subpart = declared_subparts.includes(suffix);
  const is_group = Object.prototype.hasOwnProperty.call(declared_groups, suffix);
  if (is_subpart || is_group) {
    return;
  }
  const location: SubpartSuffixLocation = {
    protocol_name,
    step_name,
    scene_name,
    slot,
    interaction_index,
    object_name: resolved_object,
    suffix,
    target,
  };
  throw new UnknownAuthoredSubpartTargetError(
    location,
    declared_subparts.length,
    Object.keys(declared_groups).length,
  );
}

// Validate that every authored "<object>.<suffix>" target names a declared
// subpart instance or subpart_group of that object. Covers interaction targets,
// final_state_matches step_validator targets, and store-writing scene-operation
// targets, each checked against the object resolved in the scene active at that
// point in the reachable flow. This is what makes a
// group write (well_plate_96.all_wells) and a per-well write (well_plate_96.A1)
// prove their subpart addressing at load instead of silently writing a
// non-rendered pseudo-node mid-walk. Throws UnknownAuthoredSubpartTargetError on
// the first miss. Called inside create_step_machine, beside
// validate_target_existence and validate_seeded_scene_operation_targets.
export function validate_authored_subpart_targets(
  config: ProtocolConfig,
  initial_scene: string | null,
  resolve_scene_adapter: SceneTargetAdapterResolver,
): void {
  const protocol_name = config.protocol_name;
  const references = walk_protocol_references(config, initial_scene);

  for (const reference of references.targets) {
    check_subpart_suffix(
      protocol_name,
      reference.step_name,
      reference.scene_name,
      reference.slot,
      reference.interaction_index,
      reference.target,
      resolve_scene_adapter(reference.scene_name),
    );
  }
  for (const reference of references.seeded_scene_operations) {
    check_subpart_suffix(
      protocol_name,
      reference.step_name,
      reference.scene_name,
      "scene_operation.target",
      reference.interaction_index,
      reference.target,
      resolve_scene_adapter(reference.scene_name),
    );
  }
}
