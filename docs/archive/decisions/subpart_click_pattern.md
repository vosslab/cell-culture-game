# Subpart-click fix pattern decision

Decision: adopt direction A as the canonical MECHANISM. A protocol interaction
always clicks the BASE placement (the plate, rack, or gel that is itself a scene
object); the subpart name lives only inside the response (`ObjectStateChange`
target) or a `final_state_matches` field reference, never as the interaction
`target`.

GATE: direction A is spec-correct but it changes what the student DOES and can
drop subpart-level (well/lane/tube) specificity. So the 5-file rewrite is
gated on a pedagogy-owner review, per protocol, before fanout. Two of the five
preserve intent and are auto-apply-safe; two drop specificity that is written
into their own `learning` block and must get a pedagogy call first; one is
borderline. See the pedagogy layer below. M16 must not silently apply the
rewrite to a protocol whose taught skill is subpart discrimination.

## Owner decision (M16 closeout)

The owner made this a UNIFORM, class-wide ruling, decided once for consistency,
not a per-protocol call.

Ruling: any interaction-level `gesture: click` (or `select`) that targets a
DISCRIMINATION-BEARING subpart -- one the student must pick correctly among its
siblings (`tube_A..G`, a specific `lane_N`, a specific `well_XX` that receives a
distinct dose) -- stays HELD with a Direction-B RFC. This is the
discrimination-bearing subpart-group-click class. The held decision applies to the
class, not only to `plate_drug_treatment_drug_addition`.

- The class members are held because collapsing a discrimination-bearing subpart
  click to a base-placement click erases the taught skill (which dose in which
  well/row, which lane) written into each protocol's own `learning` block, and
  degenerates the UX to repeated identical base-object clicks.
- The rule is stated as a CLASS so it catches future members automatically: any
  new protocol that authors an interaction-level click on a
  discrimination-bearing subpart falls under it without a fresh ruling.
- `plate_drug_treatment_drug_addition` is today's ONLY member (and the canonical
  one: `dilution_tube_rack_8.tube_A..G` plus per-well dose mapping). M16 closes
  with the class held as an explicit, owned, documented known-red walker
  exception. Status is tracked as PEDAGOGY-HELD in
  [../../archive/audits/walker_click_bug_register.md](../../archive/audits/walker_click_bug_register.md)
  and [../../archive/audits/midwalk_sweep_triage.md](../../archive/audits/midwalk_sweep_triage.md).
- The durable resolution for the whole class is a future Direction-B RFC (stubbed
  below), owned by the ARCHITECT, not walker-plan or content work in this session.

EXCLUDED from the held class (NOT discrimination-bearing):

- `well_plate_96.all_wells` and any `subpart_group` bulk state-write
  (`mtt_plate_reaction`, `mtt_solubilization_readout`). These write the same state
  to every subpart at once; there is no correct-subpart choice to preserve. They
  are handled by runtime group-write support in a SEPARATE lane and follow the
  base-click rewrite recipe below. Do not fold `all_wells` into the Direction-B
  RFC.
- Protocols whose taught skill is not subpart discrimination even though the
  target is a single subpart (`sdspage_load_sample_single_lane`, where the graded
  skill is dispense technique, not lane picking) follow the base-click rewrite,
  not the held class. If the pedagogy owner later judges a specific single-lane
  protocol to teach lane discrimination, it joins the held class.
- The protocols already Direction-A-fixed (`drug_dilution_setup`, the `sdspage_*`
  loads, the `mtt` whole-object writes) are NOT in the discrimination class: they
  carry no subpart-discrimination pedagogy, so a base-placement click is the
  faithful gesture and they are already green. They are excluded because the class
  test (does the protocol grade WHICH subpart) does not match them, not as one-off
  exceptions.

The line is the TAUGHT SKILL, not the target shape: a subpart target is in the
held class only when picking the correct subpart is the discrimination the
protocol grades. Bulk group-writes and technique-only single-subpart steps are
outside it.

