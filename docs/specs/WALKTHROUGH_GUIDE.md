# Walkthrough guide

## Purpose

This guide documents the real-browser protocol walkthrough system. The
walkthrough is not a unit test. It is a Playwright-driven UI walker that starts
the built app, opens a protocol in a browser, clicks real DOM elements, waits
for observable game-state progress, records a JSON report, and saves
screenshots.

The canonical walker is
[protocol_walkthrough_yaml.mjs](../../tests/playwright/e2e/protocol_walkthrough_yaml.mjs).
Shared helpers live in
[walker_helpers.mjs](../../tests/playwright/e2e/walker_helpers.mjs). The optional
Python wrapper is
[run_protocol_walkthrough.py](../../tools/run_protocol_walkthrough.py). The fast
browser smoke wrapper [run_smoke.py](../../tools/run_smoke.py) is useful context,
but it is not a full protocol walkthrough.

The goal is to prove that a mini-protocol is playable through visible browser
interactions, not merely schema-valid.

The walker drives the Solid protocol host
([protocol_host.tsx](../../src/protocol_host.tsx)). It reads two FROZEN
read-only browser surfaces and never writes them:

- `window.PROTOCOL_STEPS`: the step list (`id` / `label` / `scene` / `nextId`).
- `window.gameState`: the read-only progress projection, including the current
  interaction's `activeTarget` / `activeGesture` (the same fields the runtime
  itself uses to resolve a click's gesture) plus the progress signals the
  progress predicate watches.

Both surfaces are installed by
[walker_debug.ts](../../src/scene_runtime/protocol/walker_debug.ts) and are a
projection of the step machine's emitter snapshot plus the scene store. The
walker reads `gameState.activeTarget` to know which visible `[data-item-id]`
element to click next, so it stays schema-driven with no per-protocol branch and
no internal-API call.

## System overview

The walkthrough has four layers:

| Layer          | File                                                                                      | Responsibility                                                                           |
| -------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Built app      | `dist/`                                                                                   | Browser-rendered game output produced by the build                                       |
| Node walker    | [protocol_walkthrough_yaml.mjs](../../tests/playwright/e2e/protocol_walkthrough_yaml.mjs) | Starts the server, launches Playwright, opens the protocol, walks steps, writes evidence |
| Helper library | [walker_helpers.mjs](../../tests/playwright/e2e/walker_helpers.mjs)                       | Selector resolution, real-click-and-wait-for-progress, wrong-order helpers               |
| Python wrapper | [run_protocol_walkthrough.py](../../tools/run_protocol_walkthrough.py)                    | Optional build-and-run convenience around the Node walker                                |

The core loop is:

1. Serve the compiled `dist/` directory.
2. Launch headless Chromium through Playwright.
3. Open the per-protocol page `/<protocol>.html` exactly as a student would.
4. Reset browser persistence with `localStorage.clear()` and reload.
5. Enter through any visible welcome/start control (best-effort; the new host
   has none, so this is a no-op there).
6. Read the compiled step list from `window.PROTOCOL_STEPS`.
7. Drive the active step: read `gameState.activeTarget` / `gameState.activeGesture`
   and prove that the same target is advertised by the visible action cue and
   painted scene affordance before acting through the visible control.
8. When a timed operation intentionally removes the active target, require the
   visible scene timer and explanatory waiting rail before waiting for the next
   action.
9. Wait for an observable progress signal after each action.
10. Verify step completion and next-step advancement through the read-only state.
11. Save report and screenshot evidence.

The walker is both an E2E test and a playable audit. It is an E2E test because
it starts the built app in a browser and completes the protocol through real
DOM clicks. It is a playable audit because it checks whether a learner-visible
path actually exists through the protocol.
It is stricter than a smoke test because it must complete the protocol. It is
less detailed than a visual regression suite because it does not yet prove
every intermediate rendered state.

## What the walkthrough proves

A passing walkthrough proves that the compiled `dist/` app can be
served locally and completed through the same visible click path a learner uses.

