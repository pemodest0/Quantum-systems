from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "review_article"
GENERATED_DIR = REPORT_DIR / "generated"
FIGURE_DIR = GENERATED_DIR / "figures"
ARTIFACT_DIR = GENERATED_DIR / "artifact_snapshots"
CLEAN_DOCS_DIR = ROOT / "docs"
CLEAN_PAPERS_DIR = CLEAN_DOCS_DIR / "papers"


PAPER_ORDER = [
    "internal_validation_baseline",
    "na23_relaxometry_2023",
    "spin32_algebraic_2004",
    "qst_relaxation_2008",
    "spin32_qlogic_qst_2005",
    "nonmarkov_noise_2022",
    "multipass_qpt_2024",
    "quadrupolar_qip_2012",
    "grape_nmr_control_2005",
    "pps_optimal_control_2012",
    "projected_ls_qpt_2022",
    "gate_set_tomography_2021",
    "nonmarkov_process_tensor_2020",
    "noise_filtering_control_2014",
    "dd_noise_spectroscopy_2011",
    "flux_qubit_noise_spectroscopy_2011",
    "experimental_decision_pipeline",
]


PAPER_META: dict[str, dict[str, str]] = {
    "internal_validation_baseline": {
        "label": "Internal Baseline",
        "title": "Internal spin-3/2 Na-23 validation baseline",
        "category": "Internal validation",
        "role": "Physical consistency gate before any paper reproduction.",
        "model": "Spin operators, Hamiltonian scales, synthetic spectra, and Liouvillian checks.",
        "lesson": "No reproduction should be trusted until the spin-3/2 algebra and spectrum basics pass.",
        "limitations": "This is an internal benchmark, not an external paper reproduction.",
    },
    "na23_relaxometry_2023": {
        "label": "Paper A",
        "title": "23Na relaxometry: theory and applications",
        "category": "Na-23 relaxation",
        "role": "Quadrupolar relaxation vocabulary and effective relaxation modeling.",
        "model": "Biexponential envelopes compared with reduced Redfield-inspired spectral-density rates.",
        "lesson": "The current empirical decay model is useful, but interpretable relaxometry needs spectral-density parameters.",
        "limitations": "Qualitative effective-model reproduction of a review paper, not a full clinical or materials review.",
    },
    "spin32_algebraic_2004": {
        "label": "Paper B",
        "title": "Algebraic description of spin 3/2 dynamics in NMR",
        "category": "Spin-3/2 algebra",
        "role": "Map spin-3/2 operator algebra into the Python Hilbert/Liouville implementation.",
        "model": "Hilbert evolution, Liouville-space superoperators, coherence-order pathways, and B0/B1 sensitivity.",
        "lesson": "The Liouville formalism is numerically consistent with Hilbert propagation and ready for dissipative extensions.",
        "limitations": "Synthetic dynamics only; experiment-specific pulse calibration is not inferred.",
    },
    "qst_relaxation_2008": {
        "label": "Paper C",
        "title": "Relaxation dynamics in a quadrupolar NMR system using QST",
        "category": "QST relaxation",
        "role": "Density-matrix-level relaxation identification.",
        "model": "Synthetic trajectories, seven-phase QST, rate extraction, noise stress tests.",
        "lesson": "QST can identify population and coherence decay rates beyond spectrum-only fitting.",
        "limitations": "Uses synthetic tomography signals; real extraction requires experimental amplitude calibration.",
    },
    "spin32_qlogic_qst_2005": {
        "label": "Paper D",
        "title": "Spin-3/2 quantum logical operations monitored by QST",
        "category": "Selective control",
        "role": "Expose finite-pulse errors in quadrupolar selective gates.",
        "model": "Selective rectangular pulses with and without internal quadrupolar evolution.",
        "lesson": "Ignoring quadrupolar evolution during pulses can destroy coherent gate fidelity.",
        "limitations": "Rectangular pulses are diagnostic baselines; optimized pulses are handled by the GRAPE layer.",
    },
    "nonmarkov_noise_2022": {
        "label": "Paper E",
        "title": "Characterization and control of non-Markovian quantum noise",
        "category": "Memory diagnostics",
        "role": "Define operational failure signatures for simple Markovian models.",
        "model": "Trace-distance revivals, negative time-local rates, Ramsey/echo disagreement, Markovian fit residuals.",
        "lesson": "A Lindblad model is sufficient only while it predicts the measured history-dependent data.",
        "limitations": "Benchmark is synthetic and minimal, not a reproduction of the full review.",
    },
    "multipass_qpt_2024": {
        "label": "Paper F",
        "title": "Multipass quantum process tomography",
        "category": "Hardware QPT",
        "role": "Characterize repeated-process tomography under synthetic SPAM/readout/shot noise.",
        "model": "Single-qubit PTM reconstruction with single-pass and multipass protocols.",
        "lesson": "Repeated blocks can amplify weak process signatures and improve reconstruction.",
        "limitations": "One-qubit synthetic prototype; not yet tied to a real backend.",
    },
    "quadrupolar_qip_2012": {
        "label": "Paper G",
        "title": "Quadrupolar nuclei for NMR quantum information processing",
        "category": "Encoded QIP",
        "role": "Interpret a spin-3/2 nucleus as an encoded two-qubit platform.",
        "model": "Product-operator decompositions, pseudo-pure states, Grover benchmark, synthetic QST.",
        "lesson": "Na-23 can be modeled both as quadrupolar NMR and as an encoded four-level QIP platform.",
        "limitations": "Ideal encoded operations are synthetic and require pulse-level implementation for experiments.",
    },
    "grape_nmr_control_2005": {
        "label": "Paper H",
        "title": "GRAPE NMR optimal control",
        "category": "Optimal control",
        "role": "Repair the selective-pulse failure mode with robust optimized pulses.",
        "model": "GRAPE unitary optimization over detuning and RF-scale ensemble members.",
        "lesson": "Robust pulse design is necessary for high-fidelity quadrupolar spin-3/2 operations.",
        "limitations": "Optimization is synthetic and does not yet include measured hardware transfer functions.",
    },
    "pps_optimal_control_2012": {
        "label": "Paper I",
        "title": "Pseudo-pure states in a quadrupolar spin system",
        "category": "State preparation",
        "role": "Prepare encoded pseudo-pure states using analytical averaging and optimal control.",
        "model": "Population averaging, GRAPE state preparation, gradient/dephasing step, QST validation.",
        "lesson": "The lab has a reproducible state-preparation layer before control or tomography experiments.",
        "limitations": "Synthetic preparation; real experiments need gradient, RF, and phase calibration.",
    },
    "projected_ls_qpt_2022": {
        "label": "Paper J",
        "title": "Projected least-squares QPT",
        "category": "Physical QPT",
        "role": "Enforce physicality in process tomography.",
        "model": "Raw Choi least squares compared with PSD and CPTP projections.",
        "lesson": "Projection reduces unphysical estimates and improves synthetic process reconstruction.",
        "limitations": "Projection is a statistical post-processing layer; it cannot fix bad experimental design alone.",
    },
    "gate_set_tomography_2021": {
        "label": "Paper K",
        "title": "Gate set tomography",
        "category": "SPAM-aware tomography",
        "role": "Separate predictive gate characterization from ideal-SPAM assumptions.",
        "model": "Minimal GST-like fitting of gates, preparation, and measurement through sequence probabilities.",
        "lesson": "Predictive probabilities are safer than direct gate parameters because GST has gauge freedom.",
        "limitations": "Minimal benchmark, not a full pyGSTi-level implementation.",
    },
    "nonmarkov_process_tensor_2020": {
        "label": "Paper L",
        "title": "Non-Markovian process tensor characterization and control",
        "category": "Multi-time memory",
        "role": "Escalation path when fixed Markovian channels fail.",
        "model": "Synthetic process tensor versus Markovian channel for multi-time prediction and control selection.",
        "lesson": "Memory-aware prediction can select different and better controls than Markovian modeling.",
        "limitations": "Synthetic correlated dephasing only; real process-tensor tomography is experimentally expensive.",
    },
    "noise_filtering_control_2014": {
        "label": "Paper M",
        "title": "Experimental noise filtering by quantum control",
        "category": "DD filtering",
        "role": "Treat pulse sequences as spectral filters.",
        "model": "Ramsey, Hahn, CPMG, and UDD filter functions under synthetic dephasing spectra.",
        "lesson": "Control can suppress noise by shifting filter sensitivity away from dominant spectral weight.",
        "limitations": "Ideal instantaneous pulses; finite-pulse errors must be added before lab claims.",
    },
    "dd_noise_spectroscopy_2011": {
        "label": "Paper N",
        "title": "Colored-noise spectroscopy by dynamical decoupling",
        "category": "DD spectroscopy",
        "role": "Invert DD coherence data into an effective dephasing spectrum.",
        "model": "Non-negative least-squares reconstruction from CPMG/UDD coherences.",
        "lesson": "DD data can reconstruct colored spectra and feed control-sequence decisions.",
        "limitations": "The inverse problem is ill-conditioned and depends on sequence coverage and pulse ideality.",
    },
    "flux_qubit_noise_spectroscopy_2011": {
        "label": "Paper O",
        "title": "Flux-qubit noise spectroscopy through DD",
        "category": "Hardware noise spectroscopy",
        "role": "Check that DD spectroscopy generalizes beyond Na-23 NMR.",
        "model": "CPMG peak-filter estimates fitted to a synthetic 1/f^alpha spectrum.",
        "lesson": "The spectroscopy layer is platform-independent in structure.",
        "limitations": "Synthetic flux-qubit-like data; not hardware-acquired data.",
    },
    "experimental_decision_pipeline": {
        "label": "Workflow",
        "title": "Experimental decision pipeline",
        "category": "Lab operations",
        "role": "Combine preparation, QST, DD spectroscopy, control selection, and lab-data comparison hooks.",
        "model": "Synthetic QST plus DD spectral inversion and candidate sequence scoring.",
        "lesson": "The paper reproductions now form a single operational decision loop.",
        "limitations": "Waiting for real lab data; current decision is synthetic.",
    },
}


