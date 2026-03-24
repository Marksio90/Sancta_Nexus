"""Sacramental Preparation API routes.

Provides unified endpoints for all four sacramental preparation programs:
- Examination of Conscience (Rachunek sumienia) before Confession
- Marriage Preparation (Przygotowanie do małżeństwa)
- RCIA (Rite of Christian Initiation of Adults)
- Confirmation Preparation (Przygotowanie do bierzmowania)

PRIVACY: Examination of conscience endpoints do NOT persist any personal
data about the content of reflections. Responses are generated on-the-fly.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Lazy service loaders
# ---------------------------------------------------------------------------

def _get_examination():
    from app.services.sacraments.examination_service import ExaminationService
    return ExaminationService()


def _get_rcia():
    from app.services.sacraments.rcia_service import RCIAService
    return RCIAService()


def _get_marriage():
    from app.services.sacraments.marriage_prep_service import MarriagePrepService
    return MarriagePrepService()


def _get_confirmation():
    from app.services.sacraments.confirmation_service import ConfirmationService
    return ConfirmationService()


# ---------------------------------------------------------------------------
# ── Examination of Conscience ───────────────────────────────────────────────
# ---------------------------------------------------------------------------

class ExaminationRequest(BaseModel):
    state_of_life: str = Field(
        default="single",
        description="State of life: single, married, parent, religious, priest, teenager, child",
    )
    focus_areas: list[str] | None = Field(
        default=None,
        description="Personal areas to focus on (optional, not stored)",
    )
    language: str = Field(default="pl")


class ContritionRequest(BaseModel):
    state_of_life: str = Field(default="single")
    personal_note: str | None = Field(
        default=None,
        max_length=200,
        description="Optional theme for the act (not stored after generation)",
    )


class ResolutionRequest(BaseModel):
    focus_area: str = Field(..., max_length=200, description="Area for amendment")
    state_of_life: str = Field(default="single")


class ReflectionStreamRequest(BaseModel):
    commandment_number: int = Field(..., ge=1, le=10)
    state_of_life: str = Field(default="single")
    user_reflection: str | None = Field(
        default=None,
        max_length=500,
        description="User's reflection to deepen (ephemeral, not stored)",
    )


@router.get("/confession/commandments")
async def get_commandments() -> dict[str, Any]:
    """Return the 10 Commandments examination structure with questions."""
    svc = _get_examination()
    return {
        "title": "Rachunek sumienia według Dziesięciu Przykazań",
        "ccc_ref": "§§ 2052–2557",
        "commandments": svc.get_commandments_overview(),
    }


@router.get("/confession/state-questions/{state_of_life}")
async def get_state_questions(state_of_life: str) -> dict[str, Any]:
    """Return examination questions specific to a state of life."""
    from app.services.sacraments.examination_service import StateOfLife
    try:
        state = StateOfLife(state_of_life)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state: '{state_of_life}'. Valid: {[s.value for s in StateOfLife]}",
        )
    svc = _get_examination()
    return {
        "state_of_life": state_of_life,
        "questions": svc.get_state_questions(state),
    }


@router.post("/confession/examination")
async def generate_examination(req: ExaminationRequest) -> dict[str, Any]:
    """Generate a personalised examination of conscience text."""
    from app.services.sacraments.examination_service import StateOfLife
    try:
        state = StateOfLife(req.state_of_life)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {req.state_of_life}")

    try:
        svc = _get_examination()
        text = await svc.generate_personalized_examination(
            state_of_life=state,
            focus_areas=req.focus_areas,
            language=req.language,
        )
        return {
            "state_of_life": req.state_of_life,
            "examination": text,
            "note": "Ten tekst nie jest przechowywany — jest generowany jednorazowo.",
        }
    except Exception as exc:
        logger.error("Examination generation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/confession/reflection/stream")
async def stream_commandment_reflection(req: ReflectionStreamRequest) -> StreamingResponse:
    """Stream an AI-guided reflection for a specific commandment."""
    from app.services.sacraments.examination_service import StateOfLife

    try:
        state = StateOfLife(req.state_of_life)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {req.state_of_life}")

    async def _generate() -> AsyncIterator[bytes]:
        try:
            svc = _get_examination()
            async for chunk in svc.stream_guided_reflection(
                commandment_number=req.commandment_number,
                state_of_life=state,
                user_reflection=req.user_reflection,
            ):
                yield chunk.encode("utf-8")
        except Exception as exc:
            logger.error("Reflection stream error: %s", exc)
            yield b"[Blad generowania refleksji]"

    return StreamingResponse(
        _generate(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.post("/confession/act-of-contrition")
async def generate_act_of_contrition(req: ContritionRequest) -> dict[str, Any]:
    """Generate a personalised Act of Contrition (Akt Żalu)."""
    from app.services.sacraments.examination_service import StateOfLife
    try:
        state = StateOfLife(req.state_of_life)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {req.state_of_life}")

    try:
        svc = _get_examination()
        text = await svc.generate_act_of_contrition(
            state_of_life=state,
            personal_note=req.personal_note,
        )
        return {"act_of_contrition": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/confession/resolution")
async def generate_resolution(req: ResolutionRequest) -> dict[str, Any]:
    """Generate a concrete purpose of amendment (postanowienie poprawy)."""
    from app.services.sacraments.examination_service import StateOfLife
    try:
        state = StateOfLife(req.state_of_life)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {req.state_of_life}")

    try:
        svc = _get_examination()
        text = await svc.generate_resolution(
            focus_area=req.focus_area,
            state_of_life=state,
        )
        return {"resolution": text, "focus_area": req.focus_area}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# ── RCIA ────────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class RCIAQuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    session_id: str | None = None
    conversation_history: list[dict] | None = None


@router.get("/rcia/curriculum")
async def get_rcia_curriculum() -> dict[str, Any]:
    """Return the full RCIA curriculum organised by stage."""
    svc = _get_rcia()
    return {
        "title": "Program RCIA — Droga do wiary",
        "stages": svc.get_curriculum(),
        "total_sessions": 14,
    }


@router.get("/rcia/session/{session_id}")
async def get_rcia_session(session_id: str) -> dict[str, Any]:
    """Return a specific RCIA session."""
    svc = _get_rcia()
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RCIA session '{session_id}' not found.",
        )
    return session


@router.post("/rcia/ask")
async def ask_rcia_question(req: RCIAQuestionRequest) -> dict[str, Any]:
    """Ask a catechetical question — AI catechist responds."""
    try:
        svc = _get_rcia()
        answer = await svc.answer_question(
            question=req.question,
            session_id=req.session_id,
            conversation_history=req.conversation_history,
        )
        return {"question": req.question, "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/rcia/reflection/{session_id}")
async def get_rcia_reflection(session_id: str) -> dict[str, Any]:
    """Generate a guided reflection for an RCIA session."""
    try:
        svc = _get_rcia()
        reflection = await svc.generate_reflection(session_id)
        return {"session_id": session_id, "reflection": reflection}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# ── Marriage Preparation ─────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class MarriageQuestionRequest(BaseModel):
    message: str = Field(..., min_length=5, max_length=1000)
    session_id: str | None = None
    conversation_history: list[dict] | None = None


@router.get("/marriage/program")
async def get_marriage_program() -> dict[str, Any]:
    """Return the full 8-session marriage preparation program."""
    svc = _get_marriage()
    return {
        "title": "Przygotowanie do małżeństwa",
        "subtitle": "8 spotkań dla narzeczonych",
        "sessions": svc.get_program(),
    }


@router.get("/marriage/session/{session_id}")
async def get_marriage_session(session_id: str) -> dict[str, Any]:
    svc = _get_marriage()
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Marriage prep session '{session_id}' not found.")
    return session


@router.post("/marriage/discuss")
async def discuss_marriage_topic(req: MarriageQuestionRequest) -> dict[str, Any]:
    """AI-facilitated discussion for a specific marriage prep session."""
    try:
        svc = _get_marriage()
        response = await svc.facilitate_discussion(
            session_id=req.session_id or "",
            user_message=req.message,
            conversation_history=req.conversation_history,
        )
        return {"response": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/marriage/reflection/{session_id}")
async def get_marriage_reflection(session_id: str) -> dict[str, Any]:
    """Generate a guided reflection for a marriage prep session."""
    try:
        svc = _get_marriage()
        reflection = await svc.generate_session_reflection(session_id)
        return {"session_id": session_id, "reflection": reflection}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# ── Confirmation Preparation ─────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class ConfirmationQuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    session_id: str | None = None
    conversation_history: list[dict] | None = None


class PatronRequest(BaseModel):
    interests: list[str] = Field(default_factory=list)
    personal_traits: list[str] = Field(default_factory=list)


@router.get("/confirmation/program")
async def get_confirmation_program() -> dict[str, Any]:
    """Return the full 6-session confirmation preparation program."""
    svc = _get_confirmation()
    return {
        "title": "Przygotowanie do Bierzmowania",
        "subtitle": "6 kroków do przyjęcia Ducha Świętego",
        "sessions": svc.get_program(),
        "gifts_of_spirit": svc.get_gifts_of_spirit(),
    }


@router.get("/confirmation/session/{session_id}")
async def get_confirmation_session(session_id: str) -> dict[str, Any]:
    svc = _get_confirmation()
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Confirmation session '{session_id}' not found.")
    return session


@router.get("/confirmation/gifts")
async def get_gifts_of_spirit() -> dict[str, Any]:
    """Return the 7 gifts of the Holy Spirit with descriptions."""
    svc = _get_confirmation()
    return {
        "title": "Siedem darów Ducha Świętego",
        "ccc_ref": "§§ 1830-1832",
        "scripture": "Iz 11,2-3",
        "gifts": svc.get_gifts_of_spirit(),
    }


@router.post("/confirmation/ask")
async def ask_confirmation_question(req: ConfirmationQuestionRequest) -> dict[str, Any]:
    """AI catechist answers a candidate's question about Confirmation."""
    try:
        svc = _get_confirmation()
        answer = await svc.answer_question(
            question=req.question,
            session_id=req.session_id,
            conversation_history=req.conversation_history,
        )
        return {"question": req.question, "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/confirmation/patron")