Specifically, it proves:

- The built app loads through the per-protocol page `/<protocol_name>.html`.
- The walker starts from normal browser entry, clears `localStorage`, reloads,
  and dismisses any visible welcome/start control by clicking it (the new host
  has none).
- Protocol steps are available through `window.PROTOCOL_STEPS`.
- Runtime state is available through `window.gameState`, including the current
  interaction's `activeTarget` / `activeGesture`.
- Required scene objects exist as DOM elements with `data-item-id`.
- Required targets are visible and intersect the viewport when the walker acts.
- The target carries the expected painted `active` or `candidate` affordance.
- The visible current-action rail advertises the same target and gesture.
- Directed instructions name the generated learner-facing object label.
- Choice-style `select` instructions do not reveal the answer and expose at
  least two visible candidates.
- Intentional timed waits show both a scene timer and an explanatory waiting
  rail before the walker waits for the next action.
- Clicks go through browser event handlers, not direct protocol APIs.
- Each click that uses `clickTargetAndWaitProgress()` produces observable state
  progress.
- Each step's `step_validator` passes and emits a `<step_name>_complete` event.
- The runtime advances to the step's `next_step`, or to a terminal state when `next_step` is `null`.
- The protocol reaches the terminal state: `isComplete` is `true`, `activeStepId`
  is `null`, and `completedSteps` covers every step.
- Console errors and same-origin network failures are captured in the report.

This is the browser evidence side of
[../PRIMARY_CONTRACT.md](../PRIMARY_CONTRACT.md): a mini-protocol is not complete
until the visible interaction works.

## Current proof boundary

The walkthrough is not a replacement for protocol validators, TypeScript
checks, focused unit tests, or visual regression tests.

Current limits:

- It saves the actionable state before every interaction, but not the rendered
  result after every click unless per-click screenshots are enabled.
- It does not compare screenshots against golden baselines.
- It does not prove that every intermediate teaching visual is correct.
- It does not inspect every visual style detail such as exact highlight color,
  liquid fill geometry, label placement, or animation timing.

The current evidence is strong enough to prove browser-playable completion. It
is not yet strong enough to prove fine-grained visual pedagogy at every click.

## How to run it

Normal walkthroughs use local headless Playwright against the compiled
`dist/` app. Build first, then run the Node walker from the repo root:

```bash
npm run build
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_assemble_electrode_module
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_extract_gel_from_cassette
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_assemble_electrode_module --wrong-order
```

To capture finer-grained screenshot evidence, use the `--screenshots` flag:

```bash
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_extract_gel_from_cassette --screenshots per-interaction
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_extract_gel_from_cassette --screenshots per-click
```

The walker drives the closed gesture set the new host exposes a visible
affordance for (currently `click`, `select`, `type`, and `adjust`). `select`
reuses the visible scene-object click affordance (the host promotes a click on
the active target to the `select` gesture); `type` fills + commits the visible
type-input affordance (`[data-type-input]` / `[data-type-commit]`); `adjust`
sets + commits a value in the shared numeric set-point editor
(`[data-adjust-input]` / `[data-adjust-commit]`). `drag` is wired in the runtime
and proven by the step-machine unit test and the walker driver, but no content
protocol authors a drag yet, so the sweep still classifies a `drag` interaction
`unsupported_gesture` rather than silently skipping or branching per protocol;
adding `drag` to the sweep set is a one-line change once a real drag protocol
lands. The simplest all-`click` protocols (`sdspage_assemble_electrode_module`,
`sdspage_extract_gel_from_cassette`) walk end-to-end, and the real walker
sweep over `content/protocols/**` exercises the `select` and `type` gestures
(including a wrong-selection rejection under `--wrong-order`).

The `--screenshots` flag accepts `per-step` (default), `per-interaction`, or
`per-click`. Per-interaction and per-click modes add report entries in
`playthrough_report.json` that link each screenshot to its `step_name`,
`interaction_index`, `gesture`, and `target`.

