// Runtime writer for compiled material SVGs. The injection layer owns every
// concrete SVG reference; this module receives only opaque operations and
// resolved material effects, then applies the gravity-part contract without
// creating, removing, or reordering SVG nodes: bottom stays fixed, body scales
// vertically about its lower anchor, and surface translates without deforming.

import type { AnchorMaterialEffect } from "./visual_state_resolver.js";
import { resolveInjectedLiquidRegion, type InjectedLiquidRegion } from "./inject_svg.js";
import { derive_oklch_shade } from "./oklch_shade.js";

function shared_effect(effects: readonly AnchorMaterialEffect[]): AnchorMaterialEffect {
  const first = effects[0];
  if (first === undefined) {
    throw new Error("liquid paint: no material effect supplied");
  }
  if (first.render_effect !== "fill_height" || first.target !== "anchor_liquid_bounds") {
    throw new Error(`liquid paint: '${first.field_name}' is not a vessel fill-height effect`);
  }
  if (first.clip !== "anchor_liquid_clip") {
    throw new Error(`liquid paint: '${first.field_name}' requires anchor_liquid_clip`);
  }
  for (const effect of effects.slice(1)) {
    if (
      effect.material_name !== first.material_name ||
      effect.color !== first.color ||
      effect.fill_percent !== first.fill_percent
    ) {
      throw new Error("liquid paint: one compiled liquid region cannot carry conflicting effects");
    }
  }
  return first;
}

function surface_y_for_fill_percent(region: InjectedLiquidRegion, fill_percent: number): number {
  const bounds_bottom = region.bounds.y + region.bounds.height;
  const body_start_fill_percent = region.bodyStartFillPercent;

  const fill_height_exponent = region.fillHeightExponent;
  if (fill_height_exponent !== null) {
    const normalized_fill = Math.max(0, Math.min(1, fill_percent / (region.maxFillPercent ?? 100)));
    return bounds_bottom - region.bounds.height * normalized_fill ** fill_height_exponent;
  }
  if (body_start_fill_percent === null) {
    const fraction = fill_percent / 100;
    return region.bounds.y + region.bounds.height * (1 - fraction);
  }
  if (region.bodyAnchorY === null) {
    throw new Error("liquid paint: body-start fill calibration requires a body anchor");
  }
  if (fill_percent <= body_start_fill_percent) {
    const cone_fraction = fill_percent / body_start_fill_percent;
    return bounds_bottom - (bounds_bottom - region.bodyAnchorY) * cone_fraction;
  }
  const body_fraction = (fill_percent - body_start_fill_percent) / (100 - body_start_fill_percent);
  return region.bodyAnchorY - (region.bodyAnchorY - region.bounds.y) * body_fraction;
}

// A conical form already declares the volume fraction at which it reaches its
// cylindrical body. Below that point the fixed authored meniscus must narrow
// with the cone. Above it, the vessel has reached its full body width.
function surface_scale_for_fill_percent(
  region: InjectedLiquidRegion,
  fill_percent: number,
): number {
  const body_start_fill_percent = region.bodyStartFillPercent;
  if (body_start_fill_percent === null || fill_percent >= body_start_fill_percent) {
    return 1;
  }
  return Math.max(0, fill_percent / body_start_fill_percent);
}

// The surface calculation combines authored decimal geometry with a fill
// fraction.  A mathematically exact endpoint can therefore land a few ULPs
// beyond the reveal rectangle.  Snap only that representational roundoff;
// a materially out-of-range request remains an error rather than being hidden.
const FLOAT64_SIGN_BIT = 0x8000_0000_0000_0000n;
const FLOAT64_MAGNITUDE_MASK = 0x7fff_ffff_ffff_ffffn;
const float64_bits_buffer = new ArrayBuffer(Float64Array.BYTES_PER_ELEMENT);
const float64_bits_view = new DataView(float64_bits_buffer);

// Map finite IEEE-754 values to monotonically increasing integer positions.
// Both signed zeroes deliberately share one position, while subnormal steps
// and each step away from either endpoint remain individually countable.
function ordered_float64_position(value: number): bigint {
  float64_bits_view.setFloat64(0, value, false);
  const bits = float64_bits_view.getBigUint64(0, false);
  const magnitude = bits & FLOAT64_MAGNITUDE_MASK;
  return (bits & FLOAT64_SIGN_BIT) === 0n
    ? FLOAT64_SIGN_BIT + magnitude
    : FLOAT64_SIGN_BIT - magnitude;
}

