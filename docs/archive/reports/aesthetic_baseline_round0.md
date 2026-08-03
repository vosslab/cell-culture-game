# Aesthetic baseline round 0

Claude vision review of 8 rendered lab scenes (after-screenshots in
`test-results/m7_after/`). Round 0 establishes the aesthetic baseline. Scores
are 1 (bad) to 5 (excellent). This is read-only analysis; no code, engine, or
tools changes were made.

## Per-scene findings (JSON)

### cell_counter_basic

```json
{
  "scene": "cell_counter_basic",
  "overall": "needs_review",
  "scores": {
    "focal_dominance": 4,
    "label_association_clarity": 4,
    "bench_plausibility": 2,
    "instructional_grouping": 3,
    "grounding": 2,
    "canvas_balance": 3,
    "scale_plausibility": 3,
    "cognitive_load": 4,
    "whitespace_quality": 2,
    "typography": 4,
    "asset_finish": 4
  },
  "strong_points": [
    "Automated cell counter instrument with lit display dominates the lower band as the clear teaching object.",
    "Live readout (Cell Count 8.50e5, Viability 92.1%) reads cleanly with no leaked debug text.",
    "Only seven objects, low cognitive load."
  ],
  "blocking_findings": [
    "Large empty horizontal void between the top row and the bottom row splits the canvas into two disconnected shelves.",
    "Objects float as stickers with no surface or grounding shadow."
  ],
  "failure_tags": ["over_sparse_canvas", "floating_assets", "weak_workflow_grouping"],
  "suggested_layout_actions": [
    "Pull the top row (slide cartridge, Trypan Blue, cell suspension) down toward the instrument to close the mid-canvas void.",
    "Cluster the consumables (microtube rack, tip box, hemocytometer slide) nearer the counter to imply the count workflow.",
    "Tighten vertical whitespace so the two bands feel like one bench, not two shelves."
  ],
  "suggested_asset_actions": [],
  "render_bugs": []
}
```

### staining_bench

```json
{
  "scene": "staining_bench",
  "overall": "needs_review",
  "scores": {
    "focal_dominance": 4,
    "label_association_clarity": 3,
    "bench_plausibility": 3,
    "instructional_grouping": 3,
    "grounding": 2,
    "canvas_balance": 4,
    "scale_plausibility": 3,
    "cognitive_load": 3,
    "whitespace_quality": 3,
    "typography": 3,
    "asset_finish": 4
  },
  "strong_points": [
    "Microwave is a strong central focal object, well centered in the lower band.",
    "Reagent bottles paired with their recycle/waste partners (stain+recycle, destain+waste) reads as intentional grouping.",
    "Even left-to-right weight across the top reagent row."
  ],
  "blocking_findings": [
    "Two-word labels under tightly paired bottles ('Coomassie stain' vs 'Coomassie recycle bottle') sit close enough that association is briefly ambiguous.",
    "All objects float; no surface line or shadow."
  ],
  "failure_tags": ["ambiguous_label", "floating_assets"],
  "suggested_layout_actions": [
    "Increase horizontal gap between each reagent and its partner so each label clearly owns one bottle.",
    "Group staining tray + rocking shaker + waste closer (they share the staining workflow) and keep the microwave as the centerpiece."
  ],
  "suggested_asset_actions": [],
  "render_bugs": []
}
```

### sample_prep_bench

```json
{
  "scene": "sample_prep_bench",
  "overall": "weak",
  "scores": {
    "focal_dominance": 2,
    "label_association_clarity": 3,
    "bench_plausibility": 2,
    "instructional_grouping": 2,
    "grounding": 2,
    "canvas_balance": 3,
    "scale_plausibility": 2,
    "cognitive_load": 2,
    "whitespace_quality": 3,
    "typography": 3,
    "asset_finish": 3
  },
  "strong_points": [
    "ddH2O bottle gives one anchor of visual weight in the top row.",
    "Color-coded microtube racks are visually distinctive."
  ],
  "blocking_findings": [
    "No single dominant teaching object; the scene reads as a packer-dump of small similar tubes/bottles in three loose rows.",
    "Duplicate objects appear twice (two 'Microtube rack (24-slot)', two 'Laemmli 4x', two tip boxes) with no spatial logic, reading as scatter rather than workflow.",
    "Tiny tubes vs large ddH2O bottle create a jarring scale spread; small items get lost.",
    "Objects float with no grounding."
  ],
  "failure_tags": ["weak_focal", "weak_workflow_grouping", "scale_mismatch", "floating_assets", "cognitive_overload"],
  "suggested_layout_actions": [
    "Cluster the duplicated racks/reagents into one workflow group instead of mirroring them across rows.",
    "Promote one object (e.g. the rack being filled) to a larger central focal position.",
    "Normalize the scale band so the smallest tubes are not dwarfed by the ddH2O bottle.",
    "Reduce row count from three loose rows to a tighter clustered bench."
  ],
  "suggested_asset_actions": [
    "HUMAN: confirm whether the duplicate racks/reagents are intentional (two physical racks) or an authoring duplication; if duplicates are intended, they still need a grouping rationale."
  ],
  "render_bugs": []
}
```

