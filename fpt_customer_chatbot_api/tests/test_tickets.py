"""
Test Tickets: Ticket CRUD, Ticket Router, Ticket Tools, HITL, State, Chat Service,
Thread Manager, Mock Store (tickets), AI Adapter logic.
"""
import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# ═══════════════════════════════════════════════════════════
# TICKET ROUTER & CRUD TESTS
# ═══════════════════════════════════════════════════════════

def _get_token(client, db, email="ticket@test.com"):
    from fpt_customer_chatbot_api.models.user import User
    from fpt_customer_chatbot_api.utils.security import get_password_hash
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(email=email, hashed_password=get_password_hash("pass123"), full_name="Ticket User")
        db.add(u); db.commit()
    login = client.post("/api/v1/auth/login", data={"username": email, "password": "pass123"})
    return login.json()["access_token"]

def test_ticket_full_lifecycle(client, db):
    token = _get_token(client, db)
    h = {"Authorization": f"Bearer {token}"}

    # Create
    res = client.post("/api/v1/tickets/", json={"content": "WiFi broken", "description": "Help"}, headers=h)
    assert res.status_code == 201
    tid = res.json()["ticket_id"]

    # List
    res = client.get("/api/v1/tickets/", headers=h)
    assert res.status_code == 200
    assert any(t["ticket_id"] == tid for t in res.json())

    # List with status filter
    res = client.get("/api/v1/tickets/?status=Pending", headers=h)
    assert res.status_code == 200

    # Get by ID
    res = client.get(f"/api/v1/tickets/{tid}", headers=h)
    assert res.status_code == 200
    assert res.json()["status"] == "Pending"

    # Update to InProgress
    res = client.put(f"/api/v1/tickets/{tid}", json={"status": "InProgress"}, headers=h)
    assert res.status_code == 200
    assert res.json()["status"] == "InProgress"

    # Resolve
    res = client.put(f"/api/v1/tickets/{tid}", json={"status": "Resolved"}, headers=h)
    assert res.status_code == 200

    # Cannot update resolved -> 400
    res = client.put(f"/api/v1/tickets/{tid}", json={"status": "Pending"}, headers=h)
    assert res.status_code == 400

    # 404 for non-existent
    res = client.get("/api/v1/tickets/nonexistent", headers=h)
    assert res.status_code == 404
    res = client.put("/api/v1/tickets/nonexistent", json={"status": "Pending"}, headers=h)
    assert res.status_code == 404
    res = client.delete("/api/v1/tickets/nonexistent", headers=h)
    assert res.status_code == 404

def test_ticket_cancel(client, db):
    token = _get_token(client, db, "cancel_tk@test.com")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/tickets/", json={"content": "Cancel me", "description": "D"}, headers=h)
    tid = res.json()["ticket_id"]
    res = client.delete(f"/api/v1/tickets/{tid}", headers=h)
    assert res.status_code == 200
    assert res.json()["status"] == "Canceled"
    # Cannot cancel again
    res = client.delete(f"/api/v1/tickets/{tid}", headers=h)
    assert res.status_code == 400

# ═══════════════════════════════════════════════════════════
# TICKET TOOLS (LangGraph tools)
# ═══════════════════════════════════════════════════════════

def test_ticket_tools_full(db):
    from fpt_customer_chatbot_api.services.tools import ticket_tools
    from fpt_customer_chatbot_api.models.user import User
    ticket_tools._test_db = db
    u = db.query(User).filter(User.email == "tktool@test.com").first()
    if not u:
        u = User(email="tktool@test.com", hashed_password="...", full_name="TK Tool")
        db.add(u); db.commit()
    # Create
    res = ticket_tools.create_support_ticket.invoke({"content": "Issue", "description": "Desc", "user_id": "1", "email": "tktool@test.com"})
    assert "Successfully" in res
    tid = res.split("ticket ")[1].split(".")[0]
    # Status
    res = ticket_tools.get_ticket_status.invoke({"ticket_id": tid, "email": "tktool@test.com"})
    assert "Pending" in res
    # Resolve
    res = ticket_tools.resolve_ticket.invoke({"ticket_id": tid, "email": "tktool@test.com"})
    assert "Resolved" in res
    # Not found
    res = ticket_tools.get_ticket_status.invoke({"ticket_id": "none", "email": "x"})
    assert "No ticket" in res
    res = ticket_tools.resolve_ticket.invoke({"ticket_id": "none", "email": "x"})
    assert "No ticket" in res
    ticket_tools._test_db = None

