# Embedded SVG interface scope

Date: 2026-08-23

Status: scope complete; migration plan not yet written or approved

## Executive finding

The SVG text problem is an ownership problem, not a font-conversion problem.
Several files classified as static equipment are complete learner-facing result,
observation, or decision screens. Their scientific values, explanations,
instructions, and state identity are flattened into artwork, so the application
cannot expose that content semantically, localize it, or update it from runtime
state.

The three files selected for visual review establish the defect clearly:

- [cell_viability_results_display.svg](../../../assets/equipment/static/cell_viability_results_display.svg)
  is a complete dashboard with measurements, a seeding gate, a manual check,
  and decision instructions.
- [electrophoresis_endpoint_display.svg](../../../assets/equipment/static/electrophoresis_endpoint_display.svg)
  is a complete observation and safety-decision screen, not an instrument.
- [gel_image_results_display.svg](../../../assets/equipment/static/gel_image_results_display.svg)
  is a complete result-review screen with lane data, a conclusion, a capture
  record, and interpretation instructions.

Moving their prose to paths would preserve the defect. The durable direction is
to make the application own the scientific state and learner-facing interface,
while an SVG owns only language-neutral visual evidence or physical equipment
geometry.

## Evidence boundary

The review covered all 186 SVG files under `assets/equipment/`, their authored
YAML references, their generated manifest entries, the runtime SVG host, current
SVG-pipeline guidance, and tests that inspect or render the affected assets.
Visual inspection used PNGs rendered directly from source with `rsvg-convert`.
The working `generated/svg_manifest.ts` and other generated code are
corroborating build evidence; [gen_svg_manifest.py](../../../pipeline/gen_svg_manifest.py)
owns their generation, while authored SVG, YAML, TypeScript, tests, and
specifications remain the sources of truth.

The source census found:

- 23 SVG files with live `text`, `tspan`, or `textPath` elements;
- 17 files with visible labels, prose, state explanations, or instructional
  content that does not belong in the artwork;
- 5 files whose visible text is limited to approved intrinsic numbers or plate
  coordinates, but whose live text still fails the normalizer contract; and
- 1 file with a hidden authoring-service credit rather than learner-visible
  content.

Eight other files contain `title` or `desc` metadata. That metadata needs a
separate accessibility review; it is not part of the visible-text count.

### Reproduction commands

The mechanical counts are reproducible from the repository root:

```bash
find assets/equipment -name '*.svg' -type f | wc -l
rg -l '<(text|tspan|textPath)([ >])' assets/equipment --glob '*.svg' | sort
rg -l '<(title|desc)([ >])' assets/equipment --glob '*.svg' | sort
```

The first command reports 186 source SVGs. The second reports the 23 live-text
files. Visible-versus-hidden and intrinsic-versus-prohibited classification
requires rendering because element presence alone cannot identify visual role.
The three representative renders used this source-preserving form:

```bash
rsvg-convert -o result.png assets/equipment/static/result.svg
```

Reference searches used exact asset names against `content/`, `src/`, `tests/`,
and `generated/`. An asset is called unreferenced only when no authored content
or source-code reference exists. A generated-manifest entry alone proves that a
file is published, not that a user workflow reaches it.

### Classification limits

- Live-text detection is exact for `text`, `tspan`, and `textPath`; it cannot
  infer words that have already been converted to paths.
- Visible-content classification is a rendered visual judgment backed by the
  source element text recorded below.
- Orphan classification is intentionally conservative. `drug_vial_rack.svg`,
  `waste_tray.svg`, and the static `electrode_module.svg` were deleted after
  fresh reachability validation confirmed they had no learner-workflow role;
  the live object uses separate open and closed assets.
- This audit found no visible logo or brand wordmark in the 186-asset review.
  The permitted-logo exception therefore has no current positive example.

## Current modeling defect

Five full-screen display objects use the same misleading shape:
`kind: equipment`, one `visible` boolean whose true and false branches resolve
to the same SVG, and `capabilities: [decoration_only]`. The fixed scientific
dataset exists only inside the SVG. This affects the linked declarations:

- [cell_viability_results_display.yaml](../../../content/objects/equipment/cell_viability_results_display.yaml);
- [electrophoresis_endpoint_display.yaml](../../../content/objects/equipment/electrophoresis_endpoint_display.yaml);
- [gel_image_results_display.yaml](../../../content/objects/equipment/gel_image_results_display.yaml);
- [hemocytometer_observation_display.yaml](../../../content/objects/equipment/hemocytometer_observation_display.yaml);
  and
- [mtt_reader_results_display.yaml](../../../content/objects/equipment/mtt_reader_results_display.yaml).

The [plate_reader.yaml](../../../content/objects/equipment/plate_reader.yaml)
declaration is more structured, but its `result_state` composites still put the
learner-facing result summary inside two transparent SVG panels.

### Runtime consequence

All seven result assets are emitted with `requires_dom_svg: false` in the
working `generated/svg_manifest.ts` built by
[gen_svg_manifest.py](../../../pipeline/gen_svg_manifest.py). The static host in
[scene_item.tsx](../../../src/scene_runtime/renderer/scene_item.tsx) renders
that class as an opaque `<img alt="">`. Therefore:

- embedded measurements, headings, instructions, and conclusions are not
  application DOM text;
- the browser treats the image as decorative rather than exposing the result
  content through its alternative text;
- the result copy cannot update independently when runtime state changes;
- localization would require replacing artwork rather than translating data;
  and
- tests can prove image presence without proving that scientific content has an
  accessible semantic representation.

Current [test_pedagogy_outcomes.spec.ts](../../../tests/playwright/test_pedagogy_outcomes.spec.ts)
coverage proves that the endpoint and gel-result `<img>` elements become
visible. [test_mtt_readout_visibility.py](../../../tests/test_mtt_readout_visibility.py)
goes in the opposite direction and parses visible words directly from
`mtt_reader_results_display.svg`. Both preserve the flattened implementation:
one checks the container without its semantics, while the other treats SVG
prose as the contract.

[test_scene_reactivity_lifecycle.spec.ts](../../../tests/playwright/test_scene_reactivity_lifecycle.spec.ts)
already protects a narrower boundary: authored object labels must not leak into
injected SVG markup. That test does not detect result prose in opaque image
assets, so the new source gate must cover both rendering modes.

## Affected inventory

### Application interfaces

These seven assets require ownership migration, not text outlining.

| Asset | Observed embedded content | Migration direction |
| --- | --- | --- |
| [cell_viability_results_display.svg](../../../assets/equipment/static/cell_viability_results_display.svg) | Dashboard heading, 8.5 x 10^5 cells/mL, 92.5% automated viability, greater-than-90% gate, 85-clear/7-blue manual cross-check, and decision instruction | Render measurements, comparison, and instructions from typed state in application UI; retain or rebuild only language-neutral measurement graphics. |
| [electrophoresis_endpoint_display.svg](../../../assets/equipment/static/electrophoresis_endpoint_display.svg) | Observation heading, 5-10 mm endpoint, `SAFE ENDPOINT`, `STOP NOW`, power-off safety instruction, and overrun explanation | Drive gel and dye evidence from electrophoresis state; render safety and next-action language in accessible UI. |
| [gel_image_results_display.svg](../../../assets/equipment/static/gel_image_results_display.svg) | Result heading, group and lane map, molecular-weight values, 24-28 kDa conclusion, capture record, quality, orientation, and interpretation instruction | Separate band evidence from lane metadata, interpretation, and capture status; render the result surface from structured state. |
| [hemocytometer_observation_display.svg](../../../assets/equipment/static/hemocytometer_observation_display.svg) | Four quadrant counts, viable/nonviable legend, per-quadrant clear/blue subtotals, and addition instruction | Model quadrant observations as data; render count evidence and its semantic table or summary in application UI. |
| [mtt_reader_results_display.svg](../../../assets/equipment/static/mtt_reader_results_display.svg) | 560 nm heading, blank and control, complete carboplatin dose series, viability row, single-drug endpoint, and combination endpoint | Replace the fixed monitor image with a state-driven result surface tied to the assay record. |
| [plate_reader_absorbance_result_panel.svg](../../../assets/equipment/static/plate_reader_absorbance_result_panel.svg) | Raw/blank-corrected MTT summary with treatment values | Render raw measurements through the plate reader's existing result state and numeric fields. |
| [plate_reader_normalized_viability_panel.svg](../../../assets/equipment/static/plate_reader_normalized_viability_panel.svg) | Normalized control, carboplatin viability, and combination viability | Render normalized values and comparison through the same application-owned result surface. |

