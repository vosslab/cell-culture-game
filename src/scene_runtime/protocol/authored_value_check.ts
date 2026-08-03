// src/scene_runtime/protocol/authored_value_check.ts
//
// Load-time authored-value validation pass.
//
// This pass runs once at protocol load, inside create_step_machine, BEFORE any
// handler closure is built. It reads the AUTHORED shapes of the only two
// state-touching validator presets and checks every authored value against the
// declared field type reported by the injected read-only schema lookup:
//
//   - target_with_value (interaction): object = interaction.target, the flat
//     {field: value} map = interaction.validator.value.
//   - final_state_matches (step): object = step.step_validator.target, the flat
//     {field: value} map = step.step_validator.contains.
//
// The pass owns ALL error behavior for schema misses and bad values. It never
// falls back, never returns a silent false, and never wraps work in a broad
// try/catch. The injected lookup never throws; it reports every miss as a
// structured result, and this pass branches on that result's `kind`.
//
// The runtime numeric-coercion backstop in validators.ts stays untouched as a
// runtime backstop. This is the load-time front line.
//
// References:
//   - docs/archive/decisions/m1b2_discovery_seam_proposal.md
//     (Items 1-4: authored shapes, result kinds, the two state-touching presets)
//   - src/scene_runtime/protocol/state_field_lookup.ts (StateFieldLookup,
//     StateFieldLookupResult)

import type { ProtocolConfig } from "../../shell/adapter/types";
import type { StateFieldLookup, StateFieldLookupResult } from "./state_field_lookup";

//============================================
// Public surface
//============================================

// The authored validator slot a flagged value came from. Used only to label the
// error so the offending YAML is locatable.
type AuthoredValidatorKind = "target_with_value" | "final_state_matches";

// Construction-time inputs for the load-time authored-value pass. Threaded as an
// options object so future load-time checks can take more injected, read-only
// dependencies without churning the signature.
export interface AuthoredValueCheckOptions {
  // The parsed protocol whose authored validator values are being checked.
  readonly protocol_config: ProtocolConfig;
  // Read-only declared-field lookup supplied by the construction layer. Never
  // throws; reports every miss as a structured result.
  readonly lookup_state_field: StateFieldLookup;
}

//============================================
// Named author-facing errors (four miss classes)
//============================================

// Common locating fields every authored-value error carries so the offending
// YAML can be found without guessing.
interface AuthoredValueLocation {
  readonly protocol_name: string;
  readonly step_name: string;
  readonly validator_kind: AuthoredValidatorKind;
  readonly target: string;
  readonly field: string;
  readonly authored_value: string | number | boolean;
}

// Build the shared "in protocol ... step ... validator ... target ... field ..."
// suffix used by every error message.
function location_suffix(location: AuthoredValueLocation): string {
  let suffix = ` in protocol "${location.protocol_name}",`;
  suffix += ` step "${location.step_name}",`;
  suffix += ` validator "${location.validator_kind}",`;
  suffix += ` target "${location.target}",`;
  suffix += ` field "${location.field}",`;
  suffix += ` authored value ${format_value(location.authored_value)}.`;
  return suffix;
}

// Render an authored value for an error message: strings are quoted, numbers and
// booleans are shown bare so the reader can see the literal type at a glance.
function format_value(value: string | number | boolean): string {
  if (typeof value === "string") {
    return `"${value}"`;
  }
  return String(value);
}

// Class 1: the named object is not declared in the object schema.
export class UnknownAuthoredObjectError extends Error {
  constructor(location: AuthoredValueLocation) {
    let message = `Authored validator names an unknown object`;
    message += location_suffix(location);
    message += ` No object schema is declared for target "${location.target}".`;
    super(message);
    this.name = "UnknownAuthoredObjectError";
  }
}

