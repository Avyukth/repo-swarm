"""
RED phase tests for AuthManager module.

Tests for:
- get_api_key() with priority order (env var → OAuth → stored API key)
- Auto-refresh OAuth tokens before expiration
- login/logout methods
- list_credentials() with redaction
- get_claude_token() singleton pattern
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestAuthManagerGetApiKey:
    """Test get_api_key() method with priority order."""

    def test_env_var_takes_priority_over_stored_credentials(self):
        """Test environment variable has highest priority."""
        from src.auth.manager import AuthManager
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-123"}):
            manager = AuthManager()
            key = manager.get_api_key("anthropic")
            assert key == "env-key-123"

    def test_oauth_token_used_when_no_env_var(self):
        """Test OAuth token is used when env var not set."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import OAuthCredentials, CredentialStore
        
        # Mock credential store with OAuth credentials
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get') as mock_get:
                mock_get.return_value = OAuthCredentials(
                    provider="anthropic",
                    access_token="oauth-token-456",
                    expires_at=time.time() + 3600,
                )
                
                manager = AuthManager()
                # Remove env var influence
                manager._env_var_names = {}
                key = manager.get_api_key("anthropic")
                
                assert key == "oauth-token-456"

    def test_api_key_used_when_no_env_var_or_oauth(self):
        """Test stored API key used as fallback."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import ApiKeyCredentials, CredentialStore
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get') as mock_get:
                mock_get.return_value = ApiKeyCredentials(
                    provider="anthropic",
                    key="api-key-789",
                )
                
                manager = AuthManager()
                manager._env_var_names = {}
                key = manager.get_api_key("anthropic")
                
                assert key == "api-key-789"

    def test_returns_none_when_no_credentials(self):
        """Test returns None when no credentials available."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get') as mock_get:
                mock_get.return_value = None
                
                manager = AuthManager()
                manager._env_var_names = {}
                key = manager.get_api_key("anthropic")
                
                assert key is None

    def test_custom_env_var_name_mapping(self):
        """Test custom environment variable name for provider."""
        from src.auth.manager import AuthManager
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}):
            manager = AuthManager()
            key = manager.get_api_key("openai")
            assert key == "openai-key"


