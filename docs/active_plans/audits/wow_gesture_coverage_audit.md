# Gesture coverage audit

Status: COMPLETE (static source audit plus the retained browser-proof snapshot). No production,
specification, or test file was changed. The browser reports are dated 2026-07-13, so they are
evidence of the then-built artifact, not a claim about the working tree on 2026-07-22.

## Executive finding

At this audit's 2026-07-22 source snapshot, the curriculum taught a two-gesture
simulation: 395 authored `click` interactions and 56 `adjust` interactions
across 26 mini-protocols (451 total). A 2026-07-24 recount finds 400 `click`
and 56 `adjust`; the per-protocol matrix below retains the original snapshot
counts. Both scans find zero `select`, `type`, and `drag` interactions. This is
not merely a missing feature count: most laboratory actions that ought to
distinguish selecting a reagent, setting a value, aspirating, dispensing,
transferring, mixing, or placing are represented as an ordered series of
correct object clicks. A student can complete many sequences by following
highlights without demonstrating the physically meaningful gesture.

The runtime has registry rows and dispatch paths for all five closed gestures, and `type`/`adjust`
have real visible overlays. `drag` has a visible-driver implementation and a step-machine test, but
the production walker rejects it as unsupported and no authored protocol proves it in the browser.
`select` and `type` are entirely unexercised by content. This makes the apparent generalization
larger than the demonstrated pedagogical interaction model.

Owner clarification on 2026-07-24 reopened the `select` design. The owner
recalled that `select` once had a more specialized purpose, but clarified that
multiple-choice controls can use ordinary browser clicks and that the intended
role of `select` is not remembered. The authoring guide and vocabulary before
commit `d5493bd0` describe presented choices; the June commit instead redefined
`select` as choosing among present clickable scene objects. Since the corpus
contains no `select` interaction, neither interpretation has content or browser
proof. Preserve the discrepancy and compare real decision tasks against the
existing compositional `click` model before deciding whether `select` should be
retained, redefined, or retired. See `docs/specs/GESTURE_MODEL.md`.

The hard contract requires a visible UI walk for every mini-protocol
([PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md), item 4). The retained reports show 25/26 mini
protocols completed visibly on 2026-07-13; `cell_culture_full` is a runner rather than a mini, and
the only mini red was `plate_drug_treatment_drug_addition` at an invisible tube-rack subpart.
Those results must be refreshed after current changes.

## Gesture-to-runtime matrix

| Gesture | Authored protocol count and list | Visible control | Runtime and validator path | Walker path | Browser proof | Evidence strength and blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `click` | 26 mini protocols; 395 interactions. Every current mini uses it. | SVG-backed scene placement with `data-item-id`. | `handle_click`; `correct_target` checks exact target equality. | Real visible `locator.click()`, checks visibility and a state change. | 25 mini protocols PASS in the 2026-07-13 reports; one mini red below. | STRONG for basic sequential clicks, but not for semantic manipulation. Click dominates nearly all lab actions. |
| `adjust` | 18 mini protocols; 56 interactions: `cell_seeding_plate_setup`, `drug_dilution_setup`, `mtt_plate_reaction`, `mtt_reagent_prep`, `mtt_solubilization_readout`, `passage_hood_detachment`, `passage_pellet_reseed`, `plate_drug_treatment_drug_addition`, `plate_drug_treatment_media_adjustment`, `trypan_blue_counting`, `sdspage_destain_gel_rock`, `sdspage_destain_gel_setup`, `sdspage_fill_tank_buffer`, `sdspage_load_protein_ladder`, `sdspage_load_sample_single_lane`, `sdspage_prepare_running_buffer`, `sdspage_prepare_sample_mix_single_lane`, and `sdspage_run_electrophoresis`. | Shared visible numeric set-point editor, input plus increment/decrement and Commit. | `handle_adjust_commit`; `target_with_value` compares the committed value to declared object state. | Visible `fill()` plus Commit, then waits for progress. | Passed in retained reports, including pipette volume and power-supply examples. | MODERATE. It proves numeric entry, not manipulation of the represented device; the entire class shares one generic overlay. |
| `select` | 0 protocols; 0 interactions. | Same rendered scene-object click as `click`; host promotes a click only while this is active. | `handle_click` with `select`; `correct_choice` is target equality. | Same visible click driver as `click`. | None. | UNPROVEN. No discrimination/choice learning task currently uses the gesture that the spec assigns to choosing among objects. |
| `type` | 0 protocols; 0 interactions. | Visible TypeInput overlay and Commit. | `handle_type_commit`; `target_with_value` with text coercion. | Visible fill plus Commit helper exists. | None. | UNPROVEN. No student has to type a calculation, label, observation, or interpretation. |
| `drag` | 0 protocols; 0 interactions. | Host drag surface, source and destination scene items. | `handle_drag_commit`; destination derives from `LayoutMove.zone`. | `dragToAndWaitProgress` exists, but the production sweep classifies `drag` unsupported. | Unit only; no authored or browser proof. | BLOCKED/UNPROVEN. Runtime and walker contract disagree, so a drag protocol cannot be accepted through the mandated full walk yet. |

