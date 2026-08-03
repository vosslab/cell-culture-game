# WOW SVG asset quality audit

Status: evidence complete; no production assets, generated files, or runtime code changed.

## Scope and method

This audit follows the ownership boundary in
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md): source art belongs in
`assets/`, while `generated/` and `dist/` are disposable outputs. It checks both
the authored reference chain and three current browser renders. A valid path is
not treated as a valid scientific representation.

| Check | Current result | Interpretation |
| --- | --- | --- |
| Tracked SVG source files | 85 | Current source-art inventory. |
| Object YAML files | 77 | Current authored object inventory. |
| Assets selected by `gen_svg_manifest.py` | 56 used; 29 orphaned | The pipeline has a smaller live asset set than the source tree. |
| Static object asset-reference tests | 10 passed | No `visual_states.asset_name` points to a non-existent SVG. |
| Explicit source placeholder SVGs | 5 files | Three are live manifest placeholders; two are orphan variants. |
| Current sample scene renders | 3/3 populated, all degraded | The renderer still substituted placeholder/degraded items in every sample. |

The 29 orphan count is a reachability signal, not a deletion recommendation.
Some may be planned variants. Do not delete or rename art until the owning
object/state migration is explicit.

## Reference-chain result

The current static asset contract passes: every authored `asset_name` resolves to
an SVG. The failure is at the semantic and emitted-coverage layers.

- `electrophoresis_bench` rendered 16 placements but only 11 real assets;
  `gel_comb`, `power_supply`, and `p10_gel_loading_tip_box` were reported as
  missing objects despite corresponding SVG source files.
- `staining_bench` rendered 10 placements but only 7 real assets; `microwave`
  and `rocking_shaker` were reported as missing objects.
- `heat_block_bench` rendered 13 placements but only 11 real assets;
  `heat_block` and `p10_gel_loading_tip_box` were reported as missing objects.

This is a pipeline/index coverage defect, not a source-file absence claim. It
needs a narrow regression that compares the selected visual-state asset with the
asset actually available to the emitted scene renderer.

The manifest generator identified three live placeholder keys:
`electrode_module`, `gel_opening_tool`, and `kimwipe_pad`. Their source SVGs
contain the placeholder border (`assets/equipment/electrode_module.svg:4`,
`assets/equipment/gel_opening_tool.svg:4`, and
`assets/equipment/kimwipe_pad.svg:4`). Two more placeholder-style source files
are currently orphaned: `microtube_rack_24_placeholder.svg` and
`power_supply_off.svg`.

## Render gallery

The screenshots are current browser-render evidence from the real scene viewer,
not a proof of a biological procedure or of the intended state transition.

| Render | Evidence | What it establishes |
| --- | --- | --- |
| Worst: electrophoresis bench | `test-results/wow_svg_quality/electrophoresis_bench.png` | A dashed electrode-module placeholder is visible; the gel cassette and gel comb are visually conflated; tiny critical tools and large blank regions weaken the protocol's visual sequence. |
| Worst: staining bench | `test-results/wow_svg_quality/staining_bench.png` | A dashed Kimwipe placeholder is visible. Coomassie, destain, and water bottles look materially indistinguishable because all use the same green bottle treatment. |
| Representative: heat-block bench | `test-results/wow_svg_quality/heat_block_bench.png` | The heat block is readable and the rack art is strong, but an instrument state can change without a matching asset change; small tubes and pipettes have weak visual prominence. |

Strong retained art in the sample includes the electrophoresis tank, heat block,
power-supply faceplate, rack, and rocking shaker. Their presence does not offset
incorrect identity or non-visible state changes elsewhere in the same scenes.

## High-confidence quality findings

### Explicit placeholders

- `electrode_module` is a dashed box in the current electrophoresis scene.
  Its state cases all point to that placeholder
  (`content/objects/equipment/electrode_module.yaml:19`).
- `kimwipe_pad` is a dashed box in the staining scene and is also reused for
  `lens_tissue` and `paper_towel_pad`, multiplying the semantic gap.
- `gel_opening_tool` is a live placeholder key. It is visually tiny in the
  electrophoresis render and should not remain a required protocol object with
  generic art.

### Incorrect identity or generic substitution

- A hemocytometer slide renders with the generic `bottle` asset in every
  material state (`content/objects/equipment/hemocytometer_slide.yaml:23`).
  This is scientifically misleading, not merely low polish.
- A label pen also renders as a `bottle` in both states
  (`content/objects/pipette/label_pen.yaml:23`).
- The byte-identical cluster `gel_cassette.svg`, `gel_comb.svg`, and
  `mini_protean_gel.svg` makes distinct electrophoresis objects share one
  visual identity. The current duplicate sweep records that cluster at
  [svg_identity_sweep.md](../../active_plans/audits/svg_identity_sweep.md). In the live scene, the
  cassette/comb pair cannot teach their distinct roles.

