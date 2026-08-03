# Layout engine tunable inventory

Read-only evidence artifact for the LayoutConfig hierarchy (M2 / WP-CFG1) of the
approved layout-engine plan
(`/Users/vosslab/.claude/plans/partitioned-shimmying-dragonfly.md`).

This inventory enumerates every tunable currently scattered across
`src/scene_runtime/layout/`: the named constants in `constants.ts` plus every
behavior-shaping inline numeric literal in the stage files. The goal is a
complete list so the declarative LayoutConfig can absorb each one and resolve it
by precedence (global defaults -> scene `layout_rules` -> zone overrides ->
placement-derived -> strategy-local).

## How to read this

- `proposed layer` is a recommendation for where the value should resolve in the
  new precedence chain, not a current fact.
  - `global`: a repo-wide default, no current authoring override.
  - `scene`: belongs in scene-level `layout_rules` (some already do).
  - `zone`: a per-zone override (some already exist as `Zone` fields).
  - `placement`: derived from or overridable per placement (some already exist
    as `PlacementAuthored` fields).
  - `strategy`: local to one layout strategy (alignment mode, wrap, stagger);
    only meaningful inside that algorithm.
- `spacing axis` distinguishes label-spacing tunables from object-spacing
  tunables where the distinction applies; `n/a` otherwise.
- `override home` notes an existing authoring surface, if any.

## Named constants (`constants.ts`)

| name | file:line | current value | what it controls | proposed layer | spacing axis | override home |
| --- | --- | --- | --- | --- | --- | --- |
| `ZONE_PADDING` | constants.ts:67 | `1.5` | inner padding subtracted from each zone's left/right (and bottom clamp for label stagger) before placing items/labels | zone | object + label | none |
| `MIN_SCALE` | constants.ts:68 | `0.55` | floor for uniform item shrink when a zone overflows horizontally | strategy (horizontal) | object | none |
| `MAX_FOOTPRINT_RATIO` | constants.ts:69 | `2.5` | caps how far a label may widen an item's footprint beyond its visual width | strategy (footprint) | label vs object | none |
| `PX_PER_SCENE_PERCENT` | constants.ts:70 | `11.52` | px-per-scene-percent constant in the cm scale formula (denominator) | global | object | none |
| `AVG_CHAR_WIDTH_PCT` | constants.ts:75 | `0.45` | mean glyph advance as a fraction of font size; estimates label text width for wrap + stagger | global | label | none |
| `MAX_LAYOUT_PASSES` | constants.ts:76 | `3` | max convergence passes in the fit loop | global | n/a | `PipelineInputs.maxPasses` (runtime opt) |
| `LAYOUT_SHRINK_FACTOR` | constants.ts:77 | `0.9` | per-pass `_width_scale` multiplier for zones that emitted fittable diagnostics | global | object | `PipelineInputs.shrinkFactor` (runtime opt) |
| `ITEM_ESCAPES_ZONE_TOLERANCE` | constants.ts:78 | `3` | vertical slack (scene-percent) before an item is flagged as escaping its zone | zone | object | none |
| `LABEL_FONT_WIDTH_FRACTION` | constants.ts:85 | `0.012` | label font size as a fraction of rendered canvas width | global | label | none |
| `LABEL_FONT_MIN_PX` | constants.ts:86 | `12` | floor for computed label font size on small panels | global | label | none |
| `LABEL_LINE_HEIGHT_PCT` | constants.ts:91 | `2.2` | staggered label row height (scene-percent), multiplied by line count | strategy (labels) | label | none |
| `DEPTH_SCALE.back` | constants.ts:93 | `0.8` | visual-width multiplier for back-depth items | placement | object | `PlacementAuthored.depth` |
| `DEPTH_SCALE.mid` | constants.ts:93 | `1.0` | visual-width multiplier for mid-depth items | placement | object | `PlacementAuthored.depth` |
| `DEPTH_SCALE.front` | constants.ts:93 | `1.1` | visual-width multiplier for front-depth items | placement | object | `PlacementAuthored.depth` |
| `DEPTH_BASELINE_OFFSET.back` | constants.ts:94 | `-4` | baseline Y offset (scene-percent) for back-depth items | placement | object | `PlacementAuthored.depth` |
| `DEPTH_BASELINE_OFFSET.mid` | constants.ts:94 | `0` | baseline Y offset for mid-depth items | placement | object | `PlacementAuthored.depth` |
| `DEPTH_BASELINE_OFFSET.front` | constants.ts:94 | `4` | baseline Y offset for front-depth items | placement | object | `PlacementAuthored.depth` |
| `DEFAULT_VIEWPORT.w` | constants.ts:95 | `1920` | default viewport width for aspect math | global | n/a | `PipelineInputs.viewport` |
| `DEFAULT_VIEWPORT.h` | constants.ts:95 | `1080` | default viewport height for aspect math | global | n/a | `PipelineInputs.viewport` |
| `DEFAULT_SCENE_BOUNDS.left` | constants.ts:98 | `1` | default scene-bounds left edge for clamp | scene | object | `SceneA.scene_bounds` |
| `DEFAULT_SCENE_BOUNDS.right` | constants.ts:99 | `99` | default scene-bounds right edge | scene | object | `SceneA.scene_bounds` |
| `DEFAULT_SCENE_BOUNDS.top` | constants.ts:99 | `5` | default scene-bounds top edge | scene | object | `SceneA.scene_bounds` |
| `DEFAULT_SCENE_BOUNDS.bottom` | constants.ts:100 | `95` | default scene-bounds bottom edge | scene | object | `SceneA.scene_bounds` |
| `DEFAULT_LAYOUT_RULES.label_font_size` | constants.ts:103 | `16` | default authored label font size | scene | label | `SceneA.layout_rules.label_font_size` |
| `DEFAULT_LAYOUT_RULES.label_line_height` | constants.ts:104 | `1.1` | default authored label line height | scene | label | `SceneA.layout_rules.label_line_height` |
| `DEFAULT_LAYOUT_RULES.label_offset_y` | constants.ts:105 | `4` | default authored label vertical offset from item | scene | label | `SceneA.layout_rules.label_offset_y` |
| `DEFAULT_LAYOUT_RULES.zone_gap` | constants.ts:106 | `2` | default authored gap between items in a zone | scene | object | `SceneA.layout_rules.zone_gap` |
| `DEFAULT_LAYOUT_RULES.default_align_stop` | constants.ts:107 | `"center"` | default tab-stop bucket for items lacking `align_stop` | scene | object | `SceneA.layout_rules.default_align_stop` |
| `WORKSPACE_PX_PER_CM.bench` | constants.ts:125 | `5.5` | px-per-cm scale calibration for the bench workspace | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |
| `WORKSPACE_PX_PER_CM.hood` | constants.ts:126 | `8.0` | px-per-cm for hood | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |
| `WORKSPACE_PX_PER_CM.microscope` | constants.ts:127 | `10.0` | px-per-cm for microscope | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |
| `WORKSPACE_PX_PER_CM.incubator` | constants.ts:128 | `9.0` | px-per-cm for incubator | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |
| `WORKSPACE_PX_PER_CM.plate_reader` | constants.ts:129 | `8.0` | px-per-cm for plate_reader | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |
| `WORKSPACE_PX_PER_CM.cell_counter` | constants.ts:130 | `9.0` | px-per-cm for cell_counter | global (per-workspace) | object | `PipelineInputs.workspacePxPerCm` |

