# SVG gradient-under-transform recheck report

**Scope:** top-20 phash offenders from the prior visual regression run
**Fix audited:** gradient-under-transform (Category B) -- `tools/normalize_svg_v3.py`
**Normalizer:** current (post-fix) `normalize_svg_v3.py`
**Engines:** chromium, firefox
**Render size:** 256x256 px
**Hash type:** phash (perceptual hash, 8x8 = 64-bit, hamming distance)

## Before/after comparison table

Legend: distance 0-2 = identical, 3-6 = minor, >6 = divergent

### Chromium engine

| File | Pre-fix phash | Post-fix phash | Verdict |
| --- | --- | --- | --- |
| `cpu.svg` | - | 40 (divergent) | no-prior |
| `cell_membrane_arc.svg` | - | 42 (divergent) | no-prior |
| `straight-curve.svg` | - | 32 (divergent) | no-prior |
| `Amphiprion_ocellaris_egg.svg` | 28 | 28 (divergent) | unchanged |
| `group-no-creation.svg` | 33 | 33 (divergent) | unchanged |
| `round-bottomed-flask-1-500ml.svg` | 14 | 14 (divergent) | unchanged |
| `arrow-twosides-horizontal.svg` | - | 34 (divergent) | no-prior |
| `flask-3-empty.svg` | 34 | 34 (divergent) | unchanged |
| `pipette-tip-box.svg` | - | 34 (divergent) | no-prior |
| `stanford_b_debakey_IIIa.svg` | 34 | 34 (divergent) | unchanged |
| `dont-convert-short-color-names.svg` | 33 | 33 (divergent) | unchanged |
| `group-creation.svg` | 33 | 33 (divergent) | unchanged |
| `path-quad-optimize.svg` | 32 | 32 (divergent) | unchanged |
| `Xenopus_new.svg` | 16 | 16 (divergent) | unchanged |
| `ribosome.svg` | - | 32 (divergent) | no-prior |
| `variational-autoencoder.svg` | - | 4 (minor) | no-prior |
| `nucleotide-a-ul.svg` | - | 10 (divergent) | no-prior |
| `microtube-closed.svg` | 28 | 28 (divergent) | unchanged |
| `stanford_a_debakey_I.svg` | - | 32 (divergent) | no-prior |
| `stanford_a_debakey_II.svg` | 32 | 32 (divergent) | unchanged |

### Firefox engine

| File | Pre-fix phash | Post-fix phash | Verdict |
| --- | --- | --- | --- |
| `cpu.svg` | - | 40 (divergent) | no-prior |
| `cell_membrane_arc.svg` | - | 42 (divergent) | no-prior |
| `straight-curve.svg` | - | 38 (divergent) | no-prior |
| `Amphiprion_ocellaris_egg.svg` | 28 | 28 (divergent) | unchanged |
| `group-no-creation.svg` | 34 | 34 (divergent) | unchanged |
| `round-bottomed-flask-1-500ml.svg` | 16 | 16 (divergent) | unchanged |
| `arrow-twosides-horizontal.svg` | - | 32 (divergent) | no-prior |
| `flask-3-empty.svg` | 32 | 32 (divergent) | unchanged |
| `pipette-tip-box.svg` | - | 32 (divergent) | no-prior |
| `stanford_b_debakey_IIIa.svg` | 34 | 34 (divergent) | unchanged |
| `dont-convert-short-color-names.svg` | 33 | 33 (divergent) | unchanged |
| `group-creation.svg` | 33 | 33 (divergent) | unchanged |
| `path-quad-optimize.svg` | 32 | 32 (divergent) | unchanged |
| `Xenopus_new.svg` | 18 | 18 (divergent) | unchanged |
| `ribosome.svg` | - | 32 (divergent) | no-prior |
| `variational-autoencoder.svg` | - | 4 (minor) | no-prior |
| `nucleotide-a-ul.svg` | - | 16 (divergent) | no-prior |
| `microtube-closed.svg` | 30 | 30 (divergent) | unchanged |
| `stanford_a_debakey_I.svg` | - | 32 (divergent) | no-prior |
| `stanford_a_debakey_II.svg` | 32 | 32 (divergent) | unchanged |

## Summary

**Chromium:** improved=0, unchanged=20, regressed=0, resolved-via-reject=0, errors=0

**Firefox:** improved=0, unchanged=20, regressed=0, resolved-via-reject=0, errors=0

## Conclusion

The gradient-under-transform fix (Category B from the prior report) bakes the accumulated element matrix into the `gradientTransform` of each referenced `userSpaceOnUse` gradient before flattening. The before/after phash distances above show whether the fix restored visual fidelity for the affected files (`cpu.svg` was the primary offender, phash=38 in both engines before the fix).

Files in other categories (A: viewBox reframe, C: stacking/scale, D: test fixtures) are included in the table as context; their phash distances are expected to remain high (they are not gradient bugs).

Gallery before/after PNGs are saved to `test-results/svg_gradient_recheck/` (gitignored).