// Class 2: the object exists but declares no subpart state schema for the dotted
// subpart in the target.
export class UnknownAuthoredSubpartError extends Error {
  constructor(location: AuthoredValueLocation) {
    let message = `Authored validator names an unknown subpart`;
    message += location_suffix(location);
    message += ` The object exists but declares no subpart state schema for`;
    message += ` target "${location.target}".`;
    super(message);
    this.name = "UnknownAuthoredSubpartError";
  }
}

// Class 3: the object/subpart schema exists but declares no such field.
export class UnknownAuthoredFieldError extends Error {
  constructor(location: AuthoredValueLocation) {
    let message = `Authored validator names an unknown field`;
    message += location_suffix(location);
    message += ` The target's schema declares no field "${location.field}".`;
    super(message);
    this.name = "UnknownAuthoredFieldError";
  }
}

// Class 4: the field resolves, but the authored value is wrong for the declared
// field type. Carries the declared field type so the author can see the mismatch.
export class BadAuthoredValueError extends Error {
  constructor(location: AuthoredValueLocation, declared_type: string, detail: string) {
    let message = `Authored validator value does not match the declared field type`;
    message += location_suffix(location);
    message += ` Declared field type is "${declared_type}".`;
    message += ` ${detail}`;
    super(message);
    this.name = "BadAuthoredValueError";
  }
}

//============================================
// Value-kind checks (mirror runtime-coercion backstop semantics)
//============================================

