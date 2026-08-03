# Decision: SVG Asset Taxonomy and Organization

## Status

Amended by user decision after WP-R1. The semantic two-axis model remains
accepted, but the earlier decision to keep 117 SVG sources in one flat directory
is superseded. Physical organization is approved and deliberately sequenced
after the true variable-volume asset conversion is complete.

## Decision

Adopt two independent axes:

| Axis | Values | Authority |
| --- | --- | --- |
| Selection model | `single`, `discrete_collection` | Object YAML `visual_states` SVG case maps |
| Rendering model, per form | `static`, `material_rendered` | The selected SVG form's normalized root semantic declaration |

A collection is not an SVG artifact and receives no duplicate collection manifest.
It is the set of complete `asset_name` outputs selected by an object's `kind: svg`
visual-state declarations. A rendering model is not inferred from a collection, a
filename, an asset directory, a material name, or literal fills.

`materials.yaml` continues to be the protocol material registry and color source.
Object `visual_states` continues to bind material identity/amount to object behavior.
Only a material-rendered SVG internally describes the semantic material layers that
the runtime may recolor and transform.

## Consequences

- Static assets retain one ordinary SVG form and the current ordinary normalization
  policy.
- Discrete-state assets select complete SVG forms. `power_supply_off.svg` and
  `power_supply_on.svg` remain static forms; the numeric display remains a text
  overlay, not a general mutable-SVG feature.
- A discrete collection may contain both static and material-rendered forms. The
  rendering declaration belongs to the individual form, so a mixed collection is
  unambiguous and requires no special collection type.
- No external SVG-layer recipe or sidecar is introduced.
- The current material-effect reachability is a migration inventory only. It is not
  a statement that the current flat artwork already satisfies the new contract.

## Organization decision

Replace the flat source directory with behavior-oriented subdirectories after the
true variable-volume assets are complete:

| Directory | Meaning |
| --- | --- |
| `assets/equipment/static/` | One opaque complete form with no current multi-form selection or mutable internal rendering |
| `assets/equipment/binary_state/` | Opaque complete forms selected from a two-form object state |
| `assets/equipment/multi_state/` | Opaque complete forms selected from a state with more than two complete SVG outputs |
| `assets/equipment/variable_volume/` | A semantic SVG whose authored liquid amount and color are changed continuously at runtime |

These are the evidenced initial categories, not a claim that four categories can
describe every future behavior. A later genuinely distinct capability, such as
in-SVG structured subpart mutation, adds a named category only after its rendering
contract is ratified. Hybrid behavior must be represented deliberately by an
explicit taxonomy extension; it must not be hidden in `static/` or guessed from a
filename.

Directory placement is an enforced projection of the two authoritative behavior
sources: object YAML owns complete-form selection, and each SVG root owns internal
rendering capability. It does not replace either source. A validation gate derives
the expected category and rejects a misplaced file.

Before moving sources, implement one recursive asset registry with globally unique,
stable logical `asset_name` keys. Migrate every flat-path consumer listed in the
audit to that registry, preserve provenance lookup and public URL behavior through
the generated manifest, and only then move files. Object and protocol YAML continue
to use logical names, not source-directory paths. This is the durable design that
allows later directory changes without another YAML migration.

The sequencing is binding: finish and accept the five true variable-volume families
first, then implement the registry and physical move as one green migration. This
keeps an asset from moving twice while its semantic artwork is still under review.

## Filename rule

Every new or renamed SVG uses a descriptive lowercase snake_case stem. A form that
represents a selected state includes its asset/family identity and state, for example
`power_supply_off.svg`, `centrifuge_lid_open.svg`, or
`microtube_1_5ml_closed.svg`. Bare state filenames such as `open.svg`, `closed.svg`,
`on.svg`, and `off.svg` are invalid. Add capacity/size only where it distinguishes a
form. Do not add a `material_rendered` suffix solely to repeat metadata that the SVG
itself declares.

Existing `_new`, `_v2`, `_v3`, `_v4`, `_v5`, and `_servier` names are legacy/import
debt; their meaning must not be inferred as a state or rendering declaration.

Filename text never classifies asset intent. In particular, `_empty` and `_full`
are not globally prohibited: `mtt_powder_vial_empty.svg` and
`sharps_container_full.svg` remain valid ordinary complete forms because they depict
genuine content states. The prohibited fan-out occurs only when paired material
identity/amount `visual_states` use runtime material rendering and select distinct
files solely for material color or liquid level; then every case selects the same
complete form.

## Ratified semantic-contract clarification

The taxonomy does not require `data-vlab-stacking-phase`. SVG document order is the
single stacking authority and the normalized validator derives the fixed-back,
material-middle, fixed-front band from that order. Therefore omit the attribute from
the initial closed vocabulary; retaining it would create two sources of truth.

`data-vlab-layer-name` is required and unique within one SVG form. It is the authored
semantic identity from which opaque runtime handles are derived. `data-vlab-paint-role`
may repeat across distinct material groups: several highlights or shadows are valid.
At least one `base` group is required; the vocabulary should not impose an arbitrary
single-base restriction unless a later renderer requirement proves it necessary.

The initial ratified root/group vocabulary is consequently:

- root: `data-vlab-rendering="material"`;
- required per semantic group: `data-vlab-layer-name`, `data-vlab-layer-kind`;
- required for a material group: `data-vlab-paint-role`;
- optional only for supported non-base material groups: `data-vlab-adjustment`.

The normalizer must preserve or canonicalize this reserved vocabulary deliberately,
preserve semantic group and child order, reject cross-boundary merges, and validate
normalized output before generated-manifest compilation. Runtime IDs remain derived;
authored layer names are never DOM IDs.

## Verification

The audit command found 117 source SVG forms, 18 YAML-derived collections, 39
collection forms, 78 referenced source forms, and 27 legacy material-effect candidate
forms. `staining_tray` is the sole collection with a legacy material effect; it is the
required regression case for per-form rendering classification.
