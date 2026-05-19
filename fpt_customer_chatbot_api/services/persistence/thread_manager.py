"""
Thread Manager

Utilities for managing conversation threads:
- List active threads
- View checkpoint history
- Delete old threads (cleanup)
"""

import os
import sqlite3
from typing import Optional
from datetime import datetime

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "checkpoints.db"
)


def list_active_threads() -> list[dict]:
    """
    List all active conversation threads in the checkpoint database.

    Returns:
        List of dicts with thread_id and last_updated info.
    """
    if not os.path.exists(DB_PATH):
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query unique thread IDs from checkpoints
        cursor.execute("""
            SELECT DISTINCT thread_id
            FROM checkpoints
            ORDER BY thread_id
        """)

        threads = []
        for row in cursor.fetchall():
            threads.append({
                "thread_id": row[0],
            })

        conn.close()
        return threads
    except Exception as e:
        return [{"error": str(e)}]


def get_thread_history(thread_id: str, limit: int = 10) -> list[dict]:
    """
    View checkpoint history for a specific thread.

    Args:
        thread_id: The thread ID to look up.
        limit: Maximum number of history entries to return.

    Returns:
        List of checkpoint info dicts.
    """
    if not os.path.exists(DB_PATH):
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT thread_id, checkpoint_id, parent_id
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY checkpoint_id DESC
            LIMIT ?
        """, (thread_id, limit))

        history = []
        for row in cursor.fetchall():
            history.append({
                "thread_id": row[0],
                "checkpoint_id": row[1],
                "parent_id": row[2],
            })

        conn.close()
        return history
    except Exception as e:
        return [{"error": str(e)}]


def delete_thread(thread_id: str) -> str:
    """
    Delete all checkpoints for a specific thread.

    Args:
        thread_id: The thread ID to delete.

    Returns:
        Status message.
    """
    if not os.path.exists(DB_PATH):
        return f"❌ No checkpoint database found."

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        deleted = cursor.rowcount

        # Also clean up writes table if it exists
        try:
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        except sqlite3.OperationalError:
            pass  # Table may not exist

        conn.commit()
        conn.close()

        return f"✅ Deleted {deleted} checkpoints for thread '{thread_id}'."
    except Exception as e:
        return f"❌ Error deleting thread: {e}"


def cleanup_old_threads(max_age_hours: int = 72) -> str:
    """
    Delete threads older than the specified age.

    Args:
        max_age_hours: Maximum age in hours before cleanup.

    Returns:
        Status message with cleanup results.
    """
    threads = list_active_threads()
    if not threads:
        return "No threads to clean up."

    # For SQLite checkpoints, we'd need timestamp metadata
    # This is a simplified version that just reports thread count
    return f"Found {len(threads)} active threads. Manual cleanup available via delete_thread()."


def format_thread_list(threads: list[dict]) -> str:
    """Format thread list for display."""
    if not threads:
        return "No active threads found."

    lines = ["📋 Active Threads:", "─" * 40]
    for i, t in enumerate(threads, 1):
        tid = t.get("thread_id", "Unknown")
        lines.append(f"  {i}. Thread ID: {tid}")
    lines.append("─" * 40)
    lines.append(f"Total: {len(threads)} threads")
    return "\n".join(lines)
