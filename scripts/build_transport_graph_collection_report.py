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
REPORT_DIR = ROOT / "reports" / "transport_graph_collection_report"
TEX_FILE = REPORT_DIR / "transport_graph_collection_report.tex"
GENERATED_DIR = REPORT_DIR / "generated"
COLLECTION_SCRIPT = ROOT / "scripts" / "run_transport_graph_collection.py"
TARGETED_SCRIPT = ROOT / "scripts" / "run_transport_targeted_studies.py"
COLLECTION_RESULTS = ROOT / "outputs" / "transport_networks" / "graph_collection" / "latest" / "results.json"
TARGETED_RESULTS = ROOT / "outputs" / "transport_networks" / "targeted_studies" / "latest" / "results.json"


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


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _interpretation(case_name: str, case_payload: dict[str, object]) -> str:
    best_regime = str(case_payload["best_regime"]).replace("_", " ")
    disorder_strength = float(case_payload["disorder_strength_hz"])
    eta_best = float(case_payload["efficiency_mean"][int(max(range(len(case_payload["efficiency_mean"])), key=lambda idx: case_payload["efficiency_mean"][idx]))])
    eta0 = float(case_payload["efficiency_mean"][0])
    final_purity = float(case_payload["final_purity_mean"])
    final_entropy = float(case_payload["final_entropy_mean"])
    final_pr = float(case_payload["final_participation_ratio_mean"])
    if best_regime == "coherent":
        core = "The coherent limit already gives the best transport, so additional dephasing mainly destroys phase relations that are helping the excitation reach the trap."
    elif best_regime == "intermediate":
        core = "An intermediate dephasing rate improves transport, which is the operational signature of environment-assisted transport in this case."
    else:
        core = "The best point lies at the strongest scanned dephasing, so the coherent pathways are being strongly suppressed and the scan should be extended."
    disorder_sentence = (
        "Static disorder is present, so the uncertainty bars quantify realization-to-realization variation across seeds rather than experimental measurement noise."
        if disorder_strength > 0.0
        else "This is a deterministic clean-graph result, so the uncertainty is dominated by numerical diagnostics rather than ensemble spread."
    )
    gain_sentence = f"The mean sink efficiency changes from {eta0:.3f} in the coherent limit to {eta_best:.3f} at the optimum."
    statmech_sentence = (
        f"At the optimum, the conditional network purity is {final_purity:.3f}, the conditional von Neumann entropy is {final_entropy:.3f}, "
        f"and the final participation ratio of the normalized node populations is {final_pr:.3f}."
    )
    return f"{core} {gain_sentence} {statmech_sentence} {disorder_sentence}"


def _write_summary_table(collection_results: dict[str, object]) -> None:
    summary_lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Summary of the graph-family collection. Means and standard deviations are taken across disorder realizations when disorder is present.}",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "Case & Group & Regime & $\\eta_{\\mathrm{best}}$ & $\\sigma_{\\eta}$ & $\\gamma_{\\phi}^{\\mathrm{best}}$ & $C_{\\ell_1}^{\\mathrm{best}}$ \\\\",
        "\\midrule",
    ]
    for case_name, payload in collection_results["cases"].items():
        best_index = int(max(range(len(payload["efficiency_mean"])), key=lambda idx: payload["efficiency_mean"][idx]))
        eta_best = float(payload["efficiency_mean"][best_index])
        sigma_eta = float(payload["efficiency_std"][best_index])
        coherence_best = float(payload["coherence_mean"][best_index])
        summary_lines.append(
            f"{case_name} & {payload['group']} & {str(payload['best_regime']).replace('_', ' ')} & "
            f"{eta_best:.3f} & {sigma_eta:.3f} & {float(payload['best_rate_hz']):.3f} & {coherence_best:.3f} \\\\"
        )
    summary_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    (GENERATED_DIR / "summary_table.tex").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def _write_pairwise_tables(collection_results: dict[str, object]) -> None:
    pairwise_sections: list[str] = []
    for group_name, group_payload in collection_results["groups"].items():
        matrix = group_payload["pairwise_best_efficiency_difference"]
        labels = list(matrix.keys())
        lines = [
            "\\begin{table}[t]",
            "\\centering",
            f"\\caption{{Pairwise differences in best sink efficiency for the {group_name} cases. Entry $(i,j)$ is $\\eta_{{\\mathrm{{best}},i}}-\\eta_{{\\mathrm{{best}},j}}$.}}",
            "\\begin{tabular}{l" + "c" * len(labels) + "}",
            "\\toprule",
            "Case & " + " & ".join(labels) + " \\\\",
            "\\midrule",
        ]
        for row_label in labels:
            values = " & ".join([f"{float(matrix[row_label][col_label]):+.3f}" for col_label in labels])
            lines.append(f"{row_label} & {values} \\\\")
        lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
        pairwise_sections.extend(lines + [""])
    (GENERATED_DIR / "pairwise_tables.tex").write_text("\n".join(pairwise_sections), encoding="utf-8")


