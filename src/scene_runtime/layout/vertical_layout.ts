// Stage 8: Vertical placement -- consumes the computed zone bands.
//
// This stage runs AFTER measure-vertical and reflow-zones. Those stages measured
// each item's side-independent combined extent (object height + label offset +
// wrapped label box) and reflowed the scene's vertical range into a computed band
// per zone, each band carrying its depth-tier rows (one row per depth_tier, the
// row as tall as its tallest member, spaced top-to-bottom with the tier gap). This
// stage derives ONE shared baseline (shelf line) per tier row and anchors every
// item in the row to it, so a row of unequal-height objects sits on one common line.
//
// heightPct = visualWidth * (viewport.w / viewport.h) / aspect. Keeps pixel
// aspect invariant regardless of viewport shape (percent units are per-axis).
//
// Objects keep their NATURAL height (no per-object shrink). The reflow already
// reserved a row tall enough for object + gap + label, so the object never needs to
// be squeezed to make room for its label. A scene whose measured content exceeds the
// scene range is handled by the scene-wide uniform object rescale, not by a
// per-object shrink here. Keeping natural height makes "an object covers its own
// label" structurally impossible and is never-crop safe by construction (aspect is
// never distorted, the artwork is never clipped to a too-short card).
//
// Bottom-anchor placement: the row shelf baseline sits at the row bottom, pulled UP
// by any bottom-side label reserve and floored so the tallest object stays framed
// (see rowBaselineFor). An item's anchor_y maps the shared baseline to its _top:
// "bottom" (the default) puts the object bottom on the shelf; "tip" hangs the object
// by its tip; "top" is a centered engine fallback. Because the whole row shares one
// baseline, every bottom/tip object's bottom edge lands on the same line. _baselineY
// stores that shared shelf line; the label stage seeds labels from the object box
// (_top, _height), not from _baselineY.

import { DEFAULT_VIEWPORT, LABEL_DOMINANT_RATIO, UNIFORM_RESCALE_MIN_SCALE } from "./constants.js";
import { buildGlobalDefaults } from "./config/index.js";
import { reflowZones } from "./reflow_zones.js";
import type { LayoutConfig } from "./config/index.js";
import type {
  ComputedItem,
  ComputedZoneBand,
  Diagnostics,
  LabelPlacement,
  SceneBoundsRect,
  Zone,
} from "./types.js";

// Compute the _top edge for an item of the given height under its anchor mode,
// given the shared row baseline (the shelf line). For the default "bottom" anchor
// the object bottom sits on the baseline, so a row of unequal-height objects that
// share one baseline sits on one common shelf line. "tip" hangs the object by its
// tip (adjusted by anchor_y_offset, 0 for every current pipette); "top" is a
// centered engine fallback (no current scene authors it).
function anchorTop(it: ComputedItem, baseline: number, heightPct: number): number {
  if (it.layout.anchor_y === "bottom") {
    return baseline - heightPct;
  }
  if (it.layout.anchor_y === "tip") {
    return baseline + it.layout.anchor_y_offset - heightPct;
  }
  // anchor_y === "top" falls through here and is treated as "center"
  // (top = baseline - height/2). It is the engine fallback only.
  return baseline - heightPct / 2;
}

// The vertical measures the row-baseline pre-pass and the placement step both read
// for one item: its natural (aspect-preserving) height, its resolved label side, and
// its wrapped label-strip height. _labelPlacement carries the scene-wide default
// folded in by measure-vertical; it.layout.label_placement is the per-placement
// override; "top" is the final fallback for a direct-call test that skipped measure.
interface VerticalMeasure {
  naturalHeight: number;
  placement: LabelPlacement;
  labelBoxHeight: number;
}

function measureItem(
  it: ComputedItem,
  viewportAspect: number,
  aspectFloor: number,
): VerticalMeasure {
  const aspect = Math.max(aspectFloor, it.aspect);
  // Natural height at the current horizontal scale; width and height share one
  // factor, so aspect is preserved exactly (never-crop safe by construction).
  const naturalHeight = (it._visualWidth * viewportAspect) / aspect;
  const placement: LabelPlacement = it._labelPlacement ?? it.layout.label_placement ?? "top";
  const labelBoxHeight = it._labelBoxHeight ?? 0;
  return { naturalHeight, placement, labelBoxHeight };
}

