"""
Unit tests for the auth credentials module.

Tests for OAuthCredentials, ApiKeyCredentials, and CredentialStore classes.
Following Extreme TDD: RED phase - all tests should fail initially.
"""

import os
import json
import stat
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# These imports will fail until we implement the module (RED phase)
from src.auth.credentials import (
    OAuthCredentials,
    ApiKeyCredentials,
    CredentialStore,
    CredentialError,
)


class TestOAuthCredentials(unittest.TestCase):
    """Test suite for OAuthCredentials dataclass."""

    def test_create_oauth_credentials_with_all_fields(self):
        """Test creating OAuthCredentials with all required fields."""
        expires_at = datetime.now(timezone.utc).timestamp() + 3600
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at,
        )
        
        assert creds.provider == "anthropic"
        assert creds.access_token == "access_token_123"
        assert creds.refresh_token == "refresh_token_456"
        assert creds.expires_at == expires_at

    def test_oauth_credentials_type_field_is_oauth(self):
        """Test that type field is always 'oauth'."""
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token="refresh",
            expires_at=time.time() + 3600,
        )
        
        assert creds.type == "oauth"

    def test_oauth_credentials_requires_provider(self):
        """Test that provider field is required."""
        with pytest.raises((TypeError, ValueError)):
            OAuthCredentials(
                access_token="token",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
            )

    def test_oauth_credentials_requires_access_token(self):
        """Test that access_token field is required."""
        with pytest.raises((TypeError, ValueError)):
            OAuthCredentials(
                provider="anthropic",
                refresh_token="refresh",
                expires_at=time.time() + 3600,
            )

    def test_oauth_credentials_requires_expires_at(self):
        """Test that expires_at field is required."""
        with pytest.raises((TypeError, ValueError)):
            OAuthCredentials(
                provider="anthropic",
                access_token="token",
                refresh_token="refresh",
            )

    def test_oauth_credentials_refresh_token_optional(self):
        """Test that refresh_token can be None."""
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token=None,
            expires_at=time.time() + 3600,
        )
        
        assert creds.refresh_token is None

    def test_oauth_credentials_to_dict(self):
        """Test serialization to dictionary."""
        expires_at = 1704067200.0  # Fixed timestamp for testing
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="access_123",
            refresh_token="refresh_456",
            expires_at=expires_at,
        )
        
        result = creds.to_dict()
        
        assert result == {
            "type": "oauth",
            "provider": "anthropic",
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_at": expires_at,
        }

    def test_oauth_credentials_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "type": "oauth",
            "provider": "anthropic",
            "access_token": "access_123",
            "refresh_token": "refresh_456",
            "expires_at": 1704067200.0,
        }
        
        creds = OAuthCredentials.from_dict(data)
        
        assert creds.provider == "anthropic"
        assert creds.access_token == "access_123"
        assert creds.refresh_token == "refresh_456"
        assert creds.expires_at == 1704067200.0

    def test_oauth_credentials_is_expired_when_past(self):
        """Test is_expired returns True when token has expired."""
        past_time = time.time() - 3600  # 1 hour ago
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token="refresh",
            expires_at=past_time,
        )
        
        assert creds.is_expired() is True

    def test_oauth_credentials_is_not_expired_when_future(self):
        """Test is_expired returns False when token is still valid."""
        future_time = time.time() + 3600  # 1 hour from now
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token="refresh",
            expires_at=future_time,
        )
        
        assert creds.is_expired() is False

    def test_oauth_credentials_is_expired_with_buffer(self):
        """Test is_expired considers buffer time (default 300s)."""
        # Token expires in 200 seconds, but with 300s buffer it's "expired"
        expires_soon = time.time() + 200
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token="refresh",
            expires_at=expires_soon,
        )
        
        # With default 300s buffer, should be considered expired
        assert creds.is_expired(buffer_seconds=300) is True
        
        # With smaller buffer, should not be expired
        assert creds.is_expired(buffer_seconds=100) is False

    def test_oauth_credentials_is_expired_custom_buffer(self):
        """Test is_expired with custom buffer value."""
        expires_at = time.time() + 600  # 10 minutes from now
        
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="token",
            refresh_token="refresh",
            expires_at=expires_at,
        )
        
        # With 500s buffer, not expired (600 - 500 = 100s remaining)
        assert creds.is_expired(buffer_seconds=500) is False
        
        # With 700s buffer, expired (600 - 700 = -100s)
        assert creds.is_expired(buffer_seconds=700) is True