PAPER_COMMENTARY: dict[str, dict[str, str]] = {
    "internal_validation_baseline": {
        "article_summary": "This is the laboratory's internal control experiment rather than an external article. It defines the minimum physical consistency conditions required before any paper reproduction or experimental interpretation is trusted.",
        "scientific_insights": "The central insight is methodological: a wrong commutator, non-Hermitian Hamiltonian, shifted synthetic transition, or non-positive density matrix would contaminate every later result. The baseline therefore treats algebra, spectra, and physical-state evolution as first-class scientific artifacts.",
        "laboratory_comparison": "The baseline is the reference layer against which all paper reproductions are compared. If a later paper seems to disagree with the platform, the first check is whether the baseline assumptions, units, phase conventions, or FFT conventions were changed.",
        "next_lab_use": "Before importing a new TNT file, pulse sequence, or tomography series, rerun the baseline and record the hashes in research memory.",
    },
    "na23_relaxometry_2023": {
        "article_summary": "The review organizes Na-23 relaxometry around the fact that Na-23 is a spin-3/2 quadrupolar nucleus whose relaxation is strongly shaped by electric-field-gradient fluctuations, correlation times, and spectral densities. It is mainly a conceptual and modeling foundation rather than a single-figure reproduction target.",
        "scientific_insights": "The important physics is that T1 and T2 are not arbitrary fitting constants: for quadrupolar nuclei they encode environmental motion through spectral densities. A phenomenological biexponential can fit an envelope, but it does not by itself identify a microscopic relaxation mechanism.",
        "laboratory_comparison": "Our lab comparison uses the current biexponential decay model as the empirical baseline and a reduced Redfield-inspired effective model as the interpretable extension. The synthetic fit shows that the empirical model can be matched qualitatively, but the interpretation should remain cautious until T1/T2 or tomography data arrive.",
        "next_lab_use": "Use this paper to define the language for the first real relaxation campaign: T1, T2, correlation time, quadrupolar coupling, spectral density, and regime of motion.",
    },
    "spin32_algebraic_2004": {
        "article_summary": "The algebraic spin-3/2 paper gives an operator-level description of quadrupolar NMR dynamics. It is directly aligned with this project because our platform is a four-level spin-3/2 system, and the paper's formalism maps naturally into Hilbert-space and Liouville-space propagation.",
        "scientific_insights": "The key insight is that spin-3/2 NMR is not just four unrelated levels. The algebra organizes RF rotations, quadrupolar evolution, coherence orders, and detection pathways into a structured model that can be tested numerically.",
        "laboratory_comparison": "Our reproduction directly compared Hilbert and Liouville propagation and found agreement at numerical precision. This supports using Liouville-space objects later for dissipators, superoperators, and process-level modeling.",
        "next_lab_use": "Use this formalism when translating experimental pulse sequences into code: define the operator basis first, then compare predicted coherence pathways with measured spectra or tomography amplitudes.",
    },
    "qst_relaxation_2008": {
        "article_summary": "This paper studies relaxation dynamics in a quadrupolar NMR system using quantum state tomography. Instead of inferring relaxation only from spectra or envelopes, it reconstructs density matrices over time and extracts rates from the evolution of populations and coherences.",
        "scientific_insights": "The major insight is identifiability: tomography separates population relaxation and coherence decay more directly than a single FID spectrum. It also exposes phase errors and reconstruction instability that a magnitude spectrum could hide.",
        "laboratory_comparison": "Our synthetic workflow reproduces the structure of the protocol: generate state trajectories, simulate QST signals, reconstruct density matrices, and fit rates. The noiseless recovery works essentially exactly, while noisy tests show how uncertainty propagates into fitted rates.",
        "next_lab_use": "This should be the template for the first serious experimental validation: collect the seven-phase tomography series at multiple delay times and compare reconstructed density-matrix trajectories to the synthetic model.",
    },
    "spin32_qlogic_qst_2005": {
        "article_summary": "This paper demonstrates spin-3/2 quadrupolar logical operations monitored by QST. Its relevance is not only the logic operation itself but the warning that finite pulse duration and quadrupolar evolution during the pulse can strongly affect the actual operation.",
        "scientific_insights": "The key insight is that a selective pulse is not automatically an ideal two-level gate embedded in a four-level system. During long pulses, the internal Hamiltonian keeps acting, and the intended transition-selective rotation can accumulate unwanted phases or leakage.",
        "laboratory_comparison": "Our benchmark compared pulses with and without internal quadrupolar evolution. The contrast was severe: the idealized model can look perfect while the physically evolved pulse fails. This made the later GRAPE reproduction necessary.",
        "next_lab_use": "Do not trust rectangular selective-pulse designs without simulating the full Hamiltonian during the pulse. Use QST to check the actual state after the pulse.",
    },
    "nonmarkov_noise_2022": {
        "article_summary": "The non-Markovian noise review frames the difference between memoryless effective dynamics and history-dependent dynamics. It motivates diagnostics such as trace-distance revivals, information backflow, negative time-local rates, and process-tensor approaches.",
        "scientific_insights": "The central insight is that a Lindblad equation is a model class, not a universal truth. Echo recovery, temporal correlations, or failure to predict multi-time data can reveal memory even when single-time decays look simple.",
        "laboratory_comparison": "Our synthetic benchmark created a memory-effective case and compared it against a Markovian fit. The Markovian model produced large residuals and failed echo predictions, giving concrete failure signatures for the lab.",
        "next_lab_use": "If repeated FIDs, echo experiments, or tomography trajectories show revival or history dependence, escalate from simple Lindblad fitting to memory models or process tensors.",
    },
    "multipass_qpt_2024": {
        "article_summary": "The multipass QPT paper studies process tomography where the same process is applied repeatedly. This can amplify process signatures relative to SPAM and sampling noise, improving characterization in some regimes.",
        "scientific_insights": "The key insight is experimental design: changing the number of passes changes the information content of the data. Repeated application is not just redundant measurement; it can expose weak process errors.",
        "laboratory_comparison": "Our one-qubit synthetic prototype compared single-pass and multipass PTM reconstruction under synthetic SPAM/readout/shot noise. The best multipass setting substantially reduced the mean reconstruction error.",
        "next_lab_use": "For gate-model hardware access, use multipass protocols as an optional amplification layer after basic QPT and GST are working.",
    },
    "quadrupolar_qip_2012": {
        "article_summary": "This paper reviews quantum information processing with quadrupolar nuclei in NMR. It treats a spin-3/2 nucleus as a four-level system that can encode two logical qubits and support pseudo-pure states, gates, and tomography.",
        "scientific_insights": "The important insight is the dual identity of the system: it is simultaneously a quadrupolar NMR object and an encoded two-qubit register. Product-operator decompositions make that connection explicit.",
        "laboratory_comparison": "Our reproduction validated the mapping from spin operators to encoded two-qubit product operators and reproduced ideal Grover-style behavior under synthetic assumptions. This links the Na-23 spectroscopy code to quantum-information protocols.",
        "next_lab_use": "Use this paper to decide how to label states, transitions, pseudo-pure preparations, and logical operations in future lab notes.",
    },
    "grape_nmr_control_2005": {
        "article_summary": "The GRAPE paper introduces gradient-based optimal control for NMR pulse design. It is the natural response to finite-pulse failures because it optimizes the full pulse shape under a modeled Hamiltonian rather than relying on ideal rectangular rotations.",
        "scientific_insights": "The central insight is that high-fidelity control is an optimization problem constrained by drift, control amplitudes, robustness requirements, and ensemble errors. Pulse design should include the physics that would otherwise appear as systematic gate error.",
        "laboratory_comparison": "Our reproduction directly compared a rectangular pulse to a GRAPE-optimized pulse on the spin-3/2 platform. The optimized pulse improved mean robustness-grid fidelity and fixed the failure mode exposed by Paper D.",
        "next_lab_use": "After measuring real B0/B1 offsets and RF limits, train GRAPE pulses against those calibrated uncertainties and validate them with QST.",
    },
    "pps_optimal_control_2012": {
        "article_summary": "This paper focuses on preparing pseudo-pure states in a quadrupolar spin system using optimal control. Pseudo-pure states are necessary because room-temperature NMR begins near a highly mixed thermal state with a small deviation component.",
        "scientific_insights": "The insight is that useful NMR quantum-information experiments operate on the deviation density matrix. State preparation is therefore about engineering the observable deviation component, not producing a truly pure thermodynamic state.",
        "laboratory_comparison": "Our implementation compared analytical population averaging and GRAPE-based preparation, followed by synthetic QST validation. Both reached near-perfect synthetic deviation fidelity under the modeled assumptions.",
        "next_lab_use": "Use this layer before any encoded algorithm or control experiment: prepare the target pseudo-pure state, apply gradient/dephasing if needed, then validate by QST.",
    },
    "projected_ls_qpt_2022": {
        "article_summary": "Projected least-squares QPT addresses the fact that raw process estimates from finite data can be non-physical. It projects estimates onto physically meaningful sets such as positive semidefinite and trace-preserving Choi matrices.",
        "scientific_insights": "The central insight is that physical constraints are not cosmetic. Enforcing complete positivity and trace preservation can reduce error and prevent impossible conclusions.",
        "laboratory_comparison": "Our synthetic benchmark showed raw Choi estimates with frequent physicality violations, while CPTP projection removed negative-eigenvalue violations and improved mean reconstruction error.",
        "next_lab_use": "Whenever process data are reconstructed from hardware, report both raw residuals and physicality-projected estimates.",
    },
    "gate_set_tomography_2021": {
        "article_summary": "Gate-set tomography models state preparation, gates, and measurements self-consistently. It avoids assuming that SPAM operations are ideal, which is often false in real hardware and can bias ordinary QPT.",
        "scientific_insights": "The key insight is that errors are gauge-structured. Direct gate matrices are not always uniquely meaningful, so predictive probabilities and held-out likelihoods are safer comparison targets.",
        "laboratory_comparison": "Our minimal GST-like benchmark compared ideal-SPAM gate-only fitting with self-consistent fitting. The GST model greatly improved held-out prediction accuracy.",
        "next_lab_use": "Use GST when hardware data show that preparation/readout errors cannot be ignored or when ordinary QPT gives inconsistent gate estimates.",
    },
    "nonmarkov_process_tensor_2020": {
        "article_summary": "The process-tensor paper demonstrates multi-time characterization and control in non-Markovian settings. Rather than describing a process by one fixed channel, it models how interventions at different times interact with memory.",
        "scientific_insights": "The central insight is that memory is operational: the best next control can depend on the previous controls. A single Markovian channel cannot represent that dependence.",
        "laboratory_comparison": "Our synthetic process-tensor benchmark predicted multi-time probabilities far better than a fixed Markovian model and selected a different, better control sequence.",
        "next_lab_use": "Escalate to process-tensor experiments only after simpler DD, QST, and Lindblad models fail; it is powerful but experimentally expensive.",
    },
    "noise_filtering_control_2014": {
        "article_summary": "This paper treats quantum control as noise filtering. Pulse sequences such as Ramsey, Hahn, CPMG, and UDD shape the spectral response of the qubit or spin to environmental noise.",
        "scientific_insights": "The key insight is spectral selectivity. Control sequences are filters in frequency space, so preserving coherence means aligning the filter with low-noise regions or rejecting dominant noise bands.",
        "laboratory_comparison": "Our benchmark computed filter functions and coherences under synthetic noise. It showed strong coherence gain from DD relative to Ramsey, establishing the basis for spectroscopy and control selection.",
        "next_lab_use": "Use filter-function plots to choose initial DD sequences before attempting full noise-spectrum inversion.",
    },
    "dd_noise_spectroscopy_2011": {
        "article_summary": "This paper uses dynamical decoupling not only to suppress noise but to measure its spectrum. Different pulse sequences sample different spectral bands, allowing reconstruction of colored noise from coherence measurements.",
        "scientific_insights": "The central insight is inversion: coherence decay under known filters can be converted into constraints on S(omega). The problem is ill-conditioned, so positivity and sequence coverage matter.",
        "laboratory_comparison": "Our NNLS reconstruction recovered the broad colored structure and localized a narrow spectral feature within the synthetic grid resolution. This method feeds the experimental-decision pipeline.",
        "next_lab_use": "Collect coherence under a planned family of CPMG/UDD sequences, reconstruct the spectrum, then select the sequence predicted to preserve coherence best.",
    },
    "flux_qubit_noise_spectroscopy_2011": {
        "article_summary": "This paper applies DD noise spectroscopy to a superconducting flux qubit and estimates a 1/f-like noise spectrum. It matters for this project because it shows that the DD spectroscopy logic is not platform-specific.",
        "scientific_insights": "The insight is portability: if the control filters and coherence model are known, the same inverse logic can apply to NMR spins or superconducting qubits, with platform-specific calibration.",
        "laboratory_comparison": "Our synthetic flux-qubit-like benchmark estimated the exponent alpha from peak-filter samples. It validates the repository's hardware-facing direction beyond Na-23.",
        "next_lab_use": "Use this as the bridge when Ygor has access to gate-model quantum hardware: treat coherence experiments as spectral probes, not only as benchmark scores.",
    },
    "experimental_decision_pipeline": {
        "article_summary": "The pipeline is not a paper; it is the operational synthesis of the papers. It prepares a state, validates QST, simulates or ingests DD coherences, reconstructs an effective spectrum, chooses a control sequence, and prepares comparison templates for real data.",
        "scientific_insights": "The insight is that research must become a decision loop. The lab should not only simulate papers; it should decide what to measure next and how to falsify or refine the model.",
        "laboratory_comparison": "The current synthetic run selects CPMG-24 and records the status as waiting for lab data. Once real coherences arrive, the same pipeline reports residuals and decides whether the model is sufficient.",
        "next_lab_use": "Use this as the default entry point for incoming experiments: fill the manifest, run the pipeline, inspect residuals, and update research memory.",
    },
}


