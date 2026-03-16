"""
Lectio Agent (A-010)
====================
Selects a scripture passage for the Lectio Divina session based on:
  - the user's emotion vector
  - the liturgical calendar
  - past session history (to avoid repetition)

Uses LangChain ChatOpenAI with a Polish-language system prompt for
biblical scholarship and exegesis.

"Lampada pedibus meis verbum tuum." -- Ps 119:105
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger("sancta_nexus.lectio_agent")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

LECTIO_SYSTEM_PROMPT = """\
Jestes biblista i egzegeta w systemie Sancta Nexus.
Twoim zadaniem jest dobranie fragmentu Pisma Swietego, ktory bedzie
najlepiej odpowiadal aktualnemu stanowi duchowemu i emocjonalnemu uzytkownika.

Zasady:
1. Wybieraj fragmenty z calego kanonu Pisma Swietego (ST i NT).
2. Uwzglednij okres liturgiczny: {liturgical_season}.
3. Unikaj powtorzen -- oto fragmenty z ostatnich sesji: {recent_passages}.
4. Dopasuj dlugosc fragmentu (3-8 wersetow) do stanu emocjonalnego.
5. Dla stanow kryzysowych preferuj Psalmy pocieszenia i teksty nadziei.
6. Uwzglednij kontekst historyczny i kulturowy fragmentu.

Wektor emocji uzytkownika:
{emotion_vector}

Kontekst liturgiczny:
{liturgical_context}

