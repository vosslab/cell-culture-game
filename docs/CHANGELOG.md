# Changelog

## 2026-08-24

### Fixes and Maintenance

- The equipment SVG sweep adopted the de-shadowed Servier visual dialect.
  Detached floor shadows were removed narrowly while local form shading and
  semantic/runtime anchors were retained.
- Human review rejected the flattened water-bath redraw. Both water-bath states
  now use the normalized direct Servier geometry on one stable canvas, with its
  coherent projection, part order, local depth, and runtime anchors retained.
  The source has no detached floor-shadow candidate. The labeled contact sheet
  was updated after the broader human layer-order review completed.
- Removed exactly 40 unreachable retired static SVG variants after reachability
  validation. Seven result composites remain byte-preserved; their migration is
  deferred.
- Retired `assets/equipment/MISSING_SVG_PLACEHOLDERS.md` after confirming that
  no retained equipment SVG uses its retired dashed-box template. Reconciled
  `assets/equipment/SOURCES.md` and `assets/SVG_ASSET_GAPS.md` against the current
  recursive asset tree, including corrected DBCLS provenance for `tube_rack.svg`
  and the current vendored Bioicons filename for the protein-ladder microtube.
- Applied the human SVG review at the physical-object boundary: corrected the
  identified layer/projection defects, restored the authored T75 flask, reused
  the canonical microtube for protein samples, collapsed the opaque sharps
  container to one form, and replaced the binary gel-opening-tool model with one
  static approximately 8 cm aluminum lever. The final tree contains 132 ordinary
  equipment SVGs and seven deferred, byte-preserved result composites.
- Made scene generation strict for object/SVG resolution. Removed the authored
  `missing_svg` scene field, the alternate scene-emission mode, and the generated
  `svg_placeholder_keys.ts` compatibility surface. Layout-only impossible states
  now use an internal `render_error` diagnostic outside authored scene schema.
- The object validator now rejects paired runtime material bindings that fan out
  to several SVG forms. This enforces the canonical one-compiled-form rule at
  the object boundary instead of leaving it as a compatibility warning.

### Developer Tests and Notes

- Audited the SVG sweep against repository test policy. Permanent additions are
  limited to one inline provenance-parser regression and one `tmp_path` dry-run
  behavior regression; both are offline fast-lane tests. Exact counts, hashes,
  per-size renders, and contact-sheet construction remain one-time
  implementation evidence. The temporary generator was removed after use. The
  verified, self-contained final SVG was intentionally promoted to
  `docs/figures/` and linked from the README and usage docs for GitHub-based
  human review; the oversized PNG remains ignored implementation evidence.
- Re-audited the later template-vendored tests against the permanent-test
  checklist. Removed machine-dependent checkout-size, arbitrary source-line,
  and blanket AST annotation gates instead of turning implementation census
  checks into permanent product contracts.
- Final combined-tree validation passes 6,182 pytest cases, 115/115 Playwright
  tests, and all 20 exhaustive-suite gates. The strict SVG audit reports 129
  objects, 139 SVGs, zero findings, and zero orphans. One-time contact-sheet
  checks confirm 139 embedded assets, seven protected markers, unique local IDs,
  no external references, valid XML, and a 2400 x 7776 px raster render.

## 2026-08-23

### Behavior or Interface Changes

- After each accepted substep, the active interaction and ordinal are now the
  primary next-action message. The authored step goal remains visible.
- Protocol interactions now have a closed six-key schema: `target`, `gesture`,
  non-empty authored `instruction` and `hint`, `validator`, and `response`.
  There is no generic runtime guidance fallback. Repeated exact action
  signatures require distinct instruction and hint text, so both live surfaces
  advance with each materially different substep.
- Layout compilation now serializes a validated 44px minimum interaction frame
  for every clickable placement. Renderer-owned hit surfaces provide the
  durable interaction envelope, with bounds and overlap checks rejecting
  unrealizable scenes before they ship.
- Desktop scenes now own scrolling within their declared frame, while narrow
  layouts use normal document flow so the protocol remains reachable without
  viewport clipping. Active-target reveal exposes the next exact subpart and
  its affordance while keeping select-choice identity hidden.
- Student progress now autosaves to one versioned browser-session store after
  each settled accepted interaction. Reload restores the exact next action,
  declared scientific state, cursor state, and progress; the header reports
  save/restore availability and offers a confirmed protocol-scoped `Start over`.

### Fixes and Maintenance

- Removed the desktop-editor text-outline wrapper, its process adapter, and
  their dedicated unit and E2E tests. The repository-native normalizer remains
  the canonical SVG gate, with optional librsvg preparation for rare approved
  intrinsic marks. Imported editor namespaces remain accepted only so the
  normalizer can strip their non-rendering metadata.
- Scoped the broader asset-ownership defect in which complete result screens,
  observation panels, and instructional labels are flattened into equipment
  SVGs. The scope audit separates application-owned interfaces from removable
  labels and approved intrinsic marks before a full migration plan is written.

### Developer Tests and Notes

- Final SVG-sweep delivery validation passed: the production material contact
  sheet passed, `./run_playwright_tests.sh` passed 115/115, and
  `./super_all_tests.sh` passed 20/20. The final audit reports 131 objects,
  146 SVGs, and zero findings. The material baseline was intentionally
  refreshed after visual review; human visual approval of the labeled all-SVG
  contact sheet remains pending.
- The real Trypan Blue first step covers all five visible interactions,
  including hint pointer and keyboard use.
- The real viability choice proves generic hint non-disclosure while preserving
  post-rejection scientific feedback.
