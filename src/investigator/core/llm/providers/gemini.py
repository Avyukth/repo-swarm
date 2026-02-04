"""
Google Gemini LLM provider implementation.

Provides integration with the Google Generative AI API for Gemini models.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ..base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMConnectionError,
)
from ..config import PROVIDER_CONFIGS


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Gemini provider.

        Args:
            api_key: Google API key
            base_url: Optional base URL override (not commonly used for Gemini)
            logger: Optional logger instance
        """
        self._api_key = api_key
        self._base_url = base_url
        self._logger = logger or logging.getLogger(__name__)
        self._config = PROVIDER_CONFIGS["gemini"]

        # Configure the API key
        genai.configure(api_key=api_key)
        self._logger.debug("Initialized Gemini client")

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        Send prompt to Gemini and return response.

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
        model_name = model or self.get_default_model()

        self._logger.debug(
            f"Sending request to Gemini: model={model_name}, max_tokens={max_tokens}"
        )

        try:
            # Create the model
            generation_config = genai.GenerationConfig(
                max_output_tokens=max_tokens,
            )

            model_kwargs: Dict[str, Any] = {
                "model_name": model_name,
                "generation_config": generation_config,
            }

            if system_prompt:
                model_kwargs["system_instruction"] = system_prompt

            gemini_model = genai.GenerativeModel(**model_kwargs)

            # Generate content
            response = gemini_model.generate_content(prompt)

            # Extract content
            content = ""
            if response.text:
                content = response.text

            # Extract usage metadata if available
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "input_tokens": getattr(
                        response.usage_metadata, "prompt_token_count", 0
                    ),
                    "output_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                }

            # Extract finish reason
            finish_reason = ""
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    finish_reason = str(candidate.finish_reason.name)

            self._logger.debug(
                f"Received response from Gemini: {len(content)} chars"
            )

            return LLMResponse(
                content=content,
                raw_response=response,
                model=model_name,
                usage=usage,
                tool_calls=[],  # Tool calls not implemented for Gemini yet
                finish_reason=finish_reason,
            )

        except google_exceptions.ResourceExhausted as e:
            self._logger.warning(f"Rate limited by Gemini: {e}")
            raise LLMRateLimitError(f"Rate limited by Gemini: {e}") from e
        except google_exceptions.PermissionDenied as e:
            self._logger.error(f"Authentication failed for Gemini: {e}")
            raise LLMAuthenticationError(f"Authentication failed: {e}") from e
        except google_exceptions.GoogleAPIError as e:
            self._logger.error(f"Gemini API error: {e}")
            raise LLMError(f"Gemini API error: {e}") from e
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str:
                raise LLMRateLimitError(f"Rate limited by Gemini: {e}") from e
            if "permission" in error_str or "auth" in error_str or "key" in error_str:
                raise LLMAuthenticationError(f"Authentication failed: {e}") from e
            self._logger.error(f"Unexpected error calling Gemini: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    def validate_model(self, model: str) -> bool:
        """Check if model is valid for Gemini."""
        return model in self._config.valid_models

    def get_default_model(self) -> str:
        """Get the default model for Gemini."""
        return self._config.default_model

    def get_valid_models(self) -> List[str]:
        """Get list of valid models for Gemini."""
        return self._config.valid_models.copy()
