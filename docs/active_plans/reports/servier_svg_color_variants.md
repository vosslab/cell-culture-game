# Servier SVG color variants

These Servier SVG families use layered solid-color paths to create glass,
liquid, highlights, shadows, and outlines. Blue and red variants are feasible,
but none of the families is a single shared drawing with one color token.

## Short answer

Yes, blue or red versions can be made.

- For bottles, copy one existing bottle as the geometry master and replace only
  its medium-color ramp.
- For test tubes, copy one filled test tube and replace its four liquid colors.
- For microtubes, choose open or closed geometry first, then recolor the plastic
  separately from any visible liquid.
- Preserve the shared glass, white highlight, and dark outline colors.
- Do not combine paths from different variants. Their coordinates and bounds
  differ slightly.

This report compares the XML directly. It checks each root `viewBox`, path
count, `d` path geometry, `fill`, `stroke`, clip path, and opacity attribute.
A color-neutralized comparison still differs within every family, proving that
the source files are sibling drawings rather than literal palette swaps.

## Medium bottles

### Source files

- `bottle-medium-pink.svg`
- `bottle-medium-orange.svg`
- `bottle-medium-green.svg`

### XML comparison

| Variant | `viewBox`             | Paths | Distinct variant colors |
| ------- | --------------------- | ----: | ----------------------: |
| Pink    | `0 0 176.92 387.628`  |    44 |                      13 |
| Orange  | `0 0 177.071 387.25`  |    42 |                      10 |
| Green   | `0 0 177.071 387.326` |    43 |                       9 |

All three files contain one `clipPath` and otherwise use paths. They do not
have identical bounds, path counts, or `d` attributes. Even orange and green,
which have nearly identical widths, differ in height and path structure.

The files share 16 colors for the bottle, cap, glass reflections, label, and
outlines:

```text
#333     #55919f #90bac4 #9d869a
#a9cad2  #b6d2d9 #b9d6dd #c0b0ba
#c4c4c4  #dde9ec #e3eef1 #e7e0e3
#ebebeb  #f6fafb #f7f4f4 #fff
```

Those shared colors should normally remain unchanged. The color-specific paths
paint the medium surface, bulk medium, side and bottom shadows, and colored
label border.

Representative color ramps are:

| Variant | Light/surface colors            | Main colors                     | Deep/shadow colors              |
| ------- | ------------------------------- | ------------------------------- | ------------------------------- |
| Pink    | `#eacbe1`, `#dba6cb`, `#c393c0` | `#c09fc5`, `#b64392`, `#95207d` | `#88016c`, `#84016a`, `#5d014a` |
| Orange  | `#f5e4ba`, `#efd392`, `#e5b24d` | `#e3af41`, `#e2ac40`, `#d98e05` | `#d98004`, `#d87103`, `#b65402` |
| Green   | `#aecb9e`, `#84b176`, `#77a86c` | `#468b4d`, `#2a7a3c`, `#207535` | `#01642a`, `#004d20`            |

The same color can occur on several paths. For example, green `#01642a`
appears five times and pink `#88016c` appears three times. A replacement
should therefore replace every occurrence in the chosen geometry master.

### Making blue or red

The green file is a practical geometry master because its medium ramp is easy
to distinguish from the shared blue-gray glass colors. The following mappings
retain its light-to-dark relationships:

| Green source | Blue proposal | Red proposal |
| ------------ | ------------- | ------------ |
| `#aecb9e`    | `#b8daf1`     | `#f2b0ad`    |
| `#84b176`    | `#98c3e5`     | `#e08d88`    |
| `#77a86c`    | `#80b4e0`     | `#dc7772`    |
| `#659d61`    | `#659fd0`     | `#c85c5b`    |
| `#468b4d`    | `#3f83bd`     | `#bd4242`    |
| `#2a7a3c`    | `#2f6fa8`     | `#a92f35`    |
| `#207535`    | `#28679f`     | `#9f2a30`    |
| `#01642a`    | `#13558f`     | `#8d1e26`    |
| `#004d20`    | `#0b3d70`     | `#68151d`    |

These are proposed ramps, not colors already present in the source set. Render
the result before adopting them. In particular, a blue medium must remain
visually distinct from the existing cyan glass highlights.

## Test tubes

### Source files

- [testtube-glass.svg](../../../servier/testtube-glass.svg)
- [testtube-green.svg](../../../servier/testtube-green.svg)
- [testtube-yellow.svg](../../../servier/testtube-yellow.svg)
- [testtube-pink.svg](../../../servier/testtube-pink.svg)
- [testtube-purple.svg](../../../servier/testtube-purple.svg)

### XML comparison

| Variant | `viewBox`            | Paths | Liquid colors |
| ------- | -------------------- | ----: | ------------: |
| Glass   | `0 0 57.335 366.123` |    13 |             0 |
| Green   | `0 0 57.713 366.161` |    20 |             4 |
| Yellow  | `0 0 57.638 366.236` |    20 |             4 |
| Pink    | `0 0 57.751 366.161` |    20 |             4 |
| Purple  | `0 0 57.638 366.236` |    20 |             4 |

