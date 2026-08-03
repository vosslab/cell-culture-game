# M1B-2 discovery and seam proposal (WP-DISC)

Status: DONE - all five HARD-GATE items resolved. No revised seam needed; the
authored shapes and material handling are well-defined. One wiring gap and one
acceptance-gate wording caveat are flagged for WP-SEAM/WP-CHECK below.

Plan: `resilient-twirling-pond.md`, milestone M-DISC, work package WP-DISC.
Scope: read-only discovery. This report is the sole deliverable.

All evidence is grounded in file:line references against the current tree.

## Item 1 - final_state_matches authored shape and how the load pass reads (object, field, value)

### Authored shape: sibling keys `target:` + `contains:`, NOT nested `parameters`

`final_state_matches` is authored as sibling keys on the `step_validator`
mapping: `preset:`, `target:` (a single object/subpart name), and `contains:`
(a flat `{ field: value }` map). There is no nested `parameters` map.

Real snippets:

- `content/protocols/cell_culture/mtt_reagent_prep/protocol.yaml:147-151`
  ```yaml
  step_validator:
    preset: final_state_matches
    target: mtt_solution_tube
    contains:
      material_volume: 1.0
  ```
- `content/protocols/cell_culture/trypan_blue_counting/protocol.yaml:364-368`
  ```yaml
  step_validator:
    preset: final_state_matches
    target: cell_counter
    contains:
      viability_percent: 90
  ```

These are the ONLY two `final_state_matches` usages in the entire content corpus
(`grep -rn final_state_matches content/`). Both target object-level (not dotted
subpart) float fields.

### Parsed config representation

The parsed `ValidatorReference` (`src/shell/adapter/types.ts:272-277`) carries
all three authored slots as optional fields:

```ts
export interface ValidatorReference {
  readonly preset: ValidatorPreset;
  readonly value?: Readonly<Record<string, string | number | boolean>>;   // target_with_value
  readonly target?: string;                                               // final_state_matches
  readonly contains?: Readonly<Record<string, string | number | boolean>>;// final_state_matches
}
```

`step.step_validator` is a `ValidatorReference`
(`src/shell/adapter/types.ts:357`). The generated bundle preserves the same
sibling-key shape (`generated/protocols.ts:12`,
`step_validator: { preset: "final_state_matches", target: "mtt_solution_tube", contains: { material_volume: 1.0 } }`).

### WIRING GAP (confirmed) - the runtime does NOT read target/contains today

`final_state_matches` is effectively a no-op at runtime in the current build.
Two independent breaks:

1. `to_validator_step` (`src/scene_runtime/protocol/step_machine.ts:376-381`)
   maps ONLY `step.step_validator.value` into `parameters`; it never reads
   `.target` / `.contains`. For a `final_state_matches` step `.value` is
   undefined, so the validator's `parameters` is never populated.
2. `emit_step_validator_outcome`
   (`src/scene_runtime/protocol/step_machine.ts:531`) calls
   `dispatch_step_validator(preset, validator_step, step.sequence.length, undefined)`
   - the `object_state_snapshot` argument is hardcoded `undefined`.

Downstream, `validate_final_state_matches`
(`src/scene_runtime/protocol/validators.ts:297-332`) reads
`step.step_validator.parameters` (undefined here -> returns `false` at line 302)
against an empty `{}` snapshot. A `grep` across `src/` confirms NOTHING reads
`step_validator.target` or `step_validator.contains` at runtime (only
`validate_protocol_presets` mentions the preset name as a string at
`step_machine.ts:413`).

