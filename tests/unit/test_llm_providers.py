"""
Unit tests for LLM provider implementations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os

from src.investigator.core.llm.base import (
    LLMProvider,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
)
from src.investigator.core.llm.config import (
    LLMConfig,
    ProviderConfig,
    PROVIDER_CONFIGS,
)
from src.investigator.core.llm.factory import (
    get_provider,
    register_provider,
    clear_provider_cache,
    get_registered_providers,
)


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_is_immutable(self):
        """Test LLMResponse is frozen dataclass."""
        response = LLMResponse(content="test", model="gpt-4")
        with pytest.raises(AttributeError):
            response.content = "modified"

    def test_llm_response_has_required_fields(self):
        """Test LLMResponse has all required fields."""
        response = LLMResponse(content="test")
        assert response.content == "test"
        assert response.raw_response is None
        assert response.model == ""
        assert response.usage == {}
        assert response.tool_calls == []
        assert response.finish_reason == ""

    def test_llm_response_with_all_fields(self):
        """Test LLMResponse with all fields populated."""
        response = LLMResponse(
            content="Hello world",
            raw_response={"id": "123"},
            model="gpt-4",
            usage={"input_tokens": 10, "output_tokens": 20},
            tool_calls=[{"id": "tc1", "name": "search", "input": {}}],
            finish_reason="stop",
        )
        assert response.content == "Hello world"
        assert response.raw_response == {"id": "123"}
        assert response.model == "gpt-4"
        assert response.usage["input_tokens"] == 10
        assert len(response.tool_calls) == 1
        assert response.finish_reason == "stop"


class TestLLMConfig:
    """Test LLM configuration."""

    def test_provider_configs_exist_for_all_providers(self):
        """Test all expected providers have configs."""
        expected_providers = {"anthropic", "openai", "gemini", "glm"}
        assert expected_providers.issubset(set(PROVIDER_CONFIGS.keys()))

    def test_resolve_provider_name_aliases(self):
        """Test provider alias resolution."""
        assert LLMConfig.resolve_provider_name("claude") == "anthropic"
        assert LLMConfig.resolve_provider_name("gpt") == "openai"
        assert LLMConfig.resolve_provider_name("google") == "gemini"
        assert LLMConfig.resolve_provider_name("zhipu") == "glm"
        assert LLMConfig.resolve_provider_name("chatglm") == "glm"

    def test_resolve_provider_name_canonical(self):
        """Test canonical provider names pass through."""
        assert LLMConfig.resolve_provider_name("anthropic") == "anthropic"
        assert LLMConfig.resolve_provider_name("openai") == "openai"
        assert LLMConfig.resolve_provider_name("gemini") == "gemini"
        assert LLMConfig.resolve_provider_name("glm") == "glm"

    def test_get_provider_config_valid(self):
        """Test getting valid provider config."""
        config = LLMConfig.get_provider_config("anthropic")
        assert isinstance(config, ProviderConfig)
        assert config.env_var == "ANTHROPIC_API_KEY"
        assert len(config.valid_models) > 0

    def test_get_provider_config_invalid(self):
        """Test getting invalid provider config raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMConfig.get_provider_config("nonexistent")

    def test_validate_model_valid(self):
        """Test model validation for valid models."""
        assert LLMConfig.validate_model("anthropic", "claude-sonnet-4-5-20250929") is True
        assert LLMConfig.validate_model("openai", "gpt-4o") is True
        assert LLMConfig.validate_model("glm", "glm-4-alltools") is True

    def test_validate_model_invalid(self):
        """Test model validation for invalid models."""
        assert LLMConfig.validate_model("anthropic", "nonexistent-model") is False
        assert LLMConfig.validate_model("openai", "claude-3") is False

    def test_list_providers(self):
        """Test listing all providers."""
        providers = LLMConfig.list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "gemini" in providers
        assert "glm" in providers

    def test_list_models(self):
        """Test listing models for a provider."""
        models = LLMConfig.list_models("openai")
        assert "gpt-4o" in models
        assert "gpt-4-turbo" in models


