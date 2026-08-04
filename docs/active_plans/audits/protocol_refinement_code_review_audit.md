# Protocol refinement code review audit

Six-pass independent code review of the uncommitted protocol-refinement change
(308 files, +22043 / -13573). Each section names the reviewer pass that produced
the finding so follow-up work can go back to the source evidence.

Reviewed against this goal: make the virtual laboratory protocols scientifically
accurate, physically plausible, pedagogically effective, and visually clear;
reorganize interactions around meaningful laboratory decisions rather than
interface clicks; maintain biological, material, vessel, and apparatus
continuity; verify through visible-UI walkthroughs without regressing existing
functionality.

Date of review: 2026-08-03. Working tree state at review time, not a commit.

## Gate status

| Gate | Before review | After the two fixes below |
| --- | --- | --- |
| `pytest tests/` | 2 failed, 6162 passed | 6163 passed, 0 failed |
| `node --import tsx --test 'tests/test_*.mjs'` | 658 tests, 0 fail, 690 ms | unchanged |
| `./check_codebase.sh` | PASS (5 checks) | unchanged |
| `./run_validate.sh` | 0 errors, 22 warnings, 117 advisories | unchanged, but see H3 |
| `tests/playwright/test_pedagogy_outcomes.spec.ts` | 5 passed | unchanged |
| Full Playwright suite (~105 tests) | NOT RUN | NOT RUN |

## Fixes already applied

Two blockers were fixed during the review. Everything else in this document is
open.

### F1. Dangling markdown link to the deleted object

`docs/active_plans/audits/protocol_pedagogy_visual_audit.md:93-95` linked
`content/objects/pipette/micropipette.yaml`, which this change deletes. That
failed `tests/test_markdown_links.py`. Rewritten as a backticked path with a
"(since retired)" note. Found independently by the test, docs, legacy, and plan
passes.

### F2. Bandit B314 in a new test

`tests/test_mtt_readout_visibility.py:24` used `xml.etree.ElementTree.parse`,
tripping `tests/test_bandit_security.py`:

```
B314 [MEDIUM/HIGH] line 24: Using xml.etree.ElementTree.parse to parse untrusted
XML data is known to be vulnerable to XML attacks. Replace with defusedxml.
```

Switched to `lxml.etree`, which is already a declared dependency and the pattern
every other SVG-parsing site uses (`tools/svg_liquid_census.py:20`). No `nosec`
suppression added.

While in that file, `test_mtt_displayed_percentages_match_the_visible_blank_corrected_values`
was deleted. It computed `1.00 - 0.08`, `0.28 - 0.08`, `0.17 - 0.08` from
literals defined inside the test body and asserted its own arithmetic, so it
verified nothing about the repository and would pass forever regardless of
authored values.

Reviewer disagreement on record: the test pass recommended deleting the whole
file as redundant with `tests/playwright/test_pedagogy_outcomes.spec.ts:194-220`;
the legacy pass recommended only the `lxml` swap. The smaller reversible action
was taken. Deleting the remaining test is still a live option.

## Decisions needed from the owner

These three are not mechanical fixes. They gate a clean sign-off.

### D1. Is `select`-as-choice-cards approved?

See H1. The gesture contract was re-declared resolved in a spec file while the
change's own resolution ledger lists it as unresolved and requiring approval.

Supporting history, which sharpens rather than settles the question:

- `docs/archive/decisions/subpart_click_pattern.md:209-238` concluded that
  `select` versus `click` IS a genuine distinction, correct for choosing among
  multiple BASE placements (the right bottle among several bottles). The same
  section proved `select` CANNOT recover subpart specificity, because a subpart
  is a `pointer-events: none` overlay with no `[data-item-id]`, so `select` on a
  plate resolves to the plate exactly as `click` does.
- `docs/specs/PROTOCOL_AUTHORING_GUIDE.md:432-434` states the live rule: a
  decision uses `select`, a scene-object action uses `click`, and a skill must
  not collapse into a rote `click`.
- The only retirement language on record is OQ-8 in two archived plans
  (`docs/archive/unified_interaction_vocabulary_plan.md:1505`,
  `docs/archive/protocol-step-vocab-refinement-plan.md:1411`), both reading
  "`select` may later collapse into `click`" and both marked watch item, not
  blocking. No decision record retires `select`.

So the open question is NOT whether both gestures are needed. It is whether 33
purpose-built decoration cards, all rendering one shared
`interpretation_choice_card` asset and placed in dedicated review scenes,
constitute a legitimate realization of `select` or a re-entry of the answer-choice
list that `docs/PRIMARY_SPEC.md:101` explicitly closes.

#### Options

**Option A: ratify choice cards.** Amend `docs/PRIMARY_SPEC.md:101` to say
`select` chooses among present scene objects INCLUDING authored decision objects,
and keep `GESTURE_MODEL.md` as rewritten.

- Pro: zero content churn; 17 working `select` interactions stay; the pedagogy
  they encode (interpret evidence, then commit to a conclusion) is the single
  biggest gain in this change.
- Pro: makes the shipped implementation and the spec agree immediately.
- Con: amends a contract line, so it needs explicit approval under
  `docs/PRIMARY_CONTRACT.md`, not a silent edit.
- Con: removes the only barrier against a future MCQ modal re-entering as
  "decoration objects". Needs a replacement fence, for example "a choice object
  must depict laboratory evidence, never a lettered or numbered answer option".

**Option B: revert the spec, keep the content pending review.** Restore
`GESTURE_MODEL.md` to HEAD; leave the 17 interactions in the tree as the evidence
package for a separate decision.

- Pro: restores the honest state, where the ledger's B6 and the specs agree that
  the contract is open.
- Pro: cheapest immediate action; one file revert.
- Con: ships content that the spec says is unsettled, which is the same
  inconsistency pointed the other way.
- Con: defers the decision without reducing it.

**Option C: reclassify the cards as a distinct object kind.** Introduce an
explicit `kind` for evidence-interpretation objects rather than overloading
`decoration`, and define `select` against that kind.

- Pro: resolves D1 and D2 together with one vocabulary edit; the closure rules
  get stronger rather than weaker.
- Pro: makes the "is this an MCQ" question answerable by schema instead of by
  reviewer judgment.
- Con: largest edit. Touches the object vocabulary, the validator, and all 33
  objects.
- Con: adds a top-level category, which `docs/PRIMARY_DESIGN.md` asks to avoid
  unless composition genuinely cannot express the behavior.

Recommendation: Option A with the explicit anti-MCQ fence, because the underlying
pedagogy is sound and the 17 interactions already have walker evidence. Option C
is the better long-term shape if the choice-object family keeps growing past the
current 33.

### D2. Amend the decoration rule, or strip the field from 42 objects?

See H2. Leaving it as-is makes the spec's "build-time error" language false for a
quarter of the object library, so doing nothing is not one of the options.

#### Options

**Option A: amend the spec to match the content.** Rewrite
`docs/specs/OBJECT_YAML_FORMAT.md:275` to say a decoration carries no MATERIAL
state but may declare non-material fields such as `visible`, and relax `:455` to
require only an empty material schema. Note `kind: decoration` is orthogonal to
the `decoration_only` capability.

- Pro: no content churn across 42 files.
- Pro: the `visible` field is genuinely useful for objects that should appear
  conditionally, even though nothing writes it today.
- Con: legitimizes 44 stubs whose `true` and `false` branches resolve to the same
  asset (M7). The spec would sanction a field that cannot change anything.
- Con: weakens a closure rule without a behavior that needs the room.

**Option B: strip the field and implement the missing check.** Remove `visible`
from all 42 objects, then add the empty-`state_fields` and empty-`visual_states`
checks to `validation/yaml_schema/object_validator.py` so the documented rule is
finally enforced.

- Pro: makes the spec true and machine-checked, closing the gap that let this
  drift ship green.
- Pro: deletes 44 dead stubs outright.
- Con: `validation/yaml_schema/constants.py:46` currently makes `state_fields`
  and `visual_states` REQUIRED object keys, so the schema must first learn to
  accept a stateless object. That is the real work.
