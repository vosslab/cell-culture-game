"""Scene lint finding shape and utilities."""

from dataclasses import dataclass, field
from enum import Enum


class Confidence(str, Enum):
	"""Confidence level derived from scale_source in SIM dump."""
	HIGH = 'high'
	MEDIUM = 'medium'
	LOW = 'low'


class Verdict(str, Enum):
	"""Render-failure verdict for a scene."""
	BLOCKED = 'BLOCKED'
	ESCAPE_REQUIRED = 'ESCAPE_REQUIRED'
	CLEAN = 'CLEAN'


@dataclass
class Finding:
	"""
	Scene lint finding shape matching SCENE_LINT_PLAN.md "Finding shape".

	Attributes:
		scene: Scene name where the finding was detected.
		placement_name: Placement name within the scene (or None if scene-level).
		rule: Rule identifier (e.g., 'B1', 'A1', group_B_10).
		verdict: Render-failure verdict (BLOCKED, ESCAPE_REQUIRED, or CLEAN).
		predicts: List of predicted failure modes (e.g., ['crop_loss', 'distortion']).
		bbox_type: Visual bbox category ('visual_bbox', 'placement_bbox', 'footprint_bbox').
		confidence: Confidence level (high, medium, low) derived from scale_source.
		message: Human-readable finding message.
		evidence: Dict with diagnostic data (e.g., computed values, thresholds).
		fix_hints: List of suggested fixes.
		suppressed_by: Suppression entry name if suppressed, else None.
	"""
	scene: str
	placement_name: str | None
	rule: str
	verdict: Verdict
	predicts: list[str] = field(default_factory=list)
	bbox_type: str = ''
	confidence: Confidence = Confidence.HIGH
	message: str = ''
	evidence: dict[str, object] = field(default_factory=dict)
	fix_hints: list[str] = field(default_factory=list)
	suppressed_by: str | None = None

	def to_dict(self) -> dict[str, object]:
		"""Convert finding to dict for JSONL serialization."""
		return {
			'scene': self.scene,
			'placement_name': self.placement_name,
			'rule': self.rule,
			'verdict': self.verdict.value,
			'predicts': self.predicts,
			'bbox_type': self.bbox_type,
			'confidence': self.confidence.value,
			'message': self.message,
			'evidence': self.evidence,
			'fix_hints': self.fix_hints,
			'suppressed_by': self.suppressed_by,
		}
