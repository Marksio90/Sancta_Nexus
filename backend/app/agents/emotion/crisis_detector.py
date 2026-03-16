"""
CrisisDetectorAgent (A-026) - Spiritual and emotional crisis detection.

SAFETY-CRITICAL COMPONENT.

Detects indicators of spiritual or emotional crisis including suicidal
ideation, severe depression, and spiritual abuse. Always provides
human resources: helpline numbers and spiritual director contact info.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class CrisisSeverity(str, Enum):
    """Severity levels for detected crises."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class CrisisResult:
    """Result of crisis detection analysis."""

    is_crisis: bool
    severity: str
    concerns: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)


# Emergency resources - ALWAYS included when any crisis is detected
_EMERGENCY_RESOURCES: list[str] = [
    "National Suicide Prevention Lifeline: 988 (US) - call or text 24/7",
    "Crisis Text Line: Text HOME to 741741 (US)",
    "International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/",
    "Samaritans (UK/Ireland): 116 123 - free 24/7",
    "Telefon Zaufania (Poland): 116 123",
    "Catholic Charities Crisis Line: 1-800-227-2345",
    "Contact your local parish for a referral to a spiritual director",
    "If you are in immediate danger, call emergency services: 911 (US), 112 (EU), 999 (UK)",
]

# Pastoral resources for lower-severity spiritual concerns
_PASTORAL_RESOURCES: list[str] = [
    "Speak with a trusted priest, spiritual director, or pastoral counsellor",
    "Contact your parish office for spiritual direction referrals",
    "Catholic Charities counselling services: https://www.catholiccharitiesusa.org",
    "Consider the Sacrament of Reconciliation for spiritual peace",
]

# Keyword and pattern sets for rapid pre-screening
_SUICIDAL_PATTERNS: list[str] = [
    r"\bsuicid\w*\b",
    r"\bkill\s+(my|him|her|them)?self\b",
    r"\bend\s+(my|this)\s+life\b",
    r"\bwant\s+to\s+die\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bbetter\s+off\s+dead\b",
    r"\bdon'?t\s+want\s+to\s+(be\s+)?alive\b",
    r"\bwish\s+I\s+(was|were)\s+dead\b",
    r"\bgoodbye\s+(cruel\s+)?world\b",
    r"\bself[- ]?harm\b",
    r"\bcut(ting)?\s+my(self)?\b",
]

_SEVERE_DEPRESSION_PATTERNS: list[str] = [
    r"\bhopeless\b",
    r"\bworthless\b",
    r"\bno\s+hope\b",
    r"\bcan'?t\s+go\s+on\b",
    r"\bgive\s+up\b",
    r"\btoo\s+much\s+pain\b",
    r"\bno\s+point\b",
    r"\bnothing\s+matters\b",
    r"\bexhausted\s+of\s+living\b",
]

_SPIRITUAL_ABUSE_PATTERNS: list[str] = [
    r"\bspiritual\s+abuse\b",
    r"\bmanipulat\w+\s+(by\s+)?(priest|pastor|minister|leader)\b",
    r"\bforced\s+to\s+(pray|confess|believe)\b",
    r"\bcoerced\s+by\s+(church|religious)\b",
    r"\b(priest|pastor|minister)\s+(hurt|abused|molested|assaulted)\b",
    r"\breligious\s+trauma\b",
    r"\bspiritual\s+coercion\b",
]

_LLM_SYSTEM_PROMPT = (
    "You are a crisis detection system for a Catholic spiritual guidance "
    "application. Your ONLY task is to evaluate whether the user's text "
    "and emotional state indicate a crisis that requires intervention.\n\n"
    "CRISIS CATEGORIES:\n"
    "1. Suicidal ideation - Any expression of desire to end one's life\n"
    "2. Severe depression - Deep hopelessness, worthlessness, inability to function\n"
    "3. Self-harm - Intent or active self-harming behaviour\n"
    "4. Spiritual abuse - Being harmed by religious authority figures\n"
    "5. Severe spiritual crisis - Extreme despair or loss of faith causing danger\n\n"
    "SEVERITY LEVELS:\n"
    "- none: No crisis detected\n"
    "- low: Mild distress, pastoral support recommended\n"
    "- moderate: Significant distress, professional support recommended\n"
    "- high: Serious crisis, immediate professional support needed\n"
    "- critical: Imminent danger, emergency intervention required\n\n"
    "IMPORTANT:\n"
    "- Err on the side of caution. If uncertain, classify higher.\n"
    "- Never dismiss or minimise someone's pain.\n"
    "- The dark night of the soul is NOT inherently a crisis unless combined "
    "with suicidal ideation or severe depression.\n"
    "- Normal spiritual struggles and doubts are NOT crises.\n\n"
    "Return a JSON object with:\n"
    '- "is_crisis": boolean\n'
    '- "severity": one of none/low/moderate/high/critical\n'
    '- "concerns": list of specific concerns identified\n\n'
    "Return ONLY the JSON object."
)