- Con: touches 42 files plus the validator plus the constants module.

**Option C: convert the stubs to the one-value enum idiom.** Leave the schema
alone and rewrite the 38 bool stubs into the shape this same change already ships
at `content/objects/equipment/calculation_pad.yaml:6-9`.

- Pro: smallest honest fix; satisfies `_validate_visual_states_completeness`
  identically, so no validator or schema change is needed.
- Pro: removes the two-competing-shapes problem in M17 at the same time.
- Con: does not resolve the spec contradiction at line 275, since a one-value
  enum is still a non-empty `state_fields` list. The spec still needs amending.
- Con: leaves the missing validator check unwritten, so the next drift of this
  class also ships green.

Recommendation: Option C now for consistency, then Option B as the durable fix
once the schema can express a stateless object. Option C alone leaves the spec
still lying, so it is a stepping stone rather than a resolution.

### D3. Is the 37-gesture single step intentional?

See H4.

#### Options

**Option A: split into three steps, one per sample tube.**

- Pro: a retry costs one sample instead of three, which is the whole complaint.
- Pro: matches the granularity of `passage_hood_detachment` and
  `trypan_blue_counting`, both 9 steps for comparable work.
- Con: three near-identical steps may read as repetitive in the YAML.
- Con: changes step count, so any test or doc asserting the current count needs
  updating. See M2 for the `len(leaves) == 16` style of assertion that breaks on
  exactly this kind of edit.

**Option B: keep one step, add per-interaction checkpointing.** Change the
failure semantics so a wrong gesture resets only the current sample rather than
the whole sequence.

- Pro: preserves the authored pedagogy that batch preparation is one continuous
  technique.
- Con: `outcome` has exactly two keys and `on_failure: retry` restarts the whole
  `sequence` by definition in `docs/PRIMARY_SPEC.md`. Partial retry is a new
  runtime semantic, so this is a contract change, not a content edit.
- Con: highest implementation cost of the three.

**Option C: accept as authored and record why.** Add a rationale comment naming
the batch-technique intent, and close the audit item as a deliberate pedagogy
call.

- Pro: zero code change; some real batch protocols genuinely are one continuous
  technique.
- Con: a 37-gesture retry is a punishing learner experience regardless of intent,
  and the change's own goal text calls for granularity consistency.
- Con: leaves `sdspage_load_samples_batch` and
  `plate_drug_treatment_drug_addition` in the same unresolved bucket.

Recommendation: Option A. The pedagogy argument for one continuous batch does not
survive the retry cost, and Option B needs a contract change to deliver the same
outcome.

## Suggested resolutions for the remaining high findings

D1 through D3 above cover H1, H2, and H4. The rest have a clear recommended path
with a named tradeoff.

### H3, validate not reproducible from clean

- **Recommended: make `validation/validate.py` fail loudly on stale or absent
  generated state.** Pro: a clean checkout gets an honest, actionable failure
  instead of a silent regeneration, and the gate record becomes trustworthy. Con:
  every contributor must now run the build and render steps before validate, so
  the workflow gains a required prerequisite.
- Alternative: correct the `run_validate.sh:3-9` header to admit it regenerates.
  Pro: one-line fix. Con: keeps a validator that mutates the tree it validates,
  which is what made the failure unreproducible in the first place.

### H5, machine-rewritten protocol YAML

- **Recommended: re-author both files by hand in the corpus format and restore
  the four deleted rationale comments.** Pro: recovers the runner-handoff
  rationale, which is exactly the kind of knowledge that is expensive to
  reconstruct later. Con: manual work on two large files, and the diff will be
  noisy.
- Alternative: dump all 31 protocols through the same serializer so the corpus is
  at least uniform. Pro: consistency by construction. Con: destroys comments in
  29 more files to fix 2, which trades a local problem for a repo-wide one.
  Not recommended.

### H6, undocumented author-facing errors

- **Recommended: document the three rules where authors will hit them.** Add a
  "Reserved terminology and tool authenticity" subsection to
  `docs/specs/PROTOCOL_AUTHORING_GUIDE.md` naming the accepted replacements
  (draw, load, pipette up); fix `PROTOCOL_VOCABULARY.md:569-571`; add the codes to
  `docs/VALIDATION_JSON_SCHEMA.md:83-101`. Pro: closes the trap where the spec
  tells an author to write something the validator rejects. Con: documentation-only
  work with no test to keep it in sync.
- Consider alongside: derive the hardcoded pipette list from `kind: pipette`
  objects (M15) so the rule cannot silently miss a newly authored pipette.

### H7, SVG attribution gap

- **Recommended: add the 61 missing rows to `assets/equipment/SOURCES.md`, and
  confirm the Servier-derivative provenance for the micropipette family.** Pro:
  this is a CC BY 3.0 obligation, not bookkeeping, so it is the one finding with a
  legal dimension. Con: needs the actual provenance for each asset, which may
  require asking whoever generated them.
- Follow-on: teach `validation/svg/asset_audit.py` to fail on an asset with no
  SOURCES row, rather than reporting "unknown" with 0 errors. Pro: prevents the
  next 61. Con: will fail immediately on the 40 pre-existing orphans until those
  are triaged too.

### H8, two dead tools

- **Recommended: delete both, and remove their rows from
  `docs/FILE_STRUCTURE.md` and `docs/CODE_ARCHITECTURE.md`.** Pro: they cannot
  run at all, so there is no behavior to preserve; AGENTS.md is explicit that git
  history is the archive. Con: none identified. This is the cheapest high-value
  cleanup in the list.

### H9, orphaned P200 statics

- **Recommended: delete both SVGs and drop lines 57-58 from the
  `EXPECTED_ANCHORED_FLEET` tuple in `tools/svg_liquid_census.py`.** Pro: removes
  a misleading pair where `_filled` is byte-identical to `_empty`. Con: none,
  provided the census tuple is updated in the same patch, or the tool will
  reference missing files.
- Consider bundling with the L-level `p10_micropipette_filled.svg` orphan and the
  broader question of whether `tools/svg_liquid_census.py` should survive at all
  (see the low findings).

## High findings

### H1. The `select` contract shipped ahead of its approval gate

Pass: plan auditor, corroborated by docs and style passes. Severity: high.

`docs/specs/GESTURE_MODEL.md` was rewritten in this change. The pre-change file
carried a "Reopened `select` decision" whose step 7 read: "Obtain explicit owner
approval, then update PRIMARY_SPEC.md, the protocol vocabulary, schema, interface
vocabulary, runtime, walker, and tests together", closing that "new production
`select` content would depend on an unsettled contract."

This change deletes that section, reclassifies `select` as "Implemented and
visible-walker-proven" reaching "curriculum proof", and ships 17 authored
`select` interactions. No approval is recorded in the diff.

Three-way contradiction:

- `docs/PRIMARY_SPEC.md:101` (higher authority, UNTOUCHED by this change):
  `select` chooses "among the scene objects already present ... there is no
  answer-choice list".
- The new `GESTURE_MODEL.md`: "Clickable rendered choice cards".
- `docs/active_plans/reports/protocol_pedagogy_visual_resolution.md:93` (B6):
  the select contract is unresolved and "New authoring semantics require user
  approval under PRIMARY_CONTRACT.md".

The spec edit and the ledger cannot both be true.

Smallest fix: revert `docs/specs/GESTURE_MODEL.md` to HEAD and leave the 17
`select` interactions in place as evidence for the owner's decision. Re-land the
doc change only with recorded approval.

### H2. 42 decoration objects contradict an unamended spec rule

Pass: plan, style, docs, and legacy auditors independently. Severity: high.

Three normative lines:

- `docs/specs/OBJECT_YAML_FORMAT.md:275` -- `kind: decoration`: "Static visual;
  no material state; `state_fields` must be empty".
- `docs/specs/OBJECT_YAML_FORMAT.md:455` -- `capabilities: [decoration_only]`
  requires that "the object's `state_fields` list is empty and the
  `visual_states` mapping is empty".
