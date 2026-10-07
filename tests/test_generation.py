import uuid
from datetime import date
from pathlib import Path
from fastapi.testclient import TestClient

from app.services.certificate_service import certificate_service


def test_real_pdf_generation_bytes():
    """Verify that ReportLab generates a valid PDF byte buffer."""
    pdf_bytes = certificate_service.generate_pdf_bytes(
        recipient_name="Grace Hopper",
        certificate_title="Computer Science Pioneer Award",
        certificate_date=date(2026, 10, 7),
        certificate_id="CERT-TEST-HOPPER-01",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF file header
    assert pdf_bytes.startswith(b"%PDF-")


def test_real_pdf_file_generation_and_storage(override_storage: Path):
    """Verify end-to-end PDF file creation, disk persistence, and path structure."""
    job_id = uuid.uuid4()
    cert_id = uuid.uuid4()

    output_path = certificate_service.generate_and_save(
        job_id=job_id,
        certificate_db_id=cert_id,
        recipient_name="Alan Turing",
        certificate_title="Theoretical Computing Distinction",
        certificate_date=date(2026, 10, 7),
        certificate_id="CERT-TEST-TURING-02",
    )

    assert output_path.exists()
    assert output_path.is_file()
    assert output_path.name == f"{cert_id}.pdf"
    assert output_path.parent.name == str(job_id)

    # Check file content
    content = output_path.read_bytes()
    assert content.startswith(b"%PDF-")
    assert len(content) > 1500


def test_bulk_generation_creates_separate_files_for_each_recipient(client: TestClient):
    """Verify that bulk job produces distinct PDF files for each individual recipient."""
    payload = {
        "certificate_title": "Advanced Python Architecture",
        "certificate_date": "2026-10-07",
        "recipients": [
            {"name": "Dev One", "email": "dev1@example.com"},
            {"name": "Dev Two", "email": "dev2@example.com"},
            {"name": "Dev Three", "email": "dev3@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Fetch certificates for the job
    certs_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    items = certs_res.json()["items"]
    assert len(items) == 3

    created_paths = set()
    for cert in items:
        assert cert["status"] == "COMPLETED"
        assert cert["file_path"] is not None
        path = Path(cert["file_path"])
        assert path.exists()
        assert path.read_bytes().startswith(b"%PDF-")
        created_paths.add(str(path))

    # All paths must be distinct
    assert len(created_paths) == 3
