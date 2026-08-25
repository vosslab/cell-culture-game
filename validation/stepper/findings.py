"""Finding dataclass and emitter for semantic walker findings."""

from dataclasses import dataclass

import validation.shared_toolkit.findings


@dataclass(frozen=True)
class Finding:
	"""
	A semantic finding: error or warning from the stepper.

	Attributes:
		level: ERROR or WARNING.
		protocol_name: Name of the protocol being stepped.
		step_name: Name of the step containing the finding (optional).
		interaction_index: 0-based interaction index within the step (optional).
		target: Target object or control name (optional).
		file_path: Path to the YAML file containing the finding.
		code: Stable short identifier for this error class.
		message: Human-readable message describing the finding.
		spec_cite: REQUIRED - docs/specs/<file>.md section or anchor governing this rule.
	"""
	level: validation.shared_toolkit.findings.Severity
	protocol_name: str
	step_name: str | None
	interaction_index: int | None
	target: str | None
	file_path: str
	code: str
	message: str
	spec_cite: str

	def __str__(self) -> str:
		"""Format the finding as a human-readable string."""
		lines = []
		lines.append(f"  {self.level.value} [{self.code}]: {self.message}")
		lines.append(f"  per {self.spec_cite}")
		return '\n'.join(lines)


class FindingEmitter:
	"""Emits findings to stdout in a standard format."""

	def __init__(self, verbose: bool = False) -> None:
		"""
		Initialize the emitter.

		Args:
			verbose: If True, prepare data for diagnostic summary (findings, per-protocol counts).
				     Verbose-mode output is generated externally by dashboard/aggregator.
		"""
		self.verbose = verbose
		self.findings: list[Finding] = []
		self.referenced_materials: set[str] = set()  # Track materials referenced in execution
		self._unregistered_dedup: set[str] = set()  # Track (protocol, material_name) pairs already reported for S-UNREGISTERED
		self.final_state: dict | None = None

	def emit_finding(self, finding: Finding) -> None:
		"""Record a finding for later output."""
		self.findings.append(finding)

	def emit_protocol_start(self, protocol_name: str, protocol_path: str, is_sequence_runner: bool = False, leaf_count: int = 0) -> None:
		"""
		Record protocol start info (structured data for JSON output only).

		Args:
			protocol_name: Name of the protocol.
			protocol_path: Path to the protocol YAML file.
			is_sequence_runner: If True, this is a sequence runner.
			leaf_count: Number of leaves in a sequence runner (0 for mini_protocol).
		"""
		# Structured data is collected for JSON/NDJSON output; no text output.
		pass

	def emit_step_transition(self, step_name: str) -> None:
		"""
		Record per-step transition (structured data for JSON output only).

		No text output in any mode.
		"""
		pass

	def emit_scene_operation(self, op_type: str) -> None:
		"""
		Record a scene operation type (structured data for JSON output only).

		No text output in any mode.
		"""
		pass

	def emit_protocol_summary(
		self,
		protocol_name: str,
		protocol_path: str,
		step_count: int,
		interaction_count: int,
		error_count: int,
		warning_count: int,
	) -> None:
		"""
		Record a protocol summary (structured data for JSON output only).

		Args:
			protocol_name: Name of the protocol.
			protocol_path: Path to the protocol YAML file.
			step_count: Number of steps stepped.
			interaction_count: Total interactions stepped.
			error_count: Number of ERROR findings.
			warning_count: Number of WARNING findings.

		No text output in any mode. Per-protocol PASS/FAIL is part of the
		aggregated dashboard (default mode) or diagnostic summary (-v mode).
		"""
		pass

	def emit_leaf_summary(
		self,
		mini_name: str,
		step_count: int,
		interaction_count: int,
		error_count: int,
		warning_count: int,
	) -> None:
		"""
		Record a per-leaf summary for a sequence runner leaf (structured data only).

		Args:
			mini_name: Name of the leaf mini-protocol.
			step_count: Number of steps stepped.
			interaction_count: Total interactions stepped.
			error_count: Number of ERROR findings.
			warning_count: Number of WARNING findings.

		No text output in any mode.
		"""
		pass

	def emit_sequence_runner_summary(
		self,
		protocol_name: str,
		protocol_path: str,
		leaf_count: int,
		step_count: int,
		interaction_count: int,
		error_count: int,
		warning_count: int,
	) -> None:
		"""
		Record a sequence runner summary (structured data for JSON output only).

		Args:
			protocol_name: Name of the sequence runner.
			protocol_path: Path to the protocol YAML file.
			leaf_count: Number of leaves.
			step_count: Total steps across all leaves.
			interaction_count: Total interactions across all leaves.
			error_count: Number of ERROR findings.
			warning_count: Number of WARNING findings.

		No text output in any mode. Per-protocol PASS/FAIL is part of the
		aggregated dashboard (default mode) or diagnostic summary (-v mode).
		"""
		pass

	def print_findings(self) -> None:
		"""
		Print all accumulated findings (structured data for JSON output only).

		In text mode, findings are aggregated and displayed via the dashboard
		or diagnostic summary. Individual per-protocol findings are not printed
		to stdout in text mode.
		"""
		pass

	def has_errors(self) -> bool:
		"""Return True if any ERROR findings are present."""
		return any(f.level == validation.shared_toolkit.findings.Severity.ERROR for f in self.findings)

	def clear(self) -> None:
		"""Clear accumulated findings."""
		self.findings = []

	def track_referenced_material(self, material_name: str) -> None:
		"""Record a material name that was referenced during execution."""
		if material_name:
			self.referenced_materials.add(material_name)


Level = validation.shared_toolkit.findings.Severity

__all__ = ['Level', 'Finding', 'FindingEmitter']
