// Layout engine type signatures. Mirrors design_advice/LAYOUT_PIPELINE.md §1.
// All coordinates are scene-percent (0..100 of viewport per axis).

import type {
  ALIGN_MODES,
  ALIGN_STOPS,
  ANCHOR_YS,
  DEPTHS,
  KINDS,
  WORKSPACES,
  CAPABILITIES,
  SCALE_SOURCES,
  STAGES,
  DIAGNOSTIC_KINDS,
  LABEL_PLACEMENTS,
} from "./constants.js";
import type { DecisionMetadata } from "./diagnostics/decision_metadata.js";
import type { OffCanvasDiagnostic } from "./diagnostics/offcanvas.js";
import type { SeverityDiagnostic } from "./diagnostics/severity_model.js";
import type { UnifiedDiagnostic } from "./diagnostics/unified.js";

export type Workspace = (typeof WORKSPACES)[number];
export type AlignMode = (typeof ALIGN_MODES)[number];
export type AlignStop = (typeof ALIGN_STOPS)[number];
export type AnchorY = (typeof ANCHOR_YS)[number];
export type Depth = (typeof DEPTHS)[number];
export type Kind = (typeof KINDS)[number];
export type Capability = (typeof CAPABILITIES)[number];
export type ScaleSource = (typeof SCALE_SOURCES)[number];
export type StageName = (typeof STAGES)[number];
export type DiagnosticKind = (typeof DIAGNOSTIC_KINDS)[number];
export type LabelPlacement = (typeof LABEL_PLACEMENTS)[number];