function ulp_distance(first: number, second: number): bigint {
  const first_position = ordered_float64_position(first);
  const second_position = ordered_float64_position(second);
  return first_position >= second_position
    ? first_position - second_position
    : second_position - first_position;
}

const ENDPOINT_ROUNDOFF_ULPS = 32n;

export function stabilize_liquid_reveal_top(
  bounds_y: number,
  bounds_height: number,
  requested_y: number,
): number {
  if (
    !Number.isFinite(bounds_y) ||
    !Number.isFinite(bounds_height) ||
    !Number.isFinite(requested_y)
  ) {
    throw new Error("liquid paint: reveal geometry must be finite with non-negative height");
  }
  const bounds_bottom = bounds_y + bounds_height;
  if (!Number.isFinite(bounds_bottom) || bounds_height < 0) {
    throw new Error("liquid paint: reveal geometry must be finite with non-negative height");
  }
  if (requested_y < bounds_y) {
    if (ulp_distance(bounds_y, requested_y) <= ENDPOINT_ROUNDOFF_ULPS) {
      return bounds_y;
    }
    throw new Error("liquid paint: reveal top must remain inside bounds");
  }
  if (requested_y > bounds_bottom) {
    if (ulp_distance(bounds_bottom, requested_y) <= ENDPOINT_ROUNDOFF_ULPS) {
      return bounds_bottom;
    }
    throw new Error("liquid paint: reveal top must remain inside bounds");
  }
  return requested_y;
}

// Returns false only for an ordinary SVG. Callers may accept that result when
// no material effect is authored; an effect on an ordinary SVG is invalid.
// A compiled SVG is fully owned here even when its effect list is empty.
export function render_liquid_material_effects(
  host: HTMLElement,
  effects: readonly AnchorMaterialEffect[],
): boolean {
  const region = resolveInjectedLiquidRegion(host);
  if (region === null) {
    return false;
  }
  // Fail closed: any later validation or shade error leaves the compiled
  // liquid hidden, never showing a stale material from the prior state.
  region.setVisible(false);
  delete host.dataset.liquidMaterialField;
  delete host.dataset.liquidMaterialName;
  delete host.dataset.liquidFillPercent;
  delete host.dataset.liquidColor;
  if (effects.length === 0) {
    return true;
  }
  const effect = shared_effect(effects);
  host.dataset.liquidMaterialField = effect.field_name;
  host.dataset.liquidMaterialName = effect.material_name;
  if (
    !Number.isFinite(effect.fill_percent) ||
    effect.fill_percent < 0 ||
    effect.fill_percent > 100
  ) {
    throw new Error(`liquid paint: '${effect.field_name}' fill percent must be in [0, 100]`);
  }
  const upperBoundedPercent = Math.min(effect.fill_percent, region.maxFillPercent ?? 100);
  const fillPercent =
    upperBoundedPercent === 0 ? 0 : Math.max(upperBoundedPercent, region.minFillPercent ?? 0);
  host.dataset.liquidFillPercent = String(fillPercent);
  host.dataset.liquidColor = effect.color ?? "transparent";
  const surfaceY = surface_y_for_fill_percent(region, fillPercent);
  const revealTop = stabilize_liquid_reveal_top(region.bounds.y, region.bounds.height, surfaceY);
  const surfaceScale = surface_scale_for_fill_percent(region, fillPercent);
  region.setRevealTop(revealTop);
  if (
    region.bodyAnchorY === null ||
    region.bodyJoinY === null ||
    region.surfaceReferenceY === null
  ) {
    region.setBodyScale(0);
  } else {
    const referenceHeight = region.bodyAnchorY - region.bodyJoinY;
    // The surface reading and the body join are separate authored geometry
    // datums.  The body ends at its scaled join line, which is the oval's
    // tangent line for a full-width meniscus, rather than at its lower edge.
    const bodyJoinY = surfaceY + (region.bodyJoinY - region.surfaceReferenceY) * surfaceScale;
    const requestedHeight = Math.max(0, region.bodyAnchorY - bodyJoinY);
    region.setBodyScale(requestedHeight / referenceHeight);
  }
  region.setSurfaceTransform(
    region.surfaceReferenceY === null ? 0 : surfaceY - region.surfaceReferenceY,
    surfaceScale,
  );
  if (effect.color === null || fillPercent <= 0) {
    return true;
  }
  for (const paint of region.paints) {
    const color = derive_oklch_shade(effect.color, paint.paint_role, paint.adjustment);
    region.setPaint(paint.paint_handle, color);
  }
  region.setVisible(true);
  return true;
}
