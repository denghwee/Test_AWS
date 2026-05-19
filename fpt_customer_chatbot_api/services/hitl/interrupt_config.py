"""
HITL Interrupt Configuration

Defines which tools are considered "sensitive" and require
human confirmation before execution.
"""

# Sensitive tool names that require HITL confirmation.
# These are the tool NODE names in the graph that should be interrupted.
# Read operations (track_ticket, track_booking) and search operations are excluded.
SENSITIVE_TOOL_NAMES = [
    "ticket_tools",
    "booking_tools",
]

# Individual sensitive tool function names (used by confirmation.py to filter)
SENSITIVE_TOOL_FUNCTIONS = [
    "create_support_ticket",
    "update_support_ticket",
    "cancel_support_ticket",
    "create_room_booking",
    "update_room_booking",
    "cancel_room_booking",
]

# Non-sensitive tool function names (read-only, no confirmation needed)
NON_SENSITIVE_TOOL_FUNCTIONS = [
    "get_ticket_status",
    "list_user_bookings",
    "search_technical_issue",
    "fpt_policy_search",
]
