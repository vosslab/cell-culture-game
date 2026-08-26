# M10 WP-H1 visual evaluator findings

## Replacement-wave addendum (2026-08-26)

The approval below is historical evidence. The variable-volume tool repair
retains detailed direct Servier geometry for P10 and multichannel pipettes,
while the other tools are controlled rounded physical adaptations. Independent
review required the multichannel to show eight separate tapered tips rather
than a box-like bank; that repair passed re-review at normal and minimum sizes.
No new visual fixture or permanent test was added. Independent cross-package
review and current M12 full-consumer evidence now pass.

Date: 2026-08-25

## Final decision

**APPROVED.** The re-review confirms that the owner corrected the only visual
blocker in the first evaluation: material paint is now visible through the
physical tip, barrel, cartridge, or eight-channel bank, without recoloring a
fixed tool housing. P200 is now included in the same compiled browser fleet.

## Evidence inspected

- The frozen [kit measurements](../../figures/equipment_kit/MEASUREMENTS.md),
  [M4 micropipette board](svg_reference_board_micropipette.md), and [M2
  provenance ledger](svg_servier_counterpart_sweep.md).
- Current object YAML, the eight variable-volume sources, and both
  serological-pipette-pack source states.
- Fresh normal-size standalone renders of every owned source.
- The frozen-tree Chromium acceptance run reported by the manager: `npx
  playwright test tests/playwright/test_liquid_render.spec.ts`, 3 passed.
  I directly inspected its current original-resolution matrices for aspirating,
  multichannel, P10, P20, P200, P1000, repeat, and serological tools. Each
  matrix includes empty through full levels in `#076dad`, `#c2015a`, and
  `#5a8f20`.

## Observations

- The repaired P10, P20, P1000, aspirating, and multichannel fixed fronts use
  transparent disposable/barrel faces; repeat removes only the former opaque
  cartridge-covering fill while retaining its rim, graduations, and outline.
- In every reviewed browser matrix, empty is visually empty and blue, magenta,
  and green partial/full states progress in a contained region. The fixed shell,
  collar, plunger, and control geometry remain stationary and neutral.
- P200 now has a compiled matrix. Its thin contained-tip fill is visible at
  partial and full levels in all three colors; it remains distinct from the
  P20's narrower/yellow-capped and P1000's broader/blue-grey-capped forms.
- The available/depleted pack shares one oblique carton construction. Six loose
  pipettes identify the available state; their absence identifies depletion.

## Per-form decisions

| Form | Decision | Criterion-specific finding |
| --- | --- | --- |
| P10 micropipette | APPROVED | Slender low-volume form, green cap, display, collar, sleeve, and pointed tip remain readable. Blue/magenta/green fill is visible only in the tip and increases with volume. |
| P20 micropipette | APPROVED | Yellow-capped narrow micropipette reads as the small-capacity sibling. Its transparent tip face now visibly carries contained color/level without altering the body. |
| P200 micropipette | APPROVED | The strongest single-channel construction: shallow rear plane, recessed display, orange collar, overlapping sleeve, and broad tip provide D04 volume with D01 restraint. Its newly included browser matrix proves contained tip fill in every requested state/color. |
| P1000 micropipette | APPROVED | Wider housing, broad plunger, and broad bore provide a capacity-specific large-volume read. Material is visibly restricted to the transparent tip. |
| Aspirating pipette | APPROVED | Bulb, long glass barrel, and pointed outlet are recognizable. The matrix visibly fills only the barrel, preserving the fixed bulb as a physical control. |
| Multichannel pipette | APPROVED | The wide head and eight aligned dispensing bores are immediately recognizable. Matrix states visibly fill the bank while retaining bore separation and fixed-head identity. |
| Repeat dispenser | APPROVED | Cartridge, trigger/body, and outlet are readable. The physical cartridge now visibly shows the full cool/warm/green progression behind retained outline and graduation cues. |
| Serological pipette | APPROVED | Glass barrel, cap, graduations, and taper remain legible; all three colors progress visibly in the barrel with no fixed-housing recolor. |
| Serological-pipette pack, available | APPROVED | The oblique carton plus six loose pipettes reads as stocked sterile consumables, not a liquid state. |
| Serological-pipette pack, depleted | APPROVED | The identical carton with loose pipettes absent creates an unambiguous stock-depletion state. |

## Scene-context judgment

The current placements remain appropriate: hood puts aspirator and serological
pipette in the right tool area; electrophoresis pairs P200 with a serological
pipette; and the plate/dilution workspace separates multichannel, repeat
dispenser, and tip box by depth/alignment. The reviewed silhouettes and now
visible contained material communicate those tool roles without relying on a
body recolor.

## Advisory follow-up

P10 and P20 are intentionally close family siblings. Their cap color, narrow
tool proportions, display/collar construction, and the explicit object labels
make the distinction adequate at this stage, but a later consumer-scale review
should retain the present capacity cues rather than simplifying them further.

## Limitation

My local final Playwright attempt was blocked by a transient macOS Chromium Mach
rendezvous permission denial after its pure math test. The manager supplied the
frozen-tree 3/3 browser run and current saved matrices; I directly inspected
those artifacts. This is valid compiled inline-SVG state evidence, while the
separate M12 consumer review still owns final in-scene screenshots.
