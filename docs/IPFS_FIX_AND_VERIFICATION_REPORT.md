# MatChain — Complete IPFS Storage, Pinning & Retrieval Fix Report

**Date:** November 21, 2026  
**Auditor / Integration Engineer:** MatChain Engineering  
**Status:** FULLY OPERATIONAL & VERIFIED (49/49 Backend Tests Passing, Live Kubo Roundtrip 100% Validated)

---

## 1. Executive Summary

This report documents the comprehensive audit, architectural fix, and live verification of the InterPlanetary File System (IPFS) integration within **MatChain**.

Previously, uploads generated CIDs, but retrieved files failed on IPFS Desktop and the local gateway. The system had constructed invalid URLs containing duplicate path segments (`http://127.0.0.1:8080/ipfs/ipfs:/bafkreig...`), omitted synchronization with Kubo's Mutable File System (MFS), lacked post-upload round-trip verification, and did not persist pinning or verification flags in the database.

Following this stabilization:
1. **Real Kubo Node Integration**: Uploads communicate directly with the host Kubo IPFS daemon (`v0.42.0/desktop`) on RPC port `5001`.
2. **Deterministic CIDv1**: Files generate canonical raw sha256 CIDv1 strings (`bafkrei...`) using standard multiformats.
3. **Canonical Gateway URLs**: URLs are formatted deterministically as `http://127.0.0.1:8080/ipfs/{CID}` and `ipfs://{CID}`, eliminating `ipfs:/` prefix corruptions and redundant slashes.
4. **Recursive Pinning & MFS Visibility**: Every upload is pinned recursively (`/api/v0/pin/add`) and synchronized into Kubo MFS (`/api/v0/files/cp`), making all uploaded materials immediately visible in IPFS Desktop's "Files" tab.
5. **Two-Pronged Roundtrip Integrity Verification**: Prior to marking an upload successful, the backend validates content byte-for-byte against both the Kubo `/cat` RPC endpoint and the HTTP local gateway.
6. **SQLite Schema Migration**: SQLite table `material_access_records` was upgraded to persist `cid_version`, `storage_provider`, `is_pinned`, `is_verified`, and `gateway_url`.
7. **Confidential Encryption Preservation**: AES-256-GCM encryption for private discovery disclosures remains intact; raw IPFS blocks contain only encrypted ciphertext, while authorized owners and on-chain license buyers retrieve decrypted content through authenticated APIs.

---

## 2. Root Cause Analysis

| # | Component | Root Cause | Impact |
|---|---|---|---|
| **1** | URL Sanitization | `clean_cid = clean_cid[7:] if clean_cid.startswith("ipfs://")` only stripped two slashes (`ipfs://`), failing when input had `ipfs:/` or `/ipfs/`. | Gateway URLs formatted as `http://127.0.0.1:8080/ipfs/ipfs:/bafk...`, returning Kubo HTTP 400 Bad Request. |
| **2** | Storage Service Gateway URLs | `f"{storage.gateway_url}/{cid}"` was used in `app/main.py`, omitting the essential `/ipfs/` path segment. | Returned HTTP 404 from the Kubo gateway. |
| **3** | IPFS Desktop Visibility | Uploads used `/api/v0/add` but never called `/api/v0/files/cp` into Kubo MFS. | Files were stored in the blockstore but invisible in the IPFS Desktop "Files" UI. |
| **4** | Integrity Verification | Upload success was declared immediately after receiving an HTTP 200 from `/api/v0/add` without testing retrieval. | Pin failures or network corruption went undetected. |
| **5** | Database Persistence | `MaterialAccessRecord` lacked columns for CID version, storage provider, pin status, verification status, and gateway URL. Public uploads without wallet were skipped. | Frontend had to reconstruct URLs and guess storage status without persistent database provenance. |
| **6** | Frontend Fallback Links | Frontend components used fragile string concatenation and failed to strip scheme prefixes when generating gateway links. | Broken hyperlinks on Discovery, Storage, and Registry pages. |

---

## 3. Code Modifications & Architecture Enhancements

### 3.1 Centralized CID and Gateway URL Utilities (`backend/app/services/ipfs_utils.py`)
Created a standalone, thoroughly tested utility providing:
- `normalize_cid(cid_or_url: str) -> str`: Normalizes any CID string, removing all variations of `ipfs://`, `ipfs:/`, `ipfs:`, `/ipfs/`, `local-sha256:`, and collapsing redundant slashes.
- `build_gateway_url(gateway_url: str, cid_or_url: str) -> str`: Constructs canonical `http://127.0.0.1:8080/ipfs/{clean_cid}` without duplicate `/ipfs` path components.
- `build_ipfs_uri(cid_or_url: str) -> str`: Constructs canonical `ipfs://{clean_cid}`.
- `is_valid_cid(cid: str) -> bool`: Regex-validates standard Base32 CIDv1 (`bafy...`, `bafk...`) and Base58 CIDv0 (`Qm...`).
- `compute_cidv1_raw_sha256(data: bytes) -> str`: Computes canonical CIDv1 using multiformats standard (`0x01` raw codec `0x55` + sha256 multihash `0x12` `0x20`).