- `docs/specs/OBJECT_YAML_FORMAT.md:457` -- "A capability declared without its
  required schema is a build-time error."

Measured: 42 of 42 files in `content/objects/decoration/` declare a state field;
this change adds 34 of them. Eight objects declare `decoration_only`, six of
them new here (`content/objects/decoration/recycle_buffer_funnel.yaml` plus the
five `content/objects/equipment/*_display.yaml`), and all declare both a
`visible` state field and non-empty `visual_states`, violating both halves of
line 455.

Why it ships green: the rule has no validator behind it.
`validation/yaml_schema/object_validator.py:279-289` implements only the narrower
"a decoration must not declare material fields" check and returns early at line
289. Lines 378-386 check only that `decoration_only` is mutually exclusive with
other capabilities. Neither empty-`state_fields` nor empty-`visual_states` exists
in code, so validate reports zero YAML errors while 42 objects contradict the
spec.

`docs/specs/OBJECT_YAML_FORMAT.md` WAS edited in this change, but only its
serological-pipette sections. Line 275 is untouched, so content now contradicts
an unchanged normative line rather than following an approved amendment. That is
the vocabulary-widening-by-content pattern
`docs/specs/SPEC_DESIGN_CHECKLIST.md` exists to catch.

Note the change FIXED this same violation in
`content/objects/decoration/micropipette_tip_box.yaml` (flipping
`[decoration_only]` to `[clickable, cursor_attachable]`, justified for the
fresh-tip steps) and then reintroduced it in the new
`recycle_buffer_funnel.yaml`. The pattern was recognized, then repeated.

Pre-dates the change at 8 objects; this change scales it five-fold.

### H3. `./run_validate.sh` is not reproducible from a clean tree

Pass: plan auditor, confirmed by the style pass. Severity: high.

First invocations report `SCENE-LINT: Checked 11 scenes. 11 errors` and
`TOTAL: 11 errors ... FAIL`. Every later invocation reports `0 errors ... PASS`
with no edits between. `ls -la generated/` shows every artifact rewritten at the
timestamp of the first invocation, though `run_validate.sh:7` states "This script
validates only: it never renders scenes or parses PNG pixels."

Consequence: a clean checkout sees FAIL first, and the "gates passed" record in
the resolution ledger only holds after a warm-up run.

The style pass reached the same wall from the other direction and initially
reported 11 SCENE-LINT errors, clearing only after running
`bash build_github_pages.sh` then `node tools/scene_to_png.mjs --all`, the
sequence documented at `run_fast_checks.sh:136-148`.

Smallest fix: make `validation/validate.py` fail loudly on stale or absent
generated state instead of silently regenerating, or correct the
`run_validate.sh:3-9` header to say it regenerates. Either way the ledger's gate
record needs re-running from clean.

### H4. Under-atomization survived in `sdspage_prepare_sample_mix_batch`

Pass: plan auditor. Severity: high.

`content/protocols/sdspage/sdspage_prepare_sample_mix_batch/protocol.yaml:22-183`
is a single `step_name: prepare_batch` carrying 37 gestures that cover three
complete sample preparations, with `step_validator: sequence_complete` and
`outcome: { on_failure: retry }`. A wrong click at interaction 36 resets all 35
correct prior actions.

The audit named this protocol directly
(`docs/active_plans/audits/protocol_pedagogy_visual_audit.md:122-134`) and
`docs/PRIMARY_SPEC.md` calls under-atomization review-gated. The resolution
ledger marks granularity Resolved.

For comparison, `passage_hood_detachment` uses 9 steps and
`trypan_blue_counting` uses 9 steps for comparable work.

Milder instances: `sdspage_load_samples_batch` (1 step, 13 gestures),
`plate_drug_treatment_drug_addition` (3 steps, 29 gestures over ~1100 lines).

Smallest fix: split `prepare_batch` into three steps, one per sample tube, so a
retry costs one sample instead of three.

### H5. Two protocol YAML files were machine-rewritten by a dumper

Pass: style auditor. Severity: high.

`content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml`
and
`content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml`
were round-tripped through a default YAML serializer:

- Comments deleted. Both now carry zero `#` comments; siblings keep theirs
  (`mtt_reagent_prep/protocol.yaml` has 4). Lost rationale includes the
  runner-handoff note: "Direct play starts after Day-1 seeding and working-stock
  preparation. In cell_culture_full the runner owns this same handoff and
  ignores these seeds."
- Block scalars mangled. `objectives: >` folded scalars became single-quoted
  one-liners with a synthetic trailing blank line and a dangling quote on its own
  indented line (`.../drug_addition/protocol.yaml:60-62`).
- Indentation diverged. These are the only 2 of 31 protocols with zero-indent
  list items (`.../drug_addition/protocol.yaml:64`, `- step_name:` at column 0)
  against two-space everywhere else.
- Flow mappings expanded. `state: { material_name: media, material_volume: 469.58 }`
  became three block lines, against corpus style.

Smallest fix: re-author both files by hand in the corpus format and restore the
four deleted rationale comments.

### H6. Three new author-facing hard ERRORs ship undocumented

Pass: docs auditor, corroborated by the plan pass. Severity: high.

`validation/yaml_schema/protocol_validator.py:590-694` adds three hard errors:

- `loading_aspirate_wording` / `scientific-terminology`: a prompt containing
  "aspirat" is rejected unless the step targets `aspirating_pipette` with no
  dispensing pipette.
- `generic_micropipette` / `scientific-tool-selection`: `target: micropipette`
  is rejected.
- `serological_setpoint` / `scientific-tool-selection`: `adjust` on
  `serological_pipette`, or writing `set_volume` to it, is rejected.

`grep -rn` for all five tags and codes across `docs/` returns nothing.
`docs/specs/PROTOCOL_AUTHORING_GUIDE.md` contains no occurrence of "aspirat".

Worse, `docs/specs/PROTOCOL_VOCABULARY.md:569-571` still lists `aspirate`
unrestricted among ratified interaction-level verbs, so an author following the
spec writes `aspirate` and hits a hard build error with no documentation.
`PROTOCOL_VOCABULARY.md` WAS edited in this change, so this is an omission
rather than untouched drift. That same line also still reads "`select`
(answer)", which supports the presented-choice reading and reinforces H1.

The plan pass judged the three rules themselves IN SCOPE, each traceable to an
audit finding (aspirate wording to audit line 67, the other two to audit lines
258 and 265). Locking a content fix behind a lint is the right shape. The defect
is purely the documentation gap.

Smallest fix: add a "Reserved terminology and tool authenticity" subsection to
`docs/specs/PROTOCOL_AUTHORING_GUIDE.md` naming the accepted replacements (draw,
load, pipette up); correct `PROTOCOL_VOCABULARY.md:569-571`; add the codes to
`docs/VALIDATION_JSON_SCHEMA.md:83-101`.

### H7. Attribution gap: 61 of 67 new SVGs missing from SOURCES.md

Pass: docs auditor. Severity: high.

Six new SVGs were added to `assets/equipment/SOURCES.md` in this change (the five
display SVGs plus `recycle_buffer_funnel.svg`). Missing:
`interpretation_choice_card.svg`, `calculation_pad.svg`, all electrophoresis
lead, dam, and chamber states, all `gel_cassette_*` states, `gel_migration_*`,
`hemocytometer_*`, `lightbox_*`, `microscope_field_*`, p1000 and p20
micropipettes, `p200_micropipette_loaded/unloaded`, `reagent_reservoir_*`,
`repeat_dispenser_*`, `serological_pipette_pack_*`, `centrifuge_balance_tube_*`,
`hazardous_liquid_waste_*`, `well_plate_formazan_crystals.svg`, and the
`plate_reader_*` and `cell_counter_manual_*` panels.

Some are plausibly Servier derivatives (`p1000_micropipette_empty.svg` sits next
to already-listed Chemistry/Servier rows at `SOURCES.md:30-31`), which makes this
a CC BY 3.0 attribution gap, not just bookkeeping.

