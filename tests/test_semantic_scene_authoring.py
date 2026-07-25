"""Behavioral coverage for the coordinate-free source-scene boundary."""

# PIP3 modules
import pytest

# local repo modules
import pipeline.gen_scene_index as gen_scene_index
import pipeline.scene_inheritance as scene_inheritance
from validation.scene_lint.rules_group_a import check_forbidden_source_geometry
from validation.scene_lint.rules_group_b import check_zone_overlap
from validation.yaml_schema.scene_base_validator import BaseSceneValidator

#============================================

def _semantic_scene() -> dict:
	"""Return the smallest scene that exercises semantic-zone boundaries."""
	scene = {
		'scene_name': 'semantic_bench',
		'workspace': 'bench',
		'capabilities': ['item_workspace'],
		'zones': [
			{'zone_name': 'front', 'label': 'Front work area', 'align': 'tab-stops'},
			{'zone_name': 'rear', 'label': 'Rear context area', 'align': 'tab-stops'},
		],
		'placements': [{
			'placement_name': 'sample_pipette',
			'object_name': 'micropipette',
			'zone': 'front',
			'depth_tier': 1,
			'depth': 'front',
			'align_stop': 'left',
			'layout': {'label_placement': 'top'},
		}],
	}
	return scene


#============================================

def test_semantic_scene_validates_and_emits_zone_identity() -> None:
	"""Semantic zones remain ordered identities with no fabricated bounds."""
	scene = _semantic_scene()
	validator = BaseSceneValidator()
	findings = validator.validate(scene, 'memory_scene.yaml')
	lines = []
	gen_scene_index.emit_scene_ts('semantic_scene', scene, lines, set())
	output = '\n'.join(lines)
	assert not findings
	assert 'bounds:' not in output and "depth: 'front'," in output


#============================================

def test_authored_geometry_fails_loudly_at_every_source_boundary() -> None:
	"""A source rectangle is a blocker in both generator and source lint."""
	scene = _semantic_scene()
	scene['scene_bounds'] = {'left': 0, 'right': 100, 'top': 0, 'bottom': 100}
	with pytest.raises(ValueError, match="Forbidden authored geometry 'scene_bounds'"):
		gen_scene_index.reject_authored_geometry(scene, 'memory_scene.yaml')
	findings = check_forbidden_source_geometry(scene, 'semantic_scene')
	assert any(finding.rule == 'forbidden_source_geometry' for finding in findings)


#============================================

def test_base_scene_validator_names_forbidden_scene_geometry() -> None:
	"""The formal schema reports scene_bounds as geometry, not generic closure."""
	scene = _semantic_scene()
	scene['scene_bounds'] = {}
	findings = BaseSceneValidator().validate(scene, 'memory_scene.yaml')
	assert any("authored geometry 'scene_bounds'" in finding.message for finding in findings)


#============================================

def test_inheritance_preserves_semantic_zone_membership() -> None:
	"""Placement operations resolve by placement identity before geometry exists."""
	base = _semantic_scene()
	base_scenes = {base['scene_name']: base}
	protocol_scene = {
		'scene_name': 'derived_scene',
		'extends': base['scene_name'],
		'reposition_placements': [{
			'placement_name': base['placements'][0]['placement_name'],
			'zone': base['zones'][-1]['zone_name'],
		}],
	}
	resolved = scene_inheritance.resolve_protocol_scene('derived_scene', protocol_scene, base_scenes)
	assert resolved['placements'][0]['zone'] == base['zones'][-1]['zone_name']
	assert 'scene_bounds' not in resolved


#============================================

def test_zone_overlap_uses_rendered_dump_geometry() -> None:
	"""Zone overlap is detected from computed dump bounds, not source YAML."""
	source_scene = _semantic_scene()
	dump_data = {
		'zones': [
			{'name': 'one', 'bounds': {'left': 0, 'right': 8, 'top': 0, 'bottom': 8}},
			{'name': 'two', 'bounds': {'left': 4, 'right': 10, 'top': 0, 'bottom': 8}},
		],
	}
	findings = check_zone_overlap(source_scene, 'semantic_scene', dump_data)
	assert any(finding.evidence['zone_a'] == 'one' for finding in findings)
