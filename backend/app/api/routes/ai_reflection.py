"""AI Reflection — unique, liturgically-aware content generated fresh on every call.

Endpoint: GET /api/v1/ai/reflection/daily
Returns a unique scripture verse + brief meditation, never from a static pool.
Uses get_llm_fast with high temperature for variety.
"""
from __future__ import annotations

import datetime
import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.llm import get_llm_fast
from app.core.rbac import require_authenticated
from app.models.database import User

logger = logging.getLogger(__name__)
router = APIRouter()

_DAY_NAMES = {
    0: "poniedziałek", 1: "wtorek", 2: "środa",
    3: "czwartek", 4: "piątek", 5: "sobota", 6: "niedziela",
}

_FALLBACK = {
    "verse": "Pan jest blisko ludzi skruszonych w sercu, ocala złamanych na duchu.",
    "ref": "Ps 34,19",
    "reflection": "Bóg nie czeka na naszą doskonałość — przychodzi właśnie wtedy, gdy jesteśmy kruchy. To nie słabość nas oddala od Niego, lecz pycha.",
}


class DailyReflectionResponse(BaseModel):
    verse: str
    ref: str
    reflection: str


@router.get("/daily", response_model=DailyReflectionResponse)
async def get_daily_reflection(
    _current_user: User = require_authenticated,
) -> DailyReflectionResponse:
    """Generate a unique AI-crafted scripture verse + meditation for today.

    Every call produces fresh content — no static pool, no random selection.
    LLM temperature is set high (0.9) for variety.
    """
    today = datetime.date.today()
    day_name = _DAY_NAMES[today.weekday()]
    hour = datetime.datetime.now().hour
    time_context = "ranek" if hour < 12 else ("południe" if hour < 17 else "wieczór")

    llm = get_llm_fast(temperature=0.9)

    prompt = (
        f"Jesteś głęboko wykształconym teologiem katolickim i towarzyszem duchowym.\n"
        f"Dzisiaj: {day_name}, {today.strftime('%d.%m.%Y')}, {time_context}.\n\n"
        f"Wybierz JEDEN werset biblijny — musi być:\n"
        f"- nieoczywisty (unikaj Ps 23, J 3,16, Mt 6,33, Flp 4,13 i innych popularnych)\n"
        f"- adekwatny do pory dnia i dnia tygodnia\n"
        f"- z różnych ksiąg (prorockie, mądrościowe, Listy, Ewangelie — rotuj)\n\n"
        f"Napisz krótką, KONKRETNĄ medytację (2-3 zdania) — nie ogólną, lecz ostrą jak brzytwa.\n\n"
        f"Odpowiedź WYŁĄCZNIE jako JSON (bez markdown, bez komentarzy):\n"
        f'{{\"verse\": \"...\", \"ref\": \"...\", \"reflection\": \"...\"}}'
    )

    try:
        msg = await llm.ainvoke(prompt)
        raw = msg.content.strip()
        # Strip optional markdown fences
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else parts[0]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return DailyReflectionResponse(
            verse=str(data.get("verse", _FALLBACK["verse"])),
            ref=str(data.get("ref", _FALLBACK["ref"])),
            reflection=str(data.get("reflection", _FALLBACK["reflection"])),
        )
    except Exception:
        logger.exception("Daily reflection generation failed — serving fallback")
        return DailyReflectionResponse(**_FALLBACK)
