"""Regression coverage for the physically executable Day-2 media adjustment."""

from pathlib import Path

import yaml

from validation.stepper.findings import Level
from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol, walk_sequence_runner


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml"
)


def load_protocol() -> dict:
    """Load the production media-adjustment mini-protocol."""
    return yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))


def state_changes(interaction: dict) -> list[dict]:
    """Return state writes in one learner-visible interaction."""
    return [
        operation
        for operation in interaction["response"]["scene_operations"]
        if operation["type"] == "ObjectStateChange"
    ]


def state_for(interaction: dict, target: str) -> dict:
    """Return the unique state mapping authored for a target."""
    matches = [operation["state"] for operation in state_changes(interaction) if operation["target"] == target]
    assert len(matches) == 1
    return matches[0]


def error_codes(emitter) -> list[str]:
    """Return only strict-stepper errors from a completed protocol walk."""
    return [finding.code for finding in emitter.findings if finding.level == Level.ERROR]


def test_media_adjustment_uses_real_column_strokes_and_row_a_transfers() -> None:
    """No partial multichannel block is disguised as one pipetting stroke."""
    protocol = load_protocol()
    steps = {step["step_name"]: step for step in protocol["steps"]}

    first_columns = [
        interaction["target"]
        for interaction in steps["fill_columns_1_6"]["sequence"]
        if interaction["target"].startswith("well_plate_96.col_")
    ]
    second_columns = [
        interaction["target"]
        for interaction in steps["fill_columns_7_12"]["sequence"]
        if interaction["target"].startswith("well_plate_96.col_")
    ]
    assert first_columns == [f"well_plate_96.col_{column}" for column in range(1, 7)]
    assert second_columns == [f"well_plate_96.col_{column}" for column in range(7, 13)]
    assert not any(".block_" in target for target in first_columns + second_columns)

    row_a = steps["correct_row_a_controls"]["sequence"]
    row_a_wells = [interaction["target"] for interaction in row_a if interaction["target"].startswith("well_plate_96.A")]
    assert row_a_wells == [f"well_plate_96.A{column}" for column in range(1, 13)]


def test_media_adjustment_conserves_all_8_point_94_ml_in_direct_play() -> None:
    """Every media aspiration is paired with a cleared visible pipette dispense."""
    protocol = load_protocol()
    source_writes = []
    for step in protocol["steps"]:
        for interaction in step["sequence"]:
            if interaction["target"] == "media_bottle":
                source_writes.append(state_for(interaction, "media_bottle")["material_volume"])

    assert source_writes[-1] == 460.64
    assert protocol["initial_state"][0] == {
        "target": "media_bottle",
        "state": {"material_name": "media", "material_volume": 469.58},
    }
    assert round(469.58 - source_writes[-1], 2) == 8.94

    _, _, emitter = walk_protocol(
        load_content_tree(REPO_ROOT), "plate_drug_treatment_media_adjustment", quiet=True,
    )
    assert error_codes(emitter) == []


def test_cell_culture_runner_carries_media_adjustment_without_ledger_errors() -> None:
    """The leaf contributes no ledger failure when runner-owned seeds take precedence."""
    _, _, emitter = walk_sequence_runner(load_content_tree(REPO_ROOT), "cell_culture_full", quiet=True)
    assert not [
        finding
        for finding in emitter.findings
        if finding.level == Level.ERROR and finding.protocol_name == "plate_drug_treatment_media_adjustment"
    ]
