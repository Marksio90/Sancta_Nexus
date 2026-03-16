"""
Lectio Divina Supervisor (A-002)
================================
Builds and compiles the LangGraph StateGraph for the complete
Lectio Divina flow:

  emotion_analysis -> scripture_selection -> lectio
      -> meditatio -> oratio -> contemplatio -> actio

Exports a compiled graph and a convenience ``run_session`` async function.

"Divina enim Scriptura ... crescit cum legente." -- St Gregory the Great
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.agents.lectio_divina.actio_agent import ActioAgent
from backend.app.agents.lectio_divina.contemplatio_agent import ContemplatioAgent
from backend.app.agents.lectio_divina.lectio_agent import LectioAgent
from backend.app.agents.lectio_divina.meditatio_agent import MeditatioAgent
from backend.app.agents.lectio_divina.oratio_agent import OratioAgent

logger = logging.getLogger("sancta_nexus.lectio_divina_graph")


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------


class LectioDivinaState(TypedDict, total=False):
    """Canonical state flowing through the Lectio Divina graph."""

    user_id: str
    raw_input: str

    # Emotion analysis output
    emotion_vector: dict[str, float]
    dominant_emotion: str

    # Liturgical context
    liturgical_context: dict[str, Any] | None

    # Session memory
    user_history: list[dict[str, Any]] | None

    # Pipeline outputs (populated by each node)
    scripture: dict[str, Any]
    meditation: dict[str, Any]
    prayer: dict[str, Any]
    contemplation: dict[str, Any]
    action: dict[str, Any]

    # Tradition preference
    tradition: str

    # Error tracking
    error: str | None


# ---------------------------------------------------------------------------
# Crisis detection
# ---------------------------------------------------------------------------

CRISIS_KEYWORDS: frozenset[str] = frozenset(
    {
        "samobojstwo",
        "suicide",
        "nie chce zyc",
        "chce umrzec",
        "skrzywdzic sie",
        "self-harm",
        "beznadziejnosc",
    }
)

CRISIS_EMOTION_THRESHOLD = 0.85


def _detect_crisis(state: LectioDivinaState) -> bool:
    """Return True if the user's state indicates a crisis."""
    emotion = state.get("emotion_vector", {})
    if emotion.get("despair", 0.0) > CRISIS_EMOTION_THRESHOLD:
        return True
    if emotion.get("suicidal_ideation", 0.0) > 0.0:
        return True

    raw_input = str(state.get("raw_input", "")).lower()
    if any(kw in raw_input for kw in CRISIS_KEYWORDS):
        return True

    for entry in state.get("user_history", []) or []:
        text = str(entry.get("user_input", "")).lower()
        if any(kw in text for kw in CRISIS_KEYWORDS):
            return True

    return False


# ---------------------------------------------------------------------------
# Lectio Divina Supervisor
# ---------------------------------------------------------------------------


