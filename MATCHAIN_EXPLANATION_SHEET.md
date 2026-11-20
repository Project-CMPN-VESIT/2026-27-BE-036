# MatChain — Project Architecture & Complete Context Reference Sheet
> **Document Purpose:** This document serves as the single source of truth and complete technical context for **MatChain**. You can copy and paste this entire sheet directly into ChatGPT, Claude, or any LLM to give it full architectural, scientific, and implementation context of the project.

---

## 1. Project Overview & Mission Statement

**MatChain** is an end-to-end decentralized materials discovery and intellectual property (IP) platform. It bridges generative artificial intelligence (crystal inverse design) with Web3 provenance, cryptographic confidentiality, and escrow-based licensing.

### The Problem It Solves:
1. **Materials Discovery Bottleneck:** Traditional laboratory materials synthesis is slow and capital-intensive. AI generative models can propose novel crystal structures, but screening them for thermodynamic stability and physical feasibility requires specialized multi-model pipelines.
2. **Provenance & Attribution Void:** Academic and industrial researchers currently publish candidate structures on preprint servers or patent offices without immutable, timestamped proof of prior discovery.
3. **Decentralized Storage Vulnerability:** Standard IPFS storage is globally public; pinning proprietary crystal structure files (`.cif`, `POSCAR`) to IPFS exposes intellectual property to scraping and unauthorized distribution.
4. **Lack of Trust in Online AI Marketplaces:** Buyers cannot trust unvalidated AI "hallucinations", while sellers risk having their atomic coordinates stolen before purchase.

### The MatChain Solution:
- **Generative AI Inverse Design:** Generates candidate crystal lattices targeting user-specified physical properties (density, band gap, formation energy) using a property-conditioned **CrystalVAE** grounded in Materials Project prototypes.
- **Physics & ML Jury Screening:** Screens generated candidates via convex hull thermodynamic stability ($E_{\text{hull}} \le 0.05 \text{ eV/atom}$) and a multi-model consensus jury (XGBoost, MatMiner, PyMatGen, optional CHGNet/M3GNet) requiring inter-model variance $\tau \le 0.15 \text{ eV}$.
- **Confidential IPFS Storage (AES-256-GCM):** Seller crystal files are encrypted server-side with AES-256-GCM before pinning to IPFS. Keys remain strictly isolated on the backend SQLite database.
- **EVM Smart Contract Registry & Escrow Marketplace:** On-chain EVM contracts (`MatChainRegistry.sol` and `MatChainMarketplace.sol`) record immutable SHA-256 crystal fingerprints and manage trustless purchase escrow.
- **Proof-of-Validation Consensus:** Third-party validators stake 0.05 ETH ("skin in the game") to audit candidates and issue on-chain attestations. Only verified materials can be listed and purchased.
- **Zero-Leak Access Control:** Server-side on-chain purchase verification ensures that only verified purchasers receive decrypted structure files; unpurchased listings show obfuscated 3D previews and permanently conceal the underlying IPFS CID.

---

## 2. High-Level Architecture & Component Interaction

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React + Vite Frontend                           │
│        (Dashboard, Discovery, IPFS Hub, Marketplace, Registry)        │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ REST API Calls                  │ MetaMask (Web3 Ethers)
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│         FastAPI Backend              │  │    Local Blockchain (EVM)    │
│  • Discovery Queue & ML Engine       │  │ • MatChainRegistry.sol       │
│  • AES-256-GCM Encryption Layer      │  │ • MatChainMarketplace.sol    │
│  • Server-Side Purchase Verification │  │   (Chain ID: 1337)           │
└─────────┬──────────────────┬─────────┘  └──────────────────────────────┘
          │                  │
          ▼                  ▼
