# Claude Authentication Integration for Repo-Swarm

## Quick Start: Antigravity Proxy (Recommended)

The simplest way to use Claude with repo-swarm is via the **antigravity-claude-proxy**. This provides free Claude access through Google OAuth.

### Setup (One-Time)

```bash
# 1. Add your Google account
npx antigravity-claude-proxy accounts add

# 2. Start the proxy (keep running in background)
npx antigravity-claude-proxy start
```

### Configure Environment

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
export ANTHROPIC_BASE_URL="http://localhost:8080"
export ANTHROPIC_API_KEY="test"
```

### Run Investigation

```bash
# Check proxy is running
mise proxy-status

# Direct investigation (no Temporal, fastest for single repos)
mise investigate-direct https://github.com/user/repo

# With Temporal workflow (requires Temporal server)
mise proxy-investigate https://github.com/user/repo
```

### Available Models (via Antigravity)

| Model | Description |
|-------|-------------|
| `claude-opus-4-5-thinking` | Claude Opus 4.5 with extended thinking (default) |
| `claude-sonnet-4-5-thinking` | Claude Sonnet 4.5 with thinking |
| `claude-sonnet-4-5` | Claude Sonnet 4.5 without thinking |
| `gemini-3-pro-high` | Gemini 3 Pro High |
| `gemini-3-flash` | Gemini 3 Flash |

### Mise Tasks Reference

| Task | Description |
|------|-------------|
| `mise proxy-status` | Check if proxy is running and account status |
| `mise proxy-start` | Start the antigravity proxy server |
| `mise proxy-add-account` | Add a Google account for OAuth |
| `mise proxy-accounts` | Manage proxy accounts |
| `mise proxy-investigate <repo>` | Investigate with proxy auto-configured |

---

## Overview

This document outlines Claude authentication in repo-swarm. We support:
1. **Antigravity Proxy** (recommended) - Free Claude via Google OAuth
2. **Direct API Key** - Traditional `ANTHROPIC_API_KEY`
3. **OAuth Tokens** - Claude Max/Pro subscriptions (via OpenCode integration)

---

## Architecture

```
┌─────────────────────┐
│   repo-swarm        │
│   ClaudeAnalyzer    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  ANTHROPIC_BASE_URL │────▶│  antigravity-proxy  │──▶ Google Cloud Code API
│  localhost:8080     │     │  (handles OAuth)    │
└─────────────────────┘     └─────────────────────┘
          │
          ▼ (if not set)
┌─────────────────────┐
│  api.anthropic.com  │──▶ Direct Anthropic API
│  (requires API key) │
└─────────────────────┘
```

## Authentication Priority

1. **Environment Variable**: `ANTHROPIC_API_KEY` (highest)
2. **Stored Credentials**: `~/.repo-swarm/auth.json`
3. **OpenCode Fallback**: `~/.local/share/opencode/auth.json`

When `ANTHROPIC_BASE_URL` is set, requests route through the proxy.

---

## Current Implementation

**Key Files:**
| File | Purpose |
|------|---------|
| `src/auth/manager.py` | Unified auth with proxy detection |
| `src/auth/credentials.py` | Secure credential storage |
| `src/auth/oauth.py` | OAuth PKCE flow implementation |
| `src/investigator/core/claude_analyzer.py` | Anthropic SDK wrapper with `base_url` support |
| `src/investigator/core/config.py` | Model config (default: `claude-opus-4-5-thinking`) |

---

## OpenCode Authentication Architecture

OpenCode implements a comprehensive multi-layered authentication system. Here's how it works:

### Authentication Storage

```
~/.local/share/opencode/auth.json    # Provider credentials (API keys, OAuth tokens)
~/.local/share/opencode/mcp-auth.json # MCP server OAuth tokens
```

### Credential Types

```typescript
// From packages/opencode/src/auth/index.ts
export const Oauth = z.object({
  type: z.literal("oauth"),
  refresh: z.string(),      // Refresh token
  access: z.string(),       // Access token
  expires: z.number(),      // Expiration timestamp
  enterpriseUrl: z.string().optional(),
})

