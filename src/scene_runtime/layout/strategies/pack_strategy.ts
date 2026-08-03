// Overflow packer strategy: non-uniform, priority-based shrink plus gap compaction.
//
// Ratified contract:
//   docs/archive/decisions/layout_model_layer_synthesis.md
//   ("Packer objective and trigger").
//
// The packer is engaged by the horizontal dispatcher only for a zone whose row
// layout would require unacceptable shrink (below config.packer.thresholdScale)
// or overflows (negative gap / out of bounds). It resolves the zone by applying
// NON-UNIFORM, priority-based shrink plus gap compaction, where the row
// strategy's uniform shrink bottoms out at MIN_SCALE and emits an overflow
// diagnostic. The packer preserves the primary teaching object's scale: it
// shrinks lower-priority fillers first and only touches the primary as a last
// resort.
//
// It is single-row, order-preserving, and deterministic. The horizontal stage
// owns _centerX only; the vertical stage recomputes _baselineY from the zone baseline, so the
// packer never stacks rows by mutating _baselineY (that would be wiped by vertical). The
// "rows" in the elkjs rectpacking vocabulary collapse to one row here; the
// packer's compaction phase is the part that does the real work.
//
// Four reduced phases (the elkjs rectpacking shape):
//   1. width approximation  - measure available width and the scale-1 footprint
//   2. row placement        - lay items left-to-right (or by tab buckets)
//   3. compaction           - only on overflow: tighten gap, then priority-shrink
//   4. whitespace expansion  - redistribute any leftover slack as gap
//
// Lexicographic cost minimized (strict priority order), subject to the hard
// constraints scale >= MIN_SCALE, in-bounds, and preserved input order:
//   [ primaryWeightedShrinkPct, orderViolations, gapDeficit, overhang ]
// Primary-weighted shrink is first, so the packer preserves the primary object's
// scale before maximizing area.

import { MAX_FOOTPRINT_RATIO } from "../constants.js";
import { footprintFor, visualWidthFor } from "../footprint.js";
import { buildActionablePayload, buildDiagnostic } from "../diagnostics/index.js";
import type { ComputedItem, Kind, ScaledPlacement, Zone } from "../types.js";
import type { PlacementStrategy, StrategyContext } from "./placement_strategy.js";

//============================================
// Shrink priority (derived, never authored)
//============================================

// Semantic-kind priority tiers. Higher tier = more protected (shrink last). The
// primary teaching object is the highest-tier, largest-footprint item; fillers
// and decorations are the lowest tier and shrink first. This is derived purely
// from the object's declared kind, never from an authored YAML field.
const KIND_PRIORITY: Readonly<Record<Kind, number>> = {
  decoration: 0,
  waste: 1,
  pipette: 2,
  bottle: 2,
  flask: 2,
  rack: 2,
  plate: 3,
  equipment: 3,
};

// The protection priority of one item. Unknown kinds (bound placeholders) rank
// as mid-tier fillers so a missing object never out-protects a real instrument.
function kindPriority(it: ScaledPlacement): number {
  const k = it.kind;
  if (k === "unknown") return 2;
  return KIND_PRIORITY[k];
}

// Rank items by SHRINK order: the item shrunk first comes first. Lower kind
// priority shrinks first; among equal priority the larger footprint shrinks
// first (it has the most slack to give); placement_name is the final, stable
// tiebreak. This never reorders the placed row, it only chooses what to shrink.
function shrinkOrder(items: ScaledPlacement[]): ScaledPlacement[] {
  const indexed = items.map((it, i) => ({ it, i }));
  indexed.sort((a, b) => {
    const pa = kindPriority(a.it);
    const pb = kindPriority(b.it);
    if (pa !== pb) return pa - pb; // lower priority shrinks first
    const fa = footprintFor(a.it, 1);
    const fb = footprintFor(b.it, 1);
    if (fa !== fb) return fb - fa; // larger footprint shrinks first
    // Stable placement_name tiebreak (ascending) so the order is deterministic.
    return a.it.placement_name < b.it.placement_name ? -1 : 1;
  });
  return indexed.map((r) => r.it);
}

