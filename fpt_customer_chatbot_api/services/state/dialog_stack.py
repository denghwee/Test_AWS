"""
Dialog Stack Management

Provides helper functions for managing the agent hierarchy stack.
The dialog_stack is a list[str] acting as a stack where the last
element is the currently active agent.
"""

from typing import Optional, Dict, Any

def pop_dialog_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pop the current agent from the dialog stack.
    Returns a state update dict that the reducer will process.
    """
    return {"dialog_stack": "pop"}

def get_current_agent(state: Dict[str, Any]) -> str:
    """
    Get the name of the currently active agent from the dialog stack.
    Returns 'primary_assistant' if the stack is empty.
    """
    stack = state.get("dialog_stack", [])
    if stack:
        return stack[-1]
    return "primary_assistant"