# ═══════════════════════════════════════════════════════════
# STATE MODULE
# ═══════════════════════════════════════════════════════════

def test_update_dialog_stack():
    from fpt_customer_chatbot_api.services.state.agent_state import update_dialog_stack, CompleteOrEscalate
    assert update_dialog_stack(["a", "b"], None) == ["a", "b"]
    assert update_dialog_stack(["a", "b"], "pop") == ["a"]
    assert update_dialog_stack([], "pop") == []
    assert update_dialog_stack(["a"], "b") == ["a", "b"]
    assert update_dialog_stack(["a"], ["x", "y"]) == ["x", "y"]
    obj = CompleteOrEscalate(cancel=True, reason="Done")
    assert obj.cancel is True

def test_dialog_stack_helpers():
    from fpt_customer_chatbot_api.services.state.dialog_stack import pop_dialog_state, get_current_agent
    assert pop_dialog_state({}) == {"dialog_stack": "pop"}
    assert get_current_agent({"dialog_stack": ["primary", "booking"]}) == "booking"
    assert get_current_agent({"dialog_stack": []}) == "primary_assistant"
    assert get_current_agent({}) == "primary_assistant"

def test_context_injection():
    from fpt_customer_chatbot_api.services.state.context_injection import inject_user_context, get_context_for_tools
    r = inject_user_context({}, user_id="u1", email="a@b.com", conversation_id="c1", metadata={"x": 1})
    assert r["user_id"] == "u1" and r["email"] == "a@b.com" and r["context"]["x"] == 1
    r2 = inject_user_context({})
    assert len(r2["conversation_id"]) == 36
    ctx = get_context_for_tools({"user_id": "u1", "email": "e", "conversation_id": "c", "context": {"k": "v"}})
    assert ctx["metadata"]["k"] == "v"
    assert get_context_for_tools({})["user_id"] == "unknown"

# ═══════════════════════════════════════════════════════════
# HITL: message_generator + confirmation
# ═══════════════════════════════════════════════════════════

def test_message_generator():
    from fpt_customer_chatbot_api.services.hitl.message_generator import (
        generate_confirmation_message, _get_readable_tool_name, extract_pending_tool_calls
    )
    assert generate_confirmation_message([]) == "No pending actions to confirm."
    msg = generate_confirmation_message([{"name": "create_room_booking", "args": {"reason": "Meet"}}])
    assert "CONFIRMATION" in msg and "Meet" in msg
    msg2 = generate_confirmation_message([
        {"name": "a", "args": {"x": 1}}, {"name": "b", "args": {"y": 2}}
    ])
    assert "Action 1" in msg2 and "Action 2" in msg2
    assert "📝" in _get_readable_tool_name("create_ticket")
    assert "🔧" in _get_readable_tool_name("unknown_tool")
    # extract
    assert extract_pending_tool_calls(None) == []
    s = MagicMock(); s.values = {}
    assert extract_pending_tool_calls(s) == []
    s.values = {"messages": []}
    assert extract_pending_tool_calls(s) == []
    s.values = {"messages": [HumanMessage(content="Hi")]}
    assert extract_pending_tool_calls(s) == []
    ai = AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    s.values = {"messages": [ai]}
    assert len(extract_pending_tool_calls(s)) == 1

