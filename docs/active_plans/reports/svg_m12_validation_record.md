# M12 validation record

## Current replacement-wave validation

Date: 2026-08-26.

The historical full-scene capture build completed successfully with 129 objects, 70 asset
specs, 135 SVG entries, 61 DOM-required assets, and 57 scenes. The later
recovered tree contained 134 SVG entries and 60 DOM-required assets. The final
ownership repair removed the full-cassette comb composite. The later MTT
ownership correction removed its material-specific vial, leaving 132 SVG
entries, 59 DOM-required assets, and 58 scenes. The second pass then deleted
four standalone lead cards and their two object definitions and added two
tank-coordinate connection overlays. The current build emits 127 objects, 67
asset specs, 130 SVG entries, 64 DOM-required assets, and 58 scenes. The
one-time built-consumer record is
[svg_m12_consumer_capture.md](svg_m12_consumer_capture.md), with machine facts
in [capture_facts.json](../../figures/svg_visual_quality_m12/capture_facts.json).

Six current 1920 x 1080 scenes, four visible-UI protocol states, and nine
grayscale copies were recorded. Full-scene and protocol console, page, request,
and render error arrays are empty. The independent cross-package visual review of the preceding tree
found no blocker or high issue. Its one medium tiny-scale lead-gap caveat was
then repaired: the unattached states now use a wider open gap with no dashed
pseudo-connection. A targeted independent card- and small-size re-review passed.
The second pass rejected that entire card model: cable connection is now
tank-owned state aligned to exact terminal geometry, with no standalone
unattached state.

Before renewed human assessment, an independent blind inspection also covered
the former 135 authored SVGs at 600 px and 180 px. Its source-only pass missed
the contextual logical and ownership defects later identified by the user; its
historical record includes an explicit human recognizability watchlist in
`docs/active_plans/reports/svg_all_asset_blind_inspection.md`.

That blind corpus and the human gallery render source SVGs as images. The later
built review in
`svg_m12_render_mode_review.md` closes the
separate E8 gap: all current 130 assets, including all 64 DOM-required forms,
passed the shared production host and per-instance ID namespacing path. It also
records the visible MTT powder-to-empty transition through one canonical
microtube asset, with an unchanged object box and hidden empty material region.

Direct detailed Servier water-bath geometry is confirmed for both bath states.
Gallery contract/docs/generator/dead-candidate-tool fixes, test-policy cleanup,
and microscope provenance correction are resolved. No added visual fixture,
screenshot, inventory, or browser-network check is a permanent test.

The final ownership check also proved the real three-step gel-cassette workflow
through visible clicks. The completed scene contains exactly one cassette and
one standalone comb, uses `gel_cassette_empty` plus `gel_comb`, reports no
degraded render or browser error, and no longer renders a second cassette in a
front-right comb slot. Lead connection state is now owned by the
electrophoresis tank; exact terminal subparts own learner targeting, while the
power supply owns voltage and running state only.

## Residual evidence boundary

The earlier 546 x 307 captures remain one-time compact evidence. A fresh
post-final-build compact attempt stalled on `bench_basic` before its ready
marker and screenshot, without a Playwright exception. Therefore compact
measurements were not freshly regenerated and are not reported as such.

## Final gates

| Gate              | Command                                          | Result                                                                         |
| ----------------- | ------------------------------------------------ | ------------------------------------------------------------------------------ |
| Current build     | Playwright production web-server build           | PASS: 127 objects, 67 asset specs, 130 SVGs, 64 DOM-required assets, 58 scenes |
| Content lint      | `python3 -m validation.yaml_schema.content_lint` | PASS: 244 YAML files; zero errors, warnings, or advisories                     |
| Python suite      | `python3 -m pytest tests/ -q`                    | PASS: 7,662 passed                                                             |
| Codebase gate     | `./check_codebase.sh`                            | PASS: all five gates; Node 675 total, 673 passed, 2 skipped                    |
| Browser suite     | `npx playwright test --reporter=dot`             | PASS: 113 passed                                                               |
| Current renderer  | one-time local production-host browser review    | PASS: 130 cards; 64 DOM, 66 image; zero failures or mismatches                 |
| Terminal workflow | visible-UI YAML walker                           | PASS: 3 of 3 steps; both wrong-sibling terminal probes rejected                |

## Historical record

The previous 2026-08-25 frozen-tree counts were valid for that older tree but
are not current replacement-wave validation. They remain historical technical
evidence only.
