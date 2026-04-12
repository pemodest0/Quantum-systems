from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SpinOperators:
    spin: float
    m_values: np.ndarray
    i_plus: np.ndarray
    i_minus: np.ndarray
    i_x: np.ndarray
    i_y: np.ndarray
    i_z: np.ndarray
    i_z2: np.ndarray
    i_z3: np.ndarray


def spin_operators(spin: float) -> SpinOperators:
    m_values = np.arange(spin, -spin - 1, -1, dtype=float)
    dim = int(round(2 * spin + 1))
    aux = spin * (spin + 1)
    i_plus = np.zeros((dim, dim), dtype=complex)

    for idx in range(1, dim):
        i_plus[idx - 1, idx] = np.sqrt(aux - m_values[idx - 1] * m_values[idx])

    i_minus = i_plus.conj().T
    i_x = 0.5 * (i_plus + i_minus)
    i_y = (i_plus - i_minus) / (2j)
    i_z = 0.5 * (i_plus @ i_minus - i_minus @ i_plus)
    i_z2 = i_z @ i_z
    i_z3 = i_z2 @ i_z

    return SpinOperators(
        spin=spin,
        m_values=m_values,
        i_plus=i_plus,
        i_minus=i_minus,
        i_x=i_x,
        i_y=i_y,
        i_z=i_z,
        i_z2=i_z2,
        i_z3=i_z3,
    )
