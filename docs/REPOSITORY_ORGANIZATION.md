# Repository Organization

This file is the navigation map for the active research workspace.

## Use These Entry Points

- `README.md`: high-level description of the full repository.
- `docs/PROJECT_OVERVIEW.md`: separation between control/NMR and transport tracks.
- `docs/APPLICATION_PRIORITIES_2026-04-24.md`: near-deadline application plan.
- `docs/transport_graph_lab.md`: quick start for the transport graph lab.
- `reports/famb_msc_transport_proposal/famb_msc_transport_proposal.pdf`: current MSc proposal.

## Active Source Modules

- `src/oqs_control/`: established open-system control/NMR layer.
- `src/oqs_transport/`: active transport-network layer.

## Active Scripts

Core transport runs:

- `scripts/run_transport_graph_lab.py`
- `scripts/run_transport_medium_campaign.py`
- `scripts/run_transport_graph_collection.py`
- `scripts/run_transport_phase_sweep.py`
- `scripts/run_transport_lab_master_pipeline.py`

Build/report scripts:

- `scripts/build_famb_msc_transport_proposal.py`
- `scripts/build_transport_medium_campaign_report.py`
- `scripts/build_transport_graph_collection_report.py`
- `scripts/build_open_quantum_transport_tutorial.py`
- `scripts/build_colab_open_quantum_transport_lab.py`

## Generated Reports Worth Keeping

- `reports/famb_msc_transport_proposal/`
- `reports/transport_medium_campaign_report/`
- `reports/transport_graph_collection_report/`
- `reports/open_quantum_transport_tutorial/`
- `reports/apostila_transporte_quantico_ptbr/`

## Temporary Files

Ignored or removable:

- `tests/_tmp*/`
- `__pycache__/`
- `.pytest_cache/`
- LaTeX auxiliaries such as `.aux`, `.log`, `.toc`, `.bbl`, `.blg`.

## Suggested Daily Workflow

1. Edit model/config/script.
2. Run one focused campaign.
3. Build or update the corresponding report.
4. Run the relevant tests.
5. Commit only the scientific unit that changed.

Do not let a campaign, a proposal edit and unrelated review-article changes sit
in the same commit.
