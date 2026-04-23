from __future__ import annotations

import argparse
import json
import sys
import urllib.error
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

from oqs_transport.local_rag import (  # noqa: E402
    DEFAULT_GENERATION_MODEL,
    DEFAULT_OLLAMA_URL,
    generate_prompt_with_ollama,
    load_index,
    ollama_available,
    retrieve,
)


MODE_PROMPTS = {
    "tutor": (
        "Mode: tutor. Explain slowly, in simple PT-BR, with equations only when useful. "
        "Translate lab shorthand: W/J is disorder strength compared with hopping; gamma_phi/J is phase scrambling compared with hopping; target arrival is successful capture. "
        "For definitions, use one bullet per concept and never merge target arrival with loss."
    ),
    "critic": (
        "Mode: critic. Look for overclaims, weak statistics, ambiguous observables, missing ensemble support, and confusion between spreading and target arrival. "
        "Be strict and concise."
    ),
    "paper_matcher": (
        "Mode: paper_matcher. Compare the question or result against the retrieved paper cards. "
        "State what each cited paper supports and what it does not support."
    ),
    "lab_analyst": (
        "Mode: lab_analyst. Explain campaign numbers and figures in plain PT-BR: axes, symbols, colors, measured trend, expected trend, strength, and uncertainty."
    ),
    "planner": (
        "Mode: planner. Suggest exactly one next simulation or refinement. Do not execute campaigns, do not edit configs, and state the reason for the suggested next action."
    ),
}


TERM_EXPANSIONS = {
    "sink": "target arrival successful capture kappa trap site rho_target target channel",
    "target": "target arrival successful capture kappa trap site",
    "loss": "uncontrolled failure loss Gamma parasitic dissipation lost channel",
    "dephasing": "phase scrambling gamma_phi coherence local dephasing projector",
    "dephas": "phase scrambling gamma_phi coherence local dephasing projector",
    "entropy": "von Neumann entropy Shannon population entropy mixedness",
    "entrop": "von Neumann entropy Shannon population entropy mixedness",
    "purity": "purity Tr rho squared mixedness",
    "pureza": "purity Tr rho squared mixedness",
    "ipr": "inverse participation ratio participation spread localization",
    "spreading": "mean squared displacement front width spatial spreading target arrival not same",
    "espalh": "mean squared displacement front width spatial spreading target arrival not same",
}


def _requested_terms(question: str) -> list[str]:
    lower = question.lower()
    terms: list[str] = []
    for term in ["sink", "target", "loss", "dephasing", "entropy", "entropia", "purity", "pureza", "ipr", "spreading", "espalhamento"]:
        if term in lower:
            terms.append(term)
    return terms


def _expand_query(question: str) -> str:
    lower = question.lower()
    expansions = [value for key, value in TERM_EXPANSIONS.items() if key in lower]
    return question if not expansions else question + " " + " ".join(expansions)


def _sources_payload(retrieved: list[dict[str, object]]) -> list[dict[str, object]]:
    sources = []
    for item in retrieved:
        chunk = dict(item["chunk"])
        sources.append(
            {
                "score": round(float(item.get("score", 0.0)), 4),
                "backend": item.get("retrieval_backend", "unknown"),
                "source_path": chunk.get("source_path", ""),
                "chunk_id": chunk.get("chunk_id", ""),
                "title": chunk.get("title", ""),
            }
        )
    return sources


def _diversify_sources(retrieved: list[dict[str, object]], *, top_k: int, max_per_source: int = 1) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for item in retrieved:
        chunk = dict(item["chunk"])
        source_path = str(chunk.get("source_path", ""))
        if counts.get(source_path, 0) >= max_per_source:
            continue
        selected.append(item)
        counts[source_path] = counts.get(source_path, 0) + 1
        if len(selected) >= top_k:
            return selected
    for item in retrieved:
        if item not in selected:
            selected.append(item)
        if len(selected) >= top_k:
            break
    return selected


def _build_prompt(
    *,
    question: str,
    retrieved: list[dict[str, object]],
    mode: str,
    strict: bool,
    max_chars_per_source: int,
) -> str:
    context_parts: list[str] = []
    for item in retrieved:
        chunk = dict(item["chunk"])
        text = str(chunk["text"])
        if len(text) > max_chars_per_source:
            text = text[:max_chars_per_source].rstrip() + "\n[context truncated]"
        context_parts.append(
            f"Source path: {chunk['source_path']}\n"
            f"Chunk id: {chunk['chunk_id']}\n"
            f"Text:\n{text}"
        )
    strict_rule = (
        "Strict policy is ON. Answer only from retrieved local sources. "
        "If the retrieved context is insufficient, say: 'Não sei com a base local atual' and list what source/calculation is missing. "
        "Do not infer mechanisms that are not stated in the sources. Do not invent papers, numerical results, or claims."
        if strict
        else "Strict policy is OFF, but still separate sourced facts from cautious interpretation."
    )
    requested_terms = _requested_terms(question)
    requested_terms_rule = (
        "The user explicitly asked about these terms: "
        + ", ".join(requested_terms)
        + ". Answer every listed term in a separate bullet. If a term is not supported by the retrieved context, say it is missing."
        if requested_terms
        else "Answer all parts of the user question explicitly."
    )
    return (
        "You are a local physics assistant for an open quantum transport laboratory.\n"
        f"{MODE_PROMPTS[mode]}\n"
        f"{strict_rule}\n"
        f"{requested_terms_rule}\n"
        "Always cite source paths inline when making technical claims.\n"
        "Never confuse target arrival with spatial spreading.\n"
        "Never confuse loss with target arrival: target arrival is success, loss is uncontrolled failure.\n"
        "Never say dephasing is population loss; dephasing changes phase relations.\n"
        "Never call gain below 0.02 a meaningful physical assistance effect.\n\n"
        f"Question:\n{question}\n\n"
        "Retrieved local context:\n"
        + "\n\n---\n\n".join(context_parts)
        + "\n\nAnswer in PT-BR unless the user explicitly asks otherwise."
    )


