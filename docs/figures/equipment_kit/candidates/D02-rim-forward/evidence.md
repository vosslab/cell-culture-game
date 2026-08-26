# D02-rim-forward evidence

## Controlled inputs

Source fixtures: `source/t75_flask.svg`, `source/centrifuge.svg`,
`source/p200_micropipette.svg`, and `source/falcon_15ml.svg`.

Literal swatches: canvas `#F5F7F8`; lit `#E8F0F4`; base `#B9CCD7`;
receding `#7895A5`; recess `#3B5668`; contour `#294657`; clear plastic
`#DDEBF1`; cool probe `#1E40AF`; warm probe `#C0266D`.

## Historical snapshot status

This rejected D02 snapshot is retained implementation evidence only. Its
recorded PNGs and measurements are not regenerated. Review current authored
equipment through `docs/figures/equipment_kit/review.html` instead.

## M0 frozen-source acceptance

`source source_me.sh && python3 -m tools.svg_normalizer.cli --shadow-dry-run -i <source.svg>`

| Source                         | Result        |
| ------------------------------ | ------------- |
| `source/t75_flask.svg`         | `SHADOW-NONE` |
| `source/centrifuge.svg`        | `SHADOW-NONE` |
| `source/p200_micropipette.svg` | `SHADOW-NONE` |
| `source/falcon_15ml.svg`       | `SHADOW-NONE` |

The renderer hashes these frozen sources before and after its derived-raster pass.

## M3 real-size frames and visual boxes

| Archetype    | Normal workspace; frame; visual box                                                                   | Minimum workspace; frame; visual box                                               |
| ------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| T75          | `passage_hood_detachment_hood_workspace/center_flask`; 486 x 273; 16.20 x 5.18                        | `centrifuge_workspace/center_t75_flask_new_reseed`; 555 x 312; 15.41 x 4.93        |
| Centrifuge   | `bench_basic/center_centrifuge`; 452 x 254; 96.64 x 132.22                                            | `centrifuge_workspace/center_centrifuge_spin`; 555 x 312; 39.30 x 53.77            |
| P200         | `sdspage_prepare_sample_mix_batch_workspace/center_p200_sample_micropipette`; 400 x 225; 7.29 x 29.18 | `drug_dilution_setup_bench_setup/right_p200_micropipette`; 523 x 294; 6.71 x 26.85 |
| Falcon 15 mL | `dilution_workspace/carb_intermediate`; 539 x 303; 11.86 x 70.72                                      | `centrifuge_workspace/rear_center_conical_rack`; 555 x 312; 2.31 x 13.78           |

## Evaluator handoff

No ranking is recorded by the compositor. The independent M6 evaluator records
cited silhouette, volume/occlusion, board-fidelity, and small-size findings.
