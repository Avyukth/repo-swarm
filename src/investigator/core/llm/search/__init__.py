"""
Search providers for web search integration.

Provides web search capabilities that can be used with any LLM provider
to augment responses with up-to-date information from the web.
"""

from .base import SearchProvider, SearchResult
from .exa import ExaSearch

__all__ = [
    "SearchProvider",
    "SearchResult",
    "ExaSearch",
]
