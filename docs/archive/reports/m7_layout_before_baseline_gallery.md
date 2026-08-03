# M7 layout before-baseline gallery

Pre-change baseline screenshots for the approved layout-engine plan
(`partitioned-shimmying-dragonfly`). These eight images fill the "before
evidence" column of the M7 scene-by-scene evidence table. They capture the
current (pre-layout-change) rendered state so later layout improvements can be
compared visually.

- Date captured: 2026-06-08
- Tool used: `tools/scene_to_png.mjs` (read-only, run per scene)
- Viewport: 1920x1080 (16:9); PNGs clipped to the `#scene-root` content bbox
  (about 1888x1062), per the tool's standard crop behavior
- Output directory: `test-results/m7_before_baseline/` (gitignored)
- Build used: existing `dist/` (no rebuild performed)

All eight scenes rendered as category `populated` with no load failures.

## Baseline images

| Scene | Image path | Notes from render stats |
| --- | --- | --- |
| cell_counter_basic | `test-results/m7_before_baseline/cell_counter_basic.png` | populated |
| staining_bench | `test-results/m7_before_baseline/staining_bench.png` | populated |
| sample_prep_bench | `test-results/m7_before_baseline/sample_prep_bench.png` | populated |
| hood_basic | `test-results/m7_before_baseline/hood_basic.png` | populated |
| seeding_workspace | `test-results/m7_before_baseline/seeding_workspace.png` | populated; 7 overlap pairs, ~53% empty |
| electrophoresis_bench | `test-results/m7_before_baseline/electrophoresis_bench.png` | populated; 2 placeholders, ~84% empty |
| heat_block_bench | `test-results/m7_before_baseline/heat_block_bench.png` | populated; ~91% empty |
| passage_hood_detachment_microscope_view | `test-results/m7_before_baseline/passage_hood_detachment_microscope_view.png` | populated; 2 overlap pairs |

## Reproduce

Render any one scene to a fresh 16:9 PNG (requires a built `dist/`):

```bash
node tools/scene_to_png.mjs --scene hood_basic --png \
	--out test-results/m7_before_baseline/hood_basic.png --viewport 1920x1080
```

Machine render stats for each scene are written to
`generated/scene_render_stats/<scene>.stats.json` by the same tool.