def test_confirmation_logic():
    from fpt_customer_chatbot_api.services.hitl.confirmation import (
        is_sensitive_tool_call, handle_confirmation, process_user_response
    )
    assert is_sensitive_tool_call([{"name": "create_room_booking"}]) is True
    assert is_sensitive_tool_call([{"name": "list_user_bookings"}]) is False
    # handle_confirmation - no next
    g = MagicMock(); st = MagicMock(); st.next = []; g.get_state.return_value = st
    needs, msg = handle_confirmation(g, {})
    assert needs is False
    # handle_confirmation - non-sensitive
    st.next = ["tools"]
    st.values = {"messages": [AIMessage(content="", tool_calls=[{"name": "list_user_bookings", "args": {}, "id": "1"}])]}
    needs, _ = handle_confirmation(g, {})
    assert needs is False
    # handle_confirmation - sensitive
    st.values = {"messages": [AIMessage(content="", tool_calls=[{"name": "create_room_booking", "args": {"r": "x"}, "id": "1"}])]}
    needs, msg = handle_confirmation(g, {})
    assert needs is True and "CONFIRMATION" in msg
    # process - approve
    g2 = MagicMock(); g2.invoke.return_value = {"messages": []}
    process_user_response(g2, {}, "yes")
    g2.invoke.assert_called_with(None, {})
    # process - reject
    g3 = MagicMock()
    st3 = MagicMock(); st3.values = {"messages": [AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "tc1"}])]}
    g3.get_state.return_value = st3; g3.invoke.return_value = {}
    process_user_response(g3, {}, "no")
    assert g3.update_state.called

# ═══════════════════════════════════════════════════════════
# MOCK STORE (tickets part)
# ═══════════════════════════════════════════════════════════

def test_mock_store_tickets():
    from fpt_customer_chatbot_api.services.tools.mock_store import (
        store_ticket, get_ticket, update_ticket_data, list_tickets
    )
    store_ticket("mt1", {"content": "Bug", "status": "Pending"})
    assert get_ticket("mt1")["content"] == "Bug"
    assert get_ticket("nope") is None
    assert update_ticket_data("mt1", {"status": "Resolved"})["status"] == "Resolved"
    assert update_ticket_data("nope", {}) is None
    assert "mt1" in list_tickets()

# ═══════════════════════════════════════════════════════════
# THREAD MANAGER
# ═══════════════════════════════════════════════════════════

def test_thread_manager(tmp_path):
    import fpt_customer_chatbot_api.services.persistence.thread_manager as tm
    orig = tm.DB_PATH
    tm.DB_PATH = str(tmp_path / "nonexistent.db")
    assert tm.list_active_threads() == []
    assert tm.get_thread_history("x") == []
    assert "No checkpoint" in tm.delete_thread("x")
    assert "No threads" in tm.cleanup_old_threads()
    assert "No active" in tm.format_thread_list([])
    # Create DB
    test_db = str(tmp_path / "test.db")
    tm.DB_PATH = test_db
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint_id TEXT, parent_id TEXT)")
    conn.execute("INSERT INTO checkpoints VALUES ('t1', 'c1', NULL)")
    conn.execute("INSERT INTO checkpoints VALUES ('t1', 'c2', 'c1')")
    conn.execute("INSERT INTO checkpoints VALUES ('t2', 'c3', NULL)")
    conn.commit(); conn.close()
    threads = tm.list_active_threads()
    assert len(threads) == 2
    assert len(tm.get_thread_history("t1")) == 2
    fmt = tm.format_thread_list(threads)
    assert "t1" in fmt and "Total: 2" in fmt
    assert "Found 2" in tm.cleanup_old_threads()
    assert "Deleted 2" in tm.delete_thread("t1")
    assert len(tm.list_active_threads()) == 1
    tm.DB_PATH = orig

# ═══════════════════════════════════════════════════════════
# CHAT SERVICE
# ═══════════════════════════════════════════════════════════

