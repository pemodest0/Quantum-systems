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

from oqs_transport.local_rag import build_chunks, build_lexical_index, collect_research_files, save_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the local research RAG index for the transport lab.")
    parser.add_argument("--output", default=str(ROOT / "outputs" / "transport_networks" / "local_rag" / "transport_research_index.json"))
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=180)
    args = parser.parse_args(argv)

    paths = collect_research_files(ROOT)
    chunks = build_chunks(paths, root=ROOT, chunk_size=args.chunk_size, overlap=args.overlap)
    index = build_lexical_index(chunks)
    index["generated_at_utc"] = datetime.now(UTC).isoformat()
    index["source_count"] = len(paths)
    index["chunk_count"] = len(chunks)
    output_path = Path(args.output)
    save_index(index, output_path)
    manifest_path = output_path.with_name("transport_research_index_manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at_utc": index["generated_at_utc"],
                "index_path": str(output_path),
                "source_count": len(paths),
                "chunk_count": len(chunks),
                "sources": [str(path.resolve().relative_to(ROOT.resolve())) for path in paths],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"index": str(output_path), "sources": len(paths), "chunks": len(chunks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
