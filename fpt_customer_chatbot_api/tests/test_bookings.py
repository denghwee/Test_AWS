"""
Test Bookings: Booking CRUD, Booking Router, Booking Tools, Graph Builder,
Entry Nodes, Tool Node, Cache, Mock Store (bookings).
"""
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

# ═══════════════════════════════════════════════════════════
# BOOKING ROUTER & CRUD TESTS
# ═══════════════════════════════════════════════════════════

def _get_token(client, db, email="booking@test.com"):
    from fpt_customer_chatbot_api.models.user import User
    from fpt_customer_chatbot_api.utils.security import get_password_hash
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(email=email, hashed_password=get_password_hash("pass123"), full_name="Booking User")
        db.add(u); db.commit()
    login = client.post("/api/v1/auth/login", data={"username": email, "password": "pass123"})
    return login.json()["access_token"]

def test_booking_validation(client, db):
    token = _get_token(client, db, "val@test.com")
    h = {"Authorization": f"Bearer {token}"}
    # Past time
    res = client.post("/api/v1/bookings/", json={
        "reason": "Past", "time": "2020-01-01T10:00:00", 
        "customer_name": "N", "customer_phone": "1"
    }, headers=h)
    assert res.status_code == 400
    assert "future" in res.json()["detail"].lower()

def test_booking_full_lifecycle(client, db):
    token = _get_token(client, db)
    h = {"Authorization": f"Bearer {token}"}

    # Create
    res = client.post("/api/v1/bookings/", json={"reason": "Meeting", "time": "2030-01-01T10:00:00"}, headers=h)
    assert res.status_code == 201
    bid = res.json()["booking_id"]
    assert res.json()["status"] == "Scheduled"

    # List
    res = client.get("/api/v1/bookings/", headers=h)
    assert res.status_code == 200
    assert any(b["booking_id"] == bid for b in res.json())

    # Get by ID
    res = client.get(f"/api/v1/bookings/{bid}", headers=h)
    assert res.status_code == 200

    # Update
    res = client.put(f"/api/v1/bookings/{bid}", json={"time": "2030-01-02T14:00:00"}, headers=h)
    assert res.status_code == 200

    # Cancel
    res = client.delete(f"/api/v1/bookings/{bid}", headers=h)
    assert res.status_code == 200
    assert res.json()["status"] == "Canceled"

    # Cannot cancel again
    res = client.delete(f"/api/v1/bookings/{bid}", headers=h)
    assert res.status_code == 400

    # Update to past time
    res = client.put(f"/api/v1/bookings/{bid}", json={"time": "2020-01-01T10:00:00"}, headers=h)
    assert res.status_code == 400
    assert "future" in res.json()["detail"].lower()

    # Cannot update canceled
    res = client.put(f"/api/v1/bookings/{bid}", json={"reason": "New"}, headers=h)
    assert res.status_code == 400

    # 404 for nonexistent
    res = client.get("/api/v1/bookings/nonexistent", headers=h)
    assert res.status_code == 404
    res = client.put("/api/v1/bookings/nonexistent", json={"reason": "x"}, headers=h)
    assert res.status_code == 404
    res = client.delete("/api/v1/bookings/nonexistent", headers=h)
    assert res.status_code == 404

# ═══════════════════════════════════════════════════════════
# BOOKING TOOLS (LangGraph tools)
# ═══════════════════════════════════════════════════════════

def test_booking_tools_full(db):
    from fpt_customer_chatbot_api.services.tools import booking_tools
    from fpt_customer_chatbot_api.models.user import User
    booking_tools._test_db = db
    u = db.query(User).filter(User.email == "bktool@test.com").first()
    if not u:
        u = User(email="bktool@test.com", hashed_password="...", full_name="BK Tool")
        db.add(u); db.commit()
    # Create
    res = booking_tools.create_room_booking.invoke({"reason": "Test", "time": "2030-12-01T10:00:00", "email": "bktool@test.com"})
    assert "Successfully" in res
    bid = res.split("ID: ")[1].split(".")[0]
    # Update
    res = booking_tools.update_booking_time.invoke({"booking_id": bid, "new_time": "2030-12-01T11:00:00", "email": "bktool@test.com"})
    assert "updated" in res
    # List
    res = booking_tools.list_user_bookings.invoke({"email": "bktool@test.com"})
    assert "bookings" in res.lower()
    # Cancel
    res = booking_tools.cancel_room_booking.invoke({"booking_id": bid, "email": "bktool@test.com"})
    assert "cancelled" in res.lower()
    # Not found
    res = booking_tools.update_booking_time.invoke({"booking_id": "nope", "new_time": "2030-01-01T10:00", "email": "x"})
    assert "No booking" in res
    res = booking_tools.cancel_room_booking.invoke({"booking_id": "nope", "email": "x"})
    assert "No booking" in res
    # User not found
    res = booking_tools.list_user_bookings.invoke({"email": "nonexistent@x.com"})
    assert "not found" in res.lower()
    # Invalid time
    res = booking_tools.create_room_booking.invoke({"reason": "T", "time": "not-a-time", "email": "bktool@test.com"})
    assert "Invalid" in res
    res = booking_tools.update_booking_time.invoke({"booking_id": bid, "new_time": "bad", "email": "bktool@test.com"})
    assert "Invalid" in res
    booking_tools._test_db = None

