// Stage 9: Label layout + 3-pass horizontal collision nudge, then greedy
// vertical stagger within each zone. Sets _labelX, _labelY, _labelLines.
// Wraps labels exceeding their budget. Labels are clamped inside the padded
// zone; cross-zone collision is not checked here.
//
// The _labelY seed is placement-aware (label_placement: top | bottom). top
// (default) seeds the label TOP edge above the object; bottom (legacy) seeds it
// below the row baseline. The vertical stagger below is direction-aware:
// each zone is partitioned by resolved placement and vertical depth tier. Each
// group ladders along its own direction -- bottom labels DOWN (rows away from
// the object below), top labels UP (rows away from the object above), each
// clamped at its own zone edge. Separate depth tiers already occupy distinct
// vertical rows, so they must never share a stagger ladder. Cross-zone
// label-vs-artwork collision is still handled later by resolveLabelCollisions.
//
// The stagger writes only _labelX/_labelY (label coordinates). It NEVER writes
// _centerX/_baselineY (item coordinates), so item placement is unchanged and a scene whose
// labels do not collide assigns every label to row 0 and renders identically
// to the pre-stagger behavior.

import { buildGlobalDefaults } from "./config/index.js";
import { wrapLabel } from "./wrap_label.js";
import { detectCollision, buildResolutionCandidate } from "./geometry/collision.js";
import { buildActionablePayload } from "./diagnostics/payload.js";
import { buildDiagnostic } from "./diagnostics/severity_model.js";
import type { Aabb } from "./geometry/types.js";
import type { AttemptedMove } from "./diagnostics/payload.js";
import type { SeverityDiagnostic } from "./diagnostics/severity_model.js";
import type { LayoutConfig } from "./config/index.js";
import type {
  ComputedItem,
  ComputedZoneBand,
  Diagnostics,
  LabelPlacement,
  LayoutRules,
  Zone,
} from "./types.js";

// The vertical extent a label is clamped within for one zone. After the vertical
// reflow this is the COMPUTED band (reflow-zones output), so a label clamps to the
// reflowed band edges, not the authored zone bounds (which became seeds). When no
// computed band exists for a zone (a direct-call unit test that did not run
// reflow-zones), it falls back to the authored zone bounds so the legacy clamp
// behavior is preserved.
interface VerticalBand {
  top: number;
  bottom: number;
}

// Resolve the vertical clamp band for one zone: the computed band edges when
// reflow-zones produced one, else the authored zone bounds. Horizontal clamps
// (left/right) always use the authored bounds; the reflow is vertical-only.
function verticalBandFor(zone: Zone, zoneBands?: Map<string, ComputedZoneBand>): VerticalBand {
  const band = zoneBands?.get(zone.id);
  if (band !== undefined) {
    return { top: band.top, bottom: band.bottom };
  }
  return { top: zone.bounds.top, bottom: zone.bounds.bottom };
}

// Effective rendered half-width of a label in scene-percent. The authored
// label_width is a layout-time budget; a long label whose wrapped line still
// exceeds the budget renders wider than it. The stagger's row-fit test uses the
// wider of the budget and the engine's own per-char text estimate
// (AVG_CHAR_WIDTH_PCT, the same model wrap_label uses) so it separates labels
// that would otherwise visually overprint. Short labels (text estimate <=
// budget) keep the budget half-width, so clean scenes still assign every label
// to row 0 and render identically.
function effectiveLabelHalfWidth(
  lines: string[],
  labelWidth: number,
  avgCharWidthPct: number,
): number {
  let maxLen = 0;
  for (const line of lines) {
    if (line.length > maxLen) maxLen = line.length;
  }
  const textWidth = maxLen * avgCharWidthPct;
  const effective = Math.max(labelWidth, textWidth);
  return effective / 2;
}

// Sign convention for a single-direction stagger/move ladder, shared by the
// per-zone stagger (layoutLabels half) and the global re-stagger / move set
// (resolveLabelCollisions half). +1 ladders DOWN the y axis (increasing _labelY:
// bottom labels move below their object); -1 ladders UP (decreasing _labelY: top
// labels move above their object). y grows downward in scene-percent.
type StaggerDirection = 1 | -1;

function depthTierOf(item: ComputedItem): number {
  return item.depth_tier ?? 0;
}

// Tunables a stagger group needs, threaded so staggerGroup stays a pure helper.
// bandTop / bandBottom are the COMPUTED band edges (reflow-zones output) the
// stagger clamps the deepest row against, replacing the authored zone bounds.
interface StaggerContext {
  readonly avgCharWidthPct: number;
  readonly lineHeightPct: number;
  readonly labelZonePadding: number;
  readonly collisionTolerance: number;
  readonly bandTop: number;
  readonly bandBottom: number;
  // OUTPUT: staggerGroup fills rowOf[placement_name] = assigned row index for
  // each label it places, read afterward by the residual same-row collision check.
  readonly rowOf: Map<string, number>;
  readonly diagnostics: Diagnostics;
}

// Greedy interval-graph vertical stagger for one placement group, laddered in a
// single direction. direction === 1 ladders DOWN (bottom labels move below the
// row baseline, away from the object beneath them); direction === -1 ladders UP
// (top labels move above the object, away from the object above them).
//
// Pass 1 assigns each label the lowest row whose last-placed label's right edge
// it clears (same interval-graph rule for both directions). Pass 2 maps a row
// index to a _labelY by stepping AWAY from row 0 in `direction`, anchored on each
// label's own seeded row-0 _labelY:
//   down: _labelY = baseline + row * step, clamped so the deepest row's BOTTOM
//         edge stays above zone.bounds.bottom - pad.
//   up:   _labelY = baseline - row * step, clamped so the deepest row's TOP edge
//         (_labelY itself) stays at or below zone.bounds.top + pad.
// The step is compressed uniformly when the natural ladder would push the deepest
// row past its clamp, so every assigned row stays at a DISTINCT y instead of
// collapsing onto the clamp line (which would reintroduce overprint in tight
// bands). Row 0 keeps its seeded _labelY, so a group with no overlap is untouched
// and byte-identical to the pre-stagger seed. Only _labelY is written.
function staggerGroup(
  group: ComputedItem[],
  zone: Zone,
  direction: StaggerDirection,
  ctx: StaggerContext,
): void {
  if (group.length === 0) return;
  // Stable order: ascending label center-x, then placement_name for determinism.
  group.sort((a, b) => {
    if (a._labelX !== b._labelX) return a._labelX - b._labelX;
    return a.placement_name.localeCompare(b.placement_name);
  });
  // Pass 1: assign each label a row index. rowRightEdges[r] tracks the right edge
  // of the last label placed in row r; a label fits in row r when its left edge
  // clears that right edge (within tolerance). Lowest fitting row wins.
  const rowRightEdges: number[] = [];
  const localRow = new Map<string, number>();
  let maxRow = 0;
  for (const it of group) {
    const half = effectiveLabelHalfWidth(
      it._labelLines,
      it.layout.label_width,
      ctx.avgCharWidthPct,
    );
    const leftEdge = it._labelX - half;
    const rightEdge = it._labelX + half;
    let row = 0;
    while (row < rowRightEdges.length) {
      const edge = rowRightEdges[row];
      if (edge === undefined || leftEdge >= edge - ctx.collisionTolerance) break;
      row++;
    }
    rowRightEdges[row] = rightEdge;
    localRow.set(it.placement_name, row);
    ctx.rowOf.set(it.placement_name, row);
    if (row > maxRow) maxRow = row;
  }
  if (maxRow === 0) return; // No overlap: leave every seeded _labelY as is.

  // Use the largest line count among staggered labels so a 2-line label in any
  // lower row still clears the row beside it where space allows.
  let maxLineCount = 1;
  for (const it of group) {
    const r = localRow.get(it.placement_name) ?? 0;
    if (r > 0) maxLineCount = Math.max(maxLineCount, it._labelLines.length);
  }
  const naturalStep = ctx.lineHeightPct * maxLineCount;
  // FRAME SAFETY: reserve the deepest label's height so the ladder stays inside
  // the padded zone (which is within the renderable frame). For a DOWN ladder the
  // clamp bounds the deepest row's BOTTOM edge; for an UP ladder the clamp bounds
  // the deepest row's TOP edge (_labelY) at the zone top. A label is never pushed
  // off-frame; if space runs out the step compresses and a residual overlap is
  // tolerated (and flagged by the residual pass) rather than ejecting a label.
  const labelHeight = ctx.lineHeightPct * maxLineCount;
  const bottomClamp = ctx.bandBottom - ctx.labelZonePadding - labelHeight;
  const topClamp = ctx.bandTop + ctx.labelZonePadding;
  for (const it of group) {
    const row = localRow.get(it.placement_name) ?? 0;
    if (row === 0) continue;
    // Anchor the ladder on this label's own seeded row-0 _labelY.
    const baseline = it._labelY;
    let step = naturalStep;
    if (direction === 1) {
      // DOWN ladder: clamp the deepest row's bottom at the padded zone floor.
      const naturalBottom = baseline + maxRow * naturalStep;
      if (naturalBottom > bottomClamp) {
        const available = bottomClamp - baseline;
        step = available > 0 ? available / maxRow : 0;
      }
      it._labelY = baseline + row * step;
    } else {
      // UP ladder: clamp the deepest row's top (_labelY) at the padded zone top.
      const naturalTop = baseline - maxRow * naturalStep;
      if (naturalTop < topClamp) {
        const available = baseline - topClamp;
        step = available > 0 ? available / maxRow : 0;
      }
      it._labelY = baseline - row * step;
    }
    ctx.diagnostics.push({
      stage: "labels",
      severity: "info",
      kind: "label_row_staggered",
      zone: zone.id,
      placement_name: it.placement_name,
      staggered_row: row,
    });
  }
}

