# MatChain — Comprehensive Testing Guide & Live Demo Script

**Version:** 2.0  
**Scope:** Automated Test Execution, System Verification Commands & Step-by-Step Live Demonstration Script

---

## Part 1: Automated Testing Suite

The MatChain automated test suite covers access control, blockchain service integration, marketplace licensing, materials science ML pipelines, and IPFS persistent storage.

### 1.1 Running the Full Backend Test Suite
Open PowerShell in the project root:

```powershell
# Activate backend virtual environment
.\backend\.venv\Scripts\Activate.ps1

# Run complete pytest suite with verbose output
python -m pytest backend/tests -v
```

### 1.2 Test Breakdown & Expected Results

| Test File | Number of Tests | Focus Area | Expected Result |
|---|:---:|---|:---:|
| `backend/tests/test_access_control.py` | 8 | Seller ownership, buyer permission checks, AES-256 decryption, role enforcement | **8/8 PASSED** |
| `backend/tests/test_materials_pipeline.py` | 12 | CDVAE interface contract, PBC wrapping, collision screening, reference potentials, 3-judge jury, consensus spread | **12/12 PASSED** |
| `backend/tests/test_blockchain_service.py` | 3 | Web3 transaction mining receipts, contract loaders, chain reset detection | **3/3 PASSED** |
| `backend/tests/test_marketplace.py` | 4 | Marketplace statistics, attestation verification, enriched listing metadata | **4/4 PASSED** |
| `backend/tests/test_persistence_and_storage.py` | 6 | Job survival on reboot, CIDv1 standard computation, Kubo fallback, AES encryption | **6/6 PASSED** |
| **Total** | **33** | **End-to-End System Integration** | **33/33 PASSED (100%)** |

### 1.3 Verifying Frontend Production Build
To ensure TypeScript types, imports, and bundling are completely error-free:

```powershell
cd frontend
npm run build
```
- **Expected Outcome:** `tsc -b && vite build` succeeds with `0 errors` and generates production bundles in `frontend/dist/`.

---

## Part 2: Step-by-Step Live Demonstration Script

Follow this scripted workflow to deliver a comprehensive, bulletproof live presentation of MatChain.

### Step 1: Pre-Demo Startup Sequence
Launch the required services in separate terminal windows:

#### Terminal 1: IPFS Kubo Daemon / IPFS Desktop
Ensure IPFS Desktop is running or launch the Kubo daemon:
```powershell
ipfs daemon
```
*Verify API & Gateway:*
```powershell
curl.exe -X POST "http://127.0.0.1:5001/api/v0/version"
curl.exe "http://127.0.0.1:8080/ipfs/bafkqaaa"
```

#### Terminal 2: Local Blockchain (Ganache)
Launch Ganache GUI or CLI on port 7545 (or 8545):
- Network ID / Chain ID: `1337` (or `5777`)
- Port: `7545`

#### Terminal 3: MatChain Backend (FastAPI)
```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend
```
*Verify Health:*
- Docs: `http://127.0.0.1:8000/docs`
- Storage Status: `http://127.0.0.1:8000/api/storage/status` (reports `"online": true`)

#### Terminal 4: MatChain Frontend (React + Vite)
```powershell
cd frontend
npm run dev
```
- Open browser: `http://localhost:5173`

---

### Step 2: Live AI Materials Discovery Demo
1. Navigate to **Discovery** (`http://localhost:5173/discovery`).
2. Point out the **Generative Model Selector**:
   - `CrystalVAE`: Marked active with prototype grounding.
   - `CDVAE`: Honestly displays `weights_not_found` (standby mode, explaining that pre-trained weights are required for diffusion sampling).
3. Set Generation Parameters:
   - Target Formation Energy: `-1.20 eV/atom`
   - Target Band Gap: `1.50 eV`
   - Target Density: `4.50 g/cm³`
   - Consensus Spread Threshold ($\tau$): `0.15 eV/atom`
   - Number of Candidates: `15`
