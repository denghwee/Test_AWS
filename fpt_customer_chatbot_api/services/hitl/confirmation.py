"""
HITL Confirmation Flow

Handles the confirmation workflow when the graph is interrupted
before a sensitive tool execution.
"""

from langchain_core.messages import ToolMessage
from hitl.interrupt_config import SENSITIVE_TOOL_FUNCTIONS, NON_SENSITIVE_TOOL_FUNCTIONS
from hitl.message_generator import generate_confirmation_message, extract_pending_tool_calls
from ai_utils.logging import get_logger

logger = get_logger(__name__)


def is_sensitive_tool_call(tool_calls: list[dict]) -> bool:
    """
    Check if any of the pending tool calls are sensitive (write operations).
    Returns False if all calls are read-only (track/search).
    """
    for tc in tool_calls:
        if tc.get("name") in SENSITIVE_TOOL_FUNCTIONS:
            return True
    return False


def handle_confirmation(graph, config: dict) -> tuple[bool, str]:
    """
    Check if the graph is in an interrupted state and handle HITL confirmation.

    Args:
        graph: The compiled StateGraph.
        config: The thread config dict.

    Returns:
        Tuple of (needs_confirmation: bool, confirmation_message: str).
        If needs_confirmation is True, the caller should prompt the user.
    """
    state = graph.get_state(config)

    # Check if graph is interrupted (has next steps pending)
    if not state.next:
        return False, ""

    # Extract pending tool calls
    tool_calls = extract_pending_tool_calls(state)
    if not tool_calls:
        return False, ""

    # Check if any are sensitive
    if not is_sensitive_tool_call(tool_calls):
        # Non-sensitive: auto-approve by resuming
        return False, ""

    # Generate confirmation message
    message = generate_confirmation_message(tool_calls)
    logger.info(f"HITL confirmation requested for tools: {[tc['name'] for tc in tool_calls]}")

    return True, message


def process_user_response(graph, config: dict, user_response: str) -> dict:
    """
    Process the user's confirmation response.

    Args:
        graph: The compiled StateGraph.
        config: The thread config dict.
        user_response: User's input ("y"/"yes" to approve, anything else to cancel).

    Returns:
        The result events from graph execution.
    """
    approved = user_response.strip().lower() in ("y", "yes")

    if approved:
        logger.info("HITL: User APPROVED the action.")
        # Resume execution — invoke with None to continue from interrupted state
        result = graph.invoke(None, config)
        return result
    else:
        logger.info(f"HITL: User REJECTED the action. Response: '{user_response}'")
        # Cancel: inject a ToolMessage indicating cancellation
        state = graph.get_state(config)
        tool_calls = extract_pending_tool_calls(state)

        cancel_messages = []
        for tc in tool_calls:
            cancel_messages.append(
                ToolMessage(
                    content=f"❌ Action '{tc['name']}' was CANCELLED by the user. "
                            f"Ask the user how they'd like to proceed.",
                    tool_call_id=tc["id"],
                )
            )

        # Update state with cancellation messages
        graph.update_state(config, {"messages": cancel_messages})

        # Resume with the cancellation
        result = graph.invoke(None, config)
        return result
