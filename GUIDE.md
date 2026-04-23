# Quantum Systems Guide

This guide explains how to work with the repository without reopening the old
documentation sprawl.

This repository has two active tracks:

- control / NMR / tomography / noise spectroscopy;
- transport on finite open quantum networks.

If you are working on transport, also read:

```text
docs/PROJECT_OVERVIEW.md
docs/REPOSITORY_ORGANIZATION.md
docs/TRANSPORT_RESEARCH_DATA_MAP.md
outputs/transport_networks/lab_registry/latest/transport_lab_memory.md
```

## 1. Environment

Use Python 3.10 or newer.

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH='src'
```

For editable package usage:

```powershell
python -m pip install -e .
```

## 2. Validate The Lab

Run the full test suite:

```powershell
$env:PYTHONPATH='src'
python -m pytest -q
```

The tests check spin-3/2 operators, Hamiltonians, Liouvillian consistency,
spectra, tomography, relaxation models, noise filtering, noise spectroscopy,
QPT, GST, process tensors, GRAPE control, and research-memory generation.

Transport-side quick checks:

```powershell
python scripts\analyze_transport_parameter_space.py
python scripts\run_transport_lab_mcp_server.py --check
```

## 3. Run A Paper Reproduction

List available reproductions:

```powershell
$env:PYTHONPATH='src'
python scripts\run_repro.py --list
```

Run one paper:

```powershell
$env:PYTHONPATH='src'
python scripts\run_repro.py --paper-id na23_relaxometry_2023
```

Outputs are written to:

```text
outputs/repro/<paper_id>/latest/
```

Each reproduction stores machine-readable artifacts:

```text
config_used.json
metrics.json
results.json
run_metadata.json
figures/
```

## 4. Run The Experimental Decision Pipeline

```powershell
$env:PYTHONPATH='src'
python scripts\run_experimental_decision_pipeline.py
```

Outputs:

```text
outputs/workflows/experimental_decision_pipeline/latest/
```

The pipeline does:

1. prepare a synthetic spin-3/2 state;
2. validate it with QST;
3. simulate or ingest DD coherence measurements;
4. reconstruct an effective noise spectrum;
5. choose a control sequence;
6. prepare comparison hooks for real lab data.

## 5. Add Real Lab Data

Use the generated manifest template:

```text
outputs/workflows/experimental_decision_pipeline/latest/lab_manifest_template.json
```

Then run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_experimental_decision_pipeline.py --lab-manifest path\to\lab_manifest.json
```

Rule: if the real measurements disagree with the model outside uncertainty,
escalate the model. Do not force a fit.

## 6. Read The Research

Compact documentation:

```text
docs/LAB_MANUAL.md
docs/papers/
```

Full review report:

```text
reports/review_article/open_quantum_control_review.pdf
reports/review_article/open_quantum_control_review.tex
```

Transport-side research entry points:

```text
docs/TRANSPORT_RESEARCH_DATA_MAP.md
docs/handoffs/transport_research_scope_ptbr.md
docs/handoffs/transport_professor_conversation_ptbr.md
outputs/transport_networks/master_scientific_report/latest/master_report.md
outputs/transport_networks/paper_reproduction_suite/latest/paper_reproduction_report.md
```

Rebuild the report:

```powershell
python scripts\build_review_article.py
```

This build also refreshes the detailed figure annotations and reference-aware
paper notes before compiling the PDF.

## 7. Research Memory

Update the local memory index:

```powershell
$env:PYTHONPATH='src'
python scripts\research_memory_agent.py
```

Output:

```text
lab/research_memory/
```

This records paper/workflow artifacts, hashes, metrics, and summaries.

## 8. What Not To Do

- Do not infer microscopic relaxation from a single FID.
- Do not trust ideal pulses when quadrupolar evolution is active during the pulse.
- Do not compare gate matrices from GST without considering gauge freedom.
- Do not claim a Markovian model if echo or multi-time data show memory.
- Do not add new scattered Markdown notes; update `docs/LAB_MANUAL.md`, one
  file in `docs/papers/`, or the LaTeX review report.
