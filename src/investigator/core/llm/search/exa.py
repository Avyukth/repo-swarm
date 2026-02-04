"""
Exa search provider implementation.

Provides integration with the Exa API for web search functionality.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from exa_py import Exa

from .base import (
    SearchProvider,
    SearchResult,
    SearchError,
    SearchAuthenticationError,
    SearchRateLimitError,
)


class ExaSearch(SearchProvider):
    """
    Exa search provider.

    Provides web search functionality using the Exa API.
    Can be used with any LLM provider to augment responses with
    up-to-date web information.

    Usage:
        exa = ExaSearch()  # Uses EXA_API_KEY env var
        results = exa.search("Python best practices 2024")

        # With content retrieval
        results = exa.search_and_contents("async patterns", num_results=5)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Exa search provider.

        Args:
            api_key: Exa API key. If None, uses EXA_API_KEY env var.
            logger: Optional logger instance.
        """
        self._api_key = api_key or os.getenv("EXA_API_KEY")
        self._logger = logger or logging.getLogger(__name__)

        if not self._api_key:
            raise SearchError(
                "No Exa API key found. Set EXA_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self._client = Exa(api_key=self._api_key)
        self._logger.debug("Initialized Exa search client")

    @property
    def provider_name(self) -> str:
        return "exa"

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        use_autoprompt: bool = True,
        type: str = "auto",
        **kwargs,
    ) -> List[SearchResult]:
        """
        Search for a query and return results.

        Args:
            query: The search query
            num_results: Maximum number of results to return
            use_autoprompt: Let Exa optimize the query
            type: Search type ('auto', 'neural', 'keyword')
            **kwargs: Additional Exa-specific options

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If the search fails
            SearchAuthenticationError: If authentication fails
            SearchRateLimitError: If rate limited
        """
        self._logger.debug(f"Searching Exa: query='{query}', num_results={num_results}")

        try:
            response = self._client.search(
                query,
                num_results=num_results,
                use_autoprompt=use_autoprompt,
                type=type,
                **kwargs,
            )

            results = []
            for item in response.results:
                results.append(
                    SearchResult(
                        title=item.title or "Untitled",
                        url=item.url,
                        snippet=getattr(item, "text", "") or "",
                        score=getattr(item, "score", None),
                        published_date=getattr(item, "published_date", None),
                    )
                )

            self._logger.debug(f"Exa search returned {len(results)} results")
            return results

        except Exception as e:
            self._handle_error(e)

    def search_and_contents(
        self,
        query: str,
        *,
        num_results: int = 5,
        use_autoprompt: bool = True,
        type: str = "auto",
        text_length_limit: int = 1000,
        highlights: bool = True,
        **kwargs,
    ) -> List[SearchResult]:
        """
        Search and retrieve full content for results.

        Args:
            query: The search query
            num_results: Maximum number of results to return
            use_autoprompt: Let Exa optimize the query
            type: Search type ('auto', 'neural', 'keyword')
            text_length_limit: Maximum characters of content per result
            highlights: Whether to include highlighted snippets
            **kwargs: Additional Exa-specific options

        Returns:
            List of SearchResult objects with content populated

        Raises:
            SearchError: If the search fails
        """
        self._logger.debug(
            f"Searching Exa with contents: query='{query}', num_results={num_results}"
        )

        try:
            # Build text options
            text_options = {"max_characters": text_length_limit}

            response = self._client.search_and_contents(
                query,
                num_results=num_results,
                use_autoprompt=use_autoprompt,
                type=type,
                text=text_options,
                highlights=highlights,
                **kwargs,
            )

            results = []
            for item in response.results:
                # Get content from text or highlights
                content = getattr(item, "text", None)

                # Use highlights if available and no full text
                snippet = ""
                if hasattr(item, "highlights") and item.highlights:
                    snippet = " ... ".join(item.highlights[:3])
                elif content:
                    snippet = content[:200] + "..." if len(content) > 200 else content

                results.append(
                    SearchResult(
                        title=item.title or "Untitled",
                        url=item.url,
                        snippet=snippet,
                        content=content,
                        score=getattr(item, "score", None),
                        published_date=getattr(item, "published_date", None),
                    )
                )

            self._logger.debug(
                f"Exa search with contents returned {len(results)} results"
            )
            return results

        except Exception as e:
            self._handle_error(e)

    def find_similar(
        self,
        url: str,
        *,
        num_results: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """
        Find pages similar to a given URL.

        Args:
            url: The URL to find similar pages for
            num_results: Maximum number of results to return
            **kwargs: Additional Exa-specific options

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If the search fails
        """
        self._logger.debug(f"Finding similar to: {url}")

        try:
            response = self._client.find_similar(
                url,
                num_results=num_results,
                **kwargs,
            )

            results = []
            for item in response.results:
                results.append(
                    SearchResult(
                        title=item.title or "Untitled",
                        url=item.url,
                        snippet=getattr(item, "text", "") or "",
                        score=getattr(item, "score", None),
                        published_date=getattr(item, "published_date", None),
                    )
                )

            self._logger.debug(f"Found {len(results)} similar pages")
            return results

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception) -> None:
        """Handle and re-raise errors with appropriate types."""
        error_str = str(e).lower()

        if "rate" in error_str or "429" in error_str or "quota" in error_str:
            self._logger.warning(f"Rate limited by Exa: {e}")
            raise SearchRateLimitError(f"Rate limited by Exa: {e}") from e

        if "auth" in error_str or "401" in error_str or "key" in error_str:
            self._logger.error(f"Authentication failed for Exa: {e}")
            raise SearchAuthenticationError(f"Authentication failed: {e}") from e

        self._logger.error(f"Exa search error: {e}")
        raise SearchError(f"Exa search error: {e}") from e