### 3.2 Storage Service Hardening (`backend/app/services/storage_service.py`)
- **MFS Synchronization (`_sync_to_mfs`)**: Calls `/api/v0/files/rm` (with force) followed by `/api/v0/files/cp` to copy `/ipfs/{cid}` to `/{filename}` in Kubo MFS.
- **Round-Trip Integrity Verification (`verify_content`)**:
  - Probes `/api/v0/pin/ls` (and falls back to `/api/v0/pin/add` if unpinned).
  - Queries `/api/v0/cat` and tests byte identity against source payload.
  - Queries local gateway HTTP GET `http://127.0.0.1:8080/ipfs/{cid}` and tests byte identity.
- **Explicit Offline Fallback**: Probes Kubo socket only when configured; if offline or unconfigured, falls back to local cache mode (`local-cache (IPFS offline)`) and never fabricates fake CIDs.
- **Global Upload Persistence**: Stores all uploads in `MaterialAccessStore` using a zero-address fallback (`0x0000...`) for public unauthenticated uploads, ensuring complete database tracking.

### 3.3 Database Schema Migration (`backend/app/services/material_access_store.py`)
Upgraded `MaterialAccessRecord` schema and added dynamic non-destructive migration in `_ensure_schema()`:
- `cid_version` (`INTEGER DEFAULT 1`)
- `storage_provider` (`VARCHAR(64) DEFAULT 'kubo'`)
- `is_pinned` (`BOOLEAN DEFAULT 0`)
- `is_verified` (`BOOLEAN DEFAULT 0`)
- `gateway_url` (`VARCHAR(512)`)
Updated `_to_dict()` and search methods to expose these fields across all APIs.

### 3.4 API Route Fixes (`backend/app/main.py`)
- Sanitized `/api/demo/status`, `/api/demo/register`, `/api/storage/share/{cid}`, `/api/storage/content/{cid}`, and `/api/storage/pins`.
- Replaced direct string formatting with `build_gateway_url()` and `normalize_cid()`.

### 3.5 Frontend UI Enhancements
- `frontend/src/pages/StoragePage.tsx`: Added live upload progress steps, clickable local gateway links, native IPFS URIs, copy-to-clipboard buttons, and badges for Pinning (`PINNED`) and Verification (`INTEGRITY VERIFIED`).
- `frontend/src/pages/DiscoveryPage.tsx`: Sanitized demo material IPFS gateway links, using `demoStatus.ipfs_gateway_url` and stripping invalid prefixes.
- `frontend/src/pages/RegistryPage.tsx`: Sanitized gateway links with regex-based prefix stripping.
- Production build verified: `npm run build --prefix frontend` built in 2.13s with **0 errors**.

---

## 4. Host Kubo IPFS Node Configuration

The MatChain backend interacts directly with the local Kubo daemon installed via IPFS Desktop:

| Attribute | Live Host Value |
|---|---|
| **Node Implementation** | Kubo (Go IPFS) |
| **Node Version** | `0.42.0/desktop` |
| **Peer ID** | `12D3KooWD3xVHpZVfU1p5nzziNpPSV5WCuVfzJEBATFZwUX6rdyB` |
| **RPC Endpoint** | `http://127.0.0.1:5001/api/v0` |
| **Gateway Endpoint** | `http://127.0.0.1:8080/ipfs` |
| **Active Swarm Peers** | 12 - 15 connected nodes |
| **MFS Root** | `/` (Accepting `/api/v0/files/cp` operations) |

---

## 5. Live End-to-End Acceptance Verification

The complete pipeline was tested against the live running backend (`http://127.0.0.1:8000`), Ganache RPC (`http://127.0.0.1:8545`), and Kubo daemon (`http://127.0.0.1:5001`).

### Test 1: Node Status Probe
- **Request**: `GET http://127.0.0.1:8000/api/storage/status`
- **Response**: HTTP 200 OK
```json
{
  "online": true,
  "provider": "kubo",
  "api_url": "http://127.0.0.1:5001",
  "gateway_url": "http://127.0.0.1:8080/ipfs",
  "version": "0.42.0",
  "peer_id": "12D3KooWD3xVHpZVfU1p5nzziNpPSV5WCuVfzJEBATFZwUX6rdyB",
  "peers_count": 12,
  "repo_size_bytes": 3878176,
  "stored_items_count": 22,
  "mode": "daemon"
}
```

