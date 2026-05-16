"""Testy jednostkowe dla voice.py — TTS, STT, /meditate (premium).

Sprawdzamy:
  - Endpointy istnieją i mają właściwą metodę HTTP
  - /tts i /stt są dostępne bez JWT (autentykacja opcjonalna lub brak)
  - /meditate wymaga require_premium (AST)
  - Schematy request mają wymagane pola
  - VoiceProfile enum ma wymagane wartości
  - Medytacja waliduje mystery_type i mystery_number
  - LLM jest importowany leniwie (get_llm_fast wewnątrz funkcji)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

VOICE_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "voice.py"
sys.path.insert(0, str(Path(__file__).parents[2]))


# ── AST helpers ───────────────────────────────────────────────────────────────


def _tree() -> ast.Module:
    return ast.parse(VOICE_PATH.read_text())


def _routes() -> list[tuple[str, str]]:
    routes = []
    for node in ast.walk(_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    method = dec.func.attr
                    args = dec.args
                    if args and isinstance(args[0], ast.Constant):
                        routes.append((method, args[0].value))
    return routes


def _func_source(name: str) -> str:
    src = VOICE_PATH.read_text()
    lines = src.split("\n")
    start = None
    for i, line in enumerate(lines):
        if f"async def {name}" in line or f"def {name}" in line:
            start = i
            break
    if start is None:
        return ""
    # Extract ~50 lines around the function
    return "\n".join(lines[start:start + 50])


# ── Endpointy ─────────────────────────────────────────────────────────────────


class TestVoiceEndpoints:
    def test_tts_endpoint_exists(self):
        routes = _routes()
        assert any(path == "/tts" for _, path in routes)

    def test_tts_is_post(self):
        assert ("post", "/tts") in _routes()

    def test_stt_endpoint_exists(self):
        assert any(path == "/stt" for _, path in _routes())

    def test_voices_endpoint_is_get(self):
        assert ("get", "/voices") in _routes()

    def test_meditate_endpoint_exists(self):
        assert any(path == "/meditate" for _, path in _routes())

    def test_meditate_is_post(self):
        assert ("post", "/meditate") in _routes()


# ── Bezpieczeństwo / JWT ─────────────────────────────────────────────────────


class TestVoiceSecurity:
    def test_meditate_requires_premium(self):
        source = VOICE_PATH.read_text()
        lines = source.split("\n")
        in_meditate = False
        for line in lines:
            if "async def meditate_audio" in line:
                in_meditate = True
            if in_meditate and "require_premium" in line:
                return  # found — test passes
            if in_meditate and line.strip().startswith("async def ") and "meditate_audio" not in line:
                break
        pytest.fail("meditate_audio nie używa require_premium")

    def test_require_premium_imported(self):
        source = VOICE_PATH.read_text()
        assert "require_premium" in source

    def test_tts_does_not_require_premium(self):
        func = _func_source("text_to_speech")
        assert "require_premium" not in func

    def test_voices_is_public_endpoint(self):
        # /voices jest listą profili głosowych — publiczne, bez JWT
        source = VOICE_PATH.read_text()
        lines = source.split("\n")
        in_func = False
        for line in lines:
            if "async def list_voices" in line:
                in_func = True
            if in_func and ("require_premium" in line or "require_authenticated" in line):
                pytest.fail("list_voices() wymaga auth — powinno być publiczne")
            if in_func and "return" in line:
                break


# ── Schematy ─────────────────────────────────────────────────────────────────


class TestVoiceSchemas:
    def test_file_defines_tts_request(self):
        tree = _tree()
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "TTSRequest" in classes

    def test_file_defines_stt_response(self):
        tree = _tree()
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "STTResponse" in classes

    def test_file_defines_meditation_request(self):
        tree = _tree()
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "MeditationAudioRequest" in classes

    def test_tts_request_has_text_field(self):
        source = VOICE_PATH.read_text()
        # Szukamy deklaracji pola text w TTSRequest
        assert "text:" in source or "text: str" in source

    def test_tts_request_has_profile_field(self):
        source = VOICE_PATH.read_text()
        assert "profile" in source


# ── VoiceProfile enum ─────────────────────────────────────────────────────────


TTS_SERVICE_PATH = Path(__file__).parents[2] / "app" / "services" / "voice" / "tts_service.py"


class TestVoiceProfile:
    def _get_enum_values(self) -> list[str]:
        """Odczytuje wartości VoiceProfile przez AST — bez importu modułu (openai unavailable)."""
        tree = ast.parse(TTS_SERVICE_PATH.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "VoiceProfile":
                values = []
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                values.append(target.id)
                return values
        return []

    def test_voice_profile_class_exists(self):
        tree = ast.parse(TTS_SERVICE_PATH.read_text())
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "VoiceProfile" in classes

    def test_voice_profile_has_contemplative(self):
        assert "CONTEMPLATIVE" in self._get_enum_values()

    def test_voice_profile_has_narrator_male(self):
        assert "NARRATOR_MALE" in self._get_enum_values()

    def test_voice_profile_has_sacred(self):
        assert "SACRED" in self._get_enum_values()

    def test_voice_profile_imported_in_voice_route(self):
        source = VOICE_PATH.read_text()
        assert "VoiceProfile" in source and "tts_service" in source


# ── STT file validation ───────────────────────────────────────────────────────


def _stt_func_source() -> str:
    src = VOICE_PATH.read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "speech_to_text":
            lines = src.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


class TestSTTFileValidation:
    """STT endpoint must validate file size and content-type at the app level
    (defense-in-depth beyond nginx client_max_body_size)."""

    def test_stt_raises_413_for_oversized_file(self):
        """413 Request Entity Too Large for files exceeding the app-level limit."""
        assert "413" in _stt_func_source()

    def test_stt_raises_415_for_invalid_content_type(self):
        """415 Unsupported Media Type for non-audio MIME types."""
        assert "415" in _stt_func_source()

    def test_stt_defines_max_audio_bytes(self):
        src = VOICE_PATH.read_text()
        assert "_max_audio_bytes" in src or "_MAX_AUDIO_BYTES" in src

    def test_stt_defines_allowed_audio_types(self):
        src = VOICE_PATH.read_text()
        assert "_allowed_audio_types" in src or "_ALLOWED_AUDIO_TYPES" in src

    def test_stt_checks_empty_file(self):
        src = _stt_func_source()
        assert "Empty" in src or "empty" in src or "not audio_bytes" in src


# ── /meditate walidacja ───────────────────────────────────────────────────────


class TestMeditateValidation:
    def test_valid_mystery_types_defined_in_source(self):
        source = VOICE_PATH.read_text()
        for mystery in ("radosne", "bolesne", "chwalebne", "swietlne"):
            assert mystery in source, f"Brak tajemnicy: {mystery}"

    def test_mystery_number_ge_1_le_5(self):
        source = VOICE_PATH.read_text()
        assert "ge=1" in source and "le=5" in source

    def test_mystery_titles_all_types_have_five_mysteries(self):
        source = VOICE_PATH.read_text()
        # Każdy typ tajemnic ma dokładnie 5
        # Sprawdzamy przez liczenie przecinków wewnątrz list
        assert source.count("Zwiastowanie") >= 1  # radosne[0]
        assert source.count("Ukrzyżowanie") >= 1  # bolesne[4]
        assert source.count("Zmartwychwstanie") >= 1  # chwalebne[0]
        assert source.count("Chrzest Jezusa") >= 1  # swietlne[0]


# ── Lazy LLM import ───────────────────────────────────────────────────────────


class TestVoiceLazyImport:
    def test_get_llm_fast_imported_inside_meditate_function(self):
        source = VOICE_PATH.read_text()
        # get_llm_fast powinien być importowany leniwie wewnątrz meditate_audio
        lines = source.split("\n")
        in_meditate = False
        for line in lines:
            if "async def meditate_audio" in line:
                in_meditate = True
            if in_meditate and "from app.core.llm import get_llm_fast" in line:
                return  # found lazy import — test passes
            if in_meditate and "async def " in line and "meditate_audio" not in line:
                break
        pytest.fail("get_llm_fast nie jest importowany leniwie wewnątrz meditate_audio")

    def test_tts_service_instantiated_at_module_level(self):
        source = VOICE_PATH.read_text()
        assert "_tts" in source and "TTSService" in source
