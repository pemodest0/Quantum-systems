from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


DEFAULT_GENERATION_MODEL = "qwen2.5:7b"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    source_path: str
    title: str
    text: str


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_+\-/.:]+", text.lower())


def _chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def collect_research_files(root: Path) -> list[Path]:
    patterns = [
        "outputs/transport_networks/**/summary.md",
        "outputs/transport_networks/**/metrics.json",
        "outputs/transport_networks/**/literature_guardrails.json",
        "outputs/transport_networks/**/campaign_review/*.md",
        "outputs/transport_networks/**/campaign_review/literature_guardrails.json",
        "reports/**/*.tex",
        "docs/**/*.md",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))
    return sorted({path.resolve() for path in paths if path.is_file()})


def build_chunks(paths: Iterable[Path], *, root: Path, chunk_size: int = 1200, overlap: int = 180) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel_path = str(path.resolve().relative_to(root.resolve()))
        for index, chunk in enumerate(_chunk_text(text, chunk_size=chunk_size, overlap=overlap)):
            chunks.append(
                RagChunk(
                    chunk_id=f"{rel_path}::{index}",
                    source_path=rel_path,
                    title=path.stem,
                    text=chunk,
                )
            )
    return chunks


def build_lexical_index(chunks: list[RagChunk]) -> dict[str, object]:
    doc_tokens = [_tokenize(chunk.text) for chunk in chunks]
    doc_freq: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1
    n_docs = max(len(chunks), 1)
    vectors: list[dict[str, float]] = []
    norms: list[float] = []
    for tokens in doc_tokens:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        total = max(len(tokens), 1)
        vector: dict[str, float] = {}
        for token, count in counts.items():
            tf = count / total
            idf = math.log((1 + n_docs) / (1 + doc_freq.get(token, 0))) + 1.0
            vector[token] = tf * idf
        norm = math.sqrt(sum(value * value for value in vector.values()))
        vectors.append(vector)
        norms.append(norm)
    return {
        "version": 1,
        "backend": "lexical",
        "chunks": [chunk.__dict__ for chunk in chunks],
        "vectors": vectors,
        "norms": norms,
    }


def _dense_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=False):
        left_float = float(left_value)
        right_float = float(right_value)
        dot += left_float * right_float
        left_norm += left_float * left_float
        right_norm += right_float * right_float
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / math.sqrt(left_norm * right_norm)


def _lexical_overlap_score(query: str, text: str) -> float:
    query_tokens = {token for token in _tokenize(query) if len(token) >= 3}
    if not query_tokens:
        return 0.0
    text_tokens = set(_tokenize(text))
    return sum(1 for token in query_tokens if token in text_tokens) / len(query_tokens)


def _source_priority_boost(source_path: str) -> float:
    normalized = source_path.replace("\\", "/")
    if normalized.startswith("docs/physics_curriculum/"):
        return 0.045
    if normalized.startswith("docs/papers/transport/"):
        return 0.030
    if normalized.startswith("docs/physics_exercises/"):
        return 0.020
    return 0.0


def embed_texts_with_ollama(
    texts: Sequence[str],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout_s: float = 120.0,
) -> list[list[float]]:
    """Embed texts with Ollama without keeping a separate local service alive.

    Ollama controls model lifecycle. This function only sends one HTTP request
    per text and stores the returned vectors in the local index.
    """

    embeddings: list[list[float]] = []
    for text in texts:
        payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
        embedding = data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError(f"Ollama did not return an embedding for model {model!r}.")
        embeddings.append([float(value) for value in embedding])
    return embeddings


def build_embedding_index(
    chunks: list[RagChunk],
    *,
    embedder: Callable[[Sequence[str]], list[list[float]]] | None = None,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout_s: float = 120.0,
) -> dict[str, object]:
    """Build a semantic RAG index with lexical fallback data embedded inside it."""

    texts = [chunk.text for chunk in chunks]
    if embedder is None:
        embeddings = embed_texts_with_ollama(texts, model=model, base_url=base_url, timeout_s=timeout_s)
    else:
        embeddings = embedder(texts)
    if len(embeddings) != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    lexical_index = build_lexical_index(chunks)
    return {
        "version": 1,
        "backend": "ollama_embeddings",
        "embedding_model": model,
        "ollama_url": base_url,
        "chunks": [chunk.__dict__ for chunk in chunks],
        "embeddings": embeddings,
        "vectors": lexical_index["vectors"],
        "norms": lexical_index["norms"],
        "fallback_backend": "lexical",
    }


