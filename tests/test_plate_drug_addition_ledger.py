"""Regression coverage for the visible per-well drug-addition ledger."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml"


def load_protocol() -> dict:
    """Load the production drug-addition mini-protocol."""
    return yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))


def object_state(interaction: dict, target: str) -> dict:
    """Return the one state mutation authored for a visible target."""
    matches = [
        operation["state"]
        for operation in interaction["response"]["scene_operations"]
        if operation["type"] == "ObjectStateChange" and operation["target"] == target
    ]
    assert len(matches) == 1
    return matches[0]


def test_direct_launch_seeds_the_real_media_and_working_stock_handoff() -> None:
    protocol = load_protocol()
    initial = {entry["target"]: entry["state"] for entry in protocol["initial_state"]}

    assert initial["dilution_tube_rack_8.tube_B"] == {
        "material_name": "carboplatin", "material_volume": 1000,
    }
    assert initial["microtube_15ml_intermediate"] == {
        "material_name": "carboplatin", "material_volume": 0.12,
    }
    assert initial["metformin_working_tube"] == {
        "material_name": "metformin", "material_volume": 300,
    }
    assert initial["well_plate_96.block_B_H_1_6"]["material_volume"] == 195
    assert initial["well_plate_96.block_B_H_7_12"]["material_volume"] == 190


def test_carboplatin_rows_are_twelve_visible_five_ul_dispenses_from_one_60_ul_draw() -> None:
    protocol = load_protocol()
    expected_rows = "BCDEFGH"
    sources = [
        "dilution_tube_rack_8.tube_B",
        "dilution_tube_rack_8.tube_C",
        "dilution_tube_rack_8.tube_D",
        "dilution_tube_rack_8.tube_E",
        "dilution_tube_rack_8.tube_F",
        "dilution_tube_rack_8.tube_G",
        "microtube_15ml_intermediate",
    ]

    for offset, row in enumerate(expected_rows):
        step = protocol["steps"][offset]
        assert step["step_name"] == f"add_carb_row_{row.lower()}"
        source = next(entry for entry in step["sequence"] if entry["target"] == sources[offset])
        expected_remaining = 0.06 if row == "H" else 940
        assert object_state(source, source["target"]) == {"material_volume": expected_remaining}
        assert object_state(source, "micropipette") == {
            "held_material_name": "carboplatin", "held_material_volume": 60,
        }

        wells = [entry for entry in step["sequence"] if entry["target"].startswith(f"well_plate_96.{row}")]
        assert [entry["target"] for entry in wells] == [f"well_plate_96.{row}{column}" for column in range(1, 13)]
        assert [object_state(entry, "micropipette")["held_material_volume"] for entry in wells] == list(range(55, -1, -5))
        assert object_state(wells[-1], "micropipette") == {
            "held_material_name": "empty", "held_material_volume": 0,
        }


def test_metformin_uses_two_visible_120_ul_draws_for_all_48_combo_wells() -> None:
    protocol = load_protocol()
    step = next(entry for entry in protocol["steps"] if entry["step_name"] == "add_metformin_cols_7_12")
    sources = [entry for entry in step["sequence"] if entry["target"] == "metformin_working_tube"]
    assert [object_state(entry, "metformin_working_tube") for entry in sources] == [
        {"material_volume": 180}, {"material_volume": 60},
    ]
    assert all(object_state(entry, "micropipette")["held_material_volume"] == 120 for entry in sources)

    wells = [entry for entry in step["sequence"] if entry["target"].startswith("well_plate_96.")]
    assert len(wells) == 48
    assert all(object_state(entry, entry["target"])["material_volume"] == 200 for entry in wells)
    assert object_state(wells[-1], "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }
