from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np

from .networks import tight_binding_hamiltonian


SUPPORTED_PAPER_VERDICTS = ("matched", "diverged", "inconclusive", "not_applicable")


@dataclass(frozen=True)
class PaperClaimVerdict:
    paper_key: str
    claim_id: str
    expected_trend: str
    observed_metric: str
    threshold: float | str
    observed_value: float | str
    verdict: str
    confidence: float
    reason: str


def paper_claim_to_dict(claim: PaperClaimVerdict) -> dict[str, object]:
    return asdict(claim)


def _finite_float(value: object, default: float = 0.0) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(converted):
        return default
    return converted


def _confidence_from_margin(value: float, threshold: float, *, scale: float = 0.10) -> float:
    margin = abs(float(value) - float(threshold))
    return float(np.clip(0.5 + margin / max(scale, 1e-12), 0.0, 1.0))


def _pearson_r2(xs: Iterable[float], ys: Iterable[float]) -> float:
    x = np.asarray(list(xs), dtype=float)
    y = np.asarray(list(ys), dtype=float)
    if x.size < 3 or np.std(x) <= 1e-12 or np.std(y) <= 1e-12:
        return 1.0
    corr = float(np.corrcoef(x, y)[0, 1])
    if not np.isfinite(corr):
        return 1.0
    return float(corr * corr)


def count_resolved_local_peaks(
    points: list[dict[str, object]],
    *,
    x_key: str = "dephasing_over_coupling",
    y_key: str = "arrival",
    min_prominence: float = 0.02,
    min_index_separation: int = 2,
) -> int:
    """Count separated local maxima in an efficiency-vs-dephasing curve."""
    ordered = sorted(
        (
            (_finite_float(point.get(x_key), default=float("nan")), _finite_float(point.get(y_key), default=float("nan")))
            for point in points
        ),
        key=lambda item: item[0],
    )
    ordered = [(x, y) for x, y in ordered if np.isfinite(x) and np.isfinite(y)]
    if len(ordered) < 3:
        return 0
    y = np.asarray([value for _, value in ordered], dtype=float)
    candidate_indices: list[int] = []
    for index in range(1, len(y) - 1):
        local_floor = max(min(y[index - 1], y[index + 1]), float(np.min(y)))
        if y[index] > y[index - 1] and y[index] > y[index + 1] and y[index] - local_floor >= min_prominence:
            candidate_indices.append(index)
    if not candidate_indices:
        return 0
    selected: list[int] = []
    for index in sorted(candidate_indices, key=lambda item: y[item], reverse=True):
        if all(abs(index - existing) >= min_index_separation for existing in selected):
            selected.append(index)
    return len(selected)


def estimate_msd_exponent(
    times: Iterable[float],
    msd_values: Iterable[float],
    *,
    min_points: int = 4,
) -> float | None:
    """Fit MSD ~ t^alpha on positive finite points."""
    t = np.asarray(list(times), dtype=float)
    msd = np.asarray(list(msd_values), dtype=float)
    mask = np.isfinite(t) & np.isfinite(msd) & (t > 0.0) & (msd > 0.0)
    t = t[mask]
    msd = msd[mask]
    if t.size < min_points:
        return None
    start = int(np.floor(0.2 * t.size))
    stop = int(np.ceil(0.8 * t.size))
    if stop - start < min_points:
        start = 0
        stop = t.size
    if stop - start < min_points:
        return None
    slope, _ = np.polyfit(np.log(t[start:stop]), np.log(msd[start:stop]), deg=1)
    if not np.isfinite(slope):
        return None
    return float(slope)


def disorder_localization_score(records: list[dict[str, object]]) -> dict[str, object]:
    """Summarize whether participation falls and IPR rises as disorder increases."""
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        family = str(record.get("family", ""))
        if family:
            by_family[family].append(record)
    matched_families: list[str] = []
    family_scores: dict[str, dict[str, float]] = {}
    for family, family_records in by_family.items():
        by_w: dict[float, list[dict[str, object]]] = defaultdict(list)
        for record in family_records:
            by_w[_finite_float(record.get("disorder_strength_over_coupling"))].append(record)
        ordered_w = sorted(by_w)
        if len(ordered_w) < 2:
            continue
        low_w = ordered_w[0]
        high_w = ordered_w[-1]
        low_pr = float(np.mean([_finite_float(row.get("participation_ratio")) for row in by_w[low_w]]))
        high_pr = float(np.mean([_finite_float(row.get("participation_ratio")) for row in by_w[high_w]]))
        low_ipr = float(np.mean([_finite_float(row.get("ipr")) for row in by_w[low_w]]))
        high_ipr = float(np.mean([_finite_float(row.get("ipr")) for row in by_w[high_w]]))
        low_msd = float(np.mean([_finite_float(row.get("msd")) for row in by_w[low_w]]))
        high_msd = float(np.mean([_finite_float(row.get("msd")) for row in by_w[high_w]]))
        pr_drop = low_pr - high_pr
        ipr_rise = high_ipr - low_ipr
        msd_drop = low_msd - high_msd
        family_scores[family] = {
            "pr_drop": float(pr_drop),
            "ipr_rise": float(ipr_rise),
            "msd_drop": float(msd_drop),
        }
        if pr_drop > 0.10 and ipr_rise > 0.01:
            matched_families.append(family)
    return {
        "matched_family_count": len(matched_families),
        "matched_families": matched_families,
        "family_scores": family_scores,
    }


