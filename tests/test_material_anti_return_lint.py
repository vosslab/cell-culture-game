"""Self-proving post-cutover lint for the retired liquid rectangle renderer."""

from pathlib import Path

import pytest

from validation.svg.material_anti_return_lint import (
	MaterialAntiReturnLintError,
	lint_material_anti_return,
	main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _valid_material_svg() -> str:
	return '''<svg xmlns="http://www.w3.org/2000/svg" data-vlab-rendering="material">
<defs><clipPath id="anchor_liquid_clip"><path d="M0 0H10V10H0Z"/></clipPath></defs>
<rect id="anchor_liquid_bounds" x="0" y="0" width="10" height="10" display="none"/>
<g data-vlab-layer-name="fixed_back" data-vlab-layer-kind="fixed"><path d="M0 0H10V10H0Z" fill="#eeeeee"/></g>
<g data-vlab-layer-name="liquid_body" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="body"><path d="M1 1H9V10H1Z" fill="#cc0066"/></g>
<g data-vlab-layer-name="fixed_front" data-vlab-layer-kind="fixed"><path d="M0 0H10" stroke="#222222"/></g>
</svg>'''


def _write_tree(tmp_path: Path, *, svg: str | None = None, runtime: str = "export {};\n", object_yaml: str | None = None) -> tuple[Path, Path, Path, Path]:
	assets = tmp_path / "assets"
	objects = tmp_path / "content" / "objects"
	runtime_dir = tmp_path / "src" / "scene_runtime" / "renderer"
	asset = assets / "equipment" / "variable_volume" / "tube.svg"
	asset.parent.mkdir(parents=True)
	asset.write_text(svg or _valid_material_svg(), encoding="utf-8")
	objects.mkdir(parents=True)
	(objects / "tube.yaml").write_text(object_yaml or '''visual_states:
  material:
    kind: svg
    cases:
      - when: water
        output: {asset_name: tube}
  volume:
    applies_to: object
    render_effect: fill_height
    target: anchor_liquid_bounds
''', encoding="utf-8")
	runtime_dir.mkdir(parents=True)
	(runtime_dir / "liquid_paint.ts").write_text(runtime, encoding="utf-8")
	return tmp_path, assets, objects, runtime_dir


def _lint_tmp(tmp_path: Path, **kwargs: str) -> None:
	repo, assets, objects, runtime = _write_tree(tmp_path, **kwargs)
	lint_material_anti_return(repo, assets_dir=assets, objects_dir=objects, source_dir=runtime.parents[1])


def test_cutover_tree_passes_the_anti_return_gate() -> None:
	"""Production has no retired renderer and every material form validates."""
	lint_material_anti_return(REPO_ROOT)


def test_lint_rejects_a_scratch_material_rect_overlay(tmp_path: Path) -> None:
	"""A deliberate object-level SVG rect reintroduction fails without source mutation."""
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-RETIRED-OVERLAY: src/scene_runtime/renderer/liquid_paint.ts"):
		_lint_tmp(tmp_path, runtime='''
export function render_liquid_material_effects() {
  document.createElementNS("http://www.w3.org/2000/svg", "rect");
}
''')


def test_lint_allows_material_runtime_svg_creation_when_no_rect_is_created(tmp_path: Path) -> None:
	"""The retired overlay rule is about rectangles, not generic SVG setup."""
	_lint_tmp(tmp_path, runtime='''
export function render_liquid_material_effects() {
  document.createElementNS("http://www.w3.org/2000/svg", "svg");
}
''')


def test_lint_rejects_rect_overlay_outside_the_renderer_directory(tmp_path: Path) -> None:
	"""An unmarked helper anywhere in ``src/`` cannot evade the anti-return gate."""
	repo, assets, objects, runtime = _write_tree(tmp_path)
	helper = runtime.parents[1] / "helpers" / "rogue_overlay.ts"
	helper.parent.mkdir()
	helper.write_text(
		'document.createElementNS("http://www.w3.org/2000/svg", "rect");\n',
		encoding="utf-8",
	)
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-RETIRED-OVERLAY: src/helpers/rogue_overlay.ts"):
		lint_material_anti_return(repo, assets_dir=assets, objects_dir=objects, source_dir=runtime.parents[1])


@pytest.mark.parametrize("relative", [
	"scene_runtime/renderer/subpart_visual_state_renderer.tsx",
	"scene_runtime/renderer/subpart_hit_surface.tsx",
])
def test_lint_allows_only_the_two_structured_svg_rect_renderers(tmp_path: Path, relative: str) -> None:
	"""Structured paint and hit-surface rectangles are intentional non-vessel geometry."""
	repo, assets, objects, runtime = _write_tree(tmp_path)
	allowed = runtime.parents[1] / relative
	allowed.parent.mkdir(exist_ok=True)
	allowed.write_text("export const Rect = () => <rect/>;\n", encoding="utf-8")
	lint_material_anti_return(repo, assets_dir=assets, objects_dir=objects, source_dir=runtime.parents[1])


def test_lint_rejects_direct_authored_semantic_lookup(tmp_path: Path) -> None:
	"""Material runtime must receive generated handles, never query semantic layers."""
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-GENERATED-HANDLES: src/scene_runtime/renderer/liquid_paint.ts"):
		_lint_tmp(tmp_path, runtime='''
export function render_liquid_material_effects(host: HTMLElement) {
  return host.querySelector('[data-vlab-layer-name="liquid_body"]');
}
''')


def test_lint_rejects_constructed_authored_semantic_id(tmp_path: Path) -> None:
	"""A semantic layer id cannot be reconstructed before a DOM lookup."""
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-GENERATED-HANDLES: src/scene_runtime/renderer/liquid_paint.ts"):
		_lint_tmp(tmp_path, runtime='''
export function render_liquid_material_effects(host: HTMLElement) {
  const semanticId = "liquid_body";
  return host.querySelector(`#${semanticId}`);
}
''')


def test_lint_rejects_unclassified_material_geometry(tmp_path: Path) -> None:
	"""Visible geometry outside a semantic group cannot silently enter material art."""
	invalid = _valid_material_svg().replace(
		'<g data-vlab-layer-name="fixed_front"',
		'<path d="M2 2H8V8H2Z" fill="#00aa00"/>\n<g data-vlab-layer-name="fixed_front"',
	)
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-SVG-SEMANTICS: assets/equipment/variable_volume/tube.svg: geometry must belong"):
		_lint_tmp(tmp_path, svg=invalid)


def test_lint_rejects_object_level_fill_height_for_an_ordinary_asset(tmp_path: Path) -> None:
	"""The object binding cannot reopen the ordinary-form overlay path."""
	ordinary = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0H1"/></svg>'
	with pytest.raises(MaterialAntiReturnLintError, match=r"M7-OBJECT-BINDING: content/objects: object-level fill_height must select a material-rendered SVG"):
		_lint_tmp(tmp_path, svg=ordinary)


def test_cli_returns_failure_and_prints_the_rule_for_a_scratch_regression(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
	"""The build-callable CLI preserves the underlying rule-labelled error."""
	repo, assets, objects, runtime = _write_tree(
		tmp_path,
		runtime='''
export function render_liquid_material_effects() {
  document.createElementNS("http://www.w3.org/2000/svg", "rect");
}
''',
	)
	assert assets.exists() and objects.exists() and runtime.exists()
	assert main(["--repo-root", str(repo)]) == 1
	assert "M7-RETIRED-OVERLAY: src/scene_runtime/renderer/liquid_paint.ts" in capsys.readouterr().err


def test_build_front_door_runs_the_anti_return_cli_before_generators() -> None:
	"""The generated-artifact build cannot bypass the post-cutover gate."""
	build_script = (REPO_ROOT / "pipeline" / "build_generated.sh").read_text(encoding="utf-8")
	gate = "python3 -m validation.svg.material_anti_return_lint"
	assert gate in build_script
	assert build_script.index(gate) < build_script.index("python3 pipeline/gen_object_library.py")
