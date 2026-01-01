"""
RED phase tests for OAuth module.

Tests for:
- PKCE generation (code_verifier, code_challenge)
- Authorization URL generation
- Token exchange
- Token refresh
"""

from __future__ import annotations

import base64
import hashlib
import re
from typing import Any, Dict
from unittest.mock import Mock, patch

import httpx
import pytest


class TestPKCE:
    """Test PKCE (Proof Key for Code Exchange) generation."""

    def test_generate_pkce_pair_returns_verifier_and_challenge(self):
        """Test PKCE pair generation returns two values."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        verifier, challenge = oauth.generate_pkce_pair()
        
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) >= 43  # RFC 7636 minimum

    def test_code_challenge_is_sha256_of_verifier(self):
        """Test code_challenge is base64url(sha256(verifier))."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        verifier, challenge = oauth.generate_pkce_pair()
        
        # Manually compute expected challenge
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        
        assert challenge == expected

    def test_pkce_pair_is_unique_each_call(self):
        """Test each call generates unique verifier."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        v1, _ = oauth.generate_pkce_pair()
        v2, _ = oauth.generate_pkce_pair()
        assert v1 != v2

    def test_verifier_stored_on_instance(self):
        """Test code_verifier is stored for later use."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        verifier, _ = oauth.generate_pkce_pair()
        assert oauth.code_verifier == verifier

    def test_verifier_uses_cryptographic_randomness(self):
        """Test verifier uses secrets module for security."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        verifier, _ = oauth.generate_pkce_pair()
        
        # Verifier should be URL-safe base64 characters only
        assert re.match(r'^[A-Za-z0-9_-]+$', verifier)
        # Should have high entropy (at least 256 bits = 43 base64 chars)
        assert len(verifier) >= 43


class TestAuthorizationURL:
    """Test authorization URL generation."""

    def test_authorization_url_contains_required_params(self):
        """Test auth URL contains all required OAuth params."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        url = oauth.get_authorization_url()
        
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "state=" in url

    def test_authorization_url_uses_correct_base(self):
        """Test URL uses correct OAuth authorization endpoint."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        url = oauth.get_authorization_url()
        
        # Should use Anthropic's OAuth endpoint
        assert url.startswith("https://")
        assert "oauth" in url.lower() or "authorize" in url.lower()

    def test_state_is_stored_and_unique(self):
        """Test state parameter is stored for CSRF protection."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        url = oauth.get_authorization_url()
        
        assert oauth.state is not None
        assert len(oauth.state) >= 32  # Sufficient entropy
        assert f"state={oauth.state}" in url

    def test_each_call_generates_new_state(self):
        """Test each auth URL has unique state for CSRF protection."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        url1 = oauth.get_authorization_url()
        state1 = oauth.state
        
        url2 = oauth.get_authorization_url()
        state2 = oauth.state
        
        assert state1 != state2

    def test_redirect_uri_is_localhost(self):
        """Test redirect URI uses localhost for CLI OAuth flow."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        url = oauth.get_authorization_url()
        
        # Should redirect to localhost for CLI capture
        assert "redirect_uri=http" in url
        assert "127.0.0.1" in url or "localhost" in url


