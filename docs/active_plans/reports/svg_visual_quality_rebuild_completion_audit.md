# SVG visual-quality rebuild completion audit

## Current replacement-wave decision

**TECHNICAL PASS; HUMAN ACCEPTANCE OPEN (2026-08-26).** The replacement wave
resolves the identified D01-D05 and follow-up equipment regressions for the
current ordinary-equipment scope. The later direct human verdict supersedes the
earlier broad cross-package PASS; final artwork acceptance must come from a new
human review of the repaired tree.

## Evidence reconciliation

- The successful recovered build emitted 129 objects, 70 asset specs, 134 SVGs,
  60 DOM-required assets, and 57 scenes. Later comb and MTT corrections reduced
  the tree to 132 SVGs. The second pass deleted four standalone binary lead cards
  and their two objects, then added two apparatus-coordinate overlays. Current
  generation emits 127 objects, 67 asset specs, 130 SVGs, 64 DOM-required
  assets, and 58 scenes.
- Six current 1920 x 1080 full built-consumer scenes are recorded in
  [svg_m12_consumer_capture.md](svg_m12_consumer_capture.md). Full-scene and
  protocol console, page, request, and render errors are zero.
- Visible learner UI reached active whole P200, exact P200 subpart, Trypan
  candidate plus rail, and the neutral viability candidate union. Nine grayscale
  copies preserve active-solid versus candidate-dashed separation.
- Review found physically credible rounded, molded, cylindrical, transparent,
  and functional forms and no detached floor shadows.
- Both water-bath states retain credible detailed direct Servier geometry. The
  microscope uses a controlled repository-authored adaptation after direct
  Servier projection failed visual adequacy at consumer scale.

## Projection and transform reconciliation

The arbitrary-skew complaint is closed at both the named-state and full-tree
levels. The heat-block, lightbox, and microwave state pairs use stable frontal
housings and contain no rotate or skew transform. Their states change only the
functional lid, illuminated surface, controls, or heating indication.

The current 130-asset census finds rotation or skew syntax in only six source
files. Each remaining use is local and physically motivated rather than a
whole-object house-style tilt:

- `calculation_pad` rotates its separate pencil;
- `gel_cassette_top_plate_removed` rotates the plate that has been removed;
- `microscope` rotates one objective ellipse to follow the objective axis;
- `rocking_shaker_running` rotates the moving platform while the housing stays
  fixed; and
- the two T75 states retain the same recovered flask projection and use
  transforms for source scaling and two cap details.

The regenerated structural census and current source-gallery review cover all
130 files. The earlier independent 600 px and 180 px review covered the
preceding 132-source tree; its transform findings remain valid because the
second pass only removed lead cards and added untransformed tank overlays. This
is one-time implementation evidence, not a permanent source-token or count test.

## Milestone-by-milestone reconciliation

| Milestone                           | Current authoritative evidence                                                                                                                       | Status                          |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| M0 normalizer unblock               | `svg_floor_shadow_audit.md`; current 130-asset rerun reports 123 `SHADOW-NONE`, seven protected-result skips, and zero candidates                    | Complete                        |
| M1 inventory and roles              | `svg_visual_quality_inventory.md`; exact path-set reconciliation against all 130 retained sources                                                    | Complete                        |
| M2 Servier sweep                    | `svg_servier_counterpart_sweep.md` plus `assets/equipment/SOURCES.md`; exact path-set reconciliation and 130-of-130 coverage                         | Complete                        |
| M3 structural/size census           | `svg_visual_size_flatness_census.md` and `.json`; regenerated from 58 current scenes for all 130 assets                                              | Complete                        |
| M4 reference boards                 | T75, centrifuge, micropipette, and Falcon 15 mL reference-board reports                                                                              | Complete                        |
| M5 candidates                       | D01-D05 and their evaluator record remain a completed experiment but were rejected by direct human review                                            | Complete, rejected evidence     |
| M6 direction                        | `svg_visual_direction_selection.md`; the user's rejection superseded the provisional D04 choice with the source-first recovery direction             | Complete, superseded            |
| M7 exemplar polish                  | recovered established T75, direct Servier centrifuge, rounded micropipettes, and detailed Falcon evidence; current M12 evaluator re-review           | Complete technically            |
| M8 kit extraction                   | `docs/figures/equipment_kit/README.md` and refreshed `MEASUREMENTS.md`; object-specific, state-stable projection replaces the stale global skew rule | Complete                        |
| M9 consumables/labware              | WP-C1 and WP-C2 implementation/evaluator reports, each with a replacement-wave addendum                                                              | Complete technically            |
| M10 tools/instruments               | WP-B1, WP-B2, and WP-H1 implementation/evaluator reports, each with a replacement-wave addendum                                                      | Complete technically            |
| M11 electrophoresis/safety/overlays | WP-E1, WP-S1, and WP-O1 reports plus tank-owned exact terminal/connection state and the gel-comb ownership repair                                    | Complete technically            |
| M12 integration/validation          | current 130-card production-host pass; 3-of-3 exact terminal walkthrough; full repository suites; final human artwork acceptance remains open        | Technical pass; human gate open |

