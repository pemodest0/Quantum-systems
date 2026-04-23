from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


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

from oqs_transport.local_rag import load_index, retrieve  # noqa: E402


def _load_exercises(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    exercises = payload.get("exercises", [])
    if not isinstance(exercises, list):
        raise ValueError("Exercise bank must contain an exercises list.")
    return [dict(item) for item in exercises]


def _keyword_score(expected_answer: str, retrieved_text: str) -> float:
    expected_tokens = {
        token
        for token in expected_answer.lower().replace("/", " ").replace("_", " ").split()
        if len(token) >= 4 and token not in {"with", "from", "that", "this", "para", "como", "because"}
    }
    if not expected_tokens:
        return 0.0
    matched = sum(1 for token in expected_tokens if token in retrieved_text)
    return matched / len(expected_tokens)


def _has_confusion_risk(exercise: dict[str, object], retrieved_text: str) -> bool:
    exercise_id = str(exercise.get("id", ""))
    if exercise_id in {"trap-001", "figure-011"}:
        return "target arrival" not in retrieved_text and "arrival" not in retrieved_text
    if exercise_id in {"trap-005", "concept-009"}:
        return "successful" not in retrieved_text and "failure" not in retrieved_text
    if exercise_id == "figure-004":
        return "0.02" not in retrieved_text
    return False


def evaluate(index: dict[str, object], exercises: list[dict[str, object]], *, top_k: int) -> dict[str, object]:
    results = []
    pass_count = 0
    hallucination_guard_violations = 0
    for exercise in exercises:
        question = str(exercise.get("question", ""))
        expected_answer = str(exercise.get("expected_answer", ""))
        retrieved = retrieve(index, question, top_k=top_k)
        retrieved_text = " ".join(str(dict(item["chunk"]).get("text", "")).lower() for item in retrieved)
        source_count = sum(1 for item in retrieved if float(item.get("score", 0.0)) > 0.0)
        keyword_score = _keyword_score(expected_answer, retrieved_text)
        confusion_risk = _has_confusion_risk(exercise, retrieved_text)
        passed = source_count > 0 and keyword_score >= 0.20 and not confusion_risk
        if passed:
            pass_count += 1
        if str(exercise.get("category")) == "trap" and source_count <= 0:
            hallucination_guard_violations += 1
        results.append(
            {
                "id": exercise.get("id"),
                "category": exercise.get("category"),
                "source_count": source_count,
                "keyword_score": round(keyword_score, 3),
                "confusion_risk": confusion_risk,
                "passed": passed,
                "top_source": dict(retrieved[0]["chunk"]).get("source_path", "") if retrieved else "",
            }
        )
    score = pass_count / max(len(exercises), 1)
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "exercise_count": len(exercises),
        "passed": pass_count,
        "score": round(score, 3),
        "hallucination_guard_violations": hallucination_guard_violations,
        "accepted": score >= 0.80 and hallucination_guard_violations == 0,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate local physics assistant retrieval readiness.")
    parser.add_argument("--index", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "physics_assistant_index.json"))
    parser.add_argument("--exercise-bank", default=str(ROOT / "docs" / "physics_exercises" / "transport_exercise_bank.json"))
    parser.add_argument("--output", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "physics_assistant_eval.json"))
    parser.add_argument("--top-k", type=int, default=7)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    index = load_index(Path(args.index))
    exercises = _load_exercises(Path(args.exercise_bank))
    if args.limit > 0:
        exercises = exercises[: args.limit]
    report = evaluate(index, exercises, top_k=args.top_k)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["exercise_count", "passed", "score", "hallucination_guard_violations", "accepted"]}, indent=2, ensure_ascii=False))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