def _print_retrieval_only(question: str, mode: str, strict: bool, retrieved: list[dict[str, object]]) -> None:
    print(json.dumps({"question": question, "mode": mode, "strict": strict, "sources_used": _sources_payload(retrieved)}, indent=2, ensure_ascii=False))
    for index, item in enumerate(retrieved, start=1):
        chunk = dict(item["chunk"])
        preview = str(chunk["text"])[:520].strip()
        print(f"\n[{index}] score={float(item['score']):.3f} backend={item.get('retrieval_backend', 'unknown')} source={chunk['source_path']}")
        print(preview)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the strict local physics assistant.")
    parser.add_argument("question", nargs="+", help="Question for the local physics assistant.")
    parser.add_argument("--mode", choices=sorted(MODE_PROMPTS), default="tutor")
    parser.add_argument("--profile", choices=["stable", "game", "gpu"], default="stable")
    parser.add_argument("--strict", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--index", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "physics_assistant_index.json"))
    parser.add_argument("--top-k", type=int, default=7)
    parser.add_argument("--max-per-source", type=int, default=1)
    parser.add_argument("--max-chars-per-source", type=int, default=1100)
    parser.add_argument("--no-generate", action="store_true", help="Only show retrieved sources.")
    parser.add_argument("--model", default=DEFAULT_GENERATION_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--generation-timeout", type=float, default=300.0)
    parser.add_argument("--num-ctx", type=int, default=1536, help="Smaller context is more stable on 16 GB RAM machines.")
    parser.add_argument("--num-predict", type=int, default=320, help="Maximum generated tokens.")
    parser.add_argument("--num-thread", type=int, default=4, help="Leave CPU headroom for VS Code and light gaming.")
    parser.add_argument("--num-gpu", type=int, default=0, help="0 forces CPU generation; stable default for GTX 1650 4 GB.")
    parser.add_argument("--num-batch", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--keep-alive", default="0s", help="0s unloads the generation model after each answer.")
    args = parser.parse_args(argv)

    if args.profile == "game":
        args.top_k = min(args.top_k, 3)
        args.max_chars_per_source = min(args.max_chars_per_source, 700)
        args.num_ctx = min(args.num_ctx, 1024)
        args.num_predict = min(args.num_predict, 160)
        args.num_thread = min(args.num_thread, 2)
        args.num_gpu = 0
        args.num_batch = min(args.num_batch, 32)
        args.keep_alive = "0s"
    elif args.profile == "gpu":
        args.num_gpu = -1

    question = " ".join(args.question)
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Index not found: {index_path}. Run scripts/build_physics_curriculum_index.py first.")
        return 2

    index = load_index(index_path)
    retrieval_query = _expand_query(question)
    raw_retrieved = retrieve(index, retrieval_query, top_k=max(args.top_k * 3, args.top_k + 8), base_url=args.ollama_url)
    retrieved = _diversify_sources(raw_retrieved, top_k=args.top_k, max_per_source=args.max_per_source)
    positive_sources = [item for item in retrieved if float(item.get("score", 0.0)) > 0.0]
    if args.strict and not positive_sources:
        print("Não sei com a base local atual. Nenhuma fonte local relevante foi recuperada.")
        print(json.dumps({"sources_used": []}, indent=2, ensure_ascii=False))
        return 0

    if args.no_generate:
        _print_retrieval_only(question, args.mode, args.strict, retrieved)
        return 0

    if not ollama_available(base_url=args.ollama_url):
        print("Ollama não está disponível. Mostrando apenas as fontes recuperadas.")
        _print_retrieval_only(question, args.mode, args.strict, retrieved)
        return 2

    prompt = _build_prompt(
        question=question,
        retrieved=retrieved,
        mode=args.mode,
        strict=args.strict,
        max_chars_per_source=args.max_chars_per_source,
    )
    try:
        options = {
            "num_ctx": args.num_ctx,
            "num_predict": args.num_predict,
            "num_thread": args.num_thread,
            "num_gpu": args.num_gpu,
            "num_batch": args.num_batch,
            "temperature": args.temperature,
        }
        answer = generate_prompt_with_ollama(
            prompt=prompt,
            model=args.model,
            base_url=args.ollama_url,
            options=options,
            keep_alive=args.keep_alive,
            timeout_s=args.generation_timeout,
        )
    except (OSError, urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"Ollama generation failed: {type(exc).__name__}: {exc}")
        print("Mostrando as fontes recuperadas para manter a resposta auditável.")
        _print_retrieval_only(question, args.mode, args.strict, retrieved)
        return 3
    print(answer)
    print("\nSources used:")
    print(json.dumps(_sources_payload(retrieved), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
