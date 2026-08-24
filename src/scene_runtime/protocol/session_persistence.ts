// Versioned browser persistence for protocol progress.
//
// This module owns the localStorage boundary. Saved JSON is always treated as
// unknown and rebuilt through explicit runtime validation before the host may
// restore it. The protocol runtime and scene store remain the in-memory sources
// of truth; persistence records their serializable checkpoints after accepted
// learner actions.

import { SCHEMA_VERSION } from "../../schema_version.js";
import type { ProtocolConfig } from "../../shell/adapter/types.js";
import type { StepMachineCheckpoint } from "./step_machine.js";

export const PROTOCOL_SESSION_STORAGE_KEY = "virtual_lab.protocol_sessions";

export type SessionSaveStatus = "fresh" | "restored" | "saved" | "unavailable";

export type PersistedStateValue = string | number | boolean;

export type PersistedDeclaredState = Readonly<
  Record<string, Readonly<Record<string, PersistedStateValue>>>
>;

export interface PersistedCursorState {
  readonly target: string;
  readonly cursor_attached: boolean;
  readonly held_material_name: string | null;
  readonly held_material_volume: number | null;
}

export interface ProtocolSessionState {
  readonly protocol_name: string;
  readonly protocol_fingerprint: string;
  readonly persistence_revision: number;
  readonly state_revision: number;
  readonly machine: StepMachineCheckpoint;
  readonly declared_state: PersistedDeclaredState;
  readonly cursor_state: ReadonlyArray<PersistedCursorState>;
}

export type ProtocolSessionLoadResult =
  | { readonly kind: "fresh"; readonly session: null }
  | { readonly kind: "restored"; readonly session: ProtocolSessionState }
  | { readonly kind: "discarded"; readonly session: null }
  | { readonly kind: "unavailable"; readonly session: null };

export interface ProtocolSessionPersistence {
  load(): ProtocolSessionLoadResult;
  save(
    checkpoint: StepMachineCheckpoint,
    declared_state: PersistedDeclaredState,
    cursor_state: ReadonlyArray<PersistedCursorState>,
    state_revision: number,
  ): number | null;
  clear(): boolean;
}

interface SessionStoreRoot {
  readonly schema_version: number;
  readonly sessions: Readonly<Record<string, ProtocolSessionState>>;
}

interface BrowserStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

//============================================
// Protocol identity
//============================================

