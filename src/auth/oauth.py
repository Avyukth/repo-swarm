"""
OAuth module for Claude/Anthropic authentication.

Provides PKCE OAuth flow for CLI-based authentication with Claude Max/Pro subscriptions.
Follows opencode patterns for consistency.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx


class OAuthError(Exception):
    """Raised when OAuth operations fail."""
    pass


class OAuthProvider(ABC):
    """Abstract base class for OAuth providers."""
    
    @abstractmethod
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge pair."""
        ...
    
    @abstractmethod
    def get_authorization_url(self) -> str:
        """Generate authorization URL for user to visit."""
        ...
    
    @abstractmethod
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens."""
        ...
    
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        ...


class ClaudeOAuth(OAuthProvider):
    """Claude/Anthropic OAuth implementation with PKCE."""
    
    # OAuth configuration - using OpenCode's public client_id
    # These are public constants used by OpenCode and other OSS projects
    # See: https://github.com/sst/opencode
    AUTHORIZATION_URL = "https://claude.ai/oauth/authorize"
    TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
    CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"  # OpenCode's public client_id
    REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
    SCOPES = ["org:create_api_key", "user:profile", "user:inference"]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        authorization_url: Optional[str] = None,
        token_url: Optional[str] = None,
    ):
        """
        Initialize Claude OAuth provider.
        
        Args:
            client_id: OAuth client ID (defaults to repo-swarm)
            authorization_url: Custom authorization endpoint
            token_url: Custom token endpoint
        """
        self.client_id = client_id or self.CLIENT_ID
        self.authorization_url = authorization_url or self.AUTHORIZATION_URL
        self.token_url = token_url or self.TOKEN_URL
        
        # PKCE state
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        
        # CSRF protection
        self.state: Optional[str] = None
    
    @property
    def redirect_uri(self) -> str:
        """Get the redirect URI for OAuth callback."""
        return self.REDIRECT_URI
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code_verifier and code_challenge.
        
        Uses cryptographic randomness per RFC 7636.
        Code challenge is SHA256 hash of verifier, base64url encoded.
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate 32 bytes of random data (256 bits of entropy)
        # This gives us a 43-character base64url string (minimum per RFC 7636)
        random_bytes = secrets.token_bytes(32)
        verifier = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
        
        # Generate challenge: base64url(sha256(verifier))
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        
        # Store for later use
        self.code_verifier = verifier
        self.code_challenge = challenge
        
        return verifier, challenge
    
    def get_authorization_url(self) -> str:
        """
        Generate authorization URL for user to visit.
        
        Generates new PKCE pair and state for each call.
        
        Returns:
            Full authorization URL with all required parameters
        """
        # Generate fresh PKCE pair and state
        self.generate_pkce_pair()
        self.state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "state": self.state,
            "scope": " ".join(self.SCOPES),
        }
        
        return f"{self.authorization_url}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access/refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Token response with access_token, refresh_token, expires_in
            
        Raises:
            OAuthError: If no code_verifier exists (PKCE not initialized)
            httpx.HTTPStatusError: If token request fails
        """
        if not self.code_verifier:
            raise OAuthError("No code verifier - call get_authorization_url() first")
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": self.code_verifier,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        
        with httpx.Client() as client:
            response = client.post(
                self.token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Token response with new access_token, optionally new refresh_token
            
        Raises:
            httpx.HTTPStatusError: If refresh request fails
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }
        
        with httpx.Client() as client:
            response = client.post(
                self.token_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()


def interactive_oauth_login(
    oauth: Optional[ClaudeOAuth] = None,
    open_browser: bool = True,
) -> Dict[str, Any]:
    """
    Run interactive OAuth login flow for CLI.
    
    Opens browser to authorization URL. User copies the displayed code.
    Uses OpenCode's console-based redirect flow.
    """
    import webbrowser
    
    if oauth is None:
        oauth = ClaudeOAuth()
    
    auth_url = oauth.get_authorization_url()
    
    print("\n" + "=" * 60)
    print("Claude OAuth Authentication")
    print("=" * 60)
    
    if open_browser:
        print("\nOpening browser for authentication...")
        webbrowser.open(auth_url)
    else:
        print(f"\nOpen this URL in your browser:\n{auth_url}")
    
    print("\n1. Log in with your Claude/Anthropic account")
    print("2. Authorize the application")
    print("3. Copy the authorization code displayed")
    print("-" * 60)
    
    code = input("\nPaste the authorization code here: ").strip()
    
    if not code:
        raise OAuthError("No authorization code provided")
    
    return oauth.exchange_code_for_tokens(code)
