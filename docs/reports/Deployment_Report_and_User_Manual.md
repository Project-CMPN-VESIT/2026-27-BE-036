# MatChain: Deployment Report and User Manual
**AI-Assisted Materials Discovery and Decentralized IP Licensing Platform**

*Final Year Computer Engineering Capstone Project*  
*Document Reference: MAT-REP-DEP-003*  
*Version: 1.0.0*  
*Date: November 2026*  
*Status: Verified Operational Manual*

---

## 1. Introduction

### 1.1 Purpose and Intended Audience
This document serves as the comprehensive **Deployment Guide and User Operating Manual** for **MatChain**—an end-to-end platform bridging generative artificial intelligence, computational materials science, content-addressed storage (IPFS), and Ethereum-compatible smart contracts. 

This document is intended for:
- **Academic Evaluators and Examiners:** To independently review, verify, install, and execute the complete platform.
- **System Administrators and DevOps Engineers:** To deploy, configure, and maintain the backend API, AI inference engine, IPFS node, and local blockchain.
- **Computational Materials Researchers:** To execute crystal discovery workflows, inspect thermodynamic hull stability, and review 3-judge model consensus.
- **IP Licensors, Material Buyers, and Patent Attorneys:** To navigate decentralized IP registration, cryptographic file verification, and on-chain escrow licensing.

### 1.2 System Architecture Overview
MatChain operates as a distributed multi-tier system:
1. **Presentation Layer:** A responsive React 18 / TypeScript single-page application built on Vite and styled with Tailwind CSS, featuring an interactive WebGL Three.js crystal structure visualizer and Web3 browser wallet connectivity.
2. **Application & Inference Layer:** A high-throughput FastAPI (Python 3.11) application orchestrating generative crystal sampling (CrystalVAE), thermodynamic convex hull screening (PyMatGen), surrogate potential jury consensus (CHGNet, M3GNet, XGBoost), and AES-256-GCM cryptographic encryption.
3. **Decentralized Storage Layer:** A local Kubo IPFS daemon providing UnixFS content-addressed storage, CIDv1 SHA-256 generation, local MFS indexing, and gateway retrieval.
4. **Decentralized Execution Layer:** EVM smart contracts deployed via Hardhat/Ganache (`MaterialRegistry.sol` and `MaterialMarketplace.sol`) managing immutable provenance and trustless license purchases.

---

## 2. Technology Stack and Dependency Manifest

The platform is constructed using modern, verified production frameworks:

| Component | Framework / Tool | Exact Version | Purpose / Scope |
|---|---|---|---|
| **Frontend Runtime** | Node.js | `v25.5.0` | JavaScript runtime environment |
| **Package Manager** | NPM | `11.1.0` | Frontend package and dependency manager |
| **Frontend Framework**| React | `18.3.1` | User interface component library |
| **Build Tool** | Vite | `8.3.4` | Fast development server and production bundler |
| **Styling** | Tailwind CSS | `3.4.1` | Utility-first responsive CSS styling |
| **Lattice Viewer** | Three.js | `0.160.0` | WebGL 3D atomic unit cell visualization |
| **Web3 Client** | Ethers.js | `6.13.0` | Ethereum wallet and RPC provider interface |
| **Backend Runtime** | Python (CPython) | `3.11.9` (64-bit) | Backend application and ML execution |
| **API Framework** | FastAPI | `0.115.8` | High-performance asynchronous REST API |
| **ASGI Server** | Uvicorn | `0.34.0` | Production ASGI web server with hot-reload |
| **Database ORM** | SQLAlchemy | `2.0.38` | Object-relational mapping and database engine |
| **Database Engine** | SQLite | `3.45.1` | ACID-compliant relational persistence |
| **ML Framework** | PyTorch | `2.14.0+cpu` | Tensor computation and neural network runtime |
| **Surrogate GNN 1** | CHGNet | `0.4.2` | Crystal Hamiltonian GNN (weights v0.3.0) |
| **Surrogate GNN 2** | MatGL / M3GNet | `4.0.3` | Materials 3-body graph potential (MatPES) |
| **Surrogate Model 3**| XGBoost | `3.2.0` | Gradient-boosted decision trees on Magpie features |
| **Crystallography** | PyMatGen | `2026.5.4` | Structure analysis, symmetry, and phase diagrams |
| **Atomic Simulation** | ASE | `3.23.0` | Atomic Simulation Environment optimizer |
| **Featurization** | MatMiner | `0.10.1` | 132-dimensional Magpie elemental featurizer |
| **IPFS Node** | Kubo IPFS | `v0.33.0` | Peer-to-peer content storage daemon |
| **Blockchain RPC** | Ganache | `v7.9.2` | Local Ethereum blockchain emulator |
| **Smart Contracts** | Solidity | `^0.8.20` | `MaterialRegistry.sol` & `MaterialMarketplace.sol` |
| **Web3 Backend** | Web3.py | `8.0.0` | Python Ethereum interaction library |
| **Testing Engine** | PyTest | `8.3.4` | Automated backend testing framework |

