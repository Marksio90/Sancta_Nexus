"""
EmotionDetectorAgent (A-022) - Multi-dimensional emotion detection.

Detects emotions from text across 36 dimensions: 12 base emotions and
24 complex emotions. For MVP, uses LLM-based detection as a placeholder
for a fine-tuned RoBERTa/DeBERTa model.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Type alias for the emotion vector
EmotionVector = dict[str, float]

# 12 base emotions
BASE_EMOTIONS: list[str] = [
    "joy",
    "sadness",
    "fear",
    "anger",
    "surprise",
    "disgust",
    "trust",
    "anticipation",
    "love",
    "hope",
    "guilt",
    "shame",
]

# 24 complex emotions (combinations / nuanced states)
COMPLEX_EMOTIONS: list[str] = [
    "gratitude",
    "awe",
    "serenity",
    "ecstasy",
    "grief",
    "loneliness",
    "anxiety",
    "dread",
    "rage",
    "frustration",
    "contempt",
    "envy",
    "jealousy",
    "nostalgia",
    "bittersweet",
    "compassion",
    "empathy",
    "tenderness",
    "longing",
    "remorse",
    "humility",
    "reverence",
    "peace",
    "confusion",
]

ALL_EMOTIONS: list[str] = BASE_EMOTIONS + COMPLEX_EMOTIONS

_SYSTEM_PROMPT = (
    "You are an expert emotion detection system specialised in analysing "
    "text for emotional content. You detect emotions across 36 dimensions.\n\n"
    "BASE EMOTIONS (12):\n"
    f"{', '.join(BASE_EMOTIONS)}\n\n"
    "COMPLEX EMOTIONS (24):\n"
    f"{', '.join(COMPLEX_EMOTIONS)}\n\n"
    "INSTRUCTIONS:\n"
    "- Analyse the provided text for emotional content.\n"
    "- Return a JSON object mapping each detected emotion to its probability "
    "(0.0 to 1.0).\n"
    "- Only include emotions with probability > 0.05.\n"
    "- Probabilities across all emotions need NOT sum to 1.0 (emotions can "
    "co-occur).\n"
    "- Consider both explicit emotional language and implicit emotional tone.\n"
    "- Be sensitive to spiritual and religious emotional nuances.\n"
    "- Return ONLY the JSON object, no other text.\n\n"
    "Example output:\n"
    '{"joy": 0.72, "gratitude": 0.65, "hope": 0.58, "peace": 0.45}'
)


class EmotionDetectorAgent:
    """
    A-022: Multi-dimensional emotion detection from text.

    Detects emotions across 36 dimensions (12 base + 24 complex).
    MVP implementation uses LLM-based detection; production will use
    a fine-tuned RoBERTa or DeBERTa model.
    """

    AGENT_ID = "A-022"
    AGENT_NAME = "EmotionDetectorAgent"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.1,
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

    async def detect(self, text: str) -> EmotionVector:
        """
        Detect emotions in the provided text.

        Args:
            text: The text to analyse for emotional content.

        Returns:
            EmotionVector - dict mapping emotion names to probabilities (0-1).
            Only emotions with probability > 0.05 are included.
        """
        if not text or not text.strip():
            logger.warning("[%s] Empty text provided", self.AGENT_ID)
            return {}

        logger.info(
            "[%s] Detecting emotions (text length=%d chars)",
            self.AGENT_ID,
            len(text),
        )

        user_prompt = f"Analyse the following text for emotional content:\n\n{text}"

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            raw = response.content.strip()
        except Exception:
            logger.exception("[%s] LLM call failed", self.AGENT_ID)
            return {}

        emotion_vector = self._parse_response(raw)

        logger.info(
            "[%s] Detected %d emotions (top: %s)",
            self.AGENT_ID,
            len(emotion_vector),
            self._top_emotions(emotion_vector, n=3),
        )

        return emotion_vector

    def _parse_response(self, raw: str) -> EmotionVector:
        """Parse and validate the LLM JSON response into an EmotionVector."""
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
                "[%s] Failed to parse LLM response as JSON: %s",
                self.AGENT_ID,
                raw[:200],
            )
            return {}

        if not isinstance(data, dict):
            logger.error("[%s] Expected dict, got %s", self.AGENT_ID, type(data))
            return {}

        # Validate and sanitise
        vector: EmotionVector = {}
        for emotion, score in data.items():
            if emotion not in ALL_EMOTIONS:
                logger.debug(
                    "[%s] Ignoring unknown emotion '%s'", self.AGENT_ID, emotion
                )
                continue

            try:
                prob = float(score)
            except (TypeError, ValueError):
                continue

            # Clamp to [0, 1]
            prob = max(0.0, min(1.0, prob))

            if prob > 0.05:
                vector[emotion] = round(prob, 4)

        return vector

    @staticmethod
    def _top_emotions(vector: EmotionVector, n: int = 3) -> str:
        """Format top-n emotions for logging."""
        sorted_emotions = sorted(vector.items(), key=lambda x: x[1], reverse=True)
        top = sorted_emotions[:n]
        return ", ".join(f"{e}={s:.2f}" for e, s in top) if top else "none"