export function layoutLabels(
  zoneLayouts: Map<string, ComputedItem[]>,
  zones: Zone[],
  layoutRules: LayoutRules = {},
  diagnostics: Diagnostics = [],
  config: LayoutConfig = buildGlobalDefaults(),
  zoneBands?: Map<string, ComputedZoneBand>,
): Map<string, ComputedItem[]> {
  // Label tunables now resolve through LayoutConfig. The authored
  // layout_rules.label_offset_y still wins; otherwise the canonical config
  // labelOffsetY (3.5) applies, matching the prior `?? 3.5` fallback.
  const labelOffsetY = layoutRules.label_offset_y ?? config.labelOffsetY;
  const avgCharWidthPct = config.avgCharWidthPct;
  const lineHeightPct = config.labelLineHeightPct;
  // Scene-wide label placement default: per-placement override wins, then the
  // scene layout_rules, then the config default ("top"). config.labelPlacement
  // already folds in the scene rule, so the middle term is belt-and-suspenders.
  const sceneLabelPlacement = layoutRules.label_placement ?? config.labelPlacement;
  const labelZonePadding = config.spacing.labelZonePadding;
  const nudgePasses = config.labelNudgePasses;
  const wrapBudgetTolerance = config.wrapBudgetTolerance;
  // Single shared label-collision slack (stagger row-fit and residual checks).
  const collisionTolerance = config.labelCollisionTolerance;
  const result = new Map<string, ComputedItem[]>();

  for (const zone of zones) {
    const source = zoneLayouts.get(zone.id) ?? [];
    // The vertical clamp band for this zone: the computed reflow band when present,
    // else the authored zone bounds. All vertical seed clamps and the stagger
    // ladder clamp against this band so a label stays inside the REFLOWED band.
    const band = verticalBandFor(zone, zoneBands);
    const items: ComputedItem[] = source.map((it) => {
      // Single wrap site: consume the wrapped lines the measure-vertical stage
      // already computed (it._labelLines) instead of re-wrapping here. The
      // measure stage runs before place-labels in PLACEMENT_PHASES and writes
      // _labelLines via the same wrapLabel call, so this is the SAME wrap, not a
      // second one. The guarded fallback only fires if an item reaches this phase
      // without measure-vertical having run (a defensive path used by direct-call
      // unit tests, where _labelLines is undefined); it must mirror the
      // measure-stage wrap arguments so the two sites cannot diverge.
      const measuredLines = it._labelLines;
      const labelLines =
        measuredLines !== undefined && measuredLines.length > 0
          ? measuredLines
          : wrapLabel(it.label, it.layout.label_width, avgCharWidthPct, wrapBudgetTolerance);
      // Resolve placement per item: per-placement override wins, then scene rule,
      // then config default. Seed _labelY (the label TOP edge) accordingly.
      const authoredPlacement = it.layout.label_placement ?? sceneLabelPlacement;
      // labelHeight is the rendered label box height (one lineHeightPct per
      // wrapped line). Prefer the measured _labelBoxHeight (computed once by
      // measure-vertical) and fall back to the line-count product only when the
      // measured field is absent (the same defensive path as the wrap above).
      const labelHeight = it._labelBoxHeight ?? lineHeightPct * labelLines.length;
      const topClamp = band.top + labelZonePadding;
      const bottomClamp = band.bottom - labelZonePadding - labelHeight;
      // The own object's art box (top..bottom). A candidate label box that
      // intersects [objectTop, objectBottom] overprints its own art.
      const objectTop = it._top;
      const objectBottom = it._top + it._height;
      // Candidate label-TOP-edge Y for each side, clamped to stay inside the OWN
      // padded BAND. The reflow reserves a row tall enough for object + gap + label,
      // so in a well-formed scene the authored side already clears the object.
      //   TOP side: the label sits labelOffsetY above the object top; clamp into
      //     [topClamp, objectTop - labelHeight] so its bottom clears the object top.
      //   BOTTOM side: the label sits labelOffsetY below the object bottom; clamp so
      //     its bottom stays above the padded band floor (clampBottomY).
      const topCeiling = objectTop - labelHeight; // highest top whose bottom clears
      const seedTop = it._top - labelOffsetY - labelHeight;
      const seedBottom = objectBottom + labelOffsetY;
      // The clamped candidate top-Y per side. The top candidate is held at or below
      // topClamp (never above the padded band top) and at or above nothing extra
      // when the ceiling sits below topClamp (no room: it lands at topClamp and
      // overprints). The bottom candidate is held at or above seedBottom and at or
      // below bottomClamp.
      const topCandidateY = Math.min(Math.max(seedTop, topClamp), Math.max(topCeiling, topClamp));
      const bottomCandidateY = Math.min(Math.max(seedBottom, topClamp), bottomClamp);
      // Own-art overlap a candidate would incur: the vertical intersection of the
      // label box [y, y+labelHeight] with the object art box [objectTop,
      // objectBottom]. Zero means the label fully clears its own art on that side.
      function ownArtOverlap(candidateY: number): number {
        const labelBottom = candidateY + labelHeight;
        const overlap = Math.min(labelBottom, objectBottom) - Math.max(candidateY, objectTop);
        return Math.max(0, overlap);
      }
      // Whether a candidate exits the padded band (its box pokes past the band top
      // or band floor after clamping -- only possible when there is no in-band room).
      function exitsBand(candidateY: number): boolean {
        const labelBottom = candidateY + labelHeight;
        return candidateY < topClamp - 1e-9 || labelBottom > band.bottom - labelZonePadding + 1e-9;
      }
      const topOverlap = ownArtOverlap(topCandidateY);
      const bottomOverlap = ownArtOverlap(bottomCandidateY);
      const topClears = topOverlap <= 1e-9 && !exitsBand(topCandidateY);
      const bottomClears = bottomOverlap <= 1e-9 && !exitsBand(bottomCandidateY);
      // Terminal safety flip. Start from the authored side. Flip to the other side
      // when the authored candidate overlaps its own art OR exits the band AND the
      // other side fully clears. When NEITHER side fully clears, pick the
      // lowest-overlap side and emit a label-clearance diagnostic so the own-art
      // gate stays loud (the scene fails unless a reviewer classifies it as
      // out-of-scope content overload). A successful flip keeps the label box inside
      // the same measured row extent (the band reserved the row for either side).
      let placement: LabelPlacement;
      if (authoredPlacement === "bottom") {
        if (bottomClears) placement = "bottom";
        else if (topClears) placement = "top";
        else placement = bottomOverlap <= topOverlap ? "bottom" : "top";
      } else {
        if (topClears) placement = "top";
        else if (bottomClears) placement = "bottom";
        else placement = topOverlap <= bottomOverlap ? "top" : "bottom";
      }
      const labelY = placement === "bottom" ? bottomCandidateY : topCandidateY;
      // When neither side fully cleared its own art (a genuine infeasibility: the
      // object is too tall for the reserved row even after reflow), surface a
      // label-clearance diagnostic naming the residual overlap on the chosen side.
      const chosenOverlap = placement === "bottom" ? bottomOverlap : topOverlap;
      if (!topClears && !bottomClears && chosenOverlap > 1e-9) {
        diagnostics.push({
          stage: "labels",
          severity: "warn",
          kind: "item_escapes_zone_vertically",
          zone: zone.id,
          placement_name: it.placement_name,
          overflow_pct: Number(chosenOverlap.toFixed(2)),
        });
      }
      // Carry the effective placement forward when the terminal flip changed the
      // side (either direction), so the stagger and resolve-collisions phases ladder
      // and anchor the label on its resolved side. Items whose placement is
      // unchanged keep their original layout object untouched (byte-identical output
      // for clean scenes).
      const flipped = placement !== authoredPlacement;
      const resolvedLayout = flipped ? { ...it.layout, label_placement: placement } : it.layout;
      return {
        ...it,
        layout: resolvedLayout,
        _labelLines: labelLines,
        _labelX: it._centerX,
        _labelY: labelY,
      };
    });

    for (let pass = 0; pass < nudgePasses; pass++) {
      items.sort((a, b) => a._labelX - b._labelX);
      for (let i = 1; i < items.length; i++) {
        const prev = items[i - 1];
        const cur = items[i];
        if (prev === undefined || cur === undefined) continue;
        // Overlap DETECTION uses each label's EFFECTIVE half-width (the wider of
        // authored budget vs rendered text width) so a budget-exceeding label
        // that visually overprints is detected even when the engine would
        // otherwise "converge". The separation target `want` is that effective
        // sum.
        const prevHalf = effectiveLabelHalfWidth(
          prev._labelLines,
          prev.layout.label_width,
          avgCharWidthPct,
        );
        const curHalf = effectiveLabelHalfWidth(
          cur._labelLines,
          cur.layout.label_width,
          avgCharWidthPct,
        );
        const want = prevHalf + curHalf;
        const gap = cur._labelX - prev._labelX;
        // Nudge MAGNITUDE is minimal: a pair is moved apart ONLY when its real
        // effective extents actually overlap (gap below the effective sum by more
        // than the shared collision tolerance), and then by exactly enough to
        // bring the two effective edges to touching (`want`). A pair already clear
        // under effective width is left exactly where it was anchored, so labels
        // that do not overprint keep their authored/anchored position instead of
        // being shoved off their bases. The tolerance gate is what restores
        // anchoring on clean scenes; the clearance target stays `want` so a real
        // overlap is fully separated (no residual handed to the global phase).
        if (gap < want - collisionTolerance) {
          const push = (want - gap) / 2;
          prev._labelX -= push;
          cur._labelX += push;
        }
      }
      const x0 = zone.bounds.left + labelZonePadding;
      const x1 = zone.bounds.right - labelZonePadding;
      for (const it of items) {
        // Clamp using the effective half-width so a budget-exceeding label is
        // held fully inside the padded zone by its real rendered extent.
        const half = effectiveLabelHalfWidth(
          it._labelLines,
          it.layout.label_width,
          avgCharWidthPct,
        );
        if (it._labelX < x0 + half) it._labelX = x0 + half;
        if (it._labelX > x1 - half) it._labelX = x1 - half;
      }
    }

    // Direction-aware vertical stagger. After the horizontal nudge,
    // adjacent labels may still overlap (the nudge is bounded by zone width).
    // Each resolved placement/depth-tier group staggers along its OWN direction:
    // bottom labels ladder DOWN (rows +1), top labels ladder UP (rows -1).
    // Distinct tiers already have distinct seeded Y positions; putting them in
    // one horizontal interval graph would invent a row conflict and pull one
    // label into a neighboring tier's artwork.
    const groups = new Map<string, ComputedItem[]>();
    for (const it of items) {
      const placement = it.layout.label_placement ?? sceneLabelPlacement;
      const key = `${placement}:${depthTierOf(it)}`;
      const group = groups.get(key) ?? [];
      group.push(it);
      groups.set(key, group);
    }
    // rowOf merges group-local row assignments (placement_name is unique per
    // zone). The residual check also compares depth tier, so a coincidental row
    // tie between already-separated tiers is never reported as a collision.
    const rowOf = new Map<string, number>();
    const placementOf = new Map<string, "top" | "bottom">();
    const orderedGroups = [...groups.values()].sort((a, b) => {
      const aPlacement = a[0]?.layout.label_placement ?? sceneLabelPlacement;
      const bPlacement = b[0]?.layout.label_placement ?? sceneLabelPlacement;
      if (aPlacement !== bPlacement) return aPlacement === "top" ? -1 : 1;
      return depthTierOf(a[0]!) - depthTierOf(b[0]!);
    });
    for (const group of orderedGroups) {
      const placement = group[0]?.layout.label_placement ?? sceneLabelPlacement;
      staggerGroup(group, zone, placement === "bottom" ? 1 : -1, {
        avgCharWidthPct,
        lineHeightPct,
        labelZonePadding,
        collisionTolerance,
        bandTop: band.top,
        bandBottom: band.bottom,
        rowOf,
        diagnostics,
      });
      for (const it of group) placementOf.set(it.placement_name, placement);
    }

    // Residual collision: after staggering, two labels still overlap only when
    // they share a group AND a row and their horizontal extents overlap. Report
    // each such pair so the diagnostic metric can flag the scene.
    items.sort((a, b) => a._labelX - b._labelX);
    for (let i = 1; i < items.length; i++) {
      const prev = items[i - 1];
      const cur = items[i];
      if (prev === undefined || cur === undefined) continue;
      // Labels in different placement groups are vertically disjoint (one above,
      // one below its object), so they can never overprint.
      if (placementOf.get(prev.placement_name) !== placementOf.get(cur.placement_name)) continue;
      // Different depth tiers have already been placed on distinct vertical rows.
      // Their group-local row numbers are not comparable.
      if (depthTierOf(prev) !== depthTierOf(cur)) continue;
      // Only labels on the same assigned row can collide horizontally; labels
      // on different rows are vertically separated by the stagger.
      if ((rowOf.get(prev.placement_name) ?? 0) !== (rowOf.get(cur.placement_name) ?? 0)) continue;
      const prevHalf = effectiveLabelHalfWidth(
        prev._labelLines,
        prev.layout.label_width,
        avgCharWidthPct,
      );
      const curHalf = effectiveLabelHalfWidth(
        cur._labelLines,
        cur.layout.label_width,
        avgCharWidthPct,
      );
      const want = prevHalf + curHalf;
      if (cur._labelX - prev._labelX < want - collisionTolerance) {
        diagnostics.push({
          stage: "labels",
          severity: "warn",
          kind: "label_collision_residual",
          zone: zone.id,
          between: [prev.placement_name, cur.placement_name],
        });
      }
    }

    items.sort((a, b) => {
      const ta = a.depth_tier ?? 0;
      const tb = b.depth_tier ?? 0;
      if (ta !== tb) return ta - tb;
      return a.placement_name.localeCompare(b.placement_name);
    });
    result.set(zone.id, items);
  }

  return result;
}

