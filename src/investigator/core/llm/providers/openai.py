"""
OpenAI GPT LLM provider implementation.

Provides integration with the OpenAI API for GPT models.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, AuthenticationError

from ..base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError,
)
from ..config import PROVIDER_CONFIGS


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API provider."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key
            base_url: Optional base URL override (for proxies or Azure)
            logger: Optional logger instance
        """
        self._api_key = api_key
        self._base_url = base_url
        self._logger = logger or logging.getLogger(__name__)
        self._config = PROVIDER_CONFIGS["openai"]

        # Initialize client
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            self._logger.debug(f"Initialized OpenAI client with base_url: {base_url}")
        else:
            self._logger.debug("Initialized OpenAI client")

        self._client = OpenAI(**kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

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
        Send prompt to OpenAI and return response.

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
            f"Sending request to OpenAI: model={model}, max_tokens={max_tokens}"
        )

        try:
            # Build messages
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Build request kwargs
            kwargs: Dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            # Add tools if provided (OpenAI function calling format)
            if tools:
                kwargs["tools"] = [
                    {"type": "function", "function": t} for t in tools
                ]

            response = self._client.chat.completions.create(**kwargs)

            # Extract content
            choice = response.choices[0]
            content = choice.message.content or ""

            # Extract tool calls
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    # Parse arguments if they're a JSON string
                    args = tc.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            pass

                    tool_calls.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "input": args,
                        }
                    )

            self._logger.debug(
                f"Received response from OpenAI: {len(content)} chars, "
                f"{len(tool_calls)} tool calls"
            )

            return LLMResponse(
                content=content,
                raw_response=response,
                model=response.model,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                },
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "",
            )

        except RateLimitError as e:
            self._logger.warning(f"Rate limited by OpenAI: {e}")
            raise LLMRateLimitError(f"Rate limited by OpenAI: {e}") from e
        except AuthenticationError as e:
            self._logger.error(f"Authentication failed for OpenAI: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}") from e
        except APIConnectionError as e:
            self._logger.error(f"Connection error to OpenAI: {e}")
            raise LLMConnectionError(f"Connection error: {e}") from e
        except APIError as e:
            self._logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"OpenAI API error: {e}") from e
        except Exception as e:
            self._logger.error(f"Unexpected error calling OpenAI: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    def validate_model(self, model: str) -> bool:
        """Check if model is valid for OpenAI."""
        return model in self._config.valid_models

    def get_default_model(self) -> str:
        """Get the default model for OpenAI."""
        return self._config.default_model

    def get_valid_models(self) -> List[str]:
        """Get list of valid models for OpenAI."""
        return self._config.valid_models.copy()