// One tier row's placement inputs: its top and reserved height from the reflow band
// plus the vertical measures of its member items. A shelf spans one or more of these
// (the same depth tier across the side-by-side zones of a band).
interface TierRowMeasures {
  zone: string;
  rowTop: number;
  rowHeight: number;
  members: TierRowMember[];
}

// A member keeps its own row and anchor information attached to the vertical
// measure.  A cross-zone shelf can only be adopted when the candidate anchor
// leaves the COMPLETE object-plus-label extent inside every member's own row.
// Keeping this association here avoids guessing from a zone or placement name.
interface TierRowMember {
  placementName: string;
  item: ComputedItem;
  measure: VerticalMeasure;
}

// The shared baseline (shelf line) every item on one visible shelf anchors to. A
// shelf is one depth tier across the side-by-side zones that share a reflow band, so
// bottles standing in a row of adjacent zones land their bottom edges on ONE line
// instead of each floating at its own height. All bottom- and tip-anchored objects
// on the shelf place their bottom edge on this line.
//
// The shelf sits at the LOWEST row bottom in the set (max(rowTop + rowHeight)), so
// the tallest column defines the line; it is pulled UP by the largest bottom-side
// label reserve so those labels stay inside their row (a top-side label sits above
// the object and needs no reserve). The `floor` term keeps every object's TOP edge at
// or below its own row top (containment): when an object is taller than its measured
// row, the floor wins and the shelf drops to keep the object framed rather than
// pushing its top above the row.
function shelfBaselineFor(rows: TierRowMeasures[], labelGap: number): number {
  let maxRowBottom = -Infinity;
  let reserve = 0;
  let floor = -Infinity;
  for (const row of rows) {
    if (row.rowTop + row.rowHeight > maxRowBottom) maxRowBottom = row.rowTop + row.rowHeight;
    for (const { measure: m } of row.members) {
      if (m.placement === "bottom") reserve = Math.max(reserve, labelGap + m.labelBoxHeight);
      if (row.rowTop + m.naturalHeight > floor) floor = row.rowTop + m.naturalHeight;
    }
  }
  const shelf = maxRowBottom - reserve;
  return Math.max(shelf, floor);
}

// True when placing `member` on `baseline` leaves both the artwork and its
// initial label strip within the member's own computed tier row.  This mirrors
// place-vertical's anchor formula and place-labels' initial label seed exactly;
// later collision resolution may move labels, but shelf selection must never
// start from an extent that already escapes its reflow reservation.
function memberFitsRow(
  member: TierRowMember,
  row: TierRowMeasures,
  baseline: number,
  labelGap: number,
): boolean {
  const objectTop = anchorTop(member.item, baseline, member.measure.naturalHeight);
  const objectBottom = objectTop + member.measure.naturalHeight;
  // Direct stage tests may intentionally skip measure-vertical. A zero-height
  // label means there is no rendered strip (and therefore no gap to reserve).
  let labelTop = objectTop;
  let labelBottom = objectBottom;
  if (member.measure.labelBoxHeight > 0) {
    labelTop =
      member.measure.placement === "top"
        ? objectTop - labelGap - member.measure.labelBoxHeight
        : objectBottom + labelGap;
    labelBottom = labelTop + member.measure.labelBoxHeight;
  }
  const extentTop = Math.min(objectTop, labelTop);
  const extentBottom = Math.max(objectBottom, labelBottom);
  const rowBottom = row.rowTop + row.rowHeight;
  return extentTop >= row.rowTop && extentBottom <= rowBottom;
}

function shelfFitsRows(rows: TierRowMeasures[], baseline: number, labelGap: number): boolean {
  return rows.every((row) =>
    row.members.every((member) => memberFitsRow(member, row, baseline, labelGap)),
  );
}

// Group the zones' computed bands into shelves by AUTHORED vertical bounds: only
// truly side-by-side zones (a horizontal row authored at the same top..bottom, like
// rear_left / rear_center / rear_right) form one shelf, so their same-depth-tier
// objects align on one line. Zones the reflow merely fused for a partial vertical
// overlap (a center band and a front band that touch) keep their OWN shelves, because
// they are stacked working surfaces, not one horizontal row. Zones with no computed
// band are omitted (the caller places those via the fallback).
function groupBandsByAuthoredRow(
  zones: Zone[],
  zoneBands: Map<string, ComputedZoneBand>,
): ComputedZoneBand[][] {
  const byKey = new Map<string, ComputedZoneBand[]>();
  for (const zone of zones) {
    const band = zoneBands.get(zone.id);
    if (band === undefined) continue;
    const key = `${zone.bounds.top}:${zone.bounds.bottom}`;
    const list = byKey.get(key) ?? [];
    list.push(band);
    byKey.set(key, list);
  }
  return [...byKey.values()];
}

