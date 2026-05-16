"""Unit tests for app/services/content/uniqueness_engine.py.

All tests are self-contained — no DB, Redis, or external services needed.
The engine is pure-Python algorithmic code, so every behaviour is testable
with direct instantiation and deterministic inputs.

Contracts verified:
- FULL_CANON contains exactly 73 books (46 OT + 27 NT)
- KERYGMATIC_THEMES has exactly 8 pillars
- compute_daily_seed: deterministic per (user, date), differs across users/days
- get_kerygmatic_theme: returns valid theme dict, rotates across the 8 themes
- suggest_books: returns all 73 books, boosts emotion/season, demotes recent
- suggest_tradition: returns a valid tradition, avoids most-recently-used
- suggest_action_category: returns a valid category, avoids most-recently-used
- build_session_context: complete context dict with all required keys
"""

from __future__ import annotations

from datetime import date

from app.services.content.uniqueness_engine import (
    CANON_NT,
    CANON_OT,
    EMOTION_SCRIPTURE_MAP,
    FULL_CANON,
    KERYGMATIC_THEMES,
    SEASON_SCRIPTURE_WEIGHTS,
    ContentUniquenessEngine,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

ENGINE = ContentUniquenessEngine()
USER_A = "user-aaaaaaaa"
USER_B = "user-bbbbbbbb"
DATE_1 = date(2026, 1, 15)
DATE_2 = date(2026, 1, 16)  # next day


# ── Canon ─────────────────────────────────────────────────────────────────────


class TestCanon:
    def test_ot_has_46_books(self):
        assert len(CANON_OT) == 46

    def test_nt_has_27_books(self):
        assert len(CANON_NT) == 27

    def test_full_canon_has_73_books(self):
        assert len(FULL_CANON) == 73

    def test_full_canon_no_duplicates(self):
        assert len(FULL_CANON) == len(set(FULL_CANON))

    def test_full_canon_is_ot_plus_nt(self):
        assert FULL_CANON == CANON_OT + CANON_NT

    def test_psalms_in_canon(self):
        assert "Ps" in FULL_CANON

    def test_john_gospel_in_canon(self):
        assert "J" in FULL_CANON

    def test_revelation_in_canon(self):
        assert "Ap" in FULL_CANON


# ── Kerygmatic themes ─────────────────────────────────────────────────────────


class TestKerygmaticThemes:
    def test_eight_themes(self):
        assert len(KERYGMATIC_THEMES) == 8

    def test_each_theme_has_required_keys(self):
        required = {"theme", "label", "key_passages", "catechism_refs"}
        for t in KERYGMATIC_THEMES:
            assert required <= set(t.keys()), f"Missing keys in theme: {t['theme']}"

    def test_each_theme_has_passages(self):
        for t in KERYGMATIC_THEMES:
            assert len(t["key_passages"]) >= 3, f"Too few passages in {t['theme']}"

    def test_theme_names_unique(self):
        names = [t["theme"] for t in KERYGMATIC_THEMES]
        assert len(names) == len(set(names))

    def test_mysterium_paschale_present(self):
        themes = {t["theme"] for t in KERYGMATIC_THEMES}
        assert "mysterium_paschale" in themes

    def test_incarnatio_present(self):
        themes = {t["theme"] for t in KERYGMATIC_THEMES}
        assert "incarnatio" in themes


# ── Season scripture weights ───────────────────────────────────────────────────


class TestSeasonScriptureWeights:
    def test_all_four_seasons_present(self):
        for season in ("advent", "christmas", "lent", "easter", "ordinary"):
            assert season in SEASON_SCRIPTURE_WEIGHTS

    def test_season_books_are_subset_of_canon(self):
        for season, books in SEASON_SCRIPTURE_WEIGHTS.items():
            for book in books:
                assert book in FULL_CANON, f"Unknown book '{book}' in season '{season}'"


# ── Emotion scripture map ─────────────────────────────────────────────────────


class TestEmotionScriptureMap:
    def test_consolation_states_covered(self):
        for emotion in ("peace", "gratitude", "love", "hope"):
            assert emotion in EMOTION_SCRIPTURE_MAP

    def test_desolation_states_covered(self):
        for emotion in ("sadness", "fear", "anxiety", "guilt"):
            assert emotion in EMOTION_SCRIPTURE_MAP

    def test_dark_night_covered(self):
        assert "dark_night" in EMOTION_SCRIPTURE_MAP

    def test_each_emotion_has_passages(self):
        for emotion, passages in EMOTION_SCRIPTURE_MAP.items():
            assert len(passages) >= 3, f"Too few passages for {emotion}"


# ── compute_daily_seed ────────────────────────────────────────────────────────


class TestComputeDailySeed:
    def test_returns_integer(self):
        seed = ENGINE.compute_daily_seed(USER_A, DATE_1)
        assert isinstance(seed, int)

    def test_deterministic_same_user_same_day(self):
        s1 = ENGINE.compute_daily_seed(USER_A, DATE_1)
        s2 = ENGINE.compute_daily_seed(USER_A, DATE_1)
        assert s1 == s2

    def test_different_day_different_seed(self):
        s1 = ENGINE.compute_daily_seed(USER_A, DATE_1)
        s2 = ENGINE.compute_daily_seed(USER_A, DATE_2)
        assert s1 != s2

    def test_different_user_different_seed(self):
        s1 = ENGINE.compute_daily_seed(USER_A, DATE_1)
        s2 = ENGINE.compute_daily_seed(USER_B, DATE_1)
        assert s1 != s2

    def test_seed_is_positive(self):
        seed = ENGINE.compute_daily_seed(USER_A, DATE_1)
        assert seed > 0


# ── get_kerygmatic_theme ──────────────────────────────────────────────────────


class TestGetKerygmaticTheme:
    def test_returns_dict(self):
        theme = ENGINE.get_kerygmatic_theme(USER_A, DATE_1)
        assert isinstance(theme, dict)

    def test_has_required_keys(self):
        theme = ENGINE.get_kerygmatic_theme(USER_A, DATE_1)
        for key in ("theme", "label", "key_passages", "catechism_refs"):
            assert key in theme

    def test_theme_name_is_valid(self):
        valid_names = {t["theme"] for t in KERYGMATIC_THEMES}
        theme = ENGINE.get_kerygmatic_theme(USER_A, DATE_1)
        assert theme["theme"] in valid_names

    def test_same_user_same_day_same_theme(self):
        t1 = ENGINE.get_kerygmatic_theme(USER_A, DATE_1)
        t2 = ENGINE.get_kerygmatic_theme(USER_A, DATE_1)
        assert t1["theme"] == t2["theme"]

    def test_different_users_can_have_different_themes(self):
        """Users start at different offsets in the cycle."""
        themes_seen: set[str] = set()
        # Use many user IDs to ensure we see variation
        for i in range(50):
            t = ENGINE.get_kerygmatic_theme(f"user-{i:04d}", DATE_1)
            themes_seen.add(t["theme"])
        assert len(themes_seen) > 1, "All users landed on the same theme — offset broken"

    def test_all_8_themes_reachable_across_cycle(self):
        """Over 8 * cycle_days days the same user cycles through all themes."""
        cycle_days = 8
        themes_seen: set[str] = set()
        base = date(2026, 1, 1)
        for offset in range(len(KERYGMATIC_THEMES) * cycle_days):
            d = date(base.year, base.month, 1)
            import datetime as _dt
            d = _dt.date.fromordinal(base.toordinal() + offset * cycle_days)
            t = ENGINE.get_kerygmatic_theme(USER_A, d)
            themes_seen.add(t["theme"])
        assert len(themes_seen) == len(KERYGMATIC_THEMES)


# ── suggest_books ─────────────────────────────────────────────────────────────


class TestSuggestBooks:
    def test_returns_all_73_books(self):
        books = ENGINE.suggest_books(USER_A, "ordinary", "peace", today=DATE_1)
        assert len(books) == 73

    def test_returns_list_of_strings(self):
        books = ENGINE.suggest_books(USER_A, "ordinary", "peace", today=DATE_1)
        assert all(isinstance(b, str) for b in books)

    def test_all_canon_books_present(self):
        books = ENGINE.suggest_books(USER_A, "lent", "sadness", today=DATE_1)
        assert set(books) == set(FULL_CANON)

    def test_emotion_books_ranked_higher_than_neutral(self):
        """Books matching the emotion should appear in the top half."""
        books = ENGINE.suggest_books(USER_A, "ordinary", "guilt", today=DATE_1)
        # guilt maps to Ps 51, 1 J 1,9, Rz 8,1-2, Iz 1,18, Lk 15,11-32
        # → "Ps" should be highly ranked
        top_half = set(books[:36])
        assert "Ps" in top_half

    def test_recent_book_penalised(self):
        """A book used in every recent session should rank lower than without history."""
        # Use "Ps" which maps to many emotions but can be tested comparatively
        history = [{"scripture": {"book": "Jk"}} for _ in range(30)]
        books_with_history = ENGINE.suggest_books(USER_A, "ordinary", "consolation", user_history=history, today=DATE_1)
        books_without_history = ENGINE.suggest_books(USER_A, "ordinary", "consolation", user_history=[], today=DATE_1)
        idx_with = books_with_history.index("Jk")
        idx_without = books_without_history.index("Jk")
        assert idx_with > idx_without, "Overused book should rank lower than when unused"

    def test_deterministic_for_same_inputs(self):
        b1 = ENGINE.suggest_books(USER_A, "advent", "hope", today=DATE_1)
        b2 = ENGINE.suggest_books(USER_A, "advent", "hope", today=DATE_1)
        assert b1 == b2

    def test_different_user_different_ordering(self):
        b1 = ENGINE.suggest_books(USER_A, "easter", "joy", today=DATE_1)
        b2 = ENGINE.suggest_books(USER_B, "easter", "joy", today=DATE_1)
        # Exact same order is astronomically unlikely
        assert b1 != b2


# ── suggest_tradition ─────────────────────────────────────────────────────────

_VALID_TRADITIONS = {"ignatian", "carmelite", "franciscan", "benedictine",
                     "charismatic", "dominican", "marian"}


class TestSuggestTradition:
    def test_returns_valid_tradition(self):
        t = ENGINE.suggest_tradition(USER_A, today=DATE_1)
        assert t in _VALID_TRADITIONS

    def test_no_history_returns_a_tradition(self):
        t = ENGINE.suggest_tradition(USER_A, user_history=[], today=DATE_1)
        assert t in _VALID_TRADITIONS

    def test_avoids_overused_tradition(self):
        """Using ignatian 14 times in a row should cause engine to suggest something else."""
        history = [{"prayer": {"tradition": "ignatian"}} for _ in range(14)]
        t = ENGINE.suggest_tradition(USER_A, user_history=history, today=DATE_1)
        assert t != "ignatian", "Should avoid the heavily overused tradition"

    def test_deterministic_for_same_inputs(self):
        history = [{"prayer": {"tradition": "franciscan"}} for _ in range(5)]
        t1 = ENGINE.suggest_tradition(USER_A, user_history=history, today=DATE_1)
        t2 = ENGINE.suggest_tradition(USER_A, user_history=history, today=DATE_1)
        assert t1 == t2


# ── suggest_action_category ───────────────────────────────────────────────────

_VALID_CATEGORIES = {
    "prayer", "charity", "relationship", "service", "gratitude",
    "forgiveness", "self_care", "teaching", "counsel", "patience",
}


class TestSuggestActionCategory:
    def test_returns_valid_category(self):
        c = ENGINE.suggest_action_category(USER_A, today=DATE_1)
        assert c in _VALID_CATEGORIES

    def test_avoids_overused_category(self):
        history = [{"action": {"category": "prayer"}} for _ in range(20)]
        c = ENGINE.suggest_action_category(USER_A, user_history=history, today=DATE_1)
        assert c != "prayer"

    def test_no_history_returns_a_category(self):
        c = ENGINE.suggest_action_category(USER_A, user_history=[], today=DATE_1)
        assert c in _VALID_CATEGORIES

    def test_deterministic(self):
        c1 = ENGINE.suggest_action_category(USER_A, today=DATE_1)
        c2 = ENGINE.suggest_action_category(USER_A, today=DATE_1)
        assert c1 == c2


# ── build_session_context ─────────────────────────────────────────────────────


class TestBuildSessionContext:
    def test_returns_all_required_keys(self):
        ctx = ENGINE.build_session_context(USER_A, "advent", "hope", today=DATE_1)
        required = {
            "daily_seed", "kerygmatic_theme", "suggested_books",
            "suggested_tradition", "suggested_action_category",
            "emotion_passages", "season", "date",
        }
        assert required <= set(ctx.keys())

    def test_suggested_books_limited_to_10(self):
        ctx = ENGINE.build_session_context(USER_A, "ordinary", "peace", today=DATE_1)
        assert len(ctx["suggested_books"]) == 10

    def test_date_iso_format(self):
        ctx = ENGINE.build_session_context(USER_A, "lent", "sadness", today=DATE_1)
        assert ctx["date"] == DATE_1.isoformat()

    def test_season_preserved(self):
        ctx = ENGINE.build_session_context(USER_A, "easter", "awe", today=DATE_1)
        assert ctx["season"] == "easter"

    def test_kerygmatic_theme_is_dict_with_theme_key(self):
        ctx = ENGINE.build_session_context(USER_A, "ordinary", "peace", today=DATE_1)
        assert "theme" in ctx["kerygmatic_theme"]

    def test_emotion_passages_for_known_emotion(self):
        ctx = ENGINE.build_session_context(USER_A, "ordinary", "fear", today=DATE_1)
        assert len(ctx["emotion_passages"]) > 0

    def test_unknown_emotion_gives_empty_passages(self):
        ctx = ENGINE.build_session_context(USER_A, "ordinary", "totally_unknown_mood", today=DATE_1)
        assert ctx["emotion_passages"] == []

    def test_different_users_different_context(self):
        ctx_a = ENGINE.build_session_context(USER_A, "ordinary", "peace", today=DATE_1)
        ctx_b = ENGINE.build_session_context(USER_B, "ordinary", "peace", today=DATE_1)
        # At least the seed differs
        assert ctx_a["daily_seed"] != ctx_b["daily_seed"]