---

## 3. System Requirements and Port Allocation

### 3.1 Hardware Requirements
- **Minimum Requirements (Functional Evaluation):**
  - Processor: 64-bit x86_64 Dual-Core CPU (2.0 GHz or higher).
  - RAM: 8.0 GB DDR3/DDR4.
  - Storage: 10 GB available solid-state storage.
  - GPU: Not required (Full CPU inference supported).
- **Recommended Requirements (Full Benchmark Execution):**
  - Processor: Quad-Core or Octa-Core x86_64 CPU (3.0 GHz+).
  - RAM: 16.0 GB DDR4/DDR5.
  - Storage: 20 GB NVMe M.2 SSD storage.
  - GPU: Optional (NVIDIA RTX 3060+ with CUDA 12.x for 15x faster relaxation).

### 3.2 Network Port Allocation
The host system must reserve the following TCP ports on `127.0.0.1` (localhost):

| Port Number | Protocol | Bound Service | Purpose |
|---|---|---|---|
| **5173** | HTTP | Vite Development Server | Frontend UI web application |
| **8000** | HTTP | FastAPI Backend / Uvicorn | Core REST API, Swagger docs (`/docs`) |
| **8545** | HTTP / JSON-RPC | Ganache EVM Node | Local Ethereum blockchain node |
| **5001** | HTTP / RPC | Kubo IPFS API | IPFS administrative and upload endpoint |
| **8080** | HTTP | Kubo IPFS Gateway | Content-addressed file retrieval |

---

## 4. Repository Structure

```
d:\Matchain\
├── backend/                        # FastAPI Python Backend
│   ├── app/
│   │   ├── api/                    # Endpoint routers (materials, ipfs, blockchain)
│   │   ├── core/                   # Security, settings, and JWT configuration
│   │   ├── db/                     # SQLAlchemy models and SQLite session engine
│   │   ├── ml/                     # AI discovery pipeline, models, and featurizers
│   │   │   ├── crystal_vae.py      # Generative crystal coordinate sampling
│   │   │   ├── models.py           # CHGNet, M3GNet, and XGBoost wrappers
│   │   │   └── pipeline.py         # Multi-stage screening and jury consensus
│   │   ├── services/               # Storage, IPFS, Web3, and demo asset services
│   │   └── main.py                 # FastAPI application factory and route registration
│   ├── tests/                      # Automated test suite (49 pytest test cases)
│   ├── requirements.txt            # Python pip dependencies
│   └── .venv/                      # Python 3.11 virtual environment
├── frontend/                       # React 18 + TypeScript + Vite Frontend
│   ├── src/
│   │   ├── components/             # Reusable UI components (Navbar, 3D Lattice Viewer)
│   │   ├── pages/                  # Top-level views (Discovery, Marketplace, Storage, IPFS Hub)
│   │   ├── services/               # Axios API clients and Ethers.js wallet providers
│   │   ├── App.tsx                 # Main application component and routing table
│   │   └── main.tsx                # Client DOM entry point
│   ├── package.json                # Node.js dependencies and scripts
│   └── vite.config.ts              # Vite configuration and proxy rules
├── contracts/                      # EVM Smart Contracts (Hardhat / Solidity)
│   ├── contracts/
│   │   ├── MaterialRegistry.sol    # Material IP registration and SHA-256 provenance
│   │   └── MaterialMarketplace.sol # Escrow licensing, revenue distribution, disputes
│   ├── scripts/
│   │   └── deploy.js               # Deployment script targeting Ganache
│   └── package.json                # Hardhat and Web3 deployment dependencies
├── docs/                           # Architecture, audit, and benchmark documentation
│   └── reports/                    # Formal academic reports (.md and .docx)
└── README.md                       # High-level project summary
```

