"""
ExegesisAgent (A-018) - Multi-dimensional biblical exegesis.

Performs exegesis along four complementary dimensions:
  1. Historical-Critical - Sitz im Leben, source/form/redaction criticism
  2. Literary            - Genre, structure, rhetorical devices, intertextuality
  3. Theological         - Christology, soteriology, ecclesiology, etc.
  4. Canonical           - Typology, salvation history, unity of revelation

Uses ChatOpenAI for LLM-based analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompts for each exegetical dimension
# ---------------------------------------------------------------------------

_DIMENSION_PROMPTS: dict[str, str] = {
    "historical_critical": (
        "You are a biblical scholar specialising in historical-critical exegesis. "
        "Analyse the passage considering its historical context, Sitz im Leben, "
        "authorship, dating, source criticism, form criticism, and redaction "
        "criticism. Ground your analysis in the original languages (Hebrew/Greek) "
        "where relevant. Cite scholarly consensus and notable dissenting views. "
        "Respond with a thorough scholarly analysis grounded in the Catholic "
        "exegetical tradition."
    ),
    "literary": (
        "You are a biblical scholar specialising in literary analysis of Scripture. "
        "Analyse the passage for genre, structure, rhetorical devices, chiasm, "
        "inclusio, parallelism, metaphor, narrative arc, characterisation, and "
        "intertextual echoes. Identify the literary function within the broader "
        "book and biblical corpus."
    ),
    "theological": (
        "You are a Catholic biblical theologian. Analyse the passage for its "
        "theological content: Christology, soteriology, ecclesiology, "
        "pneumatology, eschatology, and moral theology as applicable. "
        "Ground your analysis in the Catholic theological tradition and the "
        "Pontifical Biblical Commission's guidelines."
    ),
    "canonical": (
        "You are a biblical scholar specialising in canonical criticism. "
        "Analyse how this passage functions within the full canon of Scripture. "
        "Identify typological connections between Old and New Testaments, "
        "how the passage relates to salvation history, and its place in the "
        "unity of divine revelation as understood by the Catholic Church."
    ),
}


class ExegesisAgent:
    """
    A-018: Multi-dimensional biblical exegesis agent.

    Analyses scripture passages along four complementary dimensions using
    LLM-based analysis with ChatOpenAI.
    """

    AGENT_ID = "A-018"
    AGENT_NAME = "ExegesisAgent"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> None:
        """
        Args:
            model: OpenAI model identifier.
            temperature: Sampling temperature for the LLM.
            max_tokens: Maximum tokens per dimension analysis.
        """
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        book: str,
        chapter: int,
        verse_start: int,
        verse_end: int,
        text: str,
    ) -> dict[str, str]:
        """
        Perform full multi-dimensional exegesis of a scripture passage.

        Args:
            book: Book name (e.g. "Genesis", "John").
            chapter: Chapter number.
            verse_start: Starting verse.
            verse_end: Ending verse (inclusive).
            text: The scripture text to analyse.

        Returns:
            Dict with four keys - *historical_critical*, *literary*,
            *theological*, *canonical* - each mapping to a string analysis.
        """
        reference = self._format_reference(book, chapter, verse_start, verse_end)
        logger.info("[%s] Beginning exegesis of %s", self.AGENT_ID, reference)

        tasks = {
            dimension: self._analyze_dimension(
                dimension=dimension,
                reference=reference,
                text=text,
            )
            for dimension in _DIMENSION_PROMPTS
        }

        results: dict[str, str] = {}
        gathered = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        for dimension, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                logger.error(
                    "[%s] Dimension '%s' failed: %s",
                    self.AGENT_ID,
                    dimension,
                    result,
                )
                results[dimension] = (
                    f"Analysis unavailable for the {dimension} dimension."
                )
            else:
                results[dimension] = result

        logger.info("[%s] Exegesis complete for %s", self.AGENT_ID, reference)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _analyze_dimension(
        self,
        *,
        dimension: str,
        reference: str,
        text: str,
    ) -> str:
        """Analyse a single exegetical dimension via LLM."""
        system_prompt = _DIMENSION_PROMPTS[dimension]
        user_prompt = (
            f"Please provide a {dimension.replace('_', '-')} analysis "
            f"of {reference}.\n\n"
            f'Passage text:\n"{text}"\n\n'
            "Provide a thorough, scholarly analysis grounded in the Catholic "
            "exegetical tradition. Cite sources where possible."
        )

        response = await self._llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return response.content

    @staticmethod
    def _format_reference(
        book: str,
        chapter: int,
        verse_start: int,
        verse_end: int,
    ) -> str:
        """Build a human-readable scripture reference string."""
        if verse_end != verse_start:
            return f"{book} {chapter}:{verse_start}-{verse_end}"
        return f"{book} {chapter}:{verse_start}"
