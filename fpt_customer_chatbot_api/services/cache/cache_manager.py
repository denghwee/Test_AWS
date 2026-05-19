"""
Cache Manager

Manages cache lifecycle including TTL-based invalidation
and manual cache operations.
"""

import time
from typing import Optional
from cache.faiss_cache import (
    _get_cache_store,
    clear_cache,
    CACHE_TTL_SECONDS,
    cache_stats,
    lookup_cache,
    cache_response,
)


class CacheManager:
    """
    High-level cache management interface.
    Provides TTL invalidation, manual clear, and stats reporting.
    """

    @staticmethod
    def check_and_return(query: str) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Check cache for a similar query. Returns (hit, response, similarity).
        This is the main entry point for cache lookup in the orchestrator.
        """
        return lookup_cache(query)

    @staticmethod
    def store(query: str, response: str, query_type: str = "general", source_agent: str = "unknown"):
        """Store a response in cache after a tool execution."""
        cache_response(query, response, query_type, source_agent)

    @staticmethod
    def clear() -> str:
        """Manually clear all cached responses."""
        return clear_cache()

    @staticmethod
    def get_stats() -> dict:
        """Get cache statistics."""
        return cache_stats.get_stats()

    @staticmethod
    def get_stats_report() -> str:
        """Get a formatted cache statistics report."""
        return cache_stats.get_report()

    @staticmethod
    def get_ttl_hours() -> float:
        """Get the current TTL setting in hours."""
        return CACHE_TTL_SECONDS / 3600