class TestTokenExchange:
    """Test token exchange (authorization code → tokens)."""

    def test_exchange_code_requires_prior_pkce(self):
        """Test exchange fails without prior PKCE generation."""
        from src.auth.oauth import ClaudeOAuth, OAuthError
        
        oauth = ClaudeOAuth()
        with pytest.raises((ValueError, OAuthError), match="[Nn]o code.?verifier|PKCE"):
            oauth.exchange_code_for_tokens("auth_code_123")

    def test_exchange_code_sends_correct_payload(self):
        """Test token exchange sends correct request."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        oauth.get_authorization_url()  # Generate PKCE
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "access_123",
                "refresh_token": "refresh_456",
                "expires_in": 3600
            }
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            
            oauth.exchange_code_for_tokens("auth_code_123")
            
            # Verify POST was called
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            # Verify payload contains required fields
            payload = call_args[1].get("json") or call_args[1].get("data")
            assert payload["grant_type"] == "authorization_code"
            assert payload["code"] == "auth_code_123"
            assert payload["code_verifier"] == oauth.code_verifier

    def test_exchange_returns_token_dict(self):
        """Test successful exchange returns token dictionary."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        oauth.get_authorization_url()
        
        expected = {
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_in": 3600
        }
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.json.return_value = expected
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            
            result = oauth.exchange_code_for_tokens("code")
            
            assert result["access_token"] == "access_123"
            assert result["refresh_token"] == "refresh_456"
            assert result["expires_in"] == 3600

    def test_exchange_raises_on_http_error(self):
        """Test exchange propagates HTTP errors."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        oauth.get_authorization_url()
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401", request=Mock(), response=Mock()
            )
            mock_client.post.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                oauth.exchange_code_for_tokens("invalid_code")


class TestTokenRefresh:
    """Test token refresh flow."""

    def test_refresh_sends_correct_payload(self):
        """Test refresh uses correct grant_type and refresh_token."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 3600
            }
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            
            oauth.refresh_access_token("old_refresh_token")
            
            call_args = mock_client.post.call_args
            payload = call_args[1].get("json") or call_args[1].get("data")
            assert payload["grant_type"] == "refresh_token"
            assert payload["refresh_token"] == "old_refresh_token"

    def test_refresh_returns_new_tokens(self):
        """Test refresh returns new token set."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        
        expected = {"access_token": "new", "expires_in": 7200}
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.json.return_value = expected
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            
            result = oauth.refresh_access_token("refresh_token")
            assert result["access_token"] == "new"

    def test_refresh_raises_on_http_error(self):
        """Test refresh propagates HTTP errors."""
        from src.auth.oauth import ClaudeOAuth
        
        oauth = ClaudeOAuth()
        
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client_cls.return_value.__enter__ = Mock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = Mock(return_value=False)
            
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401", request=Mock(), response=Mock()
            )
            mock_client.post.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                oauth.refresh_access_token("invalid_token")


class TestOAuthProviderBase:
    """Test OAuthProvider abstract base class."""

    def test_oauth_provider_is_abstract(self):
        """Test OAuthProvider cannot be instantiated directly."""
        from src.auth.oauth import OAuthProvider
        
        with pytest.raises(TypeError, match="abstract"):
            OAuthProvider()

    def test_oauth_provider_requires_generate_pkce_pair(self):
        """Test subclasses must implement generate_pkce_pair."""
        from src.auth.oauth import OAuthProvider
        
        class IncompleteProvider(OAuthProvider):
            def get_authorization_url(self) -> str:
                return ""
            def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
                return {}
            def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
                return {}
        
        with pytest.raises(TypeError, match="abstract"):
            IncompleteProvider()

    def test_oauth_provider_requires_get_authorization_url(self):
        """Test subclasses must implement get_authorization_url."""
        from src.auth.oauth import OAuthProvider
        
        class IncompleteProvider(OAuthProvider):
            def generate_pkce_pair(self) -> tuple[str, str]:
                return ("", "")
            def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
                return {}
            def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
                return {}
        
        with pytest.raises(TypeError, match="abstract"):
            IncompleteProvider()


class TestOAuthError:
    """Test OAuthError exception class."""

    def test_oauth_error_exists(self):
        """Test OAuthError can be raised and caught."""
        from src.auth.oauth import OAuthError
        
        with pytest.raises(OAuthError):
            raise OAuthError("Test error")

    def test_oauth_error_has_message(self):
        """Test OAuthError preserves error message."""
        from src.auth.oauth import OAuthError
        
        try:
            raise OAuthError("Token expired")
        except OAuthError as e:
            assert "Token expired" in str(e)


class TestInteractiveLogin:
    """Test interactive OAuth login flow for CLI."""

    def test_interactive_login_exists(self):
        """Test interactive_oauth_login function exists."""
        from src.auth.oauth import interactive_oauth_login
        
        assert callable(interactive_oauth_login)

    def test_interactive_login_accepts_provider(self):
        """Test interactive_oauth_login accepts provider parameter."""
        import inspect
        from src.auth.oauth import interactive_oauth_login
        
        sig = inspect.signature(interactive_oauth_login)
        params = list(sig.parameters.keys())
        
        # Should accept at least a provider or oauth object
        assert len(params) >= 1
