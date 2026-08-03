# Liquid gravity-part hypothesis audit

## Decision

The canonical authored liquid model is an optional decomposition into three
gravity-defined parts:

```text
       movable meniscus
      +--------------+
      |              |
      | stretched    |
      | middle body  |
      |              |
      +--------------+
       fixed cone
          \    /
           \  /
            \/
```

1. `surface` is a fixed-shape meniscus or surface detail. It translates
   vertically to the requested liquid surface and never stretches.
2. `body` is the middle region between the lower vessel shape and the surface.
   It scales only in Y and carries the main fill plus repeatable vertical
   highlights and shadows.
3. `bottom` is the fixed cone, rounded base, bulb, or tip. It remains anchored
   in vessel coordinates and never translates or stretches. The complete
   material region is hidden at zero volume.

An asset may omit parts it does not need. The runtime behavior is selected by
these closed semantic parts, never by an asset name or vessel-specific branch.
The vessel clip and the reveal boundary remain in stationary vessel
coordinates.

## Evidence boundary

The earlier 33-file census is a census of legacy liquid anchors, not of
variable-volume liquid artwork. It includes empty tools and interaction targets.
Those files cannot be used as the denominator for this hypothesis.

The following volume-bearing families are the relevant initial evidence set:

| Family | Current evidence | Expected parts | Finding |
| --- | --- | --- | --- |
| 1.5 mL microtube and small vial | `microtube.svg`, `mtt_vial.svg`, protein tube art | rounded or pointed lower vessel with a vertical column and a horizontal surface | `bottom`, `body`, `surface` |
| 15 mL conical tube | `falcon_15ml.svg` geometry and volume contact page | fixed conical tip, cylindrical middle, fixed meniscus | `bottom`, `body`, `surface`; whole-group translation is falsified |
| 50 mL conical tube | `falcon_50ml.svg` source and census render | fixed conical tip, cylindrical middle, fixed meniscus | `bottom`, `body`, `surface` |
| Media or reagent bottle | bottle donor family and `bottle_medium_pink.svg` contact page | rounded base, near-constant middle, fixed surface | `bottom`, `body`, `surface` through the straight-body operating range; tapered shoulder deferred |
| Serological pipette | `serological_pipette.svg` | fixed pointed tip, narrow middle, fixed surface | `bottom`, `body`, `surface` |

All five variable-volume families support the same gravity decomposition within
their reviewed operating ranges. This meets the architectural hypothesis for
the current primary volume vessels. It does not establish that a single
Y-stretched middle can enter every tapered shoulder. The bottle pilot's logical
100% reproduces the donor reference level at about 60% geometric vessel fill.
The reviewed straight-body hard ceiling is about 70%, but it is not the normal
100% endpoint; the contact page reports both values rather than relabeling a
70%-full bottle as geometrically full.
Carboys, waste reservoirs, electrophoresis chambers, and staining trays remain
later conversion families; their legacy anchors do not alter the canonical
runtime contract.

## Classification audit

Classification uses two evidence passes:

1. The variant-difference pass geometry-matches differently colored donor
   families and proposes paths whose fill or stroke changes as material
   candidates. `tools/svg_semantic_inspector.py --compare-variants` makes this
   read-only evidence reproducible even when sibling drawings differ slightly
   in root frame or path coordinates.
2. The physical-behavior pass reviews those candidates plus every white,
   translucent, highlight, shadow, bubble, and reflection path near the donor
   liquid. A path is assigned by what it would do when the real liquid level
   changes: fixed `bottom`, Y-scaled `body`, translated `surface`, or fixed
   vessel art.

The four bottle donors produced 11 geometry-matched paint-changing candidates
and seven shared white or translucent review candidates. This found the main
fill, surface plate, side and bottom shading, and liquid edge strokes. It also
found the color-coordinated label border, which physical review correctly kept
with fixed label art. Conversely, white donor surface outlines and bubbles did
not change across variants but physical review assigned them to `surface`.

The conical-tube review found a second failure mode: paths recolored to resemble
empty glass still ended at the donor meniscus. Those fixed paths created a
horizontal residual near the 15 mL tube's original 8 mL level even though their
new color was not an obvious liquid color. The accepted sources instead render
continuous empty-vessel shading behind the material groups. This establishes
two acceptance invariants:

- Fixed layers alone render a coherent empty vessel and expose no artificial
  boundary at the donor meniscus.
- At every tested level, no material-dependent base, tint, highlight, shadow,
  bubble, or reflection remains above the current surface; surface features
  move with that surface.

## Explicit exclusions and exceptions

- Aspirating pipettes do not store a user-visible calibrated volume. Their
  anchors support suction interaction and are excluded from the volume-art
  census.
- A T75 culture flask is normally shown with a shallow working layer, not as a
  continuously variable upright reservoir. Prefer complete `empty` and `filled`
  forms, where `filled` represents the normal shallow working volume. Do not
  force the continuous gravity-part renderer onto it merely because an older
  object file declares `fill_height`.
- Hemocytometer chambers and plate wells use structured subpart tinting. They are
  not whole-vessel fill-height evidence.
- SVG user units measure geometry, not milliliters or microliters. A physical
  volume-to-surface calibration, including any conical nonlinear segment, is a
  separate authored concern and is never inferred from image size or graduation
  marks.
- A changing cross-section above the reviewed middle, such as the bottle's
  tapered shoulder, is a deferred geometry class. Do not make the rectangular
  body wider or narrower through an asset-name branch. Either decompose the
  shoulder into additional generic geometry in a follow-on decision or keep the
  supported maximum below it.

## Falsified model

The Falcon contact page disproved the previous single translated liquid group.
Moving one finite slab moves both its top and bottom: low fills escaped below the
vessel, high fills abandoned the cone, and full volume stopped at the donor
surface. Extending that slab with hidden overscan repaired one screenshot but
did not repair the physical model. The compiler and runtime must therefore
control the three semantic parts independently.
