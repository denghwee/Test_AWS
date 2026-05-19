"""
FAISS Response Cache

Stores and retrieves cached responses using FAISS vectorstore
with sentence-transformers embeddings for semantic similarity matching.
"""

import os
import time
import json
from typing import Optional, Tuple
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from cache.cache_stats import CacheStats

# Singleton cache instance
_cache_store: Optional[FAISS] = None
_cache_metadata: dict[str, dict] = {}  # query_hash -> {response, timestamp, query_type, source_agent}
_embeddings = None

# Configuration
SIMILARITY_THRESHOLD = 0.85
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# Stats tracker
cache_stats = CacheStats()


def _get_embeddings():
    """Lazy-load sentence-transformers embeddings."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


def _get_cache_store() -> Optional[FAISS]:
    """Get or initialize the FAISS cache store."""
    global _cache_store
    return _cache_store


def cache_response(
    query: str,
    response: str,
    query_type: str = "general",
    source_agent: str = "unknown"
) -> None:
    """
    Store a response in the FAISS cache.

    Args:
        query: The original user query.
        response: The response to cache.
        query_type: Type of query (e.g., "faq", "it_support").
        source_agent: Which agent generated the response.
    """
    global _cache_store

    embeddings = _get_embeddings()
    metadata = {
        "response": response,
        "timestamp": time.time(),
        "query_type": query_type,
        "source_agent": source_agent,
        "original_query": query,
    }

    if _cache_store is None:
        # Create new FAISS store with the first entry
        _cache_store = FAISS.from_texts(
            texts=[query],
            embedding=embeddings,
            metadatas=[metadata]
        )
    else:
        # Add to existing store
        _cache_store.add_texts(
            texts=[query],
            metadatas=[metadata]
        )

    cache_stats.record_store()
    print(f"  [System] 💾 Response cached. Total size: {len(_cache_store.docstore._dict)} entries.")


def lookup_cache(query: str) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Look up a cached response by semantic similarity.

    Args:
        query: The query to search for.

    Returns:
        Tuple of (cache_hit: bool, cached_response: Optional[str], similarity: Optional[float]).
    """
    store = _get_cache_store()
    if store is None:
        cache_stats.record_miss()
        return False, None, None

    try:
        results = store.similarity_search_with_score(query, k=1)
    except Exception:
        cache_stats.record_miss()
        return False, None, None

    if not results:
        cache_stats.record_miss()
        return False, None, None

    doc, score = results[0]
    # FAISS returns L2 distance — lower is more similar
    # Convert to similarity: sim = 1 / (1 + distance)
    similarity = 1 / (1 + score)

    metadata = doc.metadata

    # Check TTL
    cached_time = metadata.get("timestamp", 0)
    if (time.time() - cached_time) > CACHE_TTL_SECONDS:
        cache_stats.record_miss()
        return False, None, None

    # Check similarity threshold
    if similarity >= SIMILARITY_THRESHOLD:
        cache_stats.record_hit()
        cached_response = metadata.get("response", "")
        source = metadata.get("source_agent", "cache")
        return True, f"📦 [Cached Response from {source}]\n{cached_response}", similarity

    cache_stats.record_miss()
    return False, None, None


def clear_cache() -> str:
    """Clear the entire cache."""
    global _cache_store, _cache_metadata
    _cache_store = None
    _cache_metadata = {}
    cache_stats.reset()
    return "✅ Cache cleared successfully."