class TestAuthManagerAutoRefresh:
    """Test automatic OAuth token refresh."""

    def test_auto_refresh_when_token_expiring(self):
        """Test tokens are refreshed when near expiration."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import OAuthCredentials, CredentialStore
        from src.auth.oauth import ClaudeOAuth
        
        # Token expiring in 2 minutes (within 5-minute buffer)
        expiring_token = OAuthCredentials(
            provider="anthropic",
            access_token="old-token",
            refresh_token="refresh-token",
            expires_at=time.time() + 120,
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get', return_value=expiring_token):
                with patch.object(CredentialStore, 'set') as mock_set:
                    with patch.object(ClaudeOAuth, 'refresh_access_token') as mock_refresh:
                        mock_refresh.return_value = {
                            "access_token": "new-token",
                            "refresh_token": "new-refresh",
                            "expires_in": 3600,
                        }
                        
                        manager = AuthManager()
                        manager._env_var_names = {}
                        key = manager.get_api_key("anthropic")
                        
                        # Should return new token
                        assert key == "new-token"
                        # Should have called refresh
                        mock_refresh.assert_called_once()

    def test_no_refresh_when_token_valid(self):
        """Test tokens are not refreshed when not near expiration."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import OAuthCredentials, CredentialStore
        from src.auth.oauth import ClaudeOAuth
        
        # Token valid for 1 hour
        valid_token = OAuthCredentials(
            provider="anthropic",
            access_token="valid-token",
            refresh_token="refresh-token",
            expires_at=time.time() + 3600,
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get', return_value=valid_token):
                with patch.object(ClaudeOAuth, 'refresh_access_token') as mock_refresh:
                    manager = AuthManager()
                    manager._env_var_names = {}
                    key = manager.get_api_key("anthropic")
                    
                    assert key == "valid-token"
                    mock_refresh.assert_not_called()

    def test_refresh_failure_returns_old_token(self):
        """Test old token returned if refresh fails."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import OAuthCredentials, CredentialStore
        from src.auth.oauth import ClaudeOAuth
        import httpx
        
        # Token expiring soon
        expiring_token = OAuthCredentials(
            provider="anthropic",
            access_token="old-token",
            refresh_token="refresh-token",
            expires_at=time.time() + 120,
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(CredentialStore, 'get', return_value=expiring_token):
                with patch.object(ClaudeOAuth, 'refresh_access_token') as mock_refresh:
                    mock_refresh.side_effect = httpx.HTTPStatusError(
                        "401", request=Mock(), response=Mock()
                    )
                    
                    manager = AuthManager()
                    manager._env_var_names = {}
                    key = manager.get_api_key("anthropic")
                    
                    # Should return old token on failure
                    assert key == "old-token"


class TestAuthManagerLogin:
    """Test login methods."""

    def test_login_with_api_key_stores_credentials(self):
        """Test login_with_api_key stores the key."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, ApiKeyCredentials
        
        with patch.object(CredentialStore, 'set') as mock_set:
            manager = AuthManager()
            manager.login_with_api_key("anthropic", "my-api-key")
            
            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][0] == "anthropic"
            assert isinstance(call_args[0][1], ApiKeyCredentials)
            assert call_args[0][1].key == "my-api-key"

    def test_login_with_oauth_triggers_flow(self):
        """Test login_with_oauth initiates OAuth flow."""
        from src.auth.manager import AuthManager
        from src.auth.oauth import interactive_oauth_login
        from src.auth.credentials import CredentialStore
        
        mock_tokens = {
            "access_token": "oauth-access",
            "refresh_token": "oauth-refresh",
            "expires_in": 3600,
        }
        
        with patch('src.auth.manager.interactive_oauth_login', return_value=mock_tokens) as mock_login:
            with patch.object(CredentialStore, 'set') as mock_set:
                manager = AuthManager()
                manager.login_with_oauth("anthropic")
                
                mock_login.assert_called_once()
                mock_set.assert_called_once()

    def test_login_with_oauth_stores_credentials(self):
        """Test login_with_oauth stores returned tokens."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, OAuthCredentials
        
        mock_tokens = {
            "access_token": "oauth-access",
            "refresh_token": "oauth-refresh",
            "expires_in": 3600,
        }
        
        with patch('src.auth.manager.interactive_oauth_login', return_value=mock_tokens):
            with patch.object(CredentialStore, 'set') as mock_set:
                manager = AuthManager()
                manager.login_with_oauth("anthropic")
                
                call_args = mock_set.call_args
                assert call_args[0][0] == "anthropic"
                cred = call_args[0][1]
                assert isinstance(cred, OAuthCredentials)
                assert cred.access_token == "oauth-access"
                assert cred.refresh_token == "oauth-refresh"


class TestAuthManagerLogout:
    """Test logout method."""

    def test_logout_removes_credentials(self):
        """Test logout removes stored credentials."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore
        
        with patch.object(CredentialStore, 'remove') as mock_remove:
            manager = AuthManager()
            manager.logout("anthropic")
            
            mock_remove.assert_called_once_with("anthropic")

    def test_logout_returns_true_on_success(self):
        """Test logout returns True when credentials existed."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, ApiKeyCredentials
        
        with patch.object(CredentialStore, 'get', return_value=ApiKeyCredentials(provider="anthropic", key="test")):
            with patch.object(CredentialStore, 'remove'):
                manager = AuthManager()
                result = manager.logout("anthropic")
                
                assert result is True

    def test_logout_returns_false_when_no_credentials(self):
        """Test logout returns False when no credentials existed."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore
        
        with patch.object(CredentialStore, 'get', return_value=None):
            with patch.object(CredentialStore, 'remove'):
                manager = AuthManager()
                result = manager.logout("anthropic")
                
                assert result is False


