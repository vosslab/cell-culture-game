// Phase registry for the layout pipeline. Ratified contract:
// docs/archive/decisions/layout_model_layer_synthesis.md "Phase model".
//
// The named phases replace the previously inline stage sequence in
// run_pipeline.ts. Phase order (serial vertical-reflow spine):
//
//   prepare -> resolve-metadata -> measure -> partition ->
//   place-horizontal -> measure-vertical -> reflow-zones -> place-vertical ->
//   place-labels -> resolve-collisions -> validate -> report
//
// measure-vertical is the vertical mirror of the horizontal label fold: it reads
// each item's NATURAL object height (visualWidth * viewportAspect / aspect, since
// place-horizontal leaves _height = 0 and place-vertical runs AFTER this stage)
// and the width-stable wrapped label box, and records the side-independent combined
// row extent (_combinedHeight) plus _labelBoxHeight / _labelPlacement /
// _labelLines. It runs AHEAD of place-vertical: the reflow needs the measured
// extents to compute the bands BEFORE the objects are placed. It is read-only with
// respect to POSITION (it writes only the measured-extent fields and _labelLines,
// never _centerX / _baselineY / _top), so the place-vertical stage it precedes
// sees unperturbed horizontal geometry.
//
// reflow-zones is the zone-level vertical fold: it reads each item's measured
// combined extent (_combinedHeight) and reflows the scene's vertical range across
// zones in depth order, producing a computed band per zone (ComputedZoneBand) plus
// the overflow / scene-range report. It runs AFTER measure-vertical (it needs
// _combinedHeight) and BEFORE place-vertical (which consumes the bands). It writes
// only ctx.zoneBands and the reflow report fields; it never touches a ComputedItem
// field, so its mutatesPositions flag is false.
//
// place-vertical CONSUMES the computed bands: it places each item's object strip
// inside its depth-tier row, back-solves the item baseline, and assigns the NATURAL
// _height (no per-object shrink). The old vertical auto-fit (fitFactor +
// maxHeightInZone) is gone; a scene whose measured content exceeds the scene range
// is handled by the uniform object rescale, not a per-object shrink.
//
// Read/mutate boundary (enforced by review and by the mutatesPositions flag):
// - place-horizontal, place-vertical, place-labels, and resolve-collisions are
//   the only position-mutating phases.
// - resolve-collisions applies geometry results to positions: it mutates only
//   label _labelX / _labelY in place; object positions are unchanged.
// - prepare, resolve-metadata, measure, partition, measure-vertical, reflow-zones,
//   validate, and report are read-only with respect to position. measure-vertical
//   writes only the measured-extent fields (_combinedHeight / _labelBoxHeight /
//   _labelPlacement / _labelLines), never a position field, so its
//   mutatesPositions flag is false. reflow-zones writes only ctx.zoneBands (a
//   side map of computed bands) and the reflow report; it never touches a
//   ComputedItem field, so its mutatesPositions flag is false too. The `validate`
//   phase (clamp_scene_bounds) is report-only: it measures scene-bounds overflow
//   and emits diagnostics without mutating positions, so its mutatesPositions flag
//   is false.
//
// The `validate` phase wraps clamp_scene_bounds.ts: it no longer translates
// out-of-bounds zone groups; the band reflow + tier placement sit items inside
// their computed bands instead.

import { clampSceneBounds } from "./clamp_scene_bounds.js";
import { collectOffCanvasDiagnostics } from "./diagnostics/offcanvas.js";
import { groupByZone } from "./group_by_zone.js";
import { horizontalLayout } from "./horizontal_layout.js";
import { layoutLabels, resolveLabelCollisions } from "./layout_labels.js";
import { reflowZones } from "./reflow_zones.js";
import { verticalLayout } from "./vertical_layout.js";
import { verticalFootprintFor } from "./vertical_footprint.js";
import type { BoundsOverflow } from "./clamp_scene_bounds.js";
import type { OffCanvasDiagnostic } from "./diagnostics/offcanvas.js";
import type { LayoutConfig } from "./config/index.js";
import type { SeverityDiagnostic } from "./diagnostics/severity_model.js";
import type { PackerZoneOutcome } from "./strategies/index.js";
import type {
  ComputedItem,
  ComputedZoneBand,
  Diagnostics,
  GroupedPlacements,
  LabelPlacement,
  ResolvedScene,
  ScaledPlacement,
} from "./types.js";

