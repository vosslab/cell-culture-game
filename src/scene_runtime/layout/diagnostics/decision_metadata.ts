// Per-scene decision metadata. Ratified contract:
//   docs/archive/decisions/layout_model_layer_synthesis.md
//   ("Decision metadata") and plan partitioned-shimmying-dragonfly.md
//   ("Decision metadata (elkjs logging discipline)").
//
// The build emits per-scene decision metadata beside generated/precomputed_layout.ts,
// SEPARATE from the typed diagnostic stream. The scorecard and the AI reviewer
// read this metadata; diagnostics stay the severity-graded problem stream.
//
// The engine records one ZoneDecision per zone: which placement strategy was
// selected (row or pack), packer attempted/result, per-item shrink applied,
// rows created, and the resolved config. Both builders exist: row zones use
// buildRowZoneDecision; pack zones use buildPackZoneDecision. The horizontal
// layout dispatcher selects the strategy per zone and fills the appropriate
// decision.

import type { LayoutConfig } from "../config/index.js";

//============================================
// Per-zone decision
//============================================

// What the engine decided for one zone. Mirrors the elkjs option/result logging
// discipline: record the selected strategy, the packer trigger and result, the
// shrink applied per item, the rows created, the resolved config, and any
// unresolved constraints.
export interface ZoneDecision {
  readonly zoneId: string;
  // The placement strategy the engine selected for this zone.
  // "row" is the default greedy single-row strategy; "pack" is the overflow packer.
  readonly selectedStrategy: "row" | "pack";
  // The uniform scale the row layout required. 1 means no shrink was needed.
  readonly requiredRowScale: number;
  // The configured packer threshold (config.packer.thresholdScale) at decision
  // time, recorded so the trigger is auditable.
  readonly packerThreshold: number;
  // Whether the packer was attempted (requiredRowScale < threshold or overflow).
  readonly packerAttempted: boolean;
  // The packer outcome. "not-needed" when the row strategy sufficed.
  readonly packerResult: "not-needed" | "fit" | "unresolved";
  // The number of rows the engine created for this zone (1 for the row default).
  readonly rowsCreated: number;
  // Per-item shrink actually applied, keyed by placement_name. 1 means no shrink.
  readonly shrinkApplied: Readonly<Record<string, number>>;
  // The effective resolved LayoutConfig for this zone.
  readonly resolvedConfig: LayoutConfig;
  // Constraints the engine could not satisfy, mirroring emitted Error codes by
  // code string. Empty when the zone resolved cleanly.
  readonly unresolvedConstraints: readonly string[];
}

//============================================
// Per-scene metadata
//============================================

// The decision metadata for one scene: its name plus one decision per zone.
export interface DecisionMetadata {
  readonly sceneName: string;
  readonly zones: readonly ZoneDecision[];
}

//============================================
// Builders
//============================================

// Build a ZoneDecision for a zone the row strategy handled. Records the row
// strategy, requiredRowScale 1 (no shrink beyond the convergence loop),
// packer not attempted, a single row, and the per-item shrink the convergence
// loop applied. shrinkApplied is supplied by the caller; unresolvedConstraints
// is supplied from the zone's emitted Error codes, defaulting to empty.
export function buildRowZoneDecision(input: {
  zoneId: string;
  resolvedConfig: LayoutConfig;
  shrinkApplied?: Readonly<Record<string, number>>;
  unresolvedConstraints?: readonly string[];
}): ZoneDecision {
  // Assemble the full record, then return it.
  const decision: ZoneDecision = {
    zoneId: input.zoneId,
    selectedStrategy: "row",
    requiredRowScale: 1,
    packerThreshold: input.resolvedConfig.packer.thresholdScale,
    packerAttempted: false,
    packerResult: "not-needed",
    rowsCreated: 1,
    shrinkApplied: input.shrinkApplied ?? {},
    resolvedConfig: input.resolvedConfig,
    unresolvedConstraints: input.unresolvedConstraints ?? [],
  };
  return decision;
}

// Build a ZoneDecision for a zone the overflow packer handled. The dispatcher
// probed the row layout's required scale, engaged the packer, and recorded its
// outcome (selected strategy "pack", required row scale, threshold, result,
// rows, and per-item shrink); this assembles that into the ZoneDecision shape.
// unresolvedConstraints carries "unresolved_overlap" when the packer could not
// fit even at MIN_SCALE.
export function buildPackZoneDecision(input: {
  zoneId: string;
  resolvedConfig: LayoutConfig;
  requiredRowScale: number;
  packerResult: "fit" | "unresolved";
  rowsCreated: number;
  shrinkApplied: Readonly<Record<string, number>>;
}): ZoneDecision {
  const unresolved = input.packerResult === "unresolved" ? ["unresolved_overlap"] : [];
  const decision: ZoneDecision = {
    zoneId: input.zoneId,
    selectedStrategy: "pack",
    requiredRowScale: input.requiredRowScale,
    packerThreshold: input.resolvedConfig.packer.thresholdScale,
    packerAttempted: true,
    packerResult: input.packerResult,
    rowsCreated: input.rowsCreated,
    shrinkApplied: input.shrinkApplied,
    resolvedConfig: input.resolvedConfig,
    unresolvedConstraints: unresolved,
  };
  return decision;
}

// Build a per-scene DecisionMetadata from its zone decisions.
export function buildDecisionMetadata(
  sceneName: string,
  zones: readonly ZoneDecision[],
): DecisionMetadata {
  const metadata: DecisionMetadata = { sceneName, zones: [...zones] };
  return metadata;
}
