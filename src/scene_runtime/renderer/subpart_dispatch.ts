// Pure declaration dispatch for structured-subpart material overlays.

import type { ObjectDef, VisualStateDef } from "../layout/types.js";

export interface SubpartAmountContract {
  field_name: string;
  capacity: number | null;
  capacity_error: string;
}

export interface SubpartMaterialContract {
  identity_field_name: string;
  amount: SubpartAmountContract | null;
}

function is_subpart_target(vs: VisualStateDef, effect: "material_tint" | "fill_height"): boolean {
  return (
    vs.applies_to === "subpart" && vs.render_effect === effect && vs.target === "subpart_geometry"
  );
}

function amount_contract(field_name: string, vs: VisualStateDef): SubpartAmountContract {
  const capacity_fields = [vs.capacity_ul, vs.capacity_ml, vs.capacity_mg].filter(
    (capacity): capacity is number => capacity !== undefined,
  );
  if (capacity_fields.length !== 1) {
    return {
      field_name,
      capacity: null,
      capacity_error:
        `fill_height '${field_name}' needs exactly one positive ` +
        "capacity_ul/capacity_ml/capacity_mg",
    };
  }
  const capacity = capacity_fields[0];
  if (typeof capacity !== "number" || !Number.isFinite(capacity) || capacity <= 0) {
    return {
      field_name,
      capacity: null,
      capacity_error:
        `fill_height '${field_name}' needs exactly one positive ` +
        "capacity_ul/capacity_ml/capacity_mg",
    };
  }
  return { field_name, capacity, capacity_error: "" };
}

// Return the declaration-owned material contract. Identity-only declarations
// remain valid; a compatible amount declaration augments the same overlay.
export function find_subpart_material_contract(def: ObjectDef): SubpartMaterialContract | null {
  if (def.subpart_geometry === undefined || def.view_box === undefined) {
    return null;
  }
  let identity_field_name: string | null = null;
  let amount: SubpartAmountContract | null = null;
  for (const field_name of Object.keys(def.visual_states)) {
    const vs = def.visual_states[field_name];
    if (vs === undefined) {
      continue;
    }
    if (is_subpart_target(vs, "material_tint") && identity_field_name === null) {
      identity_field_name = field_name;
    }
    if (is_subpart_target(vs, "fill_height") && amount === null) {
      amount = amount_contract(field_name, vs);
    }
  }
  if (identity_field_name === null) {
    return null;
  }
  return { identity_field_name, amount };
}

// Compatibility export for existing identity-only callers and focused tests.
export interface SubpartTintContract {
  field_name: string;
}

export function find_material_tint_subpart_field(def: ObjectDef): SubpartTintContract | null {
  const contract = find_subpart_material_contract(def);
  if (contract === null) {
    return null;
  }
  return { field_name: contract.identity_field_name };
}
