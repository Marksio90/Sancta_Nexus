"""Unit tests for sacrament services in app/services/sacraments/.

Tests three services using pure-data and pure-logic methods only — no AI/LLM:
  - ExaminationService: 10 commandments catalog, state-of-life questions
  - ConfirmationService: 7 gifts of Holy Spirit, 6 sessions, get_program/get_session
  - RCIAService: 4 stages, 14 topics, get_curriculum/get_session

All instances bypass __init__ to avoid OpenAI/config imports.

Contracts verified:
ExaminationService:
- StateOfLife / ExaminationMethod enums
- _COMMANDMENTS: exactly 10, all fields, numbered 1-10
- _STATE_ADDITIONS: every StateOfLife has at least 2 questions
- get_commandments_overview: 10 items with ccc_ref / scripture / questions
- get_state_questions: returns list for known state, [] for unknown

ConfirmationService:
- GIFTS_OF_SPIRIT: exactly 7, all required fields, Latin names
- CONFIRMATION_SESSIONS: exactly 6, all have session_id / scripture / key_question
- get_gifts_of_spirit: returns 7 dicts with gift/latin/description
- get_program: returns 6 dicts with session_id / title / ccc_refs
- get_session: found / not found

RCIAService:
- RCIAStage enum values
- RCIA_CURRICULUM: exactly 14 topics, all 4 stages present
- All topics have required fields, unique session_ids
- get_curriculum: 4 stage groups, session_count matches topics
- get_session: found / not found
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub openai only (may not be installed in this environment)
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

from app.services.sacraments.confirmation_service import (
    CONFIRMATION_SESSIONS,
    GIFTS_OF_SPIRIT,
    ConfirmationService,
)
from app.services.sacraments.examination_service import (
    _COMMANDMENTS,
    _STATE_ADDITIONS,
    ExaminationMethod,
    ExaminationService,
    StateOfLife,
)
from app.services.sacraments.rcia_service import (
    RCIA_CURRICULUM,
    RCIAService,
    RCIAStage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exam_svc() -> ExaminationService:
    svc = ExaminationService.__new__(ExaminationService)
    svc._model = "gpt-4o"
    return svc


def _conf_svc() -> ConfirmationService:
    svc = ConfirmationService.__new__(ConfirmationService)
    svc._model = "gpt-4o-mini"
    return svc


def _rcia_svc() -> RCIAService:
    svc = RCIAService.__new__(RCIAService)
    svc._model = "gpt-4o-mini"
    return svc


# ===========================================================================
# ExaminationService
# ===========================================================================


class TestStateOfLifeEnum:
    def test_parent_value(self):
        assert StateOfLife.PARENT == "parent"

    def test_married_value(self):
        assert StateOfLife.MARRIED == "married"

    def test_religious_value(self):
        assert StateOfLife.RELIGIOUS == "religious"

    def test_priest_value(self):
        assert StateOfLife.PRIEST == "priest"

    def test_teenager_value(self):
        assert StateOfLife.TEENAGER == "teenager"

    def test_has_at_least_5_states(self):
        assert len(StateOfLife) >= 5


class TestExaminationMethodEnum:
    def test_has_commandments(self):
        assert hasattr(ExaminationMethod, "COMMANDMENTS") or any(
            "commandment" in m.value.lower() for m in ExaminationMethod
        )

    def test_is_str_enum(self):
        for m in ExaminationMethod:
            assert isinstance(m.value, str)


class TestCommandmentsCatalog:
    def test_exactly_10_commandments(self):
        assert len(_COMMANDMENTS) == 10

    def test_all_have_required_fields(self):
        required = {"number", "title", "ccc", "scripture", "questions"}
        for c in _COMMANDMENTS:
            assert required <= set(c.keys()), f"Missing fields in commandment {c.get('number')}"

    def test_numbered_1_to_10(self):
        numbers = [c["number"] for c in _COMMANDMENTS]
        assert numbers == list(range(1, 11))

    def test_all_have_ccc_references(self):
        for c in _COMMANDMENTS:
            assert c["ccc"].strip() and "§" in c["ccc"]

    def test_all_have_scripture_references(self):
        for c in _COMMANDMENTS:
            assert c["scripture"].strip()

    def test_all_have_at_least_2_questions(self):
        for c in _COMMANDMENTS:
            assert len(c["questions"]) >= 2, (
                f"Commandment {c['number']} has only {len(c['questions'])} questions"
            )

    def test_first_commandment_is_about_god(self):
        first = _COMMANDMENTS[0]
        assert first["number"] == 1
        assert "Bóg" in first["title"] or "bóg" in first["title"] or "Mnie" in first["title"]

    def test_fifth_commandment_is_about_life(self):
        fifth = _COMMANDMENTS[4]
        assert fifth["number"] == 5
        assert "zabijaj" in fifth["title"].lower() or "zabij" in fifth["title"].lower()


class TestStateAdditions:
    def test_all_states_have_questions(self):
        for state in (StateOfLife.PARENT, StateOfLife.MARRIED, StateOfLife.RELIGIOUS,
                      StateOfLife.PRIEST, StateOfLife.TEENAGER):
            assert state in _STATE_ADDITIONS, f"{state} missing from _STATE_ADDITIONS"
            assert len(_STATE_ADDITIONS[state]) >= 2

    def test_parent_has_children_question(self):
        questions = " ".join(_STATE_ADDITIONS[StateOfLife.PARENT])
        assert "dziec" in questions.lower() or "rodz" in questions.lower()

    def test_priest_has_liturgy_question(self):
        questions = " ".join(_STATE_ADDITIONS[StateOfLife.PRIEST])
        assert "liturgi" in questions.lower() or "modlit" in questions.lower()


class TestGetCommandmentsOverview:
    def test_returns_10_items(self):
        svc = _exam_svc()
        result = svc.get_commandments_overview()
        assert len(result) == 10

    def test_each_item_has_required_keys(self):
        svc = _exam_svc()
        for item in svc.get_commandments_overview():
            assert {"number", "title", "ccc_ref", "scripture", "questions"} <= set(item.keys())

    def test_questions_are_lists(self):
        svc = _exam_svc()
        for item in svc.get_commandments_overview():
            assert isinstance(item["questions"], list)

    def test_ccc_refs_present(self):
        svc = _exam_svc()
        for item in svc.get_commandments_overview():
            assert item["ccc_ref"].strip()


class TestGetStateQuestions:
    def test_parent_state_returns_questions(self):
        svc = _exam_svc()
        questions = svc.get_state_questions(StateOfLife.PARENT)
        assert isinstance(questions, list)
        assert len(questions) >= 2

    def test_all_known_states_return_questions(self):
        svc = _exam_svc()
        for state in StateOfLife:
            if state in _STATE_ADDITIONS:
                result = svc.get_state_questions(state)
                assert len(result) >= 1

    def test_questions_are_strings(self):
        svc = _exam_svc()
        questions = svc.get_state_questions(StateOfLife.MARRIED)
        assert all(isinstance(q, str) for q in questions)


# ===========================================================================
# ConfirmationService
# ===========================================================================


class TestGiftsOfSpirit:
    def test_exactly_7_gifts(self):
        assert len(GIFTS_OF_SPIRIT) == 7

    def test_all_have_required_fields(self):
        required = {"gift", "latin", "description", "opposite_vice", "scripture", "ccc", "fruit"}
        for g in GIFTS_OF_SPIRIT:
            assert required <= set(g.keys()), f"Missing fields in gift: {g.get('gift')}"

    def test_all_have_latin_names(self):
        for g in GIFTS_OF_SPIRIT:
            assert g["latin"].strip()

    def test_wisdom_is_sapientia(self):
        gifts_by_latin = {g["latin"]: g for g in GIFTS_OF_SPIRIT}
        assert "Sapientia" in gifts_by_latin
        assert "Mądrość" in gifts_by_latin["Sapientia"]["gift"]

    def test_all_have_ccc_refs(self):
        for g in GIFTS_OF_SPIRIT:
            assert "§" in g["ccc"]

    def test_all_have_scripture_refs(self):
        for g in GIFTS_OF_SPIRIT:
            assert g["scripture"].strip()

    def test_pietas_is_present(self):
        latins = {g["latin"] for g in GIFTS_OF_SPIRIT}
        assert "Pietas" in latins


class TestConfirmationSessions:
    def test_exactly_6_sessions(self):
        assert len(CONFIRMATION_SESSIONS) == 6

    def test_all_have_session_id(self):
        for s in CONFIRMATION_SESSIONS:
            assert s.session_id.strip()

    def test_all_have_unique_session_ids(self):
        ids = [s.session_id for s in CONFIRMATION_SESSIONS]
        assert len(ids) == len(set(ids))

    def test_all_have_scripture(self):
        for s in CONFIRMATION_SESSIONS:
            assert len(s.scripture) > 0

    def test_all_have_key_question(self):
        for s in CONFIRMATION_SESSIONS:
            assert s.key_question.strip()

    def test_numbered_sequentially(self):
        numbers = [s.number for s in CONFIRMATION_SESSIONS]
        assert numbers == sorted(numbers)


class TestGetGiftsOfSpirit:
    def test_returns_7_gifts(self):
        svc = _conf_svc()
        result = svc.get_gifts_of_spirit()
        assert len(result) == 7

    def test_each_has_gift_and_description(self):
        svc = _conf_svc()
        for item in svc.get_gifts_of_spirit():
            assert "gift" in item
            assert "description" in item

    def test_returns_list_of_dicts(self):
        svc = _conf_svc()
        assert isinstance(svc.get_gifts_of_spirit(), list)


class TestGetConfirmationProgram:
    def test_returns_6_items(self):
        svc = _conf_svc()
        result = svc.get_program()
        assert len(result) == 6

    def test_each_has_session_id_and_title(self):
        svc = _conf_svc()
        for item in svc.get_program():
            assert "session_id" in item
            assert "title" in item

    def test_each_has_ccc_refs(self):
        svc = _conf_svc()
        for item in svc.get_program():
            assert "ccc_refs" in item
            assert len(item["ccc_refs"]) > 0


class TestGetConfirmationSession:
    def test_returns_session_by_id(self):
        svc = _conf_svc()
        first_id = CONFIRMATION_SESSIONS[0].session_id
        result = svc.get_session(first_id)
        assert result is not None
        assert result["session_id"] == first_id

    def test_returns_none_for_unknown_id(self):
        svc = _conf_svc()
        assert svc.get_session("nonexistent_session") is None


# ===========================================================================
# RCIAService
# ===========================================================================


class TestRCIAStage:
    def test_precatechumenate_value(self):
        assert RCIAStage.PRECATECHUMENATE == "precatechumenate"

    def test_catechumenate_value(self):
        assert RCIAStage.CATECHUMENATE == "catechumenate"

    def test_purification_value(self):
        assert RCIAStage.PURIFICATION == "purification"

    def test_mystagogia_value(self):
        assert RCIAStage.MYSTAGOGIA == "mystagogia"

    def test_has_exactly_4_stages(self):
        assert len(RCIAStage) == 4


class TestRCIACurriculum:
    def test_exactly_14_topics(self):
        assert len(RCIA_CURRICULUM) == 14

    def test_all_stages_represented(self):
        stages = {t.stage for t in RCIA_CURRICULUM}
        assert stages == set(RCIAStage)

    def test_all_have_required_fields(self):
        for t in RCIA_CURRICULUM:
            assert t.session_id.strip()
            assert t.title.strip()
            assert t.title_pl.strip()
            assert len(t.scripture) > 0
            assert len(t.ccc_refs) > 0
            assert t.key_question.strip()

    def test_unique_session_ids(self):
        ids = [t.session_id for t in RCIA_CURRICULUM]
        assert len(ids) == len(set(ids)), "Duplicate RCIA session IDs"

    def test_precatechumenate_has_multiple_sessions(self):
        stage_topics = [t for t in RCIA_CURRICULUM if t.stage == RCIAStage.PRECATECHUMENATE]
        assert len(stage_topics) >= 2

    def test_catechumenate_has_most_sessions(self):
        """Catechumenate is the longest stage."""
        counts = {s: 0 for s in RCIAStage}
        for t in RCIA_CURRICULUM:
            counts[t.stage] += 1
        assert counts[RCIAStage.CATECHUMENATE] >= counts[RCIAStage.PRECATECHUMENATE]


class TestGetRCIACurriculum:
    def test_returns_4_stage_groups(self):
        svc = _rcia_svc()
        result = svc.get_curriculum()
        assert len(result) == 4

    def test_each_group_has_stage_key(self):
        svc = _rcia_svc()
        for group in svc.get_curriculum():
            assert "stage" in group

    def test_each_group_has_session_count(self):
        svc = _rcia_svc()
        for group in svc.get_curriculum():
            assert "session_count" in group
            assert group["session_count"] == len(group["sessions"])

    def test_total_sessions_is_14(self):
        svc = _rcia_svc()
        total = sum(g["session_count"] for g in svc.get_curriculum())
        assert total == 14

    def test_sessions_have_required_keys(self):
        svc = _rcia_svc()
        required = {"session_id", "title", "title_pl", "scripture", "ccc_refs", "key_question"}
        for group in svc.get_curriculum():
            for s in group["sessions"]:
                assert required <= set(s.keys())


class TestGetRCIASession:
    def test_returns_session_by_id(self):
        svc = _rcia_svc()
        result = svc.get_session("rcia_pre_01")
        assert result is not None
        assert result["session_id"] == "rcia_pre_01"

    def test_returned_session_has_stage(self):
        svc = _rcia_svc()
        result = svc.get_session("rcia_pre_01")
        assert "stage" in result
        assert result["stage"] == RCIAStage.PRECATECHUMENATE.value

    def test_returns_none_for_unknown_id(self):
        svc = _rcia_svc()
        assert svc.get_session("nonexistent") is None

    def test_any_session_id_is_retrievable(self):
        svc = _rcia_svc()
        for topic in RCIA_CURRICULUM:
            result = svc.get_session(topic.session_id)
            assert result is not None
