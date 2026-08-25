"""Cross-protocol checks: camelCase ban, contents drift."""

import re

from validation.yaml_schema.findings import Finding, Severity

# spec: docs/specs/SPEC_DESIGN_CHECKLIST.md "snake_case lock" (plan: giggly-mixing-minsky Class E)
# Authored YAML keys must be snake_case. A camelCase boundary inside a key
# (lower-case letter followed by upper-case letter) is rejected. Closed
# vocabulary closure (unknown-key errors per-container) catches retired
# tokens; this regex catches the broader camelCase pattern generally.
CAMELCASE_KEY_RE = re.compile(r'[a-z][A-Z]')


class CrossProtocolValidator:
	"""Cross-cutting hygiene checks (camelCase ban, contents drift)."""

	def check_camelcase_keys(self, data: dict, path: str) -> list:
		"""
		Recursive walk of YAML tree. Any dict key with a camelCase boundary
		(`[a-z][A-Z]`) is an ERROR tagged T3_CAMELCASE. Authored YAML keys
		must be snake_case per plan giggly-mixing-minsky Class E.
		"""
		findings = []
		self._walk_camelcase(data, path, findings)
		return findings

	def _walk_camelcase(self, obj: object, path: str, findings: list) -> None:
		if isinstance(obj, dict):
			for key, value in obj.items():
				if isinstance(key, str) and CAMELCASE_KEY_RE.search(key):
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"[T3_CAMELCASE] key '{key}' is camelCase; use snake_case",
					))
				self._walk_camelcase(value, f"{path}.{key}", findings)
		elif isinstance(obj, list):
			for idx, item in enumerate(obj):
				self._walk_camelcase(item, f"{path}[{idx}]", findings)

	# Deferred: check_contents_drift. Cross-protocol drift sweep is not wired in
	# this pass. Re-add when contents schema is post-cleanup and protocols agree
	# on canonical entries.

