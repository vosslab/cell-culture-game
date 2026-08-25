"""Tests for the pure predicate functions in pipeline/gen_svg_manifest.py.

Covers _visual_state_needs_dom_svg and _object_needs_dom_svg with small
in-memory dict literals.  No filesystem I/O, no subprocess calls.
"""

import os
import sys

# Add pipeline/ to sys.path so gen_svg_manifest can be imported without
# triggering its module-level side effects (no top-level code runs).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import gen_svg_manifest

#============================================
def test_fill_height_formula_needs_dom_svg() -> None:
	"""A visual_state with a fill_height( formula requires DOM SVG."""
	vs = {"kind": "overlay", "formula": "fill_height(0.5)"}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is True


#============================================
def test_composite_nonempty_needs_dom_svg() -> None:
	"""A composite kind with a non-empty list requires DOM SVG."""
	vs = {"kind": "composite", "composite": ["layer_liquid", "layer_cap"]}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is True


#============================================
def test_composite_empty_does_not_need_dom_svg() -> None:
	"""A composite kind with an empty list is img-eligible."""
	vs = {"kind": "composite", "composite": []}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is False


#============================================
def test_overlay_kind_does_not_need_dom_svg() -> None:
	"""An overlay kind (text label over asset) is img-eligible."""
	vs = {"kind": "overlay"}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is False


#============================================
def test_svg_kind_does_not_need_dom_svg() -> None:
	"""A whole-asset svg swap is img-eligible."""
	vs = {"kind": "svg", "asset_name": "bottle_green"}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is False


#============================================
def test_unknown_kind_safe_bias_needs_dom_svg() -> None:
	"""An unrecognized kind defaults to True (safe bias)."""
	vs = {"kind": "future_render_effect"}
	assert gen_svg_manifest._visual_state_needs_dom_svg(vs) is True


#============================================
def test_material_container_capability_needs_dom_svg() -> None:
	"""An object with material_container capability requires DOM SVG."""
	obj = {"capabilities": ["material_container"]}
	assert gen_svg_manifest._object_needs_dom_svg(obj) is True


#============================================
def test_structured_surface_capability_needs_dom_svg() -> None:
	"""An object with structured_surface capability requires DOM SVG."""
	obj = {"capabilities": ["structured_surface"]}
	assert gen_svg_manifest._object_needs_dom_svg(obj) is True


#============================================
def test_clickable_only_img_eligible_states_does_not_need_dom_svg() -> None:
	"""An object with only clickable capability and img-eligible states is False."""
	obj = {
		"capabilities": ["clickable"],
		"visual_states": {
			"selected": {"kind": "overlay"},
			"default": {"kind": "svg", "asset_name": "bottle_green"},
		},
	}
	assert gen_svg_manifest._object_needs_dom_svg(obj) is False
