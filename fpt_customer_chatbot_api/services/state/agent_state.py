from typing import Annotated, List, Optional, Union, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

def update_dialog_stack(left: list[str], right: Optional[Union[str, list[str]]]) -> list[str]:
    """Reducer for the dialog stack. 
    - If None: no change.
    - If string: push to stack.
    - If list: replace stack.
    - If 'pop': remove last item.
    """
    if right is None:
        return left
    if right == "pop":
        return left[:-1] if left else left
    if isinstance(right, str):
        return left + [right]
    return right # Replace

class AgentState(TypedDict):
    """The state of the conversation agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    email: str
    conversation_id: str
    # The stack of active dialogs (e.g., ["primary", "booking"])
    dialog_stack: Annotated[list[str], update_dialog_stack]
    # Context injected from external systems or previous turns
    context: Dict[str, Any]

class CompleteOrEscalate(BaseModel):
    """A tool to mark the current task as complete and return to the main assistant, 
    or escalate to a human if the AI cannot fulfill the request."""
    cancel: bool = Field(default=False, description="True if the user wants to cancel the current task.")
    reason: Optional[str] = Field(default=None, description="The reason for completion or escalation.")
