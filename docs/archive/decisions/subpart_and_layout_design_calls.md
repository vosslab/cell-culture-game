# Subpart and layout design calls (architect brief)

- Date: 2026-07-04
- Status: decision-ready; packaged for one architect ruling
- Author: architect brief (packages three held/decision-ready items)

This brief packages the three design calls left open at the close of the
velvet-napping-tower plan (Release 1 + 2). All implementation is done; only
these decisions remain. They are gathered here so the subpart-identity call and
the two layout calls land together instead of scattered across the register and
the plan.

Loud-and-owned discipline (from the walker click-bug register): every item below
names a concrete question, the evidence already gathered, the options with
trade-offs, the current owner, and the exact action that clears it. Each item is
tagged PEDAGOGY (needs human sign-off) or ENGINE/LAYOUT (the architect may
default).

Cross-linked source docs (Markdown links, confirmed tracked):

- [walker_click_bug_register.md](../../archive/audits/walker_click_bug_register.md) -- the
  owned ledger; see row OP1 and the O-series scene-manager rows.
- [subpart_click_pattern.md](subpart_click_pattern.md) -- the Direction-A ruling
  that made the interaction-level `- target:` a base placement, with subpart
  suffixes legal only nested inside a response.

Layout evidence docs are cited as `path:line` (backticked) below rather than as
Markdown links: their git-tracked status is not verifiable in this session
without running git, and the link test (`tests/test_markdown_links.py`) requires
every Markdown link target to be tracked. Backticked paths are masked out of the
link scan, so they cite the evidence safely whether or not those docs are yet
committed. When they are confirmed tracked, they may be promoted to Markdown
links.

## Item 1: discrimination-bearing subpart click (Direction-B RFC) -- PEDAGOGY

### Question

Should a discrimination-bearing subpart click -- one where the student must pick
the CORRECT subpart among its present siblings (`tube_A..G`, a specific `lane_N`,
a specific dosed `well_XX`) -- be a first-class interaction-level target
(Direction B), rather than being forced to a base-placement click (Direction A)?

This is the only case Direction A does not faithfully serve. The class ruling
already holds it: base-click is the canonical MECHANISM for every non-
discrimination subpart write, but for a graded "which subpart" choice, collapsing
to a base-object click erases the taught skill and degenerates the UX.

### Evidence already gathered

- Register row OP1 (PEDAGOGY-HELD, class-wide) in
  [walker_click_bug_register.md](../../archive/audits/walker_click_bug_register.md): the
  discrimination-bearing subpart-click class, owner ARCHITECT via a Direction-B
  RFC. Today's only member is `plate_drug_treatment_drug_addition`.
- Register full-register row for the live failure:
  `walker_click_bug_register.md:87` -- `plate_drug_treatment_drug_addition`, step
  `add_carb_row_b`, target `rear_center_carb_stocks.tube_A` not in DOM (fails on
  row B, the first row walked). Subparts render as a `pointer-events: none`
  material overlay with no DOM hit target, so the click can never resolve.
- Class ruling and the Direction-B RFC stub in
  [subpart_click_pattern.md](subpart_click_pattern.md): Direction A is spec-
  correct as the mechanism (`subpart_click_pattern.md:1-15`); the class stays held
  because base-click erases "which dose in which well/row, which lane"
  (`subpart_click_pattern.md:17-68`); the RFC scope reverses the architect-locked
  `pointer-events: none` overlay contract and touches the renderer plus scene YAML
  (`subpart_click_pattern.md:70-102`).
- Pedagogy table (`subpart_click_pattern.md:187-193`):
  `plate_drug_treatment_drug_addition` teaches "well-by-row targeted addition of
  variable-concentration drugs" (different wells/rows get different doses); the
  standout case. `sdspage_load_protein_ladder` names "verify correct lane
  targeting" as an explicit outcome. Both drop specificity under base-click.
- The `select` gesture was evaluated and does NOT recover subpart specificity: it
  reuses the same visible scene-object affordance as `click` and can only choose
  among present BASE placements (`subpart_click_pattern.md:209-238`).
- The CHANGELOG 2026-07-04 entry records the same live block: single-well writes
  live only in `plate_drug_treatment_drug_addition`, blocked upstream by the
  `rear_center_carb_stocks.tube_A` missing-in-DOM state, outside the walker task
  boundary.

### Options and trade-offs

