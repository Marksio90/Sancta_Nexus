"""
ConfirmationService — Preparation for the Sacrament of Confirmation (Bierzmowanie).

Implements a 6-session formation program for candidates preparing for
the Sacrament of Confirmation, emphasising:
- Personal ownership of the faith received at Baptism
- The seven gifts of the Holy Spirit
- Choosing a confirmation name and sponsor
- Christian witness in daily life
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ConfirmationSession:
    session_id: str
    number: int
    title: str
    subtitle: str
    holy_spirit_gift: str | None
    scripture: list[str]
    ccc_refs: list[str]
    key_question: str
    personal_challenge: str
    prayer: str


# Seven Gifts of the Holy Spirit
GIFTS_OF_SPIRIT: list[dict] = [
    {
        "gift": "Mądrość",
        "latin": "Sapientia",
        "description": "Zdolność widzenia rzeczy oczami Boga i oceniania spraw w świetle wiary.",
        "opposite_vice": "Głupota duchowa",
        "scripture": "Mdr 7,7-12",
        "ccc": "§§ 1831",
        "fruit": "Miłość",
    },
    {
        "gift": "Rozum",
        "latin": "Intellectus",
        "description": "Głębsze rozumienie prawd wiary, wnikanie w Boże tajemnice.",
        "opposite_vice": "Tępota umysłu",
        "scripture": "Ef 1,17-19",
        "ccc": "§§ 1831",
        "fruit": "Radość",
    },
    {
        "gift": "Rada",
        "latin": "Consilium",
        "description": "Zdolność rozeznawania woli Bożej w konkretnych sytuacjach życia.",
        "opposite_vice": "Pochopność w decyzjach",
        "scripture": "Ps 25,9",
        "ccc": "§§ 1788",
        "fruit": "Pokój",
    },
    {
        "gift": "Męstwo",
        "latin": "Fortitudo",
        "description": "Siła do wyznawania wiary mimo trudności, oporu świata lub lęku.",
        "opposite_vice": "Tchórzostwo",
        "scripture": "2Tm 1,7",
        "ccc": "§§ 1808",
        "fruit": "Cierpliwość",
    },
    {
        "gift": "Umiejętność",
        "latin": "Scientia",
        "description": "Właściwa ocena rzeczy stworzonych i ich użytkowanie zgodne z wolą Bożą.",
        "opposite_vice": "Nierozwaga",
        "scripture": "Kol 2,2-3",
        "ccc": "§§ 1831",
        "fruit": "Łagodność",
    },
    {
        "gift": "Pobożność",
        "latin": "Pietas",
        "description": "Synowska miłość wobec Boga i Kościoła, żarliwość w modlitwie.",
        "opposite_vice": "Oziębłość",
        "scripture": "Rz 8,15",
        "ccc": "§§ 1831",
        "fruit": "Dobroć",
    },
    {
        "gift": "Bojaźń Boża",
        "latin": "Timor Domini",
        "description": "Szacunek wobec Bożej wielkości i lęk przed oddaleniem się od Boga.",
        "opposite_vice": "Pycha",
        "scripture": "Ps 111,10",
        "ccc": "§§ 1831",
        "fruit": "Wierność",
    },
]

CONFIRMATION_SESSIONS: list[ConfirmationSession] = [
    ConfirmationSession(
        session_id="conf_01_baptism",
        number=1,
        title="Mój chrzest — moje korzenie wiary",
        subtitle="Odkrycie łaski chrzcielnej i tożsamości chrześcijańskiej",
        holy_spirit_gift=None,
        scripture=["Rz 6,3-5", "Ga 3,26-27", "1P 2,9"],
        ccc_refs=["§§ 1212-1274", "§§ 1285-1288"],
        key_question="Co wiesz o swoim chrzcie? Jak twoja wiara jest twoja — a nie tylko rodziców?",
        personal_challenge="Porozmawiaj z rodzicami o dniu twojego chrztu. Odnajdź świadectwo chrzcielne.",
        prayer="Ojcze, dziękuję za łaskę chrztu. Pragnę dziś świadomie przyjąć wiarę, którą mi ofiarowałeś.",
    ),
    ConfirmationSession(
        session_id="conf_02_holy_spirit",
        number=2,
        title="Duch Święty — Osoba Boska, nie 'siła'",
        subtitle="Kim jest Duch Święty i jak działa w moim życiu",
        holy_spirit_gift="Mądrość / Rozum",
        scripture=["J 14,16-17", "J 16,13", "Dz 2,1-4"],
        ccc_refs=["§§ 687-741"],
        key_question="Czy doświadczyłeś kiedyś działania Ducha Świętego? Jak to rozpoznać?",
        personal_challenge="Codziennie przez tydzień: 'Duchu Święty, prowadź mnie dziś' — przed wyjściem z domu.",
        prayer="Przyjdź, Duchu Święty. Napełnij serce moje i zapal w nim ogień Twojej miłości.",
    ),
    ConfirmationSession(
        session_id="conf_03_gifts",
        number=3,
        title="Siedem darów Ducha Świętego",
        subtitle="Mądrość, Rozum, Rada, Męstwo, Umiejętność, Pobożność, Bojaźń Boża",
        holy_spirit_gift="Siedem darów",
        scripture=["Iz 11,2-3", "1Kor 12,4-11", "Ga 5,22-23"],
        ccc_refs=["§§ 1830-1832"],
        key_question="Który dar jest ci najbardziej potrzebny? Który czujesz już w sobie?",
        personal_challenge="Przez tydzień obserwuj: który dar Ducha widzisz u rówieśników i w sobie?",
        prayer="Duchu Święty, rozdziel we mnie dary mądrości, rozumu i męstwa — abym był świadkiem Jezusa.",
    ),
    ConfirmationSession(
        session_id="conf_04_witness",
        number=4,
        title="Świadek Chrystusa w świecie",
        subtitle="Bierzmowanie jako misja — żołnierz Chrystusa",
        holy_spirit_gift="Męstwo",
        scripture=["Mt 5,14-16", "1P 3,15-16", "Dz 1,8"],
        ccc_refs=["§§ 897-913"],
        key_question="Czy wstydzisz się wyznawać wiarę wśród rówieśników? Co ci to utrudnia?",
        personal_challenge="Wykonaj jeden konkretny gest wiary w miejscu publicznym (modlitwa przed posiłkiem, krzyżyk w widocznym miejscu).",
        prayer="Panie Jezu, daj mi odwagę, bym był Twoim świadkiem tam, gdzie mnie posyłasz.",
    ),
    ConfirmationSession(
        session_id="conf_05_name_sponsor",
        number=5,
        title="Imię bierzmowania i patron",
        subtitle="Wybór świętego jako patrona i wzoru życia",
        holy_spirit_gift="Rada",
        scripture=["Ap 2,17", "Hbr 12,1-2", "Rz 8,29"],
        ccc_refs=["§§ 2156-2159", "§§ 2692-2694"],
        key_question="Dlaczego wybrałeś takie imię? Co wiesz o tym świętym? Co chcesz od niego przejąć?",
        personal_challenge="Przeczytaj życiorys swojego patrona. Napisz 5 zdań: 'Chcę naśladować tego świętego, bo...'",
        prayer="Święty [patron], módl się za mną. Niech twoje życie będzie dla mnie drogowskazem.",
    ),
    ConfirmationSession(
        session_id="conf_06_commitment",
        number=6,
        title="Moje postanowienie wiary",
        subtitle="Osobista deklaracja przed Bierzmowaniem",
        holy_spirit_gift="Pobożność / Bojaźń Boża",
        scripture=["Joz 24,15", "Rut 1,16", "J 21,17"],
        ccc_refs=["§§ 1309-1316"],
        key_question="Czy jesteś gotów? Czego się boisz? Czego pragniesz po przyjęciu Bierzmowania?",
        personal_challenge="Napisz list do siebie samego — do przeczytania za 10 lat: co dziś obiecujesz Bogu?",
        prayer="Panie, oddaję Ci swoje życie. Przyjmij mnie takiego, jakim jestem. Uczyń mnie świadkiem Twojej miłości.",
    ),
]

_CONFIRMATION_SYSTEM = """Jesteś katechistą przygotowującym młodych ludzi do sakramentu bierzmowania.
Twoja rola:
- Pomagać kandydatom dokonać osobistego, świadomego wyboru wiary
- Rozmawiać o Duchu Świętym, darach i owocach w kontekście ich codziennego życia
- Odpowiadać na pytania i wątpliwości z szacunkiem — bez moralizowania
- Wskazywać na piękno życia z Duchem Świętym
- Motywować do odważnego świadectwa wiary
Mów bezpośrednio i z entuzjazmem — to są młodzi ludzie (nastolatki/młodzi dorośli)."""


class ConfirmationService:
    """Confirmation preparation service — 6-session program."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from app.core.config import settings
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_program(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "number": s.number,
                "title": s.title,
                "subtitle": s.subtitle,
                "holy_spirit_gift": s.holy_spirit_gift,
                "scripture": s.scripture,
                "ccc_refs": s.ccc_refs,
                "key_question": s.key_question,
                "personal_challenge": s.personal_challenge,
                "prayer": s.prayer,
            }
            for s in CONFIRMATION_SESSIONS
        ]

    def get_gifts_of_spirit(self) -> list[dict]:
        """Return all 7 gifts of the Holy Spirit with descriptions."""
        return GIFTS_OF_SPIRIT

    def get_session(self, session_id: str) -> dict | None:
        for s in CONFIRMATION_SESSIONS:
            if s.session_id == session_id:
                return {
                    "session_id": s.session_id,
                    "number": s.number,
                    "title": s.title,
                    "subtitle": s.subtitle,
                    "holy_spirit_gift": s.holy_spirit_gift,
                    "scripture": s.scripture,
                    "ccc_refs": s.ccc_refs,
                    "key_question": s.key_question,
                    "personal_challenge": s.personal_challenge,
                    "prayer": s.prayer,
                }
        return None

    async def answer_question(
        self,
        question: str,
        session_id: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Answer a candidate's question about faith and Confirmation."""
        context = ""
        if session_id:
            session = self.get_session(session_id)
            if session:
                context = f"Kontekst: sesja {session['number']} — '{session['title']}'."

        messages: list[dict] = [{"role": "system", "content": _CONFIRMATION_SYSTEM}]
        if context:
            messages.append({"role": "system", "content": context})
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": question})

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.75,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def help_choose_patron(
        self,
        interests: list[str],
        personal_traits: list[str],
    ) -> str:
        """Suggest confirmation patron saints based on candidate's interests and traits."""
        prompt = (
            f"Pomóż wybrać patrona na bierzmowanie.\n"
            f"Zainteresowania kandydata: {', '.join(interests) if interests else 'nie podano'}.\n"
            f"Cechy osobowości: {', '.join(personal_traits) if personal_traits else 'nie podano'}.\n\n"
            "Zaproponuj 3 świętych z krótkim (2-3 zdania) uzasadnieniem dla każdego. "
            "Uwzględnij świętych z różnych epok i tradycji."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.8,
            messages=[
                {"role": "system", "content": _CONFIRMATION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
