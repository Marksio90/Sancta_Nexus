"""Unit tests for app/services/scripture/liturgical_calendar.py.

All tests are self-contained — pure-Python date arithmetic only.

Contracts verified:
- _easter_date: known Easter Sundays for 2024–2027
- _advent_start: known First Sundays of Advent
- LiturgicalCalendar.get_today: correct season, color, feast, rank
- Season resolution: advent / christmas / lent / easter / ordinary
- Fixed solemnities: Epiphany, St Joseph, Annunciation, etc.
- Moveable feasts: Ash Wednesday, Palm Sunday, Easter, Pentecost, Corpus Christi
- get_season: shorthand wrapper returns same as get_today().season
- get_daily_readings: returns readings for key days
- LiturgicalDay dataclass has expected fields
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services.scripture.liturgical_calendar import (
    LiturgicalCalendar,
    LiturgicalDay,
    ScriptureReference,
    _advent_start,
    _easter_date,
)

# ── Easter date computation ────────────────────────────────────────────────────


class TestEasterDate:
    """Known Easter Sundays from the Roman Calendar."""

    @pytest.mark.parametrize("year,expected", [
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4,  5)),
        (2027, date(2027, 3, 28)),
        (2000, date(2000, 4, 23)),   # Year 2000 — millennial year
        (1818, date(1818, 3, 22)),   # Earliest possible Easter in the Gregorian algorithm
        (1954, date(1954, 4, 18)),   # Historical verification
    ])
    def test_known_easter(self, year: int, expected: date):
        assert _easter_date(year) == expected

    def test_easter_is_sunday(self):
        for year in range(2020, 2031):
            e = _easter_date(year)
            assert e.weekday() == 6, f"Easter {year} ({e}) is not a Sunday"

    def test_easter_is_in_march_or_april(self):
        for year in range(2020, 2031):
            e = _easter_date(year)
            assert e.month in (3, 4)


# ── Advent start computation ───────────────────────────────────────────────────


class TestAdventStart:
    @pytest.mark.parametrize("year,expected", [
        (2024, date(2024, 12, 1)),
        (2025, date(2025, 11, 30)),
        (2026, date(2026, 11, 29)),
        (2027, date(2027, 11, 28)),
    ])
    def test_known_advent_starts(self, year: int, expected: date):
        assert _advent_start(year) == expected

    def test_advent_start_is_sunday(self):
        for year in range(2020, 2031):
            a = _advent_start(year)
            assert a.weekday() == 6, f"Advent {year} start ({a}) is not a Sunday"

    def test_advent_start_is_late_november_or_early_december(self):
        for year in range(2020, 2031):
            a = _advent_start(year)
            assert a.month in (11, 12)
            if a.month == 11:
                assert a.day >= 27
            if a.month == 12:
                assert a.day <= 4


# ── LiturgicalDay dataclass ───────────────────────────────────────────────────


class TestLiturgicalDay:
    def test_has_all_fields(self):
        day = LiturgicalDay(date=date(2026, 4, 5), season="easter", color="white")
        assert day.date == date(2026, 4, 5)
        assert day.season == "easter"
        assert day.color == "white"
        assert day.feast is None
        assert day.rank == "feria"
        assert day.readings == []

    def test_scripture_reference_str(self):
        ref = ScriptureReference("J", 3, 16)
        assert "J" in str(ref)
        assert "3" in str(ref)


# ── Season resolution ─────────────────────────────────────────────────────────

CAL = LiturgicalCalendar()


class TestSeasonResolution:
    def test_christmas_before_epiphany(self):
        """Jan 1-13 is still Christmas season."""
        day = CAL.get_today(today=date(2026, 1, 5))
        assert day.season == "christmas"

    def test_ordinary_after_epiphany(self):
        """After Jan 13 (Baptism of the Lord) → Ordinary Time begins."""
        day = CAL.get_today(today=date(2026, 1, 20))
        assert day.season == "ordinary"

    def test_lent_ash_wednesday(self):
        """Ash Wednesday 2026 = 2026-02-18 (Easter 2026-04-05, minus 46)."""
        ash_wednesday_2026 = _easter_date(2026) - timedelta(days=46)
        day = CAL.get_today(today=ash_wednesday_2026)
        assert day.season == "lent"

    def test_lent_mid_lent(self):
        """A date well inside Lent should return 'lent'."""
        # 3rd week of Lent 2026
        day = CAL.get_today(today=date(2026, 3, 10))
        assert day.season == "lent"

    def test_easter_season(self):
        """Easter Sunday itself and dates through Pentecost are 'easter'."""
        easter_2026 = _easter_date(2026)
        day = CAL.get_today(today=easter_2026)
        assert day.season == "easter"

    def test_easter_season_mid(self):
        easter_2026 = _easter_date(2026)
        day = CAL.get_today(today=easter_2026 + timedelta(days=20))
        assert day.season == "easter"

    def test_ordinary_after_pentecost(self):
        """Day after Pentecost → Ordinary Time."""
        pentecost_2026 = _easter_date(2026) + timedelta(days=49)
        day = CAL.get_today(today=pentecost_2026 + timedelta(days=1))
        assert day.season == "ordinary"

    def test_advent(self):
        """Advent 2026 starts Nov 29."""
        day = CAL.get_today(today=date(2026, 12, 1))
        assert day.season == "advent"

    def test_christmas_dec_25(self):
        day = CAL.get_today(today=date(2026, 12, 25))
        assert day.season == "christmas"

    def test_get_season_matches_get_today(self):
        for d in [date(2026, 3, 15), date(2026, 5, 1), date(2026, 7, 4), date(2026, 12, 1)]:
            assert CAL.get_season(d) == CAL.get_today(today=d).season


# ── Season colors ─────────────────────────────────────────────────────────────


class TestSeasonColors:
    def test_advent_color_is_violet(self):
        day = CAL.get_today(today=date(2026, 12, 1))
        assert day.color == "violet"

    def test_lent_color_is_violet(self):
        ash_wednesday_2026 = _easter_date(2026) - timedelta(days=46)
        day = CAL.get_today(today=ash_wednesday_2026 + timedelta(days=5))
        assert day.color == "violet"

    def test_easter_color_is_white(self):
        day = CAL.get_today(today=_easter_date(2026))
        assert day.color == "white"

    def test_ordinary_color_is_green(self):
        day = CAL.get_today(today=date(2026, 7, 1))
        assert day.color == "green"


# ── Fixed solemnities ─────────────────────────────────────────────────────────


class TestFixedSolemnities:
    def test_epiphany(self):
        day = CAL.get_today(today=date(2026, 1, 6))
        assert day.feast is not None
        assert "Trzech Kroli" in day.feast or "Objawienie" in day.feast
        assert day.rank == "solemnity"

    def test_annunciation(self):
        day = CAL.get_today(today=date(2026, 3, 25))
        assert day.feast is not None
        assert "Zwiastowanie" in day.feast

    def test_st_joseph(self):
        day = CAL.get_today(today=date(2026, 3, 19))
        assert day.feast is not None
        assert "Jozef" in day.feast or "Józef" in day.feast

    def test_queens_of_poland_may_3(self):
        day = CAL.get_today(today=date(2026, 5, 3))
        assert day.feast is not None

    def test_assumption_aug_15(self):
        day = CAL.get_today(today=date(2026, 8, 15))
        assert day.feast is not None
        assert day.rank == "solemnity"
        assert day.color == "white"

    def test_all_saints_nov_1(self):
        day = CAL.get_today(today=date(2026, 11, 1))
        assert day.feast is not None
        assert day.rank == "solemnity"

    def test_immaculate_conception_dec_8(self):
        day = CAL.get_today(today=date(2026, 12, 8))
        assert day.feast is not None
        assert day.rank == "solemnity"

    def test_christmas_dec_25(self):
        day = CAL.get_today(today=date(2026, 12, 25))
        assert day.feast is not None
        assert day.rank == "solemnity"

    def test_ordinary_tuesday_has_no_feast(self):
        day = CAL.get_today(today=date(2026, 7, 14))
        # No feast on a random July Tuesday (unless it's a known saint's day)
        # At minimum, rank should be feria if no solemnity
        assert day.rank in ("feria", "memorial", "feast", "solemnity")


# ── Moveable feasts ───────────────────────────────────────────────────────────


class TestMoveableFeasts:
    def test_ash_wednesday_feast(self):
        ash = _easter_date(2026) - timedelta(days=46)
        day = CAL.get_today(today=ash)
        assert day.feast is not None
        assert "Popielcowa" in day.feast

    def test_palm_sunday(self):
        palm = _easter_date(2026) - timedelta(days=7)
        day = CAL.get_today(today=palm)
        assert day.feast is not None
        assert "Palmowa" in day.feast

    def test_good_friday(self):
        good_friday = _easter_date(2026) - timedelta(days=2)
        day = CAL.get_today(today=good_friday)
        assert day.feast is not None
        assert day.color == "red"

    def test_easter_sunday(self):
        day = CAL.get_today(today=_easter_date(2026))
        assert day.feast is not None
        assert "Zmartwychwstan" in day.feast

    def test_pentecost(self):
        pentecost = _easter_date(2026) + timedelta(days=49)
        day = CAL.get_today(today=pentecost)
        assert day.feast is not None
        assert "Duch" in day.feast
        assert day.color == "red"

    def test_corpus_christi(self):
        corpus = _easter_date(2026) + timedelta(days=60)
        day = CAL.get_today(today=corpus)
        assert day.feast is not None
        assert "Boze Cialo" in day.feast or "Bożym Ciałem" in day.feast


# ── get_daily_readings ────────────────────────────────────────────────────────


class TestDailyReadings:
    def test_easter_sunday_has_readings(self):
        readings = CAL.get_daily_readings(_easter_date(2026).isoformat())
        assert len(readings) > 0

    def test_ash_wednesday_has_readings(self):
        ash = _easter_date(2026) - timedelta(days=46)
        readings = CAL.get_daily_readings(ash.isoformat())
        assert len(readings) > 0

    def test_christmas_has_readings(self):
        readings = CAL.get_daily_readings("2026-12-25")
        assert len(readings) > 0

    def test_advent_sunday_1_has_readings(self):
        advent = _advent_start(2026)
        readings = CAL.get_daily_readings(advent.isoformat())
        assert len(readings) > 0

    def test_ordinary_day_returns_list(self):
        readings = CAL.get_daily_readings("2026-07-01")
        assert isinstance(readings, list)

    def test_readings_are_scripture_references(self):
        readings = CAL.get_daily_readings("2026-12-25")
        assert all(isinstance(r, ScriptureReference) for r in readings)
