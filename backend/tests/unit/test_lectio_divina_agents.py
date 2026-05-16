"""Unit tests for Lectio Divina agents (A-010 through A-014).

All four agents have pure-logic static/instance methods that are tested
without LLM calls:
  - LectioAgent (A-010): FALLBACK_PASSAGES, _get_fallback, _extract_recent_passages,
    _resolve_liturgical_season, _parse_json, _EMOTION_FALLBACK_MAP
  - MeditatioAgent (A-011): FALLBACK_MEDITATION, _parse_json
  - ContemplatioAgent (A-013): FALLBACK_CONTEMPLATION, _SEASON_AMBIENT,
    _validate_breathing, _parse_json, _get_seasonal_fallback
  - ActioAgent (A-014): FALLBACK_ACTION, _assess_difficulty, _format_reflection,
    _parse_json

All agents bypass __init__ to avoid LLM initialisation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.lectio_divina.actio_agent import (
    FALLBACK_ACTION,
    ActioAgent,
)
from app.agents.lectio_divina.contemplatio_agent import (
    _SEASON_AMBIENT,
    FALLBACK_CONTEMPLATION,
    ContemplatioAgent,
)
from app.agents.lectio_divina.lectio_agent import (
    _EMOTION_FALLBACK_MAP,
    FALLBACK_PASSAGES,
    LectioAgent,
)
from app.agents.lectio_divina.meditatio_agent import (
    FALLBACK_MEDITATION,
    MeditatioAgent,
)

# ---------------------------------------------------------------------------
# Helpers — bypass __init__ for all agents
# ---------------------------------------------------------------------------

def _lectio() -> LectioAgent:
    svc = LectioAgent.__new__(LectioAgent)
    svc._llm = None
    svc._uniqueness = MagicMock()
    return svc


def _meditatio() -> MeditatioAgent:
    svc = MeditatioAgent.__new__(MeditatioAgent)
    svc._llm = None
    return svc


def _contemplatio() -> ContemplatioAgent:
    svc = ContemplatioAgent.__new__(ContemplatioAgent)
    svc._llm = None
    return svc


def _actio() -> ActioAgent:
    svc = ActioAgent.__new__(ActioAgent)
    svc._llm = None
    return svc


# ===========================================================================
# LectioAgent (A-010)
# ===========================================================================


class TestFallbackPassages:
    def test_has_five_keys(self):
        assert set(FALLBACK_PASSAGES.keys()) == {
            "consolation", "desolation", "hope", "dark_night", "gratitude"
        }

    def test_each_passage_has_required_fields(self):
        required = {"book", "chapter", "verse_start", "verse_end", "text", "translation"}
        for key, passage in FALLBACK_PASSAGES.items():
            assert required <= set(passage.keys()), f"{key} missing required fields"

    def test_consolation_is_john(self):
        assert "J" in FALLBACK_PASSAGES["consolation"]["book_abbrev"]

    def test_all_passages_have_historical_context(self):
        for key, passage in FALLBACK_PASSAGES.items():
            assert passage.get("historical_context", "").strip(), f"{key} missing historical_context"

    def test_all_chapters_are_positive(self):
        for key, passage in FALLBACK_PASSAGES.items():
            assert passage["chapter"] > 0, f"{key} chapter should be positive"


class TestEmotionFallbackMap:
    def test_joy_maps_to_gratitude(self):
        assert _EMOTION_FALLBACK_MAP["joy"] == "gratitude"

    def test_sadness_maps_to_desolation(self):
        assert _EMOTION_FALLBACK_MAP["sadness"] == "desolation"

    def test_loneliness_maps_to_dark_night(self):
        assert _EMOTION_FALLBACK_MAP["loneliness"] == "dark_night"

    def test_hope_maps_to_hope(self):
        assert _EMOTION_FALLBACK_MAP["hope"] == "hope"

    def test_all_map_values_are_valid_passage_keys(self):
        valid = set(FALLBACK_PASSAGES.keys())
        for emotion, category in _EMOTION_FALLBACK_MAP.items():
            assert category in valid, f"emotion '{emotion}' maps to unknown '{category}'"


class TestLectioGetFallback:
    def test_joy_returns_gratitude_passage(self):
        result = LectioAgent._get_fallback({"joy": 0.8, "sadness": 0.2})
        expected = FALLBACK_PASSAGES["gratitude"]
        assert result["book"] == expected["book"]

    def test_sadness_returns_desolation_passage(self):
        result = LectioAgent._get_fallback({"sadness": 0.9})
        expected = FALLBACK_PASSAGES["desolation"]
        assert result["chapter"] == expected["chapter"]

    def test_unknown_emotion_returns_consolation(self):
        result = LectioAgent._get_fallback({"neutral": 1.0})
        assert result["book"] == FALLBACK_PASSAGES["consolation"]["book"]

    def test_returns_copy_not_original(self):
        result = LectioAgent._get_fallback({"joy": 1.0})
        result["injected"] = True
        assert "injected" not in FALLBACK_PASSAGES["gratitude"]

    def test_dark_night_emotion(self):
        result = LectioAgent._get_fallback({"guilt": 0.7, "shame": 0.3})
        assert result["book"] == FALLBACK_PASSAGES["dark_night"]["book"]


class TestLectioExtractRecentPassages:
    def test_extracts_passages_from_history(self):
        history = [
            {"scripture": {"book": "J", "chapter": 1, "verse_start": 1}},
            {"scripture": {"book": "Ps", "chapter": 23, "verse_start": 1}},
        ]
        result = LectioAgent._extract_recent_passages(history)
        assert "J 1:1" in result
        assert "Ps 23:1" in result

    def test_empty_history_returns_empty(self):
        assert LectioAgent._extract_recent_passages([]) == []

    def test_session_without_scripture_skipped(self):
        history = [{"no_scripture": True}, {"scripture": {"book": "Rz", "chapter": 8, "verse_start": 28}}]
        result = LectioAgent._extract_recent_passages(history)
        assert len(result) == 1

    def test_respects_max_recent_limit(self):
        history = [
            {"scripture": {"book": "J", "chapter": i, "verse_start": 1}}
            for i in range(30)
        ]
        result = LectioAgent._extract_recent_passages(history, max_recent=5)
        assert len(result) == 5

    def test_skips_entries_without_book(self):
        history = [{"scripture": {"chapter": 1, "verse_start": 1}}]  # no book
        result = LectioAgent._extract_recent_passages(history)
        assert result == []


class TestLectioResolveLiturgicalSeason:
    def test_explicit_season_in_context(self):
        ctx = {"season": "lent", "color": "purple"}
        assert LectioAgent._resolve_liturgical_season(ctx) == "lent"

    def test_none_context_returns_string(self):
        result = LectioAgent._resolve_liturgical_season(None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_context_without_season_returns_string(self):
        result = LectioAgent._resolve_liturgical_season({"color": "green"})
        assert isinstance(result, str)


class TestLectioParseJson:
    def test_valid_json(self):
        raw = '{"book": "J", "chapter": 1}'
        result = LectioAgent._parse_json(raw)
        assert result["book"] == "J"

    def test_json_in_prose(self):
        raw = 'Here is the result: {"book": "Ps", "chapter": 23} done.'
        result = LectioAgent._parse_json(raw)
        assert result["book"] == "Ps"

    def test_unparseable_returns_empty_dict(self):
        result = LectioAgent._parse_json("not json at all")
        assert result == {}


# ===========================================================================
# MeditatioAgent (A-011)
# ===========================================================================


class TestFallbackMeditation:
    def test_has_questions_list(self):
        assert isinstance(FALLBACK_MEDITATION["questions"], list)
        assert len(FALLBACK_MEDITATION["questions"]) >= 4

    def test_questions_have_text_and_layer(self):
        for q in FALLBACK_MEDITATION["questions"]:
            assert "text" in q
            assert "layer" in q

    def test_has_all_four_quadriga_layers(self):
        layers = {q["layer"] for q in FALLBACK_MEDITATION["questions"]}
        assert layers == {"literalis", "allegoricus", "moralis", "anagogicus"}

    def test_reflection_layers_has_four_keys(self):
        layers = FALLBACK_MEDITATION["reflection_layers"]
        assert set(layers.keys()) == {"literalis", "allegoricus", "moralis", "anagogicus"}

    def test_patristic_insight_present(self):
        assert "patristic_insight" in FALLBACK_MEDITATION
        assert len(FALLBACK_MEDITATION["patristic_insight"]) > 20

    def test_key_word_present(self):
        assert FALLBACK_MEDITATION["key_word"].strip()


class TestMeditatioParseJson:
    def test_valid_json(self):
        raw = '{"questions": [], "key_word": "milosc"}'
        result = MeditatioAgent._parse_json(raw)
        assert result["key_word"] == "milosc"

    def test_json_in_prose(self):
        raw = 'Output: {"questions": ["Q1"]} end'
        result = MeditatioAgent._parse_json(raw)
        assert "questions" in result

    def test_unparseable_returns_fallback(self):
        result = MeditatioAgent._parse_json("definitely not json")
        assert "questions" in result  # returns FALLBACK_MEDITATION


# ===========================================================================
# ContemplatioAgent (A-013)
# ===========================================================================


class TestFallbackContemplation:
    def test_has_guidance_text(self):
        assert FALLBACK_CONTEMPLATION["guidance_text"].strip()

    def test_has_sacred_word(self):
        assert FALLBACK_CONTEMPLATION["sacred_word"].strip()

    def test_has_breathing_pattern(self):
        bp = FALLBACK_CONTEMPLATION["breathing_pattern"]
        assert "inhale_seconds" in bp
        assert "exhale_seconds" in bp
        assert "cycles" in bp

    def test_default_breathing_sane_values(self):
        bp = FALLBACK_CONTEMPLATION["breathing_pattern"]
        assert 2 <= bp["inhale_seconds"] <= 8
        assert 3 <= bp["exhale_seconds"] <= 10
        assert bp["cycles"] >= 1

    def test_has_duration_minutes(self):
        assert FALLBACK_CONTEMPLATION["duration_minutes"] > 0

    def test_has_closing_prayer(self):
        assert "Amen" in FALLBACK_CONTEMPLATION["closing_prayer"]


class TestSeasonAmbient:
    def test_advent_is_silence(self):
        assert _SEASON_AMBIENT["advent"] == "silence"

    def test_easter_is_gregorian_chant(self):
        assert _SEASON_AMBIENT["easter"] == "gregorian_chant"

    def test_lent_is_silence(self):
        assert _SEASON_AMBIENT["lent"] == "silence"

    def test_ordinary_has_value(self):
        assert _SEASON_AMBIENT["ordinary"].strip()

    def test_has_5_seasons(self):
        assert len(_SEASON_AMBIENT) == 5


class TestContemplatioValidateBreathing:
    def test_valid_breathing_passthrough(self):
        bp = {"inhale_seconds": 4, "hold_seconds": 4, "exhale_seconds": 6, "cycles": 3}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result == bp

    def test_clamps_inhale_too_high(self):
        bp = {"inhale_seconds": 20, "hold_seconds": 0, "exhale_seconds": 6, "cycles": 3}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["inhale_seconds"] == 8

    def test_clamps_inhale_too_low(self):
        bp = {"inhale_seconds": 1, "hold_seconds": 0, "exhale_seconds": 5, "cycles": 3}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["inhale_seconds"] == 2

    def test_clamps_exhale_too_low(self):
        bp = {"inhale_seconds": 4, "hold_seconds": 0, "exhale_seconds": 1, "cycles": 3}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["exhale_seconds"] == 3

    def test_clamps_cycles_to_min_1(self):
        bp = {"inhale_seconds": 4, "hold_seconds": 0, "exhale_seconds": 6, "cycles": 0}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["cycles"] == 1

    def test_clamps_cycles_to_max_10(self):
        bp = {"inhale_seconds": 4, "hold_seconds": 0, "exhale_seconds": 6, "cycles": 99}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["cycles"] == 10

    def test_hold_clamped_to_max_7(self):
        bp = {"inhale_seconds": 4, "hold_seconds": 10, "exhale_seconds": 6, "cycles": 3}
        result = ContemplatioAgent._validate_breathing(bp)
        assert result["hold_seconds"] == 7


class TestContemplatioGetSeasonalFallback:
    def test_known_season_adds_ambient(self):
        agent = _contemplatio()
        result = agent._get_seasonal_fallback("advent")
        assert result["ambient_suggestion"] == "silence"

    def test_easter_season_ambient(self):
        agent = _contemplatio()
        result = agent._get_seasonal_fallback("easter")
        assert result["ambient_suggestion"] == "gregorian_chant"

    def test_unknown_season_uses_fallback_ambient(self):
        agent = _contemplatio()
        result = agent._get_seasonal_fallback("unknown_season")
        assert "ambient_suggestion" in result

    def test_returns_dict_with_guidance_text(self):
        agent = _contemplatio()
        result = agent._get_seasonal_fallback("lent")
        assert result["guidance_text"].strip()


class TestContemplatioParseJson:
    def test_valid_json(self):
        raw = '{"guidance_text": "Cisza.", "sacred_word": "Milosc"}'
        result = ContemplatioAgent._parse_json(raw)
        assert result["sacred_word"] == "Milosc"

    def test_unparseable_returns_fallback(self):
        result = ContemplatioAgent._parse_json("no json here")
        assert "guidance_text" in result


# ===========================================================================
# ActioAgent (A-014)
# ===========================================================================


class TestFallbackAction:
    def test_has_challenge_text(self):
        assert FALLBACK_ACTION["challenge_text"].strip()

    def test_has_difficulty(self):
        assert FALLBACK_ACTION["difficulty"] in {"easy", "medium", "hard", "divine"}

    def test_has_category(self):
        assert FALLBACK_ACTION["category"].strip()

    def test_has_virtue_focus(self):
        assert "virtue_focus" in FALLBACK_ACTION

    def test_has_evening_examen(self):
        examen = FALLBACK_ACTION["evening_examen"]
        assert "retrospection" in examen
        assert "divine_presence" in examen
        assert "resolution" in examen

    def test_has_scripture_anchor(self):
        assert "scripture_anchor" in FALLBACK_ACTION


class TestActioAssessDifficulty:
    def test_0_sessions_is_easy(self):
        assert ActioAgent._assess_difficulty(0) == "easy"

    def test_19_sessions_is_easy(self):
        assert ActioAgent._assess_difficulty(19) == "easy"

    def test_20_sessions_is_medium(self):
        assert ActioAgent._assess_difficulty(20) == "medium"

    def test_39_sessions_is_medium(self):
        assert ActioAgent._assess_difficulty(39) == "medium"

    def test_40_sessions_is_hard(self):
        assert ActioAgent._assess_difficulty(40) == "hard"

    def test_59_sessions_is_hard(self):
        assert ActioAgent._assess_difficulty(59) == "hard"

    def test_60_sessions_is_divine(self):
        assert ActioAgent._assess_difficulty(60) == "divine"

    def test_100_sessions_is_divine(self):
        assert ActioAgent._assess_difficulty(100) == "divine"


class TestActioFormatReflection:
    def test_empty_reflection_returns_fallback(self):
        result = ActioAgent._format_reflection({})
        assert result == "brak refleksji"

    def test_questions_as_strings(self):
        reflection = {"questions": ["Pytanie 1?", "Pytanie 2?"]}
        result = ActioAgent._format_reflection(reflection)
        assert "Pytanie 1?" in result
        assert "Pytanie 2?" in result

    def test_questions_as_dicts(self):
        reflection = {"questions": [{"text": "Q dict format?"}, {"text": "Second?"}]}
        result = ActioAgent._format_reflection(reflection)
        assert "Q dict format?" in result

    def test_includes_reflection_layers(self):
        reflection = {
            "questions": ["Q1?"],
            "reflection_layers": {"moralis": "Wezwanie moralne...", "literalis": "Sens literalny..."},
        }
        result = ActioAgent._format_reflection(reflection)
        assert "moralis" in result
        assert "Wezwanie moralne" in result

    def test_numbered_questions(self):
        reflection = {"questions": ["Alpha?", "Beta?", "Gamma?"]}
        result = ActioAgent._format_reflection(reflection)
        assert "1." in result
        assert "2." in result
        assert "3." in result


class TestActioParseJson:
    def test_valid_json(self):
        raw = '{"challenge_text": "Modlić się.", "difficulty": "easy"}'
        result = ActioAgent._parse_json(raw)
        assert result["difficulty"] == "easy"

    def test_json_in_prose(self):
        raw = 'Oto wynik: {"challenge_text": "Działaj.", "category": "charity"} koniec.'
        result = ActioAgent._parse_json(raw)
        assert result["category"] == "charity"

    def test_unparseable_returns_fallback(self):
        result = ActioAgent._parse_json("completely invalid")
        assert result["challenge_text"] == FALLBACK_ACTION["challenge_text"]
