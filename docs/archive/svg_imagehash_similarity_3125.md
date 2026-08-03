# SVG imagehash similarity and normalization-requirement census

Scope: the full wild corpus of 3125 `*.svg` files under `OTHER_REPOS/`
(bioicons, scienceicons, UI, SVG test sets). Two questions are answered:

- How visually similar is each SVG before vs after v3 normalization, and how
  consistent is the render across browser engines? (imagehash)
- How many SVGs carry clipping and each other normalization requirement,
  independent of whether the file is accepted or rejected? (feature census)

Ground truth for similarity is the browser render itself (chromium + firefox);
perceptual hashes (phash primary, dhash secondary) are the numeric signal.

Source artifacts:

- [svg_visual_regression.md](../active_plans/reports/svg_visual_regression.md) /
  [svg_visual_regression.json](../active_plans/reports/svg_visual_regression.json) -- full imagehash run.
- [svg_feature_census.md](../active_plans/reports/svg_feature_census.md) /
  [svg_feature_census.json](../active_plans/reports/svg_feature_census.json) -- per-file feature census.
- [svg_gradient_fix_verification.md](reports/svg_gradient_fix_verification.md) -- the two
  real regressions the harness caught, and their fixes.
- [normalize_svg_v3_findings.md](normalize_svg_v3_findings.md) -- ranked next
  feature to graduate.

Harness: `tests/e2e/e2e_svg_visual_regression.py --full` (before/after, both
engines) and `tools/svg_feature_census.py` (read-only feature scan). Both run
the current `tools/normalize_svg_v3.py` fresh, so counts reflect the live gate,
not a stale verdict cache.

## Headline

- 3125 corpus files. 721 (23.1%) normalize; 2404 reject with a reason code.
- imagehash ran on all 721 normalizable files in both engines: 1442 renders per
  engine, 0 render errors.
- Cross-engine agreement on normalized output is strong: 627 of 721 (87.0%)
  perceptually identical chromium-vs-firefox, 43 (6.0%) divergent.
- Before/after phash "divergence" is high (about 47%) but is dominated by
  intended viewBox reframing (crop-to-bbox), not content loss. The two genuine
  color regressions ever found (gradient placement, stroke-width scaling) were
  caught by this harness and are already fixed.
- Clipping is the single largest normalization requirement: 1393 files (44.6%)
  carry a clipPath, and 1119 of them reject as complex. Widening the simple-clip
  allowlist remains the highest-value next feature.

## Imagehash similarity (721 normalizable files, both engines)

Distance is phash hamming on a 64-bit hash. identical = 0-2, minor = 3-6,
divergent = >6.

### Before vs after normalization

| Engine | identical | minor | divergent | render errors | worst phash |
| --- | --- | --- | --- | --- | --- |
| chromium | 212 (29.4%) | 173 (24.0%) | 336 (46.6%) | 0 | 42 |
| firefox | 218 (30.2%) | 161 (22.3%) | 342 (47.4%) | 0 | 42 |

### Cross-engine consistency (normalized output, chromium vs firefox)

| Classification | Files | Percent |
| --- | --- | --- |
| identical | 627 | 87.0% |
| minor | 51 | 7.1% |
| divergent | 43 | 6.0% |
| unavailable | 0 | 0.0% |

### Reading the divergence

A high before/after phash distance is expected and usually benign. v3's job is
to crop to the drawn bbox and rewrite the viewBox; phash is framing-sensitive,
so any legitimate reframe scores as "divergent" even when every pixel of the
object is faithful. The worst offenders confirm this:

- `plasmid-3.svg`, `cell_membrane_arc.svg`, `plasmid-4.svg` (phash 42): authored
  viewBox clipped content that v3 correctly expands to show -- a framing change,
  not a regression. Cross-engine hamming is 0 (both engines render the
  normalized file identically).
- `cpu.svg` (phash 40): the known reframe; render-verified full-color in both
  engines after the gradient + stroke fixes. dhash dropped 41 -> 33; the
  residual phash is the no-crop viewBox expansion, documented in
  [svg_gradient_fix_verification.md](reports/svg_gradient_fix_verification.md).

