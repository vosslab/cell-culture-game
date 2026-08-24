// Unified layout diagnostics stream.
//
// PipelineResult historically carried four inconsistent diagnostic streams:
//   - `diagnostics`        : the legacy closed-kind Diagnostic[] (identity + placement)
//   - `passes[].diagnostics`: the same closed-kind stream, one array per convergence pass
//   - `severityDiagnostics`: the severity-graded SeverityDiagnostic[] (build gate)
//   - `offCanvasDiagnostics`: the report-only per-item off-canvas classification
//
// Each has its own record shape and its own severity spelling, so a report tool
// had to know all four to answer "what is wrong with this scene". This module
// folds all four into ONE flat, normalized record (UnifiedDiagnostic) so a single
// consumer can read one array. It is the long-term single source of truth reports
// read instead of recomputing from the engine (see the plan's "Diagnostics source
// of truth" note).
//
// The build gate itself stays on `severityDiagnostics` (countBuildFailures reads
// that array). This unified stream is for reporting: `failBuild` is authoritative
// only on the severity-sourced entries; the legacy, pass, and off-canvas entries
// are report-only and carry failBuild:false even when their local grade reads
// "error". A fully-off-canvas item therefore appears twice: once as an off-canvas
// entry (report-only) and once as the promoted art_below_viewport severity entry
// (failBuild:true). The `source` tag distinguishes them, and build-failure counts
// stay correct because only the severity entry sets failBuild.

import type { DiagnosticSeverity, SeverityDiagnostic } from "./severity_model.js";
import type { OffCanvasDiagnostic } from "./offcanvas.js";
import type { Diagnostic, PassRecord } from "../types.js";

//============================================
// Unified record
//============================================

// Which original stream an entry came from. Reports filter on this to recover the
// per-stream view when they need it.
export type UnifiedDiagnosticSource = "legacy" | "pass" | "severity" | "offcanvas";

// One normalized diagnostic. Flat primitive fields only: no nested payload blob,
// so the shape is stable across all four sources. severity is the display grade
// (normalized to the three severity tiers); failBuild is the build-gate flag and
// is true only on severity-sourced Error entries. scene/zone/placement locate the
// finding; pass is set only for pass-sourced entries; message is a short
// human-readable trigger/fix line.
export interface UnifiedDiagnostic {
  readonly source: UnifiedDiagnosticSource;
  readonly code: string;
  readonly severity: DiagnosticSeverity;
  readonly failBuild: boolean;
  readonly scene: string;
  readonly zone?: string;
  readonly placement?: string;
  readonly pass?: number;
  readonly message: string;
}

//============================================
// Severity normalization
//============================================

// Map the legacy Diagnostic severity spelling onto the three-tier display grade.
// "error" -> Error, "warn" -> Warning, "info" -> Review-required (advisory items a
// reviewer should glance at). This is a DISPLAY mapping only; it never sets
// failBuild, which stays false for every legacy entry.
function normalizeLegacySeverity(severity: Diagnostic["severity"]): DiagnosticSeverity {
  if (severity === "error") return "Error";
  if (severity === "warn") return "Warning";
  return "Review-required";
}

// Map the off-canvas report grade onto the display tiers. "error" (fully off
// canvas) -> Error, "warning" (partial overflow) -> Warning. Report-only: the
// build-gate consequence of a fully-off-canvas item is carried by its promoted
// art_below_viewport severity entry, not by this off-canvas entry.
function normalizeOffCanvasSeverity(severity: OffCanvasDiagnostic["severity"]): DiagnosticSeverity {
  return severity === "error" ? "Error" : "Warning";
}

//============================================
// Per-source normalizers
//============================================

// Assemble a short message for a legacy diagnostic from its stage and kind plus
// any measured deltas it carries, so the unified line reads without the caller
// needing the original record.
function legacyMessage(d: Diagnostic): string {
  let message = `${d.stage}: ${d.kind}`;
  if (d.between !== undefined) message += ` (${d.between[0]} <-> ${d.between[1]})`;
  return message;
}

// Normalize one legacy Diagnostic. Legacy entries are always report-only.
function fromLegacy(
  d: Diagnostic,
  sceneName: string,
  source: UnifiedDiagnosticSource,
  pass?: number,
): UnifiedDiagnostic {
  const entry: UnifiedDiagnostic = {
    source,
    code: d.kind,
    severity: normalizeLegacySeverity(d.severity),
    failBuild: false,
    scene: sceneName,
    ...(d.zone !== undefined ? { zone: d.zone } : {}),
    ...(d.placement_name !== undefined ? { placement: d.placement_name } : {}),
    ...(pass !== undefined ? { pass } : {}),
    message: legacyMessage(d),
  };
  return entry;
}

// Normalize one severity-graded diagnostic. This is the only source whose
// failBuild flag is authoritative for the build gate.
function fromSeverity(d: SeverityDiagnostic): UnifiedDiagnostic {
  const entry: UnifiedDiagnostic = {
    source: "severity",
    code: d.code,
    severity: d.severity,
    failBuild: d.failBuild,
    scene: d.pointer.scene_name,
    ...(d.pointer.zone_name !== undefined ? { zone: d.pointer.zone_name } : {}),
    ...(d.pointer.placement_name !== undefined ? { placement: d.pointer.placement_name } : {}),
    message: `${d.trigger} -- ${d.suggestedFix}`,
  };
  return entry;
}

// Normalize one off-canvas classification. Report-only (failBuild false).
function fromOffCanvas(d: OffCanvasDiagnostic): UnifiedDiagnostic {
  const entry: UnifiedDiagnostic = {
    source: "offcanvas",
    code: d.classification,
    severity: normalizeOffCanvasSeverity(d.severity),
    failBuild: false,
    scene: d.scene,
    zone: d.zone,
    placement: d.placementName,
    message: `${d.classification} (worst overshoot ${d.worstOverflow}%, tier ${d.tier})`,
  };
  return entry;
}

//============================================
// Builder
//============================================

// Consolidate the four parallel streams into one normalized array, in a stable
// order: legacy final-stream entries, then per-pass entries in pass order, then
// severity entries, then off-canvas entries. Reads only; mutates nothing.
export function buildUnifiedDiagnostics(input: {
  sceneName: string;
  legacy: readonly Diagnostic[];
  passes: readonly PassRecord[];
  severity: readonly SeverityDiagnostic[];
  offCanvas: readonly OffCanvasDiagnostic[];
}): UnifiedDiagnostic[] {
  const unified: UnifiedDiagnostic[] = [];
  for (const d of input.legacy) unified.push(fromLegacy(d, input.sceneName, "legacy"));
  for (const record of input.passes) {
    for (const d of record.diagnostics) {
      unified.push(fromLegacy(d, input.sceneName, "pass", record.pass));
    }
  }
  for (const d of input.severity) unified.push(fromSeverity(d));
  for (const d of input.offCanvas) unified.push(fromOffCanvas(d));
  return unified;
}
