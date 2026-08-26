# Plan: strengthen the SVG visual-quality rebuild plan

## Context

[docs/active_plans/active/svg_visual_quality_rebuild_plan.md](svg_visual_quality_rebuild_plan.md)
has sound structure and was still rejected on sight. The user named why: the art reads as flat UI icons
rather than Bioicons Servier laboratory objects, and the three-dimensional visual language the
`svg-creator-expert` skill recommends was never achieved. Both complaints are now measured.

The previous sweep produced valid, consistent, palette-matched **icons** when the requested outcome was
**objects**, and every criterion in the plan treated those as the same thing.

This plan revises the target document along four axes:

1. **Exemplars before rules.** Produce a few unmistakably successful three-dimensional objects, verify
   them, then extract the house language from what demonstrably worked.
2. **Preference vote, not approval gate.** Subagents develop and narrow candidate visual directions to
   about five, and the user picks the one they like. That selection is preferred evidence. When it is
   unavailable, the manager selects on recorded criteria and execution continues.
3. **Every milestone completes with manager and subagents.** Each exit criterion names a subagent
   decision or a measurement.
4. **Twelve small milestones.** Progress stays visible, dispatch stays simple, and each milestone
   carries one design decision rather than several.

This plan edits planning documents. The SVG, CSS, and TypeScript work belongs to the milestones it
defines.

## Current implementation status

The historical M0-M12 rollout completed its parser, state, material, and
consumer work, but its D01-D05 visual direction was rejected by direct human
review on 2026-08-26 as cubist rather than realistic laboratory equipment.
Those candidate comparisons and their former approvals are retained as
historical implementation evidence only; they are not the current target or a
selection pool.

The active replacement wave preserves the established asset identities and
runtime contracts while rebuilding the visual forms around physically
credible rounded shells, molded surfaces, recesses, cylinders, transparent
vessels, and functional overlaps. It takes detailed Servier geometry directly
where that geometry is visually credible, and uses controlled repository
adaptations where exact source projection is not. The human gallery is
the generated complete equipment-library review at
`docs/figures/equipment_kit/review.html`; regenerate it with
`tools/render_svg_library_review.mjs`.
The old four-object candidate URL redirects there.

The technical history in the M12 records remains useful and the replacement
wave now has current built-consumer full-scene evidence and final repository
gates. The compact 546 x 307 set remains earlier one-time evidence: a fresh
post-final-build compact recapture stalled before the bench ready marker without
a Playwright exception. Record that residual evidence gap accurately rather
than calling compact PNGs freshly regenerated. This plan remains in `active/`
because its path is user-staged; documentation records progress in place
without changing the index.

### Current replacement-wave evidence and remaining gates

Human review on 2026-08-26 rejected a subset of the replacement wave after the
blind inspection and full-suite run. That rejection invalidates the earlier
visual closure claim. Lead connector logic, arbitrary instrument skew, a copied
MTT-empty microtube, and regressions from the established T75 and microtube art
were not caught by the blind pass. The affected vessel and instrument assets have now been recovered
from the repository's frozen final-equipment contact sheet. Both MTT states now
select the canonical Servier-derived microtube; generic mass-capacity rendering
shows 20 mg at 8 percent or hides the material region when empty. Removing the
redundant empty-vial redraw first left 134 authored SVGs; the later ownership
repairs removed the false full-cassette comb state and the material-specific MTT
vial. A second-pass browser audit then rejected the remaining four standalone
lead-state SVGs: they depicted a cable, plug, and private terminal as one binary
card instead of depicting a connection to the apparatus. Those four forms and
their two object definitions are now deleted. The tank owns two exact terminal
subparts and two connected-lead overlays, leaving 130 SVGs and 64 DOM-required
assets. The source gallery, production-renderer gallery, and production-shaped scene captures were used as one-time visual
evidence; no screenshot or pixel test was added.

- Rebuilt/re-reviewed exemplars: direct detailed Servier centrifuge and Falcon
  15 mL, the recovered transparent T75 pair, and rounded micropipette family. The independent
  exemplar review initially found the Falcon minimum-fill floor and the
  multichannel's box-like tip bank; both were repaired and independently
  re-reviewed.
