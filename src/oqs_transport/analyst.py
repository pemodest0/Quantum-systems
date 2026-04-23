from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FigureExplanation:
    figure_key: str
    title_meaning_ptbr: str
    axes_meaning_ptbr: list[str]
    symbols_meaning_ptbr: list[str]
    literature_expectation_ptbr: str
    measured_result_ptbr: str
    physical_sense_ptbr: str
    uncertainty_ptbr: str


@dataclass(frozen=True)
class ScoutFinding:
    finding: str
    reason: str


@dataclass(frozen=True)
class CriticAssessment:
    level: str
    concern: str
    evidence: str


@dataclass(frozen=True)
class PlannerRecommendation:
    next_action: str
    reason: str


@dataclass(frozen=True)
class CampaignReviewBundle:
    scout: list[ScoutFinding]
    analyst_summary_ptbr: str
    critic: list[CriticAssessment]
    planner: PlannerRecommendation
    figure_explanations: list[FigureExplanation]


def build_medium_campaign_review(
    *,
    scenario_names: list[str],
    transport_range: tuple[float, float],
    spreading_range: tuple[float, float],
    mixing_range: tuple[float, float],
    regime_counts: dict[str, int],
) -> CampaignReviewBundle:
    scout = [
        ScoutFinding(
            finding="A campanha ja separa chegada ao alvo, espalhamento pelo meio e mistura interna do estado.",
            reason="Isso evita confundir boa chegada ao alvo com simples espalhamento dentro do meio.",
        ),
        ScoutFinding(
            finding="Ha regioes de mudanca de regime dentro do mapa.",
            reason="Os rotulos calculados nao ficaram todos iguais, entao ha fronteiras fisicas a explorar.",
        ),
    ]

    critic: list[CriticAssessment] = []
    if transport_range[1] - transport_range[0] < 0.05:
        critic.append(
            CriticAssessment(
                level="warning",
                concern="A faixa de eficiencia ficou estreita.",
                evidence="Pode indicar que a malha de parametros ainda nao esta pegando uma mudanca forte de comportamento.",
            )
        )
    if spreading_range[1] <= spreading_range[0] + 1e-9:
        critic.append(
            CriticAssessment(
                level="warning",
                concern="O espalhamento nao variou de forma visivel.",
                evidence="Sem contraste em espalhamento, a leitura fisica do meio fica pobre.",
            )
        )
    if not critic:
        critic.append(
            CriticAssessment(
                level="ok",
                concern="Nenhum problema estrutural imediato apareceu na leitura automatica.",
                evidence="As tres familias de observaveis variaram e os regimes nao colapsaram num unico rotulo.",
            )
        )

    dominant_regime = max(regime_counts.items(), key=lambda item: item[1])[0] if regime_counts else "mixed-crossover"
    planner = PlannerRecommendation(
        next_action="refine a boundary",
        reason=f"O proximo passo mais seguro e refinar a fronteira do regime dominante observado ({dominant_regime}) em vez de abrir um meio novo cedo demais.",
    )

    figure_explanations = [
        FigureExplanation(
            figure_key="transport_success_maps",
            title_meaning_ptbr="Este grafico mostra quanto da excitacao conseguiu chegar ao alvo no fim da evolucao.",
            axes_meaning_ptbr=[
                "Eixo horizontal: embaralhamento de fase comparado com a forca de troca entre os sitios.",
                "Eixo vertical: irregularidade local comparada com a mesma forca de troca.",
            ],
            symbols_meaning_ptbr=[
                "Cada painel e um tipo de meio diferente.",
                "Cores mais claras significam chegada mais eficiente ao alvo.",
            ],
            literature_expectation_ptbr="A literatura espera que alguma desordem atrapalhe e que uma quantidade moderada de embaralhamento as vezes ajude.",
            measured_result_ptbr="O mapa medido mostra onde o transporte melhora, piora ou quase nao muda.",
            physical_sense_ptbr="Faz sentido quando regioes claras aparecem entre regioes muito coerentes e regioes muito dissipativas.",
            uncertainty_ptbr="Se as transicoes entre cores forem muito suaves ou muito ruidosas, ainda pode faltar ensemble ou refinamento local.",
        ),
        FigureExplanation(
            figure_key="spreading_maps",
            title_meaning_ptbr="Este grafico mostra o quanto a excitacao se espalhou pelo meio antes de ser perdida ou capturada.",
            axes_meaning_ptbr=[
                "Eixo horizontal: embaralhamento de fase comparado com a troca entre os sitios.",
                "Eixo vertical: irregularidade local comparada com essa troca.",
            ],
            symbols_meaning_ptbr=[
                "A cor representa o espalhamento espacial final.",
                "Valores maiores significam que a excitacao percorreu uma regiao maior do meio.",
            ],
            literature_expectation_ptbr="Em meios simples, espera-se espalhamento maior no caso mais coerente e espalhamento menor quando ha forte travamento por ruido ou irregularidade.",
            measured_result_ptbr="O mapa mostra se boa chegada ao alvo veio junto com boa propagacao espacial ou nao.",
            physical_sense_ptbr="Isso e importante porque um meio pode chegar bem ao alvo sem realmente propagar longe, se houver geometria favoravel.",
            uncertainty_ptbr="Se o mapa de espalhamento nao contrastar com o mapa de sucesso, a interpretacao fisica pode ficar fraca.",
        ),
        FigureExplanation(
            figure_key="mixing_maps",
            title_meaning_ptbr="Este grafico mostra o quanto o estado ficou misturado dentro do meio.",
            axes_meaning_ptbr=[
                "Eixo horizontal: embaralhamento de fase relativo a troca.",
                "Eixo vertical: irregularidade local relativa a troca.",
            ],
            symbols_meaning_ptbr=[
                "A cor representa a mistura interna do estado.",
                "Valores maiores significam perda maior de estrutura quantica fina.",
            ],
            literature_expectation_ptbr="Espera-se mais mistura quando aumentamos o embaralhamento de fase.",
            measured_result_ptbr="O mapa medido indica onde o transporte melhora junto com mistura e onde isso nao acontece.",
            physical_sense_ptbr="Isso ajuda a distinguir transporte assistido por ambiente de simples destruicao de coerencia.",
            uncertainty_ptbr="Se a mistura cresce mas o transporte nao muda, talvez o ruido so esteja apagando informacao sem ajudar a dinamica util.",
        ),
        FigureExplanation(
            figure_key="regime_maps",
            title_meaning_ptbr="Este grafico coloca um rotulo fisico em cada ponto do mapa de parametros.",
            axes_meaning_ptbr=[
                "Eixo horizontal: embaralhamento de fase relativo a troca.",
                "Eixo vertical: irregularidade local relativa a troca.",
            ],
            symbols_meaning_ptbr=[
                "Cada cor e um regime diferente.",
                "O rotulo foi decidido por regras explicitas, nao por texto livre.",
            ],
            literature_expectation_ptbr="A literatura sugere regioes coerentes, regioes assistidas por ruido e regioes em que a irregularidade trava o transporte.",
            measured_result_ptbr="O mapa medido mostra onde cada comportamento domina no conjunto atual de meios.",
            physical_sense_ptbr="Faz sentido quando as fronteiras entre regimes acompanham mudancas visiveis nos mapas de sucesso, espalhamento e mistura.",
            uncertainty_ptbr="Se a confianca da classificacao for baixa em muitas celulas, a campanha seguinte deve refinar a fronteira em vez de abrir um tema novo.",
        ),
    ]

    summary = (
        f"A campanha comparou {len(scenario_names)} meios e encontrou uma faixa de sucesso de transporte entre {transport_range[0]:.3f} e {transport_range[1]:.3f}. "
        f"O espalhamento espacial variou entre {spreading_range[0]:.3f} e {spreading_range[1]:.3f}, e a mistura interna variou entre {mixing_range[0]:.3f} e {mixing_range[1]:.3f}. "
        "Isso ja permite falar em regioes fisicas diferentes do mapa, em vez de so mostrar numeros isolados."
    )

    return CampaignReviewBundle(
        scout=scout,
        analyst_summary_ptbr=summary,
        critic=critic,
        planner=planner,
        figure_explanations=figure_explanations,
    )


def review_bundle_to_dict(bundle: CampaignReviewBundle) -> dict[str, object]:
    return {
        "scout": [asdict(item) for item in bundle.scout],
        "analyst_summary_ptbr": bundle.analyst_summary_ptbr,
        "critic": [asdict(item) for item in bundle.critic],
        "planner": asdict(bundle.planner),
        "figure_explanations": [asdict(item) for item in bundle.figure_explanations],
    }
