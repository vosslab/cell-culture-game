// src/scene_runtime/state/scene_store.ts
//
// Reactive scene-object state store backed by Solid's createStore.
//
// This store is the single source of truth for per-target scene object
// state during a running protocol. The Solid renderer reads from it so visual
// updates follow state writes automatically, and the store-driven
// scene_operations layer writes to it in place of the imperative Map/Set
// in protocol_host.tsx build_scene_op_deps.
//
// What this store is:
//   - Runtime state keyed by target, including subpart targets
//     (e.g. "treatment_plate.A1").
//   - Declared object state fields (material_name, material_volume,
//     held_material_*, set_volume, set_temperature, set_rpm, ...) plus a
//     small set of runtime-only flags (is_selected,
//     cursor attach + held material).
//
// What this store is NOT:
//   - It is not the stepper. It carries no step-flow logic, no validators,
//     no next_step. The stepper calls into it through a runtime bridge.
//   - It does not infer writable keys from visual_states. Writable keys are
//     validated ONLY against the generated declared state_fields schemas
//     (OBJECT_STATE_SCHEMAS / OBJECT_SUBPART_STATE_SCHEMAS). visual_states is
//     a rendering map, not a contract for what may be written.
//
// Schema resolution rule:
//   - An object target ("centrifuge") validates writes against the object's
//     OBJECT_STATE_SCHEMAS entry.
//   - A subpart target ("treatment_plate.A1") validates writes against the
//     object's OBJECT_SUBPART_STATE_SCHEMAS entry (NOT the object-level
//     schema). The object name is the segment before the first ".".
//
// References:
//   - docs/specs/OBJECT_VOCABULARY.md (state_fields, subpart state, target
//     naming: "treatment_plate.A1")
//   - docs/PRIMARY_SPEC.md ("Scene operations": ObjectStateChange is the sole
//     primitive that mutates declared object state)
//   - src/scene_runtime/layout/types.ts (StateFieldDef, ObjectStateSchema)
//   - generated/object_library.ts (OBJECT_STATE_SCHEMAS,
//     OBJECT_SUBPART_STATE_SCHEMAS)

import { createStore, produce } from "solid-js/store";

import {
  OBJECT_LIBRARY,
  OBJECT_STATE_SCHEMAS,
  OBJECT_SUBPART_STATE_SCHEMAS,
} from "../../../generated/object_library.js";
import type { ObjectStateSchema } from "../layout/types.js";
import type { MaterialRegistry } from "../renderer/visual_state_resolver.js";
import { is_accepted_material_name } from "../renderer/material_acceptance.js";

// Declared material-identity fields whose acceptance is registry-backed (D1),
// not gated by the object's declared enum `allowed` list. The shared
// well_plate_96 object declares only the sentinel floor [empty, mixed]; the
// curriculum's drug/assay names live in each protocol's materials.yaml. These
// two fields route through is_accepted_material_name; every other enum field
// keeps the generic closed-vocabulary membership check.
const REGISTRY_BACKED_MATERIAL_FIELDS: ReadonlySet<string> = new Set([
  "material_name",
  "held_material_name",
]);

//============================================
// Public value types
//============================================

// A declared state field value is one of the three primitive kinds the
// schema declares (enum -> string, int/float -> number, bool -> boolean).
export type StateValue = string | number | boolean;

// A partial-merge write payload: a subset of declared fields for one target.
export type StatePartial = Readonly<Record<string, StateValue>>;

// Runtime-only flags and held-material cursor info for one target. These are
// store concerns, not declared object state, so they live in their own slot
// and are never schema-validated.
export interface TargetRuntimeFlags {
  // True when the target is the student's current selection.
  is_selected: boolean;
  // True when the cursor is "holding" this target (CursorAttach attach).
  cursor_attached: boolean;
  // Material currently held by the cursor while attached. Null when the
  // cursor holds nothing (detached, or attached with no material).
  held_material_name: string | null;
  held_material_volume: number | null;
  // Runtime equipment phase driven by TimedWait. The display string is an
  // authored render hint, not declared object state.
  timed_wait_active: boolean;
  timed_wait_display: string | null;
}

// One target's full reactive record: declared state plus runtime flags.
export interface TargetState {
  // The object_name this target belongs to (segment before first ".").
  object_name: string;
  // The subpart suffix ("A1") for a subpart target, or null for an object
  // target. Determines which schema validates writes.
  subpart: string | null;
  // Declared state fields, keyed by field_name. Seeded from schema defaults.
  state: Record<string, StateValue>;
  flags: TargetRuntimeFlags;
}

