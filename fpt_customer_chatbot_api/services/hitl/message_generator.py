"""
HITL Message Generator

Extracts pending tool call information from graph state and
formats it into human-readable confirmation messages.
"""

from typing import Optional


def generate_confirmation_message(pending_tool_calls: list[dict]) -> str:
    """
    Generate a human-readable confirmation message from pending tool calls.

    Args:
        pending_tool_calls: List of tool call dicts with 'name' and 'args'.

    Returns:
        Formatted confirmation message string.
    """
    if not pending_tool_calls:
        return "No pending actions to confirm."

    lines = []
    lines.append("=" * 50)
    lines.append("⚠️  CONFIRMATION REQUIRED")
    lines.append("=" * 50)
    lines.append("")

    for i, tc in enumerate(pending_tool_calls, 1):
        tool_name = tc.get("name", "Unknown Tool")
        args = tc.get("args", {})

        # Human-readable tool name
        readable_name = _get_readable_tool_name(tool_name)
        lines.append(f"Action {i}: {readable_name}")
        lines.append("-" * 30)

        # Format arguments
        for key, value in args.items():
            display_key = key.replace("_", " ").title()
            lines.append(f"  • {display_key}: {value}")

        lines.append("")

    lines.append("─" * 50)
    lines.append("Type 'y' or 'yes' to APPROVE")
    lines.append("Type anything else to CANCEL")
    lines.append("─" * 50)

    return "\n".join(lines)


def _get_readable_tool_name(tool_name: str) -> str:
    """Convert function name to human-readable label."""
    mapping = {
        "create_ticket": "📝 Create Support Ticket",
        "update_ticket": "✏️ Update Ticket",
        "cancel_ticket": "🗑️ Cancel Ticket",
        "book_room": "📅 Book Room/Meeting",
        "update_booking": "✏️ Update Booking",
        "cancel_booking": "🗑️ Cancel Booking",
    }
    return mapping.get(tool_name, f"🔧 {tool_name}")


def extract_pending_tool_calls(graph_state) -> list[dict]:
    """
    Extract pending tool calls from graph state snapshot.

    Args:
        graph_state: The state snapshot from graph.get_state(config)

    Returns:
        List of tool call dicts with 'name', 'args', 'id'.
    """
    if not graph_state or not graph_state.values:
        return []

    messages = graph_state.values.get("messages", [])
    if not messages:
        return []

    last_message = messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return []

    return last_message.tool_calls
