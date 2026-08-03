# Detector coverage audit

Read-only audit of every layout/label/object overlap and placement detector in
the repo. Motivated by the `recycle_buffer_bottle` defect (a label clamped onto
its own cap) that shipped GREEN. This audit confirms that the detector layer has
systemic blind spots, not one bug, and inventories them.

No detectors, gates, engine, or tests were edited. Analysis ran read-only over
`generated/scene_render_stats/*.stats.json` and source. See the root cause in
[buffer_recycle_label_overlap_root_cause.md](buffer_recycle_label_overlap_root_cause.md).

## Headline findings

- Every overlap detector that associates a label to an object EXCLUDES the
  label's own object, except `structural_guards.ts` Guard 8. Guard 8 is the only
  detector that geometrically sees own-art overlap, and it runs REPORT-ONLY at
  live render (degrade, never throw). Its throwing path runs only in unit tests
  (synthetic items) and the generalization preflight (which never gates and
  never sees protocol scenes).
- Three independent own-art exclusions: Playwright assertion H (ancestor-walk
  returns null, vacuous), `scene_stats.mjs` `label_art_overlap_count`
  (`labelFor === placementName` continue), and scene_lint B8
  (`other_pname == label_pname` continue). All three are structurally blind to
  the exact recycle defect.
- No overlap/label/placement detector runs in `check_codebase.sh` (the CI gate)
  or as a throwing step in `build_github_pages.sh`. `scene_to_png.mjs --all`
  runs in the build but only writes stats and always exits 0.
- The WP-6 alignment "gate" measured horizontal x-center alignment only
  (`abs(diff) <= 1px`); the contract-required vertical-above gate
  (`label_bbox.bottom <= visual_bbox.top`) was specified but never run, and
  exists in no committed script.
- The `artwork_integrity` / never-crop check the primary design demands
  (`PRIMARY_DESIGN.md` visual-integrity section) exists in no committed gate
  script; it lives only as throwaway review computations.

## Estimated current exposure

Re-deriving own-art label overlap directly from the rendered geometry in every
`generated/scene_render_stats/*.stats.json` (label_bbox vs its own visual_bbox,
1 px tolerance, both rects are `getBoundingClientRect`):

- 38 scenes have a geometry block; 0 load-failed.
- 35 of 38 scenes carry at least one own-art label overlap that NO detector
  currently throws on. 106 placements total.
