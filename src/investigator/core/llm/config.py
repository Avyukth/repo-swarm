"""
Configuration for LLM providers.

Centralizes model lists, env var names, and validation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""

    env_var: str
    base_url_env_var: Optional[str]
    default_model: str
    valid_models: List[str]
    max_tokens_default: int = 6000
    supports_tools: bool = False


# Provider configurations
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "anthropic": ProviderConfig(
        env_var="ANTHROPIC_API_KEY",
        base_url_env_var="ANTHROPIC_BASE_URL",
        default_model="claude-sonnet-4-5-20250929",
        valid_models=[
            # Direct Anthropic API models
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-5-20251101",
            "claude-opus-4-1-20250805",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            # Proxy models (Antigravity)
            "claude-opus-4-5-thinking",
            "claude-sonnet-4-5",
            "claude-sonnet-4-5-thinking",
        ],
        supports_tools=True,
    ),
    "openai": ProviderConfig(
        env_var="OPENAI_API_KEY",
        base_url_env_var="OPENAI_BASE_URL",
        default_model="gpt-4o",
        valid_models=[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
            "o1",
            "o3-mini",
        ],
        supports_tools=True,
    ),
    "gemini": ProviderConfig(
        env_var="GEMINI_API_KEY",
        base_url_env_var="GEMINI_BASE_URL",
        default_model="gemini-2.0-flash",
        valid_models=[
            "gemini-2.0-flash",
            "gemini-2.0-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            # Via proxy
            "gemini-3-pro-high",
            "gemini-3-pro-low",
            "gemini-3-flash",
        ],
        supports_tools=True,
    ),
    "glm": ProviderConfig(
        env_var="GLM_API_KEY",
        base_url_env_var="GLM_BASE_URL",
        default_model="glm-4-plus",
        valid_models=[
            "glm-4-plus",
            "glm-4",
            "glm-4-flash",
            "glm-4-alltools",  # Supports web search
            "glm-4-long",
            "glm-4v",
            "glm-4v-plus",
        ],
        supports_tools=True,
    ),
}

# Provider aliases
PROVIDER_ALIASES: Dict[str, str] = {
    "claude": "anthropic",
    "gpt": "openai",
    "google": "gemini",
    "zhipu": "glm",
    "zhipuai": "glm",
    "chatglm": "glm",
}


class LLMConfig:
    """Global LLM configuration."""

    # Default provider (can be overridden via env var)
    DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")

    # Default max tokens
    DEFAULT_MAX_TOKENS = 6000

    @staticmethod
    def resolve_provider_name(provider: str) -> str:
        """Resolve provider aliases to canonical names."""
        provider = provider.lower()
        return PROVIDER_ALIASES.get(provider, provider)

    @staticmethod
    def get_provider_config(provider: str) -> ProviderConfig:
        """Get configuration for a provider."""
        provider = LLMConfig.resolve_provider_name(provider)
        if provider not in PROVIDER_CONFIGS:
            available = ", ".join(PROVIDER_CONFIGS.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")
        return PROVIDER_CONFIGS[provider]

    @staticmethod
    def validate_model(provider: str, model: str) -> bool:
        """Validate model name for provider."""
        config = LLMConfig.get_provider_config(provider)
        return model in config.valid_models

    @staticmethod
    def get_api_key(provider: str) -> Optional[str]:
        """Get API key from environment for a provider."""
        config = LLMConfig.get_provider_config(provider)
        return os.getenv(config.env_var)

    @staticmethod
    def get_base_url(provider: str) -> Optional[str]:
        """Get base URL from environment for a provider."""
        config = LLMConfig.get_provider_config(provider)
        if config.base_url_env_var:
            return os.getenv(config.base_url_env_var)
        return None

    @staticmethod
    def list_providers() -> List[str]:
        """List all available providers."""
        return list(PROVIDER_CONFIGS.keys())

    @staticmethod
    def list_models(provider: str) -> List[str]:
        """List all valid models for a provider."""
        config = LLMConfig.get_provider_config(provider)
        return config.valid_models.copy()
