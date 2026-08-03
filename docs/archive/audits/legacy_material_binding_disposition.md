# Legacy material-binding disposition audit

## Scope and method

This is the M6 closure record for the historical object-level effect surface.
It is deliberately based on repository evidence, not on asset names or visual
guessing:

```sh
git grep -l 'render_effect: fill_height\|render_effect: material_tint' HEAD -- content/objects
source source_me.sh && python3 -m pytest tests/test_material_effect_retirement.py -q
```

The first command identifies the 48 historical effect-bearing object YAMLs:
46 object-level `fill_height` effects and two structured `material_tint`
effects. Current YAML and the recursive SVG registry determine each final
form/mechanism below. The companion M6 regression test proves that every
current object-level amount binding selects a registered material-rendered
variable-volume form and that all five such forms are selected.

There were also four formula-only `fill_height(...)` structured-subpart
entries. They were not among the 48 object-level render effects, so they are
listed separately rather than silently disappearing from the audit.

## Historical object-level effect dispositions

| Historical object YAML | Final category | Final selected form or mechanism |
| --- | --- | --- |
| `content/objects/bottle/bme_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/carboplatin_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/cell_suspension_tube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/conical_15ml.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/conical_tube_for_dilution.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/coomassie_recycle_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/coomassie_stain_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/ddh2o_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/ddh2o_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/destain_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/destain_waste_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/dmso_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/ethanol_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/laemmli_4x_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/media_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/metformin_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/metformin_working_tube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/microtube.yaml` | true variable-volume | `microtube`; compiled material gravity parts |
| `content/objects/bottle/microtube_15ml_intermediate.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/mtt_stock_tube.yaml` | true variable-volume | `falcon_50ml`; compiled material gravity parts |
| `content/objects/bottle/pbs_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/recycle_buffer_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_10x_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_1x_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/running_buffer_preparation_carboy.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/sterile_water_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/bottle/trypan_blue_tube.yaml` | true variable-volume | `falcon_15ml`; compiled material gravity parts |
| `content/objects/bottle/trypsin_bottle.yaml` | true variable-volume | `bottle_medium_pink`; compiled material gravity parts |
| `content/objects/pipette/serological_pipette.yaml` | true variable-volume | `serological_pipette`; compiled material gravity parts |
| `content/objects/bottle/protein_ladder_tube.yaml` | discrete complete-form | `protein_ladder_tube_empty` or `protein_ladder_tube_filled` |
| `content/objects/bottle/protein_sample_tube.yaml` | discrete complete-form | `protein_sample_tube_empty` or `protein_sample_tube_filled` |
| `content/objects/equipment/staining_tray.yaml` | discrete complete-form | `staining_tray_empty`, `staining_tray_buffer`, `staining_tray_stain`, `staining_tray_destain`, or `staining_tray_water` |
| `content/objects/flask/t75_flask.yaml` | discrete complete-form | `t75_flask_empty` or `t75_flask_filled` |
| `content/objects/flask/t75_flask_new.yaml` | discrete complete-form | `t75_flask_empty` or `t75_flask_filled` |
| `content/objects/bottle/mtt_solution_tube.yaml` | invalid legacy effect | static `mtt_vial`; amount has an explicit no-op visual declaration |
| `content/objects/bottle/mtt_vial.yaml` | invalid legacy effect | static `mtt_vial`; amount has an explicit no-op visual declaration |
| `content/objects/equipment/electrophoresis_inner_chamber.yaml` | invalid legacy effect | static `electrophoresis_tank_inner_chamber`; amount has an explicit no-op visual declaration |
| `content/objects/equipment/electrophoresis_outer_chamber.yaml` | invalid legacy effect | static `electrophoresis_tank_outer_chamber`; amount has an explicit no-op visual declaration |
| `content/objects/pipette/aspirating_pipette.yaml` | invalid legacy effect | static `aspirating_pipette`; aspirated amount has an explicit no-op visual declaration |
| `content/objects/pipette/micropipette.yaml` | invalid legacy effect | static `p200_micropipette_empty`; amount is explicit no-op and setpoint remains text overlay |
| `content/objects/pipette/multichannel_pipette.yaml` | invalid legacy effect | static `multichannel_pipette`; amount is explicit no-op and setpoint remains text overlay |
| `content/objects/pipette/p10_micropipette.yaml` | invalid legacy effect | static `p10_micropipette_empty`; amount is explicit no-op and setpoint remains text overlay |
| `content/objects/pipette/p200_micropipette.yaml` | invalid legacy effect | static `p200_micropipette_empty`; amount is explicit no-op and setpoint remains text overlay |
| `content/objects/waste/biohazard_decant.yaml` | invalid legacy effect | static `biohazard_decant`; amount has an explicit no-op visual declaration |
| `content/objects/waste/biohazard_decant_bin.yaml` | invalid legacy effect | static `biohazard_decant_bin`; amount has an explicit no-op visual declaration |
| `content/objects/waste/waste_container.yaml` | invalid legacy effect | static `waste_container`; amount has an explicit no-op visual declaration |
| `content/objects/equipment/hemocytometer_slide.yaml` | structured concern | `material_tint` on generated chamber geometry; amount is explicit no-op |
| `content/objects/plate/well_plate_96.yaml` | structured concern | `material_tint` on generated well geometry; amount is explicit no-op |

