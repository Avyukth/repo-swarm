"""
CLI commands for authentication.

Provides commands:
- auth login [--method oauth|api] [--key KEY]
- auth logout
- auth list
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

from .manager import AuthManager, AuthError
from .oauth import OAuthError

# Console for output
console = Console()
error_console = Console(stderr=True)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for auth CLI."""
    parser = argparse.ArgumentParser(
        prog="auth",
        description="Manage authentication credentials for repo-swarm",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login with OAuth or API key")
    login_parser.add_argument(
        "--method",
        choices=["oauth", "api"],
        default="oauth",
        help="Authentication method (default: oauth)",
    )
    login_parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="API key (required for --method api)",
    )
    login_parser.add_argument(
        "--provider",
        type=str,
        default="anthropic",
        help="Provider name (default: anthropic)",
    )
    
    # Logout command
    logout_parser = subparsers.add_parser("logout", help="Remove stored credentials")
    logout_parser.add_argument(
        "--provider",
        type=str,
        default="anthropic",
        help="Provider name (default: anthropic)",
    )
    
    # List command
    subparsers.add_parser("list", help="List stored credentials")
    
    return parser


def run_login(
    method: str = "oauth",
    key: Optional[str] = None,
    provider: str = "anthropic",
) -> int:
    """
    Run login command.
    
    Args:
        method: Authentication method ("oauth" or "api")
        key: API key (required for "api" method)
        provider: Provider name
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    manager = AuthManager()
    
    if method == "api":
        if key is None:
            error_console.print("[red]Error:[/red] --key is required for API key login")
            return 1
        
        try:
            manager.login_with_api_key(provider, key)
            console.print(f"[green]Success:[/green] Logged in to {provider} with API key")
            return 0
        except Exception as e:
            error_console.print(f"[red]Error:[/red] Failed to store credentials: {e}")
            return 1
    
    # OAuth flow
    try:
        console.print(f"Starting OAuth login for {provider}...")
        console.print("A browser window will open for authentication.")
        manager.login_with_oauth(provider)
        console.print(f"[green]Success:[/green] Logged in to {provider} with OAuth")
        return 0
    except OAuthError as e:
        error_console.print(f"[red]Error:[/red] OAuth failed: {e}")
        return 1
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Login failed: {e}")
        return 1


def run_logout(provider: str = "anthropic") -> int:
    """
    Run logout command.
    
    Args:
        provider: Provider name
        
    Returns:
        Exit code (0 for success)
    """
    manager = AuthManager()
    
    existed = manager.logout(provider)
    
    if existed:
        console.print(f"[green]Success:[/green] Logged out from {provider}")
    else:
        console.print(f"[yellow]Note:[/yellow] No credentials found for {provider}")
    
    return 0


def run_list() -> int:
    """
    Run list command.
    
    Returns:
        Exit code (0 for success)
    """
    manager = AuthManager()
    credentials = manager.list_credentials()
    
    if not credentials:
        console.print("[yellow]No stored credentials found.[/yellow]")
        console.print("\nUse [bold]auth login[/bold] to add credentials.")
        return 0
    
    # Create table
    table = Table(title="Stored Credentials")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Details", style="green")
    
    for cred in credentials:
        provider = cred.get("provider", "unknown")
        cred_type = cred.get("type", "unknown")
        
        # Build details string
        details = []
        if cred_type == "api_key":
            key = cred.get("key", "***")
            details.append(f"Key: {key}")
        elif cred_type == "oauth":
            if "expires" in cred:
                details.append(f"Expires: {cred['expires']}")
            if cred.get("has_refresh_token"):
                details.append("Has refresh token")
        
        table.add_row(provider, cred_type, ", ".join(details) if details else "-")
    
    console.print(table)
    return 0


def main() -> int:
    """
    Main entry point for auth CLI.
    
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "login":
        return run_login(
            method=args.method,
            key=args.key,
            provider=args.provider,
        )
    
    if args.command == "logout":
        return run_logout(provider=args.provider)
    
    if args.command == "list":
        return run_list()
    
    # Unknown command
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