// The primary teaching object: highest kind priority, then largest footprint,
// then placement_name. The packer weights this item's shrink heaviest so its
// scale is preserved before any filler's.
function primaryOf(items: ScaledPlacement[]): ScaledPlacement | undefined {
  let best: ScaledPlacement | undefined;
  for (const it of items) {
    if (best === undefined) {
      best = it;
      continue;
    }
    const pi = kindPriority(it);
    const pb = kindPriority(best);
    if (pi > pb) {
      best = it;
    } else if (pi === pb) {
      const fi = footprintFor(it, 1);
      const fb = footprintFor(best, 1);
      if (fi > fb || (fi === fb && it.placement_name < best.placement_name)) {
        best = it;
      }
    }
  }
  return best;
}

//============================================
// Compaction: priority-shrink + gap tighten
//============================================

// Minimum gap the compaction phase will tolerate before it starts shrinking
// items. Expressed as a fraction of the resolved object gap so a dense zone can
// pull items closer than the comfortable default without negative overlap.
const MIN_GAP_FRACTION = 0.25;

interface CompactionResult {
  // Per-item scale keyed by placement_name (1 means untouched).
  scales: Map<string, number>;
  // The gap actually used between adjacent items after compaction.
  gap: number;
  // Total footprint of the row at the chosen scales plus gaps.
  rowWidth: number;
  // True when the row fits the available width within tolerance.
  fits: boolean;
}

// The scale that makes an item's footprint equal targetFp, floored at minScale.
//
// footprintFor is piecewise in scale: footprint(s) = max(v0*s, min(label,
// v0*s*MAX_FOOTPRINT_RATIO)), where v0 is the scale-1 visual width. For a wide
// label the cap pins the footprint flat at `label` until v0*s*RATIO drops below
// label, after which the footprint shrinks linearly. A naive footprint/fullWidth
// ratio therefore stalls in the flat region (it never reduces the real
// footprint). This inverts the piecewise function exactly so the packer can shed
// label-bound footprint down toward minScale.
function scaleForFootprint(it: ScaledPlacement, targetFp: number, minScale: number): number {
  const v0 = visualWidthFor(it, 1);
  if (v0 <= 0) return minScale;
  // The footprint is bounded below by the visual width (footprint >= v0*s), so a
  // target under v0*s is unreachable without going below the scale that visual
  // alone implies.
  // Region 1: label cap does not bind once v0*s*RATIO < label, i.e. the linear
  // tail. There footprint = max(v0*s, v0*s*RATIO) = v0*s*RATIO (RATIO>1), so
  // s = targetFp / (v0*RATIO).
  const tailScale = targetFp / (v0 * MAX_FOOTPRINT_RATIO);
  // Region 2: below the cap entirely (label <= v0*s) footprint = v0*s, so
  // s = targetFp / v0. This applies when the label is narrower than the visual.
  const visualScale = targetFp / v0;
  // The reachable scale is whichever region the target lands in; take the larger
  // feasible scale that still yields footprint <= targetFp. Both candidates are
  // valid lower bounds; the binding one is the smaller scale needed. We want the
  // minimal scale that reaches the target, so evaluate both and pick the one
  // whose resulting footprint is closest to (but not above) the target.
  const candidates = [tailScale, visualScale, minScale, 1].filter((s) => s > 0);
  let best = minScale;
  for (const s of candidates) {
    const clamped = Math.max(minScale, Math.min(1, s));
    if (footprintFor(it, clamped) <= targetFp + 1e-6 && clamped > best) {
      best = clamped;
    }
  }
  return best;
}

// Compute the row width for a set of per-item scales and a gap.
function rowWidthFor(items: ScaledPlacement[], scales: Map<string, number>, gap: number): number {
  let total = 0;
  for (const it of items) {
    const s = scales.get(it.placement_name) ?? 1;
    total += footprintFor(it, s);
  }
  total += gap * Math.max(0, items.length - 1);
  return total;
}

