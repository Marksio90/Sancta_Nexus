"""
Contemplatio Agent (A-013)
==========================
Generates gentle, minimalist contemplation guidance for the silent-prayer
phase of Lectio Divina. Provides breathing exercises, ambient suggestions,
and timer recommendations.

The guidance intentionally uses few words -- contemplatio is about
*resting* in God's presence, not thinking more.

"Vacate et videte quoniam ego sum Deus." -- Ps 46:11
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger("sancta_nexus.contemplatio_agent")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CONTEMPLATIO_SYSTEM_PROMPT = """\
Jestes przewodnikiem kontemplacji chrzescijanskiej w systemie Sancta Nexus.
Twoim zadaniem jest przygotowanie delikatnego, minimalistycznego
przewodnictwa do ciszy modlitewnej.

Fragment Pisma: {book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}

Zasady -- WAZNE:
1. Uzywaj MINIMALNEJ ilosci slow -- kontemplacja to cisza, nie wyklad
2. Podaj wzorzec oddechowy (np. wdech 4s, zatrzymanie 4s, wydech 6s)
3. Zaproponuj czas trwania: 2, 3 lub 5 minut
4. Ton: cieply, lagodny, pelny szacunku dla ciszy
5. NIE tlumacz, NIE pouczaj -- tylko delikatnie prowadz
6. Zasugeruj atmosfere dzwiekowa (cisza, dzwieki natury, spiew gregorianski)

Odpowiedz w formacie JSON:
{{
  "guidance_text": "Tekst przewodnictwa kontemplacyjnego (max 60 slow)",
  "breathing_pattern": {{
    "inhale_seconds": 4,
    "hold_seconds": 4,
    "exhale_seconds": 6,
    "cycles": 3
  }},
  "duration_minutes": 2,
  "ambient_suggestion": "silence|nature_sounds|gregorian_chant|bells"
}}
"""

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

FALLBACK_CONTEMPLATION: dict[str, Any] = {
    "guidance_text": (
        "Zamknij oczy. Oddychaj spokojnie. "
        "Pozwol ciszy objac twoje serce. "
        "Nie musisz nic mowic -- po prostu badz."
    ),
    "breathing_pattern": {
        "inhale_seconds": 4,
        "hold_seconds": 4,
        "exhale_seconds": 6,
        "cycles": 3,
    },
    "duration_minutes": 2,
    "ambient_suggestion": "silence",
}


class ContemplatioAgent:
    """
    A-013 -- Contemplation guidance agent.

    Produces minimalist, breathing-centred guidance for the silent
    prayer phase. Aims for gentleness and economy of words.
    """

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=0.6)
        logger.info("ContemplatioAgent (A-013) initialised with model=%s.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def contemplate(self, scripture: dict) -> dict:
        """
        Generate minimalist contemplation guidance.

        Args:
            scripture: Dict with book, chapter, verse_start, verse_end, text.

        Returns:
            Dict with: guidance_text, breathing_pattern, duration_minutes,
            ambient_suggestion.
        """
        prompt = CONTEMPLATIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
        )

        try:
            response = await self._llm.ainvoke(prompt)
            contemplation = self._parse_json(response.content)

            # Validate and clamp duration
            duration = contemplation.get("duration_minutes", 2)
            if not isinstance(duration, (int, float)) or duration < 1:
                contemplation["duration_minutes"] = 2
            elif duration > 10:
                contemplation["duration_minutes"] = 5

            # Validate breathing parameters
            contemplation["breathing_pattern"] = self._validate_breathing(
                contemplation.get("breathing_pattern", {})
            )

            # Validate ambient suggestion
            valid_ambient = {"silence", "nature_sounds", "gregorian_chant", "bells"}
            if contemplation.get("ambient_suggestion") not in valid_ambient:
                contemplation["ambient_suggestion"] = "silence"

            # Ensure guidance_text exists
            if not contemplation.get("guidance_text"):
                contemplation["guidance_text"] = FALLBACK_CONTEMPLATION["guidance_text"]

            logger.info(
                "Contemplation generated: duration=%d min, ambient=%s",
                contemplation["duration_minutes"],
                contemplation["ambient_suggestion"],
            )
            return contemplation

        except Exception as exc:
            logger.error("Contemplation generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_CONTEMPLATION)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_breathing(breathing: dict) -> dict:
        """Ensure breathing parameters are physiologically reasonable."""
        return {
            "inhale_seconds": min(
                max(int(breathing.get("inhale_seconds", 4)), 2), 8
            ),
            "hold_seconds": min(
                max(int(breathing.get("hold_seconds", 4)), 0), 7
            ),
            "exhale_seconds": min(
                max(int(breathing.get("exhale_seconds", 6)), 3), 10
            ),
            "cycles": min(
                max(int(breathing.get("cycles", 3)), 1), 10
            ),
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Best-effort JSON extraction from LLM output."""
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse contemplation JSON: %s", exc)
            return dict(FALLBACK_CONTEMPLATION)
