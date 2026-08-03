# Formula and scene-op inventory

Plan reference: M2, WS-M2-I
Date: 2026-06-02
Status: DONE_WITH_CONCERNS

## Purpose

This report answers two questions for downstream workstreams:

- (a) Which formula tokens do authored objects actually use, and what
  coverage scope does WS-M2-R (visual_state_resolver) need to implement?
- (b) Is `LayoutMove` used by any authored protocol, and what does that
  imply for the WS-M3-D Option A vs Option B decision?

---

## Section 1: Formula inventory (content/objects/**)

### Verification commands

```
grep -rn "formula:" content/objects/
grep -rn "fill_height" content/objects/ | wc -l
grep -rn "formula:.*label(" content/objects/ | wc -l
grep -rn "formula:.*conditional(" content/objects/ | wc -l
grep -rn "formula:.*compose(" content/objects/ | wc -l
grep -rn "capacity_mg=" content/objects/
```

### Token usage counts

| Formula token  | Count | Notes                                       |
| -------------- | ----- | ------------------------------------------- |
| `fill_height`  | 47    | All use `state(...)` + one capacity keyword |
| `label`        | 19    | All wrap `state(...)` + `format=` string    |
| `conditional`  | 4     | NOT in the closed spec token set (see below)|
| `compose`      | 0     | In spec; not yet used by any authored object|

Total formula lines: 68 (47 + 19 + 4 = 70 raw grep hits; 2 lines contain
nested `label` inside `conditional`, so they are counted once each).

### Objects using each token

#### fill_height (47 occurrences)

Capacity keyword variants:

| Keyword        | Count | Example object                |
| -------------- | ----- | ----------------------------- |
| `capacity_ml`  | 38    | `pbs_bottle.yaml`, `t75_flask.yaml` |
| `capacity_ul`  | 8     | `p200_micropipette.yaml`, `dilution_tube_rack_8.yaml` |
| `capacity_mg`  | 1     | `mtt_powder_container.yaml`   |

Object categories using `fill_height`:
- `bottle/`: 28 objects
- `pipette/`: 5 objects (`serological_pipette`, `p10_micropipette`,
  `p200_micropipette`, `micropipette`, `multichannel_pipette`,
  `aspirating_pipette`)
- `rack/`: 2 objects (`conical_15ml_rack`, `dilution_tube_rack_8`)
- `waste/`: 3 objects (`biohazard_decant`, `biohazard_decant_bin`,
  `waste_container`)
- `flask/`: 2 objects (`t75_flask`, `t75_flask_new`)
- `equipment/`: 3 objects (`electrophoresis_tank` uses it twice for
  inner and outer chambers, `staining_tray`)

#### label (19 occurrences)

Objects using `label(state(...), format=...)`:
- `pipette/`: `serological_pipette`, `p10_micropipette`, `p200_micropipette`,
  `micropipette`, `multichannel_pipette`
- `equipment/`: `incubator` (2x: temperature + CO2), `centrifuge` (2x: rpm +
  time), `plate_reader` (wavelength), `power_supply` (voltage), `heat_block`,
  `water_bath`, `rocking_shaker` (2x), `microwave`
- `rack/`: `counter_slide_cartridge`

#### conditional (4 occurrences) -- FLAG: not in the closed spec

Objects:
- `equipment/cell_counter.yaml` (3 occurrences):
  - `formula: conditional(state(focused), "Focused", "Focusing...")`
  - `formula: conditional(state(cell_count), label(state(cell_count), format="Count: {value}"), "Ready")`
  - `formula: conditional(state(viability_percent), label(state(viability_percent), format="Viability: {value}%"), "Analyzing")`
- `equipment/hemocytometer_slide.yaml` (1 occurrence):
  - `formula: conditional(state(excess_wiped), "Wiped clean", "Excess present")`

The `conditional` token is NOT in the closed formula mini-language defined
in `docs/specs/OBJECT_YAML_FORMAT.md`. That spec lists only: `state(...)`,
`const(...)`, arithmetic operators, `min`, `max`, `clamp`, `fill_height`,
`label`, and `compose`. `conditional` is an extension that exists in
authored content but has no spec backing.

#### compose (0 occurrences)

The `compose(...)` token is in the spec but is not used by any authored
object as of this scan.

### Formula coverage requirement for WS-M2-R

The resolver must implement these tokens to cover the authored corpus:

- `fill_height(state(<field>), capacity_ml=<n>)` -- required
- `fill_height(state(<field>), capacity_ul=<n>)` -- required
- `fill_height(state(<field>), capacity_mg=<n>)` -- required (1 object uses it)
- `label(state(<field>), format="<string>")` -- required
- `conditional(state(<field>), <then-expr>, <else-expr>)` -- required to
  handle existing authored content, but flagged as out-of-spec (see concerns)
- `compose(...)` -- in spec; zero authored uses today; may skip in first pass

---

## Section 2: Scene-operation inventory (content/protocols/**)

### Verification commands

```
grep -rln "LayoutMove" content/protocols/
grep -rn "type: LayoutMove" content/protocols/ | wc -l
grep -rn "type: ObjectStateChange" content/protocols/ | wc -l
grep -rn "type: CursorAttach" content/protocols/ | wc -l
grep -rn "type: SceneChange" content/protocols/ | wc -l
grep -rn "type: TimedWait" content/protocols/ | wc -l
find content/protocols -name "protocol.yaml" | wc -l
```

### Usage counts across 31 protocol files

| scene_operation type | Count | % of all ops |
| -------------------- | ----- | ------------ |
| `ObjectStateChange`  | 333   | 77.8%        |
| `CursorAttach`       | 39    | 9.1%         |
| `SceneChange`        | 34    | 7.9%         |
| `TimedWait`          | 16    | 3.7%         |
| `LayoutMove`         | 0     | 0.0%         |

Total scene operations authored: 422

### LayoutMove finding

`LayoutMove` is used in zero authored protocol files. The word "LayoutMove"
appears only in:
- `docs/specs/` (vocabulary and spec docs)
- `docs/archive/` (design history)
- `src/` (runtime type definitions)
- `pipeline/gen_protocols.py` (enum/constant)
- `tests/` (test stubs)
- `validation/` (schema constants)

No protocol YAML under `content/protocols/` contains a `LayoutMove`
scene operation.

---

## Section 3: Decisions

### (a) Formula coverage scope for WS-M2-R

WS-M2-R must implement `fill_height`, `label`, and `conditional` to cover
the existing authored corpus. `compose` may be deferred to a second pass
since no authored object uses it today. The `capacity_mg` variant of
`fill_height` must be supported (one authored object uses it).

### (b) LayoutMove: Option A vs Option B recommendation

**Recommended: Option A -- mark LayoutMove as unsupported in this pass.**

Rationale:
- Zero authored protocols use `LayoutMove`. There is no concrete authored
  workflow that requires it at launch.
- Implementing Option B (typed resolved placement override) for zero
  existing consumers adds complexity with no immediate return.
- The spec definition of `LayoutMove` is stable (two valid uses: reposition
  within scene, or cross-scene move). When a protocol author first needs it,
  Option B is the correct implementation path -- but that decision belongs
  to the milestone where the first authored consumer appears.
- Option A keeps WS-M3-D focused on the four primitives that do have
  authored consumers (`ObjectStateChange`, `CursorAttach`, `SceneChange`,
  `TimedWait`).

If WS-M4-B (protocol corpus sweep) or a new mini-protocol introduces a
`LayoutMove` use before WS-M3-D ships, this recommendation should be
revisited and Option B implemented.

---

## Concerns

1. `conditional` is not in the closed formula spec but is used by 2 objects
   (4 formula lines). WS-M2-R must implement it to handle authored content,
   but doing so without first ratifying the token in `OBJECT_YAML_FORMAT.md`
   widens the vocabulary surface silently. Recommended action: file a spec
   addition for `conditional(cond, then, else)` before or alongside WS-M2-R.

2. `capacity_mg` in `fill_height` is unusual (volumes measured in milligrams
   suggests a mass-based fill). Only `mtt_powder_container.yaml` uses it.
   The resolver must not assume capacity is always a liquid volume unit.

3. `compose` is in the spec but has zero authored uses. If the resolver
   skips it, tests must cover the deferred-token path explicitly so a future
   author's first `compose` use does not silently fail.

---

## Residual risks

- This scan covers `content/objects/**` and `content/protocols/**` only.
  If smoke protocols under `tests/content/` or future content under a new
  cluster introduce additional formula tokens or `LayoutMove` uses, this
  inventory becomes stale. Re-run the verification commands above after any
  new protocol or object addition.
- The `label` inside `conditional` nesting (2 of the 4 conditional lines)
  means WS-M2-R must handle nested formula expressions, not just flat ones.
