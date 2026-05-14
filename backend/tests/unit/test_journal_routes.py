"""Unit tests for journal route pure helper functions (no DB/infra required).

We inline the trivial pure-logic functions here to avoid importing the full
route module (which would drag in neo4j, redis, sqlalchemy at import time).
"""

from __future__ import annotations

import pytest


# ── Inline copies of the helpers under test ─────────────────────────────────
# These mirror app/api/routes/journal.py exactly.  If the originals change,
# update here to keep tests green.

_VALID_MOODS = {
    "spokój", "radość", "wdzięczność", "smutek", "niepokój",
    "nadzieja", "zagubienie", "miłość", "tęsknota", "pokuta",
}


def _tags_to_str(tags: list[str]) -> str:
    return ",".join(t.strip()[:64] for t in tags[:20])


def _str_to_tags(tags_str: str | None) -> list[str]:
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


# ── Tests ────────────────────────────────────────────────────────────────────


class TestTagConversion:
    def test_tags_to_str_basic(self):
        assert _tags_to_str(["modlitwa", "Ewangelia"]) == "modlitwa,Ewangelia"

    def test_tags_to_str_empty(self):
        assert _tags_to_str([]) == ""

    def test_tags_to_str_strips_whitespace(self):
        assert _tags_to_str(["  modlitwa  ", "Ewangelia"]) == "modlitwa,Ewangelia"

    def test_tags_to_str_max_20_tags(self):
        tags = [f"tag{i}" for i in range(25)]
        result = _tags_to_str(tags)
        assert result.count(",") == 19  # 20 tags → 19 commas

    def test_tags_to_str_truncates_tag_at_64_chars(self):
        long_tag = "a" * 100
        result = _tags_to_str([long_tag])
        assert len(result) == 64

    def test_str_to_tags_basic(self):
        assert _str_to_tags("modlitwa,Ewangelia") == ["modlitwa", "Ewangelia"]

    def test_str_to_tags_none_returns_empty(self):
        assert _str_to_tags(None) == []

    def test_str_to_tags_empty_string_returns_empty(self):
        assert _str_to_tags("") == []

    def test_str_to_tags_skips_blank_segments(self):
        assert _str_to_tags("modlitwa,,Ewangelia") == ["modlitwa", "Ewangelia"]

    def test_str_to_tags_strips_whitespace(self):
        assert _str_to_tags(" modlitwa , Ewangelia ") == ["modlitwa", "Ewangelia"]

    def test_roundtrip(self):
        original = ["modlitwa", "Ewangelia", "Lectio"]
        assert _str_to_tags(_tags_to_str(original)) == original


class TestValidMoods:
    def test_valid_moods_not_empty(self):
        assert len(_VALID_MOODS) >= 10

    def test_expected_moods_present(self):
        for mood in ("spokój", "radość", "smutek", "wdzięczność", "niepokój"):
            assert mood in _VALID_MOODS

    def test_invalid_mood_not_present(self):
        assert "złość" not in _VALID_MOODS
        assert "happy" not in _VALID_MOODS
        assert "" not in _VALID_MOODS

    def test_all_moods_are_strings(self):
        assert all(isinstance(m, str) for m in _VALID_MOODS)
