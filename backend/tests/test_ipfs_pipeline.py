import json
import os
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from app.services.ipfs_utils import (
    build_gateway_url,
    build_ipfs_uri,
    compute_cidv1_raw_sha256,
    is_valid_cid,
    normalize_cid,
)
from app.services.material_access_store import MaterialAccessStore
from app.services.storage_service import StorageService

# Sample genuine CIF content for testing
SAMPLE_CIF_CONTENT = (
    "data_Mg2Si\n"
    "_chemical_formula_sum 'Mg2 Si'\n"
    "_symmetry_space_group_name_H-M 'F m -3 m'\n"
    "_cell_length_a 6.35\n"
    "_cell_length_b 6.35\n"
    "_cell_length_c 6.35\n"
    "_cell_angle_alpha 90.0\n"
    "_cell_angle_beta 90.0\n"
    "_cell_angle_gamma 90.0\n"
    "loop_\n"
    " _atom_site_label\n"
    " _atom_site_fract_x\n"
    " _atom_site_fract_y\n"
    " _atom_site_fract_z\n"
    " Mg 0.25 0.25 0.25\n"
    " Si 0.00 0.00 0.00\n"
)


# ============================================================================
# 1. CID & URL HANDLING UNIT TESTS (Phase 5)
# ============================================================================

class TestIpfsUrlAndCidUtils:
    def test_normalize_cid_various_malformed_formats(self):
        raw_cid = "bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y"
        
        # Test bare CID
        assert normalize_cid(raw_cid) == raw_cid
        
        # Test single slash ipfs:/
        assert normalize_cid(f"ipfs:/{raw_cid}") == raw_cid
        
        # Test double slash ipfs://
        assert normalize_cid(f"ipfs://{raw_cid}") == raw_cid
        
        # Test colon prefix ipfs:
        assert normalize_cid(f"ipfs:{raw_cid}") == raw_cid
        
        # Test path prefix /ipfs/
        assert normalize_cid(f"/ipfs/{raw_cid}") == raw_cid
        assert normalize_cid(f"ipfs/{raw_cid}") == raw_cid
        
        # Test malformed nested /ipfs/ipfs:/...
        assert normalize_cid(f"http://127.0.0.1:8080/ipfs/ipfs:/{raw_cid}") == raw_cid
        assert normalize_cid(f"http://127.0.0.1:8080/ipfs/ipfs://{raw_cid}") == raw_cid
        assert normalize_cid(f"http://127.0.0.1:8080/ipfs/{raw_cid}") == raw_cid
        
        # Test local-sha256 prefix
        assert normalize_cid("local-sha256:abcd1234ef5678") == "abcd1234ef5678"

    def test_build_gateway_url_prevents_duplicate_segments(self):
        raw_cid = "bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y"
        expected = f"http://127.0.0.1:8080/ipfs/{raw_cid}"
        
        # Base with or without trailing /ipfs
        assert build_gateway_url("http://127.0.0.1:8080", raw_cid) == expected
        assert build_gateway_url("http://127.0.0.1:8080/ipfs", raw_cid) == expected
        assert build_gateway_url("http://127.0.0.1:8080/ipfs/", raw_cid) == expected
        
        # Input with various prefixes
        assert build_gateway_url("http://127.0.0.1:8080", f"ipfs:/{raw_cid}") == expected
        assert build_gateway_url("http://127.0.0.1:8080", f"ipfs://{raw_cid}") == expected
        assert build_gateway_url("http://127.0.0.1:8080", f"/ipfs/{raw_cid}") == expected
        assert build_gateway_url("http://127.0.0.1:8080", f"http://127.0.0.1:8080/ipfs/{raw_cid}") == expected

    def test_build_ipfs_uri(self):
        raw_cid = "bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y"
        expected = f"ipfs://{raw_cid}"
        
        assert build_ipfs_uri(raw_cid) == expected
        assert build_ipfs_uri(f"ipfs:/{raw_cid}") == expected
        assert build_ipfs_uri(f"ipfs://{raw_cid}") == expected
        assert build_ipfs_uri(f"/ipfs/{raw_cid}") == expected

    def test_is_valid_cid(self):
        # CIDv1 Base32 (bafk..., bafy...)
        assert is_valid_cid("bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y") is True
        assert is_valid_cid("bafybeicq6oangez2j3a2v4jndkfe7ajjyivphfogybuwtkovuv3azpp5pe") is True
        
        # CIDv0 Base58 (Qm...)
        assert is_valid_cid("QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco") is True
        
        # Non-CID inputs
        assert is_valid_cid("not-a-cid") is False
        assert is_valid_cid("") is False
        assert is_valid_cid("local-sha256:abcd") is False


