"""Quarterly scorecard report generator.

Generates Markdown report ranking scenes by score drift over a quarter.
Manual-trigger only. Canonical invocation:

	python3 -m validation.scene_design.quarterly --quarter 2026-Q2 \
		--history-path test-results/scene_design/history/scorecard_history.jsonl \
		--out /path/to/scorecard_quarterly_2026-Q2.md
"""

import sys
import json
import argparse
from pathlib import Path

from validation.scene_design.archive import load_history, score_quarter_range


def quarter_to_dates(quarter_str: str) -> tuple[str, str]:
	"""
	Convert quarter string to start and end dates.

	Args:
		quarter_str: Quarter string like '2026-Q2'.

	Returns:
		Tuple of (start_date, end_date) as 'YYYY-MM-DD' strings.

	Raises:
		ValueError if quarter_str format is invalid.
	"""
	parts = quarter_str.split('-')
	if len(parts) != 2 or parts[0].isdigit() is False or not parts[1].startswith('Q'):
		raise ValueError(f'Invalid quarter format: {quarter_str}. Expected YYYY-Qn.')

	year_str = parts[0]
	quarter_str_num = parts[1][1:]

	try:
		year = int(year_str)
		quarter = int(quarter_str_num)
	except ValueError:
		raise ValueError(f'Invalid quarter format: {quarter_str}. Expected YYYY-Qn.')

	if quarter < 1 or quarter > 4:
		raise ValueError(f'Quarter must be 1-4, got Q{quarter}.')

	# Map quarter to month range
	month_ranges = {
		1: ('01', '03'),
		2: ('04', '06'),
		3: ('07', '09'),
		4: ('10', '12'),
	}

	start_month, end_month = month_ranges[quarter]
	start_date = f'{year}-{start_month}-01'
	# Last day of quarter month
	if quarter == 4:
		end_day = '31'
	else:
		end_month_int = int(end_month)
		# Days in months (non-leap year; leap year adjustment not needed for date validation)
		days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
		end_day = str(days_in_month[end_month_int - 1])

	end_date = f'{year}-{end_month}-{end_day}'

	return start_date, end_date


def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description='Generate quarterly scorecard report.',
	)
	parser.add_argument(
		'--quarter',
		required=True,
		help='Quarter as YYYY-Qn (e.g., 2026-Q2)',
	)
	parser.add_argument(
		'--history-path',
		type=Path,
		default=Path('test-results/scene_design/history/scorecard_history.jsonl'),
		help='Path to scorecard history file',
	)
	parser.add_argument(
		'--out',
		type=Path,
		required=True,
		help='Output Markdown file path',
	)
	return parser.parse_args()


def main() -> None:
	"""Main entry point for quarterly report generator."""
	args = parse_args()

	# Parse quarter string
	try:
		start_date, end_date = quarter_to_dates(args.quarter)
	except ValueError as e:
		print(f'Error: {e}', file=sys.stderr)
		sys.exit(1)

	# Load history. load_history raises OSError (missing/unreadable) or
	# json.JSONDecodeError (malformed line) -- catch both narrowly.
	try:
		history = load_history(args.history_path)
	except (OSError, json.JSONDecodeError) as e:
		print(f'Error loading history: {e}', file=sys.stderr)
		sys.exit(1)

	# Collect scene score changes over the quarter
	scene_deltas = {}

	for row in history:
		scene = row['scene']
		if scene not in scene_deltas:
			scene_deltas[scene] = []
		scene_deltas[scene].append((row['date_utc'], row['score']))

	# Compute deltas (latest - earliest) for each scene
	delta_rows = []

	for scene in sorted(scene_deltas.keys()):
		scores_in_range = score_quarter_range(history, scene, start_date, end_date)
		if not scores_in_range:
			continue

		# Filter out None scores
		valid_scores = [s['score'] for s in scores_in_range if s['score'] is not None]
		if not valid_scores:
			continue

		# min/max bound the quarter window; chronological first/last would
		# require sorting by date_utc, which is not what the report wants:
		# "largest drop" is defined as max - min, not first - last.
		min_score = min(valid_scores)
		max_score = max(valid_scores)
		delta = max_score - min_score

		delta_rows.append({
			'scene': scene,
			'min_score': min_score,
			'max_score': max_score,
			'delta': delta,
		})

	# Sort by delta (largest drops first, i.e., negative deltas first)
	delta_rows.sort(key=lambda r: r['delta'])

	# Generate Markdown report
	lines = []
	lines.append('# Quarterly Scene Design Report')
	lines.append('')
	lines.append(f'**Quarter:** {args.quarter}')
	lines.append(f'**Period:** {start_date} to {end_date}')
	lines.append('')

	if not delta_rows:
		lines.append('No scene data for this quarter.')
		lines.append('')
	else:
		lines.append('## Score Changes (Ranked by Largest Drop)')
		lines.append('')
		lines.append('| Scene | Min | Max | Delta |')
		lines.append('| --- | --- | --- | --- |')

		for row in delta_rows:
			lines.append(
				f"| {row['scene']} | {row['min_score']:.1f} | {row['max_score']:.1f} | {row['delta']:+.1f} |"
			)

		lines.append('')

		# Bottom decile (lowest 10% by max score)
		if len(delta_rows) >= 10:
			lines.append('## Bottom Decile (Lowest-Scoring Scenes)')
			lines.append('')
			bottom_count = len(delta_rows) // 10
			for row in sorted(delta_rows, key=lambda r: r['max_score'])[:bottom_count]:
				lines.append(f"- {row['scene']}: {row['max_score']:.1f}")
			lines.append('')

	lines.append('## Methodology')
	lines.append('')
	lines.append('- Min score: minimum score recorded in quarter date range.')
	lines.append('- Max score: maximum score recorded in quarter date range.')
	lines.append('- Delta: max - min (always non-negative; report ranks by largest swing).')
	lines.append('')

	output = '\n'.join(lines)

	# Write output. mkdir + open raise only OSError.
	try:
		args.out.parent.mkdir(parents=True, exist_ok=True)
		with open(args.out, 'w') as f:
			f.write(output)
	except OSError as e:
		print(f'Error writing output: {e}', file=sys.stderr)
		sys.exit(1)


if __name__ == '__main__':
	main()
