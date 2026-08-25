"""Shared confidence policy for predictive Group B scene-lint rules."""

# local repo modules
from validation.scene_lint.findings import Confidence


#============================================

def confidence_from_scale_source(scale_source: str) -> Confidence:
	"""Map simulator provenance to the advisory finding confidence level."""
	if scale_source == 'cm_model':
		return Confidence.HIGH
	if scale_source == 'fallback_authored':
		return Confidence.MEDIUM
	return Confidence.LOW