The trustworthy fidelity signal is cross-engine agreement: 87% identical with 0
render errors means the normalized SVGs render consistently across the two
engines the product ships in. The 43 cross-engine-divergent files are the
inspect-first set (gallery PNGs under `test-results/svg_visual_regression/`).

### Why before/after phash is not the gate

phash penalizes intended reframing. The harness keeps it as a tripwire (it did
catch the two real regressions below) but uses dhash and the browser render as
corroboration. A file is a suspected regression only when the before/after
distance is high AND the render shows dropped or recolored content -- not when
the object is simply re-cropped.

### Regressions this harness caught (already fixed)

The imagehash run is not just descriptive; it found two real bugs that bbox math
and unit tests missed, both visible only in render:

- userSpaceOnUse gradient coordinates were shifted by the crop delta, mis-placing
  the paint and collapsing gradients to a single stop color.
- transform flatten did not scale `stroke-width`, so `cpu.svg`'s mesh stroke
  thickened about 2.4x and filled its hole cutouts with the mesh color.

Both fixed and render-verified colorful in both engines. Details in
[svg_gradient_fix_verification.md](reports/svg_gradient_fix_verification.md).

## Normalization-requirement census (all 3125 files)

Feature presence is counted per file and is independent of the verdict: a file
may carry a clipPath yet be rejected for text, so the primary rejection reason
alone undercounts how common each requirement is. This census walks every
element of every file.

### Feature prevalence

| Requirement | Files | Percent |
| --- | --- | --- |
| clipPath | 1393 | 44.6% |
| inline style | 1228 | 39.3% |
| transform attribute | 965 | 30.9% |
| nested groups (depth >= 2) | 894 | 28.6% |
| `<style>` block | 729 | 23.3% |
| non-ASCII id | 543 | 17.4% |
| shape: rect | 407 | 13.0% |
| gradient | 387 | 12.4% |
| text | 314 | 10.0% |
| shape: ellipse | 291 | 9.3% |
| shape: circle | 290 | 9.3% |
| shape: polygon | 196 | 6.3% |
| foreignObject | 164 | 5.2% |
| attribution (dc/cc/rdf) | 150 | 4.8% |
| image | 119 | 3.8% |
| shape: line | 114 | 3.6% |
| use / symbol | 102 | 3.3% |
| filter | 54 | 1.7% |
| shape: polyline | 42 | 1.3% |
| marker | 37 | 1.2% |
| mask | 31 | 1.0% |
| script / handler | 24 | 0.8% |
| pattern | 16 | 0.5% |
| parse error | 8 | 0.3% |

### Verdict distribution (current gate)

| Verdict | Files | Percent |
| --- | --- | --- |
| CLIPPATH_UNSUPPORTED_COMPLEX | 1120 | 35.8% |
| normalized | 721 | 23.1% |
| STYLE_GEOMETRY_UNSUPPORTED | 482 | 15.4% |
| TEXT_UNSUPPORTED | 295 | 9.4% |
| DOCTYPE_OR_ENTITY | 234 | 7.5% |
| EMBEDDED_RASTER_UNSUPPORTED | 73 | 2.3% |
| USE_OR_SYMBOL_UNSUPPORTED | 38 | 1.2% |
| UNSUPPORTED_TRANSFORM | 34 | 1.1% |
| FILTER_UNSUPPORTED | 32 | 1.0% |
| MARKER_UNSUPPORTED | 22 | 0.7% |
| SCRIPT_OR_HANDLER | 21 | 0.7% |
| EMPTY_GEOMETRY | 19 | 0.6% |
| FOREIGNOBJECT_UNSUPPORTED | 15 | 0.5% |
| PARSER_ERROR | 7 | 0.2% |
| UNRESOLVED_REFERENCE | 5 | 0.2% |
| PATTERN_UNSUPPORTED | 2 | 0.1% |
| MASK_UNSUPPORTED | 2 | 0.1% |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 | 0.1% |
| UNSUPPORTED_UNIT | 1 | 0.0% |