Implication for M1B-2: this is a PRE-EXISTING runtime gap and is OUT OF SCOPE to
fix here (the plan's non-goals forbid reworking the runtime comparison path).
The M1B-2 load-time pass must read the ACTUAL AUTHORED shape
(`step_validator.target` + `step_validator.contains`), NOT `.value` and NOT
`parameters`, because the runtime's `parameters` projection is broken for this
preset and would give the load pass nothing to check. WP-CHECK reads
`step_validator.target` (object/subpart name) and iterates
`step_validator.contains` ({field -> value}) directly off `ProtocolConfig`.

### Exact load-pass read recipe for BOTH state-touching validators

For each step in `config.steps`:

- target_with_value interaction (flat `value: { field: val }`): for each
  interaction in `step.sequence` whose `interaction.validator.preset ===
  "target_with_value"`, the object/subpart name is `interaction.target` and the
  field->value pairs are the entries of `interaction.validator.value`. This
  mirrors the runtime, which builds parameters from `ref.value`
  (`step_machine.ts:351-362` `validator_parameters`) and uses the
  `${interaction.target}.${key}` context string (`validators.ts:255`).
- final_state_matches step (sibling `target:` + `contains:`): the object/subpart
  name is `step.step_validator.target` and the field->value pairs are the
  entries of `step.step_validator.contains`. (Do NOT route through
  `to_validator_step`/`parameters`; read the authored fields directly.)

## Item 2 - structured lookup RESULT type (material handling decided, not hand-waved)

### Schema facts

- `resolve_schema(object_name, subpart)`
  (`src/scene_runtime/state/scene_store.ts:199-207`) selects
  `OBJECT_STATE_SCHEMAS` for object targets and `OBJECT_SUBPART_STATE_SCHEMAS`
  for subpart targets (keyed by object_name). Throws on a missing object entry.
- `StateFieldDef.type` is `"enum" | "int" | "float" | "bool"`
  (`src/scene_runtime/layout/types.ts:71-86`); enum fields may carry
  `allowed?: string[]`.
- Material identity is NOT a distinct type token. The fields `material_name` and
  `held_material_name` are declared as `type: "enum"` but their RUNTIME
  acceptance is registry-backed when (and only when) the field is on a SUBPART:
  `REGISTRY_BACKED_MATERIAL_FIELDS = {material_name, held_material_name}`
  (`scene_store.ts:59-62`) routes a SUBPART write through
  `is_accepted_material_name(value, registry)`
  (`src/scene_runtime/renderer/material_acceptance.ts:46-65`), SKIPPING the
  declared enum `allowed` floor (`scene_store.ts:281-284`). An OBJECT-level
  material field keeps the generic enum `allowed` gate (the `is_subpart &&`
  guard at `scene_store.ts:281`).

### The material trap (why this matters and is not a fake enum)

`well_plate_96` subpart `material_name` declares `allowed: ['empty', 'mixed']`
(`generated/object_library.ts:7312-7320`) - the sentinel floor only. The
curriculum's drug/assay names (carboplatin, mtt, ...) live in each protocol's
`materials.yaml` registry, not in the object enum. If the load pass treated a
subpart `material_name` as enum-with-allowed-set `[empty, mixed]`, it would
WRONGLY REJECT a valid authored `material_name: carboplatin`. So a subpart
material field MUST report as "material field -> validate via material-name
checker", never as a synthetic enum. By contrast, OBJECT-level `material_name`
(e.g. `mtt_solution_tube`, `allowed: ['mtt_solution_12mm', 'empty']`,
`generated/object_library.ts:6435-6442`) is a genuine closed enum and validates
against `allowed`.

### Proposed result type (discriminated union)

The lookup returns a structured discriminated union (never a bare `{type,
allowed?}`, never null-only):

```ts
// protocol-layer type (no scene_store import)
export type StateFieldLookupResult =
  | { kind: "typed"; field_type: "int" | "float" | "bool" }
  | { kind: "enum"; allowed: readonly string[] | null }  // null = enum w/o declared allowed set
  | { kind: "material" }                                  // registry-backed; checked by impl, see note
  | { kind: "unknown_object" }
  | { kind: "unknown_subpart" }
  | { kind: "unknown_field" };
```

Mapping rule (in the construction-layer impl):

1. Split target on first "." -> (object_name, subpart|null) exactly as
   `split_target` (`scene_store.ts:181-193`).
2. Select registry: subpart === null -> `OBJECT_STATE_SCHEMAS`; else
   `OBJECT_SUBPART_STATE_SCHEMAS`. Missing object entry -> `unknown_object`
   (object target) or `unknown_subpart` (subpart target). (Return structured,
   never throw - the impl wraps `resolve_schema`'s throw or re-implements the
   lookup against the raw registries.)
3. Missing field on a resolved schema -> `unknown_field`.
4. Resolved field:
   - If subpart AND field_name in {material_name, held_material_name} ->
     `{ kind: "material" }`. The impl can ALSO pre-run
     `is_accepted_material_name(value, registry)` itself, because the impl holds
     `material_registry`; but to keep the protocol-layer rule the single owner of
     error behavior, the cleaner contract is: report `{kind:"material"}` and let
     the protocol-layer rule require a string value, then delegate value
     acceptance to a second injected predicate. SIMPLER alternative that still
     avoids a fake enum: for material fields, return
     `{ kind: "enum"; allowed: null }` (string required, no closed set checked) -
     i.e. fold material into "string-typed, membership not load-checkable". Given
     that NO authored content currently validates a material field (see Item 4
     note), either is safe; the union above keeps `material` explicit for
     durability and so a future author who DOES write a material value gets a
     value check via the registry. RECOMMENDATION: keep `{kind:"material"}`
     explicit and have the protocol-layer rule require a string (full registry
     value-check is optional and can defer, since today's corpus has no material
     value validators).
   - Else if field_type === "enum" -> `{ kind: "enum"; allowed: field.allowed ?? null }`.
   - Else -> `{ kind: "typed"; field_type }` (int/float/bool).

Sentinels: there are no "empty/mixed" SENTINEL VALUES the lookup must special-case
on the TYPE side; `empty`/`mixed` are accepted VALUES handled by
`is_accepted_material_name`, not schema types. The only "sentinel" is the
declared `allowed: [empty, mixed]` floor on subpart material fields, which the
lookup must NOT treat as the closed set (handled by the material branch above).

### Validation rules by result kind (for WP-CHECK)

- typed int/float: authored value is a number, OR a finite-parseable numeric
  string (mirror M1B-1 `coerce_observed_to_number`,
  `validators.ts:128-140`).
- typed bool: authored value is a boolean only (NOT "true"/"false" strings),
  mirroring `authored_value_matches` boolean branch (`validators.ts:116-118`)
  and `validate_value_type` (`scene_store.ts:351-352`).
- enum (allowed != null): string AND a member of `allowed`.
- enum (allowed == null): string (no closed-set check available).
- material: string (acceptance optionally delegated to the registry predicate;
  not load-checked against a closed set).
- unknown_object / unknown_subpart / unknown_field: load-time error, subject to
  the dev_smoke exemption (Item 3).

## Item 3 - complete dev_smoke exemption list

dev_smoke fixtures live under `tests/content/dev_smoke/`. Eight directories
exist; only those carrying `protocol_name` reach the generated bundle and thus
`create_step_machine`.

Generator gate: `pipeline/gen_protocols.py:113-114` skips any dev_smoke fixture
lacking `protocol_name` ("Legacy dev_smoke fixtures ... excluded from the new
generator surface. Skip rather than error"). Confirmed against
`generated/protocols.ts` keys.

| Fixture dir | Schema | In bundle? | Reaches create_step_machine? | State validator? | Target / value | Resolves? |
| --- | --- | --- | --- | --- | --- | --- |
| `type_check` | new (`protocol_type`) | YES (`type_check`) | YES | `target_with_value` | `cell_count_pad` / `entered_count: 42` | RESOLVES (object `cell_count_pad`, field `entered_count` type=int, `generated/object_library.ts:5545-5556`). MUST still validate (42 is a valid int). |
| `select_check` | new | YES (`select_check`) | YES | none (`correct_choice` target-equality, `tests/content/dev_smoke/select_check/protocol.yaml:20`) | `pbs_bottle` | n/a (no value validator) |
| `missing_svg_check` | new | YES (`missing_svg_check_check`) | YES | none (`correct_target`) | `test_missing_svg_target` (NOT in object library; INTENTIONAL unknown object) | INTENTIONALLY UNKNOWN - but no value validator, so the load pass never resolves a field for it; the unknown-object exemption is moot here unless WP-CHECK also checks bare interaction targets (it should NOT; the pass only checks state-touching validators). |
| `well_plate_96_zoom_check` | new | YES (`well_plate_96_zoom_check`) | YES | none (`correct_target`) | `well_plate_96.E7` (resolvable subpart) | n/a (no value validator) |
| `adversarial_overflow_smoke` | scene-only (no protocol.yaml) | n/a | NO | n/a | n/a | n/a |
| `long_labels_smoke` | scene-only (no protocol.yaml) | n/a | NO | n/a | n/a | n/a |
| `bench_direct_check` | LEGACY (`protocolType`, `entry:`, `completionPath: directTool`, `tests/content/dev_smoke/bench_direct_check/protocol.yaml:1-32`) | NO | NO (skipped by gen gate; no `protocol_name`) | n/a | n/a | n/a |
| `plate_reader_check` | LEGACY (`protocolType`, `entry:`, `tests/content/dev_smoke/plate_reader_check/protocol.yaml:1-15`) | NO | NO (skipped by gen gate) | n/a | n/a | n/a |

Confirmation requested by the plan: legacy fixtures `bench_direct_check` and
`plate_reader_check` do NOT reach `create_step_machine` (excluded from the
bundle). Only `type_check` exercises a state-touching validator, and its
object/field RESOLVE, so under the narrow exemption it must still be type-checked
(42 vs int -> passes). The intentional-unknown fixture (`missing_svg_check`)
references a missing OBJECT but only via a `correct_target` interaction, which the
load pass does NOT inspect (the pass checks `target_with_value` +
`final_state_matches` only). So the dev_smoke unknown-reference exemption has no
live trigger in the current fixture set, but WP-CHECK must still implement it
narrowly (only in the unknown-resolution branch) per the plan, so a FUTURE
dev_smoke fixture that writes a value to an unknown object/field loads while a
resolvable-but-malformed value still fails.

## Item 4 - complete set of state-touching validators

Only TWO validators compare authored values to object state:

- `target_with_value` (interaction; `validators.ts:233-262`) - compares
  `interaction.validator.value` entries against the value_map snapshot via
  `authored_value_matches`.
- `final_state_matches` (step; `validators.ts:297-332`) - compares
  `step_validator.contains` (authored) entries against the object_state_snapshot.

The other three presets do NOT touch object state:
`correct_target` (`validators.ts:178-185`), `correct_choice`
(`validators.ts:209-216`), `sequence_complete` (`validators.ts:279-284`) - all
target-equality or count checks with no value comparison. The closed preset sets
are `InteractionValidatorPreset` and `StepValidatorPreset`
(`src/shell/adapter/types.ts:27`). Confirmed: only `target_with_value` +
`final_state_matches`.

Corpus note (for WP-CHECK/WP-TEST expectations): across ALL content, every
authored `value:`/`contains:` field is NUMERIC (int/float): `set_volume` (47x),
`held_material_volume`, `material_volume`, `set_rpm`, `set_time_min`,
`set_time_s`, `set_voltage`, `wavelength_nm`, `viability_percent`,
`entered_count`. No authored bool, string-enum, or material value validators
exist today. The bool/enum/material branches are correctness-of-design for future
content and to avoid false positives, not exercised by the current corpus.

## Item 5 - create_step_machine seam signature and dotted-subpart rule

### Current signature and call sites

`create_step_machine(config: ProtocolConfig, emitter: RuntimeEmitterHandle,
scene_op_handler: SceneOpHandler)` (`src/scene_runtime/protocol/step_machine.ts:460-464`).

Production call site: exactly one, `src/protocol_host.tsx:308`
(`const step_machine = create_step_machine(active_config, emitter, scene_op_handler);`).
The construction layer already holds everything the lookup impl needs in scope at
that point: `scene_store` (line 224), `material_registry`
(`src/protocol_host.tsx:214`, `PROTOCOL_MATERIALS[protocol_name] ?? null`), and
it can import the generated schemas / `resolve_schema` directly.

ADDITIONAL callers WP-SEAM must update (the plan says "single call site" - true
for `src/`, but tests also call it positionally):
- `tests/test_m2_integration.mjs:141`
- `tests/test_step_machine.mjs:82,595,635`
These pass three positional args today and must be updated to the new signature.

### Recommendation: options object `{ lookup_state_field }`

Recommend threading the lookup via an options object as the FOURTH parameter:

```ts
export function create_step_machine(
  config: ProtocolConfig,
  emitter: RuntimeEmitterHandle,
  scene_op_handler: SceneOpHandler,
  options: { lookup_state_field: StateFieldLookup },
): StepMachineHandle
```

with

```ts
export type StateFieldLookup = (target: string, field: string) => StateFieldLookupResult;
```

Rationale:
- The plan explicitly prefers the options object "for durability if other
  load-time validators later need injected dependencies"
  (`resilient-twirling-pond.md:56-61, 240, 352-354`).
- `docs/TYPESCRIPT_STYLE.md` does not mandate positional vs options; it favors
  clear explicit params and narrow types. An options object with one named field
  is readable and extensible.
- CAVEAT: existing protocol-layer factories are positional
  (`create_step_machine(config, emitter, scene_op_handler)`,
  `create_scene_op_handler(deps)` at `scene_operations.ts:100`). A positional
  fourth arg would be locally consistent. The options object is still the
  recommended choice because the plan calls it out and future load-time deps are
  anticipated; the one-field object is a small, justified deviation. If WP-SEAM
  prefers strict local consistency, a positional `lookup_state_field` fourth arg
  is an acceptable fallback. Either way, value is the construction-layer impl.

### Dotted-subpart resolution rule

Split the target on the FIRST "." (mirror `split_target`,
`scene_store.ts:181-193`):
- no "." -> `(object_name = target, subpart = null)`; resolve against
  `OBJECT_STATE_SCHEMAS`.
- with "." -> `(object_name = before-first-dot, subpart = after-first-dot)`;
  resolve against `OBJECT_SUBPART_STATE_SCHEMAS[object_name]`.
- empty object segment or empty subpart ("plate.") is malformed; the impl should
  surface this as a structured unknown (it currently throws in
  `split_target`; the impl must catch/avoid the throw and return a structured
  result so the protocol-layer rule owns error behavior).

Distinguish, on miss: object registry has no entry -> `unknown_object` (object
target) / `unknown_subpart` (subpart target); object entry exists but field
absent -> `unknown_field`. Material/enum/typed routing as in Item 2.

## Acceptance-gate wording caveat (flag for WP-SEAM)

The plan's acceptance gate (`resilient-twirling-pond.md:275`) states
`rg "scene_store|object_library|registry" src/scene_runtime/protocol` must return
nothing. As written that gate ALREADY returns matches today, because
`scene_op_deps.ts` (line 46) and `walker_debug.ts` (line 45) legitimately import
the `SceneStore` TYPE, and several files mention "scene_store" in comments. The
plan's BODY scopes the no-import rule to the two files that must stay clean:
`validators.ts` and `step_machine.ts` (`resilient-twirling-pond.md:88, 114, 323`).
WP-SEAM should treat the gate as "no NEW store/registry import in
`validators.ts` or `step_machine.ts`", verified e.g. with
`grep -n "scene_store\|object_library\|registry"
src/scene_runtime/protocol/validators.ts src/scene_runtime/protocol/step_machine.ts`
(should stay empty), not a blanket directory grep.

## Handoff summary

- (1) final_state_matches: authored as `step_validator.target` + `.contains`
  ({field->val}); runtime does NOT read these (broken via `to_validator_step`
  `.value`-only mapping + hardcoded `undefined` snapshot). Load pass reads the
  authored fields directly. target_with_value reads `interaction.target` +
  `interaction.validator.value`.
- (2) Lookup result: discriminated union `typed(int|float|bool) | enum(allowed|null)
  | material | unknown_object | unknown_subpart | unknown_field`. Subpart
  material_name/held_material_name => `material` (registry-backed, NOT enum);
  object-level material_name => real enum w/ allowed. No type-side sentinels.
- (3) dev_smoke: only `type_check` hits a state validator (`cell_count_pad` /
  `entered_count: 42`, RESOLVES -> must validate). `bench_direct_check` and
  `plate_reader_check` are legacy and do NOT reach create_step_machine.
  `missing_svg_check` has an intentional unknown object but only via
  `correct_target` (not checked by the pass).
- (4) Exactly two state-touching validators: `target_with_value` +
  `final_state_matches`. Current corpus uses numeric fields only.
- (5) Seam: add fourth param `options: { lookup_state_field: StateFieldLookup }`
  to `create_step_machine`; update the one src caller (`protocol_host.tsx:308`)
  plus three test callers. Split target on first "." for object vs
  OBJECT_SUBPART_STATE_SCHEMAS. Acceptance-gate grep must be scoped to
  validators.ts + step_machine.ts (caveat above).
