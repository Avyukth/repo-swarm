"""
Factory for creating LLM provider instances.

Uses singleton pattern to cache provider instances per configuration.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Type

from .base import LLMError, LLMProvider
from .config import LLMConfig

logger = logging.getLogger(__name__)

# Provider registry - maps provider names to classes
_PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {}

# Singleton cache - caches provider instances
_provider_instances: Dict[str, LLMProvider] = {}


def register_provider(name: str, provider_class: Type[LLMProvider]) -> None:
    """
    Register a provider class with a name.

    Args:
        name: The provider name (e.g., 'anthropic', 'openai')
        provider_class: The provider class to register
    """
    _PROVIDER_REGISTRY[name.lower()] = provider_class
    logger.debug(f"Registered provider: {name}")


def get_registered_providers() -> Dict[str, Type[LLMProvider]]:
    """Return a copy of the provider registry."""
    return _PROVIDER_REGISTRY.copy()


def clear_provider_cache() -> None:
    """Clear the provider instance cache. Useful for testing."""
    _provider_instances.clear()


def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    *,
    use_cache: bool = True,
) -> LLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider_name: Provider name ('anthropic', 'openai', 'gemini', 'glm').
                      If None, uses LLM_PROVIDER env var or defaults to 'anthropic'.
        api_key: API key for the provider. If None, uses appropriate env var.
        base_url: Optional base URL override for the provider.
        logger: Optional logger instance.
        use_cache: Whether to cache and reuse provider instances.

    Returns:
        LLMProvider instance for the requested provider.

    Raises:
        LLMError: If provider is unknown or configuration is invalid.
    """
    # Determine provider
    provider_name = provider_name or os.getenv("LLM_PROVIDER", "anthropic")
    provider_name = LLMConfig.resolve_provider_name(provider_name)

    # Check cache
    cache_key = f"{provider_name}:{api_key or 'default'}:{base_url or 'default'}"
    if use_cache and cache_key in _provider_instances:
        return _provider_instances[cache_key]

    # Get provider class
    if provider_name not in _PROVIDER_REGISTRY:
        available = ", ".join(_PROVIDER_REGISTRY.keys())
        raise LLMError(f"Unknown provider '{provider_name}'. Available: {available}")

    provider_class = _PROVIDER_REGISTRY[provider_name]

    # Get API key from config or auth manager
    if api_key is None:
        api_key = _get_api_key_for_provider(provider_name)

    if not api_key:
        config = LLMConfig.get_provider_config(provider_name)
        raise LLMError(
            f"No API key found for provider '{provider_name}'. "
            f"Set {config.env_var} environment variable or use authentication."
        )

    # Get base URL if not provided
    if base_url is None:
        base_url = LLMConfig.get_base_url(provider_name)

    # Create instance
    instance = provider_class(
        api_key=api_key,
        base_url=base_url,
        logger=logger or logging.getLogger(__name__),
    )

    # Cache
    if use_cache:
        _provider_instances[cache_key] = instance

    return instance


def _get_api_key_for_provider(provider_name: str) -> Optional[str]:
    """Get API key for a provider using auth manager or env vars."""
    # First try auth manager
    try:
        from src.auth import AuthManager

        manager = AuthManager()
        key = manager.get_api_key(provider_name)
        if key:
            return key
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"AuthManager lookup failed: {e}")

    # Fallback to env vars via config
    return LLMConfig.get_api_key(provider_name)


def _register_all_providers() -> None:
    """Register all available providers. Called on module import."""
    # Lazy import to avoid circular dependencies
    try:
        from .providers.anthropic import AnthropicProvider

        register_provider("anthropic", AnthropicProvider)
        register_provider("claude", AnthropicProvider)
    except ImportError as e:
        logger.warning(f"Could not register Anthropic provider: {e}")

    try:
        from .providers.openai import OpenAIProvider

        register_provider("openai", OpenAIProvider)
        register_provider("gpt", OpenAIProvider)
    except ImportError as e:
        logger.warning(f"Could not register OpenAI provider: {e}")

    try:
        from .providers.gemini import GeminiProvider

        register_provider("gemini", GeminiProvider)
        register_provider("google", GeminiProvider)
    except ImportError as e:
        logger.warning(f"Could not register Gemini provider: {e}")

    try:
        from .providers.glm import GLMProvider

        register_provider("glm", GLMProvider)
        register_provider("zhipu", GLMProvider)
        register_provider("chatglm", GLMProvider)
    except ImportError as e:
        logger.warning(f"Could not register GLM provider: {e}")


# Register providers on module import
_register_all_providers()
