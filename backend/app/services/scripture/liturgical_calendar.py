"""Liturgical calendar service.

Provides current liturgical season, feast days and daily readings based
on the Roman Rite calendar.  This is a self-contained basic implementation
that covers the major seasons and solemnities; a production deployment
would integrate with an external liturgical API or a comprehensive
date-table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScriptureReference:
    """A pointer to a specific scripture passage."""

    book: str
    chapter: int
    verse_start: int
    verse_end: int | None = None
    label: str = ""  # e.g. "First Reading", "Gospel"

    def __str__(self) -> str:
        ref = f"{self.book} {self.chapter},{self.verse_start}"
        if self.verse_end and self.verse_end != self.verse_start:
            ref += f"-{self.verse_end}"
        return ref


@dataclass
class LiturgicalDay:
    """Full description of a single liturgical day."""

    date: date
    season: str
    color: str
    feast: str | None = None
    rank: str = "feria"  # feria | memorial | feast | solemnity
    readings: list[ScriptureReference] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Key-date helpers
# ---------------------------------------------------------------------------


def _easter_date(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _advent_start(year: int) -> date:
    """First Sunday of Advent (4th Sunday before 25 Dec)."""
    christmas = date(year, 12, 25)
    # Sunday before or on Christmas
    days_to_sunday = (christmas.weekday() + 1) % 7  # Mon=0 in Python
    fourth_sunday_before = christmas - timedelta(days=days_to_sunday + 21)
    return fourth_sunday_before


# ---------------------------------------------------------------------------
# Fixed solemnities (month, day) -> (name, readings)
# ---------------------------------------------------------------------------

_FIXED_SOLEMNITIES: dict[tuple[int, int], dict[str, Any]] = {
    # January
    (1, 1): {
        "feast": "Uroczystosc Swietej Bozej Rodzicielki Maryi",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Lb 6,22-27", "Ga 4,4-7", "Lk 2,16-21"],
    },
    (1, 6): {
        "feast": "Objawienie Panskie (Trzech Kroli)",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Iz 60,1-6", "Ef 3,2-3a.5-6", "Mt 2,1-12"],
    },
    # February
    (2, 2): {
        "feast": "Ofiarowanie Panskie (Swieto Matki Bozej Gromnicznej)",
        "rank": "feast",
        "color": "white",
        "readings": ["Ml 3,1-4", "Hbr 2,14-18", "Lk 2,22-40"],
    },
    (2, 11): {
        "feast": "NMP z Lourdes (Swiatowy Dzien Chorego)",
        "rank": "memorial",
        "color": "white",
    },
    # March
    (3, 19): {
        "feast": "Uroczystosc sw. Jozefa, Oblubienka NMP",
        "rank": "solemnity",
        "color": "white",
        "readings": ["2 Sm 7,4-5a.12-14a.16", "Rz 4,13.16-18.22", "Mt 1,16.18-21.24a"],
    },
    (3, 25): {
        "feast": "Zwiastowanie Panskie",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Iz 7,10-14", "Hbr 10,4-10", "Lk 1,26-38"],
    },
    # May
    (5, 3): {
        "feast": "NMP Krolowa Polski",
        "rank": "solemnity",
        "color": "white",
    },
    (5, 13): {
        "feast": "NMP Fatimska",
        "rank": "memorial",
        "color": "white",
    },
    (5, 31): {
        "feast": "Nawiedzenie NMP",
        "rank": "feast",
        "color": "white",
        "readings": ["So 3,14-18", "Rz 12,9-16", "Lk 1,39-56"],
    },
    # June
    (6, 24): {
        "feast": "Narodzenie sw. Jana Chrzciciela",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Iz 49,1-6", "Dz 13,22-26", "Lk 1,57-66.80"],
    },
    (6, 29): {
        "feast": "Uroczystosc sw. Piotra i Pawla",
        "rank": "solemnity",
        "color": "red",
        "readings": ["Dz 12,1-11", "2 Tm 4,6-8.17-18", "Mt 16,13-19"],
    },
    # July
    (7, 16): {
        "feast": "NMP z Gory Karmel (Szkaplerzna)",
        "rank": "memorial",
        "color": "white",
    },
    # August
    (8, 6): {
        "feast": "Przemienienie Panskie",
        "rank": "feast",
        "color": "white",
        "readings": ["Dn 7,9-10.13-14", "2 P 1,16-19", "Mt 17,1-9"],
    },
    (8, 15): {
        "feast": "Wniebowziecie NMP",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Ap 11,19a;12,1-6a.10ab", "1 Kor 15,20-27a", "Lk 1,39-56"],
    },
    (8, 22): {
        "feast": "NMP Krolowa",
        "rank": "memorial",
        "color": "white",
    },
    # September
    (9, 8): {
        "feast": "Narodzenie NMP",
        "rank": "feast",
        "color": "white",
        "readings": ["Mi 5,1-4a", "Rz 8,28-30", "Mt 1,1-16.18-23"],
    },
    (9, 12): {
        "feast": "Najswietszego Imienia Maryi",
        "rank": "memorial",
        "color": "white",
    },
    (9, 15): {
        "feast": "NMP Bolesnej",
        "rank": "memorial",
        "color": "white",
        "readings": ["Hbr 5,7-9", "J 19,25-27"],
    },
    (9, 29): {
        "feast": "Swietych Archaniolow Michala, Gabriela i Rafala",
        "rank": "feast",
        "color": "white",
    },
    # October
    (10, 7): {
        "feast": "NMP Rozancowej",
        "rank": "memorial",
        "color": "white",
    },
    # November
    (11, 1): {
        "feast": "Uroczystosc Wszystkich Swietych",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Ap 7,2-4.9-14", "1 J 3,1-3", "Mt 5,1-12a"],
    },
    (11, 2): {
        "feast": "Wspomnienie Wszystkich Wiernych Zmarlych",
        "rank": "feast",
        "color": "violet",
    },
    (11, 21): {
        "feast": "Ofiarowanie NMP",
        "rank": "memorial",
        "color": "white",
    },
    # December
    (12, 8): {
        "feast": "Niepokalane Poczecie NMP",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Rdz 3,9-15.20", "Ef 1,3-6.11-12", "Lk 1,26-38"],
    },
    (12, 12): {
        "feast": "NMP z Guadalupe",
        "rank": "memorial",
        "color": "white",
    },
    (12, 25): {
        "feast": "Boze Narodzenie",
        "rank": "solemnity",
        "color": "white",
        "readings": ["Iz 9,1-6", "Tt 2,11-14", "Lk 2,1-14"],
    },
}

# Liturgical colours per season
_SEASON_COLORS: dict[str, str] = {
    "advent": "violet",
    "christmas": "white",
    "lent": "violet",
    "easter": "white",
    "ordinary": "green",
}

# ---------------------------------------------------------------------------
# Sample daily readings (abbreviated for key days)
# ---------------------------------------------------------------------------

_SAMPLE_READINGS: dict[str, list[ScriptureReference]] = {
    "advent_sunday_1": [
        ScriptureReference("Iz", 2, 1, 5, label="Pierwsze Czytanie"),
        ScriptureReference("Rz", 13, 11, 14, label="Drugie Czytanie"),
        ScriptureReference("Mt", 24, 37, 44, label="Ewangelia"),
    ],
    "christmas": [
        ScriptureReference("Iz", 9, 1, 6, label="Pierwsze Czytanie"),
        ScriptureReference("Tt", 2, 11, 14, label="Drugie Czytanie"),
        ScriptureReference("Łk", 2, 1, 14, label="Ewangelia"),
    ],
    "ash_wednesday": [
        ScriptureReference("Jl", 2, 12, 18, label="Pierwsze Czytanie"),
        ScriptureReference("2 Kor", 5, 20, 6, label="Drugie Czytanie"),
        ScriptureReference("Mt", 6, 1, 6, label="Ewangelia"),
    ],
    "easter_sunday": [
        ScriptureReference("Dz", 10, 34, 43, label="Pierwsze Czytanie"),
        ScriptureReference("Kol", 3, 1, 4, label="Drugie Czytanie"),
        ScriptureReference("J", 20, 1, 9, label="Ewangelia"),
    ],
}


# ---------------------------------------------------------------------------
# LiturgicalCalendar
# ---------------------------------------------------------------------------


class LiturgicalCalendar:
    """Provides liturgical season, feast days and daily readings.

    This implementation covers the core Roman Rite calendar.  It
    resolves the season for any given date, checks for fixed
    solemnities, and provides sample readings for key days.
    """

    def get_today(self, today: date | None = None) -> LiturgicalDay:
        """Return liturgical information for today (or a given date).

        Args:
            today: Override date (defaults to ``date.today()``).

        Returns:
            A :class:`LiturgicalDay` instance.
        """
        today = today or date.today()
        season = self._resolve_season(today)
        color = _SEASON_COLORS.get(season, "green")

        # Check fixed solemnities
        key = (today.month, today.day)
        solemnity = _FIXED_SOLEMNITIES.get(key)
        feast: str | None = None
        rank = "feria"
        if solemnity:
            feast = solemnity["feast"]
            rank = solemnity["rank"]
            color = solemnity["color"]

        # Check moveable feasts
        moveable = self._check_moveable(today)
        if moveable:
            feast = moveable.get("feast", feast)
            rank = moveable.get("rank", rank)
            color = moveable.get("color", color)

        readings = self._resolve_readings(today, season)

        return LiturgicalDay(
            date=today,
            season=season,
            color=color,
            feast=feast,
            rank=rank,
            readings=readings,
        )

    def get_daily_readings(self, date_str: str) -> list[ScriptureReference]:
        """Return the readings for a given date string (``YYYY-MM-DD``).

        Args:
            date_str: ISO-format date string.

        Returns:
            List of :class:`ScriptureReference` for that day.
        """
        d = date.fromisoformat(date_str)
        day = self.get_today(today=d)
        return day.readings

    def get_season(self, today: date | None = None) -> str:
        """Return the current liturgical season name.

        Returns one of: ``advent``, ``christmas``, ``lent``,
        ``easter``, ``ordinary``.
        """
        today = today or date.today()
        return self._resolve_season(today)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_season(self, d: date) -> str:
        """Determine the liturgical season for *d*."""
        year = d.year
        easter = _easter_date(year)

        # Ash Wednesday = Easter - 46 days
        ash_wednesday = easter - timedelta(days=46)
        # Pentecost = Easter + 49 days
        pentecost = easter + timedelta(days=49)

        advent_start = _advent_start(year)
        christmas = date(year, 12, 25)

        # Check previous year's Christmas season carrying into Jan
        prev_epiphany_end = date(year, 1, 13)  # approx baptism of the Lord
        if d <= prev_epiphany_end:
            return "christmas"

        if advent_start <= d < christmas:
            return "advent"

        if d >= christmas:
            return "christmas"

        if ash_wednesday <= d < easter:
            return "lent"

        if easter <= d <= pentecost:
            return "easter"

        return "ordinary"

    def _check_moveable(self, d: date) -> dict[str, str] | None:
        """Check whether *d* is a moveable feast."""
        year = d.year
        easter = _easter_date(year)

        moveable_feasts: dict[date, dict[str, str]] = {
            easter - timedelta(days=46): {
                "feast": "Sroda Popielcowa",
                "rank": "feria",
                "color": "violet",
            },
            easter - timedelta(days=7): {
                "feast": "Niedziela Palmowa",
                "rank": "solemnity",
                "color": "red",
            },
            easter - timedelta(days=3): {
                "feast": "Wielki Czwartek",
                "rank": "solemnity",
                "color": "white",
            },
            easter - timedelta(days=2): {
                "feast": "Wielki Piatek",
                "rank": "solemnity",
                "color": "red",
            },
            easter - timedelta(days=1): {
                "feast": "Wielka Sobota",
                "rank": "solemnity",
                "color": "white",
            },
            easter: {
                "feast": "Niedziela Zmartwychwstania",
                "rank": "solemnity",
                "color": "white",
            },
            easter + timedelta(days=39): {
                "feast": "Wniebowstapienie Panskie",
                "rank": "solemnity",
                "color": "white",
            },
            easter + timedelta(days=49): {
                "feast": "Zeslanie Ducha Swietego",
                "rank": "solemnity",
                "color": "red",
            },
            easter + timedelta(days=60): {
                "feast": "Boze Cialo",
                "rank": "solemnity",
                "color": "white",
            },
        }

        return moveable_feasts.get(d)

    def _resolve_readings(self, d: date, season: str) -> list[ScriptureReference]:
        """Return readings for the given date.

        This is a simplified implementation; a production system would
        load the full lectionary.
        """
        year = d.year
        easter = _easter_date(year)

        if d == easter:
            return list(_SAMPLE_READINGS.get("easter_sunday", []))
        if d == easter - timedelta(days=46):
            return list(_SAMPLE_READINGS.get("ash_wednesday", []))
        if d.month == 12 and d.day == 25:
            return list(_SAMPLE_READINGS.get("christmas", []))
        if d == _advent_start(year):
            return list(_SAMPLE_READINGS.get("advent_sunday_1", []))

        # Default: empty (would be populated from a full lectionary DB)
        return []
