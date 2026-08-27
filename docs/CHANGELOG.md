# Changelog

## 2026-08-26

### Additions and New Features

- Added `tools/render_svg_library_review.mjs`, a developer helper that builds
  the shipped `docs/figures/equipment_kit/review.html` current-library gallery.
  It works under `file://`, live-links all current authored equipment SVGs, and
  provides search, behavior filtering, card sizing, and transparency backdrops.
- Added `dist/equipment_review.html`, built from an authored host and Solid
  component, for exhaustive HTTP review through the same shared SVG host used
  by production scenes. It exposes search, render-mode, backdrop, and size
  controls without creating a parallel renderer.

### Behavior or Interface Changes

- Rebuilt the equipment art after direct human review rejected the D01-D05
  candidate family as cubist rather than realistic laboratory equipment. The
  current direction uses physically credible forms and retains direct detailed
  Servier geometry only where it is visually adequate; the microscope is a
  controlled repository-authored compound-microscope adaptation after its
  direct projection proved inadequate.
- Applied the follow-up human rejection as a bounded recovery rather than a new
  redraw. Restored the established transparent T75 pair, Servier-derived open
  microtube, aligned heat block, lightbox, microwave, and logically separated
  electrophoresis lead states from the frozen equipment contact sheet.
- Removed the MTT-specific vessel entirely. Both MTT states select the canonical
  Servier-derived microtube; generic mass-capacity rendering shows the 20 mg
  powder at 8 percent and hides the compiled material region when empty.
- Deleted the four standalone red/black attached/unattached lead cards and their
  two object definitions. The electrophoresis tank now owns exact black/red
  terminal subparts and two tank-coordinate connection overlays; visible attach
  and disconnect actions target the actual terminal while the power supply owns
  only voltage and running state.
- Replaced the gel comb's false binary state with a single standalone comb.
  The cassette now solely owns its inserted-comb overlay, and the completed
  visible workflow introduces the removed comb without rendering a second
  cassette.

### Fixes and Maintenance

- Corrected the human-review routing. The D01-D05 candidate artifacts and the
  historical 139-asset contact sheet are explicitly rejected snapshots; the
  current 130-source gallery is `docs/figures/equipment_kit/review.html`, and
  `/equipment_review.html` exercises the production renderer.
- Removed the dedicated MTT vial and restored `capacity_mg` as a generic
  `fill_height` contract alongside microliter and milliliter capacities. The
  pre-weighed MTT object keeps its material identity and 20 mg amount while one
  canonical microtube owns all vessel geometry.
- Completed the six-pass code audit. Removed two rebuild-only permanent
  Node test files and one order-dependent browser assertion, clarified the
  former E8 shipping-render-mode evidence gap. A built all-manifest page now
  proves 60 DOM-SVG and 74 image assets through the production host with zero
  load, render-mode, namespacing, aspect-ratio, or browser failures. The final
  second-pass rerun covers 64 DOM-SVG and 66 image assets.
- The independent post-implementation audit corrected the current 130-asset
  contact-sheet routing, removed stale plan and normalizer commentary, and
  restored Git-based repository-root discovery in pipeline entry points as
  required by `docs/REPO_STYLE.md`. It also repaired README and file-structure
  links after the committed license-filename normalization.
- The recovered tree passed the build with 129 objects, 70 asset specs, 134
  SVGs, 60 DOM-required assets, and 57 scenes; all five codebase checks with 673
  Node passes and two skips; 7,682 pytest cases; and all 113 Playwright cases.
  The second-pass build contains 127 objects, 67 asset specs, 130 SVGs, 64
  DOM-required assets, and 58 scenes. Its current gates pass 7,662 Python tests,
  673 Node tests with two skips, and all 113 Playwright tests. Its
  production-host review passes all 130 cards with zero load or mode failures.

## 2026-08-25

### Additions and New Features

- Added a calibration-first SVG equipment visual-quality rebuild plan. It preserves the completed
  structural SVG work while requiring human art-direction approval, reference-backed family
  construction, consumer-specific review surfaces, and small review batches before broad redraws.

### Behavior or Interface Changes

- Completed the SVG visual-quality rebuild through M12. That day's 135-SVG
  equipment tree uses the selected D04 occlusion-strong construction with D01
  restraint; seven result interfaces remain byte-preserved application UI.
  The completed compact viewer preserves a 1152 x 648 label-safe scene in one
  local scrollport and renders resolved state facts in the external
  occurrence-keyed observation rail. Measured orange, blue, and blue-gray
  contrast repairs meet the 3:1 non-text floor on their rendered surfaces.

