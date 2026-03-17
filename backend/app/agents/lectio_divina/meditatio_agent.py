"""
Meditatio Agent (A-011)
=======================
Generates personalised reflective questions and multi-layered meditation
from the selected scripture passage, enriched with:

  - Full Quadriga (4 senses of Scripture per Catholic tradition)
  - Patristic cross-references (Fathers of the Church)
  - Kerygmatic lens (salvation history context)
  - Personal existential application
  - Original language insights (Hebrew/Greek key words)

"Maria autem conservabat omnia verba haec, conferens in corde suo." — Lk 2:19
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_primary

logger = logging.getLogger("sancta_nexus.meditatio_agent")

# ---------------------------------------------------------------------------
# System prompt — enriched with patristic and kerygmatic depth
# ---------------------------------------------------------------------------

MEDITATIO_SYSTEM_PROMPT = """\
Jestes mistrzem medytacji chrzescijanskiej w tradycji Lectio Divina, \
uformowanym w pelnej katolickiej tradycji egzegetycznej, patrystycznej \
i kontemplacyjnej. Twoja refleksja czerpie z 2000 lat madrosci Kosciola.

═══════════════════════════════════════════════════════════
FRAGMENT PISMA SWIETEGO
═══════════════════════════════════════════════════════════

Ksiega: {book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}
Kontekst historyczny: {historical_context}
{patristic_context}
{original_language_context}

═══════════════════════════════════════════════════════════
KONTEKST UZYTKOWNIKA
═══════════════════════════════════════════════════════════

Stan emocjonalny: {user_context}
Temat kerygmatyczny sesji: {kerygmatic_theme}

═══════════════════════════════════════════════════════════
PELNA ANALIZA QUADRIGA (4 sensy Pisma Swietego)
═══════════════════════════════════════════════════════════

Zastosuj kompletna analize wedlug tradycji katolickiej (CCC 115-119):

"Littera gesta docet, quid credas allegoria,
 moralis quid agas, quo tendas anagogia."

SENSUS LITERALIS (warstwa historyczno-literalna):
- Co tekst MOWI w swoim oryginalnym kontekscie historycznym?
- Jakie sa kluczowe slowa w oryginale (hebr./gr.) i ich znaczenie?
- Jaki gatunek literacki (narracja, poezja, proroctwo, madrosciowy, epistola)?
- Jaki jest Sitz im Leben — kontekst zyciowy autora i odbiorcow?
- Odwolaj sie do konkretnego Ojca Kosciola, ktory kommentowal ten fragment.

SENSUS ALLEGORICUS (warstwa typologiczno-chrystologiczna):
- Jak ten tekst wskazuje na Chrystusa i misterium zbawienia?
- Jakie typy i figury (typologia biblijna) sa tu obecne?
- Jak ten fragment laczy sie z Nowym Testamentem (lub odwrotnie)?
- Jak odnosza sie do niego Ojcowie Kosciola (patrystyka)?

SENSUS MORALIS (warstwa egzystencjalno-etyczna):
- Co to znaczy dla MOJEGO obecnego zycia?
- Jakie cnoty lub wady tekst odsłania?
- Do jakiej przemiany serca (metanoia) zaprasza?
- Jak ten fragment kształtuje moje sumienie?

SENSUS ANAGOGICUS (warstwa mistyczno-eschatologiczna):
- Jak ten tekst prowadzi ku kontemplacji i zjednoczeniu z Bogiem?
- Jakie otwiera przestrzenie modlitwy i mistyki?
- Jak wskazuje na rzeczywistosc eschatologiczna (niebo, pelnia)?
- Jakie echo tego tekstu slychac w liturgii?

═══════════════════════════════════════════════════════════
PYTANIA REFLEKSYJNE
═══════════════════════════════════════════════════════════

Wygeneruj 3-4 pytania refleksyjne, kazde z innej warstwy:
- Pytania osobiste (w drugiej osobie — "ty")
- Pytania otwarte (nie "tak/nie")
- Pytania prowokujace gleboka refleksje, nie powierzchowne
- Przynajmniej jedno pytanie odwolujace sie do konkretnej frazy z tekstu
- Przynajmniej jedno pytanie lacze fragment z codziennym doswiadczeniem

