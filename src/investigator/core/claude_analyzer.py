"""
Claude API integration for the Claude Investigator.

This module is maintained for backward compatibility.
For new code, use the LLM provider interface directly:
    from src.investigator.core.llm import get_provider
"""

from __future__ import annotations

import os
from typing import Optional

from .config import Config
from .llm import get_provider, LLMProvider, LLMError


class ClaudeAnalyzer:
    """
    Handles LLM API interactions for analysis.

    This class is a backward-compatible adapter. It uses the new
    LLM provider system internally but maintains the original API.

    The provider is selected based on the LLM_PROVIDER environment variable.
    Supported providers: anthropic (default), openai, gemini, glm

    Example:
        # Use default provider (anthropic)
        analyzer = ClaudeAnalyzer(api_key="...", logger=logger)

        # Use OpenAI
        os.environ["LLM_PROVIDER"] = "openai"
        analyzer = ClaudeAnalyzer(api_key="sk-...", logger=logger)
    """

    def __init__(self, api_key: str, logger, base_url: Optional[str] = None):
        """
        Initialize the analyzer with an LLM provider.

        Args:
            api_key: API key for the provider
            logger: Logger instance
            base_url: Optional base URL override (for proxies)
        """
        self.logger = logger
        self.base_url = base_url

        # Determine provider from environment
        provider_name = os.getenv("LLM_PROVIDER", "anthropic")

        # Create provider using the new system
        try:
            self._provider: LLMProvider = get_provider(
                provider_name=provider_name,
                api_key=api_key,
                base_url=base_url,
                logger=logger,
            )
            self.logger.info(f"Using LLM provider: {self._provider.provider_name}")
        except LLMError as e:
            self.logger.error(f"Failed to initialize LLM provider: {e}")
            raise

    @property
    def provider(self) -> LLMProvider:
        """Get the underlying LLM provider."""
        return self._provider

    @property
    def provider_name(self) -> str:
        """Get the name of the current provider."""
        return self._provider.provider_name

    def clean_prompt(self, prompt_template: str) -> str:
        """
        Clean the prompt template by removing version lines and other metadata.

        Args:
            prompt_template: Raw prompt template that may contain version headers

        Returns:
            Cleaned prompt template ready for the LLM
        """
        if not prompt_template:
            return prompt_template

        lines = prompt_template.split("\n")

        # Only clean if version line exists at the beginning
        if lines and lines[0].startswith("version"):
            lines = lines[1:]
            self.logger.debug("Removed version line from prompt")

            # Remove any leading empty lines after version removal
            while lines and lines[0].strip() == "":
                lines = lines[1:]

            cleaned_prompt = "\n".join(lines)
            self.logger.debug(f"Cleaned prompt ({len(cleaned_prompt)} characters)")

            return cleaned_prompt
        else:
            # No version line found, return as-is
            return prompt_template

    def analyze_with_context(
        self,
        prompt_template: str,
        repo_structure: str,
        previous_context: Optional[str] = None,
        config_overrides: Optional[dict] = None,
    ) -> str:
        """
        Analyze using the LLM with optional context from previous analyses.

        Args:
            prompt_template: Prompt template to use
            repo_structure: Repository structure string
            previous_context: Previous analysis results to include as context
            config_overrides: Optional dict with claude_model, max_tokens overrides

        Returns:
            Analysis result from the LLM
        """
        if config_overrides is None:
            config_overrides = {}

        # Clean the prompt template first (remove version lines, etc.)
        cleaned_template = self.clean_prompt(prompt_template)

        # Replace placeholders in the cleaned prompt
        prompt = cleaned_template.replace("{repo_structure}", repo_structure)

        # Add previous context if available
        if previous_context:
            context_section = (
                f"\n\n## Previous Analysis Context\n\n{previous_context}\n\n"
            )
            prompt = prompt.replace("{previous_context}", context_section)
        else:
            # Remove the placeholder if no context
            prompt = prompt.replace("{previous_context}", "")

        self.logger.debug(f"Prompt created ({len(prompt)} characters)")
        self.logger.debug(f"Prompt preview (first 1000 chars): {prompt[:1000]}...")

        try:
            # Use config overrides or defaults
            # Support both claude_model (legacy) and model (new) keys
            model = (
                config_overrides.get("claude_model")
                or config_overrides.get("model")
                or os.getenv("LLM_MODEL")
                or Config.CLAUDE_MODEL
            )
            max_tokens = config_overrides.get("max_tokens") or Config.MAX_TOKENS

            self.logger.info(
                f"Sending analysis request to {self._provider.provider_name} API"
            )
            self.logger.debug(f"Using model: {model}, max_tokens: {max_tokens}")

            # Use the provider
            response = self._provider.analyze(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
            )

            analysis_text = response.content
            self.logger.info(
                f"Received analysis from {self._provider.provider_name} "
                f"({len(analysis_text)} characters)"
            )
            self.logger.debug(
                f"Analysis preview (first 1000 chars): {analysis_text[:1000]}..."
            )

            return analysis_text

        except LLMError as e:
            self.logger.error(f"LLM API request failed: {str(e)}")
            raise Exception(f"Failed to get analysis from LLM: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error in analyze_with_context: {str(e)}")
            raise Exception(f"Failed to get analysis from LLM: {str(e)}") from e

    def analyze_structure(self, repo_structure: str, prompt_template: str) -> str:
        """
        Analyze repository structure using the LLM.

        Args:
            repo_structure: Repository structure string
            prompt_template: Prompt template to use

        Returns:
            Analysis result from the LLM
        """
        return self.analyze_with_context(prompt_template, repo_structure, None)
