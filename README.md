# Sancta Nexus

Katolicka platforma modlitwy i formacji duchowej.

Sancta Nexus pomaga użytkownikowi codziennie modlić się Słowem Bożym, prowadzić dziennik duchowy, przechodzić przez programy rekolekcyjne, zapisywać intencje i korzystać z bezpiecznego Asystenta refleksji.

> **Platforma nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.** Jej celem jest wspieranie regularnej modlitwy, refleksji i życia duchowego w oparciu o zatwierdzone treści oraz odpowiedzialne użycie AI.

---

## Czym NIE jest Sancta Nexus

- Nie jest AI-kierownikiem duchowym
- Nie jest AI-spowiednikiem ani AI-ksiądzem
- Nie zastępuje spowiedzi, sakramentów ani realnej wspólnoty
- Nie rozstrzyga o stanie łaski, grzechu ciężkim ani woli Bożej wobec użytkownika

---

## Stack technologiczny

| Warstwa | Technologia |
|---|---|
| Backend API | FastAPI (Python 3.12) |
| Frontend | Next.js 15 (React 19, TypeScript) |
| Baza relacyjna | PostgreSQL 16 |
| Cache / sesje | Redis 7 |
| Wektory (RAG) | Qdrant |
| Graf pamięci | Neo4j 5 |
| Orchestracja AI | LangChain + LangGraph |
| Konteneryzacja | Docker + Docker Compose |
| Migracje DB | Alembic |

---

## Moduły platformy

| Moduł | Nazwa produktowa | Status |
|---|---|---|
| `lectio-divina` | Lectio Divina | **stable** |
| `bible` | Biblia interaktywna | **stable** |
| `prayer-journal` | Dziennik duchowy | **beta** |
| `reflection-assistant` | Asystent refleksji | **experimental** |
| `breviary` | Liturgia Godzin | **beta** |
| `prayer-intentions` | Intencje modlitewne | **experimental** |
| `communities` | Wspólnoty | **planned** |
| `retreat-programs` | Programy rekolekcyjne | **planned** |
| `sacramental-prep` | Przewodnik przygotowania | **experimental** |
| `spiritual-dashboard` | Panel duchowy | **planned** |
| `content-library` | Biblioteka duchowa | **planned** |
| `examination-of-conscience` | Pomocnik rachunku sumienia | **planned** |
| `discernment-notebook` | Notatnik rozeznawania | **planned** |

Cykl statusów: `planned` → `experimental` → `beta` → `stable` → `disabled`

Moduły `experimental` i `planned` są dostępne tylko dla administratorów. Każdy moduł ma feature flag i może być wyłączony bez wpływu na resztę aplikacji.

---

## Szybki start

### Wymagania

- Docker Desktop (lub Docker Engine + Docker Compose v2)
- Klucz API OpenAI lub Anthropic

### Uruchomienie lokalne

```bash
# 1. Skopiuj zmienne środowiskowe
cp .env.example .env

# 2. Uzupełnij obowiązkowe wartości w .env:
#    - OPENAI_API_KEY lub ANTHROPIC_API_KEY
#    - SECRET_KEY (zmień na losowy ciąg)
#    - POSTGRES_PASSWORD
#    - NEO4J_PASSWORD

# 3. Uruchom wszystkie usługi
docker compose up -d

# 4. Sprawdź status
docker compose ps

# Backend:  http://localhost:8000
# Swagger:  http://localhost:8000/docs
# Frontend: http://localhost:3000
```

### Kluczowe zmienne środowiskowe

| Zmienna | Opis | Wymagana |
|---|---|---|
| `OPENAI_API_KEY` | Klucz OpenAI | Tak (lub Anthropic) |
| `ANTHROPIC_API_KEY` | Klucz Anthropic | Opcjonalnie |
| `SECRET_KEY` | Klucz JWT — zmień w produkcji! | Tak |
| `POSTGRES_PASSWORD` | Hasło bazy danych | Tak |
| `NEO4J_PASSWORD` | Hasło Neo4j | Tak |

### Feature flags

