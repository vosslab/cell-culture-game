# M9 WP-C1 visual evaluator findings

## Replacement-wave addendum (2026-08-26)

The approval below is historical D01-D05 evidence, not current art-direction
approval. This package was rebuilt and re-reviewed for physically credible
vessels and labware: the hinged microtube was corrected away from an unrelated
Falcon-like cone, and the reservoir retains a real cavity and contained state.
The later MTT correction deleted its material-specific vial entirely: both MTT
states select the canonical microtube, while generic mass-capacity rendering
shows 20 mg at 8 percent of its 250 mg authored capacity. The runtime microtube
calibration removed arbitrary 8/92 percent clamps and restores a 35.98 percent
body start. Its material behavior remains covered by durable semantic/runtime
tests; the renders used to confirm this repair are one-time evidence.

## Decision

WP-C1 is **APPROVED**. The previously missing balance-tube consumer evidence is
now present in successful full and compact `centrifuge_workspace` captures.

| Subgroup                   | Owned sources                                                      | Decision                       | Reason                                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Balance tube               | `centrifuge_balance_tube_empty`, `centrifuge_balance_tube_matched` | APPROVED                       | Full and compact real consumer captures show the stable tube shell in context.                                                                    |
| Hazardous waste            | `hazardous_liquid_waste_empty`, `hazardous_liquid_waste_filled`    | APPROVED                       | Recognizable carboy, stable shell, contained state change, and real bench consumer evidence.                                                      |
| MTT microtube              | canonical `microtube` for both states                              | CURRENT MODEL                  | Material identity and amount paint or hide the contained MTT without selecting a second vessel SVG.                                                |
| Reagent reservoir          | `reagent_reservoir_empty`, `reagent_reservoir_filled`              | APPROVED                       | Shallow basin, near wall, receding right face, and contained fill survive the intended scene use.                                                 |
| Canonical material vessels | `bottle_medium_pink`, `falcon_50ml`, `microtube`                   | APPROVED                       | Direct-root material forms preserve their physical shells and pass the real browser liquid matrix.                                                |

## Evidence reviewed

I read the frozen [equipment kit](../../figures/equipment_kit/README.md), its
[measurements](../../figures/equipment_kit/MEASUREMENTS.md), the WP-C1
[implementation record](svg_m9_wp_c1_reference_and_implementation.md), the M1
[inventory](svg_visual_quality_inventory.md), M2
[counterpart sweep](svg_servier_counterpart_sweep.md), and M3
[size census](svg_visual_size_flatness_census.md). The historical pass inspected
the then-owned eleven source SVGs; the current package owns ten after deleting
the material-specific MTT vial.

The historical source inspection used fresh 512 px standalone renders and exact source XML.
The real-consumer inspection used a fresh production build and the actual
`tools/scene_to_png.mjs` renderer at 1920 by 1080. The following consumer scenes
were populated, with no render errors:

- `mtt_reagent_prep_bench_workspace` (10 of 10 placements)
- `sdspage_recycle_buffer_workspace` (6 of 6 placements)
- `plate_drug_treatment_media_adjustment_plate_workspace` (6 of 6 placements)
- `bench_basic` (9 of 9 placements)
- `cell_counter_basic` (7 of 7 placements)

The initial `centrifuge_workspace` capture was transiently `load-failed` during
concurrent production-build churn. A frozen-tree escalated Chromium retry then
rendered all 15 of 15 placements with zero render errors and zero overlap pairs
at both 1920 by 1080 and 546 by 307. The evidence PNGs are
`/private/tmp/svg_m9_c1_centrifuge_workspace.png` and
`/private/tmp/svg_m9_c1_centrifuge_workspace_min.png`. At the compact frame the
balance tube is necessarily silhouette-level, which agrees with its measured
3.85 by 9.42 px minimum art box; its state and object role remain clear in the
larger scene composition. Crowded global labels at that compact frame are an M12
layout advisory, not a WP-C1 asset defect.

The real Chromium material matrix also passed:

```text
npx playwright test tests/playwright/test_liquid_render.spec.ts --reporter=line
3 passed
```

It instantiates `bottle_medium_pink`, `falcon_50ml`, and `microtube` through the
compiled runtime at 0, 5, 10, 25, 50, 60, 75, 85, 90, and 100 percent with cool
blue, warm magenta, and green material colors. It verifies stationary clipping,
semantic paint roles, contained gravity parts, and the tapered microtube regime.
That is stronger evidence than the static source colors.

## Observations

### Recognition and volume

- The balance-tube pair has a narrow capped rim, clear tapered tube, three sparse
  graduations, a white near highlight, and a narrow right receding face. The
  matched state changes only the blue liquid below its curved meniscus. This is
  a stable shell and a restrained D04/D01 depth cue, not a differently drawn
  state.
- The waste pair reads as a closed handled carboy before its detail is read. The
  dark hose connection, cap, front hazard placard, and right-side attached panel
  identify the intended waste form. The magenta liquid remains within the inner
  body and below the shoulder, label, and cap.
- The MTT states use one open hinged-cap microtube construction. The powder
  state renders a small yellow bed through the canonical material region; it does
  not paint over the transparent near body. Its cap, rim, taper, and side face are clear
  at its approximately 36 by 102 px normal placement. At the 9 by 26 px minimum,
  the intended surviving cue is the microtube silhouette and powder-versus-empty
  state, not the individual hinge construction.
- The reservoir has a useful shallow-trough silhouette: lit far rim, visible
  inner basin, near wall, and a dark right receding face. The filled state places
  a blue liquid plane inside that basin, with the near wall still in front. It
  is deliberately sparse at its roughly 79 to 112 px normal width; that is the
  appropriate D01 restraint rather than flat decorative striping.
- `bottle_medium_pink` reads as a broad-shouldered reagent bottle with a true
  cap cylinder, clear fixed shell, and a contained material surface. `falcon_50ml`
  retains cap, neck, cylindrical body, graduation field, right far face, and
  continuous cone. `microtube` retains the open hinged cap, rim, transparent
  body, and tapered bottom. Their fixed geometry is distinct from material paint.

### Context coherence

The populated scenes place the reviewed forms coherently with the selected kit:
the MTT tube is legible in reagent preparation, the reservoir remains a shallow
bench/hood accessory rather than a flat label, and the material bottle/tube
forms share the upper-left light, pale front planes, and restrained dark far
planes of the centrifuge and other bench equipment. In the cell-counter and
bench consumers, their smallest placements are understandably silhouette-led;
the runtime preserves the larger interaction core rather than attempting to
make sub-pixel graduations readable.

## Blocking and advisory findings

### Advisory follow-up

The implementation record says the two hazardous-waste SVGs need a concise
repository-authored/no-Servier row in `assets/equipment/SOURCES.md`. That is a
provenance-documentation follow-up, not a visual acceptance blocker: the M2
sweep already records that the local Servier corpus has no corresponding waste
vessel.

## Conclusion

All WP-C1 subgroups satisfy the reference-backed anatomy, D04-with-D01 volume,
stable state shells, containment, source-size simplification, and real-consumer
coherence required by M9. The package is approved without source redesign.
