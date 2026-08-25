"""Scene geometry loader: reads rendered geometry from stats.json.

The browser pipeline (tools/scene_to_png.mjs -> tools/scene_stats.mjs) is the
single source of truth for scene layout geometry. It renders every shipped scene
through the real TypeScript layout pipeline and writes the rendered bounding
boxes to generated/scene_render_stats/<scene>.stats.json under a "geometry" block.

This module is a thin LOADER. It does not compute layout. It reads the rendered
geometry block and returns the dict shape the downstream consumers
(validation.scene_lint group B rules, validation.scene_design metrics) expect.
There is no Python geometry model; the validator follows the generator.

See docs/archive/decisions/scene_calc_validator_follows_generator.md.

Coordinate space: all boxes are CSS pixels with a top-left origin, from one
render. Placement-level bboxes (visual_bbox, placement_bbox, footprint_bbox,
label_bbox) use {x, y, w, h} keys. Scene bounds, zone bounds, and zone
inner_rect use {left, right, top, bottom} edge-coordinate form. Every box in a
single returned dict shares one pixel space, so rules that compare boxes against
each other and against zone rects are unit-consistent.

If the stats.json for a scene is missing, stale, or carries no geometry block
(load-failed render), this loader raises RuntimeError. It never synthesizes
geometry. The fix is to re-render (node tools/scene_to_png.mjs --all), not to
predict layout in Python.
"""

import json
from pathlib import Path

from validation.shared_toolkit.yaml_io import load_yaml


#============================================
# Typed signal for missing/stale render evidence
#============================================

class MissingRenderEvidenceError(RuntimeError):
	"""Raised when a scene's rendered stats.json is missing or load-failed.

	This is a render-evidence prerequisite failure, distinct from other
	RuntimeErrors (e.g. repo-root not found, malformed YAML). The validator
	CLIs catch this specific type to emit a precise "render scenes first"
	prerequisite message. The fix is always to re-render:
	node tools/scene_to_png.mjs --all
	"""


#============================================
# Stats path resolution
#============================================

def _find_repo_root(start: Path) -> Path:
	"""Walk upward from start until a directory containing AGENTS.md is found.

	Args:
		start: Path to begin the search from.

	Returns:
		Path to the repo root.

	Raises:
		RuntimeError: if no AGENTS.md is found walking up to the filesystem root.
	"""
	current = start
	while current.parent != current:
		if (current / 'AGENTS.md').exists():
			return current
		current = current.parent
	raise RuntimeError(
		f"could not locate repo root (no AGENTS.md) walking up from {start}"
	)


def _stats_path_for_scene(repo_root: Path, scene_name: str) -> Path:
	"""Return the rendered stats.json path for a scene.

	Args:
		repo_root: Repo root path.
		scene_name: Scene name (matches the rendered PNG/stats basename).

	Returns:
		Path to generated/scene_render_stats/<scene_name>.stats.json.
	"""
	return repo_root / 'generated' / 'scene_render_stats' / f'{scene_name}.stats.json'


#============================================
# Main loader
#============================================

def dump_scene_geometry(
	scene_path: Path,
	library_paths: list[Path] | None = None,
	svg_root: Path | None = None,
	viewport: dict[str, int] | None = None
) -> dict[str, object]:
	"""Load rendered scene geometry from the stats.json produced by the render.

	Reads the scene YAML only to discover its scene_name, then loads the
	rendered geometry block from generated/scene_render_stats/<scene_name>.stats.json.
	Returns the dict shape the group B rules and design metrics consume.

	Args:
		scene_path: Path to the scene YAML file (used to discover scene_name and
			the repo root).
		library_paths: Ignored. Kept for call-site compatibility.
		svg_root: Ignored. Kept for call-site compatibility.
		viewport: Ignored. The render tool owns the viewport.

	Returns:
		Dict with keys:
			scene: scene name string.
			scene_bounds: {left, right, top, bottom} in CSS pixels.
			zones: list of {name, bounds, inner_rect} (edge-coordinate pixels).
			placements: list of {placement_name, kind, asset_path, visual_bbox,
				placement_bbox, footprint_bbox, label_bbox, aspect_delta_pct,
				scale_source}; bboxes are {x, y, w, h} pixels.

	Raises:
		MissingRenderEvidenceError: if the stats.json is missing or carries no
			geometry block (the scene must be re-rendered; no geometry is
			synthesized here). This subclasses RuntimeError so existing broad
			RuntimeError handlers still catch it.
	"""
	# library_paths/svg_root/viewport are accepted for call-site compatibility
	# but unused: geometry comes from the rendered stats.json, not from YAML.
	_ = (library_paths, svg_root, viewport)

	# Resolve to an absolute path so the repo-root walk works for relative
	# inputs (e.g. content/base_scenes/hood_basic.yaml passed on the CLI).
	scene_path = Path(scene_path).resolve()
	scene = load_yaml(scene_path)
	scene_name = scene['scene_name']

	repo_root = _find_repo_root(scene_path.parent)
	stats_path = _stats_path_for_scene(repo_root, scene_name)

	if not stats_path.exists():
		raise MissingRenderEvidenceError(
			f"rendered geometry not found for scene {scene_name!r}: expected "
			f"{stats_path} under generated/scene_render_stats/. Generate the stats "
			f"first: run ./build_github_pages.sh (or the direct renderer "
			f"node tools/scene_to_png.mjs --all)"
		)

	stats = json.loads(stats_path.read_text())
	geometry = stats.get('geometry')
	if not geometry:
		# A null/absent geometry block means the render load-failed for this
		# scene. Fail loudly; do not synthesize geometry.
		raise MissingRenderEvidenceError(
			f"stats.json for scene {scene_name!r} has no geometry block (render "
			f"load-failed?): {stats_path} under generated/scene_render_stats/. "
			f"Regenerate the stats: run ./build_github_pages.sh (or the direct "
			f"renderer node tools/scene_to_png.mjs --all)"
		)

	# The geometry block already carries the consumer shape. Surface scene_name
	# at the top level under the 'scene' key the consumers read.
	return {
		'scene': scene_name,
		'scene_bounds': geometry['scene_bounds'],
		'zones': geometry['zones'],
		'placements': geometry['placements'],
	}


def dumps_scene_geometry(
	scene_path: Path,
	library_paths: list[Path] | None = None,
	svg_root: Path | None = None,
	viewport: dict[str, int] | None = None
) -> str:
	"""Load scene geometry and serialize to a single-line JSON string.

	Args:
		scene_path: Path to the scene YAML file.
		library_paths: Ignored. Kept for call-site compatibility.
		svg_root: Ignored. Kept for call-site compatibility.
		viewport: Ignored. Kept for call-site compatibility.

	Returns:
		JSON string (single line, no pretty printing).
	"""
	dump_dict = dump_scene_geometry(
		scene_path,
		library_paths=library_paths,
		svg_root=svg_root,
		viewport=viewport
	)
	return json.dumps(dump_dict, separators=(',', ':'))
