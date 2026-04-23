from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import (  # noqa: E402
    DYNAMIC_SIGNATURE_FEATURES,
    SUPPORTED_DYNAMIC_NETWORK_FAMILIES,
    SUPPORTED_REGIME_LABELS,
    aggregate_record_statistics,
    generate_network_instance,
    mean_std_sem_ci95,
    numeric_feature_names,
    signature_from_dephasing_scan,
    simulate_classical_transport,
    simulate_transport,
    static_disorder_energies,
    target_candidates,
    topology_metrics,
    write_statistics_csv,
)


RANDOM_FAMILIES = {
    "erdos_renyi",
    "watts_strogatz_small_world",
    "barabasi_albert_scale_free",
    "modular_two_community",
    "random_geometric",
}

ATLAS_METRICS = (
    "best_arrival",
    "dephasing_gain",
    "best_sink_hitting_time_filled",
    "best_mean_coherence_l1",
    "best_final_entropy",
    "best_final_purity",
    "best_population_shannon_entropy",
    "best_participation_ratio",
    "best_ipr",
    "best_final_msd",
    "best_final_front_width",
    "quantum_minus_classical",
)

FIGURE_EXPLANATIONS_PTBR = {
    "atlas_dashboard.png": {
        "title": "Painel geral do atlas dinamico",
        "meaning": "Compara, por tipo de rede, chegada ao alvo, ganho por embaralhamento de fase, diferenca quantico menos classico e entropia final.",
        "x_axis": "Familia da rede.",
        "y_axis": "Valor medio da metrica indicada em cada painel.",
        "color": "Cada barra representa uma familia; barras maiores nao sao sempre melhores, depende da metrica.",
        "reading_rule": "Chegada alta e diferenca quantico-classico positiva sao sinais de transporte util; entropia alta so indica mistura/espalhamento.",
    },
    "arrival_by_family_heatmap.png": {
        "title": "Chegada ao alvo por rede e irregularidade",
        "meaning": "Mostra quanto da excitacao chegou ao canal de chegada para cada familia e cada nivel de irregularidade local.",
        "x_axis": "W/J: irregularidade local comparada ao acoplamento coerente.",
        "y_axis": "Familia da rede.",
        "color": "Mais claro significa maior chegada ao alvo.",
        "reading_rule": "Nao confundir cor clara com espalhamento: aqui a cor e chegada acumulada no alvo.",
    },
    "entropy_coherence_panel.png": {
        "title": "Mistura, pureza, coerencia e participacao",
        "meaning": "Compara se a excitacao fica coerente, misturada, pura ou espalhada por muitos nos.",
        "x_axis": "Familia da rede.",
        "y_axis": "Valor medio da metrica.",
        "color": "Cada painel mostra uma metrica diferente.",
        "reading_rule": "Entropia alta nao significa transporte melhor; ela significa estado mais misturado.",
    },
    "quantum_minus_classical_map.png": {
        "title": "Diferenca entre transporte quantico aberto e classico",
        "meaning": "Mostra onde o modelo quantico chega mais ou menos ao alvo que a caminhada classica no mesmo grafo.",
        "x_axis": "W/J: irregularidade local comparada ao acoplamento coerente.",
        "y_axis": "Familia da rede.",
        "color": "Positivo favorece o modelo quantico; perto de zero indica que o classico explica quase tudo.",
        "reading_rule": "So chamar assinatura quantica se a diferenca for maior que 0.05 e estatisticamente sustentada.",
    },
    "regime_phase_map.png": {
        "title": "Mapa de regime fisico dominante",
        "meaning": "Resume se cada familia tende a ser coerente, assistida por ruido, localizada, dominada por perda, amortecida ou mista.",
        "x_axis": "W/J: irregularidade local comparada ao acoplamento coerente.",
        "y_axis": "Familia da rede.",
        "color": "Cada cor e um regime fisico dominante.",
        "reading_rule": "Regimes sao classificacoes auditaveis por limiares, nao opiniao da IA.",
    },
    "signature_embedding.png": {
        "title": "Projecao 2D das impressoes digitais dinamicas",
        "meaning": "Cada ponto e uma simulacao resumida por varias metricas dinamicas.",
        "x_axis": "Componente dinamica 1.",
        "y_axis": "Componente dinamica 2.",
        "color": "Familia da rede.",
        "reading_rule": "Separacao visual sugere que a dinamica carrega informacao sobre a rede; nao e prova sozinha.",
    },
    "family_fingerprint_radar.png": {
        "title": "Impressao digital media por familia",
        "meaning": "Compara varias metricas normalizadas para ver o perfil dinamico medio de cada rede.",
        "x_axis": "Metricas normalizadas.",
        "y_axis": "Escala relativa de 0 a 1.",
        "color": "Familia da rede.",
        "reading_rule": "Serve para comparacao qualitativa; as conclusoes quantitativas devem vir dos CSVs com CI95.",
    },
}


