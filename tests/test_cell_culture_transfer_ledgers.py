"""Regression coverage for authored cell-culture material ledgers."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_protocol(protocol_name: str) -> dict:
    """Load one production cell-culture protocol by package name."""
    path = REPO_ROOT / "content/protocols/cell_culture" / protocol_name / "protocol.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def interaction(protocol: dict, step_name: str, target: str, occurrence: int = 0) -> dict:
    """Return one authored interaction for a semantic target in sequence order."""
    step = next(step for step in protocol["steps"] if step["step_name"] == step_name)
    matches = [entry for entry in step["sequence"] if entry["target"] == target]
    assert occurrence < len(matches)
    return matches[occurrence]


def state_changes(entry: dict) -> list[dict]:
    """Return declared state writes in interaction order."""
    return [
        operation
        for operation in entry["response"]["scene_operations"]
        if operation["type"] == "ObjectStateChange"
    ]


def state_for(changes: list[dict], target: str) -> dict:
    """Return the one declared state mapping for ``target``."""
    matches = [change["state"] for change in changes if change["target"] == target]
    assert len(matches) == 1
    return matches[0]


def test_trypan_transfers_conserve_the_visible_diamond_to_semicircle_load():
    protocol = load_protocol("trypan_blue_counting")

    stain_aspirate = state_changes(interaction(protocol, "add_trypan_blue_to_chamber", "trypan_blue_tube"))
    assert state_for(stain_aspirate, "trypan_blue_tube") == {"material_volume": 9.99}
    assert state_for(stain_aspirate, "micropipette") == {
        "held_material_name": "trypan_blue", "held_material_volume": 10,
    }
    stain_dispense = state_changes(interaction(protocol, "add_trypan_blue_to_chamber", "hemocytometer_slide.diamond"))
    assert state_for(stain_dispense, "hemocytometer_slide.diamond") == {
        "material_name": "trypan_blue", "material_volume": 0.01,
    }
    assert state_for(stain_dispense, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }

    cells_aspirate = state_changes(interaction(protocol, "add_cell_suspension_to_chamber", "cell_suspension_tube"))
    assert state_for(cells_aspirate, "cell_suspension_tube") == {"material_volume": 14.99}
    assert state_for(cells_aspirate, "micropipette") == {
        "held_material_name": "cell_suspension", "held_material_volume": 10,
    }
    mixed_dispense = state_changes(interaction(protocol, "add_cell_suspension_to_chamber", "hemocytometer_slide.diamond"))
    assert state_for(mixed_dispense, "hemocytometer_slide.diamond") == {
        "material_name": "trypan_blue_mixture", "material_volume": 0.02,
    }
    assert state_for(mixed_dispense, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }

    load_aspirate = state_changes(interaction(protocol, "load_semicircle_chamber", "hemocytometer_slide.diamond"))
    assert state_for(load_aspirate, "hemocytometer_slide.diamond") == {
        "material_name": "trypan_blue_mixture", "material_volume": 0.01,
    }
    assert state_for(load_aspirate, "micropipette") == {
        "held_material_name": "trypan_blue_mixture", "held_material_volume": 10,
    }
    load_dispense = state_changes(interaction(protocol, "load_semicircle_chamber", "hemocytometer_slide.semicircle"))
    assert state_for(load_dispense, "hemocytometer_slide.semicircle") == {
        "material_name": "trypan_blue_mixture", "material_volume": 0.01,
    }
    assert state_for(load_dispense, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }


def test_cell_seeding_authors_the_complete_9_point_6_ml_plate_ledger():
    protocol = load_protocol("cell_seeding_plate_setup")
    assert "9.6 mL" in protocol["steps"][0]["prompt"]

    stock_aspirate = state_changes(interaction(protocol, "prepare_diluted_suspension", "cell_suspension_tube"))
    assert protocol["initial_state"] == [
        {"target": "cell_suspension_tube", "state": {"material_name": "cell_suspension", "material_volume": 14.99}},
        {"target": "media_bottle", "state": {"material_name": "media", "material_volume": 483.1}},
    ]
    assert state_for(stock_aspirate, "cell_suspension_tube") == {"material_volume": 12.59}
    assert state_for(stock_aspirate, "serological_pipette") == {
        "held_material_name": "cell_suspension", "held_material_volume": 2.4,
    }
    stock_dispense = state_changes(interaction(protocol, "prepare_diluted_suspension", "conical_tube_for_dilution", 0))
    assert state_for(stock_dispense, "conical_tube_for_dilution") == {
        "material_name": "cell_suspension", "material_volume": 2.4,
    }
    assert state_for(stock_dispense, "serological_pipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }

    media_aspirate = state_changes(interaction(protocol, "prepare_diluted_suspension", "media_bottle"))
    assert state_for(media_aspirate, "media_bottle") == {"material_volume": 475.9}
    assert state_for(media_aspirate, "serological_pipette") == {
        "held_material_name": "media", "held_material_volume": 7.2,
    }
    media_dispense = state_changes(interaction(protocol, "prepare_diluted_suspension", "conical_tube_for_dilution", 1))
    assert state_for(media_dispense, "conical_tube_for_dilution") == {"material_volume": 9.6}
    assert state_for(media_dispense, "serological_pipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }

    seed_step = next(step for step in protocol["steps"] if step["step_name"] == "seed_96_well_plate")
    seed_aspirations = [entry for entry in seed_step["sequence"] if entry["target"] == "conical_tube_for_dilution"]
    seed_dispenses = [entry for entry in seed_step["sequence"] if entry["target"].startswith("well_plate_96.col_")]
    assert len(seed_aspirations) == len(seed_dispenses) == 12
    assert seed_dispenses[0]["target"] == "well_plate_96.col_1"
    assert seed_dispenses[-1]["target"] == "well_plate_96.col_12"
    for index, (seed_aspirate, seed_dispense) in enumerate(zip(seed_aspirations, seed_dispenses), start=1):
        assert state_for(state_changes(seed_aspirate), "conical_tube_for_dilution") == {
            "material_volume": round(9.6 - index * 0.8, 1),
        }
        assert state_for(state_changes(seed_aspirate), "multichannel_pipette") == {
            "held_material_name": "cell_suspension", "held_material_volume": 100,
        }
        assert state_for(state_changes(seed_dispense), seed_dispense["target"]) == {
            "material_name": "cell_suspension", "material_volume": 100,
        }
        assert state_for(state_changes(seed_dispense), "multichannel_pipette") == {
            "held_material_name": "empty", "held_material_volume": 0,
        }
    assert len(seed_dispenses) * 8 == 96
    assert sum(
        state_for(state_changes(seed_dispense), seed_dispense["target"])["material_volume"] * 8
        for seed_dispense in seed_dispenses
    ) == 9600


def test_passage_reseed_declares_direct_prerequisite_and_split_destinations():
    protocol = load_protocol("passage_pellet_reseed")
    assert protocol["initial_state"] == [
        {"target": "t75_flask", "state": {"material_name": "cell_suspension", "material_volume": 12}},
        {"target": "media_bottle", "state": {"material_name": "media", "material_volume": 491}},
    ]

    transfer = state_changes(interaction(protocol, "transfer_to_conical", "conical_15ml_rack"))
    assert state_for(transfer, "t75_flask") == {"material_volume": 4}
    assert state_for(transfer, "conical_15ml") == {
        "material_name": "cell_suspension", "material_volume": 8,
    }

    supernatant_aspirate = state_changes(interaction(protocol, "aspirate_supernatant", "conical_15ml"))
    assert state_for(supernatant_aspirate, "conical_15ml") == {
        "material_name": "cell_pellet", "material_volume": 0.1,
    }
    assert state_for(supernatant_aspirate, "aspirating_pipette") == {
        "held_material_name": "cell_supernatant", "held_material_volume": 7.9,
    }
    supernatant_discard = state_changes(interaction(protocol, "aspirate_supernatant", "biohazard_decant"))
    assert state_for(supernatant_discard, "biohazard_decant") == {
        "material_name": "cell_supernatant", "material_volume": 7.9,
    }
    assert state_for(supernatant_discard, "aspirating_pipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }

    resuspend_aspirate = state_changes(interaction(protocol, "resuspend_pellet", "media_bottle"))
    assert state_for(resuspend_aspirate, "media_bottle") == {"material_volume": 483.1}
    assert state_for(resuspend_aspirate, "serological_pipette") == {
        "held_material_name": "media", "held_material_volume": 7.9,
    }
    resuspend_dispense = state_changes(interaction(protocol, "resuspend_pellet", "conical_15ml"))
    assert state_for(resuspend_dispense, "conical_15ml") == {
        "material_name": "cell_suspension", "material_volume": 8,
    }
    assert state_for(resuspend_dispense, "serological_pipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }
    assert not any(step["step_name"] == "add_fresh_media_to_plate" for step in protocol["steps"])

    split_aspirate = state_changes(interaction(protocol, "calculate_split_volume", "conical_15ml"))
    assert state_for(split_aspirate, "conical_15ml") == {"material_volume": 1.14}
    assert state_for(split_aspirate, "serological_pipette") == {
        "held_material_name": "cell_suspension", "held_material_volume": 6.86,
    }
    split_dispense = state_changes(interaction(protocol, "calculate_split_volume", "t75_flask"))
    assert state_for(split_dispense, "t75_flask") == {
        "material_name": "cell_suspension", "material_volume": 10.86,
    }
    assert state_for(split_dispense, "serological_pipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }


def test_reseed_scene_exposes_the_milliliter_tool_and_return_destination():
    scene_path = REPO_ROOT / "content/protocols/cell_culture/passage_pellet_reseed/scenes/centrifuge_workspace.yaml"
    scene = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    objects = {placement["object_name"] for placement in scene["add_placements"]}
    assert {"serological_pipette", "t75_flask"} <= objects


def test_cell_supernatant_is_a_closed_material_for_aspiration_and_waste():
    material_path = REPO_ROOT / "content/protocols/cell_culture/passage_pellet_reseed/materials.yaml"
    pipette_path = REPO_ROOT / "content/objects/pipette/aspirating_pipette.yaml"
    waste_path = REPO_ROOT / "content/objects/waste/biohazard_decant.yaml"
    materials = yaml.safe_load(material_path.read_text(encoding="utf-8"))["materials"]
    pipette = yaml.safe_load(pipette_path.read_text(encoding="utf-8"))
    waste = yaml.safe_load(waste_path.read_text(encoding="utf-8"))

    assert "cell_supernatant" in materials
    assert "cell_supernatant" in pipette["state_fields"][0]["allowed"]
    assert "cell_supernatant" in waste["state_fields"][0]["allowed"]


def test_passage_hood_reagent_additions_decrement_sources_and_clear_the_serological_pipette():
    protocol = load_protocol("passage_hood_detachment")
    expected_transfers = (
        ("pbs_wash", "pbs_bottle", 496, "pbs", 4, "pbs", 4),
        ("add_trypsin", "trypsin_bottle", 497, "trypsin", 3, "trypsin", 3),
        ("neutralize_trypsin", "media_bottle", 491, "media", 9, "cell_suspension", 12),
    )
    for step_name, source, source_remaining, material, transfer_volume, flask_material, flask_volume in expected_transfers:
        source_changes = state_changes(interaction(protocol, step_name, source))
        assert state_for(source_changes, source) == {"material_volume": source_remaining}
        assert state_for(source_changes, "serological_pipette") == {
            "held_material_name": material, "held_material_volume": transfer_volume,
        }
        flask_changes = state_changes(interaction(protocol, step_name, "t75_flask"))
        assert state_for(flask_changes, "t75_flask") == {
            "material_name": flask_material, "material_volume": flask_volume,
        }
        assert state_for(flask_changes, "serological_pipette") == {
            "held_material_name": "empty", "held_material_volume": 0,
        }


def test_drug_dilution_authors_a_complete_single_source_working_stock_ledger():
    """Every stated C1V1=C2V2 dilution moves liquid through the visible pipette."""
    protocol = load_protocol("drug_dilution_setup")
    initial = {entry["target"]: entry["state"] for entry in protocol["initial_state"]}
    assert initial == {
        "carboplatin_stock_tube": {"material_name": "carboplatin", "material_volume": 50},
        "media_bottle": {"material_name": "media", "material_volume": 475.9},
        "metformin_stock_tube": {"material_name": "metformin", "material_volume": 50},
    }

    parent_stock_aspirate = state_changes(
        interaction(protocol, "prepare_carb_parent_stock", "carboplatin_stock_tube")
    )
    assert state_for(parent_stock_aspirate, "carboplatin_stock_tube") == {"material_volume": 49.96}
    assert state_for(parent_stock_aspirate, "micropipette") == {
        "held_material_name": "carboplatin", "held_material_volume": 40,
    }
    parent_stock_dispense = state_changes(
        interaction(protocol, "prepare_carb_parent_stock", "microtube_15ml_intermediate")
    )
    assert state_for(parent_stock_dispense, "microtube_15ml_intermediate") == {
        "material_name": "carboplatin", "material_volume": 0.04,
    }
    assert state_for(parent_stock_dispense, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }
    parent_media_aspirate = state_changes(interaction(protocol, "prepare_carb_parent_stock", "media_bottle"))
    assert state_for(parent_media_aspirate, "media_bottle") == {"material_volume": 474.94}
    assert state_for(parent_media_aspirate, "micropipette") == {
        "held_material_name": "media", "held_material_volume": 960,
    }

    working_stocks = [
        ("prepare_carb_working_200um", "tube_G", 200, 500, 0.5, 474.44, "200 &micro;M"),
        ("prepare_carb_working_80um", "tube_F", 80, 200, 0.3, 473.64, "80 &micro;M"),
        ("prepare_carb_working_40um", "tube_E", 40, 100, 0.2, 472.74, "40 &micro;M"),
        ("prepare_carb_working_20um", "tube_D", 20, 50, 0.15, 471.79, "20 &micro;M"),
        ("prepare_carb_working_8um", "tube_C", 8, 20, 0.13, 470.81, "8 &micro;M"),
        ("prepare_carb_working_4um", "tube_B", 4, 10, 0.12, 469.82, "4 &micro;M"),
    ]
    for step_name, tube_name, concentration, drug_volume, parent_remaining, media_remaining, concentration_text in working_stocks:
        step = next(step for step in protocol["steps"] if step["step_name"] == step_name)
        assert concentration_text in step["prompt"]
        assert f"{drug_volume} &micro;L" in step["prompt"]

        drug_aspirate = state_changes(interaction(protocol, step_name, "microtube_15ml_intermediate"))
        assert state_for(drug_aspirate, "microtube_15ml_intermediate") == {"material_volume": parent_remaining}
        assert state_for(drug_aspirate, "micropipette") == {
            "held_material_name": "carboplatin", "held_material_volume": drug_volume,
        }
        drug_dispense = state_changes(interaction(protocol, step_name, "dilution_tube_rack_8", 0))
        tube_target = f"dilution_tube_rack_8.{tube_name}"
        assert state_for(drug_dispense, tube_target) == {
            "material_name": "carboplatin", "material_volume": drug_volume,
        }
        assert state_for(drug_dispense, "micropipette") == {
            "held_material_name": "empty", "held_material_volume": 0,
        }

        media_aspirate = state_changes(interaction(protocol, step_name, "media_bottle"))
        media_volume = 1000 - drug_volume
        assert state_for(media_aspirate, "media_bottle") == {"material_volume": media_remaining}
        assert state_for(media_aspirate, "micropipette") == {
            "held_material_name": "media", "held_material_volume": media_volume,
        }
        media_dispense = state_changes(interaction(protocol, step_name, "dilution_tube_rack_8", 1))
        assert state_for(media_dispense, tube_target) == {"material_volume": 1000}
        assert state_for(media_dispense, "micropipette") == {
            "held_material_name": "empty", "held_material_volume": 0,
        }
        assert f"{concentration} &micro;M" in step["prompt"]

    metformin_aspirate = state_changes(interaction(protocol, "prepare_metformin_200mm", "metformin_stock_tube"))
    assert state_for(metformin_aspirate, "metformin_stock_tube") == {"material_volume": 49.94}
    assert state_for(metformin_aspirate, "micropipette") == {
        "held_material_name": "metformin", "held_material_volume": 60,
    }
    metformin_dispense = state_changes(
        interaction(protocol, "prepare_metformin_200mm", "metformin_working_tube", 0)
    )
    assert state_for(metformin_dispense, "metformin_working_tube") == {
        "material_name": "metformin", "material_volume": 60,
    }
    assert state_for(metformin_dispense, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }
    metformin_media = state_changes(interaction(protocol, "prepare_metformin_200mm", "media_bottle"))
    assert state_for(metformin_media, "media_bottle") == {"material_volume": 469.58}
    assert state_for(metformin_media, "micropipette") == {
        "held_material_name": "media", "held_material_volume": 240,
    }
    metformin_final = state_changes(
        interaction(protocol, "prepare_metformin_200mm", "metformin_working_tube", 1)
    )
    assert state_for(metformin_final, "metformin_working_tube") == {"material_volume": 300}
    assert state_for(metformin_final, "micropipette") == {
        "held_material_name": "empty", "held_material_volume": 0,
    }