┌───────────────────┐  ┌─────────────────────────────────────────────────┐
│ SQLite Database   │  │ IPFS / Kubo Storage Layer                       │
│ • Jobs & Results  │  │ • Pinned Ciphertext Objects (CIDv1 Raw SHA-256) │
│ • Access Records  │  │ • Local Cache Fallback (matchain_ipfs_store.json)│
│ • Secret Keys     │  │ • Public Gateway Links (ipfs.io, dweb.link)     │
└───────────────────┘  └─────────────────────────────────────────────────┘
```

---

## 3. Technology Stack & Key Dependencies

| Layer | Technologies & Libraries | Version / Details |
| :--- | :--- | :--- |
| **Backend API** | Python, FastAPI, Uvicorn, Pydantic | Python 3.12 (64-bit), FastAPI 0.115 |
| **Scientific & AI ML** | PyTorch, PyMatGen, MatMiner, XGBoost, Scikit-Learn | PyTorch 2.2.1, PyMatGen, MatMiner |
| **Cryptography** | PyCryptodome (AES-256-GCM), hashlib (SHA-256) | Server-side key isolation |
| **Decentralized Storage** | IPFS (Kubo RPC), Base32 CIDv1, Offline JSON fallback | Kubo v0.24+ / `matchain_ipfs_store.json` |
| **Smart Contracts** | Solidity, Hardhat, Ganache | Solidity ^0.8.24, Ganache (Chain ID 1337) |
| **Web3 Client** | ethers.js, Web3.py | Ethers v6 (frontend), Web3.py v6 (backend) |
| **Frontend UI** | React 18, Vite, TypeScript, TailwindCSS / CSS Vars, Lucide | Obsidian & Titanium high-end dark theme |
| **3D Crystal Rendering** | Three.js / WebGL / Canvas | Fractional coordinate masking for unpurchased previews |
| **Authentication** | Firebase Auth (Email/Google) + Built-in Guest Auth + Web3 Signer | Optional Firebase, fallback guest mode |
| **Database** | SQLite3 (`backend/data/matchain.sqlite3`) | Stores jobs, access records, AES keys |

---

## 4. Scientific Discovery Pipeline (Core Machine Learning)

The core scientific pipeline is implemented in `matchain_colab_corrected.py` and orchestrated by `backend/app/services/matchain_service.py`.

```
[Target Conditions]
(Density, Band Gap, Formation Energy)
        │
        ▼
[CrystalVAE Generator] ──► Generates continuous composition & lattice vectors
        │
        ▼
[Structure Grounding]  ──► Matches nearest Materials Project prototype & maps species
        │
        ▼
[Geometric Sanity]     ──► Minimum atomic clearance check (d_ij >= 0.70 Å)
        │
        ▼
[Thermodynamic Hull]   ──► PhaseDiagram convex hull evaluation (E_hull <= 0.05 eV/atom)
        │
        ▼
[Multi-Model Jury]     ──► XGBoost + MatMiner + PyMatGen (+ optional CHGNet/M3GNet)
                           Requires jury consensus variance (tau <= 0.15 eV)
        │
        ▼
