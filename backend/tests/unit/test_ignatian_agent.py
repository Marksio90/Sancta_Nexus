"""Unit tests for app/agents/spiritual_director/ignatian_agent.py.

Self-contained — no LLM, no DB. The LLM client is mocked.

Contracts verified:
- Enums: SpiritualMovement, ExerciseWeek, DiscernmentRuleSet, ExamenPhase
- Dataclasses: SpiritualState, IgnatianExercise, IgnatianGuidance
- CONSOLATION_MARKERS / DESOLATION_MARKERS exist
- _detect_movement: consolation, desolation, tranquility, ambiguous
- _build_system_prompt: week-specific context injected
- _build_user_prompt: contains message, movement, grace desired, history
- _recommend_exercises: desolation → agere contra; consolation → journaling;
  second-week → compositio loci always appended
- _should_suggest_examen: daily/twice_daily trigger; weekly does not
- _analyze_movement: non-empty, movement-specific text
- _get_applied_rules: first-week desolation rules; second-week ambiguous rules
- _format_discernment_notes: contains all key fields
- guide(): full flow — movement detected, exercises recommended, metadata set,
  agere_contra set only for desolation, examen_guidance set for daily prayer
- guide_examen(): examen path returns TRANQUILITY + examen exercise
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.spiritual_director.ignatian_agent import (
    CONSOLATION_MARKERS,
    DESOLATION_MARKERS,
    DiscernmentRuleSet,
    ExamenPhase,
    ExerciseWeek,
    IgnatianDiscernmentAgent,
    IgnatianExercise,
    IgnatianGuidance,
    SpiritualMovement,
    SpiritualState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent(llm_response: str = "Kierunek duchowy po polsku.") -> IgnatianDiscernmentAgent:
    mock_llm = MagicMock()
    response = MagicMock()
    response.content = llm_response
    mock_llm.chat = AsyncMock(return_value=response)
    return IgnatianDiscernmentAgent(llm_client=mock_llm)


def _state(**kwargs) -> SpiritualState:
    defaults = {"user_id": "test-user"}
    defaults.update(kwargs)
    return SpiritualState(**defaults)


# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


class TestEnums:
    def test_spiritual_movement_values(self):
        assert SpiritualMovement.CONSOLATION == "consolation"
        assert SpiritualMovement.DESOLATION == "desolation"
        assert SpiritualMovement.TRANQUILITY == "tranquility"
        assert SpiritualMovement.AMBIGUOUS == "ambiguous"

    def test_exercise_week_values(self):
        for w in ExerciseWeek:
            assert w.value in ("first", "second", "third", "fourth")

    def test_discernment_rule_set_values(self):
        assert DiscernmentRuleSet.FIRST_WEEK in DiscernmentRuleSet
        assert DiscernmentRuleSet.SECOND_WEEK in DiscernmentRuleSet

    def test_examen_phase_values(self):
        assert len(ExamenPhase) >= 5


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


class TestMarkers:
    def test_consolation_markers_non_empty(self):
        assert len(CONSOLATION_MARKERS) >= 5

    def test_desolation_markers_non_empty(self):
        assert len(DESOLATION_MARKERS) >= 5

    def test_pokój_in_consolation(self):
        assert "pokój" in CONSOLATION_MARKERS

    def test_smutek_in_desolation(self):
        assert "smutek" in DESOLATION_MARKERS


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestSpiritualState:
    def test_required_user_id(self):
        state = SpiritualState(user_id="u1")
        assert state.user_id == "u1"

    def test_defaults(self):
        state = SpiritualState(user_id="u1")
        assert state.current_movement is None
        assert state.exercise_week == ExerciseWeek.FIRST
        assert state.rule_set == DiscernmentRuleSet.FIRST_WEEK
        assert state.recent_consolations == []
        assert state.recent_desolations == []
        assert state.in_retreat is False
        assert state.days_in_exercises == 0

    def test_custom_values(self):
        state = SpiritualState(
            user_id="u2",
            exercise_week=ExerciseWeek.SECOND,
            in_retreat=True,
            days_in_exercises=5,
        )
        assert state.exercise_week == ExerciseWeek.SECOND
        assert state.in_retreat is True
        assert state.days_in_exercises == 5


class TestIgnatianExercise:
    def test_required_fields(self):
        ex = IgnatianExercise(name="Test", description="Do this")
        assert ex.name == "Test"
        assert ex.description == "Do this"

    def test_defaults(self):
        ex = IgnatianExercise(name="X", description="Y")
        assert ex.scripture is None
        assert ex.duration_minutes == 30
        assert ex.method == ""
        assert ex.grace_to_ask == ""


class TestIgnatianGuidance:
    def test_required_fields(self):
        g = IgnatianGuidance(
            response="Go in peace",
            spiritual_movement=SpiritualMovement.CONSOLATION,
            movement_analysis="all good",
            exercises=[],
        )
        assert g.response == "Go in peace"
        assert g.spiritual_movement == SpiritualMovement.CONSOLATION
        assert g.agere_contra_suggestion is None
        assert g.examen_guidance is None
        assert g.discernment_notes == ""
        assert g.rules_applied == []
        assert g.metadata == {}


# ---------------------------------------------------------------------------
# _detect_movement
# ---------------------------------------------------------------------------


class TestDetectMovement:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    @pytest.mark.asyncio
    async def test_consolation_markers(self, agent):
        msg = "Czuję pokój i radość w sercu, bliskość Boga."
        movement = await agent._detect_movement(msg, _state())
        assert movement == SpiritualMovement.CONSOLATION

    @pytest.mark.asyncio
    async def test_desolation_markers(self, agent):
        msg = "Czuję smutek, ciemność, brak nadziei i zniechęcenie."
        movement = await agent._detect_movement(msg, _state())
        assert movement == SpiritualMovement.DESOLATION

    @pytest.mark.asyncio
    async def test_no_markers_tranquility(self, agent):
        msg = "Modliłem się przez chwilę dzisiaj rano."
        movement = await agent._detect_movement(msg, _state())
        assert movement == SpiritualMovement.TRANQUILITY

    @pytest.mark.asyncio
    async def test_equal_markers_ambiguous(self, agent):
        msg = "Czuję pokój i smutek jednocześnie."
        movement = await agent._detect_movement(msg, _state())
        assert movement == SpiritualMovement.AMBIGUOUS

    @pytest.mark.asyncio
    async def test_consolation_dominates(self, agent):
        # 3 consolation markers vs 1 desolation
        msg = "Mam pokój, radość, wdzięczność mimo chwilowego smutku."
        movement = await agent._detect_movement(msg, _state())
        assert movement == SpiritualMovement.CONSOLATION


# ---------------------------------------------------------------------------
# _build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_contains_base_prompt(self, agent):
        prompt = agent._build_system_prompt(_state())
        assert "Ignac" in prompt

    def test_first_week_context(self, agent):
        state = _state(exercise_week=ExerciseWeek.FIRST)
        prompt = agent._build_system_prompt(state)
        assert "I Tygo" in prompt or "oczyszcz" in prompt.lower()

    def test_second_week_context(self, agent):
        state = _state(exercise_week=ExerciseWeek.SECOND)
        prompt = agent._build_system_prompt(state)
        assert "II Tygo" in prompt or "Chryst" in prompt

    def test_third_week_context(self, agent):
        state = _state(exercise_week=ExerciseWeek.THIRD)
        prompt = agent._build_system_prompt(state)
        assert "III Tygo" in prompt or "Mę" in prompt

    def test_fourth_week_context(self, agent):
        state = _state(exercise_week=ExerciseWeek.FOURTH)
        prompt = agent._build_system_prompt(state)
        assert "IV Tygo" in prompt or "Zmartwychwst" in prompt

    def test_retreat_flag(self, agent):
        state = _state(in_retreat=True)
        prompt = agent._build_system_prompt(state)
        assert "rekolekcj" in prompt.lower()


# ---------------------------------------------------------------------------
# _build_user_prompt
# ---------------------------------------------------------------------------


class TestBuildUserPrompt:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_contains_message(self, agent):
        msg = "Unique spiritual message 12345"
        prompt = agent._build_user_prompt(msg, _state(), SpiritualMovement.TRANQUILITY)
        assert msg in prompt

    def test_contains_movement(self, agent):
        prompt = agent._build_user_prompt(
            "msg", _state(), SpiritualMovement.DESOLATION
        )
        assert "desolation" in prompt

    def test_contains_grace_desired(self, agent):
        state = _state(current_grace_desired="Łaska pokory")
        prompt = agent._build_user_prompt("msg", state, SpiritualMovement.TRANQUILITY)
        assert "Łaska pokory" in prompt

    def test_contains_recent_consolations(self, agent):
        state = _state(recent_consolations=["radość", "pokój", "miłość"])
        prompt = agent._build_user_prompt("msg", state, SpiritualMovement.CONSOLATION)
        assert "radość" in prompt

    def test_no_consolation_if_empty(self, agent):
        prompt = agent._build_user_prompt("msg", _state(), SpiritualMovement.TRANQUILITY)
        assert "Ostatnie pocieszenia" not in prompt


# ---------------------------------------------------------------------------
# _recommend_exercises
# ---------------------------------------------------------------------------


class TestRecommendExercises:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_desolation_includes_agere_contra(self, agent):
        exercises = agent._recommend_exercises(_state(), SpiritualMovement.DESOLATION)
        names = [e.name for e in exercises]
        assert any("Agere" in n or "agere" in n.lower() for n in names)

    def test_desolation_includes_prayer_in_darkness(self, agent):
        exercises = agent._recommend_exercises(_state(), SpiritualMovement.DESOLATION)
        assert len(exercises) >= 2

    def test_consolation_includes_journaling(self, agent):
        exercises = agent._recommend_exercises(_state(), SpiritualMovement.CONSOLATION)
        names = [e.name for e in exercises]
        assert any("pocieszen" in n.lower() or "utrwal" in n.lower() for n in names)

    def test_second_week_adds_contemplation(self, agent):
        state = _state(exercise_week=ExerciseWeek.SECOND)
        exercises = agent._recommend_exercises(state, SpiritualMovement.TRANQUILITY)
        names = [e.name for e in exercises]
        assert any("Kontemplacj" in n or "ewangel" in n.lower() for n in names)

    def test_exercises_are_ignatian_exercise_instances(self, agent):
        exercises = agent._recommend_exercises(_state(), SpiritualMovement.DESOLATION)
        assert all(isinstance(e, IgnatianExercise) for e in exercises)

    def test_exercises_have_positive_duration(self, agent):
        exercises = agent._recommend_exercises(_state(), SpiritualMovement.CONSOLATION)
        for e in exercises:
            assert e.duration_minutes > 0


# ---------------------------------------------------------------------------
# _should_suggest_examen
# ---------------------------------------------------------------------------


class TestShouldSuggestExamen:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_daily_prayer_suggests_examen(self, agent):
        assert agent._should_suggest_examen(_state(prayer_frequency="daily")) is True

    def test_twice_daily_suggests_examen(self, agent):
        assert agent._should_suggest_examen(_state(prayer_frequency="twice_daily")) is True

    def test_weekly_does_not_suggest(self, agent):
        assert agent._should_suggest_examen(_state(prayer_frequency="weekly")) is False

    def test_sporadic_does_not_suggest(self, agent):
        assert agent._should_suggest_examen(_state(prayer_frequency="sporadic")) is False


# ---------------------------------------------------------------------------
# _analyze_movement
# ---------------------------------------------------------------------------


class TestAnalyzeMovement:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_returns_string(self, agent):
        for m in SpiritualMovement:
            result = agent._analyze_movement("msg", m)
            assert isinstance(result, str)

    def test_consolation_analysis_non_empty(self, agent):
        result = agent._analyze_movement("msg", SpiritualMovement.CONSOLATION)
        assert len(result) > 10

    def test_desolation_mentions_agere_contra(self, agent):
        result = agent._analyze_movement("msg", SpiritualMovement.DESOLATION)
        assert "agere" in result.lower() or "strapieniu" in result.lower()

    def test_ambiguous_mentions_discernment(self, agent):
        result = agent._analyze_movement("msg", SpiritualMovement.AMBIGUOUS)
        assert "rozeznaw" in result.lower() or "niejednoznaczn" in result.lower()


# ---------------------------------------------------------------------------
# _get_applied_rules
# ---------------------------------------------------------------------------


class TestGetAppliedRules:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_first_week_desolation_returns_rules(self, agent):
        state = _state(rule_set=DiscernmentRuleSet.FIRST_WEEK)
        rules = agent._get_applied_rules(state, SpiritualMovement.DESOLATION)
        assert len(rules) >= 3
        assert any("RI-" in r for r in rules)

    def test_first_week_consolation_returns_rule(self, agent):
        state = _state(rule_set=DiscernmentRuleSet.FIRST_WEEK)
        rules = agent._get_applied_rules(state, SpiritualMovement.CONSOLATION)
        assert len(rules) >= 1
        assert any("pocieszeni" in r.lower() for r in rules)

    def test_second_week_ambiguous_returns_rules(self, agent):
        state = _state(rule_set=DiscernmentRuleSet.SECOND_WEEK)
        rules = agent._get_applied_rules(state, SpiritualMovement.AMBIGUOUS)
        assert len(rules) >= 2
        assert any("RII-" in r for r in rules)

    def test_returns_list(self, agent):
        rules = agent._get_applied_rules(_state(), SpiritualMovement.TRANQUILITY)
        assert isinstance(rules, list)


# ---------------------------------------------------------------------------
# _format_discernment_notes
# ---------------------------------------------------------------------------


class TestFormatDiscernmentNotes:
    @pytest.fixture
    def agent(self):
        return IgnatianDiscernmentAgent()

    def test_contains_movement(self, agent):
        notes = agent._format_discernment_notes(
            SpiritualMovement.DESOLATION, _state()
        )
        assert "desolation" in notes

    def test_contains_week(self, agent):
        state = _state(exercise_week=ExerciseWeek.SECOND)
        notes = agent._format_discernment_notes(SpiritualMovement.CONSOLATION, state)
        assert "second" in notes

    def test_contains_days(self, agent):
        state = _state(days_in_exercises=7)
        notes = agent._format_discernment_notes(SpiritualMovement.TRANQUILITY, state)
        assert "7" in notes


# ---------------------------------------------------------------------------
# guide() full integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGuide:
    async def test_returns_ignatian_guidance(self):
        agent = _agent("Dobry kierunek duchowy.")
        result = await agent.guide(_state(), "Czuję pokój i radość.")
        assert isinstance(result, IgnatianGuidance)

    async def test_response_content_from_llm(self):
        agent = _agent("Kierunek: medytuj Ps 23.")
        result = await agent.guide(_state(), "Czuję spokój.")
        assert result.response == "Kierunek: medytuj Ps 23."

    async def test_movement_is_spiritual_movement_enum(self):
        agent = _agent()
        result = await agent.guide(_state(), "msg")
        assert isinstance(result.spiritual_movement, SpiritualMovement)

    async def test_consolation_message_detects_consolation(self):
        agent = _agent()
        result = await agent.guide(_state(), "Czuję głęboki pokój, radość i wdzięczność.")
        assert result.spiritual_movement == SpiritualMovement.CONSOLATION

    async def test_desolation_message_sets_agere_contra(self):
        agent = _agent()
        result = await agent.guide(_state(), "Czuję smutek, ciemność i zniechęcenie.")
        assert result.agere_contra_suggestion is not None

    async def test_consolation_message_no_agere_contra(self):
        agent = _agent()
        result = await agent.guide(_state(), "Czuję pokój, radość i nadzieję.")
        assert result.agere_contra_suggestion is None

    async def test_daily_prayer_has_examen_guidance(self):
        agent = _agent()
        result = await agent.guide(_state(prayer_frequency="daily"), "Modlę się.")
        assert result.examen_guidance is not None

    async def test_weekly_prayer_no_examen_guidance(self):
        agent = _agent()
        result = await agent.guide(_state(prayer_frequency="weekly"), "Modlę się.")
        assert result.examen_guidance is None

    async def test_exercises_is_list_of_ignatian_exercises(self):
        agent = _agent()
        result = await agent.guide(_state(), "msg")
        assert isinstance(result.exercises, list)
        assert all(isinstance(e, IgnatianExercise) for e in result.exercises)

    async def test_metadata_contains_agent_id(self):
        agent = _agent()
        result = await agent.guide(_state(), "msg")
        assert result.metadata.get("agent_id") == "A-043"

    async def test_metadata_contains_user_id(self):
        agent = _agent()
        result = await agent.guide(_state(user_id="user-xyz"), "msg")
        assert result.metadata.get("user_id") == "user-xyz"

    async def test_rules_applied_is_list(self):
        agent = _agent()
        result = await agent.guide(_state(), "msg")
        assert isinstance(result.rules_applied, list)

    async def test_discernment_notes_non_empty(self):
        agent = _agent()
        result = await agent.guide(_state(), "msg")
        assert len(result.discernment_notes) > 0


# ---------------------------------------------------------------------------
# guide_examen()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGuideExamen:
    async def test_returns_ignatian_guidance(self):
        agent = _agent("Rachunek sumienia: wdzięczność...")
        result = await agent.guide_examen(_state())
        assert isinstance(result, IgnatianGuidance)

    async def test_movement_is_tranquility(self):
        agent = _agent()
        result = await agent.guide_examen(_state())
        assert result.spiritual_movement == SpiritualMovement.TRANQUILITY

    async def test_has_one_examen_exercise(self):
        agent = _agent()
        result = await agent.guide_examen(_state())
        assert len(result.exercises) >= 1
        ex = result.exercises[0]
        assert "examen" in ex.method.lower() or "Examen" in ex.name

    async def test_response_is_llm_content(self):
        agent = _agent("Pięć kroków rachunku sumienia.")
        result = await agent.guide_examen(_state())
        assert result.response == "Pięć kroków rachunku sumienia."

    async def test_metadata_has_exercise_type(self):
        agent = _agent()
        result = await agent.guide_examen(_state())
        assert result.metadata.get("exercise_type") == "examen"
