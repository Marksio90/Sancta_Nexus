"""
SpiritualDirectorOrchestrator (A-047)
Meta-agent that integrates all spiritual traditions and routes
user interactions to the appropriate tradition-specific agent.
Always includes a disclaimer about not replacing a human spiritual director.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


HUMAN_DIRECTOR_DISCLAIMER = (
    "Uwaga: Sancta Nexus jest narzędziem wspomagającym życie duchowe, "
    "ale nie zastępuje ludzkiego kierownika duchowego. Zachęcamy do regularnych "
    "spotkań z kapłanem lub doświadczonym kierownikiem duchowym, który może "
    "towarzyszyć Ci osobiście na drodze wiary. W sprawach poważnych decyzji "
    "życiowych, kryzysów duchowych czy rozeznawania powołania, zawsze szukaj "
    "żywego przewodnika duchowego."
)


class SpiritualTradition(str, Enum):
    """Supported spiritual traditions for direction."""

    IGNATIAN = "ignatian"
    CARMELITE = "carmelite"
    FRANCISCAN = "franciscan"
    BENEDICTINE = "benedictine"
    CHARISMATIC = "charismatic"
    THOMISTIC = "thomistic"
    GENERAL = "general"


class DirectionMode(str, Enum):
    """Mode of spiritual direction interaction."""

    CONVERSATION = "conversation"
    DISCERNMENT = "discernment"
    EXAMEN = "examen"
    LECTIO_DIVINA = "lectio_divina"
    CRISIS = "crisis"


@dataclass
class UserProfile:
    """Spiritual profile of the user."""

    user_id: str
    preferred_tradition: SpiritualTradition = SpiritualTradition.GENERAL
    spiritual_maturity: str = "intermediate"  # beginner / intermediate / advanced
    sacramental_life: Optional[str] = None
    vocation: Optional[str] = None  # lay / religious / ordained
    prayer_practices: list[str] = field(default_factory=list)
    current_challenges: list[str] = field(default_factory=list)


@dataclass
class DirectorResponse:
    """Response from the Spiritual Director Orchestrator."""

    response: str
    tradition_used: SpiritualTradition
    direction_mode: DirectionMode
    follow_up_questions: list[str]
    recommended_practices: list[str]
    scripture_references: list[str]
    disclaimer: str = HUMAN_DIRECTOR_DISCLAIMER
    metadata: dict = field(default_factory=dict)


TRADITION_SYSTEM_PROMPTS: dict[SpiritualTradition, str] = {
    SpiritualTradition.IGNATIAN: (
        "Prowadź kierownictwo duchowe w tradycji ignacjańskiej. "
        "Kluczowe elementy: rozeznawanie duchów, Ćwiczenia Duchowe, "
        "szukanie Boga we wszystkich rzeczach, magis, Ad Maiorem Dei Gloriam."
    ),
    SpiritualTradition.CARMELITE: (
        "Prowadź kierownictwo duchowe w tradycji karmelitańskiej. "
        "Kluczowe elementy: modlitwa wewnętrzna, noc ciemna, "
        "zamek wewnętrzny, zjednoczenie z Bogiem, ogołocenie."
    ),
    SpiritualTradition.FRANCISCAN: (
        "Prowadź kierownictwo duchowe w tradycji franciszkańskiej. "
        "Kluczowe elementy: ubóstwo, braterstwo, radość, "
        "kontemplacja stworzenia, naśladowanie Chrystusa ubogiego."
    ),
    SpiritualTradition.BENEDICTINE: (
        "Prowadź kierownictwo duchowe w tradycji benedyktyńskiej. "
        "Kluczowe elementy: Ora et Labora, stabilitas, lectio divina, "
        "Liturgia Godzin, wspólnota, posłuszeństwo."
    ),
    SpiritualTradition.CHARISMATIC: (
        "Prowadź kierownictwo duchowe w tradycji charyzmatycznej. "
        "Kluczowe elementy: otwartość na Ducha Świętego, charyzmaty, "
        "uwielbienie, wspólnota modlitewna, osobista relacja z Jezusem."
    ),
    SpiritualTradition.THOMISTIC: (
        "Prowadź kierownictwo duchowe w tradycji tomistycznej. "
        "Kluczowe elementy: cnoty teologalne i kardynalne, "
        "dary Ducha Świętego, porządek łaski, kontemplacja prawdy."
    ),
    SpiritualTradition.GENERAL: (
        "Prowadź kierownictwo duchowe w duchu Kościoła katolickiego, "
        "czerpiąc z bogactwa różnych tradycji duchowych. "
        "Bądź wrażliwy na potrzeby rozmówcy i dostosuj się do jego poziomu."
    ),
}

ORCHESTRATOR_BASE_PROMPT = (
    "Jesteś kierownikiem duchowym w tradycji katolickiej. "
    "Twoje zadanie to towarzyszenie osobie na jej drodze duchowej.\n\n"
    "ZASADY KIEROWNICTWA DUCHOWEGO:\n"
    "1. Słuchaj z uwagą i empatią.\n"
    "2. Nie narzucaj swoich rozwiązań - pomagaj rozmówcy usłyszeć głos Boga.\n"
    "3. Zadawaj pytania otwierające, a nie zamykające.\n"
    "4. Szanuj tajemnicę sumienia.\n"
    "5. Rozpoznawaj granice swojej kompetencji jako narzędzia AI.\n"
    "6. W sytuacjach kryzysowych (myśli samobójcze, przemoc) kieruj do specjalistów.\n"
    "7. Zawsze przypominaj o wartości ludzkiego kierownika duchowego.\n\n"
    "STRUKTURA ROZMOWY:\n"
    "1. Wysłuchaj uważnie.\n"
    "2. Odzwierciedlaj emocje i duchowe poruszenia.\n"
    "3. Odwołuj się do Pisma Świętego i Tradycji.\n"
    "4. Proponuj konkretne praktyki duchowe.\n"
    "5. Zakończ modlitwą lub błogosławieństwem.\n\n"
    "Odpowiadaj w języku polskim z ciepłem i mądrością."
)


class SpiritualDirectorOrchestrator:
    """
    Agent A-047: Meta-agent for spiritual direction.

    Routes conversations to the appropriate tradition-specific agent
    and provides integrated spiritual guidance drawing from the full
    richness of Catholic tradition. Always reminds users that AI
    assistance does not replace a human spiritual director.
    """

    agent_id: str = "A-047"
    agent_name: str = "SpiritualDirectorOrchestrator"

    def __init__(
        self,
        llm_client=None,
        user_store=None,
        tradition_agents: dict | None = None,
    ):
        """
        Args:
            llm_client: Async LLM client with ``chat(messages, **kwargs)`` method.
            user_store: Persistent store for user profiles and history.
            tradition_agents: Map of tradition -> agent instance for delegation.
        """
        self._llm = llm_client
        self._user_store = user_store
        self._tradition_agents = tradition_agents or {}

    async def direct(
        self,
        user_id: str,
        message: str,
        tradition: str = "general",
    ) -> DirectorResponse:
        """
        Provide spiritual direction, routing to the appropriate tradition.

        Args:
            user_id: Unique identifier of the user.
            message: The user's message.
            tradition: Preferred spiritual tradition (defaults to "general").

        Returns:
            A ``DirectorResponse`` with guidance, practices, and disclaimer.
        """
        logger.info(
            "Directing user=%s, tradition=%s",
            user_id,
            tradition,
        )

        # Resolve tradition
        try:
            resolved_tradition = SpiritualTradition(tradition.lower())
        except ValueError:
            resolved_tradition = SpiritualTradition.GENERAL

        # Load user profile
        profile = await self._load_user_profile(user_id, resolved_tradition)

        # Detect direction mode
        mode = self._detect_mode(message)

        # Check for crisis indicators
        if self._detect_crisis(message):
            return await self._handle_crisis(message, profile)

        # Try delegation to tradition-specific agent
        if resolved_tradition in self._tradition_agents:
            return await self._delegate_to_tradition_agent(
                message, profile, resolved_tradition, mode
            )

        # Direct LLM-based response
        system_prompt = self._build_system_prompt(resolved_tradition, profile, mode)
        user_prompt = self._build_user_prompt(message, profile)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self._llm.chat(messages, temperature=0.7, max_tokens=2048)

        follow_up = await self._generate_follow_up_questions(
            message, response.content, resolved_tradition
        )
        practices = self._recommend_practices(resolved_tradition, mode)
        scriptures = await self._suggest_scriptures(message, resolved_tradition)

        return DirectorResponse(
            response=response.content,
            tradition_used=resolved_tradition,
            direction_mode=mode,
            follow_up_questions=follow_up,
            recommended_practices=practices,
            scripture_references=scriptures,
            disclaimer=HUMAN_DIRECTOR_DISCLAIMER,
            metadata={
                "agent_id": self.agent_id,
                "user_id": user_id,
                "tradition": resolved_tradition.value,
                "mode": mode.value,
            },
        )

    async def _load_user_profile(
        self, user_id: str, tradition: SpiritualTradition
    ) -> UserProfile:
        """Load or create a user profile."""
        if self._user_store:
            try:
                data = await self._user_store.get(user_id)
                if data:
                    return UserProfile(**data)
            except Exception:
                logger.exception("Failed to load profile for user=%s", user_id)

        return UserProfile(user_id=user_id, preferred_tradition=tradition)

    def _detect_mode(self, message: str) -> DirectionMode:
        """Detect the appropriate direction mode from the message content."""
        message_lower = message.lower()

        if any(
            kw in message_lower
            for kw in ["rozeznanie", "decyzja", "powołanie", "wybór", "rozeznawanie"]
        ):
            return DirectionMode.DISCERNMENT
        elif any(
            kw in message_lower
            for kw in ["rachunek sumienia", "examen", "przegląd dnia"]
        ):
            return DirectionMode.EXAMEN
        elif any(
            kw in message_lower
            for kw in ["lectio", "czytanie", "słowo boże", "fragment"]
        ):
            return DirectionMode.LECTIO_DIVINA
        elif any(
            kw in message_lower
            for kw in ["kryzys", "nie mogę", "ciemność", "rozpacz", "samobójstwo"]
        ):
            return DirectionMode.CRISIS

        return DirectionMode.CONVERSATION

    def _detect_crisis(self, message: str) -> bool:
        """Detect if the message indicates a mental health crisis."""
        crisis_indicators = [
            "samobójstwo", "chcę umrzeć", "nie chcę żyć",
            "skrzywdzić się", "kończyć z życiem", "nie mam sensu żyć",
        ]
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in crisis_indicators)

    async def _handle_crisis(
        self, message: str, profile: UserProfile
    ) -> DirectorResponse:
        """Handle a crisis situation with appropriate care and referrals."""
        crisis_response = (
            "Widzę, że przeżywasz bardzo trudny czas. Twój ból jest prawdziwy "
            "i ważny. Chcę, żebyś wiedział/a, że nie jesteś sam/a.\n\n"
            "Bóg Cię kocha - nawet w tej ciemności. Psalm 34 mówi: "
            "\"Pan jest blisko ludzi ze złamanym sercem.\"\n\n"
            "Proszę Cię gorąco:\n"
            "1. Zadzwoń na Telefon Zaufania: 116 123\n"
            "2. Centrum Wsparcia: 800 70 2222\n"
            "3. Porozmawiaj z kapłanem, któremu ufasz.\n"
            "4. Jeśli jesteś w bezpośrednim niebezpieczeństwie, zadzwoń na 112.\n\n"
            "Jako narzędzie AI nie jestem w stanie zastąpić profesjonalnej pomocy. "
            "Proszę, zwróć się do żywego człowieka, który może Ci towarzyszyć."
        )

        return DirectorResponse(
            response=crisis_response,
            tradition_used=SpiritualTradition.GENERAL,
            direction_mode=DirectionMode.CRISIS,
            follow_up_questions=[],
            recommended_practices=[
                "Modlitwa Psalm 23 - Pan jest moim pasterzem",
                "Kontakt z zaufaną osobą",
                "Telefon Zaufania: 116 123",
            ],
            scripture_references=["Ps 34,19", "Ps 23", "Iz 43,1-4", "Mt 11,28-30"],
            disclaimer=HUMAN_DIRECTOR_DISCLAIMER,
            metadata={
                "agent_id": self.agent_id,
                "user_id": profile.user_id,
                "crisis_detected": True,
            },
        )

    async def _delegate_to_tradition_agent(
        self,
        message: str,
        profile: UserProfile,
        tradition: SpiritualTradition,
        mode: DirectionMode,
    ) -> DirectorResponse:
        """Delegate to a tradition-specific agent."""
        agent = self._tradition_agents[tradition]

        try:
            result = await agent.guide(
                user_state={"user_id": profile.user_id},
                message=message,
            )
            return DirectorResponse(
                response=result.response,
                tradition_used=tradition,
                direction_mode=mode,
                follow_up_questions=[],
                recommended_practices=[],
                scripture_references=[],
                disclaimer=HUMAN_DIRECTOR_DISCLAIMER,
                metadata={
                    "agent_id": self.agent_id,
                    "delegated_to": agent.agent_id,
                    "user_id": profile.user_id,
                },
            )
        except Exception:
            logger.exception(
                "Delegation to %s agent failed; falling back to orchestrator.",
                tradition.value,
            )
            # Fall through to direct handling
            return await self.direct(
                profile.user_id, message, SpiritualTradition.GENERAL.value
            )

    def _build_system_prompt(
        self,
        tradition: SpiritualTradition,
        profile: UserProfile,
        mode: DirectionMode,
    ) -> str:
        """Assemble the full system prompt."""
        tradition_prompt = TRADITION_SYSTEM_PROMPTS.get(tradition, "")

        mode_instructions = {
            DirectionMode.CONVERSATION: "Prowadź otwartą rozmowę duchową.",
            DirectionMode.DISCERNMENT: (
                "Pomóż w rozeznawaniu duchowym. Stosuj metodę pro/contra, "
                "badaj poruszenia, szukaj woli Bożej."
            ),
            DirectionMode.EXAMEN: (
                "Poprowadź przez Rachunek Sumienia - pięć kroków refleksji nad dniem."
            ),
            DirectionMode.LECTIO_DIVINA: (
                "Poprowadź przez Lectio Divina: lectio, meditatio, oratio, contemplatio, actio."
            ),
            DirectionMode.CRISIS: "Zapewnij wsparcie i kieruj do specjalistów.",
        }

        maturity_note = {
            "beginner": "Osoba jest na początku drogi duchowej. Używaj prostego języka.",
            "intermediate": "Osoba ma doświadczenie w życiu duchowym. Możesz pogłębiać.",
            "advanced": "Osoba jest zaawansowana duchowo. Możesz poruszać tematy mistyczne.",
        }

        return (
            f"{ORCHESTRATOR_BASE_PROMPT}\n\n"
            f"TRADYCJA: {tradition_prompt}\n\n"
            f"TRYB: {mode_instructions.get(mode, '')}\n\n"
            f"DOJRZAŁOŚĆ: {maturity_note.get(profile.spiritual_maturity, '')}"
        )

    def _build_user_prompt(self, message: str, profile: UserProfile) -> str:
        """Build user prompt with profile context."""
        parts = [f'Osoba mówi: "{message}"']

        if profile.current_challenges:
            parts.append(
                f"Aktualne wyzwania: {', '.join(profile.current_challenges)}"
            )

        if profile.prayer_practices:
            parts.append(
                f"Praktyki modlitewne: {', '.join(profile.prayer_practices)}"
            )

        return "\n\n".join(parts)

    async def _generate_follow_up_questions(
        self, message: str, response: str, tradition: SpiritualTradition
    ) -> list[str]:
        """Generate follow-up questions for continuing the direction."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Na podstawie rozmowy kierownictwa duchowego, "
                    "zaproponuj 2-3 pytania pogłębiające. "
                    "Pytania powinny być otwarte i prowadzić do refleksji. "
                    "Zwróć tylko pytania, każde w osobnej linii."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Osoba powiedziała: \"{message}\"\n"
                    f"Kierownik odpowiedział: \"{response[:500]}\"\n\n"
                    "Zaproponuj pytania pogłębiające."
                ),
            },
        ]

        try:
            result = await self._llm.chat(messages, temperature=0.7, max_tokens=256)
            return [q.strip() for q in result.content.strip().split("\n") if q.strip()]
        except Exception:
            logger.exception("Failed to generate follow-up questions")
            return []

    def _recommend_practices(
        self, tradition: SpiritualTradition, mode: DirectionMode
    ) -> list[str]:
        """Recommend spiritual practices based on tradition and mode."""
        base_practices = {
            SpiritualTradition.IGNATIAN: [
                "Rachunek sumienia (Examen) - 15 min wieczorem",
                "Kontemplacja ewangeliczna - 30 min",
                "Colloquium - rozmowa z Chrystusem",
            ],
            SpiritualTradition.CARMELITE: [
                "Modlitwa wewnętrzna - 30 min w ciszy",
                "Lectio divina z pismami św. Jana od Krzyża",
                "Praktyka obecności Bożej",
            ],
            SpiritualTradition.FRANCISCAN: [
                "Modlitwa uwielbienia w przyrodzie",
                "Czytanie Kwiatków św. Franciszka",
                "Akt miłosierdzia wobec potrzebującego",
            ],
            SpiritualTradition.BENEDICTINE: [
                "Lectio divina - 30 min",
                "Liturgia Godzin (Jutrznia/Nieszpory)",
                "Praca w duchu modlitwy (Ora et Labora)",
            ],
            SpiritualTradition.CHARISMATIC: [
                "Uwielbienie spontaniczne - 20 min",
                "Modlitwa w językach",
                "Słuchanie Słowa Bożego z otwartością na Ducha",
            ],
        }

        return base_practices.get(tradition, [
            "Codzienna modlitwa - 20 min",
            "Lektura duchowa - 15 min",
            "Rachunek sumienia wieczorem",
        ])

    async def _suggest_scriptures(
        self, message: str, tradition: SpiritualTradition
    ) -> list[str]:
        """Suggest relevant Scripture references."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Na podstawie tematu rozmowy duchowej, zaproponuj 2-3 "
                    "fragmenty Pisma Świętego, które mogą pomóc w refleksji. "
                    "Podaj same odnośniki biblijne, każdy w osobnej linii."
                ),
            },
            {
                "role": "user",
                "content": f'Temat rozmowy: "{message[:300]}"',
            },
        ]

        try:
            result = await self._llm.chat(messages, temperature=0.5, max_tokens=128)
            return [
                ref.strip()
                for ref in result.content.strip().split("\n")
                if ref.strip()
            ]
        except Exception:
            logger.exception("Failed to suggest scriptures")
            return ["Ps 23", "J 14,1-6", "Flp 4,6-7"]
