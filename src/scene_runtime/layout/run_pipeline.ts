// Top-level pipeline runner, expressed over a phase registry (see phases.ts and
// the phase model documented in docs/specs/LAYOUT_ENGINE.md).
//
// Identity resolution (the prepare / resolve-metadata / measure phases:
// normalize -> inheritance -> bind -> scale) runs once. The placement phases
// (partition -> place-horizontal -> place-vertical -> place-labels ->
// resolve-collisions -> validate) run inside the bounded convergence loop, up to
// config.maxPasses. Per-pass detail is recorded in result.passes. The last
// pass's stage maps are exposed via result.stages. report is assembled here from
// the final context.
//
// Output is byte-identical to the prior inline 10-stage pipeline: same phase
// order, same per-pass diagnostics, same shrink step, same final assembly.

import { DEFAULT_VIEWPORT, READABLE_FLOOR_SCALE, WORKSPACE_PX_PER_CM } from "./constants.js";
import { bindObjects } from "./bind_objects.js";
import { buildGlobalDefaults, resolveConfig } from "./config/index.js";
import {
  buildDecisionMetadata,
  buildPackZoneDecision,
  buildRowZoneDecision,
} from "./diagnostics/decision_metadata.js";
import { collectItemOverlapDiagnostics } from "./diagnostics/item_overlap.js";
import { collectUnfittableAssets, promoteBelowViewport } from "./diagnostics/promote.js";
import { buildUnifiedDiagnostics } from "./diagnostics/unified.js";
import { normalizeSchema } from "./normalize_schema.js";
import { lowerSceneZones } from "./lower_semantic_zones.js";
import { resolveInheritance } from "./resolve_inheritance.js";
import { scaleToRealWorld } from "./scale_to_real_world.js";
import { PLACEMENT_PHASES, VERTICAL_TAIL_PHASES, runPhases } from "./phases.js";
import { applyUniformRescale } from "./vertical_layout.js";
import { derive_scene_interaction_geometry } from "./interaction_geometry.js";
import type { LayoutConfig } from "./config/index.js";
import type { PackerZoneOutcome } from "./strategies/index.js";
import type { LayoutContext } from "./phases.js";
import type {
  AssetSpecs,
  ComputedItem,
  ComputedZoneBand,
  Diagnostics,
  GroupedPlacements,
  ObjectLibrary,
  PassRecord,
  PipelineInputs,
  PipelineResult,
  ResolvedScene,
  ScaledPlacement,
  SceneA,
} from "./types.js";

// Diagnostic kinds that drive the convergence loop's per-zone _width_scale
// shrink + re-entry. These are HORIZONTAL fit signals only: a zone whose items
// overflow its WIDTH is shrunk on the horizontal axis and re-placed.
//
// item_escapes_zone_vertically is intentionally NOT here. A vertical escape is a
// HEIGHT problem; shrinking a zone's width to fix it is the wrong lever (it was
// the legacy mechanism this reflow plan removes). Vertical now contributes only
// measured extents (the measure-vertical stage) and leaves _width_scale to the
// horizontal stage; item_escapes_zone_vertically remains in the diagnostics
// stream as a scene-level reflow-overflow signal (surfaced in the scene-wide
// uniform object rescale and the scene_reflow_overflow diagnostic).
// Decoupling it here lets the loop iterate on horizontal signals only.
const FITTABLE_KINDS = new Set(["zone_overflow_negative_gap", "tab_stop_overflow"]);