export const PHASE_ORDER = [
  "prepare",
  "resolve-metadata",
  "measure",
  "partition",
  "place-horizontal",
  "measure-vertical",
  "reflow-zones",
  "place-vertical",
  "place-labels",
  "resolve-collisions",
  "validate",
  "report",
] as const;

export type PhaseName = (typeof PHASE_ORDER)[number];

// Mutable context threaded through one pass of the placement phases. Identity
// resolution (prepare..partition source data) is computed once in run_pipeline
// and fed in via `scaled`; the per-pass context carries the maps each placement
// phase fills. diagnostics is the per-pass diagnostic sink.
export interface LayoutContext {
  readonly scene: ResolvedScene;
  readonly viewport: { w: number; h: number };
  // Source placements for this pass (post-shrink in later passes).
  scaled: ScaledPlacement[];
  diagnostics: Diagnostics;
  grouped?: GroupedPlacements;
  horizontal?: Map<string, ComputedItem[]>;
  vertical?: Map<string, ComputedItem[]>;
  // measure-vertical output: the SAME per-zone items as ctx.horizontal with the
  // measured-extent fields (_combinedHeight / _labelBoxHeight / _labelPlacement /
  // _labelLines) filled in. measure-vertical runs AHEAD of place-vertical, so these
  // items still carry the post-place-horizontal geometry (_height = 0); they are
  // mutated in place, so reflow-zones and place-vertical read the same objects.
  measuredVertical?: Map<string, ComputedItem[]>;
  // reflow-zones output: the computed band per zone (keyed by zone id), reflowed
  // from the measured per-tier content extents in depth order. place-vertical
  // consumes it to space tier rows and back-solve item baselines. It is a side map
  // of computed bands, never a ComputedItem field, so producing it does not perturb
  // item geometry.
  zoneBands?: Map<string, ComputedZoneBand>;
  // reflow-zones report fields, threaded so run_pipeline can surface them on the
  // result for the uniform object rescale. reflowOverflow is true when the measured
  // content exceeds the scene range; reflowTotalContent is the summed per-zone
  // content extent; reflowSceneRangeTop/Bottom are the scene_bounds top/bottom the
  // reflow ran across (verbatim).
  reflowOverflow?: boolean;
  reflowTotalContent?: number;
  // The non-scaling portion of reflowTotalContent: zone padding, tier gaps, and
  // fixed label strips. The uniform object rescale sizes the object scale against
  // the SCALABLE remainder (reflowTotalContent - reflowFixedOverhead) so the
  // post-scale content fits the scene range instead of overshooting by this fixed
  // overhead.
  reflowFixedOverhead?: number;
  reflowSceneRangeTop?: number;
  reflowSceneRangeBottom?: number;
  labelled?: Map<string, ComputedItem[]>;
  collided?: Map<string, ComputedItem[]>;
  clamped?: Map<string, ComputedItem[]>;
  // Report-only validate-phase output: structured unresolved_overlap Errors for
  // any zone whose items still escape scene_bounds after fit/shrink. run_pipeline
  // reads this to surface the Errors; it does not affect positions.
  overflows?: BoundsOverflow[];
  // Report-only validate-phase output: per-item off-canvas classification.
  // Each escaping item is graded fully_off_canvas (error class) or
  // partial_overflow (warning, magnitude-scaled). This is a SEPARATE informational
  // stream from the build-gate severity diagnostics; nothing reads it to fail or
  // block a build. run_pipeline surfaces it on PipelineResult.offCanvasDiagnostics.
  offCanvas?: OffCanvasDiagnostic[];
  // resolve-collisions output: severity diagnostics from the global label
  // de-overlap (unresolved_label_overlap Errors, poor_label_alignment Warnings,
  // possible_overload Reviews). run_pipeline surfaces these on
  // PipelineResult.severityDiagnostics alongside the validate-phase overlaps.
  labelDiagnostics?: SeverityDiagnostic[];
  // place-horizontal output: per-zone packer outcomes for zones where the
  // dispatcher engaged the overflow packer. run_pipeline reads this to fill the
  // packer fields of the per-scene DecisionMetadata. Zones the row strategy
  // handled are absent (they keep the row-strategy decision).
  packerDecisions?: Map<string, PackerZoneOutcome>;
  // place-horizontal output: unresolved_overlap Errors the packer emitted for
  // zones it could not fit even at MIN_SCALE. run_pipeline surfaces these on
  // PipelineResult.severityDiagnostics.
  packerSeverity?: SeverityDiagnostic[];
}

