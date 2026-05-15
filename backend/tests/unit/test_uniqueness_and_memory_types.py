"""Unit tests for ContentUniquenessEngine and SpiritualMemoryGraph data types.

All tests are pure-Python, no DB, no LLM, no Neo4j.

Contracts verified:
ContentUniquenessEngine:
- CANON_OT: 46 books (full Catholic OT including deuterocanonicals)
- CANON_NT: 27 books
- FULL_CANON: 73 books, OT + NT
- KERYGMATIC_THEMES: 8 pillars, required fields, all key_passages non-empty
- SEASON_SCRIPTURE_WEIGHTS: advent/christmas/lent/easter/ordinary keys,
  ordinary == FULL_CANON
- EMOTION_SCRIPTURE_MAP: core emotions present, each with ≥ 3 passages
- compute_daily_seed: deterministic, same user+day→same seed,
  different day→different, different user→different, integer result
- get_kerygmatic_theme: valid keys, index in range, personalised offset varies
- suggest_books: ordered list, only books from FULL_CANON,
  emotion books appear early, recent books penalised
- suggest_tradition: returns one of the 7 known traditions,
  least-used tradition preferred
- suggest_action_category: returns one of 10 works-of-mercy categories,
  least-used preferred
- build_session_context: all required keys present, date is today ISO format,
  suggested_books limited to 10

SpiritualMemoryGraph data types:
- NodeType: 10 values, expected values present
- RelationType: 8 values, expected values present
- SessionData: required fields, optional defaults
- Pattern: required fields, strength default 0.0
- Theme: required fields, optional defaults
- JourneyGraph: required fields, list defaults
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.services.content.uniqueness_engine import (
    CANON_NT,
    CANON_OT,
    EMOTION_SCRIPTURE_MAP,
    FULL_CANON,
    KERYGMATIC_THEMES,
    SEASON_SCRIPTURE_WEIGHTS,
    ContentUniquenessEngine,
)
from app.services.memory.spiritual_memory_graph import (
    JourneyGraph,
    NodeType,
    Pattern,
    RelationType,
    SessionData,
    Theme,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _engine() -> ContentUniquenessEngine:
    return ContentUniquenessEngine()


_USER = "user-abc-123"
_TODAY = date(2026, 5, 15)


# ===========================================================================
# Canon constants
# ===========================================================================


class TestCanon:
    def test_ot_count(self):
        assert len(CANON_OT) == 46

    def test_nt_count(self):
        assert len(CANON_NT) == 27

    def test_full_canon_count(self):
        assert len(FULL_CANON) == 73

    def test_full_canon_is_ot_plus_nt(self):
        assert FULL_CANON == CANON_OT + CANON_NT

    def test_no_duplicates_in_ot(self):
        assert len(CANON_OT) == len(set(CANON_OT))

    def test_no_duplicates_in_nt(self):
        assert len(CANON_NT) == len(set(CANON_NT))

    def test_no_duplicates_in_full(self):
        assert len(FULL_CANON) == len(set(FULL_CANON))

    def test_pentateuch_present(self):
        for book in ("Rdz", "Wj", "Kpl", "Lb", "Pwt"):
            assert book in CANON_OT

    def test_deuterocanonical_ot_present(self):
        for book in ("Tb", "Jdt", "1 Mch", "2 Mch", "Mdr", "Syr", "Ba"):
            assert book in CANON_OT

    def test_psalms_in_ot(self):
        assert "Ps" in CANON_OT

    def test_gospels_in_nt(self):
        for book in ("Mt", "Mk", "Lk", "J"):
            assert book in CANON_NT

    def test_revelation_in_nt(self):
        assert "Ap" in CANON_NT

    def test_pauline_epistles_in_nt(self):
        for book in ("Rz", "1 Kor", "2 Kor", "Ga", "Ef"):
            assert book in CANON_NT


# ===========================================================================
# Kerygmatic themes
# ===========================================================================


class TestKerygmaticThemes:
    def test_exactly_8_themes(self):
        assert len(KERYGMATIC_THEMES) == 8

    def test_all_have_required_fields(self):
        required = {"theme", "label", "key_passages", "catechism_refs"}
        for t in KERYGMATIC_THEMES:
            assert required <= set(t.keys()), f"Missing fields in {t.get('theme')}"

    def test_all_labels_non_empty(self):
        for t in KERYGMATIC_THEMES:
            assert t["label"].strip()

    def test_all_have_key_passages(self):
        for t in KERYGMATIC_THEMES:
            assert len(t["key_passages"]) >= 3

    def test_all_have_ccc_refs(self):
        for t in KERYGMATIC_THEMES:
            assert len(t["catechism_refs"]) >= 1

    def test_creatio_present(self):
        themes = [t["theme"] for t in KERYGMATIC_THEMES]
        assert "creatio" in themes

    def test_incarnatio_present(self):
        themes = [t["theme"] for t in KERYGMATIC_THEMES]
        assert "incarnatio" in themes

    def test_mysterium_paschale_present(self):
        themes = [t["theme"] for t in KERYGMATIC_THEMES]
        assert "mysterium_paschale" in themes

    def test_eschaton_present(self):
        themes = [t["theme"] for t in KERYGMATIC_THEMES]
        assert "eschaton" in themes

    def test_all_theme_ids_unique(self):
        theme_ids = [t["theme"] for t in KERYGMATIC_THEMES]
        assert len(theme_ids) == len(set(theme_ids))


# ===========================================================================
# Liturgical season weights
# ===========================================================================


class TestSeasonWeights:
    def test_has_5_seasons(self):
        assert len(SEASON_SCRIPTURE_WEIGHTS) == 5

    def test_advent_present(self):
        assert "advent" in SEASON_SCRIPTURE_WEIGHTS

    def test_christmas_present(self):
        assert "christmas" in SEASON_SCRIPTURE_WEIGHTS

    def test_lent_present(self):
        assert "lent" in SEASON_SCRIPTURE_WEIGHTS

    def test_easter_present(self):
        assert "easter" in SEASON_SCRIPTURE_WEIGHTS

    def test_ordinary_present(self):
        assert "ordinary" in SEASON_SCRIPTURE_WEIGHTS

    def test_ordinary_is_full_canon(self):
        assert SEASON_SCRIPTURE_WEIGHTS["ordinary"] is FULL_CANON

    def test_advent_contains_isaiah(self):
        assert "Iz" in SEASON_SCRIPTURE_WEIGHTS["advent"]

    def test_lent_contains_psalms(self):
        assert "Ps" in SEASON_SCRIPTURE_WEIGHTS["lent"]

    def test_easter_contains_acts(self):
        assert "Dz" in SEASON_SCRIPTURE_WEIGHTS["easter"]

    def test_all_season_entries_are_book_abbreviations(self):
        for season, books in SEASON_SCRIPTURE_WEIGHTS.items():
            if season == "ordinary":
                continue
            for book in books:
                assert book in FULL_CANON, f"{book!r} from {season} not in canon"


# ===========================================================================
# Emotion → Scripture map
# ===========================================================================


class TestEmotionScriptureMap:
    def test_ignatian_states_present(self):
        for state in ("consolation", "desolation", "dark_night"):
            assert state in EMOTION_SCRIPTURE_MAP

    def test_core_emotions_present(self):
        for emotion in ("joy", "sadness", "fear", "guilt", "hope", "peace"):
            assert emotion in EMOTION_SCRIPTURE_MAP

    def test_each_has_at_least_3_passages(self):
        for emotion, passages in EMOTION_SCRIPTURE_MAP.items():
            assert len(passages) >= 3, f"{emotion} has fewer than 3 passages"

    def test_all_passages_have_book_chapter(self):
        for emotion, passages in EMOTION_SCRIPTURE_MAP.items():
            for p in passages:
                assert len(p.split()) >= 2, f"Passage {p!r} in {emotion} malformed"

    def test_psalm_51_in_guilt(self):
        assert any("Ps 51" in p for p in EMOTION_SCRIPTURE_MAP["guilt"])

    def test_1_cor_13_in_love(self):
        assert any("1 Kor 13" in p for p in EMOTION_SCRIPTURE_MAP["love"])


# ===========================================================================
# compute_daily_seed
# ===========================================================================


class TestComputeDailySeed:
    def test_returns_integer(self):
        seed = ContentUniquenessEngine.compute_daily_seed(_USER, _TODAY)
        assert isinstance(seed, int)

    def test_deterministic_same_user_same_day(self):
        s1 = ContentUniquenessEngine.compute_daily_seed(_USER, _TODAY)
        s2 = ContentUniquenessEngine.compute_daily_seed(_USER, _TODAY)
        assert s1 == s2

    def test_different_day_different_seed(self):
        tomorrow = _TODAY + timedelta(days=1)
        s1 = ContentUniquenessEngine.compute_daily_seed(_USER, _TODAY)
        s2 = ContentUniquenessEngine.compute_daily_seed(_USER, tomorrow)
        assert s1 != s2

    def test_different_user_different_seed(self):
        s1 = ContentUniquenessEngine.compute_daily_seed("user-A", _TODAY)
        s2 = ContentUniquenessEngine.compute_daily_seed("user-B", _TODAY)
        assert s1 != s2

    def test_positive_integer(self):
        seed = ContentUniquenessEngine.compute_daily_seed(_USER, _TODAY)
        assert seed > 0


# ===========================================================================
# get_kerygmatic_theme
# ===========================================================================


class TestGetKerygmaticTheme:
    def test_returns_dict_with_theme_key(self):
        engine = _engine()
        result = engine.get_kerygmatic_theme(_USER, _TODAY)
        assert "theme" in result

    def test_theme_is_valid(self):
        engine = _engine()
        result = engine.get_kerygmatic_theme(_USER, _TODAY)
        valid_themes = {t["theme"] for t in KERYGMATIC_THEMES}
        assert result["theme"] in valid_themes

    def test_has_all_required_keys(self):
        engine = _engine()
        result = engine.get_kerygmatic_theme(_USER, _TODAY)
        assert "label" in result
        assert "key_passages" in result
        assert "catechism_refs" in result

    def test_different_users_may_have_different_themes(self):
        engine = _engine()
        themes = {
            engine.get_kerygmatic_theme(f"user-{i}", _TODAY)["theme"]
            for i in range(10)
        }
        # With 8 themes and 10 users, we should see at least 2 distinct themes
        assert len(themes) >= 2

    def test_cycle_days_parameter(self):
        engine = _engine()
        # With cycle_days=1, different users at different offsets should cover many themes
        themes = {
            engine.get_kerygmatic_theme(_USER, _TODAY + timedelta(days=i), cycle_days=1)["theme"]
            for i in range(16)
        }
        assert len(themes) >= 2


# ===========================================================================
# suggest_books
# ===========================================================================


class TestSuggestBooks:
    def test_returns_list(self):
        engine = _engine()
        result = engine.suggest_books(_USER, "ordinary", "peace", today=_TODAY)
        assert isinstance(result, list)

    def test_all_books_in_full_canon(self):
        engine = _engine()
        result = engine.suggest_books(_USER, "lent", "sadness", today=_TODAY)
        for book in result:
            assert book in FULL_CANON

    def test_no_duplicates(self):
        engine = _engine()
        result = engine.suggest_books(_USER, "easter", "joy", today=_TODAY)
        assert len(result) == len(set(result))

    def test_all_canon_books_included(self):
        engine = _engine()
        result = engine.suggest_books(_USER, "ordinary", "peace", today=_TODAY)
        assert len(result) == len(FULL_CANON)

    def test_emotion_books_score_high(self):
        engine = _engine()
        # "guilt" maps to Ps 51, 1 J 1,9, Rz 8,1-2 — so "Ps", "1 J", "Rz" should appear early
        result = engine.suggest_books(_USER, "ordinary", "guilt", today=_TODAY)
        guilt_books = {p.split()[0] for p in EMOTION_SCRIPTURE_MAP["guilt"]}
        top_10 = set(result[:15])
        # At least some emotion-related books should appear in the top 15
        assert len(top_10 & guilt_books) >= 1

    def test_recent_book_penalised(self):
        engine = _engine()
        history = [{"scripture": {"book": "Ps"}} for _ in range(5)]
        result_with_history = engine.suggest_books(_USER, "ordinary", "peace", history, _TODAY)
        result_no_history = engine.suggest_books(_USER, "ordinary", "peace", None, _TODAY)
        ps_rank_with = result_with_history.index("Ps")
        ps_rank_without = result_no_history.index("Ps")
        # With heavy Ps history it should rank lower (higher index)
        assert ps_rank_with > ps_rank_without

    def test_deterministic_same_day(self):
        engine = _engine()
        r1 = engine.suggest_books(_USER, "lent", "fear", today=_TODAY)
        r2 = engine.suggest_books(_USER, "lent", "fear", today=_TODAY)
        assert r1 == r2


# ===========================================================================
# suggest_tradition
# ===========================================================================


_TRADITIONS = ["ignatian", "carmelite", "franciscan", "benedictine",
               "charismatic", "dominican", "marian"]


class TestSuggestTradition:
    def test_returns_valid_tradition(self):
        result = ContentUniquenessEngine.suggest_tradition(_USER, today=_TODAY)
        assert result in _TRADITIONS

    def test_with_empty_history(self):
        result = ContentUniquenessEngine.suggest_tradition(_USER, [], _TODAY)
        assert result in _TRADITIONS

    def test_overused_tradition_not_returned_if_others_available(self):
        # Fill history with ignatian x many times
        history = [{"prayer": {"tradition": "ignatian"}} for _ in range(10)]
        # other traditions have 0 count — should not return ignatian
        result = ContentUniquenessEngine.suggest_tradition(_USER, history, _TODAY)
        assert result != "ignatian"

    def test_deterministic_same_day(self):
        r1 = ContentUniquenessEngine.suggest_tradition(_USER, today=_TODAY)
        r2 = ContentUniquenessEngine.suggest_tradition(_USER, today=_TODAY)
        assert r1 == r2


# ===========================================================================
# suggest_action_category
# ===========================================================================


_ACTION_CATEGORIES = [
    "prayer", "charity", "relationship", "service", "gratitude",
    "forgiveness", "self_care", "teaching", "counsel", "patience",
]


class TestSuggestActionCategory:
    def test_returns_valid_category(self):
        result = ContentUniquenessEngine.suggest_action_category(_USER, today=_TODAY)
        assert result in _ACTION_CATEGORIES

    def test_overused_category_avoided(self):
        history = [{"action": {"category": "prayer"}} for _ in range(15)]
        result = ContentUniquenessEngine.suggest_action_category(_USER, history, _TODAY)
        assert result != "prayer"

    def test_deterministic(self):
        r1 = ContentUniquenessEngine.suggest_action_category(_USER, today=_TODAY)
        r2 = ContentUniquenessEngine.suggest_action_category(_USER, today=_TODAY)
        assert r1 == r2


# ===========================================================================
# build_session_context
# ===========================================================================


class TestBuildSessionContext:
    def test_returns_all_required_keys(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "lent", "sadness", today=_TODAY)
        required = {
            "daily_seed", "kerygmatic_theme", "suggested_books",
            "suggested_tradition", "suggested_action_category",
            "emotion_passages", "season", "date",
        }
        assert required <= set(ctx.keys())

    def test_suggested_books_limited_to_10(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "easter", "joy", today=_TODAY)
        assert len(ctx["suggested_books"]) == 10

    def test_date_is_today_iso(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "ordinary", "peace", today=_TODAY)
        assert ctx["date"] == _TODAY.isoformat()

    def test_season_preserved(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "advent", "longing", today=_TODAY)
        assert ctx["season"] == "advent"

    def test_emotion_passages_from_map(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "ordinary", "fear", today=_TODAY)
        assert ctx["emotion_passages"] == EMOTION_SCRIPTURE_MAP["fear"]

    def test_unknown_emotion_returns_empty_passages(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "ordinary", "unknown_emotion", today=_TODAY)
        assert ctx["emotion_passages"] == []

    def test_daily_seed_is_integer(self):
        engine = _engine()
        ctx = engine.build_session_context(_USER, "ordinary", "joy", today=_TODAY)
        assert isinstance(ctx["daily_seed"], int)


# ===========================================================================
# SpiritualMemoryGraph data types
# ===========================================================================


class TestNodeType:
    def test_exactly_10_values(self):
        assert len(NodeType) == 10

    def test_emotional_state(self):
        assert NodeType.EMOTIONAL_STATE == "EmotionalState"

    def test_spiritual_state(self):
        assert NodeType.SPIRITUAL_STATE == "SpiritualState"

    def test_scripture_encounter(self):
        assert NodeType.SCRIPTURE_ENCOUNTER == "ScriptureEncounter"

    def test_prayer(self):
        assert NodeType.PRAYER == "Prayer"

    def test_life_event(self):
        assert NodeType.LIFE_EVENT == "LifeEvent"

    def test_grace_note(self):
        assert NodeType.GRACE_NOTE == "GraceNote"

    def test_dark_night(self):
        assert NodeType.DARK_NIGHT == "DarkNight"

    def test_decision(self):
        assert NodeType.DECISION == "Decision"

    def test_theme(self):
        assert NodeType.THEME == "Theme"

    def test_virtue(self):
        assert NodeType.VIRTUE == "Virtue"


class TestRelationType:
    def test_exactly_8_values(self):
        assert len(RelationType) == 8

    def test_triggered_by(self):
        assert RelationType.TRIGGERED_BY == "TRIGGERED_BY"

    def test_led_to(self):
        assert RelationType.LED_TO == "LED_TO"

    def test_resolved_by(self):
        assert RelationType.RESOLVED_BY == "RESOLVED_BY"

    def test_echoes(self):
        assert RelationType.ECHOES == "ECHOES"

    def test_deepened_by(self):
        assert RelationType.DEEPENED_BY == "DEEPENED_BY"

    def test_challenged_by(self):
        assert RelationType.CHALLENGED_BY == "CHALLENGED_BY"

    def test_answered_through(self):
        assert RelationType.ANSWERED_THROUGH == "ANSWERED_THROUGH"

    def test_connected_to(self):
        assert RelationType.CONNECTED_TO == "CONNECTED_TO"


class TestSessionData:
    def test_required_fields(self):
        sd = SessionData(
            session_id="sess-001",
            timestamp=datetime(2026, 1, 1),
            emotional_state={"joy": 0.8},
            spiritual_state="consolation",
        )
        assert sd.session_id == "sess-001"
        assert sd.spiritual_state == "consolation"

    def test_optional_lists_default_empty(self):
        sd = SessionData(
            session_id="s",
            timestamp=datetime.now(),
            emotional_state={},
            spiritual_state="peace",
        )
        assert sd.scriptures_presented == []
        assert sd.life_events == []
        assert sd.decisions == []
        assert sd.grace_notes == []
        assert sd.themes == []

    def test_optional_strings_default_empty(self):
        sd = SessionData(
            session_id="s",
            timestamp=datetime.now(),
            emotional_state={},
            spiritual_state="peace",
        )
        assert sd.user_reflection == ""
        assert sd.prayer_type == ""

    def test_custom_fields(self):
        sd = SessionData(
            session_id="s",
            timestamp=datetime.now(),
            emotional_state={"peace": 0.9},
            spiritual_state="consolation",
            themes=["trust", "love"],
            grace_notes=["Sensed peace during prayer"],
        )
        assert sd.themes == ["trust", "love"]
        assert len(sd.grace_notes) == 1


class TestPattern:
    def test_required_fields(self):
        p = Pattern(
            pattern_type="recurring_emotion",
            description="Joy appears repeatedly",
            frequency=5,
        )
        assert p.pattern_type == "recurring_emotion"
        assert p.frequency == 5

    def test_strength_default_zero(self):
        p = Pattern(pattern_type="t", description="d", frequency=1)
        assert p.strength == 0.0

    def test_optional_dates_default_none(self):
        p = Pattern(pattern_type="t", description="d", frequency=1)
        assert p.first_seen is None
        assert p.last_seen is None

    def test_related_scriptures_default_empty(self):
        p = Pattern(pattern_type="t", description="d", frequency=1)
        assert p.related_scriptures == []


class TestTheme:
    def test_required_fields(self):
        t = Theme(name="trust", occurrences=4)
        assert t.name == "trust"
        assert t.occurrences == 4

    def test_optional_defaults(self):
        t = Theme(name="hope", occurrences=2)
        assert t.related_emotions == []
        assert t.related_scriptures == []
        assert t.description == ""

    def test_custom_fields(self):
        t = Theme(
            name="love",
            occurrences=7,
            related_emotions=["joy", "consolation"],
            related_scriptures=["1 Kor 13"],
            description="Recurring theme of divine love",
        )
        assert len(t.related_emotions) == 2
        assert t.description == "Recurring theme of divine love"


class TestJourneyGraph:
    def test_required_user_id(self):
        g = JourneyGraph(user_id="user-123")
        assert g.user_id == "user-123"

    def test_optional_lists_default_empty(self):
        g = JourneyGraph(user_id="u")
        assert g.nodes == []
        assert g.edges == []

    def test_summary_default_empty(self):
        g = JourneyGraph(user_id="u")
        assert g.summary == ""

    def test_custom_fields(self):
        g = JourneyGraph(
            user_id="u",
            nodes=[{"id": 1, "labels": ["EmotionalState"], "properties": {}}],
            edges=[{"type": "LED_TO", "target_id": 2}],
            summary="Growing in consolation",
        )
        assert len(g.nodes) == 1
        assert len(g.edges) == 1
        assert g.summary == "Growing in consolation"
