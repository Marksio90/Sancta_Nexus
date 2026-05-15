"""Unit tests for Ignatian Examen constants from app/api/routes/examen.py.

No HTTP, no DB, no LLM — pure data-layer testing.

Contracts verified:
DISCLAIMER:
- Is the canonical mission-constraint disclaimer
- Mentions kapłana, spowiednika, kierownika duchowego, terapeuty

EXAMEN_PHASES:
- Exactly 5 phases (Ignatian 5-point examen)
- Specific phases present: gratitude, petition, review, response, resolution
- Correct Ignatian order
- No duplicates
- All are non-empty strings

PHASE_META:
- Exactly 5 entries — one per phase
- Keys match EXAMEN_PHASES
- All entries have: title, subtitle, icon, prompt_intro
- All Polish titles present (Wdzięczność/Prośba o światło/Przegląd dnia/
  Odpowiedź serca/Postanowienie na jutro)
- All prompt_intros are non-empty Polish strings (> 50 chars)
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in ["neo4j", "qdrant_client", "qdrant_client.models",
             "jose", "jose.jwt", "jose.exceptions"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.examen import DISCLAIMER, EXAMEN_PHASES, PHASE_META

_REQUIRED_PHASE_KEYS = {"title", "subtitle", "icon", "prompt_intro"}
_EXPECTED_ORDER = ["gratitude", "petition", "review", "response", "resolution"]


# ===========================================================================
# DISCLAIMER
# ===========================================================================


class TestExamenDisclaimer:
    def test_non_empty(self):
        assert len(DISCLAIMER.strip()) > 30

    def test_is_string(self):
        assert isinstance(DISCLAIMER, str)

    def test_mentions_asystent_refleksji(self):
        assert "Asystent refleksji" in DISCLAIMER

    def test_mentions_kaplana(self):
        assert "kapłana" in DISCLAIMER

    def test_mentions_spowiednika(self):
        assert "spowiednika" in DISCLAIMER

    def test_mentions_kierownika_duchowego(self):
        assert "kierownika duchowego" in DISCLAIMER

    def test_mentions_terapeuty(self):
        assert "terapeuty" in DISCLAIMER

    def test_canonical_phrase(self):
        # Exact mission-constraint phrase must be present verbatim
        assert "Nie zastępuje kapłana" in DISCLAIMER


# ===========================================================================
# EXAMEN_PHASES
# ===========================================================================


class TestExamenPhases:
    def test_exactly_5_phases(self):
        assert len(EXAMEN_PHASES) == 5

    def test_gratitude_present(self):
        assert "gratitude" in EXAMEN_PHASES

    def test_petition_present(self):
        assert "petition" in EXAMEN_PHASES

    def test_review_present(self):
        assert "review" in EXAMEN_PHASES

    def test_response_present(self):
        assert "response" in EXAMEN_PHASES

    def test_resolution_present(self):
        assert "resolution" in EXAMEN_PHASES

    def test_all_expected_phases(self):
        assert set(EXAMEN_PHASES) == set(_EXPECTED_ORDER)

    def test_ignatian_order(self):
        assert list(EXAMEN_PHASES) == _EXPECTED_ORDER

    def test_no_duplicates(self):
        assert len(EXAMEN_PHASES) == len(set(EXAMEN_PHASES))

    def test_all_are_strings(self):
        for phase in EXAMEN_PHASES:
            assert isinstance(phase, str), f"Phase {phase!r} is not a string"

    def test_all_non_empty(self):
        for phase in EXAMEN_PHASES:
            assert phase.strip(), "Empty phase found"


# ===========================================================================
# PHASE_META
# ===========================================================================


class TestPhaseMeta:
    def test_exactly_5_entries(self):
        assert len(PHASE_META) == 5

    def test_keys_match_phases(self):
        assert set(PHASE_META.keys()) == set(EXAMEN_PHASES)

    def test_all_have_required_keys(self):
        for phase, meta in PHASE_META.items():
            missing = _REQUIRED_PHASE_KEYS - set(meta.keys())
            assert not missing, f"{phase} missing keys: {missing}"

    def test_all_titles_non_empty(self):
        for phase, meta in PHASE_META.items():
            assert meta["title"].strip(), f"{phase} has empty title"

    def test_all_subtitles_non_empty(self):
        for phase, meta in PHASE_META.items():
            assert meta["subtitle"].strip(), f"{phase} has empty subtitle"

    def test_all_icons_non_empty(self):
        for phase, meta in PHASE_META.items():
            assert meta["icon"].strip(), f"{phase} has empty icon"

    def test_all_prompt_intros_substantial(self):
        for phase, meta in PHASE_META.items():
            assert len(meta["prompt_intro"]) > 50, (
                f"{phase} prompt_intro too short: {meta['prompt_intro']!r}"
            )

    # Polish title checks
    def test_gratitude_title(self):
        assert "Wdzięczność" in PHASE_META["gratitude"]["title"]

    def test_petition_title(self):
        assert "światło" in PHASE_META["petition"]["title"]

    def test_review_title(self):
        assert "Przegląd" in PHASE_META["review"]["title"]

    def test_response_title(self):
        assert "serca" in PHASE_META["response"]["title"]

    def test_resolution_title(self):
        assert "Postanowienie" in PHASE_META["resolution"]["title"]

    def test_prompt_intros_are_polish(self):
        # All Polish prompts must contain Polish-specific characters
        combined = " ".join(m["prompt_intro"] for m in PHASE_META.values())
        polish_chars = set("ąęółśźżćń")
        assert any(ch in combined for ch in polish_chars), (
            "No Polish characters found in prompt_intros"
        )