class LectioDivinaSupervisor:
    """
    A-002 -- Supervisor that orchestrates the Lectio Divina pipeline
    as a LangGraph StateGraph with nodes:

      emotion_analysis -> scripture_selection -> lectio
          -> meditatio -> oratio -> contemplatio -> actio
    """

    def __init__(self) -> None:
        self._lectio_agent = LectioAgent()
        self._meditatio_agent = MeditatioAgent()
        self._oratio_agent = OratioAgent()
        self._contemplatio_agent = ContemplatioAgent()
        self._actio_agent = ActioAgent()

        self._graph = self._build_graph()
        logger.info("LectioDivinaSupervisor (A-002) initialised.")

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    async def _emotion_analysis(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """
        Analyse the user's emotional state.

        If an emotion_vector is already present (e.g. from the parent
        orchestrator), this node is a pass-through. Otherwise it sets
        a neutral default.
        """
        logger.info("Node: emotion_analysis")

        if state.get("emotion_vector"):
            dominant = max(
                state["emotion_vector"],
                key=state["emotion_vector"].get,
                default="neutral",
            )
            return {**state, "dominant_emotion": dominant}

        # Default neutral vector when none is provided
        default_vector: dict[str, float] = {
            "peace": 0.5,
            "gratitude": 0.3,
            "sadness": 0.1,
            "joy": 0.3,
        }
        return {
            **state,
            "emotion_vector": default_vector,
            "dominant_emotion": "peace",
        }

    async def _scripture_selection(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """A-010: Select a scripture passage."""
        logger.info("Node: scripture_selection")
        scripture = await self._lectio_agent.select_scripture(
            emotion_vector=state.get("emotion_vector", {}),
            liturgical_context=state.get("liturgical_context"),
            user_history=state.get("user_history"),
        )
        return {**state, "scripture": scripture}

    async def _lectio(self, state: LectioDivinaState) -> LectioDivinaState:
        """
        Lectio node: reading and enrichment of the scripture passage.

        This is the 'reading' step -- the scripture is already selected,
        so we just ensure it is properly structured for downstream nodes.
        """
        logger.info("Node: lectio")
        # Scripture is already selected; this node can add enrichment
        scripture = state.get("scripture", {})
        if not scripture.get("historical_context"):
            scripture["historical_context"] = (
                "Kontekst historyczny zostanie uzupelniony w przyszlych wersjach."
            )
        return {**state, "scripture": scripture}

    async def _meditatio(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """A-011: Generate meditation questions and reflection layers."""
        logger.info("Node: meditatio")
        user_context = {
            "emotion_vector": state.get("emotion_vector", {}),
            "dominant_emotion": state.get("dominant_emotion", ""),
        }
        meditation = await self._meditatio_agent.meditate(
            scripture=state.get("scripture", {}),
            user_context=user_context,
        )
        return {**state, "meditation": meditation}

    async def _oratio(self, state: LectioDivinaState) -> LectioDivinaState:
        """A-012: Generate prayer."""
        logger.info("Node: oratio")
        tradition = state.get("tradition", "ignatian")
        prayer = await self._oratio_agent.pray(
            scripture=state.get("scripture", {}),
            emotion_state=state.get("emotion_vector", {}),
            tradition=tradition,
        )
        return {**state, "prayer": prayer}

    async def _contemplatio(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """A-013: Generate contemplation guidance."""
        logger.info("Node: contemplatio")
        contemplation = await self._contemplatio_agent.contemplate(
            scripture=state.get("scripture", {}),
        )
        return {**state, "contemplation": contemplation}

    async def _actio(self, state: LectioDivinaState) -> LectioDivinaState:
        """A-014: Generate daily action / micro-quest."""
        logger.info("Node: actio")
        action = await self._actio_agent.challenge(
            scripture=state.get("scripture", {}),
            reflection=state.get("meditation", {}),
        )
        return {**state, "action": action}

    async def _crisis_handler(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """Immediate safe response for crisis situations."""
        logger.warning(
            "CRISIS detected for user=%s -- activating safe response.",
            state.get("user_id"),
        )
        return {
            **state,
            "scripture": {
                "book": "Ksiega Psalmow",
                "chapter": 34,
                "verse_start": 19,
                "verse_end": 19,
                "text": (
                    "Pan jest blisko ludzi skruszonych w sercu, "
                    "ocala zlamanych na duchu."
                ),
                "translation": "BT5",
                "historical_context": "Psalm pocieszenia -- Boza bliskosc w cierpieniu.",
            },
            "prayer": {
                "prayer_text": (
                    "Panie, Ty znasz moj bol. Badz przy mnie teraz. "
                    "Nie pozwol, bym czul/czula sie sam/sama. Amen."
                ),
                "tradition": "universal",
                "elements": ["petitio"],
            },
            "action": {
                "challenge_text": (
                    "Zadzwon do kogos bliskiego lub na Telefon Zaufania: 116 123. "
                    "Nie jestes sam/sama."
                ),
                "difficulty": "easy",
                "category": "self_care",
                "evening_checkin_prompt": (
                    "Czy udalo ci sie dzis porozmawiac z kims bliskim?"
                ),
            },
            "error": None,
        }

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    @staticmethod
    def _check_crisis(
        state: LectioDivinaState,
    ) -> Literal["crisis_handler", "scripture_selection"]:
        if _detect_crisis(state):
            return "crisis_handler"
        return "scripture_selection"

    @staticmethod
    def _check_crisis_after_scripture(
        state: LectioDivinaState,
    ) -> Literal["crisis_handler", "lectio"]:
        if _detect_crisis(state):
            return "crisis_handler"
        return "lectio"

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(LectioDivinaState)

        # --- Nodes ---
        builder.add_node("emotion_analysis", self._emotion_analysis)
        builder.add_node("scripture_selection", self._scripture_selection)
        builder.add_node("lectio", self._lectio)
        builder.add_node("meditatio", self._meditatio)
        builder.add_node("oratio", self._oratio)
        builder.add_node("contemplatio", self._contemplatio)
        builder.add_node("actio", self._actio)
        builder.add_node("crisis_handler", self._crisis_handler)

        # --- Edges ---

        # START -> emotion_analysis
        builder.add_edge(START, "emotion_analysis")

        # After emotion analysis, check for crisis
        builder.add_conditional_edges(
            "emotion_analysis",
            self._check_crisis,
            {
                "crisis_handler": "crisis_handler",
                "scripture_selection": "scripture_selection",
            },
        )

        # After scripture selection, check for crisis
        builder.add_conditional_edges(
            "scripture_selection",
            self._check_crisis_after_scripture,
            {
                "crisis_handler": "crisis_handler",
                "lectio": "lectio",
            },
        )

        # Linear flow for the remaining stages
        builder.add_edge("lectio", "meditatio")
        builder.add_edge("meditatio", "oratio")
        builder.add_edge("oratio", "contemplatio")
        builder.add_edge("contemplatio", "actio")

        # Terminal nodes
        builder.add_edge("actio", END)
        builder.add_edge("crisis_handler", END)

        return builder.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def graph(self) -> Any:
        """Return the compiled LangGraph."""
        return self._graph

    async def run(self, state: LectioDivinaState) -> LectioDivinaState:
        """Execute the full Lectio Divina pipeline."""
        logger.info(
            "LectioDivinaSupervisor run started (user=%s)",
            state.get("user_id"),
        )
        try:
            result = await self._graph.ainvoke(state)
            logger.info(
                "LectioDivinaSupervisor run completed (user=%s)",
                state.get("user_id"),
            )
            return result
        except Exception as exc:
            logger.error("Lectio Divina pipeline failed: %s", exc, exc_info=True)
            return {
                **state,
                "error": f"Lectio Divina pipeline error: {exc}",
            }


# ---------------------------------------------------------------------------
# Module-level exports
# ---------------------------------------------------------------------------

_supervisor = LectioDivinaSupervisor()

#: Compiled LangGraph -- can be served by LangGraph Studio / LangServe.
lectio_divina_graph = _supervisor.graph


async def run_session(
    user_id: str,
    emotion_vector: dict[str, float] | None = None,
    liturgical_context: dict[str, Any] | None = None,
    user_history: list[dict[str, Any]] | None = None,
    tradition: str = "ignatian",
    raw_input: str = "",
) -> LectioDivinaState:
    """
    Convenience function to run a full Lectio Divina session.

    Args:
        user_id: Unique user identifier.
        emotion_vector: Mapping of emotion labels to intensity scores.
        liturgical_context: Optional liturgical calendar context.
        user_history: Optional list of past sessions.
        tradition: Prayer tradition (ignatian, carmelite, franciscan,
                   benedictine, charismatic).
        raw_input: Raw user text input (used for crisis detection).

    Returns:
        Completed LectioDivinaState with all pipeline outputs.
    """
    initial_state: LectioDivinaState = {
        "user_id": user_id,
        "raw_input": raw_input,
        "emotion_vector": emotion_vector or {},
        "liturgical_context": liturgical_context,
        "user_history": user_history,
        "tradition": tradition,
    }
    return await _supervisor.run(initial_state)
