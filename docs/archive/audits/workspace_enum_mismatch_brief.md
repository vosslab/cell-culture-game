# Workspace enum mismatch decision brief

Status: READ-ONLY investigation. No files were modified. User decision required before any fix lands.

## The mismatch

`docs/specs/SCENE_YAML_FORMAT.md` line 113 documents the `workspace` field enum as:
`equipment_bench`, `wet_lab_hood`, `modal_overlay`, `dedicated_plate`.

All 9 authored base scenes in `content/base_scenes/` use a different set:
`bench` (x6), `hood` (x1), `cell_counter` (x1), `microscope` (x1).

The TypeScript runtime enum in `src/scene_runtime/layout/constants.ts` lines 21-28
(the `WORKSPACES` const) uses: `bench`, `hood`, `microscope`, `incubator`,
`plate_reader`, `cell_counter`. This matches the authored YAML, not the spec doc.

## Consumer inventory

The following surfaces read or use the `workspace` field value at runtime or build time.

### Runtime-load-bearing consumers (values are enforced)

- `src/scene_runtime/layout/constants.ts` lines 21-28: `WORKSPACES` const defines
  the closed enum `["bench", "hood", "microscope", "incubator", "plate_reader",
  "cell_counter"]`. TypeScript derives `export type Workspace` from this array
  (`types.ts` line 20). Any value not in this list causes an `unknown_workspace`
  diagnostic and falls back to authored `width_scale` instead of the per-workspace
  `px_per_cm` scaling (see `scale_to_real_world.ts` lines 55-57).

- `src/scene_runtime/layout/constants.ts` lines 127-134: `WORKSPACE_PX_PER_CM`
  record is keyed by `Workspace` and maps `bench: 5.5`, `hood: 8.0`,
  `microscope: 10.0`, `incubator: 9.0`, `plate_reader: 8.0`, `cell_counter: 9.0`.
  A workspace value not in this map silently loses cm-based scaling.

- `src/style.css` lines 235-259: `data-scene-workspace` CSS attribute selector gates
  the bench-surface visual band on the values `bench`, `cell_counter`,
  `microscope`, `incubator`, `plate_reader`. These must match the authored YAML
  values passed through `render_scene.tsx` line 108.

- `src/scene_runtime/renderer/render_scene.tsx` line 108:
  `root.setAttribute("data-scene-workspace", result.scene.workspace)` stamps the
  raw authored string onto the DOM. CSS gating fails silently if the value does not
  match a selector.

- `pipeline/gen_scene_index.py` line 416-418: reads `data["workspace"]` and raises
  `ValueError` if absent; line 523 emits the raw string into generated TypeScript.
  No enum check is applied here; any non-empty string passes.

- `pipeline/scene_inheritance.py` line 303: copies `workspace` from base scene into
  child without validation.

### Purely documentary (values are not checked)

- `validation/yaml_schema/constants.py` line 90: records `workspace` as a required
  key but does not validate its value.

- `validation/yaml_schema/summary.py` line 89 and `compiled_summary.py` line 82:
  read `workspace` for display and telemetry aggregation only; any string is
  accepted.

### Tests with workspace values

- `tests/test_layout_engine.mjs` lines 30, 89, 113, 655, 709: all use `"bench"`.
  These tests are correct relative to the runtime enum.

- `tests/test_structural_guards.mjs` line 55: uses `"bench"`.

- `tests/test_label_placement_validator.py` line 41: uses `"equipment_bench"`.
  This fixture value is inconsistent with the runtime enum and would produce an
  `unknown_workspace` diagnostic if passed through the layout engine at runtime.

- `tests/content/dev_smoke/select_check/scene.yaml` line 2: uses `"bench"`.

## When the divergence arose

The spec doc `docs/specs/SCENE_YAML_FORMAT.md` has documented `equipment_bench`
since its first commit (48d7445, the initial spec expansion batch).

The TypeScript runtime `constants.ts` has used `"bench"` since its first commit
(8d1bb18, the build-time codegen pipeline introduction).

The two surfaces were never aligned. The spec doc appears to have been drafted with
a prospective vocabulary that was never adopted in code.

## Load-bearing vs. documentary verdict