## Direction-B RFC (future work) -- OWNER: architect

This is a pointer/stub and a PROPOSAL TO THE ARCHITECT, not a full RFC and not
work this session or the walker plan implements. It reverses an architect-locked
pattern (subparts render `pointer-events: none` material overlays on purpose) and
touches the scene renderer plus scene YAML, so it must be owned and ratified by
the architect. Doing it reactively mid-close would destabilize the walker and
scene-manager plans at once.

Scope: give discrimination-bearing subpart overlays (`tube_X`, a specific
`well_XX`, `lane_N`) independent `[data-item-id]` click targets in the renderer
and the scene model, so `select` and `click` can address a specific subpart. This
preserves subpart-discrimination pedagogy (pick the correct well/lane/tube, map
different doses to different wells) that base-click cannot exercise.

- Reverses an architect-locked render contract: today subparts render as a
  `pointer-events: none` material overlay
  (`src/scene_runtime/renderer/subpart_visual_state_renderer.tsx`) with no DOM hit
  target of their own; the base placement is the only click target. Direction B
  changes that render/scene contract, which only the architect may authorize.
- Crosses into scene-manager / renderer territory; a separate future plan, not
  this session and not the walker plan.
- Gated by the PRIMARY_DESIGN new-primitive evidence bar (see the evidence
  criteria in "Does any subpart legitimately need to be independently clickable?"
  below): entered only through a ratified spec edit, never by an author editing
  YAML alone.
- EXCLUDES `all_wells` and `subpart_group` bulk writes: those are non-discrimination
  bulk state-writes served by runtime group-write in a separate lane, not by this
  RFC.
- Candidate protocols the RFC would serve: `plate_drug_treatment_drug_addition`
  (strongest, dose-to-well mapping) and any protocol whose learning block grades
  lane/well/tube discrimination (for example `sdspage_load_protein_ladder`'s
  "verify correct lane targeting" outcome).

## Scope

This decision covers the dominant M16 walker-FAIL cluster: five protocols that
author `gesture: click` directly on a `.<subpart>` target and therefore never
advance. It sets the canonical fix pattern an M16 coder applies to each, and
records why the alternative (making subparts independently clickable) is a
symptom patch, not a design fix. The human may override after; the documented
default is direction A now so M16 is unblocked.

Affected protocols (from
[walk_all_fail_triage.md](../../archive/audits/walk_all_fail_triage.md), dominant cluster):

- `mtt_plate_reaction` (`well_plate_96.all_wells`)
- `mtt_solubilization_readout` (`well_plate_96.all_wells`, three steps)
- `plate_drug_treatment_drug_addition` (`dilution_tube_rack_8.tube_A` plus
  `well_plate_96.<well>`, one occurrence per row, all eight rows)
- `sdspage_load_protein_ladder` (`gel_cassette.lane_5`)
- `sdspage_load_sample_single_lane` (`gel_cassette.lane_1`)

## The two candidate directions

- Direction A (protocol-YAML pattern): the interaction `target` is the base
  placement that IS a clickable scene object (`well_plate_96`, `gel_cassette`,
  the tube rack). The subpart (`well_plate_96.all_wells`, `gel_cassette.lane_5`,
  `dilution_tube_rack_8.tube_A`) is named only inside the response's
  `ObjectStateChange` target, or inside a `final_state_matches` field
  reference. The student clicks the object; the specific subpart is the effect,
  not the hit target.
- Direction B (runtime change): make subparts render their own `[data-item-id]`
  DOM node and become independent click targets.

## Why direction A is the design fix and B is the symptom patch

Direction A restores the contract the repo already holds; direction B changes
the contract to accommodate five miswritten protocols.

