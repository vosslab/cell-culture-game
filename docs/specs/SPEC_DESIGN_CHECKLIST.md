# Spec smell checklist -- anti-drift sweep brief

This is the brief for the independent sweep agent that audits canonical
spec docs for underspecified concepts and junk-drawer escape hatches.

## Core detector

Identify every place where the spec allows authors to invent new meaning
without editing the vocabulary itself.

The strongest pattern across prior reviews was not "wrong implementation"
but "underspecified escape hatches." The agent hunts for any concept that
silently expands the vocabulary surface.

## Author YAML vocabulary lock

This section is the canonical lock for authored YAML vocabulary. Subsequent
sweeps and spec edits obey these rules.

### Ratified rules

1. `short_label` retired everywhere. No identity row, no override surface, no fallback prose, no example.
2. Scene placement may not override `label`. `label` is object-owned and required. If a scene needs a different name, declare a new object with a different `object_name`.
3. `element_id` retired from authored YAML completely. Scene YAML does not declare `element_id`. Runtime derives the mount element from `scene_name`. Any current-code exceptions are adapter/runtime migration issues, not authoring schema fields.
4. `liquid_color` retired as an authored state field. Color derives from `material_name` via the object's `visual_states`, sourced from `materials.yaml`.
5. `liquid_container` capability renamed to `material_container` everywhere.
6. `render_map` retired. Closed-enum `visual_states` is the only state-to-visual surface.
7. Retired-term tables and retired-term mentions do not live inside any spec doc. Retired terms appear only in `docs/CHANGELOG.md`, archived plans, and git history.
8. Authored YAML identity handles are scope-specific. Bare `name:` is not allowed as an authored YAML field or as a schema-table field name. Use the scope-specific handle in every authored YAML schema, example, and field-row label:
   - Protocol handle is `protocol_name`.
   - Step handle is `step_name`.
   - Object identity handle is `object_name` (instruments included; the object is the instrument).
   - Object state-field handle is `field_name`.
     Ordinary prose may still use the English word "name"; the ban is only on YAML fields and schema field-name cells. `entry_step` and `next_step` reference a `step_name` value. Any "the name of X" schema wording becomes "the `X_name`" when X is a YAML handle.

### Object identity

Identity is the locked tuple `object_name`, `kind`, `label`.

- `object_name`: required, snake_case, stable across scenes.
- `kind`: required, closed enum.
- `label`: required, object-owned.

### Scene placement override surface

Scene placement may set layout hints only: `default_width`, `label_width`, `anchor_y_offset`, `width_scale`, `anchor_y`. Scene placement may not override identity (`object_name`, `kind`, `label`), `state_fields`, `visual_states`, or `capabilities`.

### YAML naming

All authored YAML fields are snake_case. TypeScript runtime identifiers may stay camelCase; spec docs describing authored YAML must use snake_case.

Valid: `object_name: ethanol_bottle`. Invalid: `objectName: ethanol_bottle`.

### Source of authority

This lock is sourced from `../CHANGELOG.md` entry 2026-05-15, "vocabulary audit sweep: retired-terms inventory and spec-consistency gates - WP-F1".

## Scope

Sweep tier 1 (highest priority -- canonical vocabulary and schema):

- `../PRIMARY_CONTRACT.md`
- `../PRIMARY_DESIGN.md`
- `../PRIMARY_SPEC.md`
- `PROTOCOL_VOCABULARY.md`
- `PROTOCOL_YAML_FORMAT.md`
- `PROTOCOL_STEPS.md`
- `PROTOCOL_AUTHORING_GUIDE.md`
- `SCENE_VOCABULARY.md`
- `SCENE_YAML_FORMAT.md`
- `SCENE_ARCHITECTURE.md`
- `OBJECT_VOCABULARY.md`
- `OBJECT_YAML_FORMAT.md`

Sweep tier 2 (supporting subsystems with their own vocabulary):

- `LAYOUT_ENGINE.md`
- `MATERIAL_CONVENTION.md`
- `SVG_PIPELINE.md`
- `SCALING_MODEL.md`
- `WALKTHROUGH_GUIDE.md`
- `../THIRD_PARTY_ASSETS.md`

