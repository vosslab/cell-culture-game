# Browser proof gap audit

## Decision summary

The repo has a credible visible-UI acceptance spine: the configured runner has
86 Chromium tests, including one schema-driven end-to-end walk per discovered
curriculum protocol. It builds and serves \`dist/\` over HTTP, uses
actionability-checked clicks in the shared walker, checks terminal completion,
records wrong-object rejection, and saves per-step evidence.

This is real student-path evidence, not merely DOM testing. It should remain
the acceptance spine. A green suite is not yet a release-grade statement that
every protocol is student-completable and visually persuasive, because two
known-incomplete protocols are expected failures, some collected
walkthrough-named specs bypass actionability, screenshot contents are not
validated, and responsive interaction coverage is narrow.

\`NEEDS_CONTEXT\` means static review cannot establish current rendered pixels or
biology. It is not a claim that the behavior is broken.

## Contract-to-evidence matrix

| Requirement | Evidence now | Grade | Gap / interpretation |
| --- | --- | --- | --- |
| Normal shipped entry | Config builds and serves \`dist/\`; walker goes to each protocol page. [playwright.config.ts:88-124](../../../playwright.config.ts), [helper_walker.mjs:313-348](../../../tests/playwright/e2e/helper_walker.mjs) | A | Matches the test-style load model. |
| Every protocol completes through visible UI | One runner test per discovered protocol calls the shared walker and requires \`outcome.passed\`. [protocol_walkthrough.spec.ts:39-95](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts) | B | Two expected failures mean the suite can pass while the contract is unmet. [protocol_walkthrough.spec.ts:42-55](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts) |
| No hidden/internal progress | Core helper reads exported state then uses locator clicks after existence/visibility checks. [walker_helpers.mjs:146-181](../../../tests/playwright/e2e/walker_helpers.mjs) | A | Strongest student-path proof. |
| Wrong-object rejection | One protocol receives a real wrong click before each correct click. [protocol_walkthrough.spec.ts:100-132](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts), [helper_walker.mjs:178-196](../../../tests/playwright/e2e/helper_walker.mjs) | B | One protocol and click/select only; no erroneous type, adjust, or drag coverage. |
| Gesture coverage | Shared walker supports click/select/type/adjust and declares drag unsupported. [helper_walker.mjs:54-60](../../../tests/playwright/e2e/helper_walker.mjs), [helper_walker.mjs:212-256](../../../tests/playwright/e2e/helper_walker.mjs) | B | \`drag\` has no curriculum witness. \`NEEDS_CONTEXT\`: determine whether a learning block needs drag. |
| Before/after screenshot evidence | Initial, per-step, per-interaction, and final captures are emitted. [helper_walker.mjs:268-280](../../../tests/playwright/e2e/helper_walker.mjs), [helper_walker.mjs:373-415](../../../tests/playwright/e2e/helper_walker.mjs) | C | No pre-image per interaction, checkpoint manifest, or assertion that highlight, target, or intended visual state is visible. |
| Scientific asset integrity | Renderer tests inspect clipping/layout/labels across base scenes. [test_generalization_render.spec.ts:190-348](../../../tests/playwright/test_generalization_render.spec.ts) | B | Protocol-specific variants and intermediate states depend on unassessed screenshots. |
| Known reachability regression | Bbox, browser hit testing, trial actionability, and screenshots cover two objects in three scenes. [test_rear_tip_box_rack_identity.spec.ts:55-126](../../../tests/playwright/test_rear_tip_box_rack_identity.spec.ts) | A | Excellent targeted proof; not whole-scene coverage. |
| Viewport coverage | A four-viewport frame test exists for one protocol; runner uses Desktop Chrome. [test_letterbox_16x9.spec.ts:93-152](../../../tests/playwright/test_letterbox_16x9.spec.ts), [playwright.config.ts:103-107](../../../playwright.config.ts) | C | No curriculum-wide narrow-viewport, post-interaction, touch, zoom, or color-scheme reachability sweep. |
| Pedagogical correctness | Learning fields and ordered workflow are required. [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md), [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md) | D / NEEDS_CONTEXT | No test checks scientific correctness or that prompt, object, feedback, state change, and outcome agree. |

## Evidence classification

| Surface | What it proves | What it must not be counted as proving |
| --- | --- | --- |
| \`e2e/protocol_walkthrough.spec.ts\` + helper | End-to-end actionability-checked progression and terminal state, subject to expected failures. | Screenshot quality, biology accuracy, all modalities, or responsive usability. |
| \`smoke.spec.ts\` | Launcher boots, one link works, a scene mounts. [smoke.spec.ts:29-66](../../../tests/playwright/smoke.spec.ts) | Complete protocol or correct pedagogy. |
| Render/layout specs | Structural/pixel-geometry integrity for covered scenes. | That a student can find, understand, and complete an action. |
| \`test_scene_dom_contract_selectors.spec.ts\` | DOM contract and receipt of a synthetic event. [test_scene_dom_contract_selectors.spec.ts:37-39](../../../tests/playwright/test_scene_dom_contract_selectors.spec.ts), [test_scene_dom_contract_selectors.spec.ts:241-255](../../../tests/playwright/test_scene_dom_contract_selectors.spec.ts) | Student reachability or UI completion. It is structural by design. |
| \`test_interaction_attrs.spec.ts\` | Attached-node data attributes; it intentionally permits a non-visible root. [test_interaction_attrs.spec.ts:41-49](../../../tests/playwright/test_interaction_attrs.spec.ts) | Visible student affordances. |
| \`test_solid_walker.spec.ts\` | Runtime event/state behavior after DOM-triggered clicks. | Visible UI completion: it calls \`HTMLElement.click()\` in \`page.evaluate\`. [test_solid_walker.spec.ts:181-193](../../../tests/playwright/test_solid_walker.spec.ts) |
| \`test_per_well_drug_walkthrough.spec.ts\` | Expected-failure diagnosis and material-state correspondence after repair. | Current visible proof: its click helper calls \`HTMLElement.click()\` in \`page.evaluate\`. [test_per_well_drug_walkthrough.spec.ts:136-149](../../../tests/playwright/test_per_well_drug_walkthrough.spec.ts) |
| Uncollected \`.mjs\` walkthroughs | Exploratory/manual diagnostics when explicitly run. | CI coverage: config collects only \`*.spec.ts\`. [playwright.config.ts:88-92](../../../playwright.config.ts) |

## False-green and false-confidence findings

### P0: expected failures make the suite green while protocols remain incomplete

\`cell_culture_full\` and \`plate_drug_treatment_drug_addition\` deliberately run
as expected failures. This is honest defect tracking and better than \`skip\`,
but a passing job can coexist with both defects. Contract item 4 says an
incomplete visible path is not completion, so release reporting needs a
separate \`0 expected visible-UI failures\` gate.

Evidence: [protocol_walkthrough.spec.ts:42-55](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts), [PRIMARY_SPEC.md](../../PRIMARY_SPEC.md).

### P0: collected walkthrough-named specs bypass actionability

\`test_solid_walker.spec.ts\` and \`test_per_well_drug_walkthrough.spec.ts\` use
\`HTMLElement.click()\` inside the page. A programmatic DOM click does not prove
an element is stable, visible, unoccluded, or pointer-reachable. Keep these
tests as runtime/material tests until their drivers use the shared
actionability-checked helpers.

Evidence: [PLAYWRIGHT_TEST_STYLE.md](../../PLAYWRIGHT_TEST_STYLE.md), [PLAYWRIGHT_TEST_STYLE.md](../../PLAYWRIGHT_TEST_STYLE.md), [test_solid_walker.spec.ts:181-209](../../../tests/playwright/test_solid_walker.spec.ts), [test_per_well_drug_walkthrough.spec.ts:136-176](../../../tests/playwright/test_per_well_drug_walkthrough.spec.ts).

### P1: visual evidence is files, not accepted visual proof

The walker produces PNGs but no reviewer-facing manifest says what each image
must show. A missing highlight, incorrect liquid color, clipped tube, or
imperceptible state change can produce a valid PNG and green state assertion.
The visual-integrity contract is stronger than bbox-only checks.

Evidence: [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md), [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md), [helper_walker.mjs:259-280](../../../tests/playwright/e2e/helper_walker.mjs).

### P1: responsive proof is narrow and mostly pre-interaction

The four-viewport test is useful but loads one protocol and checks frame/center
geometry. It does not prove that each required target remains visible and
reachable before and after interactions at constrained sizes. \`NEEDS_CONTEXT\`:
confirm the student-device viewport range before choosing exact widths.

### P2: documented scratch exclusion is absent from config

The style guide asks for \`testIgnore\` covering \`_temp*\` and \`dist_*/\`; the
config has restrictive \`testMatch\` but no explicit \`testIgnore\`. This is test
hygiene risk, not current student-path breakage.

Evidence: [PLAYWRIGHT_TEST_STYLE.md](../../PLAYWRIGHT_TEST_STYLE.md), [playwright.config.ts:88-98](../../../playwright.config.ts).

## Highest-risk uncovered behavior

The highest-risk gap is a protocol whose required action renders but is not
discoverable or pointer-reachable in the student's viewport or intermediate
state. Static DOM tests, base-scene geometry checks, and unreviewed screenshots
can all miss it. The tube-rack subpart expected failure is direct evidence that
semantic targets can outgrow rendered affordances.

Next is a mechanically complete but pedagogically wrong path: incorrect prompt,
wrong highlight, invisible consequence, or biologically misleading response.
Browser automation cannot responsibly invent a biology oracle; this needs a
teaching rubric and human review.

## Bisect-friendly plan

1. Add a small acceptance-lane assertion that release status requires zero
   expected visible-UI failures. Keep a diagnostic lane that still runs them.
2. Replace \`page.evaluate(...el.click())\` in the two collected walkthrough
   specs with existing visible/actionability helpers. Do one spec per commit.
3. Have the shared walker emit a JSON checkpoint per interaction: protocol,
   step, target, gesture, pre/post screenshot, visible target bbox, prompt, and
   expected state transition. Assert files exist and target bboxes are on screen.
4. Add one representative visual-state test per family: highlight, material,
   prompt/tooltip, selection, modal, timed wait, type, adjust, and drag if a
   curriculum protocol ratifies it.
5. Add a two-viewport actionability sweep: a course-evidenced desktop width and
   constrained laptop/tablet width. Walk initial and post-scene-change steps.
6. Create a human pedagogy score sheet for each protocol: objective-to-step
   alignment, scientific order, cue before action, perceptible consequence,
   wrong-action feedback, and no unexplained leap. Convert only ratified,
   repeatable findings into automated tests.

## Verification performed

- Compared Contract item 4, walker rules, and Playwright style against the
  collected suite and relevant browser tests.
- \`npx playwright test --list\` succeeded and reported **86 tests in 22
  collected \`*.spec.ts\` files**. It did not execute browser tests.
- No product or test source was edited; unrelated worktree changes were
  preserved.

## Residual risk

This is a test-shape audit, not a live visual or biology review. It did not run
protocols, inspect screenshots, or judge the scientific clarity of prompts.