// The reactive store map: target name -> TargetState.
export type SceneStoreState = Record<string, TargetState>;

// One seed entry: which targets the store should initialize for a scene.
// The full target name carries the subpart suffix; object_name names the
// object-library entry whose schema seeds the defaults.
export interface TargetSeed {
  target: string;
  object_name: string;
}

// A resolved declared-state mutation, exposed read-only for the walker/debug
// surface. `before` and `after` contain exactly the fields written, after any
// declared subpart-group expansion has selected a concrete target.
export interface StateDelta {
  readonly target: string;
  readonly before: StatePartial;
  readonly after: StatePartial;
}

export interface CursorStateSnapshot {
  readonly target: string;
  readonly cursor_attached: boolean;
  readonly held_material_name: string | null;
  readonly held_material_volume: number | null;
}

//============================================
// Public store API
//============================================

export interface SceneStore {
  // Reactive read accessor. Components subscribe by reading state[target].
  readonly state: SceneStoreState;
  // Initialize targets for a scene, seeding declared fields to schema
  // defaults and runtime flags to off. Replaces any prior contents.
  seed_from_scene(seeds: ReadonlyArray<TargetSeed>): void;
  // Begin a fresh protocol session. Clears the durable archive, validates and
  // applies initial_state, then projects the supplied scene targets reactively.
  start_session(
    seeds: ReadonlyArray<TargetSeed>,
    initial_state: ReadonlyArray<{ readonly target: string; readonly state: StatePartial }>,
  ): void;
  // Restore a validated browser-session archive into one active scene. Saved
  // fields are checked again against current object schemas before the archive
  // or reactive projection changes.
  restore_session(
    seeds: ReadonlyArray<TargetSeed>,
    declared_state: Readonly<Record<string, StatePartial>>,
    cursor_state: ReadonlyArray<CursorStateSnapshot>,
    restored_state_revision: number,
  ): void;
  // Transition to another scene without discarding the scientific state of
  // exact target identities that remain present. New targets start at schema
  // defaults, absent targets are dropped, and runtime-only flags reset.
  reconcile_scene(seeds: ReadonlyArray<TargetSeed>): void;
  // Immutable snapshot of all declared state retained for this protocol
  // session, including targets absent from the currently mounted scene.
  snapshot_declared_state(): Readonly<Record<string, StatePartial>>;
  // Detached cursor-held runtime state for the currently mounted scene.
  snapshot_cursor_state(): ReadonlyArray<CursorStateSnapshot>;
  // Monotonic diagnostic revision. Declared writes and scene reconciliation
  // advance it; cursor/selection/timed-wait flags do not.
  readonly state_revision: number;
  // Most recent concrete declared-state write, or null before one occurs.
  readonly last_state_delta: StateDelta | null;
  // Every concrete declared-state write in this protocol session, in runtime
  // application order. Reconciliation preserves it; a fresh session/reset
  // clears it. Getter values are detached snapshots.
  readonly state_delta_log: ReadonlyArray<StateDelta>;
  // Ensure a single target is seeded WITHOUT disturbing other targets. Scene
  // mounting seeds declared subparts, while this remains a no-op safety net for
  // a valid target reached by a first write outside a normal mounted scene.
  // Never resets an already-seeded target or any sibling target.
  seed_target(seed: TargetSeed): void;
  // Partial-merge a declared-state write into a seeded target. Every key is
  // validated against the target's resolved schema; an undeclared key throws.
  set_object_state(target: string, partial: StatePartial): void;
  // Attach or detach the cursor for a target, optionally carrying material.
  set_cursor(target: string, op: CursorWrite): void;
  // Set one or both runtime selection/active-target flags on a target. These
  // are render-layer flags (not declared object state) the Solid renderer
  // reads reactively to drive highlight. A partial write leaves the unset
  // flag unchanged.
  set_flags(target: string, flags: FlagWrite): void;
  // NARROW reactive read of one declared subpart state field. Returns the
  // current value of state field `fieldName` for the subpart
  // `placementId + "." + subpartName` (e.g. ("treatment_plate", "A1",
  // "material_name")). The structured-subpart renderer calls this
  // inside a reactive context (memo/effect) so the read subscribes
  // fine-grained: A1 and A2 are separate targets and update independently.
  //
  // This is the ONLY read surface the renderer needs for per-subpart state;
  // it never returns the whole TargetState record or the SceneStoreState
  // tree, so a consumer cannot subscribe to the entire store by accident.
  //
  // Returns undefined when the subpart target is not seeded or the field is
  // not present on it. Reading it inside a reactive scope still subscribes to
  // the slot, so a later seed + write becomes visible reactively.
  getSubpartStateField(
    placementId: string,
    subpartName: string,
    fieldName: string,
  ): StateValue | undefined;
  // Clear all targets. The store returns to its empty initial condition.
  reset(): void;
}

