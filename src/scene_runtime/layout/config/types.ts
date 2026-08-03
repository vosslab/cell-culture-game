// LayoutConfig type hierarchy. Ratified contract:
// docs/archive/decisions/layout_model_layer_synthesis.md "Config hierarchy".
//
// All values are scene-percent unless a comment states otherwise. The config is
// the single home for every layout tunable that was previously read from a
// direct `constants.ts` import inside a stage file. Stages read tunables through
// LayoutConfig; constants.ts keeps the canonical default values that
// buildGlobalDefaults() copies into the global-defaults config.
//
import type { AlignMode, AlignStop, LabelPlacement } from "../types.js";

//============================================
// Spacing (margin-based, scene-percent)
//============================================

export interface SpacingConfig {
  // Gap between objects in a row (previously layout_rules.zone_gap / `?? 2`).
  readonly objectGap: number;
  // Gap reserved between labels during de-overlap (label-axis spacing).
  readonly labelGap: number;
  // Inset from zone edges used by horizontal object placement (was ZONE_PADDING).
  readonly objectZonePadding: number;
  // Inset from zone edges used by label placement / stagger (was ZONE_PADDING).
  readonly labelZonePadding: number;
}

//============================================
// Packer config (defaults live here; resolve_config.ts layers scene overrides)
//============================================

export interface PackerConfig {
  // Required row scale below which the packer is preferred over uniform shrink.
  readonly thresholdScale: number; // PACKER_THRESHOLD_SCALE, default 0.75
  readonly minScale: number; // MIN_SCALE floor, 0.55 today
}

//============================================
// Per-zone override subset
//============================================

// The subset a per-zone override may set. Drawn from existing Zone schema
// fields (align, baseline) plus a sparse spacing override; never new authored
// keys. align/baseline are optional because a zone may set neither.
export interface ZoneLayoutConfig {
  readonly align?: AlignMode; // existing Zone.align enum
  readonly baseline?: number; // existing Zone.baseline
  readonly spacing?: Partial<SpacingConfig>;
}

//============================================
// Top-level resolved config
//============================================

export interface LayoutConfig {
  readonly spacing: SpacingConfig;
  readonly packer: PackerConfig;

  // Convergence loop.
  readonly maxPasses: number; // MAX_LAYOUT_PASSES, 3 today
  readonly shrinkFactor: number; // LAYOUT_SHRINK_FACTOR, 0.9 today

  // Label sizing / placement tunables.
  readonly labelFontSize: number; // authored default (DEFAULT_LAYOUT_RULES.label_font_size)
  readonly labelLineHeight: number; // authored default (DEFAULT_LAYOUT_RULES.label_line_height)
  readonly labelOffsetY: number; // canonical 3.5 (see header note)
  // Default label placement when neither a placement nor scene rule authors one.
  readonly labelPlacement: LabelPlacement; // "top" by default

  readonly labelLineHeightPct: number; // staggered row height per line (LABEL_LINE_HEIGHT_PCT)
  readonly avgCharWidthPct: number; // glyph-advance fraction (AVG_CHAR_WIDTH_PCT)
  readonly labelFontWidthFraction: number; // LABEL_FONT_WIDTH_FRACTION
  readonly labelFontMinPx: number; // LABEL_FONT_MIN_PX
  readonly labelCollisionTolerance: number; // shared 0.3 (see header note)
  readonly labelNudgePasses: number; // horizontal nudge pass count (was `< 3`)
  // Global label de-overlap pass budget (resolve-collisions phase). Fixed
  // small budget so the sweep is bounded and deterministic.
  readonly labelMaxResolvePasses: number;
  readonly wrapBudgetTolerance: number; // wrap budget slack multiplier (was * 1.1)

  // Footprint tunable (object-side; default lives here, strategy reads it).
  readonly maxFootprintRatio: number; // MAX_FOOTPRINT_RATIO

  // Vertical tunables.
  readonly aspectFloor: number; // Math.max(0.01, aspect) floor

  // Default tab-stop bucket for items lacking align_stop.
  readonly defaultAlignStop: AlignStop;

  // Per-zone overrides resolved from Zone fields; sparse, keyed by zone id.
  readonly zoneOverrides: Readonly<Record<string, ZoneLayoutConfig>>;
}
