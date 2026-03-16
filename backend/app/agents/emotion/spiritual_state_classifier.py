"""
SpiritualStateClassifier (A-025) - Ignatian spiritual state classification.

Classifies the user's spiritual state using Ignatian terminology and
discernment rules. Takes an emotion vector and user history as input
and produces a classified spiritual state.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class SpiritualStateEnum(str, Enum):
    """Spiritual states in Ignatian terminology."""

    DARK_NIGHT = "dark_night"
    CONSOLATION = "consolation"
    DESOLATION = "desolation"
    DRYNESS = "dryness"
    FERVOR = "fervor"
    TEMPTATION = "temptation"
    PEACE = "peace"
    GROWTH = "growth"


@dataclass(frozen=True, slots=True)
class SpiritualState:
    """Classified spiritual state with supporting information."""

    primary_state: SpiritualStateEnum
    confidence: float
    secondary_state: SpiritualStateEnum | None = None
    description: str = ""
    ignatian_rule: str = ""
    recommended_response: str = ""


_SYSTEM_PROMPT = (
    "You are an expert Ignatian spiritual director and discernment counsellor. "
    "Your task is to classify the user's current spiritual state based on their "
    "emotional profile and recent history.\n\n"
    "SPIRITUAL STATES (from Ignatian tradition):\n"
    "1. dark_night - The dark night of the soul (St. John of the Cross). "
    "Profound spiritual dryness, feeling of God's absence, purification.\n"
    "2. consolation - Spiritual consolation (Ignatius, SpEx 316). Interior "
    "movement toward God: peace, joy, tears of devotion, increase of faith/hope/love.\n"
    "3. desolation - Spiritual desolation (Ignatius, SpEx 317). Darkness of soul, "
    "turmoil, inclination to low things, restlessness, temptation to despair.\n"
    "4. dryness - Spiritual dryness without desolation. Prayer feels arid but "
    "no active turning from God; often a phase of maturation.\n"
    "5. fervor - Intense spiritual enthusiasm and zeal. May be authentic or "
    "may need discernment to distinguish from superficial emotion.\n"
    "6. temptation - Active spiritual temptation. The enemy proposes attractive "
    "falsehoods or discouragement.\n"
    "7. peace - Deep interior peace. The fruit of the Spirit (Gal 5:22). "
    "A settled confidence in God's providence.\n"
    "8. growth - Active spiritual growth. The person is progressing in virtue, "
    "deepening prayer life, and growing in charity.\n\n"
    "IGNATIAN RULES FOR DISCERNMENT:\n"
    "- Rule 1 (SpEx 314): In persons going from mortal sin to mortal sin, the "
    "enemy proposes apparent pleasures; the good spirit stings conscience.\n"
    "- Rule 2 (SpEx 315): In persons earnestly purifying themselves, the enemy "
    "causes anxiety and sadness; the good spirit gives courage and strength.\n"
    "- Rule 3 (SpEx 316): Consolation definition.\n"
    "- Rule 4 (SpEx 317): Desolation definition.\n"
    "- Rule 5 (SpEx 318): In desolation, never make a change.\n"
    "- Rule 6 (SpEx 319): In desolation, intensify prayer and penance.\n"
    "- Rule 7 (SpEx 320): In desolation, consider it a trial.\n"
    "- Rule 8 (SpEx 321): In desolation, be patient; consolation will return.\n"
    "- Rule 9 (SpEx 322): Three causes of desolation.\n"
    "- Rule 10 (SpEx 323): In consolation, prepare for desolation.\n"
    "- Rule 11 (SpEx 324): In consolation, be humble.\n"
    "- Rule 14 (SpEx 327): The enemy acts like a false lover - seeks secrecy.\n\n"
    "INSTRUCTIONS:\n"
    "Based on the emotion vector and user history provided, classify the "
    "spiritual state. Return a JSON object with these fields:\n"
    '- "primary_state": one of the 8 states above\n'
    '- "confidence": float 0.0-1.0\n'
    '- "secondary_state": optional second state, or null\n'
    '- "description": brief description of why this classification was made\n'
    '- "ignatian_rule": which Ignatian rule(s) apply\n'
    '- "recommended_response": pastoral guidance based on the state\n\n'
    "Return ONLY the JSON object."
)


class SpiritualStateClassifier:
    """
    A-025: Classifies spiritual state using Ignatian discernment.

    Uses an emotion vector and user history to determine the user's
    current spiritual state according to the Ignatian tradition.
    """

    AGENT_ID = "A-025"
    AGENT_NAME = "SpiritualStateClassifier"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> None:
        """
        Args:
            model: OpenAI model identifier.
            temperature: Low temperature for consistent classification.
            max_tokens: Maximum tokens for response.
        """
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def classify(
        self,
        emotion_vector: dict[str, float],
        user_history: list[dict[str, Any]],
    ) -> SpiritualState:
        """
        Classify the user's current spiritual state.

        Args:
            emotion_vector: Dict mapping emotion names to probabilities (0-1).
            user_history: List of recent interaction records, each a dict
                with at minimum 'text' and 'timestamp' keys.

        Returns:
            SpiritualState with classification and pastoral guidance.
        """
        logger.info(
            "[%s] Classifying spiritual state (%d emotions, %d history items)",
            self.AGENT_ID,
            len(emotion_vector),
            len(user_history),
        )

        user_prompt = self._build_user_prompt(emotion_vector, user_history)

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            raw = response.content.strip()
        except Exception:
            logger.exception("[%s] LLM call failed", self.AGENT_ID)
            return SpiritualState(
                primary_state=SpiritualStateEnum.PEACE,
                confidence=0.0,
                description="Classification unavailable due to system error.",
            )

        return self._parse_response(raw)

    def _build_user_prompt(
        self,
        emotion_vector: dict[str, float],
        user_history: list[dict[str, Any]],
    ) -> str:
        """Build the user prompt with emotion and history data."""
        # Sort emotions by strength
        sorted_emotions = sorted(
            emotion_vector.items(), key=lambda x: x[1], reverse=True
        )
        emotion_str = "\n".join(
            f"  {name}: {score:.3f}" for name, score in sorted_emotions
        )

        # Summarise recent history (limit to last 10 entries)
        recent = user_history[-10:] if user_history else []
        if recent:
            history_parts = []
            for entry in recent:
                text = entry.get("text", "")
                ts = entry.get("timestamp", "unknown")
                prev_state = entry.get("spiritual_state", "unknown")
                history_parts.append(
                    f"  [{ts}] (state: {prev_state}) {text[:200]}"
                )
            history_str = "\n".join(history_parts)
        else:
            history_str = "  No prior history available."

        return (
            f"CURRENT EMOTION VECTOR:\n{emotion_str}\n\n"
            f"RECENT USER HISTORY:\n{history_str}\n\n"
            "Please classify the spiritual state."
        )

    def _parse_response(self, raw: str) -> SpiritualState:
        """Parse the LLM JSON response into a SpiritualState."""
        # Strip markdown code fences if present
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
                "[%s] Failed to parse response as JSON: %s",
                self.AGENT_ID,
                raw[:200],
            )
            return SpiritualState(
                primary_state=SpiritualStateEnum.PEACE,
                confidence=0.0,
                description="Unable to parse classification response.",
            )

        # Parse primary state
        try:
            primary = SpiritualStateEnum(data.get("primary_state", "peace"))
        except ValueError:
            primary = SpiritualStateEnum.PEACE

        # Parse optional secondary state
        secondary = None
        sec_val = data.get("secondary_state")
        if sec_val:
            try:
                secondary = SpiritualStateEnum(sec_val)
            except ValueError:
                secondary = None

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return SpiritualState(
            primary_state=primary,
            confidence=round(confidence, 4),
            secondary_state=secondary,
            description=data.get("description", ""),
            ignatian_rule=data.get("ignatian_rule", ""),
            recommended_response=data.get("recommended_response", ""),
        )
