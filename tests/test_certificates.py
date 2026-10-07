import os
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services.certificate_service import certificate_service


def test_get_certificate_metadata_and_download_success(client: TestClient):
    payload = {
        "certificate_title": "Cloud Architecture",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Ada Lovelace", "email": "ada@lovelace.io"},
        ],
    }

    # Create and process job
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    cert = certs_res.json()["items"][0]
    cert_db_id = cert["id"]
    cert_code = cert["certificate_id"]

    # 1. Fetch metadata by UUID
    meta_res1 = client.get(f"/api/v1/certificates/{cert_db_id}")
    assert meta_res1.status_code == 200
    assert meta_res1.json()["recipient_name"] == "Ada Lovelace"
    assert meta_res1.json()["certificate_id"] == cert_code

    # 2. Fetch metadata by Certificate String Identifier
    meta_res2 = client.get(f"/api/v1/certificates/{cert_code}")
    assert meta_res2.status_code == 200
    assert meta_res2.json()["id"] == cert_db_id

    # 3. Download generated PDF
    download_res = client.get(f"/api/v1/certificates/{cert_db_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert f"certificate_{cert_code}.pdf" in download_res.headers.get("content-disposition", "")
    assert download_res.content.startswith(b"%PDF-")


def test_get_certificate_not_found(client: TestClient):
    random_id = uuid.uuid4()
    meta_res = client.get(f"/api/v1/certificates/{random_id}")
    assert meta_res.status_code == 404
    assert "not found" in meta_res.json()["detail"].lower()


def test_download_failed_certificate_returns_400(client: TestClient):
    def mock_fail(**kwargs):
        raise RuntimeError("PDF layout rendering failed")

    with patch.object(certificate_service, "generate_and_save", side_effect=mock_fail):
        payload = {
            "certificate_title": "Failed Rendering Course",
            "certificate_date": "2026-10-07",
            "recipients": [
                {"name": "Failed User", "email": "fail@test.com"},
            ],
        }

        response = client.post("/api/v1/jobs", json=payload)
        job_id = response.json()["job_id"]

        certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
        cert_id = certs_res.json()["items"][0]["id"]

        # Attempt download on failed certificate
        dl_res = client.get(f"/api/v1/certificates/{cert_id}/download")
        assert dl_res.status_code == 400
        assert "generation failed" in dl_res.json()["detail"].lower()


def test_download_missing_file_on_disk_returns_404(client: TestClient):
    payload = {
        "certificate_title": "Disk Removal Test",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Delete File User", "email": "delete@test.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert = certs_res.json()["items"][0]
    file_path = Path(cert["file_path"])

    # Simulate accidental file deletion from disk
    if file_path.exists():
        file_path.unlink()

    dl_res = client.get(f"/api/v1/certificates/{cert['id']}/download")
    assert dl_res.status_code == 404
    assert "file not found on disk" in dl_res.json()["detail"].lower()


def test_download_pending_certificate_returns_409(client: TestClient, db_session):
    from app.models.certificate import Certificate, CertificateStatus
    from app.models.generation_job import GenerationJob, JobStatus
    from datetime import date

    # Manually create job and pending certificate in DB
    job = GenerationJob(
        id=uuid.uuid4(),
        status=JobStatus.PENDING.value,
        total_count=1,
    )
    db_session.add(job)
    cert = Certificate(
        id=uuid.uuid4(),
        job_id=job.id,
        recipient_name="Pending User",
        recipient_email="pending@test.com",
        certificate_title="Pending Course",
        certificate_date=date(2026, 10, 7),
        certificate_id=f"CERT-{uuid.uuid4().hex[:12].upper()}",
        status=CertificateStatus.PENDING.value,
    )
    db_session.add(cert)
    db_session.commit()

    dl_res = client.get(f"/api/v1/certificates/{cert.id}/download")
    assert dl_res.status_code == 409
    assert "not ready" in dl_res.json()["detail"].lower()

