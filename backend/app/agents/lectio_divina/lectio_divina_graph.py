"""
Lectio Divina Supervisor (A-002)
================================
Builds and compiles the LangGraph StateGraph for the complete
Lectio Divina flow, now enriched with:

  - Content Uniqueness Engine integration
  - Kerygmatic cycle awareness
  - 7 prayer traditions (rotation)
  - Sacred word extraction for contemplatio
  - Works of Mercy action categories
  - Full liturgical context propagation

Flow:
  emotion_analysis -> scripture_selection -> lectio
      -> meditatio -> oratio -> contemplatio -> actio

"Divina enim Scriptura ... crescit cum legente." — St Gregory the Great
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.lectio_divina.actio_agent import ActioAgent
from app.agents.lectio_divina.contemplatio_agent import ContemplatioAgent
from app.agents.lectio_divina.lectio_agent import LectioAgent
from app.agents.lectio_divina.meditatio_agent import MeditatioAgent
from app.agents.lectio_divina.oratio_agent import OratioAgent
from app.services.content.uniqueness_engine import ContentUniquenessEngine

logger = logging.getLogger("sancta_nexus.lectio_divina_graph")


# ---------------------------------------------------------------------------
# State definition — enriched
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

    # Uniqueness context
    uniqueness_context: dict[str, Any]

    # Tradition preference
    tradition: str

    # Kerygmatic theme
    kerygmatic_theme: str

    # Error tracking
    error: str | None


# ---------------------------------------------------------------------------
# Crisis detection
# ---------------------------------------------------------------------------

CRISIS_KEYWORDS: frozenset[str] = frozenset({
    "samobojstwo", "suicide", "nie chce zyc", "chce umrzec",
    "skrzywdzic sie", "self-harm", "beznadziejnosc",
    "chce sie zabic", "nie mam po co zyc", "chce zniknac",
})

CRISIS_EMOTION_THRESHOLD = 0.85


def _detect_crisis(state: LectioDivinaState) -> bool:
    emotion = state.get("emotion_vector", {})
    if emotion.get("despair", 0.0) > CRISIS_EMOTION_THRESHOLD:
        return True
    if emotion.get("suicidal_ideation", 0.0) > 0.0:
        return True
    raw_input = str(state.get("raw_input", "")).lower()
    if any(kw in raw_input for kw in CRISIS_KEYWORDS):
        return True
    return False


# ---------------------------------------------------------------------------
# Lectio Divina Supervisor
# ---------------------------------------------------------------------------


class LectioDivinaSupervisor:
    """
    A-002 — Supervisor orchestrating the Lectio Divina pipeline
    with full Content Uniqueness Engine integration.
    """

    def __init__(self) -> None:
        self._lectio_agent = LectioAgent()
        self._meditatio_agent = MeditatioAgent()
        self._oratio_agent = OratioAgent()
        self._contemplatio_agent = ContemplatioAgent()
        self._actio_agent = ActioAgent()
        self._uniqueness = ContentUniquenessEngine()

        self._graph = self._build_graph()
        logger.info("LectioDivinaSupervisor (A-002) initialised with uniqueness engine.")

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    async def _emotion_analysis(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """Analyse emotions and build uniqueness context."""
        logger.info("Node: emotion_analysis")

        if state.get("emotion_vector"):
            dominant = max(
                state["emotion_vector"],
                key=state["emotion_vector"].get,
                default="neutral",
            )
        else:
            default_vector: dict[str, float] = {
                "peace": 0.5, "gratitude": 0.3,
                "sadness": 0.1, "joy": 0.3,
            }
            state = {**state, "emotion_vector": default_vector}
            dominant = "peace"

        # Build uniqueness context
        season = (state.get("liturgical_context") or {}).get("season", "ordinary")
        ctx = self._uniqueness.build_session_context(
            user_id=state.get("user_id", "anonymous"),
            season=season,
            emotion=dominant,
            user_history=state.get("user_history"),
        )

        return {
            **state,
            "dominant_emotion": dominant,
            "uniqueness_context": ctx,
            "tradition": state.get("tradition") or ctx["suggested_tradition"],
            "kerygmatic_theme": ctx["kerygmatic_theme"]["theme"],
        }

    async def _scripture_selection(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """A-010: Select scripture with uniqueness engine."""
        logger.info("Node: scripture_selection")
        scripture = await self._lectio_agent.select_scripture(
            emotion_vector=state.get("emotion_vector", {}),
            liturgical_context=state.get("liturgical_context"),
            user_history=state.get("user_history"),
            user_id=state.get("user_id", "anonymous"),
        )
        return {**state, "scripture": scripture}

    async def _lectio(self, state: LectioDivinaState) -> LectioDivinaState:
        """Lectio node: enrichment of the scripture passage."""
        logger.info("Node: lectio")
        scripture = state.get("scripture", {})
        if not scripture.get("historical_context"):
            scripture["historical_context"] = (
                "Kontekst historyczny zostanie uzupelniony w przyszlych wersjach."
            )
        return {**state, "scripture": scripture}

    async def _meditatio(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """A-011: Generate meditation with kerygmatic awareness."""
        logger.info("Node: meditatio")
        user_context = {
            "emotion_vector": state.get("emotion_vector", {}),
            "dominant_emotion": state.get("dominant_emotion", ""),
        }
        meditation = await self._meditatio_agent.meditate(
            scripture=state.get("scripture", {}),
            user_context=user_context,
            kerygmatic_theme=state.get("kerygmatic_theme", ""),
        )
        return {**state, "meditation": meditation}

    async def _oratio(self, state: LectioDivinaState) -> LectioDivinaState:
        """A-012: Generate prayer in the rotated tradition."""
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
        """A-013: Generate contemplation with liturgical awareness."""
        logger.info("Node: contemplatio")
        season = (state.get("liturgical_context") or {}).get("season", "ordinary")
        contemplation = await self._contemplatio_agent.contemplate(
            scripture=state.get("scripture", {}),
            season=season,
        )
        return {**state, "contemplation": contemplation}

    async def _actio(self, state: LectioDivinaState) -> LectioDivinaState:
        """A-014: Generate action with Works of Mercy rotation."""
        logger.info("Node: actio")
        ctx = state.get("uniqueness_context", {})
        suggested_category = ctx.get("suggested_action_category", "gratitude")
        action = await self._actio_agent.challenge(
            scripture=state.get("scripture", {}),
            reflection=state.get("meditation", {}),
            suggested_category=suggested_category,
        )
        return {**state, "action": action}

    async def _crisis_handler(
        self, state: LectioDivinaState
    ) -> LectioDivinaState:
        """Immediate safe response for crisis situations."""
        logger.warning(
            "CRISIS detected for user=%s — activating safe response.",
            state.get("user_id"),
        )
        return {
            **state,
            "scripture": {
                "book": "Ksiega Psalmow",
                "book_abbrev": "Ps",
                "chapter": 34,
                "verse_start": 19,
                "verse_end": 19,
                "text": (
                    "Pan jest blisko ludzi skruszonych w sercu, "
                    "ocala zlamanych na duchu."
                ),
                "translation": "BT5",
                "historical_context": "Psalm pocieszenia — Boza bliskosc w cierpieniu.",
                "patristic_note": (
                    "Sw. Augustyn: 'Bog jest blizej nas w naszym bolu, "
                    "niz my sami jestesmy blisko siebie.'"
                ),
            },
            "prayer": {
                "prayer_text": (
                    "Panie, Ty znasz moj bol. Badz przy mnie teraz. "
                    "Nie pozwol, bym czul/czula sie sam/sama. "
                    "Trzymaj mnie w swoich rekach. Amen."
                ),
                "tradition": "universal",
                "elements": ["petitio"],
            },
            "action": {
                "challenge_text": (
                    "Zadzwon do kogos bliskiego lub na Telefon Zaufania: 116 123. "
                    "Nie jestes sam/sama. Mozesz tez napisac na czat: "
                    "116123.pl. Twoje zycie ma wartosc."
                ),
                "difficulty": "easy",
                "category": "self_care",
                "evening_examen": {
                    "retrospection": "Czy udalo ci sie dzis porozmawiac z kims bliskim?",
                    "divine_presence": "Czy poczules/as Boza obecnosc w rozmowie z ta osoba?",
                    "resolution": "Jutro tez mozesz zadzwonic. Nie jestes sam/sama.",
                },
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

        builder.add_node("emotion_analysis", self._emotion_analysis)
        builder.add_node("scripture_selection", self._scripture_selection)
        builder.add_node("lectio", self._lectio)
        builder.add_node("meditatio", self._meditatio)
        builder.add_node("oratio", self._oratio)
        builder.add_node("contemplatio", self._contemplatio)
        builder.add_node("actio", self._actio)
        builder.add_node("crisis_handler", self._crisis_handler)

        builder.add_edge(START, "emotion_analysis")

        builder.add_conditional_edges(
            "emotion_analysis", self._check_crisis,
            {"crisis_handler": "crisis_handler", "scripture_selection": "scripture_selection"},
        )
        builder.add_conditional_edges(
            "scripture_selection", self._check_crisis_after_scripture,
            {"crisis_handler": "crisis_handler", "lectio": "lectio"},
        )

        builder.add_edge("lectio", "meditatio")
        builder.add_edge("meditatio", "oratio")
        builder.add_edge("oratio", "contemplatio")
        builder.add_edge("contemplatio", "actio")

        builder.add_edge("actio", END)
        builder.add_edge("crisis_handler", END)

        return builder.compile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def graph(self) -> Any:
        return self._graph

    async def run(self, state: LectioDivinaState) -> LectioDivinaState:
        logger.info("LectioDivinaSupervisor run started (user=%s)", state.get("user_id"))
        try:
            result = await self._graph.ainvoke(state)
            logger.info("LectioDivinaSupervisor run completed (user=%s)", state.get("user_id"))
            return result
        except Exception as exc:
            logger.error("Lectio Divina pipeline failed: %s", exc, exc_info=True)
            return {**state, "error": f"Lectio Divina pipeline error: {exc}"}


# ---------------------------------------------------------------------------
# Module-level exports
# ---------------------------------------------------------------------------

_supervisor = LectioDivinaSupervisor()
lectio_divina_graph = _supervisor.graph


async def run_session(
    user_id: str,
    emotion_vector: dict[str, float] | None = None,
    liturgical_context: dict[str, Any] | None = None,
    user_history: list[dict[str, Any]] | None = None,
    tradition: str = "",
    raw_input: str = "",
) -> LectioDivinaState:
    """Convenience function to run a full Lectio Divina session."""
    initial_state: LectioDivinaState = {
        "user_id": user_id,
        "raw_input": raw_input,
        "emotion_vector": emotion_vector or {},
        "liturgical_context": liturgical_context,
        "user_history": user_history,
        "tradition": tradition,  # empty = let uniqueness engine decide
    }
    return await _supervisor.run(initial_state)
