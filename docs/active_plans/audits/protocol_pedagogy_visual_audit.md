# Protocol pedagogy and visual audit

Date: 2026-08-03

Status: review complete; findings implemented with genuine blockers documented

Implementation follow-up: the source-to-visible-UI disposition of every
applicable P0, P1, and P2 finding is recorded in the
`docs/active_plans/reports/protocol_pedagogy_visual_resolution.md` ledger.
This audit remains the historical evidence and repair specification; the ledger
is the current implementation and verification record.

## Scope

This audit reviews every authored step in the shipped protocol YAML from a
scientific, procedural, pedagogical, interaction, and visual perspective. It
uses [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md) as the product contract
and compares course content with
[OVCAR8_Carboplatin_Metformin_MTT_Protocol.md](../../protocols/OVCAR8_Carboplatin_Metformin_MTT_Protocol.md),
[OVCAR8_MATH_REVIEW.md](../../protocols/OVCAR8_MATH_REVIEW.md), and
[SDS-PAGE_Protocol_2026.md](../../protocols/SDS-PAGE_Protocol_2026.md).

Coverage:

- 31 protocol YAML files: 28 mini-protocols and 3 sequence runners
- 127 authored steps
- 566 authored interactions: 499 clicks and 67 numeric adjustments
- 42 current scene renders inspected
- all 31 protocol pages completed through visible browser controls
- one wrong-order browser pass used to inspect targeting and retry feedback

The code and content validators pass. That establishes technical consistency,
not teaching quality. This report therefore treats a green validation result as
background evidence only.

## Review method

Each of the 28 mini-protocol sections has two evidence levels:

- A scene note evaluates hierarchy, target visibility, visible state change,
  distraction, object scale and placement, and continuity with adjacent work.
- A row for every authored step evaluates scientific and procedural validity,
  whether the action deserves a distinct learning boundary, what skill or
  decision it teaches, whether the learner can recognize its result, and the
  specific repair or reason to keep it.

Cross-protocol patterns then identify incidental controls, unexplained clicks,
fragmentation, overloaded steps, generic feedback, and missing result
interpretation. Runner rows evaluate continuity across mini-protocol boundaries.
This division avoids repeating the same scene-composition defect in every row
while still making every authored step independently traceable.

## Overall verdict

The protocols are not yet ready for unsupervised teaching use. Much of the
underlying course science is sound, especially the reconciled OVCAR8 drug math,
the MTT volume model, and the canonical SDS-PAGE sample recipe. The principal
problem is translation: the simulations often replace a laboratory judgment
with a required click or exact set point, while several physical workflows are
represented inaccurately.

The three concerns from the manual pass are broad patterns, not isolated cases:

- Repetition is over-fragmented in the six carboplatin working-stock recipes,
  seven carboplatin dosing rows, three sample-mix cycles, six one-action ladder
  steps, and long runs of individual well clicks.
- Twenty-one prompts use `aspirate` for drawing liquid into a dispensing
  pipette. The three vacuum-removal uses in cell passage are appropriate; the
  other uses should say `draw`, `pipette up`, or `load`.
- The 25 mL control is one instance of a wider proxy-control pattern. Ten steps
  present a graduated serological pipette as an adjustable instrument. Four
  SDS-PAGE steps then use one source click and one destination click to stand for
  100, 900, 600, or 400 mL of transfer.

Several higher-risk findings also emerged:

- The cell counter stores `cell_count: 850000` without a displayed unit and
  92.5% viability, but the next protocol requires a concentration, supplies a
  worked example for 1,000,000 cells/mL, and forces 2.4 mL. The measured result
  does not drive the calculation.
- Cell seeding uses 9.6 mL at 2.5&times;10^5 cells/mL with no dead volume, while the
  course protocol specifies 12 mL at 2&times;10^5 cells/mL. The simulation therefore
  changes both the seeding density and the excess volume.
- The passage workflow transfers only 8 of 12 mL, sets a centrifuge to 200 rpm
  when the prompt requires 200&times;g, returns the 6/7 fraction to the old flask,
  never seeds the retained 1/7 fraction into a new culture vessel, and then
  labels and incubates an unseeded 96-well plate.
