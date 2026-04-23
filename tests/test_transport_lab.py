from __future__ import annotations

import json
from pathlib import Path

import pytest

from oqs_transport import classify_transport_regime, load_transport_lab_config


def _local_tmp_path(filename: str) -> Path:
    tmp_dir = Path(__file__).resolve().parent / "_tmp_transport_lab"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / filename


def test_load_transport_lab_config_reads_expected_structure() -> None:
    config_path = _local_tmp_path("config.json")
    config_path.write_text(
        json.dumps(
            {
                "study_name": "Test transport lab",
                "output_subdir": "tmp_lab",
                "time_grid": {"t_final": 10.0, "n_samples": 200},
                "visualization": {"animation_stride": 7, "animation_fps": 9},
                "dephasing_rates_hz": [0.0, 0.5, 1.0],
                "scenarios": [
                    {
                        "name": "Chain",
                        "topology": "chain",
                        "n_sites": 4,
                        "coupling_hz": 1.0,
                        "sink_rate_hz": 0.5,
                        "loss_rate_hz": 0.0,
                        "initial_site": 3,
                        "trap_site": 0,
                        "disorder_strength_hz": 0.0,
                        "seed": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_transport_lab_config(config_path)

    assert config.study_name == "Test transport lab"
    assert config.output_subdir == "tmp_lab"
    assert config.n_time_samples == 200
    assert config.animation_stride == 7
    assert config.animation_fps == 9
    assert config.scenarios[0].topology == "chain"
    assert config.scenarios[0].n_sites == 4


def test_load_transport_lab_config_rejects_bad_topology() -> None:
    config_path = _local_tmp_path("bad_config.json")
    config_path.write_text(
        json.dumps(
            {
                "study_name": "Bad config",
                "output_subdir": "tmp_bad",
                "time_grid": {"t_final": 10.0, "n_samples": 200},
                "visualization": {"animation_stride": 7, "animation_fps": 9},
                "dephasing_rates_hz": [0.0, 0.5, 1.0],
                "scenarios": [
                    {
                        "name": "Bad",
                        "topology": "star",
                        "n_sites": 4,
                        "coupling_hz": 1.0,
                        "sink_rate_hz": 0.5,
                        "loss_rate_hz": 0.0,
                        "initial_site": 3,
                        "trap_site": 0,
                        "disorder_strength_hz": 0.0,
                        "seed": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported topology"):
        load_transport_lab_config(config_path)


def test_classify_transport_regime_behaviour() -> None:
    assert classify_transport_regime(0, 5) == "coherent"
    assert classify_transport_regime(4, 5) == "strongly_dissipative"
    assert classify_transport_regime(2, 5) == "intermediate"


def test_load_transport_lab_config_accepts_zero_sink_rate_for_learning_case() -> None:
    config_path = _local_tmp_path("zero_sink_config.json")
    config_path.write_text(
        json.dumps(
            {
                "study_name": "Zero sink config",
                "output_subdir": "tmp_zero_sink",
                "time_grid": {"t_final": 10.0, "n_samples": 200},
                "visualization": {"animation_stride": 5, "animation_fps": 8},
                "dephasing_rates_hz": [0.0],
                "scenarios": [
                    {
                        "name": "Coherent walk",
                        "topology": "chain",
                        "n_sites": 2,
                        "coupling_hz": 1.0,
                        "sink_rate_hz": 0.0,
                        "loss_rate_hz": 0.0,
                        "initial_site": 1,
                        "trap_site": 0,
                        "disorder_strength_hz": 0.0,
                        "seed": 1
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config = load_transport_lab_config(config_path)

    assert config.scenarios[0].sink_rate_hz == 0.0