Sweep tier 3 (architecture and structure -- lower vocabulary risk, higher
shadow-term risk):

- `../CODE_ARCHITECTURE.md`
- `../FILE_STRUCTURE.md`
- `TARGET_FILE_STRUCTURE.md`

Sweep tier 4 (external-format docs -- check for schema escape hatches and
shadow vocabularies that bleed into authoring):

- `QTI_v3_SPEC.md`

Exclude entirely (not vocabulary docs):

- `docs/CHANGELOG.md`, `docs/CHANGELOG-*.md` (chronological log).
- `docs/ROADMAP.md`, `docs/TODO.md` (intent, not authoring rule).
- `docs/INSTALL.md`, `docs/USAGE.md`, `docs/AUTHORS.md` (operational).
- `docs/REPO_STYLE.md`, `docs/PYTHON_STYLE.md`, `docs/PYTEST_STYLE.md`,
  `docs/TYPESCRIPT_STYLE.md`, `docs/MARKDOWN_STYLE.md`,
  `docs/E2E_TESTS.md`, `docs/PLAYWRIGHT_USAGE.md`,
  `docs/CLAUDE_HOOK_USAGE_GUIDE.md` (style/process, not authoring vocab).
- `docs/Miraculin_Protocol_2026.md`, `docs/SDS-PAGE_Protocol_2026.md`,
  `docs/OVCAR8_*.md`, `docs/VOSS_DILUTIONS_GUIDE.md` (specific protocol
  content, not vocabulary).
- `docs/active_plans/*_inventory.md` (counts belong there).
- `docs/active_plans/*` general (active design surface, not canonical).
- `docs/archive/*` (historical).

## Severity labels

Tag every finding:

- `blocker` -- permits uncontrolled vocabulary growth.
- `warning` -- ambiguous but bounded.
- `note` -- wording or aging risk.

## Section-context tag

Every finding also carries a section-context tag:

- `target-state` -- canonical authoring rule. Findings here describe
  required behavior.
- `current-code` -- descriptive prose of what exists today; flag but
  ensure the wording does not silently bleed into canonical vocab.
- `migration/history` -- transitional or archive context. Flag only if
  the wording risks bleeding back into canonical vocab.

False-positive rule: words like `metadata`, `config`, `properties` may
legitimately appear in current-code or migration/history sections. Flag
anyway, but tag the context so the human can triage by impact.

## Sweep targets and rules

### 0. Schema escape hatch (top category)

The unifying smell. Any field that lets authors invent new structure,
meaning, or behavior without a vocabulary edit.

Includes:

- Open-key objects (`additionalProperties: true`).
- "Pass-through" fields forwarded to runtime without schema.
- Author-defined keys inside a "metadata" or "extras" container.
- Inline expression or formula text evaluated by the runtime.
- Type unions that accept "or any object".
- "Plugin" / "module" / "adapter" registration shapes that accept
  arbitrary author payloads.

Rule:

- Authors must NOT be able to expand the vocabulary surface by editing
  YAML alone. New meaning requires a vocabulary edit.
- Default severity for this category: `blocker`.

### 1. Open-ended primitive types

Flag: `string`, `any`, free-form maps, arbitrary nested objects, JSON
blobs, unnamed dictionaries, `metadata`, `properties`, `attributes`,
`config`.

Rule:

- If values come from a known set, use `enum`.
- If structure matters, define fields explicitly.
- Unknown keys must fail validation.

### 2. Junk-drawer nouns

Flag vague containers: `capabilities`, `constraints`, `settings`,
`options`, `flags`, `extras`, `custom`, `extensions`, `annotations`,
`data`, `params`.

Rule:

- Every container must have a closed schema.

### 3. Arbitrary nesting

Flag: nested state writes, recursive structures, object trees without
depth limits, polymorphic payloads.

Rule:

- Prefer flat primitives.
- Composition through multiple named fields, not nested blobs.

### 4. Hidden semantic leakage (cross-layer)

Flag lower layers learning higher-layer meaning:

- Protocol naming SVG assets.
- Scene defining object behavior.
- Object defining protocol sequencing.
- Layout engine interpreting learning semantics.

Rule:

- Protocol = intent.
- Object = representation / state.
- Scene = placement / layout.

