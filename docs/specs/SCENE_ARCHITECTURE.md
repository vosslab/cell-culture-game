# Scene architecture

## Purpose

This document explains how scenes are wired and run at runtime. The schema for
scene YAML is documented separately in
[SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md); the canonical terms are in
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md). Read this doc when you need to
understand the driver, registry, adapter, or capability layers, when you are
adding a new scene, or when you are debugging runtime behavior.

This doc covers the runtime side only. It does not duplicate the YAML schema
and it does not document author-facing protocol concepts (those live under the
`PROTOCOL_*` family).

This doc describes the driver, registry,
adapter, and capability layers. See
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md) for the canonical interaction model.

## Layered model

The scene system has four cooperating layers. Each layer owns a different
concern, and the layers communicate through small, documented interfaces.

```
+------------------------------------------------------------------+
| Layer 4: per-scene YAML config                                   |
|   src/scenes/<scene>/<scene>.yaml                                |
|   Owns: scene-side static declarations only -- sceneId,          |
|   capabilities, object placements, zones,                        |
|   wrongOrderMessage. Object identity (state_fields,              |
|   visual_states, subparts, capabilities) is object YAML; see     |
|   OBJECT_VOCABULARY.md and OBJECT_YAML_FORMAT.md. No behavior.   |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
| Layer 3: per-scene adapter                                       |
|   src/scenes/<scene>/<scene>.ts                                  |
|   Owns: render assembly, dispatchInteraction, per-step state     |
|   mutations, completion-event emitters, scene-specific DOM.      |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
| Layer 2: capabilities (reusable mechanics)                       |
|   src/scenes/capabilities/*.ts                                   |
|   Owns: shared mechanics that multiple scenes can compose        |
|   (item-zone click routing, modal flow, grid counting, etc.).    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
| Layer 1: driver core                                             |
|   src/scenes/scene_driver.ts, src/scenes/scene_registry.ts       |
|   Owns: runSceneRender, runScene lifecycle, capture-phase click  |
|   dispatch, capability and adapter registries.                   |
+------------------------------------------------------------------+
```

Higher-numbered layers depend on lower-numbered layers but never the reverse.
The driver core knows nothing about specific scenes; capabilities know nothing
about which scenes will mount them; adapters bind a specific scene id to its
behavior; YAML carries that scene id's static configuration.

## Layout and hit surfaces

Layout remains a reusable, scene-agnostic geometry service. The build-time
layout result includes final placement geometry plus serialized interaction
envelopes and the scene's minimum valid 16:9 frame. `protocol_host.tsx` consumes
that metadata verbatim: it applies the frame dimensions and 44-pixel hit-core
size to the scene hosts so a dense scene can remain usable through the panel's
normal scrolling behavior.

`SceneView` rejects invalid interaction geometry and passes each placement's
envelope to `SceneItem`. For a clickable top-level placement, the transparent
envelope owns the delegated whole-object `data-item-id`; the visual root stays
focused on artwork and does not own that delegated identity. Structured objects
keep their declaration-owned SVG subpart surfaces instead. When an exact or
group subpart interaction is active, those surfaces retain their subpart hit
geometry and identity so sibling subparts remain addressable; the whole-object
envelope does not cover that surface.

## Driver (`scene_driver.ts`)

The driver is the universal scene runtime. Two entry points matter:

- `runSceneRender(sceneId)` at
  `src/scenes/scene_driver.ts:91-108` -
  Looks up the registered adapter for `sceneId`, builds a `SceneContext`, and
  calls `adapter.render(ctx)`. Throws a loud error if no adapter is
  registered. Called every frame from the `setRenderGame` switch in
  `init.ts`.

- `runScene(sceneId)` at
  `src/scenes/scene_driver.ts:123-210` -
  Called once per scene (the first time the scene is shown). Looks up the
  scene config from `SCENE_CONFIGS`, mounts every declared capability, and
  attaches a single capture-phase click listener to the scene's DOM element.
  When a click reaches a delegated interaction surface carrying
  `data-item-id` (a whole-object envelope or declaration-owned subpart surface),
  the driver walks the capability list until one returns `true` from `onClick`;
  if none claim the click, the adapter's `dispatchInteraction` runs as the
  fallback path.

`SceneAdapter.render(ctx)` is required (not optional). The optional `?` was
a temporary bridge during the A1-A6a render-ownership migration and was
removed at the end of A6b. Every adapter under `src/scenes/<scene>/` exports
a `render` method today.

`SceneContext` carries `sceneId` and a `dispatchInteraction(itemId)` callback
that closes over the resolved adapter. Capabilities and adapter code use the
context to route clicks back through the adapter without holding a direct
reference to the registry.

`ClickTarget` is a minimal `{itemId: string}` shape (with extension fields).
The capture-phase click handler reads `data-item-id` from the clicked interaction
surface and feeds it to capability `onClick` handlers as a `ClickTarget`.

