from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "repro" / "paper_registry.yaml"
MANIFEST = ROOT / "repro" / "repro_manifest.yaml"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oqs_control.figure_annotations import (  # noqa: E402
    annotate_output_directory,
    clean_results_payload,
    remove_redundant_markdown,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'")


def load_registry(path: Path = REGISTRY) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- paper_id:"):
            if current:
                entries.append(current)
            current = {"paper_id": _clean_scalar(line.split(":", 1)[1])}
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.strip()] = _clean_scalar(value)
    if current:
        entries.append(current)
    return entries


def find_entry(paper_id: str) -> dict[str, str]:
    for entry in load_registry():
        if entry.get("paper_id") == paper_id:
            return entry
    raise SystemExit(f"Unknown paper_id: {paper_id}")


def write_runner_metadata(
    paper_id: str,
    script: Path,
    output_dir: Path,
    command: list[str],
) -> None:
    results = output_dir / "results.json"
    metrics = output_dir / "metrics.json"
    config_used = output_dir / "config_used.json"
    metadata = {
        "paper_id": paper_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "command": command,
        "registry_sha256": sha256_file(REGISTRY),
        "manifest_sha256": sha256_file(MANIFEST),
        "script_sha256": sha256_file(script),
        "results_sha256": sha256_file(results) if results.exists() else None,
        "metrics_sha256": sha256_file(metrics) if metrics.exists() else None,
        "config_used_sha256": sha256_file(config_used) if config_used.exists() else None,
        "output_dir": str(output_dir),
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run registered reproducibility targets.")
    parser.add_argument("--paper-id", help="Registered paper_id to run.")
    parser.add_argument("--list", action="store_true", help="List available paper IDs.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override target output directory.")
    args = parser.parse_args(argv)

    if args.list:
        for entry in load_registry():
            print(f"{entry.get('paper_id')}: {entry.get('title', '')}")
        return 0

    if not args.paper_id:
        parser.error("--paper-id is required unless --list is used")

    entry = find_entry(args.paper_id)
    script = ROOT / entry["script"]
    output_dir = args.output_dir or (ROOT / entry["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, str(script), "--output-dir", str(output_dir)]
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if completed.returncode != 0:
        return int(completed.returncode)
    clean_results_payload(output_dir / "results.json")
    remove_redundant_markdown(output_dir)
    annotate_output_directory(args.paper_id, output_dir)
    write_runner_metadata(args.paper_id, script, output_dir, command)
    print(f"Reproduction target completed: {args.paper_id}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
