"""
Oratio Agent (A-012)
====================
Generates personalised prayer inspired by the scripture passage,
adapted to the user's emotional state and chosen prayer tradition.

Supported traditions:
  - Ignatian (imaginative, dialogical)
  - Carmelite (contemplative, mystical)
  - Franciscan (joyful, creation-centred)
  - Benedictine (liturgical, psalm-based)
  - Charismatic (spontaneous, Spirit-led)

"Ipse enim Spiritus postulat pro nobis gemitibus inenarrabilibus." -- Rom 8:26
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_creative

logger = logging.getLogger("sancta_nexus.oratio_agent")

# ---------------------------------------------------------------------------
# Tradition-specific system prompts
# ---------------------------------------------------------------------------

TRADITION_PROMPTS: dict[str, str] = {
    "ignatian": """\
Jestes mistrzem modlitwy ignacjanskiej w systemie Sancta Nexus.
Styl: modlitwa dialogiczna z Bogiem, wyobraznia modlitewna,
rozmowa jak przyjaciel z Przyjacielem.
Struktura: compositio loci (wyobrazenie sceny) -> rozważanie -> colloquium (rozmowa koncowa).

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Wygeneruj spersonalizowana modlitwe ignacjanska. Zacznij od wyobrazenia sobie sceny
biblijnej, poprowadz przez rozważanie, zakoncz osobista rozmowa z Bogiem.
Dlugosc: 80-150 slow. Zakoncz "Amen".

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "ignatian",
  "elements": ["compositio_loci", "meditatio", "colloquium"]
}}""",
    "carmelite": """\
Jestes mistrzem modlitwy karmelitanskiej w systemie Sancta Nexus.
Styl: modlitwa mistyczna, intymna bliskosc z Bogiem, cisza wewnetrzna,
tesknota duszy. Inspiracja: sw. Jan od Krzyza, sw. Teresa z Avili.

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Wygeneruj spersonalizowana modlitwe karmelitanska. Skup sie na intymnosci
z Bogiem, tescknocie duszy i wewnetrznej ciszy.
Dlugosc: 80-150 slow. Zakoncz "Amen".

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "carmelite",
  "elements": ["silentium", "unio_mystica", "desiderium"]
}}""",
    "franciscan": """\
Jestes mistrzem modlitwy franciszkanskiej w systemie Sancta Nexus.
Styl: radosc, prostosc, uwielbienie przez stworzenie, braterstwo
z calym stworzeniem. Inspiracja: Piesn Sloneczna sw. Franciszka.

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Wygeneruj spersonalizowana modlitwe franciszkanska. Podkresl radosc,
wdziecznosc za stworzenie i prostosc serca.
Dlugosc: 80-150 slow. Zakoncz "Amen".

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "franciscan",
  "elements": ["laudatio_creaturae", "gaudium", "simplicitas"]
}}""",
    "benedictine": """\
Jestes mistrzem modlitwy benedyktynskiej w systemie Sancta Nexus.
Styl: modlitwa liturgiczna, osadzona w Psalmach, stabilitas i conversatio,
rytm ora et labora.

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Wygeneruj spersonalizowana modlitwe benedyktynska. Uzyj jezyka psalmicznego,
odwolaj sie do rytmu dnia i stabilnosci zycia w Bogu.
Dlugosc: 80-150 slow. Zakoncz "Amen".

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "benedictine",
  "elements": ["psalmodia", "stabilitas", "ora_et_labora"]
}}""",
    "charismatic": """\
Jestes mistrzem modlitwy charyzmatycznej w systemie Sancta Nexus.
Styl: spontaniczna modlitwa uwielbienia, otwartosc na Ducha Swietego,
wolnosc wyrazu, radosc i dziekczynienie.

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Wygeneruj spersonalizowana modlitwe charyzmatyczna. Wyrazi spontaniczna
radosc, uwielbienie i otwartosc na dzialanie Ducha Swietego.
Dlugosc: 80-150 slow. Zakoncz "Amen".

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "charismatic",
  "elements": ["laudatio", "effusio_spiritus", "gratiarum_actio"]
}}""",
}

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

FALLBACK_PRAYER: dict[str, Any] = {
    "prayer_text": (
        "Panie Boze, dziekuje Ci za ten moment ciszy. "
        "Uwielbiam Cie za Twoja wiernosc i milosc. "
        "Prosze, badz blisko mnie w tym, co przezywam. "
        "Wstawiaj sie za tymi, ktorych kocham. "
        "Przez Chrystusa, Pana naszego. Amen."
    ),
    "tradition": "universal",
    "elements": ["laudatio", "gratiarum_actio", "petitio", "intercessio"],
}


class OratioAgent:
    """
    A-012 -- Prayer generation agent.

    Composes personalised prayers that honour the scripture passage,
    the user's emotional landscape, and a chosen prayer tradition.
    """

    VALID_TRADITIONS = frozenset(
        {"ignatian", "carmelite", "franciscan", "benedictine", "charismatic"}
    )

    def __init__(self) -> None:
        try:
            self._llm = get_llm_creative(temperature=0.8, max_tokens=2048)
            logger.info("OratioAgent (A-012) initialised.")
        except Exception as exc:
            logger.warning("OratioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def pray(
        self,
        scripture: dict,
        emotion_state: dict,
        tradition: str = "ignatian",
    ) -> dict:
        """
        Generate a personalised prayer in the chosen tradition.

        Args:
            scripture: Dict with book, chapter, verse_start, verse_end,
                       text, historical_context.
            emotion_state: Dict mapping emotion labels to intensity scores.
            tradition: One of ignatian, carmelite, franciscan, benedictine,
                       charismatic.

        Returns:
            Dict with: prayer_text, tradition, elements.
        """
        if tradition not in self.VALID_TRADITIONS:
            logger.warning(
                "Unknown tradition '%s'; falling back to ignatian.", tradition
            )
            tradition = "ignatian"

        reference = (
            f"{scripture.get('book', '')} "
            f"{scripture.get('chapter', '')}:"
            f"{scripture.get('verse_start', '')}-{scripture.get('verse_end', '')}"
        )

        if self._llm is None:
            return dict(FALLBACK_PRAYER)

        prompt_template = TRADITION_PROMPTS[tradition]
        system_prompt = prompt_template.format(
            reference=reference,
            text=scripture.get("text", ""),
            emotion_state=json.dumps(emotion_state, ensure_ascii=False),
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Wygeneruj spersonalizowana modlitwe."),
            ])
            prayer = self._parse_json(response.content)

            # Validate prayer has actual text
            if len(prayer.get("prayer_text", "")) < 30:
                logger.warning("Prayer too short; using fallback.")
                return dict(FALLBACK_PRAYER)

            prayer.setdefault("tradition", tradition)
            prayer.setdefault("elements", [])

            logger.info(
                "Prayer generated: tradition=%s, length=%d chars",
                prayer["tradition"],
                len(prayer["prayer_text"]),
            )
            return prayer

        except Exception as exc:
            logger.error("Prayer generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_PRAYER)

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
            logger.warning("Could not parse prayer JSON: %s", exc)
            return dict(FALLBACK_PRAYER)
