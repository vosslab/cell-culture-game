# Plan: SVG equipment consistency sweep

## Context

The equipment library began with SVGs from several unrelated Bioicons sources,
locally drawn assets, and state-specific derivatives. Their visual grammars differ
substantially. This sweep uses only the Servier Medical Art subset of Bioicons as
the external style reference, removes its excessive detached floor shadows, and
brings the retained equipment library into one restrained visual dialect.

The target is generic laboratory equipment: unbranded, model-independent, and
recognizable from its silhouette and minimum characteristic parts. Generic design
is a success condition. An asset needs revision only when it is visually
inconsistent, over-shadowed, or ambiguous enough to read as the wrong object class.

The exact source-by-source disposition and protected result-screen hashes live in
the [SVG consistency sweep ledger](../reports/svg_consistency_sweep.md). This plan owns
the execution sequence and acceptance gates; the ledger owns the 186-row inventory.

## Objectives

- Establish one documented de-shadowed Servier visual dialect for retained equipment SVGs.
- Apply that dialect to 139 retained SVGs without flattening useful form, glass, or liquid cues.
- Remove 40 approved unreachable SVGs after repeatable reachability checks.
- Preserve seven result composites byte-for-byte and keep their future application-UI migration in `docs/TODO.md` and `docs/ROADMAP.md`.
- Preserve material rendering hooks, semantic anchors, state distinctions, asset bindings, and real delivery behavior.
- Finish with automated structural and production-shaped browser evidence, independent source and visual review, and a labeled SVG contact sheet for human inspection.

## Design philosophy

Use the repository's **fix the design, not the symptom** philosophy: define one
visual acceptance dialect and apply it consistently instead of accumulating
per-file exceptions. Prefer restrained value separation, overlap, and local
material shading over detached floor shadows or decorative effects. Preserve
generic recognition cues while excluding brand- and model-specific decoration.

- Evidence strategy for uncertain methods: compare source and rendered output at thumbnail and source scale, validate through the real compiler and browser path, and resolve ambiguous cases by independent visual review.

## Scope

- Document the visual acceptance dialect in `docs/specs/SVG_PIPELINE.md`.
- Maintain an exact edit/delete/protected ledger for the 186 baseline SVGs.
- Repair the shadow-removal dry-run path and keep one focused behavior regression.
- Remove the 40 approved unreachable assets and reconcile provenance and audit links.
- Retire authored missing-SVG placeholders and generated placeholder-key
  compatibility so unresolved object assets fail at generation and impossible
  internal layout states use renderer-owned diagnostics.
- Enforce one compiled SVG form for paired runtime material bindings at the
  object-validation boundary.
- Parse Servier provenance by explicit source-path grammar and keep one focused parser regression.
- Edit the 139 retained assets in small, independently reviewable families.
- Preserve family-level viewBox, projection, palette, state distinction, and semantic interfaces.
- Validate normalized XML, local references, materials, manifests, compiled output, and production browser behavior.
- Produce a self-contained labeled SVG contact sheet containing every final retained SVG.
- Record completion evidence in the plan, ledger, changelog, and current-work documentation.

## Non-goals

- Migrate the seven result composites into typed application state or accessible DOM UI; preserve their files unchanged and retain that future work in `docs/TODO.md` and `docs/ROADMAP.md`.
- Make non-Servier Bioicons sources into additional style authorities.
- Recreate Servier artwork pixel-for-pixel or retain its detached floor-shadow treatment.
- Add brand, manufacturer, or model-specific details to otherwise generic equipment.
- Change protocol learning behavior, material vocabulary, visual layout
  algorithms, or the primary contract beyond the approved strict-resolution,
  internal-diagnostic, and one-form material-binding cleanup.
- Use pixel equivalence as the artistic acceptance gate.
- Treat the final contact sheet as a shipped application asset; it is a review artifact.

## Current state summary

Status date: 2026-08-24.

<!-- prettier-ignore -->
| Area                        | Status          | Current evidence                                                                                                             |
| --------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Visual dialect and ledger   | Complete        | Servier-only target, de-shadowing rule, and 186-row disposition are documented.                                              |
| Shadow-removal tooling      | Complete        | Dry-run formatting is fixed and one focused behavior regression passes.                                                       |
| Approved cleanup            | Complete        | 40 unreachable SVGs and the superseded liquid-census helper are removed.                                                     |
| Gold-set calibration        | Complete        | Eight representative SVGs passed source and visual re-review after recognition-cue repairs.                                  |
| Remaining retained SVGs     | Complete        | Seventeen bounded work packages edited the other 131 retained SVGs.                                                          |
| Source-interface review     | Complete        | Lost anchors, live prose, and geometry-affecting CSS findings were repaired and re-reviewed.                                 |
| Visual stream review        | Complete        | All four asset streams passed independent visual review.                                                                     |
| Repository validation       | Revalidation blocked | The SVG-sweep tree passed; the later vendored refresh added failing permanent gates, so combined-tree proof is pending. |
| Final labeled contact sheet | Complete        | The labeled all-SVG contact sheet is the final review artifact.                                                               |
| Human visual acceptance     | Pending review  | Human inspection begins from the repository-linked final labeled contact sheet.                                              |

