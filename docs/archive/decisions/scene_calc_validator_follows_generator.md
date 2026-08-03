# Decision: scene_calc validators follow the generator, not a shadow model

Status: RATIFIED (architect ruling)
Date: 2026-05-29
Scope: validation/scene_calc, validation/scene_lint, validation/scene_design,
layout schema (width_scale / fudge), pipeline/gen_scene_index.py interaction.

This is a design ruling only. No code, scene, object, or validator was edited
to produce it. It defines the durable design and an ordered plan a coder
executes next.

## Problem (verified)

The repo has two layout implementations that drifted apart.

1. Authoritative path (the generator + runtime). `pipeline/gen_scene_index.py`
   emits scene structure into `generated/scenes.ts`. The real layout math runs
   in the TypeScript layout pipeline under `src/scene_runtime/layout/`
   (`run_pipeline.ts` orchestrates `resolve_inheritance.ts`,
   `scale_to_real_world.ts` cm-model sizing, `horizontal_layout.ts` align_stop
   tab-stops, `vertical_layout.ts`, `layout_labels.ts`, `clamp_scene_bounds.ts`).
   `tools/scene_to_png.mjs` renders the shipped scenes through that exact
   pipeline in a browser and writes real DOM bounding boxes to
   `<scene>.stats.json` via `getBoundingClientRect` in `collect_rendered_items`
   and `collect_labels`.

2. Shadow path (the validator). `validation/scene_calc/dump.py` is a separate
   Python re-implementation of layout geometry. It is consumed by
   `validation/scene_lint/` (group B rules) and `validation/scene_design/`
   (all metrics). It does NOT do what the authoritative pipeline does:
   - It does not resolve scene inheritance (`extends:`). It reads one scene
     YAML in isolation, so every per-protocol scene that inherits a base scene
     emits `skipped_error` placements. All 25 protocol scenes are effectively
     BLOCKED.
   - It does not apply the cm-model. `_synthesize_placement_inputs` sizes items
     from `layout.default_width` (scene-percent) times an authored
     `width_scale`, never from `display_width_cm * px_per_cm`. This produces the
     ~44% bogus `aspect_distorted` deltas.
   - It does not apply align_stop tab-stops. It anchors every item at the zone
     center (`zone_cx`, `zone_cy`), so it invents item/label overlaps that the
     real horizontal layout never produces.

A prior agent muted scene-lint with suppressions to hide these false positives.
That was the wrong fix (hiding the symptom) and has been reverted.

## Binding user principles applied

- The generator wins. `scene_calc` is only a validator. When the validator
  disagrees with the generator/runtime geometry, the validator is wrong by
  definition. A validator must never become a second source of truth for
  layout.
- No override escape hatches. Object size has exactly one source:
  `display_width_cm * px_per_cm` (SCALING_MODEL.md). Per-placement `width_scale`
  and `fudge` are escape hatches and are forbidden (PRIMARY_DESIGN.md vocabulary
  closure: "Closure over openness", "Flat primitives over nested blobs",
  "New meaning requires a vocabulary edit").

## Ruling 1: single source of truth for validator geometry

Decision: Option B. The geometry validators consume the real rendered
bounding boxes already produced by `tools/scene_to_png.mjs`
(`<scene>.stats.json`). `validation/scene_calc/dump.py` and its geometry
helpers (`bboxes.py`, `aspect.py`, `zones.py`, `labels.py` as geometry
synthesizers) are retired as a layout model. The drift class is eliminated
because there is then exactly one place that computes layout (the TS pipeline),
and the validator reads its output rather than re-deriving it.

### Why B over A and C

- The three drift causes are all "the Python model computes geometry
  differently from the runtime." Any approach that keeps Python computing
  geometry (re-deriving from YAML) only narrows the gap; it does not close the
  drift class. Two implementations of the same math will diverge again the next
  time the TS pipeline changes (a new layout stage, a tweaked clamp, a new
  px_per_cm). The durable fix is one implementation.
