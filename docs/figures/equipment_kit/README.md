# Equipment SVG construction kit

## Purpose and authority

This is the M8 construction authority for new physical-equipment SVG work. It
turns the approved M7 exemplars into a small, reviewable set of constraints and
principles; it does not replace the SVG, material, object-YAML, or scene
contracts. The source assets remain the only editable production sources.

For an all-library, file://-usable inspection surface, open the generated
`docs/figures/equipment_kit/review.html` after running
`tools/render_svg_library_review.mjs`.
It loads each card directly from the current `assets/equipment/` source path.
The four-object candidate page is an archived comparison notice, not a
production-art gallery.

That source gallery deliberately uses ordinary images. For exhaustive review
through the production render-mode boundary, serve the built site and open
`/equipment_review.html`. The built page shares `svg_host.tsx` with real scenes,
including DOM fetch, per-instance ID namespacing, and injection.

Use this kit with the applicable M4 reference board, then verify the result in
its real scene at normal and literal-minimum sizes. The kit distinguishes:

- **Measured constraints**: facts and normal-size targets derived from current
  production exemplars in [MEASUREMENTS.md](MEASUREMENTS.md).
- **Visual principles**: demonstrated construction choices, selected from M5
  and confirmed by M7. They guide a review; they are not a new pixel or
  count-based test contract.

**Current visual-status boundary:** on 2026-08-26 the user rejected D01-D05 as
cubist rather than realistic laboratory equipment. Their archived sections are
historical evidence, not current authority. The current production exemplars,
source-first rules, and refreshed measurements in this kit are the M8
construction authority. The active direction is physically credible,
source-first equipment art: rounded or molded shells, real openings and
recesses, cylinder/ellipse relationships where warranted, transparent vessel
faces, and functional overlaps. Start from detailed Servier geometry when it
is visually credible; use a controlled repository adaptation when an exact
source projection is not. Preserve the runtime contracts below in either case.

The historical M7 evaluator record remains in
[svg_m7_exemplar_evaluator_findings.md](../../active_plans/reports/svg_m7_exemplar_evaluator_findings.md),
but the later user verdict supersedes its D01-D05 direction. The current
all-library and targeted replacement re-reviews are recorded in
[svg_m12_visual_evaluator_findings.md](../../active_plans/reports/svg_m12_visual_evaluator_findings.md).
The durable SVG semantics, normalization, and source-tree rules remain in
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md).

## Canonical exemplars

Draw from these production files directly. Do not copy them into this kit,
derive a second editable source, or use a candidate fixture as a runtime asset.

| Archetype              | Canonical production source                                                                                                                                               | What it demonstrates                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Transparent vessel     | [t75_flask_empty.svg](../../../assets/equipment/binary_state/t75_flask_empty.svg) and [t75_flask_filled.svg](../../../assets/equipment/binary_state/t75_flask_filled.svg) | Broad shallow chamber, angled neck, cap-over-neck overlap, and a filled state behind unchanged near contours. |
| Benchtop instrument    | [centrifuge.svg](../../../assets/equipment/binary_state/centrifuge.svg) and [centrifuge_running.svg](../../../assets/equipment/binary_state/centrifuge_running.svg)       | Three-plane housing, true cavity, rear-hinged lid, seated rotor, and state-specific occlusion.                |
| Handheld material tool | [p200_micropipette.svg](../../../assets/equipment/variable_volume/p200_micropipette.svg)                                                                                  | Shallow front/rear tool mass, recessed display, one sleeve-over-shaft overlap, and tip-only material paint.   |
| Material vessel        | [falcon_15ml.svg](../../../assets/equipment/variable_volume/falcon_15ml.svg)                                                                                              | Clear cylindrical body, cap, continuous cone, far face, and calibrated contained liquid.                      |

The detailed identity evidence is in the four M4 boards:
[T75](../../active_plans/reports/svg_reference_board_t75_flask.md),
[centrifuge](../../active_plans/reports/svg_reference_board_centrifuge.md),
[micropipette](../../active_plans/reports/svg_reference_board_micropipette.md),
and [Falcon 15 mL](../../active_plans/reports/svg_reference_board_falcon_15ml.md).
Manufacturer/manual sources establish the object; Servier-adjacent sources
establish the compatible illustration language.

## Direction and construction

### Historical implementation principle (not current art direction)

