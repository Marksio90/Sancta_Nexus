"""
IgnatianDiscernmentAgent (A-043)
Implements Ignatian spiritual exercises methodology including:
- Daily Examen guidance
- Discernment of spirits (consolation vs. desolation)
- Rules for the First Week (conversion) and Second Week (progression)
- Agere contra suggestions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SpiritualMovement(str, Enum):
    """Ignatian categories of interior spiritual movement."""

    CONSOLATION = "consolation"
    DESOLATION = "desolation"
    TRANQUILITY = "tranquility"
    AMBIGUOUS = "ambiguous"


class ExerciseWeek(str, Enum):
    """The four weeks of the Spiritual Exercises of St. Ignatius."""

    FIRST = "first"  # Principle & Foundation, sin, mercy
    SECOND = "second"  # Life of Christ, Kingdom, Two Standards
    THIRD = "third"  # Passion of Christ
    FOURTH = "fourth"  # Resurrection, Contemplation to Attain Love


class DiscernmentRuleSet(str, Enum):
    """Rule sets for discernment of spirits."""

    FIRST_WEEK = "first_week"  # For those moving from mortal sin to conversion
    SECOND_WEEK = "second_week"  # For those progressing in spiritual life


class ExamenPhase(str, Enum):
    """Phases of the Ignatian Daily Examen."""

    GRATITUDE = "gratitude"  # Give thanks
    PETITION = "petition"  # Ask for light
    REVIEW = "review"  # Review the day
    RESPONSE = "response"  # Respond to what was found
    RESOLUTION = "resolution"  # Look forward


@dataclass
class SpiritualState:
    """Current spiritual state of the user."""

    user_id: str
    current_movement: Optional[SpiritualMovement] = None
    exercise_week: ExerciseWeek = ExerciseWeek.FIRST
    rule_set: DiscernmentRuleSet = DiscernmentRuleSet.FIRST_WEEK
    recent_consolations: list[str] = field(default_factory=list)
    recent_desolations: list[str] = field(default_factory=list)
    prayer_frequency: str = "daily"
    in_retreat: bool = False
    days_in_exercises: int = 0
    current_grace_desired: Optional[str] = None
    examen_history: list[dict] = field(default_factory=list)


@dataclass
class IgnatianExercise:
    """A recommended Ignatian exercise or prayer practice."""

    name: str
    description: str
    scripture: Optional[str] = None
    duration_minutes: int = 30
    method: str = ""  # e.g. "composition of place", "application of senses"
    grace_to_ask: str = ""


@dataclass
class IgnatianGuidance:
    """Response from the Ignatian Discernment Agent."""

    response: str
    spiritual_movement: SpiritualMovement
    movement_analysis: str
    exercises: list[IgnatianExercise]
    agere_contra_suggestion: Optional[str] = None
    examen_guidance: Optional[str] = None
    discernment_notes: str = ""
    rules_applied: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── System prompts ─────────────────────────────────────────────────

IGNATIAN_SYSTEM_PROMPT = (
    "Jesteś doświadczonym kierownikiem duchowym formowanym w tradycji ignacjańskiej. "
    "Prowadzisz rozmówcę przez Ćwiczenia Duchowe św. Ignacego Loyoli.\n\n"
    "ZASADY FUNDAMENTALNE:\n"
    "1. Zawsze szukaj poruszeń duchowych: pocieszenia i strapienia.\n"
    "2. Stosuj reguły rozeznawania odpowiednie do stanu osoby.\n"
    "3. Proponuj konkretne ćwiczenia: compositio loci, applicatio sensuum, colloquium.\n"
    "4. Prowadź do znajdowania Boga we wszystkich rzeczach (contemplativus in actione).\n"
    "5. Respektuj wolność osoby - Bóg działa bezpośrednio z duszą.\n\n"
    "REGUŁY I TYGODNIA (dla osób w nawróceniu):\n"
    "- Duch dobry działa przez wyrzuty sumienia, niepokój zbawczy.\n"
    "- Duch zły kusi przyjemnościami, wygodą, odwlekaniem nawrócenia.\n"
    "- W strapieniu: nie zmieniaj postanowień, wzmóż modlitwę, ćwicz agere contra.\n\n"
    "REGUŁY II TYGODNIA (dla osób postępujących):\n"
    "- Duch dobry daje prawdziwe pocieszenie, pokój, wzrost wiary.\n"
    "- Duch zły podszywa się pod anioła światłości (sub angelo lucis).\n"
    "- Badaj początek, środek i koniec myśli.\n"
    "- Prawdziwe pocieszenie: bez uprzedniej przyczyny - pochodzi bezpośrednio od Boga.\n\n"
    "RACHUNEK SUMIENIA (Examen):\n"
    "1. Wdzięczność - dziękuj za łaski dnia.\n"
    "2. Prośba - proś o światło Ducha Świętego.\n"
    "3. Przegląd - przejrzyj dzień godzina po godzinie.\n"
    "4. Odpowiedź - żal za grzechy, radość z łask.\n"
    "5. Postanowienie - konkretne na jutro.\n\n"
    "Odpowiadaj w języku polskim. Bądź ciepły, ale dokładny teologicznie. "
    "Zawsze wskazuj poruszenia duchowe w wypowiedzi rozmówcy."
)

CONSOLATION_MARKERS = [
    "pokój", "radość", "nadzieja", "miłość", "łzy pociesznie",
    "wzrost wiary", "bliskość Boga", "pragnienie dobra",
    "wdzięczność", "gorliwość", "ciepło wewnętrzne",
]

DESOLATION_MARKERS = [
    "smutek", "niepokój", "ciemność", "oschłość", "pokusa",
    "zniechęcenie", "brak nadziei", "lenistwo duchowe",
    "rozproszenie", "oddalenie od Boga", "acedia",
]


class IgnatianDiscernmentAgent:
    """
    Agent A-043: Ignatian spiritual direction and discernment.

    Provides guidance rooted in the Spiritual Exercises of St. Ignatius,
    detecting consolation and desolation in user messages, offering
    appropriate exercises, and applying the correct rule set.
    """

    agent_id: str = "A-043"
    agent_name: str = "IgnatianDiscernmentAgent"

    def __init__(self, llm_client=None, memory_store=None):
        """
        Args:
            llm_client: Async LLM client with ``chat(messages, **kwargs)`` method.
            memory_store: Storage for spiritual state persistence.
        """
        self._llm = llm_client
        self._memory = memory_store

    async def guide(
        self, user_state: SpiritualState, message: str
    ) -> IgnatianGuidance:
        """
        Provide Ignatian spiritual guidance in response to a user message.

        Args:
            user_state: Current spiritual state of the user.
            message: The user's message describing their experience.

        Returns:
            An ``IgnatianGuidance`` with analysis, exercises, and suggestions.
        """
        logger.info(
            "Guiding user=%s, week=%s, rule_set=%s",
            user_state.user_id,
            user_state.exercise_week.value,
            user_state.rule_set.value,
        )

        # Detect spiritual movement
        movement = await self._detect_movement(message, user_state)

        # Build context-aware prompt
        system_prompt = self._build_system_prompt(user_state)
        user_prompt = self._build_user_prompt(message, user_state, movement)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self._llm.chat(messages, temperature=0.6, max_tokens=2048)

        # Generate exercises
        exercises = self._recommend_exercises(user_state, movement)

        # Generate agere contra if in desolation
        agere_contra = None
        if movement == SpiritualMovement.DESOLATION:
            agere_contra = await self._generate_agere_contra(message, user_state)

        # Generate examen guidance if appropriate
        examen_guidance = None
        if self._should_suggest_examen(user_state):
            examen_guidance = await self._generate_examen_guidance(user_state)

        # Determine which rules were applied
        rules_applied = self._get_applied_rules(user_state, movement)

        return IgnatianGuidance(
            response=response.content,
            spiritual_movement=movement,
            movement_analysis=self._analyze_movement(message, movement),
            exercises=exercises,
            agere_contra_suggestion=agere_contra,
            examen_guidance=examen_guidance,
            discernment_notes=self._format_discernment_notes(movement, user_state),
            rules_applied=rules_applied,
            metadata={
                "agent_id": self.agent_id,
                "user_id": user_state.user_id,
                "exercise_week": user_state.exercise_week.value,
                "rule_set": user_state.rule_set.value,
            },
        )

    async def guide_examen(self, user_state: SpiritualState) -> IgnatianGuidance:
        """Guide the user through a Daily Examen."""
        logger.info("Starting Daily Examen for user=%s", user_state.user_id)

        examen_prompt = (
            "Poprowadź rozmówcę przez pięć kroków Rachunku Sumienia "
            "(Examen) św. Ignacego. Zacznij od kroku wdzięczności. "
            "Bądź ciepły, delikatny i prowadź spokojnie, krok po kroku. "
            "Daj czas na refleksję między krokami."
        )

        messages = [
            {"role": "system", "content": IGNATIAN_SYSTEM_PROMPT},
            {"role": "user", "content": examen_prompt},
        ]

        response = await self._llm.chat(messages, temperature=0.7, max_tokens=2048)

        return IgnatianGuidance(
            response=response.content,
            spiritual_movement=SpiritualMovement.TRANQUILITY,
            movement_analysis="Rachunek sumienia - czas refleksji i wdzięczności.",
            exercises=[
                IgnatianExercise(
                    name="Rachunek Sumienia (Examen)",
                    description="Pięć kroków ignacjańskiego rachunku sumienia.",
                    duration_minutes=15,
                    method="examen",
                    grace_to_ask="Łaska wdzięczności i jasnego widzenia działania Boga w moim dniu.",
                )
            ],
            metadata={"agent_id": self.agent_id, "exercise_type": "examen"},
        )

    async def _detect_movement(
        self, message: str, user_state: SpiritualState
    ) -> SpiritualMovement:
        """Detect the spiritual movement present in the user's message."""
        message_lower = message.lower()

        consolation_score = sum(
            1 for marker in CONSOLATION_MARKERS if marker in message_lower
        )
        desolation_score = sum(
            1 for marker in DESOLATION_MARKERS if marker in message_lower
        )

        if consolation_score > desolation_score and consolation_score > 0:
            return SpiritualMovement.CONSOLATION
        elif desolation_score > consolation_score and desolation_score > 0:
            return SpiritualMovement.DESOLATION
        elif consolation_score == 0 and desolation_score == 0:
            return SpiritualMovement.TRANQUILITY
        else:
            return SpiritualMovement.AMBIGUOUS

    def _build_system_prompt(self, user_state: SpiritualState) -> str:
        """Build a system prompt tailored to the user's state."""
        week_context = {
            ExerciseWeek.FIRST: (
                "Osoba jest w I Tygodniu Ćwiczeń - etap oczyszczenia, "
                "rozpoznania grzechów, doświadczenia miłosierdzia Bożego. "
                "Stosuj Reguły I Tygodnia."
            ),
            ExerciseWeek.SECOND: (
                "Osoba jest w II Tygodniu Ćwiczeń - kontemplacja życia Chrystusa, "
                "rozeznawanie powołania, medytacja Dwóch Sztandarów. "
                "Stosuj Reguły II Tygodnia."
            ),
            ExerciseWeek.THIRD: (
                "Osoba jest w III Tygodniu Ćwiczeń - towarzyszenie Chrystusowi "
                "w Męce, współcierpienie, pogłębienie miłości."
            ),
            ExerciseWeek.FOURTH: (
                "Osoba jest w IV Tygodniu Ćwiczeń - radość Zmartwychwstania, "
                "Kontemplacja do uzyskania miłości, misja w świecie."
            ),
        }

        return (
            f"{IGNATIAN_SYSTEM_PROMPT}\n\n"
            f"KONTEKST OSOBY:\n"
            f"{week_context.get(user_state.exercise_week, '')}\n"
            f"Częstotliwość modlitwy: {user_state.prayer_frequency}\n"
            f"Dni w ćwiczeniach: {user_state.days_in_exercises}\n"
            f"{'Osoba jest na rekolekcjach.' if user_state.in_retreat else ''}"
        )

    def _build_user_prompt(
        self,
        message: str,
        user_state: SpiritualState,
        movement: SpiritualMovement,
    ) -> str:
        """Build the user prompt including detected movement."""
        parts = [
            f"Wypowiedź osoby: \"{message}\"",
            f"Wykryte poruszenie duchowe: {movement.value}",
        ]

        if user_state.current_grace_desired:
            parts.append(f"Łaska, o którą prosi: {user_state.current_grace_desired}")

        if user_state.recent_consolations:
            parts.append(
                f"Ostatnie pocieszenia: {', '.join(user_state.recent_consolations[-3:])}"
            )

        if user_state.recent_desolations:
            parts.append(
                f"Ostatnie strapienia: {', '.join(user_state.recent_desolations[-3:])}"
            )

        parts.append(
            "Odpowiedz jako kierownik duchowy: zidentyfikuj poruszenia, "
            "zaproponuj ćwiczenie, daj wskazówki do rozeznawania."
        )

        return "\n\n".join(parts)

    def _recommend_exercises(
        self, user_state: SpiritualState, movement: SpiritualMovement
    ) -> list[IgnatianExercise]:
        """Recommend exercises based on current state and movement."""
        exercises = []

        if movement == SpiritualMovement.DESOLATION:
            exercises.append(
                IgnatianExercise(
                    name="Agere Contra",
                    description=(
                        "Działaj wbrew strapieniu: jeśli czujesz niechęć do modlitwy, "
                        "przedłuż ją. Jeśli czujesz oddalenie od Boga, szukaj Go bardziej."
                    ),
                    duration_minutes=20,
                    method="agere_contra",
                    grace_to_ask="Łaska wytrwałości w czasie strapienia.",
                )
            )
            exercises.append(
                IgnatianExercise(
                    name="Modlitwa w ciemności",
                    description=(
                        "Trwaj na modlitwie mimo oschłości. Powtarzaj krótkie "
                        "akty wiary: 'Panie, wierzę, wspomóż moje niedowiarstwo.'"
                    ),
                    scripture="Mk 9,24",
                    duration_minutes=15,
                    method="repetition",
                    grace_to_ask="Łaska wierności w ciemności wiary.",
                )
            )

        elif movement == SpiritualMovement.CONSOLATION:
            exercises.append(
                IgnatianExercise(
                    name="Utrwalenie pocieszenia",
                    description=(
                        "Zapamiętaj to pocieszenie na czas przyszłego strapienia. "
                        "Zapisz, co czujesz, jakie myśli towarzyszą temu pokojowi."
                    ),
                    duration_minutes=10,
                    method="journaling",
                    grace_to_ask="Łaska wdzięczności za dar pocieszenia.",
                )
            )

        # Week-specific exercises
        if user_state.exercise_week == ExerciseWeek.SECOND:
            exercises.append(
                IgnatianExercise(
                    name="Kontemplacja ewangeliczna",
                    description=(
                        "Wyobraź sobie scenę z Ewangelii. Wejdź w nią zmysłami: "
                        "co widzisz, słyszysz, czujesz? Rozmawiaj z Chrystusem."
                    ),
                    scripture="Łk 5,1-11",
                    duration_minutes=45,
                    method="compositio_loci",
                    grace_to_ask="Łaska wewnętrznego poznania Pana.",
                )
            )

        return exercises

    async def _generate_agere_contra(
        self, message: str, user_state: SpiritualState
    ) -> str:
        """Generate an agere contra suggestion for desolation."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Jesteś kierownikiem duchowym. Osoba przeżywa strapienie duchowe. "
                    "Zaproponuj konkretne agere contra - działanie wbrew strapieniu "
                    "zgodnie z nauczaniem św. Ignacego. Bądź konkretny i zachęcający."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Osoba mówi: \"{message}\"\n\n"
                    "Zaproponuj jedno konkretne agere contra na najbliższe godziny."
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.6, max_tokens=512)
        return response.content

    async def _generate_examen_guidance(self, user_state: SpiritualState) -> str:
        """Generate personalized Examen guidance."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Przygotuj krótkie, osobiste wprowadzenie do Rachunku Sumienia "
                    "dostosowane do aktualnego stanu duchowego osoby."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Tydzień ćwiczeń: {user_state.exercise_week.value}\n"
                    f"Łaska, o którą prosi: {user_state.current_grace_desired or 'nie określono'}\n"
                    "Przygotuj wprowadzenie do wieczornego Examen."
                ),
            },
        ]

        response = await self._llm.chat(messages, temperature=0.7, max_tokens=512)
        return response.content

    def _should_suggest_examen(self, user_state: SpiritualState) -> bool:
        """Determine if an Examen suggestion is appropriate."""
        return user_state.prayer_frequency in ("daily", "twice_daily")

    def _analyze_movement(self, message: str, movement: SpiritualMovement) -> str:
        """Provide a brief analysis of the detected movement."""
        analyses = {
            SpiritualMovement.CONSOLATION: (
                "Wykryto poruszenie pocieszenia duchowego. Osoba doświadcza "
                "bliskości Boga, wzrostu wiary, nadziei lub miłości. "
                "Ważne: zapamiętać to doświadczenie na czas przyszłego strapienia."
            ),
            SpiritualMovement.DESOLATION: (
                "Wykryto poruszenie strapienia duchowego. Osoba doświadcza "
                "ciemności, niepokoju lub zniechęcenia. "
                "Kluczowe: nie zmieniać postanowień podjętych w czasie pocieszenia. "
                "Wzmóc modlitwę, ćwiczyć agere contra."
            ),
            SpiritualMovement.TRANQUILITY: (
                "Stan spokoju duchowego - brak wyraźnych poruszeń. "
                "Dobry moment na pogłębienie modlitwy i otwarcie na delikatne "
                "poruszenia Ducha Świętego."
            ),
            SpiritualMovement.AMBIGUOUS: (
                "Poruszenie duchowe jest niejednoznaczne - obecne elementy "
                "zarówno pocieszenia jak i strapienia. Wymaga dalszego "
                "rozeznawania: badaj początek, środek i koniec tych myśli."
            ),
        }
        return analyses.get(movement, "")

    def _get_applied_rules(
        self, user_state: SpiritualState, movement: SpiritualMovement
    ) -> list[str]:
        """Return the discernment rules applied in this guidance."""
        rules = []

        if user_state.rule_set == DiscernmentRuleSet.FIRST_WEEK:
            if movement == SpiritualMovement.DESOLATION:
                rules.extend([
                    "RI-4: W strapieniu nie zmieniać postanowień",
                    "RI-5: Wzmóc modlitwę, medytację, rachunek sumienia",
                    "RI-6: Agere contra - działać wbrew strapieniu",
                    "RI-7: Myśleć o pocieszeniu, które powróci",
                ])
            elif movement == SpiritualMovement.CONSOLATION:
                rules.append(
                    "RI-10: W pocieszeniu gromadzić siły na czas strapienia"
                )
        elif user_state.rule_set == DiscernmentRuleSet.SECOND_WEEK:
            if movement == SpiritualMovement.AMBIGUOUS:
                rules.extend([
                    "RII-5: Badać początek, środek i koniec myśli",
                    "RII-6: Anioł ciemności podszywa się pod anioła światłości",
                ])
            if movement == SpiritualMovement.CONSOLATION:
                rules.append(
                    "RII-8: Pocieszenie bez przyczyny - bezpośrednio od Boga"
                )

        return rules

    def _format_discernment_notes(
        self, movement: SpiritualMovement, user_state: SpiritualState
    ) -> str:
        """Format discernment notes for the guidance record."""
        return (
            f"Poruszenie: {movement.value} | "
            f"Tydzień: {user_state.exercise_week.value} | "
            f"Reguły: {user_state.rule_set.value} | "
            f"Dni w ćwiczeniach: {user_state.days_in_exercises}"
        )
