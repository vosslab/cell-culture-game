# Scene metric calibration set

Provisional calibration set for the scene composition metrics (focal detection,
grouping, survivors, and the bbox scorecard candidates). New or refined metrics
must be validated against human aesthetic judgment, not against their own
formulas. This doc is that reference: a small labeled set of real rendered
scenes, each carrying a plain-language judgment, the render path, an evidence
citation, and an expected relative ranking.

- Ship status: provisional. Ratification is a one-time human flip of the status
  line below from `provisional` to `ratified`. That flip does NOT block the
  downstream metric work (M3-M6); those milestones proceed against this set
  while it is provisional.
- Status: provisional.

## How judgments are grounded

Every judgment is grounded in the round-0 vision review recorded in
[../../archive/reports/aesthetic_baseline_round0.md](../../archive/reports/aesthetic_baseline_round0.md),
which scored eight rendered scenes 1 (worst) to 5 (best) and attached failure
tags, strong points, and blocking findings per scene. Each row below cites that
scene's round-0 scores and tags; no verdict is invented here.

Judgment labels are drawn from this closed set:

- `correct focal` -- one clear primary object the eye lands on first.
- `weak focal` -- no clear primary, or the primary competes with peers.
- `good grouping` -- related objects cluster so the grouping reads as intentional.
- `weak grouping` -- objects scattered or duplicated with no spatial logic.
- `cluttered` -- too many objects for the space; visually overwhelming.
- `too sparse` -- a dead region dominates; content only at the rim.
- `acceptable` -- no blocking composition defect on that axis.

A scene carries one focal label and one grouping label (the two coverage-floor
axes), plus an optional canvas label (`cluttered`, `too sparse`, or
`acceptable`) when the round-0 tags call for it.

## Render paths and their volatility

The `png_path` column records the render each judgment maps to, using the
round-0 render batch path (`test-results/m7_after/<scene>.png`). These paths are
gitignored build artifacts, not tracked files, so they are recorded as plain
text rather than Markdown image links (an untracked link would 404 on
github.com and fail the repo link check). Regenerate the render batch before
opening a path. The six base-scene benches also emit to
`test-results/generalization/<scene>.png`; those renders were spot-checked
against round-0 during authoring (see Residual risks).

## Calibration set

Eight real scenes span the full round-0 verdict range (one clear, five
needs_review, two weak), giving both coverage-floor axes a high anchor, a low
anchor, and a populated middle. Rank 1 is best, rank 8 is worst.

| rank | scene | png_path | focal label | grouping label | canvas label | round-0 evidence (scores; tags) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | passage_hood_detachment_microscope_view | `test-results/m7_after/passage_hood_detachment_microscope_view.png` | correct focal | good grouping | acceptable | focal 5, grouping 4, balance 4; overall clear, no blocking findings |
| 2 | staining_bench | `test-results/m7_after/staining_bench.png` | correct focal | good grouping | acceptable | focal 4, grouping 3, balance 4; tags ambiguous_label |
| 3 | cell_counter_basic | `test-results/m7_after/cell_counter_basic.png` | correct focal | weak grouping | too sparse | focal 4, grouping 3; tags over_sparse_canvas, weak_workflow_grouping |
| 4 | heat_block_bench | `test-results/m7_after/heat_block_bench.png` | weak focal | weak grouping | acceptable | focal 3, grouping 3, balance 4; tags weak_focal, weak_workflow_grouping |
| 5 | hood_basic | `test-results/m7_after/hood_basic.png` | weak focal | weak grouping | too sparse | focal 3, grouping 3; tags over_sparse_canvas, scale_mismatch, ambiguous_label |
| 6 | seeding_workspace | `test-results/m7_after/seeding_workspace.png` | weak focal | weak grouping | too sparse | focal 3, grouping 3, balance 4; tags ambiguous_label, over_sparse_canvas |
| 7 | sample_prep_bench | `test-results/m7_after/sample_prep_bench.png` | weak focal | weak grouping | cluttered | focal 2, grouping 2; tags weak_focal, weak_workflow_grouping, cognitive_overload |
| 8 | electrophoresis_bench | `test-results/m7_after/electrophoresis_bench.png` | weak focal | weak grouping | too sparse | focal 2, grouping 2; tags weak_focal, lopsided_balance, over_sparse_canvas, placeholder_asset |