// A small deterministic FNV-1a fingerprint binds a save to the exact flattened
// protocol shape. It is not a security hash; it is a stale-progress guard.
export function fingerprint_protocol(config: ProtocolConfig): string {
  const serialized = JSON.stringify(config);
  let hash = 0x811c9dc5;
  for (let index = 0; index < serialized.length; index += 1) {
    hash ^= serialized.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  const unsigned_hex = (hash >>> 0).toString(16).padStart(8, "0");
  return `${serialized.length}-${unsigned_hex}`;
}

//============================================
// Unknown JSON validation
//============================================

function is_record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function read_string(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

function read_nullable_string(
  record: Record<string, unknown>,
  key: string,
): string | null | undefined {
  const value = record[key];
  if (value === null) {
    return null;
  }
  return typeof value === "string" ? value : undefined;
}

function read_nonnegative_integer(record: Record<string, unknown>, key: string): number | null {
  const value = record[key];
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

function parse_string_array(value: unknown): string[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const strings: string[] = [];
  for (const item of value) {
    if (typeof item !== "string") {
      return null;
    }
    strings.push(item);
  }
  return strings;
}

function parse_pending_timed_wait(
  value: unknown,
): StepMachineCheckpoint["pending_timed_wait"] | undefined {
  if (value === null) {
    return null;
  }
  if (!is_record(value)) {
    return undefined;
  }
  const step_name = read_string(value, "step_name");
  const interaction_index = read_nonnegative_integer(value, "interaction_index");
  const target = read_string(value, "target");
  const next_operation_index = read_nonnegative_integer(value, "next_operation_index");
  if (
    step_name === null ||
    interaction_index === null ||
    target === null ||
    next_operation_index === null
  ) {
    return undefined;
  }
  return { step_name, interaction_index, target, next_operation_index };
}

function parse_checkpoint(value: unknown): StepMachineCheckpoint | null {
  if (!is_record(value)) {
    return null;
  }
  const active_step_name = read_nullable_string(value, "active_step_name");
  const interaction_index = read_nonnegative_integer(value, "interaction_index");
  const completed_step_names = parse_string_array(value.completed_step_names);
  const current_scene = read_nullable_string(value, "current_scene");
  const is_complete = value.is_complete;
  const pending_timed_wait = parse_pending_timed_wait(value.pending_timed_wait);
  if (
    active_step_name === undefined ||
    interaction_index === null ||
    completed_step_names === null ||
    current_scene === undefined ||
    typeof is_complete !== "boolean" ||
    pending_timed_wait === undefined
  ) {
    return null;
  }
  return {
    active_step_name,
    interaction_index,
    completed_step_names,
    current_scene,
    is_complete,
    pending_timed_wait,
  };
}

function parse_declared_state(value: unknown): PersistedDeclaredState | null {
  if (!is_record(value)) {
    return null;
  }
  const declared_state: Record<string, Record<string, PersistedStateValue>> = {};
  for (const [target, raw_fields] of Object.entries(value)) {
    if (!is_record(raw_fields)) {
      return null;
    }
    const fields: Record<string, PersistedStateValue> = {};
    for (const [field, raw_value] of Object.entries(raw_fields)) {
      if (
        typeof raw_value !== "string" &&
        typeof raw_value !== "number" &&
        typeof raw_value !== "boolean"
      ) {
        return null;
      }
      if (typeof raw_value === "number" && !Number.isFinite(raw_value)) {
        return null;
      }
      fields[field] = raw_value;
    }
    declared_state[target] = fields;
  }
  return declared_state;
}

function parse_cursor_state(value: unknown): PersistedCursorState[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const cursor_state: PersistedCursorState[] = [];
  for (const raw_entry of value) {
    if (!is_record(raw_entry)) {
      return null;
    }
    const target = read_string(raw_entry, "target");
    const cursor_attached = raw_entry.cursor_attached;
    const held_material_name = read_nullable_string(raw_entry, "held_material_name");
    const raw_volume = raw_entry.held_material_volume;
    const held_material_volume =
      raw_volume === null
        ? null
        : typeof raw_volume === "number" && Number.isFinite(raw_volume)
          ? raw_volume
          : undefined;
    if (
      target === null ||
      typeof cursor_attached !== "boolean" ||
      held_material_name === undefined ||
      held_material_volume === undefined
    ) {
      return null;
    }
    cursor_state.push({
      target,
      cursor_attached,
      held_material_name,
      held_material_volume,
    });
  }
  return cursor_state;
}

function parse_session(value: unknown): ProtocolSessionState | null {
  if (!is_record(value)) {
    return null;
  }
  const protocol_name = read_string(value, "protocol_name");
  const protocol_fingerprint = read_string(value, "protocol_fingerprint");
  const persistence_revision = read_nonnegative_integer(value, "persistence_revision");
  const state_revision = read_nonnegative_integer(value, "state_revision");
  const machine = parse_checkpoint(value.machine);
  const declared_state = parse_declared_state(value.declared_state);
  const cursor_state = parse_cursor_state(value.cursor_state);
  if (
    protocol_name === null ||
    protocol_fingerprint === null ||
    persistence_revision === null ||
    state_revision === null ||
    machine === null ||
    declared_state === null ||
    cursor_state === null
  ) {
    return null;
  }
  return {
    protocol_name,
    protocol_fingerprint,
    persistence_revision,
    state_revision,
    machine,
    declared_state,
    cursor_state,
  };
}

function parse_root(value: unknown): SessionStoreRoot | null {
  if (!is_record(value) || value.schema_version !== SCHEMA_VERSION || !is_record(value.sessions)) {
    return null;
  }
  const sessions: Record<string, ProtocolSessionState> = {};
  for (const [protocol_name, raw_session] of Object.entries(value.sessions)) {
    const session = parse_session(raw_session);
    if (session === null || session.protocol_name !== protocol_name) {
      return null;
    }
    sessions[protocol_name] = session;
  }
  return { schema_version: SCHEMA_VERSION, sessions };
}

function decode_root(raw: string | null): SessionStoreRoot | null {
  if (raw === null) {
    return { schema_version: SCHEMA_VERSION, sessions: {} };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  return parse_root(parsed);
}

function without_protocol(root: SessionStoreRoot, protocol_name: string): SessionStoreRoot {
  const sessions: Record<string, ProtocolSessionState> = {};
  for (const [name, session] of Object.entries(root.sessions)) {
    if (name !== protocol_name) {
      sessions[name] = session;
    }
  }
  return { schema_version: SCHEMA_VERSION, sessions };
}

//============================================
// Storage facade
//============================================

export function create_protocol_session_persistence(
  storage: BrowserStorage,
  protocol_name: string,
  protocol_fingerprint: string,
): ProtocolSessionPersistence {
  let persistence_revision = 0;

  function load(): ProtocolSessionLoadResult {
    let root: SessionStoreRoot | null;
    try {
      root = decode_root(storage.getItem(PROTOCOL_SESSION_STORAGE_KEY));
    } catch {
      return { kind: "unavailable", session: null };
    }
    if (root === null) {
      try {
        storage.removeItem(PROTOCOL_SESSION_STORAGE_KEY);
      } catch {
        return { kind: "unavailable", session: null };
      }
      return { kind: "discarded", session: null };
    }
    const session = root.sessions[protocol_name];
    if (session === undefined) {
      return { kind: "fresh", session: null };
    }
    if (session.protocol_fingerprint !== protocol_fingerprint) {
      const next_root = without_protocol(root, protocol_name);
      try {
        storage.setItem(PROTOCOL_SESSION_STORAGE_KEY, JSON.stringify(next_root));
      } catch {
        return { kind: "unavailable", session: null };
      }
      return { kind: "discarded", session: null };
    }
    persistence_revision = session.persistence_revision;
    return { kind: "restored", session };
  }

  function save(
    checkpoint: StepMachineCheckpoint,
    declared_state: PersistedDeclaredState,
    cursor_state: ReadonlyArray<PersistedCursorState>,
    state_revision: number,
  ): number | null {
    try {
      const current_root = decode_root(storage.getItem(PROTOCOL_SESSION_STORAGE_KEY));
      const root = current_root ?? { schema_version: SCHEMA_VERSION, sessions: {} };
      persistence_revision += 1;
      const session: ProtocolSessionState = {
        protocol_name,
        protocol_fingerprint,
        persistence_revision,
        state_revision,
        machine: checkpoint,
        declared_state,
        cursor_state,
      };
      const sessions: Record<string, ProtocolSessionState> = { ...root.sessions };
      sessions[protocol_name] = session;
      const next_root: SessionStoreRoot = { schema_version: SCHEMA_VERSION, sessions };
      storage.setItem(PROTOCOL_SESSION_STORAGE_KEY, JSON.stringify(next_root));
      return persistence_revision;
    } catch {
      return null;
    }
  }

  function clear(): boolean {
    try {
      const root = decode_root(storage.getItem(PROTOCOL_SESSION_STORAGE_KEY));
      if (root === null) {
        storage.removeItem(PROTOCOL_SESSION_STORAGE_KEY);
        persistence_revision = 0;
        return true;
      }
      const next_root = without_protocol(root, protocol_name);
      storage.setItem(PROTOCOL_SESSION_STORAGE_KEY, JSON.stringify(next_root));
      persistence_revision = 0;
      return true;
    } catch {
      return false;
    }
  }

  return { load, save, clear };
}