`validation/svg/asset_audit.py` treats SOURCES.md as the provenance manifest and
reports "unknown: 109 objects" with 0 errors, so nothing catches it.

### H8. Two fully dead tools

Pass: legacy auditor. Severity: high.

`tools/build_probe.sh` guards at line 25 on `src/shell/_probe.tsx`, which does
not exist, so the script exits 1 on every invocation. It self-describes at line 6
as "a one-time verification step (WP-1-2)".

`tools/build_test_fixture.sh` has two broken entry points: line 25 targets
`tests/playwright/fixtures/`, which does not exist, and line 37 bundles
`src/scene_runtime/adapters/well_plate/index.ts`, which does not exist. It also
emits `window.adapterExports` for `file://` loading at line 52, against the
ESM-only rule in `docs/TYPESCRIPT_STYLE.md`, and its whole purpose is building
`tests/playwright/fixtures/`, which the no-fixture policy forbids.

Neither has a caller. `grep -rln` across shell, JSON, Python, mjs, and Markdown
(excluding `node_modules` and `docs/archive`) returns only the files themselves
plus `docs/FILE_STRUCTURE.md` and `docs/CODE_ARCHITECTURE.md`.

Smallest fix: delete both per the AGENTS.md rule that git history is the archive,
and remove their rows from the two docs. Both are `tools/` dev-only helpers, so
no `pipeline/` doc obligation is triggered.

### H9. Newly orphaned P200 static assets

Pass: legacy auditor. Severity: high.

`content/objects/pipette/p200_micropipette.yaml:60-88` was rewritten in this
change from `p200_micropipette_empty` / `_filled` to the new
`binary_state/p200_micropipette_unloaded` / `_loaded`. The two statics
`assets/equipment/static/p200_micropipette_empty.svg` and `..._filled.svg` now
have no object consumer, and they are byte-identical to each other (md5
`2b6e5fd1`), so `_filled` never conveyed "filled".

Remaining references are stale bookkeeping: the hardcoded
`EXPECTED_ANCHORED_FLEET` tuple at `tools/svg_liquid_census.py:57-58`, and
inline synthetic test data at
`tests/test_object_validator_variant_collapse.py:334-336` (fine as-is, it is
invented input rather than a file read).

Smallest fix: delete both SVGs and drop lines 57-58 from the census tuple.

## Medium findings

### M1. Ambiguous gesture sources in recovery copy

Pass: comment auditor. Severity: medium. Highest-value missing comment in the
change.

`src/shell/regions/guidance_bar.tsx:50-87` -- `recovery_copy` reads two different
gesture sources in adjacent switch arms. The `wrong_target` arm (57-73) branches
on the new `expected_gesture` parameter, meaning the gesture the learner SHOULD
perform next. The `wrong_value` arm six lines below (74-81) branches on
`rejection.gesture`, meaning the gesture the learner DID perform. Both are called
"gesture" and nothing explains the asymmetry. A future editor will unify them and
silently change learner copy.

Related: the new signature adds two defaulted positional parameters of the same
shape (`expected_label`, `expected_gesture`), so a transposed call would be
invisible. Consider an options object.

### M2. Fragile pytests recommended for deletion

Pass: test auditor. Severity: medium. Default action is removal, per
`docs/PYTEST_STYLE.md`.

`tests/test_sds_subpart_geometry.py` (267 lines) is a Python transcription of
authored YAML. Delete six of its eight tests:

- `:32` exact viewBox dict; `:34,35,47-50` exact pixel geometry (x 36.0, y 33.0,
  w 11.0), which are tunable layout constants.
- `:74` `len(leaves) == 16` AND `:78` `"16 focused mini-protocols" in
  learning["goals"]`. Adding one mini-protocol breaks it twice, once against
  prose.
- `:97-108` exact float ledgers (0.9925, 0.9985, 21, 30).
- `:142-146` an exact 9-element ordered list of target and `set_volume` pairs.
- `:237-246` exact whole-dict equality on a 9-field state write.
- `:258-259` funnel zone equals "rear_left" and depth_tier equals 2, which is
  pure scene-layout tuning asserted as correctness.
- `:247-249` raw `.read_text()` substring match on a scene YAML.
- `:223,231,262,264` step_name and next_step string equality.

Worth keeping: the lane-region shape checks at `:36-37` minus exact coordinates,
and the genuine pipette-range property at `:147-149`
(`field["min"] <= value <= field["max"]`) minus the literal setpoint list.

`tests/test_cell_culture_transfer_ledgers.py:54-81` -- `:78` asserts
`mix_cycles == [1,2,3]` (exact ordered tunable), `:81` asserts "strictly greater
than 90%" appears in a prompt (exact authored prose), plus four step_name dict
keys, a nested helper with logic in the test body (`:63-69`), and six assertions
in one function. The same behavior is covered visibly at
`tests/playwright/test_pedagogy_outcomes.spec.ts:108-142`. Delete this one test;
the other three in the file are sound.