export const Api = z.object({
  type: z.literal("api"),
  key: z.string(),          // Direct API key
})
```

### Claude OAuth Constants (Public - Used Industry-Wide)

```typescript
// From multiple OSS projects (charmbracelet/crush, plandex, Fabric, etc.)
const CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
const OAUTH_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
const OAUTH_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
const OAUTH_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
const OAUTH_SCOPES = "org:create_api_key user:profile user:inference"
```

### OAuth Flow (PKCE)

```
1. Generate code_verifier (random string)
2. Generate code_challenge = base64url(sha256(code_verifier))
3. Open browser to OAUTH_AUTHORIZE_URL with:
   - client_id
   - redirect_uri
   - scope
   - code_challenge
   - code_challenge_method=S256
   - response_type=code
4. User authenticates on claude.ai
5. Receive authorization code
6. Exchange code for tokens at OAUTH_TOKEN_URL with:
   - grant_type=authorization_code
   - client_id
   - code
   - code_verifier
   - redirect_uri
7. Store access_token, refresh_token, expires_in
8. Refresh token before expiration
```

---

## Implementation Plan for Repo-Swarm

### Phase 1: Authentication Module

Create a new authentication module that handles both API key and OAuth:

```python
# src/auth/__init__.py
```

#### 1.1 Credentials Storage

```python
# src/auth/credentials.py
import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime

@dataclass
class OAuthCredentials:
    """OAuth token credentials."""
    type: str = "oauth"
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0  # Unix timestamp
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired (with 5-minute buffer)."""
        return datetime.now().timestamp() > (self.expires_at - buffer_seconds)

@dataclass
class ApiKeyCredentials:
    """API key credentials."""
    type: str = "api"
    key: str = ""

Credentials = Union[OAuthCredentials, ApiKeyCredentials]

class CredentialStore:
    """Manages credential storage similar to OpenCode's auth.json."""
    
    DEFAULT_PATH = Path.home() / ".repo-swarm" / "auth.json"
    
    def __init__(self, path: Optional[Path] = None):
        self.path = path or self.DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def get(self, provider: str = "anthropic") -> Optional[Credentials]:
        """Get credentials for a provider."""
        data = self._load()
        cred_data = data.get(provider)
        if not cred_data:
            return None
        
        if cred_data.get("type") == "oauth":
            return OAuthCredentials(
                access_token=cred_data.get("access_token", ""),
                refresh_token=cred_data.get("refresh_token", ""),
                expires_at=cred_data.get("expires_at", 0)
            )
        elif cred_data.get("type") == "api":
            return ApiKeyCredentials(key=cred_data.get("key", ""))
        return None
    
    def set(self, provider: str, credentials: Credentials) -> None:
        """Store credentials for a provider."""
        data = self._load()
        if isinstance(credentials, OAuthCredentials):
            data[provider] = {
                "type": "oauth",
                "access_token": credentials.access_token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expires_at
            }
        elif isinstance(credentials, ApiKeyCredentials):
            data[provider] = {
                "type": "api",
                "key": credentials.key
            }
        self._save(data)
    
    def remove(self, provider: str) -> None:
        """Remove credentials for a provider."""
        data = self._load()
        data.pop(provider, None)
        self._save(data)
    
    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}
    
    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2))
        # Set restrictive permissions (owner read/write only)
        os.chmod(self.path, 0o600)
```

#### 1.2 OAuth Flow Implementation

```python
# src/auth/oauth.py
import os
import hashlib
import base64
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Tuple
import httpx

# Claude OAuth Constants (public, used by many projects)
CLAUDE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
CLAUDE_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
CLAUDE_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
CLAUDE_SCOPES = "org:create_api_key user:profile user:inference"

