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

from oqs_transport.local_rag import (  # noqa: E402
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_URL,
    build_chunks,
    build_embedding_index,
    build_lexical_index,
    ollama_available,
    save_index,
)


def collect_physics_assistant_files(root: Path) -> list[Path]:
    patterns = [
        "docs/physics_curriculum/**/*.md",
        "docs/physics_exercises/**/*.md",
        "docs/physics_exercises/**/*.json",
        "docs/papers/transport/**/*.md",
        "docs/LAB_MANUAL.md",
        "docs/local_physics_assistant.md",
        "docs/literature_map_dynamic_open_transport.md",
        "docs/transport_lab_mcp_server.md",
        "docs/transport_graph_lab.md",
        "docs/guia_inicial_transporte_quantico_ptbr.md",
        "outputs/transport_networks/mcp_index/latest/index.json",
        "outputs/transport_networks/mcp_index/latest/campaigns.json",
        "outputs/transport_networks/mcp_index/latest/entropy_summary.json",
        "outputs/transport_networks/mcp_index/latest/quantum_classical_summary.json",
        "outputs/transport_networks/mcp_index/latest/claims.json",
        "outputs/transport_networks/mcp_index/latest/paper_guardrails.json",
        "outputs/transport_networks/mcp_index/latest/notebooks.json",
        "outputs/transport_networks/**/summary.md",
        "outputs/transport_networks/**/metrics.json",
        "outputs/transport_networks/**/literature_guardrails.json",
        "outputs/transport_networks/**/campaign_review/*.md",
        "outputs/transport_networks/**/campaign_review/literature_guardrails.json",
        "reports/**/*.tex",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))
    return sorted({path.resolve() for path in paths if path.is_file()})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the strict local physics assistant RAG index.")
    parser.add_argument("--output", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "physics_assistant_index.json"))
    parser.add_argument("--backend", choices=["auto", "lexical", "ollama_embeddings"], default="auto")
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=180)
    parser.add_argument("--no-fallback", action="store_true", help="Fail instead of falling back to lexical indexing.")
    args = parser.parse_args(argv)

    paths = collect_physics_assistant_files(ROOT)
    chunks = build_chunks(paths, root=ROOT, chunk_size=args.chunk_size, overlap=args.overlap)
    backend_requested = args.backend
    backend_used = "lexical"
    fallback_reason: str | None = None

    if backend_requested == "lexical":
        index = build_lexical_index(chunks)
    else:
        can_try_embeddings = backend_requested == "ollama_embeddings" or ollama_available(base_url=args.ollama_url)
        if can_try_embeddings:
            try:
                index = build_embedding_index(
                    chunks,
                    model=args.embedding_model,
                    base_url=args.ollama_url,
                )
                backend_used = "ollama_embeddings"
            except Exception as exc:  # noqa: BLE001 - command-line fallback should report the concrete failure.
                if args.no_fallback:
                    raise
                fallback_reason = f"{type(exc).__name__}: {exc}"
                index = build_lexical_index(chunks)
        else:
            fallback_reason = "Ollama is not available; built lexical index."
            index = build_lexical_index(chunks)

    index["generated_at_utc"] = datetime.now(UTC).isoformat()
    index["source_count"] = len(paths)
    index["chunk_count"] = len(chunks)
    index["physics_assistant_policy"] = {
        "strict_default": True,
        "unsupported_claim_rule": "If no local source, paper card, campaign result, or calculation supports the claim, say the base is insufficient.",
        "no_autonomous_campaigns": True,
    }
    output_path = Path(args.output)
    save_index(index, output_path)

    manifest = {
        "generated_at_utc": index["generated_at_utc"],
        "index_path": str(output_path),
        "backend_requested": backend_requested,
        "backend_used": backend_used if index.get("backend") == "ollama_embeddings" else str(index.get("backend")),
        "fallback_reason": fallback_reason,
        "source_count": len(paths),
        "chunk_count": len(chunks),
        "sources": [str(path.resolve().relative_to(ROOT.resolve())) for path in paths],
    }
    manifest_path = output_path.with_name("physics_assistant_index_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "index": str(output_path),
                "backend": manifest["backend_used"],
                "sources": len(paths),
                "chunks": len(chunks),
                "fallback_reason": fallback_reason,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
