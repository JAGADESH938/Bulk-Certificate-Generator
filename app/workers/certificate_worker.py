import logging
import uuid
from datetime import datetime, timezone
from typing import Protocol

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.certificate import Certificate, CertificateStatus
from app.models.generation_job import GenerationJob, JobStatus
from app.services.certificate_service import certificate_service

logger = logging.getLogger(__name__)


class CertificateWorkerProtocol(Protocol):
    """Worker contract allowing seamless transition to Celery or RQ."""

    def dispatch(self, job_id: uuid.UUID, background_tasks: BackgroundTasks) -> None:
        """Enqueue or dispatch the job for asynchronous execution."""
        ...

    def process_job(self, job_id: uuid.UUID) -> None:
        """Execute processing logic for a given job."""
        ...


class CertificateWorker:
    """Production background worker for isolated batch certificate generation."""

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    def dispatch(self, job_id: uuid.UUID, background_tasks: BackgroundTasks) -> None:
        """Dispatch job processing to FastAPI BackgroundTasks.
        
        To switch to Celery or RQ:
        Replace this with `celery_app.send_task('tasks.process_job', args=[str(job_id)])`.
        """
        background_tasks.add_task(self.process_job, job_id)

    def process_job(self, job_id: uuid.UUID) -> None:
        """Orchestrate certificate generation for a job with fine-grained error isolation."""
        logger.info("Starting processing for GenerationJob %s", job_id)
        db: Session = self.session_factory()

        try:
            job = db.get(GenerationJob, job_id)
            if not job:
                logger.error("Job %s not found in database", job_id)
                return

            # Transition job to PROCESSING
            job.status = JobStatus.PROCESSING.value
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            # Retrieve all pending certificates for this job
            stmt = (
                select(Certificate)
                .where(
                    Certificate.job_id == job_id,
                    Certificate.status == CertificateStatus.PENDING.value,
                )
                .order_by(Certificate.created_at.asc())
            )
            certificates = list(db.scalars(stmt).all())

            for cert in certificates:
                # Mark individual certificate as PROCESSING
                cert.status = CertificateStatus.PROCESSING.value
                db.commit()

                try:
                    # Attempt PDF generation and filesystem storage
                    file_path = certificate_service.generate_and_save(
                        job_id=job.id,
                        certificate_db_id=cert.id,
                        recipient_name=cert.recipient_name,
                        certificate_title=cert.certificate_title,
                        certificate_date=cert.certificate_date,
                        certificate_id=cert.certificate_id,
                    )

                    cert.status = CertificateStatus.COMPLETED.value
                    cert.file_path = str(file_path)
                    cert.error_message = None
                    cert.completed_at = datetime.now(timezone.utc)
                    job.successful_count += 1
                    db.commit()
                    logger.debug("Successfully generated certificate %s for %s", cert.id, cert.recipient_email)

                except Exception as exc:
                    # Isolate failure: roll back uncommitted changes, record error, and proceed
                    db.rollback()
                    logger.warning(
                        "Failed generating certificate %s for recipient %s: %s",
                        cert.id,
                        cert.recipient_email,
                        str(exc),
                    )
                    cert.status = CertificateStatus.FAILED.value
                    cert.error_message = str(exc)
                    cert.completed_at = datetime.now(timezone.utc)
                    job.failed_count += 1
                    db.commit()

            # Determine final job outcome based on individual results
            if job.total_count == 0:
                job.status = JobStatus.COMPLETED.value
            elif job.failed_count == job.total_count:
                job.status = JobStatus.FAILED.value
            elif job.failed_count > 0:
                job.status = JobStatus.COMPLETED_WITH_ERRORS.value
            else:
                job.status = JobStatus.COMPLETED.value

            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(
                "Job %s completed with status %s (Success: %d, Failed: %d)",
                job_id,
                job.status,
                job.successful_count,
                job.failed_count,
            )

        except Exception as catastrophic_exc:
            logger.exception("Fatal failure while processing job %s: %s", job_id, catastrophic_exc)
            try:
                db.rollback()
                job = db.get(GenerationJob, job_id)
                if job:
                    job.status = JobStatus.FAILED.value
                    job.error_message = f"Fatal worker error: {catastrophic_exc}"
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                logger.exception("Unable to update failed status for job %s", job_id)
        finally:
            db.close()


certificate_worker = CertificateWorker()