// Runtime-flag write payload. The flag may be omitted to leave it as-is.
export interface FlagWrite {
  is_selected?: boolean;
  timed_wait_active?: boolean;
  timed_wait_display?: string | null;
}

// Cursor write payload. attach=true holds the target (optionally with the
// named material); attach=false detaches and clears held material.
export interface CursorWrite {
  attach: boolean;
  held_material_name?: string;
  held_material_volume?: number;
}

//============================================
// Schema resolution
//============================================

// Split a target name into object_name and optional subpart suffix. The
// object name is everything before the first "."; the subpart is the rest.
// "treatment_plate.A1" -> { object_name: "treatment_plate", subpart: "A1" }
// "centrifuge"         -> { object_name: "centrifuge", subpart: null }
function split_target(target: string): { object_name: string; subpart: string | null } {
  const dot_index = target.indexOf(".");
  if (dot_index < 0) {
    return { object_name: target, subpart: null };
  }
  const object_name = target.slice(0, dot_index);
  const subpart = target.slice(dot_index + 1);
  // A trailing/empty subpart ("plate.") is malformed and must fail loudly.
  if (object_name.length === 0 || subpart.length === 0) {
    throw new Error(`scene_store: malformed target name "${target}"`);
  }
  return { object_name, subpart };
}

// Resolve the declared state-field schema that governs writes to a target.
// Object targets use OBJECT_STATE_SCHEMAS; subpart targets use
// OBJECT_SUBPART_STATE_SCHEMAS. A missing object entry is a loud error: the
// scene referenced an object the library does not declare.
function resolve_schema(object_name: string, subpart: string | null): ObjectStateSchema {
  const registry = subpart === null ? OBJECT_STATE_SCHEMAS : OBJECT_SUBPART_STATE_SCHEMAS;
  const schema = registry[object_name];
  if (schema === undefined) {
    const level = subpart === null ? "object" : "subpart";
    throw new Error(`scene_store: no ${level} state schema for object "${object_name}"`);
  }
  return schema;
}

// Validate one concrete object/subpart target against the generated object
// vocabulary. Object-level schema presence alone is insufficient for dotted
// targets: a structured object has one shared subpart schema, but only its
// declared subpart instances are addressable.
function validate_concrete_target(
  target: string,
  object_name: string,
  subpart: string | null,
  require_declared_subpart = false,
): void {
  const object_def = OBJECT_LIBRARY[object_name];
  if (object_def === undefined) {
    throw new Error(`scene_store: unknown object "${object_name}" in target "${target}"`);
  }
  if (require_declared_subpart && subpart !== null && !object_def.subparts?.includes(subpart)) {
    throw new Error(
      `scene_store: unknown subpart "${subpart}" for object "${object_name}" in target "${target}"`,
    );
  }
}

// Resolve an initial-state target. Unlike ordinary state writes, initial state
// may deliberately name a declared group; return only concrete store targets
// so collision detection and state application are exact.
function resolve_initial_targets(target: string): string[] {
  const { object_name, subpart } = split_target(target);
  const object_def = OBJECT_LIBRARY[object_name];
  if (object_def === undefined) {
    throw new Error(
      `scene_store: initial_state target "${target}" names unknown object "${object_name}"`,
    );
  }
  if (subpart === null) {
    return [target];
  }
  if (object_def.subparts?.includes(subpart)) {
    return [target];
  }
  const group_members = object_def.subpart_groups?.[subpart];
  if (group_members !== undefined) {
    if (group_members.length === 0) {
      throw new Error(`scene_store: initial_state group "${target}" has no declared members`);
    }
    return group_members.map((member) => `${object_name}.${member}`);
  }
  throw new Error(
    `scene_store: initial_state target "${target}" names no declared subpart or subpart group`,
  );
}

//============================================
// Default-state seeding
//============================================

// Build the initial declared-state record for a target from its schema
// defaults. Every declared field starts at its declared default value.
function build_default_state(schema: ObjectStateSchema): Record<string, StateValue> {
  const state: Record<string, StateValue> = {};
  for (const field_name of Object.keys(schema)) {
    const field_def = schema[field_name];
    // Defensive: Object.keys guarantees the key exists; noUncheckedIndexedAccess
    // narrows field_def to possibly-undefined, so assert presence loudly.
    if (field_def === undefined) {
      throw new Error(`scene_store: schema field "${field_name}" missing definition`);
    }
    state[field_name] = field_def.default;
  }
  return state;
}

