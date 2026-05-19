from typing import List, Dict, Any, Optional
from fpt_customer_chatbot_api.services.ai_adapter import ai_adapter
from fpt_customer_chatbot_api.schemas.chat import ChatMessage

class ChatService:
    async def get_chat_response(self, message: str, thread_id: Optional[str] = None, user_id: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for chat requests. Coordinates AI processing and history formatting.
        """
        user_info = {
            "user_id": user_id or "default",
            "email": email or "user@fpt.com.vn"
        }
        
        # AI processing (synchronous invoke inside adapter)
        result = ai_adapter.process_message(message, thread_id, user_info)
        
        # Format history for the response
        history = []
        if thread_id:
            try:
                state = ai_adapter.graph.get_state({"configurable": {"thread_id": thread_id}})
                messages = state.values.get("messages", [])
                for msg in messages:
                    # Map LangChain message types to user/assistant roles
                    role = "user" if hasattr(msg, "type") and msg.type == "human" else "assistant"
                    # Exclude internal tool messages from public history
                    if getattr(msg, "type", "") == "tool":
                        continue
                    content = getattr(msg, "content", str(msg))
                    if content:
                        history.append(ChatMessage(role=role, content=content))
            except:
                pass # Thread might not exist yet
        
        return {
            "response": result["response"],
            "thread_id": result["thread_id"],
            "history": history,
            "status": result["status"]
        }

    async def confirm_action(self, conversation_id: str, confirm: bool) -> Dict[str, Any]:
        """
        Handle HITL confirmation responses.
        """
        result = ai_adapter.confirm_action(conversation_id, confirm)
        return result

chat_service = ChatService()
