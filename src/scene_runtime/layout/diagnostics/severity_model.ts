// Severity-graded diagnostic model. Ratified contract:
//   docs/archive/decisions/layout_model_layer_synthesis.md
//   ("Decision metadata") and plan partitioned-shimmying-dragonfly.md
//   ("Diagnostic severity table"; "Actionable payload").
//
// This file implements the severity table as typed data plus the typed
// diagnostic-record shape that carries severity, fail_build, likely owner, a
// YAML pointer, the trigger, and a suggested fix for each diagnostic code. It is
// pure data + helpers: it does NOT emit diagnostics, mutate layout, or read the
// scene. Layout stages call buildDiagnostic(code, ...) when they detect the
// trigger condition for a code.
//
// All coordinates referenced by payloads are scene-percent (0..100 per axis),
// matching the layout engine convention.

import type { ActionablePayload } from "./payload.js";

//============================================
// Closed code, severity, and owner vocabularies
//============================================

// Every diagnostic code this model grades. The set is closed: a new code is a
// vocabulary edit here, not an open string at a call site. Codes cover both the
// legacy runtime Diagnostic.kind set and the severity-graded codes emitted by
// the label, packer, and bounds-validation stages.
export const SEVERITY_DIAGNOSTIC_CODES = [
  // New plan-named codes (emitted by later milestones).
  "asset_clipping",
  "unresolved_label_overlap",
  "unresolved_overlap",
  "heavy_shrink",
  "low_primary_area",
  "poor_label_alignment",
  "excessive_packing",
  "possible_overload",
  "visual_review_unavailable",
  "invalid_scene_schema",
  "missing_asset",
  "impossible_bounds",
  // Preventive never-crop regression guard (M17): an item's whole artwork box
  // sits outside scene_bounds, so the object renders off the visible canvas.
  // Promoted from the report-only offcanvas fully_off_canvas classification.
  "art_below_viewport",
  // D2 "unfittable asset" advisory (M17): an object shrank below the readable
  // floor to fit. Warning only; it names the degradation without failing the build.
  "unfittable_asset",
] as const;

export type SeverityDiagnosticCode = (typeof SEVERITY_DIAGNOSTIC_CODES)[number];

// Three-tier severity. Error fails the build; Warning and Review-required
// surface in the report and allow success.
export type DiagnosticSeverity = "Error" | "Warning" | "Review-required";

// The party most able to act. The build operator may not own pedagogy, so the
// owner routes a diagnostic to the right person.
export type DiagnosticOwner =
  "author" | "author/asset" | "author/engine" | "engine/author" | "pedagogy author" | "reviewer";

// The YAML granularity a diagnostic's pointer can name.
export type YamlPointerLevel = "scene" | "zone" | "placement" | "scene/zone";

//============================================
// Severity-table rule (one row of the plan's table)
//============================================

// One row of the diagnostic severity table. severity + failBuild encode the
// gate behavior; owner + pointerLevel route it; trigger + suggestedFix make the
// emitted message fixable rather than a bare "build failed".
export interface SeverityRule {
  readonly code: SeverityDiagnosticCode;
  readonly severity: DiagnosticSeverity;
  // Error rows fail the build; Warning and Review-required do not.
  readonly failBuild: boolean;
  readonly likelyOwner: DiagnosticOwner;
  readonly pointerLevel: YamlPointerLevel;
  readonly trigger: string;
  readonly suggestedFix: string;
}