Totals: 29 true variable-volume, five discrete complete-form, two structured
concerns, and 12 invalid legacy effects = 48 historical effect-bearing object
YAMLs.

This table records the mechanical cutover disposition, not final pedagogical
acceptance of every static visual. In particular, an explicit amount no-op does
not establish that a nonempty material identity should remain invisible. The
intent assessment and future priorities are recorded below.

## Formula-only structured-subpart dispositions

| Historical object YAML | Final category | Final selected form or mechanism |
| --- | --- | --- |
| `content/objects/equipment/gel_cassette.yaml` | structured concern | lane amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/conical_15ml_rack.yaml` | structured concern | slot amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/dilution_tube_rack_8.yaml` | structured concern | tube amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |
| `content/objects/rack/microtube_rack_8.yaml` | structured concern | tube amount is retained as an explicit no-op; generated structured-subpart geometry is permanent |

## Final invariant

Object-level `fill_height` is now reserved for the five compiled,
material-rendered gravity-part SVG forms. All other forms are selected as
complete SVGs, remain static while retaining protocol state through explicit
no-op visual declarations, or use the separate structured-subpart mechanism.
No ordinary SVG receives a whole-object liquid effect.

## Visual-intent follow-up

### Question

Seventeen object files gained an empty `composite` visual declaration during
the semantic material-renderer cutover. This follow-up asks whether those
declarations represent intentional final behavior or merely an honest interim
state after removal of the invalid whole-object fill renderer.

Evidence date: 2026-08-03.

This is a diagnostic record, not a new authoring contract or an implementation
plan.

### Verdict

The empty composites are intentional schema declarations. They say that the
named numeric amount field remains available to protocol state, validation,
and conservation logic but produces no visual output of its own.

That does not mean every affected object is intentionally allowed to look
unchanged. The two decisions are separate:

- Removing the bounding-box fill was correct. It painted an object's full
  rectangle rather than authored material geometry and could not return.
- Making every retained state field explicit was correct. An empty composite
  keeps the missing renderer visible in object YAML instead of relying on an
  omitted binding.
- Five objects already provide a meaningful categorical visual change through
  complete-form SVG selection.
- Twelve objects remain static after material identity or amount changes. They
  are visual-design debt, with different priorities, rather than twelve
  equally intentional final designs.

The decisive specification distinction is that an exact numeric amount can be
nonvisual while the material remains visible. The canonical material
vocabulary says every non-`empty` material identity is visible. The object
format permits an explicit no-op for a field whose value does not affect the
visual; it does not turn a nonempty material into an intentionally invisible
one. See [MATERIAL_VOCABULARY.md](../../specs/MATERIAL_VOCABULARY.md)
and [OBJECT_YAML_FORMAT.md](../../specs/OBJECT_YAML_FORMAT.md).

### Defensible amount no-ops

These five objects use complete-form selection for the meaningful visible
category while retaining exact amount as nonvisual state:

| Object | Current visible behavior | Assessment |
| --- | --- | --- |
| `protein_ladder_tube` | Selects empty or filled tube art. | Exact microliter differences need not be resolved at scene scale. |
| `protein_sample_tube` | Selects empty or filled tube art. | Empty/nonempty remains visible; exact amount and material stage share the filled form. |
| `staining_tray` | `gel_state` selects empty, buffer, stain, destain, or water tray art. | The phase is visible even though exact bath volume is not. |
| `t75_flask` | Selects empty or filled flask art. | Empty/nonempty is useful; exact milliliters are intentionally coarse for now. |
| `t75_flask_new` | Selects empty or filled flask art. | Same disposition as `t75_flask`; the object is currently dormant. |

This classification does not claim that coarse rendering can never improve.
For example, a T75 flask remains "filled" when a protocol changes it from 12
mL to 4 mL. That is acceptable as a categorical visual but is weaker than
proportional authored liquid geometry.

### High-priority visual gaps