Odpowiedz WYLACZNIE w formacie JSON:
{{
  "questions": [
    {{
      "text": "Pytanie refleksyjne",
      "layer": "literalis|allegoricus|moralis|anagogicus",
      "scripture_echo": "Fraza z tekstu, do ktorej pytanie sie odnosi"
    }}
  ],
  "reflection_layers": {{
    "literalis": "Refleksja historyczno-literalna z odwolaniem patrystycznym",
    "allegoricus": "Refleksja typologiczno-chrystologiczna",
    "moralis": "Refleksja egzystencjalno-etyczna",
    "anagogicus": "Refleksja mistyczno-eschatologiczna"
  }},
  "patristic_insight": "Krotki cytat lub mysl jednego z Ojcow Kosciola",
  "key_word": "Jedno kluczowe slowo z tekstu, ktore jest bramą do medytacji"
}}
"""

# ---------------------------------------------------------------------------
# Fallback — enriched with patristic depth
# ---------------------------------------------------------------------------

FALLBACK_MEDITATION: dict[str, Any] = {
    "questions": [
        {
            "text": "Ktore slowo z tego fragmentu najbardziej przyciaga twoja uwage i dlaczego?",
            "layer": "literalis",
            "scripture_echo": "",
        },
        {
            "text": "W jaki sposob ten tekst ukazuje Boza milosc do ciebie osobiscie?",
            "layer": "allegoricus",
            "scripture_echo": "",
        },
        {
            "text": "Do jakiej konkretnej zmiany w twoim zyciu zaprasza cie dziś ten fragment?",
            "layer": "moralis",
            "scripture_echo": "",
        },
        {
            "text": "Gdybys mogl/mogla usiasc w ciszy z tym jednym slowem, co uslyszalbys/uslyszalabys?",
            "layer": "anagogicus",
            "scripture_echo": "",
        },
    ],
    "reflection_layers": {
        "literalis": (
            "Ten fragment zostal napisany w konkretnym kontekscie historycznym. "
            "Sw. Hieronim uczy nas, ze 'nieznajomość Pisma Swietego jest nieznajomoscia "
            "Chrystusa'. Zatrzymaj sie nad oryginalnym znaczeniem tych slow — co autor "
            "natchniony chcial przekazac swoim pierwszym czytelnikom?"
        ),
        "allegoricus": (
            "Tradycja Kosciola odczytuje kazdy fragment Pisma w swietle Chrystusa. "
            "Sw. Augustyn pisal: 'Nowy Testament jest ukryty w Starym, a Stary jest "
            "objawiony w Nowym.' Jak ten tekst prowadzi cie ku spotkaniu z Chrystusem?"
        ),
        "moralis": (
            "Pomysl, w jaki sposob te slowa odnosza sie do tego, co teraz przezywasz. "
            "Sw. Grzegorz Wielki mawiał: 'Pismo Swiete rosnie z tym, kto je czyta.' "
            "Jakie wezwanie slyszysz w tych slowach dzis?"
        ),
        "anagogicus": (
            "Pozwol, by cisza wypelnila twoje serce. Bog moze mowic przez jedno slowo, "
            "ktore cie poruszylo. Sw. Jan od Krzyza uczy: 'Jedno slowo wyrzekl Ojciec, "
            "ktorym jest Jego Syn, i to Slowo wypowiada nieustannie w wiecznym milczeniu; "
            "w milczeniu tez dusza powinna je sluchac.'"
        ),
    },
    "patristic_insight": (
        "Sw. Grzegorz Wielki: 'Pismo Swiete jest listem Boga Wszechmogacego "
        "do swego stworzenia. Czytaj je jak list milosny.'"
    ),
    "key_word": "slowo",
}


class MeditatioAgent:
    """
    A-011 — Meditation / reflection agent.

    Produces personalised reflective questions and multi-layered scriptural
    analysis using the full Quadriga, enriched with patristic wisdom,
    original language insights, and kerygmatic context.
    """

    def __init__(self) -> None:
        try:
            self._llm = get_llm_primary(temperature=0.7, max_tokens=3072)
            logger.info("MeditatioAgent (A-011) initialised.")
        except Exception as exc:
            logger.warning("MeditatioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    async def meditate(
        self,
        scripture: dict,
        user_context: dict | None = None,
        kerygmatic_theme: str = "",
    ) -> dict:
        """Generate reflective questions and multi-layered meditation."""
        if self._llm is None:
            return dict(FALLBACK_MEDITATION)

        system_prompt = MEDITATIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
            historical_context=scripture.get("historical_context", "brak kontekstu"),
            patristic_context=(
                f"Refleksja patrystyczna: {scripture['patristic_note']}"
                if scripture.get("patristic_note") else ""
            ),
            original_language_context=(
                f"Slowo kluczowe: {scripture['original_language_key']}"
                if scripture.get("original_language_key") else ""
            ),
            user_context=json.dumps(user_context or {}, ensure_ascii=False),
            kerygmatic_theme=kerygmatic_theme or "mysterium_paschale",
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Wygeneruj gleboka medytacje wielowarstwowa w tradycji Quadriga."),
            ])
            meditation = self._parse_json(response.content)

            # Validate questions
            questions = meditation.get("questions", [])
            if not isinstance(questions, list) or len(questions) < 2:
                logger.warning("Too few questions generated; using fallback.")
                return dict(FALLBACK_MEDITATION)

            # Normalize questions format
            normalized_questions = []
            for q in questions:
                if isinstance(q, str):
                    normalized_questions.append({
                        "text": q, "layer": "moralis", "scripture_echo": ""
                    })
                elif isinstance(q, dict) and q.get("text"):
                    normalized_questions.append(q)
            meditation["questions"] = normalized_questions or FALLBACK_MEDITATION["questions"]

            # Validate reflection_layers with both naming conventions
            layers = meditation.get("reflection_layers", {})
            required_layers = ("literalis", "allegoricus", "moralis", "anagogicus")
            # Also accept old naming
            layer_aliases = {
                "exegetical": "literalis", "existential": "moralis",
                "mystical": "anagogicus", "practical": "allegoricus",
            }
            for old_key, new_key in layer_aliases.items():
                if old_key in layers and new_key not in layers:
                    layers[new_key] = layers.pop(old_key)

            fallback_layers = FALLBACK_MEDITATION["reflection_layers"]
            for layer in required_layers:
                layers.setdefault(layer, fallback_layers[layer])
            meditation["reflection_layers"] = layers

            # Ensure patristic insight
            meditation.setdefault("patristic_insight", FALLBACK_MEDITATION["patristic_insight"])
            meditation.setdefault("key_word", FALLBACK_MEDITATION["key_word"])

            # Backward compatibility: also provide old keys
            meditation["exegetical"] = layers.get("literalis", "")
            meditation["existential"] = layers.get("moralis", "")
            meditation["mystical"] = layers.get("anagogicus", "")
            meditation["practical"] = layers.get("allegoricus", "")

            logger.info(
                "Meditation generated: %d questions, all 4 layers present, patristic enriched.",
                len(meditation["questions"]),
            )
            return meditation

        except Exception as exc:
            logger.error("Meditation generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_MEDITATION)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse meditation JSON: %s", exc)
            return dict(FALLBACK_MEDITATION)