## Inline literals in stage files

| name (described) | file:line | current value | what it controls | proposed layer | spacing axis | override home |
| --- | --- | --- | --- | --- | --- | --- |
| zone gap default fallback | horizontal_layout.ts:59 | `?? 2` | gap used when `layout_rules.zone_gap` is unset (duplicates `DEFAULT_LAYOUT_RULES.zone_gap`) | scene | object | `layout_rules.zone_gap` |
| tab-stop overflow tolerance | horizontal_layout.ts:89 | `+ 0.5` | slack before emitting `tab_stop_overflow` | strategy (horizontal) | object | none |
| zone overflow tolerance | horizontal_layout.ts:135 | `+ 0.5` | slack before emitting `zone_overflow_negative_gap` | strategy (horizontal) | object | none |
| overflow_pct rounding | horizontal_layout.ts:96,142 | `.toFixed(2)` | diagnostic decimal precision | strategy (diagnostics) | n/a | none |
| aspect floor | vertical_layout.ts:30 | `Math.max(0.01, ...)` | minimum item aspect to avoid divide-by-zero in height math | global | object | none |
| label offset Y fallback | layout_labels.ts:39 | `?? 3.5` | label vertical offset when `layout_rules.label_offset_y` is unset (differs from `DEFAULT_LAYOUT_RULES.label_offset_y = 4`) | scene | label | `layout_rules.label_offset_y` |
| horizontal nudge pass count | layout_labels.ts:51 | `< 3` | number of label horizontal-collision nudge passes | strategy (labels) | label | none |
| stagger row-fit tolerance | layout_labels.ts:99 | `- 0.3` | left-edge slack when testing if a label fits an existing stagger row | strategy (labels) | label | none |
| residual-collision tolerance | layout_labels.ts:164 | `- 0.3` | overlap slack before emitting `label_collision_residual` | strategy (labels) | label | none |
| clamp dx/dy rounding | clamp_scene_bounds.ts:51,52 | `.toFixed(2)` | diagnostic decimal precision | strategy (diagnostics) | n/a | none |
| wrap budget tolerance | wrap_label.ts:10 | `budget * 1.1` | how far estimated text width may exceed the label budget before wrapping | strategy (wrap) | label | none |
| max wrap lines | wrap_label.ts:21-23 | 2 lines (head/tail) | hard cap of two lines per wrapped label | strategy (wrap) | label | none |
| neutral fallback scale | scale_to_real_world.ts:33,62,70 | `1.0` | `_width_scale` used in every non-cm-model fallback branch | global | object | none |

