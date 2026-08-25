# Changelog

## 2026-08-25

### Behavior or Interface Changes

- Reorganized the SVG ingestion normalizer as the focused `tools/svg_normalizer/`
  package. The stable `tools/normalize_svg_v3.py` command is now a thin CLI
  launcher, while callers import the module that owns the required API.

### Fixes and Maintenance

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
