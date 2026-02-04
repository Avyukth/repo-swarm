"""
ZhipuAI GLM LLM provider implementation with web search support.

Provides integration with the ZhipuAI/Z.AI API for GLM models,
including the glm-4-alltools model with built-in web search.

Supports two modes:
1. Native ZhipuAI SDK (default) - uses zhipuai package
2. OpenAI-compatible mode - uses OpenAI SDK with Z.AI endpoint (like OpenCode)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from ..base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError,
)
from ..config import PROVIDER_CONFIGS


# Z.AI OpenAI-compatible endpoints
ZAI_BASE_URL = "https://api.z.ai/api/paas/v4"  # Regular Z.AI
ZAI_CODING_PLAN_URL = "https://api.z.ai/api/coding/paas/v4"  # Z.AI Coding Plan (glm-4.7)
# Native ZhipuAI endpoint
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


class GLMProvider(LLMProvider):
    """
    ZhipuAI GLM API provider with web search support.

    GLM-4-AllTools model supports built-in web search capability.
    Use `analyze_with_web_search()` for automatic web search integration.

    Supports two modes controlled by GLM_USE_OPENAI_COMPAT env var:
    - Native mode (default): Uses zhipuai SDK
    - OpenAI-compatible mode: Uses OpenAI SDK with Z.AI endpoint
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        use_openai_compat: Optional[bool] = None,
        use_coding_plan: Optional[bool] = None,
    ):
        """
        Initialize the GLM provider.

        Args:
            api_key: ZhipuAI API key
            base_url: Optional base URL override
            logger: Optional logger instance
            use_openai_compat: Use OpenAI-compatible mode (default: from env or False)
            use_coding_plan: Use Z.AI Coding Plan endpoint for glm-4.7 (default: from env or True)
        """
        self._api_key = api_key
        self._logger = logger or logging.getLogger(__name__)
        self._config = PROVIDER_CONFIGS["glm"]

        # Determine mode
        if use_openai_compat is None:
            use_openai_compat = os.getenv("GLM_USE_OPENAI_COMPAT", "").lower() in (
                "1",
                "true",
                "yes",
            )
        self._use_openai_compat = use_openai_compat

        # Determine if using Coding Plan endpoint (for glm-4.7)
        if use_coding_plan is None:
            use_coding_plan = os.getenv("GLM_USE_CODING_PLAN", "true").lower() in (
                "1",
                "true",
                "yes",
            )
        self._use_coding_plan = use_coding_plan

        # Set base URL
        if base_url:
            self._base_url = base_url
        elif use_openai_compat:
            # Use Coding Plan endpoint by default (has glm-4.7 access)
            self._base_url = ZAI_CODING_PLAN_URL if use_coding_plan else ZAI_BASE_URL
        else:
            self._base_url = ZHIPUAI_BASE_URL

        # Initialize appropriate client
        if self._use_openai_compat:
            self._init_openai_client()
        else:
            self._init_native_client()

    def _init_native_client(self):
        """Initialize native ZhipuAI client."""
        from zhipuai import ZhipuAI

        self._client = ZhipuAI(api_key=self._api_key)
        self._client_type = "native"
        self._logger.debug(f"Initialized GLM native client (base_url: {self._base_url})")

    def _init_openai_client(self):
        """Initialize OpenAI-compatible client for Z.AI endpoint."""
        from openai import OpenAI

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        self._client_type = "openai_compat"
        self._logger.debug(
            f"Initialized GLM OpenAI-compatible client (base_url: {self._base_url})"
        )

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
            f"Sending request to GLM ({self._client_type}): model={model_name}, "
            f"max_tokens={max_tokens}, web_search={enable_web_search}"
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

            # Add web search tool if enabled (native mode only)
            if enable_web_search and not self._use_openai_compat:
                kwargs["tools"] = [
                    {"type": "web_search", "web_search": {"enable": True}}
                ]
            elif tools:
                if self._use_openai_compat:
                    # OpenAI format for tools
                    kwargs["tools"] = [
                        {"type": "function", "function": t} for t in tools
                    ]
                else:
                    kwargs["tools"] = tools

            # Make the API call
            if self._use_openai_compat:
                response = self._client.chat.completions.create(**kwargs)
            else:
                response = self._client.chat.completions.create(**kwargs)

            # Extract content
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""

            # Z.AI models may return content in reasoning_content field
            if not content and hasattr(message, "reasoning_content") and message.reasoning_content:
                content = message.reasoning_content
                self._logger.debug("Using reasoning_content as primary content")

            # Extract tool calls
            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    if self._use_openai_compat:
                        tool_calls.append(
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "input": tc.function.arguments,
                            }
                        )
                    else:
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

            # Extract web search results if present (native mode only)
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

            # Check for rate limiting / insufficient balance
            if (
                "rate" in error_str
                or "429" in error_str
                or "quota" in error_str
                or "余额" in str(e)  # Chinese for "balance"
                or "1113" in error_str  # ZhipuAI insufficient balance code
            ):
                self._logger.warning(f"Rate limited / insufficient balance for GLM: {e}")
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
