// src/scene_runtime/protocol/state_field_lookup.ts
//
// Protocol-layer read-only schema-lookup seam.
//
// This module defines ONLY the lookup TYPE consumed by the load-time
// authored-value validation pass. The IMPLEMENTATION lives
// in the construction layer (src/protocol_host.tsx), which already holds the
// object registry and the per-protocol material registry. The protocol layer
// must NOT import scene_store, the object library, or any registry: it only
// names the read-only function shape and the structured result it returns.
//
// The lookup answers "what is the declared type of <target>.<field_name>?"
// by returning a discriminated union. The protocol-layer validation pass owns
// all error behavior, so the lookup never throws on an unknown
// object/subpart/field; it reports the miss as a structured result instead.
//
// Material handling: registry-backed material-identity fields (material_name /
// held_material_name on a SUBPART) are reported as { kind: "material" }, NOT a
// synthetic enum. The shared object declares only the sentinel floor
// [empty, mixed]; the curriculum's drug/assay names live in each protocol's
// materials.yaml, so treating a subpart material field as a closed enum would
// wrongly reject a valid authored material name. An OBJECT-level material field
// stays a genuine enum and reports { kind: "enum"; allowed }.
//
// References:
//   - docs/archive/decisions/m1b2_discovery_seam_proposal.md
//     (Item 2: the finalized result union and mapping rule)
//   - src/scene_runtime/layout/types.ts (StateFieldType source enum)

//============================================
// Public types
//============================================

// The structured result of a single declared-field lookup. A discriminated
// union so the protocol-layer validation pass can branch on `kind` and own
// the error behavior for each miss class.
//
// - typed:          a plain int/float/bool field. Numeric declarations also
//                   carry their authored min/max/step constraints.
// - enum:           a closed-vocabulary string field; `allowed` is the declared
//                   member set, or null when the field declares no closed set.
// - material:       a registry-backed material-identity field (subpart
//                   material_name / held_material_name). String required;
//                   membership is registry-backed, not load-checkable against a
//                   closed set here.
// - unknown_object: the object name is not declared in the object schema.
// - unknown_subpart: the object exists but declares no subpart state schema.
// - unknown_field:  the object/subpart schema exists but has no such field.
export type StateFieldLookupResult =
  | {
      kind: "typed";
      field_type: "int" | "float" | "bool";
      min?: number;
      max?: number;
      step?: number;
      unit?: string;
    }
  | { kind: "enum"; allowed: readonly string[] | null }
  | { kind: "material" }
  | { kind: "unknown_object" }
  | { kind: "unknown_subpart" }
  | { kind: "unknown_field" };

// A read-only declared-field lookup injected by the construction layer. Given a
// semantic target name (object "centrifuge" or dotted subpart
// "treatment_plate.A1") and a declared field name, it returns the structured
// lookup result above. It never throws on an unknown reference; it reports the
// miss as a structured result so the protocol-layer rule owns error behavior.
export type StateFieldLookup = (target: string, field_name: string) => StateFieldLookupResult;
