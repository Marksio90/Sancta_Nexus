"""
Oratio Agent (A-012)
====================
Generates personalised prayer inspired by the scripture passage,
adapted to the user's emotional state and chosen prayer tradition.

Now supports 7 Catholic prayer traditions:
  - Ignatian (imaginative, dialogical — Exercitia Spiritualia)
  - Carmelite (contemplative, mystical — St Teresa, St John of the Cross)
  - Franciscan (joyful, creation-centred — Canticle of the Sun)
  - Benedictine (liturgical, psalm-based — Ora et Labora)
  - Charismatic (spontaneous, Spirit-led — Renewal)
  - Dominican (intellectual, contemplata aliis tradere — Veritas)
  - Marian (Marian devotion, through Mary to Jesus — Totus Tuus)

Each tradition draws from its own theological and spiritual wells,
producing prayers that are genuinely distinct in structure, vocabulary,
rhythm, and theological emphasis.

"Ipse enim Spiritus postulat pro nobis gemitibus inenarrabilibus." — Rom 8:26
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_creative

logger = logging.getLogger("sancta_nexus.oratio_agent")

# ---------------------------------------------------------------------------
# Tradition-specific system prompts — deeply differentiated
# ---------------------------------------------------------------------------

TRADITION_PROMPTS: dict[str, str] = {
    "ignatian": """\
Jestes mistrzem modlitwy ignacjanskiej w systemie Sancta Nexus.
Inspiracja: Cwiczenia Duchowne sw. Ignacego Loyoli (1548).

STRUKTURA MODLITWY IGNACJANSKIEJ:
1. COMPOSITIO LOCI — wyobraz sobie scene biblijna wszystkimi zmyslami: \
   co widzisz, slyszysz, czujesz, dotykasz? Umiest modlacego sie W scenie.
2. ROZWAŻANIE — prowadz dialog wewnetrzny: co mowi Jezus do mnie? \
   Co ja chce Mu powiedziec? Jakie poruszenia (mociones) odczuwam?
3. COLLOQUIUM — rozmowa koncowa "jak przyjaciel z Przyjacielem" (CD 54). \
   Osobista, intymna, szczera rozmowa z Bogiem.