# ═══════════════════════════════════════════════════════════
# MOCK STORE (bookings part)
# ═══════════════════════════════════════════════════════════

def test_mock_store_bookings():
    from fpt_customer_chatbot_api.services.tools.mock_store import (
        store_booking, get_booking, update_booking_data, list_bookings
    )
    store_booking("mb1", {"reason": "Meet", "status": "Scheduled"})
    assert get_booking("mb1")["reason"] == "Meet"
    assert get_booking("nope") is None
    assert update_booking_data("mb1", {"status": "Canceled"})["status"] == "Canceled"
    assert update_booking_data("nope", {}) is None
    assert "mb1" in list_bookings()

# ═══════════════════════════════════════════════════════════
# GRAPH: Entry Nodes, Tool Node, Builder
# ═══════════════════════════════════════════════════════════

def test_entry_node():
    from fpt_customer_chatbot_api.services.graph.entry_nodes import create_entry_node
    fn = create_entry_node("Booking Assistant", "booking")
    assert fn.__name__ == "enter_booking"
    ai = AIMessage(content="", tool_calls=[{"name": "ToBookingAssistant", "args": {}, "id": "tc1"}])
    result = fn({"messages": [ai]})
    assert result["dialog_stack"] == "booking"
    assert "Booking Assistant" in result["messages"][0].content

def test_tool_node_error_handler():
    from fpt_customer_chatbot_api.services.graph.tool_node import _handle_tool_error
    ai = AIMessage(content="", tool_calls=[{"name": "tool1", "args": {}, "id": "tc1"}, {"name": "tool2", "args": {}, "id": "tc2"}])
    result = _handle_tool_error({"error": ValueError("Bad"), "messages": [ai]})
    assert len(result["messages"]) == 2
    assert "Error" in result["messages"][0].content

def test_graph_routing():
    from fpt_customer_chatbot_api.services.graph.builder import (
        tasks_dispatcher_node, route_tasks_dispatcher, route_primary_assistant,
        route_specialized_agent, leave_skill_node, build_graph
    )
    assert tasks_dispatcher_node({}) == {}
    # route_tasks_dispatcher
    assert route_tasks_dispatcher({"dialog_stack": []}) == "primary_assistant"
    assert route_tasks_dispatcher({"dialog_stack": ["ticket"]}) == "ticket"
    assert route_tasks_dispatcher({"dialog_stack": ["booking"]}) == "booking"
    assert route_tasks_dispatcher({"dialog_stack": ["it_support"]}) == "it_support"
    assert route_tasks_dispatcher({"dialog_stack": ["faq"]}) == "faq"
    assert route_tasks_dispatcher({"dialog_stack": ["unknown"]}) == "primary_assistant"
    # route_primary_assistant
    assert route_primary_assistant({"messages": [AIMessage(content="Done")]}) == END
    assert route_primary_assistant({"messages": [AIMessage(content="", tool_calls=[{"name": "ToTicketAssistant", "args": {}, "id": "1"}])]}) == "enter_ticket"
    assert route_primary_assistant({"messages": [AIMessage(content="", tool_calls=[{"name": "ToBookingAssistant", "args": {}, "id": "1"}])]}) == "enter_booking"
    assert route_primary_assistant({"messages": [AIMessage(content="", tool_calls=[{"name": "ToITAssistant", "args": {}, "id": "1"}])]}) == "enter_it_support"
    assert route_primary_assistant({"messages": [AIMessage(content="", tool_calls=[{"name": "ToFAQAssistant", "args": {}, "id": "1"}])]}) == "enter_faq"
    assert route_primary_assistant({"messages": [AIMessage(content="", tool_calls=[{"name": "Unknown", "args": {}, "id": "1"}])]}) == END
    # route_specialized_agent
    assert route_specialized_agent({"messages": [AIMessage(content="Hi")], "dialog_stack": ["ticket"]}) == END
    assert route_specialized_agent({"messages": [AIMessage(content="", tool_calls=[{"name": "CompleteOrEscalate", "args": {}, "id": "1"}])], "dialog_stack": ["ticket"]}) == "leave_skill"
    assert route_specialized_agent({"messages": [AIMessage(content="", tool_calls=[{"name": "create_support_ticket", "args": {}, "id": "1"}])], "dialog_stack": ["ticket"]}) == "ticket_tools"
    # leave_skill_node
    ai = AIMessage(content="", tool_calls=[{"name": "CompleteOrEscalate", "args": {"reason": "Finished"}, "id": "tc1"}])
    result = leave_skill_node({"messages": [ai]})
    assert result["dialog_stack"] == "pop" and "Finished" in result["messages"][0].content
    result2 = leave_skill_node({"messages": [HumanMessage(content="Hi")]})
    assert result2["messages"] == []