class ClaudeOAuth:
    """Handles Claude OAuth authentication flow."""
    
    def __init__(self):
        self.code_verifier: Optional[str] = None
        self.state: Optional[str] = None
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        # Generate random code verifier (43-128 characters)
        self.code_verifier = secrets.token_urlsafe(64)
        
        # Generate code challenge (SHA256 hash, base64url encoded)
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        
        return self.code_verifier, code_challenge
    
    def get_authorization_url(self) -> str:
        """Generate the OAuth authorization URL."""
        self.state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        params = {
            "client_id": CLAUDE_CLIENT_ID,
            "redirect_uri": CLAUDE_REDIRECT_URI,
            "response_type": "code",
            "scope": CLAUDE_SCOPES,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": self.state,
            "code": "true",  # Console mode - returns code to display
        }
        
        return f"{CLAUDE_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access/refresh tokens."""
        if not self.code_verifier:
            raise ValueError("No code verifier available. Call get_authorization_url first.")
        
        with httpx.Client() as client:
            response = client.post(
                CLAUDE_TOKEN_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type": "authorization_code",
                    "client_id": CLAUDE_CLIENT_ID,
                    "code": code,
                    "redirect_uri": CLAUDE_REDIRECT_URI,
                    "code_verifier": self.code_verifier,
                }
            )
            response.raise_for_status()
            return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh the access token using refresh token."""
        with httpx.Client() as client:
            response = client.post(
                CLAUDE_TOKEN_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type": "refresh_token",
                    "client_id": CLAUDE_CLIENT_ID,
                    "refresh_token": refresh_token,
                }
            )
            response.raise_for_status()
            return response.json()


def interactive_oauth_login() -> Optional[dict]:
    """
    Perform interactive OAuth login flow.
    
    Returns:
        Token response dict with access_token, refresh_token, expires_in
    """
    oauth = ClaudeOAuth()
    auth_url = oauth.get_authorization_url()
    
    print("\n" + "=" * 60)
    print("Claude OAuth Authentication")
    print("=" * 60)
    print("\n1. Open this URL in your browser:")
    print(f"\n   {auth_url}\n")
    print("2. Log in to your Claude account")
    print("3. Copy the authorization code displayed")
    print("\n" + "-" * 60)
    
    # Try to open browser automatically
    try:
        webbrowser.open(auth_url)
        print("(Browser opened automatically)")
    except Exception:
        print("(Please open the URL manually)")
    
    # Get authorization code from user
    code = input("\nEnter the authorization code: ").strip()
    
    if not code:
        print("No code provided. Authentication cancelled.")
        return None
    
    try:
        tokens = oauth.exchange_code_for_tokens(code)
        print("\nAuthentication successful!")
        return tokens
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        return None
```

#### 1.3 Unified Authentication Manager

```python
# src/auth/manager.py
import os
import logging
from typing import Optional
from datetime import datetime

from .credentials import CredentialStore, OAuthCredentials, ApiKeyCredentials
from .oauth import ClaudeOAuth

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Unified authentication manager supporting API keys and OAuth.
    Similar to OpenCode's Auth + ProviderAuth namespaces.
    """
    
    def __init__(self, credential_store: Optional[CredentialStore] = None):
        self.store = credential_store or CredentialStore()
        self.oauth = ClaudeOAuth()
    
    def get_api_key(self, provider: str = "anthropic") -> Optional[str]:
        """
        Get API key for Claude, checking multiple sources in priority order:
        1. Environment variable (ANTHROPIC_API_KEY)
        2. Stored OAuth token (refreshed if needed)
        3. Stored API key
        """
        # Priority 1: Environment variable
        env_key = os.getenv("ANTHROPIC_API_KEY")
        if env_key:
            logger.debug("Using API key from ANTHROPIC_API_KEY environment variable")
            return env_key
        
        # Priority 2+3: Stored credentials
        creds = self.store.get(provider)
        
        if isinstance(creds, OAuthCredentials):
            # Refresh if expired
            if creds.is_expired():
                logger.info("OAuth token expired, refreshing...")
                creds = self._refresh_oauth_token(provider, creds)
            
            if creds and creds.access_token:
                logger.debug("Using OAuth access token")
                return creds.access_token
        
        elif isinstance(creds, ApiKeyCredentials):
            logger.debug("Using stored API key")
            return creds.key
        
        return None
    
    def _refresh_oauth_token(self, provider: str, creds: OAuthCredentials) -> Optional[OAuthCredentials]:
        """Refresh OAuth token and update storage."""
        try:
            tokens = self.oauth.refresh_access_token(creds.refresh_token)
            
            new_creds = OAuthCredentials(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", creds.refresh_token),
                expires_at=datetime.now().timestamp() + tokens.get("expires_in", 3600)
            )
            
            self.store.set(provider, new_creds)
            logger.info("OAuth token refreshed successfully")
            return new_creds
            
        except Exception as e:
            logger.error(f"Failed to refresh OAuth token: {e}")
            return None
    
    def login_with_api_key(self, api_key: str, provider: str = "anthropic") -> None:
        """Store an API key."""
        self.store.set(provider, ApiKeyCredentials(key=api_key))
        logger.info(f"API key stored for {provider}")
    
    def login_with_oauth(self, provider: str = "anthropic") -> bool:
        """
        Interactive OAuth login flow.
        
        Returns:
            True if login successful, False otherwise
        """
        from .oauth import interactive_oauth_login
        
        tokens = interactive_oauth_login()
        if not tokens:
            return False
        
        creds = OAuthCredentials(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_at=datetime.now().timestamp() + tokens.get("expires_in", 3600)
        )
        
        self.store.set(provider, creds)
        logger.info(f"OAuth credentials stored for {provider}")
        return True
    
    def logout(self, provider: str = "anthropic") -> None:
        """Remove stored credentials."""
        self.store.remove(provider)
        logger.info(f"Credentials removed for {provider}")
    
    def list_credentials(self) -> dict:
        """List all stored credentials (without exposing secrets)."""
        data = self.store._load()
        result = {}
        for provider, creds in data.items():
            cred_type = creds.get("type", "unknown")
            if cred_type == "oauth":
                expires_at = creds.get("expires_at", 0)
                is_expired = datetime.now().timestamp() > expires_at
                result[provider] = {
                    "type": "oauth",
                    "status": "expired" if is_expired else "valid",
                    "expires": datetime.fromtimestamp(expires_at).isoformat() if expires_at else "unknown"
                }
            elif cred_type == "api":
                key = creds.get("key", "")
                result[provider] = {
                    "type": "api",
                    "key_preview": f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
                }
        return result