# ============================================================================
# 2. OFFLINE / MOCKED CONNECTION TESTS (Phase 2 & Phase 3)
# ============================================================================

class TestIpfsOfflineAndUnit:
    def test_daemon_offline_returns_cache_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "cache.json")
        monkeypatch.setenv("IPFS_API_URL", "")

        svc = StorageService(database_path=tmp_path / "test.sqlite3")
        status = svc.get_node_status()
        assert status["online"] is False
        assert status["mode"] == "local-cache"

    def test_upload_fallback_when_daemon_unconfigured(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "cache.json")
        monkeypatch.setenv("IPFS_API_URL", "")

        svc = StorageService(database_path=tmp_path / "test.sqlite3")
        res = svc.upload_file("offline.cif", b"DATA CIF", content_type="chemical/x-cif")

        assert res["is_ipfs"] is False
        assert res["is_pinned"] is False
        assert res["is_verified"] is False
        assert "local-cache" in res["storage_backend"]
        assert res["storage_reference"].startswith("local-sha256:")

    def test_mocked_pin_failure_detected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "cache.json")
        monkeypatch.setenv("IPFS_API_URL", "http://ipfs.mock:5001")

        class MockResponse:
            def __init__(self, status_code, json_data, text=""):
                self.status_code = status_code
                self._json = json_data
                self.text = text
                self.content = text.encode("utf-8")

            def raise_for_status(self):
                pass

            def json(self):
                return self._json

        def mock_post(url, **kwargs):
            if "/pin/ls" in url:
                return MockResponse(500, {}, text="pin not found")
            if "/pin/add" in url:
                return MockResponse(500, {}, text="pin add error")
            if url.rstrip("/").endswith("/add"):
                return MockResponse(200, {"Hash": "bafkreitestmockcid1234567890"})
            if "/cat" in url:
                return MockResponse(200, {}, text="test content")
            return MockResponse(200, {})

        monkeypatch.setattr(module.httpx, "post", mock_post)
        svc = StorageService(database_path=tmp_path / "test.sqlite3")
        res = svc.upload_file("test.txt", b"test content")

        assert res["cid"] == "bafkreitestmockcid1234567890"
        assert res["is_ipfs"] is True
        assert res["is_pinned"] is False


# ============================================================================
# 3. REAL KUBO INTEGRATION TESTS (Phase 2, 3, 4, 6, 7, 8, 11)
# ============================================================================

def is_local_kubo_running() -> bool:
    """Checks if a real local Kubo node is online on 127.0.0.1:5001."""
    try:
        r = httpx.post("http://127.0.0.1:5001/api/v0/version", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not is_local_kubo_running(), reason="Local Kubo IPFS node is not running on 127.0.0.1:5001")