The Node walker:

- Starts an owned `python3 -m http.server` child for `dist/`.
- Requests an OS-assigned port by default, verifies that its own child bound
  that port, and tears down only that child.
- Opens `http://127.0.0.1:<assigned-port>/<protocol_name>.html`.
- Accepts `--port` (or `PORT`) only as an explicit fixed-port override and
  fails before navigation when that port is already occupied.
- Launches Chromium through the Playwright library.
- Uses a `1280 x 900` viewport.
- Runs headless.

To sweep every curriculum protocol under `content/protocols/` in one run
(worst-first summary plus `test-results/walker/sweep_summary.json`), build once
and run the sweep runner or its `npm run walk:all` alias:

```bash
npm run build
node tests/playwright/e2e/walk_all_protocols.mjs
```

The front-door script `run_playwright_tests.sh` drives the same sweep and is the
recommended entry point. It builds `dist/` when it is missing (or with `--build`
to force a rebuild), runs `walk_all_protocols.mjs`, and prints a final `PASS` or
`FAIL` line. It mirrors the `npm run test:playwright` alias:

```bash
./run_playwright_tests.sh
./run_playwright_tests.sh --build
```

`run_playwright_tests.sh` is kept separate from `check_codebase.sh` so the fast
typecheck/lint/format/unit gate stays fast; the browser walker sweep is its own
front door.

The Python wrapper is an optional convenience around the same headless
walkthrough. It can build first and then invoke the Node walker:

```bash
python3 tools/run_protocol_walkthrough.py --protocol tutorial_plate_drug_additions
```

Agents running Python in this repo should use the repo Python environment:

```bash
source source_me.sh && python3 tools/run_protocol_walkthrough.py --protocol tutorial_plate_drug_additions
```

The wrapper also supports:

- `--list-protocols`: list protocol names discovered by recursively searching
  `content/protocols/**/protocol.yaml` (works with both the flat
  `content/protocols/<name>` and clustered `content/protocols/<cluster>/<name>`
  layouts).
- `--wrong-order`: pass wrong-order mode through to the Node walker.
- `--no-build`: skip its build step and run the walker against the existing
  `dist/` output.

The three workflows are:

| Workflow            | Use                                                                   | Command                                                                   |
| ------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Normal walkthrough  | Default real-browser protocol walkthrough                             | `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <id>` |
| Python wrapper      | Optional convenience around the same headless walker                  | `python3 tools/run_protocol_walkthrough.py --protocol <id>`               |
| Codex-only fallback | UI review only when local browser launch fails in Codex macOS sandbox | `tools/run_ui_review_podman.sh`                                           |

The Podman path is not the default walkthrough path. It is only for Codex macOS
sandbox browser-launch failures during screenshot-oriented UI review. It is not
for ordinary walkthroughs and not for Claude Code.

## Output files

The walker writes output under:

```text
test-results/walker/
```

Current outputs include:

- `playthrough_report.json`: structured run report with timestamp, protocol id,
  wrong-order mode, screenshot mode, summary counts, log entries, final-state
  notes, console errors, and same-origin network errors.
- `initial_state.png`: screenshot after browser entry, localStorage clearing,
  reload, and welcome dismissal.
- `checkpoint_<step>_i<n>_<target>.png`: actionable-state evidence saved before
  every interaction. Each corresponding manifest entry records viewport
  geometry, painted-affordance evidence, and the visible action cue.
- `waiting_<step>.png`: evidence that an intentional timed phase is explained
  in both the scene and current-action rail.
- `step_<n>_<step_name>.png`: screenshot after each passed step.
- `fail_<step_name>.png`: screenshot after a step failure.
- `final_screen.png`: screenshot after final checks.
- `crash_screen.png`: screenshot if the top-level walker crashes.
- `interaction_<step_name>_i<n>_<target>.png`: screenshot after each interaction
  (only when `--screenshots per-interaction` is set).
- `click_<step_name>_i<n>_c<k>_<item_id>.png`: screenshot after each click
  (only when `--screenshots per-click` is set).

