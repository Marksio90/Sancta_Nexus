"""
MarriagePrepService — Catholic marriage preparation program.

Implements an 8-session formation program following the Polish Bishops'
Conference guidelines and Theology of the Body (Teologia Ciała).

Sessions
--------
1. Sakrament małżeństwa — przymierze, nie umowa
2. Miłość — co to znaczy kochać?
3. Komunikacja i rozwiązywanie konfliktów
4. Płciowość i Teologia Ciała (Jan Paweł II)
5. Planowanie rodziny — NPR i Humanae Vitae
6. Modlitwa w małżeństwie i rodzinie
7. Wyzwania współczesności — praca, finanse, cyfryzacja
8. Plany na przyszłość — wizja małżeństwa
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class MarriagePrepSession(str, Enum):
    SACRAMENT = "sacrament"
    LOVE = "love"
    COMMUNICATION = "communication"
    THEOLOGY_OF_BODY = "theology_of_body"
    FAMILY_PLANNING = "family_planning"
    PRAYER_IN_FAMILY = "prayer_in_family"
    MODERN_CHALLENGES = "modern_challenges"
    VISION = "vision"


@dataclass
class SessionContent:
    session_id: str
    number: int
    title: str
    subtitle: str
    scripture: list[str]
    ccc_refs: list[str]
    key_document: str
    key_questions: list[str]
    couple_exercise: str
    prayer: str
    duration_hours: float = 1.5


SESSIONS: list[SessionContent] = [
    SessionContent(
        session_id="mp_01_sacrament",
        number=1,
        title="Sakrament małżeństwa",
        subtitle="Przymierze miłości, nie umowa prawna",
        scripture=["Rdz 2,18-25", "Ef 5,25-32", "J 2,1-11"],
        ccc_refs=["§§ 1601-1658"],
        key_document="Familiaris Consortio (Jan Paweł II, 1981)",
        key_questions=[
            "Co rozumiecie przez słowa 'przymierze małżeńskie'?",
            "Dlaczego małżeństwo jest sakramentem — znakiem Bożej miłości?",
            "Czego oczekujecie od siebie nawzajem za 10, 20, 50 lat?",
        ],
        couple_exercise="Napiszcie razem 3 zdania o tym, dlaczego chcecie być razem na zawsze.",
        prayer="Panie, bądź gościem w naszym domu, jak byłeś gościem w Kanie. Pobłogosław naszą miłość.",
    ),
    SessionContent(
        session_id="mp_02_love",
        number=2,
        title="Co to znaczy kochać?",
        subtitle="Eros, philia, agape — trzy wymiary miłości",
        scripture=["1Kor 13,4-8", "1J 4,7-12", "Pnp 2,3-5"],
        ccc_refs=["§§ 1822-1829", "§§ 2331-2359"],
        key_document="Deus Caritas Est (Benedykt XVI, 2005) — cz. I",
        key_questions=[
            "Jak rozumiecie różnicę między miłością uczuciową a miłością z wyboru?",
            "Co robicie, gdy miłość wymaga poświęcenia?",
            "Jak okazujecie sobie miłość w codziennych sytuacjach?",
        ],
        couple_exercise="Lista: '10 rzeczy, które lubię w Tobie'. Wymieńcie się listami.",
        prayer="Boże miłości, ucz nas kochać tak, jak Ty kochasz — bezinteresownie i wiernie.",
    ),
    SessionContent(
        session_id="mp_03_communication",
        number=3,
        title="Komunikacja i konflikty",
        subtitle="Słuchać sercem — rozmawiać z miłością",
        scripture=["Ef 4,25-32", "Kol 3,12-15", "Jk 1,19"],
        ccc_refs=["§§ 2464-2474"],
        key_document="Amoris Laetitia (Franciszek, 2016) — rozdz. IV",
        key_questions=[
            "Jak rozwiązujecie spory? Czy potraficie przepraszać i przebaczać?",
            "Czego się boisz, gdy rozmawiacie o trudnych sprawach?",
            "Jakie tematy omijasz i dlaczego?",
        ],
        couple_exercise="Ćwiczenie aktywnego słuchania: jedna osoba mówi 3 minuty, druga słucha bez przerywania.",
        prayer="Panie, daj nam uszy do słuchania siebie nawzajem i serca zdolne do przebaczenia.",
    ),
    SessionContent(
        session_id="mp_04_tob",
        number=4,
        title="Teologia Ciała",
        subtitle="Ludzkie ciało jako sakrament oblubieńczy",
        scripture=["Rdz 1,27", "Rdz 2,24-25", "1Kor 6,19-20"],
        ccc_refs=["§§ 2331-2400"],
        key_document="Teologia Ciała (Jan Paweł II, 1979-1984) — katechezy środowe",
        key_questions=[
            "Jak postrzegacie swoją cielesność jako dar od Boga?",
            "Co znaczy, że ciało ludzkie ma charakter 'oblubieńczy'?",
            "Jak chronić intymność i czystość przed ślubem?",
        ],
        couple_exercise="Rozmowa o granicach i wzajemnym szacunku w sferze cielesnej.",
        prayer="Boże, Ty stworzyłeś nas mężczyzną i kobietą. Pomóż nam szanować ten dar w sobie nawzajem.",
    ),
    SessionContent(
        session_id="mp_05_family_planning",
        number=5,
        title="Planowanie rodziny",
        subtitle="Naturalne Planowanie Rodziny i Humanae Vitae",
        scripture=["Rdz 1,28", "Ps 127,3-5", "Ef 5,21"],
        ccc_refs=["§§ 2366-2379"],
        key_document="Humanae Vitae (Paweł VI, 1968)",
        key_questions=[
            "Jak rozumiecie odpowiedzialne rodzicielstwo?",
            "Czy rozmawiali o liczbie dzieci i czasie ich przyjścia na świat?",
            "Co wiecie o Naturalnym Planowaniu Rodziny?",
        ],
        couple_exercise="Wspólne omówienie wartości, jakie chcecie przekazać dzieciom.",
        prayer="Boże życia, daj nam mądrość, by przyjmować nowe życie z radością i odpowiedzialnością.",
    ),
    SessionContent(
        session_id="mp_06_prayer",
        number=6,
        title="Modlitwa w małżeństwie",
        subtitle="Dom Kościołem domowym — Ecclesia domestica",
        scripture=["Mt 18,20", "Kol 3,16-17", "1Tes 5,16-18"],
        ccc_refs=["§§ 2685-2691"],
        key_document="Familiaris Consortio §§ 55-62",
        key_questions=[
            "Czy modlicie się razem? Jak wygląda wasza wspólna modlitwa?",
            "Jakie tradycje religijne chcecie pielęgnować w rodzinie?",
            "Jak widzicie udział w niedzielnej Eucharystii jako rodzina?",
        ],
        couple_exercise="Zmówcie razem Ojcze Nasz i Różaniec — jedna dziesiąta. Porozmawiajcie, jak to przeżyliście.",
        prayer="Panie Jezu, mieszkaj w naszym domu. Bądź gościem naszego stołu i centrum naszego życia.",
    ),
    SessionContent(
        session_id="mp_07_challenges",
        number=7,
        title="Wyzwania współczesności",
        subtitle="Praca, finanse, technologia, przeszkody wiary",
        scripture=["Mt 6,24-34", "1Tm 6,6-10", "Koh 4,9-12"],
        ccc_refs=["§§ 2401-2463"],
        key_document="Laudato Si' §§ 46-54 (technologia i relacje)",
        key_questions=[
            "Jak będziecie zarządzać finansami? Osobno czy razem?",
            "Ile czasu spędzacie przy ekranach? Jak to wpłynie na waszą relację?",
            "Jak reagujecie, gdy praca pochłania za dużo czasu i energii?",
        ],
        couple_exercise="Ułóżcie razem 5 zasad korzystania z technologii w waszym domu.",
        prayer="Boże, chroń naszą relację od wszystkiego, co mogłoby ją osłabić. Daj nam mądrość wyboru.",
    ),
    SessionContent(
        session_id="mp_08_vision",
        number=8,
        title="Wizja naszego małżeństwa",
        subtitle="Zbudowanie na skale — lista wartości i zobowiązań",
        scripture=["Mt 7,24-27", "Joz 24,15", "Rut 1,16-17"],
        ccc_refs=["§§ 1641-1651"],
        key_document="Amoris Laetitia — rozdz. IX: Duchowość małżeńska",
        key_questions=[
            "Jakie trzy wartości są dla was najważniejsze w małżeństwie?",
            "Jakie będą wasze zasady w chwilach kryzysu?",
            "Jak wyobrażacie sobie wasz dom za 25 lat?",
        ],
        couple_exercise="Napisanie wspólnej 'Karty małżeńskiej' — 5-7 zasad waszego związku.",
        prayer="Panie, oddajemy Ci nasze małżeństwo. Zbuduj je na skale Twojej miłości. Amen.",
    ),
]


_MARRIAGE_SYSTEM_PROMPT = """Jesteś doradcą małżeńskim i katechetą przygotowującym narzeczonych do sakramentu małżeństwa.
Twoim zadaniem jest:
- Pomagać parom odkryć piękno sakramentalnej miłości
- Wprowadzać w Teologię Ciała Jana Pawła II
- Wspierać otwartą, szczerą komunikację między partnerami
- Omawiać realistyczne wyzwania małżeńskiego życia
- Być ciepłym przewodnikiem, nie sędzią
Mów po polsku, z optymizmem i mądrością."""


class MarriagePrepService:
    """Catholic marriage preparation service — 8-session program."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from app.core.config import settings
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_program(self) -> list[dict]:
        """Return the full 8-session program."""
        return [
            {
                "session_id": s.session_id,
                "number": s.number,
                "title": s.title,
                "subtitle": s.subtitle,
                "scripture": s.scripture,
                "ccc_refs": s.ccc_refs,
                "key_document": s.key_document,
                "key_questions": s.key_questions,
                "couple_exercise": s.couple_exercise,
                "prayer": s.prayer,
                "duration_hours": s.duration_hours,
            }
            for s in SESSIONS
        ]

    def get_session(self, session_id: str) -> dict | None:
        for s in SESSIONS:
            if s.session_id == session_id:
                return {
                    "session_id": s.session_id,
                    "number": s.number,
                    "title": s.title,
                    "subtitle": s.subtitle,
                    "scripture": s.scripture,
                    "ccc_refs": s.ccc_refs,
                    "key_document": s.key_document,
                    "key_questions": s.key_questions,
                    "couple_exercise": s.couple_exercise,
                    "prayer": s.prayer,
                }
        return None

    async def facilitate_discussion(
        self,
        session_id: str,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Facilitate a couple's discussion for a specific session topic."""
        session = self.get_session(session_id)
        context = ""
        if session:
            context = (
                f"Temat sesji: {session['title']} — {session['subtitle']}.\n"
                f"Kluczowy dokument: {session['key_document']}.\n"
                f"Pytania sesji: {'; '.join(session['key_questions'])}"
            )

        messages: list[dict] = [{"role": "system", "content": _MARRIAGE_SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": context})
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_message})

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.75,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def generate_session_reflection(self, session_id: str) -> str:
        """Generate a guided reflection for a session."""
        session = self.get_session(session_id)
        if not session:
            return "Nie znaleziono sesji."

        prompt = (
            f"Przygotuj 200-słowną medytację dla narzeczonych na temat:\n"
            f"'{session['title']} — {session['subtitle']}'\n"
            f"Pismo Święte: {', '.join(session['scripture'])}\n"
            f"KKK: {', '.join(session['ccc_refs'])}\n\n"
            "Medytacja powinna być: ciepła, konkretna, zakończona modlitwą pary."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.8,
            messages=[
                {"role": "system", "content": _MARRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
