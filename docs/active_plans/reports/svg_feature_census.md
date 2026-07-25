# SVG corpus feature census

Corpus: every `*.svg` under `OTHER_REPOS/` (3125 files).
Feature presence is counted per file and is independent of the v3
verdict: a file may carry a clipPath yet be rejected for text. Use
this census to size each normalization requirement across the corpus.

## Normalize rate

"Normalized" is defined as the true `normalize_svg_file` outcome (the
first-wins verdict). Inside-pipeline reject codes (`EMPTY_GEOMETRY`,
`CLIPPATH_UNSUPPORTED_COMPLEX`) are folded into each non-normalized
file's reasons list from the verdict because they are not standalone
detectors, so zero reasons means the file truly normalizes.

Normalized: 1733 / 3125 (raw 55.5%)
Normalized (excluding intentional raster rejects): 1733 / (3125 - 73) = 1733 / 3052 (adjusted 56.8%)
Raster-embedding SVGs (verdict `EMBEDDED_RASTER_UNSUPPORTED`) are
intentionally unsupported and excluded from the adjusted denominator.

## Reason presence (all-reasons, overlapping)

Each file's full set of applicable rejection reasons is computed with
no first-wins short-circuit. The counts below are overlapping file-
presence counts: a file with several reasons is counted under each one,
so these columns do NOT sum to the corpus total of 3125 files.

| Reason | Files with reason | Percent of corpus |
| --- | --- | --- |
| STYLE_GEOMETRY_UNSUPPORTED | 683 | 21.9% |
| TEXT_UNSUPPORTED | 314 | 10.0% |
| DOCTYPE_OR_ENTITY | 234 | 7.5% |
| FOREIGNOBJECT_UNSUPPORTED | 164 | 5.2% |
| EXTERNAL_RESOURCE_UNSUPPORTED | 143 | 4.6% |
| EMBEDDED_RASTER_UNSUPPORTED | 111 | 3.6% |
| CLIPPATH_UNSUPPORTED_COMPLEX | 108 | 3.5% |
| USE_OR_SYMBOL_UNSUPPORTED | 102 | 3.3% |
| FILTER_UNSUPPORTED | 57 | 1.8% |
| MARKER_UNSUPPORTED | 38 | 1.2% |
| UNSUPPORTED_TRANSFORM | 34 | 1.1% |
| MASK_UNSUPPORTED | 31 | 1.0% |
| SCRIPT_OR_HANDLER | 24 | 0.8% |
| EMPTY_GEOMETRY | 19 | 0.6% |
| PATTERN_UNSUPPORTED | 13 | 0.4% |
| PARSER_ERROR | 9 | 0.3% |
| UNRESOLVED_REFERENCE | 5 | 0.2% |
| UNSUPPORTED_UNIT | 1 | 0.0% |

## Blocker multiplicity histogram

How many distinct rejection reasons apply to each file. Zero reasons
means the file normalizes.

| Distinct reasons | Files | Percent |
| --- | --- | --- |
| 0 (normalized) | 1733 | 55.5% |
| 1 | 1023 | 32.7% |
| 2 | 156 | 5.0% |
| 3 | 125 | 4.0% |
| 4+ | 88 | 2.8% |

Normalized (zero reasons): 1733 of 3125 files (55.5%).

## Stacked-blocker co-occurrence

For each of the three biggest reject buckets, how many of its files
ALSO carry at least one other distinct reason. Those files would NOT
normalize even if that one bucket were fully solved.

| Reason | Files with reason | Also blocked by another | Solved by this bucket alone |
| --- | --- | --- | --- |
| STYLE_GEOMETRY_UNSUPPORTED | 683 | 201 | 482 |
| TEXT_UNSUPPORTED | 314 | 89 | 225 |
| DOCTYPE_OR_ENTITY | 234 | 181 | 53 |

## Feature prevalence