---

## 5. Step-by-Step Installation Guide

Follow these steps sequentially to configure the complete MatChain environment from a clean machine.

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-org/matchain.git
cd matchain
```

### Step 2: Configure Python Virtual Environment and Backend Dependencies
Ensure Python 3.11 (64-bit) is installed and available in your system path:
```bash
# Navigate to backend directory
cd backend

# Create isolated virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Upgrade pip and wheel
python -m pip install --upgrade pip setuptools wheel

# Install core dependencies
pip install -r requirements.txt

# Verify deep learning and crystallographic dependencies
python -c "import torch, pymatgen, chgnet, matgl, xgboost; print('AI Toolchain Verified Successfully')"
cd ..
```

### Step 3: Install and Configure Kubo IPFS Node
1. Download **Kubo IPFS v0.33.0** (or higher) from [ipfs.tech](https://docs.ipfs.tech/install/command-line/) or via Chocolatey/Scoop:
   ```powershell
   choco install ipfs
   ```
2. Initialize the IPFS repository:
   ```bash
   ipfs init
   ```
3. Configure Cross-Origin Resource Sharing (CORS) headers to allow the MatChain frontend and backend to communicate with the local RPC:
   ```bash
   ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["http://localhost:5173", "http://127.0.0.1:8000", "http://127.0.0.1:5001"]'
   ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["PUT", "POST", "GET"]'
   ```
4. Start the IPFS daemon:
   ```bash
   ipfs daemon
   ```
   *Verification:* Ensure output displays `API server listening on /ip4/127.0.0.1/tcp/5001` and `Gateway server listening on /ip4/127.0.0.1/tcp/8080`.

### Step 4: Configure Local Ethereum Blockchain (Ganache)
1. Install and launch Ganache via npm in the `contracts` directory:
   ```bash
   cd contracts
   npm install
   npm run node
   ```
   *Verification:* Ensure Ganache is listening on `http://127.0.0.1:8545` with Network ID `1337`.

### Step 5: Compile and Deploy Smart Contracts
In a new terminal window within the `contracts` directory:
```bash
cd contracts
npx hardhat run scripts/deploy.js --network localhost
```
Expected output:
```
Deploying contracts with the account: 0x90F79bf6EB2c4f870365E785982E1f101E93b906
MaterialRegistry deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3
MaterialMarketplace deployed to: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
Contract addresses exported to backend and frontend configurations.
```

### Step 6: Configure Frontend Dependencies
```bash
cd frontend
npm install
npm run build
cd ..
```
*Verification:* The production build should complete in ~1.0 second with zero TypeScript compilation errors.

---

## 6. Environment Variables and Configuration Reference

Create a `.env` file in the `backend/` directory based on the following reference:

```ini
# ==============================================================================
# MatChain Backend Configuration (.env)
# ==============================================================================

# Application Settings
PROJECT_NAME="MatChain AI & IPFS Platform"
DEBUG=True
API_V1_STR="/api/v1"

# Database Configuration
DATABASE_URL="sqlite:///./mat_chain.db"

# Security & Cryptography
SECRET_KEY="mat-chain-production-cryptographic-secret-key-change-in-prod"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CONFIDENTIAL_ENCRYPTION_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# IPFS Kubo Configuration
IPFS_RPC_URL="http://127.0.0.1:5001"
IPFS_GATEWAY_URL="http://127.0.0.1:8080"
IPFS_TIMEOUT_SECONDS=30

# Ethereum / Ganache Web3 Configuration
WEB3_PROVIDER_URI="http://127.0.0.1:8545"
CHAIN_ID=1337
REGISTRY_CONTRACT_ADDRESS="0x5FbDB2315678afecb367f032d93F642f64180aa3"
MARKETPLACE_CONTRACT_ADDRESS="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"

# AI Discovery & Consensus Thresholds
CONSENSUS_TOLERANCE_EV_PER_ATOM=0.15
MAX_FORMATION_ENERGY_E_HULL=0.05
MIN_INTERATOMIC_DISTANCE_ANGSTROM=1.00
```

