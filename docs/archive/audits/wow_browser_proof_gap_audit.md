# Browser proof gap audit

## Resolution status

Status: resolved for the 26.07.1 standard-browser curriculum scope.

The original audit found two false-green paths: accepted expected failures and
walkthrough-named tests that called `HTMLElement.click()` inside the page. Both
are closed. Every discovered curriculum protocol now uses the same canonical
visible walker, and a failure is a normal failed Playwright test. The collected
SDS-focused spec delegates to that walker; the exact-well drug spec uses real
Playwright locators; the obsolete manual all-wells script was removed.

The walker also gained evidence that the original audit lacked. Before each
authored action it records target geometry, viewport intersection, browser hit
testing, painted affordance, visible action cue, interaction ordinal,
`stateRevision`, and declared state. After the action it records and verifies
the ordered state delta. Exact subparts and every member of a declared group
must expose a learner-sized visible hit surface, and a real wrong-sibling click
must be rejected whenever a nonmember sibling exists.

## Closed findings

| Original finding                                                      | Decision and implementation                                                                                                                                                                         | Success condition                                                                                                                | Validation owner and evidence                                                                              |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Expected failures could produce a green suite                         | In scope and closed. `tests/playwright/e2e/protocol_walkthrough.spec.ts` has no expected-failure registry. Every discovered protocol must return `outcome.passed`.                                  | Zero accepted incomplete visible paths.                                                                                          | Walkthrough maintainer: full Playwright suite plus per-protocol reports under `test-results/walker/runs/`. |
| Walkthrough-named tests used synthetic DOM clicks                     | In scope and closed. `test_solid_walker.spec.ts` calls `runProtocolWalk`; `test_per_well_drug_walkthrough.spec.ts` uses locator clicks; the obsolete uncollected all-wells script was deleted.      | No walkthrough driver calls `HTMLElement.click()`, dispatches a synthetic progress event, forces a click, or writes `gameState`. | Test maintainer: source scan plus focused Solid and exact-well Playwright specs.                           |
| PNG files were not accepted checkpoint proof                          | In scope and closed for reachability/state proof. The checkpoint manifest asserts target bounds, viewport/hit-test status, affordance, cue, and pre/post state evidence.                            | Every green walk contains at least one valid checkpoint and every authored write is accounted for.                               | Walkthrough maintainer: manifest integrity assertions in the canonical sweep and wrong-order lane.         |
| Exact or group targets could fall back to a parent object             | In scope and closed. Exact subparts render their own surfaces. Declared groups render every concrete member under one semantic identity; geometry-complete nonmembers stay clickable for rejection. | No parent shortcut, invisible padding rectangle, or missing group member can satisfy a directed checkpoint.                      | Scene/UI maintainer: `tests/test_affordance.mjs`, exact-well Playwright, and full walker reports.          |
| Scientific state could advance without conserved sources/destinations | In scope and closed for the repaired Cell MTT and SDS-PAGE chains. Strict validation and browser state-delta checks cover every authored structured material write; numeric set points must fit the selected tool's declared range. | Sources decrement, destinations receive the declared material/volume/state, untargeted members remain unchanged, and an out-of-range instrument value fails before use. | Curriculum maintainers: focused Cell/SDS/range Python tests, strict content lint, and direct/runner walks. |

## Current contract-to-evidence matrix

| Requirement                                 | Current evidence                                                                                                                                                                                    | Grade and interpretation                                   |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Normal shipped entry                        | Playwright serves built `dist/` and opens each generated protocol page.                                                                                                                             | A: matches the standard browser entry used by students.    |
| Every protocol completes through visible UI | One discovered-protocol test calls `runProtocolWalk` and requires passed terminal state plus a valid checkpoint manifest.                                                                           | A: no expected-failure exception.                          |
| No hidden/internal progress                 | Drivers use Playwright locator click/fill/commit paths. `window.gameState` is read-only routing and evidence. Adjustment values come from the visible action rail; hidden type answers are refused. | A: learner-visible path only.                              |
| Wrong-object rejection                      | Wrong-order mode and exact/group sibling probes click real visible alternatives and require no progress.                                                                                            | A for authored click/select targets.                       |
| Target discoverability                      | Current-action rail names the object and action; exact/group surfaces carry painted focus and learner-sized cores.                                                                                  | A at the standard `1280 x 900` walkthrough viewport.       |
| State consequence                           | Checkpoints record before/after revision and the ordered declared-state delta; structured material effects verify all affected members.                                                             | A for authored state writes.                               |
| Scientific correctness                      | Cell MTT and SDS-PAGE have explicit content ledgers and focused invariant tests in addition to browser proof. SDS batch preparation visibly switches from P200 at 21 uL to P10 at 7.5 and 1.5 uL.     | A for the repaired chains; not a universal biology oracle. |

## Explicit out-of-scope decisions

- Responsive/touch corpus certification is out of scope because the course
  device range has not been specified. This version succeeds by certifying the
  standard desktop-browser student path and making no unsupported mobile or
  touch claim.
- Golden-image comparison is out of scope. This version succeeds because
  checkpoint manifests prove that the instructed object is visible,
  pointer-reachable, painted, and coupled to the declared consequence; it does
  not claim pixel-identical screenshots.
- Drag curriculum certification is out of scope because no released curriculum
  protocol authors `drag` and neither repaired chain needs it. The runtime seam
  is not counted as curriculum proof.
- Automated evaluation of every pedagogical or biological nuance is out of
  scope. This version succeeds with ratified Cell/SDS scientific invariants,
  visual-action evidence, and professor review rather than inventing an
  unrestricted machine-scored teaching rubric.

## Completed recovery artifacts

- `tests/playwright/e2e/protocol_walkthrough.spec.ts`: zero-exception acceptance
  sweep and wrong-order lane.
- `tests/playwright/e2e/helper_walker.mjs`: canonical visible driver, exact and
  group-target proof, wrong-sibling rejection, and declared-state accounting.
- `tests/playwright/e2e/walker_helpers.mjs`: actionability-checked interactions,
  visible adjustment-value extraction, bounded event-based waits, and
  checkpoint capture.
- `tests/playwright/test_solid_walker.spec.ts`: focused SDS acceptance through
  the canonical walker.
- `tests/playwright/test_per_well_drug_walkthrough.spec.ts`: real exact-well
  locators plus conservation of untargeted controls.
- `tests/test_walker_declared_state_proof.mjs` and
  `tests/test_material_area_verify.mjs`: generic state-delta and structured
  material-effect proof.

Release-gate commands and their final results are recorded in
[wow_recovery_plan.md](../../archive/wow_recovery_plan.md), which is the execution
record for this audit.
