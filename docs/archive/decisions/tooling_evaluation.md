# Tooling evaluation for the virtual lab protocol simulation

## Context

This document evaluates every tool proposed for the SolidJS-based YAML-driven lab
protocol simulation, with pros, cons, and a fit verdict grounded in the actual
repo. It exists because the recommended "standard SolidJS stack" overlaps heavily
with what is already built and partly conflicts with deliberate, documented
architecture decisions. The goal is a single reference an author can scan before
adding any dependency.

## How to read the verdicts

- **Already done** -- present in the repo; adding the tool is redundant.
- **Adopt-candidate** -- genuine gap; worth a focused plan.
- **Conditional** -- only valuable under a specific constraint stated inline.
- **Skip** -- cost exceeds benefit against this architecture.
- **Reject** -- conflicts with a contract invariant.

## Architecture facts the verdicts rest on

- UI: SolidJS in heavy use, confined to `src/shell/`,
  `src/scene_runtime/renderer/`, `src/scene_runtime/state/`.
- State: Solid `createStore` + `produce` in
  `src/scene_runtime/state/scene_store.ts`.
- Build: Python codegen to `generated/*.ts`, then esbuild three entries
  (`pipeline/build_main_bundle.mjs`, `esbuild-plugin-solid`), then Python
  per-protocol HTML emit. Documented canonical shape in
  [../../TYPESCRIPT_STYLE.md](../../TYPESCRIPT_STYLE.md).
- YAML is compile-time only. The browser never parses YAML.
- Schema truth: `validation/yaml_schema/constants.py`; TS hand-mirror in
  `src/shell/adapter/types.ts`; load-time author check in
  `src/scene_runtime/protocol/authored_value_check.ts`.
- Tests: `node --test` via tsx (`tests/test_*.mjs`), pytest (`.py`), Playwright
  (browser evidence is required by contract item 4).
- SVG: normalized by `tools/normalize_svg_v2.py`
  ([../../specs/SVG_PIPELINE.md](../../specs/SVG_PIPELINE.md)); assets are
  YAML-declared and placed by the layout engine (contract item 3).
- CSS: single global `src/style.css` plus a CSS content-policy check.

## Summary table

| Tool | Category | Verdict |
| --- | --- | --- |
| SolidJS | UI/runtime | Already done |
| Solid stores | State | Already done |
| SVGO | SVG hygiene | Skip unless folded into existing pipeline |
| Generated Valibot/Zod guard | Runtime validation | Adopt-candidate (must be generated) |
| Ladle | Component preview | Adopt-candidate (dev-only) |
| Vitest | Unit tests | Conditional (only with component tests) |
| Solid Testing Library | Component tests | Conditional (supplements Playwright) |
| localStorage | Progress save | Adopt-candidate (when feature scoped) |
| esbuild watch dev script | Dev DX | Adopt-candidate (cheap HMR substitute) |
| UnoCSS / Tailwind | Styling | Skip (low value) |
| Storybook | Component preview | Skip (heavy; Ladle lighter) |
| Vite | Build/dev | Skip (migration cost > benefit) |
| Vitest migration of existing tests | Tests | Skip |
| XState | Interaction state | Skip (contract prefers flat primitives) |
| TanStack Router | Routing | Skip (DOM-root + per-protocol HTML) |
| TanStack Query | Data fetching | Skip (no runtime fetch) |
| yaml runtime loader | YAML at runtime | Reject (compile-time only) |
| vite-plugin-solid-svg | SVG-as-component | Reject (contract item 3) |
| SolidStart | Meta-framework | Reject (no SSR/routing/server need) |
| SvelteKit | Meta-framework | Reject (different UI runtime, blurs layers) |
| `src/protocol_ui/` affordance layer | Gesture-to-control abstraction | Adopt (the real UI simplifier) |
| Kobalte | Solid-native headless primitives | Adopt-candidate (pick ONE headless lib) |
| Ark UI for Solid | Cross-framework headless primitives | Alternative to Kobalte (not both) |
| Floating UI (Solid bindings) | Object-anchored coach marks | Adopt-candidate (narrow) |
| `@thisbeyond/solid-dnd` | Drag gestures | Conditional (when a drag protocol is scoped) |
| solid-motionone / Motion for Solid | Object motion polish | Conditional (polish only) |
| svg-pan-zoom / panzoom | Zoomable structured surface | Skip for whole scene; narrow-use only |
| Zag.js | Low-level widget state machines | Skip (subsumed by Kobalte/Ark) |
| `@dschz/solid-flow` | Node/flow editor | Skip for runtime (authoring tool only) |
| SVG.js / direct SVG manipulation | Mutate scene SVG | Reject for placement; conditional for subpart internals |
| SAT.js | 2D overlap detection utility | Adopt-candidate (deterministic, pure) |
| elkjs / ELK | Constraint layout for one dense zone | Conditional (determinism caveat) |
| D3-force | Optional label/overlap relax pass | Conditional (determinism caveat) |
| rectangle-packer | Inventory/tray/shelf packing | Conditional (inventory-like only) |
| Cytoscape.js / Dagre | Graph/diagram layout | Skip for scene (authoring/debug only) |
| ts-pattern | Value-matching at dispatch seams | Conditional (exhaustiveness already enforced) |
| fast-check | Property-based invariant tests | Adopt-candidate |
| Playwright visual snapshots | Visual regression | Adopt-candidate (after affordance layer) |
| @axe-core/playwright | Shell/control accessibility checks | Conditional (protocol_ui + shell only) |
| Knip | Unused TS files/exports/deps | Conditional |
| TypeDoc | Seam documentation | Conditional |
| API Extractor | Stable exported API reports | Conditional |
| ts-morph | Custom TS AST audits | Conditional |