The completed M7-M11 implementation used **D04 occlusion strong with D01
Servier restraint**. D04 was the selected
construction logic: establish volume with a real far plane, cavity, or physical
overlap. D01 limits that treatment to the evidence needed for recognition at
normal scene size. A dark band that cannot name a recess, far face, or overlap
does not belong in the artwork.

This describes the rejected D01-D05 historical tree only. It is not approval
to propagate that direction after the user verdict above.

This is a visual principle, not a palette or geometry quota. The decision and
archetype-specific limits are recorded in
[svg_visual_direction_selection.md](../../active_plans/reports/svg_visual_direction_selection.md),
and the M7 evaluator confirms that the production forms retain this balance.

### View, elevation, and light

Choose projection from the object's characteristic structure. Prefer a frontal
or near-orthographic view for paired instruments and control-facing equipment.
Use shallow perspective only when it reveals a real hinge, cavity, vessel neck,
or other identifying structure. Do not rotate or skew an object merely to
signal depth, and keep one projection across every state in a family.

For a local object frame with +x right, +y down, and +z toward the viewer, use
an upper-left/front light vector of **(-1, -1, +1)**. Lit top and left-facing
planes lead; right/receding planes and real cavities receive the darker value.
Apply that lighting within the projection already justified by the source; it
does not authorize a global three-quarter camera. This convention is
demonstrated by the current exemplars in
[MEASUREMENTS.md](MEASUREMENTS.md#exemplar-derived-visual-principles).

### Draw order

Build a recognizable silhouette and major masses before detail. For ordinary
art, use this order where the subject permits it:

1. Far or rear fixed planes.
2. Real interior/recess geometry and occluded functional parts.
3. Contained material geometry in its required semantic order.
4. Near fixed faces, rims, and physical overlap edges.
5. Contours, sparse intrinsic markings, and highlights that clarify form.

For material-rendered art, semantic root groups and their document order win
over a convenient artistic grouping. Preserve direct-root semantic groups,
paint roles, clips, and structural anchors exactly as required by
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md#closed-authored-semantic-vocabulary).
Do not use a foreground contour to hide an incorrectly ordered material layer.

## Measured constraints

### Normal-size stroke targets

At a normal, task-relevant placement, target a 1.0 CSS-pixel stroked outer
contour and a 0.75 CSS-pixel identity-carrying detail. Convert authored units
through the source viewBox before judging the target. These are measured
starting targets, not literal-minimum requirements.

At a literal M3 minimum, simplify sub-floor detail away. Preserve silhouette,
filled-face separation, visible state, scene selection treatment, and the 44
CSS-pixel interaction core instead of accumulating heavier strokes. A face
boundary or overlap may carry an edge without a stroke. The evidence and
conversion method are in [MEASUREMENTS.md](MEASUREMENTS.md#stroke-measurements).

### Source-owned swatches

There is no mandatory six-color equipment palette. Direct Servier sources,
transparent vessels, and repository adaptations retain family-appropriate
values; forcing them into one palette was part of the rejected icon-like
direction. Reuse a current family's literal values when extending that same
physical form, and preserve credible source values when adopting detailed
source geometry.

The current source-fact swatch ledger remains in
[MEASUREMENTS.md](MEASUREMENTS.md#literal-production-swatches). Material
identity and color remain owned by `materials.yaml` and the material renderer;
do not copy a probe color or one exemplar's liquid hue into fixed equipment
art.

### Face-value guidance

The following counts are observed exemplar evidence, not mandatory counts.
Use as many distinct values as are needed to make real faces, recesses, and
functional subassemblies legible at normal size; remove values that only make
decorative striping.

| Material or archetype    | Demonstrated current structure                               | Batch guidance                                                                                       |
| ------------------------ | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Opaque housing           | Detailed source faces or a small set of justified planes     | Separate only real housing, control, opening, and cavity relationships; do not add decorative skew.  |
| Fixed tool shell         | One stable tool mass, display recess, collar, and shaft      | Establish silhouette and physical part overlap before display detail.                                |
| Clear chamber/vessel     | 7 T75 chamber planes; detailed direct-source Falcon geometry | Let clear near, far, rim, and highlight faces explain transparency; keep dark far faces subordinate. |
| Cap                      | Molded T75 cap; ribbed direct-source Falcon cap              | Use real cylinder and rim relationships, not repeated bands added for style.                         |
| Static contained liquid  | 1 clipped T75 liquid plane                                   | Keep the level contained behind final near contours.                                                 |
| Material-rendered liquid | 5 P200 tip layers; 11 Falcon semantic layers                 | Preserve the semantic paint-role and liquid-part contract; do not repaint fixed housing geometry.    |

The exact source observations are in
[MEASUREMENTS.md](MEASUREMENTS.md#face-value-evidence). The compact direction
rules also prohibit indiscriminate ellipse bands and nested rims: use them only
when they explain a true cylinder, opening, or vessel rim.

## Semantic and state preservation

Visual polish must preserve the owned behavior boundary:

- Keep selection and physical-state ownership in object YAML. A state family
  retains one stable silhouette, projection, viewBox, canvas, safe padding,
  contour roles, and anchors; state art changes inside that frame.
- Keep material identity and amount out of fixed housing paint. Preserve the
  direct-root semantic groups, `data-vlab-*` vocabulary, material clips, and
  `anchor_liquid_bounds` / `anchor_liquid_clip` inputs for material forms.
- Retain unique structural IDs, reference targets, and named anchors. Treat
  them as runtime/compiler inputs, not decorative opportunities for renaming.
- Keep SVG art language-neutral. Put learner prose and identity labels in the
  surrounding DOM/object data, not in the SVG.

These are established system rules; see
[SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md#ownership-and-processing-boundary)
and [HUMAN_GUIDANCE.md](../../HUMAN_GUIDANCE.md#scientific-equipment-svgs).

## Candidate archive and routing

All five M5 directions are retained as rejected historical snapshots. They
record why a four-object comparison of faceted treatments was not an acceptable
visual direction; none is a production source, current rule, or regeneration
target. Open `docs/figures/equipment_kit/review.html` (made by
`tools/render_svg_library_review.mjs`) to inspect current authored SVGs. The
[candidate review page](candidates/review.html) redirects to it and labels the
historical comparison accordingly.

| Direction            | Historical source                                 | Evidence                                                | Retained purpose                  |
| -------------------- | ------------------------------------------------- | ------------------------------------------------------- | --------------------------------- |
| D01 Servier shallow  | [source](candidates/D01-servier-shallow/source/)  | [evidence](candidates/D01-servier-shallow/evidence.md)  | Rejected shallow/faceted baseline |
| D02 rim forward      | [source](candidates/D02-rim-forward/source/)      | [evidence](candidates/D02-rim-forward/evidence.md)      | Rejected rim emphasis             |
| D03 mass first       | [source](candidates/D03-mass-first/source/)       | [evidence](candidates/D03-mass-first/evidence.md)       | Rejected simplified mass          |
| D04 occlusion strong | [source](candidates/D04-occlusion-strong/source/) | [evidence](candidates/D04-occlusion-strong/evidence.md) | Rejected dark/occlusion treatment |
| D05 quiet cylinder   | [source](candidates/D05-quiet-cylinder/source/)   | [evidence](candidates/D05-quiet-cylinder/evidence.md)   | Rejected cylinder treatment       |

The [candidate fixture README](candidates/README.md) defines their frozen-input
and render-evidence boundary. A later user preference can reopen a bounded
selection review as documented in
[svg_visual_direction_selection.md](../../active_plans/reports/svg_visual_direction_selection.md#later-preference).

## Batch acceptance workflow

1. Start from the owning M4-style identity evidence: identify silhouette,
   characteristic parts, physical opening/recess, material behavior, and
   normal-size scene placement.
2. Construct the major masses and drawing order from the object reference.
   Preserve detailed source geometry where it remains credible; otherwise use
   a controlled adaptation that names a physical relation rather than a
   decorative dark band or faceted plane.
3. Preserve the selected form, object binding, semantic groups, IDs, anchors,
   and material ownership. Change the canonical source under `assets/`, never
   a generated file or a kit fixture.
4. Run the normalizer/validator path and rebuild the authored source through
   the repository pipeline. For a material form, inspect the compiled DOM path
   at empty, partial, and full volumes with cool and warm material inputs.
5. Inspect standalone and real-workspace renders at normal and minimum sizes.
   Confirm silhouette, face separation, no clipping/distortion, state
   continuity, contained material, and selection/context legibility.
6. Record the source board, normalized stroke conversion, render evidence, and
   fresh visual-review finding for the family. A concrete reference, semantic,
   or real-render failure returns to the owning SVG before integration.

The repeatable measurement checks are listed in
[MEASUREMENTS.md](MEASUREMENTS.md#verification); the canonical material and
normalization boundary is [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md).
