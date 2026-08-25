"""Fast pytest guard: gen_scene_index.discover_per_protocol_scenes fails loud on
duplicate scene_name values across per-protocol scene YAML files.

Two protocols authoring the same scene_name would otherwise silently collide in
the composite-key dict (last one wins), so a SceneChange.to_scene reference could
resolve to the wrong file at runtime. See docs/PYTEST_STYLE.md fixture policy:
setup is inline, built under tmp_path, no on-disk fixture files.
"""

# Standard Library
import os

# PIP3 modules
import pytest

# local repo modules
import pipeline.gen_scene_index as gen_scene_index


def write_scene_yaml(scenes_dir: str, filename: str, scene_name: str) -> None:
	"""Write a minimal per-protocol scene YAML with the given scene_name."""
	os.makedirs(scenes_dir, exist_ok=True)
	content = (
		f"scene_name: {scene_name}\n"
		"workspace: bench_basic\n"
	)
	scene_path = os.path.join(scenes_dir, filename)
	with open(scene_path, "w") as f:
		f.write(content)


def test_duplicate_scene_name_raises(tmp_path: object) -> None:
	"""Two per-protocol scenes sharing a scene_name must fail loud, not silently
	overwrite one another in the composite-key registry."""
	protocols_dir = tmp_path / "content" / "protocols" / "cluster_a"
	write_scene_yaml(
		str(protocols_dir / "protocol_one" / "scenes"), "shared.yaml", "colliding_scene"
	)
	write_scene_yaml(
		str(protocols_dir / "protocol_two" / "scenes"), "shared.yaml", "colliding_scene"
	)

	with pytest.raises(ValueError, match="Duplicate scene_name 'colliding_scene'"):
		gen_scene_index.discover_per_protocol_scenes(str(tmp_path))


def test_distinct_scene_names_do_not_collide(tmp_path: object) -> None:
	"""Two per-protocol scenes with distinct scene_name values register cleanly."""
	protocols_dir = tmp_path / "content" / "protocols" / "cluster_a"
	write_scene_yaml(
		str(protocols_dir / "protocol_one" / "scenes"), "one.yaml", "scene_one"
	)
	write_scene_yaml(
		str(protocols_dir / "protocol_two" / "scenes"), "two.yaml", "scene_two"
	)

	discovered = gen_scene_index.discover_per_protocol_scenes(str(tmp_path))
	assert set(discovered.keys()) == {"scene_one", "scene_two"}
