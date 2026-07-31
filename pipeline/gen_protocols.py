#!/usr/bin/env python3
"""
Codegen for protocol index and protocol config from content/protocols.

Reads all protocol.yaml files from:
- content/protocols/<cluster>/<protocol_name>/protocol.yaml

Validates against the closed protocol schema per PRIMARY_SPEC.md and
PROTOCOL_VOCABULARY.md. Emits generated/protocols.ts with two named exports:
- PROTOCOLS: Readonly<Record<string, ProtocolConfig>>
- PROTOCOLS_INDEX: ReadonlyArray<ProtocolIndexEntry>

Validation:
- protocol_type is one of: mini_protocol, sequence_runner
- protocol_name is present and is a string
- entry_step is present and matches a step_name
- mini_protocol and sequence_runner require a learning block
- steps array is present for mini_protocol
- sequence array is present for sequence_runner
- every step carries step_name, prompt, sequence, step_validator, outcome, next_step
- every interaction carries target, gesture, validator, response
- gesture is one of: click, drag, adjust, select, type
- validator preset is one of: correct_target, correct_choice, target_with_value,
  sequence_complete, final_state_matches
- outcome.on_success is "complete" and outcome.on_failure is "retry"
- scene_operations are valid (discriminated by type field)
- unknown top-level fields raise an error, enforced by invoking the canonical
  closure check in validation/yaml_schema/protocol_validator.py
  (ProtocolValidator.validate_closure, backed by PROTOCOL_ALL_KEYS in
  validation/yaml_schema/constants.py). This is the single schema source for
  top-level key closure; the checks below do not re-derive their own
  allow-list.
- missing required fields raise an error

Output ordering: PROTOCOLS_INDEX sorted by cluster then protocol_name (deterministic).
"""

# Standard Library
import os
import re
import subprocess
from pathlib import Path

# PIP3 modules
import yaml

# Cross-package import: the canonical protocol closure check lives in
# validation/yaml_schema/, a sibling top-level directory to pipeline/.
# pipeline/build_generated.sh exports PYTHONPATH with the repo root before
# invoking this script, so the package-qualified import resolves.

# local repo modules
import pipeline.entity_decode
import validation.yaml_schema.protocol_validator
from validation.yaml_schema.database import ContentDatabase

#============================================

#============================================