//============================================
// Global 2D label de-overlap + label-vs-artwork avoidance (resolve-collisions)
//============================================
//
// layoutLabels (above) runs the legacy per-zone horizontal nudge + vertical
// stagger; it never checks a label against a NEIGHBORING object's artwork, and
// its residual check only flags same-row, adjacent-pair label overlaps. The
// resolve-collisions phase adds a global pass that runs AFTER labels are placed,
// resolving BOTH label-vs-artwork and label-vs-label overlaps across every zone
// using the shared geometry primitive (detectCollision / buildResolutionCandidate).
//
// Movement model (closed set of moves, DIRECTION-AWARE per placement):
// - Artwork boxes are obstacles; they never move. Only label boxes move.
// - Each label carries a placementMode ("top" | "bottom") resolved from the same
//   per-placement-then-scene-default chain layoutLabels used. The vertical move
//   set is mirrored by mode: a bottom label may only step DOWN (toward the padded
//   zone floor, away from the object above it); a top label may only step UP
//   (toward the padded zone top, away from the object below it). A label is never
//   pushed across its object, which would re-collide on the far side.
// - Allowed moves: a horizontal nudge along the label's x axis, or a discrete
//   row step (whole labelLineHeightPct increments) in the label's own vertical
//   direction. For an artwork collision the resolver enumerates BOTH vertical
//   candidates that exist for the mode (a bottom label: step down clearing the
//   obstacle bottom; a top label: step up clearing the obstacle top) plus the two
//   horizontal nudges, bounded by bottomMax (down) and topMin (up); the scorer
//   picks the cheapest deterministically. The geometry's suggestedAxis breaks ties.
//   EXCEPT:
//   - label-vs-artwork avoidance has PRIORITY over label-label spacing: an
//     artwork collision is always resolved before a label-label collision for
//     the same label in the same pass.
//   - if a horizontal nudge would push the label outside its zone bounds, a row
//     step is used instead (keep labels inside the padded zone).
//   - full containment (Collision.aInB / bInA: the label sits entirely inside an
//     object box) cannot be cleared by one interval-separation step, so it forces
//     a (larger) row step in the label's own direction.
// - When clearing an artwork collision re-introduces a label-label overlap, the
//   per-zone re-stagger (Phase B) re-separates that group in its own direction.
//
// Determinism: labels are visited in a fixed order (_labelX, then placement_name
// tiebreak); each label resolves its single deepest current collision per visit;
// a fixed pass budget (config.labelMaxResolvePasses, default 4) bounds the sweep
// and it stops early when a pass makes no move. Identical input -> identical
// output.
//
// End-state classification (severity diagnostics, returned to run_pipeline):
// - a label still overlapping after the budget -> unresolved_label_overlap Error.
// - a label clear of overlaps but far from its IDEAL UNCLAMPED seed anchor ->
//   poor_label_alignment Warning. anchorY is the ideal seed Y (NOT the clamped
//   seed), so a label held at a zone edge by the seed-level clamp is flagged just
//   as a label displaced by a collision move is. The diagnostic carries cause
//   context (clamp drift vs collision displacement) in its payload's attempted
//   moves so the single reused code stays interpretable.
// - a dense-but-readable cluster (many labels packed into deep rows but all
//   clear) -> possible_overload Review-required.