- M9 consumables/labware, M10 instruments/tools, and M11 electrophoresis,
  safety, and contextual-art packages have received their owned repairs and
  package-level visual re-review. The second pass supersedes the earlier lead-gap
  repair: no standalone attached/unattached lead state remains. The apparatus
  connection workflow now targets measured black and red lid terminals and
  adds aligned plug overlays only after the exact terminal is selected. Full built-consumer M12 evidence covers
  six scenes, active whole/exact subpart/Trypan candidate/viability-union UI
  states, and nine grayscale copies.
- The Falcon material surface now includes its base meniscus role. The
  microtube material calibration no longer uses arbitrary 8/92 percent clamps;
  its body-start calibration is restored to 35.98 percent.
- Implementation visual evidence (gallery link checks, contact sheets, exact
  inventories, scene captures, grayscale review, and temporary render scripts)
  is one-time evidence, not permanent test coverage. Existing durable semantic,
  compiler, and real-runtime material tests remain the proper regression
  boundary.
- The all-asset blind inspection rendered and reviewed the former 135-source
  tree at 600 px and 180 px before renewed human assessment. Human review then
  found contextual logic, ownership, and regression failures, so its `PASS` is
  historical implementation evidence rather than an acceptance result. The
  corrected record is in
  `docs/active_plans/reports/svg_all_asset_blind_inspection.md`.
- E8's exhaustive shipping-render-mode review is exercised by the built
  `/equipment_review.html` page. It shares the production `SvgHost` with real
  scenes. The second-pass rerun covered all 130 entries: 64 inline DOM, 66
  image, 430 namespaced IDs, zero load/mode/browser failures, and zero 390 px
  horizontal overflow.
  The one-time record is
  `docs/active_plans/reports/svg_m12_render_mode_review.md`.
- The earlier full gates passed on the rejected tree and therefore did not
  close this plan. The current ownership-repaired build emits 127 objects,
  67 asset specs, 130 SVGs, 64 DOM-required assets, and 58 scenes. Current
  full-suite results are recorded after rerun in the M12 validation record.
  Human visual acceptance remains distinct from those automated repository gates.
  The implementation and evidence summary is
  `docs/active_plans/reports/svg_visual_quality_second_pass.md`.

## Root cause of the rejection

**The art is original rather than Servier-derived.** A full Bioicons checkout sits in the repo at
`OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Lab_apparatus/Servier/`, holding 30 lab-apparatus files
including direct counterparts for objects the repo drew from scratch: `incubator`, `centrifuge`,
`microscope`, `spectrophotometer`, `gel-electrophoresis`, `electrophoresis-chamber`, `bath-empty`,
`bath_filled`, `agitator`, `scale`, `glassslide-top`, and the `cuvette` family. Servier's
`centrifuge.svg` carries roughly 26,000 tokens of modeled path data. The repo's `incubator.svg` is 21
hand-authored lines wearing a Servier-like palette.

**The volumetric language is absent.**
[assets/equipment/static/incubator.svg](../../../assets/equipment/static/incubator.svg)
is built from `h` and `v` path segments and axis-aligned circles: one plane, front elevation, which is
the projection that expresses the least volume. Systemic: 8 of 62 static equipment files use an
`<ellipse>`, and 2 of 62 use a rotation or skew.

## Primary acceptance criterion

Place this above the objectives; every other criterion sits under it.

> The rebuilt equipment looks like coherent three-dimensional laboratory equipment in the established
> Servier visual language. Technical checks support that result.

Two evidence sources answer two different questions. **Servier establishes how the house style draws an
object. Manufacturer pages and manuals establish what the object is.** Use both, each for its own
question.

## Decision model: five candidates, one vote, a default path

Visual direction is a preference, so the user picks it. Execution keeps moving either way.

```
evidence -> candidate directions -> subagent review -> shortlist of ~5
-> user preference vote when available -> manager selection on recorded criteria
-> record the construction reference -> continue autonomously
```

How it runs:

- **Subagents build and narrow.** M5 develops candidate directions across the four exemplar archetypes
  and an `image_evaluator` narrows them to about five credible, visually distinct options. Each
  candidate arrives as a bench composite at real size, so the choice is between five concrete pictures.
- **The user votes on preference.** The question is "which of these do you like", not "does this satisfy
  the checklist". Five pictures, one pick.
- **The manager has a defined default.** When a vote is unavailable, the manager selects the candidate
  best supported by Servier consistency, real-object reference fidelity, actual-size legibility, and
  independent visual review, records it as provisional with the reasoning, and continues.
