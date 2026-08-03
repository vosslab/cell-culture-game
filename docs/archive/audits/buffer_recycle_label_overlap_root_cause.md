# Buffer recycle label overlap root cause

Read-only investigation. No engine, gate, asset, or YAML edits were made. A PNG
of the affected scene was rendered to `/tmp/recycle_scene.png` and inspected to
confirm the defect visually.

## Summary

The "Buffer recycle bottle" label overlaps its OWN bottle SVG, and the
overlapped portion of the wrapped second line ("le" of "bottle") is hidden
behind the bottle art, so the text reads "bott". This is ONE positional defect
(label seeded above the object, then the seed-level top-clamp pushes the 2-line
label DOWN onto the object's own cap), plus a secondary paint-order symptom
(the object SVG carries a z-index, the label does not, so the SVG paints over
the overlapped text). The user-named gate (Playwright assertion H) passed
because it is structurally dead, not because the overlap is absent.

## 1. Scene, placement, object, asset, zone

| Field | Value |
| --- | --- |
| Scene | `sdspage_recycle_buffer_workspace` |
| Inherits from | `electrophoresis_bench` (base scene) |
| Placement | `rear_left_recycle_buffer_bottle` |
| Object | `recycle_buffer_bottle` (`kind: bottle`) |
| Label | "Buffer recycle bottle" -> wraps to ["Buffer recycle", "bottle"] |
| Asset | `bottle_green` (a NORMALIZED bottle, not the deferred pipette case) |
| Zone | `rear_left` (a rear shelf band, `bounds.top = 5%`) |
| Depth tier | 2 |

Files:
- `content/protocols/sdspage/sdspage_recycle_buffer/scenes/sdspage_recycle_buffer_workspace.yaml` (extends base)
- `content/base_scenes/electrophoresis_bench.yaml` (placement + zone defs)
- `content/objects/bottle/recycle_buffer_bottle.yaml` (object, `label_width: 8`)
- `generated/precomputed_layout.ts` (computed geometry, lines ~11606-11637)
- `generated/scene_render_stats/sdspage_recycle_buffer_workspace.stats.json`

## 2. Overlap cause: top-label seed clamped DOWN onto own cap

Engine numbers for this placement (scene-percent, from `precomputed_layout.ts`):

- `_top` = 9.946, `_height` = 22.054 -> visual box vertical span [9.946, 32.000]
- `_centerX` = 25.887, `_visualWidth` = 5.729 -> visual box [23.02, 28.75]
- `_labelX` = 24.5, `_labelY` = 6.5
- `_labelLines` = ["Buffer recycle", "bottle"] (2 lines)

Relevant tunables (`src/scene_runtime/layout/constants.ts`,
`config/resolve_config.ts`):

- `labelOffsetY` = 3.5
- `LABEL_LINE_HEIGHT_PCT` = 2.2 (label height = 2 lines * 2.2 = 4.4)
- `labelZonePadding` = `ZONE_PADDING` = 1.5 (the prompt's "~6.5" is stale; 6.5 is
  the resulting `_labelY`, not the padding)

Seed + clamp arithmetic in `src/scene_runtime/layout/layout_labels.ts`
(lines 215-240), top placement (default):

- Ideal seed (label TOP edge above the object):
  `seededY = _top - labelOffsetY - labelHeight = 9.946 - 3.5 - 4.4 = 2.046`
- `topClamp = zone.bounds.top + labelZonePadding = 5 + 1.5 = 6.5`
- `seededY (2.046) < topClamp (6.5)` -> clamp fires -> `_labelY = 6.5`

So the seed-level top-clamp (line 239: `if (labelY < topClamp) labelY = topClamp`)
pushes the label's TOP edge DOWN from 2.046 to 6.5 because the ideal seed would
escape above the rear-zone top. The label box becomes:

- label span = [_labelY, _labelY + labelHeight] = [6.5, 10.9]
- visual box top = 9.946

Vertical overlap = 10.9 - 9.946 = **0.954% of scene height** (~11 px) of the
label's second line sitting INSIDE the bottle's own visual box (the cap). This
is a genuine clamp-onto-own-cap defect: the clamp keeps the label inside the
zone but has no guard that the label must stay ABOVE its own object's top edge.

Horizontally, Guard-8's label width model
(`longestLine.length * AVG_CHAR_WIDTH_PCT = 14 * 0.45 = 6.3`, half 3.15) gives
label x-span [21.35, 27.65], which overlaps the visual x-span [23.02, 28.75]
from 23.02 rightward. That overlap region (x >= 23.02) is exactly where the
second line's trailing characters fall -- i.e. the "le" of "bottle".

## 3. Why the named gate (Playwright assertion H) missed it

`tests/playwright/test_generalization_render.mjs`, assertion H ("No
label-own-SVG overlap", lines 358-381) resolves each label's owning placement by
walking the label DOM node's ANCESTOR chain for `data-placement-name`:

```js
const placementName = await labelLocators[i].evaluate((el) => {
  let current = el;
  while (current) {
    if (current.hasAttribute("data-placement-name")) return current.getAttribute("data-placement-name");
    current = current.parentElement;
  }
  return null;
});
const associatedPlacement = placements.find((p) => p.name === placementName);
if (associatedPlacement && associatedPlacement.svgBbox) { ... compare ... }
```

But in the current renderer (`src/scene_runtime/renderer/scene_view.tsx`,
lines 248-264) the `SceneLabel` div is a SIBLING of `SceneItem`, not a child of
the placement element. The label node carries its association as
`data-label-for={placement_name}` (line 116), NOT as a `data-placement-name`
ancestor. So the ancestor walk returns `null`, `placements.find(p => p.name ===
null)` returns `undefined`, the `if (associatedPlacement ...)` body is skipped
for EVERY label, and `hFailed` is never set. Assertion H performs ZERO real
comparisons and passes vacuously on every scene. It is a dead gate, not a
passing gate.

Note a SECOND, geometric own-SVG check exists and is NOT dead:
`structural_guards.ts` Guard 8 (`checkNoLabelOwnSvgOverlap`, lines 409-435)
compares `labelBbox` vs the visual `itemBbox` and would flag this overlap at
~16% (`overlapPct = 4.42 / 27.7 ~ 16%`, above `LABEL_OVERLAP_TOLERANCE = 1`).
The scene stats confirm it: `label_art_overlap_count: 1`. But at LIVE render
(`scene_view.tsx` line 168) Guard 8 runs in report-only mode
(`collectStructuralViolations`, never throws -- it only drives degrade-not-blank).
The throwing wrapper `runStructuralGuards` is only invoked by the unit tests
(synthetic items) and `tests/e2e/e2e_generalization_preflight.mjs`. So nothing
in the interactive/Playwright path turns the detected overlap into a failure,
and the one gate the prompt named (assertion H) cannot see it at all.

## 4. The "truncation" is paint-order occlusion, not a width/wrap cap

The text is fully present; it is HIDDEN behind the bottle SVG.

Paint order evidence:
- `scene_item.tsx` lines 90-98: each `SceneItem` gets an explicit
  `z-index: z_index_for(item)` (DEPTH_Z back=1/mid=2/front=3, default 1).
- `scene_view.tsx` lines 114-129: `SceneLabel` has NO z-index (effectively
  `auto`/0) and `pointer-events: none`.
- `scene_view.tsx` lines 248-264: per item, `SceneItem` then `SceneLabel` render
  as absolutely-positioned siblings.

Because the bottle's item has a positive z-index (>= 1) and its own label has
z-index auto (0), the bottle's green SVG paints ABOVE its own label. The label
text that falls inside the visual box (x >= 23.02, the cap region) is occluded.
That occluded region is exactly the horizontal extent where `label_bbox`
overlaps `visual_bbox` (item 2 arithmetic), which is where the trailing "le"
of "bottle" sits -- hence the on-screen "bott". Rendered PNG
(`/tmp/recycle_scene.png`) confirms: line 1 "Buffer recycle" is clear above the
cap; line 2 shows "bott" with the remainder swallowed by the cap art. (The same
class of defect is visible on the bottom-left "Mini-PROTEAN" label; the recycle
bottle is the named instance.)

There is NO width-cap / `AVG_CHAR_WIDTH_PCT` / `text-overflow` truncation: the
label uses `white-space: pre` with no clip/ellipsis, and `wrap_label` already
produced the full "bottle" line. The missing glyphs are occluded, not dropped.

## Recommendations (not implemented)

Smallest durable fixes:

- (a) PRIMARY / positional: in the seed-level top clamp
  (`layout_labels.ts` lines 233-240, and the matching clamp in `staggerGroup`
  `topClamp`), a TOP label must never be clamped below its own object's top edge.
  Bound `_labelY` so `label_bbox.bottom <= visual_bbox.top` (i.e.
  `_labelY <= it._top - labelHeight`, with a small gap) rather than only
  `_labelY >= zone.top + padding`. When the zone top leaves no room for a 2-line
  top label above the object (rear band, object near scene top), fall back to
  bottom placement (as `center_serological_pipette` already does manually) or
  shrink the label, instead of overprinting the cap. This is "fix the design,
  not the symptom": stop the overlap, do not just raise z-order.
- (b) Paint order (secondary): give the label a z-index above its object's
  (e.g. label `z-index` = object tier + a label offset, or render all labels in
  a top layer). This makes any residual overlap READABLE, but on its own it
  leaves the label sitting on the cap (ugly), so it is a backstop, not the fix.

Gate fix is part of the durable fix: assertion H in
`test_generalization_render.mjs` must resolve the label's owner via
`data-label-for` (it already exists on the label node), not via a
`data-placement-name` ancestor walk that the current sibling DOM can never
satisfy. Additionally, the live/preflight path should treat Guard 8
`label_svg_overlap` (already detecting this, `label_art_overlap_count: 1`) as a
hard failure for normalized objects, so own-cap overlap cannot ship green again.

### One-line fix recommendations + severity

- Overlap fix (PRIMARY): clamp top labels above their own object's top edge
  (`_labelY <= _top - labelHeight`), falling back to bottom placement when the
  rear zone has no room -- severity HIGH (visible own-art overlap, contract
  visual-integrity issue).
- Truncation/occlusion fix: raise label z-index above its object's SVG so any
  residual overlap is readable -- severity MEDIUM (secondary; do not rely on it
  instead of fixing the overlap). Repair dead assertion H (resolve owner via
  `data-label-for`) and gate on Guard 8 `label_svg_overlap` -- severity HIGH for
  the gate, since it is the blind spot that let this ship.
