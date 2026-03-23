"""
Actio Agent (A-014)
===================
Generates a concrete daily challenge / micro-quest that connects
the scripture reflection to the user's everyday life.

Now enriched with:
  - Corporal & Spiritual Works of Mercy (CCC 2447)
  - Cardinal & Theological Virtues framework
  - Evening Examen (rachunek sumienia) integration
  - Scripture-grounded challenges (not abstract)
  - Difficulty calibrated to user's spiritual journey stage

"Estote factores verbi et non auditores tantum." — Jas 1:22
"Fides sine operibus mortua est." — Jas 2:26
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_fast

logger = logging.getLogger("sancta_nexus.actio_agent")

# ---------------------------------------------------------------------------
# System prompt — enriched with Works of Mercy and virtues
# ---------------------------------------------------------------------------

ACTIO_SYSTEM_PROMPT = """\
Jestes przewodnikiem duchowym w systemie Sancta Nexus, specjalizujacym sie
w przekladaniu rozwaznan biblijnych na konkretne, codzienne dzialania.

Twoje wyzwania sa zakorzenione w:
- Uczynkach milosierdzia (CCC 2447)
- Cnotach kardynalnych (roztropnosc, sprawiedliwosc, mestwo, umiarkowoanie)
- Cnotach teologalnych (wiara, nadzieja, milosc)
- Owocach Ducha Swietego (Ga 5,22-23)

═══════════════════════════════════════════════════════════
FRAGMENT PISMA
═══════════════════════════════════════════════════════════

{book} {chapter}:{verse_start}-{verse_end}
Tekst: {text}

═══════════════════════════════════════════════════════════
REFLEKSJA MEDYTACYJNA
═══════════════════════════════════════════════════════════

{reflection}

═══════════════════════════════════════════════════════════
KONTEKST UNIKALNOSCIOWY
═══════════════════════════════════════════════════════════

Sugerowana kategoria dzialania (na podstawie rotacji): {suggested_category}
Unikaj powtarzania kategorii z ostatnich sesji.

═══════════════════════════════════════════════════════════
ZASADY TWORZENIA WYZWANIA
═══════════════════════════════════════════════════════════

1. KONKRETNOSC: Wyzwanie musi byc KONKRETNE i MIERZALNE:
   ✓ "Porozmawiaj z jedna osoba, ktora jest samotna"
   ✓ "Napisz list/wiadomosc do osoby, za ktora jestes wdzieczny/a"
   ✓ "Poswiec 10 minut na cicha modlitwe za osobe, ktora cie zranila"
   ✗ "Badz dobry" (zbyt ogolne)
   ✗ "Pomysl o Bogu" (zbyt abstrakcyjne)

2. ZAKORZENIENIE: Wyzwanie MUSI bezposrednio wynikac z przeslania fragmentu.

3. WYKONALNOSC: Mozliwe do realizacji w ciagu 24 godzin.

4. KATEGORIE DZIALANIA (oparte na Uczynkach Milosierdzia):
   Uczynki milosierdzia co do ciala:
   - "feed_hungry" — karmienie glodnych, dzielenie sie jedzeniem
   - "shelter" — goscina, troska o bezdomnych
   - "clothe" — pomaganie potrzebujacym materialnie
   - "visit_sick" — odwiedzanie chorych
   - "visit_imprisoned" — pamiec o wiezionych, wykluczonych
   - "bury_dead" — pamiec o zmarlych, modlitwa za nich

   Uczynki milosierdzia co do duszy:
   - "teach" — nauczanie, dzielenie sie wiedza o wierze
   - "counsel" — doradzanie wątpiacym
   - "admonish" — upomnienie braterskie (z miloscia)
   - "comfort" — pocieszanie strapionych
   - "forgive" — przebaczenie uraz
   - "bear_wrongs" — cierpliwe znoszenie

   Cnoty i modlitwa:
   - "prayer" — modlitwa osobista lub wstawiennicza
   - "gratitude" — wdziecznosc i uwielbienie
   - "self_care" — troska o cialo jako swiatynie Ducha (1 Kor 6,19)
   - "silence" — cisza i sluchanie Boga

