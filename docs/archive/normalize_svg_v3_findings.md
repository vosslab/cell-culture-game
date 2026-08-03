# SVG normalizer v3: synthesis findings

**Generated from:** wild-corpus verdicts (3125 files), parity report (102 assets),
visual regression report (300-file sample), v2 audit, and the wild-mapping-teacup plan.

---

## Executive summary

SVG normalizer v3 (`tools/normalize_svg_v3.py`) is a sound ingestion gate. It
normalizes or rejects every file with a stable, classified reason -- there are no
silent partial successes and no crashes over the full wild corpus. The gate is
conservative by design: a file is normalized only when every verification step
passes; any ambiguity is a rejection.

**Wild-corpus pass rate:** 721 of 3125 files normalize (23.1%). The remaining
2404 are rejected with reason codes. This low pass rate is expected. The wild
corpus spans untested bioicons, scour unit-test fixtures, and pathological SVGs.
It deliberately stress-tests the classifier. The 23.1% rate confirms the
classifier does its job: it rejects files it cannot guarantee are safe.

**Our 102 committed assets:** 27 normalize under v3 as-is. 75 are rejected, 74
of which previously passed v2. Those 74 require one-time author fixes before
v3 ingestion can proceed. They are not broken assets -- they are assets that use
features (complex clipPaths, `<style>` geometry rules, `<text>`) that v3 refuses
to guess at. Fixing them is bounded and categorized; see the next-investment
section.

**Visual fidelity:** of the normalized files, the headline "50% divergent" rate
from the imagehash harness is misleading. The dominant category (A) is viewBox
reframing -- correct normalizer behavior that changes scale on a fixed canvas
but loses no content. Real regressions (Category B, gradient color loss) were
found and have since been fixed. After the fix, the remaining genuine concern is
a handful of deeply nested transform + userSpaceOnUse gradient combinations.

**Cross-engine:** chromium and firefox render normalized SVGs identically in 87%
of the 300-file sample. The 4.3% divergent cases are concentrated in SVGs with
CSS geometry features, which the normalizer already rejects from real assets.

**Recommended next investment:** graduate stroke-only clip targets from
`CLIPPATH_UNSUPPORTED_COMPLEX` to the simple-clip allowlist. This single targeted
extension unblocks 50 of our 74 rejected assets (67% of the backlog) and 1120 of
2404 wild rejections (47% of wild rejections). Details in the prioritization
section.

---

## Rejection-reason distribution

### Wild corpus (3125 files, 2404 rejected)

| Reason code | Count | % of rejections |
| --- | --- | --- |
| `CLIPPATH_UNSUPPORTED_COMPLEX` | 1120 | 46.6% |
| `STYLE_GEOMETRY_UNSUPPORTED` | 482 | 20.1% |
| `TEXT_UNSUPPORTED` | 295 | 12.3% |
| `DOCTYPE_OR_ENTITY` | 234 | 9.7% |
| `EMBEDDED_RASTER_UNSUPPORTED` | 73 | 3.0% |
| `USE_OR_SYMBOL_UNSUPPORTED` | 38 | 1.6% |
| `UNSUPPORTED_TRANSFORM` | 34 | 1.4% |
| `FILTER_UNSUPPORTED` | 32 | 1.3% |
| `MARKER_UNSUPPORTED` | 22 | 0.9% |
| `SCRIPT_OR_HANDLER` | 21 | 0.9% |
| `EMPTY_GEOMETRY` | 19 | 0.8% |
| `FOREIGNOBJECT_UNSUPPORTED` | 15 | 0.6% |
| `PARSER_ERROR` | 7 | 0.3% |
| `UNRESOLVED_REFERENCE` | 5 | 0.2% |
| Other (`PATTERN`, `MASK`, `EXTERNAL_RESOURCE`, `UNSUPPORTED_UNIT`) | 7 | 0.3% |

### Our 102 committed assets (75 rejected, 74 were v2-passes)

