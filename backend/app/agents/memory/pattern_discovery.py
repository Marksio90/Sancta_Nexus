"""PatternDiscoveryAgent (A-037) — Odkrywanie wzorów w życiu duchowym.

Discovers recurring themes, cyclical crises, grace moments, and other patterns
in the user's spiritual life using temporal analysis.
"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

PATTERN_TYPES = [
    "recurring_theme",      # Powtarzający się temat (np. zaufanie, miłosierdzie)
    "cyclical_crisis",      # Cykliczny kryzys (np. oschłość co 3 miesiące)
    "grace_moment",         # Momenty łaski i przełomów
    "growth_trajectory",    # Trajektoria wzrostu duchowego
    "scripture_affinity",   # Powtarzające się fragmenty biblijne
    "emotional_pattern",    # Wzory emocjonalne w czasie
]


class PatternDiscoveryAgent:
    """Discovers spiritual patterns through temporal analysis."""

    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.3)

    async def discover(
        self, user_id: str, sessions: list[dict] | None = None
    ) -> list[dict]:
        """Discover patterns from session history."""
        if not sessions:
            return self._default_patterns()

        try:
            sessions_summary = "\n".join(
                f"- Data: {s.get('date', 'N/A')}, Emocja: {s.get('primary_emotion', 'N/A')}, "
                f"Stan: {s.get('spiritual_state', 'N/A')}, "
                f"Fragment: {s.get('scripture_ref', 'N/A')}"
                for s in sessions[-30:]  # Last 30 sessions
            )

            response = await self.llm.ainvoke([
                SystemMessage(content=(
                    "Jesteś analitykiem życia duchowego. Na podstawie historii sesji "
                    "modlitewnych odkryj wzory i tendencje. Dla każdego wzoru podaj:\n"
                    "- Typ: recurring_theme, cyclical_crisis, grace_moment, "
                    "growth_trajectory, scripture_affinity, emotional_pattern\n"
                    "- Opis wzoru\n"
                    "- Częstotliwość występowania\n"
                    "- Powiązane fragmenty biblijne\n\n"
                    "Format każdego wzoru:\n"
                    "PATTERN: [typ]\nDESC: [opis]\nFREQ: [częstotliwość]\nSCRIPTURE: [fragmenty]"
                )),
                HumanMessage(content=f"Historia sesji użytkownika {user_id}:\n{sessions_summary}"),
            ])

            patterns = self._parse_patterns(response.content)
            return patterns if patterns else self._default_patterns()

        except Exception as e:
            logger.error(f"Pattern discovery error: {e}")
            return self._default_patterns()

    def _parse_patterns(self, text: str) -> list[dict]:
        patterns = []
        current = {}

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("PATTERN:"):
                if current:
                    patterns.append(current)
                current = {"type": line.split(":", 1)[1].strip()}
            elif line.startswith("DESC:") and current:
                current["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("FREQ:") and current:
                current["frequency"] = line.split(":", 1)[1].strip()
            elif line.startswith("SCRIPTURE:") and current:
                current["related_scriptures"] = [
                    s.strip() for s in line.split(":", 1)[1].split(",")
                ]

        if current:
            patterns.append(current)
        return patterns

    def _default_patterns(self) -> list[dict]:
        return [
            {
                "type": "growth_trajectory",
                "description": "Początek drogi duchowej — budowanie regularności modlitwy",
                "frequency": "ciągły",
                "related_scriptures": ["Ps 1,1-3", "Mt 7,24-27"],
            },
        ]