def solve_effective_source_drain_steady_state(
    adjacency: np.ndarray,
    *,
    source_site: int,
    drain_site: int,
    coupling_hz: float = 1.0,
    dephasing_rate_hz: float = 0.1,
    reset_rate_hz: float = 0.5,
    site_energies_hz: np.ndarray | None = None,
) -> dict[str, object]:
    """Solve a trace-preserving source-drain reset NESS for Manzano-style diagnostics.

    The reset jump |source><drain| is an effective source+dreno loop. It is not the
    same object as the absorbing sink model used in the finite-time campaigns.
    """
    adjacency = np.asarray(adjacency, dtype=float)
    n_sites = int(adjacency.shape[0])
    hamiltonian = tight_binding_hamiltonian(adjacency, coupling_hz, site_energies_hz)
    identity = np.eye(n_sites, dtype=complex)
    liouvillian = -1j * (np.kron(identity, hamiltonian) - np.kron(hamiltonian.T, identity))
    jumps: list[np.ndarray] = []
    if dephasing_rate_hz > 0.0:
        for site in range(n_sites):
            jump = np.zeros((n_sites, n_sites), dtype=complex)
            jump[site, site] = np.sqrt(dephasing_rate_hz)
            jumps.append(jump)
    if reset_rate_hz > 0.0:
        reset = np.zeros((n_sites, n_sites), dtype=complex)
        reset[int(source_site), int(drain_site)] = np.sqrt(reset_rate_hz)
        jumps.append(reset)
    for jump in jumps:
        jump_dag_jump = jump.conj().T @ jump
        liouvillian += np.kron(jump.conj(), jump)
        liouvillian += -0.5 * np.kron(identity, jump_dag_jump)
        liouvillian += -0.5 * np.kron(jump_dag_jump.T, identity)

    trace_row = np.zeros(n_sites * n_sites, dtype=complex)
    for site in range(n_sites):
        trace_row[site + site * n_sites] = 1.0
    system = liouvillian.copy()
    rhs = np.zeros(n_sites * n_sites, dtype=complex)
    system[0, :] = trace_row
    rhs[0] = 1.0
    solution, *_ = np.linalg.lstsq(system, rhs, rcond=None)
    rho = solution.reshape((n_sites, n_sites), order="F")
    rho = 0.5 * (rho + rho.conj().T)
    trace = complex(np.trace(rho))
    if abs(trace) > 1e-14:
        rho = rho / trace
    eigenvalues = np.linalg.eigvalsh(rho)
    drain_population = float(np.real(rho[int(drain_site), int(drain_site)]))
    current = float(reset_rate_hz * max(drain_population, 0.0))
    residual = liouvillian @ rho.reshape(n_sites * n_sites, order="F")
    return {
        "rho": rho,
        "current": current,
        "drain_population": drain_population,
        "trace_error": float(abs(np.trace(rho) - 1.0)),
        "min_eigenvalue": float(np.min(eigenvalues).real),
        "residual_norm": float(np.linalg.norm(residual)),
    }


def _dynamic_feature_matrix(records: list[dict[str, object]]) -> tuple[np.ndarray, list[str]]:
    feature_names = [
        "zero_dephasing_arrival",
        "best_arrival",
        "dephasing_gain",
        "best_dephasing_over_coupling",
        "high_dephasing_penalty",
        "best_loss_population",
        "best_mean_coherence_l1",
        "best_final_entropy",
        "best_participation_ratio",
        "best_ipr",
        "best_sink_hitting_time_filled",
    ]
    available = [name for name in feature_names if records and name in records[0]]
    matrix = np.asarray([[_finite_float(record.get(name)) for name in available] for record in records], dtype=float)
    if matrix.size == 0:
        return np.zeros((0, 0), dtype=float), available
    mean = np.mean(matrix, axis=0)
    std = np.std(matrix, axis=0)
    std[std <= 1e-12] = 1.0
    return (matrix - mean) / std, available