- Generator and YAML validation now share the interaction allow-list, reject
  partial or empty guidance, and reject literal select-identity or typed-value
  answer leaks using available content-registry evidence.
- Connected Playwright acceptance now advances through visible controls, proves
  the real production save record, reloads and resumes, completes the protocol,
  resets through the visible dialog, and captures screenshots from that same
  browser journey. The exhaustive runner bounds every auxiliary non-browser E2E,
  reaches Playwright before shell E2Es, and records hung process groups as
  explicit failures.
- Generated `test-results/` browser artifacts are outside source-lint scope, and
  the glyph-render browser test now removes its temporary compiled bundle even
  when browser startup fails partway through suite setup.
- The SVG migration scope records source assets, current YAML owners, semantic
  ownership boundaries, exact embedded content, runtime rendering consequences,
  reproducible census commands, source and workflow links, evidence confidence,
  plan decisions, and connected browser acceptance gates.

## 2026-08-03

### Fixes and Maintenance

- Implemented the P0/P1/P2 protocol-pedagogy audit across the cell-culture and
  SDS-PAGE pathways. Range-specific tools, fresh-tip continuity, realistic bulk
  and repeating transfers, visible calculation/observation decisions,
  per-well and per-lane material state, apparatus continuity, informative
  feedback, and interpreted experimental results now form coherent full runs.
- Normalized authored HTML entities at both protocol and object codegen
  boundaries. Committed YAML retains ASCII `&micro;M` / `&micro;L`, while generated
  labels, enum values, prompts, and runtime DOM text consistently use U+00B5.
- Preserved the MTT assay's dry, treatment-dependent formazan crystals as
  visible non-liquid evidence after decanting, then removed that evidence only
  after DMSO dissolution. The reviewed material baseline now covers 795
  protocol-host surfaces with no drift.
- Added a resolution ledger that distinguishes completed fixed teaching
  scenarios from six genuine evidence or contract blockers: Bradford inputs,
  ladder product/volume, local one-gel apparatus values, local microwave SOP,
  true conditional branching, and choice-only selection eligibility.
- Completed a six-pass pre-merge audit. Rejected scientific choices now show
  what the learner selected, the evidence-matching answer, and the authored
  scientific reason. Stale shell-pilot, generic-pipette, and active-plan
  guidance now points at the current implementation or archived evidence.
- Archived the completed semantic in-SVG liquid-rendering and protocol
  walkthrough-recovery plans after confirming that their milestones, release
  gates, and closure records were complete. Updated all tracked links to their
  history-preserving archive locations.
- Archived 63 closed audits and historical reports, reducing
  `docs/active_plans/` from 109 files to 45. Retained current generated
  baselines, material-pipeline evidence, and records still under review.
- Archived the remaining 21 completed decision records, seven completed audits,
  one obsolete pointer report, and the superseded material-issues prompt,
  reducing the active set from 45 files to 15. The retained set is limited to
  two audit outputs that current tools regenerate and 13 fixed-path generated
  reports or baselines; live source comments and specifications now cite the
  archived records.

### Decisions and Failures

- The exhaustive wrapper's optional Inkscape text-outline E2E is blocked by the
  installed Inkscape 1.4.4 CLI: under the suite it writes the outlined SVG but
  never exits, and a direct retry aborts with status 134. Experimental wrapper
  changes were reverted; all protocol, material-render, repository, and 105
  visible-browser tests pass independently of that authoring-tool defect.
- Audited the 17 material-amount no-op declarations added during the semantic
  renderer cutover. The declarations honestly preserve nonvisual numeric state,
  but they do not approve all affected objects as intentionally static: five
  have defensible complete-form visuals, while twelve retain visual-design debt.
- Prioritized learner-visible repairs for the MTT solution tube and both
  electrophoresis chambers, followed by categorical loaded/empty pipette cues
  and nonempty waste feedback. Future work must use semantic object geometry or
  complete forms rather than revive whole-object bounding-box fills.

### Developer Tests and Notes

- Saved the visual-intent findings in the legacy material-binding audit,
  including behavior-based acceptance guidance and a separation between useful
  one-time visual evidence and durable automated tests.
- Checked all 91 moved Markdown documents with the repository's archive-link
  flattener. A target-scoped apply repaired five basename-resolvable links with
  no delinked or unresolved targets; the final dry run found no remaining
  changes. The repository Markdown-link test passed all 561 cases.

## 2026-08-02

### Behavior or Interface Changes

- Replaced the inherited non-target 24-slot microtube rack in the focused
  SDS-PAGE heat-denaturation scene with the protocol's intended 8-slot rack.
  The learner now sees only the heat block and the rack used by the authored
  workflow, with no duplicate lookalike or item overlap.

### Fixes and Maintenance

- Restored explicit nonvisual composite declarations for retained material
  amount fields on static and complete-form objects. Protocol state remains
  available for conservation and validation without reviving the retired
  whole-object overlay renderer.
- Removed the dormant HTML bounding-box fill renderer that survived the
  semantic cutover. Unlowered `fill_height` formulas now fail loudly at the
  runtime boundary, and the anti-return lint rejects both SVG-rectangle and
  HTML whole-object fill reintroductions.
- Made `super_all_tests.sh` single-writer per checkout so concurrent exhaustive
  runs fail before overwriting generated render evidence, Playwright
  checkpoints, or `SUPER_LOG.txt`.
- Repaired the material-render audit at the DOM ownership boundary: compiled
  liquid metadata is read from the injected SVG host while asset and placement
  identity comes from the enclosing scene item. The capture now waits for DOM
  SVG injection, reports SVG load failures, and refuses baselines without both
  compiled-liquid and structured-subpart coverage.
