# Scene vocabulary

This document is the canonical vocabulary for the scene system: scene
authoring, scene-adapter code, scene tests, and scene documentation in
this repository. Every scene-related doc, code comment, error message,
validator output, and authoring guide must use these exact terms with
these exact meanings. Synonyms listed in the retired-terms table are
not used.

This doc is one corner of a three-vocabulary model. The protocol side
names what happens; the object side names what a thing is and how its
state appears; the scene side names where things appear and how the
space is arranged. The protocol-side counterpart is
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md). The object-side
counterpart is [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md). Where a
concept is protocol-side or object-side, this doc points to the
relevant canonical doc rather than redefining it.

Related docs:

- [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) -- scene YAML schema.
- [SCENE_ARCHITECTURE.md](SCENE_ARCHITECTURE.md) -- how scenes are
  wired and run at runtime.
- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) -- the object-side
  vocabulary; identity, structure, state, render map, capabilities,
  and layout hints all live there.
- [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md) -- the
  protocol-side vocabulary; the boundary section below cross-references
  it.
- [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) -- the shared placement system.
- [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md) -- the closed material terms,
  sentinel/visible classification, and color resolver invariants.
- [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) -- the runtime render-effect
  and target vocabulary; the rendering contract for object visual states.

## What a scene is

A scene is the unit of authoring for "where things appear and how the
space is arranged". One scene declares one workspace surface, one
optional static backdrop, one set of named placement regions
([zones](#zones)), one set of object [placements](#object-by-id-placement)
(each placement references an object from the object library by id),
and the spatial-arrangement rules that the layout engine consumes.

The scene definition does not say what any thing is (object identity,
structure, state, state-to-visual mapping, capabilities, and layout
hints are object-side; see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)) and does not say what
should happen on the scene (that is protocol-side; see
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)).

## The scene side of the boundary

The three-way boundary names what each vocabulary owns:

- **Protocol** names what happens. Canonical doc:
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
- **Object** names what a thing is and how its state appears.
  Canonical doc: [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- **Scene** names where things appear and how the space is arranged.
  Canonical doc: this file.

The scene side encodes the following rule: a scene references objects
by id, places them inside ordered named [zones](#zones), declares bounded
[layout_rules](#layout-rules), and declares the static
[background](#background-as-a-static-backdrop) backdrop. The layout manager
derives numeric scene and zone geometry after it measures the objects.
A scene never declares object identity, `state_fields`, `visual_states`,
or `capabilities`.

Scene placement may carry only the categorical `layout.anchor_y` and
`layout.label_placement` hints. A placement may not
override object identity (`object_name`, `kind`, `label`),
`state_fields`, `visual_states`, or `capabilities`. The full override
rule lives on the object side; see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).

The scene vocabulary has no named-group construct. A protocol that
needs to act on several subparts lists each subpart explicitly (for
example `treatment_plate.A1`, `treatment_plate.A2`). Subparts belong
to the object, not the scene.

The boundary exists because of a documented failure: PRIMARY_CONTRACT
item 1 records that earlier TypeScript was built around the hood scene
and treated other scenes as derivatives. The boundary rule keeps that
drift out. On the scene side, that means the scene never demands that
any one object's structure leak into placement; the scene names
objects only by id.

## Background as a static backdrop

A scene background is a pure backdrop. The scene declares a
background asset (an image or an SVG); the renderer paints it under
everything else. A background is not interactive and carries no
state.

A clickable region that authors might place on a background
image (a sink basin, a benchtop edge, a tool drop zone) is not a
property of the background. It is an object placed over the backdrop
through the normal object reference and placement mechanism. The
object library declares what the region is (identity, the
`clickable` capability, render rules); the scene places it on top of
the backdrop in the appropriate zone. See
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) for the object side of
"clickable region as object".

The scene declares one optional `background` block with an asset reference; it
never declares clickable behavior on
the background and never attaches state, capabilities, or
`visual_states` to it.

| Field               | Required                    | Purpose                                                                                   |
| ------------------- | --------------------------- | ----------------------------------------------------------------------------------------- |
| `background.asset`  | yes (if background present) | Asset id (image or SVG) used as the static backdrop. The asset library resolves the file. |

## Object-by-id placement

A scene places objects by id. Each placement entry in the scene's
`placements` list names exactly one object from the object library
and states where that placement goes. The placement does not declare
object identity, structure, `state_fields`, `visual_states`, or
`capabilities`; those belong to the object definition (see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)).

Scene placement may carry only `layout.anchor_y` and
`layout.label_placement`. A
placement may not override object identity (`object_name`, `kind`,
`label`), `state_fields`, `visual_states`, or `capabilities`. The full override surface is in
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md), "## The object side of
the boundary".

