# Walker timeout triage

## Purpose

The all-protocols walker sweep (`tests/playwright/e2e/walk_all_protocols.mjs`,
`npm run walk:all`) reported 6 timeouts, all failing with
`page.waitForFunction: Timeout 30000ms exceeded`. This report separates
genuine never-completing bugs from walker-budget noise for each of the 6,
before M16 spends effort on the wrong fix.

## Verdict summary

All 6 are real bugs. None are walker-budget noise. Raising the walker's
timeout, even far past the documented 30000ms per-step budget, does not
change the outcome for any of the 6: each one crashes deterministically
inside `protocol_host_entry` at page-load time, before the walker ever
reaches its first click.

| Protocol | Stalls at | Raised-budget outcome (90000ms) | Verdict | Root cause class | Recommended action |
| --- | --- | --- | --- | --- | --- |
| `cell_culture_full` | `waitForExports` (initial page load, before any step) | Still fails; `window.PROTOCOL_STEPS` stays permanently empty | real-bug | (a) sequence_runner playback unimplemented | Fix M16: implement mini-protocol chaining in `protocol_host.tsx`/`step_machine.ts` |
| `routine_passage` | `waitForExports` (initial page load) | Still fails; same empty `PROTOCOL_STEPS` | real-bug | (a) sequence_runner playback unimplemented | Same fix as above |
| `sdspage_full` | `waitForExports` (initial page load) | Still fails; same empty `PROTOCOL_STEPS` | real-bug | (a) sequence_runner playback unimplemented | Same fix as above |
| `sdspage_load_samples_batch` | `waitForExports` (initial page load) | Still fails; same empty `PROTOCOL_STEPS` | real-bug | (a) sequence_runner playback unimplemented | Same fix as above |
| `sdspage_prepare_sample_mix_batch` | `waitForExports` (initial page load) | Still fails; same empty `PROTOCOL_STEPS` | real-bug | (a) sequence_runner playback unimplemented | Same fix as above |
| `sdspage_extract_gel_from_cassette` | `waitForExports` (initial page load); `window.gameState` never defined at all | Still fails; app throws before mounting | real-bug | (c) avoidable scene-layout defect (label/SVG overlap guard) | Fix the `staining_bench` scene: the `front_center_staining_tray` label overlaps its own SVG by 52.9% |

Recommended walker budget: no change. The documented budgets (per-click
3000ms, per-step 30000ms, whole-run 600000ms) are not the problem here and
should not be raised to "fix" this set. See "Do not raise the budget" below.

## Methodology

1. `npm run build` produced a fresh `dist/`.
2. Read the current walker budgets in `tests/playwright/e2e/protocol_walkthrough_yaml.mjs`
   (`RUN_BUDGET_MS = 600000`, `STEP_BUDGET_MS = 30000`, `CLICK_BUDGET_MS = 3000`)
   and `tests/playwright/e2e/walker_helpers.mjs` (`waitForExports(page, timeoutMs = 8000)`).
3. Read the existing same-day sweep reports already present under
   `test-results/walker/reports/<id>.json` for all 6 protocols; every one
   crashes at the identical stack frame:
   `waitForExports (tests/playwright/e2e/walker_helpers.mjs:75)` called from
   `main (tests/playwright/e2e/protocol_walkthrough_yaml.mjs:401)` -- this is
   the FIRST `waitForExports` call, immediately after the initial
   `page.goto()`, before `localStorage.clear()`, before reload, before any
   step is walked and before any scene transition happens. The "scene
   transitions" framing in the sweep summary describes what these protocols
   are (multi-scene sequence runners), not where the failure occurs.
4. A throwaway diagnostic script (`tests/playwright/_temp_diagnose_six.mjs`,
   deleted after use, port 8127 so it never collided with the real walker's
   port 8126 or `test-results/walker/` artifacts) loaded each of the 6
   protocol pages directly, captured console/page errors, and polled
   `window.gameState` / `window.PROTOCOL_STEPS` with a 90000ms budget (3x the
   step budget) instead of the walker's 8000ms/30000ms. All 6 still never
   became ready inside 90 seconds, and the page's own `pageerror` /
   `console.error` events showed each one throws synchronously during
   `protocol_host_entry`, well under 1 second after `networkidle`. This
   confirms budget size is irrelevant: the app never reaches a ready state at
   any budget, so this is not "works but slow."