// Phase 3 (compaction): tighten gap first, then apply priority shrink. Items are
// shrunk in shrink-priority order (fillers first), each pushed toward MIN_SCALE
// just enough to claw back the overflow, before moving to the next item. The
// primary teaching object is shrunk only when every lower-priority item has
// already hit MIN_SCALE. Stops as soon as the row fits.
function compact(
  items: ScaledPlacement[],
  availWidth: number,
  baseGap: number,
  minScale: number,
): CompactionResult {
  const scales = new Map<string, number>();
  for (const it of items) scales.set(it.placement_name, 1);

  // Tolerance: a hairline overshoot is not worth shrinking for.
  const tol = 0.5;

  // Start from the comfortable gap; tighten toward the minimum gap on overflow.
  let gap = baseGap;
  const minGap = baseGap * MIN_GAP_FRACTION;

  let rowWidth = rowWidthFor(items, scales, gap);
  if (rowWidth <= availWidth + tol) {
    return { scales, gap, rowWidth, fits: true };
  }

  // Phase 3a: tighten the gap toward minGap. This alone may resolve a small
  // overflow without shrinking any artwork.
  if (rowWidth > availWidth + tol && items.length > 1) {
    const overflow = rowWidth - availWidth;
    const gapRoom = (gap - minGap) * (items.length - 1);
    const gapReduce = Math.min(overflow, gapRoom);
    gap -= gapReduce / (items.length - 1);
    rowWidth = rowWidthFor(items, scales, gap);
  }
  if (rowWidth <= availWidth + tol) {
    return { scales, gap, rowWidth, fits: true };
  }

  // Phase 3b: priority shrink. Walk the shrink order (fillers first). For each
  // item, shrink it just enough to absorb the remaining overflow, but never
  // below minScale. Move to the next item only if overflow remains.
  const order = shrinkOrder(items);
  for (const it of order) {
    rowWidth = rowWidthFor(items, scales, gap);
    const overflow = rowWidth - availWidth;
    if (overflow <= tol) break;

    const curScale = scales.get(it.placement_name) ?? 1;
    const fpCur = footprintFor(it, curScale);
    // The least footprint this item can reach is its footprint at minScale.
    const fpAtMin = footprintFor(it, minScale);
    const sheddable = fpCur - fpAtMin;
    if (sheddable <= 0) continue;

    // Shed only as much as the overflow needs, but no more than this item can.
    const shed = Math.min(overflow, sheddable);
    const targetFp = fpCur - shed;
    // Invert the piecewise footprint(scale) to the scale that reaches targetFp.
    // This correctly handles the label-cap flat region (a naive ratio stalls
    // there and leaves the footprint pinned at label_width).
    const newScale = Math.min(curScale, scaleForFootprint(it, targetFp, minScale));
    scales.set(it.placement_name, newScale);
  }

  rowWidth = rowWidthFor(items, scales, gap);
  const fits = rowWidth <= availWidth + tol;
  return { scales, gap, rowWidth, fits };
}

//============================================
// Cost (lexicographic; used for metadata + feasibility audit)
//============================================

export interface PackingCost {
  readonly primaryWeightedShrinkPct: number;
  readonly orderViolations: number;
  readonly gapDeficit: number;
  readonly overhang: number;
}

// The lexicographic cost of a compaction result. Primary-weighted shrink is the
// dominant term so the packer's choice always favors preserving the primary
// object. orderViolations is always 0 here (the packer is order-preserving by
// construction) but is recorded so the cost vector matches the ratified shape.
function packingCost(
  items: ScaledPlacement[],
  result: CompactionResult,
  availWidth: number,
  baseGap: number,
  primary: ScaledPlacement | undefined,
): PackingCost {
  // Primary-weighted shrink percent: the primary object's shrink counts triple.
  let weighted = 0;
  let weight = 0;
  for (const it of items) {
    const s = result.scales.get(it.placement_name) ?? 1;
    const shrinkPct = (1 - s) * 100;
    const w = primary !== undefined && it.placement_name === primary.placement_name ? 3 : 1;
    weighted += shrinkPct * w;
    weight += w;
  }
  const primaryWeightedShrinkPct = weight > 0 ? weighted / weight : 0;

  // Gap deficit: how far the used gap fell below the comfortable base gap.
  const gapDeficit = Math.max(0, baseGap - result.gap);
  // Overhang: how far the row still exceeds the available width (0 when it fits).
  const overhang = Math.max(0, result.rowWidth - availWidth);

  const cost: PackingCost = {
    primaryWeightedShrinkPct: Number(primaryWeightedShrinkPct.toFixed(4)),
    orderViolations: 0,
    gapDeficit: Number(gapDeficit.toFixed(4)),
    overhang: Number(overhang.toFixed(4)),
  };
  return cost;
}

//============================================
// Per-zone packer outcome (recorded for decision metadata)
//============================================

