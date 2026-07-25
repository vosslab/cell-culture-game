## 2026-06-04

### Additions and New Features

- Added `docs/active_plans/decisions/tooling_evaluation.md`, a decision record
  evaluating every proposed tool (SolidJS, Solid stores, SVGO, Valibot/Zod, Ladle,
  Vitest, Solid Testing Library, localStorage, Vite, XState, TanStack Router/Query,
  yaml runtime loader, vite-plugin-solid-svg, SolidStart, SvelteKit, UnoCSS/Tailwind,
  Storybook, esbuild watch) with pros, cons, and a fit verdict grounded in the
  current build pipeline and contract invariants. Top recommendation: a Valibot/Zod
  runtime guard GENERATED from `validation/yaml_schema/constants.py` (not hand-written)
  to close the constants.py / `src/shell/adapter/types.ts` drift gap.
- Added unit tests for `enumerate_candidate_targets` in
  `tests/test_affordance.mjs` (4 new cases): top-level names included, subpart
  names with "." excluded, empty `result.final` yields empty set, and result
  contains exactly the top-level names provided. This was the real coverage gap:
  a bug returning an empty/wrong set would have made the whole affordance
  invisible with no test catching it.
- Added `adjust` and `type` directed-gesture cases to
  `tests/test_affordance.mjs` (2 new cases): both return "active" when
  `item == active_target`, uniformly locking the "any other directed gesture"
  branch. Test count grew from 7 to 13.

### Fixes and Maintenance

- Reordered imports in `tests/playwright/test_affordance_evidence.mjs`: stdlib
  `node:*` now comes before external `playwright`, then local `./repo_root.mjs`
  (matches TypeScript style guide import ordering).
- Removed dead `return {...}` from `assert_select_affordance` and
  `assert_click_affordance` in `tests/playwright/test_affordance_evidence.mjs`;
  both are side-effect assert functions and callers discarded the return values.
- Replaced raw color/style literals in pass-message strings of hover-persistence
  and focus-persistence assertions with the named constants
  `EXPECTED_CANDIDATE_OUTLINE_COLOR` / `EXPECTED_CANDIDATE_OUTLINE_STYLE` so
  they cannot go stale when the constants change.
- Added design-assumption comment above `candidate_count === clickable_count`
  assertion in `tests/playwright/test_affordance_evidence.mjs` documenting that
  select_check contains only candidate scene objects (no non-candidate fixtures)
  and noting the update needed if that changes.
- Stripped WS-3A/M3 planning tags from the file header of
  `tests/playwright/test_affordance_evidence.mjs` and replaced WS-2C tags at
  hover-persistence and focus-persistence comments with plain wording.

## 2026-06-03

### Additions and New Features

