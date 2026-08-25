"""Writers for scene_lint findings: JSONL and Markdown formats.

JSONL writer emits one line per finding (consumable by downstream tools).
Markdown writer emits per-scene sections with grouped findings.
"""

import io
import json
from pathlib import Path

from validation.scene_lint.findings import Finding, Verdict


#============================================
# JSONL writer
#============================================

def write_findings_jsonl(findings: list[Finding], output: io.TextIOBase | Path | str) -> None:
	"""
	Write findings to JSONL format (one JSON object per line).

	Args:
		findings: List of Finding objects.
		output: File object, path string, or Path object. If file object,
			write to it without closing. Otherwise, open the path for writing.
	"""
	if isinstance(output, (str, Path)):
		with open(output, 'w', encoding='utf-8') as f:
			for finding in findings:
				f.write(json.dumps(finding.to_dict(), separators=(',', ':')))
				f.write('\n')
	else:
		for finding in findings:
			output.write(json.dumps(finding.to_dict(), separators=(',', ':')))
			output.write('\n')


#============================================
# Markdown writer
#============================================

def write_findings_markdown(findings: list[Finding], output: io.TextIOBase | Path | str) -> None:
	"""
	Write findings to Markdown format with per-scene sections.

	Format:
	```
	## <scene_name>

	**Verdict:** BLOCKED / ESCAPE_REQUIRED / CLEAN

	### Findings

	- **<rule>** (confidence: <high/medium/low>)
	  - **Message:** <message>
	  - **Evidence:** <key=value, ...>
	  - **Fixes:** <fix1>, <fix2>, ...

	...

	## <next_scene_name>
	...
	```

	Args:
		findings: List of Finding objects.
		output: File object, path string, or Path object.
	"""
	if isinstance(output, (str, Path)):
		with open(output, 'w', encoding='utf-8') as f:
			_write_findings_markdown_impl(findings, f)
	else:
		_write_findings_markdown_impl(findings, output)


def _write_findings_markdown_impl(findings: list[Finding], out: io.TextIOBase) -> None:
	"""Internal helper to write Markdown output."""
	if not findings:
		out.write('# Scene Lint Report\n\nNo findings.\n')
		return

	out.write('# Scene Lint Report\n\n')

	findings_by_scene = {}
	for finding in findings:
		scene = finding.scene or 'unknown'
		if scene not in findings_by_scene:
			findings_by_scene[scene] = []
		findings_by_scene[scene].append(finding)

	for scene_name in sorted(findings_by_scene.keys()):
		scene_findings = findings_by_scene[scene_name]

		out.write(f'## {scene_name}\n\n')

		verdicts = {f.verdict for f in scene_findings}
		out.write(f'**Verdict:** {", ".join(str(v.value) for v in sorted(verdicts))}\n\n')

		out.write('### Findings\n\n')

		for finding in scene_findings:
			out.write(f'- **{finding.rule}** (confidence: {finding.confidence.value})\n')

			out.write(f'  - **Message:** {finding.message}\n')

			if finding.placement_name:
				out.write(f'  - **Placement:** {finding.placement_name}\n')

			if finding.evidence:
				evidence_items = []
				for key, val in finding.evidence.items():
					if isinstance(val, (list, dict)):
						evidence_items.append(f'{key}={json.dumps(val)}')
					else:
						evidence_items.append(f'{key}={val}')
				out.write(f'  - **Evidence:** {", ".join(evidence_items)}\n')

			if finding.fix_hints:
				out.write('  - **Suggestions:**\n')
				for hint in finding.fix_hints:
					out.write(f'    - {hint}\n')

			out.write('\n')


#============================================
# Summary generator
#============================================

def generate_summary(findings: list[Finding]) -> dict[str, int]:
	"""
	Generate a summary of findings by verdict and rule.

	Args:
		findings: List of Finding objects.

	Returns:
		Dict with keys: 'total', 'blocked', 'escape_required', 'clean',
		and a 'by_rule' sub-dict mapping rule name -> count.
	"""
	summary = {
		'total': len(findings),
		'blocked': 0,
		'escape_required': 0,
		'clean': 0,
		'by_rule': {},
	}

	for finding in findings:
		if finding.verdict == Verdict.BLOCKED:
			summary['blocked'] += 1
		elif finding.verdict == Verdict.ESCAPE_REQUIRED:
			summary['escape_required'] += 1
		elif finding.verdict == Verdict.CLEAN:
			summary['clean'] += 1

		rule = finding.rule
		summary['by_rule'][rule] = summary['by_rule'].get(rule, 0) + 1

	return summary
