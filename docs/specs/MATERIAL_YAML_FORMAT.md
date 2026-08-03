# Material YAML format

This document is the canonical schema for the `materials.yaml` authoring file:
its top-level shape, the per-material keys, which keys are required, the exact
scalar `display_color` format, the closed-schema rule that rejects unknown keys,
the per-protocol scope of the registry, and whether sentinels appear in the
file. It also fixes the material-openness decision (D1) for how a subpart
`material_name` validates.

This is the schema-only doc. It does not define the closed material terms, the
sentinel/visible classification, the render-effect or target tokens, the color
resolver contract, or the validator and cross-YAML rules. Those live in their
owning docs:

- The closed material terms (material, sentinel, visible material, registry,
  mixture, waste, transfer) and the settled sentinel/visible classification are
  defined in [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).
- The design rationale (why color is a single scalar, why protocol YAML never
  names a color, why empty is transparent) is in
  [MATERIAL_DESIGN.md](MATERIAL_DESIGN.md).
- The runtime render convention (render effects, targets, identity and amount
  layers, fill behavior) is in [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).
- The validator behavior and cross-YAML agreement rules live in
  `MATERIAL_LINT.md`.

Where a term is used below, it is used with the meaning fixed in
[MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).

## File location and scope

A material registry is authored per protocol. Each protocol package owns exactly
one registry file:

```
content/protocols/<cluster>/<protocol_name>/materials.yaml
```

This is one of the closed set of approved authoring files (see
[SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md)). No other path is a valid
material registry, and there is no global materials file. A material name
resolves against the active protocol's registry, not a shared table. Two
protocols that both register `media` each carry their own entry; the entries are
independent and may differ in `label` or `display_color`.

`materials.yaml` is only the protocol material registry. It cannot describe an
asset, SVG layer, paint role, adjustment, runtime handle, liquid region, or SVG
recipe, and it cannot serve as an SVG sidecar. The closed two-key entry schema
below is the entire material-registry surface. A material-rendered SVG keeps its
own self-describing semantic recipe under [SVG_PIPELINE.md](SVG_PIPELINE.md),
so one SVG recipe remains reusable across protocol registries.

## Top-level shape

The file has exactly one top-level key, `materials`, whose value is a mapping.
Each key of that mapping is a material name (the snake_case identifier defined in
[MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)); each value is a material
entry. An empty registry is written as `materials: {}`.

```yaml
materials:
  <material_name>:
    label: "<human display label>"
    display_color: "<scalar hex string>"
```

No other top-level key is allowed. Material names are the registry keys; a
material name is never repeated, because YAML mapping keys are unique.

## Material entry schema

A material entry is a closed schema with exactly two keys, both required, no
optional keys:

| Field           | Required | Type          | Allowed values                                                                 | Meaning                                                                  |
| --------------- | -------- | ------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `label`         | yes      | string        | Non-empty string. ASCII only; non-ASCII glyphs are written as HTML entities.   | Human display label shown to the student (for example `"1x PBS"`).       |
| `display_color` | yes      | string        | A single scalar hex string in the format fixed in "Scalar display_color" below. | The visible material's color; the sole source of that material's color. |

Both keys are required on every entry. There are no optional keys and no defaults:
an entry missing either key, or carrying any third key, fails validation.

There is no material-kind field (no `liquid` / `solid` / `gel` / `powder` enum).
A material kind is not authored until a non-liquid material needs distinct
behavior; adding one is a vocabulary edit, not an author-introduced key.

### Material name (registry key)

The mapping key is the material name. It is a snake_case identifier matching
`^[a-z][a-z0-9_]*$` (lowercase letter first, then lowercase letters, digits, and
underscores). It names a substance or condition, never a color, asset, or volume.
The two sentinels (`empty`, `mixed`) are not registry keys; see "Sentinels do not
appear in materials.yaml" below.

### `label`

`label` is a non-empty human-readable string used as the display name. It is
ASCII-only per [MARKDOWN_STYLE.md](../MARKDOWN_STYLE.md) and the repo ASCII rule;
characters outside ASCII are written as HTML entities (for example `&micro;M
carboplatin`, `&beta;-mercaptoethanol`). `label` is free display text, not an
identifier, and is never used for resolution or matching.