The empty glass tube has 13 paths. Each filled tube has 20 paths, adding the
liquid body, meniscus, and shading layers. The four filled tubes use the same
logical layer order, but their `d` values are not identical. For example,
yellow and purple share a `viewBox` but differ in tube bottom, rim, meniscus,
and bubble coordinates.

All five share the glass and outline palette:

```text
#333 #48bad6 #79cde1 #a8dfec #ade0ed #d9f1f7 #eff9fb #fff
```

Each filled variant then adds exactly four liquid colors:

| Variant | Body      | Meniscus/light | Side shadow | Deep shadow |
| ------- | --------- | -------------- | ----------- | ----------- |
| Green   | `#9ad7aa` | `#c3e8c9`      | `#65bf87`   | `#29a268`   |
| Yellow  | `#fee46e` | `#ffefa6`      | `#ffc429`   | `#ff9400`   |
| Pink    | `#f685a6` | `#f9b4c6`      | `#f2457e`   | `#ee015c`   |
| Purple  | `#c39ab2` | `#d8bcca`      | `#ab7095`   | `#893b73`   |

### Making blue or red

This is the simplest family to recolor. Copy one of the 20-path filled tubes
and change only its four liquid colors:

| Role           | Blue proposal | Red proposal |
| -------------- | ------------- | ------------ |
| Body           | `#74a9e6`     | `#f08b83`    |
| Meniscus/light | `#bfd4f4`     | `#fac0b9`    |
| Side shadow    | `#3f78c5`     | `#d94c43`    |
| Deep shadow    | `#214f9c`     | `#a82424`    |

Leave all eight shared glass and outline colors unchanged. Using four related
colors rather than one flat fill preserves the rounded tube and liquid depth.

## Microtubes

### Source files

- `microtube-closed-%20pink.svg`
- [microtube-closed-blue.svg](../../../servier/microtube-closed-blue.svg)
- [microtube-closed-translucent.svg](../../../servier/microtube-closed-translucent.svg)
- [microtube-open-blue.svg](../../../servier/microtube-open-blue.svg)
- [microtube-open-pink.svg](../../../servier/microtube-open-pink.svg)
- [microtube-open-translucent.svg](../../../servier/microtube-open-translucent.svg)

The space in `microtube-closed- pink.svg` is present in the repository
filename. It is not a transcription error.

### XML comparison

| Variant            | `viewBox`             | Paths | Visible content                   |
| ------------------ | --------------------- | ----: | --------------------------------- |
| Closed pink        | `0 0 156.51 263.357`  |    71 | Pink plastic, teal liquid         |
| Closed blue        | `0 0 150.085 252.472` |    71 | Blue plastic, purple liquid       |
| Closed translucent | `0 0 150.236 252.472` |    71 | Gray plastic, yellow-green liquid |
| Open blue          | `0 0 129.524 371.83`  |    47 | Blue plastic, no visible liquid   |
| Open pink          | `0 0 134.098 382.45`  |    46 | Pink plastic, no visible liquid   |
| Open translucent   | `0 0 137.046 393.298` |    46 | Gray plastic, no visible liquid   |

Open and closed files are different poses, not state toggles on shared paths.
Even within one pose, the variants differ:

- Closed variants have the same 71-path count but different bounds and `d`
  geometry.
- Open blue has one more path than open pink and open translucent.
- Open variant heights span from `371.83` to `393.298`, so substituting one
  `viewBox` for another can crop or change apparent scale.
- Every explicit `fill-opacity` and `stroke-opacity` in these files is `1`.
  The translucent look is painted with gray, white, and highlight paths; it
  does not use partial alpha transparency.

The closed files contain two independent color decisions:

1. the plastic body, lid, and hinge color;
2. the liquid color and its meniscus/highlights.

For example, the closed pink tube contains a pink plastic ramp from dark
`#a0015a` through main `#ed66b1` to pale `#fad7ea`, plus a separate teal-gray
liquid ramp. The closed blue tube combines a blue plastic ramp with a purple
liquid ramp. The closed translucent tube combines a gray plastic ramp with a
yellow-green liquid ramp.

### Making blue or red

Blue open and closed artwork already exists. For red:

- Use `microtube-open-pink.svg` as the open geometry master.
- Replace the full pink plastic ramp, not only its darkest color.
- Use `microtube-closed- pink.svg` as the closed geometry master if its teal
  liquid is appropriate.
- Recolor only the plastic ramp for a red tube with teal liquid.
- Recolor the liquid ramp separately if the intended contents should also be
  red.

A global hue rotation is unsafe for closed microtubes because it changes both
container and contents. It can also shift the cyan structural accents retained
in some closed files.

## Recommended workflow

1. Choose one existing SVG as the geometry master for the desired family and
   open/closed state.
2. Duplicate that file without changing its `viewBox`, clip path, path order,
   or `d` attributes.
3. Build a list of only the family-specific `fill` and `stroke` colors.
4. Replace the complete light-to-dark ramp consistently.
5. Preserve `#333`, `#fff`, and the family's shared glass palette.
6. Render old and new files at the same height and compare outlines, highlights,
   meniscus, and label borders.
7. Normalize the finished SVG through the repository's SVG pipeline before
   using it as a scene asset.

The safest implementation is therefore palette substitution within one file,
not attempting to synthesize a new file by merging the existing variants.
