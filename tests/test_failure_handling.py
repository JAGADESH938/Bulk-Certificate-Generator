from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services.certificate_service import certificate_service


def test_individual_failure_does_not_halt_bulk_job(client: TestClient):
    """Verify that when one certificate generation fails, the rest proceed and complete."""
    original_generate_and_save = certificate_service.generate_and_save

    def mock_generate_and_save(**kwargs):
        if kwargs.get("recipient_name") == "Error Prone User":
            raise RuntimeError("Disk write error simulated for test")
        return original_generate_and_save(**kwargs)

    with patch.object(certificate_service, "generate_and_save", side_effect=mock_generate_and_save):
        payload = {
            "certificate_title": "Distributed Systems",
            "certificate_date": "2026-10-07",
            "recipients": [
                {"name": "Alice Healthy", "email": "alice@healthy.com"},
                {"name": "Error Prone User", "email": "error@prone.com"},
                {"name": "Charlie Healthy", "email": "charlie@healthy.com"},
            ],
        }

        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Check job status
        status_res = client.get(f"/api/v1/jobs/{job_id}")
        assert status_res.status_code == 200
        job_data = status_res.json()

        assert job_data["status"] == "COMPLETED_WITH_ERRORS"
        assert job_data["total_count"] == 3
        assert job_data["successful_count"] == 2
        assert job_data["failed_count"] == 1
        assert job_data["pending_count"] == 0

        # Check individual certificates
        certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
        assert certs_res.status_code == 200
        items = certs_res.json()["items"]

        # Sort items by name for consistent assertion
        items_by_name = {c["recipient_name"]: c for c in items}

        alice = items_by_name["Alice Healthy"]
        assert alice["status"] == "COMPLETED"
        assert alice["file_path"] is not None
        assert alice["error_message"] is None

        err_user = items_by_name["Error Prone User"]
        assert err_user["status"] == "FAILED"
        assert err_user["file_path"] is None
        assert "Disk write error simulated" in err_user["error_message"]

        charlie = items_by_name["Charlie Healthy"]
        assert charlie["status"] == "COMPLETED"
        assert charlie["file_path"] is not None
        assert charlie["error_message"] is None


def test_all_certificates_failure_marks_job_failed(client: TestClient):
    """Verify that when all certificates fail, the job ends with FAILED status."""
    def mock_always_fail(**kwargs):
        raise ValueError("Simulated PDF engine crash")

    with patch.object(certificate_service, "generate_and_save", side_effect=mock_always_fail):
        payload = {
            "certificate_title": "Failure Testing Course",
            "certificate_date": "2026-10-07",
            "recipients": [
                {"name": "Recipient One", "email": "r1@test.com"},
                {"name": "Recipient Two", "email": "r2@test.com"},
            ],
        }

        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        status_res = client.get(f"/api/v1/jobs/{job_id}")
        assert status_res.status_code == 200
        job_data = status_res.json()

        assert job_data["status"] == "FAILED"
        assert job_data["successful_count"] == 0
        assert job_data["failed_count"] == 2
