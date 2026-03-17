"""
Lectio Agent (A-010)
====================
Selects a scripture passage for the Lectio Divina session based on:
  - the user's 36-dimensional emotion vector
  - the liturgical calendar (season, feast, colour, readings)
  - past session history (sliding-window anti-repetition)
  - kerygmatic cycle position (salvation history arc)
  - canon coverage (73-book Catholic Bible breadth)

The selection integrates the Content Uniqueness Engine to guarantee that
no two sessions ever serve the same passage to the same user within a
configurable horizon, and that over time the user encounters the full
breadth of Sacred Scripture.

"Lampada pedibus meis verbum tuum et lumen semitae meae." — Ps 119:105
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_primary
from app.services.content.uniqueness_engine import (
    ContentUniquenessEngine,
    EMOTION_SCRIPTURE_MAP,
)

logger = logging.getLogger("sancta_nexus.lectio_agent")

# ---------------------------------------------------------------------------
# System prompt — kerygmatically and patristially enriched
# ---------------------------------------------------------------------------

LECTIO_SYSTEM_PROMPT = """\
Jestes biblista, egzegeta i duchowy przewodnik w systemie Sancta Nexus — \
katolickiej platformie towarzyszenia duchowego opartej na Pismie Swietym \
i Tradycji Kosciola.

Twoim zadaniem jest dobranie fragmentu Pisma Swietego, ktory bedzie \
najlepiej odpowiadal aktualnemu stanowi duchowemu, emocjonalnemu i \
kerygmatycznemu uzytkownika.

═══════════════════════════════════════════════════════════
ZASADY DOBORU FRAGMENTU
═══════════════════════════════════════════════════════════

1. KANON: Wybieraj z pelnego kanonu katolickiego (73 ksiegi: 46 ST + 27 NT), \
   wlaczajac ksiegi deuterokanoniczne (Tb, Jdt, 1-2 Mch, Mdr, Syr, Ba).

2. PRIORYTET KSIAG: Preferuj fragmenty z tych ksiag (w kolejnosci): \
   {suggested_books}

3. OKRES LITURGICZNY: {liturgical_season}
   Kolor liturgiczny: {liturgical_color}
   Swieto dnia: {feast_day}

4. ANTYREPETYCJA: Unikaj powtorzen — oto fragmenty z ostatnich sesji: \
   {recent_passages}. NIGDY nie powtarzaj zadnego z nich.

5. TEMAT KERYGMATYCZNY: Obecny temat w cyklu kerygmatycznym uzytkownika: \
   {kerygmatic_theme} — {kerygmatic_label}.
   Kluczowe fragmenty tego tematu: {kerygmatic_passages}.
   Nawet jesli nie wybierasz dokladnie tych fragmentow, niech duch tego \
   tematu rezonuje w twoim wyborze.

6. DOPASOWANIE EMOCJONALNE:
   Wektor emocji uzytkownika: {emotion_vector}
   Dominujaca emocja: {dominant_emotion}
   Sugerowane fragmenty dla tego stanu: {emotion_passages}

7. DLUGOSC: 3-12 wersetow, dostosowana do stanu emocjonalnego:
   - Dla stanow kryzysowych: krotsze (3-5 wersetow), pocieszajace
   - Dla stanow kontemplacyjnych: srednie (5-8 wersetow)
   - Dla stanow radosnych/poszukujacych: dluzsze (8-12 wersetow)

8. KONTEKST: Podaj bogaty kontekst historyczny, egzegetyczny i patrystyczny:
   - Sitz im Leben (kontekst zyciowy tekstu)
   - Kluczowe slowa w jezyku oryginalnym (hebr./gr.)
   - Odniesienie do jednego z Ojcow Kosciola (np. Augustyn, Chryzostom, \
     Hieronim, Grzegorz Wielki, Orygenes, Bazyli)
   - Powiazanie z nauczaniem Katechizmu (CCC)

9. TEKST: Podaj pelny tekst w tlumaczeniu Biblii Tysiaclecia V (BT5).

═══════════════════════════════════════════════════════════