```

### Phase 2: Integration with ClaudeAnalyzer

Modify the existing ClaudeAnalyzer to use the new auth system:

```python
# src/investigator/core/claude_analyzer.py (modified)
from anthropic import Anthropic
from typing import Optional
from .config import Config

# Import auth manager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ClaudeAnalyzer:
    """Handles Claude API interactions for analysis."""
    
    def __init__(self, api_key: Optional[str] = None, logger=None):
        """
        Initialize the Claude analyzer.
        
        Args:
            api_key: Optional API key. If not provided, uses AuthManager to get credentials.
            logger: Logger instance
        """
        self.logger = logger
        
        # Get API key using auth manager if not provided
        if api_key is None:
            try:
                from auth.manager import AuthManager
                auth_manager = AuthManager()
                api_key = auth_manager.get_api_key("anthropic")
            except ImportError:
                # Fallback to environment variable
                api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            raise ValueError(
                "Claude API key is required. Set ANTHROPIC_API_KEY environment variable, "
                "use 'repo-swarm auth login' for OAuth, or pass api_key parameter."
            )
        
        self.client = Anthropic(api_key=api_key)
    
    # ... rest of the class remains the same
```

### Phase 3: CLI Commands

Add authentication commands to the CLI:

```python
# src/cli/auth.py
import argparse
import sys
from auth.manager import AuthManager

def cmd_login(args):
    """Handle login command."""
    auth = AuthManager()
    
    if args.method == "oauth":
        print("Starting OAuth authentication flow...")
        if auth.login_with_oauth():
            print("Login successful! You can now use Claude with your subscription.")
        else:
            print("Login failed.")
            sys.exit(1)
    
    elif args.method == "api":
        api_key = args.key or input("Enter your Anthropic API key: ").strip()
        if not api_key:
            print("No API key provided.")
            sys.exit(1)
        auth.login_with_api_key(api_key)
        print("API key saved successfully!")

