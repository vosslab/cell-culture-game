"""Promotion policy and strict mode for Group B rules.

A B-rule is promoted to strict mode only when its confusion-table metrics
meet the promotion bar: precision >= 0.90, recall >= 0.80, and >= 20
ground-truth positive labels in the labeled corpus.

Promotion configuration lives at validation/scene_lint/promotions.yaml
with a closed schema:
  - rule: str (B-rule name, not Group A)
  - promoted_at: str (YYYY-MM-DD)
  - precision: float (metric at promotion time)
  - recall: float (metric at promotion time)
  - positive_count: int (positive labels in corpus at promotion time)
  - low_confidence_approved: bool (default False; allows low-confidence
    findings on this rule to contribute to strict-mode failures)

At load time, each promotion entry is re-validated against the current
labeled corpus. If current precision < 0.90, recall < 0.80, or
positive_count < 20, the rule is emitted as a promotion_below_bar advisory
finding and remains advisory (not strict).

Strict mode exits 1 on any ESCAPE_REQUIRED finding from a successfully-
promoted rule (when --strict is passed).
"""

from dataclasses import dataclass
from pathlib import Path

from validation.scene_lint.findings import Finding, Verdict, Confidence
from validation.scene_lint.confusion import load_labeled_corpus, compute_confusion
from validation.shared_toolkit.yaml_io import load_yaml


@dataclass
class PromotionEntry:
	"""Single promotion entry from promotions.yaml config.

	Attributes:
		rule: B-rule name to promote. Must NOT be a Group A rule.
		promoted_at: Date the promotion landed, YYYY-MM-DD.
		precision: Precision (TP / (TP + FP)) recorded at promotion time;
			must be >= MIN_PRECISION. Re-validated against the current
			labeled corpus at load time.
		recall: Recall (TP / (TP + FN)) recorded at promotion time;
			must be >= MIN_RECALL. Re-validated at load time.
		positive_count: Ground-truth positive label count recorded at
			promotion time; must be >= MIN_POSITIVE_COUNT. Re-validated.
		low_confidence_approved: If True, low-confidence findings on this
			rule (those derived from fallback scale_source values) still
			contribute to the strict-mode exit code. Defaults to False so
			low-confidence findings stay advisory until explicitly approved.
	"""
	rule: str
	promoted_at: str  # YYYY-MM-DD
	precision: float
	recall: float
	positive_count: int
	low_confidence_approved: bool = False


#============================================
# Closed set of Group A rule names (must not be promoted)
#============================================

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

# Promotion bar thresholds (decision-gated; immutable)
MIN_PRECISION = 0.90
MIN_RECALL = 0.80
MIN_POSITIVE_COUNT = 20


#============================================
# Promotion loader
#============================================

