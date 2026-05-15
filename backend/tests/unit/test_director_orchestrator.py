"""Unit tests for app/agents/spiritual_director/director_orchestrator.py.

Self-contained — no DB, no LLM (LLM client is mocked).

Contracts verified:
- SpiritualTradition / DirectionMode enums
- UserProfile / DirectorResponse dataclasses
- HUMAN_DIRECTOR_DISCLAIMER: present and contains key text
- _detect_mode: keyword-based routing for each mode
- _detect_crisis: returns True for crisis phrases, False for normal
- _handle_crisis: crisis response includes helpline number, no LLM needed,
  mode=CRISIS, crisis_detected=True in metadata
- _build_system_prompt: tradition prompt injected; maturity note present
- _build_user_prompt: message present; challenges/practices included
- _recommend_practices: returns list per tradition; GENERAL fallback
- direct(): valid tradition; invalid tradition → GENERAL; crisis short-circuits;
  delegation to tradition agent; metadata keys
- DirectorResponse.disclaimer == HUMAN_DIRECTOR_DISCLAIMER
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.spiritual_director.director_orchestrator import (
    HUMAN_DIRECTOR_DISCLAIMER,
    DirectionMode,
    DirectorResponse,
    SpiritualDirectorOrchestrator,
    SpiritualTradition,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _orchestrator(llm_response: str = "Odpowiedź kierownika.") -> SpiritualDirectorOrchestrator:
    mock_llm = MagicMock()
    resp = MagicMock()
    resp.content = llm_response
    mock_llm.chat = AsyncMock(return_value=resp)
    return SpiritualDirectorOrchestrator(llm_client=mock_llm)


def _profile(**kwargs) -> UserProfile:
    defaults = {"user_id": "test-user"}
    defaults.update(kwargs)
    return UserProfile(**defaults)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestSpiritualTradition:
    def test_ignatian(self):
        assert SpiritualTradition.IGNATIAN == "ignatian"

    def test_carmelite(self):
        assert SpiritualTradition.CARMELITE == "carmelite"

    def test_franciscan(self):
        assert SpiritualTradition.FRANCISCAN == "franciscan"

    def test_benedictine(self):
        assert SpiritualTradition.BENEDICTINE == "benedictine"

    def test_charismatic(self):
        assert SpiritualTradition.CHARISMATIC == "charismatic"

    def test_general(self):
        assert SpiritualTradition.GENERAL == "general"

    def test_has_at_least_6_traditions(self):
        assert len(SpiritualTradition) >= 6


class TestDirectionMode:
    def test_conversation(self):
        assert DirectionMode.CONVERSATION == "conversation"

    def test_discernment(self):
        assert DirectionMode.DISCERNMENT == "discernment"

    def test_examen(self):
        assert DirectionMode.EXAMEN == "examen"

    def test_lectio_divina(self):
        assert DirectionMode.LECTIO_DIVINA == "lectio_divina"

    def test_crisis(self):
        assert DirectionMode.CRISIS == "crisis"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestUserProfile:
    def test_required_user_id(self):
        p = UserProfile(user_id="u1")
        assert p.user_id == "u1"

    def test_default_tradition(self):
        p = UserProfile(user_id="u1")
        assert p.preferred_tradition == SpiritualTradition.GENERAL

    def test_default_maturity(self):
        p = UserProfile(user_id="u1")
        assert p.spiritual_maturity == "intermediate"

    def test_default_empty_lists(self):
        p = UserProfile(user_id="u1")
        assert p.prayer_practices == []
        assert p.current_challenges == []


class TestDirectorResponse:
    def test_disclaimer_is_set_by_default(self):
        r = DirectorResponse(
            response="Go in peace.",
            tradition_used=SpiritualTradition.GENERAL,
            direction_mode=DirectionMode.CONVERSATION,
            follow_up_questions=[],
            recommended_practices=[],
            scripture_references=[],
        )
        assert r.disclaimer == HUMAN_DIRECTOR_DISCLAIMER

    def test_metadata_defaults_empty(self):
        r = DirectorResponse(
            response="r",
            tradition_used=SpiritualTradition.GENERAL,
            direction_mode=DirectionMode.CONVERSATION,
            follow_up_questions=[],
            recommended_practices=[],
            scripture_references=[],
        )
        assert r.metadata == {}


# ---------------------------------------------------------------------------
# HUMAN_DIRECTOR_DISCLAIMER
# ---------------------------------------------------------------------------


class TestDisclaimer:
    def test_not_empty(self):
        assert len(HUMAN_DIRECTOR_DISCLAIMER) > 50

    def test_mentions_kierownik_duchowy(self):
        assert "kierownik" in HUMAN_DIRECTOR_DISCLAIMER.lower() or "kierownictwa" in HUMAN_DIRECTOR_DISCLAIMER.lower()

    def test_not_a_human_replacement(self):
        # Must not claim to replace a human spiritual director
        assert "nie zastępuje" in HUMAN_DIRECTOR_DISCLAIMER or "nie zastąpi" in HUMAN_DIRECTOR_DISCLAIMER


# ---------------------------------------------------------------------------
# _detect_mode
# ---------------------------------------------------------------------------


class TestDetectMode:
    @pytest.fixture
    def agent(self):
        return SpiritualDirectorOrchestrator()

    def test_rozeznanie_triggers_discernment(self, agent):
        assert agent._detect_mode("Mam ważne rozeznanie w sprawie...") == DirectionMode.DISCERNMENT

    def test_decision_keywords_discernment(self, agent):
        assert agent._detect_mode("Mam trudną decyzja do podjęcia.") == DirectionMode.DISCERNMENT

    def test_powolanie_triggers_discernment(self, agent):
        assert agent._detect_mode("Myślę o powołanie zakonne.") == DirectionMode.DISCERNMENT

    def test_rachunek_sumienia_triggers_examen(self, agent):
        assert agent._detect_mode("Chcę zrobić rachunek sumienia.") == DirectionMode.EXAMEN

    def test_examen_keyword(self, agent):
        assert agent._detect_mode("Pomoż mi z examen.") == DirectionMode.EXAMEN

    def test_lectio_keyword(self, agent):
        assert agent._detect_mode("Proszę o lectio divina.") == DirectionMode.LECTIO_DIVINA

    def test_slowo_boze_triggers_lectio(self, agent):
        assert agent._detect_mode("Czytam dziś słowo Boże.") == DirectionMode.LECTIO_DIVINA

    def test_crisis_keyword(self, agent):
        assert agent._detect_mode("Przeżywam głęboki kryzys wiary.") == DirectionMode.CRISIS

    def test_default_is_conversation(self, agent):
        assert agent._detect_mode("Dzisiaj się modliłem rano.") == DirectionMode.CONVERSATION

    def test_case_insensitive(self, agent):
        assert agent._detect_mode("ROZEZNAWANIE mojego życia") == DirectionMode.DISCERNMENT


# ---------------------------------------------------------------------------
# _detect_crisis
# ---------------------------------------------------------------------------


class TestDetectCrisis:
    @pytest.fixture
    def agent(self):
        return SpiritualDirectorOrchestrator()

    def test_samobojstwo(self, agent):
        assert agent._detect_crisis("Myślę o samobójstwo teraz.") is True

    def test_chce_umrzec(self, agent):
        assert agent._detect_crisis("Chcę umrzeć.") is True

    def test_nie_chce_zyc(self, agent):
        assert agent._detect_crisis("Nie chcę żyć.") is True

    def test_normal_message_no_crisis(self, agent):
        assert agent._detect_crisis("Dziękuję za modlitwę.") is False

    def test_spiritual_darkness_no_crisis(self, agent):
        assert agent._detect_crisis("Przeżywam duchową ciemność.") is False

    def test_case_insensitive(self, agent):
        assert agent._detect_crisis("CHCĘ UMRZEĆ") is True


# ---------------------------------------------------------------------------
# _handle_crisis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHandleCrisis:
    async def test_mode_is_crisis(self):
        agent = _orchestrator()
        profile = _profile()
        result = await agent._handle_crisis("msg", profile)
        assert result.direction_mode == DirectionMode.CRISIS

    async def test_response_contains_helpline(self):
        agent = _orchestrator()
        profile = _profile()
        result = await agent._handle_crisis("msg", profile)
        # Polish crisis helpline
        assert "116 123" in result.response or "800 70 2222" in result.response

    async def test_response_not_empty(self):
        agent = _orchestrator()
        result = await agent._handle_crisis("msg", _profile())
        assert len(result.response) > 100

    async def test_metadata_crisis_detected(self):
        agent = _orchestrator()
        result = await agent._handle_crisis("msg", _profile(user_id="u-crisis"))
        assert result.metadata.get("crisis_detected") is True

    async def test_practices_include_telefon_zaufania(self):
        agent = _orchestrator()
        result = await agent._handle_crisis("msg", _profile())
        practices_text = " ".join(result.recommended_practices)
        assert "116 123" in practices_text or "Telefon Zaufania" in practices_text

    async def test_scripture_references_not_empty(self):
        agent = _orchestrator()
        result = await agent._handle_crisis("msg", _profile())
        assert len(result.scripture_references) > 0

    async def test_disclaimer_present(self):
        agent = _orchestrator()
        result = await agent._handle_crisis("msg", _profile())
        assert result.disclaimer == HUMAN_DIRECTOR_DISCLAIMER


# ---------------------------------------------------------------------------
# _build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    @pytest.fixture
    def agent(self):
        return SpiritualDirectorOrchestrator()

    def test_contains_tradition_text(self, agent):
        prompt = agent._build_system_prompt(
            SpiritualTradition.IGNATIAN, _profile(), DirectionMode.CONVERSATION
        )
        assert "ignac" in prompt.lower() or "Ignac" in prompt

    def test_carmelite_prompt(self, agent):
        prompt = agent._build_system_prompt(
            SpiritualTradition.CARMELITE, _profile(), DirectionMode.CONVERSATION
        )
        assert "karmelit" in prompt.lower() or "Karmel" in prompt

    def test_beginner_maturity_note(self, agent):
        profile = _profile(spiritual_maturity="beginner")
        prompt = agent._build_system_prompt(
            SpiritualTradition.GENERAL, profile, DirectionMode.CONVERSATION
        )
        assert "pocz" in prompt.lower() or "prost" in prompt.lower()

    def test_advanced_maturity_note(self, agent):
        profile = _profile(spiritual_maturity="advanced")
        prompt = agent._build_system_prompt(
            SpiritualTradition.GENERAL, profile, DirectionMode.CONVERSATION
        )
        assert "zaawansowan" in prompt.lower() or "mistyczn" in prompt.lower()

    def test_discernment_mode_prompt(self, agent):
        prompt = agent._build_system_prompt(
            SpiritualTradition.GENERAL, _profile(), DirectionMode.DISCERNMENT
        )
        assert "rozeznaw" in prompt.lower() or "woli Bo" in prompt

    def test_examen_mode_prompt(self, agent):
        prompt = agent._build_system_prompt(
            SpiritualTradition.GENERAL, _profile(), DirectionMode.EXAMEN
        )
        assert "Rachunek" in prompt or "Examen" in prompt


# ---------------------------------------------------------------------------
# _build_user_prompt
# ---------------------------------------------------------------------------


class TestBuildUserPrompt:
    @pytest.fixture
    def agent(self):
        return SpiritualDirectorOrchestrator()

    def test_contains_message(self, agent):
        msg = "Unique test message 9876"
        prompt = agent._build_user_prompt(msg, _profile())
        assert msg in prompt

    def test_challenges_included(self, agent):
        profile = _profile(current_challenges=["samotność", "zwątpienie"])
        prompt = agent._build_user_prompt("msg", profile)
        assert "samotność" in prompt

    def test_prayer_practices_included(self, agent):
        profile = _profile(prayer_practices=["różaniec", "jutrznia"])
        prompt = agent._build_user_prompt("msg", profile)
        assert "różaniec" in prompt

    def test_no_challenges_section_when_empty(self, agent):
        prompt = agent._build_user_prompt("msg", _profile())
        assert "Aktualne wyzwania" not in prompt


# ---------------------------------------------------------------------------
# _recommend_practices
# ---------------------------------------------------------------------------


class TestRecommendPractices:
    @pytest.fixture
    def agent(self):
        return SpiritualDirectorOrchestrator()

    def test_ignatian_practices(self, agent):
        practices = agent._recommend_practices(
            SpiritualTradition.IGNATIAN, DirectionMode.CONVERSATION
        )
        assert len(practices) >= 2
        assert any("examen" in p.lower() or "Examen" in p for p in practices)

    def test_benedictine_practices(self, agent):
        practices = agent._recommend_practices(
            SpiritualTradition.BENEDICTINE, DirectionMode.CONVERSATION
        )
        assert any("lectio" in p.lower() for p in practices)

    def test_unknown_tradition_fallback(self, agent):
        practices = agent._recommend_practices(
            SpiritualTradition.GENERAL, DirectionMode.CONVERSATION
        )
        assert len(practices) >= 2

    def test_returns_list_of_strings(self, agent):
        practices = agent._recommend_practices(
            SpiritualTradition.FRANCISCAN, DirectionMode.CONVERSATION
        )
        assert all(isinstance(p, str) for p in practices)


# ---------------------------------------------------------------------------
# direct() — full integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDirect:
    async def test_returns_director_response(self):
        agent = _orchestrator()
        result = await agent.direct("user-1", "Dzisiaj modliłem się.", "general")
        assert isinstance(result, DirectorResponse)

    async def test_response_content_from_llm(self):
        agent = _orchestrator("Idź w pokoju.")
        result = await agent.direct("user-1", "Modlę się.", "general")
        assert result.response == "Idź w pokoju."

    async def test_invalid_tradition_defaults_to_general(self):
        agent = _orchestrator()
        result = await agent.direct("user-1", "msg", "taoism")
        assert result.tradition_used == SpiritualTradition.GENERAL

    async def test_valid_tradition_preserved(self):
        agent = _orchestrator()
        result = await agent.direct("user-1", "msg", "ignatian")
        assert result.tradition_used == SpiritualTradition.IGNATIAN

    async def test_crisis_message_short_circuits(self):
        agent = _orchestrator()
        result = await agent.direct("u1", "Chcę umrzeć.", "general")
        assert result.direction_mode == DirectionMode.CRISIS
        assert "116 123" in result.response or "800 70 2222" in result.response

    async def test_crisis_does_not_call_llm_for_direction(self):
        mock_llm = MagicMock()
        resp = MagicMock()
        resp.content = "LLM response"
        mock_llm.chat = AsyncMock(return_value=resp)
        agent = SpiritualDirectorOrchestrator(llm_client=mock_llm)
        await agent.direct("u1", "Nie chcę żyć.", "general")
        # chat called for follow-up/scriptures — but we should see no regular direct call
        result_call_count = mock_llm.chat.await_count
        # Crisis path doesn't call the main LLM for the direction response
        # (it uses a pre-set response)
        assert result_call_count == 0

    async def test_disclaimer_always_set(self):
        agent = _orchestrator()
        result = await agent.direct("u1", "msg", "general")
        assert result.disclaimer == HUMAN_DIRECTOR_DISCLAIMER

    async def test_metadata_contains_agent_id(self):
        agent = _orchestrator()
        result = await agent.direct("u1", "msg", "general")
        assert "agent_id" in result.metadata

    async def test_metadata_contains_user_id(self):
        agent = _orchestrator()
        result = await agent.direct("user-xyz", "msg", "general")
        assert result.metadata.get("user_id") == "user-xyz"

    async def test_follow_up_questions_is_list(self):
        agent = _orchestrator("Pytanie 1\nPytanie 2\nPytanie 3")
        result = await agent.direct("u1", "msg", "general")
        assert isinstance(result.follow_up_questions, list)

    async def test_recommended_practices_is_list(self):
        agent = _orchestrator()
        result = await agent.direct("u1", "msg", "benedictine")
        assert isinstance(result.recommended_practices, list)

    async def test_delegation_to_tradition_agent(self):
        """When a tradition-specific agent is registered, it should be used."""
        mock_trad_agent = MagicMock()
        mock_guidance = MagicMock()
        mock_guidance.response = "Ignacjański kierunek."
        mock_trad_agent.agent_id = "A-043"
        mock_trad_agent.guide = AsyncMock(return_value=mock_guidance)

        agent = _orchestrator()
        agent._tradition_agents[SpiritualTradition.IGNATIAN] = mock_trad_agent

        result = await agent.direct("u1", "Potrzebuję rozeznania.", "ignatian")
        mock_trad_agent.guide.assert_awaited_once()
        assert result.response == "Ignacjański kierunek."
        assert result.metadata.get("delegated_to") == "A-043"
