import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.schemas.certificate import CertificateResponse, RecipientInput
from app.utils.validation import TITLE_MAX_LENGTH, normalize_string


class JobCreateRequest(BaseModel):
    certificate_title: str = Field(
        ...,
        min_length=1,
        max_length=TITLE_MAX_LENGTH,
        description="Title or course name to display on the certificates",
        examples=["Python Course Completion"],
    )
    certificate_date: date = Field(
        ...,
        description="Issue date for the certificate (YYYY-MM-DD)",
        examples=["2026-10-07"],
    )
    recipients: list[RecipientInput] = Field(
        ...,
        min_length=1,
        description="List of certificate recipients",
    )

    @field_validator("certificate_title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return normalize_string(v)

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: list[RecipientInput]) -> list[RecipientInput]:
        if not v:
            raise ValueError("Recipients list cannot be empty")
        
        if len(v) > settings.MAX_RECIPIENTS_PER_JOB:
            raise ValueError(
                f"Recipients list exceeds maximum allowed limit of {settings.MAX_RECIPIENTS_PER_JOB}"
            )

        seen_emails: set[str] = set()
        duplicates: set[str] = set()
        for recipient in v:
            normalized_email = recipient.email.lower()
            if normalized_email in seen_emails:
                duplicates.add(normalized_email)
            seen_emails.add(normalized_email)

        if duplicates:
            raise ValueError(
                f"Duplicate recipient emails found in request: {', '.join(sorted(duplicates))}"
            )

        return v


class JobCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total_count: int
    message: str = "Certificate generation job accepted"


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    total_count: int
    successful_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    certificates: Optional[list[CertificateResponse]] = None

    model_config = ConfigDict(from_attributes=True)
