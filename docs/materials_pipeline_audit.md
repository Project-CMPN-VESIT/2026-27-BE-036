# MatChain — Materials Generation Pipeline & Model Performance Audit Report

**Date:** October 25, 2026  
**Auditor:** Senior Computational Materials Scientist & AI/ML Systems Engineer  
**System Under Audit:** MatChain Materials Discovery & IP Provenance Pipeline  
**Repository Branch/Commit:** Main Active Working Copy  
**Python Runtime:** Python 3.11.9 (64-bit, Windows AMD64)  
**Primary Dependencies:** PyTorch 2.14.0, PyMatGen 2026.5.4, MatMiner 0.10.1, CHGNet 0.4.2, MatGL 4.0.3 (M3GNet), XGBoost 3.2.0, FastAPI 0.115.8, Web3.py 8.0.0

---

## 1. Executive Summary & Audit Classification

An exhaustive end-to-end technical audit was conducted on the generative materials pipeline of MatChain, spanning data ingestion, generative modeling, structure decoding, geometry validation, thermodynamic screening, multi-model surrogate evaluation, backend persistence, API serialization, and frontend rendering.

### Primary Audit Verdict:
| Objective | Documented Claim | Verified Reality | Status |
| :--- | :--- | :--- | :---: |
| **1. Generative Architecture** | CDVAE (Crystal Diffusion VAE) | Multi-Layer Perceptron VAE (`CrystalVAE`) with prototype substitution | ❌ **Defect Confirmed** |
| **2. Structure Decoding** | Decoded fractional coordinates & lattice | Nearest-prototype coordinate replacement + tiny Gaussian jitter | ❌ **Defect Confirmed** |
| **3. Three-Judge Evaluation** | 3 independent judges (CHGNet, M3GNet, XGBoost) | CHGNet & M3GNet votes were silently suppressed; single-surrogate fallback | ❌ **Defect Confirmed** |
| **4. Consensus Calculation** | Three-judge consensus agreement within $\tau=0.15$ eV | Agreement fabricated as $\tau=0.000$ when 1 model remained | ❌ **Defect Confirmed** |
| **5. Thermodynamic Hull** | Convex hull phase diagram ($E_{\text{hull}} \le 0.05$ eV/atom) | Computed with PyMatGen `PhaseDiagram`, but fed uncalibrated candidate energies | ⚠️ **Scientific Limitation** |
| **6. Output Diversity** | Diverse novel candidate crystals | 96 valid structures produced only 12 unique compositions (12.5% diversity) | ❌ **Defect Confirmed** |
| **7. Candidate Provenance** | Unique SHA-256 structure fingerprints | Backend fabricated hashes & target values on rejected candidates | ❌ **Defect Confirmed** |
| **8. Test Suite Health** | 21/21 passing tests | 19 passing, 2 failing due to schema mismatch & unseeded test database | ❌ **Defect Confirmed** |

---

## 2. End-to-End Call Graph & Traceability

The complete execution path from user interaction to display was traced through the codebase:

```
[User clicks "Run Generation & Validation" in Frontend (DiscoveryPage.tsx)]
                          │
                          ▼  POST /api/discovery/generate (TargetCondition: FE, BG, Density, tau, top_k)
[FastAPI Router (app/main.py)]
                          │
                          ▼  Calls service.create_job() & asyncio.create_task(service.run_job)
[MatchainService (app/services/matchain_service.py)]
                          │
                          ▼  Invokes matchain_colab_corrected.matchain_pipeline()
[Core ML Engine (matchain_colab_corrected.py)]
     ├── 1. Dataset Loading: get_dataset() [Synthetic 1500-sample fallback]
     ├── 2. Model Loading: load_all_models()
     │      ├── Train/test split (80/20)
     │      ├── Train CrystalVAE (MLP, 40 epochs)
     │      ├── Load CHGNet (v0.3.0 weights)
     │      ├── Load M3GNet (MatPES-PBE-2025.2 via MatGL)
     │      ├── Train XGBoost on MatMiner Magpie features
     │      └── Evaluate held-out test set & fit elemental reference energies
     ├── 3. Generation: generate_candidates()
     │      ├── VAE decode(z, c) -> continuous feature vector
     │      ├── vector_to_structure_grounded() -> Nearest prototype substitution
     │      └── validate_generated_structure() -> Min distance >= 0.7 Å check
     ├── 4. Thermodynamic Screening: thermodynamic_filter()
     │      ├── Approximate candidate formation energy
     │      ├── Construct local PhaseDiagram via PyMatGen
     │      └── Filter candidates with E_hull < 0.05 eV/atom
     ├── 5. Jury Consensus: run_ensemble_jury()
     │      ├── ensemble_consensus() evaluates CHGNet, M3GNet, XGBoost
     │      └── Strips failing models and calculates spread
     └── 6. Return top_k sorted by consensus spread
                          │
                          ▼  Serialized into SQLite jobs_store
[JobsStore (app/services/jobs_store.py)]
                          │
                          ▼  Polled via GET /api/discovery/jobs/{job_id}
[Frontend Rendering (DiscoveryPage.tsx & DashboardPage.tsx)]
```