// The facts the dispatcher records about a packed zone, so run_pipeline can fill
// the DecisionMetadata's packer fields without re-running the packer.
export interface PackerZoneOutcome {
  readonly zoneId: string;
  readonly selectedStrategy: "pack";
  readonly requiredRowScale: number;
  readonly packerThreshold: number;
  readonly packerAttempted: true;
  readonly packerResult: "fit" | "unresolved";
  readonly rowsCreated: number;
  readonly shrinkApplied: Readonly<Record<string, number>>;
  readonly cost: PackingCost;
}

//============================================
// Placement assembly (phases 1, 2, 4)
//============================================

interface PlacedItem extends ScaledPlacement {
  _scale: number;
  _centerX: number;
  _baselineY: number;
  _visualWidth: number;
  _footprint: number;
}

// Lay the items left-to-right at their compacted scales, centered in the zone,
// distributing any leftover slack as extra gap (phase 4, whitespace expansion).
function layoutRow(
  items: ScaledPlacement[],
  result: CompactionResult,
  x0: number,
  availWidth: number,
  provisionalY: number,
): ComputedItem[] {
  const footprints = items.map((it) => {
    const s = result.scales.get(it.placement_name) ?? 1;
    return footprintFor(it, s);
  });
  const contentWidth = footprints.reduce((sum, f) => sum + f, 0);

  // Phase 4: if the row fits with slack, spread the slack across the gaps so the
  // zone is not bunched to one side. If it does not fit, fall back to the
  // compacted gap (already tightened) with no extra slack.
  let gap = result.gap;
  if (result.fits && items.length > 1) {
    const slack = availWidth - contentWidth - gap * (items.length - 1);
    if (slack > 0) {
      gap += slack / (items.length - 1);
    }
  }

  const totalSpan = contentWidth + gap * Math.max(0, items.length - 1);
  // Center the packed row inside the available width.
  let cursor = x0 + Math.max(0, (availWidth - totalSpan) / 2);

  const out: PlacedItem[] = [];
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    const fw = footprints[i];
    if (it === undefined || fw === undefined) continue;
    const scale = result.scales.get(it.placement_name) ?? 1;
    const vw = visualWidthFor(it, scale);
    out.push({
      ...it,
      _scale: scale,
      _centerX: cursor + fw / 2,
      _baselineY: provisionalY,
      _visualWidth: vw,
      _footprint: fw,
    });
    cursor += fw + gap;
  }

  const finalItems: ComputedItem[] = out.map((it): ComputedItem => ({
    ...it,
    _top: 0,
    _height: 0,
    _labelX: 0,
    _labelY: 0,
    _labelLines: [],
  }));
  return finalItems;
}

//============================================
// Strategy entry point
//============================================

