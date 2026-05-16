"""Unit tests for OratioAgent (A-012) — catalog data and _parse_json.

No LLM, no network, no async — pure data-layer and static-method testing.

Contracts verified:
TRADITION_PROMPTS:
- Exactly 7 traditions present
- All known traditions: ignatian, carmelite, franciscan, benedictine,
  charismatic, dominican, marian
- Each prompt contains format placeholders {reference}, {text}, {emotion_state}
- Each prompt template embeds JSON schema with prayer_text, tradition,
  elements, spiritual_movement keys
- Tradition-specific theological vocabulary present in each prompt

FALLBACK_PRAYER:
- Has all required keys: prayer_text, tradition, elements, spiritual_movement
- tradition == "universal"
- spiritual_movement == "peace"
- prayer_text at least 30 chars
- elements is a non-empty list

OratioAgent.VALID_TRADITIONS:
- Is a frozenset
- Exactly 7 members
- All 7 traditions match TRADITION_PROMPTS keys
- All known tradition IDs present

OratioAgent._parse_json (static):
- Valid JSON string → correct dict
- JSON embedded in prose → extracted and parsed
- Malformed JSON → returns FALLBACK_PRAYER copy
- Empty string → returns FALLBACK_PRAYER copy
- Nested braces → outer object extracted correctly
- Missing both braces → returns FALLBACK_PRAYER copy
"""

from __future__ import annotations

import json

from app.agents.lectio_divina.oratio_agent import (
    FALLBACK_PRAYER,
    TRADITION_PROMPTS,
    OratioAgent,
)

_ALL_TRADITIONS = frozenset(
    {"ignatian", "carmelite", "franciscan", "benedictine",
     "charismatic", "dominican", "marian"}
)


# ===========================================================================
# TRADITION_PROMPTS catalog
# ===========================================================================


