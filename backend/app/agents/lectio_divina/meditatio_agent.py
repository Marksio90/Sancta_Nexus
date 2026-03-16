"""
Meditatio Agent (A-011)
=======================
Generates personalised reflective questions and multi-layered meditation
from the selected scripture passage.

Analysis layers:
  1. Exegetical  -- what does the text say in its original context?
  2. Existential -- what does it mean for my life right now?
  3. Mystical    -- what does God whisper through this text?
  4. Practical   -- what concrete change does it invite?

"Maria autem conservabat omnia verba haec, conferens in corde suo." -- Lk 2:19
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger("sancta_nexus.meditatio_agent")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

MEDITATIO_SYSTEM_PROMPT = """\
Jestes mistrzem medytacji chrzescijanskiej w tradycji Lectio Divina.
Na podstawie podanego fragmentu Pisma Swietego wygeneruj gleboka,
spersonalizowana refleksje wielowarstwowa.

Fragment: {book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}
Kontekst historyczny: {historical_context}

Kontekst uzytkownika: {user_context}

Zastosuj analize wielowarstwowa:

WARSTWA EGZEGETYCZNA -- Co tekst mowi w swoim oryginalnym kontekscie?
WARSTWA EGZYSTENCJALNA -- Co to znaczy dla mojego obecnego zycia?
WARSTWA MISTYCZNA -- Co Bog szepcze przez ten tekst do mojego serca?
WARSTWA PRAKTYCZNA -- Do jakiej konkretnej zmiany zaprasza mnie ten fragment?

Zasady:
- Pytania powinny byc osobiste (w drugiej osobie)
- Unikaj pytan zamknietych (tak/nie)
- Dopasuj glebokosc do kontekstu uzytkownika
- Kazde pytanie powinno pochodzic z innej warstwy analizy
- Wygeneruj 2-3 pytan refleksyjnych

Odpowiedz w formacie JSON:
{{
  "questions": [
    "pytanie refleksyjne 1",
    "pytanie refleksyjne 2",
    "pytanie refleksyjne 3"
  ],
  "reflection_layers": {{
    "exegetical": "Refleksja egzegetyczna -- co tekst mowi w oryginale",
    "existential": "Refleksja egzystencjalna -- co to znaczy dla mojego zycia",
    "mystical": "Refleksja mistyczna -- co Bog szepcze",
    "practical": "Refleksja praktyczna -- do czego zaprasza"
  }}
}}
"""

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

FALLBACK_MEDITATION: dict[str, Any] = {
    "questions": [
        "Ktore slowo z tego fragmentu najbardziej przyciaga twoja uwage?",
        "Gdybys mogl/mogla usiasc obok autora tych slow, co chcialbys/chcialabys mu powiedziec?",
        "Co Bog chce ci dzis przez ten tekst powiedziec?",
    ],
    "reflection_layers": {
        "exegetical": (
            "Ten fragment zostal napisany w konkretnym kontekscie historycznym. "
            "Zastanow sie, jakie znaczenie mialy te slowa dla pierwszych odbiorcow."
        ),
        "existential": (
            "Pomysl, w jaki sposob te slowa odnosza sie do tego, "
            "co teraz przezywasz w swoim zyciu."
        ),
        "mystical": (
            "Pozwol, by cisza wypelnila twoje serce. "
            "Bog moze mowic przez jedno slowo, ktore cie poruszyla."
        ),
        "practical": (
            "Czy jest cos konkretnego, do czego zaprasza cie ten fragment dzisiaj?"
        ),
    },
}


class MeditatioAgent:
    """
    A-011 -- Meditation / reflection agent.

    Produces personalised reflective questions and multi-layered scriptural
    analysis (exegetical, existential, mystical, practical).
    """

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=0.7)
        logger.info("MeditatioAgent (A-011) initialised with model=%s.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def meditate(
        self,
        scripture: dict,
        user_context: dict | None = None,
    ) -> dict:
        """
        Generate reflective questions and multi-layered meditation.

        Args:
            scripture: Dict with book, chapter, verse_start, verse_end,
                       text, translation, historical_context.
            user_context: Optional dict with user emotional/spiritual state.

        Returns:
            Dict with:
              - questions: list of 2-3 reflective question strings
              - reflection_layers: dict with exegetical, existential,
                mystical, practical reflections
        """
        prompt = MEDITATIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
            historical_context=scripture.get("historical_context", "brak kontekstu"),
            user_context=json.dumps(user_context or {}, ensure_ascii=False),
        )

        try:
            response = await self._llm.ainvoke(prompt)
            meditation = self._parse_json(response.content)

            # Validate questions
            questions = meditation.get("questions", [])
            if not isinstance(questions, list) or len(questions) < 2:
                logger.warning("Too few questions generated; using fallback.")
                return dict(FALLBACK_MEDITATION)

            # Validate reflection_layers
            layers = meditation.get("reflection_layers", {})
            required_layers = ("exegetical", "existential", "mystical", "practical")
            if not all(layers.get(layer) for layer in required_layers):
                logger.warning(
                    "Reflection layers incomplete; filling from fallback."
                )
                fallback_layers = FALLBACK_MEDITATION["reflection_layers"]
                for layer in required_layers:
                    layers.setdefault(layer, fallback_layers[layer])
                meditation["reflection_layers"] = layers

            logger.info(
                "Meditation generated: %d questions, all layers present.",
                len(questions),
            )
            return meditation

        except Exception as exc:
            logger.error("Meditation generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_MEDITATION)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Best-effort JSON extraction from LLM output."""
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse meditation JSON: %s", exc)
            return dict(FALLBACK_MEDITATION)
