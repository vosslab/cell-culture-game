# SVG visual direction selection

## User verdict update

**REJECTED on 2026-08-26.** After seeing the candidate review page, the user
found the four archetypes cubist rather than realistic laboratory equipment.
That direct human preference supersedes the provisional manager default for
future visual work. None of D01-D05 is currently an approved replacement
direction, because all five reuse the same four developed-massing archetypes.

The candidate page deliberately contains four object classes per direction; it
was never a review of the complete production library. Use the current
production review workflow in [USAGE.md](../../USAGE.md#equipment-svg-visual-review)
to inspect six real-consumer scenes and all authored equipment sources. The
technical, state, material, and browser validation from M7-M12 remains useful,
but it does not establish visual realism or user acceptance.

## Current replacement direction

The replacement is not a sixth candidate. It is source-first, visually
adequate physical equipment art: retain detailed direct Servier geometry where
its projection and modeled parts are credible, then add only required runtime
anchors and material/state layers. Where the exact source projects as cubist at
real consumer size, use a controlled repository adaptation backed by
real-equipment anatomy instead. The microscope and loading-tip boxes are that
boundary; the water-bath pair, incubator, vortex, P10, multichannel pipette,
bottle, and Falcon forms retain detailed direct Servier geometry.

The generated source-art gallery is `docs/figures/equipment_kit/review.html`,
produced by `tools/render_svg_library_review.mjs`, and loads all 130 live
authored source assets. The candidate URL redirects there. The current
production-host proof reached 130 of 130 assets with zero broken images or
render-mode mismatches. M9-M11
repairs now have a fresh independent cross-package PASS and current M12
full-scene capture. The retained compact PNGs are earlier one-time evidence,
because the fresh post-final-build compact rerun stalled before readiness.

## Historical M6 decision (superseded and rejected)

No user preference vote had arrived when the M5 evidence became complete, so
the original record called `D04-occlusion-strong` a provisional manager
default for M7 and `D01-servier-shallow` its runner-up. The 2026-08-26
realistic-equipment replacement wave rejected that result. D01-D05 are now
frozen historical comparisons only, not accepted assets, fallbacks, or a pool
for future visual selection.

The historical decision uses the final independent
[evaluator findings](svg_candidate_evaluator_findings.md), the five frozen M5
fixtures, the four M4 reference boards, and their 320 px and real-size
surfaces. Its methodology remains useful, but its verdict does not control the
M12-complete production work or the canonical state/material contracts.

## Historical review surfaces

The controlled comparison is frozen in
`docs/figures/equipment_kit/candidates/D01-servier-shallow/` through
`docs/figures/equipment_kit/candidates/D05-quiet-cylinder/`, with handling
instructions in the [archived-fixture README](../../figures/equipment_kit/candidates/README.md).
Do not use `candidates/review.html`: it redirects to the canonical production
gallery. Inspect current art at `docs/figures/equipment_kit/review.html`.
Each retained 320 px bench composite below is historical diagnostic evidence,
not an application-art input.

| Rank | Direction              | 320 px bench composite                                                                             | Decision                                   |
| ---: | ---------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------ |
|    1 | `D04-occlusion-strong` | [PNG](../../figures/equipment_kit/candidates/D04-occlusion-strong/renders/bench-composite-320.png) | Historical provisional default; superseded |
|    2 | `D01-servier-shallow`  | [PNG](../../figures/equipment_kit/candidates/D01-servier-shallow/renders/bench-composite-320.png)  | Historical runner-up; superseded           |
|    3 | `D02-rim-forward`      | [PNG](../../figures/equipment_kit/candidates/D02-rim-forward/renders/bench-composite-320.png)      | Retain as rim experiment                   |
|    4 | `D05-quiet-cylinder`   | [PNG](../../figures/equipment_kit/candidates/D05-quiet-cylinder/renders/bench-composite-320.png)   | Retain as cylinder experiment              |
|    5 | `D03-mass-first`       | [PNG](../../figures/equipment_kit/candidates/D03-mass-first/renders/bench-composite-320.png)       | Retain as simplification experiment        |

## Historical criteria and ranking

The ranking weighs Servier consistency, M4 reference fidelity, coherent volume,
normal/minimum-size legibility, and the independent evaluator's findings.

| Direction              | Evidence-based result                                                                                                                                                                                                       |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `D04-occlusion-strong` | Best overall. It is still cool and restrained enough to remain Servier-adjacent, while localized dark recesses and real overlaps make the four forms read as constructed volumes. It most completely meets the four boards. |
| `D01-servier-shallow`  | Best restrained alternative. Its economical planes, rims, and recognition details are closest to the local Servier language, but its cavity and overlap depth are less decisive after downsampling.                         |
| `D02-rim-forward`      | Strong cavity and opening test, especially for the centrifuge, but paired rims collapse into competing narrow stripes at 320 px. Keep the useful nested-rim idea, not the whole treatment.                                  |
| `D05-quiet-cylinder`   | Coherent tube, cap, and liquid ellipses, but too quiet for the P200 sleeve/shaft hierarchy and less seated than D04 for the centrifuge. Reuse ellipse discipline only where cylindrical structure warrants it.              |
| `D03-mass-first`       | Calm at small size, but removes reference-board evidence needed at normal size: the centrifuge becomes target-like and P200/Falcon lose decisive construction cues.                                                         |

## Historical archetype reasons

- **T75 flask:** D04 preserves the broad shallow chamber and lit rim while the
  cap-over-neck and near-wall overlaps establish a clear vessel. In M7, shrink
  any dark cap/near-wall area that competes with the cap ellipse. D01 remains
  the safe recovery path if the transparent chamber loses its lightness.
- **Centrifuge:** D04 best realizes the board's top/front/side housing, nested
  oval cavity, seated rotor, rear hinge, lid underside, control recess, and
  feet. D02 proves that nested rims work, but D04 supplies the stronger
  physical recess without stripe accumulation.
- **P200 micropipette:** D04 keeps the rounded plunger, inset display, collar,
  tapered shaft, and one sleeve-over-shaft overlap. It reads as a tool mass
  rather than a stack of horizontal bands. D01 is the fallback if the dark
  sleeve feels too heavy in a crowded workspace.
- **Falcon 15 mL vessel:** D04 separates cap, shoulder, near/far clear-plastic
  faces, cone, and liquid-surface ellipse as physical masses. In production,
  keep the clear-plastic hierarchy ahead of the dark plane and preserve the
  canonical material layers; the M5 surrogate does not define runtime material
  semantics.

## Historical transferable observations

The historical comparison proposed D04 construction with D01 restraint. That
proposal is rejected as a direction; retain only the following observations
when reference-backed current production art supports them:

1. Use a dark value only for a real recess, far plane, or physical overlap;
   never as decorative internal linework.
2. Retain D04's centrifuge cavity, lid, and hinge construction, but make the
   rotor safely occluded in closed/running states.
3. Give a micropipette one decisive sleeve-over-shaft overlap. Do not repeat
   D05-style ellipse bands along a narrow shaft.
4. Use consistent ellipses for true cylinders and vessel rims; use one or two
   nested rims only where they clarify a real opening.
5. Keep material color inside the production material band. Clear-plastic,
   liquid, and conical planes obtain depth from ordered faces and restrained
   value separation, not filters or shadows.
6. For broad batch work, borrow D01's economical detail whenever D04-style
   depth lacks a physical justification.

## Real-size limit

At literal minimum placement, the T75 is approximately 15 by 5 CSS pixels and
the Falcon approximately 2 by 14 CSS pixels. Neither can reliably communicate
full internal volume or class-specific anatomy there. M7 must verify meaningful
recognition at normal scene placement; at these minimum placements, selection,
state, and surrounding scene context supply the remaining meaning. This is a
shared scene-scale limitation, not a reason to add detail or reject D04.

## Historical M7 handoff (superseded)

The original handoff said that M7 would translate D04 into the four canonical
production families without changing
viewBoxes, anchors, render modes, object bindings, state ownership, or material
contracts merely to match a review fixture:

1. Rebuild the T75 empty/filled pair from shared geometry; filled adds only
   contained liquid behind the final near contours.
2. Rebuild centrifuge idle/open and running/closed states on one housing and
   mounting frame, with a rear-hinged lid and safely hidden running rotor.
3. Rebuild the P200 family around one generic adjustable-pipette construction;
   retain stable body geometry and limit state/material difference to the
   contained tip cue.
4. Rebuild the Falcon 15 mL canonical material-rendered SVG using its required
   direct-root semantic layers and volume-calibrated material band.
5. Compare each finished exemplar with its M4 board, D04 fixture, and real
   workspace render at normal and minimum sizes. A concrete reference-back or
   contract failure returns the exemplar for repair before M8 kit extraction.

This handoff is retained solely as a historical record. The realistic-equipment
replacement wave supersedes its D04/D01 art-direction choice; current work
uses the source-first direction stated above and the completed M12 evidence.

## Later preference

The 2026-08-26 user verdict reopened visual direction selection and rejected
the five retained directions as the replacement pool. The next visual pass must
start from reference-backed, recognizably realistic laboratory-equipment
archetypes rather than selecting another D01-D05 treatment. The current assets
remain inspectable implementation evidence while that redesign is open; no
legacy-compatibility requirement preserves their visual construction.
