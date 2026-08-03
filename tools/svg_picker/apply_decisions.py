#!/usr/bin/env python3
"""
Apply SVG picker decisions to behavior-organized equipment sources.

Reads decisions.json (positional CLI arg) and runs 6-class preflight validation
before any disk mutation. Apply phase copies/moves SVGs and appends attribution rows.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from validation.svg.asset_registry import build_svg_asset_registry


BEHAVIOR_CATEGORIES = frozenset({
	"static",
	"binary_state",
	"multi_state",
	"variable_volume",
})


def target_path(repo_root: Path, decision: dict) -> Path:
	"""Return the behavior-organized target selected by picker metadata."""
	return (
		repo_root
		/ "assets/equipment"
		/ decision["behavior_category"]
		/ f"{decision['asset_name']}.svg"
	)


def get_repo_root() -> Path:
	"""Get repository root via git rev-parse --show-toplevel."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=True,
	)
	return Path(result.stdout.strip())


def read_decisions(decisions_path: Path) -> list:
	"""Read and parse decisions.json file."""
	with open(decisions_path, "r") as f:
		return json.load(f)


def read_candidates(candidates_path: Path) -> dict:
	"""Read candidates.json and return dict keyed by candidate id."""
	with open(candidates_path, "r") as f:
		candidates_list = json.load(f)
	return {c["id"]: c for c in candidates_list}


def run_preflight(decisions: list, candidates: dict, options: dict, repo_root: Path) -> list:
	"""
	Run all preflight checks. Returns list of error messages (empty = OK).
	"""
	errors = []

	# Check 1: Schema validation per decision record
	for idx, decision in enumerate(decisions):
		# Every decision must have asset_name and state
		if "asset_name" not in decision:
			errors.append(f"Decision {idx}: missing required key 'asset_name'")
		if "state" not in decision:
			errors.append(f"Decision {idx}: missing required key 'state'")
		else:
			state = decision["state"]
			if state not in ("assigned", "defer", "ignore_intentional"):
				errors.append(f"Decision {idx}: state '{state}' must be one of (assigned, defer, ignore_intentional)")

			# Assigned decisions carry the source and intended behavior directory.
			if state == "assigned":
				for required_key in (
					"behavior_category", "candidate_id", "source_repo", "source_path", "license_tag",
				):
					if required_key not in decision:
						errors.append(f"Decision {idx}: state='assigned' requires key '{required_key}'")
				behavior_category = decision.get("behavior_category")
				if behavior_category is not None and behavior_category not in BEHAVIOR_CATEGORIES:
					errors.append(
						f"Decision {idx}: behavior_category '{behavior_category}' must be one of "
						f"{sorted(BEHAVIOR_CATEGORIES)}"
					)

			# If ignore_intentional, require non-empty reason
			if state == "ignore_intentional":
				if "reason" not in decision or not decision["reason"]:
					errors.append(f"Decision {idx}: state='ignore_intentional' requires non-empty 'reason'")

	# Check 2: No duplicate asset_name across decisions
	asset_names = [d.get("asset_name") for d in decisions if "asset_name" in d]
	seen = set()
	for name in asset_names:
		if name in seen:
			errors.append(f"Duplicate asset_name across decisions: '{name}'")
		seen.add(name)

	registry = build_svg_asset_registry(repo_root / "assets")

	# Check 3, 4, 5, 6: Only for assigned decisions
	for idx, decision in enumerate(decisions):
		if decision.get("state") != "assigned":
			continue
		if decision.get("behavior_category") not in BEHAVIOR_CATEGORIES:
			# The schema pass above already records the actionable error. Avoid
			# dereferencing incomplete records during the remaining checks.
			continue

		candidate_id = decision.get("candidate_id")
		source_repo = decision.get("source_repo")
		source_path = decision.get("source_path")
		asset_name = decision.get("asset_name")

		# Check 3: candidate_id exists in candidates.json
		if candidate_id not in candidates:
			errors.append(f"Decision {idx}: candidate_id '{candidate_id}' not found in candidates.json")
			continue  # Skip further checks for this decision

		candidate = candidates[candidate_id]

		# Check 4: source_path matches candidate's rel_path and file exists
		candidate_rel_path = candidate.get("rel_path")
		if source_path != candidate_rel_path:
			errors.append(
				f"Decision {idx}: source_path drift detected. "
				f"decisions.json has '{source_path}' but candidates.json has '{candidate_rel_path}'. "
				"Source drifted since manifest build; re-run tools/svg_picker/build_candidate_manifest.py"
			)
		else:
			# Check file exists at repo_root/rel_path
			file_path = repo_root / candidate_rel_path
			if not file_path.exists():
				errors.append(
					f"Decision {idx}: source file does not exist at {candidate_rel_path}. "
					"Source drifted since manifest build; re-run tools/svg_picker/build_candidate_manifest.py"
				)

		# Check 5: No overwrite without --force
		existing_path = None
		if asset_name in registry.asset_names:
			existing_path = registry.asset_path(asset_name)
		if existing_path is not None and not options.get("force"):
			relative_existing_path = existing_path.relative_to(repo_root)
			errors.append(
				f"Decision {idx}: target {relative_existing_path} already exists. "
				"Use --force to overwrite."
			)
		elif existing_path is not None and existing_path != target_path(repo_root, decision):
			errors.append(
				f"Decision {idx}: existing logical asset '{asset_name}' is in a different "
				"behavior directory; move it deliberately before replacing it."
			)

		# Check 6: In-repo source requires --rename-existing
		if source_repo == "assets/equipment" and not options.get("rename_existing"):
			errors.append(
				f"Decision {idx}: source_repo='assets/equipment' (in-repo source) requires --rename-existing flag. "
				"Use --rename-existing to enable git mv for in-repo sources."
			)

	return errors