## Registry (`scene_registry.ts`)

The registry is two simple maps and four functions:

- `registerCapability(capability)` and the `CAPABILITY_REGISTRY` map at
  `src/scenes/scene_registry.ts:18,54-60` -
  Capability modules call this at module load. Duplicate ids throw loudly.

- `registerScene(adapter)` and an internal `SCENE_REGISTRY` map at
  `src/scenes/scene_registry.ts:38,76-83` -
  Scene adapter modules call this at module load. Duplicate scene ids throw
  loudly.

- `getRegisteredScene(sceneId)` at
  `src/scenes/scene_registry.ts:97-99` -
  The driver uses this to look up the adapter for a scene. Returns
  `undefined` if not registered (the driver throws on `undefined` so the
  registry stays a pure data-store).

Registration is the entire reason adapter and capability modules need to be
imported from `src/init.ts`: importing the module triggers its top-level
`registerScene(...)` or `registerCapability(...)` call. Without the import,
no registration runs and the registry stays empty for that scene.

## Adapter registry (target resolution)

The adapter registry is the per-scene map that resolves each semantic
protocol `target` name to a concrete scene object. It is the scene side of
protocol target resolution: the protocol writes a flat namespace of
geometry-free `target` names, and the adapter registry grounds each name in
the scene's geometry. The protocol writes `target: flask`; the adapter
registry resolves `flask` to the scene's flask object.

The adapter registry is distinct from the scene registry and the capability
registry described above: those are runtime maps keyed by scene id and
capability id. The adapter registry is the per-scene `target`-name to
scene-object map.

A `target` that addresses one of an object's subparts -- a single well in a
plate, a single lane in a gel -- resolves through the object's declared
`structure.subparts` (see [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md))
and is written by the protocol as `<object_name>.<subpart_name>` (for example
`treatment_plate.A1`). Named groups are retired with no successor;
protocols list explicit subparts until a future plan
revisits named groups.

This section names the registry concept and where it lives; the canonical
term is in [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md), and the protocol-side
half of the boundary is in
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md). The concrete TypeScript
shape of the registry is future work for the code-migration plan; the
runtime does not implement target resolution yet (see "Adapters" below for
what adapters own today).

## Adapters

Six first-class adapters live under `src/scenes/<scene>/`. Each registers
itself at module load and provides `dispatchInteraction(itemId, ctx)` and
`render(ctx)`.

| Scene                | Adapter file              | Notes                                                                                                                                                                                                                                                                        |
| -------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bench                | `bench.ts`                | Persistent equipment-bench scene; layout-engine-driven items. Split by responsibility seam: `bench.ts` holds module-load registrations and the `SceneAdapter` shell; `render.ts` owns assembly + event wiring; `dispatch.ts` owns click handling and completionPath routing. |
| Cell-culture hood    | `cell_culture_hood.ts`    | Split across the adapter file (dispatch + registration) and a sibling render.ts (assembly seam). Dispatch is K2-only: compatibility-token handling folded into completionPath dispatch.                             |
| Incubator            | `incubator.ts`            | Modal overlay scene for incubation timing.                                                                                                                                                                                                                                   |
| Microscope           | `microscope.ts`           | Modal overlay scene; mounts to the shared `instrument-overlay` element. Manual hemocytometer flow extracted into sibling `manual_hemocytometer.ts` so the automated cell-counter and manual grid-counting paths no longer share a single dispatcher.                         |
| Well-plate workspace | `well_plate_workspace.ts` | First-class workspace scene for plate-transfer and tube-prep mini-protocols. Render assembly and dispatch live in sibling render.ts and `dispatch.ts`.                                                              |
| Plate reader         | `plate_reader.ts`         | Render-only modal scene; click handlers are wired directly inside the renderer rather than dispatched through `data-item-id`. Mounts to the shared `instrument-overlay` element.                                                                                             |

The microscope and plate_reader adapters share a single DOM modal slot, the
`instrument-overlay` element.

## Capabilities

Capabilities are reusable mechanics that scenes opt into by listing them in
the YAML `capabilities` array. Each capability conforms to the
`SceneCapability` contract (`mount`, `onStepChange`, `onClick`, `unmount`)
and registers at module load.

Six capability ids are registered today. Their runtime status varies: most
capabilities serve as click routers or no-op state holders and validate a
small slice of their declared config. This matches the status recorded in
[SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md).

| Capability id             | Module                       | Status                                                                                     |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ |
| `item_workspace`          | `item_workspace.ts`          | Validates `placements` and `zones`; dispatches `data-item-id` clicks to the scene adapter. |
| `modal_workspace`         | `modal_workspace.ts`         | Validates `scene_name` only.                                                               |
| `instrument_workspace`    | `instrument_workspace.ts`    | Validates `scene_name` only.                                                               |
| `grid_counting_workspace` | `grid_counting_workspace.ts` | Mounts and routes quadrant clicks; validates `scene_name` and `quadrants`.                 |
| `incubator_workspace`     | `incubator_workspace.ts`     | Validates `scene_name` only.                                                               |
| `plate_reader_workspace`  | `plate_reader_workspace.ts`  | Validates `scene_name` only.                                                               |

