# WOW scene gallery audit

## Scope and evidence

This is a visual audit of the current shipped `dist/` pages, served over local HTTP by
`tools/protocol_to_png.mjs`. It is not a source review and does not claim that an
interaction can be completed; it evaluates the initial, student-visible state.

- Desktop capture: 1440 x 1000.
- Tablet capture: 1024 x 900.
- Capture date: 2026-07-22.
- Both capture runs loaded 31 of 31 protocol pages as `populated`: a shell, a guidance
  bar, and at least one rendered scene object were present.
- The scene-stat figures below are the existing 1920 x 1080 renderer measurements. They
  are useful for identifying placeholders and collision/crop regressions, but they do
  not measure learning quality or active-target prominence.

The full contact sheets are `test-results/wow_scene_gallery/desktop_contact_sheet.png`
and `test-results/wow_scene_gallery/tablet_contact_sheet.png`. Individual files are
indexed below so a later reviewer can open the same evidence without rebuilding.

## Capture index

Every protocol has a pair of captures:
`../../../test-results/wow_scene_gallery/protocol_desktop/<protocol>.png` and
`../../../test-results/wow_scene_gallery/protocol_tablet/<protocol>.png`.

| Protocol | Initial items |
| --- | ---: |
| cell_seeding_plate_setup | 10 |
| drug_dilution_setup | 10 |
| mtt_plate_reaction | 9 |
| mtt_reagent_prep | 6 |
| mtt_solubilization_readout | 6 |
| passage_hood_detachment | 5 |
| passage_pellet_reseed | 12 |
| plate_drug_treatment_drug_addition | 10 |
| plate_drug_treatment_media_adjustment | 8 |
| trypan_blue_counting | 8 |
| cell_culture_full | 5 |
| routine_passage | 5 |
| sdspage_full | 16 |
| sdspage_load_samples_batch | 17 |
| sdspage_prepare_sample_mix_batch | 11 |
| sdspage_assemble_electrode_module | 16 |
| sdspage_attach_lid_and_leads | 16 |
| sdspage_destain_gel_rock | 10 |
| sdspage_destain_gel_setup | 10 |
| sdspage_extract_gel_from_cassette | 17 |
| sdspage_fill_tank_buffer | 16 |
| sdspage_heat_denature_samples | 12 |
| sdspage_image_gel | 11 |
| sdspage_load_protein_ladder | 16 |
| sdspage_load_sample_single_lane | 17 |
| sdspage_prepare_gel_cassette | 16 |
| sdspage_prepare_running_buffer | 16 |
| sdspage_prepare_sample_mix_single_lane | 11 |
| sdspage_recycle_buffer | 16 |
| sdspage_run_electrophoresis | 16 |
| sdspage_stain_gel | 10 |

## Ranked representative findings

Rank is based on student impact, recurrence, and whether the defect obscures the action.
The eight scenes deliberately span both the strongest readable assets and the weakest states.

| Rank | Evidence and scene | What a student sees | Classification | Reusable corrective direction |
| ---: | --- | --- | --- | --- |
| 1 | `sdspage_fill_tank_buffer` (desktop and tablet captures) | A 16-object electrophoresis bench has five placeholders and no visually dominant tank. Labels stay associated and no crop is apparent, but the active tank competes with scattered tips, bottles, and blank space. | Renderer asset-library defect plus scene-composition defect. Stats: 5 placeholders, 68.8% render yield, 93.5% empty. | Add all missing scientific-object assets first; then add a shared active-workspace composition mode that groups the required object, tool, and source material while visually recessing everything else. |
| 2 | `cell_seeding_plate_setup` (desktop and tablet captures) | The incubator, vortex, and hood surface render as placeholders. The long numeric prompt is visible but becomes tiny at tablet width, and the student is asked to calculate before the scene makes a clear action target. | Renderer asset-library defect; prompt/pedagogy issue is protocol content. Stats: 3 placeholders, 70.0% yield, 95.6% empty. | Shared prompt treatment needs a concise imperative plus expandable calculation context. Replace the three missing lab assets; author the calculation as a dedicated visible substep, not a wall of guidance. |
| 3 | `mtt_plate_reaction` (desktop and tablet captures) | The plate, incubator, and pipette are recognizable, but the screen reads as an inventory spread. The required 96-well plate is not the clear visual center, and a pink outline card does not compensate. | Shared active-target salience and composition defect. Stats: 3 placeholders, 66.7% yield, 89.7% empty. | Treat the selected/required object as the scene focal point: scale or zoom its workspace group, dim unrelated objects, and make the active affordance use one consistent visual grammar. |
| 4 | `trypan_blue_counting` (desktop and tablet captures) | The automated counter is readable, yet the task begins with tiny isolated tubes and a dilute grid of labels. The real learning object, the cell-count result, is neither enlarged nor visibly tied to the prompt. | Shared pedagogy-to-scene binding defect; `cell_counter` is also missing. Stats: 2 placeholders, 77.8% yield, 96.0% empty. | Add a reusable result/readout focus state and an explicit visual before/after for the counted cells. Supply the counter asset or make the existing instrument readout the primary scene object. |
| 5 | `passage_hood_detachment` (desktop and tablet captures) | This is among the clearest frames: the microscope is large and recognizable, and its active outline is unambiguous. Still, the crucial flask and medium samples are tiny and visually disconnected from the microscope task. | Scene-specific composition/content refinement; renderer passes its basic geometry checks. Stats: 2 placeholders, 66.7% yield, 93.7% empty. | Preserve this large-instrument scale as a reusable reference. For this protocol, promote the flask/sample pair into the microscope focus state rather than leaving them as distant inventory. |
| 6 | `drug_dilution_setup` (desktop and tablet captures) | Color-coded reagents help, labels associate cleanly, and the shell remains responsive. The actual dilution sequence is still hard to infer because the plate, stock, and pipette do not form a clear left-to-right action path. | Predominantly scene-specific content/composition issue; one missing vortex asset. Stats: 1 placeholder, 90.9% yield, 96.4% empty. | Use a reusable staged-flow overlay for source -> tool -> destination, then author the dilution protocol to expose the relevant concentration/volume state at each stage. |
| 7 | `mtt_reagent_prep` (desktop and tablet captures) | The sparse bench has no object collisions or crop, but so much beige space that the MTT vial and PBS look like unrelated icons. The initial instruction is visible but too small to carry the learning flow alone. | Shared shell/scene proportion defect plus one missing vortex asset. Stats: 1 placeholder, 85.7% yield, 97.0% empty. | Reserve more of the shell for the experiment at this density, and let a focused work tray expand around the currently required reagents. |
| 8 | `sdspage_image_gel` (desktop and tablet captures) | The rocking shaker, staining tray, and lightbox make this the most visually distinctive SDS-PAGE scene. Their relationship is nevertheless not staged: students see a warehouse of equipment instead of a gel moving through a workflow. | Scene-specific workflow narration; two missing assets. `imaging_bench` stats: 2 placeholders, 83.3% yield, 89.2% empty. | Keep the strong assets, but show one gel specimen moving between the tray, lightbox, and image/result; make the current station large and the next station anticipatory. |

