# Roadmap

## Completed: protocol pedagogy and visible-UI workflows

The reusable shell, all five gestures, per-subpart state, protocol runners, and
visible browser walkthroughs are established. The 2026-08-03 pedagogy overhaul
adds range-specific laboratory tools, contamination controls, calculation and
observation decisions, visible experimental outcomes, and durable cell-culture
and SDS-PAGE continuity. All 31 generated protocol pages complete through the
visible interface; see
`docs/active_plans/reports/protocol_pedagogy_visual_resolution.md`.

## Current roadmap

The next protocol-quality work depends on explicit evidence or contract
decisions rather than another generic shell milestone:

- Supply the faculty-owned Bradford inputs, ladder product/load volume,
  one-gel apparatus values, and local microwave SOP recorded as B1-B4.
- Approve a closed conditional step-graph vocabulary before implementing B5.
- Decide whether selection candidates need a closed choice-role capability
  (B6), so decision scenes can retain visible experimental context without
  presenting every clickable context object as an answer.
- Re-run the optional SVG text-outline E2E with a working Inkscape installation.
- Continue evidence-led protocol expansion without weakening visible-action,
  state-continuity, or scientific-conservation gates.

Per-well material state plan status (dynamic-coalescing-flask.md, 2026-06-03)

The material plan is COMPLETE for per-well material state and rendering. Automated gates
GREEN. Per-well render proven via production Playwright harness (carboplatin -> #a719db
by `data-subpart-name`, no DOM hand-editing).

What shipped (M0-M4):

* M0: material spec split into 5 docs under docs/specs/MATERIAL_*.md.
* M0: SVG-namespacing/DOM-isolation contract (D13).
* M1: per-subpart state in Python stepper; 834 state_value_not_allowed -> 0.
* M1: D6 validator rule for structured well-plate objects.
* M1: materials.yaml scalar display_color sweep + validator flip.
* M1: gen_protocols.py scalar fix; MATERIAL_SENTINEL_ALLOWLIST narrowed to {empty, mixed}.
* M2: PATH-B geometry (96 wells); determinism test.
* M3: scalar color resolver (material_color.ts D3); generic subpart interpreter
  (subpart_visual_state_renderer.tsx); narrow store accessor (getSubpartStateField).
* Runtime store: accepts registry-backed subpart material_name (mirrors stepper D1).
* M4: production render-path per-well color proven; walkthrough spec retained, honestly
  reports blocker.

Visible-UI per-well-protocol walkthrough:

* Completed. The in-flow set-point editor supplies the visible `adjust`
  affordance, and the per-well protocols complete through the same
  runtime-authoritative validation path as the other gestures.

Non-goals of this plan:

* Amount-layer (volume-driven) well rendering: wells rendering fill level by
  `material_volume` value, not just material_name color tint.
* Dark-mode rendering: per-subpart renderer uses the single scalar `display_color`;
  light/dark variants are not in scope.
* Anchor/vessel-fill render path for bottles and flasks: the CSS/SVG recolor path
  (using `anchor_liquid_clip`/`anchor_liquid_bounds`) awaits the SVG M5 lookup seam.

