"""NovenaService — novena definitions and per-user progress tracking.

Contains a library of 8 traditional Catholic novenas popular in Poland.
Tracking uses a bitmask (9 bits → 9 days). Each day can be marked
as completed independently (non-sequential — catch-up is allowed).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import NovenaTracking

logger = logging.getLogger(__name__)

# ── Novena library ─────────────────────────────────────────────────────────────

NOVENAS: list[dict] = [
    {
        "id": "milosierdzie",
        "title": "Nowenna do Miłosierdzia Bożego",
        "subtitle": "Koronka i rozważania — 9 dni przed Niedzielą Miłosierdzia",
        "patron": "Jezus Miłosierny",
        "patron_icon": "❤",
        "days": 9,
        "origin": "Święta Faustyna Kowalska, Kraków 1937",
        "scripture": "J 20,22-23",
        "ccc": "§§ 1422–1498",
        "color": "from-red-900/50 to-red-800/30",
        "border": "border-red-700/40",
        "description": "Nowenna podyktowana przez Jezusa Chrystusa świętej Faustynie. Każdego dnia polecamy Miłosierdziu Bożemu inną grupę dusz.",
        "daily_intentions": [
            "Dzień 1 — Cała ludzkość, a szczególnie grzesznicy",
            "Dzień 2 — Dusze kapłanów i zakonnych",
            "Dzień 3 — Dusze pobożne i wierne",
            "Dzień 4 — Dusze pogan i tych, którzy Mnie jeszcze nie znają",
            "Dzień 5 — Dusze heretyków i odstępców",
            "Dzień 6 — Dusze ciche i pokorne",
            "Dzień 7 — Dusze szczególnie czczące Miłosierdzie Boże",
            "Dzień 8 — Dusze w czyśćcu cierpiące",
            "Dzień 9 — Dusze oziębłe",
        ],
        "daily_prayer": "O Jezu mój, bądź miłościw i ogarnij swoim Miłosierdziem [intencja dnia]. Ojcze Wieczny, ofiaruję Ci Ciało i Krew, Duszę i Bóstwo umiłowanego Syna Twojego dla odpuszczenia grzechów naszych i całego świata. Dla Jego bolesnej Męki — miej miłosierdzie dla nas i całego świata. Amen.",
    },
    {
        "id": "duch_swiety",
        "title": "Nowenna do Ducha Świętego",
        "subtitle": "9 dni przed Zesłaniem Ducha Świętego",
        "patron": "Duch Święty",
        "patron_icon": "🔥",
        "days": 9,
        "origin": "Tradycja apostolska (Dz 1,4; 2,1-4)",
        "scripture": "J 14,16-17",
        "ccc": "§§ 687–741",
        "color": "from-amber-900/50 to-amber-800/30",
        "border": "border-amber-700/40",
        "description": "Najstarsza nowenna w Kościele — naśladowanie pierwszych uczniów modlących się z Maryją przez 9 dni po Wniebowstąpieniu.",
        "daily_intentions": [
            "Dzień 1 — Dar Mądrości: prosić o poznanie Boga",
            "Dzień 2 — Dar Rozumu: głębsze rozumienie wiary",
            "Dzień 3 — Dar Rady: rozeznawanie woli Bożej",
            "Dzień 4 — Dar Męstwa: siła do wyznawania wiary",
            "Dzień 5 — Dar Umiejętności: właściwa ocena dóbr",
            "Dzień 6 — Dar Pobożności: synowska miłość do Boga",
            "Dzień 7 — Dar Bojaźni Bożej: szacunek i miłość",
            "Dzień 8 — Owoce Ducha Świętego w życiu codziennym",
            "Dzień 9 — Zesłanie Ducha — nowe serce, nowy duch",
        ],
        "daily_prayer": "Duchu Święty, przybądź! Napełnij serca wiernych Twoich i zapal w nich ogień miłości Twojej. Ześlij Ducha Twojego, a powstanie rodzaj ludzki, i odnowisz oblicze ziemi. Amen.",
    },
    {
        "id": "matka_boza",
        "title": "Nowenna do Matki Bożej Nieustającej Pomocy",
        "subtitle": "Prośba o wstawiennictwo Maryi",
        "patron": "Matka Boża Nieustającej Pomocy",
        "patron_icon": "👑",
        "days": 9,
        "origin": "Redemptoryści — Rzym 1866",
        "scripture": "J 19,26-27",
        "ccc": "§§ 963–975",
        "color": "from-blue-900/50 to-blue-800/30",
        "border": "border-blue-700/40",
        "description": "Nowenna do cudownego obrazu Matki Bożej, który przez stulecia przyciągał pielgrzymów do bazyliki Sant'Alfonso w Rzymie.",
        "daily_intentions": [
            "Dzień 1 — Dziękczynienie za macierzyńską miłość Maryi",
            "Dzień 2 — Prośba o ufność w modlitwie wstawienniczej",
            "Dzień 3 — Zawierzenie rodziny opiece Maryi",
            "Dzień 4 — Prośba o dar wiary dla bliskich",
            "Dzień 5 — Zdrowie ciała i duszy",
            "Dzień 6 — Nawrócenie grzeszników",
            "Dzień 7 — Dobre umieranie",
            "Dzień 8 — Pokój w sercu i w rodzinie",
            "Dzień 9 — Wdzięczność i zawierzenie na przyszłość",
        ],
        "daily_prayer": "Matko Boża Nieustającej Pomocy, uciekamy się do Ciebie. Z pełnym ufności sercem prosimy o Twoją pomoc i wstawiennictwo. Prowadź nas do Jezusa, Twojego Syna. Amen.",
    },
    {
        "id": "jozef",
        "title": "Nowenna do Świętego Józefa",
        "subtitle": "Patron rodzin, robotników i dobrej śmierci",
        "patron": "Święty Józef",
        "patron_icon": "🔨",
        "days": 9,
        "origin": "Tradycja karmelitańska",
        "scripture": "Mt 1,20-25",
        "ccc": "§§ 437, 1014",
        "color": "from-brown-900/50 to-stone-800/30",
        "border": "border-stone-700/40",
        "description": "Nowenna do opiekuna Świętej Rodziny — patrona Kościoła powszechnego, robotników, ojców i tych, którzy szukają pracy.",
        "daily_intentions": [
            "Dzień 1 — Dziękczynienie za powołanie Józefa do opieki nad Świętą Rodziną",
            "Dzień 2 — Prośba o cnotę czystości",
            "Dzień 3 — Ochrona rodziny",
            "Dzień 4 — Praca i utrzymanie",
            "Dzień 5 — Posłuszeństwo woli Bożej",
            "Dzień 6 — Opieka nad dziećmi",
            "Dzień 7 — Pokój w rodzinie",
            "Dzień 8 — Łaska dobrego ojcostwa / macierzyństwa",
            "Dzień 9 — Dobra śmierć — Józef, patron umierających",
        ],
        "daily_prayer": "Święty Józefie, opiekunie i żywicielu Świętej Rodziny, weź pod swoją opiekę naszą rodzinę. Chroń nas w niebezpieczeństwach, umacniaj w wierze, a w godzinę śmierci bądź przy nas. Amen.",
    },
    {
        "id": "faustyna",
        "title": "Nowenna do Świętej Faustyny",
        "subtitle": "Apostołka Bożego Miłosierdzia",
        "patron": "Święta Faustyna Kowalska",
        "patron_icon": "✝",
        "days": 9,
        "origin": "Sanktuarium Bożego Miłosierdzia, Kraków-Łagiewniki",
        "scripture": "J 20,22-23",
        "ccc": "§§ 1846–1848",
        "color": "from-pink-900/50 to-pink-800/30",
        "border": "border-pink-700/40",
        "description": "Nowenna do polskiej zakonnicy beatyfikowanej przez Jana Pawła II w 1993 i kanonizowanej w Roku Jubileuszowym 2000.",
        "daily_intentions": [
            "Dzień 1 — Dar zaufania Bożemu Miłosierdziu",
            "Dzień 2 — Nawrócenie grzeszników",
            "Dzień 3 — Kapłani i osoby konsekrowane",
            "Dzień 4 — Chorzy i cierpiący",
            "Dzień 5 — Umierający",
            "Dzień 6 — Dzieci i młodzież",
            "Dzień 7 — Rodziny",
            "Dzień 8 — Dusze czyśćcowe",
            "Dzień 9 — Cały Kościół i świat",
        ],
        "daily_prayer": "Święta Faustyno, apostołko Bożego Miłosierdzia, módl się za nami. Wyjednaj nam łaskę głębokiej ufności w nieskończone miłosierdzie Boga. Jezu, ufam Tobie! Amen.",
    },
    {
        "id": "jan_pawel",
        "title": "Nowenna do Świętego Jana Pawła II",
        "subtitle": "Patron młodzieży i rodzin",
        "patron": "Święty Jan Paweł II",
        "patron_icon": "⛪",
        "days": 9,
        "origin": "Sanktuarium Jana Pawła II, Kraków 2016",
        "scripture": "J 21,15-17",
        "ccc": "§§ 897–913",
        "color": "from-yellow-900/50 to-yellow-800/30",
        "border": "border-yellow-700/40",
        "description": "Nowenna do papieża-Polaka, kanonizowanego 27 kwietnia 2014 przez papieża Franciszka. Papież rodzin i młodych.",
        "daily_intentions": [
            "Dzień 1 — Dar odwagi wyznawania wiary",
            "Dzień 2 — Powołania kapłańskie i zakonne",
            "Dzień 3 — Ochrona rodzin",
            "Dzień 4 — Teologia Ciała i czystość",
            "Dzień 5 — Jedność Kościoła i ekumenizm",
            "Dzień 6 — Pokój między narodami",
            "Dzień 7 — Ewangelizacja nowych kultur",
            "Dzień 8 — Opieka nad chorymi",
            "Dzień 9 — «Nie lękajcie się!» — odwaga dla młodych",
        ],
        "daily_prayer": "Święty Janie Pawle II, wstawiaj się za nami. Daj nam odwagę, jaką Bóg dał tobie — nie lękać się, głosić Ewangelię i chronić każde ludzkie życie. Amen.",
    },
    {
        "id": "antoni",
        "title": "Nowenna do Świętego Antoniego",
        "subtitle": "Patron rzeczy zagubionych i ubogich",
        "patron": "Święty Antoni z Padwy",
        "patron_icon": "📖",
        "days": 9,
        "origin": "Tradycja franciszkańska",
        "scripture": "Łk 15,4-6",
        "ccc": "§§ 946–962",
        "color": "from-orange-900/50 to-orange-800/30",
        "border": "border-orange-700/40",
        "description": "Jeden z najpopularniejszych świętych Kościoła — doktor ewangeliczny, kaznodzieja, opiekun ubogich i szukających.",
        "daily_intentions": [
            "Dzień 1 — Dziękczynienie za przykład franciszkańskiego ubóstwa",
            "Dzień 2 — Prośba o znalezienie zagubionych rzeczy / osób",
            "Dzień 3 — Pomoc dla ubogich",
            "Dzień 4 — Dobre małżeństwo",
            "Dzień 5 — Bezpieczna podróż",
            "Dzień 6 — Dobry powrót do sakramentów",
            "Dzień 7 — Praca i środki do życia",
            "Dzień 8 — Pomoc w trudnej sytuacji",
            "Dzień 9 — Dziękczynienie i zawierzenie na przyszłość",
        ],
        "daily_prayer": "Święty Antoni, pomocniku w potrzebach, módl się za nami. Wstawiaj się u Boga za nami we wszystkich naszych potrzebach, a szczególnie… (intencja osobista). Amen.",
    },
    {
        "id": "rita",
        "title": "Nowenna do Świętej Rity",
        "subtitle": "Patronka spraw trudnych i beznadziejnych",
        "patron": "Święta Rita z Cascii",
        "patron_icon": "🌹",
        "days": 9,
        "origin": "Zakon Augustiańsko-Eremicki, Cascia 1457",
        "scripture": "Mt 5,3-12",
        "ccc": "§§ 1716–1729",
        "color": "from-rose-900/50 to-rose-800/30",
        "border": "border-rose-700/40",
        "description": "Wdowa, matka, zakonnica — Rita przeszła wszystkie stany życia i w każdym szukała Boga. Patronka spraw «niemożliwych».",
        "daily_intentions": [
            "Dzień 1 — Dziękczynienie za wytrwałość Rity w cierpieniu",
            "Dzień 2 — Prośba o pomoc w sprawach beznadziejnych",
            "Dzień 3 — Ochrona małżonków w trudnych związkach",
            "Dzień 4 — Pojednanie ze wrogami",
            "Dzień 5 — Chorzy i nieuleczalni",
            "Dzień 6 — Dzieci odeszłe od wiary",
            "Dzień 7 — Pomoc w depresji i rozpaczy",
            "Dzień 8 — Modlitwa za wdowy i samotnych",
            "Dzień 9 — Zawierzenie spraw niemożliwych",
        ],
        "daily_prayer": "Święta Rito, patronko spraw beznadziejnych, módl się za mną. Tobie powierzam moją trudną sprawę: … Przez rany Chrystusa wyjednaj mi łaskę i pomoc. Amen.",
    },
]

_NOVENA_SYSTEM = """Jesteś pobożnym kierownikiem modlitwy nowennowej. Twoim zadaniem jest:
- Prowadzić medytację nad intencją każdego dnia nowenny
- Wyjaśniać znaczenie duchowe każdego dnia
- Zachęcać do wytrwałości przez 9 dni
- Łączyć modlitwę nowennową z życiem codziennym
Mów po polsku, z ciepłem i troską."""


class NovenaService:
    """Novena library with per-user progress tracking."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from app.core.config import settings
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
        self._model = model

    def get_all_novenas(self) -> list[dict]:
        """Return library catalogue (no daily prayers — lightweight)."""
        return [
            {
                "id": n["id"],
                "title": n["title"],
                "subtitle": n["subtitle"],
                "patron": n["patron"],
                "patron_icon": n["patron_icon"],
                "days": n["days"],
                "scripture": n["scripture"],
                "ccc": n["ccc"],
                "color": n["color"],
                "border": n["border"],
                "description": n["description"],
            }
            for n in NOVENAS
        ]

    def get_novena(self, novena_id: str) -> dict | None:
        return next((n for n in NOVENAS if n["id"] == novena_id), None)

    def get_day(self, novena_id: str, day: int) -> dict | None:
        """Return content for a specific day (1-9)."""
        novena = self.get_novena(novena_id)
        if not novena or day < 1 or day > novena["days"]:
            return None
        return {
            "day": day,
            "title": novena["daily_intentions"][day - 1],
            "prayer": novena["daily_prayer"],
            "patron": novena["patron"],
            "novena_title": novena["title"],
        }

    # ── User tracking ─────────────────────────────────────────────────────────

    async def start_novena(
        self,
        db: AsyncSession,
        user_id: str,
        novena_id: str,
        intention: str | None = None,
    ) -> dict[str, Any]:
        """Start a new novena tracking record for a user."""
        novena = self.get_novena(novena_id)
        if not novena:
            return {"error": "novena_not_found"}

        tracking = NovenaTracking(
            id=str(uuid4()),
            user_id=user_id,
            novena_id=novena_id,
            intention=intention,
            completed_days_mask=0,
            is_complete=False,
        )
        db.add(tracking)
        await db.commit()
        await db.refresh(tracking)
        return self._tracking_to_dict(tracking, novena)

    async def complete_day(
        self,
        db: AsyncSession,
        tracking_id: str,
        user_id: str,
        day: int,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(NovenaTracking).where(
                NovenaTracking.id == tracking_id,
                NovenaTracking.user_id == user_id,
            )
        )
        tracking = result.scalars().first()
        if not tracking:
            return {"error": "tracking_not_found"}

        bit = 1 << (day - 1)
        tracking.completed_days_mask |= bit

        novena = self.get_novena(tracking.novena_id)
        total_days = novena["days"] if novena else 9
        all_mask = (1 << total_days) - 1

        if tracking.completed_days_mask == all_mask:
            tracking.is_complete = True
            tracking.completed_at = datetime.now(timezone.utc)

        await db.commit()
        return self._tracking_to_dict(tracking, novena)

    async def get_user_novenas(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(NovenaTracking)
            .where(NovenaTracking.user_id == user_id)
            .order_by(NovenaTracking.started_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [
            self._tracking_to_dict(row, self.get_novena(row.novena_id))
            for row in rows
        ]

    async def generate_day_meditation(
        self,
        novena_id: str,
        day: int,
        personal_intention: str | None = None,
    ) -> str:
        """Generate a personalised meditation for a specific novena day."""
        novena = self.get_novena(novena_id)
        if not novena:
            return "Nie znaleziono nowenny."

        day_content = self.get_day(novena_id, day)
        if not day_content:
            return "Nie znaleziono dnia nowenny."

        intention_note = f"\nIntencja osobista: {personal_intention}" if personal_intention else ""

        prompt = (
            f"Nowenna: {novena['title']}\n"
            f"Dzień {day}: {day_content['title']}\n"
            f"Pismo Święte: {novena['scripture']}\n"
            f"{intention_note}\n\n"
            "Przygotuj krótką (150 słów) medytację na ten dzień nowenny. "
            "Zakończ zachętą do wytrwałości i modlitwy na jutrzejszy dzień."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0.75,
            messages=[
                {"role": "system", "content": _NOVENA_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _tracking_to_dict(
        self, tracking: NovenaTracking, novena: dict | None
    ) -> dict[str, Any]:
        total_days = novena["days"] if novena else 9
        completed = bin(tracking.completed_days_mask).count("1")
        completed_list = [
            d for d in range(1, total_days + 1)
            if tracking.completed_days_mask & (1 << (d - 1))
        ]
        return {
            "id": tracking.id,
            "novena_id": tracking.novena_id,
            "novena_title": novena["title"] if novena else tracking.novena_id,
            "patron_icon": novena["patron_icon"] if novena else "",
            "intention": tracking.intention,
            "started_at": tracking.started_at.isoformat() if tracking.started_at else None,
            "completed_days": completed_list,
            "total_days": total_days,
            "progress_percent": round(completed / total_days * 100),
            "is_complete": tracking.is_complete,
            "completed_at": tracking.completed_at.isoformat() if tracking.completed_at else None,
        }