## Per-scene judgments and evidence

Each entry states the plain-language judgment and the round-0 evidence it rests
on.

### 1. passage_hood_detachment_microscope_view (correct focal, good grouping)

- Correct focal: round-0 scored focal_dominance 5 and recorded "Microscope is
  large, centered, high-contrast: textbook focal dominance, the eye lands on it
  immediately." This is the high anchor for focal.
- Good grouping: round-0 scored instructional_grouping 4 and recorded
  "Supporting objects (rack, suspension, T75 flask, hemocytometer, ethanol) sit
  around the microscope in a believable cluster." High anchor for grouping.
- Acceptable canvas: round-0 overall verdict was clear with no blocking findings.

### 2. staining_bench (correct focal, good grouping)

- Correct focal: round-0 scored focal_dominance 4 and recorded "Microwave is a
  strong central focal object, well centered in the lower band."
- Good grouping: round-0 recorded "Reagent bottles paired with their
  recycle/waste partners (stain+recycle, destain+waste) reads as intentional
  grouping." The numeric grouping score was 3 because the broader staining
  workflow (tray, shaker, waste) is not yet clustered; the local reagent pairing
  is the good-grouping evidence.

### 3. cell_counter_basic (correct focal, weak grouping, too sparse)

- Correct focal: round-0 scored focal_dominance 4 and recorded "Automated cell
  counter instrument with lit display dominates the lower band."
- Weak grouping: round-0 scored grouping 3 with tag weak_workflow_grouping; the
  consumables are not pulled toward the counter to imply the count workflow.
- Too sparse: round-0 tag over_sparse_canvas, "Large empty horizontal void
  between the top row and the bottom row splits the canvas into two disconnected
  shelves."

### 4. heat_block_bench (weak focal, weak grouping, acceptable)

- Weak focal: round-0 scored focal_dominance 3 with tag weak_focal, "Heat block
  is not visually dominant enough relative to the racks given it is the teaching
  instrument."
- Weak grouping: round-0 scored grouping 3 with tag weak_workflow_grouping; a
  duplicate 24-slot rack appears in two bands with no obvious workflow reason.
- Acceptable canvas: round-0 recorded "Even three-band layout with good
  left-right balance" and scored canvas_balance 4, so the canvas itself is fine
  even though focal and grouping are weak.

### 5. hood_basic (weak focal, weak grouping, too sparse)

- Weak focal: round-0 scored focal_dominance 3; the 96-well plate draws the eye
  but an empty "BSC workspace" zone and a dwarfed aspirating pipette keep any
  object from clearly winning.
- Weak grouping: round-0 scored grouping 3; objects are readable but not
  organized into workflow steps.
- Too sparse: round-0 tag over_sparse_canvas, "The 'BSC workspace' label sits
  under a large empty gap with no visible object."

### 6. seeding_workspace (weak focal, weak grouping, too sparse)

- Weak focal: round-0 scored focal_dominance 3; two instrument anchors
  (incubator, vortex) split attention so no single object dominates.
- Weak grouping: round-0 scored grouping 3; the reagent row pairs cleanly but
  the bottom-left trio is crowded and a "BSC workspace" label is orphaned.
- Too sparse: round-0 tag over_sparse_canvas, "'BSC workspace' label again
  anchors to empty space in the middle band."

### 7. sample_prep_bench (weak focal, weak grouping, cluttered)

- Weak focal: round-0 scored focal_dominance 2 with tag weak_focal, "No single
  dominant teaching object; the scene reads as a packer-dump of small similar
  tubes/bottles in three loose rows." Low anchor for focal.
- Weak grouping: round-0 scored grouping 2 with tag weak_workflow_grouping,
  "Duplicate objects appear twice ... with no spatial logic, reading as scatter
  rather than workflow." Low anchor for grouping.
- Cluttered: round-0 tag cognitive_overload from three loose rows of duplicated
  small items.

### 8. electrophoresis_bench (weak focal, weak grouping, too sparse)