The authored YAML values (`bench`, `hood`, etc.) are load-bearing: they flow
through the pipeline into generated TypeScript, are stamped onto the DOM as
`data-scene-workspace`, and must match the `WORKSPACES` const for px-per-cm
scaling to apply. The CSS selectors in `style.css` also key directly on these
string values.

The spec doc values (`equipment_bench`, `wet_lab_hood`, etc.) are purely
documentary. They exist nowhere in the runtime, pipeline, or generated code. No
validator checks the spec doc enum against authored scenes.

## Option A: fix the spec doc to match authored values

Update `docs/specs/SCENE_YAML_FORMAT.md` line 113 to replace `equipment_bench`,
`wet_lab_hood`, `modal_overlay`, `dedicated_plate` with the runtime enum:
`bench`, `hood`, `microscope`, `incubator`, `plate_reader`, `cell_counter`.
Also update the example at line 454 (`workspace: equipment_bench` becomes
`workspace: bench`) and line 432 (`workspace: modal_overlay` -- needs a decision
on whether `modal_overlay` should remain as a distinct concept or map to an
existing runtime value).

Blast radius:
- 1 file: `docs/specs/SCENE_YAML_FORMAT.md` (lines 113 and 454; line 432 needs
  separate decision on `modal_overlay`).
- 1 test fixture: `tests/test_label_placement_validator.py` line 41 uses
  `equipment_bench`; must be corrected to `bench`.
- No pipeline regeneration required.
- No YAML content changes required.
- No TypeScript changes required.

## Option B: migrate YAML to the documented spec values

Update all 9 base scenes in `content/base_scenes/` to use the spec doc values
(`bench` -> `equipment_bench`, `hood` -> `wet_lab_hood`, etc.). Simultaneously
update `WORKSPACES` in `constants.ts`, `WORKSPACE_PX_PER_CM`, and all CSS
selectors to use the new strings. Update `modal_overlay` and `dedicated_plate`
in the spec doc if no runtime equivalent exists yet.

Blast radius:
- 9 YAML files in `content/base_scenes/` (all workspace lines).
- Unknown number of protocol-scene YAML files in `content/protocols/` that
  inherit workspace from base scenes via `scene_inheritance.py` (inheritance
  copies the base value, so child YAML files do not repeat it; child changes
  are zero if inheritance is correct).
- `src/scene_runtime/layout/constants.ts` lines 21-28 and 127-134: rename all
  6 keys in `WORKSPACES` and `WORKSPACE_PX_PER_CM`.
- `src/style.css` lines 235-259: rename all CSS selectors for
  `data-scene-workspace`.
- `tests/test_layout_engine.mjs`: update all `workspace: "bench"` fixture values.
- `tests/test_structural_guards.mjs` line 55: update fixture value.
- `tests/content/dev_smoke/select_check/scene.yaml` line 2: update value.
- `tests/test_label_placement_validator.py` line 41: already uses `equipment_bench`
  and would require no change.
- Pipeline regeneration required after any change to `constants.ts` or YAML.

## Recommendation

Option A is the correct choice under the "fix the design, not the symptom" and
"long-term over short-term" principles from `docs/REPO_STYLE.md`.

The load-bearing truth is in the runtime code and authored YAML, not in the spec
doc. The spec doc introduced prospective terminology (`equipment_bench`,
`wet_lab_hood`) that was never adopted in code, making it a spec that documents a
vocabulary that does not exist in the working system. Correcting the spec to
describe what actually runs is a smaller, safer change with a well-bounded blast
radius (1 spec file, 1 test fixture) and zero risk of breaking the running system.

Option B would migrate six working values across the runtime, CSS, tests, and YAML
to match a documentary fiction. The migration would be mechanical but wide, carries
regeneration cost, and offers no functional benefit because the spec-doc values
(`equipment_bench` etc.) carry no semantic advantage over the current short forms.

One open point requiring user judgment before Option A is finalized: `modal_overlay`
and `dedicated_plate` appear in the spec doc but have no counterpart in the runtime
enum. Option A should either drop them from the spec, add a note that they are
reserved for future use, or map them to an existing runtime value. This is a
vocabulary scope decision, not a blast-radius concern.