---

## 7. Ordered Application Startup Instructions

For seamless operation, launch the platform processes in the following strict order:

```mermaid
flowchart LR
    P1["1. Kubo IPFS Daemon\n(:5001, :8080)"] --> P2["2. Ganache EVM Node\n(:8545)"]
    P2 --> P3["3. Contract Deployment\n(Hardhat deploy)"]
    P3 --> P4["4. FastAPI Backend\n(:8000)"]
    P4 --> P5["5. React Vite Frontend\n(:5173)"]
```

### Process 1: IPFS Node (Terminal 1)
```powershell
ipfs daemon
```

### Process 2: Ganache Blockchain (Terminal 2)
```powershell
cd d:\Matchain\contracts
npm run node
```

### Process 3: FastAPI Backend (Terminal 3)
```powershell
cd d:\Matchain\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Health Check:* Open `http://127.0.0.1:8000/docs` in your browser. You should see interactive Swagger UI documentation.

### Process 4: Frontend Development Server (Terminal 4)
```powershell
cd d:\Matchain\frontend
npm run dev
```
*Access Application:* Open `http://localhost:5173` in Google Chrome or Brave.

---

## 8. Complete User Manual and Walkthrough

### 8.1 Connecting Web3 Wallet and User Profiles
1. Navigate to `http://localhost:5173`.
2. Click the **Connect Wallet** button in the top-right navigation bar.
3. Select MetaMask or connect using the built-in Ganache test account:
   - Test Account Address: `0x90F79bf6EB2c4f870365E785982E1f101E93b906`.
4. Switch network to **Ganache Localhost** (RPC URL: `http://127.0.0.1:8545`, Chain ID: `1337`).
5. Use the user role selector in the navbar to toggle between **Materials Scientist (Seller/Creator)** and **Industrial Buyer (Licensee)**.

---

### 8.2 AI Materials Discovery Interface
1. Click on the **Discovery** tab in the main navigation.
2. Enter the target material parameters:
   - **Target Reduced Formula:** e.g., `Mg2Si`, `Ba3Zn2S3`, or `LiFePO4`.
   - **Candidate Sample Count:** Set between `10` and `200` using the slider.
   - **Convex Hull Stability Threshold:** Default `0.05 eV/atom`.
   - **Jury Consensus Tolerance ($\tau$):** Default `0.15 eV/atom`.
3. Click **Run AI Discovery**.
4. The system will asynchronously execute the pipeline, displaying live progress across the 5 diagnostic stages.

---

### 8.3 Diagnostic Accounting and Candidate Screening
Inspect the **Diagnostic Accounting** banner:
- **1. Sampled:** Displays total raw generative candidates sampled from the CrystalVAE latent distribution.
- **2. Geometry Valid:** Shows candidates meeting the interatomic distance constraint ($d \ge 1.0\text{ \AA}$) with non-overlapping Wyckoff positions.
- **3. Convex Hull Pass:** Indicates candidates lying on or within $0.05\text{ eV/atom}$ of the PyMatGen phase stability boundary.
- **4. Jury Consensus:** Shows candidates evaluated by the three independent surrogate models (CHGNet, M3GNet, XGBoost).
- **5. Final Validated:** Candidates whose inter-model standard deviation/spread $\tau \le 0.15\text{ eV/atom}$.

If zero candidates pass consensus (as observed in unconstrained quaternary exploration), the system clearly explains that candidates were rejected to maintain scientific integrity.

---

