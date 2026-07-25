"""Behavioral tests for protocol-derived launcher learning hooks."""

# PIP3 modules
import pytest

# local repo modules
import pipeline.gen_protocols


@pytest.mark.parametrize(
	("learning", "expected"),
	[
		(
			{
				"outcomes": (
					"Students completing this mini-protocol will be able to calculate "
					"a dilution volume before seeding a 96-well plate."
				),
			},
			"Calculate a dilution volume before seeding a 96-well plate.",
		),
		(
			{
				"outcomes": (
					"Students completing this protocol will be able to execute the "
					"complete cell-culture-to-readout workflow."
				),
			},
			"Execute the complete cell-culture-to-readout workflow.",
		),
		(
			{
				"outcomes": (
					"Students completing this mini-protocol will be able to prepare the\n"
					"sample mix. Then verify the tube label."
				),
			},
			"Prepare the sample mix.",
		),
		(None, None),
		({}, None),
		({"goals": "Broader purpose."}, None),
	],
)
def test_extract_learning_hook_uses_first_authored_outcome(
	learning: dict[str, str] | None,
	expected: str | None,
) -> None:
	assert pipeline.gen_protocols.extract_learning_hook(learning) == expected


def test_extract_learning_hook_truncates_only_at_word_boundaries() -> None:
	authored_outcome = " ".join(["calibrate"] * 40)
	learning = {
		"outcomes": (
			"Students completing this mini-protocol will be able to "
			f"{authored_outcome}"
		),
	}

	hook = pipeline.gen_protocols.extract_learning_hook(learning)

	assert hook is not None
	assert (
		len(hook) < len(authored_outcome)
		and hook.endswith("...")
		and set(hook.removesuffix("...").split()) <= {"Calibrate", "calibrate"}
	)