4. Click **Run Generation & Validation**.
5. Observe the Real-Time Funnel:
   - Explain the live step indicator: `Initializing → Generating → Screening Hull → Jury Evaluation → Finalizing`.
6. Inspect the Detailed Evaluation Diagnostics:
   - Show the breakdown: `Geometry Passed vs Collisions Rejected`, `Thermodynamic Hull Screened`, and `Jury Consensus Agreement`.
   - Explain that unstable candidates are honestly rejected rather than lowering scientific thresholds.
7. Inspect Validated Candidates:
   - Click a candidate card to view its chemical formula, space group, and unit cell lattice parameters.
   - Interact with the **3D Crystal Structure Viewer**.
   - Show the 3-judge surrogate energy table: `CHGNet`, `M3GNet`, and `XGBoost` along with the consensus spread ($\tau$).

---

### Step 3: IPFS Storage & Desktop MFS Synchronization Demo
1. Navigate to **Storage** (`http://localhost:5173/storage`).
2. Show the **IPFS Daemon Status Card**:
   - Status: `Online (Kubo v0.42.0)`
   - Gateway: `http://127.0.0.1:8080/ipfs/`
3. Upload a crystal structure file (e.g., `sample_crystal.cif` or CSV):
   - Leave the **Confidential (AES-256-GCM)** checkbox unchecked for public content.
   - Click **Upload to IPFS**.
4. Observe the Generated CID:
   - Show the returned CID (e.g., `bafkreif...`).
   - Click the local gateway link: `http://127.0.0.1:8080/ipfs/YOUR_CID`.
   - Show that the browser loads the plain file immediately.
5. Demonstrate **IPFS Desktop "Files" (MFS) Mirroring**:
   - Open the **IPFS Desktop application**.
   - Click the **Files** tab on the left sidebar.
   - Show that the uploaded file appears directly in the Files directory with its actual filename and size.
   - Explain the technical innovation: MatChain automatically mirrors pins into MFS (`/files/cp`), bridging programmatic API uploads with user-friendly desktop file navigation.

---

### Step 4: Confidential Access Control & AES-256-GCM Demo
1. On the **Storage** page, upload a confidential file:
   - Check the **Confidential (AES-256-GCM)** toggle.
   - Click **Upload to IPFS**.
2. Explain the Security Model:
   - The file payload is encrypted in memory using AES-256-GCM with a unique 256-bit key and 96-bit nonce.
   - The ciphertext is pinned to IPFS. Opening the raw IPFS gateway link displays unreadable encrypted bytes.
3. Access Control Verification:
   - As the **Seller/Owner**: Clicking View/Download retrieves the decrypted file seamlessly.
   - As an **Unauthorized User**: Demonstrates that attempts to query `/api/storage/content/{cid}` return `403 Forbidden: Access denied`.

---

### Step 5: Marketplace & IP Licensing Escrow Demo
1. Navigate to **Marketplace** (`http://localhost:5173/marketplace`).
2. View existing material intellectual property listings.
3. Create a New Listing:
   - Select an accepted candidate material.
   - Set an IP license price (e.g., `0.5 MAT` or `0.05 ETH`).
   - Submit the listing to publish it to the marketplace catalog.
4. Demonstrate Buyer Purchase Flow:
   - Connect a secondary buyer wallet.
   - Execute the licensing purchase transaction.
   - Show on-chain attestation and verified purchaser status.
   - Demonstrate that the buyer is now authorized to decrypt and download the proprietary material CIF.

---

### Step 6: Summary & Scientific Defensibility Q&A
Conclude the demonstration by summarizing:
- **Real ML Potentials**: CHGNet and M3GNet are fully operational neural network potentials running locally.
- **Scientific Integrity**: Zero accepted candidates on unstable target conditions is mathematically honest; thresholds are never relaxed to fake results.
- **Production Storage**: IPFS Kubo integration provides genuine content-addressing and MFS Desktop file synchronization.