- Option A (have the generator/pipeline emit a computed-layout artifact the
  validator ingests) is the right SHAPE but the wrong layer to source from
  today. The numbers that matter for visual review are the rendered pixel
  boxes after the browser lays out flex/grid, applies `object-fit: contain`,
  wraps labels, and clips. `scene_to_png.mjs` already captures exactly those
  via `getBoundingClientRect`. The PRIMARY_DESIGN "never crop" rule is itself
  defined against the rendered asset bbox vs the parent card; that is a DOM
  measurement, not a pre-render prediction. A pipeline-only artifact would
  still be a prediction of the browser, i.e. a third model that can drift from
  the browser.
- Option B reuses an artifact the repo already generates on every render run.
  No new emit step, no new schema to keep in sync.

### The one allowed nuance (documented, not a hybrid escape hatch)

Pure Option B has one real gap: a fast lint that does not want to spin up
Chromium. Today `scene_lint`/`scene_design` run as Python without a browser.
Resolve this by execution policy, not by keeping the shadow model:

- The browser render (`scene_to_png.mjs --all`) is the single geometry
  producer. It already runs in the build/verify path and writes
  `test-results/scenes/<scene>.stats.json` plus `summary.json`.
- `scene_calc` becomes a thin loader: it reads the rendered `stats.json` for a
  scene and exposes the same dict shape the group B rules and design metrics
  already expect (`visual_bbox`, `placement_bbox`, `footprint_bbox`,
  `label_bbox`, `aspect_delta_pct`, `scale_source`, zone `inner_rect`). It
  performs no layout math. Any derived quantity that is pure post-processing of
  rendered boxes (e.g. overlap area between two rendered rects, percent-empty
  from rendered coverage) stays in the rules layer, because it is arithmetic on
  truth, not a re-derivation of layout.
- If a stats.json is missing or stale for a scene, the validator fails loudly
  (PYTHON_STYLE "fail on missing required data"); it does NOT fall back to
  re-deriving geometry. The fix is to render, not to predict.

This is not Option C/hybrid in the "two geometry models" sense. There remains
exactly one geometry producer (the browser pipeline). The validator is pure
consumer.

Coordinate-space note for the coder: the rendered boxes are CSS pixels with a
top-left origin; the legacy dump schema mixed scene-percent placement boxes
(`{x,y,w,h}`) with edge-coordinate zone rects (`{left,right,top,bottom}`).
The rules only compare boxes against each other and against zone rects, and
thresholds are ratios/percentages (`ASPECT_DISTORTION_THRESHOLD_PCT`,
percent-empty, overlap fraction), so the rules are unit-agnostic as long as
every box fed to a given rule shares one coordinate space. The loader must
therefore present all four placement boxes AND the zone `inner_rect` for a
scene in one consistent space (pixels, from the same render), and convert the
zone rect to pixels from the rendered `#scene-root` box rather than from raw
YAML scene-percent. Do not mix a YAML-percent zone rect with pixel placement
boxes.

## Ruling 2: width_scale and fudge

Decision: REMOVE both as authoring/override surfaces.

- `fudge`: remove entirely. It is documented in SCALING_MODEL.md as an optional
  per-item final-tweak multiplier (`width_scale *= fudge`). It appears in zero
  content files today. It is a textbook escape hatch. Remove it from the schema,
  from `scale_to_real_world.ts` (the `* fudge` term and the `fudge` field on the
  layout type), and from SCALING_MODEL.md. Strike the "Optional fudge factor"
  section.

- `width_scale` as a per-placement override: remove. It appears in 7 scene
  files (placements), enumerated below. Task #13 is already removing those
  placement overrides and reverting the `scale_to_real_world.ts` multiplier so
  authored `width_scale` is ignored. This ruling ratifies that direction and
  extends it: once the multiplier is reverted, also remove the `width_scale`
  field from the placement/object layout schema and from
  `gen_scene_index.py` override-emission, so an author cannot reintroduce it by
  editing YAML alone (vocabulary closure). The shadow dump's own
  `width_scale` read (`_synthesize_placement_inputs`, default 1.0) dies with
  `dump.py`.