def apply_decisions(decisions: list, candidates: dict, options: dict, repo_root: Path) -> None:
	"""Apply all assigned decisions to disk."""
	attribution_rows = []

	for decision in decisions:
		if decision.get("state") != "assigned":
			# defer and ignore_intentional are no-ops on disk
			continue

		# Preflight has already validated every required key for assigned decisions
		# and every assigned candidate exists in candidates; direct lookups here.
		candidate_id = decision["candidate_id"]
		source_repo = decision["source_repo"]
		source_path = decision["source_path"]
		license_tag = decision["license_tag"]
		asset_name = decision["asset_name"]

		candidate = candidates[candidate_id]
		attribution_required = candidate["attribution_required"]
		license_confidence = candidate["license_confidence"]
		license_url = candidate["license_url"]

		source_file = repo_root / source_path
		target_file = target_path(repo_root, decision)
		target_relative = target_file.relative_to(repo_root)

		# Perform copy or move based on source_repo
		if source_repo == "assets/equipment":
			# In-repo source: use git mv (only reached if --rename-existing is set)
			if not options.get("dry_run"):
				target_file.parent.mkdir(parents=True, exist_ok=True)
				subprocess.run(
					["git", "mv", str(source_file), str(target_file)],
					check=True,
					cwd=repo_root,
				)
			action = f"git mv {source_path} -> {target_relative}"
		else:
			# OTHER_REPOS source: copy and git add
			if not options.get("dry_run"):
				target_file.parent.mkdir(parents=True, exist_ok=True)
				subprocess.run(["cp", str(source_file), str(target_file)], check=True)
				subprocess.run(
					["git", "add", str(target_file)],
					check=True,
					cwd=repo_root,
				)
			action = f"cp {source_path} -> {target_relative} (git add)"

		# Run normalize_svg_v3.py on the target, in place (v3 CLI: -i/--input,
		# --in-place; a rejection exits non-zero and leaves the file untouched).
		if not options.get("dry_run"):
			subprocess.run(
				["python3", "tools/normalize_svg_v3.py", "-i", str(target_file), "--in-place"],
				check=True,
				cwd=repo_root,
			)

		# Append attribution row if required
		if attribution_required:
			attribution_rows.append({
				"asset_name": asset_name,
				"source_repo": source_repo,
				"original_rel_path": source_path,
				"license_tag": license_tag,
				"license_confidence": license_confidence,
				"license_url": license_url,
			})

		# Print per-decision summary
		if options.get("verbose"):
			print(f"  {asset_name}: {action}")
		else:
			print(f"  {asset_name}")

	# Append attribution rows to docs/SVG_ATTRIBUTION.md
	if attribution_rows:
		attribution_file = repo_root / "docs/SVG_ATTRIBUTION.md"
		if not attribution_file.exists():
			# Create with header
			if not options.get("dry_run"):
				with open(attribution_file, "w") as f:
					f.write("# SVG attribution\n\n")
					f.write("Per-asset attribution rows for SVGs sourced from upstream libraries requiring credit\n")
					f.write("(typically CC BY). Generated and appended by `tools/svg_picker/apply_decisions.py`.\n\n")
					f.write("| asset_name | source_repo | original_rel_path | license_tag | license_confidence | license_url |\n")
					f.write("| --- | --- | --- | --- | --- | --- |\n")

		# Append rows
		if not options.get("dry_run"):
			with open(attribution_file, "a") as f:
				for row in attribution_rows:
					line = (
						f"| {row['asset_name']} | {row['source_repo']} | "
						f"{row['original_rel_path']} | {row['license_tag']} | "
						f"{row['license_confidence']} | {row['license_url']} |\n"
					)
					f.write(line)


