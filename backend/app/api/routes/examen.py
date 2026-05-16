"""Rachunek Sumienia (Daily Examen) — Sancta Nexus.

Ignacjański Rachunek Sumienia w 5 krokach:
  1. Wdzięczność   — Dziękuj za łaski dnia
  2. Prośba        — Proś o światło Ducha Świętego
  3. Przegląd      — Przejrzyj dzień godzina po godzinie
  4. Odpowiedź     — Żal za grzechy, radość z łask
  5. Postanowienie — Konkretne na jutro

Zasady prywatności:
- Treść rachunku jest prywatna i nie jest przechowywana dłużej niż czas sesji Redis (24h).
- Zapis do dziennika wymaga jawnej decyzji użytkownika.
- AI jest asystentem refleksji — NIE spowiednikiem, NIE sędzią sumienia.

Endpoints:
    POST /examen/start          — Rozpocznij sesję rachunku sumienia
    POST /examen/step           — Prześlij refleksję nad krokiem, otrzymaj prowadzenie
    POST /examen/complete       — Zakończ i opcjonalnie zapisz do dziennika
    GET  /examen/session/{id}   — Stan bieżącej sesji
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession, RedisDep
from app.core.rbac import require_authenticated
from app.models.database import JournalEntry, User
from app.services.cache.session_store import SessionStore

logger = logging.getLogger(__name__)
router = APIRouter()

DISCLAIMER = (
    "Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy. "
    "Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty."
)

EXAMEN_PHASES = ["gratitude", "petition", "review", "response", "resolution"]

PHASE_META = {
    "gratitude": {
        "title": "Wdzięczność",
        "subtitle": "Dziękuj za łaski tego dnia",
        "icon": "🙏",
        "prompt_intro": (
            "Zatrzymaj się w ciszy. Pomyśl o dzisiejszym dniu. "
            "Za co jesteś wdzięczny? Co dobrego się wydarzyło — może coś małego, "
            "czego łatwo nie zauważyć? Zapisz te myśli."
        ),
    },
    "petition": {
        "title": "Prośba o światło",
        "subtitle": "Proś Ducha Świętego o jasność widzenia",
        "icon": "✨",
        "prompt_intro": (
            "Przed przeglądem dnia poproś Boga o łaskę szczerego widzenia. "
            "Chcesz widzieć siebie tak, jak widzi Cię On — z miłością, ale wyraźnie. "
            "Co chciałbyś, żeby dziś było widoczne?"
        ),
    },
    "review": {
        "title": "Przegląd dnia",
        "subtitle": "Wróć do dnia — godzina po godzinie",
        "icon": "🔍",
        "prompt_intro": (
            "Wróć do rana. Jak się obudziłeś? Jak minęły kolejne godziny? "
            "Nie oceniaj — obserwuj. Gdzie czułeś pokój? Gdzie niepokój? "
            "Gdzie był Bóg, a gdzie Go nie zauważyłeś?"
        ),
    },
    "response": {
        "title": "Odpowiedź serca",
        "subtitle": "Żal, radość, przeproszenie",
        "icon": "❤️",
        "prompt_intro": (
            "Po przeglądzie dnia — co czujesz? "
            "Jeśli jest coś, za co chcesz przeprosić Boga, powiedz Mu to po prostu. "
            "Jeśli jest radość — wyraź ją. Bogu nie chodzi o formułki, ale o serce."
        ),
    },
    "resolution": {
        "title": "Postanowienie na jutro",
        "subtitle": "Jeden konkretny krok naprzód",
        "icon": "🌅",
        "prompt_intro": (
            "Patrząc na jutro — co jedno, konkretne postanowienie chcesz wziąć? "
            "Nie wielki plan, ale jeden mały krok w dobrą stronę. "
            "Powierz jutrzejszy dzień Bogu i zakończ modlitwą."
        ),
    },
}


# ── Request / Response schemas ─────────────────────────────────────────────────


class StartExamenRequest(BaseModel):
    intention: str | None = Field(default=None, max_length=300, description="Intencja na ten Rachunek Sumienia")


class StartExamenResponse(BaseModel):
    session_id: str
    current_phase: str
    phase_meta: dict[str, Any]
    disclaimer: str


class StepRequest(BaseModel):
    session_id: str
    reflection: str = Field(..., min_length=1, max_length=2000, description="Twoja refleksja nad tym krokiem")


class StepResponse(BaseModel):
    session_id: str
    phase_completed: str
    ai_response: str
    next_phase: str | None
    next_phase_meta: dict[str, Any] | None
    is_final: bool
    disclaimer: str


class CompleteRequest(BaseModel):
    session_id: str
    save_to_journal: bool = Field(default=False, description="Czy zapisać Rachunek do dziennika duchowego?")


class CompleteResponse(BaseModel):
    session_id: str
    summary: str
    journal_entry_id: str | None
    message: str
    disclaimer: str


class ExamenSessionResponse(BaseModel):
    session_id: str
    current_phase: str
    phases_completed: list[str]
    started_at: str
    disclaimer: str


# ── System prompt dla AI ───────────────────────────────────────────────────────

_EXAMEN_SYSTEM_PROMPT = (
    "Jesteś towarzyszem modlitwy prowadzącym przez Rachunek Sumienia w tradycji ignacjańskiej.\n\n"
    "TWOJA ROLA:\n"
    "- Pomagasz osobie reflektować nad jej dniem w świetle Ewangelii.\n"
    "- Zauważasz pocieszenia (consolatio) i strapienia (desolatio) w słowach osoby.\n"
    "- Zadajesz jedno lub dwa pytania pogłębiające, nie przytłaczając.\n"
    "- Wskazujesz obecność lub nieobecność Boga w codziennych zdarzeniach.\n\n"
    "CZYM NIE JESTEŚ:\n"
    "- Nie jesteś spowiednikiem — nie oceniasz grzechów, nie udzielasz rozgrzeszenia.\n"
    "- Nie diagnozujesz psychicznie ani medycznie.\n"
    "- Nie wydajesz wyroków na temat stanu łaski.\n\n"
    "STYL:\n"
    "- Odpowiadaj w języku polskim, ciepło i spokojnie.\n"
    "- Krótko (3-5 zdań) — Rachunek Sumienia to modlitwa, nie wykład.\n"
    "- Zakończ odpowiedź jednym pytaniem do dalszej refleksji lub zachętą do modlitwy.\n"
    "- Jeśli osoba wyraża ból lub kryzys — skieruj do realnego wsparcia: kapłana, duszpasterza.\n"
)


async def _get_ai_response(phase: str, reflection: str) -> str:
    """Generuje odpowiedź AI dla danego kroku Rachunku Sumienia."""
    try:
        from app.core.llm import get_llm_client
        from app.core.safety import AISafetyLayer

        safety = AISafetyLayer()
        check = await safety.check(reflection)
        if check.blocked:
            return (
                "Zauważam, że to, co piszesz, może być bardzo trudne. "
                "Zachęcam Cię do rozmowy z kapłanem lub duszpasterzem. "
                "Jesteś ważny/ważna — proszę, szukaj wsparcia u prawdziwego człowieka."
            )

        llm = get_llm_client()
        phase_meta = PHASE_META[phase]

        messages = [
            {"role": "system", "content": _EXAMEN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Krok: {phase_meta['title']}\n\n"
                    f"Refleksja osoby:\n{reflection}\n\n"
                    "Odpowiedz jako towarzysz modlitwy."
                ),
            },
        ]

        response = await llm.chat(messages, temperature=0.7, max_tokens=400)
        return response.content
    except Exception:
        logger.warning("AI unavailable for examen step=%s; returning default", phase)
        return (
            "Dziękuję za tę refleksję. "
            "Trwaj chwilę w ciszy z tym, co napisałeś/napisałaś. "
            "Pozwól Bogu działać w tym, co odkryłeś/odkryłaś."
        )


# ── POST /examen/start ─────────────────────────────────────────────────────────


@router.post(
    "/start",
    response_model=StartExamenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rozpocznij Rachunek Sumienia",
)
async def start_examen(
    body: StartExamenRequest,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> StartExamenResponse:
    """Tworzy sesję Rachunku Sumienia w Redis (ważna 24h)."""
    session_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    session_data = {
        "session_id": session_id,
        "user_id": current_user.id,
        "started_at": now.isoformat(),
        "current_phase": "gratitude",
        "phases_completed": [],
        "reflections": {},
        "ai_responses": {},
        "intention": body.intention or "",
    }

    store = SessionStore(redis, namespace="examen")
    await store.create(session_id, session_data)

    logger.info("Examen session started: %s for user %s", session_id, current_user.id)

    return StartExamenResponse(
        session_id=session_id,
        current_phase="gratitude",
        phase_meta=PHASE_META["gratitude"],
        disclaimer=DISCLAIMER,
    )


# ── POST /examen/step ─────────────────────────────────────────────────────────


@router.post(
    "/step",
    response_model=StepResponse,
    summary="Prześlij refleksję i przejdź do następnego kroku",
)
async def submit_examen_step(
    body: StepRequest,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> StepResponse:
    """Przyjmuje refleksję nad bieżącym krokiem, zwraca odpowiedź AI i metadane następnego kroku."""
    store = SessionStore(redis, namespace="examen")
    session = await store.get(body.session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesja nie istnieje lub wygasła.")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="To nie jest Twoja sesja.")

    current_phase = session["current_phase"]
    if current_phase not in EXAMEN_PHASES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wszystkie kroki zostały już ukończone.")

    # Generuj odpowiedź AI
    ai_response = await _get_ai_response(current_phase, body.reflection)

    # Zapisz refleksję i odpowiedź
    session["reflections"][current_phase] = body.reflection
    session["ai_responses"][current_phase] = ai_response

    # Zaznacz krok jako ukończony
    if current_phase not in session["phases_completed"]:
        session["phases_completed"].append(current_phase)

    # Wyznacz następny krok
    current_idx = EXAMEN_PHASES.index(current_phase)
    next_phase = EXAMEN_PHASES[current_idx + 1] if current_idx + 1 < len(EXAMEN_PHASES) else None
    is_final = next_phase is None

    session["current_phase"] = next_phase or "completed"
    await store.update(body.session_id, session)

    return StepResponse(
        session_id=body.session_id,
        phase_completed=current_phase,
        ai_response=ai_response,
        next_phase=next_phase,
        next_phase_meta=PHASE_META[next_phase] if next_phase else None,
        is_final=is_final,
        disclaimer=DISCLAIMER,
    )


# ── POST /examen/complete ─────────────────────────────────────────────────────


@router.post(
    "/complete",
    response_model=CompleteResponse,
    summary="Zakończ Rachunek Sumienia i opcjonalnie zapisz do dziennika",
)
async def complete_examen(
    body: CompleteRequest,
    redis: RedisDep,
    db: DbSession,
    current_user: User = require_authenticated,
) -> CompleteResponse:
    """Finalizuje sesję. Jeśli save_to_journal=True, tworzy wpis w dzienniku duchowym."""
    store = SessionStore(redis, namespace="examen")
    session = await store.get(body.session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesja nie istnieje lub wygasła.")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="To nie jest Twoja sesja.")

    reflections = session.get("reflections", {})

    # Buduj podsumowanie z refleksji
    summary_parts = []
    for phase in EXAMEN_PHASES:
        if phase in reflections:
            meta = PHASE_META[phase]
            summary_parts.append(f"**{meta['title']}**: {reflections[phase][:200]}")

    reflections.get("resolution", "")
    summary = "\n\n".join(summary_parts) if summary_parts else "Rachunek Sumienia zakończony."

    journal_entry_id: str | None = None

    if body.save_to_journal and summary_parts:
        content = (
            f"Rachunek Sumienia — {datetime.now(UTC).strftime('%d.%m.%Y')}\n\n"
            + "\n\n".join(summary_parts)
        )
        if session.get("intention"):
            content = f"Intencja: {session['intention']}\n\n" + content

        entry = JournalEntry(
            user_id=current_user.id,
            title=f"Rachunek Sumienia — {datetime.now(UTC).strftime('%d.%m.%Y')}",
            content=content,
            tags="rachunek-sumienia,examen",
            mood="spokój",
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        journal_entry_id = entry.id
        logger.info("Examen saved to journal: entry=%s user=%s", entry.id, current_user.id)

    # Oznacz sesję jako zakończoną
    session["status"] = "completed"
    session["completed_at"] = datetime.now(UTC).isoformat()
    await store.update(body.session_id, session)

    message = (
        "Rachunek Sumienia zakończony. Zapisany do dziennika."
        if journal_entry_id
        else "Rachunek Sumienia zakończony."
    )

    return CompleteResponse(
        session_id=body.session_id,
        summary=summary,
        journal_entry_id=journal_entry_id,
        message=message,
        disclaimer=DISCLAIMER,
    )


# ── GET /examen/session/{id} ──────────────────────────────────────────────────


@router.get(
    "/session/{session_id}",
    response_model=ExamenSessionResponse,
    summary="Stan bieżącej sesji Rachunku Sumienia",
)
async def get_examen_session(
    session_id: str,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> ExamenSessionResponse:
    """Zwraca aktualny stan sesji (przydatne przy odświeżeniu strony)."""
    store = SessionStore(redis, namespace="examen")
    session = await store.get(session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesja nie istnieje lub wygasła.")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="To nie jest Twoja sesja.")

    return ExamenSessionResponse(
        session_id=session_id,
        current_phase=session.get("current_phase", "gratitude"),
        phases_completed=session.get("phases_completed", []),
        started_at=session.get("started_at", ""),
        disclaimer=DISCLAIMER,
    )
