// src/scene_runtime/state/state_field_lookup_impl.ts
//
// Construction-layer implementation of the protocol-layer StateFieldLookup
// seam. This module lives in the state layer (which already owns the generated
// object schemas) and is wired into create_step_machine by the construction
// layer (src/protocol_host.tsx). The protocol layer names the lookup TYPE; this
// file is the only place that reads the declared schemas to answer a lookup.
//
// Contract (finalized; see
// docs/active_plans/decisions/m1b2_discovery_seam_proposal.md, Item 2):
//   1. Split target on the FIRST "." into (object_name, subpart|null), mirror
//      scene_store's split_target.
//   2. Select registry: subpart === null -> OBJECT_STATE_SCHEMAS; else
//      OBJECT_SUBPART_STATE_SCHEMAS. A missing object entry reports
//      unknown_object (object target) or unknown_subpart (subpart target).
//      This never throws (unlike resolve_schema) so the protocol-layer rule
//      owns error behavior.
//   3. A missing field on a resolved schema reports unknown_field.
//   4. A resolved field:
//      - subpart material_name / held_material_name -> { kind: "material" }
//        (registry-backed; NOT a synthetic enum).
//      - enum field -> { kind: "enum"; allowed: field.allowed ?? null }.
//      - else int/float/bool -> { kind: "typed"; field_type, constraints }.
//   5. A malformed target (empty object or empty subpart segment) reports the
//      matching unknown_* result rather than throwing.
//
// References:
//   - src/scene_runtime/protocol/state_field_lookup.ts (the seam type)
//   - src/scene_runtime/state/scene_store.ts (split_target, resolve_schema,
//     REGISTRY_BACKED_MATERIAL_FIELDS the impl mirrors)
//   - generated/object_library.ts (OBJECT_STATE_SCHEMAS,
//     OBJECT_SUBPART_STATE_SCHEMAS)

import {
  OBJECT_STATE_SCHEMAS,
  OBJECT_SUBPART_STATE_SCHEMAS,
} from "../../../generated/object_library.js";
import type { ObjectStateSchema } from "../layout/types.js";
import type { StateFieldLookup, StateFieldLookupResult } from "../protocol/state_field_lookup.js";

// Declared material-identity fields whose acceptance is registry-backed rather
// than gated by the declared enum `allowed` list. Mirrors
// REGISTRY_BACKED_MATERIAL_FIELDS in scene_store.ts; kept local so this module
// does not import the store. A SUBPART field with one of these names is a
// material field; an object-level field with the same name stays a closed enum.
const REGISTRY_BACKED_MATERIAL_FIELDS: ReadonlySet<string> = new Set([
  "material_name",
  "held_material_name",
]);

//============================================
// Target splitting
//============================================

// Split a target into object_name and optional subpart suffix on the FIRST
// ".", mirroring scene_store.split_target. A malformed target (empty object or
// empty subpart segment) returns null so the caller can report a structured
// unknown result instead of throwing.
function split_target(target: string): { object_name: string; subpart: string | null } | null {
  const dot_index = target.indexOf(".");
  if (dot_index < 0) {
    if (target.length === 0) {
      return null;
    }
    return { object_name: target, subpart: null };
  }
  const object_name = target.slice(0, dot_index);
  const subpart = target.slice(dot_index + 1);
  // A leading/trailing empty segment ("plate." or ".A1") is malformed.
  if (object_name.length === 0 || subpart.length === 0) {
    return null;
  }
  return { object_name, subpart };
}

//============================================
// Field classification
//============================================

// Classify a resolved field definition into the structured lookup result. The
// is_subpart flag distinguishes a registry-backed subpart material field from
// an object-level closed enum of the same field name.
function classify_field(
  schema: ObjectStateSchema,
  field_name: string,
  is_subpart: boolean,
): StateFieldLookupResult {
  const field_def = schema[field_name];
  if (field_def === undefined) {
    return { kind: "unknown_field" };
  }
  // A subpart material-identity field is registry-backed: report it as
  // material, never as the [empty, mixed] sentinel enum it declares.
  if (is_subpart && REGISTRY_BACKED_MATERIAL_FIELDS.has(field_def.field_name)) {
    return { kind: "material" };
  }
  if (field_def.type === "enum") {
    // allowed is the declared closed set, or null when the field declares none.
    const allowed = field_def.allowed ?? null;
    return { kind: "enum", allowed };
  }
  // int / float / bool are typed fields. Preserve numeric constraints so the
  // protocol load gate can reject an authored setpoint outside the real
  // instrument range before a learner reaches it.
  const result: StateFieldLookupResult = {
    kind: "typed",
    field_type: field_def.type,
  };
  if (field_def.min !== undefined) {
    result.min = field_def.min;
  }
  if (field_def.max !== undefined) {
    result.max = field_def.max;
  }
  if (field_def.step !== undefined) {
    result.step = field_def.step;
  }
  if (field_def.unit !== undefined) {
    result.unit = field_def.unit;
  }
  return result;
}

//============================================
// Lookup factory
//============================================

// Build the read-only StateFieldLookup over the generated declared schemas.
// The returned function never throws on an unknown reference; it reports the
// miss as a structured result so the protocol-layer rule owns error behavior.
export function create_state_field_lookup(): StateFieldLookup {
  function lookup_state_field(target: string, field_name: string): StateFieldLookupResult {
    const split = split_target(target);
    if (split === null) {
      // A malformed dotted target ("plate.", ".A1", "") cannot name a real
      // object/subpart. Report it as the nearest unknown class: a dotted form
      // is a subpart attempt, a bare empty string is an object attempt.
      const looks_like_subpart = target.includes(".");
      return looks_like_subpart ? { kind: "unknown_subpart" } : { kind: "unknown_object" };
    }
    const is_subpart = split.subpart !== null;
    const registry = is_subpart ? OBJECT_SUBPART_STATE_SCHEMAS : OBJECT_STATE_SCHEMAS;
    const schema = registry[split.object_name];
    if (schema === undefined) {
      // Distinguish a missing object from a missing subpart schema: a subpart
      // target whose object declares no subpart schema is unknown_subpart; a
      // bare object target with no object schema is unknown_object.
      return is_subpart ? { kind: "unknown_subpart" } : { kind: "unknown_object" };
    }
    const result = classify_field(schema, field_name, is_subpart);
    return result;
  }
  return lookup_state_field;
}