BASE_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    ("Open-system Na-23 simulation", "outputs/nmr_open_simulation.json", "Physical trace/Hermiticity/positivity checks for dense Liouvillian propagation."),
    ("Open-system Na-23 simulation plot", "outputs/nmr_open_simulation.png", "Visual artifact for the open-system Na-23 simulation."),
    ("Noise-free synthetic dissipation fit", "outputs/nmr_synthetic_dissipation_fit.json", "Synthetic parameter-recovery validation for gamma_phi and gamma_relax."),
    ("Noise-free synthetic dissipation fit plot", "outputs/nmr_synthetic_dissipation_fit.png", "Visual comparison for the synthetic dissipation fit."),
    ("Synthetic validation suite", "outputs/nmr_validation_suite.json", "Noise robustness sweep for dissipation-rate recovery."),
    ("Synthetic validation suite plot", "outputs/nmr_validation_suite.png", "Visual summary of robustness versus synthetic noise."),
    ("Reference FID diagnostic fit", "outputs/nmr_reference_dissipation_fit.json", "Diagnostic fit against the current real reference TNT FID."),
    ("Reference FID diagnostic fit plot", "outputs/nmr_reference_dissipation_fit.png", "Visual comparison for the diagnostic reference-data fit."),
    ("NMR tomography pipeline", "outputs/nmr_tomography_pipeline.json", "Synthetic tomography extraction and reconstruction validation."),
    ("NMR tomography pipeline plot", "outputs/nmr_tomography_pipeline.png", "Visual tomography-pipeline artifact."),
    ("Open qubit demo", "outputs/open_qubit_demo.json", "Generic open-system qubit thermodynamic/dissipative demonstration."),
    ("Open qubit demo plot", "outputs/open_qubit_demo.png", "Visual open-qubit demo artifact."),
    ("Lab manual", "docs/LAB_MANUAL.md", "Canonical human-readable description of the laboratory, validation policy, and experimental workflow."),
    ("Paper registry", "repro/paper_registry.yaml", "Canonical list of reproduced papers and internal baselines."),
    ("Reproduction manifest", "repro/repro_manifest.yaml", "Machine-readable reproduction manifest."),
    ("Research memory summary", "lab/research_memory/SUMMARY.md", "Generated memory of completed paper/workflow artifacts."),
    ("Research memory index", "lab/research_memory/index.json", "Compact index of reproducible records."),
    ("Locked requirements", "requirements.lock.txt", "Pinned Python dependency baseline."),
    ("Project metadata", "pyproject.toml", "Package and test configuration."),
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latex_escape(text: object) -> str:
    raw = str(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in raw)