Future (task #27):

* Declared registry-backed field affordance: retire the [empty, mixed] syntactic seam
  in well_plate_96.yaml by making the registry-backed field explicitly declared in the
  object schema. No runtime behavior change required; schema + validator + generator
  changes only.

Longer-term roadmap

* Add richer lab gestures beyond click and adjust as needed.
* Add results screen and scoring display.
* Add better shell styling once functional coverage is stable.
* Expand protocol library coverage.
* Add optional debug panel for protocol state snapshots.
* Improve authoring diagnostics for protocol / scene mismatches.
* Consider mobile / touch support only after desktop protocol flow is stable.

Note: keyboard navigation, ARIA, focus management, and screen-reader support for shell
controls are deferred. See the "Accessibility scope" subsection in
[PRIMARY_DESIGN.md](PRIMARY_DESIGN.md) for the current scope boundary and the
conditions under which accessibility work would be re-prioritized.


Planned features and improvements for the cell culture simulation game.

## Delivered

- Two-scene workspace: hood (sterile work) and bench (equipment) peer scenes
- 96-well plate geometry with 8-point carboplatin dose response and metformin sensitization
- 25-step protocol across 3 days (Day 1 split/count/seed, Day 2 dilute/treat, Day 4 MTT/read)
- 22 hood reagents and equipment organized in tab-stop clusters
- 6 bench instruments: centrifuge, water bath, vortex, cell counter, microscope, incubator
- Depth-based visual layering (back/mid/front tiers with opacity and brightness)
- Cell model with metformin sensitization (2x IC50 shift)
- MTT assay readout with OD560 absorbance and realistic noise
- Protocol-fidelity scoring (5 categories: dilution, plate map, timing, MTT technique, absorbance plausibility)
- Dilution prep validation (intermediate, low-range, high-range, metformin stocks)
- Day timeline state machine (day1/day2/day4 with incubator-gated transitions)
- Capability-based scene dispatch migration (Patches 1-16, 2026-05-08 to 2026-05-09; archived plan: [archive/scene_capability_architecture_2026-05-09.md](archive/scene_capability_architecture_2026-05-09.md))
- Scene render-ownership migration: render moved from flat `src/scenes/{hood,bench,microscope,plate,incubator}.ts` source modules into per-scene adapters under `src/scenes/<scene>/<scene>.ts`; `SceneAdapter.render(ctx)` made required; new first-class `plate_reader` adapter; helper duplicates consolidated into `shared/liquid_transfer.ts` and `shared/legacy_tokens.ts`; `sceneRouter` flag retired (decision: REMOVED, see "sceneRouter resolution" below). Completed 2026-05-09 (Patches A1-B4; archived plan: [archive/scene_render_migration_2026-05-09.md](archive/scene_render_migration_2026-05-09.md)).
- Scene migration closeout (Plans A/B/C): generated TS moved out of `src/content/` into gitignored `generated/`; four authored facades (`src/svg_assets.ts`, `src/scene_configs.ts`, `src/inventory.ts`, `src/protocol.ts`); scene YAML extended schema with formal typed `sceneBounds` and `layoutRules.label*`; bench and hood layout migrated to scene YAML and `src/bench_config.ts` + `src/hood_config.ts` deleted; bench split into render/dispatch/effects siblings; microscope manual hemocytometer extracted into a sibling module; hood compatibility-token ladder folded into K2 completionPath dispatch; `src/scenes/shared/legacy_tokens.ts` deleted. Completed 2026-05-09 (Patches A1-A6, B1-B12, C1-C5; archived plan: [archive/scene_migration_completion_2026-05-09.md](archive/scene_migration_completion_2026-05-09.md)).

## sceneRouter resolution (recorded 2026-05-09)

The per-protocol `sceneRouter` flag was migration scaffolding from the
2026-05-08 capability migration. Patch B3 of the render-ownership
migration applied the decision rule from the archived plan and resolved
the flag as **REMOVED**:

- Every protocol used `driver` (no `legacy` opt-out remained).
- Patch B2 retired the alternative implementation (the flat source
  modules), so `legacy` had no backing path.
- No roadmap product feature would consume the field.

The flag, the `SceneRouterMode` type, and the `resolveSceneRouter`
function are gone. There is one render and one dispatch path. The
field is intentionally absent rather than missing by oversight.

## Future enhancements

## Glossary doc (planned)

A single repo-wide `docs/GLOSSARY.md` defining the wet-lab +
simulation vocabulary used across EVERY lab protocol in this
repo, not just the MTT/OVCAR8 work that triggered it. Scope spans
cell culture (passage, seeding, trypan blue counting), drug
dilutions (carboplatin / metformin / serial dilution math),
colorimetric assays (MTT, formazan), electrophoresis (SDS-PAGE,
ladder, lanes, running buffer, destain), pipetting mechanics
(draw / dispense / aspirate / trituration), instrumentation
(multichannel pipette, plate reader, centrifuge, vortex,
microscope, incubator), and the simulation-side vocabulary
(material_volume well-total semantics, subpart groups, scene_op
primitives, learning block, mini-protocol vs sequence runner).

Triggering incident: the MTT cleanup work (2026-05-16) where
multiple terms drifted within a single protocol family (MTT
etymology, aspirate vs draw vs dispense, formazan identity, well-
total volume semantics, trituration). Same drift class is likely
in every other lab area; the glossary prevents repeat work.

Acceptance criteria:

- Single file at `docs/GLOSSARY.md` indexed from `README.md`.
- Covers terms used by EVERY lab protocol family in
  `content/protocols/`, not a one-lab subset. Group by domain
  (Cell culture, Drug dilution, Colorimetric assay,
  Electrophoresis, Pipetting mechanics, Instrumentation,
  Simulation-side authoring) for scannability.
- Each term: one-line definition, a "do" usage, a "do not
  confuse with" cross-reference where relevant.
- Cross-linked from `docs/MARKDOWN_STYLE.md` and `AGENTS.md` so
  authors hit it before introducing new vocabulary.
- Cross-linked from existing authoring vocabularies
  (`docs/specs/PROTOCOL_VOCABULARY.md`,
  `docs/specs/SCENE_VOCABULARY.md`,
  `docs/specs/OBJECT_VOCABULARY.md`) so spec layers reference
  glossary instead of restating definitions.
- Glossary tested by a markdown link check; no orphan terms.

Surfaced cleanups that would land alongside:

- [protocol_manual.py](../validation/manual/protocol_manual.py) already enforces
  "draw" for pipette loading + "aspirate and remove" for vacuum-to-waste;
  glossary ratifies the convention.
- The protocol validator now rejects "aspirate" in a learner-facing loading
  prompt unless the step uses the dedicated vacuum aspirating pipette. The
  current corpus is clean; retain that gate for new protocol content.
- Authoring vocabularies (PROTOCOL_VOCABULARY, SCENE_VOCABULARY,
  OBJECT_VOCABULARY) shrink as they cite the glossary.

Defer until the next vocabulary drift incident in a different
lab family (the MTT incident alone is insufficient justification
for a one-lab glossary; the cross-lab pattern is the value).

## Next deferred item: split `src/layout_engine.ts` (promoted 2026-05-09)

Promoted to the top of the deferred queue by the scene migration closeout
(Patch C5). `src/layout_engine.ts` is ~857 LOC and coherent at its current
size, but it is the next decomposition target after the scene migration:
split into `layout_assets.ts` + a slimmed `layout_engine.ts`. Revisit if it
crosses 1000 LOC, or pair it with any further layout-policy work in
`src/scenes/shared/scene_layout.ts`. Backref:
`~/.claude/plans/sharded-imagining-diffie.md` (origin of the split idea)
and the closeout archive
[archive/scene_migration_completion_2026-05-09.md](archive/scene_migration_completion_2026-05-09.md).

## Scene adapter responsibility-seam decomposition (closed 2026-05-09)

Closed by the scene migration closeout (Plans A/B/C). Concrete outcomes:

- Hood interaction-ladder cleanup: folded into K2 completionPath dispatch (Patch C1).
- Bench dispatch decomposition: bench split into `render.ts` / `dispatch.ts` / `effects.ts` siblings with `bench.ts` as the thin SceneAdapter shell (Patch C2).
- Microscope dispatch decomposition: manual hemocytometer flow extracted into a sibling module so the automated and manual paths no longer share a single dispatcher (Patch C3).
- `buildLegacyToken` call sites reached zero; `src/scenes/shared/legacy_tokens.ts` deleted (Patch C4).
- Plate / incubator: surfaces remain small; revisit only if they grow.

Archived plan: [archive/scene_migration_completion_2026-05-09.md](archive/scene_migration_completion_2026-05-09.md).

## Hood setup phase

- Add a pre-protocol step where students arrange equipment inside the biosafety hood themselves
- Items start outside or on a staging area; students drag each into the hood workspace
- Teach sterile field layout: clean-to-dirty direction, airflow awareness, spacing
- Score placement based on proper technique (e.g., not blocking rear vents, waste on dirty side, spacing items)
- Could serve as an intro tutorial before the main cell culture protocol

- **Split `src/layout_engine.ts` (857 LOC) into 2 modules: `layout_assets.ts` + slimmed `layout_engine.ts`.** Coherent at
  current size; revisit if it crosses 1000 LOC. Some of this logic moves into `src/scenes/shared/scene_layout.ts` during this
  plan; the residual layout engine stays where it is.
- **Add `tests/types/` with `Expect<Equal<...>>` scaffold + 2 type-test files for `ProtocolStep` and `CompletionPath`.** Wire
  into all three build scripts. Would have caught the K2 drift at compile time.
- **Capability contract type tests.** When the type-test suite lands, add a third file that asserts every capability module
  conforms to the `SceneCapability` interface and every YAML scene config conforms to the `SceneConfig` schema. This is the
  type-level safety net for the new system.

## Capability-based scene architecture (added 2026-05-08)

Items below were deferred from the capability-based scene architecture refactor plan
(`~/.claude/plans/sharded-imagining-diffie.md`). They are tracked here so they survive
the migration and surface during planning.

### Deferred work items

- **Add `tests/types/` with `Expect<Equal<...>>` scaffold + 2 type-test files for `ProtocolStep` and `CompletionPath`.**
  Wire into all three build scripts. Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **Capability contract type tests.** When the type-test suite lands, add a third file that asserts every capability module
  conforms to the `SceneCapability` interface and every YAML scene config conforms to the `SceneConfig` schema.
  Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **Scene YAML validator pytest.** Replace the one-time manual experiment in MS-FOUNDATION with an automated builder test
  that asserts a corpus of malformed scene YAMLs fail loudly and a corpus of valid ones load cleanly. Add once at least one
  real scene YAML exists. Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **Move scene YAML to `src/content/scenes/` if it becomes author-facing content.** Currently lives beside the adapter under
  `src/scenes/<scene>/`; if scenes become protocol-authored content, relocate in a separate migration.
  Backref: `~/.claude/plans/sharded-imagining-diffie.md`.

### Locked-decision reminders (guardrails)

- **Mini-protocol failures are design evidence, not nuisance failures.** If a mini-protocol fails during a scene migration,
  fix the scene model or capability boundary before proceeding. Do not patch around the failure.
  Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **`sceneRouter` was migration scaffolding, not a product feature.** Resolved 2026-05-09 (Patch B3) as REMOVED; see "sceneRouter resolution" above.
  Do not reintroduce the flag or a near-equivalent without an explicit product reason.
  Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **Patch report contract.** Every subagent patch report must answer 3 questions in order: (1) what changed? (2) which
  mini-protocol (or full protocol) proves it? (3) which legacy path still exists?
  Backref: `~/.claude/plans/sharded-imagining-diffie.md`.
- **Adapter LOC budgets are warning lights, not gates.** If an adapter exceeds budget, classify the excess (capability
  candidate? scene-specific? unrealistic budget?) and act on the classification -- do not squeeze code purely to hit the
  number. Backref: `~/.claude/plans/sharded-imagining-diffie.md`.

## Deferred cleanups (post 2026-05-09 render migration)

The render-ownership migration (Patches A1-B4) and the scene migration
closeout (Plans A/B/C, Patches A1-A6 + B1-B12 + C1-C5) cleared the layout
duplication item: `src/bench_config.ts` and `src/hood_config.ts` were
retired and bench/hood layout is now sourced from scene YAML.

The next deferred layout-engine item is the `src/layout_engine.ts` split
described in "Next deferred item" above.

## Deferred scene-diagnostic statistics (added 2026-05-29)

The scene diagnostic tools (`tools/scene_stats.mjs`, `tools/scene_to_png.mjs`)
currently report render-yield and the easy diagnostics. The following richer
statistics are deferred for later passes:

- Browser-event counts per scene.
- Exact-union coverage of the scene area.
- Severe-overlap and occlusion detection.
- Stability scoring and unstable-layout flags.
- Balance scoring across the scene area.
- Zone-coverage metrics.
- Contrast checks.
- Interaction-readiness scoring.
- Fuller item labels in the stats output.
