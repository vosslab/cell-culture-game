// Public surface for the layout engine. Renderers, validators, and tests
// import from this module. Internal helpers stay in their own files.

// Named re-exports from constants: only symbols imported by code outside
// src/scene_runtime/layout/. Internal-only constants remain unexported here.
export {
  DEFAULT_VIEWPORT,
  DEPTH_TIER_GAP,
  LABEL_LINE_HEIGHT_PCT,
  PX_PER_SCENE_PERCENT,
  UNIFORM_RESCALE_MIN_SCALE,
  WORKSPACE_PX_PER_CM,
  ZONE_PADDING,
} from "./constants.js";

export * from "./types.js";
export { normalizeSchema } from "./normalize_schema.js";
export { lowerSceneZones } from "./lower_semantic_zones.js";
export { resolveInheritance } from "./resolve_inheritance.js";
export { bindObjects } from "./bind_objects.js";
export { scaleToRealWorld } from "./scale_to_real_world.js";
export { groupByZone } from "./group_by_zone.js";
export { horizontalLayout } from "./horizontal_layout.js";
export { verticalLayout, applyUniformRescale } from "./vertical_layout.js";
// applyUniformRescale + result type exported for the terminal-rescale unit test
// (one scene-wide object factor, fixed label/gap extents, single reflow).
export type { UniformRescaleResult } from "./vertical_layout.js";
export { layoutLabels, resolveLabelCollisions } from "./layout_labels.js";
export { clampSceneBounds } from "./clamp_scene_bounds.js";
export { runPipeline } from "./run_pipeline.js";
export {
  assert_valid_scene_interaction_geometry,
  derive_scene_interaction_geometry,
  INTERACTION_HIT_CORE_PX,
} from "./interaction_geometry.js";
export { wrapLabel } from "./wrap_label.js";
// verticalFootprintFor exported for the vertical-footprint unit test
// (side-independence of the combined extent). VerticalFootprint type re-exported
// for typed test assertions.
export { verticalFootprintFor } from "./vertical_footprint.js";
export type { VerticalFootprint } from "./vertical_footprint.js";
// reflowZones exported for the reflow-zones unit test (depth order, per-tier-max
// content extent, proportional leftover, baseline fraction). Result types
// re-exported for typed test assertions and for place-vertical to consume bands.
export { reflowZones } from "./reflow_zones.js";
export type { ReflowZonesResult, BaselineClampReport } from "./reflow_zones.js";
// depthFor, footprintFor, visualWidthFor, widthScaleFor omitted: no consumer
// outside src/scene_runtime/layout/ (grep confirmed zero imports).
export { DEMO_OBJECT_LIBRARY, DEMO_ASSET_SPECS } from "./__fixtures__/demo_library.js";
export { resolveConfig, buildGlobalDefaults } from "./config/index.js";
export type {
  LayoutConfig,
  SpacingConfig,
  PackerConfig,
  ZoneLayoutConfig,
} from "./config/index.js";
// PHASE_ORDER, PLACEMENT_PHASES, VERTICAL_TAIL_PHASES, runPhases, Phase, PhaseName, LayoutContext omitted:
// used only by run_pipeline.ts internally (grep confirmed zero external imports).
export {
  SEVERITY_TABLE,
  severityRuleFor,
  buildDiagnostic,
  failsBuild,
  countBuildFailures,
  buildActionablePayload,
  buildRowZoneDecision,
  buildDecisionMetadata,
  OFFCANVAS_TIERS,
  offCanvasTier,
  classifyItemOffCanvas,
  collectOffCanvasDiagnostics,
} from "./diagnostics/index.js";
// SEVERITY_DIAGNOSTIC_CODES omitted: no external consumer (grep confirmed zero imports).
// SeverityDiagnosticCode kept as a discriminant type for test assertions.
export type {
  SeverityDiagnosticCode,
  DiagnosticSeverity,
  DiagnosticOwner,
  YamlPointerLevel,
  SeverityRule,
  YamlPointer,
  SeverityDiagnostic,
  ActionablePayload,
  AttemptedMove,
  ZoneDecision,
  DecisionMetadata,
  OffCanvasTier,
  OffCanvasClass,
  OffCanvasSeverity,
  OffCanvasOverflow,
  OffCanvasDiagnostic,
} from "./diagnostics/index.js";
