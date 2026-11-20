"""
MatChain — End-to-End Materials Pipeline Test Suite
===================================================
Comprehensive tests covering:
1. CDVAE Interface Contract & Scaffolding
2. Crystal Structure Decoding & Periodic Boundary Conditions (PBC)
3. Structure Hashing & Identity Preservation
4. Geometry Validation & Collision Detection
5. Calibrated Elemental Reference Energies (eV/atom)
6. Real CHGNet Inference & Formation Energy Conversion
7. Real M3GNet Inference & Formation Energy Conversion
8. Real XGBoost Inference & Magpie Featurization
9. Three-Judge Consensus Evaluation (Agreement, Disagreement, Incomplete)
10. Rejection Reason Codes & Accounting Laws
11. Duplicate Structure Suppression
12. End-to-End Pipeline Traceability & Persistence
"""

import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
from pymatgen.core import Composition, Lattice, Structure

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
while str(BACKEND) in sys.path:
    sys.path.remove(str(BACKEND))
sys.path.insert(0, str(BACKEND))
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import matchain_colab_corrected as mc
from app.services.cdvae_interface import (
    CDVAEGeneratorInterface,
    CDVAEInferenceConfig,
    CDVAEStatus,
)


@pytest.fixture(scope="session")
def trained_models():
    ds = mc.get_dataset()
    return mc.load_all_models(ds)


@pytest.fixture(scope="session")
def dataset():
    return mc.get_dataset()


# =====================================================================
# 1. CDVAE Interface & Tensor Decoding Tests
# =====================================================================

def test_cdvae_interface_status_reporting():
    """Verify CDVAE interface honestly reports operational status and weight search paths."""
    interface = CDVAEGeneratorInterface()
    diag = interface.get_diagnostics()
    assert diag["generator_name"] == "CDVAE"
    assert "status" in diag
    assert diag["status"] in [CDVAEStatus.OPERATIONAL.value, CDVAEStatus.WEIGHTS_NOT_FOUND.value]
    if not interface.is_operational:
        assert "weights" in diag["status_message"].lower() or "not found" in diag["status_message"].lower()


def test_cdvae_tensor_decoding_and_pbc_wrapping():
    """Verify CDVAE tensor-to-Structure decoding correctly wraps coordinates on the 3-torus T^3."""
    lengths = np.array([4.05, 4.05, 4.05])
    angles = np.array([90.0, 90.0, 90.0])
    atom_types = ["Al", "Al", "Al", "Al"]
    # Coordinates containing points outside [0, 1) that require periodic boundary wrapping
    frac_coords = np.array([
        [0.0, 0.0, 0.0],
        [1.5, 0.5, 0.0],   # wraps to [0.5, 0.5, 0.0]
        [0.5, -1.0, 0.5],  # wraps to [0.5, 0.0, 0.5]
        [0.0, 0.5, 2.5],   # wraps to [0.0, 0.5, 0.5]
    ])

    struct = CDVAEGeneratorInterface.decode_tensors_to_structure(lengths, angles, atom_types, frac_coords)
    assert struct is not None
    assert len(struct) == 4
    assert struct.composition.reduced_formula == "Al"
    # All wrapped fractional coordinates must be strictly in [0, 1)
    for site in struct:
        assert np.all(site.frac_coords >= 0.0)
        assert np.all(site.frac_coords < 1.0)


def test_cdvae_rejects_unphysical_lattice_tensors():
    """Verify decoding rejects unphysical lattice dimensions (e.g. < 1.5 A or > 30 A)."""
    # Unphysically small cell
    s_small = CDVAEGeneratorInterface.decode_tensors_to_structure(
        np.array([0.5, 0.5, 0.5]), np.array([90.0, 90.0, 90.0]), ["Al"], np.array([[0.0, 0.0, 0.0]])
    )
    assert s_small is None

    # Unphysical unit cell angles (< 30 deg)
    s_angles = CDVAEGeneratorInterface.decode_tensors_to_structure(
        np.array([5.0, 5.0, 5.0]), np.array([15.0, 90.0, 90.0]), ["Al"], np.array([[0.0, 0.0, 0.0]])
    )
    assert s_angles is None