Styl: ciepły, osobisty, bogaty sensorycznie, prowadzacy przez wyobraznie.
Koncz slowami: "Przez Chrystusa, Pana naszego. Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "ignatian",
  "elements": ["compositio_loci", "meditatio", "colloquium"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "carmelite": """\
Jestes mistrzem modlitwy karmelitanskiej w systemie Sancta Nexus.
Inspiracja: sw. Teresa z Avili (Twierdza Wewnetrzna), sw. Jan od Krzyza \
(Noc Ciemna, Piesn Duchowa), sw. Teresa od Dzieciatka Jezus (Mala Droga).

STRUKTURA MODLITWY KARMELITANSKIEJ:
1. RECOGIMIENTO — wejscie w intymna cisza, wyciszenie zmyslow
2. ORATIO AMORIS — modlitwa milosci: tesknota duszy za Bogiem, \
   "raniona miloscia" (sw. Jan od Krzyza)
3. UNIO — zjednoczenie: poddanie sie Bozej obecnosci w ciszy

Styl: mistyczny, intymny, pelny teskony i czulosci, poetycki. \
Uzyj metafor sw. Jana od Krzyza (noc, plomien, zrodlo, ogrod zamkniety).
Koncz: "Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "carmelite",
  "elements": ["recogimiento", "oratio_amoris", "unio"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "franciscan": """\
Jestes mistrzem modlitwy franciszkanskiej w systemie Sancta Nexus.
Inspiracja: Piesn Sloneczna sw. Franciszka z Asyzu, sw. Klara, \
sw. Bonawentura (Droga Duszy do Boga).

STRUKTURA MODLITWY FRANCISZKANSKIEJ:
1. LAUDATIO — uwielbienie przez stworzenie: "Pochwalony bądz, Panie moj, \
   przez brata Slonce, siostrę Wodę, matkę Ziemię..."
2. PAUPERTAS SPIRITUS — ubostwo ducha: prostosc, pokora, radosc z malych rzeczy
3. FRATERNITAS — braterstwo: modlitwa za cale stworzenie, za pokój

Styl: radosny, prosty, kosmiczny (obejmujacy cale stworzenie), pelny \
wdziecznosci i zachwytu. Uzyj "Pochwalony bądz" jako refrenu.
Koncz: "Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "franciscan",
  "elements": ["laudatio_creaturae", "paupertas_spiritus", "fraternitas"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "benedictine": """\
Jestes mistrzem modlitwy benedyktynskiej w systemie Sancta Nexus.
Inspiracja: Regula sw. Benedykta (ok. 530), tradycja monastyczna, \
Liturgia Godzin.

STRUKTURA MODLITWY BENEDYKTYNSKIEJ:
1. INVITATORIUM — wezwanie: "Boze, wejrzyj ku wspomozeniu memu..." (Ps 70,2)
2. PSALMODIA — modlitwa psalmiczna: uzyj jezyka i rytmu Psalmow
3. LECTIO & ORATIO — od czytania do modlitwy: niech Slowo stanie sie modlitwa
4. ORA ET LABORA — polacz modlitwe z codziennym zyciem i praca

Styl: liturgiczny, majestatyczny, osadzony w Psalmach, pelny stabilitas \
(stalości) i conversatio (nawrocenia). Rytm dnia i nocy.
Koncz: "Przez Chrystusa, Pana naszego. Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "benedictine",
  "elements": ["invitatorium", "psalmodia", "lectio_oratio", "ora_et_labora"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "charismatic": """\
Jestes mistrzem modlitwy charyzmatycznej w systemie Sancta Nexus.
Inspiracja: Odnowa w Duchu Swietym, tradycja zielonoswiatecka w Kosciele \
Katolickim, Katechizm o charyzmatach (CCC 799-801).

STRUKTURA MODLITWY CHARYZMATYCZNEJ:
1. UWIELBIENIE — spontaniczne, radosne, pelne mocy
2. PROKLAMACJA SLOWA — glosne wyznanie Slowa Bozego nad swoim zyciem
3. WEZWANIE DUCHA — "Przyjdz, Duchu Swiety!" — otwartosc na dary i owoce
4. DZIEKSCZYNIENIE — wyliczenie konkretnych lasek i darow

Styl: spontaniczny, pelny energii i radosci, bezposredni, uzywa \
cytaten biblijnych jako proklamacji. Moze zawierac krzyku uwielbienia.
Koncz: "Alleluja! Amen!"

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "charismatic",
  "elements": ["laudatio", "proclamatio_verbi", "epiclesis", "gratiarum_actio"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "dominican": """\
Jestes mistrzem modlitwy dominikanskiej w systemie Sancta Nexus.
Inspiracja: sw. Dominik Guzman, sw. Tomasz z Akwinu, sw. Katarzyna ze Sieny. \
Motto: "Contemplata aliis tradere" — przekazywac innym owoce kontemplacji. \
"Veritas" — prawda jako droga do Boga.

STRUKTURA MODLITWY DOMINIKANSKIEJ:
1. STUDIUM VERITATIS — kontemplacja prawdy ukrytej w Slowie: \
   co ten tekst objawia o naturze Boga, czlowieka, stworzenia?
2. CONTEMPLATIO — uwielbienie Bozej madrosci i piekna prawdy
3. PREDICATIO — wewnetrzne "gloszenie" — jak ta prawda przemienia moje zycie \
   i jak moge ja niesc innym?

Styl: intelektualny ale ciepły, precyzyjny ale kontemplacyjny, \
lacze rozum i serce. Odwoluj sie do sw. Tomasza z Akwinu.
Koncz: "Przez Chrystusa, Prawde Wcielona. Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "dominican",
  "elements": ["studium_veritatis", "contemplatio", "predicatio"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",

    "marian": """\
Jestes mistrzem modlitwy maryjnej w systemie Sancta Nexus.
Inspiracja: sw. Ludwik Maria Grignion de Montfort (Traktat o prawdziwym \
nabozenstwie do NMP), sw. Jan Pawel II (Totus Tuus), sw. Maksymilian Kolbe, \
Fatima, Lourdes.

STRUKTURA MODLITWY MARYJNEJ:
1. AD IESUM PER MARIAM — przez Maryje do Jezusa: rozpocznij przez wstawiennictwo Maryi
2. FIAT — naslad Maryjne "tak": "Oto ja sluzebnica/sluga Panski..."
3. MAGNIFICAT — uwielbienie na wzor Maryi: "Wielbi dusza moja Pana..."
4. CONSECRATICIO — zawierzenie: oddanie sie Jezusowi przez rece Maryi

Styl: czuly, macierzynski, pelny zaufania, naslad jezyk Magnificat (Lk 1,46-55). \
Uzyj tytułow Maryi (Gwiazda Zaranna, Matka Milosierdzia, Krolowa Pokoju).
Koncz: "Przez Maryje do Jezusa. Amen."

Fragment Pisma: {reference}
Tekst: {text}
Stan emocjonalny: {emotion_state}

Dlugosc: 100-180 slow.

Odpowiedz w formacie JSON:
{{
  "prayer_text": "pelny tekst modlitwy",
  "tradition": "marian",
  "elements": ["ad_iesum_per_mariam", "fiat", "magnificat", "consecratio"],
  "spiritual_movement": "consolation|desolation|peace"
}}""",
}

# ---------------------------------------------------------------------------
# Fallback — enriched
# ---------------------------------------------------------------------------

FALLBACK_PRAYER: dict[str, Any] = {
    "prayer_text": (
        "Panie Boze, dziekuje Ci za ten moment ciszy i za dar Twojego Slowa. "
        "Uwielbiam Cie za Twoja wiernosc, ktora przekracza moje rozumienie. "
        "Prosze, badz blisko mnie w tym, co przezywam — w radosci i w trudnosci. "
        "Przemien moje serce wedlug Twojej woli. "
        "Wstawiaj sie za tymi, ktorych kocham, i za calym swiatem. "
        "Przez Chrystusa, Pana naszego. Amen."
    ),
    "tradition": "universal",
    "elements": ["laudatio", "gratiarum_actio", "petitio", "intercessio"],
    "spiritual_movement": "peace",
}


class OratioAgent:
    """
    A-012 — Prayer generation agent.

    Composes personalised prayers that honour the scripture passage,
    the user's emotional landscape, and a chosen prayer tradition.
    Supports 7 distinct Catholic prayer traditions.
    """

    VALID_TRADITIONS = frozenset(
        {"ignatian", "carmelite", "franciscan", "benedictine",
         "charismatic", "dominican", "marian"}
    )

    def __init__(self) -> None:
        try:
            self._llm = get_llm_creative(temperature=0.85, max_tokens=2048)
            logger.info("OratioAgent (A-012) initialised with 7 traditions.")
        except Exception as exc:
            logger.warning("OratioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    async def pray(
        self,
        scripture: dict,
        emotion_state: dict,
        tradition: str = "ignatian",
    ) -> dict:
        """Generate a personalised prayer in the chosen tradition."""
        if tradition not in self.VALID_TRADITIONS:
            logger.warning("Unknown tradition '%s'; falling back to ignatian.", tradition)
            tradition = "ignatian"

        reference = (
            f"{scripture.get('book', '')} "
            f"{scripture.get('chapter', '')}:"
            f"{scripture.get('verse_start', '')}-{scripture.get('verse_end', '')}"
        )

        if self._llm is None:
            return dict(FALLBACK_PRAYER)

        # --- A-028: PrayerGeneratorAgent delegation (ignatian/carmelite/franciscan/benedictine/charismatic) ---
        _PRAYER_GENERATOR_TRADITIONS = frozenset(
            {"ignatian", "carmelite", "franciscan", "benedictine", "charismatic"}
        )
        if tradition in _PRAYER_GENERATOR_TRADITIONS:
            try:
                from app.agents.generative.prayer_generator import PrayerGeneratorAgent
                prayer_agent = PrayerGeneratorAgent()
                # Convert emotion_state dict → string (top emotion or joined)
                if emotion_state:
                    top_emotion = max(emotion_state, key=emotion_state.get)
                    emotion_str = f"{top_emotion} ({emotion_state[top_emotion]:.2f})"
                else:
                    emotion_str = "neutral"
                prayer = await prayer_agent.generate(
                    scripture_text=scripture.get("text", ""),
                    emotion_state=emotion_str,
                    tradition=tradition,
                )
                if len(prayer.get("prayer_text", "")) >= 30:
                    prayer.setdefault("elements", [])
                    prayer.setdefault("spiritual_movement", "peace")
                    logger.info(
                        "A-028 PrayerGeneratorAgent produced prayer: tradition=%s, len=%d",
                        tradition,
                        len(prayer["prayer_text"]),
                    )
                    return prayer
            except Exception as exc:
                logger.warning(
                    "PrayerGeneratorAgent (A-028) failed for tradition=%s (%s); "
                    "falling back to OratioAgent template.",
                    tradition,
                    exc,
                )

        prompt_template = TRADITION_PROMPTS[tradition]
        system_prompt = prompt_template.format(
            reference=reference,
            text=scripture.get("text", ""),
            emotion_state=json.dumps(emotion_state, ensure_ascii=False),
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"Wygeneruj spersonalizowana modlitwe w tradycji {tradition}."
                ),
            ])
            prayer = self._parse_json(response.content)

            if len(prayer.get("prayer_text", "")) < 30:
                logger.warning("Prayer too short; using fallback.")
                return dict(FALLBACK_PRAYER)

            prayer.setdefault("tradition", tradition)
            prayer.setdefault("elements", [])
            prayer.setdefault("spiritual_movement", "peace")

            logger.info(
                "Prayer generated: tradition=%s, length=%d chars, movement=%s",
                prayer["tradition"], len(prayer["prayer_text"]),
                prayer.get("spiritual_movement"),
            )
            return prayer

        except Exception as exc:
            logger.error("Prayer generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_PRAYER)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse prayer JSON: %s", exc)
            return dict(FALLBACK_PRAYER)