- Versioned the material evidence as the post-cutover v3 surface model and
  refreshed it only after reviewing the authoritative protocol-host captures.
  The baseline now covers 56 compiled liquid regions and 578 generated
  structured-subpart surfaces instead of accepting retired anchor overlays.
- Updated the generated object-library E2E boundary to prove that static
  aspirating-pipette amount state compiles to a no-op while the variable-volume
  serological pipette retains its compiler-backed `fill_height` contract.

### Developer Tests and Notes

- Kept permanent coverage at behavioral boundaries: existing generated-scene
  and browser E2Es prove the rack correction, the generated-artifact E2E avoids
  exact dictionary snapshots, and the render baseline uses documented geometry
  and footprint tolerances instead of pixel equality. No fixture was added.
- Ran six independent plan, test, style, documentation, legacy-code, and comment
  reviews. Their actionable test and documentation findings were applied, and
  the legacy review exposed the dormant HTML fill path removed above.
- Aligned the browser degrade harness with the compiler-lowered empty-composite
  representation, so its valid control object no longer relies on the retired
  raw `fill_height` formula path.
- Passed `./super_all_tests.sh` after the cleanup: all 20 categories passed,
  including 5,819 pytest cases, all 42 scene preflights, the reviewed 634-surface
  material capture, and 102 visible browser tests.

## 2026-08-01

### Behavior or Interface Changes

- Completed the material-SVG cutover: object-level `fill_height` now renders
  only compiled material SVG gravity parts (fixed bottom, Y-scaled body,
  translated fixed-shape surface, and stationary reveal). Structured-subpart
  material rendering remains the separate generated-geometry mechanism.
- Added a compiler-owned optional maximum fill percentage for vessel forms. The
  medium bottle now caps at 85%, so requests at 85%, 90%, and 100% render
  identically without losing the meniscus.
- Corrected the 50 mL conical's full endpoint so the bottom of its concave
  meniscus reads at the drawn 50 mL graduation, and made the microtube's moving
  surface a complete highlighted ellipse with a darker front rim.
- Conical forms now narrow their authored meniscus uniformly below the declared
  body-start percentage, using that existing calibration rather than an
  asset-specific scale rule; a nonzero floor continues to apply before this
  geometry calculation.
- Added optional form-owned `data-vlab-fill-height-exponent` calibration:
  non-conical material SVGs may map normalized effective fill to height using a
  bounded power curve, while conical body-anchor calibration remains explicitly
  incompatible. This keeps one generic runtime path with no asset-name rule.

### Developer Tests and Notes

- Added `tools/render_liquid_volume_contact_sheet.sh` as the one-step front door for
  rebuilding and rendering all five variable-volume families. Its contact sheet
  records a Chicago creation timestamp and build ID, generates and labels a
  fresh random material color for each vessel family, and reports requested
  fill, rendered fill, and clamp state from the compiler-generated manifest.

### Removals and Deprecations

- Retired the ordinary object-level anchor-overlay renderer and its migration
  contract. Structural liquid anchors remain compiler-only source inputs; the
  runtime uses generated manifest handles rather than authored anchor lookup.

### Decisions and Failures

- The Falcon pilot showed that translating one whole-liquid group moves the
  bottom and leaves donor-level artifacts. The gravity-part contract and
  build-integrated anti-return lint now prevent that model from returning.

## 2026-07-30

### Fixes and Maintenance

- Repaired the GitHub Pages build environment by installing the declared
  Python dependencies under Python 3.12 and using deterministic `npm ci`
  installs.
- Enabled the setup actions' npm and pip download caches, keyed from
  `package-lock.json` and `pip_requirements-dev.txt`.
- Separated browser-derived scene-stat validation from the production Pages
  build. Pages now builds and uploads `dist/` without installing or launching
  Playwright; the fast and exhaustive validation front doors still render the
  required scene statistics explicitly before content validation.

### Developer Tests and Notes

- The failed Pages run stopped in `pipeline/gen_object_library.py` because
  `lxml` was declared but not installed. The workflow now consumes the
  repository dependency manifests instead of relying on runner-global tools.
- The local Pages build reached the browser-only scene-stat stage after
  generation, type-checking, and bundling, confirming that Python dependency
  installation was the reported CI blocker. The browser launch then hit the
  known macOS sandbox Mach-port restriction, which no longer affects Pages.

## 2026-07-29

### Behavior or Interface Changes

- Added optional root `initial_state` for a direct mini-protocol or sequence
  runner. Each entry is a validated object, subpart, or declared-group target
  plus flat declared state. The browser now owns a durable target-keyed
  session archive, projects the active scene from that archive, preserves state
  across scene changes, and restarts from the same root seed. A runner seed
  applies once; constituent mini-protocol seeds do not reset a running runner.
- Restricted sequence runners to non-empty, unique lists of direct
  `mini_protocol` leaves. The generator, YAML validator, TypeScript flattener,
  and Python stepper reject unknown, nested, or duplicate constituents instead
  of expanding an ambiguous or partial package.
- Directed well, lane, and rack-slot interactions now use their exact declared
  subpart geometry. The active target has a minimum 24 px clickable core,
  visible siblings remain available for ordinary wrong-target rejection, and a
  missing exact geometry fails instead of falling back to the parent object.
- Repaired the MTT material chain: 20 mg powder plus 4 mL PBS produces the
  12 mM solution; 25 uL MTT raises 200 uL wells to 225 uL; 90-minute reaction,
  decanting, 200 uL DMSO solubilization, source accounting, and 560 nm readout
  now agree. Drug dosing addresses the intended individual wells.