def cmd_logout(args):
    """Handle logout command."""
    auth = AuthManager()
    auth.logout()
    print("Logged out successfully.")

def cmd_list(args):
    """Handle list credentials command."""
    auth = AuthManager()
    creds = auth.list_credentials()
    
    if not creds:
        print("No credentials stored.")
        return
    
    print("\nStored Credentials:")
    print("-" * 40)
    for provider, info in creds.items():
        print(f"\n{provider}:")
        for key, value in info.items():
            print(f"  {key}: {value}")

def main():
    parser = argparse.ArgumentParser(description="Repo-Swarm Authentication")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Log in to Claude")
    login_parser.add_argument(
        "--method", "-m",
        choices=["oauth", "api"],
        default="oauth",
        help="Authentication method (default: oauth)"
    )
    login_parser.add_argument(
        "--key", "-k",
        help="API key (for api method)"
    )
    login_parser.set_defaults(func=cmd_login)
    
    # Logout command
    logout_parser = subparsers.add_parser("logout", help="Log out from Claude")
    logout_parser.set_defaults(func=cmd_logout)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List stored credentials")
    list_parser.set_defaults(func=cmd_list)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
```

### Phase 4: Temporal Worker Integration

Update the worker to support both authentication methods:

```python
# src/worker.py (modified validation)
async def validate_claude_credentials():
    """Validate Claude API credentials are available."""
    try:
        from auth.manager import AuthManager
        auth = AuthManager()
        api_key = auth.get_api_key("anthropic")
        
        if api_key:
            logger.info("Claude credentials validated successfully")
            return True
        
        logger.error("No Claude credentials found")
        logger.info("Run 'python -m cli.auth login' to authenticate")
        return False
        
    except ImportError:
        # Fallback to environment variable only
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            logger.info("Using ANTHROPIC_API_KEY environment variable")
            return True
        
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        return False
```

---

## Directory Structure

```
repo-swarm/
├── src/
│   ├── auth/                          # NEW: Authentication module
│   │   ├── __init__.py
│   │   ├── credentials.py             # Credential storage
│   │   ├── oauth.py                   # OAuth flow implementation
│   │   └── manager.py                 # Unified auth manager
│   ├── cli/                           # NEW: CLI commands
│   │   ├── __init__.py
│   │   └── auth.py                    # Auth CLI commands
│   ├── investigator/
│   │   └── core/
│   │       └── claude_analyzer.py     # MODIFIED: Use auth manager
│   └── worker.py                      # MODIFIED: Credential validation
├── .repo-swarm/                       # NEW: User config directory
│   └── auth.json                      # Credential storage
└── pyproject.toml                     # MODIFIED: Add dependencies
```

---

## Dependencies to Add

```toml
# pyproject.toml additions
[project]
dependencies = [
    # ... existing deps
    "httpx>=0.27.0",  # For OAuth HTTP requests
]
```

---

## Usage Examples

### Initial Setup with OAuth (Claude Max/Pro)

```bash
# Authenticate using OAuth (recommended for Claude Max subscribers)
python -m cli.auth login --method oauth

# This opens browser for authentication
# Copy the code and paste it when prompted
```

### Using API Key

```bash
# Authenticate using API key
python -m cli.auth login --method api --key "sk-ant-..."