### 8.4 One-Click End-to-End Demonstration Lifecycle ($\text{Mg}_2\text{Si}$)
To test the entire discovery, storage, registration, and licensing flow in under 3 seconds:
1. On the Discovery page, locate the **Demonstration Recipe** card for $\text{Mg}_2\text{Si}$ (Materials Project `mp-1367`).
2. Click **Run Demo Recipe**.
3. In **2.24 seconds**, the system will:
   - Sample 200 candidates $\to$ filter to 75 geometry valid $\to$ 9 hull pass $\to$ 1 consensus validated ($\text{Mg}_2\text{Si}$ with spread $0.005\text{ eV/atom}$).
   - Package structure `.cif`, calculate SHA-256 hash (`0xb6cdc24f...`).
   - Ingest into IPFS, generate genuine CID `bafkreidecv6j4xkxkwba25kzhmvyv2ur6yp6wb4tsurt2mj546fcpq3eqq`, and pin locally.
   - Execute an on-chain transaction registering the material in `MaterialRegistry.sol`.
   - Automatically list a commercial IP license in `MaterialMarketplace.sol` for `0.05 ETH`.
4. To rerun the demo from scratch, click the **Reset Pipeline Demo** button.

---

### 8.5 Interactive 3D Crystal Lattice Viewer
1. Click **View Crystal Structure** on any validated material.
2. The interactive Three.js WebGL viewer loads:
   - **Atoms:** Rendered as color-coded CPK spheres scaled by covalent radii (e.g., Green = Magnesium, Grey = Silicon).
   - **Unit Cell Bounding Box:** Dashed lattice vectors indicating dimensions $a, b, c$ and angles $\alpha, \beta, \gamma$.
   - **Interactions:**
     - Left-Click + Drag: Rotate unit cell in 3D space.
     - Scroll Wheel: Zoom in and out.
     - Right-Click + Drag: Pan viewport.
     - Toggle Axes: Show/hide Cartesian $X, Y, Z$ coordinates.

---

### 8.6 IPFS Storage Hub and Content Retrieval
1. Navigate to the **IPFS Hub** page.
2. Inspect the **Connection Status** indicator: Shows a green `Connected` badge with daemon version `v0.33.0`.
3. **Upload File:**
   - Drag and drop any `.cif`, `.json`, or `.csv` material data file.
   - Check **Encrypt with AES-256-GCM** if the file contains confidential trade secrets.
   - Click **Upload & Pin to IPFS**.
4. The system sends file bytes to `/api/v0/add`, pins the block, updates MFS `/matchain/`, and returns the genuine CID.
5. **Direct Retrieval:** Click **Open Gateway** or **Download Verified Bytes** to retrieve the file directly from `http://127.0.0.1:8080/ipfs/{cid}`.

---

### 8.7 Decentralized IP Licensing and Marketplace
1. Navigate to the **Marketplace** page.
2. Browse active material listings showing formula, stability energy, IPFS CID, and price in ETH.
3. Switch user view to **Industrial Buyer**.
4. Click **Purchase Commercial License** on the desired material:
   - MetaMask prompts to confirm the transaction of `0.05 ETH` plus gas.
   - The smart contract holds funds in escrow, records the buyer's address, and unlocks authorized access to confidential synthesis files.
5. Switch view back to **Materials Scientist**: Click **Claim Escrow Revenue** to withdraw earned licensing royalties directly to your wallet.

---

## 9. Comprehensive Troubleshooting Guide