The report summary currently tracks:

- `stepsWalked`
- `stepsPassed`
- `stepsFailed`
- `totalClicks`
- `failureReason`

Report entries are timestamped and have a severity such as `info`, `warn`,
`error`, or `injection`. Wrong-order injections are intentionally logged with
the `injection` severity so they are grep-able.

## How the walker starts

The startup sequence is part of the contract. The walker does not call a test
API to place the app in a ready state.

The current sequence is:

1. Start a local static server for `dist/`.
2. Launch Chromium headlessly with Playwright.
3. Open `/<protocol_name>.html`.
4. Wait for browser exports: `window.gameState` and
   `window.PROTOCOL_STEPS` (read-only walker surfaces).
5. Clear `localStorage`.
6. Reload the page.
7. Wait for exports again.
8. Click a visible welcome/start control if present (the new host has none, so
   this is a no-op there; `step_machine.start()` already ran at mount).
9. Read `window.PROTOCOL_STEPS` from the page.
10. Save `initial_state.png`.

This matters because persisted browser state can hide runtime bugs. The walker
is expected to start from fresh browser state and enter through the same UI path
as a normal user.

## How the walker decides what to click

The walker is schema-driven. `walkActiveStep()` dispatches from the current
interaction's `gesture` plus its resolved `target`, not from a per-step kind
discriminator and not from a hand-authored recipe table. Step kinds are retired
entirely; see [../PRIMARY_SPEC.md](../PRIMARY_SPEC.md) for the canonical
interaction model.

The walker does not parse the protocol YAML itself. It reads the current
interaction's `target` and `gesture` from the read-only `window.gameState`
(`activeTarget` / `activeGesture`). These are projected from the same emitter
snapshot the runtime uses to resolve a click's gesture, so the walker mirrors
the runtime's own resolution: it clicks the visible `[data-item-id]` element
whose id equals `activeTarget`. The runtime advances `interactionIndex` on each
validated interaction and changes `activeStepId` when the step completes, so the
walker simply loops: read the active interaction, click its target, wait for
progress, repeat until the step id changes.

Reading the answer from `gameState` is routing data, not proof that a learner
could find it. Before every interaction,
`captureVisibleTargetCheckpoint()` independently requires the visible product
UI to advertise the same target and gesture. Directed interactions need a
painted active affordance plus a cue containing the generated object label.
`select` needs painted candidate affordances and an answer-neutral cue. The
walker fails instead of clicking when this learner-facing evidence is absent.

The walker acts only on the closed gesture set (`click`, `drag`, `adjust`,
`select`, `type`). `click`, `select`, `type`, and `adjust` all have a visible
affordance in the new host: the click resolver promotes a click on the active
target to the active gesture, so `select` -- choosing the correct next-step
object among the present objects -- reuses the click path; `type` fills + commits
the visible type-input affordance; `adjust` sets + commits a value in the shared
numeric set-point editor. `drag` is wired but no content protocol authors one
yet, so a `drag` interaction still FAILS with an `unsupported_gesture`
classification rather than silently skipping or branching per protocol. For a
`type` interaction the walker reads the expected value read-only from
`gameState.activeTypeValue` (projected from the authored validator `value`) and
types it into `[data-type-input]`, then clicks `[data-type-commit]`; for an
`adjust` interaction it reads `gameState.activeAdjustValue` and commits it on
`[data-adjust-input]` / `[data-adjust-commit]`.

See `docs/specs/GESTURE_MODEL.md` for the distinction between this
browser-driving mechanism and the authored gesture semantics, including the
reopened status of the unused `select` value.

The central click helper is `clickTargetAndWaitProgress()`. After the separate
checkpoint has proved the learner-facing cue and affordance, it resolves a
scene-scoped `data-item-id` selector, verifies that the element exists, verifies
that it is visible, clicks it via Playwright's actionability-checked
`locator.click()`, increments `report.summary.totalClicks`, and waits for
observable state progress.