# Or set environment variable (highest priority)
export ANTHROPIC_API_KEY="sk-ant-..."
```

### List Credentials

```bash
python -m cli.auth list
```

### Logout

```bash
python -m cli.auth logout
```

---

## Security Considerations

1. **File Permissions**: Auth file uses `0o600` (owner read/write only)
2. **Token Storage**: Tokens stored locally, not in version control
3. **PKCE Flow**: Uses Proof Key for Code Exchange for secure OAuth
4. **Token Refresh**: Automatic refresh before expiration (5-minute buffer)
5. **Environment Priority**: Environment variables take precedence for CI/CD

---

## Migration Path

### For Existing Users

1. **No changes required** - `ANTHROPIC_API_KEY` continues to work
2. **Optional OAuth** - Run `auth login` for OAuth support
3. **Gradual adoption** - Both methods work simultaneously

### Priority Order

1. `ANTHROPIC_API_KEY` environment variable
2. OAuth tokens (auto-refreshed)
3. Stored API key

---

## Comparison: OpenCode vs Proposed Repo-Swarm Auth

| Feature | OpenCode | Repo-Swarm (Proposed) |
|---------|----------|----------------------|
| API Key Auth | Yes | Yes |
| OAuth Flow | Yes (plugin-based) | Yes (built-in) |
| Token Storage | `~/.local/share/opencode/auth.json` | `~/.repo-swarm/auth.json` |
| Token Refresh | Automatic | Automatic |
| PKCE Support | Yes | Yes |
| CLI Commands | `/connect`, `/logout` | `auth login`, `auth logout` |
| Multi-provider | Yes (75+ providers) | No (Claude only) |
| Plugin System | Yes | No (not needed) |
| MCP OAuth | Yes | No (not needed) |

---

## Code Flow: API Key vs OAuth

This section shows exactly how the code flow changes when using OAuth instead of API keys.

### Flow Comparison Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CURRENT FLOW (API Key)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Environment                                                                │
│  ┌────────────────────┐                                                     │
│  │ ANTHROPIC_API_KEY  │                                                     │
│  │ = "sk-ant-..."     │                                                     │
│  └─────────┬──────────┘                                                     │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ worker.py:42                                                         │   │
│  │   if not os.getenv('ANTHROPIC_API_KEY'):                            │   │
│  │       errors.append("ANTHROPIC_API_KEY required")                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ investigate_activities.py:614                                        │   │
│  │   api_key = os.getenv('ANTHROPIC_API_KEY')  ◄── Direct env read     │   │
│  │   claude_analyzer = ClaudeAnalyzer(api_key, logger)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ claude_analyzer.py:14                                                │   │
│  │   self.client = Anthropic(api_key=api_key)  ◄── SDK initialized     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ claude_analyzer.py:92                                                │   │
│  │   response = self.client.messages.create(...)  ◄── API call         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         OAUTH FLOW (Claude Max/Pro)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ONE-TIME: User runs `repo-swarm auth login`                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Generate PKCE verifier/challenge                                  │   │
│  │ 2. Open browser → https://claude.ai/oauth/authorize                 │   │
│  │ 3. User authenticates with Anthropic account                        │   │
│  │ 4. Receive authorization code                                        │   │
│  │ 5. Exchange code → access_token + refresh_token                     │   │
│  │ 6. Store in ~/.repo-swarm/auth.json                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  RUNTIME: Same as API key, but token comes from storage                    │
│  ┌────────────────────┐     ┌────────────────────┐                         │
│  │ ~/.repo-swarm/     │     │ Environment        │                         │
│  │   auth.json        │     │ ANTHROPIC_API_KEY  │  (optional override)    │
│  │ {                  │     └─────────┬──────────┘                         │
│  │   "access_token"   │               │                                    │
│  │   "refresh_token"  │               │ Priority 1 (if set)                │
│  │   "expires_at"     │               │                                    │
│  │ }                  │               │                                    │
│  └─────────┬──────────┘               │                                    │
│            │ Priority 2               │                                    │
│            └───────────┬──────────────┘                                    │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ auth/manager.py:get_api_key()    ◄── NEW: Unified credential getter │   │
│  │   1. Check ANTHROPIC_API_KEY env (priority)                         │   │
│  │   2. Check stored OAuth token                                        │   │
│  │   3. If OAuth expired → auto-refresh                                │   │
│  │   4. Return token (same format as API key!)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                        │                                                    │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ claude_analyzer.py:14  (UNCHANGED!)                                  │   │
│  │   self.client = Anthropic(api_key=api_key)                          │   │
│  │                                    ▲                                 │   │
│  │              OAuth access_token works exactly like API key!         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                        │                                                    │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ claude_analyzer.py:92  (UNCHANGED!)                                  │   │
│  │   response = self.client.messages.create(...)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Insight

**OAuth `access_token` IS functionally equivalent to an API key for the Anthropic SDK.**

The SDK doesn't care where the token comes from - it just needs a valid bearer token.

---

## Minimal Code Changes for Feature Parity

### Files to MODIFY (3 files)

```
src/
├── worker.py                           # Change validation logic
├── activities/investigate_activities.py # Change how api_key is obtained
└── investigator/investigator.py        # Change how api_key is obtained
```

### Files to ADD (4 files)

```
src/
└── auth/
    ├── __init__.py
    ├── credentials.py    # Token storage
    ├── oauth.py          # OAuth flow
    └── manager.py        # Unified get_api_key()