- Rebuilt the SDS-PAGE full run as 16 unique direct mini-protocol leaves with
  loading before lid connection. The normalized eight-slot rack, exact gel
  lanes, compatible gel-loading tip box, 150 V 30-minute run, and visible
  separated/stained/destaining/destained gel states now preserve the sample and
  ladder chain through imaging.
- The current-action rail now names the generated learner-facing label for
  every directed click, drag, type, and adjust interaction while retaining the
  matching scene highlight. Choice-style `select` interactions continue to
  conceal the correct answer and direct learners to the equally highlighted
  candidates.
- Timed protocol operations now replace the action prompt with an explicit
  `Lab process running` state. The rail names the running process and explains
  that the next highlighted action will appear automatically, so an
  intentionally inactive interval no longer looks like a dead end. Authored lab
  durations project to a brief 0.3-0.6 second browser acknowledgment rather
  than making the learner wait.

### Developer Tests and Notes

- Added focused seed, session-archive, runner-integrity, MTT-content,
  SDS-subpart-geometry, asset-audit, affordance, and walker-debug coverage.
  Targeted checks are the first acceptance evidence for these changes; the full
  fast-check, build, and complete Playwright gates remain pending and are not
  claimed green by this entry.
- Strengthened the schema-driven browser walker without adding protocol-specific
  branches. Before acting, it now proves that the authored target is visible
  and in the viewport, carries the expected painted active or candidate
  affordance, and matches a visible action cue for the same target and gesture.
  Directed cues must name the learner-facing object; `select` cues must not
  reveal the correct label and must present at least two visible candidates.
- Added timed-wait browser evidence. The walker requires both the scene timer
  and the explanatory action-rail state, captures a `waiting_<step>.png`
  screenshot, records visible interaction ordinal plus `stateRevision` and
  `lastStateDelta`, and resumes only after the visible runtime state changes.
- Made the walker's owned static-server startup independent of reverse DNS and
  Python's human-readable `http.server` banner. A loopback-only helper now
  publishes a machine-readable ready port before the browser navigates.

## 2026-07-23

### Additions and New Features

- Added `tools/outline_svg_text.sh`, an optional, transactional SVG
  text-to-path authoring preparer for approved intrinsic markings and legacy
  imports. It preserves source SVGs by default, validates its temporary output,
  preserves source permissions for explicit `--in-place` replacement, and
  remains outside runtime and build dependencies.
- Added a coordinate-free semantic-zone authoring path. Scene YAML now names
  ordered teaching zones while the shared layout manager lowers those
  identities to measured internal bands, lanes, bounds, and baselines. Added
  dedicated plate-focus bench and hood scenes so the 96-well plate can be an
  intentionally exaggerated foreground teaching object without authoring
  rectangles or per-scene scale coordinates.
- Added modular material rendering for whole-object SVG anchors alongside the
  existing structured-subpart path. Object assets declare a clipped interior
  and bounds; the renderer colors and fills that region from protocol material
  state without hard-coded object-specific drawing code.
- Added focused SDS-PAGE scenes for loading, staining, destaining, imaging,
  extraction, tank filling, buffer recycling, electrophoresis, and sample
  preparation. Each learning block keeps its protocol targets and the minimum
  coherent apparatus context instead of inheriting every object on the shared
  electrophoresis bench.

### Behavior or Interface Changes

- SVG source art is now documented as language-neutral: identity, state, and
  instructional prose belongs in layout-manager DOM labels and object metadata
  for localization and accessibility. Numbers, units or symbols, polarity,
  graduations, and plate coordinates remain permitted as sparse intrinsic
  markings; outlining prose is not an accessibility solution.
- Scene changes now reconcile persistent placement state into the new scene
  while replacing the initial scene atomically. Student-visible material and
  instrument state therefore survives legitimate scene transitions without
  leaking placements that are absent from the destination scene.
- The protocol shell presents a single current action, authored tip, recovery
  feedback, step outline, and terminal completion route through the typed shell
  adapter. Source filenames use the repository's snake_case convention, and
  non-ASCII UI glyphs are represented with source-safe escapes.
- The launcher groups full experiments ahead of focused practice and presents
  human titles and action-oriented entry points while retaining stable protocol
  identifiers only as data attributes.

### Fixes and Maintenance

- Corrected the OVCAR8 treatment sequence from the production protocol data.
  Every well now reaches the intended 200 microliter final volume across
  untreated, metformin-only, carboplatin-only, and combination regions; the
  learning outcome now states the seven authored dose concentrations.
- Replaced misleading, missing, or ambiguous scientific art for the cell
  counter cartridge, hemocytometer, biological safety cabinet, label pen,
  electrode module, gel assembly, heat block, microplate reader,
  electrophoresis power supply, rocker, staining tray, water bath, pipette-tip
  boxes, and waste families. Active state pairs now use distinct source art
  where the visual transition is pedagogically meaningful.
- Scoped TypeScript to the supported `typescript-eslint` peer range, retained
  version `26.07` in `VERSION`, `package.json`, and `package-lock.json`, and
  resolved `brace-expansion` to the patched 5.0.7 release.
- Repaired the package boundary in `pipeline.gen_scene_index`; it now imports
  its sibling through `pipeline.scene_inheritance` under the documented
  repo-root Python environment instead of depending on test-time `sys.path`
  mutation.

### Decisions and Failures

