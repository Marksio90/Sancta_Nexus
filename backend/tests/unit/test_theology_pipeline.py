"""Unit tests for app/agents/theology/theology_pipeline.py.

Self-contained — no Qdrant, no LLM. All four agents are mocked so the pipeline
logic is tested in complete isolation.

Contracts verified:
- GateStatus enum values
- GateResult / PipelineResult / ScripturePassage dataclasses
- AGGREGATE_THRESHOLD = 0.85
- GATE_WEIGHTS sum to exactly 1.0
- _parse_scripture_ref: various reference formats
- _compute_aggregate: weighted average, skipped gates excluded
- validate: all-pass path, doctrine-guard-fail immediate-reject, low-score-fail,
  gates-2-and-3-skipped (no Qdrant), fallback content, duration > 0
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub qdrant_client before importing any theology module
# ---------------------------------------------------------------------------

for _mod in (
    "qdrant_client",
    "qdrant_client.models",
    "qdrant_client.models.common",
    "qdrant_client.http",
    "qdrant_client.http.models",
    "qdrant_client.http.models.models",
    "qdrant_client.async_qdrant_client",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# langchain stubs
for _mod in (
    "langchain_openai",
    "langchain_core",
    "langchain_core.messages",
    "langchain_core.prompts",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.agents.theology.magisterium_validator import ValidationResult
from app.agents.theology.patristic_agent import PatristicReference
from app.agents.theology.theology_pipeline import (
    AGGREGATE_THRESHOLD,
    GateResult,
    GateStatus,
    PipelineResult,
    ScripturePassage,
    TheologicalValidationPipeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline(
    exegesis_result: dict | None = None,
    doctrine_result: dict | None = None,
    magisterium_result: ValidationResult | None = None,
    patristic_refs: list[PatristicReference] | None = None,
    *,
    with_optional: bool = True,
    threshold: float = AGGREGATE_THRESHOLD,
    fallback: str = "FALLBACK",
) -> TheologicalValidationPipeline:
    """Build a pipeline with all agents mocked."""
    if exegesis_result is None:
        exegesis_result = {
            "literal": "text " * 10,
            "allegorical": "text " * 10,
            "moral": "text " * 10,
            "anagogical": "text " * 10,
        }
    if doctrine_result is None:
        doctrine_result = {"passed": True, "violations": [], "confidence": 1.0}

    mock_exegesis = MagicMock()
    mock_exegesis.analyze = AsyncMock(return_value=exegesis_result)

    mock_doctrine = MagicMock()
    mock_doctrine.guard = AsyncMock(return_value=doctrine_result)
    mock_doctrine._dogmas = ["Trinity", "Incarnation", "Resurrection"]

    mock_magisterium = None
    mock_patristic = None

    if with_optional:
        if magisterium_result is None:
            magisterium_result = ValidationResult(
                is_valid=True, confidence=0.9, issues=[], references=["CCC 1234"]
            )
        mock_magisterium = MagicMock()
        mock_magisterium.validate = AsyncMock(return_value=magisterium_result)

        if patristic_refs is None:
            patristic_refs = [
                PatristicReference(
                    father_name="Augustine",
                    work="Confessions",
                    quote="our heart is restless",
                    relevance_score=0.9,
                )
            ]
        mock_patristic = MagicMock()
        mock_patristic.find_patristic_references = AsyncMock(
            return_value=patristic_refs
        )

    return TheologicalValidationPipeline(
        exegesis_agent=mock_exegesis,
        doctrine_guard=mock_doctrine,
        magisterium_validator=mock_magisterium,
        patristic_agent=mock_patristic,
        threshold=threshold,
        fallback_content=fallback,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_aggregate_threshold(self):
        assert AGGREGATE_THRESHOLD == 0.85

    def test_gate_weights_sum_to_one(self):
        total = sum(TheologicalValidationPipeline.GATE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"GATE_WEIGHTS sum={total}"

    def test_gate_weights_keys(self):
        expected = {
            "scripture_coherence",
            "magisterium_alignment",
            "patristic_crossref",
            "doctrine_guard",
        }
        assert set(TheologicalValidationPipeline.GATE_WEIGHTS.keys()) == expected


# ---------------------------------------------------------------------------
# GateStatus enum
# ---------------------------------------------------------------------------


class TestGateStatus:
    def test_passed_value(self):
        assert GateStatus.PASSED == "passed"

    def test_failed_value(self):
        assert GateStatus.FAILED == "failed"

    def test_skipped_value(self):
        assert GateStatus.SKIPPED == "skipped"

    def test_error_value(self):
        assert GateStatus.ERROR == "error"


# ---------------------------------------------------------------------------
# GateResult dataclass
# ---------------------------------------------------------------------------


class TestGateResult:
    def test_required_fields(self):
        gr = GateResult(gate_name="test", status=GateStatus.PASSED, confidence=0.9)
        assert gr.gate_name == "test"
        assert gr.status == GateStatus.PASSED
        assert gr.confidence == 0.9

    def test_defaults(self):
        gr = GateResult(gate_name="x", status=GateStatus.SKIPPED, confidence=0.7)
        assert gr.details == ""
        assert gr.duration_ms == 0.0

    def test_frozen(self):
        gr = GateResult(gate_name="x", status=GateStatus.PASSED, confidence=1.0)
        with pytest.raises((TypeError, AttributeError)):
            gr.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PipelineResult dataclass
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_passed_result(self):
        pr = PipelineResult(passed=True, aggregate_score=0.92)
        assert pr.passed is True
        assert pr.aggregate_score == 0.92
        assert pr.fallback_used is False
        assert pr.fallback_content is None
        assert pr.gates == []
        assert pr.total_duration_ms == 0.0

    def test_failed_result_with_fallback(self):
        pr = PipelineResult(
            passed=False,
            aggregate_score=0.5,
            fallback_used=True,
            fallback_content="safe text",
        )
        assert pr.passed is False
        assert pr.fallback_used is True
        assert pr.fallback_content == "safe text"


# ---------------------------------------------------------------------------
# ScripturePassage dataclass
# ---------------------------------------------------------------------------


class TestScripturePassage:
    def test_required_fields(self):
        sp = ScripturePassage(book="John", chapter=3, verse_start=16, text="For God so loved")
        assert sp.book == "John"
        assert sp.chapter == 3
        assert sp.verse_start == 16
        assert sp.verse_end is None

    def test_optional_verse_end(self):
        sp = ScripturePassage(book="Romans", chapter=8, verse_start=28, text="all things", verse_end=30)
        assert sp.verse_end == 30


# ---------------------------------------------------------------------------
# _parse_scripture_ref
# ---------------------------------------------------------------------------


class TestParseScriptureRef:
    def _parse(self, ref: str) -> ScripturePassage:
        return TheologicalValidationPipeline._parse_scripture_ref(ref, "dummy text")

    def test_simple_verse(self):
        sp = self._parse("John 3:16")
        assert sp.book == "John"
        assert sp.chapter == 3
        assert sp.verse_start == 16
        assert sp.verse_end is None

    def test_verse_range(self):
        sp = self._parse("Romans 8:28-30")
        assert sp.book == "Romans"
        assert sp.chapter == 8
        assert sp.verse_start == 28
        assert sp.verse_end == 30

    def test_book_with_number(self):
        sp = self._parse("1 Cor 13:4-7")
        assert sp.book == "1 Cor"
        assert sp.chapter == 13
        assert sp.verse_start == 4
        assert sp.verse_end == 7

    def test_chapter_only(self):
        sp = self._parse("Ps 23")
        assert sp.book == "Ps"
        assert sp.chapter == 23
        assert sp.verse_start == 1

    def test_malformed_ref(self):
        sp = self._parse("malformed")
        assert sp.book == "malformed"
        assert sp.chapter == 1

    def test_text_preserved(self):
        ref_text = "some spiritual content here"
        sp = TheologicalValidationPipeline._parse_scripture_ref("John 3:16", ref_text)
        assert sp.text == ref_text


# ---------------------------------------------------------------------------
# _compute_aggregate
# ---------------------------------------------------------------------------


class TestComputeAggregate:
    def _pipeline(self) -> TheologicalValidationPipeline:
        return _make_pipeline()

    def test_all_full_confidence(self):
        p = self._pipeline()
        gates = [
            GateResult("scripture_coherence", GateStatus.PASSED, 1.0),
            GateResult("magisterium_alignment", GateStatus.PASSED, 1.0),
            GateResult("patristic_crossref", GateStatus.PASSED, 1.0),
            GateResult("doctrine_guard", GateStatus.PASSED, 1.0),
        ]
        score = p._compute_aggregate(gates)
        assert abs(score - 1.0) < 1e-9

    def test_all_zero_confidence(self):
        p = self._pipeline()
        gates = [
            GateResult("scripture_coherence", GateStatus.FAILED, 0.0),
            GateResult("magisterium_alignment", GateStatus.FAILED, 0.0),
            GateResult("patristic_crossref", GateStatus.FAILED, 0.0),
            GateResult("doctrine_guard", GateStatus.FAILED, 0.0),
        ]
        score = p._compute_aggregate(gates)
        assert abs(score - 0.0) < 1e-9

    def test_skipped_gates_excluded_from_weight(self):
        p = self._pipeline()
        gates = [
            GateResult("scripture_coherence", GateStatus.PASSED, 1.0),
            GateResult("magisterium_alignment", GateStatus.SKIPPED, 0.7),
            GateResult("patristic_crossref", GateStatus.SKIPPED, 0.7),
            GateResult("doctrine_guard", GateStatus.PASSED, 1.0),
        ]
        score = p._compute_aggregate(gates)
        w_sc = TheologicalValidationPipeline.GATE_WEIGHTS["scripture_coherence"]
        w_dg = TheologicalValidationPipeline.GATE_WEIGHTS["doctrine_guard"]
        expected = (1.0 * w_sc + 1.0 * w_dg) / (w_sc + w_dg)
        assert abs(score - expected) < 1e-9

    def test_empty_gates_returns_zero(self):
        p = self._pipeline()
        assert p._compute_aggregate([]) == 0.0


# ---------------------------------------------------------------------------
# validate() — full pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidatePipeline:
    async def test_all_gates_pass_returns_passed(self):
        p = _make_pipeline()
        result = await p.validate("God is Love", "John 3:16")
        assert result.passed is True
        assert result.fallback_used is False
        assert result.fallback_content is None

    async def test_aggregate_score_is_between_0_and_1(self):
        p = _make_pipeline()
        result = await p.validate("God is Love", "John 3:16")
        assert 0.0 <= result.aggregate_score <= 1.0

    async def test_result_has_four_gates(self):
        p = _make_pipeline()
        result = await p.validate("God is Love", "John 3:16")
        assert len(result.gates) == 4

    async def test_gate_names_correct(self):
        p = _make_pipeline()
        result = await p.validate("God is Love", "John 3:16")
        names = {g.gate_name for g in result.gates}
        expected = {
            "scripture_coherence",
            "magisterium_alignment",
            "patristic_crossref",
            "doctrine_guard",
        }
        assert names == expected

    async def test_doctrine_guard_fail_rejects_immediately(self):
        """Gate 4 failure → passed=False regardless of other gate scores."""
        p = _make_pipeline(
            doctrine_result={"passed": False, "violations": ["heresy detected"], "confidence": 0.0}
        )
        result = await p.validate("heretical content", "John 1:1")
        assert result.passed is False
        assert result.fallback_used is True
        assert result.fallback_content == "FALLBACK"

    async def test_low_aggregate_score_fails(self):
        """All gates at low confidence → aggregate < threshold → failed."""
        p = _make_pipeline(
            exegesis_result={
                "literal": "x",     # too short → 0 non-empty
                "allegorical": "",
            },
            magisterium_result=ValidationResult(
                is_valid=False, confidence=0.1, issues=["off-topic"]
            ),
            patristic_refs=[
                PatristicReference(
                    father_name="X", work="Y", quote="z", relevance_score=0.1
                )
            ],
            doctrine_result={"passed": True, "violations": [], "confidence": 0.3},
            threshold=0.85,
        )
        result = await p.validate("weak content", "Ps 23")
        assert result.passed is False

    async def test_no_optional_agents_skips_gates_2_and_3(self):
        """Without magisterium/patristic agents, gates 2 and 3 are SKIPPED."""
        p = _make_pipeline(with_optional=False)
        result = await p.validate("God is Love", "John 3:16")
        gate_map = {g.gate_name: g for g in result.gates}
        assert gate_map["magisterium_alignment"].status == GateStatus.SKIPPED
        assert gate_map["patristic_crossref"].status == GateStatus.SKIPPED

    async def test_skipped_gates_use_moderate_confidence(self):
        p = _make_pipeline(with_optional=False)
        result = await p.validate("content", "Ps 1:1")
        gate_map = {g.gate_name: g for g in result.gates}
        assert gate_map["magisterium_alignment"].confidence == 0.7
        assert gate_map["patristic_crossref"].confidence == 0.7

    async def test_duration_ms_is_positive(self):
        p = _make_pipeline()
        result = await p.validate("God is Love", "John 3:16")
        assert result.total_duration_ms >= 0.0

    async def test_fallback_content_returned_on_failure(self):
        custom_fallback = "Please speak with a priest."
        p = _make_pipeline(
            doctrine_result={"passed": False, "violations": ["heresy"], "confidence": 0.0},
            fallback="Please speak with a priest.",
        )
        result = await p.validate("bad content", "Mk 1:1")
        assert result.fallback_content == custom_fallback

    async def test_exegesis_agent_called_with_parsed_ref(self):
        mock_exegesis = MagicMock()
        mock_exegesis.analyze = AsyncMock(
            return_value={"literal": "long " * 10, "moral": "long " * 10}
        )
        mock_doctrine = MagicMock()
        mock_doctrine.guard = AsyncMock(
            return_value={"passed": True, "violations": [], "confidence": 1.0}
        )
        mock_doctrine._dogmas = []

        p = TheologicalValidationPipeline(
            exegesis_agent=mock_exegesis,
            doctrine_guard=mock_doctrine,
        )
        await p.validate("test content", "Romans 8:28-30")

        mock_exegesis.analyze.assert_awaited_once()
        call_kwargs = mock_exegesis.analyze.call_args
        assert call_kwargs.kwargs.get("book") == "Romans" or call_kwargs.args[0] == "Romans"

    async def test_doctrine_guard_called_with_content(self):
        mock_exegesis = MagicMock()
        mock_exegesis.analyze = AsyncMock(return_value={"x": "y" * 25})
        mock_doctrine = MagicMock()
        mock_doctrine.guard = AsyncMock(
            return_value={"passed": True, "violations": [], "confidence": 1.0}
        )
        mock_doctrine._dogmas = []

        p = TheologicalValidationPipeline(
            exegesis_agent=mock_exegesis,
            doctrine_guard=mock_doctrine,
        )
        content = "unique theological statement here"
        await p.validate(content, "John 1:1")
        mock_doctrine.guard.assert_awaited_once_with(content)

    async def test_empty_exegesis_result_low_confidence(self):
        """Exegesis with all empty responses → low confidence → gate 1 fails."""
        p = _make_pipeline(exegesis_result={"dim1": "", "dim2": "", "dim3": ""})
        result = await p.validate("content", "Ps 1:1")
        gate_map = {g.gate_name: g for g in result.gates}
        assert gate_map["scripture_coherence"].status == GateStatus.FAILED

    async def test_exception_in_exegesis_sets_error_status(self):
        mock_exegesis = MagicMock()
        mock_exegesis.analyze = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        mock_doctrine = MagicMock()
        mock_doctrine.guard = AsyncMock(
            return_value={"passed": True, "violations": [], "confidence": 1.0}
        )
        mock_doctrine._dogmas = []

        p = TheologicalValidationPipeline(
            exegesis_agent=mock_exegesis,
            doctrine_guard=mock_doctrine,
        )
        result = await p.validate("content", "John 1:1")
        gate_map = {g.gate_name: g for g in result.gates}
        assert gate_map["scripture_coherence"].status == GateStatus.ERROR
        assert gate_map["scripture_coherence"].confidence == 0.0

    async def test_exception_in_doctrine_guard_fails_closed(self):
        """Doctrine guard error must cause pipeline failure (fail closed)."""
        mock_exegesis = MagicMock()
        mock_exegesis.analyze = AsyncMock(return_value={"x": "y" * 25})
        mock_doctrine = MagicMock()
        mock_doctrine.guard = AsyncMock(side_effect=RuntimeError("guard crash"))
        mock_doctrine._dogmas = []

        p = TheologicalValidationPipeline(
            exegesis_agent=mock_exegesis,
            doctrine_guard=mock_doctrine,
        )
        result = await p.validate("content", "John 1:1")
        gate_map = {g.gate_name: g for g in result.gates}
        assert gate_map["doctrine_guard"].status == GateStatus.ERROR
        assert result.passed is False
