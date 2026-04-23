<p align="center">
 
</p>

# Quantum Systems

Python-first laboratory for open quantum systems with two active research
tracks kept in the same repository:

- open quantum control / NMR / tomography / noise spectroscopy;
- open quantum transport on finite networks.

The repository started from a Na-23 quadrupolar NMR workflow and grew into a
broader reproducible research lab in Python. MATLAB is not part of the active
workflow.

## Two Research Tracks

## Track A: Open Quantum Control And NMR

Theme:

**Control and identification of dissipative dynamics in open quantum systems:
a statistical-physics approach with experimental validation.**

Main components:

- spin-3/2 Na-23 NMR modeling;
- FID and spectrum simulation;
- quadrupolar relaxation benchmarks;
- quantum state tomography;
- selective-pulse and GRAPE control;
- dynamical-decoupling filtering;
- noise spectroscopy;
- quantum process tomography;
- gate-set tomography;
- process-tensor memory diagnostics;
- a single experimental decision pipeline for future lab data.

Key paths:

```text
src/oqs_control/
docs/papers/
outputs/repro/
outputs/workflows/
reports/review_article/
```

## Track B: Open Quantum Transport

Theme:

**Transport of a single excitation on finite open quantum networks with
topology, disorder, dephasing, loss, and target arrival as central variables.**

Main components:

- finite graph and medium models;
- open-transport simulation with sink/loss;
- target-position campaigns;
- quantum-versus-classical control;
- classification of network families by dynamic signatures;
- paper-by-paper reproduction guardrails;
- registry, MCP index, and handoff layer for long-running campaigns.

Key paths:

```text
src/oqs_transport/
configs/transport_*.json
scripts/run_transport_*.py
outputs/transport_networks/
reports/famb_msc_transport_proposal/
```

## Repository Structure

```text
src/oqs_control/                         open-quantum-control and NMR layer
src/oqs_transport/                       transport-network simulation and campaign layer
scripts/                                 one-command runs and build utilities
tests/                                   regression tests for both tracks
docs/PROJECT_OVERVIEW.md                 clean separation between the two tracks
docs/REPOSITORY_ORGANIZATION.md          navigation map for the repo
docs/TRANSPORT_RESEARCH_DATA_MAP.md      where the transport outputs actually live
outputs/repro/                           control/NMR paper artifacts
outputs/workflows/                       control/NMR workflow artifacts
outputs/transport_networks/              transport campaigns, registries, reports, indices
reports/review_article/                  control/NMR review-style PDF and source
reports/famb_msc_transport_proposal/     current transport proposal
```

## Fast Entry Points

If you are working on control/NMR:

```text
docs/LAB_MANUAL.md
docs/papers/
GUIDE.md
```

If you are working on transport:

```text
docs/PROJECT_OVERVIEW.md
docs/REPOSITORY_ORGANIZATION.md
docs/TRANSPORT_RESEARCH_DATA_MAP.md
outputs/transport_networks/lab_registry/latest/transport_lab_memory.md
```

## Quick Start

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the full test suite:

```powershell
python -m pytest -q
```

Run a transport-side light check:

```powershell
python scripts\analyze_transport_parameter_space.py
python scripts\run_transport_lab_mcp_server.py --check
```

Run a transport campaign:

```powershell
python scripts\run_transport_dynamic_network_atlas.py --profile evidence_prep
```

Run the control/NMR experimental decision pipeline:

```powershell
python scripts\run_experimental_decision_pipeline.py
```

## Main Documents

```text
docs/LAB_MANUAL.md
docs/PROJECT_OVERVIEW.md
docs/REPOSITORY_ORGANIZATION.md
docs/TRANSPORT_RESEARCH_DATA_MAP.md
docs/papers/
reports/review_article/open_quantum_control_review.pdf
reports/review_article/open_quantum_control_review.tex
reports/famb_msc_transport_proposal/famb_msc_transport_proposal.pdf
GUIDE.md
```

## Transport Source Of Truth

For transport research, the source of truth is not the chat. It is:

```text
outputs/transport_networks/lab_registry/latest/
outputs/transport_networks/mcp_index/latest/
outputs/transport_networks/paper_reproduction_suite/latest/
outputs/transport_networks/dynamic_network_atlas_evidence_prep/latest/
```

## Current Reproduced Research Stack

The repository includes compact notes and reproducible artifacts for:

- Na-23 relaxometry and quadrupolar relaxation;
- spin-3/2 algebraic NMR dynamics;
- relaxation dynamics by quantum state tomography;
- spin-3/2 logical operations monitored by QST;
- non-Markovian noise diagnostics;
- multipass quantum process tomography;
- quadrupolar NMR quantum information processing;
- GRAPE NMR optimal control;
- pseudo-pure state preparation by optimal control;
- projected least-squares QPT;
- gate-set tomography;
- process-tensor characterization and control;
- dynamical-decoupling noise filtering;
- DD noise spectroscopy;
- flux-qubit-like noise spectroscopy.

## Scientific Status

Validated:

- spin-3/2 operator algebra;
- Na-23 Hamiltonian and transition structure;
- synthetic FID/spectrum generation;
- synthetic QST reconstruction;
- synthetic dissipative-rate recovery;
- paper-reproduction metrics and figures;
- experimental-decision workflow under synthetic data.

Not yet claimed:

- microscopic identification from a single real FID;
- final T1/T2 relaxometry on real data;
- full experimental seven-phase tomography;
- hardware-level calibration of SPAM/readout/pulse errors;
- experimental optimality of any selected control sequence.

## License

MIT License. See `LICENSE`.
