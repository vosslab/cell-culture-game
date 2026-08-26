# M9 WP-C1 vessel and waste implementation

## Scope and visual contract

This report records the M9 `WP-C1` implementation from the SVG visual-quality
rebuild plan. It owns the two balance-tube states, two hazardous-waste states,
two MTT microtube states, two reagent-reservoir states, and the three
material-rendered canonical vessel forms. All retain their existing viewBoxes,
object-selected asset names, and inline-DOM delivery mode.

The construction uses the equipment kit's selected D04 occlusion-strong logic
with D01 restraint: a darker plane identifies a true receding side, an opening,
or contained contents; it is not decorative striping. The common light is
upper-left/front. The balance tube and reservoir now use the kit's `#294657`,
`#7895a5`, `#b9ccd7`, and `#e8f0f4` fixed-art ladder. The state pairs retain one
stable physical shell and differ only by the contained matched liquid, powder,
or reservoir liquid.

## Recognition and source evidence

| Family | Recognition target and retained contract | Evidence used |
| --- | --- | --- |
| Centrifuge balance tube | A narrow conical 15 mL tube with cap/rim, transparent body, graduations, and a physically contained matched liquid state. | M2's Servier-adjacent `falcon-15ml-empty.svg` guides the rim, conical body, and liquid-bearing opening. |
| MTT microtube and variable microtube | A hinged microcentrifuge tube with an offset cap, rim, tapered transparent body, and, only for the MTT state, a small contained powder bed. | M2's Servier-adjacent `microtube-closed-translucent.svg` guides the cap/body relationship. |
| Reagent reservoir | A shallow disposable trough whose near wall, inner basin, rim, and right receding face remain legible at bench size. | M2's `dyetray.svg` adjacent construction record guides a shallow liquid-bearing tray. |
| Medium bottle and 50 mL Falcon | Material-rendered reusable forms: material color and amount remain entirely in direct-root semantic layers and anchors. | M2 direct Servier records: `bottle-medium-pink.svg` and `falcon-50ml-empty.svg`. |
| Hazardous liquid waste | A generic closed waste carboy with handle/cap, hose connection, visible front hazard placard, and contents that remain inside the body. | No Servier source. Bounded physical-reference research below informed anatomy without copying a brand. |

### Waste-container physical-reference board

Accessed 2026-08-25. The illustrations retain only shared physical facts: a
handled rigid carboy, threaded cap, short hose/funnel connection, a front
hazard label zone, and a contained liquid level. They do not retain brand
logos, manufacturer labels, product dimensions, or a distinctive molding
pattern.

- [Thermo Scientific Nalgene carboy overview](https://www.thermofisher.com/us/en/home/life-science/lab-plasticware-supplies/carboys.html): rigid laboratory carboy body, top handle/cap, and dispensing/connection context.
- [New Pig hazardous-waste container guidance](https://www.newpig.com/hazardous-waste-containers/c/507): separate hazardous-waste collection, compatible closure, and clearly visible hazard labeling context.
- [EPA hazardous-waste container management](https://www.epa.gov/hw/guidance-hazardous-waste-containers): containers remain closed except when adding/removing waste and are marked to identify their hazardous contents.

Later integration should add a concise repository-authored/no-Servier row for
`hazardous_liquid_waste_empty.svg` and `hazardous_liquid_waste_filled.svg` to
`assets/equipment/SOURCES.md`. This package intentionally does not edit that
shared provenance file.

## Preserved material and state boundaries

- `bottle_medium_pink.svg`, `falcon_50ml.svg`, and `microtube.svg` retain their
  direct-root `data-vlab-layer-*` groups, `anchor_liquid_clip`,
  `anchor_liquid_bounds`, and all existing material calibration attributes.
  The change adds explicit `preserveAspectRatio="xMidYMid meet"`; it does not
  move material color into fixed art or duplicate one form per material.
- The discrete balance-tube, MTT, waste, and reservoir object YAML continues to
  select whole SVG states. No SVG ID, object YAML, runtime schema, or generated
  artifact changed.
- Hazardous-waste structural IDs `anchor_highlight`, `anchor_label`,
  `anchor_error`, and `overlay_root` remain intact in both states.

## Validation and render evidence

Temporary normalizer output was written outside the repository before source
replacement. The rebuilt balance-tube and reservoir sources parse and normalize
successfully. `bottle_medium_pink.svg` and `falcon_50ml.svg` now also normalize
successfully: their authored path data was converted source-locally from
relative commands to equivalent absolute path segments, with no change to
semantic groups, anchors, material calibration, or measured Falcon 50 mL path
geometry. A direct parsed-path comparison confirms the Falcon source's complete
path-segment list remains exactly equal to the pre-conversion source.

The balance-tube pair shares exact `tube_back` and `tube_front` groups; the
reservoir pair shares exact `reservoir_fixed` and `reservoir_front` groups. The
waste-container shell and highlight geometry also remain identical across empty
and filled states. The only state-specific geometry is contained liquid or
powder.

Standalone review is performed at each SVG's natural aspect ratio and at the
M3 minimum/representative scene widths named by the inventory. The review checks
the tube silhouette, stable state frame, contained liquid/powder, reservoir
basin depth, waste placard legibility, and material-vessel clip containment.
The package-local command record is:

```bash
source source_me.sh && python3 tools/normalize_svg_v3.py -i assets/equipment/binary_state/centrifuge_balance_tube_empty.svg -o /private/tmp/wp_c1_svg
source source_me.sh && python3 tools/normalize_svg_v3.py -i assets/equipment/binary_state/reagent_reservoir_filled.svg -o /private/tmp/wp_c1_svg
```

The final integration gate must run the repository XML/material/object/taxonomy
suite and real inline-DOM scene rendering after all M9 packages complete.
