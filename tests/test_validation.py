import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


def test_empty_recipients_validation(client: TestClient):
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "2026-10-07",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "recipients" in data["detail"].lower()


def test_invalid_email_validation(client: TestClient):
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "email" in data["detail"].lower()


def test_duplicate_recipient_email_validation(client: TestClient):
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Alice Duplicate", "email": "ALICE@EXAMPLE.COM"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "duplicate" in data["detail"].lower()
    assert "alice@example.com" in data["detail"].lower()


def test_empty_recipient_name_validation(client: TestClient):
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "   ", "email": "blank@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_missing_title_validation(client: TestClient):
    payload = {
        "certificate_title": "   ",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_invalid_date_validation(client: TestClient):
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "not-a-valid-date",
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_exceeding_max_recipients_validation(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "MAX_RECIPIENTS_PER_JOB", 2)
    payload = {
        "certificate_title": "Python Specialist",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "User 1", "email": "u1@example.com"},
            {"name": "User 2", "email": "u2@example.com"},
            {"name": "User 3", "email": "u3@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "maximum" in data["detail"].lower() or "limit" in data["detail"].lower()