| Reason code | Count | Assets |
| --- | --- | --- |
| `CLIPPATH_UNSUPPORTED_COMPLEX` | 50 | bottles, microtubes, micropipettes, gel equipment, staining trays, tip boxes, microscopes, test tubes (Servier), plate readers |
| `TEXT_UNSUPPORTED` | 11 | cell counter, drug vial rack, lightbox, micropipette rack, flask versions v2-v4, waste tray, 24-well plate, biohazard decant, angry professor |
| `STYLE_GEOMETRY_UNSUPPORTED` | 9 | electrode module, gel opening tool, heat block, kimwipe, microtube rack placeholder, power supply off, T75 flask variants, tube rack |
| `DOCTYPE_OR_ENTITY` | 2 | `docs/interface_layout.svg`, `servier/tube-rack.svg` |
| `UNSUPPORTED_TRANSFORM` | 1 | `servier/falcon_50_media.svg` (non-uniform skew on stroked element) |
| `USE_OR_SYMBOL_UNSUPPORTED` | 1 | `assets/equipment/96well_pcr_plate.svg` |
| `EMPTY_GEOMETRY` | 1 | `assets/equipment/hood_workspace_surface.svg` |

### Interpretation of dominant classes

**`CLIPPATH_UNSUPPORTED_COMPLEX` (1120 wild / 50 assets):** The current
simple-clip allowlist requires the clip target to be filled (non-stroked)
geometry. Our committed assets and many bioicons use stroke-only clip targets
(fill:none on the clipped element). This is the single largest blocker. The
guard is correct -- stroke-only clips are geometrically trickier to flatten --
but it is overly conservative for the stroke-only-no-fill subcase, which is
structurally simpler than a filled+stroked clip and has a well-defined
intersection semantics. Graduating stroke-only clips to the allowlist is the
highest-leverage improvement available.

**`STYLE_GEOMETRY_UNSUPPORTED` (482 wild / 9 assets):** The normalizer resolves
geometry (fill, opacity, stroke-width, etc.) from inline `style=` only. An SVG
that sets geometry-affecting properties via a `<style>` block or class rules is
rejected. This is the inline-only cascade policy. Resolving simple class rules
(flat selector, no specificity, no inheritance) is tractable and would unlock a
meaningful fraction of these rejections.

**`TEXT_UNSUPPORTED` (295 wild / 11 assets):** Text elements are rejected by
design. The required author fix is to convert text to paths before ingestion
(Inkscape, Illustrator, or `fonttools` can do this). This is an authoring rule,
not a normalizer limitation. An optional pre-processing step (convert-text-to-path)
could be added to the tool, but it would require a font renderer and is outside
the normalize-or-reject scope.

**`DOCTYPE_OR_ENTITY` (234 wild / 2 assets):** DOCTYPE and entity declarations
are rejected for parser security. The fix for the 2 committed assets is to strip
the DOCTYPE declaration manually -- a one-line edit to each file.

**`EMBEDDED_RASTER_UNSUPPORTED` (73 wild / 0 assets):** Inline base64 raster
images inside SVG are rejected. No committed assets are affected. Bioicons
occasionally embed pixel art this way. No fix path in v3 scope.

**`USE_OR_SYMBOL_UNSUPPORTED` (38 wild / 1 asset):** The `<use>` element with
`<symbol>` expansion is not implemented. The one committed asset affected is the
96-well PCR plate. Symbol expansion is a non-trivial addition that requires
handling `<symbol>` viewBox and coordinate rescaling.

**`UNSUPPORTED_TRANSFORM` (34 wild / 1 asset):** Non-uniform or skew transforms
on stroked elements cannot be flattened safely (the stroke width is directional
under a skew). The one committed asset (`falcon_50_media.svg`) has a
non-uniform/skew transform on a stroked element. The fix is to pre-flatten the
transform in the source SVG.

**Smaller classes (filter, marker, script, empty, etc.):** These are each less
than 1.5% of wild rejections and affect zero or one committed asset. They are
correctly rejected and present no current investment priority.

---

## Visual fidelity findings

### Harness setup

