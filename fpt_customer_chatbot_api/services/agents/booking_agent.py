import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state.agent_state import CompleteOrEscalate
from tools.booking_tools import booking_tools

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

booking_agent_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are the **Booking Agent** for FPT Software's customer service system.

Your capabilities:
- Book a room/meeting (book_room)
- Track existing bookings by ID (track_booking)
- Update booking details (update_booking)
- Cancel bookings (cancel_booking)

Rules:
1. Always collect required fields before booking: reason, time, customer_name, customer_phone.
2. Time MUST be in the future (ISO format: YYYY-MM-DDTHH:MM:SS).
3. Status transitions: Scheduled → Finished (or Canceled from any state).
4. When the booking task is complete or user wants to switch topics, call 'CompleteOrEscalate'.
5. Be helpful and confirm bookings clearly with booking IDs.

Current Context:
- User ID: {user_id}
- Email: {email}
- Conversation ID: {conversation_id}
"""),
    ("placeholder", "{messages}")
])

booking_agent_runnable = booking_agent_prompt | llm.bind_tools(
    booking_tools + [CompleteOrEscalate]
)
