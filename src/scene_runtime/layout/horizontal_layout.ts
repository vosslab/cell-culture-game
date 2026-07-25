// Stage 7: Horizontal layout per zone (dispatcher).
//
// Resolves the shared per-call context (gap, floor scale, zone padding) once,
// then selects a PlacementStrategy per zone and delegates placement to it.
// Two strategies exist: the row strategy (default greedy single-row placement)
// and the overflow packer (non-uniform shrink plus gap compaction).
//
// Per-zone strategy selection: probe the row layout's required uniform scale
// and overflow without placing anything; engage the packer when the row layout
// would require unacceptable shrink (requiredScale < config.packer.thresholdScale)
// OR overflows (negative gap / out of bounds). Otherwise the row strategy runs.
// See docs/active_plans/decisions/layout_model_layer_synthesis.md
// "Packer objective and trigger" for the ratified trigger rule.

import { buildGlobalDefaults } from "./config/index.js";
import { packStrategy, probeRow, rowStrategy } from "./strategies/index.js";
import type { LayoutConfig } from "./config/index.js";
import type { SeverityDiagnostic } from "./diagnostics/index.js";
import type { PackerZoneOutcome, PackingCost } from "./strategies/index.js";
import type { PlacementStrategy, StrategyContext } from "./strategies/index.js";
import type { ComputedItem, Diagnostics, LayoutRules, ScaledPlacement, Zone } from "./types.js";

// The result of selecting a strategy for one zone: the strategy plus the row
// probe numbers (so the dispatcher can record requiredRowScale even when it
// dispatches the packer).
interface StrategyChoice {
  strategy: PlacementStrategy;
  requiredRowScale: number;
  packerEngaged: boolean;
}

// Selects the placement strategy for a zone. Probes the row layout;
// engages the packer when the row layout would require unacceptable shrink
// (below config.packer.thresholdScale) or overflows. Tab-stop and single-row
// modes both probe; an empty zone or a comfortably-fitting zone keeps the row
// strategy.
function selectStrategy(
  zone: Zone,
  items: ScaledPlacement[],
  ctx: StrategyContext,
): StrategyChoice {
  const probe = probeRow(items, zone, ctx.gap, ctx.zonePadding, ctx.minScale);
  const threshold = ctx.config.packer.thresholdScale;
  // Positive trigger: unacceptable shrink OR overflow engages the packer.
  const packerNeeded = probe.requiredScale < threshold || probe.overflow;
  if (packerNeeded) {
    return { strategy: packStrategy, requiredRowScale: probe.requiredScale, packerEngaged: true };
  }
  return { strategy: rowStrategy, requiredRowScale: probe.requiredScale, packerEngaged: false };
}

// A depth tier is a vertical row, not another member of the same horizontal
// row. Keep this partition here, at the horizontal control layer, so the row
// probe and overflow packer measure exactly the content that will share an x
// axis. Names remain opaque: they provide only the stable tie-break within a
// declared numeric tier.
function partitionByDepthTier(items: ScaledPlacement[]): ScaledPlacement[][] {
  const byTier = new Map<number, ScaledPlacement[]>();
  for (const item of items) {
    const tier = item.depth_tier ?? 0;
    const tierItems = byTier.get(tier);
    if (tierItems === undefined) byTier.set(tier, [item]);
    else tierItems.push(item);
  }
  return [...byTier.entries()]
    .sort(([left], [right]) => left - right)
    .map(([, tierItems]) =>
      [...tierItems].sort((left, right) => left.placement_name.localeCompare(right.placement_name)),
    );
}

function worstPackingCost(outcomes: PackerZoneOutcome[]): PackingCost {
  return outcomes.reduce<PackingCost>(
    (worst, outcome) => ({
      primaryWeightedShrinkPct: Math.max(
        worst.primaryWeightedShrinkPct,
        outcome.cost.primaryWeightedShrinkPct,
      ),
      orderViolations: Math.max(worst.orderViolations, outcome.cost.orderViolations),
      gapDeficit: Math.max(worst.gapDeficit, outcome.cost.gapDeficit),
      overhang: Math.max(worst.overhang, outcome.cost.overhang),
    }),
    { primaryWeightedShrinkPct: 0, orderViolations: 0, gapDeficit: 0, overhang: 0 },
  );
}

export function horizontalLayout(
  groups: Map<string, ScaledPlacement[]>,
  zones: Zone[],
  layoutRules: LayoutRules = {},
  diagnostics: Diagnostics = [],
  config: LayoutConfig = buildGlobalDefaults(),
  sinks: {
    sceneName?: string;
    packerSink?: Map<string, PackerZoneOutcome>;
    severitySink?: SeverityDiagnostic[];
  } = {},
): Map<string, ComputedItem[]> {
  const result = new Map<string, ComputedItem[]>();
  // Object spacing and the floor scale now resolve through LayoutConfig. The
  // authored layout_rules.zone_gap still wins when set; otherwise the resolved
  // config's objectGap (canonically 2) applies.
  const gap = layoutRules.zone_gap ?? config.spacing.objectGap;
  const minScale = config.packer.minScale;
  const zonePadding = config.spacing.objectZonePadding;

  for (const zone of zones) {
    const items = groups.get(zone.id) ?? [];
    const tierRows = partitionByDepthTier(items);
    const placed: ComputedItem[] = [];
    const packedOutcomes: PackerZoneOutcome[] = [];
    const requiredRowScales: number[] = [];

    for (const tierItems of tierRows) {
      // The shared per-call context is recreated per tier because the packer
      // writes one outcome per call. The dispatcher aggregates those outcomes
      // back to the original zone after every vertical row has been placed.
      const ctx: StrategyContext = { gap, minScale, zonePadding, config, diagnostics };
      if (sinks.sceneName !== undefined) ctx.sceneName = sinks.sceneName;
      if (sinks.severitySink !== undefined) ctx.severitySink = sinks.severitySink;
      const choice = selectStrategy(zone, tierItems, ctx);
      requiredRowScales.push(choice.requiredRowScale);
      ctx.requiredRowScale = choice.requiredRowScale;

      if (choice.packerEngaged) {
        const tierPackerSink = new Map<string, PackerZoneOutcome>();
        ctx.packerSink = tierPackerSink;
        placed.push(...choice.strategy(tierItems, zone, ctx));
        const outcome = tierPackerSink.get(zone.id);
        if (outcome !== undefined) packedOutcomes.push(outcome);
      } else {
        placed.push(...choice.strategy(tierItems, zone, ctx));
      }
    }

    if (packedOutcomes.length > 0 && sinks.packerSink !== undefined) {
      const shrinkApplied: Record<string, number> = {};
      for (const item of placed) shrinkApplied[item.placement_name] = item._scale;
      sinks.packerSink.set(zone.id, {
        zoneId: zone.id,
        selectedStrategy: "pack",
        requiredRowScale: Math.min(...requiredRowScales),
        packerThreshold: config.packer.thresholdScale,
        packerAttempted: true,
        packerResult: packedOutcomes.some((outcome) => outcome.packerResult === "unresolved")
          ? "unresolved"
          : "fit",
        rowsCreated: tierRows.length,
        shrinkApplied,
        cost: worstPackingCost(packedOutcomes),
      });
    }
    result.set(zone.id, placed);
  }

  return result;
}