### Authoring and workflow evidence

| Surface | Object declaration | Scene placement | Protocol state and decision flow |
| --- | --- | --- | --- |
| Cell viability | [cell_viability_results_display.yaml](../../../content/objects/equipment/cell_viability_results_display.yaml) | [viability_review.yaml](../../../content/protocols/cell_culture/trypan_blue_counting/scenes/viability_review.yaml) | [trypan_blue_counting/protocol.yaml](../../../content/protocols/cell_culture/trypan_blue_counting/protocol.yaml) |
| Hemocytometer observation | [hemocytometer_observation_display.yaml](../../../content/objects/equipment/hemocytometer_observation_display.yaml) | [hemocytometer_count_review.yaml](../../../content/protocols/cell_culture/trypan_blue_counting/scenes/hemocytometer_count_review.yaml) | [trypan_blue_counting/protocol.yaml](../../../content/protocols/cell_culture/trypan_blue_counting/protocol.yaml) |
| MTT result monitor | [mtt_reader_results_display.yaml](../../../content/objects/equipment/mtt_reader_results_display.yaml) and [plate_reader.yaml](../../../content/objects/equipment/plate_reader.yaml) | [result_review.yaml](../../../content/protocols/cell_culture/mtt_solubilization_readout/scenes/result_review.yaml) | [mtt_solubilization_readout/protocol.yaml](../../../content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml) |
| Electrophoresis endpoint | [electrophoresis_endpoint_display.yaml](../../../content/objects/equipment/electrophoresis_endpoint_display.yaml) and [gel_cassette.yaml](../../../content/objects/equipment/gel_cassette.yaml) | [endpoint_review.yaml](../../../content/protocols/sdspage/sdspage_run_electrophoresis/scenes/endpoint_review.yaml) | [sdspage_run_electrophoresis/protocol.yaml](../../../content/protocols/sdspage/sdspage_run_electrophoresis/protocol.yaml) |
| Gel image | [gel_image_results_display.yaml](../../../content/objects/equipment/gel_image_results_display.yaml) and [lightbox.yaml](../../../content/objects/equipment/lightbox.yaml) | [result_review.yaml](../../../content/protocols/sdspage/sdspage_image_gel/scenes/result_review.yaml) | [sdspage_image_gel/protocol.yaml](../../../content/protocols/sdspage/sdspage_image_gel/protocol.yaml) |

The authored sources show three kinds of duplication that a full plan must
remove:

- The Trypan Blue viability scene notes repeat the 92.5% result, 8.5 x 10^5
  cells/mL, and 85/7 manual check that are also embedded in the image. The
  display object itself owns only `visible`, so none of those scientific facts
  are declared by the object.
- The MTT monitor shows raw 0.28 A and 0.17 A endpoints with a 0.08 A blank,
  while `plate_reader` stores the blank-corrected 0.20 A and normalized 22%
  selected condition. The values are currently coherent, but their relationship
  is spread across SVG prose, protocol writes, overlays, and a Python test.
- `gel_cassette.migration_state` already owns `not_started`, `running`,
  `near_bottom`, and `overrun`, while the four SVG layers repeat those state
  names in pixels. Likewise, `lightbox` already owns lane, orientation, archive,
  and quality state while the full gel-result SVG repeats the same facts.