The primary-reason verdict counts a file once, against the first refusal that
fires, so they understate raw feature load. Example: 234 files reject for
DOCTYPE before their clipPath or transform is ever assessed.

### Clipping deep-dive

1393 files carry a clipPath (44.6% of corpus). Their verdicts:

| Verdict | Files |
| --- | --- |
| CLIPPATH_UNSUPPORTED_COMPLEX | 1119 |
| TEXT_UNSUPPORTED | 96 |
| DOCTYPE_OR_ENTITY | 59 |
| normalized | 58 |
| USE_OR_SYMBOL_UNSUPPORTED | 23 |
| STYLE_GEOMETRY_UNSUPPORTED | 15 |
| EMBEDDED_RASTER_UNSUPPORTED | 7 |
| UNSUPPORTED_TRANSFORM | 6 |
| SCRIPT_OR_HANDLER | 3 |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 |
| MARKER_UNSUPPORTED | 2 |
| FOREIGNOBJECT_UNSUPPORTED | 2 |
| FILTER_UNSUPPORTED | 1 |

Only 58 clip-bearing files normalize today; the simple-clip allowlist is
deliberately narrow. 1119 reject specifically because the clip is complex. This
is the largest single block of rejected files in the corpus and the strongest
data-driven case for widening the simple-clip allowlist (stroke-only clip
targets, multi-shape clips) as the next feature to graduate.

### Transform deep-dive

965 files carry a `transform=` attribute (30.9% of corpus). Their verdicts:

| Verdict | Files |
| --- | --- |
| TEXT_UNSUPPORTED | 277 |
| normalized | 214 |
| DOCTYPE_OR_ENTITY | 142 |
| CLIPPATH_UNSUPPORTED_COMPLEX | 64 |
| EMBEDDED_RASTER_UNSUPPORTED | 63 |
| STYLE_GEOMETRY_UNSUPPORTED | 62 |
| UNSUPPORTED_TRANSFORM | 34 |
| FILTER_UNSUPPORTED | 30 |
| USE_OR_SYMBOL_UNSUPPORTED | 23 |
| SCRIPT_OR_HANDLER | 18 |
| MARKER_UNSUPPORTED | 17 |
| FOREIGNOBJECT_UNSUPPORTED | 13 |
| UNRESOLVED_REFERENCE | 5 |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 |
| PATTERN_UNSUPPORTED | 1 |

Transform flattening works: of the 965 transform-bearing files, only 34 reject
on the transform itself (`UNSUPPORTED_TRANSFORM`, the non-uniform-stroke and
shared-paint cases). The rest reject for an unrelated higher-priority reason
(text, DOCTYPE) or normalize cleanly. Transform support is not the bottleneck;
clipping is.

## How hard was the requirement summary

Low effort. The feature census is one read-only script
(`tools/svg_feature_census.py`, about 400 lines) that parses each SVG once with
lxml, sets a boolean per feature, and cross-tabs against the live verdict from
`normalize_svg_v3.normalize_svg_file`. Full corpus scan runs in well under a
minute. It is re-runnable any time the gate changes; the JSON carries the
per-file feature matrix for any further slicing.

The only subtlety worth stating: presence must be counted independently of the
verdict. Reusing the rejection reason codes alone would have undercounted
clipping by roughly 20x (58 normalized-with-clip vs 1393 clip-bearing), because
most clip files reject on the clip and never report their other features.

## Recommendation

The data ranks the next investment unambiguously: widen the simple-clip
allowlist. clipPath is present in 44.6% of the corpus, accounts for the largest
rejected block (1119 complex), and only 58 clip files normalize today. Every
other normalization requirement is either already handled (transform: 931 of 965
do not reject on transform) or a deliberate hard reject (text, DOCTYPE, raster,
script). See [normalize_svg_v3_findings.md](normalize_svg_v3_findings.md) for the
allowlist-widening sketch.