[Validated Candidate]  ──► SHA-256 Fingerprint generated, ready for registry & AES-256 IPFS
```

### Key ML Pipeline Stages:
1. **Dataset Ingestion (`fetch_materials_project_data` / `make_synthetic_dataset`):**
   - Live query from Materials Project API (`MPRester`) filtered by $E_{\text{hull}} \in [0, 0.05]$ eV/atom.
   - If no API key is provided, falls back to a 1,500-sample synthetic dataset spanning 40 chemical elements (`Al, B, Ba, Bi, C, Ca, Fe, Li, Ni, O, Ti, V...`).
2. **Property-Conditioned VAE (`CrystalVAE`):**
   - Architecture: Multilayer Perceptron encoder-decoder with latent dimension $z \in \mathbb{R}^{32}$.
   - Condition vector $c \in \mathbb{R}^3$: target density ($\text{g/cm}^3$), target band gap (eV), target formation energy (eV/atom).
   - Loss function: $\mathcal{L} = \text{MSE}(\hat{x}, x) + \beta \cdot D_{\text{KL}}(\mathcal{N}(\mu, \sigma^2) \parallel \mathcal{N}(0, I))$ with $\beta = 0.01$.
3. **Structure Grounding (`vector_to_structure_grounded`):**
   - Decoded vectors represent continuous element fractions and lattice parameters.
   - The grounding algorithm finds the nearest physical prototype from the reference crystal dataset using compositional cosine similarity and lattice matching, then replaces sites with generated species.
4. **Geometric Integrity (`validate_generated_structure`):**
   - Rejects unphysical structures where any inter-atomic distance $d_{ij} < 0.70 \text{ \AA}$ (prevents atom overlap and coordinate collapse).
5. **Thermodynamic Stability ($E_{\text{hull}}$):**
   - PyMatGen `PhaseDiagram` calculates energy above convex hull ($E_{\text{hull}}$).
   - Threshold: $E_{\text{hull}} \le 0.05 \text{ eV/atom}$ (experimentally synthesizable threshold).
6. **Ensemble Jury Consensus (`run_ensemble_jury`):**
   - Multiple surrogate models predict formation energy independently:
     - XGBoost trained on MatMiner compositional & structural featurizations.
     - PyMatGen elemental baseline reference frame.
     - Optional pre-trained universal graph potentials (CHGNet / M3GNet).
   - Candidate is accepted only if the maximum spread across jurors $\le \tau$ (default: $\tau = 0.15 \text{ eV/atom}$).

---

## 5. Confidential IPFS Storage & AES-256-GCM Encryption Layer

### The Vulnerability of Plain IPFS:
IPFS is a public peer-to-peer network. If unencrypted structure files (`.cif`, `POSCAR`) are pinned to IPFS, any node or gateway that receives the Content Identifier (CID) can read the proprietary crystal coordinates. Obfuscating the CID in client JavaScript is security through obscurity and completely ineffective.

### The MatChain Confidential Storage Protocol:
1. **Server-Side Encryption:**
   - When a seller uploads a material file or approves an AI candidate, the backend executes `StorageService.encrypt_content(data)`.
   - Generates a cryptographically secure 256-bit key (`Crypto.Random.get_random_bytes(32)`) and uses **AES-256-GCM** (Galois/Counter Mode).
   - Produces `(ciphertext, key_hex, nonce_hex, tag_hex)`.
2. **Ciphertext Pinned to IPFS:**
   - Only the encrypted ciphertext is pinned to the local Kubo IPFS daemon (or fallback JSON store).
   - Standard CIDv1 multihash is computed: Base32 lowercase prefixed with `b` (`0x01` CIDv1, `0x55` raw codec, `0x12` sha2-256, `0x20` 32-byte digest).
3. **Backend Key Isolation:**
   - The decryption key, nonce, and authentication tag are stored exclusively in SQLite table `material_access_records`.
   - Keys are **never** committed to the blockchain, never exposed in public endpoints, and never sent to unverified clients.
4. **Offline Local Fallback (`matchain_ipfs_store.json`):**
   - If no local Kubo IPFS daemon is running on port 5001, the system automatically falls back to `matchain_ipfs_store.json`, allowing the complete app to run offline without errors.

---

## 6. Smart Contracts Architecture (EVM / Solidity ^0.8.24)

### Contract 1: `MatChainRegistry.sol`
Maintains the immutable record of all discovered materials and handles validator staking.
- **State Data:**
  - `struct Discovery`:
    - `bytes32 fingerprint`: SHA-256 digest of normalized crystal structure.
    - `address creator`: Wallet address that registered the discovery.
    - `uint256 blockNumber`: Block height at registration.
    - `string ipfsCid`: IPFS CID of the encrypted structure file.
    - `string metadata`: Public JSON string (formula, density, $E_{\text{hull}}$, predicted formation energy).
    - `bool verified`: Set to `true` when a validator stakes 0.05 ETH and attests stability.
  - `mapping(bytes32 => Discovery) public discoveries`
  - `mapping(address => uint256) public validatorStake`
- **Key Methods:**
  - `registerDiscovery(bytes32 fingerprint, string ipfsCid, string metadata)`: Stores discovery; enforces unique registration (`creator == address(0)`).
  - `verifyDiscovery(bytes32 fingerprint) external payable`: Requires exact stake `msg.value == 0.05 ether`. Marks `verified = true`, records stake in `validatorStake[msg.sender]`, and emits `DiscoveryAttested` & `DiscoveryVerified`.
  - `withdrawStake() external`: Allows validators to reclaim their stake balance.

### Contract 2: `MatChainMarketplace.sol`
Manages crystal licensing listings and trustless escrow payment.
- **State Data:**
  - `struct Listing`:
    - `bytes32 materialHash`: The crystal fingerprint.
    - `address seller`: The original creator.
    - `address buyer`: The purchasing wallet.
    - `uint256 price`: License price in Wei.
    - `string licenseTerms`: e.g. `"Commercial Research"`, `"Single Lab"`.
    - `bool sold`: Status flag.
  - `mapping(bytes32 => Listing) public listings`
- **Key Methods:**
  - `listMaterial(bytes32 materialHash, uint256 price, string licenseTerms)`: Creator lists material. Verifies `creator == msg.sender` by querying `registry.discoveries(materialHash)`.
  - `purchaseMaterial(bytes32 materialHash) external payable`:
    - Verifies listing exists and is unsold (`!item.sold`).
    - Queries `registry.discoveries(materialHash)` to enforce `verified == true` (unverified materials cannot be sold).
    - Checks exact payment `msg.value == item.price`.
    - Marks `item.sold = true` and `item.buyer = msg.sender`.
    - Direct transfer of ETH to `seller`. Emits `ListingPurchased`.

---

## 7. Security & Access Control Matrix

| Feature / Data | Public / Unauthenticated | Authenticated Buyer (Pre-Purchase) | Authenticated Buyer (Post-Purchase) | Seller (Material Owner) | Staked Validator |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Public Metadata** (Formula, Density, Price, $E_{\text{hull}}$) | Allowed | Allowed | Allowed | Allowed | Allowed |
| **3D Crystal Preview** | Obfuscated | Obfuscated | Obfuscated | Full True Structure | Full for Audit |
| **Encrypted IPFS CID** | Blocked | Blocked | **Permanently Masked** | Visible & Shareable | Blocked |
| **IPFS Share Modal / Gateway URLs** | 401 | 403 Forbidden | 403 Forbidden | Full Access | 403 Forbidden |
| **Storage Pins Listing** (`/api/storage/pins`) | 401 | Shows only own uploads | Shows only own uploads | Shows own CIDs | Shows own uploads |
| **Decrypted Data API** (`/api/storage/content/{cid}`) | 401 | 403 Forbidden | Allowed (CID omitted) | Allowed (+ CID) | Allowed for Audit |
| **Authorized CIF Download** (`/api/storage/download/{hash}`) | 401 | 403 Forbidden | **Allowed (Decrypted File)** | Allowed | 403 Forbidden |

### Server-Side Purchase Verification:
When a user calls `GET /api/storage/download/{material_hash}`, the backend checks:
```python
listing = self.marketplace.functions.listings(digest).call()
if listing[5] and listing[2].lower() == user.wallet_address.lower():
    # Authorized on-chain buyer: fetch encrypted blob, decrypt with backend key, stream CIF