export function verticalLayout(
  zoneLayouts: Map<string, ComputedItem[]>,
  zones: Zone[],
  zoneBands: Map<string, ComputedZoneBand>,
  viewport: { w: number; h: number } = DEFAULT_VIEWPORT,
  diagnostics: Diagnostics = [],
  config: LayoutConfig = buildGlobalDefaults(),
): Map<string, ComputedItem[]> {
  const viewportAspect = viewport.w / viewport.h;
  const aspectFloor = config.aspectFloor;
  // The gap between the object strip and a bottom-side label strip. It is the SAME
  // label_offset_y the measure-vertical stage folded into _combinedHeight, so the
  // shelf reserve computed here matches the reserved row height.
  const labelGap = config.labelOffsetY;

  // Measure every item once. placement_name is unique scene-wide, so one global map
  // serves both the shelf pre-pass (which crosses zones) and the placement step.
  const measureByName = new Map<string, VerticalMeasure>();
  const itemByName = new Map<string, ComputedItem>();
  for (const zone of zones) {
    for (const it of zoneLayouts.get(zone.id) ?? []) {
      measureByName.set(it.placement_name, measureItem(it, viewportAspect, aspectFloor));
      itemByName.set(it.placement_name, it);
    }
  }

  // Derive ONE shared baseline per shelf: one depth tier across the side-by-side
  // zones that share a reflow band. Every object on that shelf maps to the same
  // baseline, so a row of adjacent bottles of unequal height lands its bottom edges
  // on one line instead of each floating at its own height.
  const baselineByName = new Map<string, number>();
  for (const bandGroup of groupBandsByAuthoredRow(zones, zoneBands)) {
    // Collect the group's tier rows (across its side-by-side zones) keyed by
    // depth_tier; each depth tier becomes one shelf carrying its member rows and the
    // placement names that anchor to it.
    const shelvesByTier = new Map<number, { rows: TierRowMeasures[]; names: string[] }>();
    for (const band of bandGroup) {
      for (const row of band.tiers) {
        const members: TierRowMember[] = [];
        for (const name of row.placementNames) {
          const m = measureByName.get(name);
          const item = itemByName.get(name);
          if (m !== undefined && item !== undefined) {
            members.push({ placementName: name, item, measure: m });
          }
        }
        const shelf = shelvesByTier.get(row.depthTier) ?? { rows: [], names: [] };
        shelf.rows.push({
          zone: band.id,
          rowTop: row.rowTop,
          rowHeight: row.rowHeight,
          members,
        });
        shelf.names.push(...row.placementNames);
        shelvesByTier.set(row.depthTier, shelf);
      }
    }
    for (const shelf of shelvesByTier.values()) {
      if (!shelf.rows.some((row) => row.members.length > 0)) continue;
      const sharedBaseline = shelfBaselineFor(shelf.rows, labelGap);
      // One row has no cross-zone alignment to trade off, so preserve its
      // existing baseline exactly. Feasibility is only a cross-zone concern.
      if (shelf.rows.length === 1 || shelfFitsRows(shelf.rows, sharedBaseline, labelGap)) {
        for (const name of shelf.names) baselineByName.set(name, sharedBaseline);
        continue;
      }

      // A shared shelf is an alignment preference, not permission to consume a
      // neighbour's row.  Demote this entire depth tier to one shelf per zone row;
      // members in the same zone remain aligned, while every affected placement
      // receives a deterministic review warning.
      for (const row of shelf.rows) {
        if (row.members.length === 0) continue;
        const localBaseline = shelfBaselineFor([row], labelGap);
        for (const member of row.members) {
          baselineByName.set(member.placementName, localBaseline);
          diagnostics.push({
            stage: "vertical",
            severity: "warn",
            kind: "item_escapes_zone_vertically",
            zone: row.zone,
            placement_name: member.placementName,
          });
        }
      }
    }
  }

  const result = new Map<string, ComputedItem[]>();
  for (const zone of zones) {
    const items = zoneLayouts.get(zone.id) ?? [];
    const updated = items.map((it): ComputedItem => {
      const measure = measureByName.get(it.placement_name);
      if (measure === undefined) {
        // Every item was measured just above, so a missing measure means the map was
        // corrupted. Fail loud rather than place an unmeasured object.
        throw new Error(
          `verticalLayout: item "${it.placement_name}" in zone "${zone.id}" was not measured`,
        );
      }
      const naturalHeight = measure.naturalHeight;

      // An authored baseline_override pins the object baseline directly (rare; no
      // current content uses it). It bypasses the shelf so an explicit author intent
      // still wins. Object geometry then derives from that baseline.
      if (it.baseline_override !== undefined) {
        const baseline = it.baseline_override;
        const placed: ComputedItem = {
          ...it,
          _baselineY: baseline,
          _top: anchorTop(it, baseline, naturalHeight),
          _height: naturalHeight,
        };
        return placed;
      }

      // The shared shelf baseline for this item. Without a band (a direct-call test
      // that skipped reflow-zones) or when the item is in no row (a pipeline-ordering
      // bug), fall back to a one-item shelf at the zone's authored band top so the
      // object still places deterministically and a diagnostic fires.
      let baseline = baselineByName.get(it.placement_name);
      if (baseline === undefined) {
        diagnostics.push({
          stage: "vertical",
          severity: "warn",
          kind: "item_escapes_zone_vertically",
          zone: zone.id,
          placement_name: it.placement_name,
        });
        const rowHeight = naturalHeight + labelGap + measure.labelBoxHeight;
        baseline = shelfBaselineFor(
          [
            {
              zone: zone.id,
              rowTop: zone.bounds.top,
              rowHeight,
              members: [{ placementName: it.placement_name, item: it, measure }],
            },
          ],
          labelGap,
        );
      }

      const placed: ComputedItem = {
        ...it,
        _baselineY: baseline,
        _top: anchorTop(it, baseline, naturalHeight),
        _height: naturalHeight,
      };
      return placed;
    });

    result.set(zone.id, updated);
  }

  return result;
}

