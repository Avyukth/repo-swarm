"""
Base classes for search providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


class SearchError(Exception):
    """Base exception for search provider errors."""

    pass


class SearchAuthenticationError(SearchError):
    """Raised when authentication fails."""

    pass


class SearchRateLimitError(SearchError):
    """Raised when rate limited."""

    pass


@dataclass(frozen=True, slots=True)
class SearchResult:
    """
    A single search result.

    Attributes:
        title: The title of the result
        url: The URL of the result
        snippet: A short snippet/summary of the content
        content: Full content if fetched (optional)
        score: Relevance score (optional)
        published_date: Publication date if available (optional)
    """

    title: str
    url: str
    snippet: str = ""
    content: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[str] = None


class SearchProvider(ABC):
    """
    Abstract base class for search providers.

    All search provider implementations must inherit from this class
    and implement the required methods.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the search provider name (e.g., 'exa', 'serper')."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """
        Search for a query and return results.

        Args:
            query: The search query
            num_results: Maximum number of results to return
            **kwargs: Provider-specific options

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If the search fails
        """
        ...

    def search_and_contents(
        self,
        query: str,
        *,
        num_results: int = 5,
        **kwargs,
    ) -> List[SearchResult]:
        """
        Search and retrieve full content for results.

        Default implementation just calls search().
        Override in subclasses that support content retrieval.

        Args:
            query: The search query
            num_results: Maximum number of results to return
            **kwargs: Provider-specific options

        Returns:
            List of SearchResult objects with content populated
        """
        return self.search(query, num_results=num_results, **kwargs)

    def format_results_as_context(
        self,
        results: List[SearchResult],
        *,
        include_content: bool = False,
        max_content_length: int = 500,
    ) -> str:
        """
        Format search results as context for an LLM prompt.

        Args:
            results: List of search results
            include_content: Whether to include full content
            max_content_length: Maximum characters of content per result

        Returns:
            Formatted string suitable for injection into a prompt
        """
        lines = ["## Web Search Results\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"### {i}. {result.title}")
            lines.append(f"URL: {result.url}")

            if result.snippet:
                lines.append(f"Summary: {result.snippet}")

            if include_content and result.content:
                content = result.content[:max_content_length]
                if len(result.content) > max_content_length:
                    content += "..."
                lines.append(f"Content: {content}")

            lines.append("")

        return "\n".join(lines)
