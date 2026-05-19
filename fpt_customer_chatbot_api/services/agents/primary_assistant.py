import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)


# ---------------------------------------------------------------------------
# Routing Tools — used by Primary to delegate to specialized agents
# ---------------------------------------------------------------------------

class ToTicketAssistant(BaseModel):
    """Transfer the conversation to the Ticket Support Assistant.
    Use when the user wants to create, track, update, or cancel support tickets."""
    request: str = Field(description="A summary of the user's ticket-related request to hand off.")


class ToBookingAssistant(BaseModel):
    """Transfer the conversation to the Booking Assistant.
    Use when the user wants to book, track, update, or cancel room/meeting bookings."""
    request: str = Field(description="A summary of the user's booking-related request to hand off.")


class ToITAssistant(BaseModel):
    """Transfer the conversation to the IT Support Agent.
    Use when the user has technical issues like WiFi, software, hardware problems."""
    request: str = Field(description="A summary of the user's IT-related issue to hand off.")


class ToFAQAssistant(BaseModel):
    """Transfer the conversation to the FAQ Agent.
    Use when the user asks about FPT company policies, code of conduct, benefits, or guidelines."""
    request: str = Field(description="A summary of the user's policy/FAQ question to hand off.")


# ---------------------------------------------------------------------------
# Primary Assistant Prompt & Runnable
# ---------------------------------------------------------------------------

primary_assistant_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are the **Primary Assistant** for FPT Software's multi-agent customer service system.

Your role is to greet the user, understand their intent, and route them to the appropriate specialized assistant:

1. **ToTicketAssistant** — For support ticket management (create, track, update, cancel tickets)
2. **ToBookingAssistant** — For room/meeting bookings (book, track, update, cancel bookings)
3. **ToITAssistant** — For technical IT troubleshooting (WiFi, software, hardware issues)
4. **ToFAQAssistant** — For FPT company policy questions (code of conduct, HR, compliance)

Rules:
- If the user's intent is clear, route immediately to the right assistant.
- If the intent is ambiguous, ask a clarifying question.
- For general greetings or chitchat, respond warmly and ask how you can help.
- Never try to handle specialized tasks yourself — always delegate.
- You can handle multiple topics in sequence (user will be routed back after each).

Current Context:
- User ID: {user_id}
- Email: {email}
- Conversation ID: {conversation_id}
"""),
    ("placeholder", "{messages}")
])

primary_routing_tools = [ToTicketAssistant, ToBookingAssistant, ToITAssistant, ToFAQAssistant]

primary_assistant_runnable = primary_assistant_prompt | llm.bind_tools(primary_routing_tools)