def save_index(index: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def load_index(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _query_vector(query: str, index: dict[str, object]) -> tuple[dict[str, float], float]:
    tokens = _tokenize(query)
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    total = max(len(tokens), 1)
    vectors = list(index.get("vectors", []))
    n_docs = max(len(vectors), 1)
    doc_freq: dict[str, int] = {}
    for vector in vectors:
        for token in vector:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    qvec: dict[str, float] = {}
    for token, count in counts.items():
        tf = count / total
        idf = math.log((1 + n_docs) / (1 + doc_freq.get(token, 0))) + 1.0
        qvec[token] = tf * idf
    norm = math.sqrt(sum(value * value for value in qvec.values()))
    return qvec, norm


def _retrieve_lexical(index: dict[str, object], query: str, *, top_k: int = 6) -> list[dict[str, object]]:
    qvec, qnorm = _query_vector(query, index)
    chunks = list(index.get("chunks", []))
    vectors = list(index.get("vectors", []))
    norms = list(index.get("norms", []))
    scored: list[dict[str, object]] = []
    for chunk, vector, norm in zip(chunks, vectors, norms, strict=False):
        dot = sum(qvec.get(token, 0.0) * float(value) for token, value in vector.items())
        score = 0.0 if qnorm <= 0.0 or float(norm) <= 0.0 else dot / (qnorm * float(norm))
        scored.append({"score": float(score), "chunk": chunk})
    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    return scored[:top_k]


def _retrieve_embeddings(
    index: dict[str, object],
    query: str,
    *,
    top_k: int = 6,
    base_url: str | None = None,
    timeout_s: float = 30.0,
) -> list[dict[str, object]]:
    chunks = list(index.get("chunks", []))
    embeddings = list(index.get("embeddings", []))
    model = str(index.get("embedding_model", DEFAULT_EMBEDDING_MODEL))
    ollama_url = base_url or str(index.get("ollama_url", DEFAULT_OLLAMA_URL))
    query_embedding = embed_texts_with_ollama([query], model=model, base_url=ollama_url, timeout_s=timeout_s)[0]
    scored: list[dict[str, object]] = []
    for chunk, embedding in zip(chunks, embeddings, strict=False):
        if not isinstance(embedding, list):
            continue
        chunk_dict = dict(chunk)
        semantic_score = _dense_cosine(query_embedding, [float(value) for value in embedding])
        lexical_score = _lexical_overlap_score(query, str(chunk_dict.get("text", "")))
        score = 0.88 * semantic_score + 0.12 * lexical_score + _source_priority_boost(str(chunk_dict.get("source_path", "")))
        scored.append(
            {
                "score": float(score),
                "semantic_score": float(semantic_score),
                "lexical_score": float(lexical_score),
                "chunk": chunk,
                "retrieval_backend": "ollama_embeddings",
            }
        )
    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    return scored[:top_k]


def retrieve(
    index: dict[str, object],
    query: str,
    *,
    top_k: int = 6,
    allow_embedding_fallback: bool = True,
    base_url: str | None = None,
) -> list[dict[str, object]]:
    backend = str(index.get("backend", "lexical"))
    if backend == "ollama_embeddings":
        try:
            return _retrieve_embeddings(index, query, top_k=top_k, base_url=base_url)
        except (OSError, urllib.error.URLError, RuntimeError, TimeoutError):
            if not allow_embedding_fallback:
                raise
            retrieved = _retrieve_lexical(index, query, top_k=top_k)
            for item in retrieved:
                item["retrieval_backend"] = "lexical_fallback"
            return retrieved

    retrieved = _retrieve_lexical(index, query, top_k=top_k)
    for item in retrieved:
        item["retrieval_backend"] = "lexical"
    return retrieved


def ollama_available(*, base_url: str = DEFAULT_OLLAMA_URL, timeout_s: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=timeout_s) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def generate_with_ollama(
    *,
    question: str,
    retrieved: list[dict[str, object]],
    model: str = DEFAULT_GENERATION_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout_s: float = 120.0,
) -> str:
    context_parts: list[str] = []
    for item in retrieved:
        chunk = dict(item["chunk"])
        context_parts.append(f"Source: {chunk['source_path']}\n{chunk['text']}")
    prompt = (
        "You are a local research assistant for an open quantum transport lab. "
        "Answer only using the retrieved local context below. "
        "If the context is insufficient, say exactly what is missing. "
        "Cite source paths inline.\n\n"
        f"Question:\n{question}\n\n"
        "Retrieved local context:\n"
        + "\n\n---\n\n".join(context_parts)
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data.get("response", "")).strip()


def generate_prompt_with_ollama(
    *,
    prompt: str,
    model: str = DEFAULT_GENERATION_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    options: dict[str, object] | None = None,
    keep_alive: str | None = None,
    timeout_s: float = 120.0,
) -> str:
    payload_data: dict[str, object] = {"model": model, "prompt": prompt, "stream": False}
    if options:
        payload_data["options"] = options
    if keep_alive is not None:
        payload_data["keep_alive"] = keep_alive
    payload = json.dumps(payload_data).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data.get("response", "")).strip()
