from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oqs_transport.local_rag import (  # noqa: E402
    DEFAULT_GENERATION_MODEL,
    DEFAULT_OLLAMA_URL,
    generate_with_ollama,
    load_index,
    ollama_available,
    retrieve,
)


def _print_retrieved(retrieved: list[dict[str, object]]) -> None:
    for index, item in enumerate(retrieved, start=1):
        chunk = dict(item["chunk"])
        preview = str(chunk["text"])[:420].strip()
        print(f"\n[{index}] score={float(item['score']):.3f} source={chunk['source_path']}")
        print(preview)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the local transport-lab assistant.")
    parser.add_argument("question", nargs="+", help="Question to ask over the local transport research index.")
    parser.add_argument("--index", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "transport_research_index.json"))
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--generate", action="store_true", help="Use Ollama to generate an answer from retrieved chunks.")
    parser.add_argument("--model", default=DEFAULT_GENERATION_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args(argv)

    question = " ".join(args.question)
    index = load_index(Path(args.index))
    retrieved = retrieve(index, question, top_k=args.top_k)
    if not args.generate:
        print(json.dumps({"question": question, "mode": "retrieval_only", "top_k": args.top_k}, indent=2, ensure_ascii=False))
        _print_retrieved(retrieved)
        return 0

    if not ollama_available(base_url=args.ollama_url):
        print("Ollama is not available. Retrieval results are shown below; install/start Ollama to enable generation.")
        _print_retrieved(retrieved)
        return 2

    answer = generate_with_ollama(question=question, retrieved=retrieved, model=args.model, base_url=args.ollama_url)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