def latex_path(path: Path) -> str:
    return path.relative_to(REPORT_DIR).as_posix()


def pretty_metric_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 1e4 or (0 < abs(value) < 1e-3):
            return f"{value:.4e}"
        return f"{value:.6g}"
    return str(value)


def copy_base_artifacts() -> list[dict[str, Any]]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for label, relative, role in BASE_ARTIFACTS:
        source = ROOT / relative
        if not source.exists():
            records.append(
                {
                    "label": label,
                    "source": relative,
                    "snapshot": None,
                    "role": role,
                    "exists": False,
                    "bytes": 0,
                    "sha256": None,
                }
            )
            continue
        target = ARTIFACT_DIR / Path(relative).name
        if source.suffix.lower() in {".png", ".json"}:
            shutil.copy2(source, target)
            snapshot = target.relative_to(REPORT_DIR).as_posix()
        else:
            snapshot = None
        records.append(
            {
                "label": label,
                "source": relative,
                "snapshot": snapshot,
                "role": role,
                "exists": True,
                "bytes": int(source.stat().st_size),
                "sha256": sha256_file(source),
            }
        )
    return records


def flatten_metrics(payload: dict[str, Any], prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in payload.items():
        next_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten_metrics(value, next_key))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out[next_key] = float(value)
    return out


def source_dir_for(source_id: str) -> Path:
    repro_dir = ROOT / "outputs" / "repro" / source_id / "latest"
    if repro_dir.exists():
        return repro_dir
    return ROOT / "outputs" / "workflows" / source_id / "latest"


def figures_for(source_id: str) -> list[Path]:
    source = source_dir_for(source_id)
    if not source.exists():
        return []
    return sorted(source.rglob("*.png"))


def metrics_for(source_id: str) -> dict[str, Any]:
    return read_json(source_dir_for(source_id) / "metrics.json")


