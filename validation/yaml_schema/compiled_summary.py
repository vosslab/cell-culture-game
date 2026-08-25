"""Compiled summary renderer for validate_content_yaml."""

import validation.shared_toolkit.console
from validation.yaml_schema.summary import _protocol_counts


def aggregate(db: object, protocol_rows: object, protocol_scene_rows: object, material_rows: object, counts_dict: object=None) -> object:
	"""
	Aggregate counts across all four content vocabularies.

	Args:
		db: ContentDatabase instance with objects and base_scenes populated.
		protocol_rows: list of (path: str, data: dict) tuples from protocol.yaml files.
		protocol_scene_rows: list of (path: str, data: dict) tuples from protocol scenes.
		material_rows: list of (path: str, data: dict) tuples from materials.yaml files.
		counts_dict: optional dict with keys 'objects', 'base_scenes', 'protocol_scenes', 'protocols', 'materials'
		             from validate_whole_tree(). If provided, overrides db/rows counts for Files total consistency.

	Returns:
		dict with aggregated counts ready for render().
	"""
	# Use provided counts_dict for totals (ensures Files matches validator terse line)
	# Otherwise fall back to len(db) and len(rows)
	if counts_dict is None:
		counts_dict = {
			'objects': len(db.objects),
			'base_scenes': len(db.base_scenes),
			'protocol_scenes': len(protocol_scene_rows),
			'protocols': len(protocol_rows),
			'materials': len(material_rows),
		}

	counts = {
		'objects': {
			'total': counts_dict['objects'],
			'by_kind': {},
			'with_capabilities': 0,
			'total_state_fields': 0,
			'distinct_capabilities': set(),
		},
		'scenes': {
			'base_count': counts_dict['base_scenes'],
			'protocol_count': counts_dict['protocol_scenes'],
			'workspaces': set(),
			'total_placements': 0,
			'protocol_scene_deltas': {},
		},
		'materials': {
			'file_count': counts_dict['materials'],
			'distinct_names': set(),
			'distinct_colors': set(),
		},
		'protocols': {
			'by_type': {},
			'total_steps': 0,
			'total_interactions': 0,
			'distinct_gestures': set(),
			'distinct_targets': set(),
			'distinct_materials': set(),
			'distinct_scene_ops': set(),
		},
	}

	# Objects aggregation
	for obj_name, obj_data in db.objects.items():
		kind = obj_data.get('kind', 'unknown')
		if kind not in counts['objects']['by_kind']:
			counts['objects']['by_kind'][kind] = 0
		counts['objects']['by_kind'][kind] += 1

		# Count capabilities
		if obj_data.get('capabilities'):
			counts['objects']['with_capabilities'] += 1
			for cap in obj_data.get('capabilities', []):
				counts['objects']['distinct_capabilities'].add(cap)

		# Count state fields
		counts['objects']['total_state_fields'] += len(obj_data.get('state_fields', []))

	# Scenes aggregation
	for scene_name, scene_data in db.base_scenes.items():
		workspace = scene_data.get('workspace', 'unknown')
		counts['scenes']['workspaces'].add(workspace)
		placements = scene_data.get('placements', [])
		counts['scenes']['total_placements'] += len(placements)

	# Protocol scenes aggregation (placement deltas)
	scene_deltas = {
		'add': 0,
		'reposition': 0,
		'deactivate': 0,
		'remove': 0,
	}
	for path, scene_data in protocol_scene_rows:
		add_count = len(scene_data.get('add_placements', []))
		reposition_count = len(scene_data.get('reposition_placements', []))
		deactivate_count = len(scene_data.get('deactivate_placements', []))
		remove_count = len(scene_data.get('remove_placements', []))
		scene_deltas['add'] += add_count
		scene_deltas['reposition'] += reposition_count
		scene_deltas['deactivate'] += deactivate_count
		scene_deltas['remove'] += remove_count

	counts['scenes']['protocol_scene_deltas'] = {k: v for k, v in scene_deltas.items() if v > 0}

	# Materials aggregation
	for path, material_data in material_rows:
		materials_dict = material_data.get('materials', {})
		if isinstance(materials_dict, dict):
			for mat_name, mat_info in materials_dict.items():
				counts['materials']['distinct_names'].add(mat_name)
				if isinstance(mat_info, dict):
					color = mat_info.get('display_color')
					if color:
						# Nested display_color: extract light and dark values
						if isinstance(color, dict):
							light = color.get('light')
							if light:
								counts['materials']['distinct_colors'].add(light)

	# Protocols aggregation
	for path, protocol_data in protocol_rows:
		protocol_type = protocol_data.get('protocol_type', 'unknown')
		if protocol_type not in counts['protocols']['by_type']:
			counts['protocols']['by_type'][protocol_type] = 0
		counts['protocols']['by_type'][protocol_type] += 1

		# Count steps, interactions, targets, gestures, materials, scene ops
		proto_counts = _protocol_counts(protocol_data)
		counts['protocols']['total_steps'] += proto_counts['steps']
		counts['protocols']['total_interactions'] += proto_counts['interactions']
		for gesture in proto_counts['gestures']:
			counts['protocols']['distinct_gestures'].add(gesture)
		for target in proto_counts['targets']:
			counts['protocols']['distinct_targets'].add(target)
		for material in proto_counts['materials']:
			counts['protocols']['distinct_materials'].add(material)
		for op_type in proto_counts['scene_ops']:
			counts['protocols']['distinct_scene_ops'].add(op_type)

	# Convert sets to sorted lists for output
	counts['objects']['distinct_capabilities'] = sorted(counts['objects']['distinct_capabilities'])
	counts['scenes']['workspaces'] = sorted(counts['scenes']['workspaces'])
	counts['materials']['distinct_names'] = sorted(counts['materials']['distinct_names'])
	counts['materials']['distinct_colors'] = sorted(counts['materials']['distinct_colors'])
	counts['protocols']['distinct_gestures'] = sorted(counts['protocols']['distinct_gestures'])
	counts['protocols']['distinct_targets'] = sorted(counts['protocols']['distinct_targets'])
	counts['protocols']['distinct_materials'] = sorted(counts['protocols']['distinct_materials'])
	counts['protocols']['distinct_scene_ops'] = sorted(counts['protocols']['distinct_scene_ops'])

	return counts