The progress predicate accepts any observable state change produced by a
validated interaction's `response.scene_operations`, read from `gameState`:

- An `ObjectStateChange` advanced `interactionIndex` (or completed the step).
- A `CursorAttach` changed `selectedTool` / `heldLiquid`.
- A `SceneChange` switched `activeScene`.
- A step resolved `complete` (`activeStepId` advanced, `completedSteps` grew, or
  `isComplete` flipped).

If none of those changes occur before the click budget expires, the helper
throws:

```text
click_did_not_advance: click on <object_name> produced no state change after <ms>ms
```

## Scene scoping

The new host mounts exactly one scene at a time into `#scene-root` (it tags the
active scene with `data-active-scene`). `resolveSelector()` therefore scopes
every item to `#scene-root`:

```text
#scene-root [data-item-id="<object_name>"]
```

This avoids picking up a shell or outline element that might share an id, and it
needs no per-scene container map.

Scene switches are NOT performed by the walker. They happen through the same
visible-click gesture model: a validated click whose `response` carries a
`SceneChange` scene_operation re-renders the next scene into `#scene-root`. The
walker observes the switch through `gameState.activeScene`; it never writes
`activeScene` and never clicks a dedicated scene-switch button. This catches
scene-wiring problems that direct state writes would hide.

## Interaction support

The walker dispatches from each interaction's closed `gesture` set
(`click`, `drag`, `adjust`, `select`, `type`) and the resolved `target`. The
retired per-step kinds (`interactionSequence`, `directTool`, `modal`,
`multipleChoice`) are no longer dispatchable shapes; every step is one
ordered `sequence` of interactions per [../PRIMARY_SPEC.md](../PRIMARY_SPEC.md).

Current new-host affordance coverage:

- `click` and `select` are fully supported. The click resolver promotes a click
  on the active target to whatever gesture that interaction declares, so a
  `click` interaction walks directly and a `select` interaction (choosing the
  correct next-step object among the present scene objects) reuses the same
  visible-click affordance. Selecting a wrong present object is rejected, exactly
  like a wrong-order click.
- `type` is supported through the visible type-input affordance
  (`[data-type-input]` + `[data-type-commit]`, from `src/shell/hud/type_input.tsx`).
  It appears only while the active interaction's gesture is `type`; the walker
  fills it and clicks Commit, routing the typed text to
  `step_machine.handle_type_commit` (validated by `target_with_value`).