def profile_config(profile: str) -> dict[str, object]:
    if profile == "resume":
        config = profile_config("strong")
        config["profile"] = "resume"
        config["resume"] = True
        return config
    if profile == "smoke":
        return {
            "profile": "smoke",
            "families": ["chain", "ring", "random_geometric"],
            "n_sites_values": [6],
            "graph_realizations": 1,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5],
            "graph_seed_base": 9100,
            "disorder_strength_over_coupling": [0.0, 0.6],
            "dephasing_over_coupling": [0.0, 0.2],
            "target_styles": ["near", "far"],
            "t_final": 5.0,
            "n_time_samples": 48,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "sink_hit_threshold": 0.1,
            "transfer_threshold": 0.5,
            "checkpoint_every": 25,
        }
    if profile == "evidence_prep":
        return {
            "profile": "evidence_prep",
            "families": [
                "chain",
                "ring",
                "bottleneck",
                "clustered",
                "random_geometric",
                "modular_two_community",
                "square_lattice_2d",
            ],
            "n_sites_values": [8, 12],
            "graph_realizations": 3,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17],
            "graph_seed_base": 9300,
            "disorder_strength_over_coupling": [0.0, 0.6, 0.9, 1.2],
            "dephasing_over_coupling": [0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.2],
            "target_styles": ["near", "far"],
            "t_final": 12.0,
            "n_time_samples": 120,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "sink_hit_threshold": 0.1,
            "transfer_threshold": 0.5,
            "checkpoint_every": 50,
        }
    if profile == "strong":
        return {
            "profile": "strong",
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "n_sites_values": [8, 10, 12],
            "graph_realizations": 12,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59],
            "graph_seed_base": 9200,
            "disorder_strength_over_coupling": [0.0, 0.3, 0.6, 0.9, 1.2],
            "dephasing_over_coupling": [0.0, 0.03, 0.05, 0.1, 0.2, 0.4, 0.8, 1.2],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final": 16.0,
            "n_time_samples": 180,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "sink_hit_threshold": 0.1,
            "transfer_threshold": 0.5,
            "checkpoint_every": 250,
        }
    if profile == "intense":
        return {
            "profile": "intense",
            "families": list(SUPPORTED_DYNAMIC_NETWORK_FAMILIES),
            "n_sites_values": [8, 10, 12, 16],
            "graph_realizations": 16,
            "deterministic_graph_realizations": 1,
            "disorder_seeds": [
                3,
                5,
                7,
                11,
                13,
                17,
                19,
                23,
                29,
                31,
                37,
                41,
                43,
                47,
                53,
                59,
                61,
                67,
                71,
                73,
                79,
                83,
                89,
                97,
            ],
            "graph_seed_base": 9400,
            "disorder_strength_over_coupling": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5],
            "dephasing_over_coupling": [0.0, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.6],
            "target_styles": ["near", "far", "high_centrality", "low_centrality"],
            "t_final": 18.0,
            "n_time_samples": 220,
            "coupling_hz": 1.0,
            "sink_rate_hz": 0.65,
            "loss_rate_hz": 0.02,
            "sink_hit_threshold": 0.1,
            "transfer_threshold": 0.5,
            "checkpoint_every": 100,
        }
    raise ValueError(f"unsupported profile: {profile}")


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _float(record: dict[str, object], key: str, default: float = 0.0) -> float:
    try:
        return float(record.get(key, default))
    except (TypeError, ValueError):
        return default


def _record_key(record: dict[str, object]) -> str:
    return "|".join(
        [
            str(record["family"]),
            str(record["instance_id"]),
            str(record["target_style"]),
            str(record["trap_site"]),
            f"{float(record['disorder_strength_over_coupling']):.6f}",
            str(record["disorder_seed"]),
        ]
    )


def _unique_targets(instance, *, initial_site: int, target_styles: list[str]) -> list[tuple[str, int]]:
    candidates = target_candidates(instance, initial_site=initial_site)
    seen: set[int] = set()
    targets: list[tuple[str, int]] = []
    for style in target_styles:
        if style not in candidates:
            continue
        site = int(candidates[style])
        if site in seen:
            continue
        seen.add(site)
        targets.append((style, site))
    return targets


def _realization_count(family: str, config: dict[str, object]) -> int:
    if family in RANDOM_FAMILIES:
        return int(config["graph_realizations"])
    return int(config["deterministic_graph_realizations"])


def _graph_seed(config: dict[str, object], *, family: str, n_sites: int, realization: int) -> int:
    base = int(config["graph_seed_base"]) + 10_000 * int(n_sites) + 101 * int(realization)
    if family not in RANDOM_FAMILIES:
        base = int(config["graph_seed_base"]) + int(n_sites) + int(realization)
    return base


def _filled_time(value: float | None, fallback: float) -> float:
    return float(fallback if value is None else value)


def _qc_case_label(delta: float) -> str:
    if delta > 0.05:
        return "quantum_higher"
    if delta < -0.05:
        return "classical_higher"
    return "classical_explains"


def _qc_summary_label(values: list[float]) -> str:
    summary = mean_std_sem_ci95(values)
    mean = float(summary["mean"])
    low = float(summary["ci95_low"])
    high = float(summary["ci95_high"])
    if int(summary["n"]) < 2:
        return "inconclusive"
    if mean > 0.05 and low > 0.0:
        return "quantum_higher"
    if mean < -0.05 and high < 0.0:
        return "classical_higher"
    if abs(mean) < 0.05 or (low <= 0.0 <= high):
        return "classical_explains"
    return "inconclusive"


def _simulate_record(
    *,
    config: dict[str, object],
    family: str,
    n_sites: int,
    realization: int,
    target_style: str,
    trap_site: int,
    disorder_strength: float,
    disorder_seed: int,
) -> dict[str, object]:
    graph_seed = _graph_seed(config, family=family, n_sites=n_sites, realization=realization)
    instance = generate_network_instance(family, n_sites=n_sites, seed=graph_seed, realization_index=realization)
    initial_site = int(n_sites) - 1
    topology = topology_metrics(instance, initial_site=initial_site, trap_site=trap_site)
    times = np.linspace(0.0, float(config["t_final"]), int(config["n_time_samples"]))
    coupling = float(config["coupling_hz"])
    dephasing_grid = np.asarray(config["dephasing_over_coupling"], dtype=float)
    seed = int(disorder_seed) + 17 * graph_seed + int(round(1000 * float(disorder_strength)))
    site_energies = static_disorder_energies(n_sites, float(disorder_strength) * coupling, seed=seed)
    scan_results = [
        simulate_transport(
            adjacency=instance.adjacency,
            coupling_hz=coupling,
            dephasing_rate_hz=float(gamma) * coupling,
            sink_rate_hz=float(config["sink_rate_hz"]),
            loss_rate_hz=float(config["loss_rate_hz"]),
            times=times,
            initial_site=initial_site,
            trap_site=trap_site,
            site_energies_hz=site_energies,
            node_coordinates=instance.coordinates,
            sink_hit_threshold=float(config["sink_hit_threshold"]),
            transfer_threshold=float(config["transfer_threshold"]),
        )
        for gamma in dephasing_grid
    ]
    record = signature_from_dephasing_scan(
        scan_results=scan_results,
        dephasing_over_coupling=dephasing_grid,
        coupling_hz=coupling,
        family=family,
        instance_id=instance.instance_id,
        graph_seed=graph_seed,
        disorder_seed=int(disorder_seed),
        disorder_strength_over_coupling=float(disorder_strength),
        target_style=target_style,
        initial_site=initial_site,
        trap_site=trap_site,
        topology=topology,
    )
    classical = simulate_classical_transport(
        adjacency=instance.adjacency,
        hopping_rate_hz=coupling,
        sink_rate_hz=float(config["sink_rate_hz"]),
        loss_rate_hz=float(config["loss_rate_hz"]),
        times=times,
        initial_site=initial_site,
        trap_site=trap_site,
        sink_hit_threshold=float(config["sink_hit_threshold"]),
        transfer_threshold=float(config["transfer_threshold"]),
    )
    delta = float(record["best_arrival"]) - float(classical.transport_efficiency)
    best_index = int(np.argmax([result.transport_efficiency for result in scan_results]))
    record.update(
        {
            "n_sites": int(n_sites),
            "realization": int(realization),
            "classical_arrival": float(classical.transport_efficiency),
            "classical_sink_hitting_time_filled": _filled_time(classical.sink_hitting_time, float(times[-1])),
            "classical_transfer_time_filled": _filled_time(classical.transfer_time_to_threshold, float(times[-1])),
            "classical_population_closure_error": float(classical.max_population_closure_error),
            "quantum_minus_classical": delta,
            "qc_case_label": _qc_case_label(delta),
            "spatial_observable_context": scan_results[best_index].spatial_observable_context,
        }
    )
    record["record_key"] = _record_key(record)
    return record


