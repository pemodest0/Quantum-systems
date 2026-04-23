# Transport Outputs

This directory stores generated outputs for the open quantum transport track.

## Read This First

Do not begin from a random campaign folder.

Start from:

- `lab_registry/latest/`
- `mcp_index/latest/`

These two folders tell you:

- what the current scientific state is;
- which claims are allowed;
- which campaigns are exploratory or smoke-only;
- where the newest relevant figures and reports live.

## High-Value Subtrees

- `lab_registry/latest/`
  - merged scientific state and critic layer;
- `mcp_index/latest/`
  - machine-readable read-only index for assistants and tools;
- `paper_reproduction_suite/latest/`
  - paper-by-paper validation and guardrails;
- `research_journey_v2/latest/`
  - current central story of the transport project;
- `dynamic_network_atlas_evidence_prep/latest/`
  - current non-smoke atlas-like campaign;
- `parameter_space_analysis/latest/`
  - cost/combinatorics analysis;
- `dynamic_network_atlas_intense/latest/`
  - destination for the long heavy campaign.

## Low-Priority Or Historical Subtrees

- `dynamic_network_atlas/latest/`
  - smoke-only;
- older `graph_lab*`, `phase_sweep`, `learning_step*`
  - useful as history, not as the current source of truth.

## Rule

If a folder is not reflected in `lab_registry/latest/transport_lab_memory.md`,
it is not the best place to start explaining the current scientific state.
