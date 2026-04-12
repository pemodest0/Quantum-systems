from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np

from oqs_control.workflows.experimental_decision_pipeline import (
    WORKFLOW_ID,
    ExperimentalDecisionConfig,
    run_pipeline,
)


def small_config() -> ExperimentalDecisionConfig:
    return ExperimentalDecisionConfig(
        frequency_points=48,
        spectroscopy_cpmg_max=5,
        spectroscopy_udd_counts=(2,),
        candidate_cpmg_counts=(2, 4, 6),
        candidate_udd_counts=(2, 4),
        coherence_noise_std=0.0,
        qst_noise_std=0.0,
        qst_phase_error_rad=0.0,
        n_time_samples=160,
    )


def test_experimental_decision_pipeline_runs_with_physical_outputs() -> None:
    result = run_pipeline(config=small_config())

    assert result.workflow_id == WORKFLOW_ID
    assert result.state_preparation.fidelity > 0.999
    assert result.reconstruction.reconstructed_spectrum.shape == result.true_spectrum.shape
    assert np.all(result.reconstruction.reconstructed_spectrum >= -1e-12)
    assert 0.0 <= result.selected_sequence.predicted_coherence <= 1.0
    assert result.selected_sequence.sequence in {row.sequence for row in result.candidate_decisions}
    assert result.lab_comparison.status == "waiting_for_lab_data"


def test_experimental_decision_pipeline_compares_lab_manifest() -> None:
    baseline = run_pipeline(config=small_config())
    measured_sequence = baseline.selected_sequence
    manifest = {
        "schema_version": 1,
        "experiment_id": "synthetic_test",
        "coherence_measurements": [
            {
                "sequence": measured_sequence.sequence,
                "coherence": measured_sequence.predicted_coherence,
                "std": 0.01,
            }
        ],
    }
    tmp_root = Path("tests") / "_tmp_experimental_decision_pipeline"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True)
    manifest_path = tmp_root / "lab_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    compared = run_pipeline(config=small_config(), lab_manifest_path=manifest_path)

    assert compared.lab_comparison.status == "compared"
    assert compared.lab_comparison.matched_measurement_count == 1
    assert compared.lab_comparison.rmse is not None
    assert compared.lab_comparison.rmse < 1e-12
    shutil.rmtree(tmp_root)
