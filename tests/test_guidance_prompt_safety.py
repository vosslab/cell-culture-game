"""Regression coverage for evidence-led select-step prompts."""

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


PROMPT_CASES = [
	(
		"passage_hood_detachment",
		"inspect_confluence",
		("inspect", "compare", "choose"),
		("visible", "coverage", "spacing"),
		("70-80%", "ready to passage"),
	),
	(
		"sdspage_destain_gel_rock",
		"judge_destain_endpoint",
		("inspect", "select"),
		("visible", "background", "band"),
		("clear background and distinct bands",),
	),
	(
		"sdspage_image_gel",
		"interpret_ladder_and_sample_lanes",
		("review", "select"),
		("visible", "ladder", "sample-band", "additional bands"),
		("24-28 kDa", "expected-band conclusion"),
	),
]


def load_step(protocol_name: str, step_name: str) -> dict:
	"""Load one authored step from its canonical protocol YAML."""
	path = REPO_ROOT / "content" / "protocols"
	protocol_path = next(path.glob(f"**/{protocol_name}/protocol.yaml"))
	protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
	return next(step for step in protocol["steps"] if step["step_name"] == step_name)


@pytest.mark.parametrize(
	"protocol_name,step_name,actions,evidence,answer_fragments",
	PROMPT_CASES,
	ids=[f"{protocol}/{step}" for protocol, step, *_ in PROMPT_CASES],
)
def test_select_prompts_request_observable_evidence_without_answer(
	protocol_name: str,
	step_name: str,
	actions: tuple[str, ...],
	evidence: tuple[str, ...],
	answer_fragments: tuple[str, ...],
) -> None:
	"""Pre-attempt prompts guide observation without stating the fixed result."""
	prompt = " ".join(load_step(protocol_name, step_name)["prompt"].lower().split())

	assert all(term in prompt for term in actions + evidence)
	assert not any(fragment.lower() in prompt for fragment in answer_fragments)
