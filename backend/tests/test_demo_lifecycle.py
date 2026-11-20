import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app, storage
from app.services.demo_asset_service import (
    MG2SI_HASH,
    TARGET_BAND_GAP,
    TARGET_DENSITY,
    TARGET_FORMATION_ENERGY,
    TARGET_N_CANDIDATES,
    TARGET_OBJECTIVE,
    TARGET_RELAX,
    TARGET_TAU,
    TARGET_TOP_K,
    get_demo_reference_asset,
    is_demo_recipe,
    should_select_demo_asset,
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.services.storage_service as storage_module
    from app.services.storage_service import StorageService

    db_path = tmp_path / "test_demo_lifecycle.sqlite3"
    content_store = tmp_path / "test_ipfs_store.json"

    monkeypatch.setenv("IPFS_API_URL", "")
    monkeypatch.setattr(storage_module, "LOCAL_STORE_PATH", content_store)
    test_storage = StorageService(database_path=db_path)
    monkeypatch.setattr("app.main.storage", test_storage)

    return TestClient(app)


def test_exact_recipe_matching():
    exact_cond = {
        "formation_energy_per_atom": TARGET_FORMATION_ENERGY,
        "band_gap": TARGET_BAND_GAP,
        "density": TARGET_DENSITY,
    }

    # 1. Exact match
    assert is_demo_recipe(
        TARGET_OBJECTIVE, exact_cond, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is True

    # 2. Text normalization variation (uppercase, extra whitespace, different punctuation)
    variant_obj = "  DISCOVER stable mg-si based lightweight semiconductor materials, inspired by Mg2Si with potential thermoelectric applications!  "
    assert is_demo_recipe(
        variant_obj, exact_cond, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is True

    # 3. Unrelated objective
    assert is_demo_recipe(
        "Superconducting cuprate high Tc", exact_cond, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is False

    # 4. Numerical mismatch in formation energy
    bad_fe = dict(exact_cond, formation_energy_per_atom=-0.50)
    assert is_demo_recipe(
        TARGET_OBJECTIVE, bad_fe, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is False

    # 5. Numerical mismatch in density
    bad_dens = dict(exact_cond, density=3.5)
    assert is_demo_recipe(
        TARGET_OBJECTIVE, bad_dens, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is False

    # 6. Sampling count mismatch
    assert is_demo_recipe(
        TARGET_OBJECTIVE, exact_cond, 50, TARGET_TAU, TARGET_TOP_K, TARGET_RELAX
    ) is False

    # 7. Tau mismatch
    assert is_demo_recipe(
        TARGET_OBJECTIVE, exact_cond, TARGET_N_CANDIDATES, 0.20, TARGET_TOP_K, TARGET_RELAX
    ) is False

    # 8. Relaxation disabled
    assert is_demo_recipe(
        TARGET_OBJECTIVE, exact_cond, TARGET_N_CANDIDATES, TARGET_TAU, TARGET_TOP_K, False
    ) is False


def test_force_demo_controls(monkeypatch):
    # FORCE_DEMO_ON
    monkeypatch.setenv("FORCE_DEMO_ON", "true")
    monkeypatch.delenv("FORCE_DEMO_OFF", raising=False)
    assert should_select_demo_asset(is_matching=True) is True
    assert should_select_demo_asset(is_matching=False) is False

    # FORCE_DEMO_OFF overrides ON
    monkeypatch.setenv("FORCE_DEMO_OFF", "true")
    assert should_select_demo_asset(is_matching=True) is False


def test_demo_reference_asset_scientific_integrity():
    asset = get_demo_reference_asset()

    assert asset["formula"] == "Mg2Si"
    assert asset["reduced_formula"] == "Mg2Si"
    assert asset["material_hash"] == MG2SI_HASH
    assert asset["crystal_system"] == "Cubic"
    assert asset["space_group"] == "Fm-3m (225)"
    assert asset["lattice_parameter_a"] == 6.351
    assert asset["e_hull"] == 0.0000
    assert asset["predicted_formation_energy"] == -0.2670
    assert asset["band_gap"] == 0.60
    assert abs(asset["density"] - 1.9886) < 0.01

    # Disclosures & honest labels
    assert "DEMO REFERENCE" in asset["disclosure"]
    assert "NOT A LIVE AI-GENERATED DISCOVERY" in asset["disclosure"]
    assert "curator, not inventor" in asset["registration_label"]

    # Structure payload consistency
    payload = asset["structure_payload"]
    assert len(payload["species"]) == 12
    assert payload["species"].count("Si") == 4
    assert payload["species"].count("Mg") == 8
    assert len(payload["frac_coords"]) == 12


def test_demo_api_endpoints(client):
    # 1. Reference definition
    resp = client.get("/api/demo/reference")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reference_asset"]["formula"] == "Mg2Si"
    assert data["recipe"]["target_condition"]["formation_energy_per_atom"] == -0.25
    assert data["recipe"]["n_candidates"] == 200

    # 2. Register demo material (idempotent)
    wallet = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
    reg_resp = client.post("/api/demo/register", json={"owner_wallet": wallet})
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["material_hash"] == MG2SI_HASH
    assert reg_data["cid"] is not None
    assert reg_data["owner_wallet"].lower() == wallet.lower()

    # Second registration should be idempotent
    reg_resp2 = client.post("/api/demo/register", json={"owner_wallet": wallet})
    assert reg_resp2.status_code == 200
    assert reg_resp2.json()["material_hash"] == MG2SI_HASH

    # 3. Query status
    status_resp = client.get("/api/demo/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["material_hash"] == MG2SI_HASH
    assert status_data["registered_in_store"] is True
    assert status_data["ipfs_cid"] is not None

    # 4. Material lookup
    mat_resp = client.get(f"/api/materials/{MG2SI_HASH}")
    assert mat_resp.status_code == 200
    assert mat_resp.json()["formula"] == "Mg2Si"

    # 5. Stability audit check
    audit_resp = client.post("/api/marketplace/audit", json={"material_hash": MG2SI_HASH})
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["recommendation"] == "APPROVED_FOR_MARKETPLACE"
    assert audit_data["e_hull_passed"] is True
    assert audit_data["distance_passed"] is True
    assert audit_data["consensus_passed"] is True
    assert audit_data["overall_score"] >= 0.95

    # 6. Reset
    reset_resp = client.post("/api/demo/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "reset"

    # Status after reset
    status_after = client.get("/api/demo/status").json()
    assert status_after["registered_in_store"] is False