class TestApiKeyCredentials(unittest.TestCase):
    """Test suite for ApiKeyCredentials dataclass."""

    def test_create_api_key_credentials(self):
        """Test creating ApiKeyCredentials with required fields."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        assert creds.provider == "anthropic"
        assert creds.key == "sk-ant-api03-xxxxx"

    def test_api_key_credentials_type_field_is_api_key(self):
        """Test that type field is always 'api_key'."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        assert creds.type == "api_key"

    def test_api_key_credentials_requires_provider(self):
        """Test that provider field is required."""
        with pytest.raises((TypeError, ValueError)):
            ApiKeyCredentials(key="sk-ant-api03-xxxxx")

    def test_api_key_credentials_requires_key(self):
        """Test that key field is required."""
        with pytest.raises((TypeError, ValueError)):
            ApiKeyCredentials(provider="anthropic")

    def test_api_key_credentials_rejects_empty_key(self):
        """Test that empty key is rejected."""
        with pytest.raises(ValueError, match="[Kk]ey.*empty|[Ee]mpty.*key"):
            ApiKeyCredentials(provider="anthropic", key="")

    def test_api_key_credentials_rejects_whitespace_key(self):
        """Test that whitespace-only key is rejected."""
        with pytest.raises(ValueError, match="[Kk]ey.*empty|[Ee]mpty.*key"):
            ApiKeyCredentials(provider="anthropic", key="   ")

    def test_api_key_credentials_to_dict(self):
        """Test serialization to dictionary."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        result = creds.to_dict()
        
        assert result == {
            "type": "api_key",
            "provider": "anthropic",
            "key": "sk-ant-api03-xxxxx",
        }

    def test_api_key_credentials_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "type": "api_key",
            "provider": "anthropic",
            "key": "sk-ant-api03-xxxxx",
        }
        
        creds = ApiKeyCredentials.from_dict(data)
        
        assert creds.provider == "anthropic"
        assert creds.key == "sk-ant-api03-xxxxx"

    def test_api_key_credentials_never_expires(self):
        """Test that API keys don't have expiration (is_expired always False)."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        assert creds.is_expired() is False


