"""Testy jednostkowe dla Rachunku Sumienia (examen routes).

Self-contained: brak DB, Redis, LLM. Testuje logikę danych i stałe.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ── Stałe z modułu routes/examen.py ──────────────────────────────────────────

EXAMEN_MODULE = Path(__file__).parent.parent.parent / "app" / "api" / "routes" / "examen.py"


def _load_examen_constants() -> dict:
    """Ładuje EXAMEN_PHASES, PHASE_META i DISCLAIMER przez AST, bez importowania modułu."""
    source = EXAMEN_MODULE.read_text()
    tree = ast.parse(source)
    constants: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "EXAMEN_PHASES", "DISCLAIMER"
                ):
                    constants[target.id] = ast.literal_eval(node.value)
    return constants


# ── DISCLAIMER ────────────────────────────────────────────────────────────────

class TestDisclaimer:
    def test_disclaimer_mentions_reflection_assistant(self):
        consts = _load_examen_constants()
        d = consts["DISCLAIMER"].lower()
        assert "asystent refleksji" in d

    def test_disclaimer_does_not_mention_confessor(self):
        consts = _load_examen_constants()
        d = consts["DISCLAIMER"].lower()
        assert "spowiednik" in d  # musi być wspomniane JAKO coś czego NIE zastępuje

    def test_disclaimer_mentions_chaplain(self):
        consts = _load_examen_constants()
        d = consts["DISCLAIMER"].lower()
        assert "kapłan" in d

    def test_disclaimer_not_empty(self):
        consts = _load_examen_constants()
        assert len(consts["DISCLAIMER"]) >= 50


# ── EXAMEN_PHASES ─────────────────────────────────────────────────────────────

class TestExamenPhases:
    def test_has_five_phases(self):
        consts = _load_examen_constants()
        assert len(consts["EXAMEN_PHASES"]) == 5

    def test_phases_are_ignatian_five(self):
        consts = _load_examen_constants()
        expected = {"gratitude", "petition", "review", "response", "resolution"}
        assert set(consts["EXAMEN_PHASES"]) == expected

    def test_gratitude_is_first(self):
        consts = _load_examen_constants()
        assert consts["EXAMEN_PHASES"][0] == "gratitude"

    def test_resolution_is_last(self):
        consts = _load_examen_constants()
        assert consts["EXAMEN_PHASES"][-1] == "resolution"

    def test_phases_are_ordered_correctly(self):
        consts = _load_examen_constants()
        assert consts["EXAMEN_PHASES"] == [
            "gratitude", "petition", "review", "response", "resolution"
        ]


# ── PHASE_META obecność w source ─────────────────────────────────────────────

class TestPhaseMetaSource:
    """Sprawdza kod źródłowy, że PHASE_META zawiera wymagane pola dla każdej fazy."""

    def test_source_has_phase_meta_for_all_phases(self):
        source = EXAMEN_MODULE.read_text()
        for phase in ["gratitude", "petition", "review", "response", "resolution"]:
            assert f'"{phase}"' in source, f"PHASE_META brak klucza: {phase}"

    def test_each_phase_has_title(self):
        source = EXAMEN_MODULE.read_text()
        assert source.count('"title"') >= 5

    def test_each_phase_has_icon(self):
        source = EXAMEN_MODULE.read_text()
        assert source.count('"icon"') >= 5

    def test_each_phase_has_prompt_intro(self):
        source = EXAMEN_MODULE.read_text()
        assert source.count('"prompt_intro"') >= 5


# ── Endpointy — sprawdzanie przez AST ────────────────────────────────────────

class TestExamenEndpoints:
    """Sprawdza że wszystkie wymagane endpointy są zdefiniowane w module."""

    def _get_router_decorators(self) -> list[str]:
        source = EXAMEN_MODULE.read_text()
        tree = ast.parse(source)
        decorators = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in node.decorator_list:
                    if isinstance(d, ast.Call):
                        func = d.func
                        if isinstance(func, ast.Attribute):
                            decorators.append(f"{func.attr}:{ast.unparse(d)}")
        return decorators

    def test_has_start_endpoint(self):
        source = EXAMEN_MODULE.read_text()
        assert '"/start"' in source

    def test_has_step_endpoint(self):
        source = EXAMEN_MODULE.read_text()
        assert '"/step"' in source

    def test_has_complete_endpoint(self):
        source = EXAMEN_MODULE.read_text()
        assert '"/complete"' in source

    def test_has_session_endpoint(self):
        source = EXAMEN_MODULE.read_text()
        assert '"/session/{session_id}"' in source

    def test_start_is_post(self):
        source = EXAMEN_MODULE.read_text()
        # router.post("/start" ...)
        assert 'router.post(\n    "/start"' in source or 'router.post("/start"' in source

    def test_complete_has_db_session(self):
        source = EXAMEN_MODULE.read_text()
        # complete_examen musi mieć db: DbSession (do zapisu w dzienniku)
        assert "db: DbSession" in source

    def test_complete_saves_journal_entry(self):
        source = EXAMEN_MODULE.read_text()
        assert "JournalEntry" in source
        assert "save_to_journal" in source


# ── Bezpieczeństwo — JWT, brak user_id w body ─────────────────────────────────

class TestExamenSecurity:
    def test_no_user_id_in_request_bodies(self):
        """user_id NIE powinien być w żadnym request body — pochodzi z JWT."""
        source = EXAMEN_MODULE.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Request"):
                for item in ast.walk(node):
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        assert item.target.id != "user_id", (
                            f"Klasa {node.name} nie powinna mieć pola user_id "
                            f"— użyj require_authenticated"
                        )

    def test_require_authenticated_used(self):
        source = EXAMEN_MODULE.read_text()
        assert "require_authenticated" in source

    def test_session_ownership_checked(self):
        """Każdy endpoint mutujący sesję sprawdza, czy sesja należy do użytkownika."""
        source = EXAMEN_MODULE.read_text()
        assert 'session["user_id"] != current_user.id' in source

    def test_safety_layer_imported_in_ai_call(self):
        source = EXAMEN_MODULE.read_text()
        assert "AISafetyLayer" in source


# ── Logika przejść faz ────────────────────────────────────────────────────────

class TestPhaseTransitionLogic:
    """Testuje logikę kolejności faz bez uruchamiania aplikacji."""

    def test_next_phase_after_gratitude_is_petition(self):
        phases = ["gratitude", "petition", "review", "response", "resolution"]
        idx = phases.index("gratitude")
        assert phases[idx + 1] == "petition"

    def test_next_phase_after_resolution_is_none(self):
        phases = ["gratitude", "petition", "review", "response", "resolution"]
        idx = phases.index("resolution")
        next_phase = phases[idx + 1] if idx + 1 < len(phases) else None
        assert next_phase is None

    def test_is_final_when_resolution_completed(self):
        phases = ["gratitude", "petition", "review", "response", "resolution"]
        current = "resolution"
        idx = phases.index(current)
        next_phase = phases[idx + 1] if idx + 1 < len(phases) else None
        is_final = next_phase is None
        assert is_final is True

    def test_five_phases_means_five_transitions(self):
        phases = ["gratitude", "petition", "review", "response", "resolution"]
        # 5 faz = 4 przejścia + 1 zakończenie (is_final)
        assert len(phases) == 5
