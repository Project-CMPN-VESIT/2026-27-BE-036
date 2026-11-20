# IPFS Integration Audit — MatChain

**Date:** 2026-11-21  
**Auditor:** Senior IPFS/Kubo Engineer & Backend Integration Engineer  
**Component:** MatChain Storage, IPFS Node Communication, Pinning, and Retrieval Pipeline  

---

## 1. Executive Summary & Root Cause Analysis

An end-to-end audit of MatChain's IPFS upload, storage, pinning, and retrieval pipeline was conducted across backend services, database records, API endpoints, and frontend components.

### The Observed Problem
When uploading files through the MatChain user interface or API, the application returned a CID (e.g., `bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y`), but:
1. The constructed gateway URL contained an invalid, duplicated path prefix:
   `http://127.0.0.1:8080/ipfs/ipfs:/bafkreigpvpi26oyjbt3tc2sayeuer4m64aa3yisdlhlk3pbyrwuh7vcd3y`
   which the local Kubo IPFS gateway rejected with **HTTP 400: `invalid path ...: invalid cid: selected encoding not supported`**.
2. When the user attempted to search for the CID in IPFS Desktop or query the local gateway directly, the content could either not be found, or files uploaded during daemon offline periods were claimed to be "pinned to IPFS" when in reality they only existed in a local JSON cache file (`matchain_ipfs_store.json`).
3. No post-upload verification step was executed to confirm that the real Kubo node held the file bytes, had pinned the root CID, and could serve the identical byte sequence via the gateway before declaring success.

---

## 2. Root Causes & Exact Files Responsible

| # | Flaw / Root Cause | Impact | Exact Files Responsible |
|---|---|---|---|
| **1** | **Asymmetric Prefix Stripping** (`ipfs://` vs `ipfs:/` vs `ipfs:`) | `clean_cid` sanitization logic only checked `if clean_cid.startswith("ipfs://")` (two slashes). Any input formatted as `ipfs:/` (single slash) or `ipfs:` remained intact. When concatenated with `{gateway}/ipfs/{cid}`, it generated `/ipfs/ipfs:/CID`. | `backend/app/services/storage_service.py` (lines 460-466, 519-525, 702-708)<br>`backend/app/services/material_access_store.py` (lines 126-132) |
| **2** | **Gateway URL Path Omission in API Responses** | In `main.py` lines 884 and 1010, the gateway URL was constructed as `f"{storage.gateway_url}/{access_rec['cid']}"`. Because `storage.gateway_url` is normalized to `http://127.0.0.1:8080`, this generated `http://127.0.0.1:8080/{CID}` (missing the required `/ipfs/` segment), causing HTTP 404 from the gateway. | `backend/app/main.py` (lines 884, 1010) |
| **3** | **Hardcoded and Inconsistent URL Construction in Frontend** | In `DiscoveryPage.tsx` line 915, the gateway URL was hardcoded as `http://127.0.0.1:8080/ipfs/${demoStatus.ipfs_cid}` without checking if `demoStatus.ipfs_cid` was already an IPFS URI or contained `ipfs:/`. In `StoragePage.tsx`, fallback logic chained `uploadedResult.gateways?.local || uploadedResult.local_gateway_url || ...` without central normalization. | `frontend/src/pages/DiscoveryPage.tsx` (line 915)<br>`frontend/src/pages/StoragePage.tsx` (line 489) |
| **4** | **Silent Local Cache Fallback Presented as IPFS** | When the Kubo daemon was not reachable or when `/api/v0/add` threw an exception, `upload_file()` fell back to computing a local CIDv1 raw multihash (`compute_cidv1_raw_sha256`) and writing to `matchain_ipfs_store.json`. However, it still returned `"cid": computed_cid` and `"ipfs_uri": f"ipfs://{computed_cid}"`. The frontend displayed *"Pinned to IPFS with CID: ..."*, creating the false illusion that the file existed on the IPFS network when it only lived on local disk. | `backend/app/services/storage_service.py` (lines 370-456)<br>`frontend/src/pages/StoragePage.tsx` (lines 104-114) |
| **5** | **Lack of Post-Upload Verification** | After uploading via `/api/v0/add`, the backend did not perform a round-trip retrieval verification (via `/api/v0/cat` or gateway HTTP GET) to guarantee byte-for-byte integrity and resolvability before persisting records to the database. | `backend/app/services/storage_service.py` (lines 380-405) |
| **6** | **Pinning vs. MFS Conflation** | While `/api/v0/add?pin=true` pins the block recursively in Kubo, `_sync_to_mfs` was treated as an unmonitored side-effect that silently caught all exceptions. As a result, files would not show up in IPFS Desktop's "Files" tab if MFS copy failed, and pin state was not explicitly checked with `/api/v0/pin/ls`. | `backend/app/services/storage_service.py` (lines 192-216, 403) |
| **7** | **Incomplete Database Metadata Schema** | `MaterialAccessRecord` in SQLite tracked basic keys and hashes, but lacked explicit fields for CID version, storage provider (`kubo` vs `local-fallback`), pin confirmation status, and gateway verification status. | `backend/app/services/material_access_store.py` (lines 19-35) |

---

## 3. Real Node Status & Infrastructure Discovery

During Phase 1 audit probing:
1. **IPFS Desktop & Kubo Version:**  
   Kubo **v0.42.0** is installed and actively running under the host user session via IPFS Desktop (`C:\Users\rushi\AppData\Local\Programs\IPFS Desktop`).
2. **Kubo RPC Endpoint:**  
   `http://127.0.0.1:5001/api/v0` is **ONLINE** and responds with peer ID `12D3KooWD3xVHpZVfU1p5nzziNpPSV5WCuVfzJEBATFZwUX6rdyB`.
3. **Local Gateway Endpoint:**  
   `http://127.0.0.1:8080/ipfs` is **ONLINE** and returns HTTP 200 with `Access-Control-Allow-Origin: *` for pinned CIDs.
4. **MFS Synchronization:**  
   The Mutable File System is active at `/` and accessible via `/api/v0/files/ls`.

---

## 4. Remediation Plan

1. **Centralized CID & Gateway URL Utility (`backend/app/services/ipfs_utils.py`)**:
   - Create a single, strictly tested module for normalizing CIDs, stripping all permutations of `ipfs://`, `ipfs:/`, `ipfs:`, and `/ipfs/`.
   - Build canonical gateway URLs (`http://127.0.0.1:8080/ipfs/{cid}`) and protocol URIs (`ipfs://{cid}`).
2. **Real Kubo Pinning & Verification**:
   - In `StorageService.upload_file()` and `upload_json()`, call `/api/v0/add?pin=true&cid-version=1`.
   - Immediately verify pinning via `/api/v0/pin/ls?arg={cid}`.
   - Immediately verify byte-for-byte retrieval integrity via `/api/v0/cat` and the local HTTP gateway.
   - Sync cleanly to MFS (`/api/v0/files/cp`) so files appear in IPFS Desktop's "Files" tab.
3. **Strict Separation of IPFS vs Local Fallback**:
   - Never present a local fallback identifier as an IPFS CID.
   - If the user requests an IPFS upload and the node is disconnected, return a clear, actionable error instead of silently faking success.
4. **Database Schema Update**:
   - Expand `MaterialAccessRecord` with `cid_version`, `storage_provider`, `is_pinned`, and `is_verified`.
5. **Frontend URL & Status Synchronization**:
   - Use the normalized gateway URL in `DiscoveryPage.tsx`, `RegistryPage.tsx`, `StoragePage.tsx`, and `IpfsShareModal.tsx`.
   - Add copy-CID and direct-download buttons.

