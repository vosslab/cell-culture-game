# SVG gradient color-loss: corrected root cause and render verification

Ground truth: browser render (chromium + firefox) via
`tests/playwright/svg_render_for_regression.mjs` (SVG embedded as a data: URI in
an `<img>`, 256x256, white background). phash/dhash via `imagehash`.

## Summary

The previous fix for the `userSpaceOnUse` gradient color-loss bug was
incomplete. A browser recheck (`svg_visual_regression_gradient_recheck.md`)
proved `cpu.svg` still greyed (phash ~40, dhash ~41 in both engines) after
normalization. This report records the TRUE root cause, the corrected fix, and
render evidence.

## True root cause (two bugs, both confirmed by render)

The earlier "bake the element matrix M into `gradientTransform`" change was
itself geometrically correct, but two later behaviors broke the render:

### Bug 1 -- crop-to-origin shift applied to gradient coordinates

After flattening, `normalize_svg_file` shifts all geometry by `(dx,dy)` to crop
to the origin. `shift_element` added `(dx,dy)` directly to every `cx/cy` and
`x1/y1/x2/y2`, including `userSpaceOnUse` gradient/pattern coordinate
attributes. But those coordinates resolve THROUGH the paint transform (which now
holds M). So `M * (coords + (dx,dy))` re-scales the shift by M instead of
translating the paint output by `(dx,dy)`; the paint lands off the geometry and
collapses to a single stop color. The same code also corrupted
`objectBoundingBox` 0..1 fractions (they are crop-invariant and must not move).

Minimal probe (one `userSpaceOnUse` linearGradient under
`translate(20,20)scale(2)`):

- original: clean red->blue diagonal filling the square.
- old normalize: collapsed to near-solid blue (gradient mis-placed).
- corrected normalize: render-identical red->blue diagonal.

Decisive candidate test (effective endpoints = gradientTransform * coords;
target = flattened path bbox corners `(2,2)`/`(62,62)`):

| Variant | effective endpoints | matches target |
| --- | --- | --- |
| A (current buggy: shift coords, gT=M) | (-36,-36),(24,24) | NO |
| B (keep coords, gT = T(dx,dy)*M) | (2,2),(62,62) | YES |
| C (gT = M*T(dx,dy), wrong order) | (-36,-36),(24,24) | NO |
| D (bake coords = T(dx,dy)*M*coords, gT=identity) | (2,2),(62,62) | YES |

Variant B chosen: it keeps the paint's own coordinates intact and works for
radial `r`/`fx`/`fy` and patterns without per-attribute special-casing, because
the matrix carries the scale.

### Bug 2 -- stroke-width not scaled on transform flatten (dominant cpu.svg cause)

`_flatten_one` baked the matrix into geometry but left `stroke-width` unchanged.
`cpu.svg`'s grid is a single `#bdcdd4` mesh path (`rect846-6`) with 252 square
hole-cutouts, authored under a ~0.415 scale with `stroke-width:0.995`. On screen
that stroke is ~0.413 units (thin). After flatten the geometry shrank to 0.415x
but the stroke stayed 0.995 (~2.4x too thick), so the ~0.5-unit half-stroke
filled the ~2.6-unit holes with the mesh color, hiding the colored layer beneath.
This is why `cpu.svg` greyed even though every gradient was correctly placed
(buggy-vs-fixed phash = 2: the gradient fix alone changed almost nothing for
cpu; the stroke was the dominant cause).

## The fix (in `tools/normalize_svg_v3.py`)

- `shift_element`: gradient/pattern coordinate attributes are never shifted.
  `userSpaceOnUse` paints get `translate(dx,dy)` prepended to their
  `gradientTransform`/`patternTransform` (`_shift_userspace_paint`);
  `objectBoundingBox` paints are left untouched.
- `_flatten_one`: scales `stroke-width` (presentation attribute and inline
  style) by the matrix's uniform scale factor `hypot(a,b)` via
  `_scale_stroke_width`. The pre-existing non-uniform/skew-stroke reject
  guarantees the scale is a single scalar whenever a visible stroke is present;
  non-scaling-stroke elements are already rejected when scale != 1.

Reject-fallback unchanged: a `userSpaceOnUse` paint shared by elements under
differing transforms still rejects `UNSUPPORTED_TRANSFORM` (one matrix cannot
satisfy two element positions). No case in the corpus needed the
radial-under-non-uniform reject path; that path remains available via the
existing stroke/transform guards.

## Render evidence (chromium unless noted)

| Asset | before (old normalize) | after (corrected) | dhash | notes |
| --- | --- | --- | --- | --- |
| probe (synthetic) | solid blue (collapsed) | red->blue diagonal | -- | render-identical |
| cpu.svg | grey grid, dark squares | full colorful CPU | 41 -> 33 | both engines; phash 40 residual is no-crop reframe (original viewBox clipped content), not color |
| genomesequencer-3.svg | -- | render-identical | 2 | phash 10 |
| scanning-electron-microscope-sem.svg | -- | render-identical | 1 | phash 2 |
| centrifuge-big.svg | -- | render-identical | 1 | phash 4 |

cpu.svg outcome: NORMALIZED, render-identical in color (full colorful CPU in
chromium AND firefox). It is not rejected; the geometry is fully supported once
both bugs are fixed. The residual phash (40) is the legitimate no-crop reframe:
the original authored viewBox (`0 0 34.9 35.0`, in mm) clips content that extends
to ~42 units, so v3 correctly expands the viewBox to show all content -- a
framing change, not color loss. dhash (structure-sensitive) dropped 41 -> 33,
and the visual render is unambiguously the full colorful chip.

Why phash is not the gate here: when normalization legitimately reframes
(crop-to-bbox, viewBox expansion), phash penalizes the framing shift even when
color is perfect. The browser render is the ground truth; phash/dhash are
supporting signals.

## Tests

- Rewrote two tests that encoded the incomplete behavior
  (`test_userspace_gradient_single_use_lands_on_flattened_geometry`,
  `test_userspace_gradient_existing_transform_stays_aligned`) to assert the
  render-meaningful invariant: effective gradient coordinates land on the
  flattened geometry bbox, not a raw `gradientTransform` matrix value.
- Added `test_userspace_gradient_crop_shift_tracks_geometry` (large crop shift),
  `test_stroke_width_scaled_by_uniform_flatten_attr`,
  `test_stroke_width_scaled_by_uniform_flatten_style`, and a
  `stroke_width_scaled_under_flatten` fixture entry.
- Strengthened `test_objectboundingbox_gradient_under_transform_unchanged` to
  assert 0..1 fractions are not shifted.
- `pyflakes` clean; `--self-test` passes; `pytest
  tests/test_normalize_svg_v3.py tests/test_normalize_svg_geometry.py` = 164
  passed.

Gallery PNGs: `test-results/svg_gradient_fix/` (gitignored).