### 5. Future-proofing language that bypasses design

Flag dangerous phrases: "arbitrary", "custom", "user-defined",
"free-form", "extensible", "etc.", "other fields", "additional
properties", "plugin-defined".

Rule:

- Force explicit extension points.
- Unknown extension points become future RFCs, not implicit support.

### 6. Fixed-count assumptions

Flag: "7 scenes", "45 assets", "8 operations", any literal count in
canonical-doc prose.

Rule:

- Canonical docs describe structure, not inventory snapshots.
- Counts belong only in inventory artifacts or audits.

### 7. Shadow vocabularies

Flag the same concept named differently across docs:

- `object_ref` vs `object_name`
- `slot` vs `subpart`
- `state_map` vs `visual_states`
- `item` vs `placement`
- `kind` vs `type` vs `category`

Rule:

- One canonical term per concept.
- Synonyms retired explicitly with pointer.

### 8. Layer ownership ambiguity

For every field, ask:

- Who owns this?
- Who mutates this?
- Who renders this?
- Who validates this?

If multiple answers appear, the boundary is drifting. Flag.

### 9. Validation gaps

Flag fields missing any of: type, allowed values/range, default
semantics, validation behavior, type coercion, units.

Rule:

- Every authored field must define type, allowed values/range, default
  semantics, validation behavior.

### 10. Render-mechanism leakage

Flag:

- SVG asset names in protocol examples.
- Renderer implementation details in object docs.
- Animation semantics in scene placement docs.

Rule:

- Specs describe meaning, not renderer internals.

### 11. Accidental mini-programming languages

Flag high-risk areas: formula syntax, conditional rendering, expression
evaluators, templating, embedded logic.

Rule:

- Closed token sets only.
- No prose-driven interpretation.
- Unknown tokens = build error.

### 12. Transitional wording that never dies

Flag: "for now", "temporary", "currently", "legacy", "eventually".

Rule:

- Transitional states belong in migration docs, not canonical vocab docs.

### 13. Negative fossil (retired-term hygiene)

Flag retired-term lists that include design-process scratch terms (terms
that were brainstormed but never shipped) instead of shipped terms only.

Rule:

- Retired-term lists name SHIPPED terms only -- terms that appeared in
  prior canonical docs, code, or YAML files.
- Scratch terms from design discussion belong in the design doc's
  "rejected alternatives" section, not the retired-terms list.
- Rationale: a retired-term list teaches readers what to stop using;
  including never-shipped terms confuses readers about what was real.

### 14. Overpowered setter

Flag setter primitives (e.g., `ObjectStateChange`) that can write
multiple unrelated fields without a schema rule, accept arbitrary
nested writes, or target undeclared fields.

Rule:

- Setter primitives may only write declared fields.
- Values must match the declared primitive type and metadata.
- Multi-field writes must be explicitly allowed by that primitive's
  spec, with the allowed shape declared.
- Validator rejects unknown fields and type-mismatched values.

### 15. Example becomes spec

Flag examples that introduce fields not defined in the schema tables.

Rule:

- Every field shown in an example must appear in a schema table earlier
  in the same doc (or in a linked schema doc).
- If an example needs a new field, add the field to the schema first.
- Examples illustrate the schema; they do not extend it.

### 16. Primitive names appearance instead of semantic state

Flag protocol-level primitives whose name describes a visual outcome
(Display, Show, Render, Color, Swap, Animate, Highlight, Move-pixels)
instead of a state change. Ask: does this primitive change semantic
simulation state, or does it merely describe how that state appears?
If it merely describes appearance, move it to object/render.

Detector keywords in primitive names: `Display`, `Show`, `Render`,
`Color`, `Swap`, `Animate`, `Highlight`, `Move-pixels`, `Visual`,
`Paint`. Detector phrases in primitive reason text: "show a
spinner", "draw under cursor", "render a progress bar", "tint",
"fill height", "asset swap", "display result".

Rule:

- Before adding any new protocol-level primitive, test whether it changes
  semantic simulation state or merely describes appearance.
- Protocol primitives change semantic simulation state -- what the
  simulation IS (declared state, held material, active scene,
  placement, equipment timed phase).