The intended integrated tree contains 139 modified retained SVGs, 40 deleted
unreachable SVGs, and seven protected result composites with no byte changes.

## Architecture boundaries and ownership

- `assets/equipment/**`: authored SVG source of truth.
- `content/objects/**` and scene YAML: existing asset bindings and placements
  remain; the authored missing-SVG compatibility field is retired.
- `docs/specs/SVG_PIPELINE.md`: canonical SVG visual and normalization guidance.
- `tools/normalize_svg_v3.py`: developer normalization and shadow-removal implementation.
- `pipeline/**`: production generation and compilation; validation consumer, not a duplicated generator target.
- `docs/active_plans/reports/svg_consistency_sweep.md`: exact disposition ledger and protected hashes.
- `docs/figures/final_equipment_contact_sheet.svg`: committed, self-contained human-review snapshot.
- `docs/EQUIPMENT_SVG_CONTACT_SHEET.md`: GitHub-accessible review page and direct figure link.
- `test-results/svg-consistency/**`: ignored construction evidence and oversized raster preview.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component                              | Review boundary                                              |
| ---------------------- | -------------------------------------- | ------------------------------------------------------------ |
| M1 / WS-P prerequisite | SVG pipeline and normalizer            | One dialect, one dry-run repair, focused regression coverage |
| M1 / WS-X cleanup      | Asset reachability                     | Exact 40-file deletion set and audit reconciliation          |
| M2 / WS-G gold set     | Representative equipment SVGs          | Eight-file calibration gate before the full sweep            |
| M3 / WS-A vessels      | Variable-volume material SVGs          | Material roles, clips, anchors, and volume renders           |
| M3 / WS-B families     | Binary/multi-state and instrument SVGs | Family consistency and meaningful state distinction          |
| M3 / WS-C tools        | Static tools and consumables           | Generic recognition at thumbnail and source scale            |
| M3 / WS-D evidence     | Observation and evidence SVGs          | Language-neutral artwork and application-owned prose         |
| M4 / WS-R review       | Full integrated SVG diff               | Independent source, semantic-interface, and visual review    |
| M5 / WS-V validation   | Repository and browser delivery path   | Single-writer final tree and exhaustive validation           |
| M5 / WS-H handoff      | Review artifacts                       | Self-contained labeled SVG contact sheet and preview         |

## Milestone plan

| M   | Title                 | Summary                                                             | Goal                                                               |
| --- | --------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| M1  | Establish boundaries  | Lock scope, repair tooling, and remove approved unreachable assets. | Create a stable source tree and acceptance contract.               |
| M2  | Calibrate the dialect | Edit and independently review a representative gold set.            | Prove the style target before broad editing.                       |
| M3  | Apply the sweep       | Edit the remaining retained SVGs in independent families.           | Bring all in-scope equipment into the same generic visual grammar. |
| M4  | Integrate and review  | Reconcile provenance and conduct source and visual audits.          | Detect cross-family regressions and semantic-interface damage.     |
| M5  | Validate and hand off | Run final gates and build the labeled SVG contact sheet.            | Deliver a reproducible final tree for human visual acceptance.     |

### Milestone M1: Establish boundaries

- Depends on: none -- this milestone establishes shared prerequisites.
- Deliverables: acceptance dialect, exact ledger, protected hashes, dry-run fix, focused regression coverage, approved cleanup deletion.
- Workstreams: WS-P and WS-X after the ledger is locked.
- Entry criteria: repository rules and the real SVG delivery path are identified.
- Exit criteria:
  - The ledger totals exactly 186 baseline SVGs: 139 edit, 40 delete, and seven protected.
  - The seven protected hashes match the ledger.
  - The asset audit reports no new authored references to the 40 deletion candidates.
  - Shadow dry-run reports numeric findings without mutating source and its focused behavior test passes.
- Parallel-plan ready: yes -- max parallel doers: 2 after the ledger is locked; tooling and reachability touch separate files.
- Status: Complete.