### hood_basic

```json
{
  "scene": "hood_basic",
  "overall": "needs_review",
  "scores": {
    "focal_dominance": 3,
    "label_association_clarity": 4,
    "bench_plausibility": 3,
    "instructional_grouping": 3,
    "grounding": 2,
    "canvas_balance": 3,
    "scale_plausibility": 2,
    "cognitive_load": 3,
    "whitespace_quality": 3,
    "typography": 4,
    "asset_finish": 4
  },
  "strong_points": [
    "96-well plate is colorful and draws the eye as the work surface.",
    "Top reagent row is evenly spaced with clear one-to-one labels.",
    "Serological pipette on the far right adds vertical variety."
  ],
  "blocking_findings": [
    "The 'BSC workspace' label sits under a large empty gap with no visible object, so the label has no anchor.",
    "Aspirating pipette (a thin small swab-like asset) is dwarfed by the 96-well plate, reading as a scale mismatch.",
    "Objects float as stickers."
  ],
  "failure_tags": ["over_sparse_canvas", "scale_mismatch", "floating_assets", "ambiguous_label"],
  "suggested_layout_actions": [
    "Place the 96-well plate (the work surface) more centrally and let it be the clear focal anchor.",
    "Resolve the empty 'BSC workspace' zone: either place its object there or pull neighbors in to remove the void.",
    "Re-scale the aspirating pipette up so it does not vanish next to the plate."
  ],
  "suggested_asset_actions": [
    "HUMAN: the aspirating pipette asset reads as a tiny swab; confirm it is the intended asset and sized appropriately."
  ],
  "render_bugs": []
}
```

### seeding_workspace

```json
{
  "scene": "seeding_workspace",
  "overall": "needs_review",
  "scores": {
    "focal_dominance": 3,
    "label_association_clarity": 3,
    "bench_plausibility": 3,
    "instructional_grouping": 3,
    "grounding": 2,
    "canvas_balance": 4,
    "scale_plausibility": 3,
    "cognitive_load": 3,
    "whitespace_quality": 3,
    "typography": 3,
    "asset_finish": 4
  },
  "strong_points": [
    "Incubator (top right) and vortex (bottom) give two strong instrument anchors.",
    "Reagent row reads cleanly with paired media/PBS/waste.",
    "96-well plate adds color interest in the lower band."
  ],
  "blocking_findings": [
    "Bottom-left cluster ('Cell suspension', 'Conical 15 ml tube', 'Micropipette') is crowded and the three labels sit close together, briefly ambiguous about which tiny asset each names.",
    "'BSC workspace' label again anchors to empty space in the middle band.",
    "Objects float."
  ],
  "failure_tags": ["ambiguous_label", "over_sparse_canvas", "floating_assets"],
  "suggested_layout_actions": [
    "Spread the crowded bottom-left trio horizontally so each small asset clearly owns its label.",
    "Fill or remove the empty 'BSC workspace' middle zone.",
    "Balance the dead center by nudging the vortex/plate group leftward toward the empty mid-band."
  ],
  "suggested_asset_actions": [],
  "render_bugs": []
}
```

### electrophoresis_bench