class TestRealKuboNodeIntegration:
    def test_real_kubo_status_and_peer_id(self):
        svc = StorageService()
        status = svc.get_node_status()
        assert status["online"] is True
        assert status["provider"] == "kubo"
        assert status["version"] is not None
        assert status["peer_id"] is not None
        assert status["api_url"] == "http://127.0.0.1:5001"

    def test_real_kubo_upload_pin_cat_and_gateway_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "real_store.json")

        db_path = tmp_path / "real_matchain.sqlite3"
        svc = StorageService(database_path=db_path)

        test_payload = b"MatChain Real IPFS Verification Token - 2026-11-21"
        upload_res = svc.upload_file("verify_token.txt", test_payload, content_type="text/plain")

        # 1. Verify upload response metadata
        assert upload_res["is_ipfs"] is True
        assert upload_res["is_pinned"] is True
        assert upload_res["is_verified"] is True
        cid = upload_res["cid"]
        assert cid.startswith("bafk")
        assert not cid.startswith("ipfs:")

        # 2. Verify URL formats
        assert upload_res["local_gateway_url"] == f"http://127.0.0.1:8080/ipfs/{cid}"
        assert upload_res["ipfs_uri"] == f"ipfs://{cid}"
        assert "ipfs:/" not in upload_res["local_gateway_url"]

        # 3. Retrieve through Kubo RPC cat
        cat_bytes = svc.get_raw_bytes(cid)
        assert cat_bytes == test_payload

        # 4. Retrieve through Local Gateway HTTP GET
        gw_res = httpx.get(f"http://127.0.0.1:8080/ipfs/{cid}", timeout=4.0)
        assert gw_res.status_code == 200
        assert gw_res.content == test_payload

        # 5. Verify database persistence
        access_rec = svc.access_store.get_by_cid(cid)
        assert access_rec is not None
        assert access_rec["cid"] == cid
        assert access_rec["is_pinned"] is True
        assert access_rec["is_verified"] is True
        assert access_rec["storage_provider"] == "kubo"

    def test_real_kubo_cif_structure_and_mfs_visibility(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "real_store.json")

        db_path = tmp_path / "real_matchain.sqlite3"
        svc = StorageService(database_path=db_path)

        cif_bytes = SAMPLE_CIF_CONTENT.encode("utf-8")
        filename = "Mg2Si_test_structure.cif"
        upload_res = svc.upload_file(filename, cif_bytes, content_type="chemical/x-cif")

        cid = upload_res["cid"]
        assert upload_res["is_ipfs"] is True
        assert upload_res["is_pinned"] is True

        # Check that file reflects in Kubo MFS (visible in IPFS Desktop Files tab)
        mfs_stat = httpx.post("http://127.0.0.1:5001/api/v0/files/stat", params={"arg": f"/{filename}"}, timeout=3.0)
        assert mfs_stat.status_code == 200
        stat_data = mfs_stat.json()
        assert stat_data.get("Hash") == cid

        # Content retrieval check
        retrieved = svc.get_content(cid)
        assert retrieved["filename"] == filename
        assert retrieved["raw_text"] == SAMPLE_CIF_CONTENT

    def test_real_kubo_confidential_encryption_and_decryption(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "real_store.json")

        db_path = tmp_path / "real_matchain.sqlite3"
        svc = StorageService(database_path=db_path)

        seller_wallet = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
        buyer_wallet = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
        unauthorized_wallet = "0xcd3B766CCDd6AE721141F452C550Ca635964ce71"

        raw_cif = SAMPLE_CIF_CONTENT.encode("utf-8")
        upload_res = svc.upload_file(
            "proprietary_mg2si.cif",
            raw_cif,
            content_type="chemical/x-cif",
            owner_wallet=seller_wallet,
            is_confidential=True,
            material_hash="0x11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        )

        cid = upload_res["cid"]
        assert upload_res["is_encrypted"] is True

        # 1. Gateway serves ONLY encrypted ciphertext
        gw_res = httpx.get(f"http://127.0.0.1:8080/ipfs/{cid}", timeout=4.0)
        assert gw_res.status_code == 200
        assert gw_res.content != raw_cif  # Public gateway cannot see plaintext!
        assert len(gw_res.content) > 0

        # 2. Unauthorized requester is strictly rejected
        with pytest.raises(PermissionError):
            svc.get_content(cid, requester_wallet=unauthorized_wallet, is_verified_purchaser=False)

        # 3. Seller/Owner receives decrypted content
        seller_data = svc.get_content(cid, requester_wallet=seller_wallet)
        assert seller_data["raw_text"] == SAMPLE_CIF_CONTENT
        assert seller_data["source"] == "owner_decrypted"

        # 4. Verified Purchaser receives decrypted content without key leak
        buyer_data = svc.get_content(cid, requester_wallet=buyer_wallet, is_verified_purchaser=True)
        assert buyer_data["raw_text"] == SAMPLE_CIF_CONTENT
        assert buyer_data["source"] == "verified_purchase_decrypted"
        assert "share_bundle" not in buyer_data  # Keys/bundles not leaked to buyer

    def test_real_kubo_persistence_survives_restart(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import app.services.storage_service as module
        monkeypatch.setattr(module, "LOCAL_STORE_PATH", tmp_path / "real_store.json")

        db_path = tmp_path / "real_matchain.sqlite3"
        svc1 = StorageService(database_path=db_path)

        data = {"formula": "Mg2Si", "band_gap": 0.6, "timestamp": 1700000000}
        res1 = svc1.upload_json(data)
        cid = res1["cid"]

        # Simulate backend restart with a new StorageService instance
        svc2 = StorageService(database_path=db_path)
        retrieved = svc2.get_content(cid)
        assert retrieved["data"]["formula"] == "Mg2Si"
        assert retrieved["data"]["band_gap"] == 0.6