## Root cause 1 (5 protocols): sequence_runner playback is not implemented

`cell_culture_full`, `routine_passage`, `sdspage_full`,
`sdspage_load_samples_batch`, and `sdspage_prepare_sample_mix_batch` are all
`protocol_type: sequence_runner`. Per `docs/PRIMARY_SPEC.md`, a sequence
runner "carries no `steps` list" and instead lists constituent
`mini_protocols`. `pipeline/gen_protocols.py`'s `emit_protocols_ts` emits the
raw YAML for a sequence runner verbatim into `generated/protocols.ts`, so the
generated `ProtocolConfig` for each of these 5 has `mini_protocols` but no
`steps` field at all (confirmed directly in `generated/protocols.ts`).

`src/protocol_host.tsx`'s `mount()` reads `const config = PROTOCOLS[protocol_name]`
and sets `const active_config = config` exactly once; there is no code path
that re-resolves to the next constituent mini-protocol's own `ProtocolConfig`
and rebuilds the step machine when one mini-protocol finishes. `create_step_machine`
(`src/scene_runtime/protocol/step_machine.ts:567-570`) builds its step lookup
from `config.steps ?? []`, which is an empty array for a sequence runner, so
`steps_by_name` is empty. When `step_machine.start()` calls `enter_step(entry_step)`,
it throws immediately:

```text
Unknown step_name in protocol: inspect_confluence
    at h (protocol_host.js:...)
    at Object.V [as start] (protocol_host.js:...)
```

(`step_machine.ts:615-619`, the literal throw site is
`throw new Error(\`Unknown step_name in protocol: ${step_name}\`);`).
This happens before `window.PROTOCOL_STEPS` is ever populated past length 0,
so the walker's `waitForExports` predicate (`window.PROTOCOL_STEPS.length > 0`)
can never resolve, no matter how long it waits.

Confirmed the mini-protocols themselves are fine in isolation: the existing
report for `passage_hood_detachment` (the first constituent of both
`cell_culture_full` and `routine_passage`) shows the walker surfaces ready in
under 1 second and 9 steps loaded when walked as its own standalone
`mini_protocol` page. The defect is specific to the sequence-runner assembly
path, not to any individual mini-protocol's YAML.

This is category (a): a genuine, always-reproducing, never-completing
transition. It is not a slow scene transition; it is a missing runtime
feature (mini-protocol-to-mini-protocol chaining and step-machine
rebuild/rebind on completion of each constituent mini-protocol). This is
exactly the class of gap M16 should scope and fix -- in
`src/protocol_host.tsx` and/or `src/scene_runtime/protocol/step_machine.ts`,
not in the walker.

## Root cause 2 (1 protocol): scene structural guard failure

`sdspage_extract_gel_from_cassette` is a `mini_protocol`, not a sequence
runner (this is the one protocol in the set of 6 that does not match the
"sequence-runners with scene transitions" framing in the sweep summary). Its
step chain includes a `SceneChange` to the shared `staining_bench` scene. On
mount, the renderer's structural guard throws before `window.gameState` is
even defined (confirmed `hasGameState: false` in the diagnostic run, unlike
the other 5 where `gameState` exists but `PROTOCOL_STEPS` stays empty):

```text
Structural guard failure (label-svg overlap): label for item
"front_center_staining_tray" overlaps its own SVG by 52.9%.
```

This is category (c): an avoidable scene-layout defect, not an inherently
slow step and not a missing feature. The fix is in the `staining_bench` base
scene (or its per-protocol placement of `staining_tray`) so the
`front_center_staining_tray` label no longer overlaps its own SVG past the
guard's threshold. This is unrelated to sequence-runner chaining and
unrelated to walker timing.

## Do not raise the budget

Raising `STEP_BUDGET_MS`, `RUN_BUDGET_MS`, or `waitForExports`'s timeout
would only make the sweep slower to report the same 6 failures; it fixes
nothing, because none of the 6 ever reach a ready state. No budget change is
recommended.