```
No client-side flag or unauthenticated header can bypass this check.

---

## 8. The 3-Role Decentralized Marketplace Engine

### 1. Seller Studio (e.g. Aarav):
- Generates crystals in Discovery Studio or uploads custom `.cif` / `POSCAR` files.
- Sets license price in ETH and selects terms (Research vs. Commercial).
- File is encrypted with AES-256-GCM and ciphertext is pinned to IPFS.
- Submits on-chain listing transaction via MetaMask to `MatChainMarketplace.sol`.
- Real-time revenue analytics track sales volume and earnings.

### 2. Validator Hub — Proof-of-Validation Consensus (e.g. Priya):
- Discovers pending listings in the audit queue.
- Executes automated pre-audit inspection:
  1. Thermodynamic stability: $E_{\text{hull}} \le 0.05 \text{ eV/atom}$.
  2. Physical density & atomic packing clearance: density $\in [1.0, 25.0]\text{ g/cm}^3$.
  3. ML jury consensus spread: spread $\le 0.15 \text{ eV}$.
- Validator stakes 0.05 ETH on-chain (`verifyDiscovery`) as a cryptographic bond.
- Smart contract records the attestation and stamps the listing with the **Verified Material** badge. Dishonest attestations are subject to slashing.

### 3. Buyer Catalog & Vault (e.g. Rohan):
- Filters verified materials by application domain (Battery, Solar/Perovskite, Superconductor).
- Inspects obfuscated 3D previews (fractional coordinates are masked with randomized displacement noise so unpurchased crystal structures cannot be reconstructed).
- Executes 1-click escrow purchase via MetaMask (`purchaseMaterial`).
- Accesses **"My Purchased Vault"**:
  - Views on-chain Provenance and Ownership Certificate.
  - Downloads the decrypted `.cif` structure file directly to disk.

---

## 9. Backend REST API Endpoints Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/health` | No | System health, blockchain status, storage mode, contract addresses |
| `GET` | `/api/dashboard/stats` | Optional | Platform metrics: jobs, registered materials, listings, volume |
| `GET` | `/api/analytics` | Optional | Model evaluations ($R^2$, MAE), VAE training curves, jury metrics |
| `POST` | `/api/discovery/generate` | Optional | Queues async discovery job with target conditions |
| `GET` | `/api/discovery/jobs/{job_id}` | Optional | Polls job status, progress %, diagnostics, and candidate crystals |
| `GET` | `/api/materials` | Optional | Returns approved public materials metadata (CIDs masked) |
| `GET` | `/api/registry` | Optional | Reads on-chain registry records (CIDs masked for non-owners) |
| `POST` | `/api/registry` | Yes | Backend-signed material registration (fallback to MetaMask) |
| `GET` | `/api/storage/status` | No | Kubo node status, peer count, repository size, storage mode |
| `GET` | `/api/storage/pins` | Yes | Lists stored pins owned by the calling wallet |
| `POST` | `/api/storage/upload-file` | Yes | Encrypts (AES-256-GCM) and pins `.cif`/`POSCAR` file to IPFS |
| `GET` | `/api/storage/share/{cid}` | Yes (Owner) | Generates public IPFS gateway links (seller/owner only) |
| `GET` | `/api/storage/content/{cid}` | Yes | Retrieves decrypted material data (CID hidden from buyers) |
| `GET` | `/api/storage/download/{hash}`| Yes | Streams decrypted `.cif` file for verified buyers or owners |
| `POST` | `/api/marketplace/audit` | No | Runs automated physics and jury screening on candidate hash |
| `POST` | `/api/marketplace/validate` | Yes (Validator)| Records validator attestation after verifying on-chain 0.05 ETH stake |
| `GET` | `/api/marketplace/validations` | No | Lists all validator attestations and audit scores |
| `GET` | `/api/marketplace/stats` | No | Live marketplace stats: active listings, volume, staked validators |
| `GET` | `/api/marketplace/listings` | No | Enriched listings with thermodynamic properties and badges |
| `GET` | `/api/users/me/materials` | Yes | Lists materials registered by calling wallet |
| `GET` | `/api/users/me/licenses` | Yes | Lists active licenses purchased by calling wallet |