Odpowiedz w formacie JSON:
{{
  "book": "Nazwa ksiegi",
  "chapter": <numer rozdzialu>,
  "verse_start": <pierwszy werset>,
  "verse_end": <ostatni werset>,
  "text": "Pelny tekst fragmentu (Biblia Tysiaclecia V)",
  "translation": "BT5",
  "historical_context": "Kontekst historyczny i egzegetyczny fragmentu"
}}
"""

# ---------------------------------------------------------------------------
# Fallback passages -- pre-approved, always safe
# ---------------------------------------------------------------------------

FALLBACK_PASSAGES: list[dict[str, Any]] = [
    {
        "book": "Ewangelia wg sw. Jana",
        "chapter": 14,
        "verse_start": 27,
        "verse_end": 27,
        "text": (
            "Pokoj zostawiam wam, pokoj moj daje wam. "
            "Nie tak jak daje swiat, Ja wam daje. "
            "Niech sie nie trwozy serce wasze ani sie nie leka."
        ),
        "translation": "BT5",
        "historical_context": (
            "Mowa pozegnalna Jezusa podczas Ostatniej Wieczerzy, "
            "ok. 30 r. n.e., Jerozolima. Jezus przygotowuje uczniow "
            "na swoja meke i zmartwychwstanie."
        ),
    },
    {
        "book": "Ksiega Psalmow",
        "chapter": 23,
        "verse_start": 1,
        "verse_end": 4,
        "text": (
            "Pan jest moim pasterzem, nie brak mi niczego. "
            "Pozwala mi lezec na zielonych pastwiskach. "
            "Prowadzi mnie nad wody, gdzie moge odpoczac: "
            "orzezwia moja dusze. Wiedzie mnie po wlasciwych sciezkach "
            "przez wzglad na swoje imie. Chociazbym chodzil ciemna dolina, "
            "zla sie nie ulekne, bo Ty jestes ze mna."
        ),
        "translation": "BT5",
        "historical_context": (
            "Psalm Dawida -- jeden z najstarszych psalmow pocieszenia. "
            "Obraz pasterza byl centralna metafora bliskowschodnia "
            "dla troskliwego wladcy i Boga."
        ),
    },
    {
        "book": "List do Rzymian",
        "chapter": 8,
        "verse_start": 28,
        "verse_end": 31,
        "text": (
            "Wiemy tez, ze Bog z tymi, ktorzy Go miluja, wspoldziala "
            "we wszystkim dla ich dobra, z tymi, ktorzy sa powolani "
            "wedlug Jego zamiaru. Albowiem tych, ktorych od wiekow poznal, "
            "tych tez przeznaczyl na to, by sie stali na wzor obrazu Jego Syna. "
            "Coz wiec na to powiemy? Jezeli Bog z nami, ktoz przeciwko nam?"
        ),
        "translation": "BT5",
        "historical_context": (
            "List do Rzymian, ok. 57 r. n.e. Pawel pisze do wspolnoty "
            "w Rzymie o pewnosci zbawienia i Bozej milosci."
        ),
    },
]


class LectioAgent:
    """
    A-010 -- Scripture selection agent.

    Selects and contextualises a scripture passage using emotion matching,
    liturgical awareness, and historical context enrichment.
    """

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=0.5)
        logger.info("LectioAgent (A-010) initialised with model=%s.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def select_scripture(
        self,
        emotion_vector: dict,
        liturgical_context: dict | None = None,
        user_history: list | None = None,
    ) -> dict:
        """
        Select the best scripture passage for the current session.

        Args:
            emotion_vector: Mapping of emotion labels to intensity scores.
            liturgical_context: Optional dict with liturgical season / feast info.
            user_history: Optional list of past session dicts to avoid repeats.

        Returns:
            Dict with keys: book, chapter, verse_start, verse_end, text,
            translation, historical_context.
        """
        recent_passages = self._extract_recent_passages(user_history or [])
        liturgical_season = self._resolve_liturgical_season(liturgical_context)

        prompt = LECTIO_SYSTEM_PROMPT.format(
            liturgical_season=liturgical_season,
            recent_passages=recent_passages or "(brak)",
            emotion_vector=json.dumps(emotion_vector, ensure_ascii=False),
            liturgical_context=json.dumps(
                liturgical_context or {}, ensure_ascii=False
            ),
        )

        try:
            response = await self._llm.ainvoke(prompt)
            scripture = self._parse_json(response.content)

            # Validate required fields
            required = (
                "book",
                "chapter",
                "verse_start",
                "verse_end",
                "text",
                "translation",
                "historical_context",
            )
            if not all(scripture.get(k) for k in required):
                logger.warning(
                    "Scripture response missing required fields; using fallback."
                )
                return self._get_fallback(emotion_vector)

            logger.info(
                "Scripture selected: %s %s:%s-%s",
                scripture["book"],
                scripture["chapter"],
                scripture["verse_start"],
                scripture["verse_end"],
            )
            return scripture

        except Exception as exc:
            logger.error("Scripture selection failed: %s", exc, exc_info=True)
            return self._get_fallback(emotion_vector)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_fallback(emotion_vector: dict) -> dict:
        """Choose the best fallback passage based on the dominant emotion."""
        dominant = max(emotion_vector, key=emotion_vector.get, default="neutral")
        if dominant in ("sadness", "fear", "smutek", "lek", "anxiety"):
            return dict(FALLBACK_PASSAGES[1])
        if dominant in ("hope", "joy", "nadzieja", "radosc"):
            return dict(FALLBACK_PASSAGES[2])
        return dict(FALLBACK_PASSAGES[0])

    @staticmethod
    def _extract_recent_passages(
        history: list[dict[str, Any]],
        max_recent: int = 10,
    ) -> list[str]:
        """Pull references from the last N sessions to avoid repetition."""
        passages: list[str] = []
        for session in history[-max_recent:]:
            scripture = session.get("scripture") or {}
            book = scripture.get("book", "")
            chapter = scripture.get("chapter", "")
            verse = scripture.get("verse_start", "")
            if book:
                passages.append(f"{book} {chapter}:{verse}")
        return passages

    @staticmethod
    def _resolve_liturgical_season(
        liturgical_context: dict | None,
    ) -> str:
        """Determine the liturgical season from context or by heuristic."""
        if liturgical_context and liturgical_context.get("season"):
            return liturgical_context["season"]

        today = date.today()
        month, day = today.month, today.day

        if (month == 12 and day >= 3) or (month == 1 and day <= 6):
            return "Adwent / Okres Bozego Narodzenia"
        if (month == 2 and day >= 14) or month == 3:
            return "Wielki Post"
        if month == 4 and day <= 20:
            return "Okres Wielkanocny"
        return "Okres Zwykly"

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Best-effort JSON extraction from LLM output."""
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse scripture JSON: %s", exc)
            return {}