// Build the off-state runtime flags for a freshly seeded target.
function build_default_flags(): TargetRuntimeFlags {
  return {
    is_selected: false,
    cursor_attached: false,
    held_material_name: null,
    held_material_volume: null,
    timed_wait_active: false,
    timed_wait_display: null,
  };
}

//============================================
// Write validation
//============================================

// Validate every key/value in a partial write against the target schema.
// An undeclared key throws (ObjectStateChange writing an undeclared key is a
// hard error per the task contract). Values are also checked against the
// field's declared primitive type so a typed write cannot corrupt the store.
//
// material_registry is the active protocol's materials.yaml registry (or null
// for a diagnostic render). It backs the D1 acceptance check for SUBPART
// material-identity fields; object-level fields and non-material fields ignore
// it.
//
// is_subpart selects the validation regime for material_name / held_material_name
// exactly as the Python stepper does (validation/stepper/state.py): a SUBPART
// material field (a structured-container well/tube/lane) validates by the
// registry-backed D1 predicate, skipping its declared enum `allowed` floor,
// because the shared object declares only the sentinel floor [empty, mixed] and
// the curriculum owns the drug/assay names per protocol. An OBJECT-level material
// field keeps the generic enum `allowed` gate unchanged (its own object enumerates
// the materials it can hold). Non-material fields keep the generic enum gate at
// both levels.
function validate_partial(
  target: string,
  schema: ObjectStateSchema,
  partial: StatePartial,
  is_subpart: boolean,
  material_registry: MaterialRegistry | null,
): void {
  for (const key of Object.keys(partial)) {
    const field_def = schema[key];
    if (field_def === undefined) {
      throw new Error(`scene_store: undeclared state key "${key}" for target "${target}"`);
    }
    const value = partial[key];
    validate_value_type(target, field_def.field_name, field_def.type, value);
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new Error(
          `scene_store: field "${field_def.field_name}" on target "${target}" must be finite`,
        );
      }
      if (field_def.type === "int" && !Number.isInteger(value)) {
        throw new Error(
          `scene_store: int field "${field_def.field_name}" on target "${target}" must be an integer`,
        );
      }
      if (field_def.min !== undefined && value < field_def.min) {
        throw new Error(
          `scene_store: field "${field_def.field_name}" on target "${target}" is below minimum ${field_def.min}`,
        );
      }
      if (field_def.max !== undefined && value > field_def.max) {
        throw new Error(
          `scene_store: field "${field_def.field_name}" on target "${target}" exceeds maximum ${field_def.max}`,
        );
      }
    }
    // SUBPART material-identity fields (material_name / held_material_name) accept
    // by the registry-backed D1 predicate (sentinel-or-built-in OR a name
    // registered in the active protocol), NOT against the object's declared enum
    // `allowed` floor. This mirrors the Python stepper so a per-well drug write
    // (carboplatin, mtt) that the stepper accepts also reaches the well at runtime.
    if (is_subpart && REGISTRY_BACKED_MATERIAL_FIELDS.has(field_def.field_name)) {
      validate_material_name(target, field_def.field_name, value, material_registry);
      continue;
    }
    // Closed-vocabulary enum membership check: an enum write whose value is not
    // in the declared `allowed` set is a bad ObjectStateChange and must fail
    // loud at the store, never degrade silently in the renderer. Only enforced
    // when the schema actually declares an `allowed` list (some enum fields are
    // open-ended sentinels and declare none). Object-level material fields stay
    // on this path: their own object enumerates the materials it can hold.
    if (field_def.type === "enum" && field_def.allowed !== undefined) {
      validate_enum_membership(target, field_def.field_name, field_def.allowed, value);
    }
  }
}

// Check a material-identity value against the registry-backed D1 predicate. A
// value that is neither a built-in (`empty`, `mixed`) nor registered in the
// active protocol's registry is a bad ObjectStateChange and throws at the store,
// exactly as the Python stepper rejects an unregistered non-sentinel material.
function validate_material_name(
  target: string,
  field_name: string,
  value: StateValue | undefined,
  material_registry: MaterialRegistry | null,
): void {
  // value is already proven defined + string-typed by validate_value_type.
  if (typeof value !== "string") {
    return;
  }
  if (!is_accepted_material_name(value, material_registry)) {
    throw new Error(
      `scene_store: material field "${field_name}" on target "${target}" got "${value}",` +
        ` not a built-in (empty, mixed) and not registered in the active protocol material registry`,
    );
  }
}

