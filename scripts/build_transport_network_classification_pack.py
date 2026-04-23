from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from oqs_transport import (  # noqa: E402
    DYNAMIC_SIGNATURE_FEATURES,
    classification_result_to_dict,
    classify_records,
    classify_train_test_records,
)


def _maybe_float(value: str) -> object:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return value
    if np.isfinite(converted):
        return converted
    return value


def _read_records(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        records = [{key: _maybe_float(value) for key, value in row.items()} for row in csv.DictReader(handle)]
    for record in records:
        if "validation_group_id" not in record or not record["validation_group_id"]:
            record["validation_group_id"] = f"{record.get('family', 'unknown')}_N{int(float(record.get('n_sites', 0)))}_seed{int(float(record.get('graph_seed', 0)))}"
    return records


def _feature_sets(records: list[dict[str, object]]) -> dict[str, list[str]]:
    dynamic = [name for name in DYNAMIC_SIGNATURE_FEATURES if name in records[0]]
    topology = sorted(name for name in records[0] if name.startswith("topology_"))
    classical = [
        "classical_arrival",
        "classical_sink_hitting_time_filled",
        "classical_loss_population",
        "classical_network_population",
    ]
    difference = [
        "arrival_quantum_minus_classical",
        "hitting_time_quantum_minus_classical",
        "loss_quantum_minus_classical",
    ]
    return {
        "dynamic_only": dynamic,
        "topology_only": topology,
        "classical_only": [name for name in classical if name in records[0]],
        "quantum_minus_classical": [name for name in difference if name in records[0]],
        "combined": dynamic + topology,
    }


def _write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _classification_suite(records: list[dict[str, object]], *, n_repeats: int) -> dict[str, object]:
    reports: dict[str, object] = {}
    for name, features in _feature_sets(records).items():
        if not features:
            continue
        reports[name] = classification_result_to_dict(
            classify_records(
                records,
                feature_names=features,
                label_name="family",
                split_strategy="group",
                group_key="validation_group_id",
                n_repeats=n_repeats,
                random_seed=31,
            )
        )
    return reports


def _size_generalization(records: list[dict[str, object]]) -> dict[str, object]:
    reports: dict[str, object] = {}
    feature_sets = _feature_sets(records)
    train_records = [record for record in records if int(round(float(record.get("n_sites", 0)))) == 8]
    if not train_records:
        return {"not_applicable": "No N=8 training records found."}
    for target_n in sorted({int(round(float(record.get("n_sites", 0)))) for record in records if int(round(float(record.get("n_sites", 0)))) != 8}):
        test_records = [record for record in records if int(round(float(record.get("n_sites", 0)))) == target_n]
        if not test_records:
            continue
        reports[f"train_N8_test_N{target_n}"] = {}
        for name, features in feature_sets.items():
            if not features:
                continue
            reports[f"train_N8_test_N{target_n}"][name] = classification_result_to_dict(
                classify_train_test_records(train_records, test_records, feature_names=features, label_name="family")
            )
    return reports


def _per_family_summary(records: list[dict[str, object]], combined_report: dict[str, object]) -> list[dict[str, object]]:
    predictions = [item for item in combined_report.get("predictions", []) if item.get("is_test")]
    by_family_pred: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in predictions:
        by_family_pred[str(item.get("true_label", ""))].append(item)
    rows: list[dict[str, object]] = []
    for family in sorted({str(record["family"]) for record in records}):
        items = [record for record in records if str(record["family"]) == family]
        pred_items = by_family_pred.get(family, [])
        rows.append(
            {
                "family": family,
                "n_records": len(items),
                "mean_arrival": float(np.mean([float(record.get("best_arrival", 0.0)) for record in items])),
                "mean_dephasing_gain": float(np.mean([float(record.get("dephasing_gain", 0.0)) for record in items])),
                "mean_best_dephasing": float(np.mean([float(record.get("best_dephasing_over_coupling", 0.0)) for record in items])),
                "combined_test_accuracy_first_split": float(np.mean([bool(item.get("correct", False)) for item in pred_items])) if pred_items else 0.0,
            }
        )
    return rows


def _plot_accuracy(reports: dict[str, object], output_path: Path) -> None:
    names = list(reports)
    accuracy = [float(reports[name].get("accuracy_mean", 0.0)) for name in names]
    baseline = [float(reports[name].get("baseline_accuracy", 0.0)) for name in names]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    ax.bar(x - 0.18, accuracy, width=0.36, label="classifier", color="#1565c0")
    ax.bar(x + 0.18, baseline, width=0.36, label="majority baseline", color="#9e9e9e")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("group-split accuracy")
    ax.set_title("Network-family classification by feature set")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_confusion(report: dict[str, object], output_path: Path) -> None:
    labels = [str(label) for label in report.get("labels", [])]
    matrix = np.asarray(report.get("confusion_matrix", []), dtype=float)
    row_sums = matrix.sum(axis=1, keepdims=True)
    normalized = np.divide(matrix, row_sums, out=np.zeros_like(matrix), where=row_sums > 0)
    fig, ax = plt.subplots(figsize=(8.2, 7.4), constrained_layout=True)
    im = ax.imshow(normalized, cmap="Blues", vmin=0.0, vmax=1.0)
    ax.set_title("Combined-feature confusion matrix")
    ax.set_xlabel("predicted family")
    ax.set_ylabel("true family")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    fig.colorbar(im, ax=ax, label="row-normalized count")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_importance(report: dict[str, object], output_path: Path) -> None:
    items = list(report.get("feature_importance", []))[:15]
    labels = [str(item["feature"]) for item in items][::-1]
    values = [float(item["importance"]) for item in items][::-1]
    fig, ax = plt.subplots(figsize=(8.6, 5.8), constrained_layout=True)
    ax.barh(labels, values, color="#2e7d32")
    ax.set_xlabel("logistic-model absolute weight")
    ax.set_title("Most useful features for graph-family classification")
    ax.grid(axis="x", alpha=0.25)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_embedding(report: dict[str, object], output_path: Path) -> None:
    points = list(report.get("embedding_2d", []))
    families = sorted({str(item["family"]) for item in points})
    cmap = plt.get_cmap("tab20")
    color_by_family = {family: cmap(index / max(len(families), 1)) for index, family in enumerate(families)}
    fig, ax = plt.subplots(figsize=(8.2, 6.0), constrained_layout=True)
    for family in families:
        family_points = [item for item in points if str(item["family"]) == family]
        ax.scatter(
            [float(item["x"]) for item in family_points],
            [float(item["y"]) for item in family_points],
            s=18,
            alpha=0.72,
            label=family,
            color=color_by_family[family],
        )
    ax.set_title("2D projection of dynamic + topology signatures")
    ax.set_xlabel("PCA axis 1")
    ax.set_ylabel("PCA axis 2")
    ax.legend(fontsize=7, ncol=2, frameon=True)
    ax.grid(alpha=0.20)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_size_generalization(size_report: dict[str, object], output_path: Path) -> None:
    rows: list[tuple[str, str, float, float]] = []
    for split_name, split_payload in size_report.items():
        if not isinstance(split_payload, dict):
            continue
        for feature_set, report in split_payload.items():
            if isinstance(report, dict):
                rows.append((split_name, feature_set, float(report.get("accuracy_mean", 0.0)), float(report.get("baseline_accuracy", 0.0))))
    if not rows:
        return
    labels = [f"{split}\n{feature}" for split, feature, _, _ in rows]
    accuracies = [item[2] for item in rows]
    baselines = [item[3] for item in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(max(8.5, 0.55 * len(rows)), 5.4), constrained_layout=True)
    ax.bar(x - 0.18, accuracies, width=0.36, label="classifier", color="#6a1b9a")
    ax.bar(x + 0.18, baselines, width=0.36, label="baseline", color="#bdbdbd")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("fixed-size transfer accuracy")
    ax.set_title("Train on N=8, test on larger networks")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _write_summary(output_dir: Path, reports: dict[str, object], size_report: dict[str, object], per_family: list[dict[str, object]]) -> None:
    combined = reports.get("combined", {})
    dynamic = reports.get("dynamic_only", {})
    topology = reports.get("topology_only", {})
    classical = reports.get("classical_only", {})
    lines = [
        "# Network Classification Complete Pack",
        "",
        "## Scientific Question",
        "",
        "Can we recognize the network family by looking at the open-transport dynamics?",
        "",
        "## Plain Reading",
        "",
        "- `dynamic_only`: uses only transport behavior, such as target arrival, coherence, entropy, and participation.",
        "- `topology_only`: uses graph numbers directly, such as degree, distance, and spectral measures.",
        "- `classical_only`: uses a classical rate-walk control.",
        "- `combined`: uses dynamic signatures plus topology numbers.",
        "- `group split`: keeps the same graph instance out of both train and test, avoiding leakage.",
        "",
        "## Main Result",
        "",
        f"- Dynamic-only accuracy: {float(dynamic.get('accuracy_mean', 0.0)):.3f}.",
        f"- Topology-only accuracy: {float(topology.get('accuracy_mean', 0.0)):.3f}.",
        f"- Classical-only accuracy: {float(classical.get('accuracy_mean', 0.0)):.3f}.",
        f"- Combined accuracy: {float(combined.get('accuracy_mean', 0.0)):.3f}.",
        f"- Combined baseline: {float(combined.get('baseline_accuracy', 0.0)):.3f}.",
        "",
        "## Interpretation",
        "",
        "The classification claim is meaningful only because the split is by graph instance, not by row. If row-level splitting were used, nearby parameter rows from the same graph could leak into train and test.",
        "",
        "## Per-Family Reading",
        "",
        "| Family | Records | Mean arrival | Mean gain | First-split accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in per_family:
        lines.append(
            f"| `{row['family']}` | {row['n_records']} | {float(row['mean_arrival']):.3f} | "
            f"{float(row['mean_dephasing_gain']):.3f} | {float(row['combined_test_accuracy_first_split']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Size Generalization",
            "",
            "The size-generalization block trains on N=8 and tests on N=10 or N=12. If this fails, the fingerprint may be size-specific rather than family-specific.",
            "",
            f"Available splits: {', '.join(str(key) for key in size_report.keys())}.",
            "",
            "## Next Action",
            "",
            "Use the confusion matrix to pick the most confused family pair and design one focused campaign for that pair.",
            "",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _copy_latest(output_dir: Path, latest_dir: Path) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        target = latest_dir / path.name
        if path.is_dir():
            target.mkdir(exist_ok=True)
            for child in path.iterdir():
                if child.is_file():
                    (target / child.name).write_bytes(child.read_bytes())
        elif path.is_file():
            target.write_bytes(path.read_bytes())


def build_pack(source_dir: Path, output_dir: Path, *, n_repeats: int) -> dict[str, object]:
    source_csv = source_dir / "dynamic_signatures_with_classical.csv"
    if not source_csv.exists():
        raise FileNotFoundError(f"missing dynamic signature source: {source_csv}")
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    records = _read_records(source_csv)
    reports = _classification_suite(records, n_repeats=n_repeats)
    size_report = _size_generalization(records)
    combined = reports.get("combined", {})
    per_family = _per_family_summary(records, combined if isinstance(combined, dict) else {})
    metrics = {
        "source_dir": str(source_dir),
        "record_count": len(records),
        "family_count": len({str(record["family"]) for record in records}),
        "n_repeats": n_repeats,
        "dynamic_accuracy": float(reports.get("dynamic_only", {}).get("accuracy_mean", 0.0)),
        "topology_accuracy": float(reports.get("topology_only", {}).get("accuracy_mean", 0.0)),
        "classical_accuracy": float(reports.get("classical_only", {}).get("accuracy_mean", 0.0)),
        "combined_accuracy": float(reports.get("combined", {}).get("accuracy_mean", 0.0)),
        "combined_baseline": float(reports.get("combined", {}).get("baseline_accuracy", 0.0)),
    }
    (output_dir / "classification_reports.json").write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "size_generalization_report.json").write_text(json.dumps(size_report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "per_family_summary.json").write_text(json.dumps({"rows": per_family}, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(per_family, output_dir / "per_family_summary.csv")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "run_metadata.json").write_text(json.dumps({"generated_at_utc": datetime.now(UTC).isoformat(), "source_dir": str(source_dir)}, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_summary(output_dir, reports, size_report, per_family)

    _plot_accuracy(reports, figures_dir / "accuracy_by_feature_set.png")
    if isinstance(combined, dict) and combined:
        _plot_confusion(combined, figures_dir / "combined_confusion_matrix.png")
        _plot_importance(combined, figures_dir / "combined_feature_importance.png")
        _plot_embedding(combined, figures_dir / "combined_embedding_2d.png")
    _plot_size_generalization(size_report, figures_dir / "size_generalization_transfer.png")
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a complete network-family classification pack from dynamic transport signatures.")
    parser.add_argument("--source-dir", default=str(ROOT / "outputs" / "transport_networks" / "paper_reproduction_suite" / "latest"))
    parser.add_argument("--output-subdir", default="network_classification_complete")
    parser.add_argument("--n-repeats", type=int, default=40)
    args = parser.parse_args(argv)
    source_dir = Path(args.source_dir).resolve()
    output_dir = ROOT / "outputs" / "transport_networks" / args.output_subdir / "latest"
    metrics = build_pack(source_dir, output_dir, n_repeats=args.n_repeats)
    print(json.dumps({"output_dir": str(output_dir), **metrics}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