- **The selection becomes a construction reference.** The chosen direction becomes the construction kit that every
  later milestone compares against. A later user vote that differs opens a bounded re-selection
  milestone: the kit is re-extracted from the newly preferred candidate, and the batches already drawn
  are reviewed against it. Keeping all five candidate artifacts as historical construction evidence
  makes that switch cheap without creating test fixtures.

The same shape applies at M12: the completed rebuild publishes a self-contained review artifact and the
technical implementation can proceed on measured and independent evidence. Human visual closure remains
open until the user accepts the artwork.

## The revised spine

```
legacy unblock -> inventory -> evidence -> candidate directions -> vote or default
-> exemplar polish -> kit extraction -> family batches -> integration -> validation
```

## Milestones

Thirteen labelled milestones, spanning one unblock milestone plus twelve rollout
stages, each with one outcome, one verification, and a stated parallel width.

| M   | Title                              | Exit criterion                                                                                                      | Max parallel doers |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------ |
| M0  | Unblock the normalizer             | Floor-shadow audit reviewed; the signal matches shadows only; the filter constraint is documented in the kit brief  | 2                  |
| M1  | Inventory and roles                | Every retained SVG carries one review role, one physical family, one disposition                                    | 2                  |
| M2  | Servier counterpart sweep          | Every object records `servier_source`, `servier_adjacent`, or `no_servier_source` with search terms                 | 3                  |
| M3  | Structural and size census         | Every asset carries visible-root cluster count, ellipse presence, rotation/skew presence, and a rendered-size range | 3                  |
| M4  | Exemplar reference boards          | Four boards answer the recognizability and volume questions                                                         | 4                  |
| M5  | Candidate directions and shortlist | About five distinct bench composites at real size, narrowed and ranked with cited reasons                           | 4                  |
| M6  | Direction selection                | One direction selected by user vote or by the manager default, recorded with reasoning                              | 1                  |
| M7  | Exemplar polish                    | Four finished exemplars pass recognition, reference-back, bench coherence, and material-range review                | 4                  |
| M8  | Kit extraction                     | Construction kit published in a review location; stroke floors tuned on the exemplars                               | 2                  |
| M9  | Consumables and labware            | WP-C families rebuilt and reviewed against the kit                                                                  | 3                  |
| M10 | Tools and instruments              | WP-H and WP-B families rebuilt and reviewed against the kit                                                         | 3                  |
| M11 | Electrophoresis, safety, overlays  | WP-E, WP-S, WP-O families rebuilt and reviewed against the kit                                                      | 3                  |
| M12 | Integration and validation         | Render modes, workspaces, ring legibility, grayscale, contrast, and repo gates pass on the frozen tree              | 3                  |

Splitting the old bulk-rebuild milestone into M9, M10, and M11 keeps roughly twenty work packages and
several construction decisions visible instead of hiding them behind one status line.

**Parallel dispatch.** M0 through M4 are file-disjoint and run concurrently from the start: the audit
touches the normalizer, the sweep touches the ledger, the census reads the tree, and the boards gather
references. That collapses the plan's opening from five serial stages into one wave. M9, M10, and M11
own disjoint SVG families and run concurrently once the kit exists, each dispatched to a fresh SVG
expert coder. Within a batch milestone, each family is one atomic package: one owner, one family, one
review.

## Edits to make

### E1. Servier as preferred starting evidence (M2, and every batch milestone)

Per object, before drawing:

1. Search `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Lab_apparatus/Servier/` and the wider Servier
   tree. The index at
   `~/.claude/skills/svg-creator-expert/references/local-only/LOCAL_SERVIER_SVG_FILE_PATHS.txt` lists
   the local set.
2. Record `servier_source` with the path, `servier_adjacent`, or `no_servier_source` with search terms.
   `servier_adjacent` means a Servier file supplies structural guidance -- how a comparable housing,
   vessel, opening, or mechanism is constructed and stacked -- and the record names what it guided. When
   the borrowing is structural, use `servier_adjacent`; when the resemblance is palette alone, the
   accurate record is `no_servier_source`. A defined boundary here keeps the category meaningful.
3. Where a source exists, start from it and adapt where adaptation produces a more coherent house
   object. Record what changed and why.
4. Verify `cc-by-3.0` license and attribution; record it in `assets/equipment/SOURCES.md`.

An object with an unused local counterpart ranks above cosmetic work: it is the cheapest quality gain in
the tree.

