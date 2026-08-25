"""Suppression manifest loader, validator, and enforcement for Group B rules.

Group A (BLOCKED) findings are never suppressible. Suppression entries apply
only to Group B (ESCAPE_REQUIRED) advisory findings.

Suppression schema (closed, all four fields required):
  - rule: <rule_name> (must not be a Group A rule)
  - scene: <scene_name>
  - placement_name: <optional placement_name, null/absent for scene-wide>
  - reason: <free-text justification>
  - ticket: <free-text identifier>
  - owner: <free-text owner>
  - expires: <YYYY-MM-DD>

Validation rules:
  1. All four fields (reason, ticket, owner, expires) are required.
  2. Missing any field rejects the suppression with a malformed_suppression
     advisory Finding (ESCAPE_REQUIRED, confidence HIGH).
  3. expires within 90 days of today is rejected (entries must have > 90
     days remaining). Short-horizon suppressions are treated as "do the
     review now"; long-horizon suppressions require explicit owner sign-off
     captured in the entry's reason/ticket/owner fields.
  4. Group A rule names are rejected with malformed_suppression finding.
  5. Past-expiry suppressions emit expired_suppression advisory Finding
     (ESCAPE_REQUIRED, confidence MEDIUM).

Matching tuple: (rule, scene, placement_name). If placement_name is null/absent
in the manifest entry, it matches every placement under that (rule, scene).

Suppressed findings are REMOVED from the output (not emitted at all).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from validation.scene_lint.findings import Finding, Verdict, Confidence
from validation.shared_toolkit.yaml_io import load_yaml


# Closed set of Group A rule names (decision-gated). object suppression entry
# naming one of these rules is rejected.
GROUP_A_RULES = {
	'duplicate_scene_name',
	'duplicate_placement_name',
	'forbidden_source_geometry',
	'missing_svg_asset',
	'invalid_svg_viewbox',
	'inheritance_unknown_base',
	'inheritance_multi_level',
	'inheritance_cycle',
	'inheritance_locked_field_mutation',
	'inheritance_dangling_ref',
}


@dataclass
class SuppressionEntry:
	"""Single suppression entry from manifest."""
	rule: str
	scene: str
	placement_name: str | None
	reason: str
	ticket: str
	owner: str
	expires: str  # YYYY-MM-DD

	def matches(self, rule_name: str, scene_name: str, placement: str | None) -> bool:
		"""Check if this entry suppresses a given finding tuple."""
		if self.rule != rule_name or self.scene != scene_name:
			return False
		# If placement_name is None, match all placements under (rule, scene)
		if self.placement_name is None:
			return True
		return self.placement_name == placement


def parse_expiry_date(date_str: str | object) -> datetime:
	"""
	Parse YYYY-MM-DD string to datetime.

	Handles both string format (from raw YAML text) and datetime.date objects
	(from YAML-loader automatic date parsing).

	Raises ValueError if malformed.
	"""
	from datetime import date
	if isinstance(date_str, datetime):
		return date_str
	if isinstance(date_str, date):
		return datetime.combine(date_str, datetime.min.time())
	return datetime.strptime(date_str, '%Y-%m-%d')


def load_suppressions(
	manifest_path: Path,
	today: datetime | None = None,
) -> tuple[list[SuppressionEntry], list[Finding]]:
	"""
	Load suppression manifest and validate entries.

	Args:
		manifest_path: Path to suppressions.yaml.
		today: Today's date (defaults to datetime.now()). Used for expiry checks.

	Returns:
		(valid_entries, advisory_findings)
		- valid_entries: List of SuppressionEntry for live, non-expired suppressions.
		- advisory_findings: List of Finding for malformed and expired entries
		  (verdict=ESCAPE_REQUIRED, confidence=HIGH for malformed, MEDIUM for expired).

	Raises:
		OSError: If manifest file cannot be read.
		RuntimeError: If YAML parsing fails.
	"""
	if today is None:
		today = datetime.now()

	data = load_yaml(manifest_path)
	entries_raw = data.get('suppressions', [])
	if not isinstance(entries_raw, list):
		entries_raw = []

	valid_entries = []
	advisory_findings = []

	for idx, entry_dict in enumerate(entries_raw):
		if not isinstance(entry_dict, dict):
			advisory_findings.append(Finding(
				scene='unknown',
				placement_name=None,
				rule='malformed_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.HIGH,
				message=f'Suppression entry {idx} is not a dict',
				evidence={'entry_index': idx, 'entry_type': type(entry_dict).__name__},
			))
			continue

		# Check all required fields are present. rule and scene are required for
		# matching; reason/ticket/owner/expires are required for justification +
		# expiry tracking. placement_name is optional (null = scene-wide).
		required_fields = {'rule', 'scene', 'reason', 'ticket', 'owner', 'expires'}
		missing = required_fields - set(entry_dict.keys())
		if missing:
			advisory_findings.append(Finding(
				scene=entry_dict.get('scene', 'unknown'),
				placement_name=entry_dict.get('placement_name'),
				rule='malformed_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.HIGH,
				message=f'Suppression entry {idx} missing required fields: {sorted(missing)}',
				evidence={
					'entry_index': idx,
					'missing_fields': sorted(missing),
					'entry_rule': entry_dict.get('rule', 'unknown'),
				},
			))
			continue

		# Required-fields guard above guarantees these are present.
		rule_name = entry_dict['rule']
		scene_name = entry_dict['scene']
		placement_name = entry_dict.get('placement_name')
		reason = entry_dict['reason']
		ticket = entry_dict['ticket']
		owner = entry_dict['owner']
		expires_raw = entry_dict['expires']

		# Normalize expires to string (YAML loader may parse as date object)
		if isinstance(expires_raw, str):
			expires_str = expires_raw
		else:
			# Convert date/datetime to YYYY-MM-DD string
			expires_str = str(expires_raw)
			if len(expires_str) > 10:
				expires_str = expires_str[:10]

		# Check Group A rule names are rejected
		if rule_name in GROUP_A_RULES:
			advisory_findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='malformed_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.HIGH,
				message=f'Suppression entry {idx} names Group A rule {rule_name}; Group A findings are never suppressible',
				evidence={
					'entry_index': idx,
					'rule': rule_name,
					'group_a_list': sorted(GROUP_A_RULES),
				},
			))
			continue

		# Parse and validate expiry date
		try:
			expiry_date = parse_expiry_date(expires_str)
		except ValueError:
			advisory_findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='malformed_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.HIGH,
				message=f'Suppression entry {idx} has invalid expires date format: {expires_str} (must be YYYY-MM-DD)',
				evidence={
					'entry_index': idx,
					'expires_str': expires_str,
				},
			))
			continue

		# Past-expiry check runs before the 90-day-max check so an entry that
		# is BOTH past its own expiry and outside the renewal window surfaces
		# as `expired_suppression` (the actionable advisory) rather than
		# `malformed_suppression`.
		if expiry_date < today:
			advisory_findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='expired_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.MEDIUM,
				message=f'Suppression for rule {rule_name} on {scene_name} expired on {expires_str}',
				evidence={
					'entry_index': idx,
					'suppressed_rule': rule_name,
					'expires': expires_str,
					'days_expired': (today - expiry_date).days,
					'today': today.strftime('%Y-%m-%d'),
				},
				fix_hints=[
					f'Owner {owner}: review and renew suppression if still justified',
				],
			))
			continue

		# Check expiry is > 90 days from today
		days_to_expiry = (expiry_date - today).days
		if days_to_expiry <= 90:
			advisory_findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='malformed_suppression',
				verdict=Verdict.ESCAPE_REQUIRED,
				confidence=Confidence.HIGH,
				message=f'Suppression entry {idx} expires in {days_to_expiry} days (<= 90 days); renewal requires explicit review',
				evidence={
					'entry_index': idx,
					'expires': expires_str,
					'days_to_expiry': days_to_expiry,
					'today': today.strftime('%Y-%m-%d'),
				},
			))
			continue

		# Valid suppression entry
		valid_entries.append(SuppressionEntry(
			rule=rule_name,
			scene=scene_name,
			placement_name=placement_name,
			reason=reason,
			ticket=ticket,
			owner=owner,
			expires=expires_str,
		))

	return valid_entries, advisory_findings


def apply_suppressions(
	findings: list[Finding],
	suppressions: list[SuppressionEntry],
) -> tuple[list[Finding], list[Finding]]:
	"""
	Filter findings based on suppression entries.

	Args:
		findings: All findings from rules.
		suppressions: Valid suppression entries (from load_suppressions).

	Returns:
		(emitted_findings, suppressed_findings)
		- emitted_findings: Findings that are not suppressed (output set).
		- suppressed_findings: Findings that matched a suppression (removed from output).

	Suppressed findings are identified by matching (rule, scene, placement_name)
	tuple and removed entirely from output.
	"""
	emitted = []
	suppressed = []

	for finding in findings:
		matched = False
		for supp in suppressions:
			if supp.matches(finding.rule, finding.scene, finding.placement_name):
				matched = True
				suppressed.append(finding)
				break
		if not matched:
			emitted.append(finding)

	return emitted, suppressed
