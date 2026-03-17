"""
LLM Factory for Sancta Nexus
=============================
Provides a unified interface to obtain LLM instances (ChatOpenAI or
ChatAnthropic) based on application configuration.

Supports:
  - Multiple use-case tiers: primary, fast, creative
  - Fallback chain: if primary provider fails, try secondary
  - Configurable via Settings

Usage::

    from app.core.llm import get_llm, get_llm_fast, get_llm_creative

    llm = get_llm()                     # primary model
    llm_fast = get_llm_fast()           # cheaper/faster model
    llm_creative = get_llm_creative()   # higher-temperature creative model
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger("sancta_nexus.llm")

# Type alias for use-case tiers
UseCaseTier = Literal["primary", "fast", "creative"]


def _create_openai_llm(
    model: str,
    temperature: float = 0.5,
    max_tokens: int = 2048,
) -> BaseChatModel:
    """Create a ChatOpenAI instance."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.OPENAI_API_KEY or None,
    )


def _create_anthropic_llm(
    model: str,
    temperature: float = 0.5,
    max_tokens: int = 2048,
) -> BaseChatModel:
    """Create a ChatAnthropic instance."""
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.ANTHROPIC_API_KEY or None,
    )


def _get_model_name(provider: str, tier: UseCaseTier) -> str:
    """Resolve the model name for a given provider and tier."""
    mapping = {
        ("openai", "primary"): settings.LLM_PRIMARY_MODEL,
        ("openai", "fast"): settings.LLM_FAST_MODEL,
        ("openai", "creative"): settings.LLM_CREATIVE_MODEL,
        ("anthropic", "primary"): settings.LLM_PRIMARY_ANTHROPIC_MODEL,
        ("anthropic", "fast"): settings.LLM_FAST_ANTHROPIC_MODEL,
        ("anthropic", "creative"): settings.LLM_CREATIVE_ANTHROPIC_MODEL,
    }
    return mapping.get((provider, tier), settings.LLM_PRIMARY_MODEL)


def _create_llm(
    provider: str,
    tier: UseCaseTier,
    temperature: float = 0.5,
    max_tokens: int = 2048,
) -> BaseChatModel:
    """Create an LLM instance for a specific provider and tier."""
    model = _get_model_name(provider, tier)

    if provider == "anthropic":
        return _create_anthropic_llm(model, temperature, max_tokens)
    else:
        return _create_openai_llm(model, temperature, max_tokens)


def get_llm(
    *,
    tier: UseCaseTier = "primary",
    temperature: float = 0.5,
    max_tokens: int = 2048,
) -> BaseChatModel:
    """
    Get an LLM instance for the specified use-case tier.

    Tries the primary provider first. If the primary provider's API key
    is not configured, falls back to the secondary provider.

    Args:
        tier: One of "primary", "fast", "creative".
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for the response.

    Returns:
        A BaseChatModel instance (ChatOpenAI or ChatAnthropic).
    """
    primary = settings.LLM_PROVIDER
    fallback = settings.LLM_FALLBACK_PROVIDER

    # Check if primary provider has an API key configured
    if primary == "openai" and settings.OPENAI_API_KEY:
        try:
            llm = _create_llm(primary, tier, temperature, max_tokens)
            logger.debug(
                "Created %s LLM (tier=%s, model=%s)",
                primary,
                tier,
                _get_model_name(primary, tier),
            )
            return llm
        except Exception:
            logger.warning(
                "Failed to create %s LLM; trying fallback %s",
                primary,
                fallback,
            )
    elif primary == "anthropic" and settings.ANTHROPIC_API_KEY:
        try:
            llm = _create_llm(primary, tier, temperature, max_tokens)
            logger.debug(
                "Created %s LLM (tier=%s, model=%s)",
                primary,
                tier,
                _get_model_name(primary, tier),
            )
            return llm
        except Exception:
            logger.warning(
                "Failed to create %s LLM; trying fallback %s",
                primary,
                fallback,
            )

    # Try fallback provider
    if fallback == "anthropic" and settings.ANTHROPIC_API_KEY:
        llm = _create_llm(fallback, tier, temperature, max_tokens)
        logger.info("Using fallback provider: %s", fallback)
        return llm
    elif fallback == "openai" and settings.OPENAI_API_KEY:
        llm = _create_llm(fallback, tier, temperature, max_tokens)
        logger.info("Using fallback provider: %s", fallback)
        return llm

    # Last resort: create with primary provider anyway (will fail at call time)
    logger.warning(
        "No API keys configured for LLM providers. "
        "Agents will fall back to template responses."
    )
    return _create_llm(primary, tier, temperature, max_tokens)


def get_llm_primary(
    *, temperature: float = 0.5, max_tokens: int = 2048
) -> BaseChatModel:
    """Get the primary (strongest) LLM for theology & exegesis."""
    return get_llm(tier="primary", temperature=temperature, max_tokens=max_tokens)


def get_llm_fast(
    *, temperature: float = 0.2, max_tokens: int = 1024
) -> BaseChatModel:
    """Get a fast/cheap LLM for classification & detection tasks."""
    return get_llm(tier="fast", temperature=temperature, max_tokens=max_tokens)


def get_llm_creative(
    *, temperature: float = 0.8, max_tokens: int = 2048
) -> BaseChatModel:
    """Get a creative LLM for prayer & reflection generation."""
    return get_llm(tier="creative", temperature=temperature, max_tokens=max_tokens)
