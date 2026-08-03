// Pure deterministic collision geometry for the layout engine. Ratified
// contract: docs/archive/decisions/layout_model_layer_synthesis.md
// ("Geometry and collision response").
//
// Geometry computes collision facts and proposes corrections; it never mutates
// positions. Only layout phases apply corrections. No Solid or DOM imports.

import type { Bounds } from "../types.js";
import type { Aabb, Collision, ResolutionCandidate } from "./types.js";

//============================================
// Adapter: lift an edge-form Bounds into geometry's top-left-plus-size Aabb.
//============================================

// One-line adapter so phases can lift a zone or placement box into geometry
// space without duplicating math. Edge form { left, right, top, bottom } maps to
// top-left origin (left, top) plus size (right - left, bottom - top).
export function aabbFromBounds(b: Bounds): Aabb {
  const aabb: Aabb = {
    x: b.left,
    y: b.top,
    w: b.right - b.left,
    h: b.bottom - b.top,
  };
  return aabb;
}

//============================================
// Interval overlap helper (one axis).
//============================================

// Overlap of two 1-D intervals [aMin, aMax] and [bMin, bMax]. Returns the
// signed overlap length: positive when the intervals truly overlap, zero when
// they only touch, negative when separated. Callers treat <= 0 as separated.
function intervalOverlap(aMin: number, aMax: number, bMin: number, bMax: number): number {
  // The overlap region is [max(aMin, bMin), min(aMax, bMax)]; its length is the
  // overlap. min(aMax, bMax) - max(aMin, bMin) is positive only on true overlap.
  const overlap = Math.min(aMax, bMax) - Math.max(aMin, bMin);
  return overlap;
}

//============================================
// Containment helper (one axis).
//============================================

// True when interval A [aMin, aMax] sits fully inside interval B on this axis.
// Mirrors SAT.js Response.aInB semantics: A is inside B unless an edge of A
// falls outside B.
function intervalAInsideB(aMin: number, aMax: number, bMin: number, bMax: number): boolean {
  const inside = aMin >= bMin && aMax <= bMax;
  return inside;
}

//============================================
// Collision detection for one ordered pair (A, B).
//============================================