- Weak focal: round-0 scored focal_dominance 2 with tags weak_focal and
  lopsided_balance, "the electrophoresis tank floats alone in a large void."
  Low anchor for focal.
- Weak grouping: round-0 scored grouping 2 with tag weak_workflow_grouping,
  "Workflow items are scattered to far corners ... with no clustering." Low
  anchor for grouping.
- Too sparse: round-0 tag over_sparse_canvas, "Massive empty center."
- Render bug: round-0 flagged a placeholder "Electrode module" dashed box
  (placeholder_asset). That is routed to the render-bug owner and is not part of
  the metric calibration. It was still present in the current render at
  authoring time.

## Coverage floor

The floor requires at least four scenes carrying a focal judgment (mix of
correct and weak) and at least four carrying a grouping judgment (mix of good and
weak). All eight scenes carry both, so both floors are met with margin.

- Focal judgments: 8 scenes. Correct focal: 3
  (passage_hood_detachment_microscope_view, staining_bench, cell_counter_basic).
  Weak focal: 5 (heat_block_bench, hood_basic, seeding_workspace,
  sample_prep_bench, electrophoresis_bench). Floor of 4 met; mix present.
- Grouping judgments: 8 scenes. Good grouping: 2
  (passage_hood_detachment_microscope_view, staining_bench). Weak grouping: 6
  (cell_counter_basic, heat_block_bench, hood_basic, seeding_workspace,
  sample_prep_bench, electrophoresis_bench). Floor of 4 met; mix present.

## Expected relative ranking

A calibrated metric should rank these scenes roughly best-to-worst as below,
grounded in the round-0 overall verdicts and scores. The ranking is ordinal, not
a numeric target.

1. passage_hood_detachment_microscope_view -- only clear verdict; strongest
   focal and grouping.
2. staining_bench -- strong central focal, intentional local reagent pairing.
3. cell_counter_basic -- strong focal, but a mid-canvas void splits the frame.
4. heat_block_bench -- balanced canvas, but weak focal and a duplicated rack.
5. hood_basic -- competing focal plus an orphan label over empty space.
6. seeding_workspace -- split focal, crowded trio, and an orphan label.
7. sample_prep_bench -- weak verdict; no focal, duplicated scatter, cluttered.
8. electrophoresis_bench -- weak verdict; lone tank in a void plus a placeholder
   render bug.

Anchors for metric checks: a `focal_dominance` metric should place
passage_hood_detachment_microscope_view at the top and
sample_prep_bench/electrophoresis_bench at the bottom; an
`instructional_grouping` metric should do the same, with staining_bench reading
as good local grouping.

## Status and next steps

- Provisional. Downstream metric work (M3-M6) uses this set to check whether a
  new metric tracks the plain-language judgment before that metric is promoted to
  a gate, per the calibration loop in
  [aesthetic_review_metrics.md](aesthetic_review_metrics.md) and the API-reviewer
  calibration in
  [ai_polish_review_calibration.md](ai_polish_review_calibration.md).
- Ratification: a human flips the status line from `provisional` to `ratified`
  after confirming the labels. That flip is a one-time approval and does not
  block M3-M6.
- Refresh after any milestone that changes visual output: regenerate the render
  batch, re-review with the same prompts, and update the table and judgments.

## Residual risks

- Render volatility. The `test-results/` render tree is a gitignored build
  artifact regenerated by the render and clean-build steps; during authoring the
  `test-results/generalization/` directory was cleared mid-task. The judgments
  here are pegged to the durable round-0 report, not to a live PNG. A durable
  tracked gallery would let this doc embed images directly; committing one is a
  human follow-up, appropriate at ratification.
- Render-batch drift. Before the generalization renders were cleared,
  electrophoresis_bench and sample_prep_bench were viewed and confirmed to match
  their round-0 descriptions (central void plus placeholder box; duplicated-rack
  dump). A separate rack-identity render of
  passage_hood_detachment_microscope_view showed a left-shifted variant with
  weaker grouping than round-0, so that scene in particular needs a fresh
  canonical render before its good-grouping label is re-confirmed.
- Two scenes need a fresh render to view. seeding_workspace and
  passage_hood_detachment_microscope_view are not emitted by the base-scene
  generalization step; regenerate the m7 after-render batch to view them.