- Object/render layer mechanisms describe how the state appears -- how
  the simulation LOOKS (asset id, color, fill height, tint, numeric
  overlay, spinner, progress bar, cursor-follow visual).
- A primitive whose name or one-line meaning describes appearance is
  not a protocol primitive; it is a render-layer mechanism.
- Default severity for this category: `blocker` in canonical vocabulary
  docs.

### 17. Copy-paste scene example becomes the canonical form

Flag: scene examples in docs that look like full copies of base or previous
protocol scenes, used as "starter templates" for new scenes, without explicit
`extends:` declarations.

Rule:

- Scene examples must show inheritance syntax (`extends:`, `add_placements`,
  `reposition_placements`, `deactivate_placements`, `remove_placements`) to
  prevent author copy-paste duplication and silent forking.
- When a scene should reuse another scene's workspace, the inheriting scene
  must declare `extends:` and only the four named operations.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the full rule.
- Default severity: `high`.

### 18. Scene inheritance chain longer than one level

Flag: scenes where the inheritance graph is not strictly one level.

Rule:

- Base scenes (`content/base_scenes/*.yaml`) must extend nothing.
- Protocol scenes (`content/protocols/<cluster>/<name>/scenes/*.yaml`) must extend
  exactly one base scene.
- No scene may extend a protocol scene.
- No scene may extend a scene that already extends another scene.
- Cycles and multi-level chains are build errors.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the full rule.
- Default severity: `high`.

### 19. Scene introduces a fifth mutation operation or a generic overrides block

Flag: protocol scene files that define mutation operations beyond the four
canonical named operations, or that include generic escape-hatch blocks
like `overrides:`, `patch:`, or `metadata:`.

Rule:

- Scene inheritance has exactly four named mutation operations:
  `add_placements`, `reposition_placements`, `deactivate_placements`,
  `remove_placements`.
- There is no `overrides:` block, no `patch:` block, no generic `metadata`
  that carries inherited-field mutations.
- New operations require a ratified spec edit.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the full rule.
- Default severity: `high`.

### 20. Scene operation targets a locked field

Flag: scene mutation operations that attempt to change locked fields.

Rule:

- Mutation operations may not change fields locked by the base scene
  (workspace, background, bounds, zones, layout_rules, capabilities,
  object identity, state_fields, visual_states).
- `reposition_placements` may change only: `zone`, `position`, `depth`,
  `anchor`.
- `add_placements` may declare only placement fields; not object identity,
  state, label, capabilities, or render fields.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the complete field
  inheritance table.
- Default severity: `high`.

### 21. Base placement missing placement_name

Flag: placements in a base scene that do not declare a `placement_name`.

Rule:

- Every placement in a base scene must carry a stable `placement_name`.
- The `placement_name` is the canonical selector for all mutation operations
  (`reposition_placements`, `deactivate_placements`, `remove_placements`).
- Selection by `object_name` is rejected because a base scene may carry several
  placements of the same object.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) for the full rule.
- Default severity: `high`.

### 22. Object schema introduces an extends field

Flag: `OBJECT_VOCABULARY.md` or `OBJECT_YAML_FORMAT.md` text that permits
objects to declare an `extends:` field or to inherit from template objects.

Rule:

- Objects are canonical-by-id with no `extends` and no template-object layer.
- If an object differs meaningfully from an existing one, mint a new id.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) asymmetry rationale and
  [OBJECT_VOCABULARY.md](OBJECT_VOCABULARY.md).
- Default severity: `high`.

### 23. Protocol schema introduces an extends field

Flag: `PROTOCOL_VOCABULARY.md` or `PROTOCOL_YAML_FORMAT.md` text that permits
protocols to declare an `extends:` field or to inherit from template protocols.

Rule:

- Protocols are spec-shaped with no template-protocol layer.
- Similarity comes from the shared `learning -> steps -> sequence ->
interaction -> response` structure, not from templates.
- Cross-protocol reuse is via `sequence_runner` composition.
- See [SCENE_INHERITANCE.md](SCENE_INHERITANCE.md) asymmetry rationale and
  [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md).
- Default severity: `high`.

### 24. Author YAML names semantic things; runtime derives DOM handles and visual colors