- Option A (keep Direction A, soften the pedagogy): rewrite the held protocol to
  base-placement clicks and soften the affected `learning` outcome wording to the
  object level (for example "load the ladder into the gel" instead of "verify
  correct lane targeting"). No new primitive, no render change, stays green. Cost:
  the graded "which subpart" skill is dropped, and `plate_drug_treatment_drug_
  addition` degenerates to ~12 identical plate clicks per row (poor UX).
- Option B (Direction-B RFC): give discrimination-bearing subpart overlays
  (`tube_X`, `well_XX`, `lane_N`) their own `[data-item-id]` click targets in the
  renderer and scene model, so `click`/`select` can address one subpart. Cost:
  reverses an architect-locked render contract (subparts are `pointer-events:
  none` overlays on purpose), touches the scene renderer and scene YAML, and must
  clear the PRIMARY_DESIGN new-primitive evidence bar (existing primitives cannot
  express it; the need spans multiple protocols; the subpart is a stable reusable
  semantic unit). Benefit: preserves genuine subpart-discrimination pedagogy that
  base-click cannot exercise.
- Option C (hold as-is): keep the class documented as a known-red walker
  exception until the pedagogy owner decides the skill is essential. Cost: one
  protocol stays red by design; benefit: no premature contract reversal.

### Owner and clearing action

- Tag: PEDAGOGY -- needs human sign-off. The MECHANISM question (Direction A vs B)
  is the architect's to route, but the load-bearing question is pedagogical:
  is subpart discrimination essential teaching for
  `plate_drug_treatment_drug_addition` (and any future member)? That judgment is
  the pedagogy owner's, not auto-defaultable.
- Owner: ARCHITECT routes; pedagogy owner signs off on the essential-teaching
  question.
- Clears when: the pedagogy owner rules essential (-> Option B, architect opens
  the Direction-B RFC) or non-essential (-> Option A, base-click rewrite plus
  outcome softening, applied by the content/walker lane). Either ruling unblocks
  `plate_drug_treatment_drug_addition` and closes register row OP1.

## Item 2: per-band rescale promotion (D2 unfittable-asset signal) -- ENGINE/LAYOUT

### Question

When (if ever) should the D2 "unfittable asset" signal be promoted from
WARNING-only (`failBuild: false`) to a build-failing Error, once the shrink-
stressed scenes are readable?

### Evidence already gathered

- D2 firm decision in the plan (`velvet-napping-tower.md:720`): the `failBuild`
  promotion stays OUT for now because a `failBuild` gate would break the build on
  ~17-21 shrink scenes that are the scene-manager's aesthetics work; M17 lands D2
  as a WARNING-only diagnostic that names the asset + zone; promotion waits for a
  later layout pass once the shrink scenes are readable.
- M17 acceptance criteria (`velvet-napping-tower.md:550`): D2 ships as a
  WARNING-only diagnostic that names the asset + zone when required scale drops
  below the readable floor; it does not fail the build (the ~20 shrink scenes stay
  green), it only makes the degradation legible for the scene-manager pass.
- Root-cause mechanism, per-band rescale record in
  `uniform_rescale_per_band_floor.md:7-15,67-73`: one over-tall label band sets
  the single scene-wide `uniform_rescale` factor for every unrelated object; a
  tier collapse yields ZERO factor gain on `label_dominant` scenes. The
  recommendation is per-band or per-object scale floors so a label-dominant band
  stops setting the factor for the whole scene.
- The current WARNING signal is a PROXY, not a true rescale-iteration count
  (`velvet-napping-tower.md:80`): band approval and the engine's iteration-count
  exposure are separate work; M5/M19 wired the failBuild gate without touching
  band ratification.
- Affected scenes table (`uniform_rescale_per_band_floor.md:22-34`): eleven
  `label_dominant`, `tier_collapsible=False` scenes at factor 0.50-0.58, including
  the seven SDS-PAGE children plus `electrophoresis_bench` (crowd=0, the cleanest
  label-dominant demonstration).

### Options and trade-offs

- Option A (default, keep WARNING-only): leave D2 as `failBuild: false` until the
  scene-manager readability pass and the per-band engine change land. Cost: the
  ~20 shrink scenes stay green with a legible-but-non-blocking signal; benefit:
  the build never breaks on known-degraded-but-acceptable scenes.
- Option B (promote to failBuild after the shrink pass): flip D2 to
  `failBuild: true` once the per-band rescale change lifts the label-dominant
  floors and the scene-manager confirms the shrink scenes are readable. Cost:
  premature promotion breaks the build on ~20 scenes; benefit: once the floors are
  lifted, an unfittable asset becomes a hard, preventive regression gate.
- Option C (replace the PROXY with a true iteration count first): expose the
  engine's real rescale-iteration count before any promotion, so the gate keys on
  a true signal rather than the shrink proxy. Cost: separate engine work; benefit:
  a promoted gate would be trustworthy rather than proxy-based.

### Owner and clearing action

- Tag: ENGINE/LAYOUT -- the architect may default. The documented default is
  Option A (stay WARNING-only). No human pedagogy sign-off is required.
- Owner: ARCHITECT (layout diagnostics / failBuild gate lane owns the promotion
  decision; the scene-manager plan owns the per-band engine change and the shrink-
  scene readability).
- Clears when: the architect ratifies one of (A) keep WARNING-only until the
  shrink pass, (B) schedule promotion after the per-band change lands, or (C)
  require a true iteration count before promotion. Defaulting to A closes the item
  now with a documented trigger for revisiting.

## Item 3: centrifuge crowd=4 density -- ENGINE/LAYOUT

### Question

Is a crowd=4 object density in one zone (`centrifuge_workspace`, `right_tool_
area`) an acceptable per-zone density, or does it need a density rework? This is
the scene-manager-owned overlap/crowding call that needs a design ruling on
acceptable object density per zone.

### Evidence already gathered

- The crowd=4 engine-only evidence is explicitly routed to the architect
  alongside the per-band record (`uniform_rescale_per_band_floor.md:81`).
- The single global `uniform_rescale` factor couples one over-tall row to every
  unrelated object; the durable fix is a per-band/per-zone factor
  (`downscaling_sweep_and_uniform_rescale_coupling.md:61-74`). Centrifuge's
  crowding is the standard packer floor of dm_shrink-crowded objects in a packed
  zone, not a whole-scene readability defect.
- The scene currently PASSES the corpus sweep and reports zero build-failing
  errors: `ws_m4c_scene_corpus_sweep.md:22` (`centrifuge_workspace` populated,
  100%, 13 placements, 0 hard-fail, PASS); `layout_diagnostics_baseline.md:17,84`
  (2 diagnostics, `label_row_staggered=2`, no `unresolved_overlap` Error).
- The residual is label-pair crowding, not art overlap or clipping:
  `label_alignment_baseline_audit.md:54,97` (score 14.6, two label-pair overlaps,
  highest `lbl_pairs` count in the corpus, no art overlaps or clipping);
  `top_label_collision_forecast.md:100-102,122` (3 of 14 forecast conflicts, all
  in `right_tool_area`, with 0 rendered overlap at `top_label_collision_
  forecast.md:226`).
- Precedent for the density call: the analogous `hemocytometer_view` density is
  routed for a density decision -- either gate-exempt like the other dense
  fixtures, or a separate density rework ticket
  (`downscaling_sweep_and_uniform_rescale_coupling.md:78-82`).

### Options and trade-offs

- Option A (accept as-is, default): rule crowd=4 in `right_tool_area` an
  acceptable per-zone density; the scene PASSes with 0 build-failing errors and
  only forecast label-pair crowding. Cost: two label pairs stay close in one zone;
  benefit: no rework, matches the existing packer-floor precedent.
- Option B (density rework ticket): open a scene-manager ticket to thin or re-zone
  `right_tool_area` (widen the tool zone or move an object out). Cost: a
  `hood_basic`-class base edit risks regressing sibling scenes that share the
  zone; benefit: lifts the two crowded objects above the packer floor.
- Option C (gate-exempt, documented dense-by-design): treat centrifuge like the
  other intentional dense fixtures and record it as accepted density. Cost:
  encodes the density as permanent; benefit: closes the forecast churn cleanly.

### Owner and clearing action

- Tag: ENGINE/LAYOUT -- the architect may default. No pedagogy sign-off required.
- Owner: scene-manager plan owns any scene-YAML density edit; the ARCHITECT owns
  the ruling on acceptable per-zone density (the engine-only evidence was routed
  to the architect).
- Clears when: the architect rules on acceptable per-zone density -- (A) accept
  as-is, (B) hand the scene-manager a density rework ticket, or (C) record it as
  gate-exempt dense-by-design. Defaulting to A closes the item now, since the
  scene already PASSes the gate with only forecast label-pair crowding.

## Summary

| Item | Tag | Owner | Clears when |
| --- | --- | --- | --- |
| 1. Discrimination-bearing subpart click (Direction-B RFC) | PEDAGOGY (human sign-off) | ARCHITECT routes; pedagogy owner decides essential-teaching | pedagogy owner rules essential (Option B RFC) or non-essential (Option A rewrite); closes register row OP1 |
| 2. Per-band rescale promotion (D2) | ENGINE/LAYOUT (architect default) | ARCHITECT (diagnostics gate); scene-manager owns per-band engine change | architect ratifies keep-WARNING (default A), schedule promotion (B), or true-count-first (C) |
| 3. Centrifuge crowd=4 density | ENGINE/LAYOUT (architect default) | scene-manager owns YAML; ARCHITECT rules on acceptable density | architect rules accept-as-is (default A), rework ticket (B), or gate-exempt (C) |
