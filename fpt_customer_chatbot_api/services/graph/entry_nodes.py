"""
Entry Nodes - Factory for Agent Transition Nodes
"""

from langchain_core.messages import ToolMessage
from fpt_customer_chatbot_api.services.state.agent_state import AgentState

def create_entry_node(assistant_name: str, new_dialog_stack_item: str):
    """
    Factory function that creates an entry node for agent transitions.
    """
    def entry_node(state: AgentState) -> dict:
        # Get the tool_call_id from the last message (the routing tool call)
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]
        return {
            "messages": [
                ToolMessage(
                    content=(
                        f"The assistant is now the {assistant_name}. "
                        f"Reflect the user's request and assist them with their task. "
                        f"If you need to return to the main menu, use CompleteOrEscalate."
                    ),
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_stack": new_dialog_stack_item,
        }

    entry_node.__name__ = f"enter_{new_dialog_stack_item}"
    return entry_node