def render(counts: object, severity_counts: object=None) -> None:
	"""
	Render compact indented dashboard to stdout.
	Uses rich Console with auto-detected output mode for section headings in bold colored style.

	Args:
		counts: dict from aggregate().
		severity_counts: optional {'errors', 'warnings', 'advisories'} from
			validate_whole_tree. When provided, the Totals block reports the
			real per-severity counts instead of a hardcoded zero.
	"""
	console = validation.shared_toolkit.console.make_console()

	output_lines = []

	#============================================
	# Totals section
	output_lines.append("[bold cyan]Validated content YAML[/bold cyan]")
	output_lines.append("[dim]Totals[/dim]")
	total_files = counts['objects']['total'] + counts['scenes']['base_count'] + counts['scenes']['protocol_count'] + counts['materials']['file_count'] + sum(counts['protocols']['by_type'].values())
	output_lines.append(f"  Files: {total_files}")
	output_lines.append(f"  Objects: {counts['objects']['total']}")
	output_lines.append(f"  Base scenes: {counts['scenes']['base_count']}")
	output_lines.append(f"  Protocol scenes: {counts['scenes']['protocol_count']}")
	output_lines.append(f"  Materials files: {counts['materials']['file_count']}")
	output_lines.append(f"  Protocols: {sum(counts['protocols']['by_type'].values())}")
	# Real per-severity counts, not a hardcoded zero. error blocks the run;
	# warning and advisory do not.
	if severity_counts is not None:
		output_lines.append(f"  Errors: {severity_counts['errors']}")
		output_lines.append(f"  Warnings: {severity_counts['warnings']}")
		output_lines.append(f"  Advisories: {severity_counts['advisories']}")

	#============================================
	# Objects section
	output_lines.append("")
	output_lines.append("[bold green]Objects[/bold green]")
	kind_list = []
	for kind in sorted(counts['objects']['by_kind'].keys()):
		count = counts['objects']['by_kind'][kind]
		kind_list.append(f"{kind} {count}")
	kinds_str = ', '.join(kind_list)
	output_lines.append(f"  [dim]Kinds:[/dim] {kinds_str}")
	output_lines.append(f"  [dim]State fields:[/dim] {counts['objects']['total_state_fields']}")
	cap_count = len(counts['objects']['distinct_capabilities'])
	output_lines.append(f"  [dim]Capabilities:[/dim] {cap_count} distinct")

	#============================================
	# Scenes section
	output_lines.append("")
	output_lines.append("[bold yellow]Scenes[/bold yellow]")
	if counts['scenes']['workspaces']:
		ws_str = ', '.join(counts['scenes']['workspaces'])
		output_lines.append(f"  [dim]Workspaces:[/dim] {ws_str}")
	output_lines.append(f"  [dim]Base placements:[/dim] {counts['scenes']['total_placements']}")
	add_count = counts['scenes']['protocol_scene_deltas'].get('add', 0)
	if add_count > 0:
		output_lines.append(f"  [dim]Protocol add_placements:[/dim] {add_count}")

	#============================================
	# Materials section
	output_lines.append("")
	output_lines.append("[bold magenta]Materials[/bold magenta]")
	output_lines.append(f"  [dim]Files:[/dim] {counts['materials']['file_count']}")
	output_lines.append(f"  [dim]Names:[/dim] {len(counts['materials']['distinct_names'])}")
	color_count = len(counts['materials']['distinct_colors'])
	output_lines.append(f"  [dim]Display colors:[/dim] {color_count}")

	#============================================
	# Protocols section
	output_lines.append("")
	output_lines.append("[bold blue]Protocols[/bold blue]")
	type_list = []
	for proto_type in sorted(counts['protocols']['by_type'].keys()):
		count = counts['protocols']['by_type'][proto_type]
		type_list.append(f"{proto_type} {count}")
	types_str = ', '.join(type_list)
	output_lines.append(f"  [dim]Types:[/dim] {types_str}")
	output_lines.append(f"  [dim]Steps:[/dim] {counts['protocols']['total_steps']}")
	output_lines.append(f"  [dim]Interactions:[/dim] {counts['protocols']['total_interactions']}")
	output_lines.append(f"  [dim]Targets:[/dim] {len(counts['protocols']['distinct_targets'])}")
	material_count = len(counts['protocols']['distinct_materials'])
	output_lines.append(f"  [dim]Materials used:[/dim] {material_count}")
	if counts['protocols']['distinct_scene_ops']:
		ops_str = ', '.join(counts['protocols']['distinct_scene_ops'])
		output_lines.append(f"  [dim]Scene operations:[/dim] {ops_str}")

	#============================================
	# Print combined output
	console.print('\n'.join(output_lines))
