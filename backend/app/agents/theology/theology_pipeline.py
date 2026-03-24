"""
TheologicalValidationPipeline - Orchestrates the four-gate theology validation.

Gates (in order):
  1. Scripture Coherence   - ExegesisAgent checks biblical grounding
  2. Magisterium Alignment - MagisteriumValidator checks Church teaching
  3. Patristic Cross-Ref   - PatristicAgent verifies patristic support
  4. Doctrine Guard         - DoctrineGuardAgent enforces dogmatic fidelity

Content passes only if the aggregate score exceeds 0.85.
If validation fails, the pipeline falls back to safe, pre-approved content.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .magisterium_validator import MagisteriumValidator, ValidationResult
from .patristic_agent import PatristicAgent, PatristicReference
from .exegesis_agent import ExegesisAgent
from .doctrine_guard import DoctrineGuardAgent

logger = logging.getLogger(__name__)

AGGREGATE_THRESHOLD = 0.85


class GateStatus(str, Enum):
    """Status of an individual pipeline gate."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class GateResult:
    """Result from a single pipeline gate."""

    gate_name: str
    status: GateStatus
    confidence: float
    details: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Complete result of the theological validation pipeline."""

    passed: bool
    aggregate_score: float
    gates: list[GateResult] = field(default_factory=list)
    fallback_used: bool = False
    fallback_content: str | None = None
    total_duration_ms: float = 0.0


# Default safe fallback content when validation fails.
_DEFAULT_FALLBACK = (
    "We are unable to provide a validated response at this time. "
    "Please consult the Catechism of the Catholic Church or speak "
    "with a qualified spiritual director for guidance on this topic."
)


class TheologicalValidationPipeline:
    """
    Orchestrates the four-gate theological validation pipeline.

    Each gate contributes a confidence score. Content passes only if
    the aggregate weighted score exceeds the threshold (0.85).
    """

    # Gate weights for aggregate scoring
    GATE_WEIGHTS = {
        "scripture_coherence": 0.25,
        "magisterium_alignment": 0.30,
        "patristic_crossref": 0.15,
        "doctrine_guard": 0.30,
    }

    def __init__(
        self,
        exegesis_agent: ExegesisAgent,
        doctrine_guard: DoctrineGuardAgent,
        *,
        magisterium_validator: MagisteriumValidator | None = None,
        patristic_agent: PatristicAgent | None = None,
        threshold: float = AGGREGATE_THRESHOLD,
        fallback_content: str = _DEFAULT_FALLBACK,
    ) -> None:
        """
        Args:
            exegesis_agent: ExegesisAgent instance for Gate 1.
            doctrine_guard: DoctrineGuardAgent for Gate 4 (CRITICAL).
            magisterium_validator: Optional MagisteriumValidator for Gate 2.
                When None, Gate 2 is skipped with moderate confidence.
            patristic_agent: Optional PatristicAgent for Gate 3.
                When None, Gate 3 is skipped with moderate confidence.
            threshold: Minimum aggregate score to pass (default 0.85).
            fallback_content: Safe content to return on failure.
        """
        self._exegesis = exegesis_agent
        self._magisterium = magisterium_validator
        self._patristic = patristic_agent
        self._doctrine = doctrine_guard
        self._threshold = threshold
        self._fallback_content = fallback_content

    async def validate(
        self,
        content: str,
        scripture_context: str,
    ) -> PipelineResult:
        """
        Run the full four-gate validation pipeline.

        The pipeline executes gates sequentially. If the Doctrine Guard
        (Gate 4) fails, the content is immediately rejected regardless
        of other scores.

        Args:
            content: The theological content to validate.
            scripture_context: Scripture reference for context, e.g.
                "John 3:16" or "Romans 8:28-30".

        Returns:
            PipelineResult with aggregate score and per-gate details.
        """
        pipeline_start = time.monotonic()
        gate_results: list[GateResult] = []

        logger.info(
            "Starting theological validation pipeline "
            "(threshold=%.2f, scripture=%s)",
            self._threshold,
            scripture_context,
        )

        # --- Gate 1: Scripture Coherence ---
        gate1 = await self._gate_scripture_coherence(content, scripture_context)
        gate_results.append(gate1)
        logger.info(
            "Gate 1 (Scripture Coherence): %s (confidence=%.4f)",
            gate1.status.value,
            gate1.confidence,
        )

        # --- Gate 2: Magisterium Alignment ---
        gate2 = await self._gate_magisterium_alignment(content)
        gate_results.append(gate2)
        logger.info(
            "Gate 2 (Magisterium Alignment): %s (confidence=%.4f)",
            gate2.status.value,
            gate2.confidence,
        )

        # --- Gate 3: Patristic Cross-Reference ---
        gate3 = await self._gate_patristic_crossref(content, scripture_context)
        gate_results.append(gate3)
        logger.info(
            "Gate 3 (Patristic Cross-Ref): %s (confidence=%.4f)",
            gate3.status.value,
            gate3.confidence,
        )

        # --- Gate 4: Doctrine Guard (CRITICAL) ---
        gate4 = await self._gate_doctrine_guard(content)
        gate_results.append(gate4)
        logger.info(
            "Gate 4 (Doctrine Guard): %s (confidence=%.4f)",
            gate4.status.value,
            gate4.confidence,
        )

        # Calculate aggregate score
        aggregate_score = self._compute_aggregate(gate_results)
        total_duration = (time.monotonic() - pipeline_start) * 1000

        # Doctrine Guard failure is an immediate rejection
        doctrine_failed = gate4.status in (GateStatus.FAILED, GateStatus.ERROR)
        passed = aggregate_score >= self._threshold and not doctrine_failed

        if not passed:
            reason = "doctrine guard violation" if doctrine_failed else (
                f"aggregate score {aggregate_score:.4f} < {self._threshold}"
            )
            logger.warning(
                "Theological validation FAILED: %s", reason
            )

            return PipelineResult(
                passed=False,
                aggregate_score=round(aggregate_score, 4),
                gates=gate_results,
                fallback_used=True,
                fallback_content=self._fallback_content,
                total_duration_ms=round(total_duration, 2),
            )

        logger.info(
            "Theological validation PASSED (aggregate=%.4f)",
            aggregate_score,
        )

        return PipelineResult(
            passed=True,
            aggregate_score=round(aggregate_score, 4),
            gates=gate_results,
            total_duration_ms=round(total_duration, 2),
        )

    # --- Individual Gate Implementations ---

    async def _gate_scripture_coherence(
        self, content: str, scripture_ref: str
    ) -> GateResult:
        """Gate 1: Verify scripture coherence via ExegesisAgent (A-018)."""
        start = time.monotonic()

        try:
            passage = self._parse_scripture_ref(scripture_ref, content)
            result: dict[str, str] = await self._exegesis.analyze(
                book=passage.book,
                chapter=passage.chapter,
                verse_start=passage.verse_start,
                verse_end=passage.verse_end if passage.verse_end else passage.verse_start,
                text=passage.text,
            )
            # Confidence: proportion of dimensions with non-empty responses
            non_empty = sum(1 for v in result.values() if v and len(v) > 20)
            total_dims = max(len(result), 1)
            confidence = round(non_empty / total_dims, 4)
            status = GateStatus.PASSED if confidence >= 0.5 else GateStatus.FAILED
            details = (
                f"Exegesis confidence={confidence:.4f}, "
                f"dimensions analysed={total_dims}"
            )
        except Exception as exc:
            logger.exception("Gate 1 (Scripture Coherence) error")
            confidence = 0.0
            status = GateStatus.ERROR
            details = f"Error: {exc}"

        duration = (time.monotonic() - start) * 1000
        return GateResult(
            gate_name="scripture_coherence",
            status=status,
            confidence=round(confidence, 4),
            details=details,
            duration_ms=round(duration, 2),
        )

    async def _gate_magisterium_alignment(self, content: str) -> GateResult:
        """Gate 2: Validate against Magisterium sources (requires Qdrant)."""
        start = time.monotonic()

        if self._magisterium is None:
            duration = (time.monotonic() - start) * 1000
            return GateResult(
                gate_name="magisterium_alignment",
                status=GateStatus.SKIPPED,
                confidence=0.7,  # moderate confidence when skipped
                details="MagisteriumValidator not configured (no Qdrant); gate skipped.",
                duration_ms=round(duration, 2),
            )

        try:
            result: ValidationResult = await self._magisterium.validate(content)
            confidence = result.confidence
            status = GateStatus.PASSED if result.is_valid else GateStatus.FAILED
            details = (
                f"Valid={result.is_valid}, "
                f"references={len(result.references)}, "
                f"issues={len(result.issues)}"
            )
            if result.issues:
                details += f"; {'; '.join(result.issues[:3])}"
        except Exception as exc:
            logger.exception("Gate 2 (Magisterium Alignment) error")
            confidence = 0.0
            status = GateStatus.ERROR
            details = f"Error: {exc}"

        duration = (time.monotonic() - start) * 1000
        return GateResult(
            gate_name="magisterium_alignment",
            status=status,
            confidence=round(confidence, 4),
            details=details,
            duration_ms=round(duration, 2),
        )

    async def _gate_patristic_crossref(
        self, content: str, scripture_ref: str
    ) -> GateResult:
        """Gate 3: Cross-reference with patristic sources (requires Qdrant)."""
        start = time.monotonic()

        if self._patristic is None:
            duration = (time.monotonic() - start) * 1000
            return GateResult(
                gate_name="patristic_crossref",
                status=GateStatus.SKIPPED,
                confidence=0.7,
                details="PatristicAgent not configured (no Qdrant); gate skipped.",
                duration_ms=round(duration, 2),
            )

        try:
            refs: list[PatristicReference] = (
                await self._patristic.find_patristic_references(
                    scripture_ref, content
                )
            )
            if refs:
                avg_relevance = sum(r.relevance_score for r in refs) / len(refs)
                confidence = min(avg_relevance, 1.0)
            else:
                confidence = 0.0

            status = (
                GateStatus.PASSED if len(refs) >= 1 and confidence >= 0.5
                else GateStatus.FAILED
            )
            fathers = list({r.father_name for r in refs})
            details = (
                f"Found {len(refs)} references from {len(fathers)} Fathers; "
                f"avg_relevance={confidence:.4f}"
            )
        except Exception as exc:
            logger.exception("Gate 3 (Patristic Cross-Ref) error")
            confidence = 0.0
            status = GateStatus.ERROR
            details = f"Error: {exc}"

        duration = (time.monotonic() - start) * 1000
        return GateResult(
            gate_name="patristic_crossref",
            status=status,
            confidence=round(confidence, 4),
            details=details,
            duration_ms=round(duration, 2),
        )

    async def _gate_doctrine_guard(self, content: str) -> GateResult:
        """Gate 4: Final doctrine safety check via DoctrineGuardAgent (A-021). CRITICAL."""
        start = time.monotonic()

        try:
            result: dict = await self._doctrine.guard(content)
            passed: bool = result.get("passed", False)
            violations: list[str] = result.get("violations", [])
            confidence = result.get("confidence", 1.0 if passed else 0.0)
            status = GateStatus.PASSED if passed else GateStatus.FAILED
            details = (
                f"Checked {len(self._doctrine._dogmas)} dogmas, "
                f"violations={len(violations)}"
            )
            if violations:
                details += f"; {'; '.join(violations[:3])}"
        except Exception as exc:
            logger.exception("Gate 4 (Doctrine Guard) error - FAILING CLOSED")
            confidence = 0.0
            status = GateStatus.ERROR
            details = f"Error: {exc}. Failing closed for safety."

        duration = (time.monotonic() - start) * 1000
        return GateResult(
            gate_name="doctrine_guard",
            status=status,
            confidence=round(confidence, 4),
            details=details,
            duration_ms=round(duration, 2),
        )

    # --- Helpers ---

    def _compute_aggregate(self, gates: list[GateResult]) -> float:
        """Compute the weighted aggregate score from gate results."""
        total_score = 0.0
        total_weight = 0.0

        for gate in gates:
            weight = self.GATE_WEIGHTS.get(gate.gate_name, 0.0)
            if gate.status == GateStatus.SKIPPED:
                continue
            total_score += gate.confidence * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0

        return total_score / total_weight

    @staticmethod
    def _parse_scripture_ref(ref: str, text: str) -> ScripturePassage:
        """
        Parse a scripture reference string into a ScripturePassage.

        Handles formats like "John 3:16", "Romans 8:28-30", "1 Cor 13:4-7".
        """
        ref = ref.strip()

        # Split book from chapter:verse
        parts = ref.rsplit(" ", 1)
        if len(parts) != 2:
            return ScripturePassage(book=ref, chapter=1, verse_start=1, text=text)

        book = parts[0]
        chapter_verse = parts[1]

        if ":" not in chapter_verse:
            try:
                chapter = int(chapter_verse)
            except ValueError:
                chapter = 1
            return ScripturePassage(
                book=book, chapter=chapter, verse_start=1, text=text
            )

        ch_str, verse_str = chapter_verse.split(":", 1)
        try:
            chapter = int(ch_str)
        except ValueError:
            chapter = 1

        if "-" in verse_str:
            v_parts = verse_str.split("-", 1)
            try:
                verse_start = int(v_parts[0])
                verse_end = int(v_parts[1])
            except ValueError:
                verse_start = 1
                verse_end = None
        else:
            try:
                verse_start = int(verse_str)
            except ValueError:
                verse_start = 1
            verse_end = None

        return ScripturePassage(
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            text=text,
        )