---

## 10. Frontend Architecture & Routing

Built with **React 18**, **Vite**, **TypeScript**, and styled with an obsidian/titanium dark mode system.

### Page Directory (`frontend/src/pages/`):
- `LandingPage.tsx`: Product introduction, architectural diagram, feature overview.
- `DashboardPage.tsx`: Real-time analytics, active jobs, recent on-chain transactions, system status indicators.
- `DiscoveryPage.tsx`: Inverse materials studio. Input forms for target properties (formation energy, band gap, density, candidate count, $\tau$ threshold), live progress bar, candidate list with $E_{\text{hull}}$ tags, and on-chain registration action.
- `MarketplacePage.tsx`: 3-tab unified marketplace:
  - **Buyer Catalog**: Filter by application, view obfuscated crystal canvas, buy with MetaMask, download licensed CIFs.
  - **Seller Studio**: Create listings, set ETH pricing, track revenue and license counts.
  - **Validator Hub**: Screen audit queue, inspect $E_{\text{hull}}$ and jury spread, stake 0.05 ETH to approve attestation.
- `RegistryPage.tsx`: Explorer for on-chain registry transactions, block numbers, creator addresses, and verification badges.
- `StoragePage.tsx`: Decentralized IPFS hub. Node status, file/JSON upload with AES-256 encryption, pin browser, CID lookup, and share modals.
- `AnalyticsPage.tsx`: Regression metrics ($R^2$, RMSE) for ML surrogate models, VAE loss history, consensus spread charts.
- `AuthPage.tsx` & `SettingsPage.tsx`: Account management, Firebase/Guest authentication, MetaMask wallet linking.

### Reusable Components & Services:
- `CifStructurePreview.tsx`: Dynamic 3D crystal preview with coordinate obfuscation for unpurchased listings.
- `CrystalCanvas.tsx`: Interactive Three.js/WebGL crystal renderer.
- `IpfsShareModal.tsx`: Gateway URLs and embed generator (restricted to seller).
- `services/contractClient.ts`: Ethers.js integration for interacting with `MatChainRegistry` and `MatChainMarketplace`.
- `services/wallet.tsx`: MetaMask connection, network validation (Ganache Chain ID 1337), account switching.

---

## 11. Step-by-Step Local Setup & Execution Guide

### Prerequisites:
- Python 3.12 (64-bit) — *Warning: Python 3.13 is incompatible with pymatgen/torch wheels*.
- Node.js v18 or v20 LTS.
- Ganache (CLI or UI) listening on `http://127.0.0.1:8545` (Chain ID 1337).
- MetaMask browser extension configured with `Ganache Local` (`http://127.0.0.1:8545`, Chain ID 1337).
- *(Optional)* Kubo IPFS daemon on port 5001.

