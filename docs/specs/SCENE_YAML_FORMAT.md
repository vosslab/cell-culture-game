# Scene YAML format

Scene terminology is defined in [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).
This doc uses that vocabulary. Where this doc names a section without
restating its meaning (for example "zone" or "placement"), the vocabulary
doc is the authority.

This document specifies the per-scene YAML schema in its cleaned, post-split
form. A scene YAML file declares one workspace surface: scene identity, a
static background, named placement zones, a list of object placements (each
referencing an object from the object library by id), and the layout-rule hints
the layout engine consumes. Scene YAML is coordinate-free: the layout manager
derives scene bounds, zone bounds, and baselines after it measures the objects.
Object identity,
state, and the state-to-visual map live in object YAML
([OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)). Protocol steps and
state-mutating operations live in protocol YAML
([PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md)).

Object identity, state_fields, visual_states, and capabilities are declared
object-side and do not appear on the scene side.
Each scene `items[]` entry is replaced by a `placements[]` entry that
references an object by id and carries only placement and instance-override
surface.

## Purpose

Scene YAML is build-time runtime configuration for scene metadata, named
placement zones, and object placements. It is not a behavior language.
TypeScript adapters and capabilities own rendering, state mutation, events,
side effects, and DOM behavior. The object library
([OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)) owns object identity and
the state-to-visual map.

Scene YAML is engine-facing configuration consumed by the build-time
generator (`pipeline/gen_scene_index.py`) and at runtime by the scene
renderer (`src/scene_runtime/renderer/`) and by mounted capabilities
under `capabilities`. It is distinct from protocol YAML and from object YAML.

## File location

Shared base scenes are authored under `content/base_scenes/<base_scene_name>.yaml`.
Protocol-scoped scene overrides (when needed) live under
`content/protocols/<cluster>/<protocol_name>/scenes/<scene_name>.yaml`. The
generator at build time consumes these YAML files; no scene YAML lives under
`src/`.

Author-facing protocol content lives under `content/protocols/<cluster>/<protocol_name>/`.
Object library files live under `content/objects/` (see
[OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)).

## Build pipeline

Scene YAMLs are compiled at build time. The chain is:

```
content/base_scenes/<base_scene_name>.yaml                       (shared base scenes)
content/protocols/<cluster>/<protocol_name>/scenes/<scene_name>.yaml  (protocol-scoped overrides)
        |
        v
pipeline/gen_scene_index.py  (validate + emit; reads generated/object_library.ts)
        |
        v
generated/scenes.ts          (AUTO-GENERATED, gitignored; do not hand-edit)
        |
        v
pipeline/precompute_layout.mjs  (runs layout engine; reads generated/scenes.ts)
        |
        v
generated/precomputed_layout.ts  (AUTO-GENERATED, gitignored; do not hand-edit)
```

The generated `scenes.ts` file carries an auto-generated header. The
precomputed layout file carries build-time layout results consumed at
render time by `src/scene_runtime/layout/precomputed_result.ts`.

The build is invoked by [build_github_pages.sh](../../build_github_pages.sh)
via `pipeline/build_generated.sh` (runs the four generators in canonical
order) followed by `pipeline/precompute_layout.mjs`. To regenerate after
YAML edits, run `bash pipeline/build_generated.sh` then
`node --import tsx pipeline/precompute_layout.mjs`.

## Top-level fields

Every scene file is a single YAML mapping with the following top-level
keys. The "Section" column links to the per-section detail below.

