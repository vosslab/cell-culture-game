# SVG exemplar size and flatness slice

## Status

This is the historical four-family M3 slice requested by
[svg_visual_quality_rebuild_plan-v2.md](../active/svg_visual_quality_rebuild_plan-v2.md)
E3 and E7.
It records the pre-recovery measurement state, not acceptance of the present
visual language. The supported current automated census is now published in
[svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md) with
its placement-level data in
[svg_visual_size_flatness_census.json](svg_visual_size_flatness_census.json).
This slice remains the manual major-physical-plane exemplar record; the
automated census uses its separately named visible-root-paint-cluster proxy.

## Scope

The four planned archetypes are represented by nine shipped assets:

| Archetype                  | Covered assets                                                                    | Render mode    | Workspaces reached by current placements      |
| -------------------------- | --------------------------------------------------------------------------------- | -------------- | --------------------------------------------- |
| Transparent vessel         | `t75_flask_empty`, `t75_flask_filled`                                             | Inline DOM SVG | `bench`, `hood`, `microscope`                 |
| Hinged benchtop instrument | `centrifuge`, `centrifuge_running`                                                | `<img>` leaf   | `bench`                                       |
| Handheld tool              | `p10_micropipette`, `p20_micropipette`, `p200_micropipette`, `p1000_micropipette` | Inline DOM SVG | `bench`, `cell_counter`, `hood`               |
| Material-rendered vessel   | `falcon_15ml`                                                                     | Inline DOM SVG | `bench`, `cell_counter`, `hood`, `microscope` |

`falcon_15ml` is the stronger material exemplar: it explicitly declares
`data-vlab-rendering="material"`; its material layers name `bottom`, `body`,
and `surface`, and its dependent objects declare `fill_height` with
`capacity_ml: 15`. The currently generated manifest marks every asset above
except the two centrifuge states `requires_dom_svg: true`; the renderer uses
that field to select inline SVG versus the `<img>` leaf path.

Evidence: `assets/equipment/variable_volume/falcon_15ml.svg`,
`content/objects/bottle/conical_15ml.yaml`,
`generated/svg_manifest.ts`, and
`src/scene_runtime/renderer/svg_manifest_loader.ts`.

## Flatness method and result

Plane count is a manual, reproducible visible-massing count. Count each major
filled surface that asserts a distinct physical orientation or recess; exclude
outlines, highlights, text and graduations, controls, liquid-only overlays,
hidden anchors, and repeated rotor wells. This measures the large forms that
can make an object read as volume, not SVG element count. Ellipse and transform
columns are literal source-token checks: `<ellipse`, `rotate(`, `skewX(`,
`skewY(`, or `matrix(`. A matrix is reported as a transform even where it is
not a rotation.

| Asset or same-geometry state pair      | Planes | Ellipses | Rotation or skew syntax          | Evidence for the plane count                                                                                                                                                     |
| -------------------------------------- | -----: | -------: | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `t75_flask_empty`, `t75_flask_filled`  |      9 |   3 each | Yes, 2 transforms each           | Two cap masses plus seven separately filled chamber faces.                                                                                                                       |
| `centrifuge`, `centrifuge_running`     | 2 each |     6, 0 | Yes, 4 transforms; no transforms | Outer housing and recessed control face; circular lid/rotor rings do not assert a changed viewing plane.                                                                         |
| `p10_micropipette`, `p20_micropipette` | 5 each |   0 each | No                               | Rear body plane, main housing, collar, sleeve, and tapered shaft/tip establish one fixed form; material is limited to the contained disposable tip.                              |
| `p200_micropipette`                    |      5 |        0 | No                               | Rear body plane, main housing, collar, ejector sleeve, and tapered shaft/tip establish the tool mass; one material-rendered asset limits liquid to the contained disposable tip. |
| `p1000_micropipette`                   |      5 |        0 | No                               | Rear body plane, wider housing, collar, sleeve, and broad tapered shaft/tip establish the high-capacity tool mass; material is limited to the contained disposable tip.          |
| `falcon_15ml`                          |      3 |        0 | No                               | Front cylindrical body, narrow right-side face, and converging conical bottom; material highlights and shadows do not add a plane.                                               |

The T75, centrifuge, and micropipette families now all carry more than one
major physical mass by the stated method. The material vessel communicates
cylinder/cone volume through layered face values and curves rather than literal
SVG ellipses. These are descriptive measurements, not a rule that every
future asset must have a particular token.

Evidence: source inspection of the nine files named in the table. The T75
chamber has seven filled paths inside `id="chamber"`; the four micropipettes
each preserve one fixed physical form while their contained tip is the only
material-painted region; `p200_micropipette` and `falcon_15ml` label fixed,
base, shadow, highlight, and liquid-part groups in source order.

## Rendered placement sizes

`W x H` is the visual art box after the pipeline's actual
`reflowUniformScale`, in scene-percent units. Min, median, and max are actual
placements ranked by visual-box area; for the two-placement centrifuge family,
the upper median is the maximum. They therefore preserve a real placement
name instead of inventing a non-existent average box.

