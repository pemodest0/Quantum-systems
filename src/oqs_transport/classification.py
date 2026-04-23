from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClassificationResult:
    label_name: str
    labels: tuple[str, ...]
    feature_names: tuple[str, ...]
    split_strategy: str
    group_key: str | None
    n_repeats: int
    accuracy: float
    baseline_accuracy: float
    accuracy_mean: float
    accuracy_std: float
    accuracy_ci95: tuple[float, float]
    baseline_ci95: tuple[float, float]
    repeat_metrics: list[dict[str, float | int]]
    confusion_matrix: list[list[int]]
    feature_importance: list[dict[str, float | str]]
    embedding_2d: list[dict[str, float | str]]
    predictions: list[dict[str, object]]


def _feature_matrix(records: list[dict[str, object]], feature_names: list[str]) -> np.ndarray:
    matrix = np.asarray([[float(record.get(name, 0.0)) for name in feature_names] for record in records], dtype=float)
    matrix[~np.isfinite(matrix)] = 0.0
    return matrix


def _standardize(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = np.mean(matrix, axis=0)
    scale = np.std(matrix, axis=0)
    scale[scale <= 1e-12] = 1.0
    return (matrix - mean) / scale, mean, scale


def _standardize_with_train(matrix: np.ndarray, train_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = matrix[train_idx]
    mean = np.mean(train, axis=0)
    scale = np.std(train, axis=0)
    scale[scale <= 1e-12] = 1.0
    return (matrix - mean) / scale, mean, scale


def _stratified_row_split(
    labels: list[str],
    *,
    test_fraction: float = 0.30,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    by_label: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        by_label.setdefault(label, []).append(index)
    train: list[int] = []
    test: list[int] = []
    for label, indices in sorted(by_label.items()):
        indices = list(indices)
        rng.shuffle(indices)
        if len(indices) < 3:
            train.extend(indices)
            test.extend(indices)
            continue
        n_test = max(1, int(round(len(indices) * test_fraction)))
        test.extend(indices[:n_test])
        train.extend(indices[n_test:])
    return np.asarray(train, dtype=int), np.asarray(test, dtype=int)


def _stratified_group_split(
    records: list[dict[str, object]],
    labels: list[str],
    *,
    group_key: str,
    test_fraction: float = 0.30,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    group_to_indices: dict[str, list[int]] = {}
    group_to_label: dict[str, str] = {}
    for index, record in enumerate(records):
        group = str(record.get(group_key, record.get("record_id", index)))
        group_to_indices.setdefault(group, []).append(index)
        group_to_label.setdefault(group, labels[index])

    groups_by_label: dict[str, list[str]] = {}
    for group, label in group_to_label.items():
        groups_by_label.setdefault(label, []).append(group)

    train_groups: set[str] = set()
    test_groups: set[str] = set()
    for label, groups in sorted(groups_by_label.items()):
        groups = list(groups)
        rng.shuffle(groups)
        if len(groups) < 2:
            train_groups.update(groups)
            continue
        n_test = max(1, int(round(len(groups) * test_fraction)))
        test_groups.update(groups[:n_test])
        train_groups.update(groups[n_test:])

    train = [index for group in sorted(train_groups) for index in group_to_indices[group]]
    test = [index for group in sorted(test_groups) for index in group_to_indices[group]]
    if not train or not test:
        raise ValueError("group split requires at least two groups and non-empty train/test partitions")
    overlap = set(train_groups).intersection(test_groups)
    if overlap:
        raise RuntimeError(f"group split leakage detected for groups: {sorted(overlap)[:5]}")
    return np.asarray(train, dtype=int), np.asarray(test, dtype=int)


def _split_indices(
    records: list[dict[str, object]],
    labels: list[str],
    *,
    split_strategy: str,
    group_key: str | None,
    test_fraction: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    if split_strategy == "row":
        return _stratified_row_split(labels, test_fraction=test_fraction, rng=rng)
    if split_strategy == "group":
        if not group_key:
            raise ValueError("group_key is required when split_strategy='group'")
        return _stratified_group_split(records, labels, group_key=group_key, test_fraction=test_fraction, rng=rng)
    raise ValueError(f"unsupported split_strategy: {split_strategy}")


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _fit_multiclass_logistic(
    features: np.ndarray,
    y: np.ndarray,
    *,
    n_classes: int,
    learning_rate: float = 0.15,
    l2: float = 1e-3,
    n_steps: int = 900,
) -> tuple[np.ndarray, np.ndarray]:
    n_samples, n_features = features.shape
    weights = np.zeros((n_features, n_classes), dtype=float)
    bias = np.zeros(n_classes, dtype=float)
    targets = np.zeros((n_samples, n_classes), dtype=float)
    targets[np.arange(n_samples), y] = 1.0
    for _ in range(n_steps):
        probabilities = _softmax(features @ weights + bias)
        error = probabilities - targets
        grad_w = (features.T @ error) / max(n_samples, 1) + l2 * weights
        grad_b = np.mean(error, axis=0)
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
    return weights, bias


def _predict(features: np.ndarray, weights: np.ndarray, bias: np.ndarray) -> np.ndarray:
    return np.argmax(features @ weights + bias, axis=1)


def _confusion(true: np.ndarray, predicted: np.ndarray, n_classes: int) -> list[list[int]]:
    matrix = np.zeros((n_classes, n_classes), dtype=int)
    for left, right in zip(true, predicted, strict=False):
        matrix[int(left), int(right)] += 1
    return matrix.tolist()


def _ci95(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    if arr.size <= 1:
        return (mean, mean)
    sem = float(np.std(arr, ddof=1) / np.sqrt(arr.size))
    delta = 1.96 * sem
    return (mean - delta, mean + delta)


def _pca_2d(features: np.ndarray) -> np.ndarray:
    if features.shape[0] == 0:
        return np.zeros((0, 2), dtype=float)
    centered = features - np.mean(features, axis=0, keepdims=True)
    if centered.shape[1] == 1:
        return np.column_stack([centered[:, 0], np.zeros(centered.shape[0])])
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:2].T
    if components.shape[1] < 2:
        projected = centered @ components
        return np.column_stack([projected[:, 0], np.zeros(projected.shape[0])])
    return centered @ components


def classify_records(
    records: list[dict[str, object]],
    *,
    feature_names: list[str],
    label_name: str = "family",
    split_strategy: str = "row",
    group_key: str | None = None,
    n_repeats: int = 1,
    test_fraction: float = 0.30,
    random_seed: int = 0,
) -> ClassificationResult:
    if not records:
        raise ValueError("records must not be empty")
    if not feature_names:
        raise ValueError("feature_names must not be empty")
    labels = [str(record[label_name]) for record in records]
    label_values = tuple(sorted(set(labels)))
    label_to_index = {label: index for index, label in enumerate(label_values)}
    y = np.asarray([label_to_index[label] for label in labels], dtype=int)
    x = _feature_matrix(records, feature_names)
    n_repeats = max(1, int(n_repeats))
    rng = np.random.default_rng(random_seed)
    repeat_metrics: list[dict[str, float | int]] = []
    accuracies: list[float] = []
    baselines: list[float] = []
    confusion_total = np.zeros((len(label_values), len(label_values)), dtype=int)
    importance_stack: list[np.ndarray] = []
    first_predictions: list[dict[str, object]] | None = None

    for repeat in range(n_repeats):
        train_idx, test_idx = _split_indices(
            records,
            labels,
            split_strategy=split_strategy,
            group_key=group_key,
            test_fraction=test_fraction,
            rng=rng,
        )
        x_scaled, _, _ = _standardize_with_train(x, train_idx)
        weights, bias = _fit_multiclass_logistic(x_scaled[train_idx], y[train_idx], n_classes=len(label_values))
        pred_all = _predict(x_scaled, weights, bias)
        pred_test = pred_all[test_idx]
        y_test = y[test_idx]
        accuracy = float(np.mean(pred_test == y_test)) if y_test.size else 0.0
        majority = Counter(y[train_idx]).most_common(1)[0][0] if train_idx.size else 0
        baseline_accuracy = float(np.mean(y_test == majority)) if y_test.size else 0.0
        accuracies.append(accuracy)
        baselines.append(baseline_accuracy)
        confusion_total += np.asarray(_confusion(y_test, pred_test, len(label_values)), dtype=int)
        importance_stack.append(np.mean(np.abs(weights), axis=1))
        repeat_metrics.append(
            {
                "repeat": repeat,
                "accuracy": accuracy,
                "baseline_accuracy": baseline_accuracy,
                "n_train": int(train_idx.size),
                "n_test": int(test_idx.size),
            }
        )
        if first_predictions is None:
            test_lookup = set(test_idx.tolist())
            first_predictions = [
                {
                    "record_id": str(record.get("record_id", index)),
                    "true_label": labels[index],
                    "predicted_label": label_values[int(pred_all[index])],
                    "is_test": bool(index in test_lookup),
                    "correct": bool(pred_all[index] == y[index]),
                }
                for index, record in enumerate(records)
            ]

    accuracy_mean = float(np.mean(accuracies))
    accuracy_std = float(np.std(accuracies, ddof=1)) if len(accuracies) > 1 else 0.0
    baseline_mean = float(np.mean(baselines))
    importance_values = np.mean(np.asarray(importance_stack, dtype=float), axis=0)
    order = np.argsort(importance_values)[::-1]
    feature_importance = [
        {"feature": feature_names[int(index)], "importance": float(importance_values[int(index)])}
        for index in order[: min(20, len(order))]
    ]
    x_scaled, _, _ = _standardize(x)
    embedding = _pca_2d(x_scaled)
    embedding_payload = [
        {
            "record_id": str(record.get("record_id", index)),
            "family": str(record.get(label_name, "")),
            "x": float(embedding[index, 0]),
            "y": float(embedding[index, 1]),
        }
        for index, record in enumerate(records)
    ]
    return ClassificationResult(
        label_name=label_name,
        labels=label_values,
        feature_names=tuple(feature_names),
        split_strategy=split_strategy,
        group_key=group_key,
        n_repeats=n_repeats,
        accuracy=accuracy_mean,
        baseline_accuracy=baseline_mean,
        accuracy_mean=accuracy_mean,
        accuracy_std=accuracy_std,
        accuracy_ci95=_ci95(accuracies),
        baseline_ci95=_ci95(baselines),
        repeat_metrics=repeat_metrics,
        confusion_matrix=confusion_total.tolist(),
        feature_importance=feature_importance,
        embedding_2d=embedding_payload,
        predictions=[] if first_predictions is None else first_predictions,
    )


def classify_train_test_records(
    train_records: list[dict[str, object]],
    test_records: list[dict[str, object]],
    *,
    feature_names: list[str],
    label_name: str = "family",
) -> ClassificationResult:
    if not train_records or not test_records:
        raise ValueError("train_records and test_records must not be empty")
    records = train_records + test_records
    labels = [str(record[label_name]) for record in records]
    label_values = tuple(sorted(set(labels)))
    label_to_index = {label: index for index, label in enumerate(label_values)}
    y = np.asarray([label_to_index[label] for label in labels], dtype=int)
    train_idx = np.arange(len(train_records), dtype=int)
    test_idx = np.arange(len(train_records), len(records), dtype=int)
    x = _feature_matrix(records, feature_names)
    x_scaled, _, _ = _standardize_with_train(x, train_idx)
    weights, bias = _fit_multiclass_logistic(x_scaled[train_idx], y[train_idx], n_classes=len(label_values))
    pred_all = _predict(x_scaled, weights, bias)
    pred_test = pred_all[test_idx]
    y_test = y[test_idx]
    accuracy = float(np.mean(pred_test == y_test)) if y_test.size else 0.0
    majority = Counter(y[train_idx]).most_common(1)[0][0] if train_idx.size else 0
    baseline_accuracy = float(np.mean(y_test == majority)) if y_test.size else 0.0
    importance_values = np.mean(np.abs(weights), axis=1)
    order = np.argsort(importance_values)[::-1]
    feature_importance = [
        {"feature": feature_names[int(index)], "importance": float(importance_values[int(index)])}
        for index in order[: min(20, len(order))]
    ]
    x_embedding, _, _ = _standardize(x)
    embedding = _pca_2d(x_embedding)
    embedding_payload = [
        {
            "record_id": str(record.get("record_id", index)),
            "family": str(record.get(label_name, "")),
            "x": float(embedding[index, 0]),
            "y": float(embedding[index, 1]),
        }
        for index, record in enumerate(records)
    ]
    predictions = [
        {
            "record_id": str(record.get("record_id", index)),
            "true_label": labels[index],
            "predicted_label": label_values[int(pred_all[index])],
            "is_test": bool(index >= len(train_records)),
            "correct": bool(pred_all[index] == y[index]),
        }
        for index, record in enumerate(records)
    ]
    return ClassificationResult(
        label_name=label_name,
        labels=label_values,
        feature_names=tuple(feature_names),
        split_strategy="fixed_train_test",
        group_key=None,
        n_repeats=1,
        accuracy=accuracy,
        baseline_accuracy=baseline_accuracy,
        accuracy_mean=accuracy,
        accuracy_std=0.0,
        accuracy_ci95=(accuracy, accuracy),
        baseline_ci95=(baseline_accuracy, baseline_accuracy),
        repeat_metrics=[
            {
                "repeat": 0,
                "accuracy": accuracy,
                "baseline_accuracy": baseline_accuracy,
                "n_train": int(train_idx.size),
                "n_test": int(test_idx.size),
            }
        ],
        confusion_matrix=_confusion(y_test, pred_test, len(label_values)),
        feature_importance=feature_importance,
        embedding_2d=embedding_payload,
        predictions=predictions,
    )


def classification_result_to_dict(result: ClassificationResult) -> dict[str, object]:
    return {
        "label_name": result.label_name,
        "labels": list(result.labels),
        "feature_names": list(result.feature_names),
        "split_strategy": result.split_strategy,
        "group_key": result.group_key,
        "n_repeats": result.n_repeats,
        "accuracy": result.accuracy,
        "baseline_accuracy": result.baseline_accuracy,
        "accuracy_mean": result.accuracy_mean,
        "accuracy_std": result.accuracy_std,
        "accuracy_ci95": list(result.accuracy_ci95),
        "baseline_ci95": list(result.baseline_ci95),
        "repeat_metrics": result.repeat_metrics,
        "confusion_matrix": result.confusion_matrix,
        "feature_importance": result.feature_importance,
        "embedding_2d": result.embedding_2d,
        "predictions": result.predictions,
    }
