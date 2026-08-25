"""Behavioral gates for object-authoritative SVG asset taxonomy validation."""

from pathlib import Path

import pytest

from pipeline import gen_liquid_regions
from validation.svg.asset_taxonomy_validator import (
	AssetTaxonomyValidationError,
	derive_requested_asset_behavior_categories,
	validate_asset_taxonomy,
)


def _write_svg(assets_dir: Path, relative: str) -> None:
	"""Write a minimal complete SVG to the recursive registry."""
	path = assets_dir / relative
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")


def _write_object(objects_dir: Path, contents: str) -> None:
	"""Write one object declaration used as the selection authority."""
	objects_dir.mkdir(parents=True, exist_ok=True)
	(objects_dir / "container.yaml").write_text(contents, encoding="utf-8")


def test_taxonomy_rejects_bare_state_only_svg_filename(tmp_path: Path) -> None:
	"""A generic state filename cannot enter the recursive SVG registry."""
	assets = tmp_path / "assets"
	_write_svg(assets, "equipment/static/open.svg")
	with pytest.raises(AssetTaxonomyValidationError, match="state-only"):
		validate_asset_taxonomy(assets, tmp_path / "objects")


def test_taxonomy_derives_mixed_form_membership_only_from_object_cases(tmp_path: Path) -> None:
	"""One state map may select static and material forms without a sidecar."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/binary_state/microtube_open.svg")
	_write_svg(assets, "equipment/binary_state/microtube_closed.svg")
	_write_svg(assets, "equipment/static/not_a_filename_collection.svg")
	_write_object(objects, '''visual_states:
  closure:
    kind: svg
    cases:
      - when: open
        output: {asset_name: microtube_open}
      - when: closed
        output: {asset_name: microtube_closed}
''')
	result = validate_asset_taxonomy(assets, objects)
	assert result.selections[0].asset_names == ("microtube_open", "microtube_closed")
	assert all("not_a_filename_collection" not in selection.asset_names for selection in result.selections)


def test_taxonomy_rejects_missing_object_selected_member(tmp_path: Path) -> None:
	"""A complete SVG form named in an object case must exist in the registry."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/binary_state/microtube_open.svg")
	_write_object(objects, '''visual_states:
  closure:
    kind: svg
    cases:
      - when: open
        output: {asset_name: microtube_open}
      - when: closed
        output: {asset_name: microtube_closed}
''')
	with pytest.raises(AssetTaxonomyValidationError, match="missing asset 'microtube_closed'"):
		validate_asset_taxonomy(assets, objects)


def test_taxonomy_rejects_duplicate_recursive_logical_asset_name(tmp_path: Path) -> None:
	"""A stem has one URL identity regardless of recursive source placement."""
	assets = tmp_path / "assets"
	_write_svg(assets, "equipment/static/microtube.svg")
	_write_svg(assets, "archive/microtube.svg")
	with pytest.raises(AssetTaxonomyValidationError, match="duplicate logical SVG basename"):
		validate_asset_taxonomy(assets, tmp_path / "objects")


def test_taxonomy_enforces_yaml_derived_behavior_directory(tmp_path: Path) -> None:
	"""A two-form object state places both opaque forms in binary_state."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/static/power_supply_off.svg")
	_write_svg(assets, "equipment/binary_state/power_supply_on.svg")
	_write_object(objects, '''visual_states:
  power:
    kind: svg
    cases:
      - when: false
        output: {asset_name: power_supply_off}
      - when: true
        output: {asset_name: power_supply_on}
''')
	with pytest.raises(AssetTaxonomyValidationError, match="expected equipment/binary_state"):
		validate_asset_taxonomy(assets, objects)


def test_taxonomy_derives_material_root_as_variable_volume(tmp_path: Path) -> None:
	"""Internal rendering semantics outrank a single-form YAML selection."""
	assets = tmp_path / "assets"
	path = assets / "equipment" / "variable_volume" / "microtube.svg"
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg" data-vlab-rendering="material"/>',
		encoding="utf-8",
	)
	result = validate_asset_taxonomy(assets, tmp_path / "objects")
	assert result.behavior_category("microtube") == "variable_volume"


def test_missing_asset_projection_uses_fill_height_intent(tmp_path: Path) -> None:
	"""The picker can place a not-yet-authored liquid asset correctly."""
	objects = tmp_path / "objects"
	_write_object(objects, '''visual_states:
  material:
    kind: svg
    cases:
      - when: empty
        output: {asset_name: future_tube}
      - when: media
        output: {asset_name: future_tube}
  volume:
    applies_to: object
    render_effect: fill_height
    target: anchor_liquid_bounds
''')
	assert derive_requested_asset_behavior_categories(objects) == {
		"future_tube": "variable_volume",
	}


def test_missing_asset_projection_uses_selection_cardinality(tmp_path: Path) -> None:
	"""Opaque missing forms inherit the complete-form state cardinality."""
	objects = tmp_path / "objects"
	_write_object(objects, '''visual_states:
  power:
    kind: svg
    cases:
      - when: false
        output: {asset_name: device_off}
      - when: true
        output: {asset_name: device_on}
''')
	assert derive_requested_asset_behavior_categories(objects) == {
		"device_off": "binary_state",
		"device_on": "binary_state",
	}


def test_object_fill_height_rejects_an_ordinary_selected_svg(tmp_path: Path) -> None:
	"""The retired overlay path cannot return through an ordinary asset binding."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/static/ordinary_tube.svg")
	_write_object(objects, '''visual_states:
  material:
    kind: svg
    cases:
      - when: water
        output: {asset_name: ordinary_tube}
  volume:
    applies_to: object
    render_effect: fill_height
    target: anchor_liquid_bounds
''')
	with pytest.raises(
		AssetTaxonomyValidationError,
		match="fill_height must select a material-rendered SVG",
	):
		validate_asset_taxonomy(assets, objects)


@pytest.mark.parametrize(
	("contents", "message"),
	[
		(
			"""visual_states:
  closure:
    kind: svg
""",
			"cases must be a list",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases: not-a-list
""",
			"cases must be a list",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - not-a-mapping
""",
			"case must be a mapping",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - when: closed
""",
			"output must be a mapping",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - output: not-a-mapping
""",
			"output must be a mapping",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - output: {}
""",
			"asset_name must be a nonempty string",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - output: {asset_name: ''}
""",
			"asset_name must be a nonempty string",
		),
		(
			"""visual_states:
  closure:
    kind: svg
    cases:
      - output: {asset_name: 7}
""",
			"asset_name must be a nonempty string",
		),
	],
)
def test_taxonomy_rejects_malformed_svg_selection_shape(
	tmp_path: Path,
	contents: str,
	message: str,
) -> None:
	"""Bounded SVG membership extraction reports its malformed structures."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/static/microtube.svg")
	_write_object(objects, contents)
	with pytest.raises(AssetTaxonomyValidationError, match=message):
		validate_asset_taxonomy(assets, objects)


def test_material_tree_uses_the_same_object_selected_membership_gate(tmp_path: Path) -> None:
	"""Material-tree scans reject a missing object-selected form before compilation."""
	assets = tmp_path / "assets"
	objects = tmp_path / "objects"
	_write_svg(assets, "equipment/static/microtube_open.svg")
	_write_object(objects, '''visual_states:
  closure:
    kind: svg
    cases:
      - when: open
        output: {asset_name: microtube_missing}
''')
	with pytest.raises(AssetTaxonomyValidationError, match="microtube_missing"):
		gen_liquid_regions.compile_material_tree(assets, tmp_path / "generated", objects)
