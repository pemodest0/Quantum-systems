from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentRole:
    name: str
    responsibility: str
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]


def default_agent_stack() -> tuple[AgentRole, ...]:
    return (
        AgentRole(
            name="Scout",
            responsibility="Inspect completed campaign outputs and flag unusual zones or candidate transitions.",
            allowed_actions=("scan finished outputs", "identify anomalies", "summarize suspicious regions"),
            blocked_actions=("edit physics assumptions", "launch new campaigns without approval"),
        ),
        AgentRole(
            name="Analyst",
            responsibility="Write the first physical reading of the campaign and explain figures in plain PT-BR.",
            allowed_actions=("read outputs", "compare observables", "draft simple explanations"),
            blocked_actions=("change labels by hand without rules", "overstate claims"),
        ),
        AgentRole(
            name="Critic",
            responsibility="Check whether conclusions outrun the data and flag under-resolved regions.",
            allowed_actions=("flag weak ensembles", "flag ambiguous boundaries", "flag low-confidence claims"),
            blocked_actions=("erase inconvenient results", "replace evidence with opinion"),
        ),
        AgentRole(
            name="Planner",
            responsibility="Propose the next parameter refinement or medium extension after a human gate.",
            allowed_actions=("recommend one next action", "suggest local refinement", "suggest ensemble increase"),
            blocked_actions=("run the next campaign without approval", "change the campaign goal alone"),
        ),
        AgentRole(
            name="Scribe",
            responsibility="Assemble the technical report and the lighter review payload.",
            allowed_actions=("write report fragments", "organize figures", "export summary tables"),
            blocked_actions=("change numerical results", "invent missing evidence"),
        ),
    )


def agent_stack_payload() -> list[dict[str, object]]:
    return [asdict(role) for role in default_agent_stack()]
