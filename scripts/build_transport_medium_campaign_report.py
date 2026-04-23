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
REPORT_DIR = ROOT / "reports" / "transport_medium_campaign_report"
TEX_FILE = REPORT_DIR / "transport_medium_campaign_report.tex"
GENERATED_DIR = REPORT_DIR / "generated"
RUNNER_SCRIPT = ROOT / "scripts" / "run_transport_medium_campaign.py"
RESULTS_FILE = ROOT / "outputs" / "transport_networks" / "medium_propagation" / "latest" / "results.json"
METRICS_FILE = ROOT / "outputs" / "transport_networks" / "medium_propagation" / "latest" / "metrics.json"
REVIEW_FILE = ROOT / "outputs" / "transport_networks" / "medium_propagation" / "latest" / "analyst_review.json"


def _tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
    }
    escaped = str(text)
    for source, target in replacements.items():
        escaped = escaped.replace(source, target)
    return escaped


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    return completed.returncode, completed.stdout


def available_engine(tex_file: Path) -> tuple[str, list[str]] | None:
    if shutil.which("tectonic"):
        return "tectonic", ["tectonic", tex_file.name]
    if shutil.which("pdflatex"):
        return "pdflatex", ["pdflatex", "--enable-installer", "-interaction=nonstopmode", tex_file.name]
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


