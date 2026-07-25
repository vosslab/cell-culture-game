# WOW recovery plan

## Purpose and boundary

Restore the project as a coherent teaching tool through one student-visible
vertical slice: a clear launch choice, a single live action coach, useful
recovery and completion states, correct high-confidence teaching copy, and
two unmistakable lab-state transitions. This plan preserves the YAML, runtime,
SVG, layout, visible-UI, and learning-block invariants in
[PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md).

The audits show a viable interaction engine but an educationally thin shell:
three representative visible-UI walks completed, while the baseline scored
17/40 for user experience and found no meaningful terminal state
([wow_ux_baseline.md](../audits/wow_ux_baseline.md)). This is not a rewrite.
It concentrates improvements at the shared seams that affect every protocol.

## Evidence-led scope

| Area | Recovery decision | Evidence |
| --- | --- | --- |
| Dependency health | Keep the now-working npm resolution reproducible; do not use force or legacy peer resolution. | User report and local package update. |
| Student shell | Make one action, one recovery message, timed-wait state, and completion state visible through the existing adapter seam. | [wow_shell_cohesion_audit.md](../audits/wow_shell_cohesion_audit.md), [wow_feedback_state_audit.md](../audits/wow_feedback_state_audit.md) |
| Launcher | Teach the difference between full experiments and focused practice without new curriculum metadata. | [wow_launcher_ux_audit.md](../audits/wow_launcher_ux_audit.md) |
| Pedagogy | Correct only directly evidenced wording and causal-order defects. Keep local-method choices for faculty ratification. | [wow_pedagogy_audit.md](../audits/wow_pedagogy_audit.md) |
| Visible state | Give the SDS-PAGE heat block and lightbox distinct, rendered before/after states. | [wow_svg_asset_quality_audit.md](../audits/wow_svg_asset_quality_audit.md) |
| Layout authoring | Preserve semantic zones while moving all zone sizing and coordinates into the layout manager. | Working-tree evidence in `docs/active_plans/audits/coordinate_free_layout_recovery_audit.md`. |
| Proof | Extend the existing visible-UI walker with focused browser assertions; do not count synthetic DOM clicks as student-path proof. | [wow_browser_proof_gap_audit.md](../audits/wow_browser_proof_gap_audit.md) |

## Tonight's vertical slice

### 1. Reproducible dependency baseline

- Owner: dependency maintainer.
- Files: `package.json`, `package-lock.json` only.
- Keep TypeScript within the supported `typescript-eslint` peer range and retain
  the user's successful `npm install` result in the lockfile.
- Gate: clean-install succeeds without `--force` or `--legacy-peer-deps`;
  TypeScript compilation and the repository check pass.

### 2. One protocol status rail

- Owner: shell maintainer.
- Files: `src/shell/**`, `src/protocol_host.tsx`,
  `src/protocol_host_template.html`, and the shell-owned portions of
  `src/style.css`. The launcher must not edit these files concurrently.
- Add one mounted shell composition root and one visible status rail. During an
  active step it states the action and target in learner language, agrees with
  the active scene affordance, and keeps an authored tip subordinate.
- Preserve the existing scene renderer, YAML semantics, and object layout. The
  shell consumes an explicit snapshot projection; it does not inspect scene DOM
  to infer state.
- Surface wrong-target/wrong-value recovery, a global timed-wait explanation,
  short valid-action acknowledgement, and a terminal completion panel. At
  completion every outline item is complete, the final counter remains useful,
  and the learner has a return-to-launcher route.
- If the closed adapter must carry a rejection reason or a student-facing target
  label, make that a small typed adapter/runtime amendment with reducer tests;
  do not add a protocol-specific fallback.

Acceptance gate:

- A real click, adjust, type, and timed-wait walk shows exactly one current
  action, one matching active affordance, recovery after a visible wrong action,
  and a completion panel with no blank/generic guidance.
- Existing normal-host and `?shell=off` diagnostic behavior continues to pass.

### 3. Student-facing launcher