Każdy moduł można włączyć lub wyłączyć zmienną środowiskową:

```env
FEATURE_LECTIO_DIVINA=true
FEATURE_BIBLE=true
FEATURE_PRAYER_JOURNAL=true
FEATURE_REFLECTION_ASSISTANT=true
FEATURE_BREVIARY=true
FEATURE_PRAYER_INTENTIONS=false
FEATURE_COMMUNITIES=false
FEATURE_RETREAT_PROGRAMS=false
FEATURE_SACRAMENTAL_PREP=false
FEATURE_SPIRITUAL_DASHBOARD=false
FEATURE_CONTENT_LIBRARY=false
FEATURE_EXAMINATION_OF_CONSCIENCE=false
FEATURE_DISCERNMENT_NOTEBOOK=false
FEATURE_VOICE=false
FEATURE_NOTIFICATIONS=true
```

---

## Bezpieczeństwo AI

Każda interakcja z AI przechodzi przez warstwę bezpieczeństwa:

1. **Klasyfikacja kategorii** — refleksja / pytanie moralne / kryzys / ryzyko
2. **Detekcja ryzyka** — kryzysy emocjonalne, pytania sakramentalne, ryzyko samookaleczenia
3. **Grounding** — odpowiedzi bazują na zatwierdzonych źródłach (Pismo, KKK, rozważania redakcyjne)
4. **Walidacja odpowiedzi** — sprawdzenie przed wysłaniem do użytkownika
5. **Rewrite przy przekroczeniu granic** — AI odsyła do realnej osoby

Zasady AI: [`docs/safety/ai-safety-policy.md`](docs/safety/ai-safety-policy.md)
Granice teologiczne: [`docs/safety/theological-boundaries.md`](docs/safety/theological-boundaries.md)

---

## Roadmapa

| Faza | Cel | Status |
|---|---|---|
| Phase 1 | Stabilizacja repo, feature flags, safety layer, bezpieczne nazwy | **W toku** |
| Phase 2 | Core Platform: auth, role, audit logs, prywatność danych | Planowana |
| Phase 3 | Lectio Divina + Dziennik duchowy (pełne flow) | Planowana |
| Phase 4 | Biblia + Biblioteka treści + RAG grounding | Planowana |
| Phase 5 | Programy rekolekcyjne + panel redakcyjny | Planowana |
| Phase 6 | Intencje + Wspólnoty + B2B | Planowana |
| Phase 7 | Moduły wrażliwe (rachunek sumienia, rozeznawanie) | Planowana |
| Phase 8 | Monetyzacja (premium, subskrypcje, organizacje) | Planowana |

---

## Struktura repozytorium

```
sancta-nexus/
├── backend/
│   ├── app/
│   │   ├── core/         # Konfiguracja, JWT, feature flags, safety layer
│   │   ├── api/routes/   # Endpointy REST (jeden plik = jeden moduł)
│   │   ├── agents/       # LangGraph agenty (Lectio, refleksja, teologia)
│   │   ├── services/     # Logika biznesowa
│   │   └── models/       # Modele SQLAlchemy
│   ├── alembic/          # Migracje bazy danych
│   └── tests/            # Testy jednostkowe i integracyjne
├── frontend/
│   └── src/
│       ├── app/          # Strony Next.js (App Router)
│       ├── components/   # Komponenty wielokrotnego użytku
│       ├── stores/       # Stan globalny (Zustand)
│       └── lib/          # Narzędzia i klient API
├── docs/
│   ├── architecture/     # Opis systemu i granic modułów
│   ├── product/          # Wizja, moduły, roadmapa
│   └── safety/           # Polityka AI i granice teologiczne
└── docker-compose.yml
```

---

## Licencja

Apache License 2.0 — szczegóły w pliku [`LICENSE`](LICENSE).

---

## Disclaimer

Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy oraz Słowa Bożego. Nie zastępuje kapłana, spowiednika, kierownika duchowego, terapeuty ani pomocy kryzysowej. W sytuacji kryzysu skontaktuj się z zaufaną osobą lub telefonem zaufania.