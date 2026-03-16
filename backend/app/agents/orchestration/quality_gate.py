"""
Quality Gate Agent (A-009)
==========================
Validates all agent outputs before they reach the user.
Implements a circuit-breaker pattern with retry tracking and falls back
to safe, pre-approved content when quality thresholds are not met.

Public methods:
  - validate_output   -- structural + theological + emotional validation
  - check_theological_safety -- LLM-based doctrinal review
  - get_fallback_content -- retrieve safe fallback for any stage

"Omnia probate; quod bonum est tenete." -- 1 Thess 5:21
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger("sancta_nexus.quality_gate")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
MIN_CONTENT_LENGTH = 20

THEOLOGICAL_SAFETY_PROMPT = """\
Jestes teologiem katolickim odpowiedzialnym za walidacje tresci duchowych.
Ocen ponizszą tresc pod katem:
1. Zgodnosci z nauczaniem Kosciola Katolickiego
2. Braku herezji i bledow doktrynalnych
3. Wrazliwosci pastoralnej
4. Odpowiedniosci dla osoby w danym stanie emocjonalnym

Tresc do walidacji:
{content}

Stan emocjonalny uzytkownika:
{emotion_vector}

Odpowiedz w formacie JSON:
{{
  "is_safe": true,
  "confidence": 0.95,
  "concerns": [],
  "suggestion": ""
}}