### Milestone M2: Calibrate the dialect

- Depends on: WP-P1 and WP-X1 -- style and cleanup boundaries must be stable.
- Deliverables: before/after evidence for the water-bath family, centrifuge family, P10 micropipette, tube rack, Falcon tube, and running-gel evidence SVG.
- Workstreams: WS-G source editing and independent visual/source review.
- Entry criteria: M1 passes.
- Exit criteria:
  - Detached floor shadows are absent while local form/material shading remains restrained.
  - Every object is generic and recognizable at thumbnail size.
  - Family states remain visibly distinct.
  - Independent source and visual re-review pass.
- Parallel-plan ready: yes -- max parallel doers: 2; implementation and independent review remain separate roles.
- Status: Complete.

### Milestone M3: Apply the sweep

- Depends on: WP-G1 -- the gold-set style gate defines the shared target.
- Deliverables: edited retained SVGs plus matched small/source-scale render evidence.
- Workstreams: WS-A, WS-B, WS-C, and WS-D.
- Entry criteria: M2 passes without an unresolved dialect decision.
- Exit criteria:
  - All 139 edit rows in the ledger have an owning completed package.
  - Asset families share stable canvases and coherent value/line hierarchy.
  - Material SVG roles and semantic anchors remain valid.
  - Learner-facing prose is absent from equipment artwork except the protected result composites.
- Parallel-plan ready: yes -- max parallel doers: 17 bounded file-disjoint packages were used.
- Status: Complete.

### Milestone M4: Integrate and review

- Depends on: WP-A1 through WP-D4 -- the full retained set must be present.
- Deliverables: reconciled provenance/current-work docs, repaired audit links, four stream-level visual reviews, four stream-level source reviews, and re-reviews of every finding.
- Workstreams: WS-R source review, WS-RV visual review, and WS-DOC documentation reconciliation.
- Entry criteria: all editing packages report local validation.
- Exit criteria:
  - No material anchor, overlay root, click hook, or family contract is unintentionally lost.
  - No geometry-affecting stylesheet rejected by the normalizer remains.
  - No unintended visible English prose remains in the 139 edited SVGs.
  - Every blocking review finding is fixed and independently re-reviewed.
- Parallel-plan ready: yes -- max parallel doers: 9 across file-disjoint reviews and bounded fixes.
- Status: Complete.

### Milestone M5: Validate and hand off

- Depends on: WP-R1, WP-R2, and WP-DOC1 -- final validation must run against one integrated tree.
- Deliverables: exhaustive validation record, protected-hash proof, production
  browser result, final labeled contact sheet SVG, ignored PNG render proof,
  GitHub review page, and human-review handoff.
- Workstreams: WS-V must run serially as the single validation writer; WS-H begins only after WS-V fixes are complete.
- Entry criteria: M4 passes and no editing agent remains active.
- Exit criteria:
  - All commands in the test strategy pass or have an explicit evidence-scoped explanation.
  - The final asset audit reports 131 objects, 146 SVGs, no orphans, and no findings.
  - The protected seven hashes match the baseline.
  - The contact sheet contains and labels all 146 retained SVGs, visibly marks the seven protected result composites, parses as XML, and renders to PNG.
  - An independent visual evaluator finds no gross contact-sheet omissions, clipping, or mislabeled tiles.
  - The human reviewer receives clickable paths to the GitHub review page and
    full-resolution SVG without a claim of human approval.
- Parallel-plan ready: no -- final validators and artifact generation intentionally consume the same integrated tree in dependency order.
- Status: Complete through automated validation and artifact generation; human visual acceptance remains pending.

## Workstream breakdown

### Workstream WS-P: Shared prerequisite

- Goal: define the visual dialect and make shadow diagnostics safe and repeatable.
- Owner: expert coder, with independent reviewer.
- Work packages: WP-P1, WP-P2.
- Interfaces:
  - Needs: repository rules, baseline inventory, normalizer behavior.
  - Provides: canonical acceptance language and working diagnostics.
- Review boundary, when modifying the repository: `docs/specs/SVG_PIPELINE.md`, `tools/normalize_svg_v3.py`, and its focused test module.

### Workstream WS-X: Reachability cleanup

- Goal: remove exactly the approved unreachable assets without broadening deletion scope.
- Owner: maintainer, with independent reviewer.
- Work packages: WP-X1, WP-X2.
- Interfaces:
  - Needs: exact ledger and fresh asset audit.
  - Provides: clean retained source inventory.
