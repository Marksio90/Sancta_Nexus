"""RosaryService — Community and personal Rosary sessions.

Implements:
- Full mystery database (Joyful / Sorrowful / Glorious / Luminous)
- Day-appropriate mystery recommendation
- Community session creation, joining, decade tracking
- AI meditation streaming for each mystery (via OpenAI)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CommunityRosary, RosaryParticipation

logger = logging.getLogger(__name__)

# ── Mystery content ────────────────────────────────────────────────────────────

MYSTERIES: dict[str, list[dict]] = {
    "radosne": [
        {
            "number": 1,
            "title": "Zwiastowanie Najświętszej Maryi Panny",
            "scripture": "Łk 1,26-38",
            "fruit": "Pokora",
            "meditation": "Maryja odpowiada «tak» na Boże zaproszenie. Anioł Gabriel przynosi niespodziewaną wieść — Bóg prosi o zgodę człowieka.",
        },
        {
            "number": 2,
            "title": "Nawiedzenie Elżbiety",
            "scripture": "Łk 1,39-56",
            "fruit": "Miłość bliźniego",
            "meditation": "Maryja spieszy z pomocą do starszej krewnej. Radość wiary przenosi się przez spotkanie — Jan tańczy z radości w łonie matki.",
        },
        {
            "number": 3,
            "title": "Narodzenie Pana Jezusa",
            "scripture": "Łk 2,1-20",
            "fruit": "Ubóstwo duchowe",
            "meditation": "Bóg rodzi się w ubóstwie. Nie pałac, nie tron — żłób i pasterze. Paradoks Wcielenia: wielkość ukryta w małości.",
        },
        {
            "number": 4,
            "title": "Ofiarowanie Pana Jezusa w świątyni",
            "scripture": "Łk 2,22-40",
            "fruit": "Posłuszeństwo i duch ofiary",
            "meditation": "Symeon trzyma w ramionach «światło na oświecenie pogan». Każde życie jest darem złożonym Bogu. Miecz boleści przeniknie duszę Maryi.",
        },
        {
            "number": 5,
            "title": "Znalezienie Pana Jezusa w świątyni",
            "scripture": "Łk 2,41-52",
            "fruit": "Gorliwość w szukaniu Boga",
            "meditation": "«Nie wiedziałeś, że powinienem być w sprawach mojego Ojca?» Zagubiony i znaleziony — doświadczenie każdego poszukującego.",
        },
    ],
    "bolesne": [
        {
            "number": 1,
            "title": "Modlitwa Pana Jezusa w Ogrójcu",
            "scripture": "Mk 14,32-42",
            "fruit": "Żal za grzechy",
            "meditation": "«Abba, Ojcze, wszystko jest możliwe dla Ciebie». Jezus przyjmuje kielich, choć się wzdryga. Samotność modlitwy w nocy.",
        },
        {
            "number": 2,
            "title": "Biczowanie Pana Jezusa",
            "scripture": "J 19,1",
            "fruit": "Umartwienie zmysłów",
            "meditation": "Ciało Boże chłostane przez ludzkie ręce. Cierpi za nasze przyjemności i nieuporządkowane pragnienia.",
        },
        {
            "number": 3,
            "title": "Cierniem ukoronowanie",
            "scripture": "Mt 27,27-31",
            "fruit": "Pogarda świata i pychy",
            "meditation": "Purpurowy płaszcz i korona z ciernia — królewska godność wyśmiana. Prawdziwa korona rodzi się z ciernia.",
        },
        {
            "number": 4,
            "title": "Dźwiganie krzyża",
            "scripture": "Łk 23,26-32",
            "fruit": "Cierpliwość",
            "meditation": "Krzyż — narzędzie hańby staje się tronem chwały. Szymon z Cyreny: wciągamy w tajemnicę zbawienia wbrew woli.",
        },
        {
            "number": 5,
            "title": "Ukrzyżowanie i śmierć Pana Jezusa",
            "scripture": "J 19,17-37",
            "fruit": "Miłość nieprzyjaciół",
            "meditation": "«Ojcze, przebacz im, bo nie wiedzą, co czynią». Ostatnie słowa: pragnienie, troska o matkę, powierzenie ducha Ojcu.",
        },
    ],
    "chwalebne": [
        {
            "number": 1,
            "title": "Zmartwychwstanie Pana Jezusa",
            "scripture": "J 20,1-18",
            "fruit": "Wiara",
            "meditation": "Kamień odsunięty, grób pusty. «Nie ma Go tu — zmartwychwstał!» Maria Magdalena poznaje Mistrza po głosie.",
        },
        {
            "number": 2,
            "title": "Wniebowstąpienie Pana Jezusa",
            "scripture": "Dz 1,6-11",
            "fruit": "Nadzieja i pragnienie nieba",
            "meditation": "«Idę przygotować wam miejsce». Rozstanie jest początkiem — chmura przyjmuje Jezusa w chwale.",
        },
        {
            "number": 3,
            "title": "Zesłanie Ducha Świętego",
            "scripture": "Dz 2,1-13",
            "fruit": "Miłość Boga i bliźniego",
            "meditation": "Gwałtowny wicher i języki ognia. Bojaźliwi uczniowie wychodzą głosić. Moc z wysoka przemienia.",
        },
        {
            "number": 4,
            "title": "Wniebowzięcie Najświętszej Maryi Panny",
            "scripture": "Ap 12,1",
            "fruit": "Łaska dobrej śmierci",
            "meditation": "Maryja — pierwsza zrealizowana eschatologia. Ciało i dusza wniebowzięte. Przedsmak naszego zmartwychwstania.",
        },
        {
            "number": 5,
            "title": "Ukoronowanie Maryi na Królową nieba i ziemi",
            "scripture": "Ap 12,1-2",
            "fruit": "Wytrwałość i wytrwałość w dobrem",
            "meditation": "Kobieta obleczona w słońce, z księżycem pod stopami. Maryja — Królowa bez tronu władzy, na tronie miłości.",
        },
    ],
    "swietlne": [
        {
            "number": 1,
            "title": "Chrzest Pana Jezusa w Jordanie",
            "scripture": "Mt 3,13-17",
            "fruit": "Otwarcie na Ducha Świętego",
            "meditation": "«Ten jest mój Syn umiłowany». Niebiosa otwarte nad wodą. Jezus przyjmuje chrzest solidarności z grzesznikami.",
        },
        {
            "number": 2,
            "title": "Objawienie się Pana Jezusa na weselu w Kanie",
            "scripture": "J 2,1-11",
            "fruit": "Maryjne wstawiennictwo",
            "meditation": "«Zróbcie wszystko, cokolwiek wam powie». Woda przemieniła się w wino. Pierwsze «tak» uczniów.",
        },
        {
            "number": 3,
            "title": "Głoszenie Królestwa Bożego i wzywanie do nawrócenia",
            "scripture": "Mk 1,14-15",
            "fruit": "Nawrócenie",
            "meditation": "«Czas się wypełnił, Królestwo Boże jest bliskie». Każda chwila — czas łaski, każde miejsce — przestrzeń zbawienia.",
        },
        {
            "number": 4,
            "title": "Przemienienie Pana Jezusa na górze Tabor",
            "scripture": "Łk 9,28-36",
            "fruit": "Pragnienie świętości",
            "meditation": "Twarz Jezusa zajaśniała jak słońce. Uczniowie padają twarzą na ziemię. Kontemplacja — dotyk Bożej chwały.",
        },
        {
            "number": 5,
            "title": "Ustanowienie Eucharystii",
            "scripture": "Łk 22,14-20",
            "fruit": "Adoracja Eucharystyczna",
            "meditation": "«To jest Ciało moje… za was wydane». Każda Msza — Ostatnia Wieczerza i Golgota uobecnione w czasie.",
        },
    ],
}

# Day-of-week mystery schedule (Monday=0)
DAILY_MYSTERY = {
    0: "radosne",      # Monday
    1: "bolesne",      # Tuesday
    2: "chwalebne",    # Wednesday
    3: "swietlne",     # Thursday
    4: "bolesne",      # Friday
    5: "radosne",      # Saturday
    6: "chwalebne",    # Sunday
}

_ROSARY_SYSTEM = """Jesteś duchowym przewodnikiem medytacji różańcowej w tradycji dominikańskiej i maryjnej.
Twoja rola:
- Prowadzić głęboką, kontemplacyjną medytację nad każdą tajemnicą różańcową
- Łączyć tekst Pisma Świętego z osobistym doświadczeniem modlącego
- Pomagać «widzieć» scenę ewangeliczną oczyma serca (imaginacja ignacjańska)
- Wydobyć duchowy owoc danej tajemnicy do praktycznego życia
- Mówić po polsku, cicho i rozważnie
Medytacja: 120-150 słów, zakończona wezwaniem do modlitwy Zdrowaś Maryjo."""


class RosaryService:

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from app.core.config import settings
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_mysteries(self, mystery_type: str) -> list[dict]:
        return MYSTERIES.get(mystery_type, [])

    def get_today_mystery(self) -> str:
        weekday = datetime.now(timezone.utc).weekday()
        return DAILY_MYSTERY[weekday]

    def get_all_mystery_types(self) -> list[dict]:
        return [
            {"id": "radosne", "label": "Tajemnice radosne", "days": "Pon · Sob", "color": "#a3c4bc"},
            {"id": "bolesne", "label": "Tajemnice bolesne", "days": "Wt · Pt", "color": "#c4a3a3"},
            {"id": "chwalebne", "label": "Tajemnice chwalebne", "days": "Śr · Nd", "color": "#c4c4a3"},
            {"id": "swietlne", "label": "Tajemnice światła", "days": "Czw", "color": "#a3b4c4"},
        ]

    async def stream_mystery_meditation(
        self,
        mystery_type: str,
        mystery_number: int,
    ) -> AsyncIterator[str]:
        """Stream an AI meditation for a specific Rosary mystery."""
        mysteries = MYSTERIES.get(mystery_type, [])
        mystery = next((m for m in mysteries if m["number"] == mystery_number), None)
        if not mystery:
            yield "Nie znaleziono tajemnicy."
            return

        prompt = (
            f"Tajemnica różańca: **{mystery['title']}** ({mystery['scripture']})\n"
            f"Owoc tajemnicy: {mystery['fruit']}\n\n"
            f"Tło do medytacji: {mystery['meditation']}\n\n"
            "Poprowadź powolną, kontemplacyjną medytację nad tą tajemnicą. "
            "Pomóż modlącemu wejść w scenę ewangeliczną wszystkimi zmysłami duszy."
        )

        from openai import AsyncOpenAI
        stream = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.75,
            stream=True,
            messages=[
                {"role": "system", "content": _ROSARY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ── Community sessions ─────────────────────────────────────────────────────

    async def create_session(
        self,
        db: AsyncSession,
        mystery_type: str,
        intention: str | None,
        user_id: str | None,
    ) -> dict[str, Any]:
        session = CommunityRosary(
            id=str(uuid4()),
            mystery_type=mystery_type,
            intention=intention,
            initiator_user_id=user_id,
            status="open",
            participant_count=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return self._session_to_dict(session)

    async def list_open_sessions(
        self,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CommunityRosary)
            .where(CommunityRosary.status == "open")
            .order_by(CommunityRosary.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [self._session_to_dict(r) for r in result.scalars().all()]

    async def join_session(
        self,
        db: AsyncSession,
        rosary_id: str,
        user_id: str | None,
    ) -> dict[str, Any]:
        try:
            part = RosaryParticipation(
                id=str(uuid4()),
                rosary_id=rosary_id,
                user_id=user_id,
                decades_mask=0,
            )
            db.add(part)
            await db.execute(
                CommunityRosary.__table__.update()
                .where(CommunityRosary.id == rosary_id)
                .values(participant_count=CommunityRosary.participant_count + 1)
            )
            await db.commit()
            return {"participation_id": part.id, "joined": True}
        except IntegrityError:
            await db.rollback()
            return {"joined": False, "reason": "already_joined"}

    async def complete_decade(
        self,
        db: AsyncSession,
        participation_id: str,
        decade_number: int,  # 1–5
    ) -> dict[str, Any]:
        if decade_number < 1 or decade_number > 5:
            return {"error": "decade_number must be 1–5"}

        result = await db.execute(
            select(RosaryParticipation).where(
                RosaryParticipation.id == participation_id
            )
        )
        part = result.scalars().first()
        if not part:
            return {"error": "not_found"}

        bit = 1 << (decade_number - 1)
        new_mask = part.decades_mask | bit
        all_done = new_mask == 0b11111  # all 5 bits set

        part.decades_mask = new_mask
        if all_done:
            part.completed_at = datetime.now(timezone.utc)

        await db.commit()
        return {
            "participation_id": participation_id,
            "decades_mask": new_mask,
            "completed": all_done,
            "decades_done": bin(new_mask).count("1"),
        }

    def _session_to_dict(self, s: CommunityRosary) -> dict[str, Any]:
        return {
            "id": s.id,
            "mystery_type": s.mystery_type,
            "intention": s.intention,
            "status": s.status,
            "participant_count": s.participant_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
