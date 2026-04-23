from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
REPORT_DIR = ROOT / "reports" / "transport_graph_lab_demo"
TEX_FILE = REPORT_DIR / "transport_graph_lab_demo.tex"
GRAPH_LAB_SCRIPT = ROOT / "scripts" / "run_transport_graph_lab.py"
GRAPH_LAB_OUTPUT = ROOT / "outputs" / "transport_networks" / "graph_lab" / "latest"
GENERATED_DIR = REPORT_DIR / "generated"


def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout


def available_engine(tex_file: Path) -> tuple[str, list[str]] | None:
    if shutil.which("tectonic"):
        return "tectonic", ["tectonic", tex_file.name]
    if shutil.which("pdflatex"):
        return "pdflatex", ["pdflatex", "--enable-installer", "-interaction=nonstopmode", tex_file.name]
    if shutil.which("latexmk"):
        return "latexmk", ["latexmk", "-pdf", "-interaction=nonstopmode", tex_file.name]
    miktex_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe",
        Path(os.environ.get("ProgramFiles", "")) / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe",
    ]
    for candidate in miktex_candidates:
        if candidate.exists():
            return "pdflatex", [str(candidate), "--enable-installer", "-interaction=nonstopmode", tex_file.name]
    return None


def available_bibtex(tex_file: Path) -> list[str] | None:
    if shutil.which("bibtex"):
        return ["bibtex", tex_file.stem]
    miktex_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "bibtex.exe",
        Path(os.environ.get("ProgramFiles", "")) / "MiKTeX" / "miktex" / "bin" / "x64" / "bibtex.exe",
    ]
    for candidate in miktex_candidates:
        if candidate.exists():
            return [str(candidate), tex_file.stem]
    return None


def _generate_comparative_table() -> None:
    metrics = json.loads((GRAPH_LAB_OUTPUT / "metrics.json").read_text(encoding="utf-8"))
    results = json.loads((GRAPH_LAB_OUTPUT / "results.json").read_text(encoding="utf-8"))
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    scenario_blocks = {block["scenario"]["name"]: block for block in results["scenarios"]}

    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Automatically generated summary of the current baseline graph comparison.}",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "Scenario & Best regime & $\\eta_{\\mathrm{coh}}$ & $\\eta_{\\mathrm{best}}$ & $\\gamma_{\\phi}^{\\mathrm{best}}$ \\\\",
        "\\midrule",
    ]
    for name, metric in metrics["scenarios"].items():
        scenario = scenario_blocks[name]["scenario"]
        lines.append(
            f"{scenario['name']} & {metric['best_regime'].replace('_', ' ')} & "
            f"{metric['efficiency_no_dephasing']:.3f} & "
            f"{metric['efficiency_optimal_dephasing']:.3f} & "
            f"{metric['optimal_dephasing_rate_hz']:.3f} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )
    (GENERATED_DIR / "comparative_table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the transport graph lab demo PDF.")
    parser.add_argument("--json", action="store_true", help="Print build status as JSON.")
    args = parser.parse_args(argv)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not TEX_FILE.exists():
        raise FileNotFoundError(TEX_FILE)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    graph_code = subprocess.run(
        [sys.executable, str(GRAPH_LAB_SCRIPT)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    (REPORT_DIR / "simulation_generation.log").write_text(graph_code.stdout, encoding="utf-8")
    if graph_code.returncode != 0:
        payload = {
            "status": "simulation_generation_failed",
            "log": str(REPORT_DIR / "simulation_generation.log"),
            "return_code": graph_code.returncode,
        }
        print(json.dumps(payload, indent=2))
        return 1

    _generate_comparative_table()

    engine = available_engine(TEX_FILE)
    if engine is None:
        payload = {
            "status": "latex_engine_missing",
            "message": "No tectonic, latexmk, or pdflatex executable was found.",
            "latex_source": str(TEX_FILE),
        }
        print(json.dumps(payload, indent=2))
        return 2

    engine_name, command = engine
    code, output = run_command(command, REPORT_DIR)
    (REPORT_DIR / "build.log").write_text(output, encoding="utf-8")

    if engine_name == "pdflatex" and code == 0:
        tex_source = TEX_FILE.read_text(encoding="utf-8")
        if "\\bibliography{" in tex_source:
            bibtex_command = available_bibtex(TEX_FILE)
            if bibtex_command is not None:
                bib_code, bib_output = run_command(bibtex_command, REPORT_DIR)
                with (REPORT_DIR / "build.log").open("a", encoding="utf-8") as handle:
                    handle.write("\n\n--- bibtex pass ---\n\n")
                    handle.write(bib_output)
                code = bib_code
        if code == 0:
            code2, output2 = run_command(command, REPORT_DIR)
            with (REPORT_DIR / "build.log").open("a", encoding="utf-8") as handle:
                handle.write("\n\n--- second pdflatex pass ---\n\n")
                handle.write(output2)
            code = code2
        if code == 0:
            code3, output3 = run_command(command, REPORT_DIR)
            with (REPORT_DIR / "build.log").open("a", encoding="utf-8") as handle:
                handle.write("\n\n--- third pdflatex pass ---\n\n")
                handle.write(output3)
            code = code3

    pdf_path = REPORT_DIR / "transport_graph_lab_demo.pdf"
    payload = {
        "status": "completed" if code == 0 and pdf_path.exists() else "failed",
        "engine": engine_name,
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "log": str(REPORT_DIR / "build.log"),
        "return_code": code,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