def copy_figures_to_report() -> dict[str, list[Path]]:
    copied: dict[str, list[Path]] = {}
    for source_id in PAPER_ORDER:
        source_figs = figures_for(source_id)
        target_dir = FIGURE_DIR / source_id
        target_dir.mkdir(parents=True, exist_ok=True)
        copied[source_id] = []
        for fig_path in source_figs:
            target = target_dir / fig_path.name
            target.write_bytes(fig_path.read_bytes())
            copied[source_id].append(target)
    return copied


def choose_key_metrics(source_id: str, flat: dict[str, float]) -> list[tuple[str, float]]:
    preference = [
        "best_fit.global_envelope_rmse",
        "hilbert_vs_liouville.max_abs_fid_error",
        "noiseless_reconstruction.mean_fidelity",
        "noiseless_reconstruction.gamma_population_estimate",
        "fidelity_summary.min_operator_fidelity_with_quadrupolar",
        "failure_metrics.blp_measure",
        "failure_metrics.markovian_fit_rmse",
        "runner_summary.best_improvement_factor",
        "runner_summary.min_grover_deviation_fidelity",
        "optimization.final_training_mean_fidelity",
        "robustness_grid.grape.mean",
        "grape_preparation.final_preparation_error",
        "grape_preparation.final_deviation_fidelity",
        "error_summary.cptp_choi_error.mean",
        "physicality_summary.cptp_negative_fraction",
        "prediction_summary.heldout_improvement_factor",
        "prediction_summary.heldout_rmse_gst",
        "prediction_summary.improvement_factor",
        "control_summary.true_control_advantage",
        "runner_summary.best_gain_vs_ramsey",
        "reconstruction_summary.spectrum_correlation",
        "reconstruction_summary.relative_spectrum_error",
        "spectroscopy_summary.estimated_alpha",
        "spectroscopy_summary.alpha_abs_error",
        "state_preparation_summary.qst_fidelity",
        "decision_summary.selected_predicted_coherence",
    ]
    rows = [(name, flat[name]) for name in preference if name in flat]
    if rows:
        return rows[:6]
    return list(flat.items())[:6]


