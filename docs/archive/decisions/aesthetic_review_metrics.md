# Aesthetic review metrics

Spec for Claude-subagent aesthetic review of rendered virtual lab scenes. The
layout engine ships compile-time 16:9 scenes. Existing numeric metrics
(bounding-box area, overlap, occupancy) catch geometric defects but miss
aesthetic and instructional quality. This spec formalizes a qualitative review
loop driven by Claude vision reviewer-subagents that read rendered PNGs.

This doc is the companion to the API-based reviewer recorded in
[ai_polish_review_calibration.md](ai_polish_review_calibration.md). That tool
sends one Messages API request per scene. This spec instead drives review
through reviewer-subagents that read PNGs with their own vision (OAuth, no API
key) and return structured findings. The two share a rubric vocabulary but
differ in execution surface.

## Purpose and framing

- The target is instructional-illustration quality, not photorealism. A scene
  reads well when a student can see what object matters, follow the workflow,
  and read every label without strain.
- Review is qualitative first. A rubric plus failure-tags comes before any
  numeric gate. Numbers are promoted to gates only after calibration shows a
  stable, agreed-upon distribution.
- There is never a hard "beauty" gate early. Aesthetic scores route scenes to
  human review; they do not fail a build. The geometric hard-fails in the
  existing scorecard (clipping, off-page, aspect distortion) remain the only
  build-blocking checks until calibration justifies more.
- The review is read-only. Reviewer-subagents read PNGs and scene metadata and
  return findings. They do not edit code, assets, or YAML.

## Owner split

Every metric and every finding is tagged with an owner so a verdict routes to
the right fix surface. The three owners are:

- `layout-engine` &mdash; placement, scale, balance, grouping, label position,
  whitespace, grounding. These are fixable by changing the layout engine or its
  per-scene layout inputs.
- `asset/author` &mdash; icon style, color, artwork finish, label text. These
  are fixable by editing an SVG asset or the authored label string, not by
  moving things around.
- `render-bug` &mdash; debug text on screen, cropped label, placeholder or
  fallback art, misleading occlusion. These are defects in the render path, not
  design choices; they are fixed in the renderer or pipeline.

A reviewer never proposes a fix outside the metric's owner. A crowding problem
is a layout action; an ugly icon is an asset action; visible debug text is a
render bug. This keeps the synthesis output dispatchable without re-triage.

## Metric catalog

Each metric names what it captures, how a Claude reviewer judges it on a 1-5
scale with a failure tag, whether a bounding-box tool could automate it, and its
owner. Scores are 1 (worst) to 5 (best). The failure tag fires when the score is
1 or 2.

