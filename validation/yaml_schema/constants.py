"""Spec-derived closed sets and schema constants with citations.

Finding tag registry (used by validators that reference these constants):

	T1_TARGET             interaction target does not resolve to a declared
	                      object or subpart.
	T1_STATE_FIELD        ObjectStateChange names a state field not declared
	                      on the target object.
	T1_ENUM               enum state field receives a value outside the
	                      declared `allowed` list.
	T1_MATERIAL_REF       material_name / held_material_name does not resolve
	                      to an entry in the protocol's materials.yaml.
	T1_TARGET_WITH_VALUE  target_with_value validator names a key that is
	                      not a declared state field on the target.
	SCENE_EXTENDS         protocol scene extends an unknown base scene name.
	CLOSURE               unknown top-level key in a closed-schema container.
	T3_CAMELCASE          authored YAML key contains a camelCase boundary.
	RETIRED               (reserved) retired-token error class.
	BANNED                (reserved) banned-token error class.

T1_* checks live in tools/validators/protocol_validator.py.
SCENE_EXTENDS lives in tools/validators/scene_protocol_validator.py.
CLOSURE lives in each per-container validator.
T3_CAMELCASE lives in tools/validators/cross_protocol.py.
"""

# ============================================
# OBJECT SCHEMA CONSTANTS
# ============================================

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Object identity"
OBJECT_KINDS = {'plate', 'bottle', 'flask', 'pipette', 'rack', 'waste', 'equipment', 'decoration'}

# spec: docs/specs/OBJECT_VOCABULARY.md "Capabilities"
OBJECT_CAPABILITIES = {
	'clickable',
	'material_container',
	'instrument_with_setpoint',
	'structured_surface',
	'cursor_attachable',
	'decoration_only',
}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Top-level fields"
# Closure: unknown top-level keys are flagged automatically. No retired-key list needed.
OBJECT_REQUIRED_KEYS = {'object_name', 'kind', 'label', 'state_fields', 'visual_states', 'capabilities', 'layout'}
OBJECT_OPTIONAL_KEYS = {'structure', 'channel_addressing'}
OBJECT_ALL_KEYS = OBJECT_REQUIRED_KEYS | OBJECT_OPTIONAL_KEYS

# spec: docs/specs/OBJECT_YAML_FORMAT.md "state_fields"
STATE_FIELD_TYPES = {'enum', 'int', 'float', 'bool'}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Structure.subpart_kind"
STRUCTURE_SUBPART_KINDS = {'well', 'tube', 'lane', 'slot', 'channel'}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Structure.layout"
STRUCTURE_LAYOUT_TYPES = {'grid', 'list', 'custom'}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Subpart groups"
SUBPART_GROUP_KINDS = {'row', 'column', 'region'}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Channel addressing"
# Note: region is NOT allowed in addressable_subpart_kinds per spec
CHANNEL_ADDRESSABLE_KINDS = {'well', 'row', 'column'}

# spec: docs/specs/OBJECT_YAML_FORMAT.md "Kind-to-material-field convention" (lines 253-275)
# Maps kind to the required material field name(s).
# - pipette: held_material_name (tool semantics)
# - bottle, flask, waste: material_name (vessel semantics)
# - rack, plate: material_name (per subpart)
# - equipment: case-by-case (review required)
# - decoration: no material fields allowed
KIND_MATERIAL_FIELD_CONVENTION = {
	'pipette': 'held_material_name',
	'bottle': 'material_name',
	'flask': 'material_name',
	'waste': 'material_name',
	'rack': 'material_name',
	'plate': 'material_name',
	'equipment': None,  # case-by-case (triggers WARNING)
	'decoration': None,  # no material fields allowed (triggers ERROR if any found)
}


# ============================================
# SCENE SCHEMA CONSTANTS
# ============================================

# spec: docs/specs/SCENE_YAML_FORMAT.md "Top-level fields"
BASE_SCENE_REQUIRED_KEYS = {'scene_name', 'workspace', 'capabilities', 'zones', 'placements'}
BASE_SCENE_OPTIONAL_KEYS = {'background', 'layout_rules', 'accent_rules', 'wrong_order_message'}
BASE_SCENE_ALL_KEYS = BASE_SCENE_REQUIRED_KEYS | BASE_SCENE_OPTIONAL_KEYS