| Object | Evidence | Required future direction |
| --- | --- | --- |
| `mtt_solution_tube` | Empty, PBS, and yellow MTT solution all select `mtt_vial`. The protocol asks the learner to verify 4 mL of yellow solution. | Add authored semantic material geometry or complete forms that visibly distinguish empty, PBS, and yellow MTT solution. |
| `electrophoresis_inner_chamber` | Empty, fresh buffer, and used buffer all select the same chamber. The protocol fills it with 600 mL. | Add chamber-reservoir material geometry with an approximate visible level and material color. |
| `electrophoresis_outer_chamber` | Empty, fresh buffer, and used buffer all select the same chamber. The protocol fills it with 400 mL. | Add separate reservoir geometry; do not paint the tank's whole bounding box. |

The MTT evidence is in
[protocol.yaml](../../../content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml).
The chamber writes are in
[protocol.yaml](../../../content/protocols/sdspage/sdspage_fill_tank_buffer/protocol.yaml).
These are high priority because the authored learning flow explicitly asks the
student to observe or verify the state that the current visual does not show.

### Categorical feedback gaps

| Objects | Current limitation | Required future direction |
| --- | --- | --- |
| `aspirating_pipette` | Empty and loaded states use the same art, including a 7.9 mL transfer. | Add a loaded/empty cue; use proportional liquid only if the authored geometry makes it legible. |
| `micropipette`, `p10_micropipette`, `p200_micropipette` | Set volume is visible as text, but held material identity and amount do not change the tool. | Preserve the set-point display and add a categorical loaded-tip cue. Exact microliter height is unnecessary at scene scale. |
| `multichannel_pipette` | Empty and loaded material states use the same art. | Show loaded versus empty channels without requiring exact per-channel pixel heights. |
| `biohazard_decant`, `biohazard_decant_bin`, `waste_container` | Empty and nonempty material states use static container art. | Show empty/nonempty status and material color; add approximate accumulation where vessel geometry supports it. |

The aspirating-pipette transfer is visible in protocol state at
[protocol.yaml](../../../content/protocols/cell_culture/passage_pellet_reseed/protocol.yaml):
the tool receives 7.9 mL of supernatant, transfers it to the biohazard decant,
and returns to empty. Exact proportional rendering in a narrow tool is not
required, but showing no loaded/empty transition removes useful action
feedback.

### Dormant gap

`mtt_vial` also selects the same static art for its material states, but current
protocol and base-scene content does not reference the object. Its design gap
is real but does not currently block learner-visible behavior. Reassess it
when content begins using it rather than adding speculative art now.

### Durable implementation direction

Future work should preserve the semantic pipeline rather than restore a
generic fallback:

- Use semantic material layers and gravity parts for reservoirs or vessels
  where amount should change an authored liquid surface.
- Use complete SVG forms for meaningful categorical states such as empty,
  loaded, reacted, or used when proportional geometry adds little value.
- Use a small object-owned overlay or complete-form cue for pipette loading
  when the true liquid column is not legible at scene scale.
- Keep exact material state in the runtime even when the visual intentionally
  communicates only a category.
- Keep material color owned by the active protocol's material registry.
- Add no protocol-specific renderer branches, whole-object rectangles, local
  color fallbacks, or open-ended YAML fields.

This follows the visible-state goal in
[PRIMARY_DESIGN.md](../../PRIMARY_DESIGN.md): after a meaningful action,
the student should be able to see what changed.

### Acceptance evidence

Future fixes should use behavior-level evidence grounded in what a learner can
actually distinguish:

- MTT: empty, PBS-filled, and yellow-MTT states are visibly distinct; the
  ready-solution checkpoint shows nonempty yellow solution.
- Electrophoresis: empty and filled reservoirs are visibly distinct, and the
  inner and outer fill states are independently rendered.
- Pipettes: loaded and empty states are visibly distinct at normal scene scale;
  exact pixel height per microliter is not required.
- Waste: empty and nonempty states are visibly distinct, with material color or
  approximate accumulation where scientifically useful.
- Discrete complete-form objects: empty/nonempty or phase changes remain
  visible even when exact numeric amount has no direct rendering.

Permanent automated coverage should assert these observable categories and
semantic DOM state, not byte equality or pixel equality. Contact sheets and
side-by-side screenshots are useful one-time implementation evidence. They
should become permanent fixtures only if they meet the repository's durable
test criteria.

### Priority order

1. Fix `mtt_solution_tube`, because the learner is asked to verify a yellow
   solution that currently looks unchanged.
2. Fix both electrophoresis chambers as one reservoir-design family, because
   the learning flow teaches distinct fill levels.
3. Add loaded/empty feedback to pipette families, starting with the tools used
   in current transfer protocols.
4. Add nonempty and accumulation feedback to current waste containers.
5. Reconsider proportional T75 rendering only if learner evidence shows the
   current empty/filled distinction is insufficient.
6. Leave dormant objects until current content uses them.

### Saved conclusion

The safe statement for future reviews is:

> An empty composite is an intentional declaration that one state field has
> no direct renderer. It is not evidence that every scientifically meaningful
> state change on that object is intentionally invisible.