export interface Phase {
  readonly name: PhaseName;
  // true only for place-* and resolve-collisions.
  readonly mutatesPositions: boolean;
  run(ctx: LayoutContext, config: LayoutConfig): LayoutContext;
}

//============================================
// Placement phases
//============================================

// partition: group scaled placements by zone. Read-only w.r.t. position; it
// only buckets items, it does not place them.
const partitionPhase: Phase = {
  name: "partition",
  mutatesPositions: false,
  run(ctx) {
    ctx.grouped = groupByZone(ctx.scaled, ctx.scene.zones ?? [], ctx.diagnostics);
    return ctx;
  },
};

const placeHorizontalPhase: Phase = {
  name: "place-horizontal",
  mutatesPositions: true,
  run(ctx, config) {
    const grouped = ctx.grouped ?? { groups: new Map(), orphans: [] };
    // Fresh per-pass packer sinks; the convergence loop reads the LAST pass's
    // outcomes (the same discipline as the diagnostics stream).
    const packerDecisions = new Map<string, PackerZoneOutcome>();
    const packerSeverity: SeverityDiagnostic[] = [];
    ctx.horizontal = horizontalLayout(
      grouped.groups,
      ctx.scene.zones ?? [],
      ctx.scene.layout_rules ?? {},
      ctx.diagnostics,
      config,
      {
        sceneName: ctx.scene.scene_name,
        packerSink: packerDecisions,
        severitySink: packerSeverity,
      },
    );
    ctx.packerDecisions = packerDecisions;
    ctx.packerSeverity = packerSeverity;
    return ctx;
  },
};

