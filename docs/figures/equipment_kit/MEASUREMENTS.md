# Equipment kit measurements

## Purpose and scope

This is the WP-X5 measurement handoff for M8 in
[svg_visual_quality_rebuild_plan-v2.md](../../active_plans/active/svg_visual_quality_rebuild_plan-v2.md).
It measures the current M7 production exemplars, rather than treating a candidate
fixture or an old state pair as a production constraint.

The sources are the two T75 states,
[centrifuge.svg](../../../assets/equipment/binary_state/centrifuge.svg),
[centrifuge_running.svg](../../../assets/equipment/binary_state/centrifuge_running.svg),
[p200_micropipette.svg](../../../assets/equipment/variable_volume/p200_micropipette.svg),
and [falcon_15ml.svg](../../../assets/equipment/variable_volume/falcon_15ml.svg).
T75 sources are [t75_flask_empty.svg](../../../assets/equipment/binary_state/t75_flask_empty.svg)
and [t75_flask_filled.svg](../../../assets/equipment/binary_state/t75_flask_filled.svg).

The reported size facts come from the current generated M3
[svg_visual_size_flatness_census.md](../../active_plans/reports/svg_visual_size_flatness_census.md)
and its adjacent JSON. The older four-family slice is historical pre-recovery
evidence and is not used for the numbers below. The P200 source is the
pre-production single, material-rendered asset; it replaces the former
loaded/unloaded pair without a compatibility alias.

## Measurement method

ViewBox dimensions and authored stroke spans are read directly from the current
SVG XML. Placement widths come from the generated census, after scene reflow.
This report keeps those two measurements separate: transforms and filled-face
boundaries mean a raw `stroke-width * placement-width / viewBox-width`
calculation is not a universal visible-line measurement. Hidden anchors and
runtime overlays are excluded.

"Smallest" is the smallest CSS width reached across current valid frames.
"Representative" is an actual normal placement, not an invented average: T75
`hood_workspace/center_original_t75_flask`, centrifuge
`bench_basic/center_centrifuge`, P200
`sdspage_prepare_sample_mix_batch_workspace/center_p200_sample_micropipette`,
and Falcon `dilution_workspace/carb_intermediate`.

## Stroke measurements

| Archetype and current source state(s) | ViewBox            | Smallest CSS box | Representative CSS box | Current authored visible stroke span                    | Interpretation                                                                                                |
| ------------------------------------- | ------------------ | ---------------- | ---------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| T75 empty / filled                    | `299.901 x 95.865` | `16.21 x 5.18`   | `66.15 x 21.14`        | `0.14` to `0.19` inside the authored scaled flask group | Transparent faces and final near contours carry identity; do not thicken every internal edge.                 |
| Centrifuge open / running             | `279.833 x 368.9`  | `41.35 x 54.50`  | `421.68 x 555.89`      | `0.63961238` to `4.6371894`                             | Detailed direct Servier geometry uses filled nested faces plus sparse strokes; preserve the source hierarchy. |
| P200 material tool                    | `120 x 460`        | `6.11 x 23.43`   | `35.02 x 134.23`       | `1` to `2.5`                                            | The long silhouette and fixed-shell/material-tip boundary matter before small display detail.                 |
| Falcon 15 mL material vessel          | `70.68 x 421.427`  | `2.43 x 14.50`   | `42.59 x 253.94`       | `0.47970927` to `1.4`                                   | The cap/body/cone silhouette and semantic material faces carry the vessel at small size.                      |

The paired T75 and centrifuge states keep one viewBox and physical projection.
These measurements were refreshed after the restored T75 and direct Servier
centrifuge replaced the rejected candidate-era forms.

### Settled floor rule

The proposed 0.75 CSS px detail and 1.0 CSS px contour values are useful
**normal-size review targets**, but are false as literal-minimum requirements.
At the actual minima, a 16 by 5 px T75 and 2 by 14 px Falcon cannot carry
anatomy independent of silhouette, filled faces, and scene context.

Use this measured rule for new batch work:

- At a normal, task-relevant placement, target 1.0 CSS px for a stroked outer
  contour and 0.75 CSS px for a detail that must itself communicate identity.
- At a literal M3 minimum, do not enlarge or accumulate strokes to force those
  numbers. Simplify sub-floor detail away; preserve silhouette, filled-face
  separation, the scene's selection treatment, and the 44 px interaction core.
- A face boundary or overlap can carry an edge without a stroke. The current
  T75 and Falcon demonstrate that exception, so the targets are not a
  byte-level rejection rule for pre-existing production geometry.
- Record the current source stroke span and real placement box in a family
  review whenever a new viewBox or ordinary placement width differs materially
  from these exemplars. Judge the rendered result when transforms or filled
  faces make a scalar conversion misleading.

This keeps the stated starting values where they are meaningful, while avoiding
the unsupported conclusion that one authored width works at all scene scales.

## Literal production swatches

These are every literal hexadecimal paint value in the current sources. They
are source facts, not a demand that a future family use every swatch. `#fff`
and `#ffffff` remain separate because the authored SVGs spell them separately.