class TestTraditionPromptsCatalog:
    def test_exactly_7_traditions(self):
        assert len(TRADITION_PROMPTS) == 7

    def test_all_tradition_ids_present(self):
        assert set(TRADITION_PROMPTS.keys()) == _ALL_TRADITIONS

    def test_ignatian_present(self):
        assert "ignatian" in TRADITION_PROMPTS

    def test_carmelite_present(self):
        assert "carmelite" in TRADITION_PROMPTS

    def test_franciscan_present(self):
        assert "franciscan" in TRADITION_PROMPTS

    def test_benedictine_present(self):
        assert "benedictine" in TRADITION_PROMPTS

    def test_charismatic_present(self):
        assert "charismatic" in TRADITION_PROMPTS

    def test_dominican_present(self):
        assert "dominican" in TRADITION_PROMPTS

    def test_marian_present(self):
        assert "marian" in TRADITION_PROMPTS

    def test_all_are_strings(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert isinstance(prompt, str), f"{key} prompt is not a string"

    def test_all_non_empty(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert len(prompt.strip()) > 50, f"{key} prompt is too short"

    def test_all_have_reference_placeholder(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "{reference}" in prompt, f"{key} missing {{reference}}"

    def test_all_have_text_placeholder(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "{text}" in prompt, f"{key} missing {{text}}"

    def test_all_have_emotion_state_placeholder(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "{emotion_state}" in prompt, f"{key} missing {{emotion_state}}"

    def test_all_contain_prayer_text_json_key(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "prayer_text" in prompt, f"{key} missing 'prayer_text' in JSON schema"

    def test_all_contain_elements_json_key(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "elements" in prompt, f"{key} missing 'elements' in JSON schema"

    def test_all_contain_spiritual_movement_json_key(self):
        for key, prompt in TRADITION_PROMPTS.items():
            assert "spiritual_movement" in prompt, f"{key} missing 'spiritual_movement'"

    def test_all_prompts_formattable(self):
        for key, prompt in TRADITION_PROMPTS.items():
            formatted = prompt.format(
                reference="J 3,16",
                text="Bo tak Bóg umiłował świat.",
                emotion_state='{"peace": 0.9}',
            )
            assert len(formatted) > 50, f"{key} formatted prompt too short"

    # Tradition-specific theological vocabulary
    def test_ignatian_mentions_compositio(self):
        prompt = TRADITION_PROMPTS["ignatian"].lower()
        assert "compositio" in prompt or "wyobraz" in prompt

    def test_ignatian_mentions_colloquium(self):
        assert "colloquium" in TRADITION_PROMPTS["ignatian"].lower()

    def test_carmelite_mentions_teresa(self):
        prompt = TRADITION_PROMPTS["carmelite"]
        assert "Teresa" in prompt or "teresa" in prompt.lower()

    def test_carmelite_mentions_jan_od_krzyza(self):
        prompt = TRADITION_PROMPTS["carmelite"]
        assert "Jan" in prompt or "Krzyza" in prompt or "Krzyż" in prompt

    def test_franciscan_mentions_franciszek(self):
        prompt = TRADITION_PROMPTS["franciscan"]
        assert "Franciszk" in prompt

    def test_franciscan_mentions_canticle(self):
        prompt = TRADITION_PROMPTS["franciscan"]
        assert "Sloneczna" in prompt or "Canticle" in prompt or "Slonce" in prompt

    def test_benedictine_mentions_ora_et_labora(self):
        prompt = TRADITION_PROMPTS["benedictine"]
        assert "ORA ET LABORA" in prompt or "Ora et Labora" in prompt

    def test_benedictine_mentions_regula(self):
        assert "Regula" in TRADITION_PROMPTS["benedictine"] or "regula" in TRADITION_PROMPTS["benedictine"].lower()

    def test_charismatic_mentions_duch(self):
        assert "Duch" in TRADITION_PROMPTS["charismatic"]

    def test_charismatic_mentions_alleluja(self):
        prompt = TRADITION_PROMPTS["charismatic"]
        assert "Alleluja" in prompt or "alleluja" in prompt.lower()

    def test_dominican_mentions_veritas(self):
        assert "Veritas" in TRADITION_PROMPTS["dominican"] or "veritas" in TRADITION_PROMPTS["dominican"].lower()

    def test_dominican_mentions_tomasz(self):
        assert "Tomasz" in TRADITION_PROMPTS["dominican"]

    def test_marian_mentions_magnificat(self):
        assert "Magnificat" in TRADITION_PROMPTS["marian"] or "magnificat" in TRADITION_PROMPTS["marian"].lower()

    def test_marian_mentions_maryja(self):
        prompt = TRADITION_PROMPTS["marian"]
        assert "Maryj" in prompt or "Maryi" in prompt

    def test_ignatian_json_schema_has_tradition_ignatian(self):
        assert '"ignatian"' in TRADITION_PROMPTS["ignatian"]

    def test_carmelite_json_schema_has_tradition_carmelite(self):
        assert '"carmelite"' in TRADITION_PROMPTS["carmelite"]

    def test_dominican_json_schema_has_tradition_dominican(self):
        assert '"dominican"' in TRADITION_PROMPTS["dominican"]

    def test_marian_json_schema_has_tradition_marian(self):
        assert '"marian"' in TRADITION_PROMPTS["marian"]


# ===========================================================================
# FALLBACK_PRAYER constant
# ===========================================================================


class TestFallbackPrayer:
    def test_has_prayer_text(self):
        assert "prayer_text" in FALLBACK_PRAYER

    def test_has_tradition(self):
        assert "tradition" in FALLBACK_PRAYER

    def test_has_elements(self):
        assert "elements" in FALLBACK_PRAYER

    def test_has_spiritual_movement(self):
        assert "spiritual_movement" in FALLBACK_PRAYER

    def test_tradition_is_universal(self):
        assert FALLBACK_PRAYER["tradition"] == "universal"

    def test_spiritual_movement_is_peace(self):
        assert FALLBACK_PRAYER["spiritual_movement"] == "peace"

    def test_prayer_text_at_least_30_chars(self):
        assert len(FALLBACK_PRAYER["prayer_text"]) >= 30

    def test_elements_is_list(self):
        assert isinstance(FALLBACK_PRAYER["elements"], list)

    def test_elements_non_empty(self):
        assert len(FALLBACK_PRAYER["elements"]) >= 1

    def test_prayer_text_contains_amen(self):
        assert "Amen" in FALLBACK_PRAYER["prayer_text"]

    def test_fallback_is_dict(self):
        assert isinstance(FALLBACK_PRAYER, dict)


# ===========================================================================
# OratioAgent.VALID_TRADITIONS
# ===========================================================================


class TestValidTraditions:
    def test_is_frozenset(self):
        assert isinstance(OratioAgent.VALID_TRADITIONS, frozenset)

    def test_exactly_7_members(self):
        assert len(OratioAgent.VALID_TRADITIONS) == 7

    def test_matches_tradition_prompts_keys(self):
        assert set(TRADITION_PROMPTS.keys()) == OratioAgent.VALID_TRADITIONS

    def test_ignatian_valid(self):
        assert "ignatian" in OratioAgent.VALID_TRADITIONS

    def test_carmelite_valid(self):
        assert "carmelite" in OratioAgent.VALID_TRADITIONS

    def test_franciscan_valid(self):
        assert "franciscan" in OratioAgent.VALID_TRADITIONS

    def test_benedictine_valid(self):
        assert "benedictine" in OratioAgent.VALID_TRADITIONS

    def test_charismatic_valid(self):
        assert "charismatic" in OratioAgent.VALID_TRADITIONS

    def test_dominican_valid(self):
        assert "dominican" in OratioAgent.VALID_TRADITIONS

    def test_marian_valid(self):
        assert "marian" in OratioAgent.VALID_TRADITIONS

    def test_unknown_not_valid(self):
        assert "buddhist" not in OratioAgent.VALID_TRADITIONS

    def test_empty_string_not_valid(self):
        assert "" not in OratioAgent.VALID_TRADITIONS


# ===========================================================================
# OratioAgent._parse_json (static method)
# ===========================================================================


class TestParseJson:
    def test_valid_json_string(self):
        raw = '{"prayer_text": "Panie, bądź ze mną.", "tradition": "ignatian"}'
        result = OratioAgent._parse_json(raw)
        assert result["prayer_text"] == "Panie, bądź ze mną."
        assert result["tradition"] == "ignatian"

    def test_json_embedded_in_prose(self):
        raw = 'Oto modlitwa: {"prayer_text": "Amen.", "tradition": "carmelite"} koniec.'
        result = OratioAgent._parse_json(raw)
        assert result["prayer_text"] == "Amen."

    def test_json_in_markdown_fence(self):
        raw = '```json\n{"prayer_text": "Przez Chrystusa. Amen.", "tradition": "benedictine"}\n```'
        result = OratioAgent._parse_json(raw)
        assert result["prayer_text"] == "Przez Chrystusa. Amen."

    def test_full_valid_json_with_all_fields(self):
        data = {
            "prayer_text": "Wielki jesteś, Panie.",
            "tradition": "dominican",
            "elements": ["studium_veritatis", "contemplatio"],
            "spiritual_movement": "consolation",
        }
        result = OratioAgent._parse_json(json.dumps(data))
        assert result["elements"] == ["studium_veritatis", "contemplatio"]
        assert result["spiritual_movement"] == "consolation"

    def test_malformed_json_returns_fallback(self):
        result = OratioAgent._parse_json("{ prayer_text: broken json }")
        assert result["tradition"] == "universal"
        assert result["spiritual_movement"] == "peace"

    def test_empty_string_returns_fallback(self):
        result = OratioAgent._parse_json("")
        assert result["tradition"] == "universal"

    def test_no_braces_returns_fallback(self):
        result = OratioAgent._parse_json("Nie ma tutaj JSON-a.")
        assert result["spiritual_movement"] == "peace"

    def test_returns_dict(self):
        result = OratioAgent._parse_json('{"prayer_text": "Amen."}')
        assert isinstance(result, dict)

    def test_fallback_result_is_copy(self):
        result = OratioAgent._parse_json("bad json")
        result["tradition"] = "modified"
        assert FALLBACK_PRAYER["tradition"] == "universal"

    def test_nested_object_parsed(self):
        raw = '{"prayer_text": "Przez Maryję.", "tradition": "marian", "data": {"key": "val"}}'
        result = OratioAgent._parse_json(raw)
        assert result["data"]["key"] == "val"

    def test_unicode_preserved(self):
        raw = '{"prayer_text": "Bądź uwielbiony, Panie Boże.", "tradition": "franciscan"}'
        result = OratioAgent._parse_json(raw)
        assert "Bądź" in result["prayer_text"]

    def test_whitespace_only_returns_fallback(self):
        result = OratioAgent._parse_json("   \n\t  ")
        assert result["tradition"] == "universal"
