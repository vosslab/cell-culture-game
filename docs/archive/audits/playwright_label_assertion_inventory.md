# Playwright label assertion inventory

Static inventory of label-related assertions in `tests/playwright/` for WP-6
pre-flight. WP-6 flips the default label position from below to above objects.
Tests that check label geometry relative to the scene boundary or SVG bounding
box may produce different results after the flip and are classified below.

Scope: all `.mjs` and `.ts` files under `tests/playwright/`. No Playwright
runs were executed; this is a source-only analysis.

---

## Impact classification key

- `BREAKS-LEGITIMATELY` -- the assertion encodes an assumption about label
  position that will change when labels move above objects. The assertion
  logic itself is correct; it will fail on geometrically valid output and
  must be reviewed and updated alongside the WP-6 change.
- `UNAFFECTED` -- the assertion does not depend on vertical label position.
  It checks presence, text, selector, count, or a geometry property that
  is position-independent. It should continue to pass unchanged.
- `NEEDS-JUDGMENT` -- the assertion depends on geometry but the impact
  cannot be determined from source alone; a rendered run is required.

---

## WP-6 gate tests (named in task brief)

The three files designated as WP-6 gate tests are covered in detail below.
Summary line for each:

| File | Impact on gate |
| --- | --- |
| `test_bench_basic_render.mjs` | Contains BREAKS-LEGITIMATELY and NEEDS-JUDGMENT assertions |
| `test_generalization_render.mjs` | Same 11-assertion pattern as bench_basic; same risk profile |
| `test_scene_dom_contract_selectors.mjs` | UNAFFECTED -- checks selector presence and text only |

---

## File: test_bench_basic_render.mjs

### Description

Loads the bench_basic scene via a local server and runs 11 named assertions
(A through K). Label assertions are G, H, I, and J.

### Label-related assertions

**Assertion G -- no label outside scene** (lines 460-481)

- What it checks: every `[data-label]` bounding box is fully contained within
  the `#scene-root` bounding box (`bboxContains(sceneRootBbox, label.bbox)`).
- Line numbers: assertion logic at lines 462-477; `bboxContains` call at line 469.
- Impact: `NEEDS-JUDGMENT`. Labels currently render below the object SVG. If a
  label at the bottom of the scene moves above an object that sits near the top
  of the scene, the label could still be within `#scene-root`. However, if the
  object is near the top of the visible scene area, moving the label above it
  could push it outside the scene boundary. Cannot be determined without a
  rendered run.

**Assertion H -- no label-own-SVG overlap** (lines 487-519)

- What it checks: for each label, walks the DOM up to find its parent
  placement, then calls `bboxsOverlap(label.bbox, associatedPlacement.svgBbox)`.
  A below-positioned label does not overlap its SVG; an above-positioned label
  also must not overlap the SVG -- but the tolerance is zero pixels (aside from
  `OVERLAP_TOLERANCE = 1` defined at line 18).
- Line numbers: overlap call at line 510; label-to-placement walk at lines
  496-505.
- Impact: `BREAKS-LEGITIMATELY`. The assertion was written under the assumption
  that labels sit below the SVG, where overlap is unlikely. Moving labels above
  the SVG may produce cases where the label edge touches the top of the SVG
  bounding box within 1px. Whether the assertion trips depends on the gap
  between label and SVG top edge after the flip. The assertion logic is correct
  (labels must not cover the scientific artwork); it will need verification
  and possibly a revised tolerance or gap rule.

**Assertion I -- no label-label overlap** (lines 525-547)

- What it checks: every pair of `[data-label]` elements must not overlap
  (`bboxsOverlap(l1.bbox, l2.bbox, OVERLAP_TOLERANCE)`).
- Line numbers: overlap call at line 534.
- Impact: `BREAKS-LEGITIMATELY`. When labels are below objects, horizontal
  spacing between adjacent objects keeps labels apart. When labels move above
  objects, two labels from neighboring objects at different horizontal positions
  may now overlap in the above-object strip. The correct behavior (no overlap)
  is the same; the geometry changes.

**Assertion J -- label readability** (lines 552-599)

- What it checks: four hard-failure subchecks -- (1) non-empty text
  (lines 558-561); (2) label within scene, redundant with G (lines 564-568);
  (3) visibility/display/opacity not hidden (lines 570-582); (4) font-size
  >= 6px (lines 584-595).
- Line numbers: text check line 559; visibility check lines 571-574;
  font-size check lines 585-594.
- Impact: `UNAFFECTED`. None of these subchecks depend on vertical position.
  Text content, visibility, and font-size are position-independent. The
  redundant within-scene check (subcheck 2) inherits the same NEEDS-JUDGMENT
  status as assertion G, but it is explicitly noted as redundant at line 564.

