# Full walker sweep regression matrix

Post-fix closeout sweep, run after: trypan gate 90 -> 92.5, mtt same-step
`SceneChange` re-resolution, orphan validator, `all_wells` group-write +
subpart-suffix load validation, the two InvariantB load invariants.

Build: `./build_github_pages.sh` (fresh `dist/` + `generated/`, clean run,
39/39 scenes rendered).

Sweep: `node tests/playwright/e2e/walk_all_protocols.mjs`, 31 protocols
discovered under `content/protocols/`. Raw sweep summary:
`test-results/walker/sweep_summary.json`. Per-protocol reports archived at
`test-results/walker/reports/<id>.json`.

## Verdict

**1 unexpected regression found.** 4 of the 5 reds are the owned/held reds
named in the task brief. `passage_hood_detachment` is a new, unexpected FAIL
not in the expected list -- flagged loud below.

## Result matrix

| Protocol | Verdict | Failing step / cause |
| --- | --- | --- |
| cell_culture_full | FAIL-at-LOAD (expected, owned) | `UnseededSceneOpTargetError` for target `conical_15ml` |
| passage_pellet_reseed | FAIL-at-LOAD (expected, owned) | `UnseededSceneOpTargetError` for target `conical_15ml` |
| routine_passage | FAIL-at-LOAD (expected, owned) | `UnseededSceneOpTargetError` for target `conical_15ml` |
| plate_drug_treatment_drug_addition | FAIL-mid-walk (expected, held) | subpart target not in DOM |
| **passage_hood_detachment** | **FAIL-mid-walk (UNEXPECTED)** | **click intercepted by overlapping element** |
| cell_seeding_plate_setup | PASS | - |
| drug_dilution_setup | PASS | - |
| mtt_plate_reaction | PASS | - |
| mtt_reagent_prep | PASS | - |
| mtt_solubilization_readout | PASS | - |
| plate_drug_treatment_media_adjustment | PASS | - |
| sdspage_assemble_electrode_module | PASS | - |
| sdspage_attach_lid_and_leads | PASS | - |
| sdspage_destain_gel_rock | PASS | - |
| sdspage_destain_gel_setup | PASS | - |
| sdspage_extract_gel_from_cassette | PASS | - |
| sdspage_fill_tank_buffer | PASS | - |
| sdspage_full | PASS | - |
| sdspage_heat_denature_samples | PASS | - |
| sdspage_image_gel | PASS | - |
| sdspage_load_protein_ladder | PASS | - |
| sdspage_load_sample_single_lane | PASS | - |
| sdspage_load_samples_batch | PASS | - |
| sdspage_prepare_gel_cassette | PASS | - |
| sdspage_prepare_running_buffer | PASS | - |
| sdspage_prepare_sample_mix_batch | PASS | - |
| sdspage_prepare_sample_mix_single_lane | PASS | - |
| sdspage_recycle_buffer | PASS | - |
| sdspage_run_electrophoresis | PASS | - |
| sdspage_stain_gel | PASS | - |
| trypan_blue_counting | PASS | - |

Totals: PASS=26, FAIL=5, of 31.

## Confirmed owned/held reds (matches brief exactly)

Console capture (`page.on("console")` / `page.on("pageerror")`) against each
built `dist/<id>.html` confirms the load-time cause text for all three
`conical_15ml` reds:

```
UnseededSceneOpTargetError: Scene operation target is not seeded in the
active scene in protocol "cell_culture_full", step "mp1__transfer_to_conical",
scene "hood_workspace", scene_operation "ObjectStateChange" at interaction
index 1, target "conical_15ml". No placement_name or object_name in that
scene matches it.
```

Same error, same target `conical_15ml`, same scene `hood_workspace`, for
`passage_pellet_reseed` (step `transfer_to_conical`) and `routine_passage`
(step `mp1__transfer_to_conical`, the sequence-runner flattening
`passage_pellet_reseed`'s mini-protocol). All three throw at protocol load,
before `window.gameState` / `window.PROTOCOL_STEPS` are exported, which is
why the sweep runner's `waitForExports` call times out at 8s rather than
reporting the `UnseededSceneOpTargetError` text directly -- confirmed by
capturing the browser console independently. This matches the brief:
`passage_pellet_reseed` FAILs at LOAD naming `conical_15ml`, owned O1,
scene-manager; the two sequence runners that flatten it fail for the same
reason.

`plate_drug_treatment_drug_addition` FAILs mid-walk at step
`add_carb_row_b`, after clicking `right_micropipette` and committing the
adjust set-point (`5`), on:

```
Step failed: add_carb_row_b - Element
#scene-root [data-item-id="rear_center_carb_stocks.tube_A"] does not exist
in DOM
```

This is the tube-rack subpart click target not resolving in the DOM, the
pedagogy-held OP1 issue named in the brief (architect Direction-B RFC). No
console errors accompany this one -- the page loads fine, the failure is the
walker's next click target being absent from the rendered scene.

## Unexpected regression: passage_hood_detachment

`passage_hood_detachment` was PASSing before this round of fixes and is not
named in the brief's expected-reds list. It now FAILs mid-walk at its first
step, `inspect_confluence`, after successfully clicking `main_microscope`.
The walker's next click target is `rear_right_hood_return`
(`data-object-name="hood_surface"`, zone `rear_right`), and Playwright times
out after 30s because a different element intercepts the pointer event:

```
Step failed: inspect_confluence - locator.click: Timeout 30000ms exceeded.
  - waiting for locator('#scene-root [data-item-id="rear_right_hood_return"]').first()
    - locator resolved to <div data-kind="equipment" data-zone="rear_right"
      data-affordance="active" data-object-name="hood_surface"
      data-asset="hood_workspace_surface"
      data-item-id="rear_right_hood_return" ...>
  - attempting click action
    - <path ... fill="#ebebeb" ...> from <div data-asset="bottle"
      data-kind="equipment" data-affordance="none" data-zone="right_bench"
      data-object-name="hemocytometer_slide"
      data-item-id="right_hemocytometer_slide_clear" ...>
      subtree intercepts pointer events
```

A `right_hemocytometer_slide_clear` bottle (`data-affordance="none"`, zone
`right_bench`) sits visually on top of the `rear_right_hood_return` hood
surface target and swallows the click for 30s of retries. Console capture on
this protocol's page shows zero console/page errors -- the page loads and
runs cleanly; this is a layout/z-order overlap between two placed scene
objects in the `passage_hood_detachment_hood_workspace` scene, not a
protocol-load or validator error. No screenshot artifact exists for this run
(`--screenshots per-step`, the sweep runner's default, only saves images in
`per-interaction`/`per-click` mode); the report text above is the walker's
full evidence and reproduces via `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs
--protocol passage_hood_detachment`.

Full report: `test-results/walker/reports/passage_hood_detachment.json`.

Per the earlier scene-health build output, this scene
(`passage_hood_detachment_hood_workspace`) is flagged `near-empty,degraded`
with a `41.136-131.801`/`201.6-268.5` bbox overlap between the two objects
-- consistent with a layout placement collision, not a one-off flake.

This is triage-only; no fix attempted per the brief. Recommend routing to
whichever workstream owns `hood_workspace`-family scene layout (the same
class of issue as the owned/held items above, but newly introduced or newly
exposed by this round's changes and not previously catalogued).