- Legitimate non-override use to PRESERVE: `_width_scale` as an INTERNAL,
  pipeline-computed quantity. `scale_to_real_world.ts` derives `_width_scale`
  from the cm-model (`(cm * px_per_cm) / (def * PX_PER_SCENE_PERCENT)`), and
  `run_pipeline.ts` mutates `_width_scale` during the convergence/shrink loop
  (`p._width_scale * shrinkFactor`). That is an internal layout variable
  (underscore-prefixed, never authored, never read back into YAML). Keep it.
  The rule is precise: NO authored `width_scale` field anywhere (object layout
  or placement layout); the internal `_width_scale` computed quantity stays.

- `display_width_cm` per-placement: out of scope of "override removal" but note
  for the coder: the single sizing source is the object-level
  `display_width_cm`. If a placement-level `display_width_cm` override exists in
  the schema, it is the same escape-hatch class and should be removed too;
  size belongs to the object, scene chooses px_per_cm via workspace. (Verify
  during implementation; do not assume it exists.)

Files carrying authored `width_scale` today (Task #13 territory, listed so the
schema-removal step can assert zero remaining occurrences):

- content/base_scenes/bench_basic.yaml
- content/protocols/cell_culture/drug_dilution_setup/scenes/dilution_workspace.yaml
- content/protocols/cell_culture/drug_dilution_setup/scenes/bench_setup.yaml
- content/protocols/cell_culture/passage_pellet_reseed/scenes/centrifuge_workspace.yaml
- content/protocols/cell_culture/mtt_plate_reaction/scenes/incubator_workspace.yaml
- content/protocols/cell_culture/mtt_solubilization_readout/scenes/bench_workspace.yaml
- content/protocols/cell_culture/mtt_solubilization_readout/scenes/plate_reader_workspace.yaml

## Ordered implementation plan

Do not start steps 3+ until Task #13 (placement-override removal + engine
revert) has landed; this plan builds on it and must not contradict it.

### Step 0 (gate): confirm Task #13 landed

- Verify `scale_to_real_world.ts` no longer multiplies by authored
  `width_scale` (lines ~42-44 reverted) and no longer reads `fudge`.
- Verify the 7 scenes above no longer carry `width_scale`.
- Verification: `grep -rn "width_scale" content/` returns only internal/no hits;
  `grep -n "fudge\|width_scale" src/scene_runtime/layout/scale_to_real_world.ts`
  shows neither authored term.

### Step 1: remove fudge + authored width_scale from schema and generator

- Files: `src/scene_runtime/layout/types.ts` (drop `fudge` and authored
  `width_scale` from the layout/placement-layout type; keep internal
  `_width_scale`), `pipeline/gen_scene_index.py` (`emit_scene_ts` layout-override
  emission loop, lines ~712-721: stop emitting `width_scale`/`fudge` keys; if a
  scene still carries them, fail loudly rather than pass them through),
  `docs/specs/SCALING_MODEL.md` (strike "Optional fudge factor"; correct the
  `width_scale = ...` narration so it describes the internal computed
  `_width_scale`, not an authored field).
- Verification: `npx tsc --noEmit -p tsconfig.json`; rebuild scenes
  (`bash build_github_pages.sh` or `pipeline/build_generated.sh`); rebuilt
  `generated/scenes.ts` contains no `fudge`/authored `width_scale`.

### Step 2: render the authoritative geometry

- Run `node tools/scene_to_png.mjs --all` to populate
  `test-results/scenes/<scene>.stats.json` + `summary.json` for every emitted
  scene.
- Verification: `summary.json` lists every emitted manifest scene; per-protocol
  (inherited) scenes are populated, NOT skipped (the inheritance gap that
  blocked the shadow model does not exist here, because the browser ran the
  real pipeline).

### Step 3: rewrite scene_calc as a stats.json loader

