# Viewport overflow reflow investigation

Read-only diagnosis of a front-zone viewport-clipping regression introduced by
the vertical-reflow spine (WP-3b). This document is the durable record of an
investigation that already concluded; it does not re-investigate. The fix is
being implemented separately as WP-3c (task #37).

## Summary

The vertical-reflow spine (WP-3b) regressed front-zone viewport clipping from 2
scenes at the pre-spine WP-0 baseline to 15 or more scenes. The root cause is a
genuine spine bug in the uniform rescale denominator: the scale factor is
computed against `totalContent`, which mixes scalable object height with fixed
non-scaling overhead. Because only object height shrinks under the scale, the
fixed overhead survives and the recomputed content still exceeds the scene
range, pushing tier-3 art below the renderable viewport. This is a
PRIMARY_DESIGN never-crop visual hard fail even though the bbox-level gates
report green. The recommended fix corrects the denominator at the design level
rather than clamping objects to the scene-bounds bottom (which would crop art
and violate never-crop).

## Symptom and evidence

| Measure | Value |
| --- | --- |
| Pre-spine WP-0 baseline clipped scenes | 2 |
| Post-reflow clipped scenes (visual review) | 15 or more |
| Post-reflow clipped scenes (stats gate) | 11 (`clipped_item_count`) |
| Affected object types | 96-well plates, vortex, rocking shaker, microtube and dilution racks |

The stats gate `clipped_item_count` undercounts. Objects pushed fully below the
viewport have an off-canvas bbox and `aspect_delta_pct = 0`, so the never-crop
bbox gate does not see them as clipped. The gate flagged 11 while visual review
found 15 or more. A green bbox gate therefore does not clear this regression;
the failure is a visual one.

## sceneRange source

The reflow range is taken verbatim from authored YAML `scene_bounds` with no
transform. In [reflow_zones.ts](../../../src/scene_runtime/layout/reflow_zones.ts)
around lines 328 to 329:

- `sceneRangeTop = sceneBounds.top` (5 for `seeding_workspace`)
- `sceneRangeBottom = sceneBounds.bottom` (95 for `seeding_workspace`)
- `sceneRange = 90` scene-pct

## Worked overflow magnitude (seeding_workspace)

Content extents exceed the scene range, so the overflow branch stacks bands from
`sceneRangeTop = 5` with no clamp to `sceneRangeBottom`. In
[reflow_zones.ts](../../../src/scene_runtime/layout/reflow_zones.ts) the overflow
branch at line 353 pushes each group's content extent, and the band layout at
lines 379 to 399 stacks from `sceneRangeTop` with `cursor = bottom` and no
bottom clamp.

| Quantity | Value (scene-pct) |
| --- | --- |
| Center zone contentExtent | 64.71 |
| Rear zone contentExtent | 44.70 |
| totalContent | 109.41 |
| sceneRange | 90.00 |
| Overflow (totalContent > sceneRange) | yes |
| group1 band | [5.00, 49.70] |
| group2 band | [49.70, 114.41] |
| scene_bounds.bottom | 95.00 |

Group2 ends at 114.41, past `scene_bounds.bottom = 95`. Precomputed final object
positions confirm the overflow at the object level:

| Object | _top | _height | objectBottom | Overshoot below clip |
| --- | --- | --- | --- | --- |
| center_vortex | 97.81 | 15.06 | 112.87 | +17.87 scene-pct (about 193 px at 1080p) |
| center_well_plate_96 | -- | -- | 105.15 | +10.15 scene-pct |

## Root cause classification

Classification (a): genuine spine bug from WP-3b.

`uniformScaleFor` in
[vertical_layout.ts](../../../src/scene_runtime/layout/vertical_layout.ts) around
lines 233 to 243 computes `raw = sceneRange / totalContent = 90 / 109.41 =
0.823`. The denominator `totalContent` includes fixed, non-scaling overhead:

- zone padding `2 * 1.5` per group
- tier gaps `4 * (nTiers - 1)`
- per-item label box `2.2` plus label gap `3.5`

Only object height scales under `uniformScale`. The label line height, label
gap, tier gap, and zone padding stay fixed (canvas-relative). Because the scale
is derived from a denominator that includes about 19 units of fixed overhead,
the scale is too gentle: roughly 19 units of overhead remain after scaling, the
re-reflow still exceeds 90, and tier-3 art clips.

Why the baseline was 2: before WP-3a, a per-object `fitFactor` shrink forced
objects inside the authored zone bounds (top 38, bottom 94), so nothing exceeded
`scene_bounds.bottom`. The reflow removed that lever.

Why 11 or 15, not 38: only multi-tier zones whose contentExtent pushes tier-3
rows below `scene_bounds.bottom` clip. Single-tier and shorter zones still fit.

## Recommended design fix

Correct the denominator so the scale acts only on the scalable content:

- `scalableContent = totalContent - fixedOverhead`
- `scale = (sceneRange - fixedOverhead) / scalableContent`
- clamp to `[UNIFORM_RESCALE_MIN_SCALE = 0.40, 1]`
  (see [constants.ts](../../../src/scene_runtime/layout/constants.ts))

This is a design-level fix: it corrects the false premise that all of
`totalContent` is scalable. It is not a symptom-level fix. A per-object clamp to
`scene_bounds.bottom` would crop art and violate the PRIMARY_DESIGN never-crop
rule.

Label-overlap risk: the corrected scale is slightly more aggressive (objects
become smaller, labels proportionally larger). The `LABEL_DOMINANT_RATIO = 0.35`
gate is the correct advisory signal for near-threshold scenes. The tier
structure is unchanged, so new label-to-label overlaps are unlikely.

## Gate coverage gap

`clipped_item_count` undercounts fully-off-canvas objects. An object pushed
entirely below the viewport has an off-canvas bbox and `aspect_delta_pct = 0`,
so the bbox-aspect never-crop gate does not flag it. A future detector should
flag any object whose art bottom exceeds the renderable viewport, independent of
bbox aspect, so that fully-displaced objects are caught rather than silently
passing a green bbox gate.
