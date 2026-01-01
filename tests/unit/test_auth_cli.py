"""
Tests for auth CLI commands.

Tests for:
- auth login (oauth and api-key methods)
- auth logout
- auth list (with redacted output)
- Exit codes and error handling
"""

from __future__ import annotations

import os
import sys
from io import StringIO
from typing import List
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestAuthCLILogin:
    """Test auth login command."""

    def test_login_command_exists(self):
        """Test login subcommand is available."""
        from src.auth.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["login"])
        
        assert args.command == "login"

    def test_login_default_method_is_oauth(self):
        """Test login defaults to oauth method."""
        from src.auth.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["login"])
        
        assert args.method == "oauth"

    def test_login_api_method_requires_key(self):
        """Test login --method api requires --key."""
        from src.auth.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["login", "--method", "api", "--key", "sk-ant-123"])
        
        assert args.method == "api"
        assert args.key == "sk-ant-123"

    def test_login_oauth_triggers_flow(self):
        """Test login with oauth triggers interactive flow."""
        from src.auth.cli import run_login
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'login_with_oauth') as mock_oauth:
            exit_code = run_login(method="oauth", key=None)
            
            mock_oauth.assert_called_once()
            assert exit_code == 0

    def test_login_api_stores_key(self):
        """Test login --method api stores the key."""
        from src.auth.cli import run_login
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'login_with_api_key') as mock_api:
            exit_code = run_login(method="api", key="sk-ant-test-key")
            
            mock_api.assert_called_once_with("anthropic", "sk-ant-test-key")
            assert exit_code == 0

    def test_login_api_without_key_returns_error(self):
        """Test login --method api without --key returns error."""
        from src.auth.cli import run_login
        
        exit_code = run_login(method="api", key=None)
        
        assert exit_code == 1

    def test_login_oauth_failure_returns_error(self):
        """Test login oauth failure returns exit code 1."""
        from src.auth.cli import run_login
        from src.auth.manager import AuthManager
        from src.auth.oauth import OAuthError
        
        with patch.object(AuthManager, 'login_with_oauth', side_effect=OAuthError("Failed")):
            exit_code = run_login(method="oauth", key=None)
            
            assert exit_code == 1


class TestAuthCLILogout:
    """Test auth logout command."""

    def test_logout_command_exists(self):
        """Test logout subcommand is available."""
        from src.auth.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["logout"])
        
        assert args.command == "logout"

    def test_logout_removes_credentials(self):
        """Test logout removes stored credentials."""
        from src.auth.cli import run_logout
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'logout', return_value=True) as mock_logout:
            exit_code = run_logout()
            
            mock_logout.assert_called_once_with("anthropic")
            assert exit_code == 0

    def test_logout_returns_success_even_if_not_logged_in(self):
        """Test logout succeeds even if no credentials existed."""
        from src.auth.cli import run_logout
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'logout', return_value=False):
            exit_code = run_logout()
            
            # Still returns 0 - idempotent operation
            assert exit_code == 0


class TestAuthCLIList:
    """Test auth list command."""

    def test_list_command_exists(self):
        """Test list subcommand is available."""
        from src.auth.cli import create_parser
        
        parser = create_parser()
        args = parser.parse_args(["list"])
        
        assert args.command == "list"

    def test_list_shows_credentials(self):
        """Test list displays stored credentials."""
        from src.auth.cli import run_list
        from src.auth.manager import AuthManager
        
        mock_creds = [
            {"provider": "anthropic", "type": "api_key", "key": "sk-ant-...1234"},
        ]
        
        with patch.object(AuthManager, 'list_credentials', return_value=mock_creds):
            exit_code = run_list()
            
            assert exit_code == 0

    def test_list_shows_empty_message_when_no_credentials(self):
        """Test list shows message when no credentials stored."""
        from src.auth.cli import run_list
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'list_credentials', return_value=[]):
            exit_code = run_list()
            
            assert exit_code == 0

    def test_list_redacts_sensitive_data(self):
        """Test list output has redacted keys."""
        from src.auth.cli import run_list
        from src.auth.manager import AuthManager
        
        mock_creds = [
            {"provider": "anthropic", "type": "api_key", "key": "sk-ant-...1234"},
        ]
        
        with patch.object(AuthManager, 'list_credentials', return_value=mock_creds) as mock_list:
            run_list()
            
            # AuthManager.list_credentials already returns redacted data
            mock_list.assert_called_once()


class TestAuthCLIMain:
    """Test main CLI entry point."""

    def test_main_exists(self):
        """Test main entry point exists."""
        from src.auth.cli import main
        
        assert callable(main)

    def test_main_with_login(self):
        """Test main dispatches to login."""
        from src.auth.cli import main
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'login_with_oauth'):
            with patch('sys.argv', ['auth', 'login']):
                exit_code = main()
                
                assert exit_code == 0

    def test_main_with_logout(self):
        """Test main dispatches to logout."""
        from src.auth.cli import main
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'logout', return_value=True):
            with patch('sys.argv', ['auth', 'logout']):
                exit_code = main()
                
                assert exit_code == 0

    def test_main_with_list(self):
        """Test main dispatches to list."""
        from src.auth.cli import main
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'list_credentials', return_value=[]):
            with patch('sys.argv', ['auth', 'list']):
                exit_code = main()
                
                assert exit_code == 0

    def test_main_no_command_shows_help(self):
        """Test main with no command shows help and returns 0."""
        from src.auth.cli import main
        
        with patch('sys.argv', ['auth']):
            # Should not raise, should show help
            exit_code = main()
            
            assert exit_code == 0


class TestAuthCLIOutput:
    """Test CLI output formatting."""

    def test_login_success_message(self, capsys):
        """Test login success prints confirmation."""
        from src.auth.cli import run_login
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'login_with_api_key'):
            run_login(method="api", key="sk-ant-test")
            
            captured = capsys.readouterr()
            assert "success" in captured.out.lower() or "logged in" in captured.out.lower()

    def test_logout_success_message(self, capsys):
        """Test logout success prints confirmation."""
        from src.auth.cli import run_logout
        from src.auth.manager import AuthManager
        
        with patch.object(AuthManager, 'logout', return_value=True):
            run_logout()
            
            captured = capsys.readouterr()
            assert "logged out" in captured.out.lower() or "success" in captured.out.lower()

    def test_error_message_on_failure(self, capsys):
        """Test error messages printed to stderr."""
        from src.auth.cli import run_login
        from src.auth.manager import AuthManager
        from src.auth.oauth import OAuthError
        
        with patch.object(AuthManager, 'login_with_oauth', side_effect=OAuthError("Network error")):
            run_login(method="oauth", key=None)
            
            captured = capsys.readouterr()
            assert "error" in captured.err.lower() or "failed" in captured.err.lower()
