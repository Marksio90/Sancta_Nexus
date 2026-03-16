"""
Actio Agent (A-014)
===================
Generates a concrete daily challenge / micro-quest that connects
the scripture reflection to the user's everyday life.

The challenge should be:
  - Specific and achievable within 24 hours
  - Rooted in the scripture passage just meditated upon
  - Practical, not abstract
  - Accompanied by an evening check-in prompt

"Estote factores verbi et non auditores tantum." -- Jas 1:22
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger("sancta_nexus.actio_agent")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

ACTIO_SYSTEM_PROMPT = """\
Jestes przewodnikiem duchowym w systemie Sancta Nexus, specjalizujacym sie
w przekladaniu rozwaznan biblijnych na konkretne dzialania.

Fragment Pisma: {book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}

Refleksja medytacyjna:
{reflection}

Wygeneruj JEDNO konkretne wyzwanie dnia (micro-quest), ktore:
1. Jest wykonalne w ciagu najblizszych 24 godzin
2. Bezposrednio laczy sie z przeslaniem fragmentu Pisma
3. Zawiera konkretny, mierzalny element (np. "porozmawiaj z jedna osoba",
   "poswiec 5 minut na...", "zapisz trzy rzeczy...")

Dodaj tez:
- Poziom trudnosci (easy / medium / hard)
- Kategorie dzialania
- Pytanie na wieczorny rachunek sumienia

Odpowiedz w formacie JSON:
{{
  "challenge_text": "Tresc wyzwania (max 50 slow)",
  "difficulty": "easy|medium|hard",
  "category": "prayer|charity|relationship|self_care|service|gratitude|forgiveness",
  "evening_checkin_prompt": "Pytanie do wieczornej refleksji nad wyzwaniem"
}}
"""

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

FALLBACK_ACTION: dict[str, Any] = {
    "challenge_text": (
        "Dzis poswiec 5 minut na cisze i zapisz jedna rzecz, "
        "za ktora jestes wdzieczny/wdzieczna Bogu."
    ),
    "difficulty": "easy",
    "category": "gratitude",
    "evening_checkin_prompt": (
        "Czy udalo ci sie dzis zatrzymac na chwile ciszy? "
        "Co zapisales/zapisalas jako powod do wdziecznosci?"
    ),
}


class ActioAgent:
    """
    A-014 -- Action / micro-quest generation agent.

    Bridges contemplation and daily life by proposing a single,
    achievable spiritual challenge rooted in the day's scripture,
    along with an evening check-in prompt.
    """

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=0.7)
        logger.info("ActioAgent (A-014) initialised with model=%s.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def challenge(
        self,
        scripture: dict,
        reflection: dict,
    ) -> dict:
        """
        Generate a daily micro-quest linked to the scripture reflection.

        Args:
            scripture: Dict with book, chapter, verse_start, verse_end, text.
            reflection: Dict with questions and reflection_layers from
                        MeditatioAgent.

        Returns:
            Dict with: challenge_text, difficulty (easy/medium/hard),
            category, evening_checkin_prompt.
        """
        # Flatten reflection into a readable string for the prompt
        reflection_text = self._format_reflection(reflection)

        prompt = ACTIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
            reflection=reflection_text,
        )

        try:
            response = await self._llm.ainvoke(prompt)
            action = self._parse_json(response.content)

            # Validate required fields
            if not action.get("challenge_text"):
                logger.warning("Challenge text missing; using fallback.")
                return dict(FALLBACK_ACTION)

            # Normalise difficulty
            valid_difficulties = {"easy", "medium", "hard"}
            if action.get("difficulty") not in valid_difficulties:
                action["difficulty"] = "easy"

            # Ensure evening check-in prompt exists
            if not action.get("evening_checkin_prompt"):
                action["evening_checkin_prompt"] = (
                    "Jak uplynql twoj dzien w swietle dzisiejszego wyzwania?"
                )

            logger.info(
                "Action generated: category=%s, difficulty=%s",
                action.get("category"),
                action.get("difficulty"),
            )
            return action

        except Exception as exc:
            logger.error("Action generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_ACTION)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_reflection(reflection: dict) -> str:
        """Convert reflection dict into a readable string for the prompt."""
        parts: list[str] = []

        questions = reflection.get("questions", [])
        if questions:
            parts.append("Pytania refleksyjne:")
            for i, q in enumerate(questions, 1):
                q_text = q if isinstance(q, str) else q.get("text", str(q))
                parts.append(f"  {i}. {q_text}")

        layers = reflection.get("reflection_layers", {})
        if layers:
            parts.append("\nWarstwy refleksji:")
            for layer_name, layer_text in layers.items():
                parts.append(f"  {layer_name}: {layer_text}")

        return "\n".join(parts) if parts else "brak refleksji"

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Best-effort JSON extraction from LLM output."""
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse action JSON: %s", exc)
            return dict(FALLBACK_ACTION)