// Check an enum value against the declared allowed set. A value outside the set
// throws so a typo'd or out-of-vocabulary enum write fails at the store.
function validate_enum_membership(
  target: string,
  field_name: string,
  allowed: ReadonlyArray<string>,
  value: StateValue | undefined,
): void {
  // value is already proven defined + string-typed by validate_value_type.
  if (typeof value === "string" && !allowed.includes(value)) {
    throw new Error(
      `scene_store: enum field "${field_name}" on target "${target}" got "${value}",` +
        ` not in allowed [${allowed.join(", ")}]`,
    );
  }
}

// Check a single value against the declared field type. enum values are
// strings; int/float are numbers; bool is boolean. A type mismatch throws.
function validate_value_type(
  target: string,
  field_name: string,
  field_type: ObjectStateSchema[string]["type"],
  value: StateValue | undefined,
): void {
  if (value === undefined) {
    throw new Error(`scene_store: undefined value for field "${field_name}" on target "${target}"`);
  }
  const actual = typeof value;
  let expected: "string" | "number" | "boolean";
  if (field_type === "enum") {
    expected = "string";
  } else if (field_type === "bool") {
    expected = "boolean";
  } else {
    // int and float both map to JS number.
    expected = "number";
  }
  if (actual !== expected) {
    throw new Error(
      `scene_store: field "${field_name}" on target "${target}" expects ${expected}` +
        ` (${field_type}), got ${actual}`,
    );
  }
}

//============================================
// Store factory
//============================================