These are drift risks even before localization: a scientific correction can
update the protocol or object state while leaving an apparently authoritative
image unchanged.

### State and observation art

These six assets can retain their scientific geometry after labels move to DOM
or object data.

| Asset group | Embedded content | Migration direction |
| --- | --- | --- |
| [gel_migration_not_started.svg](../../../assets/equipment/static/gel_migration_not_started.svg), [gel_migration_running.svg](../../../assets/equipment/static/gel_migration_running.svg), [gel_migration_near_bottom.svg](../../../assets/equipment/static/gel_migration_near_bottom.svg), and [gel_migration_overrun.svg](../../../assets/equipment/static/gel_migration_overrun.svg) | `tracking dye at wells`, `dye migrating`, `stop: dye near bottom`, and `overrun: separation compromised` | Keep dye and gel geometry; expose state name, warning, and next action from the runtime state already declared in [gel_cassette.yaml](../../../content/objects/equipment/gel_cassette.yaml). |
| [electrophoresis_tank_module_mounted.svg](../../../assets/equipment/static/electrophoresis_tank_module_mounted.svg) | `mounted module, cassette, and buffer dam` | Keep the apparatus drawing; let `module_present` in [electrophoresis_tank.yaml](../../../content/objects/equipment/electrophoresis_tank.yaml) and accessible labels identify it. |
| [lightbox_image_bands_visible.svg](../../../assets/equipment/static/lightbox_image_bands_visible.svg) | Lane numbers and `L`, plus `samples 1-3` and `ladder` labels | Remove prose; decide in the plan whether sparse lane marks remain intrinsic or move into the result renderer backed by [lightbox.yaml](../../../content/objects/equipment/lightbox.yaml). |

### Equipment cleanup

These four files do not justify a new result-surface abstraction.

| Asset | Embedded content | Migration direction |
| --- | --- | --- |
| [hemocytometer_slide.svg](../../../assets/equipment/static/hemocytometer_slide.svg) | `Diamond mix chamber` and `Semicircle load` | Keep target geometry; expose region identity and action guidance through [hemocytometer_slide.yaml](../../../content/objects/equipment/hemocytometer_slide.yaml) and [trypan_blue_counting/protocol.yaml](../../../content/protocols/cell_culture/trypan_blue_counting/protocol.yaml). |
| `drug_vial_rack.svg` (deleted) | `Drug Stock` | Deleted after fresh reachability validation confirmed no authored learner workflow reference. |
| `electrode_module.svg` (deleted) | `GEL SLOT` and `ELECTRODE CORE` | Deleted after reachability validation confirmed the legacy static asset was not the open/closed object state used by [electrode_module.yaml](../../../content/objects/equipment/electrode_module.yaml). |
| `waste_tray.svg` (deleted) | `X Waste` | Deleted after fresh reachability validation confirmed no authored learner workflow reference. |

Older repository audits independently classified `drug_vial_rack` and
`waste_tray` as file-exists/mapping-missing orphans. See
[no_crop_missing_asset_audit.md](../../archive/plan-reset-2026-05-22/workstreams/no_crop_missing_asset_audit.md)
and [bundle_split_per_protocol.md](../../archive/web_ui/bundle_split_per_protocol.md).
Those historical reports corroborate the current reference search but do not
replace a fresh reachability gate in the implementation plan.

### Intrinsic marks

The following five former files contained only the kinds of sparse marks the
current policy permits, but they still contained live SVG text at the time of
this audit. All five were deleted after reachability validation, so no
path-only source remediation remains:

- `micropipette_rack.svg` (deleted): `020`, `200`, and `1000`;
- `t75_flask_v2.svg`, `t75_flask_v3.svg`, and `t75_flask_v4.svg` (deleted):
  `75`, `50`, and `25` graduations; and
- `well_plate_24.svg` (deleted): rows `A-D` and columns `1-6`.

The rendered path-only review also found already-outlined intrinsic marks:

- [heat_block_closed.svg](../../../assets/equipment/binary_state/heat_block_closed.svg)
  and [heat_block_open.svg](../../../assets/equipment/binary_state/heat_block_open.svg)
  show `65C` as an instrument setpoint;
- [power_supply_off.svg](../../../assets/equipment/binary_state/power_supply_off.svg)
  and [power_supply_on.svg](../../../assets/equipment/binary_state/power_supply_on.svg)
  show physical polarity symbols; and
- [falcon_15ml.svg](../../../assets/equipment/variable_volume/falcon_15ml.svg)
  and [falcon_50ml.svg](../../../assets/equipment/variable_volume/falcon_50ml.svg)
  show physical volume graduations and units.

Those path-only marks are permitted by the current intrinsic-mark rule. Their
presence also demonstrates why a no-live-text gate is necessary but not
sufficient: path conversion cannot decide whether words belong in artwork.

### Hidden and metadata text

[angry_professor.svg](../../../assets/equipment/static/angry_professor.svg)
contains a hidden `Created on AvatarMaker.com` text node. Remove or convert the
attribution according to its license and provenance requirements; never expose
hidden live text merely to preserve a credit.

At the time of the census, eight files carried `title` and `desc` metadata:

- [centrifuge_running.svg](../../../assets/equipment/binary_state/centrifuge_running.svg);
- [gel_opening_tool_hidden.svg](../../../assets/equipment/binary_state/gel_opening_tool_hidden.svg);
- [mtt_powder_vial.svg](../../../assets/equipment/binary_state/mtt_powder_vial.svg);
- `electrode_module.svg` (deleted after reachability validation);
- [kimwipe_pad.svg](../../../assets/equipment/static/kimwipe_pad.svg);
- [lens_tissue.svg](../../../assets/equipment/static/lens_tissue.svg);
- [paper_towel_pad.svg](../../../assets/equipment/static/paper_towel_pad.svg);
  and
- [recycle_buffer_funnel.svg](../../../assets/equipment/static/recycle_buffer_funnel.svg).

These descriptions are not visible labels, and some may be useful when SVG is
injected into the DOM. Static assets rendered through `<img alt="">` do not gain
an accessible name from internal `title` or `desc`, however. The full plan must
define one context-aware accessible-name owner and then retain, migrate, or
remove this metadata consistently instead of treating every metadata string as
either automatically good or automatically prohibited.

The live-text partition is exhaustive: seven application interfaces, six
labeled state/observation assets, four equipment-cleanup assets, five
intrinsic-mark assets, and one hidden-credit asset account for all 23 files.

## Existing reusable seams

The repository already contains most of the durable primitives needed for the
migration:

- [plate_reader.yaml](../../../content/objects/equipment/plate_reader.yaml)
  declares `result_state`, `mean_absorbance`, and
  `normalized_viability_percent` and renders exact values as DOM overlays.
- [gel_cassette.yaml](../../../content/objects/equipment/gel_cassette.yaml)
  declares the four migration states that should drive dye-front evidence.
- [lightbox.yaml](../../../content/objects/equipment/lightbox.yaml) declares
  result, lane, orientation, archive, and image-quality state.
- [hemocytometer_slide.yaml](../../../content/objects/equipment/hemocytometer_slide.yaml)
  already owns chamber identities, mixing, load quality, and observation state.
- Required authored `instruction` and `hint` fields in
  [PRIMARY_SPEC.md](../../PRIMARY_SPEC.md) already own learner next-action
  guidance and advance after each interaction.
- The DOM-overlay path in
  [scene_item.tsx](../../../src/scene_runtime/renderer/scene_item.tsx) already
  proves that typed object state can become visible application text without
  entering SVG geometry.

The full plan should extend these typed seams rather than create a parallel
results application or allow arbitrary authored HTML in YAML.

## Policy evidence

The ownership conclusion follows existing repository policy rather than adding
a silent new contract:

- [HUMAN_GUIDANCE.md](../../HUMAN_GUIDANCE.md) explicitly places identity,
  state, and instructional prose in DOM labels or object data and keeps SVG art
  language-neutral.
- [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md) rejects live text and permits
  only sparse physically intrinsic markings.
- [PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md) requires normalized SVG-backed
  physical scene objects, YAML-owned configuration, and visible connected
  browser completion through the same UI students receive.
- [PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md) requires the learner to see the
  correct state change and understand the next action.
- [normalize_svg_v3.py](../../../tools/normalize_svg_v3.py) is the canonical
  normalizer and emits `TEXT_UNSUPPORTED` for live text.
- [test_normalize_svg_v3.py](../../../tests/test_normalize_svg_v3.py) proves
  that imported editor-namespace cruft is stripped while attribution metadata
  survives.

The contract says physical clickable objects remain SVG-backed. It does not say
a complete scientific dashboard or decision interface must be flattened into
one equipment SVG. Any new authoring vocabulary still requires explicit user
approval; the ownership correction can first test whether current closed state,
overlay, and component seams are sufficient.

## Integration removal evidence

The executable desktop-editor integration is absent from the final tree:

- the shell wrapper, process adapter, adapter unit test, and real-editor E2E are
  deleted;
- [INSTALL.md](../../INSTALL.md), [USAGE.md](../../USAGE.md),
  [CODE_ARCHITECTURE.md](../../CODE_ARCHITECTURE.md),
  [FILE_STRUCTURE.md](../../FILE_STRUCTURE.md),
  [SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md), and
  [HUMAN_GUIDANCE.md](../../HUMAN_GUIDANCE.md) describe only optional librsvg
  preparation plus the repository normalizer; and
- [CHANGELOG.md](../../CHANGELOG.md) records the removal and preserves the
  historical sequence of the earlier adapter experiment.

Other than this audit's own explanation, an unrestricted `rg -i inkscape`
still finds four non-integration classes:

- the namespace URI and literal removal fixtures in
  [normalize_svg_v3.py](../../../tools/normalize_svg_v3.py) and
  [test_normalize_svg_v3.py](../../../tests/test_normalize_svg_v3.py);
- historical changelog and archive statements;
- source-editor provenance or metadata in
  [tissue_culture_flask.svg](../../../tissue_culture_flask.svg) and
  [falcon_50_media.svg](../../../servier/falcon_50_media.svg); and
- external-corpus names and observations in
  [other_repos_info.txt](../../../OTHER_REPOS/other_repos_info.txt) and generated
  audit data such as
  [normalize_svg_v3_wild_verdicts.json](../reports/normalize_svg_v3_wild_verdicts.json).

None of those paths executes the editor, declares it as a dependency, or
recommends it as a workflow. The namespace compatibility is retained so the
repository-native normalizer can safely accept and strip imported metadata.

## Evidence confidence

| Finding | Confidence | Basis |
| --- | --- | --- |
| 186 source SVGs and 23 live-text files | High | Reproducible filesystem and source-element census |
| 17 prohibited visible-text assets | High | Source text extraction plus rendered review |
| Seven complete or partial application interfaces | High | Rendered role, opaque runtime mode, object declarations, scenes, and protocol decisions agree |
| Five permitted intrinsic live-text assets | High | Source text plus rendered physical context |
| `drug_vial_rack.svg` and `waste_tray.svg` lacked current authored references | High | Exact-name searches across authored content and source, corroborated by historical audits; both were deleted after fresh reachability validation |
| Static `electrode_module.svg` was unreachable in a learner workflow | High | Live object uses open/closed assets; fresh reachability validation confirmed the legacy static asset could be deleted |
| Best implementation is one reusable result-surface model | Medium | Strong common ownership need; component shape still requires a representative prototype |
| Existing object vocabulary is sufficient without amendment | Open | Must be tested against all three representative screens before contract approval is requested |

## Target ownership

The migration plan should preserve one clear owner for each concern.

