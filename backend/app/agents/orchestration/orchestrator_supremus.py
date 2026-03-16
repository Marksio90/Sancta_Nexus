"""
Orchestrator Supremus (A-001)
=============================
Main orchestration agent for Sancta Nexus.
Uses LangGraph StateGraph to route user intent through the appropriate
sub-graphs and ensure quality-gated output.

"Deus in adiutorium meum intende." — Ps 69:2
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

logger = logging.getLogger("sancta_nexus.orchestrator")


# ---------------------------------------------------------------------------
# Shared state flowing through every node
# ---------------------------------------------------------------------------

class SanctaState(TypedDict, total=False):
    """Canonical state exchanged among all Sancta Nexus agents."""

    user_id: str
    emotion_vector: dict[str, float]
    spiritual_state: dict[str, Any]
    intent: str
    scripture: dict[str, Any]
    meditation: dict[str, Any]
    prayer: dict[str, Any]
    contemplation: dict[str, Any]
    action: dict[str, Any]
    theological_validation: dict[str, Any]
    session_history: list[dict[str, Any]]
    error: str | None


# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------

VALID_INTENTS = frozenset(
    {
        "lectio_divina",
        "free_reflection",
        "interactive_bible",
        "spiritual_direction",
        "community",
        "crisis",
    }
)

INTENT_ROUTING_PROMPT = """\
Jesteś rozpoznawaczem intencji w systemie modlitewnym Sancta Nexus.
Na podstawie kontekstu emocjonalnego i duchowego użytkownika, określ intencję.

Możliwe intencje:
- lectio_divina: użytkownik chce modlitwy Lectio Divina
- free_reflection: swobodna refleksja nad fragmentem Pisma
- interactive_bible: interaktywne studiowanie Biblii
- spiritual_direction: kierownictwo duchowe
- community: wspólnota i modlitwa wstawiennicza
- crisis: sytuacja kryzysowa wymagająca natychmiastowej pomocy

Wektor emocji użytkownika: {emotion_vector}
Stan duchowy: {spiritual_state}

Odpowiedz JEDNYM SŁOWEM — nazwą intencji.
"""


class OrchestratorSupremus:
    """
    A-001 — The supreme orchestrator.

    Builds and compiles the top-level LangGraph that routes each user
    session to the appropriate sub-graph based on detected intent.
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.3,
    ) -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=temperature)
        self._graph = self._build_graph()
        logger.info("OrchestratorSupremus (A-001) initialised.")

    # ------------------------------------------------------------------
    # Node functions
    # ------------------------------------------------------------------

    async def _intent_router(self, state: SanctaState) -> SanctaState:
        """Classify user intent via LLM when not already present."""

        if state.get("intent") and state["intent"] in VALID_INTENTS:
            logger.debug("Intent already set: %s", state["intent"])
            return state

        prompt = INTENT_ROUTING_PROMPT.format(
            emotion_vector=state.get("emotion_vector", {}),
            spiritual_state=state.get("spiritual_state", {}),
        )

        try:
            response = await self._llm.ainvoke(prompt)
            raw_intent = response.content.strip().lower()
            intent = raw_intent if raw_intent in VALID_INTENTS else "lectio_divina"
        except Exception as exc:
            logger.error("Intent routing failed: %s", exc)
            intent = "lectio_divina"

        logger.info("Resolved intent: %s (user=%s)", intent, state.get("user_id"))
        return {**state, "intent": intent}

    async def _dispatch_lectio_divina(self, state: SanctaState) -> SanctaState:
        """Delegate to the Lectio Divina sub-graph."""
        from app.agents.lectio_divina.lectio_divina_graph import (
            LectioDivinaSupervisor,
        )

        supervisor = LectioDivinaSupervisor()
        return await supervisor.run(state)

    async def _dispatch_free_reflection(self, state: SanctaState) -> SanctaState:
        logger.info("Dispatching to free_reflection (stub).")
        return state

    async def _dispatch_interactive_bible(self, state: SanctaState) -> SanctaState:
        logger.info("Dispatching to interactive_bible (stub).")
        return state

    async def _dispatch_spiritual_direction(self, state: SanctaState) -> SanctaState:
        logger.info("Dispatching to spiritual_direction (stub).")
        return state

    async def _dispatch_community(self, state: SanctaState) -> SanctaState:
        logger.info("Dispatching to community (stub).")
        return state

    async def _dispatch_crisis(self, state: SanctaState) -> SanctaState:
        """Crisis path — return safe, immediate content."""
        logger.warning("Crisis intent detected for user=%s", state.get("user_id"))
        return {
            **state,
            "prayer": {
                "text": (
                    "Panie, bądź przy mnie w tej chwili. "
                    "Nie jestem sam/sama — Ty jesteś ze mną. "
                    "Proszę, daj mi siłę i pokój."
                ),
                "tradition": "universal",
            },
            "action": {
                "challenge": (
                    "Jeśli potrzebujesz natychmiastowej pomocy, "
                    "skontaktuj się z Telefonem Zaufania: 116 123."
                ),
            },
        }

    async def _quality_gate(self, state: SanctaState) -> SanctaState:
        """Final quality validation before returning to the user."""
        from app.agents.orchestration.quality_gate import QualityGateAgent

        gate = QualityGateAgent()
        return await gate.validate(state)

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------

    @staticmethod
    def _route_by_intent(
        state: SanctaState,
    ) -> Literal[
        "lectio_divina",
        "free_reflection",
        "interactive_bible",
        "spiritual_direction",
        "community",
        "crisis",
    ]:
        intent = state.get("intent", "lectio_divina")
        if intent not in VALID_INTENTS:
            return "lectio_divina"
        return intent  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(SanctaState)

        # Nodes
        builder.add_node("intent_router", self._intent_router)
        builder.add_node("lectio_divina", self._dispatch_lectio_divina)
        builder.add_node("free_reflection", self._dispatch_free_reflection)
        builder.add_node("interactive_bible", self._dispatch_interactive_bible)
        builder.add_node("spiritual_direction", self._dispatch_spiritual_direction)
        builder.add_node("community", self._dispatch_community)
        builder.add_node("crisis", self._dispatch_crisis)
        builder.add_node("quality_gate", self._quality_gate)

        # Edges
        builder.add_edge(START, "intent_router")

        builder.add_conditional_edges(
            "intent_router",
            self._route_by_intent,
            {
                "lectio_divina": "lectio_divina",
                "free_reflection": "free_reflection",
                "interactive_bible": "interactive_bible",
                "spiritual_direction": "spiritual_direction",
                "community": "community",
                "crisis": "crisis",
            },
        )

        # All sub-graphs funnel into quality_gate
        for node in (
            "lectio_divina",
            "free_reflection",
            "interactive_bible",
            "spiritual_direction",
            "community",
            "crisis",
        ):
            builder.add_edge(node, "quality_gate")

        builder.add_edge("quality_gate", END)

        return builder.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def graph(self) -> Any:
        """Return the compiled LangGraph for external invocation."""
        return self._graph

    async def run(self, state: SanctaState) -> SanctaState:
        """Execute the full orchestration pipeline."""
        logger.info(
            "OrchestratorSupremus run started (user=%s)", state.get("user_id")
        )
        result = await self._graph.ainvoke(state)
        logger.info(
            "OrchestratorSupremus run completed (user=%s)", state.get("user_id")
        )
        return result


# ---------------------------------------------------------------------------
# Module-level compiled graph (for LangGraph Studio / serve)
# ---------------------------------------------------------------------------

_orchestrator = OrchestratorSupremus()
sancta_graph = _orchestrator.graph
