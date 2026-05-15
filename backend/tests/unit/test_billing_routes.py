"""Unit tests for app/api/routes/billing.py.

Contracts verified (AST-based — no Stripe/DB required):
- All 4 endpoints present with correct HTTP methods
- checkout, portal, status require require_authenticated
- stripe_webhook is public (Stripe calls it directly with its own signature)
- No user_id in CheckoutRequest (identity from JWT)
- Webhook endpoint does NOT use require_authenticated
- Webhook verifies Stripe signature (stripe-signature header)
- CheckoutRequest has price_id field
- CheckoutResponse has checkout_url (Stripe redirect)
- PortalResponse has portal_url
- SubscriptionStatus has tier, status, is_premium
- Stripe feature flag checked before creating sessions
- user_id passed to Stripe metadata from current_user.id (not request body)
- 503 when Stripe is not configured
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BILLING_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "billing.py"
SRC = BILLING_PATH.read_text()
TREE = ast.parse(SRC)


# ── AST helpers ───────────────────────────────────────────────────────────────


def _route_decorators() -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = {}
    for node in ast.walk(TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        routes: list[tuple[str, str]] = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute):
                continue
            if not (isinstance(func.value, ast.Name) and func.value.id == "router"):
                continue
            method = func.attr.upper()
            path_arg = dec.args[0] if dec.args else None
            path = (
                ast.literal_eval(path_arg)
                if path_arg and isinstance(path_arg, ast.Constant)
                else "?"
            )
            routes.append((method, path))
        if routes:
            result[node.name] = routes
    return result


def _model_fields(model_name: str) -> set[str]:
    fields: set[str] = set()
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.add(stmt.target.id)
    return fields


def _function_source(func_name: str) -> str:
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            lines = SRC.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def _uses_require_authenticated(func_name: str) -> bool:
    for node in ast.walk(TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        all_args = node.args.args
        all_defaults = (
            [None] * (len(all_args) - len(node.args.defaults))
        ) + node.args.defaults
        for _arg, default in zip(all_args, all_defaults):
            if isinstance(default, ast.Name) and default.id == "require_authenticated":
                return True
    return False


ROUTES = _route_decorators()


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestEndpointPresence:
    def test_create_checkout_exists(self):
        assert "create_checkout" in ROUTES

    def test_create_portal_exists(self):
        assert "create_portal" in ROUTES

    def test_stripe_webhook_exists(self):
        assert "stripe_webhook" in ROUTES

    def test_get_status_exists(self):
        assert "get_status" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_create_checkout_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["create_checkout"])

    def test_create_portal_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["create_portal"])

    def test_stripe_webhook_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["stripe_webhook"])

    def test_get_status_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_status"])


# ── Auth guard ────────────────────────────────────────────────────────────────


class TestAuthGuard:
    @pytest.mark.parametrize("func_name", [
        "create_checkout",
        "create_portal",
        "get_status",
    ])
    def test_authenticated_endpoint_requires_auth(self, func_name: str):
        assert _uses_require_authenticated(func_name), (
            f"{func_name} must use require_authenticated — billing is personal"
        )

    def test_webhook_is_public(self):
        """Stripe calls the webhook directly — no user JWT, just Stripe signature."""
        assert not _uses_require_authenticated("stripe_webhook"), (
            "stripe_webhook must be public — Stripe cannot send a user JWT"
        )


# ── Webhook security ──────────────────────────────────────────────────────────


class TestWebhookSecurity:
    def test_webhook_verifies_stripe_signature(self):
        """Webhook must verify the Stripe-Signature header to prevent spoofing."""
        src = _function_source("stripe_webhook")
        assert "stripe-signature" in src.lower() or "stripe_signature" in src.lower() or "webhook_secret" in src.lower()

    def test_webhook_raises_400_on_invalid_signature(self):
        src = _function_source("stripe_webhook")
        assert "400" in src or "HTTP_400_BAD_REQUEST" in src

    def test_webhook_path(self):
        """Webhook must be at /webhook (matches nginx rate-limit zone)."""
        paths = [p for _, p in ROUTES.get("stripe_webhook", [])]
        assert any("webhook" in p for p in paths)


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInRequestBody:
    def test_checkout_request_no_user_id(self):
        """user_id must come from JWT, not checkout request body."""
        assert "user_id" not in _model_fields("CheckoutRequest")

    def test_checkout_request_has_price_id(self):
        assert "price_id" in _model_fields("CheckoutRequest")

    def test_user_id_passed_from_current_user(self):
        """Checkout must use current_user.id for Stripe metadata, not request.user_id."""
        src = _function_source("create_checkout")
        assert "current_user.id" in src


# ── Response schemas ──────────────────────────────────────────────────────────


class TestResponseSchemas:
    def test_checkout_response_has_checkout_url(self):
        assert "checkout_url" in _model_fields("CheckoutResponse")

    def test_portal_response_has_portal_url(self):
        assert "portal_url" in _model_fields("PortalResponse")

    def test_status_has_tier(self):
        assert "tier" in _model_fields("SubscriptionStatus")

    def test_status_has_status(self):
        assert "status" in _model_fields("SubscriptionStatus")

    def test_status_has_is_premium(self):
        """is_premium is the fast boolean check used by feature gates."""
        assert "is_premium" in _model_fields("SubscriptionStatus")

    def test_status_has_cancel_at_period_end(self):
        assert "cancel_at_period_end" in _model_fields("SubscriptionStatus")

    def test_status_has_current_period_end(self):
        assert "current_period_end" in _model_fields("SubscriptionStatus")


# ── Stripe feature flag ───────────────────────────────────────────────────────


class TestStripeFeatureFlag:
    def test_stripe_enabled_helper_exists(self):
        assert "_stripe_enabled" in SRC

    def test_checkout_checks_stripe_enabled(self):
        src = _function_source("create_checkout")
        assert "_stripe_enabled" in src

    def test_disabled_stripe_raises_503(self):
        """503 = service unavailable — Stripe not configured."""
        src = _function_source("create_checkout")
        assert "503" in src or "HTTP_503_SERVICE_UNAVAILABLE" in src


# ── Subscription tiers ────────────────────────────────────────────────────────


class TestSubscriptionTiers:
    @pytest.mark.parametrize("tier", ["FREE", "PILGRIM", "DISCIPLE", "MYSTIC"])
    def test_subscription_tier_referenced(self, tier: str):
        assert tier in SRC, f"SubscriptionTier.{tier} must be referenced in billing.py"

    def test_activate_premium_helper_exists(self):
        assert "_activate_premium" in SRC

    def test_deactivate_premium_helper_exists(self):
        assert "_deactivate_premium" in SRC