```json
{
  "scene": "electrophoresis_bench",
  "overall": "weak",
  "scores": {
    "focal_dominance": 2,
    "label_association_clarity": 2,
    "bench_plausibility": 2,
    "instructional_grouping": 2,
    "grounding": 1,
    "canvas_balance": 2,
    "scale_plausibility": 3,
    "cognitive_load": 2,
    "whitespace_quality": 2,
    "typography": 2,
    "asset_finish": 2
  },
  "strong_points": [
    "Electrophoresis tank and green buffer bottles are individually well-drawn assets.",
    "Power supply shows a clean lit '300 V' readout."
  ],
  "blocking_findings": [
    "Massive empty center: the electrophoresis tank floats alone in a large void with huge dead zones all around, severe lopsided balance and over-sparse canvas.",
    "PLACEHOLDER: 'Electrode module' is a dashed empty rectangle (unfinished/placeholder asset) leaking into the render.",
    "Label collisions/awkward wraps in the top-left cluster: 'Protein ladder tube', 'Buffer recycle bottle' and 'Running buffer 10x' labels overlap and wrap so each label is hard to tie to its bottle.",
    "Objects sit on no surface; the lone tiny ladder tube floats between two large bottles.",
    "Workflow items are scattered to far corners (gel cassette + comb + tip box on the right, buffers far left) with no clustering."
  ],
  "failure_tags": ["placeholder_asset", "weak_focal", "ambiguous_label", "awkward_wrap", "over_sparse_canvas", "lopsided_balance", "floating_assets", "weak_workflow_grouping"],
  "suggested_layout_actions": [
    "Collapse the large central void: bring the tank, power supply, and gel cassette into one tighter electrophoresis-run cluster.",
    "Resolve top-left label overlaps by widening horizontal spacing between the running buffer / ladder tube / recycle bottle so labels stop wrapping into each other.",
    "Cluster gel-prep items (cassette, comb, gel loading tip box, micropipette) together rather than splitting them across right and bottom.",
    "Distribute weight so the canvas is not empty in the center with content only at the rim."
  ],
  "suggested_asset_actions": [
    "HUMAN: 'Electrode module' is rendering as a dashed placeholder box. Supply/normalize the real SVG asset before this scene can pass."
  ],
  "render_bugs": [
    "Placeholder dashed-box asset ('Electrode module') leaking into the render.",
    "Overlapping/wrapping labels in the top-left bottle cluster."
  ]
}
```

### heat_block_bench

```json
{
  "scene": "heat_block_bench",
  "overall": "needs_review",
  "scores": {
    "focal_dominance": 3,
    "label_association_clarity": 4,
    "bench_plausibility": 3,
    "instructional_grouping": 3,
    "grounding": 2,
    "canvas_balance": 4,
    "scale_plausibility": 3,
    "cognitive_load": 3,
    "whitespace_quality": 3,
    "typography": 4,
    "asset_finish": 4
  },
  "strong_points": [
    "Heat block (lower center, '95 C' readout) and the two loaded microtube racks make clear instrument/sample anchors.",
    "Even three-band layout with good left-right balance.",
    "Clean one-to-one labels with no overlaps."
  ],
  "blocking_findings": [
    "Duplicate 'Microtube rack (24-slot)' appears twice (top band and bottom band) without an obvious workflow reason, reading as repetition.",
    "Heat block is not visually dominant enough relative to the racks given it is the teaching instrument.",
    "Objects float."
  ],
  "failure_tags": ["weak_focal", "weak_workflow_grouping", "floating_assets"],
  "suggested_layout_actions": [
    "Promote the heat block to a larger/more central focal position so the teaching instrument dominates.",
    "Cluster the heat block with the microtube rack it heats to show the workflow, instead of separating racks across two bands.",
    "If two racks are intentional, place them adjacent so the pairing reads as before/after."
  ],
  "suggested_asset_actions": [
    "HUMAN: confirm whether the two microtube racks are intentional (before/after) or an authoring duplicate."
  ],
  "render_bugs": []
}
```

### passage_hood_detachment_microscope_view

```json
{
  "scene": "passage_hood_detachment_microscope_view",
  "overall": "clear",
  "scores": {
    "focal_dominance": 5,
    "label_association_clarity": 4,
    "bench_plausibility": 3,
    "instructional_grouping": 4,
    "grounding": 3,
    "canvas_balance": 4,
    "scale_plausibility": 4,
    "cognitive_load": 4,
    "whitespace_quality": 4,
    "typography": 4,
    "asset_finish": 4
  },
  "strong_points": [
    "Microscope is large, centered, high-contrast: textbook focal dominance, the eye lands on it immediately.",
    "Supporting objects (rack, suspension, T75 flask, hemocytometer, ethanol) sit around the microscope in a believable cluster.",
    "Good canvas balance with content in all quadrants and comfortable whitespace.",
    "Clean labels, low cognitive load, no leaked debug text or placeholders."
  ],
  "blocking_findings": [],
  "failure_tags": ["floating_assets"],
  "suggested_layout_actions": [
    "Minor: add a light grounding/shadow so the supporting assets sit on the bench rather than float."
  ],
  "suggested_asset_actions": [],
  "render_bugs": []
}
```