- Review boundary, when modifying the repository: the 40 ledger-marked SVGs, superseded helper, provenance audit, its focused parser test, and direct documentation references.

### Workstream WS-G: Gold-set calibration

- Goal: prove the de-shadowed Servier dialect on representative equipment categories.
- Owner: SVG expert coder, with source and image evaluators.
- Work packages: WP-G1, WP-G2.
- Interfaces:
  - Needs: WP-P1, WP-P2, WP-X1.
  - Provides: approved visual target and repair lessons for the broad sweep.
- Review boundary, when modifying the repository: eight named gold-set SVGs.

### Workstream WS-A: Variable-volume vessels

- Goal: make five material-aware vessels consistent while preserving fill geometry.
- Owner: SVG expert coder.
- Work packages: WP-A1.
- Interfaces:
  - Needs: WP-G2.
  - Provides: validated material-aware vessel family.
- Review boundary, when modifying the repository: `assets/equipment/variable_volume/`.

### Workstream WS-B: State families and instruments

- Goal: align binary/multi-state families and retained instruments while preserving meaningful state differences.
- Owner: SVG expert coders in file-disjoint packages.
- Work packages: WP-B1 through WP-B5.
- Interfaces:
  - Needs: WP-G2.
  - Provides: stable state families and instruments.
- Review boundary, when modifying the repository: package-owned subsets of `binary_state/`, `multi_state/`, and selected `static/` instruments.

### Workstream WS-C: Tools and consumables

- Goal: align retained static physical tools with generic recognizable silhouettes.
- Owner: SVG expert coders in file-disjoint packages.
- Work packages: WP-C1 through WP-C4.
- Interfaces:
  - Needs: WP-G2.
  - Provides: consistent tools and consumables.
- Review boundary, when modifying the repository: package-owned static SVGs only.

### Workstream WS-D: Evidence artwork

- Goal: align language-neutral evidence and observation artwork while keeping learner prose application-owned.
- Owner: SVG expert coders in file-disjoint packages.
- Work packages: WP-D1 through WP-D4.
- Interfaces:
  - Needs: WP-G2.
  - Provides: consistent evidence artwork with no new result-interface migration.
- Review boundary, when modifying the repository: package-owned static evidence SVGs only.

### Workstream WS-R: Integrated review and documentation

- Goal: independently examine source contracts, rendered families, and documentation after integration.
- Owner: reviewer, image evaluator, and planner.
- Work packages: WP-R1, WP-R2, WP-DOC1.
- Interfaces:
  - Needs: all editing work packages.
  - Provides: accepted integrated tree and documented remaining scope.
- Review boundary, when modifying the repository: read-only review over the full diff; documentation owner edits docs only.

### Workstream WS-V: Final validation

- Goal: prove the integrated tree through focused, repository-wide, build, and browser gates.
- Owner: integrator/tester operating serially.
- Work packages: WP-V1 through WP-V4.
- Interfaces:
  - Needs: all fixes from WS-R.
  - Provides: final validated source tree and exact evidence record.
- Review boundary, when modifying the repository: validation is read-only except for ignored/generated evidence artifacts.

### Workstream WS-H: Human-review handoff

- Goal: produce one readable labeled contact sheet for final human judgment.
- Owner: integrator with image evaluator.
- Work packages: WP-H1, WP-H2.
- Interfaces:
  - Needs: WP-V4.
  - Provides: self-contained SVG contact sheet, ignored raster preview, and
    repository-linked reviewer instructions.
- Review boundary, when modifying the repository: construction artifacts stay
  under `test-results/svg-consistency/`; the verified review snapshot and guide
  live under `docs/`.

## Work packages

### Work package WP-P1: Lock the visual contract and inventory

- Owner: planner/SVG expert.
- Touch points: `docs/specs/SVG_PIPELINE.md`, sweep ledger, `docs/TODO.md`, `docs/ROADMAP.md`.
- Depends on: none.
- Acceptance criteria: Servier-only authority, detached-shadow boundary, local shading rule, generic-recognition target, exact 139/40/7 disposition, and seven protected hashes are explicit.
- Evidence or review, when useful: ledger count and protected-hash command.
- Obvious follow-ons: publish package boundaries from the ledger.
- Status: Complete.

### Work package WP-P2: Repair shadow dry-run

- Owner: coder and tester.
- Touch points: `tools/normalize_svg_v3.py`, `tests/test_normalize_svg_v3.py`.
- Depends on: WP-P1.
- Acceptance criteria: shadow diagnostics format numeric geometry safely, preserve source bytes, and pass one focused behavior test.
- Evidence or review, when useful: `source source_me.sh && python3 -m pytest tests/test_normalize_svg_v3.py`.
- Obvious follow-ons: use the diagnostic only as evidence, not as a blind bulk rewrite.
- Status: Complete.

