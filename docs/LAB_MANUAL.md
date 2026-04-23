# Open Quantum Control Lab Manual

This is the canonical compact documentation file for the Python-first lab.
Old planning notes and duplicate result Markdown files were intentionally removed.

## Goal

Build a reproducible laboratory for control and identification of dissipative dynamics in open quantum systems, starting from spin-3/2 Na-23 NMR and extending toward hardware characterization.

## Canonical Reading Order

1. `README.md` for quick start.
2. `docs/LAB_MANUAL.md` for the lab structure and validation rules.
3. `docs/papers/` for one Markdown file per reproduced paper/workflow, each with figure-by-figure commentary and references.
4. `reports/review_article/open_quantum_control_review.pdf` for the full review-style report with plots.

## Repository Roles

- `src/oqs_control/`: validated code.
- `scripts/`: one-command runs and build utilities.
- `outputs/repro/`: JSON/PNG artifacts from paper reproductions.
- `outputs/workflows/`: JSON/PNG artifacts from operational workflows.
- `docs/papers/`: one Markdown file per paper/workflow with a detailed figure guide.
- `reports/review_article/`: publication-style LaTeX/PDF report.
- `lab/research_memory/`: generated research memory.

## Validation Policy

- Synthetic validation tests the machinery.
- Diagnostic real-data fits are not final physical identification.
- Microscopic dissipative mechanisms require multiple calibrated datasets.
- New lab data must include metadata, uncertainty, and a manifest.

## Current Base Simulation Metrics

- `Open-system max trace error`: `3.5527e-15` - Trace preservation under dense Liouvillian propagation.
- `Open-system max Hermiticity error`: `1.0121e-17` - Numerical Hermiticity preservation.
- `Open-system minimum eigenvalue`: `0.249994` - Positivity floor for the tested trajectory.
- `Synthetic fitted gamma_phi`: `210` - Noise-free recovery of dephasing rate.
- `Synthetic fitted gamma_relax`: `55` - Noise-free recovery of relaxation rate.
- `Validation-suite success count`: `9` - Number of synthetic robustness cases that converged.
- `Validation-suite median gamma_phi relative error`: `0.0178259` - Typical dephasing-rate recovery error under tested noise.
- `Validation-suite median gamma_relax relative error`: `0.0288546` - Typical relaxation-rate recovery error under tested noise.
- `Reference-fit normalized FID RMSE`: `0.13601` - Diagnostic mismatch against the current real TNT reference FID.
- `Reference-fit gamma_phi`: `467.884` - Effective transverse decay from one-FID diagnostic fit.
- `Reference-fit gamma_relax`: `2.0656e-05` - Not interpretable as final T1 identification from one FID.
- `Tomography-pipeline fidelity`: `1` - Synthetic QST reconstruction fidelity.
- `Tomography-pipeline residual norm`: `7.4720e-13` - Linear tomography residual.
- `Open-qubit final purity`: `0.634231` - Generic two-level dissipative demonstration.
- `Open-qubit final entropy`: `0.552153` - Entropy after open-qubit evolution.

## Base Artifact Inventory

