// Unit tests for src/scene_runtime/layout/geometry. Pure deterministic
// collision geometry per the ratified contract:
//   docs/archive/decisions/layout_model_layer_synthesis.md
// Uses the tsx loader so we import the TS source directly. Run via:
//   node --import tsx --test tests/test_layout_geometry.mjs

import test from "node:test";
import assert from "node:assert/strict";

import {
  aabbFromBounds,
  detectCollision,
  buildResolutionCandidate,
  sortResolutionOrder,
} from "../src/scene_runtime/layout/geometry/collision.ts";

//============================================
// Helpers
//============================================

// Apply a separation vector to an Aabb, returning a shifted copy.
function shift(box, vec) {
  return { x: box.x + vec.x, y: box.y + vec.y, w: box.w, h: box.h };
}

// True when two boxes overlap on BOTH axes with strictly positive overlap.
// Mirrors the detector's collide rule so we can confirm separation clears it.
function boxesOverlap(a, b) {
  const xOverlap = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const yOverlap = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return xOverlap > 0 && yOverlap > 0;
}

const EPS = 1e-9;

//============================================
// aabbFromBounds adapter
//============================================

test("aabbFromBounds maps edge form to top-left plus size", () => {
  const aabb = aabbFromBounds({ left: 10, right: 30, top: 5, bottom: 25 });
  assert.deepEqual(aabb, { x: 10, y: 5, w: 20, h: 20 });
});

//============================================
// Separated and touching: no collision
//============================================

