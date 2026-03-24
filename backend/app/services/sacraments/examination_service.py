"""
ExaminationService — AI-guided examination of conscience before Confession.

Generates a personalised, structured examination following the traditional
Catholic method rooted in the Ten Commandments, Beatitudes, and the
duties proper to the penitent's state of life.

PRIVACY NOTE: This service does NOT persist specific sins or examination
answers. All data is ephemeral (session-scoped). The backend merely
generates prompts and acts-of-contrition text — it never stores the
user's responses to examination questions.

Stages
------
1. intro        — Brief catechesis on the Sacrament of Penance
2. examination  — AI-guided interactive examination (stream)
3. contrition   — Personal Act of Contrition generation
4. resolution   — Firm purpose of amendment suggestions
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class StateOfLife(str, Enum):
    """Canonical states of life for a Catholic penitent."""
    SINGLE = "single"
    MARRIED = "married"
    PARENT = "parent"
    RELIGIOUS = "religious"
    PRIEST = "priest"
    TEENAGER = "teenager"
    CHILD = "child"


class ExaminationMethod(str, Enum):
    TEN_COMMANDMENTS = "ten_commandments"
    BEATITUDES = "beatitudes"
    SEVEN_SINS = "seven_sins"
    CORPORAL_WORKS = "corporal_works"
    SPIRITUAL_WORKS = "spiritual_works"


@dataclass
class ExaminationQuestion:
    commandment: str
    commandment_number: int | None
    question: str
    scripture_ref: str
    ccc_ref: str
    tradition: str = "all"


# ---------------------------------------------------------------------------
# Examination structure: 10 Commandments
# ---------------------------------------------------------------------------

_COMMANDMENTS: list[dict] = [
    {
        "number": 1,
        "title": "Nie będziesz miał cudzych bogów obok Mnie",
        "ccc": "§§ 2083–2141",
        "scripture": "Wj 20,2-3",
        "questions": [
            "Czy moja wiara w Boga jest żywa i czynna, czy sprowadza się do zewnętrznych praktyk?",
            "Czy szukałem Boga w modlitwie każdego dnia, czy dawałem pierwszeństwo innym sprawom?",
            "Czy ufam Bogu w trudnościach, czy raczej zaufałem ludzkim siłom, magii, horoskopom?",
            "Czy zaniedbałem niedzielne praktyki religijne bez poważnego powodu?",
        ],
    },
    {
        "number": 2,
        "title": "Nie wzywaj imienia Pana Boga twego nadaremno",
        "ccc": "§§ 2142–2167",
        "scripture": "Wj 20,7",
        "questions": [
            "Czy wymawiałem imię Boga lub Jezusa Chrystusa bez uszanowania, w złości lub żartem?",
            "Czy złożyłem fałszywą przysięgę lub lekkomyślnie przywoływałem imię Boże?",
            "Czy dotrzymuję złożonych ślubów i obietnic wobec Boga?",
        ],
    },
    {
        "number": 3,
        "title": "Pamiętaj, abyś dzień święty święcił",
        "ccc": "§§ 2168–2195",
        "scripture": "Wj 20,8",
        "questions": [
            "Czy uczestniczyłem w niedzielnej i świątecznej Eucharystii?",
            "Czy dzień Pański poświęcam na modlitwę, odpoczynek i czas z rodziną?",
            "Czy zmuszałem innych do niepotrzebnej pracy w niedzielę?",
        ],
    },
    {
        "number": 4,
        "title": "Czcij ojca swego i matkę swoją",
        "ccc": "§§ 2197–2257",
        "scripture": "Wj 20,12",
        "questions": [
            "Czy odnosiłem się do rodziców z szacunkiem, wdzięcznością i miłością?",
            "Czy troszczyłem się o starszych lub chorych rodziców?",
            "Czy okazywałem posłuszeństwo prawowitym władzom w sprawach dobra wspólnego?",
            "Czy jako rodzic wychowuję dzieci w wierze i modlitwie?",
        ],
    },
    {
        "number": 5,
        "title": "Nie zabijaj",
        "ccc": "§§ 2258–2330",
        "scripture": "Wj 20,13",
        "questions": [
            "Czy żywiłem gniew, nienawiść lub niechęć wobec kogokolwiek?",
            "Czy wyrządziłem komuś krzywdę fizyczną lub psychiczną?",
            "Czy dbałem o własne zdrowie, czy nadużywałem alkoholu, narkotyków lub innych substancji?",
            "Czy pomogłem komuś w potrzebie, czy przeszedłem obojętnie?",
        ],
    },
    {
        "number": 6,
        "title": "Nie cudzołóż",
        "ccc": "§§ 2331–2400",
        "scripture": "Wj 20,14",
        "questions": [
            "Czy zachowałem czystość w myślach, słowach i czynach?",
            "Czy oglądałem lub czytałem treści pornograficzne?",
            "Czy szanowałem godność osoby ludzkiej w relacjach z innymi?",
            "Czy byłem wierny w małżeństwie — duchem i ciałem?",
        ],
    },
    {
        "number": 7,
        "title": "Nie kradnij",
        "ccc": "§§ 2401–2463",
        "scripture": "Wj 20,15",
        "questions": [
            "Czy wziąłem coś cudzego bez pozwolenia?",
            "Czy byłem uczciwy w pracy, interesach, płaceniu podatków?",
            "Czy dzieliłem się z potrzebującymi według swoich możliwości?",
            "Czy wyrządziłem komuś szkodę materialną i naprawiłem ją?",
        ],
    },
    {
        "number": 8,
        "title": "Nie mów fałszywego świadectwa",
        "ccc": "§§ 2464–2513",
        "scripture": "Wj 20,16",
        "questions": [
            "Czy byłem szczery w słowach, czy kłamałem lub oszukiwałem?",
            "Czy mówiłem źle o innych za ich plecami (obmowa) lub fałszywie (oszczerstwo)?",
            "Czy ujawniałem tajemnice powierzone mi w zaufaniu?",
            "Czy naprawiłem dobre imię kogoś, kogo skrzywdziłem słowem?",
        ],
    },
    {
        "number": 9,
        "title": "Nie pożądaj żony bliźniego",
        "ccc": "§§ 2514–2533",
        "scripture": "Wj 20,17",
        "questions": [
            "Czy zachowałem czystość serca wobec osób zamężnych lub żonatych?",
            "Czy zwalczałem myśli i pożądania, które sprzeciwiają się czystości?",
        ],
    },
    {
        "number": 10,
        "title": "Nie pożądaj żadnej rzeczy bliźniego twego",
        "ccc": "§§ 2534–2557",
        "scripture": "Wj 20,17",
        "questions": [
            "Czy byłem zadowolony z tego, co posiadam, czy trawiła mnie zazdrość?",
            "Czy chciwość lub żądza posiadania kierowała moim postępowaniem?",
            "Czy żyję prostotą i wewnętrzną wolnością wobec dóbr materialnych?",
        ],
    },
]

_STATE_ADDITIONS: dict[StateOfLife, list[str]] = {
    StateOfLife.PARENT: [
        "Czy modliłem się codziennie razem z dziećmi?",
        "Czy pokazywałem dzieciom swoją wiarę przez osobisty przykład?",
        "Czy zadbałem o chrzest, katechezę i sakramenty dzieci?",
        "Czy byłem cierpliwy i łagodny wobec dzieci, czy wymierzałem kary z gniewu?",
    ],
    StateOfLife.MARRIED: [
        "Czy troszczyłem się o modlitwę i wiarę w naszym małżeństwie?",
        "Czy byłem dla małżonka partnerem w miłości, wzajemnym szacunku i przebaczeniu?",
        "Czy respektowałem nauczanie Kościoła dotyczące małżeństwa i rodzicielstwa?",
    ],
    StateOfLife.RELIGIOUS: [
        "Czy żyłem zgodnie ze ślubami czystości, ubóstwa i posłuszeństwa?",
        "Czy byłem wierny regule zakonnej i godzinom liturgicznym?",
        "Czy służyłem braciom/siostrom z miłością i pokorą?",
    ],
    StateOfLife.PRIEST: [
        "Czy sprawowałem liturgię z należytą pobożnością i wiernością przepisom?",
        "Czy byłem dostępny dla powierzonej mi wspólnoty?",
        "Czy głosiłem Ewangelię w całości, bez omijania trudnych prawd wiary?",
        "Czy dbałem o życie modlitwy, breviarium i rekolekcje?",
    ],
    StateOfLife.TEENAGER: [
        "Czy okazywałem szacunek rodzicom i nauczycielom?",
        "Czy byłem uczciwy w szkole i wobec rówieśników?",
        "Czy używałem internetu i mediów społecznościowych w sposób godziwy?",
    ],
}

_SYSTEM_PROMPT = """Jesteś katolickim kierownikiem duchowym o wielkiej mądrości i czułości.
Prowadzisz penitenta przez rachunek sumienia przed Sakramentem Pojednania.

