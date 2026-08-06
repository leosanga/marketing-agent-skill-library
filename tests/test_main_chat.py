# tests/test_main_chat.py
import pytest
from fastapi.testclient import TestClient
from app.main import app, check_config, get_agent, security_gate
from app.agent import AgentResponse
from app.scenarios import SCENARIOS
from app import security_gate as gate_module


class StubAgent:
    def handle_query(self, query):
        return AgentResponse(answer="stub answer", skill_used="segment_leads", skill_created=False)


def _noop_security_gate():
    return None


def test_chat_endpoint_returns_agent_response():
    app.dependency_overrides[get_agent] = lambda: StubAgent()
    app.dependency_overrides[security_gate] = _noop_security_gate
    client = TestClient(app)
    try:
        response = client.post("/chat", json={"scenario_id": "top_leads"})
        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "stub answer"
        assert body["skill_created"] is False
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_rejects_unknown_scenario():
    app.dependency_overrides[get_agent] = lambda: StubAgent()
    app.dependency_overrides[security_gate] = _noop_security_gate
    client = TestClient(app)
    try:
        response = client.post("/chat", json={"scenario_id": "not_a_real_scenario"})
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_check_config_raises_when_groq_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    with pytest.raises(RuntimeError):
        check_config()


def test_check_config_raises_when_groq_api_key_empty(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    with pytest.raises(RuntimeError):
        check_config()


def test_check_config_passes_when_groq_api_key_and_allowed_origin_present(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    check_config()  # should not raise


def test_check_config_raises_when_allowed_origin_missing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)
    with pytest.raises(RuntimeError):
        check_config()


def test_check_config_raises_when_allowed_origin_empty(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("ALLOWED_ORIGIN", "")
    with pytest.raises(RuntimeError):
        check_config()


def test_check_config_raises_when_allowed_origin_whitespace_only(monkeypatch):
    """A whitespace-only value would pass the old `not allowed_origin` check
    (truthy) and reach security_gate as a non-empty ALLOWED_ORIGIN that can
    never match a real Origin header, silently 403ing every /chat request."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("ALLOWED_ORIGIN", "   ")
    with pytest.raises(RuntimeError):
        check_config()


def test_check_config_raises_when_allowed_origin_left_as_placeholder(monkeypatch):
    """A deployer could plausibly paste the placeholder domain verbatim
    without realizing it isn't a real value. GROQ_API_KEY is correctly set
    in this scenario, proving the ALLOWED_ORIGIN check is independent."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://REPLACE_WITH_YOUR_DOMAIN.com")
    with pytest.raises(RuntimeError):
        check_config()


def test_app_fails_to_start_without_groq_api_key(monkeypatch):
    """Integration check that check_config is actually wired into app startup
    (via the lifespan handler), not just defined and unused. A misconfigured
    deployment must fail before /health can ever report green."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.com")
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass  # pragma: no cover - should never be reached


def test_app_fails_to_start_without_allowed_origin(monkeypatch):
    """Integration check mirroring test_app_fails_to_start_without_groq_api_key,
    but for ALLOWED_ORIGIN: a deploy with GROQ_API_KEY set but ALLOWED_ORIGIN
    missing must also fail startup, not silently boot and 403 every /chat
    request later."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass  # pragma: no cover - should never be reached


class RecordingStubAgent:
    def __init__(self):
        self.received_query = None

    def handle_query(self, query):
        self.received_query = query
        return AgentResponse(answer="stub answer", skill_used=None, skill_created=False)


def test_chat_endpoint_passes_scenario_query_not_scenario_id_to_agent():
    stub = RecordingStubAgent()
    app.dependency_overrides[get_agent] = lambda: stub
    app.dependency_overrides[security_gate] = _noop_security_gate
    client = TestClient(app)
    try:
        response = client.post("/chat", json={"scenario_id": "top_leads"})
        assert response.status_code == 200
        expected_query = next(s["query"] for s in SCENARIOS if s["id"] == "top_leads")
        assert stub.received_query == expected_query
        assert stub.received_query != "top_leads"
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_rejects_disallowed_origin_via_real_security_gate(monkeypatch):
    """Regression: proves /chat is actually gated by the real security_gate
    dependency, not just by whatever the test happens to override it with.
    If `dependencies=[Depends(security_gate)]` were ever accidentally removed
    from the /chat route, this test would fail."""
    monkeypatch.setattr(gate_module, "ALLOWED_ORIGIN", "https://leosanga.example")
    monkeypatch.setattr(gate_module, "_request_log", {})
    app.dependency_overrides[get_agent] = lambda: StubAgent()
    client = TestClient(app)
    try:
        response = client.post(
            "/chat",
            json={"scenario_id": "top_leads"},
            headers={"origin": "https://evil.example"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
