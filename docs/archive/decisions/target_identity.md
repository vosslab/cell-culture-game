# Target-identity decision

Status: committed (architect, milestone M7). This is the settled default adopted
so the M8 target-adapter dispatch never blocks on an absent human. The human may
override later; until then this decision is binding and is M8's entry criterion.

## Decision

The protocol-target-to-DOM identity contract is split into two distinct keys:

- `placement_name` is the DOM and target key. It is unique per placement within a
  scene, so it is the only key that stays unambiguous when a scene places the same
  object more than once.
- `object_name` remains the capability and asset lookup key. The object library
  resolves identity, structure, `state_fields`, `visual_states`, `capabilities`,
  and asset through `object_name`; that role does not move.
- A protocol `target` name is a semantic identifier. It resolves through the target
  adapter (M8) to exactly one `placement_name`. The adapter is the single place this
  resolution happens.

This ends the current implicit three-way string-equality contract
(`protocol.target === object_name === data-item-id`). That contract is unsound
because `object_name` is not unique: a scene may place one object twice
(`SCENE_YAML_FORMAT.md` Placements table, `placement_name` row), so `object_name`
cannot be a DOM key. `placement_name` is the stable per-scene unique handle and
becomes the key.

## Why placement_name

- Uniqueness. The scene format states directly that `placement_name` is
  "distinct from `object_name`: a scene may place the same object more than once, and
  each placement needs its own scene-scoped name." `object_name` is deliberately
  non-unique; a DOM identity key must be unique.
- It is already in the DOM. Every rendered element already carries
  `data-placement-name={item.placement_name}` (`src/scene_runtime/renderer/scene_item.tsx:595`
  and `:623`, both the placeholder and normal render paths). Only `data-item-id` is
  wrongly sourced from `item.object_name` (`:601`, `:629`). Adopting `placement_name`
  as the key is a routing change, not a data-plumbing change: the value already
  reaches the browser.
- Layer boundaries hold. Object stays the representation-and-capability layer keyed
  by `object_name`; scene owns placement keyed by `placement_name`; protocol stays
  geometry-free and names semantic targets that the adapter resolves. This matches the
  vocabulary-closure and strict-layer rules in
  [../../PRIMARY_SPEC.md](../../PRIMARY_SPEC.md) and
  [../../specs/SCENE_VOCABULARY.md](../../specs/SCENE_VOCABULARY.md).

## Affected surfaces

Every surface that today assumes `protocol.target === object_name === data-item-id`
is named below, with what M8 does to it.

| Surface | Location today | Change under this decision |
| --- | --- | --- |
| Content YAML target strings | `content/protocols/**/protocol.yaml` `target:` fields | No blanket change. Each `target` stays a semantic name resolved by the adapter. A `target` string changes only in the disambiguation case below. |
| `data-item-id` value | `scene_item.tsx:601`, `:629` (sourced from `item.object_name`) | Sourced from `item.placement_name` so the DOM click key is unique per placement. `data-placement-name` already carries this value; `data-item-id` is realigned to it. |
| Runtime target equality | `src/scene_runtime/protocol/step_machine.ts:699` (`interaction.target !== target`) | Both sides normalize through the adapter to a `placement_name` before comparison. The raw string compare of authored-target vs clicked-id is replaced by resolved-placement vs clicked-placement. |
| Walker reverse-lookup | `src/scene_runtime/protocol/walker_debug.ts:247-248` projecting `activeTarget` from `snapshot.active_interaction_target`; walker selector `#scene-root [data-item-id="<...>"]` (`WALKTHROUGH_GUIDE.md:320`) | `activeTarget` projects the adapter-resolved `placement_name`. The walker's existing selector then matches the realigned `data-item-id` with zero walker-logic change: `activeTarget` and `data-item-id` agree because both are the resolved `placement_name`. |
| Debug `activeTarget` | `walker_debug.ts:248` (`activeTarget: snapshot.active_interaction_target`) | Same field, now carrying the resolved `placement_name` rather than the raw authored target, so the read-only debug projection stays truthful post-adapter. |

Related but out of this decision: `data-target-id=""` (`scene_item.tsx:600`, `:628`)
is dead and is removed by M6 capability enforcement, not here. `data-object-name`
stays on the element as the capability/asset key.

## Must any protocol target string change?

No blanket rename is required or wanted. The rule is:

- Object placed once (every current protocol). No `target` string changes. The
  adapter auto-derives the registry entry `object_name -> its unique placement_name`,
  so an authored `target` that today equals `object_name` still resolves, even when
  the scene names the placement differently (the live example
  `placement_name: hood_flask` with `object_name: t75_flask`,
  `SCENE_YAML_FORMAT.md:235`). The adapter absorbs that translation.
- Object placed more than once, and a protocol must act on one specific placement.
  Here `object_name` is ambiguous and cannot resolve. The `target` string MUST become
  the scene-unique `placement_name` (or a semantic alias the adapter registers to one
  specific placement). No current protocol addresses a multiply-placed object, so this
  is a forward rule for M16 and future authoring, not a migration of existing content.
- Subpart targets (`treatment_plate.A1`). The adapter resolves the object/placement
  prefix to one `placement_name` and preserves the `.<subpart>` suffix. The same
  once-vs-twice rule applies to the prefix.

Bottom line for M8/M16 scope: this decision changes no existing protocol `target`
string. It changes the DOM key source, the runtime equality, and the debug
projection, all inside the adapter boundary. A `target` string changes only if and
when a protocol first needs to disambiguate two identical placements.

## Verification performed

- Checked against the dual-placement rule (`SCENE_YAML_FORMAT.md:212`): confirms
  `placement_name` is the unique per-scene handle and `object_name` is intentionally
  non-unique, which is the basis for choosing `placement_name` as the DOM key.
- Checked against the walker reverse-lookup contract
  ([../../specs/WALKTHROUGH_GUIDE.md](../../specs/WALKTHROUGH_GUIDE.md), the
  `resolveSelector()` / `activeTarget` -> `data-item-id` path at `:271-274`, `:316-320`):
  confirms the walker mirrors the runtime by clicking the `[data-item-id]` element
  whose id equals `activeTarget`. Keeping both as the resolved `placement_name` means
  the walker needs no per-protocol branch, honoring the walker-requirement rule in
  [../../PRIMARY_SPEC.md](../../PRIMARY_SPEC.md).

## Residual risks for M8

- Adapter registry source. The adapter must build `target -> placement_name` from the
  scene placements. For a singly-placed object the derivation is unambiguous; the
  adapter must fail loud, not silently pick one, if it ever finds an authored `target`
  that resolves to more than one placement with no disambiguation.
- Both-sides normalization at `step_machine.ts:699`. The click resolver must yield the
  clicked element's `placement_name` and `interaction.target` must be adapter-resolved
  before compare; normalizing only one side reintroduces the mismatch this decision
  removes.
- `activeTarget` truthfulness. `walker_debug.ts:248` must project the resolved
  `placement_name`; if it keeps projecting the raw authored `target` while
  `data-item-id` moves to `placement_name`, the walker selector silently misses.
- M8's own new fixture (a scene placing one object twice) is the acceptance probe for
  the disambiguation path; no existing scene exercises it, so the fixture is the only
  guard that the twice-placed case resolves each placement uniquely.