`tests/test_protocol_initial_state.py:123-174` -- four try/except/else blocks
asserting on error MESSAGE substrings ("duplicate constituent", "direct
mini_protocol leaves", "non-empty", "missing mini-protocol"). Rewording any
generator error breaks them, and the control flow is complex for a test body.
The tag-based assertions elsewhere in this file are the correct shape and should
be preserved.

`tests/test_sds_subpart_geometry.py:81-89` -- the `_state_write` helper carries
`assert len(matches) == 1`, so a content edit surfaces as an opaque helper
failure. Moot if the file is trimmed.

### M3. Pytest fast lane is roughly half repeated content-tree loads

Pass: test auditor. Severity: medium.

About 7.4 s of the 15.2 s suite is repeated full content-tree loads.
`validation/stepper/loader.py:111` `load_content_tree` has no caching, and
`tests/test_protocol_initial_state.py:13-17` rebuilds `ContentDatabase` per test.

Measured with `--durations`:

| Duration | Test |
| --- | --- |
| 0.74 s | `test_cell_culture_mtt_content.py::test_mtt_assay_states_and_readout_are_visible_and_executable` |
| 0.72 s | `test_media_adjustment_conservation.py::test_media_adjustment_is_executable_directly_and_in_its_runner_context` |
| 0.54 s | `test_cell_culture_transfer_ledgers.py::test_direct_cell_transfer_protocols_complete_without_stepper_errors` |
| 0.50 s | `test_plate_drug_addition_ledger.py::test_drug_addition_completes_with_valid_tip_and_material_state` |
| 0.42-0.44 s each, 12 tests, ~5.0 s total | `test_protocol_initial_state.py` |

All exceed the "well under one second" budget in `docs/PYTEST_STYLE.md`.

Cheapest durable fix: a module-level ALL_CAPS cached loader in
`test_protocol_initial_state.py`, sanctioned by `docs/PYTHON_STYLE.md`,
recovering about 4.6 s. Consolidating the four separate "walk protocols, expect
no ERROR findings" tests into one recovers another 1.5 s with no coverage loss.

### M4. E2E-shaped work sitting in the pytest lane

Pass: test auditor. Severity: medium.

The four stepper-walk tests are in-process integration runs over the entire
production content tree; nothing else in `tests/` does that. No subprocess and no
network, so they are not clear-cut E2E, but per `docs/E2E_TESTS.md` the whole
class is a defensible move to `tests/e2e/`. The test pass recommends
consolidate-to-one rather than move, since they are the strongest correctness
signal in the batch.

Separately, `tests/test_entity_decode.py:78-89` rglobs every `content/*.yaml` --
a repo-hygiene scan that bypasses the canonical `file_utils.discover_files` API
and writes no `report_*.txt`, contrary to the "Hygiene file discovery" section of
`docs/PYTEST_STYLE.md`. Its regex `r"\bu(?:M|L)\b"` also fires on ordinary prose.
Move it into a proper hygiene module or delete it.

### M5. The `s-unused` validator never counts `initial_state`

Pass: legacy auditor. Severity: medium.

`validation/stepper/scene_ops.py:463-466` is the only call site of
`track_referenced_material` in the repository (`grep -rn
"track_referenced_material" validation/` returns that line plus the definition at
`validation/stepper/findings.py:184`). It fires only inside `ObjectStateChange`
scene-op validation, so the `initial_state` seeding path never registers a
material and `validation/stepper/step_check.py:131-146` computes
`declared_keys - referenced_materials` against an incomplete reference set.

Proof: `formazan_carboplatin_0_1umol` is reported "declared but never
referenced" in `mtt_solubilization_readout`, yet
`content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml:11`
seeds it.

Masked versus genuine breakdown of the 77 advisories:

| Protocol | s-unused | Verdict |
| --- | --- | --- |
| `mtt_solubilization_readout` | 18 | False positive; all 18 seeded via `initial_state` |
| `sdspage_assemble_electrode_module` | 14 | Genuine; `initial_state` sets only `lid_present` / `module_present` |
| `sdspage_prepare_gel_cassette` | 14 | Genuine; no `initial_state` at all |
| `sdspage_prepare_running_buffer` | 11 | Genuine; uses 3 of 14 |
| 15 other protocols | 20 total | Not individually triaged |

Roughly 39 genuinely dead declarations sit behind 18 or more known false
positives. The noise is what let the dead ones survive.

Smallest fix: call `emitter.track_referenced_material` for `material_name` and
`held_material_name` while walking `initial_state` in
`validation/stepper/runner.py`.

### M6. Copy-pasted `materials.yaml` boilerplate

Pass: legacy auditor. Severity: medium. Do this after M5 so the advisory list is
trustworthy.

`find content/protocols -name materials.yaml | xargs md5 -r | sort | uniq -w32 -D`:

```
f9231a2a  content/protocols/sdspage/sdspage_assemble_electrode_module/materials.yaml
f9231a2a  content/protocols/sdspage/sdspage_prepare_gel_cassette/materials.yaml
f9231a2a  content/protocols/sdspage/sdspage_prepare_running_buffer/materials.yaml
a9d9e2a1  content/protocols/sdspage/sdspage_load_sample_single_lane/materials.yaml
a9d9e2a1  content/protocols/sdspage/sdspage_load_samples_batch/materials.yaml
```

The `f9231a2a` file is 57 lines declaring 14 materials.
`sdspage_assemble_electrode_module` and `sdspage_prepare_gel_cassette` are pure
apparatus-assembly protocols referencing none of them;
`sdspage_prepare_running_buffer` uses 3.

Smallest fix: trim each copy to what its protocol actually uses -- `materials: {}`
for the first two, three entries for the third.

### M7. Dead `visible` state field on 44 objects

Pass: legacy auditor, corroborated by the style pass. Severity: medium.

Representative shape at `content/objects/decoration/calculation_100_ul.yaml:6-18`
and `content/objects/equipment/cell_viability_results_display.yaml:11-18`: a
`visible` bool whose `when: true` and `when: false` cases both output
`asset_name: interpretation_choice_card`, so the false branch is unreachable in
effect.

Evidence it is dead: `grep -rn "visible" content/protocols --include=*.yaml`
returns only prose inside prompts and comments. No protocol anywhere writes
`visible` via `ObjectStateChange` or `initial_state`.
`grep -rln "field_name: visible" content/objects | wc -l` returns 44, of which 38
are decorations and 6 are the new `*_display` equipment objects. The nine
`*_display.yaml` objects are inert on both ends, since `decoration_only` means
nothing can ever write the field either.

This is a schema-satisfying stub: `validation/yaml_schema/constants.py:46` makes
`state_fields` and `visual_states` required object keys. The honest pre-existing
precedent is `content/objects/equipment/gel_opening_tool.yaml:12-18`, which maps
`false` to a real `gel_opening_tool_hidden` asset. The better idiom ships in this
same change at `content/objects/equipment/calculation_pad.yaml:6-9`: a one-value
enum with one case, which is what `docs/specs/OBJECT_VOCABULARY.md:210` intends
for a static form.

Smallest fix: convert the 38 to the `calculation_pad` enum shape, which satisfies
`_validate_visual_states_completeness` identically. The deeper option, tied to
D2, is letting a `kind: decoration` object declare no mutable state.

### M8. Fourteen new `l-matdrift` warnings

Pass: style auditor. Severity: medium.

Fourteen of the 22 warnings come from `dose_carboplatin_series`, a step ADDED by
this change (confirmed as `+` lines in `git diff HEAD`; `add_mtt_to_wells` and
`add_dmso_to_wells` are context lines, so pre-existing):

```
{"severity": "WARNING", "code": "l-matdrift",
 "message": "source material undefined; dest material '...' assumed by author",
 "protocol": "plate_drug_treatment_drug_addition", "step": "dose_carboplatin_series"}
```

Cause at
`content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml:100-103`:
the source write is volume-only with no `material_name`, while destinations at
115-129 each assert a fresh identity.

Smallest fix: carry `material_name: carboplatin_4umol` on the source write so
lineage stays traceable.

### M9. Interpretation prompts state the conclusion

Pass: plan auditor. Severity: medium. Contradicts resolution ledger line 32.

- `content/protocols/sdspage/sdspage_image_gel/protocol.yaml:144-147` names the
  correct card's content verbatim ("a strong 24-28 kDa miraculin monomer band in
  lanes 1-3 and no prominent extra bands") against choices
  `gel_conclusion_expected_band` and `gel_conclusion_nonspecific_bands`.
- `content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml:72-74` does
  the same ("its background is clear and its bands are distinct").
- `content/protocols/sdspage/sdspage_run_electrophoresis/protocol.yaml:102-105`
  and `content/protocols/cell_culture/passage_hood_detachment/protocol.yaml:40`
  state the observation, which is more defensible.

The calculation cards show the standard these did not meet: calculation prompts
do NOT leak the answer
(`cell_seeding_plate_setup/protocol.yaml:39-42`,
`drug_dilution_setup/protocol.yaml:32-36`).

Smallest fix: move the evidence sentence out of the prompt and into the scene or
overlay state the learner reads, leaving the prompt as the question only.

### M10. Well-plate fill heights may not be distinguishable

Pass: plan auditor. Severity: medium. Unverified claim.

`content/objects/plate/well_plate_96.yaml:238-242` sets `capacity_ul: 300`
against teaching values of 90, 95, 100, 195, and 200 &micro;L. That makes 90
versus 95 &micro;L a 1.7 percent fill-height difference inside a 96-well subpart.
Resolution ledger line 47 claims per-well volumes visibly distinguish four
treatment classes; no rendered evidence for that specific claim exists in the
ledger or the diff.

Smallest fix: capture one render at the media-adjustment endpoint and either
confirm the claim or scale `capacity_ul` to the plate's real working volume
(roughly 200-250 &micro;L) so the classes separate.

### M11. A named calculation step with no calculation

Pass: plan auditor. Severity: medium.

`content/protocols/cell_culture/passage_pellet_reseed/protocol.yaml:370-372` has
`step_name: calculate_split_volume`, a prompt that supplies the answer
"(1.14 mL)", and a sequence of three clicks with no `select`. Every other named
calculation in this change got a paired-card decision. The step name claims work
the learner never does.

Smallest fix: add a two-card 1.14 versus 1.60 mL select, matching the seeding and
dilution pattern.

### M12. Manual count cannot be checked against the instrument

Pass: plan auditor. Severity: medium.

`content/protocols/cell_culture/trypan_blue_counting/protocol.yaml:378-416` has
the learner select "85 live / 7 dead" from unspecified "representative
quadrants", with no quadrant count and no dilution factor stated. Line 476 then
reports `cell_concentration_per_ml: 850000`. Viability reconciles (85/92 = 92.4
percent against the reported 92.5 percent), but the concentration follows from no
stated arithmetic, so the manual observation cannot be checked against the
instrument. That weakens the "meaningful observation" goal.

Smallest fix: state the quadrant count and the 1:1 trypan dilution in the prompt
so 85 resolves to 8.5e5 per mL derivably.

### M13. Duplicated placement-inheritance logic in the stepper

Pass: comment auditor, corroborated by the style pass. Severity: medium.

The remove-before-add reorder is CORRECT and now matches
`pipeline/scene_inheritance.py:335` (remove) and `:350` (add). But it was written
twice into two near-identical 25-line blocks with two separately worded comments
for the same rule: `validation/stepper/state.py:174-195` (`_register_placements`)
and `validation/stepper/state.py:524-544` (`_get_effective_placements`).

A future fix applied to one site only would silently diverge target registration
from placement resolution.

Smallest fix: extract one `_apply_placement_inheritance(scene_data,
base_placements) -> list` and call it from both sites.

### M14. Optional and nullable mixed on one field

Pass: style auditor. Severity: medium.

`src/shell/adapter/types.ts:196` and `:208` declare
`readonly feedback?: string | null;`. `docs/TYPESCRIPT_STYLE.md` says not to mix
both without a clear reason.

The cost lands immediately as a double guard written twice verbatim at
`src/scene_runtime/protocol/step_machine.ts:309-312` and `:334-337`. Both
producers already emit `... ?? null` (`step_machine.ts:1082`, `:1101`), so the
field is never actually `undefined`.

Smallest fix: drop the `?`, making it `readonly feedback: string | null`. Both
guards collapse to `=== null`.

### M15. Hardcoded pipette vocabulary and `or {}` fallbacks in the validator

Pass: style auditor, corroborated by comment and plan passes. Severity: medium.

`validation/yaml_schema/protocol_validator.py:665,671` use
`(interaction.get('response') or {})` and `(operation.get('state') or {})`.
`docs/PYTHON_STYLE.md` forbids `value or fallback` to silently replace None. Here
`or {}` also swallows a malformed non-mapping `response`, which is the opposite
of what a schema validator should do.

Separately, lines 612-624 hardcode the dispensing-tool vocabulary in Python
(`micropipette`, `p10_`, `p20_`, `p200_`, `p1000_micropipette`,
`multichannel_pipette`, `serological_pipette`, `repeat_dispenser`). A newly
authored range-specific pipette silently escapes the check with no failure
anywhere.

`protocol_validator.py:640` compounds it with a third synonym: the docstring says
"universal pipettes", the code checks `target == 'micropipette'`, and the emitted
message says "generic micropipette", against the one-canonical-term rule. The
method is also about 55 lines with three unrelated checks plus a nested loop.

Smallest fix: use `isinstance(..., dict)` guards matching lines 604 and 653;
derive the pipette set from `kind: pipette` objects or a declared capability;
lift the serological `set_volume` scan (roughly lines 665-693) into
`_serological_setpoint_findings(...)`.

### M16. Test-only fixture shipped in production `src/`

Pass: legacy auditor. Severity: medium. Pre-existing, not from this change.

`src/scene_runtime/layout/index.ts:44` re-exports `DEMO_OBJECT_LIBRARY` and
`DEMO_ASSET_SPECS` from `./__fixtures__/demo_library.js`.
`src/scene_runtime/layout/__fixtures__/demo_library.ts` has zero runtime
consumers; the only importers are five test files
(`tests/test_layout_engine.mjs:13-14`,
`tests/test_layout_semantic_zones.mjs:8-9`,
`tests/test_layout_vertical_footprint.mjs:17-18`,
`tests/test_layout_uniform_rescale.mjs:23-24`,
`tests/test_layout_item_overlap.mjs:26-27`), all reaching it through the shipped
bundle. This puts test data in the production bundle and contradicts the
no-fixture policy.

Smallest fix: move `demo_library.ts` under `tests/`, drop line 44 from
`index.ts`, and repoint the five test imports.

### M17. Two competing shapes for "this object is static"

Pass: style auditor. Severity: medium. Related to M7 and D2.

Thirty-eight of 49 new objects use the inert `visible` bool described in M7. The
same change ships the better idiom at
`content/objects/equipment/calculation_pad.yaml:6-9`. Two shapes for one concept
inside one new family.

Vocabulary-closure compliance is otherwise good: flat primitive state fields, no
open maps, and no `metadata`, `extras`, or `params` blobs anywhere in `content/`
(verified by grep).

### M18. Copy-paste families with no parameterization

Pass: style auditor. Severity: medium. Needs a decision record, not a workaround.

Thirty-three choice-card objects in `content/objects/decoration/` differ only in
`object_name`, `label`, and three hand-tuned widths, and all render the same
`interpretation_choice_card` asset. Four scene files
(`content/protocols/cell_culture/drug_dilution_setup/scenes/dilution_calculation_{50,60,200,500}.yaml`)
are byte-identical apart from two `object_name` values and `scene_notes` prose.

Both grow linearly with each new calculation or decision step, and the
hand-computed width triples will drift as labels are reworded.

The legacy pass notes the one-file-per-choice shape may be FORCED by the
`select`-gesture vocabulary, since `select` reuses the visible scene-object click
affordance and each choice must therefore be a distinct clickable object. The
file count is not itself the defect; the unparameterized duplication is.

### M19. The decision-card and review-scene pattern exists only as example YAML

Pass: docs auditor. Severity: medium.

`docs/specs/PROTOCOL_AUTHORING_GUIDE.md:226-250` still teaches a hypothetical
`choice_20uL_stock` target with no explanation of how it becomes a scene object.
The shipped pattern has three coupled pieces a future author cannot infer:

1. A `kind: decoration` plus `capabilities: [clickable]` object per alternative,
   rendering `interpretation_choice_card`.
2. A dedicated review scene that removes the workspace and adds the paired cards
   to separate zones
   (`content/protocols/cell_culture/trypan_blue_counting/scenes/viability_review.yaml:1-49`).
3. A `SceneChange` into it from the preceding response (that
   `protocol.yaml:402-405`).

Eleven such scenes ship. `grep -rn "review" docs/specs/SCENE_*.md` returns one
unrelated hit.

Smallest fix: replace the fake example with a real excerpt and add a "Review
scenes and choice objects" subsection.

### M20. The results-display object family is undocumented

Pass: docs auditor. Severity: medium.

Five new `kind: equipment` plus `decoration_only` objects are the visible evidence
every new `select` decision reads from. They appear in
`assets/equipment/SOURCES.md` but in no spec, and
`docs/specs/OBJECT_VOCABULARY.md` has no entry for the role.

Smallest fix: add a paragraph near the `kind` table at
`docs/specs/OBJECT_VOCABULARY.md:63`.

### M21. CHANGELOG entry omits required categories

Pass: docs auditor. Severity: medium.

Subsection order in the 2026-08-03 entry is correct (Fixes, Decisions, Developer
Tests) and rotation is NOT due (`wc -l docs/CHANGELOG.md` returns 658 against a
threshold near 1000). But everything is filed under "Fixes and Maintenance" while
the diff contains uncategorized:

- Removals: `micropipette.yaml` deleted; generic-micropipette targeting is now a
  hard error.
- Additions: roughly 40 decision and calculation decoration objects, 5 display
  objects, p20, p1000, `repeat_dispenser`, 11 review and calculation scenes, 67
  SVGs.
- Behavior or Interface Changes: `select` moving from unused to
  curriculum-proven; three new authoring ERRORs changing what YAML is accepted.

Every changelog entry must belong to a category per `docs/REPO_STYLE.md`.

Smallest fix: split into the four subsections and name the deleted object and the
three error codes explicitly.

### M22. Stale specs contradicted by the change

Pass: docs auditor. Severity: medium.

- `docs/specs/PROTOCOL_VOCABULARY.md:569-571` still ratifies `aspirate` as a
  general verb and labels `select` "(answer)". The file WAS edited in this change,
  so both are omissions. See H6 and H1.
- `docs/specs/WALKTHROUGH_GUIDE.md:357-359` and `:624-626` still call `select`
  unused and its status reopened. The file was untouched. Contradicted by
  `docs/specs/GESTURE_MODEL.md:48,146` and by 17 authored `select` interactions
  across 10 protocols.
- `docs/specs/GESTURE_MODEL.md` gesture table gives `drag` an "Authored evidence"
  of "Current protocol corpus", while the acceptance section of the SAME file says
  `type` and `drag` remain runtime paths without current authored curriculum
  evidence. Measured counts across `content/protocols/`: click 433, adjust 49,
  select 17, drag 0, type 0. The table row is simply wrong.
- `docs/LAYOUT_REMAINING_WORK.md:599-615` names now-orphaned assets
  (`static/p200_micropipette_empty.svg`, `_filled.svg`,
  `p10_micropipette_filled.svg`) as live contract-compliance gaps. The file was
  edited by this change but this section was not reconciled.
- `content/objects/plate/well_plate_96.yaml:15-19` header still says "Visual: the
  identity layer only" and "there is no fill_height composite on wells in this
  plan", contradicting lines 238-242 of the same file.

## Low findings

- **`p10_micropipette` renders identically loaded or empty.**
  `content/objects/pipette/p10_micropipette.yaml:48-64` maps EVERY
  `held_material_name` case, loaded ones included, to `p10_micropipette_empty`.
  `static/p10_micropipette_filled.svg` is orphaned and byte-identical to
  `_empty`. This change touched the file (adding `tip_status` at lines 14-18 and
  45-47) but left the P10 visually mute while P200, P1000, and P20 all gained
  loaded art. Legacy pass.
- **Naming vocabulary split in one new asset family.**
  `binary_state/p1000_micropipette_{empty,filled}.svg` and
  `p20_micropipette_{empty,filled}.svg` against
  `p200_micropipette_{loaded,unloaded}.svg`. One canonical term per concept.
  Legacy pass.
- **Three pre-existing orphan objects**, referenced by no scene, protocol, or
  code: `content/objects/bottle/mtt_stock_tube.yaml`,
  `content/objects/decoration/p10_gel_loading_tip.yaml`,
  `content/objects/decoration/professor_avatar.yaml`. Note
  `p10_gel_loading_tip_box.yaml` IS referenced; only the bare `_tip` is orphaned.
  Legacy pass.
- **Stale placeholder row.** `assets/equipment/MISSING_SVG_PLACEHOLDERS.md:16`
  lists `microtube_rack_24_placeholder.svg` for object `microtube_rack_24`, but
  `content/objects/rack/microtube_rack_24.yaml:26` uses `asset_name: tube_rack`.
  Legacy pass.
- **Orphaned data file.** `assets/equipment/bottle.colormap.json` is read by no
  code; `grep -rln "bottle.colormap"` finds only `docs/FILE_STRUCTURE.md` and
  archived reports. Legacy pass.
- **Stale hardcoded fleet list.** `tools/svg_liquid_census.py:2-7` describes
  itself as a proposal tool superseded by work that has since landed, and its
  `EXPECTED_ANCHORED_FLEET` (lines 37-71) hardcodes 34 filenames, at least a
  dozen now orphaned. Nothing invokes it. Legacy pass.
- **Dead BEM base class.** `src/shell/regions/guidance_bar.tsx:198` uses
  `class="action-rail-feedback action-rail-feedback--correct"` while `:143` uses
  only the modifier, and `src/style.css:472` defines ONLY the modifier. The base
  half of the pair matches no rule anywhere. Comment and style passes.
- **Four levels of inline callback nesting in JSX.**
  `src/shell/regions/guidance_bar.tsx:205-233`. Smallest split: extract a
  `RecoveryPanel(props: { rejection, snapshot })` component. Comment pass.
- **Duplicated feedback ternary.**
  `src/scene_runtime/protocol/step_machine.ts:309-312` and `:334-338` differ only
  in the `kind` literal. Comment pass.
- **Snapshot literal duplicated across three files.** Adding one field to
  `ShellViewSnapshot` requires four hand-edits (`src/protocol_host.tsx:171`,
  `src/scene_runtime/protocol/step_machine.ts:144` and `:264`,
  `tools/seam_types_compile_check.ts:95`). Smallest fix: one exported
  `make_initial_snapshot(...)` factory. Style pass.
- **Hand-maintained declaration file with no sync guarantee.**
  `tests/playwright/e2e/walker_helpers.d.mts` declares 3 functions while
  `walker_helpers.mjs` exports 25, with no header comment warning of the drift
  trap. `ReadonlyGameState` (lines 5-17) has no `readonly` member despite the
  name. Smallest fix: convert `walker_helpers.mjs` to `.ts` and delete the shadow
  file. Comment and style passes.
- **Misleading boundary comment.** `pipeline/gen_object_library.py:922-925`
  enumerates "labels, enum defaults/allowed values, descriptions, formulas, and
  visual cases", but `decode_entity_values` rewrites EVERY string in the tree
  including `object_name`, `asset_name`, SVG path data, and colors. The list reads
  as exhaustive. Comment pass.
- **Inverted intent in a geometry comment.**
  `pipeline/gen_object_library.py:208-214` reads "These exact rectangles prevent a
  learner from successfully clicking the entire vertical gel lane", which reads as
  though frustrating the learner is the goal. Suggested rewording: "require the
  learner to click the narrow well mouth rather than anywhere in the vertical
  lane". The geometry claims themselves were verified accurate against
  `assets/equipment/multi_state/gel_cassette_empty.svg`. Comment pass.
- **Missing Strategy 1 marker.** `validation/stepper/runner.py:283-290` renumbered
  the docstring to five strategies and bumped inline markers to Strategy 2, 3, and
  4, but the new entry-step block that IS strategy 1 carries no comment. Comment
  pass.
- **Discarded return value reads like a bug.**
  `_activate_declared_scene(...)` returns a documented success bool, checked at
  `validation/stepper/runner.py:286` but discarded with no comment at `:192` and
  `:601`. One line saying a step without a declared scene keeps the current active
  scene would resolve it. Comment pass.
- **Renamed term in a citation.**
  `src/scene_runtime/renderer/subpart_material_state.ts:67-70` says
  "no-visible-liquid state"; `docs/specs/MATERIAL_CONVENTION.md:503` calls it
  "no-visible-amount state". The citation is also a bare basename where a path is
  required. Comment pass.
- **Bare backticked path where a link is required.**
  `docs/specs/WALKTHROUGH_GUIDE.md:357`. This change fixed exactly this shape at
  `PROTOCOL_AUTHORING_GUIDE.md:115-117` and left the sibling. Docs pass.
- **Wrong example name in scene lint docs.** `docs/specs/SCENE_LINT.md:266` uses
  `micropipette` as an example `placement_name`, a dead name that is now a
  validator ERROR as a target. Change to `p200_micropipette`. Docs pass.
- **Wrong validator paths in schema docs.**
  `docs/VALIDATION_JSON_SCHEMA.md:12-15,46,139,147,160` cite
  `validation/yaml/content_lint.py` and `validation/yaml/validate.py`; the real
  paths are `validation/yaml_schema/content_lint.py` and
  `validation/validate.py`. Pre-existing drift, but the same file needs editing
  for H6. Docs pass.
- **Paired choice cards render identical artwork.** Both members of every
  interpretation pair output `asset_name: interpretation_choice_card`, and
  `docs/specs/GESTURE_MODEL.md:96-99` now asserts alternatives must be
  "distinguishable without relying only on color". They are distinguished by DOM
  label over identical artwork. Defensible, but should say so explicitly. Docs
  pass.
- **Authoring vocabulary leaks into learner text.** Three instances of "In this
  fixed scenario" and one "The fixed simulated outcome is heated without boiling".
  Also `src/shell/regions/guidance_bar.tsx:71` renders "Return to P1000
  micropipette, the highlighted item, and try again." -- missing article, and it
  names the item then re-describes it. Four exceptions across 278 changed
  prompt and feedback strings. Comment pass.
- **First wrong click hands over the answer.**
  `src/scene_runtime/protocol/step_machine.ts:321-333` populates `expected_label`
  on a rejected select. With `on_failure: retry` this is defensible for formative
  practice, but it is unmentioned in the ledger's feedback row. Plan pass.
- **Stale comment referencing the removed generic pipette.**
  `content/protocols/cell_culture/drug_dilution_setup/scenes/bench_setup.yaml:16`.
  Plan pass.
- **Two YAML formatting shapes inside one new family.**
  `content/objects/decoration/calculation_100_ul.yaml:22` uses a one-line flow
  mapping while the other 21 new choice cards use block style. The four
  `dilution_calculation_*.yaml` scenes also omit the blank line before
  `scene_notes:` that every sibling has. Style pass.
- **Playwright specs assert full authored feedback sentences.**
  `tests/playwright/test_pedagogy_outcomes.spec.ts:132-134,169-171`. Not a gate
  concern, since that lane is allowed to be slow and user-visible text is
  legitimately its subject; expect edits whenever feedback copy is reworded. Test
  pass.

## Explicitly NOT defects

Recorded so a future sweep does not "clean up" deliberate work.

- **`protocol_validator.py:615` and `:651` still name the deleted bare
  `micropipette`.** This is deliberate anti-regression: an author who writes that
  target gets the clear `generic_micropipette` error instead of an opaque
  unresolved-object error. `tests/test_protocol_initial_state.py:316-339`
  correctly tests the rejection. Keep it.
- **`src/scene_runtime/renderer/subpart_material_state.ts:55-57` and `:66-72`
  return identical values** and could collapse, but the intervening error branch
  at 58-65 makes the current structure readable. Leave it.
- **The 44 `composite: []` no-op declarations** are the documented
  honest-nonvisual pattern, not half-alive legacy.
- **Camel-case helper names in new Playwright specs** match every existing spec
  under `tests/playwright/`. Consistent, not a finding.

## What held up well

Recorded because a findings-only document misrepresents the change.

- **Runner coherence is genuinely verified.** Volumes reconcile numerically end
  to end: `passage_pellet_reseed/protocol.yaml:348-358` sets `conical_15ml` to
  8.0 mL, `:391-405` removes 1.14 mL leaving 6.86, which is exactly
  `trypan_blue_counting`'s seed at `:7-10`. Trypan reports 850000 cells/mL at
  `:476`, which is the 8.5e5 the seeding prompt reads back at
  `cell_seeding_plate_setup:41`. On the SDS side, `sdspage_full` seeds slot B4 as
  `protein_ladder` (`:29-30`) and `sdspage_heat_denature_samples:77` converts it
  to `protein_ladder_denatured`, which `sdspage_load_protein_ladder:102`
  consumes.
- **Root-only seeding is correct and deliberately commented.**
  `content/protocols/runners/cell_culture_full/protocol.yaml:4-7` and
  `sdspage_full/protocol.yaml:4-6` state that constituent direct-launch seeds are
  ignored, matching the "Sequence runners" section of `docs/PRIMARY_SPEC.md`.
  `entry_step` matches the first mini's `entry_step` in every runner. Only three
  step-level `scene:` fields exist repo-wide and all three are on entry steps.
- **Fresh-tip continuity is real and pervasive.** 49 `tip_status: fresh` and 52
  `tip_status: used` writes across `content/protocols/`, enforced by sequence
  order.
- **Every authored pipette setpoint sits inside its declared range.** P20 uses
  7.5, 10, 20; P200 uses 20 through 200 against an object min of 20 and max of
  200 at `content/objects/pipette/p200_micropipette.yaml:9-10`; P1000 uses 240
  through 990.
- **Result interpretation before completion is proven.** `sdspage_image_gel` and
  `mtt_solubilization_readout` both terminate on an interpretation step, and
  `tests/playwright/test_pedagogy_outcomes.spec.ts:219,249` asserts
  `data-protocol-complete` has count 0 before it.
- **Bulk and repeating transfers landed.**
  `content/protocols/cell_culture/mtt_plate_reaction/protocol.yaml:142` onward
  now performs 12 discrete column strokes instead of the single plate click the
  audit flagged.
- **Genuine paired distractors.** Seventeen `select` interactions with real
  alternatives, for example
  `content/protocols/cell_culture/cell_seeding_plate_setup/scenes/seeding_calculation_review.yaml:11-21`
  placing both `calculation_2_8_ml` and `calculation_2_4_ml`.
- **Four of the six declared blockers are genuinely blocked**, named in
  learner-visible text rather than silently skipped. For example
  `content/protocols/sdspage/sdspage_load_protein_ladder/protocol.yaml:76` names
  Bradford normalization and product-specific ladder volumes as out of scope. All
  104 authored steps use exactly `on_success: complete` and `on_failure: retry`,
  so there is zero fake branching anywhere.
- **The micropipette migration is otherwise clean.** No protocol, scene, or
  runtime code references the removed object; the renamed gel cassette asset
  leaves no stale path outside `docs/archive/`.
- **No orphans among the new work.** All 67 new or renamed SVGs are selected by
  at least one object; all 50 new object YAMLs are referenced by a scene or
  protocol; all four new review scenes are reached by a `SceneChange`.
- **No manifest drift.** `git diff HEAD` on `package.json`,
  `pip_requirements.txt`, `pip_requirements-dev.txt`, and `Brewfile` is empty,
  and `tests/test_import_requirements.py` passes.
- **No planning scaffolding, TODO, FIXME, disabled tests, or commented-out
  blocks added.** The one stale plan pointer in `src/shell/adapter/types.ts` was
  correctly retargeted to an archive path that exists.
- **Two test files were substantially de-fragilized.**
  `tests/test_material_effect_retirement.py` and
  `tests/test_media_adjustment_conservation.py` replaced exact asset-name set
  equalities, hardcoded `Path()` inventories, and literal volumes with behavior
  properties. That is the direction the rest of the batch should move.
- **Learner-facing copy is strong overall.** One representative example:
  "Confirmed: the cells are rounded and detached, so medium can now neutralize
  trypsin." Four exceptions across 278 changed strings, listed above.

## Residual risk and evidence gaps

- **The full Playwright suite was not run.** Only the new
  `test_pedagogy_outcomes.spec.ts` (5 passed) and a subset were exercised. The
  ledger's 105/105 record predates the two red gates fixed here. Visible-UI
  completability is the contract's actual completion bar, so the whole
  verification record should be re-run and re-stated.
- **Scene-level asset integrity is unverified.** SCENE-LINT and SCENE-DESIGN
  depend on regenerated render artifacts under gitignored, volatile paths. Whether
  the 67 new SVGs place and render correctly in a scene was not confirmed. See
  H3.
- **M10 cannot be settled without a render.**
- **20 of the 77 `s-unused` advisories were not individually triaged** (15
  protocols, 1 to 3 each). Re-run after fixing M5 for a clean list.
- **No pre-change baseline for the 22 `l-matdrift` warnings.** Fourteen were
  attributed to this change by diff-line analysis; the provenance of the other 8
  is unconfirmed.
- **No reviewer read all 22043 added lines.** Each pass sampled the diff for its
  scope categories and backed that with repo-wide greps, md5 dedupes, and the
  automated gates.
- **Repository tooling mutates tracked files during read-only checks.** Running
  `pytest tests/` and `validation/validate.py` rewrote all of `generated/` and
  left two TRACKED report files modified:
  `docs/active_plans/reports/normalize_svg_v3_wild_verdicts.json` and
  `docs/active_plans/reports/svg_visual_regression.json`. Tracked-file count went
  from 308 to 310 during review. Check this before committing.
- **Unrelated pre-existing tooling defect**, noticed during evidence gathering:
  `python3 validation/validate.py -O manual -J` crashes with an unhandled
  traceback at `validation/validate.py:345` (`json.loads(stdout)`), while
  `-O yaml -J` works. Not in this diff. Working route:
  `python3 -m validation.manual.validate --validate -a -J`.
