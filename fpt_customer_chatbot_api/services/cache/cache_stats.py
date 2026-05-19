"""
Cache Statistics Tracking

Tracks cache hits, misses, stores, and computes hit rate.
"""

import time
from typing import Optional


class CacheStats:
    """Thread-safe cache statistics tracker."""

    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.stores: int = 0
        self.start_time: float = time.time()
        self._history: list[dict] = []

    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
        self._history.append({"type": "hit", "time": time.time()})

    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
        self._history.append({"type": "miss", "time": time.time()})

    def record_store(self):
        """Record a cache store operation."""
        self.stores += 1
        self._history.append({"type": "store", "time": time.time()})

    @property
    def total_lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_lookups == 0:
            return 0.0
        return self.hits / self.total_lookups

    def get_stats(self) -> dict:
        """Get stats as a dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "stores": self.stores,
            "total_lookups": self.total_lookups,
            "hit_rate": round(self.hit_rate, 4),
            "uptime_seconds": round(time.time() - self.start_time, 1),
        }

    def get_report(self) -> str:
        """Get a formatted report string."""
        stats = self.get_stats()
        return (
            f"📊 Cache Statistics Report\n"
            f"{'─' * 30}\n"
            f"  Hits:          {stats['hits']}\n"
            f"  Misses:        {stats['misses']}\n"
            f"  Total Lookups: {stats['total_lookups']}\n"
            f"  Hit Rate:      {stats['hit_rate']:.1%}\n"
            f"  Stores:        {stats['stores']}\n"
            f"  Uptime:        {stats['uptime_seconds']:.0f}s\n"
            f"{'─' * 30}"
        )

    def reset(self):
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.stores = 0
        self.start_time = time.time()
        self._history.clear()
