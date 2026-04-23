from __future__ import annotations

import numpy as np

from oqs_transport.visual_journey import VisualCaseSpec, _row_col_to_case


def test_row_col_to_case_maps_axes_correctly() -> None:
    payload = {
        "scenario_name": "Test medium",
        "disorder_strength_over_coupling": [0.0, 0.4, 0.8],
        "dephasing_over_coupling": [0.0, 0.1, 0.2],
        "efficiency_mean": [
            [0.7, 0.6, 0.4],
            [0.5, 0.45, 0.35],
            [0.3, 0.28, 0.2],
        ],
    }
    case_spec = _row_col_to_case(
        payload=payload,
        label="best",
        row=0,
        col=1,
        representative_seed=5,
        representative_efficiency=0.61,
        std_efficiency=0.02,
    )

    assert isinstance(case_spec, VisualCaseSpec)
    assert case_spec.scenario_name == "Test medium"
    assert np.isclose(case_spec.disorder_over_coupling, 0.0)
    assert np.isclose(case_spec.dephasing_over_coupling, 0.1)
    assert case_spec.representative_seed == 5
    assert np.isclose(case_spec.ensemble_mean_efficiency, 0.6)
