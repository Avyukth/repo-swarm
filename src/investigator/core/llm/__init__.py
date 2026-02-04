"""
Multi-provider LLM abstraction layer.

This module provides a unified interface for multiple LLM providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- ZhipuAI (GLM)

Usage:
    from src.investigator.core.llm import get_provider

    # Get provider based on LLM_PROVIDER env var (default: anthropic)
    provider = get_provider()
    response = provider.analyze("Your prompt here")

    # Or specify provider explicitly
    provider = get_provider("openai", api_key="sk-...")
    response = provider.analyze("Your prompt here", model="gpt-4o")

    # Use Exa search with any provider
    from src.investigator.core.llm import ExaSearch
    exa = ExaSearch()
    results = exa.search("Python best practices 2024")
"""

from .base import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMInvalidModelError,
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
)
from .config import LLMConfig, ProviderConfig, PROVIDER_CONFIGS
from .factory import (
    clear_provider_cache,
    get_provider,
    get_registered_providers,
    register_provider,
)

# Lazy import search to avoid import errors if exa-py not installed
def _get_exa_search():
    from .search import ExaSearch
    return ExaSearch


__all__ = [
    # Base classes and types
    "LLMProvider",
    "LLMResponse",
    "LLMMessage",
    # Exceptions
    "LLMError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMInvalidModelError",
    # Configuration
    "LLMConfig",
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    # Factory
    "get_provider",
    "register_provider",
    "get_registered_providers",
    "clear_provider_cache",
]
