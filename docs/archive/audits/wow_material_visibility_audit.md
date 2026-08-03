# Material-state visibility audit

Status: superseded by the current protocol-host material evidence.

## Current follow-up

The modular material path is now implemented and exercised through the real
protocol host. The current capture covers all 31 emitted protocols and records
702 initial-scene material surfaces:

- 110 SVG-anchor surfaces for whole objects;
- 592 structured-subpart surfaces, primarily individual wells;
- 42 initially visible colored surfaces;
- 660 intentionally empty or transparent initial surfaces.

The verified baseline reports 702 unchanged, zero regressed, zero new, and zero
missing surfaces. Every current surface uses either the normalized SVG-anchor
contract or structured-subpart geometry; the old full-item HTML bbox overlay is
not part of this corpus. See [material_render.md](../../active_plans/reports/material_render.md)
for the generated evidence and
`source source_me.sh && python3 tests/e2e/e2e_material_render.py` for the
verification command.

This remains an initial-scene regression measurement, not a claim that a static
capture proves every post-interaction transition. The visible protocol walkers
remain the evidence for authored state changes during student actions.

## Historical scope and result

This audit rechecks the live claims in
[material_render.md](../../active_plans/reports/material_render.md) without changing source,
content, generated data, specs, or that report. It separates the diagnostic
scene viewer's object-level fill behavior from the protocol-host and structured
subpart paths.

Historical status: confirmed material-visibility defects at the old
object-level render seam; the well-plate subpart renderer was the functioning
contrasting path.

## Evidence captured

- Capture: `test-results/wow_material_visibility/current_capture/capture.json`
- Screenshots: 112 PNG files under
  `test-results/wow_material_visibility/current_capture/`
- Representative before/after pairs:
  - `bench_basic.png` and `bench_basic.nofill_material_volume.png`
  - `plate_workspace.png` and `plate_workspace.nofill_material_volume.png`
  - `sdspage_fill_tank_buffer_workspace.png` and
    `sdspage_fill_tank_buffer_workspace.nofill_material_volume.png`
- Structured-well browser evidence produced by the existing acceptance test:
  `test-results/subpart_render/before_writes.png` and
  `test-results/subpart_render/after_writes.png`

The object-level capture loaded every emitted scene through
`dist/scene_viewer.html?scene=<scene>`. That viewer deliberately has no active
protocol material registry. The capture is therefore direct evidence of the
diagnostic viewer and the shared object-fill geometry, not proof that every
protocol-host render lacks a registry.

## Current hypothesis results

| Hypothesis | Current result | Evidence and qualification |
| --- | --- | --- |
| Object fill overlays cover the whole item bbox rather than liquid interior geometry. | CONFIRMED | `scene_item.tsx` renders each fill as an absolutely positioned `left: 0`, `bottom: 0`, `width: 100%` rectangle. It has no SVG clip path, anchor, or internal liquid bounds. This is structural evidence, not a claim that the diff percentage is a liquid-volume measurement. |
| Distinct top-level material identities appear as the neutral fallback in relevant rendered scenes. | CONFIRMED for the diagnostic scene viewer. | The new capture found 231 of 231 `[data-overlay="fill"]` elements across 34 emitted scenes with computed `rgba(120, 120, 120, 0.35)`. Examples include PBS, ethanol, media, running buffer, protein ladder, and tank chambers. |
| The old report's grey result proves that the protocol host never resolves material identity colors. | NOT CONFIRMED; report wording is too broad. | `scene_viewer` calls `renderScene`, which intentionally creates its store and renderer with `materialRegistry: null`. The protocol host instead passes `PROTOCOL_MATERIALS[protocol_name]`. A host-path, stateful object-level capture is still needed before making a universal claim. |
| Initial full bottles nevertheless lack their declared material identity by default. | CONFIRMED by source-path analysis; NEEDS_CONTEXT for a protocol screenshot. | Object schemas such as `pbs_bottle` and `ethanol_bottle` default `material_name` to `empty` while `material_volume` defaults to 500. The store seeds schema defaults. Null material color then deliberately selects the grey fill fallback. This explains the diagnostic capture and is likely to persist until a protocol writes the identity field. |
| Structured well colors behave differently. | CONFIRMED. | The production-path well-plate browser test rendered 96 shapes and, after normal store writes, observed `A1=#686868`, `A2=transparent`, `H1=#686868`, `D6=#a719db`, and `H12=transparent`, with no page errors. Thus registry-backed per-well color and spatial correspondence work. |

## What remains true or stale in the prior report

- Current and confirmed: the 34-scene, 231-overlay diagnostic corpus and grey
  fallback are still reproducible.
- Current and confirmed: the object-level fill shape remains a bottom-anchored
  full-width rectangle, so it cannot follow bottle, tube, flask, or tank
  interiors.
- Overstated: "the renderer is not showing PBS as PBS" is accurate for this
  diagnostic viewer and for default-empty object state, but does not establish
  that a protocol-host render after an identity write fails. The protocol host
  has a registry path the diagnostic viewer intentionally omits.
- Not remeasured here: the exact percentage baseline and its regression status.
  The existing end-to-end script would rewrite the owned report artifact, which
  was outside this audit's authorized scope. The before/after images are a
  coarse overlay-footprint proxy only, not a liquid-volume or interior-shape
  correctness oracle.

## Ranked implementation seams

1. **Object material initialization** -- `create_scene_store` seeds
   `material_name: empty` even for semantically prefilled source containers.
   Establish a closed, authored way for a placement/object's initial material
   identity to match its initial volume. This needs a contract/spec decision;
   do not work around it with label-based inference or an open scene override.
2. **Object liquid geometry** -- replace the generic full-bbox HTML fill in
   `scene_item.tsx` with a declared, normalized SVG liquid-region contract.
   The seam must work for multiple chambers and not obscure clicks. The existing
   structured-overlay pattern provides a useful direction, but object interiors
   need their own explicit geometry/clip declaration.
3. **Evidence-path split** -- keep diagnostic scene rendering useful, but make
   its no-registry status visible in tooling/report language. Add a protocol-host
   regression capture for selected material-bearing objects so registry behavior
   cannot be conflated with viewer behavior.
4. **Visual acceptance** -- once seams 1 and 2 exist, add material-specific
   screenshots for clear, colored, opaque, and multi-chamber materials. Continue
   treating visible-vs-hidden pixel difference only as a coarse footprint check.

## Reproduction commands

```bash
node --import tsx tests/playwright/material_render_capture.mjs \
  test-results/wow_material_visibility/current_capture

node -e 'const fs=require("fs"); const p=JSON.parse(fs.readFileSync(
  "test-results/wow_material_visibility/current_capture/capture.json","utf8"));
  const all=p.scenes.flatMap(s=>s.items); console.log(p.scenes.length, all.length,
  [...new Set(all.map(item=>item.css_color))]);'

node tests/playwright/test_subpart_well_plate_render.mjs
```

Observed results:

- `34 231 [ 'rgba(120, 120, 120, 0.35)' ]`
- Well acceptance: 96 subpart shapes; `A1=#686868`, `A2=transparent`,
  `H1=#686868`, `D6=#a719db`, `H12=transparent`; no page errors.

## Boundaries and residual risk

- This audit made no product changes and did not modify the existing material
  report or baseline.
- The diagnostic viewer is not a substitute for a protocol-host stateful test.
- The structured-well test writes through the production store path but uses a
  focused harness, not a complete student walkthrough.
- No claim here says that an object fill percentage measures actual liquid
  volume, vessel shape, or pedagogical correctness.