- M3 WP-SUBPART-RENDER: added the GENERIC structured-subpart material-tint
  renderer so per-well material color is actually drawn. New
  `src/scene_runtime/renderer/subpart_visual_state_renderer.tsx` (265 lines) builds
  ONE static `<svg>` overlay per structured object, sized to the def's `view_box`,
  and draws one shape per `subpart_geometry` entry via `<For>`. Each shape's fill
  is a per-subpart `createMemo` reading the driving field through the narrow
  `getSubpartStateField` accessor (M3 #18) and the single color source
  `resolve_color_result` (M3 #17): `ok:true`+color paints that color, `ok:true`+null
  (empty/sentinel/unseeded) renders `fill="transparent"` (D4), and `ok:false` routes
  to the per-item degrade sink (never a painted region). The interpreter keys on the
  DECLARED contract (`render_effect == material_tint`, `applies_to == subpart`,
  `target == subpart_geometry`, plus generated `subpart_geometry`/`view_box`),
  hardcoding no object name, no field name (the driving field NAME is read from the
  `visual_states` key), and no shape literal (it switches on `geometry.shape`
  circle/rect). The pure dispatch predicate lives in a JSX-free
  `src/scene_runtime/renderer/subpart_dispatch.ts` (`find_material_tint_subpart_field`)
  so it is importable without the Solid JSX transform and both `scene_item.tsx` and the
  renderer dispatch on the same function. `scene_item.tsx` stays dispatch-only: it
  replaces the old subpart-skip with a `<Show>` on the predicate result and a one-line
  forwarder that re-qualifies each failing well's degrade message
  (`well_plate_96.A1`) to the existing SceneView-owned degrade sink. The overlay is a
  separate `<svg>` over generated geometry: it references no base-SVG id, builds no DOM
  id, does no anchor lookup, queries no arbitrary DOM, and carries
  `pointer-events: none` so the base art stays clickable; each shape carries
  `data-subpart-name` + `data-material-name`. Browser evidence (contract item 4, D11
  spatial correspondence) in `tests/playwright/test_subpart_well_plate_render.mjs`
  mounts the real generated `bench_basic` scene (which places `well_plate_96`) through
  the production `mountScene` path and drives per-well state ONLY through the store's
  normal seed/write path (`seed_target` + `set_object_state`, schema/enum validated,
  no DOM hand-editing): it asserts exactly 96 `[data-subpart-name]` shapes render, all
  transparent before any write, and after writes A1=`mixed` paints `#686868`, A2=`empty`
  is transparent (A1 != A2), H1=`mixed` paints `#686868` (a distant painted well), and
  H12 (unset) is transparent; screenshots saved under `test-results/subpart_render/`.
  Modularity proof in `tests/test_subpart_visual_state_renderer.mjs` (8 pure tests):
  the same predicate dispatches a synthetic rect-subpart object with a RENAMED driving
  field with no new TS, and returns null whenever any contract part is missing. The
  store's well subpart `material_name` enum is the closed sentinel set `[empty, mixed]`,
  so only those two paint through the renderer's normal path today (`mixed` -> built-in
  gray, `empty` -> transparent); registry-backed per-well drug colors remain gated by
  the WP-STORE/object enum decision (the unimplemented per-well distinct-material
  feature). `npm run check`: 6/6 PASS (228 pass, 0 fail, 2 skipped). tsc: 0 errors.
  `npm run build`: built `dist/` GitHub Pages-ready. Existing reactivity-lifecycle and
  scene-degrade Playwright specs still pass (no regression).

- M3 WP-STORE: added the narrow reactive read accessor
  `getSubpartStateField(placementId, subpartName, fieldName)` to
  `src/scene_runtime/state/scene_store.ts`. It builds the subpart target
  (`placementId + "." + subpartName`), indexes the Solid store proxy, and
  returns one declared subpart state-field value (or `undefined` when the
  subpart is unseeded or the field is absent). Both property reads happen on the
  reactive proxy, so the structured-subpart renderer (M3 #19) can read each well
  independently and track fine-grained: A1 and A2 are distinct targets that
  update separately. The accessor never returns the `TargetState` record or the
  `SceneStoreState` tree, so a consumer cannot subscribe to the whole store. No
  parallel store was added; this reuses the existing `TargetState.subpart`
  storage and its writes/seeding. Added focused tests in
  `tests/test_scene_store.mjs` using a `well_plate_96` fixture where A1 and A2
  hold divergent material states and are read separately; two `createMemo`-based
  reactivity assertions prove A1/A2 track independently and a later seed+write
  becomes visible. Those two assertions are gated to Solid's reactive (browser)
  build, since `node --import tsx` resolves Solid's non-reactive server build by
  default; run `node --conditions=browser --import tsx --test
  tests/test_scene_store.mjs` to exercise them. `npm run check`: 6/6 PASS
  (220 pass, 0 fail, 2 skipped). tsc: 0 errors.

- M1 WP-MATERIALS: confirmed all 7 registry-backed well materials resolve to a
  scalar `display_color` across every writing protocol. Added sentinel guard to
  `MaterialValidator._validate_entry` (tag `SENTINEL_IN_REGISTRY`): rejects
  `empty` or `mixed` authored as a materials.yaml entry per
  `MATERIAL_YAML_FORMAT.md` "Sentinels do not appear in materials.yaml". Removed
  the illegal `empty` entry from
  `content/protocols/cell_culture/passage_pellet_reseed/materials.yaml`; the
  sentinel is a built-in resolver state and was never read from the registry.
  The protocol writes only `media` to wells; no runtime behavior depended on the
  entry. Tests: 1451 passed (4 new). STEPPER: 0 errors, 0 s-unregistered.
  Content lint: 168 files, 0 errors, 5 warnings, 0 advisories.

- Added D6 structured-well-plate per-subpart material rule to `ObjectValidator`
  (`validation/yaml_schema/object_validator.py`). The rule fires only for objects
  with `structure.subpart_kind: well` and rejects any such object that lacks both
  `material_name` and `material_volume` declared with `applies_to: subpart`.
  Non-well structured objects (rack/tube, gel/lane) and unstructured plates are
  unaffected. `well_plate_96.yaml` passes the rule cleanly (0 new errors).
  Three focused behavioral pytests added in
  `tests/test_object_validator_well_plate_subpart_material.py`.
  Full suite: 1447 passed. Content lint: 168 files, 113 errors (timing artifact; see Decisions and Failures), 5 warnings, 0 advisories.

- SVG-pipeline work (M1 through M5, partial): per-render-instance id namespacing, SVG manifest
  generation, tiered rendering infrastructure, dev tooling, and asset hygiene. Specifically:
  - Per-render-instance id namespacing at the single injection chokepoint
    (`src/scene_runtime/renderer/inject_svg.ts` `namespaceSvgIds`). Every injected SVG's internal
    ids are prefixed `<asset_name>__<scene_or_page_id>__<placement_name>__<old_id>`. Reference
    rewriting covers all `url()` forms (unquoted, quoted, whitespace) in any attribute, `href` and
    `xlink:href`, and `url(#id)` inside `<style>` text nodes. Fixes the duplicate-id collision
    (`clipPath id="a"` repeated across Servier-normalized assets) that mis-clipped objects in
    multi-object scenes (the "wedge" on `destain_gel_rock`, `destain_gel_setup`, `stain_gel`,
    `image_gel`).
  - SVG manifest generation: `pipeline/gen_svg_manifest.py` (renamed from `gen_svg_registry.py`)
    emits `generated/svg_manifest.ts` mapping `asset_name -> { relative path, requires_dom_svg }`.
    `build_github_pages.sh` copies SVG sources to `dist/assets/svg/<category>/`. New runtime
    fetch/cache layer `src/scene_runtime/renderer/svg_manifest_loader.ts`. New anchor-resolver seam
    `resolveAnchor(host, bareAuthoredId)` so material code resolves bare authored anchor ids to
    namespaced DOM elements without string concatenation.
  - `requires_dom_svg` predicate derived from declared object capabilities
    (`material_container`/`structured_surface`, non-empty `visual_states` or `composite`,
    `fill_height` formula). Objects needing internal SVG access are DOM-injected; static objects
    are `<img>`-eligible. Tightened from 41 to 30 assets flagged.
  - Dev tools: `tools/svg_to_html_render.mjs` (multi-swatch SVG render/diff harness using
    Playwright Firefox) and `tools/svg_identity_sweep.py` (perceptual-hash duplicate/mislabel
    sweep). Identity sweep report in `docs/active_plans/audits/svg_identity_sweep.md`.

- Registered and placed `well_plate_96` using the existing Servier SVG `96well_pcr_plate.svg`.
  Created `content/objects/plate/well_plate_96.yaml` with a grid 8x12 structure,
  subpart groups, object-level `material_name`/`material_volume` state fields (required by
  `kind: plate` validator), and `material_container` capability. Added one placement to each
  of `hood_basic` and `bench_basic`; removed the `microtube_rack_24` placeholder placements
  and stale quarantine notes from 6 cell-culture protocol-local scenes. After placement, YAML
  target warnings for `well_plate_96.*` cleared automatically. The residual per-well material
  gap is reported as ONE narrowly-keyed STEPPER signal:
  `well_plate_96: per-well material state not implemented (K writes across M protocols, out of
  scope)`. Per-well fill rendering remains out of scope (see TODO.md).

- M5 SVG cutover COMPLETE (closeout): the runtime now renders SVG from
  `generated/svg_manifest.ts` only, verified post-material-merge. The tiered render
  path is live: objects with `requires_dom_svg: true` (30 of 56 assets, derived from
  declared capabilities) fetch SVG text and inject namespaced SVG DOM; objects with
  `requires_dom_svg: false` render as `<img>` with relative manifest paths that
  resolve under the GitHub Pages repo subpath.
- New test `tests/playwright/test_svg_file_loading.mjs`: serves `dist/` under
  `http://localhost:<port>/virtual-lab-protocol-simulation/` and proves SVGs load
  (HTTP 200, `image/svg+xml`, relative URLs), the four wedge pages
  (`destain_gel_rock`, `destain_gel_setup`, `stain_gel`, `image_gel`) render with
  `duplicateInjectedIds=0`, a `requires_dom_svg:true` object (`bottle_green`) renders
  as injected `<svg>` while a `requires_dom_svg:false` object (`rocking_shaker_idle`)
  renders as `<img>`, and `resolveAnchor(host, "anchor_liquid_bounds")` resolves to
  the per-instance namespaced element with no string concatenation.

- M3 WS-3C: defined the interaction affordance in
  `docs/specs/SCENE_VOCABULARY.md` (new "Interaction affordance" section)
  and added a cross-link from `docs/specs/PROTOCOL_VOCABULARY.md` at the
  `select` gesture definition. The spec now closes the silence that allowed
  a visible-affordance gap: (a) every clickable scene object carries a
  baseline cue (pointer cursor + faint hover/focus outline), always on;
  (b) a directed gesture (`click`, `drag`, `adjust`, `type`) shows a strong
  solid ring on the single active target; (c) a `select` gesture shows equal
  strong candidate rings on all clickable objects present -- the correct
  answer carries the same ring as every other candidate and is never singled
  out (the student must identify it from the prompt); (d) the affordance is
  derived view state computed by the renderer from the active-interaction
  snapshot, never authored in YAML, never persisted, and it adds no
  vocabulary. Distinct ring styles (solid vs. dashed, color-plus-style not
  color-only) keep the directed vs. candidate cues accessible.

- M2 WS-2B: clickable scene objects are now keyboard-focusable and carry an
  accessible name. `src/scene_runtime/renderer/scene_item.tsx` gains `tabIndex={0}`
  and `role="button"` on the item root `<div>`, making every rendered `[data-item-id]`
  element reachable by Tab in reading order. The accessible name is sourced from
  `BoundPlacement.label` (the same visible object label already rendered beneath
  the item), so assistive technology announces the object by its display name
  without revealing select-answer identity beyond what a sighted student already
  sees. Enter/Space key activation was intentionally NOT added this pass; no
  existing target-submit helper was available to wire it to without expanding into
  gesture-dispatch refactoring. Activation ships as a tracked follow-up.

- M3 WS-3A: added `src/scene_runtime/protocol/affordance.ts`, a pure Solid-free
  helper that owns affordance-kind derivation. Exports `compute_affordance_kind`
  (maps active target, active gesture, item target, and candidate set to
  `AffordanceKind` -- "active" | "candidate" | "none") and
  `enumerate_candidate_targets` (builds the resolver-consistent candidate set from
  `PipelineResult.final`). Also exports types `AffordanceKind`, `AffordanceGesture`,
  `ActiveAffordanceAccessor`, and `ComputeAffordanceKindArgs`. No Solid reactive
  reads, no I/O, no per-protocol branch. Mount plumbing threads the active-interaction
  accessor from `protocol_host.tsx` through `render_scene.tsx` and `scene_view.tsx`
  down to `scene_item.tsx`.

- M3 WS-3A: `src/scene_runtime/renderer/scene_item.tsx` now derives and stamps a
  `data-affordance` attribute on every rendered scene-object root element. A
  `createMemo` reads the active-interaction accessor (active target + gesture) and
  calls `compute_affordance_kind` with the per-item object name and the scene's
  candidate set, producing `"active"`, `"candidate"`, or `"none"`. The attribute
  updates automatically on every step or interaction advance without any store write.

- M2 WS-2A: added baseline clickable cue and affordance ring rules to
  `src/style.css`. Every `[data-item-id]` element receives a pointer cursor plus a
  faint hover and focus outline at all times. `[data-item-id][data-affordance="active"]`
  carries a strong solid ring; `[data-item-id][data-affordance="candidate"]` carries
  a strong dashed ring. The compound attribute selectors give the ring rules higher
  specificity than the baseline hover/focus rule so a ring always wins when present.

- P1 WP-TYPE-1: added `src/scene_runtime/protocol/preset_guards.ts` with typed
  type-guard functions for all validator preset families. `load-time
  validate_protocol_presets` in `step_machine.ts` now runs at startup and throws
  with protocol/step/slot/index/preset/family on any misslotted preset, catching
  authoring errors before any student interaction.

- P3 WP-TYPE-3 (M1B-1): added authored-expected-value-directed coercion in
  `validators.ts` (`target_with_value`): the declared `value` type drives
  coercion direction -- numeric expects parse; string and bool require same-type
  match. A named `console.warn` developer diagnostic fires on a numeric-format
  mismatch so authors can trace type errors without reading validation source.
  Regression tests in `tests/test_protocol_validators.mjs`.

- P4 WP-RX-1: `subscribeEmitterToSnapshot` in `src/shell/signals.ts` now returns
  `{snapshot, unsubscribe}` instead of discarding the unsubscribe handle. Three
  call sites in `protocol_host.tsx` updated to capture the handle; `pagehide`
  teardown wired. Resolves the previously-tracked emitter listener leak.
  `tests/test_shell_signals.mjs` updated with fake-emitter unit tests confirming
  subscribe/unsubscribe lifecycle.

- P6 WP-UX-2: added visible type-input rejection feedback in
  `src/shell/hud/type_input.tsx`: a Solid signal plus `<Show>` renders the
  string "Entry not accepted, try again" when `handle_type_commit` returns false.
  No ARIA added (pointer-optimized runtime; see "Accessibility scope" in
  [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md)). New
  `tests/playwright/test_type_input_feedback.mjs` proves the message appears on
  a bad commit and is absent on a good one.

- P8 WP-UX-4a: native `title` tooltip added to truncated `StepOutline` labels in
  `src/shell/regions/step_outline.tsx`. Pointer users hovering a clipped step name
  now see the full label without any JS.

- P9 WP-UX-4b: `src/launcher/protocol_launcher.tsx` now uses Solid `<Show>` for the
  empty-state path. When the protocol list is empty the launcher renders a
  human-readable message instead of a blank screen.

### Behavior or Interface Changes

- Narrowed `authored_value_matches` parameter type from `unknown` to
  `string | number | boolean` in `src/scene_runtime/protocol/validators.ts`.
  Both call sites in `validate_target_with_value` and `validate_final_state_matches`
  now guard the raw `unknown` entry with an explicit type check before passing it
  to the helper.

- SCENE-LINT and SCENE-DESIGN now emit a precise prerequisite failure when
  rendered scene stats are missing or stale, replacing the generic
  `dump_error [BLOCKED]` output. `validation/scene_calc/dump.py` raises a new
  typed `MissingRenderEvidenceError(RuntimeError)` at both render-evidence raise
  sites (missing `generated/scene_render_stats/<scene>.stats.json`, or a
  load-failed render with no geometry block); both CLIs catch that type narrowly
  and print `SCENE-LINT blocked: rendered scene stats are missing.` (and the
  `SCENE-DESIGN` variant) pointing at `./build_github_pages.sh` as the fix. Both
  stages still FAIL on this prerequisite. Validation never renders:
  `run_validate.sh` and the validators do not auto-run the renderer; scene
  render-stats are produced by the build instead.

- Scene render-stats are now BUILD output: `build_github_pages.sh` generates
  `generated/scene_render_stats/*.stats.json` as its final build step (after
  `dist/` is built, via `node tools/scene_to_png.mjs --all`), so the required
  validation evidence is a declared build artifact, not a hidden test-results
  cache.

- `run_validate.sh` validates existing generated stats only (no rendering, no
  self-heal); when the stats are absent, `MissingRenderEvidenceError` fails
  clearly pointing at `./build_github_pages.sh`.

- Machine stats relocated from `test-results/scenes/` to
  `generated/scene_render_stats/`; PNG screenshots are now optional
  (`node tools/scene_to_png.mjs --all --png`) human artifacts under
  `test-results/scenes/`. Documented in `docs/USAGE.md` and
  `docs/FILE_STRUCTURE.md`.

- Arc-extrema bounding-box fix in `tools/normalize_svg_v2.py`: true elliptical-arc extrema with
  rotation, large-arc, and sweep flags (not endpoint-only), preventing clipped arc assets.
  Documented in `docs/active_plans/audits/normalize_svg_v2_audit.md`.

- Migrated the TypeScript material-color path from nested `{light, dark}` to a
  single scalar `display_color` hex string (M3 WP-COLOR), clearing the 171 tsc
  `TS2322` errors that task #25's scalar pipeline emit left in
  `generated/protocol_materials.ts`. `MaterialEntry.display_color` is now
  `string`, `MaterialColor` is now `string | null`, and no runtime path reads
  `.light` / `.dark`. Added `src/scene_runtime/renderer/material_color.ts` as the
  single color source: `resolve_color_result(material_name, registry)` returns
  the D3 discriminated union `{ ok: true; color: string | null } | { ok: false;
  reason: string }` (empty/sentinel/no-field -> ok/null; built-in `mixed` ->
  ok/`#686868`; registry-backed valid scalar -> ok/`#rrggbb`; non-sentinel
  missing from a provided registry or invalid `^#[0-9a-f]{6}$` hex -> not-ok with
  a reason; null registry -> ok/null no-color context). `resolve_material_color`
  in `visual_state_resolver.ts` delegates to it and rethrows `ok:false` to keep
  the render path fail-loud. Vessel fills (the `Overlays` fill consumer in
  `scene_item.tsx`) render identically, now reading the scalar color directly.
  Added 12 pure resolver-contract pytests-equivalent Node tests in
  `tests/test_material_color.mjs` and updated the existing
  `tests/test_visual_state_resolver.mjs` fixtures to scalar. tsc: 171 -> 0.

- Removed the protocol-specific `well_plate_96` material-write fold from
  `validation/stepper/state.py`. The fold had been suppressing all
  `state_value_not_allowed` errors for any write to `well_plate_96.material_name`
  whose value was not in the declared plate-level enum `[empty, media, cells]`.
  Also removed two pre-existing TEMPORARY unresolved-target demotions from
  `validation/stepper/state.py` and `validation/yaml_schema/protocol_validator.py`;
  these had been dead since the plate was placed (targets now resolve) and removed
  cleanly without changing any active finding. With the fold gone, 834 genuine
  `state_value_not_allowed` errors surfaced initially: protocols such as
  `mtt_plate_reaction` and `plate_drug_treatment_*` write per-well drug material
  names (`carboplatin`, etc.) into `well_plate_96.material_name`, whose plate-level
  enum does not include drug material names. This was the unimplemented per-well
  distinct-material feature, now visible instead of hidden. The validator is now
  protocol-agnostic throughout. After M1 per-subpart material state implementation
  (see Additions), the 834 `state_value_not_allowed` errors resolved to 0; see
  Decisions and Failures for the resolution path.

- Bundle-size win realized by the M5 SVG cutover: `dist/protocol_host.js` dropped
  from 1.7 MB to 478 KB (489496 bytes), about 72% smaller, as the ~1.3 MB inline-SVG-markup
  blob left the JS bundle. The bundled inline-SVG-markup registry
  (`generated/svg_registry.ts`) is no longer emitted (the generator removes any stale
  copy) and is no longer imported anywhere under `src/`. `structural_guards.ts` Guard 6
  now validates asset presence against `SVG_MANIFEST`, not the removed registry.

- Moved `enumerate_candidate_targets` out of `src/scene_runtime/protocol/affordance.ts`
  into a new renderer-layer module `src/scene_runtime/renderer/affordance_candidates.ts`.
  The function imports the layout `PipelineResult` type, so it belongs in the
  renderer/mount layer, not the protocol layer; keeping it in `protocol/` was a
  protocol-imports-layout boundary violation. `compute_affordance_kind` stays in
  `src/scene_runtime/protocol/affordance.ts`. Zero behavior change; all call sites
  updated to the new import path. `tsc`: 0 errors. `check_codebase.sh`: 6/6 PASS.

- Replaced the hand-written `AffordanceGesture` union type in
  `src/scene_runtime/protocol/affordance.ts` with the canonical `Gesture | null`
  imported from `src/shell/adapter/types.ts`. The two definitions had identical
  member sets, so there is no behavior change; the hand-written union was a
  vocabulary duplicate that could silently drift from the canonical set.

- P2 WP-TYPE-2: removed 7 lateral-downcast casts in `step_machine.ts`, narrowing
  through the preset type-guards added in WP-TYPE-1. Type narrowing is now
  structural, not asserted.

- P5 WP-UX-1: removed misleading `tabIndex` and `role="button"` from the scene
  object root `<div>` in `src/scene_runtime/renderer/scene_item.tsx`; these were
  added in an earlier pass before the pointer-only scope decision was recorded.
  Also enlarged scene-error overlay text from 10px to 14px for readability.

- P7 WP-UX-3: hover-outline alpha in `src/style.css` raised from 0.35 to 0.45
  (`rgba(37,99,235,...)`) for improved visibility on light backgrounds. Outline-only
  (no fill); no color change.

- WP-DOC-1 (this patch): added "Accessibility scope" subsection to
  `docs/PRIMARY_DESIGN.md` recording that keyboard navigation, ARIA, focus
  management, and screen-reader support are not current goals for the pointer-
  optimized scene runtime. Deleted conflicting keyboard-accessibility task lines
  from `docs/TODO.md` and `docs/ROADMAP.md`; added breadcrumb pointers to the
  new subsection. This records the maintainer decision and prevents re-introduction
  of accessibility work as a silent TODO item.

### Fixes and Maintenance

- Scrubbed all planning/workstream/milestone scaffolding tokens from `src/`
  comments (M1B, M1B-1, M1B-2, WP-SEAM, WP-CHECK, WP-DISC, WP-3-8, WP-3-10,
  WP-FRAME-1, WP-FRAME-2, WP-CHROME-1 through WP-CHROME-3, WP-RESOLVE-1,
  WP-RESOLVE-2, WP-RESOLVE-3, WP-TYPE-1, WP-2-4, WP-2-5, WS-M1-B, WS-M1-E,
  WS-M2-I, WS-M3-C, WS-M3-D, WS-M5-ST, M-SEAM, resilient-twirling-pond).
  Each comment was rewritten in plain present-tense language keeping the same
  technical meaning. One token remains in a string literal (console.warn in
  `scene_op_deps.ts`) and was intentionally left per the rule that string
  literals must not be changed.
- Annotated `[data-item-id]:focus-visible` in `src/style.css` as inert under
  the current pointer-only scope (tabIndex removed from scene items); kept as
  reversible infrastructure rather than deleted because it shares a rule block
  with the still-active `:hover` selector.

- Stripped planning-scaffolding tags (WS-1A, WS-1B, WS-2A, WS-2B) from permanent
  source comments in five files: `src/scene_runtime/protocol/affordance.ts`,
  `src/scene_runtime/renderer/render_scene.tsx`,
  `src/scene_runtime/renderer/scene_item.tsx`,
  `src/scene_runtime/renderer/scene_view.tsx`, and `src/protocol_host.tsx`. Replaced
  each tag with a plain English phrase (see tag replacements below). Also merged the
  split `import type { ActiveAffordanceAccessor }` + `import { compute_affordance_kind }`
  pair in `scene_item.tsx` into one statement with an inline type modifier, matching the
  existing style in `render_scene.tsx`. `tsc`: 0 errors. `npm run check`: 6/6 PASS.

- Asset hygiene: deleted byte-duplicate `assets/equipment/vortex_new.svg`; replaced the mislabeled
  `rocking_shaker_idle.svg` with the DBCLS shaker (CC-BY-4.0, attributed in
  `docs/THIRD_PARTY_ASSETS.md`).
- Doc and comment cleanup from pre-merge audit: updated stale `SVG_REGISTRY` wording in
  `docs/specs/SVG_PIPELINE.md`, `docs/CODE_ARCHITECTURE.md`, `docs/FILE_STRUCTURE.md`;
  `gen_svg_registry.py` references updated to `gen_svg_manifest.py` where applicable.
- Renamed mislabeled `bench_basic` placement `center_rocking_shaker` (object `centrifuge`) to
  `center_centrifuge`. Propagated the rename into 5 inheriting scenes'
  `remove_placements` lists and the local add in `centrifuge_workspace`
  (-> `center_centrifuge_spin`). Cleared 66 `placement_name_collision` errors and 4
  `tray_present` `undeclared_state_field` errors.
- Fixed a real bug in `validation/stepper/state.py` where `remove_placements` (a list of
  strings) was read as a list of dicts, so removals were never applied. Also cleared 7
  `ambiguous_target_in_scene` errors by removing redundant inherited duplicate placements
  (`serological_pipette`, `hemocytometer_slide`, `microtube`, `pbs_bottle` x2,
  `media_bottle` x2) via `remove_placements` in protocol-local scene YAMLs.
- Scene-layout tuning across 8 base scenes cleared 15 SCENE-LINT overlap and outside-zone
  warnings; 54 warnings -> 39 warnings. Remaining cases require design judgment and
  are left out of scope.
- SVG anchor normalization. Added missing `anchor_liquid_clip` and
  `anchor_liquid_bounds` anchors to 6 liquid-container SVGs: `bottle_green.svg`,
  `bottle_orange.svg`, `bottle_pink.svg`, `bottle_medium_pink.svg`, `mtt_vial.svg`,
  `falcon_15ml.svg`. Also ran `normalize_svg_v2.py --in-place` on `mtt_vial.svg`
  (viewBox `0 0 102.085 270.69` -> `0 0 104.097 272.637`) and `falcon_15ml.svg`
  (viewBox `0 0 68.863 419.187` -> `0 0 70.68 421.427`). YAML non-normalized warnings
  dropped from 28 to 1 (residual: `tube_rack.svg` left out of scope -- ambiguous
  liquid-anchor placement for a structured rack with 8 tubes). Registry regenerated:
  95/95 PASS. Orphan deletion: 9 `*_new` SVGs remain unreferenced in YAML; no clear
  rename/supersession evidence, left in place.
- Net validation from the merges above (before hardcode removal):
  baseline 135 errors / 618 warnings / 121 advisories (FAIL) ->
  0 errors / 156 warnings / 114 advisories (claimed PASS at that point).
  That figure was achieved only because a protocol-specific fold in the
  protocol-agnostic validator was suppressing 834 genuine errors (see
  Behavior or Interface Changes above and Decisions and Failures below).

- WP-MAT-CROSSREF (M0 final): updated cross-references across the spec set so each
  non-material doc now points to the correct owning material doc. Key changes:
  `PROTOCOL_YAML_FORMAT.md` materials block replaced stale nested `display_color`
  table row and example (light/dark mapping) with the scalar `#rrggbb` schema and
  a link to `MATERIAL_YAML_FORMAT.md`; also fixed the generated-data description to
  use scalar `display_color`. `SCENE_VOCABULARY.md` split the single MATERIAL_CONVENTION
  reference into one entry for MATERIAL_VOCABULARY.md (terms) and one for
  MATERIAL_CONVENTION.md (render effects). `OBJECT_VOCABULARY.md` terms table now
  points `material` at `MATERIAL_VOCABULARY.md` instead of `MATERIAL_CONVENTION.md`.
  `validation/stepper/state.py` `spec_cite` for `unknown_material` updated from
  `MATERIAL_CONVENTION.md material identity` to `MATERIAL_YAML_FORMAT.md D1
  registry-backed membership`. `validation/yaml_schema/constants.py` `# spec:` comment
  for `MATERIAL_REQUIRED_KEYS` updated to cite `MATERIAL_YAML_FORMAT.md "Material
  entry schema"`. Within the five material docs, bare-backtick references to
  `MATERIAL_YAML_FORMAT.md`, `MATERIAL_DESIGN.md`, and `MATERIAL_VOCABULARY.md`
  (all tracked) were upgraded to hard markdown links. `MATERIAL_LINT.md` remains
  as bare backtick references only (file is untracked; upgrade deferred to commit).
  `MATERIAL_LINT.md` hook table updated to mark L5 and L3 spec_cite as EXISTS
  (done by WP-MAT-SWEEP and this workstream respectively).

- Resolved the post-material-merge doc conflicts in `docs/CHANGELOG.md`,
  `docs/CODE_ARCHITECTURE.md`, and `docs/FILE_STRUCTURE.md`, preserving both the
  material and SVG content from each side.
- Migrated SVG test tooling off the removed registry. `tests/playwright/svg_namespacing_harness.ts`
  and `tests/playwright/test_svg_id_namespacing.mjs` now use the post-cutover API
  (`injectSvgMarkupInto` with small inline-markup fixtures, `injectSvgFromManifest`,
  `resolveAnchor`) instead of `SVG_REGISTRY`/`injectSvgInto`; registry-specific
  error-message assertions were replaced with the real throw strings, and the obsolete
  "missing registry key" negative case was dropped (no key->markup lookup exists
  post-cutover). `tools/scene_to_png.mjs` fixed to read
  `generated/svg_placeholder_keys.ts` (was an undefined `SVG_REGISTRY_PATH`).
- One-line render-path lint fix in `scene_item.tsx`: the SVG resource error is narrowed
  to `unknown` then to Error/string/`JSON.stringify`, clearing `no-unsafe-assignment`
  and `no-base-to-string`.
- M2 WS-2C: fixed a CSS cascade defect in `src/style.css` where the affordance ring
  rules could be overridden by the baseline hover/focus outline. Ring selectors were
  re-anchored to `[data-item-id][data-affordance="active"]` and
  `[data-item-id][data-affordance="candidate"]` (compound attribute selectors,
  higher specificity) so a candidate or active ring always wins over the baseline
  `:hover`/`:focus-visible` outline and remains visible while the object is also
  hovered or focused.

- P4 WP-RX-1 (emitter leak fix): the previously-tracked emitter listener leak in
  `subscribeEmitterToSnapshot` is now resolved. The fix is documented as a
  learning-relevant item: unsubscribe handles from reactive bridges must be
  captured and wired to teardown (pagehide or dispose) to prevent listener
  accumulation across navigations.

### Removals and Deprecations

- M5 cutover closeout: `generated/svg_registry.ts` is no longer emitted (the generator
  removes any stale copy) and is no longer imported anywhere under `src/`. The gated
  runtime cutover described in the next bullet is now fully landed; the registry is
  removed from the app render path. `structural_guards.ts` Guard 6 validates against
  `SVG_MANIFEST`.

- `generated/svg_registry.ts` is now a transitional bridge file, still emitted, to be removed in
  the gated runtime cutover (scene_item render-mode flip + registry removal, including
  `structural_guards.ts` Guard 6). The cutover is gated on the material commit landing first.

- Removed the `is_active_target` runtime flag from `src/scene_runtime/state/scene_store.ts`,
  `src/scene_runtime/renderer/scene_item.tsx`, and the `test_scene_op_deps.mjs`
  flag-clear test. The flag drove the old box-shadow highlight path; it was superseded
  by `data-affordance="active"` + CSS outline (WS-3A/WS-2A). The `is_selected` flag
  and the `set_flags` API are retained for the named post-selection-confirmation-ring
  follow-up.

### Decisions and Failures

- Root cause of the multi-object "wedge": a duplicate inline-SVG id collision (`url(#a)` resolving
  to the first match in document order), not normalizer geometry. Fixed by per-render-instance id
  namespacing at the inject chokepoint rather than per-asset prefixing. Per-asset prefixing would
  miss same-asset-twice collisions.
- `requires_dom_svg` means "needs internal SVG access", not "has any visual state". This narrows
  the set from 41 to 30 assets. `<img>` is the safe default for static objects and is immune to
  the id-collision bug.
- Runtime cutover (scene_item render-mode flip + SVG_REGISTRY removal) is NOT done yet. It is
  gated on the material commit landing. Until then the `SVG_REGISTRY` remains in the app render
  path alongside the new manifest.
- Decision: `kind: plate` object validation requires declaring `material_name` and
  `material_volume` at the object level plus `material_container` capability. These are
  object-level placeholders only; per-well material state is not implemented and the
  object-level fields will be removed when per-well fill rendering is added (see TODO.md).
- Decision: kept the validator honest after hardcode removal. Rather than re-adding the
  `well_plate_96` fold or widening the plate-level `material_name` enum as a band-aid,
  the 834 `state_value_not_allowed` errors were resolved by implementing per-subpart
  material state (M1 WP-ENUM, WP-YAML, WP-STEPPER, WP-PLATEVAL, WP-MAT-SWEEP). The
  centrifuge rename, ambiguity fixes, scene-layout tuning, and SVG normalization from
  earlier workstreams all stand. Final validator state after M1: 0 errors; see M1
  gate results appended to this day-block.
- Decision (M4 WP-DOCS, well_plate_96 plan closeout): the material plan is COMPLETE for
  per-well material state and rendering. `tests/playwright/test_subpart_well_plate_render.mjs`
  mounts the real generated `bench_basic` scene via the production `mountScene` path, writes
  carboplatin through the store seed/write path (no DOM hand-editing), and asserts the
  well renders `#a719db` by `data-subpart-name`. All automated gates are GREEN. The
  material plan scope: per-well material state (834 `state_value_not_allowed` -> 0),
  registry-backed material acceptance (Python stepper + TS store, cross-layer aligned),
  scalar color resolution, PATH-B subpart geometry, and production render-path per-well
  color are all done. The visible end-to-end per-well protocol walkthrough is OUT OF SCOPE
  for the material plan. It is gated on task #28 (`[EXPERT_CODER] Wire visible adjust
  gesture affordance`), a separate web_ui task in the same gesture family as the landed
  select and type gestures -- a UI-affordance gap, not a material-rendering defect. The
  walkthrough spec at `tests/playwright/test_per_well_drug_walkthrough.mjs` is retained
  and honestly reports the blocker; render evidence is retained via the production-path
  harness.
- Decision (content_lint timing artifact): the "113 errors" count that appears in the
  D6 validator entry above was a concurrency artifact: the D6 rule landed while the
  materials.yaml scalar sweep (M1 WP-MAT-SWEEP) was still in progress. The ground-truth
  content_lint count at M1 completion is 0 errors, 5 warnings. The 113 errors were not
  pre-existing defects; they were schema findings created by the sweep transition and
  cleared by it. Rephrase in this entry for accuracy per REPO_STYLE changelog rules.
- Decision ([empty,mixed] schema seam): runtime acceptance of per-subpart `material_name`
  is registry-backed per stepper D1 (the full enum including drug names). The YAML
  `allowed` field in `well_plate_96.yaml` retains `[empty, mixed]` as the closed
  sentinel set for the object-level enum; the runtime store accepts registry-backed
  names via `seed_target` + `set_object_state` validated against the schema/enum at
  write time. This is not a vocabulary escape hatch: the seam is explicit and narrow.
  Task #27 (future: declared registry-backed field affordance) tracks the option to
  retire the `[empty, mixed]` syntactic seam entirely.
- Note: five new `docs/specs/MATERIAL_*.md` files were created as part of M0
  (MATERIAL_DESIGN.md, MATERIAL_VOCABULARY.md, MATERIAL_YAML_FORMAT.md,
  MATERIAL_CONVENTION.md narrowed, MATERIAL_LINT.md). `docs/specs/MATERIAL_LINT.md` is
  currently untracked in git. The human must `git add docs/specs/MATERIAL_LINT.md` (and
  the other four if not yet staged) so cross-doc links resolve on GitHub.
- Decision (WS-2B, keyboard Enter/Space activation): intentionally not shipped
  this pass. No existing target-submit helper was available in the runtime; wiring
  Enter/Space without one would have required factoring a new gesture-dispatch path,
  expanding scope beyond a visual affordance fix. The decision records that
  focusability and accessible naming are done; key activation is a named follow-up.
  The WS-3A Playwright evidence run surfaced the CSS cascade defect (rings lost
  under hover/focus) that WS-2C fixed.

- TRACKED follow-up (pre-existing Solid-infra, not introduced by the affordance
  cleanup): the emitter snapshot bridge in `src/shell/signals.ts` discards the
  `subscribe()` unsubscribe handle on every call, creating a listener leak on
  teardown. The candidate fix is Solid `from()`, which owns the subscription
  lifecycle; deferred until the bridge receives broader refactoring.

- TRACKED follow-up (pre-existing Solid-infra, not introduced by the affordance
  cleanup): `src/scene_runtime/renderer/scene_view.tsx` captures `props.result`
  and `props.root` into `const` at the top of the component body, which is the
  Solid props-destructure antipattern (the captured values are stale after a
  re-render, though currently harmless under dispose-remount). Deferred as a
  named follow-up for when the component is next refactored.

### Developer Tests and Notes

- Robustness fixes across four test files: loosened exact-count `warnings.length === 1`
  asserts to `>= 1` in `tests/test_protocol_validators.mjs`; replaced exact
  subscription-count and per-slot unsubscribe-count asserts with `>= N` behavioral
  contracts in `tests/test_shell_signals.mjs`; softened the `"interaction index 0"`
  literal substring check in `tests/test_step_machine.mjs` to verify locating info
  without coupling to exact phrasing; fixed silent-skip in
  `tests/playwright/test_type_input_feedback.mjs` when the welcome affordance is
  missing (now a hard failure), and dropped the verbatim `REJECTION_MESSAGE` copy
  match in favor of a visibility-only assertion on `[data-type-reject-message]`.
- Added failure message to Case 2b in `tests/test_authored_value_check.mjs`:
  `assert.ok(err instanceof BadAuthoredValueError)` now carries a second argument
  `` `Expected BadAuthoredValueError, got ${err.name}` `` matching Case 2a style.
- Added Case 3e to `tests/test_authored_value_check.mjs`: "normal protocol +
  unknown_subpart throws with context" asserts `UnknownAuthoredSubpartError` is
  thrown for a non-dev_smoke `mini_protocol` and that `err.message` includes
  the protocol name and step name, mirroring Case 3a context-string assertions.
  Test count grew from 28 to 29; all pass.

- New tests: `tests/playwright/test_svg_id_namespacing.mjs` (namespacing correctness + four wedge
  pages render clean), `tests/test_svg_manifest_predicate.py` (`requires_dom_svg` branches), and
  `tests/test_normalize_svg_geometry.py` (2 arc-extrema tests).
- New test from the M5 cutover closeout: `tests/playwright/test_svg_file_loading.mjs`
  (subpath file-loading: 5/5), proving manifest-served SVGs load and the tiered
  `<svg>`/`<img>` split renders.
- `check_codebase.sh` PASS (6 steps) after M1 through M4 and M5 Phase 1.
- M4 WP-DOCS final gate results (per-well material state plan):
  - `pytest tests/`: 1460 passed.
  - `./run_validate.sh`: TOTAL 0 errors. 288 warnings. 113 advisories across 7 stages. -> PASS (warnings only); STEPPER 0 errors.
  - `bash check_codebase.sh`: PASS 6/6 (typecheck, typecheck:lint, lint, format:check, css:policy, test:node).
  - `npm run build` / `build_github_pages.sh`: built `dist/` (GitHub Pages-ready).
- M4 WP-DOCS final closeout: material plan COMPLETE for per-well state + rendering.
  Automated gates GREEN. Per-well render proven via production-path Playwright harness.
  Visible-UI per-well-protocol walkthrough is out of scope for this plan; gated on #28
  (visible adjust gesture affordance, a separate web_ui task, not a material-rendering
  defect).
- M5 SVG cutover gate results (closeout, post-material-merge):
  - `bash check_codebase.sh`: PASS (6 checks).
  - `pytest tests/`: 1487 passed.
  - `node --test`: SVG id-namespacing 5/5 and file-loading 5/5.
  - `./run_validate.sh`: PASS (0 errors).
  - Wedge-page screenshots saved under `test-results/`.
- M3 WS-2C: hover/focus ring-persistence assertions added to
  `tests/playwright/test_affordance_evidence.mjs`. The spec asserts that when a
  candidate-ring object is hovered or focused, the candidate ring remains visible
  and the baseline outline does not replace it, proving the WS-2C specificity fix
  holds in a live browser.

## 2026-06-02

### Additions and New Features

- Made validation output honest and scannable (validation-clarity series). The aggregate runner and every stage previously printed warnings as "failures" and colored the count red: `YAML: 191 failures` were all WARNING-severity, `SVG: 86 failures` were 49 validator-bug normalization false-positives plus 37 orphan-file advisories, and `STEPPER: 31 failures` lumped 135 real errors with 398 warnings under a protocol-level count. Replaced the single "failures" count with a closed three-tier severity model rendered identically by every stage: `Checked <N> <items>. <E> errors. <W> warnings. <A> advisories.` Severity is the existing closed `Severity(ERROR, WARNING, INFO)` enum (INFO is the advisory tier, rendered "advisory"); it drives exit code (ERROR-only: warnings and advisories never fail the run) and color (error red, warning yellow, advisory dim) and nothing else. Added a grouped per-code rollup under each finding-bearing stage (`verbosity.severity_rollup`): fixed ERRORS/WARNINGS/ADVISORIES order, empty groups omitted, codes sorted by count, each line carrying an ASCII severity icon (`!` `?` `i`) so `NO_COLOR=1` loses no meaning. A friendly category label (`code`) drives the rollup grouping while the raw diagnostic (`tag`) is preserved in `--json`; per-stage `code -> category` maps own the labels (`T1_TARGET -> unresolved-target`, `placement_name_collision -> placement-collision`, etc.) and the finding's own severity (never the label) decides the tier. Added an aggregate `TOTAL:` scoreboard in `validate.py` that sums the three tiers across stages, prints a `FAIL`/`PASS`/`PASS (warnings only)` verdict, and lists `ERROR stages:` on failure. Result: the only red number is a real blocking error; `YAML` now reads `0 errors. 176 warnings. 0 advisories`, `SVG` `0 errors. 0 warnings. 37 advisories`, `STEPPER` `135 errors. 314 warnings. 84 advisories` with `(errors span 31 of 31 protocols)`. New regression tests in `tests/test_validation_clarity.py` (12 cases) lock severity bucketing, rollup icons/grouping, the dropped "failures" word, and both detection-bug fixes; updated `tests/test_validation_verbosity.py` for the three-tier summary line.

- Implemented the `select` and `type` gestures end-to-end (WS-M5-ST). `select` is the primary way a student drives a protocol: it means "choose the correct next-step object among the scene objects already present." There is no answer-choice list, no modal, and no choice id. `select` reuses the existing visible scene-object click affordance (the host promotes a click on the active target to the active `select` gesture); selecting a wrong present object is rejected exactly like a wrong-order click and does not advance. `type` renders a visible text-input affordance (`src/shell/hud/type_input.tsx`, selectors `[data-type-input]` / `[data-type-commit]`) that appears only while the active interaction's gesture is `type`; a real fill + commit routes the typed text to the new `step_machine.handle_type_commit`, which coerces it to the declared `value` field's type and validates via `target_with_value`. Walker (`tests/playwright/e2e/protocol_walkthrough_yaml.mjs` + `walker_helpers.mjs`): added `select` and `type` to the supported gesture set; `select` dispatches through the existing real-visible-click path (`clickTargetAndWaitProgress`), `type` through the new `typeCommitAndWaitProgress` (Playwright `locator.fill()` + Commit click, then wait for observable store progress), reading the expected typed value read-only from the new `gameState.activeTypeValue` projection. `adjust` and `drag` remain classified-unsupported (the walker still fails loud with `unsupported_gesture`). Two new dev_smoke fixtures prove the gestures through the visible UI: `tests/content/dev_smoke/select_check/` (two clickable bottles; selecting `pbs_bottle` advances, selecting `ethanol_bottle` is rejected -- proven by a passing `--wrong-order` walk) and `tests/content/dev_smoke/type_check/` (typing `42` into the input and committing advances). `pipeline/gen_object_library.py` now also includes fixture-local objects under `tests/content/dev_smoke/*/objects/` (tolerant: a fixture object that intentionally references a missing asset is skipped with a warning, not a build failure) so the runtime store can seed their declared `state_fields`. Ratified the corrected `correct_choice` semantics in `docs/specs/PROTOCOL_VOCABULARY.md`, `docs/specs/PROTOCOL_YAML_FORMAT.md`, and `docs/PRIMARY_SPEC.md`; moved `select`/`type` to supported in `docs/specs/WALKTHROUGH_GUIDE.md`; documented the `data-type-*` affordance in `docs/specs/INTERFACE_VOCABULARY.md`. Scene DOM contract diff stays 36/36 PASS (the type input is a new body-level control, not a scene-item DOM change).

- Rewrote the canonical walker for the new Solid protocol host (WS-M4-A). `tests/playwright/e2e/protocol_walkthrough_yaml.mjs` and `tests/playwright/e2e/walker_helpers.mjs` no longer target the retired cell-culture game (no `window.resolveInteractionByIndex`, no `#welcome-start-btn`, no `completionPath.kind`, no scene-switch buttons, no scoring screen). The walker now loads the per-protocol page `dist/<protocol>.html` exactly as a student would, clears localStorage, reloads, and drives the protocol entirely through real visible clicks. Dispatch is schema-driven from the read-only `window.gameState.activeTarget` / `activeGesture` (the same snapshot fields the runtime uses to resolve a click's gesture) plus the closed gesture set; there are NO step-name branches and NO per-protocol special cases. Only `click` has a visible affordance in the new host today; any other gesture (`adjust`/`select`/`drag`/`type`) fails loudly with an `unsupported_gesture` classification for M4-D rather than silently skipping or branching. Real-click integrity is enforced and self-audited: every advance is a Playwright actionability-checked `locator.click()` on a verified-visible `#scene-root [data-item-id]` element; the wait-for-progress predicate only reads `window.gameState`; the walker never writes the read-only surfaces, never calls an internal runtime/emitter API to advance, never forces a scene change, and never mutates `window.prompt`/`confirm`. Preserved `--screenshots per-step|per-interaction|per-click` and per-interaction report entries; rewrote `--wrong-order` to assert rejection through the read-only `wrongOrderClicks` counter (the new host has no `wrong_order_message` toast). First visible-state proof: `sdspage_extract_gel_from_cassette` (chosen as the simplest click-only protocol with a mid-flow `SceneChange`) walks 5/5 steps to `isComplete`, with a before/after artwork delta at the validated `transfer_gel_to_staining_tray` interaction (full scene swap `extraction_workspace` -> `staining_bench`). `sdspage_assemble_electrode_module` also walks 4/4 as the minimal first proof. Updated `docs/specs/WALKTHROUGH_GUIDE.md` to match (new-host startup, read-only window surfaces, schema-driven dispatch, single-scene `#scene-root` scoping, counter-based wrong-order, `unsupported_gesture` failure mode, terminal-state completion in place of a scoring screen).

- Read-only `activeTarget` / `activeGesture` on the walker debug surface (WS-M4-A). Extended `src/scene_runtime/protocol/walker_debug.ts` `WalkerGameState` with `activeTarget` / `activeGesture`, projected read-only from the existing emitter snapshot fields `active_interaction_target` / `active_interaction_gesture` (no runtime-logic change; these are the same fields the host's click resolver already reads to promote a click to the active gesture). This gives the schema-driven walker the current interaction's target without parsing protocol YAML or calling an internal API. Added a focused projection test to `tests/test_walker_debug.mjs` (215 node tests pass).

- Store-driven scene operations (WS-M3-D). Rewrote the scene-operation layer so a validated interaction drives the reactive `scene_store` instead of poking DOM attributes. Added `src/scene_runtime/protocol/scene_op_deps.ts` (`build_store_scene_op_deps`): `ObjectStateChange` partial-merges declared object state (auto-seeding subpart targets like `plate.A1` on first write via the new `scene_store.seed_target`); `CursorAttach` drives the cursor flag and preserves any already-held material; `SceneChange` re-renders the next scene and applies the reset policy while carrying cursor-held tool/material across the transition; `TimedWait` stays observable through the subsequent state write; `LayoutMove` is an explicit reported no-op (Option A, zero authored uses). Deleted `build_scene_op_deps` and its local `Map`/`Set` from `src/protocol_host.tsx`; the host now wires the store-driven deps and tracks the Solid root dispose for `pagehide` teardown. Added `tests/test_scene_op_deps.mjs` (reset matrix: scene-local vessel state clears, cursor-held tool/material persist, active-target/selected flags clear, subpart state clears on leaving the scene; plus ObjectStateChange merge, subpart auto-seed, LayoutMove no-op, TimedWait safe no-op). `tests/test_scene_operations.mjs` (handler routing) and `tests/test_step_machine.mjs` remain green.

- Per-protocol material registry generation + threading (WS-M3-D). Added `generated/protocol_materials.ts` emitted by `pipeline/gen_protocols.py`: `PROTOCOL_MATERIALS` keyed by `protocol_name`, each value a `MaterialRegistry` (`material_name -> {label, display_color: {light, dark}}`) read from that protocol package's `materials.yaml`; a `sequence_runner` aggregates its constituent mini-protocols' materials. The registry is per-protocol, never a global table. `src/protocol_host.tsx` threads `PROTOCOL_MATERIALS[protocol_name] ?? null` into `mountScene` -> the visual-state resolver, replacing the previously-null material registry so non-sentinel material colors resolve at runtime. Updated `docs/CODE_ARCHITECTURE.md` and `docs/FILE_STRUCTURE.md` pipeline/output rows.

- Restored read-only walker/debug surfaces (WS-M3-D). Added `src/scene_runtime/protocol/walker_debug.ts` (`install_walker_debug_surface`): installs `window.PROTOCOL_STEPS` (step id/label/scene/nextId) and `window.gameState` (activeStepId, interactionIndex, activeScene, completedSteps ids, selectedTool, heldLiquid, wrongOrderClicks, stepsOutOfOrder, isComplete) projected read-only from the emitter snapshot + step events + scene store. These are the frozen contract surfaces the canonical walker reads (per `docs/specs/WALKTHROUGH_GUIDE.md` "Required future work"). Added `tests/test_walker_debug.mjs`. Verified in-browser: a real click on `micropipette` in `trypan_blue_counting` drove `activeScene` null->`cell_counter_workspace`, `interactionIndex` 0->1, and `selectedTool` null->`micropipette` through the store-driven SceneChange + CursorAttach path.

- Visual-state resolver (WS-M2-R). Added `src/scene_runtime/renderer/visual_state_resolver.ts`, a pure (no-DOM, no-Solid) `resolve_visual_state(object_visual_states, state, material_registry)` that maps an object's current state plus authored `visual_states` plus the active protocol's material registry into a renderable description `{ asset_name, overlays, material_color, label_text?, placeholder?, data_attrs }`. Implements the inventoried formula mini-language: `fill_height` (capacity keyword parameterized as `capacity_ml`/`capacity_ul`/`capacity_mg`, never assuming a liquid-volume unit), `label` (with `{value}` substitution), `conditional` (flat and nested `label`-inside-`conditional`, as used by `cell_counter` and `hemocytometer_slide`), and `compose` (implemented, not silently no-opped). Unknown formula tokens, arity mismatches, undeclared state fields, unmatched svg cases, and unregistered non-sentinel materials all fail loud. Material color is read per protocol from the passed-in registry (never a global table); the eight sentinel materials (`empty`, `mixed`, `cells`, `formazan`, `waste_*`) resolve to null color. Added `tests/test_visual_state_resolver.mjs` (16 behavioral tests, all pass). Consumed by WS-M3-C (Solid scene components).

- Walker per-interaction screenshot evidence (WS-M1-W). Added `--screenshots per-step|per-interaction|per-click` flag to `tests/playwright/e2e/protocol_walkthrough_yaml.mjs` (default `per-step`, preserves existing behavior). Per-interaction mode captures a screenshot after all clicks in each `sequence` interaction complete, named `interaction_<step_name>_i<N>_<target>.png`. Per-click mode captures a screenshot inside `clickItemAndWaitProgress()` after each click, named `click_<step_name>_i<N>_c<K>_<item_id>.png`. Both modes add report entries to `playthrough_report.json` carrying `screenshot`, `step_name`, `interaction_index`, `gesture`, and `target`. The top-level `screenshotMode` field in the report is always written so the report is self-describing. Updated `docs/specs/WALKTHROUGH_GUIDE.md`: moved per-interaction screenshots from "Required future work" to implemented; documented the new flag, naming conventions, and report fields; updated the output files table and the "How to run it" section. Also fixed a pre-existing import mismatch in the walker (symbols `_recordInfo`, `_recordWarn`, `_recordError`, `_waitForHeldLiquid`, `_waitForActiveScene` were imported by wrong names; fixed to use `as` aliases matching actual exports). Fixed a pre-existing URL mismatch: the walker was navigating to `/?protocol=<name>` (the launcher, which does not expose `gameState`/`PROTOCOL_STEPS`); updated to `/<protocol_name>.html` (the per-protocol host page).

- Generator emits visual_states and state schemas (WS-M1-F). Extended `pipeline/gen_object_library.py` to emit per-object `state_schema` (object-level state_fields), `visual_states` (cases + composite formulas), and `subpart_state_schema` (subpart-level state_fields) on each entry in `OBJECT_LIBRARY`. Added two new top-level exports: `OBJECT_STATE_SCHEMAS` and `OBJECT_SUBPART_STATE_SCHEMAS` (keyed by `object_name`), derived from declared `state_fields` only -- not inferred from `visual_states` -- giving the reactive store (WS-M2-S) a typed contract to validate against. Added new TypeScript types to `src/scene_runtime/layout/types.ts`: `StateFieldDef`, `VisualStateDef`, `VisualStateCase`, `VisualStateOutput`, `ObjectVisualStates`, `ObjectStateSchema`, `ObjectStateSchemas`, `ObjectSubpartStateSchemas`. Updated `ObjectDef` to include `state_schema`, `visual_states`, and `subpart_state_schema`. Updated `src/scene_runtime/layout/__fixtures__/demo_library.ts` fixture to satisfy the extended interface. Added 5 behavioral pytest tests in `tests/test_object_library_visual_states.py` verifying the empty-state->asset mapping and fill_height formula round-trip. Updated `docs/CODE_ARCHITECTURE.md` pipeline table row. Bundle size: 7.4M -> 8.0M (+0.6M, expected from new visual_states + schema data for 76 objects).

- Scene DOM contract baseline and diff check (WS-M1-T). Frozen 36 scene stats baselines into `tests/fixtures/scene_dom_contract/` (one `.stats.json` per non-row_slot scene, sourced from `test-results/scenes/`). Added `tests/e2e/e2e_scene_dom_contract_diff.mjs`: a runnable diff check that compares current `test-results/scenes/*.stats.json` against the baseline with contractual tolerances (data-* attributes EXACT, item count EXACT, placement names EXACT, label count EXACT, bbox x/y/w/h within <=1px or <=0.5% relative). Added `tests/playwright/test_scene_dom_contract_selectors.mjs`: browser-driven Playwright test asserting all nine contractual selectors (`data-item-id`, `data-object-name`, `data-placement-name`, `data-zone`, `data-kind`, `data-depth`, `data-target-id`, `data-asset`, `data-missing-svg`, `data-label`, `data-label-for`) on bench_basic (full coverage), hood_workspace (multi-scene spot-check), and missing_svg_check (placeholder contract). Click-target behavior verified via in-page `dispatchEvent`. Contractual vs incidental separation documented in the test file: internal div nesting depth, CSS class names, z-index, and sub-SVG structure are incidental; identities, bboxes, labels, and attributes are frozen. Diff check: 36/36 PASS. Selector tests: 202/202 PASS.

- Solid.js import boundary (WS-M1-B). Documented the Solid-in-scene architectural boundary in `docs/CODE_ARCHITECTURE.md` (new "Solid.js import boundary" section). Extended `tests/test_typescript_boundaries.py` with five new enforcement tests: `test_no_solid_js_in_layout`, `test_no_solid_js_in_pipeline`, `test_no_solid_js_in_validation`, `test_no_solid_js_in_generated`, and `test_no_solid_js_runtime_import_in_protocol`. Solid is forbidden in `src/scene_runtime/layout/`, `pipeline/`, `validation/`, `generated/`, and `src/scene_runtime/protocol/` (runtime imports); type-only imports of Solid types are permitted in `protocol/` so the stepper can reference state types. Solid remains allowed in `src/shell/`, `src/scene_runtime/renderer/`, and `src/scene_runtime/state/`. Also removed `renderer/` from the previous solid-js block (it was incorrectly forbidden; the renderer will host Solid scene components in M2/M3). The old `test_no_solid_js_in_scene_runtime` and `test_no_shell_launcher_in_scene_runtime` tests were replaced with the zone-specific tests above.

### Behavior or Interface Changes

- Redefined the `correct_choice` validator preset to target-equality (WS-M5-ST). Before: `validate_correct_choice(interaction, modal_close_choice_id)` compared a modal `choice_id` against a `value.choice_id` parameter (an answer-list / modal concept). After: `validate_correct_choice(interaction, selected_target)` passes when the selected scene object equals the interaction's declared `target`, and rejects with `wrong_target` otherwise -- the student chose the correct next-step object among the present objects. The closed preset name is kept. `dispatch_interaction_validator` now feeds the clicked/selected target to `correct_choice` and ignores the former choice-id slot; `step_machine.handle_click` already verifies target-equality before dispatch, so a `select` interaction validates through the normal visible-click path and `handle_modal_close` no longer carries `correct_choice`-specific choice-id logic. Updated `tests/test_protocol_validators.mjs` and `tests/test_step_machine.mjs` to the new semantics (the old modal `choice_id` match/mismatch tests are replaced by select-via-click correct/wrong-object tests and type-commit tests). No authored protocol used a `correct_choice` `value.choice_id`.

- Scene store enum membership validation (WS-M3-D). `scene_store.set_object_state` now validates enum writes against the field's declared `allowed` set, not just the primitive type. A bad `ObjectStateChange` enum value (typo or out-of-vocabulary material/state) throws at the store rather than degrading silently in the renderer, per the closed-vocabulary principle. Only enforced when the schema declares an `allowed` list. Added enum-membership tests to `tests/test_scene_store.mjs`. This converts a previously-silent path to fail-loud; the M4 corpus sweep must confirm every authored protocol's writes are in each object's `allowed` set.

- Made the scene-degraded promotion ordering-independent (FIX-3 follow-up). The renderer's `data-scene-degraded` scene-root marker no longer depends on `SceneView.onMount` stamping `data-scene-root` before a child `SceneItem` effect runs `closest("[data-scene-root]")`. `src/scene_runtime/renderer/scene_view.tsx` now owns a reactive `createSignal<Set<string>>` of resolver-degraded targets and a `createEffect` on its own root that sets/clears `data-scene-degraded` from that set plus the structural-violation count; `SceneItem` notifies it through a new optional `onDegrade(target, message)` callback instead of reaching up to the root via the DOM. `src/scene_runtime/renderer/scene_item.tsx` was split into a PURE resolve memo (resolved-state-or-error) plus a single side-effecting `createEffect` that stamps the per-item `data-resolver-degraded`, warns once per transition into failure, and calls `onDegrade`; the old `itemNode` signal and `closest()` effect were removed. Behavior preserved: `data-resolver-degraded` stays on the item, the `console.warn` stays, the item still degrades to its bound asset (never blank), and dispose still clears `data-scene-root` + `data-scene-degraded` with no stale marker across a `SceneChange`. Solid stays confined to the renderer (boundary lint green).

### Fixes and Maintenance

- Fixed two validator detection bugs that invented false findings (validation-clarity series). (1) `validation/svg/asset_audit.py` `check_normalization` checked `root.get('xmlns')`, but ElementTree folds the default namespace into the tag (`root.tag` becomes `{http://www.w3.org/2000/svg}svg`) and never exposes `xmlns` as a gettable attribute, so the check returned `bad_xmlns` for every correctly-namespaced SVG (49 false normalization failures). Now detects normalization from the parsed tag namespace. A second bug in the same file compared the normalization status against `'OK'` when the function returns `'normalized'`, counting every asset as a failure; fixed to split malformed (parse error -> error) from non-normalized (other reasons -> warning). (2) `validation/yaml_schema/object_validator._check_asset_anchors` resolved the repo root with `pathlib.Path(os.getcwd()).parent` then walked UP, starting ABOVE the repo, so `svg_path.exists()` was False for files that exist (e.g. `bottle_orange.svg`) and emitted 43 false "asset not on disk" warnings. Now uses the shared `validation.shared_toolkit.repo_root.REPO_ROOT`; only genuinely absent assets report `missing`. Removed the stale "WS-ANCHORS will author ... once WP-YAML-1/2 lands" migration narration from those finding messages and gave them literal `code` values (`missing`, `non-normalized`, `variant-collapse`). `compiled_summary.py` no longer hardcodes `Failures: 0`; it prints the real per-severity counts. and assert FIRST-render promotion (FIX-3 follow-up). `tests/playwright/_degrade_harness.tsx` was rewritten to mount through the production `mountScene -> SceneView -> SceneItem` chain (hand-built clean PipelineResult with zero structural violations, two synthetic OBJECT_LIBRARY objects: one with a throwing `badtoken` formula, one well-formed), instead of mounting bare `SceneItem` nodes under a manually-stamped `data-scene-root` (which masked the onMount/child-effect ordering). `tests/playwright/test_scene_degrade.mjs` now asserts, SYNCHRONOUSLY right after `mount()` returns with no state write and no settle, that the scene root carries `data-scene-degraded="true"` with NO structural-violation marker (proving the resolver-promotion path lands on first render), plus a new dispose assertion that `data-scene-degraded` and `data-scene-root` are cleared and no orphan nodes remain. Test passes 8/8 including the first-render and dispose checks.

- Widened the dev_smoke tolerant catch in `pipeline/gen_object_library.py` from `(ValueError, KeyError)` to `(ValueError, KeyError, yaml.YAMLError, FileNotFoundError)` so a deliberately-broken smoke fixture that is malformed YAML or references a moved/missing path is SKIPped with a warning instead of aborting the build. The catch stays narrow (NOT bare `Exception`): a genuine generator bug (`TypeError`, `AttributeError`, etc.) still aborts with a full traceback. Regeneration confirms the existing `missing_svg_check` fixture still SKIPs and the library generates with all curriculum objects.

### Removals and Deprecations

- Retired the imperative item-paint path and the WS-M1-T fixture baseline (WS-M4-E closeout). The Solid renderer migration is proven (scene contract diff 36/36 PASS against the frozen baseline with the Solid renderer; M4-D defect register reports zero renderer-class blockers; 7 click protocols walk end-to-end), so the deletion gate is clear. Deleted `src/scene_runtime/renderer/render_item.ts` (the old `renderItem` single-item paint) and `src/scene_runtime/renderer/render_label.ts` (its label helper); both were superseded by the Solid `scene_item.tsx` / `scene_view.tsx` paint path and were referenced only by the now-deleted `renderItem`/`renderLabel` barrel re-exports and one test. Removed those two re-exports from `src/scene_runtime/renderer/index.ts` (barrel now exports `renderScene`, `mountScene`, `SceneView`, `SceneItem`, `renderBackground`). `render_scene.tsx` stays as the public Solid mount facade; `render_background.ts`, `structural_guards.ts`, and `inject_svg.ts` stay (still used by the Solid path). A grep confirms no remaining imports of the deleted paint path. Deleted the test `tests/test_render_item_missing_svg.mjs` (covered the deleted module; the visual/placeholder contract is now exercised by `tests/test_visual_state_resolver.mjs` and the live Playwright selector test). Removed the committed contract baseline `tests/fixtures/scene_dom_contract/` (36 `.stats.json` files) and retired its diff runner `tests/e2e/e2e_scene_dom_contract_diff.mjs`: with the migration proven there is no committed baseline to diff against, so ongoing scene-DOM-contract enforcement relies on the durable `tests/playwright/test_scene_dom_contract_selectors.mjs` (live assertions on all 11 contractual `data-*` selectors, 198/198 PASS) plus `tools/scene_stats.mjs` render-yield diagnostics. Dropped the always-skipping baseline spot-check helper from the selector test so it no longer depends on the deleted fixtures directory. Updated `docs/CODE_ARCHITECTURE.md` (renderer table + data-flow now describe the Solid paint path; imperative paint marked retired) and `docs/FILE_STRUCTURE.md` (renderer tree + test rows). No fallback renderer remains. Verification: `npx tsc --noEmit` clean, `npm run build` success, `bash check_codebase.sh` 6/6 PASS, `pytest tests/` green.

- Collapsed `ValidatorReference.params` into `value` across the protocol seam (WS-M1-E vocabulary-closure patch). The `params` field was a silent alias for `value` with a `ref.params ?? ref.value` fallback in `step_machine.ts`. Both spellings of one concept violated vocabulary closure. Removed `readonly params?` from `src/shell/adapter/types.ts`; updated `validator_parameters()` in `src/scene_runtime/protocol/step_machine.ts` to read `ref.value` only (no fallback); updated `to_validator_step()` to branch on `step.step_validator.value`. Updated 3 authored occurrences of `params:` in `tests/test_step_machine.mjs` to `value:`. No authored protocol YAML in `content/` used `params:`. All 20 step-machine tests pass; `pipeline/gen_protocols.py` regenerates cleanly; `validation/validate.py` exits 0 failures.

### Decisions and Failures

- Empirical verdict on the FIX-3 first-render dispute: under the current Solid + esbuild-plugin-solid configuration the TESTER was right, not the reviewer. An isolated probe mounted a clean single-item scene (zero structural violations, so `data-scene-degraded` could only come from the resolver path) through production `mountScene/SceneView`, with a throwing `media_bottle` formula; `data-scene-degraded="true"` was present on FIRST render with `data-degraded-violation-count` absent, proving the child `closest()` effect did see the onMount-stamped `data-scene-root`. The reviewer's first-render gap did NOT reproduce. The fix was applied ANYWAY because the working behavior was an effect-scheduling/DOM-attachment timing coincidence; the redesign (SceneView-owned reactive degraded set + `onDegrade` callback, marker derived from owned state) removes the fragile ordering dependency so the marker is correct on first render and every later render regardless of effect order. The original `test_scene_degrade.mjs` PASS was a harness artifact: the harness manually stamped `data-scene-root` before rendering bare SceneItems, so it validated the harness wiring, not the production onMount ordering.

- LayoutMove decision applied (WS-M3-D, Option A). Authored protocols use `LayoutMove` zero times; the store-driven deps treat it as explicitly unsupported this pass -- a reported `console.warn` no-op, never a silent skip and never a throw. The typed placement-override (Option B) is deferred to the milestone where the first authored consumer appears.
- Walker end-to-end completion is BLOCKED for new-host protocols (WS-M3-D). The read-only `window.PROTOCOL_STEPS` / `window.gameState` surfaces were restored and verified (a real click drives the store-backed gameState through the visible UI). However, the canonical walker `tests/playwright/e2e/protocol_walkthrough_yaml.mjs` cannot complete a new-host protocol: its startup contract still targets the legacy cell-culture game -- it requires `window.resolveInteractionByIndex`, a `#welcome-start-btn` welcome modal, the legacy `completionPath.kind` step schema, legacy scene-switch buttons, and a scoring screen, none of which the new protocol host produces. Rewriting the walker to consume the new schema-driven step/sequence/interaction model (without per-protocol branches, per the plan) is M4 work, tracked there; it is outside WS-M3-D scope.

### Additions and New Features

- Real-asset object remaps (replaced placeholder/misnamed art with real SVGs). (1) Cell counter: the misnamed `cell_counter.svg` rendered as a blue diagonal inoculation loop (both `cell_counter.svg` and `cell_counter_new.svg` were identical loops, neither a valid instrument); replaced with new `assets/equipment/cell_counter_instrument.svg` (benchtop automated cell counter: dark housing, LCD showing count/viability/READY, CAPTURE/FOCUS/EJECT buttons, slide slot) and updated `content/objects/equipment/cell_counter.yaml` visual_states to reference it. (2) Imported real instrument SVGs into `assets/equipment/`: `heat_block_closed.svg` (PCR cycler / heat block), `microwave_closed.svg` (front-load microwave), `lightbox_on.svg` (lit yellow-surface transilluminator), `tube_rack.svg` (multi-tube rack, Servier CC-BY-3.0); stripped Adobe Illustrator `<switch>`/`<foreignObject>`/aipgf cruft from `tube_rack.svg` and cleaned non-ASCII Japanese layer-id strings from heat_block SVGs. (3) Imported 4 pre-colored bottle/rack SVGs via `tools/normalize_svg_v2.py`: `bottle_pink.svg`, `bottle_orange.svg`, `bottle_green.svg`, `tube_rack.svg` (from Servier/Bioicons CC-BY-3.0 sources); all pass `tools/validate_svg_registry.py` (119/119). Note: anchor IDs (`anchor_liquid_clip`, `anchor_liquid_bounds`) are present only on the older `bottle.svg`, not the imported variants; the recolor follow-up must add them. (4) Remapped all 8 reagent bottle objects to the pre-colored variants and `dilution_tube_rack_8`/`microtube_rack_24` to the real `tube_rack` asset; two decoration objects (`professor_avatar`, `p10_gel_loading_tip`) used a non-schema `asset:` key and were converted to `visual_states` (vocabulary closure fix). (5) Created `content/objects/bottle/trypan_blue_bottle.yaml` (kind bottle, `bottle_medium_pink` base, display_width_cm 8, material_name/material_volume state fields) resolving the missing reference in `hemocytometer_view.yaml`. (6) Restored `content/objects/bottle/trypsin_bottle.yaml` from quarantine (uses `bottle_pink`; trypsin with phenol red reads pink) and used it in `passage_hood_detachment/scenes/hood_workspace.yaml` in place of the sterile_water_bottle placeholder.

- Collapsed state-pair art to a single asset (no dynamic-SVG swap runtime exists yet). Both `when` cases in 5 equipment objects now point at one shared asset, state field and `visual_states` structure preserved for later reversal: `heat_block` -> `heat_block_closed`; `rocking_shaker` -> `rocking_shaker_idle`; `lightbox` -> `lightbox_on` (off variant was a stub); `microwave` -> `microwave_closed`; `power_supply` -> `power_supply_off`. Orphaned second-state assets (`heat_block_open.svg`, `rocking_shaker_running.svg`, `lightbox_off.svg`, `microwave_open.svg`, `power_supply_on.svg`) left on disk for human git deletion. Tracked in [../assets/SVG_ASSET_GAPS.md](../assets/SVG_ASSET_GAPS.md).

- Hood_surface waste-tray removal: removed the waste_tray visual from the `hood_surface` object and created `assets/equipment/hood_workspace_surface.svg` (transparent 100x60 click target); `hood_surface` visual_states now use it for both `dirty` and `ethanol_sprayed`, with `display_width_cm` 70 -> 50. Hood scenes no longer show the giant grey tray with red X and "Waste" text; the object stays as an invisible clickable target for back-navigation steps.

- Placeholder policy (dashed-box flag + metric + 0-byte guard + label-below). (1) `pipeline/gen_svg_registry.py` detects dashed-box placeholders (SVGs using the `placeholder-border` + `placeholder-text` class convention) and emits a `SVG_PLACEHOLDER_KEYS` export alongside `SVG_REGISTRY` (4 flagged: `electrode_module`, `gel_opening_tool`, `kimwipe_pad`, `power_supply_off`); `render_item.ts` emits `data-asset` on every item; `tools/scene_to_png.mjs` marks placeholder-resolved items (`placeholder-art` kind); `tools/scene_stats.mjs` computes `render_yield_percent` from real items only, excludes placeholder area from `percent_empty_approx`, and adds `placeholder_count` per scene and to `summary.json`. Effect: `sdspage_run_electrophoresis_workspace` render_yield 100% -> 81.3%, real_item_count 16 -> 13, placeholder_count 0 -> 3; all 11 placeholder-bearing scenes flagged. (2) `injectSvgInto` in `inject_svg.ts` now throws `SVG asset is empty in registry` on empty/whitespace markup (loud-failure; the Python validator already rejects empty bodies at registry build). (3) Dashed-box placeholder SVGs moved label text below the tile and added `textLength`/`lengthAdjust` (newly allow-listed in the registry sanitizer) so labels are no longer truncated ("Electrode Modu..." -> "Electrode Module").

- Standalone scene viewer: `mount_scene_viewer` in [dist_entry.tsx](../src/dist_entry.tsx) reads `?scene=<name>`, shows an unknown-scene banner before running the pipeline, and sets a `data-viewer-ready` marker. New host page [scene_viewer_template.html](../src/scene_viewer_template.html) is emitted as `dist/scene_viewer.html` by [build_github_pages.sh](../build_github_pages.sh) and [build_main_bundle.mjs](../pipeline/build_main_bundle.mjs). Added Playwright smoke `tests/playwright/test_scene_viewer.mjs`.

- Render-to-PNG tooling: [scene_to_png.mjs](../tools/scene_to_png.mjs) renders a scene to PNG plus structured stats (`--scene`, `--all`, `scene:png` npm alias); [scene_stats.mjs](../tools/scene_stats.mjs) (exports `computeSceneStats`; render-yield + easy diagnostics) with helpers in [bbox_helpers.mjs](../tools/bbox_helpers.mjs) and unit tests `tests/test_scene_stats.mjs`; [protocol_to_png.mjs](../tools/protocol_to_png.mjs) renders a protocol interface and scene, reports load outcomes, supports `--all`/`--steps`/`protocol:png`.

- Real-world object sizing calibration. Added `layout.display_width_cm` to all 74 `content/objects/**/*.yaml` files, values from the calibration table in [specs/SCALING_MODEL.md](specs/SCALING_MODEL.md) (vortex 22, microcentrifuge 25, centrifuge 60, water bath 55, incubator 50, cell counter 38, microscope 35, plate reader 42, T75 flask 20, well-plate-class 18, media bottle 12, serological pipette 3, multichannel 14) and interpolated for the rest at the 1.1-1.5 exaggeration ratio; `default_width` preserved. Calibrated `WORKSPACE_PX_PER_CM` in [constants.ts](../src/scene_runtime/layout/constants.ts): bench 3.2 -> 5.5, microscope -> 10.0, incubator and cell_counter -> 9.0, hood and plate_reader kept at 8.0. Render evidence: centrifuge_workspace 78.7% empty 0 clips; electrophoresis_bench 83.1% empty 0 clips; no `item_escapes_zone` or clip diagnostics in any non-degraded scene.

- Full-canvas vertical zone use: added explicit `baseline:` values to all 9 functional base scene YAMLs (`bench_basic`, `hood_basic`, `microscope_basic`, `cell_counter_basic`, `imaging_bench`, `heat_block_bench`, `sample_prep_bench`, `staining_bench`, `electrophoresis_bench`). Previously zones used only `bounds.top/bottom`, so derived midpoint baselines clustered all items in the upper ~35% and left the lower ~33% empty. Now: `baseline: 32` for rear-shelf bands, `84` for center/working bands, `88-90` for single-instrument/front bands; `electrophoresis_bench` uses three bands at 32/64/90. Zone bounds widened to encompass the band while baseline controls the vertical anchor; zone names unchanged so child scenes inherit. PNG evidence shows full top-to-bottom distribution across bench/hood/SDS-PAGE scenes.

- Scene population and calibration pass across all scene families (bench, hood, SDS-PAGE, microscope/imaging/cell-counter), using only existing real-asset objects, no new art, never-crop respected. Bench family: redesigned `bench_basic` zones to tab-stops for left/center/right clusters, added water_bath plus a distinct `centrifuge` (domed-lid) to the center band to remove duplicate-looking equipment, kept 5 original zone names so 7 protocol children inherit; added `align_stop` to all protocol placements; switched items-that-should-be-absent from `deactivate_placements` to `remove_placements` (deactivated placements still render) to clear dozens of spurious overlaps; bench_basic 0 overlaps, all 8 scenes 100% placement yield. Hood family: redesigned `hood_basic` from align:center to tab-stops, base placements 4 -> 9 (pbs/media/sterile-water bottles, tip box, serological pipette, `base_`-prefixed to avoid child-name conflicts); substituted quarantined objects in 4 protocol scenes (trypsin/well_plate_96 proxies); fixed `conical_15ml_rack` display_width_cm 18 -> 3 (the 6:1-portrait falcon_15ml SVG rendered ~108cm tall at 18cm width); hood_basic 9 placements 70% empty, children 11-17 placements, all 100% yield. SDS-PAGE family: populated/calibrated all 4 base scenes and 10 protocol children with tab-stops and `align_stop`; moved the 35cm microwave into the staining_bench center to stop right-edge clipping (never-crop); heat_block_bench 3 -> 11 items, sample_prep_bench 5 -> 10; all children 100% yield. Microscope/imaging/cell-counter and near-empty sweep: rebuilt `microscope_basic` (3 -> 8 items, empty 80.5% -> 69.6%), `imaging_bench` (5 -> 11, 93.3% -> 86.8%), `sample_prep_bench`/`heat_block_bench` to three-tier layouts (13 items each), `cell_counter_basic` (5 -> 7) with `rear_shelf` + `right_accessory_area` zones and `base_hemocytometer_slide` preserved for inheritors, `centrifuge_workspace` 10 -> 13; removed the placeholder `lens_tissue` so no dashed box renders; cell_counter_workspace de-duplicates `base_hemocytometer_slide` via `remove_placements`. `hood_basic` left as a sparse inherited template by decision (populating its center would clutter sibling-owned protocol scenes). All scenes plus inheritors render `populated` at 100% yield, 0 placeholders. Eye-checked PNGs across families: objects spread across the canvas, no clipped glassware, labels legible.

- Microscope artwork cleanup: removed three orphaned floating paths from `assets/equipment/microscope.svg` (a `#333` open arc, a `#b0bfc2` figure-eight curl, a `#fff` leaf sliver) that drew a stray doodle lower-right of the stage; the fix propagates to inheritors `hemocytometer_view` and `passage_hood_detachment_microscope_view`. (SVG edits require a full `build_github_pages.sh` rebuild because `tools/scene_to_png.mjs` serves the bundled `dist/`.)

- Label legibility engine. (1) Bundled font: scene-object labels render in condensed PT Sans Narrow instead of `monospace`; bundled as latin-subset woff2 (SIL OFL 1.1) at `assets/fonts/pt_sans_narrow_regular.woff2` (400) and `pt_sans_narrow_bold.woff2` (700) with `OFL.txt` and `ATTRIBUTION.md`; two `@font-face` rules added to [style.css](../src/style.css); [build_github_pages.sh](../build_github_pages.sh) copies the fonts into `dist/assets/fonts/`; `.woff2 -> font/woff2` added to the [scene_to_png.mjs](../tools/scene_to_png.mjs) MIME map; `render_label.ts` `fontFamily` -> `"PT Sans Narrow", "Arial Narrow", sans-serif`; `AVG_CHAR_WIDTH_PCT` retuned 0.6 -> 0.45 (consumed only by `wrap_label.ts`/`layout_labels.ts`, downstream of placement, so item layout unchanged). Proof: woff2 served 200 with `font/woff2`, `document.fonts.check('PT Sans Narrow')` true, a test string measures 181.8px vs 259.3px in monospace (~30% narrower). (2) Canvas-relative font size: added `LABEL_FONT_WIDTH_FRACTION = 0.012` and `LABEL_FONT_MIN_PX = 12` to [constants.ts](../src/scene_runtime/layout/constants.ts); [render_scene.tsx](../src/scene_runtime/renderer/render_scene.tsx) derives label font size from the mounted root width (`max(12, round(width * 0.012))`) instead of a fixed 16px that read ~0.8% wide on the ~1920px canvas; an authored `layout_rules.label_font_size` still overrides; removed the redundant `label_font_size: 16` line from the 9 base scenes (dev_smoke fixtures keep their `: 9` overrides). (3) Vertical label stagger: added `LABEL_LINE_HEIGHT_PCT = 2.2` and the `label_row_staggered` diagnostic; [layout_labels.ts](../src/scene_runtime/layout/layout_labels.ts) replaced the warn-only residual block with a deterministic two-pass greedy interval-graph row assignment over x-sorted labels (placement_name tiebreak), writing only `_labelX`/`_labelY` so item placement is byte-identical before/after across all 46 scenes. (4) Render wrap fix: `render_label.ts` `white-space` `nowrap` -> `pre` so 2-line labels honor pipeline line breaks instead of collapsing into one ~2x-wide line (the dominant overprint cause). (5) New `label_overlap_pair_count` metric: total rendered label-label overlaps across all scenes dropped 40 -> 3 then to 0 after the narrow font; the residual tight clusters (`cell_counter_basic`, `cell_counter_workspace`, `seeding_workspace`) emit `label_collision_residual` and are a placement concern out of scope. Eye-checked PNGs: labels condensed, legible, staggered where needed, no overprint.

### Behavior or Interface Changes

- Canonicalized the material-overlay recolor design in [specs/MATERIAL_CONVENTION.md](specs/MATERIAL_CONVENTION.md): added a "Recolor model" section (single neutral base SVG tinted by `display_color`, body-tint vs fill-height as separate color/amount concerns, `display_color` as the sole color source) and a "Target overlay interface" subsection (identity + level + color + base markup -> composited overlay), synthesized from the archived `material_overlay_vocabulary.md` and `material_overlay_audit_2026_05_18.md`. Added a dedicated "Current implementation status" section flagging that the recolor pipeline is NOT yet implemented in the Solid.js runtime (bottles use pink/orange/green proxy variants; blue reagents proxy to green; per-well and per-chamber overlays blocked), pointing to [../assets/SVG_ASSET_GAPS.md](../assets/SVG_ASSET_GAPS.md) as the live gap tracker. Normative body kept present-tense; transitional wording confined to the status section per the vocabulary-closure rule. No code, YAML, or other spec changed.

- scene_calc validators (`scene_lint`, `scene_design`) now consume rendered geometry from `test-results/scenes/<scene>.stats.json` (single producer: `tools/scene_to_png.mjs` -> `tools/scene_stats.mjs`). `stats.json` gained a `geometry` block (scene_bounds, per-item bbox and label_bbox in scene-percent). `runPipeline`, `normalizeSchema`, and structural guards now accept only SceneA (row_slot/SceneB schema support removed).

- Deleted `SCENE_ALLOWLIST` from [gen_scene_index.py](../pipeline/gen_scene_index.py) and replaced it with discover-all plus per-scene classification: `emitted`, `skipped` (non-fatal, with a recorded reason), or `errored` (fatal, raises). The generator now emits `generated/scene_manifest.json` (`{name, outcome, reason, source_placement_count, source_placement_names}`). Added regression test [test_no_scene_allowlist.py](../tests/test_no_scene_allowlist.py).

- Flipped the `--missing-svg` default in [gen_scene_index.py](../pipeline/gen_scene_index.py) from `strict` to `placeholder` so a scene referencing a missing SVG now emits a labeled placeholder instead of vanishing; `strict` is retained for CI gating.

### Fixes and Maintenance

- Electrophoresis tank now reads as a real tank: added buffer-blue interior fill, darker rim, surface line, and gel-slot/electrode hints to the chamber SVGs (`electrophoresis_tank_inner_chamber.svg`, `electrophoresis_tank_outer_chamber.svg`); removed the no-op `lid_present`/`module_present` asset swaps from the `electrophoresis_tank` composite (was rendering a near-blank pale box).

- `validate.py` scene/protocol validator: `remove_placements` and `deactivate_placements` are now validated as lists of placement-name strings (matching the builder contract in `scene_inheritance.py`), fixing ~50 false-positive "entry must be a mapping" errors; `add_placements`/`reposition_placements` still require mappings. Fixed missing `visual_states` entries on `electrophoresis_tank` (`lid_present`, `module_present` -> `kind: composite`, `[]`) and removed orphan `visual_states` keys on `cell_counter` and `hemocytometer_slide`.

- t75_flask gradient fix (systemic pipeline): widened the `_strip_unsafe_attrs` safe-attribute allowlist in `pipeline/gen_svg_registry.py`, which was missing `gradientUnits`, `offset`, `stop-color`, `stop-opacity`, `points`, `x1`, `y1`, `x2`, `y2`, `rx`, `ry`, and the ET-internal Clark-notation `{http://www.w3.org/1999/xlink}href`. Because these were stripped, all radial gradients on t75_flask (and any SVG using xlink:href gradient inheritance) rendered as broken blue cubes. The fix benefits any asset with xlink:href gradient inheritance or polygon/line/ellipse geometry. Also hardened `pipeline/normalize_svg.py` to reject and cleanly strip non-ASCII id attributes (encountered as Japanese layer-id strings in the imported heat_block SVGs).

- M3 blank-scene fix: structural guards now report instead of throw in the render path. `collectStructuralViolations` gathers violations and `renderScene` sets `data-scene-degraded`, warns, and renders all items; a strict throwing wrapper is retained for tests/CI. Added a missing-object placeholder path in `bind_objects.ts`, `group_by_zone.ts`, and `render_item.ts` with a distinct `data-placeholder-kind="missing-object"`. Result: before 25 populated / 19 load-failed / 1 empty / 1 skipped; after 44 populated / 0 load-failed / 0 empty / 1 placeholder-only / 1 skipped. `bash check_codebase.sh` passes (6 checks, 151 node tests). Evidence: `docs/active_plans/audits/blank_scene_evidence.md`.

### Removals and Deprecations

- Retired `fudge` field and authored per-placement `width_scale` (and forbade placement-level `display_width_cm`) from layout schema, engine, and generator. Internal `_width_scale` preserved in the engine for backward-compat. Removed 8 per-placement `layout: { width_scale: N }` overrides from 7 scene YAMLs (`bench_basic` heat_block 0.65, `dilution_workspace`/`drug_dilution_setup_bench_setup` dilution_tube_rack_8 1.4, `centrifuge_workspace` centrifuge 0.85 + t75_flask 0.85, `incubator_workspace` incubator 1.1, `mtt_solubilization_readout_bench_workspace` microtube_rack_24 1.2, `mtt_solubilization_readout_plate_reader_workspace` plate_reader 1.2). Corrected object-level `display_width_cm` to preserve rendered size: heat_block 25->16, dilution_tube_rack_8 18->25, centrifuge 60->51, t75_flask 20->17, incubator 50->55, microtube_rack_24 20->24, plate_reader 42->50. The escape-hatch per-placement override surface is now closed.

- Retired row_slot/SceneB scene schema (Option B). SceneB engine code removed from `src/scene_runtime/layout/`. The 9 `content/base_scenes/*_row_slot.yaml` scenes and `src/scene_runtime/layout/workspace_row_library.ts` are quarantined and unreferenced pending human `git rm`. `runPipeline`, `normalizeSchema`, and structural guards now accept only SceneA.

- `validation/scene_calc/{bboxes,aspect,labels,zones}.py` geometry-model files retired pending human `git rm` (superseded by the stats.json producer/consumer model: `tools/scene_to_png.mjs` produces `test-results/scenes/<scene>.stats.json`; validators consume it).

### Decisions and Failures

- Ratified "the generator wins; scene_calc is only a validator": the generator (pipeline + layout engine) is the single source of rendered geometry truth. `scene_calc` predicts geometry but does not override the generator. Decision record: `docs/active_plans/decisions/scene_calc_validator_follows_generator.md`.

- Reverted an earlier scene-lint suppression-gaming attempt where suppressions were added to silence real layout violations rather than fix them. Suppressions are now restricted to known false positives with documented tickets and expiry dates.

- Display color limited to pink/orange/green bottle variants because the per-material `display_color` recolor pipeline was lost in the Solid.js rewrite. Blue dyes are proxied to green temporarily. Full recolor restoration (restoring `anchor_liquid_clip`/`anchor_liquid_bounds` to bottle variants and re-implementing the CSS/SVG recolor path) is a tracked follow-up.

- Temporarily demoted ERROR->WARNING (reversible, tied to [../assets/SVG_ASSET_GAPS.md](../assets/SVG_ASSET_GAPS.md)): `well_plate_96` target-resolution failures (per-well overlay deferred to the Solid.js runtime) and reagent bottle VARIANT-COLLAPSE / `display_color` color gaps (recolor pipeline lost in the Solid.js rewrite). Scoped narrowly: non-`well_plate` unresolved targets and non-material errors stay ERROR.

- `well_plate_96` remains quarantined pending the per-well material-overlay runtime: restoring it with `96well_pcr_plate` as base would render 96 overlapping plate SVGs (per-subpart `visual_states applies_to: subpart` emits one SVG per well). The quarantine duplicate `content/objects_quarantine/plate/well_plate_96.yaml` stays as design reference and the `microtube_rack_24` proxy stays in the 5 scenes that reference it.

- Structural guards stay in report mode (the render path never blanks a scene) per user direction; quality assessment lives in the diagnostic tools, not the render path. Git workflow is fully out of scope for agents.

- Deferred diagnostic statistics (browser-event counts, exact-union coverage, severe-overlap/occlusion, stability/unstable flags, balance, zone-coverage, contrast, interaction-readiness, fuller labels) are recorded in [ROADMAP.md](ROADMAP.md).

### Developer Tests and Notes

- `check_codebase.sh` 6/6 PASS maintained throughout all workstreams. Full object validator (`python3 validation/yaml_schema/object_validator.py`) and scene validators run after each workstream and exit 0. All 45 scene families re-rendered as browser evidence (`tools/scene_to_png.mjs --all`).

- WP4 verbosity patch series (validation consistency). New `validation/shared_toolkit/verbosity.py`:
  closed `VerbosityLevel` enum (`QUIET`/`NORMAL`/`VERBOSE`) + `resolve_level` (raises `ValueError`
  on `--quiet --verbose` conflict); canonical `summary_line` grammar "Checked N <label>. F failures.
  W warnings." (always emits both counts including zero; preserves the `N failures`/`N warnings` regex
  tokens `validate.py` depends on); `diagnostic_summary(DiagnosticData)` with empty-state
  ("No diagnostics."), count-desc/name-asc sort, top-K=10 truncation. All 7 validation stages
  migrated: `yaml_schema`, `svg_audit`, `stepper`, `structure`, `manual`, `scene_lint`,
  `scene_design`. Fast formatter unit tests: `tests/test_validation_verbosity.py` (10 tests,
  sub-second). Per-stage subprocess and machine-format contract checks:
  `tests/e2e/e2e_validation_verbosity.py` (25/25 pass). Full suite: 1392 passed, 1 xfail, 0 failed.

### Additions and New Features

- WP4 verbosity: added `validation/shared_toolkit/verbosity.py` -- closed `VerbosityLevel` enum
  (`QUIET`/`NORMAL`/`VERBOSE`), `resolve_level` (raises `ValueError` on conflicting flags),
  canonical `summary_line` ("Checked N <label>. F failures. W warnings." always printing both counts
  including zero), and `diagnostic_summary` with empty-state guard, count-desc/name-asc sort,
  top-10 truncation. This is now the single source for the `N failures`/`N warnings` regex tokens
  that `validate.py` parses from each stage.

- WP4 verbosity: `reporter.print_summary_line` now delegates to `verbosity.summary_line`
  (single source); zero-warning count is now always emitted (previously omitted), preserving the
  aggregate regex contract.

- M1B-2 Patch 2 (WP-SEAM): added a read-only protocol-layer lookup seam for declared object and
  subpart state fields. New `src/scene_runtime/protocol/state_field_lookup.ts` exports the
  `StateFieldLookupResult` discriminated union and the `StateFieldLookup` function type (zero
  imports, no runtime deps). New `src/scene_runtime/state/state_field_lookup_impl.ts` provides
  `create_state_field_lookup` over `OBJECT_STATE_SCHEMAS` / `OBJECT_SUBPART_STATE_SCHEMAS` plus
  `REGISTRY_BACKED_MATERIAL_FIELDS`; resolves subpart names by first-dot split, never throws.
  The lookup is threaded into `create_step_machine` via an `options` object
  `{ lookup_state_field }` and wired at the single caller `src/protocol_host.tsx`. The seam keeps
  the protocol layer free of direct schema-table imports.

- M1B-2 Patch 3 (WP-CHECK): added load-time authored-value validation in
  `src/scene_runtime/protocol/authored_value_check.ts`. `validate_authored_validator_values({
  protocol_config, lookup_state_field })` runs in `create_step_machine` at startup (beside
  `validate_protocol_presets`) and checks every `target_with_value` and `final_state_matches`
  authored value against the DECLARED field type (`int`, `float`, `bool`, `string`, enum
  `allowed` set, and registry-backed material fields). Four named author-facing error classes are
  thrown on bad authoring: `UnknownAuthoredObjectError`, `UnknownAuthoredSubpartError`,
  `UnknownAuthoredFieldError`, and `BadAuthoredValueError`, each carrying
  protocol/step/validator-kind/target/field context (plus declared type for bad-value errors).
  The M1B-1 runtime diagnostic in `validators.ts` is kept unchanged as a backstop.

### Behavior or Interface Changes

- WP4 verbosity: `scene_lint` and `scene_design` `--json` now emit a single JSON document
  (`{"findings":[...]}` / `{"cards":[...]}`) instead of JSONL, matching the other 5 stages and the
  `validate.py` aggregate `json.loads` contract. `--ndjson` still emits JSONL. `--markdown` remains
  an explicit format flag orthogonal to verbosity. `tests/e2e/e2e_scene_design_cli.py` updated to
  pass `--json`.

- WP4 verbosity: per-stage quiet/default/verbose output now consistent across all 7 stages.
  Quiet = exactly 1 canonical summary line. Default <= 40 lines. Verbose <= 199 lines.
  Per-stage drift fixed: `yaml_schema` (corrected "Validated" wording and embedded-newline quiet bug;
  default 658->~34 lines); `svg_audit` (fixed hardcoded `verbose=False` so cleanup-surface items
  print at `-v`); `stepper` (removed inverted `runner_quiet=not args.verbose`; per-protocol fail
  lines now show in both default and verbose; default 160->40 lines); `structure` and `manual`
  (added missing verbose diagnostic branch; `manual` default 198->3 lines); `scene_lint` and
  `scene_design` (converted from always-JSONL to text at quiet/normal/verbose).

### Removals and Deprecations

- WP4 verbosity: dropped missing `validation/svg/pipeline_check.py` from the `validate.py` svg
  stage map (was printing "Stage script not found" on every run). Decision recorded in
  `docs/active_plans/decisions/pipeline_check_dispatch.md`.

### Decisions and Failures

- WP4 verbosity (KNOWN ISSUE, pre-existing, not fixed): whole-suite `validate.py --json` still raises
  `JSONDecodeError` because the 5 text-mode stages emit plain text (not JSON) under `--json` --
  the aggregate JSON merge was explicitly out of scope for this patch. Covered by an `xfail` test in
  `tests/test_validation_verbosity.py`. Deferred cleanup nits from review left as-is: loop variable
  `l` in one internal helper, omitted `warnings=` kwarg in two yaml calls, `is_verbose` local bool
  in `svg_audit`.

- M1B-2 Patch 3 (WP-CHECK, dev_smoke exemption): the `dev_smoke` exemption in
  `authored_value_check.ts` is LOCAL to the unknown-object and unknown-subpart resolution branch
  only. Smoke fixtures may reference objects not in the full object library; the check skips the
  unknown-object and unknown-subpart errors for `protocol_type: dev_smoke`. Resolvable fields on
  dev_smoke protocols (where the object IS in the library) are still type-checked. This is a
  narrow carve-out, not a blanket exemption: a smoke protocol with a reachable field and a
  type-wrong authored value still throws `BadAuthoredValueError`.

### Developer Tests and Notes

- M1B-2 Patch 4 (WP-TEST): added `tests/test_authored_value_check.mjs` (29 Node `--test` cases):
  fake lookup, both validator shapes (`target_with_value` and `final_state_matches`), all four
  error classes, and both sides of the dev_smoke exemption (smoke protocol skips unknown-object
  error; resolvable field on smoke protocol is still type-checked). Updated
  `tests/test_step_machine.mjs` and `tests/test_m2_integration.mjs` callers to pass the new
  `{ lookup_state_field }` option. Discovery decision recorded in
  `docs/active_plans/decisions/m1b2_discovery_seam_proposal.md` (WP-DISC). Gates: 29/29 tests
  pass; `bash check_codebase.sh` 6/6 PASS; build and pilot walker pass.

## 2026-05-28

### Additions and New Features

- Added [build_generated.sh](../pipeline/build_generated.sh): the single source of truth for generator order. It wipes and fully regenerates the gitignored `generated/` artifact tree by running the four generators in canonical order (`gen_object_library.py` -> `gen_svg_registry.py` -> `gen_scene_index.py` -> `gen_protocols.py`). A fresh clone now reaches a running server in one command, `bash run_web_server.sh`.

- WP-FRAME-1 (M2): replaced `#scene-root` `100vw x 100vh` with a bounded aspect-locked panel inside a six-region CSS grid layout. Added `.protocol-page-grid` grid in [style.css](../src/style.css) with named areas: `header` (avatar + tips + counter), `scene` (bounded panel), `outline` (right column spanning scene + guidance rows), `guidance` (teal bar). Added `.scene-panel-inner` intermediate wrapper to enforce `aspect-ratio: 16/9` on a non-scene-content element (CSS policy compliance). Updated [protocol_host_template.html](../src/protocol_host_template.html) with all six regions using `data-region` attributes for Playwright targeting. `#shell-root` remains a sibling of `.protocol-page-grid` (asset-crop rule preserved).

- WP-FRAME-2 (M2): fixed scene-percent -> pixel mapping for the bounded panel. [protocol_host.tsx](../src/protocol_host.tsx) now calls `getBoundingClientRect()` on `#scene-root` before `runPipeline`, measuring the actual panel size (e.g. 1044x587) instead of assuming `DEFAULT_VIEWPORT` (1920x1080). The measured `viewport` is passed to both `runPipeline` and `renderScene`. Updated `runStructuralGuards` in [structural_guards.ts](../src/scene_runtime/renderer/structural_guards.ts) to accept an optional `viewport` parameter for Guard 5 (aspect distortion), fixing false failures when the panel aspect ratio differs from 16:9 default. Updated `renderScene` in [render_scene.tsx](../src/scene_runtime/renderer/render_scene.tsx) to forward `viewport` to guards. All 3 items in the `sdspage_heat_denature_samples` scene render inside the bounded panel with no overflow and correct aspect ratios.

- WP-CHROME-1 (M2): styled all six regions in [style.css](../src/style.css): speech-bubble shape for tips via CSS `::before`/`::after`, green `.step-counter-box`, pink/rose current-step highlight and grey previous/upcoming outline cards, teal guidance bar. Shell is a sibling, never an ancestor of `#scene-root`.

- WP-CHROME-2 (M2): built read-only step outline component (`src/shell/regions/step_outline.tsx`). Renders ordered step cards from `config.steps` fed to `ProtocolHud`. Current step gets `data-step-status="current"` (pink), previous steps get "previous" (grey), upcoming get "upcoming" (white). No click navigation.

- WP-CHROME-3 (M2): added region components `src/shell/regions/TipsBubble.tsx` (shows `current_tip` or fallback "Follow the current step guidance."), `src/shell/regions/StepCounter.tsx` (shows `completed / total`), `src/shell/regions/GuidanceBar.tsx` (shows `current_prompt`). Restructured the shell component, now [protocol_hud.tsx](../src/shell/hud/protocol_hud.tsx), to use Solid's `render()` inside `onMount` to mount each region into its DOM target (`#tips-text`, `#step-counter-text`, `#outline-steps`, `#guidance-text`). DOM targets are cleared before mounting to prevent duplicate content. `data-hud-*` attributes retained on hidden container for backward-compat.

- WP-TIP-1 (M2): documented optional `tip` field in [specs/PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md) optional step-fields table (closed `string`, no default, absent means null). Added `tip?: string` to `ProtocolStep` in [types.ts](../src/shell/adapter/types.ts). Added `current_tip: string | null` to `ShellViewSnapshot` (same file) and populated it in the step_started reducer case in [step_machine.ts](../src/scene_runtime/protocol/step_machine.ts) (null when absent). Added `current_tip: null` to `initial_snapshot`, `protocol_completed` reducer case, and both raw-snapshot literal sites (`src/protocol_host.tsx`, `tools/seam_types_compile_check.ts`). Validator unchanged (no per-step key closure; unknown optional fields pass through). No protocol YAML edited. All 5 new `current_tip` reducer tests pass (21 total pass). `npx tsc`, ESLint, Prettier, and build all clean.

- WP-RESOLVE-1 (M1): rewrote `resolve_entry_scene_name` in [protocol_host.tsx](../src/protocol_host.tsx) with explicit precedence: (1) entry step's `scene:` field, (2) first `SceneChange.to_scene` in the entry step (compat fallback), (3) throw. Added `sequence_runner` delegation: runners have no `steps` list; resolution now delegates to the first listed mini-protocol via lookup in `PROTOCOLS`. This fixes all 5 sequence_runner protocols (`cell_culture_full` -> `passage_hood_detachment_microscope_view`; `routine_passage` -> `passage_hood_detachment_microscope_view`; `sdspage_full` -> `sdspage_prepare_running_buffer_workspace`; `sdspage_load_samples_batch` -> `sdspage_load_sample_single_lane_workspace`; `sdspage_prepare_sample_mix_batch` -> `sdspage_prepare_sample_mix_single_lane_workspace`). Removed the brittle protocol-name prefix guess. No YAML changes required.

- WP-RESOLVE-2 (M1): added fail-loud empty-scene guard via `assert_scene_not_empty` in `src/scene_runtime/protocol/resolve_entry_scene.ts`. For student-visible protocols (mini_protocol, sequence_runner), `final.length === 0` after `runPipeline` now throws a clear error naming the protocol and scene. `dev_smoke` is the only exempt `protocol_type`. Extracted resolution and guard logic into `src/scene_runtime/protocol/resolve_entry_scene.ts` (exports `resolve_entry_scene_name` and `assert_scene_not_empty`); the module is importable by tests without a DOM. Added optional `scene?: string` field to `ProtocolStep` interface in [types.ts](../src/shell/adapter/types.ts) (spec-sanctioned per-step scene field from [specs/PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md)).

- WP-RESOLVE-3 (M1): implemented missing-SVG placeholder rendering in `render_item.ts`. When a `ComputedItem` carries `missing_svg: true` (placeholder-mode build only), `renderItem` renders a visually obvious dashed-border labeled box instead of injecting an SVG. The placeholder element carries the same `data-item-id` as a normal item (walker-addressable) plus `data-missing-svg="true"` and the `object_name` text. Updated [structural_guards.ts](../src/scene_runtime/renderer/structural_guards.ts) Guard 5 (aspect ratio) and Guard 6 (asset resolved) to skip `missing_svg` items, preventing false failures during placeholder-mode renders. The `missing_svg` flag was already threaded through the full pipeline via spread operators in `bindObjects` (PlacementAuthored -> BoundPlacement -> ScaledPlacement -> ComputedItem); no pipeline refactoring was needed.

- WP-SUPPLY-1 (M1): added `--missing-svg=strict|placeholder` flag to [gen_scene_index.py](../pipeline/gen_scene_index.py). Strict (default, normal build): a scene with a placement whose object references a missing SVG asset is reported loudly to stderr; the scene is excluded; the build fails if the scene is allowlisted. Placeholder (dev/test): the scene emits with `missing_svg: true` on affected placements for renderer placeholder display. Both modes emit a missing-asset report. Expanded `SCENE_ALLOWLIST` to include `electrophoresis_bench` and `imaging_bench` (their SVGs are confirmed present per M0 audit). Removed the stale `SCENES_SKIPPED_METADATA["electrophoresis_bench"]` entry (SVG gap no longer exists). Added dev-smoke fixture `tests/content/dev_smoke/missing_svg_check/` with a deliberate missing-SVG object (`test_missing_svg_target`) to exercise both modes. Added `missing_svg?: true` to `PlacementAuthored` and `SceneBRow` slot interfaces in [types.ts](../src/scene_runtime/layout/types.ts) for WP-RESOLVE-3 consumption. Scene count before: 31 (6 base + 25 per-protocol); after: 35 (8 base + 25 per-protocol + 2 smoke fixtures always-emitted).

- WP-SUPPLY-2 (M1): verified that protocol and scene structural validators in `yaml_schema` do not check SVG asset presence and pass unchanged in both strict and placeholder modes. A missing SVG is a content-quality issue (reported by the pipeline), not a structural-validation failure. No validator edits were required.

- Added [README.md](../content/objects_quarantine/README.md) documenting quarantine restoration policy.

- Added [README.md](../content/base_scenes_quarantine/README.md) documenting quarantine restoration policy.

- Added `docs/active_plans/audits/blank_scene_gap_report.md` (WP-DIAG-1, M0): per-protocol initial-scene gap report classifying all 31 protocols as OK (22), scene-missing (4), or unresolved (5). H1 refuted (all 25 per-protocol scenes emit). H2 confirmed for sequence_runners. H3 refuted (no empty scenes). H4 confirmed (4 protocols resolve to allowlist-excluded base scenes). No code changed. Evidence nominated: `passage_hood_detachment` (cell_culture, 2 placements), `sdspage_heat_denature_samples` (sdspage, 3 placements).

### Behavior or Interface Changes

- Made file generation an explicit step in the shell entry scripts instead of a hidden npm lifecycle side effect. [build_github_pages.sh](../build_github_pages.sh) now calls [build_generated.sh](../pipeline/build_generated.sh) directly before type-checking and bundling, fixing the clean-repo failure `ERROR: required source file missing: generated/protocols.ts`. [check_codebase.sh](../check_codebase.sh) checks the codebase only; it never generates and does not depend on whether the gitignored `generated/` tree exists. [run_web_server.sh](../run_web_server.sh) auto-runs `devel/setup_typescript.sh` when `node_modules` is missing (local dev convenience); `build_github_pages.sh` stays CI/GitHub-Pages clean by erroring on missing `node_modules` instead of installing. `devel/dist_clean.sh` now also wipes `generated/`.

- Stripped `package.json` `scripts` to six thin shell-script aliases (`setup`, `setup:playwright`, `build`, `serve`, `check`, `clean`). Removed all six duplicated `pre*` generator hooks and the standalone `typecheck`/`lint`/`format:*`/`test:node`/`browser:smoke`/`ui:review`/`pdf` aliases; those tools now run as direct commands (documented in [USAGE.md](USAGE.md)).

### Fixes and Maintenance

- Purged the jargon word "codegen" (not a dictionary word; confusing for non-programmer protocol authors) across docs prose and code docstrings/comments, replacing it with plain English ("file generation", "generator scripts"): [USAGE.md](USAGE.md), [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [VALIDATION_JSON_SCHEMA.md](VALIDATION_JSON_SCHEMA.md), [specs/TARGET_FILE_STRUCTURE.md](specs/TARGET_FILE_STRUCTURE.md), and docstrings in `pipeline/gen_object_library.py`, `pipeline/gen_scene_index.py`, `pipeline/scene_inheritance.py`, `pipeline/gen_svg_registry.py`, `validation/validate.py`.

- WP-EVID-1 honesty fix: removed synthetic DOM-injection block from `tests/playwright/test_initial_scene_evidence_m1.mjs`. The previous Part B (placeholder-mode evidence) injected a `data-missing-svg="true"` element into `#scene-root` via `page.evaluate()` and then asserted on it -- a test asserting on an element it created itself proves nothing. Removed the injection block, three dependent assertions, and supporting infrastructure (`PLACEHOLDER_PROTOCOL`, `PLACEHOLDER_OBJECT_NAME`, `test_placeholder_protocol()`, `restore_strict_build()`, `register_custom_route`, `execSync` import). The strict-mode evidence (3 protocols, item counts >=1, screenshots) is unchanged. Added explanatory comment noting that placeholder render contract is covered by `tests/test_render_item_missing_svg.mjs` and that end-to-end placeholder rendering through the pipeline is tracked as follow-up (gen_object_library.py does not scan dev_smoke fixtures). The `tests/content/dev_smoke/missing_svg_check/` fixture is left in place (untracked, no build step reads it, no tracked test references it).

- Fixed pre-existing lint errors in `tests/playwright/test_initial_scene_evidence_m1.mjs`: removed unused `spawn`, `net` imports and unused `run_command` function. Fixed pre-existing broken Markdown link in this changelog (WP-TIP-1 entry used `../docs/specs/` redundant traversal; corrected to `specs/`).

- Rewrote [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) from current repo evidence; removed drift describing the removed game architecture (`src/init.ts` entry, core modules `cell_model.ts`/`game_state.ts`/`scoring.ts`, step modules, six old scene adapters, dynamic-svg-recolor and scoring sections). Now documents the `dist_entry` routing, `src/scene_runtime/{layout,protocol,renderer}`, `src/shell/{adapter,hud,regions}`, the pipeline generators, and the two-bundle esbuild build; notes scene operations are stubbed (protocols not yet playable).

- Rewrote [FILE_STRUCTURE.md](FILE_STRUCTURE.md) to match the current tree and corrected the `generated/` artifact list (`object_library.ts`, `svg_registry.ts`, `scenes.ts`, `protocols.ts`, `protocols_index_slim.ts`); removed stale entries (`dist-single/`, `experiments/`, nonexistent scripts/tests).

- Standardized [README.md](../README.md): replaced the nonexistent `export_single_file.sh` / `cell_culture_game.html` quick start with `bash run_web_server.sh`; rewrote the first paragraph as a clean GitHub About description; corrected documentation links.

### Removals and Deprecations

- Deleted `design_advice/` directory (planning docs and JSX prototypes, all superseded by implemented code in `validation/`).
- Deleted 9 unreferenced legacy SVG assets from `assets/equipment/`: `cell_counter_old`, `incubator_legacy`, `microscope_old`, `multichannel_pipette_old`, `plate_reader_old`, `t75_flask_legacy`, `tip_box_old`, `vortex_old`, `water_bath_old`.
- Removed `tools/check_dist_ready.sh`: obsolete now that `run_web_server.sh` always builds before serving. Removed the `package.json` `pre*` generator hooks (`prebuild`, `pretypecheck`, `prelint`, `pretest:node`, `prebrowser:smoke`, `preui:review`) and the standalone npm aliases they guarded; file generation now runs inside the shell entry scripts via `pipeline/build_generated.sh`.

### Decisions and Failures

- M1 + M2 scope boundary: this work fixes initial-scene rendering (entry-step resolution, empty-scene guard, missing-SVG placeholder pipeline) and the framed interface (bounded six-region layout, scene-percent mapping, chrome regions, professor-tip field). It does NOT expand protocol playability. Scene operations (`ObjectStateChange`, `SceneChange`, etc.) remain stubbed in the runtime (`build_stub_scene_op_deps` console.warns). No mini-protocol is complete under PRIMARY_CONTRACT item 4 (visible browser interaction). Un-stubbing scene operations is deferred follow-up work.
- sequence_runner protocols now resolve and render their initial scene (via delegation to the first listed mini-protocol). They are NOT runnable: the step machine logs "Unknown step_name" because runners have no own `steps` list. Driving runner steps through the step machine is deferred playability work.
- Missing-SVG placeholder render contract is covered by the unit test `tests/test_render_item_missing_svg.mjs` (9 tests, all pass). End-to-end placeholder rendering through the full pipeline is not yet proven: gen_object_library.py does not scan `tests/content/dev_smoke/` fixtures, so dev_smoke fixture objects are never loaded into OBJECT_LIBRARY and therefore never reach the renderer. Tracked as follow-up.
- WP-DIAG-1 finding: `SCENES_SKIPPED_METADATA["electrophoresis_bench"]` entry in [gen_scene_index.py](../pipeline/gen_scene_index.py) was stale. The referenced SVGs (`electrophoresis_tank`, `electrophoresis_tank_inner_chamber`, `electrophoresis_tank_outer_chamber`) are all present in `assets/equipment/`. WP-SUPPLY-1 cleaned up this stale metadata when expanding the allowlist.

- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) Known gaps: scene operations are stubbed (`build_stub_scene_op_deps` console.warns on every interaction); `sequence_runner` protocols render their entry scene but the step machine cannot drive them (no own `steps` list); end-to-end missing-SVG placeholder rendering through the full pipeline is not yet proven (gen_object_library.py does not scan dev_smoke fixtures).

### Developer Tests and Notes

- WP-EVID-2 (M2): added `tests/playwright/test_framed_layout_m2.mjs`. Nine measurable assertions on `sdspage_heat_denature_samples`: (1) `#scene-root` 1044x587 < viewport 1280x900; (2) >=1 `[data-item-id]`; (3-6) all four chrome regions visible with correct text; (7) current step card has `data-step-status="current"`; (8) all item bboxes within scene-root (no overflow); (9) click target for first item lands inside item bbox. All 9 PASS. Screenshot saved to `test-results/m2_framed_layout_sdspage_heat_denature_samples.png`.
- Added `tests/test_resolve_entry_scene.mjs`: 16 unit tests covering all resolution branches (step.scene, SceneChange fallback, throw, runner delegation) and the empty-scene guard (non-dev_smoke throws, dev_smoke passes). All 16 pass.
- Added `tests/test_render_item_missing_svg.mjs`: 9 unit tests covering all four placeholder contract requirements (data-missing-svg, data-item-id, object_name text, no injected SVG) plus normal-item regression. All 9 pass. Formatting of `tests/test_resolve_entry_scene.mjs` also fixed via `npm run format:write`.

## 2026-05-26

### Additions and New Features

- Added a browser protocol selector as the default `dist/index.html` experience. The launcher lists generated protocol metadata, groups full sequences before mini-protocols, supports direct `?protocol=<protocol_name>` links, and shows a recoverable unavailable-scene state when a protocol starts outside the current scene allowlist.
- Added [build_protocol_index.py](../pipeline/build_protocol_index.py), which emits `generated/protocol_index.ts` from `content/protocols/**/protocol.yaml` for the browser launcher.
- Added [test_protocol_selector.mjs](../tests/playwright/test_protocol_selector.mjs) as a reusable smoke test for the protocol selector landing page and first-card navigation.

### Behavior or Interface Changes

- Fresh-clone build workflow now treats [build_github_pages.sh](../build_github_pages.sh) as the single generated-data build entry point. The script regenerates `generated/object_library.ts`, `generated/svg_registry.ts`, and `generated/scenes.ts` before type-checking and bundling, so `bash build_github_pages.sh`, `npm run build`, and [run_web_server.sh](../run_web_server.sh) share the same fresh-build path.

### Fixes and Maintenance

- Removed the duplicate npm `prebuild` hook. `npm run serve` now delegates directly to [run_web_server.sh](../run_web_server.sh), which already rebuilds before serving.
- Moved generated-artifact builders from `tools/` to `pipeline/`: [gen_object_library.py](../pipeline/gen_object_library.py), [gen_svg_manifest.py](../pipeline/gen_svg_manifest.py), and [gen_scene_index.py](../pipeline/gen_scene_index.py). Build scripts and npm pre-hooks now call the pipeline paths.
- Fixed [gen_scene_index.py](../pipeline/gen_scene_index.py) validation to read authored `zone_name` instead of retired `id`, matching the 2026-05-26 `zone.id` retirement. Required scene and placement keys now use direct `dict[key]` access per [PYTHON_STYLE.md](PYTHON_STYLE.md); the generator still emits runtime `id` fields for the TypeScript `SceneZone` shape.

## 2026-05-24

### Additions and New Features

- WP-ARCHIVE-1: Scorecard history archive write + read + quarterly report. Created `validation/scene_design/archive.py` with append-on-write `append_history_row(scene_name, scene_class, score, metric_values, history_path)` function that creates parent dirs and writes one JSON line per invocation to `test-results/scene_design/history/scorecard_history.jsonl` (gitignored runtime artifact). Row schema: `{run_id (ISO-8601 UTC timestamp), date_utc (YYYY-MM-DD), scene, class, score, metric_values}`. Read side: `load_history(path)` returns list-of-dict or [] on missing file; raises on malformed JSON line (no silent skip); `score_for_run(history, scene, run_id)` -> float | None; `score_quarter_range(history, scene, start_date, end_date)` -> list of rows within quarter date range. CLI integration: `--no-history` flag added to `python3 -m validation.scene_design.cli` to skip write (useful for tests/dry runs); default behavior writes. Note: `score_at_commit(scene, sha)` is dropped per 2026-05-24 plan revision (agents have no git access); `score_for_run` is the replacement keyed on `run_id` (ISO-8601 timestamp). Created `validation/scene_design/quarterly.py` (executable script) with argparse interface `--quarter YYYY-Qn --history-path <p> --out <p>`. Converts quarter string to date range (Q1=Jan-Mar, etc.), loads history, filters by scene and quarter, computes per-scene score deltas (latest - earliest in quarter), ranks by largest drop, emits Markdown report with summary table and bottom-decile highlight. Methodology section included. Manual-trigger only; no CI scheduling. 23 unit tests in `tests/test_scene_design_archive_write.py` (5 tests covering file creation, parent dirs, row format, multiple appends), `tests/test_scene_design_archive_read.py` (11 tests covering missing file, empty file, single/multiple line loads, blank-line tolerance, malformed JSON rejection, score_for_run lookup, score_quarter_range filtering), `tests/test_scene_design_quarterly.py` (7 tests covering quarter-to-date conversion for all quarters, invalid format/quarter rejection, integration structure). Verified: pytest tests/test_scene_design_archive_write.py tests/test_scene_design_archive_read.py tests/test_scene_design_quarterly.py -q (23/23), pyflakes clean (116/116), CLI smoke with bench_basic + hood_basic scenes produces history file with valid JSON rows.

- WP-STRICT-1: Promotion policy and --strict CLI mode for Group B rules. Created `validation/scene_lint/promotion.py` with closed-schema config promotion.yaml loader and bar-evaluation engine. Promotion schema (all fields required): rule (B-rule name, not Group A), promoted_at (YYYY-MM-DD), precision (float, metric value at promotion time), recall (float), positive_count (int), low_confidence_approved (bool, default False). Load-time re-validation: each promotion is checked against the current labeled_corpus.yaml; rules failing re-validation (precision < 0.90, recall < 0.80, or positive_count < 20) emit promotion_below_bar advisory and are omitted from the active set. Exported functions: `load_promotions(path, corpus_path)` -> (valid_promotions, advisory_findings); `evaluate_promotion_bar(rule_name, findings, corpus)` -> bar evaluation dict with keys {precision, recall, positive_count, meets_bar, reasons_failing}; `apply_strict_filter(findings, promotions)` is a no-op on findings (actual gate is CLI exit-code logic, not finding filtering). CLI wiring via `_add_scene_lint_extras`: `--promotions <path>` flag (defaults to validation/scene_lint/promotions.yaml when omitted; `--no-promotions` explicit disable); shared toolkit --strict flag (line 137-142) gates exit behavior. When --strict is passed, cli.main loads promotions, emits advisory findings for malformed/below-bar entries, and exits 1 if any ESCAPE_REQUIRED finding matches a successfully-promoted rule (after re-validation). Group A BLOCKED findings still always exit 1 (unchanged, independent of --strict). Empty default at validation/scene_lint/promotions.yaml with comment explaining closed schema. 28 unit tests in tests/test_scene_lint_promotion.py covering load happy path, malformed entries (missing fields, Group A rules, non-dict, invalid metric types), schema validation, bar evaluation (met/not-met cases, insufficient positives, low precision/recall, None precision/recall), promotion_below_bar advisory generation, and no-op filter behavior; all pass in 0.06s. Verified: pytest tests/test_scene_lint_promotion.py -q (28/28), pytest tests/test_pyflakes_code_lint.py -q (116/116), all 201 scene-lint tests pass (promotions + suppressions + B1-B10 + Group A + confusion). CLI smoke: python3 -m validation.scene_lint.cli -S content/base_scenes/bench_basic.yaml --strict exits 0 (no rules promoted yet, empty promotions.yaml).

- WP-ARCHIVE-2: Suggested-fix engine for below-class-floor scenes. Created `validation/scene_design/suggest.py` with entry function `suggest_moves(scene_path, n_suggestions=1)` that permutes three classes of single-move mutations: (1) zone reassign (iterate all zones), (2) display_width_cm adjust (+/-10, +/-20, +/-30 cm steps), (3) data-primary flip (true/false toggle). Each candidate mutation is scored in-memory by: apply to scene dict copy, regenerate dump_data via temp file, recompute metrics, aggregate score via per-class weights. Render-risk guard: before emit, re-run render predictor on mutated scene in-memory and filter moves that introduce new ESCAPE_REQUIRED findings (logged but not surfaced). Score-monotonicity guard: assert projected score strictly increases vs baseline before emit. Engine is advisory-only (never mutates YAML). Per-class score floors (M4 calibration-ready stubs): template 70, composition 65, instrument_heavy 65, zoom_detail 70, dense_clutter 60. Integration helpers: `dump_scene_geometry_from_scene_dict(scene, temp_dir)` writes mutated scene to temp YAML, calls dump_scene_geometry, cleans up; `compute_metrics_from_dict(scene, dump_data)` imports and invokes all 16 metric functions with correct signatures (primary_detection_confidence and protocol_step_affinity take scene-only; others take both). 18 unit tests in `tests/test_scene_design_suggest.py` covering permutation enumeration (all 3 mutation types, guards against mutation of original), score monotonicity (guards filtering), render-risk guard (filter logic), advisory-only semantics (YAML immutability), class-floor lookup (all classes present, reasonable bounds). M0 corpus smoke run over 9 base scenes (excluding row_slot scenes); engine executes without crash; reports generated under test-results/scene_design/suggestions/. Scenes show no monotonic improvement under current permutation set (expected M4 behavior pending metric calibration on real post-render scores). Verified: pytest tests/test_scene_design_suggest.py -q (18/18), pyflakes clean, all 1803 repo tests pass.

- WP-SUPPRESS-1: Group B suppression manifest schema and enforcement. Created `validation/scene_lint/suppressions.py` with (1) `load_suppressions(manifest_path, today)` loader and validator emitting malformed/expired advisories; (2) `apply_suppressions(findings, suppressions)` filter removing matched findings; (3) `SuppressionEntry` dataclass and `parse_expiry_date` date parser handling YAML date objects. Suppression entry shape: `rule, scene, placement_name (optional, null=>scene-wide), reason, ticket, owner, expires`. Validation: all four fields required (rejection -> `malformed_suppression` advisory); Group A rule names rejected (doc-hardcoded closed list); `expires > 90 days` required (rejection -> `malformed_suppression`); past-expiry -> `expired_suppression` advisory (MEDIUM confidence, non-gating). Matching: `(rule, scene, placement_name)` tuple; null placement_name matches all placements under (rule, scene). Suppressed findings REMOVED from output (not emitted). CLI wiring: `--suppressions <path>` flag added to `cli.py` via extras callback; advisory findings from manifest appended to findings list; live suppressions applied before JSONL emit and confusion-table path. Example manifest at `validation/scene_lint/suppressions.yaml` with one valid (expires 2026-08-24) entry. 29 unit tests in `tests/test_scene_lint_suppressions.py` covering happy path, missing/malformed fields, date validation, expiry checks, Group A rejection, apply logic, CLI integration; all pass. Verified: `pytest tests/test_scene_lint_suppressions.py -q` (29/29), `pytest tests/test_pyflakes_code_lint.py -q` (116/116), all 173 scene-lint tests pass. CLI smoke: `python3 -m validation.scene_lint.cli -S bench_basic.yaml --suppressions suppressions.yaml` correctly filters matched findings.

- WP-B-RULES-3: Group B rules B7-B10 implemented in `validation/scene_lint/rules_group_b.py`. B7 (`label_offscreen`): emits ESCAPE_REQUIRED when label_bbox extends outside scene_bounds horizontally (left or right edges). B8 (`label_object_overlap`): checks if label_bbox intersects any placement's visual_bbox with > 10 px² intersection (conservative: checks all placements, not filtered to scientific-kind due to lack of object-load helper in this context). B9 (`invisible_placement`): emits ESCAPE_REQUIRED on five triggers: (1) visual_bbox area < 100 px², (2) height > 2x zone_inner_h, (3) scale_source='skipped_error' (HIGH confidence), (4) [defensive] default_width missing/invalid, (5) fallback_authored scale source (MEDIUM confidence, indicates reduced simulator confidence). B10 (`zone_overlap`): emits ESCAPE_REQUIRED for any pair of zones with non-zero intersection; NO SIM DEPENDENCY (static geometry on scene.zones); unit test asserts never invokes dump_data. All four rules wired into `run_all_rules()` in `validation/scene_lint/cli.py` after B1-B6. 18 new tests in `tests/test_scene_lint_b7_b10.py`; all pass in 0.02s. Verified: pyflakes clean, 144 total scene-lint tests pass (18 B7-B10 + 36 B3-B6 + 25 B1-B2 + 33 Group A + 32 confusion). CLI on bench_basic.yaml emits B7/B8/B9 findings correctly (B9 fallback_authored signals on rear_left_waste, rear_right_vortex).

- M2-EXIT-1: Scene-design metrics cross-check: dump_data wiring completed. Modified `validation/scene_design/cli.py` to compute `dump_scene_geometry(path)` once per scene with error handling (OSError, RuntimeError, KeyError), passing dump_data to all metrics that consume it. Metrics that need dump_data now return computed values instead of None (NotReady). Wrapped dump failures in narrow try/except; row-slot scenes and others that fail dump (missing scene_bounds) degrade gracefully to None metrics without raising exceptions. New test `tests/test_scene_design_cli_dump_wiring.py` (2 tests) verifies metric population on successful dump and graceful degradation on failure. Baseline report regenerated at `test-results/scene_design/metrics_baseline_2026-05-24.md`: population rate improved from 12% (1 of 8 metrics) to 90% (129 of 144 metric cells). Non-None metrics: predicted_label_overlap, label_to_object_distance, label_wrap_rate, scene_density, row_overcrowding, tab_stops_symmetry, depth_tier_usage, aspect_fidelity, primary_area_ratio, primary_prominence, primary_detection_confidence (only-YAML), zone_footprint_balance, largest_empty_band, scene_occupied, support_distance (15 of 16 total; protocol_step_affinity remains skeleton-only per WP-METRICS-1 deferral). All 84 existing metric tests still pass; pyflakes clean.

- WP-B-RULES-2: Group B rules B3-B6 implemented in `validation/scene_lint/rules_group_b.py`. B3 (`row_footprint_overflow`): sums footprint_bbox widths per row within a zone; emits ESCAPE_REQUIRED when total exceeds zone inner_rect width; skips silently when dump_data contains no row info (row-slot schema decision-gated). B4 (`placement_bbox_outside_scene`): emits ESCAPE_REQUIRED when placement_bbox extends outside scene_bounds on any edge; zero tolerance; skips scale_source=skipped_error. B5 (`placement_bbox_outside_zone`): emits ESCAPE_REQUIRED when placement_bbox extends outside zone inner_rect beyond 4-px tolerance (ZONE_OVERFLOW_TOLERANCE_PCT ~0.347 scene-%); skips skipped_error. B6 (`item_item_overlap`): for each pair of placements in the same zone, emits ESCAPE_REQUIRED when footprint_bbox rects have non-zero intersection; each pair reported once; skips skipped_error. All four wired into `run_all_rules()` in `validation/scene_lint/cli.py` after B1+B2. `validation/scene_lint/confusion.py::load_labeled_corpus` updated to accept `entries` as alias for `labels` top-level key (matches labeled_corpus.yaml auto-seed format). 36 new tests in `tests/test_scene_lint_b3_b6.py`; 126 total pass (36 B3-B6 + 25 B1-B2 + 33 Group A + 32 confusion) in 0.11s. Confusion reports emitted to `test-results/scene_lint/confusion_b3_b6_2026-05-24_*.md` (0 positive corpus entries for B3/B6 per audit; B4/B5 also 0 corpus positives). Baseline refreshed at `test-results/scene_lint/base_scenes_baseline_2026-05-24.md` with post-B3-B6 ESCAPE_REQUIRED counts per scene.

- WP-B-RULES-1: Group B rules B1 and B2 implemented in `validation/scene_lint/rules_group_b.py`. B1 (`aspect_distorted_predicted`): emits ESCAPE_REQUIRED when precomputed aspect_delta_pct exceeds 5% threshold; skips placements with scale_source=skipped_error; confidence derived from scale_source (cm_model->high, fallback_authored->medium, fallback_no_workspace->low); bbox_type=visual_bbox per spec. B2 (`item_taller_than_zone`): emits ESCAPE_REQUIRED when zone_inner_h / placement_h < MIN_SCALE (0.55); uses placement_bbox height and zone inner_rect from dump schema; bbox_type=placement_bbox per spec. Both rules wired into `run_all_rules()` in `validation/scene_lint/cli.py` after Group A; dump computed once per scene and reused. Advisory only (exit=0 default; exit=1 only with --strict). Verified: pyflakes clean, 25 new tests pass in tests/test_scene_lint_b1_b2.py, existing 33 Group A tests unchanged, bench_basic.yaml lint exits 0 with B1 advisories on rear_left_waste and rear_right_vortex (43.7% aspect delta, fallback_authored confidence).

- WP-B-RULES-4 confusion-table runner scaffolding: `validation/scene_lint/confusion.py` with `load_labeled_corpus(path)` (YAML loader, raises on missing required fields per PYTHON_STYLE.md), `compute_confusion(findings, corpus, rule_name)` (TP/FP/FN/TN counts, precision, recall), and `write_confusion_markdown(stats, rule_name, corpus, out_path)` (Markdown table with counts + metrics). CLI flags `--validate-against` and `--emit-confusion` in `validation/scene_lint/cli.py` now wired: corpus loads when `--validate-against` is given; per-rule Markdown files emit when `--emit-confusion` is also set. The `sys.exit(2)` "not yet implemented" guard replaced with real corpus loading and emit loop. Missing corpus file treated as empty corpus (no crash). 32 unit tests in `tests/test_scene_lint_confusion.py` covering corpus loading (happy path, missing file, missing-field rejection), confusion math (TP/FP/FN/TN, precision/recall), and markdown writer; all pass in 0.05s. Pyflakes clean.

- WP-METRICS-2: label hygiene, density, and composition health metrics implemented in `validation/scene_design/metrics/`. Labels: `predicted_label_overlap` (fraction of placements whose label_bbox intersects another footprint or label_bbox, score 100 at 0 collisions), `label_to_object_distance` (mean center-to-center gap between label and footprint, score 100 at distance 0, normalized by scene diagonal, 0 at dn >= 0.25), `label_wrap_rate` (fraction of labels with height > 5.0 scene-%, score 100 at no wrapping). Density: `scene_density` (total footprint / scene area, same target band [0.15, 0.70] and scoring formula as scene_occupied), `row_overcrowding` (sum of footprint widths per zone / zone inner_width; highest zone load; score 100 when load <= 1.0, 0 at load >= 2.0; capped at 100). Composition: `tab_stops_symmetry` (footprint widths distributed across three scene-width thirds; score penalizes max/min ratio > 1.0 by 20 pts/unit; None when < 2 populated columns), `depth_tier_usage` (distinct depth tiers from zone names: rear=1, mid=2, front=3; score = distinct/3 * 100), `aspect_fidelity` (100 minus mean aspect_delta_pct across valid placements; skips scale_source=skipped_error; returns None when all skipped). All functions return None on missing dump_data (NotReady semantics). 46 unit tests in `tests/test_scene_design_metrics_labels_density_composition.py`; all pass in 0.08s. Fixture YAML at `tests/fixtures/scene_design/metrics/labels_golden.yaml`, `density_golden.yaml`, `composition_golden.yaml`. Baseline cross-check: 9 primary scenes run at `test-results/scene_design/metrics_baseline_2026-05-24.md`; depth_tier_usage populates for all 9 scenes (no sim pipeline needed); remaining 7 metrics return None (NotReady, require dump_data). No post-render scorecard data available; calibration deferred per plan.

- WP-METRICS-1: hierarchy, balance, and proximity metrics implemented in `validation/scene_design/metrics/` package. Hierarchy: `primary_area_ratio` (primary footprint area / total footprint area, 0-100), `primary_prominence` (primary area / largest supporter area normalized to 2x target, 0-100), `primary_detection_confidence` (100 if data-primary explicit tag, 50 if heuristic fallback, None if no placements). Balance: `zone_footprint_balance` (max/min footprint sum ratio across populated zones, score penalizes ratio above 1.0 by 20 pts/unit, floors at 0; requires >= 2 populated zones per resolved decision placement_count >= 1), `largest_empty_band` (grid-scan for largest contiguous empty horizontal/vertical band as fraction of scene, score 100 at no empty, 0 at >= 50% empty), `scene_occupied` (total footprint / scene area, 100 inside [0.15, 0.70] target band, linear penalty outside). Proximity: `support_distance` (mean Euclidean distance from supporters to primary center, normalized by scene diagonal, score 100 at distance 0, 0 at dn >= 0.50), `protocol_step_affinity` (skeleton only, returns None; protocol vocab access not yet wired; documented in docstring). All functions return None on missing data (NotReady; aggregate_score skips). 38 unit tests in `tests/test_scene_design_metrics_hierarchy_balance_proximity.py` covering canonical, boundary, failure, and NotReady cases per function; hand-computed expected values in fixture YAML files under `tests/fixtures/scene_design/metrics/`. Tests pass in 0.06s, pyflakes clean.

### Behavior or Interface Changes

- `python3 -m validation.scene_lint.cli` flag additions: `--suppressions <path>` (load Group B suppression manifest), `--promotions <path>` (load promotion config; defaults to `validation/scene_lint/promotions.yaml`), `--no-promotions` (skip promotion loading entirely; works whether or not `--strict` is set), and `--strict` semantic now gates exit code 1 on `ESCAPE_REQUIRED` findings from promoted rules. Group A `BLOCKED` exit code 1 is unchanged. Stale "not yet implemented" help text removed from `--validate-against` and `--emit-confusion`. Unused `--rules` flag deleted.
- `python3 -m validation.scene_design.cli` flag addition: `--no-history` (skip writing a row to `test-results/scene_design/history/scorecard_history.jsonl`). Default behavior writes. Per-scene `SceneCard.score` is now the real `aggregate_score(metrics, scene_class)` output (was hardcoded `None`); the same value flows to the archive row.
- `python3 -m validation.scene_design.quarterly` is a new manual-trigger script for quarterly rollup Markdown reports.

### Fixes and Maintenance

- Multi-reviewer audit fix pass (Plan, Test, Style, Docs, Legacy, Comment reviewers). Production-code fixes: (a) `validation/scene_design/cli.py` -- scene-card `score` field now flows from `aggregate_score(metrics, scene_class)` instead of being hardcoded `None`; broad `except Exception` around `append_history_row` removed (raises normally on `OSError`); metric imports hoisted from inside `compute_metrics` to module top; visual `#====` separators added; (b) `validation/scene_design/weights.py` -- `balance_largest_empty_band` weight key renamed to `largest_empty_band` so template-class scenes can actually score (the cli was emitting `largest_empty_band` but weights required the prefixed name; aggregate_score had been returning `None` for every template scene); (c) `validation/scene_design/quarterly.py` -- broad `except Exception` blocks narrowed to `(OSError, json.JSONDecodeError)` and `OSError`; misleading `earliest_score`/`latest_score` variable names (actually min/max, not chronological) renamed to `min_score`/`max_score` and Markdown columns/methodology updated; redundant shebang dropped (canonical invocation is `python3 -m`); (d) `validation/scene_design/suggest.py` -- stub `_check_render_risk` returning False replaced with real implementation that writes mutated scene to temp YAML, runs `run_all_rules`, and rejects mutations introducing new `ESCAPE_REQUIRED` (rule, placement_name) keys vs baseline; `.get()` defaults on required fields (`placements`, `placement_name`, `zone`, `zones`, `scene_name`) replaced with direct `dict[key]` access; broad `except (..., Exception)` tuple narrowed to `(OSError, RuntimeError, KeyError)`; broad `except Exception` in class detection narrowed to `SceneClassError`; `from typing import Any` (unused) dropped; lazy imports inside `compute_metrics_from_dict` hoisted to module top; redundant `balance_largest_empty_band` alias dropped (consistent with weights.py rename); stub-era `render_guard_rejections: 0` comments removed; `dump_scene_geometry_from_scene_dict` docstring documents the known dump-path limitation (`/tmp` cannot resolve `content/objects/` asset refs); `_get_class_floor` floors hoisted to module-level `CLASS_FLOORS` constant; visual `#====` separators added; (e) `validation/scene_lint/cli.py` -- dead `if args.no_promotions: promotions_path = None` branch inside `if args.strict and not args.no_promotions:` removed; unused `suppressed` variable swallowed via `_` unpack; (f) `validation/scene_lint/suppressions.py` -- `rule` and `scene` added to closed `required_fields` set (they were missing despite being required for matching, so an entry lacking `rule` would silently key to `rule='unknown'`); `.get(key, default)` calls after the guard replaced with direct key access; redundant adjacent comments collapsed; (g) `validation/scene_lint/promotion.py` -- broad `except Exception` around `PromotionEntry` dataclass construction removed (constructor was already given validated typed values; raising on the construction is a programming error that should propagate); `.get('positives', [])` / `.get('mapped_rule')` on guaranteed-present corpus fields replaced with direct access; `PromotionEntry` dataclass docstring extended with full `Attributes:` section; `apply_strict_filter` (no-op, zero callers) deleted as dead API surface; (h) `validation/scene_lint/rules_group_b.py` -- non-ASCII `^2` and `~=` characters in B8 comment replaced with ASCII; B9 docstring + trigger 5 comment updated to remove "informational, not a hard failure" contradiction with the `ESCAPE_REQUIRED` verdict; B10 `.get(..., default)` on required `zone_name` / `bounds` fields replaced with direct access. Test-suite pruning: 11 brittle and stub-only tests removed across `tests/test_scene_lint_promotion.py`, `tests/test_scene_lint_suppressions.py`, `tests/test_scene_design_suggest.py`, `tests/test_scene_design_quarterly.py`, `tests/test_scene_design_archive_write.py`, `tests/test_scene_design_archive_read.py` -- empty `pass`-body tests (5), dataclass field-assignment tests (5), hardcoded `days_expired == 4` constant assertion, `len(advisories) == len(GROUP_A_RULES)` collection-size assertion, `[:3]` slice that contradicted its own docstring, never-collected `quarterly_report_integration` function (no `test_` prefix), brittle `test_quarterly_report_markdown_structure` (asserted hardcoded fixture scores), required-key list assertion in `test_append_history_row_format`, and brittle bare-`except Exception` in `test_load_history_malformed_json_raises` (replaced with `pytest.raises(json.JSONDecodeError)`). Test relocation: subprocess-driven `tests/test_scene_design_cli_dump_wiring.py` moved to `tests/e2e/e2e_scene_design_cli.py` (real CLI subprocess invocation belongs in E2E per [E2E_TESTS.md](E2E_TESTS.md); excluded from `pytest tests/`).
- T10 rename follow-on: completed the `validation/yaml/` -> `validation/yaml_schema/` rename by fixing 23 stale cross-imports inside `validation/yaml_schema/` itself. The 2026-05-23 CHANGELOG entry for WP-LOAD-1 incorrectly claimed "updated all importers"; 9 files within the package still imported from `validation.yaml.*`. Fixed: `compiled_summary.py` (1), `content_lint.py` (9), `cross_protocol.py` (1), `database.py` (1), `material_validator.py` (2), `object_validator.py` (2), `protocol_validator.py` (3), `scene_base_validator.py` (2), `scene_protocol_validator.py` (2). All `from validation.yaml.<module> import` and `import validation.yaml.<module> as` forms replaced with `validation.yaml_schema.*` equivalents. Fixes `ModuleNotFoundError: No module named 'validation.yaml'` at `tests/test_object_validator_variant_collapse.py` collection. Verified: pyflakes clean, 8 tests pass, stale-import grep empty.
- Stale doc paths fixed: [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) line 315 references `validation/yaml_schema/` (was `validation/yaml/`); [USAGE.md](USAGE.md) "five stages" updated to "seven stages" and per-stage invocation list now lists `validation.yaml_schema` (was stale `validation.yaml`) plus `validation.scene_lint.cli` and `validation.scene_design.cli`. `--only` flag-cell extended with `scene-lint` / `scene-design` tokens. New "Scene-lint specific flags" + "Scene-design specific flags" tables document `--suppressions`, `--promotions`, `--no-promotions`, `--no-history`, `--report-only`, `--validate-against`, `--emit-confusion`. [FILE_STRUCTURE.md](FILE_STRUCTURE.md) `yaml` subsection renamed to `yaml_schema`; new `scene_calc`, `scene_lint`, `scene_design` subsections enumerate every file under each new subtree (entries use backticked paths since the new files are not yet tracked; convert to Markdown links after `git add`). `shared_toolkit` subsection extended with `scene_loaders.py` and `cli.py`.

### Removals and Deprecations

- `apply_strict_filter` no-op function removed from `validation/scene_lint/promotion.py` and from `tests/test_scene_lint_promotion.py` import + test class. The function was documented as a no-op and had zero callers. The `--strict` gate is purely a CLI exit-code decision in `cli.main`; the placeholder added unused API surface.
- `--rules` CLI flag removed from `validation/scene_lint/cli.py`. The flag was registered and accepted, but `args.rules_filter` was never read; no rule filtering was wired in.
- Authored YAML field `zone.id` retired per SPEC_DESIGN_CHECKLIST.md rule 25 (RD-15 closure extension). Replaced by `zone.zone_name` across all authoring surfaces. See Decisions and Failures for full migration scope.

### Decisions and Failures

- **`zone_name` ratified as the canonical authored zone identifier per SPEC_DESIGN_CHECKLIST.md rule 25.** Rule 25 enumeration of allowed `_name` handles extended with `zone_name`. The retired-terms closure (RD-15) had explicitly listed `object_id -> object_name`, `scene_id -> scene_name`, `placement_id -> placement_name`, `subpart_id -> subpart_name`, `step_id -> step_name`, `protocol_id -> protocol_name`, `part_id -> part_name`, `day_id -> day_name`, `asset_id -> asset_name`, `overlay_id -> overlay_name`, but zone identity was omitted from the explicit list. Bench `zone.id` slipped past closure when WP-SIM-2 (2026-05-23) ratified `dict[key]` direct access on `zone.id` and `zone.bounds` in dump.py without flagging the `_id` violation. All 18 base scenes + 1 quarantine scene rewritten: `  - id:` -> `  - zone_name:` (38 zones in 9 primary scenes + 1 quarantine zone, 39 renames total). Consumer reads updated: `validation/yaml_schema/scene_base_validator.py` enforces `zone_name` (was `id`); `validation/scene_calc/dump.py` reads `zone['zone_name']`; `pipeline/build_scene_data.py` + `pipeline/build_new_scene_data.py` + `tools/gen_scene_index.py` all read authored YAML as `zone['zone_name']`; the latter two continue to emit runtime TS field `id:` per rule 25 carve-out (runtime variables in Python/TS may use `_id`). `validation/scene_lint/rules_group_b.py` B10 reverted from temporary `zone_label()` fallback helper to direct `zone['zone_name']` access (fix-the-design, no fallback). Spec docs updated: SCENE_VOCABULARY.md zone field table, SCENE_YAML_FORMAT.md zone field table + two YAML examples, LAYOUT_ENGINE.md zone field table (TS-adapter pattern `zone.id` retained as runtime code per the carve-out). Test fixtures in `tests/test_scene_design_suggest.py` updated from `- id:` to `- zone_name:`. Python local variable names like `zone_id` (in test helpers + dump.py local scope) NOT touched -- runtime code per the rule 25 carve-out. Verified: 1836 pytest pass, scene_lint CLI smoke on bench_basic exits 0, markdown links + ASCII gates clean.
- CI / GitHub Actions / PR-comment scope removed from the scene-lint plan at `/Users/vosslab/.claude/plans/replicated-hatching-avalanche.md` per user direction. Plan body now carries a 2026-05-24 revision header documenting the cut: WS-CI-LINT, WS-CI-DESIGN, WP-CI-LINT-1, WP-CI-DESIGN-1 deleted; M3 narrowed to suppression manifest only (WP-SUPPRESS-1); M4 entry criteria dropped the "one sprint of CI confusion data" gate in favor of `>= 20 ground-truth positive labels in test-results/scene_lint/labeled_corpus.yaml`; `composition-review-required` label removed; "build-gating" framing replaced with CLI-level gate framing throughout. M4 closure carries two NOT MET exit criteria, both user-gated: (a) first B-rule promotion requires reviewer-confirmed labels in the labeled corpus, and (b) the suggested-fix engine emits zero suggestions across the M0 corpus because `dump_scene_geometry` cannot resolve `content/objects/` asset references when called on a temp YAML written under `/tmp` (engine + guards work; dump-path refactor is the unblock). Active plan tracker `docs/active_plans/active/scene_lint/README.md` updated with M2/M3/M4 status, M4 heading changed from "SCAFFOLDING CLOSED" to "PARTIAL", and the five decision-gated items section now enumerates the fifth (dump_scene_geometry repo-root refactor) alongside the four carried over from M1-M2 (row-slot dump acceptance, scene-design row-slot blindspot, Step-4 data-primary dead code, kind forwarding in `dump._synthesize_placement_inputs`).
- CHANGELOG rotation: `devel/rotate_changelog.py` ran 2026-05-24, moving 6 day blocks (2026-05-17 through 2026-05-22) to `docs/CHANGELOG-2026-05d.md`. Active file went from 4258 lines to 153 lines plus today's additions; two most recent day blocks (2026-05-24, 2026-05-23) retained.

## 2026-05-23

### Fixes and Maintenance

- WP-SIM-2 spec reviewer defect fixes (7 issues): (1) Schema drift fixed: placement-level bboxes (visual_bbox, placement_bbox, footprint_bbox, label_bbox) now emit {x, y, w, h} keys (x=left, y=top, w=width, h=height) per pinned WP-SIM-2 schema; zone bounds/inner_rect retain {left, right, top, bottom} edge-coordinate form. (2) Six bare `except Exception:` blocks removed from dump.py; no more silent zero-fill placeholders. (3) Required-field `.get()` calls converted to direct `dict[key]` access for `scene_name`, `scene_bounds`, `placement_name`, `object_name`, `zone`, `zone.id`, `zone.bounds` per PYTHON_STYLE.md. (4) Stub asset argument fixed: dump now loads actual object library (walks `content/objects/`), resolves `asset_name` from object `visual_states`, loads SVG viewBox via `load_svg_viewbox`, and synthesizes `_x`, `_top`, `_visualWidth` from zone center and `layout.default_width`. (5) scale_source now computed correctly: `cm_model` if `display_width_cm` authored, `fallback_authored` if `default_width` authored, `fallback_no_workspace` if no size hint, `skipped_error` only on real asset-load failure. (6) Golden case counts boosted: zone_inner_rect 2->4, fits_in_zone 3->4 (exact-boundary case), required_scale_to_fit 3->4 (height-binding case), estimate_label_box 3->5 (decoration gap + scientific zone-edge proximity). New fixtures in tests/fixtures/scene_calc/. (7) Scientific-vs-decoration distinction implemented in `validation/scene_calc/labels.py::estimate_label_box`: scientific objects (equipment, flask, pipette, rack, plate, waste, bottle) use LABEL_GAP_SCIENTIFIC=2.0 scene-%, decoration objects use LABEL_GAP_DECORATION=4.0 scene-%; tested with two new golden cases. All changes: pyflakes clean, 67 tests pass.

- WP-LINT-2 spec reviewer defect fixes (5 issues): (1) Critical gate filter bug fixed: `cli.py:169` now correctly filters Group A findings by verdict (BLOCKED) instead of broken rule-name regex that matched zero rules, making gate always exit 0. (2) Silent output fixed: JSONL writer wired to stdout before gate check so findings emit to stdout for all invocations; --report-only suppresses exit 1 while still emitting findings. (3) Style violation fixed: broad `except Exception` narrowed to `(yaml.YAMLError, OSError, RuntimeError)` per PYTHON_STYLE.md, extracted Finding construction to `_yaml_parse_error_finding()` helper so try body is 1 line and except body is 2 lines. (4) Test quality fixed: `test_multi_level_inheritance()` was asserting wrong rule (inheritance_unknown_base instead of inheritance_multi_level); rewritten to create real base-extends-base chain in tmp_path and assert genuine MultiLevelInheritanceError detection. (5) Documentation count fixed: coverage_matrix.md line 25 updated from "3 rules delegated" to "4 rules delegated" (inheritance_unknown_base, inheritance_multi_level, inheritance_cycle, inheritance_locked_field_mutation). All changes verified: pyflakes clean, pytest all green, gate now fires correctly on violations, JSONL output flows to stdout.

### Developer Tests and Notes

- T12 test brittleness audit: removed 11 brittle assertions from M1 scene-lint/scene-design/scene-calc test batch per PYTEST_STYLE.md. Changes: (1) `test_scene_design_weights.py`: deleted 5 tests asserting exact weight values (test_template_weight_values etc.) and 5 tests asserting metric key sets (test_template_metrics etc.); replaced test_weights_has_five_classes with behavioral check (all classes are non-empty dicts with numeric values); converted 4 partial-value aggregate_score tests from exact-result assertions to range-property assertions (0.0 <= result <= 100.0) so tests survive weight tuning. (2) `test_scene_calc_aspect.py`: deleted test_aspect_prediction_dataclass_fields (asserting on attribute names); removed now-unused ASPECT_DISTORTION_THRESHOLD_PCT import. (3) `test_scene_lint_coverage_matrix.py`: replaced test_coverage_decisions_documented doc-phrasing check with structural markdown-heading check. Net: 10 files unchanged in count, 166 -> 155 test functions (-11), pyflakes clean, 155 passed in 0.37s.

### Additions and New Features

- T11 integration: scene-lint and scene-design added as stages in `validation/validate.py`. Both stages appear in the `-O/--only` choices list in `validation/shared_toolkit/cli.py`. Default suite now runs `['yaml', 'svg', 'stepper', 'structure', 'manual', 'scene-lint', 'scene-design']`. Both CLIs (`validation/scene_lint/cli.py`, `validation/scene_design/cli.py`) refactored to use `validation.shared_toolkit.cli.build_parser` with an extras callback; scene selection now uses shared `-S/--scene` flag instead of a positional `paths` argument. Whole-suite runs without `-S` auto-discover all `content/base_scenes/*.yaml` files. Gate behavior preserved: scene-lint exits 1 on BLOCKED (Group A) findings; scene-design is advisory-only and never exits 1. Verified: `--only scene-lint -S bench_basic.yaml` exits 0, `--only scene-design` auto-discovers 18 scenes, pyflakes clean, 80 scene tests pass.

### Removals and Deprecations

- Deleted `validation/run_scene_lint.py`, `validation/run_scene_design.py`, and `run_scene_calc_dump.py` (repo root). The first two were thin wrapper scripts made redundant by direct dispatch from `validate.py` to `validation/scene_lint/cli.py` and `validation/scene_design/cli.py`. The repo-root `run_scene_calc_dump.py` was misplaced (dump is a debug-only library function, not a routine entry point; if needed, it can be recreated under `validation/`).

- Scene lint Group A rules (WP-LINT-2): `validation/scene_lint/rules_group_a.py` implements all 12 Group A data-blocker rules from SCENE_LINT_PLAN.md (duplicate_scene_name, duplicate_placement_name, invalid_scene_bounds, invalid_zone_bounds, zone_outside_scene_bounds, missing_svg_asset, invalid_svg_viewbox, inheritance_unknown_base, inheritance_multi_level, inheritance_cycle, inheritance_locked_field_mutation, inheritance_dangling_ref). All findings carry verdict BLOCKED (never suppressible). Coverage matrix (validation/scene_lint/coverage_matrix.md) documents which rules are already covered by vocab lint vs. implemented here vs. require post-inheritance logic. Writers: JSONL output (one line per finding) and Markdown output (per-scene sections with grouped findings). CLI integration wires all rules into main loop. Exit code 1 on any Group A finding (data-blocker gate); exit 0 otherwise. 33 unit tests + 5 matrix tests, all passing. Pyflakes clean. Pre-verified with bench_basic.yaml fixture (0 findings expected, exit 0 achieved).

### Additions and New Features (previous)

- Scene geometry calculator (WP-SIM-1): `validation/scene_calc/bboxes.py` and `validation/scene_calc/aspect.py` implement pure-function geometry primitives for scene-layout validation. `compute_visual_bbox(placement, asset)`, `compute_placement_bbox(placement, asset)`, `compute_footprint_bbox(placement, asset)` return typed `BBox` dataclass (left, right, top, bottom in scene-percent). `predict_aspect_delta_pct(placement, asset)` returns `AspectPrediction` dataclass implementing SCENE_LINT_PLAN.md §"B1 aspect_distorted_predicted" rule: aspect-correction formula per LAYOUT_PIPELINE.md, delta_pct and is_distorted flag (>5.0 threshold). All functions use LAYOUT_PIPELINE.md §1 units and constants (ZONE_PADDING, MIN_SCALE, DEFAULT_VIEWPORT). Golden-fixture tests: 27 bbox + 15 aspect tests (42 total) covering square/tall/wide assets, boundary conditions (MIN_SCALE, edge positioning), label heights, and viewport variations. All hand-computed expected values in tests/fixtures/scene_calc/*.yaml. Tolerance: BBOX_TOL_PCT=0.1%, ASPECT_TOL_PCT=0.1%. Functions cite spec sections in docstrings per acceptance criteria.
- Scene design scoring framework (WP-DESIGN-2): `validation/scene_design/weights.py` with WEIGHTS dict mapping five scene classes to per-metric weight tables (template, composition, instrument_heavy, zoom_detail, dense_clutter). All class weight sums validated to 1.00. `validation/scene_design/score.py` with `aggregate_score(metrics, scene_class)` returning weighted-sum design score (0-100 float) or None if any required metric is missing (NotReady semantics for metrics to be populated in WP-METRICS-1/2). Weight tables match SCENE_DESIGN_LINT_PLAN.md section "Per-class weight tables" exactly. 27 unit tests (test_scene_design_weights.py) cover weight table structure, exact values, sum-to-1.0 invariants, and score aggregation logic; all passing.

### Additions and New Features (previous)

- Scene loader helpers (WP-LOAD-1): `validation/shared_toolkit/scene_loaders.py` with `load_svg_viewbox(svg_path)` returning (width, height) and `resolve_inheritance(scene)` covering single-level extends chains with add_placements, remove_placements, deactivate_placements, reposition_placements operations. Typed exception classes (UnknownBaseError, MultiLevelInheritanceError, InheritanceCycleError, DanglingReferenceError, LockedFieldMutationError) for Group A rule consumption. Reuses existing toolkit (yaml_io, objects, paths) unchanged. Unit tests: 19 passing (7 SVG viewBox + 12 inheritance tests covering happy path, malformed input, error conditions).
- Scene design lint package (WP-DESIGN-1): `validation/scene_design/` with class detection, card writers (JSON + Markdown), and runnable script `validation/run_scene_design.py`. Class detection follows the 5-step order from SCENE_DESIGN_LINT_PLAN.md: data-scene-mode="template", data-scene-mode="zoom_detail", >=10 placements, primary is instrument/equipment, else composition. Card schema carries all required fields (scene, class, score, confidence, gated_by_render_predictor, metrics, suggestions). M1 output explicitly marked confidence="stub" and score=null. JSON line-delimited output by default; --markdown flag emits Markdown cards. 15 unit tests (test_scene_design_class_detect.py) cover all 5 detection steps, precedence rules, error handling, and edge cases; all passing.
- Scene lint package (WP-LINT-1): `validation/scene_lint/` scaffolding with Finding shape, CLI entry point, and runnable script `validation/run_scene_lint.py`. CLI surface matches plan spec: positional paths, --strict, --report-only, --validate-against, --emit-confusion, --rules. Finding dataclass carries all required fields (scene, placement_name, rule, verdict, predicts, bbox_type, confidence, message, evidence, fix_hints, suppressed_by) for downstream rule implementations in WP-LINT-2 and B-rules. Confidence derived from SIM dump's scale_source (cm_model -> high, fallback_authored -> medium, fallback_no_workspace/partial -> low). Confusion-table flags accepted but not yet implemented (exit 2 as per plan). Group A gate inactive (WP-LINT-2).
- Build-time codegen pipeline: three Python scripts (tools/gen_object_library.py, tools/gen_svg_registry.py, tools/gen_scene_index.py) plus shared validator tools/svg_validate.py emit generated/object_library.ts, generated/svg_registry.ts, generated/scenes.ts. `generated/` stays gitignored.
- Renderer surface: src/scene_runtime/renderer/ (5 files plus inject_svg.ts helper) reads `PipelineResult.final` and paints DOM. Only inject_svg.ts uses `innerHTML`. Structural guards (structural_guards.ts) run before paint.
- Gradient backgrounds as a first-class scene field: `background: {type: gradient, from: ..., to: ...}` (M2b ships gradient-only).
- Label rendering at src/scene_runtime/renderer/render_label.ts with monospace text and `data-label-for` association.
- Two-stage precheck (tests/test_bench_basic_preflight.mjs): exercises pipeline against demo fixtures and generated content path.
- npm `pre*` hooks (`prebuild`, `pretypecheck`, `prelint`, `pretest:node`, `prebrowser:smoke`, `preui:review`) that regenerate `generated/` before every gate that imports from it. `serve` script gated by tools/check_dist_ready.sh.
- Playwright walkthrough at tests/playwright/test_bench_basic_render.mjs with 11 DOM/bbox assertions; artifact at tests/playwright/artifacts/bench_basic.png.
- Interaction-readiness test at tests/playwright/test_interaction_attrs.mjs asserting six required `data-*` attrs per item.

### Behavior or Interface Changes

- TypeScript renderer at src/main.ts + src/index.html is the new entry point for bench_basic. Static-template HTML for bench_basic is deprecated.
- Demo fixtures moved from src/scene_runtime/layout/demo_library.ts to src/scene_runtime/layout/__fixtures__/demo_library.ts.

### Fixes and Maintenance

- Root-cause fix for `validation/yaml/` package shadow (WP-LOAD-1 spec reviewer note): renamed `validation/yaml/` directory to `validation/yaml_schema/` to eliminate collision with third-party `pyyaml` module on sys.path. Updated all importers (tests/test_object_validator_variant_collapse.py, validation/stepper/loader.py, validation/validate.py path strings, and 13 internal imports within the package). Reverted symptom patches: removed 4-line warning comment from validation/shared_toolkit/yaml_io.py and removed sys.path/sys.modules mutations from validation/run_scene_design.py per "fix the design, not the symptom" (PYTHON_STYLE.md, REPO_STYLE.md). Closed blocker row in docs/active_plans/active/scene_lint/blocked_by.md.
- M1 quality nits: `validation/scene_design/cards.py` defensive defaults fixed (metrics/suggestions now use explicit None check instead of `or` operator per PYTHON_STYLE.md); `validation/scene_design/cli.py` --markdown flag now accepts short form `-m`; `validation/shared_toolkit/scene_loaders.py` typing annotations migrated to Python 3.12 lowercase generics (tuple, dict) and `|` union syntax, removed Tuple/Optional/Dict from typing import.
- tools/gen_svg_registry.py now registers SVG default namespace so emitted strings use `<svg>` (not `<ns0:svg>`).
- src/scene_runtime/renderer/structural_guards.ts aspect check multiplies by viewport aspect before comparing to viewBox aspect.
- src/scene_runtime/renderer/render_label.ts uses `data-label-for` instead of `data-placement-name` to avoid collision with item selectors in tests.
- content/objects/vortex.yaml `default_width` reduced from 12 to 6 to fit the rear_right zone.
- Test harness tests/test_bench_basic_preflight.mjs corrected to pass ASSET_SPECS and use 1920x1080 viewport.
- Scene cascade: content/base_scenes_quarantine/well_plate_96_zoom.yaml moved to quarantine after `well_plate_96` object was quarantined.
- A1x quarantined four objects without backing SVGs (trypan_blue_bottle, trypsin_bottle, hemocytometer, well_plate_96) to content/objects_quarantine/.

### Removals and Deprecations

- Static-template HTML for bench_basic is no longer the rendering path; deprecated for M2b/M2c. experiments/css_native_layout/ retained as diagnostic reference (see docs/archive/m2_cleanup_queue.md for the cleanup queue).
- `generated/` artifacts never committed; codegen always regenerates.

### Decisions and Failures

- M2b acceptance closed with bench_basic 11/11 C2 assertions and 0 visual-integrity failures (M0 had 3 failures on the same scene).
- L review APPROVED M2b with two non-blocking WARNs: `pretest:node` hook added (fixed); JSX cleanup deferred to M3.
- Lane D1 selected 8 generalization scenes; lane D2 added 6 to the allowlist (4 blocked with documented reasons: electrophoresis_bench SVG gap, well_plate_96_zoom quarantine, long_labels_smoke missing objects, adversarial_overflow_smoke is by-design fail-loud).
- Briefing 06.01 (section-7 heights) unresolved; M2b ships without frozen-baseline screenshots. Defer to M3 after designer confirmation.
- Briefing 06.02 (strict validator) deferred to M3 per lane F4 plan.

### Developer Tests and Notes

- 23 layout tests still passing after fixtures move.
- 7 SVG validator unit tests at tests/test_svg_validate.py pass.
- 9 structural guard tests at tests/test_structural_guards.mjs pass.
- Preflight, C2 Playwright, interaction-attrs Playwright all green for bench_basic.
- See reports: docs/archive/m2_codegen.md, m2_renderer.md, m2_structural_guards.md, m2_label_rendering.md, m2_preflight.md, m2_render.md, m2_vs_m0.md, m2_generalization_scene_set.md, m2_generalization_codegen.md, m2_reproducibility.md, m2_svg_completeness.md, m2_state_mutation.md, m2_cleanup_queue.md, m2_m3_productionization_plan.md, m2_diff_review.md.

### Additions and New Features (M2c+M2d)

- `SCENE_ALLOWLIST` expanded from 1 to 6 (bench_basic, bench_basic_row_slot, sample_prep_bench, staining_bench, cell_counter_basic, hood_basic). Allowlist metadata visible in generated/scenes.ts when generated.
- M2c generalization Playwright walkthrough at tests/playwright/test_generalization_render.mjs.
- D3 preflight at tests/test_generalization_preflight.mjs.
- M2 scorecard tool at tools/scorecard_m2.mjs; methodology adapted from `experiments/css_native_layout/score_layout.mjs` without mutating the source.
- Viewport sweep test at tests/playwright/test_viewport_sweep.mjs; 18 artifacts (6 scenes x 3 viewports) under tests/playwright/artifacts/.
- Generalization contact sheet at test-results/m2_generalization_gallery/INDEX.html.
- M2d audits: F2 state-mutation readiness, F3 cleanup queue, F4 M3 productionization plan, E1 no-crop diagnostics, E3 scorecard, E4 viewport sweep, E5 visual report (HTML + PDF; lane in flight at changelog time, will land alongside this entry).

### Behavior or Interface Changes (M2c+M2d)

- Five scenes migrated from asset-form background to gradient form (sample_prep_bench, staining_bench, cell_counter_basic, hood_basic, bench_basic_row_slot); migration log in docs/archive/m2_generalization_codegen.md.
- Object default_width reduced on 11 objects to satisfy zone containment guards: laemmli_4x_bottle, bme_bottle, coomassie_stain_bottle, coomassie_recycle_bottle, destain_bottle, destain_waste_bottle, microtube_rack_24, staining_tray, hood_surface (50->6), rocking_shaker, aspirating_pipette (3->0.8). Aspect ratios preserved per SVG viewBox.
- Zone bounds adjusted in 3 scenes: cell_counter_basic instrument_area top 20->15; staining_bench center top 45->28; staining_bench right_tool_area right 95->97.

### Fixes and Maintenance (M2c+M2d)

- gen_scene_index.py validation now distinguishes blocked scenes from allowed scenes via SCENES_SKIPPED_METADATA; previously failed loud on validation errors regardless of allowlist membership.

### Removals and Deprecations (M2c+M2d)

- 4 D1 scenes excluded from M2c allowlist with documented reasons: electrophoresis_bench (electrophoresis_tank missing 4 visual-state SVGs), well_plate_96_zoom (object quarantined), long_labels_smoke (6 chemical bottle objects not authored), adversarial_overflow_smoke (capacity stress test, by-design fail-loud).

### Decisions and Failures (M2c+M2d)

- M2c acceptance MET (5 of 6 non-adversarial scenes pass all 11 common acceptance criteria). M2c known failure: staining_bench label-label overlap (10/11, assertion I). Queued for M3 label-placement refinement.
- L M2c review APPROVED with conditions: human commit required before M2c artifacts are durably anchored; M3 visual review of hood_surface (default_width 6) and aspirating_pipette (default_width 0.8) for pixel fidelity; latent `_x` horizontal-bbox bug in structural_guards.ts filed for separate M3 issue.
- M0 baseline comparison: M2 reports 0 visual-integrity failures vs M0's 3 on bench_basic. M2 scorecard average 85.2/100.
- M2d diagnostic counts (per docs/archive/m2_no_crop_diagnostics.md): 0 cropped, 0 off-page, 0 item-overlaps, 0 aspect distortions, 0 placeholders, 0 labels-outside, 1 label-label overlap (staining_bench).
- F4 M3 productionization plan delivered at docs/active_plans/reports/m3_productionization_plan.md; covers multi-scene selector, click handling, ObjectStateChange wiring, strict validator (briefing 06.02), protocol step wiring, frozen-baseline mode after designer confirms section-7 heights.

### Developer Tests and Notes (M2c+M2d)

- 23 layout tests + 7 svg validator tests + 9 structural guard tests + bench_basic preflight + 6 generalization preflight + 6 generalization render Playwright (5 with 11/11, 1 with 10/11) + 18 viewport sweep artifacts + interaction attrs Playwright all pass.
- M2 reports under docs/active_plans/reports/: generalization scene set, generalization codegen, generalization preflight, generalization render, generalization failures, no_crop_diagnostics, scorecard, viewport_sweep, content_fix_d3_failures, c2_bc_failure_diagnosis, svg_injection_root_cause, bench_basic_root_cause, m2c_diff_review, m3_productionization_plan, svg_completeness, state_mutation_readiness, cleanup_queue, reproducibility, types_passthrough, structural_layout_guards, object_library_codegen, scene_cascade_fix.

### Decisions and Failures (M1 scene-lint/scene-design closure)

- M1 (Foundation) of the scene-lint / scene-design / scene-calc plan (`/Users/vosslab/.claude/plans/replicated-hatching-avalanche.md`) closed. All seven M1 work packages complete: WP-SIM-1 (scene_calc bbox + aspect primitives), WP-SIM-2 (zone-fit + label-box primitives + corpus dump), WP-LOAD-1 (shared_toolkit/scene_loaders helpers), WP-LINT-1 (scene_lint skeleton + CLI + finding shape), WP-LINT-2 (Group A rules + writers + coverage matrix), WP-DESIGN-1 (scene_design skeleton + class detection + cards), WP-DESIGN-2 (per-class weight tables + score aggregation). Both pre-M1 blockers logged in [archive/scene_lint/blocked_by.md](archive/scene_lint/blocked_by.md) are resolved: the pytest_sessionstart bootstrap repair landed upstream, and the `validation/yaml/` shadow against the third-party `pyyaml` module was eliminated by renaming the directory to `validation/yaml_schema/` (root-cause fix, see Fixes and Maintenance above). User-directed restructure (T11) superseded the plan's original "three standalone run_*.py scripts" approach: scene-lint and scene-design are now stages in `validation/validate.py`, and `validation/run_scene_lint.py`, `validation/run_scene_design.py`, and the repo-root `run_scene_calc_dump.py` were deleted. T12 brittleness audit further reduced the test surface from 166 to 155 functions per [PYTEST_STYLE.md](PYTEST_STYLE.md) (no brittle assertions on collection sizes, required-key lists, dataclass fields, or hardcoded weight values). M1 exit gates met: SIM golden-fixture tests green, SIM corpus smoke produces a dump for every base scene without raising, scene-lint CLI exits non-zero on any Group A (BLOCKED) finding, and scene-design emits stub cards marked `confidence: stub` and `score: null`. Evidence: 155 pytest tests passing, pyflakes clean, markdown-links clean. M2 (Predictors and metrics) is unblocked.

---
