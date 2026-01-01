"""
Auth module for credential management.

Provides secure storage and retrieval of OAuth and API key credentials,
plus OAuth flow implementations for CLI authentication.
"""

from .credentials import (
    OAuthCredentials,
    ApiKeyCredentials,
    CredentialStore,
    CredentialError,
    Credentials,
)
from .oauth import (
    OAuthProvider,
    OAuthError,
    ClaudeOAuth,
    interactive_oauth_login,
)
from .manager import (
    AuthManager,
    AuthError,
    get_claude_token,
    get_anthropic_base_url,
)

__all__ = [
    # Credentials
    "OAuthCredentials",
    "ApiKeyCredentials",
    "CredentialStore",
    "CredentialError",
    "Credentials",
    # OAuth
    "OAuthProvider",
    "OAuthError",
    "ClaudeOAuth",
    "interactive_oauth_login",
    # Manager
    "AuthManager",
    "AuthError",
    "get_claude_token",
    "get_anthropic_base_url",
]