### Scalar display_color

`display_color` is a single scalar hex color string. It is the only color surface
for a material. There is no nested mapping, no `light` / `dark` split, and no
theme branch: the project targets light scientific workspaces only, and the one
scalar color is used everywhere the material renders.

Allowed format:

- A string beginning with `#` followed by exactly six hexadecimal digits
  (`#rrggbb`). The pattern is `^#[0-9a-f]{6}$`.
- Hex digits are lowercase. `#a719db` is valid; `#A719DB` is rejected.
- No shorthand three-digit form (`#abc`), no eight-digit alpha form
  (`#rrggbbaa`), no named colors (`red`), and no `rgb(...)` / `hsl(...)`
  functional syntax.

```yaml
display_color: "#a719db"
```

When an active registry is supplied, a non-`empty`, non-built-in material name
that is missing there or has an invalid color is a resolver failure, not a
silent invisible success. A null registry is instead the bounded
diagnostic/unseeded no-protocol-color-context case and returns `color: null`; it
does not accept the name as registered. Null material fields and the authored
`empty` sentinel are also successful no-color cases. These resolver invariants
are fixed in [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md); this schema's job
is to require the registry field and fix its format.

## Glyph rendering

This is the canonical statement of the author-entity -> codegen-decode ->
DOM-glyph convention. Every other spec that states the ASCII/entity escaping
rule for an authored string (material `label` above, object unit strings and
labels, protocol prompts, descriptions, and feedback) cross-links here rather
than restating it.

- Authors write non-ASCII characters as named or numeric HTML entities in
  committed YAML (for example `&micro;M`, `&alpha;`, `&#181;`). The committed
  source stays ASCII, satisfying the repo-wide rule in
  [../MARKDOWN_STYLE.md](../MARKDOWN_STYLE.md).
- Codegen decodes each entity to its Unicode character at the string-emit
  choke point, so `generated/**` carries the real glyph (for example U+00B5,
  the micro sign) instead of the literal entity text. `generated/**` carries
  no ASCII restriction, so a decoded Unicode character in build output is not
  a violation.
- The runtime renders the decoded string as a plain DOM text node, never
  `innerHTML`. Decoding to a text node keeps the path free of HTML injection
  and entity-expansion risk regardless of which entity was authored.
- Both named entities (`&micro;`, `&alpha;`, `&beta;`, `&mu;`, and similar)
  and numeric entities (`&#181;`, `&#xB5;`) decode. A named entity outside the
  decode map that is not numeric is left verbatim: a visible, safe
  pass-through rather than a silent failure.
- This convention applies to every generated text path that can carry an
  entity: material `label` (this doc), object unit strings and labels, and
  protocol prompts, descriptions, feedback, and learning-hook text.

## Closed schema: unknown keys rejected

The entry schema is closed. The only allowed keys in a material entry are `label`
and `display_color`. Any other key (for example `color`, `colour`, `hex`,
`theme`, `light`, `dark`, `kind`, `metadata`, `notes`, `description`) is a
validation error. The only allowed top-level key is `materials`. Authors cannot
expand the material vocabulary by adding a key; new meaning requires a vocabulary
edit, per the schema-escape-hatch rule in
[SPEC_DESIGN_CHECKLIST.md](SPEC_DESIGN_CHECKLIST.md).

## Sentinels do not appear in materials.yaml

The two sentinels are exempt from registration and must not be authored as
registry entries:

- `empty` is the non-rendering sentinel; it carries no color and is never an
  entry. A container holding `empty` (or `material_volume: 0`) renders no fill.
- `mixed` is the one built-in visible material; its color is a spec-defined
  built-in (owned by [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md)), not an
  authored entry. Writing a `mixed` entry into `materials.yaml` is a validation
  error.

Every other material name a protocol writes into a `material_name` /
`held_material_name` field is a registry-backed visible material and must appear
as an entry in that protocol's `materials.yaml`. The settled per-name
classification table is in [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).

## D1: material-name openness decision