- **Owner**: integrator. **Validation**: every ledger row carries one of the three values with its
  supporting path or search terms.

### E2. Reference boards judged on what they explain (M4, every batch milestone)

A board is accepted when it answers:

1. **What makes this object recognizable?** Characteristic parts drawn from what several real examples
   share, so the result stays unbranded.
2. **What gives it convincing volume?** Which planes, openings, and cylindrical features carry its
   three-dimensionality, and the view that shows them best.

Typically three or more images from distinct viewpoints, at least one three-quarter, each with URL and
access date. That is the normal shape of a sufficient board; a board answering both questions from two
excellent references is sufficient.

**Prefer a manufacturer page or manual where one exists.** Image search gives breadth; manuals give
structure -- hinges, door swings, vessel geometry, control relationships. **A completed search is
bounded:** check the manufacturer name when the object names one, the object class, and any Servier
source metadata. Three lookups with a recorded result is a finished search.

**Keep the board attached to the finished drawing.** At batch review the finished object is compared
back against its own board: are silhouette, proportions, visible planes, openings, controls, and
characteristic parts still supported by the references? A drawing that traces to its board passes this
check; one that has drifted returns to its owner. This makes the board the standard the result is judged
against rather than proof that research happened.

The standard is **structurally faithful, visually simplified**. Dropping a vent grille, fastener row, or
label is correct: these render small and simplification is the point of the dialect. Keep the door on
the face where the references put it, keep the controls the object actually has, keep vessel proportions,
and keep the parts the object is identified by.

- **Owner**: reviewer. **Validation**: each board answers both questions and names its manufacturer or
  manual source when one was found.

### E3. Prove the volumetric language on exemplars (M5, M7)

Four archetypes:

| Archetype                                 | Subject                      | Why it earns a slot                                                                     |
| ----------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------- |
| Transparent vessel                        | T75 flask family             | Glass, liquid boundary, hardest silhouette                                              |
| Benchtop instrument with a hinged opening | Centrifuge family            | Housing, controls, a lid that opens, cylindrical rotor                                  |
| Handheld tool                             | Micropipette family          | Long tapered masses, grip proportion                                                    |
| Material-rendered vessel                  | `falcon_15ml` or `microtube` | Semantic band, `bottom`/`body`/`surface` split, paint roles computed from runtime color |

**The benchtop slot is the centrifuge rather than the plate reader.** Hinged openings are the recurring
hard class -- centrifuge, water bath, incubator, microwave, gel cassette, sharps. An exemplar that
exercises a hinge gives all six families one convention to inherit. The centrifuge also brings a
cylindrical rotor, and Servier ships a modeled counterpart, so it exercises the E1 source-reuse path at
the same time. Anchor it to `HINGING AND ROTATING FLAPS AND DOORS`.

**The material-rendered vessel is an addition.** The five material forms carry the hardest contract in
the tree, and including one now proves the value grammar works with the `highlight` and `shadow`
adjustments before the grammar propagates. Render it at several fill levels with two contrasting
material colors.

Confirm against M1 that these four cover most of the hard construction classes present; swap a subject
if one is unrepresented.

**Construction brief per object**: one-sentence recognition target; chosen projection; two or three
massing thumbnails compared at real rendered size; characteristic-part list mapped onto major masses;
then line hierarchy and face values. Cite the installed corpus:

| Need                      | Source and search term                                                                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Volume, perspective, cuts | `local-only/object_construction/How_to_Draw_...-2013.md`: `X-Y-Z COORDINATE SYSTEM`, `WORKING WITH VOLUME`, `PLANNING BEFORE PERSPECTIVE`, `CUTTING VOLUMES` |
| Tubes, caps, cylinders    | same source, `ELLIPSE BASICS AND TERMINOLOGY`; `local-only/technical_drawing/Technical_Drawing_...-2023.md`, `Curves and Circles in Perspective`             |
| Lids and doors            | `How_to_Draw_...-2013.md`, `HINGING AND ROTATING FLAPS AND DOORS`                                                                                            |
| Line hierarchy            | `local-only/scientific_illustration/A_Handbook_of_Biological_Illustration-1988.md`, `heaviest lines are used to draw the closest parts`, `CLARITY`           |
| SVG structure             | `local-only/svg_authoring/Mastering_SVG-2018.md`, `viewBox and viewport in SVG`                                                                              |
| Draw order                | `local-only/vector_tools/Quick_and_Easy_Vector_Graphics-2020.md`, `Z-Ordering`                                                                               |