- PRIMARY_CONTRACT item 3 is explicit: custom geometry is allowed only for
  subparts INSIDE a structured scientific object (wells inside a plate, tubes
  inside a rack, lanes inside a gel). The structured object itself remains the
  YAML-declared scene object placed by the layout engine. The clickable scene
  object is the plate/rack/gel; the well/tube/lane is interior geometry, not an
  independently placed clickable object. Direction A honors this. Direction B
  promotes interior geometry to a top-level clickable scene object, which the
  contract reserves to the structured object.
- The well-plate-as-material model treats a plate as ONE object whose wells are
  per-well material overlays, exactly like a bottle's liquid fill. The subpart
  overlay renderer
  (`src/scene_runtime/renderer/subpart_visual_state_renderer.tsx`) states the
  contract in its own comments: the overlay is a separate `<svg>` with
  `pointer-events: none` that "never intercepts clicks: the base art under it
  stays the click target," and the click resolver reads back only a base
  `placement_name`, never a subpart-suffixed one. The subpart is a material
  effect surface, not an affordance. Direction A treats it that way.
- All twelve PASSING protocols already use base-placement clicks; ZERO author a
  subpart-suffixed `gesture: click`. The passing reference is
  `cell_seeding_plate_setup`'s `seed_96_well_plate` step: the interaction
  target is `well_plate_96` (base) and the response `ObjectStateChange` target
  is `well_plate_96.all_wells` (subpart). Direction A makes the five failing
  protocols match the working majority. The working pattern is the design;
  restoring it is the fix.
- SPEC_DESIGN_CHECKLIST layer ownership (rule 4, hidden semantic leakage; rule
  27, three-layer ownership) keeps protocol YAML semantic and scene structure
  out of the protocol layer. Under direction A the protocol names a semantic
  target (the object the student acts on) and the response names the affected
  subpart state; the render layer owns whether a subpart draws its own DOM.
  Direction B would make protocol authorability depend on a render-layer DOM
  decision, coupling the layers the checklist keeps apart.
- "Fix the design, not the symptom" (REPO_STYLE core philosophies) is decisive.
  The design already says base-clicks-only; the five protocols simply violate
  it. Direction A fixes the violation. Direction B rewrites a sound runtime and
  render contract to make an authoring mistake valid, expanding the clickable
  surface and the material-overlay model to paper over five files.

## Pedagogy layer: does base-click preserve each protocol's intent?

Spec-correctness (subparts are material overlays) settles the MECHANISM. It does
not settle the TEACHING. Retargeting "click well A1" to "click the plate" is a
different student action and drops well-level specificity. Whether that loss
matters is per-protocol: it hinges on whether the protocol's own `learning`
block teaches subpart DISCRIMINATION (pick the correct well/lane/tube) or a
whole-object action whose subpart is merely the recorded effect. Assessed from
each protocol's learning block and failing-step prompt:

| Protocol | Subpart target | What the learning block teaches | Base-click verdict |
| --- | --- | --- | --- |
| `mtt_plate_reaction` | `well_plate_96.all_wells` | Uniform whole-plate MTT dispensing with a multichannel pipette; the file header states the sim models "dispense MTT uniformly, not the per-column motion" | Preserves intent. Auto-apply-safe. |
| `mtt_solubilization_readout` | `well_plate_96.all_wells` (3 steps) | Uniform whole-plate DMSO addition; prompt: "each well receives the same 200 uL" | Preserves intent. Auto-apply-safe. |
| `sdspage_load_sample_single_lane` | `gel_cassette.lane_1` | Controlled dispense TECHNIQUE into a single lane (avoid bubbles/splash); lane discrimination is not the emphasized skill | Largely preserves intent (taught skill is the dispense). Borderline; likely auto-apply. |
| `sdspage_load_protein_ladder` | `gel_cassette.lane_5` | Outcomes EXPLICITLY include "verify correct lane targeting" and loading into a "designated lane (lane 5)" | Drops the lane-targeting outcome. NEEDS PEDAGOGY CALL. |
| `plate_drug_treatment_drug_addition` | per-well `well_plate_96.<well>` (all 8 rows) + `dilution_tube_rack_8.tube_A` | "Well-by-row targeted addition of variable-concentration drugs"; different wells/rows get different doses; the correct dose tube is the correct choice | Drops well/row/dose specificity AND degenerates to repeated identical plate clicks (12 per row). NEEDS PEDAGOGY CALL, strongest case. |

