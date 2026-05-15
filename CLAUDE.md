# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Mission constraint (non-negotiable)

Sancta Nexus is **not** an AI priest, confessor, or spiritual director. The AI is a *reflection assistant*. It never:
- Pretends to be a priest or grants absolution
- Evaluates a user's state of grace or diagnoses sin
- Replaces therapy or crisis services
- Issues moral judgements on specific acts

Every AI-generated response page **must** display the disclaimer:
> *Asystent refleksji pomaga uporządkować myśli i wrócić do modlitwy. Nie zastępuje kapłana, spowiednika, kierownika duchowego ani terapeuty.*

**Never put `user_id` in request bodies or path parameters.** Identity always comes from the JWT via `require_authenticated`.

---

## Commands

### Backend (run from `backend/`)

```bash
# Dev infrastructure (Postgres + Redis only — no Neo4j / Qdrant overhead)
docker compose -f ../docker-compose.dev.yml up -d

# Run the API server
uvicorn app.main:app --reload --port 8000

# All unit tests (skip rbac test — broken cffi in local env)
python -m pytest tests/unit/ -q --ignore=tests/unit/test_rbac.py

# Single test file
python -m pytest tests/unit/test_safety.py -v

# Single test class or function
python -m pytest tests/unit/test_safety.py::TestClassifyInput::test_detects_crisis_polish -v

# Integration tests (no infra needed — self-contained)
python -m pytest tests/integration/test_safety_critical.py -v

# Lint
ruff check .
ruff format --check .
ruff format .           # auto-fix formatting
```

### Frontend (run from `frontend/`)

```bash
npm run dev             # Next.js dev server on :3000
npx tsc --noEmit        # TypeScript check (must be zero errors before commit)
npm run lint            # ESLint
npm run build           # Production build
```

### Mobile (Capacitor)
```bash
npm run build:mobile    # Build + cap sync
npm run cap:ios         # Open Xcode
npm run cap:android     # Open Android Studio
```

---

## Architecture

### Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16
- **Sessions**: Redis 7 (24 h TTL; `SessionStore` wrapper in `app/services/cache/session_store.py`)
- **AI**: LangChain + LangGraph; optional Qdrant (RAG) + Neo4j (memory graph)
- **Frontend**: Next.js 15 App Router, React 19, TypeScript, Tailwind v4, Zustand

### Backend layout

```
backend/app/
├── core/
│   ├── llm.py          # LLM factory — ALWAYS use this, never import langchain_openai directly
│   ├── safety.py       # AISafetyLayer — 5-stage pipeline, mandatory for every AI call
│   ├── rbac.py         # require_authenticated, require_admin, require_role()
│   ├── dependencies.py # FastAPI DI: DbSession, RedisDep, QdrantDep, Neo4jDep
│   ├── config.py       # Settings (pydantic-settings, reads from .env)
│   └── feature_flags.py
├── api/routes/         # One file = one module; registered lazily in main.py _ROUTERS list
├── agents/             # LangGraph agents, grouped by domain
│   ├── lectio_divina/  # LangGraph StateGraph (A-002): emotion→scripture→lectio→meditatio→oratio→contemplatio→actio
│   ├── memory/         # JourneyTrackerAgent (A-036), PatternDiscoveryAgent (A-037)
│   ├── emotion/        # EmotionDetectorAgent, SpiritualStateClassifier, CrisisDetectorAgent
│   ├── generative/     # PrayerGeneratorAgent
│   ├── theology/       # ExegesisAgent, DoctrineGuardAgent
│   ├── orchestration/
│   └── spiritual_director/  # IgnatianDiscernmentAgent (A-043), DirectorOrchestrator
├── services/           # Business logic; agents are called from here or from routes
└── models/database.py  # All ORM models (SQLAlchemy 2.0 mapped_column style)
```

### Key patterns

**LLM factory** — never import `ChatOpenAI` / `ChatAnthropic` directly in agent files:
```python
def __init__(self) -> None:
    from app.core.llm import get_llm_fast   # lazy import inside __init__
    self.llm = get_llm_fast(temperature=0.3)
```
Use `get_llm()` (primary), `get_llm_fast()` (cheaper/faster), `get_llm_creative()` (temperature≈0.9), or `get_llm_client()` (returns `LLMClientAdapter` with `.chat(messages, ...)` interface, needed by agents that take a raw client).

**Safety layer** — wrap every AI call:
```python
from app.core.safety import AISafetyLayer
safety = AISafetyLayer()
check = await safety.check(user_text)
if check.blocked:
    return CRISIS_RESPONSE
```

