# M11 WP-S1 safety, containment, and bench support

## Scope and visual contract

This work package owns the safety, containment, and bench-support artwork named
in the [batch ownership matrix](svg_batch_ownership_matrix.md#wp-s1-safety-containment-and-bench-support).
The source assets remain ordinary SVG art except where the existing object
contract already supplies inline material-region anchors. No generated asset,
result interface, scene placement, or electrophoresis-system SVG is edited.

The construction direction is D04 physical relation with D01 restraint from the
[equipment kit](../../figures/equipment_kit/README.md): an upper-left/front
light, pale near faces, a darker receding face or genuine recess, and no
detached floor shadow. At normal placements the near contour starts at the kit's
one CSS-pixel target; at the literal minima, silhouette and the host interaction
envelope carry recognition rather than tiny decorative marks.

The drawing stack used the local `svg-creator-expert` references: Robertson,
`WORKING WITH VOLUME` and `HINGING AND ROTATING FLAPS AND DOORS`, for the
three-plane housing and open module; *A Handbook of Biological Illustration*,
`heaviest lines are used to draw the closest parts`, for the near rim and
occlusion edges; and *Mastering SVG*, `viewBox and viewport in SVG`, for stable
state-family frames. The assets use the project SVG pipeline contract rather
than live text or an external resource.

## Bounded reference boards

### Hood workspace surface

| Reference | Recognition evidence | Construction carried into the source |
| --- | --- | --- |
| [CDC biosafety cabinet guidance](https://www.cdc.gov/labs/biosafety/index.html) | A biological safety cabinet has a working chamber, rear wall, sash/front opening, and a clear front intake region. | The source is a cabinet interior, not a generic countertop: it shows a raised rear/top housing, back-wall plane, work deck, and unobstructed front grill. |
| [NIH biosafety cabinet fact sheet](https://ors.od.nih.gov/sr/dohs/Documents/biosafety-cabinet-factsheet.pdf) | Work surfaces must be kept clear and disinfected without obstructing front airflow. | The dirty state has only a localized deck spill/flecks; the clean state replaces those with an ethanol-wipe glint while keeping geometry and anchors identical. |

### Biohazard decant pair

| Reference | Recognition evidence | Construction carried into the source |
| --- | --- | --- |
| [CDC laboratory biosafety manual](https://www.cdc.gov/labs/pdf/CDC-BiosafetyMicrobiologicalBiomedicalLaboratories-2020-P.pdf) | Liquid biohazard waste requires a stable, closable receiving container with a visible hazard cue. | The upright decant has a lidded funnel and a narrow stable body; the bin has a broad receiving rim and rear splash guard. Both retain a high-contrast, shape-only warning trefoil. |
| [OSHA biohazard warning signs](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.145) | A hazard cue must remain legible without relying on a fill color alone. | The pale triangle plus dark trefoil stays in the fixed foreground above any contained material. |

### Sharps container

| Reference | Recognition evidence | Construction carried into the source |
| --- | --- | --- |
| [NIH sharps disposal guidance](https://ors.od.nih.gov/sr/dohs/Documents/sharps-disposal.pdf) | A sharps container is a rigid yellow body with a restricted red lid/opening. | The asset uses a yellow three-plane body, a red lid, and a narrow guarded opening; the slot is an actual recess, not decorative horizontal striping. |

Access date: 2026-08-25. The boards establish generic physical features, not
branding, learner instructions, or copied manufacturer artwork. The M2 sweep
records no direct Servier counterpart for the three safety forms. The electrode
module uses the recorded `electrophoresis-chamber.svg` adjacent construction:
transparent/blue housing planes, recess, tank-compatible terminals, and a
physical wing-clamp opening.

## State and ownership decisions

## Source disposition

Every owned source was inspected against its M2 provenance, M3 placement range,
and the M8 kit. "Retained" below means the existing source already expressed
the required physical relationship and was left structurally stable; it does
not mean it escaped family review. "Refined" is a direct source edit limited to
the kit contour hierarchy. No asset outside this table is claimed by WP-S1.

| Source group | Disposition | Family-gate reason |
| --- | --- | --- |
| `electrode_module_closed.svg`, `electrode_module_open.svg` | Rebuilt | The prior state pair read as a flat front box. Both now use the same three-plane shell and recessed cassette well; state differs only by physical wing-clamp occlusion. |
| `hood_workspace_surface.svg`, `hood_workspace_surface_clean.svg` | Retained | The pair already shares frame/anchors and a legible cabinet rear wall, deck, front grill, and localized dirty-versus-clean evidence. Their shallow built-in perspective is correct for an inline workspace surface. |
| Five `staining_tray_*.svg` states | Retained | One shared tapered vessel frame, rim, side planes, clip, liquid bounds, and overlay seam supports distinct gel lifecycle evidence. The state-to-material migration analysis below rejects a premature collapse. |
| `biohazard_decant.svg`, `biohazard_decant_bin.svg` | Retained | The pair is intentionally not one scaled object: upright decant has funnel/lid geometry; broad bin has a receiving rim/splash guard. Both preserve material anchors and foreground hazard cue. |
| `kimwipe_pad.svg`, `lens_tissue.svg`, `paper_towel_pad.svg` | Refined | Their overlapping/folded paper construction already gives soft-good volume; the near contours now use the kit's dark contour role without forcing manufactured-instrument mass. |
| `label_pen.svg` | Retained | Cap, barrel, paper label, collar, and chisel tip form a clear long handheld silhouette at the small tool placement. Its existing dark shell hierarchy already matches the kit. |
| `recycle_buffer_funnel.svg` | Refined | Its elliptical mouth, tapered transparent cone, and stem already establish the correct glass/funnel form; the primary contours now use the kit role. |
| `sharps_container.svg` | Refined | The yellow body, red lid, guarded slot, and fixed anchors are preserved; primary lid/body contours now use the kit dark role. |

### Electrode module

`electrode_module_closed.svg` and `electrode_module_open.svg` share the exact
`0 0 240 160` frame, cable terminals, bench feet, shell, recess position, and
contour roles. The closed state seats two wing clamps over a pale cassette face;
the open state moves only those clamps into the side-open condition and exposes
the deeper receiving recess. This makes `wing_clamps_open` a physical state
instead of a palette swap, while leaving the mounted/cassette state composition
to its object and the WP-E1 system untouched.

### Staining tray: retain the five-state family

The tray has `material_name` and `material_volume`, but a material-rendered
single-source migration is not correct under the current contract. The five
selected forms encode the independent `gel_state`: separated, stained,
destaining, and destained gels differ in bands, background, and gel treatment,
not merely liquid identity or height. The existing material renderer owns only
contained liquid paint and fill geometry; it has no owned semantic overlay for
the gel lifecycle. Collapsing those files now would either discard visible gel
state or introduce an unowned state-composition mechanism.

Therefore this package retains one coherent five-state physical housing with a
fixed frame, rim, side planes, liquid clip, `overlay_root`, and liquid-bounds
anchor. The state files differ only in contained-solution/gel evidence. This is
the stronger current ownership boundary; a later migration should first provide
a canonical gel-state overlay contract, then remove all five files together
without compatibility aliases.

### Containment and soft goods

The decant forms retain their existing inline liquid anchors and foreground
hazard cue so material is behind the rim/trefoil. The hood sources retain
`overlay_root`, `anchor_label`, and `anchor_error`. The tissue, towel, Kimwipe,
pen, and funnel are intentionally thin/soft or transparent subjects: overlap,
fold, rim, and face value establish their physical read without pretending that
they are heavy instruments.

## Render and validation record

The package is reviewed in the normal hood, staining, cell-counter, and SDS-PAGE
contexts and at their M3 minimum placements. The key minimum facts are: hood
surface is a host/background asset, staining tray is about 45 by 63 CSS pixels,
the upright decant is about 9 by 11 CSS pixels, and paper towel can be about
10 by 6 CSS pixels. Those minima justify sparse fixed detail and make the
silhouette/semantic host treatment the durable oracle.

Run after the source tree is quiescent:

```sh
source source_me.sh && python3 tools/normalize_svg_v3.py \
  -i assets/equipment/binary_state/electrode_module_closed.svg \
  -i assets/equipment/binary_state/electrode_module_open.svg \
  -o /tmp/wp_s1_normalized
bash build_github_pages.sh
bash check_codebase.sh
```

The source changes preserve the static-object contracts; no staining-tray
material migration occurred, so no new material empty/partial/full browser
matrix is required for this package.

### Completed capture evidence

The rebuilt production site rendered `hood_basic` at 681 by 383 through the
actual `scene_viewer` consumer: 9 of 9 placements rendered, zero render errors,
zero overlap pairs, and 84.4 percent approximate deliberate scene whitespace
(`generated/scene_render_stats/hood_basic.stats.json`). The captured image is
`/private/tmp/wp_s1_renders/hood_basic.png` during this implementation run. The
hood surface retained its full cabinet silhouette and no SVG load fallback was
reported.

Standalone actual-SVG delivery renders were also inspected for the rebuilt open
and closed electrode module, the stained tray, sharps container, and upright
biohazard decant at `/private/tmp/wp_s1_renders/`. They show, respectively, a
stable shell with visible clamp occlusion, a contained gel within its tapered
tray, a guarded sharps slot, and the high-contrast fixed decant warning.

Concurrent generated-tree rebuilds intermittently removed the manifest between
captures. The completed hood capture is production-consumer evidence; the
staining, cell-counter, and electrophoresis composite commands remain the exact
repeat route for M12/integration when the generated tree is quiescent.