//============================================
// Terminal uniform object rescale
//============================================

// The result of the scene-wide uniform object rescale. scaledMeasured is the
// measured-items map with every object's dimensions multiplied by uniformScale and
// its combined extent recomputed; bands are the zone bands reflowed from those
// scaled extents (the caller feeds both into place-vertical). uniformScale is the
// one factor applied to every object's width AND height (aspect preserved).
// stillOverflow is true when the required scale fell BELOW the dedicated floor
// (the raw ratio sceneRange/totalContent < UNIFORM_RESCALE_MIN_SCALE, so the
// uniformScale was clamped up to the floor and even the floor-scaled objects cannot
// bring the content within the scene range). labelDominant is true when any item's
// label strip is at least LABEL_DOMINANT_RATIO of its scaled object height.
// newTotalContent is the reflowed content extent after scaling, surfaced for the
// report.
export interface UniformRescaleResult {
  scaledMeasured: Map<string, ComputedItem[]>;
  bands: Map<string, ComputedZoneBand>;
  uniformScale: number;
  stillOverflow: boolean;
  labelDominant: boolean;
  newTotalContent: number;
}

// The scene-wide uniform object scale factor plus whether it was clamped up to the
// floor. The factor shrinks ONLY the scalable (object-height) portion of the content:
//
//   scalableContent = totalContent - fixedOverhead
//   raw = (sceneRange - fixedOverhead) / scalableContent
//
// fixedOverhead is the part of totalContent the object rescale does NOT shrink: zone
// padding, tier gaps, and per-tier fixed label strips (label gap + label box height).
// Sizing the scale against the scalable remainder makes the post-scale content land
// at sceneRange (fixedOverhead + raw*scalableContent == sceneRange), instead of the
// old sceneRange/totalContent which left fixedOverhead of content past the bottom.
//
// clamped is min(1, max(floor, raw)). The upper clamp of 1 means the rescale never
// ENLARGES an object. The floor is the dedicated vertical terminal-fallback floor
// UNIFORM_RESCALE_MIN_SCALE, distinct from the horizontal packer MIN_SCALE (0.55).
// clampedToFloor records when raw < floor: the required shrink was below the floor,
// so even floor-scaled objects leave the scene over its range -- the "still over at
// the floor" condition the diagnostic reports.
interface UniformScaleDecision {
  uniformScale: number;
  clampedToFloor: boolean;
}