// measure-vertical: the vertical mirror of the horizontal label fold. For each
// placed item it computes the side-independent combined row extent
// (NATURAL object height + label offset + wrapped label box) and records that
// magnitude plus its label-strip height, the resolved label side, and the wrapped
// lines. It runs AHEAD of place-vertical, so _height is still 0 here; the stage
// derives the NATURAL object height (visualWidth * viewportAspect / aspect, the
// same formula place-vertical uses) and threads it to verticalFootprintFor as the
// explicit object height. It mutates ONLY the measured-extent fields and
// _labelLines, never a position field, so place-vertical sees unperturbed
// horizontal geometry. The authored/default label side is recorded for initial
// placement; the terminal safety flip stays in place-labels.
const measureVerticalPhase: Phase = {
  name: "measure-vertical",
  mutatesPositions: false,
  run(ctx, config) {
    const horizontal = ctx.horizontal ?? new Map<string, ComputedItem[]>();
    // Label tunables resolve through the scene config. config.labelOffsetY already
    // folds in the authored scene layout_rules.label_offset_y (applySceneRules), so
    // the measured gap matches what place-vertical and place-labels use.
    const labelOffsetY = config.labelOffsetY;
    const lineHeightPct = config.labelLineHeightPct;
    // Wrap-tuning values threaded so this single wrap site reads the SAME resolved
    // config values place-labels would use for its guarded fallback wrap. This is
    // the only wrapLabel call site in the pipeline; place-labels consumes the
    // _labelLines it writes here.
    const avgCharWidthPct = config.avgCharWidthPct;
    const wrapBudgetTolerance = config.wrapBudgetTolerance;
    // Scene-wide default label side: the scene layout_rules value already folds
    // into config.labelPlacement, so a per-placement override is the only extra
    // term. This records the authored/default side for initial placement; the
    // terminal safety flip (place-labels) may override it later.
    const sceneLabelPlacement = config.labelPlacement;
    // Natural-height formula (mirrors place-vertical): visualWidth * viewportAspect
    // / aspect, with the same aspect floor. _height is 0 at this stage, so the
    // measure uses this natural height for the combined extent the reflow reserves.
    const viewportAspect = ctx.viewport.w / ctx.viewport.h;
    const aspectFloor = config.aspectFloor;
    for (const items of horizontal.values()) {
      for (const it of items) {
        const aspect = Math.max(aspectFloor, it.aspect);
        const naturalHeight = (it._visualWidth * viewportAspect) / aspect;
        const fp = verticalFootprintFor(
          it,
          lineHeightPct,
          labelOffsetY,
          avgCharWidthPct,
          wrapBudgetTolerance,
          naturalHeight,
        );
        const placement: LabelPlacement = it.layout.label_placement ?? sceneLabelPlacement;
        // Mutate only the measured-extent fields + the reused wrap. Horizontal
        // geometry (_centerX / _visualWidth) is left exactly as place-horizontal
        // set it, so place-vertical sees unchanged horizontal positions.
        it._labelLines = fp.labelLines;
        it._labelBoxHeight = fp.labelBoxHeight;
        it._combinedHeight = fp.combinedHeight;
        it._labelPlacement = placement;
      }
    }
    // Thread the measured items forward explicitly. These are the SAME objects as
    // ctx.horizontal (mutated in place), so reflow-zones and place-vertical read
    // the same measured objects.
    ctx.measuredVertical = horizontal;
    return ctx;
  },
};

// reflow-zones: the zone-level vertical fold. For each zone it derives the
// content extent from the per-tier maximum combined extents (one row per
// depth_tier, the row as tall as its tallest member), then reflows the scene's
// vertical range (scene.scene_bounds top/bottom) across the zones in depth order,
// producing a ComputedZoneBand per zone. It runs AFTER measure-vertical (it reads
// _combinedHeight) and BEFORE place-vertical (which consumes the bands). It writes
// ONLY ctx.zoneBands and the reflow report fields, never a ComputedItem position
// field, so its mutatesPositions flag is false.
const reflowZonesPhase: Phase = {
  name: "reflow-zones",
  mutatesPositions: false,
  run(ctx, config) {
    // Read the measured items (the SAME objects measure-vertical filled with
    // _combinedHeight). Fall back to ctx.horizontal so the phase still runs if
    // measure-vertical was skipped (those items would lack _combinedHeight, which
    // reflowZones rejects loudly).
    const measured = ctx.measuredVertical ?? ctx.horizontal ?? new Map<string, ComputedItem[]>();
    // zonePad is the resolved object zone padding (the inset from the band edges);
    // tierGap defaults to the depth spacing magnitude (DEPTH_TIER_GAP) inside
    // reflowZones, reusing the engine's existing depth spacing.
    const zonePad = config.spacing.objectZonePadding;
    // labelGap (config.labelOffsetY) is threaded so reflowZones can split each tier
    // row into its scaling object height and its fixed label strip for fixedOverhead
    // It is the SAME gap measure-vertical folded into _combinedHeight.
    const labelGap = config.labelOffsetY;
    const reflow = reflowZones(
      measured,
      ctx.scene.zones ?? [],
      ctx.scene.scene_bounds,
      zonePad,
      undefined,
      labelGap,
    );
    ctx.zoneBands = reflow.bands;
    // Thread the reflow report so run_pipeline can surface it for the terminal
    // uniform object rescale (this phase leaves the honest overflow signal and the
    // compressed bands reflowZones produced).
    ctx.reflowOverflow = reflow.overflow;
    ctx.reflowTotalContent = reflow.totalContent;
    ctx.reflowFixedOverhead = reflow.fixedOverhead;
    ctx.reflowSceneRangeTop = reflow.sceneRangeTop;
    ctx.reflowSceneRangeBottom = reflow.sceneRangeBottom;
    return ctx;
  },
};

