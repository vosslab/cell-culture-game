# M11 WP-E1 electrophoresis physical-system implementation

## Second-pass connection-ownership correction

The later browser review rejected the standalone lead-card model recorded below.
Four attached/unattached SVGs and two lead object definitions are deleted. The
electrophoresis tank now owns `black_lead_connected` and
`red_lead_connected`, exposes exact measured `black_terminal` and
`red_terminal` subparts, and composes two tank-coordinate connection overlays.
This addendum supersedes the older retained-lead disposition while preserving
the rest of the WP-E1 implementation record.

## Scope and visual contract

WP-E1 owns the vertical electrophoresis apparatus and its ordinary handling
objects: tank, lid, nested chambers, mounted module, buffer dam, cassette,
comb, packaged gel, leads, power supply, loading-tip boxes, fine loading tip,
and opening lever. The cassette fragments in WP-O1 remain untouched.

The system uses the M8 D04 physical-cavity construction with D01 restraint:
front-left, slightly elevated manufactured faces; upper-left/front light; a
dark value only for a real cavity, far face, or overlap. Tank, mounted module,
and chamber cavities share the same contour and face roles. The cassette keeps
its fixed `214 x 308` composite frame and all ten `data-subpart-id` lane
handles; it adds depth through a receding right face rather than by changing
the overlay coordinate system.

## Reference evidence

Servier source evidence is the frozen M2 ledger:

- `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Lab_apparatus/Servier/gel-electrophoresis.svg`
  is the direct starting evidence for the gel, cassette, and comb family.
- `OTHER_REPOS/bioicons/static/icons/cc-by-3.0/Lab_apparatus/Servier/electrophoresis-chamber.svg`
  is adjacent evidence for transparent tank walls, nested chambers, lid opening,
  and electrode-module stacking.