Flag: any YAML vocabulary doc that names runtime-derived values (DOM mount
points, computed visual colors, internal renderer state) as if they were
author vocabulary.

Rule:

- Authors name semantic things in YAML: scene names, object names, placement
  names, target names, step names, interaction sequences, material names.
- The runtime derives implementation details from author-named semantic values.
  Examples: `${scene_name}-scene` mount elements (not authored), palette
  colors computed from `visual_states` (not authored).
- Specs must not surface derived values as authoring vocabulary.
- YAML vocabulary remains clean and semantic; derivation is a runtime concern.
- Default severity: `blocker`.

### 25. Author-facing YAML handles use `_name`; `_id` does not appear in author YAML

Flag: any author-facing YAML field named with `_id` suffix (e.g.,
`object_id`, `scene_id`, `placement_id`, `step_id`, etc.).

Rule:

- Author-facing YAML uses `_name` suffixes to name semantic entities:
  `object_name`, `scene_name`, `placement_name`, `target_name`, `step_name`,
  `part_name`, `day_name`, `asset_name`, `overlay_name`, `material_name`,
  `held_material_name`, `zone_name`.
- `_id` does not appear in author-facing YAML vocabulary. The runtime may
  use `_id` internally for deduplication, indexing, or DOM binding; that is
  a runtime implementation detail.
- Field renames from `_id` to `_name` are canonical vocabulary migrations,
  not optional aliases. Old `_id` fields are retired terms.
- Default severity: `blocker`.

### 26. Objects declare closed `visual_states`; no generic rendering map or expression surface

Flag: any OBJECT_VOCABULARY.md or OBJECT_YAML_FORMAT.md text that permits
objects to declare a generic rendering map, render-expression language,
templating surface, or free-form visual-configuration escape hatch
(including fields named `render_map`, `render_config`, `appearance`,
`style_map`, `expression`, `template`, `metadata`, or similar).

Rule:

- Objects declare closed named `visual_states`, each with a fixed visual
  configuration.
- `visual_states` is a closed enumeration, not a template or rule engine.
  Authors select from the declared set; unknown state names are a build error.
- Objects do NOT expose a generic rendering map, expression evaluator,
  templating surface, or free-form visual configuration.
- Asset names appear only inside `visual_states` declarations (not at the
  object top level or in behavior fields).
- Default severity: `blocker`.

### 27. Layer ownership: object YAML names assets only inside visual_states; scene YAML names objects and placements; protocol YAML stays semantic

Flag: any cross-layer leakage of naming responsibility.

Rule:

- Object YAML declares an object's identity, state fields, capabilities, and
  closed `visual_states`. Asset names appear only inside `visual_states`.
- Scene YAML names objects and placements, declares placement positions and
  layout operations, and defines scene-level layout and zones.
- Protocol YAML names targets, steps, interactions, parts, days, and scenes.
  Protocol YAML does not name assets (no SVG references), does not name
  visual configurations or render mechanics, and does not declare scene
  structure.
- This layering ensures no YAML layer tries to invent meaning at a lower
  layer and no lower layer exposes implementation details upward.
- Default severity: `blocker`.

### 28. Authoring surfaces are closed

Flag: any spec or example that introduces an authoring file outside the
approved layout.

Allowed authoring files:

- `content/objects/<object_name>.yaml`
- `content/base_scenes/<scene_name>.yaml`
- `content/protocols/<cluster>/<protocol_name>/protocol.yaml`
- `content/protocols/<cluster>/<protocol_name>/materials.yaml`
- `content/protocols/<cluster>/<protocol_name>/scenes/<scene_name>.yaml`

Rule:

- No other authoring files are valid unless the vocabulary is edited first.
- A new authoring file kind requires a ratified spec edit, not an ad-hoc
  introduction in an example or migration note.
- Default severity: `blocker`.

### 29. Bare `name:` is banned in authored YAML

Extends rule 25 (author-facing YAML handles use `_name`, not `_id`) by
banning the scope-ambiguous bare `name:`. Locked in ratified rule 8.

Flag: any authored YAML schema row, YAML fenced-block field key, or
schema-table field-name cell that uses bare `name:` instead of the
scope-specific handle.

Rule:

- Bare `name:` is not a valid authored YAML field. Use the scope-specific
  handle in every authored YAML schema, example, and field-row label:
  - Protocol handle is `protocol_name`.
  - Step handle is `step_name`.
  - Object identity handle is `object_name` (instruments included).
  - Object state-field handle is `field_name`.
- `entry_step` and `next_step` reference a `step_name` value; their prose
  must say so.
- Any "the name of X" schema wording becomes "the `X_name`" when X is a
  YAML handle.
- Ordinary prose may still use the English word "name"; the ban is only
  on YAML fields and schema field-name cells.
- Default severity: `blocker`.

### 30. Material-rendered SVGs have one semantic authority

Flag: a material SVG sidecar or recipe YAML; a collection manifest duplicating
object `visual_states` SVG case maps; a directory or filename used as rendering
authority; a material binding used to decide whether root-declared material SVG
normalization runs; an authored runtime DOM id or CSS paint handle; an authored
stacking phase; an open `data-vlab-*` field/value map; or runtime code querying
authored `data-vlab-*` or constructing DOM IDs from authored names.

Rule:

- Selection authority is object YAML `visual_states` `kind: svg` case maps.
  A discrete collection is only the set of complete selected forms; it has no
  duplicate manifest.
- Per-form rendering authority is only the validated root
  `data-vlab-rendering="material"`. Every declared material SVG is normalized
  and validated even if it is unreferenced; an object material binding gates
  runtime mutation only.
- After selection, exact root `data-vlab-rendering="material"` selects the
  compiled material-layer path; its absence identifies a static opaque form.
  Invalid or misplaced reserved attributes fail. Object-level `fill_height`
  uses generated manifest handles: identity recolors semantic groups by role and
  volume/capacity applies the compiler-derived gravity-part operations (fixed
  bottom, Y-scaled body, translated fixed-shape surface, stationary reveal).
  It creates no runtime rect and never queries/mutates anchors or authored
  `data-vlab-*`. `anchor_liquid_bounds`, `anchor_liquid_clip`, and existing
  capacity fields remain compiler inputs for material forms; no new YAML target
  or binding token is introduced. Structured subpart material rendering remains
  the separate generated-geometry mechanism. A declared unbound material form
  is still compiled/validated and shows authored fallback paint without state
  mutation.
- `data-vlab-rendering` is valid only on the root `<svg>` and only with exact
  value `material`. The root may also declare the optional closed geometry
  ceiling `data-vlab-max-fill-percent`, an integer from 1 through 100. Requests
  above that ceiling render exactly at it. The root may also declare
  `data-vlab-min-fill-percent`, an integer from 1 through 99: zero remains
  empty, while nonzero requests below it render at that floor, which cannot
  exceed the optional ceiling. A conical form may instead declare
  `data-vlab-body-start-fill-percent`, a finite decimal strictly between 0 and
  100, to map that volume percentage to its measured body anchor. Any reserved `data-vlab-*` attribute
  in an SVG without the rendering declaration fails rather than taking the
  ordinary path. In a material SVG, every remaining reserved attribute is valid
  only on direct root-child semantic groups; unknown, misplaced, and
  role-incompatible attributes fail.
- The material SVG is self-describing. It owns its closed semantic layer recipe,
  geometry, document order, clip anchors, and literal fallback paint. There is
  no sidecar. `materials.yaml` owns material color and object YAML owns binding.
- The only initial semantic vocabulary is root
  `data-vlab-rendering="material"`, optional root
  `data-vlab-max-fill-percent`, `data-vlab-min-fill-percent`, `data-vlab-body-start-fill-percent`, or
  `data-vlab-fill-height-exponent` (finite decimal in `(0, 10]`, mutually
  exclusive with body-start), then direct root-child semantic `<g>` groups
  with unique snake_case `data-vlab-layer-name`,
  `data-vlab-layer-kind` (`fixed` or `material`), and, for material groups,
  `data-vlab-paint-role` (`base`, `highlight`, `shadow`). Roles may repeat and
  at least one `base` is required. `data-vlab-adjustment` is required for
  highlights and shadows, forbidden otherwise, and uses only
  `-?[0-9]+(?:\.[0-9]+)?`: highlight is `0 < value <= 0.5`; shadow is
  `-0.5 <= value < 0`. Unknown fields and values fail validation.
