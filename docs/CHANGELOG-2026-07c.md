## 2026-07-04

### Additions and New Features

- Adopted the Playwright test-runner model (`@playwright/test` +
  `playwright.config.ts` + `.spec.ts`) as this repo's single Playwright model.
  Phase 1 landed the config plus one real smoke spec, proven green end to end
  through the config's managed `webServer`. Added `playwright.config.ts` at the
  repo root: `testDir: tests/playwright`, `testMatch: **/*.spec.ts`, a single
  headless chromium project, `reporter: list`, and a `webServer` block whose
  command BUILDS then SERVES (`bash build_github_pages.sh && python3 -m
  http.server <port> --bind 127.0.0.1 --directory dist`) so every worker shares
  one built-artifact server. Port honors the repo random-port convention
  (`8000 + rand(0..999)`, `PORT`-env overridable); the chosen port is persisted
  into `process.env.PORT` so the main runner and worker processes agree, pinned
  into both the `webServer` url and `use.baseURL`, and a bind collision fails
  loud (no free-port scan). Added `tests/playwright/smoke.spec.ts` (converted
  from `test_protocol_selector.mjs`): loads the launcher over HTTP, asserts the
  "Virtual Lab Protocols" heading via `getByRole`, that protocol cards render,
  that a real click on the `mtt_reagent_prep` card navigates to its page, and
  that `#scene-root` mounts a clickable `[data-item-id]` object; web-first
  `expect` replaces fixed sleeps; screenshots numbered into `test-results/`.
  The already-runner-shaped `run_playwright_tests.sh` now works unchanged
  (`1 passed`).
- Completed the runner-model migration (Phases 2-4). Converted the remaining
  23 library-model `.mjs` tests to `tests/playwright/*.spec.ts`, and the
  custom worker-pool walker sweep to
  `tests/playwright/e2e/protocol_walkthrough.spec.ts`: it discovers every
  `content/protocols/**/protocol.yaml` id (`helper_protocol_discovery.mjs`),
  emits one `test()` per protocol inside a `test.describe.configure({ mode:
  "parallel" })` block so native Playwright workers replace the old
  `--jobs`/`--server-url` pool, and adds a wrong-object-click negative test
  (`sdspage_heat_denature_samples`). Renamed non-test support files to a
  `helper_` prefix (`helper_scene_discovery.mjs`/`.d.mts`,
  `helper_degrade_harness.tsx`, `helper_scene_reactivity_harness.tsx`,
  `helper_subpart_render_harness.tsx`, `helper_protocol_discovery.mjs`/`.d.mts`,
  `helper_walker.mjs`/`.d.mts`) per `PLAYWRIGHT_TEST_STYLE.md`'s reserved
  bare-underscore-for-scratch convention.
