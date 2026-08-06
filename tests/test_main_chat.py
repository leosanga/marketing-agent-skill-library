# tests/test_main_chat.py
from fastapi.testclient import TestClient
from app.main import app, get_agent, security_gate
from app.agent import AgentResponse


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
