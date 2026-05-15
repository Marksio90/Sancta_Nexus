"""Testy jednostkowe dla modułu billing (Stripe subskrypcje).

Self-contained — bez DB, bez Stripe API, bez zewnętrznych serwisów.
AST-based checks dla bezpieczeństwa i struktury routingu.
"""

from __future__ import annotations

import ast
from pathlib import Path

BILLING_MODULE = Path(__file__).parent.parent.parent / "app" / "api" / "routes" / "billing.py"


def _source() -> str:
    return BILLING_MODULE.read_text()


def _tree() -> ast.Module:
    return ast.parse(_source())


def _func_source(name: str) -> str | None:
    for node in ast.walk(_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    return None


# ── Struktura endpointów ──────────────────────────────────────────────────────

class TestBillingEndpoints:
    def test_checkout_endpoint_exists(self):
        assert '"/checkout"' in _source()

    def test_portal_endpoint_exists(self):
        assert '"/portal"' in _source()

    def test_webhook_endpoint_exists(self):
        assert '"/webhook"' in _source()

    def test_status_endpoint_exists(self):
        assert '"/status"' in _source()

    def test_checkout_is_post(self):
        src = _source()
        assert 'router.post(\n    "/checkout"' in src or 'router.post("/checkout"' in src

    def test_status_is_get(self):
        src = _source()
        assert 'router.get("/status"' in src or 'router.get(\n    "/status"' in src

    def test_webhook_is_post(self):
        src = _source()
        assert 'router.post(\n    "/webhook"' in src or 'router.post("/webhook"' in src


# ── Bezpieczeństwo ────────────────────────────────────────────────────────────

class TestBillingSecurity:
    def test_checkout_requires_authentication(self):
        src = _func_source("create_checkout") or ""
        assert "require_authenticated" in src

    def test_portal_requires_authentication(self):
        src = _func_source("create_portal") or ""
        assert "require_authenticated" in src

    def test_status_requires_authentication(self):
        src = _func_source("get_status") or ""
        assert "require_authenticated" in src

    def test_webhook_has_no_jwt_auth(self):
        """Webhook Stripe NIE może mieć require_authenticated — weryfikacja podpisem."""
        src = _func_source("stripe_webhook") or ""
        assert "require_authenticated" not in src

    def test_webhook_verifies_signature(self):
        """Webhook musi weryfikować podpis Stripe (construct_event)."""
        src = _func_source("stripe_webhook") or ""
        assert "construct_event" in src or "SignatureVerificationError" in src

    def test_no_user_id_in_checkout_body(self):
        """user_id nie może być w CheckoutRequest."""
        for cls in ast.walk(_tree()):
            if isinstance(cls, ast.ClassDef) and cls.name == "CheckoutRequest":
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "user_id" not in fields, "CheckoutRequest nie może mieć user_id"

    def test_price_id_validation_in_checkout(self):
        """Checkout musi walidować price_id żeby nie można było podać dowolnej ceny."""
        src = _func_source("create_checkout") or ""
        assert "allowed" in src or "price_id not in" in src


# ── Modele Pydantic ───────────────────────────────────────────────────────────

class TestBillingSchemas:
    def test_checkout_request_has_price_id(self):
        for cls in ast.walk(_tree()):
            if isinstance(cls, ast.ClassDef) and cls.name == "CheckoutRequest":
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "price_id" in fields

    def test_subscription_status_has_is_premium(self):
        for cls in ast.walk(_tree()):
            if isinstance(cls, ast.ClassDef) and cls.name == "SubscriptionStatus":
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "is_premium" in fields
                assert "tier" in fields
                assert "status" in fields

    def test_checkout_response_has_checkout_url(self):
        for cls in ast.walk(_tree()):
            if isinstance(cls, ast.ClassDef) and cls.name == "CheckoutResponse":
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "checkout_url" in fields


# ── Logika premium ────────────────────────────────────────────────────────────

class TestBillingLogic:
    def test_tier_role_mapping_exists(self):
        """_TIER_ROLE musi mapować wszystkie tiers na role."""
        src = _source()
        assert "_TIER_ROLE" in src
        assert "PREMIUM_USER" in src

    def test_price_tier_mapping_exists(self):
        """_PRICE_TIER mapuje price_id Stripe na tier."""
        assert "_PRICE_TIER" in _source()

    def test_activate_premium_updates_user_role(self):
        src = _func_source("_activate_premium") or ""
        assert "user.role" in src

    def test_deactivate_premium_resets_to_user_role(self):
        src = _func_source("_deactivate_premium") or ""
        assert "UserRole.USER" in src or "role" in src

    def test_get_or_create_subscription_helper_exists(self):
        assert "_get_or_create_subscription" in _source()

    def test_webhook_handles_checkout_completed(self):
        src = _func_source("stripe_webhook") or ""
        assert "checkout.session.completed" in src

    def test_webhook_handles_subscription_deleted(self):
        src = _func_source("stripe_webhook") or ""
        assert "customer.subscription.deleted" in src

    def test_stripe_lazy_import(self):
        """Stripe musi być importowany leniwie (nie na poziomie modułu)."""
        src = _source()
        # Import na poziomie modułu byłby "import stripe" bez wcięcia
        lines = src.splitlines()
        top_level_stripe = [
            ln for ln in lines
            if ln.startswith("import stripe") or ln.startswith("from stripe")
        ]
        assert not top_level_stripe, "stripe nie powinien być importowany na poziomie modułu"