## Per-tool detail

### SolidJS (UI/runtime) -- Already done

Fine-grained reactive renderer and HUD layer, confined to the documented import
boundary.

- Pros: signals and memos update only what changed; small bundle; no virtual DOM;
  the layout engine and step machine stay pure TypeScript.
- Cons: smaller ecosystem than React; fewer off-the-shelf components.
- Verdict: keep. Nothing to add.

### Solid stores (state) -- Already done

`createStore` plus `produce` already back `SceneStore`.

- Pros: surgical nested updates fit per-step, per-object, and per-subpart state;
  matches the flat-primitive contract.
- Cons: store mutation rules require discipline (already enforced by the store
  API's validated setters).
- Verdict: keep. Nothing to add.

### SVGO -- Skip unless folded into existing pipeline

The repo already has an SVG normalization pipeline (`tools/normalize_svg_v2.py` and
the SVG pipeline spec). This is not a claim that SVGO's exact optimization role is
already covered; it is a claim that a second, parallel SVG cleanup path must not exist.

- Pros (if SVGO added): well-known optimizer with a plugin ecosystem.
- Cons: a separate SVGO step invites drift and could fight the normalize schema in
  `src/scene_runtime/layout/normalize_schema.ts`.
- Verdict: skip unless a concrete optimization gap is found; then fold SVGO into the
  existing pipeline rather than adding a parallel path.

### Generated Valibot or Zod guard -- Adopt-candidate (conditional)

Runtime schema guard at the `generated/*.ts` boundary, before the step machine and
renderer consume the data.

- Pros: catches bad generated data before it becomes weird UI; a drift tripwire
  between Python codegen and TS consumers; reinforces the closed-vocabulary model;
  better failure messages than a downstream crash.
- Cons: if hand-written, it becomes a third copy of the schema (after
  `constants.py` and `types.ts`) and makes drift worse, not better; risks becoming
  a second authoring schema separate from the YAML specs; it guards codegen and
  drift, not author errors (those already die at build time and in
  `authored_value_check.ts`).
- Critical constraint: the guard must be generated from `constants.py` inside the
  existing codegen step. One source, zero hand copies.
- Valibot vs Zod: Valibot is modular and tree-shakeable (smaller browser bundle);
  Zod has wider contributor familiarity. Prefer Valibot here if generated.
- Verdict: highest value-for-churn item, but only in the generated form.

### Ladle -- Adopt-candidate (dev-only)

Isolated rendering of single components and visual states (Vite-based).

- Pros: review HUD regions, `SceneItem`, missing-SVG and degrade-sink states
  without walking a full protocol; catches visual regressions earlier than
  Playwright; lighter than Storybook; Solid-friendly.
- Cons: needs good fixtures or it becomes noise; does not satisfy the contract
  item 4 browser-walkthrough requirement; pulls Vite into devDependencies
  (dev-only, acceptable).
- Verdict: adopt when component-level visual review becomes a recurring need;
  pairs with Vitest and Solid Testing Library.

### Vitest -- Conditional

Fast TypeScript-native test runner.

- Pros: ergonomic describe/it, watch mode, coverage; the natural home for Solid
  component DOM tests via Solid Testing Library and happy-dom.
- Cons: the repo already runs `node --test` via tsx (documented choice); for pure
  helpers there is no ergonomic gain worth a second runner; migrating existing
  `.mjs` tests is churn with no behavior change.
- Verdict: adopt only paired with component testing (with Ladle). Do not migrate
  pure-function tests. Never let jsdom tests replace Playwright walkthroughs.

### Solid Testing Library -- Conditional

Render Solid components in a test DOM and assert output.

- Pros: useful for click-order and visual-state unit tests on individual lab
  objects; fast feedback below the full-walkthrough level.
- Cons: jsdom and happy-dom are not a real browser; contract item 4 still requires
  visible-browser Playwright evidence for mini-protocol completion.
- Verdict: supplement only, alongside Vitest. Never a replacement for Playwright.

### localStorage -- Adopt-candidate (when scoped)

Per-protocol progress persistence with no backend.

- Pros: enough for the no-database plan; restore-on-reload is a real
  student-facing feature; no framework needed.
- Cons: must be verified by a Playwright walkthrough (reload plus restored state);
  needs a clear key scheme and reset path. Progress persistence must have a separate
  restore test, because the canonical walkthrough intentionally clears browser storage
  and reloads on start; the normal fresh-start path will never exercise restore.
- Verdict: adopt when a save-progress feature is actually scoped, with a dedicated
  restore test path; trivial dependency footprint.

### esbuild watch dev script -- Adopt-candidate (cheap)

`esbuild context().watch()` plus a static serve, instead of migrating to Vite.

- Pros: live reload on `.tsx` edits; keeps the prod build byte-identical and the
  documented esbuild canonical shape; small script, no new bundler.
- Cons: not full HMR (state is lost on reload); content still requires a Python
  re-run since it comes from `generated/`.
- Verdict: the cheap answer to the "I want HMR" itch.

### UnoCSS / Tailwind -- Skip

Utility-first CSS.

- Pros: fast styling iteration; large example corpus (Tailwind); UnoCSS is
  lighter.
- Cons: current styling is a single global `src/style.css` plus a CSS
  content-policy check; utility CSS is a stylistic change with low functional
  payoff and a new build and lint surface.
- Verdict: skip; revisit only if styling volume grows substantially.

### Storybook -- Skip

Component workshop and visual catalog.

- Pros: mature ecosystem; addons; visual regression integrations.
- Cons: heavy install and config; `tools/scene_to_png.mjs` already gives scene
  previews; Ladle covers the component-isolation need more cheaply.
- Verdict: skip in favor of Ladle if component previews are wanted.

### Vite -- Skip (migration)

Vite dev server plus Rollup prod build with `vite-plugin-solid`.

- Pros: fast HMR dev server; official Solid plugin; documented GitHub Pages flow.
- Cons: replaces only the esbuild box -- Python codegen before and Python
  per-protocol HTML emit after both remain; the prod bundler changes to Rollup
  (re-verify Pages serving, set `base`); drops the documented canonical esbuild
  shape; the per-protocol HTML model gains nothing from Vite's MPA support; HMR
  helps only the TS runtime layer because content lives in `generated/`.
- Verdict: skip the migration. Use the esbuild watch script for dev DX. Vite may
  still enter devDependencies via Ladle, which is fine.

### XState -- Skip

Statecharts for complex interaction modes.

- Pros: clean modeling when one small interaction has many internal states (drag,
  focus, modal decision flows).
- Cons: `src/scene_runtime/protocol/step_machine.ts` already owns protocol
  progression; the contract mandates flat named primitive fields over nested
  state; an `adjust` or drag widget is a signal plus a small enum, not a
  statechart; a global XState rewrite would fight the architecture.
- Verdict: skip, even locally for now. Back-pocket only for a genuinely
  multi-state drag or focus affordance later.

### TanStack Router -- Skip

Type-safe client routing.

- Pros: deep links, search-param state, nested routes for a richer app.
- Cons: current routing is DOM-root presence plus per-protocol HTML files, which
  matches contract item 2 (mini-protocols compile independently).
- Verdict: skip; reconsider only if the launcher grows dashboards, filters, or
  instructor views.

### TanStack Query -- Skip

Async data fetching and caching.

- Pros: caching, retries, background refetch for server data.
- Cons: the system compiles YAML into TypeScript before build; no YAML, progress,
  or scores are fetched at runtime.
- Verdict: skip; reconsider only if a server or LMS backend appears.

### yaml runtime loader -- Reject

Parse `.yaml` in the browser at runtime.

- Pros: simpler mental model for a greenfield app; edit YAML without a build.
- Cons: this repo validates YAML at build time and freezes it into typed
  `generated/*.ts`; runtime loading discards build-time validation, the typed
  boundary, and per-protocol HTML emission; conflicts with contract item 2.
- Verdict: reject; the compile-time path is strictly better here.

### vite-plugin-solid-svg -- Reject

Import each SVG as a Solid component.

- Pros: ergonomic per-object components in a Vite app.
- Cons: SVGs here are YAML-declared assets placed by the layout engine and
  injected by the renderer; turning each into a TS component conflicts with
  contract item 3.
- Verdict: reject.

### SolidStart -- Reject

Solid meta-framework (SSR, routing, server functions).

- Pros: routing, SSR, and API routes for a larger app.
- Cons: no backend and no SSR need; GitHub Pages is static; adds server
  conventions the project does not want.
- Verdict: reject; plain Vite or esbuild plus Solid is cleaner.

### SvelteKit -- Reject

Different UI runtime plus app framework.

- Pros: cohesive routing, loaders, and build for a fresh app.
- Cons: would replace the existing Solid runtime; adds routing, loaders, and
  server conventions already covered by the launcher, protocol host, and
  per-protocol HTML; blurs the strong `content/` to `pipeline/` to `generated/` to
  `src/` to `dist/` split.
- Verdict: reject.

## Browser UX affordance layer

This section answers a sharper question than the table above: the browser UI is
largely incomplete, and translating YAML protocol intent into on-screen interaction
keeps feeling like reinventing the wheel. The finding: no app framework fixes this.
The browser is already fully data-driven (adding a protocol is 3-4 YAML files plus a
build; there is no per-protocol TypeScript, JSX, or CSS). The incompleteness is a
missing affordance layer plus a few stubbed primitives.

### The real gap

Three of the five gestures have a working browser path (`click`, `type`, and `select`
via the click affordance); `adjust` and `drag` have no control at all, and a few scene
operations are minimal.

| Surface | Status | Location |
| --- | --- | --- |
| `click` gesture | Works | `src/scene_runtime/protocol/click_resolver.ts` |
| `type` gesture | Works (hand-rolled) | `src/shell/hud/type_input.tsx` |
| `select` gesture | Works via click affordance; commit/feedback could be clearer | `affordance.ts` + click-to-select promotion in `protocol_host.tsx` |
| `adjust` gesture | No control (44 authored uses) | none |
| `drag` gesture | No control | none |
| `TimedWait` op | Minimal; observable via a subsequent state write, needs UX evidence | `src/scene_runtime/protocol/scene_op_deps.ts` |
| `LayoutMove` op | Documented no-op | `src/scene_runtime/protocol/scene_op_deps.ts` |
| Asset background | Fallback fill only | `src/scene_runtime/renderer/render_background.ts` |

### The simplifier is an abstraction, not a dependency

The durable fix is a `src/protocol_ui/` affordance layer that maps one active
interaction to one visible control to a step-machine handler:

```
active interaction (target + gesture + validator value)
  -> protocol UI affordance (render the control for this gesture)
  -> visible browser control (slider, drop surface, text field)
  -> step_machine handler (handle_click / handle_type_commit / ...)
```

This generalizes the pattern already proven by `type_input.tsx`. The protocol engine
stays pure: no UI import leaks into `step_machine.ts` or `validators.ts`. Libraries
below only supply widget internals; the abstraction is what lets a protocol pick up an
existing control instead of inventing browser UI, without forcing every protocol onto
the same one.

### Improve the existing gestures too

The working gestures are hand-rolled and worth hardening, not just the missing ones.
`type_input.tsx` carries hand-written commit, Enter-key, and reject-feedback logic, and
the click highlight is custom box-shadow code. Re-expressing them on a headless
text-field / number-field primitive yields tested behavior and one consistent commit
contract across `click`, `select`, `adjust`, and `type`. This is hardening, not a
rewrite.

### Per-tool detail (affordance layer)

#### `src/protocol_ui/` affordance layer -- Adopt

- Pros: the real simplifier; keeps the engine pure; reuses the `type_input.tsx`
  pattern; a shared control per gesture is available where it fits, and a protocol can
  still supply a bespoke affordance when its interaction needs one.
- Cons: an abstraction to design and maintain; needs a clear gesture-to-control map.
- Verdict: adopt first. The libraries below are optional internals; this is the fix.

#### Kobalte -- Adopt-candidate (pick one headless lib)

- Pros: Solid-native, will not fight Solid reactivity; supplies slider (adjust),
  dialog (modal), popover and tooltip (tips), and progress primitives.
- Cons: smaller component set than Ark UI; its headline a11y value (ARIA, focus,
  keyboard) mostly lands on the deferred shell layer, not the pointer-optimized scene.
- Verdict: preferred headless library for the affordance internals.

#### Ark UI for Solid -- Alternative to Kobalte

- Pros: broader cross-framework component set; well-tested headless behavior.
- Cons: cross-framework, less Solid-philosophical; heavier. Do not add both.
- Verdict: choose only if Kobalte's coverage proves insufficient.

#### Floating UI (Solid bindings) -- Adopt-candidate (narrow)

- Pros: positions coach marks and wrong-target feedback anchored to `[data-item-id]`,
  flipping and staying inside `#scene-root`; pure positioning, no layout conflict.
- Cons: a positioning engine only, not a component set; Solid bindings are a small
  ecosystem piece.
- Verdict: adopt for object-anchored hints; avoids hand-writing placement math.

#### `@thisbeyond/solid-dnd` -- Conditional

- Pros: best Solid-native drag/drop; uses CSS transforms, custom collision detection.
- Cons: container/list oriented, so it needs a thin adapter to scene coordinates and
  `data-item-id`; drag results must map back to target, gesture, and validator; the
  walker (contract item 4) needs a click-to-drop fallback it can drive; zero authored
  drag uses today.
- Verdict: adopt only when a drag protocol is scoped; consider a narrow custom drag
  first.

#### solid-motionone / Motion for Solid -- Conditional

- Pros: smooth object snap, shake-on-wrong, reveal, and layout transitions.
- Cons: animation only; must stay declarative and tied to layout and state, never a
  hidden state channel.
- Verdict: polish, not a blocker; adopt when layout moves need to feel real.

#### svg-pan-zoom / panzoom -- Skip for whole scene

- Pros: solves pan and zoom for one large structured surface (gel image, plate map).
- Cons: not Solid-native; applied to the whole scene it conflicts with the layout
  engine.
- Verdict: narrow-use only on a single zoomable surface; never the whole app.

#### Zag.js -- Skip

- Pros: low-level state-machine logic behind complex widgets.
- Cons: this is what Kobalte and Ark UI already wrap.
- Verdict: skip; redundant once a headless library is chosen.

#### `@dschz/solid-flow` -- Skip for runtime

- Pros: pan, zoom, nodes, edges for a flowchart editor.
- Cons: node-editor infrastructure, not a physical lab bench; would pull the runtime
  toward a workflow-editor model.
- Verdict: skip for the student runtime; back-pocket for a future instructor authoring
  tool.

#### SVG.js / direct SVG manipulation -- Reject for placement; conditional for subpart internals

- Pros: can mutate SVG paths, groups, and transforms.
- Cons: scene objects are YAML-declared assets placed by the layout engine; using SVG
  mutation to move or position a scene object conflicts with contract item 3.
- Verdict: reject for scene-object placement (move the wrapper, do not mutate the SVG).
  Conditional for custom geometry inside structured objects, which contract item 3
  explicitly allows -- wells in a plate, tubes in a rack, lanes in a gel, marks in an
  instrument display. Even there, prefer the existing subpart renderer
  (`subpart_visual_state_renderer.tsx`) before reaching for a library.

### Cross-cutting constraints

- Walker-operability is mandatory for every widget (contract item 4). An
  `AdjustControl` of a number input plus a commit button is walker-trivial; a
  `DragSurface` likely needs a click-to-drop fallback the walker can drive.
- The headless libraries' a11y payoff is the deferred shell layer, not the
  pointer-optimized scene; adopt them for tested widget behavior, not for a11y.
- Value commits reuse `ObjectStateChange` plus the `target_with_value` validator; a new
  widget emits a value into existing handlers and adds no YAML field.

### How to obtain the code

All are npm packages; install as dependencies (or devDependencies for the preview
tool). Per repo policy these are passthrough installs the human runs; record them in
`package.json` and the lockfile.

```bash
# headless primitives (choose ONE)
npm install @kobalte/core
npm install @ark-ui/solid

# object-anchored hints (positioning engine + Solid bindings)
npm install @floating-ui/dom solid-floating-ui

# drag gestures (only when a drag protocol is scoped)
npm install @thisbeyond/solid-dnd

# motion polish (optional)
npm install solid-motionone

# zoomable structured surface (narrow use)
npm install svg-pan-zoom

# component-state preview (dev only)
npm install --save-dev ladle
```

Representative imports (Solid-native):

```ts
import { Slider } from "@kobalte/core/slider";
import { Dialog } from "@kobalte/core/dialog";
import { Tooltip } from "@kobalte/core/tooltip";
```

The wrap-once rule: import a primitive in exactly one affordance file, never across the
app. For example `src/protocol_ui/affordances/adjust_control.tsx` imports the slider,
and the protocol host only knows `activeGesture === "adjust"` renders `AdjustControl`.
Follow the repo filename convention (snake_case files, CamelCase reserved for the
exported component identifier).

## Layout engine helpers (SVG placement)

This section answers whether a FOSS layout tool could improve the layout manager. The
finding: do not replace it. Most FOSS "SVG placement" tools are graph, diagram,
drag/drop, or collision/label tools. They can sharpen parts of the engine; none models
a physical lab scene.

### What the engine is (and the constraint that governs helpers)

The engine (`src/scene_runtime/layout/run_pipeline.ts`) is a deterministic, zone-based
row layout: group placements by zone, sort by `depth_tier`, place left/right/center/
justify/tab-stops by footprint, derive height from asset aspect and viewport aspect.
There is no constraint solver and no packing. Overflow shrinks gaps, then scales objects
to a `MIN_SCALE` floor, then permits negative-gap overlap. Overlap is the intended
visible signal that a zone is overloaded (LAYOUT_ENGINE.md), not a bug to auto-resolve.

Two hard constraints bound any helper:

- Determinism. Output is reproducible and clean scenes are byte-identical across runs.
  A force-directed or stress solver is non-deterministic unless seeded and run to a
  fixed convergence; an unseeded relax pass breaks the reproducibility the tests rely
  on.
- Same output shape. A helper must be a pure pipeline stage emitting the existing
  `ComputedItem` shape so the renderer is unchanged.

The most hand-tuned, maintenance-prone code is label collision (`layout_labels.ts`:
3-pass horizontal nudge plus greedy vertical stagger, with a hardcoded
`AVG_CHAR_WIDTH_PCT` font metric). That, not the object placement, is where a geometry
helper earns its keep.

### Per-tool detail (layout helpers)

#### SAT.js -- Adopt-candidate (deterministic, pure)

- Pros: 2D overlap test and minimum separation vector via the separating-axis theorem;
  deterministic and dependency-light; would clean up the hand-rolled overlap math in
  `layout_labels.ts` (does this box hit that box, smallest push to separate).
- Cons: detects collisions, does not decide layout; the placement decision stays ours.
- Verdict: adopt as a utility if the collision code keeps growing; it does not change
  the algorithm, only the geometry primitives.

#### elkjs / ELK -- Conditional (one dense zone only)

- Pros: the most serious FOSS layout engine; layered layout, rectangle packing, fixed
  nodes, relative placement; could auto-arrange a dense object cluster within one zone.
- Cons: built for "place nodes with constraints," not "place scientific objects in a
  meaningful physical scene"; no baselines, anchor points, depth scale, or bench/hood
  semantics; some layouts are non-deterministic (determinism caveat above).
- Verdict: prototype only as an internal solver for a single dense zone or cluster,
  feeding the same `ComputedItem` output; never a full replacement.

#### D3-force -- Conditional (optional post-pass)

- Pros: collision, repulsion, and gentle auto-spacing; a small force pass could relax
  label or object overlap in dense zones.
- Cons: non-deterministic unless seeded and run to fixed convergence; current label
  nudging already covers the common case.
- Verdict: a small optional post-pass only if the hand-rolled nudging becomes hard to
  maintain, and only seeded for reproducibility; not the primary algorithm.

#### rectangle-packer -- Conditional (inventory-like only)

- Pros: area-based and guillotine bin packing; fits a tray, shelf, palette, object
  picker, or reagent collection.
- Cons: packing into a box is not a realistic bench or hood; wrong model for the
  teaching scene.
- Verdict: use only for an inventory-like surface, never the physical scene.

#### Cytoscape.js / Dagre -- Skip for the scene

- Pros: mature graph and directed-graph layouts (grid, CoSE, fCoSE, Cola); fCoSE adds
  fixed-position and alignment constraints.
- Cons: graph visualization, not physical object placement or scientific SVG rendering.
- Verdict: good for a protocol-flow diagram, step-dependency view, or debug
  visualization (alongside the already-listed `@dschz/solid-flow`); skip for the
  runtime scene.

For interactive (not automatic) placement -- a future visual scene editor where an
author drags objects into zones and saves YAML -- `@thisbeyond/solid-dnd` (already
listed under the affordance layer) is the Solid-native choice; it is a drag tool, not a
layout engine.

### Ranked recommendation (layout helpers)

1. SAT.js -- deterministic collision utility to simplify the label geometry; lowest
   risk.
2. elkjs -- prototype as a constrained solver for one dense zone, same output shape,
   compared against current output.
3. D3-force -- seeded optional relax post-pass only if label nudging gets unwieldy.
4. rectangle-packer -- only when an inventory or tray surface is scoped.
5. Cytoscape.js / Dagre / `@dschz/solid-flow` -- authoring or debug diagrams only, never
   the scene.

## TypeScript tooling gaps (support, not replace)

These tools support the existing architecture rather than replace any part of it. They
target real gaps: invariant testing of the pure layers, visual regression on the
screenshots the contract already requires, and hygiene/documentation as the TypeScript
surface grows. The verdicts below were checked against the code, not taken from the
external review; where the code already covers a tool's pitch, that is stated.

### ts-pattern -- Conditional (exhaustiveness already enforced)

Pattern matching with type inference over the closed sets: `gesture`
(`src/shell/adapter/types.ts:22`), `SceneOperation` (the five PascalCase op types,
`types.ts:313`), and the validator presets (`types.ts:25,27`).

- Verified: the repo already enforces compile-time exhaustiveness with a `never`
  default in its dispatch switches (`src/scene_runtime/protocol/scene_operations.ts:127`
  and the validator dispatch in `validators.ts`). The reviewer's headline pitch -- "a
  missing arm fails at compile time" -- is therefore already true with zero
  dependencies.
- Pros: what ts-pattern adds beyond that is ergonomic matching on nested shapes and
  values (not just the discriminant tag), which could read well in `protocol_ui`
  gesture-to-control dispatch.
- Cons: redundant for the exhaustiveness it is usually sold for; a new dependency for a
  style the codebase already has a working, dependency-free idiom for.
- Verdict: conditional, and low priority. Consider only if value-shape matching in the
  affordance layer becomes genuinely awkward with plain switches; otherwise skip.

### fast-check -- Adopt-candidate

Property-based testing for the pure layers, where invariants matter more than
hand-picked fixtures.

- Verified: not currently present in `src/` or `tests/`; the gap is real. The test
  runner is `node --import tsx --test` (`check_codebase.sh:213`), and fast-check is
  runner-agnostic assertions, so it drops into the existing `tests/test_*.mjs` without a
  new runner.
- Pros: stresses broad classes of input -- layout output has finite coordinates and
  stays in bounds unless overflow is declared; labels do not overlap after the label
  pass when there is room; step flow terminates or reports a cycle; wrong-order clicks
  never advance; generated target references resolve or fail loudly.
- Cons: generators must stay small and deterministic to keep runs reproducible.
- Verdict: adopt for pure layout and protocol functions first; do not fuzz the browser.

### Playwright visual snapshots (`toHaveScreenshot`) -- Adopt-candidate (after affordance layer)

Turns the contract-required screenshots from evidence artifacts into regression checks.

- Verified: `@playwright/test` (which provides `toHaveScreenshot`) is already a
  devDependency (`package.json:17`), so this needs no new dependency. Current walkthroughs
  use `page.screenshot` for evidence across many `tests/playwright/*` files; zero use
  `toHaveScreenshot` today, so the regression gap is real.
- Pros: the contract already mandates browser screenshots; `toHaveScreenshot` makes
  object highlights, labels, coach marks, and `AdjustControl` regression-tested.
- Cons: snapshots are brittle if applied too broadly; dynamic text needs masking.
- Verdict: adopt once the affordance layer stabilizes; start with dev-smoke scenes and
  one or two stable protocols, not every step.

### @axe-core/playwright -- Conditional (protocol_ui + shell only)

Automated a11y checks (low contrast, unlabeled controls, duplicate IDs).

- Pros: validates that Kobalte/Ark controls are wired correctly; duplicate-ID checks
  are especially relevant given namespaced injected SVGs; covers new dialogs, popovers,
  type inputs, and `AdjustControl`.
- Cons: scene-layer a11y is explicitly deferred (PRIMARY_DESIGN, pointer-optimized);
  gating the scientific scene on axe now would contradict that scope.
- Verdict: gate `src/protocol_ui/` controls and shell surfaces only; not the scene.

### Knip -- Conditional

Finds unused dependencies, exports, and files.

- Pros: useful once `protocol_ui` plus Kobalte/Ark, Floating UI, and Ladle add surface
  area; prunes dead exports and dependency creep.
- Cons: generated files and dynamic entry points need ignore config.
- Verdict: add after the new layer is large enough to justify the config.

### TypeDoc -- Conditional

Generates docs from TypeScript comments for selected entry points.

- Pros: documents the internal seams authors and agents must respect (shell adapter
  types, protocol config, computed layout items, scene-op deps, renderer facade).
- Cons: noise if pointed at every file.
- Verdict: document seam contracts only, and only if `protocol_ui` becomes a real
  internal library.

### API Extractor -- Conditional

Exported-API reports and `.d.ts` rollups for review.

- Pros: could snapshot `src/shell/adapter/types.ts` and `protocol_ui` public exports to
  catch accidental API drift.
- Cons: heavy unless part of `src/` is treated as a stable internal package; TypeDoc is
  the lighter option.
- Verdict: defer until a seam is formalized as a versioned internal package.

### ts-morph -- Conditional

Compiler-API wrapper for custom static analysis and codegen audits.

- Pros: could enforce repo-specific rules -- Solid imports only in allowed directories,
  Kobalte/Ark imported only in wrapper files (the wrap-once rule), generated TS shape
  audits.
- Cons: custom AST checks are maintenance work.
- Verdict: only if ESLint and file-based tests prove too blunt for a needed rule.

### Ranked recommendation (TypeScript gaps)

1. fast-check -- the clearest real gap; stress-tests layout and protocol invariants
   without hundreds of fixtures, no new runner.
2. Playwright visual snapshots -- promotes existing screenshots to regression checks
   with no new dependency.
3. @axe-core/playwright -- once `protocol_ui` controls exist.
4. Knip, TypeDoc, API Extractor, ts-morph -- hygiene and seam tooling as the surface
   grows.
5. ts-pattern -- low priority; the exhaustiveness it is sold for is already enforced
   dependency-free, so adopt only if value-shape matching becomes awkward.

## Guiding rule for any future tool

Add a tool only if it makes one of the project's strongest parts cleaner: the YAML
source of truth, the closed vocabulary, the pure protocol and layout layers, the
generated TypeScript boundary, or the visible-UI walkthrough requirement. Reject
anything that adds a parallel routing model, a second schema language, hidden state
transitions, or framework-specific protocol logic.

## Ranked recommendation

1. `src/protocol_ui/` affordance layer, `AdjustControl` first -- the real UI
   simplifier; unblocks 44 authored `adjust` uses.
2. Kobalte or Ark UI -- pick one headless library for widget internals.
3. Floating UI -- object-anchored hints and wrong-target feedback.
4. Generated Valibot or Zod guard from `constants.py` -- fixes real latent drift.
5. Ladle plus Solid Testing Library -- only after the first few affordance components
   exist.
6. esbuild watch dev script -- HMR developer experience without a Vite migration.
7. localStorage -- only with a separate restore test path.
8. `@thisbeyond/solid-dnd` -- only when a real drag protocol is scoped.
9. SAT.js -- only if label or overlap geometry keeps growing.
10. Everything else -- skip or reject per the table above.