- Treated blind image recognition as an experiment rather than a filename
  assertion. Anonymous 600 px and 180 px review exposed several assets that
  were valid SVGs but depicted the wrong or ambiguous instrument. Targeted
  revisions were retained only after fresh reviewers recognized the intended
  families; low-specificity wipes remain a documented non-instrument backlog.
- Kept protocol YAML and protocol reference documents as the scientific source
  of truth. Layout, material rendering, and tests consume that content rather
  than introducing protocol-specific runtime branches or fixed scene
  coordinates.

### Developer Tests and Notes

- Replaced the historical standalone-viewer material baseline with a
  protocol-host capture that inventories SVG-anchor and structured-subpart
  surfaces, records visible-vs-hidden pixel evidence, aggregates failures
  across protocols, and reports browser diagnostics before failing.
- Added production-data regression coverage for the complete 96-well OVCAR8
  media-adjustment and drug-addition sequence, material-anchor readiness,
  semantic source scenes, structural gap guards, plate-focus layout, instrument
  state pairs, and waste-family rendering.
- Added bounded server ownership and duration coverage so browser tests start,
  verify, and stop their own server instead of relying on leaked Node or Python
  helpers.

## 2026-07-13

### Behavior or Interface Changes

- Implemented `TimedWait` as an ordered, blocking response operation. The step
  machine now pauses at each timed phase, rejects duplicate interaction input
  while waiting, and resumes the remaining response operations exactly once
  after elapsed notification. The scene store exposes runtime-only timed-phase
  flags, the object renderer shows the authored display hint in a visible status
  badge, and the browser clock compresses one laboratory hour to one second with
  a 0.5-2 second bound so long incubations remain visibly completable.
- Changed unsupported `LayoutMove` handling from a warning-only no-op to a
  descriptive exception. The ratified operation remains in the closed
  vocabulary, but the runtime no longer reports success without moving the
  placement.
- The shared numeric set-point editor now rejects blank, malformed, and
  non-finite drafts instead of silently committing zero. A rejected draft is
  surfaced through the existing visible error state and `aria-invalid`.
- `run_validate.sh` now forwards validator arguments, making
  `./run_validate.sh --strict` an explicit warning-failing entry point. Updated
  `run_fast_checks.sh` comments to describe its actual default policy: errors
  fail while warnings and advisories remain visible and non-failing.

### Tests and Quality

- Added focused regression coverage for ordered `TimedWait` pause/resume,
  duplicate-input rejection, render-state scheduling, browser-clock bounds,
  fail-loud `LayoutMove`, and set-point draft parsing.
- Updated both visible-UI walker implementations to recognize the rendered
  `data-timed-wait="active"` phase and wait for its bounded elapsed transition
  instead of misclassifying the intentional no-active-interaction interval as a
  stalled protocol.
- Rotated the 2026-07-04 day block into `docs/CHANGELOG-2026-07c.md` after the
  active changelog crossed the repository's 1000-line threshold; the active
  file retains the two newest day blocks.
- Removed stale links to the retired `tools/scorecard_m2.mjs` and
  `run_scene_health.py` entry points from the architecture, file-structure, and
  active metric-decision docs; these links were exposed by the full pytest gate.

## 2026-07-05

### Additions and New Features

- Extended the scene geometry dump (WP-1B1) in `tools/scene_stats.mjs`
  `computeGeometry`: each zone entry now carries `item_union_rect`, the measured
  edge-coordinate union of every rendered item tagged with that `data-zone`
  (null when no item rendered into the zone), distinct from the declared
  `bounds`/`inner_rect`. The geometry block also carries informational
  `provenance` (`renderer_bundle` with the built bundle mtime, and `rendered_at`),
  gathered by the impure caller `tools/scene_to_png.mjs` and passed in so
  `scene_stats.mjs` stays deterministic. Re-rendered all scenes via
  `node tools/scene_to_png.mjs --all` to regenerate
  `generated/scene_render_stats/*.stats.json` with the new fields.
- Added `docs/archive/decisions/scene_metric_calibration.md` (WP-2A1), a
  provisional scene-metric calibration set: eight real scenes from the round-0
  vision review (`docs/active_plans/reports/aesthetic_baseline_round0.md`)
  spanning the full verdict range, each with a plain-language judgment that
  anchors the `focal_dominance` and `instructional_grouping` scores. Meets the
  coverage floor (at least four usable calibration points per metric, anchored
  high and low). Status provisional; ratification is non-blocking. Serves as the
  ground-truth reference the bbox scorecard candidates in
  `docs/archive/decisions/aesthetic_review_metrics.md` are calibrated
  against before any metric is promoted to a gate.
- Added `docs/specs/NO_FIXTURE_POLICY.md`, the repo-specific no-fixture policy
  ("content is the fixture": curriculum content under `content/protocols/**`
  is exercised directly by the walker sweep; there is no separate diagnostic
  fixture surface). Linked from `AGENTS.md`.
- Documented the author-entity -> codegen-decode -> DOM-glyph convention once,
  canonically, in a new "Glyph rendering" subsection of
  `docs/specs/MATERIAL_YAML_FORMAT.md`, and cross-linked it (not restated)
  from the entity/ASCII hygiene rules in `docs/specs/OBJECT_YAML_FORMAT.md`
  (unit-strings note and file-hygiene note) and
  `docs/specs/PROTOCOL_YAML_FORMAT.md`.
- Added `tests/playwright/test_glyph_dom_render.spec.ts` (WP-A4): a browser
  DOM-text proof, on the real `drug_dilution_setup` content, that the
  guidance bar (`#guidance-text`), the outline step card text, and the
  card's `title` attribute (`step_outline.tsx`) all render the real
  U+00B5 micro sign glyph rather than the literal `&micro;` entity string.
  Verified non-vacuous by temporarily disabling the WP-A2 decode call and
  confirming all three assertions fail against the raw entity text, then
  restoring the decode call and confirming green.
