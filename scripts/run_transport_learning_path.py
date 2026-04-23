from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
RUNNER = ROOT / "scripts" / "run_transport_graph_lab.py"
CONFIGS = [
    ROOT / "configs" / "transport_learning_step1_walk.json",
    ROOT / "configs" / "transport_learning_step2_sink.json",
    ROOT / "configs" / "transport_learning_step3_dephasing.json",
]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    logs: list[str] = []
    for config in CONFIGS:
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--config", str(config)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=env,
        )
        logs.append(f"=== {config.name} ===\n{completed.stdout}\n")
        if completed.returncode != 0:
            (ROOT / "outputs" / "transport_networks" / "learning_path_run.log").write_text("".join(logs), encoding="utf-8")
            return completed.returncode

    (ROOT / "outputs" / "transport_networks" / "learning_path_run.log").write_text("".join(logs), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
