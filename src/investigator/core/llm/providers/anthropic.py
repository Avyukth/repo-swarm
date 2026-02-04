"""
Anthropic/Claude LLM provider implementation.

Provides integration with the Anthropic API for Claude models.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from anthropic import APIError, APIConnectionError, RateLimitError, AuthenticationError

from ..base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError,
)
from ..config import PROVIDER_CONFIGS


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude API provider."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
            base_url: Optional base URL override (for proxies)
            logger: Optional logger instance
        """
        self._api_key = api_key
        self._base_url = base_url
        self._logger = logger or logging.getLogger(__name__)
        self._config = PROVIDER_CONFIGS["anthropic"]

        # Initialize client
        if base_url:
            self._client = Anthropic(api_key=api_key, base_url=base_url)
            self._logger.debug(f"Initialized Anthropic client with base_url: {base_url}")
        else:
            self._client = Anthropic(api_key=api_key)
            self._logger.debug("Initialized Anthropic client")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supports_tools(self) -> bool:
        return self._config.supports_tools

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
        Send prompt to Claude and return response.

        Args:
            prompt: The user prompt to send
            model: Model to use (default: provider default)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions

        Returns:
            LLMResponse with the model's response

        Raises:
            LLMRateLimitError: If rate limited
            LLMAuthenticationError: If authentication fails
            LLMConnectionError: If connection fails
            LLMError: For other API errors
        """
        model = model or self.get_default_model()

        self._logger.debug(
            f"Sending request to Anthropic: model={model}, max_tokens={max_tokens}"
        )

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Build request kwargs
            kwargs: Dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools:
                kwargs["tools"] = tools

            response = self._client.messages.create(**kwargs)

            # Extract content - handle text blocks and tool use blocks
            content = ""
            tool_calls = []

            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            self._logger.debug(
                f"Received response from Anthropic: {len(content)} chars, "
                f"{len(tool_calls)} tool calls"
            )

            return LLMResponse(
                content=content,
                raw_response=response,
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "",
            )

        except RateLimitError as e:
            self._logger.warning(f"Rate limited by Anthropic: {e}")
            raise LLMRateLimitError(f"Rate limited by Anthropic: {e}") from e
        except AuthenticationError as e:
            self._logger.error(f"Authentication failed for Anthropic: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}") from e
        except APIConnectionError as e:
            self._logger.error(f"Connection error to Anthropic: {e}")
            raise LLMConnectionError(f"Connection error: {e}") from e
        except APIError as e:
            self._logger.error(f"Anthropic API error: {e}")
            raise LLMError(f"Anthropic API error: {e}") from e
        except Exception as e:
            self._logger.error(f"Unexpected error calling Anthropic: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    def validate_model(self, model: str) -> bool:
        """Check if model is valid for Anthropic."""
        return model in self._config.valid_models

    def get_default_model(self) -> str:
        """Get the default model for Anthropic."""
        return self._config.default_model

    def get_valid_models(self) -> List[str]:
        """Get list of valid models for Anthropic."""
        return self._config.valid_models.copy()