| Concern | Durable owner |
| --- | --- |
| Scientific measurements, observations, and result state | Closed object or protocol data plus runtime state |
| Learner-facing instructions, explanations, and decisions | Authored protocol guidance and accessible application DOM |
| Result tables, summaries, and status surfaces | Reusable SolidJS UI driven by typed state |
| Scientific evidence graphics such as bands, cells, and dye fronts | Code-native SVG/DOM component or language-neutral asset driven by state |
| Physical equipment shape and intrinsic marks | Normalized, language-neutral equipment SVG |
| Accessible name and description | Application semantics at the rendered context, not visible SVG prose |
| Future localization | Text-bearing content data and UI, never path geometry |

This audit does not choose between DOM/CSS, code-native SVG components, and a
hybrid evidence renderer. The full plan should prototype the three representative
screens against the same typed interface and choose the smallest reusable model
that expresses all three without an open-ended authoring escape hatch.

## Plan workstreams

The later full plan should cover these connected workstreams:

- define a closed result/observation data model from current scientific state;
- establish reusable accessible result surfaces and visual-evidence renderers;
- migrate the seven application interfaces before deleting their flattened
  source assets;
- remove labels from the six state/observation assets and four equipment assets;
- convert the five approved intrinsic-mark files to path-only source art;
- review `title`, `desc`, hidden text, attribution, and orphan reachability;
- add a source and publication gate for prohibited visible SVG text;
- replace SVG-word assertions and image-presence-only checks with semantic,
  state-driven application assertions; and
- regenerate all derived outputs and documentation from the canonical sources.

### Plan decisions required

The full plan must answer these questions with a representative prototype or
repository evidence:

1. Where does a result record live? Prefer existing object state when it owns
   the scientific fact; introduce a closed result record only if the three
   representative screens cannot share existing state cleanly.
2. Which visual layer renders evidence? Compare semantic HTML for tables and
   summaries, code-native SVG for scientific graphics, and a hybrid. Choose one
   typed component boundary, not one bespoke solution per protocol.
3. Which values are stored and which are derived? For example, MTT raw
   absorbance, blank-corrected absorbance, and normalized viability need one
   explicit relationship rather than three synchronized literals.
4. How are fixed teaching datasets authored? Preserve deterministic grading,
   but place the dataset in inspectable typed content rather than an image.
5. How does a result surface receive a context-aware accessible name and
   description? Define whether redundant evidence art is decorative and where
   equivalent tabular or textual content lives.
6. Which lane numbers, units, polarity marks, graduations, and true logos are
   physically intrinsic? Encode a small positive rule and classify every
   exception; do not create a general prose allowlist.
7. Which source assets become orphans after migration? Prove reachability from
   authored YAML through the generated manifest and delete superseded files
   rather than keeping parallel implementations.
8. Does any new object kind, state field, or authoring vocabulary remain
   necessary after the prototype? Request contract approval only for the
   smallest closed addition supported by evidence.

### Workflow evidence matrix

| Learner workflow | Current evidence | Required migrated evidence |
| --- | --- | --- |
| Trypan Blue manual count and viability decision | [test_pedagogy_outcomes.spec.ts](../../../tests/playwright/test_pedagogy_outcomes.spec.ts) proves visible decisions and guidance; the two full result images remain opaque | Visible UI creates the observation/result state, semantic quadrant counts and viability values match it, the decision uses those values, and reload preserves the next action and result |
| MTT readout and dose-response interpretation | [test_mtt_readout_visibility.py](../../../tests/test_mtt_readout_visibility.py) checks YAML writes plus SVG words; Playwright checks the monitor image and DOM overlays | One typed dataset drives raw, corrected, normalized, visual, and accessible output; Playwright verifies it through the visible reader workflow without parsing source SVG prose |
| SDS-PAGE endpoint decision | [test_pedagogy_outcomes.spec.ts](../../../tests/playwright/test_pedagogy_outcomes.spec.ts) checks the endpoint image, wrong choice, recovery, and power-off action | `migration_state` drives language-neutral dye evidence and semantic endpoint guidance; wrong choice leaves power state unchanged and reload resumes correctly |
| SDS-PAGE image interpretation | The same Playwright file checks the full result image plus lightbox state overlays and conclusion choices | Lightbox state drives lane/band evidence, lane metadata, archive status, quality, and conclusion; no result fact exists only in the image |
| Connected persistence and reset | [test_protocol_persistence.spec.ts](../../../tests/playwright/test_protocol_persistence.spec.ts) proves persisted visible actions on the production-shaped app | Each migrated result remains identical after reload, supports continued interaction, and resets through the same visible product path |