def get_repo_root() -> str:
	"""Get repository root via git rev-parse --show-toplevel."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=True,
	)
	return result.stdout.strip()


#============================================

def collect_protocols(repo_root: str) -> tuple:
	"""
	Collect all protocol.yaml files from content/protocols.
	Returns a tuple (protocols, protocol_dirs) where:
	  protocols: {protocol_name: (yaml_data, cluster)}
	  protocol_dirs: {protocol_name: absolute path of the protocol package dir}

	The package directory map is returned alongside the protocols dict (rather
	than stored in a module-level global) so the materials emitter can locate
	each package's materials.yaml without hidden temporal coupling. The PROTOCOLS
	tuple shape stays stable for existing unpackers; the dir map travels beside it.
	"""
	protocols = {}
	protocol_dirs = {}

	# Collect curriculum protocols from content/protocols/<cluster>/<name>/
	content_dir = os.path.join(repo_root, "content", "protocols")
	if os.path.isdir(content_dir):
		for cluster in os.listdir(content_dir):
			cluster_path = os.path.join(content_dir, cluster)
			if not os.path.isdir(cluster_path):
				continue
			for protocol_dir in os.listdir(cluster_path):
				protocol_path = os.path.join(cluster_path, protocol_dir)
				if not os.path.isdir(protocol_path):
					continue
				protocol_yaml = os.path.join(protocol_path, "protocol.yaml")
				if os.path.isfile(protocol_yaml):
					with open(protocol_yaml, "r") as f:
						data = yaml.safe_load(f)
					if not isinstance(data, dict):
						raise ValueError(
							f"Protocol YAML must be a mapping: {protocol_yaml}"
						)
					protocol_name = data["protocol_name"]
					protocols[protocol_name] = (data, cluster)
					protocol_dirs[protocol_name] = protocol_path

	return protocols, protocol_dirs


#============================================

def validate_gesture(gesture: str) -> None:
	"""Validate gesture is one of: click, drag, adjust, select, type."""
	valid = {"click", "drag", "adjust", "select", "type"}
	if gesture not in valid:
		raise ValueError(f"Unknown gesture: {gesture}. Must be one of: {valid}")


def validate_validator_preset(preset: str) -> None:
	"""Validate validator preset is one of the ratified presets."""
	valid = {
		"correct_target",
		"correct_choice",
		"target_with_value",
		"sequence_complete",
		"final_state_matches",
	}
	if preset not in valid:
		raise ValueError(
			f"Unknown validator preset: {preset}. Must be one of: {valid}"
		)


def validate_scene_operation(op: dict, protocol_name: str) -> None:
	"""Validate a scene_operation has a valid type."""
	if not isinstance(op, dict):
		raise ValueError(
			f"Protocol {protocol_name}: scene_operation is not a dict: {op}"
		)

	op_type = op["type"]
	if not op_type:
		raise ValueError(
			f"Protocol {protocol_name}: scene_operation missing type field"
		)

	valid_types = {
		"ObjectStateChange",
		"CursorAttach",
		"SceneChange",
		"LayoutMove",
		"TimedWait",
	}
	if op_type not in valid_types:
		raise ValueError(
			f"Protocol {protocol_name}: unknown scene_operation type: {op_type}"
		)


def validate_interaction(interaction: dict, protocol_name: str) -> None:
	"""Validate an interaction has all four required slots."""
	required_slots = {"target", "gesture", "validator", "response"}
	missing = required_slots - set(interaction.keys())
	if missing:
		raise ValueError(
			f"Protocol {protocol_name}: interaction missing slots: {missing}"
		)

	validate_gesture(interaction["gesture"])

	validator = interaction["validator"]
	if not isinstance(validator, dict):
		raise ValueError(
			f"Protocol {protocol_name}: validator is not a dict: {validator}"
		)
	if "preset" not in validator:
		raise ValueError(
			f"Protocol {protocol_name}: validator missing preset field"
		)
	validate_validator_preset(validator["preset"])

	response = interaction["response"]
	if not isinstance(response, dict):
		raise ValueError(
			f"Protocol {protocol_name}: response is not a dict: {response}"
		)
	if "scene_operations" not in response:
		raise ValueError(
			f"Protocol {protocol_name}: response missing scene_operations"
		)
	scene_ops = response["scene_operations"]
	if not isinstance(scene_ops, list):
		raise ValueError(
			f"Protocol {protocol_name}: scene_operations is not a list: {scene_ops}"
		)
	for op in scene_ops:
		validate_scene_operation(op, protocol_name)


def validate_step(step: dict, protocol_name: str, all_step_names: set) -> None:
	"""Validate a step has all six required slots."""
	required_slots = {
		"step_name",
		"prompt",
		"sequence",
		"step_validator",
		"outcome",
		"next_step",
	}
	missing = required_slots - set(step.keys())
	if missing:
		raise ValueError(
			f"Protocol {protocol_name}: step missing slots: {missing}"
		)

	step_name = step["step_name"]
	all_step_names.add(step_name)

	sequence = step["sequence"]
	if not isinstance(sequence, list):
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} sequence is not a list"
		)
	for interaction in sequence:
		validate_interaction(interaction, protocol_name)

	step_validator = step["step_validator"]
	if not isinstance(step_validator, dict):
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} step_validator is not a dict"
		)
	if "preset" not in step_validator:
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} step_validator missing preset"
		)
	validate_validator_preset(step_validator["preset"])

	outcome = step["outcome"]
	if not isinstance(outcome, dict):
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} outcome is not a dict"
		)
	if outcome["on_success"] != "complete":
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} outcome.on_success must be 'complete'"
		)
	if outcome["on_failure"] != "retry":
		raise ValueError(
			f"Protocol {protocol_name}: step {step_name} outcome.on_failure must be 'retry'"
		)


def enforce_top_level_closure(protocol_data: dict, path: str) -> None:
	"""
	Enforce top-level protocol key closure by invoking the canonical
	validator (validation/yaml_schema/protocol_validator.py), the single
	schema source for PROTOCOL_ALL_KEYS. Raises ValueError naming every
	unknown/escape-hatch top-level field so the always-run build fails
	loudly instead of silently accepting it.
	"""
	validator = validation.yaml_schema.protocol_validator.ProtocolValidator()
	closure_findings = validator.validate_closure(protocol_data, path)
	if closure_findings:
		messages = "; ".join(finding.format() for finding in closure_findings)
		raise ValueError(f"Protocol closure violation: {messages}")


def validate_protocol(
	protocol_data: dict, cluster: str, path: str, all_protocols: dict | None = None,
	db: ContentDatabase | None = None,
) -> None:
	"""Validate a protocol against the closed schema."""
	enforce_top_level_closure(protocol_data, path)

	required_top = {"protocol_type", "protocol_name", "entry_step"}
	missing = required_top - set(protocol_data.keys())
	if missing:
		raise ValueError(
			f"Protocol missing required top-level fields: {missing}"
		)

	protocol_type = protocol_data["protocol_type"]
	valid_types = {"mini_protocol", "sequence_runner"}
	if protocol_type not in valid_types:
		raise ValueError(
			f"Unknown protocol_type: {protocol_type}. Must be one of: {valid_types}"
		)

	protocol_name = protocol_data["protocol_name"]
	if all_protocols is None:
		all_protocols = {}
	if not isinstance(protocol_name, str):
		raise ValueError(f"protocol_name must be a string, got: {protocol_name}")

	entry_step = protocol_data["entry_step"]
	if not isinstance(entry_step, str):
		raise ValueError(f"entry_step must be a string, got: {entry_step}")

	# Learning block required for mini_protocol and sequence_runner
	if protocol_type in {"mini_protocol", "sequence_runner"}:
		if "learning" not in protocol_data:
			raise ValueError(
				f"Protocol {protocol_name}: {protocol_type} requires learning block"
			)
		learning = protocol_data["learning"]
		if not isinstance(learning, dict):
			raise ValueError(
				f"Protocol {protocol_name}: learning block is not a dict"
			)
		required_learning = {"objectives", "outcomes", "goals"}
		missing_learning = required_learning - set(learning.keys())
		if missing_learning:
			raise ValueError(
				f"Protocol {protocol_name}: learning block missing: {missing_learning}"
			)

	# mini_protocol requires steps
	if protocol_type in {"mini_protocol"}:
		if "steps" not in protocol_data:
			raise ValueError(
				f"Protocol {protocol_name}: {protocol_type} requires steps field"
			)
		steps = protocol_data["steps"]
		if not isinstance(steps, list):
			raise ValueError(
				f"Protocol {protocol_name}: steps is not a list"
			)
		all_step_names = set()
		for step in steps:
			validate_step(step, protocol_name, all_step_names)

		# Validate entry_step names a declared step
		if entry_step not in all_step_names:
			raise ValueError(
				f"Protocol {protocol_name}: entry_step '{entry_step}' does not match any step_name"
			)

		# Validate all next_step references are valid (or null)
		for step in steps:
			next_step = step["next_step"]
			if next_step is not None and next_step not in all_step_names:
				raise ValueError(
					f"Protocol {protocol_name}: step '{step['step_name']}' next_step '{next_step}' does not match any step_name"
				)

	# sequence_runner requires mini_protocols field
	elif protocol_type == "sequence_runner":
		if "mini_protocols" not in protocol_data:
			raise ValueError(
				f"Protocol {protocol_name}: sequence_runner requires mini_protocols field"
			)
		mini_protocols = protocol_data["mini_protocols"]
		if not isinstance(mini_protocols, list):
			raise ValueError(
				f"Protocol {protocol_name}: mini_protocols is not a list"
			)
		if not mini_protocols:
			raise ValueError(
				f"Protocol {protocol_name}: mini_protocols must be non-empty"
			)
		seen_mini_names = set()
		for mini_name in mini_protocols:
			if not isinstance(mini_name, str):
				raise ValueError(
					f"Protocol {protocol_name}: mini_protocols entries must be strings"
				)
			if mini_name in seen_mini_names:
				raise ValueError(
					f"Protocol {protocol_name}: duplicate constituent mini-protocol '{mini_name}'"
				)
			seen_mini_names.add(mini_name)
			if mini_name not in all_protocols:
				raise ValueError(
					f"Protocol {protocol_name}: sequence_runner references missing mini-protocol '{mini_name}'"
				)
			mini_data, _mini_cluster = all_protocols[mini_name]
			if mini_data.get("protocol_type") != "mini_protocol":
				raise ValueError(
					f"Protocol {protocol_name}: sequence_runner must reference direct mini_protocol leaves; "
					f"'{mini_name}' is {mini_data.get('protocol_type')!r}"
				)

	if db is not None:
		initial_state_findings = validation.yaml_schema.protocol_validator.ProtocolValidator(
			db=db
		)._validate_initial_state(protocol_data, path)
		if initial_state_findings:
			messages = "; ".join(finding.format() for finding in initial_state_findings)
			raise ValueError(f"Protocol initial_state violation: {messages}")


#============================================

# Acronyms that must stay uppercase (or hyphenated uppercase) when a
# protocol_name is converted to a display_title. Hard-coded to keep the
# author surface closed: new acronyms require editing this list.
DISPLAY_ACRONYMS = {
	"sdspage": "SDS-PAGE",
	"mtt": "MTT",
	"pbs": "PBS",
	"dmso": "DMSO",
	"hepes": "HEPES",
}


def derive_display_title(protocol_name: str) -> str:
	"""
	Convert snake_case protocol_name to a human-readable display_title.
	Hard-coded acronyms (SDS-PAGE, MTT, PBS, DMSO, HEPES) keep canonical
	casing. The first acronym becomes a leading "ACRONYM:" prefix; remaining
	tokens are Title Case with underscores replaced by spaces.

	Examples:
		sdspage_heat_denature_samples -> "SDS-PAGE: Heat denature samples"
		mtt_plate_reaction            -> "MTT: Plate reaction"
		trypan_blue_counting          -> "Trypan blue counting"
	"""
	tokens = protocol_name.split("_")
	leading_acronym = None
	if tokens and tokens[0] in DISPLAY_ACRONYMS:
		leading_acronym = DISPLAY_ACRONYMS[tokens[0]]
		tokens = tokens[1:]
	# Title-case the remaining tokens; preserve embedded acronyms anywhere
	# in the name (rare but possible).
	rendered_tokens = []
	for i, tok in enumerate(tokens):
		if tok in DISPLAY_ACRONYMS:
			rendered_tokens.append(DISPLAY_ACRONYMS[tok])
		elif i == 0:
			rendered_tokens.append(tok.capitalize())
		else:
			rendered_tokens.append(tok)
	rest = " ".join(rendered_tokens)
	if leading_acronym is None:
		return rest
	if rest == "":
		return leading_acronym
	return f"{leading_acronym}: {rest}"


def emit_protocols_index_slim_ts(repo_root: str, protocols: dict) -> None:
	"""
	Emit generated/protocols_index_slim.ts. Slim launcher-only metadata:
	{protocol_name, cluster, display_title, learning_goal_hook}. The full
	protocol surface (steps, sequences, validators, scene operations) lives
	in generated/protocols.ts and is loaded only by the protocol_host bundle.
	"""
	generated_dir = os.path.join(repo_root, "generated")
	os.makedirs(generated_dir, exist_ok=True)
	output_path = os.path.join(generated_dir, "protocols_index_slim.ts")

	ts_lines = []
	ts_lines.append(
		"// AUTO-GENERATED by pipeline/gen_protocols.py. Do not edit by hand."
	)
	ts_lines.append("")
	ts_lines.append(
		"import type { ProtocolIndexSlimEntry } from '../src/shell/adapter/types';"
	)
	ts_lines.append("")
	ts_lines.append(
		"// Slim launcher metadata. Sorted by cluster then protocol_name."
	)
	ts_lines.append(
		"export const PROTOCOLS_INDEX_SLIM: ReadonlyArray<ProtocolIndexSlimEntry> = ["
	)

	index_entries = []
	for protocol_name, (protocol_data, cluster) in protocols.items():
		learning_goal_hook = extract_learning_hook(protocol_data.get("learning"))
		display_title = derive_display_title(protocol_name)
		# protocol_type is required at this point; validation has already run.
		# Use dict[key] not .get to fail loudly if it's missing.
		protocol_type = protocol_data["protocol_type"]
		step_count = compute_step_count(protocol_data, protocols)
		index_entries.append(
			(cluster, protocol_name, display_title, learning_goal_hook, protocol_type, step_count)
		)

	index_entries.sort()

	for cluster, protocol_name, display_title, learning_goal_hook, protocol_type, step_count in index_entries:
		ts_lines.append(
			f"\t{{ protocol_name: '{protocol_name}', cluster: '{cluster}', "
			f"display_title: {to_ts_literal(display_title)}, "
			f"learning_goal_hook: {to_ts_literal(learning_goal_hook)}, "
			f"protocol_type: '{protocol_type}', "
			f"step_count: {step_count} }},"
		)

	ts_lines.append("] as const;")

	with open(output_path, "w") as f:
		f.write("\n".join(ts_lines) + "\n")

	print(f"Generated: {output_path}")


def compute_step_count(protocol_data: dict, all_protocols: dict) -> int:
	"""
	Compute the step count for a protocol.
	- mini_protocol: length of the `steps` list
	- sequence_runner: sum of step counts of constituent mini-protocols
	If a constituent mini-protocol is missing, raise loudly so the
	authoring surface stays closed.
	"""
	protocol_type = protocol_data["protocol_type"]
	if protocol_type == "mini_protocol":
		steps = protocol_data["steps"]
		return len(steps)
	if protocol_type == "sequence_runner":
		mini_names = protocol_data["mini_protocols"]
		total = 0
		for mini_name in mini_names:
			if mini_name not in all_protocols:
				raise ValueError(
					f"sequence_runner references missing mini-protocol: {mini_name}"
				)
			mini_data, _cluster = all_protocols[mini_name]
			# Recurse one level (a sequence_runner referencing another
			# sequence_runner is not in scope; mini-protocols only).
			if mini_data["protocol_type"] != "mini_protocol":
				raise ValueError(
					f"sequence_runner must reference mini_protocol entries; "
					f"got {mini_data['protocol_type']} for {mini_name}"
				)
			total += len(mini_data["steps"])
		return total
	# Unknown protocol_type: caller should not have reached here.
	raise ValueError(f"compute_step_count: unsupported protocol_type {protocol_type}")


LEARNING_HOOK_MAX_LENGTH = 128
LEARNING_OUTCOME_PREFIXES = (
	"Students completing this mini-protocol will be able to",
	"Students completing this protocol will be able to",
)


def normalize_learning_text(value: str) -> str:
	"""Collapse authored line wrapping into one launcher-card line."""
	normalized = " ".join(value.split())
	return normalized


def strip_learning_outcome_prefix(outcome: str) -> str:
	"""Remove an exact required learning-block lead-in when it is present."""
	for prefix in LEARNING_OUTCOME_PREFIXES:
		if outcome == prefix:
			return ""
		if outcome.startswith(f"{prefix} "):
			stripped = outcome[len(prefix):].strip()
			return stripped
	return outcome


def first_complete_sentence(text: str) -> str:
	"""Keep the first authored sentence when its terminal punctuation is present."""
	match = re.search(r"[.!?]+(?=\s|$)", text)
	if match is None:
		return text
	first_sentence = text[:match.end()]
	return first_sentence


def truncate_learning_hook(text: str) -> str:
	"""Bound a hook at a word boundary while making omitted text explicit."""
	if len(text) <= LEARNING_HOOK_MAX_LENGTH:
		return text
	words = text.split()
	truncated_words = []
	for word in words:
		candidate_words = [*truncated_words, word]
		candidate = " ".join(candidate_words)
		if len(candidate) + 3 > LEARNING_HOOK_MAX_LENGTH:
			break
		truncated_words = candidate_words
	if not truncated_words:
		return "..."
	hook = " ".join(truncated_words) + "..."
	return hook


def extract_learning_hook(learning: dict | None) -> str | None:
	"""Extract a concise, outcome-led hook from a protocol learning block."""
	if not isinstance(learning, dict):
		return None
	outcomes = learning.get("outcomes")
	if not isinstance(outcomes, str):
		return None
	normalized = normalize_learning_text(outcomes)
	if normalized == "":
		return None
	stripped = strip_learning_outcome_prefix(normalized)
	if stripped == "":
		return None
	capitalized = stripped[0].upper() + stripped[1:]
	first_sentence = first_complete_sentence(capitalized)
	hook = truncate_learning_hook(first_sentence)
	return hook


def emit_protocols_ts(
	repo_root: str, protocols: dict
) -> None:
	"""
	Emit generated/protocols.ts with PROTOCOLS and PROTOCOLS_INDEX exports.
	"""
	generated_dir = os.path.join(repo_root, "generated")
	os.makedirs(generated_dir, exist_ok=True)

	output_path = os.path.join(generated_dir, "protocols.ts")

	# Build the TypeScript output
	ts_lines = []
	ts_lines.append(
		"// AUTO-GENERATED by pipeline/gen_protocols.py. Do not edit by hand."
	)
	ts_lines.append("")
	ts_lines.append(
		"import type { ProtocolConfig, ProtocolIndexEntry } from '../src/shell/adapter/types';"
	)
	ts_lines.append("")
	ts_lines.append(
		"// All protocols (mini_protocol and sequence_runner), for validation and testing."
	)
	ts_lines.append(
		"export const PROTOCOLS: Readonly<Record<string, ProtocolConfig>> = {"
	)

	for protocol_name in sorted(protocols.keys()):
		protocol_data, cluster = protocols[protocol_name]
		ts_lines.append(f"\t{protocol_name}: {to_ts_literal(protocol_data)},")

	ts_lines.append("} as const;")
	ts_lines.append("")
	ts_lines.append(
		"// Student-visible protocol index. Sorted by cluster then protocol_name."
	)
	ts_lines.append(
		"export const PROTOCOLS_INDEX: ReadonlyArray<ProtocolIndexEntry> = ["
	)

	# Build index: sort by cluster then protocol_name
	index_entries = []
	for protocol_name, (protocol_data, cluster) in protocols.items():
		learning_hook = extract_learning_hook(protocol_data.get("learning"))
		index_entries.append((cluster, protocol_name, learning_hook))

	index_entries.sort()

	for cluster, protocol_name, learning_hook in index_entries:
		protocol_data, _cluster = protocols[protocol_name]
		protocol_type = protocol_data["protocol_type"]
		ts_lines.append(
			f"\t{{ protocol_name: '{protocol_name}', cluster: '{cluster}', protocol_type: '{protocol_type}', learning_hook: {to_ts_literal(learning_hook)} }},"
		)

	ts_lines.append("] as const;")

	# Write to file
	with open(output_path, "w") as f:
		f.write("\n".join(ts_lines) + "\n")

	print(f"Generated: {output_path}")


def to_ts_literal(value: object) -> str:
	"""Convert a Python value to a TypeScript literal."""
	if value is None:
		return "null"
	if isinstance(value, bool):
		return "true" if value else "false"
	if isinstance(value, str):
		# Decode authored HTML entities (e.g. &micro;) to their Unicode
		# glyph before emission, so generated/protocols.ts carries the real
		# character and the runtime renders it as a normal DOM text node.
		# This is the single point every string field (prompt, learning
		# text, display_title, learning hooks) routes through on its way
		# into protocols.ts, so decoding here covers all of them at once.
		decoded = pipeline.entity_decode.decode_entities(value)
		# Escape backslashes, newlines, and quotes
		escaped = (decoded
			.replace("\\", "\\\\")
			.replace("\n", "\\n")
			.replace("\r", "\\r")
			.replace('"', '\\"')
		)
		return f'"{escaped}"'
	if isinstance(value, (int, float)):
		return str(value)
	if isinstance(value, dict):
		items = []
		for k, v in value.items():
			items.append(f"{k}: {to_ts_literal(v)}")
		return f"{{ {', '.join(items)} }}"
	if isinstance(value, list):
		items = [to_ts_literal(v) for v in value]
		return f"[{', '.join(items)}]"
	raise TypeError(f"Cannot convert {type(value)} to TypeScript literal: {value}")


#============================================

def load_package_materials(protocol_name: str, protocol_dirs: dict) -> dict:
	"""
	Read one protocol package's materials.yaml and return its materials map.
	Returns an empty dict when the package has no materials.yaml (a protocol may
	declare no materials). The map is {material_name: {label, display_color}},
	where display_color is a single scalar hex string (no nested light/dark).

	protocol_dirs must contain protocol_name; a missing key is a bug (the caller
	resolved this name from the same protocols dict), so index directly and let a
	KeyError fail loud rather than masking it with a default.
	"""
	package_dir = protocol_dirs[protocol_name]
	materials_path = os.path.join(package_dir, "materials.yaml")
	if not os.path.isfile(materials_path):
		return {}
	with open(materials_path, "r") as f:
		data = yaml.safe_load(f)
	if not isinstance(data, dict):
		raise ValueError(f"materials.yaml must be a mapping: {materials_path}")
	# materials.yaml top-level shape is {materials: {name: {...}}}.
	materials = data.get("materials", {})
	if not isinstance(materials, dict):
		raise ValueError(f"materials.yaml 'materials' must be a mapping: {materials_path}")
	return materials


def resolve_protocol_materials(
	protocol_name: str, protocols: dict, protocol_dirs: dict
) -> dict:
	"""
	Resolve the material registry for one protocol. A mini_protocol uses its
	own package materials.yaml. A sequence_runner aggregates the materials of
	its constituent mini-protocols (each per-package, merged by material_name;
	later minis win on a name collision, which is fine since the same
	material_name carries the same definition by convention).
	"""
	protocol_data, _cluster = protocols[protocol_name]
	protocol_type = protocol_data["protocol_type"]
	if protocol_type == "sequence_runner":
		merged: dict = {}
		for mini_name in protocol_data.get("mini_protocols", []):
			if mini_name in protocols:
				merged.update(load_package_materials(mini_name, protocol_dirs))
		return merged
	return load_package_materials(protocol_name, protocol_dirs)


def emit_protocol_materials_ts(
	repo_root: str, protocols: dict, protocol_dirs: dict
) -> None:
	"""
	Emit generated/protocol_materials.ts: PROTOCOL_MATERIALS keyed by
	protocol_name. Each value is a MaterialRegistry (material_name -> {label,
	display_color}), where display_color is a single scalar hex string (the
	light-only schema in docs/specs/MATERIAL_YAML_FORMAT.md; no nested
	light/dark split). Protocols with no materials emit an empty
	registry entry so the lookup is total and the consumer can use
	PROTOCOL_MATERIALS[name] ?? null without a separate presence check.

	The registry is PER PROTOCOL, never a global table: a protocol reads only its
	own entry. See docs/specs/MATERIAL_CONVENTION.md.
	"""
	generated_dir = os.path.join(repo_root, "generated")
	os.makedirs(generated_dir, exist_ok=True)
	output_path = os.path.join(generated_dir, "protocol_materials.ts")

	ts_lines = []
	ts_lines.append("// AUTO-GENERATED by pipeline/gen_protocols.py. Do not edit by hand.")
	ts_lines.append("")
	ts_lines.append(
		"import type { MaterialRegistry } from '../src/scene_runtime/renderer/visual_state_resolver';"
	)
	ts_lines.append("")
	ts_lines.append(
		"// Per-protocol material registry (each protocol package's materials.yaml)."
	)
	ts_lines.append(
		"// Keyed by protocol_name; never read as a global table."
	)
	ts_lines.append(
		"export const PROTOCOL_MATERIALS: Readonly<Record<string, MaterialRegistry>> = {"
	)

	for protocol_name in sorted(protocols.keys()):
		materials = resolve_protocol_materials(protocol_name, protocols, protocol_dirs)
		# Normalize each entry to the MaterialEntry shape {label, display_color}.
		normalized = {}
		for mat_name in sorted(materials.keys()):
			entry = materials[mat_name]
			if not isinstance(entry, dict):
				raise ValueError(
					f"Protocol {protocol_name}: material '{mat_name}' is not a mapping"
				)
			label = entry["label"]
			# display_color is a single scalar hex string (^#[0-9a-f]{6}$) per
			# docs/specs/MATERIAL_YAML_FORMAT.md. The project targets light
			# workspaces only; there is no nested light/dark split. Index it
			# directly as a required key so a missing field fails loud.
			display_color = entry["display_color"]
			if not isinstance(display_color, str):
				raise ValueError(
					f"Protocol {protocol_name}: material '{mat_name}' display_color "
					f"must be a scalar hex string, got {type(display_color).__name__}"
				)
			normalized[mat_name] = {
				"label": label,
				"display_color": display_color,
			}
		ts_lines.append(f"\t{protocol_name}: {to_ts_literal(normalized)},")

	ts_lines.append("} as const;")

	with open(output_path, "w") as f:
		f.write("\n".join(ts_lines) + "\n")

	print(f"Generated: {output_path}")


#============================================

def main() -> None:
	"""Main entry point."""
	repo_root = get_repo_root()

	protocols, protocol_dirs = collect_protocols(repo_root)

	if not protocols:
		raise RuntimeError("No protocols found in content/protocols")

	db = ContentDatabase()
	db.load_from_tree(Path(repo_root))

	for protocol_name, (protocol_data, cluster) in protocols.items():
		protocol_path = os.path.join(protocol_dirs[protocol_name], "protocol.yaml")
		protocol_rel_path = os.path.relpath(protocol_path, repo_root)
		validate_protocol(protocol_data, cluster, protocol_rel_path, protocols, db)

	emit_protocols_ts(repo_root, protocols)
	emit_protocols_index_slim_ts(repo_root, protocols)
	emit_protocol_materials_ts(repo_root, protocols, protocol_dirs)


if __name__ == "__main__":
	main()