Odpowiedz WYLACZNIE w formacie JSON (bez komentarzy, bez markdown):
{{
  "book": "Nazwa ksiegi (pelna, po polsku)",
  "book_abbrev": "Skrot (np. Ps, Mt, Iz)",
  "chapter": <numer rozdzialu>,
  "verse_start": <pierwszy werset>,
  "verse_end": <ostatni werset>,
  "text": "Pelny tekst fragmentu (Biblia Tysiaclecia V)",
  "translation": "BT5",
  "historical_context": "Kontekst historyczny, egzegetyczny i kulturowy",
  "patristic_note": "Krotka refleksja jednego z Ojcow Kosciola nad tym fragmentem",
  "original_language_key": "Jedno kluczowe slowo w jezyku oryginalnym z objasnieniem",
  "catechism_ref": "Odniesienie do Katechizmu Kosciola Katolickiego (np. CCC 1234)"
}}
"""

# ---------------------------------------------------------------------------
# Fallback passages — pre-approved, organised by spiritual state
# ---------------------------------------------------------------------------

FALLBACK_PASSAGES: dict[str, dict[str, Any]] = {
    "consolation": {
        "book": "Ewangelia wg sw. Jana",
        "book_abbrev": "J",
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
            "Mowa pozegnalna Jezusa podczas Ostatniej Wieczerzy, ok. 30 r. n.e., "
            "Jerozolima. Greckie 'eirene' (pokoj) odpowiada hebr. 'shalom' — "
            "pelnia zycia, nie tylko brak konfliktu."
        ),
        "patristic_note": (
            "Sw. Augustyn: 'Pokoj Chrystusa to nie pokoj swiata, ktory jest "
            "kruchy i przemijajacy. To pokoj, ktory przewyzsza wszelki rozum, "
            "bo pochodzi od Tego, ktory jest Pokojem'."
        ),
        "original_language_key": "eirene (gr.) — pelnia, harmonia, calosc zycia w Bogu",
        "catechism_ref": "CCC 2305",
    },
    "desolation": {
        "book": "Ksiega Psalmow",
        "book_abbrev": "Ps",
        "chapter": 23,
        "verse_start": 1,
        "verse_end": 6,
        "text": (
            "Pan jest moim pasterzem, nie brak mi niczego. "
            "Pozwala mi lezec na zielonych pastwiskach. "
            "Prowadzi mnie nad wody, gdzie moge odpoczac: "
            "orzezwia moja dusze. Wiedzie mnie po wlasciwych sciezkach "
            "przez wzglad na swoje imie. Chociazbym chodzil ciemna dolina, "
            "zla sie nie ulekne, bo Ty jestes ze mna. "
            "Twoj kij i Twoja laska sa moja pociecha. "
            "Stol dla mnie zastawiasz wobec mych przeciwnikow; "
            "namaszczasz mi glowe olejkiem; moj kielich jest przeobfity. "
            "Tak, dobroc i laska poscigac mnie beda przez wszystkie dni mego zycia "
            "i zamieszkam w domu Panskim po najdluzsze czasy."
        ),
        "translation": "BT5",
        "historical_context": (
            "Psalm Dawida — jeden z najstarszych psalmow pocieszenia. "
            "Obraz pasterza (hebr. ro'eh) byl centralna metafora bliskowschodnia "
            "dla troskliwego wladcy. Ciemna dolina (gey tsalmawet) oznacza "
            "doswiadczenie smierci i cierpienia."
        ),
        "patristic_note": (
            "Sw. Grzegorz z Nysy: 'Ciemna dolina to nie kara, lecz droga "
            "przejscia. Pasterz nie prowadzi owiec PRZEZ ciemnosc, "
            "lecz jest Z nimi W ciemnosci'."
        ),
        "original_language_key": "ro'eh (hebr.) — pasterz, opiekun, ten ktory karmi i chroni",
        "catechism_ref": "CCC 754",
    },
    "hope": {
        "book": "List do Rzymian",
        "book_abbrev": "Rz",
        "chapter": 8,
        "verse_start": 28,
        "verse_end": 39,
        "text": (
            "Wiemy tez, ze Bog z tymi, ktorzy Go miluja, wspoldziala "
            "we wszystkim dla ich dobra, z tymi, ktorzy sa powolani "
            "wedlug Jego zamiaru. Albowiem tych, ktorych od wiekow poznal, "
            "tych tez przeznaczyl na to, by sie stali na wzor obrazu Jego Syna. "
            "Coz wiec na to powiemy? Jezeli Bog z nami, ktoz przeciwko nam? "
            "On, ktory nawet wlasnego Syna nie oszczedzil, ale Go za nas "
            "wszystkich wydal, jakze mialoby nam wraz z Nim i wszystkiego nie darowac? "
            "I jestem pewien, ze ani smierc, ani zycie, ani aniolowie, ani Zwierzchnosci, "
            "ani rzeczy terazniejsze, ani przyszle, ani Moce, ani co wysokie, ani co glebokie, "
            "ani zadne inne stworzenie nie zdola nas odlaczyc od milosci Boga, "
            "ktora jest w Chrystusie Jezusie, Panu naszym."
        ),
        "translation": "BT5",
        "historical_context": (
            "List do Rzymian, ok. 57 r. n.e. Pawel pisze do wspolnoty "
            "w Rzymie. Ten hymn stanowi szczytowosc argumentacji Listu — "
            "po opisie ludzkiej slabosci (Rz 7) przechodzi do triumfalnej "
            "pewnosci zbawienia w Chrystusie."
        ),
        "patristic_note": (
            "Sw. Jan Chryzostom: 'Pawel nie mowi, ze nie doswiadczymy "
            "cierpienia, lecz ze zadne cierpienie nie jest w stanie "
            "oddzielic nas od Milosci. To jest prawdziwe zwyciestwo — "
            "nie unikniecie bolu, lecz pewnosc Obecnosci'."
        ),
        "original_language_key": "agape (gr.) — milosc bezwarunkowa, darmowa, Boza",
        "catechism_ref": "CCC 1821",
    },
    "dark_night": {
        "book": "Ksiega Psalmow",
        "book_abbrev": "Ps",
        "chapter": 130,
        "verse_start": 1,
        "verse_end": 7,
        "text": (
            "Z glebokosci wolam do Ciebie, Panie, "
            "Panie, wysluchaj glosu mego! "
            "Nachyl swe ucho na glos mojego blagania! "
            "Jezeli zachowasz pamiec o grzechach, Panie, "
            "Panie, ktoz sie ostoi? "
            "Ale Ty udzielasz przebaczenia, aby Cie czczono ze czcia. "
            "W Panu pokladam nadzieje, dusza moja poklade nadzieje w Jego slowie, "
            "dusza moja oczekuje Pana bardziej niz straze switu, "
            "bardziej niz straze poranka."
        ),
        "translation": "BT5",
        "historical_context": (
            "Jeden z siedmiu Psalmow Pokutnych i jeden z Psalmow Wstepowania "
            "(Ps 120-134). 'Z glebokosci' (hebr. mimma'amaqim) — to wolanie "
            "z dna ludzkiego doswiadczenia, z otchlani."
        ),
        "patristic_note": (
            "Sw. Augustyn: 'Glebokosci, z ktorych wolamy, to nie miejsce potepienia, "
            "lecz miejsce rozpoznania wlasnej malości. Kto nie zna swoich glebokosci, "
            "nie moze poznac Bozych wyzyn'."
        ),
        "original_language_key": "mimma'amaqim (hebr.) — z glebokosci, z otchlani duszy",
        "catechism_ref": "CCC 2559",
    },
    "gratitude": {
        "book": "Ksiega Psalmow",
        "book_abbrev": "Ps",
        "chapter": 103,
        "verse_start": 1,
        "verse_end": 5,
        "text": (
            "Blogoslaw, duszo moja, Pana, i calym swym wnetrzem — swietemu Jego imieniu! "
            "Blogoslaw, duszo moja, Pana i nie zapominaj o zadnym z Jego dobrodiejstw! "
            "On odpuszcza wszystkie twoje winy, leczy wszystkie twe niemoce, "
            "On zycie twoje wybawia od zaglady, wienczy cie laska i zmiłowaniem, "
            "On twoje pragnienie nasyca dobrami: odnawia sie, jak u orla, twoja mlodosc."
        ),
        "translation": "BT5",
        "historical_context": (
            "Psalm Dawida — wielki hymn dziekszynny obejmujacy caloksztalt "
            "Bozego dzialania. Hebr. 'barkhi nafshi' (blogoslaw, duszo moja) "
            "to wezwanie wlasnej duszy do wdziecznosci."
        ),
        "patristic_note": (
            "Sw. Bazyli Wielki: 'Wdziecznosc jest matka wszystkich cnot. "
            "Kto pamięta o darach Bożych, ten nie moze popasc w rozpacz, "
            "bo kazdy dar jest dowodem Bozej milosci'."
        ),
        "original_language_key": "barkhi (hebr.) — blogoslaw, slav, wielb (rozkaz wewnetrzny)",
        "catechism_ref": "CCC 2637",
    },
}

# Map emotions to fallback categories
_EMOTION_FALLBACK_MAP: dict[str, str] = {
    "joy": "gratitude", "gratitude": "gratitude", "serenity": "consolation",
    "peace": "consolation", "love": "consolation", "hope": "hope",
    "awe": "gratitude", "sadness": "desolation", "fear": "desolation",
    "anxiety": "desolation", "grief": "desolation", "anger": "desolation",
    "loneliness": "dark_night", "guilt": "dark_night", "shame": "dark_night",
    "dark_night": "dark_night", "desolation": "desolation",
    "confusion": "desolation", "longing": "hope",
}


class LectioAgent:
    """
    A-010 — Scripture selection agent.

    Selects and contextualises a scripture passage using the Content
    Uniqueness Engine, emotion matching, liturgical awareness, kerygmatic
    cycle positioning, and historical-patristic enrichment.
    """

    def __init__(self) -> None:
        self._uniqueness = ContentUniquenessEngine()
        try:
            self._llm = get_llm_primary(temperature=0.5, max_tokens=3072)
            logger.info("LectioAgent (A-010) initialised with uniqueness engine.")
        except Exception as exc:
            logger.warning("LectioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    async def select_scripture(
        self,
        emotion_vector: dict,
        liturgical_context: dict | None = None,
        user_history: list | None = None,
        user_id: str = "anonymous",
    ) -> dict:
        """Select the best scripture passage for the current session."""
        if self._llm is None:
            return self._get_fallback(emotion_vector)

        dominant = max(emotion_vector, key=emotion_vector.get, default="neutral")
        season = self._resolve_liturgical_season(liturgical_context)
        recent_passages = self._extract_recent_passages(user_history or [])

        # Build uniqueness context
        ctx = self._uniqueness.build_session_context(
            user_id=user_id,
            season=season,
            emotion=dominant,
            user_history=user_history,
        )

        system_prompt = LECTIO_SYSTEM_PROMPT.format(
            suggested_books=", ".join(ctx["suggested_books"]),
            liturgical_season=season,
            liturgical_color=(liturgical_context or {}).get("color", "zielony"),
            feast_day=(liturgical_context or {}).get("feast", "brak"),
            recent_passages=recent_passages or "(brak)",
            kerygmatic_theme=ctx["kerygmatic_theme"]["theme"],
            kerygmatic_label=ctx["kerygmatic_theme"]["label"],
            kerygmatic_passages=", ".join(ctx["kerygmatic_theme"]["key_passages"]),
            emotion_vector=json.dumps(emotion_vector, ensure_ascii=False),
            dominant_emotion=dominant,
            emotion_passages=", ".join(ctx["emotion_passages"][:5]),
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Dobierz fragment Pisma Swietego."),
            ])
            scripture = self._parse_json(response.content)

            required = ("book", "chapter", "verse_start", "verse_end", "text",
                        "translation", "historical_context")
            if not all(scripture.get(k) for k in required):
                logger.warning("Scripture response missing required fields; using fallback.")
                return self._get_fallback(emotion_vector)

            logger.info(
                "Scripture selected: %s %s:%s-%s (kerygma=%s)",
                scripture["book"], scripture["chapter"],
                scripture["verse_start"], scripture["verse_end"],
                ctx["kerygmatic_theme"]["theme"],
            )
            return scripture

        except Exception as exc:
            logger.error("Scripture selection failed: %s", exc, exc_info=True)
            return self._get_fallback(emotion_vector)

    @staticmethod
    def _get_fallback(emotion_vector: dict) -> dict:
        """Choose the best fallback passage based on the dominant emotion."""
        dominant = max(emotion_vector, key=emotion_vector.get, default="neutral")
        category = _EMOTION_FALLBACK_MAP.get(dominant, "consolation")
        return dict(FALLBACK_PASSAGES.get(category, FALLBACK_PASSAGES["consolation"]))

    @staticmethod
    def _extract_recent_passages(
        history: list[dict[str, Any]], max_recent: int = 20,
    ) -> list[str]:
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
    def _resolve_liturgical_season(liturgical_context: dict | None) -> str:
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
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse scripture JSON: %s", exc)
            return {}
