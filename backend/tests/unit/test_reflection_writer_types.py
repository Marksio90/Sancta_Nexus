"""Unit tests for ReflectionWriterAgent data types and constants.

No LLM, no network, no async — pure type and data-layer testing.

Contracts verified:
ReflectionLayer enum:
- Exactly 4 layers
- Values: exegetical, existential, mystical, practical
- Is a str+Enum

ScripturePassage dataclass:
- Required: reference, text, book, chapter, verses
- Optional: liturgical_context, original_language_notes

UserContext dataclass:
- Required: user_id
- Default theological_depth == "intermediate"
- Default preferred_language == "pl"
- Default spiritual_stage is None

ReflectionLayerContent dataclass:
- Required: layer, title, content
- Default sources == []
- Default key_insight == ""

Reflection dataclass:
- Required: passage, layers, synthesis, prayer_response, action_step
- Default patristic_quotes == []
- Default metadata == {}

REFLECTION_SYSTEM_PROMPT:
- Non-empty string
- Mentions all 4 layer names in Polish
- References Polish spiritual masters

RAG_QUERY_TEMPLATE:
- Has {reference} format placeholder
- Mentions Ojcowie Kościoła / patristic tradition

ReflectionWriterAgent class attributes:
- agent_id == "A-029"
- agent_name == "ReflectionWriterAgent"
"""

from __future__ import annotations

from app.agents.generative.reflection_writer import (
    RAG_QUERY_TEMPLATE,
    REFLECTION_SYSTEM_PROMPT,
    Reflection,
    ReflectionLayer,
    ReflectionLayerContent,
    ReflectionWriterAgent,
    ScripturePassage,
    UserContext,
)

# ===========================================================================
# ReflectionLayer enum
# ===========================================================================


class TestReflectionLayer:
    def test_exactly_4_layers(self):
        assert len(ReflectionLayer) == 4

    def test_exegetical_value(self):
        assert ReflectionLayer.EXEGETICAL.value == "exegetical"

    def test_existential_value(self):
        assert ReflectionLayer.EXISTENTIAL.value == "existential"

    def test_mystical_value(self):
        assert ReflectionLayer.MYSTICAL.value == "mystical"

    def test_practical_value(self):
        assert ReflectionLayer.PRACTICAL.value == "practical"

    def test_is_str_subclass(self):
        assert isinstance(ReflectionLayer.EXEGETICAL, str)

    def test_all_values_unique(self):
        vals = [layer.value for layer in ReflectionLayer]
        assert len(vals) == len(set(vals))


# ===========================================================================
# ScripturePassage dataclass
# ===========================================================================


class TestScripturePassage:
    def _make(self) -> ScripturePassage:
        return ScripturePassage(
            reference="J 15,1-8",
            text="Ja jestem krzewem winnym",
            book="J",
            chapter=15,
            verses="1-8",
        )

    def test_required_fields(self):
        p = self._make()
        assert p.reference == "J 15,1-8"
        assert p.text == "Ja jestem krzewem winnym"
        assert p.book == "J"
        assert p.chapter == 15
        assert p.verses == "1-8"

    def test_liturgical_context_defaults_none(self):
        assert self._make().liturgical_context is None

    def test_original_language_notes_defaults_none(self):
        assert self._make().original_language_notes is None

    def test_with_optional_fields(self):
        p = ScripturePassage(
            reference="J 15,1",
            text="Ja jestem",
            book="J",
            chapter=15,
            verses="1",
            liturgical_context="V Niedziela Wielkanocna",
            original_language_notes="ἐγώ εἰμι ἡ ἄμπελος",
        )
        assert p.liturgical_context == "V Niedziela Wielkanocna"
        assert "ἄμπελος" in p.original_language_notes


# ===========================================================================
# UserContext dataclass
# ===========================================================================