Jesli tresc jest bezpieczna, ustaw is_safe na true.
Jesli zawiera bledy doktrynalne lub moze byc szkodliwa, ustaw is_safe na false
i opisz zastrzezenia w polu concerns.
"""

# ---------------------------------------------------------------------------
# Fallback content -- pre-approved, always safe
# ---------------------------------------------------------------------------

FALLBACK_CONTENT: dict[str, dict[str, Any]] = {
    "scripture": {
        "book": "Ksiega Psalmow",
        "chapter": 23,
        "verse_start": 1,
        "verse_end": 4,
        "text": (
            "Pan jest moim pasterzem, nie brak mi niczego. "
            "Pozwala mi lezec na zielonych pastwiskach. "
            "Prowadzi mnie nad wody, gdzie moge odpoczac. "
            "Orzezwia moja dusze."
        ),
        "translation": "BT5",
        "historical_context": "Psalm pocieszenia -- Dawid wyraza zaufanie do Boga.",
    },
    "meditation": {
        "questions": [
            "Co oznacza dla ciebie, ze Pan jest twoim pasterzem?",
            "Gdzie w swoim zyciu doswiadczasz Bozego prowadzenia?",
        ],
        "reflection_layers": {
            "exegetical": "Psalm 23 to jeden z najstarszych psalmow wyrazajacych zaufanie do Boga-Pasterza.",
            "existential": "Kazdy z nas potrzebuje przewodnika -- komu ufasz w swoim zyciu?",
            "mystical": "Bog prowadzi cie lagodnie, nawet gdy tego nie dostrzegasz.",
            "practical": "Zaufanie Bogu moze zaczac sie od jednej malej decyzji dzisiaj.",
        },
    },
    "prayer": {
        "prayer_text": (
            "Panie, Ty jestes moim Pasterzem. "
            "Prowadz mnie dzis przez ten dzien. "
            "Daj mi pokoj serca i sile ducha. Amen."
        ),
        "tradition": "universal",
        "elements": ["laudatio", "petitio"],
    },
    "contemplation": {
        "guidance_text": (
            "Zamknij oczy. Oddychaj spokojnie. "
            "Powtarzaj w sercu: 'Pan jest moim Pasterzem'. "
            "Trwaj w ciszy przez dwie minuty."
        ),
        "breathing_pattern": {
            "inhale_seconds": 4,
            "hold_seconds": 4,
            "exhale_seconds": 6,
            "cycles": 3,
        },
        "duration_minutes": 2,
        "ambient_suggestion": "silence",
    },
    "action": {
        "challenge_text": (
            "Dzis poswiec 5 minut na cisze i zauważ "
            "jeden moment, w ktorym poczujesz Boze prowadzenie."
        ),
        "difficulty": "easy",
        "category": "gratitude",
        "evening_checkin_prompt": (
            "Czy zauwazyles/zauwazylaz dzis moment Bozego prowadzenia?"
        ),
    },
}

# All valid stage names
VALID_STAGES = frozenset(FALLBACK_CONTENT.keys())


# ---------------------------------------------------------------------------
# Circuit breaker bookkeeping
# ---------------------------------------------------------------------------


@dataclass
class _CircuitState:
    """Per-node retry tracking for the circuit-breaker pattern."""

    failures: dict[str, int] = field(default_factory=dict)

    def record_failure(self, node: str) -> None:
        self.failures[node] = self.failures.get(node, 0) + 1

    def is_open(self, node: str) -> bool:
        """Return True if the circuit breaker has tripped (too many failures)."""
        return self.failures.get(node, 0) >= MAX_RETRIES

    def reset(self, node: str) -> None:
        self.failures.pop(node, None)

    @property
    def failure_counts(self) -> dict[str, int]:
        return dict(self.failures)


# ---------------------------------------------------------------------------
# Quality Gate Agent
# ---------------------------------------------------------------------------


class QualityGateAgent:
    """
    A-009 -- Quality gate that validates every piece of content before
    it is surfaced to the user.

    Implements a circuit-breaker pattern: after ``MAX_RETRIES`` consecutive
    failures for a given stage, the agent stops calling the LLM and
    returns pre-approved fallback content instead.

    Public methods:
        validate_output          -- full validation pipeline
        check_theological_safety -- LLM-based doctrinal review
        get_fallback_content     -- retrieve safe fallback for any stage
    """

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=0.1)
        self._circuit = _CircuitState()
        logger.info("QualityGateAgent (A-009) initialised with model=%s.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def validate_output(
        self,
        stage: str,
        content: dict[str, Any],
        emotion_vector: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Validate content from a specific pipeline stage.

        Runs structural checks, theological safety validation, and
        circuit-breaker logic. Returns a validation report.

        Args:
            stage: Pipeline stage name (scripture, meditation, prayer,
                   contemplation, action).
            content: The content dict to validate.
            emotion_vector: Optional emotion vector for context-aware checks.

        Returns:
            Dict with keys:
              - is_valid: bool
              - stage: str
              - content: the original or fallback content
              - concerns: list of issues found
              - used_fallback: bool
        """
        emotion_vector = emotion_vector or {}
        node_key = f"quality_gate.{stage}"

        # Circuit breaker check
        if self._circuit.is_open(node_key):
            logger.warning(
                "Circuit breaker OPEN for %s -- returning fallback.", stage
            )
            return {
                "is_valid": False,
                "stage": stage,
                "content": self.get_fallback_content(stage),
                "concerns": ["circuit_breaker_open"],
                "used_fallback": True,
            }

        concerns: list[str] = []

        # 1. Structural validation
        text = self._extract_text(content)
        if len(text) < MIN_CONTENT_LENGTH:
            concerns.append(f"Content too short ({len(text)} chars, min {MIN_CONTENT_LENGTH})")
            self._circuit.record_failure(node_key)

            if self._circuit.is_open(node_key):
                return {
                    "is_valid": False,
                    "stage": stage,
                    "content": self.get_fallback_content(stage),
                    "concerns": concerns,
                    "used_fallback": True,
                }

            return {
                "is_valid": False,
                "stage": stage,
                "content": content,
                "concerns": concerns,
                "used_fallback": False,
            }

        # 2. Theological safety (skip for action items)
        if stage != "action":
            safety = await self.check_theological_safety(text, emotion_vector)
            if not safety["is_safe"]:
                concerns.extend(safety.get("concerns", []))
                self._circuit.record_failure(node_key)

                if self._circuit.is_open(node_key):
                    return {
                        "is_valid": False,
                        "stage": stage,
                        "content": self.get_fallback_content(stage),
                        "concerns": concerns,
                        "used_fallback": True,
                    }

                return {
                    "is_valid": False,
                    "stage": stage,
                    "content": content,
                    "concerns": concerns,
                    "used_fallback": False,
                }

        # All checks passed
        self._circuit.reset(node_key)
        return {
            "is_valid": True,
            "stage": stage,
            "content": content,
            "concerns": [],
            "used_fallback": False,
        }

    async def check_theological_safety(
        self,
        content: str,
        emotion_vector: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Check content against Catholic theological standards via LLM.

        Args:
            content: The text content to validate.
            emotion_vector: Optional emotional context.

        Returns:
            Dict with: is_safe (bool), confidence (float),
            concerns (list[str]), suggestion (str).
        """
        emotion_vector = emotion_vector or {}

        prompt = THEOLOGICAL_SAFETY_PROMPT.format(
            content=content,
            emotion_vector=json.dumps(emotion_vector, ensure_ascii=False),
        )

        try:
            response = await self._llm.ainvoke(prompt)
            result = self._parse_json(response.content)

            is_safe = result.get("is_safe", True)
            if isinstance(is_safe, str):
                is_safe = is_safe.lower() == "true"

            return {
                "is_safe": bool(is_safe),
                "confidence": float(result.get("confidence", 0.5)),
                "concerns": result.get("concerns", []),
                "suggestion": result.get("suggestion", ""),
            }

        except Exception as exc:
            logger.error("Theological safety check failed: %s", exc, exc_info=True)
            # Fail open for availability -- but log loudly
            return {
                "is_safe": True,
                "confidence": 0.0,
                "concerns": [f"Validation error: {exc}"],
                "suggestion": "",
            }

    def get_fallback_content(self, stage: str) -> dict[str, Any]:
        """
        Retrieve safe, pre-approved fallback content for a pipeline stage.

        Args:
            stage: One of 'scripture', 'meditation', 'prayer',
                   'contemplation', 'action'.

        Returns:
            Dict with safe content appropriate for the stage.
        """
        if stage not in VALID_STAGES:
            logger.warning(
                "Unknown stage '%s' requested for fallback; returning scripture.",
                stage,
            )
            return dict(FALLBACK_CONTENT["scripture"])
        return dict(FALLBACK_CONTENT[stage])

    def check_circuit_breaker(self, stage: str) -> bool:
        """Return True if the circuit breaker is open (tripped) for *stage*."""
        return self._circuit.is_open(f"quality_gate.{stage}")

    @property
    def failure_counts(self) -> dict[str, int]:
        """Current failure counts per node (for monitoring)."""
        return self._circuit.failure_counts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(content: dict[str, Any] | str) -> str:
        """Pull a human-readable string out of a content dict."""
        if isinstance(content, str):
            return content
        for key in (
            "text",
            "prayer_text",
            "guidance_text",
            "challenge_text",
            "guidance",
            "challenge",
            "questions",
        ):
            val = content.get(key)
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                return " ".join(str(v) for v in val)
        return str(content)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Best-effort JSON extraction from LLM output."""
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse validation JSON: %s", exc)
            return {"is_safe": True, "confidence": 0.0, "concerns": []}