- Drug preparation, Trypan Blue preparation, and SDS-PAGE sample preparation
  omit required tip changes. This teaches carry-over between stock solutions
  and between samples. Thermo Fisher's pipetting guidance explicitly calls for
  a new tip after each sample to prevent carry-over
  ([manufacturer guidance](https://www.thermofisher.com/us/en/home/life-science/lab-plasticware-supplies/lab-plasticware-supplies-learning-center/lab-plasticware-supplies-resource-library/fundamentals-of-pipetting/proper-pipetting-techniques/preventing-cross-contamination.html)).
- A generic
  `content/objects/pipette/micropipette.yaml` (since retired) claims a
  0.5-1000 &micro;L range while rendering as a P200. It lets one virtual instrument
  perform transfers that require different real pipettes.
- Seven plate-dosing steps load 60 &micro;L once and dispense twelve 5 &micro;L aliquots;
  the metformin step loads 120 &micro;L twice and dispenses 48 aliquots. That is a
  repeating-dispenser workflow, not an ordinary micropipette workflow.
  Manufacturer guidance distinguishes a multi-dispenser that can fill once and
  dispense repeatedly
  ([Eppendorf](https://www.eppendorf.com/gb-en/Products/Liquid-Handling/Positive-Displacement-Pipettes-Dispensers-c-WebPSub-H-12612110)).
- Bio-Rad's Mini-PROTEAN instructions require a second gel or buffer dam for an
  odd gel count, a leakproof gasket seal made by the clamping frame, buffer
  levels tied to the upper and lower chambers, and 700 mL total for two gels.
  The simulation shows one gel without a dam and assigns 600 + 400 mL to it
  ([Bio-Rad manual](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/10007296D.pdf)).

## Pedagogical patterns

### Answers replace thinking

Every interaction is a click or an exact numeric adjustment. There is no
learner-entered calculation, prediction, observation classification, or result
interpretation. Calculation prompts commonly provide the equation, substitution,
answer, and required set point before the learner acts.

Nine steps say `verify`, `confirm`, `inspect`, or `check`, but none offers a
meaningful branch based on what the learner observes. The learner clicks the
object that the prompt already declares correct.

### Granularity is inconsistent

The same type of work is modeled at incompatible scales:

- Loading a ladder is six one-interaction steps, while preparing an entire
  three-reagent protein sample is one 10- or 11-interaction step.
- Seeding a plate requires twelve visible column cycles, while adding MTT to all
  96 wells is one plate click.
- Seven carboplatin rows require 105 interactions, while a 900 mL buffer
  transfer is one source click and one receiving-vessel click.
- Trituration described as about ten cycles per well across 96 wells is one
  click.

Step boundaries should follow learning units, not mouse actions. A useful common
shape is:

| Phase | Learner work | Required evidence |
| --- | --- | --- |
| Observe | Read the relevant physical state | State is visible and distinguishable |
| Decide | Choose a vessel, tool, value, or endpoint | Choice can be wrong for a meaningful reason |
| Execute | Perform the necessary physical sequence | Granularity matches the skill being taught |
| Verify | Interpret the receiving state or result | Feedback explains consequence and recovery |

### Feedback is correctness-only

All 127 steps use `on_failure: retry`; none authors step-specific explanatory
feedback. The visible wrong-order response is the generic statement that the
item is not needed yet. It does not explain contamination, wrong volume, wrong
polarity, loss of a pellet, puncturing a gel well, or another laboratory
consequence.

Feedback should identify:

- what the learner selected or set;
- why it does or does not fit the laboratory objective;
- the likely experimental consequence; and
- the next recoverable action.

### Readouts stop too early

The cell counter, plate reader, and gel-imaging endpoints all stop at instrument
operation:

- The cell counter stores a count and viability but does not make them legible or
  use them in the seeding calculation.
- The plate reader shows a generic graph but produces no well data, blank
  correction, viability normalization, dose-response comparison, or conclusion.
- The lightbox captures a generic gel without a lane record, molecular-weight
  estimate, purity judgment, filename, or metadata.

These are the experimental outcomes. They should receive more teaching time than
opening a lid, picking up a pipette, or pressing Capture.

## Visual patterns

All scenes render and the automated layout report finds no overlaps. Those
metrics do not measure instructional hierarchy.

Strengths:

- Plate-focused scenes keep the 96-well plate central and make the completed
  dose map visually prominent.
- Focused reader, tank-chamber, heat-block, and gel-loading scenes remove much
  unrelated bench clutter.
- Persistent protocol progress makes ordering visible.

Problems:

- The hood and dilution scenes devote about 95% of the frame to empty space
  while making tubes, bottles, and the T75 flask very small. The incubator or
  microscope can dominate even when a small reagent is the next target.
- Concentration identity in the eight-tube rack is not legible. Six working-stock
  steps therefore look nearly identical.
- Well volume is intentionally state-only in
  [well_plate_96.yaml](../../../content/objects/plate/well_plate_96.yaml). The
  media-adjustment protocol changes color but cannot show 90, 95, 195, or
  200 &micro;L. A volume-balancing lesson has no visible volume evidence.
- Loaded gel-lane identity and volume are intentionally invisible in
  [gel_cassette.yaml](../../../content/objects/equipment/gel_cassette.yaml).
  The target focus enlarges the cassette until it clips the scene and highlights
  a full-height vertical lane, not the well opening where the tip belongs.
- The microscope scenes show equipment, not a cell field. Confluence and
  detachment cannot be observed.
- The SDS-PAGE tank, electrode module, cassette, and power supply repeatedly
  change size and position and reappear as separate objects after assembly.
  The run scene visually depicts an unassembled apparatus.
- Receiving-object feedback is often weaker than source depletion. Buffer leaves
  the carboy, but the filled chamber remains visually empty; pipette contents do
  not visibly change; labels and lane contents remain indistinct.
- The MTT endpoint makes all 96 wells the same purple even though the preceding
  treatment map encodes a dose response. This removes the causal link between
  treatment, metabolic activity, formazan, and absorbance.

## Repair order

1. Correct scientific blockers and sequence handoffs before changing wording.
2. Make observation and readout states visible and consequential.
3. Replace universal pipettes, repeated-dispense fiction, and bulk-transfer
   proxies with the correct tools and physical operations.
4. Add contamination control and safety gates to every liquid workflow.
5. Recut steps around pedagogical units and consolidate repetitive click work.
6. Add explanatory failure feedback and result interpretation.
7. Recompose scenes only after the physical state model and step boundaries are
   correct.

Priority meanings used below:

- `P0`: scientific, procedural, safety, or physical contradiction; fix before
  student use.
- `P1`: the step defeats its intended learning or hides the experimental result.
- `P2`: improve granularity, wording, hierarchy, or feedback.
- `KEEP`: accurate and meaningful; retain while applying global feedback polish.

## Cell-culture steps

### [cell_seeding_plate_setup](../../../content/protocols/cell_culture/cell_seeding_plate_setup/protocol.yaml)

Scene note: the plate is prominent and column completion is visible. The source
tube and tools are small, and exact well volumes are not visible.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `cell_seeding_plate_setup/calculate_dilution_volume` | P0 | The prompt supplies 1&times;10^6 cells/mL and the 2.4 mL answer instead of defining and using the preceding `cell_count: 850000` result. It also conflicts with the course target of 12 mL at 2&times;10^5 cells/mL. Make the counter result and unit legible, require the learner to calculate from it, and preserve excess volume. |
| `cell_seeding_plate_setup/prepare_diluted_suspension` | P0 | The 9.6 mL total has no pipetting excess, reuses one serological pipette from cells into the media stock, and suggests vortexing mammalian cells. Use the approved 12 mL recipe, a fresh sterile pipette or media-first order, and gentle resuspension. Replace the digital serological set point with graduation-based measurement. |
| `cell_seeding_plate_setup/seed_96_well_plate` | P0 | Twelve column cycles are physically meaningful, but an eight-channel pipette cannot load from a 15 mL conical tube and 9.6 mL leaves no reservoir dead volume. Add a reagent reservoir and preserve the strong visible column-progress feedback. |
| `cell_seeding_plate_setup/incubate_for_attachment` | P1 | Placement and timing are meaningful, but no incubator check or post-incubation attachment state appears. Show 37&deg;C/5% CO2 readiness and a visible attached-cell endpoint before Day 2. |

### [drug_dilution_setup](../../../content/protocols/cell_culture/drug_dilution_setup/protocol.yaml)

Scene note: all stock math is internally consistent with the reconciled 40&times;
well-dosing model. Tube identity and fill changes are too small to verify, the
same P200-looking generic pipette spans 10-990 &micro;L, and no step changes tips
between drug and media stocks.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `drug_dilution_setup/prepare_carb_parent_stock` | P0 | The C1V1 math is correct, but the prompt gives the answer, calls pipette loading `aspirate`, uses one impossible-range pipette for 40 and 960 &micro;L, and carries the drug-contaminated tip into sterile media. Require the calculation, P200/P1000 selection, fresh tips, a visible label, and mixing verification. |
| `drug_dilution_setup/prepare_carb_working_200um` | P1 | This is the first useful application of the single-source rule, but the answer is supplied and the tube identity is not readable. Teach this one as the worked transfer with correct tips and a labeled 200 &micro;M receiving tube. |
| `drug_dilution_setup/prepare_carb_working_80um` | P2 | Scientifically correct but pedagogically duplicates the prior step. Put it in one visible series-preparation checklist and require the learner to calculate or check the 200/800 &micro;L pair. |
| `drug_dilution_setup/prepare_carb_working_40um` | P2 | Scientifically correct but another nearly identical seven-action step. Consolidate it into the series unit and make the target tube and completed concentration legible. |
| `drug_dilution_setup/prepare_carb_working_20um` | P0 | The 50/950 &micro;L pair cannot be handled accurately by one real micropipette, and the tip is reused between drug and media. Require appropriate pipettes and fresh tips within the consolidated series unit. |
| `drug_dilution_setup/prepare_carb_working_8um` | P0 | The 20/980 &micro;L pair requires different pipettes. The current universal set point and supplied answer teach instrument fiction; use P20/P1000-equivalent tools and visible tube labels. |
| `drug_dilution_setup/prepare_carb_working_4um` | P0 | The 10/990 &micro;L pair is the clearest impossible-range case. Use separate pipettes, a fresh tip for media, and a learner calculation; keep it in the same stock-series progress view rather than a separate lesson. |
| `drug_dilution_setup/prepare_metformin_200mm` | P0 | The 60/240 &micro;L math and dead-volume rationale are strong, but one generic pipette, reused tip, `aspirate` wording, and a 102-word prompt obscure them. Split explanation from action, select suitable pipettes, and show a labeled 300 &micro;L endpoint. |
| `drug_dilution_setup/verify_metformin_volume` | P1 | Clicking the tube merely confirms an answer already encoded in state; there is no readable volume or learner judgment. Show a graduated volume against the 300 &micro;L requirement and ask the learner to decide whether dosing plus dead volume is covered. |

### [passage_hood_detachment](../../../content/protocols/cell_culture/passage_hood_detachment/protocol.yaml)

Scene note: the microscope and incubator dominate a sparse hood while the flask
and reagent bottles are small. The so-called microscope view shows a microscope
and flask, not cells.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `passage_hood_detachment/inspect_confluence` | P0 | A confluence gate is scientifically essential, but no cell field or 70-80% criterion is visible. Show representative fields, require a proceed/wait decision, and explain the consequence of under- or over-confluence. |
| `passage_hood_detachment/spray_hood_with_ethanol` | P1 | `Sterilize` overstates what 70% ethanol does, and one bottle click shows neither coverage nor contact/wipe behavior. Say disinfect or decontaminate and show the approved surface-cleaning sequence. |
| `passage_hood_detachment/aspirate_spent_media` | KEEP | `Aspirate` is correct for vacuum removal. Enlarge the flask and show tip position and monolayer protection so the learner sees why the cells are not contacted. |
| `passage_hood_detachment/pbs_wash` | P1 | Adding 4 mL is not itself a wash; the monolayer is never visibly covered or rocked. Add the physical rinse motion, use a fresh sterile serological pipette, and show the receiving flask rather than only source depletion. |
| `passage_hood_detachment/aspirate_pbs` | KEEP | The order and terminology are correct. Make complete removal visible and reinforce that residual serum inhibits trypsin. |
| `passage_hood_detachment/add_trypsin` | P1 | The rationale is useful, but `approximately 3 mL for a T75` needs faculty confirmation against the vessel-specific course procedure. Show surface coverage and use a fresh pipette instead of a reusable digital set point. |
| `passage_hood_detachment/incubate_for_detachment` | P1 | A timer alone does not teach endpoint control. Show rounding/detachment progress and let the learner decide whether to extend briefly, rather than guaranteeing success after two minutes. |
| `passage_hood_detachment/confirm_detachment` | P0 | The critical microscope confirmation has no cell image and no branch. Show attached versus rounded/detached cells and block neutralization until the learner interprets the field correctly. |
| `passage_hood_detachment/neutralize_trypsin` | P1 | The 3:1 media-to-trypsin rule is coherent, but the reused serological pipette and invisible suspension state weaken it. Use fresh equipment and show the flask change to a mixed cell suspension. |

### [passage_pellet_reseed](../../../content/protocols/cell_culture/passage_pellet_reseed/protocol.yaml)

Scene note: the sequence changes workspaces often, and the final 96-well plate
appears without ever receiving cells. State continuity, not layout polish, is the
primary problem.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `passage_pellet_reseed/transfer_to_conical` | P0 | The prompt says transfer the suspension, but state moves only 8 of 12 mL and leaves 4 mL unexplained in the flask. Transfer the intended full volume or explain and visibly allocate each fraction. |
| `passage_pellet_reseed/label_conical_tube` | P2 | Labeling is authentic, but pen-plus-tube clicks do not show cell line, date, passage, or initials. Require and display the actual label content. |
| `passage_pellet_reseed/centrifuge_spin` | P0 | The prompt requires 200&times;g while the control writes 200 rpm; RCF depends on rotor radius and rpm squared ([Eppendorf](https://www.eppendorf.com/gb-en/lab-academy/life-science/cell-biology/basics-in-centrifugation/)). The scene also spins one unbalanced tube. Require RCF mode or a documented conversion, an opposite balance tube, lid closure, and pellet feedback. |
| `passage_pellet_reseed/aspirate_supernatant` | KEEP | The aspiration term, waste path, and retained pellet are appropriate. Make the pellet and tip depth visible and give consequence feedback for disturbing the pellet. |
| `passage_pellet_reseed/resuspend_pellet` | P0 | Adding 7.9 mL does not resuspend the pellet; no pipetting or gentle mixing occurs. Model the repeated resuspension action, show disappearance of the pellet, and use an appropriate fresh pipette. |
| `passage_pellet_reseed/calculate_split_volume` | P0 | The answer is supplied and the operation returns 6/7 to the old flask while claiming 1:7 passage. Retain 1/7 for a fresh culture vessel, add the approved final medium volume, and allocate or discard the remaining cells explicitly. |
| `passage_pellet_reseed/label_plate` | P0 | The target is an unseeded 96-well assay plate, while the source procedure describes a fresh culture plate/flask. Resolve the intended vessel, seed it first, and display the actual label. |
| `passage_pellet_reseed/return_to_incubator` | P0 | The step calls the plate seeded although no prior operation transferred cells to it. Repair the split-and-reseed sequence before retaining this otherwise meaningful incubation handoff. |

### [trypan_blue_counting](../../../content/protocols/cell_culture/trypan_blue_counting/protocol.yaml)

Scene note: preparation targets are identifiable, but the slide subparts and
counter result are too small. The stored count and 92.5% viability are not
legible in the completed scene. The learning outcomes also claim manual quadrant
counting, but no step displays cells, quadrants, live/dead classification, or a
manual count calculation.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `trypan_blue_counting/add_trypan_blue_to_chamber` | P1 | The 10 &micro;L amount matches the course procedure. Add an explicit clean tip and make the diamond chamber fill visible. |
| `trypan_blue_counting/add_cell_suspension_to_chamber` | P0 | The same tip is taken from Trypan Blue into the cell suspension source, creating carry-over. Require a fresh tip and visibly establish the 1:1 mixture. |
| `trypan_blue_counting/mix_by_pipetting` | P1 | Mixing is meaningful, but one click does not show three to four cycles or an even mixture. Use a short visible cycle/progress treatment without making each stroke a separate lesson. |
| `trypan_blue_counting/load_semicircle_chamber` | P1 | Replace `aspirate` with `draw` or `pipette up`. Show capillary loading, the correct chamber edge, and failure states for bubbles, underfill, and overfill. |
| `trypan_blue_counting/wipe_off_excess` | KEEP | This is a useful preparation check. Make the before/after liquid edge visible and explain why liquid must remain in the chamber. |
| `trypan_blue_counting/insert_slide_into_counter` | KEEP | The physical handoff is clear. Show orientation and a seated-cartridge state. |
| `trypan_blue_counting/wait_for_focus` | P2 | Waiting for an automatic interface action has little independent learning value. Merge it with counter operation while keeping focus status visible. |
| `trypan_blue_counting/press_capture` | P1 | `Press Capture` teaches a button label, not the claimed manual-counting objective. Add the missing live/dead quadrant-counting lesson, then merge automated capture with measurement and frame it as the comparison method. |
| `trypan_blue_counting/verify_viability_gate` | P0 | The result is unreadable, the course source says greater than 90% while this step accepts 90% or greater, and the sequence proceeds regardless of a learner decision. Display count and viability, resolve the threshold, branch on accept/reject, and pass the measured concentration to seeding. |

### [plate_drug_treatment_media_adjustment](../../../content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml)

Scene note: the plate map is central, but colors have no legend and represent
material identity rather than the volume differences this lesson is meant to
teach.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `plate_drug_treatment_media_adjustment/fill_columns_1_6` | P1 | The 95 &micro;L column plan is correct for rows B-H, and six column cycles are authentic. Use a reservoir rather than drawing eight tips from a bottle, and overlay the target/final volume for each quadrant. |
| `plate_drug_treatment_media_adjustment/fill_columns_7_12` | P1 | The 90 &micro;L value is correct for combined-treatment wells. Consolidate it with the first block as one plate-balancing unit while preserving a visible 95 versus 90 &micro;L distinction. |
| `plate_drug_treatment_media_adjustment/correct_row_a_controls` | P1 | Twenty-five clicks mostly test mouse endurance. The arithmetic is valid, but use a suitable multichannel/repeating strategy or a batched row action, then require the learner to verify all four final-volume classes from a labeled plate map. |

### [plate_drug_treatment_drug_addition](../../../content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml)

Scene note: this is the strongest plate visualization; rows and the metformin
half-plate become visually distinct. The rack concentrations remain too small to
read, and the instrument behaves as an undeclared repeating dispenser.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `plate_drug_treatment_drug_addition/add_carb_row_b` | P0 | The concentration math is correct, but a standard micropipette cannot load 60 &micro;L once and accurately dispense twelve 5 &micro;L aliquots. Declare and show a repeating dispenser or model proper reloading; say `draw`, use a fresh tip, and keep the strong row feedback. |
| `plate_drug_treatment_drug_addition/add_carb_row_c` | P0 | The same instrument problem repeats, and no tip change protects the 8 &micro;M stock from row-B carry-over. Consolidate row dosing into one series unit with a fresh-tip checkpoint and readable stock labels. |
| `plate_drug_treatment_drug_addition/add_carb_row_d` | P0 | Math and destination are correct; dispensing mechanics and cross-contamination control are not. Use the approved repeat-dispensing method and visible row progress. |
| `plate_drug_treatment_drug_addition/add_carb_row_e` | P0 | This repeats the same false 60-to-twelve behavior. Keep the dose-map color change, but make tool mode, tip change, stock identity, and 5 &micro;L aliquot size explicit. |
| `plate_drug_treatment_drug_addition/add_carb_row_f` | P0 | Scientifically correct concentration; physically incorrect dispensing and no stock-protection step. Repair within the consolidated dose-series workflow. |
| `plate_drug_treatment_drug_addition/add_carb_row_g` | P0 | Scientifically correct concentration; physically incorrect dispensing and no fresh tip. Preserve the visible 5 &micro;M row as a progress checkpoint, not another standalone lesson. |
| `plate_drug_treatment_drug_addition/add_carb_row_h` | P0 | The 400 &micro;M parent is correctly used as-is, but the same tip and repeat-dispense fiction remain. Make the parent-versus-diluted-stock distinction visible. |
| `plate_drug_treatment_drug_addition/add_metformin_cols_7_12` | P0 | Fifty-two interactions teach clicking wells. Two 120 &micro;L loads followed by 48 five-microliter dispenses require a real multidispenser; identify that tool, use a fresh tip, and show the fixed-modifier half-plate as the learning result. |
| `plate_drug_treatment_drug_addition/incubate_48h` | KEEP | The treatment-to-incubation handoff is meaningful. Add a visible 48-hour cell-response state so the next MTT phase inherits biological, not merely material, differences. |

### [mtt_reagent_prep](../../../content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml)

Scene note: all necessary objects are visible, but the pre-weighed vial and final
tube are tiny. The powder remains conceptually picked up while the learner uses a
serological pipette in the next step.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `mtt_reagent_prep/pick_up_mtt_powder` | P2 | Picking up a vial is an interface action with no independent learning outcome and creates awkward cursor continuity. Merge it into the actual powder-transfer step. |
| `mtt_reagent_prep/prepare_solution_tube` | P1 | The 4 mL amount is correct for the pre-weighed 20 mg vial. Replace the digital serological set point with a 5 mL graduated pipette/controller action and make the receiving volume legible. |
| `mtt_reagent_prep/dissolve_and_mix` | KEEP | Powder transfer plus 30-second vortexing is a coherent pedagogical unit. Show the transition from suspended/undissolved material to a clearly yellow homogeneous solution. |
| `mtt_reagent_prep/verify_final_volume` | P1 | A required tube click cannot establish 4 mL, complete dissolution, or color. Present those as visible acceptance criteria and require a readiness decision. |

### [mtt_plate_reaction](../../../content/protocols/cell_culture/mtt_plate_reaction/protocol.yaml)

Scene note: the plate is readable, but all wells eventually become identical.
The protocol loses the dose-response pattern it needs to explain.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `mtt_plate_reaction/gather_mtt_materials` | P2 | The step asks the learner to ensure freshness and room temperature, but two object clicks cannot verify either. Show reagent status or merge this into the addition setup. |
| `mtt_plate_reaction/prepare_pipette_for_mtt` | P1 | The corrected 1.33 mM final calculation is valuable, but a 59-word prompt both warns that 25 &micro;L is at the P200 edge and then requires it. Use an appropriate multichannel range and separate the calculation from tool setup. |
| `mtt_plate_reaction/add_mtt_to_wells` | P0 | An eight-channel pipette cannot draw from the small tube shown, and one plate click hides twelve column additions even though seeding models them. Use a reservoir, consistent column granularity, and visible 25 &micro;L addition without a 102-word action prompt. |
| `mtt_plate_reaction/incubate_formazan_conversion` | P0 | Time, temperature, and chemistry are correct, but assigning identical formazan to every well destroys the treatment effect. Generate visibly different formazan outcomes from the prior plate map and retained cell viability. |
| `mtt_plate_reaction/decant_mtt_to_waste` | P1 | The intended endpoint is correct. Show plate inversion, retained insoluble crystals, and complete liquid removal rather than a generic plate-to-bin click. |
| `mtt_plate_reaction/pat_plate_dry` | P1 | The physical instruction is useful, but no scene state shows exterior liquid or dryness. Add visible before/after feedback and consequence text for dislodging crystals. |

### [mtt_solubilization_readout](../../../content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml)

Scene note: the two-object plate-reader scene has good hierarchy. It shows a
generic chart and uniformly magenta wells rather than experimental data.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `mtt_solubilization_readout/add_dmso_to_wells` | P0 | One click represents 19.2 mL across 96 wells, and the eight-channel tool draws from a tube instead of a reservoir. Model twelve columns or a justified batch abstraction, preserve excess DMSO, and show crystals dissolving by treatment condition. |
| `mtt_solubilization_readout/trituration_to_dissolve` | P1 | One click stands for about 960 mix cycles and teaches no bubble control or completion criterion. Show a representative controlled mix, a whole-plate progress abstraction, and a visible no-crystal endpoint. |
| `mtt_solubilization_readout/read_absorbance` | P0 | Wavelength and loading are authentic, but the reader has no result field at all. Add plate orientation, blank/background correction, a well table or heat map, viability normalization, dose-response comparison, and a learner conclusion. |

## SDS-PAGE steps

### [sdspage_prepare_running_buffer](../../../content/protocols/sdspage/sdspage_prepare_running_buffer/protocol.yaml)

Scene note: the 1 L carboy is visible, but sixteen small objects dilute the
hierarchy. The source and destination state changes stand for bulk work that is
not shown.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_prepare_running_buffer/dilute_10x_concentrate` | P0 | The 100 mL + 900 mL recipe is correct, but a 25 mL serological pipette is a graduated single-use pipette used with a controller, not a digital set-point device ([Thermo Fisher](https://www.thermofisher.com/order/catalog/product/jp/en/170357T)). Show four measured transfers or use the approved bulk measuring vessel, then mix. |
| `sdspage_prepare_running_buffer/add_diluent_water` | P0 | One source click represents thirty-six 25 mL transfers. Teach filling to a 1 L mark with a suitable carboy/cylinder, make the meniscus/final volume visible, mix thoroughly, and verify the 1&times; identity rather than the interface value 25. |

### [sdspage_prepare_sample_mix_batch](../../../content/protocols/sdspage/sdspage_prepare_sample_mix_batch/protocol.yaml)

Scene note: three source tubes, two pipettes, and the destination rack are
visible but small and unlabeled by slot. The scene is a bench even though BME
handling requires the approved fume-hood workflow.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_prepare_sample_mix_batch/prepare_sample_one` | P0 | The 21 + 7.5 + 1.5 &micro;L recipe yields 1&times; Laemmli correctly, but the step reuses tips across protein, Laemmli, and BME, and it performs BME work on a bench. Require a new tip for every source, move the hazardous step to the approved hood, and make the protein volume depend on the Bradford result when that is the course objective. |
| `sdspage_prepare_sample_mix_batch/prepare_sample_two` | P0 | The same P200 and P10 tips carry material between samples and stocks. Keep one sample as the detailed model, then use a visible batch checklist with fresh-tip checkpoints and sample-specific loading calculations. |
| `sdspage_prepare_sample_mix_batch/prepare_sample_three` | P0 | Repetition does not add a new concept and preserves the same contamination and fixed-volume errors. Consolidate it with the batch unit while showing B1-B3 completion and preserving each tube's identity. |

### [sdspage_heat_denature_samples](../../../content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml)

Scene note: only the heat block and rack appear, which gives clear focus but
little context. Rack placement and all four denatured states should remain
visibly continuous into loading.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_heat_denature_samples/open_heat_block_lid` | P2 | Opening a lid is an internal gesture, not a learning unit. Merge it into setup unless lid state itself is being assessed for safety. |
| `sdspage_heat_denature_samples/place_rack_in_heat_block` | P2 | Correct physical order, but another one-click micro-step. Combine open, place, close, and verify temperature within one denaturation setup unit. |
| `sdspage_heat_denature_samples/close_lid_and_start_timer` | P1 | The five-minute rationale for SDS/BME denaturation is strong. Require the learner to verify the pre-set 95&deg;C state and show the timer and all four tubes changing to ready, rather than starting from a single generic click. |
| `sdspage_heat_denature_samples/retrieve_denatured_samples` | KEEP | Retrieval after the completed wait is meaningful. Preserve tube and rack identity in the next gel-loading scene. |

### [sdspage_prepare_gel_cassette](../../../content/protocols/sdspage/sdspage_prepare_gel_cassette/protocol.yaml)

Scene note: the electrophoresis bench contains many unrelated items and makes
the cassette, comb, tape, gasket, and orientation details too small to inspect.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_prepare_gel_cassette/open_package` | KEEP | Opening the pouch is a real prerequisite. Focus the sealed-to-open change on the cassette rather than the entire equipment inventory. |
| `sdspage_prepare_gel_cassette/remove_tape_and_orient` | P0 | One click removes tape and claims to verify a `top glass plate facing inward toward the gel`; the manufacturer criterion is the cassette's short plate facing inward toward the module gasket. Separate preparation from later orientation, show tape removal, and use the correct plate/gasket language. |
| `sdspage_prepare_gel_cassette/secure_side_clamps` | P0 | The cassette is not yet in a clamping frame, has no second gel or buffer dam, and contains no buffer, so the stated clamp and leak test cannot occur. Move sealing to module assembly and make an actual upper-chamber leak check visible. |
| `sdspage_prepare_gel_cassette/remove_comb` | P1 | Comb removal is correct, but the state change is invisible and the wells are not rinsed. Follow the manufacturer cassette-preparation order, show the comb leaving, and rinse the exposed wells. |

### [sdspage_assemble_electrode_module](../../../content/protocols/sdspage/sdspage_assemble_electrode_module/protocol.yaml)

Scene note: module, cassette, and tank stay as separate icons. Assembly state is
stored but not depicted as a physical composite.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_assemble_electrode_module/open_wing_clamps` | P1 | The action belongs in module assembly, but a standalone one-click lesson is unnecessary. Combine it with cassette placement while visibly opening the clamping frame. |
| `sdspage_assemble_electrode_module/insert_cassette` | P0 | Short-plate orientation is correct, but a single-gel Tetra assembly requires a buffer dam or second gel and neither appears. Add the approved counterpart and show the cassette seated against the gasket. |
| `sdspage_assemble_electrode_module/close_wing_clamps` | P0 | The prompt says the clamps create electrical contact; Bio-Rad describes their role as pressing the short plates against the gasket to create a leakproof upper chamber. Correct the rationale and show the seal. |
| `sdspage_assemble_electrode_module/dock_module_in_tank` | P1 | Lowering the assembled module is correct, but the next scenes again show separate parts. Render one persistent assembled apparatus with correct red/black orientation. |

### [sdspage_fill_tank_buffer](../../../content/protocols/sdspage/sdspage_fill_tank_buffer/protocol.yaml)

Scene note: chamber focus is clean, but buffer leaves the carboy while the
receiving chambers remain visually empty. The 25 mL overlay becomes the lesson's
most salient number even though it is incidental.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_fill_tank_buffer/fill_inner_chamber` | P0 | A 25 mL setting is made to represent 600 mL with one transfer. For Mini-PROTEAN Tetra, teach the upper chamber's fill line just under the outer plate edge and tie the volume to the actual gel/dam configuration. Show a rising fill and a leak check. |
| `sdspage_fill_tank_buffer/fill_outer_chamber` | P0 | The 400 mL state completes an unsupported 1 L total for a one-gel apparatus. Resolve whether the course is simulating one, two, or four gels; use the corresponding manufacturer lower-chamber line and fill volume, and remove the false multi-transfer proxy. |

### [sdspage_load_protein_ladder](../../../content/protocols/sdspage/sdspage_load_protein_ladder/protocol.yaml)

Scene note: the loading scene is intentionally sparse, but the target zoom makes
the cassette enormous and marks the whole vertical lane instead of its top well.
Loaded ladder remains invisible.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_load_protein_ladder/open_gel_workspace` | P2 | Opening a workspace is an interface transition, not laboratory work. Enter the focused scene as part of the ladder-loading unit without resetting pedagogical progress. |
| `sdspage_load_protein_ladder/pick_up_micropipette` | P2 | This click has no state change and no independent learning value. Merge it into tool selection and explain why the chosen range fits the ladder volume. |
| `sdspage_load_protein_ladder/mount_gel_loading_tip` | P1 | A fresh loading tip is scientifically important. Keep it as an internal checkpoint in one ladder-loading step and show the long tip on the pipette. |
| `sdspage_load_protein_ladder/set_micropipette_volume` | P1 | Twenty microliters is the P200 minimum and may not match the ladder product or well capacity. Confirm the faculty-approved ladder volume and use the most accurate compatible pipette. |
| `sdspage_load_protein_ladder/aspirate_protein_ladder` | P2 | The prompt already uses the clearer verb `draw`. Merge this action with the same ladder-loading unit and show liquid in the loading tip. |
| `sdspage_load_protein_ladder/dispense_into_lane_5` | P0 | Lane 5 identity is a useful reference choice, but the active target is a full-height stripe and the loaded state is invisible. Target the well opening, show the tip depth and slow settling, and visibly mark the ladder lane for later analysis. |

### [sdspage_load_samples_batch](../../../content/protocols/sdspage/sdspage_load_samples_batch/protocol.yaml)

Scene note: all three lane targets share the same over-zoom/full-lane defect.
The scene also visually removes the cassette from the module and tank after
assembly.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_load_samples_batch/load_sample_one` | P0 | A fresh tip and slow dispense are good, but `aspirate` wording, fixed 30 &micro;L loading, invisible lane content, and the full-lane target do not teach correct well loading. Use the Bradford-derived approved volume, target the well mouth, and show settled sample. |
| `sdspage_load_samples_batch/load_sample_two` | P0 | Fresh-tip behavior is correctly repeated, but the same visual and fixed-volume problems remain. Keep lane assignment in a visible loading record and reduce redundant interface actions. |
| `sdspage_load_samples_batch/load_sample_three` | P0 | Fresh-tip behavior is correct; the receiving well, loaded state, and sample-specific protein amount are not. Complete one coherent batch-loading unit with visible lanes 1-3 and ladder lane 5. |

### [sdspage_attach_lid_and_leads](../../../content/protocols/sdspage/sdspage_attach_lid_and_leads/protocol.yaml)

Scene note: the tank is readable, but the tank, power supply, electrode module,
and cassette remain four evenly spaced inventory objects. Nothing visibly
assembles or connects. Make the tank/module/cassette one central composite,
keep the power supply nearby but secondary until lead connection, and show the
lid, leads, polarity, and power-off state on the completed apparatus.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_attach_lid_and_leads/secure_apparatus` | P0 | Power-off, lid, polarity, and seated connections belong together, but the apparatus is visually disassembled and power-off is only prose. Require an off-state check, show the lid physically mating with the assembled tank, and provide distinct black/red connection targets with polarity feedback. |

### [sdspage_run_electrophoresis](../../../content/protocols/sdspage/sdspage_run_electrophoresis/protocol.yaml)

Scene note: tank, module, cassette, and power supply are four separate objects.
There is no visible dye front, bubbling, current path, or migration endpoint.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_run_electrophoresis/set_voltage` | KEEP | The selected 150 V for 30 minutes matches the course table and is defensible, although the same course document also contains a stray 110 V instruction that should be resolved. Keep voltage setting as an authentic control and remove unnecessary alternatives from the action prompt. |
| `sdspage_run_electrophoresis/start_run` | P1 | The safety language is strong, but lid/lead/hand-dry readiness is not an enforceable state and no running evidence appears. Gate start on the assembled apparatus and show current/bubble or dye-front feedback. |
| `sdspage_run_electrophoresis/wait_and_stop` | P1 | A fixed timer teaches stopping by clock, while the course procedure says stop when the tracking dye approaches the bottom. Animate migration and ask the learner to stop at the reference line, with overrun and underrun consequences. |

### [sdspage_extract_gel_from_cassette](../../../content/protocols/sdspage/sdspage_extract_gel_from_cassette/protocol.yaml)

Scene note: the sequence has the correct broad safety order, but the gel never
becomes a distinct fragile object and assembled hardware continuity is absent.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_extract_gel_from_cassette/disconnect_power_and_remove_lid` | KEEP | Turning off power before disconnecting and opening is correct. Make each state visible on the assembled tank rather than clicking detached icons. |
| `sdspage_extract_gel_from_cassette/remove_electrode_module` | KEEP | Removal after de-energizing is correct. Preserve buffer, cassette, and module state as the composite is lifted. |
| `sdspage_extract_gel_from_cassette/pry_cassette_open` | P1 | The tool choice is right, but the course procedure requires alignment at marked arrows and warns against twisting. Make those target points visible and give gel/cracked-cassette consequence feedback. |
| `sdspage_extract_gel_from_cassette/transfer_gel_to_staining_tray` | P1 | The transfer is essential but visually moves a cassette, not a fragile gel. Show the gel floating/freeing from the plate, prevent folding or tearing, and preserve lane orientation in the tray. |

### [sdspage_recycle_buffer](../../../content/protocols/sdspage/sdspage_recycle_buffer/protocol.yaml)

Scene note: a clean four-object layout supports a decision, but only the recycle
path exists.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_recycle_buffer/inspect_buffer` | P0 | The prompt describes a real contamination decision, but clicking the tank always confirms recycle readiness. Show clear and contaminated examples, require recycle/dispose choice, and route contaminated buffer to hazardous waste. |
| `sdspage_recycle_buffer/pour_inner_chamber` | P1 | Correct only after a passed inspection. Show a funnel and transfer from the persistent apparatus; group inner and outer draining as one recycling operation. |
| `sdspage_recycle_buffer/pour_outer_chamber` | P1 | The transfer completes volume recovery but the protocol omits concentration, date, course, use count, cap, and storage labeling required by the course source. Add those visible completion criteria. |

### [sdspage_stain_gel](../../../content/protocols/sdspage/sdspage_stain_gel/protocol.yaml)

Scene note: tray, microwave, rocker, water, stain, and waste are visible. Liquid
depth, gel coverage, boiling, and rocker speed are not.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_stain_gel/rinse_tray` | P1 | The rinse order is correct, but retaining the gel while pouring is not taught. Show the cassette-plate dam or approved retention method and give feedback for a sliding gel. |
| `sdspage_stain_gel/add_stain` | P1 | Adding stain is correct, but a bottle click cannot establish the course target of about 1.5 cm coverage. Show liquid depth around the gel. |
| `sdspage_stain_gel/microwave_stain` | P1 | Fifty seconds is within the course range, but `avoid breathing deeply` is not a sufficient safety control and the learner cannot stop before boiling. Show the approved ventilated microwave procedure and a boil threshold. |
| `sdspage_stain_gel/transfer_to_rocker` | P1 | Seven minutes is within the course range. Add rocker speed/spill control and show even gel immersion rather than only timer clicks. |
| `sdspage_stain_gel/recover_stain` | P1 | Reuse is course-authentic, but no label or storage state appears. Require the stain name, date, course, cap, and designated storage destination. |

### [sdspage_destain_gel_setup](../../../content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml)

Scene note: objects are identifiable, but kimwipe count/position, coverage depth,
and gel background remain indistinct.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_destain_gel_setup/rinse_first` | P2 | The first rinse is correct. Treat the two required rinses as one pedagogical unit with a visible rinse counter and gel-retention technique. |
| `sdspage_destain_gel_setup/rinse_second` | P2 | Procedurally required but not a new concept. Keep the second physical cycle inside the same rinse step and show removal of residual blue stain. |
| `sdspage_destain_gel_setup/add_destain` | P1 | The correct reagent is selected, but the course target of about 2 cm coverage is invisible. Show depth and full gel immersion. |
| `sdspage_destain_gel_setup/place_kimwipes` | P1 | The loose knot and no-contact rule are useful, but one pad click cannot show four wipes or their position around the gel. Make number, knot, placement, and contact error visible. |
| `sdspage_destain_gel_setup/microwave_heat` | P1 | Fifty seconds is plausible, but add the approved ventilation and stop-before-boil behavior rather than advising shallow breathing. |
| `sdspage_destain_gel_setup/transfer_to_rocker` | P0 | The course procedure removes and discards the kimwipes after microwaving before the 10-minute rocker incubation. Reorder the handoff so the pad does not remain through the rock cycle. |

### [sdspage_destain_gel_rock](../../../content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml)

Scene note: the tray and rocker are identifiable, but rocking and background
clearing produce no visible change. The tiny kimwipe pad is isolated at the far
right and the waste bottle at the far left, turning the handoff into a search
across empty space. Enlarge the gel/tray during endpoint judgment, move the pad
and waste beside it for disposal, and remove or de-emphasize completed tools.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_destain_gel_rock/rock_run` | P0 | The ten-minute cycle is correct, but it starts with the kimwipes still in the tray because the preceding protocol has not removed them. Repair that order, then show gradual background clearing and controlled speed. |
| `sdspage_destain_gel_rock/remove_kimwipes` | P0 | This action occurs after rocking but belongs immediately after microwave heating in the course procedure. Move it earlier and preserve correct chemical-waste handling. |
| `sdspage_destain_gel_rock/dispose_destain` | P1 | Waste instructions are useful, but `repeat if not clear` has no visible clarity criterion or repeat branch. Show gel-versus-background contrast, let the learner decide, and route additional cycles explicitly. |

### [sdspage_image_gel](../../../content/protocols/sdspage/sdspage_image_gel/protocol.yaml)

Scene note: the lightbox is clear and central, but its final image is a generic
gel with no persistent lane identities or analysis data.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_image_gel/final_rinse` | P1 | The waste-water sequence is plausible, but seven clicks obscure the goal. Show a brief rinse, preserve gel orientation, and give a clean-background endpoint. |
| `sdspage_image_gel/place_on_lightbox` | KEEP | Powering the lightbox and placing the gel flat are meaningful. Add alignment, direct-overhead framing, and reflection/shadow guidance from the course procedure. |
| `sdspage_image_gel/capture` | P0 | Clicking Capture produces no inspectable record. Render the actual ladder and sample bands, require image-quality review, save lane assignment/date/group metadata, and add molecular-weight and purity interpretation before completion. |

### [sdspage_prepare_sample_mix_single_lane](../../../content/protocols/sdspage/sdspage_prepare_sample_mix_single_lane/protocol.yaml)

Scene note: this alternate one-lane lesson uses one generic pipette across the
full 1.5-21 &micro;L range and depicts BME work outside a hood.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_prepare_sample_mix_single_lane/add_protein_sample` | P0 | A fixed 21 &micro;L sample ignores the Bradford-derived protein amount, and the generic pipette cannot accurately cover the whole recipe. Select the correct pipette and loading amount and start with a fresh tip. |
| `sdspage_prepare_sample_mix_single_lane/add_laemmli_buffer` | P0 | The same tip enters Laemmli after protein, contaminating the stock. Require a fresh P10-compatible tip and explain the 4&times; to 1&times; concentration relationship. |
| `sdspage_prepare_sample_mix_single_lane/add_bme` | P0 | The same tip is reused again and the visual scene contradicts the fume-hood warning. Move to the approved hood, use a fresh P10 tip, and make containment/waste handling explicit. |
| `sdspage_prepare_sample_mix_single_lane/cap_and_rack` | P1 | Capping a volatile-reagent tube is meaningful, but the two clicks have no visible state. Show the cap sealed, tube label/slot, and safe handoff to heat denaturation. |

### [sdspage_load_sample_single_lane](../../../content/protocols/sdspage/sdspage_load_sample_single_lane/protocol.yaml)

Scene note: this alternate lesson has the same full-lane target and invisible
loaded state as batch loading.

| Step | Priority | Review and recommended change |
| --- | --- | --- |
| `sdspage_load_sample_single_lane/swap_tip` | KEEP | Ejecting the prior tip and mounting a fresh loading tip is scientifically meaningful. Keep it within one coherent sample-loading unit and show the tip change. |
| `sdspage_load_sample_single_lane/draw_sample` | P1 | Replace `aspirate` with `draw`, confirm that 30 &micro;L is the approved sample-specific loading volume, and show the denatured sample in the long loading tip. |
| `sdspage_load_sample_single_lane/dispense_lane` | P0 | The whole vertical lane is clickable instead of the well opening, loaded sample stays invisible, and a final pipette click is interface cleanup. Target the top well, teach depth/slow delivery, and visibly preserve lane identity. |

## Runner continuity

Sequence runners author no new steps, but their handoffs determine whether the
mini-protocol lessons form a coherent experiment.

| Runner | Priority | Review and recommended change |
| --- | --- | --- |
| [routine_passage](../../../content/protocols/runners/routine_passage/protocol.yaml) | P0 | The runner carries the 12 mL neutralized suspension into a partial 8 mL transfer, reversed split, unseeded 96-well plate, and false incubation endpoint. Repair the full flask-to-new-culture path before judging individual scene polish. |
| [cell_culture_full](../../../content/protocols/runners/cell_culture_full/protocol.yaml) | P0 | The unit-ambiguous `cell_count: 850000` result is discarded; the next step assumes 1,000,000 cells/mL. A 96-well plate is also called seeded during passage before the actual seeding protocol. Carry count, concentration, viability, vessel identity, volume, and day transitions through one authoritative state chain. |
| [sdspage_full](../../../content/protocols/runners/sdspage_full/protocol.yaml) | P0 | The runner uses one cassette without a visible buffer dam, repeatedly separates assembled hardware, loses loaded-lane visibility, rocks destain with kimwipes in place, and ends at a generic capture. Preserve one physical apparatus/gel identity from preparation through interpreted image. |

## Faculty decisions

These choices should be resolved in course documentation before implementation:

- Confirm 12 mL at 2&times;10^5 cells/mL and 20,000 cells/well versus the current
  9.6 mL at 2.5&times;10^5 cells/mL and 25,000 cells/well.
- Confirm the culture vessel and allocation for a 1:7 OVCAR8 passage.
- Confirm T75 PBS, trypsin, neutralization, spin RCF/time, and final culture
  volumes.
- Select the actual pipettes, repeat dispenser, reservoirs, and tip-change policy
  available in the teaching lab.
- Resolve the SDS-PAGE source's stray 110 V line versus its 150 V/25-30 minute
  table.
- Confirm the gel count, buffer dam, chamber fill levels, ladder product/volume,
  sample loading volumes, and buffer-reuse limit.
- Confirm the local fume-hood and microwave controls for BME, Coomassie, and
  methanol/acetic-acid destain.
- Define what students must conclude from cell counts, plate-reader data, and
  gel images before a protocol is complete.

## Acceptance criteria

A revised protocol set is pedagogically ready when:

- every calculation uses prior experimental state or an explicit provided input;
- every observation gate presents distinguishable evidence and a real decision;
- each transfer uses a physically plausible tool, range, source vessel, and tip
  policy;
- all receiving volumes, fills, pellets, wells, lanes, and assembled states that
  matter to learning are visible;
- full runners preserve vessel, material, apparatus, and biological state across
  scene changes;
- step boundaries correspond to laboratory concepts rather than interface
  clicks;
- repeated work uses consistent, justified granularity;
- incorrect choices produce consequence-based feedback and a recoverable retry;
- counter, plate-reader, and gel-image results are interpreted before completion;
  and
- the visible-control walker still passes without weakening its honest-click or
  wrong-order guards.

## Reproduction

The review used these commands from the repository root:

```bash
source source_me.sh && python3 validation/manual/protocol_manual.py --all --lint
node tools/scene_to_png.mjs --all --png --out test-results/pedagogy_scene_audit
./run_playwright_tests.sh --build tests/playwright/e2e/protocol_walkthrough.spec.ts
```