5. POZIOMY TRUDNOSCI:
   - "easy"   — proste dzialanie, dostepne dla kazdego, zajmuje do 10 minut
   - "medium" — wymaga refleksji lub pewnego wysilku, zajmuje 15-30 minut
   - "hard"   — wymaga ofiary, odwagi lub wytrwalosci przez caly dzien
   - "divine" — POZIOM BOSKI: tylko dla zaawansowanych na Drodze Zjednoczenia (Via Unitiva).
                Wyzwanie transformacyjne, wymagajace calkowitego oddania sie Bogu przez minimum
                3 dni. Zakorzenione w mistycznej jednosci z Chrystusem (np. kontemplacja,
                modlitwa wstawiennicza za wrogow, heroiczny uczynek milosierdzia, post
                i modlitwa, pelne przebaczenie).
                Przyklad: "Przez 3 dni w ciszy serca modl sie za osobe, ktora cie najbardziej
                zranila, ofiarujac kazdy bol jako dar dla Chrystusa Ukrzyzowanego."
                UWAZ: uzywaj "divine" rzadko i tylko gdy kontekst duchowy na to pozwala.

6. RACHUNEK SUMIENIA WIECZORNY:
   Pytanie wieczorne powinno prowadzic przez 3 kroki:
   a) Spojrzenie wstecz: co sie wydarzylo?
   b) Rozpoznanie Bozej obecnosci: gdzie Bog byl w tym dzialaniu?
   c) Postanowienie na jutro: co chce kontynuowac?

