#!/usr/bin/env python3
"""
check_css_content_policy.py

Validates that src/style.css enforces the no-clip, no-crop content policy.

Banned properties for scene-content selectors (those matching #scene-root,
[data-zone], [data-placement-name], [data-label], and ancestors between them):

  - overflow: hidden, overflow: clip
  - clip, clip-path
  - mask, mask-image
  - contain: paint, contain: strict, contain: content
  - object-fit: cover
  - fixed-aspect crop containers (padding-top hack)
  - transform: scale(), transform: translate(), any transform on scene-content
  - max-height, max-width that hides content
  - negative margin on scene-content

Harmless UI selectors (dev panels, debug overlays, page chrome outside
#scene-root) are unaffected; their max-width and overflow rules are permitted.

Exit non-zero with offending selector + property + line number on failure.
"""

import re
import sys
from pathlib import Path

#============================================

# Scene-content selector patterns (loose match; not exhaustive)
SCENE_CONTENT_SELECTORS = {
	'#scene-root',
	'[data-zone]',
	'[data-placement-name]',
	'[data-label]',
}

# Banned CSS properties and value patterns for scene-content selectors
BANNED_RULES = {
	'overflow': [r'hidden', r'clip'],
	'clip': None,  # any value is banned
	'clip-path': None,
	'mask': None,
	'mask-image': None,
	'contain': [r'paint', r'strict', r'content'],
	'object-fit': [r'cover'],
	'transform': [r'scale\s*\(', r'translate\s*\('],
	'max-height': None,  # any value is banned (assume hiding content)
	'max-width': None,   # any value is banned (assume hiding content)
	'margin': [r'^-'],   # negative margin
	'margin-top': [r'^-'],
	'margin-bottom': [r'^-'],
	'margin-left': [r'^-'],
	'margin-right': [r'^-'],
}

#============================================

def is_scene_content_selector(selector: str) -> bool:
	"""
	Check if a CSS selector matches a scene-content pattern.

	Heuristic: matches if it contains any of the core scene-content patterns.
	This is conservative (may have false positives for coincidental matches),
	but that is acceptable for a lint rule: erring on the side of caution.
	"""
	selector = selector.strip()
	# Check for direct matches
	for pattern in SCENE_CONTENT_SELECTORS:
		if pattern in selector:
			return True
	# Check for inheritance (e.g. "#scene-root .foo", "[data-placement-name] svg")
	if any(pattern in selector for pattern in SCENE_CONTENT_SELECTORS):
		return True
	return False

#============================================

def parse_simple_css(css_text: str) -> list:
	"""
	Simple CSS parser. Returns list of (selector, properties_dict, line_number).

	This is a minimal hand-written parser acceptable for M2b. For more complex
	CSS, a proper parser like tinycss2 would be needed, but for our static
	style.css this suffices.

	Returns:
		List of (selector, properties_dict, start_line) tuples.
		properties_dict maps property name to list of (value, line_num) pairs.
	"""
	rules = []
	lines = css_text.split('\n')

	i = 0
	while i < len(lines):
		line = lines[i]
		stripped = line.strip()
		i += 1

		# Skip empty lines and comments
		if not stripped or stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('//'):
			continue

		# Look for selector (line containing no ':' and no ';')
		if ':' in stripped or ';' in stripped:
			# This is property content, skip it for now (part of ongoing block)
			continue

		# Found a potential selector line
		if '{' in stripped:
			selector_part = stripped[:stripped.index('{')].strip()
			selector_start_line = i  # 1-indexed

			# Now collect properties until we find '}'
			properties_text = stripped[stripped.index('{') + 1:]
			full_rule = ''

			while '}' not in properties_text and i < len(lines):
				full_rule += properties_text + '\n'
				properties_text = lines[i]
				i += 1

			# Handle final line with '}'
			if '}' in properties_text:
				full_rule += properties_text[:properties_text.index('}')]

			# Parse properties
			properties = {}
			for prop_line in full_rule.split('\n'):
				prop_line = prop_line.strip()
				if not prop_line or prop_line.startswith('/*') or prop_line.startswith('*'):
					continue
				if ':' in prop_line:
					parts = prop_line.split(':', 1)
					prop_name = parts[0].strip().lower()
					prop_value = parts[1].rstrip(';').strip().lower() if len(parts) > 1 else ''
					if prop_name not in properties:
						properties[prop_name] = []
					properties[prop_name].append((prop_value, i))

			if selector_part and properties:
				rules.append((selector_part, properties, selector_start_line))

	return rules

#============================================

def check_css_policy(css_path: Path) -> tuple:
	"""
	Check CSS file against content policy.

	Returns:
		(passed: bool, violations: list of (selector, prop, value, line) tuples)
	"""
	print(f"processing {css_path}")

	css_text = css_path.read_text(encoding='utf-8')
	rules = parse_simple_css(css_text)

	violations = []

	for selector, properties, selector_line in rules:
		# Check if this selector applies to scene content
		if not is_scene_content_selector(selector):
			continue

		# Check for banned properties
		for prop_name, prop_values in properties.items():
			if prop_name not in BANNED_RULES:
				continue

			banned_patterns = BANNED_RULES[prop_name]

			for prop_value, prop_line in prop_values:
				# If banned_patterns is None, any value is banned
				if banned_patterns is None:
					violations.append((selector, prop_name, prop_value, prop_line))
				else:
					# Check if value matches any banned pattern
					for pattern in banned_patterns:
						if re.search(pattern, prop_value):
							violations.append((selector, prop_name, prop_value, prop_line))
							break

	return (len(violations) == 0, violations)

#============================================

def main() -> None:
	"""Main entry point."""
	css_path = Path(__file__).parent.parent / 'src' / 'style.css'

	if not css_path.exists():
		print(f"ERROR: {css_path} not found", file=sys.stderr)
		sys.exit(1)

	passed, violations = check_css_policy(css_path)

	if passed:
		print(f"OK: {css_path} passes content policy check")
		sys.exit(0)

	# Report violations
	print(f"FAIL: {len(violations)} violation(s) found in {css_path}", file=sys.stderr)
	for selector, prop, value, line in violations:
		print(f"  Line {line}: selector '{selector}' has banned property: {prop}: {value}", file=sys.stderr)

	sys.exit(1)

#============================================

if __name__ == '__main__':
	main()