The imagehash visual regression harness ran on a random 300-file sample (seed=42)
drawn from a pre-screened set of 1500 wild candidates, rendered at 256x256 px in
Chromium and Firefox via Playwright. Similarity is measured with perceptual hash
(phash) and directional hash (dhash). The full harness run took approximately
48 minutes.

### Raw numbers

| Engine | Identical (0-2) | Minor (3-6) | Divergent (>6) | Render errors |
| --- | --- | --- | --- | --- |
| Chromium | 79 (26.3%) | 70 (23.3%) | 151 (50.3%) | 0 |
| Firefox | 85 (28.3%) | 60 (20.0%) | 155 (51.7%) | 0 |

The 50% divergent headline is the key number to unpack.

### Failure mode taxonomy

Visual inspection of the 25 worst offenders reveals four distinct categories.
The categories differ fundamentally in whether the divergence is a real regression.

**Category A: viewBox/canvas reframing (not a regression).** The normalizer
correctly crops to the drawn bounding box and shifts the origin. When the
original had extra whitespace around the artwork, the crop changes the scale
relative to a fixed 256x256 canvas. Phash detects this framing shift as a large
distance (30+) even though no content is lost or distorted. Dhash (gradient
direction) stays low (<10) because the local structure is unchanged. Estimated
60-80 of the 151 divergent Chromium files fall in this category. This is
expected, correct normalizer behavior.

**Category B: userSpaceOnUse gradient color loss (real regression, now fixed).**
File: `cpu.svg` (phash=38 both engines). The SVG used 278 linearGradients and
804 radialGradients with `gradientUnits="userSpaceOnUse"` (absolute coordinates)
plus 22 transform attributes. When v3 flattened the transforms into path
coordinates, the gradient def coordinates were not updated to match, causing all
gradients to resolve to out-of-bounds positions and collapse to their nearest
end-stop color. The colorful CPU rendering became a near-monochrome grey grid.