class CrisisDetectorAgent:
    """
    A-026: Detects spiritual and emotional crises.

    SAFETY-CRITICAL: This component must ALWAYS err on the side of caution.
    When any crisis indicators are detected, human resources are provided.
    """

    AGENT_ID = "A-026"
    AGENT_NAME = "CrisisDetectorAgent"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> None:
        """
        Args:
            model: OpenAI model identifier.
            temperature: Zero temperature for deterministic classification.
            max_tokens: Maximum tokens for response.
        """
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._suicidal_re = [re.compile(p, re.IGNORECASE) for p in _SUICIDAL_PATTERNS]
        self._depression_re = [
            re.compile(p, re.IGNORECASE) for p in _SEVERE_DEPRESSION_PATTERNS
        ]
        self._abuse_re = [
            re.compile(p, re.IGNORECASE) for p in _SPIRITUAL_ABUSE_PATTERNS
        ]

    async def check(
        self,
        text: str,
        emotion_vector: dict[str, float],
    ) -> CrisisResult:
        """
        Check text and emotional state for crisis indicators.

        SAFETY-CRITICAL: Always provides human resources when crisis detected.

        Args:
            text: The user's text to analyse.
            emotion_vector: Dict mapping emotions to probabilities (0-1).

        Returns:
            CrisisResult with crisis determination, severity, and resources.
        """
        logger.info("[%s] Running crisis detection check", self.AGENT_ID)

        # Stage 1: Rapid keyword pre-screening
        keyword_result = self._keyword_prescreen(text)

        # If keyword screening finds CRITICAL indicators, respond immediately
        # without waiting for LLM
        if keyword_result and keyword_result.severity == CrisisSeverity.CRITICAL.value:
            logger.warning(
                "[%s] CRITICAL crisis detected via keyword pre-screening",
                self.AGENT_ID,
            )
            return keyword_result

        # Stage 2: LLM-based analysis for nuanced detection
        llm_result = await self._llm_analysis(text, emotion_vector)

        # Stage 3: Merge results - take the higher severity
        final = self._merge_results(keyword_result, llm_result)

        if final.is_crisis:
            logger.warning(
                "[%s] Crisis detected: severity=%s, concerns=%s",
                self.AGENT_ID,
                final.severity,
                final.concerns,
            )
        else:
            logger.info("[%s] No crisis detected", self.AGENT_ID)

        return final

    def _keyword_prescreen(self, text: str) -> CrisisResult | None:
        """
        Rapid keyword-based pre-screening for crisis indicators.

        Returns a CrisisResult if patterns match, None otherwise.
        """
        concerns: list[str] = []
        max_severity = CrisisSeverity.NONE

        # Check suicidal patterns - CRITICAL
        for pattern in self._suicidal_re:
            if pattern.search(text):
                concerns.append("Potential suicidal ideation detected")
                max_severity = CrisisSeverity.CRITICAL
                break

        # Check severe depression patterns - HIGH
        depression_matches = sum(
            1 for p in self._depression_re if p.search(text)
        )
        if depression_matches >= 2:
            concerns.append("Multiple severe depression indicators detected")
            if max_severity.value < CrisisSeverity.HIGH.value:
                max_severity = CrisisSeverity.HIGH
        elif depression_matches == 1:
            concerns.append("Depression indicator detected")
            if max_severity == CrisisSeverity.NONE:
                max_severity = CrisisSeverity.MODERATE

        # Check spiritual abuse patterns - HIGH
        for pattern in self._abuse_re:
            if pattern.search(text):
                concerns.append("Spiritual abuse indicator detected")
                if max_severity.value < CrisisSeverity.HIGH.value:
                    max_severity = CrisisSeverity.HIGH
                break

        if not concerns:
            return None

        is_crisis = max_severity != CrisisSeverity.NONE
        resources = self._get_resources(max_severity)

        return CrisisResult(
            is_crisis=is_crisis,
            severity=max_severity.value,
            concerns=concerns,
            resources=resources,
        )

    async def _llm_analysis(
        self,
        text: str,
        emotion_vector: dict[str, float],
    ) -> CrisisResult:
        """Perform LLM-based crisis analysis for nuanced detection."""
        sorted_emotions = sorted(
            emotion_vector.items(), key=lambda x: x[1], reverse=True
        )
        emotion_str = ", ".join(
            f"{name}: {score:.2f}" for name, score in sorted_emotions[:10]
        )

        user_prompt = (
            f"EMOTION VECTOR:\n{emotion_str}\n\n"
            f"USER TEXT:\n{text}\n\n"
            "Evaluate for crisis indicators."
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=_LLM_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            raw = response.content.strip()
        except Exception:
            logger.exception("[%s] LLM crisis analysis failed", self.AGENT_ID)
            # Fail safe: if LLM fails and we have concerning emotions,
            # flag for review
            if self._has_concerning_emotions(emotion_vector):
                return CrisisResult(
                    is_crisis=True,
                    severity=CrisisSeverity.MODERATE.value,
                    concerns=[
                        "LLM analysis unavailable; concerning emotion pattern detected"
                    ],
                    resources=self._get_resources(CrisisSeverity.MODERATE),
                )
            return CrisisResult(
                is_crisis=False,
                severity=CrisisSeverity.NONE.value,
            )

        return self._parse_llm_response(raw)

    def _parse_llm_response(self, raw: str) -> CrisisResult:
        """Parse LLM JSON response into a CrisisResult."""
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(
                "[%s] Failed to parse LLM response: %s",
                self.AGENT_ID,
                raw[:200],
            )
            return CrisisResult(
                is_crisis=False,
                severity=CrisisSeverity.NONE.value,
            )

        is_crisis = bool(data.get("is_crisis", False))
        severity_str = data.get("severity", "none").lower()
        try:
            severity = CrisisSeverity(severity_str)
        except ValueError:
            severity = CrisisSeverity.NONE

        concerns = data.get("concerns", [])
        if isinstance(concerns, str):
            concerns = [concerns]

        resources = self._get_resources(severity) if is_crisis else []

        return CrisisResult(
            is_crisis=is_crisis,
            severity=severity.value,
            concerns=concerns,
            resources=resources,
        )

    def _merge_results(
        self,
        keyword_result: CrisisResult | None,
        llm_result: CrisisResult,
    ) -> CrisisResult:
        """Merge keyword and LLM results, taking the higher severity."""
        if keyword_result is None:
            return llm_result

        severity_order = list(CrisisSeverity)
        kw_idx = severity_order.index(CrisisSeverity(keyword_result.severity))
        llm_idx = severity_order.index(CrisisSeverity(llm_result.severity))

        if kw_idx >= llm_idx:
            # Keyword result is more severe - merge concerns
            all_concerns = list(keyword_result.concerns)
            for c in llm_result.concerns:
                if c not in all_concerns:
                    all_concerns.append(c)
            severity = CrisisSeverity(keyword_result.severity)
            return CrisisResult(
                is_crisis=True,
                severity=severity.value,
                concerns=all_concerns,
                resources=self._get_resources(severity),
            )

        # LLM result is more severe
        all_concerns = list(llm_result.concerns)
        for c in keyword_result.concerns:
            if c not in all_concerns:
                all_concerns.append(c)
        severity = CrisisSeverity(llm_result.severity)
        return CrisisResult(
            is_crisis=llm_result.is_crisis,
            severity=severity.value,
            concerns=all_concerns,
            resources=self._get_resources(severity),
        )

    @staticmethod
    def _get_resources(severity: CrisisSeverity) -> list[str]:
        """Get appropriate resources based on severity level."""
        if severity in (CrisisSeverity.CRITICAL, CrisisSeverity.HIGH):
            return list(_EMERGENCY_RESOURCES)
        if severity == CrisisSeverity.MODERATE:
            return list(_EMERGENCY_RESOURCES[:4]) + list(_PASTORAL_RESOURCES)
        if severity == CrisisSeverity.LOW:
            return list(_PASTORAL_RESOURCES)
        return []

    @staticmethod
    def _has_concerning_emotions(emotion_vector: dict[str, float]) -> bool:
        """Check if the emotion vector contains concerning patterns."""
        concerning = {
            "sadness": 0.7,
            "fear": 0.7,
            "shame": 0.6,
            "guilt": 0.6,
            "grief": 0.7,
            "dread": 0.6,
            "loneliness": 0.7,
        }
        matches = sum(
            1
            for emotion, threshold in concerning.items()
            if emotion_vector.get(emotion, 0.0) >= threshold
        )
        return matches >= 2