**Route registration** — add new route files to `_ROUTERS` in `app/main.py`:
```python
("app.api.routes.my_module", "/api/v1/my-module", ["my-module"]),
```
Imports are deferred; a missing module is silently skipped at startup.

**Session data** (Redis) — use `SessionStore`:
```python
store = SessionStore(redis, namespace="myfeature")
await store.create(session_id, data)      # sets 24h TTL
session = await store.get(session_id)
await store.update(session_id, session)
```

**Dependency shortcuts** (use these in route signatures):
```python
db: DbSession           # AsyncSession, auto-commit/rollback
redis: RedisDep         # aioredis.Redis
qdrant: QdrantDep
neo4j: Neo4jDep
current_user: User = require_authenticated
admin: User = require_admin
```

**Auth guard** — `require_authenticated` is a FastAPI `Depends` used as a default parameter value. Do not call it as a function.

### Frontend layout

```
frontend/src/
├── app/                # Next.js App Router pages (one folder = one route)
├── components/
│   ├── layout/         # Header
│   └── mobile/         # BottomNav (5 primary links, mobile-only)
├── stores/             # Zustand stores: auth, journal, lectio, reflection, insights, progress
└── lib/
    ├── api.ts          # Central HTTP client: api.get/post/put/delete
    │                   # Reads JWT from localStorage, auto-refreshes on 401
    └── notifications.ts
```

**API calls** — always use `src/lib/api.ts`, never raw `fetch` in pages/stores:
```typescript
const data = await api.post<MyResponse>("/api/v1/my-route", { field: value });
```
The client reads the JWT from `localStorage.token` and sets `Authorization: Bearer ...` automatically.

**Zustand stores** — one store per domain. Each store is `create<State & Actions>()`. Stores call `api.*` for all backend communication.

---

## Database models (key entities)

| Model | Purpose |
|---|---|
| `User` | Auth + role + subscription tier + soft-delete |
| `UserPrivacySettings` | `ai_can_read_journal` gate (checked before any AI journal analysis) |
| `JournalEntry` | Private spiritual diary; soft-deleted via `deleted_at` |
| `Session` | Completed Lectio Divina / spiritual direction sessions |
| `Prayer`, `ScriptureEncounter` | Artefacts from sessions |
| `PrayerIntention` | Community intentions; moderated via `IntentionStatus` |
| `PrayerGroup`, `PrayerGroupMembership` | Community groups |
| `CommunityRosary`, `RosaryParticipation` | Shared rosary sessions |
| `NovenaTracking` | Per-user novena progress |
| `FavoritePassage` | Saved scripture |
| `AuditLog` | All sensitive actions (role changes, deletions, moderation) |
| `AiInteraction` | Safety metadata per AI call (no message content stored) |

All PKs are UUID strings. Timestamps are timezone-aware UTC. Use `alembic` for schema migrations in production; `create_tables()` in `dependencies.py` handles dev/test.

---

## Testing conventions

All unit tests are **self-contained** — no real DB, Redis, Qdrant, or LLM. Preferred patterns:
- **AST inspection** for checking source-level contracts (no `user_id` in request bodies, disclaimer present, `require_authenticated` used)
- **`unittest.mock.AsyncMock` + `patch`** for agent/service tests
- **Mock target = source module**, not consumer: patch `app.core.llm.get_llm_fast`, not `app.agents.memory.journey_tracker.get_llm_fast`

`test_rbac.py` is excluded locally (`--ignore`) because `python-jose`'s `cffi` backend is broken in this environment; it passes in CI where the full dep set is installed.

Integration tests in `tests/integration/` stub heavy deps inline and test the full pipeline logic without infrastructure.

---

## AI Safety layer details

`app/core/safety.py` — five stages, called via `AISafetyLayer`:
1. **classify_input** — regex + keyword heuristics → `RiskCategory`
2. **detect_crisis** — flags `CRISIS` / `SELF_HARM_RISK` immediately
3. **validate_response** — checks generated text against policy
4. **apply_disclaimer** — appends mandatory disclaimer
5. **rewrite_if_needed** — replaces responses that impersonate a priest/confessor

`HIGH_RISK_CATEGORIES` = `{CRISIS, SELF_HARM_RISK, ABUSE_RISK, MEDICAL_OR_PSYCHOLOGICAL, CONFESSION_RELATED}` — these are blocked and redirected to real human support.

Polish morphology requires `\w*` suffix patterns (e.g. `r"\bdepresj\w+\b"` covers depresja/depresję/depresją).

---

## Feature flags

Each module has a `FEATURE_*` env var (e.g. `FEATURE_LECTIO_DIVINA=true`). Check `app/core/feature_flags.py`. Modules are registered regardless of flag state; the flag gates actual functionality at the service level.