// Run the packer for one zone. Mirrors the PlacementStrategy signature so the
// dispatcher can swap it in for rowStrategy on the overflow trigger.
export const packStrategy: PlacementStrategy = (
  items: ScaledPlacement[],
  zone: Zone,
  ctx: StrategyContext,
): ComputedItem[] => {
  const { gap, minScale, zonePadding, diagnostics } = ctx;
  const provisionalY = zone.baseline ?? (zone.bounds.top + zone.bounds.bottom) / 2;
  if (items.length === 0) return [];

  const x0 = zone.bounds.left + zonePadding;
  const x1 = zone.bounds.right - zonePadding;
  const availWidth = x1 - x0;

  // Phase 1 (width approximation) + phase 3 (compaction): compute the per-item
  // scales and gap that fit the zone.
  const result = compact(items, availWidth, gap, minScale);

  // Phases 2 + 4: place the row at the compacted scales, expanding whitespace.
  const placed = layoutRow(items, result, x0, availWidth, provisionalY);

  // Decision metadata + cost.
  const primary = primaryOf(items);
  const cost = packingCost(items, result, availWidth, gap, primary);
  const shrinkApplied: Record<string, number> = {};
  for (const it of items)
    shrinkApplied[it.placement_name] = result.scales.get(it.placement_name) ?? 1;

  const packerResult: "fit" | "unresolved" = result.fits ? "fit" : "unresolved";
  if (ctx.packerSink !== undefined) {
    const outcome: PackerZoneOutcome = {
      zoneId: zone.id,
      selectedStrategy: "pack",
      requiredRowScale: ctx.requiredRowScale ?? 1,
      packerThreshold: ctx.config.packer.thresholdScale,
      packerAttempted: true,
      packerResult,
      rowsCreated: 1,
      shrinkApplied,
      cost,
    };
    ctx.packerSink.set(zone.id, outcome);
  }

  // The packer could not fit even at MIN_SCALE: authoring overload. Emit an
  // actionable unresolved_overlap Error and return the best-effort placement.
  if (!result.fits) {
    // Record the warn-stream overflow too, so the convergence loop still sees a
    // fittable diagnostic (the legacy stream drives the shrink loop and the
    // baseline tooling); the packer has already done the non-uniform shrink, so
    // this is a genuine overload, not a transient.
    diagnostics.push({
      stage: "horizontal",
      severity: "warn",
      kind: "zone_overflow_negative_gap",
      zone: zone.id,
      items: items.length,
      overflow_pct: Number((result.rowWidth - availWidth).toFixed(2)),
    });

    if (ctx.severitySink !== undefined) {
      const involved = items.map((it) => it.placement_name);
      const remainingDepth = result.rowWidth - availWidth;
      const payload = buildActionablePayload({
        scene: ctx.sceneName ?? "",
        zone: zone.id,
        involvedItems: involved,
        remainingOverlapDepth: Number(remainingDepth.toFixed(2)),
        // Single-row overlap area ~= remaining depth times the zone height band.
        remainingOverlapArea: Number(
          (remainingDepth * (zone.bounds.bottom - zone.bounds.top)).toFixed(2),
        ),
        availableArea: Number((availWidth * (zone.bounds.bottom - zone.bounds.top)).toFixed(2)),
        attemptedMoves: items.map((it) => ({
          target: it.placement_name,
          kind: "shrink" as const,
          magnitude: Number((1 - (result.scales.get(it.placement_name) ?? 1)).toFixed(3)),
          outcome: "hit MIN_SCALE floor",
        })),
        suggestedFix: "reduce items, enlarge the zone, or split the zone",
      });
      ctx.severitySink.push(
        buildDiagnostic(
          "unresolved_overlap",
          { scene_name: ctx.sceneName ?? "", zone_name: zone.id },
          payload,
        ),
      );
    }
  }

  return placed;
};

//============================================
// Probe: would the row strategy require unacceptable shrink / overflow?
//============================================

// The row layout's required uniform scale and whether it overflows, computed
// without placing anything. The dispatcher uses this as the packer trigger:
// engage the packer when requiredScale < thresholdScale OR the row overflows.
// This mirrors the uniform-shrink path inside row_strategy.ts exactly so the
// trigger reads the same numbers the row strategy would produce.
export function probeRow(
  items: ScaledPlacement[],
  zone: Zone,
  gap: number,
  zonePadding: number,
  minScale: number,
): { requiredScale: number; overflow: boolean } {
  if (items.length === 0) return { requiredScale: 1, overflow: false };
  const x0 = zone.bounds.left + zonePadding;
  const x1 = zone.bounds.right - zonePadding;
  const zoneW = x1 - x0;
  const mode = zone.align ?? "left";

  if (mode === "tab-stops") {
    // Tab-stops place three buckets at scale 1 with no shrink; overflow is the
    // only signal. Approximate the bucket total the same way row_strategy does.
    let total = 0;
    for (const it of items) total += footprintFor(it, 1);
    total += gap * Math.max(0, items.length - 1) + 2 * gap;
    const overflow = total > zoneW + 0.5;
    // The row strategy never shrinks tab-stops, so requiredScale is reported as 1
    // (no shrink attempted); the overflow flag alone drives the trigger.
    return { requiredScale: 1, overflow };
  }

  // Single-row modes: required uniform scale is zoneW / minSpread when the
  // scale-1 footprint exceeds the zone, mirroring row_strategy's shrink path.
  let minSpread = 0;
  for (const it of items) minSpread += footprintFor(it, 1);
  const totalFootprint = minSpread + gap * Math.max(0, items.length - 1);
  if (totalFootprint <= zoneW) {
    return { requiredScale: 1, overflow: false };
  }
  if (minSpread < zoneW) {
    // Fits once the inter-item gap is removed; the row strategy keeps scale 1.
    return { requiredScale: 1, overflow: false };
  }
  const requiredScale = Math.max(minScale, zoneW / minSpread);
  const footprintsAtScale = items.reduce((s, it) => s + footprintFor(it, requiredScale), 0);
  const overflow = footprintsAtScale > zoneW + 0.5;
  return { requiredScale, overflow };
}
