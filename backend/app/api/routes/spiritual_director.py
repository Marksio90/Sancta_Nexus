"""Spiritual Director API routes.

Provides endpoints for AI-assisted spiritual direction sessions,
supporting multiple Catholic spiritual traditions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import RedisDep
from app.services.cache.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Traditions
# ---------------------------------------------------------------------------

TRADITIONS: list[dict[str, Any]] = [
    {
        "id": "ignatian",
        "name": "Tradycja Ignacjanska",
        "description": (
            "Duchowość sw. Ignacego Loyoli oparta na Cwiczeniach Duchowych, "
            "rozeznawaniu duchów i szukaniu woli Bozej."
        ),
        "key_practices": [
            "Rachunek sumienia (Examen)",
            "Medytacja ignacjanska",
            "Rozeznawanie duchowe",
            "Cwiczenia Duchowe",
        ],
    },
    {
        "id": "carmelite",
        "name": "Tradycja Karmelitanska",
        "description": (
            "Duchowość sw. Jana od Krzyza i sw. Teresy z Avili, "
            "podkreslajaca kontemplacje i zjednoczenie z Bogiem."
        ),
        "key_practices": [
            "Modlitwa kontemplacyjna",
            "Ciemna noc duszy",
            "Twierdza wewnetrzna",
            "Lectio Divina",
        ],
    },
    {
        "id": "benedictine",
        "name": "Tradycja Benedyktynska",
        "description": (
            "Duchowość sw. Benedykta — 'Ora et Labora', "
            "harmonia modlitwy i pracy."
        ),
        "key_practices": [
            "Liturgia Godzin",
            "Lectio Divina",
            "Stabilitas",
            "Ora et Labora",
        ],
    },
    {
        "id": "franciscan",
        "name": "Tradycja Franciszkanska",
        "description": (
            "Duchowość sw. Franciszka z Asyzu — ubostwo, radosc, "
            "bliskosc z stworzeniem i Ukrzyzowanym."
        ),
        "key_practices": [
            "Modlitwa ubogich",
            "Kontemplacja stworzenia",
            "Naśladowanie Chrystusa ubogiego",
            "Pieśń Sloneczna",
        ],
    },
    {
        "id": "dominican",
        "name": "Tradycja Dominikanska",
        "description": (
            "Duchowość sw. Dominika — 'Contemplata aliis tradere', "
            "kontemplacja przekazywana innym."
        ),
        "key_practices": [
            "Studium i kontemplacja",
            "Rozaniec",
            "Kaznodziejstwo",
            "Dziewiec sposobow modlitwy sw. Dominika",
        ],
    },
]


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartDirectionRequest(BaseModel):
    """Request to start a spiritual direction session."""

    user_id: str
    tradition: str = "ignatian"
    initial_intention: str | None = None
    previous_session_id: str | None = None


class DirectionSessionResponse(BaseModel):
    """Response after creating a direction session."""

    session_id: str
    user_id: str
    tradition: str
    status: str
    created_at: str
    opening_message: str
    spiritual_state: str | None = None


class MessageRequest(BaseModel):
    """Request to send a message in a direction session."""

    session_id: str
    user_id: str
    content: str
    message_type: str = "text"  # text | voice_transcription


class DirectorMessage(BaseModel):
    """A message from the spiritual director."""

    role: str  # "user" | "director"
    content: str
    timestamp: str
    emotion_detected: str | None = None
    scripture_reference: str | None = None


class MessageResponse(BaseModel):
    """Response to a user message in a direction session."""

    session_id: str
    director_response: str
    emotion_analysis: dict[str, Any] = Field(default_factory=dict)
    suggested_scriptures: list[dict[str, Any]] = Field(default_factory=list)
    spiritual_state: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list)
    prayer_suggestion: str | None = None


class TraditionInfo(BaseModel):
    """Information about a spiritual tradition."""

    id: str
    name: str
    description: str
    key_practices: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tradition-specific opening messages
# ---------------------------------------------------------------------------

_OPENING_MESSAGES: dict[str, str] = {
    "ignatian": (
        "Witaj w duchowym towarzyszeniu w tradycji ignacjanskiej. "
        "Rozpocznijmy od chwili ciszy, prosząc Ducha Swietego o swiatlo. "
        "Co przynosi Ci serce na dzisiejsze spotkanie?"
    ),
    "carmelite": (
        "Witaj, droga duszo. Wchodzimy razem w przestrzen ciszy i kontemplacji, "
        "w tradycji sw. Teresy i sw. Jana od Krzyza. "
        "Jak sie czujesz w swojej modlitwie ostatnio?"
    ),
    "benedictine": (
        "Pokój Ci! W duchu sw. Benedykta — 'słuchaj uważnie'. "
        "Zapraszam do otwartosci na Slowo. "
        "Co niesie Twoje serce w tej chwili?"
    ),
    "franciscan": (
        "Pokoj i Dobro! W duchu sw. Franciszka, prostoty i radosci, "
        "spotkajmy sie przed Panem. "
        "Co chcialbyś/chcialabys powierzyc Bogu?"
    ),
    "dominican": (
        "Witaj w swietle Prawdy. W tradycji sw. Dominika szukamy "
        "Prawdy, ktora jest Osoba — Chrystusem. "
        "Jaki temat chcialbyś/chcialabys dzis rozwazyc?"
    ),
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/session",
    response_model=DirectionSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_direction_session(
    request: StartDirectionRequest,
    redis: RedisDep,
) -> DirectionSessionResponse:
    """Start a new spiritual direction session.

    The session is configured with the chosen Catholic spiritual
    tradition and provides an appropriate opening message.
    """
    if request.tradition not in {t["id"] for t in TRADITIONS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown tradition '{request.tradition}'. "
                f"Available: {[t['id'] for t in TRADITIONS]}"
            ),
        )

    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    opening = _OPENING_MESSAGES.get(request.tradition, _OPENING_MESSAGES["ignatian"])
    if request.initial_intention:
        opening += f"\n\nTwoja intencja: {request.initial_intention}"

    session_data: dict[str, Any] = {
        "session_id": session_id,
        "user_id": request.user_id,
        "tradition": request.tradition,
        "status": "active",
        "created_at": now.isoformat(),
        "messages": [
            {
                "role": "director",
                "content": opening,
                "timestamp": now.isoformat(),
            }
        ],
        "emotions": [],
        "previous_session_id": request.previous_session_id,
    }
    store = SessionStore(redis, namespace="direction")
    await store.create(session_id, session_data)

    logger.info(
        "Started spiritual direction session %s (tradition=%s) for user %s",
        session_id,
        request.tradition,
        request.user_id,
    )

    return DirectionSessionResponse(
        session_id=session_id,
        user_id=request.user_id,
        tradition=request.tradition,
        status="active",
        created_at=now.isoformat(),
        opening_message=opening,
    )


@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest, redis: RedisDep) -> MessageResponse:
    """Send a message in a spiritual direction session.

    The director analyses the user's emotional state, references
    relevant scripture and responds with spiritual guidance.
    """
    from app.services.emotion.emotion_service import EmotionService
    from app.services.scripture.scripture_matcher import IgnatianState, MatchContext, ScriptureMatcher

    store = SessionStore(redis, namespace="direction")
    session = await store.get(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    if session["user_id"] != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not own this session",
        )

    now = datetime.utcnow()

    # Record user message
    session["messages"].append({
        "role": "user",
        "content": request.content,
        "timestamp": now.isoformat(),
    })

    # Analyse emotion
    emotion_svc = EmotionService()
    analysis = emotion_svc.analyze_text(request.content)
    spiritual_state = emotion_svc.get_spiritual_state(analysis)

    session["emotions"].append({
        "timestamp": now.isoformat(),
        "primary": analysis.primary_emotion,
        "state": spiritual_state.state.value,
    })

    # Find relevant scripture
    matcher = ScriptureMatcher()
    context = MatchContext(
        user_id=request.user_id,
        ignatian_state=(
            IgnatianState(spiritual_state.ignatian_movement.replace("towards_", ""))
            if spiritual_state.ignatian_movement.startswith("towards_")
            else IgnatianState.NEUTRAL
        ),
    )
    matches = matcher.match(analysis.vector, context)

    suggested = [
        {
            "reference": m.reference,
            "passage": m.passage,
            "explanation": m.explanation,
        }
        for m in matches
    ]

    # Generate director response
    director_response = _generate_director_response(
        user_message=request.content,
        tradition=session["tradition"],
        analysis=analysis,
        spiritual_state=spiritual_state,
        matches=matches,
    )

    session["messages"].append({
        "role": "director",
        "content": director_response,
        "timestamp": datetime.utcnow().isoformat(),
    })
    await store.update(request.session_id, session)

    follow_ups = _generate_follow_up_questions(
        session["tradition"], analysis.primary_emotion
    )

    return MessageResponse(
        session_id=request.session_id,
        director_response=director_response,
        emotion_analysis={
            "primary_emotion": analysis.primary_emotion,
            "secondary_emotions": analysis.secondary_emotions,
            "confidence": analysis.confidence,
        },
        suggested_scriptures=suggested,
        spiritual_state=spiritual_state.state.value,
        follow_up_questions=follow_ups,
        prayer_suggestion=spiritual_state.suggested_prayer_form,
    )


@router.get("/traditions", response_model=list[TraditionInfo])
async def list_traditions() -> list[TraditionInfo]:
    """List available Catholic spiritual traditions."""
    return [
        TraditionInfo(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            key_practices=t["key_practices"],
        )
        for t in TRADITIONS
    ]


# ---------------------------------------------------------------------------
# Response generation helpers
# ---------------------------------------------------------------------------


def _generate_director_response(
    user_message: str,
    tradition: str,
    analysis: Any,
    spiritual_state: Any,
    matches: list[Any],
) -> str:
    """Generate a spiritual director response.

    In production this would call an LLM with tradition-specific
    prompting.  Here we construct a template-based response.
    """
    parts: list[str] = []

    # Acknowledge emotional state
    parts.append(f"Slyszę w Twoich slowach '{analysis.primary_emotion}'.")

    # Spiritual state observation
    if spiritual_state.description:
        parts.append(spiritual_state.description)

    # Scripture suggestion
    if matches:
        top = matches[0]
        parts.append(
            f"\nZachęcam do modlitewnego rozważenia: {top.reference}."
        )
        if top.passage:
            parts.append(f'"{top.passage}"')

    # Tradition-specific closing
    closings: dict[str, str] = {
        "ignatian": "Prosze, zastanów sie: gdzie w tym doswiadczeniu jest Bog?",
        "carmelite": "Zapraszam do trwania w ciszy z tym, co sie wylanial.",
        "benedictine": "Sluchaj serca — co Bog mówi przez to doswiadczenie?",
        "franciscan": "Spójrz na to oczami prostoty i zaufania sw. Franciszka.",
        "dominican": "Jakiej prawdy szukasz w tym doswiadczeniu?",
    }
    parts.append(closings.get(tradition, closings["ignatian"]))

    return "\n\n".join(parts)


def _generate_follow_up_questions(tradition: str, primary_emotion: str) -> list[str]:
    """Generate contextual follow-up questions."""
    base_questions: list[str] = [
        "Co jeszcze chcialbyś/chcialabys powiedziec?",
        "Jak to doswiadczenie wplywa na Twoja modlitwe?",
    ]

    emotion_questions: dict[str, list[str]] = {
        "sadness": [
            "Czy czujesz bliskosc Boga w tym smutku?",
            "Czy jest ktos, z kim mozesz podzielic ten bol?",
        ],
        "joy": [
            "Za co szczególnie jestes wdzieczny/wdzieczna?",
            "Jak ta radosc wplywa na Twoje relacje?",
        ],
        "fear": [
            "Czego sie obawiasz najbardziej?",
            "Czy potrafisz powierzyc ten lek Bogu?",
        ],
        "guilt": [
            "Czy rozważales/rozważalas sakrament pojednania?",
            "Jak widzisz milosierdzie Boze w tej sytuacji?",
        ],
        "longing": [
            "Czego szuka Twoja dusza?",
            "Co mówi Ci to pragnienie o Twojej relacji z Bogiem?",
        ],
    }

    specific = emotion_questions.get(primary_emotion, [])
    return (specific + base_questions)[:3]
