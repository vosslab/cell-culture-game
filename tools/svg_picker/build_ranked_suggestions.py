#!/usr/bin/env python3
"""
Patch 3 (WS-RANK): Join candidates.json and missing_targets.json to emit
suggestions.json with top-50 ranked candidates per target.

Scoring model:
  - Target tokens: derived from state_family + asset_name (split, lowercase, dedupe)
  - Filename token overlap: Jaccard(candidate.search_tokens, target_tokens)
  - Parent folder overlap: Jaccard(candidate parent-folder tokens, target_tokens),
    but only count parent-folder tokens not already in search_tokens
  - Source trust boost: 0.20 for assets/equipment, 0.10 for bioicons, 0.00 others
  - Final score: filename_overlap * 0.6 + parent_overlap * 0.2 + source_trust_boost

Tie-breaking:
  - Higher source_trust_boost first (assets > bioicons > scienceicons)
  - Then candidate_id lexicographic

Omit candidates with score == 0. Mark targets with no candidates as no_suggestions: true.
"""

import json
import argparse
import os
import sys

FILENAME_OVERLAP_WEIGHT = 0.6
PARENT_FOLDER_OVERLAP_WEIGHT = 0.2
SOURCE_TRUST_BOOST = {
	'assets/equipment': 0.20,
	'OTHER_REPOS/bioicons': 0.10,
	'OTHER_REPOS/scienceicons': 0.00,
}


def jaccard_similarity(set_a, set_b):
	"""Compute Jaccard similarity between two sets."""
	if not set_a and not set_b:
		return 0.0
	intersection = len(set_a & set_b)
	union = len(set_a | set_b)
	if union == 0:
		return 0.0
	return intersection / union

def tokenize_name(name):
	"""Split name on underscores, lowercase, dedupe."""
	tokens = name.split('_')
	return set(t.lower() for t in tokens if t)

def get_parent_folder_tokens(rel_path):
	"""Extract tokens from parent folder path (not filename)."""
	# Example: "assets/equipment/static/xyz.svg" -> ["assets", "equipment", "static"]
	# Example: "OTHER_REPOS/bioicons/static/icons/cc-by-4.0/arrow.svg" -> ["other", "repos", "bioicons", "static", "icons", "cc", "by", "arrow"]
	# Split on / and - and filter out extension
	path_parts = rel_path.split('/')
	folder_parts = path_parts[:-1]
	tokens = []
	for part in folder_parts:
		# Split each folder part on hyphens too
		subparts = part.split('-')
		for subpart in subparts:
			if subpart:
				tokens.append(subpart.lower())
	return set(tokens)

def get_source_trust_boost(candidate):
	"""Return source trust boost based on candidate's source_repo."""
	source_repo = candidate['source_repo']
	if source_repo == 'assets/equipment':
		return SOURCE_TRUST_BOOST['assets/equipment']
	elif source_repo == 'bioicons':
		return SOURCE_TRUST_BOOST['OTHER_REPOS/bioicons']
	else:
		return SOURCE_TRUST_BOOST['OTHER_REPOS/scienceicons']

def compute_score(candidate, target_tokens):
	"""Compute score for a candidate against target tokens."""
	# Filename token overlap
	candidate_search_tokens = set(candidate.get('search_tokens', []))
	filename_overlap = jaccard_similarity(candidate_search_tokens, target_tokens)

	# Parent folder overlap: use parent folder tokens only (excluding search_tokens)
	rel_path = candidate.get('rel_path', '')
	parent_tokens = get_parent_folder_tokens(rel_path)
	# Only count parent tokens not already in search_tokens
	parent_only = parent_tokens - candidate_search_tokens
	parent_overlap = jaccard_similarity(parent_only, target_tokens)

	# Source trust boost
	source_boost = get_source_trust_boost(candidate)

	score = (
		filename_overlap * FILENAME_OVERLAP_WEIGHT
		+ parent_overlap * PARENT_FOLDER_OVERLAP_WEIGHT
		+ source_boost
	)
	return score, filename_overlap, parent_overlap, source_boost

