from __future__ import annotations

from pathlib import Path
import shutil

from oqs_transport import local_rag


def test_local_rag_retrieves_relevant_campaign_text() -> None:
    tmp_dir = Path("tests") / "_tmp_local_rag"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    try:
        source = tmp_dir / "summary.md"
        source.write_text(
            "Ring campaign result: unfavorable target improves under moderate phase scrambling. "
            "The favorable target remains close to coherent motion.",
            encoding="utf-8",
        )
        chunks = local_rag.build_chunks([source], root=Path.cwd(), chunk_size=240, overlap=20)
        index = local_rag.build_lexical_index(chunks)
        retrieved = local_rag.retrieve(index, "unfavorable target phase scrambling", top_k=1)
        assert retrieved
        assert "unfavorable target" in retrieved[0]["chunk"]["text"]
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_local_rag_embedding_backend_uses_semantic_vectors(monkeypatch) -> None:
    chunks = [
        local_rag.RagChunk(
            chunk_id="ring::0",
            source_path="ring.md",
            title="ring",
            text="Ring campaign: unfavorable target improves under moderate phase scrambling.",
        ),
        local_rag.RagChunk(
            chunk_id="entropy::0",
            source_path="entropy.md",
            title="entropy",
            text="Purity and entropy measure mixedness, not target arrival.",
        ),
    ]

    def fake_embedder(texts):
        vectors = []
        for text in texts:
            lower = text.lower()
            if "unfavorable" in lower or "phase scrambling" in lower:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors

    index = local_rag.build_embedding_index(chunks, embedder=fake_embedder)
    monkeypatch.setattr(local_rag, "embed_texts_with_ollama", lambda texts, **_: fake_embedder(texts))

    retrieved = local_rag.retrieve(index, "phase scrambling helps unfavorable ring target", top_k=1)
    assert retrieved
    assert retrieved[0]["retrieval_backend"] == "ollama_embeddings"
    assert retrieved[0]["chunk"]["source_path"] == "ring.md"