def load_promotions(
	path: Path,
	corpus_path: Path | None = None,
) -> tuple[list[PromotionEntry], list[Finding]]:
	"""Load and validate promotions.yaml config.

	Args:
	  path: Path to promotions.yaml
	  corpus_path: Path to labeled_corpus.yaml for re-validation (optional)

	Returns:
	  tuple[valid_promotions, advisory_findings]:
	    - valid_promotions: list of PromotionEntry for rules that passed
	      re-validation
	    - advisory_findings: list of malformed_promotion or
	      promotion_below_bar advisories for entries that failed validation

	If promotions.yaml does not exist, returns ([], []).
	If corpus_path is provided, re-validates each promotion against current
	corpus metrics. Promotions that fail re-validation emit a
	promotion_below_bar advisory and are omitted from the valid set.
	"""
	advisories: list[Finding] = []
	valid_promotions: list[PromotionEntry] = []

	# Treat missing file as empty promotions per scope boundaries
	if not path.exists():
		return (valid_promotions, advisories)

	data = load_yaml(path)
	if data is None or not isinstance(data, dict):
		return (valid_promotions, advisories)

	promotions_list = data.get('promotions', [])
	if not isinstance(promotions_list, list):
		return (valid_promotions, advisories)

	# Load corpus for re-validation if provided
	corpus = None
	if corpus_path:
		corpus = load_labeled_corpus(corpus_path)

	for entry_dict in promotions_list:
		if not isinstance(entry_dict, dict):
			# Malformed entry (not a dict)
			advisories.append(
				Finding(
					scene='<manifest>',
					placement_name=None,
					rule='<promotions>',
					verdict=Verdict.ESCAPE_REQUIRED,
					confidence=Confidence.HIGH,
					message='Promotion entry is not a YAML mapping',
					evidence={'entry': str(entry_dict)},
				)
			)
			continue

		# Check required fields
		required_fields = {'rule', 'promoted_at', 'precision', 'recall', 'positive_count'}
		missing = required_fields - set(entry_dict.keys())
		if missing:
			advisories.append(
				Finding(
					scene='<manifest>',
					placement_name=None,
					rule='<promotions>',
					verdict=Verdict.ESCAPE_REQUIRED,
					confidence=Confidence.HIGH,
					message=f'Promotion entry missing required fields: {sorted(missing)}',
					evidence={'entry': entry_dict},
				)
			)
			continue

		rule_name = entry_dict['rule']
		if not isinstance(rule_name, str):
			advisories.append(
				Finding(
					scene='<manifest>',
					placement_name=None,
					rule='<promotions>',
					verdict=Verdict.ESCAPE_REQUIRED,
					confidence=Confidence.HIGH,
					message=f'Promotion rule field must be a string, got {type(rule_name).__name__}',
					evidence={'rule': rule_name},
				)
			)
			continue

		# Check for Group A rule names (not allowed to promote)
		if rule_name in GROUP_A_RULES:
			advisories.append(
				Finding(
					scene='<manifest>',
					placement_name=None,
					rule='<promotions>',
					verdict=Verdict.ESCAPE_REQUIRED,
					confidence=Confidence.HIGH,
					message=f'Cannot promote Group A rule: {rule_name}',
					evidence={'rule': rule_name},
				)
			)
			continue

		# Parse and validate metric fields
		try:
			precision = float(entry_dict['precision'])
			recall = float(entry_dict['recall'])
			positive_count = int(entry_dict['positive_count'])
			promoted_at = str(entry_dict['promoted_at'])
			low_confidence_approved = bool(entry_dict.get('low_confidence_approved', False))
		except (TypeError, ValueError) as e:
			advisories.append(
				Finding(
					scene='<manifest>',
					placement_name=None,
					rule='<promotions>',
					verdict=Verdict.ESCAPE_REQUIRED,
					confidence=Confidence.HIGH,
					message=f'Promotion entry has invalid metric types: {str(e)}',
					evidence={'entry': entry_dict},
				)
			)
			continue

		# If corpus provided, re-validate current metrics
		if corpus:
			revalidation = evaluate_promotion_bar(
				rule_name,
				[],  # No current findings needed for bar check
				corpus,
			)
			if not revalidation['meets_bar']:
				reasons = ', '.join(revalidation['reasons_failing'])
				advisories.append(
					Finding(
						scene='<manifest>',
						placement_name=None,
						rule='<promotions>',
						verdict=Verdict.ESCAPE_REQUIRED,
						confidence=Confidence.MEDIUM,
						message=f'Promotion {rule_name} below bar (re-validation): {reasons}',
						evidence={
							'rule': rule_name,
							'precision': revalidation['precision'],
							'recall': revalidation['recall'],
							'positive_count': revalidation['positive_count'],
						},
					)
				)
				continue

		# All type/value validation already passed above. Construct dataclass
		# directly; if PromotionEntry.__init__ raises, that is a programming
		# error that should propagate, not be swallowed into an advisory.
		entry = PromotionEntry(
			rule=rule_name,
			promoted_at=promoted_at,
			precision=precision,
			recall=recall,
			positive_count=positive_count,
			low_confidence_approved=low_confidence_approved,
		)
		valid_promotions.append(entry)

	return (valid_promotions, advisories)


#============================================
# Promotion bar evaluation
#============================================

def evaluate_promotion_bar(
	rule_name: str,
	findings: list[Finding],
	corpus: dict[str, object],
) -> dict[str, object]:
	"""Evaluate if a rule meets the promotion bar.

	Computes precision, recall, and positive label count from the corpus
	and checks against thresholds (precision >= 0.90, recall >= 0.80,
	positive_count >= 20).

	Args:
	  rule_name: Rule to evaluate (e.g., 'B1', 'aspect_distorted_predicted')
	  findings: Current findings (not used for bar computation; pass [] for
	    re-validation)
	  corpus: Loaded corpus dict from load_labeled_corpus()

	Returns:
	  Dict with keys:
	    precision: float or None
	    recall: float or None
	    positive_count: int (count of positive labels for this rule in corpus)
	    meets_bar: bool (True if all three metrics pass thresholds)
	    reasons_failing: list[str] (empty if meets_bar, else reasons for failure)
	"""
	# Compute confusion against current corpus
	confusion = compute_confusion(findings, corpus, rule_name)

	precision = confusion.get('precision')
	recall = confusion.get('recall')
	# corpus['positives'] always exists (load_labeled_corpus guarantees it),
	# and every positive label entry has a mapped_rule field by schema.
	positive_count = len([
		p for p in corpus['positives']
		if p['mapped_rule'] == rule_name
	])

	reasons_failing: list[str] = []

	if positive_count < MIN_POSITIVE_COUNT:
		reasons_failing.append(
			f'positive_count {positive_count} < {MIN_POSITIVE_COUNT}'
		)

	if precision is not None and precision < MIN_PRECISION:
		reasons_failing.append(f'precision {precision:.3f} < {MIN_PRECISION}')
	elif precision is None:
		reasons_failing.append('precision is None (insufficient negative labels)')

	if recall is not None and recall < MIN_RECALL:
		reasons_failing.append(f'recall {recall:.3f} < {MIN_RECALL}')
	elif recall is None:
		reasons_failing.append('recall is None (no positive labels)')

	meets_bar = len(reasons_failing) == 0

	return {
		'precision': precision,
		'recall': recall,
		'positive_count': positive_count,
		'meets_bar': meets_bar,
		'reasons_failing': reasons_failing,
	}