| Issue / Symptom | Probable Root Cause | Resolution Procedure |
|---|---|---|
| **"Failed to fetch" on Discovery or Upload** | FastAPI backend (`:8000`) is offline or crashed. | Check Terminal 3. Restart uvicorn: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`. |
| **"IPFS Node Disconnected" error** | Kubo daemon is not running or port 5001 is blocked. | Open a new terminal and run `ipfs daemon`. Verify `http://127.0.0.1:5001/api/v0/version` returns JSON in browser. |
| **IPFS Gateway URL contains duplicate `ipfs:/` prefix** | Legacy CID URL constructor formatted `ipfs/{cid}` with an already prefixed CID string. | Resolved in codebase. Ensure backend returns clean raw CIDs without protocol scheme. Verify gateway URL is `http://127.0.0.1:8080/ipfs/<CID>`. |
| **MetaMask "Transaction Failed: RPC Error"** | Ganache node (`:8545`) was restarted with new contract addresses. | Redeploy contracts: `npx hardhat run scripts/deploy.js --network localhost`. Clear MetaMask activity cache under Settings $\to$ Advanced $\to$ Clear activity tab data. |
| **Candidate discovery takes > 8 minutes** | Full atomic relaxation was enabled on a large candidate batch ($N \ge 100$) on CPU. | For rapid evaluation, use the deterministic demo recipe (`Mg2Si`), or reduce candidate count to 10–20 in the UI slider. |
| **"Zero Candidates Passed Consensus"** | AI models legitimately disagreed on complex quaternary composition (spread $\tau > 0.15\text{ eV}$). | Expected scientific behavior. Select well-characterized binary or ternary systems (e.g., Silicides, Oxides, Phosphates) to obtain consensus. |
| **3D Lattice Viewer shows black canvas** | WebGL disabled in browser or invalid CIF string format. | Ensure Hardware Acceleration is enabled in Chrome settings (`chrome://settings/system`). Verify candidate CIF contains valid lattice parameters. |
| **"Authentication Required (401)" on file download** | Attempting to access confidential file without connecting wallet. | Connect Web3 wallet in navbar. If file is restricted, ensure your address owns the material or has purchased an active marketplace license. |

---

## 10. Security, Cryptography, and Data Governance

### 10.1 Confidential File Encryption (AES-256-GCM)
MatChain provides dual-tier storage for material discoveries:
1. **Public Metadata:** Crystallographic space groups, lattice parameters, and formation energies are stored in plain `.cif` and `.json` formats on IPFS for open verification.
2. **Confidential Synthesis Recipes:** Proprietary laboratory instructions, precursor ratios, and experimental temperatures are encrypted on the backend using **AES-256-GCM** before IPFS ingestion. The 12-byte initialization vector (IV) and 16-byte authentication tag are prepended to the ciphertext. Decryption keys are released strictly to buyers with confirmed on-chain license receipts.

### 10.2 Cryptographic Provenance Integrity
Every material is permanently bound to its cryptographic signature:
$$\text{Material Fingerprint} = \text{SHA-256}(\text{Normalized CIF Data} \parallel \text{Composition} \parallel \text{Creator Address})$$
This 32-byte digest is stored immutably in `MaterialRegistry.sol`. Any alteration to atomic coordinates or lattice vectors invalidates the hash, preventing IP spoofing or tampering.

### 10.3 Private Key Safety
MatChain operates strictly with client-side Web3 providers (MetaMask / Ethers.js). The application never requests, transmits, or stores user private keys or seed phrases on backend servers.

---

## 11. System Shutdown and Maintenance Procedures

To safely shut down the platform:
1. **Frontend:** In Terminal 4, press `Ctrl + C` and confirm termination.
2. **Backend:** In Terminal 3, press `Ctrl + C`. SQLite WAL journal files will safely commit to disk (`mat_chain.db`).
3. **Blockchain:** In Terminal 2, press `Ctrl + C` to stop Ganache.
4. **IPFS Daemon:** In Terminal 1, press `Ctrl + C` to gracefully stop Kubo. Local repository blocks and pinsets are preserved in `~/.ipfs`.

To reset database state and start with a clean slate:
```powershell
# Remove SQLite database
Remove-Item backend\mat_chain.db -Force

# Contracts redeployment
cd contracts
npx hardhat run scripts/deploy.js --network localhost
```

---

## 12. Deployment Verification Sign-Off

This deployment configuration has been fully validated against automated test suites and live hardware execution:
- **Backend Test Suite:** 49 of 49 automated PyTest tests passing (100% success rate).
- **Frontend Build:** Clean compilation via Vite in 0.97 seconds.
- **Kubo IPFS Node:** Verified operational on ports 5001 / 8080.
- **Ganache Blockchain:** Verified operational on port 8545 with 2 deployed contracts.
- **Demonstration Pipeline:** $\text{Mg}_2\text{Si}$ complete lifecycle verified in 2.24 seconds.

