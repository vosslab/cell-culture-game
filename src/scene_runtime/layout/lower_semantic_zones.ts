// Semantic-zone lowering is the boundary between authored scene meaning and
// renderer geometry. Source-zone names are opaque identifiers: declaration
// order and measured placement demand, never spelling, determine the plan.

import {
  DEFAULT_SCENE_BOUNDS,
  DEFAULT_VIEWPORT,
  DEPTH_TIER_GAP,
  LABEL_LINE_HEIGHT_PCT,
  ZONE_PADDING,
} from "./constants.js";
import { footprintFor, visualWidthFor } from "./footprint.js";
import type { Bounds, ResolvedScene, ScaledPlacement, SceneA, SourceZone, Zone } from "./types.js";

interface ZoneDemand {
  zone: SourceZone;
  width: number;
  height: number;
}

interface PlannedRow {
  zones: ZoneDemand[];
  width: number;
  height: number;
}

function cloneBounds(bounds: Bounds): Bounds {
  return { ...bounds };
}

function hasLegacyGeometry(scene: SceneA): boolean {
  return scene.scene_bounds !== undefined && scene.zones.every((zone) => zone.bounds !== undefined);
}

function labelLinesFor(placement: ScaledPlacement): number {
  // This is an early demand estimate, not a second label renderer. The later
  // measured-label phase remains authoritative for exact placement. It simply
  // reserves a deterministic extra line when a label cannot fit its authored
  // label-width budget at the shared average glyph advance.
  const labelCapacity = Math.max(1, placement.layout.label_width / 0.45);
  return Math.max(1, Math.ceil(placement.label.length / labelCapacity));
}

function heightFor(placement: ScaledPlacement): number {
  const viewportAspect = DEFAULT_VIEWPORT.w / DEFAULT_VIEWPORT.h;
  const artHeight = (visualWidthFor(placement) * viewportAspect) / Math.max(placement.aspect, 0.01);
  return artHeight + 4 + labelLinesFor(placement) * LABEL_LINE_HEIGHT_PCT;
}

function demandFor(
  zone: SourceZone,
  placements: readonly ScaledPlacement[],
  gap: number,
): ZoneDemand {
  const assigned = placements.filter(
    (placement) => placement.active !== false && placement.zone === zone.id,
  );
  if (assigned.length === 0) return { zone, width: 2 * ZONE_PADDING, height: 2 * ZONE_PADDING };

  const tierWidths = new Map<number, { width: number; count: number }>();
  const tiers = new Map<number, number>();
  for (const placement of assigned) {
    const tier = placement.depth_tier ?? 0;
    const horizontal = tierWidths.get(tier) ?? { width: 0, count: 0 };
    horizontal.width += footprintFor(placement);
    horizontal.count += 1;
    tierWidths.set(tier, horizontal);
    tiers.set(tier, Math.max(tiers.get(tier) ?? 0, heightFor(placement)));
  }
  // Depth tiers stack vertically, so their row widths compete by maximum rather
  // than sum. Objects inside one tier share a horizontal row and retain the
  // configured inter-placement gap.
  const width =
    Math.max(
      ...[...tierWidths.values()].map((tier) => tier.width + Math.max(0, tier.count - 1) * gap),
    ) +
    2 * ZONE_PADDING;
  const height =
    [...tiers.values()].reduce((total, tierHeight) => total + tierHeight, 0) +
    Math.max(0, tiers.size - 1) * DEPTH_TIER_GAP +
    2 * ZONE_PADDING;
  return { zone, width, height };
}

function planRows(demands: ZoneDemand[], availableWidth: number, gap: number): PlannedRow[] {
  const rows: PlannedRow[] = [];
  let current: PlannedRow = { zones: [], width: 0, height: 0 };
  for (const demand of demands) {
    // A demand wider than the workspace occupies a row by itself. The layout
    // phases then use their established shrink/overflow policy; no source-zone
    // coordinate workaround is invented here.
    const addedWidth = demand.width + (current.zones.length > 0 ? gap : 0);
    if (current.zones.length > 0 && current.width + addedWidth > availableWidth) {
      rows.push(current);
      current = { zones: [], width: 0, height: 0 };
    }
    current.zones.push(demand);
    current.width += addedWidth;
    current.height = Math.max(current.height, demand.height);
  }
  if (current.zones.length > 0) rows.push(current);
  return rows;
}

function lowerSemanticZones(scene: SceneA, placements: readonly ScaledPlacement[]): ResolvedScene {
  const scene_bounds = cloneBounds(scene.scene_bounds ?? DEFAULT_SCENE_BOUNDS);
  const gap = scene.layout_rules?.zone_gap ?? 2;
  const width = scene_bounds.right - scene_bounds.left;
  const height = scene_bounds.bottom - scene_bounds.top;
  const rows = planRows(
    scene.zones.map((zone) => demandFor(zone, placements, gap)),
    width,
    gap,
  );
  const totalRowHeight = rows.reduce((total, row) => total + row.height, 0);
  const verticalScale = totalRowHeight > 0 ? height / totalRowHeight : 1;
  const zones: Zone[] = [];
  let top = scene_bounds.top;

  for (const row of rows) {
    const rowHeight = row.height * verticalScale;
    const rowGapTotal = Math.max(0, row.zones.length - 1) * gap;
    const demandWidth = row.width - rowGapTotal;
    const slack = Math.max(0, width - row.width);
    let left = scene_bounds.left;
    for (let index = 0; index < row.zones.length; index += 1) {
      const demand = row.zones[index]!;
      const zoneWidth =
        row.width > width
          ? (demand.width * width) / demandWidth
          : demand.width + (slack * demand.width) / demandWidth;
      const right = left + zoneWidth;
      zones.push({
        id: demand.zone.id,
        ...(demand.zone.align === undefined ? {} : { align: demand.zone.align }),
        ...(demand.zone.label === undefined ? {} : { label: demand.zone.label }),
        bounds: { left, right, top, bottom: top + rowHeight },
        baseline: top + rowHeight - ZONE_PADDING,
      });
      left = right + (index === row.zones.length - 1 ? 0 : gap);
    }
    top += rowHeight;
  }

  return { ...scene, scene_bounds, zones };
}

/**
 * Produce a complete internal scene without mutating author input or scaled
 * placements. Fully coordinate-bearing legacy scenes keep their exact geometry
 * during migration; semantic scenes receive an object-aware flow plan.
 */
export function lowerSceneZones(
  scene: SceneA,
  placements: readonly ScaledPlacement[],
): ResolvedScene {
  if (!hasLegacyGeometry(scene)) return lowerSemanticZones(scene, placements);

  return {
    ...scene,
    scene_bounds: cloneBounds(scene.scene_bounds!),
    zones: scene.zones.map((zone): Zone => ({
      id: zone.id,
      ...(zone.align === undefined ? {} : { align: zone.align }),
      ...(zone.label === undefined ? {} : { label: zone.label }),
      bounds: cloneBounds(zone.bounds!),
      ...(zone.baseline === undefined ? {} : { baseline: zone.baseline }),
    })),
  };
}
