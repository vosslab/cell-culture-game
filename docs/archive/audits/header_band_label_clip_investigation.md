# Header-band label clip investigation (Task #20 WS-P)

Date: 2026-06-10
Scope: read-only investigation of the top-row label "trim" reported in
`test-results/scene_label_alignment/visual_eval_4a/visual_verdicts.md` for
hood_basic, hood_workspace, seeding_workspace. No src/, tools/, or content/
edits. Measurement via a scratch Playwright script against the current `dist/`
build.

## Symptom

In the eval PNGs, the top-row labels in hood_basic, hood_workspace, and
seeding_workspace look trimmed at the very top of the frame (e.g. the leftmost
bottle's label and "Aspirating"). Scientific artwork (bottles, pipettes,
plate) is never cropped. The verdicts file calls it a "framing, not artwork"
issue.

## Measurement evidence (current dist build, hood_basic)

Viewport 1920x1080. All numbers are `getBoundingClientRect` px from a live
DOM measurement of the current `dist/` build.

Scene root and frame:

- `#scene-root` rect: top=16, left=16, bottom=1078, right=1904 (w=1888, h=1062).
- `#scene-root` computed overflow: `visible / visible / visible`.
- Every ancestor up to `<html>`: overflow `visible` on all axes. No
  `overflow: hidden` clipper anywhere in the chain.
- `scene_to_png.mjs` `compute_scene_clip` result: `{x:16, y:16, w:1888, h:1062}`
  (clamped to scene-root, which is fully inside the 1920x1080 viewport).

Engine labels (`[data-label]`) vs. the frame:

- Topmost label top edge = 85.0px (label "PBS"/"Media"/etc.), which is 69px
  BELOW the clip top (16px).
- Labels with top edge above scene-root top: NONE (`aboveRootTop: []`).
- Labels with left edge left of scene-root left: NONE (`leftOfRootLeft: []`).
- "70% ethanol" label: top=85, left=167, fully inside the frame.
- "Aspirating | pipette" label: top=435 (mid-frame), not a top-row label at all.

Top-row OBJECT artwork (`[data-placement-name]` -> inner `<svg>`):

- Four rear-zone bottles (ethanol, pbs, media, sterile_water): item top = svg
  top = 69.1px.
- waste container: top = 94.8px.
- The clamped top-label top edge (85px) lands 16px BELOW the object/svg top
  (69px), i.e. INSIDE the object's upper artwork band (the colored cap region).

## Root cause

Two facts together explain the appearance, and neither is a frame crop:

1. There is no clipping element. scene-root and all ancestors are
   `overflow: visible`; the `scene_to_png.mjs` crop rect starts exactly at the
   scene-root top (y=16), and the topmost label sits at y=85, well inside the
   crop. In the CURRENT dist build, no engine label is clipped by the frame on
   any side.

2. The label-top clamp in `src/scene_runtime/layout/layout_labels.ts` pulls
   rear-zone top labels DOWN onto their own object artwork. For a `top`
   placement label the seed is `_labelY = it._top - labelOffsetY - labelHeight`
   (label sits above the object). For a rear-zone object whose top is near the
   scene top, that natural "above" position escapes the frame, so the seed
   clamp `topClamp = zone.bounds.top + labelZonePadding` (rear zones:
   5 + 1.5 = 6.5 scene-pct) forces the label TOP edge to 6.5%
   (~85px at this viewport). The rear-zone object top sits at ~3.6%
   (~69px). So the clamp deterministically places the label's top edge
   ~16px BELOW the object top, INSIDE the colored cap/upper artwork. The label
   then reads as "trimmed" because the bottle cap art is drawn over/under it,
   not because the frame cut it.

In short: the engine traded "label escapes the frame top" (the WP-3a interim
clipping) for "label overlaps the object's own upper artwork". The clamp does
exactly what its comment says; the visible artifact is label-over-art
occlusion at the top row, not a header band and not a screenshot crop.

Note on the eval PNGs: `visual_verdicts.md` states the eval used the existing
`dist/` and was NOT rebuilt. The label-alignment renderer fixes (WP-1b /
WP-3a / WP-4a per `docs/CHANGELOG.md`) mean the eval PNGs and a fresh render
can differ. A fresh `scene_to_png.mjs --scene hood_basic` render still shows
the same top-row label-on-cap occlusion, so the symptom reproduces, but the
mechanism is occlusion from the 6.5% clamp, not a frame/header clip.

## Scientific artwork risk (never-crop)

NONE. No object SVG is clipped or aspect-distorted. scene-root and ancestors
are `overflow: visible`; the crop rect contains the full scene-root; every
top-row object svg top (69-95px) is inside the crop (top 16px). The only
overlap is a non-scientific text label drawn over the top strip of a bottle
cap. The never-crop contract (PRIMARY_DESIGN.md) is not at risk from this
issue.

## Fix recommendation

Owner: ENGINE PADDING / LABEL-PLACEMENT layer
(`src/scene_runtime/layout/`), already owned by the active expert. This is not
a renderer-CSS bug (no clipper to remove) and not a `scene_to_png.mjs` framing
bug (the crop is correct and contains the full scene-root).

The genuine defect is that the 6.5% top clamp can place a rear-zone top label
ON its own object. Options, in preference order:

1. Make rear-zone top labels that cannot fit fully above their object fall
   back to BOTTOM placement (flip), rather than clamping onto the artwork. This
   keeps the never-overlap-art intent and avoids the cap occlusion.
2. Grow the usable label band at the top: reserve a small top margin inside
   scene-root (push all rear-zone objects down by ~labelHeight) so an above
   label fits without escaping the frame and without landing on the cap. This
   is the "header band" reading of the task title and is the most uniform fix,
   but it shifts every rear object.
3. Accept-and-note in WP-6: document that rear-zone top labels may sit over the
   upper cap band of tall rear glassware when there is no room above, and gate
   it as an advisory (not a hard fail), since artwork is never cropped.

Recommended: option 1 (flip to bottom when "above" does not fit within the
padded zone), with option 3 as the interim WP-6 note if the flip is out of
scope for the current expert pass.

## Numbers summary

| Quantity | Value (px @1920x1080) |
| --- | --- |
| scene-root top | 16 |
| scene_to_png clip top | 16 |
| topmost engine label top | 85 |
| rear-zone object/svg top | 69 |
| label-top minus object-top | +16 (label is below object top, on the cap) |
| labels above scene-root top | 0 |
| ancestor overflow:hidden clippers | 0 |