// The severity table from plan partitioned-shimmying-dragonfly.md, verbatim in
// severity/owner/trigger/fix. Keyed by code so a stage looks a rule up in O(1).
// Order follows the plan table for readability.
export const SEVERITY_TABLE: Readonly<Record<SeverityDiagnosticCode, SeverityRule>> = Object.freeze(
  {
    invalid_scene_schema: {
      code: "invalid_scene_schema",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author",
      pointerLevel: "scene/zone",
      trigger: "unknown key, missing required field, or bad enum",
      suggestedFix: "fix the named YAML field",
    },
    missing_asset: {
      code: "missing_asset",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author/asset",
      pointerLevel: "placement",
      trigger: "object or SVG asset not found",
      suggestedFix: "add the asset or correct object_name",
    },
    impossible_bounds: {
      code: "impossible_bounds",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author",
      pointerLevel: "zone",
      trigger: "right<=left, bottom<=top, or zone area <= 0",
      suggestedFix: "correct the zone bounds",
    },
    asset_clipping: {
      code: "asset_clipping",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author/engine",
      pointerLevel: "placement",
      trigger: "asset bbox overflows its placement card, or aspect deviation > 5%",
      suggestedFix: "enlarge the zone/card to keep the full asset",
    },
    unresolved_label_overlap: {
      code: "unresolved_label_overlap",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author",
      pointerLevel: "placement",
      trigger: "a label still overlaps another label or artwork after all mechanical fixes",
      suggestedFix: "reduce labels, enlarge the zone, or shorten labels",
    },
    unresolved_overlap: {
      code: "unresolved_overlap",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author",
      pointerLevel: "scene/zone",
      trigger: "objects still overlap after shrink-to-MIN_SCALE + pack",
      suggestedFix: "reduce items, enlarge the zone, or split the zone",
    },
    heavy_shrink: {
      code: "heavy_shrink",
      severity: "Warning",
      failBuild: false,
      likelyOwner: "author",
      pointerLevel: "placement",
      trigger: "item _scale < 0.70 to fit (floor is MIN_SCALE 0.55)",
      suggestedFix: "enlarge the zone or reduce items",
    },
    low_primary_area: {
      code: "low_primary_area",
      severity: "Warning",
      failBuild: false,
      likelyOwner: "author",
      pointerLevel: "scene",
      trigger: "primary object < 15% of scene area",
      suggestedFix: "promote or enlarge the primary object",
    },
    poor_label_alignment: {
      code: "poor_label_alignment",
      severity: "Warning",
      failBuild: false,
      likelyOwner: "engine/author",
      pointerLevel: "placement",
      trigger: "label is clear of overlaps but sits far from its anchor",
      suggestedFix: "tune label_offset_y or zone density",
    },
    excessive_packing: {
      code: "excessive_packing",
      severity: "Warning",
      failBuild: false,
      likelyOwner: "author",
      pointerLevel: "zone",
      trigger: "packer engaged with > N rows or > M items",
      suggestedFix: "split the zone or reduce items",
    },
    possible_overload: {
      code: "possible_overload",
      severity: "Review-required",
      failBuild: false,
      likelyOwner: "pedagogy author",
      pointerLevel: "scene/zone",
      trigger: "scene is dense but still readable",
      suggestedFix: "author reviews teaching priority",
    },
    visual_review_unavailable: {
      code: "visual_review_unavailable",
      severity: "Review-required",
      failBuild: false,
      likelyOwner: "reviewer",
      pointerLevel: "scene",
      trigger: "Claude's vision model or credentials are unavailable",
      suggestedFix: "run human visual review for the scene",
    },
    art_below_viewport: {
      code: "art_below_viewport",
      severity: "Error",
      failBuild: true,
      likelyOwner: "author/engine",
      pointerLevel: "placement",
      trigger: "item artwork box sits fully outside scene_bounds (object renders off-canvas)",
      suggestedFix: "enlarge the zone/scene or reduce items so the asset stays on the canvas",
    },
    unfittable_asset: {
      code: "unfittable_asset",
      severity: "Warning",
      failBuild: false,
      likelyOwner: "author",
      pointerLevel: "placement",
      trigger: "object shrank below the readable floor (final scale < MIN_SCALE) to fit its zone",
      suggestedFix: "enlarge the zone or reduce items so the asset renders at a readable size",
    },
  },
);

//============================================
// Build-gate scene exemptions
//============================================

