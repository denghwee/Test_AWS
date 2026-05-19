import os
import sys
import uuid
from typing import Dict, Any, List, Optional

# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from fpt_customer_chatbot_api.services.graph.builder import build_graph
from fpt_customer_chatbot_api.services.persistence.checkpointer import get_sqlite_checkpointer
from fpt_customer_chatbot_api.services.cache.cache_manager import CacheManager
from fpt_customer_chatbot_api.services.hitl.message_generator import extract_pending_tool_calls, generate_confirmation_message
from fpt_customer_chatbot_api.services.hitl.confirmation import is_sensitive_tool_call
from fpt_customer_chatbot_api.services.state.context_injection import inject_user_context

class AIAdapter:
    def __init__(self):
        self.checkpointer = None
        self.graph = None
        self._initialize()

    def _initialize(self):
        # Persistent checkpointer for the lifecycle of the adapter
        self.checkpointer_cm = get_sqlite_checkpointer()
        self.checkpointer = self.checkpointer_cm.__enter__()
        self.graph = build_graph(checkpointer=self.checkpointer)

    async def process_message(self, message: str, conversation_id: str, user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to the AI and handle the response or HITL interruption."""
        config = {"configurable": {"thread_id": conversation_id}}
        user_id = user_info.get("user_id", "default") if user_info else "default"
        email = user_info.get("email", "user@fpt.com.vn") if user_info else "user@fpt.com.vn"

        try:
            # 1. Check Cache
            hit, cached_response, _ = CacheManager.check_and_return(message)
            if hit:
                return {"response": cached_response, "status": "success", "from_cache": True, "thread_id": conversation_id}

            # 2. Get State to see if we are resuming
            current_state = self.graph.get_state(config)
            
            # 3. Prepare Input
            if current_state.next:
                # We have pending actions but the user sent a new message instead of confirming.
                # We must "cancel" the pending tool calls by providing tool outputs before adding the new human message.
                tool_calls = extract_pending_tool_calls(current_state)
                if tool_calls:
                    cancel_messages = [
                        ToolMessage(
                            tool_call_id=tc['id'], 
                            content="User chose to ignore this action and sent a new message."
                        ) for tc in tool_calls
                    ]
                    self.graph.update_state(config, {"messages": cancel_messages})
                input_data = {"messages": [HumanMessage(content=message)]}
            elif not current_state.values:
                # Fresh start: inject context
                input_data = inject_user_context(
                    {},
                    user_id=str(user_id),
                    email=email,
                    conversation_id=conversation_id,
                    metadata=user_info.get("metadata", {})
                )
                input_data["messages"] = [HumanMessage(content=message)]
            else:
                # Resume/Continue
                input_data = {"messages": [HumanMessage(content=message)]}
            
            # 4. Run Graph (sync invoke since graph is sync, but we are in async method)
            result = self.graph.invoke(input_data, config)
            
            # 5. Check for HITL
            state = self.graph.get_state(config)
            if state.next:
                tool_calls = extract_pending_tool_calls(state)
                if tool_calls and is_sensitive_tool_call(tool_calls):
                    confirmation_msg = generate_confirmation_message(tool_calls)
                    return {
                        "response": confirmation_msg,
                        "status": "pending_confirmation",
                        "tool_calls": tool_calls,
                        "thread_id": conversation_id
                    }
            
            # 6. Success Response
            response_text = self._get_response_text(result)
            CacheManager.store(message, response_text)
            return {"response": response_text, "status": "success", "thread_id": conversation_id}

        except Exception as e:
            return {"response": f"Error: {str(e)}", "status": "error", "thread_id": conversation_id}

    async def confirm_action(self, conversation_id: str, confirm: bool) -> Dict[str, Any]:
        """Resume the graph after a HITL interruption."""
        config = {"configurable": {"thread_id": conversation_id}}
        
        try:
            state = self.graph.get_state(config)
            if not state.next:
                return {"response": "No pending action found.", "status": "error", "thread_id": conversation_id}

            if confirm:
                # Proceed
                result = self.graph.invoke(None, config)
            else:
                # Cancel: provide tool output to the blocked node
                tool_calls = extract_pending_tool_calls(state)
                tool_output = [
                    ToolMessage(
                        tool_call_id=tc['id'], 
                        content="Action cancelled by user."
                    ) for tc in tool_calls
                ]
                self.graph.update_state(config, {"messages": tool_output})
                result = self.graph.invoke(None, config)

            response_text = self._get_response_text(result)
            return {"response": response_text, "status": "success", "thread_id": conversation_id}

        except Exception as e:
            return {"response": f"Confirmation Error: {str(e)}", "status": "error", "thread_id": conversation_id}

    def _get_response_text(self, result: dict) -> str:
        messages = result.get("messages", [])
        if not messages: return "..."
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") != "tool":
                return msg.content
        return "Process completed."

# Singleton instance
ai_adapter = AIAdapter()