**M5 treats projection as an experiment.** Observed failure: the tree reads as flat icons. Suspected
cause: no shared depth treatment and no volumetric construction. Candidates: a shared depth vector for
every object, a shared viewer elevation and light with per-object depth handling, and variations in
contour weight and face-value spread that produce visually distinct results. Success metric: an
`image_evaluator` reports which composites read as one coherent bench of laboratory objects, citing
specific objects. Revert criterion: when every candidate reads as flat, the construction approach is the
variable to change, and M5 runs again with revised massing.

Build candidates at **developed massing**, then polish the selected direction in M7. Massing plus face
values carries enough information to judge bench coherence, so the shortlist stays cheap to produce and
cheap to re-run.

**What generalizes to the batch milestones**, as expectations applied with judgment: manufactured
equipment shows more than one plane so it reads as a volume (a genuinely flat subject such as a slide,
pad, or tape strip records its reason and stays flat); cylindrical parts carry ellipses consistent with
the family; overlap and face value carry depth ahead of gradients. Where a Servier counterpart exists,
consistency with it is the default answer, and runtime, scientific, or state-family requirements justify
adaptation where they apply.

- **Owner**: SVG expert coder per archetype, four in parallel. **Validation**: `image_evaluator`
  shortlist with cited objects.

### E4. Extract the kit from the selected direction (M8)

Separate two kinds of rule.

**Measured technical constraints** belong in a table, because they sit below eyeball resolution:

- Rendered stroke floor. Start from 0.75 CSS px for detail and 1.0 CSS px for outer contour at an
  asset's minimum rendered size, and **tune both on the exemplars**. They are starting values; M7 and M8
  measure what stays legible in this renderer. A detail below the settled floor is simplified away.
  Authored `stroke-width` spans 1.2 to 9 with no shared scale, so the ratio is normalized to the viewBox
  to compare across files.
- Face-value count per material; palette as literal hex swatches.
- Depth comes from overlap and face value, which the sanitizer's supported feature set makes the
  reliable path.

**Demonstrated visual principles** live in the exemplars. Ship a construction kit containing the four
finished exemplars, the palette swatches, the selected viewer elevation and light vector, all five
candidate composites as construction references, and a note on what the selected direction got right. A new
object starts by copying the nearest archetype.

**Publish the kit in a review location such as `docs/figures/equipment_kit/`.**
[pipeline/gen_svg_manifest.py](../../../pipeline/gen_svg_manifest.py)
line 261 walks `assets/` with `rglob("*")`, so keeping the kit outside `assets/` keeps production
discovery, validation, and packaging focused on shipped art. Confirm the census and validator tools scope
the same way.

`symbol` and `use` serve repeated parts in static forms. Material-rendered forms express repeated parts
directly, which keeps them inside the material contract.

- **Owner**: planner, with a coder for the measurement pass. **Validation**: every constraint in the kit
  traces to a measurement taken on an exemplar.

### E5. Selection and closure decided by evidence (M6, M12)

**M6, direction selection.** The shortlist goes to the user as five pictures. When a preference arrives,
it decides. When it does not, the manager selects the candidate best supported by Servier consistency,
reference fidelity, real-size legibility, and evaluator ranking, and records the choice as provisional
with reasoning. Either way M7 starts the same day. Selecting here fixes the **visual direction**; the
completed rebuild is judged separately at M12.

**M12, technical closure and human acceptance.** Technical closure rests on each batch milestone's own
review, the integration checks, and repo gates on the material tree. The published artifact invites
human assessment; visual acceptance remains open until the user gives it. Later comments open a bounded
repair milestone with named families rather than being overwritten by an earlier evaluator result.

**Evaluator briefs carry three artifacts together**: the selected direction's kit, the object's own
reference board, and the real-size render on its real workspace. With all three present, "compare
against the kit" stays grounded. Findings cite a concrete object, state, plane, or use-size; findings
that cite one are blocking, and the rest are advisory. Each batch gets a fresh evaluator.

- **Owner**: manager for selection, `image_evaluator` for ranking. **Validation**: the selection record
  names the criteria that decided it.

### E6. Recognition evidence, sized correctly (every batch milestone)

