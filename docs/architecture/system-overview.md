# Przegląd architektury systemu — Sancta Nexus

## Komponenty

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 15)                 │
│  App Router · React 19 · Zustand · Tailwind · Capacitor      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP REST / JSON
┌───────────────────────────▼─────────────────────────────────┐
│                      Backend API (FastAPI)                    │
│                                                              │
│  core/                    api/routes/                        │
│    config.py                auth · users                     │
│    security.py              lectio_divina · bible            │
│    feature_flags.py         spiritual_director (→ refl.)     │
│    safety.py                breviary · community             │
│    dependencies.py          sacraments · knowledge           │
│                             voice · notifications            │
│  agents/ (LangGraph)      services/                          │
│    lectio_divina/           knowledge/ (RAG)                 │
│    theology/                emotion/                         │
│    spiritual_director/      memory/ (Neo4j)                  │
│    emotion/                 community/                       │
│    generative/              sacraments/                      │
│    memory/                  scripture/                       │
│    orchestration/           rag/ · cache/                    │
└──────┬──────────┬──────────┬──────────────┬─────────────────┘
       │          │          │              │
  ┌────▼────┐ ┌──▼──┐ ┌─────▼──────┐ ┌───▼────┐
  │Postgres │ │Redis│ │   Qdrant   │ │ Neo4j  │
  │   16    │ │  7  │ │(wektory)   │ │(graf)  │
  └─────────┘ └─────┘ └────────────┘ └────────┘
```

## Przepływ interakcji AI

```
Użytkownik → input → AISafetyLayer.assess()
                         ↓
                  klasyfikacja kategorii
                         ↓
              [kategoria wysokiego ryzyka?]
               TAK → komunikat kryzysowy
               NIE → generacja AI (LangGraph)
                         ↓
                  AISafetyLayer.validate_response()
                         ↓
                  [naruszenie polityki?]
               TAK → rewrite / komunikat graniczny
               NIE → dodanie disclaimera
                         ↓
                    odpowiedź do użytkownika
```

## Bazy danych

| Baza | Rola |
|---|---|
| PostgreSQL | Użytkownicy, sesje, wpisy dziennika, intencje, modele relacyjne |
| Redis | Cache sesji, limity requestów, kolejka zadań |
| Qdrant | Embeddingi tekstowe dla RAG (Pismo, KKK, treści redakcyjne) |
| Neo4j | Graf pamięci duchowej — wzorce, powiązania tematyczne |

## Feature flags

Każdy moduł ma zmienną `FEATURE_<MODUŁ>=true/false` w `.env`.

FastAPI dependency `require_feature(FeatureFlags.X)` zwraca HTTP 503 gdy moduł wyłączony.

Rejestr flag: `backend/app/core/feature_flags.py`

## Struktura modułu (backend)

Każdy moduł API powinien mieć:

```
api/routes/<moduł>.py      # Endpointy FastAPI
services/<moduł>/          # Logika biznesowa
models/                    # Encje SQLAlchemy (współdzielone)
agents/<moduł>/            # Agenty LangGraph (jeśli potrzebne)
tests/unit/test_<moduł>.py
tests/integration/test_<moduł>.py
```

## Bezpieczeństwo AI

Warstwa bezpieczeństwa: `backend/app/core/safety.py`  
Polityka: `docs/safety/ai-safety-policy.md`  
Granice teologiczne: `docs/safety/theological-boundaries.md`

## Stos technologiczny — wersje

| Technologia | Wersja |
|---|---|
| Python | 3.12 |
| FastAPI | ≥ 0.110 |
| SQLAlchemy | ≥ 2.0 (async) |
| Alembic | ≥ 1.13 |
| LangChain | ≥ 0.2 |
| LangGraph | ≥ 0.1 |
| Next.js | 15 |
| React | 19 |
| TypeScript | 5.7 |
| Tailwind CSS | 4 |
| Zustand | 5 |
| PostgreSQL | 16 |
| Redis | 7 |
| Qdrant | latest |
| Neo4j | 5 |