def _generate_records(config: dict[str, object], output_dir: Path) -> list[dict[str, object]]:
    output_path = output_dir / "atlas_records.csv"
    records = _read_csv(output_path) if bool(config.get("resume", False)) else []
    existing = {str(record.get("record_key") or _record_key(record)) for record in records if record}
    checkpoint_every = int(config.get("checkpoint_every", 250))
    stop_after_records = config.get("stop_after_records")
    stop_after_records = None if stop_after_records is None else int(stop_after_records)
    generated_since_checkpoint = 0

    for family in list(config["families"]):
        if stop_after_records is not None and len(records) >= stop_after_records:
            break
        for n_sites in list(config["n_sites_values"]):
            if stop_after_records is not None and len(records) >= stop_after_records:
                break
            for realization in range(_realization_count(str(family), config)):
                if stop_after_records is not None and len(records) >= stop_after_records:
                    break
                graph_seed = _graph_seed(config, family=str(family), n_sites=int(n_sites), realization=realization)
                instance = generate_network_instance(str(family), n_sites=int(n_sites), seed=graph_seed, realization_index=realization)
                initial_site = int(n_sites) - 1
                targets = _unique_targets(instance, initial_site=initial_site, target_styles=list(config["target_styles"]))
                for target_style, trap_site in targets:
                    if stop_after_records is not None and len(records) >= stop_after_records:
                        break
                    for disorder_strength in list(config["disorder_strength_over_coupling"]):
                        if stop_after_records is not None and len(records) >= stop_after_records:
                            break
                        for disorder_seed in list(config["disorder_seeds"]):
                            if stop_after_records is not None and len(records) >= stop_after_records:
                                break
                            key_record = {
                                "family": str(family),
                                "instance_id": instance.instance_id,
                                "target_style": target_style,
                                "trap_site": int(trap_site),
                                "disorder_strength_over_coupling": float(disorder_strength),
                                "disorder_seed": int(disorder_seed),
                            }
                            key = _record_key(key_record)
                            if key in existing:
                                continue
                            record = _simulate_record(
                                config=config,
                                family=str(family),
                                n_sites=int(n_sites),
                                realization=realization,
                                target_style=target_style,
                                trap_site=int(trap_site),
                                disorder_strength=float(disorder_strength),
                                disorder_seed=int(disorder_seed),
                            )
                            records.append(record)
                            existing.add(str(record["record_key"]))
                            generated_since_checkpoint += 1
                            if generated_since_checkpoint >= checkpoint_every:
                                _write_csv(records, output_path)
                                generated_since_checkpoint = 0
    _write_csv(records, output_path)
    return records