The decision (D1): a structured-container subpart `material_name` (and any
`material_name` / `held_material_name`) validates by **registry-backed
membership**, not against a single global closed enum. The accepted value set is
the union of the closed sentinel allowlist and the active protocol's registry
keys.

### Validation predicate

For a written material-name value `m` under active protocol `P`:

```
valid(m, P)  ==  m in {empty, mixed}            # closed sentinel allowlist
              OR m in registry_keys(P)          # keys of P's materials.yaml `materials` map
```

- `registry_keys(P)` is the set of top-level keys under `materials:` in
  `content/protocols/<cluster>/<P>/materials.yaml`.
- The sentinel allowlist `{empty, mixed}` is the closed set fixed in
  [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md); it is not extended here.
- Any `m` that satisfies neither clause is an unregistered-material error (the
  stepper's `s-unregistered` gate; see `MATERIAL_LINT.md`).

### Why registry-backed, not a closed enum

- A shared structured object such as `well_plate_96` must not enumerate every
  drug, buffer, or assay product any protocol might place in a well. A closed
  enum on the object would force an object edit for every new curriculum
  treatment, recoupling the object layer to protocol content and breaking the
  closed-by-id object rule (objects do not change identity to host new content).
- The registry-backed model keeps the curriculum's treatments where they belong:
  each protocol registers the materials it uses in its own `materials.yaml`, and
  the shared object validates membership dynamically against that per-protocol
  registry plus the two sentinels.
- The set is still closed per protocol: each registry entry is a closed-schema
  entry, and an author cannot invent a material name by writing it into protocol
  YAML alone -- the name must also be registered (or be a sentinel), or the
  `s-unregistered` gate rejects it. Openness is bounded registration, not a
  free-form string.

### Handoff to stepper and YAML

- The Python stepper (WP-STEPPER) implements `valid(m, P)` exactly as the
  predicate above: sentinel-or-registry membership, evaluated against the active
  protocol's loaded registry.
- The shared `well_plate_96` object (WP-YAML) needs no per-subpart enum of
  material names; its subpart `material_name` field is validated by the predicate
  above, not by an object-declared value list.

## Examples

Every key shown below appears in the entry schema table above; the examples
illustrate the schema and do not extend it.

Minimal single-entry registry:

```yaml
materials:
  pbs:
    label: "1x PBS"
    display_color: "#076dad"
```

Multiple entries, including a condition pair and a tracked mixture (each
condition and each mixture is its own material name with its own scalar color):

```yaml
materials:
  media:
    label: "Growth media"
    display_color: "#6c6c00"
  spent_media:
    label: "Spent media"
    display_color: "#935d00"
  carboplatin:
    label: "Carboplatin solution"
    display_color: "#a719db"
  metformin:
    label: "Metformin solution"
    display_color: "#00775f"
  carboplatin_metformin_combo:
    label: "Carboplatin and metformin mixture"
    display_color: "#b84db8"
```

A label carrying a non-ASCII glyph, written as an HTML entity:

```yaml
materials:
  carboplatin_4umol:
    label: "4 &micro;M carboplatin"
    display_color: "#a719db"
```

An empty registry (a protocol that writes only sentinels):

```yaml
materials: {}
```

The sentinels `empty` and `mixed` never appear as entries in any example above,
because they are not registered.

## What this doc does not own

- The closed sentinel allowlist and the per-name visible/sentinel classification:
  [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).
- The `mixed` built-in color value: [MATERIAL_VOCABULARY.md](MATERIAL_VOCABULARY.md).
- Render effects, targets, identity/amount layers, and fill behavior:
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md).
- The color resolver's typed contract and degrade path:
  [MATERIAL_CONVENTION.md](MATERIAL_CONVENTION.md) and `MATERIAL_LINT.md`.
- The `s-unregistered` gate behavior and cross-YAML agreement rules:
  `MATERIAL_LINT.md`.
- Object-side `state_fields`, `subpart_state_fields`, and `visual_states`:
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- Material-rendered SVG semantic layers and generated runtime handles:
  [SVG_PIPELINE.md](SVG_PIPELINE.md).
- Protocol-side `ObjectStateChange` that writes a `material_name`:
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