| Field                         | Required | Purpose                                                                                                                                                                                                                                                  |
| ----------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `placement.placement_name`    | yes      | Stable per-scene name for this placement. Distinct from `object_name`: a scene may place the same object more than once, and each placement needs its own scene-scoped name.                                                                             |
| `placement.object_name`       | yes      | The name of the object in the object library. The object resolves identity, structure, state, rendering, and capabilities.                                                                                                                               |
| `placement.zone`              | yes      | The [zone](#zones) this placement belongs to.                                                                                                                                                                                                            |
| `placement.depth_tier`        | no       | Numeric layering hint within the zone.                                                                                                                                                                                                                   |
| `placement.align_stop`        | no       | One of `left`, `center`, `right`. Tab-stop group for the layout engine.                                                                                                                                                                                  |
| `placement.layout`            | no       | Categorical `anchor_y` and `label_placement` hints only. |

Notes:

- A placement may not declare or modify subparts; subparts
  are object-side, not scene-side.
- A placement may not declare state or a render map; the object owns
  state and rendering, and the protocol mutates state semantically
  through `ObjectStateChange` (see
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)).
- Placement `layout` cannot override intrinsic object dimensions or introduce
  numeric geometry.

## Zones

A zone is an ordered named semantic group. The layout manager combines source
order, measured placement demand, and approved alignment hints to arrange its
contents. Zones replace ad-hoc coordinates with a small named-group vocabulary.

A zone is scene-side because it is a property of where things go, not
of what any thing is. Zones do not carry identity, state, rendering, or source
geometry.

