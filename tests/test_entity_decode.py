"""
Unit tests for pipeline.entity_decode.decode_entities.

Cases are inline literals per PYTEST_STYLE.md; no on-disk fixture file. Values
that carry a decoded glyph are asserted via chr(codepoint) rather than a
literal character, so this test file stays ASCII-only.
"""

import pathlib
import re

import pipeline.entity_decode


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_decode_named_entity_micro() -> None:
	decoded = pipeline.entity_decode.decode_entities("400 &micro;M")
	assert decoded == "400 " + chr(0x00B5) + "M"


def test_decode_numeric_decimal_entity() -> None:
	decoded = pipeline.entity_decode.decode_entities("&#181;")
	assert decoded == chr(181)


def test_decode_numeric_hex_entity() -> None:
	decoded = pipeline.entity_decode.decode_entities("&#xB5;")
	assert decoded == chr(0xB5)


def test_decode_numeric_hex_entity_greek_mu() -> None:
	decoded = pipeline.entity_decode.decode_entities("&#956;")
	assert decoded == chr(956)


def test_decode_amp_does_not_double_decode() -> None:
	decoded = pipeline.entity_decode.decode_entities("Tris &amp; EDTA")
	assert decoded == "Tris & EDTA"


def test_decode_two_entities_in_one_string() -> None:
	decoded = pipeline.entity_decode.decode_entities("&alpha; and &beta;")
	assert decoded == chr(0x03B1) + " and " + chr(0x03B2)


def test_decode_entity_adjacent_to_punctuation() -> None:
	decoded = pipeline.entity_decode.decode_entities("20&micro;L, added.")
	assert decoded == "20" + chr(0x00B5) + "L, added."


def test_decode_unknown_named_entity_passes_through() -> None:
	decoded = pipeline.entity_decode.decode_entities("&notarealentity;")
	assert decoded == "&notarealentity;"


#============================================

def test_decode_entity_values_normalizes_nested_yaml_strings() -> None:
	"""Object enum values and visual cases share the protocol Unicode vocabulary."""
	authored = {
		"state_fields": [{
			"allowed": ["unlabeled", "400 &micro;M"],
			"default": "unlabeled",
		}],
		"visual_states": {"label": {"formula": "value=&micro;M"}},
		"capacity": 1000,
	}

	decoded = pipeline.entity_decode.decode_entity_values(authored)
	micro = chr(0x00B5)

	assert decoded["state_fields"][0]["allowed"][1] == f"400 {micro}M"
	assert decoded["visual_states"]["label"]["formula"] == f"value={micro}M"
	assert decoded["capacity"] == 1000


#============================================

def test_authored_content_uses_entity_micro_units() -> None:
	"""Authored YAML uses HTML entities so codegen owns Unicode decoding."""
	raw_unit_pattern = re.compile(r"\bu(?:M|L)\b")
	violations = []
	for path in sorted((REPO_ROOT / "content").rglob("*.yaml")):
		if raw_unit_pattern.search(path.read_text(encoding="utf-8")):
			violations.append(str(path.relative_to(REPO_ROOT)))

	assert violations == [], "raw uM/uL spellings found: " + ", ".join(violations)