- **Silhouette read, diagnostic.** Early in massing, render silhouette-only at minimum size and ask
  whether it reads as a volume or a flat panel. Treat the answer as evidence about massing. Objects like
  a centrifuge or incubator legitimately depend on openings and controls that a silhouette omits.
- **Finished-object recognition, the gate.** A blind evaluator identifies the object's correct class, or
  a scientifically reasonable functional class, at the specificity its reference board supports. Where
  the board establishes a centrifuge, "a benchtop centrifuge" passes; where the board itself shows a
  generic heating-or-shaking block, that generic answer passes. The gate catches unrecognizable art and
  lets accurate generic equipment through.
- **Reference-back check**, run in the same review.

- **Owner**: `image_evaluator`. **Validation**: three recorded answers per object.

### E7. Size census that matches the real layout (M3)

Reuse the `runPipeline` shape from
[tools/scene_scale_report.mjs](../../../tools/scene_scale_report.mjs).
Per asset emit min, median, and max box, each multiplied by that scene's `reflowUniformScale`, plus
workspaces and render mode. Unplaced assets carry a declared nominal size.

**Express sizes as a fraction of frame width, then convert.**
[pipeline/precompute_layout.mjs](../../../pipeline/precompute_layout.mjs)
lines 15-42 record that the engine's only viewport-dependent term is aspect ratio, so any 16:9 viewport
yields identical items: 1920x1080 is a canonical frame rather than the size users see. Actual CSS pixels
follow the real rendered frame width, and `tools/protocol_to_png.mjs` already defaults to 1280x900. The
census therefore reports fraction-of-frame plus pixels at both the canonical frame and the smallest
realistic frame width, and the stroke floor is checked against the smallest.

Run the four-family slice first so M4 through M7 proceed while the full census completes alongside them.

- **Owner**: integrator. **Validation**: `node --import tsx tools/scene_scale_report.mjs --all` produces
  per-placement boxes and applied scale for every scene.

### E8. Integration requirements (M12)

1. **Both render modes.** Each asset is reviewed in the mode it ships in. Inline DOM inherits page CSS
   and id namespacing; `<img>` renders as a leaf.
2. **The four live workspaces**: `bench`, `hood`, `cell_counter`, `microscope`, with surface bands
   present.
3. **Affordance-ring legibility, judged in the real UI.** Render active and candidate states and confirm
   the ring reads as a ring against the object behind it. Where an accent competes with the ring, adjust
   the accent. This is visual review, since looking at the ring on the object predicts the failure better
   than a color-distance threshold.
4. **Value-only legibility.** Face separation survives a grayscale render, which keeps the art correct
   when the deactivation treatment lands.
5. **Contrast handoff** to `color-accessibility-expert` for measured repair.
6. **Preserve two clean invariants**: every asset keeps a meaningful `preserveAspectRatio`, and styling
   stays in the stylesheet. Both hold today; the existing normalizer and `svg_validate.py` gates keep
   them.

The review-surface work package starts from an inventory of the eleven existing tools and extends the one
that fits each surface. Each family closes with a source-hygiene pass that preserves structural anchors,
group order, class hooks, and unique ids, and material forms run through the material policy.

- **Owner**: integrator, `playwright_operator`, `image_evaluator`. **Validation**: captures from the built
  app through the real render path.

### E9. Clear the legacy that constrains the art (M0)

Two items shape what an SVG can be, so they gate the rebuild:

- **Floor-shadow heuristic.** `detect_floor_shadow_candidates` matches any wide-flat bottom-band path
  whose fill is low-opacity or desaturated grey, which also describes a base plinth, a bottom front face,
  and a rounded instrument foot. Run report-only over the tree, review every candidate against its
  object, and tighten the signal so it selects shadows.
- **Filter support.** The sanitizer's supported feature set defines the shading path; record it in the
  kit brief so owners build depth from overlap and face value from the start.

- **Owner**: coder with reviewer. **Validation**: the audit report lists every candidate with a verdict,
  and the tightened signal reproduces those verdicts.

### E10. Risk register rows to add

