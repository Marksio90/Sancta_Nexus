"""
Contemplatio Agent (A-013)
==========================
Generates gentle, minimalist contemplation guidance for the silent-prayer
phase of Lectio Divina. Now enriched with:

  - Hesychast tradition (Jesus Prayer, sacred silence)
  - Sacred Word meditation (Centering Prayer, Thomas Keating)
  - Physiologically-calibrated breathing patterns
  - Ambient atmosphere matched to liturgical season
  - Scripture-derived focus word (verbum sacrum)

The guidance intentionally uses few words — contemplatio is about
*resting* in God's presence, not thinking more.

"Vacate et videte quoniam ego sum Deus." — Ps 46:11
"Maranatha." — 1 Cor 16:22
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_creative

logger = logging.getLogger("sancta_nexus.contemplatio_agent")

# ---------------------------------------------------------------------------
# System prompt — enriched with contemplative traditions
# ---------------------------------------------------------------------------

CONTEMPLATIO_SYSTEM_PROMPT = """\
Jestes przewodnikiem kontemplacji chrzescijanskiej w systemie Sancta Nexus, \
uformowanym w tradycji kontemplacyjnej Kosciola: hesychazm, Modlitwa \
Jezusowa, Centering Prayer (Thomas Keating), kontemplacja ignacjanska, \
i mistyka karmelitanska.

═══════════════════════════════════════════════════════════
FRAGMENT PISMA
═══════════════════════════════════════════════════════════

{book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}

═══════════════════════════════════════════════════════════
ZASADY KONTEMPLACJI — FUNDAMENTALNE
═══════════════════════════════════════════════════════════

1. EKONOMIA SLOW: Uzywaj ABSOLUTNIE MINIMALNEJ ilosci slow. \
   Kontemplacja to CISZA, nie wyklad. Maks 50 slow przewodnictwa.
   "W wielomownosci nie unikniesz grzechu" (Prz 10,19).

2. VERBUM SACRUM: Wyodrebnij JEDNO slowo kluczowe z fragmentu, \
   ktore bedzie "kotwica" kontemplacji — slowo, do ktorego modlacy \
   sie wraca, gdy mysli odciagaja. W tradycji Centering Prayer to \
   "sacred word" (slowo swiete).

3. WZORZEC ODDECHOWY: Dostosuj do stanu emocjonalnego:
   - Dla stanow lekowych/niespokojnych: dluzszy wydech (4-4-8)
   - Dla stanow smutku: lagodny, rownomierny (4-4-4)
   - Dla stanow pokoju: poglebiony (5-5-7)
   - Dla stanow radosci: swobodny (4-2-6)

4. ATMOSFERA DZWIEKOWA: Wybierz jedna z opcji:
   - "silence" — pelna cisza (domyslna dla doswiadczonych)
   - "nature_sounds" — dzwieki natury (woda, wiatr, ptaki)
   - "gregorian_chant" — spiew gregorianski (dla okresow liturgicznych)
   - "bells" — dzwony klasztorne (dla poczatku/konca)
   - "taize" — spiwy z Taize (dla wspolnotowych)
   - "jesus_prayer" — tlo do Modlitwy Jezusowej

5. CZAS: 2, 3, 5, 7 lub 10 minut — dostosuj do doswiadczenia.

6. MODLITWA JEZUSOWA: Jesli stosowne, zaproponuj formule:
   "Panie Jezu Chryste, Synu Bozy, zmiluj sie nade mna"
   zsynchronizowana z oddechem.

7. ZAKONCZENIE: Zaproponuj lagodne wyjscie z kontemplacji \
   (Ojcze Nasz, trojkrotne "Amen", lub chwila wdziecznosci).

