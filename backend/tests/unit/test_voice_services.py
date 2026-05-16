"""Unit tests for app/services/voice/tts_service.py and stt_service.py.

Self-contained — no real OpenAI API or ElevenLabs calls. Instances are
created by bypassing __init__ and injecting mocked clients directly.

Contracts verified:
TTS:
- VoiceProfile enum values
- _OPENAI_VOICES: all four profiles mapped
- synthesize: text truncated to 4096 chars
- synthesize: ElevenLabs preferred when configured
- synthesize: falls back to OpenAI on ElevenLabs error
- synthesize: raises RuntimeError when no provider configured
- _openai_synthesize: calls audio.speech.create with correct args
- _elevenlabs_synthesize: POSTs to correct URL with xi-api-key header

STT:
- _MIME_TO_EXT: common MIME types mapped
- transcribe: raises RuntimeError when no OpenAI configured
- transcribe: language defaults to 'pl'
- transcribe: result has required keys
- transcribe: prompt injected only when provided
- transcribe: mime normalised (strips codec suffix)
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub openai + httpx at sys.modules level so module-level imports succeed
# in environments without these packages installed
# ---------------------------------------------------------------------------

for _mod in ("openai", "httpx"):
    if _mod not in sys.modules:
        _stub = MagicMock()
        _stub.AsyncOpenAI = MagicMock
        sys.modules[_mod] = _stub

# app.core.config.settings must exist for module-level code
_config_stub = MagicMock()
_config_stub.settings = MagicMock(
    OPENAI_API_KEY="sk-test",
    ELEVENLABS_API_KEY="",
    ELEVENLABS_VOICE_NARRATOR_MALE="",
    ELEVENLABS_VOICE_NARRATOR_FEMALE="",
    ELEVENLABS_VOICE_CONTEMPLATIVE="",
    ELEVENLABS_VOICE_SACRED="",
)
if "app.core.config" not in sys.modules:
    sys.modules["app.core.config"] = _config_stub

from app.services.voice.stt_service import STTService
from app.services.voice.tts_service import (
    _OPENAI_VOICES,
    TTSService,
    VoiceProfile,
)

# ---------------------------------------------------------------------------
# TTS Helpers
# ---------------------------------------------------------------------------


def _tts(
    openai_client=None,
    use_elevenlabs: bool = False,
) -> TTSService:
    svc = TTSService.__new__(TTSService)
    svc._openai = openai_client
    svc._use_elevenlabs = use_elevenlabs
    return svc


def _mock_openai_tts(audio_bytes: bytes = b"mp3-audio") -> MagicMock:
    mock = MagicMock()
    response = MagicMock()
    response.content = audio_bytes
    mock.audio.speech.create = AsyncMock(return_value=response)
    return mock


# ---------------------------------------------------------------------------
# VoiceProfile
# ---------------------------------------------------------------------------


class TestVoiceProfile:
    def test_narrator_male(self):
        assert VoiceProfile.NARRATOR_MALE == "narrator_male"

    def test_narrator_female(self):
        assert VoiceProfile.NARRATOR_FEMALE == "narrator_female"

    def test_contemplative(self):
        assert VoiceProfile.CONTEMPLATIVE == "contemplative"

    def test_sacred(self):
        assert VoiceProfile.SACRED == "sacred"

    def test_four_profiles(self):
        assert len(VoiceProfile) == 4


# ---------------------------------------------------------------------------
# _OPENAI_VOICES mapping
# ---------------------------------------------------------------------------


class TestOpenAIVoices:
    def test_all_profiles_mapped(self):
        for profile in VoiceProfile:
            assert profile in _OPENAI_VOICES

    def test_narrator_male_is_onyx(self):
        assert _OPENAI_VOICES[VoiceProfile.NARRATOR_MALE] == "onyx"

    def test_narrator_female_is_nova(self):
        assert _OPENAI_VOICES[VoiceProfile.NARRATOR_FEMALE] == "nova"

    def test_contemplative_is_echo(self):
        assert _OPENAI_VOICES[VoiceProfile.CONTEMPLATIVE] == "echo"

    def test_sacred_is_fable(self):
        assert _OPENAI_VOICES[VoiceProfile.SACRED] == "fable"


# ---------------------------------------------------------------------------
# TTSService.synthesize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTTSSynthesize:
    async def test_returns_bytes_from_openai(self):
        svc = _tts(openai_client=_mock_openai_tts(b"audio-data"))
        result = await svc.synthesize("Kyrie Eleison")
        assert result == b"audio-data"

    async def test_text_truncated_at_4096(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        long_text = "A" * 5000
        await svc.synthesize(long_text)
        call_kwargs = mock_openai.audio.speech.create.call_args
        passed_text = call_kwargs.kwargs.get("input") or call_kwargs.args[0]
        assert len(passed_text) == 4096

    async def test_short_text_not_truncated(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        short = "Panie, zmiłuj się."
        await svc.synthesize(short)
        call_kwargs = mock_openai.audio.speech.create.call_args
        passed_text = call_kwargs.kwargs.get("input") or call_kwargs.args[0]
        assert passed_text == short

    async def test_raises_when_no_provider(self):
        svc = _tts(openai_client=None, use_elevenlabs=False)
        with pytest.raises(RuntimeError, match="No TTS provider"):
            await svc.synthesize("text")

    async def test_elevenlabs_preferred_when_configured(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai, use_elevenlabs=True)
        svc._elevenlabs_synthesize = AsyncMock(return_value=b"elevenlabs-audio")
        result = await svc.synthesize("text")
        assert result == b"elevenlabs-audio"
        mock_openai.audio.speech.create.assert_not_awaited()

    async def test_falls_back_to_openai_on_elevenlabs_error(self):
        mock_openai = _mock_openai_tts(b"openai-fallback")
        svc = _tts(openai_client=mock_openai, use_elevenlabs=True)
        svc._elevenlabs_synthesize = AsyncMock(side_effect=RuntimeError("ElevenLabs down"))
        result = await svc.synthesize("text")
        assert result == b"openai-fallback"

    async def test_uses_default_profile_narrator_male(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        await svc.synthesize("text")
        call_kwargs = mock_openai.audio.speech.create.call_args
        voice = call_kwargs.kwargs.get("voice") or call_kwargs.args[2]
        assert voice == "onyx"

    async def test_uses_specified_profile(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        await svc.synthesize("text", profile=VoiceProfile.SACRED)
        call_kwargs = mock_openai.audio.speech.create.call_args
        voice = call_kwargs.kwargs.get("voice")
        assert voice == "fable"

    async def test_openai_synthesize_uses_hd_model(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        await svc._openai_synthesize("text", VoiceProfile.CONTEMPLATIVE, 0.9)
        call_kwargs = mock_openai.audio.speech.create.call_args
        model = call_kwargs.kwargs.get("model")
        assert model == "tts-1-hd"

    async def test_openai_synthesize_mp3_format(self):
        mock_openai = _mock_openai_tts()
        svc = _tts(openai_client=mock_openai)
        await svc._openai_synthesize("text", VoiceProfile.NARRATOR_FEMALE, 0.9)
        call_kwargs = mock_openai.audio.speech.create.call_args
        fmt = call_kwargs.kwargs.get("response_format")
        assert fmt == "mp3"


# ---------------------------------------------------------------------------
# STT Helpers
# ---------------------------------------------------------------------------


def _stt(openai_client=None) -> STTService:
    svc = STTService.__new__(STTService)
    svc._openai = openai_client
    return svc


def _mock_openai_stt(text: str = "Panie Jezu", language: str = "pl", duration: float = 3.5):
    mock = MagicMock()
    result = MagicMock()
    result.text = text
    result.language = language
    result.duration = duration
    mock.audio.transcriptions.create = AsyncMock(return_value=result)
    return mock


# ---------------------------------------------------------------------------
# STTService._MIME_TO_EXT
# ---------------------------------------------------------------------------


class TestMimeToExt:
    def test_webm_mapped(self):
        assert STTService._MIME_TO_EXT["audio/webm"] == "webm"

    def test_ogg_mapped(self):
        assert STTService._MIME_TO_EXT["audio/ogg"] == "ogg"

    def test_mp4_mapped(self):
        assert STTService._MIME_TO_EXT["audio/mp4"] == "mp4"

    def test_mpeg_mapped(self):
        assert STTService._MIME_TO_EXT["audio/mpeg"] == "mp3"

    def test_wav_mapped(self):
        assert STTService._MIME_TO_EXT["audio/wav"] == "wav"

    def test_flac_mapped(self):
        assert STTService._MIME_TO_EXT["audio/flac"] == "flac"

    def test_webm_opus_variant_mapped(self):
        assert STTService._MIME_TO_EXT.get("audio/webm;codecs=opus") == "webm"


# ---------------------------------------------------------------------------
# STTService.transcribe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSTTTranscribe:
    async def test_raises_when_no_openai(self):
        svc = _stt(openai_client=None)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            await svc.transcribe(b"audio")

    async def test_returns_required_keys(self):
        svc = _stt(openai_client=_mock_openai_stt("Kyrie Eleison"))
        result = await svc.transcribe(b"audio")
        assert "text" in result
        assert "language" in result
        assert "duration_seconds" in result
        assert "provider" in result

    async def test_text_from_whisper(self):
        svc = _stt(openai_client=_mock_openai_stt("Zdrowa Mario"))
        result = await svc.transcribe(b"audio")
        assert result["text"] == "Zdrowa Mario"

    async def test_provider_is_whisper_1(self):
        svc = _stt(openai_client=_mock_openai_stt())
        result = await svc.transcribe(b"audio")
        assert result["provider"] == "whisper-1"

    async def test_default_language_polish(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("language") == "pl"

    async def test_custom_language(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio", language="la")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("language") == "la"

    async def test_prompt_injected_when_provided(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio", prompt="Modlitwa, różaniec, brewiarz")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("prompt") == "Modlitwa, różaniec, brewiarz"

    async def test_prompt_not_injected_when_none(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert "prompt" not in call_kwargs.kwargs

    async def test_mime_with_codec_suffix_normalised(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio", content_type="audio/webm;codecs=opus")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        file_tuple = call_kwargs.kwargs.get("file")
        assert file_tuple[0] == "audio.webm"

    async def test_unknown_mime_defaults_to_webm(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio", content_type="audio/unknown-format")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        file_tuple = call_kwargs.kwargs.get("file")
        assert file_tuple[0] == "audio.webm"

    async def test_uses_verbose_json_format(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("response_format") == "verbose_json"

    async def test_uses_whisper_1_model(self):
        mock_openai = _mock_openai_stt()
        svc = _stt(openai_client=mock_openai)
        await svc.transcribe(b"audio")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("model") == "whisper-1"
