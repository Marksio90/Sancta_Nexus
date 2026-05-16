.PHONY: help dev dev-stop test test-unit test-integration lint fmt check build push logs health

COMPOSE_DEV  = docker compose -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -f docker-compose.prod.yml

help:
	@echo "Sancta Nexus — dostępne komendy:"
	@echo ""
	@echo "  make dev          Uruchom infrastrukturę deweloperską (Postgres + Redis)"
	@echo "  make dev-stop     Zatrzymaj infrastrukturę deweloperską"
	@echo "  make test         Uruchom wszystkie testy jednostkowe"
	@echo "  make test-unit    Testy jednostkowe"
	@echo "  make test-int     Testy integracyjne"
	@echo "  make lint         Sprawdź styl kodu (ruff)"
	@echo "  make fmt          Automatyczne formatowanie (ruff format)"
	@echo "  make check        lint + typecheck frontend"
	@echo "  make build        Zbuduj obrazy produkcyjne"
	@echo "  make logs         Pokaż logi produkcyjne (tail -f)"
	@echo "  make health       Sprawdź stan usług produkcyjnych"

# ── Infrastruktura deweloperska ───────────────────────────────────────────────

dev:
	$(COMPOSE_DEV) up -d
	@echo "Postgres dostępny na :5432, Redis na :6379"
	@echo "Uruchom backend: cd backend && uvicorn app.main:app --reload --port 8000"

dev-stop:
	$(COMPOSE_DEV) down

# ── Testy ─────────────────────────────────────────────────────────────────────

test: test-unit

test-unit:
	cd backend && python -m pytest tests/unit/ -q

test-integration:
	cd backend && python -m pytest tests/integration/ -v

test-watch:
	cd backend && python -m pytest tests/unit/ -q -f

# ── Jakość kodu ───────────────────────────────────────────────────────────────

lint:
	cd backend && ruff check .

fmt:
	cd backend && ruff format .

fmt-check:
	cd backend && ruff format --check .

check: lint fmt-check
	cd frontend && npx tsc --noEmit

# ── Produkcja ─────────────────────────────────────────────────────────────────

build:
	$(COMPOSE_PROD) build --no-cache

up:
	$(COMPOSE_PROD) up -d

down:
	$(COMPOSE_PROD) down

logs:
	$(COMPOSE_PROD) logs -f --tail=100

health:
	@echo "=== Backend ===" && curl -sf http://localhost/health | python3 -m json.tool || echo "FAIL"
	@echo "=== Nginx ===" && curl -sf http://localhost/ -o /dev/null -w "%{http_code}\n" || echo "FAIL"

ssl-init:
	$(COMPOSE_PROD) --profile certbot run --rm certbot
	$(COMPOSE_PROD) exec nginx nginx -s reload

# ── Baza danych ───────────────────────────────────────────────────────────────

migrate:
	cd backend && alembic upgrade head

migrate-new:
	@read -p "Nazwa migracji: " name; \
	cd backend && alembic revision --autogenerate -m "$$name"

db-shell:
	$(COMPOSE_DEV) exec postgres psql -U sancta -d sancta_nexus_dev
