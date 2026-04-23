from __future__ import annotations

import json
import ssl
import sys
from pathlib import Path
from urllib.request import urlopen


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
REGISTRY = ROOT / "reports" / "famb_msc_transport_proposal" / "literature_registry.json"
TARGET_DIR = ROOT / "reports" / "famb_msc_transport_proposal" / "reference_pdfs"
OPEN_PDFS = {
    "potocnik_2018": "https://www.nature.com/articles/s41467-018-03312-x.pdf",
    "jacob_2024": "https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1474018/pdf",
    "novo_2016": "https://www.nature.com/articles/srep18142.pdf",
    "blach_2025": "https://www.nature.com/articles/s41467-024-55812-8.pdf",
    "kassal_2012": "https://arxiv.org/pdf/1201.5202.pdf",
    "caruso_2014": "https://iopscience.iop.org/article/10.1088/1367-2630/16/5/055015/pdf",
    "marais_2013": "https://iopscience.iop.org/article/10.1088/1367-2630/15/1/013038/pdf",
}


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    context = ssl._create_unverified_context()

    for ref_id, url in OPEN_PDFS.items():
        target = TARGET_DIR / f"{ref_id}.pdf"
        try:
            with urlopen(url, timeout=60, context=context) as response:
                target.write_bytes(response.read())
            downloaded.append({"id": ref_id, "path": str(target.relative_to(ROOT)), "url": url})
        except Exception as exc:  # pragma: no cover - network-dependent
            failures.append({"id": ref_id, "url": url, "error": str(exc)})

    payload = {
        "downloaded_count": len(downloaded),
        "downloads": downloaded,
        "failed_count": len(failures),
        "failures": failures,
    }
    (TARGET_DIR / "download_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
