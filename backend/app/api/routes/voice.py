"""Voice API routes — TTS and STT endpoints.

Endpoints
---------
POST /tts
    Convert text to MP3 audio using a sacred voice profile.
    Body: { "text": "...", "profile": "narrator_male|narrator_female|contemplative|sacred", "speed": 0.9 }
    Returns: audio/mpeg stream

POST /stt
    Transcribe audio to text via OpenAI Whisper.
    Body: multipart/form-data  (file: audio blob, language: str)
    Returns: { "text": "...", "language": "pl", "duration_seconds": float }

GET /voices
    List available voice profiles with descriptions.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.voice.tts_service import TTSService, VoiceProfile
from app.services.voice.stt_service import STTService

logger = logging.getLogger(__name__)
router = APIRouter()

_tts = TTSService()
_stt = STTService()


# ── Schemas ───────────────────────────────────────────────────────────────────


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4096)
    profile: VoiceProfile = VoiceProfile.NARRATOR_MALE
    speed: float = Field(default=0.9, ge=0.25, le=1.5)


class STTResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float | None
    provider: str


class VoiceProfileInfo(BaseModel):
    id: str
    label: str
    description: str
    gender: str
    style: str


# ── Route handlers ────────────────────────────────────────────────────────────


@router.post("/tts", response_class=Response, summary="Text to sacred speech")
async def text_to_speech(body: TTSRequest) -> Response:
    """Synthesise *body.text* with the chosen sacred voice profile.

    Returns raw MP3 bytes (audio/mpeg).  The frontend plays this directly
    via an HTMLAudioElement or the Web Audio API.
    """
    try:
        audio_bytes = await _tts.synthesize(
            text=body.text,
            profile=body.profile,
            speed=body.speed,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="TTS synthesis failed") from exc

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline; filename=sancta_voice.mp3",
        },
    )


@router.post("/stt", response_model=STTResponse, summary="Speech to text (Whisper)")
async def speech_to_text(
    file: UploadFile = File(..., description="Audio recording (webm/ogg/mp4/wav)"),
    language: str = Form(default="pl", description="BCP-47 language tag"),
    spiritual_prompt: str = Form(
        default=(
            "Modlitwa katolicka, Pismo Święte, Lectio Divina, "
            "kierownictwo duchowe, łaska, zbawienie"
        ),
        description="Whisper prompt to improve theological vocabulary recognition",
    ),
) -> STTResponse:
    """Transcribe a prayer audio recording to text.

    Pass a *spiritual_prompt* to help Whisper recognise theological vocabulary
    (names of saints, liturgical terms, scripture references).
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    content_type = file.content_type or "audio/webm"

    try:
        result = await _stt.transcribe(
            audio_bytes=audio_bytes,
            content_type=content_type,
            language=language,
            prompt=spiritual_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("STT transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed") from exc

    return STTResponse(
        text=result["text"],  # type: ignore[arg-type]
        language=result["language"],  # type: ignore[arg-type]
        duration_seconds=result.get("duration_seconds"),  # type: ignore[arg-type]
        provider=result["provider"],  # type: ignore[arg-type]
    )


@router.get("/voices", response_model=list[VoiceProfileInfo], summary="Available voice profiles")
async def list_voices() -> list[VoiceProfileInfo]:
    """Return the list of available sacred voice profiles."""
    return [
        VoiceProfileInfo(
            id="narrator_male",
            label="Lektor — głos męski",
            description="Głęboki, spokojny głos lektora. Idealny do czytania Pisma Świętego.",
            gender="male",
            style="authoritative",
        ),
        VoiceProfileInfo(
            id="narrator_female",
            label="Lektorka — głos żeński",
            description="Ciepły, jasny głos. Polecany do modlitw i refleksji.",
            gender="female",
            style="warm",
        ),
        VoiceProfileInfo(
            id="contemplative",
            label="Kontemplacyjny",
            description="Miękki, medytacyjny głos. Przeznaczony do Contemplatio i ciszy.",
            gender="neutral",
            style="meditative",
        ),
        VoiceProfileInfo(
            id="sacred",
            label="Sakralny",
            description="Rezonujący, uroczysty głos. Używany do tekstów liturgicznych.",
            gender="neutral",
            style="reverential",
        ),
    ]