def load_json_file(path):
	"""Load JSON file, exit with error if missing."""
	if not os.path.exists(path):
		print(f'ERROR: {path} not found', file=sys.stderr)
		sys.exit(1)
	with open(path) as f:
		return json.load(f)

def main():
	parser = argparse.ArgumentParser(
		description='Rank candidates per target, emit suggestions.json'
	)
	parser.add_argument(
		'--candidates',
		default='tools/svg_picker/candidates.json',
		help='Path to candidates.json'
	)
	parser.add_argument(
		'--targets',
		default='tools/svg_picker/missing_targets.json',
		help='Path to missing_targets.json'
	)
	parser.add_argument(
		'--output',
		default='tools/svg_picker/suggestions.json',
		help='Output path for suggestions.json'
	)
	parser.add_argument(
		'--top',
		type=int,
		default=50,
		help='Number of top candidates per target'
	)
	parser.add_argument(
		'--verbose',
		action='store_true',
		help='Verbose output'
	)
	args = parser.parse_args()

	# Load inputs
	if args.verbose:
		print(f'Loading {args.candidates}...')
	candidates = load_json_file(args.candidates)

	if args.verbose:
		print(f'Loading {args.targets}...')
	targets_data = load_json_file(args.targets)

	# Flatten targets: they come as dict grouped by state_family
	all_targets = []
	if isinstance(targets_data, dict):
		for state_family, records in targets_data.items():
			all_targets.extend(records)
	else:
		all_targets = targets_data

	# Build candidate lookup by id
	candidate_by_id = {}
	for c in candidates:
		candidate_by_id[c['id']] = c

	# Process each target
	suggestions = []
	no_suggestions_count = 0

	for target in all_targets:
		asset_name = target['asset_name']
		state_family = target['state_family']

		# Derive target tokens from state_family + asset_name
		state_family_tokens = tokenize_name(state_family)
		asset_name_tokens = tokenize_name(asset_name)
		target_tokens = state_family_tokens | asset_name_tokens

		if args.verbose:
			print(f'Target: {asset_name} (state_family={state_family}, tokens={sorted(target_tokens)})')

		# Score all candidates
		scored_candidates = []
		for candidate in candidates:
			score, filename_overlap, parent_overlap, source_boost = compute_score(
				candidate, target_tokens
			)

			# Omit if score is exactly 0
			if score == 0:
				continue

			scored_candidates.append({
				'candidate_id': candidate['id'],
				'score': score,
				'filename_overlap': filename_overlap,
				'parent_overlap': parent_overlap,
				'source_boost': source_boost,
				'source_repo': candidate['source_repo'],
			})

		# Sort: by score desc, then by source_boost desc, then by candidate_id
		scored_candidates.sort(
			key=lambda x: (-x['score'], -x['source_boost'], x['candidate_id'])
		)

		# Take top N
		top_candidates = scored_candidates[:args.top]

		# Format output: omit intermediate fields
		ranked = []
		for sc in top_candidates:
			ranked.append({
				'candidate_id': sc['candidate_id'],
				'score': round(sc['score'], 2),
				'signals': {
					'filename_token_overlap': round(sc['filename_overlap'], 2),
					'parent_folder_overlap': round(sc['parent_overlap'], 2),
					'source_trust_boost': round(sc['source_boost'], 2),
				}
			})

		no_suggestions = len(ranked) == 0

		suggestion_record = {
			'target_asset_name': asset_name,
			'no_suggestions': no_suggestions,
			'ranked': ranked,
		}

		suggestions.append(suggestion_record)

		if no_suggestions:
			no_suggestions_count += 1
			if args.verbose:
				print('  -> no suggestions (all candidates scored 0)')
		else:
			if args.verbose:
				print(f'  -> {len(ranked)} suggestions, top: {ranked[0]["candidate_id"]} (score={ranked[0]["score"]})')

	# Write output
	with open(args.output, 'w') as f:
		json.dump(suggestions, f, indent=2)

	if args.verbose:
		print()

	# Summary
	total_ranked = sum(len(s['ranked']) for s in suggestions)
	print(
		f'Ranked {total_ranked} candidates per target across {len(suggestions)} targets; '
		f'{no_suggestions_count} targets have no_suggestions=true'
	)

if __name__ == '__main__':
	main()
