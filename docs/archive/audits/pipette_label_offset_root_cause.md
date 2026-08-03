# Pipette label offset root-cause audit

Read-only audit. No assets, engine, scene YAML, tests, or gates were changed.
One SVG was copied to `/tmp` and the normalizer was run on the copy only.

## Question

Scene-object labels were re-centered to sit above objects. A reviewer found
that for micropipette tool objects the label sits ~6px off the rendered visual
center, while the layout engine centers symmetrically on the footprint center
(`_centerX`). With an SVG normalization pipeline present, a 6px offset is
suspicious. Why did normalization not center the visible art inside the viewBox?

## Step 1: resolve the exact asset the renderer loads

Failing placement chosen: `base_right_micropipette` in `bench_basic`.

Trace:

- Scene YAML `content/base_scenes/bench_basic.yaml` line 139-140:
  placement `base_right_micropipette` -> `object_name: micropipette`.
- Object `content/objects/pipette/micropipette.yaml`: default state
  `held_material_name: empty` -> `visual_states.held_material_name` case
  `empty` -> `asset_name: p200_micropipette_empty`.
- Manifest `generated/svg_manifest.ts` line 49: `p200_micropipette_empty` ->
  `path: "assets/svg/equipment/p200_micropipette_empty.svg"`.
- That built-site path does not exist in the repo; it is produced at build
  time. `build_github_pages.sh` lines 132-138 copy `assets/<category>/*.svg`
  verbatim into `dist/assets/svg/<category>/`. The source-of-truth file is:

  **`/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/assets/equipment/p200_micropipette_empty.svg`**

  (16K, last modified May 17). The build copy is byte-identical; no
  transformation occurs on copy.

## Step 2: viewBox vs drawn-path bbox

The SVG declares `viewBox="0 0 109.909 478.488"`, so the viewBox horizontal
center is x = 54.955.

Measured with the normalizer's own bbox helpers
(`parse_path_to_absolute` + `path_bbox_from_segments`) over all `path`
elements:

| Metric | Value (user units) |
| --- | --- |
| viewBox center x | 54.955 |
| full path bbox x | [-0.320, 109.454], width 109.774 |
| full-path-bbox center x | 54.567 |
| full-bbox offset from viewBox center | -0.387 (-0.35%) |

By full geometric bbox the art looks centered. But the left/right extremes are
set by **stroke-only outline paths** (`fill:none`), not by the visible filled
body. Area-weighted over **filled** paths only (the visible ink mass):

| Metric | Value |
| --- | --- |
| filled-ink area-weighted centroid x | 61.906 |
| centroid offset from viewBox center | +6.951 (6.32% of width) |

The visible barrel sits left of center while a tall thin ejector/plunger strut
(`[50.33, 108.37]`) carries area to the right; the net visible ink is **not
symmetric about the viewBox center**. The geometric path bbox masks this
because two stroke-only outline paths straddle the full width symmetrically.

## Step 3: what the normalizer centers, and whether it ran

`tools/normalize_svg_v3.py` M1 scope (header lines 28-29): "crop to drawn
bbox, shift to origin, rewrite viewBox." It centers the **drawn path bbox** in
the viewBox (tight crop to geometry extents). It does not compute a
filled-ink-mass centroid; the "drawn bbox" includes stroke-only outline paths.

Running the normalizer on the `/tmp` copies:

```
REJECT: /tmp/p200_empty.svg  | CLIPPATH_UNSUPPORTED_COMPLEX: A clipPath could
not be flattened. (clip target is stroke-only (fill:none)) | at: .../path[19]
REJECT: /tmp/p200_filled.svg | CLIPPATH_UNSUPPORTED_COMPLEX (same)
```

Both pipette assets are **rejected** by the normalizer. They contain a
`<clipPath id="a">` applied to stroke-only paths that v3 cannot flatten. No
normalized output is produced. **These assets were never successfully
normalized and cannot be by the current pipeline.**

## Step 4: does normalized output center the drawn pixels horizontally

Not applicable / NO. The normalizer rejects the file, so there is no normalized
output. Even if it succeeded, it would crop to the **drawn path bbox** (which
is already near-centered, -0.35%), not to the filled-ink centroid (+6.3%). The
normalizer would not fix the visible-ink asymmetry because its centering target
is geometry extents, not ink mass.

## Step 5: what `visual_bbox` actually measures

