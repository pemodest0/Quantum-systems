# Quantum Transport Lab Agent Guide

This repository is the source of truth for the open quantum transport lab. Do not rely on chat memory when repository state is available.

## Mandatory startup sequence

Before doing anything substantial, read these files in this order:

1. `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`
2. `configs/transport_intense_campaign_plan.md`
3. `outputs/transport_networks/parameter_space_analysis/latest/parameter_space_report.md`
4. `outputs/transport_networks/paper_reproduction_suite/latest/paper_reproduction_report.md`
5. `docs/handoffs/transport_lab_mac_handoff.md`
6. `docs/handoffs/workspace_repo_map.md`

## Ground rules

- Treat repository files and generated outputs as the scientific source of truth.
- Do not claim that `dynamic_network_atlas` is scientific evidence; it is smoke-only unless a non-smoke profile is used.
- `dynamic_network_atlas_evidence_prep` and `paper_reproduction_suite` are current scientific-candidate outputs.
- `dynamic_network_atlas_intense` is prepared but may not be executed yet.
- Do not run `--profile intense` unless the user explicitly approves.

## Low-RAM machine rule

If the machine has around 4 GB of RAM:

- do not launch the full intense atlas;
- only inspect, validate, or run small chunked pilots;
- prefer `registry_only`, report reading, and lightweight tests first.

## Safe first actions on a fresh machine

1. Inspect project metadata and dependencies.
2. Run only light checks.
3. Summarize current lab state from the files above.
4. Propose the safest next chunk instead of starting a heavy campaign automatically.

## Mac handoff helpers

If the repository is opened on the Mac:

- use `bash scripts/mac_transport_bootstrap.sh` for lightweight setup;
- use `bash scripts/mac_transport_long_run.sh pilot` for the first real intense chunk;
- use `bash scripts/mac_transport_long_run.sh finalize` after any long run.

## Optional MCP usage

If an MCP bridge is available, use it only as an auxiliary read layer. The repository outputs still override chat context.
