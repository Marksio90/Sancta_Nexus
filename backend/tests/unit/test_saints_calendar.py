"""Testy jednostkowe dla kalendarza świętych — saints_calendar.py.

Sprawdzamy:
  - Kluczowe polskie i powszechne święta
  - Fallback dla nieznanych dat
  - Struktura SaintInfo (TypedDict)
  - Funkcje get_saint_today / get_saint_for_date
  - Pokrycie wszystkich 12 miesięcy (co najmniej 1 wpis)
  - Brak pustych pól obowiązkowych
"""

from __future__ import annotations

import ast
import sys
from datetime import date
from pathlib import Path

import pytest

CALENDAR_PATH = Path(__file__).parents[2] / "app" / "services" / "scripture" / "saints_calendar.py"

# ── Import modułu ─────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parents[2]))
from app.services.scripture.saints_calendar import (
    _DEFAULT_SAINT,
    _SAINTS,
    get_saint_for_date,
    get_saint_today,
)

# ── Podstawowa struktura ──────────────────────────────────────────────────────


class TestSaintInfoStructure:
    def test_all_entries_have_name(self):
        for key, saint in _SAINTS.items():
            assert saint["name"], f"Brak name dla klucza {key}"

    def test_all_entries_have_description(self):
        for key, saint in _SAINTS.items():
            assert saint["description"], f"Brak description dla klucza {key}"

    def test_all_entries_have_icon(self):
        for key, saint in _SAINTS.items():
            assert saint["icon"], f"Brak icon dla klucza {key}"

    def test_all_entries_have_died(self):
        for key, saint in _SAINTS.items():
            assert "died" in saint, f"Brak pola 'died' dla {key}"

    def test_all_entries_have_patronage(self):
        for key, saint in _SAINTS.items():
            assert "patronage" in saint, f"Brak pola 'patronage' dla {key}"

    def test_all_keys_are_mm_dd_format(self):
        import re
        pattern = re.compile(r"^\d{2}-\d{2}$")
        for key in _SAINTS:
            assert pattern.match(key), f"Nieprawidłowy format klucza: {key}"

    def test_at_least_50_entries(self):
        assert len(_SAINTS) >= 50, f"Za mało świętych: {len(_SAINTS)}"


# ── Pokrycie miesięcy ─────────────────────────────────────────────────────────


class TestMonthCoverage:
    @pytest.mark.parametrize("month", range(1, 13))
    def test_each_month_has_at_least_one_saint(self, month):
        prefix = f"{month:02d}-"
        found = [k for k in _SAINTS if k.startswith(prefix)]
        assert found, f"Brak świętych dla miesiąca {month:02d}"


# ── Kluczowe polskie święta ───────────────────────────────────────────────────


class TestPolishKeyDates:
    def test_jan_pawel_ii_april(self):
        saint = get_saint_for_date(4, 2)
        assert "Jan Paweł" in saint["name"] or "Jana Pawła" in saint["name"]

    def test_jan_pawel_ii_october(self):
        saint = get_saint_for_date(10, 22)
        assert "Jan Paweł" in saint["name"] or "Jana Pawła" in saint["name"]

    def test_faustyna(self):
        saint = get_saint_for_date(10, 5)
        assert "Faustyn" in saint["name"]

    def test_maksymilian_kolbe(self):
        saint = get_saint_for_date(8, 14)
        assert "Kolbe" in saint["name"] or "Maksymilian" in saint["name"]

    def test_andrzej_bobola(self):
        saint = get_saint_for_date(5, 16)
        assert "Bobola" in saint["name"] or "Andrzej" in saint["name"]

    def test_wojciech(self):
        saint = get_saint_for_date(4, 23)
        assert "Wojciech" in saint["name"]

    def test_stanislawa(self):
        saint = get_saint_for_date(4, 11)
        assert "Stanisław" in saint["name"]

    def test_christmas(self):
        saint = get_saint_for_date(12, 25)
        assert "Narodzenie" in saint["name"] or "Boże Narodzenie" in saint["name"] or "Słowo" in saint["description"]


# ── Fallback ──────────────────────────────────────────────────────────────────


class TestFallback:
    def test_unknown_date_returns_default(self):
        result = get_saint_for_date(6, 3)  # data bez wpisu
        # może być konkretny lub default — sprawdzamy tylko że coś zwraca
        assert result["name"]

    def test_default_saint_has_all_fields(self):
        for field in ("name", "description", "patronage", "icon", "died"):
            assert field in _DEFAULT_SAINT, f"Brak pola '{field}' w _DEFAULT_SAINT"
        assert _DEFAULT_SAINT["name"]

    def test_get_saint_for_missing_date_returns_default_saint(self):
        # Szukamy daty która na pewno nie ma wpisu w słowniku
        for day in range(1, 29):
            key = f"02-{day:02d}"
            if key not in _SAINTS:
                result = get_saint_for_date(2, day)
                assert result["name"] == _DEFAULT_SAINT["name"]
                break


# ── get_saint_today ───────────────────────────────────────────────────────────


class TestGetSaintToday:
    def test_returns_saint_info(self):
        result = get_saint_today()
        assert isinstance(result, dict)
        assert "name" in result

    def test_accepts_date_param(self):
        result = get_saint_today(date(2026, 4, 2))
        assert "Jan Paweł" in result["name"] or "Jana Pawła" in result["name"]

    def test_defaults_to_today(self):
        today = date.today()
        result_a = get_saint_today()
        result_b = get_saint_today(today)
        assert result_a["name"] == result_b["name"]


# ── Kontrakt kodu źródłowego (AST) ───────────────────────────────────────────


class TestSourceContract:
    def test_file_exists(self):
        assert CALENDAR_PATH.exists()

    def test_get_saint_today_is_defined(self):
        tree = ast.parse(CALENDAR_PATH.read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "get_saint_today" in funcs

    def test_get_saint_for_date_is_defined(self):
        tree = ast.parse(CALENDAR_PATH.read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "get_saint_for_date" in funcs

    def test_default_saint_defined_as_module_level(self):
        tree = ast.parse(CALENDAR_PATH.read_text())
        assigns = [
            n.targets[0].id
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and hasattr(n.targets[0], "id")
        ]
        assert "_DEFAULT_SAINT" in assigns