// place-vertical: consume the computed zone bands. For each
// item it places the object strip inside its depth-tier row, back-solves the item
// baseline per anchor mode, and assigns the NATURAL object height (no per-object
// shrink). It reads ctx.measuredVertical (the measured items, which still carry
// the post-place-horizontal _centerX / _visualWidth) plus ctx.zoneBands, and
// produces ctx.vertical (fresh items with final _top / _height / _baselineY, the
// measured fields carried forward). place-labels reads ctx.vertical.
const placeVerticalPhase: Phase = {
  name: "place-vertical",
  mutatesPositions: true,
  run(ctx, config) {
    const measured = ctx.measuredVertical ?? ctx.horizontal ?? new Map<string, ComputedItem[]>();
    const bands = ctx.zoneBands ?? new Map<string, ComputedZoneBand>();
    ctx.vertical = verticalLayout(
      measured,
      ctx.scene.zones ?? [],
      bands,
      ctx.viewport,
      ctx.diagnostics,
      config,
    );
    return ctx;
  },
};

const placeLabelsPhase: Phase = {
  name: "place-labels",
  mutatesPositions: true,
  run(ctx, config) {
    // Consume the PLACED items (ctx.vertical): place-vertical now runs after
    // measure-vertical, so ctx.vertical carries the final object geometry AND the
    // measured fields (_labelLines / _labelBoxHeight / _labelPlacement), which
    // place-vertical forwards. ctx.measuredVertical holds the pre-placement
    // geometry (no final _top / _baselineY), so it must NOT be read here.
    const vertical = ctx.vertical ?? new Map<string, ComputedItem[]>();
    // Thread the computed bands so label seed clamps and the stagger ladder clamp
    // against the REFLOWED band, not the authored zone bounds (which became seeds).
    const bands = ctx.zoneBands ?? new Map<string, ComputedZoneBand>();
    ctx.labelled = layoutLabels(
      vertical,
      ctx.scene.zones ?? [],
      ctx.scene.layout_rules ?? {},
      ctx.diagnostics,
      config,
      bands,
    );
    return ctx;
  },
};

// resolve-collisions: global label de-overlap. Reads the placed labels
// (ctx.labelled) plus every object's artwork box and resolves both
// label-vs-artwork and label-vs-label overlaps across all zones, mutating only
// the labels' _labelX / _labelY in place. The vertical moves are DIRECTION-AWARE
// per label placement: a bottom label only steps DOWN toward the padded
// zone floor, a top label only steps UP toward the padded zone top, so a label is
// never pushed across its own object. For an artwork collision the resolver
// enumerates the horizontal nudges plus the natural-direction vertical candidate
// plus a mirrored against-mode fallback when the natural side has no in-zone
// room, and picks the cheapest in-zone clearing move; the per-zone re-stagger
// then ladders each mode group in its own direction. Artwork
// boxes are obstacles and are never moved, so object positions stay exactly as
// place-vertical left them; the downstream validate phase therefore sees
// unchanged item geometry. Drift is measured against each label's IDEAL UNCLAMPED
// seed Y, so the poor_label_alignment Warning fires for clamp-displaced labels too
// and its payload distinguishes clamp drift from collision displacement.
const resolveCollisionsPhase: Phase = {
  name: "resolve-collisions",
  mutatesPositions: true,
  run(ctx, config) {
    const labelled = ctx.labelled ?? new Map<string, ComputedItem[]>();
    // Thread the computed bands so label moves and the per-zone re-stagger clamp
    // against the REFLOWED band, not the authored zone bounds.
    const bands = ctx.zoneBands ?? new Map<string, ComputedZoneBand>();
    ctx.labelDiagnostics = resolveLabelCollisions(
      labelled,
      ctx.scene.zones ?? [],
      ctx.scene.scene_name,
      ctx.diagnostics,
      config,
      bands,
    );
    // resolveLabelCollisions mutates the same ComputedItem objects in place, so
    // ctx.collided is the same map with updated label coordinates.
    ctx.collided = labelled;
    return ctx;
  },
};