def plot_figure_count(copied: dict[str, list[Path]]) -> Path:
    labels = [PAPER_META[item]["label"] for item in PAPER_ORDER if copied.get(item)]
    counts = [len(copied[item]) for item in PAPER_ORDER if copied.get(item)]
    path = FIGURE_DIR / "comparison_figure_count.png"
    fig, ax = plt.subplots(figsize=(11.2, 5.2), constrained_layout=True)
    ax.bar(labels, counts, color="#284b63")
    ax.set_title("Visual artifact coverage by reproduction/workflow")
    ax.set_ylabel("number of generated plots included in the article")
    ax.set_xlabel("paper or workflow")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_quality_metrics() -> Path:
    candidates = [
        ("Paper C QST fidelity", "qst_relaxation_2008", "noiseless_reconstruction.mean_fidelity"),
        ("Paper G QST fidelity", "quadrupolar_qip_2012", "runner_summary.qst_noise_0p02_deviation_fidelity_mean"),
        ("Paper H GRAPE mean", "grape_nmr_control_2005", "robustness_grid.grape.mean"),
        ("Paper I PPS fidelity", "pps_optimal_control_2012", "grape_preparation.final_deviation_fidelity"),
        ("Paper K GST heldout score", "gate_set_tomography_2021", "prediction_summary.heldout_improvement_factor"),
        ("Paper L PT improvement", "nonmarkov_process_tensor_2020", "prediction_summary.improvement_factor"),
        ("Paper N spectrum corr.", "dd_noise_spectroscopy_2011", "reconstruction_summary.spectrum_correlation"),
        ("Paper O alpha score", "flux_qubit_noise_spectroscopy_2011", "spectroscopy_summary.alpha_abs_error"),
        ("Pipeline QST fidelity", "experimental_decision_pipeline", "state_preparation_summary.qst_fidelity"),
        ("Pipeline spectrum corr.", "experimental_decision_pipeline", "spectroscopy_summary.spectrum_correlation"),
    ]
    labels: list[str] = []
    values: list[float] = []
    for label, source_id, metric_key in candidates:
        flat = flatten_metrics(metrics_for(source_id))
        if metric_key not in flat:
            continue
        value = flat[metric_key]
        if metric_key.endswith("heldout_improvement_factor"):
            value = min(value / 10.0, 1.0)
        elif metric_key.endswith("improvement_factor"):
            value = min(value / 15.0, 1.0)
        elif metric_key.endswith("alpha_abs_error"):
            true_alpha = 0.78
            value = max(0.0, 1.0 - value / true_alpha)
        labels.append(label)
        values.append(float(value))
    path = FIGURE_DIR / "comparison_quality_scores.png"
    fig, ax = plt.subplots(figsize=(11.5, 5.6), constrained_layout=True)
    ax.bar(labels, values, color="#2a9d8f")
    ax.set_title("Direct comparison of normalized quality-style scores")
    ax.set_ylabel("normalized score, higher is better")
    ax.set_ylim(0.0, 1.08)
    ax.tick_params(axis="x", rotation=50)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_improvement_factors() -> Path:
    rows = [
        ("Paper F multipass QPT", "multipass_qpt_2024", "runner_summary.best_improvement_factor"),
        ("Paper H GRAPE/rect.", "grape_nmr_control_2005", "robustness_grid.mean_improvement"),
        ("Paper J CPTP/raw", "projected_ls_qpt_2022", "error_summary.mean_error_improvement_raw_to_cptp"),
        ("Paper K GST/ideal-SPAM", "gate_set_tomography_2021", "prediction_summary.heldout_improvement_factor"),
        ("Paper L PT/Markov", "nonmarkov_process_tensor_2020", "prediction_summary.improvement_factor"),
        ("Paper M DD/Ramsey", "noise_filtering_control_2014", "runner_summary.best_gain_vs_ramsey"),
    ]
    labels: list[str] = []
    values: list[float] = []
    for label, source_id, metric_key in rows:
        flat = flatten_metrics(metrics_for(source_id))
        if metric_key not in flat:
            continue
        value = flat[metric_key]
        if source_id == "grape_nmr_control_2005":
            rect = flat.get("robustness_grid.rectangular.mean")
            grape = flat.get("robustness_grid.grape.mean")
            if rect and rect > 0:
                value = grape / rect
        labels.append(label)
        values.append(float(value))
    path = FIGURE_DIR / "comparison_improvement_factors.png"
    fig, ax = plt.subplots(figsize=(11.0, 5.3), constrained_layout=True)
    ax.bar(labels, values, color="#e76f51")
    ax.set_title("Direct comparison of improvement factors across benchmarks")
    ax.set_ylabel("improvement factor")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def plot_error_metrics() -> Path:
    rows = [
        ("Paper A envelope RMSE", "na23_relaxometry_2023", "best_fit.global_envelope_rmse"),
        ("Paper E Markov RMSE", "nonmarkov_noise_2022", "failure_metrics.markovian_fit_rmse"),
        ("Paper J CPTP Choi error", "projected_ls_qpt_2022", "error_summary.cptp_choi_error.mean"),
        ("Paper K GST heldout RMSE", "gate_set_tomography_2021", "prediction_summary.heldout_rmse_gst"),
        ("Paper L PT RMSE", "nonmarkov_process_tensor_2020", "prediction_summary.process_tensor_validation_rmse"),
        ("Paper N relative spectrum error", "dd_noise_spectroscopy_2011", "reconstruction_summary.relative_spectrum_error"),
        ("Paper O alpha error", "flux_qubit_noise_spectroscopy_2011", "spectroscopy_summary.alpha_abs_error"),
        ("Pipeline spectrum error", "experimental_decision_pipeline", "spectroscopy_summary.relative_spectrum_error"),
    ]
    labels: list[str] = []
    values: list[float] = []
    for label, source_id, metric_key in rows:
        flat = flatten_metrics(metrics_for(source_id))
        if metric_key in flat:
            labels.append(label)
            values.append(max(float(flat[metric_key]), 1e-16))
    path = FIGURE_DIR / "comparison_error_metrics.png"
    fig, ax = plt.subplots(figsize=(11.5, 5.5), constrained_layout=True)
    ax.bar(labels, values, color="#6d597a")
    ax.set_yscale("log")
    ax.set_title("Heterogeneous reported error metrics, log scale")
    ax.set_ylabel("reported error or residual, lower is better")
    ax.tick_params(axis="x", rotation=50)
    ax.grid(axis="y", alpha=0.25, which="both")
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def write_comparison_sections(copied: dict[str, list[Path]], comparison_figures: list[Path]) -> None:
    lines = [
        "% Auto-generated by scripts/generate_review_article_assets.py",
        r"\section{Direct Cross-Paper Visual Comparison}",
        "",
        "This section compares the reproduced papers as a laboratory stack rather",
        "than as isolated articles.  The metrics are heterogeneous: fidelities,",
        "correlations, RMSEs, improvement factors, and physicality diagnostics do",
        "not represent the same observable.  The comparison is therefore used to",
        "locate what each paper contributes to the laboratory, not to rank papers",
        "scientifically.",
        "",
    ]
    captions = {
        "comparison_figure_count.png": "Number of plot artifacts available for each reproduction or workflow. This is a reproducibility-coverage diagnostic.",
        "comparison_quality_scores.png": "Normalized quality-style scores. Fidelity and correlation metrics are already in [0,1]; selected improvement metrics are rescaled only for visual comparison.",
        "comparison_improvement_factors.png": "Direct comparison of reported improvement factors: optimized control, constrained tomography, GST, process tensors, and DD filtering improve different failure modes.",
        "comparison_error_metrics.png": "Heterogeneous reported errors on a logarithmic scale. These errors are not interchangeable but reveal where each benchmark measures residual model mismatch.",
    }
    for fig_path in comparison_figures:
        lines.extend(
            [
                r"\begin{figure}[p]",
                r"  \centering",
                rf"  \includegraphics[width=0.92\textwidth]{{{latex_path(fig_path)}}}",
                rf"  \caption{{{latex_escape(captions.get(fig_path.name, fig_path.stem))}}}",
                r"\end{figure}",
                "",
            ]
        )

    lines.extend(
        [
            r"\begin{longtable}{p{0.18\textwidth}p{0.20\textwidth}p{0.18\textwidth}p{0.34\textwidth}}",
            r"\toprule",
            r"\textbf{ID} & \textbf{Category} & \textbf{Plots} & \textbf{Main comparison role}\\",
            r"\midrule",
            r"\endhead",
        ]
    )
    for source_id in PAPER_ORDER:
        meta = PAPER_META[source_id]
        lines.append(
            rf"{latex_escape(meta['label'])} & {latex_escape(meta['category'])} & {len(copied.get(source_id, []))} & {latex_escape(meta['role'])}\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])
    (GENERATED_DIR / "direct_comparison_sections.tex").write_text("\n".join(lines), encoding="utf-8")


def write_expanded_sections(copied: dict[str, list[Path]]) -> None:
    lines = [
        "% Auto-generated by scripts/generate_review_article_assets.py",
        r"\section{Expanded Paper-by-Paper Reproduction Analysis}",
        "",
        "Each subsection below follows the same structure: physical role,",
        "implemented model, direct comparison target, key metrics, limitations,",
        "and project-level value.  This is the part of the report that should be",
        "read before deciding what to measure next in the laboratory.",
        "",
    ]
    for source_id in PAPER_ORDER:
        meta = PAPER_META[source_id]
        commentary = PAPER_COMMENTARY[source_id]
        metrics = metrics_for(source_id)
        flat = flatten_metrics(metrics)
        key_metrics = choose_key_metrics(source_id, flat)
        lines.extend(
            [
                rf"\subsection{{{latex_escape(meta['label'])}: {latex_escape(meta['title'])}}}",
                rf"\textbf{{Category.}} {latex_escape(meta['category'])}.",
                "",
                rf"\textbf{{Article summary.}} {latex_escape(commentary['article_summary'])}",
                "",
                rf"\textbf{{Scientific insights.}} {latex_escape(commentary['scientific_insights'])}",
                "",
                rf"\textbf{{Role.}} {latex_escape(meta['role'])}",
                "",
                rf"\textbf{{Implemented model.}} {latex_escape(meta['model'])}",
                "",
                rf"\textbf{{Laboratory comparison.}} {latex_escape(commentary['laboratory_comparison'])}",
                "",
                rf"\textbf{{Project lesson.}} {latex_escape(meta['lesson'])}",
                "",
                rf"\textbf{{Next laboratory use.}} {latex_escape(commentary['next_lab_use'])}",
                "",
                rf"\textbf{{Known limitations.}} {latex_escape(meta['limitations'])}",
                "",
                rf"\textbf{{Generated plots included.}} {len(copied.get(source_id, []))}.",
                "",
            ]
        )
        if key_metrics:
            lines.extend(
                [
                    r"\begin{center}",
                    r"\begin{tabular}{lr}",
                    r"\toprule",
                    r"\textbf{Metric} & \textbf{Value}\\",
                    r"\midrule",
                ]
            )
            for name, value in key_metrics:
                lines.append(rf"{latex_escape(name)} & {latex_escape(pretty_metric_value(value))}\\")
            lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{center}", ""])
        else:
            lines.append("No numeric metrics were available in the current metrics file.\n")
    (GENERATED_DIR / "expanded_paper_sections.tex").write_text("\n".join(lines), encoding="utf-8")


def write_figure_atlas(copied: dict[str, list[Path]]) -> None:
    lines = [
        "% Auto-generated by scripts/generate_review_article_assets.py",
        r"\section{Complete Figure Atlas From Reproductions and Workflows}",
        "",
        "This appendix includes every PNG artifact generated by the current",
        "paper-reproduction and workflow layer.  The figures are grouped by paper",
        "or workflow and are included from copied report-local artifacts so that",
        "the article can be compiled without depending on absolute paths.",
        "",
    ]
    for source_id in PAPER_ORDER:
        figs = copied.get(source_id, [])
        if not figs:
            continue
        meta = PAPER_META[source_id]
        lines.extend(
            [
                rf"\subsection{{{latex_escape(meta['label'])}: {latex_escape(meta['title'])}}}",
                "",
            ]
        )
        for fig_path in figs:
            caption_name = fig_path.stem.replace("_", " ")
            lines.extend(
                [
                    r"\begin{figure}[p]",
                    r"  \centering",
                    rf"  \includegraphics[width=0.93\textwidth]{{{latex_path(fig_path)}}}",
                    rf"  \caption{{{latex_escape(meta['label'])}: {latex_escape(caption_name)}.}}",
                    r"\end{figure}",
                    "",
                ]
            )
        lines.append(r"\clearpage")
        lines.append("")
    (GENERATED_DIR / "complete_figure_atlas.tex").write_text("\n".join(lines), encoding="utf-8")


def json_metric(path: str, *keys: str) -> Any:
    payload = read_json(ROOT / path)
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def experimental_metric_rows() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    def add(label: str, value: Any, meaning: str) -> None:
        if value is not None:
            rows.append((label, pretty_metric_value(value), meaning))

    add(
        "Open-system max trace error",
        json_metric("outputs/nmr_open_simulation.json", "checks", "max_trace_error"),
        "Trace preservation under dense Liouvillian propagation.",
    )
    add(
        "Open-system max Hermiticity error",
        json_metric("outputs/nmr_open_simulation.json", "checks", "max_hermiticity_error"),
        "Numerical Hermiticity preservation.",
    )
    add(
        "Open-system minimum eigenvalue",
        json_metric("outputs/nmr_open_simulation.json", "checks", "min_eigenvalue"),
        "Positivity floor for the tested trajectory.",
    )
    add(
        "Synthetic fitted gamma_phi",
        json_metric("outputs/nmr_synthetic_dissipation_fit.json", "fitted_rates", "gamma_phi_s^-1"),
        "Noise-free recovery of dephasing rate.",
    )
    add(
        "Synthetic fitted gamma_relax",
        json_metric("outputs/nmr_synthetic_dissipation_fit.json", "fitted_rates", "gamma_relax_s^-1"),
        "Noise-free recovery of relaxation rate.",
    )
    add(
        "Validation-suite success count",
        json_metric("outputs/nmr_validation_suite.json", "success_count"),
        "Number of synthetic robustness cases that converged.",
    )
    add(
        "Validation-suite median gamma_phi relative error",
        json_metric("outputs/nmr_validation_suite.json", "summary", "median_relative_error_gamma_phi"),
        "Typical dephasing-rate recovery error under tested noise.",
    )
    add(
        "Validation-suite median gamma_relax relative error",
        json_metric("outputs/nmr_validation_suite.json", "summary", "median_relative_error_gamma_relax"),
        "Typical relaxation-rate recovery error under tested noise.",
    )
    add(
        "Reference-fit normalized FID RMSE",
        json_metric("outputs/nmr_reference_dissipation_fit.json", "normalized_rmse", "fid"),
        "Diagnostic mismatch against the current real TNT reference FID.",
    )
    add(
        "Reference-fit gamma_phi",
        json_metric("outputs/nmr_reference_dissipation_fit.json", "fitted_rates", "gamma_phi_s^-1"),
        "Effective transverse decay from one-FID diagnostic fit.",
    )
    add(
        "Reference-fit gamma_relax",
        json_metric("outputs/nmr_reference_dissipation_fit.json", "fitted_rates", "gamma_relax_s^-1"),
        "Not interpretable as final T1 identification from one FID.",
    )
    add(
        "Tomography-pipeline fidelity",
        json_metric("outputs/nmr_tomography_pipeline.json", "fidelity"),
        "Synthetic QST reconstruction fidelity.",
    )
    add(
        "Tomography-pipeline residual norm",
        json_metric("outputs/nmr_tomography_pipeline.json", "residual_norm"),
        "Linear tomography residual.",
    )
    add(
        "Open-qubit final purity",
        json_metric("outputs/open_qubit_demo.json", "final_purity"),
        "Generic two-level dissipative demonstration.",
    )
    add(
        "Open-qubit final entropy",
        json_metric("outputs/open_qubit_demo.json", "final_entropy"),
        "Entropy after open-qubit evolution.",
    )
    return rows


def write_experimental_simulation_sections(base_records: list[dict[str, Any]]) -> None:
    png_records = [
        record for record in base_records
        if record["exists"] and str(record["snapshot"]).lower().endswith(".png")
    ]
    lines = [
        "% Auto-generated by scripts/generate_review_article_assets.py",
        r"\section{Experimental Simulation, Base, and Validation Artifacts}",
        "",
        "This section documents the artifacts that are not tied to a single",
        "external paper but are essential for turning the repository into a",
        "laboratory.  These files validate the base machinery, run synthetic",
        "experimental simulations, perform diagnostic fitting against the current",
        "reference FID, and preserve the configuration/registry layer needed for",
        "auditable work.",
        "",
        r"\subsection{Core Experimental-Simulation Metrics}",
        "",
        r"\begin{longtable}{p{0.34\textwidth}p{0.18\textwidth}p{0.38\textwidth}}",
        r"\toprule",
        r"\textbf{Metric} & \textbf{Value} & \textbf{Interpretation}\\",
        r"\midrule",
        r"\endhead",
    ]
    for label, value, meaning in experimental_metric_rows():
        lines.append(rf"{latex_escape(label)} & {latex_escape(value)} & {latex_escape(meaning)}\\")
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])

    lines.extend(
        [
            r"\subsection{Base Artifact Inventory}",
            "",
            "The following inventory is copied into the report directory as an",
            "artifact snapshot.  Hashes point to the source artifact at generation",
            "time.",
            "",
            r"\begin{longtable}{p{0.22\textwidth}p{0.28\textwidth}p{0.12\textwidth}p{0.28\textwidth}}",
            r"\toprule",
            r"\textbf{Artifact} & \textbf{Source path} & \textbf{Bytes} & \textbf{SHA256 prefix}\\",
            r"\midrule",
            r"\endhead",
        ]
    )
    for record in base_records:
        status = record["bytes"] if record["exists"] else "missing"
        sha = str(record["sha256"])[:16] if record["sha256"] else "missing"
        lines.append(
            rf"{latex_escape(record['label'])} & \texttt{{{latex_escape(record['source'])}}} & {latex_escape(status)} & \texttt{{{latex_escape(sha)}}}\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])

    lines.extend(
        [
            r"\subsection{Experimental-Simulation Figures}",
            "",
            "These figures are the base simulation and validation plots.  The",
            "paper-specific figure atlas appears later in the appendix.",
            "",
        ]
    )
    for record in png_records:
        lines.extend(
            [
                r"\begin{figure}[p]",
                r"  \centering",
                rf"  \includegraphics[width=0.92\textwidth]{{{record['snapshot']}}}",
                rf"  \caption{{{latex_escape(record['label'])}. {latex_escape(record['role'])}}}",
                r"\end{figure}",
                "",
            ]
        )
    (GENERATED_DIR / "experimental_simulation_sections.tex").write_text("\n".join(lines), encoding="utf-8")


def write_reading_copy(copied: dict[str, list[Path]], comparison_figures: list[Path]) -> None:
    lines = [
        "# Generated Visual Atlas",
        "",
        "This file is generated by `scripts/generate_review_article_assets.py`.",
        "",
        "## Direct comparison figures",
        "",
    ]
    for fig in comparison_figures:
        lines.append(f"- `{fig.relative_to(ROOT)}`")
    lines.extend(["", "## Paper/workflow figure coverage", ""])
    for source_id in PAPER_ORDER:
        meta = PAPER_META[source_id]
        lines.append(f"### {meta['label']}: {meta['title']}")
        lines.append("")
        for fig in copied.get(source_id, []):
            lines.append(f"- `{fig.relative_to(ROOT)}`")
        lines.append("")
    lines.extend(["## Base and validation artifacts", ""])
    for label, relative, role in BASE_ARTIFACTS:
        exists = (ROOT / relative).exists()
        status = "present" if exists else "missing"
        lines.append(f"- `{relative}` [{status}] - {role}")
    (GENERATED_DIR / "VISUAL_ATLAS_READING_COPY.md").write_text("\n".join(lines), encoding="utf-8")


def write_clean_paper_docs(copied: dict[str, list[Path]]) -> None:
    CLEAN_PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    for source_id in PAPER_ORDER:
        meta = PAPER_META[source_id]
        commentary = PAPER_COMMENTARY[source_id]
        metrics = metrics_for(source_id)
        flat = flatten_metrics(metrics)
        key_metrics = choose_key_metrics(source_id, flat)
        filename = f"{source_id}.md"

        lines = [
            f"# {meta['label']}: {meta['title']}",
            "",
            f"Paper/workflow ID: `{source_id}`",
            "",
            f"Category: `{meta['category']}`",
            "",
            "## Article Summary",
            "",
            commentary["article_summary"],
            "",
            "## Scientific Insights",
            "",
            commentary["scientific_insights"],
            "",
            "## Implemented Laboratory Model",
            "",
            meta["model"],
            "",
            "## Direct Laboratory Comparison",
            "",
            commentary["laboratory_comparison"],
            "",
            "## Project Lesson",
            "",
            meta["lesson"],
            "",
            "## Next Laboratory Use",
            "",
            commentary["next_lab_use"],
            "",
            "## Known Limitations",
            "",
            meta["limitations"],
            "",
            "## Key Metrics",
            "",
        ]
        if key_metrics:
            for name, value in key_metrics:
                lines.append(f"- `{name}`: `{pretty_metric_value(value)}`")
        else:
            lines.append("- No numeric metrics are currently available.")
        lines.extend(["", "## Generated Figures", ""])
        if copied.get(source_id):
            for fig_path in copied[source_id]:
                source_relative = fig_path.relative_to(REPORT_DIR)
                lines.append(f"- `{source_relative.as_posix()}`")
        else:
            lines.append("- No generated figures are currently available.")
        lines.extend(
            [
                "",
                "## Canonical Artifacts",
                "",
                f"- Metrics: `{source_dir_for(source_id).relative_to(ROOT).as_posix()}/metrics.json`",
                f"- Config: `{source_dir_for(source_id).relative_to(ROOT).as_posix()}/config_used.json`",
                f"- Results: `{source_dir_for(source_id).relative_to(ROOT).as_posix()}/results.json`",
                "",
            ]
        )
        (CLEAN_PAPERS_DIR / filename).write_text("\n".join(lines), encoding="utf-8")


def write_lab_manual(base_records: list[dict[str, Any]]) -> None:
    rows = experimental_metric_rows()
    lines = [
        "# Open Quantum Control Lab Manual",
        "",
        "This is the canonical compact documentation file for the Python-first lab.",
        "Old planning notes and duplicate result Markdown files were intentionally removed.",
        "",
        "## Goal",
        "",
        "Build a reproducible laboratory for control and identification of dissipative dynamics in open quantum systems, starting from spin-3/2 Na-23 NMR and extending toward hardware characterization.",
        "",
        "## Canonical Reading Order",
        "",
        "1. `README.md` for quick start.",
        "2. `docs/LAB_MANUAL.md` for the lab structure and validation rules.",
        "3. `docs/papers/` for one Markdown file per reproduced paper/workflow.",
        "4. `reports/review_article/open_quantum_control_review.pdf` for the full review-style report with plots.",
        "",
        "## Repository Roles",
        "",
        "- `src/oqs_control/`: validated code.",
        "- `scripts/`: one-command runs and build utilities.",
        "- `outputs/repro/`: JSON/PNG artifacts from paper reproductions.",
        "- `outputs/workflows/`: JSON/PNG artifacts from operational workflows.",
        "- `docs/papers/`: one Markdown file per paper/workflow.",
        "- `reports/review_article/`: publication-style LaTeX/PDF report.",
        "- `lab/research_memory/`: generated research memory.",
        "",
        "## Validation Policy",
        "",
        "- Synthetic validation tests the machinery.",
        "- Diagnostic real-data fits are not final physical identification.",
        "- Microscopic dissipative mechanisms require multiple calibrated datasets.",
        "- New lab data must include metadata, uncertainty, and a manifest.",
        "",
        "## Current Base Simulation Metrics",
        "",
    ]
    for label, value, meaning in rows:
        lines.append(f"- `{label}`: `{value}` - {meaning}")
    lines.extend(
        [
            "",
            "## Base Artifact Inventory",
            "",
        ]
    )
    for record in base_records:
        status = "present" if record["exists"] else "missing"
        sha = str(record["sha256"])[:16] if record["sha256"] else "missing"
        lines.append(f"- `{record['source']}` [{status}, sha256 prefix `{sha}`] - {record['role']}")
    lines.extend(
        [
            "",
            "## Paper And Workflow Notes",
            "",
        ]
    )
    for source_id in PAPER_ORDER:
        meta = PAPER_META[source_id]
        lines.append(f"- `{meta['label']}`: `docs/papers/{source_id}.md` - {meta['title']}")
    lines.extend(
        [
            "",
            "## Main Commands",
            "",
            "```powershell",
            "$env:PYTHONPATH='src'",
            "python -m pytest -q",
            "python scripts\\run_experimental_decision_pipeline.py",
            "python scripts\\research_memory_agent.py",
            "python scripts\\build_review_article.py",
            "```",
            "",
            "## Incoming Lab Data Rule",
            "",
            "Use the generated lab manifest from the experimental decision pipeline. If measured coherences or QST observables disagree with the model outside uncertainty, escalate the model instead of forcing a fit.",
            "",
        ]
    )
    (CLEAN_DOCS_DIR / "LAB_MANUAL.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    base_records = copy_base_artifacts()
    copied = copy_figures_to_report()
    comparison_figures = [
        plot_figure_count(copied),
        plot_quality_metrics(),
        plot_improvement_factors(),
        plot_error_metrics(),
    ]
    write_comparison_sections(copied, comparison_figures)
    write_experimental_simulation_sections(base_records)
    write_expanded_sections(copied)
    write_figure_atlas(copied)
    write_clean_paper_docs(copied)
    write_lab_manual(base_records)
    print(
        json.dumps(
            {
                "status": "completed",
                "source_count": len(PAPER_ORDER),
                "figure_count": sum(len(value) for value in copied.values()),
                "base_artifact_count": len(base_records),
                "comparison_figure_count": len(comparison_figures),
                "generated_dir": str(GENERATED_DIR),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