def _write_generated_fragments() -> None:
    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_FILE.read_text(encoding="utf-8"))

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Best point found for each medium family in campaign A.}",
        "\\begin{tabular}{lccccc}",
        "\\toprule",
        "Medium & Best success & Disorder / coupling & Phase scrambling / coupling & Best regime & Final spread \\\\",
        "\\midrule",
    ]
    for row in metrics["scenario_best_points"]:
        summary_lines.append(
            f"{_tex_escape(row['scenario'])} & {float(row['best_efficiency']):.3f} & {float(row['best_disorder_over_coupling']):.2f} & "
            f"{float(row['best_dephasing_over_coupling']):.2f} & {_tex_escape(row['best_regime'])} & {float(row['best_spreading']):.3f} \\\\"
        )
    summary_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    (GENERATED_DIR / "summary_table.tex").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    review_lines = [
        "\\section{Automated review summary}",
        _tex_escape(review["analyst_summary_ptbr"]),
        "",
        "\\subsection{Scout findings}",
    ]
    for finding in review["scout"]:
        review_lines.append(f"\\textbf{{Finding:}} {_tex_escape(finding['finding'])}\\\\")
        review_lines.append(f"\\textbf{{Reason:}} {_tex_escape(finding['reason'])}\\\\")
        review_lines.append("")
    review_lines.append("\\subsection{Critic assessment}")
    for item in review["critic"]:
        review_lines.append(f"\\textbf{{Level:}} {_tex_escape(item['level'])}\\\\")
        review_lines.append(f"\\textbf{{Concern:}} {_tex_escape(item['concern'])}\\\\")
        review_lines.append(f"\\textbf{{Evidence:}} {_tex_escape(item['evidence'])}\\\\")
        review_lines.append("")
    review_lines.append("\\subsection{Planner recommendation}")
    review_lines.append(f"\\textbf{{Next action:}} {_tex_escape(review['planner']['next_action'])}\\\\")
    review_lines.append(f"\\textbf{{Reason:}} {_tex_escape(review['planner']['reason'])}\\\\")
    (GENERATED_DIR / "review_summary.tex").write_text("\n".join(review_lines) + "\n", encoding="utf-8")

    scenario_lines = ["\\section{Scenario-by-scenario reading}"]
    for scenario in results["scenarios"]:
        expectation = scenario["literature_expectation"]
        assessment = scenario["expectation_assessment"]
        best = scenario["best_point"]
        scenario_lines.extend(
            [
                f"\\subsection{{{scenario['scenario_name']}}}",
                (
                    f"This medium uses the geometry type {_tex_escape(scenario['medium_type'])} with {int(scenario['n_sites'])} physical sites, "
                    f"coherent coupling $J={float(scenario['coupling_hz']):.2f}$, target-capture rate $\\kappa={float(scenario['sink_rate_hz']):.2f}$, "
                    f"and parasitic loss rate $\\Gamma={float(scenario['loss_rate_hz']):.2f}$."
                ),
                (
                    f"The best point found in the scanned map occurs at disorder-to-coupling ratio "
                    f"$W/J={float(best['disorder_over_coupling']):.2f}$ and phase-scrambling-to-coupling ratio "
                    f"$\\gamma_\\phi/J={float(best['dephasing_over_coupling']):.2f}$, giving final success "
                    f"$\\eta={float(best['transport_efficiency']):.3f}$, final spread {float(best['spreading']):.3f}, "
                    f"final mixing entropy {float(best['mixing']):.3f}, and regime label {_tex_escape(best['regime'])}."
                ),
                "\\paragraph{Literature expectation.}",
                (
                    f"Expected transport trend: {_tex_escape(expectation['expected_transport_trend'])} "
                    f"Expected role of disorder: {_tex_escape(expectation['expected_role_of_disorder'])} "
                    f"Expected role of phase scrambling: {_tex_escape(expectation['expected_role_of_phase_scrambling'])} "
                    f"Expected failure mode: {_tex_escape(expectation['expected_failure_mode'])}"
                ),
                "\\paragraph{Measured comparison.}",
                (
                    f"Disorder suppression observed: {assessment['measured_disorder_suppresses_transport']}. "
                    f"Moderate phase scrambling helps: {assessment['measured_moderate_phase_scrambling_can_help']}. "
                    f"Strong phase scrambling suppresses transport: {assessment['measured_strong_phase_scrambling_suppresses_transport']}. "
                    f"Agreement level: {_tex_escape(assessment['agreement_level'])} with score {float(assessment['agreement_score']):.2f}."
                ),
                "",
            ]
        )
    (GENERATED_DIR / "scenario_sections.tex").write_text("\n".join(scenario_lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the medium campaign report.")
    parser.add_argument("--json", action="store_true", help="Print build status as JSON.")
    parser.add_argument(
        "--reuse-existing-results",
        action="store_true",
        help="Reuse existing outputs instead of rerunning the campaign.",
    )
    args = parser.parse_args(argv)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not TEX_FILE.exists():
        raise FileNotFoundError(TEX_FILE)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    if not args.reuse_existing_results:
        completed = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=env,
        )
        (REPORT_DIR / "simulation_generation.log").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            payload = {
                "status": "campaign_generation_failed",
                "log": str(REPORT_DIR / "simulation_generation.log"),
                "return_code": completed.returncode,
            }
            print(json.dumps(payload, indent=2))
            return 1
    else:
        for required in (RESULTS_FILE, METRICS_FILE, REVIEW_FILE):
            if not required.exists():
                payload = {"status": "missing_results_for_reuse", "missing": str(required)}
                print(json.dumps(payload, indent=2))
                return 1

    _write_generated_fragments()

    engine = available_engine(TEX_FILE)
    if engine is None:
        payload = {"status": "latex_engine_missing", "latex_source": str(TEX_FILE)}
        print(json.dumps(payload, indent=2))
        return 2

    engine_name, command = engine
    code, output = run_command(command, REPORT_DIR)
    (REPORT_DIR / "build.log").write_text(output, encoding="utf-8")

    if engine_name == "pdflatex" and code == 0:
        bibtex_command = available_bibtex(TEX_FILE)
        if bibtex_command is not None:
            bib_code, bib_output = run_command(bibtex_command, REPORT_DIR)
            with (REPORT_DIR / "build.log").open("a", encoding="utf-8") as handle:
                handle.write("\n\n--- bibtex pass ---\n\n")
                handle.write(bib_output)
            code = bib_code
        if code == 0:
            for label in ("second", "third"):
                code_next, output_next = run_command(command, REPORT_DIR)
                with (REPORT_DIR / "build.log").open("a", encoding="utf-8") as handle:
                    handle.write(f"\n\n--- {label} pdflatex pass ---\n\n")
                    handle.write(output_next)
                code = code_next
                if code != 0:
                    break

    pdf_path = REPORT_DIR / "transport_medium_campaign_report.pdf"
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