class TestProviderFactory:
    """Test provider factory."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_provider_cache()

    def test_get_provider_returns_anthropic_by_default(self):
        """Default provider should be Anthropic."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with patch("src.investigator.core.llm.providers.anthropic.Anthropic"):
                provider = get_provider()
                assert provider.provider_name == "anthropic"

    def test_get_provider_from_env_var(self):
        """LLM_PROVIDER env var controls provider selection."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"},
            clear=False,
        ):
            with patch("src.investigator.core.llm.providers.openai.OpenAI"):
                provider = get_provider()
                assert provider.provider_name == "openai"

    def test_get_provider_explicit_name(self):
        """Provider can be specified explicitly."""
        with patch("src.investigator.core.llm.providers.openai.OpenAI"):
            provider = get_provider(provider_name="openai", api_key="test-key")
            assert provider.provider_name == "openai"

    def test_get_provider_raises_on_unknown_provider(self):
        """Unknown provider should raise LLMError."""
        with pytest.raises(LLMError, match="Unknown provider"):
            get_provider(provider_name="unknown", api_key="test")

    def test_get_provider_raises_without_api_key(self):
        """Missing API key should raise LLMError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMError, match="No API key"):
                get_provider(provider_name="anthropic")

    def test_get_provider_caches_instances(self):
        """Provider instances should be cached."""
        with patch("src.investigator.core.llm.providers.anthropic.Anthropic"):
            p1 = get_provider(provider_name="anthropic", api_key="test")
            p2 = get_provider(provider_name="anthropic", api_key="test")
            assert p1 is p2

    def test_get_provider_no_cache(self):
        """Provider instances should not be cached when use_cache=False."""
        with patch("src.investigator.core.llm.providers.anthropic.Anthropic"):
            p1 = get_provider(provider_name="anthropic", api_key="test", use_cache=False)
            p2 = get_provider(provider_name="anthropic", api_key="test", use_cache=False)
            assert p1 is not p2

    def test_get_registered_providers(self):
        """Test getting registered providers."""
        providers = get_registered_providers()
        assert "anthropic" in providers
        assert "openai" in providers


