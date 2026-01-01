"""
Credential storage module for OAuth and API key authentication.

Provides secure storage of credentials in ~/.repo-swarm/auth.json
with 0600 file permissions for security.
"""

from __future__ import annotations

import json
import os
import stat
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


class CredentialError(Exception):
    """Raised when credential operations fail."""
    pass


@dataclass
class OAuthCredentials:
    """OAuth credentials with access and refresh tokens."""
    
    provider: str
    access_token: str
    expires_at: float
    refresh_token: Optional[str] = None
    type: str = field(default="oauth", init=False)
    
    def __post_init__(self):
        if not self.provider:
            raise ValueError("Provider must be a non-empty string")
        if not self.access_token:
            raise ValueError("Access token must be a non-empty string")
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """
        Check if the token is expired or will expire within the buffer period.
        
        Args:
            buffer_seconds: Number of seconds before expiration to consider expired.
                           Default is 300 (5 minutes).
        
        Returns:
            True if expired or expiring within buffer, False otherwise.
        """
        return time.time() >= (self.expires_at - buffer_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "type": self.type,
            "provider": self.provider,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OAuthCredentials:
        """Deserialize from dictionary."""
        return cls(
            provider=data["provider"],
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=data["expires_at"],
        )


@dataclass
class ApiKeyCredentials:
    """API key credentials for direct API access."""
    
    provider: str
    key: str
    type: str = field(default="api_key", init=False)
    
    def __post_init__(self):
        if not self.provider:
            raise ValueError("Provider must be a non-empty string")
        if not self.key or not self.key.strip():
            raise ValueError("Key must be a non-empty string")
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """API keys don't expire."""
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "type": self.type,
            "provider": self.provider,
            "key": self.key,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApiKeyCredentials:
        """Deserialize from dictionary."""
        return cls(
            provider=data["provider"],
            key=data["key"],
        )


# Type alias for any credential type
Credentials = Union[OAuthCredentials, ApiKeyCredentials]


class CredentialStore:
    """
    Secure credential storage with file-based persistence.
    
    Stores credentials in JSON format with 0600 file permissions.
    Default location: ~/.repo-swarm/auth.json
    """
    
    DEFAULT_PATH = os.path.expanduser("~/.repo-swarm/auth.json")
    
    def __init__(self, path: Optional[str] = None):
        """
        Initialize credential store.
        
        Args:
            path: Custom path for auth file. Defaults to ~/.repo-swarm/auth.json
        """
        self.path = path or self.DEFAULT_PATH
    
    def _ensure_directory(self) -> None:
        """Create parent directory if it doesn't exist."""
        parent = Path(self.path).parent
        parent.mkdir(parents=True, exist_ok=True)
    
    def _read_store(self) -> Dict[str, Any]:
        """Read the credential store from disk."""
        if not os.path.exists(self.path):
            return {}
        
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CredentialError(f"Corrupted credential file: {e}") from e
        
        if not isinstance(data, dict):
            raise CredentialError("Invalid credential file format: expected object")
        
        return data
    
    def _write_store(self, data: Dict[str, Any]) -> None:
        """Write the credential store to disk with secure permissions."""
        self._ensure_directory()
        
        # Write to file
        with open(self.path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Set secure permissions (owner read/write only)
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    
    def _deserialize_credentials(self, data: Dict[str, Any]) -> Credentials:
        """Convert stored dict to appropriate credential type."""
        cred_type = data.get("type")
        
        if cred_type == "oauth":
            return OAuthCredentials.from_dict(data)
        elif cred_type == "api_key":
            return ApiKeyCredentials.from_dict(data)
        else:
            raise CredentialError(f"Unknown credential type: {cred_type}")
    
    def get(self, provider: str) -> Optional[Credentials]:
        """
        Get credentials for a provider.
        
        Args:
            provider: Provider identifier (e.g., 'anthropic', 'openai')
        
        Returns:
            Credentials object or None if not found.
        """
        store = self._read_store()
        
        if provider not in store:
            return None
        
        return self._deserialize_credentials(store[provider])
    
    def set(self, provider: str, credentials: Credentials) -> None:
        """
        Store credentials for a provider.
        
        Args:
            provider: Provider identifier
            credentials: Credentials object to store
        """
        store = self._read_store()
        store[provider] = credentials.to_dict()
        self._write_store(store)
    
    def remove(self, provider: str) -> None:
        """
        Remove credentials for a provider.
        
        Args:
            provider: Provider identifier
        """
        store = self._read_store()
        
        if provider in store:
            del store[provider]
            self._write_store(store)
    
    def list_providers(self) -> list[str]:
        """
        List all providers with stored credentials.
        
        Returns:
            List of provider identifiers.
        """
        store = self._read_store()
        return list(store.keys())
