// Promotions from report-only signals to severity-graded diagnostics.
//
// Two promotions live here, both turning an existing report-only observation into
// a graded SeverityDiagnostic the severity stream (and, later, the build gate)
// can act on:
//   - promoteBelowViewport: each fully_off_canvas off-canvas finding becomes a
//     build-failing art_below_viewport Error. This is the PREVENTIVE never-crop
//     regression guard; 0 real scenes trip it today.
//   - collectUnfittableAssets: each final item shrunk below the readable floor
//     becomes an advisory unfittable_asset Warning (never fails the build).
//
// Both are pure: they read their inputs and return new diagnostics, mutating
// nothing. Keeping them here (rather than inline in run_pipeline) gives the two
// promotions one testable home and keeps run_pipeline's assembly readable.

import { buildDiagnostic } from "./severity_model.js";
import type { OffCanvasDiagnostic } from "./offcanvas.js";
import type { SeverityDiagnostic, YamlPointer } from "./severity_model.js";
import type { ComputedItem } from "../types.js";

//============================================
// Below-viewport promotion (never-crop regression guard)
//============================================

// Promote every fully_off_canvas off-canvas finding to a build-failing
// art_below_viewport Error. partial_overflow findings are left in the report-only
// off-canvas stream and are NOT promoted (they still touch the canvas). Returns
// one Error per fully-off-canvas item, in input order; an empty list means no
// item is fully off canvas.
export function promoteBelowViewport(
  offCanvas: readonly OffCanvasDiagnostic[],
): SeverityDiagnostic[] {
  const promoted: SeverityDiagnostic[] = [];
  for (const oc of offCanvas) {
    if (oc.classification !== "fully_off_canvas") continue;
    const pointer: YamlPointer = {
      scene_name: oc.scene,
      zone_name: oc.zone,
      placement_name: oc.placementName,
    };
    promoted.push(buildDiagnostic("art_below_viewport", pointer));
  }
  return promoted;
}

//============================================
// Unfittable-asset advisory (D2 warning-only)
//============================================

// Emit an advisory unfittable_asset Warning for each item whose final rendered
// scale fell below the readable floor. An item only reaches a sub-floor scale
// through the terminal uniform rescale (the horizontal stage floors at MIN_SCALE),
// so this names the objects a dense scene squeezed past a readable size. Warning
// only: it never fails the build. Returns one Warning per unfittable item, in
// input order.
export function collectUnfittableAssets(
  items: readonly ComputedItem[],
  sceneName: string,
  readableFloor: number,
): SeverityDiagnostic[] {
  const unfittable: SeverityDiagnostic[] = [];
  for (const it of items) {
    if (it._scale >= readableFloor) continue;
    const pointer: YamlPointer = {
      scene_name: sceneName,
      zone_name: it.zone,
      placement_name: it.placement_name,
    };
    unfittable.push(buildDiagnostic("unfittable_asset", pointer));
  }
  return unfittable;
}