- Generic structured material-area verification in the general walker. The
  schema-driven walker (`tests/playwright/e2e/protocol_walkthrough_yaml.mjs`)
  now asserts subpart material writes, not just progress signals. `walker_debug.ts`
  gains a read-only `activeMaterialEffect` projection on the frozen `gameState`
  surface: for the active interaction it exposes `{object_name, material_field,
  material_value, expected_subparts}`, computed purely from the interaction's
  `ObjectStateChange` ops, the object's declared material-tint subpart contract
  (`find_material_tint_subpart_field`), and the SAME group fan-out the runtime
  applies (`expand_subpart_group_target`). `walker_helpers.mjs` gains a generic
  `readSubpartOverlay` (reads every `[data-subpart-overlay] [data-subpart-name]`
  shape's material + fill) and `verifyMaterialAreaEffect`: after each material-
  writing interaction it asserts EVERY targeted member subpart carries the
  authored material (fill changed on a real transition) AND every other rendered
  subpart kept its prior material/fill ("and nothing else", MATERIAL_DESIGN.md
  spatial correspondence). This generalizes the bespoke 5-of-96-well
  `test_all_wells_group_write_walkthrough.mjs` to all 96 members plus the
  negative check, with no per-protocol branch. Added
  `tests/test_material_area_verify.mjs` (node unit test) exercising the positive,
  silent-no-op, stray-change negative, missing-overlay, and bulk paths.

### Behavior or Interface Changes

- Standardized liquid-container sizes to a discrete 6-bucket capacity+width
  ladder in `docs/specs/SCALING_MODEL.md`; set discrete `display_width_cm` on
  the true bottles (M=10, L=12, XL=14; the `running_buffer_1x_carboy` carboy
  kept at 18).
- `run_all_checks.sh` renamed to `run_fast_checks.sh` to state its fast-gate
  scope (it does not run the browser walker sweep); repointed the
  `package.json` `check:all` alias and updated `docs/FILE_STRUCTURE.md` and
  `docs/CODE_ARCHITECTURE.md` references. The `git mv` completing the on-disk
  rename is a follow-up human action.
- `run_playwright_tests.sh` is now the single front door for every browser
  test (`npx playwright test` against `playwright.config.ts`); `super_all_tests.sh`'s
  browser step collapsed from a hand-maintained list of individual `.mjs`
  invocations to one call to `run_playwright_tests.sh`.
- Playwright runner suite: known-routed browser reds are now documented
  expected-fails via `test.fail()` with inline routing reasons
  (`cell_culture_full` mp5; `plate_drug_treatment_drug_addition` and
  `per_well_drug` `tube_A` subpart OP1; `microscope_basic` overlap O6) -- a
  green suite now means "green minus documented routed items," and an
  unexpected pass flips the annotation so it self-clears.
- The all-protocols walker sweep (`tests/playwright/e2e/walk_all_protocols.mjs`)
  now runs protocols through a bounded concurrent worker pool served by ONE
  shared static server, replacing the earlier rejected design that spawned N
  per-slot servers derived from a hardcoded base port 8126. Server ownership is
  now injectable: the sweep starts a single read-only `python -m http.server`
  on ONE random port `8000 + floor(random*1000)` (the canonical repo pattern
  from `run_web_server.sh` line 64, `PORT="${PORT:-$((8000 + RANDOM % 1000))}"`,
  overridable by the `PORT` env var), waits for it, injects its URL into every
  walker child via a new `--server-url` flag, and kills it once at the end
  (including on error paths). A static serve is read-only, so all concurrent
  walks safely share the one server; per-walk isolation comes from each walker
  running as its own child process (fresh browser context, fresh
  gameState/localStorage) writing into its own `--out-dir`
  (`test-results/walker/runs/<id>/`). There is no free-port scan and no
  collision-retry loop: one random port is picked and used. Default job count is
  now `min(8, max(1, os.cpus().length - 2))` (the shared server is one process,
  not one-per-walk, so the browser-child bound is what matters); override with
  `--jobs N` (forwarded through `run_playwright_tests.sh`). The single-protocol
  walker (`tests/playwright/e2e/protocol_walkthrough_yaml.mjs`) is now injectable
  too: with `--server-url URL` it spawns no server and navigates against the
  injected origin; without it (SELF-SERVE default) it picks its own random
  `8000 + floor(random*1000)` port (overridable by `--port` or `PORT`), spawns
  its own server, and tears it down. The old hardcoded 8126 default is gone. The
  sweep still archives each run's report to the stable
  `test-results/walker/reports/<id>.json` path and writes the worst-first
  `test-results/walker/sweep_summary.json`, so every downstream reader (the
  click-bug register) is unchanged. Exit-code contract preserved: nonzero if any
  FAIL or error. Verified parallel vs serial (`--jobs 1`) verdicts match exactly
  across all 31 protocols (0 mismatches; PASS=27 / FAIL=4). The 4 reds are the
  known owned/held set (`plate_drug_treatment_drug_addition` pedagogy-held
  subpart-click, `passage_hood_detachment` transit-scene target, and the
  `cell_culture_full` / `routine_passage` sequence-runner timeouts); no protocol
  went newly red under concurrency.

- Sweep output is now colorized and gated. Verdicts print green (PASS), red
  (FAIL / error), and yellow (unsupported_gesture) ANSI codes ONLY when
  `process.stdout.isTTY` is true AND `NO_COLOR` is unset (https://no-color.org);
  piped/CI output and `sweep_summary.json` stay plain text and parseable. A live
  line prints as each protocol FINISHES (interleaved under concurrency) with its
  verdict, id, and duration, and the worst-first summary table plus Totals line
  are retained. Column padding is applied to the visible verdict text before the
  color codes are added, so alignment is unaffected by the invisible escape bytes.
  The sweep also now strips any SGR ANSI a walker child's failure reason embeds
  (Playwright's own dim-styled locator-timeout text) before printing the reason
  column or writing `sweep_summary.json`, so a piped sweep emits zero escape
  bytes and file output stays plain regardless of the child's formatting.

- The general walker now reds a protocol whose subpart material write silently
  no-ops or leaks to the wrong subpart (previously only progress signals were
  asserted). Full sweep after the change: 26 PASS / 5 FAIL (of 31), the SAME 5
  pre-existing non-material failures as the baseline (load-timeout and
  scene-target-missing bugs upstream of any material step). Newly-red count: 0 --
  every reachable well-plate write verifies correctly. Coverage spans both bulk
  and PARTIAL group writes: `mtt_solubilization_readout` and
  `cell_seeding_plate_setup` (`all_wells`, 96/96 members) exercise the positive
  path; `plate_drug_treatment_media_adjustment` (`block_*` group writes) exercises
  the NEGATIVE "and nothing else" path live, verifying 6 members with 90 other
  subparts unchanged and 42 members with 54 unchanged.
- M12 "Adjust/drag primitives": `dispatch_gesture`'s single `adjust`/`drag` seam arm
  (previously a throw "declared seam not yet wired (M12)") now routes to
  `handle_adjust_commit` / `handle_drag_commit` and returns the runtime accept
  signal; both `GESTURE_REGISTRY` rows flip `wired: false` -> `wired: true`.
  `protocol_host.tsx` mounts the `SetPointEditor` overlay in its own body-appended
  root beside the type-input overlay, routing its committed number through the same
  single registry dispatch point. The walker's `SUPPORTED_GESTURES` grows to
  include `adjust` (drag stays sweep-unsupported only because no content protocol
  authors a drag yet; the wired path is proven by the step-machine unit test plus
  the walker driver). Walker evidence: `mtt_reagent_prep` now COMPLETES all 4 steps
  through visible UI via a real adjust interaction (`set_volume` 1000 filled and
  committed on the visible `[data-adjust-input]` / `[data-adjust-commit]`), where it
  previously classified `unsupported_gesture`. The all-protocols sweep moved from
  6 PASS / 15 `unsupported_gesture` / 10 FAIL to 12 PASS / 0 `unsupported_gesture`
  / 19 FAIL: every previously adjust-blocked protocol is now driven by the affordance
  (unsupported dropped to zero), 6 of them now PASS, and the rest fail on unrelated
  pre-existing content defects (missing scene item ids, sequence-runner timeouts,
  and M8 ambiguous-target reducer crashes on interactions AFTER the adjust). The M2
  gesture-collapse guard in `step_machine.ts` is preserved (M13 removes it).
- M12 content fix (`content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml`):
  disambiguated the `prepare_solution_tube` PBS target from the bare object_name
  `pbs_bottle` (which the scene places twice: inherited `rear_center_pbs` plus the
  workspace-added `rear_center_pbs_bottle` "for dissolving MTT") to the specific
  placement_name `rear_center_pbs_bottle`. The bare object_name is ambiguous to the
  M8 target adapter and crashed the snapshot reducer once the walker (now driving
  adjust) reached that interaction; naming the placement is the M8-sanctioned
  disambiguation path. A parallel `media_bottle` double-placement blocks
  `plate_drug_treatment_media_adjustment` the same way and remains for a later pass.

- M11 "Affordance registry": `protocol_host.tsx` no longer routes gestures inline. The click
  resolver callback now derives a `GestureCommand` from the live snapshot via
  `scene_click_to_command` and hands it to `dispatch_gesture`; the `TypeInput` `on_commit`
  routes the `type` gesture through the same `dispatch_gesture` and returns the runtime's accept
  signal for the visible rejection message. The behavior of `click`, `select`, and `type` is
  unchanged: select still promotes a click on the active target and rejects a non-active target,
  and type still fills + commits `[data-type-input]` / `[data-type-commit]`. Walker evidence:
  `sdspage_assemble_electrode_module` completes all 4 click steps; `select_check --wrong-order`
  rejects the wrong-order click on `ethanol_placement` (no advance) then advances on the correct
  `pbs_placement` select; `type_check` commits "42" and advances. The 443-test Node suite stays
  green (441 pass, 2 skipped).
- M8 "Target adapter": the protocol-target-to-DOM key moved from the non-unique `object_name`
  to the unique-per-placement `placement_name`, resolved through the single new
  `target_adapter.ts` (per the M7 decision `docs/archive/decisions/target_identity.md`). No
  existing protocol `target` string changed: the adapter auto-derives `object_name -> its unique
  placement_name` for every singly-placed object. `scene_item.tsx` now sources `data-item-id`
  from `item.placement_name` (both the placeholder and normal render paths), keeping M6's
  `is_clickable` gate, and the affordance highlight compares the item's `placement_name`;
  `affordance_candidates.ts` enumerates the candidate set in `placement_name` space;
  `click_resolver.ts` reads the DOM key back through the adapter (`TARGET_DOM_SELECTOR` /
  `placement_name_from_element`). The snapshot reducer (`create_snapshot_reducer`, new optional
  resolver arg) normalizes `active_interaction_target` to the resolved `placement_name`, so the
  walker's `activeTarget`, the `protocol_host.tsx` select-promotion equality, and the affordance
  ring all agree with the DOM `data-item-id`. `step_machine.ts` takes a new optional
  `target_adapter` option and normalizes BOTH sides of the `handle_click` and `handle_type_commit`
  target equality to `placement_name`, feeds the same resolved values into the interaction
  validator (which re-checks `clicked_target === interaction.target`), and normalizes the
  `target_with_value` / `final_state_matches` state reads to the `object_name` store key (the
  scene store stays `object_name`-keyed, so two placements of one object share one state). The
  new resolver args default to identity, so pure unit tests (target == placement == object) stay
  green. `protocol_host.tsx` rebuilds the scene-scoped adapter from each mounted scene's
  `PipelineResult.final` and threads a stable delegating wrapper into the step machine and
  reducer. Walker evidence: `sdspage_assemble_electrode_module` completes all 4 steps clicking
  real placement_names that differ from their object_names (`center_electrode_module`,
  `rear_center_electrophoresis_tank`), and the `--wrong-order` run rejects a wrong placement
  before advancing on the correct one.
- M6 "Enforce capabilities in renderer and candidate enumeration": interactivity is now a
  modeled property instead of an emergent side effect of "every rendered item gets an id".
  `src/scene_runtime/renderer/scene_item.tsx` stamps `data-item-id` only when
  `item.capabilities` includes `"clickable"`; a `decoration_only` object or a missing-object
  placeholder (bound with `capabilities: []`) now renders with no `data-item-id`, so it gets no
  cursor/hover/ring CSS affordance and is invisible to the delegated `click_resolver`.
  `src/scene_runtime/renderer/affordance_candidates.ts` `enumerate_candidate_targets` applies the
  same capability gate, so the resolver-accepted candidate set can never include a non-clickable
  item. Removed the dead, always-empty `data-target-id=""` attribute from the renderer, from
  `docs/specs/INTERFACE_VOCABULARY.md`, and from `tests/playwright/test_scene_dom_contract_selectors.mjs`
  / `tests/playwright/test_interaction_attrs.mjs` (both updated to assert `data-item-id` only
  when present, since a scene may now legitimately render non-clickable items).
- M9 "Typed gesture/validator unions": `ValidatorReference`
  (`src/shell/adapter/types.ts`) is now a discriminated union keyed on `preset`,
  mirroring the existing `SceneOperation` union, replacing the loose bag where any
  preset could carry any field. Five member interfaces (`CorrectTargetValidator`,
  `CorrectChoiceValidator`, `TargetWithValueValidator`, `SequenceCompleteValidator`,
  `FinalStateMatchesValidator`) encode field legality per preset: `target_with_value`
  carries the flat `value` map, `final_state_matches` carries `target` plus the flat
  `contains` map, and the three field-free presets carry `preset` only. Illegal fields
  are typed `never` on each variant so they cannot be authored on the wrong preset,
  while remaining declared optional keys so the step machine's and authored-value
  checker's union-wide reads keep resolving without narrowing (no changes forced in
  `step_machine.ts`). The second, looser `Interaction` in
  `src/scene_runtime/protocol/validators.ts` had its `gesture: string` field tightened
  to the canonical closed `Gesture` union so the validator DTO cannot carry an
  out-of-vocabulary gesture. `Gesture` itself stays the closed string-literal union
  (the canonical payload-free discriminated form); giving it object payloads is
  deferred to the affordance-registry work. Validator dispatch keeps its `never`
  exhaustiveness. `./check_codebase.sh` stays green.
- M2 "Gesture-guard truth (temporary)": a bare pointer click can no longer silently satisfy an
  `adjust` or `drag` interaction. `src/protocol_host.tsx` now promotes a bare click ONLY to
  `select` (the one gesture that legitimately reuses the visible-click affordance); `adjust`,
  `drag`, and `type` are no longer relabeled from a bare click, so the raw `"click"` gesture
  reaches the step machine and is rejected instead of falsely completing the step. A matching
  TEMPORARY guard in `src/scene_runtime/protocol/step_machine.ts` `handle_click` loudly rejects an
  active `adjust`/`drag` interaction reached by a bare `"click"`. Both are gesture-data-driven, not
  per-protocol, and are marked TEMPORARY: M13's load-time gesture-affordance invariant replaces and
  deletes them once real `adjust`/`drag` affordances exist (M12). `select` and `click` are
  unaffected; the M1 adjust unit test (which drives an `adjust` gesture directly) stays green.
- `handle_modal_close` and `handle_timer_elapsed` in `step_machine.ts` now emit a `no_active_step`
  `interaction_rejected` in the no-active-step condition instead of returning silently, matching
  `handle_click`/`handle_type_commit`, so a dropped modal-close or timer-elapsed event is observable
  to emitter subscribers (`window.gameState`) rather than vanishing.
- `docs/COLOR_CONTRAST_ACCESSIBILITY.md` reduced to the generic WCAG contrast method; the
  previously bundled concept-map palette tables were re-homed to `concept-map-maker`'s new
  `docs/PALETTE_CONTRAST_AUDIT.md`.
- Walker diagnosability: the walker now registers a `pageerror` listener
  (`tests/playwright/e2e/walker_helpers.mjs`) so an uncaught page exception thrown during
  next-target resolution (for example `AmbiguousTargetError` from a twice-placed object) is
  surfaced as the real exception instead of a bare `waitForFunction` timeout.
- `microscope_basic`, `hemocytometer_view`, and
  `passage_hood_detachment_microscope_view` now honestly stack two rows
  (rear shelf and bench) instead of one fused band, so the uniform object
  rescale engages and objects render somewhat smaller than the prior,
  buggy, fused-band render. Aspect is preserved and no artwork is cropped;
  all render-integrity gates pass.

### Fixes and Maintenance

- Converted SVG XML parsing from stdlib `xml.etree` to a hardened lxml
  parser (`resolve_entities=False`, `no_network=True`) in
  `pipeline/gen_object_library.py`, `pipeline/gen_svg_manifest.py`,
  `validation/svg/asset_audit.py`, and `tools/svg_validate.py` -- byte-identical
  output, closes the XXE/entity-expansion threat class without `# nosec`
  (owner preference: lxml over `xml.etree`).
- Marked md5 filename-stem hashes `usedforsecurity=False` in
  `tests/e2e/e2e_svg_gradient_recheck.py` and
  `tests/e2e/e2e_svg_visual_regression.py` (non-security use; digest
  unchanged).
- Cleared the last three bandit findings at source (non-security use, digest
  and path unchanged): `usedforsecurity=False` on the MD5 content-identity
  hash in `tools/svg_identity_sweep.py` and the SHA1 path-derived ID in
  `tools/svg_picker/build_candidate_manifest.py`; replaced three hardcoded
  `Path('/tmp')` temp targets with `Path(tempfile.gettempdir())` in
  `validation/scene_design/suggest.py` (B108). Relocated the bandit gate from
  the custom `tests/e2e/e2e_bandit_security.py` to the vendored
  `tests/test_bandit_security.py`, so it now runs in the fast `pytest tests/`
  lane (147 -> 148 files scanned, all pass).
- `super_all_tests.sh` runs TypeScript-importing `tests/e2e/*.mjs` under
  `node --import tsx` (per-file selection); fixed the `../src` ->
  `../../src` import path in `tests/e2e/e2e_generalization_preflight.mjs`.
  The three TS-importing e2e (preflight, layout_parity_16x9,
  layout_diagnostics_baseline) now run green.
- Fixed `tools/svg_picker/apply_decisions.py` (and its README) to call the
  current `tools/normalize_svg_v3.py` CLI (`-i <file> --in-place`) instead
  of the deleted `normalize_svg_v2.py`.
- Removed dead `normalize_svg_v2` doc references in
  `docs/CODE_ARCHITECTURE.md` and `docs/FILE_STRUCTURE.md`.
- Inlined the SVG input in
  `tests/test_validation_clarity.py::test_check_normalization_accepts_real_normalized_svg`
  (was reading a real asset file; now uses an inline minimal SVG per the
  PYTEST_STYLE inline-inputs rule).
- `tests/e2e/e2e_svg_visual_regression.py` render loop now uses
  `page.setContent(...)` plus an image-decode wait instead of a temp-file
  `goto(file://...)` with `networkidle` and a fixed 80ms sleep, and the
  prescreen pass keeps and reuses each passing file's normalized output
  instead of normalizing it a second time; measured well under 0.15s/render
  (was ~0.6s/render), a large speedup on the ~300-file default run.
- Re-typed 7 sub-100 mL reagents from bottle to tube and renamed
  `*_bottle` -> `*_tube` (`bme`, `laemmli_4x`, `trypan_blue` -> 15 mL falcon;
  `dmso`, `carboplatin_stock`, `metformin_stock` -> 50 mL;
  `mtt_solution_bottle` -> `mtt_stock_tube`), atomically across object, scene,
  and protocol surfaces; protocol target names moved with authored volumes
  preserved.
- Normalized and declared the previously-orphaned `falcon_50ml` SVG asset
  (added the missing `anchor_liquid_clip` clipPath, mirroring `falcon_15ml`).
- Swept old-name references in `tests/` and `tools/`; excluded `generated/**`
  from ESLint in `eslint.config.local.js` (machine-emitted build output,
  mirroring the `dist/**` ignore).
- Base-scene test sets and their counts now derive from content discovery
  instead of stale hand-maintained lists. Added
  `tests/playwright/_scene_discovery.mjs` (`discoverBaseSceneNames`, reads
  `content/base_scenes/*.yaml`, the definitional base-scene directory; the
  generated `SCENES` map mixes base + protocol + smoke scenes so it is not a
  clean base-only authority). `tests/playwright/test_viewport_sweep.mjs` and
  `tests/playwright/test_generalization_render.mjs` now build `SCENES_TO_TEST` /
  `SCENES_TO_RENDER` from the helper, and their pass gates and report counts are
  derived (`SCENES_TO_TEST.length * VIEWPORTS.length` replaces the hardcoded
  `18`; per-scene assertion totals replace the hardcoded `11`/`6`). The prior
  hand lists already missed 4 of the 9 real base scenes
  (`electrophoresis_bench`, `heat_block_bench`, `imaging_bench`,
  `microscope_basic`).
- `test_generalization_render.mjs` now exits non-zero honestly: the process
  exit code reflects the per-scene assertion outcomes instead of always exiting
  0. `main()` returns 0 only when every discovered base scene reaches a full
  assertion pass; any assertion failure, render FAIL, or ERROR returns 1, read
  by a single top-level `process.exit`. The final summary now names each
  scene's failing assertions and prints a `RESULT: PASS/FAIL` line. Diagnosed
  and fixed the previously fake-green assertions B and C, which were BROKEN
  ASSERTIONS (false negatives), not real defects: both only inspected inline
  `<svg>` and null-failed every img-mode asset. The renderer
  (`src/scene_runtime/renderer/scene_item.tsx:273-308`) has two valid render
  modes -- inline dom-svg and `<img data-svg-render-mode="img">` for static
  assets. B now passes when a placement rendered a real asset in either mode
  (inline `<svg>` with content OR a loaded `<img>`) and has no
  `data-svg-load-error` fallback; C now checks the real distortion switch per
  mode (inline svg `preserveAspectRatio !== "none"`, img
  `object-fit` contain/scale-down) instead of comparing the `<svg>` element box
  to its viewBox, a measure that wrongly flagged plain letterboxing (e.g.
  `electrophoresis_bench` tank: landscape 114x99 asset in a portrait placement
  box, art preserved via default `xMidYMid meet`). After the fix, 8 of 9 base
  scenes reach 11/11.
- The Phase 2-3 `.spec.ts` conversion surfaced and fixed real test rot the
  library-model scripts had been carrying: `test_protocol_host` was
  permanently SKIP (bare `npx esbuild` cannot transform Solid JSX; the
  converted spec builds through the esbuild JS API with
  `esbuild-plugin-solid`, the same plugin path `pipeline/build.mjs` already
  uses); `test_scene_degrade` fake-passed (its throwaway fake server returned
  200 HTML for every SVG fetch, so the degrade path it claimed to exercise
  never actually ran); `test_generalization_render` exited 0 while its own
  assertions failed (see the honest-exit-code fix above); several specs used
  stale `placement_name`-vs-`object_name` selectors left over from earlier
  scene refactors; and one spec navigated to a page `build_github_pages.sh`
  no longer emits. Each is fixed in its `.spec.ts`, not papered over with a
  skip.
- Corrected the `unifiedDiagnostics` field doc-comment in
  `src/scene_runtime/layout/types.ts`, which wrongly claimed the field is "not
  serialized into the precompute". It IS serialized
  (`pipeline/precompute_layout.mjs:118`) and rehydrated
  (`src/scene_runtime/layout/precomputed_result.ts:71`), just unused at
  runtime (report tooling only). Comment-only, no behavior change;
  `./check_codebase.sh` green (504 tests pass).

- Confirmed the per-subpart material overlay (the `data-subpart-overlay` /
  `data-subpart-name` / `data-material-name` DOM stamping) is rendered only for
  objects declaring the material-tint contract (`subpart_geometry` + a
  `material_tint` subpart visual_state). In the current corpus that is
  `well_plate_96` only. `gel_cassette` declares its per-lane `material_name` as a
  `kind: svg` subpart swap whose three cases all emit the SAME asset
  (`mini_protean_gel`), so a lane load produces no per-lane visual change and no
  overlay stamping; `dilution_tube_rack_8` renders per-tube `material_volume` as a
  `kind: composite` field with no `subpart_geometry`, so tubes get no overlay
  either. These are flagged render-coverage gaps (per-subpart material STATE with
  no proven visible per-area rendering), surfaced by the generic verifier as a gap
  rather than fixed here; a per-area gel/tube render is a separate renderer change.

- Seeded a standalone `conical_15ml` tube placement (`rear_center_conical_tube`,
  rear_center) in
  `content/protocols/cell_culture/passage_pellet_reseed/scenes/hood_workspace.yaml`.
  The entry step `transfer_to_conical` writes `ObjectStateChange`/`CursorAttach`
  state onto the `conical_15ml` object while in this scene, but the scene
  previously seeded only `conical_15ml_rack`, causing
  `UnseededSceneOpTargetError: conical_15ml` at protocol load. Mirrors the
  existing standalone tube in the sibling `centrifuge_workspace.yaml`. Fixes the
  load failure for `passage_pellet_reseed` and the two runners that flatten it
  (`cell_culture_full`, `routine_passage`).

- Investigated the reported `passage_hood_detachment` walker regression
  (microscope click timeout in step `inspect_confluence`): traced it to STALE
  gitignored build artifacts (`generated/`, `test-results/layout_metrics/`)
  predating the committed `microscope_basic.yaml` fix, not a source defect. A
  clean rebuild of current committed source produces `main_microscope` with
  zero overlap edges and the walker clicks the microscope successfully; no
  source change was made. A residual non-blocking `hood_return` <->
  hemocytometer-slide cross-zone occlusion in
  `passage_hood_detachment_microscope_view` is routed to the architect as a
  shared `microscope_basic` base-zone decision.

- Removed test magic-counts and a duplicated color literal that could silently
  drift from content. `tests/playwright/test_bench_basic_render.mjs` now derives
  its `Passed: N/M assertions` denominator from the length of the assertion
  results array instead of a hardcoded `11`. `tests/playwright/
  test_per_well_drug_walkthrough.mjs` and `tests/playwright/
  test_subpart_well_plate_render.mjs` both read `CARBOPLATIN_COLOR` live from
  `generated/protocol_materials.ts` (the `plate_drug_treatment_drug_addition`
  registry's `carboplatin.display_color`) instead of hardcoding `#a719db`.
  `tests/test_scene_op_deps.mjs` derives its expected well count from
  `OBJECT_LIBRARY["well_plate_96"].subpart_geometry`'s key count instead of the
  literal `96`, so the assertion no longer just re-reads the array under test.
- Label-overlap handshake (walker M19 failBuild gate): cleared `unresolved_label_overlap` Errors
  on the 8 SDS-PAGE/electrophoresis scenes with one base edit -- placed the `front_right_gel_comb`
  label below the comb in `content/base_scenes/electrophoresis_bench.yaml`, moving it out of the
  bottom-right corner it shared with the `right_tool_area_p10_gel_loading_tip_box` label. Also
  cleared the same Error class in the microscope family: pushed the `left_microtube_rack` and
  `right_hemocytometer_slide` labels below their bench objects in `content/base_scenes/microscope_basic.yaml`
  (they rose into the rear shelf band), and applied the same fix to the re-added
  `right_hemocytometer_slide_clear` in `passage_hood_detachment/scenes/microscope_view.yaml`. All
  fixes reposition labels only; no object shrunk, no target moved. `hemocytometer_view` keeps one
  residual label overlap that stems from its intentional cross-zone density (overlap_count 6); left
  as authored and flagged for a density decision.
- Downscaling sweep: ranked every scene by `final_scale` and lifted the worst floor. In
  `passage_hood_detachment/scenes/hood_workspace.yaml` (T7) collapsed a sparse third tier-row
  (hood surface tier 2 -> tier 1, sharing the flask's wide center row); the scene-wide uniform
  rescale is a vertical stack fit, so removing a tier-row's label overhead raised the whole-scene
  factor 0.461 -> 0.499 and lifted every readable glassware bottle (mean 0.427 -> 0.462), with no
  large-by-design object shrunk. Documented the finding that the single global uniform-rescale
  factor couples one over-tall row to every object (7 of 9 T7 objects are uncrowded yet dragged
  down); that layout-model change (per-zone/per-band scale floors) routes to the architect. See
  `docs/active_plans/audits/downscaling_sweep_and_uniform_rescale_coupling.md`.
- Scene-manager handshake (walker certified register): five placement/dedupe edits that clear the
  walker's remaining `target_missing` and ambiguous-target reds, all inside the scene-content
  boundary. Placed the `hood_surface` return affordance in
  `passage_hood_detachment/scenes/microscope_view.yaml` (freeing rear_right by removing the
  non-target ethanol) and the `plate_reader` doorway in
  `mtt_solubilization_readout/scenes/bench_workspace.yaml` (freeing rear_right by removing the
  non-target vortex); placed a real clickable `kimwipe_pad` in `content/base_scenes/staining_bench.yaml`
  (tier-2 above the waste, resolving the noted collision) so the two destain protocols can complete;
  deduped `media_bottle` in `plate_drug_treatment_media_adjustment/scenes/plate_workspace.yaml`
  (removed inherited `base_rear_right_media`, kept `rear_center_media`) and `laemmli_4x_bottle` in
  `content/base_scenes/sample_prep_bench.yaml` (removed the working-surface duplicate, kept the
  reagent-shelf placement), both clearing an `AmbiguousTargetError`. Each bare target now resolves to
  exactly one placement. Layout gate re-run on all touched scenes: no new overflow or overlap
  (flag set unchanged from the de-shrink baseline). Also removed the never-targeted `sterile_water`
  staging bottle from `drug_dilution_setup/scenes/bench_setup.yaml` (the diluent is `media_bottle`,
  clicked in `dilution_workspace`) to reconcile the diluent narrative.
- M14b "Reconcile the three walker docs": brought `docs/specs/WALKTHROUGH_GUIDE.md`,
  `docs/FILE_STRUCTURE.md`, and `docs/CODE_ARCHITECTURE.md` in line with the landed single-walker
  tree in one patch. WALKTHROUGH_GUIDE.md gained the `run_playwright_tests.sh` front-door run path
  (build-as-needed browser sweep, kept separate from the fast `check_codebase.sh` gate), dropped
  every stale `M4-D` planning token, corrected the `--list-protocols` glob to the recursive
  `content/protocols/**/protocol.yaml` (clustered layout via `rglob`), and updated the gesture
  coverage to current reality (`click`/`select`/`type`/`adjust` supported through visible
  affordances; `drag` wired and unit-tested but sweep-classified `unsupported_gesture` only because
  no content protocol authors one yet). FILE_STRUCTURE.md replaced the deleted-per-M14a
  `tests/playwright/walker/` "shared Playwright walker engine" line with the single canonical
  `tests/playwright/e2e/` walker (`protocol_walkthrough_yaml.mjs`, `walk_all_protocols.mjs`,
  `walker_helpers.mjs`), added the new protocol modules (`target_adapter.ts`, `gesture_registry.ts`,
  `gesture_affordance_check.ts`, `target_existence_check.ts`, `flatten_sequence_runner.ts`,
  `authored_value_check.ts`), the `set_point_editor.tsx` adjust affordance, and root scripts
  `run_all_checks.sh` / `run_playwright_tests.sh`. CODE_ARCHITECTURE.md documented the same six
  protocol modules, retired the stale "Known gaps" (walker cannot complete a protocol,
  sequence_runners not runnable, `tests/playwright/walker/` supersession question -- all resolved by
  M4/M5/M16-A/M14a), and added the umbrella and sweep gates. Docs-only; no code, test, or protocol
  YAML changed.

- Scene layout de-shrink pass: rebalanced 22 crowded curriculum scenes (four base-scene
  families -- `electrophoresis_bench`, `hood_basic`, `staining_bench`, `bench_basic` -- plus
  `imaging_bench`) so the solver no longer shrinks whole scenes toward the packing floor.
  Base-scene `zones`/`placements` were spread across added front bands and widened rear zones;
  per-child `add_placements` were redistributed and inherited non-target clutter
  (`center_water_bath`, `center_centrifuge`, `center_well_plate_96`, spare pipettes) removed with
  `remove_placements` (target-scanned: an object is removed only when the mounting `protocol.yaml`
  never clicks it in that scene). Cleared all three engine `unresolved_overlap` errors
  (`seeding_workspace`, `hood_workspace`, `imaging_bench` now report `overlap_count == 0`) and the
  one `post_rescale_overflow` scene (`passage_hood_detachment_hood_workspace`). Fixed four
  contract item-4 missing-target gaps where a protocol clicked an object its scene never placed:
  added `microscope`+`incubator` (`passage_hood_detachment/hood_workspace`),
  `biohazard_decant`+`media_bottle` (`passage_pellet_reseed/centrifuge_workspace`), and kept the
  inherited `media_bottle` in `drug_dilution_setup/dilution_workspace` (the diluent clicked every
  step, previously removed while only an untargeted `sterile_water_bottle` was staged). Resized
  the incubator asset (`display_width_cm` 55 -> 40) so it fits `rear_right` without overflow.
  Corpus gate: every rebalanced scene holds `post_rescale_overflow == false`, `off_canvas == 0`,
  object `overlap_count == 0`, and `mean final_scale >= 0.50`, except the documented
  `passage_hood_detachment_hood_workspace` per-scene floor (0.4272, structurally unreachable with
  its three large required objects; flagged for a visual read). The three `bench_basic` healthy
  children and the four intentional dense-by-design scenes (`microscope_basic`,
  `passage_hood_detachment_microscope_view`, `hemocytometer_view`, `adversarial_overflow_smoke`)
  are unchanged. All edits are `content/**` YAML only; no engine, pipeline, or runtime source
  touched.

- Implemented sequence-runner mini-protocol chaining (M16-A), fixing all 5
  `protocol_type: sequence_runner` protocols (`cell_culture_full`,
  `routine_passage`, `sdspage_full`, `sdspage_load_samples_batch`,
  `sdspage_prepare_sample_mix_batch`) that previously threw
  `Unknown step_name in protocol` at page load because
  `protocol_host.tsx` resolved the runner config once and
  `create_step_machine` was handed an empty steps list. Added
  `src/scene_runtime/protocol/flatten_sequence_runner.ts`, a pure function that
  expands a runner into one flat `mini_protocol`-shaped config: each
  constituent's steps are namespaced (`mp{i}__<name>`) so a mini listed multiple
  times keeps distinct ids, each constituent's terminal step is rechained to the
  next constituent's entry step, and each constituent's entry step carries its
  resolved entry scene. `mount()` now flattens every config unconditionally
  (non-runners pass through unchanged), so the step machine, reducer, walker
  surface, and HUD run the runner as one steps list with no `protocol_name`
  branch. `step_machine.ts` gained a data-driven step-entry scene render:
  `enter_step` transitions to `step.scene` (the documented
  "initial/transition scene for this step") before emitting `step_started` when
  it differs from the tracked current scene, so each mini boundary renders the
  correct scene and rebinds the target adapter before the student interacts; a
  new `initial_scene` option seeds the tracker so no redundant re-render fires
  for normal protocols. Walker evidence: `sdspage_load_samples_batch` now walks
  all 9 flattened steps to completion (three chained instances of
  `sdspage_load_sample_single_lane`), and `sdspage_full` chains through its whole
  first constituent into `mp1` before stalling on a separate constituent bug.
  Added `tests/test_flatten_sequence_runner.mjs` and step-entry-scene cases in
  `tests/test_step_machine.mjs`. The remaining 4 runners now load and chain
  correctly but cannot yet walk to completion because a constituent mini
  (`passage_hood_detachment` `hood_surface`;
  `sdspage_prepare_sample_mix_single_lane` `adjust`) still fails standalone under
  separate M16 waves.
- Fixed the repo-wide `eslint` gate: background-agent git worktree checkouts under
  `.claude/worktrees/agent-*` were matched by the canonical `**/*.{ts,tsx,mts,cts,js,mjs,cjs}`
  glob, and each worktree's own `tsconfig.json` caused typescript-eslint to fail every one of
  its files with "No tsconfigRootDir was set, and multiple candidate TSConfigRootDirs are
  present", flooding `./check_codebase.sh` step 3 with hundreds of unrelated errors. Added a
  `.claude/**` ignore entry to consumer-owned `eslint.config.local.js` (the propagated
  `eslint.config.js` is not edited directly), matching the existing `OTHER_REPOS/**` sibling-repo
  ignore convention.
- Updated `tests/test_affordance.mjs` fixtures for the M6 capability gate: the
  `make_pipeline_result` helper now stamps `capabilities: ["clickable"]` on its fixture items
  (`enumerate_candidate_targets` now reads `item.capabilities`), and added two dedicated unit
  tests asserting a `decoration_only` item and a `capabilities: []` placeholder are excluded from
  the candidate set.
- Made the two state-touching validators read real scene state (M1 validator truth). The
  `target_with_value` click path in `step_machine.ts` sourced its "observed" value map from the
  authored validator parameters, so the expected value was compared against itself and the check
  was always `ok`; it now reads the live scene-store state through a new read-only
  `read_object_state` seam on `StepMachineOptions` (wired over `scene_store` in
  `protocol_host.tsx`), so a click whose target state does not match the authored value fails with
  `wrong_value`.
- Fixed `final_state_matches` so it can actually pass or fail at runtime instead of retrying
  forever. `to_validator_step` now projects the step-validator parameters from the authored
  `target` + `contains` fields (it previously read `step_validator.value`, which is undefined for
  this preset and starved the validator of parameters), and `emit_step_validator_outcome` builds
  and passes the real observed object-state snapshot. The `validators.ts` `final_state_matches`
  dispatch no longer masks a missing snapshot with a silent `?? {}` default; a missing snapshot now
  throws loudly. Removed the now-stale "runtime projection is broken" acknowledgement comment in
  `authored_value_check.ts`.

- M16-C-safe "Subpart-click retarget, 3 auto-safe protocols": applied the ratified
  `docs/archive/decisions/subpart_click_pattern.md` recipe to the three protocols the
  architect pedagogy-cleared as auto-apply-safe (whole-object action; subpart is the recorded
  effect, not the graded skill). In each, changed the failing interaction `target` from
  `<base>.<subpart>` to `<base>` (the clickable scene object); left the response
  `ObjectStateChange` target and any `final_state_matches` field reference on the subpart
  unchanged, matching the passing `cell_seeding_plate_setup` shape. `mtt_plate_reaction`:
  `add_mtt_to_wells` interaction `well_plate_96.all_wells` -> `well_plate_96` (one occurrence).
  `mtt_solubilization_readout`: `add_dmso_to_wells`, `trituration_to_dissolve`, and
  `read_absorbance` interactions `well_plate_96.all_wells` -> `well_plate_96` (three
  occurrences). `sdspage_load_sample_single_lane`: `dispense_lane` interaction
  `gel_cassette.lane_1` -> `gel_cassette` (one occurrence). Walked all three post-fix:
  `mtt_plate_reaction` and `sdspage_load_sample_single_lane` PASS all steps through visible UI.
  `mtt_solubilization_readout` clears its own subpart-click FAIL (`add_dmso_to_wells` and
  `trituration_to_dissolve` now pass) but `read_absorbance` still fails on an unrelated,
  pre-existing gap: `scenes/bench_workspace.yaml` has no `plate_reader` placement, so the
  step's own `target: plate_reader` entry interaction (untouched by this fix) has no DOM node to
  click from that scene. Left `sdspage_load_protein_ladder` and
  `plate_drug_treatment_drug_addition` untouched per the decision's pedagogy-call gate (subpart
  discrimination is explicit taught skill in both).

- M16-B "waitForExports honest-budget one-liner": fixed `waitForExports` in
  `tests/playwright/e2e/walker_helpers.mjs` passing `{ timeout: timeoutMs }` into the `arg`
  position of `page.waitForFunction(pageFunction, arg, options)` instead of `options`, since
  the zero-parameter predicate left no slot for it to land correctly. The intended 8000ms
  budget was silently replaced by Playwright's 30000ms default, so a genuinely dead export
  took 30s to surface instead of 8s. Added the missing `undefined` `arg` argument so
  `{ timeout: timeoutMs }` lands in `options`. Verified with a scratch page that never defines
  the exports: the wait now times out at 8007ms (was previously falling through to 30000ms).
- Root-caused the `microscope_basic` / `hemocytometer_view` /
  `passage_hood_detachment_microscope_view` 100% item-overlap fail (O6) to a
  transitive band-merge in `groupVerticalBands`
  (`src/scene_runtime/layout/reflow_zones.ts`): the function used
  vertical-range overlap as the band-membership test, so the tall
  `instrument_area` zone (authored `[18, 92]`) bridged the vertically-disjoint
  rear-shelf row `[5, 34]` and bench row `[40, 92]`, fusing all five zones of
  the scene into one computed band. `rear_tip_box` and `left_microtube_rack`
  (same `depth_tier`, same x-column) then landed at an identical position --
  a 100% coincident box -- while the engine's own `overlap_count` read 0,
  because containment was checked per-band and no cross-zone AABB check
  existed. Fixed with a new `crossesDisjointRowGap` predicate that classifies
  a zone bridging two vertically-disjoint row cohorts as a spanning overlay,
  placed at its own authored bounds outside the contiguous row stack, while
  genuine same-horizontal-row zones (side-by-side rows and the documented
  small partial-overlap pair) still merge unchanged. The predicate stays
  threshold-free apart from `BAND_EPS = 1e-9`.
- Un-blinded the engine's overlap diagnostic: new
  `src/scene_runtime/layout/diagnostics/item_overlap.ts` compares final
  placed object AABBs across all zones and emits an `item_overlap`
  diagnostic (added to `DIAGNOSTIC_KINDS`); `structural_guards.ts` now
  imports the same shared AABB predicate as its single source of truth, so a
  real 100% render overlap can no longer read `overlap_count = 0`.

### Removals and Deprecations

- Retired the stale `tests/e2e/e2e_facade_smoke.py` (it smoke-loaded four
  pre-migration facade modules that no longer exist; module loading and
  exports are already covered by `tsc`, the node unit tests, and the build --
  redundant). Removed the dead `normalize_svg_v2` orphans:
  `tests/test_normalize_svg_geometry.py` (broke pytest collection),
  `tests/data/scenes_freeze_baseline.json` (unreferenced), and
  `tests/e2e/e2e_normalize_svg_parity.py` (dead v2 parity harness). Human ran
  the `git rm`.
- M14a "Delete stale walker tree (staleness check)": confirmed `tests/playwright/walker/`
  (`audit_all.mjs`, `click_resolver.js`, `engine.mjs`, `index.js`, `run.mjs`, `screenshot.js`,
  `tsconfig.json`) is dead. The tree targets an extinct runtime contract
  (`data-testid` selectors, a `__RUNTIME_PROTOCOL_CONFIG` global) superseded by the live walker
  (`tests/playwright/e2e/protocol_walkthrough_yaml.mjs` + `walker_helpers.mjs`). A repo-wide grep
  found no external reference to any file in the folder (only self-referencing usage-comment
  docstrings and agent worktree copies under `.claude/worktrees/`), and `grep -rn
  "__RUNTIME_\|data-testid" src/` returned empty, confirming no live runtime still emits the old
  contract. Full evidence and the exact `git rm` file list are recorded in
  `docs/active_plans/audits/stale_walker_staleness_check.md`. No files were deleted by this
  check; a human runs the listed `git rm` to complete the removal.

- M13 "Gesture load-time invariant": deleted the M2 TEMPORARY gesture-collapse guard from
  `src/scene_runtime/protocol/step_machine.ts` (the explanatory comment block plus the
  `if ((interaction.gesture === "adjust" || interaction.gesture === "drag") && gesture ===
  "click")` runtime reject). The generic wrong_target check immediately below
  (`interaction.gesture !== gesture`) already rejects that same bare-click-on-adjust/drag
  mismatch, so removing the M2 block does not regress runtime behavior; the existing
  "M2 temporary gesture-collapse guard" unit tests still pass through the generic check. The
  real gain moves to load time: the new `validate_gesture_affordances` invariant now rejects an
  unaffordanced gesture before any browser session.
- Removed `set -u` from `source_me.sh` and `run_validate.sh`: unset-variable strictness tripped
  on optional environment fallbacks; `run_validate.sh` retains `set -e`.
- `tests/playwright/test_viewport_sweep.mjs` was already removed from the
  repo (confirmed absent from the working tree, from `HEAD`, and from
  `git ls-files`; it was deleted in the same commit that landed the
  content-derived base-scene discovery helper, see the "Base-scene test
  sets" entry above). It was dead (`rewriteMainTsForScene` read the
  removed `src/main.ts`, ENOENT on every scene) and redundant with
  `tests/playwright/test_generalization_render.mjs` (covers all 9 base
  scenes) and `tests/playwright/test_letterbox_16x9.mjs` (covers
  viewport-aspect/letterbox behavior); the layout engine is aspect-only, so
  a multi-viewport-size sweep tested a dimension the product already
  collapses. No further removal action is needed; a repo-wide grep found no
  live reference in `package.json`, `run_playwright_tests.sh`, or any
  `.sh`/`.mjs`/`.json` file, only historical mentions in `docs/CHANGELOG.md`,
  its dated archive, and `docs/archive/`.
- Retired the `microscope_basic` entry from `EXPECTED_FAIL_SCENES`
  (`tests/playwright/test_generalization_render.spec.ts`) now that the
  underlying overlap is fixed. Added
  `tests/playwright/test_rear_tip_box_rack_identity.spec.ts` proving
  `rear_tip_box` and `left_microtube_rack` are independently visible and
  clickable by their own placement identity.

### Decisions and Failures

- Recorded: `xml.etree` -> lxml hardened parser chosen over `# nosec` or
  `defusedxml` (durable fix, no new dependency; lxml is already a declared
  requirement). A fragile-test audit found the pytest suite otherwise near
  the PYTEST_STYLE ideal (inline inputs, no snapshot counts) -- only the
  normalize_svg_v2 orphans needed removal.
- Playwright runner adoption is intentional: it reverses an earlier
  library-model resolution per owner decision, aligning this repo with sibling
  repos under `~/nsh/TYPESCRIPT/` (concept-map-maker is the house template).
  Phase 1 ships config + smoke spec TOGETHER to avoid a vacuous green: a config
  with zero specs makes `npx playwright test` exit 0 on an empty run. The spec
  was proven non-vacuous by temporarily breaking its heading assertion
  (confirmed RED, `1 failed`, exit 1) then restoring it (`1 passed`).
- Two deviations from the concept-map-maker template, both driven by real
  needs: (1) the `webServer` command builds then serves (the template serves a
  prebuilt dist only), so a bare `npx playwright test` is self-sufficient and
  matches the PLAYWRIGHT_TEST_STYLE build-first-then-serve load model; (2)
  `baseURL` and the server bind to `127.0.0.1` rather than `localhost` (the
  template uses `localhost`), because on this host `localhost` resolves to IPv6
  `::1` while python's `http.server` listens on IPv4, so chromium refused the
  connection. The repo's own library tests already standardized on `127.0.0.1`.
- Random-port persistence was required, not optional: the config is evaluated
  in both the main runner process and each worker process, so a bare
  `Math.random()` picks a different port per process and the browser targets a
  dead port (observed as `ERR_CONNECTION_REFUSED` after the readiness probe
  passed). Persisting the port into `process.env.PORT` on first evaluation makes
  workers inherit the main process's port.
- The 23 remaining library-model `.mjs` tests and the walker sweep
  (`walk_all_protocols.mjs`, `protocol_walkthrough_yaml.mjs`) are staged for a
  later batch phase; `test_protocol_selector.mjs` (the smoke source) stays in
  place this phase and must not be double-converted.
- The completed runner-sweep spec matches the library sweep verdict-for-verdict
  against the same `dist/` build (29 pass / 2 fail of 31), so the conversion
  changed execution model, not acceptance outcome. The remaining reds are
  routed honestly rather than hidden by the migration: the `microscope_basic`
  base-scene overlap (register item O6, routed to scene-manager);
  the `tube_A` dotted-subpart click in `per_well_drug` and
  `plate_drug_treatment_drug_addition` (register item OP1, pedagogy-held,
  needs an architect ruling); and the `cell_culture_full` mp5 material-quadrant
  gap (a known scene-manager item already tracked in memory). Separately,
  `test_decoration_noninteractive.spec.ts` is marked `test.fixme` because its
  source dev-smoke fixture content was removed elsewhere in the repo; it is a
  retire candidate, not a migration regression.
- Making `test_generalization_render.mjs` honest surfaced one real layout defect
  that the fake-green exit had hidden: `microscope_basic` fails F (no item
  overlap) and I (no label-label overlap) with genuine, substantial overlaps
  (`left_microtube_rack` over `rear_slide_cartridge` ~171x111px, over
  `rear_tip_box` ~53x130px; `rear_ethanol_bottle` over `right_hemocytometer_slide`
  ~67x181px; and the "Microtube rack (24-slot)" / "Cell counter slide cartridge"
  labels overlap ~72x23px). These are keep-red-correctly failures, routed to the
  scene-manager for microscope_basic layout/overlap; F/I logic was left intact
  (not weakened). The test now exits 1 on the current tree for exactly this real
  defect. Advisory for the same owner: the `electrophoresis_bench` tank is
  letterboxed (landscape asset in a portrait placement box); art aspect is
  preserved (not a contract violation), but the box shape could be sized to the
  asset to reduce whitespace.
- Added `docs/archive/decisions/subpart_and_layout_design_calls.md`, packaging
  three held architect design calls into one brief: (a) discrimination-bearing
  subpart click Direction-B RFC (pedagogy, needs human sign-off, clears register
  row OP1); (b) D2 unfittable-asset WARNING -> failBuild promotion (engine/layout,
  defaulted keep-WARNING); (c) centrifuge crowd=4 per-zone density (scene-manager
  YAML plus architect ruling, defaulted accept-as-is). `pytest
  tests/test_markdown_links.py`: 520 passed.

- The single-subpart, single-lane, and single-tube writes remain unexercised
  end-to-end by the generic verifier: single-well writes live only in
  `plate_drug_treatment_drug_addition`, blocked upstream by a pre-existing
  non-material scene-target bug (`rear_center_carb_stocks.tube_A` missing in DOM,
  outside the walker task boundary); single-lane and single-tube writes render on
  gel/tube objects that carry no material-tint overlay (see the stamping gap
  above). The single-subpart positive + negative comparison logic is pinned
  deterministically by `tests/test_material_area_verify.mjs`. The bespoke
  `test_all_wells_group_write_walkthrough.mjs` was subsumed by the generic path
  and has been removed, eliminating its synthetic-click and hidden-answer
  shortcuts.

- M19b "Commit the durable layout baseline": added `docs/SCENE_LAYOUT_BASELINE.md`, a
  committed, hand-refreshed snapshot of the settled corpus after the M19 failBuild gate
  went live (38 scenes, `countBuildFailures` on non-exempt scenes = 0, health scorecard
  top-10 plus the `severityDiagnostics` Error table). The only Error-level residuals are
  `unresolved_overlap` x2 in the exempt `adversarial_overflow_smoke` fixture and
  `unresolved_label_overlap` x3 in the exempt `hemocytometer_view`; both scenes are named
  in `BUILD_GATE_EXEMPT_SCENES`. Added a pointer note at
  `docs/active_plans/reports/scene_layout_baseline_pointer.md` and a refresh-command
  section in `docs/USAGE.md`. This file is refreshed by hand at each release, not
  auto-regenerated.

- M19 "Honor the failBuild gate + carry diagnostics through production paths":
  the layout never-crop/never-off-canvas gate is now enforced at build time and
  the build-time diagnostics travel into the shipped artifact. `pipeline/
  precompute_layout.mjs` main now calls `countBuildFailures` on each scene's
  `severityDiagnostics`, skipping `isBuildGateExemptScene` scenes, and exits
  nonzero naming the scene, object/placement, and code for every non-exempt scene
  with a `failBuild` diagnostic; `build_github_pages.sh` (`set -euo pipefail`,
  which invokes precompute directly) and the `run_all_checks.sh` umbrella both
  fail when the gate fails. Separately, the `unifiedDiagnostics` report stream is
  serialized alongside `final` into `generated/precomputed_layout.ts` (the
  `PrecomputedSceneLayout` interface gains a `unifiedDiagnostics:
  UnifiedDiagnostic[]` field), and `src/scene_runtime/layout/precomputed_result.ts`
  rehydrates that field into the resolved `PipelineResult` instead of hard-coding
  an empty list, so report tooling reading a resolved result sees the same
  findings the engine produced.
- M19 gate flip followed a verify-first hold. The first corpus scan found 8
  non-exempt scenes tripping `unresolved_label_overlap` (Error, failBuild:true) on
  the shared placements `front_right_gel_comb` and
  `right_tool_area_p10_gel_loading_tip_box` (electrophoresis_bench,
  extraction_workspace, and six sdspage_* workspaces), so the gate was held rather
  than break the build on known-bad scenes; the blocker was recorded as item 5 of
  the scene-manager handshake in
  `docs/archive/audits/walker_click_bug_register.md`. After the scene-manager
  placement edits landed, a fresh reconciliation confirmed all 8 clean and
  `countBuildFailures` on non-exempt scenes is 0 (the only remaining
  `unresolved_label_overlap` is on the exempt `hemocytometer_view`), so the gate
  was flipped. The 3 historical object-overlap scenes (`seeding_workspace`,
  `hood_workspace`, `imaging_bench`) are clean; the only remaining corpus
  `unresolved_overlap` is the exempt `adversarial_overflow_smoke` fixture. Gate
  proven by a scratch broken non-exempt scene (real overflowing layout under a
  non-exempt name): `precompute_layout.mjs` exited 1 naming it, and the clean tree
  exits 0 after the scratch was removed.

- M17 "Layout diagnostics result + preventive below-viewport code": consolidated the
  layout engine's four parallel diagnostic streams and added two closed-vocabulary
  codes. `PipelineResult` (`layout/types.ts`) gains `unifiedDiagnostics`, one flat
  normalized array folding the legacy `diagnostics`, per-pass `passes[].diagnostics`,
  `severityDiagnostics`, and `offCanvasDiagnostics` streams (built by the new
  `diagnostics/unified.ts`); it is the long-term single source of truth report tooling
  reads instead of recomputing. Added the PREVENTIVE never-crop code `art_below_viewport`
  (Error, `failBuild:true`) to the closed `severity_model.ts` vocabulary: the
  report-only `fully_off_canvas` off-canvas classification is now promoted into
  `severityDiagnostics` (`diagnostics/promote.ts` `promoteBelowViewport`). It is a
  regression guard, not a fix -- 0 of 38 real scenes trip it today (the historical
  below-viewport clipping was fixed by the uniform rescale); it fails loud if one ever
  regresses. Added the D2 advisory code `unfittable_asset` (Warning, `failBuild:false`):
  a final item shrunk below the readable floor (`READABLE_FLOOR_SCALE`, tied to
  `MIN_SCALE`) emits a named Warning (`collectUnfittableAssets`); 40 such Warnings fire
  across ~10 dense shrink scenes, making the degradation legible for the scene-manager
  pass WITHOUT failing the build. Added `BUILD_GATE_EXEMPT_SCENES` /
  `isBuildGateExemptScene` naming the intentional-void scenes plus the
  `adversarial_overflow_smoke` dev fixture, for the M19 gate to skip. M17 does NOT wire
  the build gate (M19 owns `countBuildFailures` in `precompute_layout.mjs`);
  `precomputed_result.ts` gets an empty `unifiedDiagnostics: []` default to satisfy the
  type until M19 wires the serialize/rehydrate path. Eleven new unit tests in
  `tests/test_layout_diagnostics.mjs` cover the two codes, the promotion (synthetic
  below-viewport item fires the code), the exempt set, and the unified builder.

- M13 "Gesture load-time invariant": added
  `src/scene_runtime/protocol/gesture_affordance_check.ts`, the PERMANENT load-time
  gesture-affordance invariant that replaces the M2 temporary runtime guard. It exports the
  named author-facing error `UnaffordancedGestureError` and the pass
  `validate_gesture_affordances(config)`, following the `authored_value_check.ts` pattern
  (named error, shared location suffix, single pass entry point). The pass reads
  `GESTURE_REGISTRY` (the single source of registered/wired gestures) and throws at protocol
  load, with full locating fields (protocol, step, interaction index, target, gesture), when any
  authored interaction names a gesture whose registry row is absent or `wired: false`. It fires
  inside `create_step_machine` beside `validate_protocol_presets` and
  `validate_authored_validator_values`, BEFORE the emitter/handlers build and before any browser
  session, so an unaffordanced gesture fails loud once at load instead of trapping a student
  mid-walk. The invariant is data-driven off the registry: it hardcodes no gesture list and
  grows automatically as the registry adds gestures or flips a `wired` flag.

- M12 "Adjust/drag primitives": wired the two M11 registry seams into real visible
  affordances. Added `src/shell/hud/set_point_editor.tsx`, the ONE shared numeric
  set-point editor serving every `adjust` field (`set_volume`, `set_rpm`,
  `set_temperature`, `set_voltage`, timed duration, pH): a stepper (decrement /
  increment) plus a direct numeric input, mounted to `document.body` so it works
  under `?shell=off`, shown only while `active_interaction_gesture === "adjust"`,
  mirroring `type_input.tsx` slot-for-slot (`data-adjust-panel` / `-input` /
  `-target` / `-decrement` / `-increment` / `-commit` / `-reject-message`). Added
  `step_machine.handle_adjust_commit(target, committed_number)` and
  `handle_drag_commit(target, destination_placement)` as the sole advance paths
  for those gestures, each returning an accept/reject boolean like
  `handle_type_commit`. `handle_adjust_commit` coerces the committed number to the
  field's DECLARED type through the same authored-value-directed path
  `handle_type_commit` uses (`build_typed_value_map`), so a float set-point
  (voltage 3.5) compares as a float and an int (`set_volume` 1000) as an int; a
  hard-coded numeric type would truncate a float. `handle_drag_commit` derives the
  accepted destination from EXISTING authored slots (the `zone` of the first
  `LayoutMove` in the interaction response) with no new YAML field. Added the
  read-only `activeAdjustValue` and `activeDragDestination` projections to
  `walker_debug.ts` gameState (derived the same way as `activeTypeValue`), and the
  `adjustCommitAndWaitProgress` / `dragToAndWaitProgress` visible-UI walker drivers
  to `walker_helpers.mjs`. Ten new step-machine unit tests cover adjust
  accept/reject, float preservation vs truncation, and drag source/destination
  validation (453 Node tests, 451 pass, 2 skipped).

- M11 "Affordance registry": added `src/scene_runtime/protocol/gesture_registry.ts`, one
  registry keyed by the closed `Gesture` union (`GESTURE_REGISTRY`) that co-locates the five
  frozen affordance-contract slots per gesture (render shape, stable `data-*` selectors, value
  extraction, single step-machine dispatch entry, walker-driver reference), transcribed from
  `docs/archive/decisions/affordance_contract.md`. The module also owns
  `scene_click_to_command` (the single home of the click-vs-select promotion that used to be an
  inline ternary in `protocol_host.tsx`) and `dispatch_gesture`, the ONE gesture-routing point,
  whose `switch` mirrors `scene_operations.ts`'s exhaustive `never` default so a new gesture is a
  compile error rather than a runtime fallthrough. `click`/`select`/`type` route to live
  step-machine methods (`handle_click`, `handle_type_commit`); `adjust`/`drag` carry the frozen
  contract shape with `wired: false` and their `dispatch_gesture` arm is the single obvious seam
  M12 plugs `handle_adjust_commit` / `handle_drag_commit` into. No affordance emits an
  adjust/drag command at this milestone, so an active adjust/drag interaction reached by a bare
  click still falls to the step machine's M2 temporary guard, unchanged. The M2 guard
  (`step_machine.ts`) is preserved (M13 removes it).
- M8 "Target adapter": added `src/scene_runtime/protocol/target_adapter.ts`, the single
  protocol-target-to-DOM identity adapter, and `tests/test_target_adapter.mjs` (15 unit tests).
  `build_target_adapter(bindings)` builds a scene-scoped adapter from a scene's
  `{object_name, placement_name}` placements and exposes `resolve_to_placement` (semantic/object
  target -> the unique DOM `placement_name`) and `resolve_to_object` (semantic/placement target
  -> the `object_name` state-store key), both preserving a `.subpart` suffix. It FAILS LOUD with
  `AmbiguousTargetError` when an authored target names a non-unique `object_name` (an object
  placed more than once) with no disambiguating `placement_name`; a specific `placement_name` of
  that same twice-placed object still resolves uniquely (the disambiguation path). The module
  also owns the DOM click-key name (`TARGET_DOM_ATTR` / `TARGET_DOM_SELECTOR`), the read-back
  helper `placement_name_from_element`, and `IDENTITY_TARGET_ADAPTER` (the adapter-less default).
  `tests/test_target_adapter.mjs` constructs the twice-placed case in-memory (no content fixture)
  as the disambiguation probe.
- Added `tests/playwright/e2e/walk_all_protocols.mjs`, an all-protocols walker sweep runner
  (also `npm run walk:all`) that enumerates every `content/protocols/**/protocol.yaml` id and
  spawns the existing single-protocol walker per id, classifying each run PASS /
  `unsupported_gesture` / FAIL / error and writing a worst-first summary to
  `test-results/walker/sweep_summary.json`. First sweep against `dist/`: 6 PASS, 15
  `unsupported_gesture` (all `adjust` gesture, expected pending affordance work), 10 FAIL
  (mostly `page.waitForFunction` timeouts on sequence-runner protocols and missing scene item
  ids such as `hood_surface`, `kimwipe_pad`, `waste_container`).
- Added `tests/content/dev_smoke/decoration_noninteractive_check/`, a dev_smoke fixture that
  places a `decoration_only` object (`micropipette_tip_box`) beside a `clickable` object
  (`ethanol_bottle`). Added `tests/playwright/test_decoration_noninteractive.mjs`, browser
  evidence (production `mountScene` path, no internal API calls) proving the decoration object
  renders with no `data-item-id` and a real click on it produces no observable progress, while
  the clickable object beside it does.
- M16-D "Load-time target-existence invariant": added
  `src/scene_runtime/protocol/target_existence_check.ts`, the load-time pass that verifies every
  authored interaction target resolves to a placed scene object before any browser session, so a
  scene-placement gap (missing `hood_surface`, `plate_reader`, `kimwipe_pad`) fails loud at
  protocol load with a named author-facing error instead of trapping a student mid-walk.
- Added `run_all_checks.sh`, the umbrella gate that runs the repo's check suite in one entry
  point (alongside the existing `run_validate.sh`).
- Subpart-click fix pattern (architect decision): adopted direction A as the MECHANISM for the
  dominant M16 walker-FAIL cluster (5 protocols authoring `gesture: click` on a `.<subpart>`
  target). A protocol interaction always clicks the BASE placement (plate/rack/gel scene object);
  the subpart is named only inside the response `ObjectStateChange` or a `final_state_matches`
  reference. Grounded in PRIMARY_CONTRACT item 3 (subparts are interior geometry, not clickable
  scene objects), the well-plate-as-material model, the `pointer-events: none` subpart-overlay
  contract, and the 12 passing protocols that already click base placements. Added a pedagogy
  gate: the rewrite changes what the student does and can drop subpart specificity, so the
  5-file fanout is per-protocol pedagogy-owner-reviewed. `mtt_plate_reaction` and
  `mtt_solubilization_readout` (whole-plate uniform) are auto-apply-safe;
  `sdspage_load_protein_ladder` ("verify correct lane targeting") and
  `plate_drug_treatment_drug_addition` (well-by-row dose targeting) are held for a pedagogy call;
  `sdspage_load_sample_single_lane` is borderline. The `select` gesture was evaluated and does
  not recover subpart specificity (it only chooses among present base placements); genuine
  subpart-picking is a future direction-B RFC under the PRIMARY_DESIGN new-primitive evidence
  bar. Recorded in
  [subpart_click_pattern.md](archive/decisions/subpart_click_pattern.md).
- Release closeout (velvet-napping-tower plan, Release 1 + Release 2 + follow-on fixes):
  `FinalDiffReview` found the full diff merge-ready, and the full walker corpus is
  clean-except-owned (`FullSweep` 26/31 PASS, the 5 remaining reds all triaged and
  owned). This closes the release. Release 1 landed the trustworthy-walker chain end
  to end: `target_with_value` and `final_state_matches` now read the real scene store
  instead of trusting authored intent, the M2 temporary adjust/drag-collapse runtime
  guard was replaced by the permanent `validate_gesture_affordances` load-time
  invariant, actionability is capability-gated, target resolution is unified on one
  adapter keyed by placement-name identity, gesture and validator dispatch moved to
  discriminated unions, the affordance contract and `GESTURE_REGISTRY` are frozen
  and intentionally never-exhaustive, `adjust`/`drag` are wired runtime primitives,
  four load-time invariants now fail loud at protocol load
  (`UnknownAuthoredTargetError`, `AmbiguousAuthoredTargetError`,
  `UnseededSceneOpTargetError`, `UnknownAuthoredSubpartTargetError` in
  `target_existence_check.ts`, plus `pedagogy_consistency_check.ts`), codegen closure
  delegates to the one canonical validator, `run_all_checks.sh` plus a rewired
  `run_playwright_tests.sh` and a root `ci.yml` seed give the repo one check entry
  point, the extinct `tests/playwright/walker/` tree was confirmed dead and removed
  from the doc set, and the certified walker sweep fixed the click-bug cluster it
  found. Release 2 landed the layout side: `PipelineResult` gained the unified
  `unifiedDiagnostics` stream plus the preventive `art_below_viewport` /
  `unfittable_asset` codes, the `failBuild` gate now runs live in
  `precompute_layout.mjs` (`countBuildFailures` / `isBuildGateExemptScene`, nonzero
  exit on a real non-exempt failure), `tools/layout_metrics.mjs` (D6) gives the
  scorecard a durable CLI, and `docs/SCENE_LAYOUT_BASELINE.md` commits the settled
  corpus snapshot. Release 2 also landed the pedagogy side: `pipeline/gen_flow_view.py`
  gives authors a flow-view audit as the first authoring-guide step, the gesture
  rubric closes the `adjust` vs `click` ambiguity, `drug_dilution_setup` was
  right-sized to Direction-A base-retarget, and a pedagogy-drift check plus prose and
  prompt fixes tightened step wording. Follow-on fixes closed the remaining gaps:
  `trypan_blue_counting`'s viability gate moved from an exact-match 90 to 92.5 to match
  the authored data, `mtt_solubilization_readout` fixed same-step `SceneChange`
  active-target re-resolution (the scene-change-completion family), the orphan
  `validate.py` bugs in `validation/yaml_schema/` converged on one resolver of record
  for placement-name targets and `add_placements` (3 errors -> 0), and the `all_wells`
  material cascade fan-out was wired end to end with a generated
  `subpart_groups`/`subparts` vocabulary, moving it from ratified-but-unimplemented to
  live. Two decisions carry forward as owned, not release-blocking: subpart-click
  discrimination stays held at Direction-A base-retarget, with genuine subpart-picking
  parked as a Direction-B RFC owned by the architect (`all_wells` is explicitly
  excluded from that RFC as a bulk write/group fan-out, not a subpart pick); and the
  M16-D load-time subpart-suffix guard landed at 0/30 blast radius against the current
  corpus. The 5 known owned reds: O1 (`conical_15ml` seeding) and O4 (hood
  pointer-overlap) route to the scene-manager plan; OP1 (subpart-click) routes to the
  architect's Direction-B RFC.
- `microscope_basic` base scene fails generalization assertions F (item overlap) and
  I (label-label overlap), 7/11, surfaced by the content-derived base-scene discovery
  widening (see the "Base-scene test sets" entry above). Routed to the scene-manager
  plan as a new owned row (O6 in
  [walker_click_bug_register.md](archive/audits/walker_click_bug_register.md)),
  tagged as possibly the same shared-base-zone / instrument-band overlap family as O4
  (hood pointer-overlap: `right_hemocytometer_slide_clear` over
  `rear_right_hood_return`), pending scene-manager confirmation before opening a
  separate investigation.

- SCENE-LINT non-determinism (the reported 0/7/9 error-count flip between
  identical runs) root-caused as a cross-process render-evidence race, not a
  scene-lint rule bug: `pipeline/build_generated.sh` unconditionally
  `rm -rf generated`s the whole `generated/` tree (including
  `generated/scene_render_stats/`) early in `build_github_pages.sh`, while
  `tools/scene_to_png.mjs` is the only writer of that evidence and runs near
  the end of the same build, one scene at a time. A `validate.py` run
  concurrent with a build observes anywhere from 0 to 9 spurious
  `missing_render_evidence` findings purely from timing. Reproduced
  (5x direct scene_lint runs at 0 errors, 5x aggregate validate runs at 9
  errors, confirmed a live disappearance of `generated/scene_render_stats/`
  mid-run) and documented with pinned file:line evidence and three candidate
  durable fixes in `docs/active_plans/audits/scene_lint_nondeterminism.md`
  (new, not yet git-tracked; link added once committed).
  Routed jointly to the validation owner (`validation/scene_calc/dump.py`,
  `validation/scene_lint/cli.py`) and the pipeline owner
  (`pipeline/build_generated.sh`, `build_github_pages.sh`,
  `tools/scene_to_png.mjs`); no fix applied by this audit.
- Fixed the band-membership predicate rather than adding a vertical gap
  constant or removing an object: a gap constant would have patched a scene
  the engine already believed fit, and object removal was rejected as
  whack-a-mole that deletes pedagogy and only moves which pair collides
  (the same class of fix that previously targeted `rear_tip_box` itself).

### Developer Tests and Notes

- Widening the base-scene test set surfaced findings the stale hand lists hid.
  In `test_generalization_render.mjs`, assertions B (no fallback/placeholder
  SVG) and C (aspect ratio preserved) fail on ALL 9 base scenes, including the
  5 originally listed; this is pre-existing and systemic (the render/assertion
  logic was untouched, the test exits 0 regardless). The newly-covered
  `microscope_basic` additionally fails F (no item overlap) and I (no
  label-label overlap) at 7/11 -- a real layout coverage gap the 5-scene list
  was hiding; left failing for the owner to route. Separately,
  `test_viewport_sweep.mjs` errors on every scene because its
  `rewriteMainTsForScene` mechanism reads `src/main.ts`, which no longer exists
  (the entry point moved to `src/*_entry.tsx` and the per-scene render path
  migrated to `scene_viewer.html?scene=`); this ENOENT is pre-existing and
  independent of the scene list (the old 5-scene version fails identically at
  line 32 before any scene logic). The scene-list refactor is correct
  (9 scenes discovered, gate derived as `9 * 3 = 27`); repairing the dead
  rewrite-rebuild mechanism is a separate owner decision, out of scope here.
- Verified the parallel sweep against a serial baseline. `./check_codebase.sh`
  green (`PASS: 5 checks passed`). Single-walker back-compat: `node
  tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol
  trypan_blue_counting` (no new flags) logged `port=8126,
  outDir=.../test-results/walker` and wrote `test-results/walker/
  playthrough_report.json` exactly as before. Ran the full sweep both ways:
  `./run_playwright_tests.sh` (parallel, default 4 jobs) in 42s and
  `./run_playwright_tests.sh --jobs 1` (serial) in 2m41s; a per-protocol verdict
  diff across all 31 protocols showed 0 mismatches (PASS=27 / FAIL=4 in both).
  Color gating checked both ways: under a pseudo-TTY (`script -q /dev/null
  ./run_playwright_tests.sh`) PASS lines carry `\x1b[32m` (green) and FAIL lines
  `\x1b[31m` (red); piped through `tee`/`grep` the sweep emits no escape codes
  from its own output and `sweep_summary.json` has zero escape bytes.

- M16 walker-scope closeout: recorded the scene-manager handshake in
  `docs/archive/audits/walker_click_bug_register.md`. Marked the `drug_dilution_setup` /
  `media_bottle` register row RESOLVED/STALE (the scene's `remove_placements` now documents
  keeping the inherited `rear_left_media_bottle`, so the bug no longer reproduces), and added a
  "Scene-manager handshake (out of walker scope)" section listing the remaining
  scene-placement gaps with fix owner = scene-manager plan: missing `hood_surface`
  (passage_hood_detachment microscope-view), missing `plate_reader` (mtt_solubilization_readout
  bench), missing `kimwipe_pad` (staining_bench base), and two duplicate-placement
  `AmbiguousTargetError` cases (`media_bottle` for plate_drug_treatment_media_adjustment,
  `laemmli_4x_bottle` for the sample-prep sdspage protocols). None are walker-scope.

- M15 "Certified walker sweep register": ran the sound post-M13 walker (`npm run build`
  then `npm run walk:all`) across all 31 curriculum protocols and confirmed the totals match
  the pre-M13 triage exactly (PASS=12, unsupported_gesture=0, FAIL=19; no protocol flipped
  membership). Added a wrong-order negative pass (`--wrong-order` on 3 sampled PASS
  protocols) and confirmed the runtime rejects every injected out-of-order click while the
  protocol still completes. Promoted the pre-triage into the certified register at
  `docs/archive/audits/walker_click_bug_register.md`, ranked most-severe first and
  cross-checked row-by-row against `test-results/walker/sweep_summary.json`, with sampled
  before/after screenshots for the subpart-click, target-missing, and adjust-commit
  clusters. One wording drift noted (not a category change): `trypan_blue_counting` now
  surfaces as `click_did_not_advance` instead of a step-validator-shaped message, same
  failing step and root cause as before.

- M13 "Gesture load-time invariant": added a `tests/test_step_machine.mjs` describe block
  covering the load-time gesture-affordance invariant. A negative test synthesizes an out-of-set
  gesture (`levitate`) and asserts `create_step_machine` throws `UnaffordancedGestureError` at
  load with the offending protocol, step, target, and gesture in the message. Positive tests
  assert a normal all-click protocol and a wired `adjust` protocol both construct without
  throwing (48 step-machine Node tests pass; 456 Node tests overall, 454 pass, 2 skipped).

- Read-only triage: classified the 19 `npm run walk:all` post-M12 FAILs into layer
  categories (`docs/active_plans/audits/walk_all_fail_triage.md`), pre-M13 evidence for M16.
  Dominant cluster (5 protocols) is a `target_not_actionable` bug: several protocols author a
  `gesture: click` directly on a `.<subpart>` target (a well, tube, or gel lane), but subparts
  render as a non-interactive material-tint overlay only (`pointer-events: none`); no passing
  protocol uses this pattern. Also found 4 `target_missing` protocols (2 sharing one
  `kimwipe_pad` never-placed root cause), 2 `no_active_interaction` step-transition gaps, 2
  unresolved `adjust_did_not_advance` cases, and one `validator_rejected` step-validator
  threshold gap (`trypan_blue_counting`, 92.5 vs an exact-match `contains: 90`). No
  `AmbiguousTargetError` (the pre-M12 dominant class) appears in the current 19; that class is
  confirmed retired.
- Release closeout verification snapshot (velvet-napping-tower plan): Node test suite
  501 pass / 2 skip, `check_codebase.sh` 5/5 green, `run_validate.sh` YAML validation 0
  errors, pytest 4794 pass, and the full walker sweep 26/31 PASS with the 5 remaining
  FAILs clean-except-owned (see the Decisions and Failures entry above for ownership).
  This is the last entry for the trustworthy-walker/layout-gate release; the
  in-progress material-oracle general-walker verification work (WP2-4) is a separate,
  later milestone and gets its own changelog entry when it lands.
- Added the "Band-owned AABB containment invariant" section to
  `docs/specs/LAYOUT_ENGINE.md`: the coordinate frame (scene-percent), the
  containment invariant (final placed object box inside its band; bands
  non-overlapping), same-horizontal-row band membership, and the rule that
  the engine diagnostic reflects final placement.
- Added `tests/test_layout_placement_containment.mjs` (4 tests, inline
  data): asserts distinct non-overlapping cohort intervals, per-item band
  containment, zero cross-zone overlap, and catches a seeded transitive
  fusion.
- Witness (band ids, `microscope_basic`, before/after): before, all 5 zones
  shared one band `[5, 95]`; after, rear cohort `[5, 40.14]`, bench cohort
  `[40.14, 95]`, `instrument_area` in its own band `[18, 92]`;
  `rear_tip_box` vs `left_microtube_rack` overlap 100.0% -> 0.0%.
- Verified: `npx tsc --noEmit` clean; `node --import tsx --test` reflow_zones
  9/9, placement_containment 4/4, item_overlap 7/7; `./run_playwright_tests.sh`
  -> 91 passed / 1 skipped / PASS, no unexpected-pass.
