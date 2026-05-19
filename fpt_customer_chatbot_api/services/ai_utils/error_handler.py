from langchain_core.messages import ToolMessage, AIMessage
from ai_utils.logging import get_logger

logger = get_logger(__name__)


class ChatbotError(Exception):
    """Base exception for the chatbot system."""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(message)
        self.user_message = user_message or "An unexpected error occurred. Please try again."


class ToolExecutionError(ChatbotError):
    """Raised when a tool fails to execute."""
    pass


class AgentRoutingError(ChatbotError):
    """Raised when agent routing fails."""
    pass


def handle_graph_error(error: Exception, context: str = "") -> str:
    """
    Handle errors during graph execution and return a user-friendly message.

    Args:
        error: The exception that was raised.
        context: Additional context about where the error occurred.

    Returns:
        User-friendly error message string.
    """
    error_type = type(error).__name__
    logger.error(f"Graph error [{context}]: {error_type}: {error}")

    # Map known error types to user-friendly messages
    error_messages = {
        "AuthenticationError": "⚠️ There's an issue with the AI service authentication. Please check your API keys.",
        "RateLimitError": "⚠️ We're experiencing high demand. Please try again in a moment.",
        "APIConnectionError": "⚠️ Unable to connect to the AI service. Please check your internet connection.",
        "TimeoutError": "⚠️ The request timed out. Please try again.",
        "InvalidRequestError": "⚠️ There was an issue with the request. Please try rephrasing your question.",
    }

    for err_type, message in error_messages.items():
        if err_type in error_type:
            return message

    return f"⚠️ An unexpected error occurred. Please try again.\nDetails: {error_type}"


def safe_invoke(graph, input_data: dict, config: dict) -> dict:
    """
    Safely invoke the graph with error handling.

    Args:
        graph: The compiled StateGraph.
        input_data: Input data for the graph.
        config: Thread configuration.

    Returns:
        Graph result dict, or error state dict.
    """
    try:
        return graph.invoke(input_data, config)
    except Exception as e:
        error_msg = handle_graph_error(e, context="safe_invoke")
        logger.error(f"Safe invoke failed: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=error_msg)],
            "error": str(e),
        }
