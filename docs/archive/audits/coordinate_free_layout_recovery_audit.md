# Coordinate-free layout recovery audit

## Verdict

The current scene format is coordinate-free only for individual placements.
Authors still assign every zone a percentage rectangle and usually a baseline.
Those fields make a zone an author-sized box rather than a semantic grouping.
The durable repair is to preserve zones while moving all zone geometry into the
layout manager.

The numeric zone edits made while investigating the plate-focus scene were
reverted. A wider rectangle can silence one capacity diagnostic, but it leaves
the author-facing coordinate system in place and moves the next failure to a
different scene.

## What the history actually says

The first April layout-engine design removed coordinates from each `SceneItem`,
but retained fixed `x0`, `x1`, and `baseline` fields on each zone. Numeric zone
geometry first appeared on April 9, 2026, in commit `7ea2c5e`. See
[2026-04-09-scene-layout-engine-design.md](../../archive/2026-04-09-scene-layout-engine-design.md).
That design was coordinate-free at the item layer, not at the scene-authoring
layer.

The current YAML rectangle form appeared on May 15, 2026, in commit `738bcc1`.
That refactor explicitly replaced `x0`, `x1`, and `baseline` with
`bounds.left`, `bounds.right`, `bounds.top`, and `bounds.bottom`. It changed the
spelling and expanded the rectangle, but did not transfer geometry ownership to
the manager.

The later activation hold identified this as a vocabulary-closure defect:
every base scene could invent another coordinate grid, preventing the manager
from enforcing a shared workspace policy. Its row-and-slot proposal is useful
evidence for engine-owned geometry, but it does not require replacing the
existing zone abstraction. See
[scene_runtime_activation_on_hold.md](../../archive/plan-reset-2026-05-22/scene_runtime_activation_on_hold.md).

The subsequent row-and-slot prototype established the useful authoring idea,
but its reported success was not trustworthy:

- The gallery converted rows to fixed rectangles inside the test and drew
  placeholder boxes instead of exercising the generated catalog, loader,
  object library, SVG renderer, or interaction runtime.
- The comparison report called the prototype green while also reporting that
  one hood placement was missing.
- Protocol-scene inheritance still required `scene_bounds`, `zones`, and flat
  `placements`.
- The row-and-slot layout function was exported but had no production or test
  caller.
- It created one equal-width fixed zone per slot and hard-coded row positions,
  so it moved coordinates rather than designing an object-aware manager.

The archived reports remain useful archaeology, not acceptance evidence:
[row_slot_base_scene_prototype.md](../../archive/scene_runtime/row_slot_base_scene_prototype.md)
and
[row_slot_prototype_comparison.md](../../archive/scene_runtime/row_slot_prototype_comparison.md).

## Current failure that exposed the defect

The MTT incubator scene has no final rendered item overlap. Its failure came
from an authored center zone that was narrower than the incubator's minimum
layout footprint after internal padding. The packer correctly reported that
the item could not fit its assigned rectangle, even though the neighboring
rendered objects did not collide.

This is useful evidence against another coordinate tweak. The engine should
allocate row space from the actual object footprints and the available scene
surface. An author should not decide whether an incubator deserves an
eight-unit or sixteen-unit rectangle.

## Recovery model

The durable source model is:

1. A scene declares an ordered list of semantic zones. A source zone has a
   stable `zone_name` and, optionally, a human-readable label; it has no
   rectangle, baseline, alignment number, or size.
2. Flat placements retain stable `placement_name`, `object_name`, and `zone`
   membership. Existing protocol targets and inheritance therefore keep their
   identity seam.
3. The TypeScript layout manager measures the assigned objects and labels,
   plans internal workspace bands and alignment groups, and lowers semantic
   zones into computed geometry before placement.
4. Internal rows, lanes, bounds, and baselines are manager implementation
   details. They are not a second authoring schema and are never emitted back
   into content YAML.
5. Source YAML does not contain `scene_bounds`, background bounds, zone
   rectangles, baselines, raw coordinates, or numeric scale fixes.
6. Temporary legacy-coordinate input may remain readable during an incremental
   migration, but validation rejects coordinates in every migrated or newly
   authored scene.
7. Protocol-scene inheritance and target resolution operate on semantic zone
   membership and stable placement identity before any geometry exists.
8. The focused 96-well plate belongs to a foreground teaching zone. Its
   supporting supplies remain in secondary semantic zones; perspective and
   object-aware scale come from shared engine policy, not a hand-widened plate
   rectangle.

Internal computed bounds remain necessary renderer output. Coordinate-free
authoring does not mean a renderer has no coordinates; it means authors never
write or tune them.

## Required proof

The replacement is accepted only when all of these agree:

- Source validation rejects authored geometry and unknown semantic zones.
- Scene generation preserves every stable placement identity.
- Protocol inheritance adds, removes, deactivates, and moves placements without
  referring to numeric geometry.
- The real build-time layout pipeline consumes semantic-zone scenes and produces
  deterministic internal geometry.
- Structural guards and diagnostics inspect that same normalized geometry.
- A built browser scene renders the real SVG instruments and materials.
- Visible UI clicks resolve to the same protocol targets after migration.
- The ordinary bench and focused 96-well plate scenes pass object-overlap,
  clipping, label, and visible-interaction checks.

Counts, placeholder galleries, fabricated performance reports, and synthetic
DOM clicks are not substitutes for those behaviors.