| Feature | Files | Percent |
| --- | --- | --- |
| clip_path | 1393 | 44.6% |
| inline_style | 1228 | 39.3% |
| transform_attr | 965 | 30.9% |
| nested_groups | 894 | 28.6% |
| style_block | 729 | 23.3% |
| non_ascii_id | 543 | 17.4% |
| shape_rect | 407 | 13.0% |
| gradient | 387 | 12.4% |
| text | 314 | 10.0% |
| shape_ellipse | 291 | 9.3% |
| shape_circle | 290 | 9.3% |
| shape_polygon | 196 | 6.3% |
| foreign_object | 164 | 5.2% |
| attribution | 150 | 4.8% |
| image | 119 | 3.8% |
| shape_line | 114 | 3.6% |
| use_or_symbol | 102 | 3.3% |
| filter | 54 | 1.7% |
| shape_polyline | 42 | 1.3% |
| marker | 37 | 1.2% |
| mask | 31 | 1.0% |
| script_or_handler | 24 | 0.8% |
| pattern | 16 | 0.5% |
| parse_error | 8 | 0.3% |

## Verdict distribution

| Verdict | Files | Percent |
| --- | --- | --- |
| normalized | 1733 | 55.5% |
| STYLE_GEOMETRY_UNSUPPORTED | 482 | 15.4% |
| TEXT_UNSUPPORTED | 295 | 9.4% |
| DOCTYPE_OR_ENTITY | 234 | 7.5% |
| CLIPPATH_UNSUPPORTED_COMPLEX | 108 | 3.5% |
| EMBEDDED_RASTER_UNSUPPORTED | 73 | 2.3% |
| USE_OR_SYMBOL_UNSUPPORTED | 38 | 1.2% |
| UNSUPPORTED_TRANSFORM | 34 | 1.1% |
| FILTER_UNSUPPORTED | 32 | 1.0% |
| MARKER_UNSUPPORTED | 22 | 0.7% |
| SCRIPT_OR_HANDLER | 21 | 0.7% |
| EMPTY_GEOMETRY | 19 | 0.6% |
| FOREIGNOBJECT_UNSUPPORTED | 15 | 0.5% |
| PARSER_ERROR | 7 | 0.2% |
| UNRESOLVED_REFERENCE | 5 | 0.2% |
| PATTERN_UNSUPPORTED | 2 | 0.1% |
| MASK_UNSUPPORTED | 2 | 0.1% |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 | 0.1% |
| UNSUPPORTED_UNIT | 1 | 0.0% |

## Clipping deep-dive

Files containing a `clipPath`: 1393 (44.6% of corpus).

Verdict among clipPath-bearing files:

| Verdict | Files |
| --- | --- |
| normalized | 1070 |
| CLIPPATH_UNSUPPORTED_COMPLEX | 107 |
| TEXT_UNSUPPORTED | 96 |
| DOCTYPE_OR_ENTITY | 59 |
| USE_OR_SYMBOL_UNSUPPORTED | 23 |
| STYLE_GEOMETRY_UNSUPPORTED | 15 |
| EMBEDDED_RASTER_UNSUPPORTED | 7 |
| UNSUPPORTED_TRANSFORM | 6 |
| SCRIPT_OR_HANDLER | 3 |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 |
| MARKER_UNSUPPORTED | 2 |
| FOREIGNOBJECT_UNSUPPORTED | 2 |
| FILTER_UNSUPPORTED | 1 |

## Transform deep-dive

Files containing a `transform=` attribute: 965 (30.9% of corpus).

Verdict among transform-bearing files:

| Verdict | Files |
| --- | --- |
| TEXT_UNSUPPORTED | 277 |
| normalized | 214 |
| DOCTYPE_OR_ENTITY | 142 |
| CLIPPATH_UNSUPPORTED_COMPLEX | 64 |
| EMBEDDED_RASTER_UNSUPPORTED | 63 |
| STYLE_GEOMETRY_UNSUPPORTED | 62 |
| UNSUPPORTED_TRANSFORM | 34 |
| FILTER_UNSUPPORTED | 30 |
| USE_OR_SYMBOL_UNSUPPORTED | 23 |
| SCRIPT_OR_HANDLER | 18 |
| MARKER_UNSUPPORTED | 17 |
| FOREIGNOBJECT_UNSUPPORTED | 13 |
| UNRESOLVED_REFERENCE | 5 |
| EXTERNAL_RESOURCE_UNSUPPORTED | 2 |
| PATTERN_UNSUPPORTED | 1 |