| Field                 | Type            | Required           | Section                                       |
| --------------------- | --------------- | ------------------ | --------------------------------------------- |
| `scene_name`          | string          | yes                | [Scene identity](#scene-identity)             |
| `workspace`           | string          | yes                | [Scene identity](#scene-identity)             |
| `capabilities`        | list of string  | yes                | [Capability names](#capability-names)         |
| `background`          | mapping         | no                 | [Background](#background)                     |
| `zones`               | list of mapping | yes (may be empty) | [Zones](#zones)                               |
| `placements`          | list of mapping | yes (may be empty) | [Placements](#placements)                     |
| `layout_rules`        | mapping         | no                 | [Layout rules](#layout-rules)                 |
| `wrong_order_message` | mapping         | no                 | [Wrong-order messages](#wrong-order-messages) |

The cleaned scene-YAML top-level keys cover scene identity, the static
background, semantic scene arrangement (`zones`, `layout_rules`), the placement
list, capability declarations,
and the scene-level UI-feedback string. Object identity, state, and the
state-to-visual map are object-side; see
[Migration from the fused format](#migration-from-the-fused-format) for
every key and sub-field that moved off the scene side.

## Scene identity

The scene identity block names the scene and the workspace it targets.
These are scene-side fields; they are not object identity.

| Field        | Type   | Required | Meaning                                                                                                                                                                                                  |
| ------------ | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scene_name` | string | yes      | Stable scene name. Must match the scene directory name and the adapter `sceneId`.                                                                                                                        |
| `workspace`  | string | yes      | Workspace family this scene targets (`equipment_bench`, `wet_lab_hood`, `modal_overlay`, `dedicated_plate`). Today advisory; the field is required so future selectors and telemetry have a stable name. |

At runtime, the scene driver derives the DOM mount element id as `${scene_name}-scene`. This is an internal runtime handle, not an authored YAML field. Scenes that use a custom DOM id (such as the `cell_culture_hood` scene using `hood-scene`) override this mapping through a separate, non-YAML configuration path.

## Background

A scene background is a pure, static backdrop. The renderer paints
the background asset under everything else; the background is not
interactive and carries no state. A clickable region that authors might once
have drawn into the background image (a sink, a benchtop edge, a tool drop
zone) is not a background sub-field. It is an object placed over the
backdrop through `placements[]`; the object library declares what the
region is (identity, capabilities such as `clickable`, `visual_states`).

| Field               | Type           | Required                      | Meaning                                                                                                                |
| ------------------- | -------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `background.asset`  | string         | yes (if `background` present) | Asset id (image or SVG) used as the static backdrop. The asset library resolves the file.                              |

The cleaned scene YAML never declares clickable behavior on the background
and never attaches state, capabilities, or visual_states to it. State and
behavior live on objects; see
[OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).

## Derived scene geometry

`scene_bounds`, zone `bounds`, and zone `baseline` are internal geometry,
derived by the layout manager. They never appear in authored scene YAML. The
same rule forbids source `x`, `y`, `left`, `right`, `top`, `bottom`,
`position`, `scale`, `width_scale`, `baseline_override`, and scene-side size
overrides.

## Zones

A zone is a named, ordered semantic group. Its declaration order, measured
placement demand, and approved alignment hint guide the layout manager; the
name itself is not a coordinate instruction. Zones are scene-side because they
describe semantic grouping, not object identity, state, or rendering. See
[LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) for derived layout behavior.

| Field        | Type           | Required | Meaning                                                                                                                                          |
| ------------ | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `zone_name`  | string         | yes      | Stable zone name, scoped to this scene. Placements reference it via `placement.zone`. Zone names must be unique within the scene.                |
| `align`      | enum           | no       | Arrangement rule for placements inside the zone. Includes `tab-stops` (paired with per-placement `align_stop`) and `center`.                     |
| `label`  | string         | no       | Optional human-readable label for authoring and debugging.                                                                                  |

Example:

```yaml
zones:
  - zone_name: back_row
    align: tab-stops
```

Zone `bounds`, `baseline`, and coordinate sub-fields are forbidden source
geometry. `align` and [Layout rules](#layout-rules) are the bounded scene-side
layout inputs.

## Placements

A placement entry references one object from the object library by name and
states where that placement goes inside a zone. The placement does not
declare object identity, structure, `state_fields`, `visual_states`, or
`capabilities`; those belong to the object definition (see
[OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)).

A placement may not override object identity. The identity tuple
`(object_name, kind, label)` is owned by the object library and is
locked from scene-side override. A placement may carry instance overrides
only for categorical `layout.anchor_y` and `layout.label_placement`. A placement may not
override `state_fields`, `visual_states`, or `capabilities`. The
boundary rule is authoritative; see
[OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) for the full
object-side field list and which fields may be overridden.

| Field               | Type                  | Required | Meaning                                                                                                                                                                                                                                              |
| ------------------- | --------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `placement_name`    | string                | yes      | Stable per-scene name for this placement. Distinct from `object_name`: a scene may place the same object more than once, and each placement needs its own scene-scoped name (for example two `dilution_tube_rack` instances).                        |
| `object_name`       | string                | yes      | Name of the object in the object library. The object resolves identity, structure, `state_fields`, `visual_states`, and `capabilities`.                                                                                                              |
| `zone`              | string                | yes      | Zone name this placement belongs to. Must match a declared `zones[].zone_name`.                                                                                                                                                                      |
| `depth_tier`        | int                   | no       | Numeric layering hint within the zone (front-to-back ordering).                                                                                                                                                                                      |
| `align_stop`        | enum                  | no       | One of `left`, `center`, `right`. Tab-stop group for the layout engine.                                                                                                                                                                              |
| `layout`            | mapping               | no       | Optional categorical hints: `anchor_y` and `label_placement`. |

Notes:

- A placement may not declare or modify subparts; those are
  object structure; the scene never authors `subpart_name`.
- A placement may not declare state or visual_states; the object owns state
  and rendering, and the protocol mutates state semantically through
  `ObjectStateChange` (see
  [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md)).
- `layout` may contain only `anchor_y` and `label_placement`; it cannot change
  object dimensions or inject numeric geometry.

Example placement:

```yaml
placements:
  - placement_name: hood_flask
    object_name: t75_flask
    zone: back_row
    depth_tier: 4
    align_stop: center
    layout:
      anchor_y: bottom
```

## Inheritance

Scenes support shallow inheritance for stable workspace context. Protocol
scenes may extend a single base scene and apply four named operations to
inherited placements. For the complete inheritance rule, constraints, and
worked examples, see [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md).

The five inheritance keys are:

- `extends` -- base scene name (required in an extending scene)
- `add_placements` -- new placements declared by the protocol scene
- `reposition_placements` -- reposition inherited placements by placement_name
- `deactivate_placements` -- deactivate inherited placements by placement_name
- `remove_placements` -- remove inherited placements by placement_name

Base placements must declare a stable `placement_name` so that mutation
operations can select them reliably.

Example protocol scene extending a base:

```yaml
scene_name: hood_flask_prep_hood_setup
extends: hood_basic
add_placements:
  - placement_name: flask_center
    object_name: t25_flask
    zone: center
reposition_placements:
  - placement_name: hood_waste_container
    zone: rear_right_far
deactivate_placements:
  - placement_name: hood_ethanol_bottle
remove_placements:
  - placement_name: hood_optional_water_bath
```

## Layout rules

The optional `layout_rules` block carries scene-wide hints the layout
engine needs to resolve placements. Per-placement overrides go on the
placement, not here. See [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md).

| Field                    | Type                     | Required | Meaning                                                                                        |
| ------------------------ | ------------------------ | -------- | ---------------------------------------------------------------------------------------------- |
| `default_align_stop`     | enum                     | no       | Default alignment for placements that do not specify `align_stop` (`left`, `center`, `right`). |
| `label_font_size`        | number (float or int)    | no       | Font size for placement labels (in pixels; must be positive).                                  |
| `label_line_height`      | number (float or int)    | no       | Line height for placement labels (must be positive).                                           |
| `label_offset_y`         | number (float or int)    | no       | Label offset hint relative to the manager-derived object anchor. |
| `label_placement`        | enum (`top` or `bottom`) | no       | Scene-wide label position relative to the object. Default `top` (labels render above artwork). Per-placement `layout.label_placement` overrides this. |
| `zone_gap`               | number (float or int)    | no       | Preferred separation between semantic zones. |

Example:

```yaml
layout_rules:
  default_align_stop: center
  label_font_size: 12
  label_line_height: 1.2
  label_offset_y: 5
  label_placement: top
  zone_gap: 3
```

## Accent rules

The optional `accent_rules` block defines styling overrides for placements
keyed by an accent key. Each key maps to an object with optional stroke,
fill, and pattern fields.

| Field   | Type    | Meaning                                                                                                                         |
| ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `<key>` | mapping | Styling rules for placements that reference this key. Contains optional `stroke` (string), `fill` (string), `pattern` (string). |

Example:

```yaml
accent_rules:
  highlight_active:
    stroke: "#ff6b6b"
    fill: "#ffe0e0"
  highlight_used:
    stroke: "#4ecdc4"
    fill: "#e0f9f7"
```

## Wrong-order messages

| Field               | Type                  | Required               | Meaning                                         |
| ------------------- | --------------------- | ---------------------- | ----------------------------------------------- |
| `template`          | string                | yes (if block present) | Toast text with `{expected_label}` placeholder. |
| `toast_duration_ms` | number (float or int) | no                     | Toast lifetime in milliseconds.                 |

`wrong_order_message` is scene-side because it is a property of how this
scene gives feedback, not of any one object's identity or state.

## Capability names

Six capability ids are registered in
`capabilities` and mounted at
module load via `src/init.ts`. The cleaned scene YAML declares the
capabilities a scene mounts; object capabilities (`clickable`,
`material_container`, `instrument_with_setpoint`, `structured_surface`,
`cursor_attachable`, `decoration_only`) are object-side and live in
object YAML. This is the closed six-capability set.

| Capability id             | Purpose                                                                                     | Status                                                                              |
| ------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `item_workspace`          | Click routing for object placements; dispatches `data-item-id` clicks to the scene adapter. | Consumes `placements` and `zones`.                                                  |
| `modal_workspace`         | Modal-screen scenes (microscope, plate, plate_reader).                                      | Validates `scene_name` only.                                                        |
| `instrument_workspace`    | Instrument workspace (microscope automated counter).                                        | Validates `scene_name` only.                                                        |
| `grid_counting_workspace` | Grid-quadrant counting (manual hemocytometer).                                              | Validates `scene_name` and an optional `quadrants` array; dispatches click routing. |
| `incubator_workspace`     | Incubator overlay flow.                                                                     | Validates `scene_name` only.                                                        |
| `plate_reader_workspace`  | Plate-reader modal (results table).                                                         | Validates `scene_name` only.                                                        |

## Validation rules

The validator in [../../pipeline/gen_scene_index.py](../../pipeline/gen_scene_index.py)
enforces these rules against the fused format:

- The YAML root must be a mapping.
- `scene_name` is required and must be a non-empty string.
- `workspace` is required and must be a non-empty string.
- `capabilities` is required and must be a list of strings.
- Each capability id must be in the validator's allow list.
- Capability ids within one scene must be unique.
- `zones`, if present, must be a list of mappings each with a non-empty
  string `id`. Zone ids must be unique within the scene.
- `placements`, if present, must be a list of mappings. Every
  `placement.object_name` must resolve against the object library, every
  `placement.zone` must match a declared `zones[].zone_name`, and per-placement
  override fields must be in the override surface.

Gaps not validated today:

- Capability-specific config blocks are not enforced.
- Placement field shapes beyond `object_name` and `zone` are not validated.
- Zone field shapes beyond `id` are not validated.
- `wrong_order_message` is not validated.
- Cross-references against `materials.yaml` and the object library are not validated.

## Sub-fields and primitives that never appear in scene YAML

The following identifiers are explicitly object-side or protocol-side in the
cleaned vocabulary and must not be authored in scene YAML:

- `state_fields`, `visual_states`, `structure`,
  `capabilities` (the object affordance tags) -- object YAML; see
  [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).
- `ObjectStateChange`, `CursorAttach`, `SceneChange`, `LayoutMove`,
  `TimedWait` -- protocol primitives; see
  [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md).
- `SvgSwap`, `ColorChange`, `LiquidDisplayChange`, `SetPointDisplayChange` --
  object/render-layer mechanisms; never authored in scene YAML or
  protocol YAML. See
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md#visual-states) for the
  canonical statement and the `ObjectStateChange` boundary.

## What scene YAML must not contain

- No inline JavaScript or TypeScript.
- No behavior hooks, callbacks, or expressions.
- No state mutations or side effects.
- No defensive defaults that hide missing required fields. A missing
  required field must fail the build loudly, not silently fall back.
- No object identity (`object_name`, `kind`, `label`), `state_fields`,
  `visual_states`, or object affordance capabilities. These are
  object-side per [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md).
- No SVG asset ids and no color values. The object's `visual_states` is the
  only authoring surface that resolves a state value to an asset or color.
- No protocol primitives or step content. Steps and `ObjectStateChange`
  live in [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md).
- No clickable behavior on the background. Clickable regions are objects
  placed over the backdrop.

## Examples

Minimal scene (modal overlay, no placements):

```yaml
scene_name: incubator
workspace: modal_overlay
capabilities:
  - incubator_workspace

zones: []
placements: []

wrong_order_message:
  template: "Proceed with the {expected_label}."
  toast_duration_ms: 2000
```

Scene with placements and a background:

```yaml
scene_name: bench
workspace: equipment_bench
capabilities:
  - item_workspace

background:
  asset: bench_backdrop

zones:
  - zone_name: back_shelf
    align: tab-stops
  - zone_name: mid_bench
    align: tab-stops

placements:
  - placement_name: bench_centrifuge
    object_name: centrifuge
    zone: mid_bench
    depth_tier: 1
    align_stop: left
  - placement_name: bench_water_bath
    object_name: water_bath
    zone: mid_bench
    depth_tier: 2
    align_stop: left
  - placement_name: bench_tip_box
    object_name: tip_box
    zone: back_shelf
    depth_tier: 1
    align_stop: left

layout_rules:
  zone_gap: 3
  default_align_stop: left

wrong_order_message:
  template: "Try the {expected_label}."
  toast_duration_ms: 2000
```

Each placement names an object from the object library by `object_name` and
states where it goes; the object library file resolves identity, the
state-to-visual map, and capabilities.

## Related docs

- [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) - Canonical scene-system terms.
- [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md) - Canonical object terms.
- [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) - Object library YAML
  schema (the target of every scene `placements[].object_name`).
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md) - Protocol YAML
  schema; declares steps and `ObjectStateChange`.
- [LAYOUT_ENGINE.md](LAYOUT_ENGINE.md) - How the layout engine consumes
  zones, placements, and `layout_rules`.
- [SCENE_ARCHITECTURE.md](SCENE_ARCHITECTURE.md) - Scene driver, capability
  registry, and the runtime wiring.
- [SVG_PIPELINE.md](SVG_PIPELINE.md) - SVG asset ownership boundary.
