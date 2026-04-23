from __future__ import annotations

import json
from pathlib import Path


def _project_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "pyproject.toml").exists() and (cwd / "src").exists():
        return cwd
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()


def _cell(cell_type: str, source: list[str]) -> dict[str, object]:
    base: dict[str, object] = {"cell_type": cell_type, "metadata": {}, "source": source}
    if cell_type == "code":
        base["execution_count"] = None
        base["outputs"] = []
    return base


def build_notebook(path: Path) -> None:
    cells = [
        _cell(
            "markdown",
            [
                "# Transport Research Journey V2\n",
                "\n",
                "Apostila interativa em PT-BR para estudar transporte quântico aberto em redes. A ideia é olhar as simulações como laboratório: mudar parâmetros, rodar campanhas pequenas e interpretar os gráficos.\n",
            ],
        ),
        _cell(
            "code",
            [
                "from pathlib import Path\n",
                "import json\n",
                "import pandas as pd\n",
                "from IPython.display import Image, Markdown, display\n",
                "\n",
                "ROOT = Path.cwd()\n",
                "if not (ROOT / 'pyproject.toml').exists():\n",
                "    ROOT = ROOT.parent\n",
                "JOURNEY = ROOT / 'outputs' / 'transport_networks' / 'research_journey_v2' / 'latest'\n",
                "TARGET = ROOT / 'outputs' / 'transport_networks' / 'target_geometry_confirm' / 'latest'\n",
                "FRACTAL = ROOT / 'outputs' / 'transport_networks' / 'fractal_geometry_followup' / 'latest'\n",
                "ARTICLE = ROOT / 'outputs' / 'transport_networks' / 'article_figure_pack' / 'latest'\n",
                "JOURNEY\n",
            ],
        ),
        _cell(
            "markdown",
            [
                "## 1. Rodar as campanhas\n",
                "\n",
                "`smoke` testa se tudo funciona. `interactive` é o padrão para estudar. `paper` é mais pesado e serve para robustez.\n",
            ],
        ),
        _cell(
            "code",
            [
                "# !python scripts/run_transport_research_journey_v2.py --profile smoke\n",
                "# !python scripts/run_transport_research_journey_v2.py --profile interactive\n",
                "# !python scripts/run_transport_research_journey_v2.py --profile paper\n",
                "# !python scripts/run_transport_target_geometry_confirm.py --profile interactive\n",
                "# !python scripts/run_transport_fractal_geometry_followup.py --profile interactive\n",
                "# !python scripts/build_transport_article_figure_pack.py\n",
            ],
        ),
        _cell(
            "markdown",
            [
                "## 2. Ideia física mínima\n",
                "\n",
                "- A excitação começa em um nó da rede.\n",
                "- As arestas dizem por onde ela pode se mover coerentemente.\n",
                "- O alvo é o nó conectado ao canal de chegada bem-sucedida.\n",
                "- O ambiente pode embaralhar fase; isso pode ajudar ou atrapalhar.\n",
                "- O controle clássico testa se o resultado é só conectividade comum ou se a dinâmica aberta traz algo além.\n",
            ],
        ),
        _cell(
            "code",
            [
                "if (JOURNEY / 'summary.md').exists():\n",
                "    display(Markdown((JOURNEY / 'summary.md').read_text(encoding='utf-8')))\n",
                "if (JOURNEY / 'metrics.json').exists():\n",
                "    display(json.loads((JOURNEY / 'metrics.json').read_text(encoding='utf-8')))\n",
            ],
        ),
        _cell(
            "markdown",
            ["## 3. Alvo e geometria\n", "\n", "Pergunta: se eu mudo só o nó de chegada, a física muda ou é detalhe técnico?\n"],
        ),
        _cell(
            "code",
            [
                "for name in ['target_position_effect_map.png']:\n",
                "    path = JOURNEY / 'figures' / name\n",
                "    if path.exists():\n",
                "        display(Image(filename=str(path)))\n",
                "if (TARGET / 'target_pair_confirmations.csv').exists():\n",
                "    display(pd.read_csv(TARGET / 'target_pair_confirmations.csv'))\n",
            ],
        ),
        _cell(
            "markdown",
            ["## 4. Quântico aberto vs clássico\n", "\n", "Pergunta: a vantagem aparece no modelo quântico aberto ou o clássico já explica tudo?\n"],
        ),
        _cell(
            "code",
            [
                "for name in ['quantum_vs_classical_delta_map.png', 'quantum_vs_classical_target_controls.png']:\n",
                "    for base in [JOURNEY, TARGET]:\n",
                "        path = base / 'figures' / name\n",
                "        if path.exists():\n",
                "            display(Markdown(f'### {name}'))\n",
                "            display(Image(filename=str(path)))\n",
                "if (TARGET / 'quantum_classical_target_controls.csv').exists():\n",
                "    display(pd.read_csv(TARGET / 'quantum_classical_target_controls.csv').head(20))\n",
            ],
        ),
        _cell(
            "markdown",
            ["## 5. Classificação de redes\n", "\n", "Aqui não refazemos o classificador. Apenas usamos o resultado já validado como evidência para artigo.\n"],
        ),
        _cell(
            "code",
            [
                "path = JOURNEY / 'figures' / 'classification_article_panel.png'\n",
                "if path.exists():\n",
                "    display(Image(filename=str(path)))\n",
            ],
        ),
        _cell(
            "markdown",
            ["## 6. Fractais\n", "\n", "Pergunta: uma geometria fractal muda o espalhamento quando comparada a uma rede 2D comum?\n"],
        ),
        _cell(
            "code",
            [
                "for name in ['fractal_msd_and_geometry.png', 'fractal_vs_lattice_msd.png', 'fractal_geometry_panel.png']:\n",
                "    for base in [JOURNEY, FRACTAL]:\n",
                "        path = base / 'figures' / name\n",
                "        if path.exists():\n",
                "            display(Markdown(f'### {name}'))\n",
                "            display(Image(filename=str(path)))\n",
                "if (FRACTAL / 'fractal_scaling_summary.csv').exists():\n",
                "    display(pd.read_csv(FRACTAL / 'fractal_scaling_summary.csv'))\n",
            ],
        ),
        _cell(
            "markdown",
            ["## 7. Figura de artigo e claims\n", "\n", "Esta seção mostra o painel 2x2 e lista o que podemos ou não afirmar com segurança.\n"],
        ),
        _cell(
            "code",
            [
                "if (ARTICLE / 'article_claims.md').exists():\n",
                "    display(Markdown((ARTICLE / 'article_claims.md').read_text(encoding='utf-8')))\n",
                "path = ARTICLE / 'figures' / 'article_four_panel.png'\n",
                "if path.exists():\n",
                "    display(Image(filename=str(path)))\n",
            ],
        ),
        _cell(
            "markdown",
            [
                "## 8. Como apresentar ao professor\n",
                "\n",
                "1. Estamos estudando redes finitas onde uma excitação se move e pode chegar a um canal de sucesso.\n",
                "2. O resultado mais forte é que a posição do alvo muda a eficiência de transporte de forma estatística, não só estética.\n",
                "3. O controle clássico mostra quando a dinâmica quântica aberta traz informação além de conectividade simples.\n",
                "4. A classificação mostra que assinaturas dinâmicas ajudam a reconhecer famílias de redes, mas topologia + dinâmica é melhor.\n",
                "5. As redes fractais entram como frente visual e científica para estudar como geometria altera espalhamento.\n",
            ],
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "pygments_lexer": "ipython3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    build_notebook(ROOT / "notebooks" / "transport_research_journey_v2.ipynb")
    print(json.dumps({"notebook": str(ROOT / "notebooks" / "transport_research_journey_v2.ipynb")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