test("fully separated boxes report no collision", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 50, y: 50, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

test("touching edge on x (overlap === 0) is separated", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 10, y: 0, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

test("touching edge on y (overlap === 0) is separated", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 0, y: 10, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

test("overlap on only one axis is separated", () => {
  // x ranges overlap, y ranges do not.
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 5, y: 20, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

//============================================
// Partial overlap: axis selection, depth, sign
//============================================

test("partial overlap picks smaller-overlap axis and positive depth", () => {
  // a and b overlap; x-overlap = 4, y-overlap = 8 -> overlapAxis x.
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.notEqual(c, null);
  assert.equal(c.overlapAxis, "x");
  assert.ok(Math.abs(c.overlapDepth - 4) < EPS);
  assert.ok(c.overlapDepth > 0);
});

test("separationForA moves A away from B; magnitude equals overlapDepth", () => {
  // B is to the right of A on x, so A must move in -x to clear.
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.equal(c.overlapAxis, "x");
  assert.ok(c.separationForA.x < 0, "A moves in -x away from B");
  assert.equal(c.separationForA.y, 0);
  const mag = Math.hypot(c.separationForA.x, c.separationForA.y);
  assert.ok(Math.abs(mag - c.overlapDepth) < EPS);
});

test("separationForB is the exact negation of separationForA", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.equal(c.separationForB.x, -c.separationForA.x);
  assert.equal(c.separationForB.y, -c.separationForA.y);
});

test("sign direction flips when B sits left of A", () => {
  // Same shape, but B to the LEFT of A: A must move +x to clear.
  const a = { x: 6, y: 2, w: 10, h: 10 };
  const b = { x: 0, y: 0, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.equal(c.overlapAxis, "x");
  assert.ok(c.separationForA.x > 0, "A moves in +x away from B on the left");
});

//============================================
// Applying separation actually clears the overlap (both vectors)
//============================================

test("applying separationForA to A clears the overlap", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.ok(boxesOverlap(a, b), "precondition: boxes overlap");
  const movedA = shift(a, c.separationForA);
  assert.ok(!boxesOverlap(movedA, b), "moved A no longer overlaps B");
});

test("applying separationForB to B clears the overlap", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  const movedB = shift(b, c.separationForB);
  assert.ok(!boxesOverlap(a, movedB), "moved B no longer overlaps A");
});

test("separation clears overlap when y is the chosen axis", () => {
  // y-overlap smaller than x-overlap -> overlapAxis y.
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 2, y: 6, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.equal(c.overlapAxis, "y");
  const movedA = shift(a, c.separationForA);
  assert.ok(!boxesOverlap(movedA, b));
  const movedB = shift(b, c.separationForB);
  assert.ok(!boxesOverlap(a, movedB));
});

//============================================
// Containment
//============================================

test("containment sets aInB / bInA correctly", () => {
  // small fully inside big. A = small, B = big.
  const small = { x: 4, y: 4, w: 2, h: 2 };
  const big = { x: 0, y: 0, w: 20, h: 20 };
  const c = detectCollision(small, "small", big, "big");
  assert.notEqual(c, null);
  assert.equal(c.aInB, true, "small is inside big");
  assert.equal(c.bInA, false, "big is not inside small");
});

test("containment reports interval-overlap depth and a valid axis sign", () => {
  // For a fully contained box, the ratified overlapDepth is the interval
  // overlap (the contained box's full extent on the chosen axis), NOT the
  // larger minimum-translation distance that would push it out a side. So a
  // single separation step is not promised to clear containment; we assert the
  // documented facts instead: positive depth, on-axis vector, exact negation.
  const small = { x: 4, y: 4, w: 2, h: 2 };
  const big = { x: 0, y: 0, w: 20, h: 20 };
  const c = detectCollision(small, "small", big, "big");
  assert.ok(c.overlapDepth > 0);
  assert.ok(Math.abs(c.overlapDepth - 2) < EPS, "depth is interval overlap");
  const onAxis = c.overlapAxis === "x" ? c.separationForA.x : c.separationForA.y;
  const offAxis = c.overlapAxis === "x" ? c.separationForA.y : c.separationForA.x;
  assert.ok(Math.abs(Math.abs(onAxis) - c.overlapDepth) < EPS);
  assert.equal(offAxis, 0);
  assert.equal(c.separationForB.x, -c.separationForA.x);
  assert.equal(c.separationForB.y, -c.separationForA.y);
});

//============================================
// Equal overlap on both axes: tie-break x first
//============================================

test("equal x and y overlap tie-breaks to x axis", () => {
  // Square overlap: x-overlap === y-overlap === 5.
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 5, y: 5, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  assert.equal(c.overlapAxis, "x");
  assert.ok(Math.abs(c.overlapDepth - 5) < EPS);
  // separation still clears.
  const movedA = shift(a, c.separationForA);
  assert.ok(!boxesOverlap(movedA, b));
});

//============================================
// Zero width / height
//============================================

test("zero-width box never collides", () => {
  const a = { x: 5, y: 0, w: 0, h: 10 };
  const b = { x: 0, y: 0, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

test("zero-height box never collides", () => {
  const a = { x: 0, y: 5, w: 10, h: 0 };
  const b = { x: 0, y: 0, w: 10, h: 10 };
  assert.equal(detectCollision(a, "a", b, "b"), null);
});

//============================================
// ResolutionCandidate builder
//============================================

test("buildResolutionCandidate carries axis, magnitude, direction, altAxis", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 2, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  const cand = buildResolutionCandidate(c);
  assert.equal(cand.suggestedAxis, "x");
  assert.ok(Math.abs(cand.magnitude - c.overlapDepth) < EPS);
  assert.equal(cand.direction, -1, "A moves in -x");
  assert.equal(cand.altAxis, "y");
  assert.equal(cand.collision, c);
});

test("candidate direction is +1 when separation is positive", () => {
  const a = { x: 6, y: 2, w: 10, h: 10 };
  const b = { x: 0, y: 0, w: 10, h: 10 };
  const c = detectCollision(a, "a", b, "b");
  const cand = buildResolutionCandidate(c);
  assert.equal(cand.direction, 1);
});

//============================================
// Stable resolution order
//============================================

test("sortResolutionOrder sorts by depth desc then lexicographic ids", () => {
  function candFor(idA, idB, ax, bx) {
    const a = { x: ax, y: 0, w: 10, h: 10 };
    const b = { x: bx, y: 0, w: 10, h: 10 };
    // make both fully overlap on y so they collide.
    const col = detectCollision(a, idA, b, idB);
    return buildResolutionCandidate(col);
  }
  // depth 4 (overlap x = 4), depth 8 (overlap x = 8), depth 4 again.
  const c1 = candFor("a", "z", 0, 6); // depth 4
  const c2 = candFor("m", "n", 0, 2); // depth 8
  const c3 = candFor("a", "b", 0, 6); // depth 4
  const sorted = sortResolutionOrder([c1, c2, c3]);
  // deepest first
  assert.equal(sorted[0], c2);
  // then the two depth-4 by (boxIdA, boxIdB) lexicographic: a/b before a/z
  assert.equal(sorted[1], c3);
  assert.equal(sorted[2], c1);
});

test("sortResolutionOrder does not mutate the input array", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  const b = { x: 6, y: 0, w: 10, h: 10 };
  const cand = buildResolutionCandidate(detectCollision(a, "a", b, "b"));
  const input = [cand];
  const out = sortResolutionOrder(input);
  assert.notEqual(out, input);
  assert.equal(input.length, 1);
});