## Existing authoring override homes (cross-reference)

The plan should treat these as already-resolved precedence inputs, not new
fields to invent:

- `align`: `Zone.align` (zone-level alignment mode).
- `baseline`: `Zone.baseline` (zone-level baseline Y).
- `align_stop`: `PlacementAuthored.align_stop` (placement tab-stop bucket).
- `baseline_override`: `PlacementAuthored.baseline_override` (placement baseline Y).
- `depth_tier`: `PlacementAuthored.depth_tier` (sort/stack order within a zone).
- `depth`: `PlacementAuthored.depth` (drives `DEPTH_SCALE` / `DEPTH_BASELINE_OFFSET`).
- `layout_rules` fields: `zone_gap`, `label_font_size`, `label_line_height`,
  `label_offset_y`, `default_align_stop` (`SceneA.layout_rules`).
- Per-placement `layout` partial: `default_width`, `label_width`, `anchor_y`,
  `anchor_y_offset`, `display_width_cm` (`PlacementAuthored.layout`).
- Runtime pipeline opts (not authored YAML, but real override points):
  `viewport`, `workspacePxPerCm`, `maxPasses`, `shrinkFactor`
  (`PipelineInputs`).

## Coverage and exclusions

Every file named in the scope was read in full and grepped for numeric
literals. The grep command was:

```
grep -nE '[^a-zA-Z_.][0-9]+\.[0-9]+|[^a-zA-Z_.0-9][0-9]+' <scope files>
```

File:line coverage confirmed for: `constants.ts`, `horizontal_layout.ts`,
`vertical_layout.ts`, `layout_labels.ts`, `wrap_label.ts`, `footprint.ts`,
`clamp_scene_bounds.ts`, `run_pipeline.ts`, `group_by_zone.ts`,
`scale_to_real_world.ts`.

Intentionally excluded literals (not tunables; behavior-neutral):

- Loop indices and bounds: `i = 0`, `i < items.length`, `i - 1`, `pass + 1`,
  `i >= 0` (horizontal_layout, layout_labels, run_pipeline). These are control
  flow, not configurable.
- Geometric halving and centering: `/ 2`, `fw / 2`, `total / 2`,
  `(top + bottom) / 2`, `heightPct / 2` (horizontal, vertical, clamp). These
  are exact midpoint math, not tunable thresholds.
- Sentinel and identity values: `0` initializers (`_x: 0`, `_top: 0`,
  `maxRow = 0`, `dx = 0`), `Infinity` / `-Infinity` bbox seeds (clamp),
  `?? 0` depth_tier defaults (group_by_zone, layout_labels), `scale = 1` /
  `gap, 1` literal scale args in tab-stop placement. These are neutral and
  changing them would be a bug, not a tuning.
- `2 * gap` (horizontal_layout.ts:88): structural (two inter-bucket gaps),
  derived from `gap`, not an independent tunable.
- The `?? 2` and `?? 3.5` fallbacks ARE included above because they shadow the
  `DEFAULT_LAYOUT_RULES` constants and notably the `3.5` disagrees with the
  constant's `4`; that divergence is a real config-consolidation target.

## Ambiguous cases (flag for plan author)

- `ZONE_PADDING` is consumed by both horizontal item placement and label
  stagger clamping, so it is both an object-spacing and label-spacing tunable.
  Listed as zone-layer; the plan may want to split it into two configs if the
  axes should diverge.
- `label_offset_y` has two disagreeing defaults: `DEFAULT_LAYOUT_RULES = 4`
  vs the inline `?? 3.5` in `layout_labels.ts:39`. The LayoutConfig must pick
  one canonical default; this is a pre-existing inconsistency, not a new
  decision.
- `zone_gap` fallback is duplicated (constant `2` and inline `?? 2`). Same
  consolidation note.
- `MAX_LAYOUT_PASSES`, `LAYOUT_SHRINK_FACTOR`, `DEFAULT_VIEWPORT`, and
  `WORKSPACE_PX_PER_CM` already have runtime override points via
  `PipelineInputs`, but no authored-YAML home. Whether they should become
  scene-authorable or stay runtime-only is a plan decision.
- The two `0.3` tolerances (stagger row-fit, residual-collision) are
  deliberately the same value per code comments. The plan should decide whether
  they share one config key or stay independent.
