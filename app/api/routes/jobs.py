import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.certificate import CertificateResponse, PaginatedCertificatesResponse
from app.schemas.generation import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
)
from app.services.generation_service import generation_service
from app.workers.certificate_worker import certificate_worker

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create bulk certificate generation job",
    description=(
        "Accepts a bulk certificate request, validates the input payload, "
        "persists the job and pending certificates atomically, triggers asynchronous "
        "processing, and immediately returns HTTP 202 Accepted."
    ),
)
def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = generation_service.create_job(db=db, request=request)
    certificate_worker.dispatch(job_id=job.id, background_tasks=background_tasks)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        message="Certificate generation job accepted",
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and progress",
    description="Retrieves the current progress counters and processing status of a certificate generation job.",
)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    job_status = generation_service.get_job_status_response(db=db, job_id=job_id)
    if not job_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job '{job_id}' not found",
        )
    return job_status


@router.get(
    "/{job_id}/certificates",
    response_model=PaginatedCertificatesResponse,
    summary="Get paginated certificates for a job",
    description="Returns paginated certificate records for the specified job, optionally filtered by status.",
)
def get_job_certificates(
    job_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Optional filter by status (PENDING, PROCESSING, COMPLETED, FAILED)",
    ),
    db: Session = Depends(get_db),
) -> PaginatedCertificatesResponse:
    job = generation_service.get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation job '{job_id}' not found",
        )

    items, total, total_pages = generation_service.get_paginated_certificates(
        db=db,
        job_id=job_id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )

    return PaginatedCertificatesResponse(
        items=[CertificateResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
