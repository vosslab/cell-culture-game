# Scene inheritance

## Purpose

Scenes in the virtual lab system follow a three-layer rule to prevent drift and maintain durable workspace context:

- **Objects** are canonical-by-id with no `extends` and no template-object layer. If an object differs meaningfully from an existing one, mint a new id.
- **Protocols** are spec-shaped with no template-protocol layer. Cross-protocol reuse is via `sequence_runner` composition.
- **Scenes** use shallow inheritance (one level only) for stable workspace context. Base scenes give students a consistent visual workspace across mini-protocols, reducing cognitive load. Scene reuse is positive pedagogical value, not author convenience.

This asymmetry exists because each layer has different semantics: objects are stateful and identity-bearing; protocols are pedagogical workflows with their own learning contract; scenes are layout composition containers for shared workspaces. Objects and protocols do not use `extends`; only scenes do.

## Inheritance graph shape

Scene inheritance is strictly one level with no chains:

- **Base scenes** (`content/base_scenes/*.yaml`) extend nothing.
- **Protocol scenes** (`content/protocols/<cluster>/<name>/scenes/*.yaml`) extend exactly one base scene.
- No scene may extend a protocol scene.
- No scene may extend a scene that already extends another scene.

Cycles, multi-level chains, and unknown bases are build errors. The scene graph is fully resolvable before runtime.

## File location

Base scenes live in `content/base_scenes/*.yaml`. Protocol scenes live in `content/protocols/<cluster>/<name>/scenes/*.yaml`. A single protocol may declare multiple protocol scene files (one per scene id); each extends its own base independently.

Cross-scene transitions between different workspaces (hood to bench, plate zoom to microscope) use the `SceneChange` `scene_operation` in a step response, not inheritance.

## Schema

A protocol scene file carries these top-level fields:

- `scene_name` (required) -- unique identifier for this scene.
- `extends` (required) -- the base scene name (resolved against `content/base_scenes/`). Bare name only; no paths.
- `add_placements` (optional) -- list of new placements declared by this protocol.
- `reposition_placements` (optional) -- list of inherited placements to reposition.
- `deactivate_placements` (optional) -- list of inherited placements to deactivate.
- `remove_placements` (optional) -- list of inherited placements to remove.
- `scene_notes` (optional) -- human-readable purpose or notes.

Every other top-level key that appears in [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) is inherited from the base and may not appear in the extending file. Unknown fields in protocol scene inheritance files are build errors. The validator rejects any top-level key, any operation key, or any field inside an operation entry that is not named in this spec; new fields require a ratified spec edit.

## Base placement requirement

Every placement in a base scene must carry a stable `placement_name`. The `placement_name` is the canonical selector for all mutation operations. Selection by object name is rejected because a base scene may carry several placements of the same object.

## Field inheritance table

Inherited from base, LOCKED (extending scene may not declare these fields at all):

| Field                                                                                    | Owner       | Why locked                                                                               |
| ---------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------- |
| `workspace`                                                                              | base        | workspace identity                                                                       |
| `background`                                                                             | base        | stable student orientation                                                               |
| `zones`                                                                                  | base        | zone schema = workspace contract                                                         |
| `layout_rules`                                                                           | base        | layout-engine hints; drift risk                                                          |
| `capabilities`                                                                           | base        | workspace contract; if a protocol scene needs a capability, the base scene needs it      |
| `wrong_order_message` (base entries)                                                     | base        | base entries untouchable; extending may add entries keyed to its own new placements only |
| object `label`, `kind`, `state_fields`, `visual_states`, `capabilities`, layout defaults | object file | scene inheritance is layout composition, not object mutation                             |

Declared by the protocol scene file (LOCAL):

| Field         | Required | Notes                           |
| ------------- | -------- | ------------------------------- |
| `scene_name`  | yes      | unique per file                 |
| `extends`     | yes      | base scene name; exactly one    |
| `scene_notes` | no       | optional human-readable purpose |

Inherited from base, CHANGEABLE only via the four named operations:

| Operation               | Selector          | What it changes                                                                                                                                                                                                                           | What it may NOT change                              |
| ----------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `add_placements`        | n/a (new entries) | adds protocol-specific placements; each new placement carries its own `placement_name`. An added placement may declare only the same placement fields allowed by [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) for a base placement entry. | object identity, state, capabilities, render fields |
| `reposition_placements` | `placement_name`  | semantic membership and approved hints only: `zone`, `depth_tier`, `depth`, `align_stop` | object identity, state, capabilities, render fields, coordinates, scale, and size |
| `deactivate_placements` | `placement_name`  | marks placement as muted and non-clickable while keeping it visible for orientation                                                                                                                                                       | object identity, state, capabilities, render fields |
| `remove_placements`     | `placement_name`  | drops placement entirely                                                                                                                                                                                                                  | n/a                                                 |

