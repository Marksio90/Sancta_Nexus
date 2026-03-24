"""Speech-to-Text service using OpenAI Whisper.

Accepts audio bytes (webm, mp4, wav, ogg, mp3) and returns a Polish
transcription with confidence metadata.

The frontend may call this endpoint when the browser's native Web Speech API
is unavailable (e.g. Firefox on Linux, certain mobile browsers).
"""

from __future__ import annotations

import io
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    """Transcribe prayer audio to text via OpenAI Whisper."""

    # Supported MIME → file extension mapping required by OpenAI API
    _MIME_TO_EXT: dict[str, str] = {
        "audio/webm": "webm",
        "audio/webm;codecs=opus": "webm",
        "audio/ogg": "ogg",
        "audio/ogg;codecs=opus": "ogg",
        "audio/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/flac": "flac",
    }

    def __init__(self) -> None:
        self._openai = (
            AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            if settings.OPENAI_API_KEY
            else None
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/webm",
        language: str = "pl",
        prompt: str | None = None,
    ) -> dict[str, object]:
        """Transcribe *audio_bytes* and return structured result.

        Returns::

            {
                "text": "Panie Jezu, proszę...",
                "language": "pl",
                "duration_seconds": 4.2,
                "provider": "whisper-1",
            }
        """
        if not self._openai:
            raise RuntimeError("OPENAI_API_KEY not configured — STT unavailable")

        # Normalise content-type (strip parameters for matching)
        mime = content_type.split(";")[0].strip().lower()
        ext = self._MIME_TO_EXT.get(mime, "webm")

        file_tuple = (f"audio.{ext}", io.BytesIO(audio_bytes), content_type)

        kwargs: dict[str, object] = {
            "model": "whisper-1",
            "file": file_tuple,
            "response_format": "verbose_json",
            "language": language,
        }
        if prompt:
            # Whisper prompt helps with theological vocabulary
            kwargs["prompt"] = prompt

        result = await self._openai.audio.transcriptions.create(**kwargs)  # type: ignore[arg-type]

        return {
            "text": result.text,
            "language": getattr(result, "language", language),
            "duration_seconds": getattr(result, "duration", None),
            "provider": "whisper-1",
        }


# Module-level singleton
stt_service = STTService()
