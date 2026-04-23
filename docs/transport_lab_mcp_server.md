# Transport Lab MCP Research Hub

This module exposes the open-quantum transport laboratory as a read-only MCP server for research assistants.

The MCP server reads a normalized index first:

```text
outputs/transport_networks/mcp_index/latest/
```

If the index is missing, it falls back to:

```text
outputs/transport_networks/lab_registry/latest/
```

## Build The MCP Index

Run this whenever campaign outputs or the master registry change:

```powershell
python scripts\build_transport_lab_mcp_index.py
```

The builder creates:

- `index.json`
- `campaigns.json`
- `metric_summaries.json`
- `entropy_summary.json`
- `quantum_classical_summary.json`
- `claims.json`
- `paper_guardrails.json`
- `figures.json`
- `notebooks.json`
- `reports.json`

## Tools

The server exposes only read-only tools:

- `get_lab_status`
- `list_campaigns`
- `get_campaign_summary`
- `get_campaign`
- `get_campaign_metrics`
- `get_lab_memory`
- `get_claims`
- `get_critic_report`
- `compare_families`
- `summarize_entropy`
- `quantum_classical_summary`
- `get_paper_guardrails`
- `list_figures`
- `list_notebooks`
- `list_reports`
- `read_campaign_file`
- `suggest_next_campaign`

Resources:

- `transport-lab://status`
- `transport-lab://memory`
- `transport-lab://campaigns`
- `transport-lab://claims`
- `transport-lab://notebooks`

## Safety Contract

- Read-only only.
- No simulation execution.
- No config editing.
- No arbitrary file reads outside campaign output directories.
- Claims are derived from `lab_registry/latest`; the MCP index is only an organized view.
- Entropy is reported as graph-normalized von Neumann entropy and must not be treated as target-arrival success by itself.

## Local Check

This does not require the `mcp` Python package:

```powershell
python scripts\run_transport_lab_mcp_server.py --check
```

The check should report `data_source: mcp_index` after the index has been built.

## Running As An MCP Server

Install the Python MCP package in the environment that will host the server, then run:

```powershell
python scripts\run_transport_lab_mcp_server.py --transport stdio
```

Codex-compatible MCP client configuration:

```json
{
  "mcpServers": {
    "transport-lab": {
      "command": "python",
      "args": [
        "scripts/run_transport_lab_mcp_server.py",
        "--transport",
        "stdio"
      ],
      "cwd": "C:/Users/Pedro Henrique/Downloads/Assyntrax-main/repos/Quantum-systems"
    }
  }
}
```

## Intended Use

Use this server for questions like:

- Which campaigns are scientific candidates?
- Which graph families have higher von Neumann entropy?
- Where does the open-quantum model beat the classical control?
- Which claims are currently allowed or blocked?
- Which figures or notebooks should be opened for review?
- What should be the next campaign?

Do not use it to launch heavy simulations. Use the Python campaign scripts for that.