// Detect whether boxes a and b collide. Returns an immutable Collision fact, or
// null when the boxes are separated or merely touching.
//
// Rules (positive form, from the memo):
// - Compute x-overlap and y-overlap as interval overlaps. Boxes collide only
//   when BOTH overlaps are strictly positive; treat touching edges
//   (overlap === 0) as separated.
// - overlapAxis is the axis of smaller positive overlap; tie-break x first when
//   x-overlap === y-overlap.
// - separationForA lies on overlapAxis with the sign that moves A clear of B
//   (the side A's center sits on relative to B's center); magnitude ===
//   overlapDepth. separationForB is its exact negation.
// - aInB / bInA: true unless one box's edge falls outside the other on the
//   tested axis (containment on both axes).
export function detectCollision(
  a: Aabb,
  boxIdA: string,
  b: Aabb,
  boxIdB: string,
): Collision | null {
  // Edge coordinates for each box on each axis.
  const aLeft = a.x;
  const aRight = a.x + a.w;
  const aTop = a.y;
  const aBottom = a.y + a.h;
  const bLeft = b.x;
  const bRight = b.x + b.w;
  const bTop = b.y;
  const bBottom = b.y + b.h;

  // Interval overlaps per axis.
  const xOverlap = intervalOverlap(aLeft, aRight, bLeft, bRight);
  const yOverlap = intervalOverlap(aTop, aBottom, bTop, bBottom);

  // Collide only when both overlaps are strictly positive. Touching edges
  // (overlap === 0) and any negative gap count as separated.
  if (xOverlap <= 0 || yOverlap <= 0) {
    return null;
  }

  // Centers, used for the separation sign and the A-toward-B reference vector.
  const aCenterX = a.x + a.w / 2;
  const aCenterY = a.y + a.h / 2;
  const bCenterX = b.x + b.w / 2;
  const bCenterY = b.y + b.h / 2;
  const overlapVectorAtoB = {
    x: bCenterX - aCenterX,
    y: bCenterY - aCenterY,
  };

  // overlapAxis is the axis of smaller positive overlap; tie-break x first.
  const overlapAxis: "x" | "y" = xOverlap <= yOverlap ? "x" : "y";
  const overlapDepth = overlapAxis === "x" ? xOverlap : yOverlap;

  // separationForA moves A AWAY from B along overlapAxis: opposite the sign of
  // the A-toward-B vector on that axis. When centers coincide on the axis
  // (delta === 0) default to the negative direction so the result stays
  // deterministic.
  const axisDelta = overlapAxis === "x" ? overlapVectorAtoB.x : overlapVectorAtoB.y;
  const awaySign = axisDelta > 0 ? -1 : 1;
  const separationForA =
    overlapAxis === "x"
      ? { x: awaySign * overlapDepth, y: 0 }
      : { x: 0, y: awaySign * overlapDepth };
  const separationForB = {
    x: -separationForA.x,
    y: -separationForA.y,
  };

  // Containment: A inside B (and B inside A) requires containment on both axes.
  const aInB =
    intervalAInsideB(aLeft, aRight, bLeft, bRight) &&
    intervalAInsideB(aTop, aBottom, bTop, bBottom);
  const bInA =
    intervalAInsideB(bLeft, bRight, aLeft, aRight) &&
    intervalAInsideB(bTop, bBottom, aTop, aBottom);

  const collision: Collision = {
    boxIdA,
    boxIdB,
    overlapAxis,
    overlapDepth,
    overlapVectorAtoB,
    separationForA,
    separationForB,
    aInB,
    bInA,
  };
  return collision;
}

//============================================
// Resolution candidate builder.
//============================================

// Build the correction a layout phase may choose from. suggestedAxis is the
// cheaper (minimum-depth) overlapAxis already chosen during detection; magnitude
// is the penetration depth; direction is the unit sign of separationForA on the
// suggested axis. altAxis names the other axis for phases that prefer a row drop
// over a nudge.
export function buildResolutionCandidate(collision: Collision): ResolutionCandidate {
  const suggestedAxis = collision.overlapAxis;
  // direction is the unit sign of A's separation on the suggested axis.
  const axisValue = suggestedAxis === "x" ? collision.separationForA.x : collision.separationForA.y;
  const direction: -1 | 1 = axisValue >= 0 ? 1 : -1;
  const altAxis: "x" | "y" = suggestedAxis === "x" ? "y" : "x";

  const candidate: ResolutionCandidate = {
    collision,
    suggestedAxis,
    magnitude: collision.overlapDepth,
    direction,
    altAxis,
  };
  return candidate;
}

//============================================
// Stable resolution order.
//============================================

// Sort candidates by overlapDepth descending, tie-break by (boxIdA, boxIdB)
// lexicographically, so output is stable across builds. Returns a new array;
// the input is not mutated.
export function sortResolutionOrder(
  candidates: readonly ResolutionCandidate[],
): ResolutionCandidate[] {
  const sorted = candidates.slice();
  sorted.sort(compareCandidates);
  return sorted;
}

// Comparator: deeper penetration first; then lexicographic by boxIdA, boxIdB.
function compareCandidates(a: ResolutionCandidate, b: ResolutionCandidate): number {
  const depthDiff = b.collision.overlapDepth - a.collision.overlapDepth;
  if (depthDiff !== 0) {
    return depthDiff;
  }
  if (a.collision.boxIdA !== b.collision.boxIdA) {
    return a.collision.boxIdA < b.collision.boxIdA ? -1 : 1;
  }
  if (a.collision.boxIdB !== b.collision.boxIdB) {
    return a.collision.boxIdB < b.collision.boxIdB ? -1 : 1;
  }
  return 0;
}