class TestUserContext:
    def test_required_user_id(self):
        ctx = UserContext(user_id="user-001")
        assert ctx.user_id == "user-001"

    def test_default_theological_depth(self):
        assert UserContext(user_id="u").theological_depth == "intermediate"

    def test_default_preferred_language(self):
        assert UserContext(user_id="u").preferred_language == "pl"

    def test_default_spiritual_stage_none(self):
        assert UserContext(user_id="u").spiritual_stage is None

    def test_default_current_struggles_none(self):
        assert UserContext(user_id="u").current_struggles is None

    def test_default_prayer_tradition_none(self):
        assert UserContext(user_id="u").prayer_tradition is None

    def test_custom_values(self):
        ctx = UserContext(
            user_id="u",
            spiritual_stage="illumination",
            current_struggles=["samotność"],
            prayer_tradition="ignatian",
            theological_depth="advanced",
            preferred_language="en",
        )
        assert ctx.spiritual_stage == "illumination"
        assert ctx.current_struggles == ["samotność"]
        assert ctx.prayer_tradition == "ignatian"
        assert ctx.theological_depth == "advanced"
        assert ctx.preferred_language == "en"


# ===========================================================================
# ReflectionLayerContent dataclass
# ===========================================================================


class TestReflectionLayerContent:
    def test_required_fields(self):
        rlc = ReflectionLayerContent(
            layer=ReflectionLayer.MYSTICAL,
            title="Wymiar mistyczny",
            content="Kontemplacja ukrytej obecności Boga.",
        )
        assert rlc.layer == ReflectionLayer.MYSTICAL
        assert rlc.title == "Wymiar mistyczny"
        assert rlc.content == "Kontemplacja ukrytej obecności Boga."

    def test_default_sources_empty_list(self):
        rlc = ReflectionLayerContent(
            layer=ReflectionLayer.EXEGETICAL, title="T", content="C"
        )
        assert rlc.sources == []

    def test_default_key_insight_empty_string(self):
        rlc = ReflectionLayerContent(
            layer=ReflectionLayer.PRACTICAL, title="T", content="C"
        )
        assert rlc.key_insight == ""

    def test_custom_sources(self):
        rlc = ReflectionLayerContent(
            layer=ReflectionLayer.MYSTICAL,
            title="T",
            content="C",
            sources=["Augustyn", "Tomasz"],
        )
        assert "Augustyn" in rlc.sources

    def test_custom_key_insight(self):
        rlc = ReflectionLayerContent(
            layer=ReflectionLayer.EXISTENTIAL,
            title="T",
            content="C",
            key_insight="Bóg jest blisko.",
        )
        assert rlc.key_insight == "Bóg jest blisko."


# ===========================================================================
# Reflection dataclass
# ===========================================================================


class TestReflection:
    def _make_passage(self) -> ScripturePassage:
        return ScripturePassage(
            reference="Rz 8,28",
            text="Wiemy, że wszystko co się dzieje, służy ku dobremu.",
            book="Rz",
            chapter=8,
            verses="28",
        )

    def _make_layer(self, layer: ReflectionLayer) -> ReflectionLayerContent:
        return ReflectionLayerContent(
            layer=layer,
            title=f"Tytuł {layer.value}",
            content="Treść refleksji.",
        )

    def test_required_fields(self):
        r = Reflection(
            passage=self._make_passage(),
            layers=[self._make_layer(ReflectionLayer.EXEGETICAL)],
            synthesis="Synteza refleksji.",
            prayer_response="Modlitwa odpowiedzi.",
            action_step="Krok działania.",
        )
        assert r.synthesis == "Synteza refleksji."
        assert r.prayer_response == "Modlitwa odpowiedzi."
        assert r.action_step == "Krok działania."

    def test_default_patristic_quotes_empty(self):
        r = Reflection(
            passage=self._make_passage(),
            layers=[],
            synthesis="S",
            prayer_response="P",
            action_step="A",
        )
        assert r.patristic_quotes == []

    def test_default_metadata_empty(self):
        r = Reflection(
            passage=self._make_passage(),
            layers=[],
            synthesis="S",
            prayer_response="P",
            action_step="A",
        )
        assert r.metadata == {}

    def test_passage_stored(self):
        p = self._make_passage()
        r = Reflection(
            passage=p, layers=[], synthesis="S", prayer_response="P", action_step="A"
        )
        assert r.passage is p

    def test_custom_metadata(self):
        r = Reflection(
            passage=self._make_passage(),
            layers=[],
            synthesis="S",
            prayer_response="P",
            action_step="A",
            metadata={"agent_id": "A-029"},
        )
        assert r.metadata["agent_id"] == "A-029"