// Create a fresh reactive scene store. Each protocol mount creates one
// store; tests create one per case for isolation.
//
// material_registry is the active protocol's materials.yaml registry (the
// PROTOCOL_MATERIALS entry for this protocol), or null when there is no protocol
// material context. It backs the D1 acceptance check for material_name /
// held_material_name writes so a registered drug (carboplatin, mtt) is accepted
// while an unregistered non-sentinel name is rejected -- mirroring the Python
// stepper. The default null keeps existing call sites and tests that write only
// sentinels (empty, mixed) working unchanged.
export function create_scene_store(material_registry: MaterialRegistry | null = null): SceneStore {
  const [state, set_state] = createStore<SceneStoreState>({});
  // Durable protocol-session archive. It intentionally is not a Solid store:
  // only the active scene projection drives rendering. Copies are taken at the
  // boundary so no Solid proxy leaks into retained scientific state.
  let archive: Record<string, TargetState> = {};
  let state_revision = 0;
  let last_state_delta: StateDelta | null = null;
  let state_delta_log: StateDelta[] = [];

  function make_fresh_target(seed: TargetSeed): TargetState {
    const { object_name, subpart } = split_target(seed.target);
    if (object_name !== seed.object_name) {
      throw new Error(
        `scene_store: seed target "${seed.target}" object segment "${object_name}"` +
          ` does not match declared object_name "${seed.object_name}"`,
      );
    }
    validate_concrete_target(seed.target, object_name, subpart);
    const schema = resolve_schema(object_name, subpart);
    return {
      object_name,
      subpart,
      state: build_default_state(schema),
      flags: build_default_flags(),
    };
  }

  function validate_seed(seed: TargetSeed): void {
    const { object_name, subpart } = split_target(seed.target);
    if (object_name !== seed.object_name) {
      throw new Error(
        `scene_store: seed target "${seed.target}" object segment "${object_name}"` +
          ` does not match declared object_name "${seed.object_name}"`,
      );
    }
    validate_concrete_target(seed.target, object_name, subpart);
    resolve_schema(object_name, subpart);
  }

  function clone_archive_state(entry: TargetState): Record<string, StateValue> {
    return { ...entry.state };
  }

  function ensure_archive_target(seed: TargetSeed): TargetState {
    const existing = archive[seed.target];
    if (existing !== undefined) {
      return existing;
    }
    const fresh = make_fresh_target(seed);
    archive[seed.target] = { ...fresh, state: { ...fresh.state } };
    return archive[seed.target] as TargetState;
  }

  //----------------------------------------
  function build_scene_state(
    seeds: ReadonlyArray<TargetSeed>,
    _preserve_existing: boolean,
  ): SceneStoreState {
    // Build the full next map before any mutation so a malformed seed makes
    // both replacement and reconciliation all-or-nothing.
    const next: SceneStoreState = {};
    for (const seed of seeds) {
      validate_seed(seed);
      const archive_entry = ensure_archive_target(seed);
      // A scene projection always gets fresh runtime flags, while all declared
      // fields hydrate from the protocol archive whether or not the target was
      // present in the immediately preceding scene.
      next[seed.target] = {
        object_name: archive_entry.object_name,
        subpart: archive_entry.subpart,
        state: clone_archive_state(archive_entry),
        flags: build_default_flags(),
      };
    }
    return next;
  }

  //----------------------------------------
  function seed_from_scene(seeds: ReadonlyArray<TargetSeed>): void {
    // Compatibility entry point for stand-alone renderer/tests: this is a
    // fresh, no-initial-state session rather than an accidental carry-over.
    archive = {};
    last_state_delta = null;
    state_delta_log = [];
    const next = build_scene_state(seeds, false);
    // Replace the target set for a (re)entered scene. Clear stale keys first:
    // Solid's createStore merges a plain-object write and never deletes keys
    // absent from the new object, so an explicit delete pass is required.
    replace_all(next);
  }

  //----------------------------------------
  function start_session(
    seeds: ReadonlyArray<TargetSeed>,
    initial_state: ReadonlyArray<{ readonly target: string; readonly state: StatePartial }>,
  ): void {
    // Validate/build in local structures first. A malformed initial-state
    // declaration cannot partially reset a live session.
    const next_archive: Record<string, TargetState> = {};
    const ensure_local = (target: string, require_declared_subpart: boolean): TargetState => {
      const existing = next_archive[target];
      if (existing !== undefined) {
        return existing;
      }
      const { object_name, subpart } = split_target(target);
      validate_concrete_target(target, object_name, subpart, require_declared_subpart);
      const schema = resolve_schema(object_name, subpart);
      const fresh: TargetState = {
        object_name,
        subpart,
        state: build_default_state(schema),
        flags: build_default_flags(),
      };
      next_archive[target] = fresh;
      return fresh;
    };
    for (const seed of seeds) {
      const { object_name } = split_target(seed.target);
      if (object_name !== seed.object_name) {
        throw new Error(
          `scene_store: seed target "${seed.target}" does not match object_name "${seed.object_name}"`,
        );
      }
      ensure_local(seed.target, false);
    }
    const resolved = new Set<string>();
    for (const entry of initial_state) {
      const concrete_targets = resolve_initial_targets(entry.target);
      for (const target of concrete_targets) {
        if (resolved.has(target)) {
          throw new Error(
            `scene_store: initial_state target "${entry.target}" overlaps resolved target "${target}"`,
          );
        }
        resolved.add(target);
        const archive_entry = ensure_local(target, true);
        const schema = resolve_schema(archive_entry.object_name, archive_entry.subpart);
        validate_partial(
          target,
          schema,
          entry.state,
          archive_entry.subpart !== null,
          material_registry,
        );
        for (const key of Object.keys(entry.state)) {
          const value = entry.state[key];
          if (value !== undefined) {
            archive_entry.state[key] = value;
          }
        }
      }
    }
    archive = next_archive;
    last_state_delta = null;
    state_delta_log = [];
    const next = build_scene_state(seeds, false);
    replace_all(next);
    state_revision += 1;
  }

  //----------------------------------------
  function reconcile_scene(seeds: ReadonlyArray<TargetSeed>): void {
    const next = build_scene_state(seeds, true);
    replace_all(next);
    state_revision += 1;
  }

  //----------------------------------------
  function restore_session(
    seeds: ReadonlyArray<TargetSeed>,
    declared_state: Readonly<Record<string, StatePartial>>,
    cursor_state: ReadonlyArray<CursorStateSnapshot>,
    restored_state_revision: number,
  ): void {
    if (!Number.isSafeInteger(restored_state_revision) || restored_state_revision < 0) {
      throw new Error("scene_store: restored state revision must be a non-negative integer");
    }

    // Validate and build every archived target before touching live state.
    const next_archive: Record<string, TargetState> = {};
    for (const [target, fields] of Object.entries(declared_state)) {
      const { object_name, subpart } = split_target(target);
      // Scene-defined structured instances (for example generated rack slots)
      // can be concrete without appearing in object_def.subparts. Match the
      // normal scene-seed boundary here; schema validation below still rejects
      // an unknown object or unsupported subpart state shape.
      validate_concrete_target(target, object_name, subpart);
      const schema = resolve_schema(object_name, subpart);
      const expected_fields = Object.keys(schema).sort();
      const restored_fields = Object.keys(fields).sort();
      const exact_schema =
        expected_fields.length === restored_fields.length &&
        expected_fields.every((field, index) => field === restored_fields[index]);
      if (!exact_schema) {
        throw new Error(`scene_store: restored target "${target}" does not match its state schema`);
      }
      validate_partial(target, schema, fields, subpart !== null, material_registry);
      next_archive[target] = {
        object_name,
        subpart,
        state: { ...fields },
        flags: build_default_flags(),
      };
    }

    // The mounted scene must be wholly represented by the restored archive.
    const next_scene: SceneStoreState = {};
    for (const seed of seeds) {
      validate_seed(seed);
      const restored = next_archive[seed.target];
      if (restored === undefined) {
        throw new Error(
          `scene_store: restored archive is missing active scene target "${seed.target}"`,
        );
      }
      next_scene[seed.target] = {
        object_name: restored.object_name,
        subpart: restored.subpart,
        state: { ...restored.state },
        flags: build_default_flags(),
      };
    }

    const cursor_targets = new Set<string>();
    for (const cursor of cursor_state) {
      if (cursor_targets.has(cursor.target)) {
        throw new Error(`scene_store: duplicate restored cursor target "${cursor.target}"`);
      }
      cursor_targets.add(cursor.target);
      const active = next_scene[cursor.target];
      if (active === undefined) {
        throw new Error(
          `scene_store: restored cursor target "${cursor.target}" is not in the active scene`,
        );
      }
      active.flags.cursor_attached = cursor.cursor_attached;
      active.flags.held_material_name = cursor.held_material_name;
      active.flags.held_material_volume = cursor.held_material_volume;
    }

    archive = next_archive;
    last_state_delta = null;
    state_delta_log = [];
    state_revision = restored_state_revision;
    replace_all(next_scene);
  }

  //----------------------------------------
  // Replace the entire store contents with next, deleting every prior key.
  // Done inside one produce so the reactive write is atomic.
  function replace_all(next: SceneStoreState): void {
    set_state(
      produce((store: SceneStoreState) => {
        for (const key of Object.keys(store)) {
          delete store[key];
        }
        for (const key of Object.keys(next)) {
          store[key] = next[key] as TargetState;
        }
      }),
    );
  }

  //----------------------------------------
  // Add one target if it is not already present, leaving every existing target
  // untouched. Unlike seed_from_scene (which replaces the whole map), this is a
  // targeted insert so a subpart write cannot reset its siblings' state.
  function seed_target(seed: TargetSeed): void {
    if (state[seed.target] !== undefined) {
      // Already seeded; never reset an existing target.
      return;
    }
    const retained = ensure_archive_target(seed);
    const fresh: TargetState = {
      object_name: retained.object_name,
      subpart: retained.subpart,
      state: clone_archive_state(retained),
      flags: build_default_flags(),
    };
    set_state(
      produce((store: SceneStoreState) => {
        store[seed.target] = fresh;
      }),
    );
  }

  //----------------------------------------
  function require_target(target: string): TargetState {
    const entry = state[target];
    if (entry === undefined) {
      throw new Error(`scene_store: target "${target}" is not seeded; call seed_from_scene first`);
    }
    return entry;
  }

  //----------------------------------------
  function set_object_state(target: string, partial: StatePartial): void {
    const entry = require_target(target);
    const schema = resolve_schema(entry.object_name, entry.subpart);
    // Validate before writing so a bad key/value leaves the store untouched.
    // SUBPART material-identity fields validate against the active protocol
    // registry (D1); object-level and non-material fields keep the declared-schema
    // checks. entry.subpart is non-null exactly for a subpart target.
    validate_partial(target, schema, partial, entry.subpart !== null, material_registry);
    const before: Record<string, StateValue> = {};
    const after: Record<string, StateValue> = {};
    for (const key of Object.keys(partial)) {
      const value = partial[key];
      if (value !== undefined) {
        before[key] = entry.state[key] as StateValue;
        after[key] = value;
      }
    }
    // Partial-merge: only the named fields change; the rest stay as-is.
    set_state(
      produce((store: SceneStoreState) => {
        const current = store[target];
        if (current === undefined) {
          // Cannot happen: require_target already proved presence. Guard for
          // noUncheckedIndexedAccess and to fail loudly if it ever does.
          throw new Error(`scene_store: target "${target}" vanished during write`);
        }
        for (const key of Object.keys(partial)) {
          const value = partial[key];
          if (value === undefined) {
            continue;
          }
          current.state[key] = value;
        }
      }),
    );
    const archived = archive[target];
    if (archived === undefined) {
      throw new Error(`scene_store: target "${target}" is active but absent from protocol archive`);
    }
    for (const key of Object.keys(after)) {
      const value = after[key];
      if (value !== undefined) {
        archived.state[key] = value;
      }
    }
    const delta: StateDelta = {
      target,
      before: Object.freeze({ ...before }),
      after: Object.freeze({ ...after }),
    };
    last_state_delta = delta;
    state_delta_log.push(delta);
    state_revision += 1;
  }

  //----------------------------------------
  function set_cursor(target: string, op: CursorWrite): void {
    // Proves the target is seeded; throws otherwise.
    require_target(target);
    set_state(
      produce((store: SceneStoreState) => {
        const current = store[target];
        if (current === undefined) {
          throw new Error(`scene_store: target "${target}" vanished during cursor write`);
        }
        if (op.attach) {
          current.flags.cursor_attached = true;
          current.flags.held_material_name = op.held_material_name ?? null;
          current.flags.held_material_volume = op.held_material_volume ?? null;
        } else {
          // Detach clears the held material so a stale name cannot linger.
          current.flags.cursor_attached = false;
          current.flags.held_material_name = null;
          current.flags.held_material_volume = null;
        }
      }),
    );
  }

  //----------------------------------------
  function set_flags(target: string, flags: FlagWrite): void {
    // Proves the target is seeded; throws otherwise.
    require_target(target);
    set_state(
      produce((store: SceneStoreState) => {
        const current = store[target];
        if (current === undefined) {
          throw new Error(`scene_store: target "${target}" vanished during flag write`);
        }
        // Partial-merge: only the named flags change.
        if (flags.is_selected !== undefined) {
          current.flags.is_selected = flags.is_selected;
        }
        if (flags.timed_wait_active !== undefined) {
          current.flags.timed_wait_active = flags.timed_wait_active;
        }
        if (flags.timed_wait_display !== undefined) {
          current.flags.timed_wait_display = flags.timed_wait_display;
        }
      }),
    );
  }

  //----------------------------------------
  // NARROW reactive read of one subpart state field. The full subpart target
  // is placementId + "." + subpartName. Each property access below walks the
  // Solid store proxy, so reading this inside a memo/effect subscribes only to
  // that one field on that one subpart -- A1 and A2 are distinct targets and
  // track independently. No object is copied out, so the consumer cannot
  // accidentally subscribe to the whole TargetState or the store tree.
  function getSubpartStateField(
    placementId: string,
    subpartName: string,
    fieldName: string,
  ): StateValue | undefined {
    // Build the subpart target name ("treatment_plate.A1").
    const target = `${placementId}.${subpartName}`;
    // Reactive index into the store map. Reading a missing slot still
    // subscribes to it, so a later seed becomes visible reactively.
    const entry = state[target];
    if (entry === undefined) {
      return undefined;
    }
    // Reactive index into this subpart's declared-state record. Returns the
    // field value directly; an absent field yields undefined.
    return entry.state[fieldName];
  }

  //----------------------------------------
  function reset(): void {
    // Full reset: the store returns to its empty initial condition. Use the
    // explicit delete pass so no stale keys survive (see replace_all).
    replace_all({});
    archive = {};
    last_state_delta = null;
    state_delta_log = [];
    state_revision += 1;
  }

  //----------------------------------------
  function snapshot_declared_state(): Readonly<Record<string, StatePartial>> {
    const snapshot: Record<string, StatePartial> = {};
    for (const target of Object.keys(archive)) {
      const entry = archive[target];
      if (entry !== undefined) {
        snapshot[target] = { ...entry.state };
      }
    }
    return snapshot;
  }

  //----------------------------------------
  function snapshot_cursor_state(): ReadonlyArray<CursorStateSnapshot> {
    const snapshot: CursorStateSnapshot[] = [];
    for (const target of Object.keys(state)) {
      const entry = state[target];
      if (entry === undefined || !entry.flags.cursor_attached) {
        continue;
      }
      snapshot.push({
        target,
        cursor_attached: true,
        held_material_name: entry.flags.held_material_name,
        held_material_volume: entry.flags.held_material_volume,
      });
    }
    return snapshot;
  }

  const store: SceneStore = {
    state,
    seed_from_scene,
    start_session,
    restore_session,
    reconcile_scene,
    snapshot_declared_state,
    snapshot_cursor_state,
    get state_revision(): number {
      return state_revision;
    },
    get last_state_delta(): StateDelta | null {
      return last_state_delta === null
        ? null
        : {
            target: last_state_delta.target,
            before: { ...last_state_delta.before },
            after: { ...last_state_delta.after },
          };
    },
    get state_delta_log(): ReadonlyArray<StateDelta> {
      return state_delta_log.map((delta) => ({
        target: delta.target,
        before: { ...delta.before },
        after: { ...delta.after },
      }));
    },
    seed_target,
    set_object_state,
    set_cursor,
    set_flags,
    getSubpartStateField,
    reset,
  };
  return store;
}
