# M12 contrast handoff

## Scope and decision

This is the durable color-accessibility handoff required by E8 and M12 of the
SVG visual-quality rebuild. It measures the real host colors that identify
active, candidate, focus, and observation-rail boundaries. It does not infer
contrast from an isolated SVG palette or treat hue alone as the state cue.

**Decision: APPROVED.** Every named non-text boundary meets the 3:1 graphical
contrast floor on its actual light surfaces. Rail text exceeds the 4.5:1 normal
text floor. Active and candidate states also retain a solid-versus-dashed
non-color distinction in the current grayscale captures.

## Repaired source boundary

The initial M12 handoff found three host-owned failures:

| Role | Initial color and measured failure | Current source color |
| --- | --- | --- |
| Active whole/exact-subpart cue | `#f5a623`: 1.57:1 on `#e8e2d0`, 1.25:1 on `#d4cbb3`, 1.76:1 on `#f2efe6` | `#9e6507` |
| Shared light-surface focus outline | `#f0a202`: 2.13:1 on white and 2.03:1 on `#f4fbfb` | `#c48402` |
| Observation/control boundary | `#829ab1`: 2.79:1 on `#fbfaf7` | `#718aa3` |

The hover and candidate blue is `#2563eb`. Hover uses a 2 px solid outline;
candidate uses a 3 px dashed outline. Active uses a 3 px solid orange outline,
and the exact-subpart indicator uses the same orange stroke with its translucent
fill. These are stylesheet-owned states in `src/style.css`, not SVG paint.

## Current measurements

All ratios below were recomputed from the current literals with
`tools/contrast_calculator.py` and target ratio 3.0.

| Cue | Foreground | Background | Ratio | Result |
| --- | --- | --- | ---: | --- |
| Active | `#9e6507` | `#e8e2d0` scene top | 3.76:1 | PASS |
| Active | `#9e6507` | `#d4cbb3` scene bottom | 3.01:1 | PASS |
| Active | `#9e6507` | `#f2efe6` fallback scene | 4.23:1 | PASS |
| Candidate/hover | `#2563eb` | `#e8e2d0` scene top | 3.99:1 | PASS |
| Candidate/hover | `#2563eb` | `#d4cbb3` scene bottom | 3.20:1 | PASS |
| Candidate/hover | `#2563eb` | `#f2efe6` fallback scene | 4.50:1 | PASS |
| Focus | `#c48402` | `#ffffff` | 3.16:1 | PASS |
| Focus | `#c48402` | `#f4fbfb` | 3.01:1 | PASS |
| Focus | `#c48402` | `#fbfaf7` | 3.03:1 | PASS |
| Focus | `#c48402` | `#fbfcfd` | 3.08:1 | PASS |
| Rail/control boundary | `#718aa3` | `#fbfaf7` | 3.43:1 | PASS |
| Fact boundary | `#718aa3` | `#f2f7f8` | 3.31:1 | PASS |
| Input/reset boundary | `#718aa3` | `#ffffff` | 3.58:1 | PASS |
| Rail body text | `#172033` | `#fbfaf7` | 15.59:1 | PASS |
| Rail heading text | `#334e68` | `#fbfaf7` | 8.28:1 | PASS |

## Real-consumer evidence

The refreshed production captures show the colors on the actual built scene
and rail surfaces:

- `docs/figures/svg_visual_quality_m12/protocol_active_whole_full.png`
- `docs/figures/svg_visual_quality_m12/protocol_p200_partial_exact_subpart.png`
- `docs/figures/svg_visual_quality_m12/protocol_trypan_candidate_full.png`
- `docs/figures/svg_visual_quality_m12/protocol_trypan_candidate_annotation_rail.png`
- the matching `_grayscale.png` active, exact-subpart, and candidate captures.

The active whole-object and exact-subpart cues remain solid in grayscale. The
candidate boxes remain dashed and wider, so candidate versus active does not
depend on hue. The current capture facts record zero page errors, console
errors, direct-label intersections, or annotation intersections.

## Repeatable calculation route

For any row, run the foreground and background literals through the repository
calculator. For example:

```bash
source source_me.sh && python3 tools/contrast_calculator.py \
    --check '#9e6507' --background '#d4cbb3' --ratio 3
```

The screenshot evidence is one-time visual proof. The source literals and the
real browser affordance tests remain the maintainable behavior boundary; no
pixel-equivalence regression test was added.