class TestCredentialStore(unittest.TestCase):
    """Test suite for CredentialStore class."""

    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.auth_file = os.path.join(self.temp_dir, "auth.json")
        self.store = CredentialStore(path=self.auth_file)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_credential_store_default_path(self):
        """Test that default path is ~/.repo-swarm/auth.json."""
        store = CredentialStore()
        expected_path = os.path.expanduser("~/.repo-swarm/auth.json")
        assert store.path == expected_path

    def test_credential_store_custom_path(self):
        """Test that custom path is respected."""
        custom_path = "/tmp/custom/auth.json"
        store = CredentialStore(path=custom_path)
        assert store.path == custom_path

    def test_set_oauth_credentials(self):
        """Test storing OAuth credentials."""
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="access_123",
            refresh_token="refresh_456",
            expires_at=time.time() + 3600,
        )
        
        self.store.set("anthropic", creds)
        
        # Verify file was created
        assert os.path.exists(self.auth_file)

    def test_get_oauth_credentials(self):
        """Test retrieving stored OAuth credentials."""
        expires_at = time.time() + 3600
        creds = OAuthCredentials(
            provider="anthropic",
            access_token="access_123",
            refresh_token="refresh_456",
            expires_at=expires_at,
        )
        
        self.store.set("anthropic", creds)
        retrieved = self.store.get("anthropic")
        
        assert isinstance(retrieved, OAuthCredentials)
        assert retrieved.access_token == "access_123"
        assert retrieved.refresh_token == "refresh_456"
        assert retrieved.expires_at == expires_at

    def test_set_api_key_credentials(self):
        """Test storing API key credentials."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        self.store.set("anthropic", creds)
        
        assert os.path.exists(self.auth_file)

    def test_get_api_key_credentials(self):
        """Test retrieving stored API key credentials."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        self.store.set("anthropic", creds)
        retrieved = self.store.get("anthropic")
        
        assert isinstance(retrieved, ApiKeyCredentials)
        assert retrieved.key == "sk-ant-api03-xxxxx"

    def test_get_nonexistent_provider_returns_none(self):
        """Test that getting non-existent provider returns None."""
        result = self.store.get("nonexistent")
        assert result is None

    def test_remove_credentials(self):
        """Test removing credentials for a provider."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        self.store.set("anthropic", creds)
        assert self.store.get("anthropic") is not None
        
        self.store.remove("anthropic")
        assert self.store.get("anthropic") is None

    def test_remove_nonexistent_provider_no_error(self):
        """Test that removing non-existent provider doesn't raise error."""
        # Should not raise
        self.store.remove("nonexistent")

    def test_list_providers(self):
        """Test listing all stored providers."""
        creds1 = ApiKeyCredentials(provider="anthropic", key="key1")
        creds2 = ApiKeyCredentials(provider="openai", key="key2")
        
        self.store.set("anthropic", creds1)
        self.store.set("openai", creds2)
        
        providers = self.store.list_providers()
        
        assert set(providers) == {"anthropic", "openai"}

    def test_list_providers_empty_store(self):
        """Test listing providers when store is empty."""
        providers = self.store.list_providers()
        assert providers == []

    def test_file_permissions_are_0600(self):
        """Test that auth file is created with 0600 permissions."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        self.store.set("anthropic", creds)
        
        # Check file permissions
        file_stat = os.stat(self.auth_file)
        permissions = stat.S_IMODE(file_stat.st_mode)
        
        assert permissions == 0o600, f"Expected 0600, got {oct(permissions)}"

    def test_file_permissions_preserved_on_update(self):
        """Test that file permissions remain 0600 after updates."""
        creds1 = ApiKeyCredentials(provider="anthropic", key="key1")
        creds2 = ApiKeyCredentials(provider="openai", key="key2")
        
        self.store.set("anthropic", creds1)
        self.store.set("openai", creds2)
        
        file_stat = os.stat(self.auth_file)
        permissions = stat.S_IMODE(file_stat.st_mode)
        
        assert permissions == 0o600

    def test_creates_parent_directory_if_missing(self):
        """Test that parent directory is created if it doesn't exist."""
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "auth.json")
        store = CredentialStore(path=nested_path)
        
        creds = ApiKeyCredentials(provider="anthropic", key="key1")
        store.set("anthropic", creds)
        
        assert os.path.exists(nested_path)

    def test_json_serialization_format(self):
        """Test that credentials are stored as valid JSON."""
        creds = ApiKeyCredentials(
            provider="anthropic",
            key="sk-ant-api03-xxxxx",
        )
        
        self.store.set("anthropic", creds)
        
        with open(self.auth_file, 'r') as f:
            data = json.load(f)
        
        assert "anthropic" in data
        assert data["anthropic"]["type"] == "api_key"
        assert data["anthropic"]["key"] == "sk-ant-api03-xxxxx"

    def test_handles_corrupted_json_file(self):
        """Test graceful handling of corrupted JSON file."""
        # Write invalid JSON
        with open(self.auth_file, 'w') as f:
            f.write("not valid json {{{")
        
        with pytest.raises(CredentialError, match="[Cc]orrupt|[Ii]nvalid"):
            self.store.get("anthropic")

    def test_handles_wrong_type_in_json(self):
        """Test handling of unexpected types in JSON file."""
        # Write valid JSON but wrong structure
        with open(self.auth_file, 'w') as f:
            json.dump(["not", "a", "dict"], f)
        
        with pytest.raises(CredentialError, match="[Ii]nvalid.*format|[Uu]nexpected"):
            self.store.get("anthropic")

    def test_multiple_providers_stored_separately(self):
        """Test that multiple providers are stored independently."""
        creds_anthropic = ApiKeyCredentials(provider="anthropic", key="key_anthropic")
        creds_openai = OAuthCredentials(
            provider="openai",
            access_token="token_openai",
            refresh_token="refresh_openai",
            expires_at=time.time() + 3600,
        )
        
        self.store.set("anthropic", creds_anthropic)
        self.store.set("openai", creds_openai)
        
        retrieved_anthropic = self.store.get("anthropic")
        retrieved_openai = self.store.get("openai")
        
        assert isinstance(retrieved_anthropic, ApiKeyCredentials)
        assert isinstance(retrieved_openai, OAuthCredentials)
        assert retrieved_anthropic.key == "key_anthropic"
        assert retrieved_openai.access_token == "token_openai"


class TestCredentialError(unittest.TestCase):
    """Test suite for CredentialError exception."""

    def test_credential_error_is_exception(self):
        """Test that CredentialError is a proper exception."""
        error = CredentialError("test message")
        assert isinstance(error, Exception)

    def test_credential_error_message(self):
        """Test that CredentialError preserves message."""
        error = CredentialError("specific error message")
        assert str(error) == "specific error message"


if __name__ == "__main__":
    unittest.main()
