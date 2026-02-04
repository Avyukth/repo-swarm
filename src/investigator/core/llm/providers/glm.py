"""
ZhipuAI GLM LLM provider implementation with web search support.

Provides integration with the ZhipuAI API for GLM models,
including the glm-4-alltools model with built-in web search.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zhipuai import ZhipuAI

from ..base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError,
)
from ..config import PROVIDER_CONFIGS


class GLMProvider(LLMProvider):
    """
    ZhipuAI GLM API provider with web search support.

    GLM-4-AllTools model supports built-in web search capability.
    Use `analyze_with_web_search()` for automatic web search integration.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the GLM provider.

        Args:
            api_key: ZhipuAI API key
            base_url: Optional base URL override
            logger: Optional logger instance
        """
        self._api_key = api_key
        self._base_url = base_url
        self._logger = logger or logging.getLogger(__name__)
        self._config = PROVIDER_CONFIGS["glm"]

        # Initialize client
        self._client = ZhipuAI(api_key=api_key)
        self._logger.debug("Initialized GLM/ZhipuAI client")

    @property
    def provider_name(self) -> str:
        return "glm"

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
        enable_web_search: bool = False,
    ) -> LLMResponse:
        """
        Send prompt to GLM and return response.

        Args:
            prompt: The user prompt to send
            model: Model to use (default: provider default)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions
            enable_web_search: Enable built-in web search (requires glm-4-alltools)

        Returns:
            LLMResponse with the model's response

        Raises:
            LLMRateLimitError: If rate limited
            LLMAuthenticationError: If authentication fails
            LLMConnectionError: If connection fails
            LLMError: For other API errors
        """
        model_name = model or self.get_default_model()

        # If web search enabled, use alltools model
        if enable_web_search and model_name != "glm-4-alltools":
            self._logger.info(
                f"Web search enabled, switching from {model_name} to glm-4-alltools"
            )
            model_name = "glm-4-alltools"

        self._logger.debug(
            f"Sending request to GLM: model={model_name}, max_tokens={max_tokens}, "
            f"web_search={enable_web_search}"
        )

        try:
            # Build messages
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Build request kwargs
            kwargs: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
            }

            # Add web search tool if enabled
            if enable_web_search:
                kwargs["tools"] = [
                    {"type": "web_search", "web_search": {"enable": True}}
                ]
            elif tools:
                kwargs["tools"] = tools

            response = self._client.chat.completions.create(**kwargs)

            # Extract content
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""

            # Extract tool calls
            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": getattr(tc, "id", ""),
                            "name": getattr(tc.function, "name", "")
                            if hasattr(tc, "function")
                            else getattr(tc, "type", ""),
                            "input": getattr(tc.function, "arguments", "")
                            if hasattr(tc, "function")
                            else "",
                        }
                    )

            # Extract web search results if present
            web_search_results = []
            if hasattr(message, "web_search") and message.web_search:
                web_search_results = message.web_search
                # Append web search summary to content
                if web_search_results:
                    content += "\n\n## Web Search Results\n"
                    for result in web_search_results:
                        title = result.get("title", "Untitled")
                        link = result.get("link", "")
                        content += f"- [{title}]({link})\n"

            # Extract usage
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "output_tokens": getattr(response.usage, "completion_tokens", 0),
                }

            self._logger.debug(
                f"Received response from GLM: {len(content)} chars, "
                f"{len(tool_calls)} tool calls, {len(web_search_results)} web results"
            )

            return LLMResponse(
                content=content,
                raw_response=response,
                model=model_name,
                usage=usage,
                tool_calls=tool_calls,
                finish_reason=getattr(choice, "finish_reason", "") or "",
            )

        except Exception as e:
            error_str = str(e).lower()

            # Check for rate limiting
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                self._logger.warning(f"Rate limited by GLM: {e}")
                raise LLMRateLimitError(f"Rate limited by GLM: {e}") from e

            # Check for authentication errors
            if (
                "auth" in error_str
                or "401" in error_str
                or "key" in error_str
                or "permission" in error_str
            ):
                self._logger.error(f"Authentication failed for GLM: {e}")
                raise LLMAuthenticationError(f"Authentication failed: {e}") from e

            # Check for connection errors
            if "connect" in error_str or "timeout" in error_str:
                self._logger.error(f"Connection error to GLM: {e}")
                raise LLMConnectionError(f"Connection error: {e}") from e

            self._logger.error(f"GLM API error: {e}")
            raise LLMError(f"GLM API error: {e}") from e

    def analyze_with_web_search(
        self,
        prompt: str,
        *,
        max_tokens: int = 6000,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Convenience method to analyze with web search enabled.

        Automatically uses glm-4-alltools model with web search.

        Args:
            prompt: The user prompt to send
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with the model's response including web search results
        """
        return self.analyze(
            prompt,
            model="glm-4-alltools",
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            enable_web_search=True,
        )

    def validate_model(self, model: str) -> bool:
        """Check if model is valid for GLM."""
        return model in self._config.valid_models

    def get_default_model(self) -> str:
        """Get the default model for GLM."""
        return self._config.default_model

    def get_valid_models(self) -> List[str]:
        """Get list of valid models for GLM."""
        return self._config.valid_models.copy()