| Archetype / current source state(s) | Literal swatches                                                                                                                                                                                                                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T75 empty / filled                  | `#236aa4`, `#274653`, `#276fb7`, `#2b79b9`, `#78b9ca`, `#7a7c7d`, `#8fcbd9`, `#a7d9e5`, `#b47cab`, `#c9e9f0`, `#e8f6fa`                                                                                                                                                                                              |
| Centrifuge open / running           | `#000`, `#019ebb`, `#07487c`, `#08619f`, `#1b1d1e`, `#1c1f1f`, `#1d6e38`, `#303434`, `#333`, `#35b85a`, `#3b3e3e`, `#464b4c`, `#484d4e`, `#618e99`, `#6c7273`, `#7fa6af`, `#83b1bc`, `#929899`, `#92d6dd`, `#9acc80`, `#b2cbd1`, `#b4ccd2`, `#c1d6db`, `#c3d7dc`, `#dee9ec`, `#e3ecee`, `#f1f6f7`, `#f4fff6`, `#fff` |
| P200 material tool                  | `#505c66`, `#53636f`, `#61728e`, `#829caf`, `#89a5ba`, `#9fb5c3`, `#a9b9ca`, `#a9c7d3`, `#acbbc9`, `#adbdcf`, `#c5d4de`, `#cfe2e7`, `#d88943`, `#d9e2ec`, `#e1e8f0`, `#e4a05c`, `#edf1f5`, `#f4fbfc`, `#f6fafc`, `#f7fbfc`, `#f8fbfd`, `#fff`                                                                        |
| Falcon 15 mL material vessel        | `#000`, `#083f7c`, `#333`, `#4776b5`, `#88bcc9`, `#96add2`, `#990147`, `#9bb0d4`, `#9fc9d4`, `#ae0152`, `#b1d4dc`, `#bdcae2`, `#c2015a`, `#c6015a`, `#c76a95`, `#d186a8`, `#d8dfee`, `#d9f2f6`, `#daebef`, `#e04e82`, `#e67198`, `#f0adc0`, `#f5f5f5`, `#fff`                                                        |

## Face-value evidence

Counts below mean distinct filled or stroked values deliberately used to
separate a physical material or functional subassembly. They exclude invisible
anchors, repeated copies of one value, and a state-only indicator unless named.

| Archetype  | Material / subassembly |                    Face-value count | Source evidence                                                                                                                                       |
| ---------- | ---------------------- | ----------------------------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| T75        | Clear chamber          |                                   7 | Seven chamber planes in `id="chamber"`: near, lower, far, top, inner highlight, upper, and neck-side.                                                 |
| T75        | Cap                    |                                   4 | Three blue molded cap values plus the gray molded points; cap geometry and neck overlap identify the part.                                            |
| T75        | Contained liquid       |                                   1 | Filled state adds one level, clipped medium plane behind unchanged chamber contours.                                                                  |
| Centrifuge | Housing and cavity     |          many source-authored faces | The detailed direct Servier source uses nested light housing, dark well, rotor, feet, and control values rather than a three-plane repository redraw. |
| P200       | Fixed tool shell       |                                   3 | Light front, mid front, and darker rear plane establish the shallow tool mass.                                                                        |
| P200       | Display recess         |                                   3 | Dark recess, pale display face, and blue digits.                                                                                                      |
| P200       | Collar                 |                                   2 | Orange upper and lighter lower collar face.                                                                                                           |
| P200       | Tip liquid             |                   5 semantic layers | Bottom base, body base, body highlight, body shadow, and surface highlight.                                                                           |
| Falcon     | Fixed clear vessel     |    5 back faces plus front contours | Direct Servier body, inner body, side highlight, cone, and final contour structure remain distinct.                                                   |
| Falcon     | Cap                    | detailed direct-source construction | Cap body, repeated ribs, top ellipse, lower rim, and side values remain source-authored rather than reduced to a palette quota.                       |
| Falcon     | Liquid                 |                  11 semantic layers | Two bottom, four body, and five surface groups preserve explicit base, highlight, and shadow roles.                                                   |

## Exemplar-derived visual principles

These are demonstrated construction choices, not numerical measurements:

- **Projection is object-specific and state-stable.** Prefer a frontal or
  near-orthographic view for controls and paired instruments. Use shallow
  perspective only when it reveals a real characteristic structure, such as a
  vessel neck, cavity, or hinge. Never rotate or skew an object merely to imply
  depth, and never change projection across a state pair.
- **Light direction.** Use upper-left/front light: pale top planes and left
  highlights lead, while right-side faces and true recesses receive the darker
  value. Preserve credible source lighting rather than forcing a global
  projection or recoloring direct Servier artwork into one palette.
- **Depth cue.** A dark value denotes a real far plane, recess, or overlap.
  The centrifuge uses a seated rotor and rear-hinged lid; the P200 uses one
  sleeve over the shaft; the T75 places the cap over the angled neck; the
  Falcon uses a right face and cone shadow. It is not decorative striping.
- **Material cue.** Transparent and material-rendered forms retain explicit
  layers and clipped liquid. Keep the P200 material in the disposable tip and
  the Falcon in its direct-root material layers; no visual treatment moves
  material semantics into a fixed housing.

## Verification

The facts above were checked against authored XML and the current generated M3
census. The following commands are the repeatable evidence
route from the repository root:

```bash
node --import tsx tools/scene_scale_report.mjs --write-census-report
python3 tests/check_ascii_compliance.py docs/figures/equipment_kit/MEASUREMENTS.md
python3 -m pytest tests/test_markdown_links.py
```

The current source line hierarchy and the rendered-size interpretation also
follow the `svg-creator-expert` object-illustration guidance: inspect at the
actual smallest and representative delivery sizes, then let silhouette,
overlap, and face separation carry form when a sub-pixel detail cannot survive.
