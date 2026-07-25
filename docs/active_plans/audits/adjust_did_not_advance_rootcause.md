# adjust_did_not_advance root cause

Read-only investigation for the `adjust_did_not_advance` cluster from
[walk_all_fail_triage.md](walk_all_fail_triage.md) (2 protocols, previously "no
confirmed shared root cause"). Zero protocol, source, or scene file was changed
to produce this report. Determination: **one shared root cause**, confirmed by
reproduction against the current tree.

## The 2 protocols and failing interactions

| Protocol | Failing step | Failing interaction | Committed value |
| --- | --- | --- | --- |
| `plate_drug_treatment_media_adjustment` | `adjust_media_quadrant_a1_h6` | interaction index 1: `adjust` on `multichannel_pipette`, `set_volume: 100` | `100` |
| `sdspage_prepare_sample_mix_single_lane` | `add_laemmli_buffer` | interaction index 0 (first interaction of the step): `adjust` on `micropipette`, `set_volume: 7.5` | `7.5` |

## Root cause

**The `adjust` gesture is not the cause.** The crash is triggered by the
interaction that immediately FOLLOWS the committed one, and it is gesture-
agnostic; it happens to land on an `adjust` boundary in both of today's cases
only because of where these two protocols place their `adjust` interactions
in their sequences.

Mechanism, traced through `src/scene_runtime/protocol/step_machine.ts` and
`src/scene_runtime/protocol/target_adapter.ts`:

1. A validated interaction commits (`handle_adjust_commit` here, but the same
   code path runs for `handle_click`, `handle_type_commit`, etc.).
   `handle_validated()` first calls `emitter.emit(interaction_validated)`.
2. The emitter's snapshot reducer (`create_snapshot_reducer`'s
   `interaction_validated` case in `step_machine.ts`) computes the NEXT active
   interaction (`interaction_index + 1`) and resolves ITS authored `target` to
   a DOM `placement_name` via `resolve_target_to_placement`, which delegates
   to the scene's live `target_adapter.resolve_to_placement`.
3. `build_target_adapter`'s `resolve_to_placement` (`target_adapter.ts:123`)
   throws `AmbiguousTargetError` **lazily, at resolve time** (not at adapter
   construction) whenever the target's `object_name` is placed more than once
   in the currently mounted scene with no placement-level disambiguation.
4. This throw happens INSIDE step 1's `emitter.emit(...)` call, which runs
   BEFORE `handle_validated` applies the response's `scene_operations` and
   BEFORE `interaction_index += 1`. The exception propagates up through
   `handle_adjust_commit` (no try/catch anywhere on this path) and out through
   the Solid `onClick` handler in `set_point_editor.tsx`'s `commit()`,
   surfacing as an **uncaught page exception** (`page.on("pageerror")`), not
   as an `interaction_rejected` event.
5. Because the throw pre-empts the state mutation, `interactionIndex`,
   `activeStepId`, `activeScene`, `completedSteps`, and `isComplete` are all
   frozen at their pre-commit values. The walker's `adjustCommitAndWaitProgress`
   (`tests/playwright/e2e/walker_helpers.mjs`) watches exactly those signals
   and times out at 3000 ms, producing the generic `adjust_did_not_advance`
   message with no diagnostic content -- the walker does not install a
   `page.on("pageerror")` listener, so the real exception is invisible in its
   own report today.