// Mutable working record for one label during de-overlap. The label box is
// recomputed from x/y/half/lineH on demand. anchorX / anchorY are the label's
// IDEAL UNCLAMPED seed position (the y the seed formula would produce with no
// zone-edge clamp and no stagger), used to measure drift for poor_label_alignment
// so a clamp-displaced label is flagged the same as a collision-displaced one.
// rowStep is the discrete row-step increment (one labelLineHeightPct).
// placementMode is the label's resolved placement ("top" | "bottom"); it gates
// the vertical move DIRECTION (top steps up, bottom steps down) so a label is
// never pushed across its own object.
interface LabelWork {
  item: ComputedItem;
  zoneId: string;
  zone: Zone;
  // bandTop / bandBottom are the COMPUTED band edges (reflow-zones output) this
  // label clamps its vertical moves and re-stagger against, replacing the authored
  // zone bounds. They fall back to the authored bounds when no band was produced.
  readonly bandTop: number;
  readonly bandBottom: number;
  half: number;
  lineH: number;
  x: number;
  y: number;
  readonly anchorX: number;
  readonly anchorY: number;
  readonly rowStep: number;
  readonly placementMode: LabelPlacement;
  // Stagger row assigned by Phase B (0 = top row). Two labels on DIFFERENT rows
  // are vertically separated even when their x-extents overlap, mirroring the
  // legacy label_collision_residual semantics; only a same-row x-overlap is a real
  // label-label collision. Defaults to 0 (single row) until Phase B assigns it.
  row: number;
  moves: AttemptedMove[];
}

// The AABB of a label given its current center-x, top-y, half-width, and height.
function labelAabb(w: LabelWork): Aabb {
  const box: Aabb = { x: w.x - w.half, y: w.y, w: w.half * 2, h: w.lineH };
  return box;
}

// The AABB of an object's artwork from its computed placement box (center-x,
// top, visual width, height).
function artworkAabb(it: ComputedItem): Aabb {
  const box: Aabb = {
    x: it._centerX - it._visualWidth / 2,
    y: it._top,
    w: it._visualWidth,
    h: it._height,
  };
  return box;
}

// A resolved collision pick for one label: the geometry fact, whether the other
// box is object artwork, the other box id (for the diagnostic payload), and the
// other box itself (so the mover can size an alternate-axis clearing nudge).
interface CollisionPick {
  readonly isArtwork: boolean;
  readonly collision: NonNullable<ReturnType<typeof detectCollision>>;
  readonly otherId: string;
  readonly otherBox: Aabb;
}

// The deepest current ARTWORK collision for one label against every object's
// artwork box (excluding its own owner's artwork). Deeper penetration wins; ties
// break on the box id so the choice is deterministic. Returns null when the label
// touches no neighboring artwork. Used by Phase A (artwork avoidance).
function deepestArtworkFor(
  self: LabelWork,
  artBoxes: { id: string; box: Aabb; owner: string }[],
): CollisionPick | null {
  const selfBox = labelAabb(self);
  const selfId = self.item.placement_name;
  let best: CollisionPick | null = null;
  for (const a of artBoxes) {
    if (a.owner === selfId) continue;
    const c = detectCollision(selfBox, "L:" + selfId, a.box, a.id);
    if (c === null) continue;
    if (
      best === null ||
      c.overlapDepth > best.collision.overlapDepth ||
      (c.overlapDepth === best.collision.overlapDepth && a.id < best.otherId)
    ) {
      best = { isArtwork: true, collision: c, otherId: a.id, otherBox: a.box };
    }
  }
  return best;
}

// The deepest current collision for one label against every OTHER label AND every
// artwork box. Artwork collisions outrank label collisions (the artwork-priority
// rule). Used by the end-state classifier to decide whether a label is still
// overlapping anything after both phases.
//
// A label-label collision counts ONLY when the two labels share the same zone,
// the same placement MODE, and the same stagger row. Different modes are
// vertically disjoint (a top label sits above its object, a bottom label below
// its object), so a top/bottom pair never overprints even with overlapping
// x-extents. Within one mode, labels on DIFFERENT rows are vertically separated
// by the stagger, which is exactly the legacy label_collision_residual semantics.
// Counting cross-mode or cross-row x-overlaps as Errors would falsely flag the
// intended staggered ladder.
function deepestAnyFor(
  idx: number,
  labels: LabelWork[],
  artBoxes: { id: string; box: Aabb; owner: string }[],
): CollisionPick | null {
  const self = labels[idx];
  if (self === undefined) return null;
  const art = deepestArtworkFor(self, artBoxes);
  if (art !== null) return art;

  const selfBox = labelAabb(self);
  const selfId = self.item.placement_name;
  let bestLab: CollisionPick | null = null;
  for (let j = 0; j < labels.length; j++) {
    if (j === idx) continue;
    const other = labels[j];
    if (other === undefined) continue;
    // Different placement modes are vertically disjoint; they can never overprint.
    if (other.placementMode !== self.placementMode) continue;
    // Within the same mode and zone, only same-row labels can truly collide; a
    // different row is a vertical separation, not an overlap.
    if (other.zoneId === self.zoneId && other.row !== self.row) continue;
    const otherId = "L:" + other.item.placement_name;
    const c = detectCollision(selfBox, "L:" + selfId, labelAabb(other), otherId);
    if (c === null) continue;
    if (
      bestLab === null ||
      c.overlapDepth > bestLab.collision.overlapDepth ||
      (c.overlapDepth === bestLab.collision.overlapDepth && otherId < bestLab.otherId)
    ) {
      bestLab = { isArtwork: false, collision: c, otherId, otherBox: labelAabb(other) };
    }
  }
  return bestLab;
}

