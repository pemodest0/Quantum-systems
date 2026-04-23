from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def best_by_disorder(payload: dict[str, object]) -> dict[str, np.ndarray]:
    efficiency = np.asarray(payload["efficiency_mean"], dtype=float)
    efficiency_std = np.asarray(payload["efficiency_std"], dtype=float)
    disorder = np.asarray(payload["disorder_strength_over_coupling"], dtype=float)
    dephasing = np.asarray(payload["dephasing_over_coupling"], dtype=float)
    best_cols = np.nanargmax(efficiency, axis=1)
    coherent = efficiency[:, 0]
    best = efficiency[np.arange(len(disorder)), best_cols]
    best_std = efficiency_std[np.arange(len(disorder)), best_cols]
    best_dephasing = dephasing[best_cols]
    return {
        "disorder": disorder,
        "coherent": coherent,
        "best": best,
        "best_std": best_std,
        "best_dephasing": best_dephasing,
        "gain": best - coherent,
    }


def average_best_arrival(payload: dict[str, object]) -> float:
    derived = best_by_disorder(payload)
    return float(np.mean(derived["best"]))


def average_phase_gain(payload: dict[str, object]) -> float:
    derived = best_by_disorder(payload)
    return float(np.mean(derived["gain"]))


def selected_scenario_names(
    results_payload: dict[str, object],
    *,
    top_n: int = 2,
    bottom_n: int = 1,
) -> list[str]:
    scenarios = list(results_payload["scenarios"])
    ranking = sorted(
        scenarios,
        key=lambda payload: average_best_arrival(payload),
        reverse=True,
    )
    chosen = ranking[:top_n]
    if bottom_n > 0:
        for payload in ranking[-bottom_n:]:
            if payload not in chosen:
                chosen.append(payload)
    return [str(payload["scenario_name"]) for payload in chosen]


def write_literature_guardrails(path: Path, guardrails: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(guardrails, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary_markdown(
    path: Path,
    *,
    title: str,
    literature_guardrails: list[dict[str, str]],
    overview_lines: list[str],
    measured_lines: list[str],
    agreement_lines: list[str],
    uncertainty_lines: list[str],
    table_headers: list[str],
    table_rows: list[list[str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    lines.extend(overview_lines)
    lines.extend(["", "## Literature guardrails", ""])
    for item in literature_guardrails:
        description = item.get("use") or item.get("reading") or ""
        lines.append(f"- {item['key']}: {item['url']} -- {description}")
    lines.extend(["", "## What was measured", ""])
    lines.extend([f"- {line}" for line in measured_lines])
    lines.extend(["", "## Agreement with literature", ""])
    lines.extend([f"- {line}" for line in agreement_lines])
    lines.extend(["", "## What is still not proven", ""])
    lines.extend([f"- {line}" for line in uncertainty_lines])
    lines.extend(["", "## Derived table", ""])
    lines.append("| " + " | ".join(table_headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(table_headers)) + " |")
    for row in table_rows:
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