### Work package WP-X1: Delete approved unreachable SVGs

- Owner: maintainer.
- Touch points: exact 40 delete rows in the sweep ledger.
- Depends on: WP-P1.
- Acceptance criteria: fresh audit confirms each row is unreachable; exactly those 40 files are removed; no additional asset is deleted.
- Evidence or review, when useful: strict asset audit and `git diff --name-status` reconciliation.
- Obvious follow-ons: repair direct documentation references.
- Status: Complete.

### Work package WP-X2: Remove superseded census helper

- Owner: maintainer.
- Touch points: `tools/svg_liquid_census.py` and any direct callers.
- Depends on: WP-X1.
- Acceptance criteria: no live caller exists; the obsolete helper is removed rather than archived into another tool directory.
- Evidence or review, when useful: repository reference search and independent cleanup review.
- Obvious follow-ons: keep canonical inventory in the live audit pipeline.
- Status: Complete.

### Work package WP-G1: Edit the gold set

- Owner: SVG expert coder.
- Touch points: water-bath pair, centrifuge pair, `p10_micropipette_empty.svg`, `tube_rack.svg`, `falcon_15ml.svg`, and `gel_migration_running.svg`.
- Depends on: WP-P2 and WP-X1.
- Acceptance criteria: recognizable generic silhouettes, restrained local shading, no detached floor shadows, preserved hooks and material semantics.
- Evidence or review, when useful: matched 160 px and 640 px source renders plus compiled material render where required.
- Obvious follow-ons: route findings into the gold-set re-review.
- Status: Complete.

### Work package WP-G2: Review and approve the gold set

- Owner: independent reviewer and image evaluator.
- Touch points: WP-G1 diff and render evidence.
- Depends on: WP-G1.
- Acceptance criteria: source and visual reviews pass; recognition defects are repaired and re-reviewed.
- Evidence or review, when useful: reviewer reports and re-rendered evidence.
- Obvious follow-ons: release M3 packages only after approval.
- Status: Complete.

### Work packages WP-A1 through WP-D4: Edit retained asset families

- Owner: 17 file-disjoint SVG expert coders.
- Touch points: the 131 non-gold edit rows, divided according to the ledger and workstream boundaries.
- Depends on: WP-G2.
- Acceptance criteria:
  - Every package owns a disjoint SVG list and reports changed files.
  - Every SVG parses, renders at 160 px and 640 px, and preserves relevant references and hooks.
  - Family variants remain compositionally stable and visibly distinct.
  - Generic recognition uses only minimum characteristic cues.
- Evidence or review, when useful: package reports and matched before/after renders.
- Obvious follow-ons: submit each stream to independent source and visual review.
- Status: Complete.

### Work package WP-R1: Review integrated SVG source contracts

- Owner: independent reviewer.
- Touch points: full integrated SVG diff.
- Depends on: WP-A1 through WP-D4.
- Acceptance criteria: anchors, overlay roots, material declarations, ID references, normalization constraints, language boundaries, and family contracts pass.
- Evidence or review, when useful: four stream source reviews and re-reviews of every finding.
- Obvious follow-ons: repair and re-review all blocking findings before validation.
- Status: Complete.

### Work package WP-R2: Review integrated rendered families

- Owner: independent image evaluator.
- Touch points: source-scale and thumbnail evidence across all four streams.
- Depends on: WP-A1 through WP-D4.
- Acceptance criteria: all streams pass recognizability, consistency, state distinction, clipping, and shading review.
- Evidence or review, when useful: four stream visual reports and any re-review evidence.
- Obvious follow-ons: record the approved final visual tree for validation.
- Status: Complete.

### Work package WP-DOC1: Reconcile provenance and scope documentation

- Owner: planner.
- Touch points: equipment sources, third-party assets, current gaps, retired-art records, SVG interface audit, changelog, TODO, and ROADMAP.
- Depends on: WP-X1, WP-R1, and WP-R2.
- Acceptance criteria: deleted assets are no longer linked as live files, Servier attribution remains accurate, result migration remains out of scope, and current-work docs distinguish completed art work from future UI migration.
- Evidence or review, when useful: Markdown link and ASCII checks.
- Obvious follow-ons: update closeout facts after final validation.
- Status: Complete.

### Work package WP-V1: Run focused SVG and documentation gates