- Moved resolved object-state text out of the measured scene stage into a
  placement-, field-, and occurrence-keyed observation rail in the existing
  scene scrollport. Stateful mounts now require that explicit rail host rather
  than silently dropping facts.
  Layout-engine labels remain in place, while the host now combines the emitted
  interaction minimum with a shared 16:9 label-safe floor. This keeps compact
  scenes and active/candidate rings readable without changing SVG/YAML state
  contracts or adding a second scroll region.
- Raised the directed active-object and exact-subpart affordance from `#f5a623`
  to `#9e6507` (including its translucent fill RGB), and shared light-surface
  focus outlines from `#f0a202` to `#c48402`. These measured replacements keep
  the orange state role distinct from the dashed blue candidate role while
  meeting the 3:1 non-text contrast floor on their rendered surfaces. The
  shared blue hover cue now uses solid `#2563eb` rather than a failing 45%-alpha
  blend; its 2px solid form remains distinct from the 3px dashed candidate ring.
- Raised the shared light-surface control and observation-rail border from
  `#829ab1` to `#718aa3`. The blue-gray remains visually subordinate to state
  affordances while clearing the 3:1 graphical-boundary floor on the rail,
  rail items, reset controls, and value-entry input surfaces.
- Reframed the SVG equipment visual-quality rebuild around M0-M12: exemplar-first evidence, a shortlist
  of about five real-size candidate directions, user preference when available, and an evidence-recorded
  manager default otherwise. Its opening ledger, Servier sweep, and size census now run concurrently as
  provisional file-disjoint evidence before reconciliation; the measured kit preserves all five candidate
  fixtures alongside Servier-source/provenance checks, reference-backed volumetric construction,
  family-owned rebuilds, and real-consumer validation.
- Reorganized the SVG ingestion normalizer as the focused `tools/svg_normalizer/`
  package. The stable `tools/normalize_svg_v3.py` command is now a thin CLI
  launcher, while callers import the module that owns the required API.

### Fixes and Maintenance

- Closed the six-pass SVG rebuild audit findings. The canonical architecture
  inventories now include the candidate renderer and XML census tools; the old
  139-asset contact sheet and sweep ledger are explicitly historical rather
  than current review surfaces; and the active plan's milestone count and
  evidence routing are internally consistent.
- Re-audited the SVG rebuild checks against the permanent-test checklist.
  Removed four implementation-evidence test files covering candidate tooling,
  census reporting, exact compact-frame measurements, and the dedicated
  annotation-rail layout proof; removed the audit-added P200 paint and
  direct-store rail assertions; and reduced liquid endpoint coverage to three
  durable pure behavior cases. No SVG-rebuild test-only fixture or
  rebuild-specific fast-lane network check remains.
- Split the oversized Python generators, validators, scene-lint rules, manual
  renderer, stepper state/operations, SVG audit, and normalizer tests into
  cohesive modules. All eleven requested Python surfaces are now below the
  1,000-line limit, with their specific line-limit exceptions removed.
- Corrected the normalizer package boundaries and direct consumers, including
  editor-cruft cleanup, transform identity ownership, pattern classification,
  and the scene semantic-inspection geometry imports.
- Corrected pyflakes issues in scene-lint findings output and manual interaction
  rendering while preserving the repository's direct-module import convention.
- Updated the SVG consistency plan, embedded-interface audit, and architecture
  maps for the normalizer package and extracted pipeline helpers. Retired-test
  references now remain accurate without linking to deleted files.

### Developer Tests and Notes

- Completed a disposable, filename-blind visual inspection of the former 135
  authored equipment SVGs at 600 px and 180 px before renewed human review.
  Human review then exposed connector logic, arbitrary projection, duplicated
  labware, and artwork-regression failures that the blind pass missed. The
  evidence report now records that limitation and remains outside permanent
  test coverage.

- The 2026-08-25 repository-rule-audited tree passed 7,694 pytest cases; all five
  `check_codebase.sh` gates with 677 Node passes and two skips; 115 built-app
  Playwright cases; and `git diff --check HEAD`.
- That day's frozen-tree validation passed: `git diff --check`; 7,694 pytest cases;
  `./check_codebase.sh` with 677 Node passes and two skips;
  `./build_github_pages.sh` with 135 SVG entries and 57 scenes; and the isolated
  browser front door with 115 Playwright cases.
  The inventory, M2 provenance sweep, and ownership matrix each reconcile all 135 source paths,
  and the seven protected result SVGs remain byte-identical to HEAD.
- Rotated the changelog after it passed the 800-line threshold. The active file
  retains the 2026-08-25 and 2026-08-24 day blocks; older blocks are preserved
  in `docs/CHANGELOG-2026-08a.md`.
- `tests/test_source_file_line_limit.py`, `tests/test_function_typing.py`, and
  `tests/test_pyflakes_code_lint.py` pass. The focused normalizer, SVG-layer,
  Markdown-link, and ASCII suites pass. The full pytest run reports 7,281
  passing tests.

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
