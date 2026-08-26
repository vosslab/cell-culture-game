# Historical M7 production exemplar evaluation (superseded)

**Historical approval, superseded and rejected as current art direction on
2026-08-26.** This report documents the then-current four production
exemplars and its D04-with-D01-restraint evaluation. The realistic-equipment
replacement wave supersedes that visual approval: it is not current acceptance
of the old exemplar art, a D04 handoff, or a live rendering claim. Its
reference, material, and scene-scale observations remain historical evidence.

## Verdict

All four production archetypes were **APPROVED** for M7 at the time. The
rebuild then retained D04's decisive physical overlaps and recesses while using
D01's restraint: dark values named real cavities, far faces, or overlap edges
rather than decoration. That approval is superseded by the 2026-08-26
realistic-equipment replacement wave; it does not approve the former art for
current use or future extraction.

This was an evaluation of the then-current production SVGs, not the M5
candidate fixtures. It compared them against the M4 boards, the now-superseded
M6 selection, and actual placement ranges in the M3 census. It does not claim
current production acceptance or replace the completed M12 production
workspace, contrast, and result-interface review.

## Evidence and method

| Evidence | What was inspected | Result |
| --- | --- | --- |
| Production source render | Fresh `rsvg-convert` renders of the two T75 states, the two centrifuge states, P200, and Falcon 15 mL. | All forms rendered cleanly with their intended silhouettes and state art. |
| Compiled material path | Fresh Firefox contact sheets from `tools/liquid_volume_contact_page.mjs`, which injects the compiled SVG and calls the real liquid writer. | P200 rendered 0%, 50%, and 100% with `#1e40af` and `#c0266d`; Falcon rendered 0%, 1.4336312%, 2.8672624%, 50%, and 100% with both colors. |
| Production-size evidence | [svg_exemplar_size_flatness_slice.md](svg_exemplar_size_flatness_slice.md) and [svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md). | Assessment used actual emitted placement ranges, not an invented fixed icon size. |
| Reference and direction evidence | The four M4 boards and [svg_visual_direction_selection.md](svg_visual_direction_selection.md). | The retained anatomy and depth treatment match the selected D04-with-D01-restraint handoff. |

The material contact sheets were generated on 2026-08-25 from the current
`dist/assets/liquid_regions.json`. The generated cards report each requested
and rendered fill percentage, the clamp state, and the runtime transforms. This
is renderer-backed evidence, not an SVG-editor preview. The exact colors are
the M4 Falcon-board cool/warm verification inputs, not new material-registry
entries.

## Criterion findings

| Archetype | Observed facts | Judgment | Verdict |
| --- | --- | --- | --- |
| T75 flask | The empty and filled files share the broad shallow three-quarter chamber, angled neck, cap cylinder, transparent top/near/end faces, and strong outer contours. The filled state adds a clipped level pink medium layer behind the same contours. | The form immediately reads as a tissue-culture flask rather than a bottle or tray. The cap-over-neck overlap and chamber planes provide D04 volume without a heavy dark mass. The fixed state difference is clear and does not change the vessel silhouette. | APPROVED |
| Benchtop centrifuge | The open state shows a broad three-plane housing, inset nested chamber, visibly seated rotor, rear-hinged thick lid with a dark underside, control face, and feet. The running state preserves the housing/camera/control geometry, fully covers the rotor with a closed lid, and adds a restrained green running indication. | The open and running views are unambiguously different physical states. The cavity, hinge, lid, and controls are reference-backed and coherent with the T75's blue-gray contour/face language. The closed state safely avoids an exposed spinning rotor. | APPROVED |
| P200 micropipette | The single material SVG has a cylindrical plunger, main front and darker rear planes, recessed display, orange nominal-range collar, separate ejector sleeve, tapered shaft, and disposable tip. Real compiled renders keep 0% empty, make 50% a contained shortened tip column, and make 100% reach the tip's full liquid bounds. Both cool and warm colors affect only the tip liquid. | The object reads as an adjustable micropipette at normal review scale; the sleeve-over-shaft overlap and inset display keep it from reading as a stack of flat bands. Material ownership is correct: liquid identity/amount never recolors the body or collar. | APPROVED |
| Falcon 15 mL | The static form has a seated ribbed blue cap, pale cap rim, clear cylindrical body with one writing panel, sparse graduation ladder, darker far side, and a continuous pointed cone. In the real compiled path, 0% leaves no residual liquid; 1.4336312% produces cone-only liquid; 2.8672624% meets the full-width body without a visible gap; 50% and 100% retain an ellipse-like surface and coherent near/far liquid values. Both blue and magenta derive across base, highlight, and shadow roles. | The tube class is recognizable without branding. The cone/body calibration is visibly continuous, and clear-plastic fixed art remains legible with either hue. This is the strongest material-behavior exemplar and meets the M4 matrix. | APPROVED |

