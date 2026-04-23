#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

MODE="${1:-pilot}"

run_intense() {
  python scripts/run_transport_dynamic_network_atlas.py "$@"
}

case "$MODE" in
  pilot)
    run_intense --profile intense --stop-after-records 10000 --resume
    ;;
  random)
    run_intense --profile intense --families modular_two_community --resume
    run_intense --profile intense --families random_geometric --resume
    run_intense --profile intense --families watts_strogatz_small_world --resume
    run_intense --profile intense --families erdos_renyi --resume
    run_intense --profile intense --families barabasi_albert_scale_free --resume
    ;;
  deterministic)
    run_intense --profile intense --families chain,ring,complete,star,square_lattice_2d,bottleneck,clustered,sierpinski_gasket,sierpinski_carpet_like --resume
    ;;
  finalize)
    python scripts/run_transport_lab_master_pipeline.py --mode registry_only
    python scripts/build_transport_lab_mcp_index.py
    python scripts/run_transport_lab_mcp_server.py --check
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    echo "Use one of: pilot, random, deterministic, finalize" >&2
    exit 1
    ;;
esac