| Risk                                    | Impact | Trigger                                                                 | Owner      | Mitigation                                                                                                                          |
| --------------------------------------- | ------ | ----------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Flat icons ship again as objects        | High   | A physical object reads as one unsupported plane in its real consumer   | SVG expert | Structural census routes review; exemplar and real-consumer visual judgment decide it (E3, E6).                                     |
| An available Servier source goes unused | High   | Ledger shows `no_servier_source` for an object with a local counterpart | Integrator | Counterpart check with recorded path or search terms (E1).                                                                          |
| Rules outrun demonstrated results       | High   | Guidance names a property no exemplar exhibits                          | Planner    | Rules extracted from the selected direction (E4).                                                                                   |
| Research collected, then set aside      | High   | A finished object no longer traces to its board                         | Reviewer   | Reference-back check runs with recognition (E2, E6).                                                                                |
| Evaluator drifts into taste             | Medium | A finding cites no concrete object, state, plane, or size               | Manager    | Three-artifact brief and concrete-referent requirement (E5).                                                                        |
| Normalizer selects real base geometry   | Medium | A wide grey or low-opacity base sits in the bottom band                 | Coder      | Report-only audit in M0, then tighten the signal (E9).                                                                              |
| Infrastructure outpaces the drawing     | Medium | Censuses advance while no candidate exists                              | Manager    | Four-family slice first; full census runs alongside drawing (E7).                                                                   |
| A late vote differs from the default    | Medium | The user prefers a candidate the manager set aside                      | Manager    | Keep all five candidate artifacts as historical construction evidence so re-selection re-extracts the kit cheaply (decision model). |

## Dispatchable tasks

Atomic: one owner, one outcome, one verification. The wave column shows what runs concurrently.

| #   | Task                                                           | Owner                               | Wave | Verification                                                                                            |
| --- | -------------------------------------------------------------- | ----------------------------------- | ---- | ------------------------------------------------------------------------------------------------------- |
| 1   | Restructure the plan: twelve milestones, vote model, E1-E10    | Planner                             | 1    | Every milestone exit names a subagent decision or a measurement                                         |
| 2   | Floor-shadow report-only audit and signal fix                  | Coder, reviewer                     | 1    | Audit report lists every candidate with a verdict; tightened signal reproduces them                     |
| 3   | Servier counterpart sweep                                      | Integrator                          | 1    | Every object records source, adjacency with what it guided, or search terms                             |
| 4   | Four-family size and flatness slice                            | Reviewer                            | 1    | Exemplar families carry fraction-of-frame and px at canonical and smallest frames                       |
| 5   | Full-tree census                                               | Reviewer                            | 1    | All current manifest assets carry visible-root cluster, ellipse, rotation/skew, and size-range evidence |
| 6   | Inventory and role ledger                                      | Reviewer, integrator                | 1    | Each SVG carries one role, one family, one disposition                                                  |
| 7   | Four exemplar reference boards                                 | Reviewer, one per archetype         | 2    | Each answers both questions and records its bounded manufacturer search                                 |
| 8   | Build candidate directions at developed massing                | SVG expert coder, one per archetype | 3    | Bench composites at real size for each candidate treatment                                              |
| 9   | Narrow to about five and rank with cited reasons               | `image_evaluator`                   | 4    | Shortlist names specific objects supporting each ranking                                                |
| 10  | Present five composites for preference vote; select or default | Manager                             | 5    | Selection record names the criteria or the vote that decided it                                         |
| 11  | Polish four exemplars in the selected direction                | SVG expert coder, one per archetype | 6    | Recognition, reference-back, bench coherence, material range all pass                                   |
| 12  | Tune stroke floors on the exemplars                            | Coder                               | 6    | Settled floors traced to measurements on real renders                                                   |
| 13  | Extract and publish the construction kit                       | Planner                             | 7    | Kit sits in a review location; every constraint traces to a measurement                                 |
| 14  | Existing-tool inventory for review surfaces                    | Integrator                          | 7    | Each of five surfaces names the tool it extends, or names the gap                                       |
| 15  | Family batches, one fresh coder per family                     | SVG expert coders                   | 8    | Each family passes its own review against the kit                                                       |

Waves 1 and 2 hold six independent tasks; dispatching them together collapses the opening from six
serial stages to two. Wave 8 runs M9, M10, and M11 concurrently on disjoint families.

## Execution note: use blueprint-plan-drafter for task 1

The target document already follows that skill's house format -- Context, Objectives, Design philosophy,
Scope, Non-goals, milestone table, per-milestone `Parallel-plan ready:` slots, work packages with
`Depends on`, risk register, rollout checklist. Task 1 is a major rewrite of that document, which is the
skill's stated purpose: it keeps the canonical core, preserves the parallel-dispatch slots, and sanctions
clean redesign where evidence shows the current design failed. Invoke `/blueprint-plan-drafter` for the
rewrite.

