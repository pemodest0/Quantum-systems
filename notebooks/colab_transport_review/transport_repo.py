from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REFERENCE_ROWS = [
    {
        "topic": "CTQW on networks",
        "citation": "Mülken & Blumen (2011)",
        "doi": "10.1016/j.physrep.2011.01.002",
        "why_it_matters": "Foundational review for continuous-time quantum walks on complex networks.",
    },
    {
        "topic": "Target placement",
        "citation": "Razzoli, Paris & Bordone (2021)",
        "doi": "10.3390/e23010085",
        "why_it_matters": "Shows that trap/target placement is a first-order transport variable.",
    },
    {
        "topic": "Dephasing-assisted transport",
        "citation": "Plenio & Huelga (2008)",
        "doi": "10.1088/1367-2630/10/11/113019",
        "why_it_matters": "Core open-system logic for noise-assisted transport.",
    },
    {
        "topic": "Environment-assisted quantum transport",
        "citation": "Mohseni et al. (2008)",
        "doi": "10.1063/1.3002335",
        "why_it_matters": "Canonical sink-efficiency picture with nonzero noise optimum.",
    },
    {
        "topic": "Disorder + dephasing maps",
        "citation": "Rebentrost et al. (2009)",
        "doi": "10.1088/1367-2630/11/3/033003",
        "why_it_matters": "Benchmark for scanning disorder and dephasing windows.",
    },
    {
        "topic": "Classical vs quantum bridge",
        "citation": "Whitfield, Rodriguez-Rosario & Aspuru-Guzik (2010)",
        "doi": "10.1103/PhysRevA.81.022323",
        "why_it_matters": "Justifies continuous-time classical controls next to quantum walks.",
    },
    {
        "topic": "Dynamic graph fingerprints",
        "citation": "Rossi, Torsello & Hancock (2015)",
        "doi": "10.1103/PhysRevE.91.022815",
        "why_it_matters": "Supports graph similarity through quantum-walk signatures.",
    },
    {
        "topic": "Graph classification",
        "citation": "Minello, Rossi & Torsello (2019)",
        "doi": "10.3390/e21030328",
        "why_it_matters": "Supports learning/classification from quantum-walk dynamics.",
    },
    {
        "topic": "Disorder assistance",
        "citation": "Novo, Mohseni & Omar (2016)",
        "doi": "10.1038/srep18142",
        "why_it_matters": "Shows disorder is not always harmful in suboptimal decoherence regimes.",
    },
    {
        "topic": "Experimental motivation",
        "citation": "Maier et al. (2019)",
        "doi": "10.1103/PhysRevLett.122.050501",
        "why_it_matters": "Finite-network experimental anchor for assisted transport.",
    },
    {
        "topic": "Multiple noise optima",
        "citation": "Coates, Lovett & Gauger (2023)",
        "doi": "10.1039/D2CP04935J",
        "why_it_matters": "Warns that noise-response curves can be more complex than a single peak.",
    },
    {
        "topic": "Fractal transport",
        "citation": "Rojo-Francas et al. (2024)",
        "doi": "10.1038/s42005-024-01747-x",
        "why_it_matters": "Motivates anomalous spreading on fractal geometries.",
    },
]


def resolve_repo_root(start: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if start is not None:
        candidates.append(Path(start).resolve())
    candidates.extend([Path.cwd().resolve(), Path("/content/Quantum-systems")])
    for candidate in candidates:
        for root in [candidate, *candidate.parents]:
            if (root / "pyproject.toml").exists() and (root / "outputs").exists():
                return root
    raise FileNotFoundError("Could not resolve the Quantum-systems repository root.")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()


def _transport_root(repo_root: str | Path | None = None) -> Path:
    return resolve_repo_root(repo_root) / "outputs" / "transport_networks"


def load_dynamic_atlas_evidence(repo_root: str | Path | None = None) -> tuple[dict, pd.DataFrame]:
    base = _transport_root(repo_root) / "dynamic_network_atlas_evidence_prep" / "latest"
    metrics = _read_json(base / "atlas_metrics.json")
    summary = _read_csv(base / "atlas_summary_by_family.csv")
    return metrics, summary


def load_research_journey_metrics(repo_root: str | Path | None = None) -> dict:
    return _read_json(_transport_root(repo_root) / "research_journey_v2" / "latest" / "metrics.json")


def load_network_classification_metrics(repo_root: str | Path | None = None) -> dict:
    return _read_json(_transport_root(repo_root) / "network_classification_complete" / "latest" / "metrics.json")


def load_paper_verdicts(repo_root: str | Path | None = None) -> pd.DataFrame:
    verdicts = _read_json(_transport_root(repo_root) / "paper_reproduction_suite" / "latest" / "paper_verdicts.json")
    rows = []
    for paper_key, payload in verdicts.items():
        rows.append(
            {
                "paper_key": paper_key,
                "verdict": payload.get("verdict", ""),
                "claim_count": payload.get("claim_count", 0),
                "mean_confidence": payload.get("mean_confidence", 0.0),
            }
        )
    return pd.DataFrame(rows).sort_values(["verdict", "paper_key"]).reset_index(drop=True)


def load_current_atlas_state(repo_root: str | Path | None = None) -> dict:
    base = _transport_root(repo_root) / "dynamic_network_atlas" / "latest"
    handoff_text = (base / "HANDOFF_STATE.md").read_text(encoding="utf-8") if (base / "HANDOFF_STATE.md").exists() else ""
    metrics = _read_json(base / "atlas_metrics.json")
    run_metadata = _read_json(base / "run_metadata.json")
    return {
        "handoff_text": handoff_text,
        "metrics": metrics,
        "run_metadata": run_metadata,
        "records_csv": base / "atlas_records.csv",
    }


def current_research_snapshot(repo_root: str | Path | None = None) -> dict:
    evidence_metrics, evidence_table = load_dynamic_atlas_evidence(repo_root)
    return {
        "evidence_prep_metrics": evidence_metrics,
        "evidence_prep_table": evidence_table,
        "research_journey_metrics": load_research_journey_metrics(repo_root),
        "classification_metrics": load_network_classification_metrics(repo_root),
        "paper_verdicts": load_paper_verdicts(repo_root),
        "atlas_state": load_current_atlas_state(repo_root),
    }


def reference_rows() -> pd.DataFrame:
    return pd.DataFrame(REFERENCE_ROWS)


def professor_talking_points() -> list[str]:
    return [
        "We study effective open quantum transport on finite networks, not microscopic materials.",
        "The main question is how topology, target placement, disorder, and phase scrambling change useful arrival at the target.",
        "Von Neumann entropy is a diagnostic of mixing on the remaining graph state; it is not the transport goal by itself.",
        "A classical control is always needed before calling a result genuinely quantum.",
        "Our strongest current evidence is that target placement matters strongly and some families show positive quantum-minus-classical arrival.",
    ]
