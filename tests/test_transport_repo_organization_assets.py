from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_transport_repo_organization_files_exist() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "GUIDE.md",
        ROOT / "docs" / "PROJECT_OVERVIEW.md",
        ROOT / "docs" / "REPOSITORY_ORGANIZATION.md",
        ROOT / "docs" / "TRANSPORT_RESEARCH_DATA_MAP.md",
        ROOT / "outputs" / "transport_networks" / "README.md",
    ]
    for path in required:
        assert path.exists(), f"missing organization asset: {path}"


def test_readme_and_guide_point_to_transport_data_map() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
    repo_doc = (ROOT / "docs" / "REPOSITORY_ORGANIZATION.md").read_text(encoding="utf-8")
    assert "docs/TRANSPORT_RESEARCH_DATA_MAP.md" in readme
    assert "outputs/transport_networks/lab_registry/latest/transport_lab_memory.md" in readme
    assert "docs/TRANSPORT_RESEARCH_DATA_MAP.md" in guide
    assert "docs/TRANSPORT_RESEARCH_DATA_MAP.md" in repo_doc