Two conventions to apply deliberately: its proof-ladder framing fits the M5 projection experiment, which
is the plan's one real unknown; and its requirement that every gate has a complete unattended path is
satisfied by the manager default at M6.

## Files to modify

- `docs/active_plans/active/svg_visual_quality_rebuild_plan.md` -- restructure to twelve milestones with
  the vote model; apply E1 through E10.
- `docs/CHANGELOG.md` -- one entry under `## 2026-08-25`, `### Behavior or Interface Changes`, recording
  the exemplar-first reorder, the five-candidate vote model with manager default, and the Servier-source
  and volumetric criteria.

Style: ASCII only, sentence-case headings, path text in every Markdown link, per
[docs/MARKDOWN_STYLE.md](../../MARKDOWN_STYLE.md).

## Verification

1. `pytest tests/test_markdown_links.py` -- every new link resolves and is GitHub-browsable.
2. `pytest tests/test_ascii_compliance.py` -- the plan stays ASCII.
3. `pytest tests/test_source_file_line_limit.py` -- the plan stays under 1000 physical lines; a companion
   review-criteria doc absorbs the overflow if it approaches the limit.
4. Grounding check for E7, run once: `source source_me.sh && bash pipeline/build_generated.sh`, then
   `node --import tsx tools/scene_scale_report.mjs --all`. Confirm per-scene applied scale and
   per-placement boxes are reachable. When they need a new access path, E7 becomes "extend
   `scene_scale_report.mjs` with a per-asset size mode", owned by the integrator.
5. Treat candidate-renderer checks, census reconciliation, compact-frame measurements, exact inventories,
   and screenshot facts as one-time implementation evidence. Record their outcomes in reports and remove
   scratch assertions after capture; do not promote them into Python, Node, or Playwright suites.
6. A permanent test earns residence only when it covers durable product behavior and satisfies every
   applicable item in [docs/PYTEST_STYLE.md](../../PYTEST_STYLE.md), including offline, deterministic,
   refactor-stable setup without test-only fixture files.
   This replacement-wave review also applies
   [tests/TESTS_README.md](../../../tests/TESTS_README.md) and
   [devel/DEVEL_README.md](../../../devel/DEVEL_README.md): gallery links,
   contact sheets, exact asset inventories, visual and grayscale inspections,
   scene captures, and temporary render/capture drivers are one-time evidence.
   No new permanent test, fixture, networked regular test, or `devel/` helper
   is warranted. Retain only existing durable semantic, compiler, and built-app
   runtime tests.
7. Autonomy read-back: each milestone exit names a subagent decision or a measurement, and M6 carries the
   manager default.
8. Read-back: M7 exit reads as a visual judgment on exemplars, and every batch criterion points at the
   kit, a measured floor, or a named evaluator.

## Scope decisions

Each item below is decided rather than deferred.

**In scope, with owners named above**: the floor-shadow signal fix (M0), the counterpart sweep (M2), the
census (M3), boards (M4), candidates and selection (M5-M6), exemplars and kit (M7-M8), family rebuilds
(M9-M11), integration and validation (M12).

**Out of scope, with the reason this version succeeds without each**:

- The dead `object-fit` rule at
  [src/style.css](../../../src/style.css) line 1001: inline
  `<svg>` already holds aspect through `preserveAspectRatio`, and `<img>` sets `object-fit` inline, so
  rendering is correct today and the rule is redundant text.
- The unused `incubator` and `plate_reader` workspace selectors: no scene declares those workspaces, so
  they affect nothing this plan renders or reviews.
- The `layer_recipe_validator` naming: the module works correctly, and renaming it changes no visual
  outcome. Its test's private-helper assertions are a test-suite concern that the rebuild does not touch.
- The `well_plate_96_zoom` quarantine entry: the scene stays out of the rebuild's asset scope either way.
- The sweep-era scripts `refactor_liquid_svg.py`, `svg_identity_sweep.py`, `svg_feature_census.py`: they
  run on request and constrain nothing the rebuild produces.
- Appearance regression tests: the visual standard is the construction kit plus independent review, which
  adapts as the art improves, while pixel, hash, and count assertions would freeze one snapshot and break
  on every intended change.
- The seven protected result composites: their application-UI migration is tracked separately, and their
  bytes are verified at each freeze.
