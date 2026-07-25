# SVG v3 visual regression report

**Sample mode:** sample (300 of 833 passing files, screened from 1500 candidates, seed=42)
**Files processed:** 300
**Engines:** chromium, firefox
**Render size:** 256x256 px
**Hash type:** phash (primary), dhash (secondary)

> NOTE: v3 flattens simple clipPaths (allowlist) and rejects complex ones.
> Only the small simple-clip subset is normalized; most clip-bearing files
> are rejected (CLIPPATH_UNSUPPORTED_COMPLEX).

> NOTE: The wild verdicts JSON was stale at time of run. This harness
> pre-screens by running the normalizer fresh on all candidates.

## Chromium engine

| Classification | Count |
| --- | --- |
| identical (distance 0-2) | 79 |
| minor (distance 3-6) | 71 |
| divergent (distance >6) | 150 |
| render errors | 0 |
| worst phash distance | 34 |

## Firefox engine

| Classification | Count |
| --- | --- |
| identical (distance 0-2) | 83 |
| minor (distance 3-6) | 63 |
| divergent (distance >6) | 154 |
| render errors | 0 |
| worst phash distance | 34 |

## Chromium vs Firefox divergence (normalized SVGs)

| Classification | Count |
| --- | --- |
| identical | 275 |
| minor | 18 |
| divergent | 7 |
| unavailable | 0 |

## Top 25 worst offenders

| File | Max phash | chromium phash | chromium class | firefox phash | firefox class | CF hamming |
| --- | --- | --- | --- | --- | --- | --- |
| `duplicate-gradient-stops-pct.svg` | 34 | 34 | divergent | 33 | divergent | 17 |
| `group-no-creation.svg` | 34 | 33 | divergent | 34 | divergent | 15 |
| `path-with-closepath.svg` | 34 | 34 | divergent | 34 | divergent | 0 |
| `flask-3-empty.svg` | 34 | 34 | divergent | 32 | divergent | 8 |
| `stanford_b_debakey_IIIa.svg` | 34 | 34 | divergent | 34 | divergent | 0 |
| `dont-convert-short-color-names.svg` | 33 | 33 | divergent | 33 | divergent | 0 |
| `group-creation.svg` | 33 | 33 | divergent | 33 | divergent | 8 |
| `quot-in-url.svg` | 33 | 33 | divergent | 33 | divergent | 0 |
| `path-quad-optimize.svg` | 32 | 32 | divergent | 32 | divergent | 6 |
| `stanford_a_debakey_II.svg` | 32 | 32 | divergent | 32 | divergent | 0 |
| `polygon-coord-neg.svg` | 31 | 30 | divergent | 31 | divergent | 0 |
| `nucleotide-u-ul.svg` | 30 | 30 | divergent | 28 | divergent | 0 |
| `ascaris-lumbricoides-eggs-2.svg` | 30 | 30 | divergent | 30 | divergent | 0 |
| `flask.svg` | 30 | 30 | divergent | 30 | divergent | 0 |
| `microtube-closed.svg` | 30 | 28 | divergent | 30 | divergent | 2 |
| `penetrating_atherosclerotic_ulcer.svg` | 30 | 30 | divergent | 30 | divergent | 0 |
| `thermometer.svg` | 28 | 22 | divergent | 28 | divergent | 6 |
| `nucleotide-t-ul.svg` | 28 | 28 | divergent | 28 | divergent | 4 |
| `erythrocyte-1.svg` | 28 | 28 | divergent | 28 | divergent | 0 |
| `lymphatic-system.svg` | 28 | 26 | divergent | 28 | divergent | 0 |
| `paranasal-sinus-head.svg` | 28 | 28 | divergent | 28 | divergent | 0 |
| `magnet.svg` | 28 | 28 | divergent | 28 | divergent | 2 |
| `cell-cultuure-quipment-3.svg` | 28 | 18 | divergent | 28 | divergent | 18 |
| `giardia_intestinalis-cyst.svg` | 28 | 26 | divergent | 28 | divergent | 0 |
| `tomato.svg` | 28 | 28 | divergent | 28 | divergent | 0 |

## Worst-offender gallery

Before/after PNG pairs saved under `test-results/svg_visual_regression/` (gitignored).
Files are named `NNN_<stem>_<engine>_orig.png` and `NNN_<stem>_<engine>_norm.png`.

## Visual fidelity assessment

**Chromium:** 26.3% identical, 23.7% minor, 50.0% divergent
**Firefox:** 27.7% identical, 21.0% minor, 51.3% divergent