The unbranded construction facts were checked against Bio-Rad's
[Mini-PROTEAN TGX precast-gel instructions](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/Bulletin_6048B.pdf)
and [PowerPac Basic manual](https://www.bio-rad.com/webroot/web/pdf/lsr/literature/4006213.pdf),
accessed 2026-08-25. They support the comb and tape removal, cassette opening
lever, tank/module/buffer-dam relationship, and red/black color-coordinated
power connections. The implementation omits marks, product names, and learner
prose; it retains only the recognizable physical relationships.

Construction followed the local SVG-object stack: Robertson, _How to Draw_,
`WORKING WITH VOLUME` and `HINGING AND ROTATING FLAPS AND DOORS`; _Mastering
SVG_, `viewBox and viewport in SVG`; and the biological-illustration handbook,
`heaviest lines are used to draw the closest parts`. Those passages informed
the stable viewBox choice, cavity-before-rim draw order, and near-contour
hierarchy rather than a copied outline.

## Material-source decision

The inner and outer chambers stay as four discrete complete source forms:
empty, partial, filled, and `leak_checked`. Their YAML remains a
`material_container` with `material_name`, `material_volume`, and the
closed `fill_state` enum.

One variable material SVG is not a stronger source with the current contract.
The renderer can tint/fill a selected material form, but the semantically
distinct leak-check condition needs a physical verification mark over the
complete chamber. The current closed `visual_states` vocabulary cannot compose
that mark over one selected material source without inventing a new source or
rendering vocabulary. Retaining the four same-frame forms therefore preserves
the visible leak-check state cleanly and avoids a compatibility alias or a
misleading material fan-out. No YAML migration was made.

## Implemented family checks

- The inner and outer chamber families preserve their respective `200 x 220`
  and `280 x 180` viewBoxes, visibly separate cavity/far wall/near rim, and
  retain their full, partial, and verified-leak distinctions.
- Every gel-cassette lifecycle form preserves `214 x 308`, lane IDs, and the
  WP-O1 composite coordinate frame while its gel evidence changes only inside
  the stable cassette.
- Tank open/lidded/module forms preserve `320 x 220`; the lid moves as a
  physical state while cavity, terminal, and module positions stay coherent.
- Tank connection overlays seat the black and red plugs on their measured
  terminals; the cables route separately toward the power-supply side. The
  power supply changes only through display/indicator state.
- Fine tips, boxes, combs, buffer dams, gel package, and lever were reviewed at
  their M3 minimum placements; their silhouette and the one identity-carrying
  feature survive before internal detail.

## Per-source disposition

Every WP-E1 source was checked with the temporary-output normalizer and a
normal/minimum render. "Retained" means the source already met the M8 kit and
the cited physical reference; it is an explicit review disposition, not an
unexamined legacy exception.

| Sources                                                                                                                                                              | Disposition                           | Inspection result                                                                                                                                                                                                                                                                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `electrophoresis_tank_black_lead_connected`, `electrophoresis_tank_red_lead_connected`                                                                               | Replaced standalone cards             | Apparatus-coordinate overlays seat each plug on the corresponding tank terminal. The PowerPac red/black reference supports the bounded colors; no private socket or unattached cable card remains.                                                                                                              |
| `electrophoresis_buffer_dam`, `electrophoresis_buffer_dam_seated`                                                                                                    | Retained                              | Existing dam frame and seated fluid/side-support distinction remain readable and match the module assembly relationship.                                                                                                                                                                                        |
| `electrophoresis_tank_open`, `electrophoresis_tank_lidded`                                                                                                           | Rebuilt                               | Exact shared shell, cavity, terminals, and fixed coordinates; the lidded source adds only foreground lid/occlusion geometry.                                                                                                                                                                                    |
| `gel_comb`                                                                                                                                                           | Retained as a standalone removed part | Existing comb teeth and handle retain their direct-gel-source construction logic at normal size. The former `gel_comb_in_cassette` full-cassette composite was deleted: `gel_cassette.comb_present` now solely owns the inserted-comb overlay, and the standalone comb enters only the completed removal scene. |
| `mini_protean_gel`, `mini_protean_gel_unsealed`                                                                                                                      | Retained                              | Existing package/cassette silhouette and broken-seal distinction remain clear without product prose.                                                                                                                                                                                                            |
| `power_supply_off`, `power_supply_on`                                                                                                                                | Retained                              | Existing one housing, color-coded connectors, display, and running indicator distinguish state without an unrelated housing change.                                                                                                                                                                             |
| `electrophoresis_inner_chamber_empty`, `electrophoresis_inner_chamber_partial`, `electrophoresis_inner_chamber_filled`, `electrophoresis_inner_chamber_leak_checked` | Rebuilt                               | Stable canvas; true cavity, far wall, fill levels, and explicit verification mark.                                                                                                                                                                                                                              |
| `electrophoresis_outer_chamber_empty`, `electrophoresis_outer_chamber_partial`, `electrophoresis_outer_chamber_filled`, `electrophoresis_outer_chamber_leak_checked` | Rebuilt                               | Stable canvas; true cavity, far wall, fill levels, and explicit verification mark.                                                                                                                                                                                                                              |
| `gel_cassette_destained`, `gel_cassette_destaining`, `gel_cassette_empty`, `gel_cassette_separated_unstained`, `gel_cassette_stained`                                | Rebuilt                               | Stable `214 x 308` frame, all ten lane handles, direct-source cassette planes, and state-only matrix/band changes.                                                                                                                                                                                              |
| `electrophoresis_tank_module_mounted`                                                                                                                                | Rebuilt                               | Same cavity, electrode-module, and terminal coordinate language as the tank state pair.                                                                                                                                                                                                                         |
| `gel_loading_tip_box`, `p10_gel_loading_tip_box`                                                                                                                     | Retained                              | Existing open-lid boxes, staggered long tips, near tray lips, anchors, and small-size silhouette are kit-consistent.                                                                                                                                                                                            |
| `gel_opening_tool`                                                                                                                                                   | Retained                              | Existing tapered aluminum wedge and hanging-hole silhouette match the cited opening-lever use at normal and minimum placement.                                                                                                                                                                                  |
| `p10_gel_loading_tip`                                                                                                                                                | Retained after inspection             | The fine tip's `0.31980619` authored outline normalizes successfully. At its actual narrow render it reads as a continuous translucent loading tip, not a generic line; adding a heavier contour would violate the minimum-detail rule.                                                                         |

## Verification record

Run the following after all concurrent M9--M11 source edits settle:

```sh
npm run build
npx playwright test tests/playwright/test_sds_exact_subpart_affordance.spec.ts
```

Use `normalize_svg_v3.py -i <owned-source.svg> -o <temporary-directory>` for
the source-normalizer check. Do not normalize in place merely to run a check:
the fixed state-family frames are composite contracts.

The M12 browser review must exercise the actual built electrophoresis bench:
tank open/lidded, cassette composite variants, normal/minimum placements, and
both image and inline-DOM chamber contexts. A future migration to a material
SVG additionally requires empty/partial/full cool/warm browser proof before it
can replace this discrete family.
