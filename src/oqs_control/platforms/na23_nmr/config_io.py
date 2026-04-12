from __future__ import annotations

import json
from pathlib import Path

from .config import NMRConfig


def config_to_dict(config: NMRConfig) -> dict[str, object]:
    return {
        "i_spin": config.i_spin,
        "nu0_hz": config.nu0,
        "nu_q_hz": config.nu_q,
        "temperature_k": config.temperature_k,
        "t_pi2_s": config.t_pi2,
        "t_tomo_s": config.t_tomo,
        "acquisition_delay_s": config.acquisition_delay,
        "evolution_time_s": config.evolution_time,
        "ringdown_delay_s": config.ringdown_delay,
        "dwell_time_s": config.dwell_time,
        "n_acq": config.n_acq,
        "n_zf": config.n_zf,
        "fi_pulse_rad": config.fi_pulse,
        "fi_rx_rad": config.fi_rx,
        "delta_bs_hz": config.delta_bs_hz,
        "delta_offset_hz": config.delta_offset_hz,
        "transition_labels": list(config.transition_labels),
        "expected_transition_centers_hz": config.expected_transition_centers_hz.tolist(),
        "decay_params": config.decay_params.tolist(),
    }


def save_config_json(config: NMRConfig, path: str | Path) -> Path:
    target = Path(path)
    target.write_text(
        json.dumps(config_to_dict(config), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target
