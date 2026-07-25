# Scene metrics

Current guidance for inspecting a scene's rendered composition. Scene YAML is
coordinate-free: authors declare ordered semantic `zones`, placement membership,
depth tiers, and the bounded categorical layout hints. The layout manager derives
scene and zone geometry after measuring the objects. See
[SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md) and
[LAYOUT_ENGINE.md](LAYOUT_ENGINE.md).

## Current workflow

Render the evidence before reading geometry-derived diagnostics:

```bash
npm run scene:png -- --all
```

Then run the current validation entry points:

```bash
source source_me.sh && python3 -m validation.scene_lint.cli
source source_me.sh && python3 -m validation.scene_design.cli --markdown
```

For one scene, pass its YAML file to both tools:

```bash
source source_me.sh && python3 -m validation.scene_lint.cli content/base_scenes/<scene_name>.yaml
source source_me.sh && python3 -m validation.scene_design.cli --markdown content/base_scenes/<scene_name>.yaml
```

The renderer writes the evidence consumed by both validators to
`generated/scene_render_stats/<scene_name>.stats.json`. The scene-lint result
identifies render-risk findings; the scene-design result reports composition
advice. Rendered geometry is diagnostic evidence, not an authored YAML surface.

## Authoring response

When a diagnostic identifies crowding, empty space, overlap, clipping, or weak
hierarchy, change the semantic model in this order:

1. Confirm that every placement is required by the protocol's visible workflow.
2. Reconsider zone declaration order and placement-to-zone membership.
3. Use `align`, `align_stop`, and `depth_tier` to express the intended grouping.
4. Use the approved categorical `layout.anchor_y` or `layout.label_placement`
   hint only when it expresses the intended semantic arrangement.
5. Change an object intrinsic metric only when the object is wrong in every
   scene where it appears.
6. Re-render and inspect the derived composition before changing another layer.

Do not author coordinates, source bounds, baselines, numeric placement geometry,
or scene-side size overrides. If the available closed vocabulary cannot express
the intended composition, stop and propose a vocabulary change rather than
adding an escape hatch.

## Reading the validators

`validation.scene_lint` blocks invalid authored structure and reports predicted
render failures from the rendered evidence. `validation.scene_design` reports
composition measures such as density, balance, label clarity, hierarchy, and
protocol affinity. The browser renderer and its generated stats remain the
source of truth when a validator and a render appear to disagree.

For the full schema, use [SCENE_YAML_FORMAT.md](SCENE_YAML_FORMAT.md). For
layout phases and the authoring tuning order, use
[LAYOUT_ENGINE.md](LAYOUT_ENGINE.md).
