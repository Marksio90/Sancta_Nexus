"""
PrayerGeneratorAgent (A-028)
Generates prayers rooted in specific Catholic spiritual traditions.
Each tradition carries its own theological emphasis, style, and structure.

Uses ChatOpenAI (langchain_openai) as the underlying LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# ── Tradition-specific system prompts ─────────────────────────────────────────

TRADITION_PROMPTS: dict[str, str] = {
    "ignatian": (
        "Jesteś przewodnikiem modlitwy w tradycji ignacjańskiej. "
        "Twórz modlitwy oparte na metodzie św. Ignacego Loyoli: "
        "compositio loci (wyobrażenie miejsca), rozmowa z Chrystusem, "
        "zastosowanie zmysłów, colloquium (rozmowa serdeczna). "
        "Modlitwa powinna prowadzić do konkretnego postanowienia (propositum). "
        "Uwzględniaj poruszenia duchowe: pocieszenie i strapienie. "
        "Styl: osobisty, dialogiczny, prowadzący do intymnej rozmowy z Bogiem. "
        "Struktura: przygotowanie -> prośba o łaskę -> rozważanie -> colloquium -> postanowienie."
    ),
    "carmelite": (
        "Jesteś przewodnikiem modlitwy w tradycji karmelitańskiej. "
        "Twórz modlitwy inspirowane nauczaniem św. Jana od Krzyża i św. Teresy z Avili. "
        "Podkreślaj drogę wewnętrzną: oczyszczenie -> oświecenie -> zjednoczenie. "
        "Używaj metafor zamku wewnętrznego, nocy ciemnej, żywego płomienia miłości. "
        "Modlitwa powinna prowadzić do ciszy kontemplacyjnej i ogołocenia. "
        "Styl: mistyczny, poetycki, pełen tęsknoty za Umiłowanym. "
        "Struktura: wyciszenie -> ogołocenie -> spotkanie w ciszy -> zanurzenie w miłości."
    ),
    "franciscan": (
        "Jesteś przewodnikiem modlitwy w tradycji franciszkańskiej. "
        "Twórz modlitwy inspirowane duchowością św. Franciszka z Asyżu. "
        "Podkreślaj braterstwo ze stworzeniem, radość ubóstwa, miłość do Chrystusa Ukrzyżowanego. "
        "Włączaj elementy Pieśni Słonecznej, uwielbienie przez stworzenie. "
        "Styl: radosny, prosty, pełen zachwytu nad pięknem Bożego dzieła. "
        "Struktura: uwielbienie Stwórcy -> braterstwo ze stworzeniami -> "
        "kontemplacja ran Chrystusa -> pokój i radość -> posłanie."
    ),
    "benedictine": (
        "Jesteś przewodnikiem modlitwy w tradycji benedyktyńskiej. "
        "Twórz modlitwy w duchu Reguły św. Benedykta: Ora et Labora. "
        "Opieraj się na Liturgii Godzin, lectio divina i stabilitas loci. "
        "Podkreślaj słuchanie (ausculta), posłuszeństwo Słowu i wspólnotę. "
        "Styl: uporządkowany, liturgiczny, oparty na Psalmach i Piśmie Świętym. "
        "Struktura: invitatorium -> psalm -> lectio -> meditatio -> oratio -> contemplatio."
    ),
    "charismatic": (
        "Jesteś przewodnikiem modlitwy w tradycji charyzmatycznej. "
        "Twórz modlitwy pełne spontanicznego uwielbienia i otwartości na Ducha Świętego. "
        "Podkreślaj charyzmaty: języki, proroctwo, uzdrowienie, słowo wiedzy. "
        "Modlitwa powinna być żywa, dynamiczna, pełna wiary w bezpośrednie działanie Boga. "
        "Styl: ekspresyjny, osobisty, pełen ognia i entuzjazmu wiary. "
        "Struktura: uwielbienie -> adoracja -> otwarcie na Ducha -> wstawiennictwo -> "
        "proklamacja Słowa -> dziękczynienie."
    ),
}

# ── Default prayer elements per tradition ─────────────────────────────────────

_TRADITION_ELEMENTS: dict[str, list[str]] = {
    "ignatian": ["compositio_loci", "colloquium", "petitio", "propositum"],
    "carmelite": ["silentium", "contemplatio", "unio", "adoratio"],
    "franciscan": ["laudatio", "fraternitas", "gaudium", "missio"],
    "benedictine": ["psalmus", "lectio", "oratio", "stabilitas"],
    "charismatic": ["laudatio", "adoratio", "intercessio", "proclamatio"],
}

# ── Fallback ──────────────────────────────────────────────────────────────────

_FALLBACK_PRAYER: dict[str, Any] = {
    "prayer_text": (
        "Panie Boże, dziękuję Ci za ten moment ciszy. "
        "Uwielbiam Cię za Twoją wierność i miłość. "
        "Proszę, bądź blisko mnie w tym, co przeżywam. "
        "Wstawiaj się za tymi, których kocham. "
        "Przez Chrystusa, Pana naszego. Amen."
    ),
    "tradition": "ignatian",
    "elements": ["laudatio", "gratiarum_actio", "petitio", "intercessio"],
}


class PrayerGeneratorAgent:
    """
    Agent A-028 — Generates prayers grounded in Catholic spiritual traditions.

    Each generated prayer is shaped by the selected tradition's theological
    and stylistic character, the user's emotional state, the given Scripture
    passage, and an optional personal intention.
    """

    agent_id: str = "A-028"
    agent_name: str = "PrayerGeneratorAgent"

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.8,
    ) -> None:
        self._llm = ChatOpenAI(model=model_name, temperature=temperature)
        logger.info("PrayerGeneratorAgent (A-028) initialised with model=%s", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        scripture_text: str,
        emotion_state: str,
        tradition: str = "ignatian",
        intention: str | None = None,
    ) -> dict:
        """Generate a prayer tailored to the given context and tradition.

        Args:
            scripture_text: The Scripture passage text to base the prayer on.
            emotion_state: Description of the user's current emotional /
                spiritual state (e.g. ``"sorrow"``, ``"joy"``).
            tradition: One of ``ignatian``, ``carmelite``, ``franciscan``,
                ``benedictine``, ``charismatic``.
            intention: Optional personal prayer intention.

        Returns:
            A dict with keys ``prayer_text``, ``tradition``, and ``elements``.
        """
        tradition_key = tradition if tradition in TRADITION_PROMPTS else "ignatian"

        logger.info(
            "Generating %s prayer | emotion=%s | intention=%s",
            tradition_key,
            emotion_state,
            intention[:60] if intention else None,
        )

        system_prompt = self._build_system_prompt(tradition_key, emotion_state)
        user_prompt = self._build_user_prompt(scripture_text, emotion_state, intention)

        try:
            response = await self._llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            parsed = self._parse_response(response.content, tradition_key)

            if len(parsed.get("prayer_text", "")) < 30:
                logger.warning("Prayer too short; returning fallback.")
                return {**_FALLBACK_PRAYER, "tradition": tradition_key}

            return parsed

        except Exception:
            logger.exception("Prayer generation failed; returning fallback.")
            return {**_FALLBACK_PRAYER, "tradition": tradition_key}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(tradition: str, emotion_state: str) -> str:
        base = TRADITION_PROMPTS[tradition]
        return (
            f"{base}\n\n"
            f"Stan emocjonalny osoby modlącej się: {emotion_state}\n"
            "Generuj modlitwę w języku polskim. "
            "Modlitwa powinna być autentyczna, głęboka teologicznie i duchowo.\n\n"
            "Odpowiedz w formacie JSON:\n"
            '{"prayer_text": "...", "tradition": "...", "elements": ["..."]}'
        )

    @staticmethod
    def _build_user_prompt(
        scripture_text: str,
        emotion_state: str,
        intention: str | None,
    ) -> str:
        parts = [f"Fragment Pisma Świętego:\n{scripture_text}"]
        if intention:
            parts.append(f"Intencja modlitwy: {intention}")
        parts.append(
            "Wygeneruj modlitwę uwzględniając powyższy kontekst. "
            "Modlitwa powinna zawierać elementy uwielbienia, dziękczynienia, "
            "prośby i wstawiennictwa, stosownie do wybranej tradycji."
        )
        return "\n\n".join(parts)

    @staticmethod
    def _parse_response(raw: str, tradition: str) -> dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            data = json.loads(raw[start:end])
            return {
                "prayer_text": data.get("prayer_text", data.get("text", "")),
                "tradition": data.get("tradition", tradition),
                "elements": data.get("elements", _TRADITION_ELEMENTS.get(tradition, [])),
            }
        except (ValueError, json.JSONDecodeError):
            logger.warning("Could not parse prayer JSON; returning raw text.")
            return {
                "prayer_text": raw.strip(),
                "tradition": tradition,
                "elements": _TRADITION_ELEMENTS.get(tradition, []),
            }