- Owner: tester.
- Touch points: final integrated tree.
- Depends on: WP-R1, WP-R2, and WP-DOC1.
- Acceptance criteria: durable SVG, unit, Markdown-link, and ASCII gates pass; implementation-only hash and diff evidence is recorded separately.
- Evidence or review, when useful: exact command results recorded below.
- Obvious follow-ons: proceed to repository-wide gates.
- Status: Complete.

### Work package WP-V2: Run repository-wide static and unit gates

- Owner: tester.
- Touch points: final integrated tree.
- Depends on: WP-V1.
- Acceptance criteria: `./check_codebase.sh` passes all named gates.
- Evidence or review, when useful: exact check and test counts recorded in closeout.
- Obvious follow-ons: build the production artifact.
- Status: Complete.

### Work package WP-V3: Build and exercise the production delivery path

- Owner: tester and Playwright operator.
- Touch points: production build and browser walkthrough entry point.
- Depends on: WP-V2.
- Acceptance criteria: `./build_github_pages.sh`, material contact rendering, and the repository's production-shaped Playwright/walker entry point pass.
- Evidence or review, when useful: build logs, browser result, and rendered material contact sheet.
- Obvious follow-ons: run the exhaustive suite after browser stability is proven.
- Status: Historical pass on the SVG-sweep tree. The production material
  contact sheet and `./run_playwright_tests.sh` passed (115/115); combined-tree
  revalidation is pending after the later vendored refresh.

### Work package WP-V4: Run the exhaustive final suite

- Owner: integrator/tester.
- Touch points: final integrated tree.
- Depends on: WP-V3.
- Acceptance criteria: `./super_all_tests.sh` completes with all applicable gates passing; any environmental exclusion is explicit and does not conceal a product failure.
- Evidence or review, when useful: exhaustive-suite summary and final status/diff reconciliation.
- Obvious follow-ons: freeze SVG edits and generate the final contact sheet.
- Status: Historical pass on the SVG-sweep tree. `./super_all_tests.sh` passed
  (20/20); combined-tree revalidation is blocked by newly vendored permanent
  gates that fail or violate the fast-pytest policy.

### Work package WP-H1: Generate the labeled SVG contact sheet

- Owner: integrator.
- Touch points: all 146 retained SVGs, `test-results/svg-consistency/`, and the
  published documentation snapshot.
- Depends on: WP-V4.
- Acceptance criteria:
  - The artifact is standalone SVG with no external asset dependencies.
  - Every tile embeds one current SVG and labels its source folder and filename.
  - Category styling distinguishes binary-state, multi-state, static, and variable-volume assets.
  - The seven protected result composites carry a visible `DEFERRED / BYTE-PRESERVED` marker.
  - The header states the final asset count and the generic de-shadowed Servier review target.
- Evidence or review, when useful: XML parse, reference check, and PNG render.
- Obvious follow-ons: inspect the raster preview for omissions and gross layout defects.
- Status: Complete. The verified final labeled all-SVG contact sheet is
  published at
  [final_equipment_contact_sheet.svg](../../figures/final_equipment_contact_sheet.svg).
  Its temporary generator was removed after the source tree and artifact were
  verified; the oversized PNG remains ignored construction evidence.

### Work package WP-H2: Review and hand off the contact sheet

- Owner: independent image evaluator, followed by the human reviewer.
- Touch points: [EQUIPMENT_SVG_CONTACT_SHEET.md](../../EQUIPMENT_SVG_CONTACT_SHEET.md),
  the final contact-sheet SVG, and the ignored PNG preview.
- Depends on: WP-H1.
- Acceptance criteria: evaluator confirms label legibility, complete tiling, no gross clipping, and clear protected markers; final handoff provides clickable artifact paths and leaves human visual approval explicitly pending.
- Evidence or review, when useful: image-evaluator report and human review notes.
- Obvious follow-ons: route any human-requested art changes into new bounded SVG packages, then repeat M5.
- Status: Pending human visual acceptance.

## Acceptance criteria and gates

- Per-patch gate: owned files only, valid XML, resolved local references, preserved semantic hooks, and a compact validation report. Source and 160/640 px renders are implementation evidence.
- Integration gate: the durable asset audit reports no findings. Exact disposition and inventory counts are one-time closeout evidence in the ledger.
- Independent review gate: every asset stream passes both source and visual review; every blocking finding is fixed by a separate owner and independently re-reviewed.
- Human gate: the final labeled contact sheet is the review surface; automated and agent review do not substitute for the user's visual acceptance.

## Verification classification

### Permanent regression coverage