Twoja rola:
- Delikatnie, bez osądzania, zadawaj pytania pomocne do głębokiej refleksji
- Opieraj się na Katechizmie Kościoła Katolickiego i Piśmie Świętym
- Wyrażaj miłosierdzie i nadzieję — Sakrament Pojednania to spotkanie z miłującym Ojcem
- Nigdy nie pytaj o szczegóły grzechów — to jest sprawa spowiednika
- Pomagaj penitentowi zobaczyć głębsze motywy, nie tylko powierzchowne czyny
- Mów po polsku, prostym i ciepłym językiem
- Zachęcaj do aktu żalu i mocnego postanowienia poprawy

Pamiętaj: Twoja misja to pomóc osobie stanąć przed Bogiem szczerym sercem."""


class ExaminationService:
    """AI-guided examination of conscience service."""

    def __init__(self, model: str = "gpt-4o") -> None:
        from app.core.config import settings
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_commandments_overview(self) -> list[dict]:
        """Return the 10 Commandments structure with questions (no AI needed)."""
        return [
            {
                "number": c["number"],
                "title": c["title"],
                "ccc_ref": c["ccc"],
                "scripture": c["scripture"],
                "questions": c["questions"],
            }
            for c in _COMMANDMENTS
        ]

    def get_state_questions(self, state: StateOfLife) -> list[str]:
        """Return extra questions for a specific state of life."""
        return _STATE_ADDITIONS.get(state, [])

    async def generate_personalized_examination(
        self,
        state_of_life: StateOfLife,
        focus_areas: list[str] | None = None,
        language: str = "pl",
    ) -> str:
        """Generate a full personalised examination text (non-streaming)."""
        focus_text = ""
        if focus_areas:
            focus_text = f"\nOsoboste obszary refleksji: {', '.join(focus_areas)}."

        state_questions = _STATE_ADDITIONS.get(state_of_life, [])
        state_text = ""
        if state_questions:
            state_text = "\nDodatkowe pytania dla stanu życia:\n" + "\n".join(
                f"- {q}" for q in state_questions
            )

        prompt = f"""Przygotuj osobisty rachunek sumienia dla osoby w stanie: {state_of_life.value}.