- All 35 are "deep" (vertical overlap >= 8 px AND overlapped area >= 15% of the
  label box); none are sub-pixel grazes. Many are frac = 1.00 (the whole label
  rect sits inside the object's SVG element rect).

Caveat on basis: `visual_bbox` is the `<svg>` ELEMENT rect
(`getBoundingClientRect`), which includes `object-fit: contain` letterbox
padding, not the drawn ink (`getBBox`). So frac = 1.00 means the label sits
inside the SVG's reserved box; the visible ink may be letterboxed away from it.
The rect basis cannot distinguish ink-overlap from letterbox padding -- that
inability is itself the core bbox-basis gap (Gap 4). The recycle bottle
(`rear_left_recycle_buffer_bottle`, 21 px / frac 0.28) is a confirmed real
on-screen defect per the root-cause PNG, so at minimum the recycle case and its
clones across the 8 electrophoresis/sdspage scenes are real; the full 35 is the
upper bound of undetected exposure on the rendered-rect basis.

## Detector inventory

| detector | what it detects | runs at | throwing or report-only | bbox basis | vacuous pass? | blind spot |
| --- | --- | --- | --- | --- | --- | --- |
| structural_guards Guard 1 (zone_lookup / item-in-zone) | item bbox inside its zone bbox; missing zone id | live render (report), preflight (throw), unit (throw) | live report-only; preflight runs throwing wrapper but preflight itself exits 0; zone-containment drift is console.warn only, never a violation | computed layout (`_centerX/_top/_visualWidth` percent) | drift is warn-only, so containment failures never fail anything | tall objects routinely exceed zone; demoted to warn |
| structural_guards Guard 2 (zone_off_scene) | zone bounds inside scene_bounds | same as G1 | report-only live; preflight non-gating | scene/zone declared bounds | no | none notable |
| structural_guards Guard 3 (item_overlap) | item-item bbox overlap > 1% | same as G1 | report-only live; preflight non-gating | computed layout percent | no | uses placement box, not ink; cannot see same-object subpart overlap |
| structural_guards Guard 4 (zone_gap) | horizontal gap < zone_gap when adjacent | same as G1 | report-only live; preflight non-gating | computed layout percent | only fires when `horizontalGap < 1`; narrow trigger window | vertical gaps never checked |
| structural_guards Guard 5 (aspect_distortion) | rendered aspect vs asset aspect > 5% | same as G1 | report-only live; preflight non-gating | computed `_visualWidth/_height` x viewport | preflight calls `runStructuralGuards` WITHOUT viewport, so DEFAULT_VIEWPORT assumed | wrong viewport gives false aspect verdicts off-1920x1080 |
| structural_guards Guard 6 (missing_asset) | asset key present in SVG_MANIFEST | same as G1 | report-only live; preflight non-gating | n/a (key lookup) | skips `missing_svg === true` items | none notable |
| structural_guards Guard 7 (label_off_scene) | label bbox inside scene_bounds | same as G1 | report-only live; preflight non-gating | label width MODEL (`longestLine.length * AVG_CHAR_WIDTH_PCT`, line count * line height) | no | width model is an estimate, not measured glyph extent |
| structural_guards Guard 8 (label_svg_overlap) | label bbox overlaps its OWN item bbox > 1% | live render (report), preflight (throw), unit (throw) | REPORT-ONLY at live render; throwing only in unit + preflight (non-gating, base scenes only) | label width MODEL vs item placement box (percent) | no | the ONE detector that sees own-art -- but never throws in any path that gates, and preflight never sees protocol scenes |
| Playwright A (no clipping) | overflow/clip styles + placement in scene-root | bench test (exit 1), generalization test (no exit) | bench: throwing; generalization: REPORT-ONLY (writes contact sheet, never exits nonzero) | element rect (`boundingBox`) | breaks on first placement; if zero placements, passes | generalization variant never fails the run |
| Playwright B (no fallback SVG) | every placement has non-empty `<svg>` | same as A | bench throwing; generalization report-only | element rect | passes if zero placements | -- |
| Playwright C (aspect preserved) | svg rect aspect vs viewBox > 5% | same as A | bench throwing; generalization report-only | `<svg>` element rect vs viewBox | passes if zero placements | element rect includes letterbox, not ink |
| Playwright D (no item off-page) | placement bbox in scene-root | same as A | bench throwing; generalization report-only | element rect | passes if zero placements | -- |
| Playwright E (zone overflow) | NOTHING -- hardcoded PASS | both tests | n/a | n/a | ALWAYS vacuous: `results.E = true` / always logs PASS | does not check anything at all |
| Playwright F (no item overlap) | placement-placement bbox overlap | same as A | bench throwing; generalization report-only | element rect | passes if < 2 placements | placement box, not ink |
| Playwright G (label in scene) | label bbox in scene-root | same as A | bench throwing; generalization report-only | element rect | passes if zero labels | -- |
| Playwright H (no label-own-SVG overlap) | label bbox vs its OWN svg rect | same as A | bench throwing; generalization report-only | element rect | ALWAYS vacuous: owner resolved by ANCESTOR walk for `data-placement-name`, but label is a SIBLING carrying `data-label-for`; walk returns null, body skipped for every label | the named gate for the recycle defect; sees nothing |
| Playwright I (no label-label overlap) | label-label bbox overlap | same as A | bench throwing; generalization report-only | element rect | passes if < 2 labels | -- |
| Playwright J (label readability) | text non-empty, visible, font >= 6px | same as A | bench throwing; generalization report-only | computed style | passes if zero labels | -- |
| Playwright K (no scene branches) | bundle string match `=== "bench_basic"` | same as A | bench throwing; generalization report-only | n/a (string scan) | only matches the literal `bench_basic`; any other scene name slips | scene-name-specific literal only |
| test_scene_dom_contract_selectors | data-* attribute contract, click receipt | own test (exit 1) | throwing | element rect (size only, not compared) | `assertGt(items.length,0)` guards emptiness | checks attributes, NOT geometry/overlap |
| scene_stats `overlap_pair_count` | placement-placement bbox overlap | scene_to_png (build + manual) | NEVER gates (tool exits 0; not in pass_fail) | element rect | n/a | emitted, never gated |
| scene_stats `label_overlap_pair_count` | label-label bbox overlap | scene_to_png | never gates | element rect | n/a | emitted, never gated |
| scene_stats `label_art_overlap_count` | label vs OTHER placements' art | scene_to_png | never gates | element rect | n/a | EXCLUDES own art (`labelFor === placementName` continue); cannot see recycle defect |
| scene_stats `clipped/offscreen/tiny` | item vs scene-root edge | scene_to_png | never gates | element rect | n/a | emitted, never gated |
| scene_stats `pass_fail` | renders / no-dropped / no-missing-assets | scene_to_png | never gates (tool ignores it for exit code) | n/a | n/a | contains NO overlap or alignment check |
| e2e_generalization_preflight | runs throwing Guard 1-8 over base SCENES | manual e2e | runs throwing guards BUT catches into verdict; main() ALWAYS exit 0 | computed layout percent | scene-not-found -> FAIL recorded but still exit 0 | non-gating; iterates `generated/scenes.ts` (base scenes), never protocol scenes like recycle |
| e2e_layout_diagnostics_baseline | pipeline diagnostics + severity overlap stream | manual e2e | REPORT-ONLY (writes markdown, never exits nonzero) | engine diagnostics (`severityDiagnostics`) | n/a | snapshot only; `unresolved_label_overlap` is label-vs-other, engine de-overlap stream |
| e2e_layout_parity_16x9 | precompute vs live ComputedItem parity | manual e2e | THROWING (exit 1 on non-parity) | computed ComputedItem fields | no | checks viewport parity only -- NO overlap/label/placement-quality check |
| WP-6 alignment metric | object x-center vs label x-center, <= 1px | one-off review (no committed script) | n/a (not a gate) | element rect x-centers | n/a | HORIZONTAL only; vertical-above never computed; "art" column reuses own-art-excluding stat |
| scene_lint B8 (label_object_overlap) | label bbox vs OTHER placements' visual_bbox > 10 px^2 | scene_design CLI (e2e test only) | not a build gate | dump geometry (scene-%) | skips empty label_bbox | EXCLUDES own placement (`other_pname == label_pname` continue); same blind spot |

## Prioritized gap list

Ranked by how many real defects each could be hiding right now.

### Gap 1 (HIGHEST): own-art overlap is structurally excluded by every gating-capable detector

Three detectors that could gate (Playwright H, scene_stats `label_art_overlap_count`,
scene_lint B8) all explicitly skip the label's own object. The only detector that
sees own-art (Guard 8) is report-only at live render and non-gating in preflight.
Result: 35 of 38 scenes carry an undetected own-art label overlap; the recycle
defect is one confirmed-real instance with 8 sibling clones across the
electrophoresis/sdspage cluster.

Smallest fix: make Guard 8 throw (or be treated as hard-fail) in a path that
actually gates the build, e.g. have `scene_to_png.mjs --all` exit non-zero when
any scene reports a Guard-8 own-art overlap above tolerance for a normalized
(non-placeholder) object; and remove the own-placement `continue` so at least one
gating detector counts own-art. Re-point Playwright H to resolve the owner via
`data-label-for` (it already exists on the label node) instead of the dead
ancestor walk.

### Gap 2: assertion H passes vacuously (and the whole generalization test is report-only)

`test_generalization_render.mjs` never exits non-zero on any assertion failure --
it only writes a contact sheet. Even its bench sibling, which does exit 1, has
the same vacuous H. So the user-named gate for the recycle defect can never fire.

Smallest fix: fix H's owner resolution (Gap 1), and make
`test_generalization_render.mjs` `process.exit(1)` when any scene scores below
11/11 (or below an explicit allowlist), matching the bench test's exit contract.

### Gap 3: assertion E checks nothing (hardcoded PASS in both tests)

`results.E = true` / "passed D3 preflight" -- E never evaluates zone containment.
A zone-overflow regression is invisible to E in both Playwright tests.

Smallest fix: compute the actual zone-bounds rect (from scene geometry, not the
self-fulfilling union of contained items) and assert each placement's box is
inside it; or delete E and rely on a real Guard 1 that throws.

### Gap 4: wrong bbox basis (element rect / width model, never drawn ink)

Every geometric detector uses either `getBoundingClientRect` (the `<svg>` element
rect, which includes `object-fit: contain` letterbox padding) or the
structural-guard label WIDTH MODEL. None uses `getBBox()` of the drawn path. This
is why the rendered-rect analysis cannot separate real ink overlap from letterbox
padding, and why a real overlap (recycle) and a benign letterbox graze look
identical in the stats.

Smallest fix: capture `svgEl.getBBox()` (ink extent in the SVG's own coordinate
space, mapped to screen via `getScreenCTM`) alongside the element rect in
`collect_rendered_items`, and feed the ink bbox to the overlap/aspect/alignment
checks; keep the element rect only for off-page/clip checks.

### Gap 5: required vertical-above label gate specified but never run

The plan's `label_bbox.y + label_bbox.h <= visual_bbox.y` gate exists in no
committed script. WP-6 shipped a horizontal-only x-center alignment metric and
explicitly accepted the recycle `art 0->1` regression as "net neutral."

Smallest fix: add a committed gate that, for every top-placed label, asserts
`label_bbox.bottom <= visual_bbox.top + tol` against the ink bbox (Gap 4), and
wire it into `check_codebase.sh` or the build.

### Gap 6: no overlap/label detector is wired into any gate

`check_codebase.sh` runs none of these. `build_github_pages.sh` runs
`scene_to_png.mjs --all`, but that tool always exits 0. The generalization
preflight and layout diagnostics are report-only. Stats are emitted and ignored.

Smallest fix: add a gate step (in `check_codebase.sh` or as a throwing wrapper
around `scene_to_png.mjs --all`) that reads each `*.stats.json` and fails the run
when own-art overlap (Gap 1) or label-label/other-art overlap exceeds an explicit
per-scene allowlist.

### Gap 7: scene_lint B8 shares the own-art exclusion and is not gated

B8 is the most principled label-object rule (configurable px^2 tolerance,
confidence from scale_source), but it skips own placement (Gap 1) and runs only
under an e2e CLI test, not a build gate.

Smallest fix: add an own-art pass to B8 (compare each label to its own
visual_bbox) and run scene_lint as a gate.

### Gap 8: Guard 5 aspect uses the wrong viewport in preflight

`e2e_generalization_preflight.mjs` calls `runStructuralGuards(final, scene)`
without the viewport arg, so Guard 5 assumes DEFAULT_VIEWPORT. At 1920x1080 this
is correct, but any future non-default preflight viewport would yield false
aspect verdicts. Low real-defect count today.

Smallest fix: pass the pipeline viewport explicitly to `runStructuralGuards` in
the preflight.

## Method note

Counts were derived by a read-only Python pass over
`generated/scene_render_stats/*.stats.json`, reconstructing label_bbox vs
own/other visual_bbox and label_bbox intersections at a 1 px tolerance, and
classifying overlap depth (vertical penetration and label-area fraction). Scratch
scripts were deleted after use; the geometry source files were not modified.