- Owner: launcher maintainer, after shell CSS merges.
- Files: `src/launcher/protocol_launcher.tsx`, launcher-specific generated-index copy
  seam if needed, launcher tests, and the launcher-only section of
  `src/style.css`.
- Present "Choose your lab experience": full experiments first, focused
  practice grouped by cluster below. Show a human title, action-oriented hook,
  protocol-kind label, guided-step burden, and text CTA while retaining a single
  normal anchor per card.
- Hide raw `protocol_name` from normal student view but retain it as a stable
  data attribute for routing and tests. Derive copy from present generated
  learning metadata; do not introduce author fields, duration promises,
  completion/resume claims, or an inferred curriculum order.

Acceptance gate:

- Browser proof at desktop and constrained-laptop widths shows clear tier
  labels, visible CTA text, no exposed snake_case IDs, direct navigation, and
  no clipped primary card copy.

### 4. Confirmed pedagogy repairs

- Owner: curriculum maintainer.
- Files: only these protocol YAML files, unless a necessary existing object
  state is already owned by the asset-state workstream:
  - `content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml`
  - `content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml`
  - `content/protocols/cell_culture/passage_hood_detachment/protocol.yaml`
  - `content/protocols/sdspage/sdspage_heat_denature_samples/protocol.yaml`
- Correct the MTT order: PBS first, powder transfer next, then vortex and only
  then the 12 mM material state. Do not claim dissolution before powder exists.
- Correct the MTT product description to purple formazan and correct the BME
  explanation: the reducing agent maintains reduced disulfides during sample
  preparation.
- Remove the room-temperature/37 C incubator contradiction with the audited
  wording: allow trypsin to act for about two minutes while checking detachment.
- Narrow or defer the MTT learning claim about weighing unless a visible,
  validated balance interaction is also implemented; a claim of mastered
  measurement without the interaction is not acceptable.

Acceptance gate:

- Content lint passes and each changed mini-protocol completes through the
  shared visible-UI walker. Before/after screenshots demonstrate that the
  corrected action order has a perceptible consequence.

### 5. High-impact visual states

- Owner: scientific asset-state maintainer.
- Files: `content/objects/equipment/heat_block.yaml`,
  `content/objects/equipment/lightbox.yaml`, any directly referenced existing
  object YAML needed for tray/capture composition, and new normalized SVGs
  under `assets/equipment/`. This workstream owns those assets and must not
  modify protocol prompts or shell files.
- Give the heat block distinct open/closed and rack-present representations.
- Give the lightbox distinct off/on, tray-present, and captured-image evidence.
  The capture state may be an existing closed visual-state composition; it must
  be visible and must not create an unratified YAML vocabulary.
- Add the minimum scene/object render regression that proves authored selected
  states emit the intended asset. Material-capable objects use the existing
  generic anchor-material path; do not add a whole-asset material workaround.
  This slice does not claim protocol-driven post-interaction material coverage
  unless an authored protocol state change and visible-UI proof establish it.

Acceptance gate:

- A real SDS-PAGE heat-denaturation and gel-imaging walk captures meaningful
  before/after screenshots for open/closed, rack transfer, lightbox power,
  tray transfer, and capture. Assets remain normalized and uncropped.

### 6. Focused browser proof

- Owner: browser-proof maintainer, after the feature workstreams land.
- Files: focused existing or new `tests/playwright/*.spec.ts` files and shared
  walker helpers only. Do not change product code or curriculum YAML.
- Add student-path assertions for the status rail, completion, launcher, and
  the two SDS-PAGE state changes. Use actionability-checked locators, not
  `HTMLElement.click()` executed through `page.evaluate`.
- Save and assert a small checkpoint manifest with protocol, step, target,
  gesture, screenshot paths, and visible target bounds for the new proof lane.
- Preserve the generic walker. No step-name or protocol-name test driver
  branches are permitted.

Acceptance gate:

- New browser tests run through the normal built and served application, assert
  visible feedback/state changes, and leave zero unexpected browser errors.
- Report known expected visible-UI failures separately; do not call the full
  contract green while `cell_culture_full` or
  `plate_drug_treatment_drug_addition` remains an expected failure.

