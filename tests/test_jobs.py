import uuid
from fastapi.testclient import TestClient


def test_create_job_success(client: TestClient):
    payload = {
        "certificate_title": "FastAPI Certification",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Developer", "email": "alice@fastapi.org"},
            {"name": "Bob Architect", "email": "bob@fastapi.org"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "job_id" in data
    assert data["total_count"] == 2
    assert data["message"] == "Certificate generation job accepted"

    job_id = data["job_id"]
    # Verify job status endpoint
    status_response = client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["job_id"] == job_id
    assert status_data["total_count"] == 2
    assert status_data["successful_count"] == 2
    assert status_data["failed_count"] == 0
    assert status_data["pending_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert status_data["status"] == "COMPLETED"


def test_job_not_found(client: TestClient):
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_job_certificates_pagination_and_filtering(client: TestClient):
    payload = {
        "certificate_title": "Fullstack Cloud Mastery",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": f"User {i}", "email": f"user{i}@cloud.com"}
            for i in range(1, 6)
        ],
    }

    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Test page 1 with page_size 2
    page1 = client.get(f"/api/v1/jobs/{job_id}/certificates?page=1&page_size=2")
    assert page1.status_code == 200
    data1 = page1.json()
    assert len(data1["items"]) == 2
    assert data1["total"] == 5
    assert data1["page"] == 1
    assert data1["page_size"] == 2
    assert data1["total_pages"] == 3

    # Test page 2 with page_size 2
    page2 = client.get(f"/api/v1/jobs/{job_id}/certificates?page=2&page_size=2")
    assert page2.status_code == 200
    data2 = page2.json()
    assert len(data2["items"]) == 2
    assert data2["items"][0]["recipient_name"] != data1["items"][0]["recipient_name"]

    # Test filtering by status
    completed_res = client.get(f"/api/v1/jobs/{job_id}/certificates?status=COMPLETED")
    assert completed_res.status_code == 200
    assert completed_res.json()["total"] == 5

    pending_res = client.get(f"/api/v1/jobs/{job_id}/certificates?status=PENDING")
    assert pending_res.status_code == 200
    assert pending_res.json()["total"] == 0


def test_job_certificates_job_not_found(client: TestClient):
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}/certificates")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_swagger_docs_available(client: TestClient):
    response = client.get("/docs")
    assert response.status_code == 200
    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == 200

