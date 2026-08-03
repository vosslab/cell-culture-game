# Aesthetic geometry levers evidence

Consolidated read-only evidence for the three candidate geometry levers from round-0.
Source material: three investigator passes over `test-results/m7_after_r17/` PNGs,
`generated/precomputed_layout.ts`, and the layout engine source under
`src/scene_runtime/layout/`.

Prior context:
[aesthetic_baseline_round0.md](aesthetic_baseline_round0.md) and
[aesthetic_round1_grounding.md](aesthetic_round1_grounding.md).

---

## Label-disambiguation lever

Lowest risk; genuine engine fix.

**Root cause.** In `src/scene_runtime/layout/layout_labels.ts` the nudge pass computes
separation `want` from the authored `label_width` budget average, not from
`effectiveLabelHalfWidth` (the wider of budget vs rendered text width, already defined in
that file but used only in the stagger row-fit test). Wide labels therefore overprint while
the engine reports convergence.

**Diagnostic blind spot.** `electrophoresis_bench` renders overlapping labels yet diagnostics
report 0 label codes / converged. The `effectiveLabelHalfWidth`-in-nudge fix closes both the
visual overlap and this blind spot.

**Route elsewhere (not the label layer).**
- `hood_basic` and `seeding_workspace`: "BSC workspace" orphan labels sit over empty zone
  slots; need object-move or render-layer label suppression.
- `sample_prep_bench`: two objects share identical text "Microtube rack (24-slot)"; needs
  authoring rename (human decision).

**Ranked label-layer targets** (label coords only, no object move):

| Rank | Scene | Issue |
| --- | --- | --- |
| 1 | `electrophoresis_bench` | Top-left 3-label overprint |
| 2 | `seeding_workspace` | Bottom-left 4-item cramped strip |
| 3 | `staining_bench` | Adjacent near-identical bottle names |

---

## Void-collapse lever

Reframed: authoring fix, not engine algorithm.

**Investigator conclusion.** The engine (`horizontal_layout` / `vertical_layout` /
`row_strategy`) places objects correctly within their zones. Voids come from sparsely
positioned zones in scene YAML (zone `y` baselines and per-placement `align_stop`). The fix
surface is scene YAML, not engine code.

**Ranked center-emptiness** (approximate void area as percent of scene):

| Rank | Scene | Approx. void % | Note |
| --- | --- | --- | --- |
| 1 | `staining_bench` | ~85% | Wide vertical inter-zone gap y=32-44 |
| 2 | `electrophoresis_bench` | ~72% | |
| 3 | `sample_prep_bench` | ~65% | |
| 4 | `cell_counter_basic` | ~55% | |
| 5 | `seeding_workspace` | ~48% | |
| 6 | `bench_basic` | ~42% | Borderline |
| 7 | `passage_hood_detachment_microscope_view` | ~38% | Intentional framing; do NOT collapse |
| 8 | `hood_basic` | ~32% | Fine as-is |

---

## Focal-promotion lever

Mixed engine/authoring; some targets debatable.

**Primary-area percent** (area / 8820 scene units, from precomputed layout):

| Scene | Object | Primary area % | Caveat |
| --- | --- | --- | --- |
| `sample_prep_bench` | `micropipette` | 0.3% | Suspicious pick; micropipette as focal is debatable |
| `heat_block_bench` | `heat_block` | 1.2% | |
| `seeding_workspace` | `well_plate_96` | 1.4% | |
| `electrophoresis_bench` | `electrophoresis_tank` | 3.0% | |
| `staining_bench` | `staining_tray` | 3.1% | |
| `bench_basic` | `centrifuge` | 10.2% | |
| `cell_counter_basic` | `cell_counter` | 12.4% | |
| `hood_basic` | `hood_surface` | 14.6% | Ambiguous; `well_plate_96` at 5.7% also candidate |
| `passage_hood_detachment_microscope_view` | `microscope` | 18.1% | |

**Promotion mechanisms.** Mostly object YAML `display_width_cm` or scene YAML dedicated
zones; only partly engine shrink-priority. Several "primary" picks are debatable.

---

## Cross-cutting concern

`heat_block_bench.png` is absent from `test-results/m7_after_r17/` (`bench_basic.png` is
present instead). Confirm whether `heat_block_bench` is a distinct scene requiring its own
render pass before acting on its focal-promotion row above.

---

## Recommendation

| Lever | Fix surface | Status |
| --- | --- | --- |
| Label-disambiguation | Engine (`layout_labels.ts` nudge pass) | Being implemented now |
| Void-collapse | Scene YAML (zone `y` baselines, `align_stop`) | Deferred; user-scope authoring decision |
| Focal-promotion | Object YAML (`display_width_cm`) + scene YAML zones | Deferred; user-scope authoring decision |

Lever 1 (label nudge fix) is the one genuine engine improvement confirmed by this evidence.
Levers 2 and 3 are largely authoring changes to pedagogical scene composition across many
scenes; rewriting that composition is a user-scope decision, deferred pending user direction.