Odpowiedz w formacie JSON:
{{
  "challenge_text": "Tresc wyzwania (max 60 slow, konkretne i mierzalne)",
  "scripture_anchor": "Konkretna fraza z fragmentu, z ktorej wynika wyzwanie",
  "difficulty": "easy|medium|hard|divine",
  "category": "<jedna z powyzszych kategorii>",
  "virtue_focus": "Cnota, ktora wyzwanie rozwija (np. cierpliwosc, milosc, roztropnosc)",
  "evening_examen": {{
    "retrospection": "Pytanie: co sie wydarzylo w zwiazku z wyzwaniem?",
    "divine_presence": "Pytanie: gdzie Bog byl w tym doswiadczeniu?",
    "resolution": "Pytanie: co chce kontynuowac jutro?"
  }}
}}
"""

# ---------------------------------------------------------------------------
# Fallback — enriched
# ---------------------------------------------------------------------------

FALLBACK_ACTION: dict[str, Any] = {
    "challenge_text": (
        "Dzis poswiec 5 minut na cisze — zamknij oczy, oddychaj spokojnie, "
        "i zapisz jedna rzecz, za ktora jestes wdzieczny/wdzieczna Bogu. "
        "Nastepnie wyslij wiadomosc do jednej osoby, by powiedziec jej, "
        "ze o niej pamiętasz."
    ),
    "scripture_anchor": "Wdziecznosc jest brama do modlitwy",
    "difficulty": "easy",
    "category": "gratitude",
    "virtue_focus": "wdziecznosc",
    "evening_examen": {
        "retrospection": "Czy udalo ci sie dzis zatrzymac na chwile ciszy? Co zapisales/as?",
        "divine_presence": "Gdzie w tej chwili ciszy poczules/as Boza obecnosc?",
        "resolution": "Jaka mala praktyke wdziecznosci chcesz kontynuowac jutro?",
    },
}


class ActioAgent:
    """
    A-014 — Action / micro-quest generation agent.

    Bridges contemplation and daily life by proposing a single,
    achievable spiritual challenge rooted in Scripture and aligned
    with the Works of Mercy, cardinal virtues, and the user's
    unique rotation through action categories.
    """

    VALID_CATEGORIES = frozenset({
        "prayer", "gratitude", "self_care", "silence",
        "feed_hungry", "shelter", "clothe", "visit_sick",
        "visit_imprisoned", "bury_dead",
        "teach", "counsel", "admonish", "comfort",
        "forgive", "bear_wrongs",
    })

    def __init__(self) -> None:
        try:
            self._llm = get_llm_fast(temperature=0.7, max_tokens=1024)
            logger.info("ActioAgent (A-014) initialised.")
        except Exception as exc:
            logger.warning("ActioAgent: LLM init failed (%s); will use fallbacks.", exc)
            self._llm = None

    VALID_DIFFICULTIES = frozenset({"easy", "medium", "hard", "divine"})

    @staticmethod
    def _assess_difficulty(session_count: int) -> str:
        """Return the appropriate difficulty cap based on the user's journey stage."""
        if session_count >= 60:
            return "divine"
        if session_count >= 40:
            return "hard"
        if session_count >= 20:
            return "medium"
        return "easy"

    async def challenge(
        self,
        scripture: dict,
        reflection: dict,
        suggested_category: str = "gratitude",
        session_count: int = 0,
    ) -> dict:
        """Generate a daily micro-quest linked to the scripture reflection.

        Args:
            session_count: Total completed sessions — used to calibrate the
                difficulty ceiling.  ≥60 sessions unlocks the "divine" level.
        """
        reflection_text = self._format_reflection(reflection)

        if self._llm is None:
            return dict(FALLBACK_ACTION)

        difficulty_ceiling = self._assess_difficulty(session_count)
        difficulty_hint = (
            f"Uzytkownik ukonczyl {session_count} sesji. "
            f"Maksymalny poziom trudnosci dla niego: '{difficulty_ceiling}'. "
            + (
                "Mozesz zaproponowac poziom 'divine' (Boski) — uzytkownik osiagnal Via Unitiva."
                if difficulty_ceiling == "divine"
                else f"Nie przekraczaj poziomu '{difficulty_ceiling}'."
            )
        )

        system_prompt = ACTIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
            reflection=reflection_text,
            suggested_category=suggested_category,
        ) + f"\n\n{difficulty_hint}"

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Wygeneruj wyzwanie dnia oparte na Uczynkach Milosierdzia."),
            ])
            action = self._parse_json(response.content)

            if not action.get("challenge_text"):
                logger.warning("Challenge text missing; using fallback.")
                return dict(FALLBACK_ACTION)

            # Normalise difficulty — clamp to assessed ceiling
            allowed = {"easy"}
            if difficulty_ceiling in ("medium", "hard", "divine"):
                allowed.add("medium")
            if difficulty_ceiling in ("hard", "divine"):
                allowed.add("hard")
            if difficulty_ceiling == "divine":
                allowed.add("divine")

            if action.get("difficulty") not in allowed:
                action["difficulty"] = difficulty_ceiling

            # Ensure evening examen structure
            examen = action.get("evening_examen", {})
            if not isinstance(examen, dict) or not examen.get("retrospection"):
                action["evening_examen"] = FALLBACK_ACTION["evening_examen"]

            # Backward compatibility
            if not action.get("evening_checkin_prompt"):
                e = action["evening_examen"]
                action["evening_checkin_prompt"] = (
                    f"{e.get('retrospection', '')} "
                    f"{e.get('divine_presence', '')}"
                )

            action.setdefault("scripture_anchor", "")
            action.setdefault("virtue_focus", "")
            action.setdefault("category", suggested_category)

            logger.info(
                "Action generated: category=%s, difficulty=%s, virtue=%s",
                action.get("category"), action.get("difficulty"),
                action.get("virtue_focus"),
            )
            return action

        except Exception as exc:
            logger.error("Action generation failed: %s", exc, exc_info=True)
            return dict(FALLBACK_ACTION)

    @staticmethod
    def _format_reflection(reflection: dict) -> str:
        parts: list[str] = []
        questions = reflection.get("questions", [])
        if questions:
            parts.append("Pytania refleksyjne:")
            for i, q in enumerate(questions, 1):
                if isinstance(q, str):
                    parts.append(f"  {i}. {q}")
                elif isinstance(q, dict):
                    parts.append(f"  {i}. {q.get('text', str(q))}")
                else:
                    parts.append(f"  {i}. {q}")

        layers = reflection.get("reflection_layers", {})
        if layers:
            parts.append("\nWarstwy refleksji:")
            for layer_name, layer_text in layers.items():
                parts.append(f"  {layer_name}: {layer_text}")

        return "\n".join(parts) if parts else "brak refleksji"

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Could not parse action JSON: %s", exc)
            return dict(FALLBACK_ACTION)