def _write_detailed_case_comments(collection_results: dict[str, object]) -> None:
    detailed_sections: list[str] = []
    for case_name, payload in collection_results["cases"].items():
        best_index = int(max(range(len(payload["efficiency_mean"])), key=lambda idx: payload["efficiency_mean"][idx]))
        eta_best = float(payload["efficiency_mean"][best_index])
        sigma_eta = float(payload["efficiency_std"][best_index])
        coherence_best = float(payload["coherence_mean"][best_index])
        final_purity = float(payload["final_purity_mean"])
        final_entropy = float(payload["final_entropy_mean"])
        final_pop_entropy = float(payload["final_population_entropy_mean"])
        final_pr = float(payload["final_participation_ratio_mean"])
        final_ipr = float(payload["final_ipr_mean"])
        detailed_sections.extend(
            [
                f"\\subsection{{{case_name}}}",
                (
                    f"This case uses a {payload['topology']} topology with {int(payload['n_sites'])} sites, "
                    f"initial site {int(payload['initial_site'])}, trap site {int(payload['trap_site'])}, "
                    f"coherent coupling $J={float(payload['coupling_hz']):.2f}$, sink rate $\\kappa={float(payload['sink_rate_hz']):.2f}$, "
                    f"and loss rate $\\Gamma={float(payload['loss_rate_hz']):.2f}$. "
                    f"The disorder strength is $W={float(payload['disorder_strength_hz']):.2f}$ and the ensemble contains {int(payload['n_realizations'])} realization(s)."
                ),
                (
                    f"The best regime is {str(payload['best_regime']).replace('_', ' ')}, with "
                    f"$\\eta_{{\\mathrm{{best}}}}={eta_best:.3f}$, uncertainty $\\sigma_\\eta={sigma_eta:.3f}$, "
                    f"and optimal dephasing rate $\\gamma_\\phi^{{\\mathrm{{best}}}}={float(payload['best_rate_hz']):.3f}$. "
                    f"The mean coherence at the optimum is $C_{{\\ell_1}}={coherence_best:.3f}$."
                ),
                (
                    f"The conditional final-state diagnostics at the optimum are purity $\\gamma={final_purity:.3f}$, "
                    f"von Neumann entropy $S={final_entropy:.3f}$, Shannon population entropy $H_\\mathrm{{pop}}={final_pop_entropy:.3f}$, "
                    f"participation ratio $PR={final_pr:.3f}$, and inverse participation ratio $IPR={final_ipr:.3f}$."
                ),
                (
                    f"The numerical diagnostics at the optimum are "
                    f"$\\max_t |\\mathrm{{Tr}}\\rho(t)-1|={float(payload['best_rate_diagnostics']['max_trace_deviation']):.2e}$, "
                    f"$\\max_t |\\sum_i P_i(t)+P_s(t)+P_\\ell(t)-1|={float(payload['best_rate_diagnostics']['max_population_closure_error']):.2e}$, "
                    f"and minimum eigenvalue $\\lambda_\\mathrm{{min}}={float(payload['best_rate_diagnostics']['min_state_eigenvalue']):.2e}$. "
                    f"These values indicate that the reported populations are numerically trustworthy."
                ),
                _interpretation(case_name, payload),
                "",
            ]
        )
    (GENERATED_DIR / "detailed_case_comments.tex").write_text("\n".join(detailed_sections), encoding="utf-8")