- Added `tests/e2e/e2e_material_render.py` (WP-C1), a material-render
  regression guard: `tests/playwright/material_render_capture.mjs` renders
  every emitted scene through the real `dist/scene_viewer.html`, isolating
  each object-level `fill_height()` overlay's own painted pixels by diffing
  the same item bbox with the overlay visible vs hidden (per driving field,
  so a two-overlay object like the electrophoresis tank's inner/outer
  chamber never gets diffed against itself). The measured percent per
  `scene::placement_name::field_name` is baselined into
  `docs/active_plans/reports/material_render.json` (`--write-baseline`, or
  automatically on first run); every later run verifies against that
  baseline and flags a regression only when an entry grows more than 5
  percentage points above its recorded value, never rewriting the baseline
  itself. Per review feedback, replaced an earlier per-entry
  percent-threshold "known-bad" tag (an arbitrary per-object cutoff) with a
  single top-level `baseline_status: "known-bad-current-state"` field plus a
  `baseline_status_note`: EVERY current fill_height overlay paints the
  object's full item bbox rather than being constrained to the SVG liquid
  interior (`docs/ROADMAP.md:183`, deferred, out of scope for this guard) --
  the bug is structural to the shared overlay mechanism, not something a
  magic-number cutoff could isolate to "some" objects. The per-entry `tag`
  field stays empty, reserved for future targeted annotation once the render
  fix lands. The report header states plainly that this proves "no worse
  than baseline", not "material rendering is correct".
- Added `pipeline/entity_decode.py` (WP-A2), the codegen decode helper that
  turns authored HTML entities (named, decimal, and hex numeric forms) into
  their Unicode characters before emission into `generated/**`, so the
  runtime renders a real glyph as a normal DOM text node instead of the
  literal entity string. A closed-set dictionary lookup
  (`NAMED_ENTITY_CODEPOINTS`), not XML entity expansion, so it carries no
  XXE risk; an entity not in the map and not a valid numeric form passes
  through verbatim. Added `tests/test_entity_decode.py` covering named
  entities (`&micro;`, `&amp;`, `&alpha;`/`&beta;`), decimal and hex numeric
  forms, multi-entity strings, and the unknown-entity pass-through case.

### Behavior or Interface Changes

- WP-F1: intra-row vertical placement now BOTTOM-anchors objects to a shared
  shelf baseline instead of top-anchoring them.
  `src/scene_runtime/layout/vertical_layout.ts` routes every object through
  `anchorTop()` so `_top = _baselineY - _height`, replacing the old
  `_top = rowTop` pin plus per-object baseline back-solve (removed
  `objectTopInRow`, `baselineFromObjectTop`, `rowTopFor`). A shelf is one
  `depth_tier` across the side-by-side zones authored at the same `top..bottom`
  (a horizontal row); its shared baseline is
  `max(rowBottom - bottomLabelReserve, rowTop + maxObjHeight)` -- the lowest row
  bottom (tallest column defines the line), pulled up by any bottom-label
  reserve, and floored so the tallest object's top stays inside its row
  (containment). Result: unequal-height bottles in a row now sit their bottom
  edges on one common line (staining_bench rear reagent shelf; electrophoresis
  center working surface) instead of hanging from the row top. Aspect is
  preserved and no artwork is cropped (never-crop safe by construction). The
  reflow band/zone-merge logic and horizontal placement are untouched. Every
  pipette's `anchor_y: tip` uses `anchor_y_offset: 0`, so tips land on the shelf
  exactly like a bottom anchor; `anchor_y: top` is unused in content (engine
  fallback only). Scene-churn report:
  `docs/active_plans/reports/wp_f1_bottom_align_scene_churn.md`.
- Playwright `webServer.reuseExistingServer` is now always `false` (was `!CI`,
  i.e. reuse-allowed locally). Justification: the walker sweep
  (`tests/playwright/e2e/protocol_walkthrough.spec.ts`) intermittently failed 8
  `sdspage_*` protocols, and all 8 were a single root cause -- a stale served
  bundle, not any content, scene, asset, or runtime defect. With reuse enabled,
  a leftover `python3 -m http.server --directory dist` from an earlier run was
  reused and the `webServer` command's `build_github_pages.sh` rebuild was
  SKIPPED, so the walker booted an old `dist/protocol_host.js` whose embedded
  `PROTOCOLS` snapshot predated the sdspage protocols (observed: bundle built
  11:25, `generated/protocols.ts` regenerated 11:35). Five protocols crashed at
  boot ("protocol not found" -> `window.gameState`/`PROTOCOL_STEPS` never set ->
  `waitForFunction` 8000ms timeout, 0/0 steps); three others logged transient
  DOM-SVG fetch errors captured against that same stale build (57/2/2), which do
  not reproduce on a clean tree. Reusing a prebuilt static server decouples the
  bytes served from the current build; forcing a fresh build+serve on every run
  ties them back together. A clean rebuild turned all 8 green (`86 passed`). CI
  already ran with reuse off, which is why CI never saw this; local now matches.
- Authored HTML entities in protocol prompts/descriptions/`learning` fields,
  material names, and object labels now decode to their real Unicode glyph in
  `generated/**` via the WP-A2 codegen decode pass
  (`pipeline/entity_decode.py`), instead of shipping the literal entity
  string for the runtime to render as-is.
