# TODO

## Current protocol-quality status

The protocol-pedagogy implementation and visible-UI proof are complete. The
`docs/active_plans/reports/protocol_pedagogy_visual_resolution.md` ledger records
the repository-supported outcomes, the full 31-page browser walkthrough, and
the remaining evidence or contract boundaries.

Current follow-ups:

- Obtain faculty-owned inputs for blockers B1-B4 before replacing the fixed,
  internally coherent teaching scenarios.
- Obtain approval for conditional step graphs before implementing B5.
- Decide whether to ratify a closed choice-role capability for B6. Current
  `select` semantics intentionally offer every clickable scene item; a semantic
  choice role would let calculation and interpretation scenes retain visible
  experimental context without presenting that context as an answer.
- Reduce private-YAML snapshot assertions where the same learner-visible
  behavior is already protected by stepper and browser tests. Preserve exact
  quantities only when they are approved scientific invariants.
- Migrate the seven overloaded result SVGs into application-owned UI in a future
  workstream. Keep `cell_viability_results_display.svg`,
  `electrophoresis_endpoint_display.svg`, `gel_image_results_display.svg`,
  `hemocytometer_observation_display.svg`, `mtt_reader_results_display.svg`,
  `plate_reader_absorbance_result_panel.svg`, and
  `plate_reader_normalized_viability_panel.svg` byte-preserved until that work
  begins. The
  [SVG interface scope audit](active_plans/audits/svg_embedded_interface_scope.md)
  defines the migration boundary.

## On hold: scene runtime activation

Big scene-runtime activation plan paused as of 2026-05-17. Gated on the focused
row-based base_scene layout plan. See
[archived scene-runtime activation record](archive/plan-reset-2026-05-22/scene_runtime_activation_on_hold.md)
for state at hold and resumption criteria.

## Stepper and validator follow-ups from 96-well spike

Surfaced by the 96-well authoring shape semantics spike. See
`96_well_authoring_shape_finding.md` (archived) for measured evidence.

### Per-cell state tracking in the protocol stepper (RESOLVED)

`validation/stepper/state.py` now stores independent subpart records, validates
subpart-scoped fields, and preserves per-well material identity and volume. The
cell-culture runner and per-well browser tests exercise the implemented path.

### Optional named-region syntax with members: all shorthand

Deferred from the 96-well spike. Only worth implementing if and when
a real subset use case appears (e.g., a control row, a 2x2 block, a
dose-response group of 4 wells that must carry an experimental name).
For whole-plate cases, `well_plate_96.all_wells` is sufficient and
ships today on `main` without any spec change.

If a real subset use case surfaces:

- Draft a spec amendment for protocol-level `regions:` + region-aware
  `ObjectStateChange` (the shape exercised by the uniform-region spike).
- Include a `members: all` (or equivalent inferred-all) shorthand so
  the region shape is not line-count-penalized when the region
  happens to span the whole plate. The spike found the explicit
  96-member list made the named-region inline form _longer_ than
  the expanded enumeration; this shorthand removes the penalty.
- Reference the spike-only branch `spike/region-stepper` (unmerged)
  for a working validator + stepper implementation of the region
  shape; the branch can be cherry-picked onto a fresh implementation
  branch rather than rewritten from scratch.

Do NOT introduce protocol-level `regions:` as a generic feature.
Reserve for meaningful subsets, not aliases for the whole plate.

## Follow-ups from 96-well enumeration audit

Surfaced by WP-AUDIT-1 of the 96-well cleanup plan. See the
[archived enumeration audit](archive/plan-reset-2026-05-22/workstreams/96_well_enumeration_audit.md)
for full evidence.

### Drug-addition enumeration audit (RESOLVED)

The treatment protocol now groups learner actions around meaningful row and
half-plate dosing skills while retaining per-well state writes needed for the
four experimental condition classes. Browser coverage verifies the visible
condition transitions without requiring per-well endurance clicks.

### Author docs/GLOSSARY.md (REPO-WIDE, all labs)

Single repo-wide file ratifying wet-lab + simulation vocabulary
used across EVERY lab family in `content/protocols/` -- cell
culture, drug dilution, colorimetric assay (MTT), SDS-PAGE
electrophoresis, plus the simulation-side authoring vocabulary.
NOT a one-lab glossary; the cross-lab coverage IS the value.

Triggered by the MTT cleanup (2026-05-16) where MTT etymology,
aspirate vs draw vs dispense, formazan identity, well-total
volume semantics, and trituration all needed clarification. The
same drift class is likely in every other lab area in the repo.

Full acceptance criteria in [ROADMAP.md](ROADMAP.md) "Glossary
doc (planned)" section.

Defer until vocabulary drift surfaces in a second lab family
(MTT alone is insufficient justification for the repo-wide
sweep).

### Vocabulary: "aspirate" reserved for vacuum removal to waste

Lab convention: "aspirate" means vacuum-line removal to waste (e.g.,
"aspirate spent media from the plate"). Pipette loading from a source uses
"draw," "load," or "pipette up," not "aspirate." The manual renderer uses
"draw" for dispensing-pipette uptake, and the protocol validator protects the
same distinction in learner-facing prompts.