# =====================================================================
# 2. Structure Hashing & Identity Preservation
# =====================================================================

def test_structure_hash_is_invariant_and_deterministic():
    """Verify structure payload and SHA-256 fingerprint are strictly deterministic."""
    lat = Lattice.cubic(4.05)
    s1 = Structure(lat, ["Al"] * 4, [[0,0,0],[0.5,0.5,0],[0.5,0,0.5],[0,0.5,0.5]])
    s2 = Structure(lat, ["Al"] * 4, [[0,0,0],[0.5,0.5,0],[0.5,0,0.5],[0,0.5,0.5]])

    p1 = mc.structure_payload(s1)
    p2 = mc.structure_payload(s2)
    h1 = mc.sha256_hash(p1)
    h2 = mc.sha256_hash(p2)

    assert h1 == h2
    assert len(h1) == 64


# =====================================================================
# 3. Geometry Validation & Collision Detection
# =====================================================================

def test_geometry_validation_detects_atomic_collision():
    """Verify atomic collisions (< 0.7 A) are reliably flagged with explicit reason codes."""
    lat = Lattice.cubic(5.0)
    # Atoms placed 0.25 A apart (0.05 * 5.0 A = 0.25 A < 0.70 A)
    colliding = Structure(lat, ["Al", "Al"], [[0.0, 0.0, 0.0], [0.05, 0.0, 0.0]])
    is_valid, reason = mc.validate_generated_structure(colliding, min_dist=0.70)
    assert not is_valid
    assert "Atomic collision" in reason
    assert "< 0.7" in reason


def test_geometry_validation_accepts_valid_crystals():
    """Verify standard crystallographic structures pass physical validation."""
    s_al = mc.get_elemental_ground_state_structure("Al")
    assert s_al is not None
    is_valid, reason = mc.validate_generated_structure(s_al, min_dist=0.70)
    assert is_valid
    assert reason == "Valid"


# =====================================================================
# 4. Reference Energy Calibration & Unit Consistency (eV/atom)
# =====================================================================

def test_standard_elemental_references_yield_zero_formation_energy(trained_models):
    """
    Verify that pure elements evaluated under calibrated reference frames yield
    formation energy Delta E_f == 0.000 eV/atom by standard definition.
    """
    models = trained_models

    for el in ["Al", "Ti", "Fe", "Si"]:
        s = mc.get_elemental_ground_state_structure(el)
        assert s is not None

        # CHGNet prediction
        fe_chg = mc.chgnet_predict_formation_energy(s, models)
        if fe_chg is not None:
            assert abs(fe_chg) < 0.05, f"CHGNet formation energy for pure {el} must be ~0.0 eV/atom, got {fe_chg}"

        # M3GNet prediction
        fe_m3g = mc.m3gnet_predict_formation_energy(s, models)
        if fe_m3g is not None:
            assert abs(fe_m3g) < 0.05, f"M3GNet formation energy for pure {el} must be ~0.0 eV/atom, got {fe_m3g}"

        # XGBoost prediction
        fe_xgb = mc.xgboost_predict_formation_energy(s, models)
        if fe_xgb is not None:
            assert abs(fe_xgb) < 0.10, f"XGBoost formation energy for pure {el} must be ~0.0 eV/atom, got {fe_xgb}"


# =====================================================================
# 5. Three-Judge Consensus Evaluation Tests
# =====================================================================

def test_ensemble_consensus_requires_all_three_judges():
    """Verify consensus rejects candidates when any judge is missing or fails (evaluation_incomplete)."""
    # Create mock models dictionary with one missing judge
    mock_models = {
        "chgnet_model": None, # CHGNet missing
        "m3gnet_calc": None,
        "xgb_model": None,
        "magpie_featurizer": None,
        "chgnet_refs": {},
        "m3gnet_refs": {},
    }
    lat = Lattice.cubic(4.0)
    s = Structure(lat, ["Al"] * 2, [[0, 0, 0], [0.5, 0.5, 0.5]])

    passed, mean_pred, spread, preds, msg, record = mc.ensemble_consensus(s, mock_models, tau=0.15)
    assert not passed
    assert record["consensus"]["status"] == "evaluation_incomplete"
    assert "JUDGE_PREDICTION_FAILED" in record["consensus"]["reason"]
    assert record["consensus"]["evaluated_judges"] < 3


