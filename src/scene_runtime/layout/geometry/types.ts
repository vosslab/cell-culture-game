// Pure geometry value types for the layout engine. Ratified contract:
// docs/archive/decisions/layout_model_layer_synthesis.md
// ("Geometry and collision response"). All coordinates are scene-percent
// (0..100 of the canonical 16:9 frame per axis). These types are immutable and
// carry no Solid or DOM dependency.

// Immutable 2D vector in scene-percent.
export interface Vector {
  readonly x: number;
  readonly y: number;
}

// Axis-aligned box, top-left origin plus size, scene-percent. Distinct from the
// edge-form Bounds { left, right, top, bottom } in ../types.ts; the two serve
// different layers (edge type for zones/renderer vs geometry value type).
export interface Aabb {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

// An immutable computed fact about one overlapping pair. Returned whole (not a
// bare vector) so a diagnostic can name both boxes and a separating vector
// without a second lookup.
export interface Collision {
  readonly boxIdA: string;
  readonly boxIdB: string;
  // The axis of minimum penetration; the cheaper axis to separate on.
  readonly overlapAxis: "x" | "y";
  // Penetration depth on overlapAxis, always positive.
  readonly overlapDepth: number;
  // Points from A's center toward B's center. Sign reference for the pair.
  readonly overlapVectorAtoB: Vector;
  // Moves A fully clear of B along overlapAxis. Magnitude === overlapDepth.
  readonly separationForA: Vector;
  // The exact negation of separationForA; moves B fully clear of A.
  readonly separationForB: Vector;
  // True when A is entirely inside B (and vice versa for bInA).
  readonly aInB: boolean;
  readonly bInA: boolean;
}

// A correction a layout phase may choose from. suggestedAxis is the cheaper
// (minimum-depth) axis; altAxis is the other axis when a phase prefers a row
// drop over a nudge. direction is the unit sign on suggestedAxis.
export interface ResolutionCandidate {
  readonly collision: Collision;
  readonly suggestedAxis: "x" | "y";
  readonly magnitude: number;
  readonly direction: -1 | 1;
  readonly altAxis?: "x" | "y";
}
