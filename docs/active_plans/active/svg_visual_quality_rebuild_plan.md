# Plan: SVG equipment visual-quality rebuild

> Superseded on 2026-08-26 by
> [svg_visual_quality_rebuild_plan-v2.md](svg_visual_quality_rebuild_plan-v2.md).
> This file retains the rejected D01-D05 rollout as historical context;
> current replacement-wave status and acceptance live in v2.

## Context

The completed [svg_consistency_implementation_plan.md](svg_consistency_implementation_plan.md)
established one tracked SVG source tree, strict resolution, protected result interfaces, and structural
validation. Human review still rejected the visual result: the equipment reads as flat UI icons rather
than coherent three-dimensional laboratory objects in the Bioicons Servier visual language.

The failure is not runtime or schema instability. It is a failed illustration workflow: earlier work
treated valid SVG, palette consistency, and a final contact sheet as enough evidence of object quality.
This plan retains working foundations while replacing the bulk-art workflow with evidence-first
exemplars, a selected construction kit, family-owned rebuilds, and review through real consumers.

## Objectives

- Rebuild retained physical equipment as recognizable, coherent three-dimensional laboratory objects.
- Prefer Servier construction where applicable and use real-object references for identity.
- Select one visual direction from concrete candidates without blocking on unavailable preference feedback.
- Publish a measured construction kit before family batches multiply visual decisions.
- Validate the final frozen tree in actual render modes, workspaces, and repository gates.

## Historical implementation closure

Implementation is complete through M12 on the current 135-SVG equipment tree.
The selected direction is D04 occlusion-strong with D01 restraint. The seven
protected result interfaces remain byte-preserved and outside ordinary-art
approval. The completed
[frozen-tree validation record](../reports/svg_m12_validation_record.md) covers
the exact-tree reconciliation, compact label-safe integration, visual closure,
and repository gates. The companion M0-M12 and E1-E10 requirement trace remains
untracked until the user chooses to add it.

