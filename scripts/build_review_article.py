from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "reports" / "review_article"
TEX_FILE = ARTICLE_DIR / "open_quantum_control_review.tex"
ASSET_GENERATOR = ROOT / "scripts" / "generate_review_article_assets.py"


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


def available_engine() -> tuple[str, list[str]] | None:
    if shutil.which("tectonic"):
        return "tectonic", ["tectonic", TEX_FILE.name]
    if shutil.which("latexmk"):
        return "latexmk", ["latexmk", "-pdf", "-interaction=nonstopmode", TEX_FILE.name]
    if shutil.which("pdflatex"):
        return "pdflatex", ["pdflatex", "--enable-installer", "-interaction=nonstopmode", TEX_FILE.name]
    miktex_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe",
        Path(os.environ.get("ProgramFiles", "")) / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe",
    ]
    for candidate in miktex_candidates:
        if candidate.exists():
            return "pdflatex", [str(candidate), "--enable-installer", "-interaction=nonstopmode", TEX_FILE.name]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Open Quantum Control review article draft.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable status payload.")
    args = parser.parse_args(argv)

    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    if not TEX_FILE.exists():
        raise FileNotFoundError(TEX_FILE)

    if ASSET_GENERATOR.exists():
        asset_code, asset_output = run_command([sys.executable, str(ASSET_GENERATOR)], ROOT)
        (ARTICLE_DIR / "asset_generation.log").write_text(asset_output, encoding="utf-8")
        if asset_code != 0:
            payload = {
                "status": "asset_generation_failed",
                "log": str(ARTICLE_DIR / "asset_generation.log"),
                "return_code": asset_code,
            }
            print(json.dumps(payload, indent=2))
            return 1

    engine = available_engine()
    if engine is None:
        payload = {
            "status": "latex_engine_missing",
            "message": "No tectonic, latexmk, or pdflatex executable was found in PATH.",
            "latex_source": str(TEX_FILE),
            "reading_copy": str(ARTICLE_DIR / "ARTICLE_READING_COPY.md"),
            "suggested_installers": ["Tectonic", "MiKTeX", "TeX Live"],
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["message"])
            print(f"LaTeX source: {payload['latex_source']}")
            print(f"Readable copy: {payload['reading_copy']}")
        return 2

    engine_name, command = engine
    code, output = run_command(command, ARTICLE_DIR)
    (ARTICLE_DIR / "build.log").write_text(output, encoding="utf-8")

    if engine_name == "pdflatex" and code == 0:
        code2, output2 = run_command(command, ARTICLE_DIR)
        with (ARTICLE_DIR / "build.log").open("a", encoding="utf-8") as handle:
            handle.write("\n\n--- second pdflatex pass ---\n\n")
            handle.write(output2)
        code = code2

    pdf_path = ARTICLE_DIR / "open_quantum_control_review.pdf"
    payload = {
        "status": "completed" if code == 0 and pdf_path.exists() else "failed",
        "engine": engine_name,
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "log": str(ARTICLE_DIR / "build.log"),
        "return_code": code,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