## Ranked engine-ownable layout actions (most impactful first)

These are placement/scale/balance/grouping/label-position/whitespace actions the
layout engine can own. Ordered by cross-scene impact.

1. **Collapse mid-canvas voids and rim-only layouts into tighter clusters.**
   - Helps: electrophoresis_bench (severe), cell_counter_basic, hood_basic,
     seeding_workspace.
   - Lifts: whitespace_quality, canvas_balance, bench_plausibility,
     instructional_grouping.
   - Feasibility: medium. The engine controls placement; the rule is "pack
     workflow objects toward a center of mass and shrink empty bands," but it
     needs a grouping signal to know what clusters.

2. **Add a focal-promotion pass: scale up / center the primary teaching object.**
   - Helps: sample_prep_bench, electrophoresis_bench, heat_block_bench, hood_basic.
   - Lifts: focal_dominance, cognitive_load.
   - Feasibility: medium. Engine can scale and center if the protocol/scene
     declares which object is primary; needs that designation as input.

3. **Spacing pass to disambiguate labels under tightly paired/crowded objects.**
   - Helps: staining_bench, electrophoresis_bench (label overlap/wrap),
     seeding_workspace, sample_prep_bench.
   - Lifts: label_association_clarity, typography (reduces awkward wraps).
   - Feasibility: easy/medium. Increase minimum horizontal gap as a function of
     label width so two-word labels do not collide or wrap into neighbors.

4. **Cluster workflow-related objects (reagent+waste, instrument+its sample).**
   - Helps: sample_prep_bench, electrophoresis_bench, heat_block_bench,
     cell_counter_basic.
   - Lifts: instructional_grouping, bench_plausibility.
   - Feasibility: hard. Requires the engine to consume a workflow/grouping hint;
     pure geometry cannot infer pairing.

5. **Resolve labels anchored to empty zones (e.g. 'BSC workspace').**
   - Helps: hood_basic, seeding_workspace.
   - Lifts: label_association_clarity, over_sparse_canvas, canvas_balance.
   - Feasibility: medium. Engine should not emit a label with no rendered object
     under it; either place the object or suppress the orphan label slot.

6. **Add light grounding (surface line / soft shadow) so assets sit on a bench.**
   - Helps: ALL 8 scenes (every scene tagged floating_assets).
   - Lifts: grounding, bench_plausibility.
   - Feasibility: medium. A per-object drop shadow or a shared bench baseline is
     an engine render-layer concern, not an asset change.

7. **Normalize relative scale bands so tiny tubes are not dwarfed by large bottles/plates.**
   - Helps: sample_prep_bench, hood_basic.
   - Lifts: scale_plausibility, cognitive_load.
   - Feasibility: medium. Engine can clamp a min on-canvas size for small assets,
     but true believable scale may need per-asset size hints.

## Asset / author actions (route to human, not the engine)

- electrophoresis_bench: 'Electrode module' renders as a dashed placeholder box.
  A real, normalized SVG asset is needed.
- hood_basic: aspirating pipette asset reads as a tiny swab; confirm it is the
  intended asset and appropriately sized.
- sample_prep_bench: duplicate racks/reagents ('Microtube rack (24-slot)' x2,
  'Laemmli 4x' x2, tip box x2). Confirm intentional vs authoring duplication.
- heat_block_bench: duplicate 'Microtube rack (24-slot)' x2. Confirm intentional
  (before/after) vs duplication.

## Render bugs found

- **placeholder_asset / debug-leak:** electrophoresis_bench 'Electrode module'
  dashed empty rectangle leaking into the render (1).
- **awkward_wrap / overlapping labels:** electrophoresis_bench top-left bottle
  cluster ('Running buffer 10x' / 'Protein ladder tube' / 'Buffer recycle
  bottle') overlap and wrap (1).

Total render-bug findings: 2 (1 placeholder asset, 1 label overlap/wrap). No
leaked numeric debug/status text was found; the lit instrument readouts
(cell counter, power supply '300 V', heat block '95 C') are intended display
state, not debug leakage.