# spec: docs/specs/SCENE_YAML_FORMAT.md "Layout rules" and docs/specs/SCENE_VOCABULARY.md "label_placement"
# Closed enum for scene-wide and per-placement label position.
# Default is 'top' (resolved in the layout engine, not the validator).
LABEL_PLACEMENT_VALUES = {'top', 'bottom'}
ALIGN_STOP_VALUES = {'left', 'center', 'right'}

# Closure handles unknown keys; BASE_SCENE_ALL_KEYS is the canonical whitelist.

# spec: docs/specs/SCENE_INHERITANCE.md "Protocol-scene schema (closed)"
PROTOCOL_SCENE_ALLOWED_KEYS = {
	'scene_name', 'extends', 'add_placements', 'reposition_placements',
	'deactivate_placements', 'remove_placements', 'scene_notes'
}

# spec: docs/specs/SCENE_INHERITANCE.md "Locked fields within placements"
PLACEMENT_LOCKED_FIELDS = {
	'label', 'kind', 'state_fields', 'visual_states', 'capabilities'
}

# spec: docs/specs/SCENE_INHERITANCE.md "Reposition operations"
REPOSITION_ALLOWED_FIELDS = {'placement_name', 'zone', 'depth', 'depth_tier', 'align_stop'}


# ============================================
# PROTOCOL SCHEMA CONSTANTS
# ============================================

# spec: docs/PRIMARY_SPEC.md "Protocol types"
PROTOCOL_TYPES = {'protocol', 'mini_protocol', 'sequence_runner'}

# spec: docs/PRIMARY_SPEC.md "Gestures"
VALID_GESTURES = {'click', 'drag', 'adjust', 'select', 'type'}

# spec: docs/PRIMARY_SPEC.md "Scene operations"
VALID_SCENE_OPERATIONS = {'ObjectStateChange', 'CursorAttach', 'SceneChange', 'LayoutMove', 'TimedWait'}

# spec: docs/specs/PROTOCOL_VOCABULARY.md "Validator preset library"
INTERACTION_VALIDATOR_PRESETS = {'correct_target', 'correct_choice', 'target_with_value'}

# spec: docs/specs/PROTOCOL_VOCABULARY.md "Validator preset library"
STEP_VALIDATOR_PRESETS = {'sequence_complete', 'final_state_matches'}

# spec: docs/PRIMARY_SPEC.md "Validators and outcome"
# spec: docs/specs/SPEC_DESIGN_CHECKLIST.md "Bare name banned"
# Closure: unknown top-level keys are flagged automatically. CamelCase keys are
# caught by the general T3_CAMELCASE regex in cross_protocol.py. No retired
# allow-list maintained.
#
# Required-key set is universal across protocol types; `steps` vs
# `mini_protocols` is enforced per type by ProtocolValidator (sequence_runner
# carries an ordered constituent list instead of authored steps, per
# docs/PRIMARY_SPEC.md "Sequence runners").
PROTOCOL_REQUIRED_KEYS = {'protocol_type', 'protocol_name', 'entry_step', 'learning'}
PROTOCOL_OPTIONAL_KEYS = {'parts', 'days', 'steps', 'mini_protocols', 'initial_state'}
PROTOCOL_ALL_KEYS = PROTOCOL_REQUIRED_KEYS | PROTOCOL_OPTIONAL_KEYS

# spec: docs/PRIMARY_SPEC.md "Learning block"
# Learning prefix requirements per PRIMARY_SPEC.md for mini_protocol
LEARNING_MINI_PROTOCOL_PREFIXES = {
	'objectives': 'Students completing this mini-protocol will have achieved',
	'outcomes': 'Students completing this mini-protocol will be able to',
	'goals': 'Overall, this mini-protocol aims to accomplish',
}

