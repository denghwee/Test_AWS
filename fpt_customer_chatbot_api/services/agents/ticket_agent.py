import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state.agent_state import CompleteOrEscalate
from tools.ticket_tools import ticket_tools

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    streaming=True,
    api_key=os.getenv("OPENAI_API_KEY")
)

ticket_agent_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are the **Ticket Support Agent** for FPT Software's customer service system.

Your capabilities:
- Create new support tickets (create_ticket)
- Track existing tickets by ID (track_ticket)
- Update ticket information (update_ticket)
- Cancel tickets (cancel_ticket)

Rules:
1. Always collect required fields before creating: content, customer_name, customer_phone.
2. Status transitions: Pending → InProgress → Resolved (or Canceled from any state).
3. When the user's ticket task is complete or they want to switch topics, call 'CompleteOrEscalate'.
4. Be helpful and confirm actions clearly with ticket IDs.
5. If you cannot assist further, escalate back to the Primary Assistant.

Current Context:
- User ID: {user_id}
- Email: {email}
- Conversation ID: {conversation_id}
"""),
    ("placeholder", "{messages}")
])

ticket_agent_runnable = ticket_agent_prompt | llm.bind_tools(
    ticket_tools + [CompleteOrEscalate]
)
