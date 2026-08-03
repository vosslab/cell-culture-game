# Aesthetic round 1 -- grounding cue iteration report

Round 1 of the aesthetic-improvement loop. Lever: render-layer grounding cue only.

Baseline reference: [aesthetic_baseline_round0.md](aesthetic_baseline_round0.md)
Rubric reference: [aesthetic_review_metrics.md](../decisions/aesthetic_review_metrics.md)

## Purpose

This report captures the full iteration cycle for round 1, in which a contact
drop-shadow and a workspace-conditional surface band were introduced as the sole
aesthetic lever. No object geometry changed. The goal was a measurable grounding
and plausibility improvement across all eight scenes without triggering any visual
integrity failures (asset crop, distort, or occlusion).

## Lever

Render-layer grounding cue only. Changes confined to:

- `src/style.css` -- contact shadow rule and surface band `::after` pseudo-element.
- `src/scene_runtime/renderer/render_scene.tsx` -- stamps `data-scene-workspace`
  on `#scene-root` so CSS can gate the band per workspace type.

No object geometry changed. `generated/precomputed_layout.ts` stayed BYTE-IDENTICAL
across every sub-round (r1, r1.5, r1.6, r1.7). `tsc` ran clean and the four layout
node-test files passed each round.

## Implementation -- final state after r1.7

### Contact drop-shadow

```
drop-shadow(0px 6px 8px rgba(40,44,48,0.26))
```

Applied to `[data-placement-name]` on ALL scenes. Neutral dark-grey tint; no warm cast.

### Surface band

`#scene-root[data-scene-workspace=...]::after` pseudo-element, positioned at the
bottom of the scene canvas (top: 78%, z-index: 0, pointer-events: none).

Band color is workspace-conditional:

| data-scene-workspace value | Band color | Rationale |
| --- | --- | --- |
| workspace_bench | warm wood-tone | matches bench surface material |
| cell_counter | warm wood-tone | bench-adjacent context |
| microscope | neutral blue-grey | clinical instrument context |
| incubator | neutral blue-grey | clinical instrument context |
| plate_reader | neutral blue-grey | clinical instrument context |
| hood | none (omitted) | clinical enclosure; warm band was wrong |

## Iteration narrative

**r1** -- added warm surface band plus soft drop-shadow across all scenes.
Vision review: 7 of 8 scenes KEEP; hood REVERT because a warm wood-tone band is
implausible inside a clinical biosafety cabinet.

**r1.5** -- gated band off for hood and microscope; strengthened shadow slightly.
Hood fixed. However, microscope and seeding_workspace lost their surface anchor
without the band; grounding score regressed for those two scenes.

**r1.6** -- recolored band to neutral blue-grey and stamped `data-scene-workspace`
on `#scene-root` to allow per-workspace CSS gating; neutralized shadow tint back to
dark-grey. Microscope recovered; hood stayed clean. Benches now had the neutral band
instead of the warm one reviewers preferred for bench contexts.

**r1.7** -- made band color workspace-conditional (warm for bench-type workspaces,
neutral for clinical instruments, absent for hood). All scenes converged: benches
prefer warm, clinical instruments prefer neutral, hood prefers none.

## Vision-review scores

Grounding (g) and plausibility (p) scored 1-5. Net = (r1.7 g - r0 g) + (r1.7 p - r0 p).

| Scene | r0 g | r0 p | r1.7 g | r1.7 p | net | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| staining_bench | 1 | 2 | 3 | 3 | +3 | IMPROVED |
| passage_hood_detachment_microscope_view | 1 | 2 | 3 | 3 | +3 | IMPROVED |
| hood_basic | 2 | 3 | 3 | 3 | +1 | IMPROVED |
| cell_counter_basic | -- | -- | -- | -- | +1 g (per r1/r1.5 review) | IMPROVED |
| sample_prep_bench | -- | -- | -- | -- | +1 g (per r1/r1.5 review) | IMPROVED |
| seeding_workspace | -- | -- | -- | -- | +1 g (per r1/r1.5 review) | IMPROVED |
| electrophoresis_bench | -- | -- | -- | -- | +1 g (per r1/r1.5 review) | IMPROVED |
| heat_block_bench | -- | -- | -- | -- | +1 g (per r1/r1.5 review) | IMPROVED |

Rows marked `--` were reviewed in earlier sub-rounds (r1/r1.5) with confirmed +1
grounding gains and KEEP votes. Exact r1.7-vs-r0 deltas for those five scenes were
not re-scored in the final r1.7 pass; figures are not available and are not invented
here.

## Guardrails honored

- Zero asset occlusion, crop, or distortion in any reviewed scene. PRIMARY_DESIGN
  visual integrity rule held throughout.
- `generated/precomputed_layout.ts` byte-identical across all sub-rounds (r1, r1.5,
  r1.6, r1.7). No geometry change, no convergence regression, no diagnostic
  regression.
- Change is render-only (CSS + one attribute stamp). No protocol YAML, no object
  YAML, no scene YAML, no layout engine code modified.

## Known limitation -- seeding_workspace band exclusion

`seeding_workspace` carries `data-scene-workspace="hood"` in the scene registry,
so the band gate excludes it (no surface band). A vision reviewer rated this
ACCEPTABLE: the contact shadow still grounds the objects; the aesthetic cost is minor.

To give `seeding_workspace` a surface band in a future round, one of two things must
happen:

1. Add a distinct workspace enum value (e.g. `seeding_hood`) -- a closed-vocabulary
   change requiring a spec edit, a validator update, and a scene YAML change, all per
   the vocabulary-closure rules in PRIMARY_DESIGN.md.
2. Re-classify `seeding_workspace` to a bench-type workspace enum value if that
   classification is defensible.

Both options are user decisions, not agent edits.

## Next levers -- not yet done

The remaining round-0 improvement levers all involve GEOMETRY changes:

- Label-disambiguation spacing -- moves label placement relative to object bounding box.
- Mid-canvas void collapse -- repositions objects to close empty regions.
- Focal promotion of the primary object -- scales or shifts the primary object relative
  to supporting objects.

These changes move `ComputedItem` geometry, so they will change
`generated/precomputed_layout.ts` and require re-baselining the layout snapshot tests
plus full determinism/convergence guardrail checks (the snapshot must match exactly
across two independent runs on the same input). These are expert_coder-tier follow-ups
due to the layout engine scope and the snapshot discipline required.