### Multi-Terminal Execution:

#### Terminal 1: Local Blockchain (Ganache)
```powershell
cd Matchain/contracts
npm run node
```
*Listens on `127.0.0.1:8545` and funds 10 test accounts with 10,000 ETH each.*

#### Terminal 2: Smart Contract Deployment
```powershell
cd Matchain/contracts
npm run deploy
```
*Automatically compiles Solidity contracts, deploys them to Ganache, and auto-updates `.env` and `frontend/.env.local` with the new contract addresses.*

#### Terminal 3: FastAPI Backend
```powershell
cd Matchain/backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Swagger docs available at `http://127.0.0.1:8000/docs`.*

#### Terminal 4: React Frontend
```powershell
cd Matchain/frontend
npm run dev
```
*Vite web application opens at `http://localhost:5173`.*

#### Terminal 5: IPFS Daemon (Optional)
```powershell
ipfs daemon
```
*If not running, MatChain seamlessly uses its local JSON store fallback (`matchain_ipfs_store.json`).*

---

## 12. Automated Verification & Testing Suite

MatChain contains **21 automated pytest tests** covering security, cryptography, and contract logic:

```powershell
cd Matchain/backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

### Verified Test Suite Breakdown:
1. `test_access_control.py`:
   - `test_1`: Seller can upload and retrieve own material CID.
   - `test_2`: Another seller cannot retrieve that CID (403 Forbidden).
   - `test_3`: Authenticated buyer cannot retrieve CID before purchasing.
   - `test_4`: Buyer cannot access restricted file contents using known CID directly.
   - `test_5`: Buyer with verified on-chain purchase receives decrypted file, but CID remains shielded.
   - `test_6`: Unauthenticated user cannot access private material.
   - `test_7`: Pins, raw, and share endpoints enforce authorization.
   - `test_8`: Public metadata remains accessible.
2. `test_blockchain_service.py`:
   - Validates backend transactions, contract code verification, and deployment manifest checking.
3. `test_marketplace.py`:
   - Validates marketplace stats, stability audit screening, validator attestation receipts, and enriched listings.
4. `test_persistence_and_storage.py`:
   - Tests job survival across restarts, SQLite persistence, IPFS client, local JSON fallback, and RFC 4648 Base32 CIDv1 computation.

---

## 13. Ready-to-Use ChatGPT Context Prompt

> Copy and paste the block below into ChatGPT to start working on the project:

```text
I am working on MatChain, an end-to-end AI-assisted materials discovery and decentralized IP licensing platform.

Here is the complete architectural context of the project:
1. Generative AI Engine: Property-conditioned PyTorch CrystalVAE (targeting density, band gap, formation energy) + structural grounding on Materials Project prototypes + geometric clearance filtering (d_ij >= 0.70 Å) + thermodynamic convex hull screening (E_hull <= 0.05 eV/atom) + multi-model ML jury consensus (XGBoost, MatMiner, PyMatGen, CHGNet/M3GNet with tau <= 0.15 eV spread).
2. Confidential Storage Layer: AES-256-GCM encryption on crystal structure files (.cif, POSCAR) before pinning to IPFS (Kubo) with Base32 CIDv1 raw multihashes. AES keys, nonces, and authentication tags are isolated on the backend SQLite database (material_access_records) and NEVER exposed on-chain. Offline local JSON fallback (matchain_ipfs_store.json).
3. EVM Smart Contracts (Ganache Chain ID 1337, Solidity ^0.8.24):
   - MatChainRegistry.sol: Records SHA-256 fingerprints, creator, IPFS CID, public metadata, and handles 0.05 ETH validator staking.
   - MatChainMarketplace.sol: Escrow licensing marketplace. Enforces that materials must be verified on-chain before purchase, transfers ETH directly to sellers, and records buyers.
4. Access Control & Security: Unpurchased materials have obfuscated 3D previews and permanently conceal IPFS CIDs. Purchases are verified server-side on-chain before streaming decrypted CIF downloads.
5. Tech Stack: FastAPI (Python 3.12), React 18 + Vite (TypeScript, TailwindCSS/Obsidian dark theme), Ethers.js, Hardhat, Ganache.

Please act as a senior full-stack AI and Web3 engineer collaborating with me on this codebase.
```