- Removed the `.object-graphic` box-shadow/drop-shadow styling in
  `src/style.css`; scene object artwork now renders without an added drop
  shadow.

### Fixes and Maintenance

- WP-F1: removed a now-stale `label_placement: bottom` override on
  `center_serological_pipette` in `content/base_scenes/electrophoresis_bench.yaml`
  (inherited by the eight `sdspage_*` workspace scenes via
  `extends: electrophoresis_bench`). The override existed to dodge a top-label
  collision with `ddh2o_bottle` in the OLD top-anchored layout; bottom-alignment
  moved `ddh2o_bottle` to the scene bottom, so that collision no longer exists
  and the override instead forced the label down into
  `front_left_mini_protean_gel`'s label, raising `unresolved_label_overlap` in
  all eight inheriting scenes. Removing the obsolete override lets the resolver
  place the label naturally and clears the overlap for real (no gate suppression,
  no baselined overlap).
- Fixed the dead build-freshness gate in `run_playwright_tests.sh`: it decided
  whether to rebuild `dist/` by testing for `dist/main.js`, a legacy
  single-bundle filename this multi-entry build never emits (the real runtime
  artifact is `dist/protocol_host.js`). The check now tests
  `dist/protocol_host.js` so a missing bundle actually triggers a rebuild;
  header comment updated to match.
- `pipeline/build_generated.sh` now exports `PYTHONPATH` to the repo root
  (mirroring `source_me.sh`'s own export) so the generator scripts'
  package-qualified imports resolve when the build script runs standalone,
  without requiring the caller to `source source_me.sh` first; reverted the
  in-code `sys.path` hack this previously papered over in
  `pipeline/gen_object_library.py`.
- Closeout reconciliation of `docs/CHANGELOG.md`: several agents working the
  same session had each appended their own full set of day-block
  subsection headings instead of writing under the existing one, leaving
  the 2026-07-05 and 2026-07-04 day blocks with duplicate, out-of-order
  `###` headings (per REPO_STYLE.md, one heading per category per day
  block). Merged every duplicate heading into a single instance per
  category, in canonical order, moving each existing bullet under its
  correct heading with no entry deleted or reworded. Then rotated the file
  per REPO_STYLE.md's "Changelog rotation" policy (1370 lines, over the
  1000-line threshold): ran `devel/rotate_changelog.py`, which kept the two
  most recent day blocks (2026-07-05, 2026-07-04) in `docs/CHANGELOG.md`
  and moved the older 2026-07-03 block, byte-for-byte, into the new
  `docs/CHANGELOG-2026-07b.md` archive (the existing `CHANGELOG-2026-07a.md`
  already held 07-01/07-02, so `b` is the next unused letter for the month).

### Removals and Deprecations

- Removed the `dev_smoke` `protocol_type` as a concept from the whole
  authoring and runtime surface: the Python codegen enum
  (`pipeline/gen_protocols.py`) and validator (`validation/yaml_schema`) now
  accept only `mini_protocol` and `sequence_runner`; the TypeScript
  `ProtocolKind` union dropped the third value; the runtime exemptions built
  around it were removed (`resolve_entry_scene.ts` no longer exempts an empty
  scene from the fail-loud guard; `authored_value_check.ts` dropped its
  `is_dev_smoke` plumbing). `dev_smoke`/fixture wording was purged from every
  editable local spec and doc.
- Neutered the four Playwright specs that depended on removed `dev_smoke`
  fixtures (`test_decoration_noninteractive`, `test_type_input_feedback`,
  `test_affordance_evidence`, `test_initial_scene_evidence_m1`, `.mjs` +
  `.spec.ts` pairs) to a skipped no-op with an "OBSOLETE: dev_smoke removed"
  header; their coverage is now carried by the real all-protocols walker
  sweep over `content/protocols/**`. Regenerated `generated/**` from the
  two-value protocol vocabulary; it contains zero `dev_smoke` references.
- Listed six tracked files for human `git rm` at closeout (de-referenced and,
  where executable, neutered so the gate stays green until removed):
  `tests/playwright/test_decoration_noninteractive.{mjs,spec.ts}`,
  `tests/playwright/test_type_input_feedback.{mjs,spec.ts}`,
  `tests/playwright/test_affordance_evidence.{mjs,spec.ts}`,
  `tests/playwright/test_initial_scene_evidence_m1.{mjs,spec.ts}`,
  `tests/playwright/smoke_fixtures/one_object.json`,
  `content/base_scenes_quarantine/well_plate_96_zoom.yaml`.
- Retired the "future plan may introduce a unit table doc" ASCII-unit stopgap
  in `docs/specs/OBJECT_YAML_FORMAT.md`: Greek-letter units are authored as
  HTML entities and render as their Unicode glyph via the codegen decode
  convention. Updated the two `200 uM` / `20 uL` ASCII examples in
  `docs/specs/PROTOCOL_AUTHORING_GUIDE.md` to the entity form (`&micro;M`,
  `&micro;L`) so the guide teaches what now renders. Closed the
  `docs/TODO.md` "Fix unit rendering for browser-displayed YAML labels" item
  as resolved.

### Decisions and Failures

- "Content is the fixture" is now the single documented rule for exercising
  protocol behavior; `dev_smoke` is removed as a concept rather than
  reformed. `docs/PRIMARY_CONTRACT.md` never named `dev_smoke`, so this is
  not a contract change.