### Test 2: Public Crystal Structure Upload (`Mg2Si_verification.cif`)
- **Request**: `POST http://127.0.0.1:8000/api/storage/upload-file?is_confidential=false`
- **File**: `Mg2Si_verification.cif` (297 bytes, chemical/x-cif)
- **Response**: HTTP 200 OK
```json
{
  "filename": "Mg2Si_verification.cif",
  "cid": "bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke",
  "material_hash": "0x2c6141badef9c8b81c017b5478acc205e59062a3f76c7ed4da2dc0a3e73e3051",
  "owner_wallet": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
  "storage_backend": "ipfs",
  "is_ipfs": true,
  "is_pinned": true,
  "is_verified": true,
  "verification": {
    "cid": "bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke",
    "verified": true,
    "pin_confirmed": true,
    "cat_matched": true,
    "gateway_matched": true,
    "size_bytes": 297,
    "errors": []
  },
  "is_encrypted": false,
  "size_bytes": 297,
  "content_type": "chemical/x-cif",
  "ipfs_uri": "ipfs://bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke",
  "local_gateway_url": "http://127.0.0.1:8080/ipfs/bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke"
}
```

### Test 3: Local Gateway HTTP Retrieval
- **Request**: `GET http://127.0.0.1:8080/ipfs/bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke`
- **Response**: HTTP 200 OK
- **Integrity**: Exact byte-for-byte match (297 bytes) with uploaded CIF content.

### Test 4: Kubo Recursive Pin Status Confirmation
- **Request**: `POST http://127.0.0.1:5001/api/v0/pin/ls?arg=bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke`
- **Response**: HTTP 200 OK
```json
{"Keys":{"bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke":{"Type":"recursive","Name":""}}}
```

### Test 5: IPFS Desktop MFS Synchronization
- **Request**: `POST http://127.0.0.1:5001/api/v0/files/stat?arg=/Mg2Si_verification.cif`
- **Response**: HTTP 200 OK
```json
{"Hash":"bafkreibmmfa3vxxzzc4byal3kr4kzqqf4wigfi7xnr7njwrnycr6oprqke","Size":297,"CumulativeSize":297,"Blocks":0,"Type":"file"}
```
*Confirmed*: File is visible under the "Files" tab in IPFS Desktop.

### Test 6: Confidential Encrypted Upload & Access Gating
- **Request**: `POST http://127.0.0.1:8000/api/storage/upload-file?is_confidential=true`
- **File**: `secret_recipe.txt` (65 bytes)
- **Response**: HTTP 200 OK (`cid: bafkreihk23hclw4ngglbgyjbdyoraf7fmrbeackbmc4rouuh455dqgssla`, `is_encrypted: true`)
- **Direct Gateway Check (`http://127.0.0.1:8080/ipfs/bafkreih...`)**: Returns AES-256-GCM ciphertext; plaintext recipe is never leaked publicly.
- **Authorized Owner Retrieval**: `GET /api/storage/content/{cid}` with `X-Wallet-Address: 0x90F79bf...` returns HTTP 200 with decrypted plain text.
- **Unauthorized Retrieval**: `GET /api/storage/content/{cid}` with `X-Wallet-Address: 0x1111111...` returns HTTP 403 Forbidden.

---

## 6. Complete Automated Test Results

The backend test suite was run against Python 3.11:

```bash
backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

### Test Breakdown
- `test_access_control.py`: **8 / 8 PASSED** (Confidential gating, download permissions, authorization enforcement)
- `test_blockchain_service.py`: **3 / 3 PASSED** (Ganache transaction mining, registry verification, contract bytecode validation)
- `test_demo_lifecycle.py`: **4 / 4 PASSED** (Mg2Si reference recipe, parameters, discovery state, lifecycle flow)
- `test_ipfs_pipeline.py`: **12 / 12 PASSED** (URL normalization, duplicate segment prevention, CID computation, offline cache fallback, mocked pin detection, real Kubo RPC status, real upload & pin, real gateway roundtrip, real CIF structure & MFS stat, real confidential encryption/decryption, persistence across restart)
- `test_marketplace.py`: **4 / 4 PASSED** (Listings, escrow, purchasing, attestation verification)
- `test_materials_pipeline.py`: **12 / 12 PASSED** (CDVAE interface, structure hashing, geometry validation, elemental reference 0 eV/atom, 3-judge consensus, strict accounting conservation, candidate result schema)
- `test_persistence_and_storage.py`: **6 / 6 PASSED** (Job restart persistence, discovery views, local JSON fallback, configured IPFS API, upload and retrieval, standard CIDv1 format)

**Total Tests:** **49 / 49 PASSED (100%)**  
**Process Exit Code:** `0`

---

## 7. Conclusion

The IPFS integration within MatChain is **fully operational, securely pinned, and technically verified**. Files uploaded through the frontend or backend API are stored in the local Kubo IPFS daemon, pinned recursively, mirrored to MFS for IPFS Desktop visibility, accessible via clean canonical gateway URLs without malformed prefixes, and cryptographically verified before completion.

