# Transport Lab Mac Handoff

This document is the handoff entry point for a Codex session running on the Mac.

## Mission

Use the Mac as a continuation node for:

- long-running transport campaigns;
- chunked atlas runs;
- registry/index refresh after heavy runs;
- report and notebook refresh after results land.

Do not treat chat memory as the source of truth. The repository files are the source of truth.

## Read First

Before doing anything substantial, read these files in this order:

1. `AGENTS.md`
2. `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`
3. `configs/transport_intense_campaign_plan.md`
4. `outputs/transport_networks/parameter_space_analysis/latest/parameter_space_report.md`
5. `outputs/transport_networks/paper_reproduction_suite/latest/paper_reproduction_report.md`
6. `docs/handoffs/workspace_repo_map.md`

## Current Scientific State

At the time this handoff was written:

- `paper_reproduction_suite` is a scientific-candidate campaign.
- `dynamic_network_atlas_evidence_prep` is a scientific-candidate campaign.
- `dynamic_network_atlas` is smoke-only and is not a scientific conclusion.
- `dynamic_network_atlas_intense` is prepared but may not have been executed yet.

Allowed claims and blocked claims must be read from:

- `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`

## Safe Bootstrap On The Mac

Run:

```bash
bash scripts/mac_transport_bootstrap.sh
```

That script:

- creates or reuses `.venv`;
- installs dependencies;
- runs only light validation;
- checks that the lab MCP server can read the latest registry/index;
- does not run heavy campaigns.

## Long-Run Workflow

For heavy work, use:

```bash
bash scripts/mac_transport_long_run.sh pilot
```

Available modes:

- `pilot`
  - first 10k records of the real intense profile;
- `random`
  - random families one by one;
- `deterministic`
  - deterministic and special families;
- `finalize`
  - rebuilds registry and MCP index after a run.

## 4 GB RAM Rule

This Mac has limited memory. Therefore:

- do not start the full intense profile in one shot;
- do not launch multiple heavy jobs at once;
- prefer chunked family-by-family runs;
- finalize registry/index after each meaningful chunk.

## Recommended First Heavy Step

Use the real intense profile, but only as a pilot:

```bash
bash scripts/mac_transport_long_run.sh pilot
```

After that, if the machine remains stable:

```bash
bash scripts/mac_transport_long_run.sh random
```

## When A Long Run Finishes

Always do:

```bash
bash scripts/mac_transport_long_run.sh finalize
```

Then inspect:

- `outputs/transport_networks/dynamic_network_atlas_intense/latest/summary.md`
- `outputs/transport_networks/lab_registry/latest/transport_lab_memory.md`
- `outputs/transport_networks/lab_registry/latest/master_critic_report.md`

## Git Discipline

Before pushing:

1. inspect `git status`;
2. confirm that the changed files belong to the campaign that was run;
3. avoid committing unrelated local noise;
4. push only after registry/index/report files are coherent.

## Handoff Back To Another Machine

The minimum clean handoff is:

- campaign output subtree updated;
- registry rebuilt;
- MCP index rebuilt;
- latest handoff state committed to Git.

That is enough for another Codex session to continue without chat history.
