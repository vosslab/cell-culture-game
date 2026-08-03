# M4-D defect register

**Date:** 2026-06-02
**Plan:** refactored-drifting-narwhal, milestone M4, workstream WS-M4-D
**Scope:** classify every sweep failure from M4-B (31 protocols) and M4-C (37 scenes)

Evidence base:
- `docs/active_plans/audits/m4b_corpus_sweep_results.md` (protocol sweep)
- `docs/active_plans/audits/ws_m4c_scene_corpus_sweep.md` (scene sweep)
- `test-results/corpus_sweep/corpus_results_table.json`
- `test-results/scenes/summary.json`
- `assets/SVG_ASSET_GAPS.md`

Post-sweep context: WS-M5-ST implemented `select` and `type` gestures.
Remaining unsupported gestures: `adjust` and `drag` only.

---

## Part A: per-failure classification table (31 protocols)

### Completed (7) - no defect

| Protocol | Steps passed | Notes |
| --- | --- | --- |
| sdspage_assemble_electrode_module | 4/4 | Click-only path; completes cleanly |
| sdspage_attach_lid_and_leads | 1/1 | Click-only path; completes cleanly |
| sdspage_extract_gel_from_cassette | 5/5 | Click-only path; completes cleanly |
| sdspage_heat_denature_samples | 4/4 | Click-only path; completes cleanly |
| sdspage_prepare_gel_cassette | 4/4 | Click-only path; completes cleanly |
| sdspage_recycle_buffer | 3/3 | Click-only path; completes cleanly |
| sdspage_stain_gel | 5/5 | Click-only path; completes cleanly |

### Unsupported gesture - adjust (14)

Bucket: **unsupported_gesture**
Owner: renderer / runtime team (adjust-affordance milestone)
Mechanism: walker error "gesture 'adjust' on target X has no visible affordance in the new host yet"
Highest-leverage fix: implement one adjust affordance in the runtime; unblocks all 14 protocols at once.

| Protocol | Failing step | Failing target | Gesture | Evidence (corpus_results_table.json line) |
| --- | --- | --- | --- | --- |
| cell_seeding_plate_setup | calculate_dilution_volume | serological_pipette | adjust | detail field row 2 |
| drug_dilution_setup | prepare_carb_parent_stock | micropipette | adjust | detail field row 3 |
| mtt_reagent_prep | prepare_solution_tube | micropipette | adjust | detail field row 5 |
| mtt_solubilization_readout | add_dmso_to_wells | micropipette | adjust | detail field row 6 |
| plate_drug_treatment_drug_addition | add_carb_row_b | micropipette | adjust | detail field row 9 |
| plate_drug_treatment_media_adjustment | adjust_media_quadrant_a1_h6 | multichannel_pipette | adjust | detail field row 10 |
| sdspage_destain_gel_rock | rock_run | rocking_shaker | adjust | detail field row 14 |
| sdspage_fill_tank_buffer | fill_inner_chamber | serological_pipette | adjust | detail field row 17 |
| sdspage_load_protein_ladder | set_micropipette_volume | p200_micropipette | adjust | detail field row 21 |
| sdspage_load_sample_single_lane | draw_sample | p200_micropipette | adjust | detail field row 22 |
| sdspage_prepare_running_buffer | dilute_10x_concentrate | serological_pipette | adjust | detail field row 25 |
| sdspage_prepare_sample_mix_single_lane | add_protein_sample | micropipette | adjust | detail field row 27 |
| sdspage_run_electrophoresis | set_voltage | power_supply | adjust | detail field row 29 |
| trypan_blue_counting | add_trypan_blue_to_chamber | micropipette | adjust | detail field row 31 |

Classification rationale: the scene renders populated (render_outcome = "populated"),
the objects are present in the DOM, and earlier steps pass where applicable
(mtt_reagent_prep: 1 step passed before hitting adjust; sdspage_load_protein_ladder: 3 steps
passed; sdspage_load_sample_single_lane: 1 step passed). The failure is purely a missing
runtime affordance for the `adjust` gesture, not a renderer defect or content error.

### Render failure - sequence_runner page-load timeout (5)

Bucket: **tooling / runtime**
Owner: runtime team (sequence_runner step-resolution bug)
Mechanism: "Unknown step_name in protocol" - the sequence runner's entry step resolver
tries to find its entry_step in the runner's own steps list, but runners carry constituent
mini-protocol references, not an authored steps list. Result: page.waitForFunction timeout
at 30000ms; 0 steps walked.
Highest-leverage fix: fix sequence_runner entry-step resolution in the runtime so it
delegates to the first mini-protocol's entry_step; unblocks all 5 runners at once.