# ===========================================================================
# REFLECTION_SYSTEM_PROMPT constant
# ===========================================================================


class TestReflectionSystemPrompt:
    def test_non_empty(self):
        assert len(REFLECTION_SYSTEM_PROMPT.strip()) > 100

    def test_is_string(self):
        assert isinstance(REFLECTION_SYSTEM_PROMPT, str)

    def test_mentions_egzegetyczna(self):
        assert "EGZEGETYCZNA" in REFLECTION_SYSTEM_PROMPT or "egzegetyczna" in REFLECTION_SYSTEM_PROMPT.lower()

    def test_mentions_egzystencjalna(self):
        assert "EGZYSTENCJALNA" in REFLECTION_SYSTEM_PROMPT or "egzystencjalna" in REFLECTION_SYSTEM_PROMPT.lower()

    def test_mentions_mistyczna(self):
        assert "MISTYCZNA" in REFLECTION_SYSTEM_PROMPT or "mistyczna" in REFLECTION_SYSTEM_PROMPT.lower()

    def test_mentions_praktyczna(self):
        assert "PRAKTYCZNA" in REFLECTION_SYSTEM_PROMPT or "praktyczna" in REFLECTION_SYSTEM_PROMPT.lower()

    def test_mentions_teresa(self):
        assert "Teresa" in REFLECTION_SYSTEM_PROMPT or "Teresy" in REFLECTION_SYSTEM_PROMPT

    def test_mentions_jan_od_krzyza(self):
        assert "Jana od Krzyża" in REFLECTION_SYSTEM_PROMPT or "Jan od Krzyza" in REFLECTION_SYSTEM_PROMPT

    def test_mentions_polish_language(self):
        assert "polskim" in REFLECTION_SYSTEM_PROMPT or "polsk" in REFLECTION_SYSTEM_PROMPT.lower()


# ===========================================================================
# RAG_QUERY_TEMPLATE constant
# ===========================================================================


class TestRagQueryTemplate:
    def test_has_reference_placeholder(self):
        assert "{reference}" in RAG_QUERY_TEMPLATE

    def test_is_string(self):
        assert isinstance(RAG_QUERY_TEMPLATE, str)

    def test_non_empty(self):
        assert len(RAG_QUERY_TEMPLATE.strip()) > 20

    def test_mentions_augustyn(self):
        assert "Augustyn" in RAG_QUERY_TEMPLATE

    def test_mentions_tomasz(self):
        assert "Tomasz" in RAG_QUERY_TEMPLATE

    def test_formattable_with_reference(self):
        result = RAG_QUERY_TEMPLATE.format(reference="J 3,16")
        assert "J 3,16" in result


# ===========================================================================
# ReflectionWriterAgent class attributes
# ===========================================================================


class TestReflectionWriterAgentAttributes:
    def test_agent_id(self):
        assert ReflectionWriterAgent.agent_id == "A-029"

    def test_agent_name(self):
        assert ReflectionWriterAgent.agent_name == "ReflectionWriterAgent"

    def test_init_without_llm(self):
        agent = ReflectionWriterAgent()
        assert agent._llm is None
        assert agent._vector_store is None

    def test_init_with_llm(self):
        mock_llm = object()
        agent = ReflectionWriterAgent(llm_client=mock_llm)
        assert agent._llm is mock_llm

    def test_init_with_vector_store(self):
        mock_vs = object()
        agent = ReflectionWriterAgent(vector_store=mock_vs)
        assert agent._vector_store is mock_vs
