# M12 shipping-render-mode review

## Scope

Date: 2026-08-26.

This is one-time implementation evidence for E8, not a permanent browser test,
fixture, snapshot, or network check. The built `dist/equipment_review.html`
page renders every entry from `generated/svg_manifest.ts` through the same
`SvgHost` component used by production `SceneItem` instances.

The page was served from `dist/` over an ephemeral loopback HTTP server. The
review driver was a temporary local script and was removed after capture.

## Exhaustive render-mode result

The second-pass built-page rerun covered all 130 manifest entries after the
standalone lead cards were replaced by two tank-coordinate connection overlays:

| Evidence                                   | Result |
| ------------------------------------------ | ------ |
| Inline DOM SVG                             | 64     |
| Opaque image                               | 66     |
| Expected/actual render-mode mismatches     | 0      |
| SVG load errors                            | 0      |
| Failed images                              | 0      |
| Namespaced inline IDs                      | 430    |
| Duplicate post-namespace IDs               | 0      |
| Invalid `preserveAspectRatio="none"` roots | 0      |
| Console, page, and request errors          | 0      |
| Wide and 390 px horizontal overflow        | 0 px   |

Search, render-mode filtering, light/dark/checker backdrops, card sizing, and
the narrow responsive control layout were exercised successfully. Screenshots
were temporary review evidence under `/private/tmp`; they are not repository
fixtures.

The rerun also asserted 130 declared entries, 130 cards, 64 inline-DOM hosts,
66 image hosts, zero load errors, zero failed images, zero expected/actual mode
mismatches, and no console, page, or request errors. Search and both render-mode
filters were exercised. The checker backdrop and 380 px card control worked,
and the 390 px viewport had zero horizontal overflow. The one-time temporary
review driver was removed after the pass.

## MTT state-transition proof

The real `mtt_reagent_prep.html` learner workflow was advanced with visible UI
clicks through the pipette pack, pipette, PBS bottle, solution tube, and MTT
powder microtube. No application state or renderer API was written directly.

Before transfer, the object rendered the canonical `microtube` through inline
DOM SVG with `material_name: mtt_powder`, `material_volume: 20`, and an 8 percent
fill. After the visible MTT click, declared state was
`{material_name: empty, material_volume: 0}` and the object still rendered
`microtube`. Its compiled liquid region had `display="none"`; no
material name, fill percentage, resolver degradation, scene degradation,
console error, page error, or failed request remained.

The outer placement box was exactly unchanged at 24.703125 x 69.734375 CSS px;
x, y, width, and height deltas were all 0. The asset name itself stayed
`microtube`; only the runtime material amount changed.

## Evidence boundary

This closes the exhaustive shipping-render-mode portion of E8. It complements,
rather than replaces, the six full-scene captures and visible learner-state
evidence in [svg_m12_consumer_capture.md](svg_m12_consumer_capture.md).
The build script permanently asserts that `dist/equipment_review.html` is
emitted, and existing scene tests exercise the shared host's image, inline-DOM,
and namespacing contracts. The review-only root and its search/filter controls
have no dedicated permanent browser test; their exhaustive browser exercise is
the one-time evidence above. This intentionally leaves review-page UI drift to
the build gate and human review instead of adding a mutable gallery test.
Human acceptance of the final artwork remains a separate decision.

## Historical renderer result

The preceding tree passed the same review with 132 cards: 59 inline DOM, 73
image, 429 namespaced IDs, and zero failures. Those counts remain dated evidence
for the tree before connection ownership moved from four standalone lead cards
to the electrophoresis tank.