## Operation order

The validator applies operations in this fixed order against the base placement set:

1. `remove_placements`
2. `deactivate_placements`
3. `reposition_placements`
4. `add_placements`

A `placement_name` referenced by `deactivate_placements` or `reposition_placements` after being removed by `remove_placements` is a build error. New `placement_name` values in `add_placements` must not collide with surviving base names.

## No generic override surface

There is no `overrides:` block, no `patch:` block, and no free-form `metadata` that could carry inherited-field mutations. The four named operations are the entire mutation surface. New operations require a ratified spec edit per [../PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md) "Vocabulary closure and anti-drift."

## Validator contract

The scene graph resolves statically before runtime. Build errors include:

- Cycles in the inheritance graph.
- Multi-level chains (base extends base, or protocol extends protocol).
- Unknown base names.
- Unknown `placement_name` references in mutation operations.
- Top-level keys outside the protocol scene schema.
- Any operation argument that targets a locked field.
- Duplicate `placement_name` values after all `add_placements` are applied.

## Deactivation explanation

Deactivation is a render-time placement flag, not an object mutation. When a placement is deactivated, it remains visible for student orientation but is muted and non-clickable. **Deactivation is placement runtime availability, not object capability mutation.** The object's declared `capabilities` list is unchanged. The renderer chooses the concrete visual treatment (grayscale, opacity, or other) and applies it to the deactivated placement's rendered SVG node.

## Promotion rule

A base scene may be promoted into `content/base_scenes/` when it is expected to serve multiple protocols OR when it represents a stable workspace contract (hood, bench, plate reader, microscope, centrifuge). Until either condition holds, the scene stays under `content/protocols/<name>/scenes/`. This rule prevents inverse drift (many one-use base scenes, each its own canonical fork) without blocking the first protocol that needs a new workspace from establishing the base. Seed workspace bases named in the migration plan count as stable workspace contracts. See [scene_inheritance_migration.md](../archive/scene_inheritance_migration.md) for the migration details.

## Asymmetry rationale

Objects, protocols, and scenes have different asymmetries by design:

- **Objects** are canonical-by-id: no `extends`, no template-object layer. Each object is a named, versioned, identity-bearing thing. See [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- **Protocols** are spec-shaped: no template-protocol layer. Similarity across protocols comes from the shared `learning -> steps -> sequence -> interaction -> response` structure, not from templates. Cross-protocol reuse is via `sequence_runner` composition (see [../PRIMARY_SPEC.md](../PRIMARY_SPEC.md)). See [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
- **Scenes** use shallow inheritance: one level only, four named operations, no generic override surface. Scenes are layout composition containers; shallow inheritance reduces student cognitive load and author duplication without introducing the drift risk of deep templates.

This asymmetry is justified by layer semantics, not consistency for its own sake, per the **fix-the-design-not-the-symptom** philosophy in [../REPO_STYLE.md](../REPO_STYLE.md).

## Worked example

### Example 1: Correct inheritance with all four operations

Base scene: `content/base_scenes/hood_basic.yaml`

```yaml
# Base scene provides stable hood workspace context
scene_name: hood_basic
workspace: hood
zones: [...]
placements:
  - placement_name: hood_waste_container
    object_name: waste_container
    zone: rear_right
  - placement_name: hood_ethanol_bottle
    object_name: ethanol_bottle
    zone: rear_left
  - placement_name: hood_optional_water_bath
    object_name: water_bath
    zone: rear_center
```

Protocol scene: `content/protocols/hood_flask_prep/scenes/hood_setup.yaml`

```yaml
# Protocol-specific scene using all four operations
scene_name: hood_flask_prep_hood_setup
extends: hood_basic
add_placements:
  - placement_name: flask_center
    object_name: t25_flask
    zone: center
  - placement_name: aspirating_pipette
    object_name: aspirating_pipette
    zone: right_tool_area
reposition_placements:
  - placement_name: hood_waste_container
    zone: center
deactivate_placements:
  - placement_name: hood_ethanol_bottle
remove_placements:
  - placement_name: hood_optional_water_bath
```

### Example 2: Forbidden mutation

The following mutation is a build error:

```yaml
# WRONG: attempting in-place field mutation (not allowed)
scene_name: hood_flask_prep_hood_setup
extends: hood_basic
reposition_placements:
  - placement_name: hood_waste_container
    capabilities: [clickable] # ERROR: capabilities is locked
    zone: center
```

Build error: `reposition_placements` may only change `zone`, `depth_tier`,
`depth`, and `align_stop`. The `capabilities` field is object-owned and locked.
Coordinates, baselines, and scale or size overrides are also rejected.

## Inheritance depth

Scene inheritance is one level: a protocol-scene extends a base scene
and a base scene does not extend another scene. Multi-level
inheritance is not part of the vocabulary.
