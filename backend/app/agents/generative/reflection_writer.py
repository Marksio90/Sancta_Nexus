"""
ReflectionWriterAgent (A-029)
Creates multi-layered spiritual reflections on Scripture passages,
combining exegetical, existential, mystical, and practical dimensions.
Uses RAG to enrich reflections with patristic and theological sources.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ReflectionLayer(str, Enum):
    """The four interpretive layers of a spiritual reflection."""

    EXEGETICAL = "exegetical"  # Historical-critical, literary context
    EXISTENTIAL = "existential"  # Personal meaning, life application
    MYSTICAL = "mystical"  # Contemplative, union with God
    PRACTICAL = "practical"  # Concrete action, daily life


@dataclass
class ScripturePassage:
    """A Scripture passage to reflect upon."""

    reference: str  # e.g. "J 15,1-8"
    text: str
    book: str
    chapter: int
    verses: str
    liturgical_context: Optional[str] = None  # e.g. "V Niedziela Wielkanocna"
    original_language_notes: Optional[str] = None


@dataclass
class UserContext:
    """Context about the user requesting the reflection."""

    user_id: str
    spiritual_stage: Optional[str] = None  # purgation / illumination / union
    current_struggles: Optional[list[str]] = None
    prayer_tradition: Optional[str] = None
    theological_depth: str = "intermediate"  # beginner / intermediate / advanced
    preferred_language: str = "pl"


@dataclass
class ReflectionLayerContent:
    """Content for a single interpretive layer."""

    layer: ReflectionLayer
    title: str
    content: str
    sources: list[str] = field(default_factory=list)
    key_insight: str = ""


@dataclass
class Reflection:
    """Complete multi-layered reflection on a Scripture passage."""

    passage: ScripturePassage
    layers: list[ReflectionLayerContent]
    synthesis: str
    prayer_response: str
    action_step: str
    patristic_quotes: list[dict[str, str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


REFLECTION_SYSTEM_PROMPT = (
    "Jesteś teologiem i mistykiem tworzącym wielowarstwowe rozważania Pisma Świętego. "
    "Każde rozważanie powinno łączyć cztery perspektywy:\n\n"
    "1. EGZEGETYCZNA: Analiza tekstu w kontekście historycznym, literackim i teologicznym. "
    "Uwzględnij oryginalne języki (hebrajski/grecki), gatunek literacki, Sitz im Leben, "
    "paralele biblijne i kontekst kanoniczny.\n\n"
    "2. EGZYSTENCJALNA: Osobiste znaczenie tekstu dla człowieka współczesnego. "
    "Jak ten tekst przemawia do ludzkiego doświadczenia: cierpienia, radości, "
    "poszukiwania sensu, relacji z innymi?\n\n"
    "3. MISTYCZNA: Wymiar kontemplacyjny i zjednoczeniowy. "
    "Jak ten tekst prowadzi do doświadczenia Boga? Jakie otwiera przestrzenie "
    "modlitwy kontemplacyjnej? Odwołuj się do mistyków: Jana od Krzyża, "
    "Teresy z Avili, Mistrza Eckharta, Grzegorza z Nyssy.\n\n"
    "4. PRAKTYCZNA: Konkretne zastosowanie w życiu codziennym. "
    "Jakie postanowienie, zmianę postawy, gest miłosierdzia ten tekst inspiruje?\n\n"
    "Wzbogacaj rozważanie cytatami Ojców Kościoła i wielkich teologów. "
    "Pisz w języku polskim, z głębią teologiczną dostosowaną do poziomu odbiorcy."
)

RAG_QUERY_TEMPLATE = (
    "Znajdź komentarze patrystyczne i teologiczne do fragmentu: {reference}. "
    "Szukaj w dziełach: Ojców Kościoła, Doktorów Kościoła, dokumentach Magisterium, "
    "komentarzach biblijnych. Priorytet: Augustyn, Tomasz z Akwinu, Jan Chryzostom, "
    "Orygenes, Grzegorz Wielki, Henri de Lubac, Hans Urs von Balthasar."
)


class ReflectionWriterAgent:
    """
    Agent A-029: Creates multi-layered Scripture reflections.

    Combines four interpretive layers (exegetical, existential, mystical,
    practical) enriched by patristic and theological sources retrieved
    through RAG.
    """

    agent_id: str = "A-029"
    agent_name: str = "ReflectionWriterAgent"

    def __init__(self, llm_client=None, vector_store=None):
        """
        Args:
            llm_client: Async LLM client with ``chat(messages, **kwargs)`` method.
            vector_store: Vector store client for RAG retrieval with
                         ``search(query, collection, limit)`` method.
        """
        self._llm = llm_client
        self._vector_store = vector_store

    async def write(
        self, passage: ScripturePassage, user_context: UserContext
    ) -> Reflection:
        """
        Create a full multi-layered reflection on a Scripture passage.

        Args:
            passage: The Scripture passage to reflect upon.
            user_context: Context about the user.

        Returns:
            A ``Reflection`` containing all four layers, synthesis, and action.
        """
        logger.info(
            "Writing reflection for %s (user=%s, depth=%s)",
            passage.reference,
            user_context.user_id,
            user_context.theological_depth,
        )

        # Retrieve patristic and theological sources via RAG
        rag_context = await self._retrieve_sources(passage)

        # Generate each layer
        layers: list[ReflectionLayerContent] = []
        for layer in ReflectionLayer:
            layer_content = await self._generate_layer(
                passage, user_context, layer, rag_context
            )
            layers.append(layer_content)

        # Generate synthesis and action
        synthesis = await self._generate_synthesis(passage, layers, user_context)
        prayer_response = await self._generate_prayer_response(passage, layers)
        action_step = await self._generate_action_step(passage, layers, user_context)

        return Reflection(
            passage=passage,
            layers=layers,
            synthesis=synthesis,
            prayer_response=prayer_response,
            action_step=action_step,
            patristic_quotes=rag_context.get("quotes", []),
            metadata={
                "agent_id": self.agent_id,
                "user_id": user_context.user_id,
                "theological_depth": user_context.theological_depth,
                "sources_retrieved": len(rag_context.get("documents", [])),
            },
        )

    async def _retrieve_sources(self, passage: ScripturePassage) -> dict:
        """Retrieve patristic and theological sources from the vector store."""
        if not self._vector_store:
            logger.warning("No vector store configured; skipping RAG retrieval.")
            return {"documents": [], "quotes": []}

        query = RAG_QUERY_TEMPLATE.format(reference=passage.reference)

        try:
            results = await self._vector_store.search(
                query=query,
                collection="patristic_theology",
                limit=10,
            )
            documents = results if results else []
            quotes = [
                {"author": doc.get("author", ""), "text": doc.get("text", "")}
                for doc in documents
                if doc.get("author")
            ]
            return {"documents": documents, "quotes": quotes}
        except Exception:
            logger.exception("RAG retrieval failed for %s", passage.reference)
            return {"documents": [], "quotes": []}

    async def _generate_layer(
        self,
        passage: ScripturePassage,
        user_context: UserContext,
        layer: ReflectionLayer,
        rag_context: dict,
    ) -> ReflectionLayerContent:
        """Generate content for a single reflection layer."""
        layer_instructions = {
            ReflectionLayer.EXEGETICAL: (
                "Przygotuj analizę egzegetyczną tego fragmentu. "
                "Uwzględnij kontekst historyczny, literacki, znaczenie kluczowych słów "
                "w języku oryginalnym, paralele biblijne i miejsce w kanonie."
            ),
            ReflectionLayer.EXISTENTIAL: (
                "Napisz rozważanie egzystencjalne tego fragmentu. "
                "Jak ten tekst odnosi się do ludzkiego doświadczenia? "
                "Jakie pytania stawia? Jakie odsłania prawdy o kondycji ludzkiej?"
            ),
            ReflectionLayer.MYSTICAL: (
                "Napisz rozważanie mistyczne tego fragmentu. "
                "Jak ten tekst otwiera na doświadczenie kontemplacyjne? "
                "Jakie przestrzenie modlitwy ukazuje? "
                "Odwołaj się do tradycji mistycznej Kościoła."
            ),
            ReflectionLayer.PRACTICAL: (
                "Napisz rozważanie praktyczne tego fragmentu. "
                "Jakie konkretne zastosowanie w życiu codziennym proponujesz? "
                "Jaki gest miłosierdzia, zmianę postawy, nowy nawyk duchowy?"
            ),
        }

        rag_text = ""
        if rag_context.get("documents"):
            source_snippets = [
                doc.get("text", "")[:300] for doc in rag_context["documents"][:5]
            ]
            rag_text = (
                "\n\nŹródła patrystyczne i teologiczne do wykorzystania:\n"
                + "\n---\n".join(source_snippets)
            )

        depth_instruction = {
            "beginner": "Pisz prostym, przystępnym językiem. Unikaj specjalistycznej terminologii.",
            "intermediate": "Używaj terminologii teologicznej z objaśnieniami kluczowych pojęć.",
            "advanced": "Pisz z pełną głębią teologiczną, swobodnie używając terminologii fachowej.",
        }

        messages = [
            {"role": "system", "content": REFLECTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Fragment: {passage.reference}\n"
                    f'Tekst: "{passage.text}"\n\n'
                    f"Zadanie: {layer_instructions[layer]}\n\n"
                    f"Poziom: {depth_instruction.get(user_context.theological_depth, '')}\n"
                    f"{rag_text}"
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.7, max_tokens=2048)

        layer_titles = {
            ReflectionLayer.EXEGETICAL: "Analiza egzegetyczna",
            ReflectionLayer.EXISTENTIAL: "Rozważanie egzystencjalne",
            ReflectionLayer.MYSTICAL: "Rozważanie mistyczne",
            ReflectionLayer.PRACTICAL: "Zastosowanie praktyczne",
        }

        return ReflectionLayerContent(
            layer=layer,
            title=layer_titles[layer],
            content=response.content,
            sources=[
                doc.get("source", "") for doc in rag_context.get("documents", [])[:3]
            ],
            key_insight="",
        )

    async def _generate_synthesis(
        self,
        passage: ScripturePassage,
        layers: list[ReflectionLayerContent],
        user_context: UserContext,
    ) -> str:
        """Generate a synthesis integrating all four layers."""
        layer_summaries = "\n\n".join(
            f"**{lc.title}**:\n{lc.content[:500]}" for lc in layers
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Jesteś teologiem tworzącym syntezę wielowarstwowego rozważania. "
                    "Połącz cztery perspektywy w spójne, głębokie podsumowanie."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Fragment: {passage.reference}\n\n"
                    f"Warstwy rozważania:\n{layer_summaries}\n\n"
                    "Napisz syntezę łączącą te cztery perspektywy w jedno "
                    "spójne przesłanie duchowe."
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.6, max_tokens=1024)
        return response.content

    async def _generate_prayer_response(
        self, passage: ScripturePassage, layers: list[ReflectionLayerContent]
    ) -> str:
        """Generate a prayer response arising from the reflection."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Na podstawie rozważania Pisma Świętego, napisz krótką, "
                    "osobistą modlitwę będącą odpowiedzią serca na usłyszane Słowo. "
                    "Modlitwa powinna być w języku polskim, osobista i szczera."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Fragment: {passage.reference}\n"
                    f'Tekst: "{passage.text}"\n\n'
                    "Napisz modlitwę-odpowiedź na to Słowo."
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.8, max_tokens=512)
        return response.content

    async def _generate_action_step(
        self,
        passage: ScripturePassage,
        layers: list[ReflectionLayerContent],
        user_context: UserContext,
    ) -> str:
        """Generate a concrete action step inspired by the reflection."""
        practical = next(
            (lc for lc in layers if lc.layer == ReflectionLayer.PRACTICAL), None
        )
        practical_text = practical.content[:500] if practical else ""

        messages = [
            {
                "role": "system",
                "content": (
                    "Na podstawie rozważania, zaproponuj jedno konkretne, "
                    "wykonalne postanowienie na dziś. Powinno być proste, "
                    "mierzalne i wynikające wprost z tekstu biblijnego."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Fragment: {passage.reference}\n"
                    f"Rozważanie praktyczne: {practical_text}\n\n"
                    "Zaproponuj jedno konkretne postanowienie na dziś."
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.6, max_tokens=256)
        return response.content