### 7. Coordinate-free scene authoring

- Owner: layout manager, before final plate-focus proof.
- Files: scene vocabulary and format specs, scene generation and inheritance,
  `src/scene_runtime/layout/**`, layout validation, current base and
  protocol-scene YAML, and focused layout/browser tests.
- Preserve zones as ordered semantic groupings. Source zones declare stable
  names, not rectangles; flat placements retain their existing `zone`,
  `placement_name`, and `object_name` identity seam.
- Authors do not declare `scene_bounds`, background bounds, zone rectangles,
  baselines, raw coordinates, or numeric scale fixes.
- Measure each zone's assigned objects and labels, then lower semantic zones to
  internal workspace bands, lanes, bounds, and baselines in the shared
  TypeScript layout manager before the existing object-aware packing and
  measured vertical-reflow phases.
- Internal rows or lanes are implementation details, not an additional YAML
  vocabulary. Do not revive the historical equal-width fixed-region-per-slot
  prototype or parse arbitrary coordinates out of zone names.
- Make generation, protocol-scene inheritance, target resolution, structural
  guards, diagnostics, and the browser renderer consume one coherent model
  before migrating every scene.
- Preserve the intentional plate perspective through a dedicated foreground
  teaching zone and shared scale policy. Supplies and pipettes remain secondary
  context; their exact rectangles are not authored.

Acceptance gate:

- Source checks reject authored geometry in new and migrated scenes.
- Stable placement names and visible protocol target resolution survive
  inheritance and migration.
- The real generated-data-to-SVG-renderer path, not a placeholder gallery,
  proves an ordinary bench scene and a plate-focused scene at browser level.
- The plate is visibly primary, instruments remain recognizable and
  unclipped, and no final object overlap is hidden by a misleading diagnostic.

## Integration order

1. Confirm dependency install and baseline checks.
2. Restore coordinate-free layout authoring at the shared control layer.
3. Implement and prove the shell rail/completion seam.
4. Apply safe pedagogy corrections and asset-state changes in parallel.
5. Merge launcher styling after shell CSS settles.
6. Add focused browser proof, then run the full validation suite and inspect
   screenshots from the representative MTT, passage, and SDS-PAGE journeys.

## Explicit deferrals

| Deferred item | Why it is not part of tonight's slice | Required next decision |
| --- | --- | --- |
| T75 vessel, trypsin volume, and neutralization ratio | Course-local method choice. | Faculty-approved method and vessel labeling. |
| Exact trypsin environment | The contradiction can be removed, but exact local conditions need approval. | Faculty ratification if an incubator is required. |
| Ladder heating, p200/tip compatibility, and lane-5 assessment | Course equipment and assessment intent are not safely inferable. | Faculty decision, then semantic target/render work. |
| Microscope confluence/detachment evidence | Needs a scientifically valid observation representation, not an automatic click. | Choose approved imagery/overlay and assessment criterion. |
| Plate-reader result/IC50 artifact | Needs a defined result representation and downstream learning scope. | Curriculum and vocabulary decision. |
| Protocol-specific material transitions beyond verified anchor rendering | The modular object path renders declared material states, but this slice does not establish every protocol interaction that changes one. | Add an approved authored state change and visible-UI proof for the teaching step. |
| Placeholder and identity corpus repair | Important but too broad for a cohesive slice. | Prioritized asset backlog after emitted-asset regression exists. |
| Drag gesture | No authored curriculum witness currently needs it. | Add only with a ratified learning block and real walker support. |
| Responsive/touch corpus sweep | Requires course-supported device range. | Define viewport/device targets. |

## Final release gates

- `npm install` resolves cleanly with the committed lockfile.
- YAML/content, TypeScript, unit, build, and browser checks pass.
- The three representative student journeys complete through visible UI.
- Screenshots show the action-to-state-change-to-next-action loop and a
  completion state, not only a final counter.
- The changelog records the behavior changes, safe pedagogy corrections, and
  any remaining expected visible-UI failures accurately.