## Module-load side effects

This section is load-bearing. Every adapter module performs work at module
load that nothing else triggers; if the adapter is not imported from
`src/init.ts`, that work silently does not happen.

Side-effect tracking prevents orphaned registrations. When ownership
moves, enumerate and move every module-load side effect with the responsibility.

When migrating, retiring, or auditing a scene module, enumerate every kind
of module-load side effect that lives in it:

- `registeredEmitters.add(...)` calls (completion-event registration).
- `registerScene(...)` and `registerCapability(...)` calls.
- `window.*` and test-API bindings.
- Top-level `addEventListener` and observer setup.
- Mutations of any global registry (`SCENE_REGISTRY`, `CAPABILITY_REGISTRY`,
  any other module-level map).
- Side-effect-only imports (`import "./foo";` with no name binding).

If a source module is being retired, every one of these must move with the
responsibility, not stay behind. After the move, the source module must
contain no top-level statements with side effects. After the move, the new
owning module must remain reachable from `src/init.ts` (directly or via the
chain of side-effect imports starting there).

Three adapter files (cell_culture_hood, plate_reader, microscope) carry an
explicit MODULE-LOAD warning comment at the top for future editors.

## How a frame renders

A single click-to-frame round trip looks like this:

1. The user clicks an item in the hood. The browser fires `click`.
2. The driver's capture-phase listener (attached during `runScene`) reads
   `data-item-id` from the nearest delegated interaction surface. If absent, it
   returns.
3. The driver iterates the scene's mounted capabilities and calls
   `capability.onClick(ctx, {itemId})` on each. The first capability to
   return `true` claims the click; the driver marks the event as handled
   and stops propagation.
4. If no capability claims the click, the adapter's `dispatchInteraction`
   runs as the fallback path (used by adapters whose dispatch logic is not
   yet split into a capability).
5. `dispatchInteraction` mutates `gameState`, may call
   `triggerStep(stepId)` to advance the protocol, and finally calls
   `renderGame()`.
6. `renderGame()` runs the `setRenderGame` switch in
   `src/init.ts:216-287`. The case for the active scene
   calls `runSceneRender(sceneId)`.
7. `runSceneRender` looks up the adapter and calls `adapter.render(ctx)`.
   The adapter rebuilds its DOM/SVG and reattaches its listeners.

The first time a scene is shown, the case in `setRenderGame` also calls
`runScene(sceneId)` (gated by the `DRIVER_INITIALIZED_SCENES` set) to mount
capabilities and attach the capture-phase listener. Subsequent frames only
re-render.

## How to add a new scene

See [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) for the complete scene
YAML schema. A new scene requires both a YAML configuration file and a
TypeScript adapter module that implement the runtime and rendering behavior.
At build time, the scene YAML is validated and compiled into generated
TypeScript exports consumed by the driver.

## Shared infrastructure

Several modules under `shared` host code
that multiple scene adapters reuse. Each is a single source of truth for
its concern.

- `liquid_transfer.ts` - Liquid
  handling abstractions: `deriveHeldLiquid`, `canonicalTool`, and the
  `LIQUID_BY_ASSET_ID` map. Consolidated in the B1 patch; do not duplicate
  these helpers in adapters.
- `wrong_order_feedback.ts` -
  `showWrongOrderToast(message)` for the transient warning toast. The
  toast styling and 2 s lifetime are hardcoded.
- `scene_item_lookup.ts` -
  Item-id lookup helpers introduced during the bench/hood YAML layout
  migration so adapters can resolve scene items without duplicating the
  lookup rules.

The `src/scenes/shared/legacy_tokens.ts` module was deleted once the
hood ladder folded into K2 completionPath dispatch. There is no
compatibility-token shim anymore: dispatch reads `completionPath`
directly.

## Relation to scene YAML

Scene YAML declares static configuration; this doc covers the runtime that
interprets it. See [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) for the
schema, the validator rules, and the build pipeline that emits
`generated/scene_data.ts` (consumed via `src/scene_configs.ts`). Scene YAML lives in `content/base_scenes/` (shared base scenes) or `content/protocols/<cluster>/<name>/scenes/` (protocol-local scenes).

## Related docs

- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) - Scene YAML schema and
  validator rules.
- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) - Canonical terms used by
  this doc, the schema doc, and scene-related code.
- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) - Canonical object terms
  (state_fields, visual_states, structure, subparts) the scene references.
- [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) - Object-definition YAML
  schema referenced by scene placements.
- [../CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md) - Higher-level system
  overview; the "Capability-based scene architecture" section there points
  at this doc for the deep dive.