`tools/scene_to_png.mjs` lines 325-332: `visual_bbox` is
`svgEl.getBoundingClientRect()` of the inner `<svg>` **element** (falling back
to the placement-div rect). It is the **element rectangle** (the
`object-fit:contain` letterboxed box), NOT `getBBox()` of the drawn paths and
NOT the drawn-pixel ink box.

From `generated/scene_render_stats/bench_basic.stats.json`, placement
`base_right_micropipette`:

| Box | x | w | center x |
| --- | --- | --- | --- |
| footprint_bbox | 1717.789 | 100.547 | 1768.06 |
| label_bbox | 1717.789 | 100.547 | 1768.06 |
| visual_bbox (= placement_bbox) | 1755.938 | 36.047 | 1773.96 |

The label is centered on the footprint center (1768.06 = `_centerX`, confirmed
at `src/scene_runtime/layout/layout_labels.ts` line 244 `_labelX: it._centerX`).
The `visual_bbox` element-rect center is 1773.96. The gap is **+5.9px** -- the
reviewer's ~6px.

Important: this 5.9px is the offset between the label (on footprint center) and
the **SVG element rect** center, not between the label and the true drawn ink.
The element rect is the letterboxed `contain` box; within it the filled ink is
itself off-center by ~6.3% of viewBox width (Step 2). So the visible-ink offset
is real, but the number the gate reports comes from the element rectangle, not
from drawn pixels.

## Which of the 5 candidate causes is true

- (1) "never run through normalize_svg_v3.py" -- **TRUE, and stronger than
  stated**: the assets are *rejected* by the normalizer (unflattenable
  clipPath), so they cannot pass through it at all.
- (2) stale/duplicate asset path -- false. The manifest path resolves to a
  build-time verbatim copy of the single source file; no duplicate.
- (3) "normalizer centers viewBox but not drawn pixel bbox" -- partially
  relevant: the normalizer centers the drawn *path* bbox (geometry extents,
  including stroke-only outlines), which is near-centered already; it never
  targets filled-ink mass. But it is moot because the file is rejected.
- (4) intentional off-center whitespace/stroke bounds -- this is the underlying
  geometry reality: stroke-only outline paths set the symmetric bbox while the
  filled body is asymmetric. Not an authored "anchor" decision; an artifact of
  the source art.
- (5) stats measure the wrong box -- **TRUE**: `visual_bbox` is the SVG element
  rectangle (`getBoundingClientRect`), not the drawn-pixel/`getBBox` of paths.

Both (1) and (5) hold. The label-vs-footprint centering is geometrically
correct (label on `_centerX`); the asset's visible ink is asymmetric inside its
own viewBox; and the metric the reviewer compared against is the element rect,
not the ink.

## Recommended route

The asset's visible ink is asymmetric in its viewBox, and the normalizer that
would re-center geometry refuses these files. Two real defects exist (asset
geometry + measurement), so the durable route is to **fix the asset pipeline so
these pipette SVGs are normalizable, then re-normalize them**, because that
puts the drawn geometry symmetric in the viewBox and removes the source of the
offset for the layout engine that already centers on `_centerX`.

Exact files needing attention (clipPath flattening blocks normalization on all
of them; verify each, then re-normalize):

- `assets/equipment/p200_micropipette_empty.svg`
- `assets/equipment/p200_micropipette_filled.svg`
- `assets/equipment/p10_micropipette_empty.svg`
- `assets/equipment/p10_micropipette_filled.svg`
- `assets/equipment/micropipette_rack.svg` (check for the same clipPath shape)

Caveat for the implementer: normalizing to the **drawn path bbox** alone will
not remove the visible-ink asymmetry (the stroke-only outline paths keep the
bbox symmetric while the filled body stays left/right-biased). The asset fix
must either (a) flatten/remove the unbalanced stroke-outline + clipPath so the
crop reflects the visible body, or (b) if the art is intentionally asymmetric,
add explicit visual-anchor metadata to the object so the layout engine offsets
the label/anchor to the ink center rather than `_centerX`.

Secondary (do not skip): the gate's `visual_bbox` measures the SVG element
rectangle, not drawn pixels (`scene_to_png.mjs` 325-332). If a future check is
meant to assert label-on-ink alignment, it must measure `getBBox()` of the
drawn paths, not `getBoundingClientRect()` of the `<svg>` element. Until then,
a "6px" reading is an element-rect-vs-footprint number, not a true ink offset.