| metric | captures | how Claude judges it (1-5 anchors + failure tag) | bbox-automatable? | owner |
| --- | --- | --- | --- | --- |
| `focal_dominance` | one clear primary object draws the eye first | 5: primary unmistakable; 3: primary present but competes; 1: no clear focus. Tag: `no_focal_point` | partial (area ratio proxies it) | layout-engine |
| `label_association_clarity` | each label clearly belongs to one object | 5: every label hugs its object; 3: one ambiguous; 1: labels float free. Tag: `label_detached` | YES (nearest-object ratio) | layout-engine |
| `bench_plausibility` | objects sit where a real bench would put them | 5: physically sensible; 3: one oddity; 1: floating or stacked wrong. Tag: `implausible_placement` | partial (baseline coherence) | layout-engine |
| `instructional_grouping` | related objects cluster by workflow step | 5: groups read as steps; 3: weak grouping; 1: scattered. Tag: `no_workflow_logic` | partial (cluster gaps) | layout-engine |
| `workflow_logic` | left-to-right or staged reading path matches the protocol | 5: path obvious; 3: path unclear; 1: path contradicts steps. Tag: `reading_path_broken` | partial (x-order vs step order) | layout-engine |
| `grounding` | objects share a believable baseline, not mid-air | 5: grounded; 3: one floater; 1: many floaters. Tag: `floating_objects` | YES (baseline band coherence) | layout-engine |
| `canvas_balance` | visual weight spreads across the canvas | 5: balanced; 3: lopsided; 1: one empty half. Tag: `canvas_imbalanced` | YES (quadrant weight) | layout-engine |
| `quadrant_balance` | no quadrant is starved or overloaded | 5: even; 3: one heavy; 1: one empty + one packed. Tag: `quadrant_starved` | YES (quadrant weight) | layout-engine |
| `scale_plausibility` | relative object sizes match real-world scale | 5: scale reads true; 3: one oddity; 1: tube larger than instrument. Tag: `scale_inverted` | YES (scale-class inversions) | layout-engine |
| `cognitive_load` | the scene is not visually overwhelming | 5: calm; 3: busy but legible; 1: cluttered. Tag: `overloaded` | partial (count + density) | layout-engine |
| `whitespace_quality` | empty space frames rather than fragments | 5: purposeful; 3: uneven; 1: awkward gaps. Tag: `awkward_whitespace` | YES (largest empty rect) | layout-engine |
| `largest_void` | no single dead region dominates | 5: small voids; 3: one large void; 1: half the canvas empty. Tag: `large_void` | YES (largest empty rect) | layout-engine |
| `edge_breathing` | objects do not crowd the canvas edge | 5: even margins; 3: one tight edge; 1: object kisses edge. Tag: `edge_crowding` | YES (edge margin) | layout-engine |
| `visual_tangents` | object edges do not awkwardly align or touch | 5: none; 3: one tangent; 1: several. Tag: `visual_tangent` | YES (edge-alignment count) | layout-engine |
| `typography_consistency` | label size, weight, and style are uniform | 5: uniform; 3: minor drift; 1: mixed fonts/sizes. Tag: `typography_drift` | partial (font-size variance) | asset/author |
| `asset_finish` | artwork looks finished, not rough or stub | 5: polished; 3: serviceable; 1: rough/stub. Tag: `unfinished_asset` | NO | asset/author |
| `completeness` | no missing or partial artwork | 5: complete; 3: minor gap; 1: missing piece. Tag: `incomplete_asset` | partial (placeholder detect) | asset/author |
| `icon_style_consistency` | icons share one drawing style | 5: one style; 3: minor mix; 1: clashing styles. Tag: `icon_style_clash` | NO | asset/author |
| `color_role_consistency` | color encodes role consistently across objects | 5: consistent; 3: minor drift; 1: same color, different meaning. Tag: `color_role_clash` | NO | asset/author |

Render-bug findings are not 1-5 metrics; they are binary defects surfaced by the
integrity reviewer (placeholder art, cropped label, on-screen debug text,
misleading occlusion) and routed to the `render-bug` owner.

## Reviewer-subagent prompts

Five focused reviewer-subagents, each owning a slice of the catalog. Each reads
the scene PNG(s) with its own vision, scores its metrics 1-5, returns failure
tags, and stays read-only. The prompts below are verbatim and ready to dispatch.
Each dispatch supplies the scene name and the absolute PNG path(s) in place of
the bracketed placeholders.

### Prompt 1: hierarchy and reading path

```
You are an aesthetic reviewer for an instructional virtual-lab scene. Read the
rendered scene image(s) at [PNG_PATHS] for scene [SCENE_NAME]. Judge
instructional-illustration quality, not photorealism. You are read-only: do not
edit any file, do not propose code, only report.

Score these metrics 1-5 (5 best): focal_dominance, instructional_grouping,
workflow_logic. For each, give the score and one sentence of evidence from the
image. The scene should have one clear primary object the eye lands on first,
related objects grouped by workflow step, and a reading path (usually
left-to-right) that matches a lab protocol's order.

Return failure tags for any metric scored 1 or 2 from this set: no_focal_point,
no_workflow_logic, reading_path_broken. List concrete strong points and any
blocking findings. Tag every finding owner as layout-engine, asset/author, or
render-bug. Return strict JSON: {scores, strong_points, blocking_findings,
failure_tags}.
```

### Prompt 2: labels