export function runPipeline(scene: SceneA, opts: Partial<PipelineInputs> = {}): PipelineResult {
  const library: ObjectLibrary = opts.library ?? {};
  const assets: AssetSpecs = opts.assets ?? {};
  const baseSceneMap = opts.baseSceneMap ?? {};
  const viewport = opts.viewport ?? DEFAULT_VIEWPORT;
  const workspacePxPerCm = opts.workspacePxPerCm ?? WORKSPACE_PX_PER_CM;
  const diagnostics: Diagnostics = [];

  // Identity resolution (prepare / resolve-metadata / measure), single pass.
  const normalized = normalizeSchema(scene);
  const sourceScene = normalized.scene ?? scene;
  const inheritance = resolveInheritance(sourceScene, baseSceneMap);
  const bound = bindObjects(inheritance.placements, library, assets, diagnostics);
  let scaled: ScaledPlacement[] = scaleToRealWorld(
    bound,
    sourceScene.workspace,
    { workspacePxPerCm },
    diagnostics,
  );
  // Lower source-zone meaning only after binding and real-world scaling. This
  // gives the planner actual object footprints and label reserves while keeping
  // sourceScene geometry-free and immutable.
  const normalScene = lowerSceneZones(sourceScene, scaled);

  const identityDiagCount = diagnostics.length;

  // Resolve the scene-wide LayoutConfig once. Runtime opts (maxPasses,
  // shrinkFactor) still override the resolved defaults; this keeps the existing
  // PipelineInputs override points working while routing the loop tunables
  // through LayoutConfig.
  const baseConfig = resolveConfig(
    buildGlobalDefaults(),
    normalScene.layout_rules ?? {},
    undefined,
    {},
    {},
    normalScene.zones ?? [],
  );
  const config: LayoutConfig = applyRuntimeOverrides(baseConfig, opts);
  const maxPasses = config.maxPasses;
  const shrinkFactor = config.shrinkFactor;

  // Convergence loop over the placement phases. After each pass, items in zones
  // that emitted fittable diagnostics get their _width_scale multiplied by
  // shrinkFactor. The loop re-enters only on new fittable diagnostics and caps
  // at maxPasses, so it cannot loop or vary between builds.
  const passes: PassRecord[] = [];
  let lastCtx: LayoutContext | undefined;
  let lastPassDiagnostics: Diagnostics = [];

  for (let pass = 0; pass < maxPasses; pass++) {
    const passDiagnostics: Diagnostics = [];
    const ctx: LayoutContext = {
      scene: normalScene,
      viewport,
      scaled,
      diagnostics: passDiagnostics,
    };
    lastCtx = runPhases(ctx, config, PLACEMENT_PHASES);

    const fittable = passDiagnostics.filter((d) => FITTABLE_KINDS.has(d.kind));
    const passRecord: PassRecord = {
      pass: pass + 1,
      diagnostics: [...passDiagnostics],
      zones_shrunk: [],
    };
    passes.push(passRecord);
    lastPassDiagnostics = passDiagnostics;

    if (fittable.length === 0) break;

    if (pass === maxPasses - 1) {
      passDiagnostics.push({
        stage: "meta",
        severity: "warn",
        kind: "max_iterations_reached",
        passes_used: maxPasses,
        unresolved: fittable.length,
      });
      lastPassDiagnostics = passDiagnostics;
      break;
    }

    const zonesToShrink = new Set<string>();
    for (const d of fittable) {
      if (d.zone !== undefined) zonesToShrink.add(d.zone);
    }
    passRecord.zones_shrunk = [...zonesToShrink];
    scaled = scaled.map((p): ScaledPlacement =>
      zonesToShrink.has(p.zone)
        ? {
            ...p,
            _width_scale: p._width_scale * shrinkFactor,
            _shrunk_passes: (p._shrunk_passes ?? 0) + 1,
          }
        : p,
    );
  }

  // Terminal uniform object rescale. After horizontal convergence, if the
  // reflow reported the measured content overflows the scene range, shrink every
  // object by ONE scene-wide factor (aspect preserved) and re-run the vertical
  // placement tail ONCE on the scaled items + reflowed bands. This is a terminal
  // scalar: it does NOT re-enter the convergence loop and leaves _width_scale to
  // the horizontal stage. When no overflow was reported the rescale is skipped and
  // the result reports uniformScale 1 / no scene overflow / no label dominance.
  let reflowUniformScale = 1;
  let sceneReflowOverflow = false;
  let labelDominant = false;
  if (lastCtx !== undefined && lastCtx.reflowOverflow === true) {
    const measured =
      lastCtx.measuredVertical ?? lastCtx.horizontal ?? new Map<string, ComputedItem[]>();
    const rescale = applyUniformRescale(
      measured,
      normalScene.zones ?? [],
      normalScene.scene_bounds,
      lastCtx.reflowTotalContent ?? 0,
      lastCtx.reflowFixedOverhead ?? 0,
      viewport,
      config,
    );
    reflowUniformScale = rescale.uniformScale;
    sceneReflowOverflow = rescale.stillOverflow;
    labelDominant = rescale.labelDominant;

    // Re-run the vertical-placement tail on the scaled items + reflowed bands. The
    // tail re-emits the stage `vertical` / `labels` / `clamp` diagnostics for the
    // RESCALED placement, so drop the pre-rescale tail diagnostics from the last
    // pass (the head-phase `group` / `horizontal` diagnostics are unchanged and
    // kept) before re-running with a fresh sink, then splice the fresh tail
    // diagnostics back in. This keeps the final diagnostics consistent with the
    // rescaled geometry instead of reporting the superseded pre-rescale placement.
    const TAIL_STAGES = new Set(["vertical", "labels", "clamp"]);
    const headDiagnostics = lastPassDiagnostics.filter((d) => !TAIL_STAGES.has(d.stage));
    const tailDiagnostics: Diagnostics = [];
    lastCtx.measuredVertical = rescale.scaledMeasured;
    lastCtx.zoneBands = rescale.bands;
    lastCtx.diagnostics = tailDiagnostics;
    lastCtx = runPhases(lastCtx, config, VERTICAL_TAIL_PHASES);
    // reflowOverflow / reflowTotalContent on the result deliberately stay at the
    // PRE-rescale reflow report: they are the raw "how overfull is this scene"
    // demand signal the scene-scale tool reads, so the rescale must not overwrite
    // them. The post-rescale state lives in the new reflowUniformScale /
    // sceneReflowOverflow / labelDominant fields. The tail re-run does not touch
    // these (only reflow-zones writes them, and reflow-zones is not in the tail).
    lastPassDiagnostics = [...headDiagnostics, ...tailDiagnostics];

    // Repurposed scene-level item_escapes_zone_vertically signal: emit it into the
    // runtime diagnostics stream when the scaled content STILL overflows at the
    // dedicated floor. It carries no placement_name (scene scope) so a consumer can
    // distinguish it from the per-item escape the place-vertical fallback emits.
    if (sceneReflowOverflow) {
      lastPassDiagnostics.push({
        stage: "vertical",
        severity: "warn",
        kind: "item_escapes_zone_vertically",
      });
    }
  }

  for (const d of lastPassDiagnostics) diagnostics.push(d);

  // report: assemble the final ComputedItem[] and the stage maps from the last
  // context. clamped is the validate-phase output (report-only bounds check).
  const finalGrouped: GroupedPlacements = lastCtx?.grouped ?? { groups: new Map(), orphans: [] };
  const finalHorizontal = lastCtx?.horizontal ?? new Map<string, ComputedItem[]>();
  const finalVertical = lastCtx?.vertical ?? new Map<string, ComputedItem[]>();
  const finalLabelled = lastCtx?.labelled ?? new Map<string, ComputedItem[]>();
  const finalClamped = lastCtx?.clamped ?? new Map<string, ComputedItem[]>();
  // reflow-zones output from the final pass. Surfaced on the result for
  // verification and consumed by place-vertical; not serialized into the precompute
  // artifact, so the artifact stays byte-identical run-to-run.
  const finalZoneBands = lastCtx?.zoneBands ?? new Map<string, ComputedZoneBand>();
  // reflow-zones overflow report from the final pass. Defaults mirror an empty
  // scene (no overflow, zero content, scene_bounds range) so a
  // scene that produced no bands still returns coherent numbers.
  const finalReflowOverflow = lastCtx?.reflowOverflow ?? false;
  const finalReflowTotalContent = lastCtx?.reflowTotalContent ?? 0;
  const finalReflowSceneRangeTop = lastCtx?.reflowSceneRangeTop ?? normalScene.scene_bounds.top;
  const finalReflowSceneRangeBottom =
    lastCtx?.reflowSceneRangeBottom ?? normalScene.scene_bounds.bottom;

  const final: ComputedItem[] = [];
  for (const zone of normalScene.zones ?? []) {
    for (const it of finalClamped.get(zone.id) ?? []) final.push(it);
  }

  // Cross-zone final-placed-item overlap check. The per-band checks
  // above (place-horizontal, resolve-collisions) never compare two items whose
  // zones got transitively fused into one computed band, so a real 100% render
  // overlap could otherwise report overlap_count 0. This scans the FINAL item
  // array -- every zone at once, the same boxes the renderer and
  // structural_guards.ts Guard 3 use -- so it closes that blind spot
  // independent of how band membership is computed upstream.
  for (const d of collectItemOverlapDiagnostics(final)) diagnostics.push(d);

  // Build per-scene decision metadata, separate from the diagnostics array.
  // Packer outcomes from the final pass: zones the dispatcher packed record a
  // "pack" ZoneDecision; all other zones record the row strategy with the
  // convergence-loop uniform per-zone shrink (derived from _shrunk_passes).
  const packerDecisions: Map<string, PackerZoneOutcome> =
    lastCtx?.packerDecisions ?? new Map<string, PackerZoneOutcome>();
  const decisionMetadata = buildSceneDecisionMetadata(
    normalScene,
    finalClamped,
    config,
    opts,
    packerDecisions,
  );

  // Surface the severity-graded Errors/Warnings/Reviews from the final pass.
  // Two sources, both kept SEPARATE from the closed-kind `diagnostics` stream:
  //   - the resolve-collisions label de-overlap
  //     (unresolved_label_overlap, poor_label_alignment, possible_overload), and
  //   - the report-only validate phase's unresolved_overlap bounds Errors.
  // The vertical auto-fit shrinks tall items to fit, so a non-empty overflow list
  // means an item still escaped scene_bounds at the MIN_SCALE floor after the
  // convergence loop exhausted its shrink budget. Taking the LAST context avoids
  // reporting a transient diagnostic that a later pass resolved.
  const labelDiagnostics = lastCtx?.labelDiagnostics ?? [];
  const boundsDiagnostics = (lastCtx?.overflows ?? []).map((o) => o.diagnostic);
  // unresolved_overlap Errors the packer emitted for zones it could not fit even
  // at MIN_SCALE. Kept SEPARATE from the closed-kind diagnostics stream, surfaced
  // here alongside the label and bounds severity diagnostics.
  const packerDiagnostics = lastCtx?.packerSeverity ?? [];

  // Report-only per-item off-canvas classification from the final pass's validate
  // phase. Kept SEPARATE from the closed-kind diagnostics stream: it is purely
  // informational. The fully_off_canvas subset is ALSO promoted below into a
  // build-failing severity Error, but the raw report-only stream stays as-is.
  const offCanvasDiagnostics = lastCtx?.offCanvas ?? [];

  // Preventive never-crop regression guard: promote each fully_off_canvas
  // item to a build-failing art_below_viewport severity Error. This is a
  // regression guard -- 0 real scenes trip it today (the historical below-viewport
  // clipping was fixed by the uniform rescale); it fails loud if one ever
  // regresses. The build gate exempts the documented
  // intentional-void scenes and the adversarial dev fixture via
  // isBuildGateExemptScene; the engine still reports the diagnostic here.
  const belowViewportDiagnostics = promoteBelowViewport(offCanvasDiagnostics);

  // "Unfittable asset" advisory: a Warning (never fails the build) for
  // each final item shrunk below the readable floor to fit its zone. It names the
  // objects the dense shrink scenes squeezed past a readable size without blocking
  // the build (the ~20 shrink scenes stay green).
  const unfittableDiagnostics = collectUnfittableAssets(
    final,
    normalScene.scene_name,
    READABLE_FLOOR_SCALE,
  );

  const severityDiagnostics = [
    ...labelDiagnostics,
    ...boundsDiagnostics,
    ...packerDiagnostics,
    ...belowViewportDiagnostics,
    ...unfittableDiagnostics,
  ];

  // Unified diagnostics: fold the four parallel streams into one normalized array
  // for report tooling (the long-term single source of truth). The build gate
  // stays on severityDiagnostics; this stream is report-facing.
  const unifiedDiagnostics = buildUnifiedDiagnostics({
    sceneName: normalScene.scene_name,
    legacy: diagnostics,
    passes,
    severity: severityDiagnostics,
    offCanvas: offCanvasDiagnostics,
  });

  return {
    scene: normalScene,
    sourceScene: scene,
    diagnostics,
    passes,
    identityDiagCount,
    stages: {
      inputs: { scene, library, assets },
      normalized,
      inheritance,
      bound,
      scaled,
      grouped: finalGrouped,
      horizontal: finalHorizontal,
      vertical: finalVertical,
      labelled: finalLabelled,
      clamped: finalClamped,
    },
    final,
    interactionGeometry: derive_scene_interaction_geometry(final),
    decisionMetadata,
    severityDiagnostics,
    offCanvasDiagnostics,
    unifiedDiagnostics,
    zoneBands: finalZoneBands,
    reflowOverflow: finalReflowOverflow,
    reflowTotalContent: finalReflowTotalContent,
    reflowSceneRangeTop: finalReflowSceneRangeTop,
    reflowSceneRangeBottom: finalReflowSceneRangeBottom,
    reflowUniformScale,
    sceneReflowOverflow,
    labelDominant,
  };
}

