# Historical M6 candidate evaluator findings (superseded)

**Historical record, rejected as current art direction on 2026-08-26.** This
comparison records the M6 result for the frozen D01-D05 fixtures. The
realistic-equipment replacement wave of 2026-08-26 superseded that provisional
choice: none of the five directions is accepted production art, a recovery
path, or a live decision surface. Retain the observations as methodology for
judging silhouette, volume, reference anatomy, and scene-scale legibility.

Inspect the frozen evidence in
`docs/figures/equipment_kit/candidates/D01-servier-shallow/` through
`docs/figures/equipment_kit/candidates/D05-quiet-cylinder/` and the
[archived-fixture README](../../figures/equipment_kit/candidates/README.md).
Inspect current production assets through
`docs/figures/equipment_kit/review.html`; it is the generated 134-asset
gallery, not a candidate renderer.

## Scope and method

This is the durable record of the final independent M6 evaluation. It evaluates
the frozen M5 review fixtures only; it neither changes candidate evidence nor
asserts that a review fixture is production art.

The evaluator inspected, for every `D01` through `D05` direction:

- the enlarged 1920 px diagnostic composite;
- the exact 320 px Lanczos downsample of that composite;
- the 1:1 normal and minimum scene-placement benchmark;
- the normal/minimum crop sheet and 320 px alpha-silhouette composite;
- all 20 authored candidate SVG sources; and
- the [candidate-direction brief](svg_candidate_direction_brief.md) and four
  M4 boards: [T75](svg_reference_board_t75_flask.md),
  [centrifuge](svg_reference_board_centrifuge.md),
  [P200](svg_reference_board_micropipette.md), and
  [Falcon](svg_reference_board_falcon_15ml.md).

The frozen fixture directories and their retained 320 px PNGs are the
historical controlled comparison surface. The former candidate `review.html`
now redirects to the production gallery and must not be used to recreate this
comparison. The 320 px images are exact downsampling evidence, not
application-art inputs.

## Criteria

Ranking weighs five connected criteria: stable class silhouette, constructed
volume and occlusion, fidelity to the M4 reference anatomy, legibility at
normal and minimum scene sizes, and a cool restrained language adjacent to the
local Servier corpus. Because the brief fixes broad silhouettes, anchors, and
art bounds, silhouette comparison is a control rather than a differentiator:
all directions retain the same canted T75, hinged centrifuge, tall P200, and
long conical tube at 320 px. The decisive comparison is physical faces,
overlap, reference-backed recognition cues, and what survives the real-size
surfaces.

## Historical ranking (rejected)

| Rank | Direction              | Decision                                   |
| ---: | ---------------------- | ------------------------------------------ |
|    1 | `D04-occlusion-strong` | Historical provisional default; superseded |
|    2 | `D01-servier-shallow`  | Historical runner-up; superseded           |
|    3 | `D02-rim-forward`      | Retain as a rim experiment                 |
|    4 | `D05-quiet-cylinder`   | Retain as a cylinder experiment            |
|    5 | `D03-mass-first`       | Retain as a simplification experiment      |

## Direction findings

### D04-occlusion-strong

`D04` is strongest overall. The centrifuge combines a dark under-lid plane,
deep nested oval cavity, lid/hinge overlap, front control recess, and feet;
at 320 px it remains the clearest class-specific object. The T75 keeps its
broad shallow chamber while a near wall and cap-over-neck overlap establish a
vessel. The P200 uses one dark sleeve-over-shaft overlap instead of outlining
each part. The Falcon separates cone and far body wall with dark planes while
retaining a liquid-surface ellipse inside the vessel.

These choices best meet the boards' demand for physical planes rather than
palette-only or detail-only depth, and the localized dark values remain
Servier-adjacent rather than decorative linework. The only translation risk is
the T75: reduce any dark cap or near-wall fill that competes with its clear
chamber at enlarged size.

### D01-servier-shallow

`D01` is the strongest restrained alternative. Its T75 has a broad lit top,
contained liquid plane, cap ellipses, and modest receding walls. Its centrifuge
keeps the board-required housing, opening, rotor, lid, and controls without
excess ring count. Its P200 retains plunger, inset display, sleeve, shaft, and
tip as a quiet vertical mass. Its Falcon keeps cap cylinder, tube wall,
material-surface ellipse, sparse writing/graduation cues, and conical base.

It is closest to the local Servier language and is the appropriate fallback if
real application rendering makes D04 too heavy. Its limitation is that cavity
and overlap depth, especially in the centrifuge, are less decisive than D04
after 320 px downsampling.

### D02-rim-forward

`D02` proves that paired rims can make an opening read as a recess. Its
centrifuge cavity is board-faithful at large size and its T75 thick outer and
inner rims give the chamber thickness. At exact 320 px, repeated light and
dark rims compress into competing stripes; the T75 rim then competes with the
more important chamber and liquid mass. Preserve one or two useful nested rims
inside D04 recesses, but do not select D02 as the complete language.

### D05-quiet-cylinder

`D05` gives the Falcon a coherent cap, rim, liquid-surface, and
cone-shoulder ellipse language, and it keeps the T75 near D01's successful
construction. On the P200, however, repeated sleeve, shaft, and tip ellipse
bands make the narrow tool read as stacked or threaded at 320 px and in the
1:1 P200 tiles. Use its ellipse discipline for genuinely cylindrical vessel
parts, not as the cross-equipment language.

### D03-mass-first

`D03` remains calm at 320 px, but it removes M4-backed recognition evidence.
Its centrifuge reduces the chamber to broad ellipse layers and loses readily
visible rotor/recess logic; its P200 loses the light display inset; its Falcon
loses writing-panel and graduation cues; and its T75 loses much cap/neck
construction. The minimum-size proof does not compensate: every direction is
already reduced to mass and silhouette at those placements. D03 therefore
sacrifices normal-size recognition without a real minimum-size advantage.

## Real-size limit

The 1:1 benchmark confirms a shared placement limit, independent of direction:

| Archetype           | Literal minimum visible box |
| ------------------- | --------------------------- |
| T75 flask           | 15.41 by 4.93 px            |
| Centrifuge          | 39.30 by 53.77 px           |
| P200 micropipette   | 6.71 by 26.85 px            |
| Falcon 15 mL vessel | 2.31 by 13.78 px            |

At the literal minimum, the T75 is a thin horizontal token and the Falcon
cannot communicate cap, body, cone, or material identity regardless of visual
direction. The P200's collar/body/shaft mass survives at normal height, while
its display and sleeve distinctions appropriately collapse at minimum size.
This is a scene-scale constraint, not a direction-specific art failure. M7/M12
must validate meaningful recognition at normal placement and use selection,
state, and surrounding scene context at the literal minimum.

## Blockers and decision

No direction-specific blocker was found in the historical comparison. Its
then-remaining M7/M12 proof was production-asset rendering in the real
application; the M5 fixtures could never prove integration or supersede
canonical state/material contracts.

The original M6 record selected `D04-occlusion-strong` provisionally and kept
`D01-servier-shallow` as a fallback. That result is superseded and rejected by
the 2026-08-26 realistic-equipment replacement wave. The transferable finding
is narrower: use physically motivated recesses, overlaps, and restraint only
when they support reference-backed anatomy in the current production art.