def _summary_by_family(records: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = aggregate_record_statistics(records, group_keys=("family",), metric_keys=ATLAS_METRICS)
    by_family = defaultdict(list)
    for record in records:
        by_family[str(record["family"])].append(_float(record, "quantum_minus_classical"))
    for row in rows:
        family = str(row["family"])
        row["quantum_classical_verdict"] = _qc_summary_label(by_family[family])
        row["record_count"] = len(by_family[family])
    return rows


def _summary_by_target(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return aggregate_record_statistics(
        records,
        group_keys=("family", "target_style"),
        metric_keys=(
            "best_arrival",
            "dephasing_gain",
            "best_sink_hitting_time_filled",
            "topology_target_degree",
            "topology_initial_target_distance",
            "topology_target_closeness",
            "quantum_minus_classical",
        ),
    )


def _regime_fractions(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    totals: Counter[tuple[str, str]] = Counter()
    for record in records:
        key = (str(record["family"]), f"{_float(record, 'disorder_strength_over_coupling'):.2f}")
        grouped[key][str(record["regime_label"])] += 1
        totals[key] += 1
    rows: list[dict[str, object]] = []
    for (family, disorder), counter in sorted(grouped.items()):
        total = max(totals[(family, disorder)], 1)
        dominant_label, dominant_count = counter.most_common(1)[0]
        row: dict[str, object] = {
            "family": family,
            "disorder_strength_over_coupling": disorder,
            "dominant_regime": dominant_label,
            "dominant_fraction": float(dominant_count / total),
            "record_count": int(total),
        }
        for label in SUPPORTED_REGIME_LABELS:
            row[f"fraction_{label}"] = float(counter[label] / total)
        rows.append(row)
    return rows


def _quantum_classical_rows(records: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = (
        "record_id",
        "family",
        "n_sites",
        "instance_id",
        "target_style",
        "trap_site",
        "disorder_strength_over_coupling",
        "disorder_seed",
        "best_arrival",
        "classical_arrival",
        "quantum_minus_classical",
        "qc_case_label",
    )
    return [{key: record.get(key, "") for key in keys} for record in records]


def _matrix(records: list[dict[str, object]], value_key: str) -> tuple[list[str], list[float], np.ndarray]:
    families = sorted({str(record["family"]) for record in records})
    disorders = sorted({_float(record, "disorder_strength_over_coupling") for record in records})
    values = np.full((len(families), len(disorders)), np.nan, dtype=float)
    for row, family in enumerate(families):
        for col, disorder in enumerate(disorders):
            subset = [
                _float(record, value_key)
                for record in records
                if str(record["family"]) == family and abs(_float(record, "disorder_strength_over_coupling") - disorder) < 1e-12
            ]
            values[row, col] = float(np.mean(subset)) if subset else np.nan
    return families, disorders, values


def _plot_heatmap(records: list[dict[str, object]], *, value_key: str, title: str, label: str, path: Path, cmap: str = "viridis") -> None:
    families, disorders, values = _matrix(records, value_key)
    fig, ax = plt.subplots(figsize=(max(8.0, 0.8 * len(disorders) + 4), max(5.0, 0.35 * len(families) + 2.5)), constrained_layout=True)
    im = ax.imshow(values, aspect="auto", cmap=cmap)
    ax.set_title(title)
    ax.set_xticks(np.arange(len(disorders)))
    ax.set_xticklabels([f"{value:.2f}" for value in disorders])
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    ax.set_xlabel("W/J: local irregularity compared with coherent coupling")
    ax.set_ylabel("network family")
    fig.colorbar(im, ax=ax, label=label)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _mean_by_family(records: list[dict[str, object]], key: str) -> tuple[list[str], list[float]]:
    families = sorted({str(record["family"]) for record in records})
    means = [
        float(np.mean([_float(record, key) for record in records if str(record["family"]) == family]))
        for family in families
    ]
    return families, means


def _plot_dashboard(records: list[dict[str, object]], path: Path) -> None:
    panels = [
        ("best_arrival", "target arrival"),
        ("dephasing_gain", "dephasing gain"),
        ("quantum_minus_classical", "quantum - classical"),
        ("best_final_entropy", "final entropy"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.0), constrained_layout=True)
    for ax, (key, title) in zip(axes.flat, panels, strict=False):
        families, means = _mean_by_family(records, key)
        ax.bar(np.arange(len(families)), means, color="#2d6cdf")
        ax.set_title(title)
        ax.set_xticks(np.arange(len(families)))
        ax.set_xticklabels(families, rotation=45, ha="right", fontsize=8)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Dynamic network atlas overview", fontsize=16)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_entropy_coherence(records: list[dict[str, object]], path: Path) -> None:
    panels = [
        ("best_final_entropy", "von Neumann entropy"),
        ("best_final_purity", "purity"),
        ("best_mean_coherence_l1", "mean l1 coherence"),
        ("best_participation_ratio", "participation ratio"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.0), constrained_layout=True)
    for ax, (key, title) in zip(axes.flat, panels, strict=False):
        families, means = _mean_by_family(records, key)
        ax.plot(np.arange(len(families)), means, marker="o", linewidth=2.0)
        ax.set_title(title)
        ax.set_xticks(np.arange(len(families)))
        ax.set_xticklabels(families, rotation=45, ha="right", fontsize=8)
        ax.grid(alpha=0.25)
    fig.suptitle("Mixing, coherence and spreading diagnostics", fontsize=16)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_regime_map(records: list[dict[str, object]], path: Path) -> None:
    rows = _regime_fractions(records)
    families = sorted({str(row["family"]) for row in rows})
    disorders = sorted({float(row["disorder_strength_over_coupling"]) for row in rows})
    label_to_index = {label: index for index, label in enumerate(SUPPORTED_REGIME_LABELS)}
    matrix = np.full((len(families), len(disorders)), np.nan, dtype=float)
    for row in rows:
        family_index = families.index(str(row["family"]))
        disorder_index = disorders.index(float(row["disorder_strength_over_coupling"]))
        matrix[family_index, disorder_index] = label_to_index[str(row["dominant_regime"])]
    fig, ax = plt.subplots(figsize=(max(8.0, 0.8 * len(disorders) + 4), max(5.0, 0.35 * len(families) + 2.5)), constrained_layout=True)
    im = ax.imshow(matrix, aspect="auto", cmap="tab10", vmin=0, vmax=max(len(SUPPORTED_REGIME_LABELS) - 1, 1))
    ax.set_title("Dominant physical regime by network family")
    ax.set_xticks(np.arange(len(disorders)))
    ax.set_xticklabels([f"{value:.2f}" for value in disorders])
    ax.set_yticks(np.arange(len(families)))
    ax.set_yticklabels(families)
    ax.set_xlabel("W/J: local irregularity compared with coherent coupling")
    ax.set_ylabel("network family")
    cbar = fig.colorbar(im, ax=ax, ticks=np.arange(len(SUPPORTED_REGIME_LABELS)))
    cbar.ax.set_yticklabels(SUPPORTED_REGIME_LABELS)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_embedding(records: list[dict[str, object]], path: Path) -> None:
    allowed = set(DYNAMIC_SIGNATURE_FEATURES) | {"quantum_minus_classical", "classical_arrival"}
    feature_names = [name for name in numeric_feature_names(records) if name in allowed]
    if len(feature_names) < 2 or len(records) < 3:
        path.write_text("Not enough records for embedding.\n", encoding="utf-8")
        return
    matrix = np.asarray([[_float(record, feature) for feature in feature_names] for record in records], dtype=float)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    std = np.std(matrix, axis=0)
    keep = std > 1e-12
    matrix = matrix[:, keep]
    if matrix.shape[1] < 2:
        path.write_text("Not enough varying features for embedding.\n", encoding="utf-8")
        return
    matrix = (matrix - np.mean(matrix, axis=0)) / np.std(matrix, axis=0)
    _, _, vt = np.linalg.svd(matrix, full_matrices=False)
    points = matrix @ vt[:2].T
    families = sorted({str(record["family"]) for record in records})
    fig, ax = plt.subplots(figsize=(8.5, 6.5), constrained_layout=True)
    for family in families:
        indices = [index for index, record in enumerate(records) if str(record["family"]) == family]
        ax.scatter(points[indices, 0], points[indices, 1], s=28, alpha=0.75, label=family)
    ax.set_title("2D projection of dynamic signatures")
    ax.set_xlabel("signature component 1")
    ax.set_ylabel("signature component 2")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_fingerprint_radar(records: list[dict[str, object]], path: Path) -> None:
    metrics = [
        ("best_arrival", "arrival"),
        ("dephasing_gain", "gain"),
        ("best_mean_coherence_l1", "coherence"),
        ("best_final_entropy", "entropy"),
        ("best_participation_ratio", "spread"),
        ("quantum_minus_classical", "q-classical"),
    ]
    families = sorted({str(record["family"]) for record in records})
    raw = np.asarray(
        [
            [
                float(np.mean([_float(record, key) for record in records if str(record["family"]) == family]))
                for key, _ in metrics
            ]
            for family in families
        ],
        dtype=float,
    )
    min_values = np.min(raw, axis=0)
    max_values = np.max(raw, axis=0)
    normalized = (raw - min_values) / np.maximum(max_values - min_values, 1e-12)
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
    angles = np.concatenate([angles, angles[:1]])
    fig, ax = plt.subplots(figsize=(9.0, 8.0), subplot_kw={"projection": "polar"}, constrained_layout=True)
    for row, family in zip(normalized, families, strict=False):
        values = np.concatenate([row, row[:1]])
        ax.plot(angles, values, linewidth=1.4, alpha=0.75, label=family)
    ax.set_title("Average dynamic fingerprint by family")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([label for _, label in metrics])
    ax.set_ylim(0.0, 1.0)
    ax.legend(frameon=False, fontsize=7, loc="upper right", bbox_to_anchor=(1.35, 1.15))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _write_summary(records: list[dict[str, object]], metrics: dict[str, object], path: Path) -> None:
    family_summary = _summary_by_family(records)
    top_arrival = sorted(family_summary, key=lambda row: float(row["best_arrival_mean"]), reverse=True)[:5]
    top_delta = sorted(family_summary, key=lambda row: float(row["quantum_minus_classical_mean"]), reverse=True)[:5]
    lines = [
        "# Dynamic Network Atlas",
        "",
        "This atlas compares finite network families through open quantum transport signatures.",
        "",
        "## What was measured",
        "",
        "- Target arrival: population accumulated in the target arrival channel.",
        "- Hitting time: first time the target channel crosses the chosen threshold.",
        "- Coherence, entropy, purity, Shannon entropy, participation ratio and IPR.",
        "- Spreading diagnostics: mean squared displacement and front width when coordinates exist.",
        "- Quantum minus classical arrival on the same graph, target, loss and final time.",
        "- Deterministic physical regime labels from explicit thresholds.",
        "",
        "## Numerical status",
        "",
        f"- Records: {metrics['record_count']}",
        f"- Families: {metrics['family_count']}",
        f"- Maximum trace deviation: {metrics['max_trace_deviation']:.3e}",
        f"- Maximum population closure error: {metrics['max_population_closure_error']:.3e}",
        f"- Minimum state eigenvalue: {metrics['min_state_eigenvalue']:.3e}",
        f"- Numerics pass: {metrics['numerics_pass']}",
        "",
        "## Highest mean target arrival",
        "",
    ]
    lines.extend([f"- {row['family']}: {float(row['best_arrival_mean']):.3f}" for row in top_arrival])
    lines.extend(["", "## Highest mean quantum-minus-classical arrival", ""])
    lines.extend([f"- {row['family']}: {float(row['quantum_minus_classical_mean']):.3f}" for row in top_delta])
    lines.extend(
        [
            "",
            "## Scientific caution",
            "",
            "- High entropy means more mixing, not automatically better transport.",
            "- Strong transport requires target arrival, not only spreading.",
            "- A quantum signature is not claimed when the classical control explains the arrival within 0.05 or the CI95 crosses zero.",
            "- Fractal networks are included as an exploratory geometry front, not as a final classification claim.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_outputs(records: list[dict[str, object]], config: dict[str, object], output_dir: Path) -> dict[str, object]:
    figures = output_dir / "figures"
    family_summary = _summary_by_family(records)
    target_summary = _summary_by_target(records)
    regime_rows = _regime_fractions(records)
    qc_rows = _quantum_classical_rows(records)

    write_statistics_csv(family_summary, output_dir / "atlas_summary_by_family.csv")
    write_statistics_csv(target_summary, output_dir / "atlas_summary_by_target.csv")
    _write_csv(regime_rows, output_dir / "atlas_regime_fractions.csv")
    _write_csv(qc_rows, output_dir / "quantum_classical_delta.csv")
    (output_dir / "figure_explanations_ptbr.json").write_text(json.dumps(FIGURE_EXPLANATIONS_PTBR, indent=2), encoding="utf-8")

    _plot_dashboard(records, figures / "atlas_dashboard.png")
    _plot_heatmap(records, value_key="best_arrival", title="Target arrival by family and local irregularity", label="mean target arrival", path=figures / "arrival_by_family_heatmap.png")
    _plot_entropy_coherence(records, figures / "entropy_coherence_panel.png")
    _plot_heatmap(records, value_key="quantum_minus_classical", title="Quantum minus classical target arrival", label="mean quantum - classical arrival", path=figures / "quantum_minus_classical_map.png", cmap="coolwarm")
    _plot_regime_map(records, figures / "regime_phase_map.png")
    _plot_embedding(records, figures / "signature_embedding.png")
    _plot_fingerprint_radar(records, figures / "family_fingerprint_radar.png")

    metrics = {
        "profile": str(config["profile"]),
        "record_count": len(records),
        "family_count": len({str(record["family"]) for record in records}),
        "n_sites_values": list(config["n_sites_values"]),
        "max_trace_deviation": max((_float(record, "max_trace_deviation") for record in records), default=0.0),
        "max_population_closure_error": max((_float(record, "max_population_closure_error") for record in records), default=0.0),
        "max_classical_population_closure_error": max((_float(record, "classical_population_closure_error") for record in records), default=0.0),
        "min_state_eigenvalue": min((_float(record, "min_state_eigenvalue", 1.0) for record in records), default=1.0),
        "mean_best_arrival": float(np.mean([_float(record, "best_arrival") for record in records])) if records else 0.0,
        "mean_dephasing_gain": float(np.mean([_float(record, "dephasing_gain") for record in records])) if records else 0.0,
        "mean_quantum_minus_classical": float(np.mean([_float(record, "quantum_minus_classical") for record in records])) if records else 0.0,
        "qc_case_counts": dict(Counter(str(record["qc_case_label"]) for record in records)),
    }
    metrics["numerics_pass"] = (
        float(metrics["max_trace_deviation"]) < 1e-8
        and float(metrics["max_population_closure_error"]) < 1e-8
        and float(metrics["max_classical_population_closure_error"]) < 1e-8
        and float(metrics["min_state_eigenvalue"]) > -1e-7
    )
    (output_dir / "atlas_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_summary(records, metrics, output_dir / "summary.md")
    return metrics


def run_atlas(config: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config_used.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    started_at = datetime.now(UTC)
    records = _generate_records(config, output_dir)
    metrics = _write_outputs(records, config, output_dir)
    metadata = {
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir),
        "profile": str(config["profile"]),
        "record_count": len(records),
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the dynamic network atlas for open quantum transport.")
    parser.add_argument("--profile", choices=["smoke", "evidence_prep", "strong", "intense", "resume"], default="strong")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--families", default=None, help="Comma-separated family subset for chunked strong runs.")
    parser.add_argument("--start-family", default=None, help="Skip families before this family in the configured order.")
    parser.add_argument("--stop-after-records", type=int, default=None, help="Stop after this many total records in atlas_records.csv.")
    parser.add_argument("--resume", action="store_true", help="Resume from atlas_records.csv in the selected output directory.")
    args = parser.parse_args()

    config = profile_config(args.profile)
    if args.families:
        wanted = [item.strip() for item in args.families.split(",") if item.strip()]
        unknown = sorted(set(wanted) - set(config["families"]))
        if unknown:
            raise ValueError(f"families not in selected profile: {unknown}")
        config["families"] = wanted
    if args.start_family:
        families = list(config["families"])
        if args.start_family not in families:
            raise ValueError(f"start-family not in selected profile: {args.start_family}")
        config["families"] = families[families.index(args.start_family) :]
    if args.stop_after_records is not None:
        config["stop_after_records"] = int(args.stop_after_records)
    if args.resume:
        config["resume"] = True

    if args.output_dir is not None:
        output_dir = args.output_dir
    elif args.profile == "evidence_prep":
        output_dir = ROOT / "outputs" / "transport_networks" / "dynamic_network_atlas_evidence_prep" / "latest"
    elif args.profile == "intense":
        output_dir = ROOT / "outputs" / "transport_networks" / "dynamic_network_atlas_intense" / "latest"
    else:
        output_dir = ROOT / "outputs" / "transport_networks" / "dynamic_network_atlas" / "latest"
    metrics = run_atlas(config, output_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