## Size and silhouette limits

Observed placement ranges from the M3 evidence are materially smaller than the
review renders in some scenes:

| Family | Normal/max evidence | Literal minimum evidence | Evaluation |
| --- | --- | --- | --- |
| T75 | 64.01 x 20.46 px median; 113.66 x 36.33 px max | 15.41 x 4.92 px | At normal placements the shallow vessel, cap, and filled boundary remain meaningful. At literal minimum, the five-pixel height can carry only selection/context and broad state, exactly as M6 records. This is a diagnostic scale limit, not a blocker or a reason to add microscopic detail. |
| Centrifuge | 410.50 x 561.66 px max | 39.30 x 53.74 px | Housing, lid state, and green running cue remain distinguishable. Rotor detail is necessarily subordinate at the minimum. |
| P200 | 24.64 x 98.56 px at the minimum-scale drug-dilution placement; 42.25 x 152.11 px max | 6.11 x 24.44 px at the two 320 px SDS-PAGE loading workspaces | At normal tall placements, silhouette, collar, display recess, and tip hierarchy read. At literal minimum, the narrow tool remains a directional silhouette; liquid is appropriately a secondary cue. The 6.71 x 26.85 px drug-dilution result is a distinct minimum-scale reference, not the literal smallest CSS box. |
| Falcon | 42.25 x 251.93 px median; 72.67 x 433.29 px max | 2.31 x 13.77 px | At normal placements, cap/body/cone and fill state read well. At literal minimum, no vessel anatomy can be reliably evaluated; scene context and selection must supply identity. |

These limits are observed placement facts. They do not invalidate the selected
direction because [svg_visual_direction_selection.md](svg_visual_direction_selection.md)
already establishes that literal-minimum T75 and Falcon placements cannot carry
full anatomy. Adding detail there would violate the selected D01 restraint and
would not produce dependable recognition.

## Cross-archetype assessment

Observed common language:

- Cool blue-gray fixed planes, pale lit faces, and deep blue-gray contours make
  the T75, centrifuge, P200, and Falcon plausibly belong on one lab bench.
- Heavy dark paint is localized to the centrifuge cavity/lid underside, P200
  display and far plane, and real contour overlaps. It does not become arbitrary
  internal striping.
- Cylinders use ellipses where they are physically useful: T75 cap, centrifuge
  chamber, P200 plunger, and Falcon cap/liquid surface. The assets do not apply
  ellipse bands indiscriminately along narrow shafts.
- Runtime material paint stays contained: the P200 tip alone changes, and the
  Falcon liquid remains within its gravity parts below the current surface.

Judgment: this meets the M6 selected direction. The production forms are more
specific and readable than a flat icon set while remaining quiet enough to sit
beside other Servier-adjacent scientific art.

## Limitations and follow-up

- This M7 review used fresh source renders and the actual compiled material
  injector/liquid writer. It did not recreate M12's full set of production-page
  screenshots across bench, hood, cell-counter, and microscope contexts.
- Minimum-size evidence comes from the real layout pipeline's emitted boxes;
  visual anatomy is intentionally not asserted below the physical information
  limit. M12 should confirm selection rings, contrast, and workspace context at
  those scales.
- No blocker was observed. The remaining work is the planned M8 construction
  kit and later M12 integration review, not repair of these four exemplars.
