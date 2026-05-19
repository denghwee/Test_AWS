import logging
import sys
from typing import Optional


# Global log level configuration
LOG_LEVEL = logging.INFO

# Format with timestamp and module context
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = LOG_LEVEL):
    """
    Configure the root logger for the application.
    Call this once at startup.
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
    )
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langsmith").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(name)


class ConversationLogger:
    """
    Logger wrapper that includes conversation context in all messages.
    """

    def __init__(self, logger_name: str, conversation_id: str, user_id: str = "unknown"):
        self._logger = get_logger(logger_name)
        self.conversation_id = conversation_id
        self.user_id = user_id

    def _format(self, message: str) -> str:
        return f"[conv:{self.conversation_id[:8]}|user:{self.user_id}] {message}"

    def info(self, message: str):
        self._logger.info(self._format(message))

    def warning(self, message: str):
        self._logger.warning(self._format(message))

    def error(self, message: str):
        self._logger.error(self._format(message))

    def debug(self, message: str):
        self._logger.debug(self._format(message))
