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

5. RACHUNEK SUMIENIA WIECZORNY:
   Pytanie wieczorne powinno prowadzic przez 3 kroki:
   a) Spojrzenie wstecz: co sie wydarzylo?
   b) Rozpoznanie Bozej obecnosci: gdzie Bog byl w tym dzialaniu?
   c) Postanowienie na jutro: co chce kontynuowac?

Odpowiedz w formacie JSON:
{{
  "challenge_text": "Tresc wyzwania (max 60 slow, konkretne i mierzalne)",
  "scripture_anchor": "Konkretna fraza z fragmentu, z ktorej wynika wyzwanie",
  "difficulty": "easy|medium|hard",
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

    async def challenge(
        self,
        scripture: dict,
        reflection: dict,
        suggested_category: str = "gratitude",
    ) -> dict:
        """Generate a daily micro-quest linked to the scripture reflection."""
        reflection_text = self._format_reflection(reflection)

        if self._llm is None:
            return dict(FALLBACK_ACTION)

        system_prompt = ACTIO_SYSTEM_PROMPT.format(
            book=scripture.get("book", ""),
            chapter=scripture.get("chapter", ""),
            verse_start=scripture.get("verse_start", ""),
            verse_end=scripture.get("verse_end", ""),
            text=scripture.get("text", ""),
            reflection=reflection_text,
            suggested_category=suggested_category,
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content="Wygeneruj wyzwanie dnia oparte na Uczynkach Milosierdzia."),
            ])
            action = self._parse_json(response.content)

            if not action.get("challenge_text"):
                logger.warning("Challenge text missing; using fallback.")
                return dict(FALLBACK_ACTION)

            # Normalise difficulty
            valid_difficulties = {"easy", "medium", "hard"}
            if action.get("difficulty") not in valid_difficulties:
                action["difficulty"] = "easy"

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