- `adjust` is supported through the shared numeric set-point editor
  (`[data-adjust-input]` + `[data-adjust-commit]`, from
  `src/shell/hud/set_point_editor.tsx`). It appears only while the active
  interaction's gesture is `adjust`; the walker sets the value and clicks Commit,
  routing the committed number to `step_machine.handle_adjust_commit` (coerced to
  the field's declared type and validated by `target_with_value`).
- `drag` is wired in the runtime (`step_machine.handle_drag_commit` plus the host
  drag surface) and proven by the step-machine unit test and the
  `dragToAndWaitProgress` walker driver, but no content protocol authors a drag
  yet. Until one does, a `drag` interaction fails with `unsupported_gesture`;
  adding `drag` to the walker's supported set is a one-line change once a real
  drag protocol lands.

The walker stays schema-driven. Step-name-specific branches and per-protocol
special cases are not allowed; if the visible UI cannot be exercised by the
closed gesture set, the fix is to extend the YAML, scene, or runtime (add the
visible affordance), never to add a walker branch.

## Implementation nuances

These details are easy to miss when extending the walker.

`clickTargetAndWaitProgress()` is deliberately state-based, not time-based. It
does not sleep after a click and hope the UI changed. It snapshots selected
tool, held liquid, interaction index, active step, active scene, completed step
count, and `isComplete` before the click. After the click, it waits until one of
those values changes. The wait predicate only READS `window.gameState`; it never
writes it.

That design catches silent click-handler failures, but it also means a valid
click that only changes CSS and not game state will fail. If a new interaction
is meant to be walker-driven, it needs an observable state signal (an
`ObjectStateChange`, `CursorAttach`, `SceneChange`, or step completion).

Selectors are scene-scoped to `#scene-root`. The new host mounts one scene at a
time, so `resolveSelector()` always scopes to `#scene-root [data-item-id="..."]`
without a per-scene container map.

The walker reads the active interaction from `gameState.activeTarget` /
`gameState.activeGesture`. It does not parse protocol YAML and does not call any
internal runtime API to discover what to click; the read-only projection is the
single source of the path.

The walker records console and network errors without stopping immediately.
Those errors are collected during the run and then written into the report and
used in the final pass/fail decision. A visually completed run can still fail
because the browser logged application errors or same-origin asset failures.

## Edge cases for new coders

When a new protocol or scene fails in the walker, check these cases before
adding special-case code.

| Symptom                                         | Likely cause                                                                                                       | Better fix                                                                                                   |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `Element ... does not exist in DOM`             | Item id is missing from scene YAML, render output, or modal markup                                                 | Add the item to the scene/render path or fix the id                                                          |
| `Element ... is not visible`                    | Wrong scene is active, hidden duplicate was selected, or overlay state blocks the target                           | Fix scene switching or pass a scoped scene selector                                                          |
| `click_did_not_advance`                         | Click handler is missing, handler changes only CSS, or state signal is delayed beyond budget                       | Add the runtime handler or expose an observable state change                                                 |
| Active step advances to the wrong `step_name`   | Step completes but the runtime resolves `next_step` to a wrong or missing step                                     | Fix protocol YAML `next_step` value or completion dispatch                                                   |
| Protocol never reaches `isComplete`             | Terminal step did not complete, or a later step stalled                                                            | Fix the terminal step's completion path or the stalled step                                                  |
| Wrong-order injection advances the step         | Runtime accepts a non-required interaction as valid progress                                                       | Tighten interaction-validator dispatch and active-target checks                                              |
| Mini-protocol enters hood or bench unexpectedly | Scene isolation is broken for a workspace-only protocol                                                            | Fix the `SceneChange` `scene_operation` chain in the affected step's `response`                              |
| `unsupported_gesture` on a step                 | Active interaction needs `drag`; the sweep does not drive `drag` until a content protocol authors one              | Author the drag protocol, then add `drag` to the walker's supported set (a one-line change)                  |
| `type_input_missing` / `type_did_not_advance`   | `type` interaction active but the type-input affordance is missing/hidden, or the committed value did not validate | Confirm `[data-type-input]`/`[data-type-commit]` render and the validator `value` matches the committed text |

Prefer fixing runtime schema, YAML, render output, or dispatch behavior before
adding walker branches. The walker is most valuable when it remains a generic
consumer of the same schema the app uses.

## Adding new interaction behavior

When a step needs a behavior the existing closed gesture set cannot express,
update the YAML vocabulary, runtime, and walker together. Step kinds are
retired; behavior extends through the gesture set, the `scene_operation`
primitives, and the validator preset library.

The minimum implementation contract is:

- The YAML schema describes the behavior through `gesture`, `target`,
  `validator`, and `response.scene_operations` without relying on a
  `step_name`.
- Runtime rendering exposes visible click targets with stable ids resolved
  from `object_name` (or `<object_name>.<subpart_name>`).
- Runtime dispatch advances state through normal handlers for the named
  gesture, firing the validator preset and the response's
  `scene_operations`.
- The walker resolves the same ids from the schema.
- Every walker interaction produces an observable state-progress signal
  through an `ObjectStateChange`, `CursorAttach`, `SceneChange`, or
  step-complete event. `LayoutMove` is ratified vocabulary but cannot provide
  a signal: current runtime dispatch throws because no placement-override
  write surface exists.
- The step's `step_validator` resolves and the runtime advances to
  `next_step`.
- Screenshot evidence captures before/after step boundary.

Avoid encoding protocol knowledge in the walker. A branch such as "if this
step is `some_specific_step_name`, click these three things" is usually a
sign that the schema or scene affordance is missing a concept.

## Adding a walkthrough for a new mini-protocol

To make a new mini-protocol walkthrough-ready:

1. Add the mini-protocol under `content/protocols/<cluster>/<protocol_name>/`.
2. Make sure `protocol.yaml` has a complete step chain.
3. Give every step a stable `step_name`.
4. Give every step a `sequence` of one or more interactions.
5. Each interaction declares a `target`, a `gesture`, a `validator`, and a
   `response`; the closed gesture set is `click`, `drag`, `adjust`,
   `select`, `type`.
6. Give every step a `next_step`, or `next_step: null` for the final step.
7. Make sure every clicked object exists in `content/objects/` and is
   placed in the relevant protocol scene.
8. Make sure every clicked object renders with `data-item-id="<object_name>"`.
9. Make sure every interaction's `response.scene_operations` produces an
   observable state change.
10. Build the app.
11. Run the walkthrough.
12. Inspect `test-results/walker/playthrough_report.json`.
13. Inspect the screenshots in `test-results/walker/`.

Observable state for walker interactions currently means at least one of
these signals fires:

- An `ObjectStateChange` mutates a declared `state_field`.
- A `CursorAttach` attaches or detaches a tool.
- A `SceneChange` switches the active scene.
- A `<step_name>_complete` event fires.

`LayoutMove` cannot satisfy this requirement in the current runtime. It stays
in the closed primitive vocabulary, but dispatch always throws before any
placement changes; author it only after executable placement-override support
exists.

Use this run pattern:

```bash
npm run build
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <protocol_name>
```

For a negative-order pass, also run:

```bash
node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <protocol_name> --wrong-order
```

## Walkthrough-ready definition

A mini-protocol is walkthrough-ready when the walker can complete it from a
fresh browser state using only real DOM clicks, with no direct game-state
mutation, no hidden click targets, no missing scene objects, no console errors,
and a terminal state (`isComplete` true, `activeStepId` null, every step in
`completedSteps`).

## Failure modes

The walker fails when the visible UI cannot support the protocol. Important
failure cases include:

- The static server does not start.
- Browser exports do not appear.
- A step has no supported completion path.
- A required item does not exist in the DOM.
- A required item exists but is hidden.
- A click produces no observable state change.
- A step exceeds its per-step budget.
- The whole run exceeds its run budget.
- A step's `step_validator` does not pass, so no `<step_name>_complete` event fires.
- The runtime advances to the wrong `step_name`, or `next_step` resolves to a missing step.
- Wrong-order clicks are accepted during the correct sequence.
- The active interaction needs a gesture the new host cannot drive yet
  (`unsupported_gesture`).
- The protocol never reaches the terminal state (`isComplete` stays false).
- Console errors are detected.
- Same-origin network requests fail.
- The walker crashes before normal cleanup.

Current budgets:

| Budget    | Value      | Failure                 |
| --------- | ---------- | ----------------------- |
| Per click | `3000ms`   | `click_did_not_advance` |
| Per step  | `30000ms`  | `step_stalled`          |
| Whole run | `600000ms` | `run_stalled`           |

## Wrong-order mode

`--wrong-order` mode is a negative test. Before each scene-target interaction
currently driven by a browser click (`click` or `select`), the walker finds a
visible, pointer-actionable `#scene-root [data-item-id]` element that is not the
current `activeTarget` and activates it with a real browser click. That shared
low-level input is an implementation detail. The walker must preserve the
authored gesture value and current validator dispatch while the semantic role
of the unused `select` value remains reopened.

The wrong-order click must:

- Increment the read-only `gameState.wrongOrderClicks` counter (the runtime
  declined to advance on a non-required target).
- Leave the step's `interactionIndex` unchanged.
- Leave `activeStepId` unchanged.

The new host has no `wrong_order_message` toast affordance, so the walker
asserts rejection through the `wrongOrderClicks` counter rather than a toast.
After the injected click is verified rejected, the walker performs the correct
click. In wrong-order mode the end-state check tolerates
`wrongOrderClicks > 0`.

## Screenshot evidence status

The walkthrough uses headless Playwright. It captures screenshots at step
boundaries by default: initial state, after each passed step, failure state,
final screen, and crash state.

Finer-grained screenshot modes are available via the `--screenshots` flag:

| Mode              | Description                                                                                                                                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `per-step`        | One screenshot after each step (default, existing behavior)                                                                                                     |
| `per-interaction` | Screenshot after every interaction in a step's `sequence`; report entries link each screenshot to its `step_name`, `interaction_index`, `gesture`, and `target` |
| `per-click`       | Screenshot after every individual click within an interaction; same report fields                                                                               |

Screenshots are always saved under `test-results/walker/`. Naming conventions:

- Per-step: `step_<n>_<step_name>.png` (existing)
- Per-interaction: `interaction_<step_name>_i<interaction_index>_<target>.png`
- Per-click: `click_<step_name>_i<interaction_index>_c<click_index>_<item_id>.png`

Report entries for per-interaction and per-click modes include the fields
`screenshot`, `step_name`, `interaction_index`, `gesture`, and `target` so the
report is self-documenting at the interaction level.

The `playthrough_report.json` top-level field `screenshotMode` records which
mode was used, making the report self-describing.

## Required future work

Documented future work, not yet implemented:

- Author a content protocol that uses the `drag` gesture, then add `drag` to
  the walker's supported set. The drag affordance and `handle_drag_commit` are
  already wired; the sweep leaves `drag` classified `unsupported_gesture` only
  because no content protocol authors one yet. This is a content + one-line
  walker change, never a per-protocol walker branch.
- Compare screenshots against golden baselines.
- Prove that every intermediate teaching visual is correct.

## Mini-protocol completion contract

A mini-protocol is not complete until the visible interaction works. A
walkthrough must run through each step and click each required interaction
through the real browser UI. Passing TypeScript, validators, and walker setup
is not enough.

The current walker saves a checkpoint before every interaction and a
step-boundary screenshot after each completed step. The checkpoint manifest
shows that intended targets are visible, action cues and painted affordances
agree, and the action remains schema-driven. Per-click mode remains available
when evidence of every post-action rendered state is needed.

## Headless browser contract

The walkthrough uses Chromium through the Playwright library, launched headless
by default. This aligns with [../PLAYWRIGHT_USAGE.md](../PLAYWRIGHT_USAGE.md): the
canonical pattern is `chromium.launch()` with no headed option, and existing
scripts already run headless.

Agents should not document headed mode as the normal workflow, should not add
`headless: false`, and should not add `--headed` to walkthrough commands. Human
local debugging may use headed mode manually, but that is not part of the
walkthrough contract.

## Relationship to smoke tests

[run_smoke.py](../../tools/run_smoke.py) builds the app and runs a fast browser
smoke test that checks that the app loads, key UI elements render, and basic
early gates pass.

Use smoke tests for fast browser sanity checks. Use the walkthrough when the
question is whether a complete protocol can be played through visible UI
interactions.

## When to update this guide

Update this guide whenever the walker gains support for a new gesture, a new
screenshot evidence mode, a new read-only `gameState` field it depends on, or a
new failure mode that future coders are likely to hit.

## Related docs

- [../PRIMARY_CONTRACT.md](../PRIMARY_CONTRACT.md): non-negotiable mini-protocol
  completion rule.
- [../PLAYWRIGHT_USAGE.md](../PLAYWRIGHT_USAGE.md): Playwright conventions,
  headless default, and Codex-only Podman fallback.
- [../E2E_TESTS.md](../E2E_TESTS.md): browser test placement and E2E conventions.
- [PROTOCOL_AUTHORING_GUIDE.md](PROTOCOL_AUTHORING_GUIDE.md): protocol
  authoring workflow and validation gates.
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md): protocol schema.