### State transitions with no visual teaching cue

Each of these authored states maps both values to the same asset, so a valid
interaction can make no object-level visual change:

- heat-block lid: `content/objects/equipment/heat_block.yaml:27`
- microwave door: `content/objects/equipment/microwave.yaml:27`
- lightbox power: `content/objects/equipment/lightbox.yaml:19`
- rocking-shaker running: `content/objects/equipment/rocking_shaker.yaml:31`
- power-supply running: `content/objects/equipment/power_supply.yaml:27`

This is directly contrary to the visible-flow goal in
[PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md): the learner needs to see what
state changed, not merely receive a completion event.

### Material identity loss

The sample staining scene makes Coomassie, destain, and water appear as the same
green bottle. The authored mappings confirm that multiple chemically distinct
bottles select `bottle_green`, for example
`content/objects/bottle/coomassie_stain_bottle.yaml:25` and
`content/objects/bottle/destain_bottle.yaml:25`. The existing
[material_render.md](../../active_plans/reports/material_render.md) independently records the
runtime's grey fallback and full-bbox fill problem. Asset replacement alone
cannot fix that renderer-owned material defect.

## Top ten actions

| Rank | Action | Why it is high leverage | Representative evidence |
| --- | --- | --- | --- |
| 1 | Repair emitted-scene asset coverage and add a selected-state-to-rendered-asset regression. | Current source references pass, yet three sampled scenes still substitute seven object types. This blocks confidence in every visual improvement. | All three gallery renders. |
| 2 | Replace the electrode module with normalized, distinct electrophoresis hardware art. | It is a visible placeholder in the core SDS-PAGE workflow. | Electrophoresis screenshot; `electrode_module.yaml:19`. |
| 3 | Split gel cassette, gel comb, and Mini-PROTEAN gel into distinct scientific illustrations. | Three separate actions currently have the same byte-identical art, defeating recognition and sequencing. | `svg_identity_sweep.md:26`. |
| 4 | Replace the bottle used as a hemocytometer slide with a slide/chamber asset and material-region anchors. | It actively teaches the wrong physical object in a cell-counting workflow. | `hemocytometer_slide.yaml:23`. |
| 5 | Restore material color and interior clipping in the renderer before adding bottle variants. | The current pipeline hides liquid identity and paints the whole item bbox; blue Coomassie cannot read as blue. | `material_render.md` and staining screenshot. |
| 6 | Create paired open/closed and off/on asset states for heat block, microwave, lightbox, shaker, and power supply. | Five high-frequency interactions presently provide no visual state evidence. | YAML paths in state-transition section. |
| 7 | Replace the Kimwipe and gel-opening-tool placeholders and stop reusing one tissue placeholder for three objects. | These are obvious unfinished elements in visible protocols. | `assets/equipment/*` placeholder sources. |
| 8 | Give label pen a pen asset and reclassify its art ownership if needed. | A bottle substitute damages basic object recognition during authoring/labeling steps. | `label_pen.yaml:23`. |
| 9 | Differentiate gel-loading-tip boxes from generic tip boxes and validate their rendered scale. | The SDS-PAGE scene makes the tiny critical loading component difficult to recognize. | Electrophoresis and heat-block screenshots. |
| 10 | Perform a focused scale/readability pass for thin pipettes, tiny tubes, and required small tools after identity fixes. | Correct art still fails if a student cannot identify it at scene scale. | Gallery renders; no crop claim is made. |

## Verification record

```bash
source source_me.sh && python3 -m pytest tests/test_object_asset_refs.py \
  tests/test_svg_manifest_predicate.py -q
# 10 passed in 0.14s

source source_me.sh && python3 pipeline/gen_svg_manifest.py
# Found 85 SVG files; generated 56 live entries; dropped 29 orphans;
# derived DOM-SVG for 30 assets; flagged 3 placeholder keys.

node tools/scene_to_png.mjs --scene electrophoresis_bench --png \
  --out test-results/wow_svg_quality/electrophoresis_bench.png \
  --missing-svg placeholder
# 16 placements; 11 real; 5 placeholders; degraded.
```

The renderer command required the normal browser permission outside the sandbox.
No semantic claim in this audit is based only on a screenshot. Static source and
YAML evidence is stated separately from visual observations.

## Residual risk

- The three screenshots cover representative weak and mixed-quality scenes, not
  every protocol state or viewport.
- The existing identity sweep is a useful duplicate lead, not proof that every
  duplicate is a bug. The gel trio is prioritized because its object names and
  protocol roles are distinct.
- The static reference test cannot detect an emitted-manifest/index mismatch;
  that gap is the first proposed regression.