def _same_vs_different_family_distance_ratio(records: list[dict[str, object]]) -> float:
    matrix, _ = _dynamic_feature_matrix(records)
    if matrix.shape[0] < 4:
        return 1.0
    families = [str(record.get("family", "")) for record in records]
    intra: list[float] = []
    inter: list[float] = []
    max_records = min(matrix.shape[0], 220)
    for i in range(max_records):
        for j in range(i + 1, max_records):
            distance = float(np.linalg.norm(matrix[i] - matrix[j]))
            if families[i] == families[j]:
                intra.append(distance)
            else:
                inter.append(distance)
    if not intra or not inter:
        return 1.0
    return float(np.mean(inter) / max(np.mean(intra), 1e-12))


def _target_spread(target_records: list[dict[str, object]]) -> float:
    by_instance: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in target_records:
        by_instance[(str(row.get("family", "")), str(row.get("instance_id", "")))].append(
            _finite_float(row.get("mean_zero_dephasing_arrival"))
        )
    return max((max(values) - min(values) for values in by_instance.values() if len(values) > 1), default=0.0)


def _target_degree_r2(target_records: list[dict[str, object]]) -> float:
    degrees = [_finite_float(row.get("mean_target_degree")) for row in target_records]
    arrivals = [_finite_float(row.get("mean_zero_dephasing_arrival")) for row in target_records]
    return _pearson_r2(degrees, arrivals)


def _best_dephasing_stat(stat_rows: list[dict[str, object]]) -> dict[str, object]:
    candidates = [
        row
        for row in stat_rows
        if _finite_float(row.get("dephasing_gain_mean")) >= 0.05
        and _finite_float(row.get("dephasing_gain_ci95_low")) > 0.0
        and _finite_float(row.get("best_dephasing_over_coupling")) > 0.0
    ]
    if not candidates:
        return {}
    return max(candidates, key=lambda row: _finite_float(row.get("dephasing_gain_mean")))


def _has_high_dephasing_suppression(records: list[dict[str, object]]) -> bool:
    return any(
        _finite_float(record.get("dephasing_gain")) >= 0.05
        and _finite_float(record.get("best_dephasing_over_coupling")) > 0.0
        and _finite_float(record.get("high_dephasing_penalty")) > 0.02
        for record in records
    )


def _positive_dephasing_disorder_persistence(stat_rows: list[dict[str, object]]) -> bool:
    contexts: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in stat_rows:
        if (
            _finite_float(row.get("dephasing_gain_mean")) >= 0.05
            and _finite_float(row.get("dephasing_gain_ci95_low")) > 0.0
            and _finite_float(row.get("best_dephasing_over_coupling")) > 0.0
        ):
            key = (str(row.get("family", "")), str(row.get("edge_model", "")), str(row.get("target_style", "")))
            contexts[key].add(str(row.get("disorder_strength_over_coupling", "")))
    return any(len(values) >= 2 for values in contexts.values())


def _nonzero_dephasing_best_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        record
        for record in records
        if _finite_float(record.get("dephasing_gain")) >= 0.05
        and _finite_float(record.get("best_dephasing_over_coupling")) > 0.0
    ]


def _disorder_assistance_candidate(stat_rows: list[dict[str, object]]) -> tuple[bool, float]:
    by_context: dict[tuple[str, str, str, str], dict[float, float]] = defaultdict(dict)
    for row in stat_rows:
        key = (
            str(row.get("family", "")),
            str(row.get("edge_model", "")),
            str(row.get("target_style", "")),
            str(row.get("best_dephasing_over_coupling", "")),
        )
        disorder = _finite_float(row.get("disorder_strength_over_coupling"))
        by_context[key][disorder] = _finite_float(row.get("best_arrival_mean"))
    best_delta = -1.0
    for values in by_context.values():
        if 0.0 not in values:
            continue
        baseline = values[0.0]
        for disorder, arrival in values.items():
            if disorder <= 0.0:
                continue
            best_delta = max(best_delta, arrival - baseline)
    return best_delta >= 0.03, float(max(best_delta, 0.0))


