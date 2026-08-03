# Load-time invariants blast-radius measurement

Read-only evidence for the two proposed load-time invariants raised during the
`no_active_interaction` cluster investigation. No code is landed. This measures
which protocols WOULD fail at load if each invariant were added, and whether any
CURRENTLY-PASSING protocol would newly red (the regression risk that gates the
sign-off).

- Date: 2026-07-04
- Method: static replay over generated (inheritance-resolved) data
  (`generated/protocols.ts`, `generated/precomputed_layout.ts`) using the real
  `resolve_entry_scene_name`, mirroring `target_existence_check.ts` scene
  tracking. Registry: 35 protocols (5 sequence_runners delegate to their minis;
  30 analyzed as step-carrying protocols).

## Proposed invariants

- Invariant 1 (reject ambiguous target): a `target` whose bare `object_name` is
  placed more than once in the scene active at that point throws
  `AmbiguousTargetError` in `resolve_to_placement` today, but only when reached
  mid-walk. The invariant promotes it to a named load-time error. Explicit
  placement-name targets resolve uniquely and are exempt.
- Invariant 2 (ObjectStateChange target must be seeded): an `ObjectStateChange`
  whose target is not a known placement/object in the active scene throws
  `scene_store: ... not seeded` at runtime today. The invariant promotes it to a
  load-time error.

## Result

| Invariant | Protocols that would RED | Newly-red among currently-PASSING |
| --- | --- | --- |
| 1 (ambiguous target) | 1: `sdspage_prepare_sample_mix_single_lane` | 0 |
| 2 (ObjectStateChange seeded) | 1: `passage_pellet_reseed` | 0 |
| Advisory (CursorAttach target not a scene placement) | 1: `passage_pellet_reseed` (`conical_15ml`) | n/a |

### Invariant 1 detail

- `sdspage_prepare_sample_mix_single_lane`, step `cap_and_rack[i1]`: target
  `microtube_rack_24` placed 2x (`center_microtube_rack`, `mid_eppendorf_rack`)
  in `sdspage_prepare_sample_mix_single_lane_workspace`.
- This protocol ALREADY fails the real walker today for the identical reason:
  `click_did_not_advance ... Ambiguous protocol target "microtube_rack_24"`.
  So Invariant 1 converts an already-broken mid-walk failure into a clear
  load-time error; it does not red any currently-passing protocol.
- `sdspage_heat_denature_samples` (the other historical hit) is already fixed by
  the M7 placement-name disambiguation to `front_microtube_rack`, so it no longer
  appears here.

### Invariant 2 detail

- `passage_pellet_reseed`, step `transfer_to_conical[i1]`: `ObjectStateChange`
  target `conical_15ml` not present in `hood_workspace` (it exists in
  `centrifuge_workspace`). Already fails the real walker today with the
  `not seeded` throw. No currently-passing protocol is newly red.

## Recommendation

Blast radius is effectively zero for currently-passing protocols. Both invariants
only touch protocols that are ALREADY broken at runtime, and they replace a
confusing torn-snapshot `no_active_interaction` symptom with a named, located
load-time error (matching the M13 / M16-D / `authored_value_check.ts` pattern).

Sequencing note: land the underlying content/scene fixes first (or in the same
change) so the two already-broken protocols pass, otherwise adding the invariants
moves their failure from mid-walk to load without fixing them:

- `sdspage_prepare_sample_mix_single_lane`: FIXED 2026-07-04 by the same M7
  placement-name disambiguation -- step `cap_and_rack` target
  `microtube_rack_24` -> `center_microtube_rack` (the front-working-surface rack
  literally named "microtube rack"; the other placement is the mid-bench
  `mid_eppendorf_rack` staging rack). Real walker now passes all 4 steps.
  Under Invariant 1 this protocol would no longer red.
- `passage_pellet_reseed`: seed `conical_15ml` in `hood_workspace` (scene-layer).

## Reproduce

- Static measurement script (not committed): imported `generated/protocols.ts` +
  `generated/precomputed_layout.ts` via `node --import tsx`, applied the two
  checks per reachable step with scene tracking.
- Walker confirmation of the two already-broken protocols:
  - `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol sdspage_prepare_sample_mix_single_lane`
  - `node tests/playwright/e2e/protocol_walkthrough_yaml.mjs --protocol passage_pellet_reseed`