## Cross-scene diagnosis

### What is working

- No measured item, label, or artwork crop/overlap was reported in the eight scene-stat
  files. The responsive shell also remains present at 1024 px.
- Labels associate to objects well enough to identify inventory, and several richer assets
  (microscope, incubator, vortex, counter screen, staining tray, and rocking shaker) prove
  that the desired visual language is already possible.
- Guidance and outline are consistently visible. That is a sound completion scaffold.

### Renderer/runtime defects

- Placeholder art is a systemic quality failure, not a one-off scene flaw. The sampled
  scenes have 1-5 placeholders each. Missing objects include core teaching equipment:
  incubator, vortex, microscope, cell counter, hood surface, gel comb, power supply, and
  loading-tip box.
- The renderer is technically solving collision avoidance, but scenes measure about
  89-97% empty. This produces an object catalogue rather than a workbench.
- The shared shell gives the scene a large visual field, yet the central guidance text is
  small and wraps into a dense strip at tablet width. It lacks the hierarchy to translate
  protocol language into a first action.
- The current active outline is useful on the microscope but inconsistent as a focal system:
  it does not create an obvious action path among related objects or communicate why an
  inactive object is present.

### YAML/content and pedagogy issues

- Several initial prompts begin with dense calculations or multi-part instructions before
  establishing the physical action. That is especially risky for open-book learners who
  need a visible relationship between the quantity, the tool, and the destination.
- Inactive objects remain equally available and equally prominent. Scenes need authored
  roles: `active`, `supporting`, `next`, and `parked`, rather than treating every declared
  object as a same-priority bench item.
- The strongest assets rarely demonstrate state change. A protocol should show the student
  a vessel filling, a gel moving, an instrument displaying a result, or a plate changing,
  not merely ask them to infer it from labels and prose.

## Recommended priority order

1. Establish one shared visual state system for active/supporting/next/parked objects, with
   focus-group zoom and an accessible text equivalent. This is the highest-leverage path to
   an immediately legible action sequence.
2. Replace placeholder assets for the common scientific equipment before polishing individual
   scene spacing. A polished layout cannot compensate for a dashed or missing microscope,
   incubator, or counter.
3. Give the guidance bar a two-level format: a short action sentence that names the current
   object, plus an expandable rationale/calculation. Ensure the named object is visibly
   emphasized in the same frame.
4. Add visible state transitions to the first high-value protocols: dilution, cell counting,
   MTT plate handling, and SDS-PAGE tank/gel workflow. This is where the simulation earns
   the "WOW" rather than functioning as a labelled diagram.
5. Re-compose each scene around its actual task after the shared system exists. Do not tune
   coordinates one by one as a substitute for roles and staged work areas.

## Limits and follow-up evidence

- This audit captures initial states. It does not prove click completion, timed waits, or
  transition fidelity; pair the prioritized redesign with visible-UI walker screenshots at
  every meaningful state change.
- The capture tool verifies that pages are populated, not that prompt text is semantically
  correct. Biology-faculty review is required for the calculation-heavy and sequence-heavy
  prompts before their workflows are made more prominent.
- The evidence directory is intentionally transient (`test-results/`). Re-run the two
  commands below after any layout, asset, shell, or protocol change:

```bash
node tools/protocol_to_png.mjs --all --out test-results/wow_scene_gallery/protocol_desktop --viewport 1440x1000
node tools/protocol_to_png.mjs --all --out test-results/wow_scene_gallery/protocol_tablet --viewport 1024x900
```