# spec: docs/PRIMARY_SPEC.md "Learning block"
# Learning prefix requirements per PRIMARY_SPEC.md for sequence_runner
LEARNING_SEQUENCE_RUNNER_PREFIXES = {
	'objectives': 'Students completing this protocol will have achieved',
	'outcomes': 'Students completing this protocol will be able to',
	'goals': 'Overall, this protocol aims to accomplish',
}


# ============================================
# MATERIAL SCHEMA CONSTANTS
# ============================================

# spec: docs/specs/MATERIAL_YAML_FORMAT.md "Material entry schema"
MATERIAL_REQUIRED_KEYS = {'label', 'display_color'}
MATERIAL_OPTIONAL_KEYS = set()
MATERIAL_ALL_KEYS = MATERIAL_REQUIRED_KEYS | MATERIAL_OPTIONAL_KEYS


# ============================================
# SCENE OPERATION SCHEMAS (TIER 2)
# ============================================

# spec: docs/specs/PROTOCOL_VOCABULARY.md "Scene operation primitives"
# Each scene_operation primitive is named with its typed fields. The five
# ratified primitives are ObjectStateChange, CursorAttach, SceneChange,
# LayoutMove, and TimedWait.
SCENE_OPERATION_SCHEMA = {
	'ObjectStateChange': {
		'required': {'type', 'target', 'state'},
		'optional': {'transition'},
		'description': 'Mutate declared object state_fields (flat mapping). state: {field: value}. transition: instant|animated.',
	},
	'CursorAttach': {
		'required': {'type', 'target', 'operation'},
		'optional': set(),
		'description': 'Set runtime held-material state. operation: attach|detach.',
	},
	'SceneChange': {
		'required': {'type', 'to_scene'},
		'optional': set(),
		'description': 'Transition runtime active scene id.',
	},
	'LayoutMove': {
		'required': {'type', 'target', 'to_slot'},
		'optional': {'to_scene'},
		'description': 'Move object placement. to_slot: layout slot name. to_scene: optional for cross-scene moves.',
	},
	'TimedWait': {
		'required': {'type', 'target', 'duration_min', 'display'},
		'optional': set(),
		'description': 'Advance equipment timed phase. duration_min: milliseconds. display: authoring hint for render layer (not SVG id).',
	},
}

# spec: docs/specs/PROTOCOL_VOCABULARY.md "Validator preset library"
# Each validator preset has required and optional fields.
VALIDATOR_PRESET_SCHEMA = {
	'correct_target': {
		'required': {'preset'},
		'optional': set(),
		'scope': 'interaction',
		'description': 'The student performed the gesture on the target.',
	},
	'correct_choice': {
		'required': {'preset'},
		'optional': set(),
		'scope': 'interaction',
		'description': 'The student selected the correct answer-choice from a presented set.',
	},
	'target_with_value': {
		'required': {'preset', 'value'},
		'optional': set(),
		'scope': 'interaction',
		'description': 'The student performed the gesture on the target and target reached the named value.',
	},
	'sequence_complete': {
		'required': {'preset'},
		'optional': set(),
		'scope': 'step',
		'description': 'Every interaction in the sequence validated, in order.',
	},
	'final_state_matches': {
		'required': {'preset', 'target', 'contains'},
		'optional': set(),
		'scope': 'step',
		'description': 'After sequence runs, named target is in state described by contains.',
	},
}

# spec: docs/specs/PROTOCOL_VOCABULARY.md "Gesture/validator coupling"
# Each gesture pairs with valid interaction-validator presets.
GESTURE_VALIDATOR_MAP = {
	'click': {'correct_target'},
	'drag': {'correct_target'},
	'adjust': {'target_with_value'},
	'select': {'correct_choice'},
	'type': {'target_with_value'},
}


# Vocabulary closure is enforced by closed key whitelists per container
# (OBJECT_ALL_KEYS, BASE_SCENE_ALL_KEYS, PROTOCOL_SCENE_ALLOWED_KEYS,
# PROTOCOL_ALL_KEYS, etc.). camelCase keys are caught by the general
# T3_CAMELCASE regex in cross_protocol.py. No retired-token allow-list.
