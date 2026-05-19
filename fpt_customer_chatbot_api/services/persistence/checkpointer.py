"""
Checkpointer Configuration

Configures persistent state storage using SqliteSaver for
conversation resumption across process restarts.
"""

import os
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver


# Database path for SQLite persistence
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "checkpoints.db"
)


def get_memory_checkpointer():
    """
    Get an in-memory checkpointer for development/testing.
    Data is lost when the process stops.

    Returns:
        MemorySaver instance.
    """
    return MemorySaver()


def get_sqlite_checkpointer():
    """
    Get a SQLite-based checkpointer for persistent state.
    Conversations survive process restarts.

    The database is stored at: ./checkpoints.db

    Returns:
        SqliteSaver context manager (use with `with` statement).

    Migration to PostgresSaver:
        For production deployment, replace SqliteSaver with PostgresSaver:

        ```python
        from langgraph.checkpoint.postgres import PostgresSaver
        DB_URI = "postgresql://user:pass@localhost:5432/chatbot"
        checkpointer = PostgresSaver.from_conn_string(DB_URI)
        ```

        The API is identical — just swap the import and connection string.
    """
    return SqliteSaver.from_conn_string(DB_PATH)