Exact inventory evidence, gallery counts, and browser captures are one-time
implementation checks, not permanent tests. The durable suite remains focused
on schemas, object/scene/protocol semantics, generation, and real runtime
behavior.

## Gallery and historical candidates

D01-D05 are retained historical snapshots. The canonical current review is
`docs/figures/equipment_kit/review.html`, generated by
`tools/render_svg_library_review.mjs`. The obsolete
`tools/render_svg_candidate_review.mjs` is deleted and owns no current
renderer. The current canonical gallery contains all 130 authored assets. The
final production-host rerun covered all 130 in their shipping modes and is recorded
in `svg_m12_render_mode_review.md`.

The 546 x 307 compact PNGs/facts are earlier one-time evidence. A fresh compact
recapture after the final build stalled on `bench_basic` before its ready marker
or screenshot, with no Playwright exception. This is a disclosed residual
evidence gap, not a visual defect; no document calls that compact set freshly
regenerated.

## Audit resolutions

The audit repairs are complete:

- gallery contract, documentation, generator routing, and dead candidate-tool
  references are corrected;
- the permanent-test policy cleanup is complete and independently passes;
- microscope provenance is corrected; and
- direct Servier water-bath provenance is confirmed;
- both MTT states now select the canonical microtube; its material amount paints
  20 mg at 8 percent or hides the canonical compiled material region when empty; and
- the standalone red and black binary lead cards are deleted; the tank now owns
  exact black/red terminal subparts and connection overlays aligned to those terminals; and
- exhaustive E8 render-mode review now passes through the shared production
  SVG host; and
- the cassette solely owns inserted-comb state, the standalone comb appears
  only after removal, and the power supply owns voltage/running state only.

## Final repository gates

| Gate                                 | Result                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| Current production build             | PASS: 127 objects, 67 asset specs, 130 SVGs, 64 DOM-required assets, 58 scenes |
| Content lint                         | PASS: 244 YAML files; zero errors, warnings, or advisories                     |
| `python3 -m pytest tests/ -q`        | PASS: 7,662 passed                                                             |
| `./check_codebase.sh`                | PASS: all five gates; Node 675 total, 673 passed, 2 skipped                    |
| `npx playwright test --reporter=dot` | PASS: 113 passed                                                               |
| Current production-host review       | PASS: 130 cards; 64 DOM, 66 image; zero load, mode, or browser failures        |
| Exact terminal visible workflow      | PASS: 3 of 3 steps; both wrong-sibling probes rejected; zero errors            |

## Permanent-test boundary

Gallery checks, contact sheets, exact inventories, captures, grayscale copies,
and temporary render scripts are one-time implementation evidence. They are not
permanent tests or fixtures. The retained permanent suites cover durable
schemas, semantic/runtime behavior, compiler/build behavior, and connected
browser workflows.

## Historical audit

Older D01-D05/frozen-tree counts and approvals remain historical implementation
evidence only. They do not substitute for current replacement-wave proof.
