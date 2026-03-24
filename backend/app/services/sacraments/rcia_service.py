"""
RCIAService — Rite of Christian Initiation of Adults (RCIA).

Implements the four-stage RCIA journey following the Rite of Christian
Initiation of Adults (1972, revised 1988) as received in the Polish Church.

Stages
------
1. Precatechumenate  — Inquiry (Ewangelizacja wstępna)
2. Catechumenate     — Formation (Katechumenat właściwy)
3. Purification      — Lenten preparation before Baptism / full reception
4. Mystagogia        — Post-baptismal mystagogy

Each stage has a structured curriculum with topics, scripture, CCC refs,
and AI-assisted reflection prompts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class RCIAStage(str, Enum):
    PRECATECHUMENATE = "precatechumenate"
    CATECHUMENATE = "catechumenate"
    PURIFICATION = "purification"
    MYSTAGOGIA = "mystagogia"


@dataclass
class RCIATopic:
    session_id: str
    stage: RCIAStage
    session_number: int
    title: str
    title_pl: str
    summary: str
    scripture: list[str]
    ccc_refs: list[str]
    key_question: str
    prayer_suggestion: str
    duration_weeks: int = 1


# ---------------------------------------------------------------------------
# RCIA Curriculum
# ---------------------------------------------------------------------------

RCIA_CURRICULUM: list[RCIATopic] = [
    # ── Stage 1: Precatechumenate ────────────────────────────────────────────
    RCIATopic(
        session_id="rcia_pre_01",
        stage=RCIAStage.PRECATECHUMENATE,
        session_number=1,
        title="Who is God?",
        title_pl="Kim jest Bóg?",
        summary="Pierwsze kroki na drodze wiary. Pytania o Boga, sens życia i ludzkie poszukiwanie.",
        scripture=["Ps 139,1-10", "J 1,1-5", "Rz 1,19-20"],
        ccc_refs=["§§ 26-49", "§§ 54-73"],
        key_question="Dlaczego szukasz Boga? Co cię do Niego przyciąga?",
        prayer_suggestion="Modlitwa poszukującego: 'Boże, jeśli jesteś — pomóż mi Cię znaleźć.'",
    ),
    RCIATopic(
        session_id="rcia_pre_02",
        stage=RCIAStage.PRECATECHUMENATE,
        session_number=2,
        title="Jesus Christ — who is He?",
        title_pl="Jezus Chrystus — kim jest?",
        summary="Historyczność i tożsamość Jezusa. Ewangelia jako dobra nowina.",
        scripture=["J 1,14", "J 14,6", "Mt 16,15-17"],
        ccc_refs=["§§ 422-478"],
        key_question="Kim dla ciebie jest Jezus? Czy spotkałeś Go w życiu?",
        prayer_suggestion="Czytanie jednej Ewangelii — 10 minut dziennie.",
    ),
    RCIATopic(
        session_id="rcia_pre_03",
        stage=RCIAStage.PRECATECHUMENATE,
        session_number=3,
        title="The Church — community of disciples",
        title_pl="Kościół — wspólnota uczniów",
        summary="Czym jest Kościół? Dlaczego Kościół jest potrzebny do zbawienia?",
        scripture=["Mt 16,18", "1Kor 12,12-27", "Ef 1,22-23"],
        ccc_refs=["§§ 748-769"],
        key_question="Jakie jest twoje doświadczenie wspólnoty? Czego szukasz w Kościele?",
        prayer_suggestion="Udział w niedzielnej Eucharystii — jako obserwator.",
    ),
    # ── Stage 2: Catechumenate ────────────────────────────────────────────────
    RCIATopic(
        session_id="rcia_cat_01",
        stage=RCIAStage.CATECHUMENATE,
        session_number=1,
        title="The Creed — I believe",
        title_pl="Credo — Wierzę",
        summary="Skład Apostolski jako synteza wiary. Artykuły wiary.",
        scripture=["J 11,25-27", "Rz 10,9-10", "Hbr 11,1"],
        ccc_refs=["§§ 185-197", "§§ 198-278"],
        key_question="W co wierzysz? Które artykuły wiary są dla ciebie trudne?",
        prayer_suggestion="Modlitwa Credo — codziennie rano.",
    ),
    RCIATopic(
        session_id="rcia_cat_02",
        stage=RCIAStage.CATECHUMENATE,
        session_number=2,
        title="Sacred Scripture and Tradition",
        title_pl="Pismo Święte i Tradycja",
        summary="Biblia jako słowo Boga. Tradycja apostolska. Lectio Divina.",
        scripture=["2Tm 3,16-17", "J 5,39", "Łk 24,45"],
        ccc_refs=["§§ 74-100", "§§ 101-141"],
        key_question="Czy czytasz Biblię? Jak Bóg przemawia przez Pismo?",
        prayer_suggestion="Lectio Divina: J 1,1-18 — 20 minut.",
    ),
    RCIATopic(
        session_id="rcia_cat_03",
        stage=RCIAStage.CATECHUMENATE,
        session_number=3,
        title="Prayer and the life of grace",
        title_pl="Modlitwa i życie łaski",
        summary="Modlitwa jako rozmowa z Bogiem. Łaska uświęcająca. Życie w Duchu.",
        scripture=["Mt 6,9-13", "Rz 8,26-27", "1Tes 5,17"],
        ccc_refs=["§§ 1716-1742", "§§ 2697-2724"],
        key_question="Jak wygląda twoja modlitwa? Co chciałbyś zmienić?",
        prayer_suggestion="Modlitwa Ojcze Nasz — wolno, z rozważaniem każdego wezwania.",
    ),
    RCIATopic(
        session_id="rcia_cat_04",
        stage=RCIAStage.CATECHUMENATE,
        session_number=4,
        title="The Sacraments — signs of grace",
        title_pl="Sakramenty — znaki łaski",
        summary="Siedem sakramentów. Chrzest i bierzmowanie. Eucharystia jako centrum.",
        scripture=["J 3,5", "Mt 28,19", "J 6,35"],
        ccc_refs=["§§ 1210-1321"],
        key_question="Które sakramenty przyjąłeś? Czego jeszcze pragniesz?",
        prayer_suggestion="Adoracja Najświętszego Sakramentu — 30 minut.",
    ),
    RCIATopic(
        session_id="rcia_cat_05",
        stage=RCIAStage.CATECHUMENATE,
        session_number=5,
        title="Moral life — love of God and neighbour",
        title_pl="Życie moralne — miłość Boga i bliźniego",
        summary="Przykazania Boże jako droga wolności. Sumienie. Cnoty.",
        scripture=["Mt 22,36-40", "J 13,34-35", "Ga 5,22-23"],
        ccc_refs=["§§ 1691-1715", "§§ 2052-2082"],
        key_question="Jak rozumiesz wolność? Czy przykazania są dla ciebie ciężarem czy drogowskazem?",
        prayer_suggestion="Rachunek sumienia wieczorny — 10 minut.",
    ),
    RCIATopic(
        session_id="rcia_cat_06",
        stage=RCIAStage.CATECHUMENATE,
        session_number=6,
        title="Mary and the Saints",
        title_pl="Maryja i Święci",
        summary="Maryja jako wzór ucznia. Świętych obcowanie. Modlitwa wstawiennicza.",
        scripture=["Łk 1,28-35", "J 19,26-27", "Ap 12,1"],
        ccc_refs=["§§ 963-975", "§§ 946-962"],
        key_question="Jaką rolę odgrywa Maryja w twoim życiu wiary?",
        prayer_suggestion="Różaniec — 1 dziesiątek z rozważaniem.",
    ),
    # ── Stage 3: Purification & Enlightenment ────────────────────────────────
    RCIATopic(
        session_id="rcia_pur_01",
        stage=RCIAStage.PURIFICATION,
        session_number=1,
        title="Scrutinies — facing sin and seeking healing",
        title_pl="Skrutinia — rachunek sumienia i prośba o uzdrowienie",
        summary="Ryty skrutiniów wielkopostnych. Wyznanie grzechów i nawrócenie.",
        scripture=["J 4,5-42", "J 9,1-41", "J 11,1-45"],
        ccc_refs=["§§ 1425-1470"],
        key_question="Co w tobie domaga się uzdrowienia? Co chcesz zostawić za sobą?",
        prayer_suggestion="Modlitwa z Ps 51 (Miserere) — codziennie w tygodniu.",
    ),
    RCIATopic(
        session_id="rcia_pur_02",
        stage=RCIAStage.PURIFICATION,
        session_number=2,
        title="The Creed and Lord's Prayer — tradition and mystagogia",
        title_pl="Traditio — przekazanie Credo i Ojcze Nasz",
        summary="Credo i Modlitwa Pańska jako fundament życia chrześcijańskiego.",
        scripture=["Mt 6,9-13", "1Kor 15,3-8"],
        ccc_refs=["§§ 197-278", "§§ 2759-2865"],
        key_question="Jak rozumiesz teraz Credo po miesiącach formacji?",
        prayer_suggestion="Memoryzacja Credo i Ojcze Nasz w oryginalnym brzmieniu.",
    ),
    RCIATopic(
        session_id="rcia_pur_03",
        stage=RCIAStage.PURIFICATION,
        session_number=3,
        title="Easter Vigil — Baptism, Confirmation, Eucharist",
        title_pl="Wigilia Paschalna — Chrzest, Bierzmowanie, Eucharystia",
        summary="Noc Paschalna jako centrum roku liturgicznego i życia chrześcijańskiego.",
        scripture=["Rz 6,3-11", "J 20,1-9"],
        ccc_refs=["§§ 1212-1274"],
        key_question="Czego się spodziewasz w tę świętą noc?",
        prayer_suggestion="Medytacja przy świecy paschalnej — 'Lumen Christi'.",
    ),
    # ── Stage 4: Mystagogia ──────────────────────────────────────────────────
    RCIATopic(
        session_id="rcia_mys_01",
        stage=RCIAStage.MYSTAGOGIA,
        session_number=1,
        title="Life after Easter — living the sacraments",
        title_pl="Życie po Wielkanocy — żyć sakramentami",
        summary="Pogłębianie zrozumienia przyjętych sakramentów przez doświadczenie.",
        scripture=["J 20,19-23", "Dz 2,42-47"],
        ccc_refs=["§§ 1212-1274", "§§ 1322-1419"],
        key_question="Jak zmieniło się twoje życie po przyjęciu sakramentów inicjacji?",
        prayer_suggestion="Codzienna Eucharystia przez oktawę Wielkanocną.",
    ),
    RCIATopic(
        session_id="rcia_mys_02",
        stage=RCIAStage.MYSTAGOGIA,
        session_number=2,
        title="Mission — witness and service",
        title_pl="Misja — świadectwo i służba",
        summary="Posłanie chrzcielne. Apostolat świeckich. Charyzmat i powołanie.",
        scripture=["Mt 28,19-20", "Dz 1,8", "1P 2,9"],
        ccc_refs=["§§ 897-913", "§§ 863-865"],
        key_question="Do czego Bóg cię posyła? Jaką misję widzisz dla siebie w Kościele?",
        prayer_suggestion="Modlitwa za powołanie i misję — codziennie.",
    ),
]


_RCIA_SYSTEM_PROMPT = """Jesteś doświadczonym katechistą RCIA, który towarzyszy dorosłym kandydatom
na drodze do wiary. Twoja rola to:
- Odpowiadać na pytania z cierpliwością i radością
- Pogłębiać rozumienie wiary, nie narzucając jej
- Łączyć doktrynę z osobistym doświadczeniem życia
- Używać prostego, przystępnego języka
- Wskazywać na piękno wiary katolickiej
Mów po polsku, chyba że kandydat pyta w innym języku."""


class RCIAService:
    """RCIA formation service — structured multi-stage faith journey."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from app.core.config import settings
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_curriculum(self) -> list[dict]:
        """Return the full RCIA curriculum as a structured list."""
        result: dict[str, list] = {s.value: [] for s in RCIAStage}
        for topic in RCIA_CURRICULUM:
            result[topic.stage.value].append({
                "session_id": topic.session_id,
                "session_number": topic.session_number,
                "title": topic.title,
                "title_pl": topic.title_pl,
                "summary": topic.summary,
                "scripture": topic.scripture,
                "ccc_refs": topic.ccc_refs,
                "key_question": topic.key_question,
                "prayer_suggestion": topic.prayer_suggestion,
            })
        return [
            {
                "stage": stage,
                "sessions": sessions,
                "session_count": len(sessions),
            }
            for stage, sessions in result.items()
        ]

    def get_session(self, session_id: str) -> dict | None:
        """Return a specific session by ID."""
        for t in RCIA_CURRICULUM:
            if t.session_id == session_id:
                return {
                    "session_id": t.session_id,
                    "stage": t.stage.value,
                    "session_number": t.session_number,
                    "title": t.title,
                    "title_pl": t.title_pl,
                    "summary": t.summary,
                    "scripture": t.scripture,
                    "ccc_refs": t.ccc_refs,
                    "key_question": t.key_question,
                    "prayer_suggestion": t.prayer_suggestion,
                }
        return None

    async def answer_question(
        self,
        question: str,
        session_id: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Answer a catechumen's question with pastoral guidance."""
        context = ""
        if session_id:
            session = self.get_session(session_id)
            if session:
                context = (
                    f"Kontekst sesji: '{session['title_pl']}'. "
                    f"Kluczowe pytanie sesji: {session['key_question']}"
                )

        messages: list[dict] = [{"role": "system", "content": _RCIA_SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": context})
        if conversation_history:
            messages.extend(conversation_history[-6:])  # last 3 exchanges
        messages.append({"role": "user", "content": question})

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.7,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def generate_reflection(self, session_id: str) -> str:
        """Generate a guided reflection for a session."""
        session = self.get_session(session_id)
        if not session:
            return "Nie znaleziono sesji."

        prompt = (
            f"Przygotuj krótką (200 słów) prowadzoną refleksję do sesji RCIA:\n"
            f"Temat: {session['title_pl']}\n"
            f"Streszczenie: {session['summary']}\n"
            f"Pismo Święte: {', '.join(session['scripture'])}\n"
            f"KKK: {', '.join(session['ccc_refs'])}\n\n"
            f"Refleksja powinna być: modlitewna, oparta na Piśmie, zakończona pytaniem do osobistej modlitwy."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.8,
            messages=[
                {"role": "system", "content": _RCIA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""