async def suggest_patron_saint(req: PatronRequest) -> dict[str, Any]:
    """Suggest confirmation patron saints based on interests and traits."""
    try:
        svc = _get_confirmation()
        suggestions = await svc.help_choose_patron(
            interests=req.interests,
            personal_traits=req.personal_traits,
        )
        return {"suggestions": suggestions}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# ── Overview ─────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@router.get("/overview")
async def sacraments_overview() -> dict[str, Any]:
    """Return an overview of all available sacramental preparation programs."""
    return {
        "programs": [
            {
                "id": "confession",
                "title": "Rachunek sumienia",
                "subtitle": "Przygotowanie do Sakramentu Pojednania",
                "description": "AI-prowadzony rachunek sumienia według 10 Przykazań i stanu życia.",
                "ccc_ref": "§§ 1422–1498",
                "sessions": 1,
                "duration": "30-60 min",
                "url_prefix": "/api/v1/sacraments/confession",
            },
            {
                "id": "rcia",
                "title": "RCIA",
                "subtitle": "Droga dla dorosłych do wiary",
                "description": "14-sesyjny program inicjacji chrześcijańskiej dla dorosłych kandydatów.",
                "ccc_ref": "§§ 1212–1274",
                "sessions": 14,
                "duration": "6-12 miesięcy",
                "url_prefix": "/api/v1/sacraments/rcia",
            },
            {
                "id": "marriage",
                "title": "Przygotowanie do małżeństwa",
                "subtitle": "Dla narzeczonych",
                "description": "8-sesyjny program obejmujący Teologię Ciała, komunikację i życie sakramentalne.",
                "ccc_ref": "§§ 1601–1658",
                "sessions": 8,
                "duration": "2-3 miesiące",
                "url_prefix": "/api/v1/sacraments/marriage",
            },
            {
                "id": "confirmation",
                "title": "Przygotowanie do bierzmowania",
                "subtitle": "Dary Ducha Świętego",
                "description": "6-sesyjny program dla kandydatów do bierzmowania z wyborem patrona.",
                "ccc_ref": "§§ 1285–1321",
                "sessions": 6,
                "duration": "6 tygodni",
                "url_prefix": "/api/v1/sacraments/confirmation",
            },
        ]
    }
