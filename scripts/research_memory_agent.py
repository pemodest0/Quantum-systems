from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oqs_control.research_memory import build_research_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collaborative research memory agent for simulation and experiment outputs."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "lab" / "research_memory",
        help="Directory where records.jsonl, index.json, and SUMMARY.md are written.",
    )
    args = parser.parse_args(argv)

    records = build_research_memory(ROOT, args.output_dir)
    print(
        json.dumps(
            {
                "status": "completed",
                "record_count": len(records),
                "output_dir": str(args.output_dir),
                "source_ids": [record.source_id for record in records],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
