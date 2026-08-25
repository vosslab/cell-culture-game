"""Scene card writers: JSON and Markdown formats.

Generates design-lint scorecards for individual scenes. M1 output includes stub
metrics explicitly marked confidence: stub and score: null. Downstream work
will populate real metric values into the same card schema.

Card schema fields (all required, even if null):
	scene: str - scene name
	class: str - detected scene class
	score: float | null - design score (null with confidence: stub in M1)
	confidence: str - 'stub' or metric-confidence values ('high', 'medium', 'low')
	gated_by_render_predictor: bool - whether render predictor blocked scoring
	metrics: dict - metric key -> value pairs (empty {} in M1)
	suggestions: list - advisory suggestions for improvement ([] in M1)
"""

import json


class SceneCard:
	"""
	Represents a single scene's design-lint scorecard.

	Attributes:
		scene: Scene name.
		scene_class: Detected class ('template', 'zoom_detail', etc.).
		score: Design score (null in M1 with confidence='stub').
		confidence: Confidence level ('stub', 'high', 'medium', 'low').
		gated_by_render_predictor: Whether render predictor blocked scoring.
		metrics: Dict of metric results (empty dict {} in M1).
		suggestions: List of advisory suggestions (empty list [] in M1).
	"""

	def __init__(
		self,
		scene: str,
		scene_class: str,
		score: float | None = None,
		confidence: str = 'stub',
		gated_by_render_predictor: bool = False,
		metrics: dict[str, object] | None = None,
		suggestions: list[str] | None = None,
	) -> None:
		self.scene = scene
		self.scene_class = scene_class
		self.score = score
		self.confidence = confidence
		self.gated_by_render_predictor = gated_by_render_predictor
		self.metrics = metrics if metrics is not None else {}
		self.suggestions = suggestions if suggestions is not None else []

	def to_dict(self) -> dict[str, object]:
		"""Convert card to dict for JSON serialization."""
		return {
			'scene': self.scene,
			'class': self.scene_class,
			'score': self.score,
			'confidence': self.confidence,
			'gated_by_render_predictor': self.gated_by_render_predictor,
			'metrics': self.metrics,
			'suggestions': self.suggestions,
		}

	def to_json_line(self) -> str:
		"""Return card as a single JSON line (no newline)."""
		return json.dumps(self.to_dict(), separators=(',', ':'))


def write_cards_jsonl(cards: list[SceneCard]) -> str:
	"""
	Serialize cards to line-delimited JSON format.

	Args:
		cards: List of SceneCard objects.

	Returns:
		String with one JSON object per line (lines joined by newlines).
		Final result ends with a newline if cards list is non-empty.
	"""
	lines = [card.to_json_line() for card in cards]
	if lines:
		return '\n'.join(lines) + '\n'
	return ''


def write_cards_markdown(cards: list[SceneCard]) -> str:
	"""
	Serialize cards to Markdown format (one section per scene).

	Args:
		cards: List of SceneCard objects.

	Returns:
		Markdown string with one ## scene heading per card.
	"""
	sections = []
	sections.append('# Scene Design Cards')
	sections.append('')

	for card in cards:
		sections.append(f'## {card.scene}')
		sections.append('')
		sections.append(f'**Class:** {card.scene_class}')
		sections.append('')
		sections.append(f'**Score:** {card.score} (confidence: {card.confidence})')
		sections.append('')
		sections.append(f'**Gated by render predictor:** {card.gated_by_render_predictor}')
		sections.append('')
		sections.append(f'**Metrics:** {card.metrics or "none"}')
		sections.append('')
		sections.append(f'**Suggestions:** {card.suggestions or "none"}')
		sections.append('')

	return '\n'.join(sections)