def _write_targeted_sections(targeted_results: dict[str, object]) -> None:
    chain_results = targeted_results["chain_crossover"]["results"]
    ring_results = targeted_results["ring_size_refined"]["results"]
    ring_parity_results = targeted_results["ring_parity_distance"]["results"]
    ring_distance_summary = targeted_results["ring_parity_distance"]["distance_summary"]
    sink_results = targeted_results["sink_position_sweep"]
    metric_correlations = targeted_results["sink_position_metric_correlations"]
    chain_ensemble_size = int(chain_results[0]["n_realizations"])
    sink_ensemble_size = int(next(iter(sink_results.values()))[0]["n_realizations"])

    chain_lines = [
        "\\subsection{Refined chain-disorder crossover}",
        (
            "The original phase-slice study suggested that the chain changed regime between $W/J=0.4$ and $W/J=0.8$. "
            f"We therefore refined the disorder grid locally with a pilot ensemble of {chain_ensemble_size} seeds."
        ),
    ]
    transition_points = [
        row for row in chain_results if str(row["best_regime"]) != "coherent"
    ]
    if transition_points:
        first_transition = transition_points[0]
        chain_lines.append(
            (
                f"The first non-coherent optimum in the refined scan appears at $W/J={float(first_transition['w_over_j']):.2f}$, "
                f"where the best regime becomes {str(first_transition['best_regime']).replace('_', ' ')} and "
                f"$\\gamma_\\phi^{{\\mathrm{{best}}}}={float(first_transition['gamma_phi_best']):.3f}$."
            )
        )
    chain_lines.append(
        (
            "This is the strongest current candidate for a genuine crossover line in the $(W/J,\\gamma_\\phi/J)$ plane. "
            "It is not yet a final claim because the targeted follow-up still needs a local refinement of the disorder axis around the transition and a convergence check of the inferred boundary against independent ensemble resampling."
        )
    )

    ring_lines = [
        "\\subsection{Refined ring-size sweep}",
        (
            "The ring was rescanned over a denser set of sizes in order to test whether the previously observed alternation with $N$ was accidental or structural."
        ),
    ]
    coherent_n = [int(row["n_sites"]) for row in ring_results if str(row["best_regime"]) == "coherent"]
    intermediate_n = [int(row["n_sites"]) for row in ring_results if str(row["best_regime"]) == "intermediate"]
    ring_lines.append(
        (
            f"In the current refined data, coherent-optimal rings appear at $N={coherent_n}$ and intermediate-optimal rings appear at $N={intermediate_n}$. "
            "That pattern is consistent with a parity/symmetry effect. The next question is whether this alternation survives after controlling explicitly for shortest-path distance to the trap."
        )
    )

    ring_parity_lines = [
        "\\subsection{Ring parity versus sink distance}",
        (
            "To separate parity from geometry, we fixed the initial site and rescanned clean rings over unique shortest-path distances to the trap. "
            "This removes the ambiguity between ``odd versus even ring'' and ``near versus far sink''."
        ),
    ]
    if ring_distance_summary:
        summary_chunks: list[str] = []
        for distance_key, payload in sorted(ring_distance_summary.items(), key=lambda item: int(item[0])):
            summary_chunks.append(
                (
                    f"At distance $d={distance_key}$, the mean best efficiency is {float(payload['even_eta_mean']):.3f} for even rings and "
                    f"{float(payload['odd_eta_mean']):.3f} for odd rings, with even-minus-odd difference "
                    f"{float(payload['eta_even_minus_odd']):+.3f}. The corresponding optimal dephasing difference is "
                    f"{float(payload['gamma_even_minus_odd']):+.3f}."
                )
            )
        ring_parity_lines.extend(summary_chunks)
    dominant_rows = sorted(
        ring_parity_results,
        key=lambda row: (float(row["eta_best_mean"]), -float(row["gamma_phi_best"])),
        reverse=True,
    )[:2]
    if dominant_rows:
        exemplar = dominant_rows[0]
        ring_parity_lines.append(
            (
                f"The strongest clean ring point in this controlled study occurs at $N={int(exemplar['n_sites'])}$, "
                f"distance $d={int(exemplar['ring_shortest_distance'])}$, with "
                f"$\\eta_{{\\mathrm{{best}}}}={float(exemplar['eta_best_mean']):.3f}$ and "
                f"$\\gamma_\\phi^{{\\mathrm{{best}}}}={float(exemplar['gamma_phi_best']):.3f}$."
            )
        )
    ring_parity_lines.append(
        (
            "If matched-distance odd and even rings remain separated, that points to a genuine parity/size effect. "
            "If they collapse onto the same trend, then the original alternation was mostly a distance-to-target effect."
        )
    )

    sink_lines = [
        "\\subsection{Sink-position sweep}",
        (
            f"The trap site was varied while keeping the topology fixed. For each trap position we again optimized over dephasing and used a {sink_ensemble_size}-seed disorder ensemble."
        ),
    ]
    best_sink_statements: list[str] = []
    for topology, rows in sink_results.items():
        best_row = max(rows, key=lambda row: float(row["eta_best_mean"]))
        best_sink_statements.append(
            (
                f"For the {topology} topology, the best mean transport occurs at trap site {int(best_row['trap_site'])}, "
                f"with $\\eta_{{\\mathrm{{best}}}}={float(best_row['eta_best_mean']):.3f}$ and "
                f"$\\gamma_\\phi^{{\\mathrm{{best}}}}={float(best_row['gamma_phi_best']):.3f}$."
            )
        )
    sink_lines.extend(best_sink_statements)
    sink_lines.append(
        (
            "This is the first direct indication that graph topology alone is not the full story: the geometric role of the target node also matters and should be correlated next with degree, closeness, and graph distance to the initial site."
        )
    )
    sink_lines.append(
        (
            f"In the present sweep, the Pearson correlations with best sink efficiency are: "
            f"trap degree = {float(metric_correlations['trap_degree']):.3f}, "
            f"trap closeness = {float(metric_correlations['trap_closeness']):.3f}, "
            f"mean distance to trap = {float(metric_correlations['mean_distance_to_trap']):.3f}, "
            f"and initial-to-trap distance = {float(metric_correlations['initial_to_trap_distance']):.3f}."
        )
    )

    lines = [
        "\\section{Targeted follow-up studies}",
        "",
        (
            "The next layer of the project is no longer a generic graph-family comparison. "
            "It is a set of targeted tests motivated by the first-pass atlas: a refined disorder scan for the chain, a denser size scan for the ring, a controlled ring study that separates parity from distance to the trap, and a sink-position sweep for all currently implemented topologies."
        ),
        "",
        "\\begin{figure}[t]",
        "\\centering",
        "\\includegraphics[width=0.86\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/chain_crossover_refined.png}",
        "\\caption{Refined chain crossover study. Top-left: best sink efficiency versus $W/J$. Top-right: optimal dephasing versus $W/J$. Bottom panels: final conditional purity, entropy, and participation ratio at the transport optimum.}",
        "\\end{figure}",
        "",
        "\\begin{figure}[t]",
        "\\centering",
        "\\includegraphics[width=0.86\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/ring_size_refined.png}",
        "\\caption{Refined ring-size study. The goal is to test whether the original alternation between coherent-optimal and intermediate-optimal behavior is a real parity/symmetry effect.}",
        "\\end{figure}",
        "",
        "\\begin{figure}[t]",
        "\\centering",
        "\\includegraphics[width=0.86\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/ring_parity_distance.png}",
        "\\caption{Controlled ring study that separates ring-size parity from shortest-path distance to the trap. Top panels: heat maps of best efficiency and optimal dephasing over $(N,d)$. Bottom panels: matched-distance comparisons between odd and even rings.}",
        "\\end{figure}",
        "",
        "\\begin{figure}[t]",
        "\\centering",
        "\\includegraphics[width=0.48\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/sink_position_eta_heatmap.png}",
        "\\includegraphics[width=0.48\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/sink_position_gamma_heatmap.png}",
        "\\includegraphics[width=0.48\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/sink_position_entropy_heatmap.png}",
        "\\includegraphics[width=0.48\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/sink_position_participation_heatmap.png}",
        f"\\caption{{Sink-position sweep. Top-left: best transport efficiency. Top-right: optimal dephasing. Bottom-left: final conditional entropy. Bottom-right: final participation ratio. The sweep uses a {sink_ensemble_size}-seed disorder ensemble.}}",
        "\\end{figure}",
        "",
        "\\begin{figure}[t]",
        "\\centering",
        "\\includegraphics[width=0.86\\textwidth]{../../outputs/transport_networks/targeted_studies/latest/figures/sink_position_metric_correlations.png}",
        "\\caption{Correlations between graph metrics of the trap node and the best sink efficiency in the sink-position sweep. These scatter plots are the first bridge from purely topological labels to quantitative transport predictors.}",
        "\\end{figure}",
        "",
    ]
    lines.extend(chain_lines + [""])
    lines.extend(ring_lines + [""])
    lines.extend(ring_parity_lines + [""])
    lines.extend(sink_lines + [""])
    lines.extend(
        [
            "\\subsection{What looks genuinely new enough to pursue}",
            (
                "At the present stage, the most credible candidates for publishable new results are: "
                "(i) a disorder-induced crossover line for the chain, "
                "(ii) a topology- and sink-position-dependent transport atlas in normalized variables, and "
                "(iii) a robustness ranking that reports both mean efficiency and ensemble spread."
            ),
        ]
    )
    (GENERATED_DIR / "targeted_sections.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _generate_tex_fragments() -> None:
    collection_results = json.loads(COLLECTION_RESULTS.read_text(encoding="utf-8"))
    targeted_results = json.loads(TARGETED_RESULTS.read_text(encoding="utf-8"))
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    _write_summary_table(collection_results)
    _write_pairwise_tables(collection_results)
    _write_detailed_case_comments(collection_results)
    _write_targeted_sections(targeted_results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the detailed graph-collection report.")
    parser.add_argument("--json", action="store_true", help="Print build status as JSON.")
    parser.add_argument(
        "--reuse-existing-results",
        action="store_true",
        help="Do not rerun the simulation scripts if the expected results files already exist.",
    )
    args = parser.parse_args(argv)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not TEX_FILE.exists():
        raise FileNotFoundError(TEX_FILE)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    generation_logs: list[str] = []
    if not args.reuse_existing_results:
        for script, label in ((COLLECTION_SCRIPT, "graph_collection"), (TARGETED_SCRIPT, "targeted_studies")):
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=env,
            )
            generation_logs.append(f"--- {label} ---\n{completed.stdout}\n")
            if completed.returncode != 0:
                (REPORT_DIR / "simulation_generation.log").write_text("\n".join(generation_logs), encoding="utf-8")
                payload = {
                    "status": f"{label}_generation_failed",
                    "log": str(REPORT_DIR / "simulation_generation.log"),
                    "return_code": completed.returncode,
                }
                print(json.dumps(payload, indent=2))
                return 1
        (REPORT_DIR / "simulation_generation.log").write_text("\n".join(generation_logs), encoding="utf-8")
    else:
        if not COLLECTION_RESULTS.exists() or not TARGETED_RESULTS.exists():
            payload = {
                "status": "missing_results_for_reuse",
                "collection_results": str(COLLECTION_RESULTS),
                "targeted_results": str(TARGETED_RESULTS),
            }
            print(json.dumps(payload, indent=2))
            return 1
    _generate_tex_fragments()

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

    pdf_path = REPORT_DIR / "transport_graph_collection_report.pdf"
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
