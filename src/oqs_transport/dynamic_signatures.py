from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import numpy as np

from .regimes import classify_regime
from .simulation import TransportSimulationResult


DYNAMIC_SIGNATURE_FEATURES = (
    "zero_dephasing_arrival",
    "best_arrival",
    "dephasing_gain",
    "best_dephasing_over_coupling",
    "high_dephasing_penalty",
    "mean_arrival_over_dephasing",
    "arrival_std_over_dephasing",
    "best_loss_population",
    "best_network_population",
    "best_mean_coherence_l1",
    "best_final_purity",
    "best_final_entropy",
    "best_population_shannon_entropy",
    "best_participation_ratio",
    "best_ipr",
    "best_final_msd",
    "best_final_front_width",
    "best_integrated_interface_current",
    "best_sink_hitting_time_filled",
    "best_transfer_time_filled",
    "regime_confidence",
)


def _filled_time(value: float | None, fallback: float) -> float:
    return float(fallback if value is None else value)


def signature_from_dephasing_scan(
    *,
    scan_results: list[TransportSimulationResult],
    dephasing_over_coupling: Iterable[float],
    coupling_hz: float,
    family: str,
    instance_id: str,
    graph_seed: int,
    disorder_seed: int,
    disorder_strength_over_coupling: float,
    target_style: str,
    initial_site: int,
    trap_site: int,
    topology: dict[str, float],
) -> dict[str, object]:
    if not scan_results:
        raise ValueError("scan_results must not be empty")
    dephasing_grid = np.asarray(list(dephasing_over_coupling), dtype=float)
    arrivals = np.asarray([result.transport_efficiency for result in scan_results], dtype=float)
    losses = np.asarray([result.loss_population[-1] for result in scan_results], dtype=float)
    msd_values = np.asarray(
        [
            0.0 if result.mean_squared_displacement_t is None else float(result.mean_squared_displacement_t[-1])
            for result in scan_results
        ],
        dtype=float,
    )
    best_index = int(np.nanargmax(arrivals))
    best = scan_results[best_index]
    zero_arrival = float(arrivals[0])
    best_arrival = float(arrivals[best_index])
    gain = best_arrival - zero_arrival
    high_dephasing_penalty = best_arrival - float(arrivals[-1])
    t_final = float(best.times[-1])
    final_msd = 0.0 if best.mean_squared_displacement_t is None else float(best.mean_squared_displacement_t[-1])
    final_width = 0.0 if best.front_width_t is None else float(best.front_width_t[-1])
    integrated_interface_current = 0.0 if best.integrated_interface_current is None else float(best.integrated_interface_current)
    classification = classify_regime(
        transport_efficiency=best.transport_efficiency,
        coherent_efficiency_reference=zero_arrival,
        best_efficiency_reference=best_arrival,
        final_loss_population=float(losses[best_index]),
        disorder_strength_over_coupling=float(disorder_strength_over_coupling),
        dephasing_over_coupling=float(dephasing_grid[best_index]),
        mean_coherence_l1=best.mean_coherence_l1,
        final_participation_ratio=best.final_participation_ratio,
        final_entropy=best.final_entropy,
        final_mean_squared_displacement=final_msd,
        max_mean_squared_displacement_reference=float(max(np.max(msd_values), 1e-12)),
        n_sites=int(topology.get("n_sites", best.node_populations.shape[1])),
    )

    record: dict[str, object] = {
        "record_id": f"{instance_id}_target-{target_style}_W{float(disorder_strength_over_coupling):.3f}_seed{int(disorder_seed)}",
        "family": family,
        "instance_id": instance_id,
        "graph_seed": int(graph_seed),
        "disorder_seed": int(disorder_seed),
        "disorder_strength_over_coupling": float(disorder_strength_over_coupling),
        "target_style": target_style,
        "initial_site": int(initial_site),
        "trap_site": int(trap_site),
        "zero_dephasing_arrival": zero_arrival,
        "best_arrival": best_arrival,
        "dephasing_gain": float(gain),
        "best_dephasing_over_coupling": float(dephasing_grid[best_index]),
        "high_dephasing_penalty": float(high_dephasing_penalty),
        "mean_arrival_over_dephasing": float(np.mean(arrivals)),
        "arrival_std_over_dephasing": float(np.std(arrivals)),
        "best_loss_population": float(best.loss_population[-1]),
        "best_network_population": float(best.network_population[-1]),
        "best_mean_coherence_l1": float(best.mean_coherence_l1),
        "best_final_purity": float(best.final_purity),
        "best_final_entropy": float(best.final_entropy),
        "best_population_shannon_entropy": float(best.final_population_shannon_entropy),
        "best_participation_ratio": float(best.final_participation_ratio),
        "best_ipr": float(best.final_ipr),
        "best_final_msd": final_msd,
        "best_final_front_width": final_width,
        "best_integrated_interface_current": integrated_interface_current,
        "best_sink_hitting_time_filled": _filled_time(best.sink_hitting_time, t_final),
        "best_transfer_time_filled": _filled_time(best.transfer_time_to_threshold, t_final),
        "regime_label": classification.label,
        "regime_confidence": float(classification.confidence),
        "regime_reason_codes": ";".join(classification.reason_codes),
        "max_trace_deviation": float(max(result.max_trace_deviation for result in scan_results)),
        "max_population_closure_error": float(max(result.max_population_closure_error for result in scan_results)),
        "min_state_eigenvalue": float(min(result.min_state_eigenvalue for result in scan_results)),
    }
    record.update({f"topology_{key}": float(value) for key, value in topology.items()})
    return record


def numeric_feature_names(records: list[dict[str, object]], *, prefixes: tuple[str, ...] = ("topology_",), include_dynamic: bool = True) -> list[str]:
    if not records:
        return []
    names: list[str] = []
    if include_dynamic:
        names.extend(name for name in DYNAMIC_SIGNATURE_FEATURES if name in records[0])
    for key in sorted(records[0]):
        if any(key.startswith(prefix) for prefix in prefixes):
            names.append(key)
    return names


def write_signature_csv(records: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