// validate: report-only bounds validation. clampSceneBounds measures overflow,
// records a zone_clamped_to_bounds warn in the runtime stream, and pushes a
// structured unresolved_overlap Error into ctx.overflows for any zone that still
// escapes scene_bounds after the vertical auto-fit and convergence shrink. It
// returns its input map unchanged, so this phase does not mutate positions.
//
// It also runs the per-item off-canvas classifier (collectOffCanvasDiagnostics),
// which grades each item independently against scene_bounds as fully_off_canvas
// (error class) or partial_overflow (warning, magnitude-scaled). That closes the
// gap between the zone-bbox overflow above (which can average a fully off-screen
// item back inside) and true per-item off-canvas art. The off-canvas stream is
// REPORT-ONLY and SEPARATE from the build gate: it is stored on ctx.offCanvas and
// surfaced on the result, but nothing reads it to fail or block a build.
//
// mutatesPositions is false: the vertical auto-fit owns the shrink-to-fit, so
// validate only reports. The prior silent group translation was removed when the
// vertical auto-fit stage took over that responsibility.
const validatePhase: Phase = {
  name: "validate",
  mutatesPositions: false,
  run(ctx) {
    const collided = ctx.collided ?? ctx.labelled ?? new Map<string, ComputedItem[]>();
    const overflows: BoundsOverflow[] = [];
    ctx.clamped = clampSceneBounds(
      collided,
      ctx.scene.zones ?? [],
      ctx.scene.scene_bounds,
      ctx.diagnostics,
      overflows,
      ctx.scene.scene_name,
    );
    ctx.overflows = overflows;
    // Report-only per-item off-canvas classification over the same final layout.
    ctx.offCanvas = collectOffCanvasDiagnostics(
      collided,
      ctx.scene.zones ?? [],
      ctx.scene.scene_bounds,
      ctx.scene.scene_name,
    );
    return ctx;
  },
};

// The placement phases run inside the convergence loop. prepare /
// resolve-metadata / measure happen once in run_pipeline (identity resolution);
// report is assembled there from the final context.
export const PLACEMENT_PHASES: readonly Phase[] = [
  partitionPhase,
  placeHorizontalPhase,
  measureVerticalPhase,
  reflowZonesPhase,
  placeVerticalPhase,
  placeLabelsPhase,
  resolveCollisionsPhase,
  validatePhase,
];

// The vertical-placement tail (place-vertical onward). The terminal uniform rescale
// re-runs ONLY these phases once, after horizontal convergence, on the
// scaled measured items + the reflowed bands: it consumes ctx.measuredVertical and
// ctx.zoneBands (which the rescale rewrote) and re-produces ctx.vertical /
// labelled / collided / clamped. The horizontal phases (partition, place-horizontal)
// and the measure/reflow phases are NOT re-run -- horizontal geometry is frozen and
// the rescale already supplied fresh bands, so re-running them would either undo the
// scale or loop the convergence (forbidden). This is the only consumer of this slice.
export const VERTICAL_TAIL_PHASES: readonly Phase[] = [
  placeVerticalPhase,
  placeLabelsPhase,
  resolveCollisionsPhase,
  validatePhase,
];

// Run an ordered list of phases over a context. The driver is intentionally
// trivial: each phase reads the resolved config and returns the (same, mutated)
// context. Determinism comes from the phases, not the driver.
export function runPhases(
  ctx: LayoutContext,
  config: LayoutConfig,
  phases: readonly Phase[],
): LayoutContext {
  let current = ctx;
  for (const phase of phases) {
    current = phase.run(current, config);
  }
  return current;
}
