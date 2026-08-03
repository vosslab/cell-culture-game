# WP-F1 bottom-anchor scene-churn report

Plan: `docs/active_plans/` transient-spinning-snowglobe (WP-F1). This report records
the render churn from switching intra-row vertical placement from top-anchor to
bottom-anchor, and confirms every scene shift is explained by that change.

## What changed

`src/scene_runtime/layout/vertical_layout.ts` now bottom-anchors objects to a shared
shelf baseline instead of top-anchoring them:

- Old: `_top = rowTop` (offset by the label strip) with a per-object baseline
  back-solve. Objects in a tier row hung from the row top, so unequal-height objects
  had different bottom edges.
- New: every object in one shelf routes through `anchorTop()` so `_top = baseline -
  height`. A shelf is one `depth_tier` across the side-by-side zones authored at the
  same `top..bottom` (a horizontal row). Its shared baseline is
  `max(rowBottom - bottomLabelReserve, rowTop + maxObjHeight)`: the lowest row bottom
  in the shelf (so the tallest column defines the line), pulled up by any bottom-side
  label reserve, and floored so the tallest object's top stays inside its row
  (containment).

The named invariant (authoritative for the code and the WS-G doc): within a shelf
(one depth tier across side-by-side zones of a band), objects with `anchor_y: bottom`
(the default) share one common baseline, so their bottom edges land on a single line;
aspect is preserved and no artwork is cropped or clipped; the row/tier organization
(rear-at-band-top, one row per `depth_tier`) is unchanged.

Only the intra-row vertical anchor changed. Horizontal placement (`_centerX`,
`_visualWidth`), the reflow band/zone-merge logic (`reflow_zones.ts`), and label
resolution (`layout_labels.ts`) are untouched.

## Non-default anchor findings

- `anchor_y: bottom` (default): exercised by every bottle/instrument/plate. Bottom
  edge lands on the shelf baseline. This is the fix.
- `anchor_y: tip`: exercised only by the pipettes (`micropipette`, `p200`, `p10`,
  `aspirating`, `serological`, `multichannel`). Every one authors
  `anchor_y_offset: 0`, so `anchorTop` reduces to `baseline - height` -- the tip
  (object bottom) lands on the shelf exactly like a bottom anchor. A positive
  `anchor_y_offset` (none in content today) would hang the tip below the baseline by
  the offset; covered by a unit test.
- `anchor_y: top`: NO scene authors it. It is the engine fallback only (treated as a
  centered anchor). Behavior is covered by a unit test; not verified against a real
  scene because none exercises it.

## Content edit (label relayout)

`content/base_scenes/electrophoresis_bench.yaml`: removed a stale
`label_placement: bottom` override on `center_serological_pipette`. Its authored
comment placed the label below because the top label collided with `ddh2o_bottle`
"at obj_bottom 64" in the old top-anchored layout. Bottom-alignment moved
`ddh2o_bottle` to the scene bottom (`_top+_height` ~93.5), so that collision no
longer exists and the override instead forced the label down into
`front_left_mini_protean_gel`'s label (`unresolved_label_overlap`). Removing the
now-obsolete override lets the resolver place the label naturally and clears the
overlap for real (no gate suppression, no baselined overlap). The eight sdspage_*
workspace scenes `extends: electrophoresis_bench`, so this single edit propagated to
all of them.

## Churn scope

- All 34 scenes' vertical positions are regenerated under the new anchor.
- Scenes where every shelf (per authored-row group, per depth tier) holds exactly one
  object are byte-identical to the old placement (no alignment target).
- All other scenes shift to bottom-alignment: multi-object tier rows and side-by-side
  same-tier zones now share one bottom line.
- Every changed `_top`/`_baselineY` is attributable to the anchor change alone: the
  only code edit is the vertical anchor; `_centerX`/`_visualWidth` are unchanged
  (16:9 precompute-vs-live parity is field-for-field exact). No scene changed for any
  other reason.

## Verification snapshot (all 34 scenes)

| Signal | Result |
| --- | --- |
| `npx tsc --noEmit` | exit 0 |
| `./check_codebase.sh` | 5/5 PASS (typecheck, typecheck:lint, lint, format:check, test:node) |
| layout unit tests | 86/86 pass (includes rewritten bottom-alignment invariant tests) |
| `precompute_layout.mjs` build gate | emitted 34 scenes, 0 non-exempt build failures |
| `e2e_layout_parity_16x9` | GO 34/34, all_exact=true, sweep_ok=true |
| `e2e_generalization_preflight` | 34/34 D4-ready |
| object-overlap guard (all scenes) | 0 object overlaps in every scene |

Flagged (not a regression): `passage_hood_detachment_microscope_view` still raises 2
`failBuild` diagnostics, but it is a PRE-EXISTING member of `BUILD_GATE_EXEMPT_SCENES`
(intentional dense-by-design microscope view, M17/M19). The other exempt scenes
(`hood_basic`, `microscope_basic`, `hemocytometer_view`) report 0 build errors under
the new anchor. No scene became newly flagged by this change.

## Proof scenes

- `staining_bench`: the two-bottle shelf `coomassie_recycle_bottle` (rear_left tier 2)
  and `destain_waste_bottle` (rear_center tier 2) now share one bounding-box bottom
  line (`_top+_height` = 55.17 for both; old top-anchor had both tops at 38.77 with
  bottoms 52.44 vs 55.17). The rear tier-1 bottles (`coomassie_stain`, `destain`,
  `ddh2o`) likewise share bottom 29.1. Rendered PNG:
  `test-results/scenes/staining_bench.png`, 0 object overlaps.
- `electrophoresis_bench`: the center working-surface bottles
  (`ddh2o`, `electrode_module`, `p200`, `running_buffer_1x_carboy`) share bottom
  93.5; the rear shelf shares bottom 39.41 (tier 1) and 29.92 (tier 2); the front
  shelf shares bottom 54.61. Rendered PNG:
  `test-results/scenes/electrophoresis_bench.png`, 0 object overlaps, no gate error.

Note: the layout engine aligns object BOUNDING-BOX bottoms (its unit of control).
Residual differences in the visible glass bottom of a few bottles are SVG-internal
art padding (each bottle SVG places its art at a different fraction of its viewBox),
an asset-pipeline concern (SVG_PIPELINE), not a layout anchor concern.