```

---

### Exact Changes per File

#### 1. `src/auth/manager.py` (NEW - Core Logic)

```python
"""Unified authentication manager - the ONLY new abstraction needed."""
import os
from datetime import datetime
from typing import Optional

from .credentials import CredentialStore, OAuthCredentials
from .oauth import ClaudeOAuth

class AuthManager:
    """Single entry point for getting Claude credentials."""
    
    def __init__(self):
        self.store = CredentialStore()
        self.oauth = ClaudeOAuth()
    
    def get_api_key(self) -> Optional[str]:
        """
        Get API key/token for Claude. Checks in order:
        1. ANTHROPIC_API_KEY env var (for CI/CD, backward compat)
        2. Stored OAuth token (auto-refreshed if expired)
        3. Stored API key
        
        Returns:
            Valid token string, or None if no credentials found
        """
        # Priority 1: Environment variable (backward compatible)
        env_key = os.getenv("ANTHROPIC_API_KEY")
        if env_key:
            return env_key
        
        # Priority 2: Stored credentials
        creds = self.store.get("anthropic")
        if not creds:
            return None
        
        # Handle OAuth tokens
        if isinstance(creds, OAuthCredentials):
            if creds.is_expired():
                creds = self._refresh_token(creds)
                if not creds:
                    return None
            return creds.access_token
        
        # Handle API keys
        return creds.key if hasattr(creds, 'key') else None
    
    def _refresh_token(self, creds: OAuthCredentials) -> Optional[OAuthCredentials]:
        """Refresh expired OAuth token."""
        try:
            tokens = self.oauth.refresh_access_token(creds.refresh_token)
            new_creds = OAuthCredentials(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", creds.refresh_token),
                expires_at=datetime.now().timestamp() + tokens.get("expires_in", 3600)
            )
            self.store.set("anthropic", new_creds)
            return new_creds
        except Exception:
            return None

# Singleton for easy import
_manager = None

def get_claude_token() -> Optional[str]:
    """Convenience function - drop-in replacement for os.getenv('ANTHROPIC_API_KEY')"""
    global _manager
    if _manager is None:
        _manager = AuthManager()
    return _manager.get_api_key()
```

#### 2. `src/activities/investigate_activities.py` (MODIFY - 2 lines changed)

```diff
 @activity.defn
 async def analyze_with_claude_context(input_params: AnalyzeWithClaudeInput) -> AnalyzeWithClaudeOutput:
     # ... existing code ...
     
-        # Initialize Claude analyzer
-        api_key = os.getenv('ANTHROPIC_API_KEY')
-        if not api_key:
-            raise Exception("Claude API key not configured. Set ANTHROPIC_API_KEY environment variable.")
+        # Initialize Claude analyzer (supports both API key and OAuth)
+        try:
+            from auth.manager import get_claude_token
+            api_key = get_claude_token()
+        except ImportError:
+            api_key = os.getenv('ANTHROPIC_API_KEY')
+        
+        if not api_key:
+            raise Exception(
+                "Claude credentials not configured. Either:\n"
+                "  1. Set ANTHROPIC_API_KEY environment variable, or\n"
+                "  2. Run 'python -m auth.cli login' for OAuth"
+            )
             
         claude_analyzer = ClaudeAnalyzer(api_key, logger)
```

#### 3. `src/investigator/investigator.py` (MODIFY - 2 lines changed)

```diff
 class ClaudeInvestigator:
     def __init__(self, api_key: Optional[str] = None, log_level: str = "INFO", 
                  workflow_context: Optional[Any] = None):