- `tests/test_normalize_svg_v3.py` retains one focused dry-run regression. It
  exercises the reporter with inline SVG input under `tmp_path`, checks numeric
  output and source-byte preservation, runs offline, and finishes in the fast
  pytest lane.
- `tests/test_asset_audit_provenance.py` retains one pure parser regression with
  inline Markdown rows. It protects the source-ownership boundary that excludes
  DBCLS and repository-authored rows from the Servier target set.
- Existing Node and Playwright contract tests were updated only where the strict
  scene-generation design retired placeholder state. They continue to test
  renderer behavior and the built visible application in their existing tiers.
- Permanent coverage adds no fixture files or fixture directories. Fast tests
  use no network, subprocess round trips, sleeps, or external test data.

### One-time implementation evidence

- The 186-row census, exact 139/40/seven disposition, protected-file hashes,
  reachability audit, and exact final asset/object counts prove this migration.
  They remain in the active-plan ledger rather than becoming count or hash tests.
- Matched 160/640 px renders, per-wave source review, perceptual comparison, and
  contact-sheet construction support visual judgment. The intermediate renders
  remain ignored evidence under `test-results/` rather than entering an
  automated suite; the verified final SVG is an intentional documentation
  snapshot, not a permanent test fixture.
- Exact pass counts from `check_codebase.sh`, Playwright, and the exhaustive
  runner record the final tree that was exercised. The existing front-door gates
  remain durable; their August 24 counts are historical closeout facts.
- Contact-sheet inventory comparison, XML parsing, and PNG rasterization are
  final artifact checks. The temporary generator was removed after it produced
  the reviewed snapshot and ignored PNG.

## Test and verification strategy

Run repository-local Python as `source source_me.sh && python3`.

Run the durable validators and existing test tiers:

```sh
source source_me.sh && python3 validation/validate.py --only svg --strict
source source_me.sh && python3 -m pytest tests/test_normalize_svg_v3.py tests/test_asset_audit_provenance.py
source source_me.sh && python3 -m pytest tests/test_markdown_links.py tests/test_ascii_compliance.py
./check_codebase.sh
./build_github_pages.sh
./tools/render_liquid_volume_contact_sheet.sh
./run_playwright_tests.sh
./super_all_tests.sh
```

Record one-time migration and final-artifact evidence after the source tree is
frozen:

```sh
shasum -a 256 assets/equipment/static/{cell_viability_results_display,electrophoresis_endpoint_display,gel_image_results_display,hemocytometer_observation_display,mtt_reader_results_display,plate_reader_absorbance_result_panel,plate_reader_normalized_viability_panel}.svg
git diff --check
xmllint --noout docs/figures/final_equipment_contact_sheet.svg
rsvg-convert -w 2400 \
  docs/figures/final_equipment_contact_sheet.svg \
  -o test-results/svg-consistency/final_equipment_contact_sheet.png
```

Failure semantics:

- During this implementation, any protected hash change blocks the sweep and requires restoring the exact baseline bytes.
- Any strict SVG warning, material render failure, broken Markdown link, or source-interface regression blocks integration.
- A browser launch failure is rerun in the repository-supported browser environment; a reproducible application failure blocks completion.
- A contact-sheet defect blocks handoff but does not authorize editing a protected result composite.

## Risk register

| Risk                                      | Impact | Trigger                                                                | Owner              | Mitigation                                                                                                       |
| ----------------------------------------- | ------ | ---------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Broad shadow removal flattens form        | High   | Curved/glass/liquid object loses readable depth                        | SVG expert         | Remove detached floor shadows narrowly and preserve restrained local value roles.                                |
| Generic becomes visually ambiguous        | High   | Human or evaluator reads the wrong object class                        | SVG expert         | Add only the minimum characteristic silhouette or component cue, then re-render at thumbnail size.               |
| Family variants drift                     | High   | Related states move, resize, or become indistinguishable               | Work-package owner | Review variants together on stable viewBoxes and require visible state distinction.                              |
| Semantic anchors are lost                 | High   | Compiler, material injection, or interaction validation fails          | Source reviewer    | Compare IDs/hooks before and after and re-run strict validation.                                                 |
| Result screens enter the art sweep        | High   | Any protected hash changes                                             | Integrator         | Check seven hashes after every integrated wave and again at closeout.                                            |
| Parallel edits collide                    | Medium | Two packages touch one file or shared generated state                  | Manager            | Use file-disjoint packages; serialize shared docs and final generation.                                          |
| Raw source render misrepresents materials | Medium | Variable-volume object appears empty or malformed outside its consumer | Image evaluator    | Inspect material-aware assets through the compiled production contact renderer.                                  |
| Contact sheet is incomplete or unreadable | Medium | Tile count differs from 146 or labels clip                             | Integrator         | Generate from the final filesystem inventory, embed all sources, validate XML, rasterize, and visually evaluate. |
| Validation mutates tracked derived files  | Medium | Unexpected generated or report diffs appear                            | Integrator         | Run final gates as a single writer and reconcile `git status` after each generator.                              |