// True when a label centered at x with the given half-width fits inside the
// padded zone on the horizontal axis.
function labelFitsX(x: number, half: number, zone: Zone, pad: number): boolean {
  const fits =
    x - half >= zone.bounds.left + pad - 1e-9 && x + half <= zone.bounds.right - pad + 1e-9;
  return fits;
}

// A concrete candidate move for one label, with the resulting coordinate, the
// cost (distance moved), whether it stays inside the zone, and whether it fully
// clears the obstacle.
interface MoveOption {
  readonly kind: "nudge-x" | "row-drop";
  readonly newX: number;
  readonly newY: number;
  readonly cost: number;
  readonly inZone: boolean;
}

// Apply the chosen single move to one label, recording it in the label's move
// log. The label is geometry "A"; separationForA moves IT.
//
// Move policy (DIRECTION-AWARE): enumerate the in-zone clearing moves on
// both axes and pick the cheapest that stays inside the label's own zone, with a
// nudge preferred over a row step at equal cost (a nudge keeps the label near its
// anchor):
//  - nudge-x-left: slide the label left until its right edge clears the obstacle.
//  - nudge-x-right: slide the label right until its left edge clears the obstacle.
//  - row-step: move the label in whole rowStep increments in its OWN vertical
//    direction until it clears the obstacle on that side, bounded by the matching
//    zone edge:
//      bottom label: step DOWN until its top clears the obstacle's bottom,
//                    bounded by bottomMax (the padded zone floor minus height).
//      top label:    step UP until its bottom clears the obstacle's top, bounded
//                    by topMin (the padded zone top).
// Both vertical candidates are bounded; the scorer picks the cheapest move overall
// so a top label never drops past its object and a bottom label never rises past
// its object. A horizontal nudge is allowed even when geometry's cheaper axis is
// y: when a blocked row step would otherwise leave the label stuck against a tall
// neighbor's artwork, an x-nudge clears it instead. Full containment disables the
// x-nudge (one interval step cannot clear it) and forces a (larger) row step in
// the label's own direction. All moves are clamped to the zone: a label never
// wanders into a lower zone's artwork. When no move fully clears AND stays
// in-zone, the cheapest in-zone partial move (a bounded step to the label's own
// zone edge) is applied so each pass still makes progress; the end-state
// classifier flags any residual overlap as unresolved.
// Returns true when a real (non-zero) move was applied.
function applyLabelMove(
  self: LabelWork,
  pick: CollisionPick,
  zonePad: number,
  zoneNeighbors: LabelWork[],
): boolean {
  const collision = pick.collision;
  const contained = collision.aInB || collision.bInA;
  const moveTarget = self.item.placement_name;
  const overlapClass = pick.isArtwork ? "artwork" : "label";
  const o = pick.otherBox;
  // The label's own vertical edge bounds. A bottom label may travel DOWN as far
  // as the padded BAND floor (its top capped so its bottom edge stays framed); a
  // top label may travel UP as far as the padded BAND top (its top edge itself).
  // The COMPUTED band (reflow-zones output) replaces the authored zone bounds.
  const bottomMax = self.bandBottom - zonePad - self.lineH;
  const topMin = self.bandTop + zonePad;
  const movesDown = self.placementMode !== "top";
  // The geometry's cheaper-axis suggestion. When two clearing moves cost the
  // same, the move on suggestedAxis is preferred so the engine honors the
  // minimum-penetration axis the geometry chose.
  const candidate = buildResolutionCandidate(collision);
  const preferRowDropOnTie = candidate.suggestedAxis === "y";

  const options: MoveOption[] = [];

  // Horizontal nudges are generated ONLY for label-vs-artwork collisions. A
  // label-vs-label collision is resolved with a row drop (when avoiding artwork
  // reintroduces a label-label overlap, resolve with a row drop); this preserves
  // the horizontal separation the per-zone stagger already established and prevents
  // one label's sideways nudge from sliding onto a zone neighbor. Nudges are also
  // disabled under full containment, where a single interval step cannot clear the
  // overlap.
  if (pick.isArtwork && !contained) {
    // Slide left so the label's right edge sits just left of the obstacle.
    const leftX = o.x - self.half - 1e-6;
    options.push({
      kind: "nudge-x",
      newX: leftX,
      newY: self.y,
      cost: Math.abs(leftX - self.x),
      inZone: labelFitsX(leftX, self.half, self.zone, zonePad),
    });
    // Slide right so the label's left edge sits just right of the obstacle.
    const rightX = o.x + o.w + self.half + 1e-6;
    options.push({
      kind: "nudge-x",
      newX: rightX,
      newY: self.y,
      cost: Math.abs(rightX - self.x),
      inZone: labelFitsX(rightX, self.half, self.zone, zonePad),
    });
  }

  // Enumerate the vertical row-step candidates, direction-aware. The label's
  // placementMode sets the NATURAL side: a bottom label steps DOWN (toward the
  // padded floor, away from the object above it), a top label steps UP (toward the
  // padded top, away from the object below it). The natural candidate is always
  // generated. The MIRRORED (against-mode) candidate is generated ONLY as a
  // fallback when the natural one does not fit in the zone -- this is the
  // no-room-above case (a top label clamped at the ceiling drops DOWN past the
  // obstacle) and its symmetric no-room-below case. Generating the mirror only on a
  // blocked natural side keeps a bottom label with room below from being yanked UP
  // by a cheaper-distance up move, which Phase B's downward re-stagger would then
  // undo. Both candidates are bounded by their own zone edge.
  // DOWN candidate: new top edge sits just below the obstacle bottom.
  const downTargetTop = o.y + o.h + 1e-6;
  const downRaw = Math.max(self.rowStep, downTargetTop - self.y);
  const downSteps = Math.max(1, Math.ceil(downRaw / self.rowStep));
  const downY = self.y + downSteps * self.rowStep;
  const downOption: MoveOption = {
    kind: "row-drop",
    newX: self.x,
    newY: downY,
    cost: downY - self.y,
    inZone: downY <= bottomMax + 1e-9,
  };
  // UP candidate: new bottom edge (newY + lineH) sits just above the obstacle top,
  // so the new top edge is obstacle_top - lineH. Move in whole rowStep increments.
  const upTargetTop = o.y - self.lineH - 1e-6;
  const upRaw = Math.max(self.rowStep, self.y - upTargetTop);
  const upSteps = Math.max(1, Math.ceil(upRaw / self.rowStep));
  const upY = self.y - upSteps * self.rowStep;
  const upOption: MoveOption = {
    kind: "row-drop",
    newX: self.x,
    newY: upY,
    cost: self.y - upY,
    inZone: upY >= topMin - 1e-9,
  };
  const naturalOption = movesDown ? downOption : upOption;
  const mirrorOption = movesDown ? upOption : downOption;
  options.push(naturalOption);
  // Add the mirror only when the natural side cannot fit (no room on the natural
  // side), so the deterministic scorer falls back across the object exactly when
  // there is no other in-zone vertical escape.
  if (!naturalOption.inZone) options.push(mirrorOption);

  // Score each in-zone move by its distance PLUS the worst new label-label
  // penetration it would create against same-zone neighbors. This steers the
  // artwork nudge toward the direction (or a row drop) that does not slide the
  // label onto a neighbor; ties still respect the geometry's cheaper axis.
  const inZone = options
    .filter((m) => m.inZone && m.cost > 1e-9)
    .map((m) => scoreMove(m, self, zoneNeighbors));
  let chosen: ScoredMove | undefined = pickCheapest(inZone, preferRowDropOnTie);
  // A clearing move (from the enumerated, obstacle-clearing candidates) fully
  // clears the obstacle; the partial fallback below does not.
  let isPartialFallback = false;
  if (chosen === undefined) {
    // No clearing move fits. Apply a bounded partial: step to the label's OWN zone
    // edge if there is any room in its direction, which reduces a y-overlap without
    // exiting the zone. A bottom label steps to the padded floor (bottomMax); a top
    // label steps to the padded top (topMin).
    const edgeY = movesDown ? bottomMax : topMin;
    const partialCost = Math.abs(edgeY - self.y);
    if (partialCost > 1e-9) {
      chosen = {
        kind: "row-drop",
        newX: self.x,
        newY: edgeY,
        cost: partialCost,
        inZone: true,
        score: partialCost,
      };
      isPartialFallback = true;
    }
  }
  if (chosen === undefined) return false;

  const prevY = self.y;
  self.x = chosen.newX;
  self.y = chosen.newY;
  // A row step from the clearing candidates fully cleared the obstacle; only the
  // partial fallback (pinned to the label's own zone edge) may leave residual.
  const cleared = !isPartialFallback;
  // Name the move by the ACTUAL direction taken (a top label with no room above
  // may legitimately drop DOWN past the obstacle), not by the label's mode.
  const wentUp = chosen.newY < prevY - 1e-9;
  const edgeName = wentUp ? "zone top" : "zone floor";
  const stepVerb = wentUp ? "row rise" : "row drop";
  self.moves.push({
    target: moveTarget,
    kind: chosen.kind,
    magnitude: Number(chosen.cost.toFixed(3)),
    outcome:
      chosen.kind === "nudge-x"
        ? "nudged clear of " + overlapClass
        : cleared
          ? stepVerb + " clear of " + overlapClass
          : stepVerb +
            " clamped to " +
            edgeName +
            "; " +
            overlapClass +
            " overlap not fully cleared",
  });
  return true;
}

