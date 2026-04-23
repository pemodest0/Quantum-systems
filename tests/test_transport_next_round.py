from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd

from scripts.build_transport_article_figure_pack import build_pack
from scripts.build_transport_research_journey_notebook import build_notebook
from scripts.run_transport_fractal_geometry_followup import profile_config as fractal_profile_config
from scripts.run_transport_fractal_geometry_followup import run_campaign as run_fractal_campaign
from scripts.run_transport_target_geometry_confirm import profile_config as target_profile_config
from scripts.run_transport_target_geometry_confirm import run_campaign as run_target_campaign


def test_target_geometry_confirm_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_target_geometry_confirm"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        metrics = run_target_campaign(target_profile_config("smoke"), tmp_dir)
        assert metrics["numerics_pass"]
        assert (tmp_dir / "target_pair_confirmations.csv").exists()
        assert (tmp_dir / "controlled_pair_tests.csv").exists()
        assert (tmp_dir / "quantum_classical_target_controls.csv").exists()
        assert (tmp_dir / "figures" / "target_pair_contrasts.png").exists()
        controlled = pd.read_csv(tmp_dir / "controlled_pair_tests.csv")
        assert (controlled["distance_delta"] >= 0.0).all()
        assert (controlled["centrality_delta"] >= 0.0).all()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_fractal_followup_smoke_outputs() -> None:
    tmp_dir = Path("tests") / "_tmp_fractal_followup"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        metrics = run_fractal_campaign(fractal_profile_config("smoke"), tmp_dir)
        assert metrics["numerics_pass"]
        assert (tmp_dir / "fractal_scaling_summary.csv").exists()
        assert (tmp_dir / "figures" / "fractal_vs_lattice_msd.png").exists()
        assert (tmp_dir / "figures" / "fractal_geometry_panel.png").exists()
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def test_article_pack_and_notebook_build() -> None:
    tmp_root = Path("tests") / "_tmp_article_pack"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    try:
        metrics = build_pack(tmp_root)
        assert metrics["figure"]
        assert (tmp_root / "figures" / "article_four_panel.png").exists()
        assert (tmp_root / "article_claims.md").exists()
        notebook = tmp_root / "transport_research_journey_v2.ipynb"
        build_notebook(notebook)
        assert notebook.exists()
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
