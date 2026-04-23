#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/analyze_transport_parameter_space.py
python scripts/run_transport_lab_mcp_server.py --check
pytest -q \
  tests/test_transport_dynamic_network_atlas.py \
  tests/test_transport_paper_reproduction_suite.py \
  tests/test_transport_parameter_space_analysis.py

echo
echo "Mac transport bootstrap complete."
echo "Read next:"
echo "  - AGENTS.md"
echo "  - docs/handoffs/transport_lab_mac_handoff.md"
echo "  - outputs/transport_networks/lab_registry/latest/transport_lab_memory.md"