---

## 3. Detailed Audit Findings by Component

### Finding 1: The Generative Model is CrystalVAE (MLP), Not CDVAE
- **File:** [`matchain_colab_corrected.py:325-357`](file:///d:/Matchain/matchain_colab_corrected.py#L325-L357)
- **Verified Behavior:**
  - The model class is `CrystalVAE(nn.Module)`.
  - Architecture: Multi-Layer Perceptron (Linear-ReLU-Linear) encoder (`feat_dim + cond_dim -> hidden -> latent_dim=32`) and decoder (`latent_dim + cond_dim -> hidden -> feat_dim`).
  - Feature representation `feat_dim = len(element_vocab) + 6`: composition element fractions + 6 lattice scalars `[a, b, c, alpha, beta, gamma]`.
  - Condition dimension `cond_dim = 3`: normalized `[formation_energy, band_gap, density]`.
- **Confirmed Defect:**
  - CDVAE (Xie et al. ICLR 2022) is an equivariant crystal diffusion model operating on 3D fractional coordinate point clouds under periodic boundary conditions using GemNet or DimeNet encoders with score-based Langevin diffusion.
  - The codebase explicitly contains a note on line 7 acknowledging: *"This demo uses a property-conditioned composition+lattice VAE with structure grounding... It is a simplified stand-in for the full CDVAE described in the paper."*
  - No CDVAE checkpoint (`.ckpt` or `.pt`) or diffusion reverse sampling loop exists in the repository.

### Finding 2: Structure Grounding Substitutes Real Prototypes Instead of Decoded Coordinates
- **File:** [`matchain_colab_corrected.py:413-480`](file:///d:/Matchain/matchain_colab_corrected.py#L413-L480)
- **Verified Behavior:**
  - The decoded vector contains both composition fractions and 6 lattice scalars (`lat_vec`).
  - However, `vector_to_structure_grounded` completely **discards the decoded lattice scalars**!
  - It searches `dataset_df` using `find_prototype_structure` for a prototype with matching elements.
  - When a prototype is found:
    ```python
    frac_coords = proto_struct.frac_coords.copy()
    jitter = np.random.normal(0, 0.003, size=frac_coords.shape)
    frac_coords = (frac_coords + jitter) % 1.0
    return Structure(new_lattice, site_species, frac_coords)
    ```
  - When no prototype is found, it constructs an artificial cubic box with 2, 4, or linear-spaced atomic coordinates.
- **Confirmed Defect:**
  - The generator does not generate true 3D crystal structures; it queries an existing database prototype, adds 0.003 Å Gaussian noise, and re-labels the atoms round-robin.
  - This leads to catastrophic duplication: in a test run of 100 candidates, 96 passed geometry, but **only 12 unique compositions were generated**, with `Ba2Ti3O3` appearing 36 times and `LiCoO2` appearing 18 times!

### Finding 3: Three Judges Were Silently Suppressed (Fabricated Agreement)
- **File:** [`backend/app/services/matchain_service.py:70-74`](file:///d:/Matchain/backend/app/services/matchain_service.py#L70-L74) and [`matchain_colab_corrected.py:1058-1088`](file:///d:/Matchain/matchain_colab_corrected.py#L1058-L1088)
- **Empirical Test Evidence (from runtime audit):**
  - Held-out test set evaluation:
    - `xgboost`: $R^2 = 0.99995$, $\text{MAE} = 0.0056\text{ eV/atom}$ (due to composition repetition in synthetic dataset)
    - `chgnet`: $R^2 = -0.1594$, $\text{MAE} = 0.9891\text{ eV/atom}$
    - `m3gnet`: $R^2 = -293.64$, $\text{MAE} = 10.435\text{ eV/atom}$, $\text{Max Abs Error} = 129.60\text{ eV/atom}$
- **Confirmed Defect:**
  - In `backend/app/services/matchain_service.py:72`:
    ```python
    if m_eval and m_eval.get("r2", 0) < 0:
        models["m3gnet_calc"] = None  # Silently disabled!
    ```
  - In `matchain_colab_corrected.py:1065`:
    ```python
    if (r2 is not None and r2 < 0.0) or (mae is not None and mae > 1.5):
        continue  # Stripped from voting!
    ```
  - In `matchain_colab_corrected.py:1078`:
    ```python
    if len(vals) <= 1:
        return True, float(vals[0]), 0.0, preds, "Passed (primary surrogate consensus)"
    ```
  - **Result:** Candidate 1 (`TiAlV`) had predictions:
    - CHGNet: `-0.5925 eV/atom`
    - M3GNet: `-8.1174 eV/atom`
    - XGBoost: `-0.3358 eV/atom`
    The actual inter-model spread was $7.7816\text{ eV/atom}$! Yet the system reported `consensus_spread = 0.0000`, declared consensus `Passed`, and registered it as a validated candidate!

### Finding 4: Why M3GNet and CHGNet Diverged on Synthetic Data
- **File:** [`matchain_colab_corrected.py:211-240`](file:///d:/Matchain/matchain_colab_corrected.py#L211-L240)
- **Root Cause Analysis:**
  - `make_synthetic_dataset` generates structures using `_make_structure_for_formula`, which places atoms at fixed grid points (e.g. $[0,0,0], [0.5,0.5,0], [0.5,0,0.5]$) in arbitrary cubic unit cells.
  - It then pairs these arbitrary coordinates with target formation energies copied from relaxed experimental compounds.
  - CHGNet and M3GNet are graph neural network universal force fields that evaluate actual interatomic distances and bonding environments.
  - When evaluating these unrelaxed, artificially packed lattices, the atomic cores experience severe strain, yielding raw total energies far away from ground truth.
  - The linear reference frame fitting (`fit_energy_reference_frame`) attempts an unregularized ordinary least squares fit on these noisy points, resulting in corrupted reference coefficients (e.g. Al elemental reference energy fitted to $+29.47\text{ eV}$ in M3GNet!).

### Finding 5: Fabricated Candidate Attributes in Backend Fallback
- **File:** [`backend/app/services/matchain_service.py:165-177`](file:///d:/Matchain/backend/app/services/matchain_service.py#L165-L177)
- **Confirmed Defect:**
  - When zero candidates pass validation, the backend tried to populate the dashboard `top_candidates` from `cand_details`:
    ```python
    "material_hash": sha256_hash(f"{job['job_id']}_{i}_{cd.get('formula')}"),
    "density": target_cond.get("density", 4.5),  # Fabricated!
    "e_hull": cd.get("e_hull", 0.0),
    "status": cd.get("status", "screened"),
    ```
  - It fabricated a material hash from the job ID string and replaced the actual candidate density with the target condition density!

### Finding 6: Test Suite Regression in Marketplace
- **File:** [`backend/tests/test_marketplace.py:25-56`](file:///d:/Matchain/backend/tests/test_marketplace.py#L25-L56)
- **Confirmed Defect:**
  - `test_marketplace_audit` failed with HTTP 400 because `_audit_material` expected the material hash to exist in the database or registry, but the test used an unseeded empty database.
  - `test_marketplace_validate_attestation` failed with HTTP 422 because `MarketplaceValidateRequest` schema required `transaction_hash`, which was omitted from the test dictionary.

### Finding 7: Double Normalization of CHGNet Output (Extraneous Division by Atom Count)
- **File:** [`matchain_colab_corrected.py:1003, 1080, 1102, 1302`](file:///d:/Matchain/matchain_colab_corrected.py#L1003)
- **Confirmed Defect:**
  - Official CHGNet documentation explicitly specifies: `prediction['e'] : energy of structures float in eV/atom`.
  - The codebase repeatedly executed `float(models['chgnet_model'].predict_structure(s)['e']) / len(s)`.
  - This divided an already normalized intensive quantity (eV/atom) by the site count $N$ a second time.
  - As a result, unit cells with 8 atoms had their energy divided by 8, while elemental reference cells with 2 atoms were divided by 2. This introduced an artificial scaling factor of $N_{\text{ref}} / N_{\text{cand}}$ that severely corrupted compound formation energies and inflated inter-model spread by $> 1.0\text{ eV/atom}$.

### Finding 8: XGBoost Compositional Blindness to 3D Geometry
- **File:** [`matchain_colab_corrected.py:985-994, 1130-1140`](file:///d:/Matchain/matchain_colab_corrected.py#L985-L994)
- **Scientific Limitation:**
  - XGBoost was trained strictly on Magpie composition descriptors (atomic numbers, electronegativity, ionic radii statistics).
  - It has zero geometric inputs: no coordinates, no bond lengths, no space group, and no cell volume.
  - Consequently, XGBoost predicts the exact same formation energy for an unrelaxed, highly strained lattice as it does for a fully relaxed DFT ground state.
  - This creates an inherent epistemological gap: XGBoost predicts the expected ground-state formation energy of the chemical formula, whereas CHGNet and M3GNet evaluate the instantaneous potential energy of the unrelaxed atomic coordinates.

### Finding 9: Nature of the $\le 0.013$ eV/atom Agreement on Standard Crystals
- **File:** [`matchain_colab_corrected.py:693-750`](file:///d:/Matchain/matchain_colab_corrected.py#L693-L750)
- **Scientific Clarification:**
  - The calibrated reference frame sets $\mu_i^0$ by computing raw potential energy on standard elemental crystals (FCC Al, BCC Fe, Diamond Si).
  - For those specific crystals, $\Delta H_f = E_{\text{raw}} - \mu_i^0 \equiv 0.000\text{ eV/atom}$ by mathematical definition.
  - For binary oxides ($MgO, NaCl, ZnS$), non-metal references were inverted directly from their experimental formation energies.
  - Therefore, the $\le 0.013\text{ eV/atom}$ agreement on those calibration structures reflects proper reference definition, not independent generalization across unseen crystal chemistries.

### Finding 10: Official CDVAE Model & Checkpoint Availability Blockers
- **Repository Reference:** `txie-93/cdvae` (ICLR 2022)
- **Confirmed Verification:**
  - Official GitHub Issue #72 confirms that the original authors never published pre-trained generative checkpoints (`mp_20.ckpt`) in the repository; only supervised property-prediction models (`cdvae/prop_models/mp20`) and training scripts were provided.
  - Pre-compiling `torch_scatter` and `torch_sparse` on Windows CPU-only environments without MSVC toolchains is not natively supported.
  - The runtime environment possesses no CUDA GPU (`torch.cuda.is_available() == False`) and only 2.2 GB of available RAM, rendering training a diffusion model from scratch physically infeasible on this machine.

---

## 4. Defect Classification & Action Plan

| ID | Issue Description | Severity | Status | Resolution |
| :--- | :--- | :---: | :---: | :--- |
| **D1** | Lack of CDVAE interface and missing checkpoint transparency | **High** | **Addressed** | Built `CDVAEGeneratorInterface` with strict Xie et al. contract; reports `weights_not_found` honestly |
| **D2** | Prototype grounding replaces decoded coordinates with noise | **High** | **Addressed** | Implemented continuous lattice decoding and deduplication tracking in VAE latent space |
| **D3** | Silent suppression of judges and fabricated consensus | **Critical** | **Resolved** | Enforced 3-judge jury; all 3 judges required; returns `evaluation_incomplete` on failures |
| **D4** | CHGNet double normalization (extraneous `/ len(struct)`) | **Critical** | **Resolved** | Corrected CHGNet energy extraction to native eV/atom; reduced average spread by >1.0 eV/atom |
| **D5** | Energy reference frame divergence in M3GNet/CHGNet | **High** | **Resolved** | Calibrated reference energies on standard ground-state crystals at 0 K |
| **D6** | Structure relaxation disabled by default | **Medium** | **Addressed** | Added active CHGNet `StructOptimizer` with geometry re-validation; verified yield improvement |
| **D7** | Fabricated candidate properties in backend fallback | **Critical** | **Resolved** | Removed fabricated hashes and hardcoded densities; preserves genuine candidate IDs and records |
| **D8** | Two failing automated tests in backend test suite | **Medium** | **Resolved** | Seeded test database fixture and provided `transaction_hash`; 33/33 tests green |

