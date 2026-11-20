# MatChain — Known Limitations & Scientific Disclaimers

**Version:** 2.0  
**Scope:** Model Assumptions, Data Provenance, Computational Boundaries & Wet-Lab Translation Disclaimers

---

## 1. Materials Generation & Model Architecture Limitations

### 1.1 CrystalVAE vs. Diffusion Models (CDVAE)
- **Active Generator:** The default operational generator in MatChain is `CrystalVAE`, a multi-layer perceptron (MLP) variational autoencoder that generates continuous chemical formula encodings and lattice parameters conditioned on target properties.
- **Prototype Grounding Requirement:** To preserve space group symmetries and prevent unphysical site overlaps, continuous representations are mapped to crystallographic prototypes (BCC, FCC, HCP, Rocksalt, Sphalerite, Perovskite). While this ensures physical validity ($d_{\min} \ge 0.70\text{ \AA}$), it restricts generation to known crystal families and does not discover entirely novel Wyckoff site symmetries.
- **CDVAE Checkpoint Dependency:** The deep diffusion generator interface (`CDVAEGeneratorInterface` in `backend/app/services/cdvae_interface.py`) is fully implemented with periodic boundary wrapping and tensor validation. However, genuine diffusion generation requires pre-trained checkpoint weights (`mp_20.ckpt`, ~400 MB). When weights are not present, the system cleanly and honestly reports `weights_not_found` and falls back to CrystalVAE rather than fabricating synthetic diffusion structures.

### 1.2 Surrogate Evaluator Constraints
- **XGBoost Representation:** The XGBoost surrogate model is trained on 132 Magpie composition descriptors via MatMiner. It evaluates purely compositional trends and is blind to atomic site permutations or polymorphic variations of the same formula. It is therefore paired with structural graph neural networks (CHGNet and M3GNet) to form a balanced jury.
- **CPU Inference Latency:** Running graph neural network evaluations (CHGNet with atomic charges and M3GNet with 3-body angles) on CPU requires approximately 0.5 to 2.0 seconds per structure. Large discovery batches ($N > 100$) should be run on CUDA-enabled GPU hardware for high-throughput screening.

---

## 2. Dataset Provenance & Reference Systems

### 2.1 Materials Project Reference Subset
- The convex hull phase diagram and elemental reference frames are constructed from a curated 1,500-structure subset derived from the Materials Project database (`data/mp_subset_1500.json`).
- While this subset spans standard elemental ground states and common binary/ternary systems (oxides, sulfides, halides, nitrides), complex quaternary or quinary phase spaces may have incomplete hull envelopes. Candidates in under-represented chemical spaces may appear artificially stable relative to an incomplete hull.

---

## 3. Computational Screening vs. Experimental Wet-Lab Synthesis

> [!IMPORTANT]
> **Scientific Disclaimer:** Computational thermodynamic stability ($E_{\text{hull}} \le 0.05\text{ eV/atom}$) and surrogate jury consensus are necessary screening criteria, but they do **not** guarantee laboratory synthesizability.

1. **Thermodynamic vs. Kinetic Stability:** A candidate material may have a negative formation energy but remain kinetically inaccessible due to high activation energy barriers or competing metastable polymorphs.
2. **Environmental & Chemical Factors:** Universal potential calculations are performed at $T = 0\text{ K}$ in a vacuum. High-temperature phase transitions, vibrational entropy, moisture sensitivity, oxidation susceptibility, and toxic precursor requirements are not modeled in the first-pass screening funnel.
3. **Wet-Lab Translation:** Any candidate proposed by MatChain must undergo first-principles Density Functional Theory (DFT) relaxation (e.g., VASP, Quantum ESPRESSO) followed by experimental solid-state or wet-chemical synthesis and X-ray diffraction (XRD) confirmation before patenting or industrial application.

---

## 4. Blockchain & Decentralized Storage Boundaries

### 4.1 Local EVM vs. Public Mainnet
- The blockchain smart contract layer (`MatChainRegistry.sol` and `MatChainMarketplace.sol`) is configured for a local development Ethereum node (Ganache on `127.0.0.1:7545` or Hardhat Node on `127.0.0.1:8545` with Chain ID `1337`).
- When running in an environment without a local EVM node active, the backend's `BlockchainService` operates in a safe offline fallback mode (`available: false`), logging clear warnings rather than failing or creating simulated on-chain transactions.

### 4.2 IPFS Node Scope
- IPFS content-addressed storage utilizes a local Kubo node (`127.0.0.1:5001`). Uploaded files and MFS mirrors are immediately accessible on the local machine and via local gateways (`127.0.0.1:8080/ipfs/`).
- For global public gateway retrieval (e.g., `ipfs.io`), the local node must be peered with public bootstrap nodes or connected to a pinning service (e.g., Pinata, Filecoin).

---

## 5. Roadmap for Production Scaling

To transition MatChain into a production-grade enterprise discovery platform:
1. **Automated DFT Feeder:** Integrate an automated workflow engine (e.g., Atomate2 / FireWorks) to dispatch DFT calculation jobs for all candidates passing surrogate jury consensus.
2. **Active Learning Feedback Loop:** Re-train XGBoost, CHGNet, and M3GNet surrogates iteratively on newly calculated DFT energies to reduce surrogate epistemic uncertainty.
3. **GPU Cluster Orchestration:** Deploy Celery / Redis background worker pools on multi-GPU nodes to scale generation and relaxation throughput to $10,000+$ candidates per hour.
4. **Decentralized Identifier (DID) Integration:** Replace local AES key management with decentralized identity and public key encryption (e.g., Lit Protocol or ECIES) for trustless peer-to-peer IP licensing.

