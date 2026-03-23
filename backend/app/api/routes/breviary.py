"""Breviary / Liturgy of Hours API routes.

Returns the current liturgical season and structured hour prayer data
for Lauds, Vespers, and Compline.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter

from app.services.scripture.liturgical_calendar import (
    LiturgicalDay,
    LiturgicalCalendar,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Static hour data (Roman Rite, simplified Polish texts)
# ---------------------------------------------------------------------------

_HOURS: dict[str, dict[str, Any]] = {
    "lauds": {
        "name": "Jutrznia",
        "latin": "Laudes",
        "time": "Poranna modlitwa — o wschodzie słońca",
        "opening": "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
        "psalm_ref": "Ps 63,2-9",
        "psalm_text": (
            "Boże, Ty Boże mój, szukam Cię\n"
            "i pragnie Ciebie moja dusza.\n"
            "Ciało moje tęskni za Tobą,\n"
            "jak ziemia zeschła, spragniona, bez wody.\n\n"
            "Oglądałem Cię w świątyni,\n"
            "patrząc na Twoją potęgę i chwałę.\n"
            "Twoja łaska jest cenniejsza od życia,\n"
            "moje wargi będą Cię sławiły."
        ),
        "reading": "Wielka jest Twoja miłość, która ocaliła mnie od przepaści zagłady.",
        "reading_ref": "Iz 38,17",
        "responsory": "Usta moje będą głosiły chwałę Twoją. — Alleluja, alleluja.",
        "canticle": "Błogosławiony Pan, Bóg Izraela, bo nawiedził i wyzwolił swój lud.",
        "canticle_ref": "Łk 1,68-79 (Benedictus)",
        "closing": (
            "Panie, rozkaż, aby Twoi aniołowie strzegli nas przez cały dzień. "
            "Prowadź nas dziś, byśmy żyli w zgodzie z Twoją wolą."
        ),
    },
    "vespers": {
        "name": "Nieszpory",
        "latin": "Vesperae",
        "time": "Wieczorna modlitwa — o zachodzie słońca",
        "opening": "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
        "psalm_ref": "Ps 141,2-4",
        "psalm_text": (
            "Niech moja modlitwa dotrze przed oblicze Twoje\n"
            "jak kadzidło;\n"
            "niech moje wzniesione dłonie będą\n"
            "jak ofiara wieczorna.\n\n"
            "Panie, postaw straż przy moich ustach,\n"
            "strzeż bramy moich warg!\n"
            "Niech serce moje nie skłania się ku złemu\n"
            "i niech nie popełniam czynów bezbożnych."
        ),
        "reading": "Jak kadzidło niech wznosi się moja modlitwa ku Tobie.",
        "reading_ref": "Ps 141,2",
        "responsory": "Niech Pan nas błogosławi i strzeże. — Niech swoje oblicze skieruje ku nam.",
        "canticle": "Wielbi dusza moja Pana i raduje się duch mój w Bogu, moim Zbawcy.",
        "canticle_ref": "Łk 1,46-55 (Magnificat)",
        "closing": (
            "Chroń nas, Panie, gdy czuwamy, strzeż nas, kiedy śpimy, "
            "abyśmy czuwali z Chrystusem i spoczywali w pokoju."
        ),
    },
    "compline": {
        "name": "Kompleta",
        "latin": "Completorium",
        "time": "Modlitwa na zakończenie dnia — przed snem",
        "opening": "Boże, wejrzyj ku wspomożeniu memu. Panie, pospiesz ku ratunkowi memu.",
        "psalm_ref": "Ps 91,1-4",
        "psalm_text": (
            "Kto przebywa w pieczy Najwyższego\n"
            "i mieszka w cieniu Wszechmocnego,\n"
            "mówi do Pana: «Ucieczko moja i twierdzo,\n"
            "mój Boże, któremu zaufałem».\n\n"
            "On sam wyzwoli cię z sideł myśliwego\n"
            "i od słowa zatrutego.\n"
            "Swoim piórami cię okryje,\n"
            "pod Jego skrzydłami znajdziesz schronienie."
        ),
        "reading": (
            "Bądźcie trzeźwi i czuwajcie! Przeciwnik wasz, diabeł, "
            "jak lew ryczący krąży szukając kogo pożreć."
        ),
        "reading_ref": "1 P 5,8",
        "responsory": (
            "W ręce Twoje, Panie, oddaję ducha mego. "
            "— Ty nas odkupiłeś, Panie, Boże wierny."
        ),
        "canticle": (
            "Teraz, o Władco, pozwól odejść słudze Twemu w pokoju, "
            "według Twojego słowa. Bo moje oczy ujrzały Twoje zbawienie."
        ),
        "canticle_ref": "Łk 2,29-32 (Nunc Dimittis)",
        "closing": (
            "Pokój wam wszystkim, którzy trwacie w Chrystusie. "
            "Niech Bóg miłości i pokoju będzie z wami."
        ),
    },
}

_SEASON_LABELS: dict[str, str] = {
    "advent": "Adwent",
    "christmas": "Boże Narodzenie",
    "lent": "Wielki Post",
    "easter": "Wielkanoc",
    "ordinary": "Zwykły",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/today")
async def get_today_breviary() -> dict[str, Any]:
    """Return today's liturgical info and all three canonical hours."""
    cal = LiturgicalCalendar()
    today = date.today()
    liturgical_day: LiturgicalDay = cal.get_today(today=today)

    return {
        "date": today.isoformat(),
        "season": liturgical_day.season,
        "season_label": _SEASON_LABELS.get(liturgical_day.season, liturgical_day.season),
        "color": liturgical_day.color,
        "feast": liturgical_day.feast,
        "rank": liturgical_day.rank,
        "hours": _HOURS,
    }


@router.get("/season")
async def get_current_season() -> dict[str, Any]:
    """Return only the current liturgical season (lightweight)."""
    cal = LiturgicalCalendar()
    today = date.today()
    liturgical_day: LiturgicalDay = cal.get_today(today=today)

    return {
        "season": liturgical_day.season,
        "label": _SEASON_LABELS.get(liturgical_day.season, liturgical_day.season),
        "color": liturgical_day.color,
        "feast": liturgical_day.feast,
    }


@router.get("/hours/{hour_id}")
async def get_hour(hour_id: str) -> dict[str, Any]:
    """Return a specific canonical hour (lauds | vespers | compline)."""
    if hour_id not in _HOURS:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hour '{hour_id}' not found. Valid: lauds, vespers, compline",
        )
    return _HOURS[hour_id]
