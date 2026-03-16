"""Pydantic v2 request/response schemas for the Sancta Nexus API.

Covers Lectio Divina sessions, Bible Q&A, and spiritual-direction
conversations.  All models use ``model_config`` with strict validation and
JSON-schema-friendly aliases where appropriate.
"""

from pydantic import BaseModel, ConfigDict, Field


# ── Shared / Emotion ─────────────────────────────────────────────────────────


class EmotionInput(BaseModel):
    """Raw emotional signal submitted by the user.

    At least one of *text* or *audio_url* should be provided so the emotion
    pipeline can derive an emotion vector.
    """

    model_config = ConfigDict(strict=True)

    text: str | None = Field(
        default=None,
        description="Free-form text describing the user's current emotional state.",
    )
    audio_url: str | None = Field(
        default=None,
        description="URL to an audio recording for voice-based emotion analysis.",
    )


class EmotionVector(BaseModel):
    """36-dimensional emotion vector produced by the emotion-analysis agents."""

    model_config = ConfigDict(strict=True)

    emotions: dict[str, float] = Field(
        ...,
        description="Mapping of emotion labels to intensity scores (0.0 - 1.0).",
    )
    primary_emotion: str = Field(
        ...,
        description="The dominant emotion identified in the input.",
    )
    spiritual_state: str = Field(
        ...,
        description=(
            "High-level spiritual-state classification derived from the "
            "emotion vector (e.g. 'consolation', 'desolation', 'peace')."
        ),
    )


# ── Scripture ────────────────────────────────────────────────────────────────


class ScripturePassage(BaseModel):
    """A specific Bible passage with full text and translation metadata."""

    model_config = ConfigDict(strict=True)

    book: str = Field(..., description="Canonical book name (e.g. 'Genesis', 'Psalms').")
    chapter: int = Field(..., ge=1, description="Chapter number.")
    verse_start: int = Field(..., ge=1, description="Starting verse (inclusive).")
    verse_end: int = Field(..., ge=1, description="Ending verse (inclusive).")
    text: str = Field(..., description="Full passage text.")
    translation: str = Field(..., description="Bible translation used (e.g. 'NRSVCE', 'ESV').")


# ── Lectio Divina ────────────────────────────────────────────────────────────


class LectioRequest(BaseModel):
    """Input for a guided Lectio Divina session.

    The system uses the optional emotion input and liturgical date to select
    a contextually appropriate scripture passage.
    """

    model_config = ConfigDict(strict=True)

    user_id: str = Field(..., description="Authenticated user identifier.")
    emotion_input: EmotionInput | None = Field(
        default=None,
        description="Optional emotional context to personalise scripture selection.",
    )
    liturgical_date: str | None = Field(
        default=None,
        description="ISO-8601 date for liturgical-calendar alignment.",
    )


class LectioResponse(BaseModel):
    """Complete output of a Lectio Divina session across all classical stages.

    Stages: Lectio (reading), Meditatio (meditation), Oratio (prayer),
    Contemplatio (contemplation), plus an Actio (action) challenge.
    """

    model_config = ConfigDict(strict=True)

    scripture: ScripturePassage = Field(
        ...,
        description="The selected scripture passage (Lectio stage).",
    )
    historical_context: str = Field(
        ...,
        description="Scholarly historical and cultural context for the passage.",
    )
    meditation_questions: list[str] = Field(
        ...,
        min_length=1,
        description="Guided reflection questions for the Meditatio stage.",
    )
    prayer: str = Field(
        ...,
        description="A personalised prayer arising from the passage (Oratio stage).",
    )
    contemplation_guidance: str = Field(
        ...,
        description="Guidance for silent resting in God's presence (Contemplatio stage).",
    )
    action_challenge: str = Field(
        ...,
        description="A concrete action step inspired by the passage (Actio stage).",
    )
    image_url: str | None = Field(
        default=None,
        description="URL to an AI-generated devotional image for the passage.",
    )
    audio_url: str | None = Field(
        default=None,
        description="URL to an AI-generated audio narration of the session.",
    )


# ── Bible Q&A ────────────────────────────────────────────────────────────────


class BibleQuestionRequest(BaseModel):
    """User question about a Bible passage or topic."""

    model_config = ConfigDict(strict=True)

    question: str = Field(
        ...,
        min_length=3,
        description="The question to answer.",
    )
    passage_reference: str | None = Field(
        default=None,
        description="Optional passage reference to scope the answer (e.g. 'John 3:16').",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user ID for personalisation and history tracking.",
    )


class BibleQuestionResponse(BaseModel):
    """Multi-dimensional answer to a Bible question.

    Each dimension provides a different scholarly or pastoral lens on the
    question so the user receives a holistic understanding.
    """

    model_config = ConfigDict(strict=True)

    theological: str = Field(
        ...,
        description="Answer from systematic and dogmatic theology.",
    )
    historical: str = Field(
        ...,
        description="Answer from historical-critical and archaeological scholarship.",
    )
    psychological: str = Field(
        ...,
        description="Answer exploring psychological and emotional dimensions.",
    )
    spiritual: str = Field(
        ...,
        description="Answer focused on personal prayer, devotion, and spiritual growth.",
    )


# ── Spiritual Direction ─────────────────────────────────────────────────────


class SpiritualDirectorRequest(BaseModel):
    """Message sent to the AI spiritual director.

    The *tradition* field selects the director's charism and approach.
    """

    model_config = ConfigDict(strict=True)

    user_id: str = Field(..., description="Authenticated user identifier.")
    message: str = Field(
        ...,
        min_length=1,
        description="The directee's message or question.",
    )
    tradition: str = Field(
        default="ignatian",
        description=(
            "Spiritual tradition guiding the director's approach "
            "(e.g. 'ignatian', 'carmelite', 'benedictine', 'franciscan')."
        ),
    )


class SpiritualDirectorResponse(BaseModel):
    """Response from the AI spiritual director."""

    model_config = ConfigDict(strict=True)

    response: str = Field(
        ...,
        description="The director's pastoral response.",
    )
    spiritual_state: str = Field(
        ...,
        description=(
            "Assessment of the directee's current spiritual state "
            "(e.g. 'consolation', 'desolation', 'dark night', 'illumination')."
        ),
    )
    exercises: list[str] | None = Field(
        default=None,
        description="Optional spiritual exercises recommended for the directee.",
    )
    follow_up_questions: list[str] | None = Field(
        default=None,
        description="Optional follow-up questions to deepen discernment.",
    )
