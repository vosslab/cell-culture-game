// Pure per-subpart material state resolution and bottom-anchored geometry.

import type { SubpartGeometry } from "../layout/types.js";
import type { MaterialRegistry } from "./visual_state_resolver.js";
import { resolve_color_result } from "./material_color.js";

export interface SubpartMaterialState {
  fill: string;
  material_name: string;
  fill_percent: number;
  degraded: string;
}

export function resolve_subpart_material_state(
  raw_identity: string | number | boolean | undefined,
  raw_amount: string | number | boolean | undefined,
  capacity: number | null,
  capacity_error: string,
  registry: MaterialRegistry | null,
): SubpartMaterialState {
  const material_name = typeof raw_identity === "string" ? raw_identity : null;
  if (capacity !== null || capacity_error !== "") {
    if (capacity_error !== "") {
      return {
        fill: "transparent",
        material_name: material_name ?? "",
        fill_percent: 0,
        degraded: capacity_error,
      };
    }
    if (material_name === null) {
      return {
        fill: "transparent",
        material_name: "",
        fill_percent: 0,
        degraded: "material identity is missing or not a string",
      };
    }
    if (typeof raw_amount !== "number" || !Number.isFinite(raw_amount)) {
      return {
        fill: "transparent",
        material_name: material_name ?? "",
        fill_percent: 0,
        degraded: "fill_height amount is missing or not numeric",
      };
    }
    if (raw_amount < 0) {
      return {
        fill: "transparent",
        material_name,
        fill_percent: 0,
        degraded: "fill_height amount is negative",
      };
    }
    if (material_name === "empty" && raw_amount === 0) {
      return { fill: "transparent", material_name, fill_percent: 0, degraded: "" };
    }
    if (material_name === "empty" && raw_amount > 0) {
      return {
        fill: "transparent",
        material_name,
        fill_percent: 0,
        degraded: "empty material has positive amount",
      };
    }
    if (material_name !== "empty" && raw_amount === 0) {
      return {
        fill: "transparent",
        material_name: material_name ?? "",
        fill_percent: 0,
        degraded: "non-empty material has zero amount",
      };
    }
  }
  const color = resolve_color_result(material_name, registry);
  if (!color.ok) {
    return {
      fill: "transparent",
      material_name: material_name ?? "",
      fill_percent: 0,
      degraded: color.reason,
    };
  }
  const amount_value = typeof raw_amount === "number" ? raw_amount : 0;
  const fill_percent =
    capacity === null ? 100 : Math.max(0, Math.min(100, (amount_value / capacity) * 100));
  return {
    fill: color.color ?? "transparent",
    material_name: material_name ?? "",
    fill_percent,
    degraded: "",
  };
}

// Circular segment from the bottom of a circle. This is self-contained SVG
// geometry: no clip path, DOM id, or base-SVG lookup is required.
export function circle_fill_path(
  geometry: Extract<SubpartGeometry, { shape: "circle" }>,
  fill_percent: number,
): string {
  const fraction = Math.max(0, Math.min(100, fill_percent)) / 100;
  if (fraction <= 0) return "";
  if (fraction >= 1) {
    const left = geometry.cx - geometry.r;
    const diameter = geometry.r * 2;
    return (
      `M ${left} ${geometry.cy} a ${geometry.r} ${geometry.r} 0 1 0 ${diameter} 0 ` +
      `a ${geometry.r} ${geometry.r} 0 1 0 ${-diameter} 0`
    );
  }
  const y = geometry.cy + geometry.r - fraction * geometry.r * 2;
  const dy = y - geometry.cy;
  const dx = Math.sqrt(Math.max(0, geometry.r * geometry.r - dy * dy));
  const left = geometry.cx - dx;
  const right = geometry.cx + dx;
  const large = fraction > 0.5 ? 1 : 0;
  // SVG coordinates increase downward. A sweep of zero travels from the left
  // chord endpoint through the lower circle boundary, enclosing the fill below
  // the chord rather than its upper complement.
  return `M ${left} ${y} A ${geometry.r} ${geometry.r} 0 ${large} 0 ${right} ${y} ` + "Z";
}
