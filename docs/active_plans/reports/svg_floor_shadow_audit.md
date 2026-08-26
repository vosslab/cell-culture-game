# SVG floor-shadow audit

## Scope and method

This M0 report originally audited the complete 2026-08-24
`assets/equipment/` tree: 139 SVGs.
For each source, report-only mode performed the same safe preparation as D1
(strict XML parse, classification, transform flattening, shape-to-path
conversion, and editor-cruft removal) without writing or changing a file.

Command used:

```bash
source source_me.sh && while IFS= read -r svg_path; do
    python3 -m tools.svg_normalizer.cli --shadow-dry-run -i "$svg_path"
done < <(rg --files assets/equipment -g '*.svg' | sort)
```

The historical initial signal found 13 candidates in five SVG families. I inspected every
candidate against its SVG geometry and a 600 px `rsvg-convert` render. There
were no detached editorial floor shadows. All 13 are object geometry, so all
must remain.

| SVG                                        | XPath          | BBox                  | Visual verdict                                                               |
| ------------------------------------------ | -------------- | --------------------- | ---------------------------------------------------------------------------- |
| `binary_state/cell_counter_instrument.svg` | `/*/*[30]`     | `(28,178)-(328,192)`  | False: lower front/base housing band.                                        |
| `binary_state/cell_counter_instrument.svg` | `/*/*[31]`     | `(30,180)-(326,190)`  | False: inset front face of the lower housing band.                           |
| `binary_state/cell_counter_instrument.svg` | `/*/*[33]`     | `(116,190)-(236,200)` | False: central lower-control/foot detail.                                    |
| `binary_state/cell_counter_instrument.svg` | `/*/*[34]`     | `(26,201)-(56,209)`   | False: left instrument foot.                                                 |
| `binary_state/cell_counter_instrument.svg` | `/*/*[35]`     | `(316,201)-(346,209)` | False: right instrument foot.                                                |
| `binary_state/cell_counter_result.svg`     | `/*/*[33]`     | `(28,178)-(328,192)`  | False: lower front/base housing band.                                        |
| `binary_state/cell_counter_result.svg`     | `/*/*[34]`     | `(30,180)-(326,190)`  | False: inset front face of the lower housing band.                           |
| `binary_state/cell_counter_result.svg`     | `/*/*[37]`     | `(26,201)-(56,209)`   | False: left instrument foot.                                                 |
| `binary_state/cell_counter_result.svg`     | `/*/*[38]`     | `(316,201)-(346,209)` | False: right instrument foot.                                                |
| `binary_state/centrifuge.svg`              | `/*/*[20]`     | `(33,318)-(225,346)`  | False: two trapezoidal support feet.                                         |
| `binary_state/power_supply_off.svg`        | `/*/*[1]`      | `(11,84)-(170,91)`    | False: front plinth below the housing.                                       |
| `binary_state/power_supply_on.svg`         | `/*/*[1]`      | `(11,84)-(170,91)`    | False: same front plinth in the alternate state.                             |
| `static/vortex.svg`                        | `/*/*[2]/*[2]` | `(36,306)-(236,322)`  | False: paired instrument feet, partly clipped by the deliberate scene frame. |

The old detector selected all 13 through `grey_fill`. Its visual premise was
wrong: grey, wide, and low are ordinary construction features in laboratory
equipment. The post-fix full-tree result is **0 candidates**, matching the
reviewed verdict set exactly.

Ten files were skipped in that historical run because the existing classifier rejects them before D1;
they are not a clean-normalizer result and were not counted as candidates:

- `static/cell_viability_results_display.svg`
- `static/electrophoresis_endpoint_display.svg`
- `static/gel_image_results_display.svg`
- `static/hemocytometer_observation_display.svg`
- `static/microscope_field_confluent_70_80.svg`
- `static/microscope_field_rounded_detached.svg`
- `static/mtt_reader_results_display.svg`
- `static/plate_reader_absorbance_result_panel.svg`
- `static/plate_reader_normalized_viability_panel.svg`
- `static/well_plate_formazan_crystals.svg`