- `outputs/nmr_open_simulation.json` [present, sha256 prefix `98d6eea7e342f312`] - Physical trace/Hermiticity/positivity checks for dense Liouvillian propagation.
- `outputs/nmr_open_simulation.png` [present, sha256 prefix `7c39da7b406abec7`] - Visual artifact for the open-system Na-23 simulation.
- `outputs/nmr_synthetic_dissipation_fit.json` [present, sha256 prefix `1933b813b07e2a7e`] - Synthetic parameter-recovery validation for gamma_phi and gamma_relax.
- `outputs/nmr_synthetic_dissipation_fit.png` [present, sha256 prefix `b028a93e88c27e84`] - Visual comparison for the synthetic dissipation fit.
- `outputs/nmr_validation_suite.json` [present, sha256 prefix `ba7e65f29b1ded08`] - Noise robustness sweep for dissipation-rate recovery.
- `outputs/nmr_validation_suite.png` [present, sha256 prefix `a9c351f432f8d64c`] - Visual summary of robustness versus synthetic noise.
- `outputs/nmr_reference_dissipation_fit.json` [present, sha256 prefix `7c2180e4bc4e9dff`] - Diagnostic fit against the current real reference TNT FID.
- `outputs/nmr_reference_dissipation_fit.png` [present, sha256 prefix `08d95e2034b16bce`] - Visual comparison for the diagnostic reference-data fit.
- `outputs/nmr_tomography_pipeline.json` [present, sha256 prefix `12d79fdfd39e1009`] - Synthetic tomography extraction and reconstruction validation.
- `outputs/nmr_tomography_pipeline.png` [present, sha256 prefix `27970e319144bec1`] - Visual tomography-pipeline artifact.
- `outputs/open_qubit_demo.json` [present, sha256 prefix `3307acb991d748cf`] - Generic open-system qubit thermodynamic/dissipative demonstration.
- `outputs/open_qubit_demo.png` [present, sha256 prefix `358035dea135f7b5`] - Visual open-qubit demo artifact.
- `docs/LAB_MANUAL.md` [present, sha256 prefix `89b8d1559141f308`] - Canonical human-readable description of the laboratory, validation policy, and experimental workflow.
- `repro/paper_registry.yaml` [present, sha256 prefix `5ef49d02c19d3f54`] - Canonical list of reproduced papers and internal baselines.
- `repro/repro_manifest.yaml` [present, sha256 prefix `fefe51555c21959b`] - Machine-readable reproduction manifest.
- `lab/research_memory/SUMMARY.md` [present, sha256 prefix `ba5f0dfaa1cbcefb`] - Generated memory of completed paper/workflow artifacts.
- `lab/research_memory/index.json` [present, sha256 prefix `53772e918b3971e6`] - Compact index of reproducible records.
- `requirements.lock.txt` [present, sha256 prefix `5d17a85f248588f5`] - Pinned Python dependency baseline.
- `pyproject.toml` [present, sha256 prefix `cf6a69c9cdcb6257`] - Package and test configuration.

## Paper And Workflow Notes

- `Internal Baseline`: `docs/papers/internal_validation_baseline.md` - Internal spin-3/2 Na-23 validation baseline
- `Paper A`: `docs/papers/na23_relaxometry_2023.md` - 23Na relaxometry: theory and applications
- `Paper B`: `docs/papers/spin32_algebraic_2004.md` - Algebraic description of spin 3/2 dynamics in NMR
- `Paper C`: `docs/papers/qst_relaxation_2008.md` - Relaxation dynamics in a quadrupolar NMR system using QST
- `Paper D`: `docs/papers/spin32_qlogic_qst_2005.md` - Spin-3/2 quantum logical operations monitored by QST
- `Paper E`: `docs/papers/nonmarkov_noise_2022.md` - Characterization and control of non-Markovian quantum noise
- `Paper F`: `docs/papers/multipass_qpt_2024.md` - Multipass quantum process tomography
- `Paper G`: `docs/papers/quadrupolar_qip_2012.md` - Quadrupolar nuclei for NMR quantum information processing
- `Paper H`: `docs/papers/grape_nmr_control_2005.md` - GRAPE NMR optimal control
- `Paper I`: `docs/papers/pps_optimal_control_2012.md` - Pseudo-pure states in a quadrupolar spin system
- `Paper J`: `docs/papers/projected_ls_qpt_2022.md` - Projected least-squares QPT
- `Paper K`: `docs/papers/gate_set_tomography_2021.md` - Gate set tomography
- `Paper L`: `docs/papers/nonmarkov_process_tensor_2020.md` - Non-Markovian process tensor characterization and control
- `Paper M`: `docs/papers/noise_filtering_control_2014.md` - Experimental noise filtering by quantum control
- `Paper N`: `docs/papers/dd_noise_spectroscopy_2011.md` - Colored-noise spectroscopy by dynamical decoupling
- `Paper O`: `docs/papers/flux_qubit_noise_spectroscopy_2011.md` - Flux-qubit noise spectroscopy through DD
- `Workflow`: `docs/papers/experimental_decision_pipeline.md` - Experimental decision pipeline

## Main Commands

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
python scripts\run_experimental_decision_pipeline.py
python scripts\research_memory_agent.py
python scripts\build_review_article.py
```

## Incoming Lab Data Rule

Use the generated lab manifest from the experimental decision pipeline. If measured coherences or QST observables disagree with the model outside uncertainty, escalate the model instead of forcing a fit.
