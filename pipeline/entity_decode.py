"""
Codegen helper that decodes HTML entities in authored YAML strings to their
Unicode characters before emission into generated/**.

Authors write ASCII HTML entities in YAML (the git-committed source stays
ASCII, per docs/specs/MATERIAL_YAML_FORMAT.md). decode_entities turns each
entity into its Unicode character so codegen can emit a real glyph into
generated/**, which the runtime then renders as a normal DOM text node (never
innerHTML). This is a closed-set dictionary lookup, not XML entity expansion,
so it carries no XXE risk.

An entity not in the named map and not a valid numeric form is left verbatim
in the output, a visible and safe pass-through.
"""

import re

# Named entity to Unicode codepoint map. Codepoints are built via chr() from
# their hex value rather than written as literal glyphs, so this source file
# stays ASCII-only per PYTHON_STYLE.md. Extend only with cause: every addition
# should correspond to a real authored need.
NAMED_ENTITY_CODEPOINTS = {
	"micro": 0x00B5,
	"sim": 0x223C,
	"alpha": 0x03B1,
	"beta": 0x03B2,
	"gamma": 0x03B3,
	"delta": 0x03B4,
	"mu": 0x03BC,
	"deg": 0x00B0,
	"plusmn": 0x00B1,
	"times": 0x00D7,
	"rarr": 0x2192,
	"larr": 0x2190,
	"amp": 0x0026,
	"lt": 0x003C,
	"gt": 0x003E,
	"quot": 0x0022,
	"apos": 0x0027,
}

NAMED_ENTITIES = {name: chr(codepoint) for name, codepoint in NAMED_ENTITY_CODEPOINTS.items()}

# Matches a named entity (&name;), a decimal numeric entity (&#NNN;), or a hex
# numeric entity (&#xHH; or &#XHH;). Numeric groups are captured separately so
# the replacement callback knows which base to parse with.
ENTITY_PATTERN = re.compile(r"&(?:([a-zA-Z]+)|#([0-9]+)|#[xX]([0-9a-fA-F]+));")


def decode_entities(s: str) -> str:
	"""
	Decode HTML entities in `s` to their Unicode characters.

	Handles named entities from NAMED_ENTITIES (each decoded exactly once, so
	`&amp;` never double-decodes into `&amp` plus a stray character) and both
	decimal (`&#181;`) and hex (`&#xB5;`) numeric entities via chr(int(...)).
	A named entity absent from NAMED_ENTITIES is left verbatim in the output.

	Args:
		s: the authored string, possibly containing HTML entities.

	Returns:
		The string with every recognized entity replaced by its Unicode
		character; unrecognized named entities are left untouched.
	"""
	def replace_one(match: re.Match) -> str:
		# Group 1 is a named entity; groups 2/3 are decimal/hex numeric forms.
		named, decimal, hexadecimal = match.group(1), match.group(2), match.group(3)
		if named is not None:
			# Unknown named entities pass through verbatim (the full match,
			# including the & and ;), rather than being silently dropped.
			return NAMED_ENTITIES.get(named, match.group(0))
		if decimal is not None:
			return chr(int(decimal))
		return chr(int(hexadecimal, 16))

	decoded = ENTITY_PATTERN.sub(replace_one, s)
	return decoded


#============================================

def decode_entity_values(value: object) -> object:
	"""Decode entities in every string value of one parsed YAML tree."""
	if isinstance(value, str):
		decoded = decode_entities(value)
		return decoded
	if isinstance(value, list):
		decoded_list = [decode_entity_values(item) for item in value]
		return decoded_list
	if isinstance(value, dict):
		decoded_mapping = {
			key: decode_entity_values(item)
			for key, item in value.items()
		}
		return decoded_mapping
	return value
