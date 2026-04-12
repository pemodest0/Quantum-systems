from pathlib import Path

from oqs_control.figure_annotations import BASE_FIGURE_NOTES, summary_for_output_figure


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = (
    "This generated plot belongs to the current reproduction and should be read together "
    "with the matching metrics and configuration files."
)


def test_all_repro_and_workflow_figures_have_specific_summaries() -> None:
    figure_paths = list((ROOT / "outputs" / "repro").rglob("*.png"))
    figure_paths.extend((ROOT / "outputs" / "workflows").rglob("*.png"))
    assert figure_paths

    for path in figure_paths:
        parts = path.parts
        if "repro" in parts:
            source_id = parts[parts.index("repro") + 1]
        else:
            source_id = parts[parts.index("workflows") + 1]
        assert summary_for_output_figure(source_id, path.name) != DEFAULT_SUMMARY


def test_all_base_figures_have_notes() -> None:
    base_figures = list((ROOT / "outputs").glob("*.png"))
    assert base_figures
    for path in base_figures:
        assert path.name in BASE_FIGURE_NOTES