The remaining 129 historical SVGs reported `SHADOW-NONE`.

## Post-recovery rerun

The same report-only command was rerun on the then-current 134-asset tree on
2026-08-26. It returned zero candidates: 127 `SHADOW-NONE` results and seven
classifier skips. The seven skips are the protected result interfaces:

- `static/cell_viability_results_display.svg`
- `static/electrophoresis_endpoint_display.svg`
- `static/gel_image_results_display.svg`
- `static/hemocytometer_observation_display.svg`
- `static/mtt_reader_results_display.svg`
- `static/plate_reader_absorbance_result_panel.svg`
- `static/plate_reader_normalized_viability_panel.svg`

This historical rerun preserved the reviewed M0 verdict: the opt-in detector
selected no ordinary equipment geometry as an editorial floor shadow.

## Final ownership-repaired rerun

After deleting the false full-cassette comb state and moving the unchanged
standalone comb to `static/`, the same command was rerun across the then-current
133 assets. It again returned zero candidates: 126 `SHADOW-NONE` results and
the same seven protected-result classifier skips. The final MTT-ownership rerun
below supersedes this historical count.

## Final MTT-ownership rerun

After deleting the material-specific MTT vial, the same command was rerun
across all 132 current assets. It returned zero candidates: 125
`SHADOW-NONE` results and the same seven protected-result classifier skips.
This supersedes the 133-asset count above as the current M0 evidence.

## Second-pass connection-ownership rerun

After deleting four standalone binary lead cards and adding two tank-coordinate
connection overlays, the same command was rerun across all 130 current assets.
It returned zero candidates: 123 `SHADOW-NONE` results and the same seven
protected-result classifier skips. This supersedes the 132-asset count above as
the current M0 evidence.

## Signal decision

D1 now requires all of the following:

1. Its own geometry is wide and flat (aspect ratio greater than 3).
2. Its centre is in the bottom 20 percent of the drawing bbox.
3. The path explicitly declares `data-editorial-floor-shadow="true"`.

This is a pre-production schema correction. `fill`, `fill-opacity`, `id`, and
`class` are presentation or generic metadata and never authorize deletion.
The exact string value makes author intent inspectable and keeps a future
shadow opt-in local to the SVG element that is safe to remove.

`document.parse_svg` already uses a restrictive XML parser (`recover=False`,
`resolve_entities=False`, `no_network=True`, `huge_tree=False`), satisfying
the relevant XML-boundary control. The audit command supplies paths discovered
from the trusted in-repository `assets/equipment/` tree; it does not derive
paths from SVG metadata. The marker compares an exact string rather than a
truthy/coerced value.

## Construction-kit handoff: supported depth language

The sanitizer rejects `<filter>` and non-`none` `filter` references because
filtered pixels can exceed the geometry bbox. The equipment kit must therefore
build depth from **overlap and face value**: distinct front, side, inset, and
opening faces with deliberate draw order and value separation. Do not depend
on blur, drop shadow, or filter-based shading for volume.

## Verification

```text
source source_me.sh && python3 -m pytest tests/test_svg_normalizer_shadows.py -q
15 passed

full report-only audit: 139 SVGs
before fix: 13 candidates, 10 classifier skips, 116 SHADOW-NONE
after fix:   0 candidates, 10 classifier skips, 129 SHADOW-NONE

post-recovery rerun: 134 SVGs (before the later gel-comb ownership deletion)
post-recovery:       0 candidates, 7 classifier skips, 127 SHADOW-NONE

post-comb-ownership rerun: 133 SVGs
post-comb:                 0 candidates, 7 classifier skips, 126 SHADOW-NONE

final MTT-ownership rerun: 132 SVGs
final MTT:                 0 candidates, 7 classifier skips, 125 SHADOW-NONE

second-pass connection ownership: 130 SVGs
current:                          0 candidates, 7 classifier skips, 123 SHADOW-NONE
```

Residual risk: an author who wants D1 to remove an editorial shadow must add
the exact marker. That intentional opt-in is preferred to inferring a shadow
from the same low, wide, grey geometry used by bases and feet.