| Field             | Required | Purpose                                                                                                                           |
| ----------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `zone.zone_name`  | yes      | Stable zone name, scoped to this scene. Placements reference it via `placement.zone`.                                             |
| `zone.align`     | no       | Arrangement rule for placements inside the zone. Includes `tab-stops` (today's behavior, paired with per-placement `align_stop`). |
| `zone.label`     | no       | Optional human-readable label for authoring and debugging.                                                                        |

Schema detail belongs in [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md)
"Zones".

## Derived geometry

The layout manager derives scene bounds, zone bounds, and baselines. They are
runtime records, not authored scene YAML fields. Source scene YAML rejects
`scene_bounds`, `bounds`, `baseline`, coordinates, `baseline_override`, and
numeric scale or size overrides.

## Layout rules

The scene declares scene-wide arrangement rules the layout engine
consumes when arranging zones and placements.

| Field          | Required | Purpose                                                                      |
| -------------- | -------- | ---------------------------------------------------------------------------- |
| `layout_rules` | no       | Scene-wide arrangement rules (label sizing, offset hints, tab-stop budgets). |

`layout_rules` is intentionally narrow: it carries scene-wide hints
the layout engine needs to resolve placements; it does not carry
object identity or state. Per-placement overrides go on the
[placement](#object-by-id-placement), not here.

Tab-stop behavior is expressed by `zone.align: tab-stops` plus
per-placement `align_stop`, and that is the canonical path.

## Label placement

`label_placement` is a closed enum that controls where a placement's label
renders relative to its object. Two values are defined:

| Value    | Behavior                                                                                              |
| -------- | ----------------------------------------------------------------------------------------------------- |
| `top`    | Default. Label renders centered above the object and staggers upward, away from artwork.              |
| `bottom` | Label renders centered below the object and staggers downward (legacy direction).                     |

Scope: scene-wide default in `layout_rules.label_placement`; per-placement
override in `placement.layout.label_placement`. Per-placement wins over scene
default; scene default wins over the engine default of `top`.

The field is optional in both locations. An absent field resolves to `top`
in the layout engine; the validator accepts an absent field without error.
The default is NOT written into the scene YAML unless the author wants to
document an intentional choice or the engine needs an explicit `bottom`
override for a specific scene.

Schema detail and the `layout_rules` field table are in
[SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md). The label coordinate
model (`_labelX`, `_labelY`) is described in [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md).

## Interaction affordance

The interaction affordance is the visible cue that tells a student what
is clickable and what to act on right now. It is derived view state:
computed by the renderer from the active-interaction snapshot, never
authored in YAML, never persisted, and it adds no vocabulary to the
closed authoring surface.

The affordance has three tiers:

- **Baseline clickable cue.** Every scene object that the click
  resolver accepts as a target carries a baseline cue at all times:
  a pointer cursor plus a faint hover and focus outline. This cue tells
  the student that the object is interactive; it does not reveal any
  step-specific intent.

- **Directed-gesture active ring.** When the active interaction uses a
  directed gesture (`click`, `drag`, `adjust`, or `type`) the single
  active target carries a strong solid ring. This ring distinguishes
  the one object the step is asking the student to act on from the rest
  of the scene. The ring is not present on any other object.

- **Select candidate rings.** When the active interaction uses the
  `select` gesture every clickable candidate present in the scene
  carries an equal strong ring. The ring is visually distinct from the
  directed-gesture ring (different style: dashed vs. solid; distinct
  color pair, not color-only, so the distinction is accessible). The
  correct answer carries the same ring as every other candidate; the
  ring never singles out the answer. The student must identify the
  correct object from the prompt, not from a visual highlight. See the
  `select` definition in
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).

The affordance is a derived computation. The renderer reads the
active-interaction snapshot (active target id and active gesture) plus
the set of rendered clickable objects and produces the ring state for
each object as a pure derivation. No store flag is written. No YAML
field controls it. No affordance data persists across steps or scenes;
it recomputes automatically whenever the interaction advances.

The renderer stamps a `data-affordance` attribute on every rendered scene
object with one of three closed values: `"active"`, `"candidate"`, or
`"none"`. This is the DOM contract the CSS ring rules consume; it is
analogous to how `data-item-id` identifies the scene object, but it
describes derived affordance state, not authoring identity.

Scene objects are pointer-clickable only. The renderer does not stamp
`role="button"` or `tabIndex={0}` on item roots. Keyboard navigation, ARIA
roles, and screen-reader support are explicitly out of current scope for the
scene interaction layer; see the "Accessibility scope" section in
[PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md) for the full scope note.

## Scene-level UI feedback

`wrong_order_message` is a scene-side UI string shown when a learner
clicks placements in an order the protocol rejects. It is a property
of how this scene gives feedback, not of any one object's identity or
state.

| Field                 | Required | Purpose                                     |
| --------------------- | -------- | ------------------------------------------- |
| `wrong_order_message` | no       | UI toast text for wrong-order interactions. |

## Scene identity

The scene itself carries a small identity block. These fields name
the scene and the workspace it targets; they are not object identity.

| Field        | Required | Purpose                       |
| ------------ | -------- | ----------------------------- |
| `scene_name` | yes      | Stable scene name.            |
| `workspace`  | yes      | Workspace this scene targets. |

The `scene_name` value matches the directory name and YAML basename
and is the key into the [scene registry](#scene-registry) and the
generated `SCENE_CONFIGS` table.

## The `ClickTarget` naming collision

`ClickTarget` is one narrow runtime type, not a vocabulary term for
"the thing a protocol addresses". The canonical resolution is a
three-way split:

- **`target` is the protocol-side term.** The semantic, geometry-free
  name a protocol author writes. Canonical in
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md). The phrase "click
  target" is retired from the protocol vocabulary entirely.
- **An object name is the addressable identity.** The scene names
  objects by `object_name` (see
  [Object-by-id placement](#object-by-id-placement)); the object
  declares the structure and capabilities behind that name. Canonical
  on the object side: see
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- **`ClickTarget` is one narrow runtime type.** `ClickTarget` survives
  only as the name of the minimal `{itemId}` driver-payload shape -- a
  low-level click-event payload. It is **not** the protocol-side
  `target` and **not** an object id.

This doc keeps `ClickTarget` strictly as that runtime type name. See
the [`ClickTarget`](#clicktarget) term-reference entry for the
runtime definition. Wherever `ClickTarget` appears in scene code, a
comment, or an error message, it means the driver payload and
nothing else.

## Scene-adapter resolution

A protocol may declare multiple scenes in its `scenes/` directory,
and each scene may inherit from a base scene (see
[SCENE_INHERITANCE.md](SCENE_INHERITANCE.md)). At runtime, the
stepper resolves protocol targets against a per-protocol registry
built by union over all scenes the protocol declares, plus the base
scenes they transitively extend.

The target-resolution algorithm is:

1. Consult the currently-active scene's placements. If a match exists,
   resolve and stop.
2. On miss, consult the per-protocol registry of all resolvable
   placements from all scenes the protocol declares (the protocol's
   `scenes/` directory files plus each base scene they extend). If
   exactly one match exists in the registry, resolve and stop.
3. On zero matches, the stepper emits `unknown_target_active_scene`
   (existing error class).
4. On multiple matches in the registry (different scenes place objects
   with the same `object_name`), the stepper emits `ambiguous_target_in_scene`
   (existing error class) and does not resolve.

The registry is built from the resolved placement set that the
scene-inheritance validator already produces (after `remove_placements`,
`deactivate_placements`, `reposition_placements`, and `add_placements`
apply per [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md)). Deactivated
placements are excluded from the registry; placement availability
follows the deactivation rule (placement runtime availability).

This scheme resolves all cases where a protocol author intends to
reference an object placed in a sibling scene of the same protocol
without requiring a `SceneChange` back to that scene. No new
author-facing YAML keys are introduced; the registry is derived
runtime metadata. See
[scene_adapter_recommendation.md](../archive/scene_adapter_recommendation.md)
for the design rationale (Option 2 analysis).

## Terms

| term                    | one-line definition                                                                                                                                                                                   |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| scene                   | A self-contained interactive surface with one DOM root, one adapter, and one YAML config where static scene config exists.                                                                            |
| scene name              | The stable string name for a scene; matches the directory name and YAML basename and is the key into `SCENE_CONFIGS` and the scene registry.                                                          |
| adapter                 | The per-scene TypeScript object that owns `render` and `dispatchInteraction` for one scene name.                                                                                                      |
| placement               | A scene-side entry that names an object by `object_name` and states where that object goes (zone, depth tier, align stop, optional layout overrides).                                                 |
| placement name          | The stable per-scene name for one placement; distinct from `object_name` because a scene may place the same object more than once.                                                                    |
| object name             | The name of an object in the object library; the only handle the scene side uses to name an object. See [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).                                                 |
| background              | The static backdrop asset declared on the scene; not interactive, carries no state.                                                                                                                   |
| zone                    | An ordered semantic group declared by `zones[]`; placements reference its `zone_name`.                                                                                                                |
| derived scene geometry  | Internal scene and zone bounds plus baselines produced by the layout manager.                                                                                                                         |
| layout_rules            | Scene-wide arrangement rules the layout engine consumes.                                                                                                                                              |
| layout engine           | Shared placement system that positions object placements in zones.                                                                                                                                    |
| structured surface      | An object with meaningful internal coordinates or subparts; the structure schema is object-side (see [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)).                                                   |
| subpart                 | A visual or clickable element inside a structured surface; declared on the object, addressable via the object's `id_pattern`.                                                                         |
| workspace               | A YAML-declared family label naming a scene's surface kind. Required by the scene YAML validator; advisory at runtime.                                                                                |
| item                    | The runtime name for a clickable DOM element rendered by the adapter and dispatched by `data-item-id`; in cleaned authoring, every item is the rendering of one [placement](#object-by-id-placement). |
| wrong_order_message     | A scene-side UI string shown when a learner clicks placements in an order the protocol rejects.                                                                                                       |
| instrument-overlay      | The shared modal-slot DOM element used by instrument-style scenes; only one scene is visible in the slot at a time.                                                                                   |
| module-load side effect | Top-level statement in an adapter or capability module that runs when the module is imported (registration, emitter pre-registration, listener attach, registry mutation).                            |
| completion event        | The string id passed to `triggerStep(stepId)` to signal that a step has completed; pre-registered via `registeredEmitters.add(...)`.                                                                  |
| render                  | The adapter's `render(ctx)` method; rebuilds the scene's DOM/SVG and rewires its listeners.                                                                                                           |
| dispatchInteraction     | The adapter's `dispatchInteraction(itemId, ctx)` method; the fallback path the driver invokes when no capability claims a click.                                                                      |
| SceneContext            | The runtime context object passed to capability and adapter methods; carries `sceneId` and a `dispatchInteraction(itemId)` callback.                                                                  |
| ClickTarget             | The minimal `{itemId: string}` driver payload built from `data-item-id`; a low-level click-event shape, not the protocol `target` and not an object id.                                               |
| scene registry          | The internal `SCENE_REGISTRY` map keyed by scene id; populated by `registerScene` calls at module load.                                                                                               |
| capability registry     | The `CAPABILITY_REGISTRY` map keyed by capability id; populated by `registerCapability` calls at module load.                                                                                         |

## Term reference

### scene

A self-contained interactive surface in the game. Each scene has one
DOM root element and one TypeScript adapter, and where it has
declarable static scene config that config lives in one YAML file.
Scenes that are render-only or programmatically configured may opt
out of YAML; today every shipped scene has a YAML, but the rule is
"one YAML where static config exists," not "every scene must have a
YAML."

### scene name

The stable string name for a scene. It matches the directory name, the
YAML basename, the adapter's `sceneId` field, the key in
`generated/scene_data.ts` `SCENE_CONFIGS` (consumed via the
`scene_configs.ts` facade), and the key
in the scene registry. The discoverer in
[../../pipeline/gen_scene_index.py](../../pipeline/gen_scene_index.py) globs
`src/scenes/<scene_name>/<scene_name>.yaml` to pick scenes up.

### adapter

The per-scene TypeScript object that implements `SceneAdapter`
(`src/scenes/scene_registry.ts:31-36`). It owns `render(ctx)` and
`dispatchInteraction(itemId, ctx)` for one scene id and is registered
at module load via `registerScene(adapter)`.

### placement

A scene-side entry that references one object from the object
library by `object_name` and states where the object goes (its zone,
depth tier, align stop, and instance overrides). See
[Object-by-id placement](#object-by-id-placement) for the field
table. Each placement carries its own `placement_name` because a scene
may place the same object more than once; the runtime DOM id remains
the placement name, and clicks dispatch through `data-item-id` against
that name (see [item](#item)).

### placement name

The stable per-scene name for one [placement](#placement). Distinct
from `object_name`: two placements may reference the same object (for
example two `dilution_tube_rack` instances on a hood scene), and
each placement gets its own scene-scoped name so the runtime can
address them independently.

### object name

The name of an object in the object library. The scene side names
objects only by `object_name`; identity, structure, state, render
rules, and capabilities are resolved object-side. Canonical
definition: [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md), "## Object
identity".

### background

The static backdrop asset declared on the scene. A
background is not interactive and carries no state; clickable
regions on top of a backdrop are objects placed over it. See
[Background as a static backdrop](#background-as-a-static-backdrop)
for the field table.

### zone

A named, ordered semantic group declared by an entry in the scene YAML's
`zones[]` array. Placements reference zones by `zone_name` via `placement.zone`.
Source zones carry only `zone_name`, optional `align`, and optional `label`.
The layout manager derives internal bounds and baselines; `layout_rules.zone_gap`
is the scene-wide spacing hint. Schema: see
[SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) "Zones".

### Derived scene geometry

The layout manager creates the scene frame, zone bounds, and baselines after
it binds and measures objects. These values are never authored in scene YAML.

### layout_rules

Scene-wide arrangement hints the layout engine consumes when
resolving zone and placement geometry. Today's `layoutRules`.
Per-placement overrides do not live here; they live on the
placement itself.

### layout engine

The shared placement system that positions object placements within
zones. It computes placement from scene YAML, the object's layout
hints, and asset metadata; renderers consume the computed placement
and produce visible DOM or SVG. Structured-surface internals may
use their own coordinate geometry declared on the object. The
layout engine is scene-side geometry; the protocol vocabulary never
reaches into it. See [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md).

### structured surface

An object with meaningful internal coordinates or subparts, such as
wells, lanes, slots, or readout marks. The structured-surface schema
is object-side; see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md), "## Structured
surfaces and subparts". The scene side only knows that a placement
references such an object by id.

### subpart

A visual or clickable element inside a structured surface. Subparts
are declared on the object via the structure block; the scene
neither declares subparts nor names them. A protocol addresses a
subpart as `<object_name>.<subpart_name>` (for example
`treatment_plate.A1`); a protocol acting on several subparts lists
each one explicitly. See
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).

### workspace

A YAML field naming the workspace family for a scene; values are
stable strings used to classify scene surface kinds. Required by the
scene YAML validator
([../../pipeline/gen_scene_index.py](../../pipeline/gen_scene_index.py));
advisory at runtime. Example:

```yaml
scene_name: <scene_name>
workspace: <workspace_kind>
```

### item

The runtime name for a clickable DOM element rendered by the
adapter and routed via `data-item-id`. Every item is the rendering of
one [placement](#placement); identity sub-fields move to the
object library, and the scene-side entry is purely a placement.

### wrong_order_message

A YAML block with two fields, `template` and `toast_duration_ms`,
declaring a per-scene wrong-order toast template. See
[scene-level UI feedback](#scene-level-ui-feedback).

### instrument-overlay

The shared modal-slot DOM element used by instrument-style scenes.
Only one scene is visible in the slot at a time. Rationale and
constraints live in [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md).

### module-load side effect

Any top-level statement in an adapter or capability module that
runs when the module is imported. Examples include
`registerScene(...)`, `registerCapability(...)`,
`registeredEmitters.add(...)`, top-level `addEventListener` calls,
and `window.*` test-API bindings. Module-load side effects only
fire if the module is imported from
`init.ts` (directly or transitively); orphaning
a module silently disables every side effect inside it. See the
dedicated "Module-load side effects" section of
[SCENE_ARCHITECTURE.md](SCENE_ARCHITECTURE.md) for the full list
and the A6a / B1 regression history.

### completion event

The string id passed to `triggerStep(stepId)` to signal that a step
has completed. Each completion-event id must be pre-registered via
`registeredEmitters.add('<event>')` at module load so the protocol
validator's coverage check (`validateCompletionEventCoverage` in
`init.ts`) can confirm every declared step has
a matching emitter at startup. Missing emitters either throw
(STRICT policy) or warn (RELAXED policy) depending on the protocol.
The event-naming convention is on the protocol side;
see [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).

The runtime mechanism `completion event` is distinct from the retired
hand-authored YAML field `completionEvent`: the runtime mechanism stays, the YAML field is retired.

### render

The adapter's `render(ctx)` method. Rebuilds the scene's DOM/SVG
and reattaches its listeners on every frame. Required (not
optional) on `SceneAdapter` since the end of the A6b migration.
Called from `runSceneRender(sceneId)` at
`src/scenes/scene_driver.ts:91-108`.

### dispatchInteraction

The adapter's `dispatchInteraction(itemId, ctx)` method. Invoked
through the `SceneContext.dispatchInteraction` callback. Today this
is the fallback path the driver uses when no mounted capability
returns `true` from `onClick` for a given item id. As more
capabilities migrate behavior off the adapter, this path will
narrow.

### SceneContext

The runtime context object created by the driver and passed to
capability and adapter methods. Defined at
`src/scenes/scene_driver.ts:21-29`. Carries `sceneId` and a
`dispatchInteraction(itemId)` callback bound to the resolved
adapter. Open for extension; capability-cross-talk fields (DOM
container, event dispatcher, item registry) are planned in later
patches.

### ClickTarget

The minimal click-event target shape the driver builds when a click
arrives on a `data-item-id` element. Defined at
`src/scenes/scene_driver.ts:12-15`. Today the only required field
is `itemId`; the index signature reserves room for
capability-specific extension.

`ClickTarget` is scoped strictly to this narrow runtime type. It is
**not** the protocol-side `target` (the semantic, geometry-free
name a protocol author writes; see
[PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md)) and **not** the
[object name](#object-name) the scene names in a placement (the object
library handle; see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md)). It is a low-level
click-event payload only. See
[The `ClickTarget` naming collision](#the-clicktarget-naming-collision).

### scene registry

The internal `SCENE_REGISTRY` map at
`src/scenes/scene_registry.ts:38`. Keyed by scene id; values are
`SceneAdapter` objects. Populated by `registerScene(adapter)` calls
that run at module load when each scene file is imported from
`init.ts`. Looked up via
`getRegisteredScene(sceneId)`. Distinct from the
[capability registry](#capability-registry).

### capability registry

The `CAPABILITY_REGISTRY` map at
`src/scenes/scene_registry.ts:18`. Keyed by capability id; values
are `SceneCapability` objects. Populated by
`registerCapability(capability)` calls that run at module load when
each capability file is imported from
`init.ts`. Read by `runScene(sceneId)` to mount
the capabilities a scene declares.

This is the runtime registry that maps a capability **id** to its
implementation. It is distinct from the object-side `capabilities`
list, which declares which affordances an object carries; see
[OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md), "## Capabilities".