def test_chat_service():
    from fpt_customer_chatbot_api.services.chat_service import ChatService
    import asyncio
    service = ChatService()
    with patch("fpt_customer_chatbot_api.services.chat_service.ai_adapter") as mock_ad:
        mock_ad.process_message.return_value = {"response": "Hi!", "thread_id": "t1", "status": "success"}
        mock_st = MagicMock()
        mock_st.values = {"messages": [HumanMessage(content="Q"), AIMessage(content="A")]}
        mock_ad.graph.get_state.return_value = mock_st
        result = asyncio.get_event_loop().run_until_complete(service.get_chat_response("Q", thread_id="t1"))
        assert result["response"] == "Hi!"
        assert len(result["history"]) == 2
        # No thread -> empty history
        result2 = asyncio.get_event_loop().run_until_complete(service.get_chat_response("Q"))
        assert result2["history"] == []
        # Confirm
        mock_ad.confirm_action.return_value = {"status": "success"}
        r = asyncio.get_event_loop().run_until_complete(service.confirm_action("t1", True))
        assert r["status"] == "success"

# ═══════════════════════════════════════════════════════════
# AI ADAPTER (Internal Logic)
# ═══════════════════════════════════════════════════════════

def test_ai_adapter_logic():
    from fpt_customer_chatbot_api.services.ai_adapter import AIAdapter
    from langchain_core.messages import AIMessage, ToolMessage
    import asyncio
    
    adapter = AIAdapter()
    mock_graph = MagicMock()
    adapter.graph = mock_graph
    
    # Test process_message with pending tool calls (cancellation injection)
    mock_st = MagicMock()
    mock_st.next = ["ticket_tools"]
    mock_st.values = {"messages": [AIMessage(content="", tool_calls=[{"id": "tc1", "name": "n", "args": {}}])]}
    mock_graph.get_state.return_value = mock_st
    mock_graph.invoke.return_value = {"messages": [AIMessage(content="Hello")]}
    
    res = asyncio.run(adapter.process_message("Hi", conversation_id="t1", user_info={"user_id": "u1"}))
    assert res["response"] == "Hello"
    assert mock_graph.update_state.called # Cancellation should be injected
    
    # Test process_message error branch
    mock_graph.get_state.side_effect = Exception("Graph crash")
    res = asyncio.run(adapter.process_message("Hi Error Branch", conversation_id="t2"))
    assert "Error" in res["response"]

    # Test confirm_action success
    mock_graph.get_state.side_effect = None
    mock_st.next = ["tools"]
    mock_graph.get_state.return_value = mock_st
    res = asyncio.run(adapter.confirm_action("t1", True))
    assert res["status"] == "success"
    
    # Test confirm_action no pending
    mock_st.next = []
    res = asyncio.run(adapter.confirm_action("t1", True))
    assert "No pending" in res["response"]


def test_faq_agent_runnable():
    from fpt_customer_chatbot_api.services.agents.faq_agent import faq_agent_runnable
    # This just ensures the runnable is constructed correctly with tools
    assert faq_agent_runnable is not None

def test_chat_router(client, db):
    from unittest.mock import AsyncMock
    token = _get_token(client, db, "chatrouter@test.com")
    h = {"Authorization": f"Bearer {token}"}
    # Start conversation
    with patch("fpt_customer_chatbot_api.routers.chat.ai_adapter") as mock_ai:
        mock_ai.process_message = AsyncMock(return_value={"response": "Hello", "status": "success", "tool_calls": None})
        mock_ai.confirm_action = AsyncMock(return_value={"response": "OK", "status": "success", "tool_calls": None})
        res = client.post("/api/v1/chat/conversations", headers=h)
        assert res.status_code == 201
        cid = res.json()["conversation_id"]
        # List conversations
        res = client.get("/api/v1/chat/conversations", headers=h)
        assert res.status_code == 200
        # Send message
        res = client.post(f"/api/v1/chat/conversations/{cid}/messages", json={"content": "Hi"}, headers=h)
        assert res.status_code == 200
        # 404 for non-existent conversation
        res = client.post("/api/v1/chat/conversations/nonexistent/messages", json={"content": "Hi"}, headers=h)
        assert res.status_code == 404
        # Confirm
        res = client.post(f"/api/v1/chat/conversations/{cid}/confirm", json={"confirm": True}, headers=h)
        assert res.status_code == 200
        res = client.post("/api/v1/chat/conversations/nonexistent/confirm", json={"confirm": True}, headers=h)
        assert res.status_code == 404