```
You are an aesthetic reviewer for an instructional virtual-lab scene. Read the
rendered scene image(s) at [PNG_PATHS] for scene [SCENE_NAME]. Focus only on
labels. You are read-only: do not edit any file, do not propose code, only
report.

Score these metrics 1-5 (5 best): label_association_clarity,
typography_consistency. Also report label readability: is every label legible at
this size, free of clipping, and clearly attached to exactly one object? A label
must hug its intended object; floating or ambiguous labels are defects.

Return failure tags for any metric scored 1 or 2 from this set: label_detached,
typography_drift, cropped_label. The cropped_label tag is a render-bug. List
strong points and blocking findings. Tag every finding owner as layout-engine
(position), asset/author (text or font), or render-bug (clipping). Return strict
JSON: {scores, strong_points, blocking_findings, failure_tags}.
```

### Prompt 3: bench plausibility and grouping

```
You are an aesthetic reviewer for an instructional virtual-lab scene. Read the
rendered scene image(s) at [PNG_PATHS] for scene [SCENE_NAME]. Focus on physical
plausibility and workflow grouping. You are read-only: do not edit any file, do
not propose code, only report.

Score these metrics 1-5 (5 best): bench_plausibility, instructional_grouping,
scale_plausibility. Objects should sit where a real bench would put them, share
a believable baseline, group by workflow step, and have relative sizes that
match real-world scale (a tube must not be larger than an instrument).

Return failure tags for any metric scored 1 or 2 from this set:
implausible_placement, no_workflow_logic, scale_inverted. List strong points and
blocking findings. Tag every finding owner as layout-engine, asset/author, or
render-bug. Return strict JSON: {scores, strong_points, blocking_findings,
failure_tags}.
```

### Prompt 4: crowding, balance, whitespace

```
You are an aesthetic reviewer for an instructional virtual-lab scene. Read the
rendered scene image(s) at [PNG_PATHS] for scene [SCENE_NAME]. Focus on spatial
distribution. You are read-only: do not edit any file, do not propose code, only
report.

Score these metrics 1-5 (5 best): cognitive_load, canvas_balance,
quadrant_balance, whitespace_quality, edge_breathing, visual_tangents. The scene
should not feel cluttered, should spread visual weight across all quadrants,
should use empty space to frame rather than fragment, should keep objects off
the canvas edge, and should avoid awkward edge tangents between objects.

Return failure tags for any metric scored 1 or 2 from this set: overloaded,
canvas_imbalanced, quadrant_starved, awkward_whitespace, large_void,
edge_crowding, visual_tangent. List strong points and blocking findings. Tag
every finding owner; all of these are layout-engine. Return strict JSON:
{scores, strong_points, blocking_findings, failure_tags}.
```

### Prompt 5: integrity and finish

```
You are an integrity reviewer for an instructional virtual-lab scene. Read the
rendered scene image(s) at [PNG_PATHS] for scene [SCENE_NAME]. Hunt for defects,
not design opinions. You are read-only: do not edit any file, do not propose
code, only report.

Score these metrics 1-5 (5 best): asset_finish, completeness,
icon_style_consistency, color_role_consistency. Then scan for hard defects:
placeholder or fallback art, cropped or clipped labels, visible debug text on
the canvas, and misleading occlusion (an object hidden in a way that changes
what a student would conclude).

Return failure tags for any metric scored 1 or 2 from this set:
unfinished_asset, incomplete_asset, icon_style_clash, color_role_clash. For each
hard defect found, add a render_bug entry naming the defect and the affected
object. List strong points and blocking findings. Tag every finding owner as
asset/author (finish, style, color) or render-bug (placeholder, cropped, debug
text, occlusion). Return strict JSON: {scores, strong_points, blocking_findings,
failure_tags, render_bugs}.
```

## Synthesis JSON schema

A synthesis step merges the five reviewer returns into one per-scene verdict. The
synthesis is mechanical: it unions scores, tags, and findings, and routes each
finding to its owner bucket. It adds no new opinions.