This is an active schema-validation gate. The protocol validator rejects a
learner-facing prompt that uses "aspirate" unless the step uses the dedicated
`aspirating_pipette` for vacuum removal. The current protocol corpus is clean:
remaining occurrences describe removal to waste rather than loading a
dispensing pipette.

Action for new content: use "draw," "load," or "pipette up" for
dispensing-pipette uptake. Reserve "aspirate" for vacuum removal to waste.

### Pipette accuracy: MTT 25 uL near low edge of P200 multichannel

`mtt_plate_reaction.add_mtt_to_wells` dispenses 25 microL per
channel. That sits in the lower-precision zone of a standard P200
multichannel (range 20-200 microL; accuracy degrades from ~3% mid-
range to ~5-10% at 20-25 microL). For dose-response assay rigor,
consider redesigning MTT prep: e.g., 100 microL of 3 mM MTT (instead
of 25 microL of 12 mM) gives same 300 nmol per well at a more
accurate pipette volume. Cascades back through Q6: post-MTT well
total changes from 225 to 300, decant + incubation volumes shift.
Defer until next wet-lab protocol revision; current YAML carries a
note in the prompt about freshly-calibrated tips.

### Renderer: multichannel aggregate-volume display

Renderer currently emits per-channel volume in dispense bullets
(e.g., "draw 25 uL from the 12 mM MTT solution") without noting
the multichannel aggregation (8 channels x 25 uL = 200 uL per
stroke drawn from the bottle). Wet-lab students may mis-interpret
the bottle drawdown rate. Possible fix: when source target is a
multichannel pipette, append "(per channel; 8 x N = M uL per
stroke)" to the dispense bullet.

### Cosmetic: validation.manual phrasing for group targets

Rendered manual for an `all_wells` target reads "the well
all_wells of the 96-well plate". Awkward but not wrong. The
renderer should special-case region / block groups to read
"every well of the 96-well plate" or similar natural phrasing.
Scope: `validation/manual/protocol_manual.py`.

### MTT solubilization action wording (RESOLVED 2026-08-03)

The current protocol models twelve visible multichannel column strokes and
describes the repeated whole-plate distribution skill consistently. The stale
whole-plate `all_wells` wording mismatch no longer applies.

## Rendering and content display

### Fix unit rendering for browser-displayed YAML labels (RESOLVED 2026-07-05)

