"""
Unified Auth Manager for credential retrieval.

Provides single entry point for authentication with priority order:
1. Environment variable (highest priority)
2. OAuth token (with auto-refresh)
3. Stored API key (fallback)

Follows opencode patterns for consistency.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .credentials import (
    ApiKeyCredentials,
    CredentialStore,
    Credentials,
    OAuthCredentials,
)
from .oauth import ClaudeOAuth, OAuthError, interactive_oauth_login

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication operations fail."""
    pass


# Default environment variable names for providers
DEFAULT_ENV_VAR_NAMES: Dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "glm": "GLM_API_KEY",
    "zhipu": "GLM_API_KEY",
    "exa": "EXA_API_KEY",
}

ANTHROPIC_BASE_URL_ENV = "ANTHROPIC_BASE_URL"

# Singleton instance
_default_manager: Optional["AuthManager"] = None


def _get_default_manager() -> "AuthManager":
    """Get or create the default AuthManager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AuthManager()
    return _default_manager


class AuthManager:
    """
    Unified authentication manager.
    
    Handles credential retrieval with priority order:
    1. Environment variable
    2. OAuth token (with auto-refresh before expiration)
    3. Stored API key
    """
    
    # Buffer time before expiration to trigger refresh (5 minutes)
    REFRESH_BUFFER_SECONDS = 300
    
    def __init__(
        self,
        credential_store_path: Optional[str] = None,
        env_var_names: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize AuthManager.
        
        Args:
            credential_store_path: Custom path for credential storage
            env_var_names: Custom mapping of provider -> env var name
        """
        self._store = CredentialStore(path=credential_store_path)
        self._env_var_names = env_var_names or DEFAULT_ENV_VAR_NAMES.copy()
        self._oauth_providers: Dict[str, ClaudeOAuth] = {}
    
    def _get_oauth_provider(self, provider: str) -> ClaudeOAuth:
        """Get or create OAuth provider for a given provider name."""
        if provider not in self._oauth_providers:
            # Currently only Claude is supported
            if provider == "anthropic":
                self._oauth_providers[provider] = ClaudeOAuth()
            else:
                raise AuthError(f"OAuth not supported for provider: {provider}")
        return self._oauth_providers[provider]
    
    def _get_env_var(self, provider: str) -> Optional[str]:
        """Get API key from environment variable."""
        env_var_name = self._env_var_names.get(provider)
        if env_var_name:
            return os.environ.get(env_var_name)
        return None
    
    def _maybe_refresh_token(
        self,
        provider: str,
        credentials: OAuthCredentials,
    ) -> OAuthCredentials:
        """
        Refresh OAuth token if near expiration.
        
        Args:
            provider: Provider name
            credentials: Current OAuth credentials
            
        Returns:
            Refreshed credentials or original if refresh not needed/failed
        """
        if not credentials.is_expired(buffer_seconds=self.REFRESH_BUFFER_SECONDS):
            return credentials
        
        if not credentials.refresh_token:
            logger.warning(f"Token expiring but no refresh token for {provider}")
            return credentials
        
        try:
            oauth = self._get_oauth_provider(provider)
            token_response = oauth.refresh_access_token(credentials.refresh_token)
            
            # Create new credentials
            new_credentials = OAuthCredentials(
                provider=provider,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token", credentials.refresh_token),
                expires_at=time.time() + token_response.get("expires_in", 3600),
            )
            
            # Save updated credentials
            self._store.set(provider, new_credentials)
            logger.info(f"Refreshed OAuth token for {provider}")
            
            return new_credentials
            
        except Exception as e:
            logger.warning(f"Failed to refresh token for {provider}: {e}")
            return credentials
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key/token for a provider.
        
        Priority order:
        1. Environment variable
        2. repo-swarm stored credentials
        3. OpenCode's auth file (fallback)
        """
        # 1. Check environment variable first
        env_key = self._get_env_var(provider)
        if env_key:
            return env_key
        
        # 2. Check repo-swarm stored credentials
        credentials = self._store.get(provider)
        if credentials is not None:
            if isinstance(credentials, OAuthCredentials):
                credentials = self._maybe_refresh_token(provider, credentials)
                return credentials.access_token
            if isinstance(credentials, ApiKeyCredentials):
                return credentials.key
        
        # 3. Fallback: Check OpenCode's auth file
        token = self._get_opencode_token(provider)
        if token:
            logger.info(f"Using token from OpenCode for {provider}")
            return token
        
        return None
    
    def _get_opencode_token(self, provider: str) -> Optional[str]:
        """Read token from OpenCode's auth file as fallback."""
        import json
        opencode_path = os.path.expanduser("~/.local/share/opencode/auth.json")
        
        if not os.path.exists(opencode_path):
            return None
        
        try:
            with open(opencode_path, 'r') as f:
                data = json.load(f)
            
            provider_data = data.get(provider, {})
            if provider_data.get("type") == "oauth":
                access_token = provider_data.get("access")
                expires_ms = provider_data.get("expires", 0)
                
                if access_token and (expires_ms / 1000) > time.time():
                    return access_token
                    
                # Token expired, try refresh
                refresh_token = provider_data.get("refresh")
                if refresh_token and provider == "anthropic":
                    return self._refresh_opencode_token(refresh_token)
        except Exception as e:
            logger.debug(f"Could not read OpenCode auth: {e}")
        
        return None
    
    def _refresh_opencode_token(self, refresh_token: str) -> Optional[str]:
        """Refresh OpenCode's Anthropic token."""
        try:
            oauth = self._get_oauth_provider("anthropic")
            token_response = oauth.refresh_access_token(refresh_token)
            return token_response.get("access_token")
        except Exception as e:
            logger.debug(f"Could not refresh OpenCode token: {e}")
            return None
    
    def login_with_api_key(self, provider: str, api_key: str) -> None:
        """
        Store API key credentials.
        
        Args:
            provider: Provider name
            api_key: API key to store
        """
        credentials = ApiKeyCredentials(provider=provider, key=api_key)
        self._store.set(provider, credentials)
        logger.info(f"Stored API key for {provider}")
    
    def login_with_oauth(
        self,
        provider: str = "anthropic",
        open_browser: bool = True,
    ) -> None:
        """
        Initiate OAuth login flow.
        
        Args:
            provider: Provider name (currently only "anthropic" supported)
            open_browser: Whether to auto-open browser
        """
        oauth = self._get_oauth_provider(provider)
        token_response = interactive_oauth_login(oauth=oauth, open_browser=open_browser)
        
        credentials = OAuthCredentials(
            provider=provider,
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            expires_at=time.time() + token_response.get("expires_in", 3600),
        )
        
        self._store.set(provider, credentials)
        logger.info(f"OAuth login successful for {provider}")
    
    def logout(self, provider: str) -> bool:
        """
        Remove stored credentials for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if credentials were removed, False if none existed
        """
        existing = self._store.get(provider)
        self._store.remove(provider)
        
        if existing:
            logger.info(f"Logged out from {provider}")
            return True
        return False
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """
        List all stored credentials with redacted sensitive data.
        
        Returns:
            List of credential info dicts with:
            - provider: Provider name
            - type: "oauth" or "api_key"
            - key: Redacted key (for api_key type)
            - expires: Expiration info (for oauth type)
        """
        result = []
        
        for provider in self._store.list_providers():
            credentials = self._store.get(provider)
            if credentials is None:
                continue
            
            info: Dict[str, Any] = {
                "provider": provider,
                "type": credentials.type,
            }
            
            if isinstance(credentials, OAuthCredentials):
                # Show expiration status
                if credentials.expires_at:
                    remaining = credentials.expires_at - time.time()
                    if remaining > 0:
                        hours = int(remaining // 3600)
                        minutes = int((remaining % 3600) // 60)
                        info["expires"] = f"{hours}h {minutes}m"
                    else:
                        info["expires"] = "expired"
                info["has_refresh_token"] = credentials.refresh_token is not None
                
            elif isinstance(credentials, ApiKeyCredentials):
                # Redact key - show first 7 and last 4 chars
                key = credentials.key
                if len(key) > 15:
                    info["key"] = f"{key[:7]}...{key[-4:]}"
                else:
                    info["key"] = "***"
            
            result.append(info)
        
        return result


def get_anthropic_base_url() -> Optional[str]:
    """Get Anthropic API base URL for proxy support (e.g., antigravity-claude-proxy)."""
    return os.environ.get(ANTHROPIC_BASE_URL_ENV)


def get_claude_token() -> str:
    """
    Get Claude/Anthropic API token.
    
    Convenience function using singleton AuthManager.
    
    Returns:
        API token for Claude
        
    Raises:
        AuthError: If no credentials available
    """
    manager = _get_default_manager()
    token = manager.get_api_key("anthropic")
    
    if token is None:
        raise AuthError(
            "No Anthropic credentials found. "
            "Set ANTHROPIC_API_KEY environment variable or run login."
        )
    
    return token