The canonical conversion is `W * 19.2` by `H * 10.8` at 1920 x 1080. The
small-frame conversion uses the exact per-scene `minimum_frame` emitted by
`derive_scene_interaction_geometry`: it starts its valid 16:9 search at 180 px
height and tests the emitted integer frame for bounds and hit-area ambiguity.
This is stronger evidence than treating 1280 px, the PNG tool default, as a
minimum. The visual box is deliberately not expanded to the 44 px interaction
core.

| Family and placements                                                   | Applied scale | Box (% frame W x % frame H)                                                                                                         | Canonical box (px)                                                                | Smallest valid frame and box (px)                         |
| ----------------------------------------------------------------------- | ------------: | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| T75 min: `centrifuge_workspace/center_t75_flask_new_reseed`             |          0.31 | 2.93 x 1.67                                                                                                                         | 56.32 x 18.00                                                                     | 546 x 307; 16.02 x 5.12                                   |
| T75 median: `hood_workspace/center_original_t75_flask`                  |          0.29 | 3.45 x 1.96                                                                                                                         | 66.15 x 21.14                                                                     | 655 x 368; 22.57 x 7.21                                   |
| T75 max: `passage_hood_detachment_microscope_view/instrument_t75_flask` |          0.40 | 5.92 x 3.36                                                                                                                         | 113.66 x 36.33                                                                    | 479 x 269; 28.36 x 9.05                                   |
| Centrifuge min: `centrifuge_workspace/center_centrifuge_spin`           |          0.31 | 7.48 x 18.19                                                                                                                        | 143.61 x 196.49                                                                   | 546 x 307; 40.84 x 55.88                                  |
| Centrifuge median/max: `bench_basic/center_centrifuge`                  |          0.88 | 21.38 x 52.01                                                                                                                       | 410.50 x 561.66                                                                   | 452 x 254; 96.64 x 132.09                                 |
| Micropipette source rows                                                |        varies | See the current `p10_micropipette`, `p20_micropipette`, `p200_micropipette`, and `p1000_micropipette` rows in the generated census. | One material-rendered form per capacity; do not infer an empty/filled asset pair. | Each row reports its real min, median, and max placement. |
| Falcon min: `centrifuge_workspace/rear_center_conical_rack`             |          0.31 | 0.44 x 4.66                                                                                                                         | 8.45 x 50.37                                                                      | 546 x 307; 2.40 x 14.32                                   |
| Falcon median: `dilution_workspace/carb_intermediate`                   |          0.94 | 2.25 x 23.86                                                                                                                        | 43.22 x 257.72                                                                    | 539 x 303; 12.13 x 72.35                                  |
| Falcon max: `cell_counter_basic/rear_trypan_blue_tube`                  |          0.97 | 3.78 x 40.12                                                                                                                        | 72.67 x 433.29                                                                    | 383 x 215; 14.50 x 86.26                                  |

Placement population: T75 5 placements from `t75_flask` and `t75_flask_new`;
centrifuge 2; micropipette 16 across the four canonical P10, P20, P200, and
P1000 material forms; Falcon 23
across `bme_tube`, `conical_15ml`, `conical_15ml_rack`,
`conical_tube_for_dilution`, `laemmli_4x_tube`,
`microtube_15ml_intermediate`, `mtt_solution_tube`, and `trypan_blue_tube`.
The single-form material tools do not have empty/filled SVG companions; material
amount changes only the compiled paint within their declared region.

## Commands, results, and handoff

Commands run from the repository root:

```bash
source source_me.sh && bash pipeline/build_generated.sh
node --import tsx tools/scene_scale_report.mjs --all
```

The generated build at capture exited 0, emitted 129 objects, 70 asset specs, 135 SVG
entries, and 57 scenes. The scale report exited 0 and found 57 scenes: 14
overloaded, 10 dense, and 33 healthy. Its relevant applied-scale evidence
includes `centrifuge_workspace` at 0.291, `bench_basic` at 0.878,
`drug_dilution_setup_bench_setup` at 0.672, and `dilution_workspace` at 0.922.

For the box table, a read-only one-shot module import invoked the same public
`runPipeline(scene, { library, assets, viewport: { w: 1920, h: 1080 } })`
shape used by `tools/scene_scale_report.mjs`, then read final
`_visualWidth`, `_height`, `reflowUniformScale`, workspace, placement name,
and `interactionGeometry.minimum_frame`. The layout implementation confirms
that terminal rescale multiplies `_visualWidth` and the natural height by the
one uniform factor before final placement.

## Relationship to the full census

The automated census is now generated by
`node --import tsx tools/scene_scale_report.mjs --write-census-report` and is
published as [svg_visual_size_flatness_census.md](svg_visual_size_flatness_census.md)
and [svg_visual_size_flatness_census.json](svg_visual_size_flatness_census.json).
It preserves the real `runPipeline` source of truth and records every final
placement's scene, workspace, owner object, resolved asset bindings,
`reflowUniformScale`, visual box, and serialized `minimum_frame`; it also
records declared nominal sizes for unplaced assets.

The census's `visible root clusters` field is deliberately a named structural
proxy, not this slice's manual major-physical-plane count and not a visual
quality verdict. This report retains the latter for four archetypes because it
records the physical-face interpretation and the source evidence needed to
evaluate their intended dimensionality.