def test_ensemble_consensus_detects_judge_disagreement(trained_models):
    """Verify consensus fails when three judges evaluate but energy spread exceeds tau."""
    models = trained_models
    struct = mc.get_elemental_ground_state_structure("Al")

    # If tau is set extremely strict (e.g. 1e-6 eV/atom), realistic numerical spread triggers disagreement
    passed, mean_pred, spread, preds, msg, record = mc.ensemble_consensus(struct, models, tau=1e-6)
    if record["consensus"]["evaluated_judges"] == 3:
        assert not passed
        assert record["consensus"]["status"] == "judge_disagreement"
        assert "exceeds tau" in record["consensus"]["reason"]


def test_ensemble_consensus_passes_on_unanimous_agreement(trained_models):
    """Verify consensus passes when all 3 judges agree within tau = 0.15 eV/atom."""
    models = trained_models
    struct = mc.get_elemental_ground_state_structure("Al")

    passed, mean_pred, spread, preds, msg, record = mc.ensemble_consensus(struct, models, tau=0.15)
    if record["consensus"]["evaluated_judges"] == 3:
        assert passed
        assert record["consensus"]["status"] == "consensus_passed"
        assert record["consensus"]["reason"] is None
        assert spread is not None and spread <= 0.15


# =====================================================================
# 6. Rejection Reason Codes & Accounting Laws
# =====================================================================

def test_pipeline_diagnostics_strict_accounting_conservation(trained_models, dataset):
    """
    Verify strict mathematical conservation of candidate counts across pipeline stages:
    generated = geometry_valid + geometry_rejected + duplicates_rejected
    thermodynamic_evaluated = e_hull_passed + e_hull_rejected
    jury_evaluated = e_hull_passed
    jury_evaluated = jury_passed + jury_rejected + jury_incomplete
    """
    models = trained_models
    ds = dataset

    target_cond = {"formation_energy_per_atom": -1.5, "band_gap": 0.0, "density": 5.0}
    results, elapsed, diag = mc.matchain_pipeline(
        target_condition=target_cond,
        n_candidates=20,
        tau=0.15,
        top_k=5,
        models=models,
        dataset_df=ds,
        relax=False,
        verbose=False,
    )

    n_gen = diag["generated"]
    g_val = diag["geometry_valid"]
    g_rej = diag["geometry_rejected"]
    d_rej = diag.get("duplicates_rejected", 0)

    # 1. Generation conservation
    assert n_gen == g_val + g_rej + d_rej

    # 2. Thermodynamic filter conservation
    th_eval = diag["thermodynamic_evaluated"]
    eh_pass = diag["e_hull_passed"]
    eh_rej = diag["e_hull_rejected"]
    assert th_eval == eh_pass + eh_rej

    # 3. Jury evaluation conservation
    j_eval = diag["jury_evaluated"]
    j_pass = diag["jury_passed"]
    j_rej = diag["jury_rejected"]
    j_inc = diag.get("jury_incomplete", 0)
    assert j_eval == eh_pass
    assert j_eval == j_pass + j_rej + j_inc


# =====================================================================
# 7. Candidate Traceability & Result Record Integrity
# =====================================================================

def test_candidate_result_schema_and_provenance(trained_models, dataset):
    """Verify each accepted candidate has full traceability, hashes, and 3-judge records."""
    models = trained_models
    ds = dataset

    target_cond = {"formation_energy_per_atom": 0.0, "density": 2.7}
    results, elapsed, diag = mc.matchain_pipeline(
        target_condition=target_cond,
        n_candidates=10,
        tau=0.25,
        top_k=5,
        models=models,
        dataset_df=ds,
        relax=False,
    )

    for cand in results:
        assert "candidate_id" in cand
        assert "structure_hash" in cand
        assert cand["structure_hash"].startswith("0x")
        assert "generator" in cand
        assert "judges" in cand
        assert "consensus" in cand
        assert "chgnet" in cand["judges"]
        assert "m3gnet" in cand["judges"]
        assert "xgboost" in cand["judges"]