## A separate, smaller walker defect found along the way (not one of the 6)

While tracing the exact timeout value, a real defect was found in
`waitForExports` itself (`tests/playwright/e2e/walker_helpers.mjs:74-86`):

```js
export async function waitForExports(page, timeoutMs = 8000) {
  await page.waitForFunction(
    () => { /* zero-parameter predicate */ },
    { timeout: timeoutMs },
  );
}
```

Playwright's `page.waitForFunction(pageFunction, arg, options)` signature
binds the second positional argument to `arg` (passed into the page
function), not to `options`, whenever `pageFunction` takes zero declared
parameters and only two total arguments are supplied. A minimal repro
(`page.waitForFunction(() => window.x !== undefined, { timeout: 2000 })`)
measured an actual elapsed time of ~30002ms and the literal message
`Timeout 30000ms exceeded`, not `Timeout 2000ms exceeded`; the `{ timeout }`
object was silently ignored and Playwright's global default action timeout
(30000ms) was used instead. This is why every one of the 6 existing sweep
reports says "30000ms" rather than the intended 8000ms for the very first
`waitForExports` call -- the walker's own two-argument call shape at line 75
is wrong for a zero-parameter predicate.

This did not change the verdict for any of the 6 protocols above (they all
fail well under 1 second into their own load, and re-testing with a 90000ms
budget in a separate diagnostic still failed all 6), so it is out of scope
for this triage's real-bug/budget classification. It is worth a follow-up
one-line fix in `walker_helpers.mjs` (pass `undefined` as the `arg`
parameter before the `{ timeout: timeoutMs }` options object) purely so
future failure messages report the walker's actually-intended budget instead
of Playwright's silent 30000ms fallback. That fix is not included here per
this task's boundary (read-mostly triage; no walker code changes committed).

## Files referenced

- `tests/playwright/e2e/walk_all_protocols.mjs`
- `tests/playwright/e2e/protocol_walkthrough_yaml.mjs`
- `tests/playwright/e2e/walker_helpers.mjs`
- `test-results/walker/reports/cell_culture_full.json`
- `test-results/walker/reports/routine_passage.json`
- `test-results/walker/reports/sdspage_full.json`
- `test-results/walker/reports/sdspage_load_samples_batch.json`
- `test-results/walker/reports/sdspage_prepare_sample_mix_batch.json`
- `test-results/walker/reports/sdspage_extract_gel_from_cassette.json`
- `test-results/walker/reports/passage_hood_detachment.json`
- `content/protocols/runners/cell_culture_full/protocol.yaml`
- `content/protocols/runners/routine_passage/protocol.yaml`
- `content/protocols/runners/sdspage_full/protocol.yaml`
- `content/protocols/runners/sdspage_load_samples_batch/protocol.yaml`
- `content/protocols/runners/sdspage_prepare_sample_mix_batch/protocol.yaml`
- `content/protocols/sdspage/sdspage_extract_gel_from_cassette/protocol.yaml`
- `content/protocols/cell_culture/passage_hood_detachment/protocol.yaml`
- `pipeline/gen_protocols.py`
- `src/protocol_host.tsx`
- `src/scene_runtime/protocol/step_machine.ts`
- `generated/protocols.ts`

## Blocker encountered

Phase 1 asked to invoke the `/repo-rules-reader` skill via the Skill tool.
No Skill tool was available in this session's tool set (Bash, Read, Write,
SendMessage only), so it could not be invoked. This report instead relies on
the repo style docs already loaded into context (`AGENTS.md`,
`docs/REPO_STYLE.md`, `docs/PYTHON_STYLE.md`, `docs/E2E_TESTS.md`,
`docs/MARKDOWN_STYLE.md`, `docs/PRIMARY_CONTRACT.md`, `docs/PRIMARY_DESIGN.md`,
`docs/PRIMARY_SPEC.md`, `docs/TYPESCRIPT_STYLE.md`, `docs/PLAYWRIGHT_USAGE.md`,
`docs/specs/WALKTHROUGH_GUIDE.md`).
