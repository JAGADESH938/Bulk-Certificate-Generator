import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.generation_job import GenerationJob


class CertificateStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    certificate_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    certificate_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    certificate_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=CertificateStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    job: Mapped["GenerationJob"] = relationship(
        "GenerationJob",
        back_populates="certificates",
    )
