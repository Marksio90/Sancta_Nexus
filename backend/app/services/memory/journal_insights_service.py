"""JournalInsightsService — analizuje historię dziennika duchowego.

Łączy JourneyTrackerAgent (A-036) i PatternDiscoveryAgent (A-037),
aby dać użytkownikowi wgląd w jego drogę duchową na podstawie wpisów.

Prywatność:
- Wywoływany TYLKO gdy privacy_settings.ai_can_read_journal == True
- Treść wpisów skracana do 200 znaków przed wysłaniem do LLM
- Wyniki nie są cachowane — generowane na żądanie

Ważne: wynik zawsze dołącza disclaimer — to asystent refleksji,
nie kierownik duchowy.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Powyższe spostrzeżenia generuje asystent refleksji na podstawie Twoich wpisów. "
    "Nie zastępuje on kierownika duchowego, spowiednika ani terapeuty. "
    "Korzystaj z nich jako punktu wyjścia do osobistej modlitwy i rozmyślania."
)


def _entries_to_sessions(entries: list[Any]) -> list[dict]:
    """Convert JournalEntry ORM objects to the session dict format agents expect."""
    sessions = []
    for e in entries:
        sessions.append({
            "date": e.created_at.strftime("%Y-%m-%d") if e.created_at else "N/A",
            "primary_emotion": e.mood or "nieznana",
            "spiritual_state": "unknown",
            "scripture_ref": e.scripture_reference or "",
            "text": (e.content or "")[:200],
        })
    return sessions


def _combined_session(entries: list[Any]) -> dict:
    """Build a single aggregate session dict for JourneyTrackerAgent."""
    moods = [e.mood for e in entries if e.mood]
    mood_primary = moods[0] if moods else "nieznana"

    scriptures = [e.scripture_reference for e in entries if e.scripture_reference]
    scripture = scriptures[0] if scriptures else ""

    reflections = " ".join(
        (e.content or "")[:100] for e in entries[-5:]
    )

    return {
        "emotions": {"primary": mood_primary},
        "spiritual_state": "unknown",
        "reflection": reflections[:500],
        "scripture": scripture,
    }


class JournalInsightsService:
    """Generates spiritual journey insights from a user's journal entries."""

    async def generate(self, user_id: str, entries: list[Any]) -> dict:
        """
        Analyse journal entries and return journey stage + patterns.

        Args:
            user_id: The authenticated user's ID.
            entries: List of JournalEntry ORM objects (recent, non-deleted).

        Returns:
            Dict with keys: journey, patterns, entry_count, generated_at, disclaimer.
        """
        sessions = _entries_to_sessions(entries)
        combined = _combined_session(entries)

        journey: dict = {
            "current_stage": "purgation",
            "stage_name_pl": "Oczyszczenie",
            "stage_description": "Etap nawrócenia i kształtowania cnót podstawowych",
            "progress_percentage": 10,
            "milestones": [],
            "next_growth_area": "Regularna modlitwa i czytanie Pisma Świętego",
        }
        patterns: list[dict] = []

        try:
            from app.agents.memory.journey_tracker import JourneyTrackerAgent
            tracker = JourneyTrackerAgent()
            journey = await tracker.track(user_id, combined)
        except Exception:
            logger.warning("JourneyTrackerAgent failed; using defaults.")

        try:
            from app.agents.memory.pattern_discovery import PatternDiscoveryAgent
            discoverer = PatternDiscoveryAgent()
            patterns = await discoverer.discover(user_id, sessions)
        except Exception:
            logger.warning("PatternDiscoveryAgent failed; using defaults.")

        return {
            "journey": journey,
            "patterns": patterns,
            "entry_count": len(entries),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": DISCLAIMER,
        }
