# M8 same-tier object overlap evidence

Evidence note for the deferred milestone M8 (same-depth-tier object de-overlap) of the
compile-time layout-engine plan (`partitioned-shimmying-dragonfly`). M8 is evidence-gated:
it should land only if real same-`depth_tier` overlaps between authored assets exist and
harm composition. This note records the evidence gathered during M7 closeout.

- Date: 2026-06-08
- Method: join each scene's rendered `visual_bbox` set
  (`generated/scene_render_stats/<scene>.stats.json`) with the per-placement `depth_tier`
  from `generated/scenes.ts`, compute AABB overlaps, and classify each overlapping pair as
  SAME-tier (M8 candidate) or cross-tier (authored z-layering, expected and preserved).
- Scenes scanned: the eight M7 named scenes.

## Result

| scene | overlapping object pairs | classification |
| --- | --- | --- |
| cell_counter_basic | none | -- |
| staining_bench | none | -- |
| sample_prep_bench | none | -- |
| hood_basic | center_hood_surface(t2) x center_well_plate_96(t3); center_well_plate_96(t3) x right_aspirating_pipette(t1) | both cross-tier (z-layering) |
| seeding_workspace | center_hood_surface(t2) x center_serological_pipette(t2) ~3364 px2; center_vortex(t3) x center_well_plate_96(t3) ~257 px2 | two SAME-tier, both involving a placeholder or surface object |
| electrophoresis_bench | none | -- |
| heat_block_bench | none | -- |
| passage_hood_detachment_microscope_view | left_cell_suspension(t2) x left_microtube_rack(t1) | cross-tier (z-layering) |

## Same-tier findings in detail

Only `seeding_workspace` shows any same-tier object overlap, and neither pair is a genuine
real-asset same-tier collision that harms composition:

- `center_hood_surface` x `center_serological_pipette` (~3364 px2): `center_hood_surface`
  is a large bench-surface object whose real SVG (`hood_surface`) is missing and rendered as
  a default-sized placeholder box (it is in the scene's `missing_object_names`). A bench
  surface is conceptually a backdrop the pipette sits on; the overlap is an artifact of the
  placeholder box, not two foreground assets fighting for the same space.
- `center_vortex` x `center_well_plate_96` (~257 px2): `center_vortex`'s real SVG (`vortex`)
  is also missing and rendered as a placeholder box. The overlap is ~257 px2 -- a tiny corner
  clip, roughly 0.01% of the 1920x1080 frame -- well inside visual noise.

All other overlaps across the eight scenes are cross-tier, which the engine intentionally
preserves as authored z-layering (`DEPTH_BASELINE_OFFSET`); they are not M8 targets.

## Verdict: is M8 warranted by evidence?

NO -- M8 is not warranted by the current evidence.

- There is zero genuine same-tier overlap between two real (non-placeholder) foreground
  assets in any of the eight scenes.
- The only two same-tier overlaps both involve a missing-asset placeholder box; one is a
  bench-surface backdrop and the other is a ~257 px2 corner clip.
- Both will most likely disappear once the real `hood_surface` and `vortex` SVGs are
  supplied (a separate author/asset task), since the placeholder boxes use default sizing
  rather than the assets' true footprints.

Recommendation: keep M8 deferred. Re-evaluate only after the missing real assets land; if a
real same-tier overlap between two foreground assets then appears and harms composition, open
the M8 evidence note (WP-OBJ1) at that point. Cross-tier overlaps stay as authored z-layering
and are out of M8 scope by design.