Resolved: the author-entity -> codegen-decode -> DOM-glyph convention is now
the documented, canonical rendering path. Authors write HTML entities in
committed YAML (`&micro;M`, `&alpha;`); codegen decodes each entity to its
Unicode glyph at the string-emit choke point, so `generated/**` carries the
real character; the runtime renders that string as a plain DOM text node,
never `innerHTML`. See the "Glyph rendering" convention in
[specs/MATERIAL_YAML_FORMAT.md](specs/MATERIAL_YAML_FORMAT.md#glyph-rendering),
cross-linked from `OBJECT_YAML_FORMAT.md`, `PROTOCOL_YAML_FORMAT.md`, and
`PROTOCOL_AUTHORING_GUIDE.md`. The prior `uL`/`uM` ASCII stopgap is retired.

## Pre-existing failures surfaced during M1b (2026-05-09)

These were uncovered while landing M1b of the SVG asset pipeline refactor
(plan ref: `~/.claude/plans/cuddly-snuggling-feather.md`). The reviewer
bisected against HEAD with M1b changes reverted and reproduced both
failures, so they are pre-existing and not caused by M1b. Surfaced here for
triage; M1c does NOT fix either. See the M1b CHANGELOG entry under
`## 2026-05-09` for the full context.

### Walker `interactionSequence` regression on hood scenes (RESOLVED 2026-05-09)

- Outcome: fixed. Root cause was the capture-phase click handler in
  `scene_driver.ts` calling
  `target.getAttribute('data-item-id')` on the raw click target, which is
  often an inner SVG shape (`ellipse`/`rect`/`path`) inside the `.hood-item`
  wrapper, not the wrapper itself. After a `directTool` step that called
  `renderHoodScene()` directly (skipping `runSceneRender`), the per-item
  bubble-phase listeners from
  `hood_shared.ts`
  were not re-attached on the rebuilt DOM, leaving only the capture-phase
  listener -- and that listener could not resolve the data-item-id from a
  nested SVG element. Fix: resolve the nearest ancestor via
  `target.closest('[data-item-id]')` before reading the id. See the
  CHANGELOG entry under `## 2026-05-09` `### Fixes and Maintenance` for
  full evidence (cell_culture 25/25, all 10 protocols pass, smoke 9/9,
  tsc clean).

### `tests/_compile_for_test.mjs` missing helper (RESOLVED 2026-05-09)

- Outcome: fixed. M6 of the SVG asset pipeline refactor authored the
  missing helper at `tests/_compile_for_test.mjs`
  (uses `npx esbuild --bundle --platform=node --define:window=globalThis`
  to compile a `.ts` entry to a tempdir `.mjs` and dynamic-import it).
  Both `test_svg_color_patch.mjs`
  and the new `test_svg_pipeline.mjs`
  use the helper to exercise production `.ts` modules directly. See the
  M6 CHANGELOG entry under `## 2026-05-09` for full evidence.

## V3 numeric-range violations follow-up

**Resolved 2026-05-17.** All three sites fixed pedagogically:

- [x] `content/protocols/cell_seeding_plate_setup/protocol.yaml`: wrong instrument
      class (micropipette max 1000 uL used for mL-range transfers). Fixed: switched to
      serological_pipette; values converted uL->mL (2400->2.4, 9600->9.6). Also fixed
      bonus bug: `well_plate_96.all_wells material_volume` 9600->100 uL per well.
- [x] `content/protocols/mtt_plate_reaction/protocol.yaml`: biohazard_decant_bin
      `material_volume` 21600 mL was mL/uL unit confusion (21600 uL total = 21.6 mL).
      Fixed: 21600->21.6.
- [x] `content/protocols/passage_hood_detachment/protocol.yaml`: trypsin_bottle
      max:100 was too small; protocol assumes 500 mL stock (consistent with pbs_bottle
      and media_bottle). Fixed: trypsin_bottle max/default 100->500; protocol value
      197->497.

Equipment V7 WARNINGs also resolved (same run):

- hemocytometer added `material_container` capability (was missing; caused WARNING).
- V7 gate refined: now warns only when equipment has material fields but lacks
  `material_container` capability (previously warned on any equipment with material fields).

## Deferred / future work

### V6b: WCAG contrast gate on material YAML palette (deferred)

Dropped from the spec-content-drift-remediation plan (see
[spec_content_drift_remediation.md](archive/spec_content_drift_remediation.md)
Objective #3). Reason: no current consumer renders material `display_color`
as a color swatch; the gate is forward-looking until a theme-aware visual
consumer ships. The gate should be included in the future "SVG asset
accessibility audit" follow-up plan as part of a WCAG audit on hard-coded
SVG fills. Note: V6a (cross-protocol material consistency) is deferred - `validation/yaml/cross_protocol.py`
lines 43-45 carry a "Deferred" comment. The gate was planned in
`docs/archive/spec_content_drift_remediation.md` WP-V6 but not implemented before plan
archive. Manual reconciliation of 9 divergent materials was done (CHANGELOG 2026-05-17),
but the automated enforcement gate does not yet exist. A future protocol addition could
re-introduce the same divergence silently.

### Authored SVG asset-reference gate (resolved)

The material overlay variant-collapse plan closed (see
[archive/material_overlay_vocabulary.md](archive/material_overlay_vocabulary.md)),
and `tests/test_object_asset_refs.py` now hard-asserts `missing == []` against
the recursive SVG registry. New authored `asset_name` gaps fail the fast suite
instead of drifting a baseline count.

- (RESOLVED) Per-well distinct material state for `well_plate_96` -- material plan
  COMPLETE (plan `dynamic-coalescing-flask.md` M0-M4). Per-well material state (834
  `state_value_not_allowed` -> 0), registry-backed material acceptance, scalar color
  resolution, PATH-B subpart geometry, and production render-path per-well color are all
  done. Per-well render proven via production Playwright harness
  (`tests/playwright/test_subpart_well_plate_render.spec.ts`). Per-well fill rendering is
  also implemented through `fill_height`; the object now declares material identity and
  amount only on well subparts, with no obsolete object-level material placeholders.

- (RESOLVED 2026-08-03) Visible `adjust` uses the in-flow set-point editor and
  completes through the same runtime-authoritative validator path as other
  gestures. Per-well protocols and all 31 generated protocol pages now complete
  through the visible Playwright walker.

- (#27, FUTURE, not this plan) Declared registry-backed field affordance: retire the
  `[empty, mixed]` syntactic seam in `well_plate_96.yaml`. Currently the runtime accepts
  registry-backed drug material names via `seed_target` + validated `set_object_state`,
  but the YAML `allowed` field is `[empty, mixed]`. A future affordance would make the
  registry-backed field explicitly declared in the object schema so the enum is not a
  conflicting surface. Scope: object schema + validator + generator changes; no runtime
  behavior change required.

## Solid runtime polish (follow-up, not blocking)

The current Solid implementation is broadly idiomatic; these are non-blocking refinements.

- Review imperative `createEffect` calls that only stamp `data-*` attributes onto DOM
  nodes. Where practical, replace them with JSX attribute bindings so Solid owns the DOM
  update directly.
- Consider a shared Solid SVG loading/error component (or boundary) later; do not refactor
  the current `createResource` path unless real duplication or an error-handling problem
  appears.
- Preserve the rule that SVG DOM access stays isolated behind the injection/lookup layer
  (`injectSvgFromManifest` / `resolveAnchor`); runtime state and control flow stay in Solid
  stores/signals, never DOM queries.