-        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
+        # Support both API key and OAuth
+        if api_key is None:
+            try:
+                from auth.manager import get_claude_token
+                api_key = get_claude_token()
+            except ImportError:
+                api_key = os.getenv('ANTHROPIC_API_KEY')
+        
+        self.api_key = api_key
         if not self.api_key:
-            raise ValueError("Claude API key is required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
+            raise ValueError(
+                "Claude credentials required. Either:\n"
+                "  1. Set ANTHROPIC_API_KEY environment variable\n"
+                "  2. Run 'python -m auth.cli login' for OAuth\n"
+                "  3. Pass api_key parameter"
+            )
```

#### 4. `src/worker.py` (MODIFY - validation logic)

```diff
 def validate_environment():
     # ... existing code ...
     
-    # Required API keys
-    if not os.getenv('ANTHROPIC_API_KEY'):
-        errors.append("ANTHROPIC_API_KEY environment variable is required for Claude API access")
-    else:
-        logger.info("  ✓ Anthropic API key present")
+    # Claude credentials (API key OR OAuth)
+    try:
+        from auth.manager import get_claude_token
+        token = get_claude_token()
+        if token:
+            if os.getenv('ANTHROPIC_API_KEY'):
+                logger.info("  ✓ Claude: Using API key from environment")
+            else:
+                logger.info("  ✓ Claude: Using OAuth token")
+        else:
+            errors.append(
+                "Claude credentials required. Either:\n"
+                "      - Set ANTHROPIC_API_KEY environment variable, or\n"
+                "      - Run 'python -m auth.cli login' for OAuth"
+            )
+    except ImportError:
+        # Fallback if auth module not available
+        if not os.getenv('ANTHROPIC_API_KEY'):
+            errors.append("ANTHROPIC_API_KEY environment variable is required")
+        else:
+            logger.info("  ✓ Anthropic API key present")
```

---

### What Stays EXACTLY The Same

| Component | Why No Change Needed |
|-----------|---------------------|
| `ClaudeAnalyzer.__init__` | Already accepts `api_key` param - works with OAuth token |
| `ClaudeAnalyzer.analyze_with_context` | No change - uses `self.client` |
| `Anthropic(api_key=...)` SDK call | OAuth access_token works identically to API key |
| All API calls | Bearer token auth is the same |
| Response handling | No change |
| Error handling | No change |
| Config/model selection | No change |

---

### Change Summary

| Change Type | Files | Lines Changed |
|-------------|-------|---------------|
| **ADD** | `src/auth/__init__.py` | ~5 |
| **ADD** | `src/auth/credentials.py` | ~80 |
| **ADD** | `src/auth/oauth.py` | ~100 |
| **ADD** | `src/auth/manager.py` | ~60 |
| **ADD** | `src/auth/cli.py` | ~50 |
| **MODIFY** | `src/worker.py` | ~15 |
| **MODIFY** | `src/activities/investigate_activities.py` | ~8 |
| **MODIFY** | `src/investigator/investigator.py` | ~8 |
| **Total** | 8 files | ~326 lines |

---

### The Core Abstraction

```python
# Before (scattered in 5 files):
api_key = os.getenv('ANTHROPIC_API_KEY')

# After (one function, multiple sources):
from auth.manager import get_claude_token
api_key = get_claude_token()  # Checks env → OAuth → stored key
```

**That's it.** The rest of the codebase doesn't need to know or care whether the token came from an environment variable, OAuth flow, or stored API key.

---

## References

- [OpenCode Auth Implementation](https://github.com/sst/opencode)
- [Claude OAuth Constants (used by multiple OSS projects)](https://github.com/charmbracelet/crush/blob/main/internal/oauth/claude/oauth.go)
- [Anthropic API Documentation](https://docs.anthropic.com/en/api/)
- [OAuth 2.0 PKCE Flow](https://oauth.net/2/pkce/)
- [CLIProxyAPI - Claude Max API Proxy](https://github.com/router-for-me/CLIProxyAPI)
