"""
HermeneuticsAgent (A-019) - Quadriga Engine.

Implements the four senses of Scripture (Quadriga) as defined by the
Catholic exegetical tradition:
  1. Literal (Peshat)    - What the text says historically and grammatically.
  2. Allegorical (Remez) - What the text signifies about Christ and the Church.
  3. Moral (Derash)      - What the text teaches about how to live.
  4. Anagogical (Sod)    - What the text reveals about eschatological realities.

Each sense is computed by a dedicated async method backed by ChatOpenAI.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Specialised system prompts per sense
# ---------------------------------------------------------------------------

_SENSE_PROMPTS: dict[str, str] = {
    "literal": (
        "You are a Catholic biblical scholar specialising in the LITERAL sense "
        "(sensus literalis / peshat) of Scripture. Determine what the sacred "
        "author intended to communicate to the original audience. Consider:\n"
        "- Grammatical and syntactical meaning of the text\n"
        "- Historical context and Sitz im Leben\n"
        "- Literary genre and conventions\n"
        "- Key terms in the original language (Hebrew/Greek)\n"
        "- Immediate literary context within the book\n\n"
        "As the Catechism teaches (CCC 116): 'The literal sense is the meaning "
        "conveyed by the words of Scripture and discovered by exegesis, following "
        "the rules of sound interpretation.'"
    ),
    "allegorical": (
        "You are a Catholic biblical theologian specialising in the ALLEGORICAL "
        "sense (sensus allegoricus / remez) of Scripture. Discern how the text "
        "points to Christ, the Church, and the mysteries of faith. Consider:\n"
        "- Typological connections between Old and New Testaments\n"
        "- How figures, events, and institutions prefigure Christ\n"
        "- Christological and ecclesiological significance\n"
        "- Sacramental symbolism\n"
        "- The unity of God's plan of salvation\n\n"
        "As the Catechism teaches (CCC 117): 'We can acquire a more profound "
        "understanding of events by recognising their significance in Christ; "
        "thus the crossing of the Red Sea is a sign of Christ's victory and "
        "also of Christian Baptism.'"
    ),
    "moral": (
        "You are a Catholic moral theologian specialising in the MORAL sense "
        "(sensus moralis / derash) of Scripture. Draw out the ethical and "
        "practical implications for Christian living. Consider:\n"
        "- What virtues the text commends or vices it warns against\n"
        "- How the text informs the formation of conscience\n"
        "- Relation to the Beatitudes and the Decalogue\n"
        "- Practical guidance for daily life\n\n"
        "As the Catechism teaches (CCC 117): 'The moral sense. The events "
        "reported in Scripture ought to lead us to act justly. As St. Paul says, "
        "they were written for our instruction.'"
    ),
    "anagogical": (
        "You are a Catholic theologian specialising in the ANAGOGICAL sense "
        "(sensus anagogicus / sod) of Scripture. Illuminate how the text points "
        "toward eschatological realities and the heavenly homeland. Consider:\n"
        "- Truths about the Last Things (death, judgement, heaven, hell)\n"
        "- The eschatological dimension of salvation history\n"
        "- How earthly realities signify heavenly ones\n"
        "- The already-and-not-yet tension of the Kingdom\n"
        "- The beatific vision and eternal life\n\n"
        "As the Catechism teaches (CCC 117): 'The anagogical sense. We can view "
        "realities and events in terms of their eternal significance, leading us "
        "toward our true homeland: thus the Church on earth is a sign of the "
        "heavenly Jerusalem.'"
    ),
}


class HermeneuticsAgent:
    """
    A-019: Quadriga Engine - Four senses of Scripture interpreter.

    Applies the traditional Catholic fourfold method of scriptural
    interpretation, producing a multi-layered reading of any given passage.
    """

    AGENT_ID = "A-019"
    AGENT_NAME = "HermeneuticsAgent (Quadriga Engine)"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> None:
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def interpret(
        self,
        book: str,
        chapter: int,
        verse_start: int,
        verse_end: int,
        text: str,
    ) -> dict[str, str]:
        """
        Produce a complete Quadriga interpretation of a scripture passage.

        All four senses are computed concurrently for efficiency.

        Args:
            book: Book name (e.g. "Genesis", "John").
            chapter: Chapter number.
            verse_start: Starting verse.
            verse_end: Ending verse (inclusive).
            text: The scripture text to interpret.

        Returns:
            Dict with keys *literal*, *allegorical*, *moral*, *anagogical*,
            each mapping to a string interpretation.
        """
        reference = self._format_reference(book, chapter, verse_start, verse_end)
        logger.info(
            "[%s] Starting Quadriga interpretation of %s",
            self.AGENT_ID,
            reference,
        )

        literal, allegorical, moral, anagogical = await asyncio.gather(
            self._interpret_literal(reference, text),
            self._interpret_allegorical(reference, text),
            self._interpret_moral(reference, text),
            self._interpret_anagogical(reference, text),
        )

        logger.info(
            "[%s] Quadriga interpretation complete for %s",
            self.AGENT_ID,
            reference,
        )

        return {
            "literal": literal,
            "allegorical": allegorical,
            "moral": moral,
            "anagogical": anagogical,
        }

    # ------------------------------------------------------------------
    # Per-sense methods
    # ------------------------------------------------------------------

    async def _interpret_literal(self, reference: str, text: str) -> str:
        """Interpret the literal (peshat) sense."""
        return await self._interpret_sense("literal", reference, text)

    async def _interpret_allegorical(self, reference: str, text: str) -> str:
        """Interpret the allegorical (remez) sense."""
        return await self._interpret_sense("allegorical", reference, text)

    async def _interpret_moral(self, reference: str, text: str) -> str:
        """Interpret the moral (derash) sense."""
        return await self._interpret_sense("moral", reference, text)

    async def _interpret_anagogical(self, reference: str, text: str) -> str:
        """Interpret the anagogical (sod) sense."""
        return await self._interpret_sense("anagogical", reference, text)

    # ------------------------------------------------------------------
    # Shared interpretation logic
    # ------------------------------------------------------------------

    async def _interpret_sense(
        self,
        sense: str,
        reference: str,
        text: str,
    ) -> str:
        """Run LLM interpretation for a single sense of Scripture."""
        system_prompt = _SENSE_PROMPTS[sense]
        user_prompt = (
            f"Please provide the {sense} interpretation of {reference}.\n\n"
            f'Text:\n"{text}"\n\n'
            "Structure your response as follows:\n"
            "1. Main interpretation\n"
            "2. Key themes (3-5 most important themes)\n"
            "3. Supporting patristic or magisterial references where applicable\n\n"
            "Write in a scholarly yet accessible style faithful to Catholic tradition."
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            return response.content
        except Exception:
            logger.exception(
                "[%s] LLM call failed for %s sense of %s",
                self.AGENT_ID,
                sense,
                reference,
            )
            return f"Interpretation unavailable for the {sense} sense."

    @staticmethod
    def _format_reference(
        book: str,
        chapter: int,
        verse_start: int,
        verse_end: int,
    ) -> str:
        if verse_end != verse_start:
            return f"{book} {chapter}:{verse_start}-{verse_end}"
        return f"{book} {chapter}:{verse_start}"
