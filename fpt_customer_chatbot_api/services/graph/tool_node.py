"""
Tool Node with Fallback

Wraps LangGraph's ToolNode with error-handling fallback so that
tool errors are returned to the LLM for self-correction instead
of crashing the system.
"""

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode


def _handle_tool_error(state: dict) -> dict:
    """
    Error handler: when a tool raises an exception, this returns
    error messages to the LLM so it can attempt self-correction.
    """
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\nPlease fix your mistakes and try again.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list):
    """
    Creates a ToolNode wrapped with a fallback error handler.

    This ensures that when a tool execution fails (e.g., invalid args),
    the error is caught and returned as a ToolMessage to the LLM,
    allowing it to self-correct rather than crashing the graph.

    Args:
        tools: List of tool objects or Pydantic schemas to bind.

    Returns:
        A ToolNode with error fallback configured.
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(_handle_tool_error)],
        exception_key="error"
    )