def _gamma_peak_summary(records: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = (
            str(record.get("family", "")),
            str(record.get("instance_id", "")),
            str(record.get("target_style", "")),
            str(record.get("disorder_strength_over_coupling", "")),
            str(record.get("disorder_seed", "")),
        )
        grouped[key].append(record)
    peak_counts = [count_resolved_local_peaks(points) for points in grouped.values() if len(points) >= 3]
    return {
        "curve_count": len(peak_counts),
        "single_peak_count": sum(1 for count in peak_counts if count == 1),
        "multi_peak_count": sum(1 for count in peak_counts if count >= 2),
        "max_peak_count": max(peak_counts, default=0),
    }


def _fractal_benchmark_summary(records: list[dict[str, object]]) -> dict[str, object]:
    changed = [
        record
        for record in records
        if str(record.get("verdict", "")) == "fractal_geometry_changes_spreading"
        or _finite_float(record.get("msd_exponent_delta_abs")) >= 0.15
        or _finite_float(record.get("front_width_delta_abs")) >= 0.10
    ]
    return {
        "comparison_count": len(records),
        "changed_comparison_count": len(changed),
        "families": sorted({str(record.get("family", "")) for record in records if record.get("family")}),
    }


def _steady_state_summary(records: list[dict[str, object]]) -> dict[str, object]:
    valid = [
        record
        for record in records
        if _finite_float(record.get("current")) > 1e-6
        and _finite_float(record.get("trace_error"), default=1.0) < 1e-8
        and _finite_float(record.get("min_eigenvalue"), default=-1.0) > -1e-7
        and _finite_float(record.get("residual_norm"), default=1.0) < 1e-6
    ]
    currents = [_finite_float(record.get("current")) for record in valid]
    return {
        "record_count": len(records),
        "valid_record_count": len(valid),
        "mean_current": float(np.mean(currents)) if currents else 0.0,
        "max_current": float(np.max(currents)) if currents else 0.0,
    }


def _noisy_network_summary(records: list[dict[str, object]]) -> dict[str, object]:
    resolved_gain = [
        record
        for record in records
        if _finite_float(record.get("dephasing_gain_mean")) >= 0.05
        and _finite_float(record.get("dephasing_gain_ci95_low")) > 0.0
    ]
    variance_values = [_finite_float(record.get("arrival_std")) for record in records]
    q_minus_classical = [_finite_float(record.get("quantum_minus_classical_mean")) for record in records]
    return {
        "record_count": len(records),
        "resolved_gain_count": len(resolved_gain),
        "max_arrival_std": float(max(variance_values, default=0.0)),
        "max_quantum_minus_classical": float(max(q_minus_classical, default=0.0)),
    }


def evaluate_paper_claims(
    *,
    closed_records: list[dict[str, object]],
    target_records: list[dict[str, object]],
    records: list[dict[str, object]],
    stat_rows: list[dict[str, object]],
    group_report: dict[str, object],
    size_report: dict[str, object],
    metrics: dict[str, object],
    gamma_curve_records: list[dict[str, object]] | None = None,
    fractal_records: list[dict[str, object]] | None = None,
    localization_records: list[dict[str, object]] | None = None,
    steady_state_records: list[dict[str, object]] | None = None,
    noisy_network_records: list[dict[str, object]] | None = None,
) -> list[PaperClaimVerdict]:
    numerics_pass = bool(metrics.get("numerics_pass", False))
    gamma_curve_records = gamma_curve_records or []
    fractal_records = fractal_records or []
    localization_records = localization_records or []
    steady_state_records = steady_state_records or []
    noisy_network_records = noisy_network_records or []
    claims: list[PaperClaimVerdict] = []

    closed_values = [_finite_float(row.get("long_time_average_return")) for row in closed_records]
    closed_std = float(np.std(closed_values)) if closed_values else 0.0
    claims.append(
        PaperClaimVerdict(
            paper_key="muelken_blumen_2011",
            claim_id="closed_ctqw_topology_dependence",
            expected_trend="Closed CTQW observables depend on network topology.",
            observed_metric="std(long_time_average_return)",
            threshold=0.01,
            observed_value=closed_std,
            verdict="matched" if numerics_pass and closed_std > 0.01 else "inconclusive",
            confidence=_confidence_from_margin(closed_std, 0.01, scale=0.05),
            reason="Closed-system return differs across topologies while numerical closure is valid." if closed_std > 0.01 else "Closed-system topology separation is below threshold.",
        )
    )

    spread = _target_spread(target_records)
    degree_r2 = _target_degree_r2(target_records)
    claims.append(
        PaperClaimVerdict(
            paper_key="razzoli_2021",
            claim_id="trap_position_changes_efficiency",
            expected_trend="Changing only trap/target position changes transport efficiency.",
            observed_metric="max_target_position_spread",
            threshold=0.05,
            observed_value=spread,
            verdict="matched" if numerics_pass and spread >= 0.05 else "inconclusive",
            confidence=_confidence_from_margin(spread, 0.05, scale=0.20),
            reason="Target placement produces efficiency spread above threshold." if spread >= 0.05 else "Target placement effect is below threshold.",
        )
    )
    claims.append(
        PaperClaimVerdict(
            paper_key="razzoli_2021",
            claim_id="connectivity_is_not_sufficient",
            expected_trend="Target degree alone should not explain transport efficiency.",
            observed_metric="r2(target_degree, target_arrival)",
            threshold="<0.75",
            observed_value=degree_r2,
            verdict="matched" if spread >= 0.05 and degree_r2 < 0.75 else "inconclusive",
            confidence=float(np.clip(1.0 - degree_r2, 0.0, 1.0)),
            reason="Degree explains less than the threshold fraction of target-arrival variation." if degree_r2 < 0.75 else "Degree correlation is too high or data are under-varied.",
        )
    )

    best_dephasing = _best_dephasing_stat(stat_rows)
    best_gain = _finite_float(best_dephasing.get("dephasing_gain_mean")) if best_dephasing else 0.0
    best_gain_low = _finite_float(best_dephasing.get("dephasing_gain_ci95_low")) if best_dephasing else 0.0
    persistent = _positive_dephasing_disorder_persistence(stat_rows)
    suppression = _has_high_dephasing_suppression(records)
    dephasing_verdict = "matched" if best_gain >= 0.05 and best_gain_low > 0.0 else "inconclusive"
    claims.append(
        PaperClaimVerdict(
            paper_key="plenio_huelga_2008",
            claim_id="dephasing_assisted_transport",
            expected_trend="Nonzero dephasing can improve useful target arrival.",
            observed_metric="max_mean_dephasing_gain_with_ci95_low",
            threshold=0.05,
            observed_value=best_gain,
            verdict=dephasing_verdict,
            confidence=_confidence_from_margin(best_gain_low, 0.0, scale=0.08),
            reason="A nonzero dephasing point has gain above threshold with positive CI95 lower bound." if dephasing_verdict == "matched" else "No statistically resolved positive dephasing gain was found.",
        )
    )
    claims.append(
        PaperClaimVerdict(
            paper_key="mohseni_2008",
            claim_id="enaqt_intermediate_regime",
            expected_trend="Intermediate environment action improves sink efficiency, while strongest dephasing is not always optimal.",
            observed_metric="dephasing_gain_and_high_dephasing_penalty",
            threshold="gain>=0.05 and penalty>0.02",
            observed_value=f"gain={best_gain:.3f}; suppression={suppression}",
            verdict="matched" if best_gain >= 0.05 and suppression else "inconclusive",
            confidence=_confidence_from_margin(best_gain, 0.05, scale=0.12),
            reason="Best transport occurs at nonzero dephasing and high dephasing is not uniformly optimal." if suppression else "The high-dephasing ceiling is not clearly resolved.",
        )
    )

    caruso_records = _nonzero_dephasing_best_records(records)
    loss_values = [_finite_float(record.get("best_loss_population")) for record in caruso_records]
    claims.append(
        PaperClaimVerdict(
            paper_key="caruso_2009",
            claim_id="noise_opens_transport_pathways_in_dissipative_networks",
            expected_trend="Noise can improve excitation transfer through a dissipative network instead of only degrading it.",
            observed_metric="positive_dephasing_gain_with_sink_loss_model",
            threshold="gain>=0.05 at nonzero dephasing",
            observed_value=f"candidate_records={len(caruso_records)}; mean_loss={float(np.mean(loss_values)) if loss_values else 0.0:.3f}",
            verdict="matched" if caruso_records and best_gain >= 0.05 else "inconclusive",
            confidence=_confidence_from_margin(best_gain, 0.05, scale=0.12),
            reason="The sink/loss model contains cases where nonzero dephasing improves useful arrival." if caruso_records else "No positive dephasing-assisted dissipative case was resolved.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="kendon_2007",
            claim_id="decoherence_as_a_tunable_quantum_walk_parameter",
            expected_trend="Moderate decoherence can tune quantum-walk spreading or mixing, while excessive decoherence removes coherent advantages.",
            observed_metric="dephasing_gain_and_high_dephasing_penalty",
            threshold="gain>=0.05 and penalty>0.02",
            observed_value=f"gain={best_gain:.3f}; suppression={suppression}",
            verdict="matched" if best_gain >= 0.05 and suppression else "inconclusive",
            confidence=_confidence_from_margin(best_gain, 0.05, scale=0.12),
            reason="The simulations show a useful nonzero-dephasing region and a high-dephasing penalty." if suppression else "The current grid has not resolved the high-dephasing penalty clearly enough.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="rebentrost_2009",
            claim_id="disorder_dephasing_efficiency_map",
            expected_trend="Efficiency maps contain a useful intermediate dephasing window across disorder values.",
            observed_metric="persistent_positive_dephasing_gain_and_high_noise_suppression",
            threshold=">=2 disorder values and penalty>0.02",
            observed_value=f"persistent={persistent}; suppression={suppression}",
            verdict="matched" if persistent and suppression else "inconclusive",
            confidence=0.85 if persistent and suppression else 0.45,
            reason="Positive dephasing gain persists across disorder values and high-noise suppression appears." if persistent and suppression else "The map does not yet resolve both persistence and high-noise suppression.",
        )
    )

    quantum_acc = _finite_float(group_report.get("quantum_only", {}).get("accuracy_mean"))
    classical_acc = _finite_float(group_report.get("classical_only", {}).get("accuracy_mean"))
    delta_acc = _finite_float(group_report.get("quantum_minus_classical", {}).get("accuracy_mean"))
    claims.append(
        PaperClaimVerdict(
            paper_key="whitfield_2010",
            claim_id="classical_quantum_walks_are_distinguishable_limits",
            expected_trend="Quantum/open signatures should not be fully explained by the classical rate-walk control.",
            observed_metric="max(quantum_only, quantum_minus_classical)-classical_only_accuracy",
            threshold=0.02,
            observed_value=max(quantum_acc, delta_acc) - classical_acc,
            verdict="matched" if max(quantum_acc, delta_acc) > classical_acc + 0.02 else "inconclusive",
            confidence=_confidence_from_margin(max(quantum_acc, delta_acc) - classical_acc, 0.02, scale=0.12),
            reason="Quantum/open signatures classify better than the classical-control features." if max(quantum_acc, delta_acc) > classical_acc + 0.02 else "Classical control explains most of the signal.",
        )
    )

    distance_ratio = _same_vs_different_family_distance_ratio(records)
    claims.append(
        PaperClaimVerdict(
            paper_key="rossi_2015",
            claim_id="dynamic_signatures_encode_graph_similarity",
            expected_trend="Dynamic CTQW-inspired signatures should place same-family graphs closer than different-family graphs.",
            observed_metric="mean_interfamily_distance/mean_intrafamily_distance",
            threshold=1.10,
            observed_value=distance_ratio,
            verdict="matched" if distance_ratio >= 1.10 else "inconclusive",
            confidence=_confidence_from_margin(distance_ratio, 1.10, scale=0.30),
            reason="Inter-family dynamic-signature distance is larger than intra-family distance." if distance_ratio >= 1.10 else "Dynamic-signature separation is below threshold.",
        )
    )

    baseline = _finite_float(group_report.get("quantum_only", {}).get("baseline_accuracy"))
    combined = _finite_float(group_report.get("combined", {}).get("accuracy_mean"))
    topology = _finite_float(group_report.get("topology_only", {}).get("accuracy_mean"))
    classification_matched = quantum_acc > baseline and combined > baseline and combined >= min(topology, 0.999)
    claims.append(
        PaperClaimVerdict(
            paper_key="minello_2019",
            claim_id="quantum_walk_signatures_support_graph_classification",
            expected_trend="Quantum-walk dynamic signatures should classify graph families above baseline.",
            observed_metric="group_split_accuracy",
            threshold="quantum>baseline and combined>=topology",
            observed_value=f"quantum={quantum_acc:.3f}; topology={topology:.3f}; combined={combined:.3f}; baseline={baseline:.3f}",
            verdict="matched" if classification_matched else "inconclusive",
            confidence=_confidence_from_margin(quantum_acc - baseline, 0.0, scale=0.20),
            reason="Dynamic and combined signatures beat the group-split baseline." if classification_matched else "Classification is not sufficiently above controls.",
        )
    )

    disorder_matched, disorder_delta = _disorder_assistance_candidate(stat_rows)
    claims.append(
        PaperClaimVerdict(
            paper_key="novo_2016",
            claim_id="disorder_can_assist_suboptimal_transport",
            expected_trend="Moderate disorder can improve transport in suboptimal regimes.",
            observed_metric="max_arrival_delta_disorder_vs_clean_same_context",
            threshold=0.03,
            observed_value=disorder_delta,
            verdict="matched" if disorder_matched else "inconclusive",
            confidence=_confidence_from_margin(disorder_delta, 0.03, scale=0.10),
            reason="At least one matched context improves with nonzero disorder." if disorder_matched else "No clean same-context disorder improvement above threshold was found.",
        )
    )

    gamma_summary = _gamma_peak_summary(gamma_curve_records)
    multi_peak_count = int(gamma_summary["multi_peak_count"])
    max_peak_count = int(gamma_summary["max_peak_count"])
    claims.append(
        PaperClaimVerdict(
            paper_key="coates_2023",
            claim_id="multiple_enaqt_optima_from_gamma_resolved_curves",
            expected_trend="Some disordered networks can have more than one optimal noise regime rather than a single Goldilocks peak.",
            observed_metric="gamma_resolved_peak_count",
            threshold="at least two separated local maxima",
            observed_value=f"curves={gamma_summary['curve_count']}; multi_peak_curves={multi_peak_count}; max_peaks={max_peak_count}",
            verdict="matched" if multi_peak_count > 0 else "inconclusive",
            confidence=0.85 if multi_peak_count > 0 else (0.50 if int(gamma_summary["single_peak_count"]) > 0 else 0.35),
            reason="At least one efficiency-versus-dephasing curve contains two separated local maxima." if multi_peak_count > 0 else "Gamma-resolved curves did not show two resolved local maxima in this profile.",
        )
    )

    localization_summary = disorder_localization_score(localization_records)
    localization_family_count = int(localization_summary["matched_family_count"])
    claims.append(
        PaperClaimVerdict(
            paper_key="anderson_1958",
            claim_id="static_disorder_localizes_spreading",
            expected_trend="Increasing static disorder suppresses spatial delocalization in tight-binding-like networks.",
            observed_metric="families_with_PR_drop_and_IPR_rise",
            threshold="at least two families",
            observed_value=localization_family_count,
            verdict="matched" if localization_family_count >= 2 else "inconclusive",
            confidence=float(np.clip(0.35 + 0.25 * localization_family_count, 0.0, 0.95)),
            reason="Participation falls and IPR rises with disorder in multiple families." if localization_family_count >= 2 else "Disorder-localization trend is not resolved across enough families.",
        )
    )

    noisy_summary = _noisy_network_summary(noisy_network_records)
    claims.append(
        PaperClaimVerdict(
            paper_key="walschaers_2016",
            claim_id="disordered_noisy_networks_need_ensemble_statistics",
            expected_trend="Disordered noisy networks should be evaluated by ensemble mean, variance, and topology sensitivity, not a single best curve.",
            observed_metric="resolved_gain_count_and_arrival_std",
            threshold="resolved_gain_count>=1 and arrival_std>0.02",
            observed_value=f"resolved_gain_count={noisy_summary['resolved_gain_count']}; max_arrival_std={noisy_summary['max_arrival_std']:.3f}",
            verdict="matched" if int(noisy_summary["resolved_gain_count"]) >= 1 and float(noisy_summary["max_arrival_std"]) > 0.02 else "inconclusive",
            confidence=0.80 if int(noisy_summary["resolved_gain_count"]) >= 1 and float(noisy_summary["max_arrival_std"]) > 0.02 else 0.45,
            reason="The benchmark exports ensemble spread and at least one statistically resolved noisy-transport gain." if int(noisy_summary["resolved_gain_count"]) >= 1 else "No resolved ensemble-level noisy-transport gain was found.",
        )
    )

    steady_summary = _steady_state_summary(steady_state_records)
    claims.append(
        PaperClaimVerdict(
            paper_key="manzano_2013",
            claim_id="stationary_source_drain_current_requires_ness_mode",
            expected_trend="Stationary transport should be measured with a source-drain steady state, not with the absorbing finite-time sink model.",
            observed_metric="valid_stationary_current_records",
            threshold="valid_record_count>0 and current>0",
            observed_value=f"valid={steady_summary['valid_record_count']}/{steady_summary['record_count']}; mean_current={steady_summary['mean_current']:.4f}",
            verdict="matched" if int(steady_summary["valid_record_count"]) > 0 and float(steady_summary["mean_current"]) > 1e-6 else "inconclusive",
            confidence=0.85 if int(steady_summary["valid_record_count"]) > 0 else 0.35,
            reason="A separate trace-preserving source-drain NESS benchmark returns finite validated current." if int(steady_summary["valid_record_count"]) > 0 else "No validated steady-state current was produced by the NESS benchmark.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="coutinho_2022",
            claim_id="noisy_quantum_networks_vs_classical_topological_controls",
            expected_trend="Noisy quantum-network dynamics should be compared against classical and topological controls before claiming a quantum signature.",
            observed_metric="quantum_minus_classical_and_noisy_gain_summary",
            threshold="quantum_minus_classical>0.05 or resolved noisy gain",
            observed_value=f"max_q_minus_classical={noisy_summary['max_quantum_minus_classical']:.3f}; resolved_gain_count={noisy_summary['resolved_gain_count']}",
            verdict="matched" if float(noisy_summary["max_quantum_minus_classical"]) > 0.05 or int(noisy_summary["resolved_gain_count"]) >= 1 else "inconclusive",
            confidence=0.80 if float(noisy_summary["max_quantum_minus_classical"]) > 0.05 or int(noisy_summary["resolved_gain_count"]) >= 1 else 0.40,
            reason="The suite exports noisy quantum, classical-control, and topology-sensitive comparisons." if noisy_network_records else "The noisy-network comparison table is missing or under-resolved.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="blach_2025",
            claim_id="environment_assisted_transport_as_material_motivation",
            expected_trend="Experiments can show best transport when disorder and dephasing are balanced.",
            observed_metric="effective_model_dephasing_disorder_window",
            threshold="persistent positive dephasing gain with high-noise suppression",
            observed_value=f"persistent={persistent}; suppression={suppression}",
            verdict="matched" if persistent and suppression else "inconclusive",
            confidence=0.80 if persistent and suppression else 0.40,
            reason="The effective model reproduces the qualitative balanced-regime motif, not the perovskite microscopic experiment." if persistent and suppression else "The effective model does not yet resolve both balance and high-noise suppression.",
        )
    )
    claims.append(
        PaperClaimVerdict(
            paper_key="blach_2025",
            claim_id="perovskite_nanocrystal_microscopic_reproduction",
            expected_trend="A perovskite experiment requires material-specific structure, temperature dependence, and exciton parameters.",
            observed_metric="model_scope",
            threshold="material-specific parameters required",
            observed_value="effective network model only",
            verdict="not_applicable",
            confidence=1.0,
            reason="This lab uses controlled effective networks and does not yet include perovskite nanocrystal parameters.",
        )
    )

    fractal_summary = _fractal_benchmark_summary(fractal_records)
    fractal_changed = int(fractal_summary["changed_comparison_count"])
    claims.append(
        PaperClaimVerdict(
            paper_key="rojo_francas_2024",
            claim_id="fractal_geometry_changes_transport_exponents",
            expected_trend="Fractal lattices can show anomalous spreading governed by geometry and spectral structure.",
            observed_metric="fractal_vs_lattice_msd_front_width",
            threshold="at least two changed fractal-vs-lattice comparisons",
            observed_value=f"changed={fractal_changed}/{fractal_summary['comparison_count']}; families={fractal_summary['families']}",
            verdict="matched" if fractal_changed >= 2 else "inconclusive",
            confidence=0.85 if fractal_changed >= 2 else 0.40,
            reason="Fractal benchmarks differ from the square-lattice control in multiple spreading comparisons." if fractal_changed >= 2 else "Fractal-vs-lattice spreading difference is not resolved in this paper profile.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="gamble_2010",
            claim_id="two_particle_quantum_walk_graph_isomorphism",
            expected_trend="Interacting two-particle quantum walks can distinguish graph structures beyond some single-particle invariants.",
            observed_metric="particle_number",
            threshold="two-particle interacting walk required",
            observed_value="single-excitation effective model",
            verdict="not_applicable",
            confidence=1.0,
            reason="The current lab intentionally stays in the single-excitation sector, so this paper is a limitation guardrail rather than a direct benchmark.",
        )
    )

    claims.append(
        PaperClaimVerdict(
            paper_key="engel_2007",
            claim_id="photosynthetic_wavelike_coherence_experimental_motivation",
            expected_trend="Spectroscopic experiments can reveal coherent excitation dynamics in photosynthetic complexes.",
            observed_metric="experimental_spectroscopy_scope",
            threshold="microscopic photosynthetic complex and spectroscopy required",
            observed_value="effective graph transport model",
            verdict="not_applicable",
            confidence=1.0,
            reason="This paper motivates coherent excitation transport but is not reproduced by a generic graph model.",
        )
    )

    finite_sizes = sorted({int(_finite_float(record.get("n_sites"))) for record in records if _finite_float(record.get("n_sites")) > 0})
    size_available = any(isinstance(value, dict) and "combined" in value for value in size_report.values())
    claims.append(
        PaperClaimVerdict(
            paper_key="maier_2019",
            claim_id="finite_network_coherent_assisted_damped_progression",
            expected_trend="Finite controlled networks can show coherent, assisted, and high-noise-damped regimes.",
            observed_metric="finite_size_grid_plus_dephasing_window_plus_suppression",
            threshold="finite N and dephasing window with suppression",
            observed_value=f"N={finite_sizes}; window={best_gain >= 0.05}; suppression={suppression}",
            verdict="matched" if finite_sizes and best_gain >= 0.05 and suppression else "inconclusive",
            confidence=0.80 if finite_sizes and best_gain >= 0.05 and suppression else 0.45,
            reason="The effective finite-network model reproduces the qualitative regime progression." if finite_sizes and best_gain >= 0.05 and suppression else "The qualitative progression is not fully resolved.",
        )
    )
    claims.append(
        PaperClaimVerdict(
            paper_key="maier_2019",
            claim_id="exact_10_qubit_hardware_reproduction",
            expected_trend="Exact trapped-ion/qubit hardware reproduction would require microscopic hardware parameters.",
            observed_metric="model_scope",
            threshold="hardware-specific parameters required",
            observed_value="effective network model only",
            verdict="not_applicable",
            confidence=1.0,
            reason="This lab tests a qualitative finite-network analogue, not the experimental hardware implementation.",
        )
    )
    return claims


def aggregate_paper_verdicts(claims: list[PaperClaimVerdict]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[PaperClaimVerdict]] = defaultdict(list)
    for claim in claims:
        grouped[claim.paper_key].append(claim)
    payload: dict[str, dict[str, object]] = {}
    for paper_key, paper_claims in sorted(grouped.items()):
        counts = Counter(claim.verdict for claim in paper_claims)
        central = [claim for claim in paper_claims if claim.verdict != "not_applicable"]
        if any(claim.verdict == "diverged" for claim in central):
            verdict = "diverged"
        elif central and counts["matched"] > len(central) / 2:
            verdict = "matched"
        elif central:
            verdict = "inconclusive"
        else:
            verdict = "not_applicable"
        payload[paper_key] = {
            "paper_key": paper_key,
            "verdict": verdict,
            "claim_count": len(paper_claims),
            "counts": dict(counts),
            "mean_confidence": float(np.mean([claim.confidence for claim in paper_claims])),
            "claims": [paper_claim_to_dict(claim) for claim in paper_claims],
        }
    return payload
