from fastapi.testclient import TestClient

from app.database import ensure_db, record_bid
from app.main import app

ensure_db()


def test_health_and_bids_api():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Reader" in r.text

    record_bid(
        project_id="test-999",
        title="API Test Project",
        url="https://www.freelancer.in/projects/test-999",
        category="seo",
        status="skipped",
        error_message="unit test",
    )
    r = client.get("/api/bids")
    assert r.status_code == 200
    data = r.json()
    assert any(b["project_id"] == "test-999" for b in data)

    r = client.get("/api/bids/export")
    assert r.status_code == 200
    assert "project_id" in r.text


def test_bot_status():
    client = TestClient(app)
    r = client.get("/api/bot/status")
    assert r.status_code == 200
    body = r.json()
    assert "running" in body
    assert body["running"] is False


def test_start_validation():
    client = TestClient(app)
    r = client.post(
        "/api/bot/start",
        json={
            "email": "test@example.com",
            "password": "secret",
            "min_delay_seconds": 500,
            "max_delay_seconds": 100,
        },
    )
    assert r.status_code == 400
