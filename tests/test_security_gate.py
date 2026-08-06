import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app import security_gate as gate_module
from app.security_gate import security_gate


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(gate_module, "ALLOWED_ORIGIN", "https://leosanga.example")
    monkeypatch.setattr(gate_module, "_request_log", {})
    test_app = FastAPI()

    @test_app.get("/protected", dependencies=[Depends(security_gate)])
    def protected():
        return {"ok": True}

    return TestClient(test_app)


def test_allows_request_from_allowed_origin(client):
    response = client.get("/protected", headers={"origin": "https://leosanga.example"})
    assert response.status_code == 200

def test_blocks_request_from_disallowed_origin(client):
    response = client.get("/protected", headers={"origin": "https://evil.example"})
    assert response.status_code == 403

def test_blocks_after_rate_limit_exceeded(client):
    headers = {"origin": "https://leosanga.example"}
    for _ in range(5):
        response = client.get("/protected", headers=headers)
        assert response.status_code == 200
    response = client.get("/protected", headers=headers)
    assert response.status_code == 429