Odpowiedz w formacie JSON:
{{
  "guidance_text": "Tekst przewodnictwa kontemplacyjnego (max 50 slow)",
  "sacred_word": "Jedno slowo swiete z fragmentu — kotwica kontemplacji",
  "sacred_word_meaning": "Krotkie objasnienie tego slowa (1 zdanie)",
  "breathing_pattern": {{
    "inhale_seconds": 4,
    "hold_seconds": 4,
    "exhale_seconds": 6,
    "cycles": 3
  }},
  "jesus_prayer_rhythm": "Opcjonalnie: 'wdech: Panie Jezu... wydech: zmiluj sie...'",
  "duration_minutes": 3,
  "ambient_suggestion": "silence|nature_sounds|gregorian_chant|bells|taize|jesus_prayer",
  "closing_prayer": "Krotka modlitwa koncowa (1 zdanie)"
}}
"""

# ---------------------------------------------------------------------------
# Fallback — enriched with contemplative depth
# ---------------------------------------------------------------------------

FALLBACK_CONTEMPLATION: dict[str, Any] = {
    "guidance_text": (
        "Zamknij oczy. Oddychaj spokojnie. "
        "Powtarzaj w sercu jedno slowo: 'Pokoj'. "
        "Pozwol ciszy objac twoje serce. "
        "Nie musisz nic mowic — po prostu badz."
    ),
    "sacred_word": "Pokoj",
    "sacred_word_meaning": "Shalom — pelnia zycia i obecnosci Boga",
    "breathing_pattern": {
        "inhale_seconds": 4,
        "hold_seconds": 4,
        "exhale_seconds": 6,
        "cycles": 3,
    },
    "jesus_prayer_rhythm": (
        "Wdech: 'Panie Jezu Chryste, Synu Bozy...' "
        "Wydech: '...zmiluj sie nade mna.'"
    ),
    "duration_minutes": 3,
    "ambient_suggestion": "silence",
    "closing_prayer": "Dziekuje Ci, Panie, za te chwile ciszy. Amen.",
}

# Season -> suggested ambient mapping
_SEASON_AMBIENT: dict[str, str] = {
    "advent": "silence",
    "christmas": "bells",
    "lent": "silence",
    "easter": "gregorian_chant",
    "ordinary": "nature_sounds",
}


class ContemplatioAgent:
    """
    A-013 — Contemplation guidance agent.

    Produces minimalist, breathing-centred guidance enriched with
    Hesychast prayer, sacred word meditation, and liturgically-aware
    ambient atmosphere. Aims for absolute gentleness and economy of words.
    """

    def __init__(self) -> None:
        try:
            self._llm = get_llm_creative(temperature=0.6, max_tokens=1024)
            logger.info("ContemplatioAgent (A-013) initialised.")
        except Exception as exc:
            logger.warning("ContemplatioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    async def contemplate(
        self,
        scripture: dict,
        season: str = "ordinary",
    ) -> dict:
        """Generate minimalist contemplation guidance."""
        if self._llm is None:
            return self._get_seasonal_fallback(season)

        system_prompt = CONTEMPLATIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Przygotuj przewodnictwo kontemplacyjne."),
            ])
            contemplation = self._parse_json(response.content)

            # Validate and clamp duration
            duration = contemplation.get("duration_minutes", 3)
            if not isinstance(duration, (int, float)) or duration < 1:
                contemplation["duration_minutes"] = 3
            elif duration > 10:
                contemplation["duration_minutes"] = 10

            # Validate breathing parameters
            contemplation["breathing_pattern"] = self._validate_breathing(
                contemplation.get("breathing_pattern", {})
            )

            # Validate ambient suggestion
            valid_ambient = {"silence", "nature_sounds", "gregorian_chant",
                             "bells", "taize", "jesus_prayer"}
            if contemplation.get("ambient_suggestion") not in valid_ambient:
                contemplation["ambient_suggestion"] = _SEASON_AMBIENT.get(season, "silence")

            # Ensure all fields
            if not contemplation.get("guidance_text"):
                contemplation["guidance_text"] = FALLBACK_CONTEMPLATION["guidance_text"]
            contemplation.setdefault("sacred_word", "Pokoj")
            contemplation.setdefault("sacred_word_meaning", "")
            contemplation.setdefault("jesus_prayer_rhythm",
                                     FALLBACK_CONTEMPLATION["jesus_prayer_rhythm"])
            contemplation.setdefault("closing_prayer",
                                     FALLBACK_CONTEMPLATION["closing_prayer"])

            logger.info(
                "Contemplation generated: duration=%d min, ambient=%s, word='%s'",
                contemplation["duration_minutes"],
                contemplation["ambient_suggestion"],
                contemplation.get("sacred_word"),
            )
            return contemplation

        except Exception as exc:
            logger.error("Contemplation generation failed: %s", exc, exc_info=True)
            return self._get_seasonal_fallback(season)

    def _get_seasonal_fallback(self, season: str) -> dict:
        """Return fallback with season-appropriate ambient."""
        fallback = dict(FALLBACK_CONTEMPLATION)
        fallback["ambient_suggestion"] = _SEASON_AMBIENT.get(season, "silence")
        return fallback

    @staticmethod
    def _validate_breathing(breathing: dict) -> dict:
        return {
            "inhale_seconds": min(max(int(breathing.get("inhale_seconds", 4)), 2), 8),
            "hold_seconds": min(max(int(breathing.get("hold_seconds", 4)), 0), 7),
            "exhale_seconds": min(max(int(breathing.get("exhale_seconds", 6)), 3), 10),
            "cycles": min(max(int(breathing.get("cycles", 3)), 1), 10),
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse contemplation JSON: %s", exc)
            return dict(FALLBACK_CONTEMPLATION)