- Replace the geometry-synthesizing body of `validation/scene_calc/dump.py`
  with a loader that reads `test-results/scenes/<scene>.stats.json` and returns
  the dict shape the consumers already expect (placements with `visual_bbox`,
  `placement_bbox`, `footprint_bbox`, `label_bbox`, `aspect_delta_pct`,
  `scale_source`; zones with `inner_rect`), all in one consistent pixel space
  (see coordinate-space note above). Delete the layout synthesis helpers
  (`_synthesize_placement_inputs`, `_determine_scale_source`, the
  `compute_*_bbox` / `predict_aspect_delta_pct` / `zone_inner_rect` /
  `estimate_label_box` call sites). Retire `bboxes.py`, `aspect.py`,
  `labels.py`, `zones.py` as geometry models (delete or reduce to pure
  consumers; git history is the archive per REPO_STYLE).
- Map fields the renderer must expose: `scene_stats.mjs` should compute and
  emit `aspect_delta_pct` per item (rendered asset bbox vs intended asset
  aspect from the SVG viewBox) and a per-item `scale_source` derived from the
  pipeline diagnostics (`cm_model` / `fallback_*` / `skipped_error`). If those
  fields are not yet in stats.json, ADD them to `scene_stats.mjs` (the producer)
  rather than recomputing them in Python. This keeps one producer.
- Missing/stale stats.json: raise a clear error naming the scene and the
  expected path. No geometry fallback.
- Verification: `pytest tests/` for any scene_calc unit tests; run
  `validation/scene_lint/cli.py` and `validation/scene_design/cli.py` on a
  known-good scene and confirm the previously-bogus `aspect_distorted`,
  item/label overlap, and `skipped_error`-on-inherited-scene findings are gone.

### Step 4: confirm validator now agrees with the render

- Pick 2-3 scenes (one base, one inherited per-protocol, one bench multi-item
  row) and confirm scene_lint findings match what the PNG actually shows
  (cross-check against the rendered PNG in `test-results/scenes/`).
- Verification: zero false `aspect_distorted` on cm-model scenes; zero
  `skipped_error` on inherited scenes; overlap findings correspond to real
  overlaps visible in the PNG.

### Step 5: docs + changelog

- Update `docs/specs/SCENE_LINT.md` and `docs/specs/SCENE_DESIGN.md` to state
  that geometry comes from the rendered stats.json (single producer:
  `scene_to_png.mjs` -> `scene_stats.mjs`), not from a Python layout model.
- Update `docs/CODE_ARCHITECTURE.md` / `docs/FILE_STRUCTURE.md` if they describe
  scene_calc as a geometry computer.
- Add a `docs/CHANGELOG.md` entry (Behavior or Interface Changes + Removals:
  removed `fudge` and authored `width_scale`; scene_calc now reads rendered
  geometry). Leave the commit to the human.

## Risks

- Browser dependency for lint. scene_lint/scene_design now require a prior
  render. Mitigation: they already run in a build/verify context that has
  Chromium (Playwright is a dev dep); the loader fails loudly if stats.json is
  absent, which is correct behavior, not a regression to hide.
- stats.json schema additions. `scale_source` and per-item `aspect_delta_pct`
  may not exist in stats.json yet and must be added to `scene_stats.mjs`. Risk
  is low (additive) but it is real work, not a pure delete.
- Coordinate-space bugs. The rules were written against a mixed
  percent/edge-coordinate schema. The coder must ensure all boxes fed to a
  given rule share one pixel space (see note). A unit test per rule on a small
  fixture scene de-risks this.
- Confidence weighting. `_confidence_from_scale_source` keys off the four-value
  enum. Preserve that enum's meaning when sourcing `scale_source` from pipeline
  diagnostics so confidence levels stay stable.
- Interaction with in-flight Task #13. Step 0 gates on it. If #13's engine
  revert changes the meaning of `_width_scale`, re-confirm Step 1 keeps the
  internal computed variable intact.

## Out of scope / explicitly not done here

- No edits to code, scenes, objects, or validators were made.
- No commit, no changelog entry written yet (Step 5 does that during
  implementation).
- The `align_stop`, `depth_tier`, and zone vocabulary are preserved unchanged.