export interface Bounds {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export type SceneBoundsRect = Bounds;

//============================================
// Background discriminated union. Supports gradient and asset forms.
//============================================

export type Background =
  | {
      type: "gradient";
      from: string;
      to: string;
      angle?: number;
    }
  | {
      asset: string;
    };

// Source-zone vocabulary.  A source zone names an ordered semantic grouping;
// geometry is optional only while coordinate-bearing scenes are migrated.
// Layout phases never consume this type directly.
export interface SourceZone {
  id: string;
  align?: AlignMode;
  label?: string;
  // Transitional legacy input. New authored scenes omit both fields.
  bounds?: Bounds;
  baseline?: number;
}

// Internal, renderer-facing geometry. Lowering produces this complete shape
// before any placement phase runs, so downstream code never handles optional
// bounds or baselines.
export interface Zone extends Omit<SourceZone, "bounds"> {
  bounds: Bounds;
}

export interface LayoutHint {
  default_width: number;
  label_width?: number;
  anchor_y?: AnchorY;
  anchor_y_offset?: number;
  display_width_cm?: number;
  // Optional per-placement override for where the label renders. Absent unless
  // a placement authored it; the engine falls back to the scene rule, then the
  // config default ("top").
  label_placement?: LabelPlacement;
}

// State-field schema types emitted by the object-library generator.
// These are the declared contract; visual_states is the rendering map.

export type StateFieldType = "enum" | "int" | "float" | "bool";

export interface StateFieldDef {
  field_name: string;
  type: StateFieldType;
  default: string | number | boolean;
  applies_to: "object" | "subpart";
  // enum-specific
  allowed?: string[];
  // numeric-specific
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

// Visual state case for enum/bool fields
export interface VisualStateCase {
  when: string | boolean;
  output: VisualStateOutput;
}

// Output shapes for a visual state case
export type VisualStateOutput =
  { asset_name: string } | { overlay_name: string } | { composite: VisualStateOutput[] };

// Render-effect tokens (MATERIAL_CONVENTION.md, D12). A material-driven visual
// state may declare a render_effect + target instead of svg/overlay/composite
// cases. The generic render-effect interpreter keys on these tokens, never on object kind.
export type RenderEffect = "material_tint" | "fill_height";
// A render-effect target names either a generated geometry region
// (subpart_geometry) or an authored SVG anchor region. See SubpartGeometry below.
export type RenderEffectTarget = "subpart_geometry" | "anchor_liquid_bounds" | "anchor_liquid_clip";

export interface VisualStateDef {
  // kind is present for svg/overlay/composite visual states. Material-driven
  // render-effect visual states omit kind and carry render_effect/target.
  kind?: "svg" | "overlay" | "composite";
  applies_to: "object" | "subpart";
  // Cases for enum/bool fields
  cases?: VisualStateCase[];
  // Formula string for int/float fields
  formula?: string;
  // Declarative render-effect form (material_tint / fill_height). When set,
  // the field drives the named effect on the named target region.
  render_effect?: RenderEffect;
  target?: RenderEffectTarget;
  // Optional clip region for an anchor-target fill_height effect.
  clip?: RenderEffectTarget;
  // Optional capacity for fill_height normalization (microliters).
  capacity_ul?: number;
  // Optional capacity for fill_height normalization (milliliters). Exactly one
  // liquid capacity unit is authored for an anchor fill effect.
  capacity_ml?: number;
}

// Keyed by field_name
export type ObjectVisualStates = Record<string, VisualStateDef>;

// Generated subpart geometry (MATERIAL_CONVENTION.md D10). A render effect whose
// target is subpart_geometry resolves the current subpart name to one of these
// shapes. circle covers round wells; rect covers rectangular subparts.
export type SubpartGeometry =
  | { shape: "circle"; cx: number; cy: number; r: number }
  | { shape: "rect"; x: number; y: number; w: number; h: number };
// Keyed by subpart name (A1, B7, H12). Deterministically ordered by the
// generator (name_pattern order) so the overlay renderer iterates a stable list.
export type SubpartGeometryMap = Record<string, SubpartGeometry>;

// The base-art coordinate frame the subpart geometry is expressed in. Matches
// the asset SVG viewBox so the overlay aligns with the rendered base art.
export interface ViewBox {
  min_x: number;
  min_y: number;
  width: number;
  height: number;
}

// State schema surface for store validation.
// Derived from declared state_fields (not inferred from visual_states).
export type ObjectStateSchema = Record<string, StateFieldDef>;

export interface ObjectDef {
  object_name: string;
  kind: Kind;
  label: string;
  asset: string;
  capabilities: Capability[];
  layout: LayoutHint;
  // Declared state-field schema (object-level fields only; subpart fields in subpart_state_schema)
  state_schema: ObjectStateSchema;
  // Per-object visual_states rendering map
  visual_states: ObjectVisualStates;
  // Subpart state schema (only set on structured objects; empty object otherwise)
  subpart_state_schema: ObjectStateSchema;
  // Generated subpart geometry for structured objects whose subparts render
  // (PATH-B derived from the structure grid; MATERIAL_CONVENTION.md D10). Absent
  // for objects with no rendered subparts.
  subpart_geometry?: SubpartGeometryMap;
  // The base-art coordinate frame subpart_geometry is expressed in (asset SVG
  // viewBox). Present iff subpart_geometry is present.
  view_box?: ViewBox;
  // Full declared subpart-instance vocabulary for a structured object, in
  // row-major order (tube_A..tube_H, lane_1..lane_10, A1..H12). This is the
  // authoritative set the runtime validates an authored "<object>.<subpart>"
  // target against; unlike subpart_geometry it is present for every structured
  // object, not only the rendered-geometry grids. Absent for non-structured
  // objects.
  subparts?: string[];
  // Declared subpart groups flattened to {group_name: [member subpart names]}
  // (all_wells, row_A, col_1, all_lanes, ...). A group write
  // (ObjectStateChange target "<object>.<group>") fans out to every member.
  // Group names are disjoint from subpart names and every member is a declared
  // subpart. Absent when the object declares no groups.
  subpart_groups?: Record<string, string[]>;
}

export interface AssetSpec {
  default_width: number;
  label_width: number;
  aspect: number;
}

export type ObjectLibrary = Record<string, ObjectDef>;
export type AssetSpecs = Record<string, AssetSpec>;

// Top-level schema registries emitted by gen_object_library.py.
// Keys are object_name. Object-level state fields only (subpart fields excluded).
export type ObjectStateSchemas = Record<string, ObjectStateSchema>;
// Subpart-level state fields only (only set for structured objects).
export type ObjectSubpartStateSchemas = Record<string, ObjectStateSchema>;

export interface LayoutRules {
  zone_gap?: number;
  label_font_size?: number;
  label_line_height?: number;
  label_offset_y?: number;
  default_align_stop?: AlignStop;
  // Scene-wide default for label placement; overridden per-placement by
  // layout.label_placement. Absent unless authored.
  label_placement?: LabelPlacement;
}

export interface PlacementAuthored {
  placement_name: string;
  object_name: string;
  zone: string;
  depth_tier?: number;
  align_stop?: AlignStop;
  baseline_override?: number;
  depth?: Depth;
  layout?: Partial<LayoutHint>;
  // Internal marker added during inheritance resolution. Not user-authored.
  active?: boolean;
  // Provenance after extends: "base" or "own".
  _from?: "base" | "own";
  // Placeholder mode only: true when the object's SVG assets are missing from assets/.
  // Set by pipeline/gen_scene_index.py --missing-svg=placeholder. Never true in
  // a strict (normal) build. The renderer reads this to render a labeled placeholder.
  missing_svg?: true;
}

export interface SceneA {
  scene_name: string;
  workspace: Workspace;
  capabilities?: string[];
  // Transitional legacy input. Coordinate-free scenes are lowered to the
  // canonical workspace bounds by the layout manager.
  scene_bounds?: SceneBoundsRect;
  background?: Background;
  zones: SourceZone[];
  placements: PlacementAuthored[];
  layout_rules?: LayoutRules;
  wrong_order_message?: { template: string; toast_duration_ms?: number };
  extends?: string;
  add_placements?: PlacementAuthored[];
  reposition_placements?: Array<
    Pick<PlacementAuthored, "placement_name"> & Partial<PlacementAuthored>
  >;
  deactivate_placements?: Array<{ placement_name: string }>;
  remove_placements?: Array<{ placement_name: string } | string>;
}

// A source SceneA after semantic-zone lowering. This is the only scene shape
// consumed by placement, guards, and render-facing PipelineResult.scene.
export interface ResolvedScene extends Omit<SceneA, "scene_bounds" | "zones"> {
  scene_bounds: SceneBoundsRect;
  zones: Zone[];
}

// Required form of LayoutHint after merge: defaults applied for every field.
// display_width_cm remains optional (may not be authored).
export interface ResolvedLayoutHint {
  default_width: number;
  label_width: number;
  anchor_y: AnchorY;
  anchor_y_offset: number;
  display_width_cm?: number;
  // label_placement stays optional after merge: it is copied only when the
  // placement authored it, so an unauthored placement adds no JSON key (mirrors
  // display_width_cm). The engine resolves the fallback chain at seed time.
  label_placement?: LabelPlacement;
}

export interface BoundPlacement extends PlacementAuthored {
  kind: Kind | "unknown";
  label: string;
  asset: string;
  capabilities: Capability[];
  aspect: number;
  layout: ResolvedLayoutHint;
  _error?: string;
  // True when the placement references an object absent from OBJECT_LIBRARY.
  // Set during bind. The placement is bound as a renderable placeholder
  // (missing_svg true) instead of being dropped, so the renderer can show a
  // distinct "missing object" box and structural guards skip it. Distinguished
  // in the DOM from a missing-SVG placeholder via data-placeholder-kind.
  _missing_object?: true;
}

export interface ScaledPlacement extends BoundPlacement {
  _width_scale: number;
  _scale_source: ScaleSource;
  _px_per_cm: number | null;
  _shrunk_passes?: number;
}

export interface ComputedItem extends ScaledPlacement {
  _scale: number;
  _centerX: number;
  _baselineY: number;
  _top: number;
  _visualWidth: number;
  _height: number;
  _footprint: number;
  _labelX: number;
  _labelY: number;
  _labelLines: string[];
  // Vertical measured-extent fields, set by the measure-vertical stage (the
  // vertical mirror of _footprint). _combinedHeight is the SCALAR side-independent
  // row-extent magnitude (object height + label offset + label box height); it is
  // a magnitude, not a geometry object. _labelBoxHeight is the rendered label
  // strip height alone (one label line height per wrapped line). _labelPlacement
  // is the authored/default label side ("top" | "bottom") that records how that
  // combined height is partitioned into a label strip and an object strip during
  // placement. They are optional so an item that has not yet
  // passed measure-vertical (a raw place-horizontal item) is still a valid
  // ComputedItem.
  _combinedHeight?: number;
  _labelBoxHeight?: number;
  _labelPlacement?: LabelPlacement;
  _clamped?: boolean;
}

// One depth tier inside a computed zone band, produced by the reflow-zones stage.
// A tier is the set of items in a zone sharing the same depth_tier; the horizontal
// stage already spread them side-by-side, so a tier renders as one vertical ROW.
// rowHeight is the maximum _combinedHeight over the tier's items (the row is as
// tall as its tallest member). rowTop is the row's top edge inside the computed
// band; place-vertical partitions [rowTop, rowTop + rowHeight] into a label strip
// and an object strip per the item's label side. placementNames
// lists the tier's items in group_by_zone order (depth_tier then placement_name).
export interface ComputedTierRow {
  depthTier: number;
  rowTop: number;
  rowHeight: number;
  placementNames: string[];
}

// A computed zone band, produced by the reflow-zones stage. It is the vertical
// mirror of the horizontal label fold at the zone level: the authored zone bounds
// become a SEED, and the band top/bottom are reflowed from measured per-tier
// content so every row has room for its object + gap + wrapped label.
// top/bottom are the computed band edges in scene-percent; baseline is the
// authored baseline recomputed relative to the new band (authored fraction
// preserved) or the band center when no baseline was authored. tiers are the
// band's rows in depth order (rear toward the band top). place-vertical consumes
// this to space tier rows and back-solve each item's baseline; reflow-zones only
// produces it and does not move any item.
export interface ComputedZoneBand {
  id: string;
  top: number;
  bottom: number;
  baseline: number;
  tiers: ComputedTierRow[];
}

export interface Diagnostic {
  stage: StageName;
  severity: "error" | "warn" | "info";
  kind: DiagnosticKind;
  placement_name?: string;
  object_name?: string;
  row?: string;
  zone?: string;
  workspace?: string;
  dx?: number;
  dy?: number;
  overflow_pct?: number;
  between?: [string, string];
  items?: number;
  passes_used?: number;
  unresolved?: number;
  // Stagger row index (0-based) for label_row_staggered diagnostics.
  staggered_row?: number;
}

export type Diagnostics = Diagnostic[];

export interface NormalizeTrace {
  op: "detect";
  value?: "zone_bounds";
}

export interface NormalizedScene {
  scene: SceneA | null;
  source: "zone_bounds" | "none";
  trace: NormalizeTrace[];
}

export interface InheritanceOp {
  op: "extends" | "remove" | "deactivate" | "reposition" | "add";
  target: string;
  count?: number;
  removed?: number;
  to_zone?: string;
  status?: string;
}

export interface InheritanceResolution {
  placements: PlacementAuthored[];
  provenance: Array<{ name: string; from: "base" | "own" }>;
  operations: InheritanceOp[];
}

export interface GroupedPlacements {
  groups: Map<string, ScaledPlacement[]>;
  orphans: ScaledPlacement[];
}

export type WorkspacePxPerCm = Record<Workspace, number>;

export interface PipelineInputs {
  scene: SceneA;
  library?: ObjectLibrary;
  assets?: AssetSpecs;
  viewport?: { w: number; h: number };
  baseSceneMap?: Record<string, SceneA>;
  workspacePxPerCm?: WorkspacePxPerCm;
  maxPasses?: number;
  shrinkFactor?: number;
}

export interface PassRecord {
  pass: number;
  diagnostics: Diagnostic[];
  zones_shrunk: string[];
}

export interface PipelineStages {
  inputs: {
    scene: SceneA;
    library: ObjectLibrary;
    assets: AssetSpecs;
  };
  normalized: NormalizedScene;
  inheritance: InheritanceResolution;
  bound: BoundPlacement[];
  scaled: ScaledPlacement[];
  grouped: GroupedPlacements;
  horizontal: Map<string, ComputedItem[]>;
  vertical: Map<string, ComputedItem[]>;
  labelled: Map<string, ComputedItem[]>;
  clamped: Map<string, ComputedItem[]>;
}

export interface PipelineResult {
  scene: ResolvedScene;
  sourceScene: SceneA;
  diagnostics: Diagnostic[];
  passes: PassRecord[];
  identityDiagCount: number;
  stages: PipelineStages;
  final: ComputedItem[];
  // Per-scene decision metadata, kept SEPARATE from the diagnostics array (see
  // diagnostics/decision_metadata.ts). The scorecard and AI reviewer read this;
  // diagnostics stay the severity-graded problem stream. Type-only import keeps
  // types.ts free of a runtime dependency on the diagnostics layer.
  decisionMetadata: DecisionMetadata;
  // Severity-graded Errors raised during layout. The report-only validate phase
  // pushes unresolved_overlap here for any zone whose items still escape
  // scene_bounds after the vertical auto-fit and convergence shrink.
  // Kept SEPARATE from the legacy `diagnostics` array, whose kinds are a closed
  // set; this carries the actionable severity payloads. Empty when nothing is
  // unresolved.
  severityDiagnostics: SeverityDiagnostic[];
  // Report-only per-item off-canvas classification from the validate phase.
  // One entry per item whose artwork box escapes scene_bounds: fully_off_canvas
  // (error class) or partial_overflow (warning, magnitude-scaled). This is a
  // SEPARATE informational stream from severityDiagnostics: it never fails or
  // blocks a build, it only reports. Audit tooling and the committed off-canvas
  // baseline read it. Empty when every item sits inside scene_bounds. Not
  // serialized into the precompute (the artifact serializes only `final`).
  offCanvasDiagnostics: OffCanvasDiagnostic[];
  // Unified diagnostics stream (M17): the four parallel streams above
  // (`diagnostics`, `passes[].diagnostics`, `severityDiagnostics`,
  // `offCanvasDiagnostics`) folded into one flat, normalized array. This is the
  // long-term single source of truth for report tooling, which reads it instead
  // of recomputing per-stream. The build gate stays on `severityDiagnostics`;
  // in this stream `failBuild` is authoritative only on severity-sourced entries.
  // See diagnostics/unified.ts. Serialized into the precompute artifact and
  // rehydrated by precomputed_result.ts, but unused at runtime (report tooling only).
  unifiedDiagnostics: UnifiedDiagnostic[];
  // Computed zone bands from the reflow-zones stage, keyed by zone id. The band
  // reflows the scene's vertical range from measured per-tier content; place-vertical
  // consumes it to space tier rows. It is NOT serialized into
  // generated/precomputed_layout.ts (the artifact serializes only `final`), so it
  // does not affect precompute determinism. Empty when the scene has no zones.
  zoneBands: Map<string, ComputedZoneBand>;
  // reflow-zones overflow report (the PRE-rescale demand signal). reflowOverflow is
  // true when the measured content extent exceeds the scene range; reflowTotalContent
  // is the summed per-zone content extent; reflowSceneRange{Top,Bottom} are the
  // scene_bounds top/bottom the reflow ran across. These stay at the pre-rescale
  // values even when the terminal uniform rescale runs: they are the raw "how
  // overfull is this scene" signal the scene-scale tool reads. reflowOverflow
  // triggers the rescale; the post-rescale state lives in the reflowUniformScale /
  // sceneReflowOverflow / labelDominant fields below. Not serialized into the
  // precompute.
  reflowOverflow: boolean;
  reflowTotalContent: number;
  reflowSceneRangeTop: number;
  reflowSceneRangeBottom: number;
  // Terminal uniform object rescale outputs, threaded for downstream review tools.
  // reflowUniformScale is the one scene-wide factor
  // applied to every object's width AND height (aspect preserved); it is 1 when no
  // rescale was needed (reflowOverflow was false). sceneReflowOverflow is true when
  // the scaled content STILL exceeds the scene range at the dedicated floor
  // (UNIFORM_RESCALE_MIN_SCALE) -- the repurposed scene-level
  // item_escapes_zone_vertically signal, also pushed into the diagnostics stream.
  // labelDominant is true when, after the rescale, any item's label strip is at
  // least LABEL_DOMINANT_RATIO of its scaled object height (a label grown visually
  // dominant relative to its shrunken object, surfaced for review). Both flags are
  // false when no rescale ran. Not serialized into the precompute.
  reflowUniformScale: number;
  sceneReflowOverflow: boolean;
  labelDominant: boolean;
}
