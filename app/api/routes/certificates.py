from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.certificate import CertificateStatus
from app.schemas.certificate import CertificateResponse
from app.services.generation_service import generation_service
from app.services.storage_service import storage_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Get certificate metadata",
    description="Retrieve detailed metadata for a single certificate by UUID or credential ID.",
)
def get_certificate_metadata(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateResponse:
    cert = generation_service.get_certificate(db=db, identifier=certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )
    return CertificateResponse.model_validate(cert)


@router.get(
    "/{certificate_id}/download",
    summary="Download certificate PDF",
    description=(
        "Stream the generated certificate PDF file to the client using FastAPI FileResponse. "
        "Returns appropriate HTTP errors if the certificate is pending, failed, or missing."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Certificate PDF file stream.",
        },
        400: {"description": "Certificate generation failed."},
        404: {"description": "Certificate or file not found."},
        409: {"description": "Certificate is still processing."},
    },
)
def download_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    cert = generation_service.get_certificate(db=db, identifier=certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )

    if cert.status == CertificateStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate generation failed: {cert.error_message or 'Unknown generation error'}",
        )

    if cert.status in (CertificateStatus.PENDING.value, CertificateStatus.PROCESSING.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate is not ready for download (current status: {cert.status})",
        )

    if not cert.file_path or not storage_service.file_exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated certificate file not found on disk",
        )

    filename = f"certificate_{cert.certificate_id}.pdf"
    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
    )
