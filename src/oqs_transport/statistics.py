from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


def mean_std_sem_ci95(values: Iterable[float]) -> dict[str, float | int]:
    arr = np.asarray([float(value) for value in values if np.isfinite(float(value))], dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"n": 0, "mean": 0.0, "std": 0.0, "sem": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    sem = float(std / np.sqrt(n)) if n > 1 else 0.0
    delta = 1.96 * sem
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "sem": sem,
        "ci95_low": mean - delta,
        "ci95_high": mean + delta,
    }


def aggregate_record_statistics(
    records: list[dict[str, object]],
    *,
    group_keys: tuple[str, ...],
    metric_keys: tuple[str, ...],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = tuple(str(record.get(name, "")) for name in group_keys)
        grouped[key].append(record)

    rows: list[dict[str, object]] = []
    for group_values, items in sorted(grouped.items()):
        row: dict[str, object] = {name: value for name, value in zip(group_keys, group_values, strict=False)}
        for metric in metric_keys:
            summary = mean_std_sem_ci95(float(item.get(metric, 0.0)) for item in items)
            for summary_key, summary_value in summary.items():
                row[f"{metric}_{summary_key}"] = summary_value
        rows.append(row)
    return rows


def write_statistics_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
