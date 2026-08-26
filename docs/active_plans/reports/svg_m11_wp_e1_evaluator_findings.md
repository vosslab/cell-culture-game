# M11 WP-E1 visual evaluation

## Replacement-wave addendum (2026-08-26)

The approval below is historical D01-D05 evidence. All 32 electrophoresis
assets were rebuilt as a coherent physical system with rounded transparent
tanks/chambers, seated cassettes, gel/comb relationships, leads, and power
components while preserving IDs, anchors, and state ownership. Normal and
minimum-size package renders, independent cross-package review, and current
M12 full-consumer evidence pass.

## Scope and method

This is a fresh visual evaluation of only the WP-E1 physical-system sources
listed in [svg_batch_ownership_matrix.md](svg_batch_ownership_matrix.md#wp-e1-electrophoresis-physical-system).
It does not evaluate WP-S1's electrode-module pair or WP-O1's cassette
fragments as owned source work.

I read the frozen [equipment kit](../../figures/equipment_kit/README.md), the
WP-E1 implementation record, M2's
[svg_servier_counterpart_sweep.md](svg_servier_counterpart_sweep.md), and M3's
[svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md). I
rendered every owned SVG with `rsvg-convert` at a reviewable standalone size,
then inspected the built `scene_viewer.html` and the shipped fill-tank,
assemble-module, and run-electrophoresis protocol pages at 1920 px and 320 px
viewports. Temporary screenshots remain outside the repository.

## Observed facts

- A structural review found that the earlier open/lidded tank sources did not
  share a stable physical form. The owner repaired both sources: their first
  ten fixed-geometry elements are now byte-identical, and the lidded source
  appends only a transparent physical lid, its rim, window, highlights, and
  handle.
- The inner four-form family keeps one tall, front-left chamber frame. Empty,
  partial, and filled forms differ through a contained blue volume, while
  `leak_checked` adds a visible green confirmation mark to the filled form.
- The outer four-form family has the same state logic in its wider reservoir
  frame. The partial and filled waterlines remain contained behind the front
  opening; its confirmation mark uses the same visual language as the inner
  family.
- The five cassette forms retain the same outer projection, ten dark well
  positions, and lane grid. Lifecycle evidence changes within that grid: pale
  empty gel, scattered bands, dense stained field, destaining field, and a
  pale destained field with retained bands.
- The open and lidded tank forms, mounted-module form, sealed/unsealed gel
  package, removed/inserted comb pair, and unseated/seated dam render as
  physical relationships. The attached lead forms close the visible connector
  gap; the power-supply pair changes the display/indicator rather than its
  enclosure.
- The built 1920 px fill-tank, electrode-module assembly, and run pages show
  the forms together without clipping. The run page shows both filled chamber
  forms, lidded tank, leads, power supply, cassette, and dam in one coherent
  camera and palette.
- M2 records direct Servier construction evidence for gel/cassette/comb forms,
  chamber-adjacent evidence for tank/chambers/dam/module, and bounded
  no-counterpart decisions for leads and power supply. M3 records real minimum
  placement widths down to 22--28 px for leads and dam, about 25--34 px for
  comb/package/tool contexts, and about 43--57 px for chamber forms.

## Findings

| Subgroup | Judgment | Finding |
| --- | --- | --- |
| Inner and outer chamber state families | APPROVED | Fill height, containing cavity, near rim, and leak-check are legible as different physical states. The check mark is additive verification, not a substitute for the full vessel state. |
| Gel-cassette lifecycle and lane registration | APPROVED | All five forms retain the cassette camera, well row, lane alignment, and right receding face. Gel changes stay inside the stable lane-bearing frame, so WP-O1 composites have a sound registration target. |
| Tank, mounted module, package, comb, and dam | APPROVED after repair | The repaired pair now has one stable tank housing and a true added lid. The open form exposes the mounted module; the lidded form preserves the same outer silhouette, terminals, base, and module position beneath a restrained transparent lid. Package, inserted comb, and seated dam still read as actual containment and overlap rather than recolorings. |
| Leads and power supply | APPROVED | Red/black polarity is immediately distinguishable. Connector reach makes the attached state physical; the on/off supply pair keeps a stable instrument housing with an appropriate display-state difference. |
| Fine tip, loading-tip boxes, and opening tool | APPROVED | At standalone and ordinary built-page sizes, the box matrix, long fine-tip silhouette, and flat opening lever remain identifiable without excessive interior strokes. At their M3 minima, they appropriately reduce to silhouette plus selection context. |
| Real SDS-PAGE consumers | APPROVED | The filled, assembly, and running views maintain one front-left, slightly elevated visual system. Deep values name real cavities, far planes, or overlaps; they do not turn the system into a striped or heavily shaded illustration. |

## Advisory observations

- At a 320 px browser viewport, the global bench layout compresses object labels
  and state-overlay pills into collisions. This is visible on both base-scene
  and protocol-page renders, but it is a responsive layout/label problem, not
  an ownership or visual defect in WP-E1's SVG sources. The literal M3
  placement evidence remains the relevant source-art lower bound.
- Some unrelated default object-state pills beneath the cassette are visually
  noisier than the cassette art at normal scene size. Keep any future cleanup
  in the renderer/overlay owner; do not put learner prose or state labels into
  the SVG.

## Tank-pair re-evaluation

The original tank-pair approval is superseded by this explicit repair check.
I rendered the repaired sources standalone at normal review size and at a
102 px width, which is below the M3 943 px viewport tank width of 109.39 px.
Both forms retain a crisp shared octagonal footprint, terminal polarity, and
interior-module location. The open form reads as an exposed apparatus; the
lidded form reads as that same apparatus viewed through a pale transparent
cover. The state distinction remains visible without a viewpoint, size, or
unrelated-body jump.

I also inspected rebuilt shipped consumers: `sdspage_attach_lid_and_leads`
shows the open tank with its mounted module before the lid action, and
`sdspage_run_electrophoresis` shows the lidded tank/module system during the
run. The module remains registered to the same central opening in both views;
the lid does not float, crop the body, or introduce a competing camera. At the
M3-sized base-bench rendering, the small tank still resolves as the same
instrument through silhouette, terminal dots, and the pale lid plane.

## Decision

**WP-E1: APPROVED after tank-pair repair.** No remaining visual blocker was
observed in the owned physical sources or their current SDS-PAGE consumers.
The repaired open/lidded tank family now meets the stable-state-frame
requirement that the original review missed. Preserve the discrete chamber
family and stable cassette registration through M12. The responsive label
collisions should be carried as an integration advisory rather than reopening
this approved SVG package.

## Limitations

- This review did not mutate a shipped protocol through every interaction;
  it inspected the built initial states and the complete standalone state
  families. The visible UI walkthrough remains an M12 acceptance obligation.
- The 320 px screenshots establish the responsive-layout advisory, not a new
  minimum-size visual contract. The authoritative source-art minima are the
  actual placement measurements in
  [svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md).