- SVG document order is the only stacking authority. Material groups are one
  nonempty contiguous band; fixed groups before/after derive back/front. No
  authored stacking metadata is permitted.
- A semantic material-layer `<g>` must not carry `clip-path`.
  `anchor_liquid_clip` stays in `defs` and the compiler applies it to the
  derived level group; ordinary child artwork follows ordinary supported clip
  rules.
- `base` paint is the resolved `display_color` unchanged. Highlight and shadow
  apply their adjustment as an additive normalized-OKLCH-lightness delta,
  preserve hue, reduce chroma only for sRGB gamut, and serialize lowercase
  `#rrggbb`; no per-asset color source is allowed.
- `id` is only for unique structural anchors; `class` is styling only. Runtime
  handles and generated paint properties are opaque derived data, never source
  SVG authoring.
- One material-aware policy in the shared normalizer must preserve/canonicalize
  the vocabulary and semantic boundaries, validate normalized and sanitized
  output, generate the manifest, and be byte-stable. Runtime uses only that
  manifest and the injection seam. No `<symbol>` / `<use>` support or general
  animated-SVG mechanism is implied.
- Any new carrier, semantic field, paint role, or extension requires a
  specification edit and user approval.

Default severity: `blocker`.

## Smell-class quick reference

| Class                                                                                                            | Detector keyword set                                                                                                                                                                   | Rule                                                                                                                                                         |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Schema escape hatch                                                                                              | open-key objects, pass-through, plugin payloads                                                                                                                                        | vocabulary edit required for new meaning                                                                                                                     |
| Open type                                                                                                        | `string`, `any`, free-form                                                                                                                                                             | enum or explicit fields                                                                                                                                      |
| Junk noun                                                                                                        | `metadata`, `extras`, `custom`, `params`                                                                                                                                               | closed schema                                                                                                                                                |
| Nesting                                                                                                          | nested writes, recursion                                                                                                                                                               | flat primitives                                                                                                                                              |
| Layer leak                                                                                                       | render in protocol, layout in object                                                                                                                                                   | strict three-layer ownership                                                                                                                                 |
| Future-proofing                                                                                                  | `arbitrary`, `extensible`, `etc.`                                                                                                                                                      | explicit RFC instead                                                                                                                                         |
| Fixed count                                                                                                      | numerals in prose                                                                                                                                                                      | inventory artifact only                                                                                                                                      |
| Shadow term                                                                                                      | two names, one concept                                                                                                                                                                 | retire one                                                                                                                                                   |
| Ownership                                                                                                        | "who owns / mutates / renders / validates" answers diverge                                                                                                                             | single owner                                                                                                                                                 |
| Validation gap                                                                                                   | type/range/default/behavior missing                                                                                                                                                    | full field spec                                                                                                                                              |
| Render leak                                                                                                      | SVG names, animation in spec                                                                                                                                                           | semantics only                                                                                                                                               |
| Mini-language                                                                                                    | formula, expression, template                                                                                                                                                          | closed token set                                                                                                                                             |
| Transitional                                                                                                     | "for now", "currently"                                                                                                                                                                 | migration doc only                                                                                                                                           |
| Negative fossil                                                                                                  | scratch term in retired list                                                                                                                                                           | shipped terms only                                                                                                                                           |
| Overpowered setter                                                                                               | multi-field or nested writes without schema                                                                                                                                            | declared fields + primitive types only                                                                                                                       |
| Example as spec                                                                                                  | example field absent from schema                                                                                                                                                       | add to schema or remove from example                                                                                                                         |
| Primitive names appearance                                                                                       | Display/Show/Render/Color/Swap/Animate in primitive name; "spinner"/"progress bar"/"tint"/"fill height" in reason text                                                                 | test: does this primitive change semantic simulation state, or merely describe appearance? If merely appearance, move to render layer                        |
| Copy-paste scene example becomes canonical form                                                                  | scene "template" copy-pasted without `extends:`                                                                                                                                        | use `extends:` and four named operations only                                                                                                                |
| Scene inheritance chain longer than one level                                                                    | base extends base, protocol extends protocol, multi-level depth                                                                                                                        | strictly one level: base extends nothing, protocol extends one base                                                                                          |
| Scene introduces a fifth mutation operation or generic overrides block                                           | undefined operation names, `overrides:`, `patch:`, generic `metadata:`                                                                                                                 | four operations only: add, reposition, deactivate, remove                                                                                                    |
| Scene operation targets a locked field                                                                           | operation changes workspace, background, bounds, zones, layout_rules, capabilities, object fields                                                                                      | only changeable via four operations; some fields locked                                                                                                      |
| Base placement missing placement_name                                                                            | placement without `placement_name` in base scene                                                                                                                                       | every base placement must declare stable `placement_name`                                                                                                    |
| Object schema introduces an extends field                                                                        | `extends:` on objects, template-object layer                                                                                                                                           | objects canonical-by-id, no `extends`, mint new id if different                                                                                              |
| Protocol schema introduces an extends field                                                                      | `extends:` on protocols, template-protocol layer                                                                                                                                       | spec-shaped protocols, no templates, reuse via `sequence_runner`                                                                                             |
| Author YAML names semantic things; runtime derives DOM and colors                                                | naming runtime-derived values as YAML vocabulary                                                                                                                                       | author YAML names semantic entities; runtime derives implementation (DOM mount points, colors)                                                               |
| Author YAML uses `_name` not `_id`                                                                               | `_id` suffix in author-facing fields                                                                                                                                                   | rename all `_id` to `_name`; `_id` is runtime internal only                                                                                                  |
| Objects declare closed `visual_states`; no generic rendering map                                                 | `render_map`, `render_config`, expressions, templating                                                                                                                                 | closed enumeration only; no template or expression evaluator; no metadata/extras escape hatches                                                              |
| Layer ownership: object names assets in `visual_states`, scene names objects/placements, protocol stays semantic | asset names at object top-level or in behavior; visual config in scene; implementation details in protocol                                                                             | strict three-layer: object YAML -> assets in visual_states only; scene YAML -> objects/placements; protocol YAML -> targets/steps/parts/scenes semantic only |
| Authoring surfaces are closed                                                                                    | new authoring file outside `content/objects/`, `content/base_scenes/`, `content/protocols/<cluster>/<name>/{protocol,materials}.yaml`, or `content/protocols/<cluster>/<name>/scenes/` | only the five approved authoring files are valid; new file kinds require a ratified spec edit                                                                |
| Bare `name:` banned in authored YAML                                                                             | `name:` field in YAML examples or schema tables for protocol, step, object, or state-field                                                                                             | use scope-specific handle: `protocol_name`, `step_name`, `object_name`, `field_name`                                                                         |