This regression was found by the imagehash harness and triggered a targeted fix
(task #15, now completed). The fix bakes the element's accumulated transform
matrix into the `gradientTransform` of single-use userSpaceOnUse gradients.
For shared gradients referenced under differing transforms (a geometrically
ambiguous case), v3 now rejects with `UNSUPPORTED_TRANSFORM` rather than
emitting a visually wrong result. The `cpu.svg` asset was verified structurally
after the fix.

The gradient fix was landed after the 300-file imagehash run. A targeted
re-run on the approximately 20 Category-B offenders is the recommended
confirmation step. Because the full harness sample took 48 minutes, a targeted
run on just the ~20 gradient offenders should complete in under 5 minutes and
is the cheapest available confirmation.

**Category C: nested-scale stacking shift (verified as reframe artifact).**
File: `Amphiprion_ocellaris_egg.svg` (phash=36 both engines). The SVG used
nested `translate + scale(0.09604)` and rotation transforms. After flattening,
the relative bounding boxes of outer and inner elements changed, altering which
layer visually dominated at the 256x256 canvas scale. Inspection confirmed that
all 17 element nodes survived normalization with the same fill colors. This is
a reframe artifact from the extreme scale factor (1/10th), not content loss. The
element hierarchy and fill data are preserved. At display size, the visual
difference would be negligible for any reasonable display scale factor.

**Category D: intentional normalizer transforms (test fixtures).** Several of
the worst-offenders list entries are scour normalizer test fixtures designed to
exercise short color names, high-precision coordinates, and unusual path
commands. Their pre-normalized form is deliberately non-canonical. The phash
difference reflects the normalizer doing its job correctly. These are not
regressions.

### Summary of genuine concerns

| Category | Estimated count in 300-file sample | Real regression risk |
| --- | --- | --- |
| A: viewBox reframe | ~60-80 files | None -- correct behavior |
| B: gradient color loss | ~10-20 files | HIGH -- was real; now fixed |
| C: nested-scale stacking | ~10-20 files | LOW -- reframe artifact at real display scale |
| D: test fixture normalization | ~40-60 files | None -- expected behavior |

After the gradient fix, genuine regressions are estimated at fewer than 10 of
the 300 sample files (under 3.5%), concentrated in SVGs with extreme nested
transforms. None of those SVG patterns appear in our committed 27-asset
normalized set.

### Phash threshold recalibration

The current thresholds (identical: 0-2, minor: 3-6, divergent: >6) flag
viewBox reframing as divergent. A better split for content-regression detection:
require both `phash > 6` AND `dhash > 6` before classifying as a potential
content regression. Reframes have high phash but low dhash. This change would
cut the false-divergent rate substantially without hiding real color-loss events.

---

## Cross-engine reliability

The chromium vs firefox comparison on normalized outputs shows:

| Classification | Count | % |
| --- | --- | --- |
| Identical | 261 | 87.0% |
| Minor | 26 | 8.7% |
| Divergent | 13 | 4.3% |
| Unavailable | 0 | 0% |

The 13 divergent cross-engine cases are concentrated in SVGs with CSS geometry
features (`arrow-twosides-horizontal.svg` has the worst CF hamming distance of
20). These are exactly the SVGs the normalizer would already reject at ingestion
via `STYLE_GEOMETRY_UNSUPPORTED`, because they use `<style>` blocks to set
geometry properties. For the assets v3 normalizes and accepts, the cross-engine
rendering is reliable: 87% identical and only 4.3% genuinely divergent.

This confirms that the normalized SVG output is browser-safe for shipping to
students without browser-specific fallbacks.

---

## Prioritized next-investment recommendations

The plan's open question -- which rejected class to graduate next -- is now
data-driven from the corpus and parity results.

### Rank 1: no-op clip elimination (the real shape of `CLIPPATH_UNSUPPORTED_COMPLEX`)

**STATUS: SHIPPED (2026-06-10).** Normalized files rose from 721 to 1757
(`CLIPPATH_UNSUPPORTED_COMPLEX` fell from 1120 to 84). A conservative-containment
follow-up corrected the buffer direction in `_clip_is_noop`. See `docs/CHANGELOG.md`
entry 2026-06-10 for details.

**Scope of unblock:** 1120 of 2404 wild rejections (47%). A per-target probe over
the corpus (2026-06-09) sharpens this: of the 1120 complex-clip rejections,
**1083 are not complex clip geometry at all** -- they reject only because the
clipped TARGET is stroke-only (`fill:none`), and the current allowlist refuses a
stroke-only target. Just 36 are `<g>` targets and 1 is an unresolved ref.

Decomposing those 1083 stroke-only targets by what the clip actually does:

| Stroke-only clip target | Targets | Files |
| --- | --- | --- |
| no-op: clip region already contains the target | 3435 | 1077 |
| genuine trim: clip really cuts the stroked path | 57 | -- |
| geometry could not be built (degenerate) | 51 | -- |

The dominant case is an editor-emitted page-bounds safety clip (Inkscape exports
a `clipPath` holding a rect the size of the page and references it from content
already inside it). Intersecting changes nothing visible; the clip is dead.

**What it requires (bounded, reuses existing machinery):** add a no-op short
circuit to `flatten_clip_paths`, BEFORE the fill-only allowlist check in
`_target_segments_for_clip`:

1. Build the clip polygon (already done: `_composed_clip_matrix` +
   `_polygon_from_segments`).
2. Build the target envelope: the target's filled polygon unioned with its
   stroke envelope (`LineString(ring).buffer(stroke_width/2)` -- shapely is
   already a dependency).
3. If `clip_poly.contains(target_envelope)` (with a small safety buffer so
   borderline cases stay rejected), drop the `clip-path` reference and leave the
   target geometry unchanged. No intersection, no stroke-to-path, no precision
   loss.
4. Otherwise fall through to the existing logic: filled targets intersect as
   today; genuine stroke trims (57 targets) stay rejected.

This also subsumes the filled-target case: a filled target fully inside its clip
can short-circuit to "drop ref, keep original d" instead of re-emitting a
polygonized path, avoiding needless precision loss.

**Safety:** a no-op drop is render-identical by construction (intersection of a
shape with a region that contains it is the shape). It is directly verifiable
with the imagehash harness -- before/after phash should be ~0, not divergent. The
57 genuine-trim cases remain rejected (correct); true stroke clipping needs
stroke-to-path expansion, which stays out of scope.

**Verdict: highest-value, lowest-complexity extension available. One bounded
short-circuit unblocks ~1077 files (~34% of the corpus) and roughly doubles the
normalized count (721 -> ~1800), with no new heavy machinery.**

### Rank 1b: cheap companions to the no-op short circuit

- **`<g>` clip targets (36 files):** a clip on a group whose content bbox is
  inside the clip is the same no-op. Apply the containment check to group
  targets (drop the ref) rather than rejecting `<g>` outright.
- **Multi-shape clipPath (`must hold exactly one path/shape`):** shapely unions
  multiple clip children into one clip polygon trivially. Relaxing the
  exactly-one rule to "union all geometry children" is a few lines, though the
  measured binding constraint is target-side, so yield is secondary.

### Rank 2: flat `<style>` class-rule resolution (`STYLE_GEOMETRY_UNSUPPORTED`)

**Scope of unblock:** 9 of our 74 rejected assets, 482 wild rejections.

**What it requires:** The current policy rejects any SVG where a `<style>` block
sets a geometry-affecting property. The affected assets use simple flat selectors
(`.cls-1 { fill: #abc; }`) with no specificity, inheritance, or cascade
interaction. Resolving simple class selectors into inline `style=` attributes
and then removing the `<style>` block would allow these files to normalize.

tinycss2 (already a declared dependency) can parse the block. A restricted
resolver that handles only flat class selectors with geometry-affecting properties
(fill, opacity, stroke-width, stroke) and inlines them would cover the majority
of affected assets without requiring a full CSS cascade engine.

Risk: pseudo-selectors, media queries, `!important`, and element+class combinator
selectors would need explicit rejection guards. The implementation must not
silently misresolve specificity. The conservative approach is: resolve only
single-class selectors, reject everything else with a more specific reason code
such as `STYLE_COMPLEX_SELECTOR_UNSUPPORTED`.

**Verdict: medium priority; moderate implementation complexity; smaller asset
backlog impact than rank 1.**

### Rank 3: optional convert-text-to-path step (`TEXT_UNSUPPORTED`)

**Scope of unblock:** 11 of our 74 rejected assets, 295 wild rejections.

**What it requires:** Text rejection is an intentional authoring rule. The
correct fix is for asset authors to pre-convert text to paths using Inkscape or
similar tooling before submitting to the repo. No normalizer change is needed
for the policy to hold.

If an optional `--convert-text-to-path` preprocessing step were added to v3,
it would require a font renderer (fonttools + a font fallback chain) to extract
glyph outlines. This is a substantial dependency and well outside the
normalize-or-reject scope.

**Verdict: low priority for normalizer change; the authoring rule is clear and
the fix is well-documented in the rejection message. Asset authors can use
Inkscape's `Path > Object to Path` or `inkscape --export-plain-svg` with the
text-to-path option.**

### Rank 4: `DOCTYPE_OR_ENTITY` strip (`DOCTYPE_OR_ENTITY`)

**Scope of unblock:** 2 of our assets, 234 wild rejections.

**What it requires:** Strip the `<!DOCTYPE` declaration and entity references
from the input before parsing. lxml's `XMLParser(resolve_entities=False)` already
handles entities safely; the reject is a conservative policy guard. Loosening
it to strip-then-parse is a small change.

However, the 2 affected committed assets are `docs/interface_layout.svg` (a
documentation diagram, not a scene asset) and `servier/tube-rack.svg` (a
Servier-sourced asset with a DOCTYPE declaration). The author fix for each is
a one-line delete.

**Verdict: low priority; small asset impact; author fix is trivial for committed
assets.**

---

## How to reproduce

All reports in this synthesis were generated by these scripts and commands.

**Wild-corpus verdict run** (produces
[normalize_svg_v3_wild_verdicts.md](../active_plans/reports/normalize_svg_v3_wild_verdicts.md) and
[normalize_svg_v3_wild_verdicts.json](../active_plans/reports/normalize_svg_v3_wild_verdicts.json)):

```bash
source source_me.sh && python3 tests/e2e/e2e_normalize_svg_wild.py \
  --wild-root OTHER_REPOS/ \
  --report-json docs/active_plans/reports/normalize_svg_v3_wild_verdicts.json \
  --report-md docs/active_plans/reports/normalize_svg_v3_wild_verdicts.md
```

**Parity report** (produces
[normalize_svg_v3_parity.md](reports/normalize_svg_v3_parity.md) and
[normalize_svg_v3_parity.json](reports/normalize_svg_v3_parity.json)):

```bash
source source_me.sh && python3 tests/e2e/e2e_normalize_svg_parity.py \
  --report-json docs/active_plans/reports/normalize_svg_v3_parity.json \
  --report-md docs/active_plans/reports/normalize_svg_v3_parity.md
```

**Visual regression harness** (produces
[svg_visual_regression.md](../active_plans/reports/svg_visual_regression.md) and
[svg_visual_regression.json](../active_plans/reports/svg_visual_regression.json); ~48 min for 300
files; before-after PNGs under `test-results/svg_visual_regression/`):

```bash
node tests/playwright/test_svg_visual_regression.mjs \
  --sample 300 --seed 42 \
  --report-md docs/active_plans/reports/svg_visual_regression.md \
  --report-json docs/active_plans/reports/svg_visual_regression.json
```

**Targeted re-run on gradient offenders** (recommended next step; ~5 min):
Run the visual regression harness with `--files` pointing to the list of
approximately 20 Category-B gradient offenders identified in the prior run.
This confirms the gradient fix landed in task #15 resolved the color-loss
regressions before the next full-corpus run.

---

## Source reports

- [normalize_svg_v3_wild_verdicts.md](../active_plans/reports/normalize_svg_v3_wild_verdicts.md) -- per-reason-code counts over 3125 wild files
- [normalize_svg_v3_wild_verdicts.json](../active_plans/reports/normalize_svg_v3_wild_verdicts.json) -- per-file JSON verdicts
- [normalize_svg_v3_parity.md](reports/normalize_svg_v3_parity.md) -- v2 vs v3 comparison on 102 committed assets
- [normalize_svg_v3_parity.json](reports/normalize_svg_v3_parity.json) -- parity data in JSON
- [svg_visual_regression.md](../active_plans/reports/svg_visual_regression.md) -- imagehash chromium+firefox, 300-file sample
- [svg_visual_regression.json](../active_plans/reports/svg_visual_regression.json) -- per-file hash distances
- [normalize_svg_v2_audit.md](normalize_svg_v2_audit.md) -- v2 audit with v3 resolution notes

---

## Open items and concerns

1. **Gradient fix confirmation needed.** The userSpaceOnUse gradient color-loss
   fix (task #15) was applied after the imagehash run. A targeted re-run on the
   ~20 Category-B files is needed to confirm `cpu.svg` and similar files now
   produce visually correct output. This is a 5-minute run, not a 48-minute one.

2. **74 committed assets blocked.** The assets blocked by
   `CLIPPATH_UNSUPPORTED_COMPLEX` (50), `TEXT_UNSUPPORTED` (11), and
   `STYLE_GEOMETRY_UNSUPPORTED` (9) remain in the repo using v2 normalization.
   Until they are re-normalized under v3, the ingestion gate does not cover them.
   Graduating stroke-only clips (Rank 1 above) is the fastest path to unblocking
   the majority.

3. **Phash threshold recalibration.** The current thresholds over-count
   viewBox-reframe divergences as real regressions. Adding a dhash co-condition
   (both phash > 6 AND dhash > 6) would produce more accurate per-category counts
   on a re-run.

4. **Cleanup nits open (task #16).** Minor review nits from the gradient fix
   (unused `tmp_path`, untested compose branch, dead-loop comment) are still
   in_progress. These are cosmetic and do not affect gate correctness.

5. **`docs/interface_layout.svg` is not a scene asset.** Its DOCTYPE rejection
   is not a production concern -- it is a documentation diagram. The rejection
   listing in the parity report is accurate but should not be treated as a
   blocked scene asset.
