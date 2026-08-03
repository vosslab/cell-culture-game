// resolveConfig + buildGlobalDefaults. Ratified contract:
// docs/archive/decisions/layout_model_layer_synthesis.md "Config hierarchy".
//
// Precedence (lowest to highest):
//   global defaults -> scene layout_rules -> zone overrides ->
//   placement-derived values -> strategy-local options
//
// buildGlobalDefaults() copies the canonical default values out of constants.ts
// into a frozen LayoutConfig. resolveConfig() layers the four higher-precedence
// inputs on top and returns a frozen config. Both freeze their output so a stage
// cannot accidentally mutate a shared config.

import {
  ZONE_PADDING,
  MIN_SCALE,
  MAX_FOOTPRINT_RATIO,
  AVG_CHAR_WIDTH_PCT,
  MAX_LAYOUT_PASSES,
  LAYOUT_SHRINK_FACTOR,
  LABEL_FONT_WIDTH_FRACTION,
  LABEL_FONT_MIN_PX,
  LABEL_LINE_HEIGHT_PCT,
  DEFAULT_LAYOUT_RULES,
} from "../constants.js";
import type { LayoutRules, Zone } from "../types.js";
import type { LayoutConfig, SpacingConfig, ZoneLayoutConfig } from "./types.js";

// Tunables that have no named constant today but were inline literals in the
// stage files (per the tunable inventory). They keep their existing values so
// the resolved config is output-neutral.
const PACKER_THRESHOLD_SCALE = 0.75; // row-scale floor below which the packer engages
const LABEL_COLLISION_TOLERANCE = 0.3; // shared stagger / residual slack (was 0.3)
const LABEL_NUDGE_PASSES = 3; // horizontal nudge pass count (was `< 3`)
const LABEL_MAX_RESOLVE_PASSES = 4; // global label de-overlap pass budget
const WRAP_BUDGET_TOLERANCE = 1.1; // wrap budget slack multiplier (was * 1.1)
const ASPECT_FLOOR = 0.01; // Math.max(0.01, aspect) floor
// Canonical label offset. The label stage applied `?? 3.5` as the effective
// fallback that produced current output, so 3.5 (not DEFAULT_LAYOUT_RULES = 4)
// is the output-neutral global default.
const CANONICAL_LABEL_OFFSET_Y = 3.5;

//============================================
// Global defaults from constants
//============================================

export function buildGlobalDefaults(): LayoutConfig {
  const spacing: SpacingConfig = {
    objectGap: DEFAULT_LAYOUT_RULES.zone_gap,
    labelGap: DEFAULT_LAYOUT_RULES.zone_gap,
    objectZonePadding: ZONE_PADDING,
    labelZonePadding: ZONE_PADDING,
  };
  const config: LayoutConfig = {
    spacing,
    packer: {
      thresholdScale: PACKER_THRESHOLD_SCALE,
      minScale: MIN_SCALE,
    },
    maxPasses: MAX_LAYOUT_PASSES,
    shrinkFactor: LAYOUT_SHRINK_FACTOR,
    labelFontSize: DEFAULT_LAYOUT_RULES.label_font_size,
    labelLineHeight: DEFAULT_LAYOUT_RULES.label_line_height,
    labelOffsetY: CANONICAL_LABEL_OFFSET_Y,
    // Default label placement: above the object. A scene layout_rules or a
    // per-placement override can switch a label to "bottom".
    labelPlacement: "top",
    labelLineHeightPct: LABEL_LINE_HEIGHT_PCT,
    avgCharWidthPct: AVG_CHAR_WIDTH_PCT,
    labelFontWidthFraction: LABEL_FONT_WIDTH_FRACTION,
    labelFontMinPx: LABEL_FONT_MIN_PX,
    labelCollisionTolerance: LABEL_COLLISION_TOLERANCE,
    labelNudgePasses: LABEL_NUDGE_PASSES,
    labelMaxResolvePasses: LABEL_MAX_RESOLVE_PASSES,
    wrapBudgetTolerance: WRAP_BUDGET_TOLERANCE,
    maxFootprintRatio: MAX_FOOTPRINT_RATIO,
    aspectFloor: ASPECT_FLOOR,
    defaultAlignStop: DEFAULT_LAYOUT_RULES.default_align_stop,
    zoneOverrides: {},
  };
  return Object.freeze(config);
}