// Scenes the build gate must NOT fail even when they raise a failBuild:true
// diagnostic. Two categories, both documented and intentional:
//   - intentional-void / dense-by-design scenes: empty or deliberately crowded
//     teaching scenes calibrated before the never-crop gate was wired (M17 risk
//     mitigation). They are aesthetic decisions, not build regressions.
//   - the adversarial_overflow_smoke dev fixture: a capacity stress test authored
//     to fail loudly; it must never gate a real build.
// The gate wiring (M19) reads this set to skip these scenes. The engine still
// REPORTS their diagnostics; only the gate decision is exempted here.
export const BUILD_GATE_EXEMPT_SCENES: ReadonlySet<string> = new Set([
  "hood_basic",
  "microscope_basic",
  "passage_hood_detachment_microscope_view",
  "hemocytometer_view",
  "adversarial_overflow_smoke",
]);

// True when a scene is exempt from the build gate (see BUILD_GATE_EXEMPT_SCENES).
export function isBuildGateExemptScene(sceneName: string): boolean {
  return BUILD_GATE_EXEMPT_SCENES.has(sceneName);
}

//============================================
// YAML pointer
//============================================

// The YAML location a diagnostic refers to. scene_name is always present; zone
// and placement are present per the code's pointerLevel.
export interface YamlPointer {
  readonly scene_name: string;
  readonly zone_name?: string;
  readonly placement_name?: string;
}

//============================================
// Severity-graded diagnostic record
//============================================

// A graded diagnostic. It carries the severity-table row's fixed fields (copied
// from SEVERITY_TABLE at build time) plus the runtime pointer and an optional
// actionable payload. The payload is required in practice for the two overlap
// Errors (unresolved_label_overlap, unresolved_overlap) so the message is
// fixable; other codes may omit it.
export interface SeverityDiagnostic {
  readonly code: SeverityDiagnosticCode;
  readonly severity: DiagnosticSeverity;
  readonly failBuild: boolean;
  readonly likelyOwner: DiagnosticOwner;
  readonly pointer: YamlPointer;
  readonly trigger: string;
  readonly suggestedFix: string;
  // Carried only for codes that build a structured payload (the overlap Errors).
  readonly payload?: ActionablePayload;
}

//============================================
// Builders and predicates
//============================================

// Look up the immutable severity rule for a code.
export function severityRuleFor(code: SeverityDiagnosticCode): SeverityRule {
  return SEVERITY_TABLE[code];
}

// Build a graded diagnostic by copying the code's severity-table row and
// attaching the runtime pointer and optional payload. Stages call this when they
// detect a trigger; the severity, owner, fail-build flag, trigger text, and
// suggested fix all come from the closed table, so a call site cannot invent a
// new severity for a known code.
export function buildDiagnostic(
  code: SeverityDiagnosticCode,
  pointer: YamlPointer,
  payload?: ActionablePayload,
): SeverityDiagnostic {
  const rule = SEVERITY_TABLE[code];
  // Assemble the full record, then return it (no inline object in return).
  const diagnostic: SeverityDiagnostic = {
    code: rule.code,
    severity: rule.severity,
    failBuild: rule.failBuild,
    likelyOwner: rule.likelyOwner,
    pointer,
    trigger: rule.trigger,
    suggestedFix: rule.suggestedFix,
    ...(payload !== undefined ? { payload } : {}),
  };
  return diagnostic;
}

// True when a diagnostic fails the build (any Error). Warnings and
// Review-required return false.
export function failsBuild(diagnostic: SeverityDiagnostic): boolean {
  return diagnostic.failBuild;
}

// Count build-failing diagnostics in a stream. A build is rejected when this is
// greater than zero.
export function countBuildFailures(diagnostics: readonly SeverityDiagnostic[]): number {
  let count = 0;
  for (const d of diagnostics) {
    if (d.failBuild) count += 1;
  }
  return count;
}