// A number, or a non-empty numeric string that parses to a finite number, is an
// acceptable authored value for an int/float field. This mirrors the runtime
// numeric-coercion backstop (validators.ts coerce_observed_to_number).
function coerce_finite_numeric(authored_value: string | number | boolean): number | null {
  if (typeof authored_value === "number") {
    return Number.isFinite(authored_value) ? authored_value : null;
  }
  if (typeof authored_value === "string") {
    const trimmed = authored_value.trim();
    if (trimmed.length === 0) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function numeric_constraint_detail(
  result: Extract<StateFieldLookupResult, { kind: "typed" }>,
  authored_value: number,
): string | null {
  const unit = result.unit === undefined ? "" : ` ${result.unit}`;
  if (result.min !== undefined && authored_value < result.min) {
    return `Value ${authored_value}${unit} is below declared minimum ${result.min}${unit}.`;
  }
  if (result.max !== undefined && authored_value > result.max) {
    return `Value ${authored_value}${unit} exceeds declared maximum ${result.max}${unit}.`;
  }
  if (result.step !== undefined && result.min !== undefined) {
    const remainder = (authored_value - result.min) % result.step;
    const aligns =
      Math.abs(remainder) <= 1e-9 || Math.abs(Math.abs(remainder) - result.step) <= 1e-9;
    if (!aligns) {
      return (
        `Value ${authored_value}${unit} does not align to declared step ` +
        `${result.step}${unit} from minimum ${result.min}${unit}.`
      );
    }
  }
  return null;
}

//============================================
// Result-kind dispatch
//============================================

// Check one (target, field, authored_value) against its structured lookup
// result, throwing the appropriate named error on a miss. Returns normally when
// the value is acceptable for the resolved field type. Every miss (unknown
// object, subpart, or field, or a bad value) always errors; there is no
// exemption path.
function check_one_value(result: StateFieldLookupResult, location: AuthoredValueLocation): void {
  switch (result.kind) {
    case "typed": {
      // int/float: a finite number or finite-parseable numeric string.
      if (result.field_type === "int" || result.field_type === "float") {
        const numeric_value = coerce_finite_numeric(location.authored_value);
        if (numeric_value === null) {
          const detail = `Expected a number or a finite numeric string.`;
          throw new BadAuthoredValueError(location, result.field_type, detail);
        }
        const constraint_detail = numeric_constraint_detail(result, numeric_value);
        if (constraint_detail !== null) {
          throw new BadAuthoredValueError(location, result.field_type, constraint_detail);
        }
        return;
      }
      // bool: a real boolean only; the strings "true"/"false" are rejected,
      // mirroring the runtime backstop boolean branch (same-type comparison only).
      if (typeof location.authored_value !== "boolean") {
        const detail = `Expected a real boolean (not the string "true"/"false").`;
        throw new BadAuthoredValueError(location, "bool", detail);
      }
      return;
    }
    case "enum": {
      // A closed-vocabulary string field. The value must be a string, and when a
      // closed member set is declared it must be a member of that set.
      if (typeof location.authored_value !== "string") {
        const detail = `Expected a string.`;
        throw new BadAuthoredValueError(location, "enum", detail);
      }
      if (result.allowed !== null && !result.allowed.includes(location.authored_value)) {
        let detail = `Expected one of the declared enum members:`;
        detail += ` ${result.allowed.map((member) => `"${member}"`).join(", ")}.`;
        throw new BadAuthoredValueError(location, "enum", detail);
      }
      return;
    }
    case "material": {
      // A registry-backed material-identity field. The value must be a string;
      // membership is NOT load-checked here. The load-time pass does not grow
      // StepMachineOptions with a material predicate and adds no registry
      // membership check: no corpus material-value validator exists today, and
      // value-level material checking is deferred. The string requirement
      // is the durable floor; a future pass can add registry membership.
      if (typeof location.authored_value !== "string") {
        const detail = `Expected a material name string.`;
        throw new BadAuthoredValueError(location, "material", detail);
      }
      return;
    }
    case "unknown_field": {
      // A known object/subpart with a bad field name always errors.
      throw new UnknownAuthoredFieldError(location);
    }
    case "unknown_object": {
      // An authored value naming an object with no declared schema always errors.
      throw new UnknownAuthoredObjectError(location);
    }
    case "unknown_subpart": {
      // An authored value naming an undeclared subpart always errors.
      throw new UnknownAuthoredSubpartError(location);
    }
    default: {
      // Compile-time exhaustiveness: every result kind is handled above.
      const exhaustion_check: never = result;
      throw new Error(`Unhandled lookup result kind: ${String(exhaustion_check)}`);
    }
  }
}

//============================================
// Pass entry point
//============================================

// Validate every authored value in the two state-touching validators against the
// declared field type reported by the injected lookup. Throws a named
// author-facing error on the first miss; returns normally when all authored
// values are well-typed. Called inside create_step_machine, beside
// validate_protocol_presets.
export function validate_authored_validator_values(options: AuthoredValueCheckOptions): void {
  const config = options.protocol_config;
  const lookup = options.lookup_state_field;
  const protocol_name = config.protocol_name;

  for (const step of config.steps ?? []) {
    const step_name = step.step_name;

    // target_with_value interactions: object = interaction.target, the flat
    // {field: value} map = interaction.validator.value.
    for (const interaction of step.sequence) {
      if (interaction.validator.preset !== "target_with_value") {
        continue;
      }
      const value_map = interaction.validator.value;
      if (value_map === undefined) {
        continue;
      }
      const target = interaction.target;
      for (const [field, authored_value] of Object.entries(value_map)) {
        const result = lookup(target, field);
        const location: AuthoredValueLocation = {
          protocol_name,
          step_name,
          validator_kind: "target_with_value",
          target,
          field,
          authored_value,
        };
        check_one_value(result, location);
      }
    }

    // final_state_matches step validator: object = step.step_validator.target,
    // the flat {field: value} map = step.step_validator.contains. Read these
    // authored fields directly, NOT .value/parameters (broken for this preset).
    if (step.step_validator.preset !== "final_state_matches") {
      continue;
    }
    const step_target = step.step_validator.target;
    const contains_map = step.step_validator.contains;
    if (step_target === undefined || contains_map === undefined) {
      continue;
    }
    for (const [field, authored_value] of Object.entries(contains_map)) {
      const result = lookup(step_target, field);
      const location: AuthoredValueLocation = {
        protocol_name,
        step_name,
        validator_kind: "final_state_matches",
        target: step_target,
        field,
        authored_value,
      };
      check_one_value(result, location);
    }
  }
}
