"""Unit tests for Lectio Divina SSE streaming endpoint."""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
    "langchain_openai", "langchain_anthropic", "langchain_core",
    "langgraph", "langgraph.graph",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest


class TestSSEEventFormat:
    def test_sse_format_has_event_and_data(self):
        from app.api.routes.lectio_divina import _sse_event

        frame = _sse_event("stage", {"key": "value"})
        assert frame.startswith("event: stage\n")
        assert "data: " in frame
        assert frame.endswith("\n\n")

    def test_sse_data_is_valid_json(self):
        from app.api.routes.lectio_divina import _sse_event

        frame = _sse_event("complete", {"scripture": "Ps 34,19", "tradition": "ignatian"})
        data_line = [l for l in frame.splitlines() if l.startswith("data:")][0]
        payload = json.loads(data_line[len("data: "):])
        assert payload["tradition"] == "ignatian"

    def test_done_event_closes_stream(self):
        from app.api.routes.lectio_divina import _sse_event

        frame = _sse_event("done", {})
        assert "event: done" in frame

    def test_error_event_format(self):
        from app.api.routes.lectio_divina import _sse_event

        frame = _sse_event("error", {"detail": "Błąd"})
        assert "event: error" in frame
        assert "Błąd" in frame


class TestNodeLabels:
    def test_all_nodes_have_labels(self):
        from app.api.routes.lectio_divina import _NODE_LABELS

        expected_nodes = {
            "emotion_analysis", "scripture_selection", "lectio",
            "meditatio", "oratio", "contemplatio", "actio", "crisis_handler",
        }
        assert expected_nodes == set(_NODE_LABELS.keys())

    def test_labels_are_non_empty_strings(self):
        from app.api.routes.lectio_divina import _NODE_LABELS

        for node, label in _NODE_LABELS.items():
            assert isinstance(label, str) and len(label) > 0, f"Empty label for {node}"


class TestStreamingEndpointRegistered:
    def test_run_stream_route_exists(self):
        from app.api.routes.lectio_divina import router

        paths = [r.path for r in router.routes]
        assert "/run/stream" in paths

    def test_run_stream_is_post(self):
        from app.api.routes.lectio_divina import router

        for route in router.routes:
            if route.path == "/run/stream":
                assert "POST" in route.methods
                break
