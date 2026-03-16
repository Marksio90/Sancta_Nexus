"""JourneyTrackerAgent (A-036) — Mapa drogi duchowej.

Tracks spiritual journey through the three classical stages:
Purgation (Oczyszczenie) -> Illumination (Oświecenie) -> Union (Zjednoczenie)
"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

JOURNEY_STAGES = {
    "purgation": {
        "name_pl": "Oczyszczenie",
        "description": "Etap nawrócenia, walki z grzechem, kształtowania cnót podstawowych",
        "indicators": ["nawrócenie", "walka", "pokuta", "oczyszczenie", "żal", "postanowienie"],
        "range": (0, 33),
    },
    "illumination": {
        "name_pl": "Oświecenie",
        "description": "Etap wzrostu w modlitwie, głębszego poznania Boga, rozwoju cnót",
        "indicators": ["modlitwa", "poznanie", "wzrost", "pokój", "rozeznawanie", "cnoty"],
        "range": (34, 66),
    },
    "union": {
        "name_pl": "Zjednoczenie",
        "description": "Etap głębokiej jedności z Bogiem, kontemplacji, mistycznego zjednoczenia",
        "indicators": ["zjednoczenie", "kontemplacja", "miłość", "pokój głęboki", "oddanie"],
        "range": (67, 100),
    },
}


class JourneyTrackerAgent:
    """Tracks user's spiritual journey through the three classical stages."""

    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.3)

    async def track(self, user_id: str, session_data: dict) -> dict:
        """Analyze session and update journey position."""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=(
                    "Jesteś doświadczonym kierownikiem duchowym analizującym postęp "
                    "na drodze duchowej. Na podstawie danych z sesji określ:\n"
                    "1. Aktualny etap: purgation, illumination, lub union\n"
                    "2. Postęp procentowy (0-100)\n"
                    "3. Kamienie milowe osiągnięte\n"
                    "4. Obszar do dalszego wzrostu\n\n"
                    "Odpowiedz w formacie:\n"
                    "STAGE: [etap]\nPROGRESS: [procent]\n"
                    "MILESTONE: [opis]\nGROWTH: [obszar]"
                )),
                HumanMessage(content=(
                    f"User ID: {user_id}\n"
                    f"Emocje: {session_data.get('emotions', {})}\n"
                    f"Stan duchowy: {session_data.get('spiritual_state', 'unknown')}\n"
                    f"Refleksja: {session_data.get('reflection', '')}\n"
                    f"Fragment biblijny: {session_data.get('scripture', '')}"
                )),
            ])

            result = self._parse_response(response.content)
            return result

        except Exception as e:
            logger.error(f"Journey tracking error: {e}")
            return {
                "current_stage": "purgation",
                "stage_name_pl": "Oczyszczenie",
                "progress_percentage": 15,
                "milestones": [],
                "next_growth_area": "Regularna modlitwa i czytanie Pisma Świętego",
            }

    def _parse_response(self, text: str) -> dict:
        stage = "purgation"
        progress = 15
        milestone = ""
        growth = ""

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("STAGE:"):
                s = line.split(":", 1)[1].strip().lower()
                if s in JOURNEY_STAGES:
                    stage = s
            elif line.startswith("PROGRESS:"):
                try:
                    progress = int(line.split(":", 1)[1].strip().rstrip("%"))
                    progress = max(0, min(100, progress))
                except ValueError:
                    pass
            elif line.startswith("MILESTONE:"):
                milestone = line.split(":", 1)[1].strip()
            elif line.startswith("GROWTH:"):
                growth = line.split(":", 1)[1].strip()

        stage_info = JOURNEY_STAGES[stage]
        return {
            "current_stage": stage,
            "stage_name_pl": stage_info["name_pl"],
            "stage_description": stage_info["description"],
            "progress_percentage": progress,
            "milestones": [milestone] if milestone else [],
            "next_growth_area": growth or "Kontynuacja codziennej modlitwy",
        }