## Rollout and release checklist

- [x] Read repository rules and SVG pipeline guidance.
- [x] Lock the 186-row disposition ledger and protected hashes.
- [x] Repair shadow dry-run and keep focused regression coverage that meets the permanent-test checklist.
- [x] Remove exactly 40 approved unreachable SVGs.
- [x] Complete and approve the eight-file gold set.
- [x] Complete 17 file-disjoint packages for the remaining 131 retained SVGs.
- [x] Pass all stream-level source and visual reviews after repairs.
- [x] Reconcile provenance, deleted links, changelog, TODO, and ROADMAP.
- [x] Pass strict SVG, focused pytest, documentation, repository static/unit, and production build gates on the SVG-sweep tree.
- [x] Pass the final material renderer, production-shaped browser path, and exhaustive suite on the SVG-sweep tree.
- [ ] Revalidate the combined tree after resolving the later vendored-test blockers.
- [x] Confirm protected hashes, exact disposition, and clean generated-output status one final time.
- [x] Generate, parse, render, and independently inspect the final labeled SVG contact sheet.
- [x] Publish and hand off the contact sheet for human visual acceptance.

## Documentation close-out requirements

- Active plan / progress tracker updates: update this file and the sweep ledger with exact final command outcomes and artifact paths.
- `docs/CHANGELOG.md` entry: retain the 2026-08-24 SVG consistency entry and add only validation facts actually observed on the final tree.
- TODO/ROADMAP: keep the seven result-interface migrations visible as future work; do not imply that the art sweep completed them.
- Archive / closure notes: retain this plan under `docs/active_plans/` until human review and any resulting bounded repairs are complete.

## Closeout ledger

- Final disposition: 139 retained SVGs modified, 40 retired SVGs deleted, and
  seven result composites byte-preserved.
- Final audit: 131 objects, 146 SVGs, and zero findings.
- The material baseline was intentionally refreshed after visual review; the
  production material contact sheet passed.
- Historical SVG-sweep delivery gates: `./run_playwright_tests.sh` passed
  115/115 and `./super_all_tests.sh` passed 20/20. These counts predate the
  later vendored refresh and do not establish combined-tree acceptance.
- The repository-linked labeled all-SVG contact sheet remains the final review
  artifact. Human visual acceptance is still pending and is not implied by
  these results.

## Patch plan and reporting format

- Patch 1: visual contract, ledger, shadow dry-run repair, and focused tests.
- Patch 2: approved unreachable-asset cleanup and provenance/link reconciliation.
- Patch 3: gold-set calibration and independent approval.
- Patch 4: variable-volume vessels.
- Patch 5: binary/multi-state families and instruments.
- Patch 6: static tools, consumables, and evidence artwork.
- Patch 7: integrated source/visual fixes and documentation reconciliation.
- Patch 8: final validation evidence and labeled contact-sheet handoff.

Each implementation package reports assumptions, decisions, concrete next
steps, changed files, validation performed, and blocking issues. Independent
review reports remain separate from implementation reports.

## Resolved decisions

- Servier Medical Art is the only Bioicons style authority for this sweep.
- The target is de-shadowed Servier, not flat artwork.
- Detached floor shadows are removed; restrained local form/glass/liquid shading remains.
- Generic, unbranded, model-independent equipment is correct and desirable.
- Only wrong-class ambiguity justifies adding recognition detail.
- The seven result composites remain byte-preserved and their application-interface migration stays in TODO/ROADMAP.
- The final human review surface is a labeled, self-contained SVG contact sheet
  generated by a temporary helper after the source tree became stable, then
  committed under `docs/figures/` for GitHub access.

## Open questions and decisions needed

- Manager/subagent decision procedure:
  - Decision owner or dedicated class: integrator for gate failures; image evaluator for contact-sheet presentation findings; user for final visual acceptance.
  - Evidence and decision rule: repair only reproducible source, delivery, or recognition defects; keep environmental failures and future result-interface work explicitly separate.
- Non-blocking follow-up: after human contact-sheet review, any requested refinements become new file-bounded work packages and repeat the final validation milestone.
