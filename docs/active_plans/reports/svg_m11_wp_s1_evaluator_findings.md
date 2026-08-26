# M11 WP-S1 visual evaluator findings

## Replacement-wave addendum (2026-08-26)

The approval below is historical evidence. The current safety repair rebuilt
the staining trays as rounded recessed vessels and softened inappropriate heavy
outlines across soft goods and safety equipment without changing semantic
anchors or material ownership. Package normalizer/render evidence, independent
cross-package review, and current M12 full-consumer evidence are complete.

Date: 2026-08-25

## Scope and decision

This is a fresh, source-and-consumer visual evaluation of the 17 SVGs assigned
to WP-S1 in [svg_batch_ownership_matrix.md](svg_batch_ownership_matrix.md#wp-s1-safety-containment-and-bench-support).
It checks the source against the M8 [equipment kit](../../figures/equipment_kit/README.md),
the M2 [provenance sweep](svg_servier_counterpart_sweep.md), and the M3
[size census](svg_visual_size_flatness_census.md). It does not approve unrelated
M11 packages or change an SVG, runtime code, or scene layout.

**Decision: APPROVED.** No visual blocker was found in the WP-S1 subgroup.

## Evidence inspected

### Observed facts

- `normalize_svg_v3.py` accepted every owned source on 2026-08-25. The output
  is in `/private/tmp/wp_s1_eval_normalized/`.
- A fresh `bash build_github_pages.sh` completed before consumer capture. It
  emitted the then-current 135 asset entries and 57 scenes.
- The actual built `scene_viewer.html` consumer rendered the four requested
  contexts without fallback or overlap: `hood_basic` (9/9), `staining_bench`
  (10/10), `cell_counter_basic` (7/7), and `electrophoresis_bench` (16/16).
  Each recorded zero render errors and zero overlap pairs. Screenshots are
  `/private/tmp/wp_s1_eval_hood.png`, `/private/tmp/wp_s1_eval_staining.png`,
  `/private/tmp/wp_s1_eval_cell_counter.png`, and
  `/private/tmp/wp_s1_eval_sds.png`.
- Standalone native SVG renders at ordinary inspection size, plus a small-scale
  contact check, are in `/private/tmp/wp_s1_standalone/`. These are review
  evidence only, not a second application surface.
- The M3 literal minima are materially smaller than ordinary inspection:
  decant 9.25 by 11.10 px, label pen 2.31 by 8.94 px, lens tissue 8.74 by
  5.96 px, towel 9.53 by 5.50 px, Kimwipe 12.22 by 8.15 px, and funnel 13.75
  by 19.86 px. The electrode module remains 43.76 by 29.17 px at its narrow
  scene and the tray remains about 45 by 63 px.

### Limitation

The first local browser launch was blocked by the macOS sandbox Mach-port
restriction. The identical production capture was retried with the necessary
local browser permission and succeeded; this report does not treat the failed
launch as a product observation. The four base-scene captures establish
consumer rendering and composite legibility, but do not walk every protocol
state. That is M12's connected interaction responsibility.

## Criterion findings

| Subgroup                            | Observed facts                                                                                                                                                                                                                                                                                                                    | Judgment                                                                                                                                                                                                                                                | Call     |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Electrode open/closed pair          | Both sources share shell, leads, feet, and recessed cassette geometry. Closed clamps cover the pale cassette; open clamps move laterally and expose the darker recess. The electrophoresis consumer preserves a recognizable compact module rather than an ambiguous flat box.                                                    | The state difference is physical occlusion and moving hardware, not color substitution. D04 is appropriate here: dark recess and near clamp contours describe a real depth relationship.                                                                | APPROVED |
| Hood dirty/clean pair               | Both render as the same cabinet: raised housing, back wall, sash/air cue, deck, and front grill. Dirty shows a localized brown spill and flecks; clean removes them and leaves a restrained wipe glint. `hood_basic` shows the whole cabinet, including the front grill, without clipping.                                        | D01 restraint is right for an embedded work surface. The state read is clear at normal size without fake heavy mass or a detached shadow.                                                                                                               | APPROVED |
| Five staining-tray lifecycle states | The five sources share one tapered tray, rim, side planes, liquid bounds, clip, and lower face. Empty has only the tray grid; buffer/water hold pale gel treatments; stain is substantially dark blue; destain retains a pale gel with two bands. In `staining_bench`, the tray is a legible primary object at about 45 by 63 px. | The five files carry independent gel-state evidence as well as contained-liquid treatment. Retaining them is the correct current ownership choice; a liquid-only migration would erase lifecycle information or require an unowned overlay abstraction. | APPROVED |
| Biohazard decant pair and sharps    | The upright decant has a lidded funnel and narrow stable body; the bin has a broad receiving rim/splash guard. Each has an exposed pale triangular trefoil over the liquid region. The sharps form has a yellow three-plane body, red top, and a visibly guarded, narrow slot/recess.                                             | Forms remain differentiated and recognizable. Hazard information has a shape cue as well as color. D04-like occlusion is limited to genuine openings and lids, not decorative dark striping.                                                            | APPROVED |
| Funnel and soft goods               | Funnel has an elliptical mouth, visible interior/light rim, tapered transparent cone, and stem. Kimwipe overlaps four uneven sheets around a soft central fold; lens tissue is one thin folded sheet; towel has stacked wavy layers. At their M3 minima, fine folds cannot be expected to identify the item independently.        | The family correctly avoids manufactured-instrument mass. Silhouette, face separation, selection treatment, and nearby semantic context carry recognition at literal minima, consistent with the kit rule.                                              | APPROVED |
| Label pen                           | Cap, labeled barrel, collar, and dark chisel tip form a readable full-size marker. At the 2.31 by 8.94 px M3 minimum it reduces to a colored vertical mark, as the census predicts.                                                                                                                                               | Appropriate D01 restraint and correct minimum-size strategy; do not add micro-detail to force standalone recognition at an impossible scale.                                                                                                            | APPROVED |
| Contours, palette, and composites   | Across the sources, pale near faces/highlights lead from upper-left; darker values identify receding side faces, openings, or overlap. The built hood, staining, cell-counter, and electrophoresis scenes show no visible detached floor shadow, clipping, or visual collision.                                                   | Coherent with the kit's selected D04 physical-relation direction moderated by D01 restraint. The palette makes containment, liquid, glass, paper, and safety forms distinct without relying on gratuitous gradients or fake depth.                      | APPROVED |

## Advisory notes

- The label pen and small paper goods necessarily become non-anatomical at their
  literal M3 minima. This is not a source-art defect: the M8 measured rule
  explicitly assigns identity at that scale to silhouette, selection treatment,
  and semantic context. Do not respond by accumulating sub-pixel strokes.
- The decant warning and tray lifecycle indicators are clear at their normal
  task placements. M12 should retain its planned real-protocol screenshots so
  active selection rings and learner guidance demonstrate the final practical
  handoff at the smallest context.

## Conclusion

WP-S1 delivers a coherent safety and bench-support family. The electrode pair,
hood pair, tray lifecycle family, containment forms, sharps container, funnel,
and soft goods make their intended physical distinctions without violating the
material/overlay ownership boundary or manufacturing false visual mass. The
subgroup is ready for M12 integration review.