## Sweep agent deliverable

Output one consolidated table plus per-doc tally:

```
<doc>:<line> <severity> <section-context> <smell-class> "<quoted phrase>" -- <why-it-rots> -- <suggested-fix>
```

- `severity`: `blocker` / `warning` / `note`.
- `section-context`: `target-state` / `current-code` / `migration/history`.
- Sort within each doc: target-state blockers first; current-code notes last.

- No silent rewrites. Flag everything for human ratification.
- Do NOT edit any spec doc -- read-only sweep.
- Group findings by smell-class within each doc; sort docs by finding
  count descending so worst offenders surface first.
- Include a "no findings" line for clean docs so coverage is visible.

## Operating rules for the sweep agent

- Read all canonical docs in scope before flagging anything; some smells
  are cross-doc (shadow vocabularies, ownership ambiguity).
- Cite the past-pitfall name when a finding matches a known pattern.
- Distinguish "current-code description" (acceptable: descriptive prose
  of what exists today) from "target-state authoring rule" (required
  behavior). Most smells live in canonical vocabulary sections.
- Do not propose new vocabulary. Only flag and suggest the closure rule.
- Do not commit. Do not touch CHANGELOG.

## Final instruction to the sweep agent

Focus on canonical vocabulary and schema docs first. The goal is not
style cleanup. The goal is to find every place the specs permit
uncontrolled meaning, hidden semantics, or cross-layer drift.

## Closure

The sweep ends when every flagged finding has either: an accepted
amendment (handed back to the manager for dispatch), or a documented
deferral with owner and resolve-by milestone. No silent acceptances.