function uniformScaleFor(
  totalContent: number,
  fixedOverhead: number,
  sceneRange: number,
): UniformScaleDecision {
  if (sceneRange <= 0 || totalContent <= 0) {
    return { uniformScale: 1, clampedToFloor: false };
  }
  const scalableContent = totalContent - fixedOverhead;
  const availableForObjects = sceneRange - fixedOverhead;
  // Degenerate overload: the fixed overhead (padding, tier gaps, fixed label strips)
  // alone meets or exceeds the scene range, or there is no object height to shrink.
  // The scene cannot fit even at zero object size -- a real overload to flag, not to
  // crop. Fall back to the MIN_SCALE floor and report it via clampedToFloor so the
  // scene_reflow_overflow diagnostic fires; do not divide by a non-positive scalable.
  if (scalableContent <= 0 || availableForObjects <= 0) {
    return { uniformScale: UNIFORM_RESCALE_MIN_SCALE, clampedToFloor: true };
  }
  const raw = availableForObjects / scalableContent;
  const clamped = Math.min(1, Math.max(UNIFORM_RESCALE_MIN_SCALE, raw));
  // clampedToFloor: the unclamped ratio fell below the floor, so the floor is the
  // binding constraint and the scaled content still exceeds the scene range.
  const clampedToFloor = raw < UNIFORM_RESCALE_MIN_SCALE;
  return { uniformScale: clamped, clampedToFloor };
}

// The maximum scale-refinement iterations. The per-tier row height is
// max(s*objectHeight + fixedLabel), a piecewise-linear function of s whose winning
// row can switch as s shrinks (a label-heavy short object overtakes a tall object
// once both shrink). The closed-form uniformScaleFor assumes a FIXED winning row, so
// after the first scale a different row may win and leave content slightly past the
// scene bottom. A bounded fixed-point refinement re-measures the post-scale content
// and recomputes the scale until the winning rows stabilize. The max function is
// monotone and deterministic, so this converges in a few steps; the cap is a safety
// bound, not an expected limit.
const UNIFORM_RESCALE_MAX_REFINE = 8;
// Convergence tolerance for the refinement: stop once the post-scale content sits at
// or below the scene range within this scene-percent slack. Tight enough that no art
// visibly crosses the bottom, loose enough to stop on float noise.
const UNIFORM_RESCALE_FIT_TOLERANCE = 1e-6;

// Measure the post-scale reflow content for a candidate scale: scale the object
// portion of each item's combined extent, re-reflow, and return the reflow's
// totalContent + fixedOverhead at that scale. Pure read of the measured map. Used by
// the fixed-point refinement to account for winning-row switches the closed-form
// scale cannot see; it does not mutate measured or build the final scaled map.
function measureScaledContent(
  measured: Map<string, ComputedItem[]>,
  zones: Zone[],
  sceneBounds: SceneBoundsRect,
  scale: number,
  viewportAspect: number,
  aspectFloor: number,
  labelGap: number,
  zonePad: number,
): { totalContent: number; fixedOverhead: number } {
  const probe = new Map<string, ComputedItem[]>();
  for (const zone of zones) {
    const items = measured.get(zone.id) ?? [];
    const scaledItems = items.map((it): ComputedItem => {
      const aspect = Math.max(aspectFloor, it.aspect);
      const scaledVisualWidth = it._visualWidth * scale;
      const scaledObjectHeight = (scaledVisualWidth * viewportAspect) / aspect;
      const labelBoxHeight = it._labelBoxHeight ?? 0;
      const scaledCombined = scaledObjectHeight + labelGap + labelBoxHeight;
      const scaled: ComputedItem = { ...it, _combinedHeight: scaledCombined };
      return scaled;
    });
    probe.set(zone.id, scaledItems);
  }
  const reflow = reflowZones(probe, zones, sceneBounds, zonePad, undefined, labelGap);
  return { totalContent: reflow.totalContent, fixedOverhead: reflow.fixedOverhead };
}