**Label count logging** (lines 162-163)

- What it checks: `page.locator("[data-label]").all()` count is logged.
- Line numbers: 162-163.
- Impact: `UNAFFECTED`. Count-only; no assertion on the value.

**boundingBox usage for labels** (lines 197-203)

- What it checks: `locator.boundingBox()` called on each label locator to
  populate `label.bbox` for assertions G, H, I, J.
- Line numbers: 199.
- Impact: `UNAFFECTED` as data collection. Impact flows to assertions above.

### Assertion summary for test_bench_basic_render.mjs

| Assertion | Category | Line(s) |
| --- | --- | --- |
| G -- label outside scene | NEEDS-JUDGMENT | 469 |
| H -- label-SVG overlap | BREAKS-LEGITIMATELY | 510 |
| I -- label-label overlap | BREAKS-LEGITIMATELY | 534 |
| J (text, visibility, font) | UNAFFECTED | 559, 571-574, 585-594 |

---

## File: test_generalization_render.mjs (WP-6 gate test)

### Description

Runs the same 11-assertion pattern as `test_bench_basic_render.mjs` against
five scenes: `bench_basic`, `sample_prep_bench`, `staining_bench`,
`cell_counter_basic`, and `hood_basic` (line 21-27). For each scene it
rebuilds `dist/` by rewriting `src/main.ts`. Label assertions are G, H, I,
and J, copied from the same logic.

### Label-related assertions

**Assertion G** (lines 396-406) -- `bboxContains(sceneRootBbox, label.bbox)`.
Same logic as bench_basic assertion G. Impact: `NEEDS-JUDGMENT`.

**Assertion H** (lines 408-431) -- `bboxsOverlap(labels[i].bbox, associatedPlacement.svgBbox)`.
Same logic as bench_basic assertion H. Impact: `BREAKS-LEGITIMATELY`.

**Assertion I** (lines 433-446) -- `bboxsOverlap(labels[i].bbox, labels[j].bbox, OVERLAP_TOLERANCE)`.
Same logic as bench_basic assertion I. Impact: `BREAKS-LEGITIMATELY`.

**Assertion J** (lines 448-475) -- text empty, visibility, font-size.
Same logic as bench_basic assertion J. Impact: `UNAFFECTED`.

**Label count logging** (line 252) -- logs `labelLocators.length`. `UNAFFECTED`.

**boundingBox for labels** (line 287) -- `locator.boundingBox()` for each
label, feeds assertions G/H/I/J. `UNAFFECTED` as data collection.

**data-label selector** (line 250) -- `page.locator("[data-label]").all()`.
`UNAFFECTED`.

### Additional note

The contact sheet HTML generated by `generateContactSheet` (lines 508-743)
uses unicode checkmark/cross characters in the card table rows (e.g.
`${asserts.G ? "&#x2713;" : "&#x2717;"}` at line 535-539 -- actual unicode
in source). This is reporting only; no assertion impact.

### Assertion summary for test_generalization_render.mjs

| Assertion | Category | Line(s) |
| --- | --- | --- |
| G -- label outside scene | NEEDS-JUDGMENT | 400 |
| H -- label-SVG overlap | BREAKS-LEGITIMATELY | 424 |
| I -- label-label overlap | BREAKS-LEGITIMATELY | 438 |
| J (text, visibility, font) | UNAFFECTED | 452, 456-459, 464-469 |

Applied across all five scenes.

---

## File: test_scene_dom_contract_selectors.mjs (WP-6 gate test)

### Description

Tests the DOM contract for `data-*` attributes across three scenes
(`bench_basic`, `hood_workspace`, `missing_svg_check`). Does not use
`boundingBox()`. Label assertions are structural and text-content only.

### Label-related assertions

**data-label presence** (lines 191-198) -- `querySelectorAll("[data-label]")`
collects all label elements. No position assertion.
Line 192: `const els = Array.from(document.querySelectorAll("[data-label]"))`.
Impact: `UNAFFECTED`.

**At least one label present** (line 266):
`assertGt(labels.length, 0, ...)`.
Impact: `UNAFFECTED`. Count only.

**data-label-for references a known placement** (lines 270-273):
Checks that `label.labelFor` (the `data-label-for` attribute value) exists in
the `placementNameSet` derived from all `[data-placement-name]` elements.
Line 271: `assert(label.labelFor !== null && placementNameSet.has(label.labelFor), ...)`.
Impact: `UNAFFECTED`. This is a referential-integrity check on attribute
values; it does not depend on rendered geometry.