class TestAuthManagerListCredentials:
    """Test list_credentials method."""

    def test_list_credentials_returns_providers(self):
        """Test list returns all providers."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, ApiKeyCredentials
        
        def mock_get(provider):
            return ApiKeyCredentials(provider=provider, key="test-key")
        
        with patch.object(CredentialStore, 'list_providers', return_value=["anthropic", "openai"]):
            with patch.object(CredentialStore, 'get', side_effect=mock_get):
                manager = AuthManager()
                result = manager.list_credentials()
                
                assert len(result) == 2
                assert any(c["provider"] == "anthropic" for c in result)
                assert any(c["provider"] == "openai" for c in result)

    def test_list_credentials_shows_type(self):
        """Test list shows credential type (oauth/api_key)."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, OAuthCredentials, ApiKeyCredentials
        
        def mock_get(provider):
            if provider == "anthropic":
                return OAuthCredentials(provider="anthropic", access_token="x", expires_at=time.time() + 3600)
            return ApiKeyCredentials(provider="openai", key="y")
        
        with patch.object(CredentialStore, 'list_providers', return_value=["anthropic", "openai"]):
            with patch.object(CredentialStore, 'get', side_effect=mock_get):
                manager = AuthManager()
                result = manager.list_credentials()
                
                anthropic_cred = next(c for c in result if c["provider"] == "anthropic")
                openai_cred = next(c for c in result if c["provider"] == "openai")
                
                assert anthropic_cred["type"] == "oauth"
                assert openai_cred["type"] == "api_key"

    def test_list_credentials_redacts_sensitive_data(self):
        """Test list redacts tokens and keys."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, ApiKeyCredentials
        
        with patch.object(CredentialStore, 'list_providers', return_value=["anthropic"]):
            with patch.object(CredentialStore, 'get', return_value=ApiKeyCredentials(
                provider="anthropic",
                key="sk-ant-very-secret-key-12345"
            )):
                manager = AuthManager()
                result = manager.list_credentials()
                
                cred = result[0]
                # Should show redacted key (e.g., "sk-ant-...2345")
                assert "very-secret" not in str(cred)
                # Key should be truncated with "..." in the middle
                assert "..." in cred.get("key", "")

    def test_list_credentials_shows_expiration_for_oauth(self):
        """Test list shows expiration status for OAuth."""
        from src.auth.manager import AuthManager
        from src.auth.credentials import CredentialStore, OAuthCredentials
        
        with patch.object(CredentialStore, 'list_providers', return_value=["anthropic"]):
            with patch.object(CredentialStore, 'get', return_value=OAuthCredentials(
                provider="anthropic",
                access_token="token",
                expires_at=time.time() + 3600,
            )):
                manager = AuthManager()
                result = manager.list_credentials()
                
                cred = result[0]
                assert "expires" in cred or "expiration" in str(cred).lower()


class TestGetClaudeToken:
    """Test get_claude_token() convenience function."""

    def test_get_claude_token_exists(self):
        """Test get_claude_token function exists."""
        from src.auth.manager import get_claude_token
        
        assert callable(get_claude_token)

    def test_get_claude_token_returns_token(self):
        """Test get_claude_token returns anthropic token."""
        from src.auth.manager import get_claude_token, AuthManager
        
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "claude-token"}):
            token = get_claude_token()
            assert token == "claude-token"

    def test_get_claude_token_uses_singleton(self):
        """Test get_claude_token uses singleton AuthManager."""
        from src.auth.manager import get_claude_token, _get_default_manager
        
        # Get manager twice - should be same instance
        manager1 = _get_default_manager()
        manager2 = _get_default_manager()
        
        assert manager1 is manager2

    def test_get_claude_token_raises_when_no_credentials(self):
        """Test get_claude_token raises error when no credentials."""
        from src.auth.manager import get_claude_token, AuthError
        from src.auth.credentials import CredentialStore
        from src.auth import manager as mgr_module
        
        # Reset singleton so we get a fresh manager
        mgr_module._default_manager = None
        
        # Clear all environment variables that could provide credentials
        env_without_api_keys = {
            k: v for k, v in os.environ.items() 
            if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")
        }
        
        with patch.dict(os.environ, env_without_api_keys, clear=True):
            with patch.object(CredentialStore, 'get', return_value=None):
                with pytest.raises(AuthError, match="[Nn]o.*credential"):
                    get_claude_token()


class TestAuthError:
    """Test AuthError exception."""

    def test_auth_error_exists(self):
        """Test AuthError can be raised."""
        from src.auth.manager import AuthError
        
        with pytest.raises(AuthError):
            raise AuthError("Test error")

    def test_auth_error_has_message(self):
        """Test AuthError preserves message."""
        from src.auth.manager import AuthError
        
        try:
            raise AuthError("Authentication failed")
        except AuthError as e:
            assert "Authentication failed" in str(e)


class TestAuthManagerInit:
    """Test AuthManager initialization."""

    def test_custom_credential_store_path(self):
        """Test AuthManager accepts custom store path."""
        from src.auth.manager import AuthManager
        
        manager = AuthManager(credential_store_path="/custom/path/auth.json")
        assert manager._store.path == "/custom/path/auth.json"

    def test_default_provider_env_var_mapping(self):
        """Test default env var names are set."""
        from src.auth.manager import AuthManager
        
        manager = AuthManager()
        
        assert "anthropic" in manager._env_var_names
        assert manager._env_var_names["anthropic"] == "ANTHROPIC_API_KEY"
