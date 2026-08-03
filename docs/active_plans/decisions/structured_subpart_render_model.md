# M8 decision: generated geometry remains the structured-subpart render model

**Decision date:** 2026-08-01  
**Decision:** Keep generated geometry permanently for structured material areas
(wells, rack slots, and gel lanes). Do not convert their base artwork to the
semantic material-SVG vessel mechanism. A future art repair may improve the
base illustration, but it does not change the material-area renderer.

## Question and decision rule

M8 asks whether semantic SVG elements would be better than the generated
per-subpart geometry already used by the production path. The plan requires
both addressable per-cell art and 96 independently stateful cells that update
within budget before it can recommend conversion. The plate passes state and
timing, but it fails the durable-addressability condition; generated geometry
also gives the better spatial contract. This closes the question.

## Evidence

### Base artwork: not semantically addressable

[`96well_pcr_plate.svg`](../../../assets/equipment/static/96well_pcr_plate.svg)
visually contains 96 filled well interiors, but they are anonymous `<path>`
elements. The source has no `A1`–`H12` ids or semantic groups, one reusable
`source-5` drawing group in `<defs>`, 39 clip paths, 24 `<use>` references, and
194 geometric transforms. Its 96 identical-color well paths are mixed with
rims, labels, and plate body. Conversion would need to reverse-engineer and
preserve an A1–H12 mapping and drawing order through normalizer/export steps.

That is possible, but not durable semantic-SVG addressability. It duplicates
the stable mapping already declared in
[`well_plate_96.yaml`](../../../content/objects/plate/well_plate_96.yaml) and
emitted as 96 typed `circle` entries in
[`generated/object_library.ts`](../../../generated/object_library.ts). The
source's `<defs>`, `<use>`, and transforms also lie outside the deliberately
narrow material-SVG authoring model.

### State: 96 independent production-path writes

[`test_subpart_well_plate_render.spec.ts`](../../../tests/playwright/test_subpart_well_plate_render.spec.ts)
mounts the real `plate_focus_bench` scene through
`runPipeline → mountScene → SceneView → SceneItem → SubpartVisualStateOverlay`.
It seeds and writes every well through normal `SceneStore` methods exposed by
the existing harness; it neither edits the DOM nor calls a renderer API.

The M8 case applies a position-dependent three-material pattern (`mixed`,
registered `carboplatin`, and registered `media`) across A1–H12. After browser
DOM completion it verifies every one of 96 generated shapes has its own expected
`data-material-name`. Repeating a shifted pattern proves independent cell state,
not a shared plate color or an `all_wells` visual shortcut.

### Timing: full plate meets the browser-frame budget

The M8 test warms state subscriptions, then for each of 25 samples starts just
after `requestAnimationFrame`, makes 96 ordinary `store.set_object_state`
writes, waits for the next `requestAnimationFrame` (the next reactive
DOM/render completion opportunity), and accepts the sample only after all 96
DOM values match. It does not measure compositor completion or pixel paint.

| Metric                                   |    Result |                       Budget | Result |
| ---------------------------------------- | --------: | ---------------------------: | ------ |
| Median to verified DOM/render completion | 16.800 ms |                    20.000 ms | pass   |
| P95 to verified DOM/render completion    | 18.500 ms | 33.333 ms (two 60 Hz frames) | pass   |

The P95 two-frame budget is deliberately conservative: one visual change can
just miss a refresh boundary, while two frames keep a complete plate update
within the next animation-frame opportunity despite scheduling variance. A
separate 20 ms median gate confirms ordinary runs complete in the first such
opportunity despite the roughly 16.7 ms `requestAnimationFrame` timestamp
quantization. The test prints every ordered sample, avoiding a lucky one-off
measurement.

### Spatial correspondence: generated geometry is equal or better

The generated map uses the base art's exact viewBox and named subparts: `A1` is
a circle at `(45.01, 49.26)` with radius `11`, through deterministic `H12`.
The overlay shares that viewBox and `preserveAspectRatio`, aligns with the
visible wells, and leaves the base plate a single physical object. The material
overlay remains `pointer-events: none`; the existing
[`subpart_hit_surface.tsx`](../../../src/scene_runtime/renderer/subpart_hit_surface.tsx)
separately provides exact generated hit targets when a subpart interaction is
active. M8 neither changes nor replaces that interaction surface.

Semanticizing source paths would add no spatial information: those paths are
anonymous and transformed, while the generated map is already named, typed,
build-validated, and schema-owned. Generated geometry therefore better fulfills
the pedagogical requirement: material state for B7 always appears in B7.

## Consequences

- The static base SVG remains opaque; it receives no `data-vlab-*` recipe,
  semantic material groups, or vessel gravity parts.
- `subpart_geometry` remains canonical for wells, rack slots, and gel lanes.
  The generic circle/rectangle renderer has no object-name branch.
- Subpart state remains independently stored on one scene object. This decision
  neither creates per-well scene objects nor changes the existing generated
  subpart hit surface used by active subpart interactions.
- Future structured assets supply object-schema geometry in the base asset's
  viewBox. They should not manufacture semantic SVG elements just to recolor
  repeated material areas.

## Residual risks

- This measures one mounted 96-well plate in the project Chromium environment.
  A much denser future structured surface needs its own timing test.
- A future base-art redraw still needs a visual correspondence review of its
  generated geometry; it does not reopen semantic-SVG conversion.
- This decision does not alter active subpart interaction behavior; its exact
  generated hit targets remain owned by `subpart_hit_surface.tsx`.

## Validation

```text
npx playwright test tests/playwright/test_subpart_well_plate_render.spec.ts
2 passed
M8 96-well update timing: n=25; median=16.800 ms; p95=18.500 ms;
budget=33.333 ms.
```
