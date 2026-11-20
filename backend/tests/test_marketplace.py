from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from pathlib import Path
import pytest
from app.main import app, blockchain, storage

TEST_MATERIAL_HASH = "0x7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.services.material_access_store import MaterialAccessStore
    test_db = tmp_path / "test_matchain.sqlite3"
    access_store = MaterialAccessStore(test_db)
    monkeypatch.setattr(storage, "access_store", access_store)

    # Seed approved material metadata for audit tests
    access_store.register_material(
        cid="bafkreitestmarketplacecid",
        material_hash=TEST_MATERIAL_HASH,
        owner_wallet="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        encryption_key_hex="00" * 32,
        encryption_nonce_hex="00" * 12,
        encryption_tag_hex="00" * 16,
        filename="Li3V2(PO4)3.cif",
        content_type="chemical/x-cif",
        size_bytes=1024,
        is_confidential=True,
        public_metadata={
            "formula": "Li3V2(PO4)3",
            "density": 3.12,
            "e_hull": 0.015,
            "predicted_formation_energy": -2.45,
            "consensus_spread": 0.04,
        },
    )
    return TestClient(app)


def test_marketplace_stats(client: TestClient):
    res = client.get("/api/marketplace/stats")
    assert res.status_code == 200
    data = res.json()
    assert "active_listings" in data
    assert "verified_materials" in data
    assert "staked_validators_active" in data
    assert "dispute_window_hours" in data


def test_marketplace_audit(client: TestClient):
    payload = {"material_hash": TEST_MATERIAL_HASH}
    res = client.post("/api/marketplace/audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["material_hash"] == payload["material_hash"]
    assert "e_hull_passed" in data
    assert "overall_score" in data
    assert "recommendation" in data
    assert data["recommendation"] == "APPROVED_FOR_MARKETPLACE"


def test_marketplace_validate_attestation(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    validator_wallet = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
    tx_hash = "0x" + "aa" * 32

    # Mock blockchain contract state & transaction receipt
    monkeypatch.setattr(blockchain, "deployment_matches", lambda: True)
    digest = blockchain.fingerprint(TEST_MATERIAL_HASH)

    mock_registry = MagicMock()
    mock_event = {
        "fingerprint": digest,
        "validator": validator_wallet,
        "stake": blockchain.web3.to_wei("0.05", "ether"),
    }
    mock_registry.events.DiscoveryAttested().process_receipt.return_value = [{"args": mock_event}]
    # discoveries() returns (fingerprint, creator, blockNumber, ipfsCid, metadata, verified)
    mock_registry.functions.discoveries(digest).call.return_value = (
        digest,
        "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        100,
        "bafkreitest",
        "{}",
        True,
    )
    monkeypatch.setattr(blockchain, "registry", mock_registry)
    monkeypatch.setattr(blockchain.web3.eth, "get_transaction_receipt", lambda _tx: {})

    payload = {
        "material_hash": TEST_MATERIAL_HASH,
        "transaction_hash": tx_hash,
        "score": 0.98,
    }
    res = client.post(
        "/api/marketplace/validate",
        json=payload,
        headers={"Authorization": f"Bearer {validator_wallet}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["validation"]["status"] == "verified"
    assert data["validation"]["score"] == 0.98
    assert data["validation"]["validator_wallet"].lower() == validator_wallet.lower()


def test_marketplace_listings_enriched(client: TestClient):
    res = client.get("/api/marketplace/listings")
    assert res.status_code == 200
    listings = res.json()
    assert isinstance(listings, list)

