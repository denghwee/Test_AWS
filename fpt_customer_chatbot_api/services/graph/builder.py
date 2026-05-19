"""
Graph Builder - Complete Multi-Agent StateGraph Construction
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition

from fpt_customer_chatbot_api.services.state.agent_state import AgentState, CompleteOrEscalate
from fpt_customer_chatbot_api.services.state.dialog_stack import pop_dialog_state
from fpt_customer_chatbot_api.services.graph.entry_nodes import create_entry_node
from fpt_customer_chatbot_api.services.graph.tool_node import create_tool_node_with_fallback
from fpt_customer_chatbot_api.services.hitl.interrupt_config import SENSITIVE_TOOL_NAMES

# Import agent runnables
from fpt_customer_chatbot_api.services.agents.primary_assistant import (
    primary_assistant_runnable,
    ToTicketAssistant, ToBookingAssistant, ToITAssistant, ToFAQAssistant,
)
from fpt_customer_chatbot_api.services.agents.ticket_agent import ticket_agent_runnable
from fpt_customer_chatbot_api.services.agents.booking_agent import booking_agent_runnable
from fpt_customer_chatbot_api.services.agents.it_support_agent import it_support_agent_runnable, it_support_tools
from fpt_customer_chatbot_api.services.agents.faq_agent import faq_agent_runnable, faq_tools

# Import tools
from fpt_customer_chatbot_api.services.tools.ticket_tools import ticket_tools
from fpt_customer_chatbot_api.services.tools.booking_tools import booking_tools

def primary_assistant_node(state: AgentState) -> dict:
    result = primary_assistant_runnable.invoke(state)
    return {"messages": [result]}

def ticket_agent_node(state: AgentState) -> dict:
    result = ticket_agent_runnable.invoke(state)
    return {"messages": [result]}

def booking_agent_node(state: AgentState) -> dict:
    result = booking_agent_runnable.invoke(state)
    return {"messages": [result]}

def it_support_agent_node(state: AgentState) -> dict:
    result = it_support_agent_runnable.invoke(state)
    return {"messages": [result]}

def faq_agent_node(state: AgentState) -> dict:
    result = faq_agent_runnable.invoke(state)
    return {"messages": [result]}

def leave_skill_node(state: AgentState) -> dict:
    from langchain_core.messages import ToolMessage
    messages = []
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls"):
        for tc in state["messages"][-1].tool_calls:
            if tc["name"] == "CompleteOrEscalate":
                reason = tc.get("args", {}).get("reason", "Task finished.")
                messages.append(
                    ToolMessage(
                        content=f"Returning to Primary Assistant. Reason: {reason}",
                        tool_call_id=tc["id"],
                    )
                )
    return {
        "messages": messages,
        "dialog_stack": "pop",
    }

def tasks_dispatcher_node(state: AgentState) -> dict:
    """Entry point for routing and resume logic."""
    return {}

def route_tasks_dispatcher(state: AgentState):
    stack = state.get("dialog_stack", [])
    if stack:
        active_agent = stack[-1]
        if active_agent in ["ticket", "booking", "it_support", "faq"]:
            return active_agent
    return "primary_assistant"

def route_primary_assistant(state: AgentState):
    route = tools_condition(state)
    if route == END:
        return END
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END
    tool_name = last_message.tool_calls[0]["name"]
    if tool_name == "ToTicketAssistant":
        return "enter_ticket"
    elif tool_name == "ToBookingAssistant":
        return "enter_booking"
    elif tool_name == "ToITAssistant":
        return "enter_it_support"
    elif tool_name == "ToFAQAssistant":
        return "enter_faq"
    return END

def route_specialized_agent(state: AgentState):
    route = tools_condition(state)
    if route == END:
        return END
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END
    tool_names = [tc["name"] for tc in last_message.tool_calls]
    if "CompleteOrEscalate" in tool_names:
        return "leave_skill"
    stack = state.get("dialog_stack", [])
    current_agent = stack[-1] if stack else "primary"
    return f"{current_agent}_tools"

def build_graph(checkpointer=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("tasks_dispatcher", tasks_dispatcher_node)
    workflow.add_node("primary_assistant", primary_assistant_node)
    workflow.add_node("ticket", ticket_agent_node)
    workflow.add_node("booking", booking_agent_node)
    workflow.add_node("it_support", it_support_agent_node)
    workflow.add_node("faq", faq_agent_node)
    workflow.add_node("ticket_tools", create_tool_node_with_fallback(ticket_tools))
    workflow.add_node("booking_tools", create_tool_node_with_fallback(booking_tools))
    workflow.add_node("it_support_tools", create_tool_node_with_fallback(it_support_tools))
    workflow.add_node("faq_tools", create_tool_node_with_fallback(faq_tools))
    workflow.add_node("enter_ticket", create_entry_node("Ticket Assistant", "ticket"))
    workflow.add_node("enter_booking", create_entry_node("Booking Assistant", "booking"))
    workflow.add_node("enter_it_support", create_entry_node("IT Support", "it_support"))
    workflow.add_node("enter_faq", create_entry_node("FAQ Agent", "faq"))
    workflow.add_node("leave_skill", leave_skill_node)

    workflow.add_edge(START, "tasks_dispatcher")
    workflow.add_conditional_edges("tasks_dispatcher", route_tasks_dispatcher, {
        "primary_assistant": "primary_assistant",
        "ticket": "ticket",
        "booking": "booking",
        "it_support": "it_support",
        "faq": "faq",
    })
    workflow.add_conditional_edges("primary_assistant", route_primary_assistant, {
        "enter_ticket": "enter_ticket",
        "enter_booking": "enter_booking",
        "enter_it_support": "enter_it_support",
        "enter_faq": "enter_faq",
        END: END,
    })
    workflow.add_edge("enter_ticket", "ticket")
    workflow.add_edge("enter_booking", "booking")
    workflow.add_edge("enter_it_support", "it_support")
    workflow.add_edge("enter_faq", "faq")

    workflow.add_conditional_edges("ticket", route_specialized_agent, {"ticket_tools": "ticket_tools", "leave_skill": "leave_skill", END: END})
    workflow.add_edge("ticket_tools", "ticket")
    workflow.add_conditional_edges("booking", route_specialized_agent, {"booking_tools": "booking_tools", "leave_skill": "leave_skill", END: END})
    workflow.add_edge("booking_tools", "booking")
    workflow.add_conditional_edges("it_support", route_specialized_agent, {"it_support_tools": "it_support_tools", "leave_skill": "leave_skill", END: END})
    workflow.add_edge("it_support_tools", "it_support")
    workflow.add_conditional_edges("faq", route_specialized_agent, {"faq_tools": "faq_tools", "leave_skill": "leave_skill", END: END})
    workflow.add_edge("faq_tools", "faq")

    workflow.add_edge("leave_skill", "primary_assistant")

    compile_kwargs = {}
    if checkpointer: compile_kwargs["checkpointer"] = checkpointer
    compile_kwargs["interrupt_before"] = SENSITIVE_TOOL_NAMES
    return workflow.compile(**compile_kwargs)