class TestAnthropicProvider:
    """Test Anthropic provider."""

    def test_analyze_returns_llm_response(self):
        """analyze() should return LLMResponse."""
        from src.investigator.core.llm.providers.anthropic import AnthropicProvider

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = "Test response"
        mock_block.type = "text"
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.stop_reason = "end_turn"

        with patch(
            "src.investigator.core.llm.providers.anthropic.Anthropic"
        ) as MockClient:
            MockClient.return_value.messages.create.return_value = mock_response

            provider = AnthropicProvider(api_key="test", logger=Mock())
            result = provider.analyze("Test prompt")

            assert isinstance(result, LLMResponse)
            assert result.content == "Test response"
            assert result.model == "claude-sonnet-4-5"
            assert result.usage["input_tokens"] == 10
            assert result.usage["output_tokens"] == 20

    def test_validate_model_accepts_valid_models(self):
        """validate_model() should accept known models."""
        from src.investigator.core.llm.providers.anthropic import AnthropicProvider

        with patch("src.investigator.core.llm.providers.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="test", logger=Mock())
            assert provider.validate_model("claude-sonnet-4-5-20250929") is True
            assert provider.validate_model("invalid-model") is False

    def test_provider_name(self):
        """Provider name should be 'anthropic'."""
        from src.investigator.core.llm.providers.anthropic import AnthropicProvider

        with patch("src.investigator.core.llm.providers.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="test", logger=Mock())
            assert provider.provider_name == "anthropic"


class TestOpenAIProvider:
    """Test OpenAI provider."""

    def test_analyze_returns_llm_response(self):
        """analyze() should return LLMResponse."""
        from src.investigator.core.llm.providers.openai import OpenAIProvider

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gpt-4o"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch(
            "src.investigator.core.llm.providers.openai.OpenAI"
        ) as MockClient:
            MockClient.return_value.chat.completions.create.return_value = mock_response

            provider = OpenAIProvider(api_key="test", logger=Mock())
            result = provider.analyze("Test prompt")

            assert isinstance(result, LLMResponse)
            assert result.content == "Test response"
            assert result.model == "gpt-4o"

    def test_provider_name(self):
        """Provider name should be 'openai'."""
        from src.investigator.core.llm.providers.openai import OpenAIProvider

        with patch("src.investigator.core.llm.providers.openai.OpenAI"):
            provider = OpenAIProvider(api_key="test", logger=Mock())
            assert provider.provider_name == "openai"


class TestGLMProvider:
    """Test GLM provider with web search."""

    def test_analyze_with_web_search_uses_alltools_model(self):
        """Web search should use glm-4-alltools model."""
        from src.investigator.core.llm.providers.glm import GLMProvider

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response with search"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch("src.investigator.core.llm.providers.glm.ZhipuAI") as MockClient:
            mock_client = MockClient.return_value
            mock_client.chat.completions.create.return_value = mock_response

            provider = GLMProvider(api_key="test", logger=Mock())
            result = provider.analyze_with_web_search("Search for X")

            # Verify alltools model was used
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == "glm-4-alltools"
            assert isinstance(result, LLMResponse)

    def test_provider_name(self):
        """Provider name should be 'glm'."""
        from src.investigator.core.llm.providers.glm import GLMProvider

        with patch("src.investigator.core.llm.providers.glm.ZhipuAI"):
            provider = GLMProvider(api_key="test", logger=Mock())
            assert provider.provider_name == "glm"

    def test_supports_tools(self):
        """GLM should support tools."""
        from src.investigator.core.llm.providers.glm import GLMProvider

        with patch("src.investigator.core.llm.providers.glm.ZhipuAI"):
            provider = GLMProvider(api_key="test", logger=Mock())
            assert provider.supports_tools is True


class TestExaSearch:
    """Test Exa search provider."""

    def test_search_returns_results(self):
        """search() should return SearchResult list."""
        from src.investigator.core.llm.search.exa import ExaSearch
        from src.investigator.core.llm.search.base import SearchResult

        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.title = "Test Title"
        mock_result.url = "https://example.com"
        mock_result.text = "Test snippet"
        mock_result.score = 0.95
        mock_result.published_date = "2024-01-01"
        mock_response.results = [mock_result]

        with patch("src.investigator.core.llm.search.exa.Exa") as MockClient:
            MockClient.return_value.search.return_value = mock_response

            exa = ExaSearch(api_key="test", logger=Mock())
            results = exa.search("test query")

            assert len(results) == 1
            assert isinstance(results[0], SearchResult)
            assert results[0].title == "Test Title"
            assert results[0].url == "https://example.com"

    def test_search_requires_api_key(self):
        """ExaSearch should raise error without API key."""
        from src.investigator.core.llm.search.exa import ExaSearch
        from src.investigator.core.llm.search.base import SearchError

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SearchError, match="No Exa API key"):
                ExaSearch()

    def test_provider_name(self):
        """Provider name should be 'exa'."""
        from src.investigator.core.llm.search.exa import ExaSearch

        with patch("src.investigator.core.llm.search.exa.Exa"):
            exa = ExaSearch(api_key="test", logger=Mock())
            assert exa.provider_name == "exa"


class TestClaudeAnalyzerBackwardCompatibility:
    """Test ClaudeAnalyzer backward compatibility."""

    def test_analyzer_uses_provider(self):
        """ClaudeAnalyzer should use LLM provider internally."""
        from src.investigator.core.claude_analyzer import ClaudeAnalyzer

        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=False):
            with patch(
                "src.investigator.core.claude_analyzer.get_provider"
            ) as mock_get:
                mock_provider = MagicMock()
                mock_provider.provider_name = "anthropic"
                mock_get.return_value = mock_provider

                logger = Mock()
                analyzer = ClaudeAnalyzer(api_key="test", logger=logger)

                assert analyzer.provider_name == "anthropic"
                mock_get.assert_called_once()

    def test_analyzer_selects_provider_from_env(self):
        """ClaudeAnalyzer should respect LLM_PROVIDER env var."""
        from src.investigator.core.claude_analyzer import ClaudeAnalyzer

        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=False):
            with patch(
                "src.investigator.core.claude_analyzer.get_provider"
            ) as mock_get:
                mock_provider = MagicMock()
                mock_provider.provider_name = "openai"
                mock_get.return_value = mock_provider

                logger = Mock()
                analyzer = ClaudeAnalyzer(api_key="test", logger=logger)

                assert analyzer.provider_name == "openai"
                mock_get.assert_called_once_with(
                    provider_name="openai",
                    api_key="test",
                    base_url=None,
                    logger=logger,
                )
