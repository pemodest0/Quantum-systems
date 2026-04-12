from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import expm

from .hamiltonians import build_hbs, build_hoffset, build_hq1, build_hq2, build_hrf
from .operators import SpinOperators, spin_operators


@dataclass
class NMRConfig:
    i_spin: float = 1.5
    nu0: float = 105.7507331e6
    nu_q: float = 15625.0
    temperature_k: float = 273.15 + 28.0
    t_pi2: float = 4e-6
    t_tomo: float = 4.6e-6
    acquisition_delay: float = 5e-6
    evolution_time: float = 7e-6
    ringdown_delay: float = 10e-6
    dwell_time: float = 8e-6
    n_acq: int = 4096
    n_zf: int | None = None
    fi_pulse: float = 0.0
    fi_rx: float = -np.pi / 2.0

    hbar: float = 1.054571817e-34
    kb: float = 1.380649e-23

    decay_params: np.ndarray = field(
        default_factory=lambda: np.array(
            [
                [0.999896221029647, -312.541270167342, 0.000103778970353297, 0.0],
                [1.0, -165.166898029245, 0.0, -0.0739022476417014],
                [1.0, -335.932241593772, 0.0, -0.0739951014816252],
            ],
            dtype=float,
        )
    )

    dim: int = field(init=False)
    m_vals: np.ndarray = field(init=False)
    w0: float = field(init=False)
    wq: float = field(init=False)
    wp: float = field(init=False)
    nu_rf: float = field(init=False)
    t_evol_total: float = field(init=False)
    sw: float = field(init=False)
    freq: np.ndarray = field(init=False)
    delta_bs_hz: float = field(init=False)
    delta_bs_rad: float = field(init=False)
    operators: SpinOperators = field(init=False)
    i_plus: np.ndarray = field(init=False)
    i_minus: np.ndarray = field(init=False)
    i_x: np.ndarray = field(init=False)
    i_y: np.ndarray = field(init=False)
    i_z: np.ndarray = field(init=False)
    i_z2: np.ndarray = field(init=False)
    i_z3: np.ndarray = field(init=False)
    h_q1: np.ndarray = field(init=False)
    h_q2: np.ndarray = field(init=False)
    h_bs: np.ndarray = field(init=False)
    h_rf: np.ndarray = field(init=False)
    h_offset: np.ndarray = field(init=False)
    h_free: np.ndarray = field(init=False)
    h_pulse: np.ndarray = field(init=False)
    delta_offset_hz: float = field(init=False)
    rho_eq: np.ndarray = field(init=False)
    u_dwell: np.ndarray = field(init=False)
    u_dead: np.ndarray = field(init=False)
    u_pi2: np.ndarray = field(init=False)
    u_tomop: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        if self.n_zf is None:
            self.n_zf = self.n_acq

        self.dim = int(round(2 * self.i_spin + 1))
        self.m_vals = np.arange(self.i_spin, -self.i_spin - 1, -1, dtype=float)
        self.w0 = 2.0 * np.pi * self.nu0
        self.wq = 2.0 * np.pi * self.nu_q
        self.wp = (np.pi / 2.0) / self.t_pi2
        self.nu_rf = self.wp / (2.0 * np.pi)
        self.t_evol_total = (
            self.evolution_time + self.acquisition_delay + self.ringdown_delay
        )
        self.sw = 1.0 / self.dwell_time
        self.freq = np.fft.fftshift(np.fft.fftfreq(self.n_zf, d=self.dwell_time))
        self.delta_bs_hz = self.nu_rf**2 / (4.0 * self.nu0)
        self.delta_bs_rad = 2.0 * np.pi * self.delta_bs_hz

        self.operators = spin_operators(self.i_spin)
        self.i_plus = self.operators.i_plus
        self.i_minus = self.operators.i_minus
        self.i_x = self.operators.i_x
        self.i_y = self.operators.i_y
        self.i_z = self.operators.i_z
        self.i_z2 = self.operators.i_z2
        self.i_z3 = self.operators.i_z3

        self.h_q1 = build_hq1(self.i_spin, self.dim, self.wq, self.i_z2)
        self.h_q2 = build_hq2(self.wq, self.w0, self.i_z, self.i_z3)
        self.h_bs = build_hbs(self.delta_bs_rad, self.i_z)
        self.h_rf = build_hrf(self.wp, self.i_x, self.i_y, self.fi_pulse)
        h_free_unshifted = self.h_q1 + self.h_q2
        e_free = np.diag(h_free_unshifted)
        self.delta_offset_hz = -(e_free[1] - e_free[2]).real / (2.0 * np.pi)
        self.h_offset = build_hoffset(self.delta_offset_hz, self.i_z)
        self.h_free = h_free_unshifted + self.h_offset
        self.h_pulse = self.h_free + self.h_bs

        eps_th = self.hbar * self.w0 / (self.kb * self.temperature_k)
        self.rho_eq = np.eye(self.dim, dtype=complex) / self.dim
        self.rho_eq = self.rho_eq + eps_th * self.i_z / self.dim

        self.u_dwell = expm(-1j * self.h_free * self.dwell_time)
        self.u_dead = expm(-1j * self.h_free * self.t_evol_total)
        hp_pi2 = build_hrf(self.wp, self.i_x, self.i_y, self.fi_pulse)
        self.u_pi2 = expm(-1j * (hp_pi2 + self.h_pulse) * self.t_pi2)

        self.u_tomop = np.zeros((self.dim, self.dim, 7), dtype=complex)
        for k in range(7):
            phase = k * 2.0 * np.pi / 7.0
            hp_k = build_hrf(self.wp, self.i_x, self.i_y, phase)
            self.u_tomop[:, :, k] = expm(-1j * (hp_k + self.h_pulse) * self.t_tomo)

    @property
    def transition_pairs(self) -> tuple[tuple[int, int], ...]:
        # [SAT-, CT, SAT+]
        return ((2, 3), (1, 2), (0, 1))

    @property
    def detector(self) -> np.ndarray:
        return np.exp(-1j * self.fi_rx) * (self.i_x + 1j * self.i_y)

    @property
    def transition_labels(self) -> tuple[str, ...]:
        return ("SAT-", "CT", "SAT+")

    @property
    def expected_transition_centers_hz(self) -> np.ndarray:
        return np.array([-self.nu_q, 0.0, self.nu_q], dtype=float)

    def clone_with(self, **overrides: object) -> "NMRConfig":
        params = {
            "i_spin": self.i_spin,
            "nu0": self.nu0,
            "nu_q": self.nu_q,
            "temperature_k": self.temperature_k,
            "t_pi2": self.t_pi2,
            "t_tomo": self.t_tomo,
            "acquisition_delay": self.acquisition_delay,
            "evolution_time": self.evolution_time,
            "ringdown_delay": self.ringdown_delay,
            "dwell_time": self.dwell_time,
            "n_acq": self.n_acq,
            "n_zf": self.n_zf,
            "fi_pulse": self.fi_pulse,
            "fi_rx": self.fi_rx,
            "hbar": self.hbar,
            "kb": self.kb,
            "decay_params": np.array(self.decay_params, copy=True),
        }
        params.update(overrides)
        return NMRConfig(**params)
