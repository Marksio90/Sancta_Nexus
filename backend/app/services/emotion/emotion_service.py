"""Emotion analysis service for Sancta Nexus.

Coordinates emotion detection from text and (future) voice inputs,
producing a 36-dimensional emotion vector aligned with the spiritual
direction framework.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Emotion taxonomy (36 dimensions)
# ---------------------------------------------------------------------------

EMOTION_LABELS: list[str] = [
    # Core affects
    "joy", "sadness", "anger", "fear", "surprise", "disgust",
    # Spiritual emotions
    "gratitude", "hope", "despair", "guilt", "shame", "peace",
    "awe", "reverence", "longing", "trust", "doubt",
    # Relational
    "love", "compassion", "loneliness", "belonging", "rejection",
    # Existential
    "meaning", "emptiness", "wonder", "anxiety", "serenity",
    # Ignatian markers
    "consolation", "desolation", "indifference",
    # Moral / volitional
    "remorse", "forgiveness", "determination", "humility",
    # Mystical
    "ecstasy", "dark_night",
]

assert len(EMOTION_LABELS) == 36, f"Expected 36 emotion labels, got {len(EMOTION_LABELS)}"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class SpiritualStateType(str, Enum):
    """High-level spiritual state classification."""

    CONSOLATION = "consolation"
    DESOLATION = "desolation"
    DARK_NIGHT = "dark_night"
    PEACE = "peace"
    SEEKING = "seeking"
    GRATITUDE = "gratitude"
    NEUTRAL = "neutral"


@dataclass
class EmotionAnalysis:
    """Result of analysing a piece of text or audio for emotional content.

    Attributes:
        vector: 36-dimensional emotion vector (label -> intensity 0..1).
        primary_emotion: The strongest detected emotion.
        secondary_emotions: Other notable emotions (intensity > threshold).
        confidence: Overall confidence of the analysis (0..1).
        spiritual_state: Mapped spiritual state.
        raw_scores: Optional raw model output before normalisation.
    """

    vector: dict[str, float]
    primary_emotion: str
    secondary_emotions: list[str]
    confidence: float
    spiritual_state: SpiritualStateType
    raw_scores: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpiritualState:
    """A richer spiritual-state descriptor derived from emotion + history."""

    state: SpiritualStateType
    description: str
    ignatian_movement: str  # "towards_consolation" | "towards_desolation" | "stable"
    suggested_prayer_form: str  # e.g. "lectio_divina", "examen", "centering"
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# EmotionService
# ---------------------------------------------------------------------------


class EmotionService:
    """High-level service for emotion detection and spiritual-state mapping.

    In production this wraps one or more ML models (text classifier,
    voice emotion recognition).  The current implementation uses a
    keyword / heuristic approach as a functional placeholder.
    """

    # Keyword -> emotion mappings (Polish + English for flexibility)
    _KEYWORD_MAP: dict[str, list[str]] = {
        "joy": ["radosc", "szczescie", "joy", "happy", "blessed", "blogoslawiony"],
        "sadness": ["smutek", "sad", "placz", "cry", "bol", "pain"],
        "anger": ["gniew", "zlosc", "angry", "wsciekly", "fury"],
        "fear": ["strach", "lek", "fear", "boje sie", "afraid", "przerazenie"],
        "gratitude": ["wdziecznosc", "dziekuje", "grateful", "thankful"],
        "hope": ["nadzieja", "hope", "ufam", "trust"],
        "despair": ["rozpacz", "despair", "beznadziejnosc", "hopeless"],
        "guilt": ["wina", "guilt", "grzech", "sin", "wyrzuty"],
        "shame": ["wstyd", "shame", "hanba"],
        "peace": ["pokoj", "spokoj", "peace", "calm", "cisza"],
        "awe": ["zachwyt", "awe", "majestat"],
        "reverence": ["czesc", "reverence", "uwielbienie"],
        "longing": ["tesknota", "longing", "pragnienie", "desire"],
        "love": ["milosc", "love", "kocham"],
        "compassion": ["wspolczucie", "compassion", "milosierdzie", "mercy"],
        "loneliness": ["samotnosc", "lonely", "osamotnienie"],
        "doubt": ["watpliwosc", "doubt", "niepewnosc"],
        "anxiety": ["niepokój", "anxiety", "lęk", "worry", "martwienie"],
        "consolation": ["pociecha", "consolation", "bliskosc boga"],
        "desolation": ["opuszczenie", "desolation", "oschlosc"],
        "dark_night": ["ciemna noc", "dark night", "noc duszy"],
        "wonder": ["zdumienie", "wonder", "cud"],
        "trust": ["zaufanie", "trust", "ufnosc"],
        "forgiveness": ["przebaczenie", "forgiveness", "odpuszczenie"],
        "humility": ["pokorą", "humility", "pokora"],
        "remorse": ["skrucha", "remorse", "zal za grzechy"],
        "determination": ["determinacja", "determination", "postanowienie"],
        "emptiness": ["pustosc", "emptiness", "pustka"],
        "meaning": ["sens", "meaning", "cel"],
        "serenity": ["pogoda ducha", "serenity"],
        "belonging": ["przynaleznosc", "belonging"],
        "rejection": ["odrzucenie", "rejection"],
        "surprise": ["zaskoczenie", "surprise", "zdziwienie"],
        "disgust": ["odraza", "obrzydzenie", "disgust"],
        "ecstasy": ["ekstaza", "ecstasy", "uniesienie"],
        "indifference": ["obojetnosc", "indifference"],
    }

    _SECONDARY_THRESHOLD = 0.3

    def __init__(self) -> None:
        # Future: load ML model here
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_text(self, text: str) -> EmotionAnalysis:
        """Analyse free-form text and return a 36-dim emotion vector.

        Args:
            text: User-provided text (any language, primarily Polish).

        Returns:
            :class:`EmotionAnalysis` with vector, primary emotion, etc.
        """
        vector = self._compute_vector(text)
        primary = max(vector, key=vector.get)
        secondary = [
            label
            for label, score in vector.items()
            if score >= self._SECONDARY_THRESHOLD and label != primary
        ]
        confidence = min(1.0, max(vector.values()) + 0.1) if any(vector.values()) else 0.1

        spiritual = self._classify_spiritual_state(vector)

        return EmotionAnalysis(
            vector=vector,
            primary_emotion=primary,
            secondary_emotions=sorted(secondary, key=lambda l: vector[l], reverse=True),
            confidence=confidence,
            spiritual_state=spiritual,
        )

    def analyze_voice(self, audio_url: str) -> EmotionAnalysis:
        """Analyse voice/audio for emotional content (placeholder).

        Args:
            audio_url: URL or path to the audio file.

        Returns:
            :class:`EmotionAnalysis` with neutral defaults.
        """
        logger.warning("Voice emotion analysis not yet implemented; returning neutral.")
        vector = {label: 0.0 for label in EMOTION_LABELS}
        vector["peace"] = 0.5
        return EmotionAnalysis(
            vector=vector,
            primary_emotion="peace",
            secondary_emotions=[],
            confidence=0.1,
            spiritual_state=SpiritualStateType.NEUTRAL,
            raw_scores={"source": "placeholder", "audio_url": audio_url},
        )

    def get_spiritual_state(
        self,
        emotion: EmotionAnalysis,
        history: list[EmotionAnalysis] | None = None,
    ) -> SpiritualState:
        """Derive a richer spiritual state from emotion analysis + history.

        Args:
            emotion: Current emotion analysis.
            history: Previous emotion analyses for trend detection.

        Returns:
            :class:`SpiritualState`.
        """
        history = history or []
        state_type = emotion.spiritual_state

        # Detect movement direction from history
        movement = self._detect_movement(emotion, history)

        prayer_form = self._suggest_prayer(state_type, emotion.vector)

        description = self._describe_state(state_type, emotion)

        return SpiritualState(
            state=state_type,
            description=description,
            ignatian_movement=movement,
            suggested_prayer_form=prayer_form,
            confidence=emotion.confidence,
        )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _compute_vector(self, text: str) -> dict[str, float]:
        """Build the 36-dim emotion vector via keyword matching.

        This is a heuristic placeholder.  A production implementation
        would use a fine-tuned multilingual classifier.
        """
        text_lower = text.lower()
        vector: dict[str, float] = {label: 0.0 for label in EMOTION_LABELS}

        for emotion, keywords in self._KEYWORD_MAP.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits:
                vector[emotion] = min(1.0, 0.3 + 0.2 * hits)

        # Ensure at least one non-zero value
        if all(v == 0.0 for v in vector.values()):
            vector["peace"] = 0.1

        return vector

    def _classify_spiritual_state(self, vector: dict[str, float]) -> SpiritualStateType:
        """Map the emotion vector to a high-level spiritual state."""
        if vector.get("dark_night", 0) > 0.5:
            return SpiritualStateType.DARK_NIGHT
        if vector.get("desolation", 0) > 0.5:
            return SpiritualStateType.DESOLATION
        if vector.get("consolation", 0) > 0.5:
            return SpiritualStateType.CONSOLATION
        if vector.get("gratitude", 0) > 0.4:
            return SpiritualStateType.GRATITUDE
        if vector.get("peace", 0) > 0.4 or vector.get("serenity", 0) > 0.4:
            return SpiritualStateType.PEACE
        if vector.get("longing", 0) > 0.4 or vector.get("doubt", 0) > 0.3:
            return SpiritualStateType.SEEKING
        return SpiritualStateType.NEUTRAL

    def _detect_movement(
        self, current: EmotionAnalysis, history: list[EmotionAnalysis]
    ) -> str:
        """Detect Ignatian movement direction from emotion history."""
        if not history:
            return "stable"

        consolation_now = current.vector.get("consolation", 0)
        desolation_now = current.vector.get("desolation", 0)

        recent = history[-3:]  # look at last 3 sessions
        avg_consolation = sum(e.vector.get("consolation", 0) for e in recent) / len(recent)
        avg_desolation = sum(e.vector.get("desolation", 0) for e in recent) / len(recent)

        consolation_delta = consolation_now - avg_consolation
        desolation_delta = desolation_now - avg_desolation

        if consolation_delta > 0.15 and desolation_delta < 0:
            return "towards_consolation"
        if desolation_delta > 0.15 and consolation_delta < 0:
            return "towards_desolation"
        return "stable"

    def _suggest_prayer(self, state: SpiritualStateType, vector: dict[str, float]) -> str:
        """Suggest an appropriate prayer form based on spiritual state."""
        suggestions: dict[SpiritualStateType, str] = {
            SpiritualStateType.CONSOLATION: "lectio_divina",
            SpiritualStateType.DESOLATION: "examen",
            SpiritualStateType.DARK_NIGHT: "centering_prayer",
            SpiritualStateType.PEACE: "contemplation",
            SpiritualStateType.SEEKING: "ignatian_meditation",
            SpiritualStateType.GRATITUDE: "psalms_of_praise",
            SpiritualStateType.NEUTRAL: "lectio_divina",
        }
        return suggestions.get(state, "lectio_divina")

    def _describe_state(self, state: SpiritualStateType, emotion: EmotionAnalysis) -> str:
        """Generate a human-readable description of the spiritual state."""
        descriptions: dict[SpiritualStateType, str] = {
            SpiritualStateType.CONSOLATION: (
                "Doswiadczasz pocieszenia duchowego - bliskosci Boga, "
                "wewnetrznego pokoju i radosci. To czas lask."
            ),
            SpiritualStateType.DESOLATION: (
                "Przechodzisz przez okres duchowej oschlosci. "
                "Pamietaj, ze Bog jest blisko nawet w ciemnosci."
            ),
            SpiritualStateType.DARK_NIGHT: (
                "Doswiadczasz 'ciemnej nocy duszy' - glebokie oczyszczenie, "
                "ktore moze prowadzic do wiekszej bliskosci z Bogiem."
            ),
            SpiritualStateType.PEACE: (
                "Jestes w stanie wewnetrznego pokoju. "
                "To dobry moment na kontemplacje i sluchanie."
            ),
            SpiritualStateType.SEEKING: (
                "Twoja dusza szuka - to naturalna czesc duchowej drogi. "
                "Otwórz sie na prowadzenie Ducha Swietego."
            ),
            SpiritualStateType.GRATITUDE: (
                "Serce pelne wdziecznosci otwiera na nowe laski. "
                "Wyraz Bogu swoja wdziecznosc."
            ),
            SpiritualStateType.NEUTRAL: (
                "Stan duchowy neutralny. Dobry moment na regularny rachunek sumienia."
            ),
        }
        return descriptions.get(state, "")