- Recorded `docs/archive/decisions/scorecard_metric_spec_discrepancy.md`
  (RATIFIED): removed the `zone_footprint_balance` and `row_overcrowding`
  scene-design scorecard metrics. Both rewarded spreading placements across
  more zones, directly conflicting with the grouping design intent in
  `docs/specs/LAYOUT_ENGINE.md` ("group related objects into one zone;
  prefer fewer, fuller zones"); a correctly-grouped scene either could not
  compute the metric or was scored worse than a scene that split itself up
  to chase evenness. Overflow coverage for an overloaded zone remains via
  scene-lint rule `B2` `item_taller_than_zone`.
- Documented tier-alignment and zone-grouping as durable design principles
  rather than one-off scene fixes: added the "Zone population and alignment
  aesthetics" section to `docs/specs/LAYOUT_ENGINE.md` (group related
  objects into one zone; prefer fewer, fuller zones; reserve separate zones
  for genuinely separate physical regions) and grouping guidance to
  `docs/specs/SCENE_DESIGN.md`.
- Tightened `AGENTS.md` to a small set of bare-path pointers into `docs/*.md`
  rather than restating rules inline, and restored the `source source_me.sh
&& python3 ...` Python-execution convention pointer that had dropped out
  of the file.

### Developer Tests and Notes

- WP-1B1 verification, all green: added two deterministic unit tests in
  `tests/test_scene_stats.mjs` (per-zone `item_union_rect` equals the edge-form
  union of same-zone item boxes, and null for an item-free zone; geometry
  `provenance` echoes the caller-supplied stamp). Added a `data-zone` membership
  assertion to both `tests/playwright/test_scene_dom_contract_selectors.mjs` and
  its `.spec.ts` sibling: every item's `data-zone` must be a declared scene zone
  (from `window.__SCENE_GEOMETRY__`), guarding the union grouping against an item
  whose zone would silently drop out of every union. `./check_codebase.sh` 5/5
  (512 node tests pass); the `.mjs` contract test passes 214/0; the two contract
  specs pass under the Playwright runner. Observed the intended measured-vs-
  declared divergence in real output (e.g. `hood_basic` rear_left
  `item_union_rect.bottom` 575 vs declared `bounds.bottom` 398).
- WP-F1 bottom-anchor verification, all green: `npx tsc --noEmit` exit 0;
  `./check_codebase.sh` 5/5 (86 layout node tests pass, including rewritten
  bottom-alignment invariant tests); `precompute_layout.mjs` emitted 34 scenes
  with 0 non-exempt build failures; `e2e_layout_parity_16x9` GO 34/34 all-exact;
  `e2e_generalization_preflight` 34/34; 0 object overlaps across all 34 scenes;
  `./run_playwright_tests.sh` 86 passed / 0 failed. `passage_hood_detachment_
microscope_view` still raises 2 exempt diagnostics but is a PRE-EXISTING member
  of `BUILD_GATE_EXEMPT_SCENES` (intentional dense-by-design scene), not a
  regression from this change.
- `./run_fast_checks.sh` (renamed from `run_all_checks.sh` per the
  2026-07-04 entry below) green: 4963 pytest passed, build/typescript/pytest/
  validate all PASS. `run_validate` reports 0 errors. `./build_github_pages.sh`
  builds clean. `grep -rn dev_smoke generated/` empty. `pytest
tests/test_markdown_links.py` passed all 526 links checked.
- `./run_playwright_tests.sh` surfaced one pre-existing, unrelated failure:
  `test_scene_dom_contract_selectors.spec.ts`'s `missing_svg_check` case
  expected a scene that depended on the `tests/content/dev_smoke/` fixture
  tree removed by an earlier, separate initiative. Fixed by removing the
  obsolete `missing_svg_check` placeholder-contract case from the `.spec.ts`
  and its `.mjs` twin; `./run_playwright_tests.sh` now passes clean
  (83 passed, 5 skipped, 0 failed).
- `tests/e2e/e2e_material_render.py` verified: `--write-baseline` (after a
  full `bash build_github_pages.sh`) captured 231 fill-overlay entries across
  the 34 emitted scenes; running verify mode twice in a row reported
  `unchanged=231, regressed=0` both times (exit 0). Seeded a regression by
  lowering `bench_basic::rear_center_ethanol::material_volume`'s baselined
  `measured_percent` from 96.26 to 40.0 (a temporary edit to the baseline
  JSON, reverted immediately after) and re-running correctly raised it as the
  sole regression (`+56.26pp`, exit 1); reverting restored a clean exit-0 run
  (`unchanged=231` again). A real content-edit seed (bumping
  `micropipette.yaml`'s `held_material_volume` default, reverted) was
  attempted first but `bash build_github_pages.sh` was failing at the time on
  unrelated pre-existing `unresolved_label_overlap` gate failures in
  `electrophoresis_bench`/`extraction_workspace`/`sdspage_*` (concurrent WP-F1
  work in `vertical_layout.ts`), so the content edit was reverted without
  rebuilding and the baseline-level seed was used instead; `dist/` was
  unaffected since that gate runs before the bundle-write step. After
  replacing the per-entry threshold tag with the top-level `baseline_status`
  field (see above), re-wrote the baseline and re-ran verify mode twice more,
  confirming the new field does not trip the diff: `unchanged=231,
regressed=0, new=0, missing=0` (exit 0) both times. `pyflakes`, ASCII
  compliance, and `npx eslint` are clean on both new files.
- `tests/test_entity_decode.py` inline-case coverage (no fixture files) for
  `pipeline.entity_decode.decode_entities`: named entities, decimal
  (`&#181;`) and hex (`&#xB5;`) numeric forms, mixed strings (`Tris &amp;
EDTA`), and an unrecognized entity left verbatim.
