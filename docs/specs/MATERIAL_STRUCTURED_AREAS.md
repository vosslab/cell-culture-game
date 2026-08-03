# Structured objects with multiple material areas

This document is the single orientation reference for a class of object that
repeatedly gets misread: one scene object whose surface carries many
independent material-bearing regions. A 96-well plate, a tube rack, and a gel
cassette are the canonical examples. Each is ONE SVG scene object, not a
collection of many objects, and its wells, tubes, or lanes are material areas
rendered on that one object.

This is a rationale and orientation doc in the style of
[MATERIAL_DESIGN.md](MATERIAL_DESIGN.md). It states the model and points every
schema term at its owning doc. It introduces no new field or token. Where a
term is named below, it is named for orientation and linked to the doc that
owns it.

It exists because the design lives correctly across several specs
([OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md),
[MATERIAL_DESIGN.md](MATERIAL_DESIGN.md),
[MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md), and the
[subpart-click decision](../archive/decisions/subpart_click_pattern.md)),
and reading only one of them invites a wrong conclusion. The common wrong
conclusions are listed in [What this is not](#what-this-is-not); read that
section before proposing any change to a plate, rack, or gel.

## The core rule: one object, many material areas

A structured object is a single scene object placed by the layout engine, with
a single underlying SVG asset. Its internal cells (wells, tubes, lanes, slots,
channels) are addressable subparts declared in the object's `structure` block
(see [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) Structure). A subpart is a
region on the one object, not a scene object of its own.

The reason is deliberate: a 96-well plate is one physical thing a student sees
and reaches for as one thing. Rendering it as many scene objects would multiply
layout work, multiply click targets, and break the "one object, one placement"
model the layout engine and the material system are built on. The plate stays
one object; the wells are material areas on it.

Generated geometry ties each subpart to its real position on the art, so a
region colored for well B7 sits on B7 and nowhere else. That alignment is a
pedagogical requirement, not a cosmetic one; see
[MATERIAL_DESIGN.md](MATERIAL_DESIGN.md) spatial correspondence.

## M8 decision: generated geometry is permanent for structured material areas

Generated geometry is the canonical and permanent rendering model for wells,
rack slots, and gel lanes. It is deliberately separate from a material-rendered
vessel SVG. The 96-well plate evidence is recorded in the
`docs/archive/decisions/structured_subpart_render_model.md` decision:
the source illustration has many anonymous transformed well paths but no
durable A1-H12 semantic namespace, whereas generated geometry already has
those named, typed, build-validated regions in the asset's exact viewBox.

The production browser spike also verified that 96 independent per-well state
writes complete within the stated browser-frame budget. Performance is therefore
not a reason to move the geometry into the SVG, and such a move would duplicate
the existing spatial mapping while adding donor-path classification and export
risk. A structured base asset remains opaque; its material areas render through
`subpart_geometry`. This is an intentional permanent split, not an incomplete
material-SVG migration. Its material overlay remains `pointer-events: none`.
The separate existing `subpart_hit_surface.tsx` component owns exact generated
hit targets for active subpart interactions; M8 does not alter that component
or its interaction behavior.

## Boundary with material-rendered SVG forms

Structured subparts and material-rendered SVG forms solve different geometry
problems. A plate's wells, rack slots, and gel lanes use generated per-subpart
geometry because they are many independently addressed material areas on one
object. A material-rendered vessel form uses semantic groups inside one SVG
because its own liquid layers need recoloring and gravity-part amount behavior.
The latter contract is owned by [SVG_PIPELINE.md](SVG_PIPELINE.md); it neither
replaces nor generalizes the structured-subpart mechanism.

SVG selection and rendering remain independent. A discrete collection can
select complete forms, and any selected form can independently be static or
material-rendered. That does not turn each well, lane, or slot into a semantic
SVG layer recipe, and it does not create a general animated-SVG feature. The
M8 structured-subpart decision remains the boundary for any future conversion
proposal; it requires evidence before changing the current generated-geometry
mechanism.

## Subparts are material areas, not new objects

Each subpart carries its own material state and renders its own material
identity. The object declares that its per-subpart region is tinted by that
subpart's material through the `material_tint` render effect with
`applies_to: subpart` (see [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md)
render-effect set). At render time the runtime reads each subpart's material
field and tints that subpart's generated geometry to the resolved color.

This reuses the exact material model that colors a bottle's liquid: a neutral
region tinted by whatever material it currently holds. A well holding
carboplatin and a bottle holding PBS are the same mechanism at two scales. The
material owns the color; the object owns where the color appears; TypeScript
interprets the declared contract and hardcodes neither. See
[MATERIAL_DESIGN.md](MATERIAL_DESIGN.md) for that ownership split.

Per-subpart state fields (the material name and volume each subpart stores) are
declared with `structure.subpart_state_fields` on the object
([OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)). The subpart is a state-bearing
material area; it is not a separate object with its own placement.

## Group addressing and the cascade write

Real lab actions often act on many cells at once: a plate-wide reagent
addition, a multichannel column sweep, a row read. Enumerating every cell in
the protocol would bury the intent. A structured-grid object may therefore
declare higher-granularity namespaces through `structure.subpart_groups`, with
a closed `group_kind` of `row`, `column`, or `region`
([OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) Subpart groups). Each group
member lists the canonical cells it contains.

A protocol addresses a group the same way it addresses one cell, through a
dotted target on one object, for example `well_plate_96.all_wells` or
`well_plate_96.col_3`. When an `ObjectStateChange` names a group target, the
write propagates the named fields to every cell in that group's `contains`
list; each member cell changes in its own place. This cascade write is the
design of record, first proposed in the
[subpart-addressing recommendation](../archive/subpart_addressing_recommendation.md)
and rendered through the per-subpart material layer above. A bulk write like
`all_wells` is meant to color exactly its member wells, each at its own
position (see [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md) spatial correspondence).

Group addressing does not violate the protocol vocabulary's "no named-group
construct" rule. That rule binds the PROTOCOL layer: an author cannot invent a
group by editing protocol YAML. Groups are declared on the OBJECT, and the
protocol still names one target. The object schema is what fans the write out.
See [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md) "Grouped targets are listed
explicitly" and [PRIMARY_SPEC.md](../PRIMARY_SPEC.md).

## Clicking versus writing state: distinct generated surfaces

A subpart material overlay is not a click target: it renders with
`pointer-events: none`. That does not mean a structured subpart can never be
an active interaction target. When an active dotted target resolves to declared
generated geometry, the separate
`src/scene_runtime/renderer/subpart_hit_surface.tsx` renders exact generated
hit shapes. Those are enabled only for the active subpart interaction and keep
the base plate, rack, or gel as one scene object. The subpart or group name can
therefore be addressed either by the interaction or by its response's
`ObjectStateChange`; the material overlay remains purely visual.

Two cases follow, and keeping them apart is what avoids the recurring
confusion:

- A group or non-discrimination subpart STATE-WRITE (for example `all_wells`, a
  column, a technique-only single lane) is correct as authored. The student
  may click the base object; the response writes the subpart or group state; the
  material layer colors the member cells. Nothing about this requires activating
  the separate hit surface.
- A discrimination-bearing subpart interaction activates exact generated hit
  shapes through `subpart_hit_surface.tsx`, allowing the learner to select the
  declared cell, slot, or lane while sibling geometry remains independently
  addressable for ordinary validation.

The dividing line is the taught skill, not the target shape. A subpart target
is in the held class only when picking the correct subpart is the discrimination
the protocol grades. Bulk group writes and technique-only single-subpart steps
are not.

## What this is not

Read this before proposing any change to a plate, rack, or gel. Each item below
is a wrong conclusion that a partial reading produces.

- A structured object is NOT many scene objects. Do not split a plate into
  per-well objects or place wells through the layout engine. One object, one
  placement; the wells are material areas.
- `well_plate_96.all_wells` in an `ObjectStateChange` is NOT a bug, a
  regression, or a missing placement. It is the ratified group cascade write.
  Do not flatten it to bare `well_plate_96` and do not expand it to individual
  per-well writes.
- `subpart_groups` is NOT an open escape hatch and NOT a protocol-layer
  named-group violation. It is a closed, build-validated object-schema block
  with a closed `group_kind` enum, declared on the object, consumed as one
  target by the protocol.
- An active subpart target that fails to resolve to declared generated geometry
  is a content/runtime error, not permission to fall back to a broad parent
  target. The material overlay remains non-interactive; the exact hit surface
  owns active subpart pointer targets.
- The absence of `subpart_groups` handling under
  `src/scene_runtime/protocol/` does NOT mean the cascade is unimplemented. The
  per-subpart material rendering lives in the renderer and material layer
  (`src/scene_runtime/renderer/subpart_dispatch.ts`,
  `subpart_visual_state_renderer.tsx`).

## Reading map

| Question                                                           | Owning doc                                                                           |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| How is the subpart namespace and `subpart_groups` schema declared? | [OBJECT_YAML_FORMAT.md](OBJECT_YAML_FORMAT.md)                                       |
| Why are wells material areas, and what is spatial correspondence?  | [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md)                                             |
| Which render effect and target tint a subpart region?              | [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md)                                     |
| What are the closed material terms?                                | [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)                                     |
| Why does clicking hit the base object, not the subpart?            | [subpart-click decision](../archive/decisions/subpart_click_pattern.md)              |
| Where did group addressing and the cascade write originate?        | [subpart-addressing recommendation](../archive/subpart_addressing_recommendation.md) |
| What are the layer-ownership and target-addressing invariants?     | [PRIMARY_SPEC.md](../PRIMARY_SPEC.md), [PRIMARY_DESIGN.md](../PRIMARY_DESIGN.md)     |
