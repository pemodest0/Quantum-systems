# Transport Research Data Map

This file is the data/navigation map for the transport side of the repository.

The main problem it solves is simple:

there are many campaign folders in `outputs/transport_networks/`, but only a
small subset should be treated as the current scientific source of truth.

## First Rule

For transport research, the current source of truth is:

1. `outputs/transport_networks/lab_registry/latest/`
2. `outputs/transport_networks/mcp_index/latest/`
3. the latest outputs of the specific campaign being discussed

Do not start from random old folders when the registry already summarizes them.

## Current High-Value Paths

## 1. Master Registry

```text
outputs/transport_networks/lab_registry/latest/
```

Use this first. It contains:

- `transport_lab_memory.md`
  - current state, allowed claims, blocked claims, next action;
- `master_results.csv`
  - merged results table;
- `master_uncertainty.csv`
  - CI95 and uncertainty aggregates;
- `master_claims.json`
  - allowed and blocked claims;
- `master_critic_report.md`
  - what the lab currently allows you to say.

## 2. MCP Index

```text
outputs/transport_networks/mcp_index/latest/
```

Use this as the organized read-only layer for agents and assistants. It mirrors
registry conclusions in a cleaner machine-readable form.

## 3. Paper Reproduction Suite

```text
outputs/transport_networks/paper_reproduction_suite/latest/
```

Use this when the question is:

- “does this agree with the literature?”
- “what papers are already reproduced?”
- “which claims are matched, inconclusive or not applicable?”

Important files:

- `paper_reproduction_report.md`
- `paper_reproduction_table.csv`
- `paper_verdicts.json`
- `paper_suite_metrics.json`

## 4. Research Journey V2

```text
outputs/transport_networks/research_journey_v2/latest/
```

Use this when the question is:

- “what is the central physics story right now?”
- “how strong is the target-position effect?”
- “how does quantum compare with classical in the current integrated story?”

Important files:

- `summary.md`
- `metrics.json`

## 5. Dynamic Atlas: Evidence Prep

```text
outputs/transport_networks/dynamic_network_atlas_evidence_prep/latest/
```

This is the current non-smoke atlas-like campaign. It is much more important
than `dynamic_network_atlas/latest`, which is smoke-only.

Important files:

- `atlas_records.csv`
- `atlas_summary_by_family.csv`
- `atlas_summary_by_target.csv`
- `quantum_classical_delta.csv`
- `atlas_metrics.json`
- `summary.md`

## 6. Dynamic Atlas: Smoke

```text
outputs/transport_networks/dynamic_network_atlas/latest/
```

Treat this as plumbing validation only.

It shows that the pipeline works. It is **not** a scientific conclusion.

## 7. Dynamic Atlas: Intense

```text
outputs/transport_networks/dynamic_network_atlas_intense/latest/
```

This folder is the destination for the long Mac/overnight campaign. It may
exist as a target path before the campaign is actually completed.

Do not infer results from it unless the run has actually happened and the
registry has been rebuilt.

## 8. Parameter-Space Analysis

```text
outputs/transport_networks/parameter_space_analysis/latest/
```

Use this when the question is:

- “why is the campaign expensive?”
- “where does combinatorics explode?”
- “which families dominate runtime?”

Important files:

- `parameter_space_report.md`
- `parameter_cost_summary.csv`
- `family_cost_breakdown.csv`

## 9. Target/Geometry Follow-Up

```text
outputs/transport_networks/target_geometry_confirm/latest/
```

Use this for the controlled target-position story.

## 10. Fractal Exploratory Front

```text
outputs/transport_networks/fractal_geometry_followup/latest/
```

Use this only as an exploratory geometry front. Do not treat it as the core
claim of the project.

## How To Read The Folder Tree

Inside `outputs/transport_networks/`, the folders roughly split into:

- `lab_registry`, `mcp_index`, `master_scientific_report`
  - global summary layer;
- `paper_reproduction_suite`, `scientific_validation`, `network_classification_complete`
  - methodological and literature-facing layer;
- `research_journey_v2`, `target_geometry_confirm`, `fractal_geometry_followup`
  - story-building layer;
- `dynamic_network_atlas*`
  - atlas and scaling layer;
- older graph/phase/learning folders
  - useful history, but not the first place to start.

## Recommended Reading Order For Humans

If you want to understand the transport project quickly:

1. `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`
2. `outputs/transport_networks/master_scientific_report/latest/master_report.md`
3. `outputs/transport_networks/research_journey_v2/latest/summary.md`
4. `outputs/transport_networks/paper_reproduction_suite/latest/paper_reproduction_report.md`
5. `outputs/transport_networks/dynamic_network_atlas_evidence_prep/latest/summary.md`

## Recommended Reading Order For Agents

If you are an agent starting a session:

1. `AGENTS.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/REPOSITORY_ORGANIZATION.md`
4. `docs/TRANSPORT_RESEARCH_DATA_MAP.md`
5. `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`

## What To Ignore First

Do not start from:

- random old `graph_lab*` folders;
- smoke outputs;
- temporary learning-step folders;
- isolated PNGs without registry context.

Those can still be useful, but they are not the right entry point for the
current scientific state.