**Visual outcome reopened on 2026-08-26:** the user rejected the four-archetype
candidate treatment as cubist rather than realistic laboratory equipment. The
technical implementation and validation remain complete, but D01-D05 are now
historical experiments rather than an approved direction pool, and the primary
visual acceptance criterion is open. The current production-art review workflow
is documented in [USAGE.md](../../USAGE.md#equipment-svg-visual-review).

Keep this superseded history beside v2 while human visual acceptance remains
open; archive both plans after the current result is accepted.

## Design philosophy

Use **fix the design, not the symptom** and **long-term over short-term**: pre-production status permits
clean replacement of the failed art process rather than compatibility layers around it. Use **the
scientific method** for the one uncertain question, projection and depth treatment: compare
developed-massing candidates at real size, ask an independent evaluator to cite what they see, then
select and freeze the demonstrated direction. Use **atomic task decomposition** for family batches.

- Evidence strategy for uncertain methods: M5 compares depth treatments on four exemplar archetypes. If
  every candidate still reads as flat, revise the massing method and repeat M5; do not encode a kit until
  one candidate demonstrably reads as a coherent laboratory bench.

## Scope

- Audit the normalizer behavior that constrains SVG depth treatment.
- Inventory retained assets, Servier counterparts, flatness indicators, sizes, roles, and families.
- Build boards, candidate directions, polished exemplars, and a review-only construction kit.
- Rebuild consumable, labware, tool, instrument, electrophoresis, safety, overlay, and evidence families.
- Review finished assets in consumer workspaces and preserve existing structural invariants.
- Update durable SVG guidance only after exemplar evidence supports a rule.

## Non-goals

- Migrate or redraw the seven protected result composites.
- Change protocol pedagogy, scene layout, material vocabulary, or runtime state behavior.
- Recreate branded manufacturer products or copy manufacturer artwork.
- Add learner-facing schema fields solely to drive review tooling.
- Add pixel, hash, exact-count, or appearance-snapshot pytest contracts for evolving art.
- Preserve failed art directions, legacy visual rules, or compatibility pathways that conflict with the
  selected foundational direction.

## Current state summary

Status date: 2026-08-25.

| Area            | Observation                                                                            | Consequence                                             |
| --------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Contracts       | SVG resolution, normalization, manifests, materials, and protected interfaces pass.    | Preserve them as validation foundations.                |
| Visual outcome  | Human review rejects a structurally complete but flat icon-like equipment tree.        | Redesign illustration workflow, not presentation alone. |
| Local evidence  | Bioicons Servier contains direct or adjacent laboratory counterparts.                  | Check it before every redraw.                           |
| Object identity | Some forms lack reference-backed construction.                                         | Attach real-object boards to finished review.           |
| Review          | Equal-size standalone tiles mix objects, overlays, evidence, and protected interfaces. | Use role-specific and workspace-specific evidence.      |
| Normalization   | Floor-shadow detection can match real low-value base geometry.                         | Audit and correct that signal before redraws.           |

The primary acceptance criterion is:

> The rebuilt equipment looks like coherent three-dimensional laboratory equipment in the established
> Servier visual language. Technical checks support that result.

Servier establishes how the house style draws an object. Manufacturer pages and manuals establish what
the object is. Each source answers its own question.

## Architecture boundaries and ownership

- `assets/equipment/**` owns authored physical and evidence SVGs.
- `content/objects/**` owns object identity, forms, states, and material binding.
- [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) owns durable construction and normalization guidance.
- `pipeline/` owns build-invoked and output-emitting files; `tools/` owns review-only helpers.
- `docs/figures/equipment_kit/` owns intentional review-only kit artifacts and stays outside `assets/`.
- `rendered-reports/equipment_svg_reviews/` owns ignored candidate and batch evidence.
- The manager owns evidence-backed default selection. The user owns preferences whenever provided.
- An `image_evaluator` owns independent visual findings; an `integrator` owns cross-family reconciliation.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / workstream | Component                                   | Review boundary                                      |
| ---------------------- | ------------------------------------------- | ---------------------------------------------------- |
| M0 / WS-N              | Normalizer floor-shadow audit               | Report, signal behavior, and supported-feature brief |
| M1-M3 / WS-I           | Inventory, provenance, and size ledger      | One reconciled record per retained asset             |
| M4-M8 / WS-X           | Boards, candidates, exemplars, and kit      | Four archetypes and frozen selection record          |
| M9 / WS-C              | Consumables and labware                     | Named physical family and direct bindings            |
| M10 / WS-H, WS-B       | Handheld tools and benchtop instruments     | Named family and direct bindings                     |
| M11 / WS-E, WS-S, WS-O | Electrophoresis, safety, overlays, evidence | One family or intended composite at a time           |
| M12 / WS-R, WS-V       | Review surfaces, integration, validation    | One frozen source tree and report                    |

## Milestone plan

The plan contains thirteen labeled milestones, M0 through M12. The earlier shorthand "twelve" describes
twelve post-unblock delivery stages; M0 is the prerequisite unblocking stage and remains named so its
design dependency cannot disappear.

| M   | Title                              | Summary                                                         | Goal                                                           |
| --- | ---------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------- |
| M0  | Unblock the normalizer             | Audit floor-shadow classification and record supported filters. | Remove a pipeline constraint that misclassifies real geometry. |
| M1  | Inventory and roles                | Reconcile role, family, and disposition for every retained SVG. | Separate object work from overlays and protected interfaces.   |
| M2  | Servier counterpart sweep          | Record direct, adjacent, or absent Servier evidence.            | Start redraws from strong house-style sources.                 |
| M3  | Flatness and size census           | Measure volume indicators and placement ranges.                 | Calibrate construction at actual use size.                     |
| M4  | Exemplar reference boards          | Establish identity and volume evidence for four archetypes.     | Give exemplars reviewable construction briefs.                 |
| M5  | Candidate directions and shortlist | Compare massing bench composites and rank about five.           | Prove a volumetric direction before polish.                    |
| M6  | Direction selection                | Record user preference or manager default.                      | Freeze one direction without waiting indefinitely.             |
| M7  | Exemplar polish                    | Finish and independently review four exemplars.                 | Demonstrate language on hard construction classes.             |
| M8  | Kit extraction                     | Publish measured constraints and principles.                    | Give every batch one construction authority.                   |
| M9  | Consumables and labware            | Rebuild WP-C families against the kit.                          | Establish shared vessel and labware geometry.                  |
| M10 | Tools and instruments              | Rebuild WP-H and WP-B families against the kit.                 | Apply volume to tools and manufactured equipment.              |
| M11 | Electrophoresis, safety, overlays  | Rebuild WP-E, WP-S, and WP-O families.                          | Complete specialized and composite-only art.                   |
| M12 | Integration and validation         | Review consumers and run final gates.                           | Close with visual and structural evidence.                     |

### Milestone M0: Unblock the normalizer

- Depends on: none.
- Deliverables: report-only floor-shadow audit, corrected signal, and supported-filter note.
- Workstreams: WS-N.
- Entry criteria: current normalizer and asset tree are available.
- Exit criteria: reviewer verifies every candidate as shadow or real geometry, corrected signal reproduces
  verdicts, and manager records the sanitizer feature boundary.
- Parallel-plan ready: yes -- max parallel doers: 2; coder owns signal and reviewer owns verdicts.

### Milestone M1: Inventory and roles

- Depends on: none.
- Deliverables: role, family, disposition, consumer, and protected-interface ledger.
- Workstreams: WS-I.
- Entry criteria: retained SVG inventory and consumers are readable.
- Exit criteria: integrator reconciles the provisional M1-M3 records into one role, family, disposition,
  provenance status, and size record per SVG before M4; overlays name context and protected interfaces
  remain separated.
- Parallel-plan ready: yes -- max parallel doers: 2; inventory and consumer tracing are file-disjoint.

### Milestone M2: Servier counterpart sweep

- Depends on: none -- use the current asset path and object name as provisional search anchors.
- Deliverables: provisional provenance rows and attribution actions.
- Workstreams: WS-I.
- Entry criteria: asset tree and local Servier corpus are readable.
- Exit criteria: integrator records provisional `servier_source`, `servier_adjacent`, or
  `no_servier_source` evidence with a path, structural guidance, or bounded search terms for every
  object, then reconciles its subject keys with M1 before M4.
- Parallel-plan ready: yes -- max parallel doers: 3; source searching is disjoint by family.

### Milestone M3: Flatness and size census

- Depends on: none -- use the current asset path as the provisional identity key.
- Deliverables: provisional plane, ellipse, rotation, and rendered-size census.
- Workstreams: WS-I.
- Entry criteria: layout pipeline and scene scale report run.
- Exit criteria: reviewer records volume indicators and minimum, median, maximum ranges or a nominal size
  for every asset, then reconciles its asset keys with M1 and M2 before M4; the four-exemplar slice is
  ready before M4 ends.
- Parallel-plan ready: yes -- max parallel doers: 3; census reads files and does not modify SVGs.

### Milestone M4: Exemplar reference boards

- Depends on: WP-N1 plus reconciled WP-I1, WP-I2, and WP-I3 -- the opening evidence runs concurrently,
  then their file-disjoint provisional records select sources together.
- Deliverables: boards and briefs for T75 flask, centrifuge, micropipette, and material `falcon_15ml` or
  `microtube` vessel.
- Workstreams: WS-X.
- Entry criteria: subjects cover difficult construction classes in the M1 ledger.
- Exit criteria: each board explains recognizability and volume, records bounded manufacturer/manual search,
  and names projection and characteristic parts.
- Parallel-plan ready: yes -- max parallel doers: 4; one reviewer owns each archetype.

### Milestone M5: Candidate directions and shortlist

- Depends on: WP-X1.
- Deliverables: developed-massing candidates, real-size bench composites, evaluator ranking, fixtures.
- Workstreams: WS-X.
- Entry criteria: briefs and normalizer feature boundary exist.
- Exit criteria: `image_evaluator` identifies about five credible, distinct composites with cited objects
  that read as one bench; if none pass, manager records failed massing hypothesis and repeats M5 with a
  changed construction approach.
- Parallel-plan ready: yes -- max parallel doers: 4; one SVG expert coder owns each archetype.

### Milestone M6: Direction selection

- Depends on: WP-X2.
- Deliverables: selection record, vote artifact, or provisional manager decision.
- Workstreams: WS-X.
- Entry criteria: about five ranked real-size composites exist.
- Exit criteria: user preference selects when available; otherwise manager selects using Servier consistency,
  reference fidelity, real-size legibility, evaluator ranking, and recorded reasons.
- Parallel-plan ready: no -- one manager selects the shared direction after evidence is complete.

### Milestone M7: Exemplar polish

- Depends on: WP-X3.
- Deliverables: four finished exemplars and real-size, reference-back, material-range evidence.
- Workstreams: WS-X.
- Entry criteria: M6 direction is frozen.
- Exit criteria: fresh `image_evaluator` confirms recognition, reference-back fidelity, bench coherence, and
  material fill behavior; a concrete finding blocks the owning repair.
- Parallel-plan ready: yes -- max parallel doers: 4; subjects are file-disjoint.

### Milestone M8: Kit extraction

- Depends on: WP-X4, WP-X5.
- Deliverables: kit, measured stroke floors, swatches, elevation/light, fixtures, principles.
- Workstreams: WS-X.
- Entry criteria: polished exemplars and measurements exist.
- Exit criteria: planner publishes kit outside `assets/`; coder traces each technical constraint to a
  measurement and reviewer traces each visual principle to an exemplar.
- Parallel-plan ready: yes -- max parallel doers: 2; measurement and kit assembly have one handoff.

### Milestone M9: Consumables and labware

- Depends on: WP-X6.
- Deliverables: reviewed WP-C families and provenance/reference records.
- Workstreams: WS-C.
- Entry criteria: kit published and rows assigned.
- Exit criteria: fresh evaluator confirms each family against kit, board, real-size render; integrator
  confirms canonical physical forms are reused where only identity and contents differ.
- Parallel-plan ready: yes -- max parallel doers: 3; families are disjoint.

### Milestone M10: Tools and instruments

- Depends on: WP-X6.
- Deliverables: reviewed WP-H and WP-B families and provenance/reference records.
- Workstreams: WS-H and WS-B.
- Entry criteria: kit published and rows assigned.
- Exit criteria: fresh evaluator verifies recognizable class, reference-back fit, volume, and real-size
  legibility for each family.
- Parallel-plan ready: yes -- max parallel doers: 3; families are disjoint.

### Milestone M11: Electrophoresis, safety, and overlays

- Depends on: WP-X6.
- Deliverables: reviewed WP-E, WP-S, WP-O families including composite-only evidence.
- Workstreams: WS-E, WS-S, and WS-O.
- Entry criteria: kit published and intended overlay bases named.
- Exit criteria: fresh evaluator reviews physical families against kit and boards, overlays only on every
  named base or learner observation context.
- Parallel-plan ready: yes -- max parallel doers: 3; each owner receives disjoint family or composite.

### Milestone M12: Integration and validation

- Depends on: WP-C1, WP-H1, WP-B1, WP-E1, WP-S1, WP-O1.
- Deliverables: review surfaces, application captures, final gate record, closure artifact.
- Workstreams: WS-R and WS-V.
- Entry criteria: family owners stop editing and integrator freezes tree.
- Exit criteria: `playwright_operator` and `image_evaluator` review render modes, workspaces, rings,
  grayscale, contrast handoff; tester records all repository gates passing.
- Parallel-plan ready: yes -- max parallel doers: 3; work shares only frozen source tree.

## Workstream breakdown

### Workstream WS-N: Normalizer boundary

- Goal: distinguish detached shadows from real geometry.
- Owner: coder, with independent reviewer.
- Work packages: WP-N1.
- Needs: normalizer behavior and asset examples.
- Provides: reviewed signal and feature boundary.
- Review boundary, when modifying the repository: normalizer logic and report only.

### Workstream WS-I: Evidence ledger

- Goal: give drawing work stable identity, counterpart, and size facts.
- Owner: reviewer, with integrator reconciliation.
- Work packages: WP-I1, WP-I2, WP-I3.
- Needs: asset tree, scenes, layout, local Servier corpus.
- Provides: provisional ledger records, a reconciliation pass, and four-archetype slice.
- Review boundary, when modifying the repository: ledger, reports, provenance records only.

### Workstream WS-X: Exemplars and kit

- Goal: demonstrate one visual language before it becomes family guidance.
- Owner: SVG expert coder, planner, `image_evaluator`, manager in separate decisions.
- Work packages: WP-X1 through WP-X6.
- Needs: M0 boundary and M1-M3 facts.
- Provides: fixtures, selection, exemplars, kit.
- Review boundary, when modifying the repository: four exemplar families and review-only artifacts.

### Workstreams WS-C through WS-O: Family rebuilds

- Goal: rebuild one physical or composite family from frozen kit.
- Owner: one fresh SVG expert coder per family, fresh evaluator per batch.
- Work packages: WP-C1, WP-H1, WP-B1, WP-E1, WP-S1, WP-O1.
- Needs: WP-X6 plus family board and provenance.
- Provides: reviewed SVGs, bindings, source evidence.
- Review boundary, when modifying the repository: named family and direct bindings only.

### Workstreams WS-R and WS-V: Integration and validation

- Goal: prove tree through real consumers without brittle appearance tests.
- Owner: integrator, tester, `playwright_operator`, `image_evaluator`.
- Work packages: WP-R1 and WP-V1.
- Needs: all family packages and frozen tree.
- Provides: captures, findings, gate results, closure report.
- Review boundary, when modifying the repository: review tooling and docs after source freeze.

## Work packages

### Work package WP-N1: Audit the floor-shadow signal

- Owner: coder, reviewed by reviewer.
- Touch points: normalizer, report-only audit, kit feature note.
- Depends on: none.
- Acceptance criteria: classify every candidate and reproduce reviewer verdicts after tightening signal.
- Evidence or review, when useful: candidate report with object and path identifiers.
- Obvious follow-ons: give boundary to WP-X1.

### Work package WP-I1: Reconcile review roles

- Owner: reviewer, reconciled by integrator.
- Touch points: SVG inventory, object consumers, ledger.
- Depends on: none; begins concurrently with WP-I2 and WP-I3 on file-disjoint evidence.
- Acceptance criteria: each asset has one provisional role, family, disposition, and applicable composite
  context; integrator reconciles it with WP-I2 and WP-I3 before WP-X1.
- Evidence or review, when useful: inventory and consumer trace keyed by asset path.
- Obvious follow-ons: reconcile, rather than serially unblock, WP-I2 and WP-I3.

### Work package WP-I2: Record Servier counterparts

- Owner: integrator.
- Touch points: ledger and `assets/equipment/SOURCES.md`.
- Depends on: none; begins from current asset paths and names concurrently with WP-I1 and WP-I3.
- Acceptance criteria: record provisional `servier_source`, `servier_adjacent`, or `no_servier_source`;
  direct reuse records adaptation and CC-BY-3.0 attribution; reconcile the path keys and subjects with
  WP-I1 and WP-I3 before WP-X1.
- Evidence or review, when useful: source path, structural note, or bounded search terms keyed by current
  asset path.
- Obvious follow-ons: route reconciled record to family owner.

### Work package WP-I3: Measure flatness and placement size

- Owner: integrator, reviewed by reviewer.
- Touch points: `tools/scene_scale_report.mjs` and census report.
- Depends on: none; begins from current asset paths concurrently with WP-I1 and WP-I2.
- Acceptance criteria: report provisional minimum, median, maximum after `reflowUniformScale`, render mode,
  workspace; unplaced assets declare nominal size; reconcile asset keys with WP-I1 and WP-I2 before
  WP-X1.
- Evidence or review, when useful: frame-width fraction and CSS pixels at canonical and smallest frame,
  keyed by current asset path.
- Obvious follow-ons: deliver reconciled exemplar slice to WP-X1 and full census to family packages.

### Work package WP-X1: Build reference boards

- Owner: reviewer, one fresh owner per archetype.
- Touch points: four boards and construction briefs.
- Depends on: WP-N1 and the reconciled WP-I1, WP-I2, and WP-I3 records.
- Acceptance criteria: board answers recognizability and volume; records bounded manufacturer/manual search,
  chosen projection, characteristic parts, and real-size massing thumbnails.
- Evidence or review, when useful: normally three viewpoints, at least one three-quarter view.
- Obvious follow-ons: hand briefs to WP-X2.

### Work package WP-X2: Compare candidate directions

- Owner: SVG expert coder per archetype; `image_evaluator` narrows shortlist.
- Touch points: developed-massing candidates and bench composites.
- Depends on: WP-X1.
- Acceptance criteria: candidates vary depth treatment, render at use size, and produce about five ranked
  candidates with cited objects.
- Evidence or review, when useful: silhouette diagnostic, massing thumbnails, composite.
- Obvious follow-ons: send shortlist to WP-X3.

### Work package WP-X3: Select the direction

- Owner: manager, with user preference when available.
- Touch points: candidate fixtures and selection record.
- Depends on: WP-X2.
- Acceptance criteria: preference wins; otherwise record default based on Servier, reference, size,
  evaluator evidence.
- Evidence or review, when useful: five concrete pictures and ranking citations.
- Obvious follow-ons: preserve candidates and release selection to WP-X4.

### Work package WP-X4: Polish exemplars

- Owner: SVG expert coder per archetype, fresh `image_evaluator` review.
- Touch points: T75 flask, centrifuge, micropipette, material vessel families.
- Depends on: WP-X3.
- Acceptance criteria: pass recognition, reference-back, bench coherence, two-color/multi-fill material
  range; retain runtime semantic anchors and material behavior.
- Evidence or review, when useful: actual workspace render and board comparison.
- Obvious follow-ons: hand measurements to WP-X5.

### Work package WP-X5: Measure construction constraints

- Owner: coder, reviewed by planner.
- Touch points: exemplar renders and kit constraints.
- Depends on: WP-X4.
- Acceptance criteria: tune 0.75 CSS px detail and 1.0 CSS px contour starting floors at minimum size;
  normalize authored widths by viewBox.
- Evidence or review, when useful: minimum-size render measurements.
- Obvious follow-ons: supply constraints to WP-X6.

### Work package WP-X6: Publish construction kit

- Owner: planner, with measurement review by coder.
- Touch points: `docs/figures/equipment_kit/` and durable SVG guidance if evidence warrants.
- Depends on: WP-X4, WP-X5.
- Acceptance criteria: publish exemplars, swatches, elevation/light, candidate fixtures, floors, face values,
  and successful-direction notes outside `assets/`.
- Evidence or review, when useful: every constraint traces to measurement or shown principle.
- Obvious follow-ons: dispatch all family packages.

### Work packages WP-C1 through WP-O1: Rebuild family batches

- Owner: fresh SVG expert coder per family; fresh `image_evaluator` per batch.
- Touch points: assigned SVG family, direct bindings, board, provenance, review render.
- Depends on: WP-X6 -- kit is common authority.
- Acceptance criteria: preserve meaningful `preserveAspectRatio`, stylesheet styling, anchors, group order,
  class hooks, unique IDs, material policy; pass recognition and reference-back at real size. Static repeated
  parts may use `symbol` and `use`; material forms express repeated parts directly.
- Evidence or review, when useful: kit, board, workspace render travel in evaluator brief.
- Obvious follow-ons: hand review to WP-R1; return blocking findings only to owning family.

### Work package WP-R1: Review real consumers

- Owner: integrator, `playwright_operator`, `image_evaluator` in separate roles.
- Touch points: review surfaces, captures, findings report.
- Depends on: WP-C1, WP-H1, WP-B1, WP-E1, WP-S1, WP-O1.
- Acceptance criteria: inspect inline DOM and `<img>`, `bench`, `hood`, `cell_counter`, `microscope`,
  active/candidate rings, grayscale separation, contrast handoff.
- Evidence or review, when useful: real render path, not a parallel mock.
- Obvious follow-ons: freeze repaired tree for WP-V1.

### Work package WP-V1: Validate and publish closure evidence

- Owner: tester and integrator.
- Touch points: frozen tree, final artifact, plan, changelog.
- Depends on: WP-R1.
- Acceptance criteria: relevant gates pass; final artifact matches frozen tree; later preference opens bounded
  repair rather than invalidating closure.
- Evidence or review, when useful: exact commands, outcomes, independent visual report.
- Obvious follow-ons: the frozen-tree validation record is published; a later preference remains a bounded follow-on.

## Acceptance criteria and gates

- Provenance gate: physical objects have E1 evidence before redraw.
- Board gate: boards answer identity and volume, then support reference-back review.
- Candidate gate: M5 proves coherent volume or repeats with changed massing hypothesis.
- Selection gate: preference decides when present; manager default otherwise permits M7.
- Kit gate: technical rules trace to measurements and visual rules to exemplars.
- Family gate: kit, board, real-size render support fresh evaluator review together.
- Integration gate: real render modes and workspaces have no unresolved concrete finding.
- Structural gate: existing SVG, material, object, build, browser gates pass on frozen tree.

## Test and verification strategy

### Permanent regression coverage

Keep tests for XML/security, semantic SVG vocabulary, local references, manifest resolution, material
compilation, state selection, ID namespacing, and real browser delivery. Every permanent Python, Node, or
Playwright check must satisfy the stability and behavior criteria in
[PYTEST_STYLE.md](../../PYTEST_STYLE.md): it covers durable product logic, not a report helper or the
current artwork snapshot. Do not freeze preference, candidate ordering, inventories, CSS formulas, exact
frame measurements, pixels, or hashes into any permanent suite.

### One-time implementation evidence

- M0 candidate audit and filter support note.
- E1 ledger, E2 boards, E3 fixtures, E4 kit measurements.
- True-size renders, family/composite surfaces, real built-app captures, evaluator findings.
- Candidate-renderer self-checks, census reconciliation, compact-frame measurements, and screenshot facts.
- Protected-interface byte record and exact final commands on frozen tree.

These checks may use disposable scripts or scratch assertions while the rebuild is in progress. Their
recorded reports and captures may remain as evidence, but implementation-only assertions do not remain
under `tests/` after closure.

Wrong subject, lost geometry, state drift, broken composite, or concrete evaluator finding blocks only its
owner package. A taste comment without a referent is advisory. A structural failure blocks M12.

## Migration and compatibility policy

This is a pre-production clean redesign. Owners replace outdated drawing structures and rules directly when
the selected kit proves a stronger design. No legacy rendering, schema, or source compatibility gate remains
merely to preserve rejected art. Existing contracts remain in force; this plan does not alter
[PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md).

## Risk register

| Risk                        | Impact | Trigger                                           | Owner      | Mitigation                              |
| --------------------------- | ------ | ------------------------------------------------- | ---------- | --------------------------------------- |
| Flat icons ship as objects  | High   | One plane without documented flat-subject reason. | SVG expert | E3/E6 composite and recognition review. |
| Servier source goes unused  | High   | Local counterpart but `no_servier_source`.        | Integrator | E1 source path/search record.           |
| Rules outrun evidence       | High   | Guidance names unproven property.                 | Planner    | E4 only extracts exemplar results.      |
| Research is ignored         | High   | Finished art cannot trace to board.               | Reviewer   | E2 reference-back check.                |
| Evaluator substitutes taste | Medium | No object, state, plane, or size cited.           | Manager    | E5 three-artifact brief.                |
| Normalizer removes a base   | Medium | Base matches bottom-band heuristic.               | Coder      | E9 audit then signal fix.               |
| Infrastructure outruns art  | Medium | Census ends before viable candidates.             | Manager    | Four-family slice unblocks exemplars.   |
| Late preference differs     | Medium | User selects non-default candidate.               | Manager    | Retain fixtures and re-extract kit.     |

## Rollout and release checklist

- [x] Close M0 audit and feature boundary.
- [x] Reconcile M1-M3 evidence and exemplar slice.
- [x] Complete M4 boards and M5 shortlist.
- [x] Record M6 manager default.
- [x] Finish M7 exemplars and M8 kit.
- [x] Complete M9-M11 family reviews.
- [x] Capture M12 consumer evidence and publish final figures from the frozen tree.
- [ ] Record later preference as bounded follow-on repair (non-blocking future work).

## Documentation close-out requirements

- Active plan: update milestone status; retain consistency plan as structural history until closure.
- `docs/CHANGELOG.md`: record demonstrated direction, batches, gates, closure facts as they occur.
- [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md): update only rules demonstrated in M7-M8.
- [HUMAN_GUIDANCE.md](../../HUMAN_GUIDANCE.md): record only stable authoring corrections.
- TODO and ROADMAP: keep result-interface work outside this plan.
- Archive / closure notes: archive only after M12 evidence completes.

## Patch plan and reporting format

- Patch 1: M0-M3 audit and ledger evidence.
- Patch 2: M4-M6 boards, candidates, shortlist, selection.
- Patch 3: M7-M8 exemplars, measurements, kit.
- Patch 4: M9 consumable and labware families.
- Patch 5: M10 tool and instrument families.
- Patch 6: M11 electrophoresis, safety, overlays, evidence families.
- Patch 7: M12 consumer review, validation, figures, close-out docs.

Each report names package, source evidence, construction decision, files, render context, validation,
independent finding, next dependency. It separates evidence from preference and records manager-default
reason when no user vote is available.

## Resolved decisions

- Rejected visual result requires workflow redesign, not production-code stabilization.
- M0 through M12 are all named; M0 is prerequisite, leaving twelve post-unblock delivery stages.
- Servier is preferred style-source; real references define identity.
- Centrifuge is hinged exemplar; material vessel proves runtime color behavior.
- Construction kit, not appearance snapshots, is batch visual authority.
- Manager default is provisional and reversible by later preference.
- Protected result composites remain byte-preserved and out of scope.

## Open questions and decisions needed

- Manager/subagent decision procedure:
  - Decision owner or dedicated class: manager default; user preference; `image_evaluator` assessment;
    architect only for a proposed cross-cutting contract change.
  - Evidence and decision rule: choose the direction best supported by Servier consistency, reference
    fidelity, real-size legibility, coherent bench depth, and cited evaluator evidence.
- Non-blocking follow-up: late preference opens only re-selection and named-family review; it does not
  restore legacy visual compatibility.

## E1-E10 implementation requirements

### E1. Start from Servier evidence

Search local Servier lab apparatus and wider tree before drawing. Record source path, structural adjacency
and what it guided, or bounded search terms. Adapt a direct source when it makes a coherent object and
record CC-BY-3.0 attribution in `assets/equipment/SOURCES.md`.

### E2. Make boards explain construction

Boards explain recognizability and volume. Prefer manufacturer pages/manuals, record access dates, and
search manufacturer, object class, and Servier metadata. Finished objects pass reference-back for silhouette,
proportions, planes, openings, controls, and characteristic parts.

### E3. Prove volume on four exemplars

Use T75 flask, centrifuge, micropipette, material vessel. Briefs specify recognition, projection, real-size
massing, characteristic parts, line hierarchy, face values. Manufactured equipment shows multiple planes
unless genuinely flat; cylinders use coherent ellipses; depth uses overlap and face value first.

Each board includes an installed-corpus citation and search-anchor table. It names the local corpus path,
the literal heading or search anchor, the construction question, and the part it informs. The required
rows cover volume/perspective/cuts, tubes/caps/cylinders, line hierarchy, SVG structure, and draw order.
The centrifuge board also cites `HINGING AND ROTATING FLAPS AND DOORS` and maps the hinge axis, lid swing,
and visible underside to its construction brief. The table keeps general illustration guidance auditable
without confusing it with manufacturer evidence for object identity.

### E4. Extract demonstrated kit rules

Keep measured constraints separate from principles. Tune 0.75 CSS px detail and 1.0 CSS px contour starting
floors at minimum size, normalize widths by viewBox, and include face values, swatches, elevation/light,
exemplars, fixtures. The measured table names a face-value count for each material and records every palette
swatch as a literal hex value, not an informal color name. Publish the selected viewer elevation and light
vector beside those literal swatches. Keep all five M5 candidate composites as reference fixtures, including
the four unselected directions, so a later preference can reselect and re-extract the kit without rebuilding
the comparison. Keep kit outside `assets/`, which `pipeline/gen_svg_manifest.py` discovers recursively.

### E5. Select and close on evidence

Present about five real-size composites. User preference wins; otherwise manager records provisional default
using Servier, reference, size, evaluator evidence. Evaluator briefs contain kit, board, workspace render;
concrete findings block. M12 treats later feedback as bounded repair work.

### E6. Size recognition evidence correctly

Use silhouette-only renders as a massing diagnostic. Gate finished object class identification at board-backed
specificity plus reference-back. Record silhouette, recognition, reference-back answers per object.

### E7. Census actual layout sizes

Follow `runPipeline` in `tools/scene_scale_report.mjs`. Report placement after `reflowUniformScale`, mode,
workspace, frame-width fraction, canonical/smallest CSS pixels. Confirm reachability after full build before
relying on this evidence.

### E8. Review integration through consumers

Review inline DOM and `<img>` modes; `bench`, `hood`, `cell_counter`, `microscope`; active/candidate rings,
grayscale separation, contrast handoff to `color-accessibility-expert`. Preserve meaningful
`preserveAspectRatio` and stylesheet styling. Inventory current review tools before adding surfaces.

### E9. Remove the art-constraining legacy signal

Floor-shadow detector distinguishes detached shadows from low-value base geometry. Report candidates and
verdicts, then tighten to reproduce them. Record sanitizer feature boundary so authors choose overlap and
face values deliberately.

### E10. Treat risks as active gates

Risk rows are execution controls. At each exit, manager checks flatness, unused sources, unproven rules,
detached research, evaluator drift, normalizer error, infrastructure drift, and late preference.