Two protocols (`mtt_plate_reaction`, `mtt_solubilization_readout`) teach a
uniform whole-plate action; the subpart is `all_wells` and base-click is a
faithful "act on the whole plate" gesture. Apply the rewrite directly.

`plate_drug_treatment_drug_addition` is the standout concern. Its whole point is
mapping different doses onto different wells and rows. Collapsing every per-well
interaction to a plate click both erases the "which dose in which well" teaching
and produces a degenerate UX: the student clicks the same plate object 12 times
per row with no visible distinction between clicks. `sdspage_load_protein_ladder`
similarly names "verify correct lane targeting" as an explicit outcome that a
plate-level click cannot exercise. These two must not be auto-rewritten; route
them to the pedagogy owner to decide between softening the outcome wording to the
object level or escalating subpart-picking to a direction-B RFC (below).

## Third candidate evaluated: the `select` gesture

The reviewer asked whether `select` (choose the correct next-step object among
present scene objects) is the right teaching gesture when a protocol needs the
student to pick a specific well/lane, rather than a bare base click. Evaluated
against the gesture vocabulary (PRIMARY_SPEC: `click` acts on a single directed
object; `select` chooses among present objects and "reuses the visible
scene-object click affordance; there is no answer-choice list"):

- `select` does NOT recover subpart specificity under the current model. A
  subpart is not an independently present scene object; it is a
  `pointer-events: none` material overlay with no `[data-item-id]` of its own.
  `select` reuses the same visible scene-object click affordance `click` does,
  so it can only choose among BASE placements. `select` on a plate resolves to
  the plate, exactly as `click` does; it cannot address `lane_5` or `B1` any
  more than `click` can.
- Therefore `select` vs `click` is a genuine teaching-gesture distinction only
  when there are multiple BASE placements to choose among (for example, pick the
  correct bottle among several bottles, or the correct instrument among several
  instruments). It is the right gesture for "choose the correct object" pedagogy
  at the object level.
- It is NOT a mechanism to regain well/lane/tube-level picking. Genuine
  subpart discrimination as a graded student choice requires the subpart to be an
  independently present clickable object, which is direction B (a future RFC),
  not `select`.

Net: `select` is available and correct for object-level choice, but it does not
solve the two "needs pedagogy call" protocols. Their real question is whether
subpart discrimination is essential teaching (escalate to direction B) or can be
expressed at the object level (rewrite plus soften the outcome wording).

## Rewrite recipe for an M16 coder

Apply the recipe only after the pedagogy gate clears the protocol.
`mtt_plate_reaction` and `mtt_solubilization_readout` are pre-cleared
(whole-plate uniform action). `sdspage_load_sample_single_lane` is borderline;
apply once the pedagogy owner confirms lane-picking is not the graded skill.
`sdspage_load_protein_ladder` and `plate_drug_treatment_drug_addition` are held
for a pedagogy call and are NOT auto-rewritten.

For every cleared interaction whose `target` is `<base>.<subpart>`:

1. Change the interaction `target` from `<base>.<subpart>` to `<base>` (the
   base placement that is a scene object). Keep the same `gesture: click` and
   the same interaction `validator` (`correct_target`).
2. Leave the subpart name exactly where it already appears in the response:
   the `ObjectStateChange` entries inside `response.scene_operations` keep
   `target: <base>.<subpart>` unchanged. Only the interaction `target` moves to
   the base; the response subpart target is already correct.
3. If a step's `step_validator` is `final_state_matches`, its field reference
   may keep naming the subpart (`<base>.<subpart>` field); that reference is a
   read, not a click, and is unaffected. No change needed there.
4. The walker then drives it with no walker change: it clicks the base
   placement's `[data-item-id]` (the plate/rack/gel), which is already a
   visible clickable scene object. No subpart DOM node is needed.

Worked example (`sdspage_load_protein_ladder`, step `dispense_into_lane_5`):

- Before: interaction `target: gel_cassette.lane_5`, response
  `ObjectStateChange target: gel_cassette.lane_5`.
- After: interaction `target: gel_cassette`, response
  `ObjectStateChange target: gel_cassette.lane_5` (unchanged).

Worked example (`well_plate_96`): interaction `target: well_plate_96.all_wells`
becomes `target: well_plate_96`; the response `ObjectStateChange target:
well_plate_96.all_wells` is unchanged. This reproduces the passing
`cell_seeding_plate_setup` shape exactly.

Per-protocol blast radius:

- `mtt_plate_reaction`: one interaction (`add_mtt_to_wells`).
- `mtt_solubilization_readout`: three interactions (three steps at the same
  pattern).
- `plate_drug_treatment_drug_addition`: widest. Apply to every one of its eight
  row-steps, BOTH the tube-rack click (`dilution_tube_rack_8.tube_A` -> base
  rack) and the per-well click (`well_plate_96.<well>` -> `well_plate_96`).
- `sdspage_load_protein_ladder`: one interaction (`dispense_into_lane_5`).
- `sdspage_load_sample_single_lane`: one interaction.

## Does any subpart legitimately need to be independently clickable?

Mechanically, no: every failing case is a "deposit material into a
well/tube/lane" action where direction A expresses the mechanism faithfully.
Pedagogically, two protocols raise the question, and the pedagogy owner decides
whether it rises to the direction-B evidence bar:

- `plate_drug_treatment_drug_addition` teaches mapping different doses onto
  different wells and rows. If subpart discrimination is judged essential
  teaching, this is the strongest candidate for independently-clickable wells and
  tubes. Note the additional degeneracy signal: base-click makes 12 identical
  plate clicks per row, which is poor UX independent of the pedagogy question.
- `sdspage_load_protein_ladder` names "verify correct lane targeting" as an
  explicit outcome, which a plate-level click cannot exercise.

Direction B stays a FUTURE RFC, gated by the PRIMARY_DESIGN new-primitive
evidence bar. It would need to show all of:

- existing primitives cannot express the behavior clearly (a base-click plus a
  subpart-targeted response demonstrably fails to teach the required skill,
  not merely reads less directly);
- the need appears across multiple protocols or scenes, not one bespoke step;
- the independently-clickable subpart is a stable, reusable semantic unit, not
  a one-off convenience.

`select` does not clear this bar for subparts: as evaluated above, it reuses the
same visible scene-object affordance and can only choose among present BASE
placements, so it cannot address a well or lane either. Genuine subpart-picking
requires promoting the subpart to an independently present clickable object,
which is direction B, entered only through a ratified spec edit, never by an
author editing YAML alone. The pedagogy owner's other option is to keep the
teaching at the object level and soften the affected outcome wording
(for example, "load the ladder into the gel" rather than "verify correct lane
targeting"), which keeps direction A and needs no new primitive.

## Note on a future load-time guard

A load-time guard that rejects `gesture: click` (and `gesture: select`) on a
`.<subpart>` target would have caught all five failures before any browser
session, matching the existing load-time invariant pattern
(`authored_value_check.ts`, `gesture_affordance_check.ts`). It fits the closure
principle: an unactionable authored click should fail loud once at load, not
trap a student mid-walk. This decision records the guard as a candidate only;
it does not build it. If ratified later, it belongs beside the other protocol
load-time checks and should name the offending protocol, step, interaction
index, target, and gesture, and point the author at the base-click pattern
above.