// Assemble the per-scene DecisionMetadata from the final per-zone layouts. Each
// zone records the row strategy plus the actual per-item shrink the convergence
// loop applied (shrinkFactor raised to the item's _shrunk_passes count). The
// resolved config is re-resolved per zone so each ZoneDecision.resolvedConfig
// reflects that zone's overrides. This reads the final layout only; it mutates
// nothing.
function buildSceneDecisionMetadata(
  scene: ResolvedScene,
  clamped: Map<string, ComputedItem[]>,
  config: LayoutConfig,
  opts: Partial<PipelineInputs>,
  packerDecisions: Map<string, PackerZoneOutcome>,
): ReturnType<typeof buildDecisionMetadata> {
  const zoneDecisions = [];
  for (const zone of scene.zones ?? []) {
    const items = clamped.get(zone.id) ?? [];
    // Per-item shrink applied = shrinkFactor ^ (passes this item was shrunk).
    // An unshrunk item records 1 (no shrink), matching current behavior.
    const shrinkApplied: Record<string, number> = {};
    for (const it of items) {
      const passes = it._shrunk_passes ?? 0;
      shrinkApplied[it.placement_name] = config.shrinkFactor ** passes;
    }
    // Re-resolve the config for this specific zone so its align/baseline/spacing
    // overrides are folded into resolvedConfig.
    const zoneBaseConfig = resolveConfig(
      buildGlobalDefaults(),
      scene.layout_rules ?? {},
      zone,
      {},
      {},
      scene.zones ?? [],
    );
    const zoneConfig = applyRuntimeOverrides(zoneBaseConfig, opts);

    // If the dispatcher packed this zone, record the packer's decision (its
    // non-uniform per-item shrink, the required row scale, and the result).
    // Otherwise record the row decision with the convergence-loop shrink.
    const packed = packerDecisions.get(zone.id);
    if (packed !== undefined) {
      zoneDecisions.push(
        buildPackZoneDecision({
          zoneId: zone.id,
          resolvedConfig: zoneConfig,
          requiredRowScale: packed.requiredRowScale,
          packerResult: packed.packerResult,
          rowsCreated: packed.rowsCreated,
          shrinkApplied: packed.shrinkApplied,
        }),
      );
    } else {
      zoneDecisions.push(
        buildRowZoneDecision({
          zoneId: zone.id,
          resolvedConfig: zoneConfig,
          shrinkApplied,
        }),
      );
    }
  }
  const metadata = buildDecisionMetadata(scene.scene_name, zoneDecisions);
  return metadata;
}

// Apply the runtime PipelineInputs override points (maxPasses, shrinkFactor)
// onto the resolved config. These are not authored YAML but real override
// points carried by PipelineInputs; folding them here keeps resolveConfig the
// single merge surface while preserving the existing opts behavior.
function applyRuntimeOverrides(base: LayoutConfig, opts: Partial<PipelineInputs>): LayoutConfig {
  if (opts.maxPasses === undefined && opts.shrinkFactor === undefined) return base;
  // Freeze the override result so a stage cannot accidentally mutate the
  // shared config, matching resolveConfig()/buildGlobalDefaults() which both
  // freeze their output.
  const overridden: LayoutConfig = Object.freeze({
    ...base,
    maxPasses: opts.maxPasses ?? base.maxPasses,
    shrinkFactor: opts.shrinkFactor ?? base.shrinkFactor,
  });
  return overridden;
}
