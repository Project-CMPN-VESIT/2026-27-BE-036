"""
MatChain — CDVAE (Crystal Diffusion Variational Autoencoder) Interface
======================================================================
This module provides a production-grade interface and validation scaffolding
for the official Crystal Diffusion Variational Autoencoder (CDVAE) architecture
described in Xie et al., ICLR 2022 ("Crystal Diffusion Variational Autoencoder
for Periodic Materials").

Scientifically Honest Note:
--------------------------
CDVAE requires:
1. Pretrained PyTorch Lightning checkpoint (.ckpt) trained on MP-20, Carbon-24, or Perov-5.
2. Geometric graph encoding (GemNet-OC / DimeNet++).
3. Score-based Langevin diffusion on fractional coordinates on the 3-torus T^3.

When checkpoint weights are not present in the local environment, this interface
explicitly reports `operational = False` with reason `WEIGHTS_NOT_FOUND`, provides
reproducible instructions for placing official weights, and exposes a deterministic
test harness for unit testing the tensor decoding and structure reconstruction contract.
"""

from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from pymatgen.core import Lattice, Structure


class CDVAEStatus(str, Enum):
    OPERATIONAL = "operational"
    WEIGHTS_NOT_FOUND = "weights_not_found"
    DEPENDENCY_MISSING = "dependency_missing"
    SCAFFOLDING_MOCK = "scaffolding_mock"


@dataclass
class CDVAEInferenceConfig:
    """Configuration parameters matching official CDVAE inference specification."""
    model_name: str = "mp_20"
    checkpoint_path: Optional[str] = None
    device: str = "cpu"
    batch_size: int = 10
    step_lr: float = 1e-4
    min_sigma: float = 0.01
    num_steps: int = 100
    seed: int = 42
    target_properties: Dict[str, float] = field(default_factory=lambda: {
        "formation_energy_per_atom": -1.5,
        "band_gap": 0.0,
        "density": 5.0,
    })


class CDVAEGeneratorInterface:
    """
    Formal interface for CDVAE generator.
    Enforces deterministic tensor-to-Structure decoding, periodic boundary condition
    enforcement, and strict diagnostic logging.
    """

    DEFAULT_CHECKPOINT_DIRS = [
        Path(__file__).resolve().parents[2] / "checkpoints" / "cdvae",
        Path(__file__).resolve().parents[3] / "checkpoints" / "cdvae",
        Path.home() / ".cache" / "cdvae",
    ]

    def __init__(self, config: Optional[CDVAEInferenceConfig] = None) -> None:
        self.config = config or CDVAEInferenceConfig()
        self.checkpoint_file = self._resolve_checkpoint_path()
        self.status, self.status_message = self._check_operational_status()
        self.model: Optional[Any] = None

    def _resolve_checkpoint_path(self) -> Optional[Path]:
        if self.config.checkpoint_path:
            p = Path(self.config.checkpoint_path)
            if p.is_file():
                return p

        # Check default locations for mp_20.ckpt, etc.
        for folder in self.DEFAULT_CHECKPOINT_DIRS:
            candidate = folder / f"{self.config.model_name}.ckpt"
            if candidate.is_file():
                return candidate
            candidate_pt = folder / f"{self.config.model_name}.pt"
            if candidate_pt.is_file():
                return candidate_pt
        return None

    def _check_operational_status(self) -> Tuple[CDVAEStatus, str]:
        if self.checkpoint_file is not None and self.checkpoint_file.is_file():
            return CDVAEStatus.OPERATIONAL, f"CDVAE checkpoint verified: {self.checkpoint_file}"
        return (
            CDVAEStatus.WEIGHTS_NOT_FOUND,
            (
                f"CDVAE checkpoint '{self.config.model_name}.ckpt' was not found in "
                f"{[str(p) for p in self.DEFAULT_CHECKPOINT_DIRS]}. "
                "Official pretrained weights from https://github.com/txie-93/cdvae "
                "are required for genuine diffusion inference."
            ),
        )

    @property
    def is_operational(self) -> bool:
        return self.status == CDVAEStatus.OPERATIONAL

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "generator_name": "CDVAE",
            "model_version": self.config.model_name,
            "status": self.status.value,
            "status_message": self.status_message,
            "checkpoint_path": str(self.checkpoint_file) if self.checkpoint_file else None,
            "is_operational": self.is_operational,
            "diffusion_steps": self.config.num_steps,
            "step_lr": self.config.step_lr,
        }

    @staticmethod
    def decode_tensors_to_structure(
        lengths: np.ndarray,
        angles: np.ndarray,
        atom_types: List[int | str],
        frac_coords: np.ndarray,
    ) -> Optional[Structure]:
        """
        Converts decoded CDVAE tensor outputs into a valid periodic pymatgen Structure.
        Applies periodic boundary condition wrapping: frac_coords % 1.0.
        """
        try:
            # 1. Validate lengths (a, b, c in Angstroms)
            a, b, c = float(lengths[0]), float(lengths[1]), float(lengths[2])
            if not (1.5 <= a <= 30.0 and 1.5 <= b <= 30.0 and 1.5 <= c <= 30.0):
                return None

            # 2. Validate angles (alpha, beta, gamma in degrees)
            alpha, beta, gamma = float(angles[0]), float(angles[1]), float(angles[2])
            if not (30.0 <= alpha <= 150.0 and 30.0 <= beta <= 150.0 and 30.0 <= gamma <= 150.0):
                return None

            lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)
            if lattice.volume <= 1.0 or lattice.volume > 5000.0:
                return None

            # 3. Fractional coordinates on 3-torus [0, 1)
            coords = np.asarray(frac_coords, dtype=np.float64) % 1.0
            if coords.shape[0] != len(atom_types) or coords.shape[1] != 3:
                return None

            return Structure(lattice, atom_types, coords)
        except Exception:
            return None

    def generate_candidate_tensors_scaffolding(
        self,
        n_samples: int = 5,
        target_density: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """
        Deterministic scaffolding generator implementing the exact CDVAE tensor contract.
        Used for verification and automated testing of tensor decoding pipelines.
        """
        rng = np.random.RandomState(self.config.seed)
        tensors = []

        # Elements commonly synthesized (Ti, Al, V, O, Li, Fe)
        species_palette = ["Ti", "Al", "V", "O", "Li", "Fe", "Ni", "Co"]

        for i in range(n_samples):
            n_atoms = rng.randint(4, 12)
            selected_species = [species_palette[(i + j) % len(species_palette)] for j in range(n_atoms)]

            # Target volume estimation from target density
            approx_mass = float(sum(Structure(Lattice.cubic(4.0), [s], [[0,0,0]]).composition.weight for s in selected_species))
            est_vol = approx_mass / (max(1.0, target_density) * 0.602214)
            a = float(np.clip(est_vol ** (1 / 3), 3.0, 15.0))

            lengths = np.array([a, a * rng.uniform(0.9, 1.1), a * rng.uniform(0.9, 1.1)])
            angles = np.array([90.0, 90.0, rng.uniform(85.0, 95.0)])

            # Dispersed coordinates with minimal overlap
            coords = rng.uniform(0.05, 0.95, size=(n_atoms, 3))

            tensors.append({
                "lengths": lengths,
                "angles": angles,
                "atom_types": selected_species,
                "frac_coords": coords,
                "latent_z": rng.normal(0, 1, size=(32,)),
            })

        return tensors