// A scored move: a MoveOption plus its selection score (move distance plus the
// worst new label-label penetration it would introduce against zone neighbors).
interface ScoredMove extends MoveOption {
  readonly score: number;
}

// Score a move: its travel cost plus the worst new label-label overlap depth the
// label would have against same-zone neighbors at the proposed position. The
// penalty steers an artwork nudge away from sliding the label onto a neighbor.
function scoreMove(m: MoveOption, self: LabelWork, zoneNeighbors: LabelWork[]): ScoredMove {
  // The label box at the proposed position.
  const moved: Aabb = { x: m.newX - self.half, y: m.newY, w: self.half * 2, h: self.lineH };
  let worstPenetration = 0;
  for (const n of zoneNeighbors) {
    if (n === self) continue;
    const c = detectCollision(moved, "L", labelAabb(n), "N");
    if (c !== null && c.overlapDepth > worstPenetration) worstPenetration = c.overlapDepth;
  }
  const scored: ScoredMove = { ...m, score: m.cost + worstPenetration };
  return scored;
}

// Pick the lowest-score move. On a score tie the preferred axis (from the
// geometry's suggestedAxis) wins: preferRowDrop true ranks row-drop first
// (geometry chose y), else nudge-x first (geometry chose x). Remaining ties break
// by (newY, newX) so the choice is fully deterministic.
function pickCheapest(options: ScoredMove[], preferRowDrop: boolean): ScoredMove | undefined {
  let best: ScoredMove | undefined;
  for (const m of options) {
    if (best === undefined) {
      best = m;
      continue;
    }
    if (m.score < best.score - 1e-9) {
      best = m;
      continue;
    }
    if (Math.abs(m.score - best.score) <= 1e-9) {
      const mRank = axisRank(m.kind, preferRowDrop);
      const bRank = axisRank(best.kind, preferRowDrop);
      if (mRank < bRank) best = m;
      else if (mRank === bRank && m.newY < best.newY - 1e-9) best = m;
      else if (mRank === bRank && Math.abs(m.newY - best.newY) <= 1e-9 && m.newX < best.newX - 1e-9)
        best = m;
    }
  }
  return best;
}

// Rank a move kind for tie-breaking. The geometry-preferred axis ranks 0.
function axisRank(kind: "nudge-x" | "row-drop", preferRowDrop: boolean): number {
  if (preferRowDrop) return kind === "row-drop" ? 0 : 1;
  return kind === "nudge-x" ? 0 : 1;
}

// Drift threshold (scene-percent) past which a clear label is flagged as far from
// its anchor. The label baseline is ~labelOffsetY below the anchor; a few rows of
// stagger is acceptable, so the threshold is generous (3 row steps) to avoid
// flagging normal de-overlap as poor alignment.
const POOR_ALIGNMENT_DRIFT_FACTOR = 3;
// A zone with at least this many labels that all needed a row drop is a dense but
// readable cluster worth an author review.
const OVERLOAD_ROW_DROP_COUNT = 4;

// Per-zone label-label de-overlap by distinct-row stagger (Phase B). Partitions
// the zone's labels by placement MODE and vertical depth tier, then ladders each
// group in its OWN direction (bottom labels DOWN toward the padded floor, top
// labels UP toward the padded top). The two modes and the already-separated tiers
// must never share a ladder. Only _labelY (via w.y) changes here; w.x is preserved
// so Phase A's artwork separation survives.
function restaggerZoneLabels(
  zoneLabels: LabelWork[],
  zone: Zone,
  zonePad: number,
  tolerance: number,
): void {
  if (zoneLabels.length < 2) return;
  const groups = new Map<string, LabelWork[]>();
  for (const w of zoneLabels) {
    const key = `${w.placementMode}:${depthTierOf(w.item)}`;
    const group = groups.get(key) ?? [];
    group.push(w);
    groups.set(key, group);
  }
  const orderedGroups = [...groups.values()].sort((a, b) => {
    const aPlacement = a[0]?.placementMode ?? "bottom";
    const bPlacement = b[0]?.placementMode ?? "bottom";
    if (aPlacement !== bPlacement) return aPlacement === "top" ? -1 : 1;
    return depthTierOf(a[0]!.item) - depthTierOf(b[0]!.item);
  });
  for (const group of orderedGroups) {
    // -1 ladders the top group UP, +1 ladders the bottom group DOWN.
    const direction = group[0]?.placementMode === "top" ? -1 : 1;
    restaggerGroup(group, zone, zonePad, tolerance, direction);
  }
}

