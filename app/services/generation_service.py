import math
import uuid
from typing import Optional, Union

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.generation_job import GenerationJob, JobStatus
from app.schemas.generation import JobCreateRequest, JobStatusResponse


class GenerationService:
    """Business logic for generation jobs and certificate entity management."""

    def create_job(self, db: Session, request: JobCreateRequest) -> GenerationJob:
        """Create a new generation job and all recipient certificate records atomically."""
        job = GenerationJob(
            id=uuid.uuid4(),
            status=JobStatus.PENDING.value,
            total_count=len(request.recipients),
            successful_count=0,
            failed_count=0,
        )
        db.add(job)

        # Pre-create all certificates in PENDING state
        certificates = [
            Certificate(
                id=uuid.uuid4(),
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                certificate_title=request.certificate_title,
                certificate_date=request.certificate_date,
                certificate_id=f"CERT-{uuid.uuid4().hex[:12].upper()}",
                status=CertificateStatus.PENDING.value,
            )
            for recipient in request.recipients
        ]
        db.add_all(certificates)

        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, job_id: uuid.UUID) -> Optional[GenerationJob]:
        """Retrieve job record by UUID."""
        return db.get(GenerationJob, job_id)

    def get_job_status_response(
        self,
        db: Session,
        job_id: uuid.UUID,
    ) -> Optional[JobStatusResponse]:
        """Fetch job and build status response with progress calculations."""
        job = self.get_job(db, job_id)
        if not job:
            return None

        pending_count = max(0, job.total_count - (job.successful_count + job.failed_count))
        processed_count = job.successful_count + job.failed_count
        progress_percentage = (
            round((processed_count / job.total_count) * 100.0, 2)
            if job.total_count > 0
            else 0.0
        )

        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            total_count=job.total_count,
            successful_count=job.successful_count,
            failed_count=job.failed_count,
            pending_count=pending_count,
            progress_percentage=progress_percentage,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    def get_paginated_certificates(
        self,
        db: Session,
        job_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[list[Certificate], int, int]:
        """Fetch paginated certificate records for a specific job, with optional status filter."""
        query = select(Certificate).where(Certificate.job_id == job_id)

        if status:
            query = query.where(Certificate.status == status.upper())

        # Count total matching records
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0

        # Calculate pagination
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        stmt = query.order_by(Certificate.created_at.asc()).offset(offset).limit(page_size)
        items = list(db.scalars(stmt).all())

        return items, total, total_pages

    def get_certificate(
        self,
        db: Session,
        identifier: Union[uuid.UUID, str],
    ) -> Optional[Certificate]:
        """Retrieve a certificate by primary key UUID or unique certificate_id string."""
        if isinstance(identifier, uuid.UUID):
            return db.get(Certificate, identifier)

        # Attempt to parse string as UUID first
        try:
            parsed_uuid = uuid.UUID(identifier)
            cert = db.get(Certificate, parsed_uuid)
            if cert:
                return cert
        except ValueError:
            pass

        # Fallback to query by certificate_id string
        stmt = select(Certificate).where(Certificate.certificate_id == str(identifier))
        return db.scalar(stmt)


generation_service = GenerationService()