```json
{
  "scene": "staining_bench",
  "overall": "clear | needs_review | weak",
  "scores": {
    "focal_dominance": 4,
    "label_association_clarity": 3,
    "bench_plausibility": 4,
    "instructional_grouping": 3,
    "workflow_logic": 3,
    "grounding": 5,
    "canvas_balance": 4,
    "quadrant_balance": 3,
    "scale_plausibility": 4,
    "cognitive_load": 3,
    "whitespace_quality": 3,
    "largest_void": 4,
    "edge_breathing": 4,
    "visual_tangents": 5,
    "typography_consistency": 4,
    "asset_finish": 4,
    "completeness": 5,
    "icon_style_consistency": 4,
    "color_role_consistency": 4
  },
  "strong_points": ["Primary instrument dominates the frame."],
  "blocking_findings": ["Two labels read as detached from their objects."],
  "review_required": ["label_association_clarity"],
  "failure_tags": ["label_detached"],
  "suggested_layout_actions": ["Move sample-tube labels to hug their tubes."],
  "suggested_asset_actions": [],
  "render_bugs": []
}
```

Rules for the schema:

- `overall` is `clear` when no failure tags fire, `needs_review` when only
  asset or layout tags fire, and `weak` when a render bug or multiple blocking
  findings fire.
- `suggested_layout_actions` lists only layout-engine-ownable actions.
- `suggested_asset_actions` lists only asset/author actions.
- `render_bugs` lists only render-bug defects.
- An action never crosses owners; the synthesis routes by the catalog owner tag.

## Scorecard v2 candidates

A subset of catalog metrics is bounding-box-automatable and can replace the
three placeholder metrics from the now-retired `tools/scorecard_m2.mjs` that
returned the hardcoded value 75: `support_distance`, `balance`, and
`region_filling`. These candidates compute from DOM bounding boxes, so they need
no vision call and can run in a future deterministic scorecard once calibrated.

| candidate | replaces / adds | computes from |
| --- | --- | --- |
| grounding / baseline coherence | adds grounding | spread of object bottom edges around a shared baseline band |
| gap-rhythm CoV | replaces `region_filling` | coefficient of variation of inter-object gaps along the reading axis |
| label-association ratio | adds label clarity | distance from each label to its nearest object vs second-nearest |
| edge margin | adds edge breathing | min distance from any object bbox to the canvas edge |
| largest-empty-rect | replaces `balance` | area of the largest axis-aligned empty rectangle vs canvas area |
| quadrant weight balance | replaces `support_distance` | variance of summed object area across the four quadrants |
| visual-tangent count | adds tangent check | count of near-coincident object edges within a small pixel band |
| scale-class inversions | adds scale plausibility | count of objects whose rendered size inverts their expected scale class |

These remain report-only until calibration shows each one tracks the
corresponding 1-5 reviewer score. Promotion to a weighted scorecard term follows
the same gate discipline as the rest of this spec: no numeric cutoff is
hand-picked before the distribution is known.

## Calibration and iteration loop

The review runs round-by-round. Each round is a single tight loop, and only one
engine-ownable action lands per round so its effect is measurable.

Round steps:

1. Render the scene set to PNGs with the read-only renderer.
2. Dispatch the five reviewer-subagents per scene; synthesize per-scene verdicts.
3. Rank `suggested_layout_actions` across scenes; pick the single highest-value
   layout-engine-ownable action.
4. Implement that one action in the layout engine.
5. Re-render the affected scenes.
6. Re-review with the same five prompts; synthesize again.
7. Compare before/after verdicts: scores, failure tags, blocking findings.

Guardrails for each round:

- No `Error` diagnostics in the render. A scene that renders with an error is
  fixed before its aesthetic verdict counts.
- No asset distortion. Aspect-ratio and clipping hard-fails from the existing
  scorecard still gate; an aesthetic gain that crops glassware is rejected.
- No convergence regression. An action that raises one scene's scores must not
  drop another scene below its prior verdict; if it does, revert and pick the
  next action.
- Re-baseline after each landed action. The new render becomes the baseline for
  the next round so deltas stay honest.

Calibration cadence mirrors the API reviewer: run when the loop is introduced,
re-run after milestones that change visual output, and re-run whenever the rubric
or the reviewer prompts change. Numeric gates are introduced only after the
reviewer scores and the bbox candidates agree across the calibration set.
