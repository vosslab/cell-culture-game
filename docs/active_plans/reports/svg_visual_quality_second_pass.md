# SVG visual-quality second pass

Date: 2026-08-26.

## Outcome

The second pass closes the reported logical and ownership regressions without
redrawing laboratory vessels that already had credible canonical art. Technical
validation passes; renewed human visual acceptance remains open.

## Foundational correction

The remaining electrophoresis lead model was wrong at the object boundary. Each
standalone object treated connection as an intrinsic boolean and each state card
drew a cable, plug, and private socket. That made a relationship look like a
floating binary object and allowed plug/cable overlap without any connection to
the apparatus.

The electrophoresis tank now owns the relationship:

- `black_lead_connected` and `red_lead_connected` are tank state fields;
- `black_terminal` and `red_terminal` are exact measured tank subparts using
  the existing insertion-receptacle `slot` kind;
- two transparent tank-coordinate overlays add plugs and separated cables only
  when the corresponding connection is true;
- attach and disconnect interactions target the exact terminal subpart; and
- the four cable-card SVGs and two standalone cable objects are deleted.

No compatibility layer was retained. This is a pre-production schema and
ownership correction.

## Reported visual regressions

| Finding               | Resolution                                                                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Plug and wire overlap | Deleted the floating card model; plugs now seat on actual tank terminals and cables exit toward the power-supply side.                                                         |
| Arbitrary skew        | Heat block, lightbox, and microwave retain level frontal housings. The current census has six transform-bearing files, each for a physically motivated local part.             |
| Rebuilt tubes         | MTT uses the canonical `microtube`; there is no MTT-specific vessel SVG.                                                                                                       |
| MTT complexity drift  | The pre-weighed object is 20 mg of MTT material in the canonical Servier-derived microtube, rendered at 8 percent of its mass capacity. Empty state hides the material region. |
| T75 regression        | Both T75 states use the recovered established transparent flask pair rather than a replacement redraw.                                                                         |
| Microtube regression  | The canonical detailed Servier-derived open microtube remains the single vessel geometry for MTT and other microtube materials.                                                |

## Visual and runtime evidence

- The regenerated current-library gallery contains all 130 authored SVGs.
- The production-renderer review passed 130 of 130 cards: 64 inline DOM, 66
  image, 430 namespaced IDs, zero load/mode/browser failures, and zero 390 px
  horizontal overflow.
- The visible three-step lid-and-leads walker completed 3 of 3 actions. It
  rejected the red terminal during the black step and the black terminal during
  the red step, then displayed both seated connections.
- The real MTT protocol scene showed the pre-weighed material in the canonical
  microtube. The restored T75 pair and microtube were also reviewed in the
  current source gallery and their real protocol consumers.
- The regenerated 58-scene structural census contains all 130 assets and no
  retired lead-card paths. The shadow audit reports 123 ordinary `SHADOW-NONE`
  assets, seven protected result-interface skips, and zero candidates.

## Validation

| Gate                       | Result                                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| Content lint               | PASS: 244 YAML files, 127 objects, 11 base scenes, 47 protocol scenes, 31 protocols; zero findings |
| Production build           | PASS: 127 objects, 67 asset specs, 130 SVGs, 64 DOM-required assets, 58 scenes                     |
| Python                     | PASS: 7,662 tests                                                                                  |
| Codebase gate              | PASS: all five gates; Node 675 total, 673 passed, 2 skipped                                        |
| Browser                    | PASS: 113 Playwright tests                                                                         |
| Exact terminal walkthrough | PASS: 3 of 3 actions and both wrong-sibling rejection probes                                       |
| Production renderer        | PASS: 130 cards with zero failures or mismatches                                                   |

Human approval of the repaired visual set remains the only open acceptance
decision; it is not inferred from the automated or manager visual checks.