**Label has text content** (line 275):
`assert(label.hasText, ...)` where `hasText` is `(el.textContent ?? "").trim().length > 0`.
Impact: `UNAFFECTED`. Text content is position-independent.

**Comment documentation** (lines 16-17): describes `data-label` and
`data-label-for` as contractual selectors. Not an assertion.

### Assertion summary for test_scene_dom_contract_selectors.mjs

| Assertion | Category | Line(s) |
| --- | --- | --- |
| At least one label present | UNAFFECTED | 266 |
| data-label-for references real placement | UNAFFECTED | 271 |
| Label has text content | UNAFFECTED | 275 |

---

## File: test_scene_reactivity_lifecycle.mjs

### Description

Builds a harness bundle with esbuild and tests Solid's keyed reactive updates
and lifecycle (no-remount, fill-height change, SceneChange disposal). Label
references appear in one block only.

### Label-related assertions

**SVG-injection safety** (lines 125-155):

Collects all `[data-label]` text content at line 127-129:
```
const labels = Array.from(document.querySelectorAll("#scene-root [data-label]")).map(
  (l) => l.textContent || "",
);
```
Then for each item asserts that no authored label text appears verbatim inside
the injected SVG markup (lines 144-154):
`assert.ok(!it.svgText.includes(trimmed), ...)` for each `labelText` with
`trimmed.length >= 4`.

This checks that label text strings and SVG asset markup are kept separate
layers. It does not assert label position.

Impact: `UNAFFECTED`. The assertion is about text-layer isolation, not
geometry.

### Assertion summary for test_scene_reactivity_lifecycle.mjs

| Assertion | Category | Line(s) |
| --- | --- | --- |
| Authored label text not in SVG markup | UNAFFECTED | 148-153 |

---

## File: test_framed_layout_m2.mjs

### Description

Tests the M2 framed-layout shell assertions (scene-root size, shell regions,
coordinate integrity). Mentions "label" only in internal variable names or
comments; no `[data-label]` selector is used and no label geometry assertion
is present. `boundingBox()` is called for `#scene-root` (line 177) and for
each `[data-item-id]` element (line 309) for coordinate-containment checks.
Labels are not queried.

### Label-related assertions

None.

### Impact

`UNAFFECTED`. The framed-layout test does not touch label DOM nodes.

---

## File: test_affordance_evidence.mjs

### Description

Tests the interaction affordance rings (`data-affordance="candidate"` and
`data-affordance="active"`) on scene objects. The word "label" does not appear
as a DOM selector; no `[data-label]` query is present. The file references
`decorative label` in a comment at line 192 as a design assumption, not a
selector.

### Label-related assertions

None.

### Impact

`UNAFFECTED`.

---

## Files with no label-related assertions

The following files in `tests/playwright/` were searched and contain no label
DOM assertions relevant to WP-6:

- `test_svg_id_namespacing.mjs` -- "label" appears only as a variable name in
  `assertThrows(label, fn, needle)` (line 432), unrelated to DOM labels.
- `e2e/walker_helpers.mjs` -- "label" appears in a comment about step fields
  (line 7), not a DOM selector.
- All files in `tests/playwright/walker/` -- no label references.
- All other `.mjs` files listed in the directory (not matched by `rg`).

---

## Counts by impact category

| Category | Distinct assertion sites |
| --- | --- |
| BREAKS-LEGITIMATELY | 4 (H and I in bench_basic; H and I in generalization, each applied to 5 scenes) |
| NEEDS-JUDGMENT | 2 (G in bench_basic; G in generalization, applied to 5 scenes) |
| UNAFFECTED | 9 (J in bench_basic; J in generalization; all three in dom_contract; reactivity SVG-safety; framed_layout none; affordance none) |

Counting by unique assertion identifier across files:

| Category | Count |
| --- | --- |
| BREAKS-LEGITIMATELY | 2 unique assertions (H, I), present in 2 files |
| NEEDS-JUDGMENT | 1 unique assertion (G), present in 2 files |
| UNAFFECTED | all remaining label assertions |

---

## Recommended pre-WP-6 actions

1. Run the current test suite with labels in below position to capture baseline
   geometry values for assertions H and I. Save those as a reference.
2. After the WP-6 flip, re-run and compare. If H or I fail, the label
   rendering is geometrically correct but the test tolerances need updating.
3. Assertion G (label outside scene) is low risk if the scene boundary is
   generous. Verify by inspection that above-positioned labels on objects near
   the top of the scene stay inside `#scene-root`.
4. Assertions in `test_scene_dom_contract_selectors.mjs` require no changes.