def main() -> None:
	"""Main entry point."""
	parser = argparse.ArgumentParser(
		description="Apply SVG picker decisions to behavior-organized equipment sources."
	)
	parser.add_argument(
		"decisions_json",
		help="Path to decisions.json (output from picker UI)",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		dest="dry_run",
		help="Print planned actions without touching disk",
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="Allow overwriting existing target assets",
	)
	parser.add_argument(
		"--rename-existing",
		action="store_true",
		dest="rename_existing",
		help="Enable git mv for in-repo asset sources (reassignment)",
	)
	parser.add_argument(
		"--candidates",
		default="tools/svg_picker/candidates.json",
		help="Path to candidates.json (default: tools/svg_picker/candidates.json)",
	)
	parser.add_argument(
		"--verbose",
		action="store_true",
		help="Print verbose per-decision action details",
	)

	args = parser.parse_args()

	repo_root = get_repo_root()
	decisions_path = Path(args.decisions_json)
	candidates_path = Path(args.candidates)

	# Resolve relative paths against repo_root
	if not decisions_path.is_absolute():
		decisions_path = repo_root / decisions_path
	if not candidates_path.is_absolute():
		candidates_path = repo_root / candidates_path

	# Read inputs. FileNotFoundError and json.JSONDecodeError propagate so the
	# user sees the full traceback identifying which file failed.
	decisions = read_decisions(decisions_path)
	candidates = read_candidates(candidates_path)

	options = {
		"dry_run": args.dry_run,
		"force": args.force,
		"rename_existing": args.rename_existing,
		"verbose": args.verbose,
	}

	# Run preflight
	preflight_errors = run_preflight(decisions, candidates, options, repo_root)
	if preflight_errors:
		print("Preflight validation failed:", file=sys.stderr)
		for error in preflight_errors:
			print(f"  {error}", file=sys.stderr)
		raise SystemExit(1)

	# Count decisions by state
	assigned_count = sum(1 for d in decisions if d.get("state") == "assigned")
	deferred_count = sum(1 for d in decisions if d.get("state") == "defer")
	ignored_count = sum(1 for d in decisions if d.get("state") == "ignore_intentional")

	# Print dry-run or apply header
	if args.dry_run:
		print(f"DRY RUN: Would apply {assigned_count} assigned decisions:")
	else:
		print(f"Applying {assigned_count} assigned decisions:")

	# Apply decisions
	apply_decisions(decisions, candidates, options, repo_root)

	# Print summary
	print()
	print(f"Summary: {assigned_count} assigned, {deferred_count} deferred, {ignored_count} ignored")

	# Count attribution rows (only count rows for new assignments with attribution_required)
	attribution_rows_count = sum(
		1 for d in decisions
		if d.get("state") == "assigned"
		and candidates[d["candidate_id"]].get("attribution_required", False)
	)
	if attribution_rows_count > 0:
		print(f"Attribution rows appended: {attribution_rows_count}")

	print()
	print("Remember to run: source source_me.sh && python3 pipeline/gen_svg_manifest.py")


if __name__ == "__main__":
	main()
