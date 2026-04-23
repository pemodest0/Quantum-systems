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
PROPOSAL_DIR = ROOT / "reports" / "famb_msc_transport_proposal"
TEX_FILE = PROPOSAL_DIR / "famb_msc_transport_proposal.tex"
BASELINE_SCRIPT = ROOT / "scripts" / "run_transport_project_lab.py"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the FAMB MSc transport proposal PDF.")
    parser.add_argument("--json", action="store_true", help="Print build status as JSON.")
    args = parser.parse_args(argv)

    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    if not TEX_FILE.exists():
        raise FileNotFoundError(TEX_FILE)

    baseline_code, baseline_output = run_command([sys.executable, str(BASELINE_SCRIPT)], ROOT)
    (PROPOSAL_DIR / "baseline_generation.log").write_text(baseline_output, encoding="utf-8")
    if baseline_code != 0:
        payload = {
            "status": "baseline_generation_failed",
            "log": str(PROPOSAL_DIR / "baseline_generation.log"),
            "return_code": baseline_code,
        }
        print(json.dumps(payload, indent=2))
        return 1

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
    code, output = run_command(command, PROPOSAL_DIR)
    (PROPOSAL_DIR / "build.log").write_text(output, encoding="utf-8")

    if engine_name == "pdflatex" and code == 0:
        tex_source = TEX_FILE.read_text(encoding="utf-8")
        if "\\bibliography{" in tex_source:
            bibtex_command = available_bibtex(TEX_FILE)
            if bibtex_command is not None:
                bib_code, bib_output = run_command(bibtex_command, PROPOSAL_DIR)
                with (PROPOSAL_DIR / "build.log").open("a", encoding="utf-8") as handle:
                    handle.write("\n\n--- bibtex pass ---\n\n")
                    handle.write(bib_output)
                code = bib_code
        if code == 0:
            code2, output2 = run_command(command, PROPOSAL_DIR)
            with (PROPOSAL_DIR / "build.log").open("a", encoding="utf-8") as handle:
                handle.write("\n\n--- second pdflatex pass ---\n\n")
                handle.write(output2)
            code = code2
        if code == 0:
            code3, output3 = run_command(command, PROPOSAL_DIR)
            with (PROPOSAL_DIR / "build.log").open("a", encoding="utf-8") as handle:
                handle.write("\n\n--- third pdflatex pass ---\n\n")
                handle.write(output3)
            code = code3

    pdf_path = PROPOSAL_DIR / "famb_msc_transport_proposal.pdf"
    payload = {
        "status": "completed" if code == 0 and pdf_path.exists() else "failed",
        "engine": engine_name,
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "log": str(PROPOSAL_DIR / "build.log"),
        "return_code": code,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
