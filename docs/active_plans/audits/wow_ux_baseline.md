# WOW UX baseline

## Scope and method

This is a read-only baseline of the current pointer-user journey. It does not
score keyboard or screen-reader support because that is explicitly outside the
current scene-runtime scope in [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md).

Fresh evidence came from a rebuilt `dist/` and three real visible-UI walks at
1280x900. The walker used ordinary page entry, visible target clicks, and the
shared visible numeric editor; it did not mutate runtime state or force scene
changes. The representative set was:

| Journey | Learning shape | Result | Evidence |
| --- | --- | --- | --- |
| Launcher -> MTT reagent preparation | Short mixed click and value-entry workflow | 4/4 steps passed | `test-results/wow_ux_baseline/mtt_reagent_prep/playthrough_report.json` |
| SDS-PAGE heat denaturation | Short click-only workflow with a timed phase | 4/4 steps passed | `test-results/wow_ux_baseline/sdspage_heat_denature_samples/playthrough_report.json` |
| Hood passage detachment | Long multi-scene culture workflow with three value entries | 9/9 steps passed | `test-results/wow_ux_baseline/passage_hood_detachment/playthrough_report.json` |

The walkthrough engine saves entry, each successful interaction, each step,
and final state [protocol_walkthrough_yaml.mjs](../../../tests/playwright/e2e/protocol_walkthrough_yaml.mjs#L580-L705).
Screenshots in the evidence folder are therefore a reproducible before/after
record rather than hand-picked static mockups.

## Executive baseline

The current experience is **functionally viable but educationally thin**. All
three chosen protocols completed through the visible interface with no browser
errors. The student sees a current target ring, a step counter, and a repeated
prompt. What is missing is the learning loop: orient, predict, act, see a
scientifically meaningful state change, explain why it happened, and finish
with a visible outcome. The result feels closer to a dependable interaction
harness than a polished virtual lab.

The immediate quality ceiling is not a general rewrite. It is a small number
of shared seams: a proper protocol start/completion state, a useful live coach,
clearer scene focus, and corrections to the few content states that currently
teach the wrong thing.

## Nielsen heuristic scorecard

Scores are 0 (absent), 1 (major problem), 2 (present but unreliable), 3 (good),
or 4 (strong). Total: **17/40 (1.7/4)**.

| Heuristic | Score | Evidence-based reading |
| --- | ---: | --- |
| Visibility of system status | 2 | The counter and target outline are clear, but final MTT state leaves a blank guidance bar and every outline card becomes upcoming: `mtt_reagent_prep/final_screen.png`; [step_outline.tsx](../../../src/shell/regions/step_outline.tsx). |
| Match between system and lab world | 2 | Labels name familiar equipment, but the passage workflow asks for room-temperature incubation by clicking an incubator whose default is 37 C: [passage protocol](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml#L221-L235), [incubator](../../../content/objects/equipment/incubator.yaml#L5-L20). |
| User control and freedom | 1 | The outline intentionally has no click navigation, and no visible restart, review, or recovery route appears in the journeys: [step_outline.tsx](../../../src/shell/regions/step_outline.tsx). |
| Consistency and standards | 2 | The shell is consistent, but the scenes combine very small tubes/pipettes, oversized instruments, empty work areas, and a placeholder-like BSC surface: `mtt_reagent_prep/initial_state.png`, `passage_hood_detachment/initial_state.png`. |
| Error prevention | 3 | The active target ring gives useful direction and the existing walker explicitly verifies that a wrong click does not advance the SDS-PAGE workflow: [style.css](../../../src/style.css#L443-L458), [walker negative check](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts#L99-L132). |
| Recognition rather than recall | 2 | Prompts are repeated in a bottom bar and a truncated side outline, but the same SDS-PAGE scene displays two identically labelled 24-slot racks while asking for "the" rack: `sdspage_heat_denature_samples/initial_state.png`; [base scene placements](../../../content/base_scenes/heat_block_bench.yaml#L116-L143). |
| Flexibility and efficiency | 1 | A long passage run requires 22 authored interactions, plus a value entry and commit for each of three adjustments, without learner-controlled review or skip/replay. The shared control is a detached bottom-fixed panel: [SetPointEditor](../../../src/shell/hud/set_point_editor.tsx#L143-L240). |
| Aesthetic and minimalist design | 2 | The cards and target ring are legible, but the launcher surfaces opaque IDs and truncated goals while the scenes carry large unused areas and inconsistent visual scale: `test-results/test_launcher_00_index.png`, `mtt_reagent_prep/initial_state.png`. |
| Recognize, diagnose, recover from errors | 1 | Numeric rejection exists, but it is only a terse set-point message; no comparable visible explanation was observed for an incorrect scene-object choice: [SetPointEditor](../../../src/shell/hud/set_point_editor.tsx#L241-L251). |
| Help and documentation | 1 | The baseline coach occupied primary visual space yet defaulted to "Follow the current step guidance." rather than supplying a technique, rationale, or next-action cue. The replacement lives in [authored_tip.tsx](../../../src/shell/regions/authored_tip.tsx); baseline evidence remains in `mtt_reagent_prep/initial_state.png`. |

## Measured task friction

| Journey | Authored interactions | Minimum visible inputs | Friction observed |
| --- | ---: | ---: | --- |
| MTT reagent preparation | 10 | 11 (one numeric value plus Commit) | Four state-only clicks in the dissolve step do not show a commensurate physical transformation; the final check is just another click. |
| SDS-PAGE heat denaturation | 5 | 5 plus timed wait | The smallest successful journey, but two identical rack visuals weaken the crucial placement decision. |
| Passage detachment | 22 | 25 (three numeric values plus Commit) | Nine cards crowd the outline; the learner repeatedly changes between pipette, detached numeric editor, bottle, and flask without an action summary. |

All counts exclude launcher selection and timed waiting. The counts are derived
from the protocol sequences, not an internal advance API: [MTT](../../../content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml#L41-L159), [SDS-PAGE](../../../content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml#L39-L117), and [passage](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml#L20-L322).

## Ranked top 10 findings

1. **Correct a scientifically contradictory incubation action.** The passage prompt specifies approximately two minutes at room temperature, but the required target is a 37 C incubator. This is a direct teaching error, not a visual preference. Expected impact: prevents students from encoding the wrong condition for trypsin detachment. Evidence: [passage protocol](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml#L221-L235), [incubator default](../../../content/objects/equipment/incubator.yaml#L5-L20), `passage_hood_detachment/interaction_incubate_for_detachment_i0_rear_right_incubator.png`.

2. **Make the confluence and detachment checks observable, not automatic.** Clicking the microscope immediately writes `observed_at_confluence`; clicking it later immediately changes the flask to cell suspension. The microscope evidence scene contains an instrument and flask, not a visible confluence or detachment decision. Expected impact: restores the central biological judgement in the passage workflow. Evidence: [inspection response](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml#L21-L45), [detachment response](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml#L242-L267), `passage_hood_detachment/interaction_inspect_confluence_i0_main_microscope.png`.

3. **Repair MTT state sequencing.** The MTT tube becomes `mtt_solution_12mm` immediately after PBS is added, before the powder-transfer and vortex interactions. Expected impact: prevents a causal misconception about how concentration and dissolution arise. Evidence: [protocol.yaml:74-84](../../../content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml#L74-L84), [protocol.yaml:91-133](../../../content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml#L91-L133).

4. **Ship a real completion moment.** After a successful 4/4 MTT walk, the current guidance is empty and the outline has no completed state because `null` maps every card to upcoming. Expected impact: supplies closure, achievement, and a clear handoff to the next learning block. Evidence: `mtt_reagent_prep/final_screen.png`; [step_outline.tsx](../../../src/shell/regions/step_outline.tsx).

5. **Replace the generic coach with contextual instructional feedback.** The largest header region combines a grey silhouette with a fallback sentence that does not add help beyond the guidance bar. Expected impact: turn unused chrome into just-in-time technique, safety, and interpretation support. Evidence: [placeholder avatar](../../../src/style.css#L69-L81), the replacement [authored_tip.tsx](../../../src/shell/regions/authored_tip.tsx), and `sdspage_heat_denature_samples/initial_state.png`.

6. **Give every consequential click a visible scientific result.** The hood cleanliness state maps both dirty and ethanol-sprayed to the same SVG; the heat-block open/closed visual states also map to the same closed SVG. Expected impact: students can connect action to a visible consequence instead of trusting the counter. Evidence: [hood states](../../../content/objects/equipment/hood_surface.yaml#L12-L20), [heat-block states](../../../content/objects/equipment/heat_block.yaml#L23-L36), `sdspage_heat_denature_samples/interaction_close_lid_and_start_timer_i0_front_heat_block.png`.

7. **Remove duplicate or non-target lookalikes from focused scenes.** SDS-PAGE presents two indistinguishable 24-slot racks while the protocol target is only `front_microtube_rack`. Expected impact: lowers avoidable search and removes a false decision at the protocol's central placement step. Evidence: [two placements](../../../content/base_scenes/heat_block_bench.yaml#L116-L143), [target](../../../content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml#L39-L53), `sdspage_heat_denature_samples/initial_state.png`.

8. **Rework visual hierarchy around the active work surface.** The three evidence scenes are very sparse but have dramatically unequal object scales; in the passage scene a large microscope competes with a small flask while the BSC workspace reads as a mostly empty rectangular outline. Expected impact: make the next object and biological substrate obvious at a glance. Evidence: `mtt_reagent_prep/initial_state.png`, `passage_hood_detachment/initial_state.png`; [passage layout note acknowledging scale pressure](../../../content/protocols/cell_culture/passage_hood_detachment/scenes/hood_workspace.yaml#L69-L100).

9. **Make value adjustment feel like an instrument operation.** The generic bottom-fixed panel only says "Set value:" and requires an extra Commit; it is visually detached from the highlighted pipette and hides the relevant units/context. Expected impact: reduce cognitive switching and make measurement instruction more credible. Evidence: [editor UI](../../../src/shell/hud/set_point_editor.tsx#L143-L240), `mtt_reagent_prep/interaction_prepare_solution_tube_i1_base_right_micropipette.png`.

10. **Make protocol selection student-facing, not registry-facing.** The launcher foregrounds opaque protocol IDs and truncates the purpose of large cards; it omits a short outcome, materials/safety preview, and a meaningful estimated time in the observed launcher. Expected impact: lets students choose and prepare for the right learning block before entering it. Evidence: `test-results/test_launcher_00_index.png`; `protocol_launcher.tsx`.

## What already works

- The shared scene engine can deliver a directed, visible click path. All three
  selected walks completed through visible controls, including numeric inputs
  and timed phases.
- The orange active ring is an effective immediate cue in all screenshots.
- The SDS-PAGE 95 C timed state is the strongest current moment: it pairs a
  clear target, a timer label, and a causal explanation in the guidance bar.
  See `sdspage_heat_denature_samples/interaction_close_lid_and_start_timer_i0_front_heat_block.png`.
- The existing per-interaction evidence mechanism is a solid regression spine;
  future WOW changes can be assessed against the same paths.

## Recommended first implementation slice

1. Fix findings 1-3 in protocol/object content before adding polish.
2. Add a shared start, action-result, and completion layer; preserve the
   existing YAML-to-runtime boundary rather than embedding protocol-specific
   UI behavior in scenes.
3. Upgrade the shared coach and value editor together, then use the three
   evidence journeys as visual regression cases.
4. Curate each focused scene to one clear instance of every intended object
   and make every authored state have an observable representation.

This order has the best instructional return: it removes false teaching first,
then creates the feedback loop that makes the current strong click-path
foundation feel like a lab.