The `adjust`-specific hypotheses from `walk_all_fail_triage.md` ("adjust right
after a same-step SceneChange" and "adjust as first-interaction-with-no-
preceding-click") were both red herrings: they examined properties of the
FAILING interaction. The actual trigger is a property of the interaction that
comes NEXT in the authored `sequence`, which is why the same two protocols'
OTHER, structurally-similar `adjust` interactions succeed -- their own next
interaction happens to target an unambiguously-placed object.

## Confirmed evidence (reproduced against current tree)

Built with `npm run build`, then drove each protocol through the real visible
UI with Playwright (fill `[data-adjust-input]`, click `[data-adjust-commit]`),
capturing `window.gameState` and `page.on("pageerror")` around the commit.

**`plate_drug_treatment_media_adjustment`** -- committing `100` on
`multichannel_pipette` (interaction index 1) fires, in the page console:

```text
Ambiguous protocol target "media_bottle": it names an object placed 2 times
(placements: base_rear_right_media, rear_center_media). Name one placement_name
to disambiguate; the object_name cannot be a DOM key.
```

`interactionIndex` stays at `1` (never becomes `2`) after the exception.
Interaction index 2 in the step's authored `sequence` is exactly
`target: media_bottle, gesture: click` -- the interaction the reducer was
computing when it threw.

Source of the duplicate placement:
[plate_workspace.yaml](../../../content/protocols/cell_culture/plate_drug_treatment_media_adjustment/scenes/plate_workspace.yaml).
This scene `extends: hood_basic` (which already places `media_bottle`, the
`base_rear_right_media` placement) and its own `add_placements` adds a SECOND
`media_bottle` placement (`rear_center_media`) without a matching
`remove_placements` entry for the inherited one. `remove_placements` in this
file already removes 4 other inherited placements
(`base_right_serological_pipette`, `right_aspirating_pipette`,
`base_rear_center_pbs`, `rear_center_waste`) -- the inherited media bottle was
simply missed.

**`sdspage_prepare_sample_mix_single_lane`** -- committing `7.5` on
`micropipette` (step `add_laemmli_buffer`, interaction index 0, the step's
FIRST interaction) fires:

```text
Ambiguous protocol target "laemmli_4x_bottle": it names an object placed 2
times (placements: center_laemmli_working, rear_center_laemmli). Name one
placement_name to disambiguate; the object_name cannot be a DOM key.
```

`interactionIndex` stays at `0` after the exception. Interaction index 1 in
`add_laemmli_buffer`'s authored `sequence` is exactly
`target: laemmli_4x_bottle, gesture: click`.

The step immediately BEFORE this one (`add_protein_sample`) commits a
DIFFERENT `adjust` (`set_volume: 21` on the same `micropipette`, right after a
same-step `SceneChange`) and SUCCEEDS -- confirmed by the same reproduction
script -- because its own next interaction targets `protein_sample_tube`,
which is placed once and resolves cleanly. This is the "adjacent successful
adjust" the earlier triage could not reconcile; it now has a clean
explanation.

Source of the duplicate placement:
[sample_prep_bench.yaml](../../../content/base_scenes/sample_prep_bench.yaml).
The BASE scene itself places `laemmli_4x_bottle` twice
(`rear_center_laemmli` at line 99-100, `center_laemmli_working` at line
147-148); the protocol's override scene
([sample_prep_bench_override.yaml](../../../content/protocols/sdspage/sdspage_prepare_sample_mix_single_lane/scenes/sample_prep_bench_override.yaml))
removes an unrelated placement (`mid_microtube_sample`) but never removes
either `laemmli_4x_bottle` duplicate. Note `sample_prep_bench.yaml` also
double-places `microtube_rack_24` (`mid_eppendorf_rack` and
`center_microtube_rack`); no current protocol's authored `sequence` happens to
target `microtube_rack_24` by its bare object name, so that second ambiguity
is currently latent and silent (see Owner note below on why this matters).

## Why this was not caught earlier

`build_target_adapter` never validates uniqueness eagerly; `resolve_to_placement`
throws only when a caller actually asks to resolve that specific ambiguous
`object_name`. So a scene can carry a duplicate placement indefinitely with
zero symptoms until some protocol's authored `sequence` happens to name that
`object_name` as a `target`. M15's certified register's claim that
`AmbiguousTargetError` is "confirmed retired" (no FAIL message contains the
string "Ambiguous") only scanned the WALKER's OWN error/reason strings; it did
not scan the page's console/`pageerror` stream, where these two live
instances have been surfacing invisibly the whole time. The class is not
retired -- it is latent and gesture-blind, and it currently masquerades as
whatever gesture happens to precede the ambiguous target in sequence order
(`adjust_did_not_advance` here; it would read `click_did_not_advance` if a
plain click preceded the same ambiguous target instead).

## Owner classification

**M16-protocol** (content/scene YAML fix) for both concrete failures:

- `plate_drug_treatment_media_adjustment`: add `base_rear_right_media` (or
  whatever the inherited `hood_basic` media_bottle placement_name is) to
  `plate_workspace.yaml`'s existing `remove_placements` list, alongside the 4
  entries already there.
- `sdspage_prepare_sample_mix_single_lane`: add one of
  `rear_center_laemmli` / `center_laemmli_working` to
  `sample_prep_bench_override.yaml`'s `remove_placements` list (keep whichever
  placement the protocol's zone layout intends the student to see).

**M16-runtime / overlaps with the pending M16-D task** for the systemic gap:
task #34 "M16-D Load-time target-existence invariant" is the right home to
close this class permanently. It should walk every authored `target` across
every interaction of every reachable step against every scene that step can
render in, and call `resolve_to_placement` once at PROTOCOL LOAD TIME (mirroring
the existing load-time `validate_gesture_affordances` /
`validate_authored_validator_values` passes in `step_machine.ts`), so an
ambiguous placement fails loud before a browser session starts instead of
silently freezing progress mid-walk. Secondary, smaller fix in the same family:
the walker (`tests/playwright/e2e/protocol_walkthrough_yaml.mjs`) does not
install a `page.on("pageerror")` listener, so any future uncaught page
exception -- ambiguous-target or otherwise -- will keep surfacing only as a
content-free `..._did_not_advance` timeout instead of the real error text.

Not scene-manager-external: unlike `passage_hood_detachment` (which needs a
placement ADDITION reflecting new scene geometry), this fix is a placement
REMOVAL that de-duplicates an existing object, the same class of edit already
accepted as M16-protocol scope for the `target_missing` cluster's
`content/protocols/**` and `content/base_scenes/**` fixes.

## Fix direction (not applied)

1. Add the missing `remove_placements` entry in each of the two scene YAML
   files named above.
2. Rebuild (`npm run build`) and re-run
   `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <name>`
   for both protocols to confirm the `adjust` commit now advances past the
   previously-ambiguous target.
3. Hand the load-time invariant + walker `pageerror` capture to M16-D (already
   in progress) rather than opening a new task.

## Methodology

1. Read [walker_click_bug_register.md](walker_click_bug_register.md) and
   [walk_all_fail_triage.md](walk_all_fail_triage.md) to identify the 2 exact
   protocols and failing steps.
2. `npm run build`, then reproduced both FAILs with
   `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol <name>`
   (unmodified walker, no fixes applied).
3. Wrote three scratch Playwright scripts (`tests/playwright/_diag_*.mjs`,
   deleted after use, never staged) that load each protocol's page, drive the
   real visible `[data-adjust-input]` / `[data-adjust-commit]` affordance
   exactly as the walker does, and additionally install `page.on("pageerror")`
   to capture what the walker's own report does not.
4. Cross-referenced the exact object names named in the captured
   `AmbiguousTargetError` messages against each protocol's authored
   `protocol.yaml` `sequence` (confirming the object is the NEXT interaction's
   target) and against the relevant scene YAML's `placements` /
   `add_placements` / `remove_placements` (confirming the duplicate placement
   and the missing removal).
5. Read `src/scene_runtime/protocol/step_machine.ts` and
   `src/scene_runtime/protocol/target_adapter.ts` to confirm the throw site,
   its lazy (resolve-time, not build-time) trigger, and its position relative
   to `interaction_index` mutation inside `handle_validated`.
6. No protocol, scene, or source file was modified. No task's owned files
   (`step_machine.ts`, `set_point_editor.tsx`) were edited.

## Files referenced

- [walker_click_bug_register.md](walker_click_bug_register.md)
- [walk_all_fail_triage.md](walk_all_fail_triage.md)
- `src/scene_runtime/protocol/step_machine.ts`
- `src/scene_runtime/protocol/target_adapter.ts`
- `src/shell/hud/set_point_editor.tsx`
- `tests/playwright/e2e/walker_helpers.mjs`
- `tests/playwright/e2e/protocol_walkthrough_yaml.mjs`
- `content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml`
- `content/protocols/cell_culture/plate_drug_treatment_media_adjustment/scenes/plate_workspace.yaml`
- `content/base_scenes/hood_basic.yaml`
- `content/protocols/sdspage/sdspage_prepare_sample_mix_single_lane/protocol.yaml`
- `content/protocols/sdspage/sdspage_prepare_sample_mix_single_lane/scenes/sample_prep_bench_override.yaml`
- `content/base_scenes/sample_prep_bench.yaml`
