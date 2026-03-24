"""Text-to-Speech service with sacred voice profiles.

Primary provider: OpenAI TTS (tts-1-hd)
Premium provider: ElevenLabs (when ELEVENLABS_API_KEY is set)

Voice profiles are mapped to spiritually appropriate voices:
  - narrator_male    → deep, calm (OpenAI: onyx / ElevenLabs: custom)
  - narrator_female  → warm, gentle (OpenAI: nova / ElevenLabs: custom)
  - contemplative    → soft, meditative (OpenAI: echo)
  - sacred           → resonant, reverent (OpenAI: fable)
"""

from __future__ import annotations

import logging
from enum import Enum

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceProfile(str, Enum):
    NARRATOR_MALE = "narrator_male"
    NARRATOR_FEMALE = "narrator_female"
    CONTEMPLATIVE = "contemplative"
    SACRED = "sacred"


# OpenAI voice mapping (tts-1-hd model)
_OPENAI_VOICES: dict[VoiceProfile, str] = {
    VoiceProfile.NARRATOR_MALE: "onyx",        # deep, authoritative
    VoiceProfile.NARRATOR_FEMALE: "nova",       # warm, clear
    VoiceProfile.CONTEMPLATIVE: "echo",         # soft, meditative
    VoiceProfile.SACRED: "fable",               # resonant, expressive
}

# ElevenLabs voice IDs — configure in .env with your custom sacred voices
_ELEVENLABS_VOICES: dict[VoiceProfile, str] = {
    VoiceProfile.NARRATOR_MALE: settings.ELEVENLABS_VOICE_NARRATOR_MALE,
    VoiceProfile.NARRATOR_FEMALE: settings.ELEVENLABS_VOICE_NARRATOR_FEMALE,
    VoiceProfile.CONTEMPLATIVE: settings.ELEVENLABS_VOICE_CONTEMPLATIVE,
    VoiceProfile.SACRED: settings.ELEVENLABS_VOICE_SACRED,
}

_ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class TTSService:
    """Convert text to sacred-quality speech audio (MP3 bytes)."""

    def __init__(self) -> None:
        self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self._use_elevenlabs = bool(
            settings.ELEVENLABS_API_KEY
            and settings.ELEVENLABS_VOICE_NARRATOR_MALE
        )

    async def synthesize(
        self,
        text: str,
        profile: VoiceProfile = VoiceProfile.NARRATOR_MALE,
        speed: float = 0.9,  # slightly slower for contemplative listening
    ) -> bytes:
        """Return MP3 audio bytes for *text* using *profile*.

        Falls back from ElevenLabs → OpenAI → raises if neither configured.
        """
        if len(text) > 4096:
            text = text[:4096]

        if self._use_elevenlabs:
            try:
                return await self._elevenlabs_synthesize(text, profile)
            except Exception as exc:
                logger.warning("ElevenLabs TTS failed, falling back to OpenAI: %s", exc)

        if self._openai:
            return await self._openai_synthesize(text, profile, speed)

        raise RuntimeError("No TTS provider configured (OPENAI_API_KEY or ELEVENLABS_API_KEY required)")

    # ── OpenAI TTS ────────────────────────────────────────────────────────

    async def _openai_synthesize(
        self,
        text: str,
        profile: VoiceProfile,
        speed: float,
    ) -> bytes:
        voice = _OPENAI_VOICES[profile]
        response = await self._openai.audio.speech.create(
            model="tts-1-hd",
            voice=voice,  # type: ignore[arg-type]
            input=text,
            response_format="mp3",
            speed=speed,
        )
        return response.content

    # ── ElevenLabs TTS ────────────────────────────────────────────────────

    async def _elevenlabs_synthesize(self, text: str, profile: VoiceProfile) -> bytes:
        voice_id = _ELEVENLABS_VOICES[profile]
        url = _ELEVENLABS_TTS_URL.format(voice_id=voice_id)

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.2,
                "use_speaker_boost": True,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "xi-api-key": settings.ELEVENLABS_API_KEY,
                    "Accept": "audio/mpeg",
                },
            )
            resp.raise_for_status()
            return resp.content


# Module-level singleton
tts_service = TTSService()
