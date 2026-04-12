from __future__ import annotations

import numpy as np


def build_hq1(spin: float, dim: int, wq: float, iz2: np.ndarray) -> np.ndarray:
    identity = np.eye(dim, dtype=complex)
    return (wq / 6.0) * (3.0 * iz2 - spin * (spin + 1.0) * identity)


def build_hq2(wq: float, w0: float, iz: np.ndarray, iz3: np.ndarray) -> np.ndarray:
    if w0 == 0:
        raise ValueError("w0 must be non-zero")
    # Effective second-order high-field correction for I = 3/2.
    coeff = (wq**2) / (16.0 * w0)
    return coeff * (iz3 - 1.25 * iz)


def build_hbs(delta_bs_rad: float, iz: np.ndarray) -> np.ndarray:
    # MATLAB comments indicate the correct sign is negative in this frame.
    return -delta_bs_rad * iz


def build_hrf(wp: float, ix: np.ndarray, iy: np.ndarray, phase: float) -> np.ndarray:
    return wp * (np.cos(phase) * ix + np.sin(phase) * iy)


def build_hoffset(delta_offset_hz: float, iz: np.ndarray) -> np.ndarray:
    return 2.0 * np.pi * delta_offset_hz * iz
