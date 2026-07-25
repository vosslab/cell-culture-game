# WOW pedagogy and protocol-content audit

Date: 2026-07-22

## Scope and method

This is a read-only audit of six student-visible mini-protocols. It compares
their learning blocks, prompts, ordered interactions, state mutations, and
declared render states to the current protocol contract and the course-source
manuals. The audit does not amend a contract, specification, or curriculum
content.

Authority used:

- `docs/PRIMARY_CONTRACT.md` items 4--5: visible-UI completion and one focused
  learning block.
- `docs/PRIMARY_DESIGN.md`: each interaction should make the relevant object,
  action, state change, and next action visible.
- `docs/protocols/OVCAR8_Carboplatin_Metformin_MTT_Protocol.md` lines 115--140.
- `docs/protocols/SDS-PAGE_Protocol_2026.md` lines 248--265 and 386--392.

`Confirmed` means the discrepancy is directly evident from the repository's
own course manual, YAML, or object render declarations. `Faculty ratification`
means an exact procedural choice depends on the instructor's local method or
assessment intent.

## Findings by mini-protocol

| Protocol | YAML line(s) | Issue | Pedagogical impact | Confidence | Recommended correction |
| --- | --- | --- | --- | --- | --- |
| `mtt_reagent_prep` | `protocol.yaml:6-18, 21-143` | The learning block promises mass measurement on an analytical balance, but the interaction chain has no balance, tare, weighing, or 5 mg verification action. | Students can finish without practicing or demonstrating the stated quantitative skill; the lesson teaches a recipe claim rather than measurement. | Confirmed | Either add a visible weigh/tare/5 mg verification sequence and state change, or narrow the objectives/outcomes to using a pre-weighed vial. |
| `mtt_reagent_prep` | `protocol.yaml:42-44, 79-84, 91-117` | `prepare_solution_tube` asks the learner to add PBS *and mix until fully dissolved* before the following step transfers the powder. It also assigns the final MTT-solution material before powder transfer and mixing. | The causal sequence is backwards and the screen can show the finished reagent before its critical transformation. | Confirmed | Safe wording/order fix: make this step add 1 mL PBS to the empty tube; transfer 5 mg MTT next; then vortex/mix and only then change to `mtt_solution_12mm`. |
| `mtt_reagent_prep` | `protocol.yaml:141-155`; `mtt_solution_tube.yaml:19-29` | Final verification checks only volume, not powder mass, final concentration, or a visible dissolved-state result; the tube maps empty and filled states to the same asset. | A student can receive completion without evidence for the stated 12 mM readiness criterion, and cannot visually inspect the claimed outcome. | Confirmed | Validate the completed material identity plus 1 mL volume; add a visibly distinct dissolved/reagent presentation or an on-object readiness indicator. |
| `passage_hood_detachment` | `protocol.yaml:173-235`; `incubator.yaml:5-40` | The prompt says incubate at room temperature while the only timed target is an incubator whose default is 37 C / 5% CO2. | It teaches mutually incompatible environmental cues and conflates a timed wait with a CO2-incubator transfer. | Confirmed | Safe wording fix: say "allow trypsin to act for about 2 minutes, checking detachment" unless the locally approved method explicitly requires an incubator; if it does, state the actual conditions and visibly set them. |
| `passage_hood_detachment` | `protocol.yaml:174-175, 276-277`; `OVCAR8...md:43-50` | A T75 flask is taught with 3 mL trypsin and 9 mL media, while the source manual gives 3 mL for a 10 cm2 plate and 5 mL for a 15 cm2 plate, not a T75 flask. | An apparent vessel-volume mismatch can train a non-transferable recipe and makes the quantitative outcome unreliable. | Faculty ratification | Confirm the course's actual vessel and reagent volumes. Then make the flask label, volumes, and neutralization ratio agree with that approved method. |
| `passage_hood_detachment` | `protocol.yaml:31-37, 253-259`; `t75_flask.yaml:18-43` | Both microscopy checkpoints mutate state, but `inspection_status` is an empty composite and the flask asset is unchanged. The detachment confirmation additionally changes the material name without a visual cell-detachment state. | The learner is told to inspect a biological result but the UI does not reveal that result; success is click-through rather than visual interpretation. | Confirmed | Add a visible confluence/detachment visual state (or microscope image/overlay) and require the observation before allowing the return-to-hood action. |
| `mtt_solubilization_readout` | `protocol.yaml:11-14, 24-29, 57-67, 75-97` | The outcome says "individual wells" and the prompt describes an 8-channel walk across 12 columns, but one whole-plate click fans material into `all_wells`; the trituration step uses one click for roughly 960 aspirate/dispense motions. | The stated lab skill and the assessed UI action disagree; no column-by-column rhythm, tip position, or mixing completion is practiced. | Confirmed | Retain group operations for runtime efficiency, but expose a visible 12-column sweep/progress state and make the prompt say the simplified action represents it. If per-column technique is an assessment goal, author column-level interactions. |
| `mtt_solubilization_readout` | `protocol.yaml:76-79` | Formazan is called "yellow" during dissolution. The course manual identifies MTT as yellow and its viable-cell product as purple formazan crystals. | Students may invert reactant/product color meaning, undermining the assay's central visual inference. | Confirmed | Safe wording fix: "purple formazan crystals" (or a faculty-approved color description matching the actual assay chemistry). |
| `mtt_solubilization_readout` | `protocol.yaml:105-150`; `plate_reader.yaml:19-29` | The reader is changed to `reading: true` and immediately to `false` with no time, result, recorded value, or visibly distinct reading state. `optical_reading` is declared but never used. | The endpoint is framed as a quantitative measurement, yet no measurement becomes visible or available for downstream IC50 reasoning. | Confirmed | Add a visible run/result transition and persist a plate/well readout artifact; use the existing material only if it is semantically appropriate, otherwise add the approved state through the vocabulary process. |
| `sdspage_heat_denature_samples` | `protocol.yaml:60-111`; `heat_block.yaml:27-36` | The protocol changes lid and rack states, but both lid values resolve to `heat_block_closed`, and `rack_present` has an empty composite. It never changes sample material to `protein_sample_denatured`, although that material is declared. | The learner cannot see the lid, tube/rack placement, or denaturation outcome change, so the timed action feels decorative. | Confirmed | Supply open/closed and rack-present visual states; after the approved heat interval, update the relevant sample tubes/rack to the denatured state and show the completed timer. |
| `sdspage_heat_denature_samples` | `protocol.yaml:61-65`; `SDS-PAGE_Protocol_2026.md:264` | The explanation says BME-cleaved disulfides "cannot re-form at this temperature." Heating does not itself make disulfide reduction irreversible; BME/DTT maintains the reduced state under the sample conditions. | It reinforces a mechanistically incorrect causal explanation in a conceptually central SDS-PAGE step. | Confirmed | Safe wording fix: heat with SDS and reducing agent to denature proteins; the reducing agent maintains reduced disulfides during preparation. |
| `sdspage_image_gel` | `protocol.yaml:23-82`; `SDS-PAGE_Protocol_2026.md:386-392` | The final-rinse chain purports to pour material to waste, add ddH2O, and pour again, but every source/destination is represented by repeated tray/waste clicks. The tray state becomes empty before the waste click, and no transfer state is shown. | Learners cannot distinguish draining, adding, or disposing, so chemical-waste handling is modeled as an arbitrary click order. | Confirmed | Model each material transfer in its causal order and visibly update tray and waste states. Use the course-approved waste destination; the manual distinguishes appropriate containers and says the final brief rinse is after removing the gel. |
| `sdspage_image_gel` | `protocol.yaml:89-132`; `lightbox.yaml:19-32`; `staining_tray.yaml:44-49` | Power, tray-present, and image-captured state changes have no visible representation: lightbox false/true use the same asset and all relevant composites are empty. | The three most important imaging actions leave the same scene, removing consequence and "WOW" value. | Confirmed | Add visibly off/on illumination, a tray/gel-on-lightbox state, and a captured-image thumbnail or gallery artifact. |
| `sdspage_image_gel` | `protocol.yaml:90-121`; `SDS-PAGE_Protocol_2026.md:388-392` | The manual says to remove the gel from the staining tray, briefly rinse it, place the gel/tray flat on the lightbox, verify ladder/lanes, then photograph and save/label it. The mini-protocol has no lane-visibility check, camera action, or file-labeling consequence. | It reduces scientific documentation to a generic button press and omits quality control needed for interpretable images. | Faculty ratification | Decide whether this mini-protocol teaches image acquisition alone or archival documentation too; then add the appropriate visible quality check and capture/label artifact. |
| `sdspage_load_protein_ladder` | `protocol.yaml:53-66` | The tip-mount step targets a `p10_gel_loading_tip_box` while the prompt and attached instrument are a p200. | It creates a concrete tool/tip mismatch at the moment students should learn compatibility and loading precision. | Confirmed | Use the course-approved tip object for the p200, or rename/reconfigure the pipette and its stated range to match the tip system. |
| `sdspage_load_protein_ladder` | `protocol.yaml:118-141`; `gel_cassette.yaml:66-95` | The prompt teaches lane 5, but the interaction clicks the whole gel cassette; ladder and empty lane states map to the same asset and volume has an empty composite. | The student is not visibly required to aim at lane 5 and cannot see that ladder was loaded into the designated lane. | Confirmed | Target `gel_cassette.lane_5` directly and render lane occupancy/ladder appearance so the intended spatial skill and its result are both visible. |
| `sdspage_load_protein_ladder` | `protocol.yaml:10-16, 94-111`; `SDS-PAGE_Protocol_2026.md:264` | The source manual says the ladder is heated with prepared sample immediately before loading; this mini-protocol calls it protein ladder without asserting that it is the post-denaturation tube. | It can create a sequencing ambiguity between the denaturation and loading mini-protocols. | Faculty ratification | Define the runner handoff state explicitly: either label it "heat-denatured protein ladder" or state that this course uses an unheated prestained ladder, then align the heat and load mini-protocols. |