Stan życia: {state_of_life.value}{focus_text}{state_text}

Przygotuj ciepłe, osobiste wprowadzenie zachęcające do szczerej refleksji, a następnie
podsumuj kluczowe obszary rachunku sumienia. Zakończ modlitwą przygotowawczą przed spowiedzią.
Całość powinna być krótka (do 300 słów), delikatna i pełna nadziei."""

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    async def stream_guided_reflection(
        self,
        commandment_number: int,
        state_of_life: StateOfLife,
        user_reflection: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a guided reflection for a specific commandment.

        If user_reflection is provided, the AI responds to the penitent's
        thoughts with compassionate guidance — without recording specifics.
        """
        commandment = next(
            (c for c in _COMMANDMENTS if c["number"] == commandment_number),
            None,
        )
        if commandment is None:
            yield "Nieznane przykazanie."
            return

        if user_reflection:
            user_msg = (
                f"Penitent rozważa przykazanie '{commandment['title']}' "
                f"({commandment['ccc']}) i dzieli się refleksją: \"{user_reflection}\"\n\n"
                "Odpowiedz krótko (3-5 zdań), z miłością i mądrością duchową, "
                "pomagając pogłębić refleksję. Nie komentuj szczegółów grzechów."
            )
        else:
            user_msg = (
                f"Przeprowadź krótką medytację (4-6 zdań) nad przykazaniem: "
                f"'{commandment['title']}' (KKK {commandment['ccc']}, {commandment['scripture']}).\n"
                f"Stan życia penitenta: {state_of_life.value}.\n"
                "Zakończ jednym łagodnym pytaniem do osobistej refleksji."
            )

        stream = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.7,
            stream=True,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def generate_act_of_contrition(
        self,
        state_of_life: StateOfLife,
        personal_note: str | None = None,
    ) -> str:
        """Generate a personalised Act of Contrition prayer."""
        note = f' Motyw osobisty: "{personal_note}".' if personal_note else ""
        prompt = (
            f"Napisz osobisty Akt Żalu dla penitenta (stan: {state_of_life.value}).{note}\n"
            "Akt Żalu powinien: wyrazić żal za grzechy, wyznać miłość do Boga, "
            "zawierać mocne postanowienie poprawy, być szczery i osobisty (15-20 zdań). "
            "Bazuj na tradycyjnej formule, ale nadaj mu osobisty charakter."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.8,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    async def generate_resolution(
        self,
        focus_area: str,
        state_of_life: StateOfLife,
    ) -> str:
        """Generate a concrete, actionable purpose of amendment (postanowienie poprawy)."""
        prompt = (
            f"Dla penitenta (stan: {state_of_life.value}), który chce pracować nad: '{focus_area}',\n"
            "zaproponuj konkretne, realistyczne postanowienie poprawy.\n"
            "Postanowienie powinno:\n"
            "- Być możliwe do wykonania w ciągu tygodnia\n"
            "- Mieć konkretny, mierzalny element duchowy lub moralny\n"
            "- Zawierać propozycję modlitwy lub praktyki sakramentalnej\n"
            "Odpowiedź: 3-4 zdania."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