Runtime evidence: [gesture_registry.ts](../../../src/scene_runtime/protocol/gesture_registry.ts#L83)
declares every affordance and walker driver; [protocol_host.tsx](../../../src/protocol_host.tsx#L464)
mounts scene-click, type, and adjust paths. The load-time guard rejects an authored gesture without
a wired registry entry in [gesture_affordance_check.ts](../../../src/scene_runtime/protocol/gesture_affordance_check.ts#L74).
The walker uses actionability-checked visible interactions and never writes the runtime surfaces in
[walker_helpers.mjs](../../../tests/playwright/e2e/walker_helpers.mjs#L12). Its production
dispatcher explicitly supports only click/select/type/adjust in
[helper_walker.mjs](../../../tests/playwright/e2e/helper_walker.mjs#L54), despite the drag helper
in [walker_helpers.mjs](../../../tests/playwright/e2e/walker_helpers.mjs#L390).

## Mini-protocol coverage matrix

`C/A` is authored click/adjust interaction count. YAML evidence gives the first authored click and,
where applicable, first adjust location; every count was derived from all `gesture:` fields in that
file. `PASS-13` and `RED-13` are retained 2026-07-13 visible-walk reports, not live verification.

| Mini-protocol | C/A | Gesture pattern and visible affordance | Validator and walker coverage | Browser proof / concern | YAML evidence |
| --- | ---: | --- | --- | --- | --- |
| `cell_seeding_plate_setup` | 12/4 | click chain plus numeric volumes | correct-target plus target-with-value; visible adjust overlay | PASS-13; mechanical seeding is still click-to-transfer | `protocol.yaml:37,67` |
| `drug_dilution_setup` | 45/16 | repeated click/set-point dilution loop | both live paths | PASS-13; strongest adjust coverage, but 16 values use one generic editor | `protocol.yaml:40,48` |
| `mtt_plate_reaction` | 12/1 | click transfers plus one set point | both live paths | PASS-13; reagent addition remains click-only | `protocol.yaml:39,73` |
| `mtt_reagent_prep` | 9/1 | click chain plus one set point | both live paths | PASS-13; mixing/dissolving lacks a distinct gesture | `protocol.yaml:25,53` |
| `mtt_solubilization_readout` | 8/2 | click plus reader set point | both live paths | PASS-13; retained report proves 560 adjustment after scene change, refresh needed | `protocol.yaml:32,40` |
| `passage_hood_detachment` | 19/3 | click-led hood workflow plus timing/volume values | both live paths | PASS-13; rich sequence, but most aseptic actions collapse to clicks | `protocol.yaml:27,109` |
| `passage_pellet_reseed` | 21/2 | click-led transfer/resuspension plus values | both live paths | PASS-13; transfer and resuspension have no distinct manipulation | `protocol.yaml:42,117` |
| `plate_drug_treatment_drug_addition` | 143/8 | per-row/per-well click sequence plus values | both paths begin visibly | RED-13: tube_A subpart has no DOM affordance; click sequence is very long and brute-force-prone | `protocol.yaml:30,38` |
| `plate_drug_treatment_media_adjustment` | 8/4 | click plus repeated set points | both live paths | PASS-13; concentration/volume work is number entry, not selection reasoning | `protocol.yaml:34,42` |
| `trypan_blue_counting` | 17/3 | click-led counter workflow plus values | both live paths | PASS-13; observation/viability judgement is represented by correct clicks | `protocol.yaml:48,59` |
| `sdspage_assemble_electrode_module` | 4/0 | pure object-click assembly | correct-target plus click walker | PASS-13; assembly should be the first drag vertical slice | `protocol.yaml:26` |
| `sdspage_attach_lid_and_leads` | 3/0 | pure object-click attachment | click only | PASS-13; attaching leads is a click proxy | `protocol.yaml:29` |
| `sdspage_destain_gel_rock` | 6/1 | clicks plus shaker time | both live paths | PASS-13; transfer onto rocker is click proxy | `protocol.yaml:25,33` |
| `sdspage_destain_gel_setup` | 9/1 | clicks plus microwave time | both live paths | PASS-13; no mode/timer selection task | `protocol.yaml:26,157` |
| `sdspage_extract_gel_from_cassette` | 10/0 | pure click chain | click only | PASS-13; extraction and transfer are click proxies | `protocol.yaml:31` |
| `sdspage_fill_tank_buffer` | 6/2 | click plus pipette volume | both live paths | PASS-13; filling repeats same generic numeric interaction | `protocol.yaml:28,36` |
| `sdspage_heat_denature_samples` | 5/0 | pure click chain | click only | PASS-13; timed equipment operation needs an intentional control state | `protocol.yaml:22` |
| `sdspage_image_gel` | 9/0 | pure click chain | click only | PASS-13; imaging/capture lacks parameter or observation interaction | `protocol.yaml:31` |
| `sdspage_load_protein_ladder` | 5/1 | click plus pipette volume | both live paths | PASS-13; aspirate/dispense/lane placement have no manipulation distinction | `protocol.yaml:25,77` |
| `sdspage_load_sample_single_lane` | 6/1 | click plus pipette volume | both live paths | PASS-13; lane loading is click proxy | `protocol.yaml:31,67` |
| `sdspage_prepare_gel_cassette` | 4/0 | pure object-click assembly | click only | PASS-13; good drag candidate | `protocol.yaml:24` |
| `sdspage_prepare_running_buffer` | 6/2 | click plus pipette volume | both live paths | PASS-13; repeated liquid transfer has no material-selection gesture | `protocol.yaml:28,36` |
| `sdspage_prepare_sample_mix_single_lane` | 9/3 | click plus pipette volumes | both live paths | PASS-13; mix is ordered clicking, not a distinct action | `protocol.yaml:30,38` |
| `sdspage_recycle_buffer` | 5/0 | pure click transfer | click only | PASS-13; pouring/collection are click proxies | `protocol.yaml:25` |
| `sdspage_run_electrophoresis` | 2/1 | power-supply set point, start, wait | both live paths | PASS-13; best existing equipment-control shape, still generic numeric entry | `protocol.yaml:26,52` |
| `sdspage_stain_gel` | 12/0 | pure click stain/rinse sequence | click only | PASS-13; multiple liquid operations visually/pedagogically indistinct | `protocol.yaml:27` |

There are five `sequence_runner` files (`cell_culture_full`, `routine_passage`, `sdspage_full`,
`sdspage_load_samples_batch`, and `sdspage_prepare_sample_mix_batch`). They author no gestures;
they flatten and reuse mini-protocol interactions. The retained reports show `sdspage_full` at
72/72 visible steps and `routine_passage` at 18/18, but this does not add gesture diversity.

## Brute-force and hidden-path assessment

- The walker itself is not a backdoor: it reads `window.gameState` and `window.PROTOCOL_STEPS` but
  advances only with visible click/fill/commit actions. Evidence:
  [helper_walker.mjs](../../../tests/playwright/e2e/helper_walker.mjs#L14) and
  [walker_helpers.mjs](../../../tests/playwright/e2e/walker_helpers.mjs#L75).
- It is nevertheless a directed-answer walker. It reads the active target and authored expected
  number, then clicks or commits exactly that answer
  ([helper_walker.mjs](../../../tests/playwright/e2e/helper_walker.mjs#L140)). This is correct for
  UI conformance but cannot establish that a student can reason through the protocol unaided.
- The single wrong-order test only covers `sdspage_heat_denature_samples`; type and adjust skip
  wrong-object injection, and no current protocol exercises select or drag
  ([protocol_walkthrough.spec.ts](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts#L99),
  [helper_walker.mjs](../../../tests/playwright/e2e/helper_walker.mjs#L178)).
- `plate_drug_treatment_drug_addition` proves that a semantically precise subpart can still be
  authored without a visible click target. The retained report fails on
  `rear_center_carb_stocks.tube_A`; the current spec's expected-fail registry also records this
  condition ([protocol_walkthrough.spec.ts](../../../tests/playwright/e2e/protocol_walkthrough.spec.ts#L49)).

## Recommended vertical-slice order

1. Make `drag` acceptance honest: update the production walker to drive its existing visible drag
   helper, then author and browser-prove one simple assembly/placement slice. Start with
   `sdspage_assemble_electrode_module` or `sdspage_prepare_gel_cassette`, where the current
   click-only model most clearly hides a spatial skill.
2. Repair the subpart-affordance contract using the drug-addition protocol as the acceptance slice.
   It must expose a real tube/well target, retain dose/well discrimination, render a state change,
   and walk visibly. Do not replace it with a base-object click; that would erase the teaching
   distinction.
3. Investigate whether `select` has a distinct job. Compare plausible scene-object decisions and
   answer-control decisions against ordinary `click` plus target capabilities and response
   operations. Prototype a `select` slice only if that comparison exposes a real semantic or
   pedagogical gap.
4. Add one `type` slice where text is academically meaningful: a calculated dilution, sample label,
   or a short observation. Validate and visibly explain rejection, rather than using numeric entry
   for every value task.
5. Redesign one high-repetition liquid workflow (`drug_dilution_setup` or an SDS-PAGE load) around
   the distinct cycle: choose tool -> set volume -> obtain source -> transfer to destination ->
   observe material state. Give transfer/placement a distinct visible gesture before scaling this
   pattern across all 451 interactions.
6. Expand negative and screenshot proof per gesture: wrong target, wrong value, wrong selection,
   and wrong drop destination; save before/after screenshots for every meaningful state change.

## Verification record

- `rg --files content/protocols | rg 'protocol\\.yaml$'` found 31 protocol files: 26 minis and 5
  runners.
- The original `awk` scan found `click=395`, `adjust=56`, and no authored
  `select`, `type`, or `drag`. The 2026-07-24 recount found `click=400`,
  `adjust=56`, and still no authored `select`, `type`, or `drag`.
- Read-only inspection of the registry, host, validators, walker, Playwright suite, and retained
  reports established the paths above. No live build or browser walk was run in this workstream;
  all retained browser proof is explicitly marked `PASS-13`/`RED-13`.

## Residual risk

The clean static vocabulary check and old positive reports can prove neither current visual quality
nor current teaching quality. In particular, they cannot establish that SVG targets are legible,
that state changes are visible rather than merely stateful, that layout overlap does not intercept a
pointer, or that a student can make a choice without the walker's privileged active-target read.
Refresh the full visible-UI sweep and inspect screenshots after each vertical slice.