// Refine the object scale to a fixed point so the POST-scale reflow content fits the
// scene range. Starts from the closed-form scale, then re-measures the scaled
// content and recomputes the scale against the post-scale fixed overhead until the
// content fits within tolerance or the floor binds. Each step uses the recurrence
//   s_next = s * (sceneRange - fixedOverhead_s) / (totalContent_s - fixedOverhead_s)
// which re-targets the object portion measured AT the current scale, so a winning-row
// switch between steps is absorbed. The result never drops below the floor; a scene
// that still overflows at the floor reports clampedToFloor (a real overload).
function refineUniformScale(
  measured: Map<string, ComputedItem[]>,
  zones: Zone[],
  sceneBounds: SceneBoundsRect,
  totalContent: number,
  fixedOverhead: number,
  viewportAspect: number,
  aspectFloor: number,
  labelGap: number,
  zonePad: number,
): UniformScaleDecision {
  const sceneRange = sceneBounds.bottom - sceneBounds.top;
  // Closed-form first guess from the pre-scale content.
  const initial = uniformScaleFor(totalContent, fixedOverhead, sceneRange);
  let scale = initial.uniformScale;
  // The closed-form already clamped to the floor: the scene cannot fit above the
  // floor, so refinement cannot help. Return it as the real, reportable overload.
  if (initial.clampedToFloor) return initial;
  // No shrink needed (content fit at scale 1); nothing to refine.
  if (scale >= 1) return initial;

  let clampedToFloor = false;
  for (let i = 0; i < UNIFORM_RESCALE_MAX_REFINE; i++) {
    const measuredAt = measureScaledContent(
      measured,
      zones,
      sceneBounds,
      scale,
      viewportAspect,
      aspectFloor,
      labelGap,
      zonePad,
    );
    const overflowNow = measuredAt.totalContent - sceneRange;
    // Within tolerance (at or under the range): the winning rows have stabilized and
    // the content fits. Done.
    if (overflowNow <= UNIFORM_RESCALE_FIT_TOLERANCE) break;
    const scalableAt = measuredAt.totalContent - measuredAt.fixedOverhead;
    const availableAt = sceneRange - measuredAt.fixedOverhead;
    // The fixed overhead measured at this scale already meets/exceeds the range, or
    // there is no scalable object height left: a real overload at any object size.
    if (scalableAt <= 0 || availableAt <= 0) {
      scale = UNIFORM_RESCALE_MIN_SCALE;
      clampedToFloor = true;
      break;
    }
    // Re-target the object portion measured AT this scale to exactly fill the range.
    const next = scale * (availableAt / scalableAt);
    if (next <= UNIFORM_RESCALE_MIN_SCALE) {
      // The refinement wants to shrink below the floor: pin to the floor and report
      // the overload. The floor-scaled content still exceeds the range.
      scale = UNIFORM_RESCALE_MIN_SCALE;
      clampedToFloor = true;
      break;
    }
    scale = next;
  }
  return { uniformScale: scale, clampedToFloor };
}