Any new object kind, state field, or protocol vocabulary item remains a contract
change and requires explicit approval under
[PRIMARY_CONTRACT.md](../../PRIMARY_CONTRACT.md). This scope report grants no
schema escape hatch.

## Settled decisions

- The three representative result SVGs are application interfaces, not
  instruments.
- Learner-facing labels, instructions, scientific values, and conclusions do
  not belong in equipment SVG geometry.
- Sparse intrinsic numbers, scientific units, polarity, graduations, plate
  coordinates, and true logos may remain when physically justified.
- The repository has no Inkscape executable integration. The former wrapper,
  process adapter, dedicated unit test, and dedicated E2E were deleted.
- Optional librsvg preparation and `tools/normalize_svg_v3.py` remain the
  supported path. The normalizer continues to recognize third-party editor
  namespaces only so it can strip imported non-rendering metadata.
- Historical changelog and archive references remain historical evidence, not
  operational guidance or executable integration.

## Acceptance for the plan

The future migration is complete only when all of the following are true:

- every source and published SVG contains no prohibited visible prose or label;
- the five approved intrinsic-mark assets contain no live SVG text;
- a reviewed positive exception list accounts for every remaining intrinsic
  number, unit, polarity mark, graduation, coordinate, or true logo, including
  path-only marks that an XML text scan cannot detect;
- the five fixed full-screen display objects no longer encode the same asset in
  both branches of a meaningless `visible` field;
- scientific values shown to learners come from the same persisted runtime
  state used by protocol logic;
- raw, derived, normalized, and displayed scientific values have one tested
  typed relationship rather than synchronized literals in SVG and YAML;
- learner-facing result content has accessible semantics and a localizable text
  ownership boundary;
- result headings, tables or lists, warnings, and decision evidence remain
  understandable without reading pixels from a decorative image;
- tests no longer parse result words from SVG source or stop at proving that an
  opaque result image is present;
- Playwright uses the production-shaped connected application, creates and
  mutates state through the visible UI, reloads persisted effects, and continues
  the same workflows;
- screenshots come from that same connected Playwright run and show the migrated
  result surfaces; and
- aggregate acceptance covers all affected cell-culture and SDS-PAGE paths,
  source and published SVG gates, generated outputs, and the complete browser
  suite; and
- no build, test, dependency, current operational document, or executable path
  invokes a desktop SVG editor.

## Out of scope now

This audit does not implement the result-surface migration, change scientific
values, introduce localization infrastructure, or approve new schema vocabulary.
It also does not require every SVG to become a SolidJS component: valid
language-neutral equipment art remains an asset.

## Validation record

Post-removal validation on the final material tree passed:

- focused normalizer and Markdown-link checks: 693 passed;
- expanded evidence-link and ASCII-compliance checks: 1,966 passed;
- `source source_me.sh && pytest tests/`: 6,237 passed;
- `source source_me.sh && ./super_all_tests.sh`: 20/20 categories passed;
- connected Playwright suite within the aggregate run: 115 passed; and
- `git diff --check`: passed.

The first aggregate attempt ran inside a restricted macOS sandbox. Chromium
could not register its Mach rendezvous service, so rendering, scene evidence,
visual regression, and browser gates failed or cascaded from missing render
stats. The exact aggregate command passed outside that browser restriction; no
application or test logic was changed to hide the environment failure.
