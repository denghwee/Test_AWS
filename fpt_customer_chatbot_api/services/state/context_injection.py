"""
Context Injection

Auto-populates user context (user_id, email, special metadata) into the state
so that agents and tools have access to identity and business information.
"""

from typing import Optional, Dict, Any
import uuid

def inject_user_context(
    state: Dict[str, Any],
    user_id: str = "default_user",
    email: Optional[str] = None,
    conversation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Inject user context and business metadata into the state.
    """
    updates = {
        "user_id": user_id,
        "conversation_id": conversation_id or str(uuid.uuid4()),
        "email": email or "",
        "context": metadata or {},
        "dialog_stack": state.get("dialog_stack", ["primary_assistant"])
    }
    
    # Merge existing state with updates
    return {**state, **updates}

def get_context_for_tools(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant context fields to be passed into tool functions.
    """
    return {
        "user_id": state.get("user_id", "unknown"),
        "email": state.get("email", ""),
        "conversation_id": state.get("conversation_id", "unknown"),
        "metadata": state.get("context", {})
    }