// Apply the scene-wide uniform object rescale and re-run the zone reflow ONCE.
//
// This is the terminal vertical fallback. It runs AFTER horizontal
// convergence, on the measured items (post measure-vertical, carrying
// _visualWidth / _combinedHeight / _labelBoxHeight / _labelPlacement). It scales
// OBJECT dimensions only -- _visualWidth, _scale, and the natural object height
// folded into _combinedHeight -- by ONE factor applied to both axes, so the aspect
// ratio is preserved exactly (never-crop safe by construction). Label line height,
// label gap (labelOffsetY), tier gap, and zone padding stay FIXED (canvas-relative):
// _labelBoxHeight and _labelPlacement are carried through unchanged, and the reflow
// re-uses the same fixed tierGap / zonePad. The combined extent is recomputed once
// as scaledObjectHeight + fixedLabelGap + fixedLabelBoxHeight, then reflowZones runs
// once on the scaled extents to produce fresh bands. It does NOT touch _centerX,
// _footprint, or _width_scale: horizontal geometry is owned by the horizontal stage
// and this fallback never routes back through the convergence loop.
//
// It is pure: it reads the measured map and returns a fresh scaled map plus the
// reflowed bands. The caller (run_pipeline) feeds the scaled map and bands into
// place-vertical to finish placement.
export function applyUniformRescale(
  measured: Map<string, ComputedItem[]>,
  zones: Zone[],
  sceneBounds: SceneBoundsRect,
  totalContent: number,
  fixedOverhead: number,
  viewport: { w: number; h: number } = DEFAULT_VIEWPORT,
  config: LayoutConfig = buildGlobalDefaults(),
): UniformRescaleResult {
  const viewportAspect = viewport.w / viewport.h;
  const aspectFloor = config.aspectFloor;
  // The fixed gap between the object strip and the label strip. It is the SAME
  // label_offset_y measure-vertical folded into _combinedHeight; it does NOT scale.
  const labelGap = config.labelOffsetY;
  const zonePad = config.spacing.objectZonePadding;
  // Size the object scale against only the SCALABLE remainder of the content (the
  // object heights), leaving the fixed overhead (padding, tier gaps, label strips)
  // untouched, then refine to a fixed point so the POST-scale content (whose winning
  // tier rows may switch as objects shrink) lands inside the scene range instead of
  // overshooting it. The result is still ONE uniform factor applied to both
  // axes; refinement only sharpens that single scalar.
  const decision = refineUniformScale(
    measured,
    zones,
    sceneBounds,
    totalContent,
    fixedOverhead,
    viewportAspect,
    aspectFloor,
    labelGap,
    zonePad,
  );
  const uniformScale = decision.uniformScale;

  // Scale every object's dimensions by the one factor and recompute its combined
  // extent. The natural object height shares the factor with the width (one scalar,
  // both axes), so aspect is preserved. The label strip (_labelBoxHeight) and the
  // gap (labelGap) are added back UNSCALED, so the label is never shrunk with the
  // object.
  let labelDominant = false;
  const scaledMeasured = new Map<string, ComputedItem[]>();
  for (const zone of zones) {
    const items = measured.get(zone.id) ?? [];
    const scaledItems = items.map((it): ComputedItem => {
      const aspect = Math.max(aspectFloor, it.aspect);
      const scaledVisualWidth = it._visualWidth * uniformScale;
      // The scaled natural object height. Width and height share the one factor, so
      // this is exactly uniformScale * the pre-scale natural height.
      const scaledObjectHeight = (scaledVisualWidth * viewportAspect) / aspect;
      const labelBoxHeight = it._labelBoxHeight ?? 0;
      // Recompute the side-independent combined extent with the FIXED label gap and
      // label box height, only the object portion shrunk.
      const scaledCombined = scaledObjectHeight + labelGap + labelBoxHeight;
      // labelDominant review flag: the label strip is large relative to the now
      // smaller object. Guard the divide; a zero-height object cannot be dominated.
      if (scaledObjectHeight > 0 && labelBoxHeight / scaledObjectHeight >= LABEL_DOMINANT_RATIO) {
        labelDominant = true;
      }
      const scaled: ComputedItem = {
        ...it,
        _visualWidth: scaledVisualWidth,
        _scale: it._scale * uniformScale,
        _combinedHeight: scaledCombined,
      };
      return scaled;
    });
    scaledMeasured.set(zone.id, scaledItems);
  }

  // Re-run the zone reflow ONCE on the scaled extents. tierGap and zonePad default
  // to the same fixed constants the reflow phase threads, so the only thing that
  // changed between reflows is the per-item object height. The fresh bands place the
  // scaled objects; when the scaled content still exceeds the range (the fixed
  // label/gap/padding portion does not shrink) reflowZones compresses each group to
  // its content extent and stacks from the top, which is the honest tight placement.
  // zonePad was resolved above (shared with the scale refinement). Thread labelGap so
  // the re-reflow's fixedOverhead is computed the same way as the pre-scale reflow.
  const reflow = reflowZones(scaledMeasured, zones, sceneBounds, zonePad, undefined, labelGap);

  // stillOverflow is the "still over at the floor" condition: the required scale fell
  // below the dedicated floor, so even floor-scaled objects cannot fit the content.
  // It is NOT reflow.overflow on the scaled extents -- the fixed label/gap/padding
  // portion keeps that flag set for most rescaled scenes even when the object shrink
  // was the intended, accepted result. Only a clamp at the floor is a real, reportable
  // overflow (the scene needs more shrink than the floor allows).
  const out: UniformRescaleResult = {
    scaledMeasured,
    bands: reflow.bands,
    uniformScale,
    stillOverflow: decision.clampedToFloor,
    labelDominant,
    newTotalContent: reflow.totalContent,
  };
  return out;
}
