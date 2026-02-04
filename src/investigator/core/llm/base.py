"""
Abstract base class for LLM providers.

Provides a unified interface for all LLM providers, handling:
- Message formatting differences
- Response parsing
- Tool/function calling (where supported)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limited by the provider."""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails."""

    pass


class LLMConnectionError(LLMError):
    """Raised when connection to the provider fails."""

    pass


class LLMInvalidModelError(LLMError):
    """Raised when an invalid model is specified."""

    pass


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """
    Unified response from any LLM provider.

    Attributes:
        content: The text content of the response
        raw_response: The original response object from the provider
        model: The model that generated the response
        usage: Token usage statistics (if available)
        tool_calls: Any tool/function calls in the response (if applicable)
        finish_reason: Why the model stopped generating
    """

    content: str
    raw_response: Any = None
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""


@dataclass
class LLMMessage:
    """A message in the conversation."""

    role: str  # "user", "assistant", "system"
    content: str


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class
    and implement the required methods.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'anthropic', 'openai')."""
        ...

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Return True if this provider supports tool/function calling."""
        ...

    @abstractmethod
    def analyze(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 6000,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Send a prompt to the LLM and return the response.

        Args:
            prompt: The user prompt to send
            model: Override the default model for this request
            max_tokens: Maximum tokens in the response
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions (if supported)

        Returns:
            LLMResponse with the model's response

        Raises:
            LLMError: If the request fails
            LLMRateLimitError: If rate limited
            LLMAuthenticationError: If auth fails
        """
        ...

    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """
        Validate that a model name is supported by this provider.

        Args:
            model: The model name to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the default model for this provider."""
        ...

    def get_valid_models(self) -> List[str]:
        """Return list of valid models for this provider."""
        return []