// One placement group's distinct-row stagger, laddered in `direction`. Mirrors the
// legacy in-zone stagger: sort labels by current center-x (placement_name
// tiebreak), greedily assign each the lowest row whose last-placed label's right
// edge it clears, then map rows to a _labelY ladder by stepping AWAY from row 0 in
// `direction`. The per-row step is compressed when the natural spacing would push
// the deepest row past the group's own zone edge (the padded floor for a DOWN
// ladder, the padded top for an UP ladder), so every assigned row stays at a
// DISTINCT y instead of collapsing onto the edge. Row 0 keeps each label's current
// baseline, so a group whose labels do not overlap is left untouched.
function restaggerGroup(
  group: LabelWork[],
  zone: Zone,
  zonePad: number,
  tolerance: number,
  direction: StaggerDirection,
): void {
  if (group.length < 2) {
    // A lone label still records its row 0 so the classifier's same-row gate is
    // well-defined; w.row defaults to 0 already, so nothing to do.
    return;
  }
  // Stable order: ascending center-x, then placement_name.
  const ordered = [...group].sort((a, b) => {
    if (a.x !== b.x) return a.x - b.x;
    return a.item.placement_name.localeCompare(b.item.placement_name);
  });

  // Greedy interval-graph row assignment. rowRightEdges[r] is the right edge of
  // the last label placed in row r; a label fits in row r when its left edge
  // clears that right edge (within tolerance). Lowest fitting row wins.
  const rowRightEdges: number[] = [];
  const rowOf = new Map<string, number>();
  let maxRow = 0;
  for (const w of ordered) {
    const leftEdge = w.x - w.half;
    const rightEdge = w.x + w.half;
    let row = 0;
    while (row < rowRightEdges.length) {
      const edge = rowRightEdges[row];
      if (edge === undefined || leftEdge >= edge - tolerance) break;
      row++;
    }
    rowRightEdges[row] = rightEdge;
    rowOf.set(w.item.placement_name, row);
    w.row = row; // record the assigned row for the end-state classifier
    if (row > maxRow) maxRow = row;
  }
  if (maxRow === 0) return; // No label-label overlap: leave _labelY as is.

  // Map row index to a _labelY. Row 0 keeps each label's current baseline; deeper
  // rows step by the staggered amount in `direction`, compressed uniformly so the
  // deepest row lands inside the group's own padded zone edge.
  let maxLineCount = 1;
  for (const w of ordered) {
    const r = rowOf.get(w.item.placement_name) ?? 0;
    if (r > 0) maxLineCount = Math.max(maxLineCount, Math.max(1, w.item._labelLines.length));
  }
  const naturalStep = (group[0]?.rowStep ?? 0) * maxLineCount;
  // FRAME SAFETY: reserve the deepest label's height so the ladder stays inside
  // the padded zone. DOWN clamps the deepest BOTTOM edge at the padded floor; UP
  // clamps the deepest TOP edge (_labelY) at the padded top.
  const labelHeight = (group[0]?.rowStep ?? 0) * maxLineCount;
  // Clamp against the COMPUTED band (reflow-zones output) the group shares, not the
  // authored zone bounds. Every label in this group is in the same zone (the caller
  // partitions per zone), so they share band edges; read them from the first member
  // and fall back to the authored bounds when no band was produced.
  const bandBottom = group[0]?.bandBottom ?? zone.bounds.bottom;
  const bandTop = group[0]?.bandTop ?? zone.bounds.top;
  const bottomClamp = bandBottom - zonePad - labelHeight;
  const topClamp = bandTop + zonePad;
  // Row 0's reference y is the smallest y in the group for a DOWN ladder (the
  // topmost label, which never moves down) and the largest y for an UP ladder (the
  // bottommost label, which never moves up). Deeper rows ladder AWAY from it.
  let rowZeroY = ordered[0]?.y ?? 0;
  for (const w of ordered) {
    if (direction === 1) {
      if (w.y < rowZeroY) rowZeroY = w.y;
    } else if (w.y > rowZeroY) rowZeroY = w.y;
  }
  let step = naturalStep;
  if (direction === 1) {
    const naturalBottom = rowZeroY + maxRow * naturalStep;
    if (naturalBottom > bottomClamp) {
      const available = bottomClamp - rowZeroY;
      step = available > 0 ? available / maxRow : 0;
    }
  } else {
    const naturalTop = rowZeroY - maxRow * naturalStep;
    if (naturalTop < topClamp) {
      const available = rowZeroY - topClamp;
      step = available > 0 ? available / maxRow : 0;
    }
  }
  // Place each deeper-row label at the FARTHER of (a) the laddered y for its row
  // and (b) its OWN current y. Taking the farther position preserves a Phase A
  // artwork drop (a label pushed well past the obstacle keeps its own deeper y
  // instead of being yanked back to the shared ladder) and makes the pass
  // idempotent: a label already at or beyond its ladder slot does not move on a
  // second resolve. "Farther" means larger y for a DOWN ladder, smaller y for UP.
  for (const w of ordered) {
    const row = rowOf.get(w.item.placement_name) ?? 0;
    if (row === 0) continue;
    const ladderY = direction === 1 ? rowZeroY + row * step : rowZeroY - row * step;
    w.y = direction === 1 ? Math.max(ladderY, w.y) : Math.min(ladderY, w.y);
  }
}