| Protocol | protocol_type | Render outcome | Error |
| --- | --- | --- | --- |
| cell_culture_full | sequence_runner | page-load-failure | Timeout 30000ms exceeded |
| routine_passage | sequence_runner | page-load-failure | Timeout 30000ms exceeded |
| sdspage_full | sequence_runner | page-load-failure | Timeout 30000ms exceeded |
| sdspage_load_samples_batch | sequence_runner | page-load-failure | Timeout 30000ms exceeded |
| sdspage_prepare_sample_mix_batch | sequence_runner | page-load-failure | Timeout 30000ms exceeded |

Classification rationale: all sequence_runner protocols fail with the same timeout;
no mini_protocol fails with a page-load timeout. This is a systematic runtime defect
in sequence_runner entry-step resolution, not a content error and not a renderer
regression (the Solid renderer itself loads and passes the DOM contract on mini-protocols).

### Missing object (4)

Bucket: **missing_asset** (scene placement gap - the object is declared in the protocol
but absent from the scene's YAML, or its SVG is quarantined)

Owner: content / scene-authoring team

| Protocol | Failing step | Missing target | Failing DOM selector | Notes |
| --- | --- | --- | --- | --- |
| mtt_plate_reaction | gather_mtt_materials | well_plate_96 | `#scene-root [data-item-id="well_plate_96"]` | well_plate_96 is quarantined per assets/SVG_ASSET_GAPS.md ("quarantined until overlay rendering lands") |
| passage_hood_detachment | inspect_confluence | hood_surface | `#scene-root [data-item-id="hood_surface"]` | hood_surface not placed in relevant scene YAML |
| sdspage_destain_gel_setup | place_kimwipes | kimwipe_pad | `#scene-root [data-item-id="kimwipe_pad"]` | kimwipe_pad is a placeholder object (no source art); scene may not include it |
| sdspage_image_gel | final_rinse | waste_container | `#scene-root [data-item-id="waste_container"]` | waste_container not placed in imaging_bench scene YAML |

Sub-classification notes:
- `well_plate_96`: this is a deliberate quarantine (assets/SVG_ASSET_GAPS.md line 67-70).
  The object exists in the object library but overlay rendering is deferred. Bucket:
  **deferred_content** (not a renderer defect; the quarantine is intentional).
- `kimwipe_pad`: listed in assets/SVG_ASSET_GAPS.md as a placeholder object with no
  source art. The scene may intentionally omit it until art is sourced. Bucket:
  **missing_asset** (art gap + scene placement gap combined).
- `hood_surface` and `waste_container`: no entry in SVG_ASSET_GAPS.md; likely scene
  placement omissions. Bucket: **content_defect** (scene YAML missing a placement entry).

### Other - passage_pellet_reseed (1)

Bucket: **content_defect** (protocol YAML defect - step has no active interaction)
Owner: content / protocol-authoring team

| Protocol | Failing step | Detail | Evidence |
| --- | --- | --- | --- |
| passage_pellet_reseed | transfer_to_conical | "step transfer_to_conical has no active target/gesture but is still active" | corpus_results_table.json row 8 |

Classification rationale: the page loads and renders ("populated"), but the step
`transfer_to_conical` has no `sequence` interaction that the runtime can dispatch.
This is a protocol YAML authoring gap: the step is defined but either has an empty
`sequence` or a target/gesture combination the runtime cannot resolve. Not a renderer
defect; not an unsupported gesture (no gesture name is surfaced). The step must be
authored correctly in the protocol YAML.

---

## Part B: renderer-class blockers for WS-M4-E

**Renderer-class blockers: NONE.**

Rationale:
- The M4-C scene sweep ran the DOM contract diff across 36 baselined scenes and
  found 0 failures and 0 contract_drift (ws_m4c_scene_corpus_sweep.md: "total: 36,
  passed: 36, failed: 0, PASS: scene DOM contract diff check").
- All 7 click-only mini-protocols completed end-to-end with no console errors.
- Every page-load failure is attributable to the sequence_runner entry-step resolution
  bug, not to a Solid renderer regression.
- Placeholder items across 10 scenes were captured in the M1 baseline and are
  explicitly not regressions (ws_m4c_scene_corpus_sweep.md notes section).
- No DOM-contract regression was detected in any swept scene.

WS-M4-E may proceed. The gate is clear.

---

## Part C: owner-grouped follow-up queue

### Group 1: adjust affordance (unblocks 14 protocols)

Owner: renderer / runtime team
Milestone: adjust-affordance milestone (post-M4)
Highest-leverage single fix: implement the `adjust` gesture affordance in the runtime
(a visible set-point control widget that a student and the walker can interact with).
This single change unblocks 14 mini-protocols - the largest single improvement available.

Protocols unblocked: cell_seeding_plate_setup, drug_dilution_setup, mtt_reagent_prep,
mtt_solubilization_readout, plate_drug_treatment_drug_addition,
plate_drug_treatment_media_adjustment, sdspage_destain_gel_rock, sdspage_fill_tank_buffer,
sdspage_load_protein_ladder, sdspage_load_sample_single_lane, sdspage_prepare_running_buffer,
sdspage_prepare_sample_mix_single_lane, sdspage_run_electrophoresis, trypan_blue_counting.

Note: `sdspage_destain_gel_rock` targets `rocking_shaker` (a timed continuous gesture);
`sdspage_run_electrophoresis` targets `power_supply` (a voltage set-point). Both are
adjust gestures but may need slightly different affordance designs. Flag for review
during affordance design.

### Group 2: sequence_runner step-resolution bug (unblocks 5 protocols)

Owner: runtime team
Milestone: sequence_runner runtime fix (post-M4)
Highest-leverage single fix: fix entry-step resolution in the sequence_runner path so
the runtime delegates to the first constituent mini-protocol's entry_step rather than
looking up the entry_step in the runner's own (absent) steps list.
This single change unblocks all 5 sequence_runner protocols.

Protocols unblocked: cell_culture_full, routine_passage, sdspage_full,
sdspage_load_samples_batch, sdspage_prepare_sample_mix_batch.

Reference: m4b_corpus_sweep_results.md render failures section: "the sequence runner
references a step_name from a constituent mini-protocol that does not exist in the
runner's own steps list."

### Group 3: missing scene placements (2 protocols; content_defect)

Owner: content / scene-authoring team
Highest-leverage fix: add `hood_surface` to the `passage_hood_detachment_hood_workspace`
scene YAML and `waste_container` to the `imaging_bench` scene YAML. Two independent one-line
scene placement additions.

- `passage_hood_detachment`: add `hood_surface` placement to relevant scene.
  Evidence: `#scene-root [data-item-id="hood_surface"]` does not exist in DOM
  (corpus_results_table.json row 7); scene `passage_hood_detachment_hood_workspace`
  renders populated at 100% yield with 13 real items but hood_surface is absent.
- `sdspage_image_gel`: add `waste_container` placement to imaging_bench scene.
  Evidence: `#scene-root [data-item-id="waste_container"]` does not exist in DOM
  (corpus_results_table.json row 20).

### Group 4: well_plate_96 quarantine (1 protocol; deferred_content)

Owner: runtime team + content team (joint)
Milestone: well-plate overlay rendering (post-M4)
Condition: `mtt_plate_reaction` cannot pass until `well_plate_96` overlay rendering
lands in the Solid.js runtime. The quarantine is documented and intentional
(assets/SVG_ASSET_GAPS.md: "quarantined until overlay rendering lands in the Solid.js runtime").
No action required now. Track as deferred.

### Group 5: kimwipe_pad missing art + placement (1 protocol; missing_asset)

Owner: content team (art sourcing) + scene-authoring team (placement)
Condition: `sdspage_destain_gel_setup` fails at `place_kimwipes` because
`kimwipe_pad` is not in the DOM. Two gaps: (1) no source art (assets/SVG_ASSET_GAPS.md
lists kimwipe_pad as "Orange placeholder box"); (2) the scene may not place it even
as a placeholder. Protocol already passes 3 of 4 steps before hitting this target.
Fix path: add kimwipe_pad to the scene YAML (placeholder art renders); source real art
when available.

### Group 6: passage_pellet_reseed authoring gap (1 protocol; content_defect)

Owner: content / protocol-authoring team
Condition: step `transfer_to_conical` in `passage_pellet_reseed` has no active
interaction (empty or malformed sequence). The page loads, renders populated, but the
step has no target/gesture the runtime can dispatch.
Fix path: inspect `passage_pellet_reseed/protocol.yaml`, add a correct `sequence` for
`transfer_to_conical` with a valid target and gesture.

### Group 7: long_labels_smoke scene YAML error (scene; content_defect)

Owner: content / scene-authoring team
Condition: `long_labels_smoke` is skipped entirely because its YAML references unknown
object `dmf_bottle`. No baseline exists for this scene.
Evidence: summary.json entry reason: "Placement 'rear_dmf_bottle' references unknown
object 'dmf_bottle': tests/content/dev_smoke/long_labels_smoke/scene.yaml"
Fix path: either add `dmf_bottle` to the object library or update the scene YAML to
reference an existing object.

### Group 8: pre-existing placeholder assets (10 scenes; missing_asset)

Owner: art sourcing team
Condition: 10 scenes carry placeholder items (electrode_module, gel_opening_tool,
kimwipe_pad, power_supply_off); all were captured in M1 baseline and are not regressions.
Tracked in assets/SVG_ASSET_GAPS.md.
No immediate action required for WS-M4-E gate. Track as open art-sourcing backlog.

---

## Coverage verification

Protocol coverage: 31 of 31 accounted for.
- completed: 7
- unsupported_gesture (adjust): 14
- render_failure (sequence_runner timeout): 5
- missing_object: 4
- other: 1
Total: 7 + 14 + 5 + 4 + 1 = 31. COVERED.

Scene coverage: 37 scenes swept (ws_m4c_scene_corpus_sweep.md TOTAL 37).
- 35 populated, 1 placeholder-only, 1 skipped.
- 36 baselined; 36/36 contract PASS.
All swept scenes accounted for. long_labels_smoke skipped (no baseline, content YAML error).
COVERED.

---

## Concerns and residual risks

1. **passage_pellet_reseed ambiguity.** The "no_active_interaction" error is unusual -
   the walker has never surfaced this for any other protocol. Root cause is unknown
   without inspecting the protocol YAML directly. It could be a missing sequence, a
   malformed target reference, or a runtime dispatch edge case. Recommend inspecting
   the protocol YAML before classifying as pure content_defect.

2. **seeding_workspace overlap density.** 5 overlap pairs (summary.json) is the highest
   count of any non-smoke scene. It passes the DOM contract check (pre-existing, captured
   in baseline) but may indicate a layout authoring problem. Advisory, not a blocker.

3. **adjust on rocking_shaker vs. pipettes.** The `sdspage_destain_gel_rock` step
   `rock_run` uses `adjust` on `rocking_shaker` - a timed continuous process, semantically
   different from pipette volume setting. The adjust affordance design must handle both
   set-point dials and timed-run controls. Raise during affordance milestone planning.

4. **sequence_runner failure mode is a timeout.** The runtime does not throw a clear
   error; it just hangs until Playwright times out. Once the entry-step resolution bug
   is fixed, verify that sequence_runners that reference non-existent mini-protocols
   fail fast with a legible error rather than silently timing out.

5. **Recolor pipeline gap.** assets/SVG_ASSET_GAPS.md documents that the display_color
   recolor pipeline was lost in the Solid.js rewrite. Bottle tinting is degraded across
   protocols. Not a blocker for WS-M4-E but may cause visual confusion in student-facing
   protocols once adjust-blocked protocols are unblocked.

---

## Handoff summary

Register path: `docs/active_plans/audits/m4d_defect_register.md`

Renderer-class blockers for WS-M4-E: NONE. Gate is clear.

Owner-grouped follow-up queue with highest-leverage fix per group:

| Group | Owner | Protocols affected | Highest-leverage fix |
| --- | --- | --- | --- |
| adjust affordance | renderer/runtime | 14 | Implement adjust gesture affordance in runtime |
| sequence_runner bug | runtime | 5 | Fix entry-step resolution to delegate to first mini-protocol |
| missing scene placements | content/scene | 2 | Add hood_surface + waste_container to scene YAMLs |
| well_plate_96 quarantine | runtime + content | 1 | Defer until overlay rendering milestone |
| kimwipe_pad art + placement | art + scene | 1 | Add to scene YAML (placeholder); source art later |
| passage_pellet_reseed authoring | content | 1 | Inspect and fix transfer_to_conical sequence |
| long_labels_smoke YAML error | content/scene | 1 scene | Add dmf_bottle to object library or fix reference |
| placeholder assets (10 scenes) | art sourcing | 10 scenes | Track in SVG_ASSET_GAPS.md (no M4-E action needed) |

Status: **DONE_WITH_CONCERNS**

Concerns: passage_pellet_reseed failure mechanism is ambiguous (see Concerns section 1);
rocking_shaker adjust semantics differ from pipette adjust and need review before affordance
implementation (Concerns section 3).