//============================================
// Scene layout_rules layer
//============================================

// Apply authored scene-level layout_rules over the global defaults. Only fields
// the author actually set override; an unset field keeps the global value. This
// reproduces the per-field `?? default` reads the stages did before, so output
// is unchanged.
function applySceneRules(base: LayoutConfig, sceneRules: LayoutRules): LayoutConfig {
  const spacing: SpacingConfig = {
    ...base.spacing,
    // Authored zone_gap drives object spacing only.
    objectGap: sceneRules.zone_gap ?? base.spacing.objectGap,
  };
  return {
    ...base,
    spacing,
    labelFontSize: sceneRules.label_font_size ?? base.labelFontSize,
    labelLineHeight: sceneRules.label_line_height ?? base.labelLineHeight,
    labelOffsetY: sceneRules.label_offset_y ?? base.labelOffsetY,
    labelPlacement: sceneRules.label_placement ?? base.labelPlacement,
    defaultAlignStop: sceneRules.default_align_stop ?? base.defaultAlignStop,
  };
}

//============================================
// Zone override layer
//============================================

// Build the sparse per-zone override map from existing Zone fields. align and
// baseline are the only existing per-zone schema fields; spacing is left unset
// here (no authored per-zone spacing field exists). The map is keyed by zone id
// and only contains zones that set at least one override field.
function buildZoneOverrides(zones: Zone[]): Record<string, ZoneLayoutConfig> {
  const overrides: Record<string, ZoneLayoutConfig> = {};
  for (const zone of zones) {
    // Build the entry once from the present fields; only register zones that set
    // at least one override.
    const hasAlign = zone.align !== undefined;
    const hasBaseline = zone.baseline !== undefined;
    if (!hasAlign && !hasBaseline) continue;
    const entry: ZoneLayoutConfig = {
      ...(hasAlign ? { align: zone.align } : {}),
      ...(hasBaseline ? { baseline: zone.baseline } : {}),
    };
    overrides[zone.id] = entry;
  }
  return overrides;
}

//============================================
// resolveConfig (full precedence)
//============================================

// Resolve the effective LayoutConfig for one scene by the ratified precedence.
// zone is optional: when resolving the scene-wide config, pass undefined and the
// returned config carries the full zoneOverrides map. When resolving for one
// zone, pass that zone and its align/baseline/spacing overrides are folded into
// the top-level fields so a stage reading config.spacing sees the zone values.
// placementDerived and strategyLocal are sparse partials applied last.
export function resolveConfig(
  globalDefaults: LayoutConfig,
  sceneRules: LayoutRules,
  zone: Zone | undefined,
  placementDerived: Partial<LayoutConfig>,
  strategyLocal: Partial<LayoutConfig>,
  zones: Zone[] = [],
): LayoutConfig {
  // 1. global defaults -> 2. scene layout_rules.
  let resolved = applySceneRules(globalDefaults, sceneRules);

  // Record the full per-zone override map so DecisionMetadata / later stages can
  // read each zone's effective options without re-resolving.
  resolved = { ...resolved, zoneOverrides: buildZoneOverrides(zones) };

  // 3. zone overrides: fold the named zone's align/baseline/spacing into the
  // top-level fields so a stage that reads config for this zone sees them.
  if (zone !== undefined) {
    const zoneOverride = resolved.zoneOverrides[zone.id];
    if (zoneOverride?.spacing !== undefined) {
      resolved = {
        ...resolved,
        spacing: { ...resolved.spacing, ...zoneOverride.spacing },
      };
    }
  }

  // 4. placement-derived values, then 5. strategy-local options. Each is a
  // sparse partial; only present keys override. Spacing partials merge by key.
  resolved = mergePartial(resolved, placementDerived);
  resolved = mergePartial(resolved, strategyLocal);

  return Object.freeze(resolved);
}

// Merge a sparse Partial<LayoutConfig> over a resolved config. Nested spacing
// and packer partials merge by key so a caller can override one spacing field
// without clearing the rest.
function mergePartial(base: LayoutConfig, partial: Partial<LayoutConfig>): LayoutConfig {
  const spacing: SpacingConfig =
    partial.spacing !== undefined ? { ...base.spacing, ...partial.spacing } : base.spacing;
  const packer = partial.packer !== undefined ? { ...base.packer, ...partial.packer } : base.packer;
  return { ...base, ...partial, spacing, packer };
}