// Run the global label de-overlap over the per-zone labelled maps. Mutates each
// item's _labelX / _labelY in place to clear label-vs-artwork and label-vs-label
// overlaps, then returns severity diagnostics for the end-state classification.
// This is the resolve-collisions phase's label work; it reads object artwork
// boxes (which are NOT moved) and writes only label coordinates.
export function resolveLabelCollisions(
  labelled: Map<string, ComputedItem[]>,
  zones: Zone[],
  sceneName: string,
  diagnostics: Diagnostics = [],
  config: LayoutConfig = buildGlobalDefaults(),
  zoneBands?: Map<string, ComputedZoneBand>,
): SeverityDiagnostic[] {
  const avgCharWidthPct = config.avgCharWidthPct;
  const lineHeightPct = config.labelLineHeightPct;
  const labelZonePadding = config.spacing.labelZonePadding;
  const maxPasses = config.labelMaxResolvePasses;
  const tolerance = config.labelCollisionTolerance;
  // The scene-resolved label tunables config folds in (label_offset_y and the
  // scene label_placement default both layer in via resolve_config). These let
  // the resolver reconstruct each label's IDEAL UNCLAMPED seed Y -- the y the
  // seed formula in layoutLabels would produce with no zone-edge clamp and no
  // stagger -- so anchorY measures drift against the ideal, not the clamped seed.
  const labelOffsetY = config.labelOffsetY;
  const sceneLabelPlacement = config.labelPlacement;

  // Build one global work list of movable labels plus the immutable artwork
  // obstacle list. A label is keyed to its owning zone for bounds clamping.
  const labels: LabelWork[] = [];
  const artBoxes: { id: string; box: Aabb; owner: string }[] = [];
  for (const zone of zones) {
    const items = labelled.get(zone.id) ?? [];
    // The vertical clamp band for this zone: the computed reflow band when present,
    // else the authored zone bounds. Each label carries it so its moves and the
    // per-zone re-stagger clamp against the REFLOWED band.
    const band = verticalBandFor(zone, zoneBands);
    for (const it of items) {
      artBoxes.push({
        id: "A:" + it.placement_name,
        box: artworkAabb(it),
        owner: it.placement_name,
      });
      const half = effectiveLabelHalfWidth(it._labelLines, it.layout.label_width, avgCharWidthPct);
      const lineH = lineHeightPct * Math.max(1, it._labelLines.length);
      // Resolve placement the same way layoutLabels did: per-placement override,
      // then the scene default config already folded in. config.labelPlacement
      // covers the scene layout_rules layer, so no separate layoutRules term.
      const placementMode = it.layout.label_placement ?? sceneLabelPlacement;
      // Ideal UNCLAMPED seed Y (label TOP edge), mirroring the layoutLabels seed
      // formula BEFORE its band clamp: bottom seeds labelOffsetY below the object's
      // ART bottom (_top + _height), top seeds the label's own height above the
      // object top. Using the object art bottom (not _baselineY) keeps this anchor
      // consistent with the layoutLabels bottom seed for every anchor mode (for a
      // bottom-anchored object _baselineY equals the art bottom, but a center/tip
      // anchor's _baselineY is the art center, which would seed onto the art). This
      // is the anchor the drift classifier measures against.
      const idealLabelHeight = lineHeightPct * Math.max(1, it._labelLines.length);
      const objectBottom = it._top + it._height;
      const idealSeedY =
        placementMode === "bottom"
          ? objectBottom + labelOffsetY
          : it._top - labelOffsetY - idealLabelHeight;
      labels.push({
        item: it,
        zoneId: zone.id,
        zone,
        bandTop: band.top,
        bandBottom: band.bottom,
        half,
        lineH,
        x: it._labelX,
        y: it._labelY,
        anchorX: it._centerX,
        anchorY: idealSeedY,
        rowStep: lineHeightPct,
        placementMode,
        row: 0,
        moves: [],
      });
    }
  }

  // Deterministic sweep order: ascending _labelX, then placement_name. Sort once;
  // the order is stable across passes because we never re-sort on mutated x.
  labels.sort((a, b) => {
    if (a.x !== b.x) return a.x - b.x;
    return a.item.placement_name.localeCompare(b.item.placement_name);
  });

  // Same-zone neighbor lists, so an artwork move can be scored by the new
  // label-label overlap it would create against its own zone's labels.
  const neighborsByZone = new Map<string, LabelWork[]>();
  for (const w of labels) {
    const list = neighborsByZone.get(w.zoneId) ?? [];
    list.push(w);
    neighborsByZone.set(w.zoneId, list);
  }

  // ----- Phase A: label-vs-artwork avoidance (global) -----
  // Each pass visits every label in order and clears its deepest neighboring
  // artwork overlap with a single move (x-nudge preferred, bounded row drop
  // fallback) chosen to introduce the least new label-label overlap. Artwork
  // boxes never move. Stop early when a whole pass makes no move, so clean scenes
  // do no work. This is the capability the legacy per-zone stagger lacked.
  for (let pass = 0; pass < maxPasses; pass++) {
    let moved = false;
    for (const self of labels) {
      const hit = deepestArtworkFor(self, artBoxes);
      if (hit === null) continue;
      const zoneNeighbors = neighborsByZone.get(self.zoneId) ?? [];
      const applied = applyLabelMove(self, hit, labelZonePadding, zoneNeighbors);
      if (applied) moved = true;
    }
    if (!moved) break;
  }

  // ----- Phase B: per-zone label-label de-overlap (row stagger) -----
  // Phase A may have nudged a label sideways onto a zone neighbor. Re-separate
  // label-label overlaps per zone with the proven distinct-row stagger: labels
  // whose horizontal extents overlap are placed in successive rows, and the row
  // step is compressed so the deepest row still lands above the padded zone floor.
  // A row drop is the only label-label move, so Phase A's horizontal artwork
  // separation is preserved. Run after Phase A so it stamps the final _labelY
  // ladder onto the artwork-adjusted x positions.
  for (const zone of zones) {
    const zoneLabels = labels.filter((w) => w.zoneId === zone.id);
    restaggerZoneLabels(zoneLabels, zone, labelZonePadding, tolerance);
  }

  // Write resolved coordinates back onto the items.
  for (const w of labels) {
    w.item._labelX = w.x;
    w.item._labelY = w.y;
  }

  // End-state classification. A label still overlapping anything after the budget
  // is an unresolved_label_overlap Error; a clear-but-drifted label is a
  // poor_label_alignment Warning; a zone whose labels all needed row drops yet are
  // all clear is a possible_overload Review.
  const severityDiagnostics: SeverityDiagnostic[] = [];
  const driftThreshold = POOR_ALIGNMENT_DRIFT_FACTOR * lineHeightPct;
  const rowDroppedByZone = new Map<string, number>();

  for (let i = 0; i < labels.length; i++) {
    const self = labels[i];
    if (self === undefined) continue;
    const hit = deepestAnyFor(i, labels, artBoxes);
    const stillOverlaps = hit !== null && hit.collision.overlapDepth > tolerance;

    if (stillOverlaps) {
      const c = hit.collision;
      const zone = self.zone;
      const zoneArea =
        (zone.bounds.right - zone.bounds.left) * (zone.bounds.bottom - zone.bounds.top);
      // Overlap area approximates the penetration rectangle on the minimum axis.
      const overlapArea =
        c.overlapAxis === "x" ? c.overlapDepth * self.lineH : c.overlapDepth * (self.half * 2);
      const otherName = hit.isArtwork
        ? hit.otherId.replace(/^A:/, "")
        : hit.otherId.replace(/^L:/, "");
      const payload = buildActionablePayload({
        scene: sceneName,
        zone: zone.id,
        involvedItems: [self.item.placement_name, otherName],
        remainingOverlapDepth: Number(c.overlapDepth.toFixed(2)),
        remainingOverlapArea: Number(Math.max(0, overlapArea).toFixed(2)),
        availableArea: Number(zoneArea.toFixed(2)),
        attemptedMoves: self.moves,
        suggestedFix: "reduce labels, enlarge the zone, or shorten labels",
      });
      const diagnostic = buildDiagnostic(
        "unresolved_label_overlap",
        { scene_name: sceneName, zone_name: zone.id, placement_name: self.item.placement_name },
        payload,
      );
      severityDiagnostics.push(diagnostic);
      continue;
    }

    // Clear label: count row drops per zone (for the overload review) and flag
    // drift past the threshold.
    const rowDrops = self.moves.filter((m) => m.kind === "row-drop").length;
    if (rowDrops > 0) {
      rowDroppedByZone.set(self.zoneId, (rowDroppedByZone.get(self.zoneId) ?? 0) + 1);
    }
    const drift = Math.abs(self.y - self.anchorY) + Math.abs(self.x - self.anchorX);
    if (drift > driftThreshold) {
      // Surface the CAUSE of the drift so one reused code stays interpretable.
      // When the resolver applied no move, the label sits where layoutLabels left
      // it: the seed-level zone-edge clamp displaced it from its ideal anchor
      // (clamp drift). When the resolver moved it, those moves displaced it
      // (collision displacement). Either way the label is clear of overlaps; the
      // Warning just reports it is far from where it ideally wants to be.
      const cause =
        self.moves.length === 0
          ? "clamp drift: held at zone edge by the seed clamp, no collision move applied"
          : "collision displacement: moved clear of a label/artwork overlap";
      const causeMoves: AttemptedMove[] =
        self.moves.length === 0
          ? [
              {
                target: self.item.placement_name,
                kind: "row-drop",
                magnitude: Number(drift.toFixed(3)),
                outcome: cause,
              },
            ]
          : self.moves;
      // poor_label_alignment is a Warning, not an overlap Error, so the structured
      // numbers describe the DRIFT (how far the label sits from its ideal anchor),
      // not an overlap. remainingOverlapDepth carries the drift distance (always
      // positive here) so the payload stays a meaningful, fixable record.
      const zone = self.zone;
      const zoneArea =
        (zone.bounds.right - zone.bounds.left) * (zone.bounds.bottom - zone.bounds.top);
      const driftPayload = buildActionablePayload({
        scene: sceneName,
        zone: self.zoneId,
        involvedItems: [self.item.placement_name],
        remainingOverlapDepth: Number(drift.toFixed(2)),
        remainingOverlapArea: 0,
        availableArea: Number(zoneArea.toFixed(2)),
        attemptedMoves: causeMoves,
        suggestedFix: "tune label_offset_y or zone density",
      });
      const diagnostic = buildDiagnostic(
        "poor_label_alignment",
        {
          scene_name: sceneName,
          zone_name: self.zoneId,
          placement_name: self.item.placement_name,
        },
        driftPayload,
      );
      severityDiagnostics.push(diagnostic);
    }
  }

  // A zone where many labels each needed a row drop yet all came out clear is a
  // dense-but-readable cluster: one Review-required possible_overload per zone.
  for (const [zoneId, count] of [...rowDroppedByZone.entries()].sort((a, b) =>
    a[0].localeCompare(b[0]),
  )) {
    if (count >= OVERLOAD_ROW_DROP_COUNT) {
      const diagnostic = buildDiagnostic("possible_overload", {
        scene_name: sceneName,
        zone_name: zoneId,
      });
      severityDiagnostics.push(diagnostic);
    }
  }

  // Echo an info-level runtime diagnostic per resolved zone so the legacy stream
  // records that the global pass ran (keeps existing tooling consistent without a
  // new closed kind: reuse label_row_staggered for any label this pass dropped).
  for (const w of labels) {
    const droppedRows = w.moves.filter((m) => m.kind === "row-drop").length;
    if (droppedRows > 0) {
      diagnostics.push({
        stage: "labels",
        severity: "info",
        kind: "label_row_staggered",
        zone: w.zoneId,
        placement_name: w.item.placement_name,
        staggered_row: droppedRows,
      });
    }
  }

  return severityDiagnostics;
}