## Cross-cutting priority order

1. **Fix the visible-consequence gap first.** The heat block, lightbox, plate
   reader, flask inspection, and gel lanes all mutate state with no distinct
   render state. This directly violates the visible-flow design goal and makes
   otherwise-correct text feel broken.
2. **Then correct confirmed scientific wording and causal order.** The MTT
   powder/PBS sequence, purple formazan description, and BME explanation are
   safe, localized fixes.
3. **Ratify local-method choices before encoding them.** T75 volume, exact
   trypsin environment, ladder heating, and what counts as the final imaging
   record are instructor-method decisions, not safe assumptions.
4. **Make assessment match the promised skill.** When a mini-protocol claims
   measurement, visual inspection, multichannel technique, or lane targeting,
   the visible path must require and display that evidence.

## Checks performed

- `source source_me.sh && python3 validation/yaml_schema/content_lint.py --only yaml --no-color -q`
  - Exit 0: `Checked 168 files. 0 errors. 5 warnings. 0 advisories.` This
    confirms that the problems above are content/pedagogy/render-semantic
    issues rather than malformed YAML.

The protocol-selection form of `content_lint` did not resolve these nested
cluster paths and exited 1 without diagnostics; it was not treated as a result
about protocol quality.

## Residual risk

This is a static audit. It establishes that several authored state changes have
identical or empty declared visual states, but it does not substitute for the
required real-UI walkthrough screenshots. Before accepting fixes, run each
mini-protocol through the visible UI and capture before/after evidence for every
meaningful state change.
