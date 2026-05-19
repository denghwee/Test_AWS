"""
Test Auth: Authentication, Users, Security, Dependencies, Error Handling, Logging, Schemas.
"""
import pytest
import logging
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from langchain_core.messages import AIMessage

# ═══════════════════════════════════════════════════════════
# AUTH & USER ROUTER TESTS
# ═══════════════════════════════════════════════════════════

def test_auth_edge_cases(client, db):
    # Duplicate Registration
    u_data = {"email": "dup@test.com", "password": "pass", "full_name": "Dup"}
    client.post("/api/v1/auth/register", json=u_data)
    res = client.post("/api/v1/auth/register", json=u_data)
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"].lower()

    # Inactive Login
    from fpt_customer_chatbot_api.models.user import User
    user = db.query(User).filter(User.email == "dup@test.com").first()
    user.is_active = False
    db.commit()
    res = client.post("/api/v1/auth/login", data={"username": "dup@test.com", "password": "pass"})
    assert res.status_code == 400
    assert "inactive" in res.json()["detail"].lower()

def test_register_and_login(client, db):
    res = client.post("/api/v1/auth/register", json={
        "email": "auth@test.com", "password": "secret123", "full_name": "Auth User"
    })
    assert res.status_code == 201

    res = client.post("/api/v1/auth/login", data={"username": "auth@test.com", "password": "secret123"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_wrong_password(client, db):
    from fpt_customer_chatbot_api.models.user import User
    from fpt_customer_chatbot_api.utils.security import get_password_hash
    u = db.query(User).filter(User.email == "wrongpw@test.com").first()
    if not u:
        u = User(email="wrongpw@test.com", hashed_password=get_password_hash("correct"), full_name="WP")
        db.add(u); db.commit()
    res = client.post("/api/v1/auth/login", data={"username": "wrongpw@test.com", "password": "wrong"})
    assert res.status_code == 401

def test_get_profile(client, db):
    from fpt_customer_chatbot_api.models.user import User
    from fpt_customer_chatbot_api.utils.security import get_password_hash
    u = db.query(User).filter(User.email == "profile@test.com").first()
    if not u:
        u = User(email="profile@test.com", hashed_password=get_password_hash("pass123"), full_name="Profile")
        db.add(u); db.commit()
    login = client.post("/api/v1/auth/login", data={"username": "profile@test.com", "password": "pass123"})
    token = login.json()["access_token"]
    res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "profile@test.com"

def test_update_profile(client, db):
    from fpt_customer_chatbot_api.models.user import User
    from fpt_customer_chatbot_api.utils.security import get_password_hash
    u = db.query(User).filter(User.email == "upd@test.com").first()
    if not u:
        u = User(email="upd@test.com", hashed_password=get_password_hash("pass123"), full_name="Old")
        db.add(u); db.commit()
    login = client.post("/api/v1/auth/login", data={"username": "upd@test.com", "password": "pass123"})
    token = login.json()["access_token"]
    res = client.put("/api/v1/users/me", json={"full_name": "New Name"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

def test_invalid_token(client):
    res = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401

def test_no_token(client):
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401

# ═══════════════════════════════════════════════════════════
# SECURITY UTILS
# ═══════════════════════════════════════════════════════════

def test_password_hash_and_verify():
    from fpt_customer_chatbot_api.utils.security import get_password_hash, verify_password
    hashed = get_password_hash("mypassword")
    assert verify_password("mypassword", hashed) is True
    assert verify_password("wrong", hashed) is False

def test_create_access_token():
    from fpt_customer_chatbot_api.utils.security import create_access_token
    from datetime import timedelta
    token = create_access_token("user@test.com")
    assert isinstance(token, str) and len(token) > 10
    token2 = create_access_token("user@test.com", expires_delta=timedelta(hours=2))
    assert isinstance(token2, str)

# ═══════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ═══════════════════════════════════════════════════════════

def test_custom_exceptions():
    from fpt_customer_chatbot_api.utils.exceptions import NotFoundException, UnauthorizedException, ForbiddenException
    e1 = NotFoundException("not found")
    assert e1.status_code == 404
    e2 = UnauthorizedException("no auth")
    assert e2.status_code == 401
    e3 = ForbiddenException("forbidden")
    assert e3.status_code == 403

# ═══════════════════════════════════════════════════════════
# SCHEMA VALIDATIONS
# ═══════════════════════════════════════════════════════════

def test_user_schema_password_validation():
    from fpt_customer_chatbot_api.schemas.user import UserCreate, UserUpdate
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="123", full_name="Test")
    with pytest.raises(ValidationError):
        UserUpdate(password="12")
    u = UserUpdate(password=None)
    assert u.password is None

# ═══════════════════════════════════════════════════════════
# ERROR HANDLER (ai_utils)
# ═══════════════════════════════════════════════════════════

def test_error_handler_classes():
    from fpt_customer_chatbot_api.services.ai_utils.error_handler import (
        ChatbotError, ToolExecutionError, AgentRoutingError
    )
    e = ChatbotError("detail", user_message="Friendly msg")
    assert e.user_message == "Friendly msg"
    assert isinstance(ToolExecutionError("x"), ChatbotError)
    assert isinstance(AgentRoutingError("x"), ChatbotError)

def test_handle_graph_error():
    from fpt_customer_chatbot_api.services.ai_utils.error_handler import handle_graph_error
    class AuthenticationError(Exception): pass
    class RateLimitError(Exception): pass
    class APIConnectionError(Exception): pass
    class TimeoutError(Exception): pass
    assert "API keys" in handle_graph_error(AuthenticationError("x"))
    assert "moment" in handle_graph_error(RateLimitError("x"))
    assert "connect" in handle_graph_error(APIConnectionError("x")).lower()
    assert "timed out" in handle_graph_error(TimeoutError("x")).lower()
    assert "unexpected" in handle_graph_error(ValueError("x")).lower()

def test_safe_invoke():
    from fpt_customer_chatbot_api.services.ai_utils.error_handler import safe_invoke
    graph = MagicMock()
    graph.invoke.return_value = {"messages": [AIMessage(content="OK")]}
    assert "messages" in safe_invoke(graph, {}, {})
    graph.invoke.side_effect = ValueError("Boom")
    result = safe_invoke(graph, {}, {})
    assert "Boom" in result["error"]

# ═══════════════════════════════════════════════════════════
# AI SCHEMAS (ai_schemas)
# ═══════════════════════════════════════════════════════════

def test_ai_schemas_instantiation():
    from fpt_customer_chatbot_api.services.ai_schemas.ticket_schemas import Ticket, TicketStatus, CreateTicket, TrackTicket, UpdateTicket, CancelTicket
    from fpt_customer_chatbot_api.services.ai_schemas.booking_schemas import Booking, BookingStatus, BookRoom, TrackBooking, UpdateBooking, CancelBooking
    
    # Ticket Schemas
    t = Ticket(content="c", customer_name="n", customer_phone="p")
    assert t.status == TicketStatus.PENDING
    assert CreateTicket(content="c", customer_name="n", customer_phone="p")
    assert TrackTicket(ticket_id="id")
    assert UpdateTicket(ticket_id="id", status="Resolved")
    assert CancelTicket(ticket_id="id")

    # Booking Schemas
    b = Booking(reason="r", time="2030-01-01T10:00:00", customer_name="n", customer_phone="p")
    assert b.status == BookingStatus.SCHEDULED
    assert BookRoom(reason="r", time="2030-01-01T10:00:00", customer_name="n", customer_phone="p")
    assert TrackBooking(booking_id="id")
    assert UpdateBooking(booking_id="id", reason="new")
    assert CancelBooking(booking_id="id")

# ═══════════════════════════════════════════════════════════
# LOGGING (ai_utils)
# ═══════════════════════════════════════════════════════════

def test_logging_setup():
    from fpt_customer_chatbot_api.services.ai_utils.logging import setup_logging, get_logger, ConversationLogger
    setup_logging(logging.DEBUG)
    logger = get_logger("test_mod")
    assert logger.name == "test_mod"

def test_conversation_logger():
    from fpt_customer_chatbot_api.services.ai_utils.logging import ConversationLogger
    cl = ConversationLogger("test", "abcdefgh-1234", user_id="u1")
    formatted = cl._format("Hello")
    assert "conv:abcdefgh" in formatted
    assert "user:u1" in formatted
    cl.info("i"); cl.warning("w"); cl.error("e"); cl.debug("d")