def test_build_graph():
    from fpt_customer_chatbot_api.services.graph.builder import build_graph
    from langgraph.checkpoint.memory import MemorySaver
    g = build_graph()
    assert g is not None
    g2 = build_graph(checkpointer=MemorySaver())
    assert g2 is not None

# ═══════════════════════════════════════════════════════════
# CACHE: CacheStats + CacheManager
# ═══════════════════════════════════════════════════════════

def test_cache_stats():
    from fpt_customer_chatbot_api.services.cache.cache_stats import CacheStats
    s = CacheStats()
    assert s.total_lookups == 0 and s.hit_rate == 0.0
    s.record_hit(); s.record_hit(); s.record_miss(); s.record_store()
    assert s.hits == 2 and s.misses == 1 and s.stores == 1
    assert s.hit_rate == pytest.approx(2/3, rel=1e-2)
    d = s.get_stats()
    assert d["total_lookups"] == 3 and "uptime_seconds" in d
    report = s.get_report()
    assert "Cache Statistics" in report and "Hit Rate" in report
    s.reset()
    assert s.hits == 0 and len(s._history) == 0

def test_cache_manager():
    from fpt_customer_chatbot_api.services.cache.cache_manager import CacheManager
    hit, resp, sim = CacheManager.check_and_return("test query")
    assert hit is False  # No cache initially
    stats = CacheManager.get_stats()
    assert "misses" in stats
    report = CacheManager.get_stats_report()
    assert "Cache" in report
    ttl = CacheManager.get_ttl_hours()
    assert ttl == 24.0
    result = CacheManager.clear()
    assert "cleared" in result.lower()

# ═══════════════════════════════════════════════════════════
# FAISS CACHE (Internal Logic)
# ═══════════════════════════════════════════════════════════

def test_faiss_cache_logic():
    from fpt_customer_chatbot_api.services.cache import faiss_cache
    from unittest.mock import patch
    
    with patch("fpt_customer_chatbot_api.services.cache.faiss_cache.HuggingFaceEmbeddings") as mock_emb:
        with patch("fpt_customer_chatbot_api.services.cache.faiss_cache.FAISS") as mock_faiss:
            # Test lazy load embeddings
            faiss_cache._embeddings = None
            faiss_cache._get_embeddings()
            assert mock_emb.called
            
            # Test cache_response
            faiss_cache._cache_store = None
            faiss_cache.cache_response("q", "r")
            assert mock_faiss.from_texts.called
            
            # Test lookup_cache - miss (no store)
            faiss_cache._cache_store = None
            hit, res, sim = faiss_cache.lookup_cache("q")
            assert hit is False
            
            # Test lookup_cache - hit
            mock_store = MagicMock()
            mock_doc = MagicMock()
            mock_doc.metadata = {"response": "cached response", "timestamp": 1234567890}
            mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.05)]
            faiss_cache._cache_store = mock_store
            
            # TTL will fail because 1234567890 is very old
            hit, res, sim = faiss_cache.lookup_cache("q")
            assert hit is False
            
            # TTL success
            mock_doc.metadata["timestamp"] = 99999999999 
            hit, res, sim = faiss_cache.lookup_cache("q")
            assert hit is True
            assert "cached response" in res

def test_it_support_agent_runnable():
    from fpt_customer_chatbot_api.services.agents.it_support_agent import it_support_agent_runnable
    assert it_support_agent_runnable is not None

# ═══════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════

def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Welcome" in res.json()["message"]
